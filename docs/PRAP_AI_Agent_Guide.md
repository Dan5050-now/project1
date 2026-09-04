# PRAP — reference for an AI agent

**Project Resource Assignment Program.** A single-file offline HTML application that simulates monthly resource demand across simultaneously running projects — per project and per person. The data lives in an Excel workbook next to it; the workbook is the archive of record, and the application never writes to it.

This document is written for a language model or an agent, not for a person. It tells you what you may change, what you must not, how to check your own work before handing it over, and what to say when you do. Its machine-readable half is `docs/prap_contract.json` — the same facts as JSON, generated from the same sources. Read whichever suits you; they cannot disagree.

|  |  |
|---|---|
| Application | `app/PRAP.html` v1.39 |
| Source schema version | 11 |
| Contract version | 1.0 |
| Guide version | 1.0 |
| Generated | 2026-09-04 |

---

## 0. If you read nothing else

```
# read a workbook as plain text
python tools/prap_io.py to-json  data.xlsx  -o data.prap.json

# edit data.prap.json  (row objects keyed by column name; dates yyyy-mm-dd)

# check it before anyone sees it
python tools/prap_io.py validate  data.prap.json
python tools/prap_io.py calculate data.prap.json --by person --flags

# hand back a workbook
python tools/prap_io.py to-xlsx   data.prap.json -o data_draft.xlsx
```

Seven rules that account for most mistakes:

- **Never overwrite the user's workbook.** Always deliver a new file.
- **Never invent a value from a controlled list** — role names, period names, statuses, systems and phases all come from the `Lists` sheet (§4).
- **Never write a derived column** (§3.3). It is recomputed on load and your value is discarded.
- **One assignment per (person, project, role).** A changing workload is a `PersonPeriodWeight` window, not a second assignment (§5.3).
- **A weight override replaces the person weight** for the months it covers. It does not multiply it.
- **The allocation thresholds are absolute FTE**, not shares of a person's capacity (§5.4).
- **Validate before you deliver**, and say what you changed in rows.

## 1. The system in one page

```
  Excel workbook (.xlsx)  ──load──▶  app/PRAP.html  ──export──▶  new .xlsx
  or .prap.json (text)                in a browser                or .prap.json
                                     offline, no server
```

- The application is **one HTML file**. Opening it in a browser is the whole installation. It makes no network requests, so a file dropped on it never leaves the machine.
- **There are two ways in**, and the second one changes what you may assume about a file you are handed:
  - *load a file* — Drop a .xlsx workbook or a .prap.json file on the page. This is the path for anything you produce.
  - *start blank* — 'Start blank' begins a plan with nothing in it but the standard value lists and settings, and opens every tab for typing. It is how someone plans from scratch without a workbook.
  - *what blank contains* — The Lists and Config sheets of the delivered template, plus a complete PeriodFTEStandard and RoleFactor grid built from those lists - every (type, phase, period) and (type, phase, period, role) combination, so nothing silently falls back to 1.00 and V-23 never fires.
  - *placeholders* — Every seeded weight and role factor is 1.00 and says so in its note. They are NOT a company standard. If a user hands you a plan started this way, check whether those figures are still 1.00 before reading the FTE totals as real - until they are set, the load reduces to person_weight x month_coverage.
  - *both end the same* — A plan started blank exports to the same .xlsx and the same .prap.json as any other, so nothing downstream needs to know which way it began.
- **The workbook is the record.** Edits inside the application are provisional until Save, and are written nowhere until Export — which produces a *new* file stamped with the date (§6).
- **You cannot drive the application.** It has no API and no command line. What you can do is produce and check the file it reads, which is what `tools/prap_io.py` is for.

### 1.1 Which file to read

The repository keeps every issue of every document, so pick from `docs/PRAP_Manifest.json` rather than by sorting filenames. The current set:

| What | Path |
|---|---|
| Development plan | `docs/PRAP_Development_Plan_v2.41.xlsx` |
| Programming specification | `docs/PRAP_Programming_Specification_v1.15.xlsx` |
| UI component list | `docs/PRAP_UI_Component_List_v1.0.xlsx` |
| Source data template | `templates/PRAP_SourceData_Template_v1.14.xlsx` |
| Worked example (62 projects, 20 people) | `templates/PRAP_SourceData_Dummy_v1.16.xlsx` |
| Worked example (10 projects, 10 people) | `templates/PRAP_SourceData_Dummy_10x10_v1.8.xlsx` |
| This guide | `docs/PRAP_AI_Agent_Guide.md` |

## 2. The eight words you need

