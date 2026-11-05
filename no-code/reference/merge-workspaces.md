---
command: merge-workspaces
block: clio-workspace-and-build
source: clio 8.1.0.145, clio/docs/commands/merge-workspaces.md (MIT)
---
# merge-workspaces - Merge workspaces

## Name

merge-workspaces - Merge workspaces


## Description

Combines multiple workspaces into a single resulting workspace structure.


## Synopsis

```bash
clio merge-workspaces [OPTIONS]
```


## Options

```bash
Supports the canonical merge-workspaces command options.
```


## Examples

```bash
clio merge-workspaces --help
Display canonical options and usage examples
```


## Notes

Packing stops when a folder under `Schemas/` or `Data/` of any package has no
`descriptor.json`, because Creatio would reject the installation with
`Invalid descriptor`. The error names the full local path of each such folder; see
[push-workspace](push-workspace.md#folders-without-descriptorjson) for what to do
with it.
