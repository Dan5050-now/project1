# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **v2.0 APPROVED BASELINE** 2026-08-02 · v2.12 records Step 4 progress |
| 2 | Programming specification | **v1.0 APPROVED** 2026-08-02 |
| 3 | Prototype UI design | **v1.0 component list APPROVED** 2026-08-02 |
| 4 | Code generation | **`app/PRAP.html` built and verified** · awaiting your Gate 4 review |
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

- `docs/PRAP_Development_Plan_v2.12.xlsx` — **current.** 70 requirements, 24 validation
  rules, source schema version 5. Records Step 4 progress against the approved baseline.
- `docs/PRAP_Development_Plan_v2.0.xlsx` — **THE APPROVED BASELINE** (Dan, 2026-08-02),
  superseding v1.3. It carries the nine changes made across the review rounds:
  R-05 (`project_type` splits into `NewDrug CT` and `Biosimilar CT`, schema version 3),
  R-06 (target volume 100 projects / 1,000 people, `Should` → `Must`), R-07 (both
  allocation thresholds absolute, under-allocation floor 0.80 → 0.60), R-08
  (a repeated period name must be distinguishable on screen), R-09 (the
  component-list review: a tab for the standing assumptions, and row insertion) and
  R-10 (the role factor is keyed on project type, clinical phase, period and role) and
  R-11 (the two conduct stretches are named apart, so `ProjectPeriod` is keyed on
  `project_id + period_name`; schema 4 → 5), R-12 (two `PersonPeriodWeight` rules
  that were specified but never implemented, now closed; V-24 added) and R-13 (the DB
  lock milestones emphasised, and a project utilisation graph added as REQ-DSH-12).
- `docs/PRAP_Development_Plan_v1.3.xlsx` — **the approved baseline** (Dan, 2026-08-01);
  65 requirements, 21 validation rules, 11 engineering decisions.
- `docs/PRAP_Development_Plan_v2.11.xlsx`, `_v2.10.xlsx`, `_v2.9.xlsx`, `_v2.8.xlsx`, `_v2.7.xlsx`, `_v2.6.xlsx`, `_v1.9.xlsx`, `_v1.8.xlsx`, `_v1.7.xlsx`, `_v1.6.xlsx`, `_v1.5.xlsx`, `_v1.4.xlsx`, `_v1.2.xlsx`, `_v1.1.xlsx`, `_v1.0.xlsx` — superseded.
- `docs/PRAP_Development_Plan_v0.4.xlsx` … `_v0.1.xlsx` — superseded drafts.
- `docs/review/` — reviewer mark-ups, kept unedited so the review trail is auditable.
- `docs/STEP2_OPEN_POINTS.md` — points raised while building the template, for the
  specification to settle.

### Step 4 deliverable — the application

