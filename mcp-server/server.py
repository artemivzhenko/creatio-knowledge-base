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
               "tools/pages", "tools/process", "tools/rules", "tools/sqlscripts",
               "tools/dcm", "tools/usertask", "tools/data", "tools/classicui", "tools/resources",
               "tools/scaffold", "tools/describe", "tools/push", "tools/uitests")
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


_tools_path()
from creatio_schemas.describe import DEFAULT_LIMIT  # noqa: E402


@mcp.tool()
def describe_package(package: str, kind: str = "", limit: int = DEFAULT_LIMIT) -> str:
    """
    What a Creatio package holds, one line per schema and SQL script: kind, name,
    caption, counts (columns, elements, rules, page elements) and the parent or the
    replaced base. Call this BEFORE reading any file of a package.

    package: the package folder, e.g. C:/work/packages/UsrPkg (a clio workspace package).
    kind:    optional filter - object, process, rules, page, sql, client, addon, source, csharp, dcm, user-task,
             data (the Data/<Name> bindings with the table they seed and their row counts; listed only when asked).
             C# files under Files/cs are listed as `csharp` by signatures (roles, method count); source code schemas as `source`.
    """
    _tools_path()
    from creatio_schemas.describe import describe_package as _dp
    try:
        return _dp(package, kind, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def describe_schema(package: str, schema: str, limit: int = DEFAULT_LIMIT) -> str:
    """
    The summary of one schema - columns and flags of an object, elements, parameters
    and flows of a process, rules of a rule addon, elements and data sources of a
    Freedom UI page, engine and dependencies of a SQL script. 6x-40x fewer tokens than
    the schema's files. At most `limit` lines (0 = all); when cut, the last line says
    how many more there are - ask describe_item for the one part you need instead of
    raising the limit.
    """
    _tools_path()
    from creatio_schemas.describe import describe_schema as _ds
    try:
        return _ds(package, schema, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def describe_item(package: str, schema: str, query: str = "topics", limit: int = DEFAULT_LIMIT) -> str:
    """
    One part of a schema, chosen by a query "<topic> [<name>] [key=value ...]";
    "topics" lists what the schema can answer. Examples:
      object : "columns type=Lookup", "column UsrAmount", "flags", "base"
      process: "elements kind=FormulaTask", "element ReadOrders", "params", "flows from=Start", "script Calc"
      rules  : "rules", "rule <name>"
      dcm    : "stages", "stage Stage1", "steps stage=Stage1", "step DcmElement1", "moves from=Stage1", "filter"
      user task: "params", "param RecordId", "methods", "method InternalExecute", "source"
      data   : (a Data/<Name> binding) "columns", "rows limit=20 culture=en-US", "row <key>"
      classic: (a 7.x client schema) "diff op=insert", "element UsrTotal", "methods", "method onSaved", "messages",
               "attributes", "details", "find UsrTotal"
      C#     : (schema name, or "Files/cs/X.cs" / "X.cs" / "X") "classes", "members UsrService kind=method visibility=public",
               "member UsrService.GetLabel" (one body), "usings", "regions", "operations" (ESQ, raw SQL, SysSettings,
               process start, HTTP ... with line numbers), "find GetTypedColumnValue"
      page   : "sections", "elements parent=SideAreaProfileContainer", "element UsrName",
               "attributes bound=true", "data-sources", "handlers", "handler crt.SaveRecordRequest",
               "validators", "converters", "containers", "find <text>"
      any    : "files", "resources culture=uk-UA", "resource Caption", "missing culture=ru-RU from=en-US"
    Nothing is returned that was not asked for: a page is a database, this is the query.
    """
    _tools_path()
    from creatio_schemas.describe import QueryError, describe_item as _di, parse_query
    try:
        if "limit" not in parse_query(query)[2]:
            query = f"{query} limit={limit}"
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
def list_lookups(path: str, limit: int = DEFAULT_LIMIT) -> str:
    """
    Every lookup object of a workspace or package - an object whose parent chain reaches
    BaseLookup, through the workspace's own objects or the stock ones - one line each:
    package, caption, parent chain, own columns, data bindings with the rows they bind,
    how many schemas refer to it. The starting list for de-duplication, binding-value
    checks and lookup clean-ups. `path` is a clio workspace root, a packages folder or one
    package. Objects whose parent is outside both the workspace and the stock list are
    reported separately as not decided.
    """
    _tools_path()
    from creatio_schemas.describe import lookups as _lk
    try:
        return _lk(path, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def find_schema(path: str, schema: str, limit: int = DEFAULT_LIMIT) -> str:
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
        return _fs(path, schema, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def schema_deps(path: str, schema: str, direction: str = "both", kind: str = "", via: str = "", limit: int = DEFAULT_LIMIT) -> str:
    """
    The typed dependency graph around one schema, from the workspace index: `depends on` (its
    parent, lookup columns, data sources, signals, sub-processes, details, mixins, bindings) and
    `dependents` (every object, process, page, DCM, rule, binding or C# listener of the workspace
    that builds on it). One line per edge: `<kind> <name>  <via>: <columns>  [ref]` - no `[ref]`
    means the metadata stores the UId; `[name]` means a name resolved in a context that names the
    object (a page's data source), and a column ending with `?` could not be shown on that object.
    Call it before changing an object or page to see the impact, and instead of grepping for who
    uses a schema. `direction` both | out | in; `kind` and `via` filter the edges (kind: object,
    process, page, dcm, rules, data, csharp; via: lookup, signal, data-source, detail, ...).
    `path` is a clio workspace root, a packages folder or one package.
    """
    _tools_path()
    from creatio_schemas.describe.deps import dependencies
    try:
        return dependencies(path, schema, direction, kind, via, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def schema_impact(path: str, schemas: str, tasks: str = "", current: str = "", md: bool = False, limit: int = DEFAULT_LIMIT) -> str:
    """
    What a change to these schemas touches: every typed dependent (pages, processes, rules, DCM,
    bindings, listeners) of each schema, and - with `tasks` (the loop's tasks folder from
    project.json paths.tasks) - the other active task folders that change or depend on them, from
    their schemas.json. The author runs it while writing plan.md: `md=True` returns the `## Impact`
    table to paste and the `affects:` line for schemas.json; a `CONFLICT` means another active task
    changes a schema of this plan or one of its dependents - stop and ask the human. The tester
    reads `## Impact` to pick what to regression-test. `schemas` comma-separated; `current` this
    task's folder name (left out of the lock check). Ends with the counts.
    """
    _tools_path()
    from creatio_schemas.describe.deps import impact
    names = [s.strip() for s in schemas.split(",") if s.strip()]
    if not names:
        return "error: name at least one schema"
    try:
        text, conflicts = impact(path, names, tasks or None, current or None, md, limit)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"
    return text + f"\nexit code {1 if conflicts else 0}"


@mcp.tool()
def push_package(package: str, env: str, probe: bool = False, dry_run: bool = False,
                 project: str = "", tasks: str = "", task: str = "", force: bool = False,
                 baseline: str = "", skip_drift: bool = False, skip_foreign_files: bool = False,
                 skip_sql_dates: bool = False, skip_compile_package: bool = False) -> str:
    """
    Install a package using push v2: check drift and task ownership, update changed SQL
    dates, clear IsChanged, push-pkg and check compilation. Assembly packages are compiled
    with compile-package --wait. compile-configuration runs only for processes with script
    or user tasks and may take minutes. probe also checks objects and SQL scripts; dry_run
    prints commands without launching processes or writing files.

    project and task select the current task for ownership checks; tasks overrides the
    project tasks folder. Without either tasks or project the ownership check is skipped.
    force, baseline and the skip flags have the same meaning as in the push CLI.
    """
    if not package.strip() or not (Path(package) / "descriptor.json").is_file():
        return "error: package must contain descriptor.json"
    if not env.strip():
        return "error: env must not be empty"
    _tools_path()
    from creatio_schemas import push as _push
    lines: list[str] = []
    try:
        code = _push.push(Path(package), env, _push.Clio(env), probe, dry_run, log=lines.append,
                          project=Path(project) if project else None, tasks=Path(tasks) if tasks else None,
                          task=Path(task) if task else None, force=force,
                          baseline=Path(baseline) if baseline else None, skip_drift=skip_drift,
                          skip_foreign_files=skip_foreign_files, skip_sql_dates=skip_sql_dates,
                          skip_compile_package=skip_compile_package)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        lines.append(f"error: {e.args[0] if e.args else e}")
        code = 2
    lines.append(f"exit code {code}")
    return "\n".join(lines)


def _env(env: str):
    from creatio_schemas.environment import Environment
    if not env.strip():
        raise ValueError("env must be a clio environment name")
    return Environment.from_clio(env.strip())


@mcp.tool()
def env_sql(env: str, sql: str, limit: int = DEFAULT_LIMIT) -> str:
    """Run SQL on a Creatio environment through clio and return the rows as JSON (one object per row; several
    statements separated by `;` at line ends run one by one). `env` is a clio environment name. Read-only by habit:
    an update or delete runs too, so only on the project's environment. An `[ERR]` from the database comes back
    as `error: ...`."""
    import json
    from creatio_schemas.describe import cut
    try:
        rows = _env(env).sql(sql)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return "\n".join(cut([json.dumps(r, ensure_ascii=False, default=str) for r in rows], limit, "rows")) or "(no rows)"


@mcp.tool()
def env_call(env: str, method: str, path: str, body: str = "") -> str:
    """Call a site path with login and CSRF: `rest/<Svc>/<Method>`, `ServiceModel/<Svc>.svc/<Method>`,
    `odata/<Entity>`, `ServiceModel/ProcessEngineService.svc/RunProcess`. `method` GET/POST/PATCH/DELETE, `body` a JSON
    text. Returns `status: N` and the JSON answer (a JSON string inside an XML answer is unwrapped), or
    `error: <status>: <reason>` with the reason taken from the WCF fault page. Writes whatever the call writes."""
    import json
    try:
        r = _env(env).request(method.upper(), path.lstrip("/"), json.loads(body) if body.strip() else None)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    if not r.ok:
        return f"error: {r.error}"
    answer = r.json()
    return f"status: {r.status}\n" + (json.dumps(answer, ensure_ascii=False, indent=2) if answer is not None else r.text.strip())


@mcp.tool()
def env_odata(env: str, entity: str, select: str = "", filter: str = "", top: int = 20) -> str:
    """Read records of an object through OData 4: `select` comma-separated columns (a lookup is `<Column>Id`),
    `filter` an OData expression (`Name eq 'x'`), at most `top` rows, as JSON - one object per line."""
    import json
    try:
        rows = _env(env).odata(entity, [c.strip() for c in select.split(",") if c.strip()] or None, filter or None, top)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) or "(no rows)"


@mcp.tool()
def schema_layers(path_or_env: str, schema: str, rule: str = "") -> str:
    """The copies of a schema on a Creatio environment, in the order the platform applies them (the last one wins):
    package, replacing or not, modified on / by, IsChanged, body size and md5. Run it BEFORE planning a change to a page
    or object that the platform or another package already has, and as the tester's first preflight step: a copy in the
    customisation package (Custom) is applied after every package you push and silently overrides it - the answer then ends
    with `Custom layer present: <package>`. `path_or_env` is a clio environment name or the path of project.json (its
    environment.customLayer names the customisation package). `rule`: a business rule UId - its state (absent / enabled /
    disabled / removed) in every layer. Reads the environment (one SELECT), writes nothing."""
    import json
    from creatio_schemas.describe.layers import CUSTOM_LAYER, render, schema_layers as _layers
    from creatio_schemas.environment import open_environment
    project = path_or_env if path_or_env.endswith(".json") else None
    try:
        env = open_environment(None if project else path_or_env, project)
        custom = json.loads(Path(project).read_text(encoding="utf-8-sig")).get("environment", {}).get("customLayer") if project else None
        return render(_layers(env, schema, rule or None, custom or CUSTOM_LAYER), env.clio_name or env.url)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"


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
