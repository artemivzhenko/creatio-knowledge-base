"""The layers of one schema across a workspace, in the order the platform applies them (S24: the layer merge).

`layers_in_order(workspace, schema, env=None)` is the one place that order comes from; the merge plan (T03) and the
object snapshot (T02) both read it.

- With `env`: the site's order (`schema_layers`: every SysSchema copy of the name, applied first to last). A copy
  on the site only (the vendor base, a package not in the workspace) has no folder. A workspace copy the site
  does not have yet comes after them, in dependency order, with `source = "workspace"`.
- Without `env`: the workspace's copies only (a vendor base is not on disk). The own (not replacing) copy first,
  then the replacing ones so that a package comes after every package it depends on, directly or through other
  packages of the workspace (descriptor.json `DependsOn`). Two layers with no dependency path either way are
  siblings: the platform's order between them is not known from the files, so they are put by package name and
  each names the other in `siblings`.

`merge_plan(workspace, schemas=None, env=None)` (T03) is what collapsing those layers into one would do, from the
describe layer's own answers (an object's added columns, a client schema's diff and methods, a page's viewConfigDiff
and handlers): the target package, what each layer adds, the conflicts that stop a merge, the dependencies the
target must take over. It opens the layer files and writes nothing either.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..files import read_text
from ..text import mask
from .core import DEFAULT_LIMIT, cut
from .index import packages_of
from .layers import schema_layers


@dataclass(frozen=True)
class Layer:
    package: str
    folder: Path | None  # <package>/Schemas/<schema>; None when the copy is on the site only
    replacing: bool
    uid: str = ""  # the schema UId from the local descriptor ("" for a site-only copy)
    manager: str = ""
    source: str = "workspace"  # "site": the position is the site's; "workspace": derived from DependsOn
    siblings: tuple[str, ...] = ()  # packages of the layers whose order against this one is guessed


def _descriptor(path: Path) -> dict:
    return json.loads(read_text(path)[0].lstrip("﻿"))["Descriptor"]


def _workspace(workspace: Path | str) -> tuple[dict[str, Path], dict[str, set[str]]]:
    """{package name: folder}, {package name: every package it depends on, transitively, as far as the workspace knows}."""
    folders, reach, _ = _graph(workspace)
    return folders, reach


def _graph(workspace: Path | str) -> tuple[dict[str, Path], dict[str, set[str]], dict[str, set[str]]]:
    """folders, transitive dependencies, direct dependencies (descriptor.json `DependsOn`) of every workspace package."""
    folders, direct = {}, {}
    for pkg in packages_of(workspace):
        d = _descriptor(pkg / "descriptor.json")
        name = d.get("Name") or pkg.name
        folders[name] = pkg
        direct[name] = {x["Name"] for x in d.get("DependsOn") or []}
    reach: dict[str, set[str]] = {}

    def closure(name: str, path: frozenset = frozenset()) -> set[str]:
        if name in reach:
            return reach[name]
        out = set()
        for dep in direct.get(name, ()):
            if dep not in path:  # a dependency cycle: stop on it rather than recurse forever
                out |= {dep} | closure(dep, path | {name})
        reach[name] = out
        return out

    for name in direct:
        closure(name)
    return folders, reach, direct


def _local(folders: dict[str, Path], schema: str, manager: str | None) -> dict[str, Layer]:
    out = {}
    for name, pkg in folders.items():
        path = pkg / "Schemas" / schema / "descriptor.json"
        if not path.is_file():
            continue
        d = _descriptor(path)
        if manager and d.get("ManagerName") != manager:
            continue
        out[name] = Layer(name, path.parent, bool(d.get("ExtendParent")), d.get("UId", ""), d.get("ManagerName", ""))
    return out


def _depth(direct: dict[str, set[str]]):
    """The longest DependsOn chain below a package, over the workspace packages (a vendor package counts as 0)."""
    memo: dict[str, int] = {}

    def depth(name: str, path: frozenset = frozenset()) -> int:
        if name not in memo:
            below = [depth(d, path | {name}) for d in direct.get(name, ()) if d in direct and d not in path]
            memo[name] = 1 + max(below) if below else 0
        return memo[name]
    return depth


def _dependency_order(layers: list[Layer], reach: dict[str, set[str]], direct: dict[str, set[str]]) -> list[Layer]:
    """Own copies first, then the replacing ones as the platform numbers packages (SysPackage.HierarchyLevel: the
    dependency depth, then the name in ordinal order) - as far as the workspace shows the depth; siblings named."""
    depth = _depth(direct)
    own = sorted((x for x in layers if not x.replacing), key=lambda x: x.package)
    ordered = sorted((x for x in layers if x.replacing), key=lambda x: (depth(x.package), x.package))
    out = list(own)
    for x in ordered:
        loose = tuple(y.package for y in ordered if y is not x and y.package not in reach.get(x.package, set())
                      and x.package not in reach.get(y.package, set()))
        out.append(Layer(x.package, x.folder, x.replacing, x.uid, x.manager, "workspace", loose))
    return out


def layers_in_order(workspace: Path | str, schema: str, env=None, manager: str | None = None) -> list[Layer]:
    """The base and every replacing layer of `schema`, applied first to last (see the module text)."""
    folders, reach, direct = _graph(workspace)
    local = _local(folders, schema, manager)
    if env is None:
        return _dependency_order(list(local.values()), reach, direct)
    out = []
    for row in schema_layers(env, schema)["layers"]:
        if manager and row.get("manager") != manager:
            continue
        mine = local.pop(row["package"], None)
        out.append(Layer(row["package"], mine.folder if mine else None, str(row.get("extendParent")).lower() == "true",
                         mine.uid if mine else "", row.get("manager") or (mine.manager if mine else ""), "site"))
    out = _by_hierarchy_level(env, out)
    # shortcut: a copy not pushed yet goes after the site's copies; place it among them by DependsOn when T04 pushes new layers
    return out + _dependency_order(list(local.values()), reach, direct)


LEVELS_SQL = 'select "Name"::text "package", "HierarchyLevel"::text "level" from "SysPackage" where "Name" in ({names})'


def _by_hierarchy_level(env, layers: list[Layer]) -> list[Layer]:
    """The replacing copies re-sorted the way the runtime folds them (story README fact 1: SysPackage.HierarchyLevel, then
    the name in ordinal order); `schema_layers`' design-time function has no tiebreak for siblings. Unchanged when the
    site gives no level for one of them."""
    replacing = [x for x in layers if x.replacing]
    if len(replacing) < 2:
        return layers
    names = ", ".join("'" + x.package.replace("'", "''") + "'" for x in replacing)
    levels = {r["package"]: r["level"] for r in env.sql(LEVELS_SQL.format(names=names)) if r.get("level") not in (None, "")}
    if any(x.package not in levels for x in replacing):
        return layers
    ordered = iter(sorted(replacing, key=lambda x: (int(levels[x.package]), x.package)))
    return [next(ordered) if x.replacing else x for x in layers]


# --------------------------------------------------------------------------- #
# The merge plan (T03)
# --------------------------------------------------------------------------- #

CHANGING_OPS = {"merge", "remove", "move"}  # two layers changing one element: which wins is the layer order
_USED_RE = re.compile(r"(?<![=!<>])=\s*[\w.$]*\bcallParent\s*\(")  # `var x = this.callParent(...)`


@dataclass
class _Ctx:
    folders: dict[str, Path]
    reach: dict[str, set[str]]
    direct: dict[str, set[str]]
    own: dict[str, str]  # object name -> the workspace package holding its own (not replacing) copy
    keys: dict[tuple[str, str], int]  # (schema folder name, manager) -> replacing copies in the workspace


def _context(workspace: Path | str) -> _Ctx:
    folders, reach, direct = _graph(workspace)
    own, keys = {}, {}
    for pkg_name, pkg in folders.items():
        for path in (pkg / "Schemas").glob("*/descriptor.json"):
            try:
                d = _descriptor(path)
            except (OSError, ValueError, KeyError):
                continue  # an unreadable descriptor: the plan of that schema says so when it opens the layer
            key = (path.parent.name, d.get("ManagerName", ""))
            if d.get("ExtendParent"):
                keys[key] = keys.get(key, 0) + 1
            else:
                keys.setdefault(key, 0)
                if key[1] == "EntitySchemaManager":
                    own[key[0]] = pkg_name
    return _Ctx(folders, reach, direct, own, keys)


def _call_parent(src: str) -> tuple[bool, bool]:
    """(a callParent inside a nested function, its return value assigned) in a method's source `name: function() {...}`."""
    masked = mask(src)
    stack, pending, callback = [], False, False
    for i in range(masked.find("{") + 1, len(masked)):
        if masked.startswith("function", i) and not (masked[i - 1].isalnum() or masked[i - 1] in "_$") or masked.startswith("=>", i):
            pending = True
        ch = masked[i]
        if ch == "{":
            stack.append(pending)
            pending = False
        elif ch == "}" and stack:
            stack.pop()
        elif ch == ";":
            pending = False
        elif masked.startswith("callParent", i) and any(stack):
            callback = True
    return callback, bool(_USED_RE.search(masked))


