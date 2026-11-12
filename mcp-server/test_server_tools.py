"""MCP push tool checks with a temporary fixture and no environment."""

import importlib
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import server

TOOLS = Path(__file__).resolve().parent.parent / "no-code" / "tools"
sys.path.insert(0, str(TOOLS / "push" / "tests"))
from test_push_tools import FakeClio, add_process  # noqa: E402

push_module = importlib.import_module("creatio_schemas.push")


def test_dry_run_uses_the_library_without_starting_processes():
    source = next(p for p in (TOOLS / "process" / "tests" / "fixtures").iterdir()
                  if (p / "descriptor.json").is_file())
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "UsrPkg"
        shutil.copytree(source, pkg)
        add_process(pkg)
        fake = FakeClio()
        with patch.object(push_module, "Clio", return_value=fake), \
             patch.object(push_module.subprocess, "run", side_effect=AssertionError("dry run started a process")):
            output = server.push_package(str(pkg), "dev", dry_run=True)
        assert not fake.calls
        for cmd in ("execute-sql-script", "push-pkg", "last-compilation-log", "compile-configuration"):
            assert "clio " + cmd in output, output
        assert output.endswith("exit code 0"), output


def test_invalid_arguments_are_refused_before_calling_clio():
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(push_module, "Clio", side_effect=AssertionError("Clio must not start")):
            assert server.push_package(tmp, "dev").startswith("error:")
            (Path(tmp) / "descriptor.json").write_text("{}", encoding="utf-8")
            assert server.push_package(tmp, "  ").startswith("error:")


def test_v2_options_are_forwarded_and_failure_reason_survives():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp)
        (pkg / "descriptor.json").write_text("{}", encoding="utf-8")
        def fake_push(package, env, clio, probe, dry_run, log, **kwargs):
            assert package == pkg and env == "dev" and probe and dry_run
            assert kwargs == {
                "project": Path("project.json"), "tasks": Path("tasks"), "task": Path("tasks/UsrTask"),
                "force": True, "baseline": Path("baseline.txt"), "skip_drift": True,
                "skip_foreign_files": True, "skip_sql_dates": True, "skip_compile_package": True,
            }
            log("push FAILED at compilation: new errors")
            return 1
        with patch.object(push_module, "Clio", return_value=FakeClio()), patch.object(push_module, "push", side_effect=fake_push):
            output = server.push_package(str(pkg), "dev", True, True, "project.json", "tasks", "tasks/UsrTask",
                                         True, "baseline.txt", True, True, True, True)
        assert "new errors" in output and output.endswith("exit code 1")


def test_raised_failure_keeps_prior_log_and_error():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp)
        (pkg / "descriptor.json").write_text("{}", encoding="utf-8")
        def fake_push(*args, log, **kwargs):
            log("step started")
            raise RuntimeError("specific failure")
        with patch.object(push_module, "Clio", return_value=FakeClio()), patch.object(push_module, "push", side_effect=fake_push):
            output = server.push_package(str(pkg), "dev")
        assert "step started" in output and "error: specific failure" in output
        assert output.endswith("exit code 2")


env_module = importlib.import_module("creatio_schemas.environment")


class FakeEnv:
    clio_name, url = "dev", "https://site.example/"

    def __init__(self):
        self.calls = []

    def sql(self, text):
        self.calls.append(("sql", text))
        if "boom" in text:
            raise RuntimeError("sql: [ERR] relation does not exist")
        return [{"Name": "UsrOrder", "ModifiedOn": "2026-11-10"}, {"Name": "Ünïcode", "ModifiedOn": None}]

    def request(self, method, path, body=None, params=None):
        self.calls.append((method, path, body))
        return env_module.Response(200, '{"d": 1}') if path.startswith("rest/") else env_module.Response(500, "<html>fault</html>")

    def odata(self, entity, select=None, filter=None, top=None, orderby=None, skip=None, expand=None):
        self.calls.append((entity, select, filter, top))
        return [{"Id": "1", "Name": "A"}]