| Term | Meaning |
|---|---|
| Project | A study or piece of work with a start, an end and a type. `NewDrug CT` and `Biosimilar CT` are clinical trials; `Others` is everything else, and the two kinds have different period sets and different role lists. |
| Milestone | A dated event in a project. Ten standard names. Two of them — `CTA submission` and a DB lock — are what the period derivation hangs on. |
| Period | A named stretch of a project carrying an effort `weight`. A clinical trial has up to seven; an `Others` project has three. |
| Person | Someone who can be assigned, with a `capacity_fte`. |
| Assignment | One person on one project in one role, between two dates, at a `person_weight`. |
| Weight override | A `PersonPeriodWeight` window that REPLACES `person_weight` for the months it covers. |
| Role factor | What one person in a role costs a project per month, before their own weight. Keyed on type, phase, period and role. |
| FTE | The unit of everything. 1.00 FTE = 160 hours per month. |

## 3. The data model

Ten sheets, all required, in this order. A missing sheet is fatal (V-00).

| Sheet | Role | Parent | Key | Columns |
|---|---|---|---|---|
| `Project` | master | — | `project_id` | 25 |
| `Milestone` | child | `Project` | `project_id`, `milestone_name`, `milestone_date` | 6 |
| `ProjectPeriod` | child | `Project` | `project_id`, `period_name` | 7 |
| `PeriodFTEStandard` | reference | — | `project_type`, `clinical_phase`, `work_scope_type`, `period_name` | 6 |
| `RoleFactor` | reference | — | `project_type`, `clinical_phase`, `work_scope_type`, `period_name`, `role_name` | 8 |
| `Person` | master | — | `person_id` | 12 |
| `Assignment` | child | `Person` | `assignment_id` | 12 |
| `PersonPeriodWeight` | child | `Assignment` | `assignment_id`, `period_start` | 5 |
| `MonthlyEstimate` | child | `Project\|Assignment` | `scope`, `ref_id`, `month` | 6 |
| `Lists` | vocabulary | — | `list_name`, `value` | 3 |
| `Config` | settings | — | `parameter` | 3 |

```
Project ──┬── Milestone
          ├── ProjectPeriod
          └── Assignment ── PersonPeriodWeight
Person  ──────┘

PeriodFTEStandard, RoleFactor   reference tables, keyed on type/phase/period
Lists, Config                      vocabulary and settings
```

### 3.1 Columns

#### `Project`

| Column | Type | Meaning |
|---|---|---|
| `project_id` | identifier | Unique key, e.g. PRJ-001. |
| `project_name` | identifier | Unique display name. |
| `project_type` | text · list `project_type` | 'NewDrug CT', 'Biosimilar CT (Healthy)', 'Biosimilar CT (Patient)' or 'Others'. Everything but 'Others' is a clinical trial. |
| `project_category` | text | Product name. Required for either clinical trial type. |
| `clinical_phase` | text · list `clinical_phase` | Required for any clinical trial type - with the type and the work scope it selects the period weights. |
| `work_scope_type` | text · list `work_scope_type` | How much of the work is done in-house. With the type and phase it selects the standard weights and role factors. |
| `outsourcing_scope_det` | text | FREE TEXT. What is outsourced and to whom, in your own words - the detail behind work_scope_type. Read by people, never by the calculation. |
| `EDC_setup` | text · list `setup_party` | Who sets up EDC. Clinical trial types only. |
| `DataReviewSystem_setup` | text · list `setup_party` | Who sets up the data review system. |
| `RBQM_setup` | text · list `setup_party` | Who sets up RBQM. |
| `DM_conduct` | text · list `setup_party` | Who reviews the data. |
| `EDC_system` | text · list `EDC_system` | EDC system in use. |
| `DataReviewSystem` | text · list `DataReviewSystem` | Data review system in use. |
| `RBQM_system` | text · list `RBQM_system` | RBQM system in use. |
| `planned_member_count` | text | Planned team size; compared against actual assignments. |
| `start_date` | date | Project start. |
| `end_date` | date | Planned project end. |
| `total_period_months` | derived · **do not write** | DERIVED - formula, do not type. |
| `status` | text · list `project_status` | Planned / Active / On hold / Completed. |
| `estimation_type` | text | 'automatic' (default) or 'manual'. Manual means the monthly FTE for THIS PROJECT is stated on MonthlyEstimate rather than calculated, and the people assigned that month are scaled to add up to it. |
| `note_1` | text | Free text. |
| `note_2` | text |  |
| `note_3` | text |  |
| `note_4` | text |  |
| `note_5` | text |  |

#### `Milestone`

| Column | Type | Meaning |
|---|---|---|
| `project_id` | identifier | Foreign key to Project. |
| `project_name` | derived · **do not write** | DERIVED - looked up from Project, do not type. |
| `milestone_name` | text · list `milestone_name` | From the standard list of ten. 'Inspection' may appear on several rows. |
| `milestone_date` | date | Planned date. |
| `milestone_seq` | text | Display order on the timeline. |
| `note_1` | text | Free text. e.g. why a date moved, or which inspection body. |

