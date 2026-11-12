"""A business-process schema: Schemas/<Name>/metadata.json (ProcessSchemaManager) and Resources/<Name>.Process/.

Elements, flows and parameters stay the dicts of metadata.json (keys decoded in assets/keymap.json);
the methods keep the cross-references between them (mappings, captions, flow endpoints) in step.
Readers never change the metadata, so an inspected schema saves to the bytes it was read from.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .. import filters
from ..files import ALL_DATA_VALUE_TYPES, DVT_OF, DATA_VALUE_TYPES, EMPTY_GUID, dump_json, is_uid, new_uid, write_text
from ..resources import Resources
from ..schema import Descriptor, Schema
from ..workspace import Package
from .catalog import (CONDITIONAL_FLOW_MANAGER, DIRECTION, DIRECTION_OF, FLOW_CLASSES, FLOW_MANAGER, KEYMAP, KIND_BY_CLASS,
                      LANE_MANAGER, LANESET_MANAGER, NS, USER_TASK_BY_UID, VALUE_SOURCE, element_kind, new_param, short_type)
from .expressions import SUGAR_RE, ExpressionCodec

SIGNAL_MODES = {"added": 1, "modified": 2, "deleted": 4}  # EntitySignal is a bit mask
# Record-signal properties of a start signal (DZ*) and an intermediate catch signal (CA*), by meaning (assets/keymap.json).
SIGNAL_KEYS = {
    "ProcessSchemaStartSignalEvent": {"message": "DZ1", "random": "DZ2", "record": "DZ3", "mode": "DZ5", "has_filter": "DZ8", "has_columns": "DZ11",
                                      "columns": "DZ12", "filter": "DZ13", "entity": "FC2"},
    "ProcessSchemaIntermediateCatchSignalEvent": {"message": "CA1", "random": "CA2", "record": "CA3", "mode": "CA5", "entity": "CA6", "has_columns": "CA7",
                                                  "has_filter": "CA8", "columns": "CA11", "filter": "CA13"},
}

DEFAULT_VERSION = "8.2.3.1351"

# Add data / Modify data: the parameter that holds the column values and the one that names the entity, by task UId.
RECORD_VALUES = {"db6abed1-0c5f-455b-8053-2665378cdb71": ("RecordDefValues", "EntitySchemaId"),
                 "d3021ca7-7450-4678-a117-060171eb2976": ("RecordColumnValues", "EntitySchemaUId")}
VALUES_TYPE = "Terrasoft.Core.Process.LocalizableParameterValuesList, Terrasoft.Core"
PARAMETER_VALUE_TYPE = "Terrasoft.Core.Process.ProcessSchemaParameterValue, Terrasoft.Core"
_COMPACT = {"separators": (",", ":"), "ensure_ascii": False}  # how the designer serialises the list (re-dumps 432 of 432 real ones)
_LOOKUP_CONST_RE = re.compile(r"\[#Lookup\.[^.#]+\.([^.#]+)#\]")
_BOOL_CONST_RE = re.compile(r"\[#BooleanValue\.(True|False)#\]")


def copy_called_params(owner_uid: str, element: dict, called: "ProcessSchema", mappings: list) -> list[dict]:
    """The copies of the called process's parameters a sub-process flow element lacks, appended to its BP2, each with its
    mapping appended to `mappings` (the BK15 of the process or DCM case `owner_uid`), as the designer writes them."""
    params = element.setdefault("BP2", [])
    have = {p["A2"] for p in params}
    added = []
    for cp in called.params:
        if cp["A2"] in have:
            continue
        p = {"BL1": cp["BL1"], "UId": new_uid(), "A2": cp["A2"], "A3": called.uid, "A4": called.uid, "IL2": element["UId"], "L1": cp["L1"],
             "L8": {"GS5": called.uid}}
        p.update({k: cp[k] for k in ("L9", "L12") if k in cp})
        params.append(p)
        added.append(p)
        mappings.append({"BL1": NS + "ProcessSchemaMapping", "UId": new_uid(), "A2": element["A2"], "A3": owner_uid, "A4": owner_uid,
                         "GT2": f"[Element:{{{element['UId']}}}].[Parameter:{{{p['UId']}}}]", "GT3": p["UId"], "GT5": cp["UId"],
                         "GT4": called.uid, "GT1": {"GS5": called.uid}})
    return added


def _without_lcz_text(value):
    """A value list with the text of its localizable items dropped: the designer keeps that text in the mapping only."""
    if isinstance(value, dict):
        return {k: _without_lcz_text(v) for k, v in value.items() if not (k == "value" and value.get("isLczValue"))}
    return [_without_lcz_text(v) for v in value] if isinstance(value, list) else value


def _disagree(value: dict | None, mapping: dict | None) -> bool:
    """Both carry a value and the values differ. One side empty is the designer's own form (localizable texts live in the
    mapping only; a mapping row without a value leaves the parameter's), so it is not reported."""
    a, b = (value or {}).get("GS2"), (mapping or {}).get("GS2")
    if a in (None, "") or b in (None, ""):
        return False
    if str((value or {}).get("GS1")) != str((mapping or {}).get("GS1")):
        return True
    if a == b:
        return False
    try:
        return _without_lcz_text(json.loads(a)) != _without_lcz_text(json.loads(b))
    except (TypeError, ValueError):
        return True