def test_env_tools_use_the_environment_layer():
    fake = FakeEnv()
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: fake)):
        assert server.env_sql("dev", 'select 1').splitlines() == ['{"Name": "UsrOrder", "ModifiedOn": "2026-11-10"}', '{"Name": "Ünïcode", "ModifiedOn": null}']
        assert server.env_sql("dev", "select boom").startswith("error: sql: [ERR]")
        assert "1 more" in server.env_sql("dev", "select 1", limit=1)
        assert server.env_call("dev", "post", "/rest/UsrSvc/Ping", '{"a": 1}') == 'status: 200\n{\n  "d": 1\n}'
        assert fake.calls[-1] == ("POST", "rest/UsrSvc/Ping", {"a": 1})
        assert server.env_call("dev", "GET", "ServiceModel/X.svc/Y").startswith("error: 500:")
        assert server.env_call("dev", "GET", "rest/x", "{not json").startswith("error:")
        assert server.env_odata("dev", "Contact", "Id, Name", "Name eq 'A'", 5) == '{"Id": "1", "Name": "A"}'
        assert fake.calls[-1] == ("Contact", ["Id", "Name"], "Name eq 'A'", 5)
    assert server.env_sql(" ", "select 1").startswith("error: env must be")


def test_schema_layers_reads_custom_layer_from_project():
    import json
    rows = [{"package": "Base", "extendParent": "false", "sl": "0", "pl": "0", "body": "", "size": 10, "md5": "a" * 32},
            {"package": "UsrCustom", "extendParent": "true", "sl": "1", "pl": "1", "body": "", "size": 5, "md5": "b" * 32}]
    fake = FakeEnv()
    fake.sql = lambda text: rows
    with tempfile.TemporaryDirectory() as tmp, patch.object(env_module, "open_environment", lambda env, project, **kw: fake):
        project = Path(tmp) / "project.json"
        project.write_text(json.dumps({"environment": {"customLayer": "UsrCustom"}}), encoding="utf-8")
        text = server.schema_layers(str(project), "UsrOrderPage")
        assert text.startswith("UsrOrderPage on dev: 2 copies") and text.endswith("Custom layer present: UsrCustom"), text
        assert "Custom layer present" not in server.schema_layers("dev", "UsrOrderPage"), "the default customisation package is Custom"
    with patch.object(env_module, "open_environment", lambda env, project, **kw: (_ for _ in ()).throw(ValueError("no such environment"))):
        assert server.schema_layers("nope", "X") == "error: no such environment"


def test_schema_deps_answers_from_the_fixture_index():
    pages = TOOLS / "pages" / "tests" / "fixtures" / "UsrPkg"
    out = server.schema_deps(str(pages), "UsrOrder", "in", kind="page")
    assert out.splitlines()[:3] == ["UsrOrder  object in UsrPkg", "dependents:", "  page UsrOrder_FormPage  data-source: PDS  [name]"], out
    assert "  object UsrOrderStatus  lookup: UsrStatus" in server.schema_deps(str(pages), "UsrOrder", "out", via="lookup")
    assert server.schema_deps(str(pages), "Nope").startswith("no schema named Nope")


def test_schema_impact_ends_with_the_exit_code():
    pages = TOOLS / "pages" / "tests" / "fixtures" / "UsrPkg"
    out = server.schema_impact(str(pages), "UsrOrderStatus, UsrOrder", md=True)
    assert out.startswith("## Impact") and "affects: UsrOrder_FormPage, UsrTests_FormPage" in out and out.endswith("exit code 0"), out
    assert server.schema_impact(str(pages), " ") == "error: name at least one schema"


