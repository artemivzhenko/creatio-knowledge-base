#!/usr/bin/env python3
"""
SQL scripts stored in a package (library: ../creatio_schemas/sqlscript.py).

    python sqlscripts.py list     <package>
    python sqlscripts.py inspect  <package> <Script>
    python sqlscripts.py new      <package> <Script> --file body.sql [--engine postgresql] [--install after-package] [--after Other ..] [--backward-compatible]
    python sqlscripts.py set      <package> <Script> [--file body.sql] [--engine ..] [--install ..] [--backward-compatible on|off]
    python sqlscripts.py depend   <package> <Script> add <Other> [--uid U] | remove <Other>
    python sqlscripts.py validate <package> <Script>
    python sqlscripts.py run      <package> <Script> --env dev        run the body on an environment now (a dev check, not an install)
    python sqlscripts.py probe    <package> <Script> --env dev        what the environment recorded for the installed script

Engines: mssql, oracle, postgresql (a script runs only on its engine; ship one per engine you support).
Install types: before-package, after-package (default), after-data, uninstall-app.
`clio push-pkg` installs the package and runs its scripts. Writing commands accept --dry-run.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas import Clio  # noqa: E402
from creatio_schemas.cli import CommandLine  # noqa: E402
from creatio_schemas.sqlscript import ENGINES, INSTALL_TYPES, SqlScript  # noqa: E402


def read_body(path: str) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def list_scripts(_, a):
    for s in SqlScript.all(Path(a.package)):
        deps = f"  after {', '.join(d['Name'] for d in s.depends_on)}" if s.depends_on else ""
        print(f"{s.name:<48} {s.engine:<10} {s.install_type:<14}{deps}")


def new(_, a):
    if bool(a.file) == bool(a.body):
        raise ValueError("give the body with --file or --body")
    s = SqlScript.create(Path(a.package), a.script, read_body(a.file) if a.file else a.body, a.engine, a.install, a.backward_compatible)
    for other in a.after or []:
        s.add_dependency(other)
    s.save()
    print(s.describe())


def set_(s, a):
    if a.file:
        s.set_body(read_body(a.file))
    if a.engine:
        s.set_engine(a.engine)
    if a.install:
        s.set_install_type(a.install)
    if a.backward_compatible:
        s.set_backward_compatible(a.backward_compatible == "on")


def validate(s, a):
    problems = s.validate()
    print("\n".join(problems) if problems else "ok")
    return 1 if s.errors() else 0


def run(s, a):
    rows = Clio(a.env).sql(s.body)
    print(f"ran {s.name} on {a.env}; {len(rows)} row(s) returned")
    for r in rows[:20]:
        print(" ", r)


def probe(s, a):
    q = s.name.replace("'", "''")
    rows = Clio(a.env).sql(f"""select p."Name"::text package, s."DBEngineType"::text engine, s."InstallType"::text install,
  s."NeedInstall"::text need_install, coalesce(s."LastError", '')::text last_error, s."IsChanged"::text changed, s."ModifiedOn"::text modified,
  md5(s."Body")::text body_md5
from "SysPackageSqlScript" s join "SysPackage" p on p."Id" = s."SysPackageId" where s."Name" = '{q}'""")
    if not rows:
        print(f"{s.name} is not installed on {a.env} (push the package)")
        return 1
    bad = 0
    mine = hashlib.md5(s.body.encode("utf-8")).hexdigest()  # a literal of the body does not survive the trip through clio intact
    for r in rows:
        print(f"{r['package']}: engine {r['engine']}, install {r['install']}, needs install {r['need_install']}, changed {r['changed']}, "
              f"modified {r['modified']}, body equals the file {r['body_md5'] == mine}")
        if r["last_error"]:
            print("  last error:", r["last_error"][:500])
            bad += 1
    return 1 if bad else 0


def build() -> CommandLine:
    cli = CommandLine(__doc__, "script")
    c = cli.command
    p = c("list", list_scripts, "the scripts of a package", target=False)
    p.add_argument("package")
    p = c("new", new, "create a script", target=False)
    p.add_argument("package")
    p.add_argument("script")
    p.add_argument("--file")
    p.add_argument("--body")
    p.add_argument("--engine", default="postgresql", choices=sorted(ENGINES))
    p.add_argument("--install", default="after-package", choices=list(INSTALL_TYPES))
    p.add_argument("--after", nargs="*", metavar="Script", help="scripts of the workspace that must run first")
    p.add_argument("--backward-compatible", action="store_true")
    c("inspect", lambda s, a: print(s.describe()), "engine, install type, dependencies, problems")
    c("validate", validate, "problems; exit code 1 on errors")
    p = c("set", set_, "change the body or the settings", writes=True)
    p.add_argument("--file")
    p.add_argument("--engine", choices=sorted(ENGINES))
    p.add_argument("--install", choices=list(INSTALL_TYPES))
    p.add_argument("--backward-compatible", choices=["on", "off"])
    g = cli.group("depend", "scripts that must run before this one")
    p = c("add", lambda s, a: s.add_dependency(a.other, a.uid), "run after <Other>", True, g)
    p.add_argument("other")
    p.add_argument("--uid", help="UId of a script outside the workspace")
    p = c("remove", lambda s, a: s.remove_dependency(a.other), "drop a dependency", True, g)
    p.add_argument("other")
    p = c("run", run, "run the body on an environment now (dev check; the install runs it on push)")
    p.add_argument("--env", required=True)
    p = c("probe", probe, "what the environment recorded for the installed script")
    p.add_argument("--env", required=True)
    return cli


def main(argv: list[str]) -> int:
    return build().run(argv, lambda a: None if a.command in ("new", "list") else SqlScript(Path(a.package), a.script))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
