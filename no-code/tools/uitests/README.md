---
description: The UI test utility (automatic-creatio-tests) for an agent - write, validate and run .act test cases of Creatio Freedom UI pages and process cases of the backend tier (start, check-result, check-record) without opening that repository; where it lives, build, the commands and MCP tools, the page and process files, the DSL in one table, the recipe that turns an acceptance criterion into .act lines with a worked example, and the Creatio traps that break cases.
---

# UI and process test cases (.act)

`automatic-creatio-tests` runs **cases**: `.act` files in a small DSL, one command per line,
validated in full before a browser opens. A UI case drives a Freedom UI page; a process case
starts a business process and checks its result and records over OData, with no browser. This
page is enough to write, validate and run both; the full language is the framework's
`docs/dsl.md` (the `creatio-tests` MCP tool `dsl()` returns it).

## Where and how to run

The clone is `project.json` -> `paths.testFramework`. Its `Configuration/creatio.env.config.json`
(gitignored: it holds a password) names the instance and the users a case may `use`.

```powershell
cd <paths.testFramework>
dotnet build                                                   # once; the exe lands in src/CreatioAutoTests.Cli/bin/Debug/net8.0/
$t = "src/CreatioAutoTests.Cli/bin/Debug/net8.0/creatio-tests.exe"   # or: dotnet run --project src/CreatioAutoTests.Cli --
& $t --validate-only --filter 012                              # parse and check, no browser, no instance
& $t --filter 012                                              # run against the instance; the report goes to Reports/
& $t schemas Shipment                                          # find a page's schema name and the address that opens it
& $t analyse "/0/Shell/#Card/UsrShipment_FormPage/edit/<id>" --name UsrShipmentForm --list   # describe a live page
```

`--filter` matches part of the case file name; `--root <dir>` runs against another folder
holding `Configuration/` and `Cases/`. Exit code 0 passed, 1 a case failed, 2 the run could not
start. The `creatio-tests` MCP server wraps the same: `overview`, `dsl`, `cases`, `case`,
`page_config`, `process_config`, `validate(filter)`, `run(filter)`, `analyse(path, name)`,
`schemas(text)`, `last_report`. It reads and runs only - you write the files.

## Files

