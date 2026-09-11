"""Generate the PRAP SERVER edition development plan workbook.

This is a THIRD plan, sibling to the other two. It does not supersede either:

    PRAP_Development_Plan_v*.xlsx         the single-file web application - FINISHED
    PRAP_NewApp_Development_Plan_v*.xlsx  the desktop application - IN SERVICE
    PRAP_Server_Development_Plan_v*.xlsx  a centrally hosted edition - PROPOSED

Everything in it is measured against the code that exists today rather than estimated
from a description of it. The figures on sheet 02 were counted, and the behaviour on
sheet 03 was run: two copies, one shared folder, one plan, and the claim watched from
both sides.

    python tools/build_server_plan.py

Output: docs/PRAP_Server_Development_Plan_v0.1.xlsx
"""

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.styles.borders import Side
from openpyxl.utils import get_column_letter

DOC_VERSION = "0.1"
DOC_STATUS = ("FOR DECISION. Nothing here is built. It is a costed proposal with its "
              "alternatives, so the choice between them can be made on evidence rather "
              "than on enthusiasm - including the choice to build none of it.")
DOC_DATE = "2026-09-11"
OUT = Path(__file__).resolve().parents[1] / "docs" / \
    f"PRAP_Server_Development_Plan_v{DOC_VERSION}.xlsx"

WEB_PLAN = "PRAP_Development_Plan_v2.51.xlsx"
NAPP_PLAN = "PRAP_NewApp_Development_Plan_v1.13.xlsx"

FONT = "Arial"
NAVY = "1F3864"
BLUE_HDR = "2F5597"
BAND = "F2F5FB"
YELLOW = "FFFF00"
GREEN = "C6E0B4"
ORANGE = "FCE4D6"
RED = "F8CBAD"
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
STOP_FILL = PatternFill("solid", fgColor=RED)

THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
WRAP_C = Alignment(vertical="top", wrap_text=True, horizontal="center")

MARK_KEEP = "[KEEP]"
MARK_CHG = "[CHANGE]"
MARK_NEW = "[NEW]"
MARK_ASK = "[ASK]"


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
            for mark, f in ((MARK_KEEP, NEW_FILL), (MARK_CHG, CHG_FILL),
                            (MARK_NEW, STOP_FILL), (MARK_ASK, INPUT_FILL)):
                if v.startswith(mark):
                    fill = f
                    data[mark_col - 1] = v[len(mark):].strip()
                    break
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


wb = Workbook()
wb.remove(wb.active)

# ---- 00 Cover -------------------------------------------------------------
ws = wb.create_sheet("00_Cover")
ws.sheet_view.showGridLines = False
ws["A1"] = "Project Resource Assignment Program (PRAP)"
ws["A1"].font = Font(name=FONT, size=20, bold=True, color=NAVY)
ws["A2"] = "Server Edition - Development Plan"
ws["A2"].font = Font(name=FONT, size=14, color=NAVY)

cover = [
    ("Document ID", "PRAP-SRV-PLAN-001"),
    ("Document type", "Development plan for a THIRD edition. For decision, not for build."),
    ("Version", f"v{DOC_VERSION}"),
    ("Status", DOC_STATUS),
    ("Issue date", DOC_DATE),
    ("Author", "Claude Code"),
    ("Reviewer", "Requester - not yet reviewed"),
    ("What is proposed",
     "One installation of PRAP, on a server, that everybody signs in to with their "
     "existing company account. Plans live in a database rather than in files. Who may "
     "see and change what is decided by the application rather than by folder "
     "permissions."),
    ("What exists today",
     "TWO editions, both finished and in service, and NEITHER is a server. The web "
     "edition is one HTML file with no server at all. The desktop edition runs on the "
     "user's own PC and listens on 127.0.0.1 only - measured: a connection from this "
     "machine's own network address to a listener bound the way PM_APP binds is "
     "REFUSED. Several people share work through a shared FOLDER and a lock file, not "
     "through a server."),
    ("The honest headline",
     "The half that decides the numbers moves across unchanged. The half that decides "
     "who may do what does not exist yet and is most of the work. See sheet 02 for the "
     "measured split and sheet 06 for what that costs."),
    ("Relationship to the other two plans",
     "PARALLEL, NOT SUCCESSOR. Neither existing edition is retired by this. Both keep "
     f"their own plans, gates and releases: {WEB_PLAN} and {NAPP_PLAN}."),
    ("Recommendation",
     "Read sheet 01 first. There are FOUR options and the cheapest one may be the right "
     "answer - it is not the one this document is titled after."),
    ("Repository", "Dan5050-now/project1"),
    ("Branch", "claude/project-resource-assignment-app-1vjdzh"),
    ("Supersedes", "Nothing."),
]
r = 4
for k, v in cover:
    ws.cell(row=r, column=1, value=k).font = BOLD_F
    c = ws.cell(row=r, column=2, value=v)
    c.font = BODY_F
    c.alignment = WRAP
    r += 1
