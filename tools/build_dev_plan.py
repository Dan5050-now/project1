"""Generate the Project Resource Assignment Program (PRAP) development plan workbook.

The workbook is a generated artifact: edit this script, re-run it, and commit both
so the plan stays diffable under version control.

    python tools/build_dev_plan.py

Output: docs/PRAP_Development_Plan_v0.2.xlsx

v0.1 is rebuildable from commit 45412d1.
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

DOC_VERSION = "1.0"
DOC_STATUS = "APPROVED BASELINE - Gate 1 passed 2026-08-01"
DOC_DATE = "2026-07-31"
OUT = Path(__file__).resolve().parents[1] / "docs" / f"PRAP_Development_Plan_v{DOC_VERSION}.xlsx"

FONT = "Arial"
NAVY = "1F3864"
BLUE_HDR = "2F5597"
BAND = "F2F5FB"
YELLOW = "FFFF00"
GREEN = "C6E0B4"
ORANGE = "FCE4D6"
GREY = "808080"

TITLE_F = Font(name=FONT, size=16, bold=True, color=NAVY)
H1_F = Font(name=FONT, size=12, bold=True, color=NAVY)
HDR_F = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_F = Font(name=FONT, size=10)
BOLD_F = Font(name=FONT, size=10, bold=True)
NOTE_F = Font(name=FONT, size=9, italic=True, color=GREY)
MONO_F = Font(name="Consolas", size=10)

HDR_FILL = PatternFill("solid", fgColor=BLUE_HDR)
BAND_FILL = PatternFill("solid", fgColor=BAND)
INPUT_FILL = PatternFill("solid", fgColor=YELLOW)
NEW_FILL = PatternFill("solid", fgColor=GREEN)
CHG_FILL = PatternFill("solid", fgColor=ORANGE)

THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

WRAP = Alignment(vertical="top", wrap_text=True)
WRAP_C = Alignment(vertical="top", wrap_text=True, horizontal="center")

# Rows whose first cell starts with these markers get a highlight fill.
MARK_NEW = "[NEW]"
MARK_CHG = "[CHANGED]"


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


def table(ws, start_row, headers, rows, widths, wrap_cols=(), mark_col=None):
    """Write a banded header+body table. Returns the row after the table.

    mark_col: 1-based column whose value may carry a [NEW]/[CHANGED] marker,
    which is stripped and turned into a row highlight.
    """
    for i, h in enumerate(headers, start=1):
        c = ws.cell(row=start_row, column=i, value=h)
        c.font = HDR_F
        c.fill = HDR_FILL
        c.border = BOX
        c.alignment = WRAP_C
    ws.row_dimensions[start_row].height = 28

    for r, data in enumerate(rows, start=start_row + 1):
        data = list(data)
        fill = None
        if mark_col is not None and isinstance(data[mark_col - 1], str):
            v = data[mark_col - 1]
            if v.startswith(MARK_NEW):
                fill = NEW_FILL
                data[mark_col - 1] = v[len(MARK_NEW):].strip()
            elif v.startswith(MARK_CHG):
                fill = CHG_FILL
                data[mark_col - 1] = v[len(MARK_CHG):].strip()
        for i, val in enumerate(data, start=1):
            c = ws.cell(row=r, column=i, value=val)
            c.font = BODY_F
            c.border = BOX
            c.alignment = WRAP if i in wrap_cols else Alignment(vertical="top")
            if fill is not None:
                c.fill = fill
            elif (r - start_row) % 2 == 0:
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


def lines(ws, row, texts, mono=False):
    for t in texts:
        c = ws.cell(row=row, column=1, value=t)
        c.font = MONO_F if (mono and t.startswith(" ")) else BODY_F
        row += 1
    return row


def legend(ws, row):
    ws.cell(row=row, column=1, value="Legend").font = BOLD_F
    row += 1
    for fill, txt in (
        (NEW_FILL, "Green = new in v0.2, added from your review answers."),
        (CHG_FILL, "Orange = changed in v0.2 as a consequence of your review."),
        (INPUT_FILL, "Yellow = still needs your input."),
    ):
        c = ws.cell(row=row, column=1, value=txt)
        c.font = BODY_F
        c.fill = fill
        row += 1
    return row + 1


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
    ("Document type", "Development plan (Step 1 deliverable) - baseline issue"),
    ("Version", f"v{DOC_VERSION}"),
    ("Status", DOC_STATUS),
    ("Issue date", DOC_DATE),
    ("Author", "Claude Code"),
    ("Reviewer", "Requester - four review rounds: v0.11, v0.2, v0.3, v0.4 reviewed"),
    ("Approved by", "Dan, 2026-08-01 - Gate 1 passed"),
    ("Repository", "Dan5050-now/project1"),
    ("Branch", "claude/project-resource-assignment-app-1vjdzh"),
    ("Supersedes", "v0.4 (2026-07-31)"),
]
r = 4
for k, v in cover:
    ws.cell(row=r, column=1, value=k).font = BOLD_F
    c = ws.cell(row=r, column=2, value=v)
    c.font = BODY_F
    c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 26
ws.column_dimensions["B"].width = 84

r += 1
r = section(ws, r, "Status of this issue")
r = lines(ws, r, [
    "This is the final Step 1 issue. Four review rounds produced 28 questions; all 28 are answered and",
    "closed, and the review log carries no open item. The plan is submitted for Gate 1 approval.",
    "",
    "What v1.0 changes from v0.4 is small - the last two answers confirmed the design rather than altering",
    "it. A single close-out is called 'Close-out (final)' (Q-27, as built), and 'Others' projects need no",
    "distinguishing: both their period dates AND their period weights are entered by hand (Q-28). That last",
    "point simplifies the model - PeriodWeightStandard is now a clinical-trial reference table only.",
])
r += 1
r = section(ws, r, "The plan in one page")
r = lines(ws, r, [
    "  Output        One HTML file, opened by double-click on Windows, offline, no install. One Excel",
    "                workbook alongside it holds the data and remains the archive of record.",
    "",
    "  Calculation   load = project period weight x role factor x person weight x month coverage,",
    "                in FTE where 1.00 FTE = 160 hours per month.",
    "                Over-allocated above 1.50 FTE in a month; under-allocated below 0.80 FTE for three",
    "                or more consecutive months, reported as a run.",
    "",
    "  Periods       Clinical Trial: five period names derived from milestone dates and month offsets,",
    "                with Conduct occurring up to twice where an interim DB lock splits it. Weights come",
    "                from the trial's clinical phase.",
    "                Others: three periods, dates and weights both entered by hand.",
    "",
    "  Dashboard     Overall (monthly simulation per project and per person, tables and graphs),",
    "                Source data (project), Source data (person). Every field editable, with identifier",
    "                edits cascading to referencing rows.",
    "",
    "  Build         Five steps, each ending at a review gate. This document closes Step 1.",
])
r += 1
r = section(ws, r, "What approving this document means")
r = lines(ws, r, [
    "Gate 1 approval on sheet 12 baselines the 63 requirements on sheet 03 as the contract for Steps 2-5,",
    "and confirms the six engineering decisions C-06 to C-11 on sheet 05 that were proposed but never",
    "explicitly answered across the review rounds. Those six are listed there with their rationale; if any",
    "is wrong, say so at approval rather than after.",
])

r += 1
r = section(ws, r, "How to read this workbook")
guide = [
    ("00_Cover", "Document control, what changed, reading guide."),
    ("01_Version_History", "Change log for this plan."),
    ("02_Scope", "Background, objectives, in scope / out of scope."),
    ("03_Requirements", "Numbered requirement register - the contract for Steps 2-5."),
    ("04_Data_Model", "Every sheet and column of the single source workbook, with rules."),
    ("05_Resource_Logic", "The calculation that turns assignments and weights into monthly FTE."),
    ("06_Dashboard_Design", "The three dashboard tabs: tables, graphs, filters, editing."),
    ("07_Architecture", "Single-file HTML + Excel-on-disk design and the file-access decision."),
    ("08_WBS_Schedule", "The five steps broken into tasks, deliverables and review gates."),
    ("09_Version_Control", "How plan, specification and output files are versioned together."),
    ("10_Risks", "Risks and assumptions with mitigations."),
    ("11_Open_Questions", "All 28 questions and their answers. Nothing open."),
    ("12_Review_Log", "Every change made across the four review rounds, and why. Gate 1 approval block."),
]
r = table(ws, r, ["Sheet", "Contents"], guide, [26, 84], wrap_cols=(2,))
r = legend(ws, r)

# ---- 01 Version history ---------------------------------------------------
ws, r = sheet(wb, "01_Version_History", "Version history",
              "One row per issued version. Numbering rules are on sheet 09_Version_Control.")
rows = [
    ["0.1", "2026-07-25", "Claude Code", "-",
     "First draft issued for review. Built from the requirements supplied by the requester, incorporating two "
     "confirmed decisions: browser file-picker + SheetJS for Excel access (option a), and the five-step plan.",
     "Superseded"],
    ["0.11", "2026-07-31", "Requester", "Requester",
     "Reviewer mark-up returned as PRAP_Development_Plan_v0.11_reviewed.xlsx. Answered all 12 open questions; "
     "added one Import/Export requirement; added clinical phase, four system-responsibility columns, three "
     "system-name columns, and denormalised name columns to the data model.",
     "Review input"],
    ["0.2", "2026-07-31", "Claude Code", "Requester",
     "Reviewer answers propagated across all sheets: single source workbook; calculation reduced to "
     "project weight x role factor x person weight x coverage; FTE capacity with 1.50 over-allocation and "
     "0.80/3-month under-allocation thresholds; in-application editing added; real role, period and milestone "
     "names adopted; performance target reduced to the stated data volume. Eight follow-up questions raised.",
     "Superseded"],
    ["0.21", DOC_DATE, "Requester", "Requester",
     "Second reviewer mark-up returned as PRAP_Development_Plan_v0.2_reviewed.xlsx, answering Q-13 to Q-20.",
     "Review input"],
    ["0.3", DOC_DATE, "Claude Code", "Requester",
     "Q-13 and Q-17 closed, clearing both blockers. Milestone list replaced (First SIV in, FPI out, DB lock "
     "cut-off and DB lock split interim/final). Period sets made type-specific: Clinical Trial keeps its four, "
     "'Others' gets Planning / Develop / Close. Period boundaries now computed from milestone dates plus month "
     "offsets. outsourcing_type fixed to three values; system_prepared_by dropped. All fields made editable with "
     "cascading referential integrity. Three coverage gaps in the supplied period mapping identified and raised "
     "as Q-21 to Q-23.",
     "Superseded"],
    ["0.31", DOC_DATE, "Requester", "Requester",
     "Third reviewer mark-up returned as PRAP_Development_Plan_v0.3_reviewed.xlsx, answering Q-21 to Q-26.",
     "Review input"],
    ["0.4", DOC_DATE, "Claude Code", "Requester",
     "Period model settled. Close-out starts 3 months before DB lock; a trial with an interim lock carries "
     "two close-out periods with Conduct resuming between them, so 'Conduct' may occur twice and "
     "ProjectPeriod gains period_seq. Clinical-trial period set grows to five names. PeriodWeightStandard "
     "re-keyed on clinical_phase. 'Protocol (v1)' added as the eighth milestone. Derivation verified "
     "contiguous against five timelines including four degenerate ones. Two questions remain.",
     "Superseded"],
    ["0.41", DOC_DATE, "Requester", "Requester",
     "Fourth reviewer mark-up returned as PRAP_Development_Plan_v0.4_reviewed.xlsx, answering Q-27 and Q-28.",
     "Review input"],
    ["1.0", DOC_DATE, "Claude Code", "Pending",
     "FINAL Step 1 issue. Both remaining answers confirmed the v0.4 design. A single close-out keeps the name "
     "'Close-out (final)'. 'Others' projects need no distinguishing and take manual weights as well as manual "
     "dates, so PeriodWeightStandard becomes a clinical-trial reference table only. All 28 review questions "
     "closed; no open items. Issued for Gate 1 approval.",
     "APPROVED 2026-08-01 by Dan"],
]
r = table(ws, r, ["Version", "Date", "Author", "Reviewer", "Summary of change", "Status"],
          rows, [10, 12, 15, 14, 92, 16], wrap_cols=(5,))
r = note(ws, r, "The reviewer's file was named v0.11. Under the numbering rule on sheet 09 that reads as a draft "
                "increment of v0.1, so it is logged above as review input and this incorporating draft is v0.2.")

# ---- 02 Scope -------------------------------------------------------------
ws, r = sheet(wb, "02_Scope", "Scope and objectives")

r = section(ws, r, "Background - the problem being solved")
r = lines(ws, r, [
    "Multiple projects run at the same time, and their timelines change frequently. Deciding who to assign, in which",
    "role, to which project is therefore difficult to do by hand. The resource burden a project places on a person is",
    "not constant: it varies by project, by period within that project, and by the role the person holds.",
    "",
    "Today there is no single view that answers 'who is over-committed next quarter, and on which project?' -",
    "nor the quieter question, 'who has been under-used for three months running?'.",
])
r += 1

r = section(ws, r, "Objectives")
objectives = [
    ["OBJ-1", "Hold project and person data in one controlled place: a single Excel workbook kept outside the application.",
     "The workbook loads without error and round-trips through export.", "Q-09"],
    ["OBJ-2", "Simulate monthly resource demand per project and per person, respecting period weights and role factors.",
     "Monthly FTE reconciles to the worked example on sheet 05.", "Q-01"],
    ["OBJ-3", "Make both over- and under-allocation visible before they bite.",
     "Person-months above 1.50 FTE are flagged; runs of three or more months below 0.80 FTE are flagged.", "Q-08"],
    ["OBJ-4", "Let the user re-run the simulation immediately after a timeline change.",
     "Editing dates in the workbook - or in the application - and re-running updates the dashboard with no code change.", "Q-01"],
    ["OBJ-5", "Run entirely on a local Windows PC with no install, no server and no network.",
     "The HTML file opens by double-click in Edge and Chrome and works offline.", "Q-05"],
]
r = table(ws, r, ["ID", "Objective", "How success is measured", "Basis"],
          objectives, [10, 60, 60, 10], wrap_cols=(2, 3))

r = section(ws, r, "In scope")
in_scope = [
    ["Single-file HTML application runnable from local disk on Windows.", "v0.1"],
    [f"{MARK_CHG}Import of all project and person data from ONE Excel workbook via a browser file picker or drag-and-drop.", "Q-09"],
    [f"{MARK_NEW}Editing imported data inside the application, with the edits carried into the export.", "REQ-IMP-07"],
    ["Export of the current working data back to .xlsx, so the workbook remains the archive of record.", "v0.1"],
    [f"{MARK_CHG}Monthly resource simulation in FTE per project and per person, default 24-month horizon, expandable to the latest project end date.", "Q-08, Q-11"],
    ["Three dashboard tabs: Overall, Source data (project), Source data (person).", "v0.1"],
    ["Tables plus graphs on the Overall tab.", "v0.1"],
    [f"{MARK_NEW}Over-allocation and under-allocation detection against the agreed FTE thresholds.", "Q-08"],
    ["Version control of plan, specification and application across the development lifecycle.", "v0.1"],
]
r = table(ws, r, ["In scope for v1.0", "Basis"], in_scope, [124, 12], wrap_cols=(1,), mark_col=1)

r = section(ws, r, "Out of scope")
out_scope = [
    ["Multi-user concurrent editing, or any server / database component.", "Requirement is a local single-file HTML tool.", "Confirmed Q-12"],
    ["Authentication, user accounts, permissions.", "No server; the workbook carries whatever access control the file share provides.", "Confirmed Q-12"],
    ["Automatic writing to the workbook on disk without user action.", "Browsers cannot do this from a file:// page - see 07_Architecture. Export is always a deliberate act.", "Confirmed Q-12"],
    ["Cost, budget or salary calculation.", "Not raised. The data model leaves room to add it.", "Confirmed Q-12"],
    ["Integration with an HR, CTMS or timesheet system.", "Not raised.", "Confirmed Q-12"],
    ["Resource optimisation / automatic assignment suggestions.", "v1.0 reports and simulates; it does not decide.", "Confirmed Q-12"],
    ["Working-day and holiday calendars.", "Q-02 confirmed calendar-day pro-rating. A working-day calendar is a later option.", "Confirmed Q-02"],
]
r = table(ws, r, ["Excluded from v1.0", "Reason", "Status"], out_scope, [66, 60, 16], wrap_cols=(1, 2))
r = note(ws, r, "Q-12 answer was 'Fine' - the v0.1 exclusions stand. Note that in-application editing has moved INTO scope "
                "via REQ-IMP-07; only automatic writing to disk without user action remains excluded.")

r = section(ws, r, "Users")
users = [
    ["Resource planner / manager", "Primary", "Loads the workbook, reviews monthly simulation, spots over- and under-allocation, tries timeline scenarios."],
    ["Project lead", "Secondary", "Checks the resource profile of their own project and who is assigned in which role."],
    ["Data maintainer", "Secondary", "Keeps the source workbook accurate; may be the same person as the planner."],
]
r = table(ws, r, ["User", "Type", "What they do with the application"], users, [28, 12, 96], wrap_cols=(3,))

# ---- 03 Requirements ------------------------------------------------------
ws, r = sheet(wb, "03_Requirements", "Requirement register",
              "The contract for Steps 2-5. Every specification section and every code module cites the REQ-IDs it satisfies.")

reqs = [
    ["REQ-OUT-01", "Output", "The application is a single HTML file that runs on a local Windows PC by double-click, with no install and no network access.", "Must", "Requester", "4"],
    ["REQ-OUT-02", "Output", "All program logic (HTML, CSS, JavaScript, libraries) is embedded in that one HTML file so it can be copied between PCs as a single artifact.", "Must", "Requester", "4"],
    [f"{MARK_CHG}REQ-OUT-03", "Output", "Source data lives in ONE Excel workbook held separately from the HTML file, and that workbook is the archive of record.", "Must", "Q-09", "4"],
    ["REQ-OUT-04", "Output", "The application reads the source workbook and uses it to drive every table and graph.", "Must", "Requester", "4"],
    ["REQ-OUT-05", "Output", "Plans and specifications are delivered as Excel workbooks.", "Must", "Requester", "1,2"],

    ["REQ-PRJ-01", "Project data", "Each project records a project type, restricted to 'Clinical Trial' or 'Others'.", "Must", "Requester", "2"],
    ["REQ-PRJ-02", "Project data", "Each project records a project category. Where type = 'Clinical Trial' the category is the product name; the field is optional for 'Others'.", "Must", "Requester", "2"],
    ["REQ-PRJ-03", "Project data", "Each project records a project name, unique within the source workbook.", "Must", "Requester", "2"],
    [f"{MARK_CHG}REQ-PRJ-04", "Project data", "Each project records its conditions: outsourcing type ('Full outsourcing' / 'Partial outsourcing' / 'Full In-house') and the number of project members.", "Must", "Q-14", "2"],
    [f"{MARK_CHG}REQ-PRJ-06", "Project data", "Each project carries a resource weight per period. For a clinical trial the weight is seeded from a standard keyed on clinical phase; for 'Others' it is entered by hand.", "Must", "Q-26, Q-28", "2"],
    ["REQ-PRJ-05", "Project data", "Each project records a timeline: start date, major milestone dates, and total period.", "Must", "Requester", "2"],
    ["REQ-PRJ-07", "Project data", "The project record accepts further project-related information without a schema change (free/extension columns).", "Should", "Requester", "2"],
    ["REQ-PRJ-08", "Project data", "Total period is derived from start and end dates rather than typed by hand, so it cannot contradict the timeline.", "Should", "Derived", "2"],
    [f"{MARK_CHG}REQ-PRJ-12", "Project data", "The set of periods a project carries depends on its type: 'Clinical Trial' uses Before-Start-up / Start-up / Conduct / Close-out (interim) / Close-out (final); 'Others' uses Planning / Develop / Close.", "Must", "Q-18, Q-23", "2"],
    [f"{MARK_CHG}REQ-PRJ-09", "Project data", "A 'Clinical Trial' project records its clinical phase (phase 1 / 2 / 3 / 4). The phase determines the project's period weights, so it drives the simulation rather than merely describing the project.", "Must", "Q-26", "2"],
    [f"{MARK_NEW}REQ-PRJ-10", "Project data", "A 'Clinical Trial' project records who performs each of EDC set-up, data-review-system set-up, RBQM set-up and DM conduct ('by CRO' / 'by SB').", "Must", "Reviewer v0.11", "2"],
    [f"{MARK_NEW}REQ-PRJ-11", "Project data", "A 'Clinical Trial' project records the EDC system, data review system and RBQM system in use, from data-driven value lists.", "Must", "Reviewer v0.11", "2"],

    ["REQ-PSN-01", "Person data", "Data is managed by person, by project assigned, and by project role assigned.", "Must", "Requester", "2"],
    ["REQ-PSN-02", "Person data", "Each assignment records the project(s) the person is assigned to.", "Must", "Requester", "2"],
    [f"{MARK_CHG}REQ-PSN-03", "Person data", "Each assignment records the role(s) the person holds on that project, drawn from the role list valid for that project's type.", "Must", "Q-03", "2"],
    ["REQ-PSN-04", "Person data", "Each assignment records the start date the person joins and the end date they leave that study.", "Must", "Requester", "2"],
    [f"{MARK_CHG}REQ-PSN-05", "Person data", "Each assignment carries a person weight saying how much that person works on that project, with optional period-specific overrides.", "Must", "Q-01", "2"],
    ["REQ-PSN-06", "Person data", "The person record accepts further project-related information without a schema change.", "Should", "Requester", "2"],
    ["REQ-PSN-07", "Person data", "One person may hold assignments on several projects simultaneously, and may hold more than one role on the same project.", "Must", "Derived", "2"],

    [f"{MARK_CHG}REQ-CAL-01", "Calculation", "Resource is simulated on a monthly grid, default horizon 24 months, expandable to the latest project end date.", "Must", "Q-11", "4"],
    [f"{MARK_CHG}REQ-CAL-02", "Calculation", "Monthly load for an assignment = project period weight x role factor x person weight x fraction of the month covered. There is no separate base allocation.", "Must", "Q-01", "2,4"],
    ["REQ-CAL-03", "Calculation", "Project monthly load is the sum of its assignments; person monthly load is the sum across all their projects.", "Must", "Requester", "4"],
    [f"{MARK_CHG}REQ-CAL-04", "Calculation", "A person-month whose total exceeds the over-allocation threshold (default 1.50 FTE) is flagged as over-allocated.", "Must", "Q-08", "4"],
    [f"{MARK_CHG}REQ-CAL-05", "Calculation", "A partial first or last month is pro-rated by calendar days worked, not counted as a whole month.", "Must", "Q-02", "4"],
    ["REQ-CAL-06", "Calculation", "All weights, factors and thresholds are data, held in the source workbook, never hardcoded in the program.", "Must", "Derived", "4"],
    [f"{MARK_NEW}REQ-CAL-07", "Calculation", "A person whose monthly total stays below the under-allocation threshold (default 0.80 FTE) for three or more consecutive months is flagged as under-allocated, with the run's start and length reported.", "Must", "Q-08", "4"],
    [f"{MARK_NEW}REQ-CAL-08", "Calculation", "Load is expressed in FTE, where 1.00 FTE = 160 hours per month (8 h/day x 5 days/week x 20 days/month). Hours are shown alongside FTE where useful.", "Must", "Q-08", "4"],
    [f"{MARK_CHG}REQ-CAL-09", "Calculation", "For a 'Clinical Trial' project, period boundaries are computed from milestone dates plus fixed month offsets (sheet 05), so a timeline change re-shapes the periods without re-typing them. For 'Others', periods are entered directly - those projects have no milestone mapping.", "Must", "Q-16, Q-22, Q-23, Q-25", "2,4"],
    [f"{MARK_NEW}REQ-CAL-10", "Calculation", "Every month of a project's timeline falls in exactly one period. A month left uncovered by the derivation is reported and carries weight 1.00 rather than being dropped from the simulation.", "Must", "Derived from Q-16", "2,4"],
    [f"{MARK_NEW}REQ-CAL-11", "Calculation", "A period name may occur more than once in one project: 'Conduct' runs as two separate stretches where an interim DB lock splits it. Each occurrence is its own row with its own dates and a sequence number.", "Must", "Q-23", "2,4"],
    [f"{MARK_NEW}REQ-CAL-12", "Calculation", "Where a timeline squeezes a derived period to zero or negative length, that period is omitted and the omission reported. Boundaries are applied in order so the periods always stay contiguous.", "Must", "Derived from Q-22, Q-23", "2,4"],

    ["REQ-DSH-01", "Dashboard", "Tab 'Overall' shows monthly resource simulation per project and per person as tables.", "Must", "Requester", "3,4"],
    ["REQ-DSH-02", "Dashboard", "Tab 'Overall' shows appropriate graphs of the same simulation.", "Must", "Requester", "3,4"],
    ["REQ-DSH-03", "Dashboard", "Tab 'Source data (project)' shows project information as a table.", "Must", "Requester", "3,4"],
    ["REQ-DSH-04", "Dashboard", "Tab 'Source data (person)' shows person information as a table.", "Must", "Requester", "3,4"],
    ["REQ-DSH-05", "Dashboard", "Tables can be filtered by date horizon, project type, project, person and role.", "Should", "Derived", "3,4"],
    ["REQ-DSH-06", "Dashboard", "Any table on screen can be exported to Excel.", "Should", "Derived", "4"],
    [f"{MARK_NEW}REQ-DSH-07", "Dashboard", "The horizon control offers 24 months by default and a one-click expansion to cover the latest project end date across all projects.", "Must", "Q-11", "3,4"],
    [f"{MARK_NEW}REQ-DSH-08", "Dashboard", "Over-allocated and under-allocated person-months are distinguishable at a glance, and both are counted in the summary tiles.", "Must", "Q-08", "3,4"],

    [f"{MARK_CHG}REQ-IMP-01", "Import/Export", "The user loads the source workbook through a file picker or drag-and-drop, chosen because a local HTML page cannot open a file from disk unaided.", "Must", "Decision D-01", "4"],
    ["REQ-IMP-02", "Import/Export", "Loading validates the workbook and reports every problem found - missing sheet, missing column, bad date, unknown project reference - without stopping at the first one.", "Must", "Derived", "4"],
    [f"{MARK_CHG}REQ-IMP-03", "Import/Export", "A blank source workbook template with correct sheet names, headers, value lists and one example row is delivered with the application.", "Must", "Derived", "4"],
    ["REQ-IMP-04", "Import/Export", "The user can export current data back to .xlsx, preserving the template layout so the export can be re-imported.", "Must", "Derived", "4"],
    ["REQ-IMP-05", "Import/Export", "The application records which file was loaded, and when, and shows it on screen.", "Should", "Derived", "4"],
    ["REQ-IMP-06", "Import/Export", "Loaded data may be cached in the browser so re-opening the page does not force a re-import; the cache never replaces the workbook as the record.", "Could", "Derived", "4"],
    [f"{MARK_NEW}REQ-IMP-07", "Import/Export", "After import, the application lets the user update the data on screen, and those updates are carried into the file produced on export.", "Must", "Reviewer v0.11", "4"],
    [f"{MARK_NEW}REQ-IMP-08", "Import/Export", "Unsaved edits are visible as such, and the user is warned before any action that would discard them (closing the page, loading another file).", "Must", "Derived from REQ-IMP-07", "4"],
    [f"{MARK_CHG}REQ-IMP-09", "Import/Export", "Every field is editable, including identifiers. An on-screen edit is re-validated against the same rules as an imported value, so editing cannot introduce data the import would have rejected.", "Must", "Q-20", "4"],
    [f"{MARK_NEW}REQ-IMP-10", "Import/Export", "Editing an identifier that other sheets reference cascades to every referencing row, after showing how many rows will change. Deleting a referenced row is refused, naming what still points at it.", "Must", "Q-20", "4"],

    ["REQ-VC-01", "Version control", "Development plan, programming specification and output files are version-controlled together and their versions are cross-referenced.", "Must", "Requester", "1-5"],
    ["REQ-VC-02", "Version control", "The application displays its own version, and the version of the source data schema it expects.", "Must", "Requester", "4"],
    ["REQ-VC-03", "Version control", "Loading a source file whose schema version is newer or older than the application expects produces a clear warning.", "Should", "Derived", "4"],
    ["REQ-VC-04", "Version control", "Every document re-issue adds a version-history row stating what changed and why.", "Must", "Requester", "1-5"],

    ["REQ-NFR-01", "Non-functional", "The application is built so later requirements can be added without restructuring: parsing, calculation and presentation are separated.", "Must", "Requester", "4"],
    ["REQ-NFR-02", "Non-functional", "Works in Microsoft Edge and Google Chrome on Windows 10/11, offline.", "Must", "Q-05", "4"],
    [f"{MARK_CHG}REQ-NFR-03", "Non-functional", "Handles the working data volume - 20 projects, 30 people - with headroom to 50 projects, 100 people, 500 assignments and a 60-month horizon, redrawing in under about 1 second.", "Should", "Q-06", "4"],
    ["REQ-NFR-04", "Non-functional", "No data leaves the PC: no network calls, no external CDN, no telemetry.", "Must", "Derived", "4"],
    ["REQ-NFR-05", "Non-functional", "Dates are handled unambiguously (ISO yyyy-mm-dd internally) regardless of Windows regional settings.", "Must", "Derived", "4"],
]

r_start = r
r = table(ws, r, ["REQ-ID", "Category", "Requirement", "Priority", "Source", "Step"],
          reqs, [15, 15, 92, 10, 18, 8], wrap_cols=(3,), mark_col=1)
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
r = table(ws, r, ["Priority", "Count"], counts, [15, 12])
r = note(ws, r, "47 requirements at v0.1, 58 at v0.2, 61 at v0.3, 63 at v0.4. v1.0 rewords 1 and adds none - "
                "the final round confirmed the design rather than changing it.")
r = note(ws, r, "'Source' = Requester (in the original request), a Q-number (answered at v0.11 review), "
                "'Reviewer v0.11' (added by the reviewer directly), Derived (engineering consequence), "
                "or a Decision ID from 07_Architecture.")
r = legend(ws, r)

# ---- 04 Data model --------------------------------------------------------
ws, r = sheet(wb, "04_Data_Model", "Data model - source Excel structure",
              "ONE workbook, PRAP_SourceData.xlsx, with the sheets below (changed at Q-09). "
              "This is the schema Step 2 will fix and the code will parse.")

r = section(ws, r, "Sheets in PRAP_SourceData.xlsx")
sheets_tbl = [
    ["Project", "One row per project.", "Master"],
    ["Milestone", "One row per project milestone.", "Child of Project"],
    [f"{MARK_NEW}ProjectPeriod", "The four standard periods per project, with their start/end and weight.", "Child of Project"],
    [f"{MARK_NEW}PeriodWeightStandard", "Default weight per project category x period. Seeds ProjectPeriod.", "Reference"],
    ["RoleFactor", "Role list and burden factor, per project type.", "Reference"],
    ["Person", "One row per person.", "Master"],
    ["Assignment", "One row per person + project + role.", "Link"],
    ["PersonPeriodWeight", "Optional time-varying override of the person weight.", "Child of Assignment"],
    [f"{MARK_NEW}Lists", "Value lists for every data-driven dropdown, so lists change without code.", "Reference"],
    ["Config", "Parameters: schema version, thresholds, horizon, FTE hours.", "Reference"],
]
r = table(ws, r, ["Sheet", "Purpose", "Kind"], sheets_tbl, [26, 84, 20], wrap_cols=(2,), mark_col=1)

r = section(ws, r, "Sheet: Project")
proj = [
    ["project_id", "Text", "Yes", "Unique key, e.g. PRJ-001. Referenced by every other sheet.", "REQ-PRJ-03"],
    ["project_name", "Text", "Yes", "Unique display name.", "REQ-PRJ-03"],
    ["project_type", "List", "Yes", "'Clinical Trial' or 'Others'.", "REQ-PRJ-01"],
    ["project_category", "Text", "Conditional", "Product name. Required when project_type = 'Clinical Trial'.", "REQ-PRJ-02"],
    [f"{MARK_NEW}clinical_phase", "List", "Conditional", "'Phase 1' / 'Phase 2' / 'Phase 3' / 'Phase 4'. Required when project_type = 'Clinical Trial'.", "REQ-PRJ-09"],
    [f"{MARK_CHG}outsourcing_type", "List", "Yes", "'Full outsourcing' / 'Partial outsourcing' / 'Full In-house'. Three values, fixed at Q-14.", "REQ-PRJ-04"],
    [f"{MARK_NEW}EDC_setup", "List", "Conditional", "Who sets up the EDC system. 'by CRO' / 'by SB'. Required when project_type = 'Clinical Trial'.", "REQ-PRJ-10"],
    [f"{MARK_NEW}DataReviewSystem_setup", "List", "Conditional", "Who sets up the data review system. 'by CRO' / 'by SB'.", "REQ-PRJ-10"],
    [f"{MARK_NEW}RBQM_setup", "List", "Conditional", "Who sets up the RBQM system. 'by CRO' / 'by SB'.", "REQ-PRJ-10"],
    [f"{MARK_NEW}DM_conduct", "List", "Conditional", "Who reviews the clinical trial data. 'by CRO' / 'by SB'.", "REQ-PRJ-10"],
    [f"{MARK_NEW}EDC_system", "List", "Conditional", "EDC system name, e.g. 'Veeva EDC' / 'Rave' / 'eSOURCE'. Data-driven list.", "REQ-PRJ-11"],
    [f"{MARK_NEW}DataReviewSystem", "List", "Conditional", "e.g. 'Veeva DQS' / 'Medidata CDS' / 'No system (manual)'. Data-driven list.", "REQ-PRJ-11"],
    [f"{MARK_NEW}RBQM_system", "List", "Conditional", "e.g. 'CluePoints' / 'Medidata CDS' / 'No system (manual)'. Data-driven list.", "REQ-PRJ-11"],
    ["planned_member_count", "Integer", "No", "Planned number of project members; compared against actual assignments.", "REQ-PRJ-04"],
    ["start_date", "Date", "Yes", "Project start.", "REQ-PRJ-05"],
    ["end_date", "Date", "Yes", "Planned project end.", "REQ-PRJ-05"],
    ["total_period_months", "Derived", "-", "Calculated from start_date and end_date; not entered by hand.", "REQ-PRJ-08"],
    ["status", "List", "No", "Planned / Active / On hold / Completed. Drives default dashboard filtering.", "REQ-PRJ-07"],
    ["note_1 .. note_5", "Text", "No", "Free extension columns.", "REQ-PRJ-07"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          proj, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)
r = note(ws, r, "system_prepared_by is dropped at v0.3 (Q-19): the four *_setup columns replace it with more detail.")

r = section(ws, r, "Sheet: Milestone")
mile = [
    ["project_id", "Text", "Yes", "Foreign key to Project.", "REQ-PRJ-05"],
    [f"{MARK_NEW}project_name", "Text", "No", "Display convenience added at v0.11. Not authoritative: checked against Project on import and refreshed from it, so a mismatch cannot corrupt the link.", "REQ-PRJ-05"],
    [f"{MARK_CHG}milestone_name", "List", "Yes", "Standard list (8), settled at Q-15 and Q-24: 'Protocol (v1)', 'CTA submission', 'First SIV', 'LPI', 'interim DB lock cut-off', 'interim DB lock', 'final DB lock cut-off', 'final DB lock'. FPI is no longer standard. Held in Lists, not fixed in code, so a project may add its own.", "REQ-PRJ-05"],
    ["milestone_date", "Date", "Yes", "Planned date.", "REQ-PRJ-05"],
    ["milestone_seq", "Integer", "No", "Display order on the timeline.", "REQ-PRJ-05"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          mile, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)
r = note(ws, r, "Of the eight, only CTA submission and the DB locks set period boundaries. 'Protocol (v1)', 'First SIV', 'LPI' and the two cut-off dates are markers shown on the timeline.")

r = section(ws, r, "Sheet: ProjectPeriod  [was ProjectPeriodWeight]")
pp = [
    ["project_id", "Text", "Yes", "Foreign key to Project.", "REQ-PRJ-06"],
    [f"{MARK_CHG}period_name", "List", "Yes", "From the period set for the project's TYPE - see the two sets below. A period name from the wrong set is rejected. NOT unique within a project: 'Conduct' occurs twice where an interim DB lock splits it.", "REQ-PRJ-12, REQ-CAL-11"],
    [f"{MARK_NEW}period_seq", "Integer", "Yes", "Orders the periods along the timeline and tells the two 'Conduct' stretches apart. Unique within a project.", "REQ-CAL-11"],
    [f"{MARK_CHG}period_start", "Date", "Yes", "Inclusive. For Clinical Trial, computed from milestones (sheet 05) and then editable. For Others, entered directly.", "REQ-CAL-09"],
    [f"{MARK_CHG}period_end", "Date", "Yes", "Inclusive. Periods for one project must not overlap and must leave no gap (REQ-CAL-10).", "REQ-CAL-09"],
    [f"{MARK_CHG}weight", "Decimal", "Yes", "Effort multiplier for this period. For a clinical trial, seeded from PeriodWeightStandard by clinical phase and then editable. For 'Others', entered by hand (Q-28). Values are data (Q-17), not fixed in this plan.", "REQ-PRJ-06"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          pp, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)

r = note(ws, r, "Period sets are type-specific (Q-18). The derivation itself is on sheet 05.")
sets = [
    ["Clinical Trial", "Before-Start-up, Start-up, Conduct, Close-out (interim), Close-out (final)", "Computed from milestone dates plus month offsets. 'Conduct' may appear twice; 'Close-out (interim)' only where an interim DB lock exists."],
    ["Others", "Planning, Develop, Close", "Entered directly - dates confirmed manual at Q-25, weights at Q-28. 'Others' projects are hand-entered throughout."],
]
r = table(ws, r, ["project_type", "Period set", "How boundaries are set"], sets, [18, 50, 66], wrap_cols=(2, 3))

r = section(ws, r, "Sheet: PeriodWeightStandard")
pws = [
    [f"{MARK_CHG}project_type", "List", "Yes", "Always 'Clinical Trial' at v1.0. 'Others' projects take manual weights (Q-28), so they need no standard row. The column stays so a standard set can be added later without a schema change.", "Q-28"],
    [f"{MARK_CHG}clinical_phase", "List", "Yes", "The phase the standard applies to. This is the key that selects a clinical trial's weights.", "Q-26"],
    ["period_name", "List", "Yes", "A period from that type's set.", "Q-04, Q-18"],
    [f"{MARK_CHG}weight", "Decimal", "Yes", "Default multiplier. You fill these in the source workbook (Q-17); the plan fixes only where they live.", "Q-01"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "Basis"],
          pws, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)
r = note(ws, r, "Re-keyed at Q-26: a clinical trial's weights come from its CLINICAL PHASE, not its product category. "
                "So a phase 1 trial and a phase 3 trial of the same product carry different period weights, which is "
                "the intended behaviour. Q-28 then confirmed that 'Others' projects are not distinguished at all and "
                "take their weights by hand - which makes this sheet a clinical-trial table, and leaves 'Others' "
                "projects entirely hand-entered: dates and weights alike.")

r = section(ws, r, "Sheet: RoleFactor")
rf = [
    [f"{MARK_NEW}project_type", "List", "Yes", "'Clinical Trial' or 'Others'. Roles differ by type, so the same role name cannot leak across types.", "Q-03"],
    [f"{MARK_CHG}role_name", "Text", "Yes", "Clinical Trial: 'Project oversight', 'Lead data manager', 'Clinical Data Associator', 'Clinical Database Programmer', 'Data Analyst'. Others: 'Project lead', 'Main staff', 'Other staff'.", "Q-03"],
    [f"{MARK_CHG}role_factor", "Decimal", "Yes", "Relative burden of the role, the same for everyone holding it. Values still to be supplied - see Q-17.", "Q-01"],
    ["role_note", "Text", "No", "Basis for the factor.", "REQ-CAL-06"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "Basis"],
          rf, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)

r = section(ws, r, "Sheet: Person")
pers = [
    ["person_id", "Text", "Yes", "Unique key, e.g. PSN-001.", "REQ-PSN-01"],
    ["person_name", "Text", "Yes", "Display name.", "REQ-PSN-01"],
    ["department", "Text", "No", "Grouping for the dashboard.", "REQ-PSN-06"],
    ["primary_role", "Text", "No", "Usual role; an assignment can override it.", "REQ-PSN-03"],
    [f"{MARK_CHG}capacity_fte", "Decimal", "No", "Available capacity in FTE, default 1.00 (= 160 h/month). Lower it for a part-timer.", "REQ-CAL-08"],
    ["employment_start / employment_end", "Date", "No", "Bounds availability; blank end = open.", "REQ-PSN-04"],
    ["note_1 .. note_5", "Text", "No", "Free extension columns.", "REQ-PSN-06"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          pers, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)

r = section(ws, r, "Sheet: Assignment")
asg = [
    ["assignment_id", "Text", "Yes", "Unique key. One row per person + project + role.", "REQ-PSN-07"],
    ["person_id", "Text", "Yes", "Foreign key to Person.", "REQ-PSN-01"],
    [f"{MARK_NEW}person_name", "Text", "No", "Display convenience added at v0.11. Not authoritative: checked against Person on import and refreshed from it.", "REQ-PSN-01"],
    ["project_id", "Text", "Yes", "Foreign key to Project.", "REQ-PSN-02"],
    [f"{MARK_CHG}role_name", "Text", "Yes", "Foreign key to RoleFactor, matched on (project's type, role_name). Several rows = several roles on one project.", "REQ-PSN-03"],
    ["assign_start_date", "Date", "Yes", "Date the person joins the study.", "REQ-PSN-04"],
    ["assign_end_date", "Date", "Yes", "Date the person leaves the study. Blank = runs to project end.", "REQ-PSN-04"],
    [f"{MARK_CHG}person_weight", "Decimal", "Yes", "RENAMED from base_allocation. How much this person works on this project, e.g. 0.40. Q-01 folded the two former fields into this one.", "REQ-CAL-02"],
    ["note_1 .. note_3", "Text", "No", "Free extension columns.", "REQ-PSN-06"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          asg, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)

r = section(ws, r, "Sheet: PersonPeriodWeight")
ppw = [
    ["assignment_id", "Text", "Yes", "Foreign key to Assignment.", "REQ-PSN-05"],
    ["period_start", "Date", "Yes", "Inclusive.", "REQ-PSN-05"],
    ["period_end", "Date", "Yes", "Inclusive. Periods within one assignment must not overlap.", "REQ-PSN-05"],
    [f"{MARK_CHG}weight_override", "Decimal", "Yes", "REPLACES person_weight for months inside this window - it no longer multiplies it. Where no row covers a month, person_weight applies unchanged.", "REQ-PSN-05"],
    ["reason", "Text", "No", "Why the weight differs, e.g. 'part-time', 'covering start-up peak'.", "REQ-PSN-05"],
]
r = table(ws, r, ["Column", "Type", "Required", "Definition / rule", "REQ-ID"],
          ppw, [26, 11, 12, 88, 14], wrap_cols=(4,), mark_col=1)
r = note(ws, r, "Changed at Q-01. The answer named exactly three factors, so a fourth multiplier would have been an "
                "invention. This sheet now overrides rather than scales - the same effect, one fewer factor, and no "
                "hidden compounding. It is optional: leave it empty and every assignment simply uses person_weight.")

r = section(ws, r, "Sheet: Config")
cfg = [
    ["schema_version", "Version of this workbook structure; checked on import.", "1", "REQ-VC-02"],
    [f"{MARK_NEW}fte_hours_per_month", "Hours equal to 1.00 FTE.", "160", "REQ-CAL-08"],
    [f"{MARK_NEW}over_allocation_fte", "Person-month total above this is over-allocated.", "1.50", "REQ-CAL-04"],
    [f"{MARK_NEW}under_allocation_fte", "Person-month total below this counts toward an under-allocated run.", "0.80", "REQ-CAL-07"],
    [f"{MARK_NEW}under_allocation_min_months", "Consecutive months below the threshold before flagging.", "3", "REQ-CAL-07"],
    [f"{MARK_CHG}default_horizon_months", "Months shown on opening.", "24", "REQ-CAL-01"],
    [f"{MARK_CHG}capacity_unit", "Display unit: 'FTE' or 'percent'.", "FTE", "REQ-CAL-08"],
]
r = table(ws, r, ["parameter", "Meaning", "Default value", "REQ-ID"],
          cfg, [30, 74, 16, 14], wrap_cols=(2,), mark_col=1)

r = section(ws, r, "Sheet: Lists   [new]")
r = lines(ws, r, [
    "Two columns - list_name, value - holding every data-driven dropdown: outsourcing_type, clinical_phase,",
    "milestone_name, period_name, EDC_system, DataReviewSystem, RBQM_system, setup_party, project_status.",
    "Adding a permitted value is a data edit, never a code change (REQ-CAL-06).",
])
r += 1

r = section(ws, r, "Referential rules checked on import")
rules = [
    ["V-01", "Every Assignment.project_id exists in Project.", "Error - row rejected, reported with its row number."],
    ["V-02", "Every Assignment.person_id exists in Person.", "Error - row rejected."],
    [f"{MARK_CHG}V-03", "Every Assignment.role_name exists in RoleFactor FOR THAT PROJECT'S TYPE.", "Error - row rejected. Was a warning in v0.1; roles are now type-specific, so a mismatch is a real error."],
    ["V-04", "project_category is present when project_type = 'Clinical Trial'.", "Warning - shown as blank in the dashboard."],
    ["V-05", "end_date is on or after start_date, for projects, assignments and all weight periods.", "Error - row rejected."],
    ["V-06", "Periods within one project, and within one assignment, do not overlap.", "Error - overlapping pair reported."],
    ["V-07", "Assignment dates fall inside the project's own start and end dates.", "Warning - kept, but listed for review."],
    ["V-08", "project_id, person_id and assignment_id are unique in their sheet.", "Error - duplicate rejected."],
    ["V-09", "schema_version in Config matches the version the application expects.", "Warning - proceeds, banner shown."],
    [f"{MARK_NEW}V-10", "Clinical-trial projects carry clinical_phase and the four *_setup values.", "Warning - the project still simulates; the gap is listed."],
    [f"{MARK_NEW}V-11", "Every list-typed value appears in the Lists sheet for its list.", "Warning - value kept, reported as unrecognised."],
    [f"{MARK_CHG}V-12", "A project's periods leave no gap and no overlap across its timeline. The full set need not be present - a period may be legitimately omitted (REQ-CAL-12).", "Warning - months with no period use weight 1.00 and are listed (REQ-CAL-10)."],
    [f"{MARK_NEW}V-13", "Denormalised project_name / person_name match their master row.", "Warning - the master value wins and the copy is refreshed."],
    [f"{MARK_NEW}V-14", "A milestone date falls inside its project's start..end window, and the standard milestones appear in chronological order.", "Error for period-defining milestones - the derivation cannot run. Warning for markers."],
    [f"{MARK_NEW}V-15", "A period_name belongs to the period set of its project's type.", "Error - a 'Planning' period on a clinical trial is a category mistake, not a typo."],
    [f"{MARK_NEW}V-16", "A clinical trial carries the milestones the derivation needs: CTA submission, and at least one DB lock.", "Error - without them no period boundary can be computed."],
    [f"{MARK_NEW}V-18", "period_seq is unique within a project and orders the periods by date.", "Error - the two Conduct stretches cannot be told apart otherwise."],
    [f"{MARK_CHG}V-19", "A clinical trial carries a clinical_phase, and PeriodWeightStandard has rows for that phase. Not applied to 'Others' projects, whose weights are entered directly.", "Error - since Q-26 the phase selects the weights, so a missing phase leaves the project unweighted."],
    [f"{MARK_NEW}V-17", "On editing an identifier, every referencing row is updated; on deleting a row, nothing may still reference it.", "Cascade after confirmation / deletion refused (REQ-IMP-10)."],
]
r = table(ws, r, ["ID", "Rule", "On failure"], rules, [9, 84, 60], wrap_cols=(2, 3), mark_col=1)
r = note(ws, r, "Import never stops at the first problem: it collects every finding and presents one report (REQ-IMP-02). "
                "Under REQ-IMP-09 the same rules run again on any value edited on screen.")
r = legend(ws, r)

# ---- 05 Resource logic ----------------------------------------------------
ws, r = sheet(wb, "05_Resource_Logic", "Resource calculation logic",
              "Rewritten at v0.2 from the Q-01, Q-02 and Q-08 answers. Step 2 will fix this as pseudocode "
              "plus the worked example as an acceptance test.")

r = section(ws, r, "Monthly load for one assignment, in one month")
r = lines(ws, r, [
    "    load(assignment, month) = project_period_weight(project, month)",
    "                            x role_factor(project_type, role)",
    "                            x person_weight(assignment, month)",
    "                            x coverage(assignment, month)",
    "",
    "The result is FTE, where 1.00 FTE = 160 hours per month (8 h/day x 5 days/week x 20 days/month).",
    "",
    "project_period_weight  is set by the project's category for the milestone period the month falls in.",
    "                       It is identical for everyone assigned to that project in that period.",
    "role_factor            is the standard burden of the role, identical for everyone holding it.",
    "                       Roles are drawn from the list valid for the project's type.",
    "person_weight          is how much this person works on this project, given per assignment;",
    "                       a PersonPeriodWeight row replaces it for the months it covers.",
    "coverage               = calendar days worked in the month / calendar days in the month.",
    "                       1.00 for a full month, a fraction in the joining and leaving months.",
], mono=True)
r += 1
r = note(ws, r, "Changed from v0.1: base_allocation is gone. Q-01 named three factors, and base_allocation was a fourth "
                "that would have silently scaled all of them. person_weight now carries that meaning alone.")
r += 1

r = section(ws, r, "Aggregation")
agg = [
    ["Per project, per month", "Sum of load over every assignment on that project.", "Overall tab, project table + stacked graph", "REQ-CAL-03"],
    ["Per person, per month", "Sum of load over every assignment that person holds, across all projects.", "Overall tab, person table + graph", "REQ-CAL-03"],
    ["Per person, per project, per month", "The individual load value.", "Drill-down when a person row is expanded", "REQ-CAL-03"],
    [f"{MARK_CHG}Over-allocation flag", "Person-month total > over_allocation_fte (1.50).", "Red cell + count in summary tiles", "REQ-CAL-04"],
    [f"{MARK_NEW}Under-allocation run", "Person-month total < under_allocation_fte (0.80) for >= under_allocation_min_months (3) consecutive months. Reported as a run with its start month and length.", "Amber cells across the run + count in summary tiles", "REQ-CAL-07"],
    [f"{MARK_NEW}Hours view", "load x fte_hours_per_month.", "Alternative display unit", "REQ-CAL-08"],
    ["Head-count per project, per month", "Count of assignments with load > 0 that month.", "Compared against planned_member_count", "REQ-PRJ-04"],
]
r = table(ws, r, ["Output", "How it is computed", "Where it appears", "REQ-ID"],
          agg, [30, 66, 44, 14], wrap_cols=(2, 3), mark_col=1)

r = note(ws, r, "Under-allocation needs a rolling window, not a per-month test: a single quiet month is normal, three "
                "in a row is a signal. A run is reported once, at its start, rather than as three separate flags.")
r += 1

r = section(ws, r, "Period derivation for a 'Clinical Trial' project   [settled at Q-21, Q-22, Q-23]")
r = lines(ws, r, [
    "Boundaries come from milestone dates plus month offsets, so moving a milestone re-shapes the periods.",
    "Only 'CTA submission' and the DB locks are boundaries; the other five milestones are markers.",
])
r += 1
deriv = [
    ["1", "Before-Start-up", "project start_date", "day before Start-up begins", "Q-21"],
    ["2", "Start-up", "one month before 'CTA submission'", "start + 4 months - 1 day", "Q-16"],
    ["3", "Conduct", "day after Start-up ends", "day before the next Close-out begins", "Q-22"],
    [f"{MARK_NEW}4", "Close-out (interim)", "3 months before 'interim DB lock'", "'interim DB lock'", "Q-22, Q-23"],
    [f"{MARK_NEW}5", "Conduct   (second stretch)", "day after 'interim DB lock'", "day before Close-out (final) begins", "Q-23"],
    [f"{MARK_CHG}6", "Close-out (final)", "3 months before 'final DB lock'", "'final DB lock' (or project end_date if later)", "Q-22, Q-23"],
]
r = table(ws, r, ["Seq", "Period", "Starts", "Ends", "Basis"],
          deriv, [6, 24, 34, 44, 12], wrap_cols=(3, 4), mark_col=1)
r = note(ws, r, "Rows 4 and 5 exist only where the project has an interim DB lock. Without one, Conduct runs as a "
                "single stretch straight into Close-out (final).")
r += 1

r = section(ws, r, "Degenerate timelines   [REQ-CAL-12]")
r = lines(ws, r, [
    "Real timelines do not always leave room for every period. Boundaries are applied in sequence order and a",
    "later one wins, so the periods stay contiguous; any period squeezed to zero or negative length is omitted",
    "and reported rather than written with a nonsensical range.",
])
r += 1
degen = [
    ["CTA submission is within a month of the project start", "Before-Start-up would be empty or negative.", "Before-Start-up omitted; Start-up begins at the project start date."],
    ["Interim and final DB lock less than 3 months apart", "The second Conduct stretch would be negative, and Close-out (final) would start before the interim lock.", "Second Conduct omitted; Close-out (final) begins the day after the interim DB lock."],
    ["No interim DB lock recorded", "Rows 4 and 5 have no anchor.", "Both omitted; one Conduct stretch runs into Close-out (final)."],
    ["Trial too short for a Conduct phase", "Start-up's fixed 4 months would overrun the Close-out start.", "Conduct omitted; Start-up is clipped where Close-out begins."],
    ["No CTA submission, or no DB lock at all", "Nothing to derive from.", "Error, not a silent default - V-16. The project's periods must then be entered by hand."],
]
r = table(ws, r, ["Timeline", "What would go wrong", "What happens instead"],
          degen, [40, 52, 54], wrap_cols=(1, 2, 3))
r = note(ws, r, "The five cases above were each run through the derivation. All produce a contiguous set of periods "
                "with no gap and no overlap. The check is worth repeating as an automated test at Step 4.")
r += 1

r = section(ws, r, "Worked example - the acceptance test for the calculation engine")
ex = [
    ["Assignment", "PSN-001 on PRJ-001 (Clinical Trial), role = Lead data manager", ""],
    ["person_weight", "0.40", "How much this person works on this project"],
    ["Assignment window", "2026-03-10 to 2026-12-31", "Joins part-way through March"],
    ["Project periods", "Start-up 2026-01-01..2026-06-30 weight 1.50; Conduct from 2026-07-01 weight 1.00", "Seeded from the project's CLINICAL PHASE (Q-26)"],
    ["role_factor", "1.20 for Lead data manager", "Illustrative. Real values are entered in the source workbook (Q-17), not fixed here"],
    ["Coverage, March 2026", "22 / 31 = 0.7097", "10 Mar to 31 Mar inclusive = 22 days"],
    ["Load, March 2026", "1.50 x 1.20 x 0.40 x 0.7097 = 0.511 FTE", "81.8 hours"],
    ["Load, April 2026", "1.50 x 1.20 x 0.40 x 1.0000 = 0.720 FTE", "115.2 hours. Full month inside Start-up"],
    ["Load, July 2026", "1.00 x 1.20 x 0.40 x 1.0000 = 0.480 FTE", "76.8 hours. Conduct weight applies"],
    ["Over-allocated?", "No - 0.720 is below the 1.50 threshold", "This person would need other assignments to breach it"],
    ["Under-allocated?", "Only if their total across ALL projects stays below 0.80 for 3 months running", "Judged on the person total, never on one assignment"],
]
r = table(ws, r, ["Element", "Value", "Note"], ex, [26, 66, 50], wrap_cols=(2, 3))
r = note(ws, r, "Please confirm these numbers at Step 2. The role_factor of 1.20 is a placeholder: the arithmetic is "
                "the thing being agreed, not that particular value.")
r += 1

r = section(ws, r, "Design decisions inside the calculation")
dec = [
    ["C-01", "Weights multiply rather than add.", "Confirmed at Q-01: project weight x role factor x person weight.", "CONFIRMED"],
    ["C-02", "Partial months are pro-rated by calendar days.", "Confirmed at Q-02: work is expected in proportion to calendar days from the joined date to the end date.", "CONFIRMED"],
    [f"{MARK_CHG}C-03", "A missing PersonPeriodWeight row means person_weight applies unchanged.", "Follows from the override semantics. No row is the normal case, not an exception.", "CONFIRMED"],
    [f"{MARK_CHG}C-04", "Capacity is FTE. 1.00 FTE = 160 h/month.", "Confirmed at Q-08. Note the flag is NOT at 1.00 - over-allocation begins above 1.50.", "CONFIRMED"],
    [f"{MARK_CHG}C-05", "The unit shown on screen is FTE, with hours available.", "Q-08 was expressed in FTE and hours, so FTE is now the default rather than percent.", "CONFIRMED"],
    [f"{MARK_NEW}C-06", "Over- and under-allocation are judged on the person's total across all projects.", "The question 'is this person over-committed' is only meaningful across their whole workload.", "Confirm"],
    [f"{MARK_NEW}C-07", "Period weights are seeded from the category standard, then editable per project.", "Q-01 ties weight to category; real projects still deviate. Seeding keeps them consistent without freezing them.", "Confirm"],
    [f"{MARK_NEW}C-08", "A month is attributed to the period containing its first day.", "Avoids splitting a month across two weights. Simpler to explain and to check by hand.", "Confirm"],
    [f"{MARK_NEW}C-09", "Editing an identifier cascades to every row referencing it; deleting a referenced row is refused.", "Q-20 asked for every field to be editable with rules preventing inconsistency. Cascading is what makes an editable ID safe - blocking the edit instead would make the field read-only in all but name.", "Confirm"],
    [f"{MARK_NEW}C-10", "Period boundaries are recomputed whenever a milestone date changes, unless the period dates were edited by hand.", "Keeps derived dates true to the timeline - the frequent-change problem this tool exists for - without silently discarding a deliberate manual override.", "Confirm"],
    [f"{MARK_NEW}C-11", "Derived boundaries are applied in sequence order, a later one overriding an earlier; a period squeezed to nothing is omitted.", "The only rule that keeps periods contiguous on every timeline, including the awkward ones. Verified against five cases on this sheet.", "Confirm"],
]
r = table(ws, r, ["ID", "Decision", "Rationale", "Status"], dec, [9, 46, 76, 14], wrap_cols=(2, 3), mark_col=1)
r = legend(ws, r)

# ---- 06 Dashboard ---------------------------------------------------------
ws, r = sheet(wb, "06_Dashboard_Design", "Dashboard design",
              "Three tabs as specified. Detailed layout is fixed at the Step 3 UI review.")

r = section(ws, r, "Tab 1 - Overall")
overall = [
    [f"{MARK_CHG}Control bar", "Horizon (default 24 months, one click to expand to the latest project end date), project type, project, person, role, department. Plus 'Load workbook', 'Export', unit toggle FTE/hours, and the loaded-file name and time.", "REQ-DSH-05, REQ-DSH-07"],
    ["Table A - resource by project", "Rows = project, columns = months, cells = monthly FTE. Row and column totals. Expanding a project reveals its assigned people.", "REQ-DSH-01"],
    [f"{MARK_CHG}Table B - resource by person", "Rows = person, columns = months, cells = FTE summed across projects. Over-allocated cells red, under-allocated runs amber. Expanding a person reveals their projects.", "REQ-DSH-01, REQ-DSH-08"],
    ["Graph 1 - stacked area or bar, by project", "Total monthly demand, one band per project. Shows how demand builds and where the peaks land.", "REQ-DSH-02"],
    [f"{MARK_CHG}Graph 2 - grouped bar, by person", "Monthly FTE per person with reference lines at 1.50 and 0.80, so both thresholds are visible.", "REQ-DSH-02, REQ-DSH-08"],
    ["Graph 3 - project timeline (Gantt-style)", "One bar per project across the horizon, with milestone markers and period-weight shading.", "REQ-DSH-02, REQ-PRJ-05"],
    [f"{MARK_CHG}Summary tiles", "Active projects, people assigned, total FTE in the horizon, over-allocated person-months, under-allocated runs.", "REQ-DSH-08"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], overall, [34, 96, 22], wrap_cols=(2,), mark_col=1)

r = section(ws, r, "Tab 2 - Source data (project)")
p2 = [
    [f"{MARK_CHG}Project table", "Every Project column from sheet 04, sortable and filterable, with derived total period. Editable under REQ-IMP-07.", "REQ-DSH-03"],
    ["Milestone sub-table", "Milestones of the selected project, in sequence.", "REQ-PRJ-05"],
    [f"{MARK_CHG}Period sub-table", "The selected project's four periods, their derived dates and their weights.", "REQ-PRJ-06"],
    ["Export", "Export the visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], p2, [34, 96, 22], wrap_cols=(2,), mark_col=1)

r = section(ws, r, "Tab 3 - Source data (person)")
p3 = [
    [f"{MARK_CHG}Person table", "Every Person column from sheet 04, sortable and filterable. Editable under REQ-IMP-07.", "REQ-DSH-04"],
    [f"{MARK_CHG}Assignment sub-table", "The selected person's assignments: project, role, start, end, person weight.", "REQ-PSN-02, REQ-PSN-03"],
    ["Person period weight sub-table", "Override periods for the selected assignment.", "REQ-PSN-05"],
    ["Export", "Export the visible table to .xlsx.", "REQ-DSH-06"],
]
r = table(ws, r, ["Component", "Content", "REQ-ID"], p3, [34, 96, 22], wrap_cols=(2,), mark_col=1)

r = section(ws, r, "Editing rules   [new at v0.2, from REQ-IMP-07]")
edit = [
    [f"{MARK_CHG}The v0.1 rule 'nothing on screen is editable' is withdrawn. Imported data can be edited in the application.", "REQ-IMP-07"],
    ["An edited cell is marked as changed, and a running count of unsaved edits is always visible.", "REQ-IMP-08"],
    ["Closing the page or loading another workbook while edits are unsaved raises a warning first.", "REQ-IMP-08"],
    [f"{MARK_CHG}Every field is editable, identifiers included (Q-20). Consistency is protected by rule, not by locking fields.", "REQ-IMP-09"],
    ["An edited value is validated exactly as an imported one would be; a rejected edit is refused at the point of entry, not at export.", "REQ-IMP-09"],
    [f"{MARK_NEW}Changing an identifier updates every row that references it, after showing how many will change. Deleting a row that is still referenced is refused, naming what points at it.", "REQ-IMP-10, V-17"],
    [f"{MARK_NEW}Editing a milestone date re-computes that project's derived periods, unless its period dates were set by hand.", "C-10"],
    ["Export writes the edited data in the template layout, so the exported file can be re-imported unchanged.", "REQ-IMP-04, REQ-IMP-07"],
    ["The application never writes to the workbook on disk by itself - export is always a deliberate act.", "Out of scope, sheet 02"],
]
r = table(ws, r, ["Rule", "REQ-ID"], edit, [124, 22], wrap_cols=(1,), mark_col=1)

r = section(ws, r, "Cross-cutting UI rules")
ui = [
    ["A validation banner appears whenever the last import produced findings, and opens the full report on click."],
    ["Empty state: with nothing loaded, every tab shows the same clear 'Load your source workbook' panel and a link to download the blank template."],
    ["The application version and expected schema version are shown in the footer at all times (REQ-VC-02)."],
]
r = table(ws, r, ["Rule"], ui, [146], wrap_cols=(1,))
r = legend(ws, r)

# ---- 07 Architecture ------------------------------------------------------
ws, r = sheet(wb, "07_Architecture", "Architecture and technical approach")

r = section(ws, r, "Decision D-01 - how the HTML file reads the Excel data  [CONFIRMED: option (a)]")
r = lines(ws, r, [
    "A page opened from local disk (file://) cannot read an .xlsx from a fixed path on its own - the browser's",
    "security model blocks it. Q-05 confirmed local .html files do open on the work PC, so the approach is viable.",
])
r += 1
opts = [
    ["(a)", "User selects the workbook through a file picker or drag-and-drop; an embedded SheetJS-style parser reads it in memory.",
     "True .xlsx support; no install; no server; user controls which file is loaded.",
     "The file must be selected each session (mitigated by optional caching, REQ-IMP-06).", "CONFIRMED - adopted"],
    ["(b)", "Data kept as .csv next to the HTML, still opened through a picker.",
     "Simplest possible parsing.", "Loses formatting, multiple sheets and validation - and Q-09 asks for one multi-sheet workbook, which .csv cannot express.", "Rejected"],
    ["(c)", "Excel is only an export target; browser storage is the working record.",
     "No load step at all.", "Contradicts the workbook being the archive of record; clearing browser data would lose everything.", "Rejected"],
]
r = table(ws, r, ["Option", "Description", "Advantages", "Disadvantages", "Outcome"],
          opts, [9, 50, 40, 48, 18], wrap_cols=(2, 3, 4))
r = note(ws, r, "Q-09 strengthens this decision: one workbook with ten sheets is exactly what .xlsx does well and .csv cannot do at all.")

r = section(ws, r, "Technology")
tech = [
    ["Container", "One .html file, opened by double-click.", "REQ-OUT-01"],
    ["Excel parsing/writing", "SheetJS (xlsx) community build, embedded inline - no CDN, so it works offline.", "REQ-OUT-02, REQ-NFR-04"],
    ["Charts", "Inline SVG drawn by the application's own code, or a small embedded chart library. No external requests either way.", "REQ-DSH-02, REQ-NFR-04"],
    ["Framework", "None. Plain modern JavaScript.", "REQ-OUT-02"],
    ["Styling", "Embedded CSS. Readable on a laptop screen and when printed.", "REQ-OUT-01"],
    ["Persistence", "Optional browser cache of the last load, marked as a convenience, never as the record.", "REQ-IMP-06"],
]
r = table(ws, r, ["Concern", "Choice and reason", "REQ-ID"], tech, [24, 108, 20], wrap_cols=(2,))

r = section(ws, r, "Internal structure - built for later change (REQ-NFR-01)")
layers = [
    ["1. IO layer", "Reads the chosen workbook into raw rows; writes .xlsx on export.", "Swapping the file-access method touches this layer only."],
    ["2. Validation layer", "Applies rules V-01..V-19, produces one findings report.", "New rules are added here without touching parsing or maths."],
    ["3. Model layer", "Typed in-memory objects: Project, Milestone, ProjectPeriod, RoleFactor, Person, Assignment, PersonPeriodWeight, Config, Lists.", "New fields are added here and flow outward."],
    [f"{MARK_NEW}4. Edit buffer", "Holds on-screen changes, tracks which rows are dirty, re-runs validation per edit, and feeds export.", "Added for REQ-IMP-07. Keeping edits out of the model layer means the calculation never has to care whether a value came from the file or the screen."],
    [f"{MARK_CHG}5. Calculation layer", "The monthly engine above. Pure functions - no DOM, no file access.", "Directly unit-testable, and the piece most likely to be refined once you see real output."],
    [f"{MARK_CHG}6. Presentation layer", "Tabs, tables, graphs, filters, editing controls, export buttons.", "A new tab or graph is added here alone."],
]
r = table(ws, r, ["Layer", "Responsibility", "Why the boundary is there"],
          layers, [22, 66, 64], wrap_cols=(2, 3), mark_col=1)
r = note(ws, r, "The calculation layer never touches the screen and never touches files. That is what makes both future "
                "requirement changes and testing cheap.")

r = section(ws, r, "Deployment")
dep = [
    [f"{MARK_CHG}The user keeps one folder containing the .html file and ONE source workbook. Copying the folder moves the whole tool."],
    ["Updating the application means replacing the .html file. Source data is untouched, because it lives outside it (REQ-OUT-03)."],
    ["The application checks the source schema version on load and warns on a mismatch (REQ-VC-03)."],
]
r = table(ws, r, ["Point"], dep, [146], wrap_cols=(1,), mark_col=1)
r = legend(ws, r)

# ---- 08 WBS ---------------------------------------------------------------
ws, r = sheet(wb, "08_WBS_Schedule", "Work breakdown - the five steps",
              "Each step ends at a review gate. Work on the next step starts only after that gate is passed.")

wbs = [
    ["1", "1.1", "Draft the development plan.", "PRAP_Development_Plan_v0.1.xlsx", "Complete"],
    ["1", "1.2", "Requester reviews; answers the open questions.", "v0.11_reviewed mark-up", "Complete"],
    ["1", "1.3", "Propagate the answers across all sheets and re-issue.", "PRAP_Development_Plan_v0.2.xlsx", "Complete"],
    ["1", "1.4", "Answer the follow-up questions Q-13..Q-20.", "v0.2_reviewed mark-up", "Complete"],
    ["1", "1.5", "Incorporate round 2; work the period mapping through for coverage gaps.", "PRAP_Development_Plan_v0.3.xlsx", "Complete"],
    ["1", "1.6", "Settle the period-boundary questions Q-21..Q-26.", "v0.3_reviewed mark-up", "Complete"],
    ["1", "1.7", "Incorporate round 3; verify the derivation against degenerate timelines.", "PRAP_Development_Plan_v0.4.xlsx", "Complete - issued for review"],
    ["1", "1.8", "Answer Q-27 and Q-28.", "v0.4_reviewed mark-up", "Complete"],
    ["1", "1.9", "Final plan issue.", "PRAP_Development_Plan_v1.0.xlsx", "Complete - issued for review"],
    ["1", "G1", "GATE 1 - development plan approved by Dan, 2026-08-01. Decisions C-06..C-11 confirmed.", "Approval recorded on 12_Review_Log", "Complete"],

    ["2", "2.0", "Generate the source workbook template and a dummy data file for review.", "PRAP_SourceData_Template_v1.0.xlsx + _Dummy_v1.0.xlsx", "Complete - issued for review"],
    ["2", "2.1", "Fix the source workbook schema: exact sheet names, column headers, types, value lists.", "Specification sheet 'Data schema'", "In progress"],
    ["2", "2.2", "Specify the calculation engine as pseudocode plus the worked example as an acceptance test.", "Specification sheet 'Calculation'", "Not started"],
    ["2", "2.3", "Specify period derivation per project type, and the over/under-allocation detection.", "Specification sheet 'Calculation'", "Not started"],
    ["2", "2.4", "Specify import validation rules V-01..V-19 and the findings report.", "Specification sheet 'Validation'", "Not started"],
    ["2", "2.5", "Specify each dashboard tab: every table, column, graph, filter and interaction.", "Specification sheet 'UI spec'", "Not started"],
    ["2", "2.6", "Specify on-screen editing, the dirty-state model and export round-tripping.", "Specification sheet 'Editing & IO'", "Not started"],
    ["2", "2.7", "Specify the version/compatibility check.", "Specification sheet 'IO & versioning'", "Not started"],
    ["2", "2.8", "Build the requirement-to-specification traceability matrix.", "Specification sheet 'Traceability'", "Not started"],
    ["2", "G2", "GATE 2 - programming specification approved.", "PRAP_Programming_Specification_v1.0.xlsx", "Not started"],

    ["3", "3.1", "High-level UI design: tab structure, page regions, navigation. No code behind it.", "Prototype HTML (UI only)", "Not started"],
    ["3", "3.2", "Requester reviews the high-level component design.", "Review comments", "Not started"],
    ["3", "3.3", "Final UI design with clear per-component requirements.", "Prototype HTML v1.0 + component list", "Not started"],
    ["3", "G3", "GATE 3 - final design and component list approved. Code generation starts only for approved components.", "Approved component list", "Not started"],

    ["4", "4.1", "IO layer: workbook load, sheet/column mapping, export.", "Application code", "Not started"],
    ["4", "4.2", "Validation layer: rules V-01..V-19 and the findings report.", "Application code", "Not started"],
    ["4", "4.3", "Model layer, Lists and Config handling.", "Application code", "Not started"],
    ["4", "4.4", "Edit buffer: on-screen editing, dirty state, per-edit validation.", "Application code", "Not started"],
    ["4", "4.5", "Calculation engine, verified against the worked example.", "Application code + test evidence", "Not started"],
    ["4", "4.6", "Overall tab: tables, graphs, filters, over/under-allocation flagging.", "Application code", "Not started"],
    ["4", "4.7", "Source data (project) and Source data (person) tabs.", "Application code", "Not started"],
    ["4", "4.8", "Blank source workbook template with value lists and example rows.", "PRAP_SourceData template", "Not started"],
    ["4", "4.9", "Requester reviews output against real data; refinements folded in.", "Updated code", "Not started"],
    ["4", "G4", "GATE 4 - application functionally complete.", "PRAP_Application_v0.9.html", "Not started"],

    ["5", "5.1", "Full pass over the traceability matrix: every Must requirement demonstrated.", "Completed traceability matrix", "Not started"],
    ["5", "5.2", "Test on a clean Windows PC in Edge and Chrome, offline.", "Test evidence", "Not started"],
    ["5", "5.3", "Write the user guide: folder layout, how to load, how to maintain source data.", "User guide", "Not started"],
    ["5", "5.4", "Final version alignment across plan, specification and application.", "Version alignment table (sheet 09)", "Not started"],
    ["5", "G5", "GATE 5 - release.", "PRAP_Application_v1.0.html", "Not started"],
]
r_start = r
r = table(ws, r, ["Step", "Task", "Activity", "Deliverable", "Status"],
          wbs, [7, 8, 86, 42, 24], wrap_cols=(3, 4))
last = r_start + len(wbs)

dv2 = DataValidation(type="list",
                     formula1='"Not started,In progress,Pending you,Complete - issued for review,Complete,Blocked"',
                     allow_blank=True)
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
r = note(ws, r, "No duration estimates: the pace is set by review turnaround at each gate, not by build effort.")

# ---- 09 Version control ---------------------------------------------------
ws, r = sheet(wb, "09_Version_Control", "Version control across documents (REQ-VC-01)")

r = section(ws, r, "What is version-controlled")
vc = [
    ["Development plan", "PRAP_Development_Plan_v<ver>.xlsx", "docs/", "Sheet 01_Version_History"],
    ["Programming specification", "PRAP_Programming_Specification_v<ver>.xlsx", "docs/", "Its own version-history sheet"],
    ["Application", "PRAP_Application_v<ver>.html", "app/", "Version constant shown in the footer"],
    [f"{MARK_CHG}Source data template", "PRAP_SourceData_v<ver>.xlsx  (one workbook, was two)", "templates/", "schema_version in the Config sheet"],
    ["Output / evidence files", "PRAP_<content>_v<ver>_<yyyymmdd>.xlsx", "output/", "Filename plus a header block"],
    ["Generator scripts", "tools/*.py", "tools/", "Git history"],
]
r = table(ws, r, ["Artifact", "Naming convention", "Folder", "Where its version is recorded"],
          vc, [28, 56, 16, 44], wrap_cols=(2, 4), mark_col=1)

r = section(ws, r, "Version numbering")
num = [
    ["0.x", "Draft, under review. Content may change substantially.", "0.1 -> 0.2 on each re-issue during review."],
    ["x.0", "Approved baseline. Changing it requires a new approval.", "0.9 -> 1.0 at the gate."],
    ["x.y", "Approved change against a baseline: added requirement, bug fix, layout change.", "1.0 -> 1.1"],
    ["Schema version", "Independent counter for the source workbook structure. Steps only when a sheet or column changes.", "schema 1 -> 2"],
]
r = table(ws, r, ["Pattern", "Meaning", "Example"], num, [16, 86, 34], wrap_cols=(2,))
r = note(ws, r, "A reviewer mark-up carries the reviewed version's number with a suffix (v0.11_reviewed against v0.1). "
                "The incorporating issue takes the next draft number - here v0.2.")

r = section(ws, r, "Version alignment - which versions belong together")
align = [
    ["v0.1", "-", "-", "-", "2026-07-25", "Plan issued for review"],
    ["v0.2", "-", "-", "1 (draft)", "2026-07-31", "Reviewer answers incorporated; single-workbook schema defined"],
    ["v0.3", "-", "-", "1 (draft)", "2026-07-31", "Round 2 incorporated; type-specific period sets; milestone list replaced"],
    ["v0.4", "-", "-", "1 (draft)", "2026-07-31", "Round 3 incorporated; period model settled and verified"],
    ["v1.0", "-", "-", "1", DOC_DATE, "Step 1 baseline. APPROVED 2026-08-01 by Dan (Gate 1)."],
    ["", "", "", "", "", ""],
]
r = table(ws, r, ["Plan version", "Specification version", "Application version", "Schema version", "Date", "Note"],
          align, [15, 22, 20, 16, 14, 52], wrap_cols=(6,))
r = note(ws, r, "One row per release. Answers 'which specification produced this .html, and which source template does it expect?'.")

r = section(ws, r, "Repository rules")
git = [
    ["All work is committed to branch claude/project-resource-assignment-app-1vjdzh."],
    ["Documents are generated from scripts in tools/ so their content is reviewable as a text diff, not only as a binary."],
    ["One commit per meaningful change, with a message naming the step and the affected REQ-IDs."],
    ["A released version is tagged, so any release can be reproduced exactly."],
    [f"{MARK_NEW}Reviewer mark-ups are committed as received, unedited, so the review trail is auditable."],
]
r = table(ws, r, ["Rule"], git, [146], wrap_cols=(1,), mark_col=1)

# ---- 10 Risks -------------------------------------------------------------
ws, r = sheet(wb, "10_Risks", "Risks and assumptions")

r = section(ws, r, "Risks")
risks = [
    [f"{MARK_CHG}R-01", "The resource formula does not match how burden is actually judged, so output looks wrong.", "Medium", "High",
     "Reduced from High at Q-01, which fixed the three factors. A worked example (sheet 05) is agreed at Step 2 before code is written, and every factor stays in data."],
    ["R-02", "The source workbook is maintained inconsistently - typos, overlapping periods - and the simulation silently misleads.", "High", "Medium",
     "Fourteen validation rules on import, ID-based references instead of name matching, and a findings report the user cannot miss."],
    [f"{MARK_CHG}R-03", "Corporate policy blocks local .html files or restricts the browser.", "-", "-",
     "CLOSED at Q-05: local .html files open on the work PC. Re-test on the target PC at Step 5.2 all the same."],
    ["R-04", "Requirements grow after you see real output.", "High", "Medium",
     "Expected and planned for: six separated layers (sheet 07) plus extension columns already in the schema."],
    [f"{MARK_CHG}R-05", "Data volume grows beyond what a browser handles comfortably.", "Low", "Low",
     "Downgraded at Q-06: under 20 projects and 30 people is comfortably inside browser limits, with the headroom target in REQ-NFR-03."],
    ["R-06", "Excel date handling differs between Windows regional settings and misreads dates.", "Medium", "High",
     "Dates normalised to ISO on import; an unparseable date is a hard error, never a guess (REQ-NFR-05)."],
    ["R-07", "The file must be re-selected each session and this becomes irritating.", "Medium", "Low",
     "Optional browser caching (REQ-IMP-06) plus a one-click reload of the last file."],
    [f"{MARK_NEW}R-08", "On-screen edits are lost because the user closes the page without exporting.", "High", "High",
     "The direct cost of REQ-IMP-07. Mitigated by REQ-IMP-08: a visible unsaved-edit count and a warning before any action that discards them. The browser cache (REQ-IMP-06) becomes more valuable here as a second net."],
    [f"{MARK_CHG}R-09", "Milestone-derived periods break for a project with missing or out-of-order milestones.", "Medium", "High",
     "Raised from Medium impact: at v0.3 the derivation depends on specific milestones, so a missing CTA submission or DB lock now stops it outright. V-14 and V-16 make those errors rather than warnings; V-12 catches any remaining gap and falls back to weight 1.00 with a report."],
    [f"{MARK_CHG}R-10", "The weight and role-factor values are unknown to the plan, so output cannot be checked against reality until they are entered.", "Medium", "Medium",
     "Downgraded at Q-17: the values are data you enter in the source workbook, not a plan input, which is what REQ-CAL-06 always required. The engine is validated against the worked example on sheet 05; realism of the numbers is validated at WBS 4.9 against your real data."],
    [f"{MARK_CHG}R-11", "The period mapping leaves parts of a project with no period, so months silently carry a default weight.", "Low", "Medium",
     "Closed in substance at Q-21..Q-23: the mapping is now contiguous, verified against five timelines including four degenerate ones. REQ-CAL-10 and V-12 keep any residual gap visible rather than silent."],
    [f"{MARK_NEW}R-12", "Fully editable identifiers let a user break the links between sheets.", "Medium", "High",
     "The direct cost of the Q-20 answer. Mitigated by V-17 and REQ-IMP-10: identifier edits cascade after confirmation, and a referenced row cannot be deleted. Without that, 'every field editable' and 'no inconsistency' could not both hold."],
]
r = table(ws, r, ["ID", "Risk", "Likelihood", "Impact", "Mitigation"],
          risks, [9, 58, 12, 10, 64], wrap_cols=(2, 5), mark_col=1)

r = section(ws, r, "Assumptions")
assum = [
    [f"{MARK_CHG}A-01", "Data volume is under 20 projects and 30 people.", "CONFIRMED Q-06"],
    [f"{MARK_CHG}A-02", "One person's capacity is 1.00 FTE = 160 hours per month; part-timers carry a lower capacity_fte.", "CONFIRMED Q-08"],
    ["A-03", "Monthly granularity is sufficient; weekly or daily simulation is not required in v1.0.", "Standing"],
    ["A-04", "The source workbook is maintained by hand, not generated by another system.", "Standing"],
    [f"{MARK_CHG}A-05", "Windows 10 or 11 with Edge or Chrome, and local .html files open.", "CONFIRMED Q-05"],
    ["A-06", "Only one person maintains the workbook at a time - no concurrent editing to reconcile.", "Standing"],
    [f"{MARK_CHG}A-07", "Milestone dates now DRIVE period boundaries (REQ-CAL-09); they are no longer merely informational.", "Changed by Q-01/Q-04"],
    [f"{MARK_CHG}A-08", "Period sets are type-specific: five names for Clinical Trial (Conduct occurring up to twice), three for 'Others'.", "CONFIRMED Q-18, Q-23"],
    [f"{MARK_CHG}A-09", "A clinical trial's period weights are selected by its clinical phase.", "CONFIRMED Q-26"],
    [f"{MARK_CHG}A-10", "'Others' projects have no milestone mapping, so their three periods are entered by hand.", "CONFIRMED Q-25"],
    [f"{MARK_NEW}A-11", "No example source file is coming; the structure in this plan is taken as matching the existing one.", "CONFIRMED Q-13"],
]
r = table(ws, r, ["ID", "Assumption", "Status"], assum, [9, 110, 24], wrap_cols=(2,), mark_col=1)
r = legend(ws, r)

# ---- 11 Open questions ----------------------------------------------------
ws, r = sheet(wb, "11_Open_Questions", "Questions and answers",
              "All 28 questions raised across four review rounds, with their answers and how each was applied. "
              "Nothing is open.")

r = section(ws, r, "Answered at the v0.4 review  [round 4 - final]")
round4 = [
    ["Q-27", "Naming", "What is a close-out called on a trial with no interim lock?", "With no interim DB lock, the final DB lock falls into 'Close-out (final)'.", "Confirms v0.4 as built - one name, no special case in the weight lookup."],
    ["Q-28", "Calculation", "What selects period weights for 'Others' projects?", "No need to distinguish each 'Others' project. They are given manual input for the weight of periods.", "Applied - 'Others' weights are entered by hand, so PeriodWeightStandard becomes a clinical-trial table only. Together with Q-25 this makes 'Others' projects hand-entered throughout: dates and weights alike."],
]
r = table(ws, r, ["ID", "Topic", "Question (short)", "Your answer", "How it was applied in v1.0"],
          round4, [8, 15, 34, 62, 52], wrap_cols=(3, 4, 5))

r = section(ws, r, "Answered at the v0.3 review  [round 3]")
round3 = [
    ["Q-21", "Calculation", "Is 'Before-Start-up' the stretch before Start-up?", "Yes - project start date to 1 month before CTA submission.", "Applied - confirms the v0.3 reading. Sequence 1 on sheet 05."],
    ["Q-22", "Calculation", "Conduct ends 3 months prior, Close-out starts 2 - which?", "Close-out starts from 3 months prior, and runs until DB lock.", "Applied - Close-out is now 3 months long and Conduct ends the day before it. This is the opposite of the v0.3 default, which had shortened Close-out instead; corrected."],
    ["Q-23", "Calculation", "Which DB lock does Close-out end at?", "With an interim lock, split into 'Close-out (interim)' and 'Close-out (final)'. The stretches before and after 'Close-out (interim)' are both Conduct.", "Applied, and the largest change in v0.4: 'Conduct' can now occur twice in one project. ProjectPeriod gains period_seq; REQ-CAL-11 added; the clinical-trial period set grows to five names."],
    ["Q-24", "Data model", "Which is the eighth standard milestone?", "'Protocol (v1)'.", "Applied - milestone list now holds eight."],
    ["Q-25", "Data model", "How do 'Others' projects get their period dates?", "'Others' projects don't have milestone mapping.", "Applied - confirms the v0.3 assumption; their periods are entered by hand. Assumption A-10 confirmed."],
    ["Q-26", "Calculation", "What selects a project's weight?", "Clinical phase, where project_type is 'Clinical Trial'.", "Applied - PeriodWeightStandard re-keyed from project_category to clinical_phase. clinical_phase now drives the simulation, so V-19 makes a missing phase an error."],
]
r = table(ws, r, ["ID", "Topic", "Question (short)", "Your answer", "How it was applied in v0.4"],
          round3, [8, 15, 34, 62, 52], wrap_cols=(3, 4, 5))

r = section(ws, r, "Answered at the v0.2 review  [round 2]")
round2 = [
    ["Q-13", "Blocker", "The '13_Templete_example' sheet is missing.", "Structure already provided is similar to the existing one. No example file coming. Close this.", "CLOSED. WBS task 1.5 removed; assumption A-11 records that the schema in this plan is taken as matching yours."],
    ["Q-14", "Data model", "outsourcing_type listed a value twice.", "'Full outsourcing' / 'Partial outsourcing' / 'Full In-house'.", "Applied - three values, REQ-PRJ-04 and the Lists sheet."],
    ["Q-15", "Data model", "Which milestone set is standard?", "'CTA submission', 'First SIV', 'LPI', 'interim DB lock cut-off', 'interim DB lock', 'final DB lock cut-off', 'final DB lock'.", "Applied - list replaced; FPI dropped. The answer says eight but names seven, so the count is queried at Q-24."],
    ["Q-16", "Calculation", "Confirm the milestone-to-period mapping.", "Start-up = 1 month before CTA submission, 4 months long. Conduct = after Start-up to 3 months before interim DB lock (final if no interim). Close-out = 2 months before that DB lock, to DB lock.", "Applied with three corrections - the mapping as written leaves gaps. See sheet 05 and Q-21, Q-22, Q-23."],
    ["Q-17", "Calculation", "The weight and role-factor values.", "Actual numbers to be filled into the source file (excel).", "CLOSED. The plan fixes where the values live, not what they are - which is what REQ-CAL-06 always required. Risk R-10 downgraded. Part (c) of the question is handled by design and re-asked lightly at Q-26."],
    ["Q-18", "Calculation", "Do 'Others' projects share the same periods?", "No - 'Others' uses 'Planning' / 'Develop' / 'Close'.", "Applied - REQ-PRJ-12, type-specific period sets, V-15. Raises Q-25: those periods have no milestones to derive from."],
    ["Q-19", "Data model", "Can system_prepared_by be dropped?", "Yes - replaced by the EDC_setup .. DM_conduct fields.", "Applied - column removed from the Project sheet."],
    ["Q-20", "Editing", "Which fields should be editable?", "Every field. Validation rules prevent inconsistency between sheets instead.", "Applied - REQ-IMP-09 widened, REQ-IMP-10 and V-17 added, decision C-09, risk R-12."],
]
r = table(ws, r, ["ID", "Topic", "Question (short)", "Your answer", "How it was applied in v0.3"],
          round2, [8, 15, 34, 62, 52], wrap_cols=(3, 4, 5))

r = section(ws, r, "Answered at the v0.11 review  [round 1]")
answered = [
    ["Q-01", "Calculation", "Do weights multiply?", "Yes: project weight x role factor x person weight. Project weight comes from the project's category and is the same for everyone on that project in that milestone period. Role factor is the standard weight of the role. Person weight says how much the person works on the project.", "Applied - sheet 05. base_allocation removed; PersonPeriodWeight became an override."],
    ["Q-02", "Calculation", "Pro-rate partial months by calendar days?", "Yes - expected work follows the calendar days worked between the joined date and the end date.", "Applied - C-02 confirmed; REQ-CAL-05 raised to Must."],
    ["Q-03", "Roles", "Which roles, and do they differ in burden?", "Clinical Trial: Project oversight, Lead data manager, Clinical Data Associator, Clinical Database Programmer, Data Analyst. Others: Project lead, Main staff, Other staff.", "Applied - RoleFactor gains a project_type column; V-03 raised to an error."],
    ["Q-04", "Project periods", "Standard period names and weights?", "Before-Start-up, Start-up, Conduct, Close-out.", "Applied - sheet 04 ProjectPeriod. Weight VALUES still needed - Q-17."],
    ["Q-05", "Environment", "Can you open a local .html file?", "Yes.", "Applied - risk R-03 closed."],
    ["Q-06", "Data volume", "How many projects and people?", "Under 20 projects and 30 people.", "Applied - REQ-NFR-03 target reduced; R-05 downgraded."],
    ["Q-07", "Milestones", "Which milestones?", "CTA submission, FPI, LPI, DB lock cut-off, DB lock.", "Applied - Milestone list. Conflicts with the v0.11 mark-up in sheet 04 - see Q-15."],
    ["Q-08", "Capacity", "Capacity and thresholds?", "1 FTE = 160 h/month (8 h/day, 5 days/week, 20 days/month). Over-allocation: total above 1.5 FTE in a month. Under-allocation: below 0.8 FTE for 3 months or longer.", "Applied - REQ-CAL-04, REQ-CAL-07, REQ-CAL-08; Config parameters; sheet 06 flagging."],
    ["Q-09", "Source files", "One workbook or two?", "One single workbook with all sheets.", "Applied - sheet 04 restructured; REQ-OUT-03 reworded; architecture and deployment updated."],
    ["Q-10", "Existing data", "Existing spreadsheet structure?", "Refer to '13_Templete_example'.", "NOT APPLIED - that sheet is not in the returned file. See Q-13."],
    ["Q-11", "Horizon", "Planning horizon?", "24 months default, expandable to the latest project end date.", "Applied - REQ-CAL-01, REQ-DSH-07, Config default_horizon_months."],
    ["Q-12", "Scope check", "Anything wrongly out of scope?", "Fine.", "Applied - exclusions confirmed on sheet 02."],
]
r = table(ws, r, ["ID", "Topic", "Question (short)", "Your answer", "How it was applied in v0.2"],
          answered, [8, 15, 34, 62, 52], wrap_cols=(3, 4, 5))

r = section(ws, r, "Open questions")
r = table(ws, r, ["Status"],
          [["None. All 28 questions raised across the four review rounds are answered and applied."]],
          [146], wrap_cols=(1,))
r = note(ws, r, "Six engineering decisions - C-06 to C-11 on sheet 05 - were proposed during the review rounds and "
                "never explicitly answered. Rather than open a fifth round for them, Gate 1 approval confirms them. "
                "They are listed on sheet 05 with their rationale.")

# ---- 12 Review log --------------------------------------------------------
ws, r = sheet(wb, "12_Review_Log", "Review log and approval",
              "Every change made in v0.2, and why. Reviewer input was given as direct mark-up in "
              "PRAP_Development_Plan_v0.11_reviewed.xlsx rather than as cell comments.")

log = [
    ["1", "11_Open_Questions", "All 12 questions answered.", "Accepted in full.", "Propagated into sheets 02-10; see rows below.", "Closed"],
    ["2", "03_Requirements!A43", "New requirement added: 'After importing the source excel file, HTML to provide updating data and the updated data to be absorbed in the exported file when it extracts from the HTML.'", "Accepted. Numbered REQ-IMP-07.", "Added REQ-IMP-07, plus REQ-IMP-08 (unsaved-edit warning) and REQ-IMP-09 (re-validate edits), which it implies. Withdrew the v0.1 rule that nothing is editable (sheet 06). Added edit-buffer layer (sheet 07) and risk R-08.", "Closed"],
    ["3", "04_Data_Model - Project", "Added clinical_phase; EDC_setup, DataReviewSystem_setup, RBQM_setup, DM_conduct; EDC_system, DataReviewSystem, RBQM_system. Made outsourcing_type required.", "Accepted.", "All carried into the Project sheet with REQ-IDs REQ-PRJ-09/10/11. Value lists moved to the new Lists sheet. V-10 and V-11 added.", "Closed"],
    ["4", "04_Data_Model - Project", "outsourcing_type list reads 'Full outsourcing' / 'Partial outsourcing' / 'Full In-house' / 'Partial outsourcing'.", "Query - 'Partial outsourcing' appears twice.", "Flagged as Q-14. Resolved at round 2 - three values, see item 17.", "Closed"],
    ["5", "04_Data_Model - Milestone", "Milestone examples changed to FPI, LPI, LPO, LPLV, interim DB Lock, final DB Lock, CSR.", "Query - conflicts with the Q-07 answer, which names five different milestones.", "Q-07's list adopted as standard; raised as Q-15. Superseded at round 2 by a replacement list - see item 18.", "Closed"],
    ["6", "04_Data_Model", "Added project_name to Milestone and person_name to Assignment.", "Accepted with a safeguard.", "Kept as display conveniences, explicitly non-authoritative. V-13 checks them against the master row and refreshes rather than trusting them, so a stale copy cannot break a link.", "Closed"],
    ["7", "Q-09 answer", "One single workbook instead of two.", "Accepted.", "Sheet 04 restructured into one workbook of ten sheets; REQ-OUT-03, REQ-IMP-01/03 reworded; architecture option (b) rejection strengthened; deployment updated.", "Closed"],
    ["8", "Q-01 answer", "Three factors: project weight x role factor x person weight.", "Accepted, with one consequence.", "base_allocation removed - it was a fourth factor the answer did not name. Renamed to person_weight. PersonPeriodWeight changed from a multiplier to an override so no hidden fourth factor returns. Sheet 05 rewritten.", "Closed"],
    ["9", "Q-08 answer", "1 FTE = 160 h/month; over-allocation above 1.5 FTE; under-allocation below 0.8 FTE for 3+ months.", "Accepted.", "REQ-CAL-04 rewritten, REQ-CAL-07 and REQ-CAL-08 added. Under-allocation needs a rolling 3-month window, so it is specified as a run with a start and length, not a per-month flag. Config parameters added; sheet 06 flags both.", "Closed"],
    ["10", "Q-04 + Q-07 answers", "Standard periods and milestones named.", "Accepted, with a derivation.", "Periods are now derived from milestone dates (REQ-CAL-09) so a timeline change re-shapes them automatically. Mapping raised as Q-16 and answered at round 2 with a different mapping - see item 19. Assumption A-07 changed: milestones now drive weights.", "Closed"],
    ["11", "Q-06 answer", "Under 20 projects and 30 people.", "Accepted.", "REQ-NFR-03 target cut from 100 projects / 200 people / 1,000 assignments to a realistic figure with headroom; R-05 downgraded to Low/Low.", "Closed"],
    ["12", "Q-10 answer", "'Refer to 13_Templete_example'.", "Cannot action - the sheet is absent from the returned workbook.", "Verified against the file itself: it holds 13 sheets, 00 to 12, none hidden. Raised as Q-13; closed at round 2 - see item 16.", "Closed"],
    ["13", "02_Scope!A1", "Sheet title cell was blank in the returned file.", "Treated as accidental.", "Title 'Scope and objectives' restored.", "Closed"],
    ["14", "Q-03 answer", "Role lists differ between project types.", "Accepted.", "RoleFactor gains a project_type column; roles are matched on (project type, role name). V-03 raised from warning to error, since a role from the wrong type is now a real mistake rather than a typo.", "Closed"],
    ["15", "-", "Role factors and period weight values.", "Not supplied at round 1.", "Resolved at round 2 - see item 20.", "Closed"],

    ["16", "Q-13 answer (round 2)", "'No example file provided from me. Close this.'", "Accepted.", "Blocker cleared. WBS task 1.5 removed; assumption A-11 records that the schema here is taken as matching the existing one.", "Closed"],
    ["17", "Q-14 answer", "outsourcing_type has three values.", "Accepted.", "REQ-PRJ-04 and the Project sheet corrected.", "Closed"],
    ["18", "Q-15 answer", "Milestone list replaced - First SIV in, FPI out, DB lock cut-off and DB lock split interim/final.", "Accepted, with one query.", "Milestone list replaced throughout. The count query was answered at Q-24 - 'Protocol (v1)' is the eighth. See item 27.", "Closed"],
    ["19", "Q-16 answer", "Milestone-to-period mapping given for Start-up, Conduct and Close-out.", "Accepted in substance; three gaps found.", "Worked the mapping through a test project: it leaves 59 days before Start-up, 30 days between Conduct and Close-out, and 183 days after the interim DB lock with no period at all. A no-gap reading was adopted and the three points raised as Q-21..Q-23, all answered at round 3 - see items 24..26. REQ-CAL-10 and risk R-11 added so any residual gap is reported rather than silent.", "Closed"],
    ["20", "Q-17 answer", "'Actual numbers to be filled into the source file (excel).'", "Accepted - this closes the question rather than deferring it.", "The plan fixes where the values live, not what they are, which is what REQ-CAL-06 required all along. R-10 downgraded from High/High to Medium/Medium. Engine correctness is proven against the worked example; realism against your data at WBS 4.9.", "Closed"],
    ["21", "Q-18 answer", "'Others' projects use Planning / Develop / Close.", "Accepted.", "REQ-PRJ-12 added; ProjectPeriod and PeriodWeightStandard keyed by project_type; V-15 rejects a period from the wrong set. Q-25 confirmed at round 3 that 'Others' periods are entered by hand.", "Closed"],
    ["22", "Q-19 answer", "system_prepared_by can be dropped.", "Accepted.", "Column removed from the Project sheet.", "Closed"],
    ["23", "Q-20 answer", "Every field editable; validation rules prevent inconsistency.", "Accepted, with the mechanism made explicit.", "REQ-IMP-09 widened to all fields; REQ-IMP-10 and V-17 added for cascading identifier edits and refused deletes; decision C-09; risk R-12. Cascading is what makes an editable identifier safe - blocking the edit would have made it read-only in all but name.", "Closed"],

    ["24", "Q-21 answer (round 3)", "Before-Start-up runs from project start to one month before CTA submission.", "Accepted - confirms the v0.3 reading.", "Sequence 1 of the derivation on sheet 05, unchanged.", "Closed"],
    ["25", "Q-22 answer", "Close-out starts 3 months prior to DB lock and runs until DB lock.", "Accepted - and it reverses the v0.3 default.", "v0.3 had closed the one-month gap by shortening Close-out to two months. Your answer closes it the other way: Close-out is three months and Conduct ends the day before it. Corrected on sheet 05.", "Closed"],
    ["26", "Q-23 answer", "With an interim DB lock, split into Close-out (interim) and Close-out (final); the stretches either side of Close-out (interim) are both Conduct.", "Accepted. The structural change of v0.4.", "A period name is no longer unique within a project - Conduct now occurs twice. ProjectPeriod gains period_seq; REQ-CAL-11 added; V-18 enforces sequence uniqueness; the clinical-trial period set grows from four names to five. Derivation re-verified contiguous.", "Closed"],
    ["27", "Q-24 answer", "The eighth standard milestone is 'Protocol (v1)'.", "Accepted.", "Milestone list now holds eight. Only CTA submission and the DB locks are boundaries; the other six are markers.", "Closed"],
    ["28", "Q-25 answer", "'Others' projects have no milestone mapping.", "Accepted.", "Confirms the v0.3 assumption. A-10 moves from 'to confirm' to confirmed; their three periods are entered by hand.", "Closed"],
    ["29", "Q-26 answer", "A clinical trial's weight relies on clinical_phase.", "Accepted, with one consequence worth noting.", "PeriodWeightStandard re-keyed from project_category to clinical_phase. clinical_phase stops being descriptive and starts driving the simulation, so V-19 makes a missing phase an error rather than the warning it was under V-10. Raises Q-28: 'Others' projects have no phase.", "Closed"],
    ["30", "Sheet 05 - derivation", "Not reviewer input - a check made while applying the answers.", "Five timelines tested.", "The revised mapping was run against the normal case plus four degenerate ones: interim and final locks a month apart, no interim lock, CTA submission before project start, and a trial too short to have a Conduct phase. All five come out contiguous. Rules recorded as REQ-CAL-12 and decision C-11, and the omission cases documented on sheet 05.", "Closed"],
    ["31", "-", "Naming and 'Others' weighting.", "Two small points raised.", "Raised as Q-27 and Q-28; both answered at round 4 - see items 32 and 33.", "Closed"],

    ["32", "Q-27 answer (round 4)", "With no interim DB lock, the final DB lock falls into 'Close-out (final)'.", "Accepted - confirms v0.4 as built.", "No change needed. One period name covers both cases, so the weight lookup needs no special branch.", "Closed"],
    ["33", "Q-28 answer", "'Others' projects are not distinguished, and take manual input for period weights.", "Accepted, and it simplifies the model.", "PeriodWeightStandard becomes a clinical-trial reference table only; its '*' rows are gone. Combined with Q-25, 'Others' projects are now hand-entered throughout - both period dates and period weights. V-19 scoped to clinical trials. REQ-PRJ-06 reworded.", "Closed"],
    ["34", "Sheet 05 - decisions C-06..C-11", "Not reviewer input - six decisions proposed during the review rounds and never explicitly answered.", "Resolved at approval rather than by a fifth round.", "Gate 1 approval confirms C-06 (over/under-allocation judged on the person total), C-07 (period weights seeded then editable), C-08 (a month belongs to the period containing its first day), C-09 (identifier edits cascade), C-10 (boundaries recomputed on milestone change unless hand-edited) and C-11 (ordered clipping). Each is stated with its rationale on sheet 05.", "Closed"],
]
r_start = r
r = table(ws, r, ["No.", "Sheet / source", "Reviewer input", "Response", "Action taken in v0.2", "Status"],
          log, [6, 22, 56, 40, 76, 12], wrap_cols=(3, 4, 5))

dv3 = DataValidation(type="list", formula1='"Open,Accepted,Rejected,Deferred,Closed"', allow_blank=True)
ws.add_data_validation(dv3)
dv3.add(f"F{r_start + 1}:F{r_start + len(log)}")

r = section(ws, r, "Disposition summary")
disp = [
    ["Closed in v0.2", f'=COUNTIF(F{r_start + 1}:F{r_start + len(log)},"Closed")'],
    ["Open - awaiting your answer", f'=COUNTIF(F{r_start + 1}:F{r_start + len(log)},"Open")'],
    ["Total items", f"=COUNTA(A{r_start + 1}:A{r_start + len(log)})"],
]
r = table(ws, r, ["Measure", "Count"], disp, [30, 12])

r = section(ws, r, "Approval - Gate 1")
appr = [["PRAP Development Plan v1.0", "Dan", "2026-08-01",
         "APPROVED. Finalise plan v1.0 and proceed to Step 2, beginning with generation of the workbook "
         "template and a dummy data file for review."]]
r_start2 = r
r = table(ws, r, ["Document", "Approver", "Date", "Decision"], appr, [30, 16, 14, 88], wrap_cols=(4,))
for cc in (1, 2, 3, 4):
    ws.cell(row=r_start2 + 1, column=cc).fill = NEW_FILL
r = note(ws, r, "GATE 1 PASSED. The 63 requirements on sheet 03 are baselined as the contract for Steps 2-5, and "
                "decisions C-06 to C-11 on sheet 05 are confirmed. Any change to them now requires a new approval "
                "and a version increment, per the rules on sheet 09.")

wb.save(OUT)
print(f"Written: {OUT}")
