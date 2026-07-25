"""Generate the Project Resource Assignment Program (PRAP) development plan workbook.

The workbook is a generated artifact: edit this script, re-run it, and commit both
so the plan stays diffable under version control.

    python tools/build_dev_plan.py

Output: docs/PRAP_Development_Plan_v0.1.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

DOC_VERSION = "0.1"
DOC_STATUS = "Draft for review"
DOC_DATE = "2026-07-25"
OUT = Path(__file__).resolve().parents[1] / "docs" / f"PRAP_Development_Plan_v{DOC_VERSION}.xlsx"

FONT = "Arial"
NAVY = "1F3864"
BLUE_HDR = "2F5597"
LIGHT = "D9E2F3"
BAND = "F2F5FB"
YELLOW = "FFFF00"
GREY = "808080"

TITLE_F = Font(name=FONT, size=16, bold=True, color=NAVY)
H1_F = Font(name=FONT, size=12, bold=True, color=NAVY)
HDR_F = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_F = Font(name=FONT, size=10)
BOLD_F = Font(name=FONT, size=10, bold=True)
NOTE_F = Font(name=FONT, size=9, italic=True, color=GREY)

HDR_FILL = PatternFill("solid", fgColor=BLUE_HDR)
BAND_FILL = PatternFill("solid", fgColor=BAND)
LIGHT_FILL = PatternFill("solid", fgColor=LIGHT)
INPUT_FILL = PatternFill("solid", fgColor=YELLOW)

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
    """Write a banded header+body table. Returns the row after the table."""
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=start_row, column=i, value=h)
        c.font = HDR_F
        c.fill = HDR_FILL
        c.border = BOX
        c.alignment = WRAP_C
    ws.row_dimensions[start_row].height = 28

    for r, data in enumerate(rows, start=start_row + 1):
        for i, val in enumerate(data, start=1):
            c = ws.cell(row=r, column=i, value=val)
            c.font = BODY_F
            c.border = BOX
            c.alignment = WRAP if i in wrap_cols else Alignment(vertical="top")
            if (r - start_row) % 2 == 0:
                c.fill = BAND_FILL

    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    return start_row + len(rows) + 2


def section(ws, row, text):
    c = ws.cell(row=row, column=1, value=text)
    c.font = H1_F
    return row + 1


def note(ws, row, text):
    c = ws.cell(row=row, column=1, value=text)
    c.font = NOTE_F
    return row + 1


# --------------------------------------------------------------------------
wb = Workbook()
wb.remove(wb.active)

# ---- 00 Cover -------------------------------------------------------------
ws = wb.create_sheet("00_Cover")
ws.sheet_view.showGridLines = False
ws["A1"] = "Project Resource Assignment Program (PRAP)"
ws["A1"].font = Font(name=FONT, size=20, bold=True, color=NAVY)
ws["A2"] = "Application Development Plan"
ws["A2"].font = Font(name=FONT, size=14, color=NAVY)

cover = [
    ("Document ID", "PRAP-PLAN-001"),
    ("Document type", "Development plan (Step 1 deliverable)"),
    ("Version", f"v{DOC_VERSION}"),
    ("Status", DOC_STATUS),
    ("Issue date", DOC_DATE),
    ("Author", "Claude Code (drafted from requirements supplied by the requester)"),
    ("Reviewer / Approver", "Requester (pending)"),
    ("Repository", "Dan5050-now/project1"),
    ("Branch", "claude/project-resource-assignment-app-1vjdzh"),
    ("Supersedes", "None - first issue"),
]
r = 4
for k, v in cover:
    ws.cell(row=r, column=1, value=k).font = BOLD_F
    c = ws.cell(row=r, column=2, value=v)
    c.font = BODY_F
    c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 78

r += 1
r = section(ws, r, "Purpose of this document")
for line in [
    "This plan defines what the Project Resource Assignment Program is, what it must do, how it will be built,",
    "and how the work is broken into the five agreed development steps. It is the controlling document for",
    "Step 1 and the direct input to the Step 2 programming specification.",
    "",
    "Every requirement carries a REQ-ID (sheet 03). The specification, the code, and the test evidence all",
    "trace back to those IDs, so nothing agreed here can be silently dropped later.",
]:
    ws.cell(row=r, column=1, value=line).font = BODY_F
    r += 1

r += 1
r = section(ws, r, "How to read this workbook")
guide = [
    ("00_Cover", "Document control and reading guide."),
    ("01_Version_History", "Change log for this plan. Every re-issue adds a row."),
    ("02_Scope", "Background, objectives, in scope / out of scope."),
    ("03_Requirements", "Numbered requirement register - the contract for Steps 2-5."),
    ("04_Data_Model", "Every field held for a project and for a person, with type and rules."),
    ("05_Resource_Logic", "The calculation that turns assignments and weights into monthly resource."),
    ("06_Dashboard_Design", "The three dashboard tabs: tables, graphs, filters."),
    ("07_Architecture", "Single-file HTML + Excel-on-disk design and the file-access decision."),
    ("08_WBS_Schedule", "The five steps broken into tasks, deliverables and review gates."),
    ("09_Version_Control", "How plan, specification and output files are versioned together."),
    ("10_Risks", "Risks and assumptions with mitigations."),
    ("11_Open_Questions", "Decisions needed from the reviewer. YELLOW cells are for your answer."),
    ("12_Review_Log", "Reviewer comments and their disposition."),
]
r = table(ws, r, ["Sheet", "Contents"], guide, [26, 78], wrap_cols=(2,))

# ---- 01 Version history ---------------------------------------------------
ws, r = sheet(
    wb,
    "01_Version_History",
    "Version history",
    "One row per issued version of this development plan. Version numbering rules are on sheet 09_Version_Control.",
)
rows = [
    ["0.1", DOC_DATE, "Claude Code", "-", "First draft issued for review. Built from the requirements supplied by the requester, "
     "incorporating two confirmed decisions: browser file-picker + SheetJS for Excel access (option a), and the five-step plan.", "Draft"],
]
r = table(
    ws, r,
    ["Version", "Date", "Author", "Reviewer", "Summary of change", "Status"],
    rows,
    [10, 12, 18, 14, 86, 14],
    wrap_cols=(5,),
)
r = note(ws, r, "Rule: the plan version, the specification version and the released application version are recorded together on sheet 09_Version_Control.")

# ---- 02 Scope -------------------------------------------------------------
ws, r = sheet(wb, "02_Scope", "Scope and objectives")

r = section(ws, r, "Background - the problem being solved")
for line in [
    "Multiple projects run at the same time, and their timelines change frequently. Deciding who to assign, in which",
    "role, to which project is therefore difficult to do by hand. The resource burden a project places on a person is",
    "not constant: it varies by project, by period within that project, and by the role the person holds.",
    "",
    "Today there is no single view that answers 'who is over-committed next quarter, and on which project?'.",
]:
    ws.cell(row=r, column=1, value=line).font = BODY_F
    r += 1
r += 1

r = section(ws, r, "Objectives")
objectives = [
    ["OBJ-1", "Hold project and person data in one controlled place, kept in Excel files outside the application.",
     "Both source workbooks load without error and round-trip through export."],
    ["OBJ-2", "Simulate monthly resource demand per project and per person, respecting period weights and role factors.",
     "Monthly figures reconcile to a hand-worked example agreed at Step 2."],
    ["OBJ-3", "Make over-allocation visible before it happens.",
     "Any person-month above the configured threshold is flagged on the Overall tab."],
    ["OBJ-4", "Let the user re-run the simulation immediately after a timeline change.",
     "Editing dates in the source Excel and re-loading updates the dashboard with no code change."],
    ["OBJ-5", "Run entirely on a local Windows PC with no install, no server and no network.",
     "The HTML file opens by double-click in Edge and Chrome and works offline."],
]
r = table(ws, r, ["ID", "Objective", "How success is measured"], objectives, [10, 62, 62], wrap_cols=(2, 3))

r = section(ws, r, "In scope")
in_scope = [
    ["Single-file HTML application runnable from local disk on Windows."],
    ["Import of project data and person/assignment data from Excel (.xlsx) via a browser file picker or drag-and-drop."],
    ["Export of the current working data back to .xlsx, so the source files remain the archive of record."],
    ["Monthly resource simulation per project and per person over a user-selected horizon."],
    ["Three dashboard tabs: Overall, Source data (project), Source data (person)."],
    ["Tables plus graphs on the Overall tab."],
    ["Version control of plan, specification and application across the development lifecycle."],
]
r = table(ws, r, ["In scope for v1.0"], in_scope, [130], wrap_cols=(1,))

r = section(ws, r, "Out of scope")
out_scope = [
    ["Multi-user concurrent editing, or any server / database component.", "Requirement is a local single-file HTML tool."],
    ["Authentication, user accounts, permissions.", "No server; the Excel files carry whatever access control the file share provides."],
    ["Automatic writing to the Excel file on disk without user action.", "Browsers cannot do this from a file:// page - see 07_Architecture."],
    ["Cost, budget or salary calculation.", "Not raised in requirements. Can be added later - the data model leaves room."],
    ["Integration with an HR, CTMS or timesheet system.", "Not raised in requirements."],
    ["Resource optimisation / automatic assignment suggestions.", "v1.0 reports and simulates; it does not decide. Candidate for a later version."],
]
r = table(ws, r, ["Excluded from v1.0", "Reason"], out_scope, [72, 62], wrap_cols=(1, 2))

r = section(ws, r, "Users")
users = [
    ["Resource planner / manager", "Primary", "Loads the source files, reviews monthly simulation, spots over-allocation, tries timeline scenarios."],
    ["Project lead", "Secondary", "Checks the resource profile of their own project and who is assigned in which role."],
    ["Data maintainer", "Secondary", "Keeps the two source Excel files accurate; may be the same person as the planner."],
]
r = table(ws, r, ["User", "Type", "What they do with the application"], users, [28, 12, 94], wrap_cols=(3,))

# ---- 03 Requirements ------------------------------------------------------
ws, r = sheet(
    wb, "03_Requirements", "Requirement register",
    "The contract for Steps 2-5. Every specification section and every code module cites the REQ-IDs it satisfies.",
)

reqs = [
    # id, category, requirement, priority, source, step
    ["REQ-OUT-01", "Output", "The application is a single HTML file that runs on a local Windows PC by double-click, with no install and no network access.", "Must", "Requester", "4"],
    ["REQ-OUT-02", "Output", "All program logic (HTML, CSS, JavaScript, libraries) is embedded in that one HTML file so it can be copied between PCs as a single artifact.", "Must", "Requester", "4"],
    ["REQ-OUT-03", "Output", "Source data lives in Excel file(s) held separately from the HTML file, and those files are the archive of record.", "Must", "Requester", "4"],
    ["REQ-OUT-04", "Output", "The application reads the source Excel files and uses them to drive every table and graph.", "Must", "Requester", "4"],
    ["REQ-OUT-05", "Output", "Plans and specifications are delivered as Excel workbooks.", "Must", "Requester", "1,2"],

    ["REQ-PRJ-01", "Project data", "Each project records a project type, restricted to 'Clinical Trial' or 'Others'.", "Must", "Requester", "2"],
    ["REQ-PRJ-02", "Project data", "Each project records a project category. Where type = 'Clinical Trial' the category is the product name; the field is optional for 'Others'.", "Must", "Requester", "2"],
    ["REQ-PRJ-03", "Project data", "Each project records a project name, unique within the source file.", "Must", "Requester", "2"],
    ["REQ-PRJ-04", "Project data", "Each project records its conditions: outsourcing type, which party prepares which system, and the number of project members.", "Must", "Requester", "2"],
    ["REQ-PRJ-05", "Project data", "Each project records a timeline: start date, major milestone dates, and total period.", "Must", "Requester", "2"],
    ["REQ-PRJ-06", "Project data", "Each project carries a resource weight applicable to a defined period, so burden can differ across the project's phases.", "Must", "Requester", "2"],
    ["REQ-PRJ-07", "Project data", "The project record accepts further project-related information without a schema change (free/extension columns).", "Should", "Requester", "2"],
    ["REQ-PRJ-08", "Project data", "Total period is derived from start and end dates rather than typed by hand, so it cannot contradict the timeline.", "Should", "Derived", "2"],

    ["REQ-PSN-01", "Person data", "Data is managed by person, by project assigned, and by project role assigned.", "Must", "Requester", "2"],
    ["REQ-PSN-02", "Person data", "Each assignment records the project(s) the person is assigned to.", "Must", "Requester", "2"],
    ["REQ-PSN-03", "Person data", "Each assignment records the role(s) the person holds on that project.", "Must", "Requester", "2"],
    ["REQ-PSN-04", "Person data", "Each assignment records the start date the person joins and the end date they leave that study.", "Must", "Requester", "2"],
    ["REQ-PSN-05", "Person data", "Each assignment carries a personal resource weight applicable to defined periods.", "Must", "Requester", "2"],
    ["REQ-PSN-06", "Person data", "The person record accepts further project-related information without a schema change.", "Should", "Requester", "2"],
    ["REQ-PSN-07", "Person data", "One person may hold assignments on several projects simultaneously, and may hold more than one role on the same project.", "Must", "Derived", "2"],

    ["REQ-CAL-01", "Calculation", "Resource is simulated on a monthly grid across a user-selected horizon.", "Must", "Requester", "4"],
    ["REQ-CAL-02", "Calculation", "Monthly load for an assignment combines base allocation, project period weight, personal period weight, role factor and the fraction of the month actually covered.", "Must", "Derived", "2,4"],
    ["REQ-CAL-03", "Calculation", "Project monthly load is the sum of its assignments; person monthly load is the sum across all their projects.", "Must", "Requester", "4"],
    ["REQ-CAL-04", "Calculation", "A person-month exceeding the configured capacity threshold is flagged as over-allocated.", "Must", "Derived", "4"],
    ["REQ-CAL-05", "Calculation", "A partial first or last month is pro-rated by calendar days, not counted as a whole month.", "Should", "Derived", "4"],
    ["REQ-CAL-06", "Calculation", "All weights and factors are data, held in the source Excel, never hardcoded in the program.", "Must", "Derived", "4"],

    ["REQ-DSH-01", "Dashboard", "Tab 'Overall' shows monthly resource simulation per project and per person as tables.", "Must", "Requester", "3,4"],
    ["REQ-DSH-02", "Dashboard", "Tab 'Overall' shows appropriate graphs of the same simulation.", "Must", "Requester", "3,4"],
    ["REQ-DSH-03", "Dashboard", "Tab 'Source data (project)' shows project information as a table.", "Must", "Requester", "3,4"],
    ["REQ-DSH-04", "Dashboard", "Tab 'Source data (person)' shows person information as a table.", "Must", "Requester", "3,4"],
    ["REQ-DSH-05", "Dashboard", "Tables can be filtered by date horizon, project type, project, person and role.", "Should", "Derived", "3,4"],
    ["REQ-DSH-06", "Dashboard", "Any table on screen can be exported to Excel.", "Should", "Derived", "4"],

    ["REQ-IMP-01", "Import/Export", "The user loads the source Excel files through a file picker or drag-and-drop, chosen because a local HTML page cannot open a file from disk unaided.", "Must", "Decision D-01", "4"],
    ["REQ-IMP-02", "Import/Export", "Loading validates the workbook and reports every problem found - missing sheet, missing column, bad date, unknown project reference - without stopping at the first one.", "Must", "Derived", "4"],
    ["REQ-IMP-03", "Import/Export", "A blank source workbook template with correct sheet names, headers and one example row is delivered with the application.", "Must", "Derived", "4"],
    ["REQ-IMP-04", "Import/Export", "The user can export current data back to .xlsx, preserving the template layout so the export can be re-imported.", "Must", "Derived", "4"],
    ["REQ-IMP-05", "Import/Export", "The application records which file was loaded, and when, and shows it on screen.", "Should", "Derived", "4"],
    ["REQ-IMP-06", "Import/Export", "Loaded data may be cached in the browser so re-opening the page does not force a re-import; the cache never replaces the Excel file as the record.", "Could", "Derived", "4"],

    ["REQ-VC-01", "Version control", "Development plan, programming specification and output files are version-controlled together and their versions are cross-referenced.", "Must", "Requester", "1-5"],
    ["REQ-VC-02", "Version control", "The application displays its own version, and the version of the source data schema it expects.", "Must", "Derived", "4"],
    ["REQ-VC-03", "Version control", "Loading a source file whose schema version is newer or older than the application expects produces a clear warning.", "Should", "Derived", "4"],
    ["REQ-VC-04", "Version control", "Every document re-issue adds a version-history row stating what changed and why.", "Must", "Requester", "1-5"],

    ["REQ-NFR-01", "Non-functional", "The application is built so later requirements can be added without restructuring: parsing, calculation and presentation are separated.", "Must", "Requester", "4"],
    ["REQ-NFR-02", "Non-functional", "Works in Microsoft Edge and Google Chrome on Windows 10/11, offline.", "Must", "Derived", "4"],
    ["REQ-NFR-03", "Non-functional", "Handles at least 100 projects, 200 people, 1,000 assignments and a 60-month horizon with a redraw under about 2 seconds.", "Should", "Derived", "4"],
    ["REQ-NFR-04", "Non-functional", "No data leaves the PC: no network calls, no external CDN, no telemetry.", "Must", "Derived", "4"],
    ["REQ-NFR-05", "Non-functional", "Dates are handled unambiguously (ISO yyyy-mm-dd internally) regardless of Windows regional settings.", "Must", "Derived", "4"],
]

r_start = r
r = table(
    ws, r,
    ["REQ-ID", "Category", "Requirement", "Priority", "Source", "Step"],
    reqs,
    [14, 15, 90, 10, 14, 8],
    wrap_cols=(3,),
)
last = r_start + len(reqs)

dv = DataValidation(type="list", formula1='"Must,Should,Could,Won\'t"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"D{r_start + 1}:D{last}")

r = section(ws, r, "Requirement count by priority")
counts = [
    ["Must", f'=COUNTIF(D{r_start + 1}:D{last},"Must")'],
    ["Should", f'=COUNTIF(D{r_start + 1}:D{last},"Should")'],
    ["Could", f'=COUNTIF(D{r_start + 1}:D{last},"Could")'],
    ["Total", f"=COUNTA(A{r_start + 1}:A{last})"],
]
r = table(ws, r, ["Priority", "Count"], counts, [14, 15])
r = note(ws, r, "Counts are live formulas over the register above - adding or re-prioritising a requirement updates them.")
r = note(ws, r, "'Source' = Requester (stated in the request), Derived (engineering consequence, needs confirmation), or a Decision ID from 07_Architecture.")

# ---- 04 Data model --------------------------------------------------------
ws, r = sheet(
    wb, "04_Data_Model", "Data model - source Excel structure",
    "Two workbooks, each with the sheets below. This is the schema the Step 2 specification will fix and the code will parse.",
)

r = section(ws, r, "Workbook 1 - PRAP_SourceData_Project.xlsx")
proj = [
    ["Project", "project_id", "Text", "Yes", "Unique key, e.g. PRJ-001. Referenced by every other sheet.", "REQ-PRJ-03"],
    ["Project", "project_name", "Text", "Yes", "Unique display name.", "REQ-PRJ-03"],
    ["Project", "project_type", "List", "Yes", "'Clinical Trial' or 'Others'.", "REQ-PRJ-01"],
    ["Project", "project_category", "Text", "Conditional", "Product name. Required when project_type = 'Clinical Trial'.", "REQ-PRJ-02"],
    ["Project", "outsourcing_type", "List", "No", "e.g. Full outsourcing / Partial / In-house. List is data-driven, not fixed in code.", "REQ-PRJ-04"],
    ["Project", "system_prepared_by", "List", "No", "Which party prepares the system, e.g. Sponsor / CRO / Vendor.", "REQ-PRJ-04"],
    ["Project", "planned_member_count", "Integer", "No", "Planned number of project members; compared against actual assignments.", "REQ-PRJ-04"],
    ["Project", "start_date", "Date", "Yes", "Project start.", "REQ-PRJ-05"],
    ["Project", "end_date", "Date", "Yes", "Planned project end.", "REQ-PRJ-05"],
    ["Project", "total_period_months", "Derived", "-", "Calculated from start_date and end_date; not entered by hand.", "REQ-PRJ-08"],
    ["Project", "status", "List", "No", "e.g. Planned / Active / On hold / Completed. Drives default dashboard filtering.", "REQ-PRJ-07"],
    ["Project", "note_1 .. note_5", "Text", "No", "Free extension columns for other project-related information.", "REQ-PRJ-07"],
    ["", "", "", "", "", ""],
    ["Milestone", "project_id", "Text", "Yes", "Foreign key to Project.", "REQ-PRJ-05"],
    ["Milestone", "milestone_name", "Text", "Yes", "e.g. FPI, LPI, LPO, DB Lock, CSR. Names are data, not fixed in code.", "REQ-PRJ-05"],
    ["Milestone", "milestone_date", "Date", "Yes", "Planned date.", "REQ-PRJ-05"],
    ["Milestone", "milestone_seq", "Integer", "No", "Display order on the timeline.", "REQ-PRJ-05"],
    ["", "", "", "", "", ""],
    ["ProjectPeriodWeight", "project_id", "Text", "Yes", "Foreign key to Project.", "REQ-PRJ-06"],
    ["ProjectPeriodWeight", "period_name", "Text", "Yes", "e.g. Start-up, Enrolment, Maintenance, Close-out.", "REQ-PRJ-06"],
    ["ProjectPeriodWeight", "period_start", "Date", "Yes", "Inclusive.", "REQ-PRJ-06"],
    ["ProjectPeriodWeight", "period_end", "Date", "Yes", "Inclusive. Periods for one project must not overlap.", "REQ-PRJ-06"],
    ["ProjectPeriodWeight", "weight", "Decimal", "Yes", "Multiplier on effort during this period. 1.00 = normal, 1.50 = 50% heavier.", "REQ-PRJ-06"],
    ["", "", "", "", "", ""],
    ["RoleFactor", "role_name", "Text", "Yes", "e.g. Project Manager, CRA, Data Manager, Statistician.", "REQ-CAL-02"],
    ["RoleFactor", "role_factor", "Decimal", "Yes", "Relative burden of the role. Default 1.00.", "REQ-CAL-02"],
    ["RoleFactor", "role_note", "Text", "No", "Basis for the factor.", "REQ-CAL-06"],
    ["", "", "", "", "", ""],
    ["Config", "parameter", "Text", "Yes", "e.g. schema_version, capacity_threshold, default_horizon_months, capacity_unit.", "REQ-VC-02"],
    ["Config", "value", "Text", "Yes", "The setting. Kept in data so tuning needs no code change.", "REQ-CAL-06"],
]
r = table(ws, r, ["Sheet", "Column", "Type", "Required", "Definition / rule", "REQ-ID"], proj, [22, 24, 11, 12, 76, 14], wrap_cols=(5,))

r = section(ws, r, "Workbook 2 - PRAP_SourceData_Person.xlsx")
person = [
    ["Person", "person_id", "Text", "Yes", "Unique key, e.g. PSN-001.", "REQ-PSN-01"],
    ["Person", "person_name", "Text", "Yes", "Display name.", "REQ-PSN-01"],
    ["Person", "department", "Text", "No", "Grouping for the dashboard.", "REQ-PSN-06"],
    ["Person", "primary_role", "Text", "No", "Usual role; an assignment can override it.", "REQ-PSN-03"],
    ["Person", "capacity", "Decimal", "No", "Available capacity, default 1.00 (= 100%). Basis of the over-allocation flag.", "REQ-CAL-04"],
    ["Person", "employment_start / employment_end", "Date", "No", "Bounds availability; blank end = open.", "REQ-PSN-04"],
    ["Person", "note_1 .. note_5", "Text", "No", "Free extension columns.", "REQ-PSN-06"],
    ["", "", "", "", "", ""],
    ["Assignment", "assignment_id", "Text", "Yes", "Unique key. One row per person + project + role.", "REQ-PSN-07"],
    ["Assignment", "person_id", "Text", "Yes", "Foreign key to Person.", "REQ-PSN-01"],
    ["Assignment", "project_id", "Text", "Yes", "Foreign key to Project in workbook 1.", "REQ-PSN-02"],
    ["Assignment", "role_name", "Text", "Yes", "Foreign key to RoleFactor. Several rows = several roles on one project.", "REQ-PSN-03"],
    ["Assignment", "assign_start_date", "Date", "Yes", "Date the person joins the study.", "REQ-PSN-04"],
    ["Assignment", "assign_end_date", "Date", "Yes", "Date the person leaves the study. Blank = runs to project end.", "REQ-PSN-04"],
    ["Assignment", "base_allocation", "Decimal", "Yes", "Baseline share of the person's capacity, e.g. 0.40 = 40%.", "REQ-CAL-02"],
    ["Assignment", "note_1 .. note_3", "Text", "No", "Free extension columns.", "REQ-PSN-06"],
    ["", "", "", "", "", ""],
    ["PersonPeriodWeight", "assignment_id", "Text", "Yes", "Foreign key to Assignment.", "REQ-PSN-05"],
    ["PersonPeriodWeight", "period_start", "Date", "Yes", "Inclusive.", "REQ-PSN-05"],
    ["PersonPeriodWeight", "period_end", "Date", "Yes", "Inclusive. Periods within one assignment must not overlap.", "REQ-PSN-05"],
    ["PersonPeriodWeight", "weight", "Decimal", "Yes", "Multiplier for this person on this assignment in this period. Default 1.00 where no row exists.", "REQ-PSN-05"],
    ["PersonPeriodWeight", "reason", "Text", "No", "Why the weight differs, e.g. 'part-time', 'covering start-up peak'.", "REQ-PSN-05"],
]
r = table(ws, r, ["Sheet", "Column", "Type", "Required", "Definition / rule", "REQ-ID"], person, [22, 24, 11, 12, 76, 14], wrap_cols=(5,))

r = section(ws, r, "Referential rules checked on import")
rules = [
    ["V-01", "Every Assignment.project_id exists in Project.", "Error - row rejected, reported with its row number."],
    ["V-02", "Every Assignment.person_id exists in Person.", "Error - row rejected."],
    ["V-03", "Every Assignment.role_name exists in RoleFactor.", "Warning - role factor defaults to 1.00."],
    ["V-04", "project_category is present when project_type = 'Clinical Trial'.", "Warning - shown as blank in the dashboard."],
    ["V-05", "end_date is on or after start_date, for projects, assignments and all weight periods.", "Error - row rejected."],
    ["V-06", "Weight periods within one project, and within one assignment, do not overlap.", "Error - overlapping pair reported."],
    ["V-07", "Assignment dates fall inside the project's own start and end dates.", "Warning - kept, but listed for review."],
    ["V-08", "project_id, person_id and assignment_id are unique in their sheet.", "Error - duplicate rejected."],
    ["V-09", "schema_version in Config matches the version the application expects.", "Warning - proceeds, banner shown."],
]
r = table(ws, r, ["ID", "Rule", "On failure"], rules, [8, 84, 54], wrap_cols=(2, 3))
r = note(ws, r, "Import never stops at the first problem: it collects every finding and presents one report (REQ-IMP-02).")

# ---- 05 Resource logic ----------------------------------------------------
ws, r = sheet(
    wb, "05_Resource_Logic", "Resource calculation logic",
    "The core of the application. Step 2 will fix this as pseudocode plus a worked example to test against.",
)

r = section(ws, r, "Monthly load for one assignment, in one month")
for line in [
    "    load(assignment, month) = base_allocation",
    "                            x project_period_weight(project, month)",
    "                            x person_period_weight(assignment, month)",
    "                            x role_factor(role)",
    "                            x coverage(assignment, month)",
    "",
    "coverage = (days in the month that fall inside the assignment's start..end window) / (days in that month).",
    "It is 1.00 for a fully covered month, and a fraction for the joining and leaving months (REQ-CAL-05).",
    "Where no weight period covers the month, the weight defaults to 1.00 rather than to zero.",
]:
    c = ws.cell(row=r, column=1, value=line)
    c.font = Font(name="Consolas", size=10) if line.startswith(" ") else BODY_F
    r += 1
r += 1

r = section(ws, r, "Aggregation")
agg = [
    ["Per project, per month", "Sum of load over every assignment on that project.", "Overall tab, project table + stacked graph", "REQ-CAL-03"],
    ["Per person, per month", "Sum of load over every assignment that person holds, across all projects.", "Overall tab, person table + graph", "REQ-CAL-03"],
    ["Per person, per project, per month", "The individual load value.", "Drill-down when a person row is expanded", "REQ-CAL-03"],
    ["Over-allocation flag", "Raised when person-month total > capacity x capacity_threshold.", "Cell highlight + count of flagged person-months", "REQ-CAL-04"],
    ["Head-count per project, per month", "Count of assignments with load > 0 that month.", "Compared against planned_member_count", "REQ-PRJ-04"],
]
r = table(ws, r, ["Output", "How it is computed", "Where it appears", "REQ-ID"], agg, [32, 62, 46, 14], wrap_cols=(2, 3))

r = section(ws, r, "Worked example - to be confirmed at Step 2 review")
ex = [
    ["Assignment", "PSN-001 (Kim) on PRJ-001, role = Project Manager", ""],
    ["base_allocation", "0.40", "40% of capacity as the baseline"],
    ["Assignment window", "2026-03-10 to 2026-12-31", "Joins part-way through March"],
    ["Project period weight", "1.50 for 2026-01-01..2026-06-30 (Start-up)", "Start-up is 50% heavier"],
    ["Person period weight", "1.00 (no row)", "Defaults to 1.00"],
    ["Role factor", "1.20 for Project Manager", ""],
    ["Coverage, March 2026", "22 / 31 = 0.7097", "10 Mar to 31 Mar inclusive = 22 days"],
    ["Load, March 2026", "0.40 x 1.50 x 1.00 x 1.20 x 0.7097 = 0.511", "51.1% of capacity"],
    ["Load, April 2026", "0.40 x 1.50 x 1.00 x 1.20 x 1.0000 = 0.720", "Full month inside Start-up"],
    ["Load, July 2026", "0.40 x 1.00 x 1.00 x 1.20 x 1.0000 = 0.480", "Start-up weight no longer applies"],
]
r = table(ws, r, ["Element", "Value", "Note"], ex, [30, 62, 46], wrap_cols=(2, 3))
r = note(ws, r, "This example becomes the acceptance test for the calculation engine. Please confirm at Step 2 that these numbers match how you reason about burden today.")

r = section(ws, r, "Design decisions inside the calculation - confirm at review")
dec = [
    ["C-01", "Weights multiply rather than add.", "Multiplication keeps each factor independent and proportional. Adding would make a 1.5 project weight mean different things at different allocations.", "Confirm"],
    ["C-02", "Partial months are pro-rated by calendar days.", "Calendar days need no working-day calendar and no holiday table. Working days are a later option if you need them.", "Confirm"],
    ["C-03", "Missing weight row means 1.00, not 0.00.", "A person with no explicit weight should carry a normal load, not disappear from the simulation.", "Confirm"],
    ["C-04", "Capacity is expressed as a fraction where 1.00 = one full-time person.", "Keeps person and project totals directly comparable and makes over-allocation obvious at a glance.", "Confirm"],
    ["C-05", "The unit shown on screen is % of capacity, with FTE available as an alternative.", "Set by capacity_unit in Config, so it can change without code.", "Confirm"],
]
r = table(ws, r, ["ID", "Decision", "Rationale", "Status"], dec, [8, 44, 76, 12], wrap_cols=(2, 3))

# ---- 06 Dashboard ---------------------------------------------------------
ws, r = sheet(wb, "06_Dashboard_Design", "Dashboard design", "Three tabs as specified. Detailed layout is fixed at the Step 3 UI review.")

r = section(ws, r, "Tab 1 - Overall")
overall = [
    ["Control bar", "Horizon from / to (month), project type, project, person, role, department. Plus 'Load files', 'Export', and the loaded-file name and time.", "REQ-DSH-05, REQ-IMP-05"],
    ["Table A - resource by project", "Rows = project, columns = months, cells = monthly load. Row total and column total. Expanding a project reveals its assigned people.", "REQ-DSH-01"],
    ["Table B - resource by person", "Rows = person, columns = months, cells = summed load across projects. Over-allocated cells highlighted. Expanding a person reveals their projects.", "REQ-DSH-01, REQ-CAL-04"],
    ["Graph 1 - stacked area or bar, by project", "Total monthly demand, one band per project. Shows how demand builds and where the peaks land.", "REQ-DSH-02"],
    ["Graph 2 - grouped bar, by person", "Monthly load per person with a capacity reference line, so over-allocation is visible.", "REQ-DSH-02, REQ-CAL-04"],
    ["Graph 3 - project timeline (Gantt-style)", "One bar per project across the horizon with milestone markers and period-weight shading.", "REQ-DSH-02, REQ-PRJ-05"],
    ["Summary tiles", "Active projects, people assigned, total demand in the horizon, count of over-allocated person-months.", "REQ-DSH-01"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], overall, [34, 92, 20], wrap_cols=(2,))

r = section(ws, r, "Tab 2 - Source data (project)")
p2 = [
    ["Project table", "Every project column from 04_Data_Model, sortable and filterable, with derived total period shown.", "REQ-DSH-03"],
    ["Milestone sub-table", "Milestones of the selected project, in sequence.", "REQ-PRJ-05"],
    ["Period weight sub-table", "The selected project's periods and their weights.", "REQ-PRJ-06"],
    ["Export", "Export the visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], p2, [34, 92, 20], wrap_cols=(2,))

r = section(ws, r, "Tab 3 - Source data (person)")
p3 = [
    ["Person table", "Every person column from 04_Data_Model, sortable and filterable.", "REQ-DSH-04"],
    ["Assignment sub-table", "The selected person's assignments: project, role, start, end, base allocation.", "REQ-PSN-02, REQ-PSN-03"],
    ["Person period weight sub-table", "Weight periods for the selected assignment.", "REQ-PSN-05"],
    ["Export", "Export the visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], p3, [34, 92, 20], wrap_cols=(2,))

r = section(ws, r, "Cross-cutting UI rules")
ui = [
    ["A validation banner appears whenever the last import produced findings, and opens the full report on click."],
    ["Empty state: with nothing loaded, every tab shows the same clear 'Load your source Excel files' panel and a link to download the blank template."],
    ["The application version and expected schema version are shown in the footer at all times (REQ-VC-02)."],
    ["Nothing on screen is editable in v1.0 - the Excel files remain the single place data is changed."],
]
r = table(ws, r, ["Rule"], ui, [146], wrap_cols=(1,))

# ---- 07 Architecture ------------------------------------------------------
ws, r = sheet(wb, "07_Architecture", "Architecture and technical approach")

r = section(ws, r, "Decision D-01 - how the HTML file reads the Excel data  [CONFIRMED: option (a)]")
for line in [
    "A page opened from local disk (file://) cannot read an .xlsx from a fixed path on its own - the browser's",
    "security model blocks it, and no setting on a standard corporate Windows PC changes that safely.",
    "The options considered, and the one you confirmed:",
]:
    ws.cell(row=r, column=1, value=line).font = BODY_F
    r += 1
r += 1
opts = [
    ["(a)", "User selects the .xlsx through a file picker or drag-and-drop; an embedded SheetJS-style parser reads it in memory.",
     "True .xlsx support; no install; no server; user stays in control of which file is loaded.",
     "The file must be selected each session (mitigated by optional browser caching, REQ-IMP-06).", "CONFIRMED - adopted"],
    ["(b)", "Data kept as .csv next to the HTML, still opened through a picker.",
     "Simplest possible parsing.", "Loses Excel formatting, multiple sheets and data validation - a poor fit for an archive of record.", "Rejected"],
    ["(c)", "Excel is only an export target; the browser's local storage is the working record.",
     "No load step at all.", "Contradicts the requirement that the Excel file is the archive of record; clearing browser data would lose everything.", "Rejected"],
]
r = table(ws, r, ["Option", "Description", "Advantages", "Disadvantages", "Outcome"], opts, [9, 50, 40, 46, 18], wrap_cols=(2, 3, 4))
r = note(ws, r, "Consequence: REQ-IMP-01 and REQ-IMP-06 exist because of this decision. The Excel files stay the archive of record in all cases.")

r = section(ws, r, "Technology")
tech = [
    ["Container", "One .html file, opened by double-click.", "REQ-OUT-01"],
    ["Excel parsing/writing", "SheetJS (xlsx) community build, embedded inline in the HTML - no CDN, so it works offline.", "REQ-OUT-02, REQ-NFR-04"],
    ["Charts", "Inline SVG drawn by the application's own code, or a small embedded chart library. No external requests either way.", "REQ-DSH-02, REQ-NFR-04"],
    ["Framework", "None. Plain modern JavaScript. A build step or framework would add a toolchain the requirement does not want.", "REQ-OUT-02"],
    ["Styling", "Embedded CSS. Readable on a laptop screen and when printed.", "REQ-OUT-01"],
    ["Persistence", "Optional browser localStorage cache of the last load, clearly marked as a convenience, never as the record.", "REQ-IMP-06"],
]
r = table(ws, r, ["Concern", "Choice and reason", "REQ-ID"], tech, [24, 108, 18], wrap_cols=(2,))

r = section(ws, r, "Internal structure - built for later change (REQ-NFR-01)")
layers = [
    ["1. IO layer", "Reads the chosen workbook into raw rows; writes .xlsx on export.", "Swapping the file-access method touches this layer only."],
    ["2. Validation layer", "Applies rules V-01..V-09, produces one findings report.", "New rules are added here without touching parsing or maths."],
    ["3. Model layer", "Typed in-memory objects: Project, Milestone, PeriodWeight, Person, Assignment, Config.", "New fields are added here and flow outward."],
    ["4. Calculation layer", "The monthly engine of 05_Resource_Logic. Pure functions - no DOM, no file access.", "Directly unit-testable, and the piece most likely to be refined after you review real output."],
    ["5. Presentation layer", "Tabs, tables, graphs, filters, export buttons.", "A new tab or graph is added here alone."],
]
r = table(ws, r, ["Layer", "Responsibility", "Why the boundary is there"], layers, [22, 66, 62], wrap_cols=(2, 3))
r = note(ws, r, "The calculation layer never touches the screen and never touches files. That is what makes both future requirement changes and testing cheap.")

r = section(ws, r, "Deployment")
dep = [
    ["The user keeps one folder containing the .html file and the two source .xlsx files. Copying the folder moves the whole tool."],
    ["Updating the application means replacing the .html file. Source data is untouched, because it lives outside it (REQ-OUT-03)."],
    ["The application checks the source schema version on load and warns on a mismatch (REQ-VC-03)."],
]
r = table(ws, r, ["Point"], dep, [146], wrap_cols=(1,))

# ---- 08 WBS ---------------------------------------------------------------
ws, r = sheet(wb, "08_WBS_Schedule", "Work breakdown - the five steps", "Each step ends at a review gate. Work on the next step starts only after that gate is passed.")

wbs = [
    ["1", "1.1", "Draft the development plan (this workbook).", "PRAP_Development_Plan_v0.1.xlsx", "Complete - issued for review"],
    ["1", "1.2", "Requester reviews; answers the open questions on sheet 11.", "Review comments", "Pending you"],
    ["1", "1.3", "Re-issue the plan incorporating comments.", "PRAP_Development_Plan_v1.0.xlsx", "Not started"],
    ["1", "G1", "GATE 1 - development plan approved.", "Approval recorded on 12_Review_Log", "Not started"],

    ["2", "2.1", "Fix the source Excel schema: exact sheet names, column headers, types, validation lists.", "Specification sheet 'Data schema'", "Not started"],
    ["2", "2.2", "Specify the calculation engine as pseudocode plus the worked example as an acceptance test.", "Specification sheet 'Calculation'", "Not started"],
    ["2", "2.3", "Specify import validation rules and the findings report.", "Specification sheet 'Validation'", "Not started"],
    ["2", "2.4", "Specify each dashboard tab: every table, column, graph, filter and interaction.", "Specification sheet 'UI spec'", "Not started"],
    ["2", "2.5", "Specify export format and the version/compatibility check.", "Specification sheet 'IO & versioning'", "Not started"],
    ["2", "2.6", "Build the requirement-to-specification traceability matrix.", "Specification sheet 'Traceability'", "Not started"],
    ["2", "G2", "GATE 2 - programming specification approved.", "PRAP_Programming_Specification_v1.0.xlsx", "Not started"],

    ["3", "3.1", "High-level UI design: tab structure, page regions, navigation. No code behind it.", "Prototype HTML (UI only)", "Not started"],
    ["3", "3.2", "Requester reviews the high-level component design.", "Review comments", "Not started"],
    ["3", "3.3", "Final UI design with clear per-component requirements.", "Prototype HTML v1.0 + component list", "Not started"],
    ["3", "G3", "GATE 3 - final design and component list approved. Code generation starts only for approved components.", "Approved component list", "Not started"],

    ["4", "4.1", "IO layer: workbook load, sheet/column mapping, export.", "Application code", "Not started"],
    ["4", "4.2", "Validation layer: rules V-01..V-09 and the findings report.", "Application code", "Not started"],
    ["4", "4.3", "Model layer and Config handling.", "Application code", "Not started"],
    ["4", "4.4", "Calculation engine, verified against the worked example.", "Application code + test evidence", "Not started"],
    ["4", "4.5", "Overall tab: tables, graphs, filters, over-allocation flagging.", "Application code", "Not started"],
    ["4", "4.6", "Source data (project) and Source data (person) tabs.", "Application code", "Not started"],
    ["4", "4.7", "Blank source workbook template with example rows.", "Two .xlsx templates", "Not started"],
    ["4", "4.8", "Requester reviews output against real data; refinements folded in.", "Updated code", "Not started"],
    ["4", "G4", "GATE 4 - application functionally complete.", "PRAP_Application_v0.9.html", "Not started"],

    ["5", "5.1", "Full pass over the traceability matrix: every Must requirement demonstrated.", "Completed traceability matrix", "Not started"],
    ["5", "5.2", "Test on a clean Windows PC in Edge and Chrome, offline.", "Test evidence", "Not started"],
    ["5", "5.3", "Write the user guide: folder layout, how to load, how to maintain source data.", "User guide", "Not started"],
    ["5", "5.4", "Final version alignment across plan, specification and application.", "Version alignment table (sheet 09)", "Not started"],
    ["5", "G5", "GATE 5 - release.", "PRAP_Application_v1.0.html", "Not started"],
]
r_start = r
r = table(ws, r, ["Step", "Task", "Activity", "Deliverable", "Status"], wbs, [7, 8, 84, 44, 22], wrap_cols=(3, 4))
last = r_start + len(wbs)

dv2 = DataValidation(type="list", formula1='"Not started,In progress,Pending you,Complete - issued for review,Complete,Blocked"', allow_blank=True)
ws.add_data_validation(dv2)
dv2.add(f"E{r_start + 1}:E{last}")

r = section(ws, r, "Progress")
prog = [
    ["Tasks total", f"=COUNTA(B{r_start + 1}:B{last})"],
    ["Complete", f'=COUNTIF(E{r_start + 1}:E{last},"Complete")+COUNTIF(E{r_start + 1}:E{last},"Complete - issued for review")'],
    ["Awaiting the requester", f'=COUNTIF(E{r_start + 1}:E{last},"Pending you")'],
    ["Not started", f'=COUNTIF(E{r_start + 1}:E{last},"Not started")'],
]
r = table(ws, r, ["Measure", "Count"], prog, [26, 12])
r = note(ws, r, "No duration estimates are given: the pace is set by your review turnaround at each gate, not by build effort. Add dates once the gate rhythm is known.")

# ---- 09 Version control ---------------------------------------------------
ws, r = sheet(wb, "09_Version_Control", "Version control across documents (REQ-VC-01)")

r = section(ws, r, "What is version-controlled")
vc = [
    ["Development plan", "PRAP_Development_Plan_v<ver>.xlsx", "docs/", "Sheet 01_Version_History"],
    ["Programming specification", "PRAP_Programming_Specification_v<ver>.xlsx", "docs/", "Its own version-history sheet"],
    ["Application", "PRAP_Application_v<ver>.html", "app/", "Version constant shown in the footer"],
    ["Source data template", "PRAP_SourceData_Project_v<ver>.xlsx / _Person_v<ver>.xlsx", "templates/", "schema_version in the Config sheet"],
    ["Output / evidence files", "PRAP_<content>_v<ver>_<yyyymmdd>.xlsx", "output/", "Filename plus a header block"],
    ["Generator scripts", "tools/*.py", "tools/", "Git history"],
]
r = table(ws, r, ["Artifact", "Naming convention", "Folder", "Where its version is recorded"], vc, [28, 56, 16, 44], wrap_cols=(2, 4))

r = section(ws, r, "Version numbering")
num = [
    ["0.x", "Draft, under review. Content may change substantially.", "0.1 -> 0.2 on each re-issue during review."],
    ["x.0", "Approved baseline. Changing it requires a new approval.", "0.9 -> 1.0 at the gate."],
    ["x.y", "Approved change against a baseline: added requirement, bug fix, layout change.", "1.0 -> 1.1"],
    ["Schema version", "Independent counter for the source Excel structure. Only steps when a sheet or column changes.", "schema 1 -> 2"],
]
r = table(ws, r, ["Pattern", "Meaning", "Example"], num, [16, 86, 34], wrap_cols=(2,))

r = section(ws, r, "Version alignment - which versions belong together")
align = [
    ["v0.1", "-", "-", "-", DOC_DATE, "Plan issued for review"],
    ["", "", "", "", "", ""],
    ["", "", "", "", "", ""],
]
r = table(ws, r, ["Plan version", "Specification version", "Application version", "Schema version", "Date", "Note"], align, [15, 22, 20, 16, 14, 46], wrap_cols=(6,))
r = note(ws, r, "One row per release. This table answers 'which specification produced this .html, and which source template does it expect?'.")

r = section(ws, r, "Repository rules")
git = [
    ["All work is committed to branch claude/project-resource-assignment-app-1vjdzh."],
    ["Documents are generated from scripts in tools/ so their content is reviewable as a text diff, not only as a binary."],
    ["One commit per meaningful change, with a message naming the step and the affected REQ-IDs."],
    ["A released version is tagged, so any release can be reproduced exactly."],
]
r = table(ws, r, ["Rule"], git, [146], wrap_cols=(1,))

# ---- 10 Risks -------------------------------------------------------------
ws, r = sheet(wb, "10_Risks", "Risks and assumptions")

r = section(ws, r, "Risks")
risks = [
    ["R-01", "The resource formula does not match how burden is actually judged in your workplace, so output looks wrong.", "High", "High",
     "A worked example (sheet 05) is agreed at Step 2 before any code is written, and every factor stays in the data so it can be re-tuned without code."],
    ["R-02", "The source Excel is maintained inconsistently - typos in project names, overlapping periods - and the simulation silently misleads.", "High", "Medium",
     "Nine validation rules run on every import, ID-based references instead of name matching, and a findings report the user cannot miss."],
    ["R-03", "Corporate policy blocks local .html files or restricts the browser.", "Low", "High",
     "No install, no network, no external file needed. Worth confirming early on a real work PC - see Q-05."],
    ["R-04", "Requirements grow after you see real output.", "High", "Medium",
     "Expected, and planned for: five separated layers (sheet 07) plus extension columns already in the schema."],
    ["R-05", "Data volume grows beyond what a browser handles comfortably.", "Low", "Medium",
     "Targets set in REQ-NFR-03 and tested at Step 5; the calculation layer can move to a worker if ever needed."],
    ["R-06", "Excel date handling differs between Windows regional settings and misreads dates.", "Medium", "High",
     "Dates are normalised to ISO on import, and any unparseable date is a hard error, never a guess (REQ-NFR-05)."],
    ["R-07", "The file must be re-selected each session and this becomes irritating.", "Medium", "Low",
     "Optional browser caching (REQ-IMP-06) plus a one-click reload of the last file."],
]
r = table(ws, r, ["ID", "Risk", "Likelihood", "Impact", "Mitigation"], risks, [8, 62, 13, 11, 62], wrap_cols=(2, 5))

r = section(ws, r, "Assumptions - correct these at review if any is wrong")
assum = [
    ["A-01", "Data volume is on the order of tens of projects and hundreds of people, not tens of thousands."],
    ["A-02", "One person's capacity is expressed as a fraction where 1.00 = fully committed."],
    ["A-03", "Monthly granularity is sufficient; weekly or daily simulation is not required in v1.0."],
    ["A-04", "Source Excel files are maintained by hand, not generated by another system."],
    ["A-05", "Windows 10 or 11 with Edge or Chrome available."],
    ["A-06", "Only one person maintains the source files at a time - no concurrent editing to reconcile."],
    ["A-07", "Milestone dates are informational for v1.0: they are displayed, but do not themselves drive resource weight."],
]
r = table(ws, r, ["ID", "Assumption"], assum, [8, 138], wrap_cols=(2,))

# ---- 11 Open questions ----------------------------------------------------
ws, r = sheet(
    wb, "11_Open_Questions", "Open questions for the reviewer",
    "Please answer in the YELLOW cells. These are the points where a wrong guess would cost real rework.",
)
qs = [
    ["Q-01", "Calculation", "Do you agree weights multiply (base x project weight x person weight x role factor)? If your practice is different - for example role sets the load outright rather than scaling it - say so now.", "2", ""],
    ["Q-02", "Calculation", "Is pro-rating a partial month by calendar days right, or should a person joining mid-month count as a whole month?", "2", ""],
    ["Q-03", "Roles", "Please list the roles actually used, and whether each carries a different burden factor. This drives the RoleFactor sheet.", "2", ""],
    ["Q-04", "Project periods", "What are the standard period names (e.g. Start-up / Enrolment / Maintenance / Close-out) and typical weights? Do they differ between 'Clinical Trial' and 'Others'?", "2", ""],
    ["Q-05", "Environment", "Can you open a local .html file in Edge or Chrome on your work PC? If corporate policy blocks it, we need to know before Step 4.", "1", ""],
    ["Q-06", "Data volume", "Roughly how many projects, people and simultaneous assignments? Confirms the performance target in REQ-NFR-03.", "1", ""],
    ["Q-07", "Milestones", "Which milestones do you track (FPI, LPI, DB Lock...)? Are they a fixed list, or does it vary by project?", "2", ""],
    ["Q-08", "Capacity", "Is one person always 1.00 capacity, or do part-time staff need a different capacity value? What over-allocation threshold should flag - above 100%, or above some buffer like 85%?", "2", ""],
    ["Q-09", "Source files", "Two separate workbooks (project / person), or a single workbook with all sheets in it? Two is assumed; one is simpler to hand around.", "1", ""],
    ["Q-10", "Existing data", "Do you already hold this data in a spreadsheet? If you can share the structure (or a de-identified sample), the template can match what you already use.", "1", ""],
    ["Q-11", "Horizon", "What planning horizon matters - 12, 24, 36 months? Sets the default view.", "2", ""],
    ["Q-12", "Scope check", "Anything in 'Out of scope' on sheet 02 that you actually need in v1.0?", "1", ""],
]
r_start = r
r = table(ws, r, ["ID", "Topic", "Question", "Needed by step", "Your answer"], qs, [8, 16, 84, 14, 48], wrap_cols=(3, 5))
for rr in range(r_start + 1, r_start + 1 + len(qs)):
    c = ws.cell(row=rr, column=5)
    c.fill = INPUT_FILL
    c.border = BOX
r = note(ws, r, "YELLOW = for you to complete. Anything left blank will be built to the assumption stated on sheet 10, and flagged as such.")

# ---- 12 Review log --------------------------------------------------------
ws, r = sheet(wb, "12_Review_Log", "Review log and approval", "One row per reviewer comment, with what was done about it.")
log = [["", "", "", "", "", ""] for _ in range(10)]
r_start = r
r = table(ws, r, ["No.", "Sheet / cell", "Reviewer comment", "Response", "Action taken", "Status"], log, [7, 20, 62, 52, 40, 14], wrap_cols=(3, 4, 5))
for rr in range(r_start + 1, r_start + 1 + len(log)):
    for cc in (1, 2, 3, 6):
        ws.cell(row=rr, column=cc).fill = INPUT_FILL

dv3 = DataValidation(type="list", formula1='"Open,Accepted,Rejected,Deferred,Closed"', allow_blank=True)
ws.add_data_validation(dv3)
dv3.add(f"F{r_start + 1}:F{r_start + len(log)}")

r = section(ws, r, "Approval - Gate 1")
appr = [["Development plan v___", "", "", "Approved / Approved with comments / Not approved"]]
r_start2 = r
r = table(ws, r, ["Document", "Approver", "Date", "Decision"], appr, [30, 26, 16, 46], wrap_cols=(4,))
for cc in (2, 3, 4):
    ws.cell(row=r_start2 + 1, column=cc).fill = INPUT_FILL
r = note(ws, r, "Step 2 begins only once this gate is recorded as approved.")

wb.save(OUT)
print(f"Written: {OUT}")
