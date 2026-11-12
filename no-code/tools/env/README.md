---
description: Creatio environment tools - one Python client (Environment) for a site - login with cookies and BPMCSRF, OData 4 CRUD, service calls with the WCF fault page reduced to one line, RunProcess with result parameters, SQL through clio as JSON rows - and nine command lines - record.py (which table holds an Id, a record with its lookups named and its details), roles.py (role members, a user's roles and a diff - nested roles included), setting.py (a setting across environments and bindings), sql.py (rows as JSON or CSV, statements split, [ERR] is exit 1), call.py (status + JSON), proc-run.py (the result parameters and the run's SysProcessLog row), proc-runs.py (the runs of a process or around a record's changes, one run's error without stack frames), unit.py (the in-Creatio tests of a project, the integration tier) and api.py (members and overloads of a platform type by reflection over a local bin folder).
---

# Environment tools: SQL, service calls, processes, in-Creatio tests, platform API signatures

Every agent that touched a site wrote a private script for the same five things. These replace
them. Pure Python standard library (`api.py` also needs Windows PowerShell).

| File | What it does |
| --- | --- |
| `sql.py` | SQL through clio: rows as JSON (default) or `--csv`, one statement per clio call |
| `call.py` | `GET`/`POST`/`PATCH`/`PUT`/`DELETE` a site path with login and CSRF: status, then JSON or the fault |
| `proc-run.py` | start a process, print its result parameters and its `SysProcessLog` row; exit 1 unless completed |
| `proc-runs.py` | `runs` of a process, or around the changes of a record; `error` of one run without stack frames |
| `unit.py` | `run --category` / `--class`: the project's in-Creatio tests, one row per test |
| `api.py` | public members of a platform type from the assemblies of a local installation |
| `record.py` | `find` the table that holds an Id; `context` of a record: lookups named, the rows that point at it |
| `roles.py` | `members` of a role, the roles of a `user`, a `diff` of users against a role - the closure, nested roles included |
| `setting.py` | a system setting on each environment with date and author, and the workspace bindings that set it |
| [`../creatio_schemas/records.py`, `access.py`](../creatio_schemas/README.md) | the library behind them |
| `tests/test_env_snapshot.py` | the snapshot's site lines through a FakeClio (chunks of 50, a planted difference) |
| `tests/test_env_forensics.py` | a scripted clio: every statement answered by what it contains; no site needed |
| [`../creatio_schemas/environment.py`](../creatio_schemas/README.md) | the library: `Environment`, `Response` |
| `tests/test_env_tools.py` | a fake HTTP opener and a fake clio; no site needed |

```bash
python sql.py -e dev 'select "Name", "Maintainer" from "SysPackage" where "Name" like '"'"'Usr%'"'"''
python sql.py -e dev --file q.sql --csv                 # the file form is the safe one from PowerShell
python call.py -e dev POST rest/UsrOrderService/Recalc '{"orderId": "..."}'
python proc-run.py -e dev UsrOrder_Process OrderId=<guid> --result Total
python proc-runs.py runs -e dev --record UsrOrder:<id>      # what ran when the record was saved
python proc-runs.py error -e dev <log id>
python unit.py run --project project.json --category UsrOrders --evidence evidence/unit.json
python api.py Terrasoft.Core.DB.Select Column --bin "<site>/Terrasoft.WebApp/bin"
```

## Commands

<!-- commands:start -->
### env sql

```
python sql.py -e <env> "select ..."                 rows of every statement as JSON
python sql.py -e <env> --file q.sql --csv           statements split on ';' at line ends, each run alone
python sql.py --project project.json "update ..."   an update/insert prints "(no rows)"
```

### env call

```
python call.py -e <env> POST ServiceModel/UsrOrderService.svc/Recalc '{"orderId": "..."}'
python call.py -e <env> POST rest/UsrOrderService/Recalc --file body.json
python call.py -e <env> GET odata/Contact?$top=1
```

### env proc-run

