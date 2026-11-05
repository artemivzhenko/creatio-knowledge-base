---
command: idp-list
block: clio-security
source: clio 8.1.0.145, clio/docs/commands/idp-list.md (MIT)
---
# idp-list - List identity providers configured in Creatio

List identity providers configured in Creatio.


## Usage

```bash
clio idp-list [options]
```


## Options

```bash
--json                 Output as indented JSON instead of a table.
--timeout <NUMBER>     Request timeout in milliseconds. Default: 100000.
-e, --Environment      Environment name.
```


## Examples

```bash
clio idp-list -e dev
clio idp-list --json -e dev
```
