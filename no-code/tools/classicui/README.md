---
description: Creatio Classic UI (7.x) client schemas (edit pages, sections, details - define() modules with entitySchemaName, attributes, messages, mixins, details, diff, methods, rules) of 8.x packages as files - read what the schema is, its sections, diff operations, methods, warnings; write a replacing schema of a platform page, adopt a copy pulled from another package (the Custom layer), add a localizable string, disable or remove an inherited business rule by UId, add a mixin, a method or a message, each a splice of one span with a dry-run diff.
---

# Classic UI tools

Scripts for **Classic UI client schemas**: the 7.x edit pages, sections and details that a package
still carries next to its Freedom UI pages - read them, and write what a replacing page needs.
Pure Python standard library.

| File | What it does |
| --- | --- |
| `classicui.py` | CLI: inspect, validate, methods, method, diff; replace, adopt, add-string, set-rule, add-mixin, add-method, set-message |
| `../creatio_schemas/classicui/schema.py` | `ClassicSchema`: the library the CLI uses |
| `../creatio_schemas/classicui/write.py` | its writers (`ClassicWriter`, mixed in) |
| `../creatio_schemas/text.py` | `mask`: comments and string, template and regex literals blanked (shared with the C# reader) |
| `tests/test_classicui_tools.py` | checks on an edit page and a section shaped like the platform's own |

```bash
python classicui.py inspect UsrPkg UsrOrderPage
python classicui.py diff    UsrPkg UsrOrderPage --op insert --parent Header
python classicui.py method  UsrPkg UsrOrderPage onEntityInitialized

python classicui.py replace    UsrPkg ContactPageV2 --parent-uid <uid> --entity Contact
python classicui.py set-rule   UsrPkg ContactPageV2 <rule uid> --enabled false --column Owner --dry-run
python classicui.py add-string UsrPkg ContactPageV2 UsrHint en-US="Fill in the owner"
```

## How it is stored

```
Schemas/<Name>/<Name>.js          define("<Name>", ["Dep", ...], function(Dep, ...) { return { <sections> }; })
Schemas/<Name>/descriptor.json    ManagerName ClientUnitSchemaManager, Parent (BasePageV2, BaseSectionV2, BaseGridDetailV2 ...)
Schemas/<Name>/properties.json    SchemaType: EditViewModelSchema, ModuleViewModelSchema, GridDetailViewModelSchema, Module
Schemas/<Name>/metadata.json      the schema's parameters as a diff against the parent (= + - ~ lines, CRLF, no final newline)
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

An untouched schema saves its bytes back. Every writer splices one span the reader found (a
section of the returned object, one member, the `define()` dependency list) and re-parses; the new
text takes the body's newline and indent unit, everything else keeps its bytes. Each editing
command takes `--dry-run` (the diff, nothing written) and validates after saving.

| Command | Writes |
| --- | --- |
| `replace <Schema> [--parent-uid]` | a replacing schema: descriptor (`Parent`, `ExtendParent: true`); metadata `= UId`, `= A5` (the package's CreatedInPackageId), `= B6` (the package), `= B8`, `+ B7 true`, `= HD1` (the parent's UId - from the workspace, else `--parent-uid`; the error prints the `env/sql.py` query that finds it); the designer's empty body (`attributes`, `messages`, `mixins`, `details`, `businessRules`, `methods`, `diff`; `entitySchemaName` with `--entity`); `properties.json`; the caption in every culture of the package |
| `adopt <Schema> --from <folder>` | a client schema pulled from another package (`clio pull-pkg` + `extract-pkg-zip` by the human; the package folder or the schema folder): copied with its resources, its UId replaced by a new one and its `A5` / `B6` by the target package's in the descriptor and the metadata (the strings' `A3`/`A4`/`A5` follow); then the diff against the parent's body when a workspace package holds the parent |
| `add-string <Key> culture=value ..` | `+ MetaData.Schema.B2 {UId, A2 key, A3/A4 the schema UId, A5}` once - before the `~ B2` order line when there is one and last in that order, else after the `A5`/`B2` lines - and `LocalizableStrings.<Key>.Value` per culture |
| `set-rule <UId> [--enabled] [--removed] [--column]` | the rule's override in `businessRules`: `"<column>": {"<uid>": {"uId": ..., "enabled": false, "removed": true}}`; an override the body has is edited in place; a rule only a workspace parent has is copied whole first (the parent's rule is not changed in the parent); with no parent in the workspace `--column` says where it goes |
| `add-mixin <Name> [--class] [--module]` | `mixins: {<Name>: "Terrasoft.<Name>"}` and `"<Name>"` in `define()`'s dependencies |
| `add-method <name> --file f.js [--replace]` | a member of `methods` (`function(...) {...}` from the file, re-indented); `--replace` swaps an existing one |
| `set-message <Name> --mode --direction` | `"<Name>": {mode: Terrasoft.MessageMode.X, direction: Terrasoft.MessageDirectionType.Y}` in `messages` |

A missing section is added empty (with the designer's `/**SCHEMA_...*/` markers where it has them)
as the last member of the returned object. Strings of a full-form metadata (a module) are refused.
The empty module, mixin module and source code schema come from `tools/scaffold` (`scaffold.py module`, `source`).

## Verified

Writers: the 34 replacing client schemas of the local workspaces (32 Freedom pages and 2 mobile
manifests - no Classic replacing page exists locally; the diff form is the same) re-serialise byte
for byte after a no-op load, and `add_string` on each keeps every old metadata line and orders the
new item last; `replace` writes their most common line order. On the fixture each writer keeps
every line outside its span and the body's CRLF. Not pushed to an environment yet.

Reader: all 269 `ClientUnitSchemaManager` schemas with a `define` in the local package folders round-trip
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
