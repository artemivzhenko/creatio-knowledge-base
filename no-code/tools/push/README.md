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

The command checks environment drift since the package's last git commit, checks changed files
against other active task locks, and updates the dates of changed SQL scripts. It then clears
`IsChanged`, runs `push-pkg`, reads the compilation log, compiles assembly packages with
`compile-package --wait`, optionally checks a baseline and publishes processes with script or user
tasks. `IsChanged` is cleared because designer-edited schemas otherwise count as modified locally
and `push-pkg` skips them.

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

Output: one line per step, then a summary line with timing or the failed step. A dry run performs
no subprocess calls or writes.

## Traps

- The script-or-user-task detection reads the package's process metadata files looking for
  `ProcessSchemaScriptTask` or `ProcessSchemaUserTask` class names - it does not parse the
  metadata structure, just searches text.
- `--probe` checks objects and SQL scripts. Rules need attribute values and processes are
  proved by process cases, so neither is probed here.
