#!/usr/bin/env python3
"""Start a business process on an environment (ProcessEngineService.svc/RunProcess) and print its result parameters.

    python proc-run.py -e <env> UsrOrder_Process OrderId=<guid> Quantity=3 --result Total --result Status

A value is sent as JSON when it parses as JSON (numbers, true/false, null), otherwise as text.
Exit 1 when the engine did not run the process; 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.environment import open_environment  # noqa: E402


def value_of(text: str):
    try:
        return json.loads(text)
    except ValueError:
        return text


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("process")
    p.add_argument("params", nargs="*", metavar="Param=value")
    p.add_argument("--result", action="append", default=[], metavar="Name", help="a result parameter to read back")
    p.add_argument("-e", "--env", help="clio environment name")
    p.add_argument("--project", help="project.json")
    a = p.parse_args(argv)
    try:
        bad = [x for x in a.params if "=" not in x]
        if bad:
            raise ValueError(f"expected Param=value, got {bad[0]!r}")
        params = {k: value_of(v) for k, v in (x.split("=", 1) for x in a.params)}
        run = open_environment(a.env, a.project, **env_kw).run_process(a.process, params, a.result)
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    print(f"{a.process}: {'ok' if run['success'] else 'FAILED ' + str(run['error'])}  processId {run['processId'] or '-'}")
    for name in a.result:
        print(f"  {name} = {json.dumps(run['results'].get(name), ensure_ascii=False)}")
    return 0 if run["success"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
