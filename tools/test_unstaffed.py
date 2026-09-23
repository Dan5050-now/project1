"""V-36: a project with periods and nobody on it says what it needs.

Reported from the field: a project is added, and the application shows no FTE for it
until somebody is assigned. The figure was computable the whole time - type, phase,
scope and periods are all the standard needs - and REQ-CAL-19 is explicit that the
project-month IS its standard and the people on it DIVIDE it. A divisor of nobody does
not make the demand nought.

Nothing reported it either. V-34 compares demand against applied, which is this gap at
its widest, but V-34 is built from projGap <- projMonth <- the LINES. No assignment, no
line, no entry, no finding: the one project short by the whole of its standard was the
only shortfall the shortfall rule could not see.

  1. IT FIRES, AND ONLY WHERE IT SHOULD
     1a. a project with periods and no assignments raises exactly one V-36
     1b. it is INFORMATION, and its class is INCOMPLETE, so it cannot refuse an edit
     1c. the clean delivered fixture raises none - every project there is staffed
     1d. a project whose status is Completed is history, not a gap, and is skipped

  2. THE FIGURE IS THE ONE THE PROJECT WILL SHOW
     This is the property that makes the rule worth having. A rule that predicts a
     number the application then contradicts is worse than no rule.
     2a. the total it names equals the project's own total once somebody is assigned
     2b. so does the peak, and the month the peak falls in
     2c. and the finding DISAPPEARS the moment the assignment exists

  3. THE TWO IMPLEMENTATIONS AGREE
     3a. tools/prap_io.py raises V-36 on the same project, at the same severity
     3b. with the same total, peak and months - to the hundredth

  4. AND THE TABLE DRAWS IT (R-49)
     The rule says what the month needs; this is the half that shows it.
     4a. a month with demand and nobody on it carries the figure, not a dot
     4b. it is NOT added to the row total, nor to the grand total
     4c. so the project table's applied total still equals the person table's -
         the one reconciliation this screen guarantees (spec sheet 06)
     4d. the unallocated is totalled on a line of its own instead
     4e. NOTHING EXISTING MOVES: the delivered fixture gains no unallocated cell
         and not one of its figures changes
     4f. and the horizon reaches a project that starts after every assignment
         ends - otherwise the figure would be drawn in a month off the screen

    python tools/test_unstaffed.py
"""

import datetime
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.11.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def make(dst, staffed=False, status=None, shift_years=0):
    """The delivered fixture plus one project cloned from PRJ-001 - same type, phase,
    scope and periods - carrying no assignments unless asked for.

    Built rather than committed for the reason test_retired.py gives: the point is the
    DIFFERENCE between this and the delivered plan, and a stale copy would stop being
    the same plan.
    """
    shutil.copy(DUMMY, dst)
    wb = load_workbook(dst)
    p, per, asg = wb["Project"], wb["ProjectPeriod"], wb["Assignment"]
    cols = [c.value for c in p[1]]
    row = [c.value for c in p[2]]
    row[cols.index("project_id")] = "PRJ-099"
    row[cols.index("project_name")] = "Brand new study"
    if status is not None:
        # Named `status` on the sheet; `project_status` is the VALUE LIST that governs
        # it. Getting that wrong is why the first version of this test passed a filter
        # it never applied, so the column is looked up strictly rather than guarded.
        row[cols.index("status")] = status
    if shift_years:
        # Before the append, not after: openpyxl copies the list into cells, so a list
        # edited afterwards changes nothing. (It did, silently, on the first try.)
        for c in ("start_date", "end_date"):
            if c in cols and isinstance(row[cols.index(c)], datetime.datetime):
                d = row[cols.index(c)]
                row[cols.index(c)] = d.replace(year=d.year + shift_years)
    p.append(row)
    pcols = [c.value for c in per[1]]
    for r in per.iter_rows(min_row=2, values_only=True):
        if r[0] == "PRJ-001":
            nr = list(r)
            nr[0] = "PRJ-099"
            # Pushed years into the future for 4f: a project that starts after every
            # assignment in the file has ended, which is where the horizon used to stop.
            if shift_years:
                for c in ("period_start", "period_end"):
                    i = pcols.index(c)
                    if isinstance(nr[i], datetime.datetime):
                        nr[i] = nr[i].replace(year=nr[i].year + shift_years)
            per.append(nr)
    if staffed:
        ac = [c.value for c in asg[1]]
        a = {c: None for c in ac}
        # Blank dates on purpose: REQ-CAL-15 makes them the project's own, which is the
        # window V-36 predicted from. Typing dates here would test a different claim.
        a.update({"assignment_id": "ASG-999", "person_id": "PSN-001",
                  "project_id": "PRJ-099", "role_name": "Lead data manager",
                  "person_weight": 1.0, "estimation_type": "automatic"})
        asg.append([a.get(c) for c in ac])
    wb.save(dst)


