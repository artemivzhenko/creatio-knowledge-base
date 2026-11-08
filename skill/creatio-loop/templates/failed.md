# 012 Failed

Tester, 2026-11-07 10:20. Three reports exist and the fourth run still fails. Testing of this task
stops until the human deletes this file.

## Where the result diverges from the criteria

| AC | Expected | Actual after round 3 | Since |
|---|---|---|---|
| AC-04 | `UsrLabel` becomes `PARCEL-0008` after the update | stays `PARCEL-0007`: the listener builds the label only on insert | report-1 |

## What the reports asked for

report-1: label format. report-2: recalculation on update. report-3: the same, the fix handled
`OnUpdating` but the business rule marks the field read-only before the status is Shipped, so the
page sends no change for `UsrSeq`.

## Possible reasons the plan and the task disagree

`task.md` says "must not be editable once the status is Shipped"; the rule built reads "once the
label exists". The human decides which one the criterion means.
