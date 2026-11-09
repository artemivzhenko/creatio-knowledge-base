"""Checks for the data binding tools:  python tests/test_data_tools.py  (the fixture bindings are real ones, names made generic)."""

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

from creatio_schemas.data import DataBinding  # noqa: E402
from creatio_schemas.data.binding import JsonFile, coerce  # noqa: E402
from creatio_schemas.files import DVT_OF  # noqa: E402
from data import main  # noqa: E402

FIXTURES = HERE / "fixtures" / "UsrPkg"
BINDINGS = ("UsrStatus", "SysSettings_UsrMaxRows", "SysSettingsValue_UsrMaxRows")
NEW = "03edf152-0b98-4b17-91d6-574473b46241"  # UsrStatus row "New"
ALL_EMPLOYEES = "a29a3ba5-4b0d-de11-9a51-005056c00008"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


@contextlib.contextmanager
def workspace():
    """A writable copy of the fixture package inside its own packages folder."""
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    try:
        yield tmp / "UsrPkg"
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_round_trip_is_byte_identical():
    for name in BINDINGS:
        b = DataBinding(FIXTURES, name)
        for path, (text, bom) in b.files().items():
            assert read(path) == ("﻿" if bom else "") + text, path
        b.describe()
        b.rows()
        assert b.diff() == "", name


def test_reads_columns_rows_and_describe():
    b = DataBinding(FIXTURES, "UsrStatus")
    assert b.describe() == "UsrStatus: binds UsrOrderStatus, 3 rows, columns Id Name(loc) Description(loc), install with package"
    assert b.schema_name == "UsrOrderStatus" and b.key_columns == ["Id"] and b.cultures == ["en-US", "ru-RU"]
    assert b.columns["Name"]["uid"] == "736c30a7-c0ec-4fa9-b034-2552b319b633" and not b.columns["Name"]["key"]
    assert b.localized == ["Name", "Description"]
    assert b.rows()[0] == {"Id": NEW, "Name": {"en-US": "New", "ru-RU": "Новый"}, "Description": {"en-US": "", "ru-RU": ""}}
    assert [r["Name"] for r in b.rows("ru-RU")] == ["Новый", "В работе", "Выполнен"]
    assert b.row(NEW.upper())["Name"]["en-US"] == "New"
    v = DataBinding(FIXTURES, "SysSettingsValue_UsrMaxRows")
    row = v.rows()[0]
    assert row["IntegerValue"] == 10000 and row["SysAdminUnit"] == ALL_EMPLOYEES and v.localized == []
    assert v.display_values(v.key_of(row)) == {"SysSettings": "Max rows", "SysAdminUnit": "All employees"}
    s = DataBinding(FIXTURES, "SysSettings_UsrMaxRows")
    assert s.rows()[0]["Code"] == "UsrMaxRows" and row["SysSettings"] == s.rows()[0]["Id"]
    try:
        b.row("nope")
    except KeyError:
        pass
    else:
        raise AssertionError("an unknown key must raise")


def test_validate_finds_each_problem():
    for name in BINDINGS:
        assert DataBinding(FIXTURES, name).validate() == [], name
    b = DataBinding(FIXTURES, "SysSettingsValue_UsrMaxRows")
    cells = b.data.obj["PackageData"][0]["Row"]
    cells.append({"SchemaColumnUId": "11111111-1111-1111-1111-111111111111", "Value": 1})
    next(c for c in cells if c["SchemaColumnUId"] == b.columns["SysAdminUnit"]["uid"])["Value"] = "All employees"
    b.data.obj["PackageData"].append(json.loads(json.dumps(b.data.obj["PackageData"][0])))
    problems = "\n".join(b.validate())
    assert "which the descriptor does not list" in problems and "lookup SysAdminUnit = 'All employees' is not a UId" in problems
    assert "duplicate key" in problems
    s = DataBinding(FIXTURES, "UsrStatus")
    s.loc["ru-RU"].obj["PackageData"][0]["Row"][0]["Value"] = "22222222-2222-2222-2222-222222222222"
    assert s.validate() == ["Localization/data.ru-RU.json: row 22222222-2222-2222-2222-222222222222 is not in data.json"]
    s.descriptor.set("Columns", [dict(c, IsKey=False) for c in s.descriptor.data["Columns"]])
    assert any(p.startswith("warning: no key column") for p in s.validate()) and s.errors() != []


