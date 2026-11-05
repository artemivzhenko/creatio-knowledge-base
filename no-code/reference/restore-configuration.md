---
command: restore-configuration
block: clio-workspace-and-build
source: clio 8.1.0.145, clio/docs/commands/restore-configuration.md (MIT)
---
# restore-configuration - Restore configuration from last backup

## Name

restore-configuration - Restore configuration from last backup


## Description

Restores Creatio configuration from the latest available backup package.


## Synopsis

```bash
clio restore-configuration [OPTIONS]
```


## Options

```bash
-d
Restore configuration without rollback data

-f
Restore configuration without SQL backward-compatibility check

-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio restore-configuration -e dev
restore-configuration configuration from backup on the dev environment

clio restore-configuration -d -f -e dev
restore-configuration configuration with relaxed safety checks
```
