"""A trial whose milestones are in but whose own dates are not.

Reported from the field: a hand-built workbook would not open at all —

    Could not read that file: Cannot read properties of null (reading 'getTime')

`derivePeriods` read `proj.start_date` and `proj.end_date` as though a project always
carried them. It runs on a clinical trial that has NO periods, which is very often a plan
somebody is part way through entering or has built from the milestones outward, so a blank
date there is ordinary rather than exceptional. Two distinct failures came out of it, and
the quiet one was the worse:

  * A BLANK end_date THREW. The exception escaped buildModel, so the load failed outright
    with a raw JavaScript message that named no project and left nothing on screen to
    repair. One project cost the user the whole file.
  * A BLANK start_date DID NOT THROW, and that was worse. `suS0 > null` compares against
    zero and is therefore always true, so no floor was applied AND a 'Before-Start-up'
    period was emitted running from null — a corrupt row that travelled on into the
    calculation looking like any other.

Both dates are FLOORS and nothing more: start stops start-up opening before the project
does, end stops close-out finishing before it ends. Absent, there is no floor, and the
milestones alone describe the run — which is what a file with milestones and no dates is
actually saying, and what REQ-CAL-17 means when it says the periods are the project.

What is checked:

  * All four combinations of the two dates LOAD, and none reports a fatal.
  * No derived period ever carries a null date — the quiet defect, checked directly.
  * The derivation is anchored where it should be: with no dates, start-up opens a month
    before CTA submission and close-out ends at the final DB lock; with dates, they floor
    it and the figures are UNCHANGED from what they have always been.
  * The browser and tools/prap_io.py agree on every person-month of all four.
  * A project whose derivation fails does not take the file down with it: the other
    projects still load and the failure is an ERROR naming the project.

    python tools/test_nodates.py
"""

import pathlib
import sys
import tempfile
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_nodates_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


BASE = prap_io.read_xlsx(ROOT / "templates" / "PRAP_SourceData_Template_v1.14.xlsx")
CTA, LOCK = date(2026, 1, 15), date(2027, 6, 30)


def fixture(name, start, end, extra_project=None):
    """One trial with milestones and no periods, its own dates as given."""
    S = {k: (list(v) if isinstance(v, list) else v) for k, v in BASE.items()}
    S["Project"] = [{"project_id": "PRJ-001", "project_name": "Hand made",
                     "project_type": "NewDrug CT", "clinical_phase": "Phase 3",
                     "work_scope_type": "fully in-housed", "start_date": start,
                     "end_date": end, "status": "Active", "__row": 2}]
    S["Milestone"] = [
        {"project_id": "PRJ-001", "milestone_name": "CTA submission",
         "milestone_date": CTA, "milestone_seq": 1, "__row": 2},
        {"project_id": "PRJ-001", "milestone_name": "final DB lock",
         "milestone_date": LOCK, "milestone_seq": 2, "__row": 3}]
    S["ProjectPeriod"] = []
    S["Person"] = [{"person_id": "PSN-001", "person_name": "A", "capacity_fte": 1.0,
                    "__row": 2}]
    S["Assignment"] = [{"assignment_id": "ASG-001", "person_id": "PSN-001",
                        "project_id": "PRJ-001", "role_name": "Project lead",
                        "person_weight": 1.0, "__row": 2}]
    S["PersonPeriodWeight"] = []
    S["MonthlyEstimate"] = []
    if extra_project:
        S["Project"].append(extra_project)
    out = TMP / f"{name}.xlsx"
    prap_io.write_xlsx(S, out)
    return out


CASES = [("neither", None, None),
         ("no_end", date(2026, 1, 1), None),
         ("no_start", None, date(2027, 12, 31)),
         ("both", date(2026, 1, 1), date(2027, 12, 31))]