def test_merge_plan_prints_and_writes_nothing():
    import json
    import shutil
    import tempfile
    root = Path(tempfile.mkdtemp())
    try:
        for name, deps in (("UsrA", []), ("UsrB", ["UsrA"])):
            folder = root / "packages" / name / "Schemas" / "Contact"
            folder.mkdir(parents=True)
            (root / "packages" / name / "descriptor.json").write_text(json.dumps({"Descriptor": {"UId": f"pkg-{name}", "Name": name, "DependsOn": [{"Name": d} for d in deps]}}), encoding="utf-8")
            (folder / "descriptor.json").write_text(json.dumps({"Descriptor": {"UId": f"uid-{name}", "Name": "Contact", "ExtendParent": True,
                                                                                "ManagerName": "EntitySchemaManager"}}), encoding="utf-8")
            (folder / "metadata.json").write_text(f'= MetaData.Schema.UId "uid-{name}"\r\n', encoding="utf-8")
        before = sorted(p.relative_to(root) for p in root.rglob("*"))
        out = server.merge_plan(str(root))
        assert out.splitlines()[0] == "Contact object: 2 layers, target UsrA" and out.endswith("1 schemas, 1 layers to remove, 0 conflicts\nexit code 0"), out
        assert sorted(p.relative_to(root) for p in root.rglob("*")) == before
        assert server.merge_plan(str(root / "nowhere")).startswith("error: ")
        out = server.merge_layers(str(root), "Contact")
        assert "delete packages/UsrB/Schemas/Contact" in out and out.endswith("(dry run; --apply writes)\nexit code 0"), out
        assert sorted(p.relative_to(root) for p in root.rglob("*")) == before  # printed, never written
    finally:
        shutil.rmtree(root, ignore_errors=True)




def test_schema_diff_compares_a_folder_without_git():
    from creatio_schemas.entity import EntitySchema

    source = TOOLS / "objects" / "tests" / "fixtures" / "UsrPkg"
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "UsrPkg"
        shutil.copytree(source, pkg)
        entity = EntitySchema(pkg, "UsrOrder")
        entity.add_column("UsrWeight", "Float", "Weight")
        entity.save()
        text = server.schema_diff(str(pkg), "UsrOrder", str(source))
        assert text.splitlines()[0] == "UsrOrder  object" and "+ UsrWeight Float 'Weight'" in text
        assert server.schema_diff(str(pkg), "UsrNoSuch", str(source)).startswith("error: ")


class ScriptedEnv:
    """sql() answers with the rows of the first needle (longest first) the statement contains."""

    clio_name, url = "dev", "https://site.example/"

    def __init__(self, answers):
        self.answers = answers

    def sql(self, text):
        for needle in sorted(self.answers, key=len, reverse=True):
            if needle in text:
                return self.answers[needle]
        raise RuntimeError("sql: 42P01: nothing scripted")


