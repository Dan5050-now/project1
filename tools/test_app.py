"""Drive app/PRAP.html in a real browser and check it against the reference.

A screenshot proves the page rendered. These checks prove it is RIGHT: the
calculation is compared cell-by-cell with tools/verify_source_workbook.py, and the
export is re-read by openpyxl - an independent .xlsx implementation - and put back
through the same verifier.

    python tools/test_app.py
"""

import json
import pathlib
import subprocess
import sys
from collections import defaultdict
from datetime import date

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.8.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

sys.path.insert(0, str(ROOT / "tools"))
_ref = (ROOT / "tools" / "verify_source_workbook.py").read_text().split("def main")[0]
exec(_ref)                                    # rows, d, months_between, coverage, CLINICAL_TYPES


def reference_person_months(path):
    wb = load_workbook(path)
    P = {r["project_id"]: r for r in rows(wb["Project"])}
    PER = defaultdict(list)
    for r in rows(wb["ProjectPeriod"]):
        PER[r["project_id"]].append(r)
    RF = {(r["project_type"], r["clinical_phase"], r["period_name"], r["role_name"]): r["role_factor"]
          for r in rows(wb["RoleFactor"])}
    PPW = defaultdict(list)
    for r in rows(wb["PersonPeriodWeight"]):
        PPW[r["assignment_id"]].append(r)

    def seg(pid, y, m):
        for s in PER.get(pid, []):
            if d(s["period_start"]) <= date(y, m, 1) <= d(s["period_end"]):
                return s
        return None

    def weight(a, y, m):
        for w in PPW.get(a["assignment_id"], []):
            if d(w["period_start"]) <= date(y, m, 1) <= d(w["period_end"]):
                return w["weight_override"]
        return a["person_weight"]

    out = defaultdict(float)
    for a in rows(wb["Assignment"]):
        pr = P[a["project_id"]]
        s = d(a["assign_start_date"])
        e = d(a["assign_end_date"]) or d(pr["end_date"])
        ph = pr["clinical_phase"] if pr["project_type"] in CLINICAL_TYPES else None
        for y, m in months_between(s, e):
            cov = coverage(y, m, s, e)
            if cov <= 0:
                continue
            sg = seg(a["project_id"], y, m)
            rf = RF.get((pr["project_type"], ph, sg["period_name"] if sg else None, a["role_name"]), 1.0)
            out[(a["person_id"], y * 12 + m - 1)] += (sg["weight"] if sg else 1.0) * rf * weight(a, y, m) * cov
    return out


def main():
    failures, notes = [], []
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME, downloads_path="/tmp")
        ctx = b.new_context(accept_downloads=True)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda dlg: dlg.accept())
        pg.goto(APP)
        pg.wait_for_timeout(200)
        pg.set_input_files("#picker", str(DUMMY))
        pg.wait_for_timeout(4000)

        findings = pg.evaluate("S.model.findings.map(f => f.rule + ': ' + f.msg)")
        if findings:
            failures.append(f"app reports {len(findings)} findings on a file the verifier calls clean; "
                            f"first: {findings[0][:110]}")

        app_pm = pg.evaluate("() => { const o = {}; "
                             "for (const [k, v] of S.calc.persMonth) o[k] = v; return o; }")
        ref = reference_person_months(DUMMY)
        got = {(k.split("|")[0], int(k.split("|")[1])): v for k, v in app_pm.items()}
        if set(got) != set(ref):
            failures.append(f"person-month coverage differs: app {len(got)}, reference {len(ref)}")
        bad = [k for k in set(got) & set(ref) if abs(got[k] - ref[k]) > 1e-6]
        if bad:
            k = bad[0]
            failures.append(f"{len(bad)} calculated values differ; e.g. {k}: "
                            f"app {got[k]:.6f} vs reference {ref[k]:.6f}")
        else:
            notes.append(f"calculation matches the reference on all {len(ref)} person-months")

        with pg.expect_download() as dl:
            pg.click("#exportBtn")
        exported = "/tmp/prap_export_test.xlsx"
        dl.value.save_as(exported)

        pg2 = ctx.new_page()
        pg2.goto(APP)
        pg2.wait_for_timeout(200)
        pg2.set_input_files("#picker", exported)
        pg2.wait_for_timeout(4000)
        n = pg2.evaluate("S.model.findings.length")
        if n:
            failures.append(f"the exported file re-imports with {n} findings")
        else:
            notes.append("export re-imports with zero findings")

        if errors:
            failures.append(f"page errors: {errors[:2]}")
        b.close()

    # The export must also satisfy a reader that is not ours.
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_source_workbook.py"), exported],
                       capture_output=True, text=True)
    if "ERRORS: none" not in r.stdout:
        failures.append("the exported file does not pass verify_source_workbook.py")
    else:
        notes.append("export passes the Python verifier via openpyxl")

    print("app/PRAP.html")
    for n_ in notes:
        print("  ok  ", n_)
    for f in failures:
        print("  FAIL", f)
    print()
    print("FAILURES: none" if not failures else f"FAILURES ({len(failures)})")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
