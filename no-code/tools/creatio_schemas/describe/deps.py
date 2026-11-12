"""Typed dependencies of a package item: what it builds on, how, and how surely (the edges the index stores).

An edge goes from the item to another schema: `to_kind to_name [to_uid] via ref detail`.

- `via` says the relation, one closed word per kind: object `parent`, `lookup`; process `signal`, `read-data`,
  `add-data`, `modify-data`, `delete-data`, `sub-process`, `user-task`, `param`; dcm `entity`, `step`; rules
  `target`, `column`; page `parent`, `data-source`, `module`; classic `parent`, `entity`, `detail`, `mixin`, `module`,
  `lookup`, `rule`; data `binds`; sql `after`, `table`; csharp `listener`, `esq`, `query`, `string`; user-task `param`.
  A process script task's code gives the csharp words, the element name first in `detail`.
- `ref` says how sure the edge is: `uid` (the metadata stores the UId), `name` (a name resolved in a context that
  names the object: the page's data source, the listener's SchemaName), `text` (a word in code or SQL - a suspicion,
  reserved for the text extractors).
- `detail` lists the columns involved. A column is resolved against the context object's effective columns (own,
  replacing copies, stock parents, the base cache from the environment): `Name` found there is that object's
  column, not a same-named one elsewhere; a name the chain cannot show ends with `?`.

Reverse edges (who depends on X) are not stored: the index answers them by scanning the stored ones.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..entity.catalog import STOCK_ENTITIES, stock_columns
from ..files import is_uid
from ..workspace import BASE_COLUMNS, Workspace

MANAGER_KIND = {"EntitySchemaManager": "object", "ProcessSchemaManager": "process", "DcmSchemaManager": "dcm",
                "ClientUnitSchemaManager": "page", "ProcessUserTaskSchemaManager": "user-task", "SourceCodeSchemaManager": "source",
                "AddonSchemaManager": "rules"}
DATA_TASKS = {"ReadDataUserTask": "read-data", "AddDataUserTask": "add-data", "ChangeDataUserTask": "modify-data", "DeleteDataUserTask": "delete-data"}
REF_RANK = {"uid": 0, "name": 1, "text": 2}


@dataclass
class Edge:
    to_kind: str
    to_name: str
    to_uid: str | None
    via: str
    ref: str = "uid"
    detail: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = {"kind": self.to_kind, "name": self.to_name, "via": self.via, "ref": self.ref}
        if self.to_uid:
            d["uid"] = self.to_uid
        if self.detail:
            d["detail"] = self.detail
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(d["kind"], d["name"], d.get("uid"), d["via"], d.get("ref", "uid"), list(d.get("detail", [])))

    def line(self) -> str:
        text = f"{self.to_kind} {self.to_name}  {self.via}"
        if self.detail:
            text += ": " + ", ".join(self.detail)
        return text + ("" if self.ref == "uid" else f"  [{self.ref}]")


class Resolver:
    """Names and UIds of the workspace plus the stock objects (entity/catalog.py: 8.3.2); columns through the entity's
    effective schema, else the stock catalogue's columns."""

    def __init__(self, workspace: Workspace):
        self.ws = workspace
        self._columns: dict[str, dict[str, str | None] | None] = {}

    def schema(self, name_or_uid: str | None, manager: str) -> tuple[str, str | None]:
        """(name, base UId or None) of a schema; a stock object answers from the asset; unknown keeps the text."""
        if not name_or_uid:
            return "?", None
        hits = self.ws.find(name_or_uid, manager)
        if hits:
            return hits[0]["name"], hits[0]["base"]
        if manager == "EntitySchemaManager":
            key = name_or_uid.lower()
            for name, uid in STOCK_ENTITIES.items():
                if key in (name.lower(), uid):
                    return name, uid
        return name_or_uid, (name_or_uid.lower() if is_uid(name_or_uid) else None)

    def entity(self, name_or_uid: str | None) -> tuple[str, str | None]:
        return self.schema(name_or_uid, "EntitySchemaManager")

    def columns(self, entity: str) -> dict[str, str | None] | None:
        """name -> column UId of every effective column of an entity; None when nothing of it is readable here."""
        if entity not in self._columns:
            out: dict[str, str | None] | None = None
            own = [s for s in self.ws.find(entity, "EntitySchemaManager") if s["uid"] == s["base"]]
            if own:
                from ..entity import EntitySchema
                try:
                    schema = EntitySchema(own[0]["dir"].parent.parent, own[0]["name"])
                    out = {c["A2"]: (c.get("UId") or "").lower() or None for c in schema.columns()}
                    if schema.effective is None:  # the parent is unknown here: the inherited base columns still exist
                        out = {**{n: None for n in BASE_COLUMNS}, **out}
                except (OSError, ValueError, KeyError):
                    out = None
                if out is not None:  # replacing copies in other packages add columns of their own
                    out = {**out, **{n: u for n, u in self.ws.column_uids(entity).items() if n not in out}}
            copies = self.ws.find(entity, "EntitySchemaManager")
            if out is None and copies:  # replacing copies only: their columns, the base ones, and the base fetched from the environment when cached
                from ..entity.hierarchy import load_base
                cached = load_base(copies[0]["dir"].parent.parent, entity)
                base = ({c["A2"]: (c.get("UId") or "").lower() or None for c in cached.get("schema", {}).get("D2", [])} if cached
                        else stock_columns(entity) or {})  # no fetched base: the stock catalogue's columns
                out = {**{n: None for n in BASE_COLUMNS}, **base, **self.ws.column_uids(entity)}
            if out is None and stock_columns(entity) is not None:  # no copy in the workspace: a stock object's columns from the catalogue
                out = dict(stock_columns(entity))
            self._columns[entity] = out
        return self._columns[entity]

    def column_names(self, entity: str, names: list[str]) -> list[str]:
        """The names as the detail shows them: a column the entity's chain cannot show ends with `?`."""
        known = self.columns(entity)

        def seen(n: str) -> bool:  # `StatusId` is the platform's Id form of the lookup column `Status`
            head = n.split(".")[0]
            if head.startswith("["):  # `[Detail:Column].X`: the records of another object pointing here - that object's column
                target = head[1:].split(":")[0]
                return self.entity(target)[1] is not None
            return head in known or (head.endswith("Id") and head[:-2] in known)

        return [n if known is not None and seen(n) else n + "?" for n in names if n and n != "null"]

    def column_name_of(self, entity: str, uid: str) -> str:
        known = self.columns(entity) or {}
        return next((n for n, u in known.items() if u == uid.lower()), uid)

    def object_named(self, word: str, stock: bool = True, exact: bool = True) -> tuple[str, str | None] | None:
        """(name, base UId) of the workspace object - or, with `stock`, the stock one - called `word` (any case unless
        `exact`); None for any other word."""
        if not hasattr(self, "_objects"):  # built once: the text extractors ask for every string and table name
            self._own = {s["name"].lower(): (s["name"], s["base"]) for s in self.ws.schemas if s["manager"] == "EntitySchemaManager"}
            self._objects = {**{n.lower(): (n, u) for n, u in STOCK_ENTITIES.items()}, **self._own}
        hit = (self._objects if stock else self._own).get(word.lower())
        return hit if hit and (not exact or hit[0] == word) else None


