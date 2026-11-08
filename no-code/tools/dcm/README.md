---
description: Creatio DCM cases (dynamic case management) of 8.x as package files - read a case (object, stage column, filter, stages with their lookup records and colours, steps that start sub-processes, result conditions, allowed stage moves), create a case on an object's lookup column, add or remove stages, connect stages; the describe layer answers stages, stage, steps, step, moves, filter.
---

# DCM case tools

Scripts that read and change DCM cases as **package files** (`Schemas/<Case>/metadata.json`,
`DcmSchemaManager`, `Resources/<Case>.Dcm/`). Pure Python standard library.

| File | What it does |
| --- | --- |
| `dcm.py` | CLI: inspect, validate, new, add-stage, remove-stage, connect, disconnect, set-caption, enable, disable |
| `../creatio_schemas/dcm/schema.py` | `DcmSchema`: the library the CLI and the describe layer use |
| `tests/test_dcm_tools.py` | checks on a real case with generic names |

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
in step; `connect` / `disconnect` edit the allowed moves. Steps and conditions are read and
described but not written: build them in the designer or paste their JSON - a step needs the
sub-process's parameter mappings, which the designer derives from that process.

```bash
python dcm.py inspect packages/UsrPkg UsrOrderCases
python dcm.py new packages/UsrPkg UsrOrderCases --caption "Order cases" --entity UsrOrder --stage-column UsrStatus \
    --stage "New=<record uid>" --stage "In progress=<record uid>" --stage "Done=<record uid>"
python dcm.py add-stage packages/UsrPkg UsrOrderCases --caption "On hold" --record <uid> --parent Stage2 --color "#FFAC07"
python dcm.py connect packages/UsrPkg UsrOrderCases Stage1 Stage3 --one-way
python describe.py item packages/UsrPkg UsrOrderCases "stage Stage1"
```

Validation refuses a stage record that is not a UId, a connection or a parent that is not a stage,
a step outside its stage, and a condition that points to a stage the case no longer has; a
sub-process missing from the workspace is a warning.

## Verified

Files only: 31 real cases of three workspaces (up to 10 stages, 4 steps, conditions, filters,
seven cultures) round-trip byte for byte and describe without errors. On the test environment
(8.2.3): a case made by `new` on an order object's status lookup with two chained stages was
pushed with `clio push-pkg`, the configuration compiled with 0 errors and the schema is in
`SysSchema` under `DcmSchemaManager` (the pulled package comes back in the platform's own binary
format, so no file-level comparison with the export).

## Checks

`python tests/test_dcm_tools.py`
