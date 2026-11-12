---
description: Push a Creatio package to an environment in one command - clear IsChanged, push-pkg, check compilation log, publish processes with scripts, and probe the changes.
---

# Push command

Push a package to an environment with drift, task ownership and compilation checks. Pure Python standard library.

| File | What it does |
| --- | --- |
| `push.py` | CLI (the commands are listed under Commands) |
| [`../creatio_schemas/push.py`](../creatio_schemas/README.md) | the library (`push`) |
| `tests/` | `python tests/test_push_tools.py` |

## Commands

<!-- commands:start -->
```
python push.py <package> -e <environment>          push and check
python push.py <package> -e <environment> --probe  also run probes
python push.py <package> -e <environment> --dry-run print commands only
```
<!-- commands:end -->

## How it works

The command checks environment drift since the package's last git commit (the schemas of the package
- joined through `SysPackage` by the descriptor's `UId` - modified on the environment after that commit),
checks that no dependency was dropped (a `DependsOn` entry of `descriptor.json` or a `Reference` /
`ProjectReference` of `Files/*.csproj` that git HEAD has and the working copy lost; `--force` lets it
through), checks changed files against other active task locks, and updates the dates of changed SQL
scripts. It then clears `IsChanged` in `SysSchema`, `SysPackageSchemaData` and `SysPackageSqlScript`, runs `push-pkg`, reads the compilation log, compiles assembly packages with
`compile-package --wait`, optionally checks a baseline and publishes processes with script or user
tasks. `IsChanged` is cleared because designer-edited schemas otherwise count as modified locally
and `push-pkg` skips them.

After drift, the `bindings` step reads every `Data/<Name>` of the package and, for the rows whose key (the binding's
`IsKey` columns, else `Id`) already exists on the site, compares each column the binding writes with the site's value;
one line per difference, `<object> <key>: <Column> site <value> -> package <value>` (`(force update)` when the column
is marked so), and the push stops unless `--force`. The statement per binding, 50 keys per `or`:
`select "<key>", "<column>"... from "<object>" where ("<key>" = '<value>') or ...` - a lookup column is its `<Name>Id`,
localizable, binary and audit columns are not compared, empty and `null` are equal, numbers compare by value. A
binding whose object the site does not have yet (the select fails) is listed as `not compared` and does not stop it.
Whether the platform rewrites a non-force column of an existing row was not measured on a site: the step lists every
difference, so the author decides with the values in front of them.

`push.py` does them all in order, stopping at the first failure.
Also available as the MCP tool `push_package`, with the same v2 safety options.

```bash
python push.py UsrPkg -e dev                      # push and check
python push.py UsrPkg -e dev --probe              # also run probes
python push.py UsrPkg -e dev --dry-run            # print commands only
python push.py UsrPkg -e dev --project project.json --task tasks/001-order
python push.py UsrPkg -e dev --tasks tasks --task tasks/001-order --baseline tasks/001-order/evidence/errors.txt
```

`--project` reads `paths.tasks` from the supplied project; `--tasks` overrides it. When a tasks
folder is supplied, `--task` must identify the current task folder directly inside it. Without a
tasks folder the ownership check is skipped. `--force` allows drift; `--skip-drift`,
`--skip-foreign-files`, `--skip-sql-dates` and `--skip-compile-package` explicitly skip their
respective checks or steps. `--baseline` creates a file containing the current compilation error
lines on first use; later runs fail on new error lines. Without a baseline, non-assembly packages
still fail on configuration compilation errors.

`<package>` is a path or a name: `push.py UsrPkg` finds `packages/UsrPkg` under the current folder or
next to `--project`, and says `no package folder named UsrPkg; give its path (packages/UsrPkg)` otherwise.
A database error (a SQLSTATE line from clio, which exits 0) fails the step: a drift check that cannot run
does not pass.

Output: one line per step, then a summary line with timing or the failed step. A dry run performs
no subprocess calls or writes, reads `dry run` on every step that would have run, and ends with
`dry run of <pkg> -> <env>: N steps, nothing sent`.

## Traps

- The script-or-user-task detection reads the package's process metadata files looking for
  `ProcessSchemaScriptTask` or `ProcessSchemaUserTask` class names - it does not parse the
  metadata structure, just searches text.
- `--probe` checks objects and SQL scripts. Rules need attribute values and processes are
  proved by process cases, so neither is probed here.