```
python proc-run.py -e <env> UsrOrder_Process OrderId=<guid> Quantity=3 --result Total --result Status
```

### env unit

```
python unit.py run --project project.json --category UsrOrders [--evidence result.json]
python unit.py run -e <env> --runner UsrRunTests_Process --class UsrOrderTest
```

| command | what it does |
| --- | --- |
| `run` | run the tests of a category or a class |

### env api

```
python api.py Terrasoft.Core.DB.Select --bin <site>/Terrasoft.WebApp/bin
python api.py Select Column                       # a short name; members whose name starts with "Column"
python api.py EntitySchemaQuery AddColumn --bin <folder>   (or set CREATIO_BIN)
```

### env record

```
python record.py find    -e <env> <id> [--workspace <folder>] [--everywhere]
python record.py context -e <env> <Entity> <id> [--columns "Name,*Id"] [--depth 1|2]
```

| command | what it does |
| --- | --- |
| `find` | the table(s) that hold an Id, with caption, dates and authors |
| `context` | a record with its lookups named and the rows that point at it |

### env roles

```
python roles.py members -e <env> <Role> [--units]
python roles.py user    -e <env> <login or contact name>
python roles.py diff    -e <env> <Role> <user>[,<user>...]
```

| command | what it does |
| --- | --- |
| `members` | the users (and with --units the units) a role reaches |
| `user` | the roles a user has, direct or through another unit |
| `diff` | the users of a list who are not in the role (exit 1) |

### env setting

```
python setting.py <Code> -e dev,test [--workspace <folder>]
python setting.py <Code> --project project.json        (its `environments` list, else `environment.clioName`)
```

### env proc-runs

```
python proc-runs.py runs  -e <env> --process UsrOrder_Process [--limit 20] [--since 2026-11-11] [--until ...]
python proc-runs.py runs  -e <env> --record UsrOrder:<id> [--window 30]
python proc-runs.py error -e <env> <log id>
```

| command | what it does |
| --- | --- |
| `runs` | the runs of a process, or the runs around the changes of a record |
| `error` | one run's error without stack frames, and the element it stopped on |
<!-- commands:end -->

## Which site

`-e <name>` reads the url, login, password and `IsNetCore` of a clio environment from clio's
settings file (`%LOCALAPPDATA%\creatio\clio\appsettings.json`); `--project project.json` reads the
loop's `environment` block (`url`, `login`, `password`, `clioName`; `isNetCore`, or clio's value for
`clioName`, else .NET Framework). SQL always runs through clio, so it needs the clio name.

## Forensics: records, roles, settings

