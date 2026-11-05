---
command: pull-pkg
block: clio-packages
source: clio 8.1.0.145, clio/docs/commands/pull-pkg.md (MIT)
---
# pull-pkg - download package to local file system from default a web application

## Name

pull-pkg - download package to local file system from default a web application


## Description

pull-pkg command can be used in CI/CD pipeline or in development
when you need download package from a web application (website).


## Prerequisites

The default download path uses the core PackageInstallerService and does **not** require cliogate.

The `--async` option requires the cliogate package to be installed on the target Creatio environment.
If cliogate is not installed, an `--async` download displays an error and exits.
Install or update cliogate with `clio install-gate -e <ENVIRONMENT_NAME>`.


## Synopsis

```bash
clio pull-pkg <PACKAGE_NAME>
```


## Options

```bash
Package name (pos. 0)	Name of package for download

--uri                   -u          Application uri

--Password              -p          User password

--Login                 -l          User login (administrator permission required)

--Environment           -e          Environment name

--Maintainer            -m          Maintainer name
```


## Example

```bash
clio pull-pkg <PACKAGE_NAME>
pull-pkg package to local file system from default application

clio pull-pkg <PACKAGE_NAME> -e <ENVIRONMENT_NAME>
pull-pkg package to local file system from non default application
```