ws.column_dimensions["A"].width = 34
ws.column_dimensions["B"].width = 112
for rr in range(4, r):
    ws.row_dimensions[rr].height = 44

r += 1
r = section(ws, r, "How to read this document")
r = lines(ws, r, [
    "  01  Four options, and what each one buys       <- start here; the decision is on this sheet",
    "  02  What can be reused, counted rather than guessed",
    "  03  What multi-user means today, measured by running it",
    "  04  The seven things a server edition needs that nothing today provides",
    "  05  The architecture, and the one seam that makes it possible",
    "  06  The work, in six stages with a gate at each",
    "  07  What it costs, and what it costs to keep",
    "  08  Risks, including the two that could stop the project",
    "  09  What is NOT proposed, and why",
    "  10  Questions only you can answer",
], mono=True)
r += 1
r = note(ws, r, "Every figure on sheet 02 was counted from the repository on the issue date. Every "
                "behaviour on sheet 03 was run, not read: two copies of the desktop edition against "
                "one shared folder, one plan, and the claim observed from both sides.")

# ---- 01 The options -------------------------------------------------------
ws, r = sheet(wb, "01_Options", "Four options, and what each one buys",
              "The document is called a server plan. That does not make a server the right answer, "
              "and the honest comparison is put first rather than last.")

r = section(ws, r, "The four")
opts = [
    [f"{MARK_KEEP}A. Change nothing", "0", "0",
     "Shared folder, one writer per plan, everybody trusted. WHAT IT ALREADY DOES: any number of "
     "readers, a named lock with a real message, a per-person data folder, one shared change log.",
     "A team of up to roughly 20 who trust each other, mostly work on different plans, and are on "
     "one file share.",
     "No sign-in, so the change log records a name somebody TYPED. No way to hide a plan from a "
     "colleague. One writer at a time."],
    [f"{MARK_CHG}B. Shared folder + real identity", "3-4 weeks", "Near zero",
     "Keep the file share. Take the name from the Windows account rather than asking for it, and "
     "record it that way in the change log. Nothing else changes.",
     "The same team, where the QUESTION being asked is 'who actually made this change' rather than "
     "'who may see this plan'.",
     "Still no permissions, still one writer at a time. But the audit record stops being "
     "self-declared, which is the single biggest gap for a regulated environment."],
    [f"{MARK_NEW}C. Server edition, read-heavy", "4-6 months", "A server, a database, a backup",
     "One installation. Everyone signs in with their company account. Plans in a database. "
     "Permissions. Full audit. EDITING IS STILL ONE WRITER AT A TIME per plan - the claim moves "
     "from a lock file into the database and gets better, but does not become simultaneous.",
     "30+ people, several departments, plans that not everyone should see, an audit somebody may "
     "have to defend.",
     "A server to run and patch. A database to back up. Someone owns it."],
    [f"{MARK_ASK}D. Server edition, simultaneous editing", "9-14 months", "The same, plus expertise",
     "All of C, plus two people editing one plan at the same time and seeing each other's changes.",
     "Only if 'two people must edit one plan at once' is a real, stated need rather than a nice "
     "idea.",
     "This is where the cost stops being linear. It is a different class of problem - see sheet 09, "
     "which explains why it is not recommended without that need being written down first."],
]
r = table(ws, r, ["Option", "Build effort", "Running cost", "What it is",
                  "Who it suits", "What it still will not do"],
          opts, [30, 13, 22, 62, 42, 52], wrap_cols=(4, 5, 6), mark_col=1)

