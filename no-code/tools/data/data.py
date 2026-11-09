#!/usr/bin/env python3
"""Data bindings stored in a package: rows of a table the package installs (library: ../creatio_schemas/data).

    python data.py inspect    <package> <Binding>
    python data.py validate   <package> <Binding>
    python data.py rows       <package> <Binding> [--limit 20] [--culture en-US]
    python data.py new        <package> <Binding> --table UsrOrderStatus [--key Id] [--columns Name,Description]
                              [--cultures en-US,ru-RU] [--rows rows.json]
    python data.py set        <package> <Binding> <key> <Column> <value> [--culture ru-RU]
    python data.py add-row    <package> <Binding> Column=value ...           (prints the new row's key)
    python data.py remove-row <package> <Binding> <key>

A row's key is the value of its key column (several key columns: joined by "|"). "null" is a null
value; a lookup takes the record's UId. A localised column (Name, Description of a lookup) lives in
Localization/data.<culture>.json: `set` needs --culture for it, `add-row Name=x` writes x to every
culture. `new` binds an object of the workspace (column UIds come from it); rows.json is a list of
{Column: value} objects. Writing commands accept --dry-run. `clio push-pkg` installs the rows.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.data import DataBinding  # noqa: E402


def validate(b, a):
    problems = b.validate()
    print("\n".join(problems) if problems else "ok")
    return 1 if b.errors() else 0


def rows(b, a):
    out = b.rows(a.culture)
    for r in out[:a.limit]:
        print(b.key_of(r) + "  " + "  ".join(f"{n}={json.dumps(v, ensure_ascii=False)}" for n, v in r.items() if n not in b.key_columns))
    if len(out) > a.limit:
        print(f"... {len(out) - a.limit} more")


def build() -> CommandLine:
    c = CommandLine(__doc__, "binding")
    c.command("inspect", lambda b, a: print(b.describe()), "bound table, row count, columns, problems")
    c.command("validate", validate, "problems; exit code 1 on errors")
    p = c.command("rows", rows, "the rows, one line each, key first")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--culture", help="localised columns in this culture only")
    p = c.command("new", lambda b, a: print(b.describe()), "a binding of an object of the workspace")
    p.add_argument("--table", required=True)
    p.add_argument("--key", default="Id", help="key columns, comma-separated")
    p.add_argument("--columns", default="", help="more columns, comma-separated (the rows add theirs)")
    p.add_argument("--cultures", default="en-US")
    p.add_argument("--rows", help="a JSON file: [{Column: value}, ...]")
    p = c.command("set", lambda b, a: b.set_value(a.key, a.column, a.value, a.culture), "one value of one row", writes=True)
    p.add_argument("key")
    p.add_argument("column")
    p.add_argument("value")
    p.add_argument("--culture")
    p = c.command("add-row", lambda b, a: print("add row", b.add_row(parse_assignments(a.values))), "a new row", writes=True)
    p.add_argument("values", nargs="+", metavar="Column=value")
    p = c.command("remove-row", lambda b, a: b.remove_row(a.key), "drop a row and its translations", writes=True)
    p.add_argument("key")
    return c


def open_binding(a):
    if a.command == "new":
        data = json.loads(Path(a.rows).read_text(encoding="utf-8-sig")) if a.rows else []
        return DataBinding.create(Path(a.package), a.binding, a.table, a.key.split(","), data, a.cultures.split(","),
                                  [n for n in a.columns.split(",") if n])
    return DataBinding(Path(a.package), a.binding)


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, open_binding)


if __name__ == "__main__":
    sys.exit(main())
