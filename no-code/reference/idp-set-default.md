---
command: idp-set-default
block: clio-security
source: clio 8.1.0.145, clio/docs/commands/idp-set-default.md (MIT)
---
# idp-set-default - Set the default identity provider in Creatio

Set the default identity provider in Creatio.


## Usage

```bash
clio idp-set-default (--id <VALUE> | --name <VALUE>) [options]
```


## Options

```bash
--id <VALUE>          Identity provider ID.
--name <VALUE>        Identity provider name.
--timeout <NUMBER>    Request timeout in milliseconds. Default: 100000.
-e, --Environment     Environment name.
```


## Examples

```bash
clio idp-set-default --name MainIdP -e dev
clio idp-set-default --id 00000000-0000-0000-0000-000000000001 -e dev
```
