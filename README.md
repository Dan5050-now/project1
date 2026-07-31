# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **Draft v0.2 issued for review** (v0.1 reviewed, answers incorporated) |
| 2 | Programming specification | Not started (starts after Gate 1) |
| 3 | Prototype UI design | Not started |
| 4 | Code generation | Not started |
| 5 | Finalisation | Not started |

Each step ends at a review gate. Work on a step begins only once the previous gate
is approved.

## Repository layout

```
docs/         Plan and specification workbooks (.xlsx deliverables)
docs/review/  Reviewer mark-ups, archived as received
tools/        Generator scripts - the reviewable source for the .xlsx documents
app/          The application HTML file            (from Step 4)
templates/    Blank source-data workbook           (from Step 4)
output/       Exported results and test evidence   (from Step 5)
```

## Documents

- `docs/PRAP_Development_Plan_v0.2.xlsx` — **current.** 13 sheets: scope,
  requirement register (58 requirements), data model, resource calculation logic,
  dashboard design, architecture, work breakdown, version-control rules, risks,
  open questions, review log.
- `docs/PRAP_Development_Plan_v0.1.xlsx` — first issue, superseded.
- `docs/review/PRAP_Development_Plan_v0.11_reviewed.xlsx` — reviewer mark-up of
  v0.1, kept unedited so the review trail is auditable.

## Why the documents are generated from scripts

The deliverables must be Excel workbooks, but a binary `.xlsx` cannot be reviewed as
a diff. Each workbook is therefore produced by a script in `tools/`, and both the
script and the workbook are committed. Changes to a document are visible as an
ordinary text diff, and any version can be rebuilt exactly:

```bash
python tools/build_dev_plan.py
```

Requires `openpyxl`.

## Confirmed decisions

- **D-01 — Excel access:** the user selects the source workbook through a browser file
  picker or drag-and-drop, and an embedded SheetJS-style parser reads it in memory.
  A page opened from local disk cannot read a fixed path unaided, and this option is
  the only one that keeps true `.xlsx` as the archive of record with no install and
  no server.
- **Five development steps** as listed above.
- **One source workbook**, not two (Q-09).
- **Load = project period weight × role factor × person weight × month coverage**,
  in FTE where 1.00 FTE = 160 h/month (Q-01, Q-08).
- **Over-allocation** above 1.50 FTE in a month; **under-allocation** below 0.80 FTE
  sustained three or more consecutive months (Q-08).
- **Imported data is editable in the application**, with edits carried into the
  export (REQ-IMP-07).

## Next action

Answer `11_Open_Questions` Q-13 to Q-20 in `docs/PRAP_Development_Plan_v0.2.xlsx`.
Two of them block real progress:

- **Q-13** — the `13_Templete_example` sheet referenced in the Q-10 answer is not
  present in the returned workbook.
- **Q-17** — the period weights and role factors themselves, without which the
  engine can be built but its output cannot be validated.