r = section(ws, r, "The recommendation, and the reasoning behind it")
r = lines(ws, r, [
    "START WITH B, AND DECIDE C ON EVIDENCE.",
    "",
    "B is three or four weeks and removes the one gap that is genuinely serious today: the change log records",
    "a name the user typed, so it is a record of what somebody SAID they did. In a regulated setting that is",
    "the difference between an audit trail and a note. Taking the name from the Windows account fixes it",
    "without a server, without a database, and without anybody having to own a service.",
    "",
    "C is the right answer IF - and the 'if' is the whole point - one of these is true:",
    "",
    "    * more than about twenty people use it, or several departments do;",
    "    * some plans must not be visible to everyone who can reach the file share;",
    "    * somebody outside the team will ask to see the audit trail and expect it to be defensible;",
    "    * the file share is going away, or people need it from outside the office.",
    "",
    "If none of those is true, C buys a server to look after and very little else. That is a real answer and",
    "it is not a defeatist one: the existing editions were built for this team and they fit it.",
    "",
    "D is not recommended unless simultaneous editing of ONE plan is a written requirement. Sheet 09.",
], mono=True)
r += 1
r = note(ws, r, "B is not a step towards C that has to be thrown away. The identity work in B is the "
                "same identity work C needs, done against Windows instead of against a database - "
                "sheet 05 keeps them behind one seam on purpose.")

# ---- 02 What can be reused ------------------------------------------------
ws, r = sheet(wb, "02_Reuse", "What can be reused, counted rather than guessed",
              "Counted from src/ on the issue date. The point of this sheet is that the expensive half "
              "is already done and the cheap-sounding half is not.")

reuse = [
    [f"{MARK_KEEP}core/", "10", "3,669",
     "THE WHOLE CALCULATION. Reading a workbook, deriving periods, the standards, the role factors, "
     "sharing a month out, the manual figures, every validation rule, the change-log record, the "
     "results export.",
     "MOVES UNCHANGED. It already touches no browser and no file - tools/test_layers.py fails the "
     "build if it ever does. It runs as-is in a browser, in the desktop shell, and would run as-is "
     "on a server."],
    [f"{MARK_KEEP}ui/", "11", "4,795",
     "EVERY SCREEN. All four tabs, both source-data tabs, the charts, the tables, the editing, the "
     "findings report, the estimation panels, Standard vs staffed.",
     "MOVES ALMOST UNCHANGED. It draws what core/ decides. What changes is where the data arrives "
     "from, which is one layer below it."],
    [f"{MARK_CHG}storage/", "6", "763",
     "Reading and writing bytes. Two implementations already exist behind one seam - the browser's "
     "and the desktop's.",
     "A THIRD IMPLEMENTATION. This is the seam the server plugs into, and the fact that there are "
     "already two proves the seam is real rather than claimed."],
    [f"{MARK_NEW}shell/", "13", "3,833",
     "The window around the application: menus, file dialogs, the local HTTP bridge, the claim "
     "heartbeat.",
     "REPLACED for the server. Roughly a third is reusable in spirit; the rest assumes one user on "
     "one machine."],
    [f"{MARK_NEW}(does not exist)", "-", "0",
     "Sign-in, sessions, permissions, a database, concurrent writes, server administration.",
     "ALL NEW. This is the work. See sheet 04."],
]
r = table(ws, r, ["Layer", "Files", "Lines", "What is in it", "What happens to it in a server edition"],
          reuse, [22, 8, 9, 66, 62], wrap_cols=(4, 5), mark_col=1)

r = section(ws, r, "What that adds up to")
r = lines(ws, r, [
    "    8,464 lines   core/ + ui/      move across essentially unchanged     65% of what exists",
    "      763 lines   storage/         gains a third implementation           6%",
    "    3,833 lines   shell/           replaced                              29%",
    "        0 lines   the server half  does not exist yet                    the work",
    "",
    "The temptation is to read '65% reusable' as '65% done'. It is not. The 8,464 lines are the part that was",
    "hard to get RIGHT - four independent implementations agree on every person-month, and 33 test suites hold",
    "them there. The missing part is not hard to get right in that sense; it is simply a lot of it, and every",
    "line of it is the kind that has to be correct on a bad day rather than a good one.",
], mono=True)
r += 1
r = note(ws, r, "The four-implementations rule is what makes the reuse claim safe. core/ is checked "
                "against tools/prap_io.py, tools/verify_source_workbook.py and test_app.py's own "
                "reference on every run. A server edition becomes a fifth reader of the same "
                "contract, not a fork of the engine.")

# ---- 03 Multi-user today --------------------------------------------------
ws, r = sheet(wb, "03_Today", "What multi-user means today, measured by running it",
              "Two copies of the desktop edition, one shared folder, one plan, watched from both "
              "sides. This is what the team has now, stated accurately so the proposal is judged "
              "against the truth rather than against a straw man.")

