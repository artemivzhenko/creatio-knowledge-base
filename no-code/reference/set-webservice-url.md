---
command: set-webservice-url
block: clio-basics
source: clio 8.1.0.145, clio/docs/commands/set-webservice-url.md (MIT)
---
# set-webservice-url - Set base url for web service

## Name

set-webservice-url - Set base url for web service


## Description

Stores or updates the base URL assigned to a configured web service.


## Synopsis

```bash
clio set-webservice-url <SERVICE_NAME> <URL> [OPTIONS]
```


## Options

```bash
<SERVICE_NAME>
Web service name to update

<URL>
New base URL for the service

-e, --Environment <ENVIRONMENT_NAME>
Target environment name
```


## Examples

```bash
clio set-webservice-url CustomerApi https://api.example.com -e dev
Set a service URL in the dev environment
```