class ProcessSchema(Schema):
    RESOURCE_SUFFIX = "Process"

    def load_metadata(self, text: str) -> None:
        self.meta = json.loads(text)
        self.schema: dict = self.meta["MetaData"]["Schema"]
        if self.schema.get("ManagerName") != "ProcessSchemaManager":
            raise ValueError(f"{self.name} is a {self.schema.get('ManagerName')}, not a process")
        self.expressions = ExpressionCodec(self)

    def render_metadata(self) -> str:
        return dump_json(self.meta, self.newline)

    # ======================================================================= #
    # Reading
    # ======================================================================= #

    @property
    def uid(self) -> str:
        return self.schema["UId"]

    @property
    def package_uid(self) -> str:
        return self.schema.get("B6") or self.schema.get("A5")

    def own_list(self, key: str) -> list:
        """A list of the schema for writing (created when absent); readers use the properties below."""
        return self.schema.setdefault(key, [])

    @property
    def elements(self) -> list[dict]:
        """Nodes and flows (BK4). Every node precedes every flow: the platform resolves flow endpoints while reading."""
        return self.schema.get("BK4", [])

    @property
    def params(self) -> list[dict]:
        return self.schema.get("FJ1", [])

    @property
    def mappings(self) -> list[dict]:
        return self.schema.get("BK15", [])

    @property
    def lanes(self) -> list[dict]:
        return [lane for ls in self.schema.get("BK3", []) for lane in ls.get("BM4", [])]

    def flows(self) -> list[dict]:
        return [e for e in self.elements if short_type(e) in FLOW_CLASSES]

    def nodes(self) -> list[dict]:
        return [e for e in self.elements if short_type(e) not in FLOW_CLASSES]

    def element(self, name: str) -> dict:
        for e in self.elements:
            if e["A2"] == name:
                return e
        raise KeyError(f"no element {name!r}; have {[e['A2'] for e in self.elements]}")

    def element_by_uid(self, uid: str) -> dict | None:
        return next((e for e in self.elements if e["UId"] == uid), None)

    def param(self, name: str) -> dict:
        for p in self.params:
            if p["A2"] == name:
                return p
        raise KeyError(f"no process parameter {name!r}; have {[p['A2'] for p in self.params]}")

    @staticmethod
    def element_params(element: dict) -> list[dict]:
        """Parameters of an element: FC1 on events, BP2 on everything else."""
        return element.get("FC1" if short_type(element).endswith("Event") else "BP2", [])

    def element_param(self, element: dict, name: str) -> dict:
        for p in self.element_params(element):
            if p["A2"] == name:
                return p
        raise KeyError(f"element {element['A2']} has no parameter {name!r}; have {[p['A2'] for p in self.element_params(element)]}")

    def _require(self, element: dict, cls: str, what: str) -> None:
        if short_type(element) != cls:
            raise ValueError(f"{element['A2']} is not {what}")

    # ======================================================================= #
    # Captions
    # ======================================================================= #

    def caption_key(self, target: str) -> str:
        """'Process' | element name | 'El.Param' | 'Parameter:Name' | a raw resource key -> resource key."""
        if target in ("", "Process", "Caption"):
            return "Caption"
        if target.startswith("Parameter:"):
            return f"Parameters.{target.split(':', 1)[1]}.Caption"
        names = {e["A2"] for e in self.elements}
        if "." in target and "." not in target.split(".", 1)[1]:
            el, p = target.split(".")
            if el in names:
                return f"BaseElements.{el}.Parameters.{p}.Caption"
        if target in names:
            return f"BaseElements.{target}.Caption"
        return target

    def set_caption(self, target: str, value: str, cultures: list[str] | None = None) -> str:
        key = self.caption_key(target)
        self.resources.set(key, value, cultures)
        if key == "Caption" and (cultures is None or "en-US" in cultures):
            self.descriptor.set_caption(value)  # descriptor.json carries the en-US caption only
        return key

    # ======================================================================= #
    # Process parameters
    # ======================================================================= #

    def add_param(self, name: str, type_name: str, direction: str = "Variable", caption: str = "", default=None, ref_schema: str | None = None) -> dict:
        if any(p["A2"] == name for p in self.params):
            raise ValueError(f"parameter {name} exists")
        p = new_param(self.uid, self.package_uid, name, type_name, direction, default, ref_schema)
        self.own_list("FJ1").append(p)
        self.resources.set(f"Parameters.{name}.Caption", caption or name)
        return p

    def rename_param(self, old: str, new: str) -> None:
        self.param(old)["A2"] = new
        self.resources.rename_prefix(f"Parameters.{old}", f"Parameters.{new}")

    def remove_param(self, name: str) -> None:
        self.params.remove(self.param(name))
        self.resources.remove_prefix(f"Parameters.{name}")

    # ======================================================================= #
    # Elements
    # ======================================================================= #

    def lane_uid(self) -> str:
        if not self.lanes:
            raise ValueError("process has no lane")
        return self.lanes[0]["UId"]

    @staticmethod
    def _position_after(after: dict | None) -> str:
        if not after or not after.get("BL3"):
            return "200;184"
        x, y = (int(float(v)) for v in after["BL3"].split(";"))
        return f"{x + 150};{y}"

    def add_element(self, kind: str, name: str, caption: str = "", after: str | None = None, before: str | None = None, values: dict | None = None) -> dict:
        """kind: see catalog.element_kind. With `after`, a flow after -> new is added; with `before` as well,
        the existing after -> before flow is re-pointed at the new element and new -> before is added."""
        if any(e["A2"] == name for e in self.elements):
            raise ValueError(f"element {name} exists")
        prev = self.element(after) if after else None
        el = element_kind(kind).create(self, name, self._position_after(prev))
        elements = self.own_list("BK4")
        first_flow = next((i for i, x in enumerate(elements) if short_type(x) in FLOW_CLASSES), len(elements))
        elements.insert(first_flow, el)  # nodes before flows, never appended after them
        self.resources.set(f"BaseElements.{name}.Caption", caption or name, ["en-US"])
        for pname, value in (values or {}).items():
            self.set_value(el, pname, value)
        if prev:
            self._wire(prev, el, before)
        return el

    def _wire(self, prev: dict, el: dict, before: str | None) -> None:
        if not before:
            self.add_flow(prev["A2"], el["A2"])
            return
        nxt = self.element(before)
        existing = next((f for f in self.flows() if f.get("CI1") == prev["UId"] and f.get("CI2") == nxt["UId"]), None)
        if existing:
            existing["CI2"] = el["UId"]
            existing.pop("CI11", None)
            existing.pop("CI12", None)
        else:
            self.add_flow(prev["A2"], el["A2"])
        self.add_flow(el["A2"], nxt["A2"])

    def rename_element(self, old: str, new: str) -> None:
        if any(e["A2"] == new for e in self.elements):
            raise ValueError(f"element {new} exists")
        self.element(old)["A2"] = new
        for m in self.mappings:
            if m.get("A2") == old:
                m["A2"] = new
        for lbl in self.schema.get("Labels", []):
            if lbl.get("A2", "").startswith(old + "_"):
                lbl["A2"] = new + lbl["A2"][len(old):]
        self.resources.rename_prefix(f"BaseElements.{old}", f"BaseElements.{new}")

    def remove_element(self, name: str) -> None:
        """An element or a flow; an element takes its flows, mappings and labels with it."""
        el = self.element(name)
        uid = el["UId"]
        for f in [f for f in self.flows() if uid in (f.get("CI1"), f.get("CI2"))]:
            self.remove_element(f["A2"])
        self.elements.remove(el)
        if "BK15" in self.schema:
            self.schema["BK15"] = [m for m in self.mappings if m.get("A2") != name]
        if "Labels" in self.schema:
            self.schema["Labels"] = [lbl for lbl in self.schema["Labels"] if lbl.get("ParentUId") != uid]
        self.resources.remove_prefix(f"BaseElements.{name}")

    # -- element settings ---------------------------------------------------- #

    def set_value(self, element: dict, pname: str, value, expression: bool = False) -> None:
        """A const value or a {Parameter:X}-style expression on an element parameter; its mapping follows."""
        p = self.element_param(element, pname)
        if expression or self.expressions.has_names(value):
            src = {"GS1": 3, "GS2": self.expressions.encode(str(value)), "GS5": self.uid, "GS8": "false"}
        else:
            src = {"GS1": 1, "GS2": "true" if value is True else "false" if value is False else str(value), "GS5": self.uid}
        self._set_source(p, src)

    def _set_source(self, p: dict, src: dict) -> None:
        p["L8"] = src
        for m in self.mappings:
            if m.get("GT3") == p["UId"]:
                m["GT1"] = dict(src)

    @staticmethod
    def empty_filter(root_schema: str) -> str:
        """The designer's serialised empty filter group of a data element (compact JSON, or the platform picks the legacy reader)."""
        return filters.build(root_schema, [], {})

    def set_entity(self, element: dict, entity: str) -> None:
        """Point a data element (read/add/modify/delete) or a record-signal start at an entity (name from the workspace, or UId)."""
        uid = self.workspace.uid_of(entity, "EntitySchemaManager")
        name = "" if is_uid(entity) else entity
        if short_type(element) == "ProcessSchemaStartSignalEvent":
            element["FC2"] = uid
            element["DZ13"] = self.empty_filter(name)
            return
        names = {p["A2"] for p in self.element_params(element)}
        # Add/Modify/Delete data carry the entity as a lookup value; Read data as the reference schema of ResultEntity.
        for pname in ("EntitySchemaId", "EntitySchemaUId"):
            if pname in names:
                self.set_value(element, pname, uid)
        if "ResultEntity" in names:
            p = self.element_param(element, "ResultEntity")
            p["L9"] = uid
            if name:
                p["L16"] = name
        if "DataSourceFilters" in names:
            self.set_value(element, "DataSourceFilters", self.empty_filter(name))

    def set_filter(self, element: dict, conditions: str) -> None:
        """Read / Modify / Delete data: which records, as `"<Column> = {Parameter:X}; <Column> is not null"` (ANDed; empty =
        every record). A `{Parameter:X}` / `{Element:..}` right side is stored as the designer's meta path; L8 and the
        element's mapping row get the same value."""
        names = {p["A2"] for p in self.element_params(element)}
        if short_type(element) != "ProcessSchemaUserTask" or "DataSourceFilters" not in names:
            raise ValueError(f"{element['A2']} has no record filter: Read data, Modify data and Delete data have one")
        uid = next(((self.element_param(element, n).get("L8") or {}).get("GS2") for n in ("EntitySchemaId", "EntitySchemaUId") if n in names), None)
        uid = uid or (self.element_param(element, "ResultEntity").get("L9") if "ResultEntity" in names else None)
        entity = self.workspace.name_of(uid) if is_uid(uid) else None
        if not entity:
            raise ValueError(f"{element['A2']} has no entity the workspace knows" + ("" if is_uid(uid) else "; set it first (--entity)"))
        text = filters.build(entity, filters.parse_conditions(conditions), self.workspace.columns(entity), self.expressions.encode)
        self._set_source(self.element_param(element, "DataSourceFilters"), {"GS1": 1, "GS2": text, "GS5": self.uid})
        if "IsMatchConditions" in names:  # Modify data applies the filter only with it (the designer sets it on every one)
            self.set_value(element, "IsMatchConditions", True)

    def describe_filter(self, element: dict) -> str | None:
        """`UsrOrder where Id = OrderId`, or None when the element has no filter parameter with a value."""
        p = next((x for x in self.element_params(element) if x["A2"] == "DataSourceFilters"), None)
        raw = ((p or {}).get("L8") or {}).get("GS2")
        return filters.summarize(filters.load(raw)) if raw else None

    def set_calls(self, element: dict, process: str) -> None:
        """Sub-process: the process to call, by name (from the workspace) or UId."""
        self._require(element, "ProcessSchemaSubProcess", "a sub-process")
        element["CK4"] = self.workspace.uid_of(process, "ProcessSchemaManager")

    # -- column values of Add / Modify data ----------------------------------- #

    def _record_target(self, element: dict) -> tuple[dict, str, dict[str, dict]]:
        """(the values parameter, the entity's name or UId, its columns by name) of an Add or Modify data element."""
        from ..data.binding import object_columns  # local: the data toolkit reads entity columns with their parents
        spec = RECORD_VALUES.get(element.get("J6")) if short_type(element) == "ProcessSchemaUserTask" else None
        if not spec:
            raise ValueError(f"{element['A2']} is not an Add data or Modify data element")
        entity_uid = (self.element_param(element, spec[1]).get("L8") or {}).get("GS2")
        if not is_uid(entity_uid):
            raise ValueError(f"{element['A2']} has no entity yet: set it first (--entity)")
        entity = self.workspace.name_of(entity_uid) or entity_uid
        return self.element_param(element, spec[0]), entity, object_columns(self.workspace, entity) if entity != entity_uid else {}

    def record_values(self, element: dict) -> list[tuple[str, str]]:
        """(column, value) of each column an Add / Modify data element writes; expressions in the {Parameter:X} notation."""
        param, _, columns = self._record_target(element)
        names = {c["UId"].lower(): n for n, c in columns.items()}
        raw = (param.get("L8") or {}).get("GS2")
        out = []
        for item in json.loads(raw)["$values"] if raw else []:
            col = item["columnMetaPath"]["value"]
            v = item["value"]
            if v.get("isLczValue"):
                text = "(localizable text)"
            else:
                text = v.get("value", "")
                m = _LOOKUP_CONST_RE.fullmatch(text) or _BOOL_CONST_RE.fullmatch(text)
                text = m.group(1) if m else self.expressions.decode(text)
            out.append((names.get(col.lower(), col), text))
        return out

    def describe_record_values(self, element: dict) -> str:
        """`UsrAmount = 100, UsrStatus = {Parameter:StatusId}`."""
        return ", ".join(f"{c} = {v}" for c, v in self.record_values(element)) or "(no values)"

    def _constant(self, column: str, col: dict, value) -> tuple[str, str]:
        """(value, display) of a constant as the designer writes it: a formula literal of the column's type."""
        kind = ALL_DATA_VALUE_TYPES.get(col.get("S2", ""), "")
        text = "true" if value is True else "false" if value is False else str(value)
        if text == "null":
            return text, text
        if kind == "Boolean":
            word = "True" if text.lower() in ("true", "1", "yes") else "False"
            return f"[#BooleanValue.{word}#]", f"[#Boolean value.{word}#]"
        if kind == "Integer" or kind.startswith(("Float", "Money")):
            float(text)  # ValueError on anything else
            return text, text
        if kind in ("Lookup", "ImageLookup"):
            if not is_uid(text):
                raise ValueError(f"{column} is a lookup: give the record's UId or an expression, not {text!r}")
            ref = (col.get("S4") or EMPTY_GUID).lower()
            return f"[#Lookup.{ref}.{text}#]", f"[#Lookup.{self.workspace.name_of(ref) or ref}.{text}.{text}#]"
        if kind in ("Date", "DateTime", "Time"):
            raise ValueError(f"{column} is a {kind}: give it as an expression (--expr), e.g. a parameter")
        literal = json.dumps(text, ensure_ascii=False)
        return literal, literal

    def set_record_values(self, element: dict, values: dict, expression: bool = False) -> None:
        """The columns an Add / Modify data element writes: {column: constant or {Parameter:X} expression}; other columns are kept."""
        param, entity, columns = self._record_target(element)
        if not columns:
            raise KeyError(f"{element['A2']}: object {entity} is not in the workspace; its columns are unknown")
        missing = [c for c in values if c not in columns]
        if missing:
            raise KeyError(f"{entity} has no column {', '.join(missing)}; columns: {', '.join(sorted(columns))}")
        raw = (param.get("L8") or {}).get("GS2")
        data = json.loads(raw) if raw else {"$type": VALUES_TYPE, "$values": []}
        entity_uid = self.workspace.uid_of(entity, "EntitySchemaManager")
        for column, value in values.items():
            col = columns[column]
            if expression or self.expressions.has_names(value):
                text = str(value)
                v, display = self.expressions.encode(text), SUGAR_RE.sub(lambda m: "[#" + ".".join(x for x in m.groups()[1:] if x) + "#]", text)
            else:
                v, display = self._constant(column, col, value)
            pv = {"$type": PARAMETER_VALUE_TYPE, "Source": 3, "DisplayValue": "", "Value": "", "MetaPath": None, "MetaDataValue": None,
                  "ModifiedInSchemaUId": EMPTY_GUID, "SchemaUId": EMPTY_GUID, "SchemaManagerName": "", "DataValueTypeUId": col["S2"],
                  "ReferenceSchemaUId": (col.get("S4") or EMPTY_GUID).lower(), "ResourceItemName": None}
            old = next((i for i in data["$values"] if i["columnMetaPath"]["value"].lower() == col["UId"].lower()), None)
            item = {"ItemUId": old["ItemUId"] if old else new_uid(), "columnMetaPath": {"value": col["UId"]}, "schemaUId": {"value": entity_uid},
                    "value": {"value": v}, "displayValue": {"value": display}, "parameterValue": {"value": json.dumps(pv, **_COMPACT)}}
            if old:
                data["$values"][data["$values"].index(old)] = item
            else:
                data["$values"].append(item)
        self._set_source(param, {"GS1": 1, "GS2": json.dumps(data, **_COMPACT), "GS5": self.uid})

    # -- parameters of a sub-process --------------------------------------------- #

    def called_process(self, element: dict) -> "ProcessSchema":
        """The process a sub-process element calls, read from the workspace."""
        self._require(element, "ProcessSchemaSubProcess", "a sub-process")
        uid = element.get("CK4")
        hits = self.workspace.find(uid, "ProcessSchemaManager") if uid else []
        if not hits:
            raise KeyError(f"{element['A2']} calls {uid or 'nothing'}, which is not in the workspace" + ("" if uid else "; set it first (--calls)"))
        return ProcessSchema(hits[0]["dir"].parent.parent, hits[0]["name"])

    def map_params(self, element: dict, values: dict, expression: bool = False) -> None:
        """Values for the called process's parameters: {parameter: constant or {Parameter:X} expression}. The element gets a
        copy of every parameter of the called process it lacks, with its mapping, as the designer does on choosing the process."""
        called = self.called_process(element)
        params = element.setdefault("BP2", [])
        if any(p["A2"] == "InputRecordCollection" for p in params):
            raise ValueError(f"{element['A2']} runs once per record of a collection; its per-record parameters are not mapped by this tool")
        unknown = [n for n in values if n not in {p["A2"] for p in called.params}]
        if unknown:
            raise KeyError(f"{called.name} has no parameter {', '.join(unknown)}; parameters: {', '.join(p['A2'] for p in called.params) or '(none)'}")
        copy_called_params(self.uid, element, called, self.own_list("BK15"))
        for name, value in values.items():
            self.set_value(element, name, value, expression)

    def describe_call(self, element: dict) -> str:
        """`calls UsrChild_Process with RecordId = {Parameter:RecordId}`."""
        uid = element.get("CK4")
        given = [f"{p['A2']} = {self.expressions.decode(p['L8']['GS2'])}" for p in element.get("BP2", []) if (p.get("L8") or {}).get("GS2") not in (None, "")]
        return f"calls {self.workspace.name_of(uid) or uid}" + (" with " + ", ".join(given) if given else "")

    def set_message(self, element: dict, message: str) -> None:
        """Message / signal name of a message or signal event. A start or catch signal given a name waits for that named
        signal (a `throwSignal` element or `ProcessEngine.ThrowSignal` in C#) instead of a record change."""
        kind = KIND_BY_CLASS.get(short_type(element))
        if not kind or not kind.message_key:
            raise ValueError(f"{element['A2']} carries no message")
        element[kind.message_key] = message
        keys = SIGNAL_KEYS.get(short_type(element))
        if keys:
            element[keys["random"]] = True
            element[keys["record"]] = False

    def set_signal(self, element: dict, entity: str | None = None, on: str | list[str] | None = None, columns: list[str] | None = None,
                   condition: str | None = None) -> None:
        """A record signal on a start or catch signal element: the entity (name from the workspace, or UId), what fires it
        (`added`, `modified`, `deleted`, several joined by a comma), which columns must change (`modified` only) and the
        conditions the record must meet (`"UsrAmount > 100; UsrStatus is not null"`, ANDed). What is not given is kept."""
        cls = short_type(element)
        keys = SIGNAL_KEYS.get(cls)
        if not keys:
            raise ValueError(f"{element['A2']} is a {cls.replace('ProcessSchema', '')}, not a start or catch signal")
        if entity is None:
            current = element.get(keys["entity"])
            entity = self.workspace.name_of(current) or (current if current and current != EMPTY_GUID else None)
            if not entity:
                raise ValueError(f"{element['A2']} has no entity yet: give --entity")
        uid = self.workspace.uid_of(entity, "EntitySchemaManager")
        name = self.workspace.name_of(uid) or ("" if is_uid(entity) else entity)
        element[keys["entity"]] = uid
        element[keys["record"]] = True
        element[keys["random"]] = False
        element[keys["message"]] = "null"
        if on is not None:
            modes = [m.strip().lower() for m in (on.split(",") if isinstance(on, str) else on) if m.strip()]
            unknown = [m for m in modes if m not in SIGNAL_MODES]
            if unknown or not modes:
                raise ValueError(f"signal mode {', '.join(unknown) or '(none)'}: one or more of {', '.join(SIGNAL_MODES)}")
            element[keys["mode"]] = sum(SIGNAL_MODES[m] for m in dict.fromkeys(modes))
        if columns is not None:
            uids = self.workspace.column_uids(name) if name else {}
            missing = [c for c in columns if c not in uids]
            if missing:
                raise KeyError(f"{name or uid} has no column {', '.join(missing)}" + (f"; columns: {', '.join(sorted(uids))}" if uids else " (entity metadata not in the workspace)"))
            element[keys["columns"]] = json.dumps([uids[c] for c in columns], separators=(",", ":"))
            element[keys["has_columns"]] = bool(columns)
        if condition is not None:
            element[keys["filter"]] = filters.build(name, filters.parse_conditions(condition), self.workspace.columns(name)) if condition.strip() else self.empty_filter(name)
            element[keys["has_filter"]] = bool(condition.strip())
        elif keys["filter"] not in element:
            element[keys["filter"]] = self.empty_filter(name)

    def describe_signal(self, element: dict) -> str:
        """`record signal: UsrOrder modified (columns: UsrAmount); when UsrOrder where UsrAmount > 100`, or `signal 'Name'`."""
        keys = SIGNAL_KEYS.get(short_type(element))
        if not keys:
            return ""
        if not element.get(keys["record"]):
            return f"signal {element.get(keys['message'])!r}"
        uid = element.get(keys["entity"])
        entity = self.workspace.name_of(uid) or uid
        mode = element.get(keys["mode"]) or 0
        text = f"record signal: {entity} " + (" or ".join(n for n, b in SIGNAL_MODES.items() if mode & b) or "?")
        try:
            col_uids = json.loads(element.get(keys["columns"]) or "[]")
        except ValueError:
            col_uids = []
        if col_uids:
            names = {u: n for n, u in self.workspace.column_uids(entity).items()} if entity and not is_uid(entity) else {}
            text += " (columns: " + ", ".join(names.get(u.lower(), u) for u in col_uids) + ")"
        f = filters.load(element.get(keys["filter"]))
        if f and f.get("items"):
            text += "; when " + filters.summarize(f, entity)
        return text

    def set_formula(self, name: str, expression: str, result_param: str) -> None:
        """Formula task: compute `expression` into the process parameter `result_param`."""
        el = self.element(name)
        self._require(el, "ProcessSchemaFormulaTask", "a formula task")
        el["CH1"] = self.expressions.encode(expression)
        el["HS1"] = self.param(result_param)["UId"]

    def get_script(self, name: str) -> str:
        el = self.element(name)
        self._require(el, "ProcessSchemaScriptTask", "a script task")
        return el.get("CH1", "")

    def set_script(self, name: str, body: str) -> None:
        el = self.element(name)
        self._require(el, "ProcessSchemaScriptTask", "a script task")
        el["CH1"] = body.replace("\r\n", "\n")

    # ======================================================================= #
    # Flows
    # ======================================================================= #

    def add_flow(self, src: str, dst: str, condition: str | None = None, name: str | None = None, caption: str | None = None) -> dict:
        a, b = self.element(src), self.element(dst)
        cls = "ProcessSchemaConditionalFlow" if condition else "ProcessSchemaSequenceFlow"
        if not name:
            base = "ConditionalSequenceFlow" if condition else "SequenceFlow"
            n = 1
            while any(e["A2"] == f"{base}{n}" for e in self.elements):
                n += 1
            name = f"{base}{n}"
        f = {"BL1": NS + cls, "UId": new_uid(), "A2": name, "A3": self.uid, "A4": self.uid, "A5": self.package_uid,
             "BL7": CONDITIONAL_FLOW_MANAGER if condition else FLOW_MANAGER, "BL8": self.uid,
             "CI1": a["UId"], "CI2": b["UId"], "CI3": self.expressions.encode(condition) if condition else "null",
             "CI5": "FF939598", "CI6": 1}
        if condition:
            f.update({"CI4": 2, "GV2": "{}", "GV3": []})
        elif short_type(a).endswith("Gateway"):
            f["CI4"] = 1  # the default branch out of a gateway
        self.own_list("BK4").append(f)
        if caption:
            self.resources.set(f"BaseElements.{name}.Caption", caption, ["en-US"])
        return f

    def set_condition(self, flow: str, condition: str) -> None:
        """A condition on a flow; a plain flow is promoted to a conditional one (same UId and endpoints)."""
        f = self.element(flow)
        if short_type(f) == "ProcessSchemaSequenceFlow":
            f.update({"BL1": NS + "ProcessSchemaConditionalFlow", "BL7": CONDITIONAL_FLOW_MANAGER, "CI4": 2, "GV2": "{}", "GV3": []})
            if f["A2"].startswith("SequenceFlow"):
                self.rename_element(f["A2"], "Conditional" + f["A2"])
        f["CI3"] = self.expressions.encode(condition)

    # ======================================================================= #
    # Checks and reports
    # ======================================================================= #

    def validate(self) -> list[str]:
        problems = []
        uids = {e["UId"] for e in self.elements}
        names = [e["A2"] for e in self.elements]
        problems += [f"duplicate element name {n}" for n in sorted({n for n in names if names.count(n) > 1})]
        for f in self.flows():
            for side in ("CI1", "CI2"):
                if f.get(side) not in uids:
                    problems.append(f"flow {f['A2']}: {KEYMAP.get(side, side)} points to a missing element")
        lane_uids = {lane["UId"] for lane in self.lanes}
        for e in self.nodes():
            if e.get("IL2") not in lane_uids:
                problems.append(f"element {e['A2']} is outside every lane")
            # the designer leaves events and gateways uncaptioned; activities carry the text a user reads
            if not short_type(e).endswith(("Event", "Gateway")) and not self.resources.get(f"BaseElements.{e['A2']}.Caption"):
                problems.append(f"element {e['A2']} has no en-US caption")
        pids = {p["UId"] for e in self.elements for p in self.element_params(e)}
        for m in self.mappings:
            if m.get("GT3") not in pids:
                problems.append(f"mapping for {m.get('A2')} targets a missing parameter")
        mapped = {m.get("GT3"): m for m in self.mappings}
        for e in self.elements:
            for p in self.element_params(e):
                m = mapped.get(p.get("UId"))
                if m and _disagree(p.get("L8"), m.get("GT1")):
                    problems.append(f"element {e['A2']} parameter {p['A2']}: value and mapping differ (the platform reads the mapping)")
        for p in self.params:
            if not self.resources.get(f"Parameters.{p['A2']}.Caption"):
                problems.append(f"parameter {p['A2']} has no en-US caption")
        for e in self.nodes():
            if e.get("J6") in RECORD_VALUES and short_type(e) == "ProcessSchemaUserTask":
                try:
                    _, entity, columns = self._record_target(e)
                    # only an object the workspace holds whole: a replacing copy does not list the base object's columns
                    values = self.record_values(e) if columns and self.workspace.is_complete(entity, "EntitySchemaManager") else []
                except (ValueError, KeyError):
                    continue  # no entity yet, or a value list this reader does not know: nothing to check against
                problems += [f"element {e['A2']}: column {c} is not a column of {entity}" for c, _ in values if c not in columns]
        codec = self.expressions  # a reference left as text, or to nothing: "Expression expected" at run time
        for f in self.flows():
            problems += codec.check(f.get("CI3"), f"flow {f['A2']} condition")
        for e in self.nodes():
            if short_type(e) == "ProcessSchemaFormulaTask":
                problems += codec.check(e.get("CH1"), f"element {e['A2']} formula")
            for p in self.element_params(e):
                if (p.get("L8") or {}).get("GS1") == 3:
                    problems += codec.check(p["L8"].get("GS2"), f"element {e['A2']} parameter {p['A2']}")
        for p in self.params:
            if (p.get("L8") or {}).get("GS1") == 3:
                problems += codec.check(p["L8"].get("GS2"), f"parameter {p['A2']}")
        if not self.resources.get("Caption"):
            problems.append("process has no en-US caption")
        return problems

    def describe_value(self, source: dict | None) -> str:
        if not source:
            return "-"
        kind = VALUE_SOURCE.get(source.get("GS1"), str(source.get("GS1")))
        value = source.get("GS2", "")
        if kind == "Expression":
            value = self.expressions.decode(value)
        value = str(value)
        return f"{kind}: {value[:160]}{'...' if len(value) > 160 else ''}"

    def describe(self) -> str:
        r = self.resources
        lines = [f"{self.name}: {r.get('Caption')!r}  uid={self.uid}", f"  cultures: {', '.join(r.cultures)}"]
        if self.params:
            lines.append("  parameters:")
            for p in self.params:
                lines.append(f"    {p['A2']} ({DATA_VALUE_TYPES.get(p.get('L1'), p.get('L1'))}, {DIRECTION.get(p.get('L12', 0))}) "
                             f"caption={r.get(f'Parameters.{p['A2']}.Caption')!r} default={self.describe_value(p.get('L8'))}")
        by_uid = {e["UId"]: e["A2"] for e in self.elements}
        lines.append("  elements:")
        for e in self.nodes():
            t = short_type(e).replace("ProcessSchema", "")
            if t == "UserTask":
                t = USER_TASK_BY_UID.get(e.get("J6"), e.get("J6", "?"))
            lines.append(f"    {e['A2']} [{t}] caption={r.get(f'BaseElements.{e['A2']}.Caption')!r} at {e.get('BL3')}")
            cls = short_type(e)
            values_param = (RECORD_VALUES.get(e.get("J6")) or ("",))[0]
            for p in self.element_params(e) if cls != "ProcessSchemaSubProcess" else []:
                if p["A2"] == values_param and (p.get("L8") or {}).get("GS2"):
                    try:
                        lines.append(f"        values: {self.describe_record_values(e)}")
                        continue
                    except ValueError:
                        pass
                if p["A2"] == "DataSourceFilters" and (p.get("L8") or {}).get("GS2"):
                    lines.append(f"        filter: {self.describe_filter(e)}")
                    continue
                if p.get("L8"):
                    lines.append(f"        {p['A2']} = {self.describe_value(p['L8'])}")
            if cls == "ProcessSchemaScriptTask":
                lines.append(f"        script: {len(e.get('CH1', ''))} chars")
            if cls == "ProcessSchemaSubProcess":
                lines.append(f"        {self.describe_call(e)}")
            if cls in SIGNAL_KEYS:
                lines.append(f"        {self.describe_signal(e)}")
            if cls == "ProcessSchemaStartTimerEvent":
                lines.append(f"        cron {e.get('PS1')!r} tz={e.get('PS6')}")
        lines.append("  flows:")
        for f in self.flows():
            cond = f" if {self.expressions.decode(f['CI3'])}" if f.get("CI3") not in (None, "null", "") else ""
            lines.append(f"    {f['A2']}: {by_uid.get(f.get('CI1'), '?')} -> {by_uid.get(f.get('CI2'), '?')}{cond}")
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # ======================================================================= #
    # New process
    # ======================================================================= #

    @classmethod
    def create(cls, package: Path, name: str, caption: str, cultures: list[str] | None = None, package_uid: str | None = None,
               version: str = DEFAULT_VERSION) -> "ProcessSchema":
        """A designer-equivalent empty process: one lane, start -> terminate. Never re-create an installed
        process under a new UId: the platform replaces the SysSchema row and drops its resources."""
        package = Path(package)
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        pkg_uid = package_uid or Package(package).uid
        uid, laneset_uid, lane_uid = new_uid(), new_uid(), new_uid()
        schema = {
            "ManagerName": "ProcessSchemaManager", "UId": uid, "A2": name, "A5": pkg_uid, "B1": [], "B2": [], "B3": [], "B6": pkg_uid,
            "B8": version, "FJ1": [], "IJ1": True, "BK8": "bb4d6607-026b-4b27-b640-8f5c77c1e89d", "IJ10": True, "BK15": [],
            "BK37": {"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": "NotificationCaption", "A3": uid, "A4": uid,
                     "L1": DVT_OF["Text"], "L8": {"GS1": 3, "GS2": "[#[PropertyValue:Caption]#]"}},
            "BK1": "FFFFFFFF", "BK2": "FFBBBBBB",
            "BK3": [{"BL1": NS + "ProcessSchemaLaneSet", "UId": laneset_uid, "A2": "LaneSet1", "A3": uid, "A4": uid, "A5": pkg_uid,
                     "BL7": LANESET_MANAGER, "BL8": uid, "BM1": 0,
                     "BM4": [{"BL1": NS + "ProcessSchemaLane", "UId": lane_uid, "A2": "Lane1", "A3": uid, "A4": uid, "A5": pkg_uid,
                              "BL7": LANE_MANAGER, "BL8": uid, "IL2": laneset_uid, "CD1": [], "CD2": [], "CD4": laneset_uid, "CD7": []}]}],
            "BK5": [], "BK4": [], "BK9": [], "BK18": "Business Process", "BK29": True, "BK30": True, "BK34": "en-US", "Labels": [], "BK24": [],
        }
        write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "ProcessSchemaManager",
                                                          "Caption": caption, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {
            "CreatedInVersion": version, "IsActiveVersion": "True", "IsCreatedInSvg": "True", "IsInterpretable": "True",
            "IsTracing": "False", "Tag": "Business Process", "UseForceCompile": "False", "Version": "0"}}), True)
        proc = cls(package, name)
        proc.resources = Resources.empty(proc.resources.folder, cultures or ["en-US"])
        proc.resources.set("Caption", caption)
        proc.resources.set("LaneSets.LaneSet1.Caption", "LaneSet 1")
        proc.resources.set("LaneSets.LaneSet1.Lanes.Lane1.Caption", "Lane 1")
        proc.resources.set("NotificationCaption.Caption", "Process instance caption")
        proc.resources.set("NotificationCaption.DisplayValue", "[#Process name#]")
        proc.add_element("start", "StartEvent1", "Start")["BL3"] = "50;184"
        proc.add_element("terminate", "TerminateEvent1", "End", after="StartEvent1")["BL3"] = "600;184"
        proc.save()
        return proc
