---
command: get-webservice-url
block: clio-basics
source: clio 8.1.0.145, clio/docs/commands/get-webservice-url.md (MIT)
---
# get-webservice-url - Get base url for web service

## Name

get-webservice-url - Get base url for web service


## Description

Displays the currently configured base URL for a web service entry.


## Synopsis

```bash
clio get-webservice-url [OPTIONS]
```


## Options

```bash
-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio get-webservice-url -e dev
Show configured service URLs for the dev environment
```
