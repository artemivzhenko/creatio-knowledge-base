# 012 Report 2

Tester, 2026-11-06 14:40. Plan read: `plan.md` as of 2026-11-06 12:05. One row per criterion;
`fail` and `blocked` point to a file in `evidence/`.

| AC | Result | Evidence |
|---|---|---|
| AC-01 | pass | `objects.py probe UsrPkg UsrShipment`: `UsrLabel Text 250 ok` |
| AC-02 | pass | `dotnet test tests/UsrPkg`: 6 passed |
| AC-03 | fail | `evidence/AC-03-report-2.txt`: expected `PARCEL-0007`, actual `Parcel-7` |
| AC-04 | not tested | depends on AC-03 |
| AC-05 | fail | `evidence/AC-05-report-2.txt`: `Label` = `Parcel-7` |
| AC-06 | pass | `creatio-tests run --filter 012-shipped-readonly`: PASS, 8.1 s |

## Tests written

- `ProcessCases/012-shipment-label.act` (AC-03, AC-04, AC-05) in the test framework
- `Cases/012-shipped-readonly.act` (AC-06)

## Notes for the author

The label is built with the type's caption as typed, not in capitals; the padding is missing too.
