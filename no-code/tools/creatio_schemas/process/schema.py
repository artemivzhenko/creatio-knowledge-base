"""A business-process schema: Schemas/<Name>/metadata.json (ProcessSchemaManager) and Resources/<Name>.Process/.

Elements, flows and parameters stay the dicts of metadata.json (keys decoded in assets/keymap.json);
the methods keep the cross-references between them (mappings, captions, flow endpoints) in step.
Readers never change the metadata, so an inspected schema saves to the bytes it was read from.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..files import DVT_OF, DATA_VALUE_TYPES, dump_json, is_uid, new_uid, write_text
from ..resources import Resources
from ..schema import Descriptor, Schema
from ..workspace import Package
from .catalog import (CONDITIONAL_FLOW_MANAGER, DIRECTION, DIRECTION_OF, FLOW_CLASSES, FLOW_MANAGER, KEYMAP, KIND_BY_CLASS,
                      LANE_MANAGER, LANESET_MANAGER, NS, USER_TASK_BY_UID, VALUE_SOURCE, element_kind, short_type)
from .expressions import ExpressionCodec

DEFAULT_VERSION = "8.2.3.1351"


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
        if type_name not in DVT_OF:
            raise ValueError(f"unknown type {type_name}; one of {sorted(DVT_OF)}")
        p = {"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": name, "A3": self.uid, "A4": self.uid,
             "A5": self.package_uid, "IL2": self.uid, "L1": DVT_OF[type_name], "L8": {}}
        if default is not None:
            p["L8"] = {"GS1": 1, "GS2": str(default), "GS5": self.uid}
        if type_name == "Lookup" and ref_schema:
            p["L16"] = ref_schema
        if direction != "In":
            p["L12"] = DIRECTION_OF[direction]
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
        p["L8"] = src
        for m in self.mappings:
            if m.get("GT3") == p["UId"]:
                m["GT1"] = dict(src)

    @staticmethod
    def empty_filter(root_schema: str) -> str:
        """The designer's serialised empty filter group of a data element (compact JSON, or the platform picks the legacy reader)."""
        compact = {"separators": (",", ":")}
        edit = json.dumps({"className": "Terrasoft.FilterGroup", "items": {}, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root_schema, "key": ""}, **compact)
        run = json.dumps({"items": {}, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root_schema}, **compact)
        return json.dumps({"className": "Terrasoft.FilterGroup", "serializedFilterEditData": edit, "dataSourceFilters": run}, **compact)

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

    def set_calls(self, element: dict, process: str) -> None:
        """Sub-process: the process to call, by name (from the workspace) or UId."""
        self._require(element, "ProcessSchemaSubProcess", "a sub-process")
        element["CK4"] = self.workspace.uid_of(process, "ProcessSchemaManager")

    def set_message(self, element: dict, message: str) -> None:
        """Message / signal name of a message or signal event."""
        kind = KIND_BY_CLASS.get(short_type(element))
        if not kind or not kind.message_key:
            raise ValueError(f"{element['A2']} carries no message")
        element[kind.message_key] = message

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
        for p in self.params:
            if not self.resources.get(f"Parameters.{p['A2']}.Caption"):
                problems.append(f"parameter {p['A2']} has no en-US caption")
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
            for p in self.element_params(e):
                if p.get("L8"):
                    lines.append(f"        {p['A2']} = {self.describe_value(p['L8'])}")
            cls = short_type(e)
            if cls == "ProcessSchemaScriptTask":
                lines.append(f"        script: {len(e.get('CH1', ''))} chars")
            if cls == "ProcessSchemaSubProcess":
                lines.append(f"        calls schema uid {e.get('CK4')}")
            if cls == "ProcessSchemaStartSignalEvent":
                lines.append(f"        entity uid {e.get('FC2')} signal={e.get('DZ5')} changed columns={e.get('DZ12')}")
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