# -- extractors, one per kind ------------------------------------------------- #

def _merge(edges: list[Edge]) -> list[Edge]:
    out: dict[tuple, Edge] = {}
    for e in edges:
        key = (e.to_kind, e.to_name.lower(), e.via)
        if key in out:
            out[key].detail += [d for d in e.detail if d not in out[key].detail]
            if REF_RANK.get(e.ref, 3) < REF_RANK.get(out[key].ref, 3):  # uid over name over text
                out[key].ref = e.ref
            out[key].to_uid = out[key].to_uid or e.to_uid
        else:
            out[key] = Edge(e.to_kind, e.to_name, e.to_uid, e.via, e.ref, list(e.detail))
    return list(out.values())


def _cols(r: Resolver, entity: str, names: list[str]) -> list[str]:
    """Column names once each, checked on the entity; `XId` of a lookup column `X` (what code reads) counts as `X`."""
    known = r.columns(entity) or {}
    out = []
    for n in names:
        n = n[:-2] if n.endswith("Id") and n not in known and n[:-2] in known else n
        if n and n not in out:
            out.append(n)
    return r.column_names(entity, out)


# -- text extractors: words in code and SQL (a name the code passes is not a UId the metadata stores) ------------ #

_LIT = r'"(?P<lit> +)"'  # a string literal of the masked code: its offsets point at the text
CODE_ROOTS = [  # (regex over the masked code, via): the literal names the object
    (re.compile(r"\bnew\s+EntitySchemaQuery\s*\([^;\"]*?,\s*" + _LIT + r"\s*\)"), "esq"),
    (re.compile(r"(?P<recv>[\w.]*)\s*\.\s*GetInstanceByName\s*\(\s*" + _LIT + r"\s*\)"), "esq"),
    (re.compile(r"\.\s*(?:From|Into|\w*Join)\s*\(\s*" + _LIT + r"\s*\)"), "query"),
    (re.compile(r"\bnew\s+Update\s*\([^;\"]*?,\s*" + _LIT), "query"),
]
_QUERY_COLUMNS = [re.compile(r"\.\s*Column\s*\(\s*(?:\"[^\"]*\"\s*,\s*)?" + _LIT + r"\s*\)"), re.compile(r"\.\s*Set\s*\(\s*" + _LIT)]
_ENTITY_COLUMN = re.compile(r"\b(?:GetTyped(?:Old)?ColumnValue\s*<[^<>()]*>|GetColumnValue|SetColumnValue|IsColumnValueLoaded)\s*\(\s*" + _LIT)
_OTHER_MANAGER = re.compile(r"(?:Process|ClientUnit|SourceCode|ProcessUserTask)\w*$")


