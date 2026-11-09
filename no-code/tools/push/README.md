---
description: Push a Creatio package to an environment in one command - clear IsChanged, push-pkg, check compilation log, publish processes with scripts, and probe the changes.
---

# Push command

Push a package to an environment with all the mandatory steps in one command. Pure Python standard library.

| File | What it does |
| --- | --- |
| `push.py` | CLI: push a package with all steps |
| [`../creatio_schemas/push.py`](../creatio_schemas/README.md) | the library (`push`) |
| `tests/` | `python tests/test_push_tools.py` |

## How it works

The typical package install requires four manual steps:
1. Clear `IsChanged` flag in `SysSchema` (otherwise the platform thinks nothing changed)
2. Run `clio push-pkg` to install the package
3. Check `clio last-compilation-log` to verify no errors
4. Run `clio compile-configuration` when the package has processes with scripts or user tasks (takes minutes)

`push.py` does them all in order, stopping at the first failure.

```bash
python push.py UsrPkg -e dev                      # push and check
python push.py UsrPkg -e dev --probe              # also run probes
python push.py UsrPkg -e dev --dry-run            # print commands only
```

Output: one line per step, then a summary line with timing.

## Traps

- The script-or-user-task detection reads the package's process metadata files looking for
  `ProcessSchemaScriptTask` or `ProcessSchemaUserTask` class names - it does not parse the
  metadata structure, just searches text.
- Probes require the probe commands to be available: `objects.py probe`, `rules.py probe`,
  `sqlscripts.py probe`, `proc.py probe` (in the same environment where push.py runs).
