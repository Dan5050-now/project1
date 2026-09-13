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

    python tools/test_unstaffed.py
"""

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
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.10.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def make(dst, staffed=False, status=None):
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
    p.append(row)
    for r in per.iter_rows(min_row=2, values_only=True):
        if r[0] == "PRJ-001":
            nr = list(r)
            nr[0] = "PRJ-099"
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
      return {n: f.length, sev: f[0] ? f[0].sev : null, msg: f[0] ? f[0].msg : null,
              cls: f[0] ? ruleClass(f[0].rule) : null,
              refuses: f[0] ? refuses(f[0]) : null,
              months: n, total: +tot.toFixed(2), peak: +peak.toFixed(2),
              peakMonth: iso(peakMonth)};
    }""")


def figures(msg):
    """total, months, peak and peak-month as the finding states them."""
    m = re.search(r"needs ([\d.]+) FTE-months across (\d+) month\(s\), from "
                  r"([\d-]+), peaking at ([\d.]+) FTE in ([\d-]+)", msg or "")
    return (float(m.group(1)), int(m.group(2)), float(m.group(4)), m.group(5)) if m else None


tmp = pathlib.Path(tempfile.mkdtemp())
bare, staffed, done = tmp / "bare.xlsx", tmp / "staffed.xlsx", tmp / "done.xlsx"
make(bare)
make(staffed, staffed=True)
make(done, status="Completed")

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
