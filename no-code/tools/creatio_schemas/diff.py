"""The line diff a package stores for a schema that has a parent (entities, replacing addons, replacing pages).

    = MetaData.Schema.<path> <json>    the key exists in the parent, the value differs
    + MetaData.Schema.<path> <json>    the key is new; on a list path the value is a new item
    - MetaData.Schema.<path>           the key (or list item) of the parent is removed
    ~ MetaData.Schema.<path> [uids]    the order of a list, by item UId

A path is dotted keys; `["uid"]` selects the list item with that UId. Values are JSON and may
span lines. `apply` turns parent + diff into the effective schema; `set` / `delete` change one
path and pick the operation by comparing with the parent, the way the platform writes them.
Untouched lines keep their bytes.
"""

from __future__ import annotations

import copy
import json
import re

from .files import CRLF, dump_json
from .workspace import parse_diff

ROOT = "MetaData.Schema"
_TOKEN_RE = re.compile(r'\["([^"]+)"\]|([^.\[]+)')
_MISSING = object()


def tokens(path: str) -> list:
    """'MetaData.Schema.D2.["u"].E16' -> ['D2', ('u',), 'E16'] (a tuple is a UId selector); the root is dropped."""
    if path == ROOT:
        return []
    if not path.startswith(ROOT + "."):
        raise ValueError(f"not a schema path: {path}")
    return [(m.group(1),) if m.group(1) else m.group(2) for m in _TOKEN_RE.finditer(path[len(ROOT) + 1:])]


def path_of(*parts) -> str:
    """path_of("D2", ("uid",), "E16") -> 'MetaData.Schema.D2.["uid"].E16'."""
    return ".".join([ROOT] + [f'["{p[0]}"]' if isinstance(p, tuple) else p for p in parts])


def _child(node, token):
    if isinstance(token, tuple):
        if not isinstance(node, list):
            return _MISSING
        return next((i for i in node if isinstance(i, dict) and str(i.get("UId", "")).lower() == token[0].lower()), _MISSING)
    return node.get(token, _MISSING) if isinstance(node, dict) else _MISSING


def get(schema: dict, path: str, default=None):
    node = schema
    for t in tokens(path):
        node = _child(node, t)
        if node is _MISSING:
            return default
    return node


def has(schema: dict, path: str) -> bool:
    return get(schema, path, _MISSING) is not _MISSING


def apply_op(schema: dict, op: str, path: str, value) -> None:
    """Apply one line to an effective schema (in place). Raises KeyError when the path does not resolve."""
    toks = tokens(path)
    *head, last = toks
    node = schema
    for t in head:
        nxt = _child(node, t)
        if nxt is _MISSING:
            if isinstance(t, tuple) or op == "-":
                raise KeyError(f"{path}: {t} not found")
            nxt = node.setdefault(t, {})
        node = nxt
    if op == "-":
        if isinstance(last, tuple):
            item = _child(node, last)
            if item is _MISSING:
                raise KeyError(f"{path}: item not found")
            node.remove(item)
        elif isinstance(node, dict):
            node.pop(last, None)
        return
    if op == "~":
        items = node.get(last, []) if isinstance(node, dict) else []
        rank = {u.lower(): i for i, u in enumerate(value)}
        items.sort(key=lambda i: rank.get(str(i.get("UId", "")).lower(), len(rank)))
        return
    if isinstance(last, tuple):
        item = _child(node, last)
        if item is _MISSING:
            node.append(value)
        else:
            item.clear()
            item.update(value)
        return
    current = node.get(last, _MISSING)
    if op == "+" and isinstance(current, list) and isinstance(value, dict):
        current.append(value)  # a new item of a parent list
    elif op == "+" and current is _MISSING and isinstance(value, dict) and "UId" in value and last not in ("D36", "D35", "D20", "EG1"):
        node[last] = [value]  # the first item of a list the parent does not have
    else:
        node[last] = value


