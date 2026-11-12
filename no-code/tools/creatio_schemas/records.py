"""Where a record lives on a site and what surrounds it, read from the database (`Environment.sql`).

    find_record(env, "<id>")                       which table holds an Id, with its caption, dates and authors
    record_context(env, "Contact", "<id>")         the record with its lookups named, then the rows that point at it

Every query is a plain `information_schema` / `select` the README lists, so a human can run it by hand. A table name
reaches a statement only from `information_schema` or after `ident` accepted it.
"""

from __future__ import annotations

import fnmatch
import re
from datetime import datetime, timezone

from .files import GUID_RE

CHUNK = 50  # tables per `union all`
DETAIL_ROWS = 20
TABLES_SQL = ('select c.table_schema as "schema", c.table_name as "table" from information_schema.columns c '
              'join information_schema.tables t on t.table_name = c.table_name and t.table_schema = c.table_schema '
              "where c.column_name = 'Id' and c.data_type in ('uuid', 'uniqueidentifier') and t.table_type = 'BASE TABLE' "
              "and c.table_schema not in ('pg_catalog', 'information_schema', 'sys') order by 1")
FK_SQL = ('select kcu.table_name as "table", kcu.column_name as "column", ccu.table_name as "ref_table" '
          "from information_schema.referential_constraints rc "
          "join information_schema.key_column_usage kcu on kcu.constraint_name = rc.constraint_name "
          "join information_schema.constraint_column_usage ccu on ccu.constraint_name = rc.unique_constraint_name where ")
CAPTION_COLUMNS = ("Name", "Caption", "Title", "Subject", "Number")  # the first the row has stands for the record
AUDIT = ("CreatedOn", "CreatedById", "ModifiedOn", "ModifiedById")


def ident(name: str) -> str:
    """A table or column name that may go into a statement."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or ""):
        raise ValueError(f"{name!r} is not a table or column name")
    return name


def guid(value: str) -> str:
    if not GUID_RE.fullmatch(value or ""):
        raise ValueError(f"{value!r} is not an Id (a guid)")
    return value.lower()


def quote(text) -> str:
    """A text as a SQL string literal."""
    return "'" + str(text).replace("'", "''") + "'"


def _zone(name: str | None):
    """(tzinfo, label): a fixed offset (`+03:00`, `UTC-5`), an IANA name when the machine has the tz database, else the machine's zone."""
    from datetime import timedelta
    if name:
        m = re.fullmatch(r"(?:UTC)?([+-])(\d{1,2})(?::?(\d\d))?", name.strip())
        if m:
            minutes = (int(m.group(2)) * 60 + int(m.group(3) or 0)) * (1 if m.group(1) == "+" else -1)
            return timezone(timedelta(minutes=minutes)), name.strip()
        try:
            from zoneinfo import ZoneInfo
            return ZoneInfo(name), name
        except Exception:  # no tz database (Windows without tzdata) or an unknown name
            return None, f"local, zone {name!r} unknown here (Windows needs `pip install tzdata` for IANA names; an offset like +02:00 always works)"
    return None, "local"


def local_time(value, zone: str | None = None) -> str:
    """`2026-11-10 12:30:00 UTC (14:30 +02:00)`; a value without a zone is UTC; `zone` is an offset or an IANA name, None the machine's."""
    if not value:
        return ""
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    moment = moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)
    tz, label = _zone(zone)
    there = moment.astimezone(tz)
    return f"{moment:%Y-%m-%d %H:%M:%S} UTC ({there:%H:%M} {label})" + ("" if there.date() == moment.date() else f" {there:%d.%m}")


def zone_of(project: str | None) -> str | None:
    """`environment.timeZone` of a project.json (an IANA name), or None for the machine's zone."""
    if not project:
        return None
    import json
    with open(project, encoding="utf-8-sig") as f:
        return (json.load(f).get("environment") or {}).get("timeZone")


