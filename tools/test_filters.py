"""The filter bar: what it can narrow by, and what the horizon does when it moves.

Two changes and one guard.

  1. OUTSOURCING TYPE joins the filter conditions, and every filter now takes SEVERAL
     values at once. Nothing ticked means All, one ticked reads as that value, more than
     one reads as a count; Clear empties one filter and Reset empties them all.

  2. The HORIZON follows the filters. Narrow to one project type and the window is still
     the one the whole portfolio needed, so a two-year span goes mostly empty and the
     reader is looking at a chart of nothing with no way to tell whether that is the
     answer or the view. Changing a filter now pulls From and To in to the months the
     surviving rows actually reach.

  3. Except when nothing survives. A filter matching no project leaves the window where
     it was, because jumping to an arbitrary span would hide the reason the screen is
     empty. And typing in From or To is the user moving the window themselves - that is
     left alone.

And the change log:

  4. A button beside the unsaved-change counter opens every pending change - when, which
     tab, which section, which row, which item, what it was and what it is now - newest
     first, in a dialog that closes, goes full screen, and scrolls.

    python tools/test_filters.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.4.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
P = "#t-proj .data-t[data-sheet='Project']"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def horizon(pg):
    return pg.evaluate("() => [el('fFrom').value, el('fTo').value]")


def span(pg):
    """The months the surviving rows really reach, computed from the model, not the UI."""
    return pg.evaluate("""() => {
      const pids = new Set(activeProjects()), sids = new Set(activePeople());
      let lo = Infinity, hi = -Infinity;
      const scan = (m, keep) => { for (const [k, v] of m){ if (!(v > 1e-9)) continue;
        const i = k.lastIndexOf('|'); if (!keep.has(k.slice(0, i))) continue;
        const n = +k.slice(i + 1); if (n < lo) lo = n; if (n > hi) hi = n; } };
      scan(S.calc.projMonth, pids); scan(S.calc.persMonth, sids);
      const f = k => `${Math.floor(k/12)}-${String(k%12+1).padStart(2,'0')}`;
      return isFinite(lo) ? [f(lo), f(hi)] : null;}""")


def pick(pg, fid, *values):
    """Tick values in one filter. The control is a <details> holding checkboxes, so it
    has to be opened before they can be clicked."""
    pg.click(f"#{fid} summary")
    pg.wait_for_timeout(300)
    for v in values:
        pg.check(f"#{fid} .msp input[value='{v}']")
        pg.wait_for_timeout(900)
    pg.click("h1")                       # anywhere outside puts the panel away
    pg.wait_for_timeout(400)


def unpick(pg, fid, *values):
    pg.click(f"#{fid} summary")
    pg.wait_for_timeout(300)
    for v in values:
        pg.uncheck(f"#{fid} .msp input[value='{v}']")
        pg.wait_for_timeout(900)
    pg.click("h1")
    pg.wait_for_timeout(400)


def edit(pg, col, text):
    td = pg.locator(f"{P} td[data-col='{col}']").first
    td.click()
    pg.wait_for_timeout(160)
    pg.keyboard.press("Control+A")
    pg.keyboard.type(text)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(450)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — filters, horizon, and the change log")
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)

    # ---- 1. outsourcing type -------------------------------------------------
    if pg.locator("#fOut").count() == 0:
        check(False, "Outsourcing joins the filter bar", "there is no #fOut control at all")
        print("\nFAILURES: the filter does not exist in this build")
        browser.close()
        sys.exit(1)
    # Schema 7: the scope filter follows work_scope_type. outsourcing_type has become
    # outsourcing_scope_det - free text - and a drop-down built from whatever sentences
    # people have typed is not a filter.
    opts = pg.eval_on_selector_all("#fOut .msp input", "es => es.map(e => e.value)")
    real = pg.evaluate("[...new Set(Object.values(S.model.projects)"
                       ".map(p => p.work_scope_type))].filter(Boolean)")
    check(sorted(opts) == sorted(real) and pg.inner_text("#fOut summary").strip() == "All",
          "Work scope joins the filter bar, offering exactly the values in the file",
          ", ".join(opts))

    all_projects = pg.evaluate("activeProjects().length")
    pick(pg, "fOut", "fully in-housed")
    narrowed = pg.evaluate("() => ({n: activeProjects().length, "
                           "all: activeProjects().every(p => "
                           "S.model.projects[p].work_scope_type === 'fully in-housed')})")
    check(narrowed["n"] and narrowed["n"] < all_projects and narrowed["all"]
          and pg.inner_text("#fOut summary").strip() == "fully in-housed",
          "choosing one narrows the page to projects of that scope, and it says which",
          f"{all_projects} projects -> {narrowed['n']}")

    # ---- 1b. several values at once ------------------------------------------
    pick(pg, "fOut", "fully outsourced")
    two = pg.evaluate("""() => ({n: activeProjects().length, chosen: [...S.f.out],
        all: activeProjects().every(p => S.f.out.has(
             S.model.projects[p].work_scope_type))})""")
    check(two["n"] > narrowed["n"] and two["all"] and len(two["chosen"]) == 2
          and pg.inner_text("#fOut summary").strip() == "2 selected",
          "a second value WIDENS the same filter — the two are an OR, not an AND",
          f"{narrowed['n']} -> {two['n']} projects; summary reads "
          f"{pg.inner_text('#fOut summary').strip()!r}")

    unpick(pg, "fOut", "fully outsourced")

    # ---- 2. the horizon follows ----------------------------------------------
    check(list(horizon(pg)) == span(pg),
          "and the horizon is pulled in to the months those projects reach",
          f"{horizon(pg)} vs the model's {span(pg)}")

    pick(pg, "fType", "NewDrug CT")
    check(list(horizon(pg)) == span(pg),
          "a second filter re-fits it again, against both conditions together",
          f"{horizon(pg)}, {pg.evaluate('activeProjects()')}")

    # ---- 3. the guards --------------------------------------------------------
    before = horizon(pg)
    unpick(pg, "fType", "NewDrug CT")
    # The fixture keeps type and scope in step, so a biosimilar trial is never
    # 'fully in-housed' and this pair still matches nothing.
    pick(pg, "fType", "Biosimilar CT (Healthy)")
    check(pg.evaluate("activeProjects().length") == 0 and horizon(pg) == before,
          "a combination that matches nothing leaves the window where it was",
          f"{before} kept, {pg.evaluate('activeProjects().length')} projects match")

    # Clear empties one filter without hunting for the ticks still on.
    pg.click("#fOut summary")
    pg.wait_for_timeout(300)
    pg.click("#fOut [data-msclear]")
    pg.wait_for_timeout(1200)
    check(pg.evaluate("S.f.out.size") == 0
          and pg.inner_text("#fOut summary").strip() == "All"
          and pg.evaluate("S.f.type.size") == 1,
          "Clear empties that one filter and leaves the others alone",
          f"out={pg.evaluate('[...S.f.out]')}, type={pg.evaluate('[...S.f.type]')}")

    pg.click("#fReset")
    pg.wait_for_timeout(1300)
    check(pg.evaluate("REQUIRED_SHEETS && Object.values(S.f).every(v => v.size === 0)")
          and pg.inner_text("#fType summary").strip() == "All",
          "Reset filters empties every one of them")

    pg.fill("#fFrom", "2027-01")
    pg.dispatch_event("#fFrom", "change")
    pg.wait_for_timeout(1000)
    check(horizon(pg)[0] == "2027-01",
          "typing in From is the user moving the window, and is left alone",
          f"{horizon(pg)}")

    # ---- 4. the change log ----------------------------------------------------
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1200)
    check(pg.eval_on_selector("#chgBtn", "e => e.disabled"),
          "with nothing pending, the details button is disabled")

    edit(pg, "project_name", "ONV-101 Phase 1 (rev)")
    edit(pg, "project_category", "Onvelaris II")
    pg.locator(f"{P} button[data-ins]").first.click()
    pg.wait_for_timeout(1000)
    n = pg.evaluate("S.pending.length")
    check(n == 3 and not pg.eval_on_selector("#chgBtn", "e => e.disabled"),
          "three changes later it is enabled", f"{n} pending")

    pg.click("#chgBtn")
    pg.wait_for_timeout(800)
    rows = pg.eval_on_selector_all(
        "#chgBody tbody tr",
        "es => es.map(e => [...e.querySelectorAll('td')].map(t => t.textContent.trim()))")
    head = pg.eval_on_selector_all("#chgBody thead th", "es => es.map(e => e.textContent)")
    check(pg.eval_on_selector("#changes", "e => e.open") and len(rows) == 3
          and head == ["time", "tab", "section", "row", "item", "before", "after"],
          "the dialog opens and lists every pending change with all six details",
          f"{len(rows)} rows, columns {head}")

    newest, oldest = rows[0], rows[-1]
    check(newest[4] == "(new row)" and oldest[4] == "project_name"
          and oldest[5] == "ONV-101 Phase 1" and oldest[6] == "ONV-101 Phase 1 (rev)",
          "newest first, and each row reads before -> after",
          f"newest {newest[4]!r}; oldest {oldest[5]!r} -> {oldest[6]!r}")

    check(all(r[0] and ":" in r[0] for r in rows) and all(r[1] and r[2] for r in rows),
          "every row carries the time it happened, its tab and its section",
          f"e.g. {newest[0]} · {newest[1]} · {newest[2]} · row {newest[3]}")

    pg.click("#chgBig")
    pg.wait_for_timeout(600)
    big = pg.evaluate("""() => {const d = el('changes');
        return {cls: d.classList.contains('big'), w: d.getBoundingClientRect().width,
                label: el('chgBig').textContent};}""")
    pg.click("#chgBig")
    pg.wait_for_timeout(600)
    small = pg.evaluate("el('changes').getBoundingClientRect().width")
    check(big["cls"] and big["w"] > small and big["label"] == "Exit full screen",
          "full screen widens it, and the button offers the way back",
          f"{small:.0f}px -> {big['w']:.0f}px")

    scrolls = pg.evaluate("""() => {const b = el('chgBody');
        return getComputedStyle(b).overflowY === 'auto' || getComputedStyle(b).overflowY === 'scroll';}""")
    check(scrolls, "the body scrolls, so a long log stays readable")

    pg.click("#chgClose")
    pg.wait_for_timeout(500)
    check(not pg.eval_on_selector("#changes", "e => e.open"), "Close closes it")

    pg.click("#discardBtn")
    pg.wait_for_timeout(1400)
    check(pg.evaluate("S.pending.length") == 0
          and pg.eval_on_selector("#chgBtn", "e => e.disabled"),
          "and once the changes are gone, so is the button")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