def load(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=60000)
    pg.wait_for_timeout(600)
    return pg.evaluate("""() => {
      const f = (S.model.findings || []).filter(x => x.rule === 'V-36');
      let tot = 0, peak = 0, n = 0, peakMonth = null;
      for (const [k, v] of S.calc.projMonth){
        if (!k.startsWith('PRJ-099|')) continue;
        tot += v; n++;
        if (v > peak){ peak = v; peakMonth = +k.slice(k.lastIndexOf('|') + 1); }
      }
      const iso = k => k === null ? null
        : `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, '0')}`;
      // Applied against applied: the one reconciliation this screen guarantees.
      let pm = 0, sm = 0, un = 0;
      for (const [, v] of S.calc.projMonth) pm += v;
      for (const [, v] of S.calc.persMonth) sm += v;
      for (const [, v] of S.calc.projUnallocated) un += v;
      return {n: f.length, sev: f[0] ? f[0].sev : null, msg: f[0] ? f[0].msg : null,
              cls: f[0] ? ruleClass(f[0].rule) : null,
              refuses: f[0] ? refuses(f[0]) : null,
              months: n, total: +tot.toFixed(2), peak: +peak.toFixed(2),
              peakMonth: iso(peakMonth),
              appliedProj: +pm.toFixed(2), appliedPers: +sm.toFixed(2),
              unalloc: +un.toFixed(2), unallocCells: S.calc.projUnallocated.size,
              lo: S.calc.lo, hi: S.calc.hi};
    }""")


def tableFacts(pg):
    """What the Resource by project table actually draws for the new project, read off
    the rendered DOM rather than off the model - the point of R-49 is the SCREEN."""
    pg.evaluate("() => { S.from = S.calc.lo; S.to = S.calc.hi; renderKeepingTab(); }")
    pg.click('nav button[data-tab="t-overall"]')
    pg.wait_for_timeout(900)
    return pg.evaluate("""() => {
      const panel = [...document.querySelectorAll('#t-overall .panel')]
        .find(e => ((e.querySelector('h2') || {}).textContent || '')
                     .startsWith('Resource by project'));
      const rows = [...panel.querySelectorAll('tbody tr')];
      const mine = rows.find(r => r.innerText.includes('PRJ-099'));
      const cells = mine ? [...mine.querySelectorAll('td')] : [];
      const unal = cells.filter(td => td.classList.contains('unal'));
      const grand = rows.find(r => r.classList.contains('grand')
                                && !r.classList.contains('unalrow'));
      const urow = rows.find(r => r.classList.contains('unalrow'));
      const num = t => {
        const m = String(t || '').replace(/[^0-9.]/g, '');
        return m ? +m : 0;
      };
      return {
        unalCells: unal.length,
        unalGlyph: unal.every(td => td.innerText.includes('\\u25E6')),
        unalValues: unal.slice(0, 3).map(td => num(td.innerText)),
        // the row total is the LAST cell of the row
        rowTotal: cells.length ? num(cells[cells.length - 1].innerText) : null,
        rowNote: (mine ? (mine.querySelector('.unals') || {}).innerText : '') || '',
        grandTotal: grand ? num([...grand.querySelectorAll('td')].pop().innerText) : null,
        hasUnalRow: !!urow,
        unalRowTotal: urow ? num([...urow.querySelectorAll('td')].pop().innerText) : null
      };
    }""")


def figures(msg):
    """total, months, peak and peak-month as the finding states them."""
    m = re.search(r"needs ([\d.]+) FTE-months across (\d+) month\(s\), from "
                  r"([\d-]+), peaking at ([\d.]+) FTE in ([\d-]+)", msg or "")
    return (float(m.group(1)), int(m.group(2)), float(m.group(4)), m.group(5)) if m else None