def _contents(layer: Layer, schema: str) -> dict:
    """What one layer adds, from the toolkit object describe opens: columns, elements, methods, handlers."""
    from ..classicui.schema import ClassicSchema
    from ..entity.schema import EntitySchema
    from ..page.schema import PageSchema
    from .core import kind_of, open_item

    item = open_item(layer.folder.parent.parent, schema)
    out = {"kind": kind_of(item), "columns": [], "elements": [], "methods": {}, "handlers": []}
    if isinstance(item, EntitySchema):
        out["columns"] = [(c.get("A2"), (c.get("UId") or "").lower(), c.get("S2"), item.ref_name(c["S4"]) if c.get("S4") else None)
                          for c in item.own_columns()]
    elif isinstance(item, ClassicSchema):
        out["elements"] = [(op["name"], op["operation"]) for op in item.diff_operations() if op["name"]]
        out["methods"] = {m["name"]: item.method(m["name"]) for m in item.methods()}
    elif isinstance(item, PageSchema):
        out["elements"] = [(op.get("name"), op.get("operation")) for op in item.elements()]
        out["handlers"] = [name for name, _ in item.handlers()]
    return out


def _and(names) -> str:
    names = list(names)
    return " and ".join(names) if len(names) < 3 else ", ".join(names[:-1]) + " and " + names[-1]


