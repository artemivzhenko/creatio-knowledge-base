"""Checks project synchronization and setup without real credentials or registration."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


project = load("project_tools", ROOT / "no-code" / "tools" / "project.py")
setup = load("agent_setup", ROOT / "agent_setup.py")


def test_sync_example_and_preserves_unmanaged_settings():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "project.json"
        shutil.copyfile(ROOT / "skill" / "creatio-loop" / "templates" / "project.example.json", source)
        config_dir = root / "framework" / "Configuration"
        config_dir.mkdir(parents=True)
        target = config_dir / "creatio.env.config.json"
        target.write_text('{"BaseUrl":"old", // keep settings\n "CasesFolders":["custom",], "AnalysisFolders":["analysis"],}', encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert project.main(["sync", str(source), "--framework", str(config_dir.parent)]) == 0
        data = json.loads(target.read_text(encoding="utf-8"))
        assert data["BaseUrl"] == "https://dev.example.com"
        assert data["Users"] == [{"Username": "Supervisor", "Password": "change-me"}]
        assert data["CasesFolders"] == ["custom"] and data["AnalysisFolders"] == ["analysis"]
        assert "change-me" not in out.getvalue() and "Users" in out.getvalue()
        assert project.sync(source, config_dir.parent) == []


def test_new_config_and_missing_environment():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "framework" / "Configuration").mkdir(parents=True)
        source = root / "project.json"
        source.write_text(json.dumps({"environment": {"url": "https://example.test", "login": "x", "password": "y"},
                                      "paths": {"testFramework": "framework"}}), encoding="utf-8")
        assert project.sync(source) == ["BaseUrl", "Users", "CasesFolders"]
        target = root / "framework" / "Configuration" / "creatio.env.config.json"
        assert json.loads(target.read_text(encoding="utf-8"))["CasesFolders"] == ["./Cases"]
        before = target.read_bytes()
        source.write_text("{}", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            assert project.main(["sync", str(source)]) == 1
        assert target.read_bytes() == before


def test_launcher_falls_back_to_py_and_check_is_read_only():
    def run(cmd, **kwargs):
        if cmd[0] == "python":
            return subprocess.CompletedProcess(cmd, 9009, "", "Install Python from the Microsoft Store")
        return subprocess.CompletedProcess(cmd, 0, "3.12.1\n", "")
    with patch.object(setup.subprocess, "run", side_effect=run), \
         patch.object(setup, "find_claude", side_effect=AssertionError("check must not register")), \
         patch.object(setup.sys, "argv", ["agent_setup.py", "--check"]), \
         contextlib.redirect_stdout(io.StringIO()) as out:
        setup.main()
    assert "Selected Python launcher: py -3" in out.getvalue()
    assert "MCP_TIMEOUT=120000" in out.getvalue()


def test_no_working_launcher_stops_before_registration():
    with patch.object(setup.subprocess, "run", side_effect=FileNotFoundError("missing")), \
         patch.object(setup, "find_claude", side_effect=AssertionError("must not register")), \
         contextlib.redirect_stdout(io.StringIO()):
        try:
            setup.main()
        except SystemExit as exc:
            assert "Neither python nor py -3 works" in str(exc)
        else:
            raise AssertionError("a working launcher is required")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