def test_edit_rows_and_save():
    with workspace() as pkg:
        v = DataBinding(pkg, "SysSettingsValue_UsrMaxRows")
        key = v.key_of(v.rows()[0])
        v.set_value(key, "IntegerValue", "500")
        v.set_value(key, "BooleanValue", "true")
        v.set_value(key, "SysAdminUnit", "33333333-3333-3333-3333-333333333333")
        for column, value in (("SysAdminUnit", "All employees"), ("Nope", "1"), ("BooleanValue", "yes")):
            try:
                v.set_value(key, column, value)
            except (KeyError, ValueError):
                pass
            else:
                raise AssertionError(f"{column}={value} must be refused")
        v.save()
        again = DataBinding(pkg, "SysSettingsValue_UsrMaxRows")
        assert again.rows()[0]["IntegerValue"] == 500 and again.rows()[0]["BooleanValue"] is True
        assert again.display_values(key)["SysAdminUnit"] == "" and again.display_values(key)["SysSettings"] == "Max rows"
        assert again.diff() == "" and "\t" not in read(again.data.path) and read(again.data.path).startswith("﻿{\r\n  \"PackageData\"")

        b = DataBinding(pkg, "UsrStatus")
        b.set_value(NEW, "Name", "Новая", "ru-RU")
        try:
            b.set_value(NEW, "Name", "x")
        except ValueError as e:
            assert "localised" in str(e)
        else:
            raise AssertionError("a localised column needs a culture")
        added = b.add_row({"Name": "On hold"})
        both = b.add_row({"Id": "44444444-4444-4444-4444-444444444444", "Name": {"en-US": "Closed", "ru-RU": "Закрыт"}})
        try:
            b.add_row({"Id": both})
        except ValueError:
            pass
        else:
            raise AssertionError("a duplicate key must be refused")
        b.remove_row("6249ed1f-9d7c-4556-8273-00bd2db4e0e0")
        assert b.errors() == []
        b.save()
        again = DataBinding(pkg, "UsrStatus")
        assert [r["Name"]["ru-RU"] for r in again.rows()] == ["Новая", "Выполнен", "On hold", "Закрыт"]
        assert again.row(added)["Name"] == {"en-US": "On hold", "ru-RU": "On hold"}
        assert all(c["SchemaColumnUId"] == again.columns["Id"]["uid"] for r in again.data.obj["PackageData"] for c in r["Row"])
        assert again.diff() == ""


