"""Who is in a role and what a system setting is, read from the database (`Environment.sql`).

    role_members(env, "UsrManagers")               everybody the role reaches, nested roles and the org structure included
    user_roles(env, "Supervisor")                  the reverse
    role_diff(env, ["Ivan", "olga"], "UsrManagers")  which of these users are not in the role
    sys_setting("UsrMaxRows", {"dev": env, ...})   the value on each environment, and the bindings of the workspace that set it

Membership is read from `SysAdminUnitInRole`, the closure the platform keeps, never from `SysUserInRole` (direct members
only). Every query is in the README.
"""

from __future__ import annotations

from pathlib import Path

from .records import guid, local_time, names_of, quote

USER = 4  # SysAdminUnit.SysAdminUnitTypeValue of a user
KINDS = {0: "organization", 1: "division", 2: "manager", 4: "user", 6: "functional role"}
# SysSettings.ValueTypeName -> the SysSettingsValue column that holds the value
VALUE_COLUMN = {"Integer": "IntegerValue", "Float": "FloatValue", "Money": "FloatValue", "Boolean": "BooleanValue", "DateTime": "DateTimeValue",
                "Date": "DateTimeValue", "Time": "DateTimeValue", "Lookup": "GuidValue", "Guid": "GuidValue", "Binary": "BinaryValue"}


def kind_of(value) -> str:
    return KINDS.get(int(value), f"type {value}") if str(value).lstrip("-").isdigit() else str(value)


def _unit(env, role: str) -> dict:
    rows = env.sql(f'select "Id", "Name", "SysAdminUnitTypeValue" from "SysAdminUnit" where "Name" = {quote(role)}')
    if not rows:
        raise KeyError(f"no role named {role!r} (SysAdminUnit.Name)")
    if len(rows) > 1:
        raise ValueError(f"{role!r} is {len(rows)} units: " + ", ".join(f"{kind_of(r['SysAdminUnitTypeValue'])} {r['Id']}" for r in rows) + "; the site must rename one")
    return rows[0]


# The chain behind a closure row is read from the tables the platform builds `SysAdminUnitInRole` from (its `Source`
# column is an integer code, not a unit): `SysUserInRole` (a user put in a role by hand), `SysAdminUnit.ParentRoleId`
# (the org and functional trees) and `SysFuncRoleInOrgRole` (a functional role granted to an org role).

def _units(env) -> dict[str, dict]:
    """Id -> {name, parent, kind} of every SysAdminUnit."""
    return {str(r["Id"]).lower(): {"name": r["Name"], "parent": str(r.get("ParentRoleId") or "").lower(), "kind": r["SysAdminUnitTypeValue"]}
            for r in env.sql('select "Id", "Name", "ParentRoleId", "SysAdminUnitTypeValue" from "SysAdminUnit"')}


def _granted(env) -> dict[str, list[str]]:
    """org role Id -> the functional roles its members get."""
    out: dict[str, list[str]] = {}
    for r in env.sql('select "FuncRoleId", "OrgRoleId" from "SysFuncRoleInOrgRole"'):
        out.setdefault(str(r["OrgRoleId"]).lower(), []).append(str(r["FuncRoleId"]).lower())
    return out


def _direct(env, user_ids: list[str]) -> dict[str, list[str]]:
    """user Id -> the roles the user is in by hand, 50 users per statement."""
    out: dict[str, list[str]] = {}
    ids = sorted({guid(i) for i in user_ids if i})
    for i in range(0, len(ids), 50):
        for r in env.sql('select "SysUserId", "SysRoleId" from "SysUserInRole" where "SysUserId" in (' + ", ".join(repr(x) for x in ids[i:i + 50]) + ")"):
            out.setdefault(str(r["SysUserId"]).lower(), []).append(str(r["SysRoleId"]).lower())
    return out


def _reach(start: str, units: dict, granted: dict) -> set[str]:
    """Every role a membership in `start` implies: the parents up the tree and the functional roles granted on the way."""
    seen: set[str] = set()
    todo = [start]
    while todo:
        r = todo.pop()
        if r in seen or r not in units:
            continue
        seen.add(r)
        todo += ([units[r]["parent"]] if units[r]["parent"] else []) + granted.get(r, [])
    return seen


def _through(role_id: str, starts: list[str], units: dict, granted: dict) -> str | None:
    """'' for a membership by hand, the name of the direct role it came through, None when no chain explains the row."""
    if role_id in starts:
        return ""
    return next((units[s]["name"] for s in starts if role_id in _reach(s, units, granted)), None)


