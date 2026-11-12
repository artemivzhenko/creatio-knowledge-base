#!/usr/bin/env python3
"""What ran on a site: business-process runs from SysProcessLog, and one run's error in full.

    python proc-runs.py runs  -e <env> --process UsrOrder_Process [--limit 20] [--since 2026-11-11] [--until ...]
    python proc-runs.py runs  -e <env> --record UsrOrder:<id> [--window 30]
    python proc-runs.py error -e <env> <log id>

`runs --record` lists every run that started within --window seconds of a change of the record or of a row pointing at
it (its details), oldest first. The processes `environment.noiseProcesses` of --project names (names or prefixes) are
hidden from `--record` and the unfiltered list, with a line saying how many. Times are UTC and `environment.timeZone`.
Exit 1 when no run is found (`runs`) or the run failed (`error`); 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.environment import open_environment  # noqa: E402
from creatio_schemas.records import zone_of  # noqa: E402
from creatio_schemas.runs import process_error, process_runs, render_error, render_runs  # noqa: E402


def noise_of(project: str | None) -> list[str]:
    if not project:
        return []
    with open(project, encoding="utf-8-sig") as f:
        return list((json.load(f).get("environment") or {}).get("noiseProcesses") or [])


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = p.add_subparsers(dest="command", required=True, metavar="command")
    runs = commands.add_parser("runs", help="the runs of a process, or the runs around the changes of a record")
    runs.add_argument("--process", help="process name or UId (every copy of that schema)")
    runs.add_argument("--record", help="<Entity>:<Id>")
    runs.add_argument("--since", help="start at or after (2026-11-11T08:00, UTC unless a zone is written)")
    runs.add_argument("--until", help="start at or before")
    runs.add_argument("--limit", type=int, default=20)
    runs.add_argument("--window", type=int, default=30, help="--record: seconds around each change (default 30)")
    error = commands.add_parser("error", help="one run's error without stack frames, and the element it stopped on")
    error.add_argument("log_id")
    for sub in (runs, error):
        sub.add_argument("-e", "--env", help="clio environment name")
        sub.add_argument("--project", help="project.json (environment, timeZone, noiseProcesses)")
    a = p.parse_args(argv)
    try:
        env, zone = open_environment(a.env, a.project, **env_kw), zone_of(a.project)
        if a.command == "runs":
            answer = process_runs(env, a.process, a.record, a.since, a.until, a.limit, a.window, noise_of(a.project), zone)
            print(render_runs(answer))
            return 0 if answer["runs"] else 1
        answer = process_error(env, a.log_id, zone)
        print(render_error(answer))
        return 1 if answer["run"]["state"] == "failed" else 0
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