r = section(ws, r, "What was run")
r = lines(ws, r, [
    "    Two installations, two accounts (kim, park), both started with --data=<one shared folder>.",
    "    Kim saved a plan into the shared folder. Kim began editing. Park then tried to edit the same plan.",
], mono=True)
r += 1

today = [
    ["Separate data folders", "WORKS",
     "kim got users/kim, park got users/park, each with their own settings, recent list and backups. "
     "Neither can overwrite the other's.", "Observed"],
    ["One writer at a time", "WORKS",
     "Kim's claim succeeded. Park's was refused with: \"Kim Soo-jin (DM) is editing this plan. Started "
     "09:18, active now.\" and the time it frees.", "Observed"],
    ["Reading is never blocked", "WORKS",
     "Park could still stat and open the plan while Kim held it. Refusing a READ would make a lock a "
     "punishment rather than a safeguard.", "Observed"],
    ["The lock cannot be won twice", "WORKS",
     "It is taken with an exclusive create, so the file system picks exactly one winner. Read-then-write "
     "would let two sessions both believe they had it.", "By construction, and unit-tested"],
    ["Taken at the first EDIT", "WORKS",
     "Not at open. Somebody who glances at a plan and goes to lunch does not block the team.", "By design"],
    ["Alive vs abandoned", "WORKS",
     "A 30-second heartbeat answers 'is the holder still there', a 30-minute expiry answers 'may somebody "
     "take over'. Two different questions, two different numbers, so the message can say WHICH.", "Observed"],
    ["Your own crashed session", "WORKS", "Comes back to you at once rather than after thirty minutes.",
     "Unit-tested"],
    ["One shared change log", "WORKS",
     "audit/ sits beside users/, so everyone's entries are in one file in time order.", "Observed"],
    [f"{MARK_NEW}Sign-in", "ABSENT",
     "There is none. The whole source was searched: no password, no account, no session. The only hit "
     "for 'password' is Excel sheet protection, which the code itself calls a guard rail rather than "
     "security.", "Searched"],
    [f"{MARK_NEW}Identity is verified", "ABSENT",
     "You type your name and it is believed. The desktop plan says so in as many words (NR-USR-08): "
     "'This identity is DECLARED, not verified.' Honest, and a real limit.", "Stated in the plan"],
    [f"{MARK_NEW}Permissions", "ABSENT",
     "Anyone who can open the folder can open and change any plan in it. The only access control is "
     "the file share's own.", "By design"],
    [f"{MARK_NEW}Reachable over the network", "ABSENT",
     "The desktop edition binds 127.0.0.1 only. Measured: a connection to a listener bound that way, "
     "from this machine's own network address, is REFUSED.", "Measured"],
    [f"{MARK_NEW}Two people editing one plan", "ABSENT",
     "Not possible, and not a bug: it is the sharing model the desktop plan was written to.", "By design"],
]
r = table(ws, r, ["Capability", "Today", "What was found", "How it is known"],
          today, [30, 12, 84, 26], wrap_cols=(3, 4), mark_col=1)
r = note(ws, r, "Green rows are what a server edition must not make worse. Several of them - the "
                "claim's two clocks, the named message, reading never being blocked - are better "
                "thought through than the default behaviour of most systems that do have logins.")

# ---- 04 What is missing ---------------------------------------------------
ws, r = sheet(wb, "04_Gaps", "The seven things a server edition needs that nothing today provides",
              "Each one is a piece of work, not a setting. They are ordered by how much of the rest "
              "depends on them.")

