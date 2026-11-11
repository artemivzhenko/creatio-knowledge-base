---
description: Creatio data bindings (Data/<Name>/ - rows of a table the package installs - lookup values, system settings and their values, folders, demo records) of 8.x as package files - read a binding (bound table, columns with key and force-update flags, rows with lookup display values and per-culture texts), validate it, create one for an object of the workspace, set one value, add or remove rows.
---

# Data binding tools

Scripts that read and change a package's **data bindings**: the rows of one table that the
platform writes while it installs the package. Pure Python standard library.

| File | What it does |
| --- | --- |
| `data.py` | CLI (the commands are listed under Commands) |
| `../creatio_schemas/data/binding.py` | `DataBinding` (and `JsonFile`): the library the CLI uses |
| `tests/test_data_tools.py` | checks on real bindings with generic names: a lookup with two cultures, a system setting and its value |

```bash
python data.py new     UsrPkg UsrOrderStatus --table UsrOrderStatus --columns Name,Description --cultures en-US,ru-RU
python data.py add-row UsrPkg UsrOrderStatus Name=New                 # prints the key (a new Id)
python data.py set     UsrPkg UsrOrderStatus <key> Name "Новый" --culture ru-RU
python data.py rows    UsrPkg UsrOrderStatus --culture ru-RU
clio push-pkg UsrPkg -e dev                                           # clear SysSchema.IsChanged first
```

## Commands

<!-- commands:start -->
```
python data.py inspect    <package> <Binding>
python data.py validate   <package> <Binding>
python data.py rows       <package> <Binding> [--limit 20] [--culture en-US]
python data.py new        <package> <Binding> --table UsrOrderStatus [--key Id] [--columns Name,Description]
                          [--cultures en-US,ru-RU] [--rows rows.json]
python data.py set        <package> <Binding> <key> <Column> <value> [--culture ru-RU]
python data.py add-row    <package> <Binding> Column=value ...           (prints the new row's key)
python data.py remove-row <package> <Binding> <key>
python data.py duplicates <Object> <Column> -e <env> | --project <project.json>
                          [--normalize trim,lower,digits] [--lookup] [--where "<OData filter>"] [--limit 40] [--json]
```

| command | what it does |
| --- | --- |
| `inspect` | bound table, row count, columns, problems |
| `validate` | problems; exit code 1 on errors |
| `rows` | the rows, one line each, key first |
| `new` | a binding of an object of the workspace |
| `set` | one value of one row |
| `add-row` | a new row |
| `remove-row` | drop a row and its translations |
| `duplicates` | groups of records sharing a value on the environment; exit 1 when any |
<!-- commands:end -->

## How it is stored

```
Data/<Name>/descriptor.json             {"Descriptor": {UId, Name, ModifiedOnUtc, InstallType, Schema {UId, Name},
                                         Columns [{ColumnUId, IsForceUpdate, IsKey, ColumnName, DataTypeValueUId}]}}
Data/<Name>/data.json                   {"PackageData": [{"Row": [{SchemaColumnUId, Value[, DisplayValue]}]}]}
Data/<Name>/filter.json                 the designer's filter of the bound records; empty in 308 of 373, else one line of JSON
Data/<Name>/Localization/data.<c>.json  the localisable columns per culture: [{SchemaColumnUId, ColumnName, Value}],
                                        the key columns included
```

- A row is matched on install by its **key columns** (`IsKey`; `Id` in 370 of 373 bindings, two
  columns in 3). `IsForceUpdate` makes the install overwrite a column of an existing row.
- `"null"` (a string) is a null value. Lookup cells (`Lookup`, `ImageLookup`) carry the record's
  UId in `Value` and its caption in `DisplayValue`, which only the designer reads.
- A localisable column (`Name`, `Description` of a lookup) is in `Localization/` and never in
  `data.json`; a binding without a `Localization` folder keeps even a localisable `Name` in
  `data.json` (seen for `SysSettings` and `CaseStatus`). Every culture file has one row per row of `data.json`.
- The base columns (`Id`, `Name`, `Description`, `CreatedOn` ...) have fixed UIds everywhere;
  `create` takes them, the types and the localisable flag from the object
  (`EntitySchema.columns()`, BaseEntity / BaseLookup from `entity/assets`).
- `InstallType` 0 in 366 bindings, 3 in 7 (not identified).
- The files differ in style: BOM or not, two spaces, four or tabs, a final newline or not; `/` is
  escaped only inside `\/Date(ms+zone)\/` literals.

## What the tools write

- An unchanged file is written back as it was read; a changed one is dumped in its own indent,
  newline and BOM, dates re-escaped. A re-dump reproduces 1316 of 1328 real data and
  localisation files exactly; the rest are hand-indented files and `0.00` literals (written `0.0`).
- `filter.json` is never rewritten; `new` writes it empty.
- `new`: descriptor with the key and named columns, `data.json`, empty `filter.json`, a
  `Localization` file per culture when a localisable column is bound - BOM, CRLF, two spaces, as
  the 8.x designer writes them. Only objects of the workspace can be bound; for a platform table
  (`SysSettings`) copy an existing binding.
- `set` converts the text to the column's type (Boolean, Integer, Float / Money); a lookup takes a
  UId or `null` and its stale `DisplayValue` is cleared. `add-row` writes every localisable
  column to every culture (empty when not given) and a new `Id` when the key is `Id`.
  `remove-row` drops the row from every culture too.

## Duplicates on an environment

`data.py duplicates <Object> <Column> -e <env> | --project <project.json>` answers "how many
duplicates are there already" before a de-duplication task is planned: the records are read over
OData (`Id` and the column, 500 a page, `--where` narrows them), grouped by the normalised value
(`--normalize trim,lower,digits`; `digits` keeps `0-9` only, for phones), and every group of two or
more is one line - `"<value>"  N records  ids: ...` - followed by the count of groups and of records
in them; exit 1 when there are any, `--json` for the tester's evidence. A lookup column needs
`--lookup`: the `Name` of the referenced record is grouped (`$expand`), and a record without one
groups under the empty value. Nothing is written; the environment is the one of `creatio_schemas/environment.py`.

## Verified

All 373 bindings found locally (8 workspaces) round-trip byte for byte through `DataBinding`,
and `validate` reports nothing on them. Not yet pushed to an environment.

## Checks

- a value for a column the descriptor does not list;
- a lookup value that is not a UId (or `null`);
- duplicate keys;
- a localisation row whose key is not in `data.json`;
- warning: no key column.

```bash
python tests/test_data_tools.py
```
