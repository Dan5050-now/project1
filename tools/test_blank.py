"""Build a plan from nothing, entirely through the application, and check it is real.

The landing screen now offers two ways in: load a source workbook, or start blank and
type. The second one is the one that can quietly not work, because every panel below the
first table is drawn from a SELECTED parent, and at the start there is no parent to
select - so a row that cannot be added, or a person who disappears the moment they are
created, would leave the user staring at a page with no way forward.

So this test never touches a fixture. It clicks Start blank and then does what a person
would do, in the order they would do it:

  1. the blank start opens every tab, with the standard lists and settings in place and
     no projects, people or assignments
  2. the reference grids are complete - every (type, phase, period) and every
     (type, phase, period, role) an assignment could reach, so nothing falls back to 1.00
     silently and V-23 never fires
  3. a project can be added and filled in, with nothing selected beforehand
  4. its milestones can be added, and the seven clinical periods DERIVE from them
  5. a person can be added - and is still listed while they have no assignment at all,
     which is the state everybody is in for the minute after they are created
  6. an assignment can be added, and the plan starts producing figures
  7. those figures match the formula computed by hand, to the cent
  8. Save commits, Export produces a workbook, and re-loading it reproduces the plan

    python tools/test_blank.py
"""

import calendar
import pathlib
import sys
import tempfile
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_blank_"))

PROJECT = {"project_id": "PRJ-001", "project_name": "Trial One", "project_type": "NewDrug CT",
           "project_category": "Compound A", "clinical_phase": "Phase 2",
           "outsourcing_type": "Partial outsourcing", "EDC_setup": "by SB",
           "DataReviewSystem_setup": "by CRO", "RBQM_setup": "by SB",
           "EDC_system": "Rave", "planned_member_count": "3",
           # Deliberately wider than the milestones: Save pulls the window in to the
           # span they describe, which is 2027-01-15 .. 2029-03-31, i.e. 27 months.
           "start_date": "2027-01-01", "end_date": "2029-06-30", "status": "Planned"}
MILESTONES = [{"milestone_name": "Protocol (v1)", "milestone_date": "2027-01-15",
               "milestone_seq": "1"},
              {"milestone_name": "CTA submission", "milestone_date": "2027-03-01",
               "milestone_seq": "2"},
              {"milestone_name": "First SIV", "milestone_date": "2027-07-01",
               "milestone_seq": "3"},
              {"milestone_name": "final DB lock", "milestone_date": "2029-03-31",
               "milestone_seq": "4"}]
PERSON = {"person_id": "PSN-001", "person_name": "Alex R.", "department": "Data Management",
          "primary_role": "Lead data manager", "capacity_fte": "1.00"}
# The assignment ends with the project. Since Save derives the project window from the
# milestones, a project now ends at its LAST MILESTONE - so an assignment running past
# that is over-running the project and is reported as V-07, correctly.
ASSIGNMENT = {"project_name": "Trial One", "role_name": "Lead data manager",
              "assign_start_date": "2027-04-10", "assign_end_date": "2029-03-31",
              "person_weight": "0.40"}
# A stretch where this person's share of the project changes. The override REPLACES the
# 0.40 for the months it covers - it does not multiply it - which is the single thing
# about PersonPeriodWeight most likely to be got wrong.
OVERRIDE = {"period_start": "2027-08-01", "period_end": "2027-10-31",
            "weight_override": "0.70", "reason": "Covering the start-up peak"}

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def rows_on_screen(pg, loc):
    """Real rows only - the empty table draws a placeholder inviting you to add one."""
    return pg.locator(f"{loc} tbody tr td[data-col]").evaluate_all(
        "es => new Set(es.map(e => e.dataset.row)).size")


