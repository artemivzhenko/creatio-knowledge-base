"""The rule model of Terrasoft.Core.BusinessRules: type names, enums and the obfuscated keys.

    BusinessRule        BR1 cases, BR2 triggers, BR3 name, BR4 enabled, BR5 parent rule, BR6 parent action
    Case                BRC1 condition (optional), BRC2 actions
    GroupCondition      BGC1 logic (1 and, 2 or), BGC2 conditions
    Condition           BCO1 left, BCO2 right, BCO3 comparison
    Expression          BRE1 data value type name, BRE2 kind, BRE3 reference schema
      attribute         BRX1 path, BRX2 scope (a list data source)
      value / empty     BVE1;  sys value BSV1;  sys setting BSS1
      filter lookup     BVP1 path, BVF1 filter column
    Action              BRA4 items (property actions), BRA5 enabled; set values BSVS1 of items (BRA2 target, BRA3 value);
                        filter lookup BSFL1 / BSFR1; static filter BRA2 column, BRA3.BVE1 filter JSON
    Trigger             BRT1 attribute, BRT2 type, BRT3 scope

8.2.3 and 8.3.2 share the model, except the relational comparisons 5-8 (8.3+ only).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from ..files import new_uid

NS = "Terrasoft.Core.BusinessRules."
M = NS + "Models."
X = M + "Expressions."
A = M + "Actions.BusinessRuleAction"
T_RULES, T_RULE, T_CASE, T_TRIGGER = NS + "BusinessRules", NS + "BusinessRule", M + "BusinessRuleCase", M + "Trigger"
T_GROUP, T_COND = M + "Conditions.BusinessRuleGroupCondition", M + "Conditions.BusinessRuleCondition"
T_ATTR, T_VALUE, T_EMPTY = X + "BusinessRuleAttributeExpression", X + "BusinessRuleValueExpression", X + "BusinessRuleEmptyValueExpression"
T_SYS, T_SETTING = X + "BusinessRuleSysValueExpression", X + "BusinessRuleSysSettingExpression"
T_SET_ITEM, T_FILTER_EXPR = X + "BusinessRuleSetValueItem", X + "BusinessRuleFilterLookupExpression"
T_SET_VALUES, T_FILTER_LOOKUP, T_SET_FILTER = A + "SetValues", A + "FilterLookup", A + "SetFilter"

OPS = {"empty": 0, "filled": 1, "equal": 2, "not-equal": 3, "less": 5, "less-or-equal": 6, "greater": 7, "greater-or-equal": 8, "contain": 11, "not-contain": 12}
OP_NAMES = {v: k for k, v in OPS.items()}
UNARY = {0, 1}
RELATIONAL = {5, 6, 7, 8}  # BusinessRuleExpressionComparisonType has them only from 8.3
LOGIC = {"and": 1, "or": 2}  # Terrasoft.Common.LogicalOperation: None, And, Or
TRIGGER_TYPES = {0: "AttributeChanged", 1: "PropertyChanged", 2: "DataLoaded", 3: "ContextReady"}
DATA_LOADED = 2
SYS_VALUE_TYPES = {"CurrentUser": "Lookup", "CurrentUserContact": "Lookup", "CurrentUserAccount": "Lookup", "CurrentDate": "Date",
                   "CurrentDateTime": "DateTime", "CurrentTime": "Time", "CurrentUserRoles": "ObjectList"}
RULES_PATH = "MetaData.Schema.AD4.BRS1"  # where the rules sit, in both storage forms
BASE_ADDON_UID = "3a2d6f51-1bfc-4c17-aacb-b53de4866b7c"  # the platform's BusinessRule addon, AD5 of an own addon


def node(type_name: str, **keys) -> dict:
    """A model object: JI0 type, a fresh UId, then the keys that are not None, in the given order."""
    out = {"JI0": type_name, "UId": new_uid()}
    out.update({k: v for k, v in keys.items() if v is not None})
    return out


def short_type(type_name: str) -> str:
    return type_name.rsplit(".", 1)[-1].replace("BusinessRule", "")


def rule_short_name(uid: str) -> str:
    """The designer's rule name: BusinessRule_ + the first 7 hex digits of the UId."""
    return "BusinessRule_" + uid.replace("-", "")[:7]


def caption_key(rule_uid: str) -> str:
    return f"AddonConfig.Rules.{rule_uid}.Caption"


def walk(item):
    """Every dict inside a rule, depth first."""
    if isinstance(item, dict):
        yield item
        for v in item.values():
            yield from walk(v)
    elif isinstance(item, list):
        for v in item:
            yield from walk(v)


def format_expr(e: dict | None) -> str:
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
    return short_type(t)


@dataclass
class RuleContext:
    """What names in a rule can refer to.

    attributes  {name: (data value type, reference schema)}: entity columns, or page attributes
    paths       page only: {"DS.Column": attribute bound to it}
    elements    page only: element names of viewConfigDiff
    complete    the workspace sees the whole target (no replacing copies), so unknown names are worth a warning
    """
    attributes: dict = field(default_factory=dict)
    paths: dict = field(default_factory=dict)
    elements: set | None = None
    complete: bool = False
