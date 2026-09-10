# AGENTS.md

Instructions for an AI agent working **inside this repository**.

If instead you are writing Creatio code in some other project and want to *consume* these
recipes, that is a different job — see [skill/creatio-kb/SKILL.md](skill/creatio-kb/SKILL.md).

## What this repository is

A knowledge base of 168 Creatio development recipes, plus a Python MCP server that makes
them searchable. See [README.md](README.md) for the full picture.

**Nothing here is application code.** No build, no tests, no dependencies to install for
the content itself. The `.js`, `.cs` and `.sql` files are templates that are never compiled
or executed.

This has consequences for how you work here:

- Do **not** run linters, formatters or type checkers over the recipes, and do not "fix"
  what they would report. Unused variables, undeclared globals (`Ext`, `Terrasoft`,
  `sdk`), classes that wrap nothing, methods no one calls, placeholder GUIDs — all
  intentional.
- Do **not** try to make a recipe compile. A `.cs` recipe is wrapped in a bare
  `class HowToDoTheThing { }` purely to hold the methods; it has no Creatio assemblies
  behind it.
- Do **not** reformat, re-wrap or re-order existing recipes as a side effect of another
  task. The header blocks are hand-tuned prose.

## The one hard contract: the header block

The index parses the header to get the title and the summary that search results show. Get
this wrong and the recipe becomes nearly unfindable — it is the single most damaging
mistake available in this repo.

**`.js`** — a `---` fenced comment line, then `//` lines until the first blank line:

```js
// --- How to filter a lookup field --------------------------------------------
// Declare `lookupListConfig` on the lookup column in `attributes`. The filters
// array holds FUNCTIONS that are called with the view model as `this` every
// time the lookup list is opened.
```

In Classic UI recipes this sits at the top of the file. In Freedom UI recipes it sits
*inside* the schema, above the section it documents (usually just before `handlers`) —
both work, the parser searches the whole file. Follow whichever the neighbouring files use.

**`.cs`** — an XML summary; the **first sentence becomes the title**, so make that sentence
say what the recipe does:

```csharp
/// <summary>
/// Demonstrates how to query records using EntitySchemaQuery (ESQ).
/// ESQ is the primary way to read records in Creatio — it respects column and
/// row-level permissions. Use FetchFromDB instead when you need a single record.
/// </summary>
```

**`.sql`** — leading `--` line comments. Note that the four existing SQL files use `/* */`
blocks instead and therefore lose their descriptions; use `--` for anything new.

Verify after any edit that touches a header:

```bash
python mcp-server/kb_index.py
```

The report must end with **no warnings** and the recipe count must be what you expect. A
warning means a header was lost and the title fell back to the file name.

## Where a new recipe goes

Pick the area first, then the topic folder. Areas are fixed — they are hardcoded in
`AREAS` in [mcp-server/kb_index.py](mcp-server/kb_index.py):

| Area | Path | Suffix |
| --- | --- | --- |
| ClassicUI | `Frontend/ClassicUI` | `.js` |
| FreedomUI | `Frontend/FreedomUI` | `.js` |
| Backend | `Backend/C#` | `.cs` |
| SQL | `Backend/SQL` | `.sql` |

Topic folders as they stand:

- **Both UI areas:** `Attributes`, `Data`, `Dialogs`, `Fields`, `Lifecycle`, `Messaging`,
  `Navigation`, `Processes`, `Services`, `Users`
- **ClassicUI only:** `BaseMethods`, `BusinessRules`, `Details`, `Diff`, `Dom`, `Modules`,
  `Sections`
- **FreedomUI only:** `Grids`, `Reference`, `Validation`, `ViewConfig`
- **Backend:** `API`, `ESQ`, `Events`, `Patterns`, `SQLClasses`

Reuse a shared name when the concept exists in both generations — the point is that the
same task sits at the same path either side. Put a file at the **root** of an area only
when it is foundational (`HowToCreateCustomPage`) or genuinely ungroupable
(`HowToLoadExternalJsLibrary`). Creating a new topic folder is fine when a real cluster
appears; a one-file folder is acceptable and several already exist.

