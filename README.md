# Project Resource Assignment Program (PRAP)

A local, single-file HTML application for simulating monthly resource demand across
simultaneously running projects, per project and per person. Source data lives in
Excel files kept outside the application; the Excel files are the archive of record.

## Status

| Step | Description | State |
|---|---|---|
| 1 | Development plan | **v2.0 APPROVED BASELINE** 2026-08-02 · v2.26 records Step 4 progress |
| 2 | Programming specification | **v1.0 APPROVED** 2026-08-02 |
| 3 | Prototype UI design | **v1.0 component list APPROVED** 2026-08-02 |
| 4 | Code generation | **`app/PRAP.html` built and verified** · awaiting your Gate 4 review |
| 5 | Finalisation | Not started |

Each step ends at a review gate. Work on a step begins only once the previous gate
is approved.

### A second product line — the desktop application

Requested 2026-08-13: the same simulation as a conventional installed program, which
keeps imported data across sessions. It is planned **separately**, under its own
document line and its own gates N1–N5, because the web application above is finished
and stays in service — the two are parallel products, not successor and predecessor.

| Step | Description | State |
|---|---|---|
| N1 | Development plan | **v1.0 APPROVED BASELINE** 2026-08-13 · Gate N1 closed |
| N2 | Programming specification | **v1.0 APPROVED** 2026-08-13 · Gate N2 closed |
| N3 | Desktop UI design | Authorised — not started |
| N4–N5 | Build, release | Not started |

Both applications share one calculation engine, one data schema (version 5) and one
JSON interchange format, so they cannot disagree about a number. Nothing in that plan
amends the web application's plan, specification, component list or code.

**`app/PRAP.html` is now a build output, not a hand-written file.** Edit the part under
`src/` and run `python tools/build_app.py`; `check_consistency` fails if the committed
file and the sources disagree.

```
src/core/      1,210 lines   decides numbers — parse, validate, derive, calculate, xlsx, JSON
src/ui/                      draws them — tables, charts, filters, the provisional-edit model
src/storage/      63 lines   puts bytes somewhere — the seam the desktop shell replaces
src/shell/web/               page markup and event wiring — the web build target
```

The split was made along the fourteen section boundaries the single file already had, in
order, so the rebuilt file is **byte-identical** to the one that passed all thirteen
suites — sha256 `a428a225…`, unchanged. Identity is a stronger claim than equivalence,
and needs no argument.

## Repository layout

```
docs/         Plan and specification workbooks (.xlsx deliverables), and the
              AI-agent reference: PRAP_AI_Agent_Guide.md, prap_contract.json,
              PRAP_Manifest.json
docs/review/  Reviewer mark-ups, archived as received
tools/        Generator scripts - the reviewable source for the .xlsx documents
app/          The application HTML file            (from Step 4)
templates/    Blank source-data workbook           (from Step 4)
output/       Exported results and test evidence   (from Step 5)
```

## If you are an AI agent, start here

**[`docs/PRAP_AI_Agent_Guide.md`](docs/PRAP_AI_Agent_Guide.md)** — instructions and
guidelines for using the application and the source-data template, written for a
language model rather than a person. Its machine-readable half is
[`docs/prap_contract.json`](docs/prap_contract.json): the schema, every column with its
type and meaning, the value lists, the `Config` parameters, the formula term by term,
the period derivation, all 25 validation rules, the interchange format and worked task
recipes. Both are generated from the template builder, the plan and the application
source, so neither can drift from what it describes.

You do not drive the application — it has no API. You produce and check the file it
reads:

```bash
python tools/prap_io.py to-json  data.xlsx -o data.prap.json   # read it as plain text
python tools/prap_io.py validate  data.prap.json               # the app's own rules
python tools/prap_io.py calculate data.prap.json --by person --flags
python tools/prap_io.py to-xlsx   data.prap.json -o data_draft.xlsx
```

`prap_io.py` runs the same rules and the same formula as the page, and
`tools/test_interop.py` proves the two agree — same findings at the same severities,
every person-month equal to 1e-6, on both worked examples. The application also loads a
`.prap.json` directly and has an **Export JSON** button, so text and workbook are
interchangeable in both directions.

[`docs/PRAP_Manifest.json`](docs/PRAP_Manifest.json) says which file is current, with a
sha256 for each — the repository keeps every superseded version alongside, so resolve a
document through the manifest rather than by sorting filenames.

## Documents

