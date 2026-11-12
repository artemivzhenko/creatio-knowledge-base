#!/usr/bin/env python3
"""A system setting's value on every environment, with its date and author, and the data bindings of the workspace that carry it.

    python setting.py <Code> -e dev,test [--workspace <folder>]
    python setting.py <Code> --project project.json        (its `environments` list, else `environment.clioName`)

Reads `SysSettings` and `SysSettingsValue` on each site (the value column follows the setting's type; a lookup is shown by
name), then the workspace's `Data/*` bindings of `SysSettingsValue` whose row names the setting: the value a push
would write. Exit 1 when a site has no such setting; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.access import render_setting, sys_setting  # noqa: E402
from creatio_schemas.environment import Environment, open_environment  # noqa: E402
from creatio_schemas.records import zone_of  # noqa: E402


def environments(names: str | None, project: str | None, **env_kw) -> dict:
    """{name: Environment}: the comma list of clio names, else the project's `environments`, else its own environment."""
    if names:
        return {n.strip(): open_environment(n.strip(), None, **env_kw) for n in names.split(",") if n.strip()}
    if not project:
        raise ValueError("name the environments: -e dev,test or --project project.json")
    config = json.loads(Path(project).read_text(encoding="utf-8-sig"))
    listed = config.get("environments") or []
    if listed:
        return {n: open_environment(n, None, **env_kw) for n in listed}
    return {config.get("environment", {}).get("clioName") or "project": Environment.from_project(project, **env_kw)}


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("code")
    p.add_argument("-e", "--env", help="clio environment names, comma-separated")
    p.add_argument("--project", help="project.json")
    p.add_argument("--workspace", help="a workspace folder whose Data bindings are read")
    a = p.parse_args(argv)
    try:
        answer = sys_setting(a.code, environments(a.env, a.project, **env_kw), a.workspace, zone_of(a.project))
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    print(render_setting(answer))
    return 0 if all(isinstance(found, list) and found for found in answer["environments"].values()) else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