def _block_end(masked: str, pos: int) -> int:
    depth = 0
    for i in range(pos, len(masked)):
        depth += {"{": 1, "}": -1}.get(masked[i], 0)
        if depth < 0:
            return i
    return len(masked)


def _code(text: str, r: Resolver, listeners: list[tuple[str, str | None, int, int]] = ()) -> list[Edge]:
    """Edges of C# code: objects an ESQ / GetInstanceByName / Select-Update-Insert-Delete names (ref name) with the columns
    the query names, the columns a listener reads or sets on its own object (`listeners`: name, uid, span), and a bare
    string that is a workspace object's name (ref text)."""
    from ..text import mask
    masked = mask(text)
    lit = lambda m: text[m.start("lit"):m.end("lit")]  # noqa: E731
    edges, used = [], set()
    for rx, via in CODE_ROOTS:
        for m in rx.finditer(masked):
            word = lit(m)
            if not re.fullmatch(r"\w+", word) or ("recv" in rx.groupindex and _OTHER_MANAGER.search(m.group("recv"))):
                continue
            used.add(m.start("lit"))
            start = max(masked.rfind(c, 0, m.start()) for c in ";{}") + 1
            stop = masked.find(";", m.end())
            stop = len(masked) if stop < 0 else stop
            cols = []
            if via == "esq":  # `var esq = new EntitySchemaQuery(...)`: esq.AddColumn("X") until the block ends
                var = re.search(r"(\w+)\s*=\s*$", masked[start:m.start()])
                if var:
                    rx_col = re.compile(rf"\b{var.group(1)}\s*\.\s*(?:AddColumn|Column)\s*\(\s*" + _LIT)
                    hits = list(rx_col.finditer(masked, m.end(), _block_end(masked, m.end())))
                    used.update(h.start("lit") for h in hits)
                    cols = [lit(h) for h in hits]
            elif sum(1 for rr, v in CODE_ROOTS if v == "query" for _ in rr.finditer(masked, start, stop)) == 1:  # one table: its columns
                hits = [h for rc in _QUERY_COLUMNS for h in rc.finditer(masked, start, stop)]
                used.update(h.start("lit") for h in hits)
                cols = [lit(h) for h in sorted(hits, key=lambda h: h.start())]
            name, uid = r.entity(word)
            edges.append(Edge("object", name, uid, via, "name", _cols(r, name, cols)))
    for name, uid, a, b in listeners:
        # shortcut: every Get/SetColumnValue in the listener class counts for its object, whatever entity the receiver is; a `?` there may be another entity's column - a data-flow reader would separate them
        hits = list(_ENTITY_COLUMN.finditer(masked, a, b))
        used.update(h.start("lit") for h in hits)
        edges.append(Edge("object", name, uid, "listener", "name", _cols(r, name, [lit(h) for h in hits])))
    reached = {e.to_name.lower() for e in edges}
    for m in re.finditer(_LIT, masked):
        hit = None if m.start("lit") in used else r.object_named(lit(m), stock=False)
        if hit and hit[0].lower() not in reached:
            reached.add(hit[0].lower())
            edges.append(Edge("object", hit[0], hit[1], "string", "text"))
    return edges


