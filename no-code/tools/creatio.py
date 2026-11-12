#!/usr/bin/env python3
"""One front door to the toolkits: creatio.py <tool> <command> ... (library: creatio_schemas).

    python creatio.py                       # every tool, one line each
    python creatio.py <tool> --help         # that tool's commands and flags
    python creatio.py objects inspect <pkg> <Object>
    python creatio.py describe deps <workspace> <Schema>
    python creatio.py env sql -e dev "select 1"

A tool is a folder of this directory with its CLI file; the kinds of the describe registry name
theirs (`Kind.tool`), the rest are listed here. The old `<tool>/<tool>.py` paths keep working:
this file only finds the module and calls its `main(argv)`.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# tools that are not a kind of the registry: name -> CLI file (env has one file per command)
TOOLS: dict[str, str] = {
    "describe": "describe/describe.py", "push": "push/push.py", "resources": "resources/resources.py",
    "scaffold": "scaffold/scaffold.py", "project": "project.py",
    "env sql": "env/sql.py", "env call": "env/call.py", "env proc-run": "env/proc-run.py", "env unit": "env/unit.py", "env api": "env/api.py",
    "env record": "env/record.py", "env roles": "env/roles.py", "env setting": "env/setting.py", "env proc-runs": "env/proc-runs.py",
}
DOC_RE = re.compile(r'^(?:#![^\n]*\n)?\s*(?:"""|\'\'\')\s*([^\n]+)', re.S)


def tools() -> dict[str, str]:
    """name -> CLI file, the registry's kinds first (in their order), then the rest."""
    from creatio_schemas.describe.registry import KINDS
    out: dict[str, str] = {}
    for k in KINDS:
        if k.tool:
            out.setdefault(k.tool.split("/")[0], k.tool)
    out.update(TOOLS)
    return out


def purpose(path: Path) -> str:
    m = DOC_RE.match(path.read_text(encoding="utf-8-sig"))
    return (m.group(1).strip() if m else "").split(" (library:")[0].rstrip('"').rstrip("'").rstrip()


def listing() -> str:
    width = max(len(n) for n in tools())
    return "\n".join(f"{n:<{width}}  {purpose(HERE / f)}" for n, f in tools().items()) + "\n\n" + "python creatio.py <tool> --help for the commands"


def run(argv: list[str]) -> int:
    table = tools()
    name = " ".join(argv[:2]) if len(argv) > 1 and " ".join(argv[:2]) in table else argv[0] if argv else ""
    if not name or name in ("-h", "--help"):
        print(listing())
        return 0
    if name not in table:
        print(f"error: no tool {name!r}; tools: {', '.join(table)}", file=sys.stderr)
        return 2
    path = HERE / table[name]
    spec = importlib.util.spec_from_file_location("creatio_tool_" + name.replace(" ", "_").replace("-", "_"), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rest = argv[len(name.split(" ")):]
    sys.argv[0] = str(path)  # argparse names the usage after the tool, not after this file
    return module.main(rest) or 0


def main(argv: list[str] | None = None) -> int:
    return run(sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
