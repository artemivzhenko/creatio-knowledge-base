"""Checks for the front door:  python tests/test_creatio.py  (dispatch only; every tool has its own suite)."""

import contextlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import creatio  # noqa: E402

PAGES = HERE.parent / "pages" / "tests" / "fixtures" / "iaTest"


def test_listing_names_every_tool_with_its_purpose():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert creatio.main([]) == 0 and creatio.main(["--help"]) == 0
    lines = out.getvalue().splitlines()
    first_words = {line.split("  ")[0].strip() for line in lines}
    for name in ("objects", "process", "pages", "describe", "push", "env sql", "env api", "project"):
        assert name in first_words, name
    assert any("Objects (entity schemas) stored in a package" in line for line in lines) and all('"""' not in line for line in lines)
    assert list(creatio.tools())[:2] == ["sqlscripts", "data"] and creatio.tools()["process"] == "process/proc.py"


def test_dispatch_runs_the_tool_with_the_rest_of_the_arguments():
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert creatio.main(["describe", "package", str(PAGES), "--kind", "object"]) == 0
    assert "  object    iaOrder " in out.getvalue()
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        assert creatio.main(["nope"]) == 2
    assert err.getvalue().startswith("error: no tool 'nope'; tools: sqlscripts")
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.suppress(SystemExit):
        creatio.main(["env", "sql", "--help"])
    assert out.getvalue().startswith("usage: sql.py")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
