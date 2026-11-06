"""Rule actions: one ActionType per spec "type", registered in ACTIONS.

An ActionType turns its spec into the action dict, may add generated rules (filter lookup does)
and names attributes that must trigger the rule. To support a new action, subclass ActionType
and add an instance to ACTIONS; describe() and the default caption come with it.
"""

from __future__ import annotations

import json

from ..files import EMPTY_GUID, new_uid
from .model import (A, OPS, T_ATTR, T_CASE, T_COND, T_EMPTY, T_FILTER_EXPR, T_FILTER_LOOKUP, T_RULE, T_SET_FILTER, T_SET_ITEM,
                    T_SET_VALUES, T_TRIGGER, T_VALUE, format_expr, node)

PAGE, ENTITY = "page", "entity"


class ActionType:
    name = ""
    cls = ""
    kinds = (PAGE, ENTITY)  # rule kinds the 8.x designers offer it on
    caption = ""

    def build(self, b, spec: dict, rule_uid: str, scope: str | None) -> tuple[dict, list[tuple[dict, str]], list[str]]:
        """(action, generated (rule, caption) pairs, trigger attribute names)."""
        raise NotImplementedError

    def describe(self, action: dict) -> str:
        return self.name

    def default_caption(self, spec: dict) -> str:
        return f"{self.caption}: {spec.get('column') or ', '.join(spec.get('values', {}))}"


class PropertyAction(ActionType):
    """required / optional / read-only / editable / show / hide: a comma-joined list of names in BRA4
    (element names on a page, column names on an object)."""

    def __init__(self, name: str, cls_suffix: str, caption: str, kinds=(PAGE, ENTITY)):
        self.name, self.cls, self.caption, self.kinds = name, A + cls_suffix, caption, kinds

    @staticmethod
    def items(spec: dict) -> list[str]:
        return [spec["items"]] if isinstance(spec["items"], str) else list(spec["items"])

    def build(self, b, spec, rule_uid, scope):
        return node(self.cls, BRA4=",".join(self.items(spec))), [], []

    def describe(self, action):
        return f"{self.name}: {action.get('BRA4')}"

    def default_caption(self, spec):
        return f"{self.caption}: {', '.join(self.items(spec))}"


class SetValuesAction(ActionType):
    """{"type": "set", "values": {"Column": <value> | {"sys": ..} | {"attr": ..} | {"setting": ..} | null}}"""
    name, cls, kinds, caption = "set", T_SET_VALUES, (ENTITY,), "Set values"

    def build(self, b, spec, rule_uid, scope):
        items = []
        for col, v in spec["values"].items():
            col = b.attr_name(col)
            items.append(node(T_SET_ITEM, BRA2=node(T_ATTR, BRE1=b.type_of(col)[0], BRE2="AttributeValue", BRX1=col, BRX2=scope or "null"),
                              BRA3=b.value(col, v if isinstance(v, dict) else {"value": v}, scope)))
        return node(T_SET_VALUES, BRA2=node(T_ATTR), BRA3=node(T_VALUE), BSVS1=items), [], []

    def describe(self, action):
        return "set " + ", ".join(f"{format_expr(i['BRA2'])} = {format_expr(i['BRA3'])}" for i in action.get("BSVS1", []))


class StaticFilterAction(ActionType):
    """{"type": "static-filter", "column": "UsrType", "filter": <the designer's filter JSON>}"""
    name, cls, kinds, caption = "static-filter", T_SET_FILTER, (ENTITY,), "Apply static filter"

    def build(self, b, spec, rule_uid, scope):
        f = spec["filter"] if isinstance(spec["filter"], str) else json.dumps(spec["filter"], separators=(",", ":"), ensure_ascii=False)
        return node(T_SET_FILTER, BRA2=node(T_ATTR, BRX1=b.attr_name(spec["column"])), BRA3=node(T_VALUE, BVE1=f)), [], []

    def describe(self, action):
        return f"static filter on {action['BRA2'].get('BRX1')}: {action['BRA3'].get('BVE1', '')[:100]}"


