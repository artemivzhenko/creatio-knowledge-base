---
description: Describe layer - what a Creatio package holds, what a schema is and one part of it (columns, elements, flows, rules, page elements, attributes, handlers, data sources) on request, without reading metadata or page bodies; 6x-40x fewer tokens than the files; describe_package, describe_schema, describe_item, index_workspace, find_schema as MCP tools and a CLI; a self-checking package index gives the files of a schema and who uses it without searching.
---

# Describe layer

Reading a schema file costs 6x-40x the tokens its summary does (an object 9.5k chars against
1.5k, a process 488k against 12k). This layer sits between the package files and the agent:
ask, do not read.

| Call | Answers |
| --- | --- |
| `describe_package(<package>, kind="")` | one line per schema and SQL script: kind, name, caption, counts, parent or replaced base |
| `describe_schema(<package>, <Schema>)` | the toolkit's summary (what `inspect` prints) |
| `describe_item(<package>, <Schema>, "<query>")` | one part, chosen by the query; nothing else |
| `index_workspace(<path>, rebuild=False)` | builds or refreshes the index of every package under a workspace root, a packages folder or one package; reports added / changed / removed |
| `find_schema(<path>, <Schema>)` | the package, kind, summary, every file (absolute paths), the schemas it refers to, the schemas and data bindings that refer to it |
| `schema_diff(...)` | a change in schema terms (S13-T07, pending) |

The same calls are MCP tools of the `creatio-kb` server and the CLI `describe.py package |
schema | item`. `<package>` is the package folder (`packages/UsrPkg` in a clio workspace).

Verified on two production workspaces (579 and 475 schemas, 33 and 56 MB, files only): every
schema opens and answers its summary and queries - objects, processes, rules, Freedom UI pages
(designer and template body forms, trailing commas included), mobile pages (plain JSON
bodies, read-only), DCM cases and user tasks; a package of 579 schemas lists in ~1.5 s from the
index. C# - source code schemas and Files/cs - answers by signatures (see below). Classic UI
client schemas and data bindings are listed with their files until their topics land.

## The package index

