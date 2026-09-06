"""The three lookup columns: where a figure got its SIZE, said on the screen that shows it.

Every figure in this application is

    standard FTE  x  period weight  x  the share (role factor / sharers) x person weight
                                       x month coverage

and until now the screens showed the middle of that and none of the ends. A Periods row
read 'Start-up x1.20' — a fifth heavier than WHAT, answerable only by leaving the tab and
reading a 48-row matrix on General assumptions. A Monthly estimation row read
'automatic_fte 0.34' with nothing to say which period selected it or how many people the
role was divided between, which are the two things that actually explain a figure that is
not the size somebody expected.

  1. THE PERIODS TABLE NAMES THE STANDARD BESIDE THE WEIGHT, and multiplies the two, so
     the row carries the month's demand rather than half of the expression for it.
  2. BOTH MONTHLY ESTIMATION PANELS NAME THE PERIOD. The project's, and the person's.
  3. THE PERSON'S ALSO NAMES THE DIVISOR — how many people held that role that month. The
     project's does NOT: a project month is divided between several roles, each with its
     own count, so one number there would be an average of things that are not comparable.
  4. ALL THREE ARE LOOKUPS. Read-only, marked as such, and absent from the sheet's own
     columns — so no amount of editing or saving can write a stale copy of a standard into
     a file and have it survive the standards being changed afterwards.
  5. THEY NAME WHAT THE ARITHMETIC USED. Every figure shown is compared against the
     calculation's own line, not merely against a plausible number.
  6. A MISSING STANDARD SAYS SO and names V-19, rather than printing the 1.00 the
     calculation falls back to. That fallback is a degradation; showing it as though it
     were a standard would hide the very thing V-19 exists to report.

    python tools/test_lookup.py
"""

import pathlib
import sys
import tempfile
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_lookup_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []
BASE = prap_io.read_xlsx(ROOT / "templates" / "PRAP_SourceData_Template_v1.14.xlsx")


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def fixture():
    """One project over three months, every figure workable out by hand.

    Sep  Start-up            standard 4.00  weight 1.00  ->  4.00 a month
    Oct  Conduct (interim)   standard 6.00  weight 1.50  ->  9.00 a month
    Nov  Conduct (final)     NO standard                 ->  the V-19 case

    One role is held by one person in September and by two in October, so `sharers`
    has something to say that is not the same in every row.
    """
    S = {k: (list(v) if isinstance(v, list) else v) for k, v in BASE.items()}
    S["Project"] = [{"project_id": "PRJ-A", "project_name": "Alpha",
                     "project_type": "NewDrug CT", "clinical_phase": "Phase 3",
                     "work_scope_type": "fully in-housed", "project_category": "Cat",
                     "start_date": date(2026, 9, 1), "end_date": date(2026, 11, 30),
                     "status": "Active", "__row": 2}]
    S["Milestone"] = []
    S["ProjectPeriod"] = [
        {"project_id": "PRJ-A", "period_name": "Start-up", "period_seq": 1,
         "period_start": date(2026, 9, 1), "period_end": date(2026, 9, 30),
         "weight": 1.00, "__row": 2},
        {"project_id": "PRJ-A", "period_name": "Conduct (interim)", "period_seq": 2,
         "period_start": date(2026, 10, 1), "period_end": date(2026, 10, 31),
         "weight": 1.50, "__row": 3},
        {"project_id": "PRJ-A", "period_name": "Conduct (final)", "period_seq": 3,
         "period_start": date(2026, 11, 1), "period_end": date(2026, 11, 30),
         "weight": 2.00, "__row": 4},
    ]
    S["PeriodFTEStandard"] = [
        {"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
         "work_scope_type": None, "period_name": "Start-up",
         "standard_fte": 4.00, "__row": 2},
        {"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
         "work_scope_type": None, "period_name": "Conduct (interim)",
         "standard_fte": 6.00, "__row": 3},
    ]                                     # Conduct (final) deliberately absent — V-19
    S["RoleFactor"] = [
        {"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
         "work_scope_type": None, "period_name": pn, "role_name": rn,
         "role_factor": rf, "absorbed_by": None, "__row": 2 + i}
        for i, (pn, rn, rf) in enumerate(
            [(p, r, f) for p in ("Start-up", "Conduct (interim)", "Conduct (final)")
             for r, f in (("Lead data manager", 0.6), ("Data Analyst", 0.4))])]
    S["Person"] = [{"person_id": f"PSN-{i}", "person_name": f"P{i}",
                    "capacity_fte": 1.0, "__row": 1 + i} for i in (1, 2, 3)]
    S["Assignment"] = [
        # the whole project
        {"assignment_id": "ASG-1", "person_id": "PSN-1", "project_id": "PRJ-A",
         "role_name": "Lead data manager", "person_weight": 1.0, "__row": 2},
        # October only, so ASG-1's role has one holder in September and two in October
        {"assignment_id": "ASG-2", "person_id": "PSN-2", "project_id": "PRJ-A",
         "role_name": "Lead data manager", "person_weight": 1.0,
         "assign_start_date": date(2026, 10, 1), "assign_end_date": date(2026, 10, 31),
         "__row": 3},
        {"assignment_id": "ASG-3", "person_id": "PSN-3", "project_id": "PRJ-A",
         "role_name": "Data Analyst", "person_weight": 1.0, "__row": 4},
    ]
    S["PersonPeriodWeight"] = []
    S["MonthlyEstimate"] = []
    out = TMP / "lookup.xlsx"
    prap_io.write_xlsx(S, out)
    return out