#### `ProjectPeriod`

| Column | Type | Meaning |
|---|---|---|
| `project_id` | identifier | Foreign key to Project. |
| `period_name` | identifier | From the set for this project's type. UNIQUE within a project, so (project_id, period_name) is the key (R-11). |
| `period_seq` | text | Orders periods along the timeline. Unique within a project. |
| `period_start` | date | Inclusive. |
| `period_end` | date | Inclusive. Periods must not overlap or leave a gap. |
| `weight` | text | THIS PROJECT'S OWN ADJUSTMENT to the standard for its type, phase and scope (REQ-CAL-19). 1.00 means an ordinary project of its kind; 1.20 means this one takes a fifth more. It does NOT carry the magnitude - PeriodFTEStandard.standard_fte does. |
| `note_1` | text | Free text. e.g. why a derived date was overridden by hand. |

#### `PeriodFTEStandard`

| Column | Type | Meaning |
|---|---|---|
| `project_type` | identifier · list `project_type` | A clinical trial type. 'Others' projects take manual weights instead. |
| `clinical_phase` | identifier · list `clinical_phase` | The phase this standard applies to. |
| `work_scope_type` | identifier · list `work_scope_type` | The work scope this standard applies to. LEAVE EMPTY for a row that applies to EVERY scope - fill only the scopes that really differ. |
| `period_name` | identifier · list `period_name_clinical` | One of the seven clinical periods. Unique within a project (R-11). |
| `standard_fte` | decimal | YOU SUPPLY. The STANDARD MONTHLY FTE a project of this type, phase and scope takes in this period - a magnitude, not a multiplier. 4.02 means the period costs about four full-time people a month. The project's own ProjectPeriod.weight then adjusts it up or down for that particular study, and the role factors divide it between the roles staffed. |
| `note_1` | text | Free text. e.g. the basis for this weight. |

#### `RoleFactor`

| Column | Type | Meaning |
|---|---|---|
| `project_type` | identifier · list `project_type` | Which type's role list this row belongs to. |
| `clinical_phase` | identifier · list `clinical_phase` | The phase this factor applies to. Leave EMPTY for 'Others'. |
| `work_scope_type` | identifier · list `work_scope_type` | The work scope this factor applies to. LEAVE EMPTY for a row that applies to EVERY scope - fill only the scopes that really differ. |
| `period_name` | identifier | The period this factor applies to. |
| `role_name` | identifier | The role. |
| `role_factor` | decimal | YOU SUPPLY. Relative burden of this role in this period. |
| `absorbed_by` | text | If NOBODY holds this role on a project, which role picks the work up. Blank = the work is simply not counted. See the README. |
| `role_note` | text | Basis for the factor. |

#### `Person`

| Column | Type | Meaning |
|---|---|---|
| `person_id` | identifier | Unique key, e.g. PSN-001. |
| `person_name` | text | Display name. |
| `department` | text | Grouping for the dashboard. |
| `primary_role` | text | Usual role; an assignment can override it. |
| `capacity_fte` | text | Available capacity. 1.00 = full time. Lower for a part-timer. |
| `employment_start` | date | Blank = open. |
| `employment_end` | date | Blank = open. |
| `note_1` | text | Free text. |
| `note_2` | text |  |
| `note_3` | text |  |
| `note_4` | text |  |
| `note_5` | text |  |

#### `Assignment`

| Column | Type | Meaning |
|---|---|---|
| `assignment_id` | identifier | Unique key. One row per person + project + role. |
| `person_id` | identifier | Foreign key to Person. |
| `person_name` | derived · **do not write** | DERIVED - looked up from Person, do not type. |
| `project_id` | identifier | Foreign key to Project. |
| `role_name` | text | Must exist in RoleFactor for this project's type. |
| `assign_start_date` | date | Date the person joins. BLANK = the project's own start date. |
| `assign_end_date` | date | Date the person leaves. BLANK = the project's own end date. |
| `person_weight` | text | How much this person works on this project, e.g. 0.40. |
| `estimation_type` | text | 'automatic' (default) or 'manual'. Manual means the monthly FTE for THIS ASSIGNMENT is stated on MonthlyEstimate rather than calculated. |
| `note_1` | text | Free text. |
| `note_2` | text |  |
| `note_3` | text |  |

#### `PersonPeriodWeight`

| Column | Type | Meaning |
|---|---|---|
| `assignment_id` | identifier | Foreign key to Assignment. |
| `period_start` | date | Inclusive. |
| `period_end` | date | Inclusive. Windows within one assignment must not overlap. |
| `weight_override` | text | REPLACES person_weight for these months - it does not multiply it. |
| `reason` | text | Why the weight differs. |

#### `MonthlyEstimate`