_SQL_NOISE = re.compile(r"--[^\n]*|/\*.*?\*/|'(?:[^']|'')*'", re.S)
_SQL_TABLE = re.compile(r"\b(?:from|join|update|into|alter\s+table(?:\s+if\s+exists)?)\s+(?:only\s+)?(?:(?:\"\w+\"|\[\w+\]|\w+)\s*\.\s*)?"
                        r"(?:\"(\w+)\"|\[(\w+)\]|(\w+))", re.I)


def _sql_tables(body: str, r: Resolver) -> list[Edge]:
    """Tables after from / join / update / insert into / delete from / alter table that are objects (a CTE or a temp table is not)."""
    edges = []
    for m in _SQL_TABLE.finditer(_SQL_NOISE.sub(" ", body)):
        word = m.group(1) or m.group(2) or m.group(3)
        hit = r.object_named(word, exact=m.group(3) is None)  # an unquoted PostgreSQL name folds case
        if hit:
            edges.append(Edge("object", hit[0], hit[1], "table", "text"))
    return edges


def _object(item, r: Resolver) -> list[Edge]:
    edges = []
    if item.parent_name or item.parent_uid:
        name, uid = r.entity(item.parent_uid or item.parent_name)
        edges.append(Edge("object", name if name != "?" else item.parent_name, uid, "parent"))
    for c in item.own_columns() if item.replacing else item.columns():
        if c.get("S4"):
            name, uid = r.entity(c["S4"])
            edges.append(Edge("object", name, uid, "lookup", "uid", [c["A2"]]))
    return edges


