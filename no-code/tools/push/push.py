#!/usr/bin/env python3
"""
Push a package to an environment: clear IsChanged, push-pkg, check compilation, publish, probe.

    python push.py <package> -e <environment>          push and check
    python push.py <package> -e <environment> --probe  also run probes
    python push.py <package> -e <environment> --dry-run print commands only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas import Clio  # noqa: E402
from creatio_schemas.cli import resolve_package  # noqa: E402
from creatio_schemas.push import push  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("package", help="path to the package folder, or its name (packages/<name> here or next to --project)")
    p.add_argument("-e", "--env", required=True, help="clio environment name")
    p.add_argument("--probe", action="store_true", help="run probes for each schema")
    p.add_argument("--dry-run", action="store_true", help="print commands without executing")
    p.add_argument("--project", type=Path, help="project.json containing paths.tasks")
    p.add_argument("--tasks", type=Path, help="folder containing task folders")
    p.add_argument("--task", type=Path, help="current task folder")
    p.add_argument("--force", action="store_true", help="allow environment drift")
    p.add_argument("--baseline", type=Path, help="file of accepted compilation error lines")
    p.add_argument("--skip-drift", action="store_true", help="skip the environment drift check")
    p.add_argument("--skip-foreign-files", action="store_true", help="skip the task ownership check")
    p.add_argument("--skip-sql-dates", action="store_true", help="do not stamp changed SQL descriptors")
    p.add_argument("--skip-compile-package", action="store_true", help="skip the assembly package build")
    args = p.parse_args(argv)

    try:
        return push(resolve_package(args.package, args.project), args.env, Clio(args.env), args.probe, args.dry_run,
                    project=args.project, tasks=args.tasks, task=args.task, force=args.force, baseline=args.baseline,
                    skip_drift=args.skip_drift, skip_foreign_files=args.skip_foreign_files,
                    skip_sql_dates=args.skip_sql_dates, skip_compile_package=args.skip_compile_package)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
