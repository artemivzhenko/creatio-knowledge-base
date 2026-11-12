# Creatio KB MCP server

Exposes this knowledge base to an AI assistant over MCP, so the model can look up a
recipe for a concrete task instead of loading all 177 files into context - and, through the
same server, ask the describe layer about a package, install it and query the environment.

## What it gives the model

Recipes (`kb_index.py`):

| Tool | Purpose |
| --- | --- |
| `search_recipes(query, area?, limit?)` | Ranked search by task or symptom. `area` = `ClassicUI` / `FreedomUI` / `RemoteModule` / `Mobile` / `Backend` / `SQL` / `Clio` / `Tools`. |
| `get_recipe(recipe_id)` | Full text of one recipe: explanation header plus runnable code. For clio, a command name (`execute-sql-script`) or a block skill (`clio-sql-and-data`) resolves directly; for a toolkit, `tools/process`. |
| `find_api(symbol, limit?)` | Reverse lookup — which recipes use `crt.OpenLookupPageRequest`, `UseAdminRights`, `EntitySchemaQuery`… A bare name also matches the dotted one. |
| `list_recipes(area?, topic?)` | Browse ids and titles. |
| `kb_overview()` | Map of areas, topics and counts — the entry point when the model does not know what exists. |
| `get_code_style(section?)` | The C# style and architecture guide (`../CREATIO_CODE_STYLE.md`), whole or one `##` section by number or heading words (`"logging"`, `"9"`). |

The describe layer (`../no-code/tools/creatio_schemas/describe/`, its README is the contract -
every list answer has a `limit`, default 40, and a `... N more` tail; `0` means all):

| Tool | Purpose |
| --- | --- |
| `describe_package(package, kind?, limit?)` | One line per schema, SQL script and data binding, from the package index. |
| `describe_schema(package, schema, limit?)` | The summary of one schema: what the toolkit's `inspect` prints. |
| `describe_item(package, schema, query, limit?)` | One part, chosen by `"<topic> [<name>] [k=v]"`; `"topics"` lists what the schema answers. |
| `find_schema(path, schema, limit?)` | The package, the files (absolute paths), what it refers to, what refers to it. |
| `schema_deps(path, schema, direction?, kind?, via?, limit?)` | The typed graph: objects a page or process builds on (and through which columns); every process, rule, page, DCM, binding or listener that builds on an object. |
| `schema_impact(path, schemas, tasks?, current?, md?, limit?, kind?)` | The dependents of the schemas a task changes; with the loop's tasks folder, which other active task changes or affects them. Ends with `exit code 1` on a conflict. `md` gives the `## Impact` table for `plan.md`; `kind` keeps one kind of dependents (a lookup with a hundred). |
| `schema_diff(package, schemas?, against?)` | The working copy against git HEAD, a revision or a folder with a pulled copy: `+` / `-` / `~` lines per item, never a JSON hunk. |
| `resolve_uid(path, text)` | What a UId names (a schema, `column X.Y`, a process element or parameter), the UId of a dotted name, or a text with every UId replaced by its name - the reverse of what the designer stores. |
| `schema_layers(path_or_env, schema, rule?)` | The SysSchema copies of a schema on an environment, applied first to last; `Custom layer present` means a copy on the site overrides what you push. |
| `schema_snapshot(schema, env?, workspace?, columns?, out?)` | An object as text lines: the effective columns over the workspace's layers and / or the site's table, row count, column checksums and copies; `out` writes the evidence file. |
| `merge_plan(path, schemas?, env?, limit?)` | Each schema replaced by more than one package (or the named ones): the target (the lowest package), `layer <pkg>: +n columns / elements / methods` in apply order, `siblings` when the order is guessed, `conflict` lines, `depends: <target> gains ...`; ends with the counts and `exit code 1` on a conflict. Writes nothing (safe on a client workspace). |
| `merge_layers(path, schema, target?, env?)` | The layers of one object as one layer of the target package, PRINTED only: the plan, `write` / `delete` per file, or `stopped: ... - nothing written`; `env` gives the site's order and the references check. `describe.py merge --apply` writes. |
| `snapshot_compare(before, after)` | Two snapshot files as `+ - ~` lines, or `same`; a difference ends with `exit code 1`. |
| `list_lookups(path, limit?)` | Every lookup object: parent chain, bindings, users. |
| `index_workspace(path, rebuild?)` | Build or refresh `.creatio-index/` under a workspace; reports added / changed / removed. The other tools refresh it themselves on every call. |

The environment (`creatio_schemas/environment.py` over clio; `env` is a clio environment name):