`<workspace>/.creatio-index/<Package>.json` (next to `packages/`; add the folder to the
workspace's `.gitignore`, it is a cache) holds, per schema, SQL script, data binding and plain C#
file under `Files`: kind, caption, summary line, parent or target, every file with size and
mtime, and the schemas of the workspace it refers to - by name or by UId found in its text files.
A `Files/cs` item is the one file, named by its package-relative path, with no descriptor or
resources; other items refer to it through the types it declares, so `find_schema UsrOrderLabel`
finds the file and who calls it. `describe_package` and
`find_schema` answer from it: a 578-schema package lists in 1.5 s instead of 35 s, and the agent
gets the files to open and the impact of a change in one call.

The versioned index also stores binding targets, row counts, columns and up to 40 Code or Name
values, plus each schema's resource cultures, en-US key count and missing-key counts. An older
index format is rebuilt automatically.

The index checks itself on every use: a file whose size or mtime changed, a schema folder that
appeared (after `clio pull-pkg`) or disappeared is re-read before the answer, and when names
appear or disappear every item's references are rescanned. There is no refresh hook to wire into
a pull script; `describe.py index <workspace>` after a pull only tells what changed. `--rebuild`
starts over. A change of the toolkit itself (a new kind, another `summary` or `opens`) changes no
package file, so the index does not see it: such a change bumps `INDEX_FORMAT` in `index.py`, or
run `describe.py index <workspace> --rebuild` after updating the toolkit. A change of the *kinds* (a kind added, removed or reordered in `registry.py`)
needs neither: the index header carries a registry fingerprint and rebuilds itself on mismatch.

A broken item costs one line, never the answer: a schema, C# file or data binding that cannot be
read (an empty `data.json`, a `Data/` folder without its descriptor, a parser error) is stored as
`{"error": "<type>: <message>"}` - the message names the file - and listed as `cannot read:` in
`describe.py package`; `describe.py package <pkg> --kind error` lists only those. `find` and
`lookups` skip them and end with `N items unreadable (describe.py package <pkg> --kind error lists
them)`; asked for a broken item by name, `find` answers its error in one line. A file that is not
UTF-8 is read as cp1251 (a `.cs` saved in the Windows code page) and its item's summary ends with
`(cp1251)`; a writer that saves such a file writes it as UTF-8. `CSharpSource` never raises: a file
it cannot read answers `summary()` = `unreadable: <reason>`.

## Typed dependencies

`describe.py deps <workspace|package> <Schema> [--in|--out] [--kind object] [--via lookup]` (MCP
`schema_deps`; topics `uses` and `used-by` of every item; `find` prints both directions) answers
"what does this build on" and "who builds on this" from edges the index stores per item
(`creatio_schemas/describe/deps.py`, format 3). An edge is `to_kind to_name via ref detail`:

- `via` is one closed word per kind - object `parent`, `lookup`; process `signal`, `read-data`,
  `add-data`, `modify-data`, `delete-data`, `sub-process`, `user-task`, `param`; dcm `entity`,
  `step`; rules `target`, `column`; page `parent`, `data-source`, `module`; classic `parent`,
  `entity`, `detail`, `mixin`, `module`, `lookup`, `rule`; data `binds`; sql `after`, `table`;
  csharp/source `listener`, `esq`, `query`, `string`.
- The words of code: `esq` - `new EntitySchemaQuery(esm, "X")` or `GetInstanceByName("X")`, with
  the columns `esq.AddColumn("Y")` names until the block ends; `query` - `Select ... From("X")`,
  `Into("X")`, `new Update(uc, "X")`, a join, with the `Column` / `Set` columns when the statement
  names one table; `listener` also lists the columns the listener reads or sets on its object
  (`XId` of a lookup `X` counts as `X`); `string` - a bare literal that is a workspace object's
  name and no other edge reaches. A process script task gives the same words, the element first in
  `detail`. `table` - a SQL script's table after `from`, `join`, `update`, `into`, `alter table`
  that is a workspace or stock object (a CTE, a temp table, a comment, a string is not). `column` -
  the attributes a business rule's conditions and actions name, on the target object, or for a page
  rule on its data source's object. Classic `rule` - the columns `businessRules` / `rules` bind,
  on the page's entity; `lookup` - an attribute's `referenceSchemaName`; Freedom `module` - a
  workspace client schema in `SCHEMA_DEPS`.
- `ref` says how sure the edge is: `uid` - the metadata stores the UId (an object's lookup column,
  a process signal, a DCM step); `name` - a name resolved in a context that names the object (a
  page's data source, a listener's `SchemaName`, a Classic page's `entitySchemaName`, the object an
  ESQ or a query constructor names, a rule's target); `text` - a word found in code or SQL (`string`,
  `table`): a suspicion to read, not a proof. One target reached several ways keeps the surest ref.
- `detail` lists the columns: a page's attribute columns are checked against the data source
  object's effective columns (own, replacing copies, the stock parents, the base cache from the
  environment, else the stock catalogue - `entity/assets/stock_columns_8.3.2.json`, every object
  of the 8.3.2 full product with its effective columns), so `Name` there is *that* object's column
  and not a same-named one elsewhere; a column the chain cannot show ends with `?`. An object the
  workspace and the stock 8.3.2 list (`entities_8.3.2.json`, 1527 objects) do not know is printed
  by its UId.

Reverse edges are not stored: `dependents` scans the stored ones over every package of the
workspace. The `refers to` / `used by` lines of `find` stay the untyped text matches.

## Export

`describe.py export <workspace|package> [--out <folder>]` writes a snapshot of the answers for
reading without the tools - a human in a file browser, an agent without the MCP, a broken item
someone wants to see: `<Package>/_package.md` (the `package` lines, then the items that cannot
be read) and one `<Schema>.md` per item - the `schema` summary, `## Depends on`, `## Dependents`
(the typed edges, as `deps` prints them) and `## Files` with absolute paths; bindings under
`Data/`, C# files under `Files/cs/`. An unreadable item is a one-line file with its error. UTF-8,
LF. Each run overwrites the files, removes the files of items that are gone and touches nothing
else in the folder. Nothing reads the snapshot back: the index is the store, this is an export of
it (the whole of a 900-item workspace in about 12 s).

The folder defaults to `<workspace>/.creatio-export` - gitignore it next to `.creatio-index`. For a
client workspace pass `--out` elsewhere: never write inside a client workspace.

## Impact of a change

