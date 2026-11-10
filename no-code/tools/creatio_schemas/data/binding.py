"""A data binding: rows of one table installed with the package, Data/<Name>/.

    descriptor.json                {"Descriptor": {UId, Name, ModifiedOnUtc, InstallType, Schema {UId, Name},
                                    Columns [{ColumnUId, IsForceUpdate, IsKey, ColumnName, DataTypeValueUId}]}}
    data.json                      {"PackageData": [{"Row": [{SchemaColumnUId, Value[, DisplayValue]}]}]}
    filter.json                    the designer's filter of the bound rows, usually empty; kept as it is
    Localization/data.<c>.json     the localizable columns per culture: rows of {SchemaColumnUId, ColumnName, Value},
                                   the key columns included; these columns never appear in data.json

"null" (a string) is a null value; lookup cells carry DisplayValue. The platform writes the files with
different indents (two spaces, four, tabs) and escapes "/" only in "\\/Date(ms+zone)\\/" literals.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..files import ALL_DATA_VALUE_TYPES, CRLF, DVT_OF, is_uid, new_uid, newline_of, read_text, write_text
from ..schema import WARNING, Descriptor, PackageItem
from ..workspace import Workspace

NULL = "null"
LOOKUP_TYPES = {DVT_OF["Lookup"], "b039feb0-ee7c-4884-8aa6-d6d45d84316f"}  # Lookup, ImageLookup (8.3)
INSTALL_TYPES = {0: "install with package"}
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
_DATE_RE = re.compile(r'"/(Date\([^)"]*\))/"')
_INDENT_RE = re.compile(r"\n([ \t]+)\S")


class JsonFile:
    """A JSON file kept as text: unchanged, it renders to the bytes read; changed, it is dumped in the file's own style."""

    def __init__(self, path: Path, text: str | None = None, bom: bool = True):
        self.path = Path(path)
        self.text, self.bom = read_text(self.path) if text is None else (text, bom)
        if not self.text.strip():
            raise ValueError(f"{self.path}: empty file")
        try:
            self.obj = json.loads(self.text)
        except ValueError as e:
            raise ValueError(f"{self.path}: not JSON ({e})") from None
        self._read = json.dumps(self.obj)
        self.nl = newline_of(self.text)
        m = _INDENT_RE.search(self.text)
        self.indent = 2 if not m else ("\t" if m.group(1)[0] == "\t" else len(m.group(1)))
        self.end = self.nl if self.text.endswith("\n") else ""

    @classmethod
    def new(cls, path: Path, obj) -> "JsonFile":
        """As the 8.x designer writes it: BOM, CRLF, two spaces, no newline at the end."""
        return cls(path, json.dumps(obj, indent=2).replace("\n", CRLF), True)

    def render(self) -> str:
        # shortcut: a re-dump writes 0.00 as 0.0 (7 values in 373 real bindings); keep literals if that diff ever matters
        if json.dumps(self.obj) == self._read:
            return self.text
        out = json.dumps(self.obj, indent=self.indent, ensure_ascii=False)
        return _DATE_RE.sub(lambda m: '"\\/' + m.group(1) + '\\/"', out).replace("\n", self.nl) + self.end


def object_columns(workspace: Workspace, schema_name: str) -> dict[str, dict]:
    """name -> column (UId, S2 type, E21 localizable) of an object over its copies in the workspace; {} when it is not there."""
    from ..entity import EntitySchema  # local: the entity toolkit is only needed to create rows
    out = {}
    for s in workspace.find(schema_name, "EntitySchemaManager"):
        for c in EntitySchema(s["dir"].parent.parent, s["name"]).columns():
            out[c["A2"]] = c
    return out


def coerce(type_uid: str, value):
    """A command-line string as the JSON value a column of that type stores; other values pass through."""
    if not isinstance(value, str) or value == NULL:
        return value
    kind = ALL_DATA_VALUE_TYPES.get(type_uid, "")
    if kind == "Boolean":
        if value.lower() not in ("true", "false"):
            raise ValueError(f"expected true or false, got {value!r}")
        return value.lower() == "true"
    if kind == "Integer":
        return int(value)
    if kind.startswith(("Float", "Money")):
        return float(value)
    return value


