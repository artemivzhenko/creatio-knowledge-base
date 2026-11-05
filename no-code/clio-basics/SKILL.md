---
name: clio-basics
description: How an agent runs clio at all - install, register a Creatio environment, authenticate, read help, and the settings-file traps that block every other command. Read first when a clio command fails for a reason that is not the command itself.
---

# clio basics

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).

## What clio is

A .NET global tool (`dotnet tool install -g clio`) that talks to a Creatio site over its
service endpoints and, for the deeper commands, through the **cliogate** package installed on
that site (`clio install-gate -e <env>`). Every command that touches an environment takes
`-e <name>` (a registered environment) or `-u <url> -l <login> -p <password>`.

```bash
clio ver                      # clio, gate, process-builder versions, settings file path
clio reg-web-app dev -u http://host:40005 -l Supervisor -p ***   # register once
clio show-web-app-list        # registered environments
clio ping -e dev              # reachable?
clio get-info -e dev          # core version, culture, maintainer
clio <command> --help         # full help of any command
clio help                     # all commands
```

## Workflow for an agent

1. `clio ver` - confirm clio runs and note the settings file path.
2. `clio show-web-app-list` - pick the environment by name; never invent one.
3. `clio ping -e <env>` before a batch of commands; `clio get-info -e <env>` to learn the
   platform version, because what works differs between 8.x and 10.x.
4. Prefer `-e <env>` over inline credentials: inline passwords end up in shell history and
   in the agent's transcript.

## Traps (verified)

- **A stale `ActiveEnvironmentKey` breaks clio's MCP server while the CLI keeps working.**
  The settings file (`%LOCALAPPDATA%\creatio\clio\appsettings.json`) keeps an "active"
  environment; if it names a deleted one, every MCP tool that needs an environment answers
  "clio settings bootstrap is broken", even with `environment-name` supplied. The fix the
  message suggests (`clio set-active-environment`) does not exist in 8.1.0.145, and
  `reg-web-app --active-environment <name>` fails on the same check. Edit the key in the
  JSON file by hand (back it up first).
- **The installed clio and the source on GitHub `main` differ.** Read the source at the tag
  `clio ver` prints; behaviour on `main` (for example user-task prefix handling) may not be
  released yet.
- **`clio` is not on PATH inside some editor terminals** on Windows until the terminal is
  restarted after `dotnet tool install`.
- **Command names are kebab-case; many have hidden aliases** (`clio ping` =
  `ping-app`). The reference page lists the aliases where the docs do.
- **Most read commands take named options, not positional values**:
  `get-entity-schema-properties --schema-name iaTest`, `get-app-info --code X`,
  `list-app-sections --application-code X`, `get-object-rights --entity-schema-name X`.
  A positional name fails with "`<option> is required`". Copy the synopsis from the
  reference page.
- **Broken in clio 8.1.0.145**: `auth-status` (DI error "No service for type
  AuthStatusCommand"), `get-build-info` without arguments (null reference),
  `get-pkg-version <path>` (crashes with a stack trace), `show-local-envs` (hangs).
  Use `ping`/`healthcheck`, `get-info` and `list-packages` instead.
- **10.x-only on the platform side** (refused on 8.2.3 with a clear message):
  `list-themes` and the theme commands (`[version-too-old]`), `get-entity-connections`
  (`EntityConnections is not registered`), `get-app-info` (`Column by path Package not
  found`), `get-record-rights` (HTML instead of JSON), DataForge.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [auth-status](../reference/auth-status.md) | Reports the configured authentication flow, whether a session is cached, and the access-token expiry |
| [autoupdate](../reference/autoupdate.md) | Enable or disable automatic clio updates on startup |
| [check-nuget-update](../reference/check-nuget-update.md) | Check for Creatio package updates in NuGet |
| [clear-browser-session](../reference/clear-browser-session.md) | delete the cached Creatio browser session |
| [config](../reference/config.md) | View and set clio configuration defaults |
| [env-ui](../reference/env-ui.md) | Interactive console UI for environment management |
| [externalLink](../reference/externalLink.md) | Handle external deep links |
| [get-browser-session](../reference/get-browser-session.md) | obtain an authenticated Creatio browser session |
| [get-build-info](../reference/get-build-info.md) | Get build information |
| [get-info](../reference/get-info.md) | Get system information for Creatio instance |
| [get-user-culture](../reference/get-user-culture.md) | Print the logged-in Creatio user's profile culture |
| [get-webservice-url](../reference/get-webservice-url.md) | Get base url for web service |
| [healthcheck](../reference/healthcheck.md) | Healthcheck monitoring |
| [hosts](../reference/hosts.md) | list all registered Creatio hosts and their running status |
| [info](../reference/info.md) | Display version information for clio and related components |
| [list-environments](../reference/list-environments.md) | Display registered Creatio environment configurations |
| [login](../reference/login.md) | Signs in to an SSO-enabled Creatio environment using OAuth authorization code and PKCE |
| [logout](../reference/logout.md) | Revokes the cached OAuth refresh token and deletes the local token file |
| [open-settings](../reference/open-settings.md) | Open the clio settings file |
| [open-web-app](../reference/open-web-app.md) | open application in web browser |
| [pin-certificate](../reference/pin-certificate.md) | `pin-certificate` stores the preferred IIS certificate thumbprint in clio's `appsettings.json` |
| [ping-app](../reference/ping-app.md) | Verify connectivity to a Creatio environment |
| [ref-to](../reference/ref-to.md) | Change package project core paths |
| [reg-web-app](../reference/reg-web-app.md) | create/update a web application (website) |
| [register](../reference/register.md) | Register clio commands in Windows context menu |
| [set-webservice-url](../reference/set-webservice-url.md) | Set base url for web service |
| [show-local-envs](../reference/show-local-envs.md) | Show local environments with filesystem and auth status |
| [unreg-web-app](../reference/unreg-web-app.md) | Remove a registered Creatio environment |
| [unregister](../reference/unregister.md) | Unregister clio commands from Windows context menu |
| [update-cli](../reference/update-cli.md) | Update clio to the latest available version |

<!-- commands:end -->
