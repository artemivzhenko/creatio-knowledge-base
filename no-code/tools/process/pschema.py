"""
Read, inspect and change a Creatio business-process schema stored as package files.

A process lives in <package>/Schemas/<Name>/{descriptor,properties,metadata}.json and
<package>/Resources/<Name>.Process/resource.<culture>.xml. The metadata uses short
obfuscated keys ("BK4", "CI1"...); assets/keymap.json names them. Pure standard library.

Byte format is preserved on save (CRLF, 2-space JSON without BOM, tab-indented XML with
BOM), so an unchanged process round-trips to identical files.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from xml.sax.saxutils import escape, unescape

ASSETS = Path(__file__).resolve().parent / "assets"
KEYMAP: dict[str, str] = json.loads((ASSETS / "keymap.json").read_text(encoding="utf-8"))
KEY_OF: dict[str, str] = {v: k for k, v in KEYMAP.items()}
DATA_VALUE_TYPES: dict[str, str] = json.loads((ASSETS / "data_value_types.json").read_text(encoding="utf-8"))
DVT_OF: dict[str, str] = {v: k for k, v in DATA_VALUE_TYPES.items()}
USER_TASKS: dict[str, dict] = json.loads((ASSETS / "user_tasks.json").read_text(encoding="utf-8"))["tasks"]
USER_TASK_BY_UID: dict[str, str] = {t["uid"]: n for n, t in USER_TASKS.items()}

NS = "Terrasoft.Core.Process."
VALUE_SOURCE = {0: "None", 1: "Const", 2: "Mapping", 3: "Expression", 4: "SystemValue", 5: "SystemSetting", 6: "EntityMapping", 7: "SamplingEntityMapping"}
DIRECTION = {0: "In", 1: "Out", 2: "Variable", 3: "Internal"}
DIRECTION_OF = {v: k for k, v in DIRECTION.items()}

# Designer constants per element type: ManagerItemUId (BL7) and default size (BN2).
# Taken from 233 designer-made processes; a user task's BL7 is its task schema UId.
ELEMENT_TYPES = {
    "start": ("ProcessSchemaStartEvent", "53818048-7868-48f6-ada0-0ebaa65af628", "31;31"),
    "startSignal": ("ProcessSchemaStartSignalEvent", "1129e72f-0e8c-445a-b2ea-463517e86395", "31;31"),
    "startTimer": ("ProcessSchemaStartTimerEvent", "c735ed92-e545-4699-b3c6-f8f57dd8c529", "31;31"),
    "startMessage": ("ProcessSchemaStartMessageEvent", "02340c80-8e75-4f7a-917b-04125bc07192", "31;31"),
    "end": ("ProcessSchemaEndEvent", "45ceaae2-4e1f-4c0c-86aa-cd4aeb4da913", "31;31"),
    "terminate": ("ProcessSchemaTerminateEvent", "1bd93619-0574-454e-bb4e-cf53b9eb9470", "31;31"),
    "catchTimer": ("ProcessSchemaIntermediateCatchTimerEvent", "97d1af3d-ef13-465c-b6d8-5425f78bf000", "31;31"),
    "catchMessage": ("ProcessSchemaIntermediateCatchMessageEvent", "3cb9d737-779e-4085-ab4b-db590853e266", "31;31"),
    "catchSignal": ("ProcessSchemaIntermediateCatchSignalEvent", "5ccad23d-fc4b-4ec7-8051-e3a825b698fc", "31;31"),
    "throwMessage": ("ProcessSchemaIntermediateThrowMessageEvent", "7b8b16fb-d4c6-4e8b-a519-988250ac636f", "31;31"),
    "throwSignal": ("ProcessSchemaIntermediateThrowSignalEvent", "1793bff9-c5fa-49e7-a32d-ca73d270e137", "31;31"),
    "exclusiveGateway": ("ProcessSchemaExclusiveGateway", "bd9f7570-6c97-4f16-90e5-663a190c6c7c", "55;55"),
    "inclusiveGateway": ("ProcessSchemaInclusiveGateway", "ffa4a06a-5747-49d4-96c2-c32a727a3b14", "55;55"),
    "parallelGateway": ("ProcessSchemaParallelGateway", "e9e1e6de-7066-4eb1-bbb4-5b75b13d4f56", "55;55"),
    "formula": ("ProcessSchemaFormulaTask", "d334d28f-b11a-477e-9ff0-0a95fa73d53b", "69;55"),
    "script": ("ProcessSchemaScriptTask", "0e490dda-e140-4441-b600-6f5c64d024df", "69;55"),
    "subProcess": ("ProcessSchemaSubProcess", "49eafdbb-a89e-4bdf-a29d-7f17b1670a45", "69;55"),
    "eventSubProcess": ("ProcessSchemaEventSubProcess", "0824af03-1340-47a3-8787-ef542f566992", "69;55"),
    "userTask": ("ProcessSchemaUserTask", None, "69;55"),
}
# Short aliases for the designer's data elements.
TASK_ALIASES = {"readData": "ReadDataUserTask", "changeData": "ChangeDataUserTask", "addData": "AddDataUserTask",
                "deleteData": "DeleteDataUserTask", "performTask": "ActivityUserTask", "sendEmail": "EmailTemplateUserTask",
                "openEditPage": "OpenEditPageUserTask", "preconfiguredPage": "PreconfiguredPageUserTask",
                "approval": "ApprovalUserTask", "changeAccessRights": "ChangeAdminRightsUserTask",
                "callWebService": "WebServiceUserTask", "userQuestion": "UserQuestionUserTask"}
FLOW_MANAGER = "0d8351f6-c2f4-4737-bdd9-6fbfe0837fec"
CONDITIONAL_FLOW_MANAGER = "dac675d4-ea84-4e44-9056-38bf918618e9"
LANESET_MANAGER = "11a47caf-a0d5-41fa-a274-a0b11f77447a"
LANE_MANAGER = "abcd74b9-5912-414b-82ac-f1aa4dcd554e"

_META_PATH_RE = re.compile(r"\[(Element|Parameter|EntityColumn|IsOwnerSchema|IsSchema):\{?([^\]}]+)\}?\]")
_SUGAR_RE = re.compile(r"\{(Parameter|Element):([A-Za-z0-9_]+)(?:\.Parameter:([A-Za-z0-9_]+))?\}")
_ITEM_RE = re.compile(r'<Item Name="([^"]*)" Value="([^"]*)" />')
_XML_ESCAPE = {'"': "&quot;"}
_XML_UNESCAPE = {"&quot;": '"', "&apos;": "'"}


def _read(path: Path) -> str:
    """Text with its CRLF kept (read_text would normalise them) and the BOM dropped."""
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read().lstrip("﻿")


def new_uid() -> str:
    return str(uuid.uuid4())


def short_type(item: dict) -> str:
    return item.get("BL1", "").rsplit(".", 1)[-1]


# --------------------------------------------------------------------------- #
# Resources
# --------------------------------------------------------------------------- #


class Resources:
    """resource.<culture>.xml files of one schema: {culture: {key: value}}."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.cultures: dict[str, dict[str, str]] = {}
        self.extra: dict[str, str] = {}  # raw text of anything besides the String group
        for path in sorted(folder.glob("resource.*.xml")):
            culture = path.name[len("resource."):-len(".xml")]
            text = _read(path)
            items = {k: unescape(v, _XML_UNESCAPE) for k, v in _ITEM_RE.findall(text)}
            self.cultures[culture] = items
            rest = re.sub(r'<Group Type="String">.*?</Group>\r?\n?', "", text, count=1, flags=re.S)
            rest = re.sub(r'<\?xml[^>]*>\r?\n?|<Resources[^>]*>\r?\n?|</Resources>\s*$', "", rest, flags=re.S)
            self.extra[culture] = rest.strip()

    def get(self, key: str, culture: str = "en-US") -> str | None:
        return self.cultures.get(culture, {}).get(key)

    def set(self, key: str, value: str, cultures: list[str] | None = None) -> None:
        for culture in cultures or list(self.cultures):
            self.cultures.setdefault(culture, {})[key] = value

    def remove(self, predicate) -> int:
        n = 0
        for items in self.cultures.values():
            for k in [k for k in items if predicate(k)]:
                del items[k]
                n += 1
        return n

    def rename_prefix(self, old: str, new: str) -> int:
        n = 0
        for items in self.cultures.values():
            for k in [k for k in items if k == old or k.startswith(old + ".")]:
                items[new + k[len(old):]] = items.pop(k)
                n += 1
        return n

    def missing(self, source: str = "en-US") -> dict[str, list[str]]:
        base = self.cultures.get(source, {})
        return {c: [k for k in base if k not in items] for c, items in self.cultures.items() if c != source}

    def render(self, culture: str) -> str:
        lines = ['﻿<?xml version="1.0" encoding="utf-8"?>', f'<Resources Culture="{culture}">', '\t<Group Type="String">', "\t\t<Items>"]
        for k in sorted(self.cultures[culture]):
            lines.append(f'\t\t\t<Item Name="{escape(k, _XML_ESCAPE)}" Value="{escape(self.cultures[culture][k], _XML_ESCAPE)}" />')
        lines += ["\t\t</Items>", "\t</Group>"]
        if self.extra.get(culture):
            lines.append("\t" + self.extra[culture])
        lines.append("</Resources>")
        return "\r\n".join(lines)

    def save(self, folder: Path | None = None) -> None:
        folder = folder or self.folder
        folder.mkdir(parents=True, exist_ok=True)
        for culture in self.cultures:
            (folder / f"resource.{culture}.xml").write_text(self.render(culture), encoding="utf-8", newline="")