Three commands answer what an author used to find out table by table. Every statement they send is below, so a human can
run it with `sql.py`; none writes. Times print in UTC and in `environment.timeZone` of `project.json` (`+03:00`, `UTC-5`
or an IANA name where the machine has the tz database; else the machine's zone, said so).

**`record.py find <id>`** - `information_schema.columns` joined to `information_schema.tables` for the base tables with a
uuid `Id` (`data_type in ('uuid', 'uniqueidentifier')`: PostgreSQL and MS SQL), then
`select '<T>' as "table" from "<T>" where "Id" = '<id>'` joined with `union all` in batches of 50 tables - the objects of
`--workspace` first, the scan stops after the first batch with a hit unless `--everywhere` - then `select * from "<T>"
where "Id" = ...` for each table found, and `Contact."Name"` of its `CreatedById` / `ModifiedById`. The caption is the
first non-empty of `Name`, `Caption`, `Title`, `Subject`, `Number`.

**`record.py context <Entity> <id>`** - `select *` of the row; the foreign keys of the table
(`referential_constraints` + `key_column_usage` + `constraint_column_usage`, never guessed from a column name) name every
lookup by the `Name` of the referenced row; `--columns "Name,Usr*Id"` picks columns by `*` wildcards (default: every
column with a value). `--depth 1` adds the tables with a foreign key to the entity, a `count(*)` per table in unions of 50,
and for each table with rows the first 20 (`order by "Id" offset 0 rows fetch first 20 rows only`: the Id, the column that
points here and a caption column); `--depth 2` names the lookups of those rows too.

**`roles.py`** - who is in a role comes from `SysAdminUnitInRole`, the closure the platform keeps (`SysAdminUnitId` the
member, `SysAdminUnitRoleId` the role), joined to `SysAdminUnit` for names and `SysAdminUnitTypeValue` for the kind
(0 organization, 1 division, 2 manager, 4 user, 6 functional role; users only unless `--units`). *Why* a user is in it
comes from the tables the closure is built from, read once each: `SysUserInRole` (`SysUserId`, `SysRoleId`: a user put
in a role by hand, `direct`), `SysAdminUnit.ParentRoleId` (the org and functional trees) and `SysFuncRoleInOrgRole`
(`SysFuncRoleId`, `SysOrgRoleId`: a functional role granted to an org role); `through <role>` names the direct role the
chain starts from, `chain not found` says the closure has a row none of the three explains. The closure's `Source`
column is an integer code (1, 2, 16, 18 on the test site) and is not read. A user is found by login
(`SysAdminUnit.Name`) or contact name; two matches are refused with both logins, and so is a role name two units share.
`diff` exits 1 when a user of the list is not in the role.

**`setting.py <Code> -e dev,test`** - on each environment `SysSettings` by `Code`, then `SysSettingsValue` by
`SysSettingsId`: the value column follows `ValueTypeName` (`IntegerValue`, `FloatValue` for Float and Money,
`BooleanValue`, `DateTimeValue` for DateTime, Date and Time, `GuidValue` for Lookup, else `TextValue`), a lookup is shown by
the `Name` of the row in the object `ReferenceSchemaUId` names, with `ModifiedOn` and the author. With `--workspace` it
reads every `Data/*` binding of `SysSettingsValue` in the workspace's packages whose row names this setting (its Id on
the site, or a `SysSettings` binding with this `Code`) and prints the value a push would write. `--project` uses its
optional `environments` list (clio names), else its own environment.

## Snapshot of an object

The site half of `describe.py snapshot` (`creatio_schemas/integrity.py`); PostgreSQL, SELECTs only.

```sql
-- table <T> column <col> <type>[(len)] [null]
select column_name::text as "column", data_type::text as "type", character_maximum_length::text as "length", is_nullable::text as "nullable"
from information_schema.columns where table_schema = current_schema() and table_name = '<T>' order by 1
-- rows <n>
select count(*) as "n" from "<T>"
-- checksum <col> <md5>: 50 columns a statement, every column but Id unless --columns names them
select md5(string_agg(coalesce("<col1>"::text, ''), '|' order by "Id")) as "c0", md5(string_agg(coalesce("<col2>"::text, ''), '|' order by "Id")) as "c1" from "<T>"
```

