---
description: Creatio Classic UI (7.x) client schemas (edit pages, sections, details - define() modules with entitySchemaName, attributes, messages, mixins, details, diff, methods, rules) of 8.x packages as files, read-only - what the schema is, its sections, the diff operations and elements, the methods by name and one method's source, warnings about parent names and handlers the file cannot prove.
---

# Classic UI tools

Read-only scripts for **Classic UI client schemas**: the 7.x edit pages, sections and details that a
package still carries next to its Freedom UI pages. Pure Python standard library.

| File | What it does |
| --- | --- |
| `classicui.py` | CLI: inspect, validate, methods, method, diff |
| `../creatio_schemas/classicui/schema.py` | `ClassicSchema`: the library the CLI uses |
| `../creatio_schemas/text.py` | `mask`: comments and string, template and regex literals blanked (shared with the C# reader) |
| `tests/test_classicui_tools.py` | checks on an edit page and a section shaped like the platform's own |

```bash
python classicui.py inspect UsrPkg UsrOrderPage
python classicui.py diff    UsrPkg UsrOrderPage --op insert --parent Header
python classicui.py method  UsrPkg UsrOrderPage onEntityInitialized
```

## How it is stored

```
Schemas/<Name>/<Name>.js          define("<Name>", ["Dep", ...], function(Dep, ...) { return { <sections> }; })
Schemas/<Name>/descriptor.json    ManagerName ClientUnitSchemaManager, Parent (BasePageV2, BaseSectionV2, BaseGridDetailV2 ...)
Schemas/<Name>/properties.json    SchemaType: EditViewModelSchema, ModuleViewModelSchema, GridDetailViewModelSchema, Module
Schemas/<Name>/metadata.json      the schema's parameters as a diff (not read)
Resources/<Name>.ClientUnit/      captions and LocalizableStrings per culture
```

The returned object's sections, as counted in 545 schema modules of the 8.3.2 platform pages,
sections and details: `diff` 500, `methods` 454, `entitySchemaName` 451, `attributes` 270,
`details` 238, `messages` 156, `mixins` 121, `rules` 109, `userCode` 35, `modules` 25,
`properties` 19, `columns` 9, `dataModels` 6, `businessRules` 4 - in any order, any of them missing.

- `diff` operations: insert 2172, merge 452, remove 210, move 80. The element's name is on the
  item or inside its `values` (`{"operation": "insert", "parentName": "Header", "values": {"name": ...}}`).
  40% of the `parentName`s (862 of 2140) name containers of the parent schema (`Header`, `Tabs`,
  `LeftContainer`, `ProfileContainer` ...), not of the file itself.
- `methods`: mostly `name: function(...) {...}`; also `Terrasoft.emptyFn` and other expressions.
- `/**SCHEMA_DIFF*/ ... /**SCHEMA_DIFF*/` (also `DETAILS`, `MODULES`, `BUSINESS_RULES`) markers
  wrap the designer-edited sections; they are comments to the reader.
- The body is JavaScript, not JSON: comments, trailing commas, `Terrasoft.*` constants, regex
  literals (11 modules), template literals (7). A mobile settings file under the same manager is
  plain JSON without `define` and is reported as such.

## What the tools write

Nothing. `ClassicSchema` keeps the body, metadata and descriptor as text; `files()` returns them
unchanged, so the round trip is byte-identical.

## Verified

All 269 `ClientUnitSchemaManager` schemas with a `define` in the local package folders round-trip
byte for byte; the 712 schema modules of the compiled 8.3.2 client content parse (2948 diff
operations, every one with an operation and a name; 5146 methods, each body cut at its own brace).
The moved `mask` gives the same output as before on all 832 local C# files.

## Checks

Warnings only - most names a Classic schema uses come from the platform's parent schema, which is
not in the workspace:

- a diff item without a name (on the item or in its values);
- `parentName`s declared neither in this diff nor in the workspace copies of the parent chain - one line;
- handler bindings (`click`, `change`, `prepareList`, `afterrender`, `linkclick`, `activeRowAction` ...)
  to methods defined neither here nor in those parents - one line.

```bash
python tests/test_classicui_tools.py
```