# --------------------------------------------------------------------------- #
# Process schema
# --------------------------------------------------------------------------- #


class Process:
    def __init__(self, package: Path, name: str):
        self.package = Path(package)
        self.name = name
        self.schema_dir = self.package / "Schemas" / name
        self.meta_path = self.schema_dir / "metadata.json"
        if not self.meta_path.is_file():
            raise FileNotFoundError(f"no schema {name} in {self.package}")
        self.meta = json.loads(_read(self.meta_path))
        self.schema: dict = self.meta["MetaData"]["Schema"]
        if self.schema.get("ManagerName") != "ProcessSchemaManager":
            raise ValueError(f"{name} is a {self.schema.get('ManagerName')}, not a process")
        self.descriptor_text = _read(self.schema_dir / "descriptor.json")
        self.resources = Resources(self.package / "Resources" / f"{name}.Process")

    # -- raw access ----------------------------------------------------------- #

    @property
    def uid(self) -> str:
        return self.schema["UId"]

    @property
    def package_uid(self) -> str:
        return self.schema.get("B6") or self.schema.get("A5")

    @property
    def elements(self) -> list[dict]:
        return self.schema.setdefault("BK4", [])

    @property
    def params(self) -> list[dict]:
        return self.schema.setdefault("FJ1", [])

    @property
    def mappings(self) -> list[dict]:
        return self.schema.setdefault("BK15", [])

    @property
    def lanes(self) -> list[dict]:
        return [lane for ls in self.schema.get("BK3", []) for lane in ls.get("BM4", [])]

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

    def element_params(self, element: dict) -> list[dict]:
        return element.setdefault("FC1" if short_type(element).endswith("Event") else "BP2", [])

    def element_param(self, element: dict, name: str) -> dict:
        for p in self.element_params(element):
            if p["A2"] == name:
                return p
        raise KeyError(f"element {element['A2']} has no parameter {name!r}; have {[p['A2'] for p in self.element_params(element)]}")

    def flows(self) -> list[dict]:
        return [e for e in self.elements if short_type(e) in ("ProcessSchemaSequenceFlow", "ProcessSchemaConditionalFlow")]

    def nodes(self) -> list[dict]:
        return [e for e in self.elements if e not in self.flows()]

    # -- decoding --------------------------------------------------------------- #

    def _uid_names(self) -> dict[str, str]:
        names = {e["UId"]: e["A2"] for e in self.elements}
        names.update({p["UId"]: p["A2"] for p in self.params})
        for e in self.elements:
            for p in self.element_params(e):
                names[p["UId"]] = p["A2"]
        names[self.uid] = self.name
        return names

    def decode_expr(self, text: str) -> str:
        """[#[Element:{uid}].[Parameter:{uid}]#] -> {Element:Name.Parameter:Name}; unknown ids are kept."""
        if not isinstance(text, str):
            return text
        names = self._uid_names()

        def repl(m):
            kind, uid = m.group(1), m.group(2)
            if kind in ("IsOwnerSchema", "IsSchema"):
                return ""
            return f"[{kind}:{names.get(uid, uid)}]"
        out = _META_PATH_RE.sub(repl, text)
        return re.sub(r"\[#\.*", "{", out).replace("#]", "}").replace("].[", ".").replace("[", "").replace("]", "")

    def encode_expr(self, text: str) -> str:
        """{Parameter:Name} / {Element:El.Parameter:P} -> designer meta paths; other text is kept."""
        by_name = {p["A2"]: p["UId"] for p in self.params}

        def repl(m):
            kind, name, pname = m.group(1), m.group(2), m.group(3)
            if kind == "Parameter":
                if name not in by_name:
                    raise KeyError(f"no process parameter {name!r}")
                return f"[#[IsOwnerSchema:false].[IsSchema:false].[Parameter:{{{by_name[name]}}}]#]"
            el = self.element(name)
            p = self.element_param(el, pname)
            return f"[#[IsOwnerSchema:false].[IsSchema:false].[Element:{{{el['UId']}}}].[Parameter:{{{p['UId']}}}]#]"
        return _SUGAR_RE.sub(repl, text)

    def describe_value(self, source: dict | None) -> str:
        if not source:
            return "-"
        kind = VALUE_SOURCE.get(source.get("GS1"), str(source.get("GS1")))
        value = source.get("GS2", "")
        if kind == "Expression":
            value = self.decode_expr(value)
        value = str(value)
        return f"{kind}: {value[:160]}{'...' if len(value) > 160 else ''}"

    # -- captions ---------------------------------------------------------------- #

    def caption_key(self, target: str) -> str:
        """'Process' | element name | 'El.Param' | 'Parameter:Name' | raw key -> resource key."""
        if target in ("", "Process", "Caption"):
            return "Caption"
        if target.startswith("Parameter:"):
            return f"Parameters.{target.split(':', 1)[1]}.Caption"
        if "." in target and "." not in target.split(".", 1)[1]:
            el, p = target.split(".")
            if any(e["A2"] == el for e in self.elements):
                return f"BaseElements.{el}.Parameters.{p}.Caption"
        if any(e["A2"] == target for e in self.elements):
            return f"BaseElements.{target}.Caption"
        return target

    def set_caption(self, target: str, value: str, cultures: list[str] | None = None) -> str:
        key = self.caption_key(target)
        self.resources.set(key, value, cultures)
        # descriptor.json carries the en-US caption only
        if key == "Caption" and (cultures is None or "en-US" in cultures):
            self.descriptor_text = re.sub(r'("Caption":\s*")[^"]*(")', lambda m: m.group(1) + json.dumps(value, ensure_ascii=False)[1:-1] + m.group(2), self.descriptor_text, count=1)
        return key

    # -- parameters ---------------------------------------------------------------- #

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
        self.params.append(p)
        self.resources.set(f"Parameters.{name}.Caption", caption or name)
        return p

    def rename_param(self, old: str, new: str) -> None:
        self.param(old)["A2"] = new
        self.resources.rename_prefix(f"Parameters.{old}", f"Parameters.{new}")

    def remove_param(self, name: str) -> None:
        p = self.param(name)
        self.params.remove(p)
        self.resources.remove(lambda k: k == f"Parameters.{name}.Caption" or k.startswith(f"Parameters.{name}."))

    # -- elements -------------------------------------------------------------------- #

    def _lane_uid(self) -> str:
        lanes = self.lanes
        if not lanes:
            raise ValueError("process has no lane")
        return lanes[0]["UId"]

    def _position_after(self, after: dict | None) -> str:
        if not after or not after.get("BL3"):
            return "200;184"
        x, y = (int(float(v)) for v in after["BL3"].split(";"))
        return f"{x + 150};{y}"

    def add_element(self, kind: str, name: str, caption: str = "", after: str | None = None, before: str | None = None, values: dict | None = None) -> dict:
        """kind: a key of ELEMENT_TYPES, an alias of TASK_ALIASES, or 'userTask:<TaskSchemaName>'."""
        if any(e["A2"] == name for e in self.elements):
            raise ValueError(f"element {name} exists")
        task = None
        if kind in TASK_ALIASES:
            task = TASK_ALIASES[kind]
        elif kind.startswith("userTask:"):
            task = kind.split(":", 1)[1]
        if task:
            if task not in USER_TASKS:
                raise ValueError(f"unknown user task {task}; one of {sorted(USER_TASKS)}")
            cls, manager, size = "ProcessSchemaUserTask", USER_TASKS[task]["uid"], "69;55"
        elif kind in ELEMENT_TYPES:
            cls, manager, size = ELEMENT_TYPES[kind]
        else:
            raise ValueError(f"unknown element kind {kind}; one of {sorted(ELEMENT_TYPES) + sorted(TASK_ALIASES)} or userTask:<Name>")
        prev = self.element(after) if after else None
        el = {"BL1": NS + cls, "UId": new_uid(), "A2": name, "A3": self.uid, "A4": self.uid, "A5": self.package_uid,
              "IL2": self._lane_uid(), "BL3": self._position_after(prev), "BL7": manager, "BL8": self.uid, "BN2": size, "BO3": True}
        if cls.endswith("Event"):
            el["FC1"] = []
            if cls != "ProcessSchemaTerminateEvent":
                el["ED1"] = False
        else:
            el["BP2"] = []
        if cls in ("ProcessSchemaUserTask", "ProcessSchemaFormulaTask", "ProcessSchemaScriptTask"):
            el["CL2"] = "FFFFFFFF"
        if cls == "ProcessSchemaScriptTask":
            el["CH1"] = ""
            el["CH2"] = True
        if cls == "ProcessSchemaUserTask":
            el["IL3"] = True
            el["BO2"] = True
            el["J6"] = manager
            self._instantiate_task_params(el, task)
        if cls == "ProcessSchemaExclusiveGateway":
            el["HH2"] = []
        if cls == "ProcessSchemaParallelGateway":
            el["CG1"] = {}
        if cls == "ProcessSchemaStartTimerEvent":
            el.update({"PS1": "0 0 0 * * ? *", "PS3": 2, "PS4": "null", "PS5": "null", "PS6": "UTC"})
        if cls == "ProcessSchemaStartSignalEvent":
            # record signal, "added"; the entity comes from set_entity (FC2 + filters)
            el.update({"DZ1": "null", "DZ2": False, "DZ3": True, "DZ5": 1, "DZ12": "[]", "FC2": "00000000-0000-0000-0000-000000000000"})
            el["FC1"].append({"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": "RecordId", "A3": self.uid, "A4": self.uid,
                              "IL2": el["UId"], "L1": DVT_OF["Guid"], "L8": {"GS1": 1, "GS2": ""}})
        if cls == "ProcessSchemaIntermediateCatchSignalEvent":
            el.update({"IL3": True, "CA1": "null", "CA2": True, "CA3": False, "CA5": 0, "CA11": "[]"})
        if cls in ("ProcessSchemaStartMessageEvent", "ProcessSchemaIntermediateCatchMessageEvent", "ProcessSchemaIntermediateThrowMessageEvent", "ProcessSchemaIntermediateThrowSignalEvent"):
            key = {"ProcessSchemaStartMessageEvent": "CJ1", "ProcessSchemaIntermediateCatchMessageEvent": "BZ1",
                   "ProcessSchemaIntermediateThrowMessageEvent": "CB1", "ProcessSchemaIntermediateThrowSignalEvent": "CC1"}[cls]
            el[key] = name  # the message/signal name defaults to the element name; see set_message
            if "Catch" in cls:
                el["IL3"] = True
        if cls == "ProcessSchemaIntermediateCatchTimerEvent":
            el.update({"IL3": True, "BY3": 0})
            el["FC1"].append({"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": "StartOffset", "A3": self.uid, "A4": self.uid,
                              "IL2": el["UId"], "L1": DVT_OF["Integer"], "L8": {"GS1": 1, "GS2": "1", "GS5": self.uid}})
        if cls in ("ProcessSchemaSubProcess", "ProcessSchemaEventSubProcess"):
            el.update({"IL3": True, "BO2": True, "CK2": [], "CK3": []})
            if cls == "ProcessSchemaEventSubProcess":
                el["CK1"] = True
        # The platform resolves a flow's source/target while reading BK4 in order, so every
        # node must precede every flow: insert before the first flow, never append.
        first_flow = next((i for i, x in enumerate(self.elements) if short_type(x).endswith("Flow")), len(self.elements))
        self.elements.insert(first_flow, el)
        self.resources.set(f"BaseElements.{name}.Caption", caption or name, ["en-US"])
        for pname, value in (values or {}).items():
            self.set_value(el, pname, value)
        if prev:
            self._wire(prev, el, before)
        return el

    def _instantiate_task_params(self, el: dict, task: str) -> None:
        spec = USER_TASKS[task]
        for tp in spec["parameters"]:
            p = {"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": tp["name"], "A3": spec["uid"], "A4": spec["uid"],
                 "IL2": el["UId"], "L1": tp["type"], "L8": dict(tp["default"])}
            if tp.get("refSchemaUId"):
                p["L9"] = tp["refSchemaUId"]
            if tp.get("refSchemaName"):
                p["L16"] = tp["refSchemaName"]
            if tp.get("direction") is not None:
                p["L12"] = tp["direction"]
            el["BP2"].append(p)
            self.mappings.append({"BL1": NS + "ProcessSchemaMapping", "UId": new_uid(), "A2": el["A2"], "A3": self.uid, "A4": self.uid,
                                  "GT2": f"[Element:{{{el['UId']}}}].[Parameter:{{{p['UId']}}}]", "GT3": p["UId"],
                                  "GT5": tp["uid"], "GT4": spec["uid"], "GT1": dict(tp["default"])})
            cap = spec["captions"].get(f"Parameters.{tp['name']}.Caption", {})
            for culture in self.resources.cultures:
                if culture in cap:
                    self.resources.set(f"BaseElements.{el['A2']}.Parameters.{tp['name']}.Caption", cap[culture], [culture])

    def _wire(self, prev: dict, el: dict, before: str | None) -> None:
        """prev -> el; when `before` is given, the existing prev -> before flow is re-pointed at el and el -> before is added."""
        if before:
            nxt = self.element(before)
            existing = next((f for f in self.flows() if f.get("CI1") == prev["UId"] and f.get("CI2") == nxt["UId"]), None)
            if existing:
                existing["CI2"] = el["UId"]
                existing.pop("CI11", None)
                existing.pop("CI12", None)
            else:
                self.add_flow(prev["A2"], el["A2"])
            self.add_flow(el["A2"], nxt["A2"])
        else:
            self.add_flow(prev["A2"], el["A2"])

    def find_entity_uid(self, entity: str) -> str:
        """UId of an entity schema from this package or its sibling packages (workspace layout)."""
        if re.fullmatch(r"[0-9a-fA-F-]{36}", entity):
            return entity.lower()
        roots = [self.package] + [p for p in self.package.parent.iterdir() if p.is_dir() and p != self.package]
        for root in roots:
            desc = root / "Schemas" / entity / "descriptor.json"
            if desc.is_file():
                d = json.loads(_read(desc))["Descriptor"]
                if d.get("ManagerName") == "EntitySchemaManager":
                    return d["UId"].lower()
        raise KeyError(f"entity {entity} not found in {self.package.parent}; pass its UId instead (clio get-entity-schema-properties)")

    @staticmethod
    def empty_filter(root_schema: str) -> str:
        """The designer's serialised empty filter group for a data element."""
        compact = {"separators": (",", ":")}  # the designer writes the nested filter JSON without spaces
        edit = json.dumps({"className": "Terrasoft.FilterGroup", "items": {}, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root_schema, "key": ""}, **compact)
        run = json.dumps({"items": {}, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root_schema}, **compact)
        return json.dumps({"className": "Terrasoft.FilterGroup", "serializedFilterEditData": edit, "dataSourceFilters": run}, **compact)

    def find_schema_uid(self, schema: str, manager: str = "ProcessSchemaManager") -> str:
        if re.fullmatch(r"[0-9a-fA-F-]{36}", schema):
            return schema.lower()
        for root in [self.package] + [p for p in self.package.parent.iterdir() if p.is_dir() and p != self.package]:
            desc = root / "Schemas" / schema / "descriptor.json"
            if desc.is_file():
                d = json.loads(_read(desc))["Descriptor"]
                if d.get("ManagerName") == manager:
                    return d["UId"].lower()
        raise KeyError(f"{manager} schema {schema} not found in {self.package.parent}; pass its UId instead")

    def set_calls(self, element: dict, process: str) -> None:
        """Sub-process element: call another process by name (resolved from the workspace) or UId."""
        if short_type(element) != "ProcessSchemaSubProcess":
            raise ValueError(f"{element['A2']} is not a sub-process")
        element["CK4"] = self.find_schema_uid(process)

    def set_message(self, element: dict, message: str) -> None:
        """Message / signal name of a start-message, catch or throw event."""
        key = {"ProcessSchemaStartMessageEvent": "CJ1", "ProcessSchemaIntermediateCatchMessageEvent": "BZ1",
               "ProcessSchemaIntermediateThrowMessageEvent": "CB1", "ProcessSchemaIntermediateThrowSignalEvent": "CC1",
               "ProcessSchemaIntermediateCatchSignalEvent": "CA1", "ProcessSchemaStartSignalEvent": "DZ1"}.get(short_type(element))
        if not key:
            raise ValueError(f"{element['A2']} carries no message")
        element[key] = message

    def set_entity(self, element: dict, entity: str) -> None:
        """Point a data element (read/add/modify/delete) or a record-signal start at an entity."""
        uid = self.find_entity_uid(entity)
        name = "" if re.fullmatch(r"[0-9a-fA-F-]{36}", entity) else entity
        if short_type(element) == "ProcessSchemaStartSignalEvent":
            element["FC2"] = uid
            element["DZ13"] = self.empty_filter(name)
            return
        names = {p["A2"] for p in self.element_params(element)}
        # Add/Modify/Delete data carry the entity as a lookup value; Read data carries it as
        # the reference schema of its ResultEntity output (ResultEntity.Schema in the task code).
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

    def set_value(self, element: dict, pname: str, value, expression: bool = False) -> None:
        """Set a const value or a {Parameter:X}-style expression on an element parameter and keep its mapping in sync."""
        p = self.element_param(element, pname)
        if expression or (isinstance(value, str) and _SUGAR_RE.search(value)):
            src = {"GS1": 3, "GS2": self.encode_expr(str(value)), "GS5": self.uid, "GS8": "false"}
        else:
            src = {"GS1": 1, "GS2": "true" if value is True else "false" if value is False else str(value), "GS5": self.uid}
        p["L8"] = src
        for m in self.mappings:
            if m.get("GT3") == p["UId"]:
                m["GT1"] = dict(src)

    def rename_element(self, old: str, new: str) -> None:
        if any(e["A2"] == new for e in self.elements):
            raise ValueError(f"element {new} exists")
        el = self.element(old)
        el["A2"] = new
        for m in self.mappings:
            if m.get("A2") == old:
                m["A2"] = new
        for lbl in self.schema.get("Labels", []):
            if lbl.get("A2", "").startswith(old + "_"):
                lbl["A2"] = new + lbl["A2"][len(old):]
        self.resources.rename_prefix(f"BaseElements.{old}", f"BaseElements.{new}")

    def remove_element(self, name: str) -> None:
        el = self.element(name)
        uid = el["UId"]
        for f in [f for f in self.flows() if uid in (f.get("CI1"), f.get("CI2"))]:
            self.remove_element(f["A2"])
        self.elements.remove(el)
        self.schema["BK15"] = [m for m in self.mappings if m.get("A2") != name]
        self.schema["Labels"] = [l for l in self.schema.get("Labels", []) if l.get("ParentUId") != uid]
        self.resources.remove(lambda k: k == f"BaseElements.{name}.Caption" or k.startswith(f"BaseElements.{name}."))

    # -- flows --------------------------------------------------------------------------- #

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
             "CI1": a["UId"], "CI2": b["UId"], "CI3": self.encode_expr(condition) if condition else "null",
             "CI5": "FF939598", "CI6": 1}
        if condition:
            f.update({"CI4": 2, "GV2": "{}", "GV3": []})
        elif short_type(a).endswith("Gateway"):
            f["CI4"] = 1  # the default branch out of a gateway
        self.elements.append(f)
        if caption:
            self.resources.set(f"BaseElements.{name}.Caption", caption, ["en-US"])
        return f

    def set_condition(self, flow: str, condition: str) -> None:
        f = self.element(flow)
        if short_type(f) == "ProcessSchemaSequenceFlow":
            # Promote a plain flow: same UId and endpoints, the designer's conditional-flow type.
            f.update({"BL1": NS + "ProcessSchemaConditionalFlow", "BL7": CONDITIONAL_FLOW_MANAGER, "CI4": 2, "GV2": "{}", "GV3": []})
            if f["A2"].startswith("SequenceFlow"):
                self.rename_element(f["A2"], "Conditional" + f["A2"])
        f["CI3"] = self.encode_expr(condition)

    # -- formula ------------------------------------------------------------------------------- #

    def set_formula(self, name: str, expression: str, result_param: str) -> None:
        """Formula task: compute `expression` into the process parameter `result_param`."""
        el = self.element(name)
        if short_type(el) != "ProcessSchemaFormulaTask":
            raise ValueError(f"{name} is not a formula task")
        el["CH1"] = self.encode_expr(expression)
        el["HS1"] = self.param(result_param)["UId"]

    # -- script ------------------------------------------------------------------------------ #

    def get_script(self, name: str) -> str:
        el = self.element(name)
        if short_type(el) != "ProcessSchemaScriptTask":
            raise ValueError(f"{name} is not a script task")
        return el.get("CH1", "")

    def set_script(self, name: str, body: str) -> None:
        el = self.element(name)
        if short_type(el) != "ProcessSchemaScriptTask":
            raise ValueError(f"{name} is not a script task")
        el["CH1"] = body.replace("\r\n", "\n")

    # -- validation ---------------------------------------------------------------------------- #

    def validate(self) -> list[str]:
        problems = []
        uids = {e["UId"] for e in self.elements}
        names = [e["A2"] for e in self.elements]
        for n in set(names):
            if names.count(n) > 1:
                problems.append(f"duplicate element name {n}")
        for f in self.flows():
            for side in ("CI1", "CI2"):
                if f.get(side) not in uids:
                    problems.append(f"flow {f['A2']}: {KEYMAP.get(side, side)} points to a missing element")
        lane_uids = {l["UId"] for l in self.lanes}
        for e in self.nodes():
            if e.get("IL2") not in lane_uids:
                problems.append(f"element {e['A2']} is outside every lane")
            # The designer leaves events and gateways uncaptioned; activities carry the text a user reads.
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

    # -- report ------------------------------------------------------------------------------------ #

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
            if short_type(e) == "ProcessSchemaScriptTask":
                lines.append(f"        script: {len(e.get('CH1', ''))} chars")
            if short_type(e) == "ProcessSchemaSubProcess":
                lines.append(f"        calls schema uid {e.get('CK4')}")
            if short_type(e) == "ProcessSchemaStartSignalEvent":
                lines.append(f"        entity uid {e.get('FC2')} signal={e.get('DZ5')} changed columns={e.get('DZ12')}")
            if short_type(e) == "ProcessSchemaStartTimerEvent":
                lines.append(f"        cron {e.get('PS1')!r} tz={e.get('PS6')}")
        lines.append("  flows:")
        for f in self.flows():
            cond = f" if {self.decode_expr(f['CI3'])}" if f.get("CI3") not in (None, "null", "") else ""
            lines.append(f"    {f['A2']}: {by_uid.get(f.get('CI1'), '?')} -> {by_uid.get(f.get('CI2'), '?')}{cond}")
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    # -- persistence ------------------------------------------------------------------------------- #

    def render_metadata(self) -> str:
        return json.dumps(self.meta, indent=2, ensure_ascii=False).replace("\n", "\r\n")

    def save(self) -> None:
        self.meta_path.write_text(self.render_metadata(), encoding="utf-8", newline="")
        (self.schema_dir / "descriptor.json").write_text("﻿" + self.descriptor_text, encoding="utf-8", newline="")
        self.resources.save()

    def files(self) -> dict[Path, str]:
        """What save() would write, for diffs and dry runs."""
        out = {self.meta_path: self.render_metadata(), self.schema_dir / "descriptor.json": "﻿" + self.descriptor_text}
        for culture in self.resources.cultures:
            out[self.resources.folder / f"resource.{culture}.xml"] = self.resources.render(culture)
        return out


