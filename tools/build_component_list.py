"""Generate the Step 3 UI component list - the thing being reviewed alongside the prototype.

    python tools/build_component_list.py

Output: docs/PRAP_UI_Component_List_v0.1.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

VERSION = "0.3"
DATE = "2026-08-01"
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
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
WRAPC = Alignment(vertical="top", wrap_text=True, horizontal="center")


def table(ws, r0, headers, rows, widths, wrap_cols=(), yellow_col=None):
    for i, h in enumerate(headers, 1):
        c = ws.cell(r0, i, h)
        c.font, c.fill, c.border, c.alignment = HDR_F, HDR_FILL, BOX, WRAPC
    ws.row_dimensions[r0].height = 28
    for r, data in enumerate(rows, r0 + 1):
        for i, v in enumerate(data, 1):
            c = ws.cell(r, i, v)
            c.font, c.border = BODY_F, BOX
            c.alignment = WRAP if i in wrap_cols else Alignment(vertical="top")
            if yellow_col == i:
                c.fill = INPUT
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
ws["A2"] = "Step 3, task 3.1 — high-level design for review"
ws["A2"].font = NOTE_F
meta = [("Version", f"v{VERSION}"), ("Date", DATE), ("Author", "Claude Code"),
        ("Prototype", "app/PRAP_Prototype_v0.3.html"),
        ("Governing plan", "PRAP_Development_Plan_v1.5.xlsx (changes R-05..R-08, awaiting signature)"),
        ("Specification", "PRAP_Programming_Specification_v0.4.xlsx (draft)")]
r = 4
for k, v in meta:
    ws.cell(r, 1, k).font = BOLD_F
    ws.cell(r, 2, v).font = BODY_F
    r += 1
ws.column_dimensions["A"].width = 22
ws.column_dimensions["B"].width = 80

r += 1
ws.cell(r, 1, "How to review this").font = H1_F
r += 1
for line in [
    "The prototype is DESIGN ONLY. Nothing on the page loads, calculates or exports - the figures are a",
    "fixed snapshot baked into the markup, and the only script is tab switching. That is deliberate: the",
    "plan has you approve the component design before any application code is written.",
    "",
    "Open the prototype, then work down sheet 01. For each component, mark the Decision column:",
    "   Keep      - as designed",
    "   Change    - keep the component, change what it does or shows (say what in your comment)",
    "   Drop      - not needed in v1.0",
    "   Add       - something missing; add a row at the bottom",
    "",
    "Approving this list fixes WHAT each component is and does. Exact layout, spacing, colour and",
    "typography stay open until task 3.3, so do not spend review time on pixels.",
    "",
    "Sheet 02 lists the design decisions taken while building the prototype that you may want to overturn -",
    "each one is a real choice, not a default.",
]:
    ws.cell(r, 1, line).font = BODY_F
    r += 1

# ---- components ----------------------------------------------------------
ws = wb.create_sheet("01_Components")
ws.sheet_view.showGridLines = False
ws["A1"] = "Component list"
ws["A1"].font = TITLE_F
ws["A2"] = "38 components across the three tabs. Mark each one in the Decision column."
ws["A2"].font = NOTE_F
ws.freeze_panes = "A5"

C = [
    # id, area, component, what it does, REQ-IDs
    ("G-01", "Global", "Header", "Application name, version, expected schema version.", "REQ-VC-02"),
    ("G-02", "Global", "Loaded-file line", "Which workbook is loaded and when it was read.", "REQ-IMP-05"),
    ("G-03", "Global", "Load workbook", "File picker / drag-and-drop. Warns first if edits are unsaved.", "REQ-IMP-01, REQ-IMP-08"),
    ("G-04", "Global", "Export", "Writes all ten sheets back in template layout, edits included.", "REQ-IMP-04, REQ-IMP-07"),
    ("G-05", "Global", "Findings banner", "Summary of the last import; opens the full report.", "REQ-IMP-02"),
    ("G-06", "Global", "Unsaved-edit counter", "Always visible once anything is edited.", "REQ-IMP-08"),
    ("G-07", "Global", "Tab bar", "Overall | Source data (project) | Source data (person).", "REQ-DSH-01..04"),
    ("G-08", "Global", "Empty state", "With nothing loaded: one load panel and a template download link.", "REQ-IMP-03"),

    ("O-01", "Overall", "Horizon control", "From/to month, defaulting to 24 months.", "REQ-CAL-01"),
    ("O-02", "Overall", "Expand to all projects", "One click widens the horizon to the latest project end date.", "REQ-DSH-07"),
    ("O-03", "Overall", "Filters (GLOBAL)", "Project type, project, person, role, department. Moved out of the Overall tab: one setting now drives every tab.", "REQ-DSH-05"),
    ("O-03b", "Overall", "Reset filters", "Clears every filter and restores the 24-month default in one action.", "REQ-DSH-05"),
    ("O-04", "Overall", "Unit toggle", "FTE or hours, seeded from Config.capacity_unit.", "REQ-CAL-08"),
    ("O-05", "Overall", "Summary tiles", "Projects, people, total demand, over-allocated months, under-allocation runs.", "REQ-DSH-08"),
    ("O-06", "Overall", "Demand chart", "Stacked monthly demand, ONE BAND PER PROJECT, largest on the baseline. 'Others' grey, trials coloured - see D-01.", "REQ-DSH-02"),
    ("O-07", "Overall", "Resource by project (table)", "Project x month heatmap. Sorted NewDrug CT, Biosimilar CT, Others, then earliest first.", "REQ-DSH-01"),
    ("O-07b", "Overall", "Project row expansion", "Clicking a project name reveals a row per person and role, each with its own monthly figures.", "REQ-DSH-01"),
    ("O-08", "Overall", "Mean load per person (chart)", "One bar per person against both thresholds - one pair of lines, since both are absolute. Above the bar budget it shows a ranked subset and rolls the rest into one band, naming what is shown.", "REQ-DSH-02, REQ-DSH-08, REQ-DSH-09"),
    ("O-09", "Overall", "Resource by person (table)", "Person x month, summed across projects, over/under flagged.", "REQ-DSH-01, REQ-DSH-08"),
    ("O-09b", "Overall", "Person row expansion", "Clicking a person name reveals a row per project and role, in the same type-then-date order.", "REQ-DSH-01"),
    ("O-10", "Overall", "Project timeline (Gantt)", "Period bands shaded by weight, milestone and inspection markers.", "REQ-DSH-02, REQ-PRJ-05"),

    ("P-01", "Project tab", "Project table", "All 23 columns, sortable, filterable, editable.", "REQ-DSH-03, REQ-IMP-07"),
    ("P-02", "Project tab", "Milestone sub-table", "Milestones of the selected project in date order; Inspection may repeat.", "REQ-PRJ-05, REQ-PRJ-13"),
    ("P-03", "Project tab", "Period sub-table", "Derived periods with seq, dates, weight and note.", "REQ-PRJ-06, REQ-CAL-09"),
    ("P-04", "Project tab", "Recompute periods", "Re-derives from current milestones; warns before replacing hand-set dates.", "decision C-10"),
    ("P-05", "Project tab", "Export visible table", "Current table to .xlsx.", "REQ-DSH-06"),

    ("S-01", "Person tab", "Person table", "All 12 columns, sortable, filterable, editable.", "REQ-DSH-04, REQ-IMP-07"),
    ("S-02", "Person tab", "Utilisation strip", "Selected person's monthly load with both thresholds drawn.", "REQ-DSH-08"),
    ("S-03", "Person tab", "Assignment sub-table", "Project, role, dates and person weight.", "REQ-PSN-02, REQ-PSN-03"),
    ("S-04", "Person tab", "Override sub-table", "PersonPeriodWeight windows for the selected assignment.", "REQ-PSN-05"),
    ("S-05", "Person tab", "Export visible table", "Current table to .xlsx.", "REQ-DSH-06"),

    ("E-01", "Editing", "Inline cell edit", "Every field editable, validated at the point of entry.", "REQ-IMP-09"),
    ("E-02", "Editing", "Cascade confirm", "Changing an identifier states how many rows will follow, then rewrites them.", "REQ-IMP-10, V-17"),
    ("E-03", "Editing", "Delete guard", "Refuses to delete a row that is still referenced, naming what points at it.", "V-17"),
    ("X-01", "Layout", "Horizontal scroll regions", "Every chart and table scrolls inside its own panel, so the page body never scrolls sideways.", "REQ-NFR-02"),
    ("X-02", "Layout", "Type and phase pills", "Project type and clinical phase as labelled pills; text carries the meaning, colour only speeds recognition.", "REQ-PRJ-01, REQ-PRJ-09"),
    ("X-03", "Layout", "Numbered repeated periods", "A period name occurring more than once in a project carries its occurrence number wherever it is shown - 'Conduct (1)', 'Conduct (2)' - in timeline bands, tooltips, the period sub-table and exports. A name occurring once is never numbered.", "REQ-DSH-10"),
    ("X-04", "Layout", "Row virtualisation", "Both Overall tables render only the rows in the viewport plus overscan, at fixed row height so the scrollbar stays truthful. Sorting, filtering and totals always run over the whole model, never the rendered slice.", "REQ-DSH-09, REQ-NFR-03"),
]
rows = [list(c) + ["", ""] for c in C]
r = table(ws, 4, ["ID", "Area", "Component", "What it does", "REQ-IDs", "Decision", "Your comment"],
          rows, [8, 13, 30, 74, 26, 14, 44], wrap_cols=(4, 7), yellow_col=6)
dv = DataValidation(type="list", formula1='"Keep,Change,Drop"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"F5:F{4 + len(rows)}")
for rr in range(5, 5 + len(rows)):
    ws.cell(rr, 7).fill = INPUT
r = table(ws, r, ["Count"], [[f"=COUNTA(A5:A{4 + len(rows)})"]], [14])
ws.cell(r, 1, "Add a row at the bottom for anything missing.").font = NOTE_F

# ---- design decisions ----------------------------------------------------
ws = wb.create_sheet("02_Design_Decisions")
ws.sheet_view.showGridLines = False
ws["A1"] = "Design decisions taken in the prototype"
ws["A1"].font = TITLE_F
ws["A2"] = "Each is a real choice with a cost. Overturn any of them here."
ws["A2"].font = NOTE_F
ws.freeze_panes = "A5"

D = [
    ("D-01", "SUPERSEDED - the demand chart now stacks by individual project, as you asked.",
     "v0.1 stacked by clinical phase because 62 project bands cannot be told apart by hue. You asked for per-project "
     "bands, so that is what v0.2 does: ordered by total resource with the largest on the baseline, 'Others' grey.",
     "Return to phase stacking, or offer both behind a toggle."),
    ("D-11", "Beyond seven projects, colour is assigned from an EXTENDED palette, not the validated one.",
     "The validated set caps at eight hues because past that, colourblind readers - and often anyone - cannot tell "
     "adjacent bands apart. Per-project colour needs ~50, so the seven validated hues are stepped in lightness to "
     "generate them. They look various, but hue alone no longer identifies a band: the legend order, the tooltip and "
     "the table below carry identity. This is a real cost of the request, not a flaw in the build.",
     "Filter to fewer projects before reading the chart; or colour only the top N and grey the rest."),
    ("D-12", "The project table samples the head of each type rather than listing a flat top-14.",
     "Your sort puts all 34 NewDrug CT projects first, so a flat top-14 would never reach Biosimilar CT or Others and "
     "the ordering could not be seen working. The mock-up shows the first few of each type, in order, with a marker "
     "row saying how many were skipped. The real table lists all 62.",
     "Show a flat top-N in strict order; or paginate."),
    ("D-13", "The global filter bar is not sticky.",
     "A sticky bar 110px tall covered panel headings as soon as the page scrolled. Making it scroll away avoids that, "
     "at the cost of scrolling back up to change a filter.",
     "Make it sticky and collapse it to a single summary line on scroll."),
    ("D-02", "The project table lists the ten busiest projects plus an aggregate row.",
     "62 rows x 12 months does not fit on screen. The real table lists all 62 with sort and filter; the prototype "
     "shows the shape, not the whole.", "Show all 62 with a scroll region instead."),
    ("D-03", "Heat shading in the tables is one blue ramp, light to dark.",
     "Magnitude is a sequential quantity, so it takes one hue. The aggregate row is deliberately NOT shaded - "
     "including it in the scale would flatten every row actually on screen.",
     "No shading at all; or shade relative to each person's capacity rather than the global maximum."),
    ("D-04", "Over- and under-allocation carry an icon and a value, never colour alone.",
     "Red-green colour blindness affects around 8% of men. A cell that says only 'red' is unreadable to them, and "
     "unprintable in mono. The arrow and the number carry the meaning; colour only speeds it up.",
     "None recommended - this one is an accessibility floor rather than a preference."),
    ("D-05", "Both thresholds are drawn on the person chart and the utilisation strip.",
     "A ceiling without a floor makes under-use invisible, and under-use is half of what you asked the tool to "
     "show.", "Draw only the ceiling; or make the floor a toggle."),
    ("D-06", "The Gantt shades period bands by weight rather than by period name.",
     "Weight is what drives the simulation. Naming the periods by colour would spend the palette on labels that "
     "are already in the tooltip and the period sub-table.",
     "Colour by period name instead, with weight in the tooltip only."),
    ("D-07", "Editing is inline in the tables, not in a separate form or dialog.",
     "You asked for every field to be editable. A dialog per row would make bulk correction - the common case "
     "after a timeline slips - slow enough that people would go back to editing the workbook by hand.",
     "A row-level edit dialog; or a dedicated edit mode."),
    ("D-08", "The findings banner persists until dismissed rather than fading.",
     "A toast that disappears is a finding nobody read. Import findings are the mechanism that stops bad data "
     "reaching the simulation silently.", "Auto-dismiss after a delay."),
    ("D-09", "Dark mode is supported, with its own selected colour steps.",
     "Not a flip of the light palette: the heatmap ramp, the categorical hues and the status inks are each "
     "re-stepped for the dark surface and validated against it.",
     "Light mode only, which would remove about 30 lines of CSS."),
    ("D-10", "The page is one scrolling column per tab, not a fixed dashboard grid.",
     "It prints, it works on a laptop screen, and it needs no layout engine. A fixed grid would look denser on a "
     "large monitor at the cost of both.", "A fixed multi-pane grid with independent scroll regions."),
    ("D-14", "At the new target volume the person chart shows the 20 most loaded people, not all 1,000.",
     "REQ-NFR-03 now reads 1,000 people (S2-06). A thousand bars across a 1,200px panel is 1.2px each - narrower "
     "than the gap between them, so the chart would render but say nothing. The subset is ranked by load, the "
     "remainder is drawn as one band, and the chart states which it is showing rather than quietly truncating. "
     "20 is a starting figure, not a derived one.",
     "A different cut-off; or only the people who breach a threshold; or a scrollable chart at a fixed bar width."),
    ("D-15", "Repeated period names are numbered by occurrence, not renamed.",
     "S2-04 asked for the two 'Conduct' stretches to be distinguishable. Numbering them - 'Conduct (1)', "
     "'Conduct (2)' - keeps the source data untouched, since the number is derived from period_seq at display "
     "time. Renaming them in the workbook would break the PeriodWeightStandard lookup, which is keyed on the "
     "period name.",
     "Label them by what separates them instead - 'Conduct (pre-interim)' and 'Conduct (post-interim)' - which "
     "reads better but only works for this one split."),
]
rows = [list(d) + ["", ""] for d in D]
r = table(ws, 4, ["ID", "Decision", "Why", "The alternative, if you want it", "Decision", "Your comment"],
          rows, [8, 46, 76, 50, 14, 40], wrap_cols=(2, 3, 4, 6), yellow_col=5)
dv2 = DataValidation(type="list", formula1='"Accept,Overturn"', allow_blank=True)
ws.add_data_validation(dv2)
dv2.add(f"E5:E{4 + len(rows)}")
for rr in range(5, 5 + len(rows)):
    ws.cell(rr, 6).fill = INPUT

# ---- deferred ------------------------------------------------------------
ws = wb.create_sheet("03_Deferred")
ws.sheet_view.showGridLines = False
ws["A1"] = "Deliberately not in the prototype"
ws["A1"].font = TITLE_F
ws["A2"] = "So their absence is not read as an oversight."
ws["A2"].font = NOTE_F
rows = [
    ["Any loading, calculation, filtering or export behaviour", "Task 3.1 is design only. The figures shown are a "
     "fixed snapshot computed in Python and baked into the markup."],
    ["Exact spacing, type scale and final colour values", "Fixed at task 3.3, once the components are agreed."],
    ["Hover tooltips beyond the native SVG title", "The full crosshair/tooltip layer is specified but not built "
     "until code generation."],
    ["Keyboard shortcuts and full accessibility pass", "Reviewed against the working prototype at task 3.3, where "
     "they can be tried rather than described."],
    ["Row expansion (project to people, person to projects)", "Shown as a caret in the row header; the behaviour "
     "is specified on sheet 06 of the specification."],
    ["The validation findings report itself", "Specified on sheet 04 of the specification; the banner that opens "
     "it is in the prototype."],
]
r = table(ws, 4, ["Not shown", "Why"], rows, [56, 96], wrap_cols=(1, 2))

wb.save(OUT)
print(f"Written: {OUT}")
