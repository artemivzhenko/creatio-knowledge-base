---
command: clone-env
block: clio-infrastructure
source: clio 8.1.0.145, clio/docs/commands/clone-env.md (MIT)
---
# clone-env - Clone environment settings

## Name

clone-env - Clone environment settings


## Description

Creates a copy of an existing environment definition in clio settings.


## Synopsis

```bash
clio clone-env <SOURCE_ENVIRONMENT> <TARGET_ENVIRONMENT>
```


## Options

```bash
<SOURCE_ENVIRONMENT>
Existing registered environment to copy

<TARGET_ENVIRONMENT>
New environment name to create
```


## Examples

```bash
clio clone-env dev test
clone-env the dev environment configuration into test
```
