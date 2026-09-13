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
VERSION = "1.21"

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

It opens in your browser, at an address only this machine can reach. Keep this
window open while you work; closing it stops the application - and closing the
page in your browser stops it too, a few seconds later. Refreshing the page
does not, and neither does closing one of two windows.

    python PM_APP.py --keep-running     leave this window open after the page
                                        is closed, and close it yourself
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

WHAT IS NEW IN 1.21

  * A PROJECT WITH NOBODY ON IT NOW TELLS YOU WHAT IT NEEDS. Add a project,
    lay out its periods, and until you assigned the first person the
    application showed no FTE for it anywhere - no row in Resource by
    project, no band on the charts, nothing in the tiles - while still
    drawing it on the timeline. So the screen told you the project exists
    and when it runs, and then would not tell you what it costs.

    It could have done all along: the type, the phase, the scope and the
    periods are everything the standard needs. A project-month IS its
    standard and the people on it divide it, so having nobody on it does
    not make the figure nought - it only made it invisible.

    You will now see a note, on the banner when the file opens and again
    when you press Save, reading like this:

        Project PRJ-099 has periods but NOBODY ASSIGNED TO IT ... its own
        standard says it needs 38.05 FTE-months across 24 month(s), from
        2025-03, peaking at 1.86 FTE in 2026-10.

    Those are the figures the project will show once you assign somebody,
    to the penny - not an estimate of them. The note disappears by itself
    the moment the first assignment exists.

  * IT IS A NOTE AND NOTHING MORE. It never refuses an edit, never blocks a
    Save, and never asks you a question, because a project with nobody on
    it yet is simply the state every project is in for the minute after you
    create it. A project you have marked Completed is left alone.

  * The project still does not appear in the tables and charts until it is
    staffed. That is a larger change and is not in this version.

  * No figure you already have moves. Workbook layout version 12 as before.


WHAT IS NEW IN 1.20

  * THE 'LAST SET' COLUMN HAS BEEN REMOVED from both Monthly estimation
    tables. It was meant to tell a figure you typed from one the application
    copied across when you switched to manual - and it never did: it was
    filled in by the switch itself, but NOT when you typed a figure into the
    cell, which is the one thing it existed to mark. It also held a long
    machine-written string rather than a date.

    Nothing is lost. The change log archived when you press Save already
    records every edit with the time, who made it, and what the figure was
    before and after - which is the same question answered properly.

  * YOUR EXISTING FILES STILL OPEN, AND STILL SAVE. A plan written by an
    earlier version still has the column in it; it is simply left out as the
    file is read, and you are told once. No figure changes.

  * Workbook layout version 12. Template v1.16, example files v1.18 and
    v1.10.


WHAT IS NEW IN 1.19

  Five things about reading the screen. No figure has changed anywhere.

  * LONG PLANS NO LONGER SQUASH THE MONTH LABELS. The Utilisation graph on
    both Source data tabs used to be one fixed width however many months you
    were looking at, so past about two years the month names ran into one
    another and the graph stopped being readable - on exactly the long plans
    that most need reading. Every month now gets room of its own and the
    panel SCROLLS SIDEWAYS when there are more than fit. Your usual two-year
    view looks exactly as it always did.

  * ASSIGNMENTS, WEIGHT OVERRIDES AND MONTHLY ESTIMATION NOW HAVE THE WHOLE
    WIDTH EACH. They used to sit two abreast with half a screen apiece, and
    all three are wide, so all three scrolled sideways all the time. They are
    stacked now, in the order you work in them: pick the assignment, then its
    override windows, then its months.

  * MONTHLY ESTIMATION SAYS WHICH ASSIGNMENT IT IS SHOWING, on a line under
    the title - the id, project, role, dates and weight, for example:

        Assignment (ASG-203): NEU-143 Phase 3 / Project oversight /
        2027-08-01 ~ 2030-05-30 / weight 0.16

  * CLICK A NAME IN A GRAPH'S KEY AND THAT ONE LIGHTS UP. Everything else
    fades back so you can follow a single project or person through the
    chart. Click it again, click another, or press Escape to bring the rest
    back. One click works across the whole tab: pick a project in the trend
    graph and it is picked out in the stacked chart and on the timeline too.
    Charts that are drawn a different way round - people rather than projects
    - are simply left alone rather than going blank.

  * EVERY COLUMN HEADING NOW SAYS WHAT THE COLUMN MEANS, in plain words. So
    'outsourcing_scope_det' now reads 'What is outsourced', 'person_weight'
    reads 'Share of this person', and 'capacity_fte' reads 'Capacity in FTE'.

    The workbook's own column name is no longer printed on the heading. Hover
    the heading - or any cell in it - and the note that pops up names it, so
    you can still match a column on screen to a column in the spreadsheet
    whenever you need to.

    NOTHING HAS BEEN RENAMED. Your files, your columns and every message are
    exactly as they were; only what is printed at the top of the table has
    changed.


