"""The base an object's diff is written against, as the platform builds it, fetched from an environment and cached.

A replacing object (or an object whose parent is not BaseEntity / BaseLookup) is a diff against
the merge of every copy of its parent in the packages the target package depends on. The
platform lists those copies with tsp_GetSysSchemaParentsInPackageHierarchyByPackage, ordered by
(SchemaLevel, PackageLevel); it merges them from the farthest to the nearest, copies on the
same level in the order the function returns them (verified: the designer's EG1.BK8 of a
replacing Account in iaTest is the events process of the copy merged last).

The cache lives outside the packages (<workspace>/.creatio-bases/<package>/<Object>.json): it
is valid until the platform or the packages below the target package change - fetch again then.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..clio import Clio
from ..diff import SchemaDiff
from ..files import dump_json, read_text, write_text


def cache_path(package: Path, obj: str) -> Path:
    package = Path(package)
    root = package.parent.parent if package.parent.name == "packages" else package.parent
    return root / ".creatio-bases" / package.name / f"{obj}.json"


def _quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def merge_order(rows: list[dict]) -> list[dict]:
    """Farthest copy first (SchemaLevel, then PackageLevel, descending); equal levels keep the order the function returned."""
    return [r for _, r in sorted(enumerate(rows), key=lambda ir: (-int(ir[1]["sl"]), -int(ir[1]["pl"] or 0), ir[0]))]


def fetch_base(clio: Clio, obj: str, package: str) -> dict:
    """{object, package, env, fetched, uid / caption of the own (not replacing) copy, chain: [package names, merge order], schema}."""
    rows = clio.sql(f"""
select f."Id"::text id, f."UId"::text uid, f."Name"::text name, s."ExtendParent"::text ext, coalesce(s."Caption", '')::text caption,
  p."Name"::text pkg, f."PackageLevel"::text pl, f."SchemaLevel"::text sl, convert_from(f."MetaData", 'UTF8') meta
from "tsp_GetSysSchemaParentsInPackageHierarchyByPackage"(
  (select "UId" from "SysSchema" where "Name" = {_quote(obj)} and "ManagerName" = 'EntitySchemaManager' and not "ExtendParent" limit 1),
  (select "UId" from "SysSchema" where "Name" = {_quote(obj)} and "ManagerName" = 'EntitySchemaManager' and not "ExtendParent" limit 1),
  (select "SysWorkspaceId" from "SysPackage" where "Name" = {_quote(package)}),
  (select "Id" from "SysPackage" where "Name" = {_quote(package)})) f
join "SysSchema" s on s."Id" = f."Id" join "SysPackage" p on p."Id" = s."SysPackageId"
""")
    if not rows:
        raise KeyError(f"no object {obj} in the hierarchy of package {package} on {clio.env}")
    ordered = merge_order([r for r in rows if r["pkg"] != package])  # the target package's own copy is what we edit
    schema: dict | None = None
    for r in ordered:
        text = r["meta"].lstrip("﻿")
        if text.lstrip().startswith("{"):
            schema = json.loads(text)["MetaData"]["Schema"]
        elif schema is None:
            raise ValueError(f"{obj}: the farthest copy ({r['pkg']}) is a diff, not a whole schema")
        else:
            schema = SchemaDiff(text).apply(schema)
    own = next(r for r in ordered if r["name"] == obj and r["ext"] == "false")
    return {"object": obj, "package": package, "env": clio.env, "fetched": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uid": own["uid"], "caption": own["caption"] or obj, "chain": [r["pkg"] for r in ordered], "schema": schema}


def save_base(package: Path, base: dict) -> Path:
    path = cache_path(package, base["object"])
    write_text(path, dump_json(base, "\n"), False)
    return path


def load_base(package: Path, obj: str) -> dict | None:
    path = cache_path(package, obj)
    return json.loads(read_text(path)[0]) if path.is_file() else None
