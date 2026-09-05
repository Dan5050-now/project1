"""The per-column filters, on the six tables that were asked for and nowhere else.

A spreadsheet's column filter, which is a specific thing and not just "hides rows":

  1. IT IS ON THE SIX TABLES ASKED FOR, and on no others. A funnel on every heading in
     the application would be noise on a four-row child sub-table, and the request named
     the tables that are long enough to need one.
  2. TICKING NARROWS THE TABLE, and the rows that remain are the rows that match.
  3. TWO COLUMNS NARROW TOGETHER - type AND phase, not type OR phase.
  4. THE VALUES OFFERED ARE WHAT THE OTHER COLUMNS LEAVE REACHABLE, which is what makes
     it feel like a spreadsheet. A column is excluded from its OWN filter when its list
     is built, so a choice can be widened and not only narrowed; it is not excluded from
     the others, so two filters can between them leave a column with a single value -
     exactly what a spreadsheet does, and cleared the same way.
  5. IT NARROWS THE TABLE AND NOT THE FIGURES. The charts and tiles are the plan, and a
     row hidden here is still in the plan. The filter bar at the top of the page is the
     control that changes what the figures mean; two controls that both said "filter"
     and both moved the numbers would be one too many.
  6. A ROW BEING TYPED IS NEVER HIDDEN. A draft has empty cells by definition, so any
     filter would hide the row the user is working in.
  7. LOADING A FILE CLEARS THEM. A filter chosen against the old plan, still running
     over the new one, is the worst kind of missing data.

    python tools/test_colfilter.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
SMALL = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.8.xlsx"
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.16.xlsx"

# The six sections named in the request, by the sheet each one draws.
WANT = {"Project", "Person", "MonthlyEstimate", "PeriodFTEStandard", "RoleFactor"}

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def open_panel(pg, sheet, col, scope="#t-proj"):
    """Open one column's filter. The scroll is settled FIRST and separately: the panel
    closes on scroll (it is anchored to a heading that moves), so scrolling into view and
    clicking in the same tick opens it and shuts it again."""
    sel = f"{scope} table[data-sheet='{sheet}'] thead th .fbtn[data-fcol='{col}']"
    pg.eval_on_selector(sel, "e => e.scrollIntoView({block:'center'})")
    pg.wait_for_timeout(400)
    pg.eval_on_selector(sel, "e => e.dispatchEvent("
                             "new MouseEvent('mousedown', {bubbles:true, cancelable:true}))")
    pg.wait_for_timeout(350)


def offered(pg):
    return pg.evaluate("() => [...document.querySelectorAll('#colf .colf-list label span')]"
                       ".map(e => e.textContent)")


def keep_only(pg, names):
    """Tick exactly these values and apply."""
    pg.evaluate("""(names) => {
        for (const l of document.querySelectorAll('#colf .colf-list label')){
          const want = names.includes(l.querySelector('span').textContent);
          const i = l.querySelector('input');
          if (i.checked !== want) i.click();
        }}""", names)
    pg.wait_for_timeout(150)
    pg.eval_on_selector("#colf [data-fapply]", "e => e.dispatchEvent("
                        "new MouseEvent('mousedown', {bubbles:true, cancelable:true}))")
    pg.wait_for_timeout(700)


def col_values(pg, sheet, col, scope="#t-proj"):
    return pg.evaluate("""([s, c, sc]) => [...document.querySelectorAll(
        sc + " table[data-sheet='" + s + "'] tbody td[data-col='" + c + "']")]
        .map(e => e.textContent.trim())""", [sheet, col, scope])


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.set_input_files("#picker", str(SMALL))
    pg.wait_for_selector("#tabs:not([hidden])", timeout=30000)
    pg.evaluate("() => { S.who = 'Test'; }")     # so no name dialog interrupts an edit

    # ---- 1. where the funnels are ------------------------------------------
    print("1. the six tables that were asked for, and no others")
    # Every tab in turn: only the pane on screen is drawn, so a survey that stayed on
    # one tab would miss the tables belonging to the others.
    seen = {}
    survey = """() => {
        const o = {};
        for (const t of document.querySelectorAll('table.data-t[data-sheet]'))
          o[t.dataset.sheet] = Math.max(o[t.dataset.sheet] || 0,
                                        t.querySelectorAll('thead .fbtn').length);
        return o;}"""
    for tab, prep in (("Source data (project)", None),
                      ("Source data (person)", None),
                      ("General assumptions",
                       "() => { S.genView.pws='rows'; S.genView.rf='rows'; renderKeepingTab(); }")):
        pg.click(f"text={tab}")
        pg.wait_for_timeout(1100)
        if prep:
            pg.evaluate(prep)
            pg.wait_for_timeout(900)
        for k, v in pg.evaluate(survey).items():
            seen[k] = max(seen.get(k, 0), v)
    withf = {k for k, v in seen.items() if v}
    check(WANT <= withf, "every table named in the request has column filters",
          ", ".join(f"{k}={seen[k]}" for k in sorted(WANT & set(seen))))
    check(not (withf - WANT), "and no other table has them",
          ", ".join(sorted(withf - WANT)) or "none")

    # ---- 2 and 3. narrowing -------------------------------------------------
    print("\n2. ticking narrows the table, and two columns narrow TOGETHER")
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1100)
    before = len(col_values(pg, "Project", "project_type"))
    open_panel(pg, "Project", "project_type")
    types = offered(pg)
    check(len(types) > 1, "the panel offers the column's distinct values", str(types))
    keep_only(pg, types[:1])
    got = col_values(pg, "Project", "project_type")
    check(got and set(got) == set(types[:1]),
          "one value ticked leaves only the rows holding it",
          f"{before} rows → {len(got)}, all {types[0]!r}")

    open_panel(pg, "Project", "clinical_phase")
    phases = offered(pg)
    reachable = set(pg.evaluate("""(t) => S.model.raw.Project
        .filter(r => r.project_type === t)
        .map(r => String(r.clinical_phase ?? ''))""", types[0]))
    check(set(phases) <= reachable,
          "a second column offers only what the FIRST one leaves reachable",
          f"phases offered {sorted(phases)} ⊆ phases of {types[0]!r} {sorted(reachable)}")
    keep_only(pg, phases[:1])
    rows_t = col_values(pg, "Project", "project_type")
    rows_p = col_values(pg, "Project", "clinical_phase")
    check(rows_t and set(rows_t) == set(types[:1]) and set(rows_p) == set(phases[:1]),
          "and the two narrow TOGETHER — type AND phase, not type OR phase",
          f"{len(rows_t)} row(s), all {types[0]!r} + {phases[0]!r}")

    # ---- 4. the column being edited still offers everything -----------------
    open_panel(pg, "Project", "project_type")
    again = offered(pg)
    reachable_types = set(pg.evaluate("""(ph) => S.model.raw.Project
        .filter(r => String(r.clinical_phase ?? '') === ph)
        .map(r => String(r.project_type ?? ''))""", phases[0]))
    check(set(again) == reachable_types and len(again) > 1,
          "a narrowed column still offers everything the OTHER columns allow, "
          "so a choice can be widened and not only narrowed",
          f"narrowed to 1 value, {len(again)} still offered "
          f"(every type having a {phases[0]!r} row)")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)

    # ---- 5. the figures are untouched ---------------------------------------
    print("\n3. it narrows the TABLE, not the plan")
    totals = pg.evaluate("""() => {
        let t = 0; for (const v of S.calc.projMonth.values()) t += v;
        return {total: +t.toFixed(2), projects: Object.keys(S.model.projects).length,
                rows: S.model.raw.Project.length};}""")
    check(totals["rows"] == before and totals["projects"] == before,
          "every project is still in the plan and still in the totals",
          f"{totals['rows']} rows in the model, {totals['total']} FTE-months")

    # ---- 6. a draft is never hidden -----------------------------------------
    drafted = pg.evaluate("""() => {
        const t = document.querySelector("table[data-sheet='Project'] [data-ins]");
        if (!t) return null;
        t.click();
        return document.querySelectorAll("table[data-sheet='Project'] tbody tr").length;}""")
    pg.wait_for_timeout(800)
    isnew = pg.evaluate("() => S.model.raw.Project.filter(r => r.__new).length")
    shown = pg.evaluate("""() => [...document.querySelectorAll(
        "#t-proj table[data-sheet='Project'] tbody tr")].length""")
    check(isnew >= 1 and shown >= 1,
          "a row still being typed is never hidden by a filter, empty though it is",
          f"{isnew} draft(s), {shown} row(s) on screen while a filter is on")
    pg.evaluate("() => discardEdits()")
    pg.wait_for_timeout(700)

    # ---- 7. a load clears them ----------------------------------------------
    print("\n4. loading a file clears them")
    still = pg.evaluate("() => Object.keys(S.colf).length")
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_timeout(5000)
    check(still and not pg.evaluate("() => Object.keys(S.colf).length"),
          "filters chosen against the old plan do not survive into the new one",
          f"{still} sheet(s) filtered before the load, "
          f"{pg.evaluate('() => Object.keys(S.colf).length')} after")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
