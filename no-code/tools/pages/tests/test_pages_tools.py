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


def test_handlers_survive_comments_with_apostrophes_and_braces():
    import re
    page = PageSchema(FIXTURES, "iaOrder_FormPage")
    snippet = """[
            {
                request: "crt.HandleViewModelInitRequest",
                handler: async (request, next) => {
                    // the user's id isn't known yet { and this brace is text
                    /* a block comment with an apostrophe ' and a } brace */
                    await next?.handle(request);
                }
            },
            {
                request: "usr.SecondRequest",
                handler: async (request, next) => next?.handle(request)
            }
        ]"""
    page.body = re.sub(r"/\*\*SCHEMA_HANDLERS\*/.*?/\*\*SCHEMA_HANDLERS\*/", lambda m: f"/**SCHEMA_HANDLERS*/{snippet}/**SCHEMA_HANDLERS*/", page.body, flags=re.S)
    assert [name for name, _ in page.handlers()] == ["crt.HandleViewModelInitRequest", "usr.SecondRequest"]


def test_create_writes_what_clio_create_page_writes():
    import re
    pkg = copy()
    try:
        orig = PageSchema(pkg, "iaOrder_FormPage")  # an empty form page made by clio from PageWithTabsFreedomTemplate
        new = PageSchema.create(pkg, "iaOrderCopy_FormPage", "iaOrder", "form", "Order form page")
        swap = lambda t: t.replace(orig.descriptor.data["UId"], new.descriptor.data["UId"]).replace("iaOrder_FormPage", "iaOrderCopy_FormPage")  # noqa: E731
        for a, b in (("iaOrder_FormPage.js", "iaOrderCopy_FormPage.js"), ("metadata.json", "metadata.json"), ("properties.json", "properties.json")):
            assert swap(read(pkg / "Schemas" / "iaOrder_FormPage" / a)) == read(pkg / "Schemas" / "iaOrderCopy_FormPage" / b), a
        undate = lambda t: re.sub(r"Date\(\d+\)", "Date(0)", t)  # noqa: E731
        assert undate(swap(orig.descriptor.text)) == undate(new.descriptor.text)
        for f in (pkg / "Resources" / "iaOrder_FormPage.ClientUnit").glob("*.xml"):  # the caption in each of the package's 28 cultures
            assert read(f) == read(pkg / "Resources" / "iaOrderCopy_FormPage.ClientUnit" / f.name), f.name
        listing = PageSchema.create(pkg, "iaOrder_ListPage", "iaOrder", "list", "Orders", ["en-US"])
        assert listing.entity == "iaOrder" and listing.descriptor.data["Parent"]["Name"] == "ListPageV2Template" and listing.validate() == []
        assert listing.diff() == "" and list(listing.resources.cultures) == ["en-US"]
        for args, error in ((("iaOrder_ListPage", "iaOrder", "list"), FileExistsError), (("iaX_Page", "iaOrder", "card"), ValueError),
                            (("ia X", "iaOrder", "form"), ValueError)):
            try:
                PageSchema.create(pkg, *args)
            except error:
                pass
            else:
                raise AssertionError(f"create{args} must raise {error.__name__}")
    finally:
        shutil.rmtree(pkg.parent, ignore_errors=True)


EXPECTED = HERE / "fixtures" / "expected"  # what the UI test utility's analyse wrote for the two pages after their push


def test_page_file_from_schema_equals_what_analyse_wrote():
    from creatio_schemas.page import compare_page_files
    data, notes = PageSchema(FIXTURES, "iaTests_FormPage").page_file()
    assert json.dumps(data, indent=2, ensure_ascii=False) + "\n" == read(EXPECTED / "iaTestsForm.json")  # byte for byte
    assert notes == ["not written (crt.Feed): Feed", "not written (crt.FileList): AttachmentList"]
    # the order page was analysed after the 17 fields and the grid were put on it with these tools
    pkg = copy()
    try:
        page = PageSchema(pkg, "iaOrder_FormPage")
        expected = json.loads(read(EXPECTED / "iaOrderForm.json"))
        assert all(line.startswith("only in the file: ") for line in compare_page_files(expected, page.page_file()[0]))
        for e in expected["elements"]:
            if e["code"] in page.workspace.columns("iaOrder"):
                page.add_field(e["code"])
        page.add_grid("iaOrdersGrid", "iaOrder", ["iaName", "iaQuantity", "iaAmount"])
        assert compare_page_files(expected, page.page_file()[0]) == []
    finally:
        shutil.rmtree(pkg.parent, ignore_errors=True)


def test_page_file_labels_types_and_template_elements():
    page = PageSchema(FIXTURES, "iaTests_FormPage")
    ops = page.view_config_diff
    by_name = {op.get("name"): op for op in ops}
    page.resources.set("LocalizableStrings.iaName_caption.Value", "Order name", ["en-US"])
    by_name["iaName"]["values"]["label"] = "#ResourceString(iaName_caption)#"       # a page string
    by_name["iaComment"]["values"]["label"] = "Plain text"                           # a literal
    by_name["iaNumber"]["values"]["label"] = "$Resources.Strings.PDS_Nope_x1"         # nothing to resolve
    by_name["iaDateTime"]["values"].pop("pickerType")                                # no picker type: the column's type
    by_name["iaAccount"]["values"]["visible"] = False                                 # hidden by the page itself
    ops.append({"operation": "merge", "name": "GeneralInfoTab", "values": {"caption": "Main"}})
    ops.append({"operation": "remove", "name": "BackButton"})
    data, notes = page.page_file("Custom")
    got = {e["code"]: e for e in data["elements"]}
    assert data["name"] == "Custom" and got["iaName"]["label"] == "Order name" and got["iaComment"]["label"] == "Plain text"
    assert got["iaNumber"]["label"] == "" and any("label unknown" in n and "iaNumber" in n for n in notes)
    assert got["iaDateTime"]["type"] == "DateTime" and "iaAccount" not in got and any("hidden" in n and "iaAccount" in n for n in notes)
    assert got["GeneralInfoTab"]["label"] == "Main" and "BackButton" not in got
    assert got["iaNumber"]["type"] == "Integer" and got["iaAmount"]["type"] == "Decimal" and got["iaOrderList"]["columns"] == ["Name", "Quantity"]
    page.descriptor.set("Parent", {"UId": "00000000-0000-0000-0000-000000000001", "Name": "BaseMiniPageTemplate"})
    data, notes = page.page_file()
    assert "CloseButton" not in {e["code"] for e in data["elements"]} and any("BaseMiniPageTemplate" in n for n in notes)


def test_from_schema_command():
    import contextlib
    import io
    pkg = copy()
    try:
        out_file = pkg.parent / "iaTestsForm.json"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert main(["from-schema", str(pkg), "iaTests_FormPage", "--out", str(out_file)]) == 0
            assert main(["from-schema", str(pkg), "iaTests_FormPage", "--compare", str(EXPECTED / "iaTestsForm.json")]) == 0
            assert main(["from-schema", str(pkg), "iaOrder_FormPage", "--compare", str(EXPECTED / "iaOrderForm.json")]) == 1
            assert main(["from-schema", str(pkg), "iaTests_FormPage", "--name", "X"]) == 0
        text = out.getvalue()
        assert read(out_file) == read(EXPECTED / "iaTestsForm.json") and "wrote " in text and "# not written (crt.Feed): Feed" in text
        assert "no difference from" in text and "only in the file: iaAmount (Decimal)" in text and '"name": "X"' in text
    finally:
        shutil.rmtree(pkg.parent, ignore_errors=True)


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
