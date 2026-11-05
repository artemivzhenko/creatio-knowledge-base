---
command: delete-pkg-remote
block: clio-packages
source: clio 8.1.0.145, clio/docs/commands/delete-pkg-remote.md (MIT)
---
# delete-pkg-remote - delete package from application

## Name

delete-pkg-remote - delete package from application


## Description

delete-pkg-remote command can be used in CI/CD pipeline or in development
when you need delete package from a web application (website).


## Synopsis

```bash
clio delete-pkg-remote <PACKAGE_NAME>
```


## Options

```bash
Package name (pos. 0)	Name/path of package folder or path for zip or gz package file

--uri                   -u          Application uri

--Password              -p          User password

--Login                 -l          User login (administrator permission required)

--Environment           -e          Environment name

--Maintainer            -m          Maintainer name
```


## Example

```bash
clio delete-pkg-remote <PACKAGE_NAME>
delete-pkg-remote package with <PACKAGE_NAME> from default application

clio delete-pkg-remote <PACKAGE_NAME> -e dev
delete-pkg-remote package with <PACKAGE_NAME> from specify application with name dev
```
