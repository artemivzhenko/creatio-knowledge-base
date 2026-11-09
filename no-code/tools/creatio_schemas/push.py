"""One-command package install: clear IsChanged, push, check compilation, publish, probe."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from .clio import Clio
from .workspace import Workspace


def push(package: Path, env: str, clio: Clio, probe: bool = False, dry_run: bool = False, log=print) -> int:
    """Push a package to an environment: clear IsChanged, push-pkg, compile, publish, probe.
    
    Args:
        package: path to the package folder
        env: clio environment name
        clio: Clio instance for running commands
        probe: if True, run probes for each schema
        dry_run: if True, print commands without executing
        log: logging function (default: print)
    
    Returns:
        0 on success, 1 on failure
    """
    package = Path(package)
    descriptor_data = json.loads(Path(package / "descriptor.json").read_text(encoding="utf-8-sig"))["Descriptor"]
    pkg_name = descriptor_data["Name"]
    pkg_root = package.parent
    start_time = time.time()
    
    steps = [
        ("clear IsChanged", lambda: _clear_is_changed(env, clio, dry_run, log)),
        ("push-pkg", lambda: _push_pkg(package, pkg_root, pkg_name, clio, dry_run, log)),
        ("compilation log", lambda: _check_compilation(env, clio, dry_run, log)),
        ("publish", lambda: _publish_if_needed(package, env, clio, dry_run, log)),
    ]
    
    for step_name, step_fn in steps:
        if dry_run:
            log(f"{step_name}: (dry run)")
        else:
            try:
                result = step_fn()
                if result is False:
                    log(f"{step_name}: FAILED")
                    return 1
                log(f"{step_name}: ok")
            except Exception as e:
                log(f"{step_name}: FAILED {str(e)[:100]}")
                return 1
    
    if probe and not dry_run:
        if _run_probes(package, env, clio, log) is False:
            return 1
        log("probes: ok")
    
    elapsed = time.time() - start_time
    log(f"pushed {pkg_name} to {env} in {int(elapsed)} s")
    return 0


def _clear_is_changed(env: str, clio: Clio, dry_run: bool, log) -> bool:
    """Clear IsChanged flag in SysSchema."""
    sql = 'update "SysSchema" set "IsChanged"=false'
    if dry_run:
        log(f"  clio execute-sql-script '{sql}' -e {env}")
        return True
    try:
        clio.execute_sql(sql)
        return True
    except Exception:
        return False


def _push_pkg(package: Path, pkg_root: Path, pkg_name: str, clio: Clio, dry_run: bool, log) -> bool:
    """Run clio push-pkg."""
    if dry_run:
        log(f"  clio push-pkg {pkg_name} -e (env)")
        return True
    try:
        result = subprocess.run(
            ["clio", "push-pkg", pkg_name, "-e", clio.env],
            cwd=str(pkg_root),
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            log(f"  error: {result.stderr[:200]}")
            return False
        return True
    except Exception:
        return False


def _check_compilation(env: str, clio: Clio, dry_run: bool, log) -> bool:
    """Check the last compilation log for errors."""
    if dry_run:
        log("  clio last-compilation-log -e (env)")
        return True
    try:
        result = subprocess.run(
            ["clio", "last-compilation-log", "-e", env],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            log(f"  error: {result.stderr[:200]}")
            return False
        
        lines = result.stdout.strip().split("\n")
        if lines:
            last_line = lines[-1]
            log(f"  {last_line}")
            
            if "Errors: 0" not in last_line:
                return False
        return True
    except Exception:
        return False


def _publish_if_needed(package: Path, env: str, clio: Clio, dry_run: bool, log) -> bool:
    """Check if package has processes with scripts/user tasks; if yes, publish."""
    has_script_task = False
    
    for metadata_path in package.glob("Schemas/*/metadata.json"):
        try:
            with open(metadata_path, "r", encoding="utf-8-sig") as f:
                text = f.read()
                if "ProcessSchemaScriptTask" in text or "ProcessSchemaUserTask" in text:
                    has_script_task = True
                    break
        except Exception:
            pass
    
    if not has_script_task:
        log("publish: not needed")
        return True
    
    if dry_run:
        log("  clio compile-configuration -e (env)")
        return True
    
    try:
        result = subprocess.run(
            ["clio", "compile-configuration", "-e", env],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode != 0:
            log(f"  error: {result.stderr[:200]}")
            return False
        
        lines = result.stdout.strip().split("\n")
        if lines:
            log(f"  {lines[-1]}")
        return True
    except Exception:
        return False


def _run_probes(package: Path, env: str, clio: Clio, log) -> bool:
    """Run probes for objects, rules, sql scripts, and processes."""
    try:
        probe_commands = [
            ("objects", "object"),
            ("rules", "rule"),
            ("sqlscripts", "sqlscript"),
            ("process", "process"),
        ]
        
        for module_name, item_type in probe_commands:
            module_path = package.parent.parent / "no-code" / "tools" / module_name
            if not module_path.exists():
                continue
            
            for schema_dir in (package / "Schemas").iterdir():
                if not schema_dir.is_dir():
                    continue
                schema_name = schema_dir.name
                
                result = subprocess.run(
                    ["python", "-m", module_name, "probe", str(package), schema_name, "--env", env],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    log(f"  probe {schema_name}: FAILED")
                    return False
        
        return True
    except Exception:
        return False
