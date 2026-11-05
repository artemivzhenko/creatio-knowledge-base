---
command: pkg-hotfix
block: clio-packages
source: clio 8.1.0.145, clio/docs/commands/pkg-hotfix.md (MIT)
---
# pkg-hotfix - Enable or disable package hotfix state

## Name

pkg-hotfix - Enable or disable package hotfix state


## Description

Changes the hotfix mode state for a package in the selected environment.


## Synopsis

```bash
clio pkg-hotfix <PACKAGE_NAME> <true|false> [OPTIONS]
```


## Options

```bash
<PACKAGE_NAME>
Package name to update

<true|false>
Desired hotfix mode state

-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio pkg-hotfix MyPackage true -e dev
Enable hotfix mode for a package

clio pkg-hotfix MyPackage false -e dev
Disable hotfix mode for a package
```