| Column | Type | Meaning |
|---|---|---|
| `scope` | identifier | 'project' or 'assignment' - which of the two this figure is for. |
| `ref_id` | text | The project_id or assignment_id it belongs to, per scope. |
| `month` | text | The month, as YYYY-MM. |
| `fte` | text | The monthly FTE, STATED rather than calculated. |
| `edited_at` | text | When it was last set. The application fills this in. |
| `note_1` | text | Why this figure was stated. |

#### `Lists`

| Column | Type | Meaning |
|---|---|---|
| `list_name` | identifier | Which list this value belongs to. |
| `value` | text | A permitted value. Add a row inside the block to extend a list. |
| `note_1` | text | Free text. e.g. when a value was added, or what it means. |

#### `Config`

| Column | Type | Meaning |
|---|---|---|
| `parameter` | identifier | Setting name. |
| `value` | text | Setting value. |
| `note` | text | What it controls. |

### 3.2 Foreign keys

| From | Must exist in | Rule if it does not |
|---|---|---|
| `Milestone.project_id` | `Project.project_id` | V-01 |
| `ProjectPeriod.project_id` | `Project.project_id` | V-01 |
| `Assignment.project_id` | `Project.project_id` | V-01 |
| `Assignment.person_id` | `Person.person_id` | V-02 |
| `PersonPeriodWeight.assignment_id` | `Assignment.assignment_id` | V-24 |

Editing an identifier inside the application rewrites every row that references it. Deleting a row is refused while anything still references it, and the refusal names what does — a delete is never cascaded (V-17).

### 3.3 Derived columns — read them, never write them

| Sheet | Column | Recomputed from |
|---|---|---|
| `Project` | `total_period_months` | `end_date` − `start_date`, in whole months, inclusive |
| `Milestone` | `project_name` | the `Project` row it points at |
| `Assignment` | `person_name` | the `Person` row it points at |

(3 columns.) The application recomputes all three on every load, reports any disagreement as V-13, and then uses the master value. In the template these cells are locked and carry a comment saying so. Leave them out of a JSON file entirely — that is the clearest signal that you did not intend to set them.

### 3.4 Dates

- **accepted** — a real Excel date cell, the text yyyy-mm-dd
- **rejected** — any ambiguous format such as 03/04/2026. It is reported, never guessed at.
- **excel serial** — Serial day numbers are read against 1899-12-30, which reproduces Excel's 1900 leap-year bug. Write 45658 for 2025-01-01.
- **inclusive** — Every start/end pair in PRAP is INCLUSIVE of both endpoints.
- **timezone** — All dates are handled as UTC calendar dates. There are no times.
- **json** — In the JSON interchange format always write dates as the string yyyy-mm-dd.

## 4. Value lists

These live on the `Lists` sheet of the workbook you are given — read them from there, because a company may have added values. The delivered set is:

| List | Values |
|---|---|
| `project_type` | `NewDrug CT`, `Biosimilar CT (Healthy)`, `Biosimilar CT (Patient)`, `Others` |
| `clinical_phase` | `Phase 1`, `Phase 2`, `Phase 3`, `Phase 4` |
| `work_scope_type` | `fully in-housed`, `fully outsourced`, `Partially outsourced (in-house for EDC)` |
| `setup_party` | `by CRO`, `by SB` |
| `EDC_system` | `Veeva EDC`, `Rave`, `eSOURCE` |
| `DataReviewSystem` | `Veeva DQS`, `Medidata CDS`, `No system (manual)` |
| `RBQM_system` | `CluePoints`, `Medidata CDS`, `No system (manual)` |
| `project_status` | `Planned`, `Active`, `On hold`, `Completed` |
| `milestone_name` | `Protocol (v1)`, `CTA submission`, `FPI`, `First SIV`, `LPI`, `interim DB lock cut-off`, `interim DB lock`, `final DB lock cut-off`, `final DB lock`, `Inspection` |
| `period_name_clinical` | `Before-Start-up`, `Start-up`, `Conduct (interim)`, `Close-out (interim)`, `Conduct (final)`, `Close-out (final)`, `After Close-out (final)` |
| `period_name_others` | `Planning`, `Develop`, `Close` |
| `role_clinical` | `Project oversight`, `Lead data manager`, `Clinical Data Associator`, `Clinical Database Programmer`, `Data Analyst` |
| `role_others` | `Project lead`, `Main staff`, `Other staff` |

A value outside its list is kept and reported (V-11), never dropped — so a mistake of yours reaches the user as a warning rather than as missing data. That is not a licence to invent values.

Note which list applies where: `role_clinical` for `NewDrug CT` and `Biosimilar CT`, `role_others` for `Others`; likewise `period_name_clinical` against `period_name_others`. Using a clinical role on an `Others` project is V-03, an error.

## 5. How the numbers are produced

### 5.1 The formula

```
monthly_load_fte = period_weight x role_factor x person_weight x month_coverage
```

