"""The describe layer: what a package holds, what a schema is, and one part of it on request.

Reading a schema file costs many times the tokens its summary does, so an agent asks this
module instead: `describe_package` (one line per schema), `describe_schema` (the summary the
toolkit's `inspect` prints) and `describe_item` (one part, through a small query grammar:
`<topic> [<name>] [key=value ...]`). Nothing is printed that was not asked for.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

from ..csharp import csharp_files
from ..data import DataBinding
from ..files import read_text


class QueryError(ValueError):
    """A query the item cannot answer; the message lists what it can."""


class GenericItem:
    """A schema without a toolkit yet: its descriptor and its files, nothing parsed."""

    kind = "schema"

    def __init__(self, package: Path, name: str):
        self.package = Path(package)
        self.name = name
        self.dir = self.package / "Schemas" / name
        self.descriptor = json.loads(read_text(self.dir / "descriptor.json")[0])["Descriptor"]
        self.kind = _KIND_LABEL.get(self.descriptor.get("ManagerName"), "schema")
        if self.kind == "client" and "Mobile" in name:
            self.kind = "mobile"
        if self.kind == "addon":
            props = self.dir / "properties.json"
            if props.is_file():
                addon = json.loads(read_text(props)[0]).get("Properties", {}).get("AddonName")
                self.kind = {"RelatedPage": "related-page", "EntityConnections": "connections"}.get(addon, f"addon:{addon}" if addon else "addon")

    def files(self) -> list[Path]:
        return sorted(p for p in self.dir.rglob("*") if p.is_file())

    def describe(self) -> str:
        d = self.descriptor
        lines = [f"{self.name}: {d.get('Caption', '')!r}  {self.kind} ({d.get('ManagerName')})"
                 + (f", extends {(d.get('Parent') or {}).get('Name')}" if d.get("ExtendParent") else "")]
        for p in self.files():
            lines.append(f"    {p.relative_to(self.dir).as_posix():<40} {p.stat().st_size:>8} bytes")
        lines.append("  (no toolkit for this kind yet: ask for 'files' or read a file by name)")
        return "\n".join(lines)


_KIND_LABEL = {
    "EntitySchemaManager": "object",
    "ProcessSchemaManager": "process",
    "ClientUnitSchemaManager": "client",
    "AddonSchemaManager": "addon",
    "SourceCodeSchemaManager": "source",
    "ProcessUserTaskSchemaManager": "user-task",
    "PageSchemaManager": "page-v1",
    "DcmSchemaManager": "dcm",
    "ImageListSchemaManager": "images",
}


def _is_freedom_page(package: Path, name: str) -> bool:
    body = package / "Schemas" / name / f"{name}.js"
    if not body.is_file():
        return False
    # Only a body with the designer's marker sections is a Freedom UI page the toolkit can parse;
    # mobile pages also say viewConfigDiff but carry no markers.
    text = read_text(body)[0]
    return "/**SCHEMA_VIEW_CONFIG_DIFF*/" in text or (text.lstrip().startswith("{") and '"viewConfigDiff"' in text[:2000])


def _csharp_file(package: Path, name: str) -> Path | None:
    """A plain C# file named by its path (`Files/cs/X.cs`) or its file name (`X.cs`, `X`) anywhere under Files."""
    direct = package / name
    if direct.suffix.lower() == ".cs" and direct.is_file():
        return direct
    stem = Path(name).name
    stem = stem if stem.lower().endswith(".cs") else stem + ".cs"
    hits = [p for p in csharp_files(package) if p.name.lower() == stem.lower()]
    return hits[0] if len(hits) == 1 else None


def open_item(package: Path | str, name: str):
    """The toolkit object for a package item - the first registered kind that recognises it (registry.KINDS), or a
    GenericItem for a schema no toolkit knows."""
    from .registry import find_kind

    package = Path(package)
    desc_path = package / "Schemas" / name / "descriptor.json"
    descriptor = json.loads(read_text(desc_path)[0])["Descriptor"] if desc_path.is_file() else None
    kind = find_kind(package, name, descriptor)
    if kind is None:
        raise FileNotFoundError(f"{package} has no schema, SQL script, data binding or C# file named {name}")
    item = kind.make(package, name)
    item._kind = kind  # the entry that opened it: two kinds may share a class (a generic item, a demo kind over one schema)
    return item


