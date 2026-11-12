"""Business-process runs as the site logs them (`SysProcessLog`, `SysProcessElementLog`), read through `Environment.sql`.

    process_log(env, "<process id>")                       the run RunProcess started: status, error, start, end
    process_runs(env, process="UsrOrder_Process")         the newest runs of a process (own and replacing copies)
    process_runs(env, record="UsrOrder:<id>")             the runs started around the changes of a record and its details
    process_error(env, "<log id>")                        the whole error without stack frames, and the element it stopped on

The process id RunProcess answers is the `SysProcessLog.Id` of the run. Every query is in `env/README.md`.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .files import GUID_RE
from .records import CHUNK, foreign_keys, guid, ident, local_time, names_of

LOG_SELECT = ('select l."Id", l."Name", st."Name" as "Status", l."ErrorDescription", l."StartDate", l."CompleteDate", '
              'l."OwnerId", s."Name" as "Process" from "SysProcessLog" l '
              'left join "SysProcessStatus" st on st."Id" = l."StatusId" left join "SysSchema" s on s."Id" = l."SysSchemaId" ')
ELEMENT_SELECT = ('select e."Caption", st."Name" as "Status", e."ErrorDescription", e."StartDate", e."CompleteDate" '
                  'from "SysProcessElementLog" e left join "SysProcessStatus" st on st."Id" = e."StatusId" ')
_FRAME_RE = re.compile(r"^\s*(at |--- End of )")


def _when(value: str) -> str:
    """A date the caller typed (`2026-11-11`, `2026-11-11T08:00`, with or without a zone) as a UTC literal for SQL."""
    try:
        moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{value!r} is not a date (2026-11-11 or 2026-11-11T08:00)") from None
    moment = moment if moment.tzinfo is None else moment.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{moment:%Y-%m-%d %H:%M:%S}"


def _moment(value) -> datetime | None:
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.replace(tzinfo=None) if moment.tzinfo is None else moment.astimezone(timezone.utc).replace(tzinfo=None)


def state(row: dict) -> str:
    """`completed`, `running` or `failed`, from the dates and the error (the status name is the site's language)."""
    if row.get("ErrorDescription"):
        return "failed"
    name = str(row.get("Status") or "").lower()
    if any(w in name for w in ("error", "cancel")):
        return "failed"
    return "completed" if row.get("CompleteDate") else "running"


def _first_line(text) -> str:
    return next((line.strip() for line in str(text or "").splitlines() if line.strip()), "")


def _run(row: dict, zone: str | None, owners: dict | None = None) -> dict:
    return {"id": str(row.get("Id", "")).lower(), "process": row.get("Process") or row.get("Name"), "status": row.get("Status"),
            "state": state(row), "error": _first_line(row.get("ErrorDescription")), "start": local_time(row.get("StartDate"), zone),
            "end": local_time(row.get("CompleteDate"), zone), "owner": (owners or {}).get(str(row.get("OwnerId") or "").lower())}


def process_log(env, process_id: str, zone: str | None = None) -> dict | None:
    """The `SysProcessLog` row of a run as {id, process, status, state, error, start, end, owner}, or None (no row yet)."""
    rows = env.sql(LOG_SELECT + f"where l.\"Id\" = '{guid(process_id)}'")
    return _run(rows[0], zone) if rows else None


def _is_noise(name: str | None, noise) -> bool:
    return bool(name) and any(str(name).startswith(n) for n in noise)


def _record_moments(env, record: str) -> list[datetime]:
    """`ModifiedOn` of the record and of every row that points at it (the tables with a foreign key to its table)."""
    entity, _, record_id = record.partition(":")
    record_id = guid(record_id.strip())
    entity = ident(entity.strip())
    rows = env.sql(f'select "ModifiedOn" from "{entity}" where "Id" = \'{record_id}\'')
    if not rows:
        raise KeyError(f"no row {record_id} in {entity}")
    moments = [rows[0].get("ModifiedOn")]
    pointing = foreign_keys(env, entity, incoming=True)
    for i in range(0, len(pointing), CHUNK):
        union = " union all ".join(f"select \"ModifiedOn\" from \"{ident(f['table'])}\" where \"{ident(f['column'])}\" = '{record_id}'"
                                   for f in pointing[i:i + CHUNK])
        try:
            moments += [r.get("ModifiedOn") for r in env.sql(union)]
        except RuntimeError:  # a table without ModifiedOn in this chunk: ask each one alone
            for f in pointing[i:i + CHUNK]:
                try:
                    moments += [r.get("ModifiedOn") for r in env.sql(f"select \"ModifiedOn\" from \"{f['table']}\" where \"{f['column']}\" = '{record_id}'")]
                except RuntimeError:
                    continue
    return sorted({m for m in (_moment(v) for v in moments if v) if m})


def _windows(moments: list[datetime], seconds: int) -> list[tuple[datetime, datetime]]:
    """[moment - window, moment + window] for each moment, overlapping ones merged."""
    out: list[list[datetime]] = []
    for m in moments:
        lo, hi = m - timedelta(seconds=seconds), m + timedelta(seconds=seconds)
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def process_runs(env, process: str | None = None, record: str | None = None, since: str | None = None, until: str | None = None,
                 limit: int = 20, window: int = 30, noise=(), zone: str | None = None) -> dict:
    """{runs [run], hidden, windows}: the newest `limit` runs of a process (`process` = its name or UId - every copy of
    that schema), or every run that started within `window` seconds of a change of `record` (`<Entity>:<Id>`, its
    details included), oldest first. `noise` (names or prefixes, `project.json` `environment.noiseProcesses`) hides
    runs of those processes unless `process` names one; `hidden` counts them."""
    where = []
    if process:
        p = process.strip()
        # every copy (the package's own and the replacing ones) has the schema's name; a UId names one of them
        where.append(f"s.\"Name\" in (select \"Name\" from \"SysSchema\" where \"UId\" = '{guid(p)}')" if GUID_RE.fullmatch(p) else f"s.\"Name\" = '{ident(p)}'")
    if since:
        where.append(f"l.\"StartDate\" >= '{_when(since)}'")
    if until:
        where.append(f"l.\"StartDate\" <= '{_when(until)}'")
    windows = []
    if record:
        windows = _windows(_record_moments(env, record), window)
        if not windows:
            return {"runs": [], "hidden": 0, "windows": []}
        where.append("(" + " or ".join(f"l.\"StartDate\" between '{lo:%Y-%m-%d %H:%M:%S}' and '{hi:%Y-%m-%d %H:%M:%S}'" for lo, hi in windows) + ")")
    order = "asc" if record else "desc"
    # noise is dropped after the query, so the page is over-fetched by what the limit could lose to it
    fetch = limit if process or not noise else limit * 5
    rows = env.sql(LOG_SELECT + ("where " + " and ".join(where) + " " if where else "")
                   + f'order by l."StartDate" {order} offset 0 rows fetch first {int(fetch)} rows only')
    hidden = 0
    if not process and noise:
        kept = [r for r in rows if not _is_noise(r.get("Process") or r.get("Name"), noise)]
        hidden, rows = len(rows) - len(kept), kept
    rows = rows[:limit]
    owners = names_of(env, "Contact", [str(r["OwnerId"]) for r in rows if r.get("OwnerId")])
    return {"runs": [_run(r, zone, owners) for r in rows], "hidden": hidden,
            "windows": [(local_time(lo.isoformat(), zone), local_time(hi.isoformat(), zone)) for lo, hi in windows]}


def trim_error(text: str | None) -> str:
    """The message chain of a .NET error without its stack frames (`   at ...`, `--- End of inner exception ...`)."""
    return "\n".join(line.rstrip() for line in str(text or "").splitlines() if line.strip() and not _FRAME_RE.match(line))


def process_error(env, log_id: str, zone: str | None = None) -> dict:
    """{run, error, element}: the run's whole error without stack frames and the element it stopped on
    (`SysProcessElementLog`: the newest with an error, else the newest that never completed), or None."""
    rows = env.sql(LOG_SELECT + f"where l.\"Id\" = '{guid(log_id)}'")
    if not rows:
        raise KeyError(f"no SysProcessLog row {log_id}")
    elements = env.sql(ELEMENT_SELECT + f"where e.\"SysProcessId\" = '{guid(log_id)}' order by e.\"StartDate\" desc")
    stopped = next((e for e in elements if e.get("ErrorDescription") or state(e) == "failed"), None) \
        or next((e for e in elements if not e.get("CompleteDate")), None)
    element = None
    if stopped:
        element = {"caption": stopped.get("Caption"), "status": stopped.get("Status"), "start": local_time(stopped.get("StartDate"), zone),
                   "error": trim_error(stopped.get("ErrorDescription"))}
    return {"run": _run(rows[0], zone), "error": trim_error(rows[0].get("ErrorDescription")), "element": element}


def render_log(log: dict | None, process_id: str = "") -> str:
    if not log:
        return f"log: no SysProcessLog row for {process_id or 'the run'} (the engine did not log it)"
    line = f"log: {log['status'] or '?'} ({log['state']})  started {log['start']}" + (f", ended {log['end']}" if log["end"] else "")
    return line + (f"\n  error: {log['error']}" if log["error"] else "")


def render_runs(answer: dict) -> str:
    lines = []
    if answer["windows"]:
        lines.append("changes of the record: " + "; ".join(f"{lo} .. {hi}" for lo, hi in answer["windows"]))
    for r in answer["runs"]:
        lines.append(f"{r['start']}  {r['process']}  {r['status'] or '?'} ({r['state']})  {r['id']}"
                     + (f"  by {r['owner']}" if r["owner"] else "") + (f"\n    {r['error']}" if r["error"] else ""))
    if not answer["runs"]:
        lines.append("(no runs)")
    if answer["hidden"]:
        lines.append(f"{answer['hidden']} runs of noise processes hidden")
    return "\n".join(lines)


def render_error(answer: dict) -> str:
    r = answer["run"]
    lines = [f"{r['process']}  {r['status'] or '?'} ({r['state']})  started {r['start']}" + (f", ended {r['end']}" if r["end"] else "")]
    e = answer["element"]
    if e:
        lines.append(f"stopped on: {e['caption']} ({e['status'] or '?'}, started {e['start']})")
    lines.append(answer["error"] or (e or {}).get("error") or "(no error text)")
    if e and e["error"] and e["error"] != answer["error"]:
        lines.append(f"element error: {e['error']}")
    return "\n".join(lines)