Evaluated for every (assignment, calendar month) pair the assignment covers, in FTE.

| Term | Where it comes from |
|---|---|
| `period_weight` | ProjectPeriod.weight of the period containing the FIRST DAY of the month, for the assignment's project. A month in no period uses 1.00 and is reported under V-12. |
| `role_factor` | RoleFactor.role_factor for (project_type, clinical_phase, period_name, role_name). clinical_phase is null for 'Others' projects. A missing factor is an error under V-23 - the calculation would otherwise silently use 1.00. |
| `person_weight` | Assignment.person_weight, UNLESS a PersonPeriodWeight window contains the first day of the month, in which case weight_override REPLACES it. It does not multiply it. |
| `month_coverage` | the fraction of that calendar month's days the assignment actually spans, inclusive of both end dates: (min(month_end, assign_end) - max(month_start, assign_start) + 1 days) / days_in_month. |

**Assignment window** — assign_start_date .. assign_end_date. An empty assign_end_date means the project's end_date.

**Aggregation**

- per project per month  - sum over that project's assignments
- per person per month   - sum over that person's assignments (this is what the over/under-allocation thresholds are compared against)
- per project per person per role per month - the finest cell the dashboard shows

### 5.2 Worked example

A person on `Phase 2` `NewDrug CT`, role `Lead data manager`, `person_weight` 0.40, assigned 2026-03-10 to 2026-12-31, in a month whose period carries weight 1.20 and whose role factor is 0.90:

```
March 2026    coverage = (31 − 10 + 1) / 31 = 0.7097
              load     = 1.20 × 0.90 × 0.40 × 0.7097 = 0.3066 FTE
April 2026    coverage = 1.0
              load     = 1.20 × 0.90 × 0.40 × 1.0    = 0.4320 FTE
```

Both endpoints are inclusive, which is why March counts 22 days and not 21.

### 5.3 Periods

| Project type | Period set |
|---|---|
| `NewDrug CT`, `Biosimilar CT` | `Before-Start-up` → `Start-up` → `Conduct (interim)` → `Close-out (interim)` → `Conduct (final)` → `Close-out (final)` → `After Close-out (final)` |
| `Others` | `Planning` → `Develop` → `Close` |

**Derivation.** Only for a clinical-trial project (NewDrug CT / Biosimilar CT) that has NO rows on ProjectPeriod at all. Any period the file supplies is used as it stands - derivation never overrides typed data (REQ-CAL-13).

Requires: CTA submission, final DB lock (or interim DB lock in its place). V-16 error - the project has no periods and none can be computed.

1. Start-up starts the day after 'Protocol (v1)', or one month before 'CTA submission' when there is no protocol date; never before the project start.
2. Start-up ends at 'First SIV' (or 'FPI'), or four months after it began.
3. 'After Close-out (final)' opens only on an Inspection date AFTER the final DB lock. Earlier inspections are markers inside the existing periods (V-21).
4. 'Close-out (final)' starts three months before the final DB lock and runs to the day before period 7, or to the later of the DB lock and the project end.
5. With an interim DB lock earlier than the final one, the conduct stretch splits: 'Conduct (interim)' up to three months before the interim lock, 'Close-out (interim)' to the interim lock, then 'Conduct (final)'.
6. Without an interim lock there is one 'Conduct (final)' stretch.
7. A period squeezed to nothing is omitted, and the remainder is renumbered from 1 (REQ-CAL-12, decision C-11).

'Others' projects are never derived. Enter their three periods (Planning / Develop / Close) and their weights directly.

Periods within a project must leave **no gap and no overlap** (V-06, V-12). A month in no period is calculated at weight 1.00 and reported — which is a wrong number rather than a visible blank, so treat a V-12 warning as something to fix.

### 5.4 Thresholds

over_allocation_fte and under_allocation_fte are ABSOLUTE FTE figures. They are NOT scaled by a person's capacity_fte (decision S2-01). under_allocation_min_months consecutive months below the floor make a run; a single low month is not flagged.

| Parameter | Default | Controls |
|---|---|---|
| `schema_version` | 11 | Structure version of this workbook. The application warns on a mismatch. |
| `fte_hours_per_month` | 160 | Hours equal to 1.00 FTE: 8 h/day x 5 days/week x 20 days/month. |
| `over_allocation_fte` | 1.5 | A person-month total above this is flagged as over-allocated. Absolute, not scaled by capacity (S2-01). |
| `under_allocation_fte` | 0.6 | A person-month total below this counts toward an under-allocated run. Absolute, not scaled by capacity (S2-01). |
| `under_allocation_min_months` | 3 | Consecutive months below the threshold before a run is flagged. |
| `default_horizon_months` | 24 | Months shown when the dashboard opens. |
| `capacity_unit` | FTE | Display unit for the figures on screen. 'FTE' shows a WEIGHT: 1.00 is one person working a full month on the project and 0.50 is half of one, so ordinary values run about 0.1 to 1.0. 'hours' shows that same weight multiplied by fte_hours_per_month. Display only - it changes nothing that is stored, and no figure the calculation produces. |
| `absorb_unstaffed_role_factor` | 1 | 1 = where nobody holds a role on a project, its factor is added to the role named in RoleFactor.absorbed_by, because the work still has to be done by whoever is there. 0 = an unstaffed role simply costs nothing, which is how versions before this one behaved. |
| `split_shared_role_fte` | 1 | 1 = when several people hold the same role on one project in a month, the role factor is divided between them. 0 = each is charged the whole factor, which is how versions before this one behaved. |

