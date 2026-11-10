"""Checks for the DCM tools:  python tests/test_dcm_tools.py  (the fixture is a real case, names made generic)."""

import contextlib
import io
import json
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


def test_steps_with_mappings_and_conditions():
    from creatio_schemas import ProcessSchema
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "iaTest")
    procs = TOOLS / "process" / "tests" / "fixtures" / "iaTest"
    shutil.copytree(procs / "Schemas" / "iaProcess_0d4c445", tmp / "iaTest" / "Schemas" / "iaProcess_0d4c445")
    shutil.copytree(procs / "Resources" / "iaProcess_0d4c445.Process", tmp / "iaTest" / "Resources" / "iaProcess_0d4c445.Process")
    try:
        pkg = tmp / "iaTest"
        called = ProcessSchema(pkg, "iaProcess_0d4c445")
        called.add_param("Request", "Lookup", "In", "Request")
        nxt = called.add_param("NextStage", "Lookup", "Out", "Next stage")
        nxt["L9"] = "0d1a858f-2b4c-4c4f-9738-a99900c3a482"  # the stage column's lookup, as the fixture's Approval step has it
        called.save()
        before = {p: read(p) for p in DcmSchema(pkg, "iaRequestCases").files()}

        case = DcmSchema(pkg, "iaRequestCases")
        e = case.add_step("Stage2", None, "iaProcess_0d4c445", "Check request", {"Request": "{Record:Id}"}, required=True,
                          conditions=[("NextStage = Stage4", "Stage4")])
        assert e["A2"] == "DcmElement5" and e["ProcessFlowElement"]["A2"] == "DcmProcessElement5" and e["RequiredType"] == 1
        assert list(e) == ["BL1", "UId", "A2", "A3", "A4", "A5", "IL2", "RequiredType", "Conditions", "ProcessFlowElement"]
        flow = e["ProcessFlowElement"]
        assert list(flow) == ["BL1", "UId", "A2", "BL7", "BN2", "BO2", "BO3", "BP2", "CK4", "CK2", "CK3"] and flow["CK4"] == called.uid
        request = next(p for p in flow["BP2"] if p["A2"] == "Request")
        assert request["L8"] == {"GS1": 3, "GS2": "[#ColumnValue.{767ff163-8d41-406e-93db-11e41147b5c3}.{ae0e45ca-c495-4fe7-a39d-3ab7278e1617}#]",
                                 "GS5": case.uid}
        maps = [m for m in case.schema["BK15"] if m["A2"] == "DcmProcessElement5"]
        assert len(maps) == 2 and all(m["GT4"] == called.uid and m["GT1"] == {"GS5": called.uid} for m in maps)
        cond = json.loads(e["Conditions"])[0]
        assert cond["nextStageId"] == case.stage("Stage4")["StageRecordId"] and cond["resultFormula"]["displayValue"].startswith("[#Check request.Next stage#] == [#Lookup.")
        assert case.errors() == []
        case.save()

        again = DcmSchema(pkg, "iaRequestCases")
        step = describe_item(pkg, "iaRequestCases", "step DcmElement5")
        assert "param Request: [#Main record.Id#]" in step and "-> Stage4" in step, step
        assert "step DcmElement5" in describe_item(pkg, "iaRequestCases", "stage Stage2")
        bad = next(p for p in again.element("DcmElement5")[1]["ProcessFlowElement"]["BP2"] if p["A2"] == "NextStage")
        bad["A2"] = "Gone"
        assert "step DcmElement5: parameter Gone is not a parameter of iaProcess_0d4c445" in again.validate()
        bad["A2"] = "NextStage"
        for fn, error in ((lambda: again.add_step("Stage2", None, "iaNope_Process", "x"), KeyError),
                          (lambda: again.add_step("Stage2", None, "iaProcess_0d4c445", "x", {"Nope": 1}), KeyError),
                          (lambda: again.add_step("Stage2", "DcmElement5", "iaProcess_0d4c445", "x"), ValueError),
                          (lambda: again.add_step("Stage2", None, "iaProcess_0d4c445", "x", {"Request": "{Record:Nope}"}), KeyError),
                          (lambda: again.add_step("Stage2", None, "iaProcess_0d4c445", "x", conditions=[("NextStage ~ 1", "Stage4")]), ValueError),
                          (lambda: again.add_step("Stage2", None, "iaProcess_0d4c445", "x", conditions=[("Nope = 1", "Stage4")]), KeyError)):
            try:
                fn()
            except error:
                pass
            else:
                raise AssertionError(f"expected {error.__name__}")
        # a constant, a case parameter and a plain (non-lookup) condition
        again = DcmSchema(pkg, "iaRequestCases")
        e2 = again.add_step("Stage5", "DcmElement9", "iaProcess_0d4c445", "Const", {"Request": "c4ed336c-3e9b-40fe-8b82-5632476472b4"},
                            conditions=[("NextStage != c4ed336c-3e9b-40fe-8b82-5632476472b4", "Stage6")])
        assert next(p for p in e2["ProcessFlowElement"]["BP2"] if p["A2"] == "Request")["L8"]["GS1"] == 1 and e2["RequiredType"] == 0
        try:
            again.add_step("Stage5", None, "iaProcess_0d4c445", "Par", {"Request": "{Parameter:Nope}"})
        except KeyError:
            pass
        else:
            raise AssertionError("an unknown case parameter must raise")

        case = DcmSchema(pkg, "iaRequestCases")  # the saved case: DcmElement5 only (the second step was never saved)
        assert case.remove_step("Check request") == "DcmElement5"
        case.save()
        after = DcmSchema(pkg, "iaRequestCases")
        for path, (text, bom) in after.files().items():
            if path.name != "descriptor.json":  # ModifiedOnUtc moves with every save
                assert ("﻿" if bom else "") + text == before[path], path

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert main(["add-step", str(pkg), "iaRequestCases", "--stage", "Stage2", "--process", "iaProcess_0d4c445", "--caption", "Cli step",
                         "--map", "Request={Record:Id}", "--when", "NextStage = Stage4 -> Stage4", "--required"]) == 0
            assert main(["remove-step", str(pkg), "iaRequestCases", "Cli step", "--dry-run"]) == 0
        assert "add step DcmElement5 'Cli step'" in out.getvalue() and "remove step DcmElement5" in out.getvalue()
        with contextlib.redirect_stderr(io.StringIO()):
            assert main(["add-step", str(pkg), "iaRequestCases", "--stage", "Stage2", "--process", "iaProcess_0d4c445", "--caption", "x",
                         "--when", "no arrow"]) == 2
        assert DcmSchema(pkg, "iaRequestCases").element("DcmElement5")[1]["RequiredType"] == 1
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
