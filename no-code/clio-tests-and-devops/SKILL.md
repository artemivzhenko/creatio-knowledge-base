---
name: clio-tests-and-devops
description: Test projects and delivery tooling through clio - scaffold unit and integration test projects, run scenario files, assert infrastructure, NuGet packaging of packages, Docker images, logging, and clio's own add-on packages (cliogate, dashboards migrator). Use for "create a test project", "pack the package as NuGet", "install cliogate".
---

# clio: tests and DevOps

Read on clio 8.1.0.145; **not verified** on Creatio 8.2.3 except `install-gate` (the gate
was already present at 2.0.0.43). Command pages: [reference/](../reference/).

```bash
clio new-test-project ... -e dev              # NUnit project referencing the environment's core
clio new-integration-test-project ...         # ATF.Repository based integration tests
clio new-ui-project ...                       # Angular remote module scaffold
clio run <scenario.yaml>                      # scripted sequence of clio commands
clio assert ...                               # infrastructure checks
clio pack-nuget-pkg / push-nuget-pkg / restore-nuget-pkg ...
clio build-docker-image ...
clio install-gate -e dev                      # cliogate, required by SQL and many MCP tools
clio add-custom-logging ...                   # NLog routing for one package
```

`run` executes a YAML scenario of commands with shared settings - the way to replay a
deployment or a test sequence without a shell script. `listen` streams the site's log.

For the C# test content itself use the code recipes (`search_recipes("unit test", area=
"Backend")`), not this block.

Verified on 8.2.3: MCP `trigger-smoke {entity, values, watch, cleanup}` creates the record,
waits 15 s for a process run and cleans up; without a signal-started process on the entity
it reports "no run started" - that is the expected answer, not a failure. MCP
`add-item-model {namespace, folder}` generated 920 entity model classes in 14 s.
`assert-infrastructure` / `show-passing-infrastructure` / `find-empty-iis-port` run locally
and report what the host has (no Kubernetes, one PostgreSQL, no Redis here).

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [add-custom-logging](../reference/add-custom-logging.md) | Add package-specific NLog file routing to a local Creatio environment |
| [assert](../reference/assert.md) | Validates infrastructure and filesystem resources |
| [build-docker-image](../reference/build-docker-image.md) | Build a Docker image for a Creatio .NET 8+ distribution or bundled database backup |
| [experimental](../reference/experimental.md) | List and toggle clio experimental feature flags |
| [install-dashboards-migrator](../reference/install-dashboards-migrator.md) | Install the bundled dashboards-migrator package to a Creatio environment |
| [install-gate](../reference/install-gate.md) | Install clio API gateway package to Creatio environment |
| [listen](../reference/listen.md) | Subscribe to a websocket |
| [new-integration-test-project](../reference/new-integration-test-project.md) | new-integration-test-project |
| [new-test-project](../reference/new-test-project.md) | Run from a clio workspace root |
| [new-ui-project](../reference/new-ui-project.md) | Create a new Freedom UI project |
| [pack-nuget-pkg](../reference/pack-nuget-pkg.md) | Pack NuGet package |
| [push-nuget-pkg](../reference/push-nuget-pkg.md) | Push package on NuGet server |
| [ring](../reference/ring.md) | Manages the internal clio-ring Windows x64 desktop preview |
| [run](../reference/run.md) | Run a YAML scenario and refresh environments between dependent steps |

<!-- commands:end -->
