"""An entity (object) schema: Schemas/<Name>/ (EntitySchemaManager) and Resources/<Name>.Entity/.

metadata.json is a diff against the parent schema (BaseEntity, BaseLookup, or the base object a
replacing schema extends); `effective` is parent + diff. Columns this package adds are the
`+ MetaData.Schema.D2 {column}` lines and are edited in place; changes to inherited columns and
to object flags become `= / + / -` lines picked by comparing with the parent, so they need a
known parent: BaseEntity / BaseLookup ship as assets, own objects of the workspace are read,
and any other base (a replacing Contact, an object derived from Account) is fetched from an
environment once and cached (entity.hierarchy, `objects.py base`). Without one, only the columns
this package adds can be changed.

After a push the platform updates the table itself (columns, indexes, constraints) - unless the
object is virtual or a DB view: then it leaves the table alone. `entity.database.check` compares.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..diff import SchemaDiff, path_of
from ..files import ALL_DATA_VALUE_TYPES, ONLY_83, dump_json, is_uid, new_uid, read_text, write_text
from ..resources import Resources
from ..schema import WARNING, Descriptor, Schema
from ..workspace import Package
from .hierarchy import load_base
from .catalog import (BASE_ENTITY_UID, BASE_LOOKUP_UID, COLUMN_FLAGS, OBJECT_FLAGS, PARENT_NAMES, STOCK_ENTITIES, column_flags,
                      ordered_column, stock_parent, template)

COLUMNS = "MetaData.Schema.D2"
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
TEXT_WIDTH = {"ShortText": 50, "MediumText": 250, "LongText": 500, "MaxSizeText": 10 ** 9}  # a type may only grow along this
DEFAULT_VERSION = "8.2.3.1351"


class EntitySchema(Schema):
    RESOURCE_SUFFIX = "Entity"

    def load_metadata(self, text: str) -> None:
        self.full = text.lstrip().startswith("{")  # one package in the corpus stores the whole schema
        self.delta = None if self.full else SchemaDiff(text, self.newline)
        self.meta = json.loads(text) if self.full else None
        self.properties_path = self.dir / "properties.json"
        self.properties_text, self.properties_bom = read_text(self.properties_path) if self.properties_path.is_file() else ("", True)
        self.properties = json.loads(self.properties_text)["Properties"] if self.properties_text else {}
        self._parent: dict | None | bool = False  # False = not resolved yet
        self._base_info: dict | None = None

    def render_metadata(self) -> str:
        return dump_json(self.meta, self.newline) if self.full else self.delta.render()

    def files(self):
        out = super().files()
        if self.properties_text:
            text = dump_json({"Properties": self.properties}, self.newline)
            out[self.properties_path] = (self.properties_text if json.loads(self.properties_text)["Properties"] == self.properties else text, self.properties_bom)
        return out

    # ======================================================================= #
    # Reading
    # ======================================================================= #

    @property
    def uid(self) -> str:
        return self.descriptor.data["UId"]

    @property
    def replacing(self) -> bool:
        return bool(self.descriptor.data.get("ExtendParent"))

    @property
    def parent_uid(self) -> str | None:
        parent = self.descriptor.data.get("Parent") or {}
        return (parent.get("UId") or "").lower() or None

    @property
    def parent_name(self) -> str | None:
        return (self.descriptor.data.get("Parent") or {}).get("Name")

    @property
    def version(self) -> str:
        return (self.meta["MetaData"]["Schema"] if self.full else {}).get("B8") or (self.delta.value("MetaData.Schema.B8") if self.delta else None) or DEFAULT_VERSION

    @property
    def is_83(self) -> bool:
        return tuple(int(x) for x in self.version.split(".")[:2]) >= (8, 3)

    @property
    def parent(self) -> dict | None:
        """The effective parent schema, when it can be known here."""
        if self._parent is False:
            self._parent = stock_parent(self.parent_uid)
            cached = load_base(self.package, self.parent_name) if self._parent is None and self.parent_name else None
            if cached:
                self._parent = cached["schema"]
                self._base_info = {k: v for k, v in cached.items() if k != "schema"}
            if self._parent is None and self.parent_uid:
                for s in self.workspace.find(self.parent_uid, "EntitySchemaManager"):
                    if s["uid"] == s["base"] and s["dir"] != self.dir:  # an own object of the workspace
                        self._parent = EntitySchema(s["dir"].parent.parent, s["name"]).effective
                        break
        return self._parent

    @property
    def base_info(self) -> dict | None:
        """Where a fetched base came from (env, date, merge chain), or None."""
        self.parent
        return self._base_info

    @property
    def effective(self) -> dict | None:
        if self.full:
            return self.meta["MetaData"]["Schema"]
        return self.delta.apply(self.parent) if self.parent is not None else None

    def own_columns(self) -> list[dict]:
        """Columns this package adds (live dicts)."""
        return self.meta["MetaData"]["Schema"].get("D2", []) if self.full else self.delta.added_items(COLUMNS)

    def columns(self) -> list[dict]:
        """Every column when the parent is known, else the ones this package adds."""
        eff = self.effective
        return eff.get("D2", []) if eff is not None else self.own_columns()

    def column(self, name: str) -> dict:
        for c in self.columns():
            if c["A2"] == name:
                return c
        raise KeyError(f"no column {name!r} in {self.name}; have {[c['A2'] for c in self.columns()]}")

    def is_own(self, column: dict) -> bool:
        return any(c["UId"] == column["UId"] for c in self.own_columns())

    def flag(self, name: str) -> bool | None:
        """An object flag (OBJECT_FLAGS) in the effective schema; None when the parent is unknown."""
        eff = self.effective
        return None if eff is None else bool(eff.get(OBJECT_FLAGS[name][0]))

    def ref_name(self, uid: str | None) -> str | None:
        if not uid:
            return None
        return self.workspace.name_of(uid) or next((n for n, u in STOCK_ENTITIES.items() if u == uid.lower()), uid)

    def _ref_uid(self, ref: str) -> str:
        if is_uid(ref):
            return ref.lower()
        hits = self.workspace.find(ref, "EntitySchemaManager")
        if hits:
            return hits[0]["base"]
        if ref in STOCK_ENTITIES:
            return STOCK_ENTITIES[ref]
        raise KeyError(f"lookup target {ref!r} is neither in the workspace nor a stock 8.2.3 object; pass its UId")

    # ======================================================================= #
    # Changing
    # ======================================================================= #

    def _require_diff(self) -> None:
        if self.full:
            raise ValueError(f"{self.name} stores its whole schema (not a diff); edit it in the designer")

    def _require_parent(self, what: str) -> dict:
        if self.parent is None:
            raise ValueError(f"{what} needs the base of {self.name} ({self.parent_name}); fetch it once: "
                             f"objects.py base {self.package} {self.name} --env <env>")
        return self.parent

    def add_column(self, name: str, type_name: str, caption: str = "", ref: str | None = None, default=None, **flags) -> dict:
        """A new column the way the designer writes it; a lookup is indexed and a simple list unless the flags say otherwise."""
        self._require_diff()
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"{name!r} is not a valid column name")
        if any(c["A2"].lower() == name.lower() for c in self.columns()):
            raise ValueError(f"column {name} exists")
        types = {v: k for k, v in ALL_DATA_VALUE_TYPES.items()}
        if type_name not in types:
            raise ValueError(f"unknown type {type_name}; one of {sorted(types)}")
        if type_name in ONLY_83 and not self.is_83:
            raise ValueError(f"{type_name} exists only from Creatio 8.3 (the schema says {self.version})")
        col = {"UId": new_uid(), "A2": name, "A3": self.uid, "A4": self.uid, "A5": self.delta.value("MetaData.Schema.A5") or self.uid,
               "S2": types[type_name]}
        if type_name == "Lookup":
            if not ref:
                raise ValueError("a lookup needs ref (the referenced object)")
            col.update({"S4": self._ref_uid(ref), "E6": True, "E20": True, "E17": f"{name}Id", "E18": f"{name}Name"})
        if default is not None:
            col["E12"] = {"FB1": 1, "FB2": str(default)}  # booleans as "True" / "False", the designer's spelling
        self._apply_flags(col, flags)
        self.delta.add_item(COLUMNS, ordered_column(col))
        self.resources.set(f"Columns.{name}.Caption", caption or name, ["en-US"])  # the designer writes column captions to en-US
        return col

    @staticmethod
    def _reorder(col: dict) -> None:
        ordered = ordered_column(col)
        col.clear()
        col.update(ordered)

    @staticmethod
    def _apply_flags(col: dict, flags: dict) -> None:
        for flag, on in flags.items():
            if flag.replace("_", "-") not in COLUMN_FLAGS:
                raise ValueError(f"unknown column flag {flag}; one of {sorted(COLUMN_FLAGS)}")
            key, on_value, off_value = COLUMN_FLAGS[flag.replace("_", "-")]
            value = on_value if on else off_value
            if value is None:
                col.pop(key, None)
            else:
                col[key] = value

    def set_column(self, name: str, **flags) -> None:
        """Change flags of a column: in place for a column this package adds, as diff lines for an inherited one."""
        self._require_diff()
        col = self.column(name)
        own = next((c for c in self.own_columns() if c["UId"] == col["UId"]), None)
        if own is not None:
            self._apply_flags(own, flags)
            self._reorder(own)
            return
        parent = self._require_parent(f"changing the inherited column {name}")
        for flag, on in flags.items():
            key, on_value, off_value = COLUMN_FLAGS[flag.replace("_", "-")]
            value = on_value if on else off_value
            path = path_of("D2", (col["UId"],), key)
            if value is None:
                self.delta.delete(parent, path)
            else:
                self.delta.set(parent, path, value)

    def set_default(self, name: str, value) -> None:
        """A constant default (None removes it): in place for a column added here, a diff line for an inherited one."""
        self._require_diff()
        col = self.column(name)
        own = next((c for c in self.own_columns() if c["UId"] == col["UId"]), None)
        default = None if value is None else {"FB1": 1, "FB2": str(value)}
        if own is not None:
            if default is None:
                own.pop("E12", None)
            else:
                own["E12"] = default
                self._reorder(own)
            return
        parent, path = self._require_parent(f"changing the default of {name}"), path_of("D2", (col["UId"],), "E12")
        if default is None:
            self.delta.delete(parent, path)
        else:
            self.delta.set(parent, path, default)

    def set_type(self, name: str, type_name: str) -> None:
        """Widen a text column (ShortText -> MediumText -> LongText -> MaxSizeText); anything else could cut or lose
        the data already in the table, so it is refused."""
        self._require_diff()
        col = self.column(name)
        current = ALL_DATA_VALUE_TYPES.get(col.get("S2"))
        if current not in TEXT_WIDTH or type_name not in TEXT_WIDTH or TEXT_WIDTH[type_name] <= TEXT_WIDTH[current]:
            raise ValueError(f"{name}: {current} -> {type_name} is refused; only a text column can grow "
                             f"({' -> '.join(TEXT_WIDTH)})")
        uid = {v: k for k, v in ALL_DATA_VALUE_TYPES.items()}[type_name]
        own = next((c for c in self.own_columns() if c["UId"] == col["UId"]), None)
        if own is not None:
            own["S2"] = uid
        else:
            self.delta.set(self._require_parent(f"changing the type of {name}"), path_of("D2", (col["UId"],), "S2"), uid)

    def remove_column(self, name: str) -> str:
        """Remove a column this package adds; returns its UId. The table column and its data are the platform's business."""
        self._require_diff()
        col = next((c for c in self.own_columns() if c["A2"] == name), None)
        if col is None:
            raise ValueError(f"{name} is not a column this package adds; inherited columns cannot be removed")
        if self.delta.value("MetaData.Schema.D4") == col["UId"]:
            raise ValueError(f"{name} is the display column; set another one first")
        self.delta.remove_item(COLUMNS, col["UId"])
        self.resources.remove_prefix(f"Columns.{name}")
        return col["UId"]

    def set_flag(self, name: str, on: bool) -> None:
        """An object flag (OBJECT_FLAGS): metadata and properties.json together."""
        self._require_diff()
        if name not in OBJECT_FLAGS:
            raise ValueError(f"unknown object flag {name}; one of {sorted(OBJECT_FLAGS)}")
        key, prop = OBJECT_FLAGS[name]
        parent = self._require_parent(f"changing {name}")
        path = path_of(key)
        if on:
            self.delta.set(parent, path, True)
        else:
            self.delta.delete(parent, path)
        if prop and prop in self.properties:
            self.properties[prop] = "True" if on else "False"

    def set_display_column(self, name: str) -> None:
        self._require_diff()
        self.delta.set(self._require_parent("changing the display column"), path_of("D4"), self.column(name)["UId"])

    def set_caption(self, target: str, value: str, cultures: list[str] | None = None) -> str:
        """'' / 'Object' for the object (every culture of the schema by default, and the descriptor), else a column name."""
        if target in ("", "Object", "Caption"):
            self.resources.set("Caption", value, cultures)
            if cultures is None or "en-US" in cultures:
                self.descriptor.set_caption(value)
            return "Caption"
        self.column(target)
        key = f"Columns.{target}.Caption"
        self.resources.set(key, value, cultures or ["en-US"])
        return key

    # ======================================================================= #
    # Checks and reports
    # ======================================================================= #

    def validate(self) -> list[str]:
        problems = []
        cols = self.columns()
        names = [c["A2"].lower() for c in cols]
        problems += [f"duplicate column name {n}" for n in sorted({n for n in names if names.count(n) > 1})]
        prefix = re.match(r"[a-z]+", self.name)
        for c in self.own_columns():
            t = ALL_DATA_VALUE_TYPES.get(c.get("S2"))
            if t is None:
                problems.append(f"column {c['A2']}: unknown data value type {c.get('S2')}")
            elif t in ONLY_83 and not self.is_83:
                problems.append(f"column {c['A2']}: {t} exists only from Creatio 8.3 (the schema says {self.version})")
            if t == "Lookup" and not c.get("S4"):
                problems.append(f"column {c['A2']}: a lookup without a referenced object (S4)")
            if c.get("E8") and c.get("E9"):
                problems.append(f"{WARNING}column {c['A2']}: weak reference (no foreign key) together with cascade delete")
            if not self.resources.get(f"Columns.{c['A2']}.Caption"):
                problems.append(f"{WARNING}column {c['A2']} has no en-US caption")
            if prefix and not self.replacing and not c["A2"].startswith(prefix.group(0)):
                problems.append(f"{WARNING}column {c['A2']} lacks the prefix {prefix.group(0)!r} of the object")
        if self.delta:
            order = self.delta.find(COLUMNS, "~")
            uids = {c["UId"] for c in cols}
            if order and self.effective is not None and set(order[3]) != uids:
                problems.append(f"the column order (~ D2) lists {len(order[3])} columns, the object has {len(uids)}")
        eff = self.effective
        if eff is not None:
            for flag, (key, prop) in OBJECT_FLAGS.items():
                if prop and prop in self.properties and (self.properties[prop] == "True") != bool(eff.get(key)):
                    problems.append(f"{flag}: properties.json says {self.properties[prop]}, the metadata says {bool(eff.get(key))}")
            if (eff.get("D1") or eff.get("D10")) and not self.replacing:
                problems.append(f"{WARNING}the object is {'virtual' if eff.get('D1') else 'a DB view'}: the platform does not create or "
                                f"change its table, so columns, indexes and constraints are not applied on push")
        if not self.resources.get("Caption") and not self.replacing:
            problems.append("the object has no en-US caption")
        missing = [c for c, items in self.resources.cultures.items() if "Caption" not in items]
        if missing and not self.replacing:
            problems.append(f"{WARNING}no object caption in {len(missing)} culture(s) ({', '.join(missing[:3])}...): they show the parent's caption")
        return problems

    def describe_column(self, c: dict) -> str:
        t = ALL_DATA_VALUE_TYPES.get(c.get("S2"), c.get("S2"))
        ref = f" -> {self.ref_name(c.get('S4'))}" if c.get("S4") else ""
        default = f" default={c['E12'].get('FB2', c['E12'])!r}" if isinstance(c.get("E12"), dict) else ""
        flags = column_flags(c)
        caption = self.resources.get(f"Columns.{c['A2']}.Caption")
        return f"    {c['A2']:<28} {t}{ref}{default}{'  [' + ', '.join(flags) + ']' if flags else ''}{'  ' + repr(caption) if caption else ''}"

    def describe(self) -> str:
        kind = "replacing" if self.replacing else "own"
        caption = self.resources.get("Caption") or self.descriptor.data.get("Caption")
        lines = [f"{self.name}: {caption!r}  {kind} object, parent {self.parent_name}, created in {self.version}, uid={self.uid}"]
        eff = self.effective
        if eff is None:
            lines.append(f"  base {self.parent_name} is not known here (objects.py base ... --env): showing the columns this package adds")
        else:
            if self.base_info:
                lines.append(f"  base: fetched from {self.base_info['env']} on {self.base_info['fetched']}, merged from {' > '.join(self.base_info['chain'])}")
            on = [f for f in OBJECT_FLAGS if self.flag(f)]
            lines.append(f"  flags: {', '.join(on) or '-'}")
            display = next((c["A2"] for c in eff.get("D2", []) if c["UId"] == eff.get("D4")), None)
            lines.append(f"  display column: {display or '-'}")
        own = self.own_columns()
        lines.append(f"  columns added here ({len(own)}):")
        lines += [self.describe_column(c) for c in own]
        if eff is not None:
            inherited = [c["A2"] for c in eff.get("D2", []) if not self.is_own(c)]
            lines.append(f"  inherited ({len(inherited)}): {', '.join(inherited)}")
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # ======================================================================= #
    # New object
    # ======================================================================= #

    @classmethod
    def create(cls, package: Path, name: str, caption: str, parent: str = "BaseEntity", version: str = DEFAULT_VERSION,
               cultures: list[str] | None = None) -> "EntitySchema":
        """A new object as the 8.2.3 designer writes it (no columns yet). Its caption goes to every culture of the
        package: a culture without one shows the parent's caption ("Base object")."""
        package = Path(package)
        if not NAME_RE.fullmatch(name):
            raise ValueError(f"{name!r} is not a valid schema name")
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        parent_uid = {v: k for k, v in PARENT_NAMES.items()}.get(parent)
        if parent_uid is None:
            raise ValueError(f"parent must be one of {sorted(PARENT_NAMES.values())}")
        pkg = Package(package)
        uid, events_uid = new_uid(), new_uid()
        prefix = re.match(r"[a-z]*", name).group(0)
        meta = template(parent)
        for k, v in {"uid": uid, "name": name, "created_in": pkg.created_in_uid(), "package": pkg.uid, "version": version,
                     "events_uid": events_uid, "events_name": f"{prefix}Entity_{events_uid.replace('-', '')[:7]}EventsProcess"}.items():
            meta = meta.replace("{" + k + "}", v)
        write_text(sdir / "metadata.json", meta, False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "Parent": {"UId": parent_uid, "Name": parent},
                                                          "ManagerName": "EntitySchemaManager", "Caption": caption, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {
            "AdministratedByColumns": "False", "AdministratedByOperations": "False", "AdministratedByRecords": "False", "CreatedInVersion": version,
            "IsSSPAvailable": "False", "IsTrackChangesInDB": "False", "IsVirtual": "False", "UseLiveEditing": "False"}}), True)
        write_text(sdir / f"{name}.cs", "", False)
        ent = cls(package, name)
        known = sorted({p.name[len("resource."):-len(".xml")] for p in package.glob("Resources/*/resource.*.xml")})
        ent.resources = Resources.empty(ent.resources.folder, cultures or known or ["en-US"])
        ent.resources.set("Caption", caption)
        ent.resources.set("EventsProcessSchema.Caption", "Business process", ["en-US"])
        ent.save()
        return ent

    @classmethod
    def create_replacing(cls, package: Path, name: str, version: str = DEFAULT_VERSION) -> "EntitySchema":
        """A replacing copy of `name` in `package`, written like the 8.2.3 designer does: its own events process
        (EG1, inheriting the base's one through BK8), B7 true, D8 the base. Needs the base fetched (load_base)."""
        package = Path(package)
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        base = load_base(package, name)
        if base is None:
            raise ValueError(f"fetch the base of {name} first: objects.py base {package} {name} --env <env>")
        parent, pkg = base["schema"], Package(package)
        uid, events_uid, created_in = new_uid(), new_uid(), pkg.created_in_uid()
        prefix = re.match(r"[a-z]*", pkg.name).group(0)
        d = SchemaDiff("")
        for path, value in (("UId", uid), ("A5", created_in), ("B6", pkg.uid), ("B8", version),
                            ("EG1.UId", events_uid), ("EG1.A2", f"{prefix}Entity_{events_uid.replace('-', '')[:7]}EventsProcess"),
                            ("EG1.A5", created_in), ("EG1.B8", version), ("EG1.BK8", parent["EG1"]["UId"]), ("EG1.BK15", []),
                            ("D36.A3", uid), ("D36.BS1", False)):
            d.set(parent, "MetaData.Schema." + path, value)
        d.put("+", "MetaData.Schema.B7", True)  # the designer writes both although the merged base already has them
        d.put("=", "MetaData.Schema.D8", base["uid"])
        write_text(sdir / "metadata.json", d.render(), False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "Parent": {"UId": base["uid"], "Name": name},
                                                          "ExtendParent": True, "ManagerName": "EntitySchemaManager", "Caption": base["caption"], "DependsOn": []})
        write_text(desc.path, desc.text, True)
        props = {prop: "True" if parent.get(key) else "False" for key, prop in OBJECT_FLAGS.values() if prop}
        props["CreatedInVersion"] = version
        write_text(sdir / "properties.json", dump_json({"Properties": dict(sorted(props.items()))}), True)
        write_text(sdir / f"{name}.cs", "", False)
        ent = cls(package, name)
        ent.resources = Resources.empty(ent.resources.folder, ["en-US"])
        ent.resources.set("EventsProcessSchema.Caption", "Business process", ["en-US"])
        ent.save()
        return ent