`copy <package> extendParent=<bool>` is `describe.py layers` (one line per copy, in the platform's order). A column the
removed layer defined stays in the table (S24-T01), so a merge that forgets one shows as a `table` line that did not move
while the disk side lost its `column` line, and as a `checksum` that changed when the data went. On a big table name the
columns: a checksum reads every row.

## References to a layer a merge removes

`describe.py merge -e` (S24-T04) runs these before it writes anything; a count above 0 stops the merge with
`references: <table>.<column> <n> rows point at <package>'s <Object>` - the install of the removal would fail whole
on that foreign key (`23503`, the package install is one transaction; S24-T01).

```sql
-- the SysSchema rows of the layers to remove
select s."Id"::text "id", p."Name"::text "package" from "SysSchema" s join "SysPackage" p on p."Id" = s."SysPackageId"
where s."Name" = '<Object>' and s."ManagerName" = 'EntitySchemaManager' and p."Name" in ('<pkg>', ...);
-- every NO ACTION foreign key to SysSchema.Id on this site (18 on a 8.2.3 test site)
select tc.table_name::text "table", kcu.column_name::text "column"
from information_schema.table_constraints tc
join information_schema.key_column_usage kcu on kcu.constraint_name = tc.constraint_name
join information_schema.referential_constraints rc on rc.constraint_name = tc.constraint_name
join information_schema.constraint_column_usage ccu on ccu.constraint_name = tc.constraint_name
where tc.constraint_type = 'FOREIGN KEY' and ccu.table_name = 'SysSchema' and ccu.column_name = 'Id' and rc.delete_rule = 'NO ACTION';
-- one count per key, in one statement
select '<table>.<column>' "ref", "<column>"::text "id", count(*)::text "n" from "<table>" where "<column>" in ('<id>', ...) group by "<column>"
union all ...
```

## Process runs

The id `RunProcess` answers is the run's `SysProcessLog.Id`. Every statement (`creatio_schemas/runs.py`):

```sql
-- one run (proc-run.py after the results; process_error)
select l."Id", l."Name", st."Name" as "Status", l."ErrorDescription", l."StartDate", l."CompleteDate",
       l."OwnerId", s."Name" as "Process"
from "SysProcessLog" l
left join "SysProcessStatus" st on st."Id" = l."StatusId"
left join "SysSchema" s on s."Id" = l."SysSchemaId"
where l."Id" = '<id>'
-- runs --process: the same select, where s."Name" = '<Name>' (a UId: s."Name" in (select "Name" from "SysSchema"
-- where "UId" = '<uid>'), so every copy of the schema), [and l."StartDate" >= / <= '<UTC>'],
-- order by l."StartDate" desc offset 0 rows fetch first <limit> rows only
-- runs --record: select "ModifiedOn" from "<Entity>" where "Id" = '<id>', then the foreign keys that point at the
-- table (the record.py context query) and select "ModifiedOn" from "<T>" where "<column>" = '<id>' in unions of 50;
-- each moment +-window seconds (overlaps merged) is one l."StartDate" between '<lo>' and '<hi>', order asc
-- the element a run stopped on
select e."Caption", st."Name" as "Status", e."ErrorDescription", e."StartDate", e."CompleteDate"
from "SysProcessElementLog" e left join "SysProcessStatus" st on st."Id" = e."StatusId"
where e."SysProcessId" = '<id>' order by e."StartDate" desc
```

A run is `failed` when it has an `ErrorDescription` or its status name says error or cancel, `completed` when it has a
`CompleteDate`, else `running` (a process waiting on a signal or a user task); the status name itself is printed as the
site has it, in its language. `proc-run.py` exits 1 unless the run is completed; with no log row it says so and
keeps the engine's answer. `error` drops the stack frames (`   at ...`, `--- End of inner exception stack trace ---`) and
keeps every message line; the element is the newest with an error, else the newest that never completed.
`environment.noiseProcesses` of `project.json` (names or prefixes) hides runs of those processes from `runs --record`
and the unfiltered list, with the line `N runs of noise processes hidden`; `--process` never hides what it names.

## How it works

- **Login** is `ServiceModel/AuthService.svc/Login` at the site root, once, lazily. Its cookies are kept
  and sent back; every request carries `ForceUseSession: true` and the `BPMCSRF` cookie as a header.
- **Paths** are site-relative. For `odata/`, `ServiceModel/`, `rest/` and `DataService/` the `0/` prefix
  is added on .NET Framework and dropped on .NET Core, so one command works on both.
- **Errors**: `get`/`post`/`patch`/`delete`/`call_service` never raise on a non-2xx answer;
  `Response.error` is `"<status>: <reason>"`, the reason taken from a JSON `Message` /
  `ExceptionMessage` / `errorInfo.message`, else the WCF fault page's "The exception message is '...'",
  else its `<title>`, else its first line of text. `odata*` and `run_process` raise `RuntimeError` with
  that line. A WCF answer of type string (`<string xmlns=...>{json}</string>`) is unwrapped by
  `Response.json()`.
- **SQL**: each statement (split on a `;` at a line end) is written to a file and run with
  `execute-sql-script -f <file> -v json -d <result>` - the file form keeps double quotes, which the
  positional form loses from PowerShell. clio exits 0 on an SQL error; `[ERR]` in its output is the
  failure. A statement without a result (update, insert) gives no rows. `sql_exec` is the positional
  form for one statement without a result.
- **Processes**: `ProcessEngineService.svc/RunProcess` with `parameterValues` and
  `resultParameterNames`, the shape the test framework's process tier uses; `proc-run.py` sends a
  value as JSON when it parses (`3`, `true`, `null`), otherwise as text.
- **In-Creatio tests** (`unit.py`): `project.json` `tests.runner` names a process (its result parameter
  `tests.resultParameter`, default `Result`) or a service path (`.svc/` or `rest/`, POSTed with
  `{<parameter>: <value>}`); `tests.categoryParameter` / `tests.classParameter` (default `Category` /
  `Class`) carry the selection. The answer's first list of objects is the list of tests; a test's name,
  outcome and message are read from the usual key names (`Name`/`TestName`, `Success`/`Passed` or
  `Status`/`Outcome`, `Message`/`Error`). `--evidence` writes the whole answer. The failed tests print
  first with their messages, then the passed ones, then `N passed, M failed` (MCP `run_tests`). With
  `tests.package` or `--package` (the package that holds the tests) it warns
  `the test package's dll is older than its last push` when `SysPackage.ModifiedOn` is newer than the
  last successful compilation: `select p."ModifiedOn" as "changed", (select max(h."CreatedOn") from
  "CompilationHistory" h where h."ProjectName" like '%<Package>%' and h."Result" = true) as "compiled"
  from "SysPackage" p where p."Name" = '<Package>'` (`= 1` on MS SQL, tried when `true` fails). Not
  verified on a site: what `CompilationHistory.ProjectName` holds for a package compiled by
  `compile-package` is assumed to contain the package name; when no row matches, the warning says so.
- **API signatures** (`api.py`): Windows PowerShell loads the assemblies reflection-only (no code
  runs), resolving dependencies from the same folder; an assembly whose types load only partly still
  answers for the types that do. A full name stops at the first assembly that has it, and the
  assembly named like its namespace is tried first (`Terrasoft.Core.DB.Select` - about 1 s); a short
  name scans the folder (a few seconds on a 446-assembly `bin/`).

## Traps

- Credentials never appear in an error, a log line or `repr(Environment)`; evidence files hold the
  answers only.
- `unit.py` guesses the result keys: when a project's runner answers in another shape the command
  exits 2 with the start of the answer - add its keys to `NAME_KEYS` / `PASS_KEYS` in `unit.py`.
- `api.py` on a .NET Core site: point `--bin` at its `.application/net-framework/core-bin` copy;
  Windows PowerShell 5.1 cannot load .NET Core-only assemblies.

## Verified

The forensics commands: the scripted-clio tests in `tests/test_env_forensics.py` (the chunked union and the workspace-first order, the foreign-key walk, wildcards, nested membership with its chain, the diff's exit code, a setting of each value type, a binding row found in the data fixture). No site was queried: the statements are proved by fakes, and the meaning of `SysAdminUnitInRole.Source` and the `SysAdminUnitTypeValue` numbers is as the feedback and Creatio's documentation give it.


The fake-opener tests: login once and the CSRF echo, a refused login without the password in the
message, OData select/filter/top/orderby and insert/update/delete, both platforms' paths, the fault
reductions, RunProcess success and failure, statement splitting and the clio file form, the five CLIs'
exit codes. `api.py` against a local 8.3.2 installation's `bin/`: `Terrasoft.Core.DB.Select` with its
eight `Column` overloads and `CustomQueryFunction` (base `QueryFunction`) with its constructors. No
site was called: the HTTP and SQL paths are proved by fakes only.

## Checks

```bash
python tests/test_env_tools.py
python tests/test_env_forensics.py
```
