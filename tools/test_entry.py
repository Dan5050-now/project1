"""The plan can be entered before the assumptions catch up - and the run is the periods.

Two behaviours that are easy to state and were both wrong.

R-19 - A MISSING ASSUMPTION IS NOT A BAD ROW. RoleFactor is a standing document,
maintained separately from any one plan and often by somebody else. If a role has no
factor yet, the figures for that role are wrong - and saying so is right. Refusing to
record who is on the project until somebody else's document catches up is not: the
person really is on the project, and the application's job is to hold that fact and
then tell you what it cannot cost. So V-03 and V-23 report at full severity and never
refuse an edit, while everything that IS wrong with the row in front of you still does.

  * V-03 is the coarse half - this role has no factor for this project TYPE at all.
  * V-23 is the precise half, and it is now raised BY the calculation: keyed on the
    exact composition the lookup used (type, phase, work scope, period, role) and
    counted only where a person-month actually had to guess. Asked the old way, off
    the sheets, it demanded rows for periods no assignment ever reached.

REQ-CAL-17 - THE PERIODS ARE THE PROJECT. Milestones are reference dates; several of
them mark moments inside the run rather than its edges. Taking the project's window
from them stretched it over months belonging to no period, which are costed at weight
1.00 - so a project drew resource in months its own plan did not cover.

    python tools/test_entry.py
"""

import json
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_entry_"))

sys.path.insert(0, str(ROOT / "tools"))
import build_source_workbook as B                                    # noqa: E402
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


LEAD, NEW_ROLE = "Project lead", "Regulatory affairs lead"
# The project runs all of 2027. Its PERIODS cover Feb to Nov - somebody entered them
# that way, or derived them and then trimmed. Its MILESTONES run from January to
# December, which is the old window: two months at each end in no period at all.
P_START, P_END = "2027-01-01", "2027-12-31"
PER_START, PER_END = "2027-02-01", "2027-11-30"


def doc(role=LEAD, with_periods=True):
    return {"prap_format": "prap-source-data", "format_version": 1, "sheets": {
        "Project": [{"project_id": "PRJ-001", "project_name": "Internal work",
                     "project_type": "Others", "start_date": P_START,
                     "end_date": P_END, "status": "Active"}],
        "Milestone": [{"project_id": "PRJ-001", "milestone_name": "Kick-off",
                       "milestone_date": P_START, "milestone_seq": 1},
                      {"project_id": "PRJ-001", "milestone_name": "Wrap-up",
                       "milestone_date": P_END, "milestone_seq": 2}],
        "ProjectPeriod": ([{"project_id": "PRJ-001", "period_name": "Planning",
                            "period_seq": 1, "period_start": PER_START,
                            "period_end": PER_END, "weight": 1.00}]
                          if with_periods else []),
        "PeriodWeightStandard": [],
        "RoleFactor": [{"project_type": "Others", "clinical_phase": None,
                        "work_scope_type": None, "period_name": "Planning",
                        "role_name": LEAD, "role_factor": 1.00, "absorbed_by": None}],
        "Person": [{"person_id": "PSN-001", "person_name": "Person One",
                    "department": "Ops", "primary_role": LEAD, "capacity_fte": 1.00}],
        "Assignment": [{"assignment_id": "ASG-001", "person_id": "PSN-001",
                        "project_id": "PRJ-001", "role_name": role,
                        "assign_start_date": None, "assign_end_date": None,
                        "person_weight": 1.00}],
        "PersonPeriodWeight": [],
        "Lists": [{"list_name": n, "value": v, "note_1": None}
                  for n, vs in B.LISTS for v in vs],
        "Config": [{"parameter": k, "value": v, "note": n} for k, v, n in B.CONFIG]}}


def write(name, d):
    p = TMP / name
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return p


GOOD = write("good.prap.json", doc())
# The same plan with a role the assumptions have never heard of.
UNKNOWN = write("unknown.prap.json", doc(role=NEW_ROLE))
# No periods at all: the window falls back to the project's own dates, and V-12 says so.
NOPER = write("noper.prap.json", doc(with_periods=False))

JAN, FEB, NOV, DEC = (2027 * 12 + m for m in (0, 1, 10, 11))


