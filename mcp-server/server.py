"""
MCP server exposing the Creatio knowledge base.

All the indexing and ranking lives in kb_index.py; this file is only the MCP
transport plus the tool descriptions the model reads.

Run directly for stdio:  python server.py
"""

from __future__ import annotations

import os
from pathlib import Path

# The SDK renamed FastMCP to MCPServer in mcp 2.0. Both expose the same .tool()
# decorator and .run(), so one shim covers either version.
try:
    from mcp.server.mcpserver import MCPServer as _Server  # mcp >= 2.0
except ImportError:  # pragma: no cover - older SDK
    from mcp.server.fastmcp import FastMCP as _Server  # mcp 1.x

from kb_index import KnowledgeBase, default_root

mcp = _Server(
    "creatio-kb",
    instructions=(
        "Curated Creatio development recipes for this solution: Classic UI (7.x) "
        "pages, details and sections, Freedom UI (8.x) pages and Angular remote "
        "modules, Mobile SDK handler modules, and C# server code. "
        "Search this knowledge base BEFORE writing Creatio code - it carries the "
        "project's idioms, naming rules and known traps that general knowledge "
        "does not have. Start with search_recipes, then get_recipe for the full "
        "example. For C# code, read get_code_style before writing: it holds the "
        "formatting, naming and architecture rules of Creatio platform code. "
        "The Clio area covers the clio CLI (packages, SQL, schemas, pages, apps, "
        "rights, its own MCP server): search_recipes(query, area='Clio') finds the "
        "block skill and the command reference; get_recipe('execute-sql-script') "
        "returns a command's full syntax, options and examples; get_recipe("
        "'clio-sql-and-data') returns the block's workflow and verified traps."
    ),
)

_ROOT: Path = default_root()
_KB: KnowledgeBase | None = None
_FINGERPRINT: tuple[int, float] | None = None


def _fingerprint(root: Path) -> tuple[int, float]:
    """Cheap staleness check: file count plus the newest mtime."""
    count = 0
    newest = 0.0
    for sub in ("Frontend", "Backend", "no-code"):
        base = root / sub
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".js", ".ts", ".cs", ".sql", ".md"):
                count += 1
                newest = max(newest, path.stat().st_mtime)
    return count, newest


def kb() -> KnowledgeBase:
    """Return the index, rebuilding it when the knowledge base changed on disk."""
    global _KB, _FINGERPRINT
    current = _fingerprint(_ROOT)
    if _KB is None or current != _FINGERPRINT:
        _KB = KnowledgeBase(_ROOT)
        _FINGERPRINT = current
    return _KB


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@mcp.tool()
def kb_overview() -> str:
    """
    Map of the Creatio knowledge base: areas, topics and how many recipes each holds.

    Call this first when you do not know what the knowledge base covers. For a
    concrete task, go straight to search_recipes instead.
    """
    base = kb()
    lines = [f"Creatio knowledge base at {base.root}", f"{len(base.recipes)} recipes.", ""]
    for area, topics in base.areas().items():
        lines.append(f"{area} ({sum(topics.values())})")
        for topic, count in topics.items():
            lines.append(f"   {count:>3}  {topic}")
        lines.append("")
    lines.append(
        "Areas: ClassicUI (Creatio 7.x pages, details, sections), "
        "FreedomUI (8.x pages), RemoteModule (Angular custom view elements), "
        "Mobile (Mobile SDK handler modules), Backend (C# server code), SQL, "
        "Clio (the clio CLI: one skill per functional block at the root, one "
        "reference page per command under reference/, and tools/<name> - the "
        "file toolkits that build processes, business rules, objects and SQL "
        "scripts as package files). "
        "RemoteModule and Mobile recipes each sit next to a copyable project "
        "folder named in the recipe header."
    )
    return "\n".join(lines)


@mcp.tool()
def search_recipes(query: str, area: str = "", limit: int = 8) -> str:
    """
    Find knowledge base recipes for a Creatio task, by keyword or by symptom.

    ALWAYS call this before writing Creatio code - the recipes carry the exact
    idioms, the naming rules and the known traps for this codebase, which are not
    guessable from general knowledge.

    query: what you are trying to do, in plain words or as an API name.
           Examples: "filter a lookup field", "run a business process",
           "crt.OpenLookupPageRequest", "make a detail editable",
           "execute sql script", "push package to environment".
    area:  optional filter - "ClassicUI", "FreedomUI", "RemoteModule", "Mobile",
           "Backend", "SQL" or "Clio" (the clio CLI and its MCP server).
           Leave empty to search everything; Classic UI and Freedom UI often have
           a recipe each for the same task, and seeing both tells you which UI
           generation the answer belongs to.
    limit: how many results (default 8).

    Returns a ranked list of ids with titles and summaries. Read a full recipe
    with get_recipe.
    """
    base = kb()
    results = base.search(query, area=area or None, limit=max(1, min(limit, 25)))
    if not results:
        return (
            f'No recipe matched "{query}"'
            + (f" in area {area}" if area else "")
            + ".\nTry fewer or more general words, or call kb_overview to see what exists."
        )

    lines = [f'{len(results)} recipe(s) for "{query}"' + (f" in {area}" if area else "") + ":", ""]
    for recipe, score in results:
        lines.append(f"[{recipe.area}] {recipe.id}   (score {score:.1f})")
        lines.append(f"    {recipe.title}")
        summary = recipe.summary(300)
        if summary:
            lines.append(f"    {summary}")
        lines.append("")
    lines.append("Use get_recipe(<id>) to read the full recipe with its code.")
    return "\n".join(lines)