WHAT IS NEW IN 1.18

  * CAPACITY IS NOW LIMITED TO BETWEEN 0.00 AND 1.00, on the People table of
    the Source data (person) tab. It is how much of ONE PERSON there is:

        1.00   full-time
        0.50   half a week
        0.00   on the books, not available at all (on leave, say)

    Anything outside that is REFUSED as you leave the cell, and the message
    tells you why - including the most likely reason, which is hours typed
    into an FTE column.

  * SOMEBODY DOING THE WORK OF TWO PEOPLE IS NOT A CAPACITY OF 2.00. It is
    two assignments, or a person weight above 1.00 on one of them. The
    message says so.

  * THIS IS THE ONLY RULE ADDED THIS YEAR THAT REFUSES. Period weights, role
    factors and stated monthly figures are all judgements you are entitled to
    make, so the application reports on them and leaves the decision with you.
    A capacity of 1.5 is not a judgement - there is no such thing as one and a
    half of a person - so it is stopped at the moment you type it, while you
    still remember what you meant.

  * A PLAN THAT ALREADY HAS ONE STILL OPENS. It is reported, and you can carry
    on working; only edits that would make things worse are stopped.

  * THE TEMPLATE STOPS IT TOO. If you fill the workbook in using Excel, Excel
    itself now refuses a capacity outside 0.00 to 1.00, with its own message.
    Template v1.15, example files v1.17 and v1.9 - the layout is unchanged,
    only the guard rail is new.

  * No figure has changed anywhere.


WHAT IS NEW IN 1.17

  * CLOSING THE BROWSER NOW CLOSES THE BLACK CONSOLE WINDOW TOO, a few
    seconds later. It used to stay open, quietly holding the port, your hold
    on whichever plan was open, and your data folder - and the only way to be
    rid of it was to know it was there and close it yourself.

  * REFRESHING THE PAGE DOES NOT STOP IT. The browser gives the same signal
    for a refresh as for a close, so the application waits a few seconds to
    see whether the page comes back before it does anything.

  * NOR DOES CLOSING ONE OF TWO WINDOWS. If you have the application open in
    two tabs, closing one leaves the other working.

  * NOR DOES LEAVING IT IN A BACKGROUND TAB. Browsers slow down and even
    freeze the timers of a tab nobody is looking at, so the fallback that
    catches a browser being killed outright waits a full fifteen minutes
    before giving up. It will never shut down under you because you were
    reading your e-mail.

  * IF YOU WANT THE OLD BEHAVIOUR, start it with --keep-running:

        python PM_APP.py --keep-running

    The console then stays open after you close the page, and you close it
    yourself as before. The start-up banner says which of the two you are
    getting.

  * Nothing about the application's figures has changed.


WHAT IS NEW IN 1.16

  * IN THE "Standard vs staffed" POP-UP, YOU CAN NOW TYPE A FIGURE FOR ANYONE
    ON THE PROJECT - not only for people already on manual estimation. Their
    Stated cell used to show a dash, which looked as though the screen was
    read-only for them, and they are usually exactly the person whose figure
    you wanted to change.

  * TYPING FOR SOMEBODY STILL ON "auto" ASKS FIRST, and it has to. Stating one
    month means stating ALL of that person's months on that project: the
    message says how many, what they total, and what the month you typed will
    become. Say yes and the switch, the copy of every month, and your figure
    happen together. Say no and nothing at all is written.

    (Why: a figure written against somebody on automatic estimation is read by
    nothing, and flipping them to manual without copying their other months
    across would count every one of those months as 0.00.)

  * SOMEBODY ALREADY ON MANUAL WHO HAS NO FIGURE FOR THAT MONTH IS NOT ASKED.
    Their months are already theirs, so the figure is simply written. That is
    the month the application counts as 0.00 and reports as V-31.

  * TYPING SOMETHING THAT IS NOT A NUMBER IS REFUSED, in the same words the
    tables use, and nothing is written.

  * Everything is an ordinary edit: listed under Show details, undone by
    Leave without change, archived when you press Save.

  * TWO SMALLER FIXES IN THE SAME POP-UP. The Estimation column now reads
    MANUAL from the ASSIGNMENT rather than from whether that month happens to
    have a figure - somebody on manual with a month missing was showing as
    "auto", which is the opposite of what is wrong with it. And where the
    Applied figure is not the Stated one, the row now carries a warning mark
    explaining that the project's own stated month overrode it (V-33).

  * No figure has changed anywhere.


