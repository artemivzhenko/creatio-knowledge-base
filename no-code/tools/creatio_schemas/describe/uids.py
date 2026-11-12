"""A UId to what it names and back, over a workspace: a schema, a column, a process element or parameter.

    resolve(path, "ef3edc7c-...")                     column UsrOrder.UsrAmount  (object UsrOrder in UsrPkg)
    resolve(path, "UsrOrder.UsrAmount")               the UId
    resolve(path, "[Element:{59bd...}].[Parameter:{c7df...}]")   every UId of the text named, then the text with names

What a site stores (meta paths, filters, the designer's metadata) carries bare UIds; this is the reverse of
`ExpressionCodec.encode` for any text, not only a process's own. A UId of a lookup row or a system record is
not in a workspace: the answer says so and points at the environment.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..files import is_uid
from ..process import ProcessSchema, short_type
from ..workspace import Workspace
from .index import packages_of

UID_RE = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")


def _package(s: dict) -> str:
    return s["dir"].parent.parent.name


class Names:
    """Lazy reverse maps over one workspace: built only as far as a question needs them."""

    def __init__(self, ws: Workspace):
        self.ws = ws
        self._columns: dict[str, tuple[str, str]] | None = None
        self._process: dict[str, str] | None = None

    def columns(self) -> dict[str, tuple[str, str]]:
        if self._columns is None:
            self._columns = {}
            for name in dict.fromkeys(s["name"] for s in self.ws.schemas if s["manager"] == "EntitySchemaManager"):
                for col, uid in self.ws.column_uids(name).items():
                    self._columns.setdefault(uid, (name, col))
        return self._columns

    def process_items(self) -> dict[str, str]:
        """uid -> `process P element E (Kind)` / `process P element E parameter X` / `process P parameter X`."""
        if self._process is None:
            self._process = {}
            for s in self.ws.schemas:
                if s["manager"] != "ProcessSchemaManager":
                    continue
                try:
                    p = ProcessSchema(s["dir"].parent.parent, s["name"])
                except (OSError, ValueError, KeyError):
                    continue
                for x in p.params:
                    self._process.setdefault(x["UId"].lower(), f"process {p.name} parameter {x['A2']}")
                for e in p.elements:
                    self._process.setdefault(e["UId"].lower(), f"process {p.name} element {e['A2']} ({short_type(e).replace('ProcessSchema', '')})")
                    for x in p.element_params(e):
                        self._process.setdefault(x["UId"].lower(), f"process {p.name} element {e['A2']} parameter {x['A2']}")
        return self._process

    def of(self, uid: str) -> list[str]:
        """Every meaning of a UId in the workspace, most specific first; empty when it is not here."""
        uid = uid.lower()
        out = [f"schema {s['name']} ({(s['manager'] or '?').replace('SchemaManager', '')}) in {_package(s)}" + (" - replacing copy" if s["base"] != s["uid"] else "")
               for s in self.ws.schemas if s["uid"] == uid or s["base"] == uid]
        hit = self.columns().get(uid)
        if hit:
            out.append(f"column {hit[0]}.{hit[1]}")
        if not out:
            hit = self.process_items().get(uid)
            if hit:
                out.append(hit)
        return out

    def short(self, uid: str) -> str:
        """The one word a decoded text shows for a UId: the column, element, parameter or schema name; the UId itself otherwise."""
        hits = self.of(uid)
        if not hits:
            return uid
        words = hits[0].split()
        if words[0] == "column":
            return words[1].split(".", 1)[1]
        if words[0] == "schema":
            return words[1]
        return words[words.index("parameter") + 1] if "parameter" in words else words[words.index("element") + 1]

    def uid_of(self, dotted: str) -> list[str]:
        """`Schema`, `Schema.Column`, `Process.Element`, `Process.Element.Parameter`, `Process.Parameter` -> lines with the UId."""
        head, *rest = dotted.split(".")
        hits = self.ws.find(head)
        if not hits:
            return []
        if not rest:
            return [f"{s['uid']}  schema {s['name']} ({(s['manager'] or '?').replace('SchemaManager', '')}) in {_package(s)}" for s in hits]
        s = hits[0]
        if s["manager"] == "EntitySchemaManager":
            uid = self.ws.column_uids(s["name"]).get(rest[0])
            return [f"{uid}  column {s['name']}.{rest[0]}"] if uid and len(rest) == 1 else []
        if s["manager"] == "ProcessSchemaManager":
            p = ProcessSchema(s["dir"].parent.parent, s["name"])
            el = next((e for e in p.elements if e["A2"] == rest[0]), None)
            if el is None:
                x = next((x for x in p.params if x["A2"] == rest[0]), None)
                return [f"{x['UId'].lower()}  process {p.name} parameter {x['A2']}"] if x and len(rest) == 1 else []
            if len(rest) == 1:
                return [f"{el['UId'].lower()}  process {p.name} element {el['A2']} ({short_type(el).replace('ProcessSchema', '')})"]
            x = next((x for x in p.element_params(el) if x["A2"] == rest[1]), None)
            return [f"{x['UId'].lower()}  process {p.name} element {el['A2']} parameter {x['A2']}"] if x and len(rest) == 2 else []
        return []


def resolve(path: Path | str, text: str) -> str:
    """The answer for a UId, a dotted name, or a text holding UIds (a meta path, a filter, a stack of them)."""
    text = text.strip()
    if not text:
        raise ValueError("give a UId, a dotted name (Schema.Column, Process.Element.Parameter) or a text holding UIds")
    ws = Workspace(packages_of(path)[0])
    names = Names(ws)
    uids = list(dict.fromkeys(m.group(0).lower() for m in UID_RE.finditer(text)))
    if not uids:
        lines = names.uid_of(text)
        return "\n".join(lines) if lines else f"{text}: not in the workspace (a schema, Schema.Column, Process.Element[.Parameter], Process.Parameter)"
    out = []
    for uid in uids:
        hits = names.of(uid)
        out.append(f"{uid}  " + ("; ".join(hits) if hits else "not in the workspace: a lookup row, a system record or another workspace's schema - env_sql finds it"))
    if not is_uid(text):  # a text with UIds in it: the same text, every UId it names replaced by the name
        out.append("")
        out.append(UID_RE.sub(lambda m: names.short(m.group(0).lower()), text))
    return "\n".join(out)
