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

The index checks itself on every use: a file whose size or mtime changed, a schema folder that
appeared (after `clio pull-pkg`) or disappeared is re-read before the answer, and when names
appear or disappear every item's references are rescanned. There is no refresh hook to wire into
a pull script; `describe.py index <workspace>` after a pull only tells what changed. `--rebuild`
starts over.

## Lookups

`describe.py lookups <workspace|package>` (MCP `list_lookups`) lists every object whose parent
chain reaches `BaseLookup` - through the workspace's own objects or the stock ones
(`entity/assets/stock_lookups_8.2.3.json`, 272 names) - with package, caption, the chain, own
columns, the data bindings that seed it (rows counted) and how many items refer to it. That is
the list a de-duplication or binding-value task starts from. An object whose parent is outside
both the workspace and the stock list is reported as *not decided* rather than guessed.

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

| Kind | Topics |
| --- | --- |
| every schema | `files`, `resources [culture=]`, `resource <key>` |
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

## Kinds without a toolkit

Mobile settings, images and the other addons are listed at package level with their files and
sizes (`describe_item ... files`); resources as a kind of their own are S13-T05.

## Checks

`python tests/test_describe.py` - runs on the other toolkits' fixtures.