### Desktop application (second product line)

- `docs/PRAP_NewApp_Development_Plan_v1.1.xlsx` — **current.** Records Step N2 progress
  against the baseline; changes no requirement, decision or risk.
- `docs/PRAP_NewApp_Development_Plan_v1.0.xlsx` — **THE APPROVED BASELINE** (2026-08-13),
  closing Gate N1 and authorising Step N2. The application is **Project Management APP**
  (`PM_APP`). 14 sheets: 69 requirements
  (NR-ids), the one-engine/two-shells architecture, the workspace persistence model and
  its write protocol, the sharing model on its own sheet, 32 engineering decisions
  (N-01…N-32, all confirmed by the approval), 19 risks, a five-gate work breakdown, and
  all 18 questions answered across six review rounds. Generated by
  `tools/build_newapp_plan.py`. It does not supersede or amend anything below.
  The constraints it fixes:
  - **Windows 10/11 only.**
  - **Non-installed** — a folder copied and run in place, writing nothing outside itself
    and no registry entry of any kind.
  - **Shareable** — one copy on a network folder may serve several people, so the data
    location is resolved by a fixed, visible rule.
  - **Single writer, many readers** — while one session is editing, no other may update.
    The claim is taken at the *first edit*, not at open, so reading is never blocked;
    it is kept alive by a 30-second heartbeat and expires after 30 minutes of silence,
    so a crashed session frees the plan by itself; and a reader whose figures have been
    superseded is told, rather than quoting stale ones.
  - **Named users** — the application asks who you are at launch (name and department,
    nothing else), so a colleague who cannot edit is shown who is holding the plan,
    which department to ask, and when it frees. The department comes from the same
    vocabulary as `Person.department` in the source schema rather than being typed
    afresh. Declared, not authenticated: it answers "who is editing this", and no more.

  Two items were resolved by the approval rather than by a seventh round: the reading
  taken of the Q-N04 answer is adopted, and the documents keep the `PRAP_NewApp_` prefix.
  Both remain correctable — say so and they change under a v1.1.
- `docs/PRAP_NewApp_Specification_v1.0.xlsx` — **APPROVED** 2026-08-13, closing Gate N2
  and authorising Step N3. All seven open points agreed with no change requested.
  13 sheets: the storage interface and its capability flags, the workspace file format,
  the desktop shell and its launch sequence, the save protocol and recovery, the write
  claim with its state table and every message a user will read, user identity, the
  import difference report, packaging and the folder. All **69 requirements traced**,
  none unspecified — and the NR-ids are read out of the approved plan when the workbook
  is generated, so a requirement cannot be dropped between the two documents.

  It deliberately does **not** restate the data schema, the validation rules or the
  calculation. Those are specified once in `PRAP_Programming_Specification_v1.0.xlsx`
  and both applications are built from the same `src/core/`.
- `docs/review/` — your mark-ups, archived as received: the plan at v0.6 and the
  specification at v0.1.
- `docs/PRAP_NewApp_Development_Plan_v0.7.xlsx` … `_v0.1.xlsx` — superseded drafts.

### Web application (first product line)

- `docs/PRAP_Development_Plan_v2.26.xlsx` — **current.** 70 requirements, 24 validation
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
- `docs/PRAP_Development_Plan_v2.25.xlsx`, `_v2.24.xlsx`, `_v2.23.xlsx`, `_v2.22.xlsx`, `_v2.21.xlsx`, `_v2.20.xlsx`, `_v2.19.xlsx`, `_v2.18.xlsx`, `_v2.17.xlsx`, `_v2.16.xlsx`, `_v2.15.xlsx`, `_v2.14.xlsx`, `_v2.13.xlsx`, `_v2.12.xlsx`, `_v2.11.xlsx`, `_v2.10.xlsx`, `_v2.9.xlsx`, `_v2.8.xlsx`, `_v2.7.xlsx`, `_v2.6.xlsx`, `_v1.9.xlsx`, `_v1.8.xlsx`, `_v1.7.xlsx`, `_v1.6.xlsx`, `_v1.5.xlsx`, `_v1.4.xlsx`, `_v1.2.xlsx`, `_v1.1.xlsx`, `_v1.0.xlsx` — superseded.
- `docs/PRAP_Development_Plan_v0.4.xlsx` … `_v0.1.xlsx` — superseded drafts.
- `docs/review/` — reviewer mark-ups, kept unedited so the review trail is auditable.
- `docs/STEP2_OPEN_POINTS.md` — points raised while building the template, for the
  specification to settle.