def role_members(env, role: str, units: bool = False) -> list[dict]:
    """[{member, login, kind, through}] of a role through `SysAdminUnitInRole`; users only unless `units`.
    `through` is the direct role the membership came through, '' when the user is in the role by hand, None when
    `SysUserInRole`, `ParentRoleId` and `SysFuncRoleInOrgRole` do not explain the closure's row."""
    unit = _unit(env, role)
    role_id = str(unit["Id"]).lower()
    rows = env.sql('select m."Id" as "id", m."Name" as "member", c."Name" as "contact", m."SysAdminUnitTypeValue" as "kind" '
                   'from "SysAdminUnitInRole" ir join "SysAdminUnit" m on m."Id" = ir."SysAdminUnitId" '
                   'left join "Contact" c on c."Id" = m."ContactId" '
                   f'where ir."SysAdminUnitRoleId" = \'{guid(unit["Id"])}\'' + ("" if units else f' and m."SysAdminUnitTypeValue" = {USER}'))
    tree, granted = _units(env), _granted(env)
    direct = _direct(env, [r["id"] for r in rows if kind_of(r["kind"]) == "user"])
    out = []
    for r in rows:
        uid, kind = str(r["id"]).lower(), kind_of(r["kind"])
        through = _through(role_id, direct.get(uid, []), tree, granted) if kind == "user" else ("" if uid == role_id or role_id in _reach(uid, tree, granted) else None)
        out.append({"member": r["contact"] or r["member"], "login": r["member"], "kind": kind, "through": through})
    return sorted(out, key=lambda m: (m["kind"], m["member"].lower()))


def find_user(env, user: str) -> dict:
    """The one user whose login (`SysAdminUnit.Name`) or contact name is `user`."""
    rows = env.sql('select u."Id", u."Name" as "login", c."Name" as "contact" from "SysAdminUnit" u '
                   'left join "Contact" c on c."Id" = u."ContactId" '
                   f'where u."SysAdminUnitTypeValue" = {USER} and (u."Name" = {quote(user)} or c."Name" = {quote(user)})')
    if not rows:
        raise KeyError(f"no user {user!r} (a login or a contact name)")
    if len(rows) > 1:
        raise ValueError(f"{user!r} is {len(rows)} users: " + ", ".join(f"{r['login']} ({r['contact']})" for r in rows) + "; give the login")
    return rows[0]


def user_roles(env, user: str) -> list[dict]:
    """[{role, kind, through}] of a user through `SysAdminUnitInRole`; `through` as in `role_members`."""
    unit = find_user(env, user)
    uid = str(unit["Id"]).lower()
    rows = env.sql('select r."Id" as "id", r."Name" as "role", r."SysAdminUnitTypeValue" as "kind" from "SysAdminUnitInRole" ir '
                   f'join "SysAdminUnit" r on r."Id" = ir."SysAdminUnitRoleId" where ir."SysAdminUnitId" = \'{guid(unit["Id"])}\'')
    tree, granted, starts = _units(env), _granted(env), _direct(env, [uid]).get(uid, [])
    return sorted(({"role": r["role"], "kind": kind_of(r["kind"]), "through": _through(str(r["id"]).lower(), starts, tree, granted)}
                   for r in rows), key=lambda r: r["role"].lower())


def role_diff(env, users: list[str], role: str) -> dict:
    """{present, missing}: the given users (logins or contact names) in the role, and the ones not in it."""
    unit = _unit(env, role)
    inside = {str(r["id"]).lower() for r in env.sql(f'select "SysAdminUnitId" as "id" from "SysAdminUnitInRole" where "SysAdminUnitRoleId" = \'{guid(unit["Id"])}\'')}
    found = [(u, find_user(env, u)) for u in users]
    return {"present": [u for u, f in found if str(f["Id"]).lower() in inside], "missing": [u for u, f in found if str(f["Id"]).lower() not in inside]}


def _chain(r: dict) -> str:
    if r["through"] is None:
        return "  chain not found (not in SysUserInRole, ParentRoleId or SysFuncRoleInOrgRole)"
    return f"  through {r['through']}" if r["through"] else ("  direct" if r["kind"] == "user" or "role" in r else "")


def render_members(rows: list[dict]) -> str:
    return "\n".join(f"{r['member']}  [{r['kind']}]" + _chain(r) + ("" if r["login"] == r["member"] else f"  login {r['login']}")
                     for r in rows) or "(nobody)"


def render_roles(rows: list[dict]) -> str:
    return "\n".join(f"{r['role']}  [{r['kind']}]" + _chain(r) for r in rows) or "(no role)"


# -- settings ---------------------------------------------------------------------- #

def setting_value(row: dict, type_name: str) -> str:
    """The value of a SysSettingsValue row in the column its setting's type names."""
    column = VALUE_COLUMN.get(type_name, "TextValue")
    value = row.get(column)
    return "" if value in (None, "null") else str(value)


def setting_on(env, code: str, zone: str | None = None) -> list[dict]:
    """[{id, name, type, values: [{for, value, shown, modifiedOn, modifiedBy}]}] of a setting on one site (an empty list: no such code)."""
    settings = env.sql('select "Id", "Name", "ValueTypeName", "ReferenceSchemaUId" from "SysSettings" where "Code" = ' + quote(code))
    out = []
    for s in settings:
        rows = env.sql('select * from "SysSettingsValue" where "SysSettingsId" = ' + quote(guid(s["Id"])))
        units = names_of(env, "SysAdminUnit", [r.get("SysAdminUnitId") for r in rows if r.get("SysAdminUnitId")])
        people = names_of(env, "Contact", [r.get("ModifiedById") for r in rows if r.get("ModifiedById")])
        values = []
        for r in rows:
            value = setting_value(r, s["ValueTypeName"])
            shown = _referenced(env, s, value) if VALUE_COLUMN.get(s["ValueTypeName"]) == "GuidValue" and value else ""
            who = str(r.get("SysAdminUnitId") or "").lower()
            values.append({"for": units.get(who) or ("all" if not who.strip("0-") else who), "value": value, "shown": shown,
                           "modifiedOn": local_time(r.get("ModifiedOn"), zone), "modifiedBy": people.get(str(r.get("ModifiedById")).lower())})
        out.append({"id": s["Id"], "name": s["Name"], "type": s["ValueTypeName"], "values": values})
    return out


