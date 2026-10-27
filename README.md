# Creatio knowledge base

A curated collection of **169 Creatio development recipes** — Classic UI (7.x), Freedom UI
(8.x), C# backend and SQL — plus copyable project templates for Freedom UI and Mobile
modules, a C# style guide, and an MCP server that makes all of it searchable by an AI
assistant.

| Area | Recipes |
| --- | --- |
| Frontend — Classic UI (7.x) | 57 |
| Frontend — Freedom UI (8.x) | 44 |
| Backend — C# | 62 |
| Backend — SQL (PostgreSQL) | 4 |
| Module templates — Freedom UI custom component, Mobile SDK module | 2 |
| **Total** | **169** |

Recipes do not compile or run on their own. Every recipe is a header block that explains
the API and its traps, followed by a code template you adapt. The value is concentrated in
the headers — they carry the things general Creatio knowledge gets wrong. The two module
templates are the exception: they are real projects that build.

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

The second problem is context: 169 files do not fit in a model's context window, and
loading them wholesale wastes it. Hence the MCP server — the assistant searches for the
one recipe it needs.

## Layout

```
CREATIO_CODE_STYLE.md          C# style and architecture guide, served by get_code_style
agent_setup.py                 one-command setup of the MCP server and companion tooling
Frontend/ClassicUI/       57   Creatio 7.x — diff, methods, Terrasoft.*
Frontend/FreedomUI/       44   Creatio 8.x — viewConfigDiff, handlers, crt.*, @creatio-devkit
Frontend/RemoteModule/     1   Freedom UI custom Angular view element — recipe + template/
Frontend/Mobile/           1   Creatio Mobile SDK handler module — recipe + template/
Backend/C#/               62   ESQ, Select/Insert/Update, event listeners, web services, processes, files
Backend/SQL/               4   PostgreSQL diagnostic queries
mcp-server/                    search server exposing the recipes over MCP
skill/creatio-kb/              Claude Code skill: the habit of consulting the KB
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
| [Frontend/RemoteModule/template/](Frontend/RemoteModule/template/) | Angular remote module with a custom Freedom UI view element | `npm install`, `npm run build`, copy the output into the package file content |
| [Frontend/Mobile/template/](Frontend/Mobile/template/) | Creatio Mobile (8.2+) module with request handlers | its [README](Frontend/Mobile/template/README.md): rename in three places, `npm install`, `npm run build:deploy` |

Each template also exists as one indexed recipe next to the folder
(`HowToCreateCustomAngularViewElement.ts`, `HowToCreateMobileRequestHandlerModule.ts`): the
whole project in a single file, split at `===== file:` markers, with the traps in the
header. That is the form the assistant reads. A folder with `package.json` inside is never
indexed, so template files do not show up as recipes.

## C# code style guide

[CREATIO_CODE_STYLE.md](CREATIO_CODE_STYLE.md) covers how back-end code should look:
formatting and `#region` layout, naming, interfaces and `[DefaultBinding]` registration,
guard clauses and exception types, logging format, concurrency, XML docs, anti-patterns,
and a review checklist. The assistant reads it through `get_code_style`, whole or one
section at a time.

## Using it with an AI assistant

The MCP server gives the assistant six tools:

| Tool | Purpose |
| --- | --- |
| `search_recipes(query, area?)` | ranked search by task or symptom |
| `get_recipe(recipe_id)` | the full recipe; a bare file name that exists in both UI generations lists both |
| `find_api(symbol)` | reverse lookup: which recipes use `crt.OpenLookupPageRequest`, `UseAdminRights`… |
| `list_recipes(area?, topic?)` | browse ids and titles |
| `kb_overview()` | map of areas, topics and counts |
| `get_code_style(section?)` | the C# style guide, whole or by section |

`area` is one of `ClassicUI`, `FreedomUI`, `RemoteModule`, `Mobile`, `Backend`, `SQL`.

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
