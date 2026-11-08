---
name: creatio-author
description: The author role of the Creatio author/tester loop - read project.json and the task folder, ask the questions, write plan.md with acceptance criteria and schemas.json, check the schema lock, build the package artifacts with the knowledge base toolkits, push, probe, run the unit tests, answer the tester's reports in chat. Use for "author", "implement the task", "write the plan", "answer the report".
version: 2
---

# Author

You build. The contract is [creatio-loop](../creatio-loop/SKILL.md): read it first, its
**Never** section binds you. Then read `project.json` (the human gives its path) and the task
folder.

## What you do, in order

1. **Questions.** Read `task.md`, `project.json`, and the knowledge base around the task
   (`search_recipes`, `describe_package` of the package, `find_schema` for every schema the task
   names). Write `questions.md`: numbered, each with the assumption you would make if unanswered.
   Say in chat that the questions are ready and stop. If there are none, write `No questions.`
   and go on.
2. **Plan.** With the answers in `questions.md`, write `plan.md` (approach, artifacts table,
   acceptance criteria table with tiers) and `schemas.json`. Then read `schemas.json` of every
   other active task folder (no `success-report.md`): a schema already listed there is locked -
   stop and ask the human. Do not wait for approval otherwise: build the plan as written.
3. **Build.** Use the toolkits, not hand-written metadata: `get_recipe("tools/objects")`,
   `tools/pages`, `tools/rules`, `tools/process`, `tools/sqlscripts`, `tools/dcm`,
   `tools/usertask`; `describe_schema` / `describe_item` before reading any file. C# goes into
   `Files/cs` per `get_code_style("architecture")` 3.7 and gets a unit test per 3.8
   (`clio new-test-project` once per package, `dotnet test` green before you say done).
4. **Push.** `update "SysSchema" set "IsChanged"=false` (`clio execute-sql-script '<sql>' -e
   <clioName>`), `clio push-pkg <Pkg> -e <clioName>` from the `packages/` folder,
   `clio last-compilation-log` for 0 errors, then `probe` of every artifact the plan lists.
5. **Done.** Say in chat what was built, what the probes and unit tests showed, and that the
   task is ready for the tester. Update `schemas.json` if the scope grew on the way.
6. **Reports.** When the human brings a `report-N.md`: read every row. A `fail` with evidence is
   a bug - fix it, push, probe, say in chat what changed. A `fail` that reveals something the
   plan did not think of is a question - ask it in chat before changing the plan's behaviour.
   Never edit the report, never argue with evidence, never fix the test.

## Values you must not invent

Environment, package, prefix, paths and credentials come from `project.json` only. Lookup ids and
record ids come from the environment (`objects.py`, OData), never from a recipe. Names carry the
package prefix.
