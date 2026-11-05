---
command: deploy-application
block: clio-apps
source: clio 8.1.0.145, clio/docs/commands/deploy-application.md (MIT)
---
# deploy-application - Deploy app from current environment to destination environment

## Name

deploy-application - Deploy app from current environment to destination environment


## Description

Transfers an application package from one Creatio environment to another.


## Synopsis

```bash
clio deploy-application <APP_NAME> [OPTIONS]
```


## Options

```bash
<APP_NAME>
Application name to deploy

-e, --Environment <SOURCE_ENVIRONMENT>
Source environment name

-d, --Destination <TARGET_ENVIRONMENT>
Target environment name
```


## Examples

```bash
clio deploy-application MyApp -e source -d target
Deploy an application from one environment to another
```
