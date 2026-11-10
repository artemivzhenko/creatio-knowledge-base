#!/usr/bin/env python3
"""
Installs the Claude Code plugins and MCP servers used for Creatio development.

General-purpose tooling (not Creatio-specific) plus this knowledge base's own MCP server.
Every step is idempotent: re-running updates or re-registers without duplicates.

  ponytail         plugin   lazy-senior-dev discipline: smallest change that fully works
  graphify         skill    /graphify builds a queryable knowledge graph of a codebase
  context7         MCP      up-to-date library docs (Angular, RxJS, npm packages)
  microsoft-learn  MCP      official .NET / C# documentation
  roslyn-codelens  MCP      Roslyn semantic analysis of C# solutions (needs .NET 10 SDK)
  creatio-kb       MCP      this knowledge base

    python agent_setup.py            # install
    python agent_setup.py --dry-run  # print the commands only
    python agent_setup.py --check    # inspect launchers and planned servers, register nothing
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent
DRY_RUN = "--dry-run" in sys.argv[1:]
WIN = sys.platform == "win32"


def python_launcher() -> list[str] | None:
    """Try both launchers before making any changes."""
    verdicts = []
    for launcher in (["python"], ["py", "-3"]):
        try:
            result = subprocess.run(
                launcher + ["-c", "import sys;print(sys.version)"],
                capture_output=True, text=True, timeout=15,
            )
            text = (result.stdout + result.stderr).strip()
            ok = result.returncode == 0 and text.startswith("3.") and "microsoft store" not in text.lower()
        except (OSError, subprocess.TimeoutExpired) as exc:
            text, ok = str(exc), False
        print(f"{' '.join(launcher)}: {'works' if ok else 'unavailable'}" + (f" ({text.splitlines()[0]})" if text else ""))
        verdicts.append(ok)
    if verdicts[0]:
        return ["python"]
    if verdicts[1]:
        return ["py", "-3"]
    return None


def run(title: str, cmd: list[str]) -> int:
    print(f"\n== {title}\n   {' '.join(cmd)}")
    if DRY_RUN:
        return 0
    try:
        code = subprocess.run(cmd).returncode
    except FileNotFoundError:
        # A missing tool skips this step only; the remaining steps still run.
        print(f"   warning: command not found: {cmd[0]}")
        return 127
    if code != 0:
        print(f"   warning: exit code {code}")
    return code


def find_claude() -> str:
    on_path = shutil.which("claude")
    if on_path:
        return on_path
    # The VS Code extension ships its own binary that is not on PATH.
    exe = "claude.exe" if WIN else "claude"
    pattern = str(Path.home() / ".vscode" / "extensions" / "anthropic.claude-code-*" / "resources" / "native-binary" / exe)
    found = sorted(glob.glob(pattern))
    if found:
        return found[-1]
    sys.exit("claude CLI not found. Install Claude Code or add it to PATH.")


def register_mcp(claude: str, name: str, add_args: list[str]) -> None:
    # `mcp add` refuses an existing name, so drop it first (no-op when absent).
    run(f"mcp: remove old {name}", [claude, "mcp", "remove", "--scope", "user", name])
    run(f"mcp: add {name}", [claude, "mcp", "add", "--scope", "user", *add_args])


def main() -> None:
    launcher = python_launcher()
    if launcher is None:
        sys.exit("Neither python nor py -3 works; install Python before registering servers.")
    print("Selected Python launcher: " + " ".join(launcher))
    if "--check" in sys.argv[1:]:
        print("Servers: context7, microsoft-learn, roslyn-codelens (requires .NET 10), creatio-kb")
        if (KB_ROOT.parent / "automatic-creatio-tests" / "mcp-server" / "server.py").is_file():
            print("Server: creatio-tests")
        print("Roslyn: set MCP_TIMEOUT=120000 in the server entry for slow solution loading.")
        return
    claude = find_claude()
    print(f"claude: {claude}")

    # 1. ponytail - plugin from its own marketplace (added on the fly, user scope).
    run("plugin: ponytail", [claude, "plugin", "install", "ponytail", "--marketplace", "DietrichGebert/ponytail"])

    # 2. graphify - a skill, not a server; `graphify install` writes ~/.claude/skills/graphify.
    run("graphify: pip install", [sys.executable, "-m", "pip", "install", "--upgrade", "graphifyy[mcp]"])
    # Via the interpreter: pip may fall back to the per-user site, whose Scripts
    # folder is usually not on PATH, so a bare `graphify` is not guaranteed to exist.
    run("graphify: register skill", [sys.executable, "-m", "graphify", "install"])

    # 3. context7 - library docs. CONTEXT7_API_KEY raises the rate limit; works without one.
    context7 = ["context7", "--", "npx", "-y", "@upstash/context7-mcp"]
    if os.environ.get("CONTEXT7_API_KEY"):
        context7 += ["--api-key", os.environ["CONTEXT7_API_KEY"]]
    register_mcp(claude, "context7", context7)

    # 4. Microsoft Learn - remote HTTP server, nothing to install.
    register_mcp(claude, "microsoft-learn", ["--transport", "http", "microsoft-learn", "https://learn.microsoft.com/api/mcp"])

    # 5. Roslyn CodeLens - semantic C# tools. Creatio package csproj files are SDK-style
    #    (net472), which is what the server requires. Needs the .NET 10 SDK.
    sdks = subprocess.run(["dotnet", "--list-sdks"], capture_output=True, text=True).stdout if shutil.which("dotnet") else ""
    if any(line.startswith("10.") for line in sdks.splitlines()):
        run("dotnet tool: RoslynCodeLens.Mcp", ["dotnet", "tool", "update", "-g", "RoslynCodeLens.Mcp"])
        register_mcp(claude, "roslyn-codelens", ["--env", "MCP_TIMEOUT=120000", "roslyn-codelens", "--", "roslyn-codelens-mcp"])
        print("Roslyn MCP_TIMEOUT=120000: allow extra time for solution loading.")
    else:
        print("\nroslyn-codelens skipped: .NET 10 SDK not found (dotnet --list-sdks).")

    # 6. This knowledge base.
    venv = KB_ROOT / "mcp-server" / ".venv"
    venv_py = venv / ("Scripts/python.exe" if WIN else "bin/python")
    if not venv_py.exists():
        run("creatio-kb: venv", launcher + ["-m", "venv", str(venv)])
    run("creatio-kb: pip install -e", [str(venv_py), "-m", "pip", "install", "-q", "-e", str(KB_ROOT / "mcp-server")])
    register_mcp(claude, "creatio-kb", ["creatio-kb", "--", str(venv_py), str(KB_ROOT / "mcp-server" / "server.py")])

    # 7. The UI test utility's server, when the repository sits next to this one.
    tests = KB_ROOT.parent / "automatic-creatio-tests"
    tests_server = tests / "mcp-server" / "server.py"
    if tests_server.exists():
        tests_venv = tests / "mcp-server" / ".venv"
        tests_py = tests_venv / ("Scripts/python.exe" if WIN else "bin/python")
        if not tests_py.exists():
            run("creatio-tests: venv", launcher + ["-m", "venv", str(tests_venv)])
        run("creatio-tests: pip install mcp", [str(tests_py), "-m", "pip", "install", "-q", "mcp>=2.0"])
        register_mcp(claude, "creatio-tests", ["creatio-tests", "--", str(tests_py), str(tests_server)])
    else:
        print(f"\ncreatio-tests skipped: {tests_server} not found (clone automatic-creatio-tests next to this repository).")

    print("\nDone. Restart Claude Code; check with: claude mcp list / claude plugin list")


if __name__ == "__main__":
    main()
