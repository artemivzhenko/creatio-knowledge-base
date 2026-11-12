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
        "Clio (the clio CLI: one skill per functional block at the root and one "
        "reference page per command under reference/), "
        "Tools (tools/<name> - the file toolkits that build processes, business "
        "rules, objects and SQL scripts as package files). "
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
           "Backend", "SQL", "Clio" (the clio CLI and its MCP server) or "Tools"
           (the file toolkits: objects, process, rules, pages, data, push ...).
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

    area:  "ClassicUI", "FreedomUI", "RemoteModule", "Mobile", "Backend", "SQL", "Clio" or "Tools".
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
def schema_impact(path: str, schemas: str, tasks: str = "", current: str = "", md: bool = False, limit: int = DEFAULT_LIMIT, kind: str = "") -> str:
    """
    What a change to these schemas touches: every typed dependent (pages, processes, rules, DCM,
    bindings, listeners) of each schema, and - with `tasks` (the loop's tasks folder from
    project.json paths.tasks) - the other active task folders that change or depend on them, from
    their schemas.json. The author runs it while writing plan.md: `md=True` returns the `## Impact`
    table to paste and the `affects:` line for schemas.json; a `CONFLICT` means another active task
    changes a schema of this plan or one of its dependents - stop and ask the human. The tester
    reads `## Impact` to pick what to regression-test. `schemas` comma-separated; `current` this
    task's folder name (left out of the lock check). Ends with the counts.
    `kind` keeps only dependents of that kind (page, process, rules ...) when a lookup has too many.
    """
    _tools_path()
    from creatio_schemas.describe.deps import impact
    names = [s.strip() for s in schemas.split(",") if s.strip()]
    if not names:
        return "error: name at least one schema"
    try:
        text, conflicts = impact(path, names, tasks or None, current or None, md, limit, kind)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"
    return text + f"\nexit code {1 if conflicts else 0}"


@mcp.tool()
def merge_plan(path: str, schemas: str = "", env: str = "", limit: int = DEFAULT_LIMIT) -> str:
    """What collapsing the replacing layers of a schema into one would do, without writing anything: per schema
    `<Schema> <kind>: <N> layers, target <package>` (the lowest package, every other layer's package depends on it),
    `layer <pkg>: +n columns / elements / methods` in the order the platform applies them, `siblings: ... (order
    guessed)` when two layers have no dependency between them, `conflict ...` lines (one column name with two UIds,
    one UId with two types, two layers changing one page element, one method overridden in two layers, a callParent
    in a callback or with its value used, a lookup to an object of a package above the target), `depends: <target>
    gains ...`; then `<M> schemas, <L> layers to remove, <C> conflicts` and the exit code (1 on a conflict).
    `schemas` comma-separated (default: every schema replaced by more than one package of the workspace); `env`
    (a clio environment) takes the layer order from the site instead of guessing it from DependsOn. Run it before
    planning a layer merge; safe on a client workspace (no index is written)."""
    _tools_path()
    from creatio_schemas.describe.merge import merge_plan as _plan
    try:
        text, conflicts = _plan(path, [s.strip() for s in schemas.split(",") if s.strip()] or None, _env(env) if env else None, limit)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return text + f"\nexit code {1 if conflicts else 0}"


@mcp.tool()
def merge_layers(path: str, schema: str, target: str = "", env: str = "") -> str:
    """The replacing layers of one OBJECT collapsed into one layer of the target package - printed, NEVER written: the
    merge plan lines, then `write <file>` / `delete <folder>` for each file, or `stopped: ... - nothing written` (a
    conflict, siblings whose order only the site knows, a site row that still points at a layer to remove). `target`:
    the package to merge into (default the lowest layer's; every layer's package must depend on it). `env` (a clio
    environment) gives the site's layer order and runs the references check. To apply, the author runs
    `describe.py merge <workspace> <Object> -e <env> --apply` and pushes the packages; prove it with schema_snapshot
    before and after."""
    _tools_path()
    from creatio_schemas.describe.merge import merge_object
    try:
        text, code = merge_object(path, schema, target or None, _env(env) if env else None, apply=False)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return text + f"\nexit code {code}"


