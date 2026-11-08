# 012 Success report

Tester, 2026-11-06 16:10. Plan read: `plan.md` as of 2026-11-06 12:05. Every criterion passed;
the task is done. Earlier rounds: `report-1.md`, `report-2.md`.

| AC | Result | Evidence |
|---|---|---|
| AC-01 | pass | `objects.py probe UsrPkg UsrShipment`: `UsrLabel Text 250 ok` |
| AC-02 | pass | `dotnet test tests/UsrPkg`: 6 passed |
| AC-03 | pass | `ProcessCases/012-shipment-label.act`: `check-record UsrShipment Id=$Shipment has UsrLabel eq "PARCEL-0007"` |
| AC-04 | pass | same case: `PARCEL-0008` after the update |
| AC-05 | pass | same case: `check-result Label eq "PARCEL-0008"` |
| AC-06 | pass | `Cases/012-shipped-readonly.act`: PASS, 7.9 s |

## Tests kept

- `ProcessCases/012-shipment-label.act`, `Cases/012-shipped-readonly.act` in the test framework
- `tests/UsrPkg/ShipmentLabelTests.cs` (author's)
