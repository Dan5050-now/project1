"""Generate the PRAP programming specification workbook (Step 2 deliverable).

Traceability is read from the approved plan rather than re-typed, so a requirement
cannot be dropped silently between the two documents.

    python tools/build_prog_spec.py

Output: docs/PRAP_Programming_Specification_v0.1.xlsx
"""

from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

DOC_VERSION = "0.3"
DOC_STATUS = "Draft for review"
DOC_DATE = "2026-08-01"
PLAN = "PRAP_Development_Plan_v1.4.xlsx"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / f"PRAP_Programming_Specification_v{DOC_VERSION}.xlsx"

FONT = "Arial"
NAVY = "1F3864"
TITLE_F = Font(name=FONT, size=16, bold=True, color=NAVY)
H1_F = Font(name=FONT, size=12, bold=True, color=NAVY)
HDR_F = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_F = Font(name=FONT, size=10)
BOLD_F = Font(name=FONT, size=10, bold=True)
NOTE_F = Font(name=FONT, size=9, italic=True, color="808080")
MONO_F = Font(name="Consolas", size=9)

HDR_FILL = PatternFill("solid", fgColor="2F5597")
BAND_FILL = PatternFill("solid", fgColor="F2F5FB")
INPUT_FILL = PatternFill("solid", fgColor="FFFF00")
CODE_FILL = PatternFill("solid", fgColor="F7F7F7")

THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
WRAP_C = Alignment(vertical="top", wrap_text=True, horizontal="center")


def sheet(wb, name, title, subtitle=None):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws["A1"] = title
    ws["A1"].font = TITLE_F
    row = 2
    if subtitle:
        ws["A2"] = subtitle
        ws["A2"].font = NOTE_F
        row = 3
    ws.freeze_panes = f"A{row + 2}"
    return ws, row + 1


def table(ws, start_row, headers, rows, widths, wrap_cols=()):
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=start_row, column=i, value=h)
        c.font, c.fill, c.border, c.alignment = HDR_F, HDR_FILL, BOX, WRAP_C
    ws.row_dimensions[start_row].height = 28
    for r, data in enumerate(rows, start=start_row + 1):
        for i, val in enumerate(data, start=1):
            c = ws.cell(row=r, column=i, value=val)
            c.font, c.border = BODY_F, BOX
            c.alignment = WRAP if i in wrap_cols else Alignment(vertical="top")
            if (r - start_row) % 2 == 0:
                c.fill = BAND_FILL
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return start_row + len(rows) + 2