@mcp.tool()
def push_package(package: str, env: str, probe: bool = False, dry_run: bool = False,
                 project: str = "", tasks: str = "", task: str = "", force: bool = False,
                 baseline: str = "", skip_drift: bool = False, skip_foreign_files: bool = False,
                 skip_sql_dates: bool = False, skip_compile_package: bool = False) -> str:
    """
    Install a package using push v2: check drift (schemas of the package modified on the
    environment after the package's last git commit, found through SysPackage) and dropped
    dependencies (DependsOn and csproj references present in git HEAD and gone now), check
    task ownership, update changed SQL dates, clear IsChanged (SysSchema, SysPackageSchemaData,
    SysPackageSqlScript), push-pkg and check compilation. Assembly packages are compiled
    with compile-package --wait. compile-configuration runs only for processes with script
    or user tasks and may take minutes. probe also checks objects and SQL scripts; dry_run
    prints commands without launching processes or writing files: it sends nothing to the environment.

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
    import http.client
    import json
    try:
        r = _env(env).request(method.upper(), path.lstrip("/"), json.loads(body) if body.strip() else None)
    except (OSError, KeyError, ValueError, RuntimeError, http.client.HTTPException) as e:
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


def _answer(env: str, work, limit: int = DEFAULT_LIMIT) -> str:
    """`work(Environment)` -> text, cut to `limit` lines; a failure is `error: ...`."""
    from creatio_schemas.describe import cut
    _tools_path()
    try:
        text = work(_env(env))
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return "\n".join(cut(text.splitlines(), limit, "lines")) or "(nothing)"


@mcp.tool()
def run_process(env: str, process: str, params: str = "", results: str = "") -> str:
    """Start a business process on a clio environment (ProcessEngineService.svc/RunProcess) and read its run back in one
    answer: `ok` or `FAILED <reason>` with the process id, each result parameter, then the run's `SysProcessLog` row -
    status, start, end and the first line of the error (`process_error` gives the whole error and the element it stopped
    on). `params` is a JSON object (`{"OrderId": "<guid>", "Quantity": 3}`), `results` a comma list of result parameter
    names. Ends with `exit code 1` when the engine refused it or the run is not completed (failed, or still waiting).
    Runs the process: whatever it writes is written."""
    import json
    from creatio_schemas.runs import render_log
    try:
        values = json.loads(params) if params.strip() else {}
        if not isinstance(values, dict):
            raise ValueError("params must be a JSON object")
    except ValueError as e:
        return f"error: params: {e.args[0] if e.args else e}"
    names = [r.strip() for r in results.split(",") if r.strip()]

    def work(e):
        run = e.run_process(process.strip(), values, names)
        lines = [f"{process}: {'ok' if run['success'] else 'FAILED ' + str(run['error'])}  processId {run['processId'] or '-'}"]
        lines += [f"  {n} = {json.dumps(run['results'].get(n), ensure_ascii=False)}" for n in names]
        log = None
        if run["processId"]:
            try:
                log = e.process_log(run["processId"])
                lines.append(render_log(log, run["processId"]))
            except (ValueError, RuntimeError) as err:
                lines.append(f"log: not read - {err.args[0] if err.args else err}")
        return "\n".join(lines + [f"exit code {0 if run['success'] and (log is None or log['state'] == 'completed') else 1}"])

    return _answer(env, work)


@mcp.tool()
def process_runs(env: str, process: str = "", record: str = "", since: str = "", until: str = "", limit: int = 20,
                 window: int = 30, time_zone: str = "", noise: str = "") -> str:
    """What ran: the business-process runs of `SysProcessLog`, each with its start (UTC and `time_zone`), process, status,
    log id, owner and the first line of its error. `process` (name or UId - every copy of that schema) gives its newest
    `limit` runs; `record` (`<Entity>:<Id>`) gives every run that started within `window` seconds of a change of that
    record or of a row pointing at it (its details), oldest first - "what ran when the manager pressed the button".
    `since` / `until` (`2026-11-11T08:00`, UTC unless a zone is written) bound the start. `noise` (comma list of names or
    prefixes, as `project.json` `environment.noiseProcesses`) hides those processes with a line saying how many. Read-only."""
    from creatio_schemas.runs import process_runs as _runs, render_runs
    return _answer(env, lambda e: render_runs(_runs(e, process.strip() or None, record.strip() or None, since.strip() or None,
                                                    until.strip() or None, max(1, min(limit, 200)), max(0, window),
                                                    [n.strip() for n in noise.split(",") if n.strip()], time_zone or None)))


@mcp.tool()
def process_error(env: str, log_id: str, time_zone: str = "") -> str:
    """One run's error in full (`SysProcessLog.ErrorDescription` without the platform's stack frames, the message chain
    kept) and the element it stopped on (`SysProcessElementLog`: caption, status, start). `log_id` is the id
    `process_runs` or `run_process` printed. Read-only."""
    from creatio_schemas.runs import process_error as _error, render_error
    return _answer(env, lambda e: render_error(_error(e, log_id.strip(), time_zone or None)))


@mcp.tool()
def find_record(env: str, id: str, objects: str = "", everywhere: bool = False, time_zone: str = "") -> str:
    """Which table holds this Id? Scans the base tables that have a uuid `Id` (`objects`, comma-separated names, first;
    the workspace's objects are the usual hint) in unions of 50 and stops at the first batch that holds it unless
    `everywhere`. Answers the table, the record's caption (Name, Caption, Title...), and the dates and authors of its
    creation and last change in UTC and `time_zone` (`+03:00` or an IANA name). Read-only."""
    from creatio_schemas.records import find_record as _find, render_hits
    return _answer(env, lambda e: render_hits(_find(e, id, [o.strip() for o in objects.split(",") if o.strip()], everywhere, time_zone or None)))


@mcp.tool()
def record_context(env: str, entity: str, id: str, columns: str = "", depth: int = 1, time_zone: str = "", limit: int = DEFAULT_LIMIT) -> str:
    """One record as the database holds it: its columns with every lookup named (`Name` of the referenced row, found
    through the foreign keys), then the tables that have a row pointing at it with the count and the first 20 rows.
    `columns` is a comma list with `*` wildcards (default: every column with a value); `depth` 0 the record only,
    1 + the rows pointing at it, 2 + their lookups named. Read-only."""
    from creatio_schemas.records import record_context as _context, render_context
    return _answer(env, lambda e: render_context(_context(e, entity, id, columns, max(0, min(depth, 2)), time_zone or None)), limit)


@mcp.tool()
def role_members(env: str, role: str, units: bool = False) -> str:
    """The users a role reaches through `SysAdminUnitInRole` - the closure, nested roles and the org structure included,
    not only the direct members `SysUserInRole` lists - each with the unit the membership came through. `units` adds
    organization units and roles. Read-only."""
    from creatio_schemas.access import render_members, role_members as _members
    return _answer(env, lambda e: render_members(_members(e, role, units)))


@mcp.tool()
def user_roles(env: str, user: str) -> str:
    """The roles of a user (login or contact name) through `SysAdminUnitInRole`, each direct or through another unit. Read-only."""
    from creatio_schemas.access import render_roles, user_roles as _roles
    return _answer(env, lambda e: render_roles(_roles(e, user)))


@mcp.tool()
def role_diff(env: str, role: str, users: str) -> str:
    """Which of these users (comma-separated logins or contact names) are not in the role: `in <role>: ...` and
    `not in <role>: ...`, then `exit code 1` when anyone is missing. Read-only."""
    from creatio_schemas.access import role_diff as _diff
    missing = []

    def work(e):
        result = _diff(e, [u.strip() for u in users.split(",") if u.strip()], role)
        missing.extend(result["missing"])
        return f"in {role}: {', '.join(result['present']) or '-'}\nnot in {role}: {', '.join(result['missing']) or '-'}"

    text = _answer(env, work)
    return text if text.startswith("error:") else text + f"\nexit code {1 if missing else 0}"


@mcp.tool()
def sys_setting(code: str, envs: str, workspace: str = "", time_zone: str = "") -> str:
    """A system setting's value on each clio environment of the comma list `envs` - per value row who it is for, the value
    (a lookup by name), the date and the author - and, with `workspace` (a folder with `packages/`), every data binding of
    the workspace that sets it and the value a push would write. Read-only."""
    from creatio_schemas.access import render_setting, sys_setting as _setting
    from creatio_schemas.environment import Environment
    _tools_path()
    try:
        answer = _setting(code, {n.strip(): Environment.from_clio(n.strip()) for n in envs.split(",") if n.strip()}, workspace or None, time_zone or None)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    return render_setting(answer)


@mcp.tool()
def schema_diff(package: str, schemas: str = "", against: str = "") -> str:
    """
    What changed in a package, in schema terms: the working copy against git HEAD
    (default), another revision, or a folder holding the package (a pulled copy of the
    environment). Per item the lines the describe layer prints: `+` added (a column, an
    element, a rule), `-` removed, `~ key old -> new` changed; `+ Name kind (new)` /
    `- Name kind (removed)` for whole items. `schemas` limits it to a space-separated
    list of items. The tester's reading of what the author changed; never a JSON hunk.
    """
    _tools_path()
    from creatio_schemas.describe.diff import schema_diff as _sd
    try:
        return _sd(package, schemas.split() or None, against or None)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


@mcp.tool()
def review_download(package: str, keep: str = "") -> str:
    """A pulled package (a folder that holds it, or its path) sorted against git HEAD before anything is committed:
    files that differ only in line endings or a BOM (nothing changed), the items changed in content (`schema_diff`'s
    lines, renames by UId), dependencies dropped or added (descriptor.json, csproj), resource folders with no schema,
    files git does not track. `keep` (space-separated items) adds the `git checkout HEAD -- <path>` lines that would
    restore every other changed file; this tool only prints them - `describe.py review --keep ... --apply` runs them."""
    _tools_path()
    from creatio_schemas.describe.review import render, review
    try:
        return render(review(package, keep.split() if keep.strip() else None))
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e}"


@mcp.tool()
def precommit_check(workspace: str) -> str:
    """The staged files of a workspace that must not be committed - over 5 MB, an archive (.rar .zip .7z .gz .bak),
    a binary (.dll .exe .pdb) outside Files/Bin of an assembly package, a file outside packages/ and the known roots -
    one line each, then `exit code 1`; `ok` when there is none. Read-only (git is only read)."""
    _tools_path()
    from creatio_schemas.describe.review import precommit
    try:
        problems = precommit(workspace)
    except (FileNotFoundError, RuntimeError) as e:
        return f"error: {e}"
    return "\n".join(problems + ["exit code 1"]) if problems else "ok"


@mcp.tool()
def run_tests(env: str = "", project: str = "", category: str = "", test: str = "", package: str = "") -> str:
    """The in-Creatio tests of a project (the integration tier) through the runner `project.json` `tests.runner` names:
    the failed tests first with their messages, the passed ones, `N passed, M failed`, then a warning when the test
    package (`package`, default `tests.package`) changed on the site after its last successful compilation - the tests
    then ran on the old dll. `category` or `test` (a test class) selects; `env` a clio name, or `project` a project.json.
    Ends with `exit code 1` when a test failed, 2 when nothing could be run. Runs the tests: whatever they write is written."""
    import importlib.util
    import io
    from contextlib import redirect_stderr, redirect_stdout
    _tools_path()
    spec = importlib.util.spec_from_file_location("env_unit", _ROOT / "no-code" / "tools" / "env" / "unit.py")
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    if bool(category.strip()) == bool(test.strip()):
        return "error: give category or test (a test class), one of them"
    argv = ["run", "--category", category.strip()] if category.strip() else ["run", "--class", test.strip()]
    argv += ["--project", project] if project.strip() else ["-e", env.strip()]
    argv += ["--package", package.strip()] if package.strip() else []
    out = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(out):
            code = unit.main(argv)
    except SystemExit as e:  # argparse refused the arguments
        code = e.code if isinstance(e.code, int) else 2
    return out.getvalue().rstrip() + f"\nexit code {code}"


@mcp.tool()
def resolve_uid(path: str, text: str) -> str:
    """
    What a UId names in the workspace - a schema, a column (`column UsrOrder.UsrAmount`), a process
    element or parameter - or the UId of a dotted name (`UsrOrder.UsrAmount`,
    `UsrOrder_Process.ReadData.ResultEntity`). Given a text with UIds in it (a meta path from
    SysSchema metadata, a filter, a stack of them), every UId is named and the text comes back with
    the names in place: the reverse of what the designer stores. A UId that is not in the
    workspace (a lookup row, a system record) says so - env_sql finds those.
    """
    _tools_path()
    from creatio_schemas.describe.uids import resolve
    try:
        return resolve(path, text)
    except (FileNotFoundError, KeyError, ValueError) as e:
        return f"error: {e}"


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


@mcp.tool()
def schema_snapshot(schema: str, env: str = "", workspace: str = "", columns: str = "", out: str = "", limit: int = 0) -> str:
    """An OBJECT as text lines, to prove a layer merge changed nothing. `workspace`: the effective schema over every layer
    on disk (`layers: a > b`, `column <Name> <uid> <type> [lookup X] [required] [default v]`, `index ...`; the site's layer
    order when `env` is also given). `env`: what the site holds (`table T column <col> <type>`, `rows <n>`,
    `checksum <col> <md5>` of every column's values ordered by Id, `copy <package> extendParent=<bool>` per layer).
    Take it BEFORE and AFTER, then `snapshot_compare`. `columns`: a comma list to checksum (default every column but Id;
    name them on a big table). `out`: a file to write the lines to (the evidence). Reads with SELECTs and files, writes
    nothing to the site or the workspace."""
    from creatio_schemas.describe import cut
    from creatio_schemas.integrity import snapshot
    _tools_path()
    try:
        if not workspace and not env:
            return "error: give a workspace (disk lines), an env (site lines), or both"
        lines = snapshot(workspace or None, schema, _env(env) if env else None, [c.strip() for c in columns.split(",") if c.strip()] or None)
    except (OSError, KeyError, ValueError, RuntimeError) as e:
        return f"error: {e.args[0] if e.args else e}"
    if out:
        Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(cut(lines, limit, "lines")) or "(nothing)"


@mcp.tool()
def snapshot_compare(before: str, after: str) -> str:
    """Two snapshot files (`schema_snapshot` out=...) compared: `+ - ~` lines, or `same` when nothing differs.
    A difference ends with `exit code 1` - after a layer merge it is the bug report."""
    from creatio_schemas.integrity import compare
    try:
        diff = compare(Path(before).read_text(encoding="utf-8").splitlines(), Path(after).read_text(encoding="utf-8").splitlines())
    except OSError as e:
        return f"error: {e}"
    return "\n".join(diff + ["exit code 1"]) if diff else "same"


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