gaps = [
    ["1", "Sign in as yourself",
     "Company Windows/AD accounts, so nobody types or remembers a new password. Single sign-on where "
     "the browser can do it; a sign-in page where it cannot.",
     "Everything else rests on it. Permissions and a defensible audit trail are both meaningless "
     "without it.", "3-4 weeks"],
    ["2", "Sessions",
     "Staying signed in across pages, timing out sensibly, signing out, and not being borrowable by a "
     "hostile page.",
     "Small in effort, large in consequence if it is wrong. Uses the framework's own, never a "
     "hand-rolled one.", "1-2 weeks"],
    ["3", "Who may do what",
     "At minimum three levels: read, edit, administer. Probably also per-department or per-project "
     "visibility.",
     "This is a POLICY question before it is a programming one, and it is question Q-S02 on sheet 10. "
     "The code is straightforward once the rules are decided.", "3-5 weeks"],
    ["4", "A database instead of files",
     "The eleven sheets become tables. Reading and writing go through the same seam storage/ already "
     "defines, so core/ never learns that anything changed.",
     "The schema already exists and is already enforced - the workbook contract is checked against "
     "the plan, the specification and the template on every build. This is transcription, not design.",
     "4-6 weeks"],
    ["5", "Several people writing at once",
     "The claim moves out of a lock file and into the database, where it gains things a file cannot "
     "have: it cannot be orphaned by a crashed PC, and it can be released by an administrator.",
     "For option C this is the SAME single-writer model, done better. For option D it is a different "
     "problem - sheet 09.", "2-3 weeks for C"],
    ["6", "An audit trail that means something",
     "The change log already records what changed, when, and against which record. What it gains is a "
     "user who was authenticated rather than one who typed a name, and a store nobody can quietly edit.",
     "MOSTLY ALREADY BUILT. This is the cheapest of the seven and the one with the highest value per "
     "week, which is why option B on sheet 01 does it on its own.", "1-2 weeks"],
    ["7", "Running it",
     "Install, upgrade, back up, restore, monitor, and a named person who owns it.",
     "Not programming, and the part most often left out of an estimate. A service nobody owns is a "
     "service that stops working on a Friday.", "2-3 weeks, then forever"],
]
r = table(ws, r, ["#", "What", "What it means", "Why it is where it is in the order", "Effort"],
          gaps, [5, 30, 62, 62, 16], wrap_cols=(3, 4, 5))

r = section(ws, r, "What is NOT on this list, because it is already done")
r = lines(ws, r, [
    "    The calculation, all of it, including the four-implementation agreement that keeps it honest.",
    "    Every screen, chart and table.",
    "    Every validation rule, including the ones added this year: V-31 to V-34.",
    "    The change log's CONTENT - what changed, when, against which record, and by which name.",
    "    The data contract: eleven sheets, 93 columns, checked against three documents on every build.",
    "    Reading and writing Excel, which a server edition still needs for import and export.",
], mono=True)

# ---- 05 Architecture ------------------------------------------------------
ws, r = sheet(wb, "05_Architecture", "The architecture, and the one seam that makes it possible",
              "Why this is a plug rather than a rewrite - and the one place where that claim is true "
              "rather than convenient.")

r = section(ws, r, "Today, both editions")
r = lines(ws, r, [
    "     ui/          draws it            same code in both editions",
    "     core/        decides it          same code in both editions - no DOM, no file access, enforced by a test",
    "     ------------------------------- THE SEAM",
    "     storage/     bytes in and out    web: the browser's download.  desktop: a local HTTP call to Python.",
], mono=True)
r += 1
r = section(ws, r, "A server edition")
r = lines(ws, r, [
    "     ui/          unchanged",
    "     core/        unchanged",
    "     ------------------------------- THE SAME SEAM",
    "     storage/     a THIRD implementation: an HTTPS call to the server, carrying the session",
    "                            |",
    "     server       sign-in, sessions, permissions, the database, the audit store   <- all new",
    "",
    "The seam is not a hopeful description written for this document. It is load-bearing today: two",
    "implementations already sit behind it, and tools/test_layers.py fails the build if core/ so much as",
    "mentions a browser. A third implementation is a thing the design already expects.",
], mono=True)
r += 1

r = section(ws, r, "What the server must answer")
r = note(ws, r, "The desktop shell exposes 28 operations to the page. A server edition implements the "
                "same list, with three differences, and the page cannot tell which shell it is "
                "talking to - which is what makes one set of screens serve all three editions.")
seam = [
    ["Stays the same", "ws/open, ws/save, ws/saveAs, ws/recent, ws/versions, ws/restore, ws/stat, "
     "file/openSource, file/export, audit/append",
     "The same question, answered from a database instead of a folder."],
    ["Changes meaning", "identity/get, identity/set, identity/suggest",
     "Stops being 'what did you type' and becomes 'who are you signed in as'. identity/set largely "
     "disappears - you cannot set who you are."],
    ["Changes mechanism", "claim/take, claim/read, claim/release, claim/holds",
     "The same four questions, answered by a row in the database rather than a lock file. The 30-second "
     "and 30-minute clocks carry over intact - they are good answers and they were hard-won."],
    ["Disappears", "caps, paths, fs/list, ws/openDialog, quit, app/alive, app/bye",
     "All of them are about one PC: where its folders are, its file dialogs, and whether its console "
     "window should close. A server has none of those."],
    ["Is added", "auth/signin, auth/signout, auth/whoami, perm/check, admin/*",
     "The seven things on sheet 04."],
]
r = table(ws, r, ["", "Operations", "What happens to them"], seam, [18, 62, 76], wrap_cols=(2, 3))

