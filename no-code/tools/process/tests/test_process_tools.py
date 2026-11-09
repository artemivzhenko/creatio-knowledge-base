"""
Checks for the process tools. Pure standard library:  python tests/test_process_tools.py
(also collected by pytest). The fixtures are two real processes exported from Creatio 8.2.3.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from creatio_schemas import ProcessSchema, rename_schema  # noqa: E402
from creatio_schemas.process import ELEMENT_KINDS, TASK_ALIASES, USER_TASKS, short_type  # noqa: E402

FIXTURES = HERE / "fixtures" / "iaTest"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_round_trip_is_byte_identical():
    for name in ("iaProcess_0d4c445", "iaDeleteOldLogs_Process"):
        p = ProcessSchema(FIXTURES, name)
        files = p.files()
        for path, (text, bom) in files.items():
            assert read(path) == ("﻿" if bom else "") + text, path
        p.describe()
        assert p.files() == files and p.diff() == ""  # reading never changes the metadata


def test_inspect_decodes_user_task_and_captions():
    p = ProcessSchema(FIXTURES, "iaDeleteOldLogs_Process")
    text = p.describe()
    assert "DeleteDataUserTask1 [DeleteDataUserTask]" in text
    assert "cron '0 0 0 * * ? *'" in text
    assert p.resources.get("BaseElements.DeleteDataUserTask1.Caption", "uk-UA") is None  # designer writes element captions to en-US only
    assert p.validate() == []


def test_build_process_from_scratch():
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "iaTest"
        shutil.copytree(FIXTURES, pkg)
        p = ProcessSchema.create(pkg, "iaDemo_Process", "Demo", ["en-US", "ru-RU"])
        p.add_param("Counter", "Integer", "Variable", "Counter", 1)
        p.add_param("Verdict", "Text", "Out", "Verdict")
        p.add_element("formula", "Compute", "Add 41", after="StartEvent1", before="TerminateEvent1")
        p.set_formula("Compute", "{Parameter:Counter} + 41", "Counter")
        p.add_element("exclusiveGateway", "Check", after="Compute", before="TerminateEvent1")
        p.add_element("formula", "Big", "big", after="Check", before="TerminateEvent1")
        p.set_formula("Big", '"big"', "Verdict")
        p.set_condition("SequenceFlow3", "{Parameter:Counter} > 10")
        read_el = p.add_element("readData", "ReadTests", "Read tests", after="StartEvent1", before="Compute")
        p.set_entity(read_el, "iaTest")
        p.set_caption("Compute", "Прибавить 41", ["ru-RU"])
        p.save()

        q = ProcessSchema(pkg, "iaDemo_Process")
        assert q.validate() == []
        names = [e["A2"] for e in q.elements]
        # every node precedes every flow: the platform resolves flow endpoints while reading
        first_flow = next(i for i, e in enumerate(q.elements) if short_type(e).endswith("Flow"))
        assert all(not short_type(e).endswith("Flow") for e in q.elements[:first_flow])
        assert all(short_type(e).endswith("Flow") for e in q.elements[first_flow:])
        assert "ConditionalSequenceFlow3" in names
        assert q.element("ConditionalSequenceFlow3")["CI4"] == 2
        assert "{Parameter:Counter} > 10" == q.expressions.decode(q.element("ConditionalSequenceFlow3")["CI3"])
        assert q.element("Compute")["HS1"] == q.param("Counter")["UId"]
        rt = q.element("ReadTests")
        assert q.element_param(rt, "ResultEntity")["L9"] == "8e9352c9-3362-4c77-8dc2-acbb079c1040"
        filters = json.loads(q.element_param(rt, "DataSourceFilters")["L8"]["GS2"])
        assert json.loads(filters["dataSourceFilters"])["rootSchemaName"] == "iaTest"
        assert len(q.mappings) == len(q.element_params(rt))
        expected = USER_TASKS["ReadDataUserTask"]["captions"]["Parameters.ResultType.Caption"]
        assert q.resources.get("BaseElements.ReadTests.Parameters.ResultType.Caption", "ru-RU") == expected["ru-RU"]
        assert q.resources.get("BaseElements.ReadTests.Parameters.ResultType.Caption", "en-US") == expected["en-US"]
        assert q.resources.get("BaseElements.Compute.Caption", "ru-RU") == "Прибавить 41"
        assert '"Caption": "Demo"' in q.descriptor.text and "\\/Date(" in q.descriptor.text

        q.rename_element("Compute", "AddFortyOne")
        assert q.resources.get("BaseElements.AddFortyOne.Caption") == "Add 41"
        q.remove_element("Big")
        assert "ConditionalSequenceFlow3" not in [e["A2"] for e in q.elements]
        assert q.validate() == []

        report = rename_schema(pkg, "iaDemo_Process", "iaRenamed_Process", apply=True)
        assert any("Schemas\\iaDemo_Process -> Schemas\\iaRenamed_Process" in r.replace("/", "\\") for r in report)
        r = ProcessSchema(pkg, "iaRenamed_Process")
        assert r.uid == q.uid and r.name == "iaRenamed_Process"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_every_element_kind_builds_and_validates():
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "iaTest"
        shutil.copytree(FIXTURES, pkg)
        p = ProcessSchema.create(pkg, "iaAll_Process", "All kinds")
        p.add_param("Counter", "Integer", "Variable", "Counter", 1)
        prev = "StartEvent1"
        for i, kind in enumerate(ELEMENT_KINDS):
            el = p.add_element(kind, f"El{i}_{kind}", kind, after=None if kind.startswith("start") else prev)
            if kind.startswith("start"):
                p.add_flow(el["A2"], "TerminateEvent1")
            else:
                prev = el["A2"]
            if kind == "startSignal":
                p.set_entity(el, "iaTest")
                assert el["FC2"] == "8e9352c9-3362-4c77-8dc2-acbb079c1040"
            if kind == "subProcess":
                p.set_calls(el, "iaProcess_0d4c445")
                assert el["CK4"] == "5939a180-af82-42dd-bf53-23ea059da70a"
            if kind in ("throwMessage", "catchMessage"):
                p.set_message(el, "Msg")
        for i, task in enumerate(USER_TASKS):
            el = p.add_element(f"userTask:{task}", f"Task{i}", task, after=prev)
            assert len(p.element_params(el)) == len(USER_TASKS[task]["parameters"])
            prev = el["A2"]
        for i, alias in enumerate(TASK_ALIASES):
            p.add_element(alias, f"Alias{i}", alias, after=prev)
            prev = f"Alias{i}"
        p.add_flow(prev, "TerminateEvent1")
        p.save()
        q = ProcessSchema(pkg, "iaAll_Process")
        assert q.validate() == [], q.validate()
        assert len(q.nodes()) == 2 + len(ELEMENT_KINDS) + len(USER_TASKS) + len(TASK_ALIASES)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_command_line():
    import contextlib
    import io
    sys.path.insert(0, str(HERE.parent))
    import proc
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "iaTest"
        shutil.copytree(FIXTURES, pkg)
        meta = pkg / "Schemas" / "iaProcess_0d4c445" / "metadata.json"
        before = read(meta)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert proc.main(["param", str(pkg), "iaProcess_0d4c445", "add", "Counter", "--type", "Integer", "--dry-run"]) == 0
        assert '"A2": "Counter"' in out.getvalue() and read(meta) == before  # a dry run writes nothing
        with contextlib.redirect_stdout(io.StringIO()):
            assert proc.main(["param", str(pkg), "iaProcess_0d4c445", "add", "Counter", "--type", "Integer"]) == 0
            assert proc.main(["element", str(pkg), "iaProcess_0d4c445", "add", "Calc", "--kind", "formula", "--after", "StartEvent1"]) == 0
            assert proc.main(["element", str(pkg), "iaProcess_0d4c445", "formula", "Calc", "{Parameter:Counter} + 1", "--result", "Counter"]) == 0
        with contextlib.redirect_stderr(io.StringIO()):
            assert proc.main(["element", str(pkg), "iaProcess_0d4c445", "remove", "Nope"]) == 2
        q = ProcessSchema(pkg, "iaProcess_0d4c445")
        assert q.expressions.decode(q.element("Calc")["CH1"]) == "{Parameter:Counter} + 1" and q.validate() == []
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_record_signals_modes_columns_and_conditions():
    import json
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "iaTest")
    try:
        pkg = tmp / "iaTest"
        p = ProcessSchema.create(pkg, "iaSignals_Process", "Signals")
        start = p.add_element("startSignal", "OnOrderChange", "On order change")
        p.set_signal(start, "iaTest", "added,modified", ["iaName", "iaIsActive"], "iaNumber > 100; iaIsActive = true; iaContactLookup is not null")
        assert start["FC2"] == "8e9352c9-3362-4c77-8dc2-acbb079c1040" and start["DZ5"] == 3 and start["DZ3"] is True and start["DZ2"] is False
        assert start["DZ11"] is True and len(json.loads(start["DZ12"])) == 2 and start["DZ8"] is True
        outer = json.loads(start["DZ13"])
        edit, run = json.loads(outer["serializedFilterEditData"]), json.loads(outer["dataSourceFilters"])
        kinds = sorted(i["className"] for i in edit["items"].values())
        assert kinds == ["Terrasoft.CompareFilter", "Terrasoft.CompareFilter", "Terrasoft.IsNullFilter"] and edit["rootSchemaName"] == "iaTest"
        assert len(run["items"]) == 3 and all("className" not in i for i in run["items"].values())
        gt = next(i for i in edit["items"].values() if i["leftExpression"]["columnPath"] == "iaNumber")
        assert gt["comparisonType"] == 5 and gt["rightExpression"]["parameter"]["value"] == 100 and gt["dataValueType"] == 4
        flag = next(i for i in edit["items"].values() if i["leftExpression"]["columnPath"] == "iaIsActive")
        assert flag["rightExpression"]["parameter"]["value"] is True and flag["dataValueType"] == 12
        assert p.describe_signal(start) == ("record signal: iaTest added or modified (columns: iaName, iaIsActive); "
                                            "when iaTest where iaNumber > 100 and iaIsActive = True and iaContactLookup is not null")
        # a named (non-record) signal on a catch element, then back to a record one
        catch = p.add_element("catchSignal", "WaitSig", "Wait", after="OnOrderChange")
        p.set_message(catch, "OrderClosed")
        assert catch["CA1"] == "OrderClosed" and catch["CA2"] is True and catch["CA3"] is False and p.describe_signal(catch) == "signal 'OrderClosed'"
        p.set_signal(catch, "iaTest", "deleted")
        assert catch["CA3"] is True and catch["CA5"] == 4 and catch["CA6"] == start["FC2"] and "CA13" in catch
        p.add_flow("WaitSig", "TerminateEvent1")
        p.save()
        again = ProcessSchema(pkg, "iaSignals_Process")
        assert again.describe_signal(again.element("OnOrderChange")).startswith("record signal: iaTest added or modified")
        assert again.errors() == []
        for bad in (lambda: p.set_signal(start, on="renamed"), lambda: p.set_signal(start, columns=["Nope"]), lambda: p.set_signal(start, condition="iaNumber ~ 1")):
            try:
                bad()
                raise AssertionError("expected an error")
            except (ValueError, KeyError):
                pass
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def test_record_values_and_sub_process_mappings():
    import contextlib
    import io
    sys.path.insert(0, str(HERE.parent))
    import proc
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(FIXTURES, tmp / "iaTest")
    try:
        pkg = tmp / "iaTest"
        child = ProcessSchema(pkg, "iaProcess_0d4c445")
        child.add_param("RecordId", "Guid", "In", "Record")
        child.add_param("Note", "Text", "In", "Note")
        child.save()
        p = ProcessSchema.create(pkg, "iaValues_Process", "Values")
        p.add_param("StatusId", "Guid", "Variable", "Status")
        add = p.add_element("addData", "AddTest", "Add test", after="StartEvent1", before="TerminateEvent1")
        p.set_entity(add, "iaTest")
        p.set_record_values(add, {"iaNumber": 100, "iaName": 'Say "hi"', "iaIsActive": "true", "iaContactLookup": "{Parameter:StatusId}",
                                  "iaAccount": "c4ed336c-3e9b-40fe-8b82-5632476472b4", "iaAmount": "null"})
        p.set_record_values(add, {"iaNumber": "200"})  # a column set again keeps its place and item id
        change = p.add_element("changeData", "MarkTest", "Mark test", after="AddTest", before="TerminateEvent1")
        p.set_entity(change, "iaTest")
        p.set_record_values(change, {"iaComment": "{Element:AddTest.Parameter:RecordId}"}, expression=True)
        sub = p.add_element("subProcess", "CallChild", "Call child", after="MarkTest", before="TerminateEvent1")
        p.set_calls(sub, "iaProcess_0d4c445")
        p.map_params(sub, {"RecordId": "{Parameter:StatusId}"})
        p.save()

        q = ProcessSchema(pkg, "iaValues_Process")
        assert q.validate() == [], q.validate()
        add = q.element("AddTest")
        assert q.describe_record_values(add) == ('iaNumber = 200, iaName = "Say \\"hi\\"", iaIsActive = True, iaContactLookup = {Parameter:StatusId}, '
                                                 'iaAccount = c4ed336c-3e9b-40fe-8b82-5632476472b4, iaAmount = null')
        assert q.describe_record_values(q.element("MarkTest")) == "iaComment = {Element:AddTest.Parameter:RecordId}"
        values = q.element_param(add, "RecordDefValues")
        items = json.loads(values["L8"]["GS2"])["$values"]
        assert list(items[0]) == ["ItemUId", "columnMetaPath", "schemaUId", "value", "displayValue", "parameterValue"]
        assert items[3]["displayValue"]["value"] == "[#StatusId#]" and items[4]["value"]["value"].startswith("[#Lookup.25d7c1ab-1de0-4501-b402-02e0e5a72d6e.")
        assert json.loads(items[0]["parameterValue"]["value"])["DataValueTypeUId"] == "6b6b74e2-820d-490e-a017-2b73d4ccf2b0"
        assert next(m for m in q.mappings if m["GT3"] == values["UId"])["GT1"] == values["L8"]  # the mapping carries the same value
        sub = q.element("CallChild")
        assert q.describe_call(sub) == "calls iaProcess_0d4c445 with RecordId = {Parameter:StatusId}"
        assert [x["A2"] for x in sub["BP2"]] == ["RecordId", "Note"] and all(x["A3"] == child.uid for x in sub["BP2"])
        maps = [m for m in q.mappings if m["A2"] == "CallChild"]
        assert len(maps) == 2 and {m["GT5"] for m in maps} == {x["UId"] for x in child.params} and all(m["GT4"] == child.uid for m in maps)
        text = q.describe()
        assert "values: iaNumber = 200" in text and "calls iaProcess_0d4c445 with RecordId" in text
        assert ProcessSchema(pkg, "iaValues_Process").diff() == ""  # a no-op load writes the same bytes

        for bad, error in ((lambda: q.set_record_values(add, {"Nope": 1}), KeyError), (lambda: q.set_record_values(add, {"iaNumber": "many"}), ValueError),
                           (lambda: q.set_record_values(add, {"iaAccount": "Acme"}), ValueError), (lambda: q.set_record_values(add, {"iaDate": "2026-01-01"}), ValueError),
                           (lambda: q.set_record_values(sub, {"iaNumber": 1}), ValueError), (lambda: q.map_params(sub, {"Nope": 1}), KeyError),
                           (lambda: q.map_params(add, {"RecordId": 1}), ValueError)):
            try:
                bad()
            except error:
                pass
            else:
                raise AssertionError(f"expected {error.__name__}")
        # a value list that names a column the object no longer has
        stale = json.loads(values["L8"]["GS2"])
        stale["$values"][0]["columnMetaPath"]["value"] = "11111111-1111-1111-1111-111111111111"
        values["L8"]["GS2"] = json.dumps(stale)
        assert q.validate() == ["element AddTest: column 11111111-1111-1111-1111-111111111111 is not a column of iaTest"]
        # collection mode and an unknown called process are refused
        sub["BP2"].append({"A2": "InputRecordCollection"})
        for bad, error in ((lambda: q.map_params(sub, {"RecordId": 1}), ValueError),):
            try:
                bad()
            except error:
                pass
            else:
                raise AssertionError("collection mode must be refused")
        sub["CK4"] = "22222222-2222-2222-2222-222222222222"
        try:
            q.called_process(sub)
        except KeyError as e:
            assert "not in the workspace" in str(e)
        else:
            raise AssertionError("an unknown called process must raise")

        with contextlib.redirect_stdout(io.StringIO()):
            assert proc.main(["element", str(pkg), "iaValues_Process", "values", "MarkTest", "iaNumber=7"]) == 0
            assert proc.main(["element", str(pkg), "iaValues_Process", "map", "CallChild", "Note={Parameter:StatusId}", "--expr"]) == 0
        with contextlib.redirect_stderr(io.StringIO()):
            assert proc.main(["element", str(pkg), "iaValues_Process", "values", "MarkTest", "Nope=1"]) == 2
        r = ProcessSchema(pkg, "iaValues_Process")
        assert r.describe_record_values(r.element("MarkTest")).endswith("iaNumber = 7")
        assert r.describe_call(r.element("CallChild")).endswith("Note = {Parameter:StatusId}")
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
