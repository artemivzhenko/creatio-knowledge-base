---
description: Creatio author shortcut - one command builds the set an author task starts with as package files - an object with its columns, lookup objects with a data binding of their rows, the lookup columns, an empty-template form page with every column as a field and a list page - each through its toolkit (objects, data, pages) and validated, in one dry-run diff first; existing schemas are refused.
---

# Scaffold an entity: object, lookups with seed rows, form and list pages in one command

One command for the start of most author tasks, on top of the toolkits: it adds nothing they do
not do, it only chains them and checks the result. Pure Python standard library.

| File | What it does |
| --- | --- |
| `scaffold.py` | CLI: `entity` |
| `tests/test_scaffold_tools.py` | checks on temp copies of the pages fixture |

```bash
python scaffold.py entity UsrPkg UsrShipment --caption "Shipment" \
    --column "UsrNumber:Integer:required" --column "UsrNotes:MediumText" --column "UsrContact:Lookup:Contact" \
    --lookup "UsrStatus:UsrShipmentStatus:New,In progress,Done" --pages --dry-run
```

## The spec

| Option | Grammar | Makes |
| --- | --- | --- |
| `<Object>` `--caption` | the object's name and caption | `Schemas/<Object>/` (BaseEntity) with `objects.py`'s writer |
| `--column` (repeatable) | `Name:Type[:flag,flag]`; a lookup `Name:Lookup:<Object>[:flag,..]` | a column; types and flags as `objects.py column add` (`required`, `indexed`, `multiline` ...) |
| `--lookup` (repeatable) | `Column:LookupObject[:Row,Row,..]` | the lookup object (BaseLookup) when the workspace lacks it, `Data/<LookupObject>` with one row per name (new Ids, `Name` in every culture) when rows are given, and the lookup column |
| `--pages` | - | `<Object>_FormPage` (PageWithTabsFreedomTemplate, every column a field in the profile container) and `<Object>_ListPage` (ListPageV2Template) |
| `--cultures` | `en-US,ru-RU` | the cultures of the captions and the binding; default the package's |
| `--dry-run` | - | the unified diff of every file, nothing written |

Captions are the names without the `Usr` (or a lower-case) prefix, split at capitals:
`UsrShipDate` -> "Ship date", `UsrShipmentStatus` -> "Shipment status"; the form page is
"<Caption> form page", the list page "<Caption>".

## How it is stored

Nothing of its own: the files are those of the objects, data and pages toolkits (see their
READMEs). The two pages are what clio's `create-page` writes for an empty page of those templates
(`creatio_schemas/page/assets/new_FormPage.*`, `new_ListPage.*`, taken from two such pages; the
test proves the form page byte for byte against one).

## What the tools write

The whole set is built in a scratch copy of the package (its neighbours copied as descriptors and
metadata, so lookups resolve); each item must pass its own toolkit's `validate`, or nothing is
written. Then `--dry-run` prints the diff, otherwise the new files are copied into the package. An
object, page or binding that exists is refused before anything is built - never overwritten. A
lookup object of the workspace is reused; with rows and no binding of its own yet, it gets one.

Not made: the list page's columns (the empty template's list), the section (the workplace and
`SysModule*` bindings), the lookup's registration in the Lookups section, business rules.

## Verified

On temp copies of the pages fixture: the set of the example above is 29 files; every item passes
its validator and round-trips byte for byte; `describe_package` lists the two objects and two pages
with their kinds; the form page's page file has the expected element types (Integer, Text, Lookup).
Not pushed to an environment yet.

## Checks

```bash
python tests/test_scaffold_tools.py
```
