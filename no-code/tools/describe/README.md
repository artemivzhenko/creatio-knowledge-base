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
| `schema_diff(<package>[, schemas, against])` | the working copy against git HEAD, a revision or a folder, in schema terms: `+` `-` `~` lines per item (see "Schema diff") |

The same calls are MCP tools of the `creatio-kb` server and the CLI `describe.py package |
schema | item`. `<package>` is the package folder (`packages/UsrPkg` in a clio workspace).

Verified on two production workspaces (579 and 475 schemas, 33 and 56 MB, files only): every
schema opens and answers its summary and queries - objects, processes, rules, Freedom UI pages
(designer and template body forms, trailing commas included), mobile pages (plain JSON
bodies, read-only), DCM cases and user tasks; a package of 579 schemas lists in ~1.5 s from the
index. C# - source code schemas and Files/cs - answers by signatures (see below). Classic UI
client schemas and data bindings are listed with their files until their topics land.

## Commands

<!-- commands:start -->
```
python describe.py package <package> [--kind object|process|rules|page|sql|client|addon|source|csharp|dcm|user-task]
python describe.py schema  <package> <Schema>
python describe.py item    <package> <Schema> "<topic> [<name>] [key=value ...]"
python describe.py item    <package> <Schema> topics                 # what this schema can answer
python describe.py index   <workspace|package> [--rebuild]           # build/refresh the index (.creatio-index/<Package>.json)
python describe.py find    <workspace|package> <Schema>              # package, files, refers to, used by
```

| command | what it does |
| --- | --- |
| `package` | one line per schema |
| `schema` | the summary of one schema |
| `item` | one part of a schema |
| `index` | build or refresh the package index |
| `find` | where a schema lives and what touches it |
| `lookups` | every lookup object (parent chain reaches BaseLookup) with bindings and users |
| `deps` | typed dependencies of a schema over the workspace: what it builds on and who builds on it |
| `impact` | the dependents of the schemas a task changes, and the other active tasks that change or affect them; exit 1 on a conflict |
| `layers` | the copies of a schema on an environment, applied first to last; exit 1 when the Custom layer has one |
| `snapshot` | an object as lines: effective columns over the workspace layers (disk), table columns / rows / checksums / copies (site) |
| `merge-plan` | the plan of collapsing each schema's replacing layers into one: target, additions, conflicts, dependencies; read-only, exit 1 on a conflict |
| `merge` | the replacing layers of one object collapsed into one layer of the target package; prints the files, --apply writes them; exit 1 when it stops |
| `compare` | two snapshot files: + - ~ lines; exit 1 on a difference |
| `export` | a snapshot for reading without the tools: one text file per schema, one per package |
| `diff` | the working copy against git HEAD, a revision or a folder, in schema terms: + added, - removed, ~ changed lines |
| `uid` | what a UId names in the workspace (a schema, a column, a process element or parameter), a dotted name's UId, or a text with every UId named |
| `review` | a pulled package against git HEAD: line endings / BOM only, content changes, dependencies, orphan resources; --keep restores the rest |
| `precommit` | the staged files that must not be committed: over 5 MB, archives, binaries outside Files/Bin, files outside packages/; exit 1 |
<!-- commands:end -->

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

## Schema diff

`describe.py diff <package> [<Schema>...] [--against HEAD|<rev>|<folder>]` (MCP `schema_diff`) is the change in
schema terms: the working copy against git HEAD (default), another revision, or a folder holding the package
(a pulled copy of the environment, a workspace, a folder of packages). Per item the lines the describe layer
prints - the summary and every list topic of its kind, unlimited - compared by their first word:

```
UsrOrder  object
  columns
    ~ UsrStatus  Lookup -> UsrOrderStatus 'Status' -> Lookup -> c59697c2-... 'Status'
    + UsrWeight Float 'Weight'
- UsrOrderStatus  object (removed)
UsrPkg against HEAD: 1 changed, 0 new, 1 removed; lines +1 -0 ~1
```

`+` added, `-` removed, `~ key  old -> new` changed; a key that repeats on a side (flows, rows) is compared by
whole lines. The summary adds only what the lists did not say; header lines, `files`, the index topics, `keys`
and the count-only `resources` are left out (a changed caption shows through its column's or element's line).
Nothing is written: the revision is extracted to a temporary folder and removed. The tester reads it to know
what the author changed before mapping the regression rows; the author, to check a pull did what it should.

## Review of a pulled package, and a pre-commit check

`describe.py review <package>` (MCP `review_download`) sorts the working copy against git HEAD: files that differ only
in line endings or a BOM (compared over the bytes - BOM dropped, CRLF read as LF - what
`git diff --stat -w --ignore-cr-at-eol` would call empty), the items changed in content (the schema diff above, renames
by UId included), dependencies dropped or added (descriptor.json `DependsOn` and the csproj references, the push's own
helper), resource folders whose schema is not in the package, and files git does not track. `--keep <Schema>...`
lists `git checkout HEAD -- <path>` for every changed tracked file outside the kept items (their `Schemas/`,
`Resources/<Item>.*`, `SqlScripts/`, `Data/` files) - the descriptor too, so dropped dependencies come back -
and `--apply` runs those lines. Untracked files are listed, never deleted. The MCP tool only prints.

