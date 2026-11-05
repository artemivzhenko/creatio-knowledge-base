---
command: list-knowledge-sources
block: clio-mcp
source: clio 8.1.0.145, clio/docs/commands/list-knowledge-sources.md (MIT)
---
# list-knowledge-sources - List all configured knowledge sources

## Name

list-knowledge-sources - List all configured knowledge sources


## Synopsis

```bash
clio list-knowledge-sources [--json]
```


## Description

Lists every source under `knowledge.sources`, including disabled sources. Human output shows alias,
stable library identity, transport, enablement, priority, participation, and a credential-safe
location. The command reads configuration only and does not contact GitHub, Git, or NuGet.

Use `info-knowledge` for installed generation, validation, resolved revision, and update state.


## Options

```bash
--json   Emit indented JSON
```


## Examples

```bash
clio list-knowledge-sources
clio list-knowledge-sources --json
```


## Exit Codes

    0   Configured sources were listed
    1   Source configuration could not be read safely
