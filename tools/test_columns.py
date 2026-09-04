"""Every column the screen names must exist on the sheet it names it for.

Reported from the field, on the General assumptions tab: the 'Standard period weights'
table showed BLANK values, and an edit typed into one was accepted, counted as an unsaved
change, survived the save prompt — and then vanished.

One cause. Schema 10 renamed PeriodFTEStandard.weight to standard_fte, and
renderGenTab still asked for `weight`. Both halves of the symptom follow from that:

  * READING  `r.weight` on a row that no longer has one is undefined, so every cell in
    both the matrix and the row view rendered empty.
  * WRITING  applyEdit wrote `target.weight`, a key nothing else looks at. It was a real
    pending change, so the editor counted it and Save asked about it — but rawToRows
    writes the columns the SHEET has, so the value was dropped on the next rebuild and
    the cell came back blank. An edit that is accepted, confirmed, saved and then
    silently discarded is the worst of the available failures.

The calculation was right throughout, which is why every one of the twenty-seven other
suites passed: they compare figures, and the figures were correct. Nothing was watching
the names the SCREEN uses.

So this sweeps the whole application: it visits every tab, opens both views of both
standards tables, selects a project and a person so the child panels render, and checks
every column header of every data table against that sheet's schema. A column the
application declares as a lookup or a proxy is exempt — dataTable marks those in the
header itself, so the exemption is read from the page rather than kept as a list here
that would go stale in the same way.

It also checks the reported case end to end: the standards show their values, an edit
takes, survives Save, and MOVES A FIGURE.

    python tools/test_columns.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.16.xlsx"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# Every table on screen, and whether each of its columns is a real column of its sheet.
# A header carrying a .drv badge is a lookup or a proxy the application has declared as
# such, and is deliberately not stored on the row.
SWEEP = """() => {
  const out = [];
  for (const t of document.querySelectorAll('table.data-t[data-sheet]')){
    const sheet = t.dataset.sheet, known = SHEET_HEADERS[sheet] || [];
    for (const th of t.querySelectorAll('thead th')){
      if (th.classList.contains('ins')) continue;         // the row-actions column
      if (th.querySelector('.drv')) continue;             // declared lookup or proxy
      const name = th.textContent.trim();
      if (!known.includes(name)) out.push(sheet + '.' + name);
    }
  }
  return out;
}"""

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 1000})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — the names the screen uses")
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3200)

    bad, seen = [], set()

    def sweep(where):
        found = pg.evaluate(SWEEP)
        n = pg.eval_on_selector_all("table.data-t[data-sheet]", "e => e.length")
        seen.update(pg.eval_on_selector_all("table.data-t[data-sheet]",
                                            "es => es.map(e => e.dataset.sheet)"))
        for f in found:
            if f not in bad:
                bad.append(f"{f} (on {where})")
        return n

    tables = 0
    for label, tab in (("Overall", "t-overall"),
                       ("Source data (project)", "t-proj"),
                       ("Source data (person)", "t-pers"),
                       ("General assumptions", "t-gen")):
        pg.click(f"text={label}")
        pg.wait_for_timeout(1100)
        tables += sweep(label)

    # Both standards tables have two views, and only one of them is on screen at a time.
    # The reported defect was in this one, so visiting it is the point rather than a
    # thoroughness gesture.
    pg.click("text=General assumptions")
    pg.wait_for_timeout(700)
    pg.eval_on_selector_all("#t-gen [data-setview]",
                            "es => es.forEach(e => e.dataset.setview.endsWith('rows') "
                            "&& e.click())")
    pg.wait_for_timeout(1200)
    tables += sweep("General assumptions · rows & editing")

    # A selected assignment brings up the overrides and the manual-estimate panels.
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    pg.evaluate("() => { const a = S.model.raw.Assignment[0]; S.selPers = a.person_id; "
                "S.selAsg = a.assignment_id; renderAll(); showTab('t-pers'); }")
    pg.wait_for_timeout(1200)
    tables += sweep("Source data (person) · assignment selected")

    check(not bad,
          "EVERY COLUMN THE SCREEN NAMES EXISTS ON THE SHEET IT NAMES IT FOR — a renamed "
          "column cannot blank a panel and swallow an edit again",
          f"{tables} table(s) across {len(seen)} sheet(s)"
          + (f"; {len(bad)} unknown: {', '.join(bad[:4])}" if bad else ""))
    check(len(seen) >= 8,
          "and the sweep actually reached the sheets — a check that visits nothing passes "
          "for the wrong reason",
          ", ".join(sorted(seen)))

    # ---- the reported case, end to end ------------------------------------------
    pg.click("text=General assumptions")
    pg.wait_for_timeout(900)
    pg.eval_on_selector_all("#t-gen [data-setview]",
                            "es => es.forEach(e => e.dataset.setview.endsWith('rows') "
                            "&& e.click())")
    pg.wait_for_timeout(1000)
    row = pg.evaluate("""() => (S.model.raw.PeriodFTEStandard.find(x =>
        x.project_type === 'NewDrug CT' && x.clinical_phase === 'Phase 3'
        && x.period_name === 'Start-up' && x.work_scope_type === 'fully in-housed')
        || {}).__row""")
    sel = (f"#t-gen table[data-sheet='PeriodFTEStandard'] "
           f"td[data-row='{row}'][data-col='standard_fte']")
    shown = pg.eval_on_selector(sel, "e => e.textContent.trim()")
    check(shown not in ("", None) and float(shown) > 0,
          "THE STANDARD PERIOD WEIGHTS SHOW THEIR VALUES — the reported blank",
          f"NewDrug CT / Phase 3 / fully in-housed / Start-up reads {shown!r}")

    probe = """() => {
      const pr = S.model.projects['PRJ-003'];
      const seg = (S.model.periods['PRJ-003'] || []).find(s => s.period_name === 'Start-up');
      const k = seg.period_start.getUTCFullYear() * 12 + seg.period_start.getUTCMonth() + 1;
      return {fte: S.calc.projMonth.get('PRJ-003|' + k) || 0,
              std: stdWeight(S.model, pr, 'Start-up')};
    }"""
    before = pg.evaluate(probe)
    pg.eval_on_selector(sel, "e => e.scrollIntoView({block:'center'})")
    pg.click(sel)
    pg.keyboard.press("Control+a")
    pg.type(sel, "9.24")
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(1400)
    after = pg.evaluate(probe)
    on_screen = pg.eval_on_selector(sel, "e => e.textContent.trim()")
    check(after["std"] == 9.24 and on_screen == "9.24"
          and pg.evaluate("() => S.pending.length") == 1,
          "AN EDIT TO ONE TAKES — the cell keeps what was typed, and the assumption "
          "behind it moves with it",
          f"cell {on_screen!r}, stdWeight {before['std']} -> {after['std']}")
    check(abs(after["fte"] / before["fte"] - 9.24 / before["std"]) < 1e-6,
          "AND IT MOVES A FIGURE, in exactly the ratio of the change — the edit reaches "
          "the calculation rather than only the sheet",
          f"PRJ-003's Start-up month {before['fte']:.4f} -> {after['fte']:.4f}, "
          f"a factor of {after['fte'] / before['fte']:.4f}")

    pg.click("#saveBtn")
    pg.wait_for_timeout(1600)
    kept = pg.eval_on_selector(sel, "e => e.textContent.trim()")
    check(kept == "9.24" and pg.evaluate("() => S.pending.length") == 0
          and pg.evaluate("() => stdWeight(S.model, S.model.projects['PRJ-003'], "
                          "'Start-up')") == 9.24,
          "AND IT SURVIVES SAVE — the reported failure was an edit that was accepted, "
          "confirmed, saved, and then silently discarded",
          f"cell reads {kept!r} after Save, nothing pending")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
