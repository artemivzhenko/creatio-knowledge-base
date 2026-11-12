"""A business-rule addon: Schemas/<Target>BusinessRule/ (AddonSchemaManager, AddonName "BusinessRule") and
Resources/<Target>BusinessRule.Addon/ (addon Caption, AddonConfig.Rules.<uid>.Caption).

properties.json binds it to an entity (object rules, every page of the object) or to one Freedom UI
page (ClientUnitSchemaManager); TargetSchemaUId is the base schema's UId.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..files import dump_json, is_uid, new_uid, read_text, write_text
from ..resources import Resources
from ..expressions import Group, describe
from ..schema import WARNING, Descriptor, Schema
from ..workspace import Package, Workspace
from .actions import ACTION_BY_CLASS, ENTITY, PAGE
from .builder import RuleBuilder
from .model import BASE_ADDON_UID, OP_NAMES, RELATIONAL, T_ATTR, T_GROUP, T_RULES, TRIGGER_TYPES, RuleContext, caption_key, condition_of, \
    short_type, walk
from .storage import DEFAULT_VERSION, load_storage

MANAGERS = {ENTITY: "EntitySchemaManager", PAGE: "ClientUnitSchemaManager"}


class RuleSchema(Schema):
    RESOURCE_SUFFIX = "Addon"
    SUFFIX = "BusinessRule"

    def load_metadata(self, text: str) -> None:
        props = json.loads(read_text(self.dir / "properties.json")[0])["Properties"]
        self.target_uid = props["TargetSchemaUId"].lower()
        self.kind = ENTITY if props["TargetSchemaManagerName"] == MANAGERS[ENTITY] else PAGE
        self.storage = load_storage(text, self.newline)

    def render_metadata(self) -> str:
        return self.storage.render()

    # ======================================================================= #
    # Reading
    # ======================================================================= #

    @property
    def replacing(self) -> bool:
        return self.storage.replacing

    @property
    def version(self) -> str:
        return self.storage.version

    @property
    def target(self) -> str | None:
        """The target's name; a base target outside the workspace is still named by the addon (<Target>BusinessRule)."""
        return self.workspace.name_of(self.target_uid) or (self.name[:-len(self.SUFFIX)] if self.name.endswith(self.SUFFIX) else None)

    @property
    def manager(self) -> str:
        return MANAGERS[self.kind]

    @property
    def rules(self) -> list[dict]:
        return self.storage.rules

    def rule(self, key: str) -> dict:
        """By UId, name (BusinessRule_1a2b3c4) or en-US caption."""
        for r in self.rules:
            if key in (r["UId"], r["BR3"]) or self.caption(r) == key:
                return r
        raise KeyError(f"rule {key!r} not found in {self.name}; have {[r['BR3'] for r in self.rules]}")

    def caption(self, rule: dict, culture: str = "en-US") -> str | None:
        return self.resources.get(caption_key(rule["UId"]), culture)

    def base_edits(self) -> list[str]:
        return self.storage.base_edits()

    def context(self) -> RuleContext:
        """What the names in a rule can refer to (from the workspace)."""
        target = self.target or self.target_uid
        if self.kind == ENTITY:
            return RuleContext(self.workspace.columns(target), complete=self.workspace.is_complete(target, self.manager))
        attrs, sources, elements = self.workspace.page_model(target)
        typed = {}
        for name, path in attrs.items():
            ds, _, col = (path or "").partition(".")
            cols = self.workspace.columns(sources[ds]) if ds in sources else {}
            typed[name] = cols.get(col.split(".")[0], (None, None)) if col else (None, None)
        return RuleContext(typed, {p: n for n, p in attrs.items() if p}, elements, bool(attrs) and self.workspace.is_complete(target, self.manager))

    def builder(self) -> RuleBuilder:
        return RuleBuilder(self.kind, self.context(), self.workspace)

    # ======================================================================= #
    # Changing
    # ======================================================================= #

    def _set_rule_caption(self, uid: str, caption: str) -> None:
        self.resources.set(caption_key(uid), caption, ["en-US"])  # the designer writes rule captions to en-US only

    def add(self, spec: dict) -> list[dict]:
        """Add a rule from a spec; returns it followed by the rules its actions generated."""
        built = self.builder().build(spec)
        names = {r["BR3"] for r in self.rules}
        for rule, caption in built:
            if rule["BR3"] in names:
                raise ValueError(f"rule name {rule['BR3']} already exists")
            self.storage.append(rule)
            self._set_rule_caption(rule["UId"], caption)
        return [r for r, _ in built]

    def replace(self, key: str, spec: dict) -> list[dict]:
        """Rebuild a rule from a spec in place, keeping its UId, name, caption and position (what a designer edit does)."""
        old = self.rule(key)
        uid = old["UId"]
        spec = dict(spec, name=spec.get("name") or old["BR3"], caption=spec.get("caption") or self.caption(old))
        (new, caption), *kids = self.builder().build(spec)
        for r in [r for r in self.rules if r.get("BR5") == uid]:  # generated rules are rebuilt with the parent
            self.remove(r["UId"])
        fresh = new["UId"]
        new["UId"] = uid
        old.clear()
        old.update(new)
        self._set_rule_caption(uid, caption)
        for r, cap in kids:
            r["BR5"], r["BR3"] = uid, r["BR3"].replace(fresh, uid)
            self.storage.append(r)
            self._set_rule_caption(r["UId"], cap.replace(fresh, uid))
        return [old] + [r for r, _ in kids]

    def remove(self, key: str) -> list[str]:
        """Remove an own rule with the rules generated for it; returns the removed UIds."""
        rule = self.rule(key)
        doomed = {rule["UId"]} | {r["UId"] for r in self.rules if r.get("BR5") == rule["UId"]}
        self.storage.remove(doomed)
        self.resources.remove(lambda k: any(k.startswith(f"AddonConfig.Rules.{u}.") for u in doomed))
        return sorted(doomed)

    def set_enabled(self, key: str, enabled: bool) -> None:
        """An own rule by name, caption or UId; a base rule (replacing addon) by its UId."""
        try:
            rule = self.rule(key)
        except KeyError:
            if not (self.replacing and is_uid(key)):
                raise
            self.storage.set_base_enabled(key, enabled)
            return
        if enabled:
            rule.pop("BR4", None)
        else:
            rule["BR4"] = False

    def remove_base(self, uid: str) -> None:
        """Replacing addon: delete a rule of the base addon."""
        self.storage.remove_base(uid)

    def set_caption(self, key: str, value: str, cultures: list[str] | None = None) -> None:
        self.resources.set(caption_key(self.rule(key)["UId"]), value, cultures or ["en-US"])

    # ======================================================================= #
    # Checks and reports
    # ======================================================================= #

    def validate(self) -> list[str]:
        problems, ctx = [], self.context()
        v83 = tuple(int(x) for x in self.version.split(".")[:2]) >= (8, 3)
        names = [r["BR3"] for r in self.rules]
        # generated duplicates do occur in designer output; templates add names the workspace cannot see
        problems += [f"{WARNING if n.startswith('Autogenerated_') else ''}duplicate rule name {n}" for n in sorted({n for n in names if names.count(n) > 1})]
        uids = {r["UId"] for r in self.rules}
        known = set(ctx.attributes) | set(ctx.paths.values())
        for r in self.rules:
            label = r["BR3"]
            if r.get("BR5") and r["BR5"] not in uids and not self.replacing:
                problems.append(f"{label}: parent rule {r['BR5']} is missing")
            if not r.get("BR5") and not self.caption(r):
                problems.append(f"{label}: no en-US caption ({caption_key(r['UId'])})")
            for item in walk(r):
                t = item.get("JI0", "")
                if "BCO3" in item and item["BCO3"] in RELATIONAL and not v83:
                    problems.append(f"{label}: comparison {OP_NAMES[item['BCO3']]} needs Creatio 8.3+ (schema says {self.version}); the 8.2 designer shows an empty condition")
                if "BCO3" in item and item["BCO3"] not in OP_NAMES:
                    problems.append(f"{label}: unknown comparison {item['BCO3']}")
                action = ACTION_BY_CLASS.get(t)
                if action and self.kind not in action.kinds:
                    problems.append(f"{label}: {action.name} is not available on a {self.kind} rule")
                if ctx.complete and t == T_ATTR and item.get("BRX1") and item.get("BRX2") in (None, "null"):  # scoped ones belong to a list data source
                    root = item["BRX1"].split(".")[0]
                    if root not in known:
                        problems.append(f"{WARNING}{label}: attribute {root!r} is not on {self.target} (or comes from a parent page)")
                if ctx.complete and "BRA4" in item:
                    pool = ctx.elements if self.kind == PAGE else ctx.attributes
                    for name in item["BRA4"].split(","):
                        if name and name not in pool:
                            problems.append(f"{WARNING}{label}: {'element' if self.kind == PAGE else 'column'} {name!r} is not on {self.target} (or comes from a parent/template)")
        return problems

    def describe_rule(self, r: dict) -> list[str]:
        state = "" if r.get("BR4", True) else "  [disabled]"
        out = [f"{r['BR3']}{state}  {self.caption(r) or ''!r}" + (f"  (generated for {r['BR5']})" if r.get("BR5") else "")]
        for case in r["BR1"]:
            c = case.get("BRC1")
            if c:
                parts = c["BGC2"] if c.get("JI0") == T_GROUP else [c]
                out.append("    when " + describe(Group(tuple(condition_of(p) for p in parts), "or" if c.get("BGC1") == 2 else "and")))
            for a in case["BRC2"]:
                action = ACTION_BY_CLASS.get(a["JI0"])
                out.append(f"    then {action.describe(a) if action else short_type(a['JI0'])}")
        trig = [tr.get("BRT1") or TRIGGER_TYPES.get(tr.get("BRT2"), "?") for tr in r.get("BR2", [])]
        out.append(f"    on {', '.join(trig)}")
        return out

    def describe(self) -> str:
        lines = [f"{self.name}: {self.kind} rules for {self.target or self.target_uid}, {'replacing' if self.replacing else 'own'} addon, "
                 f"created in {self.version}, {len(self.rules)} rule(s)"]
        for r in self.rules:
            lines += self.describe_rule(r)
        edits = self.base_edits()
        if edits:
            lines.append("changes to base rules:")
            lines += [f"    {e}" for e in edits]
        problems = self.validate()
        if problems:
            lines.append("problems:")
            lines += [f"    {p}" for p in problems]
        return "\n".join(lines)

    # ======================================================================= #
    # New addon
    # ======================================================================= #

    @classmethod
    def name_for(cls, package: Path, target: str) -> str:
        """The addon name for a target name; an addon name is returned as given."""
        if target.endswith(cls.SUFFIX) and (Path(package) / "Schemas" / target / "properties.json").is_file():
            return target
        return target + cls.SUFFIX

    @classmethod
    def create(cls, package: Path, target: str, parent_uid: str | None = None, target_uid: str | None = None,
               kind: str | None = None, version: str = DEFAULT_VERSION, caption: str | None = None) -> "RuleSchema":
        """Addon `<target>BusinessRule` in `package`.

        Without parent_uid: an own addon (full JSON). With parent_uid (the UId of the base package's
        `<target>BusinessRule`): a replacing addon in the diff form. The target is resolved from the
        workspace; a target outside it needs target_uid and kind (entity | page).
        """
        package = Path(package)
        name = target + cls.SUFFIX
        sdir = package / "Schemas" / name
        if sdir.exists():
            raise FileExistsError(sdir)
        ws = Workspace(package)
        hits = ws.find(target)
        if hits:
            target_uid = target_uid or hits[0]["base"]
            kind = kind or (ENTITY if hits[0]["manager"] == MANAGERS[ENTITY] else PAGE)
            caption = caption or f"{hits[0]['caption']} (Business rules)"
        if not target_uid or kind not in MANAGERS:
            raise ValueError(f"{target} is not in the workspace; pass target_uid and kind "
                             f"(SQL: select \"UId\" from \"SysSchema\" where \"Name\" = '{target}' and \"ExtendParent\" = false)")
        caption = caption or f"{target} (Business rules)"
        pkg = Package(package)
        created_in, uid = pkg.created_in_uid(), new_uid()
        if parent_uid:
            meta = "\r\n".join([f'= MetaData.Schema.UId "{uid}"', f'= MetaData.Schema.A5 "{created_in}"', f'= MetaData.Schema.B6 "{pkg.uid}"',
                                "+ MetaData.Schema.B7 true", f'= MetaData.Schema.B8 "{version}"', f'= MetaData.Schema.AD5 "{parent_uid}"'])
            write_text(sdir / "metadata.json", meta, False)
            fields = {"UId": uid, "Name": name, "ModifiedOnUtc": "", "Parent": {"UId": parent_uid, "Name": name}, "ExtendParent": True,
                      "ManagerName": "AddonSchemaManager", "Caption": caption, "DependsOn": []}
        else:
            schema = {"ManagerName": "AddonSchemaManager", "UId": uid, "A2": name, "A5": created_in, "B1": [], "B2": [], "B3": [], "B6": pkg.uid, "B8": version,
                      "AD1": target_uid, "AD2": MANAGERS[kind], "AD3": "BusinessRule", "AD5": BASE_ADDON_UID, "AD4": {"JI0": T_RULES, "BRS1": []}}
            write_text(sdir / "metadata.json", dump_json({"MetaData": {"Schema": schema}}), True)
            fields = {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "AddonSchemaManager", "Caption": caption, "DependsOn": []}
        desc = Descriptor.new(sdir / "descriptor.json", fields)
        write_text(desc.path, desc.text, True)
        write_text(sdir / "properties.json", dump_json({"Properties": {"AddonName": "BusinessRule", "CreatedInVersion": version,
                                                                       "TargetSchemaManagerName": MANAGERS[kind], "TargetSchemaUId": target_uid}}), True)
        rs = cls(package, name)
        rs.resources = Resources.empty(rs.resources.folder, ws.cultures_of(target) or ["en-US"])
        rs.resources.set("Caption", caption)
        rs.save()
        return rs
