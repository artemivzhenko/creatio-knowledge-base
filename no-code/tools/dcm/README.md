---
description: Creatio DCM cases (dynamic case management) of 8.x as package files - read a case (object, stage column, filter, stages with their lookup records and colours, steps that start sub-processes, result conditions, allowed stage moves), create a case on an object's lookup column, add or remove stages and steps (sub-process parameter mappings, result conditions), connect stages; the describe layer answers stages, stage, steps, step, moves, filter.
---

# DCM case tools

Scripts that read and change DCM cases as **package files** (`Schemas/<Case>/metadata.json`,
`DcmSchemaManager`, `Resources/<Case>.Dcm/`). Pure Python standard library.

| File | What it does |
| --- | --- |
| `dcm.py` | CLI (the commands are listed under Commands) |
| `../creatio_schemas/dcm/schema.py` | `DcmSchema`: the library the CLI and the describe layer use |
| `tests/test_dcm_tools.py` | checks on a real case with generic names |

## Commands

<!-- commands:start -->
```
python dcm.py inspect      <package> <Case>
python dcm.py validate     <package> <Case>
python dcm.py new          <package> <Case> --caption "Order cases" --entity UsrOrder --stage-column UsrStatus
                           [--stage "New=<record uid>" --stage "Done=<record uid>" ...] [--cultures en-US,ru-RU]
python dcm.py add-stage    <package> <Case> --caption "On hold" --record <uid> [--name Stage7] [--color #FFAC07] [--parent Stage4]
python dcm.py remove-stage <package> <Case> <stage>
python dcm.py connect      <package> <Case> <from> <to> [--one-way]
python dcm.py disconnect   <package> <Case> <from> <to> [--one-way]
python dcm.py add-step     <package> <Case> --stage Stage2 --process UsrNotify_Process --caption "Notify"
                           [--name DcmElement5] [--map Request={Record:Id} ..] [--required] [--when "NextStage = Stage3 -> Stage3" ..]
python dcm.py remove-step  <package> <Case> <step>
python dcm.py set-caption  <package> <Case> <Caption|stage> <value>
python dcm.py enable       <package> <Case>
python dcm.py disable      <package> <Case>
```

| command | what it does |
| --- | --- |
| `inspect` | object, stage column, filter, stages with steps and conditions, moves |
| `validate` | problems; exit code 1 on errors |
| `new` | an empty case on an object's lookup column, stages optional |
| `add-stage` | a stage for a record of the stage column's lookup |
| `remove-stage` | drop a stage, its connections and captions |
| `add-step` | a step that starts a process of the workspace on a stage |
| `remove-step` | drop a step, its mappings and captions |
| `connect` | allow moving between two stages |
| `disconnect` | forbid moving between two stages |
| `set-caption` | the case caption (target Caption) or a stage caption |
| `enable` | set Enabled |
| `disable` | clear Enabled |
<!-- commands:end -->

## How a case is stored

- `EntitySchemaUId` and `StageColumnUId`: the object and its lookup column that holds the stage;
  `properties.json` repeats both.
- `Stages[]`: `A2` name (`StageN`), `Color`, `StageRecordId` (a record of the stage column's
  lookup), optional `ParentStageUId` (an *alternative* stage shown under its parent), `Elements[]`.
- A step (`DcmSchemaElement`) wraps a `ProcessFlowElement` of class `ProcessSchemaSubProcess`
  whose `CK4` is the process to start; `RequiredType` 1 = required; `Conditions` (a JSON string)
  moves the record to another stage by `nextStageId` when a result formula holds. Sub-process
  parameter mappings sit in `BK15`.
- `StageConnections.Connections[]`: `{Source, Target}` stage UIds - the moves the user may make;
  an empty list means any stage can follow any.
- `Filters`: a `Terrasoft.FilterGroup` JSON string that limits the records the case applies to.
- Captions: `Stages.<Stage>.Caption`, `Stages.<Stage>.Elements.<Step>.Caption` in the resources.

## What the tools write

`new` builds an empty case (optionally with chained stages) on an object of the workspace; the
column must be a lookup. `add-stage` / `remove-stage` keep connections, alternatives and captions
in step; `connect` / `disconnect` edit the allowed moves.

`add-step` puts a step on a stage that starts a process of the workspace, as the designer does:
`DcmElementN` with a `DcmProcessElementN` flow element (`CK4` the process), a copy of each of
the process's parameters (`A3` the called UId) with one mapping per copy in the case's `BK15`
(the shared `copy_called_params` of the process toolkit), the captions of the step and of each
parameter. `--map Param=value` writes the value into the copy's `L8`: `{Record:Column}` is a
column of the case's record (`[#ColumnValue.{object}.{column}#]`, shown as
`[#Main record.Column#]` - every valued parameter of the 15 real steps is this, `{Record:Id}`),
`{Parameter:X}` a parameter of the case, anything else a constant. The mapping's `GT1` stays
`{GS5: called}`, as the designer leaves it. `--when "Param op value -> Stage"` adds a result
condition (`==`, `!=`, `>`, `>=`, `<`, `<=`; a lookup value is a record UId or the name of a stage,
standing for its record), serialised like the designer's `Conditions`. `remove-step` takes the
step's mappings and captions with it.

```bash
python dcm.py inspect packages/UsrPkg UsrOrderCases
python dcm.py new packages/UsrPkg UsrOrderCases --caption "Order cases" --entity UsrOrder --stage-column UsrStatus \
    --stage "New=<record uid>" --stage "In progress=<record uid>" --stage "Done=<record uid>"
python dcm.py add-stage packages/UsrPkg UsrOrderCases --caption "On hold" --record <uid> --parent Stage2 --color "#FFAC07"
python dcm.py connect packages/UsrPkg UsrOrderCases Stage1 Stage3 --one-way
python dcm.py add-step packages/UsrPkg UsrOrderCases --stage Stage2 --process UsrCheckOrder_Process --caption "Check order" \
    --map OrderId={Record:Id} --required --when "Verdict = Stage3 -> Stage3"
python describe.py item packages/UsrPkg UsrOrderCases "stage Stage1"
```

Validation refuses a stage record that is not a UId, a connection or a parent that is not a stage,
a step outside its stage, a condition that points to a stage the case no longer has, and a step
parameter the called process does not have; a sub-process missing from the workspace is a warning.

## Verified

Files only: 32 real cases of the local workspaces (15 steps: all plain sub-processes, 17 parameters, every one
mapped; 14 values `{Record:Id}`-style column values, one constant; one step with conditions) (up to 10 stages, 4 steps, conditions, filters,
seven cultures) round-trip byte for byte and describe without errors. On the test environment
(8.2.3): a case made by `new` on an order object's status lookup with two chained stages was
pushed with `clio push-pkg`, the configuration compiled with 0 errors and the schema is in
`SysSchema` under `DcmSchemaManager` (the pulled package comes back in the platform's own binary
format, so no file-level comparison with the export).

## Checks

`python tests/test_dcm_tools.py`
