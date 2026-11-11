"""
Checks for the SQL script tools. Pure standard library:  python tests/test_sqlscripts_tools.py
(also collected by pytest). Fixtures: four scripts built by these tools in UsrPkg and installed on
Creatio 8.2.3 (a function, a view that depends on it, a run log, an MSSQL script the PostgreSQL
install skips), and one platform script with dependencies (ProcessLibrary).
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

from creatio_schemas.sqlscript import SqlScript  # noqa: E402

FIXTURES = HERE / "fixtures"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def copy() -> Path:
    tmp = Path(tempfile.mkdtemp())
    shutil.copytree(FIXTURES, tmp, dirs_exist_ok=True)
    return tmp


def test_round_trip_and_redump_are_byte_identical():
    scripts = SqlScript.all(FIXTURES / "UsrPkg") + SqlScript.all(FIXTURES / "ProcessLibrary")
    assert len(scripts) == 5
    for s in scripts:
        files = s.files()
        for path, (text, bom) in files.items():
            assert read(path) == ("﻿" if bom else "") + text, path
        original = s.descriptor.text
        engine = s.descriptor.data["DBEngineType"]
        s.set_engine("oracle")
        s.descriptor.set("DBEngineType", engine)
        assert s.descriptor.text == original  # a re-dump keeps the "\/Date(ms)\/" literal and the layout
        assert s.errors() == [], (s.name, s.validate())


def test_read_settings_and_dependencies():
    view = SqlScript(FIXTURES / "UsrPkg", "UsrAShipmentViewPostgreSql")
    assert view.engine == "postgresql" and view.install_type == "after-package"
    assert [d["Name"] for d in view.depends_on] == ["UsrFnShipmentLabelPostgreSql"]
    platform = SqlScript(FIXTURES / "ProcessLibrary", "VwProcessLibPostgreSql")
    assert len(platform.depends_on) == 3 and all(set(d) == {"UId", "Name"} for d in platform.depends_on)
    assert "runs after: VwSysSchemaInWorkspacePostgreSql" in platform.describe()
    assert SqlScript(FIXTURES / "UsrPkg", "UsrSqlRunLogMSSql").engine == "mssql"


def test_create_and_change():
    tmp = copy()
    try:
        pkg = tmp / "UsrPkg"
        s = SqlScript.create(pkg, "UsrDemoPostgreSql", "select 1;\nselect 2;\n", "postgresql", "after-data")
        desc = read(s.descriptor.path)
        assert desc.startswith("﻿{\r\n  \"SqlScript\": {") and '"ModifiedOnUtc": "\\/Date(' in desc
        assert list(json.loads(desc.lstrip("﻿"))["SqlScript"]) == ["UId", "Name", "DBEngineType", "InstallType", "ModifiedOnUtc",
                                                                       "BackwardCompatibilityConfirmed", "DependsOn"]
        assert read(s.body_path) == "select 1;\r\nselect 2;\r\n"  # no BOM, CRLF as the platform exports
        dep = s.add_dependency("UsrFnShipmentLabelPostgreSql")
        assert dep["UId"] == SqlScript(pkg, "UsrFnShipmentLabelPostgreSql").uid
        s.add_dependency("VwSysSchemaInWorkspacePostgreSql", uid="CF234830-1CFB-4D0E-9278-E8578253F3A7")
        s.save()
        s = SqlScript(pkg, "UsrDemoPostgreSql")
        assert s.install_type == "after-data" and [d["Name"] for d in s.depends_on] == ["UsrFnShipmentLabelPostgreSql", "VwSysSchemaInWorkspacePostgreSql"]
        s.remove_dependency("VwSysSchemaInWorkspacePostgreSql")
        s.set_install_type("before-package")
        assert '-    "InstallType": 2,' in s.diff() and '+    "InstallType": 0,' in s.diff()
        try:
            s.add_dependency("NoSuchScript")
            raise AssertionError("an unknown script needs its UId")
        except KeyError:
            pass
        s.set_body("select 1\nGO\n")
        s.set_engine("postgresql")
        assert any("'GO'" in p for p in s.validate())
        s.set_engine("mssql")
        assert any("ends with 'PostgreSql'" in p for p in s.validate())
        s.descriptor.set("DependsOn", s.depends_on + [{"UId": s.uid, "Name": s.name}])
        assert "the script depends on itself" in s.errors()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_command_line():
    import sqlscripts
    tmp = copy()
    try:
        pkg = tmp / "UsrPkg"
        body = tmp / "b.sql"
        body.write_text("create or replace view \"UsrVwX\" as select 1 as a;\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            assert sqlscripts.main(["new", str(pkg), "UsrVwXPostgreSql", "--file", str(body), "--after", "UsrFnShipmentLabelPostgreSql"]) == 0
        before = read(pkg / "SqlScripts" / "UsrVwXPostgreSql" / "descriptor.json")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert sqlscripts.main(["set", str(pkg), "UsrVwXPostgreSql", "--install", "after-data", "--dry-run"]) == 0
            assert sqlscripts.main(["list", str(pkg)]) == 0
        assert '"InstallType": 2' in out.getvalue() and "UsrVwXPostgreSql" in out.getvalue()
        assert read(pkg / "SqlScripts" / "UsrVwXPostgreSql" / "descriptor.json") == before
        with contextlib.redirect_stderr(io.StringIO()):
            assert sqlscripts.main(["depend", str(pkg), "UsrVwXPostgreSql", "remove", "Nope"]) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
