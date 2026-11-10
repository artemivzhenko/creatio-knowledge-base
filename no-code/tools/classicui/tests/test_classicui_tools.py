"""Checks for the Classic UI tools:  python tests/test_classicui_tools.py  (the fixture follows the shapes of the platform's pages)."""

import contextlib
import difflib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))

from classicui import main  # noqa: E402
from creatio_schemas.classicui import ClassicSchema  # noqa: E402
from creatio_schemas.diff import SchemaDiff  # noqa: E402
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


@contextlib.contextmanager
def workspace():
    """A temp packages folder with a copy of the fixture (UsrPkg) and an empty second package (UsrPkg2)."""
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    (tmp / "UsrPkg2").mkdir()
    desc = read(FIXTURES / "descriptor.json").lstrip("﻿")
    uid = json.loads(desc)["Descriptor"]["UId"]
    write_text(tmp / "UsrPkg2" / "descriptor.json", desc.replace(uid, "c0ffee00-0000-4000-8000-000000000002").replace('"UsrPkg"', '"UsrPkg2"'), True)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def on_disk(s) -> bool:
    return all(read(path) == ("﻿" if bom else "") + text for path, (text, bom) in s.files().items())


def refused(fn, kind, text=""):
    try:
        fn()
    except kind as e:
        assert text in str(e), (text, str(e))
        return
    raise AssertionError(f"expected {kind.__name__}")


RULE = "6e0f3b9a-1c2d-4e5f-8a9b-0c1d2e3f4a5b"


def test_body_writers_splice_only_their_span():
    with workspace() as ws:
        s = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        before, ops, methods = s.body, s.diff_operations(), [m["name"] for m in s.methods()]
        s.set_rule(RULE, enabled=False, column="UsrStatus")
        s.set_rule(RULE, removed=True)  # the second call edits the override in place
        s.add_mixin("UsrXMixin")
        s.add_mixin("UsrXMixin", "Terrasoft.UsrXMixinV2")  # existing: value replaced, dependency not doubled
        s.add_method("usrHello", "usrHello: function() {\n\treturn 1;\n}")
        s.replace_method("onUsrDiscountChange", "function() {\n\tthis.recalculateTotal();\n}")
        s.set_message("UsrPing", "ptp", "publish")
        s.set_message("UsrOrderTotalChanged", "broadcast", "bidirectional")
        s.save()
        s = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        assert on_disk(s) and "\n" not in s.body.replace("\r\n", "")  # the body's CRLF everywhere
        assert s.mixins() == {"UsrPrintMixin": "Terrasoft.UsrPrintMixin", "UsrXMixin": "Terrasoft.UsrXMixinV2"}
        assert s.dependencies.count("UsrXMixin") == 1
        assert [m["name"] for m in s.methods()] == methods + ["usrHello"] and "this.recalculateTotal();" in s.method("onUsrDiscountChange")
        assert s.messages()["UsrPing"] == {"mode": "Terrasoft.MessageMode.PTP", "direction": "Terrasoft.MessageDirectionType.PUBLISH"}
        assert s.messages()["UsrOrderTotalChanged"]["direction"] == "Terrasoft.MessageDirectionType.BIDIRECTIONAL"
        assert s.diff_operations()[0]["source"] == ops[0]["source"] and len(s.diff_operations()) == len(ops)
        assert s.entries("businessRules") == {"UsrStatus": {RULE: "{...}"}}
        assert '\t\t\t\t\t\t"enabled": false,\r\n\t\t\t\t\t\t"removed": true\r\n' in s.body
        removed = [ln for ln in difflib.ndiff(before.splitlines(), s.body.splitlines()) if ln.startswith("- ")]
        assert removed == ['- define("UsrOrderPage", ["BusinessRuleModule", "ConfigurationConstants", "UsrOrderPageResources"],',
                           '- \t\t\t\tUsrPrintMixin: "Terrasoft.UsrPrintMixin"',
                           "- \t\t\tbusinessRules: /**SCHEMA_BUSINESS_RULES*/{}/**SCHEMA_BUSINESS_RULES*/,",
                           "- \t\t\t\tonUsrDiscountChange: Terrasoft.emptyFn"], removed  # every other line is kept
        refused(lambda: s.add_method("usrHello", "function() {}"), KeyError, "replace_method")
        refused(lambda: s.replace_method("nope", "function() {}"), KeyError)
        refused(lambda: s.set_message("X", "loud", "publish"), ValueError)
        refused(lambda: s.set_rule(RULE), ValueError)
        refused(lambda: s.set_rule("00000000-0000-0000-0000-00000000000f", enabled=False), ValueError, "name its column")
        bare = ClassicSchema(ws / "UsrPkg", "UsrOrderSection")
        bare._deps_at = None
        refused(lambda: bare.add_dependency("UsrX"), ValueError, "dependency list")
        bare._return_at = None
        refused(lambda: bare._section("mixins"), ValueError, "returned object")


