---
command: get-sql-schema
block: clio-schemas
source: clio 8.1.0.145, clio/docs/commands/get-sql-schema.md (MIT)
---
# get-sql-schema - Read body and metadata of a SQL script schema on a remote Creatio environment

## Name

get-sql-schema - Read body and metadata of a SQL script schema on a remote Creatio environment

**Aliases:** `sql-schema-get`


## Description

The get-sql-schema command reads the body and metadata of an existing SQL script schema on a
remote Creatio environment via SqlScriptSchemaDesignerService. The schema is resolved by name and
the script UId, name, package and body are returned. The legacy caption field is null. No local
workspace files are created or modified.

When `--output-file` is set, the schema body is written to the specified file and the body
field is omitted from the response JSON printed to stdout. This keeps the terminal output
small and makes it easy to edit the body locally before piping it back through
`update-sql-schema`. The output path is confined to the workspace or the OS temp directory
(symlinks are resolved; a path resolving outside both, or one that already exists, is rejected before
any write), because this command is MCP-callable and its path can be agent-supplied.


## Synopsis

```bash
clio get-sql-schema [options]
```


## Options

```bash
--schema-name                      SQL script schema name (required)

--output-file                      Optional absolute path. When set, the schema body is
                                   written to this file and the body field is omitted
                                   from the response JSON. Confined to the workspace or
                                   the OS temp directory

--uri                    -u       Application uri

--Password               -p       User password

--Login                  -l       User login (administrator permission required)

--Environment            -e       Environment name

--Maintainer             -m       Maintainer name
```


## Example

```bash
clio get-sql-schema --schema-name UsrCleanupStaleRows -e dev

clio get-sql-schema --schema-name UsrCleanupStaleRows --output-file /tmp/UsrCleanupStaleRows.sql -e dev
# Save the body to /tmp/UsrCleanupStaleRows.sql; response JSON omits the body

clio sql-schema-get --schema-name UsrCleanupStaleRows -e dev
# Same as the first example using the alias
```


## Native package SQL

Resolves package SQL scripts through VwSysSqlScriptInPackage and reads them through SqlScriptSchemaDesignerService/GetSchema. Ambiguous names are rejected. Updates preserve the existing engine, installation phase and dependencies.
