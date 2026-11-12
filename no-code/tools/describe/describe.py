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
    python describe.py snapshot <Schema> [--workspace <ws>] [-e <env>] [--columns a,b] [--out <file>]  # an object as lines: effective columns on disk; table, rows, checksums, copies on a site
    python describe.py compare <before> <after>                    # two snapshot files: + - ~ lines; exit 1 on a difference
    python describe.py merge-plan <workspace> [<Schema>...] [-e <env>]  # collapsing replacing layers into one: target, conflicts; exit 1 on a conflict
    python describe.py merge   <workspace> <Object> [--target <pkg>] [-e <env>] [--apply]  # the object's layers as one layer of the target; exit 1 when it stops
    python describe.py export  <workspace|package> [--out <folder>]    # a text file per schema and per package (default <workspace>/.creatio-export)
    python describe.py diff    <package> [<Schema>...] [--against HEAD|<rev>|<folder>]  # what changed, in schema terms: + - ~ lines
    python describe.py review  <package> [--keep <Schema>...] [--apply]   # a pulled package sorted: line endings only, content, deps, orphans
    python describe.py precommit <workspace>                       # staged files that must not be committed (size, archives, binaries); exit 1
    python describe.py uid     <workspace|package> <uid | Schema.Column | Process.Element[.Param] | "<text with UIds>">  # what a UId names, and back

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


