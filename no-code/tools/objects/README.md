---
description: Creatio objects (entity schemas) of 8.x as package files - create objects, lookups and replacing objects of base objects (Contact, Account), change base (inherited) columns, add, change and remove columns (types, lookups, required, default, index, cascade, weak reference...), object flags (virtual, rights, change log, deactivation), captions in every culture; push applies the table; probe compares metadata with the database.
---

# Object tools

Scripts that create and change Creatio **objects** (entity schemas) as **package files**, the
route that avoids clio's object commands and their 8.2 traps (no date-only column, no
Decimal0, captions in en-US only). Pure Python standard library.

| File | What it does |
| --- | --- |
| `objects.py` | CLI: inspect, new (also `--replace`), base, column add/set/default/type/caption/remove, set (object flags), caption, display, validate, probe |
| [`../creatio_schemas/entity/`](../creatio_schemas/README.md) | the library (`EntitySchema`, flag catalog, parents and designer templates of 8.2.3, `database.check`) |
| `tests/` | `python tests/test_objects_tools.py` - round trip and edit checks on a real 8.2.3 export |

Verified on Creatio 8.2.3 (ti823): an object changed only with these scripts (virtual and DB-view
flags off, three columns added, a foreign key switched from weak to cascade) and a new object
plus a new lookup were pushed with `clio push-pkg`; the platform built the tables - columns,
indexes, foreign keys with the right delete rule, the `Sys<Object>Right` table, `RecordInactive`
- `probe` matched every item, a date-only column came back as Date through DataService, and a
pull returned the same bytes. All 344 objects of the real packages in the workspaces (8.1-10.0,
own and replacing) round-trip byte-for-byte.

## The loop

```bash
python objects.py inspect UsrPkg UsrOrder                       # flags, columns, problems
python objects.py column  UsrPkg UsrOrder add UsrAmount --type Money --caption Amount --dry-run
python objects.py column  UsrPkg UsrOrder add UsrAmount --type Money --caption Amount
python objects.py column  UsrPkg UsrOrder add UsrManager --type Lookup --ref Contact --caption Manager --on required
clio push-pkg UsrPkg -e dev                                      # the platform updates the table
python objects.py probe   UsrPkg UsrOrder --env dev              # metadata vs the table
```

New objects: `objects.py new UsrPkg UsrOrder --caption "Order"` (`--parent BaseLookup` for a
lookup with Name / Description). Then add columns and `display` the primary column.

## Replacing objects and base columns

