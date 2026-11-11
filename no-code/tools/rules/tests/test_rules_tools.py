"""
Checks for the business-rule tools. Pure standard library:  python tests/test_rules_tools.py
(also collected by pytest). The fixtures are a Creatio 8.2.3 export of the UsrPkg package after
rules built by these tools were pushed and pulled back: an own entity addon, an own page addon
and a replacing addon of a base entity (ContactAddress, base rules in CrtBase).
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from creatio_schemas import RuleSchema  # noqa: E402
from creatio_schemas.rules.model import OPS, T_FILTER_LOOKUP, T_GROUP  # noqa: E402

FIXTURES = HERE / "fixtures" / "UsrPkg"
SCHEMAS = ("UsrPkgBusinessRule", "UsrTests_FormPageBusinessRule", "ContactAddressBusinessRule")


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def copy() -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    return tmp


def test_round_trip_is_byte_identical():
    for name in SCHEMAS:
        rs = RuleSchema(FIXTURES, name)
        files = rs.files()
        for path, (text, bom) in files.items():
            assert read(path) == ("﻿" if bom else "") + text, path
        rs.describe()
        assert rs.files() == files and rs.diff() == ""  # reading never changes the metadata


def test_inspect_decodes_all_three_forms():
    entity = RuleSchema(FIXTURES, "UsrPkgBusinessRule")
    assert entity.kind == "entity" and not entity.replacing and entity.target == "UsrPkg"
    text = entity.describe()
    assert "then filter UsrContactLookup by UsrContactLookup.Account = UsrAccount" in text
    assert "when UsrNumber empty or UsrAmount empty" in text
    assert "UsrContactLookup = sys:CurrentUserContact" in text
    page = RuleSchema(FIXTURES, "UsrTests_FormPageBusinessRule")
    assert page.kind == "page" and "then hide: UsrDate,UsrDateTime" in page.describe()
    repl = RuleSchema(FIXTURES, "ContactAddressBusinessRule")
    assert repl.replacing and repl.target == "ContactAddress"  # base target: named after the addon
    assert repl.base_edits() == ['+ MetaData.Schema.AD4.BRS1.["34a9fedf-e4d8-f6e1-cb04-2e74816d4502"].BR4 false']
    for name in SCHEMAS:
        assert [p for p in RuleSchema(FIXTURES, name).validate() if not p.startswith("warning:")] == [], name


def test_build_entity_rules_and_edit_them():
    tmp = copy()
    try:
        rs = RuleSchema(tmp / "UsrPkg", "UsrPkgBusinessRule")
        before = len(rs.rules)
        rule = rs.add({"caption": "Amount required for big numbers", "logic": "or",
                       "conditions": [{"left": "UsrNumber", "op": "equal", "value": 100}, {"left": "UsrIsActive", "op": "equal", "value": True}],
                       "actions": [{"type": "required", "items": ["UsrAmount"]}]})[0]
        cond = rule["BR1"][0]["BRC1"]
        assert cond["JI0"] == T_GROUP and cond["BGC1"] == 2
        assert cond["BGC2"][0]["BCO1"]["BRE1"] == "Integer" and cond["BGC2"][0]["BCO2"]["BVE1"] == 100  # types come from the entity
        assert [t.get("BRT1", t.get("BRT2")) for t in rule["BR2"]] == ["UsrNumber", "UsrIsActive", 2]
        kids = rs.add({"caption": "Filter", "actions": [{"type": "filter-lookup", "column": "UsrContactLookup", "by": "Account", "source": "UsrAccount",
                                                          "column_ref": "Contact", "source_ref": "Account", "populate": False}]})
        parent, clear, populate = kids
        assert parent["BR1"][0]["BRC2"][0]["JI0"] == T_FILTER_LOOKUP and "BRC1" not in parent["BR1"][0]
        assert clear["BR5"] == parent["UId"] and clear["BR6"] == parent["BR1"][0]["BRC2"][0]["UId"]
        assert clear["BR1"][0]["BRC1"]["BCO3"] == OPS["not-equal"] and populate["BR4"] is False
        assert rs.resources.get(f"AddonConfig.Rules.{clear['UId']}.Caption") == f"ChildRule-{parent['UId']}-ClearValue"
        rs.save()

        rs = RuleSchema(tmp / "UsrPkg", "UsrPkgBusinessRule")
        assert len(rs.rules) == before + 4 and rs.validate() == []
        position = [r["UId"] for r in rs.rules].index(parent["UId"])
        rs.replace(parent["BR3"], {"actions": [{"type": "filter-lookup", "column": "UsrContactLookup", "by": "Account", "source": "UsrAccount",
                                                  "column_ref": "Contact", "source_ref": "Account"}]})
        assert [r["UId"] for r in rs.rules].index(parent["UId"]) == position  # edited in place, same UId
        assert rs.caption(rs.rule(parent["UId"])) == "Filter"
        assert len([r for r in rs.rules if r.get("BR5") == parent["UId"]]) == 2
        removed = rs.remove(parent["BR3"])
        assert len(removed) == 3 and not any(k.startswith(f"AddonConfig.Rules.{u}") for u in removed for k in rs.resources.cultures["en-US"])
        rs.set_enabled(rule["BR3"], False)
        assert rs.rule(rule["UId"])["BR4"] is False
        rs.save()
        assert len(RuleSchema(tmp / "UsrPkg", "UsrPkgBusinessRule").rules) == before + 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_page_rules_map_paths_and_check_elements():
    tmp = copy()
    try:
        rs = RuleSchema(tmp / "UsrPkg", "UsrTests_FormPageBusinessRule")
        rule = rs.add({"conditions": [{"left": "PDS.UsrIsActive", "op": "equal", "value": True}],
                       "actions": [{"type": "show", "items": ["UsrDate"]}, {"type": "editable", "items": ["UsrName"]}]})[0]
        left = rule["BR1"][0]["BRC1"]["BGC2"][0]["BCO1"]
        assert left["BRX1"] == "UsrIsActive" and left["BRE1"] == "Boolean"  # PDS.Column resolves to the page attribute bound to it
        assert rs.caption(rule) == "Show elements: UsrDate"
        rs.add({"caption": "bad", "actions": [{"type": "hide", "items": ["NoSuchElement"]}]})
        assert any("NoSuchElement" in p and p.startswith("warning:") for p in rs.validate())
        try:
            rs.add({"caption": "x", "actions": [{"type": "set", "values": {"UsrName": "a"}}]})
            raise AssertionError("set values must be refused on a page")
        except ValueError:
            pass
        rs.add({"caption": "8.3 only", "conditions": [{"left": "UsrNumber", "op": "greater", "value": 5}], "actions": [{"type": "hide", "items": ["UsrDate"]}]})
        assert any("needs Creatio 8.3+" in p for p in rs.validate())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_replacing_and_new_addons():
    tmp = copy()
    try:
        pkg = tmp / "UsrPkg"
        rs = RuleSchema(pkg, "ContactAddressBusinessRule")
        new = rs.add({"caption": "Zip required", "conditions": [{"left": "Country", "op": "filled"}], "actions": [{"type": "required", "items": ["Zip"]}]})[0]
        rs.set_enabled("34a9fedf-e4d8-f6e1-cb04-2e74816d4502", True)  # re-enable the base rule: the override line goes away
        rs.remove_base("ac27cf9c-1a50-3db2-30b9-b6479422cc25")
        rs.save()
        text = read(pkg / "Schemas" / "ContactAddressBusinessRule" / "metadata.json")
        assert "BR4 false" not in text and '- MetaData.Schema.AD4.BRS1.["ac27cf9c-1a50-3db2-30b9-b6479422cc25"]' in text
        assert text.count("+ MetaData.Schema.AD4.BRS1 {") == 2 and not text.startswith("﻿")
        assert new["UId"] in [r["UId"] for r in RuleSchema(pkg, "ContactAddressBusinessRule").rules]

        own = RuleSchema.create(pkg, "Contact", target_uid="16be3651-8fe2-4159-8dd0-a803d4683dd3", kind="entity")
        own.add({"caption": "Notes read-only for the marker", "conditions": [{"left": "JobTitle", "op": "equal", "value": "x", "type": "ShortText"}],
                 "actions": [{"type": "readonly", "items": ["Notes"]}]})
        own.save()
        again = RuleSchema(pkg, "ContactBusinessRule")
        meta = json.loads(read(pkg / "Schemas" / "ContactBusinessRule" / "metadata.json").lstrip("﻿"))["MetaData"]["Schema"]
        assert meta["AD1"] == "16be3651-8fe2-4159-8dd0-a803d4683dd3" and meta["AD3"] == "BusinessRule" and len(again.rules) == 1
        assert '"ModifiedOnUtc": "\\/Date(' in read(pkg / "Schemas" / "ContactBusinessRule" / "descriptor.json")
        repl = RuleSchema.create(pkg, "Account", parent_uid="11111111-1111-1111-1111-111111111111", target_uid="25d7c1ab-1de0-4501-b402-02e0e5a72d6e", kind="entity")
        assert repl.replacing and repl.rules == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_command_line():
    import contextlib
    import io
    sys.path.insert(0, str(HERE.parent))
    import rules
    tmp = copy()
    try:
        pkg, spec = tmp / "UsrPkg", tmp / "rule.json"
        spec.write_text(json.dumps({"caption": "Comment required when active", "conditions": [{"left": "UsrIsActive", "op": "equal", "value": True}],
                                    "actions": [{"type": "required", "items": ["UsrComment"]}]}), encoding="utf-8")
        meta = pkg / "Schemas" / "UsrPkgBusinessRule" / "metadata.json"
        before = read(meta)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert rules.main(["add", str(pkg), "UsrPkg", "--spec", str(spec), "--dry-run"]) == 0
        assert "Comment required when active" in out.getvalue() and read(meta) == before
        with contextlib.redirect_stdout(io.StringIO()):
            assert rules.main(["add", str(pkg), "UsrPkgBusinessRule", "--spec", str(spec)]) == 0  # the addon name works too
            assert rules.main(["disable", str(pkg), "UsrPkg", "Comment required when active"]) == 0
        with contextlib.redirect_stderr(io.StringIO()):
            assert rules.main(["remove-base", str(pkg), "UsrPkg", "34a9fedf-e4d8-f6e1-cb04-2e74816d4502"]) == 2  # own addon: refused
        assert RuleSchema(pkg, "UsrPkgBusinessRule").rule("Comment required when active")["BR4"] is False
        # the first rule of a target creates its addon, as the designer does - except under --dry-run
        shutil.rmtree(pkg / "Schemas" / "UsrPkgBusinessRule")
        shutil.rmtree(pkg / "Resources" / "UsrPkgBusinessRule.Addon")
        with contextlib.redirect_stderr(io.StringIO()):
            assert rules.main(["add", str(pkg), "UsrPkg", "--spec", str(spec), "--dry-run"]) == 2
        assert not (pkg / "Schemas" / "UsrPkgBusinessRule").exists()
        with contextlib.redirect_stdout(io.StringIO()):
            assert rules.main(["add", str(pkg), "UsrPkg", "--spec", str(spec)]) == 0
        assert RuleSchema(pkg, "UsrPkgBusinessRule").rule("Comment required when active").get("BR4", True) is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
