---
name: clio-workspace-and-build
description: The pro-code loop with clio - a workspace of packages, push it, compile the configuration or one package, read the compilation log, restart, flush Redis, switch file-system mode, link packages to a repository. Use for "compile", "why does the build fail", "restart the site", "FSM".
---

# clio: workspace and build

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).

## Workspace

A workspace is a folder with `.clio/workspaceSettings.json` (packages, target version) and
`packages/<Name>/`. It is the git-able form of a set of packages.

```bash
clio create-workspace -e dev                 # from the environment's custom packages
clio restore-workspace -e dev                # pull every workspace package from the site
clio push-workspace -e dev                   # install every workspace package
clio build-workspace                         # local build of the C# (needs the SDK and core refs)
clio show-diff ...                           # see the reference page
```

## Compile and verify

```bash
clio compile-package UsrMyPackage -e dev     # one package (preferred after a push)
clio compile-configuration -e dev            # whole configuration (slow; only when required)
clio last-compilation-log -e dev             # the build output with file:line errors
clio restart-web-app -e dev                  # after DLL changes on a .NET Framework host
clio clear-redis-db -e dev                   # after data-level changes that are cached
```

Decide by what changed:

| Change | Needed afterwards |
| --- | --- |
| entity schema, lookup, page, business rule (no-code) | nothing - usable at once; OData rebuilds itself in 1-2 min |
| C# in one package | `compile-package <pkg>`; restart only if the log says the assembly changed |
| client JS schema | browser reload |
| package data (bindings) | `clear-redis-db` when the cached value does not change |

## File-system mode (FSM)

`turn-fsm on` plus `link-from-repository` make the site read packages from a folder you
control, so designer saves land in files. It is the fastest loop but the most fragile one
(exports written into a linked repository, `.csproj` regenerated on every compile, deleted
schemas leaving folders behind). Most environments run with FSM off; prefer the
push / pull cycle in [clio-packages](../clio-packages/SKILL.md) unless FSM is already on.
`clio get-fsm-mode` exists only on clio's MCP, not as a CLI verb (verified).

## Traps (verified)

- **The last compilation log can be red before you touched anything.** On the test
  environment the configuration already failed on another package (a missing assembly
  reference); a new error on top looks like yours. Read the log first, then push.
- **Package compilation is per package; `compile-configuration` rebuilds everything** and
  takes minutes. Never run it "just in case".
- **A restart on a .NET Framework host is done by the platform itself when the workspace
  assembly changes**; a manual restart right after it races the automatic one.
- **MCP `compile-creatio {package-name}` returns after ~45 s with an `operation-id`
  while the build keeps running**; poll `compile-status` until `succeeded` / `failed`
  (one package took 5 min 12 s on 8.2.3, exit code 0, verified). A package compile
  succeeded even though the whole-configuration log was red from another package.
- **MCP `restart-by-environment-name {waitReady: true}`** brought the site back in 30 s
  and `restart-status` reported `ready` (verified).
- **`download-configuration-by-environment` wants an existing workspace path** (one with
  `.clio/workspaceSettings.json`); a scratch folder is refused. It copies the core
  assemblies the C# build needs (4 s on a local host).

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [apply-manifest](../reference/apply-manifest.md) | Apply environment manifest |
| [build-workspace](../reference/build-workspace.md) | Build or rebuild workspace for selected environment |
| [cfg-worspace](../reference/cfg-worspace.md) | Configure workspace package selection |
| [clear-redis-db](../reference/clear-redis-db.md) | clear web application(website) cache |
| [compile-configuration](../reference/compile-configuration.md) | compile Creatio configuration with real-time progress monitoring |
| [compile-package](../reference/compile-package.md) | compile one or more Creatio packages on a target environment |
| [create-workspace](../reference/create-workspace.md) | By default, the command can connect to a Creatio environment (via -e/--uri) to download editable packages and populat... |
| [download-configuration](../reference/download-configuration.md) | Download Creatio configuration files to workspace |
| [generate-source-code](../reference/generate-source-code.md) | generate source code for schemas in Creatio |
| [git-sync](../reference/git-sync.md) | Sync environment with Git repository |
| [install-nuget-pkg](../reference/install-nuget-pkg.md) | Install NuGet package to a web application |
| [last-compilation-log](../reference/last-compilation-log.md) | Get last compilation log |
| [link-core-src](../reference/link-core-src.md) | Link core source code to environment for development |
| [link-from-repository](../reference/link-from-repository.md) | Link repository package(s) to environment |
| [link-package-store](../reference/link-package-store.md) | Link packages from PackageStore to environment packages with version control |
| [link-to-repository](../reference/link-to-repository.md) | Link environment package(s) to repository |
| [link-workspace-with-tide-repository](../reference/link-workspace-with-tide-repository.md) | Link a workspace with a T.I.D.E |
| [merge-workspaces](../reference/merge-workspaces.md) | Merge workspaces |
| [pkg-to-db](../reference/pkg-to-db.md) | Imports the package definitions stored on the web application's file system into the Creatio configuration database |
| [pkg-to-file-system](../reference/pkg-to-file-system.md) | Exports the package definitions registered in the Creatio configuration database to the web application's file system |
| [push-workspace](../reference/push-workspace.md) | Push workspace to selected environment |
| [restart-web-app](../reference/restart-web-app.md) | restart web application(website) |
| [restore-configuration](../reference/restore-configuration.md) | Restore configuration from last backup |
| [restore-nuget-pkg](../reference/restore-nuget-pkg.md) | Restore NuGet package to a folder |
| [restore-workspace](../reference/restore-workspace.md) | When no packages are eligible after applying ignore and external-package settings, the command reports a warning and... |
| [save-state](../reference/save-state.md) | Save state of Creatio instance to file |
| [set-dev-mode](../reference/set-dev-mode.md) | Setup develepment mode for selected web application(website) |
| [set-fsm-config](../reference/set-fsm-config.md) | Set file system mode properties in config file |
| [show-diff](../reference/show-diff.md) | Show difference between environments or manifests |
| [switch-nuget-to-dll-reference](../reference/switch-nuget-to-dll-reference.md) | Switch NuGet references to DLL references in csproj files |
| [turn-fsm](../reference/turn-fsm.md) | Turn file system mode on or off for an environment |

<!-- commands:end -->
