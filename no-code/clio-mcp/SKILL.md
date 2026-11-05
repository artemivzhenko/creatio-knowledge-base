---
name: clio-mcp
description: clio's own MCP server - how to start it, discover its ~236 tools through get-tool-contract and clio-run, read its guidance library, what it costs in context, and the argument conventions that make calls fail. Use when an agent should drive Creatio through MCP tools instead of shell commands.
---

# clio MCP server

Verified on clio 8.1.0.145 against Creatio 8.2.3. Command pages: [reference/](../reference/).

```bash
clio mcp-server            # stdio transport (what Claude Code / Cursor spawn)
clio mcp-http              # Streamable HTTP, same tools
clio install-toolkit       # Creatio AI App Development Toolkit skills for claude/codex/cursor/copilot
```

Register in Claude Code: `claude mcp add --scope user clio -- clio mcp-server`.

## Shape of the server

| Layer | Size | How to reach it |
| --- | --- | --- |
| Resident tools in `tools/list` | 18-19 | call directly: `get-page`, `list-pages`, `list-packages`, `get-entity-schema-properties`, `find-app`, `get-guidance`, `get-tool-contract`, `clio-run` ... |
| Hidden tools | ~218 (110 destructive) | `get-tool-contract` (index, or `tool-names` for contracts), then `clio-run {"command": "<name>", "args": {...}}` |
| Guidance articles | ~170 | `get-guidance name=list`, then by name (`core-rules`, `routing`, `page-modification`, `business-rules`, `esq`, `process-digest` ...) |
| Prompts | 74 | workflow recipes (`get-page` -> `get-component-info` -> `update-page`) |

The server's own instructions require reading `core-rules` and `routing` first. Together
with `tools/list` that is about 70 000 characters before the first action; a page edit adds
another ~35 000 (guide plus contract). Budget for it, or use the CLI for simple steps.

## Argument conventions (verified)

- Names are kebab-case (`environment-name`, `package-name`, `schema-name`).
- Unknown arguments are refused, not ignored: the error lists the valid names
  (`list-packages` takes `filter`, not `search`; `odata-read` takes structured `filters`).
- Some tools take the arguments only inside `args` of `clio-run`; the message
  `argument 'args' must be an object` means a resident tool was called through `clio-run`
  with the wrong nesting - call it directly.
- Tools that read the platform return structured JSON (`success`, `count`, `error`,
  `correlation-id`); older lifecycle tools return `exit-code` plus
  `execution-log-messages` - check both shapes.
- Large results go to files (`get-page`, `*-to-file` variants): read the path, not the
  tool output.

## Traps (verified)

- A broken `ActiveEnvironmentKey` in clio's settings disables every environment tool with
  "settings bootstrap is broken" ([clio-basics](../clio-basics/SKILL.md)).
- `resources/list` fails on this version (an error, not an empty list); guidance is reached
  through `get-guidance`, not through MCP resources.
- The server is written for Creatio 10.x: `success: true` does not prove the saved object
  works on 8.x (see the operator trap in [clio-pages](../clio-pages/SKILL.md) and the type
  traps in [clio-schemas](../clio-schemas/SKILL.md)). Verify through the platform (OData,
  SQL, the designer), not by reading back through clio.
- Telemetry consent and the knowledge-feedback policy are asked for on every session;
  answering is the user's decision, not the agent's.
- Of the 96 MCP-only tools, 55 were run on 8.2.3: 45 work, the rest fail for a named
  reason (CrtProcessBuilder, DataForge, 10.x services, an old gate). The ledger is
  [VERIFIED.md](../VERIFIED.md); an agent on 8.x should consult it before planning a
  workflow around a tool.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [add-knowledge-source](../reference/add-knowledge-source.md) | Add a trusted GitHub Release, Git, or NuGet knowledge source |
| [delete-knowledge](../reference/delete-knowledge.md) | Delete installed knowledge while retaining source configuration |
| [delete-toolkit](../reference/delete-toolkit.md) | Uninstall the Creatio toolkit skill from coding agents |
| [disable-knowledge-source](../reference/disable-knowledge-source.md) | Disable one configured knowledge source without deleting its cache |
| [enable-knowledge-source](../reference/enable-knowledge-source.md) | Enable one configured knowledge source |
| [info-knowledge](../reference/info-knowledge.md) | Show configured knowledge sources, installed generations, and update status |
| [install-knowledge](../reference/install-knowledge.md) | Install verified knowledge from one source or all enabled sources |
| [install-toolkit](../reference/install-toolkit.md) | Install the Creatio toolkit skill for all detected coding agents |
| [list-knowledge-examples](../reference/list-knowledge-examples.md) | Discover registered reference examples without cloning them |
| [list-knowledge-sources](../reference/list-knowledge-sources.md) | List all configured knowledge sources |
| [mcp-http](../reference/mcp-http.md) | start MCP server in HTTP transport mode |
| [mcp-server](../reference/mcp-server.md) | Starts a Model Context Protocol (MCP) server that communicates over standard input/output using JSON-RPC 2.0 |
| [remove-knowledge-source](../reference/remove-knowledge-source.md) | Remove one configured source and its managed cache |
| [update-knowledge](../reference/update-knowledge.md) | Update verified knowledge from one source or all enabled sources |
| [update-toolkit](../reference/update-toolkit.md) | Update the Creatio toolkit skill for all detected coding agents |

<!-- commands:end -->
