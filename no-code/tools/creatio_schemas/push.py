"""One-command package install: clear IsChanged, push, check compilation, publish, probe."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from .clio import Clio


def _schemas(package: Path, manager: str):
    """Yield schema directories belonging to the requested manager."""
    for descriptor in sorted(package.glob("Schemas/*/descriptor.json")):
        data = json.loads(descriptor.read_text(encoding="utf-8-sig"))["Descriptor"]
        if data.get("ManagerName") == manager:
            yield descriptor.parent


def _needs_publish(package: Path) -> bool:
    """Identify processes containing script or user tasks."""
    for schema in _schemas(package, "ProcessSchemaManager"):
        text = (schema / "metadata.json").read_text(encoding="utf-8-sig")
        if "ProcessSchemaScriptTask" in text or "ProcessSchemaUserTask" in text:
            return True
    return False


def push(package: Path, env: str, clio: Clio, probe: bool = False, dry_run: bool = False, log=print) -> int:
    """Push a package, stopping on the first failed step."""
    package = Path(package).resolve()
    pkg_name = json.loads((package / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"]["Name"]
    start = time.monotonic()
    sql = 'update "SysSchema" set "IsChanged"=false'

    def command(args, cwd=None):
        if dry_run:
            log("  " + subprocess.list2cmdline(["clio", *args]))
            return ""
        return clio.run(args, cwd=cwd)

    def clear():
        if dry_run:
            command(["execute-sql-script", sql, "-e", env])
        else:
            clio.execute_sql(sql)

    def install():
        command(["push-pkg", pkg_name, "-e", env], cwd=package.parent)

    def compilation():
        output = command(["last-compilation-log", "-e", env])
        if dry_run:
            return
        summaries = [line for line in output.splitlines() if "Finished building project:" in line]
        if not summaries:
            raise RuntimeError("compilation summary not found")
        summary = summaries[-1]
        log(f"  {summary}")
        match = re.search(r"\bErrors:\s*(\d+)\b", summary)
        if not match or int(match.group(1)) != 0:
            raise RuntimeError(summary)

    def publish():
        if not _needs_publish(package):
            return False
        if not dry_run:
            log("publish: started")
        output = command(["compile-configuration", "-e", env])
        if output.strip():
            log(f"  {output.strip().splitlines()[-1]}")
        return True

    for name, step in (("clear IsChanged", clear), ("push-pkg", install),
                       ("compilation log", compilation), ("publish", publish)):
        try:
            result = step()
        except RuntimeError as e:
            log(f"{name}: FAILED {str(e)[:200]}")
            return 1
        log(f"{name}: {'not needed' if result is False else 'ok'}")

    if probe:
        try:
            _run_probes(package, env, dry_run, log)
        except RuntimeError as e:
            log(f"probes: FAILED {str(e)[:200]}")
            return 1
        log("probes: ok")

    log(f"pushed {pkg_name} to {env} in {int(time.monotonic() - start)} s")
    return 0


def _run_probes(package: Path, env: str, dry_run: bool, log) -> None:
    """Run object and SQL script probes for package items."""
    tools = Path(__file__).resolve().parent.parent
    items = [(tools / "objects" / "objects.py", p.name) for p in _schemas(package, "EntitySchemaManager")]
    items += [(tools / "sqlscripts" / "sqlscripts.py", p.parent.name)
              for p in sorted(package.glob("SqlScripts/*/descriptor.json"))]
    for script, name in items:
        args = [sys.executable, str(script), "probe", str(package), name, "--env", env]
        if dry_run:
            log("  " + subprocess.list2cmdline(args))
            continue
        try:
            result = subprocess.run(args, capture_output=True, text=True, check=False)
        except OSError as e:
            raise RuntimeError(f"probe {name}: {e}") from e
        output = result.stdout + result.stderr
        for line in output.splitlines():
            log(f"  probe {name}: {line}")
        if result.returncode:
            raise RuntimeError(f"probe {name} exited {result.returncode}: {output[-500:]}")
