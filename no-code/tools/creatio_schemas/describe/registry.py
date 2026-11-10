"""The registry of kinds: what the describe layer knows about each kind of package item, in one place.

A `Kind` says how to recognise an item (`opens`), how to build it (`make`), its one-line summary and
the query topics it answers. `open_item`, `kind_of`, `summary`, `topics_of` and (later) the CLI read
this list and nothing else, so adding a kind is one `register(Kind(...))` - the kind's own module
stays unaware of the describe layer. Order matters: the first kind whose `opens` says yes wins, so
the specific ones come before the generic `source`/`client` fallbacks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from ..classicui import ClassicSchema
from ..csharp import CSharpSource
from ..data import DataBinding
from ..dcm import DcmSchema
from ..entity import EntitySchema
from ..files import read_text
from ..page import PageSchema
from ..process import ProcessSchema
from ..rules import RuleSchema
from ..sqlscript import SqlScript
from ..usertask import UserTaskSchema
from . import queries as q
from .core import GenericItem, _csharp_file, _is_freedom_page


@dataclass
class Kind:
    name: str
    cls: type
    opens: Callable[[Path, str, dict | None], bool]  # (package, item name, descriptor of Schemas/<name> or None) -> is this kind?
    make: Callable[[Path, str], object]
    summary: Callable[[object], str]
    topics: dict = field(default_factory=dict)
    # a kind whose instances may report a different kind name (a PageSchema that is a mobile page)
    rename: Callable[[object], str] | None = None
    # the kind's CLI, relative to no-code/tools (creatio.py <folder> ... dispatches to it); None for kinds read by describe only
    tool: str | None = None


def _manager(descriptor: dict | None) -> str | None:
    return (descriptor or {}).get("ManagerName")


def _descriptor(package: Path, name: str) -> dict:
    return json.loads(read_text(package / "Schemas" / name / "descriptor.json")[0])["Descriptor"]


def _entity_summary(item: EntitySchema) -> str:
    cols = item.columns()
    own = sum(1 for c in cols if item.is_own(c))
    return f"{len(cols)} columns ({own} own)" + (f", replacing {item.parent_name}" if item.replacing else f", parent {item.parent_name}")


def _page_summary(item: PageSchema) -> str:
    d = item.descriptor.data
    of = item.entity or (f"extends {d['Parent']['Name']}" if d.get("ExtendParent") and d.get("Parent") else "no own data source")
    return f"{len(item.elements())} elements, {len(item.attributes)} attributes, " + (f"page of {of}" if item.entity else of)


def _files_summary(item) -> str:
    files = item.files()
    return f"{len(files)} files, {sum(p.stat().st_size for p in files)} bytes"


KINDS: list[Kind] = [
    Kind("sql", SqlScript, lambda p, n, d: d is None and (p / "SqlScripts" / n / "descriptor.json").is_file(), SqlScript,
         lambda s: f"{s.engine}, {s.install_type}, {len(s.depends_on)} deps", q.SQL, tool="sqlscripts/sqlscripts.py"),
    Kind("data", DataBinding, lambda p, n, d: d is None and (p / "Data" / n / "descriptor.json").is_file(), DataBinding,
         lambda b: b.summary(), q.DATA, tool="data/data.py"),
    Kind("csharp", CSharpSource, lambda p, n, d: d is None and _csharp_file(p, n) is not None, lambda p, n: CSharpSource(p, _csharp_file(p, n)),
         lambda c: c.summary(), q.CSHARP),
    Kind("source", CSharpSource, lambda p, n, d: _manager(d) == "SourceCodeSchemaManager" and (p / "Schemas" / n / f"{n}.cs").is_file(),
         lambda p, n: CSharpSource(p, p / "Schemas" / n / f"{n}.cs", n, _descriptor(p, n)), lambda c: c.summary(), q.CSHARP),
    Kind("object", EntitySchema, lambda p, n, d: _manager(d) == "EntitySchemaManager", EntitySchema, _entity_summary, q.OBJECT, tool="objects/objects.py"),
    Kind("process", ProcessSchema, lambda p, n, d: _manager(d) == "ProcessSchemaManager", ProcessSchema,
         lambda s: f"{len(s.nodes())} elements, {len(s.params)} params, {len(s.flows())} flows", q.PROCESS, tool="process/proc.py"),
    Kind("dcm", DcmSchema, lambda p, n, d: _manager(d) == "DcmSchemaManager", DcmSchema,
         lambda s: f"{len(s.stages)} stages, {len(s.elements())} steps, case of {s.entity}" + ("" if s.enabled else " (disabled)"), q.DCM, tool="dcm/dcm.py"),
    Kind("user-task", UserTaskSchema, lambda p, n, d: _manager(d) == "ProcessUserTaskSchemaManager", UserTaskSchema,
         lambda s: f"{len(s.params)} params, {len(s.methods())} methods" + (", interactive" if s.interactive else ""), q.USERTASK, tool="usertask/usertask.py"),
    Kind("rules", RuleSchema, lambda p, n, d: _manager(d) == "AddonSchemaManager" and n.endswith("BusinessRule"), RuleSchema,
         lambda s: f"{len(s.rules)} rules for {s.target}" + (" (replacing)" if s.replacing else ""), q.RULES, tool="rules/rules.py"),
    Kind("page", PageSchema, lambda p, n, d: _manager(d) == "ClientUnitSchemaManager" and _is_freedom_page(p, n), PageSchema, _page_summary, q.PAGE,
         rename=lambda s: "mobile" if getattr(s, "mobile", False) else "page", tool="pages/pages.py"),
    Kind("classic", ClassicSchema, lambda p, n, d: _manager(d) == "ClientUnitSchemaManager" and ClassicSchema.is_classic(p, n), ClassicSchema,
         lambda s: s.summary(), q.CLASSIC, tool="classicui/classicui.py"),
]
FALLBACK = Kind("schema", GenericItem, lambda p, n, d: d is not None, GenericItem, _files_summary, {}, rename=lambda g: g.kind)


def register(kind: Kind, first: bool = True) -> None:
    """Add a kind; `first` puts it before the existing ones (it then wins ties)."""
    KINDS.insert(0 if first else len(KINDS), kind)


def unregister(name: str) -> None:
    KINDS[:] = [k for k in KINDS if k.name != name]


def kind_for(item) -> Kind:
    """The registry entry of an item: the one that opened it (`open_item` stamps it), else by its class and - for
    CSharpSource - by whether it is a schema."""
    stamped = getattr(item, "_kind", None)
    if stamped is not None and stamped in KINDS:
        return stamped
    for k in KINDS:
        if type(item) is k.cls or (isinstance(item, k.cls) and k.cls is not CSharpSource):
            if k.cls is CSharpSource and (k.name == "source") != (getattr(item, "descriptor", None) is not None):
                continue
            return k
    return FALLBACK


def kind_name(item) -> str:
    k = kind_for(item)
    return k.rename(item) if k.rename else k.name


def find_kind(package: Path, name: str, descriptor: dict | None) -> Kind | None:
    return next((k for k in KINDS if k.opens(package, name, descriptor)), FALLBACK if descriptor is not None else None)