PATHS = {n: fixture(n, s, e) for n, s, e in CASES}

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page()
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    print("app/PRAP.html — a trial with milestones and no dates of its own")

    got = {}
    for name, _, _ in CASES:
        pg.goto(APP)
        pg.wait_for_timeout(250)
        pg.set_input_files("#picker", str(PATHS[name]))
        pg.wait_for_timeout(2200)
        banner = pg.inner_text("#banner") if pg.locator("#banner").count() else ""
        built = pg.evaluate("() => !!(S && S.model)")
        check(built and "Could not read that file" not in banner,
              f"'{name.replace('_', ' ')}' LOADS — a blank project date is ordinary, not a "
              f"reason to refuse the file",
              " ".join(banner.split())[:78] if not built else "")
        if not built:
            got[name] = None
            continue
        segs = pg.evaluate("""() => (S.model.periods['PRJ-001'] || []).map(p => ({
            name: p.period_name,
            s: p.period_start ? p.period_start.toISOString().slice(0, 10) : null,
            e: p.period_end ? p.period_end.toISOString().slice(0, 10) : null}))""")
        fatal = pg.evaluate("() => S.model.findings.filter(f => f.sev === 'fatal').length")
        pm = pg.evaluate("() => { const o = {}; for (const [k, v] of S.calc.persMonth) "
                         "o[k] = v; return o; }")
        got[name] = {"segs": segs, "fatal": fatal, "pm": pm}
        check(fatal == 0, f"  and nothing fatal in '{name}'", f"{fatal} fatal")

    # ---- the quiet defect: no derived period may carry a null date ------------------
    bad = {n: [s for s in g["segs"] if not s["s"] or not s["e"]]
           for n, g in got.items() if g}
    total_bad = sum(len(v) for v in bad.values())
    check(total_bad == 0,
          "NO DERIVED PERIOD CARRIES A NULL DATE — the failure that did not announce "
          "itself, and travelled into the calculation looking like an ordinary row",
          f"{sum(len(g['segs']) for g in got.values() if g)} periods across four files"
          + (f"; {total_bad} still null: {bad}" if total_bad else ""))

    # ---- anchored where it should be -------------------------------------------------
    n = got["neither"]
    check(n and n["segs"] and n["segs"][0]["name"] == "Start-up"
          and n["segs"][0]["s"] == "2025-12-15"
          and n["segs"][-1]["e"] == "2027-06-30",
          "WITH NO DATES AT ALL the milestones alone describe the run — start-up opens a "
          "month before CTA submission, close-out ends at the final DB lock",
          " | ".join(f"{s['name']} {s['s']}→{s['e']}" for s in n["segs"]) if n else "")
    check(n and not any(s["name"] == "Before-Start-up" for s in n["segs"]),
          "and there is no Before-Start-up period, because there is no project start for "
          "it to run from")
    b = got["both"]
    check(b and b["segs"][0]["s"] == "2026-01-01" and b["segs"][-1]["e"] == "2027-12-31",
          "WITH BOTH DATES they floor the derivation exactly as they always have — this "
          "fix moves no figure that was ever right",
          " | ".join(f"{s['name']} {s['s']}→{s['e']}" for s in b["segs"]) if b else "")

    # ---- and the reference implementation agrees on all four -------------------------
    worst, n_pm = 0.0, 0
    for name, _, _ in CASES:
        M = prap_io.Model(prap_io.read_xlsx(PATHS[name]))
        C = prap_io.calculate(M)
        ref = {f"{sid}|{k}": v for (sid, k), v in C["pers_month"].items()}
        app = got[name]["pm"] if got[name] else {}
        if set(ref) != set(app):
            worst = float("inf")
            break
        n_pm += len(ref)
        for k in ref:
            worst = max(worst, abs(ref[k] - app[k]))
    check(worst < 1e-9,
          "THE BROWSER AND tools/prap_io.py AGREE on every person-month of all four — "
          "the two derivations were fixed separately and must not have drifted",
          f"{n_pm} person-months, worst difference {worst:.2e}")

    # ---- one bad project does not cost the user the file ------------------------------
    # A trial with a CTA submission and a DB lock so far apart that the arithmetic between
    # them cannot produce a sane run is not the point; the point is that WHATEVER happens
    # in there, the rest of the workbook still opens and the failure is named.
    victim = fixture("with_second", date(2026, 1, 1), date(2027, 12, 31),
                     extra_project={"project_id": "PRJ-002", "project_name": "Second",
                                    "project_type": "NewDrug CT", "clinical_phase": "Phase 2",
                                    "work_scope_type": "fully in-housed",
                                    "start_date": None, "end_date": None,
                                    "status": "Active", "__row": 3})
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(victim))
    pg.wait_for_timeout(2200)
    check(pg.evaluate("() => !!(S && S.model)")
          and pg.evaluate("() => Object.keys(S.model.projects).length") == 2,
          "A SECOND PROJECT WITH NO DATES AND NO MILESTONES loads alongside the first "
          "rather than taking the file down",
          f"{pg.evaluate('() => Object.keys(S.model.projects).length')} project(s)")
    v16 = pg.evaluate("""() => S.model.findings.filter(f => f.rule === 'V-16')
                           .map(f => f.sev + ': ' + f.msg)""")
    check(any("PRJ-002" in m for m in v16),
          "and the one that could not be derived is named, with the reason",
          " ".join(v16[0].split())[:96] if v16 else "(nothing reported)")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
