"""Measure the application at the volume REQ-NFR-03 names, and say whether X-04 matters.

REQ-NFR-03: 100 projects, 1,000 people, order 8,000 assignments, a 60-month horizon, and
"tables of that height are virtualised". X-04 of the UI component list recorded that
virtualisation as built; it never was. This decides by measurement whether that is a
defect to fix or a requirement to move.

What is timed, and why each one:

  import        picking the file to the first painted screen. The one number a user
                actually waits on, and the only one they experience as "slow".
  tab switch    rendering a tab from scratch. This is where row count bites: the two
                Overall tables are the tall ones, and they render every row.
  edit          committing one cell. It rebuilds the model and re-renders, so it is the
                cost paid on EVERY keystroke-to-blur, many times an hour.
  filter        opening a column filter panel on a 1,000-row table.
  rows/nodes    how much DOM is actually made. The reason to virtualise, if there is one.

Run against the small file too, so the figures have something to be a multiple OF.

    python tools/build_stress_workbook.py --keep
    python tools/measure_scale.py
"""

import pathlib
import statistics
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

FILES = [
    ("10x10   (today's typical)", ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.10.xlsx"),
    ("50x50   (a busy portfolio)", ROOT / "templates" / "PRAP_SourceData_Scenarios_50x50_v1.0.xlsx"),
    ("100x1000 (REQ-NFR-03)", ROOT / "templates" / "PRAP_SourceData_Stress_1000_v1.0.xlsx"),
]

# Anything a person waits on beyond this reads as a hang rather than a pause. Chosen
# before the numbers were seen, so the verdict is not fitted to them.
BUDGET_MS = {"import": 5000, "tab": 1000, "edit": 1000, "filter": 600}


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def measure(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(300)
    t = pg.evaluate("() => performance.now()")
    pg.set_input_files("#picker", str(path))
    # Wait for the tab strip to be showing AND the first table to have rows in it.
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=180000)
    pg.wait_for_function(
        "() => document.querySelectorAll('#t-overall .grid-t tbody tr').length > 0",
        timeout=180000)
    imp = pg.evaluate("() => performance.now()") - t

    out = {"import": imp}
    # Widen to the full horizon the requirement names, so the month columns are real.
    # THE HORIZON THE REQUIREMENT NAMES. This matters more than it looks: the Overall
    # tables are rows x MONTHS, so cell count scales with the horizon. Measured at the
    # default 24 months the Overall tab switches in 632 ms; at the 60 months REQ-NFR-03
    # names it is five times that. Measuring at the default would have answered the
    # wrong question.
    pg.evaluate("() => { S.from = S.calc.lo; S.to = Math.min(S.calc.hi, S.calc.lo + 59);"
                "        renderKeepingTab(); }")
    pg.wait_for_timeout(1200)

    per_tab = {"t-proj": [], "t-pers": [], "t-overall": []}
    for _ in range(4):
        for tab in per_tab:
            t0 = pg.evaluate("() => performance.now()")
            pg.click(f'nav button[data-tab="{tab}"]')
            pg.wait_for_function(f"() => !document.getElementById('{tab}').hidden")
            per_tab[tab].append(pg.evaluate("() => performance.now()") - t0)
    out["tab"] = med(per_tab["t-overall"])          # the tall one, which is the question
    out["tabProj"] = med(per_tab["t-proj"])
    out["tabPers"] = med(per_tab["t-pers"])
    out["tabWorst"] = max(per_tab["t-overall"])

    pg.click('nav button[data-tab="t-pers"]')
    pg.wait_for_timeout(600)
    edits = []
    for i in range(3):
        t0 = pg.evaluate("() => performance.now()")
        pg.evaluate(f"""() => {{
          const t = document.querySelector('#t-pers table.data-t[data-sheet="Person"]');
          const i = [...t.querySelectorAll('thead th')].findIndex(x => x.dataset.cid === 'department');
          const td = t.querySelectorAll('tbody tr')[0].querySelectorAll('td')[i];
          td.focus(); td.textContent = 'Programming';
          td.dispatchEvent(new Event('input', {{bubbles:true}})); td.blur();
        }}""")
        pg.wait_for_timeout(50)
        edits.append(pg.evaluate("() => performance.now()") - t0)
    out["edit"] = med(edits)

    t0 = pg.evaluate("() => performance.now()")
    pg.evaluate("""() => {
      const b = document.querySelector('#t-pers table.data-t[data-sheet="Person"] .fbtn');
      if (b) b.click();
    }""")
    pg.wait_for_timeout(40)
    out["filter"] = pg.evaluate("() => performance.now()") - t0
    pg.keyboard.press("Escape")

    out.update(pg.evaluate("""() => {
      const t0 = performance.now(); calculate(S.model);
      const calc = performance.now() - t0;
      return {calcMs: calc};
    }"""))
    out.update(pg.evaluate("""() => {
      const rows = [...document.querySelectorAll('#t-overall .grid-t tbody tr')].length;
      return {overallRows: rows,
              overallCells: document.querySelectorAll('#t-overall .grid-t td').length,
              nodes: document.getElementsByTagName('*').length,
              people: Object.keys(S.model.people).length,
              projects: Object.keys(S.model.projects).length,
              assignments: (S.model.raw.Assignment || []).length,
              lines: S.calc.lines.length,
              months: S.to - S.from + 1,
              heapMB: performance.memory
                      ? +(performance.memory.usedJSHeapSize / 1048576).toFixed(0) : null};
    }"""))
    return out


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME,
                                 args=["--enable-precise-memory-info"])
    pg = browser.new_page(viewport={"width": 1600, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    results = []
    for label, path in FILES:
        if not path.exists():
            print(f"  (missing: {path.name} - run tools/build_stress_workbook.py --keep)")
            continue
        print(f"measuring {label} ...", flush=True)
        results.append((label, measure(pg, path)))
    browser.close()

print()
print(f"{'fixture':28}{'proj':>6}{'people':>8}{'asg':>7}{'lines':>8}"
      f"{'import':>9}{'tab':>8}{'edit':>8}{'filter':>8}{'rows':>7}{'nodes':>8}{'heap':>7}")
print("-" * 110)
for label, m in results:
    print(f"{label:28}{m['projects']:>6}{m['people']:>8}{m['assignments']:>7}{m['lines']:>8}"
          f"{m['import']:>8.0f}m{m['tab']:>7.0f}m{m['edit']:>7.0f}m{m['filter']:>7.0f}m"
          f"{m['overallRows']:>7}{m['nodes']:>8}"
          f"{(str(m['heapMB']) + 'M') if m['heapMB'] else '-':>7}")

print()
if results:
    label, big = results[-1]
    print(f"AGAINST THE BUDGETS, at {label.strip()}, {big['months']}-month horizon:")
    over = []
    for k, budget in BUDGET_MS.items():
        v = big[k]
        ok = v <= budget
        if not ok:
            over.append(k)
        print(f"  {'ok  ' if ok else 'OVER'} {k:8} {v:7.0f} ms   budget {budget} ms"
              f"   {'' if ok else f'({v / budget:.1f}x over)'}")
    print(f"       (Overall tab worst case {big['tabWorst']:.0f} ms; "
          f"project tab {big['tabProj']:.0f} ms, person tab {big['tabPers']:.0f} ms - "
          f"those two are short tables and are not the question)")
    print()
    print("  WHAT VIRTUALISATION WOULD AND WOULD NOT FIX")
    print(f"    The Overall tab draws {big['overallCells']:,} cells in "
          f"{big['overallRows']:,} rows. Rendering them is what 'tab' measures, and it is "
          f"the cost virtualisation removes.")
    print(f"    The import is {big['import']:.0f} ms, of which the CALCULATION alone is "
          f"{big['calcMs']:.0f} ms for {big['lines']:,} person-months. Virtualisation does "
          f"not touch that, nor the workbook parse. So it cannot be the whole answer to "
          f"import even if it is the whole answer to the tab.")
    if not over:
        print("    Nothing is over budget: virtualisation would change no number a user feels.")
    else:
        print(f"    Over budget: {', '.join(over)}.")

if errors:
    print("\npage errors:", errors[:3])
sys.exit(0)
