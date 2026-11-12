"""The condition grammar every toolkit reads: `UsrAmount > 100; UsrStatus is not null; UsrType = sys:CurrentUser`.

`parse` turns the text into `Condition`s with one canonical operator name each; a consumer maps those names to its own
codes (`filters.OP_CODE`, `rules.model.OPS`, DCM's `==`) with the table it already has.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# canonical operator -> every spelling the text form accepts (the symbols, the filter words, the rule spec's names)
SPELLINGS = {
    "eq": ("==", "=", "equal"),
    "ne": ("!=", "<>", "not-equal"),
    "lt": ("<", "less"),
    "le": ("<=", "less-or-equal"),
    "gt": (">", "greater"),
    "ge": (">=", "greater-or-equal"),
    "contains": ("contains", "contain"),
    "not-contains": ("not contains", "not-contains", "not-contain"),
    "starts": ("starts with",),
    "ends": ("ends with",),
    "empty": ("is null", "empty"),
    "filled": ("is not null", "filled"),
}
UNARY = ("empty", "filled")
_CANONICAL = {spelling: op for op, spellings in SPELLINGS.items() for spelling in spellings}
_WORDS = "|".join(re.escape(s) for s in sorted(_CANONICAL, key=len, reverse=True) if s[-1].isalpha())
_SYMBOLS = "|".join(re.escape(s) for s in sorted(_CANONICAL, key=len, reverse=True) if not s[-1].isalpha())
# a word operator needs a space before it and no word character after it; a symbol may touch its neighbours
_CONDITION_RE = re.compile(rf"^\s*([\w.]+)(?:\s+({_WORDS})(?![\w-])|\s*({_SYMBOLS}))\s*(.*?)\s*$", re.I)
_PARAM_RE = re.compile(r"\{Parameter:(\w+)\}")
_RECORD_RE = re.compile(r"\{Record:(\w+)\}")


@dataclass(frozen=True)
class Const:
    """A literal; `quoted` says the author quoted it, so it is text whatever it looks like."""
    text: str
    quoted: bool = False


@dataclass(frozen=True)
class Param:
    """`{Parameter:X}`: a parameter of the process or case."""
    name: str


@dataclass(frozen=True)
class Column:
    """`{Record:Col}` or `attr:X`: a column of the record, an attribute of the page."""
    path: str


@dataclass(frozen=True)
class Sys:
    """`sys:CurrentUser`: a system value."""
    name: str


@dataclass(frozen=True)
class Setting:
    """`setting:Code`: a system setting."""
    code: str


@dataclass(frozen=True)
class Null:
    """The missing right side of `empty` and `filled`."""


Operand = Const | Param | Column | Sys | Setting | Null


@dataclass(frozen=True)
class Condition:
    """`left op right`; `op` is a canonical name from SPELLINGS, or a raw word a stored filter has no canonical name for."""
    left: str
    op: str
    right: Operand = Null()
    enabled: bool = True


def operand(text: str) -> Operand:
    """The right side: a quoted literal, `{Parameter:X}`, `{Record:C}` / `attr:X`, `sys:X`, `setting:X`, or a plain literal."""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        if text[0] == '"':  # the form `operand_text` writes: JSON escapes undone
            try:
                return Const(json.loads(text), quoted=True)
            except ValueError:
                pass
        return Const(text[1:-1], quoted=True)
    for pattern, make in ((_PARAM_RE, Param), (_RECORD_RE, Column)):
        m = pattern.fullmatch(text)
        if m:
            return make(m.group(1))
    prefix, _, rest = text.partition(":")
    if rest and prefix.lower() == "attr":
        return Column(rest)
    if rest and prefix.lower() == "sys":
        return Sys(rest)
    if rest and prefix.lower() == "setting":
        return Setting(rest)
    return Const(text)


def _split(text: str) -> list[str]:
    """Split on `;` outside quotes."""
    parts, start, quote = [], 0, ""
    for i, ch in enumerate(text):
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'" and not (i and text[i - 1].isalnum()):  # O'Brien: an apostrophe inside a word is not a quote
            quote = ch
        elif ch == ";":
            parts.append(text[start:i])
            start = i + 1
    return parts + [text[start:]]


def parse(text: str) -> list[Condition]:
    """`"UsrAmount > 100; UsrStatus is not null"` -> [Condition, ...], ANDed; `;` outside quotes separates, quotes around a literal are dropped."""
    out = []
    for part in [p for p in _split(text) if p.strip()]:
        m = _CONDITION_RE.match(part)
        if not m:
            raise ValueError(f"cannot read condition {part.strip()!r}; expected '<Column> <op> <value>' with op one of "
                             f"{', '.join(_CANONICAL)}")
        left, op, right = m.group(1), m.group(2) or m.group(3), m.group(4)
        canonical = _CANONICAL[op.lower()]
        out.append(Condition(left, canonical, Null() if canonical in UNARY and not right else operand(right)))
    return out
