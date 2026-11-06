#!/usr/bin/env python3
"""
Business rules of objects and Freedom UI pages stored in a package (library: ../creatio_schemas/rules).

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

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from creatio_schemas import Clio, RuleEngine, RuleSchema  # noqa: E402
from creatio_schemas.cli import CommandLine  # noqa: E402
from creatio_schemas.rules.engine import STATES  # noqa: E402


def new(_, a):
    print(RuleSchema.create(Path(a.package), a.target, a.parent_uid, a.target_uid, a.kind, a.version, a.caption).describe())


def inspect(rs, a):
    print(rs.describe())


def validate(rs, a):
    problems = rs.validate()
    print("\n".join(problems) if problems else "ok")
    return 1 if rs.errors() else 0


def load_spec(path: str) -> list[dict]:
    spec = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return spec if isinstance(spec, list) else [spec]


def add(rs, a):
    for r in [r for s in load_spec(a.spec) for r in rs.add(s)]:
        print(f"add: {r['BR3']} ({r['UId']})")


def replace(rs, a):
    spec = load_spec(a.spec)
    if len(spec) != 1:
        raise ValueError("replace takes one rule spec")
    for r in rs.replace(a.rule, spec[0]):
        print(f"replace: {r['BR3']} ({r['UId']})")


def caption(rs, a):
    for item in a.values:
        culture, _, value = item.partition("=")
        rs.set_caption(a.rule, value, [culture])


def probe(rs, a):
    """Entity: run the deployed rules for a record state. Page: the rules the server hands to the page (they run in the browser)."""
    engine = RuleEngine(Clio(a.env))
    scope = rs.target or rs.target_uid
    if rs.kind == "page":
        ok, delivered = engine.page_rules(scope)
        print(f"{len(delivered)} rule(s) delivered to the page {scope} (page rules execute in the browser):")
        for r in delivered:
            print(f"  {r.get('name')}  enabled={r.get('enabled', True)}")
        return 0 if ok else 1
    known = rs.context().attributes
    attrs = []
    for item in a.values:
        name, _, raw = item.partition("=")
        name, _, dvt = name.partition(":")  # Name:Type=value overrides the type
        try:
            value = json.loads(raw)
        except ValueError:
            value = raw
        attrs.append(engine.attribute(name, value, dvt or known.get(name, (None, None))[0]))
    resp = engine.execute(scope, attrs, a.trigger, a.state)
    if not resp.get("success"):
        print(json.dumps(resp.get("errorInfo"), ensure_ascii=False))
        return 1
    for act in engine.actions(resp):
        value = act.get("value")
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        flags = ("  (reset)" if act.get("resetToDefault") else "") + ("  (skipped)" if act.get("skip") else "")
        print(f"{act.get('businessRuleName')}: {act.get('typeName')} {act.get('path')} = {json.dumps(value, ensure_ascii=False)}{flags}")
    for err in engine.errors(resp):
        print("error:", json.dumps(err, ensure_ascii=False))
    return 0


def build() -> CommandLine:
    cli = CommandLine(__doc__, "target")
    c = cli.command
    p = c("new", new, "create the addon <Target>BusinessRule (own, or replacing with --parent-uid)", target=False)
    p.add_argument("package")
    p.add_argument("target")
    p.add_argument("--parent-uid", help="UId of the base package's <Target>BusinessRule -> a replacing addon")
    p.add_argument("--target-uid", help="UId of a target that is not in the workspace")
    p.add_argument("--kind", choices=["entity", "page"], help="kind of a target that is not in the workspace")
    p.add_argument("--version", default="8.2.3.1351", help="platform version written as CreatedInVersion")
    p.add_argument("--caption", help="addon caption (default '<Target caption> (Business rules)')")
    c("inspect", inspect, "the rules, decoded, and the changes to base rules")
    c("validate", validate, "problems; exit code 1 on errors (warnings do not count)")
    p = c("add", add, "add rules from a spec file", writes=True)
    p.add_argument("--spec", required=True, help="JSON file with one rule spec or a list of them")
    p = c("replace", replace, "rebuild a rule from a spec keeping its UId, name and caption", writes=True)
    p.add_argument("rule")
    p.add_argument("--spec", required=True)
    p = c("remove", lambda rs, a: print("removed", ", ".join(rs.remove(a.rule))), "remove a rule with its generated rules", writes=True)
    p.add_argument("rule")
    for name, on in (("enable", True), ("disable", False)):
        p = c(name, lambda rs, a, on=on: rs.set_enabled(a.rule, on), f"{name} a rule (a base rule by UId)", writes=True)
        p.add_argument("rule")
    p = c("remove-base", lambda rs, a: rs.remove_base(a.rule), "replacing addon: delete a base rule by UId", writes=True)
    p.add_argument("rule")
    p = c("caption", caption, "set a rule caption", writes=True)
    p.add_argument("rule")
    p.add_argument("values", nargs="+", metavar="culture=value")
    p = c("probe", probe, "prove deployed rules on an environment")
    p.add_argument("values", nargs="*", metavar="Attr[:Type]=value")
    p.add_argument("--env", required=True, help="clio environment name")
    p.add_argument("--trigger", nargs="*", help="attributes that just changed (default: the record was loaded)")
    p.add_argument("--state", default="Update", choices=STATES, help="record state; set-values are skipped when an existing record loads")
    return cli


def main(argv: list[str]) -> int:
    return build().run(argv, lambda a: None if a.command == "new" else RuleSchema(Path(a.package), RuleSchema.name_for(a.package, a.target)))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
