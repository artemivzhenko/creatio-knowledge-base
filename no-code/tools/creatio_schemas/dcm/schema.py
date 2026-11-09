"""A DCM (dynamic case management) schema: Schemas/<Name>/metadata.json (DcmSchemaManager) and Resources/<Name>.Dcm/.

A case runs on one entity and one of its lookup columns (the stage column). Stages carry a lookup
record (StageRecordId), a colour and steps (DcmSchemaElement, each wrapping a sub-process to start
when the record enters the stage); StageConnections say which stage can follow which; Filters
restricts the records the case applies to. Keys follow the process keymap (A2 name, B6 package,
IL2 container stage, CK4 called schema).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..entity.catalog import STOCK_ENTITIES
from ..files import dump_json, is_uid, new_uid, write_text
from ..filters import summarize
from ..resources import Resources
from ..schema import WARNING, Descriptor, Schema
from ..workspace import Package

DEFAULT_VERSION = "8.2.3.1351"
NS = "Terrasoft.Core.DcmProcess."
DCM_PARENT = "51b280eb-d8a3-4932-81b9-ef61a0877aab"  # BK8 of every case: the base DCM schema
DEFAULT_COLOR = "#4D84E2"
LOOKUP_TYPE = "b295071f-7ea9-4e62-8d1a-919bf3732ff2"


class DcmSchema(Schema):
    RESOURCE_SUFFIX = "Dcm"

    def load_metadata(self, text: str) -> None:
        self.meta = json.loads(text)
        self.schema: dict = self.meta["MetaData"]["Schema"]
        if self.schema.get("ManagerName") != "DcmSchemaManager":
            raise ValueError(f"{self.name} is a {self.schema.get('ManagerName')}, not a DCM case")

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

    @property
    def entity_uid(self) -> str | None:
        return self.schema.get("EntitySchemaUId")

    @property
    def entity(self) -> str | None:
        """The case's object, by name when the workspace or the stock list knows the UId."""
        uid = (self.entity_uid or "").lower()
        return self.workspace.name_of(uid) or next((n for n, u in STOCK_ENTITIES.items() if u == uid), None) or self.entity_uid

    @property
    def stage_column(self) -> str | None:
        """The stage column's name, from the entity's own metadata when it is in the workspace; else the UId."""
        uid = (self.schema.get("StageColumnUId") or "").lower()
        for s in self.workspace.find(self.entity_uid or "", "EntitySchemaManager"):
            from ..entity import EntitySchema  # local: entity imports nothing from dcm, but keep the module graph flat
            try:
                for c in EntitySchema(s["dir"].parent.parent, s["name"]).columns():
                    if c.get("UId", "").lower() == uid:
                        return c["A2"]
            except (OSError, ValueError, KeyError):
                continue
        return self.schema.get("StageColumnUId")

    @property
    def enabled(self) -> bool:
        return bool(self.schema.get("Enabled", True))

    @property
    def stages(self) -> list[dict]:
        return self.schema.get("Stages", [])

    def stage(self, key: str) -> dict:
        """A stage by name, caption or UId."""
        k = key.lower()
        for s in self.stages:
            if k in (s["A2"].lower(), s["UId"].lower(), (self.stage_caption(s) or "").lower()):
                return s
        raise KeyError(f"no stage {key!r}; stages: {', '.join(s['A2'] for s in self.stages)}")

    def _res(self, key: str, culture: str) -> str | None:
        """A resource in `culture`, else in the first culture that has it (client packages may lack en-US)."""
        return self.resources.get(key, culture) or next((v for c in self.resources.cultures if (v := self.resources.get(key, c))), None)

    def stage_caption(self, stage: dict, culture: str = "en-US") -> str | None:
        return self._res(f"Stages.{stage['A2']}.Caption", culture)

    def stage_by_record(self, record_id: str | None) -> dict | None:
        return next((s for s in self.stages if (s.get("StageRecordId") or "").lower() == (record_id or "").lower()), None)

    def stage_by_uid(self, uid: str | None) -> dict | None:
        return next((s for s in self.stages if s["UId"].lower() == (uid or "").lower()), None)

    def elements(self, stage: dict | None = None) -> list[tuple[dict, dict]]:
        """(stage, step) pairs, of one stage or of all."""
        return [(s, e) for s in ([stage] if stage else self.stages) for e in s.get("Elements", [])]

    def element(self, key: str) -> tuple[dict, dict]:
        k = key.lower()
        for s, e in self.elements():
            if k in (e["A2"].lower(), e["UId"].lower(), (self.element_caption(s, e) or "").lower()):
                return s, e
        raise KeyError(f"no step {key!r}; steps: {', '.join(e['A2'] for _, e in self.elements())}")

    def element_caption(self, stage: dict, element: dict, culture: str = "en-US") -> str | None:
        return self._res(f"Stages.{stage['A2']}.Elements.{element['A2']}.Caption", culture)

    def calls(self, element: dict) -> str | None:
        """The process a step starts (name when the workspace knows it, else the UId)."""
        flow = element.get("ProcessFlowElement") or {}
        uid = flow.get("CK4")
        return self.workspace.name_of(uid) or uid

    def conditions(self, element: dict) -> list[dict]:
        """[{when, then}] - the step's result conditions that move the record to another stage."""
        raw = element.get("Conditions")
        if not raw:
            return []
        items = json.loads(raw) if isinstance(raw, str) else raw
        out = []
        for c in items:
            then = self.stage_by_record(c.get("nextStageId"))
            formula = c.get("resultFormula") or {}
            out.append({"when": formula.get("displayValue") or formula.get("value") or "", "then": (then or {}).get("A2") or c.get("nextStageId")})
        return out

    @property
    def connections(self) -> list[tuple[str, str]]:
        """Allowed stage moves as (from, to) stage names."""
        out = []
        for c in (self.schema.get("StageConnections") or {}).get("Connections", []):
            src, dst = self.stage_by_uid(c.get("Source")), self.stage_by_uid(c.get("Target"))
            out.append(((src or {}).get("A2") or c.get("Source"), (dst or {}).get("A2") or c.get("Target")))
        return out

    @property
    def filters(self) -> dict | None:
        raw = self.schema.get("Filters")
        if not raw:
            return None
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return {"raw": raw}

    def describe_filter(self) -> str:
        return summarize(self.filters, self.entity)

    def describe(self) -> str:
        r = self.resources
        lines = [f"{self.name}: {r.get('Caption')!r}  uid={self.uid}  case of {self.entity}, stage column {self.stage_column}"
                 + ("" if self.enabled else ", DISABLED"), f"  cultures: {', '.join(r.cultures)}", f"  applies to: {self.describe_filter()}", "  stages:"]
        for s in self.stages:
            parent = self.stage_by_uid(s.get("ParentStageUId"))
            steps = s.get("Elements", [])
            lines.append(f"    {s['A2']} {self.stage_caption(s)!r} {s.get('Color', '')} record={s.get('StageRecordId')}"
                         + (f" alternative of {parent['A2']}" if parent else "") + (f"  ({len(steps)} steps)" if steps else ""))
            for e in steps:
                kind = (e.get("ProcessFlowElement") or {}).get("BL1", "").rsplit(".", 1)[-1].replace("ProcessSchema", "").lower() or "step"
                lines.append(f"        {e['A2']} {self.element_caption(s, e)!r} {kind} {self.calls(e)} [{'required' if e.get('RequiredType') else 'optional'}]")
                for c in self.conditions(e):
                    lines.append(f"            when {c['when']} -> {c['then']}")
        lines += self.describe_moves()
        problems = self.validate()
        if problems:
            lines.append("  problems:")
            lines += [f"    - {p}" for p in problems]
        return "\n".join(lines)

    def describe_moves(self) -> list[str]:
        """Allowed moves per stage, `any` when a stage may go to every other one."""
        names = [s["A2"] for s in self.stages]
        if not self.connections:
            return ["  moves: (no connections: any stage can follow any)"]
        targets = {n: [b for a, b in self.connections if a == n] for n in names}
        if all(set(targets[n]) >= set(names) - {n} for n in names):
            return ["  moves: every stage to every other"]
        lines = ["  moves:"]
        for n in names:
            t = targets[n]
            lines.append(f"    {n} -> " + ("any" if set(t) >= set(names) - {n} else ", ".join(t) if t else "(nowhere)"))
        return lines

    def validate(self) -> list[str]:
        problems = []
        if not self.entity_uid:
            problems.append("no EntitySchemaUId")
        if not self.schema.get("StageColumnUId"):
            problems.append("no StageColumnUId")
        names = [s["A2"] for s in self.stages]
        if len(names) != len(set(names)):
            problems.append("duplicate stage names")
        uids = {s["UId"].lower() for s in self.stages}
        for s in self.stages:
            if not is_uid(s.get("StageRecordId", "")):
                problems.append(f"stage {s['A2']}: StageRecordId is not a UId")
            if s.get("ParentStageUId") and s["ParentStageUId"].lower() not in uids:
                problems.append(f"stage {s['A2']}: parent stage not found")
            if self.stage_caption(s) is None:
                problems.append(f"{WARNING}stage {s['A2']}: no caption")
            for e in s.get("Elements", []):
                if (e.get("IL2") or "").lower() != s["UId"].lower():
                    problems.append(f"step {e['A2']}: container (IL2) is not its stage")
                called = (e.get("ProcessFlowElement") or {}).get("CK4")
                if called and not self.workspace.name_of(called):
                    problems.append(f"{WARNING}step {e['A2']}: called process {called} is not in the workspace")
                for c in self.conditions(e):
                    if is_uid(c["then"]):
                        problems.append(f"step {e['A2']}: condition moves to an unknown stage record {c['then']}")
        for c in (self.schema.get("StageConnections") or {}).get("Connections", []):
            for end in ("Source", "Target"):
                if (c.get(end) or "").lower() not in uids:
                    problems.append(f"connection {end} {c.get(end)} is not a stage")
        return problems

    # ======================================================================= #
    # Changing
    # ======================================================================= #

    def _new_name(self, prefix: str, items: list[dict]) -> str:
        taken = {i["A2"] for i in items}
        n = len(items) + 1
        while f"{prefix}{n}" in taken:
            n += 1
        return f"{prefix}{n}"

    def add_stage(self, caption: str, record_id: str, name: str | None = None, color: str = DEFAULT_COLOR, parent: str | None = None,
                  cultures: list[str] | None = None) -> dict:
        """A stage for the lookup record `record_id` of the stage column; `parent` makes it an alternative of that stage."""
        if not is_uid(record_id):
            raise ValueError("record_id must be the UId of a record of the stage column's lookup")
        if self.stage_by_record(record_id):
            raise ValueError(f"a stage for record {record_id} exists: {self.stage_by_record(record_id)['A2']}")
        name = name or self._new_name("Stage", self.stages)
        if any(s["A2"] == name for s in self.stages):
            raise ValueError(f"stage {name} exists")
        stage = {"BL1": NS + "DcmSchemaStage", "UId": new_uid(), "A2": name, "A3": self.uid, "A4": self.uid, "A5": self.package_uid,
                 "Color": color, "StageRecordId": record_id, "Elements": []}
        if parent:
            stage = {**stage, "ParentStageUId": self.stage(parent)["UId"]}
            # keep the platform's key order: ParentStageUId sits before Color
            stage = {k: stage[k] for k in ("BL1", "UId", "A2", "A3", "A4", "A5", "ParentStageUId", "Color", "StageRecordId", "Elements")}
        self.schema.setdefault("Stages", []).append(stage)
        self.resources.set(f"Stages.{name}.Caption", caption, cultures)
        return stage

    def remove_stage(self, key: str) -> str:
        s = self.stage(key)
        self.stages.remove(s)
        conns = (self.schema.get("StageConnections") or {}).get("Connections", [])
        conns[:] = [c for c in conns if s["UId"].lower() not in ((c.get("Source") or "").lower(), (c.get("Target") or "").lower())]
        for other in self.stages:
            if (other.get("ParentStageUId") or "").lower() == s["UId"].lower():
                other.pop("ParentStageUId")
        self.resources.remove_prefix(f"Stages.{s['A2']}")
        return s["A2"]

    def connect(self, src: str, dst: str, both: bool = True) -> None:
        """Allow moving from `src` to `dst` (and back when `both`)."""
        a, b = self.stage(src), self.stage(dst)
        conns = self.schema.setdefault("StageConnections", {}).setdefault("Connections", [])
        for x, y in ([(a, b), (b, a)] if both else [(a, b)]):
            if not any(c.get("Source") == x["UId"] and c.get("Target") == y["UId"] for c in conns):
                conns.append({"Source": x["UId"], "Target": y["UId"]})

    def disconnect(self, src: str, dst: str, both: bool = True) -> int:
        a, b = self.stage(src), self.stage(dst)
        conns = (self.schema.get("StageConnections") or {}).get("Connections", [])
        pairs = {(a["UId"], b["UId"])} | ({(b["UId"], a["UId"])} if both else set())
        before = len(conns)
        conns[:] = [c for c in conns if (c.get("Source"), c.get("Target")) not in pairs]
        return before - len(conns)

    def set_caption(self, target: str, value: str, cultures: list[str] | None = None) -> str:
        """`Caption` of the case, or a stage's caption by stage name."""
        key = "Caption" if target == "Caption" else f"Stages.{self.stage(target)['A2']}.Caption"
        if key == "Caption":
            self.descriptor.set_caption(value)
        self.resources.set(key, value, cultures)
        return key

    def set_enabled(self, on: bool) -> None:
        self.schema["Enabled"] = bool(on)

    def set_filter(self, filter_json: str | dict | None) -> None:
        """The case filter as the designer stores it (a Terrasoft.FilterGroup JSON); None removes it."""
        if filter_json is None:
            self.schema.pop("Filters", None)
        else:
            self.schema["Filters"] = filter_json if isinstance(filter_json, str) else json.dumps(filter_json, ensure_ascii=False)

    # ======================================================================= #
    # New case
    # ======================================================================= #

    @classmethod
    def create(cls, package: Path, name: str, caption: str, entity: str, stage_column: str, stages: list[tuple[str, str]] | None = None,
               cultures: list[str] | None = None, version: str = DEFAULT_VERSION) -> "DcmSchema":
        """An empty case on `entity` driven by its lookup column `stage_column`; `stages` are (caption, record UId) pairs,
        connected in a chain. The entity must be in the workspace: the column UId is read from its metadata."""
        from ..entity import EntitySchema

        package = Path(package)
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        pkg = Package(package)
        from ..workspace import Workspace
        ws = Workspace(package)
        hits = ws.find(entity, "EntitySchemaManager")
        if not hits:
            raise KeyError(f"entity {entity} is not in the workspace")
        ent = EntitySchema(hits[0]["dir"].parent.parent, hits[0]["name"])
        col = ent.column(stage_column)
        if (col.get("S2") or "") != LOOKUP_TYPE:
            raise ValueError(f"{stage_column} is not a lookup column")
        uid = new_uid()
        schema = {
            "ManagerName": "DcmSchemaManager", "UId": uid, "A2": name, "A5": pkg.uid, "B1": [], "B2": [], "B3": [], "B6": pkg.uid, "B8": version,
            "FJ1": [], "IJ1": True, "BK8": DCM_PARENT, "IJ10": True, "EntitySchemaUId": hits[0]["base"], "BK15": [],
            "BK37": {"BL1": "Terrasoft.Core.Process.ProcessSchemaParameter", "UId": new_uid(), "A2": "NotificationCaption", "A3": uid, "A4": uid,
                     "L1": "8b3f29bb-ea14-4ce5-a5c5-293a929b6ba2", "L8": {"GS1": 3, "GS2": "[#[PropertyValue:Caption]#]"}},
            "Stages": [], "Transitions": [], "StageConnections": {"Connections": []}, "StageColumnUId": col["UId"], "SystemElements": [],
        }
        write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), False)
        desc = Descriptor.new(sdir / "descriptor.json", {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "DcmSchemaManager",
                                                          "Caption": caption, "DependsOn": []})
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {
            "CreatedInVersion": version, "Enabled": "True", "EntitySchemaUId": hits[0]["base"], "IsActiveVersion": "True", "IsTracing": "False",
            "StageColumnUId": col["UId"], "Version": "0"}}), True)
        case = cls(package, name)
        case.resources = Resources.empty(case.resources.folder, cultures or ["en-US"])
        case.resources.set("Caption", caption)
        case.resources.set("NotificationCaption.Caption", "Process instance caption")
        case.resources.set("NotificationCaption.DisplayValue", "[#Process name#]")
        previous = None
        for stage_caption, record in stages or []:
            s = case.add_stage(stage_caption, record)
            if previous:
                case.connect(previous["A2"], s["A2"])
            previous = s
        case.save()
        return case
