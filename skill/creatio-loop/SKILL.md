---
name: creatio-loop
description: Run a Creatio task through the author/tester loop - acceptance criteria written by the human, an author agent that builds the package artifacts, a tester agent that proves them on the environment (probe, integration tests inside Creatio, processes as tests, UI cases), one report round per hand-over, three rounds at most. Use for "run the loop", "author", "tester", "acceptance criteria", "report round", "spec".
---

# The author / tester loop

One task, two agents, one human. The human writes the spec and decides when the loop stops;
the author builds; the tester proves. Neither agent sees the other's reasoning: they exchange
files.

Two MCP servers, one per side: `creatio-kb` (this knowledge base and its file toolkits - the
author's) and `creatio-tests` (the UI test utility: `dsl`, `cases`, `page_config`,
`process_config`, `validate`, `run`, `analyse`, `schemas`, `last_report` - read and run only,
the tester's). The tester role is given `creatio-tests` and the read tools, nothing that writes.

## Files

```
tasks/runs/<task-id>/spec.md      written by the human; the author never edits it
tasks/runs/<task-id>/report.md    append-only; one block per round, by whoever hands over
```

Templates: [templates/spec.md](templates/spec.md), [templates/report.md](templates/report.md).
`tasks/` is `C:\Creatio\workspaces\agent_repos\tasks`.

## The loop

1. The human writes `spec.md`: numbered criteria `AC-nn`, each with the tier that proves it.
2. **Author** (round n): reads the spec and the previous tester block, builds the artifacts
   with the file toolkits (`get_recipe("tools/objects")`, `tools/process`, `tools/rules`,
   `tools/sqlscripts`; C# per `get_code_style("architecture")` 3.7), clears the
   modified-locally flag (`update "SysSchema" set "IsChanged"=false`, see
   `get_recipe("clio-packages")`), pushes with `clio push-pkg`, runs `probe`, appends its
   block: files changed, what was checked, and `Returned to: tester`.
3. **Tester** (round n): reads the spec and the author's file list - not the author's text -
   runs the tier of every criterion, appends its block with one row per criterion and
   evidence, and ends with `Returned to: author` (something failed) or `Returned to: human`
   (all pass, or a criterion is wrong or impossible).
4. Stop after round 3 whatever the state: `Returned to: human`.

## Tiers and the command that proves them

| Tier | Proves | Command |
|---|---|---|
| probe | the artifact landed on the environment as written | `objects.py probe`, `rules.py probe`, `sqlscripts.py probe`, `proc.py probe` |
| integration | backend logic, data, rights | `tests.py run <pkg> --env ti823` (the runner inside Creatio, see tasks/S03) |
| process | a process started with parameters returns the expected results and leaves the expected records | a process case in `ProcessCases/` of the UI test utility: `start`, `check-result`, `check-record`; `proc.py test-config` writes the process file it validates against (`get_recipe("tools/process")`, "Testing a process") |
| ui | the page behaves as a user sees it | `.act` cases: `creatio-tests --validate-only`, then a live run (`get_recipe("tools/uitests")`) |

## Rules that make the loop converge

- A `fail` row without evidence (command output, not opinion) is rejected: the author treats it
  as `not tested`.
- The author never changes the spec. A criterion it cannot meet is `blocked` with the reason,
  and the round goes to the human.
- The tester never fixes anything, not even a typo. It reports.
- Rows carry the criterion id; a free-text report is not a report.
- Round 3 red means the human looks. Do not start round 4.
