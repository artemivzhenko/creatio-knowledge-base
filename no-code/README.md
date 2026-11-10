# clio for AI agents

How an agent drives the Creatio platform through the [clio](https://github.com/Advance-Technologies-Foundation/clio)
CLI: packages, SQL and data, schemas, Freedom UI pages, applications, rights, builds, and
clio's own MCP server. This is the no-code half of the knowledge base; the code recipes live
in `Frontend/` and `Backend/`.

Two layers:

| Layer | What it is | Where |
| --- | --- | --- |
| **Block skills** | One `SKILL.md` per functional block: when to use it, the working sequence of commands, and the traps verified on a real environment | `clio-*/SKILL.md` |
| **Command reference** | One page per clio command (261): synopsis, options, examples, exit codes, MCP notes. Generated from clio's own docs | `reference/<command>.md` |

Both are indexed by the `creatio-kb` MCP server as area `Clio`:
`search_recipes("execute sql script", area="Clio")`, `get_recipe("execute-sql-script")`,
`get_recipe("clio-sql-and-data")`.

## Blocks

| Skill | Covers |
| --- | --- |
| [clio-basics](clio-basics/SKILL.md) | install, environments, authentication, help, the settings file |
| [clio-sql-and-data](clio-sql-and-data/SKILL.md) | SQL, DataService, OData, ESQ, system settings, data bindings, file upload |
| [clio-packages](clio-packages/SKILL.md) | create, push, pull, lock, version, dependencies, hotfix |
| [clio-workspace-and-build](clio-workspace-and-build/SKILL.md) | workspace, compile, compilation log, restart, FSM, repository links |
| [clio-schemas](clio-schemas/SKILL.md) | objects, columns, lookups, C#/JS/SQL schemas, export and import |
| [clio-pages](clio-pages/SKILL.md) | Freedom UI pages, templates, components, business rules |
| [clio-apps](clio-apps/SKILL.md) | composable applications and their sections |
| [clio-processes](clio-processes/SKILL.md) | business processes and user tasks |
| [clio-security](clio-security/SKILL.md) | users, roles, licenses, object and record rights, OAuth, identity service |
| [clio-theming](clio-theming/SKILL.md) | themes, logo, background |
| [clio-tests-and-devops](clio-tests-and-devops/SKILL.md) | test projects, scenario runner, NuGet, Docker, clio add-on packages |
| [clio-mcp](clio-mcp/SKILL.md) | clio's own MCP server, tool discovery, guidance, toolkits |
| [clio-infrastructure](clio-infrastructure/SKILL.md) | local installs, databases, Kubernetes, IIS, web farms |

## Verified means verified

Every trap marked **verified** in a skill was reproduced on Creatio 8.2.3 (PostgreSQL,
.NET Framework host) with clio 8.1.0.145 and cliogate 2.0.0.43. Everything else is read from
the clio source and docs at that tag. [VERIFIED.md](VERIFIED.md) is the ledger: one row per
MCP tool and CLI command that was actually run, with what happened. clio is written against Creatio 10.x first; several
no-code tools silently store things an 8.x designer cannot show, and the skills say which.

## Process tools

[tools/process/](tools/process/README.md) builds and refactors business processes as
package files (`proc.py`, `refactor.py`), the route that works on Creatio 8.x
where clio's own process tools do not. It ships the decoded key map of the process
metadata and the user-task definitions of 8.2.3.

## Business-rule tools

[tools/rules/](tools/rules/README.md) creates and edits object and Freedom UI page business
rules as package files (`rules.py`) from a short JSON spec, including replacing
addons of base objects and the generated rules of a lookup filter, and proves object rules
through the platform's rule engine (`rules.py probe`).

## Object tools

[tools/objects/](tools/objects/README.md) creates objects and lookups and adds, changes and
removes their columns and flags as package files (`objects.py`); `push-pkg` makes the platform
update the table, and `objects.py probe` compares the metadata with the database.

## Page tools

[tools/pages/](tools/pages/README.md) puts the fields of a page's object (every column type)
and grids of other objects on a Freedom UI form page by editing the page body's JSON sections
(`pages.py`); `push-pkg` installs the page, and the UI test utility's `analyse` shows what
rendered.

## DCM case tools

[tools/dcm/](tools/dcm/README.md) reads a case (object, stage column, filter, stages with their
lookup records, steps that start sub-processes, result conditions, allowed moves), creates a case
on an object's lookup column, adds or removes stages and connects them (`dcm.py`); steps are
described, not written.

## User-task tools

[tools/usertask/](tools/usertask/README.md) reads a user task (parameters, the C# methods, one
method's body), creates one with a compilable skeleton, adds, renames or removes parameters and
replaces the C# half (`usertask.py`); icons in the resources are kept.

## Data binding tools

[tools/data/](tools/data/README.md) reads a data binding (the bound table, key columns, rows with
lookup captions and per-culture texts), validates it, binds an object of the workspace, sets one
value, adds or removes rows (`data.py`); unchanged files are written back byte for byte.

## Classic UI tools

[tools/classicui/](tools/classicui/README.md) reads a Classic UI (7.x) edit page, section or detail
(sections, diff operations and elements, methods and one method's source) and warns about parent
containers and handlers the file alone cannot prove (`classicui.py`); read-only.

## UI test cases

[tools/uitests/](tools/uitests/README.md) is the UI test utility (`automatic-creatio-tests`) for an
agent: build and run, the page and process files, the DSL in one table, the backend tier, the
recipe that turns an acceptance criterion into an `.act` case, and the traps; nothing to run here.

## Resource tools

[tools/resources/](tools/resources/README.md) works on the captions of a whole package: the
cultures it ships, the keys missing per culture and schema, filling a culture from another,
setting, renaming and removing a key everywhere (`resources.py`); only changed files are written.

## Scaffold

[tools/scaffold/](tools/scaffold/README.md) builds the start of an author task in one command: an object
with its columns, lookup objects with a data binding of their rows, a form page with every field and a
list page, each through its toolkit and validated, as one dry-run diff first (`scaffold.py entity`).

## SQL script tools

[tools/sqlscripts/](tools/sqlscripts/README.md) creates and changes the package's SQL scripts
(views, functions, triggers, data fixes) per database engine, with install type and run order
(`sqlscripts.py`); `push-pkg` runs them, `sqlscripts.py probe` shows what the environment recorded.

## The schema library

The toolkits are command lines over [tools/creatio_schemas/](tools/creatio_schemas/README.md):
one `Schema` base class (files, descriptor, resources, diff, save) with `ProcessSchema` and
`RuleSchema` and `EntitySchema` on top, registries for process element kinds and rule actions, and the
workspace lookups they share. New schema types and new element or action kinds go there.

## Regenerating the reference

```bash
cd <clio repo> && git checkout <tag matching `clio ver`>
python no-code/tools/sync_clio_docs.py <clio repo>
```

The generator rewrites `reference/` and the command tables between
`<!-- commands:start -->` / `<!-- commands:end -->` in each skill. It fails on a command it
has no block for: add it to `BLOCKS` in the script. Hand-written text in the skills is never
touched. clio's docs are MIT-licensed; each reference page names its source file.