class SchemaDiff:
    """The lines of a diff metadata.json: [op, path, raw value text, parsed value]."""

    def __init__(self, text: str, nl: str = CRLF):
        self.nl = nl
        self.lines: list[list] = []
        for op, path, raw in parse_diff(text.replace("\r\n", "\n").replace("\n", "\r\n")):
            self.lines.append([op, path, raw, json.loads(raw) if raw else None])

    # -- read ---------------------------------------------------------------- #

    def apply(self, parent: dict) -> dict:
        """parent schema + these lines -> effective schema (a new dict). Lines whose path does not resolve in the
        parent (the parent known here is not the whole hierarchy the platform merges) go to `self.unresolved`."""
        schema = copy.deepcopy(parent)
        self.unresolved = []
        for op, path, _, value in self.lines:
            try:
                apply_op(schema, op, path, copy.deepcopy(value))
            except KeyError:
                self.unresolved.append(path)
        return schema

    def find(self, path: str, op: str | None = None) -> list | None:
        return next((ln for ln in self.lines if ln[1] == path and (op is None or ln[0] == op)), None)

    def value(self, path: str, default=None):
        ln = self.find(path)
        return ln[3] if ln and ln[0] != "-" else default

    def added_items(self, list_path: str) -> list[dict]:
        """Items this diff adds to a list (`+ <list_path> {item}`), as live dicts: editing them edits the line."""
        return [ln[3] for ln in self.lines if ln[0] == "+" and ln[1] == list_path and isinstance(ln[3], dict)]

    # -- change -------------------------------------------------------------- #

    def _drop(self, path: str, prefix: bool = False) -> None:
        self.lines = [ln for ln in self.lines if not (ln[1] == path or prefix and ln[1].startswith(path + "."))]

    def put(self, op: str, path: str, value, before: str | None = None) -> None:
        """Insert a line as given (before the `~` line of `before` when there is one)."""
        line = [op, path, None, value]
        at = next((i for i, ln in enumerate(self.lines) if before and ln[1] == before and ln[0] == "~"), None)
        self.lines.insert(len(self.lines) if at is None else at, line)

    def set(self, parent: dict, path: str, value) -> None:
        """Make the effective value at `path` equal `value`: no line when the parent already has it, `=` when the
        parent has another value, `+` when the parent lacks the key."""
        self._drop(path)
        if has(parent, path):
            if get(parent, path) != value:
                self.put("=", path, value)
        else:
            self.put("+", path, value)

    def delete(self, parent: dict, path: str) -> None:
        """Make the key absent in the effective schema."""
        self._drop(path)
        if has(parent, path):
            self.put("-", path, None)

    def add_item(self, list_path: str, item: dict) -> None:
        """A new list item; when the diff orders the list, the item goes last in the order too."""
        order = self.find(list_path, "~")
        self.put("+", list_path, item, before=list_path if order else None)
        if order:
            order[3] = order[3] + [item["UId"]]
            order[2] = None

    def remove_item(self, list_path: str, uid: str) -> None:
        """Remove an item this diff added, every line about it and its place in the order."""
        self.lines = [ln for ln in self.lines if not (ln[0] == "+" and ln[1] == list_path and isinstance(ln[3], dict) and ln[3].get("UId") == uid)]
        self._drop(f'{list_path}.["{uid}"]', prefix=True)
        order = self.find(list_path, "~")
        if order:
            order[3] = [u for u in order[3] if u != uid]
            order[2] = None

    # -- write --------------------------------------------------------------- #

    def render(self) -> str:
        parts = []
        for ln in self.lines:
            op, path, raw, value = ln
            if raw is not None and (json.loads(raw) if raw else None) != value:
                raw = None  # an item edited in place
            if raw is None and op != "-":
                raw = dump_json(value) if isinstance(value, dict) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            parts.append(f"{op} {path}" + (f" {raw}" if raw else ""))
        return CRLF.join(parts).replace(CRLF, self.nl)