| Path | What |
| --- | --- |
| `Cases/*.act` | UI cases. `.act` is gitignored (it names an environment's records); bundled examples are `*.act.exp`, skipped by the runner - copy one to `.act` to run it |
| `ProcessCases/*.act` | process cases (backend tier), run after the UI cases |
| `Analysis/*.act` | scripts that only `analyse` pages; run with `--analyse` / `--analyse-only` |
| `Configuration/pages/*.json` | one file per page: `name` (what `open` takes), `url`, `type`, `elements` (`code`, `label`, `type`, `pinned` ...). Written by `analyse`; `pinned: true` keeps a hand edit on re-analysis |
| `Configuration/processes/*.json` | one file per process a case may `start`: `name`, `parameters` (`code`, `type`, `direction` in / out / variable). `proc.py test-config <pkg> <Process> --out <file>` writes it from the package |
| `Configuration/static.values.json`, `objects.config.json` | named values for `set`, and the objects `create` knows |
| `Reports/run-*.txt` | one report per run (`last_report()`) |

## The DSL in one table

The first line is `use <user>`; `#` starts a comment; double quotes make a literal value.

| Command | Example |
| --- | --- |
| `use <user>` | `use Supervisor` |
| `open <page> [for <recordId>]` | `open UsrShipmentForm for 0f3c2a8e-5d41-4b7a-9c26-1e8d7b4a6f90` |
| `click <code>` (buttons, tabs) | `click GeneralInfoTab` |
| `set <code> "value"` / `set <code> <staticValue>` | `set UsrStatus "Shipped"` |
| `clear <code>` | `clear UsrCarrier` |
| `check <code> [not] exists` (also compares the caption with `label`) | `check UsrLabel exists` |
| `check <code> is [not] required / readonly / editable` | `check UsrLabel is readonly` |
| `check <code> columns` (grid columns against the page file) | `check UsrItemList columns` |
| `check-value <code> eq / ne / gt / ge / lt / le / contains / startswith / endswith <value>` | `check-value UsrLabel startswith "PARCEL-"` |
| `add-record <grid> set Col=Value;Col=Value` | `add-record UsrItemList set Name=Box;Quantity=2` |
| `goto <lookup>` | `goto UsrAccount` |
| `create <object>` | `create UsrShipment` |
| `wait <n> second / minute` | `wait 2 second` |
| `end` | `end` |

Values: dates `yyyy-MM-dd[THH:mm[:ss]]`, booleans `true` / `false`, invariant numbers. Element
types (`Text`, `Lookup`, `Boolean`, `Date`, `Tab`, `ToggleTab`, `DataGrid`, `Button`, `CasesBar` ...)
decide which commands an element accepts; a mismatch fails in validation.

## Backend tier

Process cases (`ProcessCases/`), no browser:

```act
use Supervisor
start UsrShipmentLabel_Process with ShipmentId=0f3c2a8e-5d41-4b7a-9c26-1e8d7b4a6f90
check-result Label eq "PARCEL-0007"
check-record UsrShipment Id=0f3c2a8e-5d41-4b7a-9c26-1e8d7b4a6f90;UsrLabel=PARCEL-0007 exists
```

- `start <process> [with P=V;P=V]` - the process must have a file in `Configuration/processes`;
  values are type-checked, an output parameter cannot be passed in.
- `check-result <parameter> <op> <value>` - an output or variable of the last started process
  (a lookup result is its id).
- `check-record <object> Col=Val;Col=Val [not] exists` - an OData filter; a lookup column given a
  GUID reads `<Column>Id`. Existence only.
- A case may write: `insert <object> as <alias> set Col=Val;...` (the Id becomes `$alias`),
  `update <object> $alias set ...`, `delete <object> $alias`, `delete-record <object> <filter>`
  (refuses more than 20 matches); `check-record ... has <column> <op> <value>`, `check-count
  <object> <filter> <op> <n>`, `check-distinct`; `remember <code> as $x` and `remember-record
  <object> <filter> as $x` bind variables, `$x+N` only as the value `check-value` compares with.
  Every inserted record is deleted when the case ends unless the `insert` says `keep`. The header
  `# writes` makes the case stop at its first failure and refuses an inserted alias that is neither
  deleted nor kept; `# ac: AC-02` names the criterion, and a run with `--task-folder <dir>` (MCP
  `run(..., task_folder, task)`) writes `<dir>/evidence/AC-02-report-N.txt` and a draft report row.
  `check console no errors [except "<regex>"]` fails on browser errors of the pages opened so far.
  The full grammar is `docs/dsl.md`, "Cases that write"; the examples are
  `ProcessCases/order-writes.act.exp` and `Cases/order-page-writes.act.exp`.

## A case from an acceptance criterion

A `ui` criterion of `plan.md` reads "open the page, do X, expect Y". One case per criterion,
named `<task>-<AC>-<slug>.act` (`012-AC-06-label-readonly-when-shipped.act`), first line a
`#` comment quoting the criterion.

1. **Page file.** `page_config(<Page>)`; when there is none, `schemas(<text>)` then
   `analyse(<path>, <Page>)`. Every code the case uses must be in it.
2. **Data.** `open <Page> for <id>` of a record that carries the task's test prefix (made by an
   earlier criterion, a process case or the task's data), or `create <object>` for a new one.
3. **Reach the control.** `click <Tab>` when it is not on the first tab - which tab opens is not
   guaranteed.
4. **Precondition** when the expectation is a change: `check <code> is not readonly` before,
   `check <code> is readonly` after; otherwise the case passes on a page that was always that way.
5. **Action.** `set` / `clear` / `add-record`, then `click SaveButton` when the criterion saves.
6. **Expectation.** `check` for presence and state, `check-value` for values, one line per
   expected fact.
7. `end`, then `validate(filter)` until clean, then `run(filter)`; keep the report as evidence.

Worked example: AC-06 of the loop's `templates/plan.md` - "open the shipment page, set the status
to Shipped, save -> the label field is read-only".

```jsonc
// Configuration/pages/UsrShipmentForm.json - analyse writes it; SaveButton is added by hand (pinned):
// a clean page renders Close, not Save, so analyse never sees it
{
  "name": "UsrShipmentForm",
  "url": "/0/Shell/#Card/UsrShipment_FormPage",
  "type": "FreedomUI",
  "elements": [
    { "code": "GeneralInfoTab", "label": "General information", "type": "Tab" },
    { "code": "UsrStatus", "label": "Status", "type": "Lookup" },
    { "code": "UsrLabel", "label": "Label", "type": "Text" },
    { "code": "SaveButton", "label": "Save", "type": "Button", "isSave": true, "pinned": true },
    { "code": "CloseButton", "label": "Close", "type": "Button" }
  ]
}
```

```act
# 012 AC-06: open the shipment page, set the status to Shipped, save -> the label field is read-only
use Supervisor
open UsrShipmentForm for 0f3c2a8e-5d41-4b7a-9c26-1e8d7b4a6f90

click GeneralInfoTab
check UsrLabel is not readonly
set UsrStatus "Shipped"
click SaveButton
check UsrLabel is readonly
check-value UsrStatus eq "Shipped"
end
```

`creatio-tests --validate-only --filter 012` on these two files: `ok 012-AC-06-label-readonly-when-shipped (9 commands)`.
The record id is the shipment the backend criteria (AC-03) left behind.

## Traps

- **A control hidden by a business rule is not in the DOM.** The page file is a snapshot of the
  record `analyse` opened: a control a rule hides on another record passes validation and fails
  at run time with "not found". Open a record in the state the criterion describes, and assert
  hiding with `check <code> not exists`.
- **Save replaces Close on a dirty page.** `SaveButton` and `CancelButton` exist only after
  something changed; `CloseButton` only before. Add Save to the page file by hand (`pinned`).
- **A lookup takes the text of an offered option**, not an id (`set UsrStatus "Shipped"`, and the
  same in `add-record` cells); the value must be offered to that user.
- **The interface language matters.** Captions (`check ... exists` compares them), option texts
  and the date pickers' icon labels follow the user's language; the framework is verified on an
  English interface. Keep the case's user and the page file in one language.
- **`wait` is a smell.** `open` already waits until the form stops growing, and every element
  command waits up to `elementTimeoutMs` (`run.config.json`) for its control; a fixed wait hides a
  race and slows every run. Assert the state you are waiting for instead.
