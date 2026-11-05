---
command: enable-knowledge-source
block: clio-mcp
source: clio 8.1.0.145, clio/docs/commands/enable-knowledge-source.md (MIT)
---
# enable-knowledge-source - Enable one configured knowledge source

## Name

enable-knowledge-source - Enable one configured knowledge source


## Synopsis

```bash
clio enable-knowledge-source --alias <alias> [--json]
```


## Description

Atomically enables one configured source. A valid retained generation becomes eligible for serving
and topic resolution on the next runtime lookup. If the source has no valid installed generation,
run `install-knowledge --source <alias>` after enabling it.


## Options

```bash
--alias <alias>   Required configured source alias
--json            Emit indented JSON
```


## Examples

```bash
clio enable-knowledge-source --alias partner
clio install-knowledge --source partner
```


## Exit Codes

    0   Source was enabled or was already enabled
    1   Source was not found or configuration persistence failed
