---
description: Creatio environment tools - one Python client (Environment) for a site - login with cookies and BPMCSRF, OData 4 CRUD, service calls with the WCF fault page reduced to one line, RunProcess with result parameters, SQL through clio as JSON rows - and five command lines - sql.py (rows as JSON or CSV, statements split, [ERR] is exit 1), call.py (status + JSON), proc-run.py, unit.py (the in-Creatio tests of a project, the integration tier) and api.py (members and overloads of a platform type by reflection over a local bin folder).
---

# Environment tools: SQL, service calls, processes, in-Creatio tests, platform API signatures

Every agent that touched a site wrote a private script for the same five things. These replace
them. Pure Python standard library (`api.py` also needs Windows PowerShell).

| File | What it does |
| --- | --- |
| `sql.py` | SQL through clio: rows as JSON (default) or `--csv`, one statement per clio call |
| `call.py` | `GET`/`POST`/`PATCH`/`PUT`/`DELETE` a site path with login and CSRF: status, then JSON or the fault |
| `proc-run.py` | start a process, print its result parameters |
| `unit.py` | `run --category` / `--class`: the project's in-Creatio tests, one row per test |
| `api.py` | public members of a platform type from the assemblies of a local installation |
| [`../creatio_schemas/environment.py`](../creatio_schemas/README.md) | the library: `Environment`, `Response` |
| `tests/test_env_tools.py` | a fake HTTP opener and a fake clio; no site needed |

```bash
python sql.py -e dev 'select "Name", "Maintainer" from "SysPackage" where "Name" like '"'"'Usr%'"'"''
python sql.py -e dev --file q.sql --csv                 # the file form is the safe one from PowerShell
python call.py -e dev POST rest/UsrOrderService/Recalc '{"orderId": "..."}'
python proc-run.py -e dev UsrOrder_Process OrderId=<guid> --result Total
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
<!-- commands:end -->

## Which site

`-e <name>` reads the url, login, password and `IsNetCore` of a clio environment from clio's
settings file (`%LOCALAPPDATA%\creatio\clio\appsettings.json`); `--project project.json` reads the
loop's `environment` block (`url`, `login`, `password`, `clioName`; `isNetCore`, or clio's value for
`clioName`, else .NET Framework). SQL always runs through clio, so it needs the clio name.

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
  `Status`/`Outcome`, `Message`/`Error`). `--evidence` writes the whole answer.
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

The fake-opener tests: login once and the CSRF echo, a refused login without the password in the
message, OData select/filter/top/orderby and insert/update/delete, both platforms' paths, the fault
reductions, RunProcess success and failure, statement splitting and the clio file form, the five CLIs'
exit codes. `api.py` against a local 8.3.2 installation's `bin/`: `Terrasoft.Core.DB.Select` with its
eight `Column` overloads and `CustomQueryFunction` (base `QueryFunction`) with its constructors. No
site was called: the HTTP and SQL paths are proved by fakes only.

## Checks

```bash
python tests/test_env_tools.py
```
