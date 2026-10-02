"""What Save recalculates from the rows beneath, and what a window can see before Save.

Four things, all about a value that was typed by hand while the rows underneath already
said what it should be.

  1. A project's start_date becomes the EARLIEST of its milestone dates and its end_date
     the LATEST, on Save - and total_period_months, which is derived from those two,
     follows without anyone touching it.
  2. planned_member_count becomes the number of DISTINCT people assigned to the project.
  3. A new row in Periods is given the next period_seq for that project. (The sheet has
     no period_id: it is keyed on project_id + period_name, and period_seq is what
     carries the order.)
  4. A weight-override window shows the project and role of its assignment even when
     that assignment has NOT been saved - those two columns exist so that, while typing,
     you can see the window is attached to the right piece of work, and blank at exactly
     that moment is when they are least useful.

And two guards, both about not destroying information:

  5. a project with no milestone dates keeps the window that was typed
  6. a project with no assignments keeps the team size that was typed, because "nobody
     is assigned yet" is not the statement "this needs nobody"

    python tools/test_derive.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

PROJECT = {"project_name": "Trial One", "project_type": "NewDrug CT",
           "project_category": "Compound A", "clinical_phase": "Phase 2",
           "outsourcing_type": "Partial outsourcing", "EDC_setup": "by SB",
           "DataReviewSystem_setup": "by CRO", "RBQM_setup": "by SB",
           "start_date": "2020-01-01", "end_date": "2040-12-31",   # deliberately wrong
           "planned_member_count": "9", "status": "Planned"}
MILESTONES = [("Protocol (v1)", "2027-01-15"), ("CTA submission", "2027-03-01"),
              ("First SIV", "2027-07-01"), ("final DB lock", "2029-03-31")]

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def add_row(pg, loc, values):
    pg.locator(f"{loc} button[data-ins]").last.click()
    pg.wait_for_timeout(800)
    row = pg.locator(f"{loc} tbody tr td[data-col]").evaluate_all(
        "es => Math.max(...es.map(e => +e.dataset.row))")
    for col, v in values.items():
        td = pg.locator(f"{loc} td[data-row='{row}'][data-col='{col}']")
        if td.count() == 0:
            continue
        td.first.click()
        pg.wait_for_timeout(130)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(str(v))
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(300)
    return row


def save(pg):
    pg.click("#saveBtn")
    pg.wait_for_timeout(1800)
    return pg.inner_text("#banner")


def project(pg):
    return pg.evaluate("""() => {const p = S.model.projects['PRJ-001']; return p ? {
        start: ymd(p.start_date), end: ymd(p.end_date),
        months: p.total_period_months, team: p.planned_member_count} : null;}""")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — values recalculated from the rows beneath")
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.click("#startBtn")
    pg.wait_for_timeout(2200)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(900)

    P = "#t-proj .data-t[data-sheet='Project']"
    add_row(pg, P, PROJECT)

    # ---- 5. no milestones yet: the typed window survives ---------------------
    save(pg)
    got = project(pg)
    check(got and got["start"] == "2020-01-01" and got["end"] == "2040-12-31"
          and got["team"] == 9,
          "with no milestones and no assignments, what was typed is left alone", f"{got}")

    # ---- 1. the window, from the milestones ----------------------------------
    M = "#t-proj .data-t[data-sheet='Milestone']"
    for name, date in MILESTONES:
        add_row(pg, M, {"milestone_name": name, "milestone_date": date})
    banner = save(pg)
    got = project(pg)
    check(got and got["start"] == "2027-01-15" and got["end"] == "2029-03-31",
          "Save sets start_date to the earliest milestone and end_date to the latest",
          f"{got['start']} .. {got['end']}")
    check(got["months"] == 27,
          "total_period_months follows, without anyone touching it",
          f"{got['months']} months")
    check("Recalculated" in banner and "2027-01-15" in banner and "2029-03-31" in banner,
          "and the banner names every value it changed", banner.strip()[:110])

    # ---- 6. still no assignments: the typed team size survives ---------------
    check(got["team"] == 9,
          "a project with no assignments keeps the team size that was typed",
          f"planned_member_count={got['team']}")

    # ---- 3. the next period_seq ----------------------------------------------
    PP = "#t-proj .data-t[data-sheet='ProjectPeriod']"
    add_row(pg, PP, {"period_name": "Start-up", "period_start": "2027-01-15",
                     "period_end": "2027-06-30"})
    first = pg.evaluate("S.model.raw.ProjectPeriod.map(r => [r.period_seq, r.weight])")
    add_row(pg, PP, {"period_name": "Conduct (final)", "period_start": "2027-07-01",
                     "period_end": "2029-03-31"})
    both = pg.evaluate("S.model.raw.ProjectPeriod.map(r => r.period_seq)")
    check(first == [[1, 1]] and both == [1, 2],
          "Periods: each new row takes the next period_seq for that project, at weight 1.00",
          f"first row {first}, then {both}")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)

    # ---- 2. the team size, from the assignments ------------------------------
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    PER = "#t-pers .data-t[data-sheet='Person']"
    add_row(pg, PER, {"person_name": "Alex R.", "department": "Data Management",
                      "primary_role": "Lead data manager"})
    add_row(pg, PER, {"person_name": "Bo T.", "department": "Programming",
                      "primary_role": "Clinical Database Programmer"})
    save(pg)

    A = "#t-pers .data-t[data-sheet='Assignment']"
    add_row(pg, A, {"project_name": "Trial One", "role_name": "Lead data manager",
                    "assign_start_date": "2027-04-01", "person_weight": "0.4"})

    # ---- 4. the window's lookups, BEFORE that assignment is saved ------------
    W = "#t-pers .data-t[data-sheet='PersonPeriodWeight']"
    add_row(pg, W, {})
    shown = pg.eval_on_selector_all(f"{W} tbody tr td.drvcell", "es => es.map(e => e.textContent)")
    unsaved = pg.evaluate("S.model.raw.Assignment.some(a => a.__new)")
    check(unsaved and shown[:2] == ["Trial One", "Lead data manager"],
          "a window shows its assignment's project and role before that assignment is saved",
          f"assignment still a draft={unsaved}, window shows {shown[:2]}")

    banner = save(pg)
    check(project(pg)["team"] == 1,
          "one person assigned makes planned_member_count 1",
          f"{banner.strip()[:90]}")

    pg.locator("#t-pers .data-t[data-sheet='Person'] tbody tr[data-id='PSN-002'] "
               "td[data-col='person_name']").first.click()
    pg.wait_for_timeout(800)
    add_row(pg, A, {"project_name": "Trial One", "role_name": "Clinical Database Programmer",
                    "assign_start_date": "2027-06-01", "person_weight": "0.3"})
    save(pg)
    check(project(pg)["team"] == 2,
          "a second person on the same project makes it 2 — distinct people, not rows",
          f"planned_member_count={project(pg)['team']}")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
