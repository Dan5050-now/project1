"""Importing a revised workbook over a plan somebody has been working in.

Until now that replaced everything. NR-IMP-02 says it should ask first, then show
what would change, then let the user accept or skip PER SHEET - and never delete.

The engine is pure (src/core/06a_diff.js), so most of this runs against it directly
with two hand-built plans whose every difference is known in advance:

    the plan            the revised workbook
    ----------------    --------------------------------------------------
    PRJ-001 Alpha       PRJ-001 Alpha, end_date moved out three months
    PRJ-002 Beta        PRJ-002 Beta, unchanged
    PRJ-003 Local       (absent - typed by hand, the file never knew it)
                        PRJ-004 Delta   (new)

so the expected answer is: 1 to add, 1 to change, 1 only here, 1 unchanged.

The four things that could each be got wrong, and are each checked:

  * ONLY HERE IS NEVER REMOVED (S-N04). The hand-typed project survives an import
    of a file that has never heard of it. This is the one that would destroy work.
  * a DERIVED column is not a difference (NR-IMP-08). total_period_months in the
    file is stale by construction; it must not appear in the report, and must not
    be written into the plan.
  * a date read from .xlsx and the same date written in a .prap.json are the same
    date, not a change.
  * accepting is PER SHEET: taking Project must not bring in the new Person.

Then the whole flow in a browser, on the Python shell where it is wired up.

    python tools/build_python_app.py && python tools/test_importdiff.py
"""

import json
import pathlib
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
PKG = ROOT / "dist" / "PM_APP_py"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_diff_"))

sys.path.insert(0, str(ROOT / "tools"))
import build_source_workbook as B                                    # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# ------------------------------------------------------------------ fixtures
def project(pid, name, end, months=None):
    return {"project_id": pid, "project_name": name, "project_type": "Others",
            "start_date": "2027-01-01", "end_date": end, "status": "Active",
            # Deliberately stale on one side. It is DERIVED, so it must be invisible
            # to the comparison and must never be written into the plan.
            "total_period_months": months}


def person(sid, name, dept="Ops"):
    return {"person_id": sid, "person_name": name, "department": dept,
            "primary_role": "Main staff", "capacity_fte": 1.00}


def doc(projects, people):
    lists = [{"list_name": n, "value": v, "note_1": None}
             for n, vs in B.LISTS for v in vs]
    config = [{"parameter": k, "value": v, "note": n} for k, v, n in B.CONFIG]
    return {"prap_format": "prap-source-data", "format_version": 1, "sheets": {
        "Project": projects,
        "Milestone": [],
        "ProjectPeriod": [{"project_id": p["project_id"], "period_name": "Planning",
                           "period_seq": 1, "period_start": "2027-01-01",
                           "period_end": p["end_date"], "weight": 1.00}
                          for p in projects],
        "PeriodWeightStandard": [],
        "RoleFactor": [{"project_type": "Others", "clinical_phase": None,
                        "work_scope_type": None, "period_name": "Planning",
                        "role_name": "Main staff", "role_factor": 1.00}],
        "Person": people,
        "Assignment": [],
        "PersonPeriodWeight": [],
        "Lists": lists, "Config": config}}


def write(name, d):
    p = TMP / name
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return p


PLAN = write("plan.prap.json", doc(
    [project("PRJ-001", "Alpha", "2027-06-30", 6),
     project("PRJ-002", "Beta", "2027-09-30", 9),
     project("PRJ-003", "Local, typed by hand", "2027-12-31", 12)],
    [person("PSN-001", "Alex R.")]))

REVISED = write("revised.prap.json", doc(
    [project("PRJ-001", "Alpha", "2027-09-30", 99),      # end moved; total is STALE
     project("PRJ-002", "Beta", "2027-09-30", 9),        # identical
     project("PRJ-004", "Delta", "2028-03-31", 15)],     # new
    [person("PSN-001", "Alex R."),
     person("PSN-002", "Sam T.")]))                      # new, on another sheet