def add_row(pg, loc, values):
    """Click + row, then type into the row it created. Enter commits; Escape reverts."""
    pg.locator(f"{loc} button[data-ins]").last.click()
    pg.wait_for_timeout(900)
    row = pg.locator(f"{loc} tbody tr td[data-col]").evaluate_all(
        "es => Math.max(...es.map(e => +e.dataset.row))")
    for col, v in values.items():
        td = pg.locator(f"{loc} td[data-row='{row}'][data-col='{col}']")
        if td.count() == 0:
            continue                       # a seeded parent key is not editable here
        td.first.click()
        pg.wait_for_timeout(120)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(str(v))
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(320)
    return row


def save(pg):
    pg.click("#saveBtn")
    pg.wait_for_timeout(1400)
    return pg.inner_text("#banner")


def month_key(y, m):
    return y * 12 + m - 1


def coverage(y, m, s, e):
    days = calendar.monthrange(y, m)[1]
    lo, hi = max(date(y, m, 1), s), min(date(y, m, days), e)
    return 0.0 if hi < lo else ((hi - lo).days + 1) / days


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, downloads_path=str(TMP))
    ctx = browser.new_context(accept_downloads=True)
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — a plan built from nothing")
    pg.goto(APP)
    pg.wait_for_timeout(300)

    both = pg.eval_on_selector_all("#empty .drop h2", "es => es.map(e => e.textContent.trim())")
    check(len(both) == 2 and not pg.eval_on_selector("#startBtn", "e => e.disabled"),
          "the landing screen offers both ways in", " / ".join(both))

    pg.click("#startBtn")
    pg.wait_for_timeout(2500)
    rows = pg.evaluate("() => {const o = {}; for (const s of REQUIRED_SHEETS) "
                       "o[s] = S.model.raw[s].length; return o;}")
    opened = pg.evaluate("() => ({tabs: !el('tabs').hidden, filters: !el('filterbar').hidden, "
                         "edit: !el('editbar').hidden, empty: el('empty').hidden, "
                         "exp: !el('exportBtn').disabled, tab: S.tab})")
    check(all(opened[k] for k in ("tabs", "filters", "edit", "empty", "exp"))
          and rows["Lists"] > 0 and rows["Config"] > 0
          and rows["Project"] == 0 and rows["Person"] == 0 and rows["Assignment"] == 0,
          "Start blank opens every tab, with the lists and settings and nothing else",
          f"{rows['Lists']} list values, {rows['Config']} settings, "
          f"0 projects / people / assignments, opens on {opened['tab']}")

    grids = pg.evaluate("""() => {
      const M = S.model, phases = M.lists.clinical_phase || [];
      const cper = M.lists.period_name_clinical || [], oper = M.lists.period_name_others || [];
      const crole = M.lists.role_clinical || [], orole = M.lists.role_others || [];
      const types = M.lists.project_type || [];
      const ct = types.filter(t => CLINICAL_TYPES.has(t)), ot = types.filter(t => !CLINICAL_TYPES.has(t));
      // Schema 6 keys both grids on the work scope, and the seeded rows carry an EMPTY
      // scope - the row that applies to every scope. So the grid is complete when a
      // project of ANY scope finds a weight, which is what stdWeight/stdFactor answer.
      // Asked through those rather than through M.pws directly, because a check that
      // reads the table straight would pass on a grid the application cannot use.
      const scopes = [...(M.lists.work_scope_type || []), ""];
      let pwsMissing = 0, rfMissing = 0;
      for (const t of ct) for (const ph of phases) for (const sc of scopes) {
        const proj = {project_type: t, clinical_phase: ph, work_scope_type: sc};
        for (const p of cper){
          if (stdWeight(M, proj, p) === undefined) pwsMissing++;
          for (const rn of crole) if (stdFactor(M, proj, p, rn) === undefined) rfMissing++;
        }
      }
      for (const t of ot) for (const sc of scopes) {
        const proj = {project_type: t, clinical_phase: null, work_scope_type: sc};
        for (const p of oper) for (const rn of orole)
          if (stdFactor(M, proj, p, rn) === undefined) rfMissing++;
      }
      return {pws: Object.keys(M.pws).length, rf: Object.keys(M.rf).length,
              pwsMissing, rfMissing};
    }""")
    check(grids["pwsMissing"] == 0 and grids["rfMissing"] == 0,
          "the weight and role-factor grids cover every combination a project can reach",
          f"{grids['pws']} standard weights, {grids['rf']} role factors, "
          f"{grids['pwsMissing'] + grids['rfMissing']} gaps")

    # ---- 3. every section is on screen before anything exists -----------------
    # A plan is entered top down. A Milestones table that only appears once the project
    # is saved reads as a Milestones table that does not exist, and someone building a
    # first plan has no way to know it is coming.
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(900)
    proj_panels = pg.eval_on_selector_all("#t-proj .panel h2", "es => es.map(e => e.textContent.trim())")
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    pers_panels = pg.eval_on_selector_all("#t-pers .panel h2", "es => es.map(e => e.textContent.trim())")
    check(proj_panels == ["Projects", "Milestones", "Periods"]
          and pers_panels == ["People", "Assignments", "Weight overrides"],
          "every data-entry section is on screen from the start, with nothing in the plan",
          f"{proj_panels} / {pers_panels}")

    locked = pg.evaluate("""() => {
      const of = sel => {
        const t = document.querySelector(sel);
        return t ? {ins: t.querySelectorAll('button[data-ins]').length,
                    why: (t.querySelector('td.muted[colspan]') || {}).textContent || ''} : null;
      };
      return {ms: of("#t-proj .data-t[data-sheet='Milestone']"),
              asg: of("#t-pers .data-t[data-sheet='Assignment']")};
    }""")
    check(locked["asg"]["ins"] == 0 and "person_id" in locked["asg"]["why"].replace("Add a person above first. An assignment is one person on one project.", "person_id"),
          "a child table with no parent yet is locked, and says why instead of offering + row",
          locked["asg"]["why"][:70])

    pg.click("text=Source data (project)")
    pg.wait_for_timeout(900)
    loc = "#t-proj .data-t[data-sheet='Project']"
    check(pg.locator(f"{loc} button[data-ins]").count() == 1,
          "an empty Projects table still offers + row")
    add_row(pg, loc, PROJECT)

    # ---- 4. milestones under a project that is not saved yet ------------------
    mloc = "#t-proj .data-t[data-sheet='Milestone']"
    check(pg.locator(f"{mloc} button[data-ins]").count() == 1,
          "the Milestones table unlocks as soon as the project has an identifier — "
          "before it is saved")
    for m in MILESTONES:
        add_row(pg, mloc, m)
    parents = pg.evaluate("S.model.raw.Milestone.map(r => r.project_id)")
    check(parents == ["PRJ-001"] * len(MILESTONES),
          "a milestone entered under an unsaved project still inherits its project_id",
          f"{parents}")

    banner = save(pg)
    got = pg.evaluate("() => {const p = S.model.projects['PRJ-001']; return p ? "
                      "{name: p.project_name, type: p.project_type, phase: p.clinical_phase, "
                      " months: p.total_period_months} : null;}")
    check(got and got["name"] == "Trial One" and got["type"] == "NewDrug CT"
          and got["months"] == 27,
          "the project and its milestones save together, and the window is derived from "
          "them: 2027-01-15 .. 2029-03-31, 27 months",
          f"{got}  ·  {banner.strip()[:60]}")

    per = pg.evaluate("() => (S.model.periods['PRJ-001'] || []).map(s => "
                      "[s.period_name, s.__derived === true])")
    check(len(per) >= 4 and all(d for _, d in per)
          and per[0][0] == "Before-Start-up" and per[-1][0] == "Close-out (final)",
          "the periods derive from the milestones just typed in",
          f"{len(per)} periods: {', '.join(n for n, _ in per)}")

    # ---- 5. a person, who must stay visible while unassigned ------------------
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    ploc = "#t-pers .data-t[data-sheet='Person']"
    check(pg.locator(f"{ploc} button[data-ins]").count() == 1,
          "an empty People table still offers + row")
    add_row(pg, ploc, PERSON)

    # ---- 6. the assignment, entered before the person is saved ----------------
    aloc = "#t-pers .data-t[data-sheet='Assignment']"
    check(pg.locator(f"{aloc} button[data-ins]").count() == 1,
          "the Assignments table unlocks as soon as the person has an identifier — "
          "before they are saved")
    add_row(pg, aloc, ASSIGNMENT)
    owner = pg.evaluate("S.model.raw.Assignment.map(r => r.person_id)")
    check(owner == ["PSN-001"],
          "an assignment entered under an unsaved person still inherits their person_id",
          f"{owner}")
    banner = save(pg)
    pg.wait_for_timeout(600)
    shown = rows_on_screen(pg, ploc)
    sel = pg.evaluate("S.selPers")
    check(shown == 1 and sel == "PSN-001",
          "the person is listed and selected once saved",
          f"{shown} row(s) on screen, selected {sel}")
    a = pg.evaluate("() => {const a = S.model.raw.Assignment[0]; return a ? "
                    "{id: a.assignment_id, pid: a.project_id, person: a.person_id, "
                    " role: a.role_name, w: a.person_weight} : null;}")
    check(a and a["pid"] == "PRJ-001" and a["person"] == "PSN-001"
          and a["id"] and a["w"] == 0.4,
          "an assignment can be added by typing the project NAME, and the key is allocated",
          f"{a}")

    findings = pg.evaluate("S.model.findings.filter(f => f.sev === 'error' "
                           "|| f.sev === 'warning').map(f => f.sev + ' ' + f.rule + ': ' + f.msg)")
    check(not findings, "the hand-built plan validates with no errors and no warnings",
          findings[0][:110] if findings else "0 findings above information")

    # ---- 7. the figures, against the formula worked by hand -------------------
    pg.click("text=Overall")
    pg.wait_for_timeout(1200)
    got = pg.evaluate("""() => {
      const out = {};
      for (const [k, v] of S.calc.persMonth) out[k] = v;
      return {pm: out, over: S.model.OVER, hours: S.model.HOURS};
    }""")
    # ymd() rather than the Date itself: a Date crosses evaluate() as a datetime whose
    # tz handling would be one more thing to get right for no gain.
    periods = pg.evaluate("() => (S.model.periods['PRJ-001'] || []).map(s => "
                          "[s.period_name, ymd(s.period_start), ymd(s.period_end), s.weight])")
    # A blank start now seeds the DELIVERED DEFAULTS rather than a placeholder 1.00, so
    # the role factor varies by period and has to be read rather than assumed. Read from
    # the RoleFactor ROWS, not through the application's own lookup, so this stays an
    # independent计算 of the same thing.
    factors = pg.evaluate("""() => Object.fromEntries(S.model.raw.RoleFactor
        .filter(r => r.project_type === 'NewDrug CT' && r.clinical_phase === 'Phase 2'
                  && !r.work_scope_type && r.role_name === 'Lead data manager')
        .map(r => [r.period_name, r.role_factor]))""")
    start, end = date(2027, 4, 10), date(2029, 3, 31)
    segs = [(n, date.fromisoformat(a), date.fromisoformat(b), w) for n, a, b, w in periods]

    def expect(y, m, weight=0.40):
        cov = coverage(y, m, start, end)
        if cov <= 0:
            return 0.0
        first = date(y, m, 1)
        seg = next((s for s in segs if s[1] <= first <= s[2]), None)
        pw = (seg[3] if seg else 1.0) or 1.0
        rf = factors.get(seg[0]) if seg else None
        rf = 1.0 if rf is None else rf         # no row for the period -> 1.00, V-23
        # One person on the role, so nothing is shared and the divisor is 1 (REQ-CAL-14).
        return pw * rf * weight * cov

    bad = []
    for k, v in got["pm"].items():
        key = int(k.split("|")[1])
        y, m = key // 12, key % 12 + 1
        want = expect(y, m)
        if abs(want - v) > 1e-9:
            bad.append(f"{y}-{m:02d}: app {v:.6f} vs {want:.6f}")
    check(len(got["pm"]) == 24 and not bad,
          "every monthly figure equals the formula worked by hand",
          f"{len(got['pm'])} person-months" + (f"; {bad[:2]}" if bad else "; e.g. Apr 2027 "
          f"{got['pm'][[k for k in got['pm'] if k.endswith('|' + str(2027 * 12 + 3))][0]]:.4f} FTE"))

    # ---- 7b. the fourth section: a weight override on that assignment ---------
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    wloc = "#t-pers .data-t[data-sheet='PersonPeriodWeight']"
    check(pg.locator(f"{wloc} button[data-ins]").count() == 1,
          "the Weight overrides table is enterable once an assignment exists")
    add_row(pg, wloc, OVERRIDE)
    save(pg)
    w = pg.evaluate("() => {const w = S.model.raw.PersonPeriodWeight[0]; return w ? "
                    "{aid: w.assignment_id, ov: w.weight_override} : null;}")
    after = pg.evaluate("() => {const o = {}; for (const [k, v] of S.calc.persMonth) o[k] = v; return o;}")
    covered = [month_key(2027, m) for m in (8, 9, 10)]
    moved = {k: round(after[f"PSN-001|{k}"], 4) for k in covered if f"PSN-001|{k}" in after}
    untouched = [k for k in got["pm"] if int(k.split("|")[1]) not in covered
                 and abs(after.get(k, 0) - got["pm"][k]) > 1e-9]
    # The override REPLACES person_weight for those months - it does not multiply it -
    # so the expected figure is the same formula with 0.70 where 0.40 was.
    want_moved = {k: expect(k // 12, k % 12 + 1, 0.70) for k in covered}
    check(w and w["aid"] == "ASG-001" and w["ov"] == 0.7
          and all(abs(after[f"PSN-001|{k}"] - want_moved[k]) < 1e-9 for k in covered)
          and not untouched,
          "the override attaches to the selected assignment and REPLACES the weight for "
          "its months only",
          f"{w}; the three covered months are now {sorted(set(moved.values()))} FTE, "
          f"{len(untouched)} other months changed")

    # ---- 8. export, and read it back -----------------------------------------
    with pg.expect_download() as dl:
        pg.click("#exportBtn")
    out = TMP / "blank_plan.xlsx"
    dl.value.save_as(out)
    pg2 = ctx.new_page()
    pg2.on("pageerror", lambda e: errors.append(str(e)))
    pg2.goto(APP)
    pg2.wait_for_timeout(300)
    pg2.set_input_files("#picker", str(out))
    pg2.wait_for_timeout(4000)
    back = pg2.evaluate("() => ({rows: {Project: S.model.raw.Project.length, "
                        "Milestone: S.model.raw.Milestone.length, "
                        "Person: S.model.raw.Person.length, "
                        "Assignment: S.model.raw.Assignment.length, "
                        "PersonPeriodWeight: S.model.raw.PersonPeriodWeight.length}, "
                        "pm: (() => {const o = {}; for (const [k, v] of S.calc.persMonth) o[k] = v; "
                        "return o;})(), "
                        "bad: S.model.findings.filter(f => f.sev !== 'information').length})")
    same = (back["rows"] == {"Project": 1, "Milestone": 4, "Person": 1, "Assignment": 1,
                             "PersonPeriodWeight": 1}
            and set(back["pm"]) == set(after)
            and all(abs(back["pm"][k] - after[k]) < 1e-9 for k in after))
    check(same and back["bad"] == 0,
          "the exported workbook reproduces the plan exactly",
          f"{out.stat().st_size:,} bytes, {back['rows']}, {back['bad']} findings above information")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
