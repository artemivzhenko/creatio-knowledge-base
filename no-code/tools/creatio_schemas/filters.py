"""Terrasoft filter groups - the JSON the designer stores for "the record must meet conditions" (signal starts,
catch signals, DCM cases, data elements): summarise one in a line, build one from `Column op value` conditions.

Two serialisations exist side by side: the designer's (`className` on every node, captions, keys) and the
runtime's (`dataSourceFilters`, the same tree without class names). A signal keeps both inside one outer
object; a DCM case keeps only the designer form.
"""

from __future__ import annotations

import json
import uuid

from .expressions import Condition, Const, Group, Null, describe, operand_text, parse
from .expressions.metapath import SUGAR_RE

COMPARISON = {0: "between", 1: "exists", 2: "not exists", 3: "=", 4: "!=", 5: ">", 6: ">=", 7: "<", 8: "<=", 9: "starts with", 10: "not starts with",
              11: "contains", 12: "not contains", 13: "ends with", 14: "not ends with", 15: "is null", 16: "is not null"}
OP_CODE = {"=": 3, "!=": 4, "<>": 4, ">": 5, ">=": 6, "<": 7, "<=": 8, "starts with": 9, "contains": 11, "not contains": 12, "ends with": 13}
# the canonical operator of the expression grammar <-> the comparisonType of a stored filter (the ones with a canonical name)
_CANONICAL = {3: "eq", 4: "ne", 5: "gt", 6: "ge", 7: "lt", 8: "le", 9: "starts", 11: "contains", 12: "not-contains", 13: "ends", 15: "empty", 16: "filled"}
_SPELLING = {"eq": "=", "ne": "!=", "gt": ">", "ge": ">=", "lt": "<", "le": "<=", "starts": "starts with", "contains": "contains",
             "not-contains": "not contains", "ends": "ends with", "empty": "is null", "filled": "is not null"}
# Terrasoft.DataValueType of the client (Resources/ui/Terrasoft/core/enums/sysenums.js); texts the enum does not name are TEXT.
CLIENT_TYPE = {"Guid": 0, "Text": 1, "ShortText": 27, "MediumText": 28, "MaxSizeText": 29, "RichText": 43, "SecureText": 24, "HashText": 23,
               "Integer": 4, "Float": 5, "Float1": 5, "Float2": 5, "Float3": 5, "Float4": 5, "Float8": 5, "Money": 6,
               "DateTime": 7, "Date": 8, "Time": 9, "Lookup": 10, "Boolean": 12, "Binary": 13, "Color": 18, "LocalizableString": 19}
_COMPACT = {"separators": (",", ":")}


def load(raw) -> dict | None:
    """The designer's FilterGroup as a dict, from a DCM `Filters` string or a signal's outer object (string or dict)."""
    if not raw:
        return None
    try:
        f = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return {"raw": raw}
    if isinstance(f, dict) and "serializedFilterEditData" in f:
        try:
            f = json.loads(f["serializedFilterEditData"])
        except ValueError:
            return {"raw": raw}
    return f if isinstance(f, dict) else None


def summarize(f: dict | None, root: str | None = None) -> str:
    """`UsrOrder where UsrAmount > 100 and UsrStatus is not null`; nested groups in parentheses."""
    if not f:
        return "every record"
    if "raw" in f and len(f) == 1:
        return f"(unreadable filter: {str(f['raw'])[:60]})"

    def group(g: dict) -> Group:
        items = []
        for item in (g.get("items") or {}).values():
            if "items" in item:
                items.append(group(item))
                continue
            left = (item.get("leftExpression") or {}).get("columnPath", "?")
            if item.get("className") == "Terrasoft.IsNullFilter" or "isNull" in item:
                op, right = ("empty" if item.get("isNull") else "filled"), Null()
            else:
                code = item.get("comparisonType")
                op = _CANONICAL.get(code) or COMPARISON.get(code, str(code))
                rights = []
                for r in item.get("rightExpressions") or ([item["rightExpression"]] if item.get("rightExpression") else []):
                    if "parameter" not in r and r.get("expressionType") == 1:  # a date macro (FunctionExpression)
                        rights.append(f"(macro {r.get('macrosType')})")
                        continue
                    v = (r.get("parameter") or {}).get("value")
                    rights.append(str(v.get("displayValue", v.get("value")) if isinstance(v, dict) else v))
                right = Const(", ".join(rights)) if rights else Null()
            items.append(Condition(left, op, right, item.get("isEnabled", True)))
        return Group(tuple(items), "or" if g.get("logicalOperation") == 1 else "and")

    return f"{f.get('rootSchemaName') or root} where " + (describe(group(f)) or "(empty filter)")