Name the file `HowToDoTheThing.js|cs`. The file name is tokenized into the search terms, so
it carries real ranking weight — name it for the task, not for the API.

## Writing a recipe

The header is the product; the code is the illustration. Write the header to answer what a
developer gets wrong, not what the API is called:

- state which part is counter-intuitive, and what the failure looks like — these APIs fail
  *silently*, so "returning null breaks the lookup list" is worth more than a signature;
- name the required dependency when there is one (`@creatio-devkit/common` in
  `SCHEMA_DEPS`, a `using`, a mixin);
- say where a value has to come from when it cannot be guessed (a `dataSourceName` is the
  lookup attribute name plus `_DS`, read off the real schema).

Code conventions, taken from the existing files:

- **`.js` — tabs.** All 92 nested recipes use them, without exception.
- **`.cs` — 4 spaces**, `using` directives at the top, above the summary.
- Use placeholder names: `QSMyEntity`, `UsrApplication`, `PDS_Name_a1b2c3d`.
- GUIDs go in named constants (`const MethodDirectImport = "7ec276fe-…"`), and must be
  invented, never lifted from a real database.
- Numbered comments (`// 1. Read a collection`, `// 2. Read a single record`) are the
  convention for multi-part recipes.

## Never mix the two UI generations

This is the mistake that produces plausible, broken code. Establish which generation the
task belongs to before writing a line:

| Generation | Marker in `properties.json` | Shape |
| --- | --- | --- |
| Freedom UI (8.x) | `"SchemaType": "AngularSchema"` | `viewConfigDiff`, `handlers`, `crt.*` requests, `sdk.*`, `request.$context` |
| Classic UI (7.x) | `EditViewModelSchema`, `GridDetailViewModelSchema`, `ModuleViewModelSchema` | `diff`, `methods`, `attributes`, `Terrasoft.*`, `Ext.create`, `this.get/set` |

`Terrasoft.FilterGroup` in a Freedom UI schema, or an `sdk.Model` in a Classic UI page, is
always wrong. When unsure which one a recipe you are editing belongs to, the folder tells
you.

## Do not do these

- **Do not add Markdown articles.** `Backend/articles/` is a lossy hand-written duplicate
  of the C# recipes that has already drifted from its sources, and the index does not read
  `.md` at all — so an article is invisible to every search tool. Prose that matters
  belongs in the header block of the source file, where the index reads it into the
  searchable summary.
- **Do not put a real GUID in a recipe**, even one that "looks harmless". Copied lookup ids
  silently target the wrong record in whatever project the recipe lands in.
- **Do not duplicate a recipe across areas** to cover both generations. Two recipes with
  the same name in `ClassicUI` and `FreedomUI` are correct and intended — searching without
  an `area` filter is how a caller sees both and picks.
- **Do not edit `mcp-server/` as part of a content change.** Adding recipes never requires
  touching the server; the index discovers files on the next call.

## Touching the MCP server

Two files, deliberately split:

- [mcp-server/kb_index.py](mcp-server/kb_index.py) — all the logic: header parsing,
  tokenizing, BM25 ranking, the symbol index. **Pure standard library, keep it that way** —
  it is what lets the index be exercised without the MCP SDK installed.
- [mcp-server/server.py](mcp-server/server.py) — thin MCP transport plus the tool
  docstrings the model reads. The docstrings are part of the interface; changing their
  wording changes when a model reaches for a tool.

The ranking weights near the top of `kb_index.py` (`W_TITLE_HIT`, `W_BODY_SCALE`,
`COVERAGE_FLOOR`) are tuned and commented with the reasoning. If you change one, check the
effect on real queries before and after:

```bash
python mcp-server/kb_index.py "make a field required conditionally"
python mcp-server/kb_index.py "run a business process"
```

Recipe ids are derived paths (`Frontend/FreedomUI/Fields/HowToFilterLookupField`), computed
at index time and stored nowhere, so moving a file between folders is safe.

## Reporting your work

When you add or change a recipe, say so explicitly in your summary to the user, and name
the trap the recipe records. A recipe added silently is a recipe nobody knows to trust.
