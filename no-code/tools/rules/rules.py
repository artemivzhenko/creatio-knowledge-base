#!/usr/bin/env python3
"""
Command line over brules.py: business rules of objects and Freedom UI pages stored in a package.

    python rules.py inspect  <package> <Target>
    python rules.py new      <package> <Target> [--parent-uid U] [--target-uid U --kind entity|page] [--version 8.3.2.4199]
    python rules.py add      <package> <Target> --spec rule.json        (one rule or a list; see README for the spec)
    python rules.py replace  <package> <Target> <Rule> --spec rule.json (rebuild keeping UId, name and caption key)
    python rules.py remove   <package> <Target> <Rule>
    python rules.py enable   <package> <Target> <Rule> | disable <package> <Target> <Rule>
    python rules.py remove-base <package> <Target> <BaseRuleUId>        (replacing addon only)
    python rules.py caption  <package> <Target> <Rule> en-US=".." [ru-RU=".."]
    python rules.py validate <package> <Target>
    python rules.py probe    <package> <Target> Attr[:Type]=value .. --env dev [--trigger Attr ..] [--state Create]
                             entity: run the deployed rules in the platform engine; page: list the rules served to it

<Target> is the entity or page name (UsrOrder, UsrOrder_FormPage) or the addon name itself
(UsrOrderBusinessRule). <Rule> is the rule name (BusinessRule_1a2b3c4), its UId or its caption.
A base rule of a replacing addon is addressed by UId (enable/disable/remove-base).
Every writing command accepts --dry-run: it prints the unified diff and changes nothing.
"""

from __future__ import annotations

import argparse
import difflib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brules import RuleSchema, create_rule_schema  # noqa: E402


def schema_name(pkg: Path, target: str) -> str:
    if (pkg / "Schemas" / target / "properties.json").is_file() and target.endswith("BusinessRule"):
        return target
    return f"{target}BusinessRule"


def finish(rs: RuleSchema, dry_run: bool) -> int:
    if dry_run:
        for path, (text, bom) in rs.files().items():
            try:
                with open(path, encoding="utf-8", newline="") as fh:
                    old = fh.read().lstrip("﻿")
            except FileNotFoundError:
                old = ""
            if old != text:
                rel = str(path.relative_to(rs.package))
                sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), text.splitlines(True), f"a/{rel}", f"b/{rel}"))
        print("\n(dry run: nothing written)")
        return 0
    rs.save()
    problems = rs.validate()
    errors = [p for p in problems if not p.startswith("warning:")]
    print(f"saved {rs.name}" + (f"; validation: {len(problems)} problem(s)" if problems else ""))
    for p in problems:
        print("  -", p)
    return 1 if errors else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["inspect", "new", "add", "replace", "remove", "enable", "disable", "remove-base", "caption", "validate", "probe"])
    ap.add_argument("package")
    ap.add_argument("target")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--spec", help="JSON file with one rule spec or a list of them")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--parent-uid", help="new: UId of the base package's <Target>BusinessRule -> a replacing addon")
    ap.add_argument("--target-uid", help="new: UId of a target that is not in the workspace")
    ap.add_argument("--kind", choices=["entity", "page"], help="new: kind of a target that is not in the workspace")
    ap.add_argument("--version", default="8.2.3.1351", help="new: platform version written as CreatedInVersion")
    ap.add_argument("--caption", help="new: addon caption (default '<Target caption> (Business rules)')")
    ap.add_argument("--env", help="probe: clio environment name")
    ap.add_argument("--trigger", nargs="*", help="probe: attributes that just changed (default: the record was loaded)")
    ap.add_argument("--state", default="Update", choices=["Create", "Update", "Copy"], help="probe: record state; set-values are skipped when an existing record loads")
    a = ap.parse_args(argv)
    pkg = Path(a.package)

    if a.command == "new":
        if a.dry_run:
            print(f"would create {pkg / 'Schemas' / (a.target + 'BusinessRule')}")
            return 0
        rs = create_rule_schema(pkg, a.target, a.parent_uid, a.target_uid, a.kind, a.version, a.caption)
        print(rs.describe())
        return 0

    rs = RuleSchema(pkg, schema_name(pkg, a.target))
    if a.command == "inspect":
        print(rs.describe())
        return 0
    if a.command == "validate":
        problems = rs.validate()
        print("\n".join(problems) if problems else "ok")
        return 1 if any(not p.startswith("warning:") for p in problems) else 0
    if a.command in ("add", "replace"):
        if not a.spec:
            raise SystemExit("--spec <file.json> is required")
        spec = json.loads(Path(a.spec).read_text(encoding="utf-8-sig"))
        if a.command == "replace":
            built = rs.replace(a.rest[0], spec)
        else:
            built = [r for s in (spec if isinstance(spec, list) else [spec]) for r in rs.add(s)]
        for r in built:
            print(f"{a.command}: {r['BR3']} ({r['UId']})")
        return finish(rs, a.dry_run)
    if a.command == "remove":
        print("removed", ", ".join(rs.remove(a.rest[0])))
        return finish(rs, a.dry_run)
    if a.command in ("enable", "disable"):
        rs.set_enabled(a.rest[0], a.command == "enable")
        return finish(rs, a.dry_run)
    if a.command == "remove-base":
        rs.remove_base(a.rest[0])
        return finish(rs, a.dry_run)
    if a.command == "caption":
        for item in a.rest[1:]:
            culture, _, value = item.partition("=")
            rs.set_caption(a.rest[0], value, [culture])
        return finish(rs, a.dry_run)
    if a.command == "probe":
        return probe(rs, a.rest, a.env, a.trigger, a.state)
    return 0


