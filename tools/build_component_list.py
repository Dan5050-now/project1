"""Generate the Step 3 UI component list - the thing being reviewed alongside the prototype.

From v0.4 this is a disposition document as well as a review form: it carries the
reviewer's own words against each component, what was done about them, and what is
left. The review trail lives in the deliverable rather than in a chat log.

    python tools/build_component_list.py

Output: docs/PRAP_UI_Component_List_v0.4.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

VERSION = "0.4"
DATE = "2026-08-01"
PROTOTYPE = "app/PRAP_Prototype_v0.4.html"
OUT = Path(__file__).resolve().parents[1] / "docs" / f"PRAP_UI_Component_List_v{VERSION}.xlsx"

FONT = "Arial"
NAVY = "1F3864"
TITLE_F = Font(name=FONT, size=16, bold=True, color=NAVY)
H1_F = Font(name=FONT, size=12, bold=True, color=NAVY)
HDR_F = Font(name=FONT, size=10, bold=True, color="FFFFFF")
BODY_F = Font(name=FONT, size=10)
BOLD_F = Font(name=FONT, size=10, bold=True)
NOTE_F = Font(name=FONT, size=9, italic=True, color="808080")
HDR_FILL = PatternFill("solid", fgColor="2F5597")
BAND = PatternFill("solid", fgColor="F2F5FB")
INPUT = PatternFill("solid", fgColor="FFFF00")
NEWF = PatternFill("solid", fgColor="E2F0D9")      # added by this review
CHGF = PatternFill("solid", fgColor="FFF2CC")      # changed by this review
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
WRAPC = Alignment(vertical="top", wrap_text=True, horizontal="center")


def table(ws, r0, headers, rows, widths, wrap_cols=(), yellow_col=None, mark_col=None):
    for i, h in enumerate(headers, 1):
        c = ws.cell(r0, i, h)
        c.font, c.fill, c.border, c.alignment = HDR_F, HDR_FILL, BOX, WRAPC
    ws.row_dimensions[r0].height = 28
    for r, data in enumerate(rows, r0 + 1):
        mark = ""
        if mark_col is not None:
            v = str(data[mark_col - 1] or "")
            for tag, fill in (("[NEW]", NEWF), ("[CHANGED]", CHGF)):
                if v.startswith(tag):
                    mark, data = fill, list(data)
                    data[mark_col - 1] = v.replace(tag, "", 1).lstrip()
                    break
        for i, v in enumerate(data, 1):
            c = ws.cell(r, i, v)
            c.font, c.border = BODY_F, BOX
            c.alignment = WRAP if i in wrap_cols else Alignment(vertical="top")
            if yellow_col == i:
                c.fill = INPUT
            elif mark:
                c.fill = mark
            elif (r - r0) % 2 == 0:
                c.fill = BAND
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    return r0 + len(rows) + 2


wb = Workbook()
wb.remove(wb.active)

# ---- cover ---------------------------------------------------------------
ws = wb.create_sheet("00_Cover")
ws.sheet_view.showGridLines = False
ws["A1"] = "PRAP — UI component list"
ws["A1"].font = TITLE_F
ws["A2"] = "Step 3, task 3.1 — review round 2: your decisions applied"
ws["A2"].font = NOTE_F
meta = [("Version", f"v{VERSION}"), ("Date", DATE), ("Author", "Claude Code"),
        ("Reviewer", "Dan — v0.3 reviewed 2026-08-01"),
        ("Prototype", PROTOTYPE),
        ("Governing plan", "PRAP_Development_Plan_v1.6.xlsx (changes R-05..R-09, awaiting signature)"),
        ("Specification", "PRAP_Programming_Specification_v0.5.xlsx (draft)")]
r = 4
for k, v in meta:
    ws.cell(r, 1, k).font = BOLD_F
    ws.cell(r, 2, v).font = BODY_F
    r += 1
ws.column_dimensions["A"].width = 22
ws.column_dimensions["B"].width = 92

r += 1
ws.cell(r, 1, "What happened to your v0.3 review").font = H1_F
r += 1
for line in [
    "All 15 design decisions accepted. Of the 38 components, 29 marked Keep and 9 marked Change.",
    "Every one of the 9 is applied in the prototype named above - none is deferred, none is partial.",
    "",
    "Sheet 01 carries your decision and your comment verbatim against each component, with a column",
    "saying what was actually done. Six new components appeared as a result of your changes; they are",
    "tinted green. The nine you changed are tinted amber.",
    "",
    "Sheet 02 records the decisions. One needs your attention: you accepted D-06 (the timeline shades",
    "bands by weight) and separately asked in O-10 for the timeline to be coloured by period name.",
    "Those cannot both hold. O-10 is the more specific instruction and the later intent, so it wins -",
    "D-06 is marked SUPERSEDED and weight now rides as a lightness step inside each period's hue,",
    "so nothing that drove the simulation stopped being visible. Overturn that on sheet 02 if I have",
    "read you backwards.",
    "",
    "Sheet 04 lists what your review changed outside this document: two new requirements, two",
    "reworded, and the plan and specification versions that carry them.",
    "",
    "To review this round: open the prototype, then mark the YELLOW column on sheets 01 and 02 -",
    "'OK' where the change landed, or 'Rework' with a note where it did not.",
]:
    ws.cell(r, 1, line).font = BODY_F
    r += 1

# ---- components ----------------------------------------------------------
ws = wb.create_sheet("01_Components")
ws.sheet_view.showGridLines = False
ws["A1"] = "Component list — your decisions and what was done"
ws["A1"].font = TITLE_F
ws["A2"] = ("44 components. 29 Keep, 9 Change (amber), 6 added by those changes (green). "
            "Your comments are quoted exactly as written.")
ws["A2"].font = NOTE_F
ws.freeze_panes = "A5"

K = "Keep"
C = [
    # id, area, component, what it does, REQ-IDs, your decision, your comment, what was done
    ("G-01", "Global", "Header", "Application name, version, expected schema version.",
     "REQ-VC-02", K, "", "Unchanged."),
    ("G-02", "Global", "[CHANGED] Loaded-file line",
     "Which workbook is loaded, and when it was read - now with the time zone.",
     "REQ-IMP-05", "Change",
     "Add GMT timezone for loaded date & time information. E.g. loaded 2026-08-01 09:14 (GMT+G6, KST)",
     "Done. The stamp now reads 'loaded 2026-08-01 09:14 (GMT+9, KST)'. The offset and the zone "
     "abbreviation both show, because either alone is ambiguous to a reader in another country. Taken "
     "as GMT+9 / KST - your note says 'GMT+G6', which I have read as a typing slip for GMT+9 given "
     "KST beside it. Correct me if not."),
    ("G-03", "Global", "Load workbook", "File picker / drag-and-drop. Warns first if edits are unsaved.",
     "REQ-IMP-01, REQ-IMP-08", K, "", "Unchanged."),
    ("G-04", "Global", "Export", "Writes all ten sheets back in template layout, edits included.",
     "REQ-IMP-04, REQ-IMP-07", K, "", "Unchanged."),
    ("G-05", "Global", "Findings banner", "Summary of the last import; opens the full report.",
     "REQ-IMP-02", K, "", "Unchanged."),
    ("G-06", "Global", "[CHANGED] Unsaved-edit counter",
     "Always visible once anything is edited, and now states the validation standing of those edits.",
     "REQ-IMP-08, REQ-IMP-09", "Change",
     "When anything is changed, the update to be checked with validation rules and if no doubt on the "
     "updated all the changes to be included into the exported file when a use runs exporting.",
     "Done, and it was already the specified behaviour - what was missing was any sign of it on screen. "
     "The counter now reads '3 unsaved edits · all 3 pass validation', and says outright that a failing "
     "edit is rejected at entry so nothing invalid can reach the export. The rule has not changed; it "
     "has become visible."),
    ("G-07", "Global", "[CHANGED] Tab bar",
     "Overall | Source data (project) | Source data (person) | General assumptions.",
     "REQ-DSH-01..04, REQ-DSH-11", "Change",
     "Add 'General assumtions' tab having other general information (e.g. 'PeriodWeightStandard' "
     "sheet, 'RoleFactor' sheet)",
     "Done - a fourth tab, and the one gap in the design worth closing. Every figure on the Overall "
     "tab is the product of these two tables, yet they were reachable only by opening the workbook. "
     "See A-01 to A-04 for what the tab holds. This one needed a new requirement, REQ-DSH-11."),
    ("G-08", "Global", "Empty state", "With nothing loaded: one load panel and a template download link.",
     "REQ-IMP-03", K, "", "Unchanged."),

    ("O-01", "Overall", "Horizon control", "From/to month, defaulting to 24 months.",
     "REQ-CAL-01", K, "", "Unchanged."),
    ("O-02", "Overall", "Expand to all projects", "One click widens the horizon to the latest project end date.",
     "REQ-DSH-07", K, "", "Unchanged."),
    ("O-03", "Overall", "[CHANGED] Filters (GLOBAL)",
     "Project type, clinical phase, project, person, role, department. One setting drives every tab.",
     "REQ-DSH-05", "Change",
     "Filter for 'Unit' isn't needed because of no meaning. Instead, add 'Clinical trial phase' right "
     "side of 'Project type'.",
     "Done both ways. 'Unit' is gone from the bar and moved to the new tab as configuration (see O-04) "
     "- you are right that it was never a filter: it changed how figures are written, not which are "
     "shown. 'Clinical phase' now sits immediately right of 'Project type', where the two type-ish "
     "controls read as a pair."),
    ("O-03b", "Overall", "Reset filters", "Clears every filter and restores the 24-month default in one action.",
     "REQ-DSH-05", K, "", "Unchanged."),
    ("O-04", "Overall", "[CHANGED] Unit toggle",
     "FTE or hours. Now a setting on the General assumptions tab, not a filter.",
     "REQ-CAL-08", "Change",
     "Include configuration information into the new sheet (i.e. General assumptions).",
     "Done. The whole Config sheet is on the new tab, and the display-unit control sits with it, "
     "under a line explaining why it is not in the filter bar."),
    ("O-05", "Overall", "Summary tiles",
     "Projects, people, total demand, over-allocated months, under-allocation runs.",
     "REQ-DSH-08", K, "", "Unchanged."),
    ("O-06", "Overall", "[CHANGED] Demand chart",
     "Stacked monthly demand, one band per project, largest on the baseline. No legend; hover pop-up instead.",
     "REQ-DSH-02", "Change",
     "In 'Monthly demand by project' section, remove legend information on the bottom. Instead, while "
     "hovering over each stack in the graph, provide pop-up information (e.g. project name, project's "
     "month FTE, acting people in the months).",
     "Done. The legend is gone and a real hover pop-up replaces it, carrying project name and type, "
     "that month's FTE and its hour equivalent, the headcount, and every person on the project that "
     "month with their role. Note the knock-on: D-11 argued that identity came from the legend order "
     "because 62 hues cannot be told apart. The tooltip now carries that alone - which is stronger, "
     "since it names one band rather than asking you to match a colour against a list of 62."),
    ("O-07", "Overall", "Resource by project (table)",
     "Project x month heatmap. Sorted NewDrug CT, Biosimilar CT, Others, then earliest first.",
     "REQ-DSH-01", K, "", "Unchanged."),
    ("O-07b", "Overall", "Project row expansion",
     "Clicking a project name reveals a row per person and role, each with its own monthly figures.",
     "REQ-DSH-01", K, "", "Unchanged."),
    ("O-08", "Overall", "Mean load per person (chart)",
     "One bar per person against both absolute thresholds; above the bar budget, a ranked subset.",
     "REQ-DSH-02, REQ-DSH-08, REQ-DSH-09", K, "", "Unchanged."),
    ("O-09", "Overall", "Resource by person (table)",
     "Person x month, summed across projects, over/under flagged.",
     "REQ-DSH-01, REQ-DSH-08", K, "", "Unchanged."),
    ("O-09b", "Overall", "Person row expansion",
     "Clicking a person name reveals a row per project and role, in the same type-then-date order.",
     "REQ-DSH-01", K, "", "Unchanged."),
    ("O-10", "Overall", "[CHANGED] Project timeline (Gantt)",
     "First panel on the tab. Duration under each name, bands coloured by period, milestone markers.",
     "REQ-DSH-02, REQ-PRJ-05, REQ-DSH-10", "Change",
     "1. Add project duration (start date, end date, total month) under individual project name. "
     "2. Change color more intuitive. e.g. before start-up (Grey), Start-up (Red), Conduct (Green), "
     "Close-out (Orange), After close-out (Dark Grey). Information given when hovering over, should "
     "include monthly FTE for each period. "
     "3. No need to seperate 'Inspection' because of that being one of milestones. Change the icon for "
     "milestone from circle to inverted triangle highlighted. "
     "4. Location: as first section right after 'Horizon and filters' section.",
     "All four done. (1) 'start -> end · n months' sits under each project name. (2) Your mapping is "
     "followed, with one departure: red beside green is the pair red-green colour blindness collapses, "
     "and you accepted D-04 making 'never colour alone' a floor - so the red is shifted slightly toward "
     "orange, every band wide enough carries its period name as text, and the tooltip names it outright. "
     "The two close-outs take a light and a deep orange so they are not one indistinguishable block. "
     "The tooltip carries dates, weight and the FTE per month the project draws across that period. "
     "(3) 'Inspection' now takes the same marker as every other milestone, and the marker is an inverted "
     "triangle in its own lane above the bands, so it never lands on a band label. (4) The timeline is "
     "now the first panel, above the summary tiles. This change supersedes D-06 - see sheet 02."),

    ("P-01", "Project tab", "[CHANGED] Project table",
     "All 23 columns, sortable, filterable, editable, with an insert control on every row.",
     "REQ-DSH-03, REQ-IMP-07, REQ-IMP-11", "Change",
     "Add 'Insert new row' button for all rows and all sections. When clicking the button, new row to "
     "be added right after the row where a user clicks that button.",
     "Done, and generalised - see X-06. Every row of every editable table now carries '+ row', and the "
     "new row lands directly below the row you pressed, not at the bottom of the table. This needed a "
     "new requirement, REQ-IMP-11: nothing in the plan said a row could be created at all."),
    ("P-02", "Project tab", "Milestone sub-table",
     "Milestones of the selected project in date order; Inspection may repeat.",
     "REQ-PRJ-05, REQ-PRJ-13", K, "", "Unchanged except for gaining the insert control (X-06)."),
    ("P-03", "Project tab", "Period sub-table",
     "Derived periods with seq, dates, weight and note; repeated names numbered.",
     "REQ-PRJ-06, REQ-CAL-09, REQ-DSH-10", K, "", "Unchanged except for gaining the insert control (X-06)."),
    ("P-04", "Project tab", "Recompute periods",
     "Re-derives from current milestones; warns before replacing hand-set dates.",
     "decision C-10", K, "", "Unchanged."),
    ("P-05", "Project tab", "Export visible table", "Current table to .xlsx.",
     "REQ-DSH-06", K, "", "Unchanged."),

    ("S-01", "Person tab", "[CHANGED] Person table",
     "All 12 columns, sortable, filterable, editable, with an insert control on every row.",
     "REQ-DSH-04, REQ-IMP-07, REQ-IMP-11", "Change",
     "Add 'Insert new row' button for all rows and all sections. When clicking the button, new row to "
     "be added right after the row where a user clicks that button.",
     "Done - same treatment as P-01, and the same generalisation to every section (X-06)."),
    ("S-02", "Person tab", "Utilisation strip",
     "Selected person's monthly load with both absolute thresholds drawn.",
     "REQ-DSH-08", K, "", "Unchanged."),
    ("S-03", "Person tab", "Assignment sub-table", "Project, role, dates and person weight.",
     "REQ-PSN-02, REQ-PSN-03", K, "", "Unchanged except for gaining the insert control (X-06)."),
    ("S-04", "Person tab", "Override sub-table", "PersonPeriodWeight windows for the selected assignment.",
     "REQ-PSN-05", K, "", "Unchanged except for gaining the insert control (X-06)."),
    ("S-05", "Person tab", "Export visible table", "Current table to .xlsx.",
     "REQ-DSH-06", K, "", "Unchanged."),

    ("E-01", "Editing", "Inline cell edit", "Every field editable, validated at the point of entry.",
     "REQ-IMP-09", K, "", "Unchanged."),
    ("E-02", "Editing", "Cascade confirm",
     "Changing an identifier states how many rows will follow, then rewrites them.",
     "REQ-IMP-10, V-17", K, "", "Unchanged."),
    ("E-03", "Editing", "Delete guard",
     "Refuses to delete a row that is still referenced, naming what points at it.",
     "V-17", K, "", "Unchanged."),

    ("X-01", "Layout", "Horizontal scroll regions",
     "Every chart and table scrolls inside its own panel, so the page body never scrolls sideways.",
     "REQ-NFR-02", K, "", "Unchanged."),
    ("X-02", "Layout", "Type and phase pills",
     "Project type and clinical phase as labelled pills; text carries the meaning, colour only speeds recognition.",
     "REQ-PRJ-01, REQ-PRJ-09", K, "", "Unchanged."),
    ("X-03", "Layout", "Numbered repeated periods",
     "'Conduct (1)', 'Conduct (2)' wherever a period name occurs more than once.",
     "REQ-DSH-10", K, "", "Unchanged. Now also visible on the timeline bands themselves."),
    ("X-04", "Layout", "Row virtualisation",
     "Both Overall tables render only the rows in the viewport plus overscan.",
     "REQ-DSH-09, REQ-NFR-03", K, "", "Unchanged."),

    ("A-01", "Assumptions tab", "[NEW] Standard period weights",
     "PeriodWeightStandard as a matrix - phase down the side, period across, shaded by magnitude.",
     "REQ-DSH-11", "", "",
     "Added for G-07. Shown as a matrix, not 48 flat rows: it is a standard, and a standard is read "
     "across. 'Others' projects are absent by design - their weights are hand-entered per project."),
    ("A-02", "Assumptions tab", "[NEW] Role factors",
     "RoleFactor: what one person in a role costs the project per month, keyed on project type.",
     "REQ-DSH-11", "", "",
     "Added for G-07. Keyed on type, so the same role can weigh differently on a new-drug trial and "
     "a biosimilar."),
    ("A-03", "Assumptions tab", "[NEW] Configuration",
     "Config: thresholds and settings, plus the display-unit control moved here from the filter bar.",
     "REQ-DSH-11, REQ-CAL-08", "", "",
     "Added for G-07 and O-04. The thresholds that colour the tables now sit next to a note saying "
     "what they mean."),
    ("A-04", "Assumptions tab", "[NEW] Value lists",
     "Lists: what each list-typed column will accept, and how many values each list holds.",
     "REQ-DSH-11", "", "",
     "Added for G-07. Answers 'what may I type here' without opening the workbook."),
    ("X-05", "Layout", "[NEW] Hover pop-up layer",
     "A real tooltip - follows the cursor, flips at the screen edge, carries formatted multi-line content.",
     "REQ-DSH-02", "", "",
     "Added for O-06 and O-10. The native SVG tooltip cannot show a list of people and waits half a "
     "second to appear, so it could not do what you asked for. This moves off the deferred list, where "
     "v0.3 had it."),
    ("X-06", "Layout", "[NEW] Insert-row control",
     "'+ row' leading every row of every editable table; the new row lands directly below that row.",
     "REQ-IMP-11", "", "",
     "Added for P-01 and S-01, generalised to 'all sections' as you asked: both source-data tables, "
     "all four sub-tables, and the role-factor and config tables on the new tab. The control leads the "
     "row - see D-18 for why."),
]
rows = [list(c) + [""] for c in C]
r = table(ws, 4,
          ["ID", "Area", "Component", "What it does", "REQ-IDs",
           "Your decision", "Your comment (verbatim)", "What was done in v0.4", "Confirm"],
          rows, [8, 15, 30, 56, 26, 12, 62, 86, 14],
          wrap_cols=(3, 4, 7, 8, 9), yellow_col=9, mark_col=3)
dv = DataValidation(type="list", formula1='"OK,Rework"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"I5:I{4 + len(rows)}")
r = table(ws, r, ["Count", "Keep", "Changed", "Added"],
          [[f"=COUNTA(A5:A{4 + len(rows)})",
            sum(1 for c in C if c[5] == K),
            sum(1 for c in C if c[5] == "Change"),
            sum(1 for c in C if "[NEW]" in c[2])]], [14, 10, 10, 10])
ws.cell(r, 1, "Green = added by this review. Amber = changed by this review.").font = NOTE_F

# ---- design decisions ----------------------------------------------------
ws = wb.create_sheet("02_Design_Decisions")
ws.sheet_view.showGridLines = False
ws["A1"] = "Design decisions — all 15 accepted, one now superseded"
ws["A1"].font = TITLE_F
ws["A2"] = ("You accepted every decision. D-06 is nonetheless overturned, because O-10 asks for the "
            "opposite; that conflict is the one thing on this sheet needing your eye.")
ws["A2"].font = NOTE_F
ws.freeze_panes = "A5"

D = [
    ("D-01", "SUPERSEDED at the v0.2 review - the demand chart stacks by individual project.",
     "You asked for per-project bands, so that is what the chart does: ordered by total resource with "
     "the largest on the baseline, 'Others' grey.", "Accept", "Stands. No change."),
    ("D-06", "[CHANGED] SUPERSEDED by your own O-10 - the timeline now colours bands by PERIOD NAME.",
     "D-06 said the timeline shades by weight, because weight is what drives the simulation and naming "
     "periods by colour would spend the palette on labels already in the tooltip. You accepted that, and "
     "then asked in O-10 for exactly the opposite - grey, red, green, orange, dark grey by period.",
     "Accept (conflicts with O-10)",
     "O-10 wins: it is the more specific instruction and the clearer statement of what you want to see. "
     "But D-06's point was real, so weight was not thrown away - it rides as a lightness step inside each "
     "period's hue, deliberately over a narrow range so it never competes with the hue, and it stays exact "
     "in the tooltip. If you did mean to keep weight as the colour, mark this Rework and O-10.2 goes back."),
    ("D-11", "[CHANGED] Beyond seven projects, colour comes from an EXTENDED palette, not the validated one.",
     "The validated set caps at eight hues; per-project colour needs ~50, so the seven validated hues are "
     "stepped in lightness. Hue alone no longer identifies a band.", "Accept",
     "Stands, but its safety net changed. D-11 said identity came from 'the legend order, the tooltip and "
     "the table below'. O-06 removed the legend, so the tooltip now carries it alone - which is the stronger "
     "half of that pair anyway, since it names one band rather than asking you to match a hue against 62."),
    ("D-12", "The project table samples the head of each type rather than listing a flat top-14.",
     "Your sort puts all 34 NewDrug CT projects first, so a flat top-14 would never reach the other types "
     "and the ordering could not be seen working.", "Accept", "Stands. No change."),
    ("D-13", "The global filter bar is not sticky.",
     "A sticky bar 110px tall covered panel headings as soon as the page scrolled.", "Accept",
     "Stands. No change."),
    ("D-02", "The project table lists the ten busiest projects plus an aggregate row.",
     "62 rows x 12 months does not fit on screen; the real table lists all 62 with sort and filter.",
     "Accept", "Stands. No change."),
    ("D-03", "Heat shading in the tables is one blue ramp, light to dark.",
     "Magnitude is a sequential quantity, so it takes one hue. The aggregate row is deliberately not shaded.",
     "Accept", "Stands, and now also carries the period-weight matrix on the new tab, so the same ramp "
     "means the same thing everywhere."),
    ("D-04", "Over- and under-allocation carry an icon and a value, never colour alone.",
     "Red-green colour blindness affects around 8% of men; a cell that says only 'red' is unreadable to "
     "them and unprintable in mono.", "Accept",
     "Stands, and it is what shaped the O-10 palette: your red/green pair is exactly the collapse this "
     "decision guards against, so the bands carry text labels and the red sits slightly toward orange."),
    ("D-05", "Both thresholds are drawn on the person chart and the utilisation strip.",
     "A ceiling without a floor makes under-use invisible, and under-use is half of what the tool is for.",
     "Accept", "Stands. No change."),
    ("D-07", "Editing is inline in the tables, not in a separate form or dialog.",
     "A dialog per row would make bulk correction - the common case after a timeline slips - slow enough "
     "that people would go back to editing the workbook by hand.", "Accept",
     "Stands, and extends naturally to X-06: a row is inserted in place, where the user is looking."),
    ("D-08", "The findings banner persists until dismissed rather than fading.",
     "A toast that disappears is a finding nobody read.", "Accept", "Stands. No change."),
    ("D-09", "Dark mode is supported, with its own selected colour steps.",
     "Not a flip of the light palette: the ramp, the categorical hues and the status inks are each "
     "re-stepped for the dark surface.", "Accept",
     "Stands, and it caught a real fault in the new period palette: your 'dark grey' for After Close-out "
     "vanished against the dark surface. Both greys were re-picked to a pair that separates on either "
     "background."),
    ("D-10", "The page is one scrolling column per tab, not a fixed dashboard grid.",
     "It prints, it works on a laptop screen, and it needs no layout engine.", "Accept",
     "Stands, and the fourth tab follows the same pattern."),
    ("D-14", "At the target volume the person chart shows the 20 most loaded people, not all 1,000.",
     "1,000 bars across a 1,200px panel is 1.2px each - narrower than the gap between them.",
     "Accept", "Stands. No change."),
    ("D-15", "Repeated period names are numbered by occurrence, not renamed.",
     "Numbering keeps the source data untouched; renaming in the workbook would break the "
     "PeriodWeightStandard lookup, which is keyed on the period name.", "Accept",
     "Stands. The numbers now appear on the timeline bands as well as in the tables."),
    ("D-16", "[NEW] The two 'Close-out' periods take a light and a deep orange, not one shared orange.",
     "Your mapping gave 'Close-out' a single colour, but a trial with an interim DB lock shows both in "
     "the same row, adjacent to each other. One shared hue made them read as a single interrupted band.",
     "", "Light amber for interim, deep orange for final. Both still read as 'the close-out family', "
         "which is what your mapping intended."),
    ("D-18", "[NEW] The insert control leads each row rather than trailing it.",
     "Placed at the end of the row, '+ row' sat off-screen on the 23-column project table and needed a "
     "horizontal scroll every time. Leading, it is always in view and reads as a row-action gutter.",
     "", "Applies to every editable table, so the control is in the same place everywhere. Alternative: "
         "trailing but pinned to the viewport edge, which costs a sticky column."),
    ("D-17", "[NEW] Milestone markers sit in their own lane above the bands, not on them.",
     "Inverted triangles drawn on the bands landed on top of the period labels, and on a busy row the "
     "two fought for the same pixels.",
     "", "The markers occupy a thin lane above each row's band. Alternative: draw them on the bands and "
         "drop the in-band labels, which trades one legibility problem for another."),
]
rows = [list(x) + [""] for x in D]
r = table(ws, 4, ["ID", "Decision", "Why", "Your decision", "State after your review", "Confirm"],
          rows, [8, 60, 66, 18, 76, 14], wrap_cols=(2, 3, 5, 6), yellow_col=6, mark_col=2)
dv2 = DataValidation(type="list", formula1='"OK,Rework"', allow_blank=True)
ws.add_data_validation(dv2)
dv2.add(f"F5:F{4 + len(rows)}")

# ---- deferred ------------------------------------------------------------
ws = wb.create_sheet("03_Deferred")
ws.sheet_view.showGridLines = False
ws["A1"] = "Deliberately not in the prototype"
ws["A1"].font = TITLE_F
ws["A2"] = "So their absence is not read as an oversight."
ws["A2"].font = NOTE_F
rows = [
    ["Any loading, calculation, filtering or export behaviour", "Task 3.1 is design only. The figures shown "
     "are a fixed snapshot computed in Python and baked into the markup. The controls are real controls; "
     "nothing is wired behind them."],
    ["Exact spacing, type scale and final colour values", "Fixed at task 3.3, once the components are agreed. "
     "The period hues are the exception - they now carry meaning, so they were settled here."],
    ["Keyboard shortcuts and full accessibility pass", "Reviewed against the working prototype at task 3.3, "
     "where they can be tried rather than described."],
    ["Row virtualisation at the target volume", "Specified (X-04, REQ-DSH-09) but not built: the prototype "
     "shows 9 rows of 62, where virtualisation would be invisible. It is a Step 4 concern."],
    ["The validation findings report itself", "Specified on sheet 04 of the specification; the banner that "
     "opens it is in the prototype."],
    ["NO LONGER DEFERRED - hover tooltips", "v0.3 deferred the tooltip layer to code generation. O-06 and "
     "O-10 both depend on it, so it is built and reviewable now (X-05)."],
]
r = table(ws, 4, ["Not shown", "Why"], rows, [56, 100], wrap_cols=(1, 2))

# ---- what the review changed elsewhere -----------------------------------
ws = wb.create_sheet("04_Change_Log")
ws.sheet_view.showGridLines = False
ws["A1"] = "What your review changed outside this document"
ws["A1"].font = TITLE_F
ws["A2"] = ("Two components could not be satisfied by design alone - they asked for behaviour the plan "
            "did not require. Those became requirements.")
ws["A2"].font = NOTE_F
rows = [
    ["REQ-DSH-11", "NEW", "G-07",
     "The application presents the standing assumptions - standard period weights, role factors, "
     "configuration and value lists - on their own tab, without the user opening the workbook.",
     "Must", "Plan v1.6, change R-09"],
    ["REQ-IMP-11", "NEW", "P-01, S-01",
     "A new row can be inserted into any editable table, immediately below the row the user acts on, "
     "and is validated on entry like any other edit.",
     "Must", "Plan v1.6, change R-09"],
    ["REQ-DSH-05", "REWORDED", "O-03",
     "The filter set now names clinical phase, and no longer implies the display unit is a filter.",
     "Must", "Plan v1.6, change R-09"],
    ["REQ-IMP-05", "REWORDED", "G-02",
     "The loaded-file stamp carries its time zone.",
     "Should", "Plan v1.6, change R-09"],
    ["Specification sheet 06", "UPDATED", "all nine",
     "Tab 4 specified; filter set, load stamp, insert-row behaviour, timeline colour rule, tooltip "
     "content and edit-counter wording all restated.",
     "-", "Specification v0.5"],
    ["Design decision D-06", "SUPERSEDED", "O-10",
     "Timeline colour moves from weight to period name; weight becomes a lightness step within the hue.",
     "-", "Sheet 02 of this document"],
]
r = table(ws, 4, ["Item", "Change", "Raised by", "What it says now", "Priority", "Carried in"],
          rows, [22, 14, 16, 88, 10, 26], wrap_cols=(4,))
r = ws.max_row + 2
ws.cell(r, 1, "Nothing else in the plan or specification moved. Everything else you asked for was a "
              "design change the existing requirements already permitted.").font = NOTE_F

wb.save(OUT)
print(f"Written: {OUT}  ({len(C)} components, {len(D)} decisions)")
