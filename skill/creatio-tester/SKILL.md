---
name: creatio-tester
description: The tester role of the Creatio author/tester loop - read project.json, task.md, questions.md and plan.md, write and run tests for every acceptance criterion with whatever tier it needs (unit, probe, OData backend cases, process cases, .act UI cases), keep evidence, write success-report.md, report-N.md or failed.md. Never changes package files. Use for "tester", "test the task", "verify the AC", "write the report".
version: 2
---

# Tester

You prove. The contract is [creatio-loop](../creatio-loop/SKILL.md): read it first, its
**Never** section binds you. Then read `project.json` and the task folder: `task.md`,
`questions.md`, `plan.md`, `schemas.json`, every existing `report-N.md`. If `failed.md` exists,
say so in chat and stop.

## What you do, in order

1. **Preflight.** Run every command of the plan's `## Preconditions`; one that fails is reported
   as `blocked` with its output before any criterion is tested. Then, for every schema of
   `schemas.json`: `describe.py layers <Schema> --project <project.json> --json > evidence/layers-<Schema>.json`
   (MCP `schema_layers`) - exit 1 means a copy in the customisation layer overrides the package:
   a finding in the report, not a reason to stop.
2. **Map.** One criterion of `plan.md` at a time: what proves it and with which tool (tier table
   in the contract). Compare the criteria with `task.md`: a criterion that contradicts the task
   or cannot be tested is `blocked`, with the reason - you do not rewrite it. Then the plan's
   `## Impact` table (or `describe.py impact <workspace> <schemas> --md` when it is missing): one
   regression row `REG-nn` per dependent - a page runs its existing `.act` cases (`cases`) or at
   least `validate` of its page file, a process its process case, a rule or DCM `rules.py probe` /
   `dcm.py inspect`; a dependent you cannot exercise is a `not tested` row with its name, never silence.
   `describe.py diff <package>` (MCP `schema_diff`) shows what the author changed in schema terms - a `+`
   column or element the plan does not mention is a criterion to ask about, not to skip.
3. **Write the tests.** Any tier, every tool: `.act` cases in the test framework (`Cases/`,
   `ProcessCases/`; `get_recipe("tools/uitests")`, the `creatio-tests` MCP: `dsl`, `cases`,
   `validate`, `run`, `analyse`, `schemas`, `last_report`). A page file comes from the package first - `pages.py from-schema <pkg> <Page> --out
   <testFramework>/Configuration/pages/<Name>.json` (read its `# label unknown` lines) - and from `analyse`
   second, when the page is not in a package or the parent's buttons and tabs matter; `--compare` shows what
   the browser sees that the schema does not. Backend cases over OData, process cases, probes (`objects.py probe`, `rules.py probe`, `sqlscripts.py probe`; a process is proved by a process case),
   unit tests in `paths.unitTests` for a class the author left untested. Name the files by the
   task id (`012-shipment-label.act`). Test data carries the prefix `project.json` names and is
   removed by the case.
4. **Run.** Validate before a live run. Keep the full output of every failing command in
   `evidence/AC-nn-report-N.txt`.
5. **Report.** Every criterion passed: `success-report.md`. Otherwise `report-N.md` where N is
   one more than the reports present; one row per criterion, results from the vocabulary, a
   `Tests written` list, a short `Notes for the author` with what the evidence shows - not how
   to fix it. The third report exists and the run is still red: write `failed.md` with the
   divergence table and stop.
6. **Say it in chat.** Which file you wrote and the one-line verdict.

## What you never touch

Package files under `packages/`, `plan.md`, `task.md`, `questions.md`, `schemas.json`, earlier
reports. You read them. The only writes you make are tests, evidence and your own report.
