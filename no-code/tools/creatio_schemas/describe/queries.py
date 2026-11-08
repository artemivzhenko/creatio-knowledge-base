"""Query topics per schema kind. Each handler is `(item, name, filters) -> str` and prints only what was asked."""

from __future__ import annotations

import json

from ..dcm import DcmSchema
from ..entity import EntitySchema
from ..entity.catalog import column_flags
from ..files import ALL_DATA_VALUE_TYPES, DATA_VALUE_TYPES
from ..page import PageSchema
from ..process import ProcessSchema
from ..process.catalog import DIRECTION, USER_TASK_BY_UID, short_type
from ..rules import RuleSchema
from ..sqlscript import SqlScript
from ..usertask import UserTaskSchema
from .core import GenericItem, QueryError


def _match(value: str | None, wanted: str | None) -> bool:
    return wanted is None or (value or "").lower() == wanted.lower()


def _json(value) -> str:
    return json.dumps(value, indent=1, ensure_ascii=False)


def _need(name: str | None, what: str) -> str:
    if not name:
        raise QueryError(f"this topic needs a name: '{what} <name>'")
    return name


# -- every kind --------------------------------------------------------------- #

def q_files(item, name, f):
    base = getattr(item, "dir", None) or getattr(item, "package")
    paths = sorted(p for p in base.rglob("*") if p.is_file()) if hasattr(item, "dir") else []
    if isinstance(item, SqlScript):
        paths = sorted(p for p in (item.package / "SqlScripts" / item.name).rglob("*") if p.is_file())
    return "\n".join(f"{p.relative_to(item.package).as_posix():<60} {p.stat().st_size:>8} bytes" for p in paths) or "(no files)"


def q_resources(item, name, f):
    res = getattr(item, "resources", None)
    if res is None or not res.cultures:
        return "(no resources)"
    culture = f.get("culture")
    if culture:
        keys = res.ordered_keys(culture)
        return "\n".join(f"{k} = {res.get(k, culture)!r}" for k in keys) or f"(no {culture})"
    missing = res.missing()
    return "\n".join([f"cultures: {', '.join(sorted(res.cultures))}; {len(res.ordered_keys('en-US'))} keys in en-US"]
                     + [f"  missing in {c}: {len(ks)}" + (f" ({', '.join(ks[:8])}{', ...' if len(ks) > 8 else ''})" if ks else "") for c, ks in missing.items() if ks])


def q_resource(item, name, f):
    key = _need(name, "resource")
    res = item.resources
    return "\n".join(f"{c}: {res.get(key, c)!r}" for c in sorted(res.cultures) if res.get(key, c) is not None) or f"no key {key}"


COMMON = {"files": q_files, "resources": q_resources, "resource": q_resource}

# -- objects ------------------------------------------------------------------ #

def q_columns(e: EntitySchema, name, f):
    out = []
    for c in e.columns():
        t = ALL_DATA_VALUE_TYPES.get(c.get("S2"), c.get("S2"))
        flags = column_flags(c)
        if not _match(t, f.get("type")):
            continue
        if f.get("flag") and f["flag"] not in flags:
            continue
        if f.get("own") and (f["own"].lower() == "true") != e.is_own(c):
            continue
        out.append(e.describe_column(c).strip() + ("" if e.is_own(c) else "  base"))
    return "\n".join(out) or "(no matching column)"


def q_column(e: EntitySchema, name, f):
    c = e.column(_need(name, "column"))
    return e.describe_column(c).strip() + ("" if e.is_own(c) else "  base") + "\n" + _json(c)


def q_flags(e: EntitySchema, name, f):
    return "\n".join(line for line in e.describe().splitlines() if line.strip().startswith(("flags:", "display column:")))


def q_base(e: EntitySchema, name, f):
    info = e.base_info
    if not info:
        return f"{e.name} has no fetched base (own object with parent {e.parent_name})" if not e.replacing else "no base cached: run objects.py base"
    return "\n".join([f"base of {e.name}: {info.get('caption')!r} fetched {info.get('fetched')} from {info.get('env')}",
                      "chain: " + " <- ".join(f"{c.get('package')}" for c in info.get("chain", []))])


OBJECT = {"columns": q_columns, "column": q_column, "flags": q_flags, "base": q_base}

# -- processes ---------------------------------------------------------------- #

