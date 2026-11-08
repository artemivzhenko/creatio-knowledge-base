"""Freedom UI pages (client unit schemas) as package files.

The page body `Schemas/<Page>/<Page>.js` holds JSON between marker comments
(`/**SCHEMA_VIEW_CONFIG_DIFF*/[...]/**SCHEMA_VIEW_CONFIG_DIFF*/`). Those sections are parsed,
edited as data and rendered back in the file's own indentation; everything else in the body
(handlers with JavaScript in them, the define() wrapper) is kept as text. A section that was not
changed is not re-rendered, so an untouched page saves to the bytes it was read from.

Two body forms exist on 8.2.3 and both are handled: a designer-saved page has `viewModelConfig`
and `modelConfig` objects; a page clio created from a template has `viewModelConfigDiff` and
`modelConfigDiff` arrays of merge operations.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from ..files import new_uid, newline_of, read_text
from ..resources import Resources
from ..schema import WARNING, Schema

JSON_SECTIONS = ("SCHEMA_VIEW_CONFIG_DIFF", "SCHEMA_VIEW_MODEL_CONFIG", "SCHEMA_VIEW_MODEL_CONFIG_DIFF",
                 "SCHEMA_MODEL_CONFIG", "SCHEMA_MODEL_CONFIG_DIFF")

# column type -> (component type, extra values), what the 8.2.3 designer emits for a bound field
CONTROL_OF = {
    "ShortText": ("crt.Input", {}), "MediumText": ("crt.Input", {}), "LongText": ("crt.Input", {}),
    "MaxSizeText": ("crt.Input", {}), "Text": ("crt.Input", {}),
    "Integer": ("crt.NumberInput", {}), "Float": ("crt.NumberInput", {}), "Float1": ("crt.NumberInput", {}),
    "Float2": ("crt.NumberInput", {}), "Float3": ("crt.NumberInput", {}), "Float4": ("crt.NumberInput", {}),
    "Float8": ("crt.NumberInput", {}), "Money": ("crt.NumberInput", {}),
    "Boolean": ("crt.Checkbox", {}),
    "Date": ("crt.DateTimePicker", {"pickerType": "date"}),
    "DateTime": ("crt.DateTimePicker", {"pickerType": "datetime"}),
    "Time": ("crt.DateTimePicker", {"pickerType": "time"}),
    "Lookup": ("crt.ComboBox", {}),
    "RichText": ("crt.RichTextEditor", {}),
    "PhoneText": ("crt.PhoneInput", {}), "EmailText": ("crt.EmailInput", {}), "WebText": ("crt.WebInput", {}),
}

# DataValueType codes a grid column carries; the ones not listed render as text (1)
DVT_CODE = {"Guid": 0, "Text": 1, "Integer": 4, "Float": 5, "Money": 6, "DateTime": 7, "Date": 8, "Time": 9,
            "Lookup": 10, "Boolean": 12, "ShortText": 28, "MediumText": 29, "MaxSizeText": 30, "LongText": 31}

DEFAULT_FIELD_PARENT = "SideAreaProfileContainer"
DEFAULT_GRID_PARENT = "GeneralInfoTabContainer"


class _Section:
    def __init__(self, name: str, inner: str):
        self.name = name
        self.inner = inner
        self.value = json.loads(inner)
        self.original = copy.deepcopy(self.value)

    @property
    def changed(self) -> bool:
        return self.value != self.original

    def style(self) -> tuple[str, str] | None:
        """(base indent of the closing bracket, one indent step) of a multi-line section; None when it is one line."""
        lines = self.inner.split("\n")
        if len(lines) < 3:
            return None
        second, last = lines[1], lines[-1]
        base = last[: len(last) - len(last.lstrip())]
        step = second[: len(second) - len(second.lstrip())]
        return base, step[len(base):] or "\t"


class PageSchema(Schema):
    """One Freedom UI page: Schemas/<Page>/<Page>.js edited through its JSON sections."""

    RESOURCE_SUFFIX = "ClientUnit"

    def __init__(self, package: Path, name: str):
        super().__init__(package, name)
        self.body_path = self.dir / f"{name}.js"
        if not self.body_path.is_file():
            raise FileNotFoundError(f"{self.body_path} is missing: {name} is not a client unit schema")
        self.body, self.body_bom = read_text(self.body_path)
        self.body_newline = newline_of(self.body)
        self.sections: dict[str, _Section] = {}
        for sec in JSON_SECTIONS:
            m = re.search(rf"/\*\*{sec}\*/(.*?)/\*\*{sec}\*/", self.body, re.S)
            if m:
                self.sections[sec] = _Section(sec, m.group(1))

    # metadata.json is kept as it is: the body is where a page lives
    def load_metadata(self, text: str) -> None:
        self._metadata = text

    def render_metadata(self) -> str:
        return self._metadata

    # -- the two body forms ---------------------------------------------------- #

    def section(self, name: str) -> _Section:
        if name not in self.sections:
            raise KeyError(f"{self.name} has no {name} section")
        return self.sections[name]

    @property
    def view_config_diff(self) -> list:
        return self.section("SCHEMA_VIEW_CONFIG_DIFF").value

    @staticmethod
    def _merge_values(ops: list, path: list, create: bool) -> dict:
        for op in ops:
            if op.get("operation") == "merge" and op.get("path") == path:
                return op.setdefault("values", {}) if create else op.get("values", {})
        if not create:
            return {}
        op = {"operation": "merge", "path": path, "values": {}}
        ops.append(op)
        return op["values"]

    def _part(self, key: str, obj_section: str, diff_section: str, create: bool) -> dict:
        """attributes / dataSources in whichever form the body has; reading never creates anything."""
        if obj_section in self.sections:
            value = self.sections[obj_section].value
            return value.setdefault(key, {}) if create else value.get(key, {})
        return self._merge_values(self.section(diff_section).value, [key], create)

    @property
    def attributes(self) -> dict:
        """The view model attributes (a copy-safe read: write through attributes_w())."""
        return self._part("attributes", "SCHEMA_VIEW_MODEL_CONFIG", "SCHEMA_VIEW_MODEL_CONFIG_DIFF", False)

    def attributes_w(self) -> dict:
        return self._part("attributes", "SCHEMA_VIEW_MODEL_CONFIG", "SCHEMA_VIEW_MODEL_CONFIG_DIFF", True)

    @property
    def data_sources(self) -> dict:
        return self._part("dataSources", "SCHEMA_MODEL_CONFIG", "SCHEMA_MODEL_CONFIG_DIFF", False)

    def data_sources_w(self) -> dict:
        return self._part("dataSources", "SCHEMA_MODEL_CONFIG", "SCHEMA_MODEL_CONFIG_DIFF", True)

    @property
    def entity(self) -> str | None:
        """The object of the page's primary data source (PDS)."""
        return ((self.data_sources.get("PDS") or {}).get("config") or {}).get("entitySchemaName")

    # -- reading ---------------------------------------------------------------- #

    def elements(self) -> list[dict]:
        return [op for op in self.view_config_diff if op.get("name")]

    def element(self, name: str) -> dict:
        for op in self.elements():
            if op["name"] == name:
                return op
        raise KeyError(f"{self.name} has no element {name}")

    def has(self, name: str) -> bool:
        return any(op["name"] == name for op in self.elements())

    def _siblings(self, parent: str) -> list[dict]:
        return [op for op in self.elements() if op.get("parentName") == parent]

    def _next_row(self, parent: str) -> int:
        rows = [op["values"]["layoutConfig"].get("row", 0) for op in self._siblings(parent)
                if isinstance(op.get("values", {}).get("layoutConfig"), dict)]
        return max(rows, default=0) + 1

    def column_type(self, column: str) -> tuple[str, str | None]:
        if not self.entity:
            raise KeyError(f"{self.name} has no PDS data source, so its columns are unknown")
        columns = self.workspace.columns(self.entity)
        if column not in columns:
            raise KeyError(f"{self.entity} has no column {column}; it has: {', '.join(sorted(columns))}")
        return columns[column]

    # -- writing ---------------------------------------------------------------- #

    def add_field(self, column: str, parent: str = DEFAULT_FIELD_PARENT, row: int | None = None,
                  col: int = 1, span: int = 1) -> dict:
        """A bound field of the primary object: the viewConfigDiff insert and the PDS attribute."""
        if self.has(column):
            raise KeyError(f"{self.name} already has an element {column}")
        kind, _ = self.column_type(column)
        if kind not in CONTROL_OF:
            raise ValueError(f"no Freedom UI control for a {kind} column ({column})")
        control, extra = CONTROL_OF[kind]
        op = {
            "operation": "insert",
            "name": column,
            "values": {
                "layoutConfig": {"column": col, "row": row or self._next_row(parent), "colSpan": span, "rowSpan": 1},
                "type": control,
                "label": f"$Resources.Strings.{column}",
                "control": f"${column}",
                "labelPosition": "auto",
                **extra,
            },
            "parentName": parent,
            "propertyName": "items",
            "index": len(self._siblings(parent)),
        }
        self.view_config_diff.append(op)
        self.attributes_w()[column] = {"modelConfig": {"path": f"PDS.{column}"}}
        return op

    def add_grid(self, name: str, entity: str, columns: list[str], parent: str = DEFAULT_GRID_PARENT,
                 rows: int = 6, editable: bool = False) -> dict:
        """A list of another object's records: the grid, its collection attribute and its data source."""
        if self.has(name):
            raise KeyError(f"{self.name} already has an element {name}")
        known = self.workspace.columns(entity)
        missing = [c for c in columns if c not in known]
        if missing:
            raise KeyError(f"{entity} has no column {', '.join(missing)}")
        ds = f"{name}DS"
        captions = self._captions_of(entity)
        op = {
            "operation": "insert",
            "name": name,
            "values": {
                "type": "crt.DataGrid",
                "columns": [{"id": new_uid(), "code": f"{ds}_{c}", "caption": captions.get(c, c),
                             "dataValueType": DVT_CODE.get(known[c][0], 1), "width": 200} for c in columns],
                "items": f"${name}",
                "primaryColumnName": f"{ds}_Id",
                "layoutConfig": {"column": 1, "row": self._next_row(parent), "colSpan": 2, "rowSpan": rows},
                "features": {"editable": {"enable": editable}, "rows": {"selection": {"enable": True, "multiple": True}}},
                "visible": True,
            },
            "parentName": parent,
            "propertyName": "items",
            "index": len(self._siblings(parent)),
        }
        self.view_config_diff.append(op)
        self.attributes_w()[name] = {
            "isCollection": True,
            "modelConfig": {"path": ds, "sortingConfig": {"default": [{"columnName": columns[0], "direction": "asc"}]}},
            "viewModelConfig": {"attributes": {**{f"{ds}_{c}": {"modelConfig": {"path": f"{ds}.{c}"}} for c in columns},
                                               f"{ds}_Id": {"modelConfig": {"path": f"{ds}.Id"}}}},
        }
        self.data_sources_w()[ds] = {
            "type": "crt.EntityDataSource",
            "scope": "viewElement",
            "config": {"entitySchemaName": entity, "attributes": {c: {"path": c} for c in columns}},
        }
        return op

    def remove(self, name: str) -> None:
        """Drop an element and what add_field / add_grid created for it."""
        op = self.element(name)
        self.view_config_diff.remove(op)
        attr = self.attributes_w().pop(name, None)
        if attr and attr.get("isCollection"):
            self.data_sources_w().pop(attr["modelConfig"]["path"], None)

    def _captions_of(self, entity: str) -> dict[str, str]:
        out = {}
        for hit in self.workspace.find(entity, "EntitySchemaManager"):
            res = Resources(hit["dir"].parent.parent / "Resources" / f"{entity}.Entity")
            for key in res.ordered_keys("en-US"):
                if key.startswith("Columns.") and key.endswith(".Caption"):
                    out.setdefault(key[len("Columns."):-len(".Caption")], res.get(key) or "")
        return out

    # -- checks, text ----------------------------------------------------------- #

    def validate(self) -> list[str]:
        problems = []
        seen = set()
        columns = self.workspace.columns(self.entity) if self.entity else {}
        for op in self.elements():
            if op["name"] in seen:
                problems.append(f"element {op['name']} is defined twice")
            seen.add(op["name"])
            control = (op.get("values") or {}).get("control", "")
            if control.startswith("$") and control[1:] not in self.attributes:
                problems.append(f"{op['name']} is bound to {control} but the page has no such attribute")
        for name, attr in self.attributes.items():
            path = (attr.get("modelConfig") or {}).get("path", "")
            if path.startswith("PDS.") and columns and path[4:] not in columns:
                problems.append(f"{WARNING}attribute {name} reads {path}, which {self.entity} does not have")
        return problems

    def describe(self) -> str:
        form = "designer form (viewModelConfig)" if "SCHEMA_VIEW_MODEL_CONFIG" in self.sections else "template form (viewModelConfigDiff)"
        lines = [f"{self.name}: page of {self.entity or '?'}, {form}, {len(self.elements())} element(s)"]
        for op in self.elements():
            v = op.get("values") or {}
            lc = v.get("layoutConfig") or {}
            where = f"{op.get('parentName')}" + (f" r{lc['row']}c{lc['column']}" if "row" in lc else "")
            bound = f" -> {v['control']}" if "control" in v else (f" of {self.data_sources.get(v.get('items', '$')[1:] + 'DS', {}).get('config', {}).get('entitySchemaName')}" if v.get("type") == "crt.DataGrid" else "")
            lines.append(f"    {op['name']:<32} {v.get('type', '?'):<22} {where}{bound}")
        lines.append(f"  attributes: {', '.join(self.attributes) or '-'}")
        lines.append("  data sources: " + ", ".join(f"{k} ({(v.get('config') or {}).get('entitySchemaName')})" for k, v in self.data_sources.items()))
        for p in self.validate():
            lines.append(f"  ! {p}")
        return "\n".join(lines)

    def render_body(self) -> str:
        text = self.body
        fallback = next((s.style() for s in self.sections.values() if s.style()), ("\t\t", "\t"))
        for sec in self.sections.values():
            if not sec.changed:
                continue
            base, step = sec.style() or fallback
            rendered = json.dumps(sec.value, indent=step, ensure_ascii=False).replace("\n", self.body_newline + base)
            marker = f"/**{sec.name}*/"
            text = re.sub(re.escape(marker) + r".*?" + re.escape(marker), lambda m: marker + rendered + marker, text, count=1, flags=re.S)
        return text

    def files(self) -> dict[Path, tuple[str, bool]]:
        out = super().files()
        out[self.body_path] = (self.render_body(), self.body_bom)
        return out
