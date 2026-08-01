# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **COMPLETE** — v1.3 approved FINAL by Dan, 2026-08-01 |
| 2 | Programming specification | **v0.2 draft issued for review** |
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

- `docs/PRAP_Development_Plan_v1.3.xlsx` — **FINAL.** Approved by Dan, 2026-08-01.
  65 requirements, 21 validation rules, 11 engineering decisions, source schema
  version 2. Step 1 is complete and the plan is closed.
- `docs/PRAP_Development_Plan_v1.2.xlsx`, `_v1.1.xlsx`, `_v1.0.xlsx` — superseded.
- `docs/PRAP_Development_Plan_v0.4.xlsx` … `_v0.1.xlsx` — superseded drafts.
- `docs/review/` — reviewer mark-ups, kept unedited so the review trail is auditable.
- `docs/STEP2_OPEN_POINTS.md` — points raised while building the template, for the
  specification to settle.

### Step 2 deliverables (for review)

- `docs/PRAP_Programming_Specification_v0.2.xlsx` — 11 sheets: parse contract,
  all 21 validation rules with their exact messages, calculation pseudocode,
  UI behaviour, editing and IO, versioning, and a traceability matrix covering
  all 65 approved requirements.

- `templates/PRAP_SourceData_Template_v1.2.xlsx` — blank workbook: 10 sheets, headers,
  value lists, dropdowns, one example row per sheet, colour-coded README. Every sheet
  carries at least one free-text note column (schema version 2).
- `templates/PRAP_SourceData_Dummy_v1.3.xlsx` — the same structure populated with
  **50 clinical trials, 12 `Others` projects and 20 people** (289 assignments, 372
  milestones, 308 periods across 73 months). Generated deterministically, so it
  rebuilds identically. 30 trials carry an interim DB lock and so show two `Conduct`
  stretches; 12 carry the seventh period from a post-lock `Inspection`.

The template stays at v1.2 — its structure did not change, only the dataset.

Validate either with:

```bash
python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_v1.3.xlsx
```

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
  Start-up / Conduct / Close-out (interim) / Close-out (final) / After Close-out
  (final), derived from milestone dates; Others uses Planning / Develop / Close,
  entered directly.
- **`Conduct` can occur twice** in one project, split by an interim DB lock, so a
  period name is not unique within a project (Q-23).
- **`Inspection` may be recorded several times** per project, and opens a seventh
  period where it follows the final DB lock. An inspection dated on or before the
  final DB lock stays a marker (R-01, R-02, R-03 — confirmed).
- **Period weights are selected by clinical phase** for clinical trials (Q-26);
  `Others` projects are hand-entered throughout — dates and weights alike (Q-28).
- **Every field is editable**, with identifier edits cascading to referencing rows
  rather than being blocked (Q-20).
- **Imported data is editable in the application**, with edits carried into the
  export (REQ-IMP-07).

## Next action

Review `docs/PRAP_Programming_Specification_v0.2.xlsx`, in particular sheet
`10_Open_Points` — five items, each stating what the draft assumes so nothing is
blocked. **S2-01** is the one that matters: the under-allocation threshold is an
absolute 0.80 FTE, so a part-timer at 0.60 capacity is flagged permanently and can
never clear it. The draft specifies both thresholds as relative to `capacity_fte`,
which changes nothing for full-time staff.

The development plan is closed, so this is the only decision outstanding across the
whole project.