- `app/PRAP.html` — **the application.** One file, offline, no network and no install.
  Open it in a browser, choose a `.xlsx`, and it parses, validates, derives periods,
  calculates, renders four tabs and exports back to `.xlsx`.

  It carries its own `.xlsx` reader and writer. An `.xlsx` is a ZIP of XML; the browser
  supplies `DecompressionStream` for the deflate entries and `DOMParser` for the XML,
  and a ZIP written with STORED entries needs only a CRC32. Vendoring a spreadsheet
  library would have been quicker and would have cost the single-file property that
  decision D-01 turns on.

  **How it was verified**, since a screenshot proves very little:

  | Check | Result |
  |---|---|
  | Calculation vs `verify_source_workbook.py` | **exact match on all 1,225 person-months** (and all 433 of the 10×10 set) |
  | Findings vs the Python verifier | both report zero on the dummy |
  | Export → re-import | identical figures, zero findings |
  | Export read by `openpyxl` (an independent implementation) | passes the full verifier |
  | Identifier edit | cascades to all 19 referencing rows, no errors introduced |
  | Bad date (`03/04/2026`) | rejected at entry, cell restored |
  | Row insert | lands directly below the row acted on |
  | Row insert / delete on the four child tables | `tools/test_rows.py`, and it fails against the build before the fix |
  | Project by name, allocated `assignment_id`, two-way scrolling | same file, and it also fails against the build before it |
  | Re-pointing an override row moves that row only | same file; the previous build dragged both windows of the old assignment |
  | The value list survives scrolling, matches on tokens | `tools/test_valuelist.py`; 6 of its 14 checks fail against the previous build |
  | The stacked utilisation segments sum to the person-month the model holds | `tools/test_charts.py`; 6 of its 8 checks fail against the previous build |

  Gate 4 round 1 (app v1.1): the three named Overall sections are up to twice their
  previous size; the project timeline scrolls in both directions, so every project in
  the filter is drawn rather than the first 20; and chart text is larger with every
  threshold label moved out of the plot area into a right-hand margin.

  Gate 4 round 2 (app v1.2): the page carries its own provenance at the top — which
  plan, specification, component list and source template the build implements, plus
  whether the loaded workbook's schema matches. `check_consistency.py` verifies that
  claim against the repository, so it cannot go stale unnoticed.

  Gate 4 round 3 (app v1.3): column headings stay visible in every scroll region; the
  utilisation charts label the year on the x axis; and **editing is now provisional** —
  a change is applied on screen but held as pending until you press **Save** or
  **Leave without change**, and export is held while anything is pending.

  Gate 4 round 4 (app v1.4): information pop-ups on every column heading, summary tile,
  month heading and type pill — hover to see, click to pin; and a **Delete** control on
  every editable row, refused when anything still references the row (V-17).

  Gate 4 round 5 (app v1.5): lookup columns on the person tab so an identifier is never
  alone; every cell shows its value and its column's meaning on hover; row actions on
  the Periods and General-assumptions tables, with a matrix/rows toggle where a matrix
  row is several workbook rows; and **type-ahead** on every column with a vocabulary.

  Gate 4 round 11 (app v1.10): a **project timeline** run-chart now stands before the
  Utilisation panel on the project tab — the Overall tab's chart for one project, each
  band labelled with its average FTE per month. And the person tab's **Utilisation bars
  are stacked by project**: the total says whether someone is over the ceiling, the split
  says because of what. Each segment's pop-up answers both halves at once — the project
  (name, type, the milestones it passes that month, this person's FTE on it and its share
  of the month) and the person (name, total FTE, how many projects, capacity, threshold
  crossed). Over- and under-allocation is drawn as an outline *behind* the stack, since
  it is a property of the month's total, not of any one project in it. Project colours
  are now fixed for the session, so one project carries one colour everywhere.

  Gate 4 round 10 (app v1.9): a reported defect — dragging the scroll bar of a value
  list closed the list, so a list taller than its box could not be read to the bottom.
  Two causes: a capturing scroll listener closed it on *any* scroll including its own,
  and pressing its scroll bar took focus off the cell. It now re-anchors instead of
  closing, and holds the press. The list closes on exactly three things: choosing a
  value, Escape, or a click outside; a click back in the field re-opens it. Matching now
  works on **tokens in any order** (`phase 1 onv` finds `ONV-101 Phase 1`), marks every
  matched fragment, ranks a typed prefix first, and shows the whole vocabulary with an
  explanation when nothing matches rather than vanishing.

  Gate 4 round 9 (app v1.8): a reported defect — choosing an `assignment_id` on a new
  Weight-overrides row warned that it would change every other override of the
  assignment being moved away from, so a second window could not be added. The edit path
  cascaded an identifier change whenever the edited column was the sheet's key, but on a
  **child** sheet that column is a *foreign* key: `PersonPeriodWeight.assignment_id`
  points at an assignment, it does not define one. The cascade is now confined to the
  sheet that owns the identifier — the same distinction `deleteRow` has made since round
  4. In place of the warning, picking an assignment that already carries windows says how
  many the row joins and names V-06 and V-24.

  Gate 4 round 8 (app v1.7): **every** scroll region scrolls in both directions and is
  bounded on both axes — a panel bounded on one axis only can still hide content on the
  other, with no scrollbar to say so. On the Assignments table the project is identified
  by **name**: type `project_name` and `project_id` follows, with type-ahead over the
  project names and a refusal (naming near matches) if the name matches nothing. Editing
  the identifier still drives the name the other way; the name is never stored on the
  assignment row. **+ row** allocates the next free `assignment_id`.

  Gate 4 round 7 (app unchanged): a second dummy dataset at 10 projects and 10 people,
  issued alongside the 62-project set rather than replacing it. One generator, two size
  profiles. `tools/test_app.py` now runs over both.

  Gate 4 round 6 (app v1.6): a reported defect — insert and delete did nothing useful on
  Milestones, Periods, Assignments and Weight overrides. Three faults, all in the shared
  insert/rebuild path: a new child row was created with no parent, so the filter that
  decides what a child table shows hid it; the re-parse that follows every edit discards
  blank rows, which silently destroyed a row not yet filled in; and rows are numbered by
  position, so a delete renumbered everything below it while pending edits still named
  the old numbers. New rows are now seeded with their parent, held out of the re-parse
  until they have content, and keep their identity across a rebuild. A row still being
  written is exempt from validation and is validated when **Save** is pressed.

