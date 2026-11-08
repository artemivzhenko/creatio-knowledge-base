#!/usr/bin/env python3
"""User tasks (reusable process elements with C# code) stored in a package (library: ../creatio_schemas/usertask).

    python usertask.py inspect      <package> <Task>
    python usertask.py validate     <package> <Task>
    python usertask.py method       <package> <Task> <Method>                      # one method's C#
    python usertask.py new          <package> <Task> --caption "Notify owner" [--param RecordId:Guid:In:required] [--param Note:Text] [--interactive] [--cultures en-US]
    python usertask.py add-param    <package> <Task> <Name> <Type> [--direction In|Out|Variable] [--caption C] [--required] [--ref UsrOrder]
    python usertask.py remove-param <package> <Task> <Name>
    python usertask.py rename-param <package> <Task> <Old> <New>
    python usertask.py set-caption  <package> <Task> <value>
    python usertask.py set-source   <package> <Task> <file.cs>                     # replace the C# half

A user task is a process element: its parameters (the same ProcessSchemaParameter a process has)
and a partial class whose InternalExecute runs when a process reaches it; the platform generates
the parameter properties. `new` writes a compilable skeleton. Types: Text, Integer, Float, Boolean,
DateTime, Date, Guid, Lookup, ... (the data value types of the process tools). Every writing
command accepts --dry-run. After `clio push-pkg` (clear SysSchema.IsChanged first) the element
appears in the process designer under "User actions"; a compile follows the push.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.cli import CommandLine  # noqa: E402
from creatio_schemas.files import read_text  # noqa: E402
from creatio_schemas.usertask import UserTaskSchema  # noqa: E402


def inspect(task, a):
    print(task.describe())


def validate(task, a):
    problems = task.validate()
    for p in problems:
        print(p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if task.errors() else 0


def method(task, a):
    print(task.method(a.method))


def new(task, a):
    print(task.describe())


def add_param(task, a):
    task.add_param(a.name, a.type, a.direction, a.caption or a.name, a.required, a.ref)
    print(f"add parameter {a.name} ({a.type}, {a.direction})")


def remove_param(task, a):
    task.remove_param(a.name)
    print(f"remove parameter {a.name}")


def rename_param(task, a):
    task.rename_param(a.old, a.new)
    print(f"rename parameter {a.old} -> {a.new}")


def set_caption(task, a):
    task.set_caption(a.value)
    print(f"caption {a.value!r}")


def set_source(task, a):
    task.set_source(read_text(Path(a.file))[0])
    print(f"source from {a.file}: {len(task.methods())} methods")


def parse_param(spec: str) -> tuple:
    """Name:Type[:Direction[:required]]."""
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError(f"--param expects Name:Type[:Direction[:required]], got {spec!r}")
    return (parts[0], parts[1], parts[2] if len(parts) > 2 and parts[2] else "In", "", len(parts) > 3 and parts[3].lower() == "required")


def build() -> CommandLine:
    c = CommandLine(__doc__, "task")
    c.command("inspect", inspect, "parameters, C# methods and problems")
    c.command("validate", validate, "problems; exit code 1 on errors")
    p = c.command("method", method, "one method's C# text")
    p.add_argument("method")
    p = c.command("new", new, "a user task with a C# skeleton")
    p.add_argument("--caption", required=True)
    p.add_argument("--param", action="append", default=[], metavar="NAME:TYPE[:DIRECTION[:required]]")
    p.add_argument("--interactive", action="store_true")
    p.add_argument("--cultures", default="en-US")
    p = c.command("add-param", add_param, "a parameter", writes=True)
    p.add_argument("name")
    p.add_argument("type")
    p.add_argument("--direction", default="In", choices=["In", "Out", "Variable", "Internal"])
    p.add_argument("--caption", default="")
    p.add_argument("--required", action="store_true")
    p.add_argument("--ref", help="referenced object of a Lookup parameter")
    p = c.command("remove-param", remove_param, "drop a parameter and its caption", writes=True)
    p.add_argument("name")
    p = c.command("rename-param", rename_param, "rename a parameter (captions follow)", writes=True)
    p.add_argument("old")
    p.add_argument("new")
    p = c.command("set-caption", set_caption, "the task caption", writes=True)
    p.add_argument("value")
    p = c.command("set-source", set_source, "replace the .cs file with the given file", writes=True)
    p.add_argument("file")
    return c


def open_schema(a):
    if a.command == "new":
        return UserTaskSchema.create(a.package, a.task, a.caption, [parse_param(s) for s in a.param], a.cultures.split(","), a.interactive)
    return UserTaskSchema(a.package, a.task)


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, open_schema)


if __name__ == "__main__":
    sys.exit(main())