def item_uid(s, key):
    return next(i["UId"] for i in SchemaDiff(s.metadata_text).added_items("MetaData.Schema.B2") if i["A2"] == key)


def test_strings_go_to_the_diff_metadata_and_resources():
    with workspace() as ws:
        s = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        old = s.metadata_text
        s.add_string("UsrHello", {"en-US": "Hello"})
        s.add_string("UsrHello", {"en-US": "Hello again"})  # once in the metadata
        s.save()
        s = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        assert s.metadata_text.startswith(old + "\r\n+ MetaData.Schema.B2 {") and s.metadata_text.count("UsrHello") == 1
        item = json.loads(s.metadata_text.split("+ MetaData.Schema.B2 ", 1)[1])
        assert item["A3"] == item["A4"] == s.descriptor.data["UId"] and item["A5"] == "7f0d5a7e-2d0c-4c1e-9a7e-5b1c3f2a9d01"
        assert s.resources.get("LocalizableStrings.UsrHello.Value") == "Hello again" and on_disk(s)
        # the shape of real replacing schemas: own items, parent strings rebound, the order; a new item goes before ~
        meta = CRLF.join(['= MetaData.Schema.UId "11111111-0000-0000-0000-000000000001"', '= MetaData.Schema.A5 "a5a5a5a5-0000-0000-0000-000000000001"',
                          '+ MetaData.Schema.B2 {\r\n  "UId": "22222222-0000-0000-0000-000000000001",\r\n  "A2": "UsrOld"\r\n}',
                          '= MetaData.Schema.B2.["33333333-0000-0000-0000-000000000001"].A4 "11111111-0000-0000-0000-000000000001"',
                          '~ MetaData.Schema.B2 [\r\n  "33333333-0000-0000-0000-000000000001",\r\n  "22222222-0000-0000-0000-000000000001"\r\n]',
                          '= MetaData.Schema.B6 "b6b6b6b6-0000-0000-0000-000000000001"', "+ MetaData.Schema.B7 true"])
        s.metadata_text = meta
        s.add_string("UsrNew", {"en-US": "New"})
        head, tail = s.metadata_text.split("~ MetaData.Schema.B2")
        assert head.startswith(meta.split("~ MetaData.Schema.B2")[0]) and '"A2": "UsrNew"' in head
        assert tail.endswith('= MetaData.Schema.B6 "b6b6b6b6-0000-0000-0000-000000000001"\r\n+ MetaData.Schema.B7 true')
        assert item_uid(s, "UsrNew") in tail and json.loads(head.split("+ MetaData.Schema.B2 ")[-1])["A5"] == "a5a5a5a5-0000-0000-0000-000000000001"
        full = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        full.metadata_text = '{"MetaData": {}}'
        refused(lambda: full.add_string("UsrX", {"en-US": "x"}), ValueError, "diff form")
        refused(lambda: s.add_string("bad key", {"en-US": "x"}), ValueError)
        refused(lambda: s.add_string("UsrY", {}), ValueError)