def _counts(c: dict) -> str:
    def n(count, word):
        return f"+{count} {word}{'' if count == 1 else 's'}"
    parts = [n(len(c[k]), w) for k, w in (("columns", "column"), ("elements", "element"), ("methods", "method"), ("handlers", "handler")) if c[k]]
    return ", ".join(parts) or "nothing added"


def _conflicts(order: list[str], contents: dict[str, dict], ctx: _Ctx, target: str) -> list[str]:
    from ..files import ALL_DATA_VALUE_TYPES

    out = []
    by_name, by_uid = {}, {}
    for p in order:
        for name, uid, typ, ref in contents[p]["columns"]:
            by_name.setdefault(name, {}).setdefault(uid, []).append(p)
            by_uid.setdefault(uid, {}).setdefault(typ, []).append(p)
            owner = ctx.own.get(ref or "")
            if owner and owner != target and target in ctx.reach.get(owner, set()):
                out.append(f"conflict lookup {name} -> {ref} (its package {owner} depends on the target): {p}")
    for name, uids in by_name.items():
        if len(uids) > 1:
            out.append(f"conflict column {name} (two UIds): {_and(p for ps in uids.values() for p in ps)}")
    for uid, types in by_uid.items():
        if len(types) > 1:
            out.append(f"conflict column {uid} (types {', '.join(ALL_DATA_VALUE_TYPES.get(t, str(t)) for t in types)}): "
                       f"{_and(p for ps in types.values() for p in ps)}")
    changing = {}
    for p in order:
        for name, op in contents[p]["elements"]:
            if op in CHANGING_OPS:
                changing.setdefault(name, {}).setdefault(p, op)
    for name, layers in changing.items():
        if len(layers) > 1:
            out.append(f"conflict element {name} ({', '.join(sorted(set(layers.values())))}): {_and(layers)}")
    methods = {}
    for p in order:
        for name in contents[p]["methods"]:
            methods.setdefault(name, []).append(p)
    for name, layers in methods.items():
        if len(layers) < 2:
            continue  # a method in one layer moves as it is
        out.append(f"conflict method {name}{' (three-deep override)' if len(layers) > 2 else ''}: {_and(layers)}")
        for p in layers:
            callback, used = _call_parent(contents[p]["methods"][name])
            if callback:
                out.append(f"conflict callParent in a callback, method {name}: {p}")
            if used:
                out.append(f"conflict callParent return value used, method {name}: {p}")
    return out