r = section(ws, r, "One decision that is worth taking early")
r = lines(ws, r, [
    "PYTHON ON THE SERVER, not a rewrite in something else.",
    "",
    "The desktop shell and its storage are already 1,806 lines of Python doing the file and claim work, and",
    "tools/prap_io.py is another 1,401 - an independent Python implementation of the whole calculation, which",
    "exists to keep the browser honest. A Python server inherits both. A different language would mean writing",
    "a FOURTH calculation implementation and then proving it agrees with the other three - which is exactly the",
    "work the four-implementation rule exists to make visible, and that nobody should take on by accident.",
], mono=True)

# ---- 06 The work ----------------------------------------------------------
ws, r = sheet(wb, "06_Work", "The work, in six stages with a gate at each",
              "Ordered so that something usable exists early and the riskiest question is answered "
              "first. Each gate is a point at which stopping is a reasonable outcome.")

work = [
    ["S1", "Prove sign-in works here", "2-3 weeks",
     "One page, on a server, that says who you are using your company account. No PRAP in it at all.",
     "GATE: does single sign-on work on this network, with this browser, under this IT policy? If it "
     "does not, options C and D are far more expensive than this plan says and the decision should be "
     "revisited before anything else is built."],
    ["S2", "The database", "4-6 weeks",
     "The eleven sheets as tables. Import an existing workbook into it and export the same workbook "
     "back out, byte-comparable.",
     "GATE: a plan that goes in comes out identical, and tools/prap_io.py computes the same figures "
     "from the database as from the file. The four-implementation rule, applied to the new store."],
    ["S3", "Read-only for everybody", "3-4 weeks",
     "Everyone signs in and can SEE every plan. No editing yet.",
     "GATE: THE FIRST USABLE THING. Genuinely useful on its own - most people only ever look - and it "
     "is a sensible place to stop if the rest is deferred."],
    ["S4", "Editing, one writer at a time", "4-5 weeks",
     "The claim moves into the database. Editing, saving, the change log against an authenticated user.",
     "GATE: two people, one plan, the second is refused with a message naming the first. The same test "
     "that was run against the shared folder for sheet 03, now against the server."],
    ["S5", "Permissions", "3-5 weeks",
     "Read / edit / administer, and whatever visibility rules Q-S02 settles on.",
     "GATE: somebody without permission cannot see a plan - checked by asking the SERVER directly, not "
     "by checking that a button is hidden."],
    ["S6", "Making it somebody's job", "2-3 weeks",
     "Install, upgrade, back up, restore, monitor. Written down and rehearsed.",
     "GATE: a restore from backup is performed, by somebody other than the author, from the written "
     "instructions alone."],
]
r = table(ws, r, ["", "Stage", "Effort", "What is built", "The gate"],
          work, [5, 30, 12, 58, 74], wrap_cols=(4, 5))

r = section(ws, r, "Total, and what the range means")
r = lines(ws, r, [
    "    18 to 26 weeks of build, plus review time between gates.  Four to six months for option C.",
    "",
    "The range is not padding. The lower end assumes single sign-on works first time (S1), that the answer to",
    "Q-S02 is simple, and that a server is available when it is needed. The upper end assumes none of those.",
    "S1 exists to move that uncertainty to the front, where it costs two weeks to discover instead of four",
    "months.",
], mono=True)

# ---- 07 Cost --------------------------------------------------------------
ws, r = sheet(wb, "07_Cost", "What it costs, and what it costs to keep",
              "The second column is the one that is usually missed, and it is the one that never stops.")

cost = [
    ["Build", "Option B: 3-4 weeks. Option C: 4-6 months. Option D: 9-14 months.",
     "One-off. The figures on sheet 06."],
    ["A server", "One Windows or Linux server, or a virtual machine. Modest - this is not a busy system.",
     "Ongoing. Someone patches it."],
    ["A database", "PostgreSQL or SQL Server, whichever your IT already runs and already backs up.",
     "Ongoing. Prefer the one they ALREADY back up; a database nobody backs up is worse than files."],
    ["A certificate", "HTTPS. Usually free from your own IT, but it expires and somebody must renew it.",
     "Ongoing, and the classic cause of an outage nobody predicted."],
    ["An owner", "A named person who is responsible for it being up.",
     "Ongoing, and NOT OPTIONAL. This is the line most likely to be left out of a business case and the "
     "one most likely to be the reason it fails."],
    ["Backups", "Of the database, tested by restoring, not merely configured.",
     "Ongoing. A backup that has never been restored is a hope."],
    ["Losing something", "Offline use. Today both editions work with no network at all.",
     "Permanent. A server edition does not work on a train. Whether that matters is Q-S04."],
]
r = table(ws, r, ["", "What", "When it is paid"], cost, [20, 76, 66], wrap_cols=(2, 3))