def test_create_replacing_and_inherited_rule():
    with workspace() as ws:
        page = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        page.set_rule(RULE, enabled=True, column="UsrStatus")
        page.save()
        r = ClassicSchema.create_replacing(ws / "UsrPkg2", "UsrOrderPage", ["en-US", "ru-RU"])
        assert r.replacing and r.parent == "UsrOrderPage" and r.descriptor.data["Parent"]["UId"] == page.descriptor.data["UId"]
        meta = r.metadata_text.split("\r\n")
        assert [ln.split(" ")[1] for ln in meta] == ["MetaData.Schema." + k for k in ("UId", "A5", "B6", "B8", "B7", "HD1")]
        assert '"c0ffee00-0000-4000-8000-000000000002"' in meta[2] and not r.metadata_text.endswith("\n")
        assert r.body.startswith('define("UsrOrderPage", [], function() {\n\treturn {\n\t\tattributes: {},')
        assert r.sections.keys() >= {"businessRules", "diff", "methods", "mixins", "messages"}
        assert r.resources.get("Caption") == "Order edit page" and set(r.resources.cultures) == {"en-US", "ru-RU"} and on_disk(r)
        assert read(r.descriptor.path).startswith("﻿") and '"ExtendParent": true' in r.descriptor.text
        r.set_rule(RULE, enabled=False)  # only the parent has it: copied whole from the workspace parent, then disabled
        r.save()
        r = ClassicSchema(ws / "UsrPkg2", "UsrOrderPage")
        assert r.entries("businessRules") == {"UsrStatus": {RULE: "{...}"}} and r.body.count('"enabled"') == 1 and '"enabled": false' in r.body
        assert '\t\t\t\t"' + RULE + '": {\n\t\t\t\t\t"uId"' in r.body  # the parent's lines re-indented to this body
        assert r.diff_against_parent().startswith("--- UsrPkg/UsrOrderPage.js\n+++ UsrPkg2/UsrOrderPage.js")
        c = ClassicSchema.create_replacing(ws / "UsrPkg2", "ContactPageV2", parent_uid="d3cc497c-0000-4000-8000-000000000009", entity="Contact")
        assert '\t\tentitySchemaName: "Contact",\n' in c.body and c.entity == "Contact" and c.resources.cultures.keys() == {"en-US", "ru-RU"}  # the package's cultures
        assert c.diff_against_parent() is None
        refused(lambda: ClassicSchema.create_replacing(ws / "UsrPkg2", "AccountPageV2"), ValueError, "SysSchema")
        refused(lambda: ClassicSchema.create_replacing(ws / "UsrPkg2", "ContactPageV2", parent_uid="x"), FileExistsError)
        refused(lambda: ClassicSchema.create_replacing(ws / "UsrPkg2", "bad name", parent_uid="x"), ValueError, "valid")


def test_adopt_rebinds_the_pulled_copy():
    with workspace() as ws:
        pulled = ws.parent / "pulled" / "Custom"
        shutil.copytree(FIXTURES, pulled)
        src = ClassicSchema(pulled, "UsrOrderSection")
        old_uid = src.descriptor.data["UId"]
        s = ClassicSchema.adopt(ws / "UsrPkg2", "UsrOrderSection", pulled)
        assert s.descriptor.data["UId"] != old_uid and old_uid not in s.metadata_text and s.descriptor.data["UId"] in s.metadata_text
        assert '= MetaData.Schema.A5 "c0ffee00-0000-4000-8000-000000000002"' in s.metadata_text  # UsrPkg2 has no schemas: its UId
        assert s.body == src.body and s.resources.cultures == src.resources.cultures
        s2 = ClassicSchema.adopt(ws / "UsrPkg2", "UsrOrderPage", pulled / "Schemas" / "UsrOrderPage")  # the schema folder itself
        assert s2.name == "UsrOrderPage" and s2.diff_against_parent() is None  # BasePageV2 is not in the workspace
        refused(lambda: ClassicSchema.adopt(ws / "UsrPkg2", "UsrOrderSection", pulled), FileExistsError)
        refused(lambda: ClassicSchema.adopt(ws / "UsrPkg2", "UsrNope", pulled), FileNotFoundError)
        obj = pulled / "Schemas" / "UsrObj"
        obj.mkdir()
        write_text(obj / "descriptor.json", '{"Descriptor": {"UId": "x", "Name": "UsrObj", "ManagerName": "EntitySchemaManager"}}', True)
        write_text(obj / "metadata.json", "{}", True)
        refused(lambda: ClassicSchema.adopt(ws / "UsrPkg2", "UsrObj", pulled), ValueError, "client schemas")