### Step 3 deliverables (approved)

- `app/PRAP_Prototype_v0.8.html` — the UI prototype. **Design only**: nothing loads,
  calculates or exports. The only scripts are tab switching, row expansion and the
  hover pop-up. Self-contained, offline, light and dark. Four tabs.
- `docs/PRAP_UI_Component_List_v1.0.xlsx` — **approved.** The review disposition: all 46 components
  with your decision and comment quoted verbatim against what was done, 19 design
  decisions, a change log of what the reviews moved in the plan and specification, and
  sheets 05 to 08 covering review rounds 3 to 6.

### Step 2 deliverables (for review)

- `docs/PRAP_Programming_Specification_v1.0.xlsx` — **approved.** 11 sheets: parse contract,
  all 24 validation rules with their exact messages, calculation pseudocode,
  UI behaviour for four tabs, editing and IO, versioning, and a traceability matrix
  covering all 70 requirements. Sheet 10 records the six open points from the v0.3
  review, the answers given, and what each one changed. None open.

- `templates/PRAP_SourceData_Template_v1.6.xlsx` — blank workbook: 10 sheets, headers,
  value lists, dropdowns, one example row per sheet, colour-coded README. Every sheet
  carries at least one free-text note column (schema version 3).
- `templates/PRAP_SourceData_Dummy_v1.8.xlsx` — the same structure populated with
  **34 NewDrug CT + 16 Biosimilar CT + 12 `Others` projects and 20 people**
  (289 assignments, 372 milestones, 308 periods across 73 months).
- `templates/PRAP_SourceData_Dummy_10x10_v1.0.xlsx` — the same again at **10 projects
  and 10 people** (8 clinical trials + 2 `Others`, 50 assignments, 60 milestones,
  50 periods across 50 months): small enough to read every row on screen and check the
  arithmetic by hand. It is not a lighter test — it carries both clinical types, all
  four phases, trials with and without an interim DB lock, inspections that open the
  seventh period, hand-entered `Others` periods, two part-timers, multi-window weight
  overrides, and both allocation thresholds crossed. Its load distribution tracks the
  large set's (median 0.80 against 0.87 FTE).

Both come from one generator driven by size profiles, so neither can drift from the
schema the other follows. The data is seeded: every sheet rebuilds byte-for-byte. The
`.xlsx` container does not, because openpyxl stamps the build time into
`docProps/core.xml`.

Validate any of them with:

```bash
python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_10x10_v1.0.xlsx
```

And check the application against the reference implementation:

```bash
python tools/test_app.py
```

That drives `app/PRAP.html` in a real browser over **both** dummy datasets, compares
its calculation with `verify_source_workbook.py` cell by cell, exports, re-imports, and
puts the export through `openpyxl` — a reader that is not ours. Pass a path to run it
against one fixture only.

And check that rows can be added and removed on every table:

```bash
python tools/test_rows.py
```

That inserts and deletes on each of the four child tables, then fills a new row in on
each, saves, exports and reads the export back — the four operations that were broken
before app v1.6.

And check that the type-ahead value list behaves like a chooser:

```bash
python tools/test_valuelist.py
```

That opens the list, scrolls it by wheel and by dragging its own scroll bar, scrolls the
page under it, searches it, and closes it every way it can be closed.

And check the two source-data charts against the model behind them:

```bash
python tools/test_charts.py
```

That counts the bands and markers on the project timeline against the periods and
milestones in the data, and adds up the stacked utilisation segments month by month to
confirm they equal the person-month the calculation holds — a chart that disagrees with
the table is worse than no chart.

And check the documents still describe the artifacts they claim to:

```bash
python tools/check_consistency.py
```

That cross-checks 64 documented columns against the template's real headers, the
schema version across all four files, the `project_type` values, every `Config`
default the specification quotes against the value the template actually holds, all 69
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
  in FTE where 1.00 FTE = 160 h/month (Q-01, Q-08). The **role factor is keyed on
  project type, clinical phase, period and role** (R-10), so a role's burden varies
  across the life of a project — the database programmer peaks at start-up, the
  analyst at lock. `RoleFactor` is 249 rows as a result, and it now varies over the
  same three dimensions as `PeriodWeightStandard`; the two multiply, so they must not
  both be edited for the same reason (D-19, specification sheet 05).