def test_create_binds_an_object_of_the_workspace():
    with workspace() as pkg:
        b = DataBinding.create(pkg, "UsrPriority", "UsrOrderStatus", ["Id"], [{"Name": "High"}, {"Name": {"en-US": "Low", "ru-RU": "Низкий"}}],
                               ["en-US", "ru-RU"])
        cols = b.descriptor.data["Columns"]
        assert [(c["ColumnName"], c["ColumnUId"], c["IsKey"]) for c in cols] == [
            ("Id", "ae0e45ca-c495-4fe7-a39d-3ab7278e1617", True), ("Name", "736c30a7-c0ec-4fa9-b034-2552b319b633", False)]
        assert cols[1]["DataTypeValueUId"] == DVT_OF["MediumText"] and b.descriptor.data["Schema"]["Name"] == "UsrOrderStatus"
        assert read(pkg / "Data" / "UsrPriority" / "filter.json") == "" and b.validate() == []
        again = DataBinding(pkg, "UsrPriority")
        assert [r["Name"] for r in again.rows("ru-RU")] == ["High", "Низкий"] and again.diff() == ""
        assert len(again.data.obj["PackageData"][0]["Row"]) == 1  # the localised Name lives in Localization/ only
        empty = DataBinding.create(pkg, "UsrEmpty", "UsrOrderStatus", ["Id"], [], ["en-US"], ["Name"])
        key = empty.add_row({"Name": "Later"})  # the object says Name is localisable, the empty files cannot
        assert empty.row(key)["Name"] == {"en-US": "Later"}
        empty.loc = {}  # no Localization files: the platform keeps Name in data.json, so does add_row
        key = empty.add_row({"Name": "Flat"})
        assert empty.row(key)["Name"] == "Flat"
        key = empty.add_row({"Name": {"de-DE": "Spaeter"}})
        assert empty.cultures == ["de-DE"] and empty.row(key)["Name"] == {"de-DE": "Spaeter"}
        for args, error in ((("UsrX", "SysSettings", ["Id"], []), KeyError), (("Usr X", "UsrOrderStatus", ["Id"], []), ValueError),
                            (("UsrPriority", "UsrOrderStatus", ["Id"], []), FileExistsError), (("UsrY", "UsrOrderStatus", ["Id"], [{"Nope": 1}]), KeyError)):
            try:
                DataBinding.create(pkg, *args)
            except error:
                pass
            else:
                raise AssertionError(f"create{args} must raise {error.__name__}")


def test_json_file_keeps_the_style_of_the_file():
    with workspace() as pkg:
        path = pkg / "x.json"
        path.write_text('{\n\t"PackageData": [\n\t\t{\n\t\t\t"Value": "\\/Date(1793376038931+0200)\\/"\n\t\t}\n\t]\n}\n', encoding="utf-8", newline="")
        f = JsonFile(path)
        assert f.render() == read(path) and not f.bom
        f.obj["PackageData"].append({"Value": "a/b"})
        assert f.render() == ('{\n\t"PackageData": [\n\t\t{\n\t\t\t"Value": "\\/Date(1793376038931+0200)\\/"\n\t\t},\n\t\t{\n\t\t\t"Value": "a/b"\n\t\t}\n\t]\n}\n')
    assert coerce(DVT_OF["Float2"], "1.5") == 1.5 and coerce(DVT_OF["Integer"], "null") == "null" and coerce(DVT_OF["MediumText"], "7") == "7"


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(FIXTURES), "UsrStatus"]) == 0
        assert main(["validate", str(FIXTURES), "SysSettings_UsrMaxRows"]) == 0
        assert main(["rows", str(FIXTURES), "UsrStatus", "--limit", "1", "--culture", "ru-RU"]) == 0
    text = out.getvalue()
    assert "binds UsrOrderStatus" in text and f'{NEW}  Name="Новый"' in text and "... 2 more" in text
    with workspace() as pkg:
        rows = pkg.parent / "rows.json"
        rows.write_text(json.dumps([{"Name": "High"}]), encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert main(["new", str(pkg), "UsrPriority", "--table", "UsrOrderStatus", "--columns", "Description", "--cultures", "en-US,ru-RU",
                         "--rows", str(rows)]) == 0
            assert main(["add-row", str(pkg), "UsrPriority", "Name=Low", "Description=-"]) == 0
            key = out.getvalue().split("add row ")[1].split()[0]
            assert main(["set", str(pkg), "UsrPriority", key, "Name", "Низкий", "--culture", "ru-RU"]) == 0
            assert main(["remove-row", str(pkg), "UsrPriority", key, "--dry-run"]) == 0
            assert main(["set", str(pkg), "UsrPriority", key, "Nope", "1"]) == 2
        assert "columns Id Description(loc) Name(loc)" in out.getvalue() and "(dry run: nothing written)" in out.getvalue()
        assert [r["Name"] for r in DataBinding(pkg, "UsrPriority").rows("ru-RU")] == ["High", "Низкий"]


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
