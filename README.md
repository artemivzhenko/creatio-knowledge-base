# Creatio knowledge base

A curated collection of **169 Creatio development recipes** — Classic UI (7.x), Freedom UI
(8.x), C# backend and SQL — plus an MCP server that makes them searchable by an AI
assistant.

Nothing here compiles or runs. Every file is a **recipe**: a header block that explains the
API and its traps, followed by a code template you adapt. The value is concentrated in the
headers — they carry the things general Creatio knowledge gets wrong.

## Why it exists

Creatio's API surface differs sharply between UI generations, and a lot of it is
counter-intuitive in ways that cost hours:

- `UseAdminRights` defaults to *bypassing* permissions, not enforcing them.
- `itemType: 2` in a Classic UI `diff` is a detail, not a tab panel.
- A Classic UI lookup filter returning `null` breaks the list; an empty `FilterGroup` is
  how you say "show everything".
- Freedom UI `lookupListConfig` filters are *functions*, re-evaluated on every open.

Writing this from memory produces code that looks right and fails silently. The recipes
pin down the shape that actually works.

The second problem is context: 167 files do not fit in a model's context window, and
loading them wholesale wastes it. Hence the MCP server — the assistant searches for the
one recipe it needs.

## Layout

```
CREATIO_CODE_STYLE.md       C# style and architecture guide, served by get_code_style
Frontend/ClassicUI/    57   Creatio 7.x — diff, methods, Terrasoft.*
Frontend/FreedomUI/    44   Creatio 8.x — viewConfigDiff, handlers, crt.*, @creatio-devkit
Frontend/RemoteModule/  1   Angular custom view element — recipe + copyable project folder example4/
Frontend/Mobile/        1   Creatio Mobile SDK — recipe + copyable project folder template/
Backend/C#/            62   ESQ, Select/Insert/Update, event listeners, web services, processes, files
Backend/SQL/            4   PostgreSQL diagnostic queries
mcp-server/                 Search server exposing the recipes over MCP
skill/creatio-kb/           Claude Code skill: the habit of consulting the KB
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

`Frontend/RemoteModule/` (Angular custom view element) and `Frontend/Mobile/` (Mobile SDK
handler module) are project templates. Each holds one `.ts` recipe - the whole project in one
indexed file, split at `===== file:` markers, for the assistant - and a real folder
(`example4/`, `template/`) to copy and rename. A folder with `package.json` inside is never
indexed as recipes.

Files sitting **at the root** of an area are the foundational or genuinely ungroupable
ones — `CommonPitfalls.js`, `HowToExtendStockSchema.js`, `HowToUseLocalizableStrings.js`
in Classic UI; `HowToCreateReusableRequest.js`, `HowToLoadExternalJsLibrary.js` in Freedom UI.

`Backend/C#/Patterns/` is the exception to the recipe format: seven reusable
building blocks (`BulkProcessor`, `RestClient`, `OperationResult`, `EntitySerializer`,
`ESQExtention`, `SoapClient`, `ScheduledJobPattern`) meant to be copied closer to
as-is.

## Using it with an AI assistant

Install the MCP server, and the assistant gets six tools: `search_recipes`,
`get_recipe`, `find_api`, `list_recipes`, `kb_overview`, and `get_code_style` for the C#
style guide in [CREATIO_CODE_STYLE.md](CREATIO_CODE_STYLE.md).

```bash
cd mcp-server
python -m venv .venv
.venv/Scripts/activate          # Windows; source .venv/bin/activate elsewhere
pip install -e .
```

Then register it — full instructions for Claude Code, Cursor and Claude Desktop are in
[mcp-server/README.md](mcp-server/README.md):

```bash
claude mcp add creatio-kb -- <path-to-venv-python> <path-to-kb>/mcp-server/server.py
```

Search is lexical BM25 with a title bonus and a light stemmer, built in memory at
startup, rebuilt automatically when a file changes. No API keys, no network, no embedding service. The
tokenizer is tuned for API names, so `crt.OpenLookupPageRequest` is findable as the full
dotted name, as `OpenLookupPageRequest`, and as `lookup page`.

The companion skill in [skill/creatio-kb/](skill/creatio-kb/) supplies the *habit* of
consulting the tools before writing Creatio code — the server alone will not make an
assistant reach for it. Copy the folder into `.claude/skills/` of the project you develop
Creatio in.

## One-shot agent setup

`agent_setup.py` installs the general development tooling used alongside this knowledge
base (ponytail, graphify, context7, Microsoft Learn, Roslyn CodeLens) and registers the
`creatio-kb` server, all at user scope. Python 3.10+, any OS. Re-running it is safe;
`--dry-run` prints the commands instead of executing them.

```bash
python agent_setup.py
```

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
- Freedom UI generated attribute suffixes (`PDS_Name_a1b2c3d`) — these are per-page and
  must be read off the real schema,
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

Nothing else needs updating — the index picks the file up on the next tool call. Verify
with `python mcp-server/kb_index.py` and check that no new warning appeared.

Conventions an agent should follow are in [AGENTS.md](AGENTS.md).

## Known gaps

Worth knowing before you trust a part of the repo:

- **The SQL header parser only reads `--` line comments.** A `/* … */` block gets a title
  synthesized from the file name and an empty summary, and no warning is raised — the
  fallback happens inside the SQL header parser rather than in the caller. The four
  existing files use `--`; keep it that way.
- **Backend API coverage is uneven.** `Backend/C#/API/` and `Backend/C#/Patterns/` are the
  thinnest areas relative to how often they come up.