WHAT IS NEW IN 1.15

  * THE APPLICATION NOW TELLS YOU WHEN A PROJECT IS NOT GETTING WHAT ITS OWN
    STANDARD SAYS IT NEEDS. Set a project's month by hand to 5.00 when its
    standard says 10.00 - or cut one person's month on it - and until now the
    application simply drew a smaller project. A study needing ten people and
    staffed with five looked exactly like a study that only ever needed five.

    (The other comparison, a project's month against the sum of its people,
    cannot differ: the month is BUILT from those people, so it is always
    their sum.)

  * A NEW SECTION ON THE OVERALL TAB, "Standard vs staffed", lists every
    month it happens in - the project, the month, what it needs, what it is
    getting, and the gap. There is a tile above it counting them.

  * CLICK ANY ROW AND YOU CAN FIX IT THERE. The month opens with its own
    figures: what it needs term by term, everybody on it, and the stated
    figures that caused the gap - EDITABLE in place. Change one and
    everything behind the dialog follows. They are ordinary edits: validated
    as you leave the cell, listed under Show details, undone by Leave without
    change, written only when you press Save.

  * BOTH DIRECTIONS ARE SHOWN AND THEY ARE NEVER ADDED TOGETHER. Short of the
    standard is amber with a down arrow; over it is red with an up arrow.
    Five short in September and five over in October come to zero, and that
    is not a plan in balance.

  * THE MONTHS THEMSELVES ARE MARKED, so you do not have to go looking: an
    outlined cell in "Resource by project", and a dashed outline on the
    project's own utilisation chart.

  * IT NEVER STOPS YOU. This is a warning (V-34), not an error. Deciding a
    month by hand is the whole point of manual estimation - somebody part way
    through a trial knows better than the assumptions - so the application
    says so and leaves the decision to you. It also appears in the findings
    report and in the archived change log. A plan nobody has edited by hand
    reports nothing at all.

  * No figure has changed anywhere.


WHAT IS NEW IN 1.14

  * THE MONTHLY ESTIMATION COLUMN NOW SHOWS THE WHOLE SUM, not just the
    period. On a project:

        Before-Start-up (standard 2.02) x period weight (1.12)
                                        x month run (1.00) = 2.26

    On a person, a second line follows with their share of that month:

        role factor (0.72) / sharers (1) x person weight (0.25, no override)
                                         x coverage (1.00) = 18.3% of it -> 0.41

    Naming the period answered one of six inputs. If you disagree with a
    figure, you can now see WHICH of the six you disagree with.

  * WHY THE PERSON'S IS SHOWN AS A PERCENTAGE and not as one long
    multiplication: those terms make a CLAIM on the month, and every claim on
    a project-month is measured against the others, so the shares always add
    to one. Multiply the terms above and you get 0.18; the figure is 0.41.
    Writing it as one product would be showing you arithmetic the application
    does not do.

  * A WEIGHT OVERRIDE IS SHOWN AS ONE TERM, not two. An override REPLACES the
    person's weight for the months it covers - it does not multiply it - so
    the cell names both and says which was used:

        x weight override (0.50, replacing person weight 1.00)

  * ANYTHING MISSING SAYS SO AND NAMES ITS CHECK. "standard 1.00 by default -
    no row for this period, V-19" rather than a bare 1.00, which you could
    not tell from a standard that really is 1.00. Same for a missing role
    factor (V-23) and a month in no period (V-12). Where a role is covering
    for an unstaffed one, the cover is named with the role it came from.

  * The sharer count also keeps its own short column, because a sentence
    cannot be sorted or filtered and "2 share this role" can.

  * No figure has changed anywhere.


