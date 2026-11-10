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
    pages = TOOLS / "pages" / "tests" / "fixtures" / "iaTest"
    out = server.schema_deps(str(pages), "iaOrder", "in", kind="page")
    assert out.splitlines()[:3] == ["iaOrder  object in iaTest", "dependents:", "  page iaOrder_FormPage  data-source: PDS  [name]"], out
    assert "  object iaOrderStatus  lookup: iaStatus" in server.schema_deps(str(pages), "iaOrder", "out", via="lookup")
    assert server.schema_deps(str(pages), "Nope").startswith("no schema named Nope")


def test_schema_impact_ends_with_the_exit_code():
    pages = TOOLS / "pages" / "tests" / "fixtures" / "iaTest"
    out = server.schema_impact(str(pages), "iaOrderStatus, iaOrder", md=True)
    assert out.startswith("## Impact") and "affects: iaOrder_FormPage, iaTests_FormPage" in out and out.endswith("exit code 0"), out
    assert server.schema_impact(str(pages), " ") == "error: name at least one schema"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
