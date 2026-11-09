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
from creatio_schemas.push import push  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("package", help="path to the package folder")
    p.add_argument("-e", "--env", required=True, help="clio environment name")
    p.add_argument("--probe", action="store_true", help="run probes for each schema")
    p.add_argument("--dry-run", action="store_true", help="print commands without executing")
    args = p.parse_args(argv)
    
    try:
        return push(Path(args.package), args.env, Clio(args.env), args.probe, args.dry_run)
    except (FileNotFoundError, KeyError, ValueError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