tmp = pathlib.Path(tempfile.mkdtemp())
bare, staffed = tmp / "bare.xlsx", tmp / "staffed.xlsx"
done, future = tmp / "done.xlsx", tmp / "future.xlsx"
make(bare)
make(staffed, staffed=True)
make(done, status="Completed")
make(future, shift_years=6)

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    print("1. IT FIRES, AND ONLY WHERE IT SHOULD")
    b = load(pg, bare)
    check(b["n"] == 1, "1a. a project with periods and no assignments raises one V-36",
          f"{b['n']} finding(s)")
    check(b["sev"] == "information" and b["cls"] == "incomplete" and b["refuses"] is False,
          "1b. it is information, classed incomplete, and refuses nothing",
          f"sev={b['sev']} class={b['cls']} refuses={b['refuses']}")

    clean = load(pg, DUMMY)
    check(clean["n"] == 0, "1c. the delivered fixture raises none - all staffed",
          f"{clean['n']} finding(s)")

    d = load(pg, done)
    check(d["n"] == 0, "1d. a Completed project is history, not a gap, and is skipped",
          f"{d['n']} finding(s)")

    print()
    print("2. THE FIGURE IS THE ONE THE PROJECT WILL SHOW")
    said = figures(b["msg"])
    s = load(pg, staffed)
    check(said is not None, "    the finding states a total, a span and a peak",
          (b["msg"] or "")[:90])
    if said:
        total, months, peak, peak_month = said
        check(abs(total - s["total"]) < 0.005 and months == s["months"],
              "2a. the total and span it named are the project's own once staffed",
              f"said {total:.2f} over {months}, got {s['total']:.2f} over {s['months']}")
        check(abs(peak - s["peak"]) < 0.005 and peak_month == s["peakMonth"],
              "2b. so are the peak and the month it falls in",
              f"said {peak:.2f} in {peak_month}, got {s['peak']:.2f} in {s['peakMonth']}")
    check(s["n"] == 0, "2c. and the finding is gone the moment the assignment exists",
          f"{s['n']} finding(s)")

    print()
    print("4. AND THE TABLE DRAWS IT")
    b2 = load(pg, bare)
    t = tableFacts(pg)
    check(t["unalCells"] > 0 and t["unalGlyph"],
          "4a. the months carry the figure, marked with a glyph and not a dot",
          f"{t['unalCells']} cell(s), first {t['unalValues']}")
    check(abs(t["rowTotal"]) < 0.005,
          "4b. and none of it is in the row total, which is what is APPLIED",
          f"row total {t['rowTotal']}")
    check(abs(b2["appliedProj"] - b2["appliedPers"]) < 0.005,
          "4c. so the project table still reconciles with the person table",
          f"{b2['appliedProj']:.2f} vs {b2['appliedPers']:.2f}")
    check(t["hasUnalRow"] and t["unalRowTotal"] > 0.004
          and abs(t["unalRowTotal"] - b2["unalloc"]) < 0.02,
          "4d. the unallocated is totalled on a line of its own",
          f"line shows {t['unalRowTotal']}, model says {b2['unalloc']:.2f}")

    clean2 = load(pg, DUMMY)
    check(clean2["unallocCells"] == 0
          and abs(clean2["appliedProj"] - clean2["appliedPers"]) < 0.005,
          "4e. the delivered fixture gains no unallocated cell, and still reconciles",
          f"{clean2['unallocCells']} cell(s), applied {clean2['appliedProj']:.2f}")

    far = load(pg, future)
    # The project was pushed 6 years out, past every assignment in the file. Before
    # R-49 the horizon came only off the assignment lines, so its months were not even
    # reachable by "show everything" - the figure would have been drawn off-screen.
    farHi = far["hi"]
    tf = tableFacts(pg)
    check(far["unallocCells"] > 0 and tf["unalCells"] > 0,
          "4f. a project starting after every assignment ends is still reached",
          f"horizon ends {farHi}, {tf['unalCells']} cell(s) drawn")

    check(not errors, "    the page raised no script error", "; ".join(errors[:2]))
    browser.close()

print()
print("3. THE TWO IMPLEMENTATIONS AGREE")
jf = tmp / "bare.prap.json"
subprocess.run([sys.executable, str(ROOT / "tools" / "prap_io.py"), "to-json",
                str(bare), "-o", str(jf)], check=True, capture_output=True)
out = subprocess.run([sys.executable, str(ROOT / "tools" / "prap_io.py"), "validate",
                      str(jf)], capture_output=True, text=True).stdout
ref = [ln for ln in out.splitlines() if "V-36" in ln]
check(len(ref) == 1 and "information" in ref[0],
      "3a. prap_io.py raises the same rule at the same severity",
      (ref[0].strip()[:80] if ref else "not raised"))
mine = figures(ref[0]) if ref else None
check(mine is not None and said is not None and mine == said,
      "3b. with the same total, span, peak and peak month",
      f"reference {mine} vs browser {said}")

shutil.rmtree(tmp, ignore_errors=True)

print()
if fails:
    print("FAILURES: " + "; ".join(fails))
    sys.exit(1)
print("FAILURES: none")
