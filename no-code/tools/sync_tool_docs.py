#!/usr/bin/env python3
"""
Rewrites the command block of every toolkit README from the CLI's own `--help`.

    python no-code/tools/sync_tool_docs.py [<tools folder>]

The block sits between `<!-- commands:start -->` and `<!-- commands:end -->`; a README that lacks it
gets one (under `## Commands`) before its first `##` heading. The block holds the syntax lines of
the CLI's docstring and a table of its commands with their help text, so the README never repeats
them by hand. Running it twice changes nothing. Pure standard library.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

START, END = "<!-- commands:start -->", "<!-- commands:end -->"
HERE = Path(__file__).resolve().parent


def help_of(root: Path, tool: str) -> str:
    env = {**os.environ, "COLUMNS": "100", "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run([sys.executable, str(root / "creatio.py"), *tool.split(), "--help"], capture_output=True, text=True,
                         encoding="utf-8", env=env, check=True)
    return run.stdout.replace("\r\n", "\n")


def syntax_of(text: str) -> list[str]:
    """The indented lines of the description (the docstring's command lines), dedented, blank lines only between them."""
    head = re.split(r"\n(?:positional arguments|options):", text)[0]
    out: list[str] = []
    pending = 0
    for line in head.split("\n\n", 1)[-1].split("\n"):
        if line.startswith("    "):
            out += [""] * pending + [line[4:].rstrip()]
            pending = 0
        elif not line.strip() and out:
            pending += 1
        elif out:
            break
    return out


def commands_of(text: str) -> list[tuple[str, str]]:
    """(name, help) of the sub-commands in argparse's `positional arguments` block; empty for a tool without any."""
    m = re.search(r"positional arguments:\n((?:  .*\n?|\n)+)", text)
    if not m:
        return []
    lines = m.group(1).split("\n")
    if not lines or not re.match(r"  (command|\{.*\})\s*$", lines[0]):
        return []
    rows: list[list[str]] = []
    for line in lines[1:]:
        if re.match(r"    \S", line):
            name, _, helptext = line.strip().partition("  ")
            rows.append([name, helptext.strip()])
        elif line.startswith("      ") and rows:
            rows[-1][1] += " " + line.strip()
    return [(n, h) for n, h in rows]


def block_for(root: Path, tools: list[str]) -> str:
    parts = []
    for tool in tools:
        text = help_of(root, tool)
        if len(tools) > 1:
            parts.append(f"### {tool}\n")
        syntax = syntax_of(text)
        if syntax:
            parts.append("```\n" + "\n".join(syntax) + "\n```\n")
        rows = commands_of(text)
        if rows:
            parts.append("| command | what it does |\n| --- | --- |\n" + "\n".join(f"| `{n}` | {h} |" for n, h in rows) + "\n")
    return "\n".join(parts).rstrip("\n")


def sync_readme(readme: Path, block: str) -> bool:
    """Put `block` between the markers (adding them before the first `##` heading); True when the file changed."""
    text = readme.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in text else "\n"
    text = text.replace("\r\n", "\n")
    new = f"{START}\n{block}\n{END}"
    if START in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: new, text, flags=re.S)
    else:
        m = re.search(r"^## ", text, re.M)
        at = m.start() if m else len(text)
        text = text[:at] + f"## Commands\n\n{new}\n\n" + text[at:]
    data = text.replace("\n", nl).encode("utf-8")
    if data == readme.read_bytes():
        return False
    readme.write_bytes(data)
    return True


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else HERE
    sys.path.insert(0, str(root))
    import creatio  # the tool table lives there

    by_folder: dict[str, list[str]] = {}
    for tool in creatio.tools():
        by_folder.setdefault(tool.split()[0], []).append(tool)
    for folder, tools in by_folder.items():
        readme = root / folder / "README.md"
        if readme.is_file():
            print(("updated " if sync_readme(readme, block_for(root, tools)) else "same    ") + folder)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
