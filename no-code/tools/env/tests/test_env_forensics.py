"""Checks for record.py, roles.py, setting.py and their library:  python tests/test_env_forensics.py  (a scripted clio; no site)."""

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent.parent
sys.path.insert(0, str(TOOLS))

from creatio_schemas import access, records  # noqa: E402
from creatio_schemas.environment import Environment  # noqa: E402

ID = "11111111-1111-1111-1111-111111111111"
BOSS = "22222222-2222-2222-2222-222222222222"
CONTACT = "33333333-3333-3333-3333-333333333333"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Scripted:
    """A clio that answers each SQL statement with the rows of the first needle (longest first) its text contains."""

    def __init__(self, answers):
        self.answers, self.statements = answers, []

    def __call__(self, args):
        text = Path(args[args.index("-f") + 1]).read_text(encoding="utf-8")
        self.statements.append(text)
        for needle in sorted(self.answers, key=len, reverse=True):
            if needle in text:
                rows = self.answers[needle]
                rows = rows(text) if callable(rows) else rows
                Path(args[args.index("-d") + 1]).write_text(json.dumps(rows), encoding="utf-8")
                return 0, "Done"
        return 0, f"42P01: no answer scripted for {text[:60]}"


def env(answers):
    clio = Scripted(answers)
    return Environment("https://site.example/", "u", "p", clio_name="dev", clio_run=clio), clio


def raises(fn, kind, text=""):
    try:
        fn()
    except kind as e:
        assert text in str(e), (text, str(e))
        return
    raise AssertionError(f"expected {kind.__name__}")


