"""Checks for the push command, without an environment."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

from creatio_schemas import Clio, ProcessSchema  # noqa: E402
from creatio_schemas.push import push  # noqa: E402

SQL = 'update "SysSchema" set "IsChanged"=false'
SUMMARY = "Finished building project: Succeeded: True. Errors: 0. Warnings: 0."


class FakeClio:
    def __init__(self, env="dev", summary=SUMMARY):
        self.env = env
        self.summary = summary
        self.calls = []

    def execute_sql(self, sql):
        self.run(["execute-sql-script", sql, "-e", self.env])

    def run(self, args, cwd=None):
        self.calls.append((args, cwd))
        return self.summary if args[0] == "last-compilation-log" else "done"


def package(root):
    pkg = root / "UsrPkg"
    pkg.mkdir()
    (pkg / "descriptor.json").write_text(json.dumps({"Descriptor": {
        "Name": "UsrPkg", "UId": "00000000-0000-0000-0000-000000000001"
    }}), encoding="utf-8")
    return pkg


def add_process(pkg):
    proc = ProcessSchema.create(pkg, "UsrProcess", "Process")
    proc.add_element("script", "Script", "Script", after="StartEvent1", before="TerminateEvent1")
    proc.save()


def test_sequence_and_publish():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        add_process(pkg)
        fake, logs = FakeClio(), []
        assert push(pkg, "dev", fake, log=logs.append) == 0
        assert fake.calls == [
            (["execute-sql-script", SQL, "-e", "dev"], None),
            (["push-pkg", "UsrPkg", "-e", "dev"], pkg.parent),
            (["last-compilation-log", "-e", "dev"], None),
            (["compile-configuration", "-e", "dev"], None),
        ]
        assert "publish: started" in logs


def test_publish_on_process_fixture_copy():
    fixtures = HERE.parent.parent / "process" / "tests" / "fixtures"
    source = next(p for p in fixtures.iterdir() if (p / "descriptor.json").is_file())
    with tempfile.TemporaryDirectory() as tmp:
        pkg = Path(tmp) / "UsrPkg"
        shutil.copytree(source, pkg)
        add_process(pkg)
        fake = FakeClio()
        assert push(pkg, "dev", fake, log=lambda line: None) == 0
        assert fake.calls[-1][0] == ["compile-configuration", "-e", "dev"]


def test_compilation_failure_stops():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        add_process(pkg)
        fake, logs = FakeClio(summary="Finished building project: Succeeded: False. Errors: 2. Warnings: 0."), []
        assert push(pkg, "dev", fake, log=logs.append) == 1
        assert [args[0] for args, _ in fake.calls] == ["execute-sql-script", "push-pkg", "last-compilation-log"]
        assert any("FAILED" in line and "Errors: 2" in line for line in logs)


def test_missing_summary_and_no_publish():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        fake, logs = FakeClio(), []
        assert push(pkg, "dev", fake, log=logs.append) == 0
        assert len(fake.calls) == 3 and "publish: not needed" in logs
        fake, logs = FakeClio(summary="unexpected"), []
        assert push(pkg, "dev", fake, log=logs.append) == 1
        assert any("summary not found" in line for line in logs)


def test_dry_run_and_non_process_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        entity = pkg / "Schemas" / "UsrEntity"
        entity.mkdir(parents=True)
        (entity / "descriptor.json").write_text(json.dumps({"Descriptor": {"ManagerName": "EntitySchemaManager"}}))
        (entity / "metadata.json").write_text("ProcessSchemaScriptTask")
        fake, logs = FakeClio(), []
        assert push(pkg, "dev", fake, dry_run=True, log=logs.append) == 0
        assert "publish: not needed" in logs
        add_process(pkg)
        logs.clear()
        assert push(pkg, "dev", fake, dry_run=True, log=logs.append) == 0
        assert not fake.calls
        for cmd in ("execute-sql-script", "push-pkg", "last-compilation-log", "compile-configuration"):
            assert any("clio " + cmd in line and "-e dev" in line for line in logs)


def test_clio_run_and_sql_errors():
    clio = Clio("dev")
    with patch("creatio_schemas.clio.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "ok", "")) as run:
        clio.execute_sql(SQL)
        assert run.call_args.args[0] == ["clio", "execute-sql-script", SQL, "-e", "dev"]
    for code, output in ((1, "failed"), (0, "[ERR] failed")):
        with patch("creatio_schemas.clio.subprocess.run", return_value=subprocess.CompletedProcess([], code, output, "")):
            try:
                clio.execute_sql(SQL)
                assert False, "expected RuntimeError"
            except RuntimeError as e:
                assert "failed" in str(e)


def test_probes_select_items_and_surface_failures():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        for name, manager in (("UsrEntity", "EntitySchemaManager"), ("UsrOther", "ClientUnitSchemaManager")):
            path = pkg / "Schemas" / name
            path.mkdir(parents=True)
            (path / "descriptor.json").write_text(json.dumps({"Descriptor": {"ManagerName": manager}}))
        script = pkg / "SqlScripts" / "UsrScript"
        script.mkdir(parents=True)
        (script / "descriptor.json").write_text("{}")
        fake, logs = FakeClio(), []
        with patch("creatio_schemas.push.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "probe result\n", "")) as run:
            assert push(pkg, "dev", fake, probe=True, log=logs.append) == 0
            calls = [call.args[0] for call in run.call_args_list]
            assert len(calls) == 2
            assert [c[4] for c in calls] == ["UsrEntity", "UsrScript"]
            assert all(c[2:4] == ["probe", str(pkg)] and c[5:] == ["--env", "dev"] for c in calls)
            assert sum("probe result" in line for line in logs) == 2
        with patch("creatio_schemas.push.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "bad probe")):
            logs.clear()
            assert push(pkg, "dev", FakeClio(), probe=True, log=logs.append) == 1
            assert any("FAILED" in line and "bad probe" in line for line in logs)
        with patch("creatio_schemas.push.subprocess.run") as run:
            logs.clear()
            assert push(pkg, "dev", FakeClio(), probe=True, dry_run=True, log=logs.append) == 0
            assert not run.called and any("UsrEntity" in line for line in logs)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
