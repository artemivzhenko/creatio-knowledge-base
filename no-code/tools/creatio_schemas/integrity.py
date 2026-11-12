"""Snapshot of an object, as lines, and the comparison of two snapshots: the proof that a layer merge changed nothing observable.

    snapshot(workspace, "Account", env)    the disk lines (effective columns over the layers) and the site lines
    compare(before, after)                 `+ - ~` lines through describe/diff.py::diff_lines; empty = nothing changed

Site lines, each from one statement the env README lists:

    table <T> column <col> <type>[(len)] [null]      information_schema.columns
    rows <count>                                     select count(*)
    checksum <col> <md5>                             md5(string_agg(coalesce("<col>"::text, ''), '|' order by "Id")), 50 columns a statement
    copy <package> extendParent=<bool>               schema_layers, in the order the platform applies them

PostgreSQL only, like `layers`. A checksum reads the whole table: on a big table name the columns (`columns=`).
"""

from __future__ import annotations

import json

from .describe.diff import diff_lines
from .describe.layers import schema_layers
from .records import ident

CHUNK = 50  # checksums per statement
COLUMNS_SQL = ('select column_name::text as "column", data_type::text as "type", character_maximum_length::text as "length", is_nullable::text as "nullable" '
               "from information_schema.columns where table_schema = current_schema() and table_name = '{table}' order by 1")


def compare(before: list[str], after: list[str]) -> list[str]:
    return diff_lines(before, after)


def table_lines(env, table: str) -> list[str]:
    """`table <T> column <col> <type>[(len)] [null]` per column of the table; no lines when the table does not exist."""
    rows = env.sql(COLUMNS_SQL.format(table=ident(table)))
    return [f"table {table} column {r['column']} {r['type']}" + (f"({r['length']})" if r.get("length") not in (None, "") else "")
            + (" null" if str(r["nullable"]).upper() == "YES" else "") for r in rows]


def checksum_lines(env, table: str, columns: list[str]) -> list[str]:
    """`checksum <col> <md5>` per column: one md5 over the column's values ordered by Id (`-` for an empty table)."""
    out = []
    for i in range(0, len(columns), CHUNK):
        chunk = [ident(c) for c in columns[i:i + CHUNK]]
        picks = ", ".join(f'md5(string_agg(coalesce("{c}"::text, \'\'), \'|\' order by "Id")) as "c{n}"' for n, c in enumerate(chunk))
        row = (env.sql(f'select {picks} from "{ident(table)}"') or [{}])[0]
        out += [f"checksum {c} {row.get(f'c{n}') or '-'}" for n, c in enumerate(chunk)]
    return out


def site_lines(env, schema: str, columns: list[str] | None = None, custom_layer: str | None = None) -> list[str]:
    """The lines of an object on a site: its table, its row count, the checksums of `columns` (default: every column but Id), its copies."""
    table = table_lines(env, schema)
    if not table:
        raise KeyError(f"no table {schema} on the site (information_schema.columns is empty): not an object, or not installed")
    names = [l.split()[3] for l in table]
    count = env.sql(f'select count(*) as "n" from "{ident(schema)}"')[0]["n"]
    layers = schema_layers(env, schema, custom_layer=custom_layer) if custom_layer else schema_layers(env, schema)
    wanted = [c for c in (columns or names) if c != "Id"]
    missing = [c for c in wanted if c not in names]
    if missing:
        raise KeyError(f"{schema} has no table column {', '.join(missing)} on the site")
    return (table + [f"rows {count}"] + checksum_lines(env, schema, wanted)
            + [f"copy {l['package']} extendParent={str(l['extendParent']).lower()}" for l in layers["layers"]])


def snapshot(workspace, schema: str, env=None, columns: list[str] | None = None, custom_layer: str | None = None) -> list[str]:
    """Disk lines of `workspace` (over `layers_in_order`, the site's order when `env` is given) followed by the site lines of `env`; either part is left out when not asked for."""
    lines: list[str] = []
    if workspace:
        lines += disk_lines(workspace, schema, env)
    if env is not None:
        lines += site_lines(env, schema, columns, custom_layer)
    return lines


def disk_lines(workspace, schema: str, env=None) -> list[str]:
    """The effective object over every layer of the workspace, in `layers_in_order` (the site's order with `env`):

        layers: <pkg> > <pkg> ...            the layers with a folder on disk (`siblings ordered by name` when two have no dependency)
        column <Name> <uid> <type> [lookup <Object>] [required] [default <v>]
        index <Name> on <col>, <col> [unique]

    The first layer's parent (its own copy's effective schema, or the fetched base, `objects.py base`) takes the diff of each
    layer in turn (`SchemaDiff.apply`, the same as `EntitySchema.effective` for one layer). A vendor base that is not on
    disk and not fetched stops the snapshot: it would describe the layers' additions only."""
    from .describe.merge import layers_in_order
    from .entity.catalog import column_flags
    from .entity.schema import EntitySchema
    from .files import ALL_DATA_VALUE_TYPES

    on_disk = [x for x in layers_in_order(workspace, schema, env, "EntitySchemaManager") if x.folder is not None]
    if not on_disk:
        raise KeyError(f"no object layer {schema} in the workspace {workspace}")
    entities = [EntitySchema(x.folder.parent.parent, schema) for x in on_disk]
    current = None
    for entity in entities:
        if entity.full or not entity.replacing:
            current = entity.effective
        else:
            if current is None:
                current = entity.parent
                if current is None:
                    raise RuntimeError(f"the base of {schema} is not known here: objects.py base {entity.dir.parent.parent} {schema} --env <env>")
            current = entity.delta.apply(current)
    lines = ["layers: " + " > ".join(x.package for x in on_disk)]
    if any(x.siblings for x in on_disk):
        lines.append("siblings ordered by name: " + ", ".join(x.package for x in on_disk if x.siblings))
    for c in current.get("D2", []):
        flags = column_flags(c)
        default = c["E12"].get("FB2", c["E12"]) if isinstance(c.get("E12"), dict) else None
        lines.append(f"column {c['A2']} {c['UId']} {ALL_DATA_VALUE_TYPES.get(c.get('S2'), c.get('S2'))}"
                     + (f" lookup {entities[0].ref_name(c['S4'])}" if c.get("S4") else "") + (" required" if "required" in flags else "")
                     + (f" default {default}" if default is not None else ""))
    columns = {c["UId"]: c["A2"] for c in current.get("D2", [])}
    lines += [f"index {i['A2']} on {', '.join(columns.get(k.get('G1'), k.get('G1')) for k in i.get('F4', []))}" + (" unique" if i.get("F1") else "")
              for i in current.get("D6", [])]
    return lines
