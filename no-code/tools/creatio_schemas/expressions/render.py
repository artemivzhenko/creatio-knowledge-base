"""Conditions back to text: `UsrAmount > 100 and UsrStatus is not null`, nested groups in parentheses.

Filters, rules and DCM steps store conditions in three shapes; each builds `Condition`s (and `Group`s) from its own and
prints them here, so one idea reads one way in every answer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from .conditions import UNARY, Column, Condition, Const, Null, Param, Setting, Sys

SYMBOL = {"eq": "=", "ne": "!=", "lt": "<", "le": "<=", "gt": ">", "ge": ">=", "contains": "contains", "not-contains": "not contains",
          "starts": "starts with", "ends": "ends with", "empty": "is null", "filled": "is not null"}


@dataclass(frozen=True)
class Group:
    """Conditions joined by `and` / `or`; a group inside a group is printed in parentheses."""
    items: tuple
    logic: str = "and"


def operand_text(right) -> str:
    """The right side as the grammar writes it: a literal the author quoted, or one holding a `;`, is quoted (JSON escapes)."""
    if isinstance(right, Const):
        return json.dumps(right.text, ensure_ascii=False) if right.quoted or ";" in right.text else right.text
    if isinstance(right, Param):
        return f"{{Parameter:{right.name}}}"
    if isinstance(right, Column):
        return f"attr:{right.path}"
    if isinstance(right, Sys):
        return f"sys:{right.name}"
    if isinstance(right, Setting):
        return f"setting:{right.code}"
    return ""


def describe(item) -> str:
    """One `Condition`, a `Group`, or a list of either (ANDed)."""
    if isinstance(item, (list, tuple)):
        item = Group(tuple(item))
    if isinstance(item, Group):
        glue = f" {item.logic} "
        parts = []
        for sub in item.items:
            inner = describe(sub)
            parts.append(f"({inner})" if isinstance(sub, Group) and inner else inner)
        return glue.join(p for p in parts if p)
    op = SYMBOL.get(item.op, item.op)
    text = f"{item.left} {op} {operand_text(item.right)}".rstrip() if item.op not in UNARY else f"{item.left} {op}"
    return text + ("" if item.enabled else " (disabled)")
