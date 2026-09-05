"""Build the Python shell of Project Management APP from the same src/ as the rest.

    core/ + ui/ + shell/python/ + storage/python/   ->   dist/PM_APP_py/

Everything above the storage line is the web application, built from the same parts
in the same order (decision N-05). What differs is the shell around it, and one
thing inside it:

  * the window chrome - a menu drawn in the page, because there is no Electron menu
    bar to draw one for us, plus the status strip and the file browser
  * a bridge that routes the file operations through 127.0.0.1 instead of a picker
  * NO src/storage/web/load.js. That file is the browser's file interface, which is
    the thing a company control stops on the target machine (R-N21). It is left out
    rather than left in and broken.

storage/web/export.js stays exactly where it is: a download is not an upload, the
control does not touch it, and every check it performs before writing a workbook is
worth keeping.

    python tools/build_python_app.py            build into dist/PM_APP_py
    python tools/build_python_app.py --zip      and package it for e-mail

Output: dist/PM_APP_py/ and, with --zip, dist/PM_APP_python_v<version>.zip
"""

import argparse
import hashlib
import importlib.util
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "dist" / "PM_APP_py"
VERSION = "1.10"

_spec = importlib.util.spec_from_file_location("build_app", ROOT / "tools" / "build_app.py")
build_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_app)

# The browser's file interface. Left out on purpose - see the module docstring.
WEB_ONLY = {"storage/web/load.js"}

# src path -> package path. The repository keeps layers side by side; a shipped
# Python program needs a package tree, and this is the whole of the difference.
MODULES = {
    "storage/python/timefmt.py": "pmapp/storage/timefmt.py",
    "storage/python/workspace.py": "pmapp/storage/workspace.py",
    "storage/python/claim.py": "pmapp/storage/claim.py",
    "shell/python/paths.py": "pmapp/shell/paths.py",
    "shell/python/files.py": "pmapp/shell/files.py",
    "shell/python/server.py": "pmapp/shell/server.py",
    "shell/python/launch.py": "pmapp/shell/launch.py",
}

ENTRY = '''"""Project Management APP - start here.

Double-click this file, or run it from a command prompt:

    python PM_APP.py

It opens in your browser, at an address only this machine can reach. Keep the
console window open while you work; closing it stops the application.
"""

import os
import sys

if sys.version_info < (3, 9):
    raise SystemExit(
        "Project Management APP needs Python 3.9 or newer.\\n"
        f"This is Python {sys.version.split()[0]}.")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pmapp.shell.launch import main            # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
'''

