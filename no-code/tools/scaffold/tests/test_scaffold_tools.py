"""Checks for the scaffold:  python tests/test_scaffold_tools.py  (runs on temp copies of the pages fixture)."""

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE.parent))

from creatio_schemas.data import DataBinding  # noqa: E402
from creatio_schemas.describe import describe_package  # noqa: E402
from creatio_schemas.entity import EntitySchema  # noqa: E402
from creatio_schemas.page import PageSchema  # noqa: E402
from scaffold import caption_of, main, parse_column, parse_lookup  # noqa: E402

PAGES = TOOLS / "pages" / "tests" / "fixtures" / "iaTest"
SPEC = ["--caption", "Shipment", "--column", "UsrNumber:Integer:required", "--column", "UsrNotes:MediumText",
        "--column", "UsrContact:Lookup:Contact", "--lookup", "UsrStatus:UsrShipmentStatus:New,In progress,Done", "--pages", "--cultures", "en-US,ru-RU"]


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


@contextlib.contextmanager
def package():
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(PAGES, tmp / "iaTest")
    try:
        yield tmp / "iaTest"
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def run(*argv) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = main(list(argv))
    return code, out.getvalue()


def files(pkg: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in pkg.rglob("*") if p.is_file()}


def test_spec_grammar():
    assert parse_column("UsrNumber:Integer:required,indexed") == {"name": "UsrNumber", "type": "Integer", "ref": None, "flags": ["required", "indexed"]}
    assert parse_column("UsrContact:Lookup:Contact:required") == {"name": "UsrContact", "type": "Lookup", "ref": "Contact", "flags": ["required"]}
    assert parse_lookup("UsrStatus:UsrShipmentStatus:New, In progress ,Done")["rows"] == ["New", "In progress", "Done"]
    assert parse_lookup("UsrKind:UsrKindLookup") == {"column": "UsrKind", "object": "UsrKindLookup", "rows": []}
    assert [caption_of(n) for n in ("UsrShipDate", "UsrURLLink", "iaOrderStatus", "Name")] == ["Ship date", "URL link", "Order status", "Name"]
    for bad in ("UsrX", ":Integer", "UsrC:Lookup"):
        try:
            parse_column(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad!r} must be refused")
    try:
        parse_lookup("UsrStatus")
    except ValueError:
        pass
    else:
        raise AssertionError("a lookup spec without its object must be refused")


def test_dry_run_then_build_then_refuse():
    with package() as pkg:
        before = files(pkg)
        code, out = run("entity", str(pkg), "UsrShipment", *SPEC, "--dry-run")
        assert code == 0 and files(pkg) == before, out  # nothing written
        assert "+++ b/Schemas/UsrShipment/metadata.json" in out and "+++ b/Data/UsrShipmentStatus/data.json" in out and "(dry run: nothing written)" in out

        code, out = run("entity", str(pkg), "UsrShipment", *SPEC)
        assert code == 0 and "29 file(s) written to iaTest" in out, out
        listing = describe_package(pkg)
        for line in ("object    UsrShipment ", "object    UsrShipmentStatus ", "page      UsrShipment_FormPage ", "page      UsrShipment_ListPage "):
            assert line in listing, listing

        ent, status = EntitySchema(pkg, "UsrShipment"), EntitySchema(pkg, "UsrShipmentStatus")
        assert ent.column("UsrNumber")["E2"] == 1 and ent.column("UsrStatus")["S4"] == status.uid and status.parent_name == "BaseLookup"
        assert ent.resources.get("Columns.UsrNotes.Caption") == "Notes" and ent.resources.cultures.keys() == {"en-US", "ru-RU"}
        binding = DataBinding(pkg, "UsrShipmentStatus")
        assert [r["Name"] for r in binding.rows("en-US")] == ["New", "In progress", "Done"]
        form = PageSchema(pkg, "UsrShipment_FormPage")
        types = {e["code"]: e["type"] for e in form.page_file()[0]["elements"]}
        assert {k: types[k] for k in ("UsrNumber", "UsrNotes", "UsrContact", "UsrStatus")} == {
            "UsrNumber": "Integer", "UsrNotes": "Text", "UsrContact": "Lookup", "UsrStatus": "Lookup"}
        assert PageSchema(pkg, "UsrShipment_ListPage").entity == "UsrShipment"
        items = [ent, status, binding, form, PageSchema(pkg, "UsrShipment_ListPage")]
        for item in items:  # each passes its toolkit and round-trips byte for byte
            assert item.errors() == [], (item.name, item.errors())
            for path, (text, bom) in item.files().items():
                assert read(path) == ("﻿" if bom else "") + text, path

        written = files(pkg)
        code, out = run("entity", str(pkg), "UsrShipment", *SPEC)
        assert code == 2 and "exists" in out and files(pkg) == written  # never overwritten


def test_existing_lookup_is_reused_and_errors_write_nothing():
    with package() as pkg:
        code, out = run("entity", str(pkg), "UsrParcel", "--caption", "Parcel", "--lookup", "UsrState:iaOrderStatus")
        assert code == 0 and "lookup object" not in out and "data binding" not in out and "page " not in out, out
        assert EntitySchema(pkg, "UsrParcel").column("UsrState")["S4"] == EntitySchema(pkg, "iaOrderStatus").uid
        before = files(pkg)
        for argv in (("--column", "UsrX:NoSuchType"), ("--column", "UsrX:Integer:no-such-flag"), ("--column", "UsrX"),
                     ("--lookup", "UsrS:iaOrderStatus:A,B", "--column", "UsrX:Integer"), ("--pages", "--column", "UsrX:Lookup:NoSuchObject")):
            code, out = run("entity", str(pkg), "UsrBox", "--caption", "Box", *argv)
            if any("iaOrderStatus:A,B" in x for x in argv):  # a binding of an existing lookup is made when it has rows and no binding yet
                assert code == 0 and DataBinding(pkg, "iaOrderStatus").rows() and EntitySchema(pkg, "UsrBox")
                shutil.rmtree(pkg / "Schemas" / "UsrBox")
                shutil.rmtree(pkg / "Data" / "iaOrderStatus")
                shutil.rmtree(pkg / "Resources" / "UsrBox.Entity")
                continue
            assert code == 2 and files(pkg) == before, (argv, out)


def test_toolkit_refusal_stops_the_write():
    import scaffold
    original = EntitySchema.errors
    EntitySchema.errors = lambda self: ["a refusal"]
    try:
        with package() as pkg:
            before = files(pkg)
            code, out = run("entity", str(pkg), "UsrBox", "--caption", "Box")
            assert code == 2 and "the toolkits refuse the result" in out and files(pkg) == before
    finally:
        EntitySchema.errors = original
    assert scaffold.EntitySchema.errors is original


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
