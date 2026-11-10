#!/usr/bin/env python3
"""Freedom UI pages stored in a package (library: ../creatio_schemas/page).

    python pages.py inspect   <package> <Page>
    python pages.py add-field <package> <Page> <Column> [--parent SideAreaProfileContainer] [--row N] [--col N] [--span N]
    python pages.py add-grid  <package> <Page> <Name> --entity UsrOrder --columns UsrName,UsrAmount [--parent GeneralInfoTabContainer] [--rows 6] [--editable]
    python pages.py remove    <package> <Page> <Element>
    python pages.py validate  <package> <Page>
    python pages.py from-schema <package> <Page> [--name UsrOrderForm] [--out Configuration/pages/UsrOrderForm.json] [--compare <page file>]

The page body (<Page>.js) is edited through its JSON marker sections; a bound field gets the
control the designer would give the column's type and a PDS attribute, a grid gets its data
source and collection attribute. Field captions come from the column captions - no resource
strings are written. Every writing command accepts --dry-run. After `clio push-pkg` (clear
SysSchema.IsChanged first) the page renders the new controls; `analyse` of the UI test utility
shows what the browser got.

`from-schema` writes the UI test utility's page file (Configuration/pages/<name>.json) from the page
schema, without a browser: one element per control the utility has a type for, `code` = the element
name, the label as the page shows it, grids with their columns, the template's own buttons and tabs.
`--compare` prints what differs from an existing page file (exit code 1 when anything does).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creatio_schemas.cli import CommandLine  # noqa: E402
from creatio_schemas.files import write_text  # noqa: E402
from creatio_schemas.page import PageSchema, compare_page_files  # noqa: E402


def inspect(page, a):
    print(page.describe())


def validate(page, a):
    problems = page.validate()
    for p in problems:
        print(p)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if page.errors() else 0


def add_field(page, a):
    op = page.add_field(a.column, parent=a.parent, row=a.row, col=a.col, span=a.span)
    print(f"add {a.column}: {op['values']['type']} in {a.parent} row {op['values']['layoutConfig']['row']}")


def add_grid(page, a):
    op = page.add_grid(a.name, a.entity, a.columns.split(","), parent=a.parent, rows=a.rows, editable=a.editable)
    print(f"add {a.name}: grid of {a.entity} in {a.parent} row {op['values']['layoutConfig']['row']}")


def remove(page, a):
    page.remove(a.element)
    print(f"remove {a.element}")


def from_schema(page, a):
    data, notes = page.page_file(a.name)
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"  # the layout analyse writes: two spaces, LF, no BOM
    if a.out:
        write_text(Path(a.out), text, False)
        print(f"wrote {a.out}: {len(data['elements'])} element(s)")
    elif not a.compare:
        sys.stdout.write(text)
    for note in notes:
        print(f"# {note}")
    if a.compare:
        diff = compare_page_files(json.loads(Path(a.compare).read_text(encoding="utf-8-sig")), data)
        print("\n".join(diff) if diff else f"no difference from {a.compare}")
        return 1 if diff else 0
    return 0


def build() -> CommandLine:
    c = CommandLine(__doc__, "page")
    c.command("inspect", inspect, "elements, attributes, data sources and problems")
    c.command("validate", validate, "problems; exit code 1 on errors")
    p = c.command("add-field", add_field, "a field bound to a column of the page's object", writes=True)
    p.add_argument("column")
    p.add_argument("--parent", default="SideAreaProfileContainer")
    p.add_argument("--row", type=int)
    p.add_argument("--col", type=int, default=1)
    p.add_argument("--span", type=int, default=1)
    p = c.command("add-grid", add_grid, "a grid listing another object's records", writes=True)
    p.add_argument("name")
    p.add_argument("--entity", required=True)
    p.add_argument("--columns", required=True, help="comma-separated column names of the entity")
    p.add_argument("--parent", default="GeneralInfoTabContainer")
    p.add_argument("--rows", type=int, default=6, help="rowSpan in the parent grid container")
    p.add_argument("--editable", action="store_true")
    p = c.command("remove", remove, "drop an element with its attribute and data source", writes=True)
    p.add_argument("element")
    p = c.command("from-schema", from_schema, "the UI test utility's page file, from the page schema")
    p.add_argument("--name", help="the page name cases `open`; default <Object>Form for <Object>_FormPage")
    p.add_argument("--out", help="file to write (default: print)")
    p.add_argument("--compare", metavar="PAGE_FILE", help="print the differences from this page file")
    return c


def main(argv=None) -> int:
    return build().run(sys.argv[1:] if argv is None else argv, lambda a: PageSchema(Path(a.package), a.page))


if __name__ == "__main__":
    sys.exit(main())
