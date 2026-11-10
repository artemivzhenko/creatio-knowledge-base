"""The layers of a schema on an environment: every SysSchema copy of the name, in the order the platform applies them.

One SQL call (through Environment.sql, so clio's file form) returns each copy with its package, ExtendParent,
ModifiedOn and ModifiedBy, IsChanged, the size and md5 of its body (SysSchemaContent, else the MetaData column)
and its level in the package hierarchy of the customisation package (the platform function the object
toolkit's base fetch uses). The copy applied last wins - and when it lives in the customisation package
(`Custom`, or project.json environment.customLayer), it overrides every package the task pushes. With a rule
UId, each layer's body says whether that business rule is absent, enabled, disabled or removed there.
PostgreSQL only, like the other probes.
"""

from __future__ import annotations

import json

from ..entity.hierarchy import merge_order

CUSTOM_LAYER = "Custom"


def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def layers_sql(schema: str, custom_layer: str = CUSTOM_LAYER) -> str:
    name, custom = _quote(schema), _quote(custom_layer)
    return f"""select p."Name"::text "package", s."ExtendParent"::text "extendParent", s."ModifiedOn"::text "modifiedOn",
  coalesce(c."Name", '')::text "modifiedBy", s."IsChanged"::text "isChanged", s."ManagerName"::text "manager",
  coalesce(octet_length(b."Content"), octet_length(s."MetaData"), 0)::text "size",
  coalesce(md5(b."Content"), md5(s."MetaData"), '')::text "md5",
  coalesce(convert_from(b."Content", 'UTF8'), '')::text "body",
  coalesce(h."SchemaLevel"::text, '-1') "sl", coalesce(h."PackageLevel"::text, '-1') "pl"
from "SysSchema" s
join "SysPackage" p on p."Id" = s."SysPackageId"
left join "Contact" c on c."Id" = s."ModifiedById"
left join lateral (select sc."Content" from "SysSchemaContent" sc where sc."SysSchemaId" = s."Id"
  order by octet_length(sc."Content") desc limit 1) b on true
left join "tsp_GetSysSchemaParentsInPackageHierarchyByPackage"(
  (select "UId" from "SysSchema" where "Name" = {name} and not "ExtendParent" limit 1),
  (select "UId" from "SysSchema" where "Name" = {name} and not "ExtendParent" limit 1),
  (select "SysWorkspaceId" from "SysPackage" where "Name" = {custom}),
  (select "Id" from "SysPackage" where "Name" = {custom})) h on h."Id" = s."Id"
where s."Name" = {name}"""


def rule_state(body: str, uid: str) -> str:
    """absent / enabled / disabled / removed of a business rule (by UId) in a Classic UI body; `no body` when empty."""
    if not body.strip():
        return "no body"
    from ..classicui.schema import ClassicSchema
    from ..text import mask

    view = ClassicSchema.__new__(ClassicSchema)  # the reader's parse over a text, without package files
    view.body, view.masked, view.name = body, mask(body), "layer"
    view.module_name, view.dependencies, view.sections, view._return_at, view._deps_at = None, [], {}, None, None
    view._parse()
    hit = view._rule_at(uid)
    if not hit:
        return "absent"
    props = {k: view._literal(va, vb) for k, _, va, vb in view._members(hit[1])}
    if props.get("removed") == "true":
        return "removed"
    return "disabled" if props.get("enabled") == "false" else "enabled"


def schema_layers(env, schema: str, rule: str | None = None, custom_layer: str = CUSTOM_LAYER) -> dict:
    """{schema, rule, customLayer, layers: [...] applied first to last, custom: [packages of the customisation layer]}."""
    rows = env.sql(layers_sql(schema, custom_layer))
    outside = [r for r in rows if r.get("sl") in (None, "", "-1")]  # not in the customisation package's hierarchy: listed first, applied nowhere above it
    out = []
    for r in outside + merge_order([r for r in rows if r not in outside]):
        layer = {k: r.get(k, "") for k in ("package", "extendParent", "modifiedOn", "modifiedBy", "isChanged", "manager", "size", "md5")}
        layer["level"] = None if r.get("pl") in (None, "", "-1") else int(r["pl"])
        if rule:
            layer["rule"] = rule_state(r.get("body") or "", rule)
        out.append(layer)
    custom = [x["package"] for x in out if x["package"].lower() == custom_layer.lower()]
    return {"schema": schema, "rule": rule, "customLayer": custom_layer, "layers": out, "custom": custom}


def render(result: dict, env_name: str = "") -> str:
    layers = result["layers"]
    where = f" on {env_name}" if env_name else ""
    if not layers:
        return f"{result['schema']}{where}: no SysSchema copy of that name"
    head = f"{result['schema']}{where}: {len(layers)} cop{'y' if len(layers) == 1 else 'ies'}, applied first to last (the last one wins)"
    cols = ["package", "extendParent", "modifiedOn", "modifiedBy", "isChanged", "size", "md5"] + (["rule"] if result["rule"] else [])
    titles = {"extendParent": "replacing", "modifiedOn": "modified on", "modifiedBy": "by", "isChanged": "changed", "size": "bytes"}
    cells = [[titles.get(c, c) for c in cols]] + [[str(x.get(c, ""))[:8] if c == "md5" else str(x.get(c, ""))[:19] if c == "modifiedOn" else str(x.get(c, ""))
                                                   for c in cols] for x in layers]
    widths = [max(len(row[i]) for row in cells) for i in range(len(cols))]
    lines = [head] + ["  " + "  ".join(v.ljust(w) for v, w in zip(row, widths)).rstrip() for row in cells]
    if result["rule"]:
        lines.append(f"  rule {result['rule']}: {layers[-1]['rule']} in the layer applied last ({layers[-1]['package']})")
    if result["custom"]:
        lines.append(f"Custom layer present: {', '.join(result['custom'])}")
    return "\n".join(lines)


def to_json(result: dict) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)