# ------------------------------------------------- 1. the engine, on its own
print("src/core/06a_diff.js — the comparison itself")
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 900})
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.set_input_files("#picker", str(PLAN))
    pg.wait_for_timeout(2000)

    d = pg.evaluate("""async (text) => {
        const incoming = buildModel(readPrapJson(text));
        const diff = importDiff(S.model.raw, incoming.raw);
        const out = {};
        for (const s of Object.keys(diff)) out[s] = {
            add: diff[s].add.length, change: diff[s].change.length,
            onlyHere: diff[s].onlyHere.length, same: diff[s].same,
            cols: diff[s].change.map(c => c.cols.map(x => x.col)).flat(),
            labels: {add: diff[s].add.map(r => diffLabel(s, r)),
                     onlyHere: diff[s].onlyHere.map(r => diffLabel(s, r))}};
        return out;
    }""", REVISED.read_text(encoding="utf-8"))

    P = d["Project"]
    check(P["add"] == 1 and P["change"] == 1 and P["onlyHere"] == 1 and P["same"] == 1,
          "Project: one to add, one to change, one only here, one unchanged",
          f"add {P['add']}, change {P['change']}, onlyHere {P['onlyHere']}, "
          f"same {P['same']}")
    check(P["labels"]["add"] == ["PRJ-004 · Delta"],
          "the added row is the one the file has and the plan does not",
          str(P["labels"]["add"]))
    check(P["labels"]["onlyHere"] == ["PRJ-003 · Local, typed by hand"],
          "and the hand-typed project is reported as ONLY HERE",
          str(P["labels"]["onlyHere"]))
    check(P["cols"] == ["end_date"],
          "the change is end_date ALONE — total_period_months is derived, and a stale "
          "value in the file is not a difference (NR-IMP-08)",
          f"columns reported: {P['cols']}")
    check(d["Person"]["add"] == 1 and d["Person"]["change"] == 0,
          "Person: one to add, nothing changed", str(d["Person"]))
    check(d["Config"]["touched" if "touched" in d["Config"] else "change"] == 0
          and d["Lists"]["change"] == 0 and d["Lists"]["add"] == 0,
          "Lists and Config are identical in both, so neither is offered")

    # ---- 2. accepting is per sheet ----------------------------------------
    print("\naccepting one sheet, and only that sheet")
    got = pg.evaluate("""async (text) => {
        const incoming = buildModel(readPrapJson(text));
        const diff = importDiff(S.model.raw, incoming.raw);
        const n = importApply(diff, new Set(["Project"]));
        rebuild(true);
        return {n, projects: S.model.raw.Project.map(r => r.project_id).sort(),
                people: S.model.raw.Person.map(r => r.person_id).sort(),
                alphaEnd: ymd(S.model.raw.Project.find(r => r.project_id === 'PRJ-001').end_date),
                alphaMonths: S.model.raw.Project.find(r => r.project_id === 'PRJ-001').total_period_months,
                pending: S.pending.length};
    }""", REVISED.read_text(encoding="utf-8"))

    check(got["projects"] == ["PRJ-001", "PRJ-002", "PRJ-003", "PRJ-004"],
          "the new project arrives AND the hand-typed one is still there",
          " ".join(got["projects"]))
    check(got["people"] == ["PSN-001"],
          "the new person does NOT — Person was not ticked (S-N03)",
          " ".join(got["people"]))
    check(got["alphaEnd"] == "2027-09-30",
          "the changed column is taken", f"end_date now {got['alphaEnd']}")
    check(got["alphaMonths"] != 99,
          "the stale derived value is NOT taken — it is recomputed from the dates",
          f"total_period_months is {got['alphaMonths']}, not the file's 99")
    check(got["pending"] >= 2,
          "and all of it is PENDING, so Leave without change puts it back",
          f"{got['pending']} pending change(s)")

    # ---- 3. an identical file has nothing to say --------------------------
    same = pg.evaluate("""async (text) => {
        const incoming = buildModel(readPrapJson(text));
        return importDiffEmpty(importDiff(S.model.raw, incoming.raw));
    }""", PLAN.read_text(encoding="utf-8"))
    check(same is False,
          "after that import the plan and the ORIGINAL file now differ, as they should")

    identical = pg.evaluate("""async () => {
        const sheets = {};
        for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
        const incoming = buildModel(sheets);
        return importDiffEmpty(importDiff(S.model.raw, incoming.raw));
    }""")
    check(identical is True,
          "and a file identical to the plan reports nothing to decide")

    check(not errors, "no uncaught errors", "; ".join(errors[:2]))
    browser.close()


