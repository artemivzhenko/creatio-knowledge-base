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
        self.rows = []

    def execute_sql(self, sql):
        self.run(["execute-sql-script", sql, "-e", self.env])

    def execute_sql_rows(self, sql):
        self.calls.append((["sql-rows", sql], None))
        return self.rows

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
            assert push(pkg, "dev", fake, probe=True, log=logs.append, skip_drift=True, skip_sql_dates=True) == 0
            calls = [call.args[0] for call in run.call_args_list]
            assert len(calls) == 2
            assert [c[4] for c in calls] == ["UsrEntity", "UsrScript"]
            assert all(c[2:4] == ["probe", str(pkg)] and c[5:] == ["--env", "dev"] for c in calls)
            assert sum("probe result" in line for line in logs) == 2
        with patch("creatio_schemas.push.subprocess.run", return_value=subprocess.CompletedProcess([], 1, "", "bad probe")):
            logs.clear()
            assert push(pkg, "dev", FakeClio(), probe=True, log=logs.append, skip_drift=True, skip_sql_dates=True) == 1
            assert any("FAILED" in line and "bad probe" in line for line in logs)
        with patch("creatio_schemas.push.subprocess.run") as run:
            logs.clear()
            assert push(pkg, "dev", FakeClio(), probe=True, dry_run=True, log=logs.append) == 0
            assert not run.called and any("UsrEntity" in line for line in logs)


def fake_git(root, status=""):
    def run(package_path, args, allow_not_repo=False):
        if args[:2] == ["rev-parse", "--show-toplevel"]:
            return str(root)
        if args[0] == "log":
            return "2026-01-02T03:04:05+00:00\n"
        if args[0] == "status":
            return status
        raise AssertionError(args)
    return run


def test_drift_and_foreign_task_stop_before_push():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = package(root)
        tasks = root / "tasks"
        current, other = tasks / "UsrCurrent", tasks / "UsrOther"
        current.mkdir(parents=True)
        other.mkdir()
        (current / "schemas.json").write_text(json.dumps({"schemas": ["UsrMine"]}))
        (other / "schemas.json").write_text(json.dumps({"schemas": ["UsrOther"], "files": ["Files/cs/UsrOther.cs"]}))
        project = root / "project.json"
        project.write_text(json.dumps({"paths": {"tasks": "tasks"}}))
        fake, logs = FakeClio(), []
        fake.rows = [{"Name": "UsrDrift"}]
        with patch("creatio_schemas.push._git", side_effect=fake_git(root)):
            assert push(pkg, "dev", fake, log=logs.append) == 1
        assert fake.calls[0][0][0] == "sql-rows" and "2026-01-02T03:04:05+00:00" in fake.calls[0][0][1]
        assert '"PackageUId"' in fake.calls[0][0][1] and any("UsrDrift" in line for line in logs)
        status = " M UsrPkg/Schemas/UsrOther/metadata.json\0"
        logs.clear()
        with patch("creatio_schemas.push._git", side_effect=fake_git(root, status)):
            assert push(pkg, "dev", fake, log=logs.append, force=True, project=project, task=current) == 1
        assert any("foreign files: FAILED UsrOther:" in line for line in logs)
        assert not any(args[0] == "push-pkg" for args, _ in fake.calls)
        logs.clear()
        with patch("creatio_schemas.push._git", side_effect=fake_git(root, status)):
            assert push(pkg, "dev", FakeClio(), log=logs.append, project=project) == 1
        assert any("--task is required" in line for line in logs)


def test_sql_date_and_assembly_compile():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = package(root)
        desc = pkg / "descriptor.json"
        package_data = json.loads(desc.read_text())
        package_data["Descriptor"]["Type"] = 1
        desc.write_text(json.dumps(package_data))
        script = pkg / "SqlScripts" / "UsrScript"
        script.mkdir(parents=True)
        descriptor = script / "descriptor.json"
        descriptor.write_bytes(b'\xef\xbb\xbf' + b'{\r\n  "SqlScript": {"ModifiedOnUtc": "\\/Date(1)\\/"}\r\n}')
        before = descriptor.read_bytes()
        status = " M UsrPkg/SqlScripts/UsrScript/UsrScript.sql\0"
        fake, logs = FakeClio(), []
        with patch("creatio_schemas.push._git", side_effect=fake_git(root, status)):
            assert push(pkg, "dev", fake, log=logs.append) == 0
        after = descriptor.read_bytes()
        assert after.startswith(b'\xef\xbb\xbf') and b'\r\n' in after and after != before
        assert "UsrScript" in next(line for line in logs if line.startswith("sql dates:"))
        assert any(args == ["compile-package", "UsrPkg", "-e", "dev", "--wait"] for args, _ in fake.calls)