def plan_schema(ctx: _Ctx, workspace: Path | str, schema: str, manager: str = "", env=None, target: str | None = None) -> dict:
    """{schema, kind, layers, target, remove, conflicts, skipped, lines, order} for one schema (see merge_plan). `target`
    names the package instead of the lowest layer: one every layer's package depends on (it need not hold a layer)."""
    layers = layers_in_order(workspace, schema, env, manager or None)
    disk = [x for x in layers if x.replacing and x.folder is not None]
    res = {"schema": schema, "kind": "?", "layers": len(disk), "target": None, "remove": 0, "conflicts": [], "skipped": False, "lines": []}
    if len(disk) < 2:
        res["lines"] = [f"{schema}: {len(disk)} replacing layer{'' if len(disk) == 1 else 's'} in the workspace, nothing to merge"]
        return res
    contents = {}
    for x in disk:
        try:
            contents[x.package] = _contents(x, schema)
        except Exception as e:  # one unreadable layer stops this schema's merge, not the plan
            contents[x.package] = {"error": f"{type(e).__name__}: {e}"}
    res["kind"] = next((c["kind"] for c in contents.values() if "kind" in c), "?")
    names = [x.package for x in disk]
    res["order"] = disk
    if target:
        if target not in ctx.folders or any(q != target and target not in ctx.reach.get(q, set()) for q in names):
            res.update(skipped=True, lines=[f"{schema} {res['kind']}: {len(disk)} layers, target {target} is not below every layer: "
                                            + ", ".join(q for q in names if q != target and target not in ctx.reach.get(q, set()))])
            return res
        lowest = [target]
    else:
        lowest = [p for p in names if all(p in ctx.reach.get(q, set()) for q in names if q != p)]
    if len(lowest) != 1:
        bottom = sorted(p for p in names if not ctx.reach.get(p, set()) & set(names))
        res.update(skipped=True, lines=[f"{schema} {res['kind']}: {len(disk)} layers, no common lowest package: {', '.join(bottom)}"])
        return res
    target = res["target"] = lowest[0]
    res["remove"] = len(disk) - (1 if target in names else 0)
    lines = [f"{schema} {res['kind']}: {len(disk)} layers, target {target}"]
    # a site-only layer folded after the first merged one: the merge would move the removed layers' lines before it
    res["between"] = [x.package for x in layers[layers.index(disk[0]):] if x.replacing and x.folder is None]
    for x in layers:
        if not x.replacing:
            continue
        if x.folder is None:
            lines.append(f"  layer {x.package}: on the site only, not merged")
            continue
        c = contents[x.package]
        if "error" in c:
            lines.append(f"  layer {x.package}: unreadable: {c['error']}")
            res["conflicts"].append(f"conflict unreadable layer: {x.package}")
        else:
            lines.append(f"  layer {x.package}: {_counts(c)}")
    guessed = [x.package for x in disk if x.siblings]
    if guessed:
        lines.append(f"  siblings: {', '.join(guessed)} (order guessed)")
    readable = [p for p in names if "error" not in contents[p]]
    res["conflicts"] += _conflicts(readable, contents, ctx, target)
    gains = set()
    for p in names:
        if p == target:
            continue
        for g in ctx.direct.get(p, ()):
            # a package above the target is not gained (a cycle); content that needs one is a `conflict lookup`
            if g != target and g not in names and g not in ctx.reach.get(target, set()) and target not in ctx.reach.get(g, set()):
                gains.add(g)
    lines += [f"  {c}" for c in res["conflicts"]]
    res["gains"] = sorted(gains)
    if gains:
        lines.append(f"  depends: {target} gains {', '.join(res['gains'])}")
    res["lines"] = lines
    return res


