# Creatio knowledge base

A curated collection of **168 Creatio development recipes** — Classic UI (7.x), Freedom UI
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

The second problem is context: 168 files do not fit in a model's context window, and
loading them wholesale wastes it. Hence the MCP server — the assistant searches for the
one recipe it needs.

## Layout

```
Frontend/ClassicUI/    60   Creatio 7.x — diff, methods, Terrasoft.*
Frontend/FreedomUI/    44   Creatio 8.x — viewConfigDiff, handlers, crt.*, @creatio-devkit
Backend/C#/            60   ESQ, Select/Insert/Update, event listeners, web services, processes
Backend/SQL/            4   PostgreSQL diagnostic queries
Backend/articles/      46   Markdown variants of the C# recipes (see the caveat below)
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

Files sitting **at the root** of an area are the foundational or genuinely ungroupable
ones — `CommonPitfalls.js`, `HowToCreateCustomPage.js`, `HowToExtendStockSchema.js` in
Classic UI; `HowToCreateReusableRequest.js`, `HowToLoadExternalJsLibrary.js` in Freedom UI.

`Backend/C#/Patterns/` is the exception to the recipe format: seven reusable
building blocks (`BulkProcessor`, `RestClient`, `OperationResult`, `EntitySerializer`,
`ESQExtention`, `SoapClient`, `ScheduledJobPattern`) meant to be copied closer to
as-is.

## Using it with an AI assistant

Install the MCP server, and the assistant gets five tools: `search_recipes`,
`get_recipe`, `find_api`, `list_recipes`, `kb_overview`.

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

Search is lexical BM25 with a title bonus, built in memory at startup, rebuilt
automatically when a file changes. No API keys, no network, no embedding service. The
tokenizer is tuned for API names, so `crt.OpenLookupPageRequest` is findable as the full
dotted name, as `OpenLookupPageRequest`, and as `lookup page`.

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

- schema and entity names (`QSMyEntity`, `UsrApplication`),
- column names,
- Freedom UI generated attribute suffixes (`PDS_Name_a1b2c3d`) — these are per-page and
  must be read off the real schema,
- **every GUID literal.** Never copy a lookup id out of a recipe.

## Adding a recipe

Drop the file into the right area and topic folder, and keep the header format — it is
what supplies the title and the summary the search shows:

| Type | Header |
| --- | --- |
| `.js` | `// --- Title ------------` then `//` comment lines until a blank line |
| `.cs` | `/// <summary>` … `/// </summary>`; the first sentence becomes the title |
| `.sql` | leading `--` comment lines |

Name the file for the task: `HowToDoTheThing`. The words in the file name are folded into
the search terms, so the name carries real weight.

Nothing else needs updating — the index picks the file up on the next tool call. Verify
with `python mcp-server/kb_index.py` and check that no new warning appeared.

Conventions an agent should follow are in [AGENTS.md](AGENTS.md).

## Known gaps

Two of these are worth knowing before you trust a part of the repo:

- **`Backend/articles/` is a lossy parallel copy, not a rendering.** It holds 46 Markdown
  variants of the C# recipes, and they have already drifted: comparing
  `HowToSendEmailFromBackend` shows the four-sentence `<summary>` compressed to one generic
  line, an entire method (`SendEmailWithOptions`) dropped, and the logger renamed. **The
  MCP index does not read `.md` at all**, so these articles are invisible to search. Three
  of them (`HowToCreateAndWriteFileWithIFile`, `HowToMoveAndDeleteFileWithIFile`,
  `HowToImplementCustomFileStorage`) have no `.cs` counterpart, which means that content
  exists *only* in a form nothing can find. Treat the `.cs` files as the source of truth.
- **SQL recipes lose their descriptions.** The four files open with a `/* … */` block
  comment, but the parser expects line comments (`--`), so each gets a title synthesized
  from its file name and an empty summary. No warning is raised, because the fallback
  happens inside the SQL header parser rather than in the caller.
