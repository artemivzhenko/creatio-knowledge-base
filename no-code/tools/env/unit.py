#!/usr/bin/env python3
"""Run the in-Creatio tests of a project (the `integration` tier): one row per test, exit 1 on a failure.

    python unit.py run --project project.json --category UsrOrders [--evidence result.json]
    python unit.py run -e <env> --runner UsrRunTests_Process --class UsrOrderTest

The runner is what `project.json` `tests.runner` names (or `--runner`): a process schema name (started
through ProcessEngineService, its result parameter `tests.resultParameter`, default `Result`) or a service
path containing `.svc/` or `rest/` (POSTed). `tests.categoryParameter` (default `Category`) and
`tests.classParameter` (default `Class`) name the parameter that selects the tests. The answer is JSON,
often inside a WCF `<string>`; `--evidence` keeps it whole. The failed tests print first, with their messages, then the
passed ones and `N passed, M failed`. With `tests.package` (or `--package`, the package holding the tests) a warning
says when that package changed on the site after its last successful compilation (`SysPackage.ModifiedOn` newer than
`CompilationHistory.CreatedOn`): the tests ran on the old dll. Exit 2 when no runner is configured or the answer has no
list of tests.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas.environment import open_environment, unwrap_xml_string  # noqa: E402

NAME_KEYS = ("Name", "name", "TestName", "testName", "Test", "test", "Method", "method", "FullName", "fullName")
PASS_KEYS = ("Success", "success", "Passed", "passed", "IsSuccess", "isSuccess", "Ok", "ok")
STATUS_KEYS = ("Status", "status", "Result", "result", "Outcome", "outcome", "State", "state")
MESSAGE_KEYS = ("Message", "message", "Error", "error", "ErrorMessage", "errorMessage", "Exception", "exception")
PASSED = {"passed", "pass", "success", "succeeded", "ok", "true"}


def _first(d: dict, keys):
    return next((d[k] for k in keys if k in d and d[k] not in (None, "")), None)


def _cases(data):
    """The list of test results inside an answer: the answer itself, or the first list of objects one level down."""
    # shortcut: the result shape of a project's runner is not standardised; keys are guessed from the common
    # names above - add the project's keys here when its runner answers differently.
    if isinstance(data, str):
        try:
            return _cases(json.loads(unwrap_xml_string(data)))
        except ValueError:
            return None
    if isinstance(data, list) and all(isinstance(x, dict) for x in data):
        return data
    if isinstance(data, dict):
        for v in data.values():
            found = _cases(v) if isinstance(v, (list, str, dict)) else None
            if found:
                return found
    return None


def rows_of(answer) -> list[dict] | None:
    """[{name, passed, message}] or None when the answer holds no list of tests."""
    cases = _cases(answer)
    if not cases:
        return None
    out = []
    for c in cases:
        ok = _first(c, PASS_KEYS)
        if ok is None:
            status = _first(c, STATUS_KEYS)
            ok = str(status).strip().lower() in PASSED if status is not None else False
        elif isinstance(ok, str):
            ok = ok.strip().lower() in PASSED
        out.append({"name": str(_first(c, NAME_KEYS) or "?"), "passed": bool(ok), "message": str(_first(c, MESSAGE_KEYS) or "")})
    return out


def run(env, tests: dict, category: str | None, cls: str | None):
    """The runner's answer (JSON-decoded when it can be)."""
    runner = tests.get("runner")
    if not runner:
        raise LookupError("no in-Creatio test runner configured: set project.json tests.runner or pass --runner")
    param = tests.get("classParameter", "Class") if cls else tests.get("categoryParameter", "Category")
    value = cls or category
    if ".svc/" in runner or runner.startswith(("rest/", "0/rest/")):
        r = env.call_service(runner, {param: value})
        if r.error:
            raise RuntimeError(f"{runner}: {r.error}")
        return r.json() if r.json() is not None else r.text
    result_name = tests.get("resultParameter", "Result")
    answer = env.run_process(runner, {param: value}, [result_name])
    if not answer["success"]:
        raise RuntimeError(f"{runner}: {answer['error']}")
    return answer["results"].get(result_name)