BOOK = fixture()

HEADERS = """(t) => [...t.querySelectorAll('thead th')].map(x => x.innerText.trim())"""
ROWS = """(t) => [...t.querySelectorAll('tbody tr')].map(
           r => [...r.querySelectorAll('td')].slice(1).map(c => c.innerText.trim()))"""


def table_with(pg, pane, col):
    """The table in `pane` whose heading row mentions `col`."""
    return pg.evaluate_handle(
        """([pane, col]) => [...document.querySelectorAll(pane + ' table.data-t')]
             .find(t => [...t.querySelectorAll('thead th')]
                          .some(x => x.innerText.trim().split(' ')[0] === col))""",
        [pane, col])


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_context(viewport={"width": 1600, "height": 1000}).new_page()
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.set_input_files("#picker", str(BOOK))
    pg.wait_for_selector("#tabs:not([hidden])", timeout=30000)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1200)

    # ---------------------------------------------- 1. the Periods table
    print("1. the Periods table names the standard the period selects")
    per = table_with(pg, "#t-proj", "period_name")
    head = pg.evaluate(HEADERS, per)
    rows = pg.evaluate(ROWS, per)
    check(head.index("standard_fte lookup") == head.index("weight") + 1,
          "standard_fte sits immediately after weight", " | ".join(head))
    by = {r[1]: r for r in rows}
    check(by["Start-up"][6] == "4.00 → 4.00 a month",
          "the standard, and what this project's weight makes of it",
          f"Start-up weight {by['Start-up'][5]} → {by['Start-up'][6]}")
    check(by["Conduct (interim)"][6] == "6.00 → 9.00 a month",
          "a weight other than 1.00 shows the product, not just the standard",
          f"6.00 × {by['Conduct (interim)'][5]} → {by['Conduct (interim)'][6]}")

    print("\n2. it names the figure the CALCULATION used, not a second lookup")
    same = pg.evaluate("""() => {
        const want = {};
        for (const L of S.calc.lines)
          if (L.project_id === 'PRJ-A') want[L.period_name] = L.standard_fte;
        return want;}""")
    check(same.get("Start-up") == 4.0 and same.get("Conduct (interim)") == 6.0,
          "the calculation's own lines carry the same standards", str(same))
    check(abs(pg.evaluate("""() => {
            const k = 2026 * 12 + 9;                 // 2026-10
            return S.calc.projMonth.get('PRJ-A|' + k) || 0;}""") - 9.00) < 5e-9,
          "and 6.00 × 1.50 really is that project-month: 9.00")

    print("\n3. a missing standard says so and names V-19")
    check(by["Conduct (final)"][6] == "none — V-19",
          "not the 1.00 the calculation falls back to — that is the degradation V-19 "
          "reports, and printing it as a standard would hide it",
          by["Conduct (final)"][6])

    print("\n4. it is a LOOKUP: not editable, and not a column of the sheet")
    check(pg.evaluate("""(t) => {
            const i = [...t.querySelectorAll('thead th')]
                        .findIndex(x => x.innerText.trim().startsWith('standard_fte'));
            return [...t.querySelectorAll('tbody tr')].every(r => {
              const td = r.querySelectorAll('td')[i];
              return td && !td.isContentEditable && !td.dataset.col
                     && td.classList.contains('drvcell');});}""", per),
          "every cell is read-only and marked as looked up")
    check(pg.evaluate("() => !(S.headers.ProjectPeriod || []).includes('standard_fte')")
          and pg.evaluate("""() => S.model.raw.ProjectPeriod.every(
                r => !Object.prototype.hasOwnProperty.call(r, 'standard_fte'))"""),
          "and it is on no ProjectPeriod row, so a save cannot write a stale copy of it")

    # ---------------------------------------------- 5. the project's months
    print("\n5. the project's Monthly estimation names the period")
    pg.evaluate("() => { switchEstimation('project', 'PRJ-A'); }")
    pg.wait_for_timeout(300)
    pg.click("#estYes")
    pg.wait_for_timeout(1200)
    est = table_with(pg, "#t-proj", "automatic_fte")
    ehead = pg.evaluate(HEADERS, est)
    erows = {r[0]: r for r in pg.evaluate(ROWS, est)}
    check(ehead.index("period lookup▾") == ehead.index("difference lookup▾") + 1,
          "period sits immediately after difference", " | ".join(ehead))
    check(erows["2026-09"][4] == "Start-up ×1.00"
          and erows["2026-10"][4] == "Conduct (interim) ×1.50",
          "each month names its period AND the weight that period carried",
          f"Sep {erows['2026-09'][4]} · Oct {erows['2026-10'][4]}")
    check(erows["2026-10"][2] == "9.00",
          "beside the automatic figure that period produced", erows["2026-10"][2])
    check(not any(h.startswith("sharers") for h in ehead),
          "and NOT the divisor: a project month is split between several roles, each "
          "with its own count, so one number here would average things that do not "
          "compare", " | ".join(ehead))

    # ---------------------------------------------- 6. the person's months
    print("\n6. the person's Monthly estimation names the period AND the divisor")
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    pg.evaluate("""() => { S.selPers = 'PSN-1'; S.selAsg = 'ASG-1';
                           renderKeepingTab(); }""")
    pg.wait_for_timeout(900)
    pg.evaluate("() => { switchEstimation('assignment', 'ASG-1'); }")
    pg.wait_for_timeout(300)
    pg.click("#estYes")
    pg.wait_for_timeout(1200)
    pest = table_with(pg, "#t-pers", "automatic_fte")
    phead = pg.evaluate(HEADERS, pest)
    prows = {r[0]: r for r in pg.evaluate(ROWS, pest)}
    check(phead.index("period lookup▾") == phead.index("difference lookup▾") + 1
          and phead.index("sharers lookup▾") == phead.index("period lookup▾") + 1,
          "period then sharers, both after difference", " | ".join(phead))
    check(prows["2026-09"][5] == "1 (only holder)"
          and prows["2026-10"][5] == "2 share this role",
          "one holder in September, two in October — said in words, not just a digit",
          f"Sep {prows['2026-09'][5]} · Oct {prows['2026-10'][5]}")
    check(pg.evaluate("""() => {
            const want = {};
            for (const L of S.calc.lines)
              if (L.assignment_id === 'ASG-1') want[L.month % 12] = L.sharers;
            return want[8] === 1 && want[9] === 2;}"""),
          "which is the divisor the calculation actually used, not a second count")
    check(prows["2026-09"][4] == "Start-up ×1.00", "the period is named here too",
          prows["2026-09"][4])
    check(pg.evaluate("() => !(S.headers.MonthlyEstimate || []).includes('period')")
          and pg.evaluate("() => !(S.headers.MonthlyEstimate || []).includes('sharers')"),
          "neither is a MonthlyEstimate column, so neither is ever written to the file")

    # ---------------------------------------------- 7. they behave like columns
    print("\n7. and they behave like every other column of the table")
    got = pg.evaluate("""() => {
        S.colf.MonthlyEstimate = {period: new Set(['Start-up \\u00d71.00'])};
        renderKeepingTab();
        const t = [...document.querySelectorAll('#t-pers table.data-t')]
          .find(t => [...t.querySelectorAll('thead th')]
                       .some(x => x.innerText.trim().startsWith('automatic_fte')));
        const rows = [...t.querySelectorAll('tbody tr')].map(
          r => (r.querySelectorAll('td')[1] || {}).innerText.trim());
        delete S.colf.MonthlyEstimate; renderKeepingTab();
        return rows;}""")
    check(got == ["2026-09"], "a derived column filters like a stored one", str(got))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
