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
sys.path.insert(0, str(HERE.parent))

from pschema import ELEMENT_TYPES, TASK_ALIASES, USER_TASKS, Process, create_process, short_type  # noqa: E402
from refactor import rename_schema  # noqa: E402

FIXTURES = HERE / "fixtures" / "iaTest"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def test_round_trip_is_byte_identical():
    for name in ("iaProcess_0d4c445", "iaDeleteOldLogs_Process"):
        p = Process(FIXTURES, name)
        for path, text in p.files().items():
            assert read(path) == text, path


def test_inspect_decodes_user_task_and_captions():
    p = Process(FIXTURES, "iaDeleteOldLogs_Process")
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
        p = create_process(pkg, "iaDemo_Process", "Demo", ["en-US", "ru-RU"])
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

        q = Process(pkg, "iaDemo_Process")
        assert q.validate() == []
        names = [e["A2"] for e in q.elements]
        # every node precedes every flow: the platform resolves flow endpoints while reading
        first_flow = next(i for i, e in enumerate(q.elements) if short_type(e).endswith("Flow"))
        assert all(not short_type(e).endswith("Flow") for e in q.elements[:first_flow])
        assert all(short_type(e).endswith("Flow") for e in q.elements[first_flow:])
        assert "ConditionalSequenceFlow3" in names
        assert q.element("ConditionalSequenceFlow3")["CI4"] == 2
        assert "{Parameter:Counter} > 10" == q.decode_expr(q.element("ConditionalSequenceFlow3")["CI3"])
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
        assert '"Caption": "Demo"' in q.descriptor_text and "\\/Date(" in q.descriptor_text

        q.rename_element("Compute", "AddFortyOne")
        assert q.resources.get("BaseElements.AddFortyOne.Caption") == "Add 41"
        q.remove_element("Big")
        assert "ConditionalSequenceFlow3" not in [e["A2"] for e in q.elements]
        assert q.validate() == []

        report = rename_schema(pkg, "iaDemo_Process", "iaRenamed_Process", apply=True)
        assert any("Schemas\\iaDemo_Process -> Schemas\\iaRenamed_Process" in r.replace("/", "\\") for r in report)
        r = Process(pkg, "iaRenamed_Process")
        assert r.uid == q.uid and r.name == "iaRenamed_Process"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_every_element_kind_builds_and_validates():
    tmp = Path(tempfile.mkdtemp())
    try:
        pkg = tmp / "iaTest"
        shutil.copytree(FIXTURES, pkg)
        p = create_process(pkg, "iaAll_Process", "All kinds")
        p.add_param("Counter", "Integer", "Variable", "Counter", 1)
        prev = "StartEvent1"
        for i, kind in enumerate(k for k in ELEMENT_TYPES if k != "userTask"):
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
        q = Process(pkg, "iaAll_Process")
        assert q.validate() == [], q.validate()
        assert len(q.nodes()) == 2 + len(ELEMENT_TYPES) - 1 + len(USER_TASKS) + len(TASK_ALIASES)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