@mcp.tool()
def get_recipe(recipe_id: str) -> str:
    """
    Return the full text of one recipe: the explanation header and the runnable code.

    recipe_id: the id from search_recipes, for example
               "Frontend/ClassicUI/Fields/HowToFilterLookupField".
               A bare file name is accepted when it is unambiguous; for clio a
               command name ("execute-sql-script"), a block skill name
               ("clio-sql-and-data") or a file toolkit ("tools/objects",
               "tools/pages", "tools/process", "tools/rules", "tools/sqlscripts")
               works directly.

    The code is a template, not a drop-in: schema names, column names and the
    generated attribute suffixes (PDS_Name_a1b2c3d) must be replaced with the
    real ones from the project.
    """
    base = kb()
    recipe = base.get(recipe_id)
    if recipe is None:
        twins = base.same_name(recipe_id)
        if twins:
            lines = [f'"{recipe_id}" exists in more than one area. Pick one:', ""]
            lines += [f"[{r.area}] {r.id}" for r in twins]
            return "\n".join(lines)
        return (
            f'No recipe with id "{recipe_id}". '
            "Use search_recipes to find the right id."
        )
    header = (
        f"# {recipe.title}\n"
        f"area: {recipe.area}"
        + (f" / {recipe.topic}" if recipe.topic else "")
        + f"\nfile: {recipe.rel_path}\n"
        + "-" * 70
        + "\n"
    )
    return header + recipe.source


@mcp.tool()
def find_api(symbol: str, limit: int = 10) -> str:
    """
    Reverse lookup: which recipes use a given Creatio API symbol.

    Use this when you already have a symbol in hand and want to see it used
    correctly - from a code review, an error message, or existing project code.

    symbol: an API name such as "crt.OpenLookupPageRequest", "EntitySchemaQuery",
            "UseAdminRights", "LookupMultiAddMixin", "ProcessModuleUtilities".
            A bare name also matches a dotted one ("OpenLookupPageRequest" finds
            "crt.OpenLookupPageRequest").

    Returns the recipes that mention it, the most frequent user first.
    """
    base = kb()
    hits = base.find_api(symbol, limit=max(1, min(limit, 25)))
    if not hits:
        return (
            f'No recipe mentions "{symbol}". '
            "It may be spelled differently - try search_recipes with a description instead."
        )
    lines = [f'Recipes using "{symbol}":', ""]
    for recipe, count in hits:
        lines.append(f"[{recipe.area}] {recipe.id}   ({count} mention(s))")
        lines.append(f"    {recipe.title}")
    lines.append("")
    lines.append("Use get_recipe(<id>) to read one.")
    return "\n".join(lines)


@mcp.tool()
def list_recipes(area: str = "", topic: str = "") -> str:
    """
    Browse recipe ids and titles, optionally narrowed to an area and a topic.

    area:  "ClassicUI", "FreedomUI", "RemoteModule", "Mobile", "Backend", "SQL" or "Clio".
    topic: a folder inside the area, e.g. "Details", "BaseMethods", "ESQ",
           "reference" (clio command pages; the block skills sit at the root).
           Call kb_overview to see the available topics.

    Prefer search_recipes when you have a task in mind; this tool is for
    surveying what exists.
    """
    base = kb()
    items = base.list(area=area or None, topic=topic or None)
    if not items:
        return (
            "Nothing matched"
            + (f" area={area}" if area else "")
            + (f" topic={topic}" if topic else "")
            + ". Call kb_overview to see the available areas and topics."
        )
    lines = [f"{len(items)} recipe(s):", ""]
    for recipe in items:
        lines.append(f"[{recipe.area}] {recipe.id}")
        lines.append(f"    {recipe.title}")
    return "\n".join(lines)


