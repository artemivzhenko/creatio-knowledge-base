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

from ..csharp import CSharpSource, csharp_files
from ..dcm import DcmSchema
from ..entity import EntitySchema
from ..files import read_text
from ..page import PageSchema
from ..process import ProcessSchema
from ..rules import RuleSchema
from ..sqlscript import SqlScript
from ..usertask import UserTaskSchema


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
    """The toolkit object for a schema, SQL script or C# file, or a GenericItem when no toolkit knows the kind."""
    package = Path(package)
    if (package / "SqlScripts" / name / "descriptor.json").is_file():
        return SqlScript(package, name)
    desc_path = package / "Schemas" / name / "descriptor.json"
    if not desc_path.is_file():
        cs = _csharp_file(package, name)
        if cs is not None:
            return CSharpSource(package, cs)
        raise FileNotFoundError(f"{package} has no schema, SQL script or C# file named {name}")
    d = json.loads(read_text(desc_path)[0])["Descriptor"]
    manager = d.get("ManagerName")
    if manager == "SourceCodeSchemaManager" and (package / "Schemas" / name / f"{name}.cs").is_file():
        return CSharpSource(package, package / "Schemas" / name / f"{name}.cs", name, d)
    if manager == "EntitySchemaManager":
        return EntitySchema(package, name)
    if manager == "ProcessSchemaManager":
        return ProcessSchema(package, name)
    if manager == "DcmSchemaManager":
        return DcmSchema(package, name)
    if manager == "ProcessUserTaskSchemaManager":
        return UserTaskSchema(package, name)
    if manager == "AddonSchemaManager" and name.endswith("BusinessRule"):
        return RuleSchema(package, name)
    if manager == "ClientUnitSchemaManager" and _is_freedom_page(package, name):
        return PageSchema(package, name)
    return GenericItem(package, name)


def kind_of(item) -> str:
    if isinstance(item, PageSchema) and getattr(item, "mobile", False):
        return "mobile"
    if isinstance(item, CSharpSource):
        return "source" if item.descriptor is not None else "csharp"
    return {EntitySchema: "object", ProcessSchema: "process", RuleSchema: "rules", PageSchema: "page", SqlScript: "sql", DcmSchema: "dcm",
            UserTaskSchema: "user-task"}.get(type(item)) or item.kind


def summary(item) -> str:
    """The short stats that follow a schema's name at package level."""
    if isinstance(item, EntitySchema):
        cols = item.columns()
        own = sum(1 for c in cols if item.is_own(c))
        return f"{len(cols)} columns ({own} own)" + (f", replacing {item.parent_name}" if item.replacing else f", parent {item.parent_name}")
    if isinstance(item, ProcessSchema):
        return f"{len(item.nodes())} elements, {len(item.params)} params, {len(item.flows())} flows"
    if isinstance(item, RuleSchema):
        return f"{len(item.rules)} rules for {item.target}" + (" (replacing)" if item.replacing else "")
    if isinstance(item, PageSchema):
        d = item.descriptor.data
        of = item.entity or (f"extends {d['Parent']['Name']}" if d.get("ExtendParent") and d.get("Parent") else "no own data source")
        return f"{len(item.elements())} elements, {len(item.attributes)} attributes, " + (f"page of {of}" if item.entity else of)
    if isinstance(item, SqlScript):
        return f"{item.engine}, {item.install_type}, {len(item.depends_on)} deps"
    if isinstance(item, DcmSchema):
        return f"{len(item.stages)} stages, {len(item.elements())} steps, case of {item.entity}" + ("" if item.enabled else " (disabled)")
    if isinstance(item, UserTaskSchema):
        return f"{len(item.params)} params, {len(item.methods())} methods" + (", interactive" if item.interactive else "")
    if isinstance(item, CSharpSource):
        return item.summary()
    files = item.files()
    return f"{len(files)} files, {sum(p.stat().st_size for p in files)} bytes"


def describe_package(package: Path | str, kind: str = "") -> str:
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
    if kind and not body:
        body = [f"  (no {kind} items; kinds: object, process, rules, page, sql, client, addon, source, csharp, dcm, user-task)"]
    return "\n".join(lines + body)


def _caption(item) -> str:
    res = getattr(item, "resources", None)
    caption = (res.get("Caption") or "") if res is not None else ""
    if caption:
        return caption
    d = getattr(item, "descriptor", None)
    data = d.data if hasattr(d, "data") else (d or {})
    return data.get("Caption", "") if isinstance(data, dict) else ""


def describe_schema(package: Path | str, name: str) -> str:
    """The toolkit's summary of one schema: what `inspect` prints."""
    return open_item(package, name).describe()


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
