# Step 2 — open points raised by building the template

Working notes for the programming specification. Recorded here so they are not lost
between the template review and the specification draft.

---

## S2-01 — The under-allocation threshold is absolute, but capacity is per person

**Severity: needs a decision before the calculation is specified.**

`REQ-CAL-07` flags a person whose monthly total stays below `under_allocation_fte`
(default **0.80 FTE**) for three or more consecutive months. The threshold is an
absolute FTE figure. But `Person.capacity_fte` lets a part-timer be recorded at, say,
**0.60 FTE**.

A person with capacity 0.60 **cannot ever reach 0.80**, even fully booked. They are
flagged as under-allocated permanently, and nothing they or their manager does can
clear it. In the dummy file, PSN-004 (capacity 0.60) is flagged for 24 consecutive
months while carrying every hour they have.

The same asymmetry applies at the other end: `over_allocation_fte` of 1.50 means a
part-timer would have to be booked to 250% of their real capacity before anything
lit up.

Three ways to resolve it:

| Option | Rule | Effect on a 0.60-capacity person |
|---|---|---|
| **A — relative** (recommended) | flag below `under_allocation_fte × capacity_fte` | floor becomes 0.48; ceiling 0.90 |
| B — absolute, exempt part-timers | apply the flag only where `capacity_fte = 1.00` | never flagged either way |
| C — absolute, as approved | leave as is | permanently flagged |

Option A is the only one that makes `capacity_fte` mean anything. It is consistent
with the intent of Q-08 for a full-time person (1.00 × 1.50 = 1.50 and 1.00 × 0.80 =
0.80 — identical to today's behaviour), and only changes what happens for part-timers.

This is a specification-level decision about how `REQ-CAL-04` and `REQ-CAL-07` apply,
not a change to the approved requirements themselves — both already say the thresholds
live in `Config`. Worth confirming explicitly all the same.

---

## S2-02 — Two columns cannot have an Excel dropdown

`ProjectPeriod.period_name` and `Assignment.role_name` both draw from a list that
depends on the **project's type**, which lives on another sheet. A plain Excel
dropdown cannot express that without dependent named ranges that break as soon as
rows are inserted.

The template therefore leaves those two columns free-text, and correctness is enforced
on import by **V-15** (period name belongs to the type's set) and **V-03** (role exists
for that type). No data can get through wrong — it is caught at load and at edit
(`REQ-IMP-09`) rather than at typing time.

Worth stating in the specification so it reads as a deliberate choice rather than an
omission.

---

## S2-03 — Adding a list value means inserting inside the block

The `Lists` sheet uses the approved long format (`list_name`, `value`). Dropdowns bind
to a contiguous row range per list, so a new value must be inserted **inside** that
list's block, not appended at the bottom of the sheet.

The alternative — one list per column — would make the ranges robust, but that is a
schema change against an approved baseline. Flagging rather than making it.

---

## Verification status of the dummy file

Run: `python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_v1.0.xlsx`

- 7 projects, 12 people, 30 assignments, 32 periods, 48 months spanned
- Referential integrity, period contiguity, period naming, sequence uniqueness and
  weight coverage: **no errors, no warnings**
- Over-allocation demonstrated: 32 person-months above 1.50 FTE
- Under-allocation demonstrated: 14 runs of 3+ months below 0.80 FTE
- Peak person-month: PSN-002 at 2.04 FTE (326 hours)
