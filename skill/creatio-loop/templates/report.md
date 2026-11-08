# <task-id> report

Append a block per hand-over. Never edit an earlier block.

## Round 1 - author - 2026-11-06 14:10

Files: `packages/UsrTest/Schemas/UsrShipment/metadata.json`, `Files/cs/ShipmentLabel.cs`, ...

| AC | Result | Evidence |
|---|---|---|
| AC-01 | pass | `objects.py probe UsrTest UsrShipment`: 9 ok |
| AC-02 | not tested | needs the runner (tester) |
| AC-03 | not tested | |
| AC-04 | not tested | |

Returned to: tester. Reason: artifacts pushed and probed.

## Round 1 - tester - 2026-11-06 14:40

| AC | Result | Evidence |
|---|---|---|
| AC-01 | pass | `objects.py probe UsrTest UsrShipment`: 9 ok |
| AC-02 | fail | `tests.py run UsrTests --filter AC02`: expected `PARCEL-0007`, actual `Parcel-7` |
| AC-03 | fail | `proc.py run UsrShipmentLabel_Process`: Label=`Parcel-7` |
| AC-04 | pass | `creatio-tests --filter AC04`: PASS (8.1s) |

Returned to: author. Reason: AC-02, AC-03 - label format.

Results: `pass` | `fail` (with evidence) | `blocked` (with the reason, goes to the human) |
`not tested` (with what blocks it).
