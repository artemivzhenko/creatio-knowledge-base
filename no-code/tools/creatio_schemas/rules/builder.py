"""Readable rule spec -> rule dicts. The spec format is in tools/rules/README.md.

Types and lookup reference schemas of the names in a spec come from the RuleContext (the
workspace); a spec may give "type" / "ref" for a target the workspace cannot see.
"""

from __future__ import annotations

from ..files import EMPTY_GUID, GUID_RE, new_uid
from .actions import ACTIONS
from .model import DATA_LOADED, LOGIC, OPS, SYS_VALUE_TYPES, T_ATTR, T_CASE, T_COND, T_EMPTY, T_GROUP, T_RULE, T_SETTING, T_SYS, \
    T_TRIGGER, T_VALUE, UNARY, RuleContext, node, rule_short_name


class RuleBuilder:
    def __init__(self, kind: str, context: RuleContext, workspace):
        self.kind, self.ctx, self.workspace = kind, context, workspace

    # -- names and types ------------------------------------------------------ #

    def attr_name(self, ref: str) -> str:
        """A page accepts "PDS.Column" for the attribute bound to it."""
        return self.ctx.paths.get(ref, ref)

    def type_of(self, path: str) -> tuple[str | None, str | None]:
        """(data value type, reference schema) of an attribute or of a path through a lookup."""
        root, _, rest = path.partition(".")
        t = self.ctx.attributes.get(root, (None, None))
        if rest and t[1]:
            return self.workspace.columns(t[1]).get(rest.split(".")[0], (None, None))
        return t if not rest else (None, None)

    # -- expressions ---------------------------------------------------------- #

    def attr(self, path: str, scope: str | None) -> dict:
        return node(T_ATTR, BRE1=self.type_of(path)[0], BRE2="AttributeValue", BRX1=path, BRX2=scope)

    def value(self, left_path: str, cond: dict, scope: str | None) -> dict:
        """The right side: "attr", "sys", "setting" or a constant "value" (null = empty lookup)."""
        t, ref = self.type_of(left_path)
        t, ref = cond.get("type", t), cond.get("ref", ref)
        if "attr" in cond:
            path = self.attr_name(cond["attr"])
            rt, rref = self.type_of(path)
            return node(T_ATTR, BRE1=rt or t, BRE2="AttributeValue", BRE3=rref if (rt or t) == "Lookup" else None, BRX1=path, BRX2=scope)
        if "sys" in cond:
            return node(T_SYS, BRE1=cond.get("type", SYS_VALUE_TYPES.get(cond["sys"], t)), BRE2="SysValue", BSV1=cond["sys"])
        if "setting" in cond:
            return node(T_SETTING, BRE1=t, BRE2="SysSetting", BSS1=cond["setting"])
        value = cond.get("value")
        if value is None:
            if t != "Lookup":
                raise ValueError(f"{left_path}: an empty value is only defined for lookups here; use op 'empty' in a condition")
            return node(T_EMPTY, BRE1="Lookup", BVE1=EMPTY_GUID)
        if t is None:
            t = "Boolean" if isinstance(value, bool) else "Integer" if isinstance(value, int) else "Lookup" if GUID_RE.fullmatch(str(value)) else None
        if t is None:
            raise ValueError(f"{left_path}: type unknown (not in the workspace); give \"type\": \"ShortText\" ... in the spec")
        if t == "Lookup" and not ref:
            raise ValueError(f"{left_path}: lookup reference schema unknown; give \"ref\": \"<EntityName>\" in the spec")
        return node(T_VALUE, BRE1=t, BRE3=ref if t == "Lookup" else None, BVE1=value)

    def condition(self, cond: dict, scope: str | None) -> dict:
        op = OPS[cond["op"]] if isinstance(cond["op"], str) else int(cond["op"])
        left = self.attr_name(cond["left"])
        out = node(T_COND, BCO1=self.attr(left, scope))
        if op not in UNARY:
            out["BCO2"] = self.value(left, cond, scope)
        out["BCO3"] = op
        return out

    # -- rules ---------------------------------------------------------------- #

    def build(self, spec: dict) -> list[tuple[dict, str]]:
        """[(rule, caption)]: the rule first, then rules its actions generate."""
        scope = spec.get("scope")
        uid = new_uid()
        case = {"JI0": T_CASE, "UId": new_uid()}
        conds = [self.condition(c, scope) for c in spec.get("conditions", [])]
        if conds:
            case["BRC1"] = node(T_GROUP, BGC1=LOGIC[spec.get("logic", "and")], BGC2=conds)
        trigger_names = [e["BRX1"].split(".")[0] for c in conds for e in (c["BCO1"], c.get("BCO2")) if e and e["JI0"] == T_ATTR]
        actions, generated = [], []
        for a in spec["actions"]:
            action_type = ACTIONS.get(a["type"])
            if action_type is None:
                raise ValueError(f"unknown action type {a['type']!r}; one of {sorted(ACTIONS)}")
            if self.kind not in action_type.kinds:
                raise ValueError(f"action {a['type']!r} is not available on a {self.kind} rule")
            action, kids, triggers = action_type.build(self, a, uid, scope)
            actions.append(action)
            generated += kids
            trigger_names += triggers
        case["BRC2"] = actions
        triggers = [{"JI0": T_TRIGGER, "UId": new_uid(), "BRT1": n, **({"BRT3": scope} if scope else {})} for n in dict.fromkeys(trigger_names)]
        triggers.append({"JI0": T_TRIGGER, "UId": new_uid(), "BRT2": DATA_LOADED})
        rule = {"JI0": T_RULE, "UId": uid, "BR1": [case], "BR2": triggers, "BR3": spec.get("name") or rule_short_name(uid)}
        if spec.get("enabled") is False:
            rule["BR4"] = False
        first = spec["actions"][0]
        caption = spec.get("caption") or ACTIONS[first["type"]].default_caption(first)
        return [(rule, caption)] + generated