def _process(item, r: Resolver) -> list[Edge]:
    from ..process.catalog import USER_TASK_BY_UID, short_type
    from ..process.schema import SIGNAL_KEYS
    edges = []
    for el in item.nodes():
        cls = short_type(el)
        keys = SIGNAL_KEYS.get(cls)
        if keys and el.get(keys["record"]) and is_uid(el.get(keys["entity"]) or ""):
            name, uid = r.entity(el[keys["entity"]])
            try:
                cols = [r.column_name_of(name, u) for u in json.loads(el.get(keys["columns"]) or "[]")]
            except ValueError:
                cols = []
            edges.append(Edge("object", name, uid, "signal", "uid", cols))
        elif cls == "ProcessSchemaScriptTask" and el.get("CH1"):
            edges += [Edge(e.to_kind, e.to_name, e.to_uid, e.via, e.ref, [el["A2"]] + e.detail) for e in _code(el["CH1"], r)]
        elif cls == "ProcessSchemaSubProcess" and el.get("CK4"):
            name, uid = r.schema(el["CK4"], "ProcessSchemaManager")
            edges.append(Edge("process", name, uid, "sub-process", "uid", [el["A2"]]))
        elif cls == "ProcessSchemaUserTask":
            task = USER_TASK_BY_UID.get((el.get("J6") or "").lower()) or el.get("J6")
            via = DATA_TASKS.get(task)
            if via:
                for p in item.element_params(el):
                    value = (p.get("L8") or {}).get("GS2") if p["A2"] in ("EntitySchemaId", "EntitySchemaUId") else p.get("L9") if p["A2"] == "ResultEntity" else None
                    if is_uid(value or ""):
                        name, uid = r.entity(value)
                        edges.append(Edge("object", name, uid, via, "uid", [el["A2"]]))
                        break
            else:
                hits = r.ws.find(el.get("J6") or "", "ProcessUserTaskSchemaManager")
                if hits:
                    edges.append(Edge("user-task", hits[0]["name"], hits[0]["base"], "user-task", "uid", [el["A2"]]))
    for p in item.params:
        if is_uid(p.get("L9") or ""):
            name, uid = r.entity(p["L9"])
            edges.append(Edge("object", name, uid, "param", "uid", [p["A2"]]))
    return edges


def _dcm(item, r: Resolver) -> list[Edge]:
    edges = []
    if item.entity_uid:
        name, uid = r.entity(item.entity_uid)
        edges.append(Edge("object", name, uid, "entity", "uid", [item.stage_column] if item.stage_column else []))
    for stage, el in item.elements():
        called = (el.get("ProcessFlowElement") or {}).get("CK4")
        if called:
            name, uid = r.schema(called, "ProcessSchemaManager")
            edges.append(Edge("process", name, uid, "step", "uid", [el["A2"]]))
    return edges


def _rules(item, r: Resolver) -> list[Edge]:
    manager = item.manager
    name, uid = r.schema(item.target_uid, manager)
    if name == item.target_uid and item.target:
        name = item.target
    edges = [Edge(MANAGER_KIND.get(manager, "schema"), name, uid, "target")]
    from ..rules.model import T_ATTR, walk
    used = [(e["BRX1"], e.get("BRX2")) for rule in item.rules for e in walk(rule) if e.get("JI0") == T_ATTR and e.get("BRX1")]
    if manager == "EntitySchemaManager":
        if used:
            edges.append(Edge("object", name, uid, "column", "name", _cols(r, name, [n for n, _ in used])))
        return edges
    attrs, sources, _ = r.ws.page_model(name)  # a page rule names attributes: their data source's object is the target
    by_entity: dict[str, list[str]] = {}
    for attr, scope in used:
        if scope not in (None, "null") and scope in sources:  # an attribute of a list data source is its column
            by_entity.setdefault(sources[scope], []).append(attr)
        elif "." in (attrs.get(attr) or "") and attrs[attr].split(".", 1)[0] in sources:
            ds, column = attrs[attr].split(".", 1)
            by_entity.setdefault(sources[ds], []).append(column)
    for entity, cols in by_entity.items():
        ename, euid = r.entity(entity)
        edges.append(Edge("object", ename, euid, "column", "name", _cols(r, ename, cols)))
    return edges


