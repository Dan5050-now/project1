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
# Both dummy sizes are checked. The small one is not a lighter version of the same
# test - it has a different period mix, a different overlap profile and a single-person
# role pool, so it exercises paths the large set happens not to reach.
FIXTURES = [ROOT / "templates" / "PRAP_SourceData_Dummy_v1.12.xlsx",
            ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.4.xlsx"]
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
    # Schema 6 keys the table on the work scope too, with an EMPTY scope meaning every
    # scope - see lookup() in verify_source_workbook.py, which this reuses.
    RF = {(r["project_type"], r["clinical_phase"], scope_of(r), r["period_name"],
           r["role_name"]): r["role_factor"] for r in rows(wb["RoleFactor"])}
    # REQ-CAL-16, worked out here independently: which absent roles land on this one.
    ABSORB = defaultdict(list)
    for r in rows(wb["RoleFactor"]):
        if r.get("absorbed_by"):
            ABSORB[(r["project_type"], r["clinical_phase"], scope_of(r),
                    r["period_name"], r["absorbed_by"])].append(r["role_name"])
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

    # Who holds which role on which project, month by month. The role factor is what
    # the ROLE costs the project, not what each person holding it costs, so it is
    # divided between them - worked out here independently of the application, which
    # is the whole point of a reference.
    ASG = list(rows(wb["Assignment"]))
    sharers = defaultdict(set)
    for a in ASG:
        pr = P[a["project_id"]]
        s, e = assignment_window(PER, pr, a)
        for y, m in months_between(s, e):
            if coverage(y, m, s, e) > 0:
                sharers[(a["project_id"], a["role_name"], y, m)].add(a["person_id"])

    out = defaultdict(float)
    for a in ASG:
        pr = P[a["project_id"]]
        s, e = assignment_window(PER, pr, a)
        ph = pr["clinical_phase"] if pr["project_type"] in CLINICAL_TYPES else None
        for y, m in months_between(s, e):
            cov = coverage(y, m, s, e)
            if cov <= 0:
                continue
            sg = seg(a["project_id"], y, m)
            rf = lookup(RF, (pr["project_type"], ph), scope_of(pr),
                        (sg["period_name"] if sg else None, a["role_name"]))
            rf = 1.0 if rf is None else rf
            pn = sg["period_name"] if sg else None
            for absent in (lookup(ABSORB, (pr["project_type"], ph), scope_of(pr),
                                  (pn, a["role_name"])) or []):
                if sharers[(a["project_id"], absent, y, m)]:
                    continue
                extra = lookup(RF, (pr["project_type"], ph), scope_of(pr), (pn, absent))
                rf += 0.0 if extra is None else extra
            share = len(sharers[(a["project_id"], a["role_name"], y, m)]) or 1
            out[(a["person_id"], y * 12 + m - 1)] += (
                (sg["weight"] if sg else 1.0) * (rf / share) * weight(a, y, m) * cov)
    return out


def main(DUMMY):
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

        # Informational findings are explanations, not problems: V-14 and V-21 both fire
        # on these fixtures to say WHY an inspection after the DB lock is legitimate.
        # Anything above information on a file the verifier calls clean is a failure.
        findings = pg.evaluate("S.model.findings.filter(f => f.sev !== 'information')"
                               ".map(f => f.sev + ' ' + f.rule + ': ' + f.msg)")
        info = pg.evaluate("S.model.findings.filter(f => f.sev === 'information').length")
        if findings:
            failures.append(f"app reports {len(findings)} findings above information on a file the "
                            f"verifier calls clean; first: {findings[0][:110]}")
        else:
            notes.append(f"no findings above information ({info} informational)")

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
        n = pg2.evaluate("S.model.findings.filter(f => f.sev !== 'information').length")
        if n:
            failures.append(f"the exported file re-imports with {n} findings above information")
        else:
            notes.append("export re-imports with no findings above information")

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

    print(f"app/PRAP.html  x  {DUMMY.name}")
    for n_ in notes:
        print("  ok  ", n_)
    for f in failures:
        print("  FAIL", f)
    return failures


if __name__ == "__main__":
    only = [pathlib.Path(a) for a in sys.argv[1:]]
    all_failures = []
    for fixture in (only or FIXTURES):
        all_failures += main(fixture)
        print()
    print("FAILURES: none" if not all_failures else f"FAILURES ({len(all_failures)})")
    sys.exit(1 if all_failures else 0)
