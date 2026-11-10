#!/usr/bin/env python3
"""Classic UI (7.x) client schemas stored in a package: read and write (library: ../creatio_schemas/classicui).

    python classicui.py inspect  <package> <Schema>
    python classicui.py validate <package> <Schema>
    python classicui.py methods  <package> <Schema>
    python classicui.py method   <package> <Schema> <name>
    python classicui.py diff     <package> <Schema> [--op insert] [--parent Header]

    python classicui.py replace     <package> <Schema> [--parent-uid U] [--entity Contact] [--caption ..] [--cultures en-US,ru-RU]
    python classicui.py adopt       <package> <Schema> --from <pulled package or schema folder>
    python classicui.py add-string  <package> <Schema> <Key> en-US="Text" [ru-RU="..."]          [--dry-run]
    python classicui.py set-rule    <package> <Schema> <RuleUId> [--enabled false] [--removed true] [--column Owner]
    python classicui.py add-mixin   <package> <Schema> <Name> [--class Terrasoft.<Name>] [--module <Name>]
    python classicui.py add-method  <package> <Schema> <name> --file method.js [--replace]
    python classicui.py set-message <package> <Schema> <Name> --mode PTP|BROADCAST --direction SUBSCRIBE|PUBLISH|BIDIRECTIONAL

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
from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.files import read_text  # noqa: E402

CREATE = {"replace", "adopt"}


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


def files_of(s) -> None:
    for path in sorted(s.files()):
        print(f"  {path.relative_to(s.package).as_posix()}")


def replace(_, a):
    s = ClassicSchema.create_replacing(Path(a.package), a.schema, a.cultures.split(",") if a.cultures else None, a.parent_uid,
                                       a.caption, a.entity or "", a.version)
    print(f"created {s.name} replacing {s.parent} ({s.descriptor.data['Parent']['UId']}):")
    files_of(s)


def adopt(_, a):
    s = ClassicSchema.adopt(Path(a.package), a.schema, Path(a.source))
    print(f"adopted {s.name} into {s.package.name} as {s.descriptor.data['UId']}:")
    files_of(s)
    diff = s.diff_against_parent()
    print(diff if diff else f"(the body of {s.parent} is not in the workspace: no diff against the parent)")


def add_string(s, a):
    values = parse_assignments(a.values) if all("=" in v for v in a.values) else None
    if not values:
        raise ValueError("expected culture=value, e.g. en-US=\"Print\"")
    s.add_string(a.key, values)


def flag(text: str | None) -> bool | None:
    if text is None:
        return None
    if text.lower() not in ("true", "false"):
        raise ValueError(f"expected true or false, got {text!r}")
    return text.lower() == "true"


def add_method(s, a):
    source = read_text(Path(a.file))[0]
    (s.replace_method if a.replace else s.add_method)(a.name, source)


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

    p = c.command("replace", replace, "a replacing schema of a client schema: descriptor, diff metadata, empty body, resources")
    p.add_argument("--parent-uid", help="the parent's UId when the workspace does not hold it")
    p.add_argument("--entity", help="entitySchemaName of the new body (default: the parent's)")
    p.add_argument("--caption")
    p.add_argument("--cultures", help="comma-separated; default the package's")
    p.add_argument("--version", default="8.2.3.1351")
    p = c.command("adopt", adopt, "move a client schema pulled from another package into this one (new UId, A5, B6)")
    p.add_argument("--from", dest="source", required=True, help="the pulled package folder or the schema folder")
    p = c.command("add-string", add_string, "a localizable string: B2 metadata + resources", writes=True)
    p.add_argument("key")
    p.add_argument("values", nargs="+", metavar="culture=value")
    p = c.command("set-rule", lambda s, a: s.set_rule(a.uid, flag(a.enabled), flag(a.removed), a.column),
                  "override a business rule by UId in businessRules (enabled / removed)", writes=True)
    p.add_argument("uid")
    p.add_argument("--enabled", metavar="true|false")
    p.add_argument("--removed", metavar="true|false")
    p.add_argument("--column", help="the rule's column when no workspace parent has the rule")
    p = c.command("add-mixin", lambda s, a: s.add_mixin(a.name, a.cls, a.module), "a mixin in mixins + its module in define()", writes=True)
    p.add_argument("name")
    p.add_argument("--class", dest="cls", help="default Terrasoft.<name>")
    p.add_argument("--module", help="the module schema to depend on; default <name>")
    p = c.command("add-method", add_method, "a method from a file (`function(...) {...}`); --replace for an existing one", writes=True)
    p.add_argument("name")
    p.add_argument("--file", required=True)
    p.add_argument("--replace", action="store_true")
    p = c.command("set-message", lambda s, a: s.set_message(a.name, a.mode, a.direction), "a message: mode and direction", writes=True)
    p.add_argument("name")
    p.add_argument("--mode", required=True)
    p.add_argument("--direction", required=True)
    return c


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv,
                       lambda a: None if a.command in CREATE else ClassicSchema(Path(a.package), a.schema))


if __name__ == "__main__":
    sys.exit(main())
