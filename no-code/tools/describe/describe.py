#!/usr/bin/env python3
"""What a package holds, what a schema is, one part of it - without reading the files (library: ../creatio_schemas/describe).

    python describe.py package <package> [--kind object|process|rules|page|sql|client|addon|source|csharp|dcm|user-task]
    python describe.py schema  <package> <Schema>
    python describe.py item    <package> <Schema> "<topic> [<name>] [key=value ...]"
    python describe.py item    <package> <Schema> topics                 # what this schema can answer
    python describe.py index   <workspace|package> [--rebuild]           # build/refresh the index (.creatio-index/<Package>.json)
    python describe.py find    <workspace|package> <Schema>              # package, files, refers to, used by

Topics: every schema - files, resources [culture=], resource <key>, missing [culture=] [from=];
  object  - columns [type= flag= own=true], column <name>, flags, base
  process - elements [kind=], element <name>, params [direction=], flows [from= to=], script <element>
  rules   - rules [enabled=], rule <name>
  sql     - body, deps
  dcm     - stages, stage <name>, steps [stage=], step <name>, moves [from= to=], filter [raw=true]
  user-task - params [direction=], param <name>, methods, method <name>, source
  data (a Data/<Name> binding) - columns, rows [limit=] [culture=], row <key>; `package <pkg> --kind data` lists them
  classic (7.x client schema) - diff [op=] [parent=], element <name>, methods, method <name>, messages, attributes, details, mixins, find <text>
  C# (a source code schema, or Files/cs/X.cs by path, file name or stem) - classes [role=] [kind=] [generated=true],
            members [<Type>] [kind=method|property|field|const] [visibility=public], member <Type.Name>, usings, regions,
            operations [kind=], find <text>
  page    - sections, elements [type= parent=], element <name>, attributes [bound=true], attribute <name>,
            data-sources, handlers, handler <request>, validators, converters, containers, find <text>
    python describe.py lookups <workspace|package>                      # every lookup object: parent chain, bindings, users
    python describe.py deps    <workspace|package> <Schema> [--in|--out] [--kind object] [--via lookup]  # typed graph
    python describe.py impact  <workspace|package> <Schema>... [--tasks <folder>] [--current <task>] [--md]  # dependents + locks
    python describe.py layers  <Schema> -e <env> [--rule <UId>] [--json]  # the SysSchema copies on an environment, Custom detected
    python describe.py export  <workspace|package> [--out <folder>]    # a text file per schema and per package (default <workspace>/.creatio-export)

The same calls are MCP tools of the creatio-kb server (describe_package, describe_schema, describe_item, index_workspace, find_schema, list_lookups).
The index checks itself against the disk on every call: after `clio pull-pkg` the next call sees the new schemas.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.describe import DEFAULT_LIMIT, QueryError, describe_item, describe_package, describe_schema, find_schema, index_workspace, lookups  # noqa: E402


def layers_command(args) -> int:
    import json

    from creatio_schemas.describe.layers import CUSTOM_LAYER, render, schema_layers, to_json
    from creatio_schemas.environment import open_environment
    try:
        custom = args.custom_layer
        if not custom and args.project:
            custom = json.loads(Path(args.project).read_text(encoding="utf-8-sig")).get("environment", {}).get("customLayer")
        env = open_environment(args.env, args.project)
        result = schema_layers(env, args.schema, args.rule, custom or CUSTOM_LAYER)
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    print(to_json(result) if args.json else render(result, env.clio_name or env.url))
    return 1 if result["custom"] else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("package", help="one line per schema")
    a.add_argument("package")
    a.add_argument("--kind", default="")
    a.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    b = sub.add_parser("schema", help="the summary of one schema")
    b.add_argument("package")
    b.add_argument("schema")
    b.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="lines to show (0 = all); the rest is one '... N more' line")
    c = sub.add_parser("item", help="one part of a schema")
    c.add_argument("package")
    c.add_argument("schema")
    c.add_argument("query", nargs="?", default="topics")
    d = sub.add_parser("index", help="build or refresh the package index")
    d.add_argument("path")
    d.add_argument("--rebuild", action="store_true")
    e = sub.add_parser("find", help="where a schema lives and what touches it")
    e.add_argument("path")
    e.add_argument("schema")
    e.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    f = sub.add_parser("lookups", help="every lookup object (parent chain reaches BaseLookup) with bindings and users")
    f.add_argument("path")
    f.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    h = sub.add_parser("deps", help="typed dependencies of a schema over the workspace: what it builds on and who builds on it")
    h.add_argument("path")
    h.add_argument("schema")
    h.add_argument("--in", dest="direction", action="store_const", const="in", default="both", help="dependents only")
    h.add_argument("--out", dest="direction", action="store_const", const="out", help="what it depends on only")
    h.add_argument("--kind", default="", help="only edges to / from this kind (object, process, page, ...)")
    h.add_argument("--via", default="", help="only this relation (lookup, signal, data-source, ...)")
    h.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    i = sub.add_parser("impact", help="the dependents of the schemas a task changes, and the other active tasks that change or affect them; exit 1 on a conflict")
    i.add_argument("path")
    i.add_argument("schemas", nargs="+", metavar="Schema")
    i.add_argument("--tasks", help="the loop's tasks folder (project.json paths.tasks): locks of the other active tasks are checked")
    i.add_argument("--current", help="this task's folder name, left out of the lock check")
    i.add_argument("--md", action="store_true", help="the `## Impact` table for plan.md and the `affects:` line for schemas.json")
    i.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    g = sub.add_parser("layers", help="the copies of a schema on an environment, applied first to last; exit 1 when the Custom layer has one")
    g.add_argument("schema")
    g.add_argument("-e", "--env", help="clio environment name")
    g.add_argument("--project", help="project.json: the environment and environment.customLayer")
    g.add_argument("--rule", help="a business rule UId: its state in every layer")
    g.add_argument("--custom-layer", help="the customisation package (default: project.json environment.customLayer, else Custom)")
    g.add_argument("--json", action="store_true", help="the result as JSON, for evidence")
    x = sub.add_parser("export", help="a snapshot for reading without the tools: one text file per schema, one per package")
    x.add_argument("path")
    x.add_argument("--out", help="the folder (default <workspace>/.creatio-export; elsewhere for a client workspace)")
    args = p.parse_args(argv)
    if args.command == "layers":
        return layers_command(args)
    try:
        if args.command == "package":
            print(describe_package(args.package, args.kind, args.limit))
        elif args.command == "lookups":
            print(lookups(args.path, args.limit))
        elif args.command == "deps":
            from creatio_schemas.describe.deps import dependencies
            print(dependencies(args.path, args.schema, args.direction, args.kind, args.via, args.limit))
        elif args.command == "impact":
            from creatio_schemas.describe.deps import impact
            text, conflicts = impact(args.path, args.schemas, args.tasks, args.current, args.md, args.limit)
            print(text)
            return 1 if conflicts else 0
        elif args.command == "schema":
            print(describe_schema(args.package, args.schema, args.limit))
        elif args.command == "export":
            from creatio_schemas.describe.export import export
            print(export(args.path, args.out))
        elif args.command == "index":
            print(index_workspace(args.path, args.rebuild))
        elif args.command == "find":
            print(find_schema(args.path, args.schema, args.limit))
        else:
            print(describe_item(args.package, args.schema, args.query))
    except (FileNotFoundError, KeyError, QueryError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
