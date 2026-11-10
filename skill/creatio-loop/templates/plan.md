# 012 Plan

Written by the author after the answers, then built as written. The tester tests against the
acceptance criteria below and nothing else.

## Approach

An entity event listener on `UsrShipment` builds the label on insert and on every save while the
status is not Shipped; the format lives in one static method so the process and the listener
share it. The read-only rule is a page business rule on `UsrShipment_FormPage`. The process
`UsrShipmentLabel_Process` has one input (`ShipmentId`) and one output (`Label`).

## Artifacts

| Kind | Name | Change |
|---|---|---|
| object | `UsrShipment` | new column `UsrLabel` (Text 250) |
| C# | `Files/cs/ShipmentLabel.cs`, `Files/cs/UsrShipmentEventListener.cs` | new |
| unit tests | `tests/UsrPkg/ShipmentLabelTests.cs` | new |
| process | `UsrShipmentLabel_Process` | new |
| page | `UsrShipment_FormPage` | rule: `UsrLabel` read-only when status is Shipped |

## Preconditions

| Fact | Checked by |
|---|---|
| `UsrShipment_FormPage` has no copy in the customisation layer | `describe.py layers UsrShipment_FormPage -e dev` exits 0 |
| the environment's package is unchanged since the last commit | `push.py packages/UsrPkg -e dev --dry-run` reports no drift |
| the test package is installed | `describe.py package` of the environment's test package lists `UsrTests` |

## Acceptance criteria

| AC | Action | Expected result | Tier |
|---|---|---|---|
| AC-01 | push the package | `UsrShipment.UsrLabel` exists as Text 250 | probe |
| AC-02 | `ShipmentLabel.Build("Parcel", 7)` | `PARCEL-0007` | unit |
| AC-03 | insert a shipment of type Parcel with `UsrSeq` 7 over OData | the row's `UsrLabel` is `PARCEL-0007` | backend |
| AC-04 | update that shipment's `UsrSeq` to 8 while not shipped | `UsrLabel` becomes `PARCEL-0008` | backend |
| AC-05 | run `UsrShipmentLabel_Process` with the id of AC-03's row | output `Label` equals the row's label | process |
| AC-06 | open the shipment page, set the status to Shipped, save | the label field is read-only | ui |

## Out of scope

Labels for shipments created before this change; printing.
