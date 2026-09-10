---
name: creatio-kb
description: Look up the project's Creatio recipes before writing or reviewing Creatio code. Use whenever the task touches a Creatio schema - Classic UI pages, details or sections (7.x), Freedom UI pages (8.x AngularSchema), C# server code (EntitySchemaQuery, event listeners, web services, business processes), or the diff/handlers/attributes of a client schema.
---

# Creatio knowledge base

This solution has a curated knowledge base of Creatio recipes, served by the
`creatio-kb` MCP server. It holds the idioms, naming rules and known traps of THIS
codebase — things general Creatio knowledge gets wrong or does not know.

## Use it before writing Creatio code

Do not write a Creatio schema from memory. The API surface differs sharply between
Classic UI and Freedom UI, and several details in this solution are counter-intuitive
(`UseAdminRights` defaults to bypassing permissions; `itemType: 2` is a detail, not a
tab panel; a delete button without the empty-selection guard deletes everything).

Workflow:

1. `search_recipes` with the task in plain words — "make a field required
   conditionally", "add rows to a detail in bulk", "run a business process".
2. `get_recipe` on the best hit to read the full example.
3. Write the code following that recipe's shape.

When you already have a symbol in hand — from existing code, an error, a review —
use `find_api` instead: it tells you which recipe demonstrates that exact API.

`kb_overview` maps the areas and topics when you are unsure what is covered.

## Pick the right UI generation first

Determine which one the task is about before searching, because the answers do not
transfer:

- `properties.json` says `"SchemaType": "AngularSchema"` → **Freedom UI**
  (`viewConfigDiff`, `handlers`, `crt.*` requests). Search with `area="FreedomUI"`.
- `"EditViewModelSchema"`, `"GridDetailViewModelSchema"`, `"ModuleViewModelSchema"`
  → **Classic UI** (`diff`, `methods`, `Terrasoft.*`). Search with
  `area="ClassicUI"`.
- C# under `Schemas/<Name>/<Name>.cs` → **Backend**. Search with `area="Backend"`.

Searching without `area` is useful on purpose when you want to see how the same task
is solved on both sides.

## The recipes are templates, not drop-ins

Every example uses placeholder names. Before using generated code, replace:

- schema and entity names (`QSMyEntity`, `UsrApplication`),
- column names,
- the generated attribute suffixes in Freedom UI (`PDS_Name_a1b2c3d`) — these are
  per-page and must be taken from the real schema,
- GUID literals — never copy a lookup id from a recipe.

## Keep the knowledge base current

When you solve something the knowledge base did not cover — a new API, a trap that
cost time — add a recipe in the matching area folder, following the existing header
format (`// --- Title ---` for `.js`, `/// <summary>` for `.cs`). The index picks it
up automatically. Say so in your summary to the user rather than adding it silently.