def merge_plan(workspace: Path | str, schemas: list[str] | None = None, env=None, limit: int = DEFAULT_LIMIT) -> tuple[str, int]:
    """(text, conflicts): the plan of every schema replaced by more than one package (or of `schemas`), then
    `<M> schemas, <L> layers to remove, <C> conflicts`. `env` takes the layer order from the site."""
    ctx = _context(workspace)
    if schemas:
        wanted = {s.lower() for s in schemas}
        keys = sorted(k for k in ctx.keys if k[0].lower() in wanted)
        missing = [s for s in schemas if s.lower() not in {k[0].lower() for k in keys}]
    else:
        keys, missing = sorted(k for k, n in ctx.keys.items() if n > 1), []
    plans = [plan_schema(ctx, workspace, name, manager, env) for name, manager in keys]
    body = [f"{name}: no copy in the workspace" for name in missing] + [line for plan in plans for line in plan["lines"]]
    merged = [p for p in plans if p["layers"] > 1]
    skipped = sum(1 for p in merged if p["skipped"])
    conflicts = sum(len(p["conflicts"]) for p in merged)
    last = (f"{len(merged)} schemas, {sum(p['remove'] for p in merged)} layers to remove, {conflicts} conflicts"
            + (f", {skipped} without a common lowest package" if skipped else ""))
    return "\n".join(cut(body, limit) + [last]), conflicts


# --------------------------------------------------------------------------- #
# The merge of an object (T04)
# --------------------------------------------------------------------------- #

# The lines that say whose layer this is: the schema UId, its package, the events process; from one layer only.
IDENTITY = {"MetaData.Schema.UId", "MetaData.Schema.A5", "MetaData.Schema.B6", "MetaData.Schema.B8", "MetaData.Schema.D36.A3",
            "MetaData.Schema.EG1.UId", "MetaData.Schema.EG1.A2", "MetaData.Schema.EG1.A5", "MetaData.Schema.EG1.B8", "MetaData.Schema.EG1.BK8"}
PACKAGE_UID = "MetaData.Schema.B6"
OBJECT = "EntitySchemaManager"
REFERENCES_FK_SQL = """select tc.table_name::text "table", kcu.column_name::text "column"
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on kcu.constraint_name = tc.constraint_name
join information_schema.referential_constraints rc on rc.constraint_name = tc.constraint_name
join information_schema.constraint_column_usage ccu on ccu.constraint_name = tc.constraint_name
where tc.constraint_type = 'FOREIGN KEY' and ccu.table_name = 'SysSchema' and ccu.column_name = 'Id' and rc.delete_rule = 'NO ACTION'
order by 1, 2"""
LAYER_IDS_SQL = """select s."Id"::text "id", p."Name"::text "package" from "SysSchema" s join "SysPackage" p on p."Id" = s."SysPackageId"
where s."Name" = {schema} and s."ManagerName" = 'EntitySchemaManager' and p."Name" in ({packages})"""


