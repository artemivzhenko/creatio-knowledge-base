---
command: disable-knowledge-source
block: clio-mcp
source: clio 8.1.0.145, clio/docs/commands/disable-knowledge-source.md (MIT)
---
# disable-knowledge-source - Disable one configured knowledge source without deleting its cache

## Name

disable-knowledge-source - Disable one configured knowledge source without deleting its cache


## Synopsis

```bash
clio disable-knowledge-source --alias <alias> [--json]
```


## Description

Atomically disables one configured source. The source becomes ineligible for logical topics and
exact namespaced routes on the next runtime lookup. Configuration and installed generations remain
on disk, so the source can be re-enabled without deleting its last-known-good cache.


## Options

```bash
--alias <alias>   Required configured source alias
--json            Emit indented JSON
```


## Examples

```bash
clio disable-knowledge-source --alias partner
clio disable-knowledge-source --alias partner --json
```


## Exit Codes

    0   Source was disabled or was already disabled
    1   Source was not found or configuration persistence failed
