"""Generate the PRAP desktop application development plan workbook.

This is a SEPARATE plan from PRAP_Development_Plan_v*.xlsx. That one governs the
single-file web application (app/PRAP.html), which is finished and stays finished.
This one governs a second, independently packaged application built on the same
calculation engine.

The two plans are siblings, not successors: neither supersedes the other.

    python tools/build_newapp_plan.py

Output: docs/PRAP_NewApp_Development_Plan_v0.1.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.styles.borders import Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

DOC_VERSION = "0.1"
DOC_STATUS = "DRAFT - issued for review. Step 1 of 5. Nothing is built until Gate N1 is passed."
DOC_DATE = "2026-08-13"
OUT = Path(__file__).resolve().parents[1] / "docs" / f"PRAP_NewApp_Development_Plan_v{DOC_VERSION}.xlsx"

WEB_PLAN = "PRAP_Development_Plan_v2.26.xlsx"
WEB_APP = "app/PRAP.html (application v1.24)"

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
        (NEW_FILL, "Green = new to the desktop application; nothing in the web application corresponds to it."),
        (CHG_FILL, "Orange = inherited from the web application but deliberately changed here."),
        (INPUT_FILL, "Yellow = needs your decision before the work can proceed."),
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
ws["A2"] = "Desktop Application - Development Plan"
ws["A2"].font = Font(name=FONT, size=14, color=NAVY)

cover = [
    ("Document ID", "PRAP-NAPP-PLAN-001"),
    ("Document type", "Development plan (Step 1 deliverable) for a SECOND application"),
    ("Version", f"v{DOC_VERSION}"),
    ("Status", DOC_STATUS),
    ("Issue date", DOC_DATE),
    ("Author", "Claude Code"),
    ("Reviewer", "Requester - review round 1 pending"),
    ("Relationship to the web application",
     "PARALLEL, NOT SUCCESSOR. The web application and its documents are complete and stay in "
     "service. This plan does not supersede, amend or retire any of them."),
    ("Governs", "A packaged desktop application built on the same calculation engine"),
    ("Does NOT govern", f"{WEB_APP}, which remains under {WEB_PLAN}"),
    ("Repository", "Dan5050-now/project1"),
    ("Branch", "claude/project-resource-assignment-app-1vjdzh"),
    ("Supersedes", "Nothing. This is a new document line, numbered from v0.1"),
]
r = 4
for k, v in cover:
    ws.cell(row=r, column=1, value=k).font = BOLD_F
    c = ws.cell(row=r, column=2, value=v)
    c.font = BODY_F
    c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 36
ws.column_dimensions["B"].width = 110
for rr in range(4, r):
    ws.row_dimensions[rr].height = 30

r += 1
r = section(ws, r, "Why a second plan rather than a new version of the first")
r = lines(ws, r, [
    "The web application is finished, verified and about to be used. Folding a desktop rewrite into its plan would",
    "put a completed, approved document back into draft, and would make it impossible to tell which requirements",
    "the finished tool actually satisfies. Two plans keep both answers clean:",
    "",
    f"    {WEB_PLAN}          the web application - CLOSED at Gate 4, going to Gate 5",
    f"    PRAP_NewApp_Development_Plan_v{DOC_VERSION}.xlsx      the desktop application - OPEN at Step 1",
    "",
    "They share one calculation engine and one data contract, and sheet 02 states exactly how that sharing is",
    "kept honest. Everything else about them is independent: their own versions, their own gates, their own",
    "approvals, their own release cycles.",
], mono=True)
r += 1
r = note(ws, r, "File naming follows the repository convention already in use - no spaces, version suffix, one "
                "generator script per document. The generator for this plan is tools/build_newapp_plan.py.")

# ---- 01 Version history ---------------------------------------------------
ws, r = sheet(wb, "01_Version_History", "Version history",
              "This document's own line. It does not continue the web application plan's numbering.")

hist = [
    [f"{MARK_NEW}0.1", DOC_DATE, "Claude Code", "Pending",
     "FIRST ISSUE. Raised on your instruction of 2026-08-13: build the requested application as a separate "
     "program type, keep imported data across sessions, and plan it apart from the web application under its "
     "own document name. Contains 33 requirements (sheet 03), the layer split that makes one engine serve two "
     "applications (sheet 04), the workspace persistence model (sheet 05), 12 decisions (sheet 06) and 11 open "
     "questions (sheet 11). Distribution size is recorded as unconstrained on your instruction, which is what "
     "makes decision N-01 affordable."],
]
r = table(ws, r, ["Version", "Date", "Author", "Reviewer", "Summary of change"],
          hist, [10, 13, 15, 13, 108], wrap_cols=(5,), mark_col=1)

r = section(ws, r, "Numbering rules for this document line")
rules = [
    ["v0.x", "Draft issues during Step 1 review rounds."],
    ["v1.0", "The approved baseline, set at Gate N1."],
    ["v1.x", "Approved changes against that baseline, each separately approved."],
    ["v2.0", "Reserved for a structural change, on the same rule the web plan used."],
]
r = table(ws, r, ["Version", "Meaning"], rules, [12, 110], wrap_cols=(2,))
r = note(ws, r, "Gate prefixes are N1..N5 throughout this document, so a reference such as 'G4' can never be "
                "confused between the two plans.")
r = legend(ws, r)

# ---- 02 Scope -------------------------------------------------------------
ws, r = sheet(wb, "02_Scope", "Scope - two applications, one engine",
              "What the desktop application is for, what it inherits, and what is explicitly out of scope.")

r = section(ws, r, "Objective")
r = lines(ws, r, [
    "Deliver the same resource simulation as a conventional installed program: an application with its own icon,",
    "its own window and its own files, which remembers the data it was given and opens showing the plan the user",
    "was last working on. The simulation itself - the load formula, the period derivation, the validation rules -",
    "does not change at all, and must not.",
])
r += 1

r = section(ws, r, "The two applications side by side")
twin = [
    ["Form", "One HTML file, opened in a browser", "Installed program with its own window and icon", "-"],
    [f"{MARK_CHG}Data after closing", "Lost - the file must be re-imported each session", "KEPT - the workspace reopens as it was left", "NR-STO-01"],
    [f"{MARK_CHG}Source of truth", "The Excel workbook outside the application", "The workspace file the application owns; Excel becomes exchange", "NR-STO-02"],
    ["Calculation engine", "Shared - one implementation", "Shared - the same implementation, not a copy", "NR-PAR-01"],
    ["Data contract", "Schema version 5, ten sheets", "Identical, unchanged", "NR-PAR-02"],
    ["AI agent interoperability", "prap-source-data JSON, format_version 1", "Identical, and now also the on-disk format", "NR-STO-03"],
    [f"{MARK_NEW}Distribution", "Copy one file", "Copy or install one package; size unconstrained on your instruction", "NR-DEP-01"],
    ["Network use", "None", "None", "NR-SEC-01"],
    ["Status", "Complete, in service, frozen at Gate 5", "Not started - this plan is Step 1", "-"],
]
r = table(ws, r, ["Aspect", "Web application", "Desktop application", "Requirement"],
          twin, [26, 46, 56, 14], wrap_cols=(2, 3), mark_col=1)
r += 1

r = section(ws, r, "What the web application keeps - not touched by this plan")
keep = [
    [f"{WEB_APP} continues in service, unchanged, and is released as v1.0 under its own Gate 5."],
    [f"{WEB_PLAN}, the programming specification v1.0 and the UI component list v1.0 stay approved as they are."],
    ["The source workbook template, the dummy datasets and the AI agent guide serve BOTH applications and are "
     "not forked."],
    ["The 13 verification suites under tools/ keep running against the HTML build after every change, which is "
     "how a regression in the shared engine is caught before it can reach either application."],
    ["Any engine fix found while building the desktop application is made in the shared engine, re-verified "
     "against both, and released to the HTML build as a point version. Fixes flow to both; features do not "
     "flow backwards without their own approval."],
]
r = table(ws, r, ["Point"], keep, [146], wrap_cols=(1,))
r += 1

r = section(ws, r, "In scope")
ins = [
    ["A packaged desktop application for Windows, launched from an icon, no browser involved."],
    ["Persistent storage: a workspace the application owns, written on every Save and reopened at launch."],
    ["Import from the Excel source workbook and from prap-source-data JSON, as today - but as an INGEST into "
     "the workspace rather than as the session's only data."],
    ["Export to Excel and JSON, as today, for sharing and archiving."],
    ["Desktop conventions the web version cannot offer: native Open/Save dialogs, a recent-workspaces list, "
     "a menu bar, window state remembered between sessions."],
    ["Crash and power-loss recovery, including edits that were pending when the application stopped."],
    ["The refactor that makes one engine serve both applications, with the HTML build proven unchanged by it."],
]
r = table(ws, r, ["Item"], ins, [146], wrap_cols=(1,))
r += 1

r = section(ws, r, "Out of scope for v1.0")
outs = [
    ["Any change to the load formula, the period derivation, the validation rules or the data schema.",
     "The engine is shared. Changing it here would change the finished web application too."],
    ["Multi-user or concurrent editing of one workspace.",
     "Assumption A-06 of the web plan still holds - one person maintains a plan at a time. Q-N06 asks whether "
     "that is still true."],
    ["A server, a database service, or any network feature.",
     "The tool is offline by requirement, and that is a property worth keeping rather than an accident."],
    ["macOS and Linux builds.",
     "Buildable from the same source at little cost, but not verified and not supported unless Q-N01 says the "
     "target is not Windows-only."],
    ["Automatic update over the network.",
     "It would be the only thing in the product that needs a network. Updates are distributed as a new package."],
    ["Migrating the web application onto the desktop shell, or retiring it.",
     "Explicitly excluded on your instruction: both applications stay."],
]
r = table(ws, r, ["Excluded", "Why"], outs, [66, 80], wrap_cols=(1, 2))
r = legend(ws, r)

# ---- 03 Requirements ------------------------------------------------------
ws, r = sheet(wb, "03_Requirements", "Requirement register - desktop application",
              "NR-ids belong to this plan. REQ-ids referenced in the last column belong to the web application "
              "plan and are inherited unchanged.")

r = section(ws, r, "Inheritance rule")
r = lines(ws, r, [
    "Every requirement of the web application plan that concerns DATA or CALCULATION is inherited by this",
    "application unchanged, and is not restated here. This register holds only what is new or deliberately",
    "different. Where a requirement here replaces an inherited one, the inherited ID is named so the",
    "contradiction is visible rather than buried.",
])
r += 1

reqs = [
    [f"{MARK_NEW}NR-APP-01", "Application form", "The application is an installed or portable desktop program with its own window, icon and menu bar. No browser is visible to the user at any point.", "Must", "Your instruction", "N4"],
    [f"{MARK_NEW}NR-APP-02", "Application form", "It runs fully offline. It makes no network request of any kind, including on first launch.", "Must", "Inherited intent", "N4"],
    [f"{MARK_NEW}NR-APP-03", "Application form", "It launches to the plan the user last had open, without asking for a file.", "Must", "Your instruction", "N4"],
    [f"{MARK_NEW}NR-APP-04", "Application form", "Window size, position and the active tab are remembered between sessions.", "Should", "Desktop convention", "N4"],
    [f"{MARK_NEW}NR-APP-05", "Application form", "Native Open, Save, Save As, Import and Export dialogs are used, not browser download prompts.", "Must", "Desktop convention", "N4"],
    [f"{MARK_NEW}NR-APP-06", "Application form", "A recent-workspaces list of at least ten entries is available from the menu.", "Should", "Desktop convention", "N4"],
    [f"{MARK_NEW}NR-APP-07", "Application form", "The application version is visible in an About dialog and in the window title alongside the open workspace name.", "Must", "Version control", "N4"],

    [f"{MARK_NEW}NR-STO-01", "Storage", "Imported and hand-entered data survives closing the application. Reopening shows the same plan, with the same figures, without re-importing anything.", "Must", "Your instruction", "N4"],
    [f"{MARK_NEW}NR-STO-02", "Storage", "The application owns a workspace file on disk. That file, not the source Excel workbook, is the working store from the moment data is imported into it.", "Must", "Derived from NR-STO-01", "N4"],
    [f"{MARK_NEW}NR-STO-03", "Storage", "The workspace file is prap-source-data JSON - the same format the AI agent guide already documents - so a workspace can be read, written or generated by an AI agent with no new contract.", "Must", "Interoperability", "N4"],
    [f"{MARK_NEW}NR-STO-04", "Storage", "A committed Save is written to disk before the application reports it as saved. A save that did not reach the disk is never reported as done.", "Must", "Data safety", "N4"],
    [f"{MARK_NEW}NR-STO-05", "Storage", "Workspace writes are atomic: an interrupted write can never leave a workspace file that is neither the old contents nor the new.", "Must", "Data safety", "N4"],
    [f"{MARK_NEW}NR-STO-06", "Storage", "The last N committed versions of a workspace are retained and can be restored from within the application. N is a setting, default 10.", "Should", "Data safety", "N4"],
    [f"{MARK_NEW}NR-STO-07", "Storage", "Edits pending at the moment of a crash or power loss are recovered on the next launch, and the user is asked whether to keep or discard them.", "Should", "Data safety", "N4"],
    [f"{MARK_NEW}NR-STO-08", "Storage", "Several workspaces may exist. The user chooses which to open, and may create a new empty one at any time.", "Must", "Scenario planning", "N4"],
    [f"{MARK_NEW}NR-STO-09", "Storage", "A workspace records which source file it was imported from, when, and by which application version.", "Should", "Traceability", "N4"],

    [f"{MARK_CHG}NR-IMP-01", "Import / export", "Import reads the Excel source workbook and prap-source-data JSON exactly as the web application does, using the same reader and reporting the same findings.", "Must", "Replaces nothing - REQ-IMP-01 inherited", "N4"],
    [f"{MARK_CHG}NR-IMP-02", "Import / export", "Importing into a workspace that already holds data presents the differences and lets the user decide, per sheet, whether to replace, merge or skip. It never overwrites silently.", "Must", "New consequence of NR-STO-02", "N4"],
    [f"{MARK_CHG}NR-IMP-03", "Import / export", "Export to Excel and to JSON produces byte-for-byte the same content the web application would produce from the same data.", "Must", "Parity", "N4"],
    [f"{MARK_NEW}NR-IMP-04", "Import / export", "A workspace can be opened directly by drag-and-drop onto the application window or its icon.", "Could", "Desktop convention", "N4"],

    [f"{MARK_NEW}NR-PAR-01", "Parity", "The calculation engine, the validation rules and the period derivation are ONE implementation shared by both applications, not two copies kept in step by hand.", "Must", "Your instruction to keep both", "N2"],
    [f"{MARK_NEW}NR-PAR-02", "Parity", "Given identical input, both applications produce identical figures, identical findings and identical exports. This is proven by an automated test, not asserted.", "Must", "Derived from NR-PAR-01", "N4"],
    [f"{MARK_NEW}NR-PAR-03", "Parity", "The HTML application continues to be built from the shared engine and its behaviour is unchanged by the refactor, proven by the existing 13 suites passing unmodified.", "Must", "Protects the finished product", "N2"],
    [f"{MARK_NEW}NR-PAR-04", "Parity", "Screen layout, wording and interaction match the web application except where a desktop convention requires otherwise, and every such difference is listed.", "Should", "Two tools, one habit", "N3"],

    [f"{MARK_NEW}NR-DEP-01", "Deployment", "The application is delivered as one package. Package size is not constrained.", "Must", "Your instruction", "N5"],
    [f"{MARK_NEW}NR-DEP-02", "Deployment", "It installs and runs without administrator rights.", "Must", "Corporate desktop reality", "N5"],
    [f"{MARK_NEW}NR-DEP-03", "Deployment", "Updating means replacing the package. No workspace is touched by an update, and a workspace written by an older version opens in a newer one.", "Must", "Data safety", "N5"],
    [f"{MARK_NEW}NR-DEP-04", "Deployment", "A workspace written by a NEWER version than the running one is refused with a clear message rather than partially read.", "Must", "Data safety", "N4"],

    [f"{MARK_NEW}NR-SEC-01", "Security", "No telemetry, no crash reporting to any server, no automatic update check, no font or script loaded from a remote host. Verified by observing that the packaged application opens no socket.", "Must", "Offline by requirement", "N5"],
    [f"{MARK_NEW}NR-SEC-02", "Security", "The embedded browser engine runs with remote content disabled and Node integration off in the renderer, so a crafted workspace file cannot execute code.", "Must", "Standard hardening", "N4"],
    [f"{MARK_NEW}NR-SEC-03", "Security", "Workspace files contain business data only - no credentials, no connection strings, nothing that would be sensitive if the file were mailed to a colleague.", "Must", "Data hygiene", "N2"],

    [f"{MARK_NEW}NR-NFR-01", "Performance", "Launch to a usable window in under 5 seconds, and reopening the last workspace adds no more than 2 seconds on the volumes in A-N01.", "Should", "Usability", "N4"],
    [f"{MARK_NEW}NR-NFR-02", "Performance", "A Save completes in under 1 second at those volumes, so autosave is never felt.", "Should", "Usability", "N4"],
]
r_start = r
r = table(ws, r, ["ID", "Area", "Requirement", "Priority", "Source", "Gate"],
          reqs, [13, 17, 92, 9, 30, 7], wrap_cols=(3, 5), mark_col=1)
last = r_start + len(reqs)

dv = DataValidation(type="list", formula1='"Must,Should,Could,Won\'t"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"D{r_start + 1}:D{last}")

r = section(ws, r, "Count")
cnt = [
    ["Total requirements", f"=COUNTA(A{r_start + 1}:A{last})"],
    ["Must", f'=COUNTIF(D{r_start + 1}:D{last},"Must")'],
    ["Should", f'=COUNTIF(D{r_start + 1}:D{last},"Should")'],
    ["Could", f'=COUNTIF(D{r_start + 1}:D{last},"Could")'],
]
r = table(ws, r, ["Measure", "Count"], cnt, [26, 12])
r = note(ws, r, "Please mark any requirement you disagree with in the Priority column, or strike it out. The "
                "register is the contract for Steps 2 to 5, exactly as sheet 03 of the web plan was.")
r = legend(ws, r)

# ---- 04 Architecture ------------------------------------------------------
ws, r = sheet(wb, "04_Architecture", "Architecture - one engine, two shells",
              "The single decision that makes two applications affordable to maintain.")

r = section(ws, r, "The problem this solves")
r = lines(ws, r, [
    "Two applications doing the same arithmetic will drift apart. The month one of them reports 3.4 FTE and the",
    "other 3.6 for the same person, both become untrustworthy - and nobody will know which to believe. The only",
    "durable answer is that there are not two implementations to drift.",
    "",
    f"{WEB_APP} is 4,865 lines, of which about 4,160 are script. Only 69 of those script lines touch the DOM",
    "at all. The engine is therefore already almost separable; this is a lift, not a rewrite.",
])
r += 1

r = section(ws, r, "Layers")
layers = [
    ["core/", "Parse, validate, derive periods, calculate load, read and write xlsx, read and write JSON. No DOM, no filesystem, no dialogs.", "Shared, identical", "The whole of the trust in both products sits here."],
    ["ui/", "Tabs, tables, charts, filters, the provisional-edit model, the change log.", "Shared, identical", "Renders into a DOM; indifferent to which shell provides it."],
    ["storage/", "An interface: open, save, listWorkspaces, restoreVersion, recoverPending.", "Interface shared, implementation per shell", "The whole of the difference between the two products sits here."],
    ["shell/web/", "Storage over the browser's own storage; the build step that emits the single HTML file.", "Web only", "Keeps the finished product buildable and unchanged."],
    [f"{MARK_NEW}shell/desktop/", "Application window, menu bar, native dialogs, storage over the filesystem, recent files, window state.", "Desktop only", "New code, and the only genuinely new code in the product."],
    ["tools/", "The 13 verification suites, the document generators, the Python reference implementation.", "Shared", "Runs against both shells after the refactor."],
]
r = table(ws, r, ["Layer", "Responsibility", "Shared?", "Why the boundary is there"],
          layers, [18, 62, 26, 42], wrap_cols=(2, 3, 4), mark_col=1)
r += 1
r = note(ws, r, "Read the table by its third column. Everything that decides a number is shared; everything that "
                "differs is about where bytes are kept and which dialog opens. That is the whole architecture.")
r += 1

r = section(ws, r, "Build targets from one source tree")
r = lines(ws, r, [
    "    core/ + ui/ + shell/web/       --build-->   app/PRAP.html          one file, unchanged, still supported",
    "    core/ + ui/ + shell/desktop/   --build-->   PRAP Desktop package   new",
    "    core/                          --used by--> tools/ test suites     unchanged",
], mono=True)
r += 1
r = note(ws, r, "The HTML file stops being hand-written and becomes a build output. Its content is identical - "
                "task N2.1 requires the rebuilt file to pass all 13 suites before anything else starts.")
r += 1

r = section(ws, r, "Shell technology - the choice, and why")
tech = [
    [f"{MARK_NEW}Electron", "RECOMMENDED", "Reuses the engine and the UI unchanged. Filesystem access is direct. Testable in this repository today - Playwright drives an Electron application natively, so all 13 suites plus new desktop suites run before you ever see a build.", "Package around 180 MB. Chromium security updates mean rebuilding periodically."],
    ["Tauri", "Later option", "Package around 10 MB, single executable. Same engine reuse.", "Needs a Rust toolchain and a Windows build host; cannot be verified from the current environment. Automated UI testing needs a WebDriver setup that is not available here."],
    ["Native rewrite (C# / .NET, Java)", "Rejected", "Smallest package, best desktop integration.", "Discards a verified engine and a verified UI, and creates the second implementation that NR-PAR-01 exists to prevent. Months of work to reach where the product already is."],
    ["Progressive web app", "Rejected", "No packaging at all.", "Does not meet NR-APP-01 - it is still the browser, with the browser's storage rules."],
]
r = table(ws, r, ["Option", "Status", "For", "Against"], tech, [26, 14, 58, 50], wrap_cols=(3, 4), mark_col=1)
r = note(ws, r, "Size was the strongest argument for Tauri, and your instruction removes it. What remains is "
                "verifiability: an Electron build can be tested here, before delivery, by the same means every "
                "other claim in this project has been tested. Recorded as decision N-01, and it is reversible - "
                "the shell layer is the only code that would change.")
r = legend(ws, r)

# ---- 05 Data flow ---------------------------------------------------------
ws, r = sheet(wb, "05_Data_Flow", "Data flow and persistence",
              "The second of the two requirements: data that survives closing the application.")

r = section(ws, r, "Today, and what changes")
r = lines(ws, r, [
    "  WEB APPLICATION      Excel  --import-->  memory  --export-->  Excel",
    "                                             |",
    "                                          closing the tab loses everything",
    "",
    "  DESKTOP APPLICATION  Excel / JSON  --import-->  WORKSPACE (on disk)  --export-->  Excel / JSON",
    "                                                       ^   |",
    "                                                       |   +--> reopened automatically at launch",
    "                                                       +------- written on every committed Save",
], mono=True)
r += 1
r = note(ws, r, "The consequential change is not the file - it is that the workspace becomes the source of truth. "
                "After the first import, the Excel workbook is an exchange format: something you export FOR "
                "somebody, or import FROM somebody, not the thing the application reads every morning.")
r += 1

r = section(ws, r, "The workspace file")
wsf = [
    ["Format", "prap-source-data JSON, format_version 1 - the format the AI agent guide already documents.", "NR-STO-03"],
    ["Why not SQLite", "The data is small - tens of projects, hundreds of people, low thousands of rows. SQLite buys concurrency and query power that nothing here needs, and costs the property that an AI agent can read a workspace with no new contract. Revisit only if Q-N06 turns out to need multi-user access.", "N-02"],
    ["Why not the Excel workbook itself", "Writing xlsx on every Save would be slow, would lose the provisional-edit state, and would make an interrupted write corrupt the user's own archive file.", "N-02"],
    ["Extension", ".prap - registered with Windows so double-clicking one opens the application.", "NR-IMP-04"],
    ["Contents", "The ten sheets exactly as imported, plus a small header: application version, schema version, source file name and import timestamp, and the retained version history.", "NR-STO-09"],
    ["Readable", "Yes - it is JSON. A workspace can be inspected, diffed, version-controlled, or handed to an AI agent as-is.", "NR-STO-03"],
]
r = table(ws, r, ["Aspect", "Decision", "Ref"], wsf, [22, 108, 12], wrap_cols=(2,))
r += 1

r = section(ws, r, "Writing safely")
safe = [
    ["1", "Serialise the committed model to JSON in memory.", "Nothing has touched the disk yet."],
    ["2", "Write it to a temporary file in the same directory, and flush it to the physical disk.", "Same directory, so the rename in step 4 cannot cross a filesystem boundary."],
    ["3", "Roll the current workspace file into the version history.", "This is what NR-STO-06 restores from."],
    ["4", "Rename the temporary file over the workspace file.", "A rename is atomic. The file is either wholly the old contents or wholly the new - never half of each (NR-STO-05)."],
    ["5", "Only now report the save as done.", "NR-STO-04. Reporting a save that has not reached the disk is the one failure that would destroy trust in the whole feature."],
]
r = table(ws, r, ["Step", "Action", "Why"], safe, [7, 76, 62], wrap_cols=(2, 3))
r += 1
r = note(ws, r, "Power loss at any point leaves a readable workspace: before step 4 the old one, after it the new "
                "one. A stray temporary file is detected and removed at the next launch.")
r += 1

r = section(ws, r, "How this meets the existing edit model")
edit = [
    ["A pending edit", "Held exactly as today - snapshot taken before the first change.", "Nothing written to the workspace."],
    ["Save", "Commits as today, then writes the workspace.", "The existing Save is already the commit point, so persistence attaches to it with no new state."],
    ["Leave without change", "Reverts as today.", "Nothing is written, so nothing needs undoing on disk."],
    [f"{MARK_NEW}Autosave of PENDING edits", "Pending edits are journalled separately, not into the workspace.", "So an unexpected close can offer them back (NR-STO-07) without a half-finished edit ever becoming committed data."],
    [f"{MARK_NEW}Recovery", "At launch, a journal newer than the workspace prompts: keep these edits, or discard them.", "The user decides. Silently applying recovered edits would be worse than losing them."],
]
r = table(ws, r, ["Event", "Behaviour", "Note"], edit, [30, 60, 56], wrap_cols=(2, 3), mark_col=1)
r += 1
r = note(ws, r, "The provisional-edit model built for the web application - snapshot, commit on Save, revert on "
                "Leave without change - turns out to be exactly the seam persistence needs. No part of it changes.")
r += 1

r = section(ws, r, "Re-importing over a workspace that already holds data")
r = lines(ws, r, [
    "This is the one genuinely new decision the change forces, and it is the one most likely to lose somebody's",
    "work if it is decided carelessly. Somebody else maintains the source workbook; you will have hand-entered",
    "assignments in the workspace. A silent replace destroys them, and a silent merge hides that it happened.",
])
r += 1
imp = [
    ["Replace everything", "Simple.", "Destroys hand-entered data with no warning.", "Rejected"],
    ["Merge by key, source wins", "Keeps rows the import does not mention.", "Silently changes rows you edited deliberately.", "Rejected"],
    [f"{MARK_NEW}Show the differences, decide per sheet", "Nothing is lost without being seen. The user keeps authority over their own data.", "One more dialog to build and to pass through.", "PROPOSED - NR-IMP-02, decision N-07"],
    ["Refuse; require a new workspace", "Impossible to lose anything.", "Makes the ordinary case - refreshed project dates - painful.", "Rejected"],
]
r = table(ws, r, ["Option", "For", "Against", "Status"], imp, [40, 44, 44, 22], wrap_cols=(2, 3), mark_col=1)
r = note(ws, r, "Q-N05 asks you to confirm this. It is worth a moment's thought: it is the one place in the "
                "design where the wrong choice quietly loses work.")
r = legend(ws, r)

# ---- 06 Decisions ---------------------------------------------------------
ws, r = sheet(wb, "06_Decisions", "Engineering decisions",
              "N-ids belong to this plan. C-01..C-11 of the web plan govern the calculation and are inherited "
              "unchanged.")

dec = [
    ["N-01", "The desktop shell is Electron, packaged without an installer requirement.", "Reuses a verified engine and a verified UI whole, and can be tested in this repository before delivery. Size was the argument against it, and your instruction removes that argument. Reversible: only shell/desktop/ would change.", "CONFIRM"],
    ["N-02", "The workspace is prap-source-data JSON, not SQLite and not xlsx.", "Small data, an existing round-trip-tested format, and it keeps a workspace directly readable by an AI agent. See sheet 05.", "CONFIRM"],
    ["N-03", "Workspace writes are atomic, with the previous versions retained.", "The cost of persistence is that a bad write now destroys data that used to live safely in Excel. Atomic rename plus history is the standard answer.", "CONFIRM"],
    ["N-04", "Many workspaces, chosen by the user, with a recent list.", "You plan scenarios. A single implicit workspace would force overwriting one plan to explore another.", "CONFIRM"],
    ["N-05", "One shared engine, two shells - never two implementations.", "Two implementations of the same arithmetic will diverge, and the divergence will be discovered by someone who trusted the wrong number.", "CONFIRM"],
    ["N-06", "The HTML application is frozen in feature terms at its v1.0. Shared-engine fixes reach it; desktop-only features do not.", "It is finished and in service. Keeping it a build target protects it; keeping it feature-frozen keeps it from becoming a second thing to design.", "CONFIRM"],
    ["N-07", "Re-import shows a difference and lets the user decide per sheet.", "The only option that cannot silently lose hand-entered work. See sheet 05.", "CONFIRM"],
    ["N-08", "Pending edits are journalled separately from the committed workspace.", "So recovery can offer them back without a half-typed row ever becoming committed data.", "CONFIRM"],
    ["N-09", "No network access of any kind, including update checks and crash reporting.", "The tool is offline by requirement. Anything that opens a socket makes it a different kind of product in the eyes of corporate IT.", "CONFIRM"],
    ["N-10", "Engine parity between the applications is mandatory and tested; visual parity is best-effort and documented.", "The figures must agree or both tools are worthless. Whether a dialog looks native matters much less.", "CONFIRM"],
    ["N-11", "The desktop application reuses the web UI rather than being redesigned.", "You have reviewed that UI over 25 rounds. Redesigning it would discard that and give you two habits to hold.", "CONFIRM"],
    ["N-12", "A workspace from a newer application version is refused, not partially read.", "Reading unknown fields and writing them back out is how data quietly disappears.", "CONFIRM"],
]
r_start = r
r = table(ws, r, ["ID", "Decision", "Rationale", "Status"], dec, [8, 62, 74, 14], wrap_cols=(2, 3))
last = r_start + len(dec)
for rr in range(r_start + 1, last + 1):
    ws.cell(row=rr, column=4).fill = INPUT_FILL

dv = DataValidation(type="list", formula1='"CONFIRM,CONFIRMED,REJECTED,DEFERRED"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"D{r_start + 1}:D{last}")

r = note(ws, r, "Each of these is a decision I have taken provisionally so that Step 1 has something concrete to "
                "review. Change any of them in the Status column and the plan follows - none is expensive to "
                "reverse at this stage, and N-01 and N-02 become expensive after Gate N2.")
r += 1
r = section(ws, r, "Inherited and unchanged")
r = note(ws, r, "C-01 weights multiply. C-02 partial months pro-rated by calendar days. C-03 a missing override "
                "means person_weight applies. C-04 1.00 FTE = 160 h/month. C-05 FTE is the display unit. "
                "C-06 over/under-allocation judged on the person total. C-07 weights seeded then editable. "
                "C-08 a month belongs to the period containing its first day. C-09 identifier edits cascade. "
                "C-10 boundaries recomputed on milestone change unless hand-edited. C-11 ordered clipping, "
                "empty periods omitted. None of these is reopened by this plan.")

# ---- 07 WBS ---------------------------------------------------------------
ws, r = sheet(wb, "07_WBS_Schedule", "Work breakdown - five steps, five gates",
              "The same method as the web application: each step ends at a review gate, and the next starts only "
              "after that gate is passed.")

wbs = [
    ["N1", "N1.1", "Draft this plan.", f"PRAP_NewApp_Development_Plan_v{DOC_VERSION}.xlsx", "Complete - issued for review"],
    ["N1", "N1.2", "Requester reviews; answers Q-N01..Q-N11; confirms or changes decisions N-01..N-12.", "Reviewed mark-up", "Pending you"],
    ["N1", "N1.3", "Apply the answers and re-issue.", "Plan v0.2", "Not started"],
    ["N1", "GN1", "GATE N1 - development plan approved as the baseline.", "Plan v1.0", "Not started"],

    ["N2", "N2.1", "Split the source into core / ui / storage / shell-web, with a build step that re-emits app/PRAP.html. NO behaviour change.", "Source tree + rebuilt PRAP.html", "Not started"],
    ["N2", "N2.2", "Prove the refactor changed nothing: all 13 existing suites pass against the rebuilt HTML file, unmodified.", "Test evidence", "Not started"],
    ["N2", "N2.3", "Specify the storage interface and the workspace file format.", "Specification sheet 'Storage'", "Not started"],
    ["N2", "N2.4", "Specify the desktop shell: window, menus, dialogs, recent files, drag-and-drop, About.", "Specification sheet 'Shell'", "Not started"],
    ["N2", "N2.5", "Specify save safety, version retention, journalling and recovery.", "Specification sheet 'Persistence'", "Not started"],
    ["N2", "N2.6", "Specify the re-import difference dialog.", "Specification sheet 'Import'", "Not started"],
    ["N2", "N2.7", "Specify packaging, deployment and update.", "Specification sheet 'Deployment'", "Not started"],
    ["N2", "N2.8", "Traceability matrix: every NR-id to a specification section.", "Specification sheet 'Traceability'", "Not started"],
    ["N2", "GN2", "GATE N2 - programming specification approved.", "PRAP_NewApp_Specification_v1.0.xlsx", "Not started"],

    ["N3", "N3.1", "Desktop-specific UI design: menu structure, dialogs, the workspace-open screen, the recovery prompt, the difference view.", "Component list draft", "Not started"],
    ["N3", "N3.2", "List every deliberate divergence from the web UI, with its reason (NR-PAR-04).", "Divergence list", "Not started"],
    ["N3", "N3.3", "Requester reviews the design.", "Review comments", "Not started"],
    ["N3", "GN3", "GATE N3 - design and component list approved.", "PRAP_NewApp_Component_List_v1.0.xlsx", "Not started"],

    ["N4", "N4.1", "Desktop shell: application window, menu bar, native dialogs, window state.", "shell/desktop/", "Not started"],
    ["N4", "N4.2", "Filesystem storage adapter: open, save, atomic write, version history.", "storage/", "Not started"],
    ["N4", "N4.3", "Workspace lifecycle: new, open, save, save as, recent list, reopen last at launch.", "shell/desktop/", "Not started"],
    ["N4", "N4.4", "Journalling and crash recovery.", "storage/", "Not started"],
    ["N4", "N4.5", "Import into an occupied workspace: the difference view and the per-sheet decision.", "ui/", "Not started"],
    ["N4", "N4.6", "Parity suite: identical input through both applications, identical figures, findings and exports.", "tools/test_parity.py", "Not started"],
    ["N4", "N4.7", "Persistence suite: save, close, relaunch, verify; kill mid-write, verify; recover pending edits.", "tools/test_persist.py", "Not started"],
    ["N4", "N4.8", "Requester reviews against real data; refinements folded in.", "Updated code", "Not started"],
    ["N4", "GN4", "GATE N4 - application functionally complete.", "PRAP Desktop v0.9", "Not started"],

    ["N5", "N5.1", "Package for Windows; verify it launches without administrator rights.", "Installable package", "Not started"],
    ["N5", "N5.2", "Verify no socket is opened, offline, on a clean machine (NR-SEC-01).", "Test evidence", "Not started"],
    ["N5", "N5.3", "Install and test on a real company PC - the only place several of these requirements can be proven.", "Test evidence", "Pending you"],
    ["N5", "N5.4", "User guide: install, workspaces, import and export, backup, what to do if it will not start.", "User guide", "Not started"],
    ["N5", "N5.5", "Full pass over the traceability matrix; version alignment across both product lines.", "Traceability matrix", "Not started"],
    ["N5", "GN5", "GATE N5 - release.", "PRAP Desktop v1.0", "Not started"],
]
r_start = r
r = table(ws, r, ["Step", "Task", "Activity", "Deliverable", "Status"],
          wbs, [7, 9, 94, 40, 26], wrap_cols=(3, 4))
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
r += 1
r = note(ws, r, "Task N2.1 is deliberately first and deliberately dull. Until the engine is shared and the HTML "
                "file is proven unchanged by the sharing, every later task risks the finished product. No "
                "durations: the pace is set by review turnaround, as before.")

# ---- 08 Verification ------------------------------------------------------
ws, r = sheet(wb, "08_Verification", "How each claim will be proven",
              "Same standard as the web application: a claim is not made until something demonstrates it.")

ver = [
    ["The refactor changed nothing", "The 13 existing suites, unmodified, against the rebuilt app/PRAP.html.", "NR-PAR-03", "Automated, in this repository"],
    ["The two applications agree", "tools/test_parity.py - one dataset through both, comparing every person-month figure, every validation finding and both export files.", "NR-PAR-02", "Automated, in this repository"],
    ["Data survives closing", "tools/test_persist.py - import, save, close the application, relaunch, compare the model to what was saved.", "NR-STO-01", "Automated, in this repository"],
    ["A save is never half-written", "Kill the process during a write, relaunch, verify the workspace is wholly old or wholly new. Repeated across many timings.", "NR-STO-05", "Automated, in this repository"],
    ["Pending edits are recovered", "Kill the process with edits pending, relaunch, verify the prompt appears and both answers behave.", "NR-STO-07", "Automated, in this repository"],
    ["Re-import loses nothing", "Import a changed workbook over hand-entered data; verify every difference is shown and nothing changes without a decision.", "NR-IMP-02", "Automated, in this repository"],
    ["An old workspace still opens", "Open a workspace written by an earlier version; verify it loads and reports the upgrade.", "NR-DEP-03", "Automated, in this repository"],
    [f"{MARK_NEW}No network access", "Run packaged, offline, with socket activity observed for a full session.", "NR-SEC-01", "Automated on the build machine; repeated on the company PC"],
    [f"{MARK_NEW}It installs without admin rights", "Install and launch on a company-managed PC.", "NR-DEP-02", "ONLY provable by you, at N5.3"],
    [f"{MARK_NEW}It is allowed to run at all", "Launch the packaged application on a company-managed PC.", "R-N01", "ONLY provable by you - see the risk sheet"],
    ["The figures are right", "Inherited: the engine is already proven against the Python reference on all 1,225 person-months of the large dataset and 433 of the 10x10 dataset.", "Inherited", "Already done, and re-run by the parity suite"],
]
r = table(ws, r, ["Claim", "How it is proven", "Requirement", "Where"],
          ver, [34, 66, 14, 34], wrap_cols=(2, 4), mark_col=1)
r += 1
r = note(ws, r, "Two rows say ONLY PROVABLE BY YOU. Everything else in this project has been demonstrated before "
                "it was claimed; these two cannot be, from here. They are the reason risk R-N01 is rated as it is.")
r = legend(ws, r)

# ---- 09 Version control ---------------------------------------------------
ws, r = sheet(wb, "09_Version_Control", "Version control across two product lines")

r = section(ws, r, "Artifacts")
vc = [
    ["Desktop plan", "PRAP_NewApp_Development_Plan_v<ver>.xlsx", "docs/", "Sheet 01 of this document"],
    ["Desktop specification", "PRAP_NewApp_Specification_v<ver>.xlsx", "docs/", "Its own version-history sheet"],
    ["Desktop component list", "PRAP_NewApp_Component_List_v<ver>.xlsx", "docs/", "Its own version-history sheet"],
    ["Desktop application", "PRAP_Desktop_v<ver> (package)", "dist/", "About dialog and window title"],
    ["Workspace file", "<user's own name>.prap", "wherever the user keeps it", "Header block inside the file"],
    ["Web plan and its documents", "PRAP_Development_Plan_v<ver>.xlsx and siblings", "docs/", "Unchanged - their own sheets"],
    ["Web application", "app/PRAP.html", "app/", "APP_VERSION constant, shown in the footer"],
    ["Shared source tree", "core/, ui/, storage/, shell/", "repository root", "Git history"],
    ["Shared data contract", "schema_version in the Config sheet; format_version in the JSON", "templates/", "Unchanged at 5 and 1"],
]
r = table(ws, r, ["Artifact", "Naming", "Folder", "Where its version is recorded"],
          vc, [26, 52, 24, 42], wrap_cols=(2, 4))
r += 1

r = section(ws, r, "Rules")
vr = [
    ["The two product lines version independently.", "Desktop v1.0 and web v1.0 are unrelated numbers. Nothing forces them to move together."],
    ["The DATA contract versions once, for both.", "Schema version 5 and JSON format_version 1 are shared. A change to either is a change to both products and needs approval on both plans."],
    ["An engine fix is released to both.", "Fix in core/, re-verify against both, re-issue the HTML file as a point version and the desktop package as a point version. The fix is recorded in both version histories."],
    ["A desktop feature does not reach the web application.", "Decision N-06. The web application is feature-frozen; adding to it would reopen a closed gate."],
    ["Neither plan supersedes the other.", "Both remain live documents. The web plan's status stays exactly what it is today."],
]
r = table(ws, r, ["Rule", "Consequence"], vr, [56, 90], wrap_cols=(1, 2))

# ---- 10 Risks -------------------------------------------------------------
ws, r = sheet(wb, "10_Risks", "Risks and assumptions")

r = section(ws, r, "Risks")
risks = [
    [f"{MARK_NEW}R-N01", "Corporate policy blocks an unsigned packaged application, so it cannot be launched on the machine it was built for.", "Medium", "HIGH",
     "The single largest risk in this plan, and it cannot be tested from here. Q-N02 asks you to check with IT BEFORE Gate N1. Mitigation if it happens: the web application still works and still meets the original need - which is precisely why keeping it, as you instructed, is the right call. A code-signing certificate is an IT purchase, not a coding task."],
    [f"{MARK_NEW}R-N02", "The refactor to share the engine breaks the finished web application.", "Medium", "High",
     "Task N2.2 gates everything else on the 13 existing suites passing unmodified against the rebuilt HTML file. If they do not pass, the refactor is wrong and nothing proceeds. This is why N2.1 is the first task and carries no other change."],
    [f"{MARK_NEW}R-N03", "A workspace file is corrupted and a plan is lost - data that used to be safe in Excel because the application never wrote to it.", "Low", "HIGH",
     "This risk is CREATED by the persistence requirement. Atomic writes (N-03), retained versions (NR-STO-06) and the fact that Excel export still exists as an independent archive. The user guide will say plainly: export to Excel for anything you cannot afford to lose."],
    [f"{MARK_NEW}R-N04", "The two applications drift apart and disagree about the same data.", "Low", "HIGH",
     "Prevented structurally by N-05 - there is one engine - and detected by the parity suite at N4.6, which compares figures rather than trusting the structure."],
    [f"{MARK_NEW}R-N05", "Chromium security advisories oblige periodic rebuilds of an application that is otherwise finished.", "High", "Low",
     "Accepted, and inherent to the option chosen at N-01. The application is offline and opens no remote content (NR-SEC-02), so the realistic exposure is a crafted workspace file. Rebuild when a package update matters; the source does not change."],
    [f"{MARK_NEW}R-N06", "The Windows build cannot be verified in the development environment, which is Linux.", "High", "Medium",
     "Structural, not incidental. Mitigation: automated tests run against the Linux build of the same source, and N5.3 - your test on a real company PC - is a named, gating task rather than an afterthought. Any claim about Windows behaviour will be labelled as unverified until you verify it."],
    [f"{MARK_NEW}R-N07", "Two products double the maintenance from here on.", "Medium", "Medium",
     "Reduced by the architecture - most maintenance lands in the shared core and serves both - and by N-06 freezing the web application's feature set. It is not eliminated. It is the price of the bilingual arrangement, and worth stating plainly."],
    [f"{MARK_NEW}R-N08", "Users are unsure which of the two applications to use, or work in both and diverge.", "Medium", "Medium",
     "A one-page note in the user guide: the desktop application for planning work you keep, the web application for a quick look on a machine where nothing may be installed. A workspace exports to Excel, which imports into either, so no work is trapped."],
]
r = table(ws, r, ["ID", "Risk", "Likelihood", "Impact", "Mitigation"],
          risks, [9, 56, 12, 10, 66], wrap_cols=(2, 5), mark_col=1)

r = section(ws, r, "Assumptions")
assum = [
    ["A-N01", "Data volume stays as assumed by the web plan - up to about 100 projects and 1,000 people.", "Inherited, standing"],
    ["A-N02", "Windows 10 or 11 is the target. macOS and Linux are out of scope unless Q-N01 says otherwise.", "To confirm - Q-N01"],
    ["A-N03", "One person works on a given workspace at a time.", "Inherited A-06 - to confirm at Q-N06"],
    ["A-N04", "Package size is unconstrained.", "CONFIRMED by your instruction, 2026-08-13"],
    ["A-N05", "Both applications remain in service indefinitely; neither is a migration path away from the other.", "CONFIRMED by your instruction, 2026-08-13"],
    ["A-N06", "The source Excel workbook continues to be maintained by hand, by someone other than the tool.", "Inherited A-04, standing"],
    ["A-N07", "The user can copy a package into their own profile or a network share and run it from there.", "To confirm - Q-N02"],
]
r = table(ws, r, ["ID", "Assumption", "Status"], assum, [9, 108, 26], wrap_cols=(2,), mark_col=1)
r = legend(ws, r)

# ---- 11 Open questions ----------------------------------------------------
ws, r = sheet(wb, "11_Open_Questions", "Questions for review round 1",
              "Please answer in the Answer column. Q-N02 is the one worth asking someone else before you answer.")

qs = [
    ["Q-N01", "Deployment", "Which operating systems must this run on? Windows 10/11 only, or also macOS?", "Decides whether one package or three are built and tested.", ""],
    ["Q-N02", "Deployment", "Can you run a packaged application from your own user folder or a network share, without administrator rights and without it being code-signed? Worth asking your IT or desktop-support team rather than assuming.", "The highest-value question in this document. A 'no' changes decision N-01, and would make the web application the right long-term answer after all. See risk R-N01.", ""],
    ["Q-N03", "Deployment", "If signing IS required, is a company code-signing certificate obtainable, and by whom?", "An IT purchase with a lead time, not a development task. Better known now than at Gate N5.", ""],
    ["Q-N04", "Storage", "Where should workspaces live by default - your user profile, or a shared network drive?", "A network drive raises file-locking and latency questions that are cheap to design for now and expensive later.", ""],
    ["Q-N05", "Storage", "When you re-import a source workbook over a workspace that already holds your hand-entered data, what should happen? The proposal is to show the differences and let you decide per sheet.", "The one design choice that can silently lose work. See sheet 05.", ""],
    ["Q-N06", "Storage", "Will more than one person ever have the same workspace open at once?", "If yes, the format decision N-02 needs revisiting and locking has to be designed. If no, the plan is simpler and stays simpler.", ""],
    ["Q-N07", "Storage", "How many previous versions of a workspace should be retained, and for how long?", "Default proposed: the last 10. Retention costs only disk space.", ""],
    ["Q-N08", "Deployment", "How will updates reach you - a file you copy, a shared folder, or a software-distribution system?", "Decides whether the package needs to be distribution-system friendly, which affects how it is built.", ""],
    ["Q-N09", "Governance", "Does this tool fall under any internal validation or record-keeping obligation, given that it will now HOLD data rather than only display it?", "Holding data can change how a tool is treated in a regulated company. Cheaper to know at Step 1 than at release.", ""],
    ["Q-N10", "Scope", "Should the desktop application be able to open the same source workbook read-only, as the web application does, for a quick look without creating a workspace?", "A small feature, but it decides whether the workspace is mandatory or optional.", ""],
    ["Q-N11", "Naming", "What should the application be called on screen and in the Start menu? 'PRAP' or something else?", "Cosmetic, but it appears in the package name, the window title and the file association.", ""],
]
r_start = r
r = table(ws, r, ["ID", "Area", "Question", "Why it matters", "Answer"],
          qs, [9, 15, 62, 56, 40], wrap_cols=(3, 4, 5))
last = r_start + len(qs)
for rr in range(r_start + 1, last + 1):
    ws.cell(row=rr, column=5).fill = INPUT_FILL
r = note(ws, r, "Nothing here blocks drafting the specification except Q-N02, Q-N05 and Q-N06 - those three change "
                "the design rather than fill it in. The rest can be answered while Step 2 proceeds.")
r = legend(ws, r)

# ---- 12 Review log --------------------------------------------------------
ws, r = sheet(wb, "12_Review_Log", "Review log and approval",
              "This document's own log. The web application's review log is unaffected and stays where it is.")

log = [
    ["1", "Instruction 2026-08-13", "Change the program from a web application to a separate program type, like other open-source applications.", "Accepted as the purpose of this plan.", "Sheet 02 scope; NR-APP-01..07; decision N-01 selects the shell technology; sheet 04 records why the engine is not rewritten.", "Closed"],
    ["2", "Instruction 2026-08-13", "Change the data flow to keep imported data even after the application closes.", "Accepted.", "NR-STO-01..09; sheet 05 sets out the workspace model, the write protocol and the recovery behaviour; decisions N-02, N-03, N-08; risk R-N03 records the new risk this creates.", "Closed"],
    ["3", "Instruction 2026-08-13", "Use both ways - the web application goes final and stays usable; keep the HTML and its documents.", "Accepted, and it shapes the architecture.", "Sheet 02 states what is kept and untouched. Decisions N-05, N-06 and N-10 make the arrangement maintainable: one engine, the web application feature-frozen, parity tested rather than assumed. Risk R-N07 records the cost.", "Closed"],
    ["4", "Instruction 2026-08-13", "Develop the new application under a separate plan with a different name.", "Accepted.", "This document, PRAP-NAPP-PLAN-001, in its own version line from v0.1 with its own gates N1..N5. The web application plan is not amended.", "Closed"],
    ["5", "Instruction 2026-08-13", "Distribution size would be allowed.", "Accepted - and it decides an open question.", "Recorded as assumption A-N04. It removes the only strong argument against Electron, so decision N-01 selects it on the grounds of verifiability instead. Sheet 04 keeps Tauri as a documented later option.", "Closed"],
    ["6", "-", "Not requester input - raised while drafting.", "Two claims in this plan cannot be verified from the development environment.", "Whether the package is allowed to run on a company PC (R-N01), and whether it installs without administrator rights (NR-DEP-02). Both are marked on sheet 08 as provable only by you, and Q-N02 asks you to check the first before Gate N1 rather than after Gate N5.", "Open"],
]
r_start = r
r = table(ws, r, ["No.", "Source", "Input", "Response", "Action taken in v0.1", "Status"],
          log, [6, 22, 56, 40, 76, 12], wrap_cols=(3, 4, 5))
last = r_start + len(log)

dv3 = DataValidation(type="list", formula1='"Open,Accepted,Rejected,Deferred,Closed"', allow_blank=True)
ws.add_data_validation(dv3)
dv3.add(f"F{r_start + 1}:F{last}")

r = section(ws, r, "Approval - Gate N1")
appr = [[f"PRAP NewApp Development Plan v{DOC_VERSION}", "", "",
         "Awaiting review. To approve: answer Q-N01..Q-N11 on sheet 11, confirm or change decisions N-01..N-12 "
         "on sheet 06, and mark any requirement on sheet 03 you disagree with."]]
r_start2 = r
r = table(ws, r, ["Document", "Approver", "Date", "Decision"], appr, [34, 16, 14, 84], wrap_cols=(4,))
for cc in (2, 3):
    ws.cell(row=r_start2 + 1, column=cc).fill = INPUT_FILL

r = note(ws, r, "STEP N1 IS OPEN. Nothing is built until this plan is approved - including the refactor, which "
                "touches the finished web application and therefore waits for the same gate as everything else.")

wb.save(OUT)
print(f"Written: {OUT}")
