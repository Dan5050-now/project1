"""Generate the UI component list - what the application is made of, screen by screen.

From v0.4 this was a disposition document as well as a review form: it carries the
reviewer's own words against each component, what was done about them, and what is
left. The review trail lives in the deliverable rather than in a chat log.

v2.0 RE-OPENS A DOCUMENT THAT WAS APPROVED, and the reason is worth stating at the top.
v1.0 closed the Step 3 gate on 2026-08-02 against plan v2.0. Thirty-four change requests
later - R-13 to R-46, plan v2.54 - the application had gained about twenty screen
elements this list had never heard of, and five of its existing entries had quietly
become WRONG: they described behaviour the application no longer has.

It drifted for a mechanical reason, not a careless one. tools/check_consistency.py holds
the plan, the specification, the template, the dummies and the machine-readable contract
to each other on every build. This document was not in that set, so it was the one
artefact nothing checked, and it fell behind in silence while everything else was kept
in step automatically.

The v1.0 review trail is preserved exactly as it was - the reviewer's words, the
decisions, what was done. Nothing there is rewritten. Corrections are marked [FIXED v2.0]
and say what the entry used to claim; additions are marked [NEW v2.0] and name the change
request that introduced them.

v2.1 CLOSES THE ONE ITEM v2.0 LEFT OPEN. X-04, row virtualisation, was recorded as NOT
IMPLEMENTED against a requirement naming 1,000 people and needed a decision. It was
measured at six volumes rather than argued about; REQ-NFR-03 was amended to 100 projects
and 150 people (R-47), which is the largest volume whose worst case is still inside the
rendering budget; so X-04 is now NOT BUILT AND NOT REQUIRED, with its figures. Marked
[FIXED v2.1].

    python tools/build_component_list.py

Output: docs/PRAP_UI_Component_List_v2.2.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

VERSION = "2.2"
DATE = "2026-09-13"
PROTOTYPE = "app/PRAP.html"
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
ws["A2"] = "Step 3, task 3.1 — APPROVED by Dan, 2026-08-02. Step 3 gate closed."
ws["A2"].font = NOTE_F
meta = [("Version", f"v{VERSION}"), ("Date", DATE), ("Author", "Claude Code"),
        ("Reviewer", "Dan — v0.3, v0.4 and v0.5 reviewed 2026-08-01 to 08-02"),
        ("Prototype", PROTOTYPE),
        ("Governing plan", "PRAP_Development_Plan_v2.0.xlsx (APPROVED BASELINE)"),
        ("Specification", "PRAP_Programming_Specification_v1.0.xlsx (APPROVED)")]
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
    "ROUND 3 (this issue) applied three further items you raised, listed in full on sheet 05:",
    "the role factor is now keyed on role AND project type AND clinical phase AND period; every table",
    "on the three data tabs scrolls inside its own panel; and the insert buttons missing from the",
    "assumptions tab are fixed. You were right about the last one, and it was worse than reported -",
    "the role-factor table had an 'insert' HEADER with no cells beneath it, so that table was a column",
    "out of alignment, and the value-lists table had buttons it should never have had.",
    "",
    "ROUND 4 (this issue) is on sheet 06. You named the two conduct stretches apart -",
    "'Conduct (interim)' and 'Conduct (final)' - which makes period_name unique in a project and",
    "gives ProjectPeriod a natural key again. That is the alternative D-15 offered and was not taken",
    "at the time, so D-15 is now SUPERSEDED. It also retires the need for the display numbering that",
    "REQ-DSH-10 introduced: the requirement is satisfied by the data model instead.",
    "",
    "ROUND 6 (this issue) is on sheet 08. You confirmed all 13 changed components and all 7 changed",
    "decisions as OK - nothing was marked Rework - and added two requests, both applied: the DB lock",
    "milestones are emphasised on the timeline, and the project tab gains a utilisation graph with",
    "relative reference lines. The second needed a new requirement, REQ-DSH-12, for the reason you",
    "gave: a project has no static threshold, so the person tab's model does not transfer.",
    "",
    "Rows already confirmed carry 'OK (v0.7)' in the Confirm column, so a blank cell means an item",
    "that is new this round rather than one nobody has looked at.",
    "",
    "APPROVED by Dan on 2026-08-02, together with development plan v2.0 and programming",
    "specification v1.0. Step 3 is closed and Step 4 - code generation - is authorised.",
    "",
    "The two judgement calls flagged on sheet 08 were approved as made: the '...cut-off' milestones",
    "stay ordinary, and the portfolio average covers active project-months only. Both are recorded",
    "here so a later reader knows they were decided rather than defaulted.",
]:
    ws.cell(r, 1, line).font = BODY_F
    r += 1

# ---- components ----------------------------------------------------------
ws = wb.create_sheet("01_Components")
ws.sheet_view.showGridLines = False
ws["A1"] = "Component list — your decisions and what was done"
ws["A1"].font = TITLE_F
SUBTITLE_CELL = ws["A2"]          # filled once the component list below is defined
ws["A2"].font = NOTE_F
ws.freeze_panes = "A5"

# Confirmed OK at the v0.7 review. Recorded here so the trail lives in the document:
# a blank column would read as "not yet looked at" a round later.
CONFIRMED = {"G-02", "G-06", "G-07", "O-03", "O-04", "O-06", "O-10", "P-01", "S-01",
             "X-01", "X-03", "A-02", "A-04",
             "D-06", "D-11", "D-15", "D-16", "D-17", "D-18", "D-19"}

K = "Keep"
A = "Added after approval"
FIX = "[FIXED v2.0] "
FIX21 = "[FIXED v2.1] "
FIX22 = "[CHANGED v2.2] "
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
    ("G-04", "Global", "Export", "Writes all ELEVEN sheets back in template layout, edits included. " + FIX
     + "v1.0 said ten; MonthlyEstimate arrived at R-30 (schema 9) and is written too.",
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
     "Projects, people, total demand, over-allocated months, under-allocation runs, "
     "and months off their own standard. " + FIX + "v1.0 said five tiles; R-42 added the "
     "sixth, 'Off their standard', which jumps to the Standard vs staffed panel.",
     "REQ-DSH-08", K, "", "Unchanged."),
    ("O-06", "Overall", "[CHANGED] Demand chart",
     "Stacked monthly demand, one band per project, largest on the baseline. THIS chart still "
     "has no legend and answers by hover, exactly as you asked. " + FIX + "v1.0's flat 'No "
     "legend' is no longer true of the application: five other charts DO carry one, and since "
     "R-45 a legend entry is clickable - it picks that series out across the whole tab. Your "
     "instruction was about this chart and it still holds here.",
     "REQ-DSH-02", "Change",
     "In 'Monthly demand by project' section, remove legend information on the bottom. Instead, while "
     "hovering over each stack in the graph, provide pop-up information (e.g. project name, project's "
     "month FTE, acting people in the months).",
     "Done. The legend is gone and a real hover pop-up replaces it, carrying project name and type, "
     "that month's FTE and its hour equivalent, the headcount, and every person on the project that "
     "month with their role. Note the knock-on: D-11 argued that identity came from the legend order "
     "because 62 hues cannot be told apart. The tooltip now carries that alone - which is stronger, "
     "since it names one band rather than asking you to match a colour against a list of 62."),
    ("O-07", "Overall", FIX22 + "Resource by project (table)",
     "Project x month heatmap. Sorted NewDrug CT, Biosimilar CT, Others, then earliest first. "
     + FIX22 + "SINCE R-49 A MONTH INSIDE THE PROJECT'S RUN WITH NOBODY ON IT CARRIES THE "
     "FIGURE ITS STANDARD ASKS FOR, not a dot. A dot was a statement and it was the wrong one: "
     "it says the month costs nothing, when what it costs is exactly what the standard for its "
     "type, phase, scope and period says. Drawn as DEMAND and never as resource - no filled "
     "sequential scale, an outline and a hatch, italic, and a hollow ring glyph so the "
     "difference is not carried by colour alone (D-04) - and never added to the row, column or "
     "grand total, which stay the APPLIED figure so this table still reconciles with O-09. The "
     "unallocated is totalled on a line of its own and beside each project's applied total. "
     "Filled only where the calculation produced no figure at all, so nothing existing moves.",
     "REQ-DSH-01, REQ-DSH-17", "Change (R-49)",
     "Yes, proceed to the built.",
     "Done. The figure was computable from the moment the periods existed - REQ-CAL-19 says the "
     "project-month IS its standard and the people on it divide it, so a divisor of nobody does "
     "not make it nought. Demand is now a property of the project-month, from one function "
     "shared with V-36 so the screen cannot contradict the finding beside it. The charts and "
     "the results export are deliberately NOT changed: a stacked bar mixing allocated and "
     "unallocated bands would misstate its own total, and REQ-OUT-06 promises every exported "
     "monthly figure is the sum of its detail rows, which unallocated demand has none of."),
    ("O-07b", "Overall", "Project row expansion",
     "Clicking a project name reveals a row per person and role, each with its own monthly figures.",
     "REQ-DSH-01", K, "", "Unchanged."),
    ("O-08", "Overall", "[FIXED v2.0] Monthly demand by person (chart)",
     "A STACKED chart, one band per person per month, the 20 most loaded shown individually "
     "and the rest folded into one band. It totals the same figure every month as 'Monthly "
     "demand by project' - the same person-months summed the other way. A segment is outlined "
     "where that person's own month crosses the ceiling or the floor. " + FIX + "v1.0 described "
     "a bar chart of MEAN load per person and recorded it 'Keep - unchanged'. No such chart "
     "exists: it was replaced by this one, which answers 'what is this month made of' rather "
     "than 'what does this person average'.",
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
    ("P-06", "Project tab", "[NEW] Project utilisation graph",
     "The selected project's monthly resource across the horizon, against three relative reference "
     "lines. Sits directly under the project table.",
     "REQ-DSH-12", "Add (round 6)",
     "In 'Source Data (project)', add 'Utilisation' graph for projects specific monthly resource with "
     "bars (upper: 2 times x average of all projects FTE, lower: 0.5 times x average of all projects, "
     "additional: the project's average FTE during entire period). The graph location is next to the "
     "'Project' table.",
     "Added, with your three lines exactly as specified. Your reasoning is what made it a new "
     "requirement rather than a copy of the person strip: a project has no static threshold, so the "
     "person tab's absolute ceiling and floor do not transfer. Hence REQ-DSH-12. One judgement call to "
     "flag - the portfolio average is taken over ACTIVE project-months only. Including months where a "
     "project draws nothing would pull the average toward zero and make every running project look "
     "heavy against it. Say if you meant the simple mean across all months instead."),

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

    ("X-01", "Layout", "[CHANGED] Scroll regions",
     "Every chart and table scrolls inside its own panel - horizontally when wide, and within a bounded "
     "height when tall, with the header row staying visible.",
     "REQ-NFR-02", "Change (round 3)",
     "Apply scroll bar on the bottom of all sections of 'Source data (project)'/'Source data (person)'/"
     "'General assumptions'. Some sections have problems that table size over the fixed section site. "
     "(e.g. Periods of 'Source data (project)', Assignments and Weight overrides of 'Source data (person)')",
     "Done. Six tables were rendering outside their panels: the milestone and period sub-tables, "
     "assignments, weight overrides, and both assumptions tables. Each now sits in a scroll region that "
     "is bounded in BOTH directions - the earlier rule only covered width, which is why a long "
     "sub-table still grew the page and pushed the panels below it down. Verified by measuring the "
     "document's scroll width against the viewport: they match, so nothing overflows sideways."),
    ("X-02", "Layout", "Type and phase pills",
     "Project type and clinical phase as labelled pills; text carries the meaning, colour only speeds recognition.",
     "REQ-PRJ-01, REQ-PRJ-09", K, "", "Unchanged."),
    ("X-03", "Layout", "[CHANGED] Numbered repeated periods — now a guard only",
     "Retained, but it never fires: since R-11 no period name repeats, so a name alone identifies a "
     "period on screen.",
     "REQ-DSH-10", "Change (round 4)",
     "Change period name for conduct as 'Conduct (interim)' and 'Conduct (final)' in order to "
     "distinguish multiple periods.",
     "Done - see sheet 06. This component is what REQ-DSH-10 asked for, and your change satisfies that "
     "requirement structurally instead. The numbering code is kept as a guard: V-18 now rejects a "
     "repeated name on import, but a hand-built model could still reach the renderer, and a silent "
     "collision there would be worse than a redundant ten lines."),
    ("X-04", "Layout", FIX21 + "Row virtualisation — not built, and not required",
     "NOT BUILT, AND SINCE R-47 NOT REQUIRED. Both Overall tables render EVERY row, and "
     "at the volume REQ-NFR-03 now names that is the right build. "
     "THIS ENTRY HAS BEEN WRONG TWICE AND IS NOW A DECISION. v1.0 recorded it 'Keep - "
     "unchanged', which reads as built; it never was, and there is no virtualisation "
     "anywhere in src/. v2.0 corrected that to NOT IMPLEMENTED, which made it an open "
     "defect against a requirement naming 1,000 people. v2.1 records what was decided "
     "once both volumes had been measured. "
     "WHAT WAS MEASURED (tools/build_stress_workbook.py builds a fixture at any "
     "--projects / --people; tools/measure_scale.py drives it). Switching to the Overall "
     "tab, 60-month horizon, against a 1,000 ms budget fixed before any number was seen: "
     "50 x 100 529 ms (53% of budget, worst case 571) | 100 x 100 689 ms (69%, 746) | "
     "100 x 150 810 ms (81%, 894) | 100 x 200 981 ms (98%, 1,225) | 50 x 400 1,044 ms "
     "(104%) | 100 x 1,000 3,058 ms (306%, worst 4,537, drawing 67,222 cells in 1,102 "
     "rows). "
     "REQ-NFR-03 WAS AMENDED TO 100 x 150 - the largest volume whose WORST case is still "
     "inside budget - so the cost this component exists to remove is 810 ms against a "
     "1,000 ms budget, and removing it would change no number a user feels. "
     "THE BINDING QUANTITY IS ROWS, AND ROWS IS PROJECTS PLUS PEOPLE. Both Overall tables "
     "sit on one tab, so 50 x 200 and 100 x 150 are the same 252 rows and measure within "
     "10 ms of each other. Anyone re-measuring this should vary the row count and the "
     "horizon together; the project count alone answers nothing. "
     "WHAT VIRTUALISATION WOULD NOT HAVE FIXED, had it been built for 1,000 people. The "
     "import at that volume is 7,328 ms against a 5,000 ms budget and 3,076 ms of it is "
     "the CALCULATION alone - 180,160 person-months. Virtualisation touches neither the "
     "calculation nor the workbook parse, so it answers the tab and about half the "
     "import: that volume was never one component away from working. Editing (98 ms) and "
     "filtering (49 ms) are inside budget even there. "
     "IF IT IS EVER NEEDED: the visible window plus a small overscan, row height fixed so "
     "the scrollbar stays truthful. It is cheap to add later because the property that "
     "would conflict with it is already a requirement - sorting, filtering and totals run "
     "over the whole model, never over the drawn slice (REQ-DSH-09).",
     "REQ-DSH-09, REQ-NFR-03", "Change (R-47)",
     "제안대로 측정부터 해줘  [measure first, as proposed]   ...   "
     "중간값으로 개정해줘  [revise to a middle value]",
     "Done, in that order - and the order mattered. Measured at six volumes first, then "
     "the middle value was chosen FROM the measurements rather than picked and checked "
     "afterwards: the candidates offered were 200 to 400 people, and measurement showed "
     "both of those over budget, so the achievable middle is 150. REQ-NFR-03 moved and the "
     "code did not. Recorded with its figures so a later reader can act on the decision "
     "instead of re-deriving it."),

    ("A-01", "Assumptions tab", "[FIXED v2.0] Standard period FTE for project types",
     "PeriodFTEStandard as a matrix - type and phase down the side, period across, shaded by "
     "magnitude. " + FIX + "v1.0 called this 'Standard period weights' and named the sheet "
     "PeriodWeightStandard. Both were renamed at R-33: the column holds a monthly FTE, a MAGNITUDE, "
     "and calling it a weight is most of why it went unused - a weight reads like something to "
     "multiply by. Caught by the new component check in check_consistency.py, not by reading.",
     "REQ-DSH-11", "", "",
     "Added for G-07. Shown as a matrix, not 48 flat rows: it is a standard, and a standard is read "
     "across. 'Others' projects are absent by design - their weights are hand-entered per project."),
    ("A-02", "Assumptions tab", "[CHANGED] Role factors — clinical trials",
     "RoleFactor as a matrix: type + phase + role down the side, the six periods across.",
     "REQ-DSH-11", "Change (round 3)",
     "Weight of Role factors should be given by Role & Project type & Clinical phase & Periods.",
     "Done - see sheet 05. The key is now all four columns and the sheet grows from 13 rows to 249, so "
     "it is shown as a matrix: 40 rows of six periods each. Reading a role ACROSS the periods is the "
     "point of the change - the database programmer peaks at start-up, the analyst at lock. Also fixed "
     "here: this table had an 'insert' header with no cells beneath it, so every row was a column out "
     "of alignment. It is a reference matrix now, and reference matrices carry no insert control."),
    ("A-02b", "Assumptions tab", "[NEW] Role factors — Others",
     "The same matrix for non-trial projects: role down the side, the three 'Others' periods across.",
     "REQ-DSH-11", "", "",
     "Split out because 'Others' projects carry no clinical phase and run a different period set, so "
     "they cannot share a matrix with the trials without a column of blanks."),
    ("A-03", "Assumptions tab", "[NEW] Configuration",
     "Config: thresholds and settings, plus the display-unit control moved here from the filter bar.",
     "REQ-DSH-11, REQ-CAL-08", "", "",
     "Added for G-07 and O-04. The thresholds that colour the tables now sit next to a note saying "
     "what they mean."),
    ("A-04", "Assumptions tab", "[CHANGED] Value lists",
     "Lists: what each list-typed column will accept, and how many values each list holds. Read-only.",
     "REQ-DSH-11", "Change (round 3)",
     "Insert row button ... Check all tables of the 'General assumptions'.",
     "Fixed. This table had insert BUTTONS it should never have had - the header carried no insert "
     "column, so it too was out of alignment, the opposite way round from A-02. It is now explicitly "
     "read-only: a value added here with nothing referring to it is noise, and the note says so."),
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
    # ---------------------------------------------------------------- added since v1.0
    # Every row below names the change request that introduced it. The decision column
    # says 'Added after approval' rather than 'Keep' or 'Change', because none of these
    # was in front of the reviewer at the Step 3 gate - saying otherwise would falsify
    # a review trail that is otherwise exact.
    ("O-11", "Overall", "[NEW v2.0] Monthly resource trend / Monthly load trend (line chart)",
     "One line per project on a shared baseline, capped at the 12 largest by total. The person "
     "tab carries the same component under the title 'Monthly load trend', one line per person "
     "with the over-allocation ceiling drawn. A stack "
     "answers 'what is this month made of'; only lines answer 'is this one rising or falling', "
     "because in a stack every band's baseline moves with the bands beneath it. Hover gives "
     "the line's total, mean and peak month.",
     "REQ-DSH-02", A, "", "R-38. First panel on Overall, and on both source-data tabs."),
    ("O-12", "Overall", "[NEW v2.0] Standard vs staffed (panel)",
     "Every month where a project is not being given what its own standard asks for: what it "
     "needs, what it is getting, and the gap. Both directions are counted APART and never "
     "netted off - short of the standard and over it are different facts. Sits second, "
     "directly under the trend it explains, and always in the same place: a panel that "
     "appears only when there is something to say is one nobody learns the position of.",
     "REQ-DSH-15, V-34", A, "", "R-42."),
    ("O-13", "Overall", "[NEW v2.0] Month detail dialog (from the gap panel)",
     "Opens the month itself: the project figure, every assigned person's stated figure, and "
     "the calculated one beside it. EVERY STATED CELL IS EDITABLE HERE, including for somebody "
     "still on automatic - for whom the application first asks, because switching seeds every "
     "other month and a lone row would be a figure nothing reads.",
     "REQ-DSH-15, REQ-CAL-18", A, "", "R-42, extended by R-43."),
    ("P-07", "Project tab", "[NEW v2.0] Monthly estimation (project level)",
     "The months of a project whose FTE is STATED rather than calculated, with the automatic "
     "figure and the difference beside each one, and a derivation column carrying the whole "
     "expression term by term. Switching to manual is a button, not a cell: it copies every "
     "calculated month across first, so nothing jumps.",
     "REQ-CAL-18, REQ-DSH-14", A, "", "R-30, R-40, R-41."),
    ("S-06", "Person tab", "[NEW v2.0] Monthly estimation (assignment level)",
     "The same panel for one assignment, with two columns the project's does not have: the "
     "sharer count, and a second derivation line giving this person's CLAIM on the month - "
     "role factor / sharers x person weight x coverage, ending in the percentage of the "
     "month it won. It states the assignment it belongs to under its title.",
     "REQ-CAL-18, REQ-DSH-14, REQ-DSH-16", A, "", "R-30, R-40, R-41, R-45."),
    ("S-07", "Person tab", "[NEW v2.0] Switch-estimation dialog",
     "Asked in both directions, because both lose something: switching to manual stops the "
     "assumptions reaching these months, and switching back DELETES every stated figure. "
     "Names how many months are affected before it does anything.",
     "REQ-CAL-18", A, "", "R-30."),
    ("E-04", "Editing", "[NEW v2.0] Calendar panel on date cells",
     "A month opens beside the cell being edited, on that cell's own month. The cell never "
     "stops accepting keys - what you type moves the calendar. Today, and the month and year "
     "arrows, all step repeatedly rather than snapping back to the cell's own month.",
     "REQ-IMP-12", A, "", "R-21, both faults fixed at R-35."),
    ("E-05", "Editing", "[NEW v2.0] Column filters",
     "A funnel on each heading of the six wide tables, filtering by value the way a "
     "spreadsheet does. Filters on different columns narrow together. A row still being "
     "typed is never filtered out, and the count of what is hidden is stated above the table.",
     "REQ-DSH-03, REQ-DSH-04", A, "", "R-36."),
    ("E-06", "Editing", "[NEW v2.0] Change log",
     "Every edit is recorded in memory with the sheet, the row, the column, the value before "
     "and after, and who made it. Archived to a shared folder on Save. It is NOT shown in the "
     "application and cannot be exported from it - the archive is the record.",
     "REQ-IMP-09", A, "", "R-36, narrowed at R-38 and R-39."),
    ("G-09", "Global", "[NEW v2.0] Identity prompt",
     "Who is editing. Asked once in the browser; taken from the Windows account in the desktop "
     "edition without asking. DECLARED, never verified - there is no authentication anywhere "
     "in this application, and the change log says so rather than implying otherwise.",
     "REQ-IMP-09, NR-USR-08", A, "", "R-36."),
    ("G-10", "Global", "[NEW v2.0] Settings-change notice on import",
     "A file whose Config differs from the settings in force says so on the banner, and lists "
     "each setting with what it WAS, what it is now, and what it affects. A threshold that "
     "moved under a plan is otherwise invisible.",
     "REQ-IMP-14", A, "", "R-28."),
    ("G-11", "Global", "[NEW v2.0] Results export",
     "The calculated monthly FTE, not just the source plan: every person-month with the terms "
     "behind it. Clearly marked as NOT a source workbook and not importable - a results file "
     "that pretends to be source data invites somebody to edit a derived column.",
     "REQ-OUT-06", A, "", "R-29."),
    ("X-07", "Layout", "[NEW v2.0] Lookup columns",
     "Where a figure's size was decided somewhere else, the table showing the figure names "
     "what decided it, in a column that is looked up and cannot be edited: the standard a "
     "period selects, the whole derivation of a month term by term, and the sharer count. "
     "Never stored on the sheet, so no save can leave a stale copy of a standard in a file.",
     "REQ-DSH-14", A, "", "R-40, extended at R-41."),
    ("X-08", "Layout", "[NEW v2.0] Legend picking",
     "Clicking a legend entry fades back everything that is not that series; a second click, "
     "another entry, or Escape brings it home. The pick applies to the WHOLE TAB, because the "
     "same project is the same id on every chart that knows it. A chart cut along a different "
     "axis is left alone rather than dimmed to nothing. Marks belonging to the MONTH - "
     "thresholds, baselines, the V-34 outline - never fade. Keyboard-operable.",
     "REQ-DSH-16", A, "", "R-45."),
    ("X-09", "Layout", "[NEW v2.0] Headings say what the column means",
     "Each heading shows a plain name - 'Share of this person', not person_weight. The "
     "workbook's own column name is in the heading's pop-up and on the element, not printed "
     "on the page: it is wanted occasionally and the heading is read on every glance. Nothing "
     "is renamed; the cell still writes back through the identifier.",
     "REQ-DSH-16", A, "", "R-45, revised at review on the same day."),
    ("X-10", "Layout", "[NEW v2.0] Charts grow with the horizon",
     "A chart whose x axis is the month grid takes its width from the month count and its "
     "panel scrolls sideways past the point where they all fit. A fixed width is legible only "
     "over the span it was chosen for and fails SILENTLY outside it - the chart still draws, "
     "it just stops being readable, on exactly the long plans that most need reading.",
     "REQ-DSH-16", A, "", "R-45."),
    ("X-11", "Layout", "[NEW v2.0] Wide panels take the full width",
     "Two panels share a row only where both are readable in half a screen. Assignments, "
     "Weight overrides and Monthly estimation are stacked, in the order the work is done in: "
     "pick the assignment, then its override windows, then its months.",
     "REQ-DSH-16", A, "", "R-45."),
    ("X-12", "Layout", "[NEW v2.0] A child panel names its parent",
     "A panel that is a child of a selection states the selected row under its title - the id, "
     "the project, the role, the window and the weight. From ONE helper shared by every panel "
     "that names the same thing, so two statements of it cannot drift apart.",
     "REQ-DSH-16", A, "", "R-45."),
    ("P-08", "Project tab", "[NEW v2.0] Period generator that fits the project",
     "A trial is offered 'Auto derivation' from its milestones; an 'Others' project is offered "
     "'Standard periods' instead, which lays out Planning / Develop / Close with the dates "
     "blank. A trial not ready yet keeps the button, greyed, naming the two milestones it needs.",
     "REQ-CAL-10, V-16", A, "", "R-22, replacing the single button P-04 described."),
    ("G-12", "Global", "[NEW v2.0] Findings carry a class",
     "What a rule is ALLOWED to do is a property of the rule, separate from how bad it is: "
     "'must' refuses the edit, 'conditional' asks at Save and lists what will be left "
     "unresolved, 'incomplete' reports only. A warning never gates an edit.",
     "REQ-IMP-13", A, "", "R-25."),
    ("X-13", "Layout", "[NEW v2.0] The application draws its own scroll bars",
     "A bounded region is only honest if the reader can SEE there is more and reach it, and "
     "the browser's overlay bar does not do that - it takes no layout space and fades when "
     "idle. Drawn bars are always there while there is anywhere to go, and can be dragged. "
     "The two bars settle against each other before either is drawn, because each costs the "
     "region space and one can be what pushes the content past the other edge.",
     "REQ-DSH-13", A, "", "R-23; the settling fix at R-45."),
    ("G-13", "Global", "[NEW v2.0] Start with no file",
     "The application opens without a workbook and seeds the delivered defaults - value "
     "lists, settings, standard period weights and role factors - so a plan can be entered "
     "from nothing. Saving writes a workbook in the current template layout.",
     "REQ-IMP-03", A, "", "R-14."),
]
# Derived, not typed: the counts have gone stale twice already.
SUBTITLE_CELL.value = (
    f"{len(C)} components. {sum(1 for c in C if c[5] == K)} Keep, "
    f"{sum(1 for c in C if str(c[5]).startswith('Change'))} Change (amber), "
    f"{sum(1 for c in C if '[NEW]' in c[2])} added by those changes (green). "
    f"Your comments are quoted exactly as written.")
rows = [list(c) + ["OK (v0.7)" if c[0] in CONFIRMED else ""] for c in C]
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
    ("D-15", "[CHANGED] SUPERSEDED — the conduct stretches are RENAMED, not numbered.",
     "D-15 argued for numbering because renaming would break the PeriodWeightStandard lookup, which is "
     "keyed on the period name. Its stated alternative was to label them by what separates them - "
     "'Conduct (pre-interim)' and 'Conduct (post-interim)'. You took that alternative in round 4.",
     "Accept, then superseded",
     "The objection was answered rather than ignored: the lookup does not break because the new names "
     "were added to the standard period set, so PeriodWeightStandard and RoleFactor are keyed on them "
     "like any other period. The cost is the one D-15 named - the set grows from six names to seven, and "
     "both weight tables grow with it. The gain is larger: period_name is unique within a project, so "
     "ProjectPeriod has a natural key and the display numbering is no longer needed at all."),
    ("D-16", "[NEW] The two 'Close-out' periods take a light and a deep orange, not one shared orange.",
     "Your mapping gave 'Close-out' a single colour, but a trial with an interim DB lock shows both in "
     "the same row, adjacent to each other. One shared hue made them read as a single interrupted band.",
     "", "Light amber for interim, deep orange for final. Both still read as 'the close-out family', "
         "which is what your mapping intended."),
    ("D-20", "[NEW] The two DB locks are drawn in red and larger; the '...cut-off' milestones are not.",
     "You asked for the interim and final DB locks to stand out because they matter more than the other "
     "milestones. They do, and specifically: they are what the whole period derivation hangs on - move a "
     "lock and every period after it moves with it. Nothing else on the timeline has that reach.",
     "", "Applied. Red plus a larger marker, so size carries the emphasis as well as hue - D-04, which "
         "you accepted, makes 'never colour alone' a floor for this UI. The markers sit in their own "
         "lane above the bands (D-17), so red reads cleanly there and does not collide with the red "
         "Start-up band. Judgement call to flag: 'interim DB lock cut-off' and 'final DB lock cut-off' "
         "are LEFT ordinary. The cut-off is preparation; the lock is the event that moves the timeline. "
         "Say if you want the cut-offs emphasised too."),
    ("D-21", "[NEW] The project utilisation graph uses RELATIVE reference lines, not thresholds.",
     "Your own reasoning: a project has no static threshold for over-burden or under-resource. So the "
     "lines are 2x and 0.5x the portfolio average, plus the project's own lifetime average - three "
     "reference points rather than two limits.",
     "", "Applied as specified, and it is why this needed a new requirement (REQ-DSH-12) rather than "
         "reusing the person strip. One consequence worth stating: because the lines move as the "
         "portfolio changes, a bar that is 'above the line' this month can fall below it next month "
         "with no change to the project itself. That is correct behaviour for a relative measure, but "
         "it means the graph answers 'heavy compared to what we usually run' rather than 'over "
         "budget'. The caption says so, because a dashed line above a bar reads as a limit unless it "
         "is labelled otherwise."),
    ("D-19", "[NEW] PeriodWeightStandard and RoleFactor are kept as two tables, not collapsed into one.",
     "Keying the role factor on phase and period means both tables now vary over (type, phase, period), "
     "and the calculation multiplies them - so they are mathematically collapsible into a single table "
     "keyed on all four columns. They are kept apart because they answer different questions: one is "
     "how busy the PROJECT is in a period, the other how much of that falls on a ROLE.",
     "", "Kept separate. But the separation is a maintenance convention, not something the arithmetic "
         "enforces: raising a project's Conduct load by editing all five role rows gives the right answer "
         "today and double-counts the next time the period weight moves. If that distinction is not kept "
         "in practice, the honest fix is to collapse them - a schema change, so flagged rather than done."),
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
rows = [list(x) + ["OK (v0.7)" if x[0] in CONFIRMED else ""] for x in D]
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

# ---- round 3 ------------------------------------------------------------
ws = wb.create_sheet("05_Round3")
ws.sheet_view.showGridLines = False
ws["A1"] = "Review round 3 — three items"
ws["A1"].font = TITLE_F
ws["A2"] = "Raised after prototype v0.4. All three applied in v0.5."
ws["A2"].font = NOTE_F
rows = [
    ["1", "Data model",
     "Weight of Role factors should be given by Role & Project type & Clinical phase & Periods. Update all "
     "relevant outputs (plan, specification, sourcedata template, dummy test sourcedata file, prototype, "
     "UI_Component_List).",
     "Applied as plan change R-10, and it is a genuine gain: a role's burden is not flat across a project, "
     "and the dummy data now shows the database programmer peaking at start-up and the analyst at lock. "
     "RoleFactor gains clinical_phase and period_name; the key becomes all four columns; the sheet grows "
     "from 13 rows to 249; schema version steps 3 to 4. Every output listed was regenerated. "
     "TWO COSTS, both stated rather than hidden. (a) 249 rows is a large table to maintain by hand. "
     "(b) RoleFactor now varies over the same three dimensions as PeriodWeightStandard and the two "
     "multiply, so editing both for the same reason double-counts - see D-19 and specification sheet 05. "
     "A new rule, V-23, catches a factor missing for a period an assignment actually spans, which would "
     "otherwise drop that stretch silently to 1.00.",
     "Plan v1.7 (R-10), spec v0.6, template v1.5, dummy v1.6, prototype v0.5"],
    ["2", "Layout",
     "Apply scroll bar on the bottom of all sections of 'Source data (project)' / 'Source data (person)' / "
     "'General assumptions'. Some sections have problems that table size over the fixed section site. "
     "(e.g. Periods of 'Source data (project)', Assignments and Weight overrides of 'Source data (person)')",
     "Applied. Six tables were rendering outside their panels. The v0.4 rule bounded WIDTH only, which is "
     "why the ones you named still overflowed - Periods is too wide for a half-width panel, Assignments "
     "and Weight overrides are too tall. Each table now sits in a region bounded in both directions, and "
     "keeps its header row visible while scrolled. Checked by measuring the document scroll width against "
     "the viewport width: equal, so nothing overflows sideways.",
     "Prototype v0.5, component X-01, spec v0.6 sheet 06"],
    ["3", "Layout",
     "Insert row button should be added, however only column is added now but no button to add new row is "
     "added under 'Insert' column. It looks like wrong information. Check all tables of the "
     "'General assumptions'.",
     "Fixed, and it was worse than you saw. The role-factor table had an 'insert' HEADER with no cells "
     "beneath it, so every row of that table was a column out of alignment - the note you read as wrong "
     "information was wrong. The value-lists table had the opposite fault: insert buttons with no header. "
     "Both came from one careless edit in v0.4 that moved the control to the front of the row and missed "
     "these two tables. Now: role factors are reference matrices with no insert control at all, value "
     "lists are explicitly read-only, and Config keeps its per-row control.",
     "Prototype v0.5, components A-02, A-02b, A-04"],
]
r = table(ws, 4, ["#", "Area", "What you raised (verbatim)", "What was done", "Carried in"],
          rows, [5, 14, 66, 104, 34], wrap_cols=(3, 4, 5))
r = ws.max_row + 2
ws.cell(r, 1, "Item 3 is the kind of fault a rendered screenshot catches and a code diff does not. The "
              "prototype is now rendered and inspected on every build for exactly that reason.").font = NOTE_F

# ---- round 4 ------------------------------------------------------------
ws = wb.create_sheet("06_Round4")
ws.sheet_view.showGridLines = False
ws["A1"] = "Review round 4 — two items"
ws["A1"].font = TITLE_F
ws["A2"] = "Raised after prototype v0.5. Both applied in v0.6. The second follows from the first."
ws["A2"].font = NOTE_F
rows = [
    ["1", "Data model",
     "Change period name for conduct as 'Conduct (interim)' and 'Conduct (final)' in order to distinguish "
     "multiple periods. Conduct (interim): if the milestone has interim DB lock and is before interim DB "
     "lock then use this period name. Conduct (final): if the milestone is after interim DB lock or the "
     "project has only final DB lock without interim DB lock, use this period name.",
     "Applied as plan change R-11. Your rule maps exactly onto the derivation already in the "
     "specification: the split branch runs only when an interim DB lock exists, so 'Conduct (interim)' is "
     "emitted only there, and every other conduct stretch - including the single one of a project with no "
     "interim lock - is 'Conduct (final)'. The clinical period set grows from six names to seven. "
     "PeriodWeightStandard grows 48 to 56 rows and RoleFactor 249 to 289; both new entries carry the same "
     "weights the single 'Conduct' did, so this RENAMES without reweighting - the dummy dataset returns "
     "189 over-allocated person-months before and after, which is the evidence. Schema 4 to 5: no column "
     "changed, but the period_name value set did, so a v4 file's 'Conduct' rows would now fail V-15.",
     "Plan v1.8 (R-11), spec v0.7, template v1.6, dummy v1.7, prototype v0.6"],
    ["2", "Data model",
     "Change key of ProjectPeriod to 'project_id + period_name' because now the period table has a unique "
     "period name list. Use the changed key to map relative information.",
     "Applied, and this is the payoff of item 1. period_name is now unique within a project, so "
     "(project_id, period_name) is a natural key and period_seq goes back to carrying ORDER rather than "
     "identity. V-18 becomes a plain uniqueness check on the name - proved by renaming one row in a copy "
     "of the dummy file and confirming the error. Three things simplify as a result: the ProjectPeriod key "
     "loses period_start, which was only ever there to tell two identically-named rows apart; decision "
     "D-15 is superseded; and REQ-DSH-10's display numbering becomes unnecessary, since a name alone now "
     "identifies a period on screen. The numbering code is kept as a guard, not as the mechanism.",
     "Plan v1.8 (R-11), spec v0.7 sheets 03 and 04, component X-03, decision D-15"],
]
r = table(ws, 4, ["#", "Area", "What you raised (verbatim)", "What was done", "Carried in"],
          rows, [5, 14, 66, 104, 34], wrap_cols=(3, 4, 5))
r = ws.max_row + 2
ws.cell(r, 1, "A note on what this change is worth: the previous design carried the repeated name through "
              "four places - a composite key, a validation rule, a display numbering rule and a "
              "requirement. Naming the two stretches apart removes the need for all four. It is the "
              "cheaper design and it was available from the start; D-15 argued against it on a lookup "
              "objection that turned out to be answerable.").font = NOTE_F

# ---- round 5 ------------------------------------------------------------
ws = wb.create_sheet("07_Round5")
ws.sheet_view.showGridLines = False
ws["A1"] = "Review round 5 — a question, not a change"
ws["A1"].font = TITLE_F
ws["A2"] = "The key was right. Checking it found two rules that were not implemented."
ws["A2"].font = NOTE_F
rows = [
    ["1", "Data model",
     "In the programming specification, key setting of 'PersonPeriodWeight' is 'assignment_id + "
     "period_start'. My opinion is why period_start is needed as key. 'assignment_id' is unique in the "
     "'PersonPeriodWeight' and 'Assignment' sheets. Explain me that point. If my opinion isn't hurting "
     "other data consistency then change the key setting of 'PersonPeriodWeight' as 'assignment_id' only.",
     "NOT CHANGED, and here is why. assignment_id is unique in Assignment - it is that sheet's primary "
     "key. It was also unique in PersonPeriodWeight, but only because the dummy file happened to carry "
     "one window per assignment; that is a property of the sample, not of the schema. "
     "PersonPeriodWeight is a CHILD of Assignment and one assignment may carry SEVERAL non-overlapping "
     "windows - a spell of leave, back to normal, then a peak - which is what REQ-PSN-05's 'overrides' "
     "(plural), V-06's assignment-window clause and the data model's 'periods within one assignment must "
     "not overlap' all assume. Keying on assignment_id alone would cap it at one window, and the second "
     "spell would need a second Assignment row, fragmenting one person-project-role across rows that are "
     "not really different assignments. Your condition - 'if it isn't hurting other data consistency' - "
     "is therefore not met, so the key stays as it is. Say the word if you want the single-window model "
     "anyway; it is a small change and the cost is exactly the one described above.",
     "Specification v0.8 sheet 03 now carries this reasoning"],
    ["2", "Validation",
     "(not raised - found while answering item 1)",
     "Two rules were specified but never implemented, and the question is what exposed them. (a) V-06 "
     "says periods within one project AND within one assignment must not overlap. Only the project half "
     "ran, so two overlapping override windows passed silently and the weight that applied in the shared "
     "months depended on the order the rows happened to sit in the file. (b) Nothing checked that a "
     "PersonPeriodWeight row pointed at a real assignment, so an orphan override was accepted and then "
     "ignored without a word - the typed weight simply never applied. Both are now in the reference "
     "implementation, the second as new rule V-24, and both were proved to fire against deliberately "
     "broken copies of the dummy file. The fixture itself is the root cause: it only ever had one window "
     "per assignment, so the multi-window path was never exercised. It now carries an assignment with "
     "two.",
     "Plan v1.9 (R-12), spec v0.8, dummy v1.8"],
]
r = table(ws, 4, ["#", "Area", "What you raised (verbatim)", "What was done", "Carried in"],
          rows, [5, 14, 66, 110, 30], wrap_cols=(3, 4, 5))
r = ws.max_row + 2
ws.cell(r, 1, "Worth noting for its own sake: a question about a key found two silent-wrong-answer bugs. "
              "Neither was reachable by reading the code, because both were absences - a rule that was "
              "written down and never built.").font = NOTE_F

# ---- round 6 ------------------------------------------------------------
ws = wb.create_sheet("08_Round6")
ws.sheet_view.showGridLines = False
ws["A1"] = "Review round 6 — everything confirmed, two additions"
ws["A1"].font = TITLE_F
ws["A2"] = ("All 13 changed components and all 7 changed decisions marked OK; none marked Rework. "
            "Two new requests, both applied in prototype v0.8.")
ws["A2"].font = NOTE_F
rows = [
    ["1", "UI",
     "Milestone markers color highlights 'Interim DB Lock' and 'Final DB Lock' as Red. Those milestones "
     "(interim/final DB Lock) are more important and it should be recognizable than others.",
     "Applied. Red, and a larger marker with it - size as well as hue, because D-04 makes 'never colour "
     "alone' a floor for this UI and a red triangle alone would be invisible to a reader with red-green "
     "colour blindness. The markers already sit in their own lane above the bands (D-17), so red reads "
     "cleanly and does not collide with the red Start-up band. The legend gains an entry naming what "
     "they are. JUDGEMENT CALL: 'interim DB lock cut-off' and 'final DB lock cut-off' are left "
     "ordinary - the cut-off is preparation, the lock is the event that moves the timeline. Say if you "
     "want the cut-offs emphasised too.",
     "Prototype v0.8, decision D-20, spec v0.9 sheet 06"],
    ["2", "UI",
     "In 'Source Data (project)', add 'Utilisation' graph for projects specific monthly resource with "
     "bars (upper: 2 times x average of all projects FTE, lower: 0.5 times x average of all projects, "
     "additional: the project's average FTE during entire period). The graph location is next to the "
     "'Project' table. Project also can provide chronological resource trend like 'Source data (person)' "
     "tab. In addition, a project doesn't have static threshold to measure over-burden or "
     "under-resource. It suggests some bars to give more informative stuffs.",
     "Applied with your three lines exactly as specified, directly under the project table where the "
     "person tab puts its strip. Your second sentence is the important one and it is why this became a "
     "new requirement rather than a copy: a person has a capacity, so absolute thresholds mean "
     "something; a project does not, so the references had to be relative. That is REQ-DSH-12. "
     "JUDGEMENT CALL: the portfolio average is taken over ACTIVE project-months only. Including months "
     "where a project draws nothing would pull the average toward zero and make every running project "
     "look heavy against it. Say if you meant the simple mean across all months. "
     "One property to be aware of: because the lines move with the portfolio, a bar can cross a line "
     "with no change to the project itself. Correct for a relative measure, but it means the graph "
     "answers 'heavy compared to what we usually run', not 'over budget' - and the caption says so.",
     "Prototype v0.8, component P-06, decision D-21, plan v1.10 REQ-DSH-12, spec v0.9"],
]
r = table(ws, 4, ["#", "Area", "What you raised (verbatim)", "What was done", "Carried in"],
          rows, [5, 10, 66, 112, 32], wrap_cols=(3, 4, 5))
r = ws.max_row + 2
ws.cell(r, 1, "Both items carry a judgement call I made rather than guessed at silently. Neither blocks "
              "anything: each is one line to change if I have read you wrong.").font = NOTE_F

# ---- why an approved document was re-opened ------------------------------
ws = wb.create_sheet("09_Since_v1.0")
ws.sheet_view.showGridLines = False
ws["A1"] = "Why v2.0 re-opened a document that was approved, and what v2.1 settles"
ws["A1"].font = TITLE_F
ws["A2"] = ("v1.0 closed the Step 3 gate on 2026-08-02. This sheet says what changed after that, "
            "what was wrong, why nothing caught it, and - at v2.1 - how the one open item ended.")
ws["A2"].font = NOTE_F
ws.column_dimensions["A"].width = 22
ws.column_dimensions["B"].width = 118

BODY = [
    ("WHAT HAPPENED", ""),
    ("", "v1.0 described the application as it stood at plan v2.0. Thirty-four change requests "
         "later - R-13 to R-46, plan v2.54 - it described an application that no longer existed."),
    ("", "22 screen elements had been added and were in nobody's list. Five entries had become "
         "actively WRONG: they described behaviour the application does not have. An entry that is "
         "merely missing leaves a reader uninformed; an entry that is wrong leaves them misinformed, "
         "which is worse, and all five read as confident statements of fact."),
    ("WHY NOTHING CAUGHT IT", ""),
    ("", "tools/check_consistency.py holds the development plan, the programming specification, the "
         "source-data template, both dummies and the machine-readable contract to each other on every "
         "build. It reports a mismatch in any of them and it has been clean throughout."),
    ("", "THIS DOCUMENT WAS NOT IN THAT SET. It was the one artefact nothing checked, so it fell "
         "behind in silence while every other document was kept in step automatically. The drift is "
         "a gap in the guard, not a lapse of attention - which is why the fix is to put this document "
         "into the checker, not to promise to remember."),
    ("WHAT WAS CORRECTED", ""),
    ("G-04", "Said the export writes 'all ten sheets'. It writes ELEVEN - MonthlyEstimate arrived at "
             "R-30 with schema 9."),
    ("O-05", "Said five summary tiles. There are SIX: R-42 added 'Off their standard', which jumps to "
             "the Standard vs staffed panel."),
    ("O-06", "Said flatly 'No legend; hover pop-up instead'. True of THAT chart, and your instruction "
             "still holds there - but five other charts carry a legend, and since R-45 a legend entry "
             "is clickable and picks its series out across the tab. The entry now says which is which."),
    ("O-08", "Described a bar chart of MEAN load per person, recorded 'Keep - unchanged'. No such "
             "chart exists. It was replaced by a STACKED 'Monthly demand by person', which answers "
             "what a month is made of rather than what a person averages."),
    ("X-04", "Recorded row virtualisation as 'Keep - unchanged', which reads as built. IT WAS NEVER "
             "BUILT - there is no virtualisation anywhere in src/. Both Overall tables render every "
             "row. This was the one correction that is not merely editorial: REQ-DSH-09 and "
             "REQ-NFR-03 named a thousand people, and at that size it was an open performance risk. "
             "v2.0 listed it as NOT IMPLEMENTED so it would stop being mistaken for done, and said "
             "it needed a decision - build it, or move the requirement. CLOSED AT v2.1 - see 'WHAT "
             "v2.1 SETTLES' below."),
    ("WHAT IS STILL TRUE", ""),
    ("", "The v1.0 review trail is preserved exactly: your words against each component, the decision "
         "you took, and what was done about it. Nothing there is rewritten. The 46 components you "
         "reviewed keep their ids, their disposition and their confirm marks."),
    ("", "The 22 additions carry 'Added after approval' in the decision column rather than 'Keep' or "
         "'Change', because none of them was in front of you at the Step 3 gate. Recording them as "
         "reviewed would falsify a trail that is otherwise exact. Each names the change request that "
         "introduced it, so it can be traced back to the conversation it came from."),
    ("WHAT THIS DOES NOT DO", ""),
    ("", "It does not re-open the Step 3 GATE. The gate was about whether the component set was the "
         "right one to build, and it was. This is the list catching up with what was then built on "
         "your instructions, request by request."),
    ("WHAT v2.1 SETTLES", ""),
    ("", "v2.0 left exactly one thing open: X-04, row virtualisation, recorded as NOT IMPLEMENTED "
         "against a requirement naming 1,000 people, and needing a decision that v2.0 deliberately "
         "did not take - build it, or move the requirement."),
    ("", "YOU ASKED FOR IT TO BE MEASURED FIRST, WHICH IS WHY THE ANSWER IS NOT THE ONE EITHER OF US "
         "WOULD HAVE GUESSED. A fixture generator takes any --projects and --people "
         "(tools/build_stress_workbook.py) and a driver times four interactions against budgets set "
         "before any number was seen (tools/measure_scale.py). Switching to the Overall tab over a "
         "60-month horizon, against a 1,000 ms budget: 50 x 100 529 ms | 100 x 100 689 ms | "
         "100 x 150 810 ms | 100 x 200 981 ms | 50 x 400 1,044 ms | 100 x 1,000 3,058 ms."),
    ("", "THE MIDDLE VALUE YOU THEN ASKED FOR IS 150 PEOPLE, NOT THE 200-400 THAT WAS OFFERED. Both "
         "of those measure over budget once the worst case is counted, so the offer was wrong and the "
         "measurement corrected it. 100 x 150 is the largest volume whose WORST case is still inside "
         "budget (894 ms of 1,000); 100 x 200 medians 98% and peaks at 1,225 ms."),
    ("", "SO REQ-NFR-03 MOVED AND THE CODE DID NOT, and X-04 is now a decision with its figures "
         "rather than a defect. The entry had been wrong twice - 'built' when it was not, then "
         "'defect' against a volume nobody had measured - and a decision is the only one of the three "
         "states a later reader can act on."),
    ("", "ONE MORE BREACH CAME OUT OF MAKING THIS CHANGE, and it is the same shape as the drift "
         "above: the desktop specification was issued as v1.5 with no v1.5 row in its own version "
         "history, which is REQ-VC-04, in the document set whose whole subject is version control. "
         "check_consistency.py now requires every controlled document to carry a history row for the "
         "version it calls itself. Nothing had been checking that either."),
]
r = 4
for head, text in BODY:
    if head and not text:
        ws.cell(r, 1, head).font = H1_F
        r += 1
        continue
    if head:
        c = ws.cell(r, 1, head); c.font = BOLD_F; c.alignment = WRAP
    c = ws.cell(r, 2, text); c.font = BODY_F; c.alignment = WRAP
    ws.row_dimensions[r].height = max(15, 13 * (len(text) // 112 + 1))
    r += 1

wb.save(OUT)
print(f"Written: {OUT}  ({len(C)} components, {len(D)} decisions)")
