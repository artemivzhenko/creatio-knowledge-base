---
command: list-apps
block: clio-apps
source: clio 8.1.0.145, clio/docs/commands/list-apps.md (MIT)
---
# list-apps - List installed apps

## Name

list-apps - List installed apps

**Aliases:** `get-app-list`, `app-list`, `apps`, `apps-list`, `lia`


## Description

Displays the list of applications installed in the selected environment.


## Synopsis

```bash
clio list-apps [OPTIONS]
```


## Options

```bash
-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio list-apps -e dev
Show applications installed in the dev environment
```