def load(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_timeout(1600)


def read(pg):
    return pg.evaluate("""() => {
        const o = {}; for (const [k, v] of S.calc.persMonth) o[k] = v;
        return {pm: o,
                rules: S.model.findings.map(f => f.sev + '|' + f.rule),
                blocking: S.model.findings.filter(blocking).map(f => f.rule),
                v23: S.model.findings.filter(f => f.rule === 'V-23').map(f => f.msg),
                role: S.model.raw.Assignment[0].role_name};}""")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — a missing assumption reports, and never refuses the row")

    # ---- 1. typing an unknown role into an assignment, through the real UI ----------
    load(pg, GOOD)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    cell = pg.locator("td[data-sheet='Assignment'][data-col='role_name']").first
    cell.click()
    pg.wait_for_timeout(350)
    pg.keyboard.press("Control+A")
    pg.keyboard.type(NEW_ROLE)
    pg.keyboard.press("Escape")          # dismiss the type-ahead, keep what was typed
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)

    banner = pg.inner_text("#banner")
    st = read(pg)
    check(st["role"] == NEW_ROLE and "Edit rejected" not in banner,
          "A ROLE THE ASSUMPTIONS HAVE NEVER HEARD OF CAN STILL BE TYPED IN",
          f"role is now '{st['role']}'"
          + (f"; banner says “{banner.strip()[:60]}”" if "reject" in banner.lower() else ""))

    check("V-03" in st["rules"] or "error|V-03" in st["rules"],
          "and it is reported, not swallowed — V-03 names it",
          "; ".join(r for r in st["rules"] if "V-03" in r) or "(nothing)")

    check("V-03" not in st["blocking"] and "V-23" not in st["blocking"],
          "neither half of the role/factor check can refuse an edit",
          f"blocking rules present: {sorted(set(st['blocking'])) or 'none'}")

    # Save must go through - the row is incomplete in its assumptions, not invalid - but
    # since R-25 it ASKS first, naming what will be left unresolved. Refusing and asking
    # are different answers, and this is the asking one.
    pg.click("#saveBtn")
    pg.wait_for_timeout(900)
    asked = pg.evaluate("document.getElementById('confirm').open")
    listed = pg.locator("#cfBody tbody tr").count()
    check(asked and listed >= 1,
          "and SAVE ASKS rather than refusing — naming what will be left unresolved",
          f"dialog open={asked}, {listed} item(s) listed")
    pg.click("#cfYes")
    pg.wait_for_timeout(900)
    saved = pg.inner_text("#banner")
    st = read(pg)
    check(st["role"] == NEW_ROLE and "Saved" in saved,
          "and 'Save anyway' keeps it, rather than refusing the whole batch",
          saved.strip()[:80])

    # ---- 2. V-23 is keyed on the composition, and counts what was calculated --------
    load(pg, UNKNOWN)
    st = read(pg)
    said = " | ".join(st["v23"])
    parts = ["Others", "Planning", NEW_ROLE, "any scope"]
    check(len(st["v23"]) == 1 and all(p in said for p in parts),
          "V-23 names the WHOLE composition it looked up — type / phase / scope / "
          "period / role",
          said[:150] or "(nothing reported)")
    check("10 person-month" in said,
          "and counts the person-months that were actually calculated at 1.00 — the ten "
          "months the periods cover, not the twelve the milestones span",
          said[said.find("person-month") - 4:said.find("person-month") + 14]
          if "person-month" in said else said[:80])

    # ---- 3. the window is the periods, not the milestones --------------------------
    check(abs(st["pm"].get(f"PSN-001|{FEB}", 0) - 1.0) < 1e-9
          and st["pm"].get(f"PSN-001|{JAN}") is None
          and st["pm"].get(f"PSN-001|{DEC}") is None,
          "THE PROJECT RUNS OVER ITS PERIODS: February to November draw resource, "
          "January and December do not",
          f"Jan {st['pm'].get(f'PSN-001|{JAN}')}, Feb {st['pm'].get(f'PSN-001|{FEB}')}, "
          f"Nov {st['pm'].get(f'PSN-001|{NOV}')}, Dec {st['pm'].get(f'PSN-001|{DEC}')}")

    # A project with no periods has nothing to take a window from, so its own dates
    # stand - otherwise a plan half way through being typed would calculate as nothing.
    load(pg, NOPER)
    st = read(pg)
    check(st["pm"].get(f"PSN-001|{JAN}") is not None
          and st["pm"].get(f"PSN-001|{DEC}") is not None,
          "with NO periods the project keeps its own dates — a plan being typed still "
          "shows a figure, and V-12 says why",
          f"Jan {st['pm'].get(f'PSN-001|{JAN}')}, Dec {st['pm'].get(f'PSN-001|{DEC}')}, "
          f"V-12 present={any('V-12' in r for r in st['rules'])}")

    # ---- 4. the guard rail is still there ------------------------------------------
    load(pg, GOOD)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    def put(col, text):
        c = pg.locator(f"td[data-sheet='Assignment'][data-col='{col}']").first
        c.click()
        pg.wait_for_timeout(350)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(text)
        pg.keyboard.press("Enter")     # a date column has no value list to dismiss first
        pg.wait_for_timeout(800)

    put("assign_start_date", "2027-06-01")
    started = pg.evaluate("S.model.raw.Assignment[0].assign_start_date")
    put("assign_end_date", "2027-03-01")          # before the start: V-05, and wrong HERE
    banner = pg.inner_text("#banner")
    ended = pg.evaluate("S.model.raw.Assignment[0].assign_end_date")
    check(started and "Edit rejected" in banner and not ended,
          "AN ASSIGNMENT THAT ENDS BEFORE IT STARTS IS STILL REFUSED — what changed is "
          "WHICH findings refuse, not that any do",
          banner.strip().split("\n")[0][:90])

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\ntools/prap_io.py — the same plans, worked out separately")
for name, path, expect in (("the periods, not the milestones", UNKNOWN,
                            {FEB: 1.0, JAN: None, DEC: None}),
                           ("no periods: the project's own dates", NOPER,
                            {JAN: 1.0, DEC: 1.0})):
    M = prap_io.Model(prap_io.read_json(path))
    C = prap_io.calculate(M)
    got = {k: C["pers_month"].get(("PSN-001", k)) for k in expect}
    ok = all((v is None and got[k] is None) or (v is not None and got[k] is not None
             and abs(got[k] - v) < 1e-9) for k, v in expect.items())
    check(ok, f"{name}", f"got {got}, expected {expect}")

M = prap_io.Model(prap_io.read_json(UNKNOWN))
v23 = [f for f in M.findings if f["rule"] == "V-23"]
check(len(v23) == 1 and "10 person-month" in v23[0]["msg"] and NEW_ROLE in v23[0]["msg"],
      "and prap_io raises the same single V-23, over the same ten person-months",
      (v23[0]["msg"][:110] if v23 else "(nothing reported)"))

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