STALE_SQL = ('select p."ModifiedOn" as "changed", (select max(h."CreatedOn") from "CompilationHistory" h '
             "where h.\"ProjectName\" like '%{name}%' and h.\"Result\" = {true}) as \"compiled\" from \"SysPackage\" p where p.\"Name\" = '{name}'")


def stale_dll(env, package: str) -> str | None:
    """A warning when the test package changed on the site after its last successful compilation, else None."""
    from creatio_schemas.records import ident
    name = ident(package)
    rows = []
    for true in ("true", "1"):  # PostgreSQL booleans, then MS SQL bits
        try:
            rows = env.sql(STALE_SQL.format(name=name, true=true))
            break
        except RuntimeError:
            if true == "1":
                raise
    if not rows:
        return f"warning: no package {name} on the site"
    changed, compiled = rows[0].get("changed"), rows[0].get("compiled")
    if not compiled:
        return f"warning: no successful compilation of {name} in CompilationHistory; the dll may be older than the package"
    return (f"warning: the test package's dll is older than its last push ({name} changed {changed}, compiled {compiled})"
            if str(changed) > str(compiled) else None)


def report(rows: list[dict]) -> list[str]:
    """The failed tests first, with their messages, then the passed ones, then `N passed, M failed`."""
    failed = [r for r in rows if not r["passed"]]
    lines = [f"FAIL  {r['name']}" + (f"  - {r['message']}" if r["message"] else "") for r in failed]
    lines += [f"ok    {r['name']}" for r in rows if r["passed"]]
    return lines + [f"{len(rows) - len(failed)} passed, {len(failed)} failed"]


def cmd_run(a, env_kw) -> int:
    tests = {}
    if a.project:
        tests = json.loads(Path(a.project).read_text(encoding="utf-8-sig")).get("tests") or {}
    if a.runner:
        tests = {**tests, "runner": a.runner}
    try:
        env = open_environment(a.env, a.project, **env_kw)
        answer = run(env, tests, a.category, a.cls)
    except LookupError as e:
        print(f"error: {e.args[0]}", file=sys.stderr)
        return 2
    except (ValueError, KeyError, FileNotFoundError, RuntimeError) as e:
        print(f"error: {e.args[0] if e.args else e}", file=sys.stderr)
        return 2
    if a.evidence:
        Path(a.evidence).write_text(json.dumps(answer, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rows = rows_of(answer)
    if rows is None:
        print(f"error: the runner's answer holds no list of tests: {json.dumps(answer, ensure_ascii=False)[:300]}", file=sys.stderr)
        return 2
    print("\n".join(report(rows)))
    package = a.package or tests.get("package")
    if package:
        try:
            warning = stale_dll(env, package)
        except (ValueError, RuntimeError) as e:
            warning = f"warning: the dll age was not checked - {e.args[0] if e.args else e}"
        if warning:
            print(warning)
    return 1 if any(not r["passed"] for r in rows) else 0


def main(argv=None, **env_kw) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="run the tests of a category or a class")
    sel = r.add_mutually_exclusive_group(required=True)
    sel.add_argument("--category")
    sel.add_argument("--class", dest="cls")
    r.add_argument("-e", "--env", help="clio environment name")
    r.add_argument("--project", help="project.json: the environment and tests.runner")
    r.add_argument("--runner", help="override tests.runner: a process name or a service path")
    r.add_argument("--evidence", help="write the runner's whole answer to this file")
    r.add_argument("--package", help="the package holding the tests (default project.json tests.package): warn when its dll is stale")
    a = p.parse_args(argv)
    return cmd_run(a, env_kw)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