WHAT IS NEW IN 1.13

  * THE PERIODS TABLE NOW SHOWS WHAT THE WEIGHT IS A WEIGHT OF. Beside it,
    the STANDARD MONTHLY FTE that period selects for a project of this type,
    phase and work scope - and the two multiplied:

        Start-up   weight 1.29   |   4.05 -> 5.22 a month

    A row reading "x1.29" told you this study is a bit heavier than usual
    through start-up and did not tell you heavier than WHAT. Finding out
    meant leaving the tab for General assumptions and reading a 48-row
    matrix for one figure.

  * AND THE MONTHLY ESTIMATION TABLES NOW SAY WHERE EACH MONTH'S AUTOMATIC
    FIGURE CAME FROM. A new column names the period the month falls in and
    the weight it carried - "Start-up x1.29" - on both the project's table
    and each person's.

  * ON A PERSON'S TABLE THERE IS ONE MORE: how many people held that role on
    that project that month. "2 share this role" is usually the answer to
    "why did this drop by half when nothing of mine changed" - the role
    factor is what the ROLE costs the project, so a second holder halves
    each share and the project's month does not move.

    The project's table deliberately does NOT show that count: a project
    month is divided between several roles, each with its own number of
    holders, so one figure there would be an average of things that do not
    compare.

  * ALL THREE ARE LOOKED UP, NOT STORED. They are read-only, they are marked
    as lookups, and they are not columns of your workbook - so nothing can
    leave a stale copy of a standard in the file after the standards have
    been edited. A period with no standard says "none - V-19" rather than
    showing the 1.00 the calculation falls back to.

  * No figure has changed anywhere.


WHAT IS NEW IN 1.12

  * WHEN A PROJECT'S MONTH IS SET BY HAND, EVERYBODY ON IT IS BROUGHT INTO
    LINE - including anyone whose own monthly figure you had already set by
    hand. That is not new behaviour; the project figure has always been the
    whole month and the people on it have always been scaled to add up to it.
    What is new is that the application now SAYS SO.

    Set a project's March to 10.00 while somebody's own March on that project
    says 99.00, and they are given 9.97. Until now the sheet said 99.00, the
    chart said 9.97, and nothing connected the two.

  * SO A FIGURE THE PROJECT OVERRODE IS NOW CALLED OUT, three ways over:

      - the cell is marked, and hovering it says what happened;
      - the Monthly estimation panel gains a table of the month, what you
        stated, what was actually given, and the project's own month;
      - it appears in the findings, and therefore in the archived change log.

  * AND EDITING ONE STOPS TO ASK. Type a figure the project's own month
    cannot accommodate and a message names both numbers and offers "Keep what
    I typed" or "Put it back". It never refuses the edit - both figures are
    ones somebody typed deliberately, and which of them is wrong is not this
    application's judgement to make. Fix it by changing the project's month,
    or by taking that person's assignment off manual.

  * THE MONTHLY ESTIMATION TABLES NOW SHOW TWO DECIMALS THROUGHOUT. The
    automatic FTE and the difference were the last four-place figures left on
    screen: a stated 2.41 beside an automatic 2.4120 read as a discrepancy you
    had caused rather than as two decimals nothing else uses.


WHAT IS NEW IN 1.11

  * EVERY FIGURE IS NOW A WHOLE NUMBER OF HUNDREDTHS. Not shown to two
    places - IS two places. A figure on screen as 4.27 was 4.27 when it was
    worked out, and the same 4.27 appears in the exported workbook, which
    used to carry 4.2683.

    YOUR FIGURES WILL MOVE SLIGHTLY. On the delivered example the total goes
    from 4,333.46 to 4,333.77 FTE-months. That is the rounding and nothing
    else - no assumption and no rule has changed.

    Two places because that is what the plan is written in: at 160 hours to
    the FTE, 0.01 is 1.6 hours, and a manual estimate is already typed at two
    places.

  * AND THE DETAIL STILL ADDS UP. The month is rounded first and its
    hundredths are then shared out, rather than each person's slice being
    rounded on its own - so on the Detail sheet the rows of one project-month
    still add to that month exactly, with nothing left over. Rounding each
    slice separately would have broken that on 40% of months.

    One consequence worth knowing: a single row can sit up to 0.01 away from
    its own demand x share, because it holds a whole number of hundredths.
    The exported workbook says so on its first sheet.

  * THE CHANGE LOG IS NO LONGER EXPORTED FROM INSIDE THE APPLICATION. It is
    written to the audit folder every time you save, so the file is already
    there - and a button handing you the same record afterwards was a second
    answer to one question, always the staler of the two.

  * THE AUDIT FOLDER IS NOW SHARED. It sits beside `users`, not inside your
    own folder:

        data/audit/PRAP_changes_YYYY-MM.csv

    So on a shared drive everybody's entries are in one file, in order, each
    naming who made the change. That is the log that answers "what happened
    to this plan", which is the question it is kept for.


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