def call_service(env: str, path: str, body: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        req, out = Path(tmp) / "req.json", Path(tmp) / "out.json"
        req.write_text(json.dumps(body), encoding="utf-8")
        subprocess.run(["clio", "call-service", "-e", env, "--service-path", path, "-f", str(req), "-d", str(out)], capture_output=True, text=True, check=False)
        if not out.is_file():
            raise SystemExit("clio call-service wrote no response; check the environment name")
        return json.loads(out.read_text(encoding="utf-8-sig"))


def probe(rs: RuleSchema, assignments: list[str], env: str, triggers: list[str] | None, state: str) -> int:
    """Entity rules: run the deployed rules for a record state through the platform's engine (the page calls the same
    service). Page rules run in the browser, so for a page this lists the rules the server hands to it."""
    if not env:
        raise SystemExit("--env <clio environment> is required")
    scope = rs.target or rs.target_uid
    if rs.kind == "page":
        resp = call_service(env, "ServiceModel/BusinessRulesManagerService.svc/GetBusinessRules", {"scopes": [{"name": scope, "type": "ViewModel"}]})
        delivered = [r for block in resp.get("businessRules") or [] for r in json.loads(block.get("businessRulesConfig") or "[]")]
        print(f"{len(delivered)} rule(s) delivered to the page {scope} (page rules execute in the browser):")
        for r in delivered:
            print(f"  {r.get('name')}  enabled={r.get('enabled', True)}")
        return 0 if resp.get("success") else 1
    ctx = rs.context()
    attrs = []
    for item in assignments:
        name, _, raw = item.partition("=")
        name, _, dvt = name.partition(":")  # Name:Type=value overrides the type
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        guess = "Boolean" if isinstance(value, bool) else "Integer" if isinstance(value, int) else "Float2" if isinstance(value, float) else \
            "Lookup" if isinstance(value, str) and len(value) == 36 and value.count("-") == 4 else "ShortText"
        attrs.append({"attributeName": name, "value": value, "dataValueTypeName": dvt or ctx["attributes"].get(name, (None, None))[0] or guess,
                      "hasValue": value not in (None, "")})
    trig = [{"type": "ChangeAttributeValue", "name": t} for t in (triggers or [])] or [{"type": "DataLoaded"}]
    resp = call_service(env, "ServiceModel/BusinessRulesEngineService.svc/Execute", {"contexts": [{
        "scopeName": scope, "scopeType": "Model", "scopeId": "PDS", "scopeState": state, "modelType": "crt.EntityDataSource", "attributes": attrs, "triggers": trig}]})
    if not resp.get("success"):
        print(json.dumps(resp.get("errorInfo"), ensure_ascii=False))
        return 1
    for block in resp.get("businessRulesResponse") or []:
        for act in block.get("actions") or []:
            value = act.get("value")
            if isinstance(value, dict) and "value" in value:
                value = value["value"]
            flags = ("  (reset)" if act.get("resetToDefault") else "") + ("  (skipped)" if act.get("skip") else "")
            print(f"{act.get('businessRuleName')}: {act.get('typeName')} {act.get('path')} = {json.dumps(value, ensure_ascii=False)}{flags}")
        for err in block.get("errors") or []:
            print("error:", json.dumps(err, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