def _el_kind(e: dict) -> str:
    t = short_type(e).replace("ProcessSchema", "")
    return USER_TASK_BY_UID.get(e.get("J6"), e.get("J6", "?")) if t == "UserTask" else t


def q_p_elements(p: ProcessSchema, name, f):
    out = [f"{e['A2']:<30} {_el_kind(e):<24} {p.resources.get(f'BaseElements.{e['A2']}.Caption') or ''!r}"
           for e in p.nodes() if _match(_el_kind(e), f.get("kind"))]
    return "\n".join(out) or "(no matching element)"


def q_p_element(p: ProcessSchema, name, f):
    e = p.element(_need(name, "element"))
    lines = [f"{e['A2']} [{_el_kind(e)}] caption={p.resources.get(f'BaseElements.{e['A2']}.Caption')!r} at {e.get('BL3')}"]
    for par in p.element_params(e):
        if par.get("L8"):
            lines.append(f"    {par['A2']} = {p.describe_value(par['L8'])}")
    by_uid = {x["UId"]: x["A2"] for x in p.elements}
    for fl in p.flows():
        if fl.get("CI1") == e["UId"] or fl.get("CI2") == e["UId"]:
            cond = f" if {p.expressions.decode(fl['CI3'])}" if fl.get("CI3") not in (None, "null", "") else ""
            lines.append(f"    flow {fl['A2']}: {by_uid.get(fl.get('CI1'), '?')} -> {by_uid.get(fl.get('CI2'), '?')}{cond}")
    if short_type(e) == "ProcessSchemaScriptTask":
        lines.append(f"    script: {len(e.get('CH1', ''))} chars (ask 'script {e['A2']}')")
    return "\n".join(lines)


def q_p_params(p: ProcessSchema, name, f):
    out = [f"{x['A2']:<28} {DATA_VALUE_TYPES.get(x.get('L1'), x.get('L1')):<12} {DIRECTION.get(x.get('L12', 0)):<9} default={p.describe_value(x.get('L8'))}"
           for x in p.params if _match(DIRECTION.get(x.get("L12", 0)), f.get("direction"))]
    return "\n".join(out) or "(no parameters)"


def q_p_flows(p: ProcessSchema, name, f):
    by_uid = {x["UId"]: x["A2"] for x in p.elements}
    out = []
    for fl in p.flows():
        src, dst = by_uid.get(fl.get("CI1"), "?"), by_uid.get(fl.get("CI2"), "?")
        if not _match(src, f.get("from")) or not _match(dst, f.get("to")):
            continue
        cond = f" if {p.expressions.decode(fl['CI3'])}" if fl.get("CI3") not in (None, "null", "") else ""
        out.append(f"{fl['A2']:<28} {src} -> {dst}{cond}")
    return "\n".join(out) or "(no flows)"


def q_p_script(p: ProcessSchema, name, f):
    return p.get_script(_need(name, "script"))


PROCESS = {"elements": q_p_elements, "element": q_p_element, "params": q_p_params, "flows": q_p_flows, "script": q_p_script}

# -- rules -------------------------------------------------------------------- #

def q_rules(r: RuleSchema, name, f):
    out = []
    for rule in r.rules:
        if f.get("enabled") and (f["enabled"].lower() == "true") != rule.get("BR4", True):
            continue
        out.append(r.describe_rule(rule)[0])
    return "\n".join(out) or "(no rules)"


def q_rule(r: RuleSchema, name, f):
    return "\n".join(r.describe_rule(r.rule(_need(name, "rule"))))


RULES = {"rules": q_rules, "rule": q_rule}

# -- SQL scripts -------------------------------------------------------------- #

def q_body(s: SqlScript, name, f):
    return s.body


def q_deps(s: SqlScript, name, f):
    return "\n".join(f"{d.get('Name')} ({d.get('UId')})" for d in s.depends_on) or "(no dependencies)"


SQL = {"body": q_body, "deps": q_deps}

# -- Freedom UI pages --------------------------------------------------------- #

def q_sections(pg: PageSchema, name, f):
    out = []
    for sec, inner in pg.raw_sections().items():
        label = sec.replace("SCHEMA_", "").lower().replace("_", "-")
        size = len(inner.strip())
        out.append(f"{label:<24} {size:>7} chars" + ("  (empty)" if size <= 2 else ""))
    return "\n".join(out)