def _referenced(env, setting: dict, value: str) -> str:
    """The Name of the record a lookup setting points at (the setting's ReferenceSchemaUId names the object)."""
    try:
        table = env.sql('select "Name" from "SysSchema" where "UId" = ' + quote(guid(setting["ReferenceSchemaUId"])))[0]["Name"]
        return names_of(env, table, [value]).get(value.lower()) or ""
    except (IndexError, ValueError, KeyError):  # no such schema, or a value that is not an Id: nothing to show
        return ""
    except RuntimeError as e:
        return f"error: {e.args[0] if e.args else e}"


def bindings_of(workspace: Path | str, setting_ids: set[str], code: str) -> list[dict]:
    """The `SysSettingsValue` rows the data bindings of the workspace's packages carry for a setting: [{package, binding, value, for}].
    The setting is known by its Id on a site or by a `SysSettings` binding with this Code."""
    from .data import DataBinding
    packages = [p for p in sorted((Path(workspace) / "packages").glob("*")) if (p / "descriptor.json").is_file()] or \
               [p for p in sorted(Path(workspace).glob("*")) if (p / "descriptor.json").is_file()]
    bindings = []
    for p in packages:
        for d in sorted((p / "Data").glob("*")):
            if (d / "descriptor.json").is_file():
                try:
                    bindings.append((p, DataBinding(p, d.name)))
                except ValueError:
                    continue  # an empty or broken data.json carries no value
    ids = {i.lower() for i in setting_ids}
    types = {}
    for _, b in bindings:
        if b.schema_name == "SysSettings":
            for r in b.rows(culture="en-US"):
                if str(r.get("Code")) == code:
                    ids.add(str(r["Id"]).lower())
                    types[str(r["Id"]).lower()] = r.get("ValueTypeName")
    out = []
    for p, b in bindings:
        if b.schema_name != "SysSettingsValue":
            continue
        for r in b.rows():
            sid = str(r.get("SysSettings")).lower()
            if sid in ids:
                out.append({"package": p.name, "binding": b.name, "value": setting_value(r, types.get(sid) or _type_hint(r)),
                            "for": str(r.get("SysAdminUnit") or "")})
    return out


def _type_hint(row: dict) -> str:
    """The setting's type when no binding names it: the one value column that is not empty."""
    for type_name, column in (("Integer", "IntegerValue"), ("Boolean", "BooleanValue"), ("Float", "FloatValue"), ("DateTime", "DateTimeValue"), ("Lookup", "GuidValue")):
        if row.get(column) not in (None, "null", "", 0, 0.0, False):
            return type_name
    return "Text"


def sys_setting(code: str, envs: dict, workspace: Path | str | None = None, zone: str | None = None) -> dict:
    """{code, environments: {name: [setting] | "error: ..."}, bindings: [..]}: `envs` maps a name to an `Environment`;
    an environment that cannot be read gets its error line and the others are still read."""
    found_on = {}
    for name, env in envs.items():
        try:
            found_on[name] = setting_on(env, code, zone)
        except RuntimeError as e:
            found_on[name] = f"error: {e.args[0] if e.args else e}"
    answer = {"code": code, "environments": found_on, "bindings": [], "workspace": bool(workspace)}
    if workspace:
        ids = {s["id"] for found in answer["environments"].values() if isinstance(found, list) for s in found}
        answer["bindings"] = bindings_of(workspace, ids, code)
    return answer


def render_setting(answer: dict) -> str:
    lines = [f"setting {answer['code']}"]
    for name, found in answer["environments"].items():
        if isinstance(found, str):
            lines.append(f"  {name}: {found}")
            continue
        if not found:
            lines.append(f"  {name}: no such setting")
        for s in found:
            lines.append(f"  {name}: {s['name']} [{s['type']}]" + ("" if s["values"] else "  (no value row)"))
            for v in s["values"]:
                lines.append(f"    for {v['for']}: {v['value']!r}" + (f" ({v['shown']})" if v["shown"] else "")
                             + (f"  modified {v['modifiedOn']}" if v["modifiedOn"] else "") + (f" by {v['modifiedBy']}" if v["modifiedBy"] else ""))
    for b in answer["bindings"]:
        lines.append(f"  binding {b['package']}/{b['binding']}: would write {b['value']!r}" + (f" for {b['for']}" if b["for"] else ""))
    if answer["workspace"] and not answer["bindings"]:
        lines.append("  (no data binding of the workspace carries this setting)")
    return "\n".join(lines)