def _first(row: dict, names=CAPTION_COLUMNS):
    """(column, value) that stands for the record: a caption column, else the first `...Name` / `...Number` ... column with a value."""
    for n in names:
        if row.get(n) not in (None, ""):
            return n, row[n]
    return next(((k, v) for k, v in row.items() if k.endswith(names) and v not in (None, "")), (None, None))


def names_of(env, table: str, ids: list[str]) -> dict[str, str]:
    """Id -> Name of the rows of `table` (an object without a Name column answers with nothing)."""
    ids = sorted({guid(i) for i in ids if i})
    if not ids:
        return {}
    rows = env.sql(f'select "Id", "Name" from "{ident(table)}" where "Id" in ({", ".join(repr(i) for i in ids)})')
    return {str(r["Id"]).lower(): r.get("Name") for r in rows}


def find_record(env, record_id: str, priority=(), everywhere: bool = False, zone: str | None = None) -> list[dict]:
    """The tables whose `Id` is `record_id`: [{table, caption, createdOn, createdBy, modifiedOn, modifiedBy}].

    Tables come from `information_schema` (base tables with a uuid `Id`), the ones named in `priority` first (the objects of
    the workspace); chunks of 50 are one `union all` each, and the scan stops after the first chunk that finds the Id unless
    `everywhere`."""
    record_id = guid(record_id)
    tables = [(ident(r["schema"]), ident(r["table"])) for r in env.sql(TABLES_SQL)]  # schema-qualified: a table outside search_path still answers
    first = {t.lower() for t in priority}
    tables = [t for t in tables if t[1].lower() in first] + [t for t in tables if t[1].lower() not in first]
    hits: list[tuple[str, str]] = []
    for i in range(0, len(tables), CHUNK):
        union = " union all ".join(f"select '{s}' as \"schema\", '{t}' as \"table\" from \"{s}\".\"{t}\" where \"Id\" = '{record_id}'" for s, t in tables[i:i + CHUNK])
        hits += [(r.get("schema") or "public", r["table"]) for r in env.sql(union)]
        if hits and not everywhere:
            break
    out = []
    for schema, table in hits:
        row = (env.sql(f'select * from "{ident(schema)}"."{ident(table)}" where "Id" = \'{record_id}\'') or [{}])[0]
        who = names_of(env, "Contact", [row.get("CreatedById"), row.get("ModifiedById")])
        out.append({"table": table, "caption": dict([_first(row)]) if _first(row)[0] else {},
                    "createdOn": local_time(row.get("CreatedOn"), zone), "createdBy": who.get(str(row.get("CreatedById")).lower()),
                    "modifiedOn": local_time(row.get("ModifiedOn"), zone), "modifiedBy": who.get(str(row.get("ModifiedById")).lower())})
    return out


def foreign_keys(env, table: str, incoming: bool = False) -> list[dict]:
    """[{table, column, ref_table}] of the foreign keys a table has (`incoming`: the ones that point at it)."""
    return env.sql(FK_SQL + ("ccu" if incoming else "kcu") + f".table_name = '{ident(table)}'")