def q_pg_elements(pg: PageSchema, name, f):
    out = []
    for op in pg.elements():
        v = op.get("values") or {}
        if not _match(v.get("type"), f.get("type")) or not _match(op.get("parentName"), f.get("parent")):
            continue
        lc = v.get("layoutConfig") or {}
        where = (op.get("parentName") or "") + (f" r{lc['row']}c{lc['column']}" if "row" in lc else "")
        bound = v.get("control") or (v.get("items") if v.get("type") == "crt.DataGrid" else "")
        out.append(f"{op['name']:<30} {v.get('type', op.get('operation')):<22} {where:<34} {bound}")
    return "\n".join(out) or "(no matching element)"


def q_pg_element(pg: PageSchema, name, f):
    return _json(pg.element(_need(name, "element")))


def q_pg_attributes(pg: PageSchema, name, f):
    out = []
    for k, v in pg.attributes.items():
        path = ((v or {}).get("modelConfig") or {}).get("path", "")
        bound = path.startswith(pg.primary + ".")
        if f.get("bound") and (f["bound"].lower() == "true") != bound:
            continue
        extra = "collection" if (v or {}).get("isCollection") else ""
        out.append(f"{k:<30} {path:<30} {extra}")
    return "\n".join(out) or "(no attributes)"


def q_pg_attribute(pg: PageSchema, name, f):
    key = _need(name, "attribute")
    if key not in pg.attributes:
        raise QueryError(f"no attribute {key}; attributes: {', '.join(pg.attributes) or '-'}")
    return _json(pg.attributes[key])


def q_pg_sources(pg: PageSchema, name, f):
    return "\n".join(f"{k:<24} {(v.get('config') or {}).get('entitySchemaName', '?'):<24} scope={v.get('scope')}  attributes={', '.join((v.get('config') or {}).get('attributes', {})) or '-'}"
                     for k, v in pg.data_sources.items()) or "(no data sources)"


def q_pg_handlers(pg: PageSchema, name, f):
    hs = pg.handlers()
    return "\n".join(f"{req:<44} {len(text):>6} chars" for req, text in hs) or "(no handlers)"


def q_pg_handler(pg: PageSchema, name, f):
    req = _need(name, "handler")
    for r, text in pg.handlers():
        if r == req:
            return text
    raise QueryError(f"no handler for {req}; handlers: {', '.join(r for r, _ in pg.handlers()) or '-'}")


def q_pg_raw(section: str):
    def q(pg: PageSchema, name, f):
        text = pg.raw_sections().get(section, "").strip()
        return text if len(text) > 2 else "(empty)"
    return q


def q_pg_containers(pg: PageSchema, name, f):
    parents: dict[str, list[str]] = {}
    for op in pg.elements():
        parents.setdefault(op.get("parentName") or "(root)", []).append(op["name"])
    return "\n".join(f"{parent}: {', '.join(children)}" for parent, children in parents.items()) or "(no elements)"


def q_pg_find(pg: PageSchema, name, f):
    needle = _need(name, "find").lower()
    hits = []
    for sec, inner in pg.raw_sections().items():
        for i, line in enumerate(inner.splitlines(), 1):
            if needle in line.lower():
                hits.append(f"{sec.replace('SCHEMA_', '').lower()}:{i}: {line.strip()[:120]}")
    return "\n".join(hits[:60]) + (f"\n... {len(hits) - 60} more" if len(hits) > 60 else "") if hits else f"'{needle}' not found"


PAGE = {"sections": q_sections, "elements": q_pg_elements, "element": q_pg_element, "attributes": q_pg_attributes,
        "attribute": q_pg_attribute, "data-sources": q_pg_sources, "handlers": q_pg_handlers, "handler": q_pg_handler,
        "validators": q_pg_raw("SCHEMA_VALIDATORS"), "converters": q_pg_raw("SCHEMA_CONVERTERS"), "containers": q_pg_containers,
        "find": q_pg_find}

# -- dcm ---------------------------------------------------------------------- #

def _req(e: dict) -> str:
    return "required" if e.get("RequiredType") else "optional"


def q_d_stages(d: DcmSchema, name, f):
    out = []
    for s in d.stages:
        parent = d.stage_by_uid(s.get("ParentStageUId"))
        out.append(f"{s['A2']:<16} {d.stage_caption(s)!r:<34} {s.get('Color', ''):<8} record={s.get('StageRecordId')}"
                   + (f"  alternative of {parent['A2']}" if parent else "") + (f"  {len(s.get('Elements', []))} steps" if s.get("Elements") else ""))
    return "\n".join(out) or "(no stages)"


