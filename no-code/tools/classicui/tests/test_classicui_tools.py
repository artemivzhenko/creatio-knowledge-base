"""Checks for the Classic UI tools:  python tests/test_classicui_tools.py  (the fixture follows the shapes of the platform's pages)."""

import contextlib
import io
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))

from classicui import main  # noqa: E402
from creatio_schemas.classicui import ClassicSchema  # noqa: E402
from creatio_schemas.files import CRLF, write_text  # noqa: E402
from creatio_schemas.text import mask  # noqa: E402

FIXTURES = HERE / "fixtures" / "UsrPkg"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_round_trip_is_byte_identical():
    for name in ("UsrOrderPage", "UsrOrderSection"):
        s = ClassicSchema(FIXTURES, name)
        for path, (text, bom) in s.files().items():
            assert read(path) == ("﻿" if bom else "") + text, path
        s.describe()
        assert s.diff() == "", name


def test_header_and_sections():
    page = ClassicSchema(FIXTURES, "UsrOrderPage")
    assert page.summary() == "edit page of UsrOrder, 14 diff operations, 9 methods, 3 details"
    assert page.kind == "edit page" and page.parent == "BasePageV2" and page.module_name == "UsrOrderPage"
    assert page.dependencies == ["BusinessRuleModule", "ConfigurationConstants", "UsrOrderPageResources"]
    assert list(page.sections) == ["entitySchemaName", "messages", "mixins", "attributes", "details", "modules", "businessRules", "methods",
                                   "diff", "rules"]
    assert page.messages() == {"UsrOrderTotalChanged": {"mode": "Terrasoft.MessageMode.BROADCAST", "direction": "Terrasoft.MessageDirectionType.PUBLISH"}}
    assert page.mixins() == {"UsrPrintMixin": "Terrasoft.UsrPrintMixin"}
    assert page.attributes()["UsrTotal"] == {"dataValueType": "Terrasoft.DataValueType.FLOAT", "dependencies": "[...]"}
    assert page.details()["Files"] == {"schemaName": "FileDetailV2", "entitySchemaName": "UsrOrderFile", "filter": "{...}"}
    assert page.entries("modules") == {} and page.entries("nope") == {}
    text = page.describe()
    assert "sections: entitySchemaName, messages 1, mixins 1, attributes 2, details 3, modules 0, businessRules 0, methods 9, diff 14, rules 1" in text
    assert "merge ESNTab; move UsrStatus; remove NotesAndFilesTab" in text
    section = ClassicSchema(FIXTURES, "UsrOrderSection")
    assert section.summary() == "section of UsrOrder, 2 diff operations, 3 methods, 0 details" and section.kind == "section"


def test_diff_operations_and_elements():
    ops = ClassicSchema(FIXTURES, "UsrOrderPage").diff_operations()
    assert [op["operation"] for op in ops].count("insert") == 11
    amount = next(op for op in ops if op["name"] == "UsrAmount")  # the name only in values
    assert amount["parentName"] == "UsrInfoContainer" and amount["index"] is None and amount["values"] == ["name", "bindTo", "layout"]
    first = ops[0]
    assert first["name"] == "UsrNumber" and first["index"] == "0" and first["propertyName"] == "items" and first["line"] == 134
    assert next(op for op in ops if op["name"] == "UsrPrintButton")["handlers"] == {"click": "onPrintClick"}
    remove = ops[-1]
    assert remove == dict(remove, operation="remove", name="NotesAndFilesTab", parentName=None, values=[])
    status = ClassicSchema(FIXTURES, "UsrOrderPage").element("UsrStatus")
    assert [op["operation"] for op in status] == ["insert", "move"] and '"parentName": "Header"' in status[1]["source"]
    try:
        ClassicSchema(FIXTURES, "UsrOrderPage").element("Nope")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown element must raise")


def test_methods_survive_braces_in_strings_comments_and_regexes():
    page = ClassicSchema(FIXTURES, "UsrOrderPage")
    names = [m["name"] for m in page.methods()]
    assert names == ["onEntityInitialized", "recalculateTotal", "isNumberValid", "setValidationConfig", "validateNumber", "onPrintClick",
                     "isPrintVisible", "getStatusCaption", "onUsrDiscountChange"]
    assert page.method("isNumberValid").endswith('return /^ORD-\\d{4}["\']?$/.test(value || "");\r\n\t\t\t\t}')
    assert page.method("recalculateTotal").count("\n") == 5 and page.method("onUsrDiscountChange") == "onUsrDiscountChange: Terrasoft.emptyFn"
    assert page.methods()[0] == {"name": "onEntityInitialized", "line": 66, "size": 6}
    try:
        page.method("nope")
    except KeyError as e:
        assert "onPrintClick" in str(e)
    else:
        raise AssertionError("an unknown method must raise")
    found = page.find("usrtotal")
    assert (80, "methods.recalculateTotal", 'this.set("UsrTotal", amount - discount);') in found and found[0][1] == "attributes"
    # the mask: a regex literal is blanked, a division is not
    assert mask('a = /[{"]/g; b = c / 2;') == 'a = /    /g; b = c / 2;'
    assert mask("x = `a{${b}`;\n// }") == "x = `      `;\n    "


