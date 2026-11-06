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
package files (`proc.py`, `refactor.py`, `pschema.py`), the route that works on Creatio 8.x
where clio's own process tools do not. It ships the decoded key map of the process
metadata and the user-task definitions of 8.2.3.

## Business-rule tools

[tools/rules/](tools/rules/README.md) creates and edits object and Freedom UI page business
rules as package files (`rules.py`, `brules.py`) from a short JSON spec, including replacing
addons of base objects and the generated rules of a lookup filter, and proves object rules
through the platform's rule engine (`rules.py probe`).

## Regenerating the reference

```bash
cd <clio repo> && git checkout <tag matching `clio ver`>
python no-code/tools/sync_clio_docs.py <clio repo>
```

The generator rewrites `reference/` and the command tables between
`<!-- commands:start -->` / `<!-- commands:end -->` in each skill. It fails on a command it
has no block for: add it to `BLOCKS` in the script. Hand-written text in the skills is never
touched. clio's docs are MIT-licensed; each reference page names its source file.