def q_d_stage(d: DcmSchema, name, f):
    s = d.stage(_need(name, "stage"))
    lines = [f"{s['A2']} {d.stage_caption(s)!r} {s.get('Color', '')} record={s.get('StageRecordId')} uid={s['UId']}"]
    for _, e in d.elements(s):
        lines.append(f"  step {e['A2']} {d.element_caption(s, e)!r} -> {d.calls(e)} [{_req(e)}]")
        lines += [f"      when {c['when']} -> {c['then']}" for c in d.conditions(e)]
    lines.append(f"  can move to: {', '.join(b for a, b in d.connections if a == s['A2']) or '(any)'}")
    lines.append(f"  reached from: {', '.join(a for a, b in d.connections if b == s['A2']) or '(any)'}")
    return "\n".join(lines)


def q_d_steps(d: DcmSchema, name, f):
    out = [f"{e['A2']:<18} in {s['A2']:<10} {d.element_caption(s, e)!r:<40} -> {d.calls(e)} [{_req(e)}]"
           for s, e in d.elements() if _match(s["A2"], f.get("stage"))]
    return "\n".join(out) or "(no steps)"


def q_d_step(d: DcmSchema, name, f):
    s, e = d.element(_need(name, "step"))
    lines = [f"{e['A2']} {d.element_caption(s, e)!r} in stage {s['A2']} -> {d.calls(e)} [{_req(e)}]"]
    prefix = f"Stages.{s['A2']}.Elements.{e['A2']}.ProcessFlowElement.Parameters."
    for p in (e.get("ProcessFlowElement") or {}).get("BP2", []):
        lines.append(f"  param {p['A2']}: {d.resources.get(prefix + p['A2'] + '.DisplayValue') or ''}")
    lines += [f"  when {c['when']} -> {c['then']}" for c in d.conditions(e)]
    return "\n".join(lines)


def q_d_moves(d: DcmSchema, name, f):
    out = [f"{a} -> {b}" for a, b in d.connections if _match(a, f.get("from")) and _match(b, f.get("to"))]
    return "\n".join(out) or "(no connections: any stage can follow any)"


def q_d_filter(d: DcmSchema, name, f):
    return d.describe_filter() + (("\n" + _json(d.filters)) if f.get("raw") == "true" and d.filters else "")


DCM = {"stages": q_d_stages, "stage": q_d_stage, "steps": q_d_steps, "step": q_d_step, "moves": q_d_moves, "filter": q_d_filter}


# -- user task ---------------------------------------------------------------- #

def q_u_params(u: UserTaskSchema, name, f):
    out = [u.describe_param(p) for p in u.params if _match(DIRECTION.get(p.get("L12", 0)), f.get("direction"))]
    return "\n".join(out) or "(no parameters)"


def q_u_param(u: UserTaskSchema, name, f):
    p = u.param(_need(name, "param"))
    return u.describe_param(p) + "\n" + _json(p)


def q_u_methods(u: UserTaskSchema, name, f):
    return "\n".join(u.methods()) or "(no .cs file)"


def q_u_method(u: UserTaskSchema, name, f):
    return u.method(_need(name, "method"))


def q_u_source(u: UserTaskSchema, name, f):
    return u.source or "(no .cs file)"


USERTASK = {"params": q_u_params, "param": q_u_param, "methods": q_u_methods, "method": q_u_method, "source": q_u_source}


TOPICS = {EntitySchema: OBJECT, ProcessSchema: PROCESS, RuleSchema: RULES, SqlScript: SQL, PageSchema: PAGE, DcmSchema: DCM, UserTaskSchema: USERTASK, GenericItem: {}}


def topics_of(item) -> dict:
    return {**TOPICS.get(type(item), {}), **COMMON}


def answer(item, topic: str, name: str | None, filters: dict[str, str]) -> str:
    table = topics_of(item)
    if topic in ("topics", "help", "?"):
        return f"{type(item).__name__} topics: " + ", ".join(sorted(table))
    if topic not in table:
        raise QueryError(f"unknown topic '{topic}' for a {type(item).__name__}; topics: {', '.join(sorted(table))}")
    return table[topic](item, name, filters)
