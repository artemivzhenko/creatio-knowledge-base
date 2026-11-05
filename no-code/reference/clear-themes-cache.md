---
command: clear-themes-cache
block: clio-theming
source: clio 8.1.0.145, clio/docs/commands/clear-themes-cache.md (MIT)
---
# clear-themes-cache - refresh only the Creatio theme cache

## Name

clear-themes-cache - refresh only the Creatio theme cache


## Description

`clear-themes-cache` refreshes the Creatio theme catalog cache on the target
environment. It affects only theme data and does not restart the application.
Requires Creatio 10.0.0 or later on the target environment.

A normal package push (`push-workspace` / `push-pkg`) already refreshes the theme
registry, so this command is only needed when theme files change on the environment
outside a clio install.


## Synopsis

```bash
clio clear-themes-cache [options]
```


## Options

```bash
--uri               -u          Application uri

--Password          -p          User password

--Login             -l          User login (administrator permission required)

--Environment       -e          Environment name

--Maintainer        -m          Maintainer name
```


## Aliases

```bash
flush-themes
```


## Example

```bash
clio clear-themes-cache
clear the theme cache of the default environment

clio clear-themes-cache -e myapp
clear the theme cache of the environment registered as myapp
```