def test_baseline_accepts_old_errors_and_rejects_new():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = package(root)
        desc = pkg / "descriptor.json"
        data = json.loads(desc.read_text())
        data["Descriptor"]["Type"] = 1
        desc.write_text(json.dumps(data))
        baseline = root / "evidence" / "baseline.txt"
        summary = "Finished building project: Succeeded: False. Errors: 1. Warnings: 0."
        old = "UsrOther.cs(1,1): error CS1000: old error"
        fake = FakeClio(summary=f"{old}\n{summary}")
        assert push(pkg, "dev", fake, baseline=baseline, skip_drift=True, skip_sql_dates=True, log=lambda _: None) == 0
        assert baseline.read_text().splitlines() == [old]
        assert push(pkg, "dev", FakeClio(summary=f"{old}\n{summary}"), baseline=baseline, skip_drift=True,
                    skip_sql_dates=True, log=lambda _: None) == 0
        logs = []
        result = push(pkg, "dev", FakeClio(summary=f"UsrNew.cs: error CS1001: new error\n{summary}"),
                      baseline=baseline, skip_drift=True, skip_sql_dates=True, log=logs.append)
        assert result == 1 and any("new error" in line for line in logs)
        assert baseline.read_text().splitlines() == [old]


def test_dry_run_never_executes_git_or_clio():
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        logs, fake = [], FakeClio()
        with patch("creatio_schemas.push.subprocess.run", side_effect=AssertionError("unexpected process")):
            assert push(pkg, "dev", fake, dry_run=True, log=logs.append, baseline=Path(tmp) / "baseline") == 0
        assert not fake.calls and any("git log" in line for line in logs)
        assert any("git status" in line for line in logs) and not (Path(tmp) / "baseline").exists()


def test_task_ownership_includes_files_and_ignores_completed_tasks():
    from creatio_schemas.push import _task_conflicts
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        current, other = root / "UsrCurrent", root / "UsrOther"
        current.mkdir()
        other.mkdir()
        (current / "schemas.json").write_text(json.dumps({"schemas": ["UsrMine"]}))
        (other / "schemas.json").write_text(json.dumps({"schemas": ["UsrForeign"], "files": ["Files/cs/UsrOther.cs"]}))
        changed = ["Schemas/UsrMine/metadata.json", "Resources/UsrForeign.Entity/resource.en-US.xml", "Files/cs/UsrOther.cs"]
        conflicts = _task_conflicts(root, current, changed)
        assert len(conflicts) == 1 and "UsrForeign.Entity" in conflicts[0] and "UsrOther.cs" in conflicts[0]
        assert "UsrMine" not in conflicts[0]
        (other / "success-report.md").write_text("done")
        assert _task_conflicts(root, current, changed) == []


def test_git_status_renames_and_git_failures():
    from creatio_schemas.push import _changed_files, _git
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = package(root)
        status = "R  UsrPkg/Schemas/UsrNew/metadata.json\0UsrPkg/Schemas/UsrOld/metadata.json\0"
        with patch("creatio_schemas.push._git", side_effect=fake_git(root, status)):
            assert _changed_files(pkg) == ["Schemas/UsrNew/metadata.json", "Schemas/UsrOld/metadata.json"]
        with patch("creatio_schemas.push.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 128, "", "fatal: permission denied")):
            try:
                _git(pkg, ["rev-parse", "--show-toplevel"], allow_not_repo=True)
                assert False, "expected git failure"
            except RuntimeError as exc:
                assert "permission denied" in str(exc)


def test_compile_failure_and_unreadable_baseline_errors_stop():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        pkg = package(root)
        desc = pkg / "descriptor.json"
        data = json.loads(desc.read_text())
        data["Descriptor"]["Type"] = 1
        desc.write_text(json.dumps(data))

        class BadCompile(FakeClio):
            def run(self, args, cwd=None):
                if args[0] == "compile-package":
                    raise RuntimeError("package compiler failed")
                return super().run(args, cwd)

        logs = []
        assert push(pkg, "dev", BadCompile(), skip_drift=True, skip_sql_dates=True, log=logs.append) == 1
        assert logs[-1] == "push FAILED at compile-package"
        baseline = root / "baseline.txt"
        logs.clear()
        summary = "Finished building project: Succeeded: False. Errors: 2. Warnings: 0."
        assert push(pkg, "dev", FakeClio(summary=summary), baseline=baseline, skip_drift=True,
                    skip_sql_dates=True, log=logs.append) == 1
        assert not baseline.exists() and logs[-1] == "push FAILED at baseline"


def test_future_sql_date_is_not_moved_backwards():
    from creatio_schemas.push import _touch_sql_dates
    with tempfile.TemporaryDirectory() as tmp:
        pkg = package(Path(tmp))
        script = pkg / "SqlScripts" / "UsrScript"
        script.mkdir(parents=True)
        descriptor = script / "descriptor.json"
        descriptor.write_bytes(b'{"SqlScript":{"ModifiedOnUtc":"\\/Date(9999999999999)\\/"}}')
        before = descriptor.read_bytes()
        try:
            _touch_sql_dates(pkg, ["SqlScripts/UsrScript/UsrScript.sql"])
            assert False, "expected timestamp failure"
        except RuntimeError as exc:
            assert "could not advance" in str(exc)
        assert descriptor.read_bytes() == before


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