def test_validate_warns_and_reads_workspace_parents():
    problems = ClassicSchema(FIXTURES, "UsrOrderPage").validate()
    assert problems == ["warning: parentName not declared here or in the workspace parents (expected from BasePageV2): "
                        "Header, LeftContainer, ProfileContainer, Tabs",
                        "warning: handlers bound to methods not defined here or in the workspace parents (expected from BasePageV2): "
                        "click -> onCloseClick"]
    assert ClassicSchema(FIXTURES, "UsrOrderPage").errors() == []
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    try:
        child = tmp / "UsrPkg" / "Schemas" / "UsrOrderMiniPage"
        shutil.copytree(tmp / "UsrPkg" / "Schemas" / "UsrOrderSection", child)
        write_text(child / "descriptor.json", read(child / "descriptor.json").replace("UsrOrderSection", "UsrOrderMiniPage")
                   .replace("BaseSectionV2", "UsrOrderPage"), False)
        (child / "UsrOrderSection.js").unlink()
        write_text(child / "UsrOrderMiniPage.js", CRLF.join([
            'define("UsrOrderMiniPage", [], function() {', "\treturn {", "\t\tdiff: [",
            '\t\t\t{"operation": "insert", "parentName": "UsrInfoContainer", "propertyName": "items", "values": {"name": "UsrNote"}},',
            '\t\t\t{"operation": "merge", "name": "UsrPrintButton", "values": {"click": {"bindTo": "onPrintClick"}}},',
            '\t\t\t{"operation": "remove", "values": {}}', "\t\t]", "\t};", "});", ""]), False)
        mini = ClassicSchema(tmp / "UsrPkg", "UsrOrderMiniPage")
        # properties.json (copied from the section) decides the kind before the parent's name does
        assert mini.kind == "section" and mini.validate() == ["warning: diff item at line 6: remove without a name"]
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_bodies_without_a_literal_object():
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    try:
        js = tmp / "UsrPkg" / "Schemas" / "UsrOrderSection" / "UsrOrderSection.js"
        write_text(js, '{"Settings": {"a": 1}}', False)  # a mobile settings file: JSON, no define
        s = ClassicSchema(tmp / "UsrPkg", "UsrOrderSection")
        assert s.summary() == "no define() module (1 lines)" and s.sections == {} and s.methods() == [] and s.diff_operations() == []
        assert not ClassicSchema.is_classic(tmp / "UsrPkg", "UsrOrderSection") and ClassicSchema.is_classic(FIXTURES, "UsrOrderPage")
        write_text(js, 'define("UsrOrderSection", ["Base"], function(Base) {\r\n\treturn Ext.apply(Base, {});\r\n});', False)
        s = ClassicSchema(tmp / "UsrPkg", "UsrOrderSection")
        assert s.module_name == "UsrOrderSection" and s.dependencies == ["Base"] and s.sections == {}
        assert s.summary() == "section, 0 diff operations, 0 methods, 0 details"
        s.schema_type = None  # no properties.json: the parent's name decides
        assert s.kind == "section"
        s.descriptor.set("Parent", {"UId": "d3cc497c-f286-4f13-99c1-751c468733c0", "Name": "BaseModule"})
        assert s.kind == "client schema"
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(FIXTURES), "UsrOrderPage"]) == 0
        assert main(["validate", str(FIXTURES), "UsrOrderSection"]) == 0
        assert main(["methods", str(FIXTURES), "UsrOrderSection"]) == 0
        assert main(["method", str(FIXTURES), "UsrOrderSection", "onTotalChanged"]) == 0
        assert main(["diff", str(FIXTURES), "UsrOrderPage", "--op", "insert", "--parent", "UsrInfoContainer"]) == 0
        assert main(["method", str(FIXTURES), "UsrOrderSection", "nope"]) == 2
    text = out.getvalue()
    assert "edit page of UsrOrder" in text and "onRecalculateClick" in text and "this.reloadGridData();" in text
    assert "insert  UsrAmount in UsrInfoContainer.items  line" in text and "insert  UsrTotal in UsrInfoContainer.items[2]" in text
    assert "UsrNumber" not in text.split("UsrInfoContainer.items")[-1]


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