def run_cli(name, argv, answers, **kw):
    out, clio = io.StringIO(), Scripted(answers)
    settings = Path(tempfile.mkdtemp()) / "appsettings.json"
    settings.write_text(json.dumps({"Environments": {"dev": {"Uri": "https://site.example", "Login": "u", "Password": "p"},
                                                       "test": {"Uri": "https://t.example", "Login": "u", "Password": "p"}}}), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = load(name).main(argv, settings=settings, clio_run=clio, **kw)
    finally:
        shutil.rmtree(settings.parent, ignore_errors=True)
    return code, out.getvalue()


TABLES = [{"schema": "public", "table": t} for t in ("Account", "Contact", "UsrOrder", "UsrOrderItem", "UsrZ")]
ROW = {"Id": ID, "Name": "Order 7", "CreatedOn": "2026-11-10T22:30:00Z", "CreatedById": BOSS, "ModifiedOn": "2026-11-11T08:00:00", "ModifiedById": BOSS}


def test_find_record_scans_the_workspace_objects_first_and_stops_at_the_first_hit():
    old, records.CHUNK = records.CHUNK, 2
    try:
        e, clio = env({"information_schema.columns": TABLES, '"UsrOrder" where': lambda t: [{"schema": "public", "table": "UsrOrder"}] if "UsrOrder" in t else [],
                       'select * from "public"."UsrOrder"': [ROW], 'from "Contact" where "Id" in': [{"Id": BOSS, "Name": "Ivan"}]})
        hits = records.find_record(e, ID.upper(), priority=["usrorder"], zone="+03:00")
        unions = [s for s in clio.statements if s.startswith("select '")]
        assert len(unions) == 1 and unions[0].startswith("select 'public' as \"schema\", 'UsrOrder' as \"table\" from \"public\".\"UsrOrder\"") and "union all select 'public' as \"schema\", 'Account'" in unions[0] and f"\"Id\" = '{ID}'" in unions[0]  # lower-cased, workspace table first, schema-qualified
        assert [h["table"] for h in hits] == ["UsrOrder"] and hits[0]["caption"] == {"Name": "Order 7"} and hits[0]["createdBy"] == "Ivan"
        assert hits[0]["createdOn"].startswith("2026-11-10 22:30:00 UTC (") and hits[0]["createdOn"].endswith("(01:30 +03:00) 11.11")
        assert "UsrOrder  Name = Order 7" in records.render_hits(hits) and records.render_hits([]) == "(no table holds this Id)"
        e, clio = env({"information_schema.columns": TABLES, 'where "Id" =': []})
        assert records.find_record(e, ID) == [] and len([s for s in clio.statements if s.startswith("select '")]) == 3  # 5 tables in chunks of 2
    finally:
        records.CHUNK = old
    raises(lambda: records.find_record(e, "not-a-guid"), ValueError, "not an Id")
    raises(lambda: records.ident('A"; drop table "B'), ValueError, "not a table or column name")
    assert records._first({"Id": "x", "Name": None, "UsrOrderNumber": "N-7"}) == ("UsrOrderNumber", "N-7")  # no caption column: the first ...Number / ...Name
    assert records._first({"Id": "x", "UsrNote": "n"}) == (None, None)


def test_record_context_names_lookups_filters_columns_and_walks_the_details():
    fk_out = [{"table": "UsrOrder", "column": "UsrContactId", "ref_table": "Contact"}]
    fk_in = [{"table": "UsrOrderItem", "column": "UsrOrderId", "ref_table": "UsrOrder"}, {"table": "UsrOrderLog", "column": "UsrOrderId", "ref_table": "UsrOrder"}]
    row = {**ROW, "UsrContactId": CONTACT, "UsrNote": None}
    item = {"Id": "aa", "Name": "Pump", "UsrOrderId": ID, "UsrContactId": CONTACT, "Extra": 1}
    answers = {'select * from "UsrOrder" where': [row], "kcu.table_name = 'UsrOrder'": fk_out, "ccu.table_name = 'UsrOrder'": fk_in,
               "count(*)": [{"table": "UsrOrderItem", "column": "UsrOrderId", "n": 3}, {"table": "UsrOrderLog", "column": "UsrOrderId", "n": 0}],
               'select * from "UsrOrderItem"': [item], "kcu.table_name = 'UsrOrderItem'": [{"table": "UsrOrderItem", "column": "UsrContactId", "ref_table": "Contact"}],
               'from "Contact" where "Id" in': [{"Id": BOSS, "Name": "Ivan"}, {"Id": CONTACT, "Name": "Olga"}]}
    e, clio = env(answers)
    got = records.record_context(e, "UsrOrder", ID, depth=1, zone="UTC")
    assert got["columns"]["UsrContactId"] == {"id": CONTACT, "name": "Olga"} and "UsrNote" not in got["columns"]  # lookups named, empty columns left out
    assert got["columns"]["CreatedOn"].startswith("2026-11-10 22:30:00 UTC")
    assert [(d["table"], d["count"]) for d in got["details"]] == [("UsrOrderItem", 3)]  # the table with no row for this Id is not listed
    assert got["details"][0]["rows"] == [{"Id": "aa", "UsrOrderId": ID, "Name": "Pump"}] and "offset 0 rows fetch first 20 rows only" in clio.statements[-1]
    deep = records.record_context(e, "UsrOrder", ID, depth=2)["details"][0]["rows"][0]
    assert deep["UsrContactId"] == {"id": CONTACT, "name": "Olga"} and deep["Extra"] == 1  # depth 2: every column of the detail row, its lookups named
    wild = records.record_context(e, "UsrOrder", ID, columns="UsrContact, name", depth=0)  # a lookup named without its Id suffix
    assert sorted(wild["columns"]) == ["Name", "UsrContactId"] and wild["details"] == []
    assert "no other table" not in records.render_context(wild)  # depth 0 did not look at the details
    text = records.render_context(got)
    assert "UsrContactId = Olga (" + CONTACT + ")" in text and "UsrOrderItem.UsrOrderId: 3 row(s), first 1" in text
    e, _ = env({'select * from "UsrOrder" where': []})
    raises(lambda: records.record_context(e, "UsrOrder", ID), KeyError, "no row")


def test_record_cli_exit_codes():
    answers = {"information_schema.columns": TABLES, "where \"Id\" =": [{"schema": "public", "table": "UsrOrder"}], 'select * from "public"."UsrOrder"': [ROW], 'from "Contact" where "Id" in': []}
    code, out = run_cli("record", ["find", "-e", "dev", ID], answers)
    assert code == 0 and "UsrOrder  Name = Order 7" in out
    project = Path(tempfile.mkdtemp()) / "project.json"
    project.write_text(json.dumps({"paths": {"workspace": "ws"}, "environment": {"clioName": "dev", "url": "https://s", "login": "u", "password": "p"}}), encoding="utf-8")
    try:
        assert run_cli("record", ["find", "--project", str(project), ID], answers)[0] == 0  # paths.workspace is read (an empty folder: no objects first)
    finally:
        shutil.rmtree(project.parent, ignore_errors=True)
    code, out = run_cli("record", ["find", "-e", "dev", ID], {"information_schema.columns": TABLES, "where \"Id\" =": []})
    assert code == 1 and "no table holds" in out
    assert run_cli("record", ["find", "-e", "dev", "nope"], answers)[0] == 2
    code, out = run_cli("record", ["context", "-e", "dev", "UsrOrder", ID, "--depth", "0"], {'select * from "UsrOrder"': [ROW], "kcu.table_name": []})
    assert code == 0 and "Name = Order 7" in out


ROLE = {"Id": BOSS, "Name": "UsrManagers", "SysAdminUnitTypeValue": 6}
TEAM, IVAN, OLGA, GHOST = "44444444-4444-4444-4444-444444444444", CONTACT, "55555555-5555-5555-5555-555555555555", "66666666-6666-6666-6666-666666666666"
# the tables the closure is built from: the org role "Sales team" grants the functional role UsrManagers; ivan is in the team by hand, olga in the role by hand
TREE = [{"Id": BOSS, "Name": "UsrManagers", "ParentRoleId": None, "SysAdminUnitTypeValue": 6}, {"Id": TEAM, "Name": "Sales team", "ParentRoleId": None, "SysAdminUnitTypeValue": 1}]
GRANTED = [{"FuncRoleId": BOSS, "OrgRoleId": TEAM}]
BY_HAND = [{"SysUserId": IVAN, "SysRoleId": TEAM}, {"SysUserId": OLGA, "SysRoleId": BOSS}]
CHAIN = {'"ParentRoleId", "SysAdminUnitTypeValue" from "SysAdminUnit"': TREE, 'from "SysFuncRoleInOrgRole"': GRANTED, 'from "SysUserInRole" where': BY_HAND}


def test_role_members_come_from_the_closure_with_the_chain_they_came_through():
    answers = {**CHAIN, 'where "Name" = \'UsrManagers\'': [ROLE],
               'from "SysAdminUnitInRole" ir join': [{"id": IVAN, "member": "ivan", "contact": "Ivan P", "kind": 4}, {"id": OLGA, "member": "olga", "contact": None, "kind": 4},
                                                     {"id": GHOST, "member": "ghost", "contact": None, "kind": 4}]}
    e, clio = env(answers)
    rows = access.role_members(e, "UsrManagers")
    assert rows == [{"member": "ghost", "login": "ghost", "kind": "user", "through": None},  # in the closure, but no table explains it
                    {"member": "Ivan P", "login": "ivan", "kind": "user", "through": "Sales team"}, {"member": "olga", "login": "olga", "kind": "user", "through": ""}]
    members_sql = next(s for s in clio.statements if "SysAdminUnitInRole" in s)
    assert 'ir."SysAdminUnitRoleId" =' in members_sql and 'm."SysAdminUnitTypeValue" = 4' in members_sql and "SysUserInRole" not in members_sql
    assert "Source" not in members_sql  # an integer code on the site, never a unit
    text = access.render_members(rows)
    assert "Ivan P  [user]  through Sales team  login ivan" in text and "olga  [user]  direct" in text and "ghost  [user]  chain not found" in text
    clio.statements.clear()
    units = access.role_members(e, "UsrManagers", units=True)
    assert 'm."SysAdminUnitTypeValue" = 4' not in next(s for s in clio.statements if "SysAdminUnitInRole" in s) and len(units) == 3
    raises(lambda: access.role_members(env({'where "Name" =': []})[0], "UsrNone"), KeyError, "no role named")
    raises(lambda: access.role_members(env({'where "Name" =': [ROLE, dict(ROLE, SysAdminUnitTypeValue=1)]})[0], "UsrManagers"), ValueError, "2 units")


def test_user_roles_and_the_diff_exit_code():
    user = {"Id": IVAN, "login": "ivan", "contact": "Ivan P"}
    answers = {**CHAIN, 'u."SysAdminUnitTypeValue" = 4': [user], 'r."Name" as "role"': [{"id": BOSS, "role": "UsrManagers", "kind": 6}, {"id": TEAM, "role": "Sales team", "kind": 1}],
               'where "Name" = \'UsrManagers\'': [ROLE], 'select "SysAdminUnitId" as "id"': [{"id": IVAN.upper()}]}
    e, _ = env(answers)
    assert access.user_roles(e, "Ivan P") == [{"role": "Sales team", "kind": "division", "through": ""}, {"role": "UsrManagers", "kind": "functional role", "through": "Sales team"}]
    assert access.role_diff(e, ["ivan"], "UsrManagers") == {"present": ["ivan"], "missing": []}
    code, out = run_cli("roles", ["diff", "-e", "dev", "UsrManagers", "ivan"], answers)
    assert code == 0 and "not in UsrManagers: -" in out
    code, out = run_cli("roles", ["diff", "-e", "dev", "UsrManagers", "ivan"], {**answers, 'select "SysAdminUnitId" as "id"': []})
    assert code == 1 and "not in UsrManagers: ivan" in out
    code, out = run_cli("roles", ["user", "-e", "dev", "Ivan P"], answers)
    assert code == 0 and "Sales team  [division]  direct" in out and "UsrManagers  [functional role]  through Sales team" in out
    assert run_cli("roles", ["user", "-e", "dev", "ghost"], {'u."SysAdminUnitTypeValue" = 4': []})[0] == 2
    raises(lambda: access.find_user(env({'u."SysAdminUnitTypeValue" = 4': [user, user]})[0], "ivan"), ValueError, "2 users")


def test_a_setting_shows_each_value_type_and_the_bindings_that_carry_it():
    sid = "e0daf018-43e6-49ea-b5e9-db5bf96372ad"  # the Id of the data fixture's UsrMaxRows setting
    answers = {'from "SysSettings" where "Code" = \'UsrMaxRows\'': [{"Id": sid, "Name": "Max rows", "ValueTypeName": "Integer", "ReferenceSchemaUId": None}],
               'from "SysSettingsValue" where': [{"IntegerValue": 5, "TextValue": "x", "SysAdminUnitId": "00000000-0000-0000-0000-000000000000", "ModifiedOn": "2026-11-11T09:00:00Z", "ModifiedById": BOSS}],
               'from "Contact" where "Id" in': [{"Id": BOSS, "Name": "Ivan"}], 'from "SysAdminUnit" where "Id" in': []}
    e, _ = env(answers)
    got = access.setting_on(e, "UsrMaxRows", zone="UTC")
    assert got[0]["type"] == "Integer" and got[0]["values"][0]["value"] == "5" and got[0]["values"][0]["for"] == "all" and got[0]["values"][0]["modifiedBy"] == "Ivan"
    for type_name, column, raw in (("Boolean", "BooleanValue", True), ("Float", "FloatValue", 1.5), ("DateTime", "DateTimeValue", "2026-01-01"), ("ShortText", "TextValue", "abc"), ("Money", "FloatValue", 2.0)):
        assert access.setting_value({column: raw, "IntegerValue": 9}, type_name) == str(raw)
    assert access.setting_value({"GuidValue": "null"}, "Lookup") == ""
    lookup = {**answers, 'from "SysSettings" where "Code" = \'UsrStatus\'': [{"Id": sid, "Name": "Status", "ValueTypeName": "Lookup", "ReferenceSchemaUId": "55555555-5555-5555-5555-555555555555"}],
              'from "SysSettingsValue" where': [{"GuidValue": CONTACT, "SysAdminUnitId": None}], 'from "SysSchema" where "UId"': [{"Name": "UsrStatus"}],
              'from "UsrStatus" where "Id" in': [{"Id": CONTACT, "Name": "Open"}]}
    shown = access.setting_on(env(lookup)[0], "UsrStatus")[0]["values"][0]
    assert shown["value"] == CONTACT and shown["shown"] == "Open"
    # the workspace's own bindings: the data fixture carries UsrMaxRows (a SysSettings row and its SysSettingsValue row)
    workspace = Path(tempfile.mkdtemp())
    try:
        shutil.copytree(TOOLS / "data" / "tests" / "fixtures" / "UsrPkg", workspace / "packages" / "UsrPkg")
        empty = workspace / "packages" / "UsrPkg" / "Data" / "UsrEmpty"  # an empty data.json (seen in a client workspace) is skipped
        empty.mkdir()
        (empty / "descriptor.json").write_text('{"Descriptor": {"UId": "0", "Name": "UsrEmpty"}}', encoding="utf-8")
        (empty / "data.json").write_text("", encoding="utf-8")
        answer = access.sys_setting("UsrMaxRows", {"dev": e}, workspace)
        assert answer["bindings"] == [{"package": "UsrPkg", "binding": "SysSettingsValue_UsrMaxRows", "value": "10000", "for": "a29a3ba5-4b0d-de11-9a51-005056c00008"}]
        text = access.render_setting(answer)
        assert "dev: Max rows [Integer]" in text and "for all: '5'" in text and "binding UsrPkg/SysSettingsValue_UsrMaxRows: would write '10000'" in text
        assert access.sys_setting("UsrOther", {"dev": env({'from "SysSettings" where "Code"': []})[0]}, workspace)["bindings"] == []
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_setting_cli_runs_on_every_environment_and_exits_1_for_a_missing_one():
    sid = "e0daf018-43e6-49ea-b5e9-db5bf96372ad"
    answers = {'from "SysSettings" where "Code"': [{"Id": sid, "Name": "Max rows", "ValueTypeName": "Integer", "ReferenceSchemaUId": None}],
               'from "SysSettingsValue" where': [{"IntegerValue": 7, "SysAdminUnitId": None}]}
    code, out = run_cli("setting", ["UsrMaxRows", "-e", "dev,test"], answers)
    assert code == 0 and "  dev: Max rows" in out and "  test: Max rows" in out
    code, out = run_cli("setting", ["UsrMaxRows", "-e", "dev"], {'from "SysSettings" where "Code"': []})
    assert code == 1 and "dev: no such setting" in out
    # one environment that cannot be read does not hide the others
    broken = {**answers, 'from "SysSettings" where "Code"': lambda t: (_ for _ in ()).throw(RuntimeError("sql: 42P01: relation does not exist"))}
    code, out = run_cli("setting", ["UsrMaxRows", "-e", "dev,test"], broken)
    assert code == 1 and "dev: error: sql: 42P01" in out and "test: error: sql: 42P01" in out, out
    assert run_cli("setting", ["UsrMaxRows"], answers)[0] == 2  # no environment named
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / "project.json"
        project.write_text(json.dumps({"environments": ["dev", "test"], "environment": {"clioName": "dev", "url": "https://s", "login": "u", "password": "p"}}), encoding="utf-8")
        code, out = run_cli("setting", ["UsrMaxRows", "--project", str(project)], answers)
        assert code == 0 and "  test: Max rows" in out


def test_local_time_names_both_zones():
    assert records.local_time("2026-07-01T10:00:00Z", "+03:00") == "2026-07-01 10:00:00 UTC (13:00 +03:00)"
    assert records.local_time("2026-07-01 23:30:00", "UTC+3").endswith("(02:30 UTC+3) 02.07")  # another day there
    assert records.local_time("2026-07-01T10:00:00Z", "-05:30").endswith("(04:30 -05:30)")
    assert records.local_time(None) == "" and records.local_time("not a date") == "not a date"
    assert "local, zone 'No/Such_Zone' unknown here" in records.local_time("2026-07-01T10:00:00Z", "No/Such_Zone")  # an unknown name falls back to the machine's
    assert records.local_time("2026-07-01T10:00:00Z").startswith("2026-07-01 10:00:00 UTC (") and "local)" in records.local_time("2026-07-01T10:00:00Z")


RUN = "44444444-4444-4444-4444-444444444444"
RUNS = [{"Id": RUN, "Name": "Order", "Status": "Error", "ErrorDescription": "Expression expected\n   at Terrasoft.Core.Process.X()",
         "StartDate": "2026-11-11T08:00:05", "CompleteDate": None, "OwnerId": BOSS, "Process": "UsrOrder_Process"},
        {"Id": ID, "Name": "Sync", "Status": "Completed", "ErrorDescription": None, "StartDate": "2026-11-11T08:00:07",
         "CompleteDate": "2026-11-11T08:00:08", "OwnerId": None, "Process": "UsrSyncNoise_Process"}]


def test_process_runs_by_process_and_noise():
    from creatio_schemas import runs
    e, clio = env({'from "SysProcessLog" l': RUNS, 'from "Contact" where "Id" in': [{"Id": BOSS, "Name": "Ivan"}]})
    answer = runs.process_runs(e, process="UsrOrder_Process", since="2026-11-11", until="2026-11-11T10:00:00+02:00", limit=5, noise=["UsrSync"])
    statement = clio.statements[0]
    assert "s.\"Name\" = 'UsrOrder_Process'" in statement and "l.\"StartDate\" >= '2026-11-11 00:00:00'" in statement, statement
    assert "l.\"StartDate\" <= '2026-11-11 08:00:00'" in statement and "fetch first 5 rows only" in statement and "desc" in statement, statement
    assert answer["hidden"] == 0 and len(answer["runs"]) == 2  # a process asked by name is never hidden as noise
    first = answer["runs"][0]
    assert (first["id"], first["state"], first["error"], first["owner"]) == (RUN, "failed", "Expression expected", "Ivan"), first
    e, clio = env({'from "SysProcessLog" l': RUNS, 'from "Contact" where "Id" in': []})
    answer = runs.process_runs(e, limit=5, noise=["UsrSync"])
    assert answer["hidden"] == 1 and [r["process"] for r in answer["runs"]] == ["UsrOrder_Process"] and "fetch first 25 rows only" in clio.statements[0]
    assert runs.render_runs(answer).endswith("1 runs of noise processes hidden")
    e, clio = env({'from "SysProcessLog" l': [], 'from "Contact" where "Id" in': []})
    runs.process_runs(e, process="AAAAAAAA-0000-0000-0000-000000000001")
    assert "s.\"Name\" in (select \"Name\" from \"SysSchema\" where \"UId\" = 'aaaaaaaa-0000-0000-0000-000000000001')" in clio.statements[0]
    assert runs.render_runs(runs.process_runs(e, process="UsrNone")) == "(no runs)"
    raises(lambda: runs.process_runs(e, process="Usr'; drop"), ValueError, "not a table or column name")
    raises(lambda: runs.process_runs(e, since="yesterday"), ValueError, "not a date")


def test_process_runs_around_a_record_and_its_details():
    from creatio_schemas import runs
    fks = [{"table": "UsrOrderItem", "column": "UsrOrderId", "ref_table": "UsrOrder"}, {"table": "UsrZ", "column": "UsrOrderId", "ref_table": "UsrOrder"}]
    answers = {'select "ModifiedOn" from "UsrOrder" where': [{"ModifiedOn": "2026-11-11T08:00:00"}], "ccu.table_name = 'UsrOrder'": fks,
               'select "ModifiedOn" from "UsrOrderItem"': [{"ModifiedOn": "2026-11-11T08:00:20"}, {"ModifiedOn": "2026-11-11T09:00:00Z"}],
               'from "SysProcessLog" l': RUNS, 'from "Contact" where "Id" in': []}
    e, clio = env(answers)
    answer = runs.process_runs(e, record=f"UsrOrder:{ID}", window=30, noise=["UsrSync"])
    query = next(s for s in clio.statements if 'from "SysProcessLog" l' in s)
    # 08:00:00 and 08:00:20 overlap into one window, 09:00:00 is its own; the chronology is oldest first
    assert "between '2026-11-11 07:59:30' and '2026-11-11 08:00:50' or l.\"StartDate\" between '2026-11-11 08:59:30' and '2026-11-11 09:00:30'" in query, query
    assert "asc" in query and answer["hidden"] == 1 and len(answer["windows"]) == 2
    assert runs.render_runs(answer).startswith("changes of the record: 2026-11-11 07:59:30 UTC (")
    # a detail table without ModifiedOn fails its union: each table is then asked alone, the rest still counts
    answers['select "ModifiedOn" from "UsrOrderItem"'] = lambda text: (_ for _ in ()).throw(RuntimeError("sql: 42703")) if "union all" in text else [{"ModifiedOn": "2026-11-11T08:00:20"}]
    e, clio = env(answers)
    assert len(runs.process_runs(e, record=f"UsrOrder:{ID}")["windows"]) == 1
    e, _ = env({'select "ModifiedOn" from "UsrOrder" where': []})
    raises(lambda: runs.process_runs(e, record=f"UsrOrder:{ID}"), KeyError, "no row")
    raises(lambda: runs.process_runs(e, record="UsrOrder:x"), ValueError, "not an Id")


def test_process_error_trims_frames_and_names_the_element():
    from creatio_schemas import runs
    text = ("Terrasoft.Common.ItemNotFoundException: Column UsrX not found ---> System.Exception: inner\n"
            "   at Terrasoft.Core.Entities.EntitySchema.GetColumn(String name)\n   --- End of inner exception stack trace ---\n"
            "   at Terrasoft.Core.Process.ProcessEngine.Run()\nSecond message line")
    elements = [{"Caption": "Read order", "Status": "Error", "ErrorDescription": "Column UsrX not found\n   at Terrasoft.X()", "StartDate": "2026-11-11T08:00:06", "CompleteDate": None},
                {"Caption": "Start", "Status": "Completed", "ErrorDescription": None, "StartDate": "2026-11-11T08:00:05", "CompleteDate": "2026-11-11T08:00:05"}]
    e, clio = env({'from "SysProcessLog" l': [dict(RUNS[0], ErrorDescription=text)], 'from "SysProcessElementLog" e': elements})
    answer = runs.process_error(e, RUN, "+03:00")
    assert answer["error"] == "Terrasoft.Common.ItemNotFoundException: Column UsrX not found ---> System.Exception: inner\nSecond message line", answer["error"]
    assert answer["element"] == {"caption": "Read order", "status": "Error", "start": "2026-11-11 08:00:06 UTC (11:00 +03:00)", "error": "Column UsrX not found"}
    assert f"e.\"SysProcessId\" = '{RUN}'" in clio.statements[1] and "order by e.\"StartDate\" desc" in clio.statements[1]
    shown = runs.render_error(answer)
    assert shown.splitlines()[1] == "stopped on: Read order (Error, started 2026-11-11 08:00:06 UTC (11:00 +03:00))" and "   at " not in shown, shown
    # no failed element: the newest one that never completed is where it waits
    waiting = [dict(elements[0], Status="Running", ErrorDescription=None, Caption="Wait for signal"), elements[1]]
    e, _ = env({'from "SysProcessLog" l': [dict(RUNS[0], ErrorDescription=None, Status="Running")], 'from "SysProcessElementLog" e': waiting})
    assert runs.process_error(e, RUN)["element"]["caption"] == "Wait for signal"
    e, _ = env({'from "SysProcessLog" l': []})
    raises(lambda: runs.process_error(e, RUN), KeyError, "no SysProcessLog row")
    code, out = run_cli("proc-runs", ["error", "-e", "dev", RUN], {'from "SysProcessLog" l': [dict(RUNS[0], ErrorDescription=text)], 'from "SysProcessElementLog" e': elements})
    assert code == 1 and "stopped on: Read order" in out, out
    project = Path(tempfile.mkdtemp()) / "project.json"
    project.write_text(json.dumps({"environment": {"clioName": "dev", "url": "https://p.example", "timeZone": "+02:00", "noiseProcesses": ["UsrSync"]}}), encoding="utf-8")
    try:
        code, out = run_cli("proc-runs", ["runs", "--project", str(project)], {'from "SysProcessLog" l': RUNS, 'from "Contact" where "Id" in': []})
        assert code == 0 and "1 runs of noise processes hidden" in out and "(10:00 +02:00)" in out, out
        code, out = run_cli("proc-runs", ["runs", "-e", "dev", "--process", "UsrNone"], {'from "SysProcessLog" l': [], 'from "Contact" where "Id" in': []})
        assert code == 1 and "(no runs)" in out
        assert run_cli("proc-runs", ["runs", "-e", "dev", "--record", "UsrOrder:x"], {})[0] == 2
    finally:
        shutil.rmtree(project.parent, ignore_errors=True)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
