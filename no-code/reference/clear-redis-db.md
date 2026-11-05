---
command: clear-redis-db
block: clio-workspace-and-build
source: clio 8.1.0.145, clio/docs/commands/clear-redis-db.md (MIT)
---
# clear-redis-db - clear web application(website) cache

## Name

clear-redis-db - clear web application(website) cache


## Description

clear-redis-db command can be used in CI/CD pipeline or in development
when you need forcible clear a web application (website) cache. Be
attentive, the command only clear  web application cache and doesn't
restart it.


## Synopsis

```bash
clear-redis-db [Name] [options]
```


## Options

```bash
Name (pos. 0)	Application name

--uri               -u          Application uri

--Password			-p          User password

--Login             -l          User login (administrator permission required)

--Environment       -e          Environment name

--Maintainer        -m          Maintainer name
```


## Example

```bash
clio clear-redis-db
clear current web application(website) cache

clio clear-redis-db myapp
clear web application(website) cache that registered as a myapp
```