@mcp.tool()
def get_code_style(section: str = "") -> str:
    """
    The C# code style and architecture guide for Creatio back-end code.

    Read it BEFORE writing or reviewing C# for Creatio: formatting (tabs, CRLF,
    #region layout), naming, DI via [DefaultBinding], error handling, logging,
    concurrency, XML docs, and a review checklist. Recipes show WHAT to call;
    this guide says how the code must look.

    section: optional - a section number ("4") or words from its heading
             ("logging", "review checklist"). Empty returns the whole guide.
    """
    text = kb().code_style(section)
    if text is None:
        return "No CREATIO_CODE_STYLE.md next to the knowledge base."
    if not text:
        return f'No section matches "{section}". Call get_code_style() with no argument to see the headings.'
    return text


def _tools_path() -> None:
    import sys
    tools = str(_ROOT / "no-code" / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)


@mcp.tool()
def describe_package(package: str, kind: str = "") -> str:
    """
    What a Creatio package holds, one line per schema and SQL script: kind, name,
    caption, counts (columns, elements, rules, page elements) and the parent or the
    replaced base. Call this BEFORE reading any file of a package.

    package: the package folder, e.g. C:/work/packages/UsrPkg (a clio workspace package).
    kind:    optional filter - object, process, rules, page, sql, client, addon, source, csharp, dcm, user-task.
             C# files under Files/cs are listed as `csharp` by signatures (roles, method count); source code schemas as `source`.
    """
    _tools_path()
    from creatio_schemas.describe import describe_package as _dp
    try:
        return _dp(package, kind)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def describe_schema(package: str, schema: str) -> str:
    """
    The summary of one schema - columns and flags of an object, elements, parameters
    and flows of a process, rules of a rule addon, elements and data sources of a
    Freedom UI page, engine and dependencies of a SQL script. 6x-40x fewer tokens than
    the schema's files; use describe_item for one part of it.
    """
    _tools_path()
    from creatio_schemas.describe import describe_schema as _ds
    try:
        return _ds(package, schema)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def describe_item(package: str, schema: str, query: str = "topics") -> str:
    """
    One part of a schema, chosen by a query "<topic> [<name>] [key=value ...]";
    "topics" lists what the schema can answer. Examples:
      object : "columns type=Lookup", "column UsrAmount", "flags", "base"
      process: "elements kind=FormulaTask", "element ReadOrders", "params", "flows from=Start", "script Calc"
      rules  : "rules", "rule <name>"
      dcm    : "stages", "stage Stage1", "steps stage=Stage1", "step DcmElement1", "moves from=Stage1", "filter"
      user task: "params", "param RecordId", "methods", "method InternalExecute", "source"
      C#     : (schema name, or "Files/cs/X.cs" / "X.cs" / "X") "classes", "members UsrService kind=method visibility=public",
               "member UsrService.GetLabel" (one body), "usings", "regions", "operations" (ESQ, raw SQL, SysSettings,
               process start, HTTP ... with line numbers), "find GetTypedColumnValue"
      page   : "sections", "elements parent=SideAreaProfileContainer", "element UsrName",
               "attributes bound=true", "data-sources", "handlers", "handler crt.SaveRecordRequest",
               "validators", "converters", "containers", "find <text>"
      any    : "files", "resources culture=uk-UA", "resource Caption"
    Nothing is returned that was not asked for: a page is a database, this is the query.
    """
    _tools_path()
    from creatio_schemas.describe import QueryError, describe_item as _di
    try:
        return _di(package, schema, query)
    except (FileNotFoundError, KeyError, ValueError, QueryError) as e:
        return f"error: {e.args[0] if e.args else e}"



@mcp.tool()
def index_workspace(path: str, rebuild: bool = False) -> str:
    """
    Build or refresh the package index - the project's knowledge-base file
    (<workspace>/.creatio-index/<Package>.json): for every schema its kind, caption,
    summary, files and the schemas it refers to. `path` is a clio workspace root, a
    packages folder or one package. The index checks itself against the disk on every
    describe_* / find_schema call, so run this only after a `clio pull-pkg` to see what
    changed, or with rebuild=True to start over.
    """
    _tools_path()
    from creatio_schemas.describe import index_workspace as _iw
    try:
        return _iw(path, rebuild)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def find_schema(path: str, schema: str) -> str:
    """
    Where a schema lives and what touches it, without searching: the package, kind,
    summary, every file with its absolute path, the schemas it refers to and the schemas
    and data bindings that refer to it (across the workspace). Call this before reading
    or changing a schema: it gives the files to open and the impact of the change.
    `path` is a clio workspace root, a packages folder or one package.
    """
    _tools_path()
    from creatio_schemas.describe import find_schema as _fs
    try:
        return _fs(path, schema)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"

def main() -> None:
    """Console entry point: serve over stdio."""
    global _ROOT
    _ROOT = default_root()
    if not (_ROOT / "Frontend").is_dir() and not (_ROOT / "Backend").is_dir():
        raise SystemExit(
            f"No knowledge base found at {_ROOT}. "
            "Set CREATIO_KB_ROOT to the folder that contains Frontend/ and Backend/."
        )
    mcp.run()


if __name__ == "__main__":
    main()
