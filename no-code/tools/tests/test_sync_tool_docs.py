"""Checks for sync_tool_docs.py:  python tests/test_sync_tool_docs.py  (runs on a temp copy of the tools folder)."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns("__pycache__", "fixtures", ".creatio-*")


def run(root: Path) -> str:
    return subprocess.run([sys.executable, str(root / "sync_tool_docs.py")], capture_output=True, text=True, check=True, cwd=root).stdout


def test_block_is_written_and_a_second_run_changes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "tools"
        shutil.copytree(TOOLS, root, ignore=IGNORE)
        run(root)
        first = {p: p.read_bytes() for p in root.glob("*/README.md")}
        again = run(root)
        assert all(line.startswith("same") for line in again.splitlines()) and again
        assert first == {p: p.read_bytes() for p in root.glob("*/README.md")}
        objects = (root / "objects" / "README.md").read_text(encoding="utf-8")
        assert "<!-- commands:start -->" in objects and "| `probe` | compare the metadata with the table" in objects
        assert "python objects.py column   <package> <Object> add <Name>" in objects
        assert "### env sql" in (root / "env" / "README.md").read_text(encoding="utf-8")
        # a stale block is rewritten; text outside the markers is untouched
        bare = root / "dcm" / "README.md"
        text = bare.read_bytes().decode("utf-8")
        start, end = text.index("<!-- commands:start -->") + len("<!-- commands:start -->"), text.index("<!-- commands:end -->")
        bare.write_bytes((text[:start] + "\nSTALE\n" + text[end:]).encode("utf-8"))
        run(root)
        assert bare.read_bytes().decode("utf-8") == text
        # a README without the markers gets them under `## Commands`, before its first `##`
        bare.write_bytes(text[:text.index("## Commands")].encode("utf-8") + text[text.index("## How a case is stored"):].encode("utf-8"))
        run(root)
        assert bare.read_bytes().decode("utf-8") == text


def test_the_repository_readmes_are_in_sync():
    out = run(TOOLS)
    assert all(line.startswith("same") for line in out.splitlines()), out  # run the script and commit the READMEs


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
