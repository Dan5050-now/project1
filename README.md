# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | v1.3 approved 2026-08-01 · **v1.5 changes awaiting signature** |
| 2 | Programming specification | **v0.4 draft — all six open points answered** |
| 3 | Prototype UI design | **v0.3 prototype + component list issued for review** |
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

- `docs/PRAP_Development_Plan_v1.5.xlsx` — **current.** 67 requirements, 22 validation
  rules. Carries four changes against the approved baseline, all awaiting signature:
  R-05 (`project_type` splits into `NewDrug CT` and `Biosimilar CT`, schema version 3),
  R-06 (target volume 100 projects / 1,000 people, `Should` → `Must`), R-07 (both
  allocation thresholds absolute, under-allocation floor 0.80 → 0.60) and R-08
  (a repeated period name must be distinguishable on screen).
- `docs/PRAP_Development_Plan_v1.3.xlsx` — **the approved baseline** (Dan, 2026-08-01);
  65 requirements, 21 validation rules, 11 engineering decisions.
- `docs/PRAP_Development_Plan_v1.4.xlsx`, `_v1.2.xlsx`, `_v1.1.xlsx`, `_v1.0.xlsx` — superseded.
- `docs/PRAP_Development_Plan_v0.4.xlsx` … `_v0.1.xlsx` — superseded drafts.
- `docs/review/` — reviewer mark-ups, kept unedited so the review trail is auditable.
- `docs/STEP2_OPEN_POINTS.md` — points raised while building the template, for the
  specification to settle.

### Step 3 deliverables (for review)

- `app/PRAP_Prototype_v0.3.html` — the UI prototype. **Design only**: nothing loads,
  calculates or exports. The only scripts are tab switching and row expansion.
  Self-contained, offline, light and dark.
- `docs/PRAP_UI_Component_List_v0.3.xlsx` — 38 components to mark Keep / Change /
  Drop, plus 15 design decisions to accept or overturn, and what is deliberately
  deferred.

### Step 2 deliverables (for review)

- `docs/PRAP_Programming_Specification_v0.4.xlsx` — 11 sheets: parse contract,
  all 22 validation rules with their exact messages, calculation pseudocode,
  UI behaviour, editing and IO, versioning, and a traceability matrix covering
  all 67 requirements. Sheet 10 records the six open points from the v0.3 review,
  the answers given, and what each one changed.

- `templates/PRAP_SourceData_Template_v1.4.xlsx` — blank workbook: 10 sheets, headers,
  value lists, dropdowns, one example row per sheet, colour-coded README. Every sheet
  carries at least one free-text note column (schema version 3).
- `templates/PRAP_SourceData_Dummy_v1.5.xlsx` — the same structure populated with
  **34 NewDrug CT + 16 Biosimilar CT + 12 `Others` projects and 20 people**
  (289 assignments, 372 milestones, 308 periods across 73 months). Generated
  deterministically, so it rebuilds identically.

Validate either with:

```bash
python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_v1.5.xlsx
```

And check the documents still describe the artifacts they claim to:

```bash
python tools/check_consistency.py
```

That cross-checks 62 documented columns against the template's real headers, the
schema version across all four files, the `project_type` values, every `Config`
default the specification quotes against the value the template actually holds, all 67
requirements plan-to-specification in both directions, and that no build markers were
left in a shipped workbook.

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
- **Over-allocation** above 1.50 FTE in a month; **under-allocation** below 0.60 FTE
  sustained three or more consecutive months (Q-08, S2-05). Both figures are
  **absolute** — not scaled by `capacity_fte` (S2-01). At 0.60 every capacity in the
  data can clear the floor; V-22 warns on import about a capacity below it.
- **Target volume: 100 projects and 1,000 people** over a 60-month horizon (S2-06).
  At that size the tables are virtualised and the per-person chart aggregates —
  requirements, not optimisations (REQ-DSH-09).
- **A repeated period name is numbered on screen** — `Conduct (1)`, `Conduct (2)` —
  wherever it is shown (S2-04, REQ-DSH-10).
- **Three project types**: `NewDrug CT`, `Biosimilar CT`, `Others`. The two trial
  types share one period set and one derivation, and differ in their weights.
- **Period sets differ by project type**: both trial types use Before-Start-up /
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

Open `app/PRAP_Prototype_v0.3.html` in a browser, then work down
`docs/PRAP_UI_Component_List_v0.3.xlsx`:

1. **Sheet 01** — mark each of the 38 components Keep / Change / Drop.
2. **Sheet 02** — accept or overturn the 15 design decisions. Three are worth the
   reading time: **D-11** (per-project colour needs ~50 hues, well past the 8 that can
   be told apart reliably, so identity comes from legend order and tooltip rather than
   hue), **D-14** (at 1,000 people the person chart shows a ranked subset, because
   1,000 bars in a 1,200px panel is 1.2px each) and **D-15** (repeated period names are
   numbered rather than renamed, so the weight lookup keyed on the name still works).

Per the plan, code generation starts only after the component list is approved.

Also pending: **sign off plan v1.5**, which carries the four changes listed above.
Nothing in the specification is now waiting on an answer — all six open points from the
v0.3 review are closed on its sheet 10.
