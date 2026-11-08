---
name: creatio-loop
description: The contract of the Creatio author/tester loop - a task folder whose files are the protocol (task.md, questions.md, plan.md, schemas.json, report-N.md, success-report.md, failed.md), project.json with the environment and the package, the schema lock between tasks, the evidence rules and the proof tiers (unit, probe, backend, process, ui). Read it with creatio-author or creatio-tester; use for "task folder", "report round", "acceptance criteria", "project.json", "schemas.json".
version: 2
---

# The author / tester loop: the contract

One task, one human, two agents that never share a chat: the **author** builds the package
artifacts, the **tester** proves them. They communicate only through files in the task folder;
the human carries the task from one to the other. This file is the contract both roles read
first; [creatio-author](../creatio-author/SKILL.md) and [creatio-tester](../creatio-tester/SKILL.md)
say what each role does with it.

## Never

- The author never edits `task.md`, `questions.md` after the human answered, or any report.
- The tester never changes package files, `plan.md` or the acceptance criteria. It reports.
- Nobody commits, branches or pushes to git: the human does.
- Nobody runs a destructive command on the environment (drop, delete of system data, restore,
  reinstall) or connects to an environment that is not the one in `project.json`.
- While `failed.md` exists in the task folder, the tester does not test that task.
- A `fail` without evidence is not a result. A free-text report is not a report.

## project.json

One file per project, outside git (it holds the password), path given to both agents by the
human. Template: [templates/project.example.json](templates/project.example.json). It names the
environment (clio name, url, login, password, platform version, whether it may be broken), the
package (name, schema prefix, workspace path, dependencies), the paths (the task folders, this
knowledge base, the test framework, the unit-test project), the read-only workspaces and the
project's own rules. Every agent reads it before touching anything; values from it are never
copied into a repository file.

## The task folder

`<paths.tasks>/<NNN>-<slug>/`. Files are written in the language of `task.md`.

| File | Written by | When | Meaning |
|---|---|---|---|
| `task.md` | human | start | the business task, free form, numbered by the folder |
| `questions.md` | author, then human | before the plan | the author's questions, the human's answers under each; `No questions.` when none |
| `plan.md` | author | after the answers | how it will be built, the artifacts, the acceptance criteria table |
| `schemas.json` | author | with the plan, kept current | every schema the task creates or changes: the lock other tasks check |
| `evidence/` | tester | each run | command output behind every `fail` row |
| `report-1.md` … `report-3.md` | tester | a run with at least one `fail` or `blocked` | one row per criterion |
| `success-report.md` | tester | a run where every criterion passes | the task is done |
| `failed.md` | tester | the 4th failing run | where the result still diverges from the criteria; the human removes it |

Templates for every file: [templates/](templates/).

## Lifecycle

1. The human writes `task.md`.
2. The author reads `project.json`, `task.md`, the knowledge base; writes `questions.md`; stops
   and says so in chat. The human answers in the same file.
3. The author writes `plan.md` and `schemas.json`, checks the lock (below), builds, pushes,
   probes, runs its unit tests, and says "done" in chat. No approval step: the plan is built
   as written. Anything that turns out unplanned is a question in chat, not a silent change.
4. The human opens the tester. The tester reads `task.md`, `questions.md`, `plan.md`,
   `schemas.json` and the previous reports; writes and runs the tests of every criterion; writes
   `success-report.md` or the next `report-N.md`. Three reports and still red: `failed.md`.
5. The human brings the report to the author. The author reads it, answers in chat (what was
   fixed, or what question the report raises), fixes, pushes, says "done". Back to 4.
6. `success-report.md` closes the task. `failed.md` parks it until the human deletes it
   (with the old reports, if a fresh count is wanted).

## The schema lock

A task is **active** while its folder has no `success-report.md`. Before creating or changing
a schema, the author reads `schemas.json` of every other active folder under `paths.tasks`; a
schema listed there belongs to that task - the author stops and asks the human instead of
touching it. `schemas.json` is updated the moment the scope grows.

## Acceptance criteria

`plan.md` carries them as a table: `AC-nn`, the action, the expected result, the tier. The
tester picks the tool; the tier says what kind of proof is enough.

| Tier | Proves | Typical tool |
|---|---|---|
| unit | a class in `Files/cs` behaves, with no environment | `dotnet test tests/<Pkg>/` (get_recipe `clio-tests-and-devops`, "Unit tests without an instance") |
| probe | the artifact landed on the environment as written | `objects.py probe`, `rules.py probe`, `sqlscripts.py probe`, `proc.py probe` |
| backend | listeners, triggers, defaults - the effect of a CRUD operation | a backend case of the test framework: `insert` / `update` / `delete` over OData, `check-record`, `check-count` |
| process | a process started with parameters returns the expected results and records | a process case: `start`, `check-result`, `check-record` |
| ui | the page behaves as a user sees it | `.act` cases: validate, then a live run |

## Evidence

A `pass` row cites the command and its decisive line. A `fail` or `blocked` row cites a file in
`evidence/` with the full output (`evidence/AC-03-report-2.txt`). `blocked` means the criterion
cannot be tested or contradicts `task.md`; it is the human's decision, the tester states why.
Results vocabulary, nothing else: `pass` | `fail` | `blocked` | `not tested`.
