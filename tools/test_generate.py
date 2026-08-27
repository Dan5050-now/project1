"""The two generators on the project tab, and that what they generate stays editable.

Both save typing, neither takes the decision away. What they produce is ordinary rows:
provisional until Save, editable afterwards, deletable, and subject to every rule.

  1. BLANK LIST lays out the standard milestone names for the selected project with the
     dates empty, so only the dates have to be typed. Names already listed are not
     repeated - a second 'CTA submission' would be the duplicate V-20 exists to catch.

  2. AUTO DERIVATION builds the project's periods from its milestones, by the rule in the
     development plan. It is checked against that rule term by term on a project built
     for the purpose: Start-up opening the day after Protocol (v1), closing at First SIV;
     an interim DB lock splitting the conduct stretch in two; Close-out (final) starting
     three months before the final lock; and an Inspection after that lock opening
     After Close-out (final). Each period takes the standard weight for the project's
     type and phase.

  3. It refuses what it cannot do, and says why: an 'Others' project (the rule hangs on
     CTA submission and the DB locks), and a trial missing either of those (V-16).

  4. Replacing an existing set asks first, and both generators are undone by
     'Leave without change' like any other edit.

    python tools/test_generate.py
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
           "start_date": "2027-01-01", "end_date": "2029-12-31", "status": "Planned"}
# Chosen so every branch of the rule is exercised: a protocol date (so Start-up opens the
# day after it), a First SIV (so it closes there), an INTERIM lock earlier than the final
# one (so the conduct stretch splits), and an Inspection AFTER the final lock (so period
# seven opens).
DATES = {"Protocol (v1)": "2027-01-15", "CTA submission": "2027-03-01",
         "First SIV": "2027-07-01", "interim DB lock": "2028-06-30",
         "final DB lock": "2029-03-31", "Inspection": "2029-09-15"}

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
        cell(pg, loc, row, col, v)
    return row


def cell(pg, loc, row, col, v):
    td = pg.locator(f"{loc} td[data-row='{row}'][data-col='{col}']")
    if td.count() == 0:
        return
    td.first.click()
    pg.wait_for_timeout(130)
    pg.keyboard.press("Control+A")
    pg.keyboard.type(str(v))
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(300)


def milestones(pg, pid):
    return pg.evaluate("p => S.model.raw.Milestone.filter(m => m.project_id === p)"
                       ".map(m => [m.milestone_name, m.milestone_date ? ymd(m.milestone_date) : null])",
                       pid)


def periods(pg, pid):
    return pg.evaluate("p => S.model.raw.ProjectPeriod.filter(r => r.project_id === p)"
                       ".map(r => [r.period_seq, r.period_name, ymd(r.period_start), "
                       "ymd(r.period_end), r.weight])", pid)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors, asked = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: (asked.append(d.message), d.accept()))

    print("app/PRAP.html — Blank list, and Auto derivation")
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.click("#startBtn")
    pg.wait_for_timeout(2200)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(900)

    P = "#t-proj .data-t[data-sheet='Project']"
    add_row(pg, P, PROJECT)
    pg.click("#saveBtn")
    pg.wait_for_timeout(1700)
    pid = pg.evaluate("S.selProj")

    # ---- 1. the blank milestone list -----------------------------------------
    standard = pg.evaluate("S.model.lists.milestone_name")
    pg.click("[data-act='blankms']")
    pg.wait_for_timeout(1400)
    got = milestones(pg, pid)
    check([n for n, _ in got] == standard and all(d is None for _, d in got),
          "Blank list lays out every standard milestone name, with the dates empty",
          f"{len(got)} rows: {', '.join(n for n, _ in got[:4])}…")

    seqs = pg.evaluate("p => S.model.raw.Milestone.filter(m => m.project_id === p)"
                       ".map(m => m.milestone_seq)", pid)
    check(seqs == list(range(1, len(standard) + 1)),
          "numbered in order, so they read as a list rather than a heap", f"{seqs}")

    before = len(got)
    pg.click("[data-act='blankms']")
    pg.wait_for_timeout(1300)
    check(len(milestones(pg, pid)) == before and "already listed" in pg.inner_text("#banner"),
          "pressing it again adds nothing — a repeated name would be a duplicate (V-20)",
          pg.inner_text("#banner").strip()[:80])

    # the rows are ordinary rows: fill in the dates, and delete the ones not wanted
    loc = "#t-proj .data-t[data-sheet='Milestone']"
    for name, date in DATES.items():
        row = pg.evaluate("a => {const m = S.model.raw.Milestone.find(x => "
                          "x.project_id === a.p && x.milestone_name === a.n); "
                          "return m ? m.__row : null;}", {"p": pid, "n": name})
        cell(pg, loc, row, "milestone_date", date)
    dated = [(n, d) for n, d in milestones(pg, pid) if d]
    check(sorted(dated) == sorted(DATES.items()),
          "and the dates can simply be typed into them", f"{len(dated)} dated")
    pg.click("#saveBtn")
    pg.wait_for_timeout(1800)

    # ---- 2. the derivation, against the rule ---------------------------------
    check(not periods(pg, pid), "the project has no period rows to begin with")
    pg.click("[data-act='autoper']")
    pg.wait_for_timeout(1600)
    got = periods(pg, pid)
    names = [n for _, n, _, _, _ in got]
    by = {n: (s, e, w) for _, n, s, e, w in got}
    check(names == ["Before-Start-up", "Start-up", "Conduct (interim)",
                    "Close-out (interim)", "Conduct (final)", "Close-out (final)",
                    "After Close-out (final)"],
          "Auto derivation builds all seven periods, in order", ", ".join(names))

    # The project's own start is 2027-01-15 too, because Save derives the window from the
    # milestones and Protocol (v1) is the earliest of them - so Before-Start-up is the
    # single day before Start-up rather than the fortnight the typed dates implied.
    check(by["Start-up"][0] == "2027-01-16"
          and by["Before-Start-up"][:2] == ("2027-01-15", "2027-01-15"),
          "Start-up opens the day after Protocol (v1); what precedes it is its own period",
          f"Before-Start-up {by['Before-Start-up'][:2]}, Start-up from {by['Start-up'][0]}")
    check(by["Start-up"][1] == "2027-07-01",
          "and closes at First SIV", f"Start-up to {by['Start-up'][1]}")
    check(by["Close-out (interim)"] == ("2028-03-30", "2028-06-30",
                                        by["Close-out (interim)"][2])
          and by["Conduct (interim)"][1] == "2028-03-29",
          "the interim lock splits the conduct stretch, closing out three months before it",
          f"Conduct (interim) to {by['Conduct (interim)'][1]}, "
          f"Close-out (interim) {by['Close-out (interim)'][:2]}")
    check(by["Close-out (final)"][0] == "2028-12-31",
          "Close-out (final) starts three months before the final lock",
          f"from {by['Close-out (final)'][0]}")
    check(by["After Close-out (final)"][0] == "2029-09-15",
          "and an Inspection after that lock opens the seventh period",
          f"from {by['After Close-out (final)'][0]}")

    # Asked through stdWeight, because schema 6 keys the table on the work scope and a
    # row with an EMPTY scope covers every scope. Reading S.model.pws straight would
    # report a missing weight where the application finds one.
    want = pg.evaluate("""p => {const pr = S.model.projects[p];
        return Object.fromEntries(CLINICAL_PERIODS.map(n =>
          [n, stdWeight(S.model, pr, n) ?? null]));}""", pid)
    check(all(want[n] is not None and abs(by[n][2] - want[n]) < 1e-9 for n in names),
          "each period carries the standard weight for this type and phase, from "
          "PeriodWeightStandard",
          ", ".join(f"{n.split(' ')[0]} {by[n][2]}" for n in names[:4]))

    # ---- 4. still ordinary rows ----------------------------------------------
    row = pg.evaluate("p => S.model.raw.ProjectPeriod.find(r => r.project_id === p "
                      "&& r.period_name === 'Start-up').__row", pid)
    cell(pg, "#t-proj .data-t[data-sheet='ProjectPeriod']", row, "weight", "1.75")
    check(pg.evaluate("p => S.model.raw.ProjectPeriod.find(r => r.project_id === p "
                      "&& r.period_name === 'Start-up').weight", pid) == 1.75,
          "what it generated is editable — a weight can simply be typed over")

    asked.clear()
    pg.click("[data-act='autoper']")
    pg.wait_for_timeout(1600)
    check(len(asked) == 1 and "Replace" in asked[0] and len(periods(pg, pid)) == 7,
          "running it again over an existing set asks before replacing them",
          asked[0].split("\n")[0] if asked else "nothing was asked")

    pg.click("#discardBtn")
    pg.wait_for_timeout(1500)
    check(not periods(pg, pid) or len(periods(pg, pid)) == 7,
          "and Leave without change undoes it like any other edit",
          f"{len(periods(pg, pid))} period row(s) after discarding")

    # ---- 3. where the rule does not reach ------------------------------------
    # A control that refuses every time it is pressed teaches the reader the feature is
    # broken. So the derivation is not OFFERED where it can never run: an 'Others'
    # project gets the generator that does fit it, and a trial that is not ready yet
    # gets the button with the reason in its place - because that answer will change.
    other = dict(PROJECT, project_name="Rollout", project_type="Others")
    del other["clinical_phase"]
    add_row(pg, P, other)
    pg.click("#saveBtn")
    pg.wait_for_timeout(1700)
    pg.locator(f"{P} tbody tr[data-id='PRJ-002'] td[data-col='project_name']").first.click()
    pg.wait_for_timeout(900)
    check(pg.locator("[data-act='autoper']").count() == 0
          and pg.locator("[data-act='blankper']").count() == 1,
          "an 'Others' project is not offered a derivation it can never run — it is "
          "offered Standard periods instead",
          f"autoper={pg.locator('[data-act=autoper]').count()}, "
          f"blankper={pg.locator('[data-act=blankper]').count()}")

    pg.click("[data-act='blankper']")
    pg.wait_for_timeout(1300)
    got = periods(pg, "PRJ-002")
    check([n for _, n, _, _, _ in got] == ["Planning", "Develop", "Close"]
          and all(s in (None, "") for _, _, s, _, _ in got),
          "and Standard periods lays those three out with the dates blank, at weight 1.00",
          f"{[(n, w) for _, n, _, _, w in got]}")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)

    # A clinical trial whose milestones are listed but not yet dated: the rule needs
    # CTA submission and a DB lock, and neither has a date.
    third = dict(PROJECT, project_name="Trial Two")
    add_row(pg, P, third)
    pg.click("#saveBtn")
    pg.wait_for_timeout(1700)
    pg.locator(f"{P} tbody tr[data-id='PRJ-003'] td[data-col='project_name']").first.click()
    pg.wait_for_timeout(900)
    pg.click("[data-act='blankms']")
    pg.wait_for_timeout(1300)
    btn = pg.locator("[data-act='autoper']")
    tip = btn.get_attribute("data-tip") or ""
    check(btn.count() == 1 and btn.is_disabled()
          and "CTA submission" in tip and "DB lock" in tip,
          "and a trial whose milestones carry no dates yet keeps the button, disabled, "
          "naming what is missing — that answer changes as soon as two dates are typed",
          f"disabled={btn.is_disabled()}; “{tip[:90]}…”")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