READ_ME = """PROJECT MANAGEMENT APP - Python edition
=======================================

WHAT IS NEW IN 1.10

  * THE POP-UPS NOW SAY WHICH PROJECT PERIOD A MONTH IS IN. Every figure in
    this application is

        standard FTE  x  period weight  x  the part of the month the project ran

    so the period is the row of your plan that decided how big the number is -
    and it was the one thing the pop-ups did not tell you. Hover any month now
    and it says, for example:

        Project period: Conduct (final) - weight x1.23

    On four charts: 'Monthly demand by project' and 'Monthly demand by person'
    on Overall, and 'Utilisation' on each of the two source-data tabs.

  * WHERE ONE BAR COVERS SEVERAL PROJECTS - a person's month is made of all the
    projects they are on - the period is shown against EACH PROJECT rather than
    once for the bar, because they need not be in the same period as each other.

  * A month in no period says so, and names V-12. Those months are weighted 1.00
    by default, which is worth knowing rather than hiding.

  * No figure changes. The period shown is read from the calculation itself, so
    it is always the period the number beside it was worked out from.


WHAT IS NEW IN 1.9

  * A CHANGE LOG, WRITTEN TO DISK AT EVERY SAVE. Every change you save is
    recorded and appended to a CSV file in a new `audit` folder beside your
    workspaces:

        data/<your account>/audit/PRAP_changes_YYYY-MM.csv

    One file a month. The header is written when the file is created and rows
    are added under it - nothing is ever rewritten, so the file only grows and
    an interrupted save cannot damage what is already in it.

    Each line carries the time in UTC, your name, what kind of change it was,
    the sheet, WHICH RECORD (PRJ-004, or PSN-012 | 2027-03 - the record's own
    identifier, not a row number, because inserting a row renumbers everything
    under it), the column, and the value before and after.

    Your name comes from your Windows account. You are not asked.

  * AND WHAT THE APPLICATION REPORTED. A second file, PRAP_findings_YYYY-MM.csv,
    records the errors and warnings standing at each save - including which of
    them you were asked about and chose to keep, which is the line in a log that
    records a DECISION rather than a keystroke.

  * Both open in Excel by double-clicking. They are written with a UTF-8 marker
    so a Korean name is not mangled.

  * IF THE LOG CANNOT BE WRITTEN, the save still works. The entries are kept and
    the next save writes them too; the status line says so once.

  * COLUMN FILTERS, like a spreadsheet's, on six tables: Projects and Monthly
    estimation on the project tab, People and Monthly estimation on the person
    tab, and Standard period FTE and Role factors on General assumptions. Click
    the small arrow in a column heading, tick the values to keep.

    Filters on different columns narrow TOGETHER, and the values a column offers
    are the ones the other columns still leave reachable. A note above the table
    says how many rows are hidden, with a button to clear them - a filter left
    on from earlier is otherwise hard to tell from data that is not there.

    IT NARROWS THE TABLE, NOT THE PLAN. The charts and the totals do not move: a
    row hidden here is still in the plan. The filter bar at the top of the page
    is still the control that changes what the figures mean.


WHAT IS NEW IN 1.8

  * THE MENU NO LONGER COVERS THE PAGE. The File/Edit/View/Plan/Help bar and the
    status strip beneath it stay at the top of the window while you scroll, and
    the page has its own bar that does the same - the tabs and the Save button.
    Both were pinned to the top of the window and the menu won, so scrolling slid
    the page's controls underneath it and left them there. The page's bar now
    stops below the menu, at whatever height the menu actually is: both bars wrap
    on a narrow window or a long file path, so it is measured rather than assumed.

  * THE STANDARDS SHEET IS RENAMED. 'PeriodWeightStandard' is now
    'PeriodFTEStandard', and the panel over it reads 'Standard period FTE for
    project types' instead of 'Standard period weights'. Version 1.6 renamed the
    COLUMN to standard_fte because the table holds a monthly FTE and not a
    multiplier; the sheet and the panel went on saying 'weight', which is the
    misreading that made version 1.7 necessary in the first place.

    YOUR EXISTING FILES STILL OPEN, and no figure changes. A workbook written by
    1.6 or 1.7 is read as it stands - the old sheet name is translated on the way
    in and the findings report says so once - and saving writes it back under the
    new name. Source schema version steps 10 to 11.

  * THE CALCULATION NOTES NOW MATCH THE CALCULATION. The Monthly estimation panel
    still described the 1.6 formula: four factors multiplied together. Since 1.7
    that has not been how a figure is arrived at, and the two levels differ:

        a PROJECT month     standard FTE x period weight x month_run
        an ASSIGNMENT month that month, divided by share - the share being
                            (role factor / sharers) x person weight x coverage
                            measured against everyone else's on that month

    Nothing about the arithmetic changed here; only what the screen says about it.


WHAT IS NEW IN 1.7

  * A PROJECT-MONTH IS NOW ITS STANDARD, and the people on it DIVIDE that month
    rather than each adding to it. Your figures will be LARGER than in 1.6, and
    on a plan staffed by part-timers they will be much larger.

        demand = standard_fte x period weight x month_run
        claim  = (role factor / people holding that role)
                     x person weight x month coverage
        FTE    = demand x claim / (the sum of the claims)

    The shares add to one, so the month comes to its demand however many people
    are on it and whatever their weights.

  * WHY IT CHANGED. In 1.6 person_weight scaled each person's share AFTER the
    demand had been divided, so a project staffed by part-time people showed a
    fraction of what it needs - on the delivered example, about 30% of it. That
    made the standard look as though it were being ignored. It was not: it was
    there, and the staffing was cancelling most of it.

  * WHAT THIS MEANS IN PRACTICE. A part-time person now pushes load ONTO their
    colleagues instead of lowering the project. Under-staffing shows up on the
    PEOPLE, as months over the 1.50 ceiling, and never as a project that costs
    less than the work it contains.

  * month_run is how much of the month the project actually ran, taken as the
    largest coverage any of its people have. A project whose period ends on the
    10th draws a third of a month, not a whole one.

  * split_shared_role_fte can no longer inflate a project total, because nothing
    can. On a project with a single role it now does nothing at all; it still
    decides the split where roles have different numbers of people on them, which
    is the case it was always really about.

  * CHECKING A FIGURE. File -> Export -> calculated FTE. On the Detail sheet
    every row of one project-month carries the same demand_fte, and the fte
    column of those rows adds up to exactly it. Each row is demand_fte x
    role_share - two numbers, both printed beside it.


WHAT IS NEW IN 1.6

  * THE STANDARD MONTHLY FTE NOW DECIDES HOW BIG A FIGURE IS. Until this version
    the 'Standard period weights' table was read by nothing except the period
    generator. Every figure came from the project's own period weight times the
    role factors, which is a SHAPE with no size behind it. Your figures will
    move, and they are meant to.

        FTE = standard_fte x period weight x role_share x person weight x coverage

    standard_fte   the month's DEMAND for a project of this type, phase and work
                   scope in that period. A quantity, not a multiplier: 4.02 means
                   the period takes about four full-time people a month. It used
                   to be called 'weight', which is most of why it went unread -
                   a weight reads like something to multiply by.
    period weight  this project's own ADJUSTMENT to that standard. 1.00 means an
                   ordinary project of its kind. It no longer carries the size.
    role_share     this person's slice: their role's factor, divided by the
                   people holding that role, over the sum of the factors of the
                   roles ACTUALLY STAFFED that month.

  * WHAT FOLLOWS FROM IT. The shares add to one, so the project month is exactly
    standard x period weight, however many roles are on it. An unstaffed role's
    work lands on the others instead of making the project look cheaper.
    (Version 1.6 shipped a different reading of person_weight - see 1.7 below.)

  * YOUR EXISTING FILES STILL OPEN. A workbook from the previous version is read
    and the renamed column is carried across. But its numbers were written as
    MULTIPLIERS around 1.00 and are now read as FTE, so check two columns before
    you trust the figures:

        PeriodWeightStandard.standard_fte   should be a real monthly FTE
        ProjectPeriod.weight                should be about 1.00, an adjustment

    Where a standard is missing the figure falls back to 1.00 and the findings
    report says so, which is exactly what the old version did.

  * A NOTE ON THE STANDARDS TABLE. A row with the work scope left EMPTY applies to
    every scope; a row naming a scope beats it for projects with that scope. So if
    you edit a standard and a project does not move, check which of the two rows
    that project is actually using.

  * FIXED: the 'Standard period weights' table showed blank values, and an edit
    typed into one was accepted, counted as an unsaved change, survived the save
    prompt and then vanished. The panel was still asking for the old column name.


WHAT IS NEW IN 1.5

  * A FIGURE CAN NOW BE STATED INSTEAD OF CALCULATED. Sometimes the assumptions
    are not the best information you have. A study two years in has a manager who
    knows what the rest of it takes, and a standard period weight multiplied by a
    standard role factor is the worse of the two available answers.

    So a PROJECT, or ONE PERSON'S ASSIGNMENT to a project, can be switched to
    MANUAL. Open a project on 'Source data (project)', or pick an assignment on
    'Source data (person)', and use the MONTHLY ESTIMATION panel:

      Switch to manual      copies every month across exactly as it stands, to
                            two decimal places, and from then on those figures
                            are used instead of the calculation. You then edit
                            the months you know better.
      Switch to automatic   deletes the stated months and goes back to working
                            them out from the assumptions.

    BOTH ASK FIRST. One of them hands you a run of figures permanently; the other
    deletes work. Neither is something to find out about afterwards.

  * THE TWO LEVELS ARE DIFFERENT, and the panel says which you are looking at.
    An ASSIGNMENT figure is that person's own contribution to that project - it
    replaces their multiplication outright. A PROJECT figure is the WHOLE month,
    and everyone assigned that month is scaled so they still add up to it. That
    is why a person's figure can move when you have not touched anything of
    theirs; the export records the scaling factor so you can see why.

  * IT IS ALL OR NOTHING for whatever you set it on. Switching copies EVERY
    month, so nothing jumps and no month is half one thing and half the other.
    What you take on in exchange is all of them: changing a period weight or a
    role factor will no longer move any of those months. The confirmation says
    so before you agree to it.

  * WHY TWO DECIMAL PLACES. A stated figure is one you read and edit, and at 160
    hours to the FTE, 0.01 is 1.6 hours - there is no useful edit finer than
    that. A month can therefore shift by up to 0.005 FTE, about 48 minutes, at
    the moment you switch. Nothing else moves.

  * YOUR EXISTING FILES STILL OPEN. A workbook saved before this version simply
    carries no stated figures. Exporting the plan keeps everything you have
    stated, so it comes back next time; the calculated export marks which rows
    were stated, at which level, and what the assumptions would have said.

  * TWO NEW CHECKS. One reports a manual project or assignment with a month that
    has no figure - those count as 0.00, and a figure quietly dropping to zero is
    the one thing this feature must never do in silence. The other reports a
    project figure for a month with nobody assigned: there is nobody to share it
    out to, so it is NOT applied rather than inventing somebody to carry it.


WHAT IS NEW IN 1.4

  * YOU CAN NOW EXPORT THE FIGURES, not just the plan. File -> Export has two
    kinds on it:

      Export the plan to Excel        the source data. Re-importable - this is
                                      the one to use to carry on working, or to
                                      hand your plan to somebody else.
      Export calculated FTE           the monthly numbers, for a report, a
                                      spreadsheet or somebody else's model.
                                      NOT re-importable, and its first sheet
                                      says so.

    Both have a '...to a folder' version if you want to choose where it goes.

  * WHAT IS IN THE CALCULATED FILE. Seven sheets: a ReadMe with the formula and
    what the file does and does not cover; a Summary of the Overall tab's
    figures; one row per project per month; one row per person per month against
    their capacity; a DETAIL sheet with one row per assignment per month
    carrying every number that produced it - period weight, role factor before
    and after absorption, how many people shared the role, the person weight and
    whether it came from an override, and how much of the month was covered; the
    over- and under-allocation flags; and the settings that were in force.

  * IT ADDS UP. Every project-month and every person-month in the file is exactly
    the sum of its Detail rows, and every total is exactly the sum of those. Add
    the column in Excel and you get the total printed above it. And each Detail
    row reconciles to its own four numbers, so any figure you disagree with can
    be traced without opening this application.

  * IT FOLLOWS THE SCREEN. Whatever horizon and filters you have set is what the
    file holds, and the ReadMe names them.


WHAT IS NEW IN 1.3

  * AN IMPORT NOW TELLS YOU WHICH SETTINGS IT BROUGHT WITH IT. Importing a
    workbook takes its Configuration as well as its rows - that is deliberate, and
    it is what lets a plan be rebuilt from the file alone. But every other sheet
    describes the PLAN, while Configuration describes how the plan is READ: two of
    its settings switch calculation rules on and off, three more set the thresholds
    every over- and under-allocation flag is measured against. So opening a
    colleague's file to look at their projects quietly took their thresholds too,
    and every figure and flag on your screen moved for a reason that was nowhere on
    it.
    Now the load message says how many settings changed, with a link listing each
    one: what it was, what it is now, and what it affects. Nothing is refused - it
    is a check, not a gate. The first file you open has nothing to compare against
    and says nothing.


WHAT IS NEW IN 1.2

  * A SETTING CAN NO LONGER BE DELETED BY MISTAKE. The Configuration table has
    lost its 'Delete' and '+ row' buttons. The nine settings are read by name, so
    a new row would be read by nothing - and a deleted one used to hand its figure
    silently to a built-in default. On a test plan with the under-allocation floor
    set to 0.80 and the shared-role division turned off, deleting those two rows
    moved the total by 10 FTE-months and said nothing at all. What you change here
    is a VALUE, and every value cell is still as editable as any other.
  * And if a workbook arrives WITHOUT one - hand-edited, or made by an older
    version - the report now says so, and names the default being used instead of
    it (V-30). Information only; nothing is refused.
  * The note on capacity_unit was wrong. It named 'percent', which this program has
    never understood. FTE is a WEIGHT: 1.00 is one person working a full month, so
    ordinary values run about 0.1 to 1.0; 'hours' is that same weight multiplied by
    fte_hours_per_month. Template v1.11 carries the corrected note.


WHAT IS NEW IN 1.1

  * DATES HAVE A CALENDAR. Click any date cell and a month opens beside it -
    click a day and it is entered. You can still just type: the cell never stops
    accepting keys, and what you type moves the calendar to that month.
  * SCROLLBARS YOU CAN SEE AND DRAG. Wide tables and charts had more to the right
    and nothing on screen said so, because the browser drew a bar that fades out
    and takes up no space. The application now draws its own. The wheel and the
    keyboard work exactly as before.
  * THE BAR AT THE TOP NO LONGER SHOWS THE PAGE THROUGH IT. Scrolling used to
    leave the rows underneath faintly visible behind the tabs, with a hairline
    between the two bars. It is one solid strip now.
  * ERRORS COME IN THREE KINDS, and the report says which is which:
      must fix       something is wrong with the row itself. Refused, as before.
      may keep       the row is fine, but something it depends on is missing, so
                     the figures that need it are short an assumption. SAVE ASKS,
                     lists exactly what will be left unresolved, and you decide.
      still to come  the row is not finished yet. Reported, nothing asked.
  * The period generator now offers what fits the project: 'Auto derivation' for
    a trial, 'Standard periods' for an 'Others' project - which lays out Planning
    / Develop / Close with the dates blank. A trial that is not ready yet keeps
    the derivation button, greyed, saying which two milestones it needs.


WHAT IS NEW IN 1.0

  * A MISSING ASSUMPTION NO LONGER STOPS YOU TYPING. If you give somebody a role
    that RoleFactor has no figure for yet, the row is kept. You are told - the
    figures for that role really are wrong, and the report says so at full
    severity - but the application does not refuse to record who is on your
    project because a document somebody else maintains has not caught up. Only
    things wrong with the row in front of you still refuse: an assignment
    pointing at a project that does not exist, one that ends before it starts.
  * And the message is now worth reading. It names the exact combination the
    calculation looked up - project type / phase / work scope / period / role -
    and how many person-months came out at factor 1.00 because of it. It used to
    ask for rows covering periods nobody was ever booked into.
  * A PROJECT IS AS LONG AS ITS PERIODS SAY IT IS. The utilisation graph used to
    stretch a project over the span of its milestones. Several milestones mark
    moments inside the run rather than its edges, so the project appeared to draw
    resource in months its own plan did not cover - at full weight, because a
    month in no period is weighted 1.00. Those flat shoulders at each end of the
    graph are gone. Milestones still lay the periods out; the periods are the run.


WHAT IS NEW IN 0.8

  * An empty post no longer makes a project look cheap. If a role carries a
    factor in your assumptions and nobody at all is holding it that month, its
    factor now lands on whoever covers for it - because they are the one under
    the extra pressure. Delivered set up so that a Clinical Data Associator is
    covered by the Lead data manager, and 'Other staff' by the 'Project lead'.
    Those two are ROWS in RoleFactor (the absorbed_by column), not something
    buried in the program: change them, add your own, or empty the column and
    the whole behaviour stops. Config -> absorb_unstaffed_role_factor = 0 also
    turns it off outright.
  * A new check reads your assumptions against your projects and says plainly
    when the two do not meet: a project whose type/phase/work scope has NO
    period weights at all (V-27), which used to be calculated silently at 1.00.
    A second, for information only, names work nobody is counting: a role with a
    factor that nobody holds and nothing covers for (V-29).
  * 0.9 REMOVES a check that 0.8 added. V-28 refused an assignment whose role had
    no role factor anywhere - and since an error refuses the edit that raised it,
    it stopped you entering who is on a project until the assumptions had caught
    up. Entering your plan should not wait on a document somebody else maintains.
    Nothing else changed and no figure moves.
  * outsourcing_type is now outsourcing_scope_det - free text, for your own
    notes. Work scope is what the calculation reads. Your existing files still
    open: the old column name is recognised and carried across.


WHY THIS VERSION EXISTS

  Two company controls shaped it, and neither is worked around:

    * an executable cannot be sent through e-mail. This edition is plain Python
      text - you can read every line of it before running it.
    * data cannot be fed into a web page through the browser's file picker. This
      edition never asks the browser for a file. You choose a path, Python opens
      the file, and the figures appear. There is no upload, so there is nothing
      for an upload control to stop.


WHAT YOU NEED

  Python 3.9 or newer. You said 3.14, which is fine.
  Check with:   python --version


HOW TO START IT

  1. Extract this whole folder somewhere of your own - your Documents folder is
     ideal. Keep the folders inside it as they are.
  2. Double-click PM_APP.py.
       If Windows asks what to open it with, choose Python.
       From a command prompt this also works:   python PM_APP.py
  3. A black console window appears and your browser opens the application.
  4. KEEP THE CONSOLE WINDOW OPEN while you work. Closing it stops the
     application; that is how you shut it down.


WHERE YOUR DATA GOES

  In a folder called data\\ beside PM_APP.py, under your own account name. It is
  never sent anywhere. Help -> About shows the exact path.

  Delete this folder and the application is gone. It installs nothing, writes
  nothing to the registry, and leaves nothing behind.


HOW TO GET YOUR SOURCE DATA IN

  File -> Import source data...      choose your .xlsx workbook
  File -> Import from a folder...    same thing, with a folder list inside the
                                     page - use this for a network share, or if
                                     the first one does nothing

  Both read the file with Python. Neither goes near the browser's file picker.


HOW TO GET DATA OUT

  File -> Export to Excel            saves to your Downloads folder
  File -> Export to a folder...      saves where you choose


IS IT SAFE TO RUN?

  It listens on 127.0.0.1 only, which is this machine talking to itself; nothing
  on the network can reach it, and Windows Firewall does not prompt for it. The
  port is chosen fresh each time, and every request must carry a key generated
  at start-up and never written to disk.

  It uses nothing but the Python standard library. There is no pip install, no
  download, and no network access of any kind.


IF SOMETHING GOES WRONG

  Send back what the console window says. That is where every error is written.
"""


