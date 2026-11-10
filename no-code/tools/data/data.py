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
    python data.py duplicates <Object> <Column> -e <env> | --project <project.json>
                              [--normalize trim,lower,digits] [--lookup] [--where "<OData filter>"] [--limit 40] [--json]

A row's key is the value of its key column (several key columns: joined by "|"). "null" is a null
value; a lookup takes the record's UId. A localised column (Name, Description of a lookup) lives in
Localization/data.<culture>.json: `set` needs --culture for it, `add-row Name=x` writes x to every
culture. `new` binds an object of the workspace (column UIds come from it); rows.json is a list of
{Column: value} objects. Writing commands accept --dry-run. `clio push-pkg` installs the rows.

`duplicates` reads the environment over OData (library: ../creatio_schemas/environment) and groups
the records by the normalised value of the column: one line per group of two or more
(`<value>  N records  ids: ...`), then the count of groups and of records in them; exit 1 when
there are any. `--normalize` is a comma list of trim (default), lower, digits (keeps 0-9 only, for
phones); `--lookup` groups the Name of the referenced record (`$expand`); `--where` narrows the
records. Nothing is written.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.cli import CommandLine, parse_assignments  # noqa: E402
from creatio_schemas.data import DataBinding  # noqa: E402
from creatio_schemas.environment import open_environment  # noqa: E402


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


PAGE = 500
NORMALIZERS = {"trim": str.strip, "lower": str.lower, "digits": lambda s: "".join(c for c in s if c.isdigit())}


def normalize(value, steps: list[str]) -> str:
    text = "" if value is None else str(value)
    for step in steps:
        text = NORMALIZERS[step](text)
    return text


def read_records(env, obj: str, column: str, lookup: bool, where: str | None) -> list[tuple[str, object]]:
    """(Id, value) of every record, paged; a lookup column yields the Name of the referenced record."""
    select, expand = (["Id", column + "Id"], f"{column}($select=Name)") if lookup else (["Id", column], None)
    out, skip = [], 0
    while True:
        page = env.odata(obj, select, where, PAGE, "Id", skip, expand)
        for r in page:
            out.append((r["Id"], (r.get(column) or {}).get("Name") if lookup else r.get(column)))
        if len(page) < PAGE:
            return out
        skip += PAGE


def group_duplicates(records, steps: list[str]) -> list[dict]:
    groups: dict[str, dict] = {}
    for id_, value in records:
        key = normalize(value, steps)
        groups.setdefault(key, {"value": value, "ids": []})["ids"].append(id_)
    out = [{"value": g["value"], "count": len(g["ids"]), "ids": g["ids"]} for g in groups.values() if len(g["ids"]) > 1]
    return sorted(out, key=lambda g: (-g["count"], str(g["value"])))


def duplicates(env, a):
    steps = [s for s in a.normalize.split(",") if s]
    unknown = [s for s in steps if s not in NORMALIZERS]
    if unknown:
        raise ValueError(f"unknown --normalize step(s) {', '.join(unknown)}; known: {', '.join(NORMALIZERS)}")
    groups = group_duplicates(read_records(env, a.object, a.column, a.lookup, a.where), steps)
    records = sum(g["count"] for g in groups)
    if a.json:
        print(json.dumps({"object": a.object, "column": a.column, "normalize": steps, "groups": groups,
                          "groups_count": len(groups), "records": records}, ensure_ascii=False, indent=2))
    else:
        for g in groups[:a.limit]:
            ids = ", ".join(g["ids"][:10]) + (f" +{len(g['ids']) - 10} more" if len(g["ids"]) > 10 else "")
            print(f"{json.dumps(g['value'], ensure_ascii=False)}  {g['count']} records  ids: {ids}")
        if len(groups) > a.limit:
            print(f"... {len(groups) - a.limit} more groups")
        print(f"{len(groups)} duplicate groups, {records} records in them ({a.object}.{a.column}, normalize: {','.join(steps) or 'none'})")
    return 1 if groups else 0


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
    p = c.command("duplicates", duplicates, "groups of records sharing a value on the environment; exit 1 when any", target=False)
    p.add_argument("object")
    p.add_argument("column")
    p.add_argument("-e", "--env", help="clio environment name")
    p.add_argument("--project", help="project.json with the environment")
    p.add_argument("--normalize", default="trim", help="comma list of trim, lower, digits (default: trim)")
    p.add_argument("--lookup", action="store_true", help="the column is a lookup: group the Name of the referenced record")
    p.add_argument("--where", help="an OData filter narrowing the records")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--json", action="store_true")
    return c


def open_binding(a):
    if a.command == "duplicates":
        return open_environment(a.env, a.project)
    if a.command == "new":
        data = json.loads(Path(a.rows).read_text(encoding="utf-8-sig")) if a.rows else []
        return DataBinding.create(Path(a.package), a.binding, a.table, a.key.split(","), data, a.cultures.split(","),
                                  [n for n in a.columns.split(",") if n])
    return DataBinding(Path(a.package), a.binding)


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, open_binding)


if __name__ == "__main__":
    sys.exit(main())
