"""What a process can contain: the metadata key map, the user tasks of 8.2.3 and one ElementKind per designer element.

To support a new element type, add an ElementKind (or a subclass with `extend`) to ELEMENT_KINDS.
The designer constants (BL7 toolbox item, BN2 size, extra keys) were read off 233 designer-made processes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from ..files import DVT_OF, EMPTY_GUID, new_uid

ASSETS = Path(__file__).resolve().parent / "assets"
KEYMAP: dict[str, str] = json.loads((ASSETS / "keymap.json").read_text(encoding="utf-8"))  # obfuscated key -> property name
KEY_OF: dict[str, str] = {v: k for k, v in KEYMAP.items()}
USER_TASKS: dict[str, dict] = json.loads((ASSETS / "user_tasks.json").read_text(encoding="utf-8"))["tasks"]
USER_TASK_BY_UID: dict[str, str] = {t["uid"]: n for n, t in USER_TASKS.items()}

NS = "Terrasoft.Core.Process."
VALUE_SOURCE = {0: "None", 1: "Const", 2: "Mapping", 3: "Expression", 4: "SystemValue", 5: "SystemSetting", 6: "EntityMapping", 7: "SamplingEntityMapping"}
DIRECTION = {0: "In", 1: "Out", 2: "Variable", 3: "Internal"}
DIRECTION_OF = {v: k for k, v in DIRECTION.items()}
FLOW_MANAGER = "0d8351f6-c2f4-4737-bdd9-6fbfe0837fec"
CONDITIONAL_FLOW_MANAGER = "dac675d4-ea84-4e44-9056-38bf918618e9"
LANESET_MANAGER = "11a47caf-a0d5-41fa-a274-a0b11f77447a"
LANE_MANAGER = "abcd74b9-5912-414b-82ac-f1aa4dcd554e"
FLOW_CLASSES = ("ProcessSchemaSequenceFlow", "ProcessSchemaConditionalFlow")
ACTIVITY_CLASSES = ("ProcessSchemaUserTask", "ProcessSchemaFormulaTask", "ProcessSchemaScriptTask")
EVENT_SIZE, GATEWAY_SIZE, TASK_SIZE = "31;31", "55;55", "69;55"


def short_type(item: dict) -> str:
    """ProcessSchemaUserTask for Terrasoft.Core.Process.ProcessSchemaUserTask."""
    return item.get("BL1", "").rsplit(".", 1)[-1]


def event_parameter(proc, el: dict, name: str, type_name: str, value: dict) -> dict:
    """A parameter the designer puts on an event (FC1), e.g. RecordId of a record signal."""
    p = {"BL1": NS + "ProcessSchemaParameter", "UId": new_uid(), "A2": name, "A3": proc.uid, "A4": proc.uid,
         "IL2": el["UId"], "L1": DVT_OF[type_name], "L8": value}
    el["FC1"].append(p)
    return p


class ElementKind:
    """One designer element type.

    cls          short class name (BL1 without the namespace)
    manager      BL7, the designer toolbox item
    size         BN2
    defaults     extra keys the designer writes on a new element, in its order
    message_key  where a message / signal event keeps its message name (set_message)
    """

    def __init__(self, cls: str, manager: str | None, size: str = TASK_SIZE, defaults: dict | None = None, message_key: str | None = None):
        self.cls, self.manager, self.size = cls, manager, size
        self.defaults = defaults or {}
        self.message_key = message_key

    @property
    def is_event(self) -> bool:
        return self.cls.endswith("Event")

    def create(self, proc, name: str, position: str) -> dict:
        el = {"BL1": NS + self.cls, "UId": new_uid(), "A2": name, "A3": proc.uid, "A4": proc.uid, "A5": proc.package_uid,
              "IL2": proc.lane_uid(), "BL3": position, "BL7": self.manager, "BL8": proc.uid, "BN2": self.size, "BO3": True}
        if self.is_event:
            el["FC1"] = []
            if self.cls != "ProcessSchemaTerminateEvent":
                el["ED1"] = False
        else:
            el["BP2"] = []
        if self.cls in ACTIVITY_CLASSES:
            el["CL2"] = "FFFFFFFF"
        el.update(copy.deepcopy(self.defaults))
        self.extend(proc, el)
        return el

    def extend(self, proc, el: dict) -> None:
        """Hook for what a plain dict of defaults cannot express (parameters, values from the element)."""


class MessageEvent(ElementKind):
    """Start / catch / throw message and throw signal: the message name starts as the element name."""

    def extend(self, proc, el):
        el[self.message_key] = el["A2"]
        if "Catch" in self.cls:
            el["IL3"] = True


class StartSignalEvent(ElementKind):
    """Record signal ("added"); the entity comes from ProcessSchema.set_entity (FC2 and the filter)."""

    def extend(self, proc, el):
        event_parameter(proc, el, "RecordId", "Guid", {"GS1": 1, "GS2": ""})


class CatchTimerEvent(ElementKind):
    def extend(self, proc, el):
        event_parameter(proc, el, "StartOffset", "Integer", {"GS1": 1, "GS2": "1", "GS5": proc.uid})


class UserTaskKind(ElementKind):
    """A user task (Read data, Send email ...): its parameters, mappings and captions come from assets/user_tasks.json."""

    def __init__(self, task: str):
        if task not in USER_TASKS:
            raise ValueError(f"unknown user task {task}; one of {sorted(USER_TASKS)}")
        super().__init__("ProcessSchemaUserTask", USER_TASKS[task]["uid"], defaults={"IL3": True, "BO2": True})
        self.task = task

    def extend(self, proc, el):
        el["J6"] = self.manager
        spec = USER_TASKS[self.task]
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
            proc.own_list("BK15").append({"BL1": NS + "ProcessSchemaMapping", "UId": new_uid(), "A2": el["A2"], "A3": proc.uid, "A4": proc.uid,
                                  "GT2": f"[Element:{{{el['UId']}}}].[Parameter:{{{p['UId']}}}]", "GT3": p["UId"],
                                  "GT5": tp["uid"], "GT4": spec["uid"], "GT1": dict(tp["default"])})
            captions = spec["captions"].get(f"Parameters.{tp['name']}.Caption", {})
            for culture in proc.resources.cultures:
                if culture in captions:
                    proc.resources.set(f"BaseElements.{el['A2']}.Parameters.{tp['name']}.Caption", captions[culture], [culture])


ELEMENT_KINDS: dict[str, ElementKind] = {
    "start": ElementKind("ProcessSchemaStartEvent", "53818048-7868-48f6-ada0-0ebaa65af628", EVENT_SIZE),
    "startSignal": StartSignalEvent("ProcessSchemaStartSignalEvent", "1129e72f-0e8c-445a-b2ea-463517e86395", EVENT_SIZE,
                                    {"DZ1": "null", "DZ2": False, "DZ3": True, "DZ5": 1, "DZ12": "[]", "FC2": EMPTY_GUID}, "DZ1"),
    "startTimer": ElementKind("ProcessSchemaStartTimerEvent", "c735ed92-e545-4699-b3c6-f8f57dd8c529", EVENT_SIZE,
                              {"PS1": "0 0 0 * * ? *", "PS3": 2, "PS4": "null", "PS5": "null", "PS6": "UTC"}),
    "startMessage": MessageEvent("ProcessSchemaStartMessageEvent", "02340c80-8e75-4f7a-917b-04125bc07192", EVENT_SIZE, message_key="CJ1"),
    "end": ElementKind("ProcessSchemaEndEvent", "45ceaae2-4e1f-4c0c-86aa-cd4aeb4da913", EVENT_SIZE),
    "terminate": ElementKind("ProcessSchemaTerminateEvent", "1bd93619-0574-454e-bb4e-cf53b9eb9470", EVENT_SIZE),
    "catchTimer": CatchTimerEvent("ProcessSchemaIntermediateCatchTimerEvent", "97d1af3d-ef13-465c-b6d8-5425f78bf000", EVENT_SIZE, {"IL3": True, "BY3": 0}),
    "catchMessage": MessageEvent("ProcessSchemaIntermediateCatchMessageEvent", "3cb9d737-779e-4085-ab4b-db590853e266", EVENT_SIZE, message_key="BZ1"),
    "catchSignal": ElementKind("ProcessSchemaIntermediateCatchSignalEvent", "5ccad23d-fc4b-4ec7-8051-e3a825b698fc", EVENT_SIZE,
                               {"IL3": True, "CA1": "null", "CA2": True, "CA3": False, "CA5": 0, "CA11": "[]"}, "CA1"),
    "throwMessage": MessageEvent("ProcessSchemaIntermediateThrowMessageEvent", "7b8b16fb-d4c6-4e8b-a519-988250ac636f", EVENT_SIZE, message_key="CB1"),
    "throwSignal": MessageEvent("ProcessSchemaIntermediateThrowSignalEvent", "1793bff9-c5fa-49e7-a32d-ca73d270e137", EVENT_SIZE, message_key="CC1"),
    "exclusiveGateway": ElementKind("ProcessSchemaExclusiveGateway", "bd9f7570-6c97-4f16-90e5-663a190c6c7c", GATEWAY_SIZE, {"HH2": []}),
    "inclusiveGateway": ElementKind("ProcessSchemaInclusiveGateway", "ffa4a06a-5747-49d4-96c2-c32a727a3b14", GATEWAY_SIZE),
    "parallelGateway": ElementKind("ProcessSchemaParallelGateway", "e9e1e6de-7066-4eb1-bbb4-5b75b13d4f56", GATEWAY_SIZE, {"CG1": {}}),
    "formula": ElementKind("ProcessSchemaFormulaTask", "d334d28f-b11a-477e-9ff0-0a95fa73d53b"),
    "script": ElementKind("ProcessSchemaScriptTask", "0e490dda-e140-4441-b600-6f5c64d024df", defaults={"CH1": "", "CH2": True}),
    "subProcess": ElementKind("ProcessSchemaSubProcess", "49eafdbb-a89e-4bdf-a29d-7f17b1670a45", defaults={"IL3": True, "BO2": True, "CK2": [], "CK3": []}),
    "eventSubProcess": ElementKind("ProcessSchemaEventSubProcess", "0824af03-1340-47a3-8787-ef542f566992",
                                   defaults={"IL3": True, "BO2": True, "CK2": [], "CK3": [], "CK1": True}),
}
KIND_BY_CLASS: dict[str, ElementKind] = {k.cls: k for k in ELEMENT_KINDS.values()}

# Short names for the designer's user tasks.
TASK_ALIASES = {"readData": "ReadDataUserTask", "changeData": "ChangeDataUserTask", "addData": "AddDataUserTask",
                "deleteData": "DeleteDataUserTask", "performTask": "ActivityUserTask", "sendEmail": "EmailTemplateUserTask",
                "openEditPage": "OpenEditPageUserTask", "preconfiguredPage": "PreconfiguredPageUserTask",
                "approval": "ApprovalUserTask", "changeAccessRights": "ChangeAdminRightsUserTask",
                "callWebService": "WebServiceUserTask", "userQuestion": "UserQuestionUserTask"}


def element_kind(kind: str) -> ElementKind:
    """A key of ELEMENT_KINDS, an alias of TASK_ALIASES, or 'userTask:<TaskSchemaName>'."""
    if kind in TASK_ALIASES:
        return UserTaskKind(TASK_ALIASES[kind])
    if kind.startswith("userTask:"):
        return UserTaskKind(kind.split(":", 1)[1])
    if kind in ELEMENT_KINDS:
        return ELEMENT_KINDS[kind]
    raise ValueError(f"unknown element kind {kind}; one of {sorted(ELEMENT_KINDS) + sorted(TASK_ALIASES)} or userTask:<Name>")