`describe.py precommit <workspace>` (MCP `precommit_check`) lists the staged files that must not be committed and exits
1: over 5 MB, archives (`.rar .zip .7z .gz .bak`), binaries (`.dll .exe .pdb`) outside `packages/<P>/Files/Bin` of an
assembly package (descriptor `Type` 1), files outside `packages/` and the known roots (`.gitignore`, `.gitattributes`,
`.editorconfig`, `README.md`, `project.json`, `.clio`, `.vscode`, `tasks`, `docs`). As a hook, `.git/hooks/pre-commit`:

```sh
#!/bin/sh
python "<knowledge base>/no-code/tools/describe/describe.py" precommit "$(git rev-parse --show-toplevel)"
```

## UIds

`describe.py uid <workspace> <text>` (MCP `resolve_uid`) names what a UId points at - a schema (own or
replacing copy), a column (`column UsrOrder.UsrAmount`), a process element or parameter - and goes the
other way for a dotted name (`UsrOrder.UsrAmount`, `UsrOrder_Process.ReadData.ResultEntity`,
`UsrOrder_Process.OrderId`). A text with UIds in it - a meta path copied from `SysSchema` metadata, a
filter, several of them - comes back with every UId named, then the text with the names in place:

```
59bdd0b9-...  process UsrOrder_Process element ReadData (UserTask)
c7dfd892-...  process UsrOrder_Process element ReadData parameter ResultEntity
ef3edc7c-...  column UsrOrder.UsrAmount

[Element:{ReadData}].[Parameter:{ResultEntity}].[EntityColumn:{UsrAmount}]
```

Schemas come from the workspace scan, columns from every object's metadata, process items from the
processes - each map is built only when a question needs it. A UId the workspace does not hold (a lookup
row, a system record) says so; `env_sql` finds those.

## Lookups

`describe.py lookups <workspace|package>` (MCP `list_lookups`) lists every object whose parent
chain reaches `BaseLookup` - through the workspace's own objects or the stock ones
(`entity/assets/stock_lookups_8.3.2.json`, 496 names; the 8.2.3 list of 272 is the fallback) - with package, caption, the chain, own
columns, the data bindings that seed it (rows counted) and how many items refer to it. That is
the list a de-duplication or binding-value task starts from. An object whose parent is outside
both the workspace and the stock list is reported as *not decided* rather than guessed.

## Snapshot of an object

`describe.py snapshot <Schema> [--workspace <ws>] [-e <env>] [--columns a,b] [--out <file>]` (library
`creatio_schemas/integrity.py::snapshot`) prints what an object is as lines, and `describe.py compare <before> <after>`
prints the `+ - ~` lines between two of them (`diff_lines`, the same as `diff`) and exits 1 on any difference: an empty
compare after a layer merge is the proof that nothing observable changed.

Disk (`--workspace`), the effective object over every layer in `describe/merge.py::layers_in_order` (the site's order with
`-e`, else dependency order with `siblings ordered by name` when two layers are not ordered by `DependsOn`):

```
layers: UsrPkg > UsrPkg2
column UsrRating 6bfc7215-... Integer required default 3
column Owner 7c85a229-... Lookup lookup Contact default 4f367ca9-...
index IAccountAlternativeName on AlternativeName
```

The first layer's parent (its own copy, or the base `objects.py base` fetched) takes each layer's diff in turn
(`SchemaDiff.apply`, the code `EntitySchema.effective` runs for one layer). A vendor base that is neither on disk nor
fetched stops the snapshot with the `objects.py base` command to run: it would describe the additions only.