def test_forensics_tools_answer_from_the_database():
    uid = "11111111-1111-1111-1111-111111111111"
    person = "22222222-2222-2222-2222-222222222222"
    role = [{"Id": person, "Name": "UsrManagers", "SysAdminUnitTypeValue": 6}]
    user = [{"Id": uid, "login": "ivan", "contact": "Ivan P"}]
    fake = ScriptedEnv({
        "information_schema.columns": [{"schema": "public", "table": "UsrOrder"}], 'where "Id" =': [{"schema": "public", "table": "UsrOrder"}],
        'select * from "': [{"Id": uid, "Name": "Order 7", "CreatedOn": "2026-11-10T22:30:00Z", "CreatedById": person}],
        'from "Contact" where "Id" in': [{"Id": person, "Name": "Ivan"}], "kcu.table_name": [], "ccu.table_name": [],
        "where \"Name\" = 'UsrManagers'": role, 'm."Name" as "member"': [{"id": uid, "member": "ivan", "contact": "Ivan P", "kind": 4}],
        'u."SysAdminUnitTypeValue" = 4': user, 'r."Name" as "role"': [{"id": person, "role": "UsrManagers", "kind": 6}],
        '"ParentRoleId", "SysAdminUnitTypeValue" from "SysAdminUnit"': [{"Id": person, "Name": "UsrManagers", "ParentRoleId": None, "SysAdminUnitTypeValue": 6}],
        'from "SysFuncRoleInOrgRole"': [], 'from "SysUserInRole" where': [{"SysUserId": uid, "SysRoleId": person}],
        'select "SysAdminUnitId" as "id"': [], 'from "SysSettings" where "Code"': [{"Id": uid, "Name": "Max", "ValueTypeName": "Integer", "ReferenceSchemaUId": None}],
        'from "SysSettingsValue" where': [{"IntegerValue": 5, "SysAdminUnitId": None}]})
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: fake)):
        found = server.find_record("dev", uid, "UsrOrder", time_zone="+03:00")
        assert found.startswith("UsrOrder  Name = Order 7\n  created  2026-11-10 22:30:00 UTC (01:30 +03:00) 11.11 by Ivan"), found
        assert server.record_context("dev", "UsrOrder", uid, depth=1).startswith(f"UsrOrder {uid}\n  Id = {uid}\n  Name = Order 7")
        assert server.role_members("dev", "UsrManagers") == "Ivan P  [user]  direct  login ivan"
        assert server.user_roles("dev", "ivan") == "UsrManagers  [functional role]  direct"
        assert server.role_diff("dev", "UsrManagers", "ivan") == "in UsrManagers: -\nnot in UsrManagers: ivan\nexit code 1"
        setting = server.sys_setting("UsrMax", "dev")
        assert "dev: Max [Integer]" in setting and "for all: '5'" in setting
        assert server.find_record("dev", "nope").startswith("error: ")
    fake.answers["where \"Name\" = 'UsrManagers'"] = []
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: fake)):
        assert server.role_members("dev", "UsrManagers") == "error: no role named 'UsrManagers' (SysAdminUnit.Name)"


def test_snapshot_tools_write_and_compare_evidence(tmp_path=None):
    import tempfile
    cols = [{"column": "Id", "type": "uuid", "length": None, "nullable": "NO"}, {"column": "UsrNote", "type": "text", "length": None, "nullable": "YES"}]
    layer = [{"package": "UsrLayer", "extendParent": "true", "sl": "1", "pl": "1"}]

    def fake(note):
        return ScriptedEnv({"information_schema.columns": cols, "count(*)": [{"n": 3}], "md5(string_agg": [{"c0": note}], 'from "SysSchema" s': layer})
    folder = Path(tempfile.mkdtemp())
    before, after = str(folder / "before.txt"), str(folder / "after.txt")
    for out, note in ((before, "aaa"), (after, "bbb")):
        with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: fake(note))):
            assert "rows 3" in server.schema_snapshot("UsrObj", "dev", out=out)
    assert server.snapshot_compare(before, before) == "same"
    assert server.snapshot_compare(before, after) == "~ checksum  UsrNote aaa -> UsrNote bbb\nexit code 1"
    assert server.snapshot_compare(before, str(folder / "none.txt")).startswith("error: ")


class ProcessEnv(ScriptedEnv):
    """ScriptedEnv that also starts processes: `success` and `processId` as the engine would answer."""

    def __init__(self, answers, success=True, process_id="44444444-4444-4444-4444-444444444444"):
        super().__init__(answers)
        self.success, self.process_id, self.started = success, process_id, []

    def run_process(self, name, params=None, results=None):
        self.started.append((name, params, results))
        return {"process": name, "processId": self.process_id if self.success else "", "success": self.success,
                "error": None if self.success else "Schema not found", "results": {"Total": 42}}

    def process_log(self, process_id, zone=None):
        from creatio_schemas.runs import process_log
        return process_log(self, process_id, zone)


