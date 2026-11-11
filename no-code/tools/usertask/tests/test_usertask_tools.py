"""Checks for the user-task tools:  python tests/test_usertask_tools.py  (the fixture is a real user task, names made generic)."""

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

from creatio_schemas.describe import describe_item, describe_package  # noqa: E402
from creatio_schemas.usertask import UserTaskSchema  # noqa: E402
from usertask import main  # noqa: E402

FIXTURES = HERE / "fixtures" / "UsrPkg"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_round_trip_keeps_images_in_resources():
    task = UserTaskSchema(FIXTURES, "UsrRunCase_UserTask")
    for path, (text, bom) in task.files().items():
        assert read(path) == ("﻿" if bom else "") + text, path
    assert task.diff() == ""
    assert 'Type="Image" ContentType="Data" FileExtension=".svg"' in task.resources.render("en-US")


def test_describe_and_queries():
    task = UserTaskSchema(FIXTURES, "UsrRunCase_UserTask")
    text = task.describe()
    assert "user task, interactive" in text
    assert "RecordId                     Guid         In        required" in text
    assert "protected override bool InternalExecute(ProcessExecutingContext context)" in text
    assert "UsrCaseHelper" in task.method("InternalExecute") and task.method("InternalExecute").rstrip().endswith("}")
    assert describe_item(FIXTURES, "UsrRunCase_UserTask", "params direction=In").count("\n") == 2
    assert '"A2": "DcmSchemaName"' in describe_item(FIXTURES, "UsrRunCase_UserTask", "param DcmSchemaName")
    assert describe_item(FIXTURES, "UsrRunCase_UserTask", "methods").count("\n") == 4
    assert "RunDcmCase" in describe_item(FIXTURES, "UsrRunCase_UserTask", "method InternalExecute")
    assert "user-task" in describe_package(FIXTURES) and "3 params, 5 methods, interactive" in describe_package(FIXTURES)


def test_edit_and_create():
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "UsrPkg")
    try:
        task = UserTaskSchema(tmp / "UsrPkg", "UsrRunCase_UserTask")
        p = task.add_param("Note", "Text", "Out", "Note", required=False)
        assert p["L12"] == 1 and "L6" not in p
        task.rename_param("DcmSchemaName", "CaseName")
        task.remove_param("EntitySchemaName")
        assert task.errors() == []
        task.save()
        again = UserTaskSchema(tmp / "UsrPkg", "UsrRunCase_UserTask")
        assert [x["A2"] for x in again.params] == ["RecordId", "CaseName", "Note"]
        assert again.resources.get("Parameters.CaseName.Caption") == "DcmSchemaName" and again.resources.get("Parameters.Note.Caption") == "Note"
        assert again.resources.get("LargeSvgImage") is not None  # images survive an edit
        new = UserTaskSchema.create(tmp / "UsrPkg", "UsrNotify_UserTask", "Notify owner", [("RecordId", "Guid", "In", "Record", True), ("Sent", "Boolean", "Out")])
        reloaded = UserTaskSchema(tmp / "UsrPkg", "UsrNotify_UserTask")
        assert reloaded.errors() == [] and len(reloaded.params) == 2 and reloaded.params[0]["L6"] is True
        assert "partial class UsrNotify_UserTask" in reloaded.source and "InternalExecute" in reloaded.methods()[0]
        assert reloaded.schema["FK7"] is True and reloaded.interactive is False
        assert "UsrNotify_UserTask" in describe_package(tmp / "UsrPkg", "user-task")
        assert not reloaded.generated_path.exists()  # no project in the package: nothing to compile
        (tmp / "UsrPkg" / "Files").mkdir()
        (tmp / "UsrPkg" / "Files" / "UsrPkg.csproj").write_text("<Project />")
        reloaded.add_param("Amount", "Money", "In", "Amount")
        reloaded.save()
        generated = read(reloaded.generated_path)
        assert generated.startswith("﻿namespace Terrasoft.Core.Process.Configuration")
        assert "public partial class UsrNotify_UserTask : ProcessUserTask" in generated
        assert "public virtual Guid RecordId {" in generated and "public virtual bool Sent {" in generated and "public virtual Decimal Amount {" in generated
        assert 'writer.WriteValue("Sent", Sent, false);' in generated and "Amount = reader.GetValue<System.Decimal>();" in generated
        assert f'ResourceManager = "{reloaded.uid.replace("-", "")}"' in generated
        assert UserTaskSchema(tmp / "UsrPkg", "UsrNotify_UserTask").diff() == ""
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(FIXTURES), "UsrRunCase_UserTask"]) == 0
        assert main(["method", str(FIXTURES), "UsrRunCase_UserTask", "InternalExecute"]) == 0
    assert "parameters:" in out.getvalue() and "RunDcmCase" in out.getvalue()


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