def page():
    """The application page: the same parts, in the same order, minus the browser's
    file interface, plus this shell's chrome."""
    chrome_css = (SRC / "shell" / "python" / "chrome.css").read_text(encoding="utf-8")
    chrome_html = (SRC / "shell" / "python" / "chrome.html").read_text(encoding="utf-8")
    bridge = (SRC / "shell" / "python" / "bridge.js").read_text(encoding="utf-8")
    # The difference report is wired into THIS shell only. Its engine lives in
    # core/06a_diff.js and is shared; the screen is not, because the web application
    # is feature-frozen (N-06) and has no workspace to merge into.
    diff = (SRC / "shell" / "python" / "importdiff.js").read_text(encoding="utf-8")

    parts = []
    for name in build_app.PARTS:
        if name in WEB_ONLY:
            continue
        text = (SRC / name).read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        if name == "shell/web/page.head.html":
            text = text.replace(
                "<title>PRAP — Project Resource Assignment Program</title>",
                '<title>Project Management APP</title>\n'
                '<meta name="pm-key" content="__PM_KEY__">', 1)
        if name == "ui/style.css":
            text += chrome_css
        if name == "shell/web/page.body.html":
            text = text.replace('<div class="wrap">', chrome_html + '\n<div class="wrap">', 1)
        if name == "shell/web/page.tail.html":
            text = (f"<script>\n{diff}</script>\n"
                    f"<script>\n{bridge}</script>\n" + text)
        parts.append(text)

    html = "".join(parts).replace(
        "<h1>Project Resource Assignment Program</h1>",
        "<h1>Project Management APP</h1>", 1)
    return html, len(parts)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "app").mkdir(parents=True)
    (OUT / "pmapp" / "shell").mkdir(parents=True)
    (OUT / "pmapp" / "storage").mkdir(parents=True)

    html, n = page()
    (OUT / "app" / "index.html").write_text(html, encoding="utf-8")

    for src, dst in MODULES.items():
        (OUT / dst).write_text((SRC / src).read_text(encoding="utf-8"), encoding="utf-8")

    for pkg, what in (("pmapp", "Project Management APP - the Python shell."),
                      ("pmapp/shell", "The shell: where files go, and how the page "
                                      "reaches them."),
                      ("pmapp/storage", "Storage: workspaces, versions, journals, "
                                        "the write claim.")):
        (OUT / pkg / "__init__.py").write_text(f'"""{what}"""\n', encoding="utf-8")

    (OUT / "PM_APP.py").write_text(ENTRY, encoding="utf-8")
    (OUT / "version.txt").write_text(VERSION + "\n", encoding="utf-8")
    (OUT / "READ ME FIRST.txt").write_text(READ_ME, encoding="utf-8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"Built  {OUT.relative_to(ROOT)}")
    print(f"  page          app/index.html   {len(html):,} bytes from {n} parts "
          f"({len(WEB_ONLY)} web-only part left out)")
    py = [p for p in OUT.rglob("*.py")]
    print(f"  python        {len(py)} files, "
          f"{sum(p.stat().st_size for p in py):,} bytes")
    print(f"  altogether    {len(files)} files, {total / 1024:.0f} KB")
    return files


def package(files):
    zip_path = ROOT / "dist" / f"PM_APP_python_v{VERSION}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, pathlib.Path("PM_APP") / p.relative_to(OUT))
    h = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"\nPackaged  {zip_path.relative_to(ROOT)}")
    print(f"  size    {zip_path.stat().st_size / 1024:.0f} KB")
    print(f"  sha256  {h}")
    return zip_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", action="store_true", help="package it for e-mail")
    args = ap.parse_args()
    files = build()
    if args.zip:
        package(files)


if __name__ == "__main__":
    main()