# ------------------------------------------------- 4. the flow, in the shell
print("\nthe Python shell — the whole flow, with the dialogs")
# Run from a COPY. Starting the packaged folder in place leaves a data/ directory
# inside dist/, which the next test to copy that folder then inherits - and a test that
# inherits another test's state is a test that passes for the wrong reason.
import shutil                                                        # noqa: E402
RUN = TMP / "PM_APP"
shutil.copytree(PKG, RUN, ignore=shutil.ignore_patterns("data"))
proc = subprocess.Popen([sys.executable, str(RUN / "PM_APP.py"), "--no-browser"],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
url = key = None
for _ in range(200):
    line = proc.stdout.readline()
    if not line:
        break
    if "http://127.0.0.1" in line and "?k=" in line:
        url, key = line.strip().split("/?k=")
        break
if not url:
    proc.kill()
    raise SystemExit("the application did not start")

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=CHROME)
        pg = browser.new_page(viewport={"width": 1500, "height": 1000})
        # A default timeout, so a dialog that never opens fails this test in twenty
        # seconds rather than waiting for ever - and a dialog handler, because
        # 'Leave without change' asks before discarding.
        pg.set_default_timeout(20000)
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda d: d.accept())
        pg.goto(f"{url}/?k={key}")
        pg.wait_for_timeout(1500)
        if pg.locator("[data-name]").count():
            pg.fill("[data-name]", "Test Person")
            pg.click("[data-ok]")
            pg.wait_for_timeout(500)

        # First import: nothing open, so it adopts with no questions asked.
        pg.evaluate("""async (p) => {
            const r = await window.__pm.call('file/openSource', {path: p});
            await window.__pm.adoptBytes(r.name, Uint8Array.from(atob(r.bytes),
                                                                 c => c.charCodeAt(0)));
        }""", str(PLAN))
        pg.wait_for_timeout(2000)
        check(pg.evaluate("S.model.raw.Project.length") == 3
              and pg.locator(".pm-back").count() == 0,
              "the first import into an empty plan asks nothing and just loads",
              f"{pg.evaluate('S.model.raw.Project.length')} projects, no dialog")

        # Second import: the plan holds data, so it must ASK before showing anything.
        # Deliberately NOT awaited. adoptBytes now opens a dialog and waits for an
        # answer, so returning its promise would have Playwright wait for a click this
        # test has not made yet, and the two would wait for each other for ever. The
        # braces make the arrow return undefined, which fires it and moves on.
        pg.evaluate("""(p) => { window.__pm.call('file/openSource', {path: p})
            .then(r => window.__pm.adoptBytes(r.name,
                  Uint8Array.from(atob(r.bytes), c => c.charCodeAt(0)))); }""", str(REVISED))
        pg.wait_for_timeout(2500)
        asked = pg.inner_text(".pm-box h3") if pg.locator(".pm-box").count() else ""
        check("already contains data" in asked,
              "the second import ASKS FIRST rather than showing a table (Q-N05)", asked)

        pg.click("[data-yes]")
        pg.wait_for_timeout(1200)
        title = pg.inner_text(".pm-box h3")
        check("Update from" in title, "then the difference report opens", title)

        sheets_shown = pg.eval_on_selector_all(".pm-diff > summary b",
                                               "es => es.map(e => e.textContent)")
        check("Project" in sheets_shown and "Person" in sheets_shown,
              "with a block per sheet that has something to decide",
              ", ".join(sheets_shown))

        rows = pg.eval_on_selector_all(".pm-diff-list.keep li .n",
                                       "es => es.map(e => e.textContent)")
        check(any("Local, typed by hand" in r for r in rows),
              "and the hand-typed project listed as kept, not as removed",
              "; ".join(rows[:2]))

        # Untick Person, take Project only.
        pg.click(".pm-diff input[data-sheet-tick='Person']")
        pg.wait_for_timeout(400)
        pg.click("[data-ok]")
        pg.wait_for_timeout(2000)

        after = pg.evaluate("""() => ({
            projects: S.model.raw.Project.map(r => r.project_id).sort(),
            people: S.model.raw.Person.map(r => r.person_id).sort(),
            pending: S.pending.length})""")
        check(after["projects"] == ["PRJ-001", "PRJ-002", "PRJ-003", "PRJ-004"],
              "Project was taken — added, changed, and nothing removed",
              " ".join(after["projects"]))
        check(after["people"] == ["PSN-001"],
              "Person was not, because it was unticked", " ".join(after["people"]))
        check(after["pending"] > 0, "and the whole import is unsaved until Save",
              f"{after['pending']} pending")

        # Leave without change must put every bit of it back.
        pg.click("#discardBtn")
        pg.wait_for_timeout(1500)
        back = pg.evaluate("S.model.raw.Project.map(r => r.project_id).sort()")
        check(back == ["PRJ-001", "PRJ-002", "PRJ-003"],
              "LEAVE WITHOUT CHANGE puts the plan back exactly as it was",
              " ".join(back))

        check(not errors, "no uncaught errors in the shell", "; ".join(errors[:2]))
        browser.close()
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