### Step 4 deliverable — the application

- `app/PRAP.html` — **the application.** One file, offline, no network and no install.
  Open it in a browser and take either way in: **load a source workbook**
  (`.xlsx` or `.prap.json`), or **start blank** and type the plan in. Both open the same
  four tabs, run the same rules and export to the same `.xlsx`.

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
  | The two Overall charts total the same figure every month | same file; and 5 more of its 14 checks fail against the build before round 12 |
  | Each assignment shows its own override windows, and only those | same file; checked for every assignment of the selected person |
  | Every trend line's total and peak month agree with the model | same file, on all three tabs; and every panel uses one header shape |
  | Derived columns locked, input columns not | `check_consistency.py`, against the plan's data model; caught in all three ways it can break |
  | Every text colour clears WCAG AA, in both themes | `tools/test_contrast.py`; the previous design had five that did not |
  | A whole plan can be built by hand, with no workbook at all | `tools/test_blank.py`; it clicks **Start blank** and enters a project, its milestones, a person, an assignment and a weight override |
  | All four child sections are on screen before anything exists | same file; and a child row entered under an *unsaved* parent still inherits its foreign key |
  | An override replaces the person weight for its months and no others | same file; three months move to 0.70, the other 24 do not move |
  | A commit never moves a scroll position | `tools/test_scroll.py`; 5 of its 11 checks fail against the previous build |
  | A row with no identifier never becomes a record called `"null"` | `tools/test_nokey.py`; 4 of its 11 checks fail against the previous build, reproducing the reported symptoms exactly |
  | A new row arrives with the next id and a neutral 1.00 weight | `tools/test_newrow.py`; ids one past the highest, `milestone_seq` within its own project |
  | A row of nothing but supplied values is still empty | same file; Save will not promote it and Export will not write it |
  | Every scroll region shades the edges that have more | same file; and the shade goes the moment that edge is reached |
  | Save derives the project window and team size from the rows beneath | `tools/test_derive.py`; 7 of its 10 checks fail against the previous build |
  | An override window names its project and role before the assignment is saved | same file |
  | The horizon re-fits to whatever the filters leave, and stays put when they leave nothing | `tools/test_filters.py` |
  | Every pending change is listed with its time, place and before/after | same file |
  | A filter takes several values, and they are an OR within one filter | `tools/test_filters.py` |
  | Auto derivation matches the plan's rule term by term | `tools/test_generate.py`, on a project built to exercise every branch |
  | What the two generators produce stays editable, and is undone by Leave without change | same file |
  | Every figure in a hand-built plan matches the formula worked by hand | same file, on all 27 person-months |
  | The blank start's reference grid has no gaps | same file; 56 standard weights and 289 role factors, so nothing falls back to 1.00 unnoticed |
  | The command line and the browser agree, rule for rule and figure for figure | `tools/test_interop.py`; same findings at the same severities, every person-month equal to 1e-6, on both fixtures |
  | `xlsx → json → xlsx → json` reproduces every cell | same file; 1,459 and 588 rows |
  | A mistyped column name is refused, not ignored | same file; both implementations name the column |
  | The generated contract is the real schema | `check_consistency.py`; columns, value lists and rules held against the template and the plan |

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

  Gate 4 round 25 (app v1.24): **multi-value filters, and two generators on the project
  tab.**

  - **Every filter now takes several values at once** — a drop-down of tick boxes built on
    `<details>`, which gives open, close, keyboard operation and focus for nothing. Nothing
    ticked means **All**; one reads as that value; more reads as a count with the full list
    on hover. Values *within* one filter are an **OR** (ticking a second project type
    widens the view) while the filters remain an **AND** with each other. Each has its own
    **Clear**, and **Reset** still empties them all.
  - **Auto derivation** in the Periods section builds a project's periods from its
    milestones by the rule on sheet 05 of the plan.
  - **Blank list** in the Milestones section lays out the ten standard milestone names
    with their dates empty, so only the dates have to be typed.

  Both generators produce **ordinary rows** — provisional until Save, editable and
  deletable afterwards, subject to every rule — because the point is to save the typing,
  not to take the decision away. Auto derivation reads the milestones from the raw sheet,
  so a set just typed and not yet saved still counts; it asks before replacing an existing
  set; and it refuses what it cannot do, naming the reason (an `Others` project, or a
  trial missing CTA submission or a DB lock — V-16). Blank list does not repeat a name
  already listed, since a second `CTA submission` is the duplicate V-20 exists to catch.

  **A latent crash was found while testing them and fixed.** Clicking a row that had not
  been saved yet made its identifier the selection, and the detail panels below need a
  *record* — dates, a name, a calculation — which a draft has none of. `projDetail` threw,
  taking the whole re-render with it, so the click appeared to do nothing at all. Both
  detail panels now fall back to the scratch panels built for exactly that state.

  Gate 4 round 24 (app v1.23): **the filter bar, and what the unsaved-change counter can
  tell you.**

  - **Outsourcing type joins the filter conditions**, driving the same machinery as the
    other six — the charts, both Overall tables and the source-data tabs — and **Reset**
    puts it back with the rest.
  - **The horizon now follows the filters.** Narrowing to one project type left the window
    the whole portfolio needed, so a two-year span went mostly empty and the reader was
    looking at a chart of nothing with no way to tell whether that was the answer or the
    view. Changing a filter pulls **From** and **To** in to the months the surviving rows
    actually reach. Two things are deliberately left alone: a combination matching
    *nothing* keeps the window where it was (jumping to an arbitrary span would hide the
    reason the screen is empty), and typing in From or To is the user moving the window
    themselves — the re-fit runs only when a filter *dropdown* moves.
  - **A Show details button** beside the counter opens every change waiting to be saved:
    the time it happened, which tab, which section, which row, which item, what it was
    and what it is now. Newest first, because the question it answers is almost always
    *"what did I just do"*. The dialog closes, goes full screen, and scrolls with the same
    visible bar and edge shading as every other scroll region.

  The section column shows the name the panel goes by on screen rather than the sheet
  name, because the point of the log is being able to walk back to the thing you changed.

  Gate 4 round 23 (app v1.22): **four values that were typed by hand while the rows
  underneath already said what they should be.**

  - **A project's window is recalculated on Save**: `start_date` becomes the earliest of
    its milestone dates, `end_date` the latest, and `total_period_months` follows.
  - **`planned_member_count` becomes the number of distinct people assigned** — people,
    not assignment rows, since one person may hold several.
  - **A new row in Periods takes the next `period_seq`** for that project. (The request
    named a `period_id`; the sheet has none — it is keyed on `project_id + period_name`
    per change R-11, and `period_seq` is the field that carries the order.)
  - **A weight-override window shows the project and role of its assignment even before
    that assignment is saved.** It read them from the validated model, which excludes
    anything still being entered, so both columns went blank until Save — and they exist
    precisely so that, while typing, you can confirm the window is attached to the right
    piece of work.

  The first two happen at **Save**, not at load: doing them at load would rewrite a
  workbook produced elsewhere the moment somebody opened it, and the delivered examples
  set a project start before its first milestone quite legitimately. Two guards keep the
  change from destroying information — a project with no milestone dates keeps the window
  that was typed, and a project with no assignments keeps the team size that was typed,
  because *"nobody is assigned yet"* is not the statement *"this needs nobody"*.

  **One consequence is worth stating.** A project now ends at its last milestone, so work
  that legitimately continues past the final DB lock — close-out, archiving, an inspection
  — has to be carried by a milestone if it is to sit inside the window, and an assignment
  running past it is reported as V-07. The period derivation already allowed for that
  headroom by running `Close-out (final)` to the later of the DB lock and the project end;
  deriving the end from the milestones removes it.

  Gate 4 round 22 (app v1.21): **what a new row arrives with, and whether you can tell
  there is more to see.**

  - **Identifiers are allocated on insert** for `project_id`, `person_id` and
    `milestone_seq` as well as `assignment_id` — **one past the highest** already in the
    sheet, so a row added today reads as the newest. `milestone_seq` counts within its own
    *project*, not across the file, because that is the list it orders. (The old rule took
    the smallest *unused* number, which was about tidiness; a gap left by a deleted row
    now stays a gap, as an identifier sequence does everywhere else.)
  - **Weights start at 1.00** — `ProjectPeriod.weight`, `Person.capacity_fte`,
    `Assignment.person_weight`, `PersonPeriodWeight.weight_override`. 1.00 is the neutral
    multiplier, and the alternative is not "no value" but **zero**: an empty weight reads
    as 0.00 in the calculation, so a row left alone contributed nothing at all and nothing
    on screen said so. A row that contributes too much gets noticed; one that contributes
    nothing does not.
  - **Scroll regions now say which way there is more.** Every section was already bounded
    on both axes, but `scrollbar-width:thin` bought a browser *overlay* bar that occupies
    no layout space and fades when idle — measured, `offsetWidth === clientWidth` — so a
    table with eleven columns off to the right looked exactly like one with none. The bar
    is now a real 12px with a visible thumb; and because overlay scrollbars are the default
    on some platforms whatever the CSS asks for, each region **also** carries a soft shade
    on any edge that has content beyond it, drawn over the box so table rows cannot paint
    on top of it, and removed the moment that edge is reached.

  The first two needed a second concept alongside "blank": a row carrying only the values
  the *application* put there is still an empty row, so **Save does not promote it and
  Export will not write it** — otherwise every insert would immediately become a
  half-record complaining about what it is missing.

  Gate 4 round 21 (app v1.20): **a row with no identifier is no longer treated as a
  record** — one cause behind three reported faults.

  A project saved with every field filled in *except* `project_id` was indexed as
  `M.projects[null]`, and JavaScript turns a null key into the **string** `"null"`. The
  application then believed in a project called `"null"`: it became the selection, and the
  row filter — which keeps a row when the set of visible `project_id`s contains it —
  compared the set `{"null"}` against the row's actual `null` and missed. So the Projects
  table the user had just typed into reported *"No rows. Use + row to add one."* The
  Milestones and Periods sections beneath went looking for a parent named `"null"`, found
  none, and said the same. A person saved without a `person_id` did exactly the same,
  which is why the Assignments and Weight overrides sections beneath them offered nothing
  to fill in.

  The rule is now explicit: **a row becomes a record when it carries its sheet's
  identifier, and not before.** Until then it is not indexed, it is reported as an error
  naming the column to fill in, and **Save is refused** rather than silently creating the
  phantom — which matches the export guard, that has always refused to write such a row.
  Crucially the row *stays on screen*, because it is the row being repaired: both master
  tables keep any keyless row alongside the real ones, and a child table now shows a row
  carrying no parent key wherever the user is — a row that cannot be seen cannot be
  repaired or deleted, only silently dropped. Supplying the identifier recovers
  completely. The same rule went into `tools/prap_io.py`, so the command line and the page
  still report the same findings.

  Gate 4 round 20 (app v1.19): **scroll position survives a re-render.** Committing a cell
  re-renders the panel it lives in, and a freshly built element starts at the top left — so
  filling one cell in a table twenty-two columns wide sent every scroll box back to the
  first row and the first column, and the next cell you meant to fill was off screen again.
  On a dashboard that is invisible; during data entry it costs a re-scroll for *every*
  cell. It surfaced as soon as a plan could be typed in from scratch, because that is the
  first time anyone fills cells one after another.

  Every scroll offset is now captured and put back around each re-render, along with the
  page's own position — which a re-render can also move, because the edit banner changes
  height between "no changes" and "*n* changes not yet saved". The key has to survive the
  DOM being rebuilt: a data table names itself by its sheet, and everything else (the
  charts) is keyed by where it sits among the other keyless boxes in its own pane. The
  same wrapper covers the three other partial redraws — selecting a parent row, selecting
  an assignment, and the matrix/rows toggle. **Changing tab still goes to the top**, because
  that is the user moving somewhere else rather than the page moving underneath them.

  Gate 4 round 19 (app v1.18): **the four child sections are enterable from the start.**
  Round 18 made a plan enterable but only in one order — the project tab showed the
  Projects table alone until a project had been saved, and the person tab the People table
  alone. Both were literally true (the detail panels need a parent *record*, and a row
  still being typed is not even parsed into the model), but the consequence was that
  Milestones, Periods, Assignments and Weight overrides were invisible to anyone building
  their first plan. **A section that appears only after you have done something else reads
  as a section that does not exist.**

  So the tables are drawn from the start, in the same two-column arrangement they have
  when a workbook is loaded, in three states:

  - **No parent at all** — locked, with the reason where the **+ row** button would be. A
    child row whose parent does not exist has nothing to attach to and would be dropped
    when the file is read back; saying so beats offering a button that creates a row
    nobody can rescue.
  - **The parent row carries an identifier** (*before* it is saved) — unlocked and scoped
    to it, so a plan can be entered the way a person thinks about one: the project and its
    milestones together, the person and their assignments together, each committed in a
    single **Save**.
  - **The parent is saved** — the full detail panel as before, timeline and charts included.

  Two fixes were needed for that to work. The draft row now becomes the tab's *selection*,
  since child rows inherit their parent key from the selection and without it they were
  created parentless. And the fallback that finds the assignment for a new override row
  now reads the raw sheet rather than the validated array — the validated array excludes
  anything still being entered, so on a plan being typed from scratch the only assignment
  on screen was not found.

  Gate 4 round 18 (app v1.17): **a plan can now be started in the application itself.**
  The landing screen offers two ways in, given equal weight — load a source workbook, or
  start blank and type. **Start blank** opens every tab and section an upload opens (it is
  the same code path, so it is not a lesser mode with its own rules), and the plan it
  produces exports to the same `.xlsx` as any other.

  A blank start is *not* an empty workbook. With no `Lists` sheet there is no vocabulary,
  so every typed value is reported as unrecognised (V-11) and no field can offer a choice;
  with no `Config` there are no thresholds. So it begins from the reference content of the
  delivered template — embedded by `tools/build_app_seed.py`, held to the template by
  `check_consistency.py`. The `PeriodWeightStandard` and `RoleFactor` grids are *not*
  embedded: the application builds them from the value lists it was just seeded with (56
  standard weights, 289 role factors, every combination a project can reach), so a company
  that adds a role to `Lists` gets it without anybody regenerating anything. Every seeded
  figure is a placeholder **1.00** that says so on its own row — an invented weight that
  looks like a company standard is worse than an obvious placeholder, because only one of
  the two gets questioned.

  Four things had to be fixed before the path worked at all, each found by walking it
  rather than by reading it:

  - **A deadlock at the first save.** A clinical trial saved before its milestones exist
    raises V-16 by definition — and its milestones cannot be entered until it is saved,
    because the milestone table hangs off a *selected* project. The save guard now treats
    V-12 and V-16 as **incompleteness** rather than error (the same line the specification
    already draws for drafts), names what is still missing in the banner, and refuses
    everything else exactly as before.
  - **A row still being typed is not yet parsed into the model**, so on a plan with no
    saved projects the Projects table said "nothing matches the filters" and hid the very
    row the user was filling in.
  - **The first assignment was the one row the application refused to name**, having named
    every one after it: `nextKey` had no house style to copy, so the sheets that allocate
    their own keys now carry a pattern to start from.
  - **Five `Project` columns had no home anywhere in the application.** The project and
    people tables showed a curated subset — survivable while every plan arrived as a
    workbook filled in elsewhere, not survivable now that a plan can be built here, because
    `DataReviewSystem_setup` could never be entered and V-10 would warn about it forever.
    Both tables now carry every column the schema lets a user type into.

  Also: a person with no assignment yet is listed on the person tab — the state everybody
  is in for the minute after they are created — and the default horizon no longer anchors
  to year 0 when nothing has been calculated.

  Gate 4 round 17 (app v1.16): **reference material for another AI system**, and an
  interoperability audit of everything delivered so far. The audit found one structural
  problem: of the files in this repository, 72 were `.xlsx` and 2 were Markdown. The
  schema, the value lists, the formula and the twenty-four validation rules existed only
  inside a ZIP of XML or inside the application's own JavaScript — readable by a person
  with Excel, and by nothing else. Four things close that.

  - `docs/PRAP_AI_Agent_Guide.md` — the guide an agent reads: what it may change, what
    it must not, how to check its own work, and what to say when it hands it over. Also
    issued as `docs/PRAP_AI_Agent_Guide_v1.0.xlsx` for human review.
  - `docs/prap_contract.json` — the same facts as data: every column with its type and
    meaning, the value lists, the Config parameters, the formula term by term, the period
    derivation, all 25 rules with the severity the application actually reports, the
    interchange format and the task recipes. **Generated** from the template builder, the
    plan's own rule table and the application source, so it cannot drift.
  - **A JSON interchange format.** The whole workbook as row objects keyed by column
    name, dates as `yyyy-mm-dd`. The application loads it and exports it, and
    `tools/prap_io.py` converts either way — so an agent that cannot write a ZIP of XML
    can still produce a file PRAP opens.
  - `tools/prap_io.py` also **validates and calculates** from the command line, running
    the same rules and the same formula as the page, so an agent can check its own draft
    without a browser. `tools/test_interop.py` holds the two implementations to each
    other.

  The audit also found a rule the documents promised and the code did not keep: **V-14**
  has been in the data model since v1.0 and the application never reported it. It does
  now — a milestone outside its project's window, or a boundary milestone out of order —
  with the one exception that is legitimate rather than merely noisy: an `Inspection`
  after the final DB lock, reported as *information*, because the derivation deliberately
  extends the timeline to reach it.

  Gate 4 round 16 (app v1.15): a **visual design pass** over the whole interface, taking
  Apple's HIG as the reference. The stylesheet is rebuilt around tokens — one palette,
  one type scale, one radius scale, one motion curve — so nothing is chosen by eye at the
  point of use. White cards on a grey field, separated by shadow rather than outline;
  translucent, blurred sticky bars; a segmented tab control; filled/tinted/plain buttons;
  and colour that means something (blue interactive, red over the ceiling, amber under
  the floor). Chart series colours are unchanged — there the colour *is* the data.
  Contrast is now measured rather than judged: `tools/test_contrast.py` composites every
  text colour onto the surface it actually sits on and applies WCAG AA at the rendered
  size. The previous design had five colours below AA; this one has none.

  Gate 4 round 15 (app v1.14, template v1.7, dummies v1.9 / v1.1): **derived columns in
  the source workbook are locked**, with a note on each heading. A green fill is a
  convention the reader has to have been told about, and the telling is on a README sheet
  they may never open; a lock is the file itself refusing the edit at the moment it is
  attempted. The export writes the same locks. `check_consistency.py` verifies all of it
  against the plan's data model — which surfaced a gap the change had to close:
  `Milestone.project_name` and `Assignment.person_name` were typed `Text` although the
  application recomputes both on import and reports disagreement as V-13. They are typed
  `Derived` now, which is what they have always been.

  Gate 4 round 14 (app v1.13): a **line chart** of monthly resource stands as the first
  panel of every data tab — one coloured line per project on Overall and the project tab,
  one per person on the person tab, each keeping the colour it carries elsewhere. The
  stacked charts say what a month's total is *made of*; they cannot say whether one series
  is rising or falling, because in a stack every band's baseline moves with the bands
  beneath it. Each line reports its total, mean and peak month, capped at the twelve
  largest. Plus a **design pass**: the summary tiles move to the top of Overall, and every
  panel now carries one header shape — title left, what it covers right — where scope had
  been stated three different ways or not at all.

  Gate 4 round 13 (app v1.12): `PersonPeriodWeight` is treated as what the schema says it
  is — a **child of Assignment**. On the person tab the overrides table now follows the
  assignment *selected* above it, exactly as Milestones and Periods follow the project
  selected above them. Clicking an assignment redraws the overrides to that assignment's
  windows and no others, and a new override row is seeded with it. Scoping to the person
  instead listed every window that person carries across every project at once. Both
  headings name the person, and the overrides panel restates the assignment it belongs
  to: identifier, project, role, dates and weight.

  Gate 4 round 12 (app v1.11): the Overall tab's *Mean load per person* becomes
  **Monthly demand by person** — the same months as *Monthly demand by project* directly
  above, cut the other way, one stacked band per person. The two total the same figure
  every month, and that is now a check rather than a claim. A segment is outlined where
  that person's own month crosses the ceiling or floor, so the flag never rests on fill
  colour (which here already means *which person*). **Utilisation** on the project tab is
  stacked by person on the same terms. And a **defect**: a row drafted on one person's tab
  appeared on every other person's tab — on *Weight overrides*, whose project and role
  columns are looked up *from* the assignment, such a row then described someone else's
  work. A draft is now admitted only while its parent key is empty.

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