| Tool | Purpose |
| --- | --- |
| `env_sql(env, sql, limit?)` | Rows as JSON, one object per row; a database error (`[ERR]`, or a SQLSTATE line such as `42703: column ... does not exist` on the clio builds that exit 0) comes back as `error: ...`, never as `(no rows)`. |
| `env_odata(env, entity, select?, filter?, top?)` | Records over OData (`top` defaults to 20). |
| `env_call(env, method, path, body?)` | A service or OData call with login and CSRF; the fault in one line. |
| `find_record(env, id, objects?, everywhere?, time_zone?)` | Which table holds an Id, with the caption, dates and authors. |
| `record_context(env, entity, id, columns?, depth?)` | A record with its lookups named and the rows that point at it. |
| `role_members(env, role, units?)`, `user_roles(env, user)`, `role_diff(env, role, users)` | Role membership from `SysAdminUnitInRole` (nested roles included); the diff ends with `exit code 1` when a user is missing. |
| `run_process(env, process, params?, results?)` | Starts a process (`params` a JSON object), prints its result parameters and its `SysProcessLog` row; `exit code 1` unless the run completed. |
| `process_runs(env, process?, record?, since?, until?, limit?, window?, time_zone?, noise?)` | The runs of a process, or every run within `window` seconds of a change of a record (`<Entity>:<Id>`) or its details; noise processes hidden with a count. |
| `process_error(env, log_id, time_zone?)` | One run's error without stack frames, and the element it stopped on. |
| `run_tests(env?, project?, category?, test?, package?)` | The in-Creatio tests: failures first, `N passed, M failed`, a warning when the test dll is older than the package; `exit code` 0/1/2. |
| `review_download(package, keep?)` | A pulled package against git HEAD: line endings / BOM only, content changes, dependencies, orphan resources, untracked files; `keep` prints the restore lines. |
| `precommit_check(workspace)` | Staged files that must not be committed (size, archives, binaries, stray roots), then `exit code 1`. |
| `sys_setting(code, envs, workspace?)` | A setting's value on each environment and the data bindings of the workspace that set it. |
| `push_package(package, env, ...)` | `IsChanged` cleared, `push-pkg`, the compilation log, `compile-configuration` when needed, the probes of the changed items; `dry_run` shows the plan. |

The describe and environment tools import `../no-code/tools` at startup (standard library only);
the environment tools also need `clio` on the PATH with the environment registered.

Search is lexical BM25 with a title bonus and a light stemmer (`pagination` finds
`paginate`, `files` finds `file`), built in memory at startup. No API keys, no network,
no embedding service. The words `creatio`, `freedom`, `classic`, `ui` are ignored in
queries — the UI generation is the `area` argument, not a search term. The index rebuilds automatically when a file in
the knowledge base changes, so editing a recipe takes effect on the next call.

## Install

```bash
cd mcp-server
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate on macOS/Linux
pip install -e .
```

`pip install -e .` pulls the only dependency, `mcp>=2.0`.

> The SDK renamed `FastMCP` to `MCPServer` in mcp 2.0. `server.py` imports either,
> so an existing `mcp<2` environment also works.

## Check it without a client

`kb_index.py` is pure standard library, so the index and the ranking can be
exercised on their own:

```bash
python kb_index.py                          # index report: areas, topics, warnings
python kb_index.py "filter a lookup field"  # try a query
```

A healthy report ends with no warnings — a warning means a recipe lost its header
block and only got a title derived from its file name.

`test_kb_index.py` pins the tokenizer, the ranking of a few known queries and the id
lookup. Run it after touching `kb_index.py`:

```bash
python test_kb_index.py          # or: pytest
```

## Wire it into a client

Replace `<KB>` with the absolute path to this knowledge base folder (the one
containing `Frontend/` and `Backend/`), and `<PY>` with the interpreter from the
virtual environment (`<KB>/mcp-server/.venv/Scripts/python.exe` on Windows,
`<KB>/mcp-server/.venv/bin/python` elsewhere).

### Claude Code

```bash
claude mcp add creatio-kb -- <PY> <KB>/mcp-server/server.py
```

Or in `.mcp.json` at the root of the project you develop Creatio in:

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Claude Desktop — `claude_desktop_config.json`

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"]
    }
  }
}
```

### Knowledge base in another location

The server assumes the knowledge base is the parent folder of `mcp-server/`.
Point it elsewhere with an environment variable:

```json
{
  "mcpServers": {
    "creatio-kb": {
      "command": "<PY>",
      "args": ["<KB>/mcp-server/server.py"],
      "env": { "CREATIO_KB_ROOT": "D:/knowledge/creatio-knowledge-base" }
    }
  }
}
```

## Companion skill

`../skill/creatio-kb/SKILL.md` tells a Claude Code agent *when* to reach for these
tools. The MCP server supplies the data; the skill supplies the habit of consulting
it before writing Creatio code. Install it by copying the folder into
`.claude/skills/` of the project you work in.

## How indexing works

- Recipes are discovered under `Frontend/ClassicUI`, `Frontend/FreedomUI`,
  `Frontend/RemoteModule`, `Frontend/Mobile`, `Backend/C#`, `Backend/SQL` and, as area
  `Clio`, the Markdown under `no-code/`. A folder with `package.json` inside (a copyable
  project template) is skipped.
- The title and description come from the header block: `// --- Title ---` in `.js`
  and `.ts` files, `/// <summary>` in `.cs`, the leading `--` comment in `.sql`, the first
  `# ` heading plus frontmatter `description:` in `.md`. A `SKILL.md` is indexed under its
  folder name (`no-code/clio-pages`).
- Without an `area`, Clio pages are scaled by `W_CLIO_UNFILTERED` unless the query names
  clio or a kebab-case command, so CLI pages do not answer platform questions.
- A recipe id is its path without the extension, e.g.
  `Frontend/ClassicUI/Fields/HowToFilterLookupField`.
- Tokenisation splits dotted and camelCase identifiers, so `crt.OpenLookupPageRequest`
  is findable as `crt.OpenLookupPageRequest`, `OpenLookupPageRequest`, and
  `lookup page`.
- A bare file name in `get_recipe` resolves when unique; when Classic UI and Freedom UI
  both have it, the tool lists the two full ids instead of failing.

## Adding recipes

Drop a new file into the right area folder and keep the header block format — it is
what supplies the title and summary. Nothing else needs updating; the index picks it
up on the next tool call.
