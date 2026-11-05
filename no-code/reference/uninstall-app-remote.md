---
command: uninstall-app-remote
block: clio-packages
source: clio 8.1.0.145, clio/docs/commands/uninstall-app-remote.md (MIT)
---
# uninstall-app-remote - Uninstall application

## Name

uninstall-app-remote - Uninstall application


## Description

Removes an installed application from the target Creatio environment.


## Synopsis

```bash
clio uninstall-app-remote <APP_NAME> [OPTIONS]
```


## Options

```bash
<APP_NAME>
Application name to uninstall

-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio uninstall-app-remote MyApp -e dev
Remove an application from the dev environment
```
