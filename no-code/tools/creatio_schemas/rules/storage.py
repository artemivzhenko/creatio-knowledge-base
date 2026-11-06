"""The two forms of a rule addon's metadata.json, behind one interface.

OwnStorage   the target was created in this package (or a base target had no rules): full JSON,
             rules in MetaData.Schema.AD4.BRS1.
DiffStorage  the target's addon lives in a base package: a line diff `= | + | - | ~ path [value]`.
             Own rules are `+ ...BRS1 {rule}`, base rules are changed by UId
             (`+ ...BRS1.["uid"].BR4 false` disables, `- ...BRS1.["uid"]` deletes), `~ ...BRS1 [uids]` is the order.

Both render an unchanged file to its original bytes.
"""

from __future__ import annotations

import json

from ..files import CRLF, dump_json
from ..workspace import parse_diff
from .model import RULES_PATH, T_RULES

DEFAULT_VERSION = "8.2.3.1351"


class OwnStorage:
    replacing = False

    def __init__(self, text: str, nl: str = CRLF):
        self.meta = json.loads(text)
        self.nl = nl
        self.schema.setdefault("AD4", {"JI0": T_RULES, "BRS1": []}).setdefault("BRS1", [])

    @property
    def schema(self) -> dict:
        return self.meta["MetaData"]["Schema"]

    @property
    def rules(self) -> list[dict]:
        return self.schema["AD4"]["BRS1"]

    @property
    def version(self) -> str:
        return self.schema.get("B8", DEFAULT_VERSION)

    def append(self, rule: dict) -> None:
        self.rules.append(rule)

    def remove(self, uids: set[str]) -> None:
        self.rules[:] = [r for r in self.rules if r["UId"] not in uids]

    def base_edits(self) -> list[str]:
        return []

    def set_base_enabled(self, uid: str, enabled: bool) -> None:
        raise ValueError("only a replacing addon changes rules of a base addon")

    def remove_base(self, uid: str) -> None:
        raise ValueError("only a replacing addon can remove base rules")

    def render(self) -> str:
        return dump_json(self.meta, self.nl)


class DiffStorage:
    replacing = True

    def __init__(self, text: str, nl: str = CRLF):
        self.nl = nl
        self.ops: list[list] = []  # [op, path, raw value, parsed rule or None, rendering of the rule as read]
        for op, path, value in parse_diff(text.replace("\r\n", "\n").replace("\n", "\r\n")):
            rule = json.loads(value) if op == "+" and path == RULES_PATH else None
            self.ops.append([op, path, value, rule, dump_json(rule) if rule else None])

    @property
    def rules(self) -> list[dict]:
        """Own rules of this addon (base rules are not in the file)."""
        return [o[3] for o in self.ops if o[3] is not None]

    @property
    def version(self) -> str:
        return next((json.loads(v) for _, p, v, *_ in self.ops if p == "MetaData.Schema.B8"), DEFAULT_VERSION)

    def _order(self) -> list | None:
        return next((o for o in self.ops if o[0] == "~" and o[1] == RULES_PATH), None)

    def append(self, rule: dict) -> None:
        order = self._order()
        self.ops.insert(self.ops.index(order) if order else len(self.ops), ["+", RULES_PATH, None, rule, None])
        if order:
            order[2] = dump_json(json.loads(order[2]) + [rule["UId"]])

    def remove(self, uids: set[str]) -> None:
        self.ops = [o for o in self.ops if not (o[3] and o[3]["UId"] in uids)]
        order = self._order()
        if order:
            order[2] = dump_json([u for u in json.loads(order[2]) if u not in uids])

    def base_edits(self) -> list[str]:
        """Lines that change rules of the base addon."""
        return [f"{op} {path} {value.splitlines()[0] if value else ''}".rstrip() for op, path, value, rule, _ in self.ops
                if rule is None and path.startswith(RULES_PATH + ".") or op == "-" and path.startswith(RULES_PATH)]

    def set_base_enabled(self, uid: str, enabled: bool) -> None:
        path = f'{RULES_PATH}.["{uid}"].BR4'
        self.ops = [o for o in self.ops if o[1] != path]
        if not enabled:
            self.ops.append(["+", path, "false", None, None])

    def remove_base(self, uid: str) -> None:
        self.ops.append(["-", f'{RULES_PATH}.["{uid}"]', "", None, None])

    def render(self) -> str:
        parts = []
        for op, path, value, rule, snapshot in self.ops:
            if rule is not None:
                text = dump_json(rule)
                value = value if text == snapshot and value is not None else text  # untouched rules keep their bytes
            parts.append(f"{op} {path}" + (f" {value}" if value else ""))
        return CRLF.join(parts).replace(CRLF, self.nl)


def load_storage(text: str, nl: str) -> OwnStorage | DiffStorage:
    return OwnStorage(text, nl) if text.lstrip().startswith("{") else DiffStorage(text, nl)
