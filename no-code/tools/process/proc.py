#!/usr/bin/env python3
"""
Inspect and change business processes stored in a package (library: ../creatio_schemas/process).

    python proc.py inspect   <package> <Process>
    python proc.py new       <package> <Process> --caption "..." [--cultures en-US ru-RU]
    python proc.py caption   <package> <Process> <target> en-US="..." [ru-RU="..."]   target: Process | Element | Element.Param | Parameter:Name
    python proc.py captions  <package> <Process> [--missing] [--from en-US]
    python proc.py fill-captions <package> <Process> [--from en-US]
    python proc.py param     <package> <Process> add <Name> --type Text [--direction In|Out|Variable] [--caption ..] [--default ..] [--ref-schema Contact]
    python proc.py param     <package> <Process> rename <Old> <New> | remove <Name>
    python proc.py element   <package> <Process> add <Name> --kind readData --after X [--before Y] [--caption ..] [--entity UsrOrder] [--set Param=value ..]
    python proc.py element   <package> <Process> rename <Old> <New> | remove <Name> | set <Name> Param=value .. [--expr]
    python proc.py element   <package> <Process> formula <Name> "<expression>" --result <ProcessParam>
    python proc.py element   <package> <Process> values <Name> Column=value .. [--expr]     Add / Modify data: the columns it writes
    python proc.py element   <package> <Process> map <Name> Param=value .. [--expr]        sub-process: the called process's parameters
    python proc.py flow      <package> <Process> add <Src> <Dst> [--condition "{Parameter:X} > 0"] [--name ..] [--caption ..]
    python proc.py flow      <package> <Process> remove <Name> | condition <Name> "<expr>"
    python proc.py script    <package> <Process> get <Element> [--out file] | set <Element> --file body.cs
    python proc.py validate  <package> <Process>

Every writing command accepts --dry-run: it prints the unified diff and changes nothing.
Expressions use {Parameter:Name} and {Element:El.Parameter:P} in place of the designer's
UId meta paths; the rest of the text is passed through.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas import DATA_VALUE_TYPES, DVT_OF, ProcessSchema  # noqa: E402
from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.process.catalog import DIRECTION, short_type  # noqa: E402
from creatio_schemas.process import ELEMENT_KINDS, TASK_ALIASES  # noqa: E402
from creatio_schemas.process.schema import SIGNAL_KEYS  # noqa: E402


# -- whole process ------------------------------------------------------------ #

def new(_, a):
    print(ProcessSchema.create(Path(a.package), a.process, a.caption, a.cultures).describe())


def test_config(proc, a):
    """The parameter list a process case validates against (name, type, in | out | variable)."""
    data = {"name": proc.name, "parameters": [
        {"code": p["A2"], "type": DATA_VALUE_TYPES.get(p.get("L1"), p.get("L1")), "direction": DIRECTION.get(p.get("L12", 0), "Variable").lower()}
        for p in proc.params if DIRECTION.get(p.get("L12", 0)) != "Internal"]}
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}: {len(data['parameters'])} parameter(s)")
    else:
        print(text, end="")


def inspect(proc, a):
    print(proc.describe())


def validate(proc, a):
    problems = proc.validate()
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


# -- captions ------------------------------------------------------------------ #

def caption(proc, a):
    values = parse_assignments(a.values)
    if not values:
        raise SystemExit('give culture=value pairs, e.g. en-US="Read contact"')
    for culture, value in values.items():
        print(f"{culture}: {proc.set_caption(a.target, value, [culture])} = {value!r}")


def captions(proc, a):
    if a.missing:
        for culture, keys in proc.resources.missing(a.source).items():
            if keys:
                print(f"{culture}: {len(keys)} missing")
                for k in keys:
                    print(f"   {k} = {proc.resources.get(k, a.source)!r}")
        return
    for k, v in sorted(proc.resources.cultures.get(a.source, {}).items()):
        print(f"{k} = {v!r}")


def fill_captions(proc, a):
    n = 0
    for culture, keys in proc.resources.missing(a.source).items():
        for k in keys:
            proc.resources.set(k, proc.resources.get(k, a.source), [culture])
            n += 1
    print(f"copied {n} caption(s) from {a.source}")


# -- elements -------------------------------------------------------------------- #

def element_signal(proc, a, el=None):
    el = el or proc.element(a.name)
    proc.set_signal(el, a.entity, a.on, a.columns.split(",") if a.columns else None, a.filter)


def element_add(proc, a):
    el = proc.add_element(a.kind, a.name, a.caption or "", a.after, a.before)
    if short_type(el) in SIGNAL_KEYS and (a.entity or a.on or a.columns or a.filter):
        element_signal(proc, a, el)
    elif a.entity:
        proc.set_entity(el, a.entity)
    if a.calls:
        proc.set_calls(el, a.calls)
    if a.message:
        proc.set_message(el, a.message)
    for k, v in parse_assignments(a.set).items():
        proc.set_value(el, k, v, a.expr)


def element_set(proc, a):
    el = proc.element(a.name)
    for k, v in parse_assignments(a.values).items():
        proc.set_value(el, k, v, a.expr)


def script_get(proc, a):
    body = proc.get_script(a.element)
    if a.out:
        Path(a.out).write_text(body, encoding="utf-8")
        print(f"{len(body)} chars -> {a.out}")
    else:
        print(body)


def build() -> CommandLine:
    cli = CommandLine(__doc__, "process")
    c = cli.command
    p = c("new", new, "create a process: one lane, start -> terminate", target=False)
    p.add_argument("package")
    p.add_argument("process")
    p.add_argument("--caption", required=True)
    p.add_argument("--cultures", nargs="*")
    c("inspect", inspect, "elements, parameters, flows and problems, with decoded names")
    c("validate", validate, "problems only; exit code 1 when there are any")
    p = c("test-config", test_config, "write the process's parameters as a Configuration/processes file of the UI test utility")
    p.add_argument("--out", help="file to write (default: print)")

    p = c("caption", caption, "set a caption: Process | Element | Element.Param | Parameter:Name | a raw key", writes=True)
    p.add_argument("target")
    p.add_argument("values", nargs="+", metavar="culture=value")
    p = c("captions", captions, "list captions of a culture, or those missing in the others")
    p.add_argument("--from", dest="source", default="en-US")
    p.add_argument("--missing", action="store_true")
    p = c("fill-captions", fill_captions, "copy captions missing in a culture from --from", writes=True)
    p.add_argument("--from", dest="source", default="en-US")

    g = cli.group("param", "process parameters")
    p = c("add", lambda proc, a: proc.add_param(a.name, a.type, a.direction, a.caption or "", a.default, a.ref_schema), "add a parameter", True, g)
    p.add_argument("name")
    p.add_argument("--type", required=True, choices=sorted(DVT_OF))
    p.add_argument("--direction", default="Variable", choices=["In", "Out", "Variable"])
    p.add_argument("--caption")
    p.add_argument("--default")
    p.add_argument("--ref-schema", help="Lookup: the reference schema name")
    p = c("rename", lambda proc, a: proc.rename_param(a.old, a.new), "rename a parameter (its captions follow)", True, g)
    p.add_argument("old")
    p.add_argument("new")
    p = c("remove", lambda proc, a: proc.remove_param(a.name), "remove a parameter", True, g)
    p.add_argument("name")

    g = cli.group("element", "process elements")
    p = c("add", element_add, "add an element; --after wires a flow, --before re-points the existing one", True, g)
    p.add_argument("name")
    p.add_argument("--kind", required=True, help=f"{', '.join(list(ELEMENT_KINDS) + list(TASK_ALIASES))} or userTask:<TaskSchema>")
    p.add_argument("--caption")
    p.add_argument("--after")
    p.add_argument("--before")
    p.add_argument("--entity", help="data elements and record-signal starts: entity schema name (resolved from the workspace) or its UId")
    p.add_argument("--calls", help="sub-process: the process to call, by name or UId")
    p.add_argument("--message", help="message / signal events: the message name (a start or catch signal then waits for that named signal)")
    p.add_argument("--on", help="record signals: added, modified, deleted - several joined by a comma")
    p.add_argument("--columns", help="record signals, modified: the columns whose change fires it, joined by a comma")
    p.add_argument("--filter", help='record signals: conditions the record must meet, e.g. "UsrAmount > 100; UsrStatus is not null"')
    p.add_argument("--set", nargs="*", default=[], metavar="Param=value")
    p.add_argument("--expr", action="store_true", help="the --set values are expressions")
    p = c("signal", element_signal, "record signal of a start or catch signal: entity, what fires it, columns, conditions", True, g)
    p.add_argument("name")
    p.add_argument("--entity")
    p.add_argument("--on")
    p.add_argument("--columns")
    p.add_argument("--filter")
    p = c("rename", lambda proc, a: proc.rename_element(a.old, a.new), "rename an element (mappings, labels, captions follow)", True, g)
    p.add_argument("old")
    p.add_argument("new")
    p = c("remove", lambda proc, a: proc.remove_element(a.name), "remove an element with its flows and mappings", True, g)
    p.add_argument("name")
    p = c("set", element_set, "set element parameter values", True, g)
    p.add_argument("name")
    p.add_argument("values", nargs="+", metavar="Param=value")
    p.add_argument("--expr", action="store_true")
    p = c("values", lambda proc, a: proc.set_record_values(proc.element(a.name), parse_assignments(a.values), a.expr),
          "Add / Modify data: column values (constants typed by the column, or {Parameter:X} expressions)", True, g)
    p.add_argument("name")
    p.add_argument("values", nargs="+", metavar="Column=value")
    p.add_argument("--expr", action="store_true", help="every value is an expression")
    p = c("map", lambda proc, a: proc.map_params(proc.element(a.name), parse_assignments(a.values), a.expr),
          "sub-process: values for the called process's parameters", True, g)
    p.add_argument("name")
    p.add_argument("values", nargs="+", metavar="Param=value")
    p.add_argument("--expr", action="store_true", help="every value is an expression")
    p = c("formula", lambda proc, a: proc.set_formula(a.name, a.expression, a.result), "formula task: expression -> process parameter", True, g)
    p.add_argument("name")
    p.add_argument("expression")
    p.add_argument("--result", required=True, help="the process parameter that receives the value")

    g = cli.group("flow", "sequence and conditional flows")
    p = c("add", lambda proc, a: proc.add_flow(a.src, a.dst, a.condition, a.name, a.caption), "add a flow", True, g)
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--condition")
    p.add_argument("--name")
    p.add_argument("--caption")
    p = c("remove", lambda proc, a: proc.remove_element(a.name), "remove a flow", True, g)
    p.add_argument("name")
    p = c("condition", lambda proc, a: proc.set_condition(a.name, a.condition), "set a condition (a plain flow becomes conditional)", True, g)
    p.add_argument("name")
    p.add_argument("condition")

    g = cli.group("script", "script task bodies")
    p = c("get", script_get, "print or save the C# body", under=g)
    p.add_argument("element")
    p.add_argument("--out")
    p = c("set", lambda proc, a: proc.set_script(a.element, Path(a.file).read_text(encoding="utf-8")), "replace the C# body from a file", True, g)
    p.add_argument("element")
    p.add_argument("--file", required=True)
    return cli


def main(argv: list[str]) -> int:
    return build().run(argv, lambda a: None if a.command == "new" else ProcessSchema(Path(a.package), a.process))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
