---
command: set-fsm-config
block: clio-workspace-and-build
source: clio 8.1.0.145, clio/docs/commands/set-fsm-config.md (MIT)
---
# set-fsm-config - Set file system mode properties in config file

## Name

set-fsm-config - Set file system mode properties in config file


## Description

Updates the Creatio configuration file to enable or disable File Design Mode.

It changes:
- terrasoft/fileDesignMode enabled
- appSettings/UseStaticFileContent value (opposite of FSM)

You can provide either:
- --physicalPath (path to the environment folder)
- -e / --Environment (registered environment)

On Windows the command updates either Web.config or Terrasoft.WebHost.dll.config.
On macOS and Linux it supports NET8 environments and uses the registered EnvironmentPath
or the provided --physicalPath to find Terrasoft.WebHost.dll.config.


## Example

```bash
clio set-fsm-config -e MyEnvironment on

clio set-fsm-config --physicalPath "/path/to/creatio" off
```
