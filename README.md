# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **Draft v0.1 issued for review** |
| 2 | Programming specification | Not started (starts after Gate 1) |
| 3 | Prototype UI design | Not started |
| 4 | Code generation | Not started |
| 5 | Finalisation | Not started |

Each step ends at a review gate. Work on a step begins only once the previous gate
is approved.

## Repository layout

```
docs/       Plan and specification workbooks (.xlsx deliverables)
tools/      Generator scripts - the reviewable source for the .xlsx documents
app/        The application HTML file            (from Step 4)
templates/  Blank source-data workbooks          (from Step 4)
output/     Exported results and test evidence   (from Step 5)
```

## Documents

- `docs/PRAP_Development_Plan_v0.1.xlsx` — Step 1 deliverable. 13 sheets: scope,
  requirement register, data model, resource calculation logic, dashboard design,
  architecture, work breakdown, version-control rules, risks, open questions,
  review log.

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

## Next action

Review `docs/PRAP_Development_Plan_v0.1.xlsx`, in particular sheet `11_Open_Questions`
(12 questions, yellow cells). Answers there drive the Step 2 specification; anything
left blank is built to the assumption recorded on sheet `10_Risks` and flagged.
