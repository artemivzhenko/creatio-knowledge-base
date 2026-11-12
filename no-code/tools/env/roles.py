#!/usr/bin/env python3
"""Who is in a role, which roles a user has, and which users are missing from a role - the closure, nested roles included.

    python roles.py members -e <env> <Role> [--units]
    python roles.py user    -e <env> <login or contact name>
    python roles.py diff    -e <env> <Role> <user>[,<user>...]

Reads `SysAdminUnitInRole` (what the platform resolves), never `SysUserInRole` (direct members only). `diff` exits 1
when a user is not in the role; 2 on a usage error or an unknown role or user.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.access import render_members, render_roles, role_diff, role_members, user_roles  # noqa: E402
from creatio_schemas.environment import open_environment  # noqa: E402


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = p.add_subparsers(dest="command", required=True, metavar="command")
    members = commands.add_parser("members", help="the users (and with --units the units) a role reaches")
    members.add_argument("role")
    members.add_argument("--units", action="store_true", help="organization units and roles too, not only users")
    user = commands.add_parser("user", help="the roles a user has, direct or through another unit")
    user.add_argument("user")
    diff = commands.add_parser("diff", help="the users of a list who are not in the role (exit 1)")
    diff.add_argument("role")
    diff.add_argument("users", help="comma-separated logins or contact names")
    for sub in (members, user, diff):
        sub.add_argument("-e", "--env", help="clio environment name")
        sub.add_argument("--project", help="project.json")
    a = p.parse_args(argv)
    try:
        env = open_environment(a.env, a.project, **env_kw)
        if a.command == "members":
            print(render_members(role_members(env, a.role, a.units)))
        elif a.command == "user":
            print(render_roles(user_roles(env, a.user)))
        else:
            result = role_diff(env, [u.strip() for u in a.users.split(",") if u.strip()], a.role)
            print(f"in {a.role}: {', '.join(result['present']) or '-'}\nnot in {a.role}: {', '.join(result['missing']) or '-'}")
            return 1 if result["missing"] else 0
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