Read the actual values from the `Config` sheet of the workbook in front of you; the table above is what the delivered template ships with.

## 6. What the application does with a file

- **provisional edits** — Every change made in the application is provisional. The file on disk is never touched. 'Save' commits changes into the in-memory model; 'Leave without change' reverts to the state at load.
- **export is the only write** — The application writes nothing until Export. Export produces a NEW file named <source>_<yyyy-mm-dd>, so the source workbook is never overwritten.
- **export blocked when**
  - there are unsaved pending changes - press Save or Leave without change first
  - a newly inserted row has no identifier, or has only its parent key filled in - such a row would be silently dropped on re-import
- **identifier edits cascade** — Editing project_id, person_id or assignment_id rewrites every row that references it (REQ-IMP-10).
- **deletes never cascade** — Deleting a row is refused while anything still references it, and the refusal names what does (V-17).
- **derived columns are not edited** — total_period_months, Milestone.project_name and Assignment.person_name are recomputed on every load. A value in the file that disagrees is reported (V-13) and then overwritten. In the template these cells are locked and carry a comment.
- **drafts** — A row inserted in the application is a draft until Save. Drafts are exempt from validation, because a half-typed row is incomplete rather than wrong.

The practical consequence for you: **a file you produce is never the file the user is looking at.** Say which file you wrote, and tell them to load it.

## 7. Validation rules

The application collects every finding and shows them as one report; it never stops at the first. `python tools/prap_io.py validate <file>` produces the same list without a browser, and `--json` gives it to you as data.

Severities: **fatal** nothing loads · **error** the figures would be wrong · **warning** the figures stand, the data is doubtful · **information** an explanation, not a problem.

| Rule | Severity | What it requires |
|---|---|---|
| **V-00** | fatal/error | The workbook contains all ten required sheets, and every sheet has a header row whose names match this contract. |
| **V-01** | error | Every Assignment.project_id exists in Project. |
| **V-02** | error | Every Assignment.person_id exists in Person. |
| **V-03** | error | Every Assignment.role_name appears in RoleFactor for that project's type - the coarse half of the question V-23 asks precisely. |
| **V-04** | warning | project_category is present for either clinical trial type. |
| **V-05** | error | end_date is on or after start_date, for projects, assignments and all weight periods. |
| **V-06** | error | Periods within one project, and override windows within one assignment, do not overlap. |
| **V-07** | warning | Assignment dates fall inside the project's own start and end dates. |
| **V-08** | error | project_id, person_id and assignment_id are unique in their sheet. |
| **V-09** | warning/information | schema_version in Config matches the version the application expects. |
| **V-10** | warning | Clinical-trial projects carry clinical_phase and the four *_setup values. |
| **V-11** | warning | Every list-typed value appears in the Lists sheet for its list. |
| **V-12** | error/warning | A project's periods leave no gap and no overlap across its timeline. The full set need not be present - a period may be legitimately omitted (REQ-CAL-12). |
| **V-13** | warning | Denormalised project_name / person_name match their master row. |
| **V-14** | warning/information | A milestone date falls inside its project's start..end window, and the boundary milestones appear in chronological order. Repeated 'Inspection' rows are exempt from the uniqueness part of this check. |
| **V-15** | error | A period_name belongs to the period set of its project's type. |
| **V-16** | error | A clinical trial carries the milestones the derivation needs: CTA submission, and at least one DB lock. |
| **V-17** | — | On editing an identifier, every referencing row is updated; on deleting a row, nothing may still reference it. |
| **V-18** | error | Within a project, period_name is unique, and period_seq is unique. |
| **V-19** | error | A clinical trial carries a clinical_phase, and PeriodFTEStandard has rows for that phase. Not applied to 'Others' projects, whose weights are entered directly. |
| **V-20** | warning | A milestone other than 'Inspection' appears at most once per project. |
| **V-21** | information | 'Inspection' dates on or before the final DB lock are treated as markers, not as the start of period 7. |
| **V-22** | warning | No person carries a capacity_fte below the under-allocation floor. |
| **V-23** | error | Every (project_type, clinical_phase, work_scope_type, period_name, role_name) that a PERSON-MONTH ACTUALLY LOOKED UP has a RoleFactor row. Raised BY the calculation (R-19), grouped on that whole composition, and counted in person-months affected. |
| **V-24** | error | Every PersonPeriodWeight.assignment_id exists in Assignment, and (assignment_id, period_start) is unique. |
| **V-25** | — | RETIRED at schema 7 (R-16). It reported a project whose work_scope_type contradicted its outsourcing_type. |
| **V-26** | error | No project carries a project_type that schema 6 retired - at present 'Biosimilar CT', which became 'Biosimilar CT (Healthy)' and 'Biosimilar CT (Patient)'. |
| **V-27** | error | Every clinical trial's (project_type, clinical_phase, work_scope_type) has at least one row in PeriodFTEStandard - checked on the PROJECT, not on its periods. |
| **V-28** | — | RETIRED at v2.32 (R-18), one version after it was added. It reported an assignment whose role had no RoleFactor row for that project's (project_type, clinical_phase, work_scope_type) at all. |
| **V-29** | information | A role that carries a factor, that nobody holds on the project, and that nothing covers for. |
| **V-30** | information | Config has no row for a setting the application reads, so its built-in default is in force. Reported for every such setting, naming the value being used. |
| **V-31** | error | A project or assignment set to MANUAL has months it covers that carry no MonthlyEstimate figure. Named, with the months listed. |
| **V-32** | error | A project set to MANUAL has a figure for a month in which nobody is assigned to it. |