`describe.py impact <workspace> <Schema>... [--tasks <folder>] [--current <task>] [--md]` (MCP
`schema_impact`) is the graph working for the loop: for every schema a task changes, its typed
dependents, and - with the loop's tasks folder - the other active task folders (no
`success-report.md`) that change one of them (`schemas` of their `schemas.json`: a **conflict**,
exit 1) or depend on it (`affects`: a heads-up). `--md` prints the `## Impact` table the author
pastes into `plan.md` and the `affects:` line that fills `schemas.json`; the tester reads the
table to pick what to regression-test. What the task changes is never listed as what it affects.

## Lookups

`describe.py lookups <workspace|package>` (MCP `list_lookups`) lists every object whose parent
chain reaches `BaseLookup` - through the workspace's own objects or the stock ones
(`entity/assets/stock_lookups_8.3.2.json`, 496 names; the 8.2.3 list of 272 is the fallback) - with package, caption, the chain, own
columns, the data bindings that seed it (rows counted) and how many items refer to it. That is
the list a de-duplication or binding-value task starts from. An object whose parent is outside
both the workspace and the stock list is reported as *not decided* rather than guessed.

## Layers on an environment

`describe.py layers <Schema> -e <env> [--rule <UId>] [--json]` (or `--project project.json`;
library `creatio_schemas/describe/layers.py`) is the one command that reads the environment: every
`SysSchema` copy of the name, applied first to last - package, replacing or not, ModifiedOn and
ModifiedBy, IsChanged, the body's size and md5 (`SysSchemaContent`, else the `MetaData` column).
The order is the package hierarchy of the customisation package (the platform function
`tsp_GetSysSchemaParentsInPackageHierarchyByPackage`, as the object toolkit's base fetch uses it);
copies outside that hierarchy are listed first. With `--rule` each layer says whether the business
rule with that UId is `absent`, `enabled`, `disabled` or `removed` in its body, and the line under
the table names its state in the layer applied last.

When a copy lives in the customisation package - `Custom`, or `environment.customLayer` of
project.json, or `--custom-layer` - the last line is `Custom layer present: <package>` and the exit
code is 1: that copy is applied after every package a task pushes and overrides it. The author runs
it before the plan, the tester as the first preflight step; `--json` is the evidence. One SQL call
through `Environment.sql` (tools/env), PostgreSQL only.

## The output contract

An answer is never a dump. `describe_schema` is the summary: header, counts, problems, and at
most `DEFAULT_LIMIT` (40) lines; a list topic of `describe_item` shows at most that many items.
When something was left out the last line is the tail `  ... N more; add limit=0 for all`.
The parameter is `limit=` in a query, `limit` on the MCP tools, `--limit` on the CLI; `0` means
everything. Constants: `creatio_schemas/describe/core.py` (`DEFAULT_LIMIT`, `TAIL`, `cut`).
The rule for the reader: a part of a schema is asked for with `describe_item`, not read from a
longer dump and not from the file - the file is opened only for what no topic returns, at the
path `find_schema` gives.

## The query grammar

`<topic> [<name>] [key=value ...]` - `topics` lists what a schema can answer; `limit=N` cuts a
list topic (default 40, `0` = all).
The MCP `describe_item` tool also accepts `limit`; an explicit `limit=` in the query takes
precedence. Package, find and lookup lists accept `--limit` on the CLI and `limit` on MCP.

| Kind | Topics |
| --- | --- |
| every schema | `files`, `resources [culture=]`, `resource <key>`, `missing [culture=] [from=en-US]` (keys a culture lacks) |
| object | `columns [type=Lookup] [flag=required] [own=true]`, `column <Name>` (line + raw JSON), `flags`, `base` |
| process | `elements [kind=FormulaTask]`, `element <Name>` (values, flows in and out), `params [direction=In]`, `flows [from=] [to=]`, `script <Element>` |
| rules | `rules [enabled=false]`, `rule <Name|caption|uid>` |
| sql | `body`, `deps` |
| dcm | `stages`, `stage <name|caption>` (steps, conditions, moves in and out), `steps [stage=]`, `step <name>`, `moves [from=] [to=]`, `filter [raw=true]` |
| user-task | `params [direction=]`, `param <name>`, `methods`, `method <name>` (one method's C#), `source` |
| classic (a 7.x client schema: `define()` module) | `diff [op=insert\|merge\|remove\|move] [parent=]`, `element <name>` (its operations with source), `methods`, `method <name>`, `messages`, `attributes`, `details`, `mixins`, `find <text>` |
| data (a `Data/<Name>` binding; `--kind data` lists them) | `columns` (uid, key, type, localised), `rows [limit=] [culture=]`, `row <key>` (values with lookup display names) |
| C# (source code schema, or `Files/cs/X.cs` by path, file name or stem) | `classes [role=] [kind=] [generated=true]` (types with bases, attributes, role, member count), `members [<Type>] [kind=] [visibility=]` (one-line signatures), `member <Type.Name>` (one body), `usings`, `regions`, `operations [kind=]` (ESQ, raw SQL, Entity save, SysSettings, process start, HTTP, ClassFactory ... by line), `find <text>` |
| page (Freedom UI) | `sections` (names and sizes), `elements [type=crt.Input] [parent=SideAreaProfileContainer]`, `element <Name>`, `attributes [bound=true]`, `attribute <Name>`, `data-sources`, `handlers` (request -> size), `handler <request>` (one handler's code), `validators`, `converters`, `containers`, `find <text>` |

A page is treated as a database: its body is split into view config, attributes, data sources,
handlers, converters and validators, and each query returns one slice. `handlers` names the
requests and their sizes; the code of one comes with `handler crt.SaveRecordRequest`. Base
members of a replacing object are marked `base`.

```bash
python describe.py package packages/UsrPkg --kind page
python describe.py item packages/UsrPkg UsrOrder "columns type=Lookup"
python describe.py item packages/UsrPkg UsrOrder_FormPage "elements parent=SideAreaProfileContainer"
python describe.py item packages/UsrPkg UsrOrder_Process "element ReadOrders"
```

## C# by signatures

A source code schema (`Schemas/<Name>/<Name>.cs`) and every file under `Files/cs` are read by
regex and brace matching over a copy with comments and string contents blanked - not a compiler
(roslyn-codelens is the tool for depth). Each type gets a **role** from its base or attribute:
web service (`BaseService` / `[ServiceContract]`), entity event listener of `<Schema>`, user task,
app event listener, scheduler job, background task, DTO (`[DataContract]`), DI binding,
exception, interface, enum, static helper, class; anything deriving from the platform's generated
bases or living under `Autogenerated/` is `generated` and hidden from `classes` unless asked.
`describe_package` lists the Files/cs files as `csharp` lines. Verified on 463 files of the
local workspaces (93 types, 721 members, 1 s, no parse errors).

## The registry of kinds

`creatio_schemas/describe/registry.py` is the one place the layer knows a kind: a `Kind` entry
says how to recognise an item (`opens`), build it (`make`), summarise it and which topics it
answers. `open_item`, `kind_of`, `summary`, `topics_of`, the index and the CLI read that list.
Adding a kind is one `register(Kind(...))` with the kind's class, summary and topic handlers -
the kind's own module never imports the describe layer. Order matters: the first entry whose
`opens` says yes wins, so specific kinds sit before the generic `source` / `client` fallbacks.

What a new kind has to know, beyond the `Kind` fields:

- `opens(package, name, descriptor)` gets `descriptor=None` for an item outside `Schemas/` (SQL
  scripts, data bindings, C# files); such kinds test `d is None` and sit before every kind that
  needs a descriptor.
- `register(kind)` inserts first by default (`first=True`), so the new kind wins ties; pass
  `first=False` to append it.
- `open_item` stamps `_kind` on the item; an item built without it is matched by class, first
  entry wins - `source` and `csharp` share `CSharpSource`, so build those through `open_item`.
- `rename(item)` lets one entry answer two kinds (`page` / `mobile`, the fallback's `client` /
  `mobile` / `schema`); `_KIND_LABEL` in `core.py` holds the labels of kinds without a toolkit.
- A kind's `topics` are merged with `COMMON` (`files`, `resources`, `resource`); on a clash
  `COMMON` wins (`topics_of`).
- The index caches `kind` and `summary`: see "The package index" above for the rebuild.

## Kinds without a toolkit

Mobile settings, images and the other addons are listed at package level with their files and
sizes (`describe_item ... files`); resources as a kind of their own are S13-T05.

## Checks

`python tests/test_describe.py` - runs on the other toolkits' fixtures.
