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
  2. BOTH MONTHLY ESTIMATION PANELS CARRY THE WHOLE DERIVATION, TERM BY TERM — the period,
     the standard it selects, the project's weight, how much of the month it ran, and
     their product. A reader who disagrees with an automatic figure can see WHICH of the
     inputs they disagree with, which naming only the period did not answer.
  3. THE PERSON'S ADDS THEIR CLAIM ON THAT MONTH: role factor ÷ sharers × person weight ×
     coverage, ending in the PERCENTAGE of the month it won — never as a product equal to
     the figure, because since R-32 it is not one. The claim is normalised against every
     other claim on that project-month (REQ-CAL-19), so 0.60 × 1.00 × 1.00 is 0.60 and the
     figure is 2.40. The two halves are therefore closed off separately.
     An OVERRIDE is one term with two sources, not two multiplied terms: it REPLACES
     person_weight for the months it covers (REQ-PSN-05), and the cell says so.
     `sharers` stays as a short column of its own, where it can be sorted and filtered.
  4. ALL OF THEM ARE LOOKUPS. Read-only, marked as such, and absent from the sheet's own
     columns — so no amount of editing or saving can write a stale copy of a standard into
     a file and have it survive the standards being changed afterwards.
  5. THEY NAME WHAT THE ARITHMETIC USED. Every figure shown is compared against the
     calculation's own line, not merely against a plausible number.
  6. A FALLBACK SAYS IT IS ONE and names its rule — V-19 for a missing standard, V-23 for
     a missing role factor, V-12 for a month in no period. A bare 1.00 is indistinguishable
     from a standard that really is 1.00, which is the whole reason those rules exist.

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
    # November only, so the override term has a month to itself and September and
    # October stay hand-checkable without it.
    S["PersonPeriodWeight"] = [
        {"assignment_id": "ASG-1", "period_start": date(2026, 11, 1),
         "period_end": date(2026, 11, 30), "weight_override": 0.5,
         "reason": "half time", "__row": 2}]
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
    check(erows["2026-09"][4] ==
          "Start-up (standard 4.00) × period weight (1.00) × month run (1.00) = 4.00"
          and erows["2026-10"][4] ==
          "Conduct (interim) (standard 6.00) × period weight (1.50) × month run (1.00) "
          "= 9.00",
          "every term of the month's demand, named and valued, and their product",
          erows["2026-10"][4])
    check(erows["2026-10"][2] == "9.00",
          "which is the automatic figure two columns to its left", erows["2026-10"][2])
    check(erows["2026-11"][4] ==
          "Conduct (final) (standard 1.00 by default — no row for this period, V-19) "
          "× period weight (2.00) × month run (1.00) = 2.00",
          "a fallback term says it is one and names its rule — a bare 1.00 there is "
          "indistinguishable from a standard that really is 1.00",
          erows["2026-11"][4])
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

    print("\n6b. and on the person's table the derivation has TWO halves")
    sep = prows["2026-09"][4].split("\n")
    check(len(sep) == 2 and sep[0] ==
          "Start-up (standard 4.00) × period weight (1.00) × month run (1.00) "
          "= 4.00 — the project's month",
          "the project's whole month, closed off with its own product", sep[0])
    check(sep[1] == "this person's claim: role factor (0.60) ÷ sharers (1) "
                    "× person weight (1.00, no override) × coverage (1.00) "
                    "= 60.0% of it → 2.40",
          "then this person's claim, ending in the PERCENTAGE of that month it won",
          sep[1])
    # The split is the whole point. Since R-32 a person's figure is the month TIMES a
    # normalised share, not the product of their own five terms - 0.60 x 1.00 x 1.00 is
    # 0.60, and the figure is 2.40. Written as one product the cell would assert an
    # arithmetic the application does not do.
    check("% of it" in sep[1] and "= 60.0%" in sep[1],
          "said as a proportion, never as a product that equals the figure — the claim "
          "is measured against the others on that project-month (REQ-CAL-19)")
    oct_ = prows["2026-10"][4].split("\n")[1]
    check("÷ sharers (2)" in oct_ and "= 30.0% of it → 2.70" in oct_,
          "a second holder halves the claim and the percentage follows", oct_)

    print("\n6c. an override REPLACES the person's weight, and is not shown as a factor")
    nov = prows["2026-11"][4].split("\n")[1]
    check("× weight override (0.50, replacing person weight 1.00) ×" in nov,
          "so the cell names both and says which one was used", nov)
    check("person weight (1.00, no override) ×" not in nov
          and "× weight override" in nov and nov.count("weight") == 2,
          "one term with two possible sources, never two multiplied terms — an override "
          "does not multiply person_weight (REQ-PSN-05)")
    check(abs(pg.evaluate("""() => {
            const L = S.calc.lines.find(l => l.assignment_id === 'ASG-1'
                                          && l.month === 2026 * 12 + 10);
            return 100 * L.role_share;}""")
              - float(nov.split("= ")[1].split("%")[0])) < 0.06,
          "and the percentage shown is the share the calculation worked out",
          nov.split("= ")[1])
    check(pg.evaluate("() => !(S.headers.MonthlyEstimate || []).includes('period')")
          and pg.evaluate("() => !(S.headers.MonthlyEstimate || []).includes('sharers')"),
          "neither is a MonthlyEstimate column, so neither is ever written to the file")

    # ---------------------------------------------- 7. they behave like columns
    print("\n7. and they behave like every other column of the table")
    got = pg.evaluate("""() => {
        S.colf.MonthlyEstimate = {sharers: new Set(['1 (only holder)'])};
        renderKeepingTab();
        const t = [...document.querySelectorAll('#t-pers table.data-t')]
          .find(t => [...t.querySelectorAll('thead th')]
                       .some(x => x.innerText.trim().startsWith('automatic_fte')));
        const rows = [...t.querySelectorAll('tbody tr')].map(
          r => (r.querySelectorAll('td')[1] || {}).innerText.trim());
        delete S.colf.MonthlyEstimate; renderKeepingTab();
        return rows;}""")
    check(got == ["2026-09", "2026-11"],
          "a derived column filters like a stored one — the two months this person held "
          "the role alone", str(got))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
