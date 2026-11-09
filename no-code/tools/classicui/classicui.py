#!/usr/bin/env python3
"""Classic UI (7.x) client schemas stored in a package, read-only (library: ../creatio_schemas/classicui).

    python classicui.py inspect  <package> <Schema>
    python classicui.py validate <package> <Schema>
    python classicui.py methods  <package> <Schema>
    python classicui.py method   <package> <Schema> <name>
    python classicui.py diff     <package> <Schema> [--op insert] [--parent Header]

An edit page, section or detail of the 7.x designer: `define("Name", [deps], function(...) { return {...} })`
with entitySchemaName, attributes, messages, mixins, details, diff (insert / merge / remove / move), methods,
rules. `inspect` gives the header, the sections with their sizes and the diff's elements; `validate` warns about
parentNames and handler methods this file cannot prove (they usually come from the platform's parent schema).
Freedom UI pages are read by ../pages.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.classicui import ClassicSchema  # noqa: E402
from creatio_schemas.cli import CommandLine  # noqa: E402


def validate(s, a):
    problems = s.validate()
    print("\n".join(problems) if problems else "ok")
    return 1 if s.errors() else 0


def methods(s, a):
    for m in s.methods():
        print(f"{m['name']:<40} line {m['line']:<6} {m['size']} lines")


def diff(s, a):
    for op in s.diff_operations():
        if (a.op and op["operation"] != a.op) or (a.parent and op["parentName"] != a.parent):
            continue
        where = f" in {op['parentName']}.{op['propertyName']}" if op["parentName"] else ""
        index = f"[{op['index']}]" if op["index"] is not None else ""
        print(f"{op['operation'] or '?':<7} {op['name'] or '(no name)'}{where}{index}  line {op['line']}  values: {', '.join(op['values']) or '-'}")


def build() -> CommandLine:
    c = CommandLine(__doc__, "schema")
    c.command("inspect", lambda s, a: print(s.describe()), "kind, object, parent, sections with sizes, diff elements, warnings")
    c.command("validate", validate, "warnings; exit code 0 (nothing here blocks)")
    c.command("methods", methods, "one line per method: name, line, size")
    p = c.command("method", lambda s, a: print(s.method(a.name)), "one method's source")
    p.add_argument("name")
    p = c.command("diff", diff, "one line per diff operation")
    p.add_argument("--op", choices=["insert", "merge", "remove", "move"])
    p.add_argument("--parent", help="only operations under this parentName")
    return c


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, lambda a: ClassicSchema(Path(a.package), a.schema))


if __name__ == "__main__":
    sys.exit(main())
