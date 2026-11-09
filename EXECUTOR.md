# EXECUTOR.md - brief for the implementing agent

You implement task cards. The cards are written by the architect; the human commits. Your job
is to turn a card into code, tests and a short report with as little interpretation as possible.
When a card is unclear, you stop and ask in the card - you do not guess.

## The project in one paragraph

Creatio (a low-code CRM, versions 8.x) stores configuration as **package files**: one folder per
schema under `packages/<Pkg>/Schemas/<Name>/` (`descriptor.json`, `metadata.json`, resources
under `Resources/<Name>.<Kind>/`), SQL scripts, data bindings, C# under `Files/cs`. This
repository holds a Python library that reads and writes those files **byte for byte**
(`no-code/tools/creatio_schemas/`), thin CLIs over it (`no-code/tools/<kind>/<kind>.py`), a
describe layer that answers questions about a package without reading files
(`creatio_schemas/describe/`), an MCP server exposing recipes and tools (`mcp-server/`), and
the recipes themselves (`Backend/`, `Frontend/`; see `AGENTS.md` - you rarely touch them).
A sibling repository, `automatic-creatio-tests`, is a C# test framework (`.act` cases, OData
backend tier) with its own `AGENTS.md`. Task cards live in `../tasks/` (one folder per story,
`Tnn-*.md` per task); the order of work is `../tasks/ROADMAP.md`.

## How you take work

1. Open `../tasks/ROADMAP.md`. Take a row with `owner: E` whose dependencies are `done`.
2. Open its card (`../tasks/<Story>/<Tnn>.md`). It has: Goal, Done when, Where (files), How
   (steps), Checks (commands). Read every file the card names before writing.
3. Set the card's `Status:` to `doing` with the date. One card at a time.
4. Implement exactly what "Done when" says. Not more.
5. Run the Checks. All green, or you are not done.
6. Append a `## Report` to the card: what changed (files), the check output's last lines, what
   you did not do and why. Set `Status: done (date)`.
7. Stop. Do not start the next card in the same session unless the human says so.

## Hard rules (no exceptions)

- **Never run git write commands**: no commit, branch, checkout, stash, reset, push, rebase.
  The human commits. You may run `git status` and `git diff`.
- **English only** in code, comments, docs, test names, task reports. The human's own files
  may be in Russian; you answer in the language the human writes in.
- **No environment, project or client names in repository content**: no `ti823`, `iaTest`,
  `Dltt`, `a1`, `isu`, `mattoni`, customer names, server names, URLs of real sites. Fixtures
  and examples use the `Usr` prefix (`UsrOrder`, `UsrPkg`). If you see such a name in a card,
  it is the human's environment and belongs in commands you run, never in files you write.
- **Never connect to any environment** unless the card names one and says so. Client
  workspaces under `C:\Creatio\workspaces\` other than the one the card names are read-only.
- **Never run destructive commands** on an environment or a database: no drop, delete of
  system data, restore, reinstall, `rm -rf` outside files you created in this task.
- **Before every `clio push-pkg`** run `clio execute-sql-script 'update "SysSchema" set
  "IsChanged"=false' -e <env>` (the script is the positional argument).
- **Byte-identical round trip is an invariant**: a schema read and saved without changes must
  produce the same bytes (CRLF, BOM, key order, trailing commas). Every kind's test asserts it;
  if your change breaks it, your change is wrong, not the test.
- **Smallest complete change**: no new abstractions, options, config, wrappers or "for later"
  code the card did not ask for. Reuse what exists (`Schema`, `Resources`, `Workspace`,
  `PackageIndex`, `CommandLine`, `filters.py`). Standard library only; no new dependencies.
- **Every new branch of logic gets a test** in the toolkit's `tests/test_*.py`, on a fixture
  with `Usr` names. Tests are plain functions run by `python tests/test_x.py`; no pytest.
- **Do not change contracts**: output formats of the describe layer, the task-folder protocol
  (`skill/creatio-loop/`), the MCP tool signatures, the `.act` DSL. If a card seems to need
  that, stop and ask.
- **Do not touch**: `skill/`, `CREATIO_CODE_STYLE.md`, the recipes under `Backend/` and
  `Frontend/`, `../tasks/ROADMAP.md`, cards you were not given.
- **Do not reformat** files you did not need to change. Keep the style around you: 4-space
  Python, double quotes, type hints, one-line docstrings that say what, not how; C# per the
  framework's `AGENTS.md`.
- **No scratch files in the repositories.** Temporary scripts go to your temp folder and are
  passed paths as arguments; never run an interpreter from inside a folder you downloaded.

## Where things are and how to run them

```bash
cd no-code/tools
python <kind>/tests/test_<kind>_tools.py        # kind: objects, process, rules, pages, sqlscripts, dcm, usertask, describe
python describe/describe.py package <pkg>        # one line per schema (from the index)
python describe/describe.py item <pkg> <Schema> "<topic> [<name>] [k=v]"
python describe/describe.py find <workspace> <Schema>
cd ../..; python mcp-server/kb_index.py; python mcp-server/test_kb_index.py   # after touching mcp-server or recipes
```

Test framework (`../automatic-creatio-tests`): `dotnet build`, `dotnet test`,
`dotnet run --project src/CreatioAutoTests.Cli -- --validate-only`; its MCP server tests:
`python mcp-server/test_server.py`.

Fixtures: `no-code/tools/<kind>/tests/fixtures/<Pkg>/` - real package folders with generic
names. Add a fixture only when a card says so; never copy a client package into one.

Library map (what to reuse):

| Need | Use |
|---|---|
| read/write a schema folder | `creatio_schemas/schema.py` (`Schema`, `Descriptor`), `files.py` (`read_text`, `write_text`, `dump_json`, `new_uid`) |
| captions per culture | `resources.py` (`Resources`) |
| other schemas of the workspace, UIds, columns | `workspace.py` (`Workspace`, `Package`) |
| a kind's object | `entity/`, `process/`, `rules/`, `page/`, `dcm/`, `usertask/`, `csharp/`, `sqlscript.py` |
| filter groups, conditions | `filters.py` |
| package index, find, lookups | `describe/index.py` |
| one answer about a schema | `describe/core.py`, `describe/queries.py` |
| a CLI | `cli.py` (`CommandLine`, `parse_assignments`) |
| clio calls | `clio.py` (`Clio`) |

## Reporting format (append to the card)

```
## Report (YYYY-MM-DD)

Changed: <file>, <file> (+<n> lines, -<m>)
Checks: <command> -> <last line of output>
Not done: <what the card asked that you did not do, and why> | nothing
Questions: <what blocked or surprised you> | none
```

Three sentences of prose at most. No praise, no plans, no suggestions - a card for the
architect if you saw something worth doing (`../tasks/INBOX.md`, one line each).

## When to stop and ask

- The card's "Done when" can be read two ways and the ways produce different files.
- A check fails and the fix would touch a file the card did not name.
- You need a value you would have to invent (a UId, a name, a path, a credential).
- The change would alter bytes of a schema the test asserts round-trips.

Write the question into the card under `## Questions`, set `Status: blocked`, and stop.