def record_context(env, entity: str, record_id: str, columns: str = "", depth: int = 1, zone: str | None = None) -> dict:
    """{entity, id, columns {name: value | {"id", "name"}}, details [{table, column, count, rows}]}.

    `columns` is a comma list with `*` wildcards (default: every column that has a value); a lookup shows the referenced
    row's Name next to its Id, found through the table's foreign keys; the details are the tables with a foreign key to
    this entity and a row for this Id, with the first 20 rows (`depth` 2 names the lookups of those rows too)."""
    record_id = guid(record_id)
    rows = env.sql(f'select * from "{ident(entity)}" where "Id" = \'{record_id}\'')
    if not rows:
        raise KeyError(f"no row {record_id} in {entity}")
    row = rows[0]
    wanted = [c.strip() for c in columns.split(",") if c.strip()]
    # a lookup may be named without its Id suffix (`UsrService` for `UsrServiceId`)
    shown = {k: v for k, v in row.items() if (any(fnmatch.fnmatchcase(k.lower(), w.lower()) or fnmatch.fnmatchcase(k.lower(), w.lower() + "id")
                                                 for w in wanted) if wanted else v not in (None, ""))}
    out = {"entity": entity, "id": record_id, "columns": _named(env, entity, [shown], zone)[0], "details": [], "depth": depth}
    if depth < 1:
        return out
    pointing = foreign_keys(env, entity, incoming=True)
    counts = []
    for i in range(0, len(pointing), CHUNK):
        union = " union all ".join(f"select '{ident(f['table'])}' as \"table\", '{ident(f['column'])}' as \"column\", count(*) as \"n\" "
                                   f"from \"{f['table']}\" where \"{f['column']}\" = '{record_id}'" for f in pointing[i:i + CHUNK])
        counts += [r for r in env.sql(union) if int(r["n"])]
    for c in sorted(counts, key=lambda r: (r["table"], r["column"])):
        sample = env.sql(f'select * from "{c["table"]}" where "{c["column"]}" = \'{record_id}\' order by "Id" offset 0 rows fetch first {DETAIL_ROWS} rows only')
        # depth 1: the Id, the column that points here and a caption; depth 2: every column, so `_named` can name its lookups
        keep = [r if depth > 1 else {k: v for k, v in r.items() if k in ("Id", c["column"]) or k in CAPTION_COLUMNS} for r in sample]
        out["details"].append({"table": c["table"], "column": c["column"], "count": int(c["n"]),
                               "rows": _named(env, c["table"], keep, zone) if depth > 1 else keep})
    return out


def _named(env, table: str, rows: list[dict], zone: str | None) -> list[dict]:
    """The rows with each lookup value as {id, name} (through the table's foreign keys) and times in UTC and the zone."""
    refs = {f["column"]: f["ref_table"] for f in foreign_keys(env, table)}
    names = {col: names_of(env, ref, [str(r[col]) for r in rows if r.get(col)]) for col, ref in refs.items() if any(r.get(col) for r in rows)}
    out = []
    for r in rows:
        shown = {}
        for k, v in r.items():
            if k in names and v:
                shown[k] = {"id": v, "name": names[k].get(str(v).lower())}
            elif k.endswith("On") and v:
                shown[k] = local_time(v, zone)
            else:
                shown[k] = v
        out.append(shown)
    return out


def _cell(value) -> str:
    if isinstance(value, dict):
        return f"{value['name']} ({value['id']})" if value.get("name") else str(value["id"])
    return str(value)


def render_hits(hits: list[dict]) -> str:
    if not hits:
        return "(no table holds this Id)"
    lines = []
    for h in hits:
        caption = ", ".join(f"{k} = {v}" for k, v in h["caption"].items())
        lines.append(f"{h['table']}" + (f"  {caption}" if caption else ""))
        lines.append(f"  created  {h['createdOn']}" + (f" by {h['createdBy']}" if h["createdBy"] else ""))
        lines.append(f"  modified {h['modifiedOn']}" + (f" by {h['modifiedBy']}" if h["modifiedBy"] else ""))
    return "\n".join(lines)


def render_context(context: dict) -> str:
    lines = [f"{context['entity']} {context['id']}"] + [f"  {k} = {_cell(v)}" for k, v in context["columns"].items()]
    for d in context["details"]:
        lines.append(f"{d['table']}.{d['column']}: {d['count']} row(s)" + (f", first {len(d['rows'])}" if d["count"] > len(d["rows"]) else ""))
        lines += ["  " + "  ".join(f"{k}={_cell(v)}" for k, v in r.items()) for r in d["rows"]]
    if not context["details"] and context.get("depth", 1):  # depth 0 did not look
        lines.append("(no other table has a row pointing at this record)")
    return "\n".join(lines)