Site (`-e`), one statement each, written in [env](../env/README.md#snapshot-of-an-object): `table <T> column <col> <type>`,
`rows <n>`, `checksum <col> <md5>`, `copy <package> extendParent=<bool>`. The MCP tools are `schema_snapshot` and
`snapshot_compare`. A planted difference is tested: a copy of the fixture workspace with one layer's column removed compares
as `- column UsrRating ...`.

## Merge plan

`describe.py merge-plan <workspace> [<Schema>...] [-e <env>] [--limit N]` (MCP `merge_plan`; library
`describe/merge.py::merge_plan`): for each schema with a replacing copy in more than one package of the workspace
(or the named ones), what collapsing those layers into one would do. Read-only: it opens the layer files and
writes nothing, no `.creatio-index` either, so it runs on a client workspace as it is.

```
Contact object: 3 layers, target UsrA
  layer UsrA: +1 column
  layer UsrB: +3 columns
  layer UsrC: +1 column
  siblings: UsrB, UsrC (order guessed)
  conflict lookup UsrStatus -> UsrBStatus (its package UsrB depends on the target): UsrB
  conflict column UsrDup (two UIds): UsrB and UsrC
  depends: UsrA gains UsrExtra
UsrThing object: 2 layers, no common lowest package: UsrB, UsrC
3 schemas, 3 layers to remove, 4 conflicts, 1 without a common lowest package
```

- **Target**: the package every other layer's package depends on, directly or through other workspace packages
  (`DependsOn`). Without one the schema is skipped with `no common lowest package: <the bottom layers>`.
- **Layers** in `layers_in_order` (the site's order with `-e`, a copy only on the site says `on the site only, not
  merged`); the counts come from the describe answers: an object's added columns, a client schema's `diff` items
  and `methods`, a page's `viewConfigDiff` items and `handlers`.
- **Conflicts**, each a stop for the merge: one column name with two UIds; one column UId with two types; two layers
  with a `merge` / `remove` / `move` on one element (an `insert` below and a `merge` above is the normal form); one
  method overridden in two layers (`three-deep override` from three), and in such a method a `callParent` inside a
  nested function or with its value assigned; a lookup column whose object lives in a package that depends on the
  target (the merged layer could not see it); an unreadable layer.
- **`depends:`** the packages a removed layer's package depends on that the target does not reach yet, leaving out
  the layer packages and any package that depends on the target (that would be a cycle).
- Exit code 1 when there is a conflict, 2 on an error.

## Merge of an object

`describe.py merge <workspace> <Object> [--target <pkg>] [-e <env>] [--apply]` (MCP `merge_layers`, which prints only;
library `describe/merge.py::merge_object`): the replacing layers of one object collapsed into one layer of the target
package. It prints the merge plan for the object, then `write <file>` / `delete <folder>` per file, and writes only with
`--apply`. It stops with `stopped: ... - nothing written` and exit 1 on a plan conflict, on siblings without `-e` (their
order is the site's `SysPackage.HierarchyLevel`, which the files cannot show), on a layer that stores the whole schema,
on a layer the site holds and the workspace does not (a vendor package) that folds after the target - the merge would put the
removed layers' lines before it - and with `-e` on a site row that still points at a layer to remove (the statements are in `env/README.md`, "References
to a layer a merge removes").

- **The diff**: every layer's lines in fold order (the site's `HierarchyLevel` with `-e`, the dependency depth and the name
  without it), as the platform folds them. The lines that say whose layer it is (`UId`, `A5`, `B6`, `B8`, `D36.A3`, `EG1.UId`,
  `EG1.A2`, `EG1.A5`, `EG1.B8`, `EG1.BK8`) come from one layer only; `B6` is the target package. From every layer but the
  top, the lines `EntitySchemaManager.ActualizeSchemaDifferencePackage` drops are left out (an add on a path holding
  `EG1` and `C2`, a remove on `D20.FA*`). The UIds of the removed layers and of their packages become the merged layer's
  and the target's, so each column's `A3` / `A4` / `A5` (created in schema, modified in schema, created in package) names
  the layer that now holds it.
- **The UId**: the target's own layer's when it has one, else the top layer's (`--target` may name a package below every
  layer that holds none).
- **The other files**: `descriptor.json` and `<Object>.cs` of that same layer, `properties.json` of the top layer (the
  object flags of the whole fold), the resource files merged key by key with the upper layer winning.
- **The removed layers**: `Schemas/<Object>` and `Resources/<Object>.Entity` deleted from their packages; `push-pkg` of
  each package then drops its `SysSchema` row, and the table columns and their data stay (S24-T01). No backup step.
- **`DependsOn`**: the target gains the `depends:` packages of the plan, each entry copied from the removed package's
  descriptor.
- Push the packages in any order (the target first is the natural one). Proved on the test site: three layers (two of them
  siblings) merged, the three packages pushed, the snapshot's columns, table, rows and checksums the same before and
  after, the merged layer pulled back byte-identical.

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

The same order over a workspace, for code: `creatio_schemas/describe/merge.py::layers_in_order(workspace, schema,
env=None, manager=None)` returns `Layer(package, folder, replacing, uid, manager, source, siblings)` applied first
to last, in the order the runtime folds them (`SysPackage.HierarchyLevel`: the dependency depth, then the name in
ordinal order). With `env`: the site's copies (`source = "site"`; a site-only copy has `folder = None`), the replacing
ones re-sorted by the site's `HierarchyLevel` (the design-time function above has no tiebreak for siblings); a workspace
copy not on the site yet comes last. Without it, the workspace's copies: the own copy first, then the replacing ones by
their depth over the workspace's `DependsOn` and the name; two copies with no dependency path either way name each
other in `siblings` - their depth may differ through vendor packages the workspace does not hold, so the order is a
guess. It reads descriptors only and writes nothing into the workspace. The layer merge (S24) takes its order from it.

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