- `templates/PRAP_SourceData_Template_v1.7.xlsx` — blank workbook: 10 sheets, headers,
  value lists, dropdowns, one example row per sheet, colour-coded README. Every sheet
  carries at least one free-text note column (schema version 5).

  **Derived columns are locked.** Three columns are computed rather than entered —
  `Project.total_period_months`, `Milestone.project_name`, `Assignment.person_name`. Their
  cells are locked and every other cell is explicitly unlocked, so typing into one is
  refused where it happens instead of going wrong later; each carries a note on its
  heading saying why. There is no password — it is a guard rail, not security — and
  inserting, deleting and sorting rows all still work. Only adding or removing *columns*
  is blocked, because the column set is the schema. The application's export writes the
  same locks, so the guard rail survives a round trip.
- `templates/PRAP_SourceData_Dummy_v1.9.xlsx` — the same structure populated with
  **34 NewDrug CT + 16 Biosimilar CT + 12 `Others` projects and 20 people**
  (289 assignments, 372 milestones, 308 periods across 73 months).
- `templates/PRAP_SourceData_Dummy_10x10_v1.1.xlsx` — the same again at **10 projects
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
python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_10x10_v1.1.xlsx
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

And check that no text colour is harder to read than it looks:

```bash
python tools/test_contrast.py
```