def parse_conditions(text: str) -> list[tuple[str, str, str]]:
    """`"UsrAmount > 100; UsrStatus is not null; UsrType = Parcel"` -> [(column, op, value)], ANDed; quotes around a value are dropped.
    The grammar is `expressions.parse`; `op` is the spelling `OP_CODE` knows."""
    return [(c.left, _SPELLING[c.op], c.right.text if isinstance(c.right, Const) else operand_text(c.right)) for c in parse(text)]


def _typed(value: str, type_name: str):
    if type_name == "Boolean":
        return value.strip().lower() in ("true", "1", "yes")
    if type_name == "Integer":
        return int(value)
    if type_name == "Money" or type_name.startswith("Float"):
        return float(value)
    if type_name == "Lookup":  # a lookup value is its record id; the designer would show the name
        return {"value": value, "displayValue": value}
    return value


PARAMETER_VALUE_TYPE = 26  # the right side is a process parameter (a meta path), whatever the column's type


def build(root: str, conditions: list[tuple[str, str, str]], columns: dict[str, tuple[str, str | None]], encode=None) -> str:
    """The outer object a signal or a data element stores (designer form + runtime form), as the compact JSON string the
    platform expects. `columns` is `Workspace.columns(root)`: name -> (data value type name, referenced schema). With
    `encode` (a process's `expressions.encode`), a value that is one `{Parameter:X}` / `{Element:E.Parameter:P[.EntityColumn:C]}`
    reference becomes the designer's parameter right side: the meta path, the name as its display value."""
    edit_items, run_items = {}, {}
    for col, op, val in conditions:
        if col not in columns:
            raise KeyError(f"{root} has no column {col}; columns: {', '.join(sorted(columns))}")
        type_name, ref = columns[col]
        code = CLIENT_TYPE.get(type_name or "", 1)
        key = str(uuid.uuid4())
        edit = {"className": "Terrasoft.IsNullFilter" if op in ("is null", "is not null") else "Terrasoft.CompareFilter",
                "filterType": 2 if op in ("is null", "is not null") else 1, "comparisonType": 15 if op == "is null" else 16 if op == "is not null" else OP_CODE[op],
                "isEnabled": True, "trimDateTimeParameterToDate": False,
                "leftExpression": {"className": "Terrasoft.ColumnExpression", "expressionType": 0, "columnPath": col},
                "isAggregative": False, "key": key, "dataValueType": code, "leftExpressionCaption": col}
        run = {"filterType": edit["filterType"], "comparisonType": edit["comparisonType"], "isEnabled": True, "trimDateTimeParameterToDate": False,
               "leftExpression": {"expressionType": 0, "columnPath": col}}
        if ref:
            edit["referenceSchemaName"] = ref
        if op in ("is null", "is not null"):
            edit["isNull"] = run["isNull"] = op == "is null"
        elif encode and SUGAR_RE.fullmatch(val.strip()):
            path = encode(val.strip())[2:-2]  # `[#...#]` -> the bare meta path a filter parameter holds
            shown = ".".join(x for x in SUGAR_RE.fullmatch(val.strip()).groups()[1:] if x)
            edit["rightExpression"] = {"className": "Terrasoft.ParameterExpression", "expressionType": 2, "parameter": {
                "className": "Terrasoft.Parameter", "dataValueType": PARAMETER_VALUE_TYPE, "value": {"value": path, "displayValue": shown}}}
            run["rightExpression"] = {"expressionType": 2, "parameter": {"dataValueType": PARAMETER_VALUE_TYPE, "value": {"value": path}}}
        else:
            value = _typed(val, type_name or "")
            edit["rightExpression"] = {"className": "Terrasoft.ParameterExpression", "expressionType": 2,
                                       "parameter": {"className": "Terrasoft.Parameter", "dataValueType": code, "value": value}}
            run["rightExpression"] = {"expressionType": 2, "parameter": {"dataValueType": code, "value": value}}
        edit_items[key], run_items[key] = edit, run
    edit_group = {"className": "Terrasoft.FilterGroup", "items": edit_items, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root, "key": ""}
    run_group = {"items": run_items, "logicalOperation": 0, "isEnabled": True, "filterType": 6, "rootSchemaName": root}
    return json.dumps({"className": "Terrasoft.FilterGroup", "serializedFilterEditData": json.dumps(edit_group, **_COMPACT),
                       "dataSourceFilters": json.dumps(run_group, **_COMPACT)}, **_COMPACT)
