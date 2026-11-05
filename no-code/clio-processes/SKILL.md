---
name: clio-processes
description: Business processes and user tasks through clio - generate process models, build and modify processes (MCP, needs CrtProcessBuilder), create user tasks and their parameter pages, register process elements. Read before touching processes on Creatio 8.x - most of this block does not work there.
---

# clio: business processes and user tasks

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).

## What clio offers

- MCP-only process tools: `create-business-process`, `modify-business-process`,
  `describe-business-process`, `validate-process-graph`, `list-user-tasks`, process
  versions and `run-process`. They need the **CrtProcessBuilder** package on the site
  (`clio install-process-builder -e dev`), and a guidance set of about 50 articles
  (`get-guidance process-digest` is the entry point).
- CLI: `generate-process-model` (C# model classes for a process), `get-process-signature`,
  `add-user-task` / `create-user-task-page` / `modify-user-task-parameters`,
  `register-process-element`.

## Traps (verified)

- **CrtProcessBuilder 1.6.6.125 does not compile on Creatio 8.2.3.** The install fails
  with `CS0117 DataValueType.Float0DataValueTypeUId` (and Money0/1/3) and
  `CS1061 ProcessUserTaskSchemaManager.FindRuntimeSchemaFromMetaData`; the package stays
  installed uncompiled and `delete-pkg-remote` refuses to remove it (archive-installed).
  Deactivate it in Installed applications. Every process MCP tool then refuses with
  "install CrtProcessBuilder". On 8.x build processes in the designer, or ship them as
  files in the package.
- **`add-user-task` on clio 8.1.0.145 is a dead end on an environment whose
  `SchemaNamePrefix` is not `Usr`:** the CLI insists the code starts with `Usr`, the site
  insists it starts with its own prefix. Fixed in the clio sources after the tag (PR
  #1876); until a release carries it, create user tasks as files in the package and
  `push-pkg`.
- **`add-user-task` with parameters fails with `Item with name "Enum" not found`** on
  8.2.3 (a type id the platform does not know).
- **Installing CrtProcessBuilder rebuilds the configuration and restarts the site** for
  everyone; ask before running it.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [add-user-task](../reference/add-user-task.md) | create a process user task schema from the current workspace |
| [create-user-task-page](../reference/create-user-task-page.md) | Creates an editable Classic parameter page for an existing workspace user task and links the task to its new page UId |
| [enroll-sequence-participants](../reference/enroll-sequence-participants.md) | Enroll an explicit selection of 1–100 unique contacts through Creatio's native sequence service |
| [generate-process-model](../reference/generate-process-model.md) | Generates a C# model for starting a business process through ATF.Repository |
| [get-process-page-facts](../reference/get-process-page-facts.md) | Reads the facts a **Pre-configured page** process element needs about a Freedom UI page |
| [get-process-signature](../reference/get-process-signature.md) | Resolves a business process by its code (schema Name) OR its display caption and returns its parameter signature: for... |
| [get-sequence-context](../reference/get-sequence-context.md) | Read effective sequence fields and live lookup/configuration choices using DataService |
| [install-process-builder](../reference/install-process-builder.md) | Install the bundled process-builder package to a Creatio environment |
| [modify-user-task-parameters](../reference/modify-user-task-parameters.md) | add or remove parameters on an existing workspace user task |
| [register-process-element](../reference/register-process-element.md) | Generate package-owned process element registration |

<!-- commands:end -->