r = section(ws, r, "The comparison worth making")
r = lines(ws, r, [
    "Option B costs three or four weeks, once, and nothing thereafter. It closes the audit gap - the change log",
    "stops recording a typed name and starts recording an authenticated one - and it changes nothing else.",
    "",
    "Option C costs four to six months, and then costs a server, a database, a certificate and a person, for as",
    "long as it is used.",
    "",
    "That difference is worth paying when the four conditions on sheet 01 hold. It is not worth paying to fix an",
    "audit trail, because B fixes that. Deciding which problem is actually being solved is the whole decision.",
], mono=True)

# ---- 08 Risks -------------------------------------------------------------
ws, r = sheet(wb, "08_Risks", "Risks, including the two that could stop the project")

risks = [
    ["R-S01", "Single sign-on is not permitted, or does not work on this network", "HIGH", "HIGH",
     "IT policy may not allow a new application to use company accounts, or may require a review "
     "that takes months.",
     "STAGE S1 EXISTS FOR THIS. Two weeks, before anything else, to find out. If the answer is no, "
     "the whole basis of options C and D changes and this plan should be reissued rather than "
     "continued."],
    ["R-S02", "No server is available, or getting one takes longer than building the software",
     "MEDIUM", "HIGH",
     "In many companies provisioning is slower than development, and it is not on the development "
     "team's critical path until suddenly it is.",
     "Ask for it on day one, before S1. It is a lead-time item, not a technical one."],
    ["R-S03", "Nobody owns the running service", "MEDIUM", "HIGH",
     "It works for a year, then the certificate expires or a disk fills, and there is no one whose "
     "job it is.",
     "Name the owner BEFORE S1 starts, not at S6. If no name can be given, that is strong evidence "
     "for option B."],
    ["R-S04", "The calculation quietly drifts from the other editions", "LOW", "HIGH",
     "A server edition that computed slightly different figures would be worse than no server "
     "edition at all.",
     "The four-implementation rule and 33 test suites already exist and already run on every build. "
     "The server becomes a fifth reader of the same contract. S2's gate tests exactly this."],
    ["R-S05", "Permissions turn out to be complicated", "MEDIUM", "MEDIUM",
     "'Read, edit, administer' is simple. 'Only the study lead and their department, except during "
     "close-out' is not.",
     "Q-S02 asks for the rules in words before S5 begins. If the answer is long, S5 grows and this "
     "plan should say so rather than absorb it quietly."],
    ["R-S06", "Offline use is missed after it is gone", "MEDIUM", "LOW",
     "Both editions work today with no network. A server edition does not.",
     "Keep the desktop edition in service. The two are not mutually exclusive, and nothing in this "
     "plan retires it."],
    ["R-S07", "The project is chosen for the wrong reason", "MEDIUM", "MEDIUM",
     "'Server' sounds more professional than 'shared folder'. It is not automatically better, and it "
     "costs a great deal more.",
     "Sheet 01 states the four conditions. If none holds, the correct answer is B or A, and saying so "
     "is part of this plan's job."],
]
r = table(ws, r, ["ID", "Risk", "Likelihood", "Impact", "What it looks like", "What is done about it"],
          risks, [8, 48, 12, 10, 58, 66], wrap_cols=(2, 5, 6))

# ---- 09 Not proposed ------------------------------------------------------
ws, r = sheet(wb, "09_Not_Proposed", "What is NOT proposed, and why",
              "Naming what is deliberately left out is as much a part of a plan as naming what is in it.")

