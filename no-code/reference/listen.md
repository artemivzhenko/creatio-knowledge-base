---
command: listen
block: clio-tests-and-devops
source: clio 8.1.0.145, clio/docs/commands/listen.md (MIT)
---
# listen - Subscribe to a websocket

## Name

listen - Subscribe to a websocket


## Description

Opens a websocket subscription and streams messages from the selected source.
Log broadcasting is provided by the cliogate ATFLogService.


## Prerequisites

This command requires the cliogate package to be installed on the target Creatio environment.
If cliogate is not installed, the command displays an error and exits.
Install or update cliogate with `clio install-gate -e <ENVIRONMENT_NAME>`.


## Synopsis

```bash
clio listen [OPTIONS]
```


## Options

```bash
Supports the canonical listen command options.
```


## Examples

```bash
clio listen --help
Display canonical options and usage examples
```