class FilterLookupAction(ActionType):
    """Show in <column> only records whose <column>.<by> equals <source>.

    {"type": "filter-lookup", "column": "City", "by": "Country", "source": "Country",
     "column_ref": "City", "source_ref": "Country", "clear": true, "populate": true}

    The designer adds two generated rules (BR5 = parent rule, BR6 = this action): ClearValue empties
    <column> when <source> changes; PopulateValue fills <source> from the chosen <column>.
    """
    name, cls, kinds, caption = "filter-lookup", T_FILTER_LOOKUP, (ENTITY,), "Apply filter"

    def build(self, b, spec, rule_uid, scope):
        column, by, source = spec["column"], spec["by"], spec["source"]
        col_ref = spec.get("column_ref") or b.type_of(column)[1]
        src_ref = spec.get("source_ref") or b.type_of(source)[1]
        if not col_ref or not src_ref:
            raise ValueError("filter-lookup: reference schemas unknown; give column_ref and source_ref")
        action = node(T_FILTER_LOOKUP, BRA2=node(T_ATTR), BRA3=node(T_VALUE),
                      BSFL1=node(T_FILTER_EXPR, BRE1="Lookup", BRE3=col_ref, BVP1=column, BVF1=by),
                      BSFR1=node(T_FILTER_EXPR, BRE1="Lookup", BRE3=src_ref, BVP1=source))
        clear = self._generated(rule_uid, action["UId"], "ClearValue",
                                node(T_COND, BCO1=node(T_ATTR, BRE2="AttributeValue", BRX1=source),
                                     BCO2=node(T_ATTR, BRE2="AttributeValue", BRX1=f"{column}.{by}"), BCO3=OPS["not-equal"]),
                                node(T_ATTR, BRE1="Lookup", BRX1=column, BRX2="null"), node(T_EMPTY, BRE1="Lookup", BVE1=EMPTY_GUID),
                                source, spec.get("clear", True))
        populate = self._generated(rule_uid, action["UId"], "PopulateValue",
                                   node(T_COND, BCO1=node(T_ATTR, BRE2="AttributeValue", BRX1=column), BCO3=OPS["filled"]),
                                   node(T_ATTR, BRX1=source, BRX2="null"),
                                   node(T_ATTR, BRE1="Lookup", BRE2="AttributeValue", BRE3=src_ref, BRX1=f"{column}.{by}"),
                                   column, spec.get("populate", True))
        return action, [clear, populate], [source]

    @staticmethod
    def _generated(parent_uid, action_uid, suffix, condition, target, value, trigger, enabled) -> tuple[dict, str]:
        r = {"JI0": T_RULE, "UId": new_uid(), "BR1": [node(T_CASE, BRC1=condition, BRC2=[
            node(T_SET_VALUES, BRA2=node(T_ATTR), BRA3=node(T_VALUE), BSVS1=[node(T_SET_ITEM, BRA2=target, BRA3=value)])])],
             "BR2": [node(T_TRIGGER, BRT1=trigger)], "BR3": f"Autogenerated_{parent_uid}_{suffix}"}
        if not enabled:
            r["BR4"] = False
        r.update({"BR5": parent_uid, "BR6": action_uid})
        return r, f"ChildRule-{parent_uid}-{suffix}"

    def describe(self, action):
        left, right = action["BSFL1"], action["BSFR1"]
        return f"filter {left.get('BVP1')} by {left.get('BVP1')}.{left.get('BVF1')} = {right.get('BVP1')}"


ACTIONS: dict[str, ActionType] = {a.name: a for a in [
    PropertyAction("required", "RequiredElement", "Make elements required"),
    PropertyAction("optional", "OptionalElement", "Make elements optional"),
    PropertyAction("readonly", "ReadonlyElement", "Make elements read-only"),
    PropertyAction("editable", "EditableElement", "Make elements editable"),
    PropertyAction("show", "ShowElement", "Show elements", (PAGE,)),
    PropertyAction("hide", "HideElement", "Hide elements", (PAGE,)),
    SetValuesAction(),
    FilterLookupAction(),
    StaticFilterAction(),
]}
ACTION_BY_CLASS: dict[str, ActionType] = {a.cls: a for a in ACTIONS.values()}
