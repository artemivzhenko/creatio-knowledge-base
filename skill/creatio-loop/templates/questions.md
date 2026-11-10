# 012 Questions

The author writes the questions, numbered, with what it would assume if unanswered. The human
answers under each - in this file, or in chat, in which case the author copies the answer here. Write `No questions.` when there are none - the file still exists.

## Q1. Where does the shipment number come from?

Assumed: a new Integer column `UsrNumber` on `UsrShipment`, filled by the user.

**Answer:** it is the existing `UsrSeq` column.

## Q2. Should the label be recalculated when the type or number changes before shipping?

Assumed: yes, on every save until the status is Shipped.

**Answer:** yes.
