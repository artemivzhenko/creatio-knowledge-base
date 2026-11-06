"""
Checks for the object tools. Pure standard library:  python tests/test_objects_tools.py
(also collected by pytest). The fixtures are a Creatio 8.2.3 export of iaTest: iaOrder (made by
clio, then changed in the designer: virtual, rights, change log, column flags), the lookup
iaOrderStatus and iaTest.
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent))

from creatio_schemas import EntitySchema  # noqa: E402
from creatio_schemas.diff import SchemaDiff, path_of  # noqa: E402
from creatio_schemas.entity.hierarchy import merge_order  # noqa: E402

FIXTURES = HERE / "fixtures" / "iaTest"
SCHEMAS = ("iaOrder", "iaOrderStatus", "iaTest", "Account")


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def copy() -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURES, tmp / "iaTest")
    return tmp


def test_round_trip_is_byte_identical_and_reading_is_pure():
    for name in SCHEMAS:
        e = EntitySchema(FIXTURES, name)
        files = e.files()
        for path, (text, bom) in files.items():
            assert read(path) == ("﻿" if bom else "") + text, path
        e.describe()
        e.validate()
        assert e.files() == files and e.diff() == "", name


def test_diff_picks_the_operation_from_the_parent():
    parent = {"D1": True, "D2": [{"UId": "c1", "A2": "Id", "E6": True}]}
    d = SchemaDiff("= MetaData.Schema.A2 \"X\"")
    d.set(parent, path_of("D10"), True)                    # parent lacks it
    d.set(parent, path_of("D2", ("c1",), "E6"), False)     # parent has another value
    d.delete(parent, path_of("D1"))                        # parent has it
    d.set(parent, path_of("D2", ("c1",), "A2"), "Id")      # equal to the parent: no line
    assert [ln[0] + " " + ln[1] for ln in d.lines[1:]] == ["+ MetaData.Schema.D10", '= MetaData.Schema.D2.["c1"].E6', "- MetaData.Schema.D1"]
    eff = d.apply(parent)
    assert eff["D10"] is True and "D1" not in eff and eff["D2"][0]["E6"] is False and eff["A2"] == "X"


def test_inspect_decodes_the_designer_changes():
    e = EntitySchema(FIXTURES, "iaOrder")
    assert e.parent_name == "BaseEntity" and e.effective is not None
    assert e.flag("virtual") and e.flag("admin-records") and e.flag("deactivation")
    assert [c["A2"] for c in e.own_columns()] == ["iaName", "iaStatus", "iaAmount", "iaDueDate", "iaContact"]
    assert len(e.columns()) == 11
    text = e.describe()
    assert "iaContact                    Lookup -> Contact  [indexed, simple-lookup, weak-reference, cascade]" in text
    problems = e.validate()
    assert any("weak reference" in p for p in problems) and any("virtual" in p for p in problems)
    assert e.errors() == []  # properties.json agrees with the metadata
    assert EntitySchema(FIXTURES, "iaOrderStatus").column("Name")  # BaseLookup columns come with the parent


def test_edit_an_object():
    tmp = copy()
    try:
        pkg = tmp / "iaTest"
        e = EntitySchema(pkg, "iaOrder")
        e.set_flag("virtual", False)
        e.set_flag("db-view", False)
        col = e.add_column("iaManager", "Lookup", "Manager", ref="Contact")
        assert col["S4"] == "16be3651-8fe2-4159-8dd0-a803d4683dd3" and col["E17"] == "iaManagerId" and col["E6"] is True  # stock object by name
        e.add_column("iaQuantity", "Integer", "Quantity", default=1, required=True)
        e.set_column("iaContact", weak_reference=False)
        e.set_column("CreatedBy", indexed=False)  # inherited: a diff line against BaseEntity
        e.set_caption("iaQuantity", "Кількість", ["uk-UA"])
        e.save()

        e = EntitySchema(pkg, "iaOrder")
        meta = read(pkg / "Schemas" / "iaOrder" / "metadata.json")
        assert "- MetaData.Schema.D1" in meta and "+ MetaData.Schema.D10" not in meta
        assert '- MetaData.Schema.D2.["ebf6bb93-8aa6-4a01-900d-c6ea67affe21"].E6' in meta
        assert json.loads(read(pkg / "Schemas" / "iaOrder" / "properties.json").lstrip("﻿"))["Properties"]["IsVirtual"] == "False"
        assert not e.flag("virtual") and e.column("iaQuantity")["E2"] == 1 and e.column("iaQuantity")["E12"] == {"FB1": 1, "FB2": "1"}
        assert "E8" not in e.column("iaContact") and "E6" not in e.column("CreatedBy")
        order = e.delta.find("MetaData.Schema.D2", "~")[3]
        assert order[-2:] == [e.column("iaManager")["UId"], e.column("iaQuantity")["UId"]]
        assert e.resources.get("Columns.iaQuantity.Caption", "uk-UA") == "Кількість"
        assert e.errors() == [] and not any("virtual" in p for p in e.validate())

        e.remove_column("iaManager")
        assert "iaManager" not in [c["A2"] for c in e.columns()] and len(e.delta.find("MetaData.Schema.D2", "~")[3]) == 12
        assert not any("iaManager" in k for k in e.resources.cultures["en-US"])
        for bad in (lambda: e.remove_column("CreatedBy"), lambda: e.add_column("iaName", "ShortText"), lambda: e.add_column("iaX", "Float0")):
            try:
                bad()
                raise AssertionError("must be refused")
            except ValueError:
                pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_objects_from_the_designer_templates():
    tmp = copy()
    try:
        pkg = tmp / "iaTest"
        kind = EntitySchema.create(pkg, "iaShipmentType", "Shipment type", "BaseLookup")
        ship = EntitySchema.create(pkg, "iaShipment", "Shipment")
        ship.add_column("iaNumber", "ShortText", "Number", required=True)
        ship.add_column("iaType", "Lookup", "Type", ref="iaShipmentType")
        ship.set_display_column("iaNumber")
        ship.save()
        for name, n in (("iaShipmentType", 8), ("iaShipment", 8)):
            e = EntitySchema(pkg, name)
            meta = read(e.metadata_path)
            assert "{" + "uid}" not in meta and "Mbot" not in meta and "a1LogLevel" not in meta
            assert len(e.columns()) == n and not e.flag("virtual") and e.errors() == [], (name, e.validate())
            assert all(e.resources.get("Caption", c) for c in e.resources.cultures)  # every culture, or it shows "Base object"
        assert EntitySchema(pkg, "iaShipment").column("iaType")["S4"] == kind.uid
        assert '"Parent": {' in read(pkg / "Schemas" / "iaShipment" / "descriptor.json")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_replacing_object_reads_its_fetched_base():
    e = EntitySchema(FIXTURES, "Account")  # made in the designer: base columns changed
    assert e.replacing and e.base_info["chain"][-1] == "EmailMining" and e.delta.find("MetaData.Schema.D2", "+") is None
    e.effective
    assert e.delta.unresolved == []  # every line resolves against the merged base
    assert e.delta.value("MetaData.Schema.EG1.BK8") == e.parent["EG1"]["UId"]  # the platform's merge order
    assert e.column("EmployeesNumber")["E2"] == 1 and e.parent and "E2" not in next(c for c in e.parent["D2"] if c["A2"] == "EmployeesNumber")
    assert e.describe_column(e.column("GPSE")).split()[1] == "LongText"
    assert e.resources.get("Columns.AnnualRevenue.Caption") == "Annual revenue test"
    assert e.errors() == []
    rows = [{"pkg": p, "sl": sl, "pl": pl} for p, sl, pl in (("C", "0", "2"), ("R", "0", "2"), ("E", "0", "2"), ("S", "0", "5"), ("Base", "1", "22"))]
    assert [r["pkg"] for r in merge_order(rows)] == ["Base", "S", "C", "R", "E"]


def test_edit_base_columns_of_a_replacing_object():
    tmp = copy()
    try:
        pkg = tmp / "iaTest"
        shutil.copytree(FIXTURES.parent / ".creatio-bases", tmp / ".creatio-bases")
        e = EntitySchema(pkg, "Account")
        e.set_column("Phone", indexed=True)
        e.set_type("GPSN", "MediumText")
        e.set_default("Notes", "n/a")
        e.set_caption("Web", "Site", ["en-US"])
        e.add_column("iaRating", "Integer", "Rating")
        for bad in (lambda: e.set_type("GPSE", "ShortText"), lambda: e.set_type("EmployeesNumber", "LongText"), lambda: e.remove_column("Notes")):
            try:
                bad()
                raise AssertionError("must be refused")
            except ValueError:
                pass
        e.save()
        e = EntitySchema(pkg, "Account")
        meta = read(e.metadata_path)
        phone, code = e.column("Phone"), e.column("GPSN")
        assert f'.["{phone["UId"]}"].E6 true' in meta and phone["E6"] is True
        assert f'= MetaData.Schema.D2.["{code["UId"]}"].S2 "ddb3a1ee-07e8-4d62-b7a9-d0e618b00fbd"' in meta  # MediumText
        assert e.column("Notes")["E12"] == {"FB1": 1, "FB2": "n/a"} and e.resources.get("Columns.Web.Caption") == "Site"
        assert [c["A2"] for c in e.own_columns()] == ["iaRating"] and e.errors() == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_create_a_replacing_object_like_the_designer():
    tmp = copy()
    try:
        pkg = tmp / "iaTest"
        designer = read(pkg / "Schemas" / "Account" / "metadata.json").lstrip("﻿")
        designer_props = read(pkg / "Schemas" / "Account" / "properties.json")
        shutil.rmtree(pkg / "Schemas" / "Account")
        shutil.rmtree(pkg / "Resources" / "Account.Entity")
        try:
            EntitySchema.create_replacing(pkg, "Account")
            raise AssertionError("must need the fetched base")
        except ValueError as e:
            assert "objects.py base" in str(e)
        shutil.copytree(FIXTURES.parent / ".creatio-bases", tmp / ".creatio-bases")
        e = EntitySchema.create_replacing(pkg, "Account")
        head = r"^[=+\-~] MetaData\.Schema\.(UId|A5|B6|B7|B8|D8|D36\.\w+|EG1\.(UId|A2|A5|B8|BK8|BK15))( |$)"
        import re
        ours = [ln.split(" ")[0] + " " + ln.split(" ")[1] for ln in read(e.metadata_path).splitlines()]
        theirs = [ln.split(" ")[0] + " " + ln.split(" ")[1] for ln in designer.splitlines() if re.match(head, ln)]
        assert ours == theirs, (ours, theirs)
        assert read(pkg / "Schemas" / "Account" / "properties.json") == designer_props
        assert e.replacing and len(e.columns()) == 35 and e.errors() == [] and e.delta.unresolved == []
        assert e.delta.value("MetaData.Schema.EG1.BK8") == e.parent["EG1"]["UId"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_command_line():
    import objects
    tmp = copy()
    try:
        pkg = tmp / "iaTest"
        meta = pkg / "Schemas" / "iaOrder" / "metadata.json"
        before = read(meta)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert objects.main(["column", str(pkg), "iaOrder", "add", "iaNotes", "--type", "MediumText", "--dry-run"]) == 0
        assert '"A2": "iaNotes"' in out.getvalue() and read(meta) == before
        with contextlib.redirect_stdout(io.StringIO()):
            assert objects.main(["set", str(pkg), "iaOrder", "--off", "virtual", "db-view"]) == 0
            assert objects.main(["column", str(pkg), "iaOrder", "add", "iaNotes", "--type", "MediumText", "--caption", "Notes"]) == 0
            assert objects.main(["caption", str(pkg), "iaOrder", "*=Order"]) == 0
        with contextlib.redirect_stderr(io.StringIO()):
            assert objects.main(["column", str(pkg), "iaOrder", "remove", "Id"]) == 2
        e = EntitySchema(pkg, "iaOrder")
        assert e.column("iaNotes") and not e.flag("virtual") and all(e.resources.get("Caption", c) == "Order" for c in e.resources.cultures)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