def test_create_module_and_mixin():
    with workspace() as ws:
        m = ClassicSchema.create_module(ws / "UsrPkg2", "UsrXMixin", mixin=True)
        assert m.kind == "module" and m.module_name == "UsrXMixin" and ClassicSchema.is_classic(ws / "UsrPkg2", "UsrXMixin") and on_disk(m)
        assert 'Ext.define("Terrasoft.configuration.mixins.UsrXMixin", {' in m.body and 'alternateClassName: "Terrasoft.UsrXMixin"' in m.body
        meta = json.loads(read(m.dir / "metadata.json").lstrip("﻿"))["MetaData"]["Schema"]
        assert meta["HD1"] == "50e3acc0-26fc-4237-a095-849a1d534bd3" and meta["HD4"] == 1 and meta["B6"] == "c0ffee00-0000-4000-8000-000000000002"
        assert read(m.dir / "UsrXMixin.less") == " " and m.resources.get("Caption") == "UsrXMixin"
        plain = ClassicSchema.create_module(ws / "UsrPkg2", "UsrHelpers", caption="Helpers")
        assert plain.body == 'define("UsrHelpers", [], function() {\n\treturn {};\n});\n' and plain.resources.get("Caption") == "Helpers"
        refused(lambda: ClassicSchema.create_module(ws / "UsrPkg2", "UsrOrderPage"), FileExistsError)


def test_writer_cli():
    with workspace() as ws:
        pkg = str(ws / "UsrPkg")
        method = ws.parent / "m.js"
        method.write_text("function() {\n\treturn 2;\n}", encoding="utf-8")
        body = ws / "UsrPkg" / "Schemas" / "UsrOrderPage" / "UsrOrderPage.js"
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            before = read(body)
            assert main(["add-mixin", pkg, "UsrOrderPage", "UsrXMixin", "--dry-run"]) == 0
            assert read(body) == before  # dry run
            assert main(["add-mixin", pkg, "UsrOrderPage", "UsrXMixin"]) == 0
            assert main(["add-string", pkg, "UsrOrderPage", "UsrHello", "en-US=Hello"]) == 0
            assert main(["add-string", pkg, "UsrOrderPage", "UsrHello", "Hello"]) == 2
            assert main(["set-rule", pkg, "UsrOrderPage", RULE, "--enabled", "false", "--column", "UsrStatus"]) == 0
            assert main(["set-rule", pkg, "UsrOrderPage", RULE, "--removed", "maybe"]) == 2
            assert main(["add-method", pkg, "UsrOrderPage", "usrTwo", "--file", str(method)]) == 0
            assert main(["add-method", pkg, "UsrOrderPage", "usrTwo", "--file", str(method), "--replace"]) == 0
            assert main(["set-message", pkg, "UsrOrderPage", "UsrPing", "--mode", "PTP", "--direction", "SUBSCRIBE"]) == 0
            assert main(["replace", str(ws / "UsrPkg2"), "UsrOrderPage", "--cultures", "en-US"]) == 0
            assert main(["replace", str(ws / "UsrPkg2"), "AccountPageV2"]) == 2
            assert main(["adopt", str(ws / "UsrPkg2"), "UsrOrderSection", "--from", str(FIXTURES)]) == 0
        text = out.getvalue()
        s = ClassicSchema(ws / "UsrPkg", "UsrOrderPage")
        assert "UsrXMixin" in s.mixins() and "usrTwo" in [m["name"] for m in s.methods()] and "UsrPing" in s.messages()
        assert "return 2;" in s.method("usrTwo") and s.resources.get("LocalizableStrings.UsrHello.Value") == "Hello"
        assert "created UsrOrderPage replacing UsrOrderPage" in text and "Schemas/UsrOrderPage/metadata.json" in text
        assert "adopted UsrOrderSection into UsrPkg2" in text and "(the body of BaseSectionV2 is not in the workspace" in text


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