def section(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = H1_F
    return row + 1


def note(ws, row, text):
    ws.cell(row=row, column=1, value=text).font = NOTE_F
    return row + 1


def lines(ws, row, texts):
    for t in texts:
        ws.cell(row=row, column=1, value=t).font = BODY_F
        row += 1
    return row


def code(ws, row, texts):
    for t in texts:
        c = ws.cell(row=row, column=1, value=t)
        c.font, c.fill = MONO_F, CODE_FILL
        row += 1
    return row + 1


wb = Workbook()
wb.remove(wb.active)

# ---- 00 Cover -------------------------------------------------------------
ws = wb.create_sheet("00_Cover")
ws.sheet_view.showGridLines = False
ws["A1"] = "Project Resource Assignment Program (PRAP)"
ws["A1"].font = Font(name=FONT, size=20, bold=True, color=NAVY)
ws["A2"] = "Programming Specification"
ws["A2"].font = Font(name=FONT, size=14, color=NAVY)

cover = [
    ("Document ID", "PRAP-SPEC-001"),
    ("Document type", "Programming specification (Step 2 deliverable)"),
    ("Version", f"v{DOC_VERSION}"),
    ("Status", DOC_STATUS),
    ("Issue date", DOC_DATE),
    ("Author", "Claude Code"),
    ("Governing document", f"{PLAN} - change R-05 against the v1.3 baseline, awaiting approval"),
    ("Schema version specified", "3"),
    ("Repository", "Dan5050-now/project1"),
    ("Branch", "claude/project-resource-assignment-app-1vjdzh"),
]
r = 4
for k, v in cover:
    ws.cell(row=r, column=1, value=k).font = BOLD_F
    c = ws.cell(row=r, column=2, value=v)
    c.font, c.alignment = BODY_F, WRAP
    r += 1
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 84

r += 1
r = section(ws, r, "What this document is")
r = lines(ws, r, [
    "The plan says WHAT the application must do. This says HOW, in enough detail that the code can be written",
    "from it and checked against it. Every section cites the REQ-IDs it implements, and sheet 09 shows the",
    "reverse: each of the 65 approved requirements mapped to the section that satisfies it.",
    "",
    "Two things make this specification unusual, and both are deliberate:",
    "",
    "  - The data schema is not described in prose. It already exists as a working file,",
    "    templates/PRAP_SourceData_Template_v1.3.xlsx, and sheet 03 documents the parse contract against it.",
    "  - The calculation and validation logic already has a reference implementation in",
    "    tools/verify_source_workbook.py, which runs against the dummy data. Sheet 05 gives the pseudocode;",
    "    that script is the executable check that the pseudocode is right.",
    "",
    "So the specification describes behaviour that has been exercised, not behaviour that is only imagined.",
])

r += 1
r = section(ws, r, "Contents")
guide = [
    ("00_Cover", "Document control and reading guide."),
    ("01_Version_History", "Change log."),
    ("02_Scope", "What is specified here, what is deferred to Step 3, and the source documents."),
    ("03_Data_Schema", "The parse contract: every sheet, column, type and coercion rule."),
    ("04_Validation", "V-01..V-21 with trigger, severity and the exact message shown."),
    ("05_Calculation", "Period derivation, the load formula, aggregation and the two thresholds."),
    ("06_UI_Spec", "The three tabs, their components, filters and states."),
    ("07_Editing_IO", "Edit buffer, dirty state, cascading identifier edits, import and export."),
    ("08_Versioning", "Schema compatibility check and version display."),
    ("09_Traceability", "All 65 requirements mapped to the section that implements them."),
    ("10_Open_Points", "Decisions still needed, and assumptions made in their absence."),
]
r = table(ws, r, ["Sheet", "Contents"], guide, [24, 86], wrap_cols=(2,))

# ---- 01 Version history ---------------------------------------------------
ws, r = sheet(wb, "01_Version_History", "Version history")
rows = [["0.3", DOC_DATE, "Claude Code", "-",
         "Change R-05: project_type split into 'NewDrug CT' and 'Biosimilar CT'. Parse contract, keys and "
         "schema version updated; RoleFactor and PeriodWeightStandard are now keyed on the type. Sheet 06 "
         "gains the UI changes requested at the Step 3 review: a global filter bar with Reset, per-project "
         "stacking, horizontal scroll regions, and row expansion on both Overall tables.", "Draft"],
        ["0.2", "2026-08-01", "Claude Code", "-",
         "Parse contract updated for change R-04: a free-text note column on every sheet, and source schema "
         "version 2. Column counts on the sheet-index table adjusted. No change to validation, calculation, "
         "UI or IO behaviour.", "Draft"],
        ["0.1", "2026-08-01", "Claude Code", "-",
         "First draft. Written against development plan v1.2 (approved baseline). Data schema documented from "
         "the delivered template; calculation and validation cross-checked against the reference implementation "
         "in tools/verify_source_workbook.py and the dummy dataset.", "Draft"]]
r = table(ws, r, ["Version", "Date", "Author", "Reviewer", "Summary of change", "Status"],
          rows, [10, 12, 15, 14, 92, 14], wrap_cols=(5,))
r = note(ws, r, "Version alignment across plan, specification and application is recorded on sheet 09 of the plan.")

# ---- 02 Scope -------------------------------------------------------------
ws, r = sheet(wb, "02_Scope", "Scope and source documents")

r = section(ws, r, "Source documents")
src = [
    [PLAN, "FINAL development plan, approved by Dan 2026-08-01. 65 requirements, 21 validation rules, 11 decisions, source schema version 2.", "Governs this document"],
    ["templates/PRAP_SourceData_Template_v1.2.xlsx", "The blank source workbook as delivered.", "The schema on sheet 03 documents this file"],
    ["templates/PRAP_SourceData_Dummy_v1.4.xlsx", "34 NewDrug CT + 16 Biosimilar CT + 12 'Others', 20 people, 289 assignments over 73 months.", "The acceptance data for sheet 05"],
    ["tools/verify_source_workbook.py", "Reference implementation of parsing, validation and the monthly engine.", "Executable check on sheets 04 and 05"],
    ["docs/STEP2_OPEN_POINTS.md", "Points raised while building the template.", "Carried into sheet 10"],
]
r = table(ws, r, ["Document", "What it is", "Relationship to this specification"], src, [46, 62, 46], wrap_cols=(2, 3))

r = section(ws, r, "In scope for this specification")
ins = [
    ["The parse contract for the source workbook: sheets, columns, types, coercion and defaults."],
    ["All 21 validation rules with their exact severity and message."],
    ["Period derivation for both project types, including every degenerate timeline."],
    ["The monthly load calculation, aggregation, and the over- and under-allocation rules."],
    ["The behaviour of each dashboard tab: components, filters, interactions and empty states."],
    ["On-screen editing: the edit buffer, dirty state, cascading identifier changes, and export round-tripping."],
    ["Schema version checking and version display."],
]
r = table(ws, r, ["In scope"], ins, [132], wrap_cols=(1,))

r = section(ws, r, "Deferred to Step 3")
defer = [
    ["Exact visual layout, spacing, colour and typography.", "Step 3 fixes the UI design; sheet 06 fixes behaviour and content, not pixels."],
    ["Which chart library, if any, is embedded.", "Sheet 06 specifies what each graph must show. The rendering choice is made at Step 3 against the prototype."],
    ["Keyboard shortcuts and accessibility details.", "Reviewed with the prototype, where they can be tried rather than described."],
]
r = table(ws, r, ["Deferred", "Why"], defer, [56, 76], wrap_cols=(1, 2))

# ---- 03 Data schema -------------------------------------------------------
ws, r = sheet(wb, "03_Data_Schema", "Data schema - the parse contract",
              "Documents templates/PRAP_SourceData_Template_v1.2.xlsx. Sheet and column names are matched "
              "exactly and case-sensitively.")

r = section(ws, r, "Reading the workbook")
r = code(ws, r, [
    "  for each required sheet:",
    "      if absent                     -> fatal, abort the load and report (V-00)",
    "      read row 1 as the header",
    "      for each column in the contract below:",
    "          locate it by exact name; if absent -> fatal for a required column,",
    "                                                ignore for an optional one",
    "      read rows 2..n; a row whose every cell is empty is skipped, not an error",
    "      coerce each cell per its type; a failed coercion is an error on that row",
])

r = section(ws, r, "Type coercion")
types = [
    ["Text", "Trim leading and trailing whitespace. An empty string becomes null.", "Never coerce a number to text silently - a project_id of 001 read as 1 breaks every join."],
    ["Date", "Accept an Excel serial date or an ISO yyyy-mm-dd string. Normalise to a date with no time part.", "Any other format is an error, never a guess (REQ-NFR-05). A dd/mm vs mm/dd guess is silently wrong half the time."],
    ["Decimal", "Accept a number, or a string parseable as one with '.' as the decimal separator.", "A percentage-formatted cell reads as its underlying fraction; 40% is 0.4, which is what person_weight expects."],
    ["Integer", "As Decimal, then require a whole number.", "A fractional period_seq is an error."],
    ["List", "Text, then checked against the Lists sheet by V-11.", "The check is a warning, not a coercion - an unrecognised value is kept and reported."],
]
r = table(ws, r, ["Type", "Coercion", "Why it matters"], types, [12, 62, 66], wrap_cols=(2, 3))

r = section(ws, r, "Sheets and keys")
sheets = [
    ["Project", "project_id", "-", "23", "Master."],
    ["Milestone", "project_id + milestone_name + milestone_date", "Project", "6", "milestone_name is NOT unique alone - 'Inspection' repeats (REQ-PRJ-13)."],
    ["ProjectPeriod", "project_id + period_seq", "Project", "7", "period_name is NOT unique alone - 'Conduct' occurs twice (REQ-CAL-11)."],
    ["PeriodWeightStandard", "project_type + clinical_phase + period_name", "-", "5", "Both trial types, keyed separately (R-05). 'Others' take manual weights (Q-28)."],
    ["RoleFactor", "project_type + role_name", "-", "4", "Keyed on all three types, so NewDrug and Biosimilar can carry different factors (R-05)."],
    ["Person", "person_id", "-", "12", "Master."],
    ["Assignment", "assignment_id", "Person, Project, RoleFactor", "11", "One row per person + project + role."],
    ["PersonPeriodWeight", "assignment_id + period_start", "Assignment", "5", "Optional. Overrides person_weight for its window."],
    ["Lists", "list_name + value", "-", "3", "Value lists, long format. Each list occupies a contiguous block."],
    ["Config", "parameter", "-", "3", "Thresholds and settings."],
]
r = table(ws, r, ["Sheet", "Key", "References", "Cols", "Note"], sheets, [22, 40, 26, 7, 45], wrap_cols=(2, 5))

r = section(ws, r, "Derived columns - read, do not trust")
der = [
    ["Project.total_period_months", "Recompute from start_date and end_date.", "The template holds a formula, but an exported or hand-edited file may not. Recomputing costs nothing and cannot disagree with the dates."],
    ["Milestone.project_name", "Recompute by lookup on project_id.", "Denormalised for display only. V-13 reports a mismatch; the master value always wins."],
    ["Assignment.person_name", "Recompute by lookup on person_id.", "As above."],
]
r = table(ws, r, ["Column", "On import", "Reason"], der, [30, 44, 66], wrap_cols=(2, 3))

r = section(ws, r, "Free-text note columns   [R-04]")
r = lines(ws, r, [
    "Every sheet carries at least one. They are parsed as Text, carried through export unchanged, and never",
    "read by the calculation - so a note can hold anything without affecting a single figure.",
])
r += 1
notes_tbl = [
    ["Project", "note_1 .. note_5"], ["Milestone", "note_1"],
    ["ProjectPeriod", "note_1"], ["PeriodWeightStandard", "note_1"],
    ["RoleFactor", "role_note"], ["Person", "note_1 .. note_5"],
    ["Assignment", "note_1 .. note_3"], ["PersonPeriodWeight", "reason"],
    ["Lists", "note_1"], ["Config", "note"],
]
r = table(ws, r, ["Sheet", "Note column(s)"], notes_tbl, [26, 34])
r = note(ws, r, "A note column that is absent is not an error - it is optional on every sheet. An import must not "
                "fail because someone deleted a column they were not using.")
r += 1

r = section(ws, r, "Config parameters")
cfg = [
    ["schema_version", "Integer", "3", "Compared with the version this application expects (sheet 08)."],
    ["fte_hours_per_month", "Decimal", "160", "Converts FTE to hours for display."],
    ["over_allocation_fte", "Decimal", "1.50", "See sheet 05 and open point S2-01."],
    ["under_allocation_fte", "Decimal", "0.80", "See sheet 05 and open point S2-01."],
    ["under_allocation_min_months", "Integer", "3", "Consecutive months before a run is flagged."],
    ["default_horizon_months", "Integer", "24", "Months shown on opening."],
    ["capacity_unit", "List", "FTE", "'FTE' or 'percent'."],
]
r = table(ws, r, ["parameter", "Type", "Default", "Use"], cfg, [30, 12, 12, 86], wrap_cols=(4,))
r = note(ws, r, "A missing Config row falls back to the default above and raises a warning. A Config value that fails "
                "coercion is an error - a threshold read as text would silently disable a flag.")

# ---- 04 Validation --------------------------------------------------------
ws, r = sheet(wb, "04_Validation", "Validation rules",
              "Every rule runs on import and again on any on-screen edit (REQ-IMP-09). The load never stops at "
              "the first problem: findings are collected and presented as one report (REQ-IMP-02).")

r = section(ws, r, "Severities")
sev = [
    ["Fatal", "The workbook cannot be used at all.", "Abort the load. Show what is missing and the template download link.", "Missing sheet; missing required column."],
    ["Error", "This row cannot be trusted.", "Reject the row, keep loading the rest, list it with its sheet and row number.", "Unknown project_id on an assignment; end before start."],
    ["Warning", "Usable, but someone should look.", "Keep the row, list the finding.", "A value not in its list; an assignment outside its project's dates."],
    ["Information", "Explains a decision the reader might otherwise question.", "List only.", "V-21: an early inspection did not open period 7."],
]
r = table(ws, r, ["Severity", "Meaning", "Behaviour", "Example"], sev, [14, 40, 56, 46], wrap_cols=(2, 3, 4))

r = section(ws, r, "The rules")
rules = [
    ["V-00", "Fatal", "A required sheet or column is absent.", "Sheet 'Assignment' not found. The workbook must contain all 10 sheets - download the template to compare."],
    ["V-01", "Error", "Assignment.project_id not found in Project.", "Assignment ASG-014 refers to project PRJ-099, which does not exist."],
    ["V-02", "Error", "Assignment.person_id not found in Person.", "Assignment ASG-014 refers to person PSN-099, which does not exist."],
    ["V-03", "Error", "Assignment.role_name not in RoleFactor for that project's type.", "Assignment ASG-014: role 'Main staff' is not valid for a Clinical Trial. Valid roles for this type: ..."],
    ["V-04", "Warning", "project_category empty where project_type = 'Clinical Trial'.", "Project PRJ-003 is a clinical trial with no product category."],
    ["V-05", "Error", "An end date precedes its start date.", "Project PRJ-003: end_date 2026-01-01 is before start_date 2026-06-01."],
    ["V-06", "Error", "Two periods of one project, or two windows of one assignment, overlap.", "Project PRJ-003: periods 3 and 4 overlap between 2027-06-01 and 2027-06-30."],
    ["V-07", "Warning", "Assignment dates fall outside the project's own dates.", "Assignment ASG-014 runs to 2029-06-30, after project PRJ-005 ends on 2029-03-31."],
    ["V-08", "Error", "A duplicate identifier.", "person_id PSN-004 appears on rows 5 and 12."],
    ["V-09", "Warning", "Config.schema_version differs from the expected version.", "This file is schema version 2; this application expects version 1. Some columns may be ignored."],
    ["V-10", "Warning", "A clinical trial missing clinical_phase or any *_setup value.", "Project PRJ-004 has no RBQM_setup recorded."],
    ["V-11", "Warning", "A list-typed value not found in the Lists sheet.", "Project PRJ-002: outsourcing_type 'Partial in house' is not a known value. Did you mean 'Full In-house'?"],
    ["V-12", "Warning", "A project's periods leave a gap or do not cover its full span.", "Project PRJ-006: 2026-07-01 to 2026-07-31 belongs to no period. Those months are calculated at weight 1.00."],
    ["V-13", "Warning", "A denormalised name does not match its master row.", "Assignment ASG-014 records person_name 'Kim' but PSN-001 is 'Kim S.'. The master value is used."],
    ["V-14", "Error / Warning", "A boundary milestone is out of chronological order, or a milestone falls outside the project window.", "Project PRJ-003: 'First SIV' 2025-12-01 precedes 'CTA submission' 2026-01-15, so periods cannot be derived."],
    ["V-15", "Error", "A period_name not in the set for that project's type.", "Project PRJ-006 is type 'Others' but has a period named 'Conduct'. Valid: Planning, Develop, Close."],
    ["V-16", "Error", "A clinical trial lacking CTA submission or any DB lock.", "Project PRJ-007 has no DB lock milestone, so its periods cannot be derived. Enter them manually or add the milestone."],
    ["V-17", "Error", "An edit would orphan a reference (see sheet 07).", "PSN-001 cannot be deleted: 3 assignments still refer to it."],
    ["V-18", "Error", "period_seq duplicated within a project.", "Project PRJ-003: period_seq 3 appears twice; the two 'Conduct' stretches cannot be told apart."],
    ["V-19", "Error", "A clinical trial with no clinical_phase, or no PeriodWeightStandard rows for its phase.", "Project PRJ-005 is Phase 3, but PeriodWeightStandard has no Phase 3 rows. Its periods cannot be weighted."],
    ["V-20", "Warning", "A milestone other than 'Inspection' recorded more than once.", "Project PRJ-002 records 'CTA submission' twice. Only 'Inspection' is expected to repeat."],
    ["V-21", "Information", "An 'Inspection' dated on or before the final DB lock.", "Project PRJ-002: 1 inspection on or before the final DB lock is treated as a marker and does not open the final period."],
]
r = table(ws, r, ["ID", "Severity", "Trigger", "Message shown to the user"],
          rules, [8, 15, 56, 76], wrap_cols=(3, 4))
r = note(ws, r, "Messages name the row and the offending value, and where there is an obvious fix they suggest it. "
                "A validation report that says only 'invalid data' forces the user to hunt, which is how findings "
                "get ignored.")

r = section(ws, r, "The findings report")
rep = [
    ["Grouped by severity, then by sheet.", "Fatals first - if any exist, nothing else matters yet."],
    ["Each finding shows sheet, row number, rule ID and message.", "The row number is the Excel row, so the user can go straight to it."],
    ["A one-line summary banner persists until dismissed.", "e.g. '3 errors, 11 warnings - 2 rows were not loaded'."],
    ["Exportable to .xlsx.", "So a data maintainer can work through it away from the application."],
]
r = table(ws, r, ["Behaviour", "Reason"], rep, [62, 70], wrap_cols=(1, 2))

# ---- 05 Calculation -------------------------------------------------------
ws, r = sheet(wb, "05_Calculation", "Calculation",
              "Pure functions: no DOM, no file access (plan sheet 07, layer 5). "
              "tools/verify_source_workbook.py is the reference implementation.")

r = section(ws, r, "Period derivation - 'Clinical Trial'   [REQ-CAL-09, REQ-CAL-12, REQ-CAL-13]")
r = code(ws, r, [
    "  protocol = milestone 'Protocol (v1)'          cta  = milestone 'CTA submission'",
    "  siv      = 'First SIV' else 'FPI'             idbl = 'interim DB lock'",
    "  fdbl     = 'final DB lock' else idbl          insp = all 'Inspection' dates",
    "",
    "  if cta is null or fdbl is null:  raise V-16 and derive nothing",
    "",
    "  su_start = max( protocol + 1 day  if protocol else  cta - 1 month , project.start )",
    "  su_end   = siv  if siv and siv >= su_start  else  su_start + 4 months - 1 day",
    "",
    "  later    = [ d in insp where d > fdbl ]            # V-21: earlier ones stay markers",
    "  p7_start = min(later) if later else null",
    "  p7_end   = max( max(later), project.end ) if later else null",
    "",
    "  cof_start = fdbl - 3 months",
    "  cof_end   = p7_start - 1 day  if p7_start  else  max( fdbl, project.end )",
    "",
    "  segments = []",
    "  if su_start > project.start:  segments += ('Before-Start-up', project.start, su_start - 1 day)",
    "  segments += ('Start-up', su_start, su_end)",
    "  if idbl and idbl < fdbl:",
    "      coi_start = idbl - 3 months",
    "      segments += ('Conduct',             su_end + 1 day,  coi_start - 1 day)",
    "      segments += ('Close-out (interim)', coi_start,       idbl)",
    "      cof_start = max( cof_start, idbl + 1 day )",
    "      segments += ('Conduct',             idbl + 1 day,    cof_start - 1 day)",
    "  else:",
    "      segments += ('Conduct',             su_end + 1 day,  cof_start - 1 day)",
    "  segments += ('Close-out (final)', cof_start, cof_end)",
    "  if p7_start:  segments += ('After Close-out (final)', p7_start, p7_end)",
    "",
    "  drop every segment whose end < start          # REQ-CAL-12, decision C-11",
    "  number the survivors 1..n as period_seq",
])
r = note(ws, r, "'month' arithmetic clamps to the end of a short month: 31 Mar minus 1 month is 28 Feb (29 in a leap "
                "year). Test that explicitly - it is the classic off-by-one in this kind of code.")
r += 1
r = note(ws, r, "For 'Others' the derivation does not run at all: periods are read from ProjectPeriod as entered (Q-25, Q-28).")
r += 1

r = section(ws, r, "Monthly load   [REQ-CAL-02, REQ-CAL-05, REQ-CAL-08]")
r = code(ws, r, [
    "  load(assignment, month) = project_period_weight( project, month )",
    "                          x role_factor( project.type, assignment.role )",
    "                          x person_weight( assignment, month )",
    "                          x coverage( assignment, month )",
    "",
    "  project_period_weight : weight of the period containing the FIRST DAY of the month  (decision C-08)",
    "                          no period covers it -> 1.00, and raise V-12",
    "  person_weight         : PersonPeriodWeight.weight_override if a window covers the",
    "                          first day of the month, else assignment.person_weight",
    "  coverage              : calendar days of the month inside [assign_start, assign_end]",
    "                          divided by the days in that month",
    "",
    "  result is FTE.  hours = FTE x config.fte_hours_per_month",
])

r = section(ws, r, "Aggregation   [REQ-CAL-03, REQ-CAL-04, REQ-CAL-07]")
agg = [
    ["project_month[p][m]", "sum of load over assignments on project p", "Overall tab, table A and the stacked graph"],
    ["person_month[s][m]", "sum of load over all assignments held by person s", "Overall tab, table B and the person graph"],
    ["cell[s][p][m]", "the individual load", "Drill-down under a person or project row"],
    ["headcount[p][m]", "count of assignments with load > 0", "Compared with planned_member_count"],
    ["over[s][m]", "true where person_month > over_threshold(s)", "Red cell, counted in the summary tiles"],
    ["under_runs[s]", "maximal runs of >= min_months consecutive months where 0 < person_month < under_threshold(s)", "Amber across the run, counted once per run"],
]
r = table(ws, r, ["Output", "Definition", "Where it surfaces"], agg, [24, 76, 40], wrap_cols=(2, 3))

r = section(ws, r, "Thresholds   [S2-01 - decision pending]")
r = lines(ws, r, [
    "The plan sets an absolute over_allocation_fte of 1.50 and under_allocation_fte of 0.80, while Person",
    "carries capacity_fte. A part-timer at 0.60 capacity can never reach 0.80, so is flagged permanently.",
    "This draft therefore specifies the thresholds as RELATIVE to capacity, which leaves a full-time person's",
    "behaviour identical:",
])
r = code(ws, r, [
    "  over_threshold(s)  = config.over_allocation_fte  x person(s).capacity_fte",
    "  under_threshold(s) = config.under_allocation_fte x person(s).capacity_fte",
    "  capacity_fte missing or zero -> treat as 1.00",
])
r = note(ws, r, "If S2-01 is decided the other way, delete the multiplication - nothing else changes. "
                "The assumption is recorded on sheet 10.")
r += 1

r = section(ws, r, "Under-allocation runs")
r = code(ws, r, [
    "  walk the person's months in order across the horizon",
    "  a month counts toward a run when  0 < person_month < under_threshold",
    "  a month at exactly 0 BREAKS the run          # no assignments at all is not under-allocation",
    "  a run of >= config.under_allocation_min_months is reported once, at its first month,",
    "      carrying its length",
])
r = note(ws, r, "Reporting the run once rather than flagging each month is what makes the signal readable: three "
                "separate amber cells look like three problems.")
r += 1

r = section(ws, r, "Acceptance test")
ex = [
    ["Assignment", "PSN-001 on PRJ-001 (Clinical Trial), role 'Lead data manager'", ""],
    ["person_weight", "0.40", ""],
    ["Window", "2026-03-10 to 2026-12-31", "Joins part-way through March"],
    ["Periods", "Start-up to 2026-06-30 at weight 1.50; Conduct from 2026-07-01 at 1.00", "From the trial's clinical phase"],
    ["role_factor", "1.20", "Illustrative; the real value is data"],
    ["March 2026", "1.50 x 1.20 x 0.40 x (22/31) = 0.511 FTE", "81.8 hours"],
    ["April 2026", "1.50 x 1.20 x 0.40 x 1.0000 = 0.720 FTE", "115.2 hours"],
    ["July 2026", "1.00 x 1.20 x 0.40 x 1.0000 = 0.480 FTE", "76.8 hours"],
]
r = table(ws, r, ["Element", "Value", "Note"], ex, [22, 62, 44], wrap_cols=(2, 3))
r = note(ws, r, "Plus the whole dummy dataset: running tools/verify_source_workbook.py against "
                "PRAP_SourceData_Dummy_v1.4.xlsx must give no errors and no warnings, across 62 projects, "
                "20 people, 289 assignments and 308 periods spanning 73 months. Every period set must be "
                "contiguous, 30 trials must show two 'Conduct' stretches, and 12 must carry the seventh "
                "period. Those figures are the regression baseline for Step 4.")

# ---- 06 UI ----------------------------------------------------------------
ws, r = sheet(wb, "06_UI_Spec", "User interface",
              "Behaviour and content. Layout, colour and typography are fixed at Step 3.")

r = section(ws, r, "Global")
glob = [
    ["Header", "Application name, application version, expected schema version, loaded file name and load time.", "REQ-VC-02, REQ-IMP-05"],
    ["Tab bar", "Overall | Source data (project) | Source data (person). Tab state survives a re-import.", "REQ-DSH-01..04"],
    ["Findings banner", "Appears when the last load or edit produced findings; opens the full report on click.", "REQ-IMP-02"],
    ["Unsaved-edit counter", "Always visible once any edit exists. Warns before unload or a new import.", "REQ-IMP-08"],
    ["Empty state", "With nothing loaded, every tab shows the same load panel plus a template download link.", "REQ-IMP-03"],
]
r = table(ws, r, ["Component", "Behaviour", "REQ-ID"], glob, [24, 90, 20], wrap_cols=(2,))

r = section(ws, r, "Tab 1 - Overall")
ov = [
    ["Horizon control", "From/to month. Defaults to 24 months from the current month. One control expands it to span every project's dates.", "REQ-CAL-01, REQ-DSH-07"],
    ["Filters", "project type (NewDrug CT / Biosimilar CT / Others), project, person, role, department. Multi-select, combined with AND. GLOBAL: one setting drives every tab, not just the Overall tab.", "REQ-DSH-05"],
    ["Unit toggle", "FTE or hours, seeded from config.capacity_unit.", "REQ-CAL-08"],
    ["Table A - by project", "Rows projects, columns months, cells FTE. Row and column totals. A project row expands to its people.", "REQ-DSH-01"],
    ["Table B - by person", "Rows people, columns months, cells FTE summed across projects. Over-allocated cells red, under-allocation runs amber. A person row expands to their projects.", "REQ-DSH-01, REQ-DSH-08"],
    ["Graph 1", "Stacked bar: total monthly demand, ONE BAND PER PROJECT, ordered by total resource with the largest on the baseline. 'Others' projects are grey; trials take the extended colour set.", "REQ-DSH-02"],
    ["Graph 2", "Grouped bar: monthly FTE per person, with reference lines at each person's over and under thresholds.", "REQ-DSH-02, REQ-DSH-08"],
    ["Graph 3", "Timeline per project across the horizon: period bands shaded by weight, milestone markers, repeated 'Inspection' markers shown individually.", "REQ-DSH-02, REQ-PRJ-05"],
    ["Summary tiles", "Active projects; people assigned; total FTE in the horizon; over-allocated person-months; under-allocation runs.", "REQ-DSH-08"],
    ["Reset filters", "Clears every filter and restores the default 24-month horizon in one action.", "REQ-DSH-05"],
    ["Scroll regions", "Every chart and table sits in its own horizontal scroll region, so wide content scrolls inside the panel and the page body never scrolls sideways.", "REQ-NFR-02"],
    ["Row expansion - project", "Clicking a project name reveals one row per person and role on it, each with its own monthly figures. Clicking again collapses.", "REQ-DSH-01"],
    ["Row expansion - person", "Clicking a person name reveals one row per project and role they hold, ordered NewDrug CT, Biosimilar CT, Others, then earliest project first.", "REQ-DSH-01"],
    ["Type and phase pills", "Project type and clinical phase shown as labelled pills. The text carries the meaning; the colour only speeds recognition.", "REQ-PRJ-01, REQ-PRJ-09"],
]
r = table(ws, r, ["Component", "Behaviour", "REQ-ID"], ov, [24, 90, 20], wrap_cols=(2,))
r = note(ws, r, "Both tables are the same numbers aggregated differently, so they must always reconcile: the grand "
                "total of table A equals that of table B. Worth asserting in code, not just hoping.")

r = section(ws, r, "Tab 2 - Source data (project)")
t2 = [
    ["Project table", "All 23 Project columns, sortable and filterable, total_period_months recomputed. Editable.", "REQ-DSH-03, REQ-IMP-07"],
    ["Milestone sub-table", "Milestones of the selected project in date order. 'Inspection' may appear several times.", "REQ-PRJ-05, REQ-PRJ-13"],
    ["Period sub-table", "Derived periods with seq, dates and weight. Shows whether each date was derived or hand-set.", "REQ-PRJ-06, REQ-CAL-09"],
    ["Recompute periods", "Re-derives from current milestones, warning that hand-set dates will be replaced.", "decision C-10"],
    ["Export", "Visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Behaviour", "REQ-ID"], t2, [24, 90, 20], wrap_cols=(2,))

r = section(ws, r, "Tab 3 - Source data (person)")
t3 = [
    ["Person table", "All 12 Person columns, sortable and filterable. Editable.", "REQ-DSH-04, REQ-IMP-07"],
    ["Assignment sub-table", "The selected person's assignments: project, role, dates, person_weight.", "REQ-PSN-02, REQ-PSN-03"],
    ["Override sub-table", "PersonPeriodWeight windows for the selected assignment.", "REQ-PSN-05"],
    ["Utilisation strip", "The person's monthly FTE across the horizon with both thresholds marked.", "REQ-DSH-08"],
    ["Export", "Visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Behaviour", "REQ-ID"], t3, [24, 90, 20], wrap_cols=(2,))

# ---- 07 Editing and IO ----------------------------------------------------
ws, r = sheet(wb, "07_Editing_IO", "Editing, import and export")

r = section(ws, r, "Import   [REQ-IMP-01, REQ-IMP-02]")
r = code(ws, r, [
    "  user picks a file, or drops one on the page",
    "  parse -> validate -> build the model -> derive periods -> calculate -> render",
    "  a fatal finding stops after validate and shows the report",
    "  a successful load replaces the model entirely; unsaved edits are warned about first",
])

r = section(ws, r, "The edit buffer   [REQ-IMP-07, REQ-IMP-09]")
edit = [
    ["Every field is editable, identifiers included.", "Q-20. Consistency is protected by rule, not by locking fields."],
    ["An edit is validated with the same rules as an import, at the moment of entry.", "REQ-IMP-09. A rejected edit never reaches the model, so the model is always valid."],
    ["An edited cell is marked; the count of unsaved edits is always visible.", "REQ-IMP-08."],
    ["Editing a milestone date re-derives that project's periods, unless its period dates were hand-set.", "Decision C-10. This is the frequent-timeline-change case the tool exists for."],
    ["Editing a weight, date or assignment recalculates immediately.", "The dashboard must never show numbers that disagree with the data on screen."],
]
r = table(ws, r, ["Rule", "Basis"], edit, [76, 56], wrap_cols=(1, 2))

r = section(ws, r, "Cascading identifier edits   [REQ-IMP-10, V-17]")
r = code(ws, r, [
    "  on changing an identifier:",
    "      count the rows referencing the old value",
    "      if 0 : apply",
    "      else : confirm ('PRJ-003 is referenced by 14 rows. Update them all?')",
    "             on confirm, rewrite every reference in one atomic step",
    "",
    "  on deleting a row:",
    "      if anything still references it -> refuse, naming what does (V-17)",
    "      never cascade a delete: losing 14 assignments to one keystroke is unrecoverable",
])
r = note(ws, r, "Cascading an edit and refusing a delete are deliberately asymmetric. A cascaded rename is visible and "
                "reversible; a cascaded delete is neither.")

r = section(ws, r, "Export   [REQ-IMP-04, REQ-IMP-07]")
exp = [
    ["Writes all 10 sheets in template order, with the template's headers and formats.", "So the export re-imports without edits."],
    ["Includes every edit made on screen.", "REQ-IMP-07 - this is the point of the feature."],
    ["Derived columns are written as values, not formulas.", "A formula referencing a row that moved would be wrong; the importer recomputes them anyway."],
    ["Filename defaults to the loaded name with a date suffix.", "Never silently overwrite the source of record."],
    ["Clears the unsaved-edit state on success.", "REQ-IMP-08."],
]
r = table(ws, r, ["Behaviour", "Reason"], exp, [76, 56], wrap_cols=(1, 2))

# ---- 08 Versioning --------------------------------------------------------
ws, r = sheet(wb, "08_Versioning", "Versioning and compatibility")
ver = [
    ["Application version", "Constant in the HTML, shown in the header and footer.", "REQ-VC-02"],
    ["Expected schema version", "Constant in the HTML. Currently 3.", "REQ-VC-02"],
    ["Check on load", "Compare Config.schema_version with the expected value.", "REQ-VC-03"],
    ["Equal", "Proceed silently.", "REQ-VC-03"],
    ["File older", "Proceed; warn that columns added since may be missing.", "REQ-VC-03"],
    ["File newer", "Proceed; warn that columns may be ignored, and suggest updating the application.", "REQ-VC-03"],
    ["Missing", "Treat as version 1 and warn.", "REQ-VC-03"],
]
r = table(ws, r, ["Item", "Behaviour", "REQ-ID"], ver, [26, 88, 18], wrap_cols=(2,))
r = note(ws, r, "The check never blocks a load. A planner with a slightly stale file still needs an answer today; "
                "a warning gives them one with the caveat attached.")

# ---- 09 Traceability ------------------------------------------------------
ws, r = sheet(wb, "09_Traceability", "Requirement traceability",
              f"Read directly from {PLAN} sheet 03, so a requirement cannot be lost between the two documents.")

plan_wb = load_workbook(ROOT / "docs" / PLAN)
plan_ws = plan_wb["03_Requirements"]
SECTION_BY_PREFIX = {
    "REQ-OUT": "02_Scope, 07_Editing_IO",
    "REQ-PRJ": "03_Data_Schema",
    "REQ-PSN": "03_Data_Schema",
    "REQ-CAL": "05_Calculation",
    "REQ-DSH": "06_UI_Spec",
    "REQ-IMP": "07_Editing_IO",
    "REQ-VC": "08_Versioning",
    "REQ-NFR": "02_Scope, 07_Editing_IO",
}
trace, counts = [], {}
for rr in range(5, plan_ws.max_row + 1):
    rid = plan_ws.cell(rr, 1).value
    if not rid or not str(rid).startswith("REQ"):
        continue
    rid = str(rid).strip()
    prefix = "-".join(rid.split("-")[:2])
    sec = SECTION_BY_PREFIX.get(prefix, "-")
    counts[sec] = counts.get(sec, 0) + 1
    trace.append([rid, str(plan_ws.cell(rr, 3).value)[:150], plan_ws.cell(rr, 4).value, sec])
r = table(ws, r, ["REQ-ID", "Requirement (from the plan)", "Priority", "Specified in"],
          trace, [15, 96, 10, 30], wrap_cols=(2,))
r = note(ws, r, f"{len(trace)} requirements, all mapped. Regenerated from the plan on every build, so a requirement "
                f"added there appears here automatically rather than being remembered.")

# ---- 10 Open points -------------------------------------------------------
ws, r = sheet(wb, "10_Open_Points", "Open points",
              "Decisions still needed. Each says what this draft assumes in the meantime, "
              "so nothing is blocked. Please answer in the YELLOW cells.")
op = [
    ["S2-01", "Calculation", "The under-allocation threshold is an absolute 0.80 FTE while Person.capacity_fte allows a part-timer at 0.60, who can therefore never clear it and is flagged permanently. Should both thresholds be relative to capacity_fte?",
     "This draft specifies them as RELATIVE (sheet 05). A full-time person behaves identically; only part-timers change.", ""],
    ["S2-02", "Data model", "period_name and role_name cannot carry an Excel dropdown, because the valid list depends on the project's type.",
     "Enforced at import and edit by V-15 and V-03 instead. No action needed unless you want dependent dropdowns building.", ""],
    ["S2-03", "Data model", "Adding a value to a list means inserting a row inside that list's block on the Lists sheet, since dropdowns bind to a contiguous range.",
     "Documented in the template README. One list per column would be more robust but is a schema change.", ""],
    ["S2-04", "UI", "Should the two 'Conduct' stretches of one project be distinguishable on screen, or shown as one Conduct total?",
     "This draft shows them as separate bands on the timeline graph but sums them in the tables.", ""],
    ["S2-05", "Calculation", "A month with zero load breaks an under-allocation run rather than continuing it - somebody with no assignments at all is not 'under-allocated', they are unassigned.",
     "Specified that way on sheet 05. Say so if a gap should instead continue the run.", ""],
    ["S2-06", "Non-functional", "The dummy dataset now holds 62 projects and 289 assignments, above REQ-NFR-03's headroom figure of 50 projects and 500 assignments. The requirement's working-volume figure (20 projects, 30 people) is well below what the dataset represents.",
     "Treated as a deliberate stress fixture, not a change to REQ-NFR-03. If 50+ trials is the real working volume rather than an upper bound, the requirement should be re-baselined at Step 4 rather than left understating it.", ""],
]
r_start = r
r = table(ws, r, ["ID", "Topic", "Question", "What this draft assumes", "Your answer"],
          op, [8, 14, 62, 52, 36], wrap_cols=(3, 4, 5))
for rr in range(r_start + 1, r_start + 1 + len(op)):
    c = ws.cell(row=rr, column=5)
    c.fill, c.border = INPUT_FILL, BOX
r = note(ws, r, "None of these blocks Step 3. Each changes a single rule that the application reads as data or "
                "applies in one place.")

wb.save(OUT)
print(f"Written: {OUT}  ({len(trace)} requirements traced)")