# --------------------------------------------------------------------------- #
# New process
# --------------------------------------------------------------------------- #


def create_process(package: Path, name: str, caption: str, cultures: list[str] | None = None, package_uid: str | None = None) -> Process:
    """A minimal designer-equivalent process: one lane, start -> terminate."""
    package = Path(package)
    schema_dir = package / "Schemas" / name
    if schema_dir.exists():
        raise FileExistsError(schema_dir)
    descriptor = json.loads((package / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"]
    pkg_uid = package_uid or descriptor["UId"]
    uid, laneset_uid, lane_uid = new_uid(), new_uid(), new_uid()
    schema = {
        "ManagerName": "ProcessSchemaManager", "UId": uid, "A2": name, "A5": pkg_uid, "B1": [], "B2": [], "B3": [], "B6": pkg_uid,
        "B8": "8.2.3.1351", "FJ1": [], "IJ1": True, "BK8": "bb4d6607-026b-4b27-b640-8f5c77c1e89d", "IJ10": True, "BK15": [],
        "BK37": {"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": "NotificationCaption", "A3": uid, "A4": uid,
                 "L1": DVT_OF["Text"], "L8": {"GS1": 3, "GS2": "[#[PropertyValue:Caption]#]"}},
        "BK1": "FFFFFFFF", "BK2": "FFBBBBBB",
        "BK3": [{"BL1": NS + "ProcessSchemaLaneSet", "UId": laneset_uid, "A2": "LaneSet1", "A3": uid, "A4": uid, "A5": pkg_uid,
                 "BL7": LANESET_MANAGER, "BL8": uid, "BM1": 0,
                 "BM4": [{"BL1": NS + "ProcessSchemaLane", "UId": lane_uid, "A2": "Lane1", "A3": uid, "A4": uid, "A5": pkg_uid,
                          "BL7": LANE_MANAGER, "BL8": uid, "IL2": laneset_uid, "CD1": [], "CD2": [], "CD4": laneset_uid, "CD7": []}]}],
        "BK5": [], "BK4": [], "BK9": [], "BK18": "Business Process", "BK29": True, "BK30": True, "BK34": "en-US", "Labels": [], "BK24": [],
    }
    schema_dir.mkdir(parents=True)
    (schema_dir / "metadata.json").write_text(json.dumps({"MetaData": {"Schema": schema}}, indent=2, ensure_ascii=False).replace("\n", "\r\n"), encoding="utf-8", newline="")
    # The platform parses ModifiedOnUtc as a WCF date literal with escaped slashes: "\/Date(ms)\/".
    descriptor_text = json.dumps({"Descriptor": {"UId": uid, "Name": name, "ModifiedOnUtc": f"/Date({int(time.time() * 1000)})/", "ManagerName": "ProcessSchemaManager",
                                                 "Caption": caption, "DependsOn": []}}, indent=2, ensure_ascii=False)
    descriptor_text = re.sub(r'"/Date\((\d+)\)/"', r'"\\/Date(\1)\\/"', descriptor_text).replace("\n", "\r\n")
    (schema_dir / "descriptor.json").write_text("﻿" + descriptor_text, encoding="utf-8", newline="")
    (schema_dir / "properties.json").write_text(
        "﻿" + json.dumps({"Properties": {"CreatedInVersion": "8.2.3.1351", "IsActiveVersion": "True", "IsCreatedInSvg": "True", "IsInterpretable": "True",
                                              "IsTracing": "False", "Tag": "Business Process", "UseForceCompile": "False", "Version": "0"}}, indent=2).replace("\n", "\r\n"), encoding="utf-8", newline="")
    res_dir = package / "Resources" / f"{name}.Process"
    res_dir.mkdir(parents=True)
    for culture in cultures or ["en-US"]:
        (res_dir / f"resource.{culture}.xml").write_text("﻿" + f'<?xml version="1.0" encoding="utf-8"?>\r\n<Resources Culture="{culture}">\r\n\t<Group Type="String">\r\n\t\t<Items>\r\n\t\t</Items>\r\n\t</Group>\r\n</Resources>', encoding="utf-8", newline="")
    proc = Process(package, name)
    proc.resources.set("Caption", caption)
    proc.resources.set("LaneSets.LaneSet1.Caption", "LaneSet 1")
    proc.resources.set("LaneSets.LaneSet1.Lanes.Lane1.Caption", "Lane 1")
    proc.resources.set("NotificationCaption.Caption", "Process instance caption")
    proc.resources.set("NotificationCaption.DisplayValue", "[#Process name#]")
    start = proc.add_element("start", "StartEvent1", "Start")
    start["BL3"] = "50;184"
    end = proc.add_element("terminate", "TerminateEvent1", "End", after="StartEvent1")
    end["BL3"] = "600;184"
    proc.save()
    return proc