A replacing object (your package's `Contact`, `Account`) is a diff against the **merged base**:
every copy of the object in the packages your package depends on, merged in the platform's order.
That base is not in the workspace, so fetch it once:

```bash
python objects.py base     UsrPkg Contact --env dev          # -> <workspace>/.creatio-bases/UsrPkg/Contact.json
python objects.py new      UsrPkg Contact --replace          # the replacing copy, as the designer writes it
python objects.py column   UsrPkg Contact set Phone --on indexed
python objects.py column   UsrPkg Contact type Zip MediumText
python objects.py column   UsrPkg Contact default DoNotUseSms True
python objects.py column   UsrPkg Contact caption Dear en-US="Salutation"
python objects.py column   UsrPkg Contact add UsrLoyalty --type Integer
clio push-pkg UsrPkg -e dev && python objects.py probe UsrPkg Contact --env dev
```

`base` calls the platform's own `tsp_GetSysSchemaParentsInPackageHierarchyByPackage` and merges
the copies farthest first (SchemaLevel, PackageLevel), copies on one level in the order the
function returns them - the same order the designer uses (its `EG1.BK8` names the events
process of the copy merged last; a sort by name or by `HierarchyLevel` gets it wrong). The
cache is valid until the platform or the packages below yours change; fetch again then. Every
command that touches an inherited column or an object flag says so when the base is missing.

What a base column takes, and how it is written:

| Change | Line | Allowed |
| --- | --- | --- |
| a flag (required, indexed, cascade ...) | `+ / = / - D2.["uid"].<key>` against the base value | yes |
| constant default | `= / + D2.["uid"].E12 {...}` | yes |
| caption | `Columns.<Name>.Caption` in the package's resources (en-US or any culture) | yes |
| type | `= D2.["uid"].S2 "<type>"` | only a text column growing: ShortText > MediumText > LongText > MaxSizeText |
| remove, rename, any other type change | - | refused: the column and its data belong to the base |

## How an object is stored

`Schemas/<Object>/metadata.json` is a **diff against the parent schema** - for an own object
the parent is `BaseEntity` or `BaseLookup`, for a replacing one the base object:

```
+ MetaData.Schema.D2 {column}                 a column this package adds (edited in place)
~ MetaData.Schema.D2 [uids]                   the column order
= MetaData.Schema.D2.["uid"].E6 false         an inherited column's property differs from the parent
+ MetaData.Schema.D10 true                    a key the parent does not have (IsDBView)
- MetaData.Schema.D1                          a parent key removed: BaseEntity is virtual, "- D1" makes a real table
```

So a change is written as `=`, `+` or `-` depending on the parent's value; the tools compute
the effective schema (parent + diff) and write the line the platform would. `BaseEntity` and
`BaseLookup` ship as assets (exported from 8.2.3); a parent that is an own object of the
workspace is read from it. With an unknown parent (a replacing `Contact`, say) the tools still
add, change and remove the columns this package adds; inherited columns and object flags need
the parent and are refused.

`properties.json` repeats some object flags (`IsVirtual`, `IsTrackChangesInDB`,
`AdministratedBy*`, `IsSSPAvailable`, `UseLiveEditing`); `set` keeps both in step and `validate`
reports a mismatch. Column captions are `Columns.<Name>.Caption` (en-US, as the designer writes);
the object caption goes to **every culture of the package** - a culture without it shows the
parent's caption ("Base object").

## Flags

| Column (`--on` / `--off`) | Key | Object (`set --on / --off`) | Key |
| --- | --- | --- | --- |
| required | E2 | virtual | D1 |
| indexed | E6 | db-view | D10 |
| simple-lookup | E20 | track-changes | D24 |
| weak-reference (no foreign key) | E8 | admin-operations / -columns / -records | D15 / D16 / D17 |
| cascade (ON DELETE CASCADE) | E9 | deny-rights | D26 |
| track-changes | E16 | deactivation (adds RecordInactive) | D32 |
| sensitive | E23 | ssp (portal) | D33 |
| multiline, localizable, masked, format-validated | E19, E21, E22, E25 | live-editing | D38 |
| copy-on-duplicate (on by default) | E5 | | |

A new lookup column is indexed and a simple list, as the designer makes it; `--off` either.
A constant default: `--default <value>` (booleans `True` / `False`).

## Traps (verified on 8.2.3)

- **"Required" and a constant default are application-level.** A required lookup stays
  nullable in the table, and a base Boolean whose default became True keeps `DEFAULT false` in
  the database; the platform applies both when it saves through the entity layer. A direct SQL
  insert does not see them.
- **The designer writes noise into a replacing object**: `- D2.["uid"].E16` followed by
  `+ D2.["uid"].E16 false` for every column, and edits of the events process (`EG1.BK4...`). The
  tools keep such lines and do not produce them; the platform accepts a replacing object
  without them.

- **A virtual or DB-view object keeps its table as it is.** The designer's "virtual" removes
  `- D1`, and then a push changes nothing in the database - no new indexes, no foreign key
  changes, no rights table. `validate` warns, `probe` says so.
- **A designer-saved object is "modified locally"** (`SysSchema.IsChanged` / `IsLocked`) and
  `push-pkg` skips it, like any designer-saved schema. Pull it, clear the two flags for that
  schema, then push the files.
- **Weak reference + cascade together** is contradictory (no foreign key, so nothing to
  cascade); `validate` warns.
- **Float0, Money0, Money1, Money3 exist only from 8.3**; `add` refuses them for an 8.2 schema.
  Date-only columns work (`--type Date`), unlike through clio.
- Removing a column or changing its type affects data in the table; the tools remove only
  columns this package added and never change a type.

## Not covered

Indexes over several columns (`D6`), system-value defaults (`FB1: 3`) and autonumbers
(`FB1: 4`) are kept when present but not built; inherited columns need the fetched base;
`probe` does not report an index the metadata no longer asks for (8.2.3 dropped it); `probe` reads
PostgreSQL only; the embedded events process (`EG1`) is passed through untouched.