class DataBinding(PackageItem):
    def __init__(self, package: Path, name: str):
        super().__init__(package, name)
        self.dir = self.package / "Data" / name
        if not (self.dir / "descriptor.json").is_file():
            if self.dir.is_dir():  # a folder the package carries, broken: the index records it as unreadable
                raise ValueError(f"{self.dir / 'descriptor.json'}: missing")
            raise FileNotFoundError(f"no data binding {name} in {self.package}")
        self.descriptor = Descriptor(self.dir / "descriptor.json")
        self.data = JsonFile(self.dir / "data.json")
        self.loc = {p.name[len("data."):-len(".json")]: JsonFile(p) for p in sorted((self.dir / "Localization").glob("data.*.json"))}

    def files(self):
        out = {self.descriptor.path: (self.descriptor.text, True), self.data.path: (self.data.render(), self.data.bom)}
        out.update({f.path: (f.render(), f.bom) for f in self.loc.values()})
        return out

    # -- reading ------------------------------------------------------------- #

    @property
    def schema_name(self) -> str:
        return self.descriptor.data["Schema"]["Name"]

    @property
    def install_type(self) -> str:
        n = self.descriptor.data.get("InstallType")
        return INSTALL_TYPES.get(n, f"install type {n}")

    @property
    def columns(self) -> dict[str, dict]:
        """name -> {uid, key, force_update, type} in the descriptor's order."""
        return {c["ColumnName"]: {"uid": c["ColumnUId"].lower(), "key": c["IsKey"], "force_update": c["IsForceUpdate"], "type": c["DataTypeValueUId"]}
                for c in self.descriptor.data.get("Columns", [])}

    @property
    def key_columns(self) -> list[str]:
        return [n for n, c in self.columns.items() if c["key"]]

    @property
    def cultures(self) -> list[str]:
        return list(self.loc)

    @property
    def localized(self) -> list[str]:
        """Columns the localisation files carry (the key columns excluded)."""
        names = {cell["ColumnName"] for f in self.loc.values() for r in f.obj["PackageData"] for cell in r["Row"]}
        return [n for n in self.columns if n in names and n not in self.key_columns]

    def _names(self) -> dict[str, str]:
        return {c["uid"]: n for n, c in self.columns.items()}

    def _key_of_cells(self, cells: list[dict]) -> str:
        values = {cell["SchemaColumnUId"].lower(): cell["Value"] for cell in cells}
        return "|".join(str(values.get(self.columns[k]["uid"], "")).lower() for k in self.key_columns)

    def key_of(self, row: dict) -> str:
        """The key of a row from rows(): the key column values joined by "|" (lower case)."""
        return "|".join(str(row.get(k, "")).lower() for k in self.key_columns)

    def _data_row(self, key: str) -> dict:
        for r in self.data.obj["PackageData"]:
            if self._key_of_cells(r["Row"]) == key.lower():
                return r
        raise KeyError(f"no row {key} in {self.name}; keys: {[self._key_of_cells(r['Row']) for r in self.data.obj['PackageData']][:10]}")

    def rows(self, culture: str | None = None) -> list[dict]:
        """Rows keyed by column name; a localised column is {culture: text}, or the text of `culture` when given."""
        names = self._names()
        loc = {c: {self._key_of_cells(r["Row"]): r["Row"] for r in f.obj["PackageData"]} for c, f in self.loc.items() if culture in (None, c)}
        out = []
        for r in self.data.obj["PackageData"]:
            row = {names.get(cell["SchemaColumnUId"].lower(), cell["SchemaColumnUId"]): cell["Value"] for cell in r["Row"]}
            key = self._key_of_cells(r["Row"])
            for col in self.localized:
                texts = {c: next((cell["Value"] for cell in rows.get(key, []) if cell["ColumnName"] == col), None) for c, rows in loc.items()}
                row[col] = texts.get(culture) if culture else texts
            out.append({n: row[n] for n in self.columns if n in row} | {n: v for n, v in row.items() if n not in self.columns})
        return out

    def row(self, key: str) -> dict:
        for r in self.rows():
            if self.key_of(r) == key.lower():
                return r
        raise KeyError(f"no row {key} in {self.name}")

    def display_values(self, key: str) -> dict[str, str]:
        """column -> DisplayValue of the lookup cells of one row."""
        names = self._names()
        return {names.get(c["SchemaColumnUId"].lower(), c["SchemaColumnUId"]): c["DisplayValue"] for c in self._data_row(key)["Row"] if "DisplayValue" in c}

    def summary(self) -> str:
        loc = set(self.localized)
        cols = " ".join(n + ("(loc)" if n in loc else "") for n in self.columns)
        return f"binds {self.schema_name}, {len(self.data.obj['PackageData'])} rows, columns {cols}, {self.install_type}"

    def describe(self) -> str:
        lines = [f"{self.name}: {self.summary()}"]
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # -- checks ---------------------------------------------------------------- #

    def validate(self) -> list[str]:
        problems = []
        cols = {c["uid"]: (n, c) for n, c in self.columns.items()}
        if not self.key_columns:
            problems.append(f"{WARNING}no key column: the install cannot match existing rows")
        seen = set()
        for r in self.data.obj["PackageData"]:
            key = self._key_of_cells(r["Row"])
            for cell in r["Row"]:
                uid = cell["SchemaColumnUId"].lower()
                if uid not in cols:
                    problems.append(f"row {key}: a value for column {uid}, which the descriptor does not list")
                elif cols[uid][1]["type"] in LOOKUP_TYPES and cell["Value"] != NULL and not is_uid(cell["Value"]):
                    problems.append(f"row {key}: lookup {cols[uid][0]} = {cell['Value']!r} is not a UId")
            if key in seen:
                problems.append(f"duplicate key {key}")
            seen.add(key)
        for culture, f in self.loc.items():
            for r in f.obj["PackageData"]:
                key = self._key_of_cells(r["Row"])
                if key not in seen:
                    problems.append(f"Localization/data.{culture}.json: row {key} is not in data.json")
        return problems

    # -- changing ------------------------------------------------------------ #

    def _column(self, column: str) -> dict:
        if column not in self.columns:
            raise KeyError(f"no column {column} in {self.name}; have {list(self.columns)}")
        return self.columns[column]

    def _loc_file(self, culture: str) -> JsonFile:
        if culture not in self.loc:
            self.loc[culture] = JsonFile.new(self.dir / "Localization" / f"data.{culture}.json", {"PackageData": []})
        return self.loc[culture]

    def _loc_row(self, culture: str, key: str) -> list[dict]:
        f = self._loc_file(culture)
        for r in f.obj["PackageData"]:
            if self._key_of_cells(r["Row"]) == key.lower():
                return r["Row"]
        cells = [c for c in self._data_row(key)["Row"] if c["SchemaColumnUId"].lower() in {self.columns[k]["uid"] for k in self.key_columns}]
        names = self._names()
        row = [{"SchemaColumnUId": c["SchemaColumnUId"], "ColumnName": names[c["SchemaColumnUId"].lower()], "Value": c["Value"]} for c in cells]
        f.obj["PackageData"].append({"Row": row})
        return row

    def set_value(self, row_key: str, column: str, value, culture: str | None = None) -> None:
        """One value; a localised column (or any column given a culture) goes to that culture's file."""
        col = self._column(column)
        if column in self.localized or culture:
            if not culture:
                raise ValueError(f"{column} is localised; give a culture ({', '.join(self.cultures)})")
            self._data_row(row_key)  # the row must exist in data.json
            cells = self._loc_row(culture, row_key)
            for cell in cells:
                if cell["SchemaColumnUId"].lower() == col["uid"]:
                    cell["Value"] = value
                    return
            cells.append({"SchemaColumnUId": col["uid"], "ColumnName": column, "Value": value})
            return
        value = coerce(col["type"], value)
        if col["type"] in LOOKUP_TYPES and value != NULL and not is_uid(value):
            raise ValueError(f"{column} is a lookup: give a record UId or null, not {value!r}")
        cells = self._data_row(row_key)["Row"]
        for cell in cells:
            if cell["SchemaColumnUId"].lower() == col["uid"]:
                if cell["Value"] != value and "DisplayValue" in cell:
                    cell["DisplayValue"] = ""  # the old caption would mislead; the install reads Value only
                cell["Value"] = value
                return
        cells.append({"SchemaColumnUId": col["uid"], "Value": value} | ({"DisplayValue": ""} if col["type"] in LOOKUP_TYPES else {}))

    def add_row(self, values: dict) -> str:
        """A new row {column: value}; a localised value is {culture: text} or one text for every culture. Returns its key."""
        values = dict(values)
        for k in self.key_columns:
            if k not in values:
                if k != "Id":
                    raise ValueError(f"the key column {k} needs a value")
                values["Id"] = new_uid()
        for n in values:
            self._column(n)
        # without Localization files the platform keeps even a localisable Name in data.json
        known = object_columns(self.workspace, self.schema_name) if self.cultures else {}
        loc = set(self.localized) | {n for n in self.columns if known.get(n, {}).get("E21")} | {n for n, v in values.items() if isinstance(v, dict)}
        for n in loc:
            values.setdefault(n, "")  # the designer writes every localised column of a row, empty when not translated
        cells = [{"SchemaColumnUId": self.columns[k]["uid"], "Value": coerce(self.columns[k]["type"], values[k])} for k in self.key_columns]
        key = self._key_of_cells(cells)
        if any(self._key_of_cells(r["Row"]) == key for r in self.data.obj["PackageData"]):
            raise ValueError(f"{self.name} already has a row {key}")
        self.data.obj["PackageData"].append({"Row": cells})
        for n in self.columns:
            if n in values and n not in loc and n not in self.key_columns:
                self.set_value(key, n, values[n])
        for n in (n for n in self.columns if n in values and n in loc):
            texts = values[n] if isinstance(values[n], dict) else {c: values[n] for c in self.cultures}
            for culture, text in texts.items():
                self.set_value(key, n, text, culture)
        return key

    def remove_row(self, key: str) -> None:
        row = self._data_row(key)
        self.data.obj["PackageData"].remove(row)
        for f in self.loc.values():
            f.obj["PackageData"] = [r for r in f.obj["PackageData"] if self._key_of_cells(r["Row"]) != key.lower()]

    # -- new ------------------------------------------------------------------- #

    @classmethod
    def create(cls, package: Path, name: str, schema_name: str, key_columns: list[str], rows: list[dict],
               cultures: list[str] | None = None, columns: list[str] | None = None) -> "DataBinding":
        """A binding of `schema_name` (an object of the workspace) with the key columns, `columns` and the columns the rows use,
        as the designer writes it."""
        package = Path(package)
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"{name!r} is not a valid binding name")
        ddir = package / "Data" / name
        if ddir.exists():
            raise FileExistsError(ddir)
        workspace = Workspace(package)
        known = object_columns(workspace, schema_name)
        if not known:
            raise KeyError(f"object {schema_name} is not in the workspace; copy an existing binding of it instead")
        used = list(dict.fromkeys(list(key_columns) + list(columns or []) + [n for r in rows for n in r]))
        missing = [n for n in used if n not in known]
        if missing:
            raise KeyError(f"{schema_name} has no column(s) {missing}; have {sorted(known)}")
        columns = [{"ColumnUId": known[n]["UId"], "IsForceUpdate": False, "IsKey": n in key_columns, "ColumnName": n,
                    "DataTypeValueUId": known[n]["S2"]} for n in used]
        desc = Descriptor.new(ddir / "descriptor.json", {"UId": new_uid(), "Name": name, "ModifiedOnUtc": "", "InstallType": 0,
                                                          "Schema": {"UId": workspace.uid_of(schema_name, "EntitySchemaManager"), "Name": schema_name},
                                                          "Columns": columns})
        write_text(desc.path, desc.text, True)
        write_text(ddir / "data.json", JsonFile.new(ddir / "data.json", {"PackageData": []}).text, True)
        write_text(ddir / "filter.json", "", False)
        binding = cls(package, name)
        if any(known[n].get("E21") for n in used):
            for culture in cultures or ["en-US"]:
                binding._loc_file(culture)
        for r in rows:
            binding.add_row(r)
        binding.save()
        return binding

    @classmethod
    def all(cls, package: Path) -> list["DataBinding"]:
        return [cls(package, d.name) for d in sorted((Path(package) / "Data").glob("*")) if (d / "descriptor.json").is_file()]
