---
command: new-test-project
block: clio-tests-and-devops
source: clio 8.1.0.145, clio/docs/commands/new-test-project.md (MIT)
---
# new-test-project - Run from a clio workspace root

## Name

new-test-project (aliases: unit-test, create-test-project) - Create package unit-test projects


## Synopsis

```bash
clio new-test-project --package <NAME[,NAME...]>
```


## Description

Run from a clio workspace root. Creates tests/<NAME>/<NAME>.Tests.csproj and
its base fixture. Registers test and package projects in tests/UnitTests.slnx,
and the test project in MainSolution.slnx using Clio's solution writer.


## Options

```bash
--package <NAME[,NAME...]>
Required package name or comma-separated package names.
```


## Examples

```bash
clio new-test-project --package UsrOrders
clio new-test-project --package UsrOrders,UsrInvoices
```


## Notes

Existing project and fixture files are preserved. Rerun to repair missing
solution registrations. Existing legacy .sln files are left untouched.
A solution-write failure returns a nonzero exit code; do not report success.
Use the Clio scaffold before writing test cases; do not create a separate harness.
MCP: clio-run command=new-test-project with package-name, absolute workspace-path,
and environment-name. No ClioGate installation is needed for scaffolding.

The package project packages/<NAME>/Files/<NAME>.csproj must exist first.
A missing package project fails before any files are written.
