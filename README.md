# Creatio knowledge base

A curated collection of **177 Creatio development recipes** — Classic UI (7.x), Freedom UI
(8.x), C# backend and SQL — plus copyable project templates for Freedom UI and Mobile
modules, a C# style guide, **a no-code layer** (13 clio block skills with a reference page for
each of its 261 commands, and 17 Python toolkits that build business processes, rules, objects,
pages, cases, data bindings and SQL scripts as package files), **a describe layer** that answers
questions about a package - what it holds, what a schema is, who depends on it, what changed -
without reading the files, and an MCP server that gives an AI assistant all of it as 37 tools.
Four Claude Code skills turn the tools into roles: an **author** that builds a task and a
**tester** that proves it, under one task-folder contract.

| Area | Entries |
| --- | --- |
| Frontend — Classic UI (7.x) | 61 |
| Frontend — Freedom UI (8.x) | 44 |
| Backend — C# | 65 |
| Backend — SQL (PostgreSQL) | 4 |
| Module templates — Freedom UI component and request handlers, Mobile SDK module | 3 |
| **Code recipes** | **177** |
| clio — block skills with verified traps | 13 |
| clio — command reference (generated from clio's docs) | 261 |
| Tools — one README per package toolkit, searchable as area `Tools` | 17 |

Recipes do not compile or run on their own. Every recipe is a header block that explains
the API and its traps, followed by a code template you adapt. The value is concentrated in
the headers — they carry the things general Creatio knowledge gets wrong. The two module
templates are the exception: they are real projects that build.

The no-code layer in [no-code/](no-code/README.md) is the counterpart for everything an agent
does *without* writing code: the clio skills cover packages, SQL, objects and columns, Freedom UI
pages, applications, rights, builds, and clio's own MCP server, and record what was verified on
a real Creatio 8.2.3 environment — including what clio silently gets wrong there; the toolkits
under `no-code/tools/` write what clio cannot on 8.x - business processes, business rules, DCM
cases, user tasks, objects, pages, data bindings, SQL scripts - as package files, byte for byte,
behind one front door (`python no-code/tools/creatio.py`).

## Quick start

```bash
git clone https://github.com/artemivzhenko/creatio-knowledge-base.git
cd creatio-knowledge-base
python agent_setup.py            # --dry-run prints the commands instead
```

Requires Python 3.10+ and Claude Code. Works on Windows, macOS and Linux. The script
creates the MCP server's virtual environment, registers `creatio-kb` with Claude Code at
user scope, and installs the general tooling used alongside it:

| Tool | Kind | Purpose |
| --- | --- | --- |
| `creatio-kb` | MCP | this knowledge base |
| ponytail | plugin | smallest change that fully works |
| graphify | skill | `/graphify` builds a queryable knowledge graph of a codebase |
| context7 | MCP | up-to-date library docs (Angular, RxJS, npm packages) |
| microsoft-learn | MCP | official .NET / C# documentation |
| roslyn-codelens | MCP | Roslyn semantic analysis of C# solutions (needs .NET 10 SDK, skipped otherwise) |

Re-running it is safe. Restart Claude Code afterwards and check with `claude mcp list`.

Manual setup for Cursor, Claude Desktop or a knowledge base in another location is in
[mcp-server/README.md](mcp-server/README.md).

## Why it exists

Creatio's API surface differs sharply between UI generations, and a lot of it is
counter-intuitive in ways that cost hours:

- `UseAdminRights` defaults to *bypassing* permissions, not enforcing them.
- `itemType: 2` in a Classic UI `diff` is a detail, not a tab panel.
- A Classic UI lookup filter returning `null` breaks the list; an empty `FilterGroup` is
  how you say "show everything".
- Freedom UI `lookupListConfig` filters are *functions*, re-evaluated on every open.
- A Mobile SDK handler with empty `scopes` fires on every page of the app.

Writing this from memory produces code that looks right and fails silently. The recipes
pin down the shape that actually works.

The second problem is context: 177 files do not fit in a model's context window, and
loading them wholesale wastes it. Hence the MCP server — the assistant searches for the
one recipe it needs.

## Layout

```
CREATIO_CODE_STYLE.md          C# style and architecture guide, served by get_code_style
agent_setup.py                 one-command setup of the MCP server and companion tooling
Frontend/ClassicUI/       61   Creatio 7.x — diff, methods, Terrasoft.*
Frontend/FreedomUI/       44   Creatio 8.x — viewConfigDiff, handlers, crt.*, @creatio-devkit
Frontend/RemoteModule/     2   Freedom UI remote module: view element, request handlers — recipes + template/
Frontend/Mobile/           1   Creatio Mobile SDK handler module — recipe + template/
Backend/C#/               65   ESQ, Select/Insert/Update, event listeners, web services, processes, files, unit tests
Backend/SQL/               4   PostgreSQL diagnostic queries
no-code/                       clio for agents: clio-*/SKILL.md per block, reference/<command>.md, tools/sync_clio_docs.py
no-code/tools/                 the package toolkits (creatio.py front door, creatio_schemas/ library, <tool>/<tool>.py CLIs,
                               describe/ the describe layer, env/ the environment layer, push/, scaffold/, project.py)
mcp-server/                    the MCP server: recipe search, the describe layer, push and environment tools
skill/creatio-kb/              Claude Code skill: the habit of consulting the KB and the describe tools before writing
skill/creatio-loop/            the author/tester contract: the task folder, project.json, the schema lock, proof tiers
skill/creatio-author/          the author role: plan.md with acceptance criteria, impact, build, push, probe
skill/creatio-tester/          the tester role: preflight, map, tests of every tier, evidence, the report
```

Each area is split into topic folders. Both UI areas use the same vocabulary wherever the
concept exists in both — `Attributes`, `Data`, `Dialogs`, `Fields`, `Lifecycle`,
`Messaging`, `Navigation`, `Processes`, `Services`, `Users` — so the same task lives at the
same path in either generation.

Where the generations genuinely differ, the folder name follows the platform:
Classic UI has `Diff`, `Details`, `Modules`, `Sections`, `Dom`, `BaseMethods`,
`BusinessRules`; Freedom UI has `ViewConfig`, `Grids`, `Validation`, and a `Reference`
folder for the four lookup tables (stock `crt.*` requests, stock converters, view element
types, sdk filters and enums).

Files sitting **at the root** of an area are the foundational or genuinely ungroupable
ones — `CommonPitfalls.js`, `HowToExtendStockSchema.js`, `HowToUseLocalizableStrings.js`
in Classic UI; `HowToCreateReusableRequest.js`, `HowToLoadExternalJsLibrary.js` in Freedom UI.

`Backend/C#/Patterns/` is the exception to the recipe format: seven reusable
building blocks (`BulkProcessor`, `RestClient`, `OperationResult`, `EntitySerializer`,
`ESQExtention`, `SoapClient`, `ScheduledJobPattern`) meant to be copied closer to
as-is.

## Module templates

Two kinds of project take the longest to set up, so each has a ready folder to copy,
rename and build on:

| Template | What it is | Start with |
| --- | --- | --- |
| [Frontend/RemoteModule/template/](Frontend/RemoteModule/template/) | Angular remote module with a custom Freedom UI view element and request handlers | its [README](Frontend/RemoteModule/template/README.md): rename in three places, `npm install`, `npm run build` |
| [Frontend/Mobile/template/](Frontend/Mobile/template/) | Creatio Mobile (8.2+) module with request handlers | its [README](Frontend/Mobile/template/README.md): rename in three places, `npm install`, `npm run build:deploy` |

Each template also exists as indexed recipes next to the folder
(`HowToCreateCustomAngularViewElement.ts` and `HowToCreateRequestHandlerInRemoteModule.ts`
for Freedom UI, `HowToCreateMobileRequestHandlerModule.ts` for Mobile): the code in a
single file, split at `===== file:` markers, with the traps in the header. That is the form the assistant reads. A folder with `package.json` inside is never
indexed, so template files do not show up as recipes.

## C# code style guide

[CREATIO_CODE_STYLE.md](CREATIO_CODE_STYLE.md) covers how back-end code should look:
formatting and `#region` layout, naming, interfaces and `[DefaultBinding]` registration,
guard clauses and exception types, logging format, concurrency, XML docs, anti-patterns,
and a review checklist. The assistant reads it through `get_code_style`, whole or one
section at a time.

## Using it with an AI assistant

The MCP server gives the assistant 37 tools in three groups.

Recipes:

| Tool | Purpose |
| --- | --- |
| `search_recipes(query, area?)` | ranked search by task or symptom |
| `get_recipe(recipe_id)` | the full recipe; a bare file name that exists in both UI generations lists both |
| `find_api(symbol)` | reverse lookup: which recipes use `crt.OpenLookupPageRequest`, `UseAdminRights`… |
| `list_recipes(area?, topic?)` | browse ids and titles |
| `kb_overview()` | map of areas, topics and counts |
| `get_code_style(section?)` | the C# style guide, whole or by section |

The describe layer, over a package folder or a clio workspace (`no-code/tools/describe/README.md`):

| Tool | Purpose |
| --- | --- |
| `describe_package(path, kind?)` | one line per schema, SQL script, data binding: kind, name, caption, counts |
| `describe_schema(path, Name)` | the summary of one schema - 6x-40x fewer tokens than its files |
| `describe_item(path, Name, "<topic> [<name>] [k=v]")` | one part: a column, an element, a handler's code, a stage, a parameter |
| `find_schema(path, Name)` | where a schema lives, its files, what it refers to and what refers to it |
| `schema_deps(path, Name, direction?, kind?, via?)` | the typed dependency graph: what it builds on, who builds on it, through which columns |
| `schema_impact(path, schemas, tasks?, current?, md?)` | the dependents of the schemas a task changes and the locks of the other active tasks |
| `schema_diff(package, schemas?, against?)` | what changed against git HEAD, a revision or a pulled copy, as `+` / `-` / `~` lines per item |
| `schema_layers(env or project.json, Name)` | the copies of a schema on an environment in the order the platform applies them; a Custom-layer copy is flagged |
| `schema_snapshot(Name, env?, workspace?)`, `snapshot_compare(before, after)` | an object before / after a layer merge as lines (disk: effective columns; site: table, rows, checksums, copies) and their `+ - ~` comparison |
| `merge_plan(path, schemas?, env?)` | collapsing the replacing layers of a schema into one: the target package, what each layer adds, the conflicts, the dependencies the target gains; writes nothing |
| `merge_layers(path, Object, target?, env?)` | the layers of one object as one layer of the target: the files it would write and delete, or why it stops; prints only |
| `list_lookups(path)` | every lookup object with its parent chain, bindings and users |
| `index_workspace(path, rebuild?)` | build or refresh the index the answers come from |

The environment, through a clio environment name, never a private script:

| Tool | Purpose |
| --- | --- |
| `env_sql(env, sql)` | rows as JSON |
| `env_odata(env, Entity, select?, filter?, top?)` | records over OData |
| `env_call(env, method, path, body?)` | a service or OData call with login and CSRF |
| `find_record(env, id, ...)`, `record_context(env, entity, id, ...)` | which table holds an Id; a record with its lookups named and its details |
| `run_process(env, process, params?, results?)`, `process_runs(env, process?, record?, ...)`, `process_error(env, log_id)` | start a process and read its log; what ran around a record's changes; one run's error without stack frames |
| `run_tests(env, category?, test?)`, `review_download(package, keep?)`, `precommit_check(workspace)` | the in-Creatio tests with counts and the stale-dll warning; a pulled package sorted against HEAD; staged files that must not be committed |
| `role_members`, `user_roles`, `role_diff`, `sys_setting` | role membership (nested roles included) and a setting across environments and bindings |
| `push_package(package, env, ...)` | install in one command: IsChanged cleared, push-pkg, compilation log, probes of the changed items |

`area` is one of `ClassicUI`, `FreedomUI`, `RemoteModule`, `Mobile`, `Backend`, `SQL`,
`Clio`, `Tools`. In the `Clio` area `get_recipe("execute-sql-script")` returns a command's reference
page and `get_recipe("clio-sql-and-data")` a block skill; in `Tools`, `get_recipe("tools/process")`
a toolkit's README. Without an area filter, clio pages are scaled down so that a platform question
("upload a file") is still answered by a platform recipe; name clio or a command in the query to
bring them up.

Search is lexical BM25 with a title bonus and a light stemmer (`pagination` finds
`paginate`), built in memory at startup and rebuilt automatically when a file changes. No
API keys, no network, no embedding service. The tokenizer is tuned for API names, so
`crt.OpenLookupPageRequest` is findable as the full dotted name, as `OpenLookupPageRequest`,
and as `lookup page`. Words like `Freedom UI` are ignored in queries: the UI generation is
the `area` filter.

The companion skill in [skill/creatio-kb/](skill/creatio-kb/) supplies the *habit* of
consulting the tools before writing Creatio code — the server alone will not make an
assistant reach for it. Copy the folder into `.claude/skills/` of the project you develop
Creatio in.

## The author/tester loop

Three more skills in [skill/](skill/) make two agents work a task against each other without a
human in between: [creatio-loop](skill/creatio-loop/SKILL.md) is the contract - a task folder
whose files are the protocol (`task.md`, `questions.md`, `plan.md` with acceptance criteria and an
`## Impact` table, `schemas.json` as the lock between tasks, `report-N.md`, `success-report.md`,
`failed.md`), `project.json` with the environment and the package, the proof tiers (unit, probe,
backend over OData, process case, UI case); [creatio-author](skill/creatio-author/SKILL.md) plans,
builds with the toolkits, pushes and probes; [creatio-tester](skill/creatio-tester/SKILL.md)
reads the plan and `schema_diff`, writes a test of the right tier for every criterion in the
sibling test framework (`automatic-creatio-tests`, its `creatio-tests` MCP server), keeps the
evidence and writes the report. The tester never changes package files; the author never writes
the report.

## Using it as a human

Browse the folders, or query the index from the command line. `kb_index.py` is pure
standard library, so this works without installing anything:

```bash
python mcp-server/kb_index.py                          # index report: areas, topics, warnings
python mcp-server/kb_index.py "filter a lookup field"  # ranked search
```

A healthy report ends with **no warnings**. A warning means a recipe lost its header block
and only got a title derived from its file name — that recipe has become much harder to
find.

## The recipes are templates

Before using generated or copied code, replace:

- schema and entity names (`UsrMyEntity`, `UsrApplication`),
- column names,
- Freedom UI and Mobile generated attribute suffixes (`PDS_Name_a1b2c3d`) — these are
  per-page and must be read off the real schema,
- **every GUID literal.** Never copy a lookup id out of a recipe.

## Adding a recipe

Drop the file into the right area and topic folder, and keep the header format — it is
what supplies the title and the summary the search shows:

| Type | Header |
| --- | --- |
| `.js`, `.ts` | `// --- Title ------------` then `//` comment lines until a blank line |
| `.cs` | `/// <summary>` … `/// </summary>`; the first sentence becomes the title |
| `.sql` | leading `--` comment lines |
| `.md` (no-code only) | the first `# ` heading; description from frontmatter `description:` or the first paragraph |

Name the file for the task: `HowToDoTheThing`. The words in the file name are folded into
the search terms, so the name carries real weight.

Nothing else needs updating — the index picks the file up on the next tool call. Verify:

```bash
python mcp-server/kb_index.py          # no new warning, recipe count as expected
python mcp-server/test_kb_index.py     # after any change to mcp-server/
```

Conventions an agent should follow are in [AGENTS.md](AGENTS.md).

Contributions are welcome. If a Creatio trap has cost you an afternoon, it deserves a
recipe: open a pull request, and it will be standardized into the base.

## Known gaps

Worth knowing before you trust a part of the repo:

- **The SQL header parser only reads `--` line comments.** A `/* … */` block gets a title
  synthesized from the file name and an empty summary, and no warning is raised. The four
  existing files use `--`; keep it that way.
- **Backend API coverage is uneven.** `Backend/C#/API/` and `Backend/C#/Patterns/` are the
  thinnest areas relative to how often they come up.
- **The Angular template and its recipe target different versions.** The folder is the
  Academy example on Angular 15; the single-file recipe describes Angular 17. Both work;
  keep them in sync when you upgrade one.
- **The Mobile template is verified by build only.** The SDK runs only inside the mobile
  runtime, so there are no unit tests; check behaviour on a device or emulator.
