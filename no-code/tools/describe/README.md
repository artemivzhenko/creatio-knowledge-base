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
index. Classic UI client schemas, data bindings, services and C# are listed with their files
until their topics land.

## The package index

`<workspace>/.creatio-index/<Package>.json` (next to `packages/`; add the folder to the
workspace's `.gitignore`, it is a cache) holds, per schema, SQL script and data binding: kind,
caption, summary line, parent or target, every file with size and mtime, and the schemas of the
workspace it refers to - by name or by UId found in its text files. `describe_package` and
`find_schema` answer from it: a 578-schema package lists in 1.5 s instead of 35 s, and the agent
gets the files to open and the impact of a change in one call.

The index checks itself on every use: a file whose size or mtime changed, a schema folder that
appeared (after `clio pull-pkg`) or disappeared is re-read before the answer, and when names
appear or disappear every item's references are rescanned. There is no refresh hook to wire into
a pull script; `describe.py index <workspace>` after a pull only tells what changed. `--rebuild`
starts over.

## The query grammar

`<topic> [<name>] [key=value ...]` - `topics` lists what a schema can answer.

| Kind | Topics |
| --- | --- |
| every schema | `files`, `resources [culture=]`, `resource <key>` |
| object | `columns [type=Lookup] [flag=required] [own=true]`, `column <Name>` (line + raw JSON), `flags`, `base` |
| process | `elements [kind=FormulaTask]`, `element <Name>` (values, flows in and out), `params [direction=In]`, `flows [from=] [to=]`, `script <Element>` |
| rules | `rules [enabled=false]`, `rule <Name|caption|uid>` |
| sql | `body`, `deps` |
| dcm | `stages`, `stage <name|caption>` (steps, conditions, moves in and out), `steps [stage=]`, `step <name>`, `moves [from=] [to=]`, `filter [raw=true]` |
| user-task | `params [direction=]`, `param <name>`, `methods`, `method <name>` (one method's C#), `source` |
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

## Kinds without a toolkit

Classic UI client schemas, data bindings, C# and the other addons are listed at package level
with their files and sizes (`describe_item ... files`); their own topics are S13-T03..T06.

## Checks

`python tests/test_describe.py` - runs on the other toolkits' fixtures.
