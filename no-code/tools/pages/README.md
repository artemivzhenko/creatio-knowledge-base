---
description: Creatio Freedom UI pages of 8.x as package files - put a field of any column type (text, number, checkbox, date, time, date-time, lookup, rich text, phone, email, web) or a grid of another object on a form page by editing the page body's JSON sections; push installs it; the UI test utility's analyse shows what rendered.
---

# Page tools

Scripts that change a **Freedom UI page** stored in a package: add the fields of the page's
object, add a grid of another object, remove an element. Pure Python standard library.

| File | What it does |
| --- | --- |
| `pages.py` | CLI (the commands are listed under Commands) |
| [`../creatio_schemas/page/`](../creatio_schemas/README.md) | the library (`PageSchema`, `CONTROL_OF`) |
| `tests/` | `python tests/test_pages_tools.py` - round trip and build checks on real 8.2.3 pages of both body forms |

Verified on Creatio 8.2.3 (the test environment): the 17 columns of `UsrOrder` (every type below) and a grid
were placed on `UsrOrder_FormPage` with these scripts only, `clio push-pkg` installed the page,
and the UI test utility's `analyse` found all 18 controls with the expected element types
(Text, Integer, Decimal, Boolean, Date, Time, DateTime, Lookup, RichText, Phone, Email, Link,
DataGrid). Two pages read from the package render back byte-for-byte.

## Commands

<!-- commands:start -->
```
python pages.py inspect   <package> <Page>
python pages.py add-field <package> <Page> <Column> [--parent SideAreaProfileContainer] [--row N] [--col N] [--span N]
python pages.py add-grid  <package> <Page> <Name> --entity UsrOrder --columns UsrName,UsrAmount [--parent GeneralInfoTabContainer] [--rows 6] [--editable]
python pages.py remove    <package> <Page> <Element>
python pages.py validate  <package> <Page>
python pages.py from-schema <package> <Page> [--name UsrOrderForm] [--out Configuration/pages/UsrOrderForm.json] [--compare <page file>]
```

| command | what it does |
| --- | --- |
| `inspect` | elements, attributes, data sources and problems |
| `validate` | problems; exit code 1 on errors |
| `add-field` | a field bound to a column of the page's object |
| `add-grid` | a grid listing another object's records |
| `remove` | drop an element with its attribute and data source |
| `from-schema` | the UI test utility's page file, from the page schema |
<!-- commands:end -->

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

## The page file of the UI test utility

`from-schema` writes `Configuration/pages/<name>.json` of `automatic-creatio-tests` from the page
schema - no browser, no record, no environment. Describe a page from the package first; run
`analyse` when the page is not in a package or its parent's elements matter.

```bash
python pages.py from-schema UsrPkg UsrOrder_FormPage --out <testFramework>/Configuration/pages/UsrOrderForm.json
python pages.py from-schema UsrPkg UsrOrder_FormPage --compare <testFramework>/Configuration/pages/UsrOrderForm.json
```

- `code` is the element's `name`: the utility addresses an element by `element-name`, which is that
  name (all 11 own controls of the designer-made test page, and all 18 of the tool-made order page,
  matched what `analyse` wrote).
- `type` from the component (`creatio_schemas/page/catalog.py`): `crt.Input` Text, `crt.NumberInput`
  Integer for an Integer column else Decimal, `crt.DateTimePicker` by `pickerType` (date, time,
  datetime; else the column's type), `crt.Checkbox` Boolean, `crt.ComboBox` Lookup, `crt.RichTextEditor`,
  `crt.EmailInput`, `crt.PhoneInput`, `crt.WebInput` Link, `crt.Button`, `crt.TabContainer` Tab,
  `crt.DataGrid` with its column captions, `crt.EntityStageProgressBar` CasesBar,
  `crt.ButtonToggleGroup` ToggleTab. Containers, labels, widgets, menus are listed at the end as
  `# not written (<type>): ...`.
- `label` as the page shows it: a literal; `#ResourceString(X)#` = the page string
  `LocalizableStrings.X.Value`; `$Resources.Strings.X` = that string, else the caption of the column
  the attribute `X` (or `<DataSource>_<Column>`) reads. A caption the workspace cannot resolve (a
  platform object's column) is written empty and named in `# label unknown`: fix it by hand or with
  `analyse` - `check <code> exists` compares it.
- A page's own schema does not list its template's elements. For `PageWithTabsFreedomTemplate` the
  ones `analyse` found are added (`CloseButton`, `BackButton`, `SetRecordRightsButton`,
  `AttachmentAddButton`, `AttachmentRefreshButton`, `GeneralInfoTab`, `CardButtonToggleGroup`),
  minus those the page removes or hides; for any other parent the output says the parent's elements
  are unknown. Elements the page hides with `visible: false` are left out and named; elements a
  business rule hides are written (they exist on some records).
- The file is written as `analyse` writes it (two spaces, LF, elements by type then code): for
  both test pages the output is byte-identical to `analyse`'s file (`tests/fixtures/expected/`).
  `--compare` lists elements only in the schema, only in the file, and type, label, column and tab
  differences; exit code 1 when there are any.

Read from all 244 local Freedom UI pages without an error: 2451 elements written, 593 labels left
empty for an object outside the workspace, 87 elements hidden by their page.

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
list page's columns (`PageSchema.create(..., "list")` writes the empty list page clio's `create-page`
writes; `PageSchema.create(..., "form")` the empty form page - both byte for byte, used by
`tools/scaffold`); handlers.
