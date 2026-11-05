---
name: clio-infrastructure
description: Local Creatio installations through clio - deploy a build to IIS or Kubernetes, restore a database, Windows features, Docker, web-farm mode, start and stop, remove an environment. Destructive block; read before running anything here on a shared machine.
---

# clio: local infrastructure

Read on clio 8.1.0.145; **not verified** (deliberately: these commands create and destroy
environments). Command pages: [reference/](../reference/).

```bash
clio check-windows-features / manage-windows-features    # IIS prerequisites
clio deploy-creatio ...                                   # unpack a build, create site + DB
clio restore-db ...                                       # restore a backup into an environment's DB
clio start / stop <env>                                   # IIS site
clio uninstall-creatio <env>                              # removes site, DB, files
clio create-k8-files / open-k8-files / deploy-infrastructure / delete-infrastructure
clio turn-farm-mode / compare-web-farm-node
```

Rules for an agent:

- `uninstall-creatio`, `restore-db`, `delete-infrastructure`, `clear-local-env` destroy
  data; never run them without the environment name confirmed by the user in this
  session.
- `deploy-creatio` has a preflight path on the MCP side (`assert-infrastructure` ->
  `show-passing-infrastructure` -> `find-empty-iis-port`); use it to pick a free port.
- Local installs are where cliogate, CrtProcessBuilder and FSM are usually switched on;
  a shared test environment is not the place for experiments with these commands.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [check-windows-features](../reference/check-windows-features.md) | Check windows for the required components |
| [clear-local-env](../reference/clear-local-env.md) | clean up deleted local environments and orphaned services |
| [clone-env](../reference/clone-env.md) | Clone environment settings |
| [compare-web-farm-node](../reference/compare-web-farm-node.md) | Compare file content across web farm nodes |
| [create-k8-files](../reference/create-k8-files.md) | Generate Kubernetes deployment files for Creatio infrastructure |
| [delete-infrastructure](../reference/delete-infrastructure.md) | Delete Kubernetes infrastructure for Creatio |
| [deploy-creatio](../reference/deploy-creatio.md) | Deploys Creatio application from a zip file |
| [deploy-infrastructure](../reference/deploy-infrastructure.md) | Deploy Kubernetes infrastructure for Creatio |
| [manage-windows-features](../reference/manage-windows-features.md) | manage Windows features required for Creatio |
| [open-k8-files](../reference/open-k8-files.md) | Open folder K8 files for deployment |
| [prune-db-templates](../reference/prune-db-templates.md) | Interactively prune clio-managed PostgreSQL templates |
| [restore-db](../reference/restore-db.md) | Every restore-db run creates a temp database-operation log file |
| [start](../reference/start.md) | start local Creatio application |
| [stop](../reference/stop.md) | stop Creatio services and background processes |
| [turn-farm-mode](../reference/turn-farm-mode.md) | Configure IIS site for Creatio web farm deployment |
| [uninstall-creatio](../reference/uninstall-creatio.md) | Completely remove a local Creatio instance |

<!-- commands:end -->