**Aim for zero errors and zero warnings you cannot explain.** A file that loads with errors still shows numbers, and those numbers are wrong in ways the user will not see.

## 8. The JSON interchange format

A plain-text form of the source workbook, so a program or an AI agent that cannot write .xlsx can still produce a file the application loads, and can read one without a spreadsheet library.

| Field | Meaning |
|---|---|
| `prap_format` | prap-source-data  (constant - identifies the file) |
| `format_version` | 1 |
| `schema_version` | must equal the contract's schema_version |
| `sheets` | an object: sheet name -> array of row objects, keyed by column name. Column order does not matter; unknown columns are rejected so a typo cannot be mistaken for data. |

```json
{
  "prap_format": "prap-source-data",
  "format_version": 1,
  "schema_version": 5,
  "sheets": {
    "Project": [
      {
        "project_id": "PRJ-001",
        "project_name": "ONV-101 Phase 1",
        "project_type": "NewDrug CT",
        "clinical_phase": "Phase 1",
        "start_date": "2026-01-01",
        "end_date": "2028-06-30",
        "status": "Active"
      }
    ],
    "Assignment": [
      {
        "assignment_id": "ASG-001",
        "person_id": "PSN-001",
        "project_id": "PRJ-001",
        "role_name": "Project oversight",
        "assign_start_date": "2026-01-01",
        "person_weight": 0.2
      }
    ]
  }
}
```

- xlsx -> json -> xlsx reproduces every cell. Proved on both worked examples by tools/test_interop.py.
- Omit a column rather than writing `null` — an absent key and an empty cell mean the same thing, and omission reads as deliberate.
- Every one of the ten sheets must be present, even where it has no rows.
- The application loads a `.prap.json` directly (drop it on the page) and its **Export JSON** button writes one, so text and workbook are interchangeable in both directions.

## 9. Task recipes

### 9.1 Draft a resource assignment for a project from its milestones

*The user gives you a project - type, phase, dates, milestones - and asks who should work on it and how much.*

1. Read the current workbook: python tools/prap_io.py to-json <file.xlsx> -o draft.prap.json
2. Add the Project row. For a clinical trial, project_type, clinical_phase, project_category, start_date and end_date are all needed, or the project cannot be weighted (V-19, V-04).
3. Add the Milestone rows. 'CTA submission' and a DB lock are what the period derivation hangs on (V-16); the other eight names are optional markers.
4. Leave ProjectPeriod EMPTY for a clinical trial and let the application derive the seven periods. For an 'Others' project you must write Planning / Develop / Close yourself, with no gap and no overlap (V-06, V-12).
5. Choose people from the Person sheet. For each, add ONE Assignment row per (person, project, role). role_name must exist in RoleFactor for that project_type (V-03); use nextKey-style ids - the smallest unused ASG-nnn.
6. Set person_weight to the fraction of that person that goes to this project. Where the fraction changes for a stretch of months, add a PersonPeriodWeight window instead of a second assignment - the override REPLACES the weight for those months, and windows on one assignment must not overlap (V-06, V-24).
7. Check the draft: python tools/prap_io.py validate draft.prap.json
8. Look at the load it produces: python tools/prap_io.py calculate draft.prap.json --by person. Keep every person-month between under_allocation_fte and over_allocation_fte; those are absolute FTE, not shares of capacity.
9. Convert back and hand the workbook over: python tools/prap_io.py to-xlsx draft.prap.json -o <file>_draft.xlsx. Say which rows you added and why.

