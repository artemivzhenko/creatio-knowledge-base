"""Compare an object's metadata with its table on an environment (PostgreSQL): what a push should have applied.

    columns      every column of the object exists (a lookup as <Name>Id) with a type of its family
    indexes      an indexed column has an index
    foreign keys a lookup has one unless it is a weak reference; cascade delete shows as ON DELETE CASCADE
    rights       admin-records needs the table Sys<Object>Right
    deactivation the platform adds the column RecordInactive
"""

from __future__ import annotations

from ..clio import Clio
from ..files import ALL_DATA_VALUE_TYPES
from .schema import EntitySchema

LOOKUPS = {"Lookup", "ImageLookup"}
# data value type -> PostgreSQL types it is stored as
PG_TYPES = {"Integer": {"integer"}, "Boolean": {"boolean"}, "Date": {"date"}, "DateTime": {"timestamp without time zone"},
            "Time": {"time without time zone"}, "Lookup": {"uuid"}, "Guid": {"uuid"}, "Binary": {"bytea"}, "Image": {"bytea"},
            "ImageLookup": {"uuid"}}
for _t in ALL_DATA_VALUE_TYPES.values():
    if _t.startswith(("Float", "Money", "Decimal")):
        PG_TYPES[_t] = {"numeric"}
    elif _t.endswith("Text") or _t in ("Color", "Text"):
        PG_TYPES.setdefault(_t, {"character varying", "text"})


from ..records import quote as _quote  # noqa: E402


def check(entity: EntitySchema, clio: Clio) -> list[tuple[str, str]]:
    """[(status, message)]: status is ok, missing, differs or note."""
    eff = entity.effective
    if eff is None:
        raise ValueError(f"the parent of {entity.name} is not known here, so the expected columns are not either")
    table = entity.name
    q = _quote(table)
    # every branch cast to text: a UNION takes the first branch's types, and sql_identifier would cut indexdef at 63 chars
    rows = clio.sql(f"""
select 'column'::text k, column_name::text a, data_type::text b, ''::text c from information_schema.columns where table_schema = 'public' and table_name = {q}
union all select 'index', indexname, indexdef, '' from pg_indexes where schemaname = 'public' and tablename = {q}
union all select 'fk', kcu.column_name, ccu.table_name, rc.delete_rule from information_schema.key_column_usage kcu
  join information_schema.referential_constraints rc on rc.constraint_name = kcu.constraint_name
  join information_schema.constraint_column_usage ccu on ccu.constraint_name = kcu.constraint_name
  where kcu.table_schema = 'public' and kcu.table_name = {q}
union all select 'table', table_name, table_type, '' from information_schema.tables where table_schema = 'public' and table_name in ({q}, {_quote('Sys' + table + 'Right')})
""")
    db_cols = {r["a"]: r["b"] for r in rows if r["k"] == "column"}
    indexes = [r["b"] for r in rows if r["k"] == "index"]
    fks = {r["a"]: (r["b"], r["c"]) for r in rows if r["k"] == "fk"}
    tables = {r["a"]: r["b"] for r in rows if r["k"] == "table"}
    out: list[tuple[str, str]] = []
    if table not in tables:
        return [("missing", f"no table {table}")]
    if eff.get("D1") or eff.get("D10"):
        out.append(("note", f"{table} is {'virtual' if eff.get('D1') else 'a DB view'} in the metadata: the platform does not manage this table"))
    for c in eff.get("D2", []):
        if c.get("E4"):  # a virtual column has no field
            continue
        t = ALL_DATA_VALUE_TYPES.get(c.get("S2"), c.get("S2"))
        name = (c.get("E17") or c["A2"] + "Id") if t in LOOKUPS else c["A2"]  # a lookup is stored as <Name>Id
        if name not in db_cols:
            out.append(("missing", f"column {name} ({t})"))
            continue
        expected = PG_TYPES.get(t)
        out.append(("ok" if not expected or db_cols[name] in expected else "differs", f"column {name}: {t} stored as {db_cols[name]}"))
        if c.get("E6"):
            hit = any(f'("{name}"' in d or f'"{name}")' in d or f'"{name}" ' in d for d in indexes)
            out.append(("ok" if hit else "missing", f"index on {name}"))
        if t in LOOKUPS:
            fk = fks.get(name)
            if c.get("E8"):
                out.append(("ok" if not fk else "differs", f"{name}: weak reference, foreign key {'present' if fk else 'absent'}"))
            elif not fk:
                out.append(("missing", f"foreign key on {name}"))
            else:
                want = "CASCADE" if c.get("E9") else "NO ACTION"
                out.append(("ok" if fk[1] == want else "differs", f"foreign key {name} -> {fk[0]} on delete {fk[1]} (expected {want})"))
    if eff.get("D17"):
        out.append(("ok" if f"Sys{table}Right" in tables else "missing", f"rights table Sys{table}Right (admin-records)"))
    if eff.get("D32"):
        out.append(("ok" if "RecordInactive" in db_cols else "missing", "column RecordInactive (deactivation)"))
    return out