That composites each colour onto the surface it actually sits on — alpha and all — and
applies WCAG AA at the size the text is really rendered at, in light and dark.

And check the two source-data charts against the model behind them:

```bash
python tools/test_charts.py
```

That counts the bands and markers on the project timeline against the periods and
milestones in the data, and adds up the stacked utilisation segments month by month to
confirm they equal the person-month the calculation holds — a chart that disagrees with
the table is worse than no chart.

And check the two generators on the project tab:

```bash
python tools/test_generate.py
```

That builds a project whose milestones exercise every branch of the rule — a protocol
date, a First SIV, an interim lock earlier than the final one, and an inspection after it
— and checks each of the seven periods it derives against the rule, term by term.

And check the filter bar, the horizon that follows it, and the change log:

```bash
python tools/test_filters.py
```

And check what Save recalculates from the rows beneath a project:

```bash
python tools/test_derive.py
```

That builds a project whose typed window is deliberately wrong, adds four milestones, and
checks the window is pulled to their span and `total_period_months` follows; that
`planned_member_count` becomes the number of distinct people assigned; that both are left
alone when there is nothing to derive them from; and that an override window names its
project and role while the assignment above it is still a draft. Seven of its ten checks
fail against the previous build.

And check what a new row arrives with, and that every panel says where the rest of it is:

