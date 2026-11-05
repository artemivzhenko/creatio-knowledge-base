---
name: clio-schemas
description: Create and change Creatio schemas with clio without the designer - entity schemas (objects) and their columns, lookups, C# source schemas, client (JS) schemas, SQL script schemas, export and import. Use for "add a column", "create an object", "create a lookup", "read the schema".
---

# clio: schemas

Verified on clio 8.1.0.145, Creatio 8.2.3. Command pages: [reference/](../reference/).

Schema commands save through the platform's designer services, exactly like pressing
"Save" in the object designer: the result lands in the environment's database and in the
package you name, not in your local files. Pull the package afterwards
([clio-packages](../clio-packages/SKILL.md)).

## Objects and columns

```bash
clio get-entity-schema-properties <Entity> -e dev          # merged view, all columns
clio get-entity-schema-column-properties <Entity> <Column> -e dev
clio find-entity-schema <pattern> -e dev
clio create-lookup UsrOrderStatus -e dev ...               # BaseLookup with Name/Description
clio create-entity-schema UsrOrder -e dev ...              # with initial columns
clio modify-entity-schema-column UsrOrder --action add --column-name UsrAmount --type Currency2 -e dev
```

Supported column types (clio names): `Guid Text ShortText MediumText LongText MaxSizeText
Text50 Text250 Text500 TextUnlimited RichText PhoneNumber WebLink Email SecureText Integer
Float Decimal0-4/8 Currency0-3 Boolean DateTime Lookup Binary Image ImageLookup File Color`.
`Money` = `Currency2`; `Date` and `Time` are **aliases of DateTime**.

Verified on 8.2.3: ShortText, Boolean (with a `Const` default that a created row received),
Currency2, Lookup to a stock object and to a new lookup, Integer, DateTime - all created
physical columns, were visible through OData and landed in the package.

## Traps (verified)

- **Decimal0 / Float0 / Money0 / Money1 / Money3 do not exist on Creatio 8.2.x.** The add
  fails with the unhelpful `Item with name "47" not found` (the type id). Use Decimal2 /
  Currency2 there.
- **A date-only column cannot be created through clio.** `type: Date` silently stores
  DateTime; the designer shows "Date/Time". Create date-only columns in the designer, or
  put a date-only control on the page.
- **Captions go to en-US only.** `title-localizations` with just `en-US` leaves the other
  cultures inheriting the parent's caption (an object showed as "Base object" for a uk-UA
  profile). Pass every culture the environment's users have.
- **Reading a page name through `get-schema` fails**: `get-schema` is for C# source
  schemas (`SourceCodeSchemaManager`); client schemas are `get-client-unit-schema`, pages
  are `get-page`.
- **`create-entity-schema` returns before the OData controller exists**; a 404 on
  `/0/odata/<Entity>` for 1-2 minutes is expected.
- **`sync-schemas` (batch create/update) exists only on clio's MCP**, not as a CLI verb.

## Commands

<!-- commands:start -->

| Command | Purpose |
| --- | --- |
| [add-item](../reference/add-item.md) | Add package item to project based on template |
| [add-schema](../reference/add-schema.md) | Add schema to package |
| [convert](../reference/convert.md) | Convert packages to project structure |
| [create-client-unit-schema](../reference/create-client-unit-schema.md) | Create a new JavaScript (ClientUnit) schema on a remote Creatio environment |
| [create-entity-schema](../reference/create-entity-schema.md) | Create an entity schema in a remote Creatio package |
| [create-lookup](../reference/create-lookup.md) | Create a lookup entity schema in a remote Creatio package |
| [create-schema](../reference/create-schema.md) | Create a new C# source-code schema on a remote Creatio environment |
| [create-sql-schema](../reference/create-sql-schema.md) | Creates an empty package SQL script on a remote Creatio environment using the native `SqlScriptSchemaDesignerService/... |
| [delete-schema](../reference/delete-schema.md) | delete a schema that belongs to the current workspace |
| [export-schema](../reference/export-schema.md) | Export a single schema from a Creatio environment into a reviewable bundle folder |
| [find-entity-schema](../reference/find-entity-schema.md) | Find entity schemas in a Creatio environment by name, substring pattern, or UId |
| [get-client-unit-schema](../reference/get-client-unit-schema.md) | Read body and metadata of a client unit (JavaScript) schema on a remote Creatio environment |
| [get-entity-connections](../reference/get-entity-connections.md) | Read an object's Connections (the ordered lookup columns shown by the Freedom UI Connections component) |
| [get-entity-schema-column-properties](../reference/get-entity-schema-column-properties.md) | Get column properties from a remote Creatio entity schema |
| [get-entity-schema-properties](../reference/get-entity-schema-properties.md) | Get properties from a remote Creatio entity schema |
| [get-schema](../reference/get-schema.md) | Read body and metadata of a C# source-code schema on a remote Creatio environment |
| [get-sql-schema](../reference/get-sql-schema.md) | Read body and metadata of a SQL script schema on a remote Creatio environment |
| [import-schema](../reference/import-schema.md) | Import a schema bundle produced by [`export-schema`](export-schema.md) into a package of a Creatio environment, creat... |
| [install-sql-schema](../reference/install-sql-schema.md) | Execute a SQL script schema on a remote Creatio environment |
| [list-entity-client-schemas](../reference/list-entity-client-schemas.md) | Resolve the Classic page-role graph (sections, edit pages, mini pages) of an entity |
| [merge-creatio-artifact](../reference/merge-creatio-artifact.md) | Semantically merge three versions of a supported Creatio artifact |
| [modify-entity-schema-column](../reference/modify-entity-schema-column.md) | Add, modify, or remove a column in a remote Creatio entity schema |
| [set-entity-schema-properties](../reference/set-entity-schema-properties.md) | Set schema-level properties on a remote Creatio entity schema |
| [sync-schemas](../reference/sync-schemas.md) | Executes a batch of schema operations in a single MCP call: create lookups, create entities, seed data, update entities |
| [update-client-unit-schema](../reference/update-client-unit-schema.md) | Update the raw body of a client unit schema |
| [update-entity-connections](../reference/update-entity-connections.md) | Set an object's Connections to a full ordered list of lookup columns (writes the EntityConnections add-on) |
| [update-entity-schema](../reference/update-entity-schema.md) | Apply batch column operations to a remote Creatio entity schema |
| [update-schema](../reference/update-schema.md) | Update the body of a C# source-code schema on a remote Creatio environment |
| [update-sql-schema](../reference/update-sql-schema.md) | Update the body of a SQL script schema on a remote Creatio environment |

<!-- commands:end -->
