# <task-id> <title>

Environment: ti823. Package: iaTest. Written by: <name>, <date>.

## Goal

One paragraph: what the user gets when this is done.

## Artifacts expected

- object `iaShipment`: column `iaLabel` (Text 250)
- process `iaShipmentLabel_Process`
- page `iaShipment_FormPage`: rule "label is read-only once shipped"
- C#: `Files/cs/ShipmentLabel.cs`

## Acceptance criteria

| AC | Action | Expected result | Tier |
|---|---|---|---|
| AC-01 | push the package | `objects.py probe iaTest iaShipment` reports every column ok | probe |
| AC-02 | insert a shipment with type "Parcel" and number 7 | `iaLabel` equals `PARCEL-0007` | integration |
| AC-03 | run `iaShipmentLabel_Process` with `ShipmentId` of AC-02's row | result parameter `Label` equals `PARCEL-0007` | process |
| AC-04 | open the shipment page, set the status to Shipped | the label field is read-only | ui |

Tiers: `probe`, `integration`, `process`, `ui` - see the creatio-loop skill.

## Out of scope

What the tester must not report on, so it is not reported.