```bash
python tools/test_newrow.py
```

And check that a half-filled row cannot turn into a phantom record:

```bash
python tools/test_nokey.py
```

That covers a project, a person, and a workbook that already carries such a row. Four of
its eleven checks fail against the previous build, reproducing the reported symptoms
exactly — *0 rows on screen*, `projects=['null']`, and *"No rows. Use + row to add one."*

And check that nothing but the user moves a scroll position:

```bash
python tools/test_scroll.py
```

That checks all four commit paths (Enter, blur, insert, Save), the page's own scroll, a
row 900px down a 289-row table, and that the cell just filled is still on screen
afterwards. Five of its eleven checks fail against the previous build. The test itself
needed care: Playwright's own click scrolls its target into view first, and Chromium's
`scrollIntoView` scrolls *every* scrollable ancestor — so a naive click on an off-screen
cell moves the box before the application has run a line, and the first draft was
measuring the driver rather than the page.

And check that a plan can be built from nothing at all, which is the path with no file
behind it to fall back on:

```bash
python tools/test_blank.py
```

That never touches a fixture. It clicks **Start blank** and does what a person would do,
in the order they would do it — a project, its milestones *before* the project is saved, a
person, an assignment *before* the person is saved, and a weight override window. It
checks each child inherited the right foreign key, that the periods derived, that every
one of the 27 monthly figures equals the formula worked by hand, that the override
replaces the weight for its three months and no others, and that the exported workbook
reproduces the plan on re-import.

And check that the command-line tools and the browser still agree, which is the whole
basis for telling another AI system it can validate a draft without opening the app:

```bash
python tools/test_interop.py
```

That round-trips both worked examples `xlsx → json → xlsx → json` and compares every
cell; loads each form into the real browser and compares the model it builds; holds
`prap_io.py`'s findings against the page's, rule for rule and severity for severity;
compares every person-month to 1e-6; re-loads the application's own **Export JSON**;
and confirms a mistyped column name is *refused and named* by both implementations
rather than silently dropped.

And check the documents still describe the artifacts they claim to:

```bash
python tools/check_consistency.py
```

That cross-checks 64 documented columns against the template's real headers, the
schema version across all four files, the `project_type` values, every `Config`
default the specification quotes against the value the template actually holds, all 69
requirements plan-to-specification in both directions, that no build markers were
left in a shipped workbook, and that `docs/prap_contract.json` still describes the real
schema — its columns against the template's headers, its value lists against the
template's `Lists` sheet, its rules against the plan's data model, and every file the
manifest points at against its recorded sha256.

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