**Do not:**
- do not invent role names, period names, systems or statuses - every one of them comes from the Lists sheet, and a value outside its list is reported (V-11)
- do not write the derived columns; they are recomputed and your value is discarded
- do not overwrite the user's source workbook - always deliver a new file

### 9.2 Level an over-allocated person

*The dashboard flags a person above over_allocation_fte for some months.*

1. python tools/prap_io.py calculate <file> --by person --flags shows every month over the ceiling and which projects make it up.
2. Reduce person_weight on the least critical assignment, or add a PersonPeriodWeight window covering only the offending months.
3. Re-run calculate. Moving load off one person usually pushes it onto another, so check the whole person list, not only the one you changed.

**Do not:**
- do not shorten an assignment to hide load - that changes the plan, not the demand. Say what you changed.

### 9.3 Answer a question about the data without changing it

*The user asks who is on what, when a project peaks, where the gaps are.*

1. python tools/prap_io.py to-json <file.xlsx> -o /tmp/read.prap.json, then read the JSON directly. It is the whole workbook as plain text.
2. python tools/prap_io.py calculate <file> --by project|person [--from YYYY-MM --to YYYY-MM] gives the same monthly figures the dashboard draws.
3. Quote figures as FTE to two decimals, and say which months you looked at.

**Do not:**
- do not re-derive the formula yourself; use calculate, so your answer and the dashboard cannot disagree

### 9.4 Continue a plan somebody started inside the application

*The user hands you a workbook they built by typing into PRAP rather than one exported from a system of record.*

1. Check the reference tables FIRST: python tools/prap_io.py to-json <file.xlsx> -o plan.prap.json, then look at PeriodFTEStandard and RoleFactor. A plan started blank seeds every one of them at 1.00 with a note saying so.
2. If they are still 1.00, say so before quoting any figure. The load formula then reduces to person_weight x month_coverage, which is a real number but not a resourced estimate.
3. Offer to fill them in from whatever the user can tell you about their own standards, one (type, phase, period) at a time. Do not invent them.
4. Everything else is an ordinary workbook - the same schema, the same rules.

**Do not:**
- do not treat a seeded 1.00 as a measured value, and do not quietly replace it with a number of your own

### 9.5 Prepare a workbook for someone to open in the application

*You have produced or edited data and the user wants to look at it.*

1. Validate first. A file with errors still loads, but the user meets a findings report before they see any numbers.
2. Deliver the .xlsx. Tell the user to open app/PRAP.html in a browser and drop the file on it - nothing is uploaded, and the application needs no network.
3. Say what you changed, in rows: 'added 4 Assignment rows, 1 PersonPeriodWeight window' beats 'updated the plan'.

**Do not:**
- do not send a .prap.json to a person expecting a spreadsheet - convert it to .xlsx first, unless they asked for the JSON

## 10. Checking your work

| To check | Run |
|---|---|
| validate a workbook (no browser) | `python tools/verify_source_workbook.py <file.xlsx>` |
| validate a draft in either format | `python tools/prap_io.py validate <file>` |
| documents against artifacts | `python tools/check_consistency.py` |
| calculation matches the reference implementation | `python tools/test_app.py  (drives the real application in a browser)` |
| JSON round-trip and cross-tool agreement | `python tools/test_interop.py` |
| row insert/delete/identity | `python tools/test_rows.py` |
| type-ahead value lists | `python tools/test_valuelist.py` |
| charts | `python tools/test_charts.py` |
| text contrast | `python tools/test_contrast.py` |

`prap_io.py` implements the same rules and the same formula as the application, and `tools/test_interop.py` proves the two agree — finding for finding and figure for figure — on both worked examples. If they ever stop agreeing, that test fails. So a file that passes `validate` is a file the application will load cleanly.

## 11. How to report back

- **Quantify in rows.** "Added 4 `Assignment` rows and 1 `PersonPeriodWeight` window" beats "updated the plan".
- **Quote FTE to two decimals**, and name the months you looked at.
- **Say what you assumed.** A `person_weight` you chose is a judgement, not a fact from the file. Mark it as yours.
- **Report the findings you left behind.** If `validate` still shows two warnings, say which and why they are acceptable.
- **Do not claim the dashboard shows something you did not check.** Run `calculate` and quote it.
- **Hand over a path.** Name the file you wrote and tell the user to open `app/PRAP.html` and drop it on the page.

---

Generated by `tools/build_ai_reference.py` on 2026-09-04 from `app/PRAP.html` v1.39, `PRAP_Development_Plan_v2.41.xlsx` and `tools/build_source_workbook.py`. Do not edit by hand — rebuild it.