def _page(item, r: Resolver) -> list[Edge]:
    edges = []
    parent = item.descriptor.data.get("Parent") or {}
    if parent.get("UId"):
        name, uid = r.schema(parent["UId"], "ClientUnitSchemaManager")
        edges.append(Edge("page", parent.get("Name") or name, uid, "parent"))
    # A data source declares its own attributes with entity paths (`QSAccountName: {path: "QSAccount.Name"}`, a lookup's
    # sub-column under a concatenated name); a page attribute's `PDS.X` names one of those or a plain column.
    def declared(cfg) -> dict:  # `{Name: {path}}`, or a list of one-key dicts of that shape (both occur in designer-made pages)
        attrs = (cfg.get("config") or {}).get("attributes") or {}
        if isinstance(attrs, list):
            attrs = {k: v for a in attrs if isinstance(a, dict) for k, v in a.items()}
        return {n: (a if isinstance(a, dict) else {}).get("path") or n for n, a in attrs.items()} if isinstance(attrs, dict) else {}

    ds_paths = {ds: declared(cfg) for ds, cfg in item.data_sources.items()}
    columns: dict[str, list[str]] = {ds: list(dict.fromkeys(paths.values())) for ds, paths in ds_paths.items()}
    for attr, cfg in item.attributes.items():
        path = ((cfg or {}).get("modelConfig") or {}).get("path") or ""
        if "." in path:
            ds, column = path.split(".", 1)
            column = ds_paths.get(ds, {}).get(column, column)
            if column not in columns.setdefault(ds, []):
                columns[ds].append(column)
    for ds, cfg in item.data_sources.items():
        entity = (cfg.get("config") or {}).get("entitySchemaName")
        if entity:
            name, uid = r.entity(entity)
            edges.append(Edge("object", name, uid, "data-source", "name", [ds] + r.column_names(name, columns.get(ds, []))))
    try:  # SCHEMA_DEPS: the modules the page loads; a workspace client schema among them is an edge
        modules = json.loads(item.raw_sections().get("SCHEMA_DEPS") or "[]")
    except ValueError:
        modules = []
    for dep in modules if isinstance(modules, list) else []:
        if isinstance(dep, str) and dep != item.name and r.ws.find(dep, "ClientUnitSchemaManager"):
            name, uid = r.schema(dep, "ClientUnitSchemaManager")
            edges.append(Edge("page", name, uid, "module", "name"))
    return edges


def _classic(item, r: Resolver) -> list[Edge]:
    edges = []
    if item.parent:
        name, uid = r.schema(item.parent, "ClientUnitSchemaManager")
        edges.append(Edge("page", name, uid, "parent", "uid" if uid else "name"))
    if item.entity:
        name, uid = r.entity(item.entity)
        edges.append(Edge("object", name, uid, "entity", "name"))
    for key, props in item.details().items():
        if not isinstance(props, dict):
            continue
        schema = props.get("schemaName")
        if schema:
            name, uid = r.schema(schema, "ClientUnitSchemaManager")
            cols = re.findall(r'(?:detailColumn|masterColumn)"?\s*:\s*"([^"]+)"', str(props.get("filter", "")))
            edges.append(Edge("page", name, uid, "detail", "name", [key] + cols))
        if props.get("entitySchemaName"):
            name, uid = r.entity(props["entitySchemaName"])
            edges.append(Edge("object", name, uid, "detail", "name", [key]))
    for key, module in item.mixins().items():
        short = str(module).split(".")[-1]
        name, uid = r.schema(short, "ClientUnitSchemaManager")
        edges.append(Edge("page", name, uid, "mixin", "name", [key]))
    for dep in item.dependencies:
        if r.ws.find(dep, "ClientUnitSchemaManager") and dep != item.name:
            name, uid = r.schema(dep, "ClientUnitSchemaManager")
            edges.append(Edge("page", name, uid, "module", "name"))
    attrs = item.attributes()
    for key, props in attrs.items():
        if isinstance(props, dict) and props.get("referenceSchemaName"):
            name, uid = r.entity(props["referenceSchemaName"])
            edges.append(Edge("object", name, uid, "lookup", "name", [key]))
    cols = []
    for section in ("businessRules", "rules"):  # keyed by the column the rules bind; conditions name more as `attribute: "X"`
        span = item.sections.get(section)
        if span and item.masked[span[0]] == "{":
            cols += list(item._object(span[0])) + re.findall(r"""\battribute["']?\s*:\s*["']([\w.]+)["']""", item.body[span[0]:span[1]])
    virtual = {k for k, p in attrs.items() if isinstance(p, dict) and "VIRTUAL" in str(p.get("type", ""))}
    cols = [c for c in cols if c not in virtual]
    entity = (item.entity or next((a.entity for a in item._ancestors() if a.entity), None)) if cols else None
    if entity:
        name, uid = r.entity(entity)
        edges.append(Edge("object", name, uid, "rule", "name", _cols(r, name, cols)))
    return edges