def snapshot_command(args) -> int:
    from creatio_schemas.environment import open_environment
    from creatio_schemas.integrity import compare, snapshot
    try:
        if args.command == "compare":
            diff = compare(Path(args.before).read_text(encoding="utf-8").splitlines(), Path(args.after).read_text(encoding="utf-8").splitlines())
            print("\n".join(diff) if diff else "same")
            return 1 if diff else 0
        if not args.workspace and not (args.env or args.project):
            raise ValueError("give --workspace (the disk lines), -e / --project (the site lines), or both")
        env = open_environment(args.env, args.project) if args.env or args.project else None
        lines = snapshot(args.workspace, args.schema, env, [c.strip() for c in args.columns.split(",") if c.strip()] or None)
    except (ValueError, KeyError, OSError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    if args.out:
        Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


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
    i.add_argument("--kind", default="", help="only dependents of this kind (page, process, rules, dcm, data, csharp ...)")
    i.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    g = sub.add_parser("layers", help="the copies of a schema on an environment, applied first to last; exit 1 when the Custom layer has one")
    g.add_argument("schema")
    g.add_argument("-e", "--env", help="clio environment name")
    g.add_argument("--project", help="project.json: the environment and environment.customLayer")
    g.add_argument("--rule", help="a business rule UId: its state in every layer")
    g.add_argument("--custom-layer", help="the customisation package (default: project.json environment.customLayer, else Custom)")
    g.add_argument("--json", action="store_true", help="the result as JSON, for evidence")
    sn = sub.add_parser("snapshot", help="an object as lines: effective columns over the workspace layers (disk), table columns / rows / checksums / copies (site)")
    sn.add_argument("schema")
    sn.add_argument("--workspace", help="the workspace: the effective columns over its layers (in the site's order with -e)")
    sn.add_argument("-e", "--env", help="clio environment name")
    sn.add_argument("--project", help="project.json holding the environment")
    sn.add_argument("--columns", default="", help="comma list of columns to checksum (default: all but Id)")
    sn.add_argument("--out", help="also write the lines to this file (the evidence)")
    mp = sub.add_parser("merge-plan", help="the plan of collapsing each schema's replacing layers into one: target, additions, conflicts, dependencies; read-only, exit 1 on a conflict")
    mp.add_argument("path")
    mp.add_argument("schemas", nargs="*", metavar="Schema", help="only these (default: every schema replaced by more than one package)")
    mp.add_argument("-e", "--env", help="clio environment name: the layer order of the site")
    mp.add_argument("--project", help="project.json holding the environment")
    mp.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    mg = sub.add_parser("merge", help="the replacing layers of one object collapsed into one layer of the target package; prints the files, --apply writes them; exit 1 when it stops")
    mg.add_argument("path")
    mg.add_argument("schema")
    mg.add_argument("--target", help="the package to merge into (default: the lowest layer's); every layer's package must depend on it")
    mg.add_argument("-e", "--env", help="clio environment name: the site's layer order and the references check")
    mg.add_argument("--project", help="project.json holding the environment")
    mg.add_argument("--apply", action="store_true", help="write and delete the files (without it: print only)")
    cp = sub.add_parser("compare", help="two snapshot files: + - ~ lines; exit 1 on a difference")
    cp.add_argument("before")
    cp.add_argument("after")
    x = sub.add_parser("export", help="a snapshot for reading without the tools: one text file per schema, one per package")
    x.add_argument("path")
    x.add_argument("--out", help="the folder (default <workspace>/.creatio-export; elsewhere for a client workspace)")
    y = sub.add_parser("diff", help="the working copy against git HEAD, a revision or a folder, in schema terms: + added, - removed, ~ changed lines")
    y.add_argument("package")
    y.add_argument("schemas", nargs="*", metavar="Schema", help="only these items (default: the whole package)")
    y.add_argument("--against", help="a git revision (default HEAD) or a folder holding the package (a pulled copy)")
    z = sub.add_parser("uid", help="what a UId names in the workspace (a schema, a column, a process element or parameter), a dotted name's UId, or a text with every UId named")
    z.add_argument("path")
    z.add_argument("text", help="a UId, Schema.Column, Process.Element[.Parameter], or a text holding UIds (a meta path, a filter)")
    r = sub.add_parser("review", help="a pulled package against git HEAD: line endings / BOM only, content changes, dependencies, orphan resources; --keep restores the rest")
    r.add_argument("package")
    r.add_argument("--keep", nargs="*", metavar="Schema", help="the items to keep; every other changed file is restored from HEAD (printed; run with --apply)")
    r.add_argument("--apply", action="store_true", help="with --keep: run the git checkout lines")
    q = sub.add_parser("precommit", help="the staged files that must not be committed: over 5 MB, archives, binaries outside Files/Bin, files outside packages/; exit 1")
    q.add_argument("workspace")
    args = p.parse_args(argv)
    if args.command == "review":
        from creatio_schemas.describe.review import render, review
        try:
            print(render(review(args.package, args.keep, args.apply and args.keep is not None)))
        except (FileNotFoundError, RuntimeError, QueryError) as e:
            print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
            return 2
        return 0
    if args.command == "precommit":
        from creatio_schemas.describe.review import precommit
        try:
            problems = precommit(args.workspace)
        except (FileNotFoundError, RuntimeError) as e:
            print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
            return 2
        print("\n".join(problems) if problems else "ok")
        return 1 if problems else 0
    if args.command == "layers":
        return layers_command(args)
    if args.command in ("snapshot", "compare"):
        return snapshot_command(args)
    if args.command in ("merge-plan", "merge"):
        from creatio_schemas.describe.merge import merge_object, merge_plan
        from creatio_schemas.environment import open_environment
        try:
            env = open_environment(args.env, args.project) if args.env or args.project else None
            if args.command == "merge":
                text, code = merge_object(args.path, args.schema, args.target, env, args.apply)
            else:
                text, conflicts = merge_plan(args.path, args.schemas, env, args.limit)
                code = 1 if conflicts else 0
        except (ValueError, KeyError, OSError, RuntimeError, QueryError) as e:
            print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
            return 2
        print(text)
        return code
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
            text, conflicts = impact(args.path, args.schemas, args.tasks, args.current, args.md, args.limit, args.kind)
            print(text)
            return 1 if conflicts else 0
        elif args.command == "schema":
            print(describe_schema(args.package, args.schema, args.limit))
        elif args.command == "export":
            from creatio_schemas.describe.export import export
            print(export(args.path, args.out))
        elif args.command == "diff":
            from creatio_schemas.describe.diff import schema_diff
            print(schema_diff(args.package, args.schemas, args.against))
        elif args.command == "uid":
            from creatio_schemas.describe.uids import resolve
            print(resolve(args.path, args.text))
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
