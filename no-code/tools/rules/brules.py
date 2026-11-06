"""
Creatio business rules (object level and Freedom UI page level) as package files.

A rule set is an addon schema `<Target>BusinessRule` (AddonSchemaManager, AddonName
"BusinessRule") bound to an entity schema or a Freedom UI page (ClientUnitSchemaManager):

    Schemas/<Target>BusinessRule/{descriptor,metadata,properties}.json
    Resources/<Target>BusinessRule.Addon/resource.<culture>.xml   (Caption, AddonConfig.Rules.<uid>.Caption)

Two storage forms, both read and written byte-for-byte as the platform exports them:
- own addon (target created in this package, or a base target without rules): metadata.json is
  full JSON, rules in MetaData.Schema.AD4.BRS1;
- replacing addon (target's addon lives in a base package): metadata.json is the line diff
  `= path value` / `+ path value` / `- path` / `~ path [order]`; own rules are
  `+ MetaData.Schema.AD4.BRS1 {rule}`, edits of base rules address them by UId.

Pure standard library. Keys are the obfuscated ones of Terrasoft.Core.BusinessRules (8.2.3 = 8.3.2,
except the relational comparisons 5-8 that only 8.3+ has).
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "process"))
from pschema import Resources, new_uid  # noqa: E402  same resource format as processes

NS = "Terrasoft.Core.BusinessRules."
M = NS + "Models."
T_RULES, T_RULE, T_CASE, T_TRIGGER = NS + "BusinessRules", NS + "BusinessRule", M + "BusinessRuleCase", M + "Trigger"
T_GROUP, T_COND = M + "Conditions.BusinessRuleGroupCondition", M + "Conditions.BusinessRuleCondition"
X = M + "Expressions."
T_ATTR, T_VALUE, T_EMPTY, T_SYS, T_SETTING = X + "BusinessRuleAttributeExpression", X + "BusinessRuleValueExpression", X + "BusinessRuleEmptyValueExpression", X + "BusinessRuleSysValueExpression", X + "BusinessRuleSysSettingExpression"
T_SET_ITEM, T_FILTER_EXPR = X + "BusinessRuleSetValueItem", X + "BusinessRuleFilterLookupExpression"
A = M + "Actions.BusinessRuleAction"
PROPERTY_ACTIONS = {  # spec type -> (class, designer caption prefix)
    "required": (A + "RequiredElement", "Make elements required"), "optional": (A + "OptionalElement", "Make elements optional"),
    "readonly": (A + "ReadonlyElement", "Make elements read-only"), "editable": (A + "EditableElement", "Make elements editable"),
    "show": (A + "ShowElement", "Show elements"), "hide": (A + "HideElement", "Hide elements"),
}
T_SET_VALUES, T_FILTER_LOOKUP, T_SET_FILTER = A + "SetValues", A + "FilterLookup", A + "SetFilter"
PAGE_ONLY = {"show", "hide"}
ENTITY_ONLY = {"set", "filter-lookup", "static-filter"}
OPS = {"empty": 0, "filled": 1, "equal": 2, "not-equal": 3, "less": 5, "less-or-equal": 6, "greater": 7, "greater-or-equal": 8, "contain": 11, "not-contain": 12}
OP_NAMES = {v: k for k, v in OPS.items()}
UNARY = {0, 1}
RELATIONAL = {5, 6, 7, 8}  # BusinessRuleExpressionComparisonType has them only from 8.3
LOGIC = {"and": 1, "or": 2}  # Terrasoft.Common.LogicalOperation: None, And, Or
DATA_LOADED = 2  # BusinessRuleTriggerType: ChangeAttributeValue, ChangeAttributeProperty, DataLoaded, ContextReady
EMPTY_GUID = "00000000-0000-0000-0000-000000000000"
SYS_VALUE_TYPES = {"CurrentUser": "Lookup", "CurrentUserContact": "Lookup", "CurrentUserAccount": "Lookup", "CurrentDate": "Date",
                   "CurrentDateTime": "DateTime", "CurrentTime": "Time", "CurrentUserRoles": "ObjectList"}
BASE_COLUMNS = {"Id": ("Guid", None), "CreatedOn": ("DateTime", None), "CreatedBy": ("Lookup", "Contact"), "ModifiedOn": ("DateTime", None),
                "ModifiedBy": ("Lookup", "Contact"), "ProcessListeners": ("Integer", None)}
DVT = json.loads((Path(__file__).resolve().parent.parent / "process" / "assets" / "data_value_types.json").read_text(encoding="utf-8"))
_OP_RE = re.compile(r"^([=+\-~]) (MetaData\.Schema\S*)(?: (.*))?$")
_RULE_PATH = "MetaData.Schema.AD4.BRS1"
_GUID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


def _read_raw(path: Path) -> tuple[str, bool]:
    with open(path, encoding="utf-8", newline="") as fh:
        text = fh.read()
    return (text[1:], True) if text.startswith("﻿") else (text, False)


def _write(path: Path, text: str, bom: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(("﻿" if bom else "") + text, encoding="utf-8", newline="")


def _dump(obj, nl: str = "\r\n") -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False).replace("\n", nl)


def _short(type_name: str) -> str:
    return type_name.rsplit(".", 1)[-1].replace("BusinessRule", "")


def rule_short_name(uid: str) -> str:
    return "BusinessRule_" + uid.replace("-", "")[:7]


# --------------------------------------------------------------------------- #
# Workspace lookups: schemas by UId/name, entity columns, page attributes and elements
# --------------------------------------------------------------------------- #


class Workspace:
    """Every schema descriptor under the packages folder that holds `package`."""

    def __init__(self, package: Path):
        self.root = package.parent
        self.schemas: list[dict] = []
        for desc in self.root.glob("*/Schemas/*/descriptor.json"):
            try:
                d = json.loads(_read_raw(desc)[0])["Descriptor"]
            except (ValueError, KeyError):
                continue
            self.schemas.append({"name": d["Name"], "uid": d["UId"].lower(), "manager": d.get("ManagerName"), "dir": desc.parent,
                                 "base": (d.get("Parent") or {}).get("UId", d["UId"]).lower() if d.get("ExtendParent") else d["UId"].lower(),
                                 "caption": d.get("Caption", d["Name"])})

    def find(self, name_or_uid: str, manager: str | None = None) -> list[dict]:
        key = name_or_uid.lower()
        return [s for s in self.schemas if (s["name"].lower() == key or s["uid"] == key or s["base"] == key) and (manager is None or s["manager"] == manager)]

    def name_of(self, uid: str | None) -> str | None:
        hits = self.find(uid) if uid else []
        return hits[0]["name"] if hits else None

    def columns(self, entity: str) -> dict[str, tuple[str, str | None]]:
        """name -> (data value type name, reference schema name) from every copy of the entity in the workspace."""
        out = dict(BASE_COLUMNS)
        for s in self.find(entity, "EntitySchemaManager"):
            text = _read_raw(s["dir"] / "metadata.json")[0]
            if text.startswith("{"):
                cols = json.loads(text)["MetaData"]["Schema"].get("D2", [])
            else:
                cols = [json.loads(v) for op, path, v in _diff_ops(text) if op in "+=" and path == "MetaData.Schema.D2" and v.startswith("{")]
            for c in cols:
                out[c["A2"]] = (DVT.get(c.get("S2", ""), c.get("S2")), self.name_of(c.get("S4")))
        return out

    def page_model(self, page: str) -> tuple[dict, dict, set]:
        """(attributes {name: "DS.Column"}, data sources {DS: entity}, element names) of every copy of the page."""
        attrs, sources, elements = {}, {}, set()
        for s in self.find(page, "ClientUnitSchemaManager"):
            for js in s["dir"].glob("*.js"):
                text = _read_raw(js)[0]
                for marker, value in re.findall(r"/\*\*(SCHEMA_[A-Z_]+)\*/(.*?)/\*\*\1\*/", text, re.S):
                    try:
                        data = json.loads(value)
                    except ValueError:
                        continue
                    if marker == "SCHEMA_VIEW_CONFIG_DIFF":
                        elements |= {i["name"] for i in data if isinstance(i, dict) and i.get("name")}
                    elif marker in ("SCHEMA_VIEW_MODEL_CONFIG", "SCHEMA_VIEW_MODEL_CONFIG_DIFF"):
                        blocks = [data.get("attributes", {})] if isinstance(data, dict) else [i.get("values", {}) for i in data if i.get("path") == ["attributes"]]
                        for block in blocks:
                            for name, cfg in block.items():
                                attrs[name] = ((cfg or {}).get("modelConfig") or {}).get("path")
                    elif marker in ("SCHEMA_MODEL_CONFIG", "SCHEMA_MODEL_CONFIG_DIFF"):
                        blocks = [data] if isinstance(data, dict) else [i.get("values", {}) for i in data if i.get("operation") in ("merge", "insert") and i.get("path", []) in ([], ["dataSources"])]
                        for block in blocks:
                            ds = block.get("dataSources", block) if isinstance(block, dict) else {}
                            for k, v in ds.items():
                                if isinstance(v, dict) and (v.get("config") or {}).get("entitySchemaName"):
                                    sources[k] = v["config"]["entitySchemaName"]
        return attrs, sources, elements


def _diff_ops(text: str) -> list[tuple[str, str, str]]:
    ops = []
    for line in text.split("\r\n"):
        m = _OP_RE.match(line)
        if m:
            ops.append([m.group(1), m.group(2), [m.group(3) or ""]])
        elif ops:
            ops[-1][2].append(line)
    return [(op, path, "\r\n".join(v)) for op, path, v in ops]


# --------------------------------------------------------------------------- #
# Rule schema
# --------------------------------------------------------------------------- #


class RuleSchema:
    def __init__(self, package: Path, name: str):
        self.package, self.name = Path(package), name
        self.dir = self.package / "Schemas" / name
        props = json.loads(_read_raw(self.dir / "properties.json")[0])["Properties"]
        self.properties_text = _read_raw(self.dir / "properties.json")[0]
        self.target_uid = props["TargetSchemaUId"].lower()
        self.kind = "entity" if props["TargetSchemaManagerName"] == "EntitySchemaManager" else "page"
        self.descriptor_text = _read_raw(self.dir / "descriptor.json")[0]
        text, self.meta_bom = _read_raw(self.dir / "metadata.json")
        self.replacing = not text.lstrip().startswith("{")
        self.nl = "\r\n" if "\r\n" in text or not text else "\n"  # a git checkout may have normalised them
        if self.replacing:
            self.ops = []  # [op, path, raw value, parsed rule or None, snapshot]
            for op, path, value in _diff_ops(text.replace("\r\n", "\n").replace("\n", "\r\n")):
                rule = json.loads(value) if op == "+" and path == _RULE_PATH else None
                self.ops.append([op, path, value, rule, _dump(rule) if rule else None])
            self.version = next((json.loads(v) for op, p, v, *_ in self.ops if p == "MetaData.Schema.B8"), "8.2.3.1351")
        else:
            self.meta = json.loads(text)
            schema = self.meta["MetaData"]["Schema"]
            schema.setdefault("AD4", {"JI0": T_RULES, "BRS1": []}).setdefault("BRS1", [])
            self.version = schema.get("B8", "8.2.3.1351")
        self.resources = Resources(self.package / "Resources" / f"{name}.Addon")
        self.ws = Workspace(self.package)
        # a base target outside the workspace is still named by the addon: <Target>BusinessRule
        self.target = self.ws.name_of(self.target_uid) or (name[:-len("BusinessRule")] if name.endswith("BusinessRule") else None)

    # ------------------------------------------------------------------ read
    @property
    def rules(self) -> list[dict]:
        if self.replacing:
            return [o[3] for o in self.ops if o[3] is not None]
        return self.meta["MetaData"]["Schema"]["AD4"]["BRS1"]

    def rule(self, key: str) -> dict:
        for r in self.rules:
            if key in (r["UId"], r["BR3"]) or self.caption(r) == key:
                return r
        raise KeyError(f"rule {key!r} not found in {self.name}; have {[r['BR3'] for r in self.rules]}")

    def caption(self, rule: dict, culture: str = "en-US") -> str | None:
        return self.resources.get(f"AddonConfig.Rules.{rule['UId']}.Caption", culture)

    def base_edits(self) -> list[str]:
        """Lines of a replacing addon that change rules of the base addon."""
        if not self.replacing:
            return []
        return [f"{op} {path} {value.splitlines()[0] if value else ''}".rstrip() for op, path, value, rule, _ in self.ops
                if rule is None and path.startswith(_RULE_PATH + ".") or op == "-" and path.startswith(_RULE_PATH)]

    # ------------------------------------------------------------------ context
    def context(self) -> dict:
        """What the names in a rule can refer to: {attr: (type, ref)} and, for pages, the element names."""
        if self.kind == "entity":
            entity = self.target or self.target_uid
            copies = self.ws.find(entity, "EntitySchemaManager")  # a replacing copy lacks the base columns
            return {"attributes": self.ws.columns(entity), "elements": None, "complete": bool(copies) and all(s["uid"] == s["base"] for s in copies)}
        attrs, sources, elements = self.ws.page_model(self.target or self.target_uid)
        typed = {}
        for name, path in attrs.items():
            ds, _, col = (path or "").partition(".")
            cols = self.ws.columns(sources[ds]) if ds in sources else {}
            typed[name] = cols.get(col.split(".")[0], (None, None)) if col else (None, None)
        complete = bool(attrs) and not any(s["uid"] != s["base"] for s in self.ws.find(self.target or self.target_uid, "ClientUnitSchemaManager"))
        return {"attributes": typed, "paths": {p: n for n, p in attrs.items() if p}, "elements": elements, "complete": complete}

    # ------------------------------------------------------------------ build
    def _attr_name(self, ctx: dict, ref: str) -> str:
        return ctx.get("paths", {}).get(ref, ref)  # a page accepts "PDS.Column" for the attribute bound to it

    def _type_of(self, ctx: dict, path: str) -> tuple[str | None, str | None]:
        root, _, rest = path.partition(".")
        t = ctx["attributes"].get(root, (None, None))
        if rest and t[1]:  # a path through a lookup: resolve in the referenced entity
            return self.ws.columns(t[1]).get(rest.split(".")[0], (None, None))
        return t if not rest else (None, None)

    @staticmethod
    def _expr(type_name: str, **keys) -> dict:
        out = {"JI0": type_name, "UId": new_uid()}
        out.update({k: v for k, v in keys.items() if v is not None})
        return out

    def _attr_expr(self, ctx: dict, path: str, scope: str | None) -> dict:
        return self._expr(T_ATTR, BRE1=self._type_of(ctx, path)[0], BRE2="AttributeValue", BRX1=path, BRX2=scope)

    def _value_expr(self, ctx: dict, left_path: str, cond: dict, scope: str | None) -> dict:
        t, ref = self._type_of(ctx, left_path)
        t, ref = cond.get("type", t), cond.get("ref", ref)
        if "attr" in cond:
            path = self._attr_name(ctx, cond["attr"])
            rt, rref = self._type_of(ctx, path)
            return self._expr(T_ATTR, BRE1=rt or t, BRE2="AttributeValue", BRE3=rref if (rt or t) == "Lookup" else None, BRX1=path, BRX2=scope)
        if "sys" in cond:
            return self._expr(T_SYS, BRE1=cond.get("type", SYS_VALUE_TYPES.get(cond["sys"], t)), BRE2="SysValue", BSV1=cond["sys"])
        if "setting" in cond:
            return self._expr(T_SETTING, BRE1=t, BRE2="SysSetting", BSS1=cond["setting"])
        value = cond.get("value")
        if value is None:
            if t != "Lookup":
                raise ValueError(f"{left_path}: an empty value is only defined for lookups here; use op 'empty' in a condition")
            return self._expr(T_EMPTY, BRE1="Lookup", BVE1=EMPTY_GUID)
        if t is None:
            t = "Boolean" if isinstance(value, bool) else "Integer" if isinstance(value, int) else "Lookup" if _GUID_RE.fullmatch(str(value)) else None
        if t is None:
            raise ValueError(f"{left_path}: type unknown (not in the workspace); give \"type\": \"ShortText\" ... in the spec")
        if t == "Lookup" and not ref:
            raise ValueError(f"{left_path}: lookup reference schema unknown; give \"ref\": \"<EntityName>\" in the spec")
        return self._expr(T_VALUE, BRE1=t, BRE3=ref if t == "Lookup" else None, BVE1=value)

    def _condition(self, ctx: dict, cond: dict, scope: str | None) -> dict:
        op = OPS[cond["op"]] if isinstance(cond["op"], str) else int(cond["op"])
        left = self._attr_name(ctx, cond["left"])
        out = {"JI0": T_COND, "UId": new_uid(), "BCO1": self._attr_expr(ctx, left, scope)}
        if op not in UNARY:
            out["BCO2"] = self._value_expr(ctx, left, cond, scope)
        out["BCO3"] = op
        return out

    @staticmethod
    def _items(items) -> str:
        return ",".join([items] if isinstance(items, str) else items)  # page: element names; entity: column names

    def _set_values(self, ctx: dict, values: dict, scope: str | None) -> dict:
        items = []
        for col, v in values.items():
            col = self._attr_name(ctx, col)
            cond = v if isinstance(v, dict) else {"value": v}
            t, _ = self._type_of(ctx, col)
            items.append({"JI0": T_SET_ITEM, "UId": new_uid(), "BRA2": self._expr(T_ATTR, BRE1=t, BRE2="AttributeValue", BRX1=col, BRX2=scope or "null"),
                          "BRA3": self._value_expr(ctx, col, cond, scope)})
        return {"JI0": T_SET_VALUES, "UId": new_uid(), "BRA2": self._expr(T_ATTR), "BRA3": self._expr(T_VALUE), "BSVS1": items}

    def build(self, spec: dict) -> list[dict]:
        """Rule dicts for a readable spec (see README); a filter-lookup action adds its two generated rules."""
        ctx, scope = self.context(), spec.get("scope")
        uid = new_uid()
        case = {"JI0": T_CASE, "UId": new_uid()}
        conds = [self._condition(ctx, c, scope) for c in spec.get("conditions", [])]
        if conds:
            case["BRC1"] = {"JI0": T_GROUP, "UId": new_uid(), "BGC1": LOGIC[spec.get("logic", "and")], "BGC2": conds}
        actions, extra, trigger_names = [], [], []
        for c in conds:
            for e in (c["BCO1"], c.get("BCO2")):
                if e and e["JI0"] == T_ATTR:
                    trigger_names.append(e["BRX1"].split(".")[0])
        for a in spec["actions"]:
            kind = a["type"]
            if kind in PAGE_ONLY and self.kind != "page" or kind in ENTITY_ONLY and self.kind != "entity":
                raise ValueError(f"action {kind!r} is not available on a {self.kind} rule")
            if kind in PROPERTY_ACTIONS:
                actions.append({"JI0": PROPERTY_ACTIONS[kind][0], "UId": new_uid(), "BRA4": self._items(a["items"])})
            elif kind == "set":
                actions.append(self._set_values(ctx, a["values"], scope))
            elif kind == "static-filter":
                f = a["filter"] if isinstance(a["filter"], str) else json.dumps(a["filter"], separators=(",", ":"), ensure_ascii=False)
                actions.append({"JI0": T_SET_FILTER, "UId": new_uid(), "BRA2": self._expr(T_ATTR, BRX1=self._attr_name(ctx, a["column"])), "BRA3": self._expr(T_VALUE, BVE1=f)})
            elif kind == "filter-lookup":
                act, kids = self._filter_lookup(ctx, uid, a)
                actions.append(act)
                extra += kids
                trigger_names.append(a["source"])
            else:
                raise ValueError(f"unknown action type {kind!r}; one of {sorted(PROPERTY_ACTIONS) + sorted(ENTITY_ONLY)}")
        triggers = [{"JI0": T_TRIGGER, "UId": new_uid(), "BRT1": n, **({"BRT3": scope} if scope else {})} for n in dict.fromkeys(trigger_names)]
        triggers.append({"JI0": T_TRIGGER, "UId": new_uid(), "BRT2": DATA_LOADED})
        case["BRC2"] = actions
        rule = {"JI0": T_RULE, "UId": uid, "BR1": [case], "BR2": triggers, "BR3": spec.get("name") or rule_short_name(uid)}
        if spec.get("enabled") is False:
            rule["BR4"] = False
        caption = spec.get("caption") or self._default_caption(spec["actions"][0])
        return [(rule, caption)] + extra

    def _default_caption(self, action: dict) -> str:
        kind = action["type"]
        if kind in PROPERTY_ACTIONS:
            items = [action["items"]] if isinstance(action["items"], str) else action["items"]
            return f"{PROPERTY_ACTIONS[kind][1]}: {', '.join(items)}"
        return {"set": "Set values", "filter-lookup": "Apply filter", "static-filter": "Apply static filter"}[kind] + ": " + (action.get("column") or ", ".join(action.get("values", {})))

    def _filter_lookup(self, ctx: dict, parent_uid: str, a: dict) -> tuple[dict, list]:
        """Show in <column> only records whose <column>.<by> equals <source>; the designer adds two generated rules."""
        column, by, source = a["column"], a["by"], a["source"]
        col_ref = a.get("column_ref") or self._type_of(ctx, column)[1]
        src_ref = a.get("source_ref") or self._type_of(ctx, source)[1]
        if not col_ref or not src_ref:
            raise ValueError("filter-lookup: reference schemas unknown; give column_ref and source_ref")
        uid = new_uid()
        action = {"JI0": T_FILTER_LOOKUP, "UId": uid, "BRA2": self._expr(T_ATTR), "BRA3": self._expr(T_VALUE),
                  "BSFL1": self._expr(T_FILTER_EXPR, BRE1="Lookup", BRE3=col_ref, BVP1=column, BVF1=by),
                  "BSFR1": self._expr(T_FILTER_EXPR, BRE1="Lookup", BRE3=src_ref, BVP1=source)}

        def kid(suffix, cond, item_target, value_expr, trigger, enabled):
            r = {"JI0": T_RULE, "UId": new_uid(), "BR1": [{"JI0": T_CASE, "UId": new_uid(), "BRC1": cond, "BRC2": [
                {"JI0": T_SET_VALUES, "UId": new_uid(), "BRA2": self._expr(T_ATTR), "BRA3": self._expr(T_VALUE), "BSVS1": [
                    {"JI0": T_SET_ITEM, "UId": new_uid(), "BRA2": item_target, "BRA3": value_expr}]}]}],
                 "BR2": [{"JI0": T_TRIGGER, "UId": new_uid(), "BRT1": trigger}], "BR3": f"Autogenerated_{parent_uid}_{suffix}"}
            if not enabled:
                r["BR4"] = False
            r.update({"BR5": parent_uid, "BR6": uid})
            return r, f"ChildRule-{parent_uid}-{suffix}"

        clear = kid("ClearValue",
                    {"JI0": T_COND, "UId": new_uid(), "BCO1": self._expr(T_ATTR, BRE2="AttributeValue", BRX1=source),
                     "BCO2": self._expr(T_ATTR, BRE2="AttributeValue", BRX1=f"{column}.{by}"), "BCO3": OPS["not-equal"]},
                    self._expr(T_ATTR, BRE1="Lookup", BRX1=column, BRX2="null"), self._expr(T_EMPTY, BRE1="Lookup", BVE1=EMPTY_GUID), source, a.get("clear", True))
        populate = kid("PopulateValue",
                       {"JI0": T_COND, "UId": new_uid(), "BCO1": self._expr(T_ATTR, BRE2="AttributeValue", BRX1=column), "BCO3": OPS["filled"]},
                       self._expr(T_ATTR, BRX1=source, BRX2="null"), self._expr(T_ATTR, BRE1="Lookup", BRE2="AttributeValue", BRE3=src_ref, BRX1=f"{column}.{by}"),
                       column, a.get("populate", True))
        return action, [clear, populate]

    # ------------------------------------------------------------------ change
    def add(self, spec: dict) -> list[dict]:
        built = self.build(spec)
        names = {r["BR3"] for r in self.rules}
        for rule, caption in built:
            if rule["BR3"] in names:
                raise ValueError(f"rule name {rule['BR3']} already exists")
            self._append(rule)
            self.resources.set(f"AddonConfig.Rules.{rule['UId']}.Caption", caption, ["en-US"])  # the designer writes rule captions to en-US only
        return [r for r, _ in built]

    def _append(self, rule: dict) -> None:
        if not self.replacing:
            self.rules.append(rule)
            return
        order = next((o for o in self.ops if o[0] == "~" and o[1] == _RULE_PATH), None)
        at = self.ops.index(order) if order else len(self.ops)
        self.ops.insert(at, ["+", _RULE_PATH, None, rule, None])
        if order:
            uids = json.loads(order[2]) + [rule["UId"]]
            order[2] = _dump(uids)

    def replace(self, key: str, spec: dict) -> list[dict]:
        """Rebuild a rule from a spec keeping its UId, name and caption key (what an edit in the designer does)."""
        old = self.rule(key)
        uid = old["UId"]
        spec = dict(spec, name=spec.get("name") or old["BR3"], caption=spec.get("caption") or self.caption(old))
        (new, caption), *kids = self.build(spec)
        for r in [r for r in self.rules if r.get("BR5") == uid]:  # generated rules are rebuilt with the parent
            self.remove(r["UId"])
        fresh = new["UId"]
        new["UId"] = uid
        old.clear()
        old.update(new)  # in place: the position and the replacing addon's order list stay
        self.resources.set(f"AddonConfig.Rules.{uid}.Caption", caption, ["en-US"])
        for r, cap in kids:
            r["BR5"], r["BR3"] = uid, r["BR3"].replace(fresh, uid)
            self._append(r)
            self.resources.set(f"AddonConfig.Rules.{r['UId']}.Caption", cap.replace(fresh, uid), ["en-US"])
        return [old] + [r for r, _ in kids]

    def remove(self, key: str) -> list[str]:
        """Remove an own rule and the rules generated for it."""
        rule = self.rule(key)
        doomed = {rule["UId"]} | {r["UId"] for r in self.rules if r.get("BR5") == rule["UId"]}
        if self.replacing:
            self.ops = [o for o in self.ops if not (o[3] and o[3]["UId"] in doomed)]
            for o in self.ops:
                if o[0] == "~" and o[1] == _RULE_PATH:
                    o[2] = _dump([u for u in json.loads(o[2]) if u not in doomed])
        else:
            self.rules[:] = [r for r in self.rules if r["UId"] not in doomed]
        self.resources.remove(lambda k: any(k.startswith(f"AddonConfig.Rules.{u}.") for u in doomed))
        return sorted(doomed)

    def set_enabled(self, key: str, enabled: bool) -> None:
        """Own rule by name/caption/UId; a base rule (replacing addon) by its UId."""
        try:
            rule = self.rule(key)
        except KeyError:
            if not (self.replacing and _GUID_RE.fullmatch(key)):
                raise
            path = f'{_RULE_PATH}.["{key}"].BR4'
            self.ops = [o for o in self.ops if o[1] != path]
            if not enabled:
                self.ops.append(["+", path, "false", None, None])
            return
        if enabled:
            rule.pop("BR4", None)
        else:
            rule["BR4"] = False

    def remove_base(self, uid: str) -> None:
        """Replacing addon: delete a rule of the base addon (the designer writes `- ...BRS1.["uid"]`)."""
        if not self.replacing:
            raise ValueError("only a replacing addon can remove base rules")
        self.ops.append(["-", f'{_RULE_PATH}.["{uid}"]', "", None, None])

    def set_caption(self, key: str, value: str, cultures: list[str] | None = None) -> None:
        self.resources.set(f"AddonConfig.Rules.{self.rule(key)['UId']}.Caption", value, cultures or ["en-US"])

    # ------------------------------------------------------------------ check
    def validate(self) -> list[str]:
        problems, ctx = [], self.context()
        v83 = tuple(int(x) for x in self.version.split(".")[:2]) >= (8, 3)
        names = [r["BR3"] for r in self.rules]
        # warnings: generated duplicates do occur in designer output; templates add elements the workspace cannot see
        problems += [f"{'warning: ' if n.startswith('Autogenerated_') else ''}duplicate rule name {n}" for n in sorted({n for n in names if names.count(n) > 1})]
        uids = {r["UId"] for r in self.rules}
        known = set(ctx["attributes"]) | set(ctx.get("paths", {}).values())
        for r in self.rules:
            label = r["BR3"]
            if r.get("BR5") and r["BR5"] not in uids and not self.replacing:
                problems.append(f"{label}: parent rule {r['BR5']} is missing")
            if not r.get("BR5") and not self.caption(r):
                problems.append(f"{label}: no en-US caption (AddonConfig.Rules.{r['UId']}.Caption)")
            for node in _walk(r):
                t = node.get("JI0", "")
                if "BCO3" in node and node["BCO3"] in RELATIONAL and not v83:
                    problems.append(f"{label}: comparison {OP_NAMES[node['BCO3']]} needs Creatio 8.3+ (schema says {self.version}); the 8.2 designer shows an empty condition")
                if "BCO3" in node and node["BCO3"] not in OP_NAMES:
                    problems.append(f"{label}: unknown comparison {node['BCO3']}")
                if t.endswith(("ShowElement", "HideElement")) and self.kind != "page":
                    problems.append(f"{label}: show/hide exists only in page rules")
                if ctx["complete"] and t == T_ATTR and node.get("BRX1") and node.get("BRX2") in (None, "null"):  # scoped ones belong to a list data source
                    root = node["BRX1"].split(".")[0]
                    if root not in known:
                        problems.append(f"warning: {label}: attribute {root!r} is not on {self.target} (or comes from a parent page)")
                if ctx["complete"] and "BRA4" in node:
                    pool = ctx["elements"] if self.kind == "page" else ctx["attributes"]
                    for item in node["BRA4"].split(","):
                        if item and item not in pool:
                            problems.append(f"warning: {label}: {'element' if self.kind == 'page' else 'column'} {item!r} is not on {self.target} (or comes from a parent/template)")
        return problems

    # ------------------------------------------------------------------ show
    def describe_expr(self, e: dict | None) -> str:
        if not e:
            return ""
        t = e.get("JI0", "")
        if t == T_ATTR:
            return e.get("BRX1", "?") + (f"@{e['BRX2']}" if e.get("BRX2") not in (None, "null") else "")
        if t == T_SYS:
            return f"sys:{e.get('BSV1')}"
        if t == T_SETTING:
            return f"setting:{e.get('BSS1')}"
        if t == T_EMPTY:
            return "<empty>"
        if "BVE1" in e:
            return json.dumps(e["BVE1"], ensure_ascii=False)[:80] + (f" ({e['BRE3']})" if e.get("BRE3") else "")
        return _short(t)

    def describe_rule(self, r: dict) -> list[str]:
        state = "" if r.get("BR4", True) else "  [disabled]"
        head = f"{r['BR3']}{state}  {self.caption(r) or ''!r}" + (f"  (generated for {r['BR5']})" if r.get("BR5") else "")
        out = [head]
        for case in r["BR1"]:
            c = case.get("BRC1")
            if c:
                parts = c["BGC2"] if c.get("JI0") == T_GROUP else [c]
                logic = " or " if c.get("BGC1") == 2 else " and "
                text = logic.join(f"{self.describe_expr(p['BCO1'])} {OP_NAMES.get(p.get('BCO3'), p.get('BCO3'))}" + (f" {self.describe_expr(p.get('BCO2'))}" if p.get("BCO2") else "") for p in parts)
                out.append(f"    when {text}")
            for a in case["BRC2"]:
                t = a["JI0"]
                kind = next((k for k, (cls, _) in PROPERTY_ACTIONS.items() if cls == t), None)
                if kind:
                    out.append(f"    then {kind}: {a.get('BRA4')}")
                elif t == T_SET_VALUES:
                    out.append("    then set " + ", ".join(f"{self.describe_expr(i['BRA2'])} = {self.describe_expr(i['BRA3'])}" for i in a.get("BSVS1", [])))
                elif t == T_FILTER_LOOKUP:
                    l, rr = a["BSFL1"], a["BSFR1"]
                    out.append(f"    then filter {l.get('BVP1')} by {l.get('BVP1')}.{l.get('BVF1')} = {rr.get('BVP1')}")
                elif t == T_SET_FILTER:
                    out.append(f"    then static filter on {a['BRA2'].get('BRX1')}: {a['BRA3'].get('BVE1', '')[:100]}")
                else:
                    out.append(f"    then {_short(t)}")
        trig = [tr.get("BRT1") or {0: "AttributeChanged", 1: "PropertyChanged", 2: "DataLoaded", 3: "ContextReady"}.get(tr.get("BRT2"), "?") for tr in r.get("BR2", [])]
        out.append(f"    on {', '.join(trig)}")
        return out

    def describe(self) -> str:
        lines = [f"{self.name}: {self.kind} rules for {self.target or self.target_uid}, {'replacing' if self.replacing else 'own'} addon, created in {self.version}, {len(self.rules)} rule(s)"]
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

    # ------------------------------------------------------------------ write
    def render_metadata(self) -> str:
        if not self.replacing:
            return _dump(self.meta, self.nl)
        parts = []
        for op, path, value, rule, snap in self.ops:
            if rule is not None:
                text = _dump(rule)
                value = value if text == snap and value is not None else text
            parts.append(f"{op} {path}" + (f" {value}" if value else ""))
        return "\r\n".join(parts).replace("\r\n", self.nl)

    def files(self) -> dict[Path, tuple[str, bool]]:
        out = {self.dir / "metadata.json": (self.render_metadata(), self.meta_bom), self.dir / "descriptor.json": (self.descriptor_text, True)}
        for culture in self.resources.cultures:
            out[self.resources.folder / f"resource.{culture}.xml"] = (self.resources.render(culture).lstrip("﻿"), True)
        return out

    def save(self) -> None:
        self.descriptor_text = re.sub(r'"\\/Date\(\d+\)\\/"', f'"\\\\/Date({int(time.time()) * 1000})\\\\/"', self.descriptor_text, count=1)
        for path, (text, bom) in self.files().items():
            _write(path, text, bom)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


# --------------------------------------------------------------------------- #
# New rule schema
# --------------------------------------------------------------------------- #


def create_rule_schema(package: Path, target: str, parent_uid: str | None = None, target_uid: str | None = None,
                       kind: str | None = None, version: str = "8.2.3.1351", caption: str | None = None) -> RuleSchema:
    """Addon `<target>BusinessRule` in `package`.

    Without parent_uid: an own addon (full JSON). With parent_uid (the UId of the base package's
    `<target>BusinessRule`): a replacing addon in the diff form. The target is resolved from the
    workspace; a base target outside it needs target_uid and kind (entity | page).
    """
    package = Path(package)
    name = f"{target}BusinessRule"
    sdir = package / "Schemas" / name
    if sdir.exists():
        raise FileExistsError(sdir)
    ws = Workspace(package)
    hits = ws.find(target)
    if hits:
        target_uid = target_uid or hits[0]["base"]
        kind = kind or ("entity" if hits[0]["manager"] == "EntitySchemaManager" else "page")
        caption = caption or f"{hits[0]['caption']} (Business rules)"
    if not target_uid or kind not in ("entity", "page"):
        raise ValueError(f"{target} is not in the workspace; pass target_uid and kind (SQL: select \"UId\" from \"SysSchema\" where \"Name\" = '{target}' and \"ExtendParent\" = false)")
    caption = caption or f"{target} (Business rules)"
    manager = "EntitySchemaManager" if kind == "entity" else "ClientUnitSchemaManager"
    pkg_uid = json.loads(_read_raw(package / "descriptor.json")[0])["Descriptor"]["UId"]
    created_in = pkg_uid
    for m in package.glob("Schemas/*/metadata.json"):  # A5 is the package's own id, the same in all its schemas
        hit = re.search(r'"A5": "([0-9a-f-]{36})"|MetaData\.Schema\.A5 "([0-9a-f-]{36})"', _read_raw(m)[0][:2000])
        if hit:
            created_in = hit.group(1) or hit.group(2)
            break
    uid = new_uid()
    if parent_uid:
        meta = "\r\n".join([f'= MetaData.Schema.UId "{uid}"', f'= MetaData.Schema.A5 "{created_in}"', f'= MetaData.Schema.B6 "{pkg_uid}"',
                            "+ MetaData.Schema.B7 true", f'= MetaData.Schema.B8 "{version}"', f'= MetaData.Schema.AD5 "{parent_uid}"'])
        _write(sdir / "metadata.json", meta, False)
        desc = {"UId": uid, "Name": name, "ModifiedOnUtc": "", "Parent": {"UId": parent_uid, "Name": name}, "ExtendParent": True,
                "ManagerName": "AddonSchemaManager", "Caption": caption, "DependsOn": []}
    else:
        schema = {"ManagerName": "AddonSchemaManager", "UId": uid, "A2": name, "A5": created_in, "B1": [], "B2": [], "B3": [], "B6": pkg_uid, "B8": version,
                  "AD1": target_uid, "AD2": manager, "AD3": "BusinessRule", "AD5": "3a2d6f51-1bfc-4c17-aacb-b53de4866b7c",  # the platform's base BusinessRule addon
                  "AD4": {"JI0": T_RULES, "BRS1": []}}
        _write(sdir / "metadata.json", _dump({"MetaData": {"Schema": schema}}), True)
        desc = {"UId": uid, "Name": name, "ModifiedOnUtc": "", "ManagerName": "AddonSchemaManager", "Caption": caption, "DependsOn": []}
    # ModifiedOnUtc must be the WCF literal "\/Date(ms)\/" or the push fails with "Specified cast is not valid"
    text = _dump({"Descriptor": desc}).replace('"ModifiedOnUtc": ""', f'"ModifiedOnUtc": "\\/Date({int(time.time()) * 1000})\\/"')
    _write(sdir / "descriptor.json", text, True)
    _write(sdir / "properties.json", _dump({"Properties": {"AddonName": "BusinessRule", "CreatedInVersion": version,
                                                           "TargetSchemaManagerName": manager, "TargetSchemaUId": target_uid}}), True)
    res = package / "Resources" / f"{name}.Addon"
    cultures = sorted({p.name[9:-4] for h in hits for p in (h["dir"].parent.parent / "Resources").glob(f"{h['name']}.*/resource.*.xml")}) or ["en-US"]
    for culture in cultures:
        _write(res / f"resource.{culture}.xml", f'<?xml version="1.0" encoding="utf-8"?>\r\n<Resources Culture="{culture}">\r\n\t<Group Type="String">\r\n\t\t<Items>\r\n\t\t</Items>\r\n\t</Group>\r\n</Resources>', True)
    rs = RuleSchema(package, name)
    rs.resources.set("Caption", caption)
    rs.save()
    return rs
