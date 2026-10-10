"""Measure the application at a given volume, against budgets fixed before the numbers.

WHAT IT SETTLED, AND WHY IT IS KEPT. REQ-NFR-03 used to name 100 projects and 1,000 people
and say "tables of that height are virtualised"; X-04 of the UI component list recorded
that virtualisation as built, and it never was. Rather than build it or argue, candidate
volumes were built (tools/build_stress_workbook.py) and driven here. The Overall tab, over
a 60-month horizon, against a 1,000 ms budget:

    50 x 100   529 ms  (53% of budget, worst case  571)   <- today's real use
    100 x 100  689 ms  (69%,                        746)
    100 x 150  810 ms  (81%,                        894)  <- REQ-NFR-03 since R-47
    100 x 200  981 ms  (98%,                      1,225)  <- worst case OVER
    50 x 400 1,044 ms  (104%)                             <- the budget is crossed here
    100 x 1000 3,058 ms (306%,                    4,537)

At R-47 the REQUIREMENT moved to 100 x 150 - the largest volume whose WORST case is still
inside budget - and the virtualisation clause was removed. The worst case decided it rather
than the median because medians reproduce between runs to a few per cent and worst cases do
not: 100 x 200 gave 1,026 ms in one run and 1,225 in the next.

THE BINDING QUANTITY IS (PROJECTS + PEOPLE) ROWS x HORIZON MONTHS, because both Overall
tables sit on one tab. 50 x 200 and 100 x 150 are the same 252 rows and measured within
10 ms of each other, so varying the project count alone answers nothing.

What is timed, and why each one:

  import        picking the file to the first painted screen. The one number a user
                actually waits on, and the only one they experience as "slow".
  tab switch    rendering a tab from scratch. This is where row count bites: the two
                Overall tables are the tall ones, and they render every row.
  edit          committing one cell. It rebuilds the model and re-renders, so it is the
                cost paid on EVERY keystroke-to-blur, many times an hour.
  filter        opening a column filter panel, which is built over the whole column.
  rows/nodes    how much DOM is actually made. The reason to virtualise, if there is one.

Run against the small file too, so the figures have something to be a multiple OF.

    python tools/build_stress_workbook.py --keep                      # REQ-NFR-03's volume
    python tools/build_stress_workbook.py --projects 50 --people 100 --keep
    python tools/measure_scale.py

FILES below lists what to measure. Add a line for any fixture on disk; missing ones are
skipped with a note rather than failing the run. Measure candidates in ONE invocation when
comparing them - the browser is launched once, so the comparison is fair.
"""

import pathlib
import statistics
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

def fixture(n_proj, n_people):
    return ROOT / "templates" / f"PRAP_SourceData_Stress_{n_proj}x{n_people}_v1.0.xlsx"


FILES = [
    ("50x100   today's real use", fixture(50, 100)),
    ("100x150  REQ-NFR-03", fixture(100, 150)),
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
print(f"{'fixture':30}{'proj':>5}{'people':>7}{'asg':>6}{'lines':>8}{'mo':>4}"
      f"{'import':>9}{'tab':>8}{'edit':>7}{'filter':>8}{'rows':>6}{'cells':>8}{'heap':>7}")
print("-" * 113)
for label, m in results:
    print(f"{label:30}{m['projects']:>5}{m['people']:>7}{m['assignments']:>6}{m['lines']:>8}"
          f"{m['months']:>4}{m['import']:>8.0f}m{m['tab']:>7.0f}m{m['edit']:>6.0f}m"
          f"{m['filter']:>7.0f}m{m['overallRows']:>6}{m['overallCells']:>8}"
          f"{(str(m['heapMB']) + 'M') if m['heapMB'] else '-':>7}")

print()
print("AGAINST THE BUDGETS  (import 5000 / tab 1000 / edit 1000 / filter 600 ms,")
print("                      fixed before any number was seen)")
print()
for label, m in results:
    bad = [k for k, b in BUDGET_MS.items() if m[k] > b]
    mark = "ok  " if not bad else "OVER"
    detail = ("everything inside budget"
              if not bad else
              ", ".join(f"{k} {m[k]:.0f}ms ({m[k] / BUDGET_MS[k]:.1f}x)" for k in bad))
    print(f"  {mark} {label:30} {detail}")
    if not bad:
        worst = max((m[k] / b, k) for k, b in BUDGET_MS.items())
        print(f"       tightest: {worst[1]} at {100 * worst[0]:.0f}% of its budget"
              f"   (Overall tab worst case {m['tabWorst']:.0f} ms)")

print()
print("WHAT VIRTUALISATION WOULD AND WOULD NOT FIX")
for label, m in results:
    if not [k for k, b in BUDGET_MS.items() if m[k] > b]:
        continue
    print(f"  at {label.strip()}:")
    print(f"    the Overall tab draws {m['overallCells']:,} cells in {m['overallRows']:,} "
          f"rows - that is the cost virtualisation removes")
    print(f"    the import is {m['import']:.0f} ms, of which the CALCULATION alone is "
          f"{m['calcMs']:.0f} ms for {m['lines']:,} person-months - virtualisation touches "
          f"neither that nor the parse")
if all(not [k for k, b in BUDGET_MS.items() if m[k] > b] for _, m in results):
    print("  Nothing measured here is over budget, so virtualisation would change no "
          "number a user feels.")

if errors:
    print("\npage errors:", errors[:3])
sys.exit(0)