out_of = [
    ["Two people editing one plan at the same time",
     "It is a different class of problem from everything else here. Either every change is sent as it is "
     "typed and merged live, or two people's edits have to be reconciled afterwards. The first is weeks of "
     "work per SCREEN; the second asks a user to resolve a conflict, which is a thing most people do badly "
     "under time pressure. Neither is worth it unless the need is real.",
     "Ask for it in writing, with an example of the situation it solves. Then it becomes option D and this "
     "plan is reissued."],
    ["Retiring either existing edition",
     "Both work, both are finished, and both cover cases a server does not: a laptop with no network, and a "
     "machine where IT will not permit a listener.",
     "Nothing. They stay."],
    ["A mobile version",
     "The screens are dense tables and wide charts. A phone-sized version is a redesign, not a reflow.",
     "Out of scope. Raise separately if wanted."],
    ["Rewriting the calculation",
     "It is correct, it is agreed by four independent implementations, and 33 test suites hold it there. "
     "Touching it would be the single most expensive mistake available.",
     "Explicitly forbidden by this plan."],
    ["Changing the data model",
     "The eleven sheets are checked against the plan, the specification and the template on every build. "
     "The database mirrors them.",
     "Explicitly out of scope for the server work. Change it on its own line if it needs changing."],
    ["Anything that weakens what exists",
     "Today: reading is never blocked, a lock names its holder and says when it frees, your own crashed "
     "session comes straight back. Those are good answers arrived at by argument.",
     "Carried into the server edition as requirements, not reinvented."],
]
r = table(ws, r, ["Not proposed", "Why", "What would change that"],
          out_of, [46, 82, 56], wrap_cols=(1, 2, 3))

# ---- 10 Questions ---------------------------------------------------------
ws, r = sheet(wb, "10_Questions", "Questions only you can answer",
              "Every one of these changes the plan. They are in the order they need answering.")

qs = [
    ["Q-S01", f"{MARK_ASK}Which of the four options on sheet 01?",
     "It decides whether the rest of this document is relevant. B is recommended as a first step "
     "whatever the eventual answer, because it is useful on its own and is not wasted if C follows.",
     "Before anything"],
    ["Q-S02", f"{MARK_ASK}Who should be able to see and change what?",
     "In your own words, with an example: 'a data manager can edit plans in their own department and "
     "read the rest' is enough to start. This sizes S5 and it cannot be guessed.",
     "Before S5, ideally before S1"],
    ["Q-S03", f"{MARK_ASK}How many people, and in how many departments?",
     "Under 20 in one team points at A or B. Thirty or more across departments points at C. This is "
     "the single strongest signal in the decision.",
     "Before Q-S01 can be answered"],
    ["Q-S04", f"{MARK_ASK}Does anyone need it away from the office network?",
     "A server edition needs the network. If people work on a plan on a train, the desktop edition "
     "stays whatever else is decided.",
     "Before Q-S01"],
    ["Q-S05", f"{MARK_ASK}Who would own the running service?",
     "A name, not a team. If there is no name, that is a strong argument for B.",
     "Before S1"],
    ["Q-S06", f"{MARK_ASK}What does your IT already run and already back up?",
     "Use whatever that is. A database your IT already backs up is worth more than the one that is "
     "technically nicer.",
     "Before S2"],
    ["Q-S07", f"{MARK_ASK}Is there a compliance requirement written down anywhere?",
     "If an auditor will ask to see the change log, that raises the value of authenticated identity - "
     "which is option B - and may make it urgent rather than merely worthwhile.",
     "Before Q-S01"],
]
r = table(ws, r, ["ID", "Question", "Why it matters and what changes with the answer", "When it is needed"],
          qs, [8, 52, 92, 24], wrap_cols=(2, 3, 4), mark_col=2)

r = section(ws, r, "If only one of these is answered")
r = lines(ws, r, [
    "Answer Q-S03: how many people, in how many departments.",
    "",
    "Everything else follows from it. A team of twelve in one department does not need a server, and building",
    "one for them would be four months spent to make something slightly worse than what they already have.",
    "Forty people across three departments will not be served by a shared folder for much longer, and the",
    "question is only when to start.",
], mono=True)

r += 1
r = section(ws, r, "Legend")
for fill, txt in ((NEW_FILL, "Green  = exists today and moves across, or already works"),
                  (CHG_FILL, "Orange = exists today but changes"),
                  (STOP_FILL, "Red    = does not exist; this is the work"),
                  (INPUT_FILL, "Yellow = needs your decision before the work can proceed")):
    c = ws.cell(row=r, column=1, value=txt)
    c.font = BODY_F
    c.fill = fill
    r += 1

wb.save(OUT)
print(f"Written: {OUT}")
print(f"  {len(wb.sheetnames)} sheets: {', '.join(wb.sheetnames)}")
