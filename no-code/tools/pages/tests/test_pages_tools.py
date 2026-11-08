"""
Checks for the page tools. Pure standard library:  python tests/test_pages_tools.py
(also collected by pytest). The fixtures are a Creatio 8.2.3 export of iaTest: iaTests_FormPage
(saved by the designer: viewModelConfig form) and iaOrder_FormPage (created by clio from a
template: viewModelConfigDiff form), with the objects they bind to.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))

from creatio_schemas.page import PageSchema  # noqa: E402
from pages import main  # noqa: E402

FIXTURES = HERE / "fixtures" / "iaTest"
PAGES = ("iaTests_FormPage", "iaOrder_FormPage")


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def copy() -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURES, tmp / "iaTest")
    return tmp / "iaTest"


def test_round_trip_is_byte_identical():
    for name in PAGES:
        page = PageSchema(FIXTURES, name)
        page.describe()
        page.validate()
        for path, (text, bom) in page.files().items():
            assert read(path) == ("﻿" if bom else "") + text, f"{name}: {path.name} re-rendered differently"
        assert page.diff() == ""


def test_add_field_in_both_body_forms():
    for name, column, parent in (("iaTests_FormPage", "iaNumber", "SideAreaProfileContainer"),
                                 ("iaOrder_FormPage", "iaShipDate", "SideAreaProfileContainer")):
        pkg = copy()
        page = PageSchema(pkg, name)
        if page.has(column):
            page.remove(column)
        op = page.add_field(column, parent=parent)
        page.save()
        again = PageSchema(pkg, name)
        el = again.element(column)
        assert el["values"]["control"] == f"${column}"
        assert again.attributes[column] == {"modelConfig": {"path": f"PDS.{column}"}}
        assert el["values"]["layoutConfig"]["row"] == op["values"]["layoutConfig"]["row"]
        assert again.diff() == "", "a second render must be stable"
        assert again.validate() == []
    pkg = copy()
    page = PageSchema(pkg, "iaOrder_FormPage")
    assert page.add_field("iaShipDate")["values"]["pickerType"] == "date"
    assert page.add_field("iaPickupTime")["values"]["pickerType"] == "time"
    assert page.add_field("iaEmail")["values"]["type"] == "crt.EmailInput"
    assert page.add_field("iaIsUrgent")["values"]["type"] == "crt.Checkbox"
    assert page.add_field("iaStatus")["values"]["type"] == "crt.ComboBox"
    rows = [page.element(c)["values"]["layoutConfig"]["row"] for c in ("iaShipDate", "iaPickupTime", "iaEmail")]
    assert rows == [1, 2, 3]
    body = page.render_body()
    assert '"iaShipDate": {' in body and "viewModelConfigDiff" in body
    ops = json.loads(body.split("/**SCHEMA_VIEW_MODEL_CONFIG_DIFF*/")[1])
    assert ops[0]["path"] == ["attributes"] and "iaEmail" in ops[0]["values"]


def test_add_grid_and_remove():
    pkg = copy()
    page = PageSchema(pkg, "iaTests_FormPage")
    # the fixture's grid was written by hand (S11-T01); the tool must reproduce it
    hand = json.loads(json.dumps(page.element("iaOrderList")))
    page.remove("iaOrderList")
    op = page.add_grid("iaOrderList", "iaOrder", ["iaName", "iaQuantity"])
    for item in (hand, op):
        for c in item["values"]["columns"]:
            c.pop("id")
    hand["values"]["columns"][1]["width"] = 200  # the only hand-picked difference
    assert op == hand
    assert op["values"]["columns"][0]["caption"] == "Name"
    assert page.data_sources["iaOrderListDS"]["config"]["entitySchemaName"] == "iaOrder"
    assert page.attributes["iaOrderList"]["isCollection"] is True
    page.save()
    again = PageSchema(pkg, "iaTests_FormPage")
    assert again.has("iaOrderList") and "iaOrderListDS" in again.data_sources
    again.remove("iaOrderList")
    assert not again.has("iaOrderList") and "iaOrderListDS" not in again.data_sources and "iaOrderList" not in again.attributes
    again.save()
    assert PageSchema(pkg, "iaTests_FormPage").diff() == ""


def test_unknown_column_and_duplicate_are_refused():
    page = PageSchema(copy(), "iaTests_FormPage")
    for args in (("iaNope",), ("iaName",)):
        try:
            page.add_field(*args)
        except KeyError as e:
            assert args[0] in str(e)
        else:
            raise AssertionError(f"add_field{args} should fail")


def test_cli_dry_run_writes_nothing():
    import contextlib
    import io
    pkg = copy()
    before = read(pkg / "Schemas" / "iaOrder_FormPage" / "iaOrder_FormPage.js")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(["add-field", str(pkg), "iaOrder_FormPage", "iaWeight", "--dry-run"])
    assert code == 0 and "crt.NumberInput" in out.getvalue() and "(dry run" in out.getvalue()
    assert read(pkg / "Schemas" / "iaOrder_FormPage" / "iaOrder_FormPage.js") == before
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(pkg), "iaTests_FormPage"]) == 0
    assert "page of iaTest" in out.getvalue()


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
