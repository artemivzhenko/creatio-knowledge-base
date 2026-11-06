---
name: clio-sql-and-data
description: Read and change Creatio data from the command line - run SQL scripts (execute-sql-script), call DataService and web services, OData and ESQ through clio's MCP, system settings, feature flags, data bindings and file uploads. Use for "query the database", "check a record", "update a system setting", "seed data".
---

# clio: SQL and data

Verified on clio 8.1.0.145, cliogate 2.0.0.43, Creatio 8.2.3 (PostgreSQL). Command pages:
[reference/](../reference/).

## Running SQL

`execute-sql-script` runs SQL **now**, on one environment. SQL that must ship with the package
and run on every install (views, functions, triggers, data fixes) is a package SQL script:
build it with [tools/sqlscripts](../tools/sqlscripts/README.md), `push-pkg` runs it.

`execute-sql-script` sends SQL to the site through cliogate (needs gate 2.0.0.41+) and
prints a table, or saves JSON / CSV / XLSX.

```bash
# read: always through a file, always JSON when the agent needs the values
clio execute-sql-script -e dev -f query.sql -v json -d result.json --silent
# write: the JSON export holds the affected-row count
clio execute-sql-script -e dev -f update.sql -v json -d out.json
```

Rules that keep it correct:

1. **Put the SQL in a file (`-f`).** Inline SQL on Windows PowerShell loses the double quotes
   around identifiers: `"SysPackage"` reaches PostgreSQL as `syspackage` and fails with
   `42P01 relation does not exist` (verified). From bash/cmd inline works, but a file is safe
   everywhere and keeps multi-line statements readable.
2. **Export JSON and read the file.** The console table wraps every cell at 40 characters,
   so long values and GUIDs get cut (verified: a 36-character GUID still fits; text does
   not). CSV is unquoted and semicolon-separated - unusable for free text.
3. **Quote identifiers.** Creatio tables and columns are mixed-case on PostgreSQL:
   `select "Name" from "SysPackage"`. Lookup columns are stored as `<Column>Id`.
4. **Exit code 1 on any SQL error**, with the database message and `POSITION` on stderr.
   Read stderr, do not retry blindly.
5. **A one-line script may hold `|nl|` markers** where newlines would be; cliogate converts
   them before execution (verified).
6. **Every statement is logged** on the site in `ClioSqlRequestLog` with its full text
   (gate 2.0.0.53+), so never put secrets in SQL.

Through clio's MCP the same tool is `execute-sql-script` with `script` or `file`, `view`,
`destination-path`, `silent` (see [clio-mcp](../clio-mcp/SKILL.md)); pass an absolute
destination path and read the file.

## Choosing the channel

| Need | Use | Why |
| --- | --- | --- |
| Ad-hoc read, diagnostics, bulk fix | `execute-sql-script` | fastest; bypasses the ORM, so no event listeners and no rights |
| Create / update records the platform way | MCP `odata-create` / `odata-update` / `odata-delete` | goes through the entity layer: defaults, listeners, rights apply (verified: a created row received the column default) |
| Read with the platform's filters | MCP `odata-read` (structured `filters`) or `execute-esq` | `odata-read` refuses raw `$filter` strings; `execute-esq` wants the SelectQuery inside `query` (both verified) |
| Call a configuration service | `call-service` | POST a JSON body to `/0/rest/<Service>/<Method>` |
| Raw DataService request | `dataservice`, `execute-dataservice-batch` | when the exact DataService shape is known |
| System setting | `set-syssetting`, MCP `get-sys-setting` / `update-sys-setting` | typed, no SQL on `SysSettingsValue` |
| Feature flag | `set-feature` | |
| Seed data shipped with a package | `create-data-binding`, `add-data-binding-row` (local) or the `-db` family (DB-first) | |

## Traps (verified)

- **OData after a schema change is asynchronous.** Right after `create-entity-schema` /
  `modify-entity-schema-column` the `/0/odata/<Entity>` controller is rebuilt in the
  background; a 404 for one or two minutes is normal. Wait, do not compile or restart.
- **`odata-read` rejects unknown arguments instead of guessing** (`filter`, `search`):
  the error names the valid arguments. Use `filters: {"all": [{"field","op","value"}]}`.
- **`odata-create` takes `rows`, not `data`** (it accepts `data` with a warning).
- **Empty lookups read back as `00000000-...` and empty dates as `0001-01-01`** through
  OData on 8.2.3, not as `null`.
- **DataForge tools (`dataforge-*`, test-data generation) require Creatio 10.0+**; on 8.x
  they refuse with a clear message.
- **Full OData CRUD works on 8.2.3** (verified): `odata-create {rows}` → `odata-update
  {id, confirm: true, data}` → `odata-read {filters}` → `odata-delete {id, confirm: true}`,
  each read back. `execute-esq` needs the SelectQuery under `query` (`rootSchemaName`,
  `columns.items.<alias>.expression.columnPath`); `-to-file` variants write the JSON.
- **System settings: `create-sys-setting {code, name, value-type-name, value}`,
  `update-sys-setting {code, value}`, `get-sys-setting`, `list-sys-settings`** all work
  (verified). The CLI `set-syssetting` is the same write.
- **`get-email-template` fails on 8.2.3** (HTML answer); `list-printables` works but the
  environment may simply have none.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [add-data-binding-row](../reference/add-data-binding-row.md) | Add or replace a row in an existing package data binding |
| [call-service](../reference/call-service.md) | Call a Creatio service endpoint |
| [create-data-binding](../reference/create-data-binding.md) | Create or regenerate a package data binding from a runtime schema |
| [create-data-binding-db](../reference/create-data-binding-db.md) | Creates a DB-first package data binding by persisting row data directly to the remote Creatio database |
| [dataservice](../reference/dataservice.md) | Send a Creatio DataService request |
| [download-sys-setting-file](../reference/download-sys-setting-file.md) | Save the exact bytes of a **Binary** system setting into a caller-named file |
| [execute-dataservice-batch](../reference/execute-dataservice-batch.md) | Write 1–100 explicit records in one native DataService BatchQuery request |
| [execute-sql-script](../reference/execute-sql-script.md) | Execute SQL script on a web application |
| [install-dbhub](../reference/install-dbhub.md) | Install, adopt, or repair a local dbHub HTTP MCP server |
| [mock-data](../reference/mock-data.md) | generates mock data for unit tests from Creatio OData models |
| [read-data-binding-db](../reference/read-data-binding-db.md) | report which columns a DB-first data binding actually ships |
| [remove-data-binding-row](../reference/remove-data-binding-row.md) | Remove a row from an existing package data binding |
| [remove-data-binding-row-db](../reference/remove-data-binding-row-db.md) | Removes a row from a DB-first package data binding |
| [set-feature](../reference/set-feature.md) | Set feature state |
| [set-file-content-storage-connection-string](../reference/set-file-content-storage-connection-string.md) | Set the connection string of a file content storage |
| [set-syssetting](../reference/set-syssetting.md) | Get or set a system setting value |
| [sync-dbhub](../reference/sync-dbhub.md) | Reconcile clio-owned dbHub sources with local Creatio environments |
| [upload-file](../reference/upload-file.md) | upload a local file into a file entity, attach it to a record and print the file id |
| [upload-image](../reference/upload-image.md) | upload a local image to an environment and print its image id |
| [upsert-data-binding-row-db](../reference/upsert-data-binding-row-db.md) | Upserts a single row in a DB-first package data binding |

<!-- commands:end -->
