#!/usr/bin/env python3
"""DCM cases (dynamic case management) stored in a package (library: ../creatio_schemas/dcm).

    python dcm.py inspect      <package> <Case>
    python dcm.py validate     <package> <Case>
    python dcm.py new          <package> <Case> --caption "Order cases" --entity UsrOrder --stage-column UsrStatus
                               [--stage "New=<record uid>" --stage "Done=<record uid>" ...] [--cultures en-US,ru-RU]
    python dcm.py add-stage    <package> <Case> --caption "On hold" --record <uid> [--name Stage7] [--color #FFAC07] [--parent Stage4]
    python dcm.py remove-stage <package> <Case> <stage>
    python dcm.py connect      <package> <Case> <from> <to> [--one-way]
    python dcm.py disconnect   <package> <Case> <from> <to> [--one-way]
    python dcm.py add-step     <package> <Case> --stage Stage2 --process UsrNotify_Process --caption "Notify"
                               [--name DcmElement5] [--map Request={Record:Id} ..] [--required] [--when "NextStage = Stage3 -> Stage3" ..]
    python dcm.py remove-step  <package> <Case> <step>
    python dcm.py set-caption  <package> <Case> <Caption|stage> <value>
    python dcm.py enable       <package> <Case>
    python dcm.py disable      <package> <Case>

A case runs on one object and one of its lookup columns (the stage column); a stage is a record of
that lookup, with a colour and optional steps (sub-processes started on entering the stage).
`connect` says which stage may follow which (both ways unless --one-way). Steps and their
conditions are written by add-step: --map gives the called process's parameters ({Record:Column} of the
case's record, {Parameter:X} of the case, or a constant), --when "Param op value -> Stage" moves the record
on a result (a lookup value may name a stage of the case).
Every writing command accepts --dry-run. After `clio push-pkg` (clear SysSchema.IsChanged first)
the case shows on the object's pages.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.dcm import DcmSchema  # noqa: E402


def inspect(case, a):
    print(case.describe())


def validate(case, a):
    problems = case.validate()
    for p in problems:
        print(p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if case.errors() else 0


def new(case, a):
    print(case.describe())


def add_stage(case, a):
    s = case.add_stage(a.caption, a.record, name=a.name, color=a.color, parent=a.parent)
    print(f"add stage {s['A2']} {a.caption!r} record {a.record}")


def add_step(case, a):
    conditions = []
    for spec in a.when:
        if "->" not in spec:
            raise ValueError(f'--when expects "Param op value -> Stage", got {spec!r}')
        when, stage = spec.rsplit("->", 1)
        conditions.append((when.strip(), stage.strip()))
    e = case.add_step(a.stage, a.name, a.process, a.caption, parse_assignments(a.map), a.required, conditions)
    print(f"add step {e['A2']} {a.caption!r} -> {a.process}")


def remove_stage(case, a):
    print(f"remove stage {case.remove_stage(a.stage)}")


def connect(case, a):
    case.connect(a.src, a.dst, both=not a.one_way)
    print(f"connect {a.src} {'->' if a.one_way else '<->'} {a.dst}")


def disconnect(case, a):
    print(f"disconnect {case.disconnect(a.src, a.dst, both=not a.one_way)} connection(s)")


def set_caption(case, a):
    print(f"set {case.set_caption(a.target, a.value)}")


def enable(case, a):
    case.set_enabled(True)
    print("enabled")


def disable(case, a):
    case.set_enabled(False)
    print("disabled")


def build() -> CommandLine:
    c = CommandLine(__doc__, "case")
    c.command("inspect", inspect, "object, stage column, filter, stages with steps and conditions, moves")
    c.command("validate", validate, "problems; exit code 1 on errors")
    p = c.command("new", new, "an empty case on an object's lookup column, stages optional")
    p.add_argument("--caption", required=True)
    p.add_argument("--entity", required=True, help="the object (must be in the workspace)")
    p.add_argument("--stage-column", required=True, help="a lookup column of the object")
    p.add_argument("--stage", action="append", default=[], metavar="CAPTION=RECORD_UID", help="repeatable; stages are connected in a chain")
    p.add_argument("--cultures", default="en-US")
    p = c.command("add-stage", add_stage, "a stage for a record of the stage column's lookup", writes=True)
    p.add_argument("--caption", required=True)
    p.add_argument("--record", required=True, help="UId of the lookup record")
    p.add_argument("--name")
    p.add_argument("--color", default="#4D84E2")
    p.add_argument("--parent", help="make it an alternative of this stage")
    p = c.command("remove-stage", remove_stage, "drop a stage, its connections and captions", writes=True)
    p.add_argument("stage")
    p = c.command("add-step", add_step, "a step that starts a process of the workspace on a stage", writes=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--process", required=True)
    p.add_argument("--caption", required=True)
    p.add_argument("--name")
    p.add_argument("--map", action="append", default=[], metavar="PARAM=VALUE", help="repeatable; {Record:Column}, {Parameter:X} or a constant")
    p.add_argument("--required", action="store_true")
    p.add_argument("--when", action="append", default=[], metavar='"Param op value -> Stage"', help="repeatable; a result condition")
    p = c.command("remove-step", lambda case, a: print(f"remove step {case.remove_step(a.step)}"), "drop a step, its mappings and captions",
                  writes=True)
    p.add_argument("step")
    for name, fn, help_ in (("connect", connect, "allow moving between two stages"), ("disconnect", disconnect, "forbid moving between two stages")):
        p = c.command(name, fn, help_, writes=True)
        p.add_argument("src")
        p.add_argument("dst")
        p.add_argument("--one-way", action="store_true")
    p = c.command("set-caption", set_caption, "the case caption (target Caption) or a stage caption", writes=True)
    p.add_argument("target")
    p.add_argument("value")
    c.command("enable", enable, "set Enabled", writes=True)
    c.command("disable", disable, "clear Enabled", writes=True)
    return c


def open_schema(a):
    if a.command == "new":
        stages = []
        for spec in a.stage:
            if "=" not in spec:
                raise ValueError(f"--stage expects CAPTION=RECORD_UID, got {spec!r}")
            caption, record = spec.split("=", 1)
            stages.append((caption, record))
        return DcmSchema.create(a.package, a.case, a.caption, a.entity, a.stage_column, stages, a.cultures.split(","))
    return DcmSchema(a.package, a.case)


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, open_schema)


if __name__ == "__main__":
    sys.exit(main())
