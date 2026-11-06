#!/usr/bin/env python3
"""
Command line over pschema.py: inspect and change business processes stored in a package.

    python proc.py inspect   <package> <Process>
    python proc.py new       <package> <Process> --caption "..." [--cultures en-US ru-RU]
    python proc.py caption   <package> <Process> <target> en-US="..." [ru-RU="..."]   target: Process | Element | Element.Param | Parameter:Name
    python proc.py captions  <package> <Process> [--missing]
    python proc.py fill-captions <package> <Process> [--from en-US]
    python proc.py param     <package> <Process> add <Name> --type Text [--direction In|Out|Variable] [--caption ..] [--default ..] [--ref-schema Contact]
    python proc.py param     <package> <Process> rename <Old> <New> | remove <Name>
    python proc.py element   <package> <Process> add <Name> --kind readData --after X [--before Y] [--caption ..] [--entity UsrOrder] [--set Param=value ..]
    python proc.py element   <package> <Process> rename <Old> <New> | remove <Name> | set <Name> Param=value .. [--expr]
    python proc.py element   <package> <Process> formula <Name> "<expression>" --result <ProcessParam>
    python proc.py flow      <package> <Process> add <Src> <Dst> [--condition "{Parameter:X} > 0"] [--name ..] [--caption ..]
    python proc.py flow      <package> <Process> remove <Name> | condition <Name> "<expr>"
    python proc.py script    <package> <Process> get <Element> [--out file] | set <Element> --file body.cs
    python proc.py validate  <package> <Process>

Every writing command accepts --dry-run: it prints the unified diff and changes nothing.
Expressions use {Parameter:Name} and {Element:El.Parameter:P} in place of the designer's
UId meta paths; the rest of the text is passed through.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pschema import DVT_OF, Process, create_process  # noqa: E402


def parse_assignments(items: list[str]) -> dict[str, str]:
    out = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"expected Name=value, got {item!r}")
        k, v = item.split("=", 1)
        out[k] = v
    return out


def finish(proc: Process, dry_run: bool) -> None:
    if dry_run:
        for path, text in proc.files().items():
            try:
                with open(path, encoding="utf-8", newline="") as fh:
                    old = fh.read()
            except FileNotFoundError:
                old = ""
            if old != text:
                rel = str(path.relative_to(proc.package))
                sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"a/{rel}", f"b/{rel}"))
        print("\n(dry run: nothing written)")
        return
    problems = proc.validate()
    proc.save()
    print(f"saved {proc.name}" + (f"; validation: {len(problems)} problem(s)" if problems else ""))
    for p in problems:
        print("  -", p)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["inspect", "new", "caption", "captions", "fill-captions", "param", "element", "flow", "script", "validate"])
    ap.add_argument("package")
    ap.add_argument("process")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--caption")
    ap.add_argument("--cultures", nargs="*")
    ap.add_argument("--from", dest="source", default="en-US")
    ap.add_argument("--missing", action="store_true")
    ap.add_argument("--type")
    ap.add_argument("--direction", default="Variable")
    ap.add_argument("--default")
    ap.add_argument("--ref-schema")
    ap.add_argument("--kind")
    ap.add_argument("--after")
    ap.add_argument("--before")
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--expr", action="store_true")
    ap.add_argument("--condition")
    ap.add_argument("--name")
    ap.add_argument("--file")
    ap.add_argument("--out")
    ap.add_argument("--result")
    ap.add_argument("--entity", help="data elements and record-signal starts: entity schema name (resolved from the workspace) or its UId")
    ap.add_argument("--calls", help="sub-process: the process to call, by name or UId")
    ap.add_argument("--message", help="message / signal events: the message name")
    a = ap.parse_args(argv)
    pkg = Path(a.package)

    if a.command == "new":
        if not a.caption:
            raise SystemExit("--caption is required")
        if a.dry_run:
            print(f"would create {pkg / 'Schemas' / a.process}")
            return 0
        proc = create_process(pkg, a.process, a.caption, a.cultures)
        print(proc.describe())
        return 0

    proc = Process(pkg, a.process)
    sub = a.rest[0] if a.rest else ""
    args = a.rest[1:]

    if a.command == "inspect":
        print(proc.describe())
        return 0
    if a.command == "validate":
        problems = proc.validate()
        print("\n".join(problems) if problems else "ok")
        return 1 if problems else 0
    if a.command == "captions":
        if a.missing:
            for culture, keys in proc.resources.missing(a.source).items():
                if keys:
                    print(f"{culture}: {len(keys)} missing")
                    for k in keys:
                        print(f"   {k} = {proc.resources.get(k, a.source)!r}")
        else:
            for k, v in sorted(proc.resources.cultures.get(a.source, {}).items()):
                print(f"{k} = {v!r}")
        return 0
    if a.command == "fill-captions":
        n = 0
        for culture, keys in proc.resources.missing(a.source).items():
            for k in keys:
                proc.resources.set(k, proc.resources.get(k, a.source), [culture])
                n += 1
        print(f"copied {n} caption(s) from {a.source}")
        finish(proc, a.dry_run)
        return 0
    if a.command == "caption":
        values = parse_assignments(args)
        if not values:
            raise SystemExit("give culture=value pairs, e.g. en-US=\"Read contact\"")
        for culture, value in values.items():
            key = proc.set_caption(sub, value, [culture])
            print(f"{culture}: {key} = {value!r}")
        finish(proc, a.dry_run)
        return 0
    if a.command == "param":
        if sub == "add":
            if not a.type:
                raise SystemExit(f"--type is required; one of {', '.join(sorted(DVT_OF))}")
            proc.add_param(args[0], a.type, a.direction, a.caption or "", a.default, a.ref_schema)
        elif sub == "rename":
            proc.rename_param(args[0], args[1])
        elif sub == "remove":
            proc.remove_param(args[0])
        else:
            raise SystemExit("param add|rename|remove")
        finish(proc, a.dry_run)
        return 0
    if a.command == "element":
        if sub == "add":
            if not a.kind:
                raise SystemExit("--kind is required (readData, changeData, addData, deleteData, formula, script, exclusiveGateway, terminate, userTask:<Schema> ...)")
            el = proc.add_element(a.kind, args[0], a.caption or "", a.after, a.before)
            if a.entity:
                proc.set_entity(el, a.entity)
            if a.calls:
                proc.set_calls(el, a.calls)
            if a.message:
                proc.set_message(el, a.message)
            for k, v in parse_assignments(a.set).items():
                proc.set_value(el, k, v, a.expr)
        elif sub == "rename":
            proc.rename_element(args[0], args[1])
        elif sub == "remove":
            proc.remove_element(args[0])
        elif sub == "set":
            el = proc.element(args[0])
            for k, v in parse_assignments(args[1:]).items():
                proc.set_value(el, k, v, a.expr)
        elif sub == "formula":
            if not a.result:
                raise SystemExit("--result <ProcessParam> is required")
            proc.set_formula(args[0], args[1], a.result)
        else:
            raise SystemExit("element add|rename|remove|set|formula")
        finish(proc, a.dry_run)
        return 0
    if a.command == "flow":
        if sub == "add":
            proc.add_flow(args[0], args[1], a.condition, a.name, a.caption)
        elif sub == "remove":
            proc.remove_element(args[0])
        elif sub == "condition":
            proc.set_condition(args[0], args[1])
        else:
            raise SystemExit("flow add|remove|condition")
        finish(proc, a.dry_run)
        return 0
    if a.command == "script":
        if sub == "get":
            body = proc.get_script(args[0])
            if a.out:
                Path(a.out).write_text(body, encoding="utf-8")
                print(f"{len(body)} chars -> {a.out}")
            else:
                print(body)
            return 0
        if sub == "set":
            if not a.file:
                raise SystemExit("--file is required")
            proc.set_script(args[0], Path(a.file).read_text(encoding="utf-8"))
            finish(proc, a.dry_run)
            return 0
        raise SystemExit("script get|set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
