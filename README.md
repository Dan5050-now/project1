# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **v1.0 FINAL — issued for Gate 1 approval** (four review rounds, all 28 questions closed) |
| 2 | Programming specification | Ready to start on Gate 1 approval |
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

- `docs/PRAP_Development_Plan_v1.0.xlsx` — **current, final Step 1 baseline.**
  13 sheets: scope, requirement register (63 requirements), data model, resource
  calculation logic, dashboard design, architecture, work breakdown,
  version-control rules, risks, questions and answers, review log.
- `docs/PRAP_Development_Plan_v0.4.xlsx` … `_v0.1.xlsx` — superseded drafts.
- `docs/review/` — reviewer mark-ups, kept unedited so the review trail is auditable.

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
- **Period sets differ by project type**: Clinical Trial uses Before-Start-up /
  Start-up / Conduct / Close-out (interim) / Close-out (final), derived from
  milestone dates; Others uses Planning / Develop / Close, entered directly.
- **`Conduct` can occur twice** in one project, split by an interim DB lock, so a
  period name is not unique within a project (Q-23).
- **Period weights are selected by clinical phase** for clinical trials (Q-26);
  `Others` projects are hand-entered throughout — dates and weights alike (Q-28).
- **Every field is editable**, with identifier edits cascading to referencing rows
  rather than being blocked (Q-20).
- **Imported data is editable in the application**, with edits carried into the
  export (REQ-IMP-07).

## Next action

**Record Gate 1 approval** on sheet `12_Review_Log` of
`docs/PRAP_Development_Plan_v1.0.xlsx`.

Approving baselines the 63 requirements as the contract for Steps 2–5, and
confirms the six engineering decisions C-06 to C-11 that were proposed during
review but never explicitly answered. Step 2 — the programming specification —
begins once the gate is recorded.

All 28 review questions are closed. The period model is verified: the derivation
was run against five timelines, including four degenerate ones, and produces
contiguous periods with no gap or overlap in every case.