def _data(item, r: Resolver) -> list[Edge]:
    name, uid = r.entity(item.schema_name)
    return [Edge("object", name, uid, "binds", "name", list(item.columns))] if item.schema_name else []


def _sql(item, r: Resolver) -> list[Edge]:
    return ([Edge("sql", d.get("Name") or d.get("UId", "?"), (d.get("UId") or "").lower() or None, "after") for d in item.depends_on]
            + _sql_tables(item.body, r))


def _usertask(item, r: Resolver) -> list[Edge]:
    edges = []
    for p in item.params:
        if is_uid(p.get("L9") or ""):
            name, uid = r.entity(p["L9"])
            edges.append(Edge("object", name, uid, "param", "uid", [p["A2"]]))
    return edges


def _csharp(item, r: Resolver) -> list[Edge]:
    edges, listeners = [], []
    for t in item.types:
        m = re.match(r"entity event listener of (\S+)", t.get("role", ""))
        if m:
            name, uid = r.entity(m.group(1))
            edges.append(Edge("object", name, uid, "listener", "name", [t["name"]]))
            listeners.append((name, uid, t["start"], t["stop"]))
    return edges + ([] if item.generated else _code(item.text, r, listeners))  # generated code names every column of its own schema


EXTRACTORS = {"object": _object, "process": _process, "dcm": _dcm, "rules": _rules, "page": _page,
              "classic": _classic, "data": _data, "sql": _sql, "user-task": _usertask, "csharp": _csharp, "source": _csharp}


def deps_of(item, resolver: Resolver, kind: str) -> list[Edge]:
    """The typed edges of an item of the given kind; a kind without an extractor has none."""
    extract = EXTRACTORS.get(kind)
    return _merge(extract(item, resolver)) if extract else []


# -- answering over the workspace --------------------------------------------- #

def dependencies(path: Path | str, name: str, direction: str = "both", kind: str = "", via: str = "", limit: int | None = None) -> str:
    """`depends on` and `dependents` of a schema over every package of the workspace, from the indexes."""
    from .core import DEFAULT_LIMIT, cut
    from .index import PackageIndex, packages_of, _unreadable_line
    limit = DEFAULT_LIMIT if limit is None else limit
    indexes = [PackageIndex(p) for p in packages_of(path)]
    for idx in indexes:
        idx.refresh()
    key = name.lower()
    own = [(idx, n, e) for idx in indexes for n, e in idx.entries() if n.lower() == key]
    if not own:
        return f"no schema named {name} in {', '.join(p.name for p in packages_of(path))}"
    out = []
    for idx, n, e in own:
        out.append(f"{n}  {e.get('kind', 'data')} in {idx.data.get('package', idx.package.name)}")
    if direction in ("both", "out"):
        edges = [Edge.from_dict(d) for _, _, e in own for d in e.get("deps", [])]
        edges = [e for e in edges if (not kind or e.to_kind == kind) and (not via or e.via == via)]
        out.append("depends on:" if edges else "depends on: nothing typed" + (f" of kind {kind}" if kind else ""))
        out += cut([f"  {e.line()}" for e in sorted(edges, key=lambda e: (e.to_kind, e.to_name.lower(), e.via))], limit)
    if direction in ("both", "in"):
        users = []
        for idx in indexes:
            for from_kind, from_name, e in idx.dependents(name):
                if (not kind or from_kind == kind) and (not via or e.via == via):
                    where = "" if any(idx is o for o, _, _ in own) else f", {idx.data.get('package', idx.package.name)}"
                    users.append(f"  {from_kind} {from_name}{where}  {e.via}" + (": " + ", ".join(e.detail) if e.detail else "") + ("" if e.ref == "uid" else f"  [{e.ref}]"))
        out.append("dependents:" if users else "dependents: nothing typed in the workspace" + (f" of kind {kind}" if kind else ""))
        out += cut(sorted(users), limit)
    return "\n".join(out + _unreadable_line(indexes))