- **Over-allocation** above 1.50 FTE in a month; **under-allocation** below 0.60 FTE
  sustained three or more consecutive months (Q-08, S2-05). Both figures are
  **absolute** — not scaled by `capacity_fte` (S2-01). At 0.60 every capacity in the
  data can clear the floor; V-22 warns on import about a capacity below it.
- **Target volume: 100 projects and 1,000 people** over a 60-month horizon (S2-06).
  At that size the tables are virtualised and the per-person chart aggregates —
  requirements, not optimisations (REQ-DSH-09).
- **A repeated period name is numbered on screen** — `Conduct (1)`, `Conduct (2)` —
  wherever it is shown (S2-04, REQ-DSH-10).
- **Four tabs, not three.** The standing assumptions — standard period weights, role
  factors, config and value lists — get their own tab, so a reader can see what a
  figure was derived from without opening the workbook (G-07, REQ-DSH-11).
- **The timeline is coloured by period name**, with weight as a lightness step inside
  each hue (O-10). This supersedes design decision D-06, on the reviewer's own
  instruction.
- **A row can be inserted anywhere**, landing directly below the row acted on rather
  than at the bottom of the table (P-01/S-01, REQ-IMP-11).
- **Three project types**: `NewDrug CT`, `Biosimilar CT`, `Others`. The two trial
  types share one period set and one derivation, and differ in their weights.
- **Period sets differ by project type**: both trial types use Before-Start-up /
  Start-up / Conduct (interim) / Close-out (interim) / Conduct (final) / Close-out
  (final) / After Close-out (final) — seven names, derived from milestone dates;
  Others uses Planning / Develop / Close, entered directly.
- **The conduct phase is split by NAME, not by sequence** (R-11): `Conduct (interim)`
  where the project has an interim DB lock and the stretch runs before it,
  `Conduct (final)` after it or where there is no interim lock. Period names are
  therefore unique within a project, and `ProjectPeriod` is keyed on
  `project_id + period_name`; `period_seq` carries order only.
- **`Inspection` may be recorded several times** per project, and opens a seventh
  period where it follows the final DB lock. An inspection dated on or before the
  final DB lock stays a marker (R-01, R-02, R-03 — confirmed).
- **Period weights are selected by clinical phase** for clinical trials (Q-26);
  `Others` projects are hand-entered throughout — dates and weights alike (Q-28).
- **Every field is editable**, with identifier edits cascading to referencing rows
  rather than being blocked (Q-20).
- **Imported data is editable in the application**, with edits carried into the
  export (REQ-IMP-07).
- **`PersonPeriodWeight` is keyed on `assignment_id + period_start`** — one assignment
  may carry several non-overlapping override windows, so `assignment_id` alone would
  cap it at one (R-12).

## Next action

Open `app/PRAP_Prototype_v0.4.html` in a browser, then work down
`docs/PRAP_UI_Component_List_v0.4.xlsx`:

1. **Sheet 01** — all nine components you marked Change are applied. Mark the yellow
   column **OK** or **Rework** for each.
2. **Sheet 02** — one item needs your eye: you accepted **D-06** (the timeline shades
   bands by weight) and separately asked in **O-10** for the timeline to be coloured by
   period name. Those cannot both hold. O-10 wins as the more specific instruction, so
   D-06 is superseded and weight now rides as a lightness step inside each period's hue.
   Overturn that if it reads backwards.
3. **Sheet 04** — what round 2 moved outside the component list: two new requirements,
   two reworded.
4. **Sheet 05** — round 3: the role-factor key, the scroll regions, and the insert-button
   fault you reported. **D-19** on sheet 02 is the one to read: keying the role factor on
   phase and period makes it overlap `PeriodWeightStandard`, and the two multiply.
5. **Sheet 06** — round 4: naming the conduct stretches apart. This supersedes **D-15**
   and retires the display numbering that REQ-DSH-10 introduced.
6. **Sheet 07** — round 5: why `PersonPeriodWeight` keeps a two-column key, and the two
   validation rules that question exposed.
7. **Sheet 08** — round 6: the DB lock emphasis and the project utilisation graph. Each
   carries a **judgement call** I made rather than guessed at silently — whether the
   `...cut-off` milestones should also be red, and whether the portfolio average should
   cover active project-months only. Both are one line to change.

Per the plan, code generation starts only after the component list is approved.

Gate 4 is the remaining review: run the application against real data and say what needs to change.