def kind_of(item) -> str:
    from .registry import kind_name

    return kind_name(item)


def summary(item) -> str:
    """The short stats that follow a schema's name at package level."""
    from .registry import kind_for

    return kind_for(item).summary(item)


# The output contract: a list answer shows at most DEFAULT_LIMIT lines, then one TAIL line; `limit=0` means all.
DEFAULT_LIMIT = 40
TAIL = "  ... {more} more; add limit=0 for all"


def describe_package(package: Path | str, kind: str = "", limit: int = DEFAULT_LIMIT) -> str:
    """One line per schema and SQL script: kind, name, caption, stats. `kind` filters (object, process, page, rules, sql, client, source ...).

    Answered from the package index (see index.py), which checks itself against the disk first."""
    from .index import PackageIndex

    package = Path(package)
    if not (package / "descriptor.json").is_file():
        raise FileNotFoundError(f"{package} is not a package folder (no descriptor.json)")
    idx = PackageIndex(package)
    idx.refresh()
    d = idx.data
    lines = [f"{d.get('package')} {d.get('version') or ''}  {len(idx.schemas)} items" + (f"  depends on {', '.join(d['depends_on'])}" if d.get("depends_on") else "")]
    body = idx.lines(kind)
    if kind == "data":  # bindings are indexed by files only; their summary is read on request (one folder each)
        for name in sorted(idx.data.get("data", {})):
            try:
                body.append(f"  {'data':<9} {name:<36} {'':<34} {DataBinding(package, name).summary()}")
            except (OSError, ValueError, KeyError) as exc:
                body.append(f"  {'data':<9} {name:<36} {'':<34} cannot read: {exc}")
    if kind and not body:
        body = [f"  (no {kind} items; kinds: object, process, rules, page, sql, client, addon, source, csharp, dcm, user-task, data)"]
    return "\n".join(lines + cut(body, limit))


def _caption(item) -> str:
    res = getattr(item, "resources", None)
    caption = (res.get("Caption") or "") if res is not None else ""
    if caption:
        return caption
    d = getattr(item, "descriptor", None)
    data = d.data if hasattr(d, "data") else (d or {})
    return data.get("Caption", "") if isinstance(data, dict) else ""


def cut(lines: list[str], limit: int = DEFAULT_LIMIT, hint: str = "") -> list[str]:
    """The first `limit` lines (0 = all) and, when something was left out, one tail line saying how much."""
    if limit < 0:
        raise QueryError("limit must be a non-negative integer")
    if limit and len(lines) > limit:
        return lines[:limit] + [TAIL.format(more=len(lines) - limit) + (f"; {hint}" if hint else "")]
    return lines


def describe_schema(package: Path | str, name: str, limit: int = DEFAULT_LIMIT) -> str:
    """The toolkit's summary of one schema: what `inspect` prints, cut to `limit` lines (0 = all) - a part is asked
    for with describe_item, never read from the dump."""
    from .queries import topics_of

    item = open_item(package, name)
    lines = item.describe().splitlines()
    return "\n".join(cut(lines, limit, f"this is the summary - ask describe_item for one part (topics: {', '.join(sorted(topics_of(item)))})"))


def parse_query(query: str) -> tuple[str, str | None, dict[str, str]]:
    """`"elements type=crt.Input parent=X"` -> ("elements", None, {...}); `"element iaName"` -> ("element", "iaName", {})."""
    tokens = shlex.split(query or "")
    if not tokens:
        return "topics", None, {}
    topic, name, filters = tokens[0].lower(), None, {}
    for t in tokens[1:]:
        if "=" in t:
            k, v = t.split("=", 1)
            filters[k.lower()] = v
        elif name is None:
            name = t
        else:
            name += " " + t
    return topic, name, filters


def describe_item(package: Path | str, name: str, query: str) -> str:
    """One part of a schema, chosen by the query. `topics` lists what the schema can answer."""
    from .queries import answer

    item = open_item(package, name)
    topic, arg, filters = parse_query(query)
    return answer(item, topic, arg, filters)