def impact(path: Path | str, schemas: list[str], tasks: Path | str | None = None, current: str | None = None,
           md: bool = False, limit: int | None = None, kind: str = "") -> tuple[str, int]:
    """The dependents of the schemas a task changes, with the other active tasks that change or affect them.

    Returns (text, conflicts): a conflict is a schema of the list, or one of its dependents, that another active task
    changes (its schemas.json `schemas`). `md` gives the `## Impact` table of plan.md plus the `affects:` line for
    schemas.json; the plain form is one block per schema. `kind` keeps only the dependents of that kind (page,
    process, rules ...) - a lookup of a hundred dependents is read one kind at a time."""
    from ..tasks import active_locks
    from .core import DEFAULT_LIMIT, cut
    from .index import PackageIndex, packages_of
    limit = DEFAULT_LIMIT if limit is None else limit
    indexes = [PackageIndex(p) for p in packages_of(path)]
    for idx in indexes:
        idx.refresh()
    changes, affects = active_locks(tasks, current) if tasks else ({}, {})
    rows, conflicts, all_dependents = [], 0, []
    for schema in schemas:
        key = schema.lower()
        own = [(idx, n, e) for idx in indexes for n, e in idx.entries() if n.lower() == key]
        head = f"{own[0][1]}  {own[0][2].get('kind', 'data')} in {own[0][0].data.get('package', own[0][0].package.name)}" if own else f"{schema}  (not in the workspace)"
        notes = []
        if key in changes:
            notes.append(f"CONFLICT: task {changes[key]} changes it")
            conflicts += 1
        if key in affects:
            notes.append(f"task {affects[key]} depends on it")
        dependents = sorted({(fk, fn, e.via) for idx in indexes for fk, fn, e in idx.dependents(schema) if not kind or fk == kind},
                            key=lambda d: (d[0], d[1].lower(), d[2]))
        lines = []
        for fk, fn, via in dependents:
            mark = f" - task {changes[fn.lower()]} changes it" if fn.lower() in changes else ""
            if mark:
                conflicts += 1
            lines.append(f"{fk} {fn} ({via}){mark}")
            if fn not in all_dependents and fn.lower() not in {s.lower() for s in schemas}:  # what the task changes is not what it affects
                all_dependents.append(fn)
        rows.append((head, notes, lines))
    out = []
    if md:
        out += ["## Impact", "", "| Schema | Dependents | Other active tasks |", "|---|---|---|"]
        for head, notes, lines in rows:
            name = head.split("  ")[0]
            others = "; ".join(notes + [l.split(" - ")[1] + f" ({l.split(' (')[0]})" for l in lines if " - task " in l]) or "-"
            out.append(f"| `{name}` | {', '.join(l.split(' - task ')[0] for l in cut(lines, limit)) or 'none typed'} | {others} |")
    else:
        for head, notes, lines in rows:
            out.append(head + (f"  [{'; '.join(notes)}]" if notes else ""))
            out.append(f"  dependents ({len(lines)}):" if lines else "  dependents: none typed in the workspace")
            out += ["    " + l for l in cut(lines, limit)]
    out.append("")
    out.append(f"affects: {', '.join(all_dependents) if all_dependents else '(none)'}")
    out.append(f"{len(all_dependents)} dependents of {len(schemas)} schema(s); {conflicts} conflict(s) with other active tasks"
               + ("" if tasks else " (no tasks folder given: locks not checked)"))
    return "\n".join(out), conflicts
