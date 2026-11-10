"""Checks for the package-wide resource tools:  python tests/test_resources_tools.py  (copies of the process and user-task fixtures)."""

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

from creatio_schemas.resources import Resources, package_resources  # noqa: E402
from resources import main  # noqa: E402

PROCESSES = TOOLS / "process" / "tests" / "fixtures" / "iaTest"
USER_TASK = TOOLS / "usertask" / "tests" / "fixtures" / "iaTest" / "Resources" / "iaRunCase_UserTask.ProcessUserTask"


def read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


@contextlib.contextmanager
def package():
    tmp = Path(tempfile.mkdtemp()) / "packages"
    shutil.copytree(PROCESSES, tmp / "iaTest")
    shutil.copytree(USER_TASK, tmp / "iaTest" / "Resources" / USER_TASK.name)
    try:
        yield tmp / "iaTest"
    finally:
        shutil.rmtree(tmp.parent, ignore_errors=True)


def run(*argv) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = main(list(argv))
    return code, out.getvalue()


def snapshot(pkg: Path) -> dict[Path, str]:
    return {p: read(p) for p in sorted((pkg / "Resources").rglob("*.xml"))}


def test_package_resources_finds_every_folder_and_kind():
    found = package_resources(PROCESSES)
    assert sorted(found) == ["iaDeleteOldLogs_Process", "iaProcess_0d4c445"] and {r.kind for r in found.values()} == {"Process"}
    assert package_resources(PROCESSES / "Schemas") == {} and Resources(USER_TASK).kind == "ProcessUserTask"
    for res in found.values():  # the class renders what it read
        for path, (text, _) in res.files().items():
            assert read(path) == "﻿" + text, path


def test_cultures_and_missing():
    with package() as pkg:
        code, out = run("cultures", str(pkg))
        assert code == 0 and "3 culture(s) over 3 schema(s): en-US, ru-RU, uk-UA" in out
        assert "1 schema(s) in en-US, ru-RU, uk-UA: iaProcess_0d4c445" in out and "1 schema(s) in en-US: iaRunCase_UserTask" in out
        code, out = run("missing", str(pkg), "--culture", "ru-RU", "--keys")
        assert code == 0 and "iaDeleteOldLogs_Process [Process]: ru-RU" in out and "(no file)" in out
        assert "      ru-RU: Caption" in out and "iaRunCase_UserTask [ProcessUserTask]: ru-RU" in out
        code, out = run("missing", str(pkg), "--kind", "user-task")
        assert "iaDeleteOldLogs_Process" not in out and "iaRunCase_UserTask" in out
        code, out = run("missing", str(pkg), "--from", "de-DE")
        assert "no de-DE" in out and out.strip().endswith("0 key(s) missing against de-DE")


def test_fill_copies_values_and_image_items_and_writes_only_changed_files():
    with package() as pkg:
        before = snapshot(pkg)
        code, out = run("fill", str(pkg), "--to", "ru-RU", "--schema", "iaRunCase_UserTask", "--dry-run")
        assert code == 0 and "would change" in out and "b/Resources/iaRunCase_UserTask.ProcessUserTask/resource.ru-RU.xml" in out
        assert snapshot(pkg) == before  # a dry run writes nothing
        code, out = run("fill", str(pkg), "--to", "ru-RU")
        assert code == 0
        after = snapshot(pkg)
        changed = sorted(p.parent.name + "/" + p.name for p in after if after[p] != before.get(p))
        assert "iaDeleteOldLogs_Process.Process/resource.ru-RU.xml" in changed and "iaRunCase_UserTask.ProcessUserTask/resource.ru-RU.xml" in changed
        assert all(name.endswith("/resource.ru-RU.xml") for name in changed), changed
        assert all(after[p] == before[p] for p in before if p.name != "resource.ru-RU.xml")  # other cultures untouched, byte for byte
        task = Resources(pkg / "Resources" / USER_TASK.name)
        en, ru = task.cultures["en-US"], task.cultures["ru-RU"]
        assert set(en) <= set(ru) and task.attrs["ru-RU"] == task.attrs["en-US"]  # the icons came along with their attributes
        code, out = run("missing", str(pkg), "--culture", "ru-RU")
        assert out.strip().endswith("0 key(s) missing in ru-RU against en-US")


def test_set_rename_and_remove_keys():
    with package() as pkg:
        res = pkg / "Resources" / "iaProcess_0d4c445.Process"
        code, out = run("set", str(pkg), "iaProcess_0d4c445", "Caption", "en-US=Renamed process", "ru-RU=Переименованный")
        assert code == 0
        r = Resources(res)
        assert r.get("Caption") == "Renamed process" and r.get("Caption", "ru-RU") == "Переименованный"
        assert '"Caption": "Renamed process"' in read(pkg / "Schemas" / "iaProcess_0d4c445" / "descriptor.json")  # descriptor follows en-US
        original = Resources(PROCESSES / "Resources" / res.name)
        assert run("rename-key", str(pkg), "iaProcess_0d4c445", "LaneSets.LaneSet1", "LaneSets.Main")[0] == 0  # the key and its subkeys
        r = Resources(res)
        assert r.get("LaneSets.Main.Lanes.Lane1.Caption", "uk-UA") == original.get("LaneSets.LaneSet1.Lanes.Lane1.Caption", "uk-UA")
        assert r.get("LaneSets.LaneSet1.Caption") is None and r.get("LaneSets.Main.Caption") == original.get("LaneSets.LaneSet1.Caption")
        assert run("remove-key", str(pkg), "iaProcess_0d4c445", "LaneSets.Main")[0] == 0
        assert not any(k.startswith("LaneSets.") for items in Resources(res).cultures.values() for k in items)
        for argv in (("rename-key", str(pkg), "iaProcess_0d4c445", "Nope", "X"), ("rename-key", str(pkg), "iaProcess_0d4c445", "Caption", "Caption"),
                     ("remove-key", str(pkg), "iaProcess_0d4c445", "Nope"), ("set", str(pkg), "iaNope", "Caption", "en-US=x"),
                     ("set", str(pkg), "iaProcess_0d4c445", "Caption", "novalue")):
            code, out = run(*argv)
            assert code == 2, (argv, out)


if __name__ == "__main__":
    for fn in [v for k, v in list(globals().items()) if k.startswith("test_")]:
        fn()
        print("ok", fn.__name__)