def test_process_tools_run_and_read_the_log():
    run = "44444444-4444-4444-4444-444444444444"
    row = {"Id": run, "Name": "Order", "Status": "Error", "ErrorDescription": "Expression expected\n   at Terrasoft.X()",
           "StartDate": "2026-11-11T08:00:05", "CompleteDate": None, "OwnerId": None, "Process": "UsrOrder_Process"}
    element = {"Caption": "Read order", "Status": "Error", "ErrorDescription": None, "StartDate": "2026-11-11T08:00:06", "CompleteDate": None}
    fake = ProcessEnv({'from "SysProcessLog" l': [row], 'from "SysProcessElementLog" e': [element], 'from "Contact" where "Id" in': []})
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: fake)):
        answer = server.run_process("dev", "UsrOrder_Process", '{"OrderId": "o-1", "Qty": 3}', "Total")
        assert fake.started[-1] == ("UsrOrder_Process", {"OrderId": "o-1", "Qty": 3}, ["Total"])
        assert answer.splitlines()[0] == f"UsrOrder_Process: ok  processId {run}" and "  Total = 42" in answer, answer
        assert "log: Error (failed)" in answer and "error: Expression expected" in answer and answer.endswith("exit code 1"), answer
        fake.answers['from "SysProcessLog" l'] = [dict(row, Status="Completed", ErrorDescription=None, CompleteDate="2026-11-11T08:00:09")]
        assert server.run_process("dev", "UsrOrder_Process").endswith("exit code 0")
        assert server.run_process("dev", "UsrOrder_Process", "[1]").startswith("error: params: params must be a JSON object")
        assert server.run_process("dev", "UsrOrder_Process", "{bad").startswith("error: params:")
        fake.answers['from "SysProcessLog" l'] = [row]
        listed = server.process_runs("dev", process="UsrOrder_Process", time_zone="+03:00")
        assert listed.startswith("2026-11-11 08:00:05 UTC (11:00 +03:00)  UsrOrder_Process  Error (failed)  " + run), listed
        assert server.process_runs("dev", record="UsrOrder:x").startswith("error: 'x' is not an Id")
        error = server.process_error("dev", run)
        assert "stopped on: Read order (Error" in error and error.splitlines()[-1] == "Expression expected", error
    tests = ProcessEnv({'from "SysPackage" p': [{"changed": "2026-11-11T09:00:00", "compiled": "2026-11-11T08:00:00"}]})
    tests.call_service = lambda path, body=None, method="POST": env_module.Response(200, '[{"Name": "T1", "Success": true}, {"Name": "T2", "Success": false, "Message": "expected 3"}]')
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: tests)):
        assert server.run_tests("dev", category="UsrOrders") == "error: no in-Creatio test runner configured: set project.json tests.runner or pass --runner\nexit code 2"
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project.json"
        project.write_text('{"environment": {"clioName": "dev", "url": "https://p.example"}, "tests": {"runner": "rest/UsrTests/Run", "package": "UsrTests"}}', encoding="utf-8")
        with patch.object(env_module.Environment, "from_project", classmethod(lambda cls, path, **kw: tests)):
            answer = server.run_tests(project=str(project), test="UsrOrderTest")
        assert answer.splitlines() == ["FAIL  T2  - expected 3", "ok    T1", "1 passed, 1 failed",
                                       "warning: the test package's dll is older than its last push (UsrTests changed 2026-11-11T09:00:00, compiled 2026-11-11T08:00:00)",
                                       "exit code 1"], answer
    assert server.run_tests("dev").startswith("error: give category or test")
    with tempfile.TemporaryDirectory() as tmp:  # the git tools answer an error line, never a traceback
        assert server.review_download(tmp).startswith("error: ") and "no descriptor.json" in server.review_download(tmp)
        assert server.precommit_check(str(Path(tmp) / "none")).startswith("error: ")
    refused = ProcessEnv({}, success=False)
    with patch.object(env_module.Environment, "from_clio", staticmethod(lambda name, **kw: refused)):
        assert server.run_process("dev", "UsrMissing") == "UsrMissing: FAILED Schema not found  processId -\nexit code 1"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
