#!/usr/bin/env python3
"""Find which table holds an Id, and show a record with its lookups named and the rows that point at it.

    python record.py find    -e <env> <id> [--workspace <folder>] [--everywhere]
    python record.py context -e <env> <Entity> <id> [--columns "Name,*Id"] [--depth 1|2]

`find` scans the base tables that have a uuid `Id` (the workspace's objects first) in unions of 50 and stops at the first
batch that holds the Id; `--everywhere` goes on. Times are UTC and the zone `environment.timeZone` of --project names.
Exit 1 when nothing is found; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.environment import open_environment  # noqa: E402
from creatio_schemas.records import find_record, record_context, render_context, render_hits, zone_of  # noqa: E402


def objects_of(workspace: str | None) -> list[str]:
    """The entity names of a workspace's packages (a table is named like its object)."""
    if not workspace:
        return []
    from creatio_schemas.workspace import Workspace
    root = Path(workspace)
    anchor = next(iter(sorted((root / "packages").glob("*") if (root / "packages").is_dir() else root.glob("*"))), None)
    return [s["name"] for s in Workspace(anchor).schemas if s["manager"] == "EntitySchemaManager"] if anchor else []


def workspace_of(project: str | None) -> str | None:
    """`paths.workspace` of a project.json, relative to the file's folder."""
    if not project:
        return None
    import json
    with open(project, encoding="utf-8-sig") as f:
        path = (json.load(f).get("paths") or {}).get("workspace")
    return str((Path(project).resolve().parent / path)) if path else None


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = p.add_subparsers(dest="command", required=True, metavar="command")
    find = commands.add_parser("find", help="the table(s) that hold an Id, with caption, dates and authors")
    find.add_argument("id")
    find.add_argument("--workspace", help="a workspace folder: its objects are scanned first (default: project.json paths.workspace)")
    find.add_argument("--everywhere", action="store_true", help="scan every batch, not only up to the first hit")
    context = commands.add_parser("context", help="a record with its lookups named and the rows that point at it")
    context.add_argument("entity")
    context.add_argument("id")
    context.add_argument("--columns", default="", help="comma list, * wildcards (default: every column with a value)")
    context.add_argument("--depth", type=int, default=1, choices=(0, 1, 2), help="0 the record only, 1 + the rows pointing at it, 2 + their lookups named")
    for sub in (find, context):
        sub.add_argument("-e", "--env", help="clio environment name")
        sub.add_argument("--project", help="project.json")
    a = p.parse_args(argv)
    try:
        env, zone = open_environment(a.env, a.project, **env_kw), zone_of(a.project)
        if a.command == "find":
            workspace = a.workspace or workspace_of(a.project)
            hits = find_record(env, a.id, objects_of(workspace), a.everywhere, zone)
            print(render_hits(hits))
            return 0 if hits else 1
        print(render_context(record_context(env, a.entity, a.id, a.columns, a.depth, zone)))
        return 0
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
