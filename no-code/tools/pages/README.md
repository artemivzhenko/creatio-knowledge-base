---
description: Creatio Freedom UI pages of 8.x as package files - put a field of any column type (text, number, checkbox, date, time, date-time, lookup, rich text, phone, email, web) or a grid of another object on a form page by editing the page body's JSON sections; push installs it; the UI test utility's analyse shows what rendered.
---

# Page tools

Scripts that change a **Freedom UI page** stored in a package: add the fields of the page's
object, add a grid of another object, remove an element. Pure Python standard library.

| File | What it does |
| --- | --- |
| `pages.py` | CLI: inspect, add-field, add-grid, remove, validate |
| [`../creatio_schemas/page/`](../creatio_schemas/README.md) | the library (`PageSchema`, `CONTROL_OF`) |
| `tests/` | `python tests/test_pages_tools.py` - round trip and build checks on real 8.2.3 pages of both body forms |

Verified on Creatio 8.2.3 (the test environment): the 17 columns of `UsrOrder` (every type below) and a grid
were placed on `UsrOrder_FormPage` with these scripts only, `clio push-pkg` installed the page,
and the UI test utility's `analyse` found all 18 controls with the expected element types
(Text, Integer, Decimal, Boolean, Date, Time, DateTime, Lookup, RichText, Phone, Email, Link,
DataGrid). Two pages read from the package render back byte-for-byte.

## The loop

```bash
python pages.py inspect   UsrPkg UsrOrder_FormPage
python pages.py add-field UsrPkg UsrOrder_FormPage UsrAmount --dry-run          # the diff, nothing written
python pages.py add-field UsrPkg UsrOrder_FormPage UsrAmount                    # profile column, next free row
python pages.py add-field UsrPkg UsrOrder_FormPage UsrNotes --parent GeneralInfoTabContainer
python pages.py add-grid  UsrPkg UsrOrder_FormPage UsrItems --entity UsrOrderItem --columns UsrName,UsrQty
clio execute-sql-script -e dev -s 'update "SysSchema" set "IsChanged"=false'   # or the push skips the page
clio push-pkg UsrPkg -e dev
creatio-tests analyse "/0/Shell/#Card/UsrOrder_FormPage/edit/<id>" --name UsrOrderForm --list
```

`<package>` is the package folder (`packages/UsrPkg` in a clio workspace); the page's object
and the grid's object are read from the workspace, so an unknown column is refused before
anything is written.

## What a field is

One `insert` in `viewConfigDiff` (`type`, `label: "$Resources.Strings.<Column>"`, `control:
"$<Column>"`, `labelPosition: "auto"`, `layoutConfig`) and one attribute `<Column>:
{modelConfig: {path: "PDS.<Column>"}}` - exactly the designer's output. The control follows the
column type (`CONTROL_OF`):

| Column type | Control | Extra |
| --- | --- | --- |
| ShortText, MediumText, LongText, MaxSizeText | `crt.Input` | |
| Integer, Float*, Money | `crt.NumberInput` | |
| Boolean | `crt.Checkbox` | |
| Date / DateTime / Time | `crt.DateTimePicker` | `pickerType` date / datetime / time |
| Lookup | `crt.ComboBox` | |
| RichText | `crt.RichTextEditor` | |
| PhoneText / EmailText / WebText | `crt.PhoneInput` / `crt.EmailInput` / `crt.WebInput` | |

Field captions come from the column captions: **no resource strings are written**, the page's
resources keep only its own `Caption`.

A grid is an `insert` of `crt.DataGrid` plus a collection attribute (`isCollection`, the
`<Name>DS_<Column>` sub-attributes) and a `crt.EntityDataSource` of scope `viewElement`; the
grid is unfiltered (every record of the object). Column captions are read from the object's
resources.

## Two body forms (verified)

A page the designer saved has `viewModelConfig` and `modelConfig` objects; a page clio
created from a template has `viewModelConfigDiff` and `modelConfigDiff` arrays of `merge`
operations (`path: ["attributes"]`, `path: ["dataSources"]`). The tools write into whichever
the page has and keep its indentation (tabs for the designer, two spaces for clio). Handlers
and anything else outside the JSON sections are kept as text.

## Traps

- **A page saved in the designer is "modified locally"** and `push-pkg` skips it with a
  warning while reporting success. Clear `SysSchema.IsChanged` (and `IsLocked`) before the
  push - see the clio-packages skill.
- The containers a field can go into are in the template, not in the page file:
  `SideAreaProfileContainer` (the profile column) and `GeneralInfoTabContainer` (the first
  tab) for `PageWithTabsFreedomTemplate`; `clio get-page` writes the merged bundle when
  another one is needed.
- Rows are not checked against the parent's grid: a field placed on a row another element
  spans is simply rendered after it.

## Not covered

Tab containers, expansion panels and new containers; moving or resizing an element; the
list page; handlers.
