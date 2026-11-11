---
description: Creatio package SQL scripts (SqlScripts) of 8.x as files - create views, functions, triggers and data fixes per database engine (MSSQL, Oracle, PostgreSQL), install type (before / after package, after data, uninstall), run order through dependencies; push installs them; probe shows what the environment recorded.
---

# SQL script tools

Scripts that create and change a package's **SQL scripts** - the database objects and data fixes
the platform runs while it installs the package. Pure Python standard library.

| File | What it does |
| --- | --- |
| `sqlscripts.py` | CLI (the commands are listed under Commands) |
| [`../creatio_schemas/sqlscript.py`](../creatio_schemas/README.md) | the library (`SqlScript`) |
| `tests/` | `python tests/test_sqlscripts_tools.py` |

Verified on Creatio 8.2.3 (the test environment, PostgreSQL): four scripts built only with these tools were
installed by `clio push-pkg` - a function, a view that uses it (named so that it sorts first and
still ran second, through its dependency), a run log and an MSSQL script the PostgreSQL install
skipped. All 39 scripts found locally (your packages and the platform's ProcessLibrary)
round-trip byte-for-byte.

## Commands

<!-- commands:start -->
```
python sqlscripts.py list     <package>
python sqlscripts.py inspect  <package> <Script>
python sqlscripts.py new      <package> <Script> --file body.sql [--engine postgresql] [--install after-package] [--after Other ..] [--backward-compatible]
python sqlscripts.py set      <package> <Script> [--file body.sql] [--engine ..] [--install ..] [--backward-compatible on|off]
python sqlscripts.py depend   <package> <Script> add <Other> [--uid U] | remove <Other>
python sqlscripts.py validate <package> <Script>
python sqlscripts.py run      <package> <Script> --env dev        run the body on an environment now (a dev check, not an install)
python sqlscripts.py probe    <package> <Script> --env dev        what the environment recorded for the installed script
```

| command | what it does |
| --- | --- |
| `list` | the scripts of a package |
| `new` | create a script |
| `inspect` | engine, install type, dependencies, problems |
| `validate` | problems; exit code 1 on errors |
| `set` | change the body or the settings |
| `depend` | scripts that must run before this one |
| `run` | run the body on an environment now (dev check; the install runs it on push) |
| `probe` | what the environment recorded for the installed script |
<!-- commands:end -->

## The loop

```bash
python sqlscripts.py new   UsrPkg UsrVwOrderTotalsPostgreSql --file vw.sql --after UsrFnOrderTotalPostgreSql
python sqlscripts.py run   UsrPkg UsrVwOrderTotalsPostgreSql --env dev     # try the body now (optional)
clio push-pkg UsrPkg -e dev                                                 # installs, runs the scripts
python sqlscripts.py probe UsrPkg UsrVwOrderTotalsPostgreSql --env dev     # recorded? error? same body?
```

## How a script is stored

```
SqlScripts/<Name>/descriptor.json   {"SqlScript": {UId, Name, DBEngineType, InstallType, ModifiedOnUtc,
                                     BackwardCompatibilityConfirmed, DependsOn: [{UId, Name}]}}   BOM, CRLF
SqlScripts/<Name>/<Name>.sql        the body, UTF-8 without BOM
```

| Field | Values (8.x designer) |
| --- | --- |
| `DBEngineType` | 0 MSSql, 1 Oracle, 2 PostgreSql - the script runs only on that engine |
| `InstallType` | 0 BeforePackage, 1 AfterPackage (default, after the schemas and their tables), 2 AfterSchemaData (after the data bindings), 3 UninstallApp |
| `DependsOn` | scripts of any package that must run first; `depend add` resolves the UId from the workspace, `--uid` for one outside it |
| `BackwardCompatibilityConfirmed` | the designer's "backward compatible" checkbox |

## Traps (verified on 8.2.3)

- **A script runs when it is new or its body changed - not on every push.** An unchanged
  re-push ran nothing; after a body change only that script ran again. Write scripts to be
  re-runnable anyway (`create or replace`, `if not exists`): an edit reruns the whole body.
- **One script per engine.** A PostgreSQL environment silently skips an MSSQL script (it is still
  recorded). Name scripts by engine (`...MSSql`, `...Oracle`, `...PostgreSql`, the platform's
  convention); `validate` warns when the name and `DBEngineType` disagree, and on `GO` in a
  PostgreSQL body or `$$` in an MSSQL one.
- **Order is by dependency, not by name.** Without `DependsOn` the order is not guaranteed;
  declare it whenever one script uses what another creates.
- **`SysPackageSqlScript.Body` is `bytea`**, and a long SQL literal does not survive the trip
  through clio intact; `probe` compares MD5 hashes.
- A script that touches a package's own table needs `after-package` (the default): the table is
  created by the package install itself.

## Not covered

Scripts for several engines from one source (write each body); the uninstall path
(`uninstall-app`) was not run.
