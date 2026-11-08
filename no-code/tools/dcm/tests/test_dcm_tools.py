"""Checks for the DCM tools:  python tests/test_dcm_tools.py  (the fixture is a real case, names made generic)."""

import contextlib
import io
import shutil
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE.parent))

from creatio_schemas.dcm import DcmSchema  # noqa: E402
from creatio_schemas.describe import describe_item, describe_package  # noqa: E402
from dcm import main  # noqa: E402

FIXTURES = HERE / "fixtures" / "iaTest"
PAGES = TOOLS / "pages" / "tests" / "fixtures" / "iaTest"  # has iaOrder with the lookup column iaStatus


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_round_trip_is_byte_identical():
    case = DcmSchema(FIXTURES, "iaRequestCases")
    for path, (text, bom) in case.files().items():
        assert read(path) == ("﻿" if bom else "") + text, path
    case.describe()
    assert case.diff() == ""


def test_describe_reads_stages_steps_conditions_moves_and_filter():
    text = DcmSchema(FIXTURES, "iaRequestCases").describe()
    assert "Stage3 'Approval'" in text and "(1 steps)" in text
    assert "DcmElement3 'Approval' subprocess" in text and "[optional]" in text
    assert "when [#Approval.Next stage#] ==" in text and "-> Stage4" in text
    assert "Stage2 'Reopened'" in text and "alternative of Stage1" in text
    assert "applies to: iaRequest where iaCategory = Parent request" in text
    assert "Stage1 -> Stage3, Stage4, Stage5, Stage6" in text and "Stage2 -> any" in text


def test_queries_answer_one_part():
    assert describe_item(FIXTURES, "iaRequestCases", "stages").count("\n") == 5
    stage = describe_item(FIXTURES, "iaRequestCases", "stage Approval")
    assert "step DcmElement3" in stage and "can move to:" in stage
    steps = describe_item(FIXTURES, "iaRequestCases", "steps stage=Stage1")
    assert steps.count("\n") == 1 and "DcmElement2" in steps
    assert "Request" in describe_item(FIXTURES, "iaRequestCases", "step DcmElement1")
    moves = describe_item(FIXTURES, "iaRequestCases", "moves from=Stage1")
    assert moves.count("\n") == 3 and "Stage1 -> Stage3" in moves
    assert describe_item(FIXTURES, "iaRequestCases", "filter").startswith("iaRequest where")
    assert "dcm " in describe_package(FIXTURES) and "6 stages, 4 steps" in describe_package(FIXTURES)


def test_edit_and_create():
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(PAGES, tmp / "iaTest")
    shutil.copytree(FIXTURES / "Schemas" / "iaRequestCases", tmp / "iaTest" / "Schemas" / "iaRequestCases")
    shutil.copytree(FIXTURES / "Resources" / "iaRequestCases.Dcm", tmp / "iaTest" / "Resources" / "iaRequestCases.Dcm")
    try:
        case = DcmSchema(tmp / "iaTest", "iaRequestCases")
        rec = str(uuid.uuid4())
        s = case.add_stage("On hold", rec, color="#FFAC07", parent="Stage4")
        assert s["A2"] == "Stage7" and s["ParentStageUId"] == case.stage("Stage4")["UId"]
        case.connect("Stage7", "Stage1", both=False)
        assert ("Stage7", "Stage1") in case.connections and ("Stage1", "Stage7") not in case.connections
        assert case.remove_stage("Stage6") == "Stage6"
        assert not any("Stage6" in pair for pair in case.connections)
        assert case.resources.get("Stages.Stage6.Caption") is None and case.resources.get("Stages.Stage7.Caption") == "On hold"
        assert case.errors() == []
        case.save()
        again = DcmSchema(tmp / "iaTest", "iaRequestCases")
        assert [x["A2"] for x in again.stages] == ["Stage1", "Stage2", "Stage3", "Stage4", "Stage5", "Stage7"]
        # a stage that a step condition moves to cannot go silently
        again.remove_stage("Stage2")
        assert any("unknown stage record" in p for p in again.errors())
        # a new case on iaOrder.iaStatus (lookup to iaOrderStatus) with two chained stages
        a, b = str(uuid.uuid4()), str(uuid.uuid4())
        new = DcmSchema.create(tmp / "iaTest", "iaOrderCases", "Order cases", "iaOrder", "iaStatus", [("New", a), ("Done", b)])
        assert new.entity == "iaOrder" and new.stage_column == "iaStatus"
        assert new.connections == [("Stage1", "Stage2"), ("Stage2", "Stage1")]
        reloaded = DcmSchema(tmp / "iaTest", "iaOrderCases")
        assert reloaded.describe().count("record=") == 2 and reloaded.errors() == []
        assert "iaOrderCases" in describe_package(tmp / "iaTest", "dcm")
        try:
            DcmSchema.create(tmp / "iaTest", "iaBad", "x", "iaOrder", "iaName")
        except ValueError as e:
            assert "not a lookup" in str(e)
        else:
            raise AssertionError("a text column must be refused as stage column")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_cli():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(["inspect", str(FIXTURES), "iaRequestCases"]) == 0
        assert main(["validate", str(FIXTURES), "iaRequestCases"]) == 0
    assert "stages:" in out.getvalue()


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