def _q(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def platform_drops(op: str, path: str) -> bool:
    """What EntitySchemaManager.ActualizeSchemaDifferencePackage ignores in every layer but the last (story README fact 3)."""
    return op == "+" and "EG1" in path and "C2" in path or op == "-" and "D20.FA" in path


def merged_diff(layers: list[Layer], source: Layer, package_uid: str, renames: dict[str, str] | None = None) -> str:
    """One diff from the layers' diffs in fold order (fact 2): the identity lines of `source` only, B6 = the target package,
    the lines the platform drops left out of every layer but the top. `renames` maps the UIds of the removed layers and of
    their packages to the merged layer's and the target's: a column keeps CreatedInSchemaUId / ModifiedInSchemaUId /
    CreatedInPackageId (A3 / A4 / A5) of a layer that no longer exists otherwise."""
    from ..workspace import parse_diff

    swap = re.compile("|".join(map(re.escape, renames)), re.I) if renames else None
    out = []
    for x in layers:
        for op, path, value in parse_diff(read_text(x.folder / "metadata.json")[0]):
            if path in IDENTITY and x is not source or x is not layers[-1] and platform_drops(op, path):
                continue
            if path == PACKAGE_UID:
                value = json.dumps(package_uid)
            elif swap:
                value = swap.sub(lambda m: renames[m.group(0).lower()], value)
            out.append(f"{op} {path}" + (f" {value}" if value else ""))
    if not any(line.startswith(f"= {PACKAGE_UID} ") for line in out):  # every designer layer has it; a hand-made one may not
        out.insert(1 if out else 0, f"= {PACKAGE_UID} {json.dumps(package_uid)}")
    return "\r\n".join(out)


def references(env, schema: str, packages: list[str]) -> list[str]:
    """`references: <table>.<column> <n> rows point at <package>'s <Schema>` for every NO ACTION foreign key to SysSchema.Id
    that holds a layer's row (T01: such a row makes the install of the removal fail whole)."""
    ids = {r["id"]: r["package"] for r in env.sql(LAYER_IDS_SQL.format(schema=_q(schema), packages=", ".join(_q(p) for p in packages)))}
    if not ids:
        return []
    keys = ", ".join(_q(i) for i in ids)
    parts = [f'select \'{r["table"]}.{r["column"]}\' "ref", "{r["column"]}"::text "id", count(*)::text "n" from "{r["table"]}" '
             f'where "{r["column"]}" in ({keys}) group by "{r["column"]}"' for r in env.sql(REFERENCES_FK_SQL)]
    hits = env.sql("\nunion all ".join(parts)) if parts else []
    return [f"references: {h['ref']} {h['n']} rows point at {ids.get(h['id'], h['id'])}'s {schema}" for h in hits if int(h.get("n") or 0)]


def _resources(layers: list[Layer], schema: str, folder: Path):
    """The layers' resource files merged key by key, the upper layer winning; None when no layer has any."""
    from ..resources import Resources

    merged, found = Resources(folder), folder.is_dir()
    for x in layers:
        own = x.folder.parent.parent / "Resources" / f"{schema}.Entity"
        if not own.is_dir():
            continue
        found = True
        r = Resources(own)
        for culture, items in r.cultures.items():
            for key, value in items.items():
                merged.set(key, value, [culture])
                if r.attrs.get(culture, {}).get(key):
                    merged.attrs.setdefault(culture, {})[key] = r.attrs[culture][key]
    return merged if found else None


def merge_object(workspace: Path | str, schema: str, target: str | None = None, env=None, apply: bool = False) -> tuple[str, int]:
    """(text, exit code): the replacing layers of one object collapsed into one layer of the target package. Prints the plan,
    then the files it writes and deletes; writes them only with `apply`. Exit 1 (nothing written) on a conflict, siblings
    without `env`, a layer that stores a whole schema, or a site row that still points at a layer to remove."""
    import shutil

    from ..files import write_text
    from ..schema import Descriptor

    ctx = _context(workspace)
    plan = plan_schema(ctx, workspace, schema, OBJECT, env, target)
    lines, stops = list(plan["lines"]), []
    if plan["layers"] < 2:
        return "\n".join(lines), 0
    if plan["kind"] != "object" and not plan["skipped"]:
        stops.append(f"{schema} is a {plan['kind']}: merge writes objects only")
    if plan["skipped"]:
        stops.append("no target; name one with --target")
    stops += [f"{len(plan['conflicts'])} conflicts"] if plan["conflicts"] else []
    order = plan.get("order", [])
    if env is None and any(x.siblings for x in order):
        stops.append("siblings: their order is a guess without the site; run with -e")
    if plan.get("between"):
        stops.append(f"a layer on the site only folds after the target: {', '.join(plan['between'])}; "
                     "the merge would put the removed layers' lines before it")
    if env is not None and not stops:
        files = [x.package for x in layers_in_order(workspace, schema, None, OBJECT) if x.replacing]
        if files != [x.package for x in order]:
            lines.append(f"  order: the site folds {' > '.join(x.package for x in order)}; the files say {' > '.join(files)}; the site's is used")
    whole = [x.package for x in order if read_text(x.folder / "metadata.json")[0].lstrip().startswith("{")]
    if whole:
        stops.append(f"a layer stores the whole schema, not a diff: {', '.join(whole)}")
    target = plan["target"]
    removed = [x for x in order if x.package != target]
    if env is not None and not stops:
        refs = references(env, schema, [x.package for x in removed])
        lines += [f"  {r}" for r in refs]
        stops += [f"{len(refs)} references"] if refs else []
        if not refs:
            lines.append(f"  references: none to the {len(removed)} layers removed")
    if stops:
        return "\n".join(lines + [f"stopped: {'; '.join(stops)} - nothing written"]), 1

    root = Path(workspace)
    pkg = ctx.folders[target]
    source = next((x for x in order if x.package == target), order[-1])  # the UId rule
    package_uid = _descriptor(pkg / "descriptor.json").get("UId")
    if not package_uid:
        return "\n".join(lines + [f"stopped: {target}/descriptor.json has no UId - nothing written"]), 1
    folder = pkg / "Schemas" / schema
    writes: dict[Path, tuple[str, bool]] = {}
    meta, bom = read_text(source.folder / "metadata.json")
    renames = {}
    for x in order:
        if x is not source:
            renames[x.uid.lower()] = source.uid
        if x.package != target:
            renames[(_descriptor(ctx.folders[x.package] / "descriptor.json").get("UId") or "").lower()] = package_uid
    renames.pop("", None)
    writes[folder / "metadata.json"] = (merged_diff(order, source, package_uid, renames) + ("\r\n" if meta.endswith(("\n", "\r\n")) else ""), bom)
    for name, frm in (("descriptor.json", source), ("properties.json", order[-1]), (f"{schema}.cs", source)):
        if (frm.folder / name).is_file():
            writes[folder / name] = read_text(frm.folder / name)
    res = _resources(order, schema, pkg / "Resources" / f"{schema}.Entity")
    if res is not None:
        writes.update(res.files())
    gains = plan["gains"]
    if gains:
        entries = {}
        for x in removed:
            for d in _descriptor(ctx.folders[x.package] / "descriptor.json").get("DependsOn") or []:
                entries.setdefault(d["Name"], d)
        desc = Descriptor(pkg / "descriptor.json")
        data = desc.data
        desc.set("DependsOn", (data.get("DependsOn") or []) + [entries[g] for g in gains])
        writes[pkg / "descriptor.json"] = (desc.text, read_text(pkg / "descriptor.json")[1])
    deletes = [p for x in removed for p in (x.folder, x.folder.parent.parent / "Resources" / f"{schema}.Entity") if p.exists()]

    def rel(p: Path) -> str:
        try:
            return p.relative_to(root).as_posix()
        except ValueError:
            return p.as_posix()
    lines += [f"write {rel(p)}" for p in writes] + [f"delete {rel(p)}" for p in deletes]
    if apply:
        for p in deletes:
            shutil.rmtree(p)
        for p, (text, b) in writes.items():
            write_text(p, text, b)
    lines.append(f"{'merged' if apply else 'would merge'} {schema} into {target}: {len(order)} layers -> 1"
                 + ("" if apply else " (dry run; --apply writes)"))
    return "\n".join(lines), 0
