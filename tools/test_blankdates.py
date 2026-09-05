"""An assignment with no dates means the whole project.

Most people are on a project for the whole of it. Asking for two dates that simply
repeat the project's is asking somebody to copy the same pair onto every row and then
keep them in step afterwards - so both dates are optional, and a blank one means the
project's own (REQ-CAL-15).

The END date already worked this way. The START did not: a blank one made the
assignment contribute NOTHING - the row sat on screen, the person looked unassigned,
and no finding said why. That is the behaviour this changes, and the reason the first
check below is the one that matters:

    an assignment with NO dates produces exactly the same figures as the same
    assignment with the project's own dates typed into it

Everything else follows from that. The one interaction worth its own check is the
role share: a blank-dated person has to count as a SHARER in the months they cover,
which they only do if the sharing pre-pass and the calculation agree about which
months those are. They are computed by one function for exactly that reason, and this
is what would catch it if that ever stopped being true.

    python tools/test_blankdates.py
"""

import json
import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_blankdates_"))

sys.path.insert(0, str(ROOT / "tools"))
import build_source_workbook as B                                    # noqa: E402
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# ---------------------------------------------------------------- the fixture
# An 'Others' project running the whole of 2027, one period at weight 1.00 and one
# role at factor 1.00, so a person at weight 1.00 costs exactly 1.00 FTE in a full
# month and every expected figure below can be written down rather than derived.
P_START, P_END = "2027-01-01", "2027-12-31"


def doc(assignments, people=("PSN-001", "PSN-002")):
    return {"prap_format": "prap-source-data", "format_version": 1, "sheets": {
        "Project": [{"project_id": "PRJ-001", "project_name": "Internal work",
                     "project_type": "Others", "start_date": P_START,
                     "end_date": P_END, "status": "Active"}],
        "Milestone": [],
        "ProjectPeriod": [{"project_id": "PRJ-001", "period_name": "Planning",
                           "period_seq": 1, "period_start": P_START,
                           "period_end": P_END, "weight": 1.00}],
        "PeriodFTEStandard": [],
        "RoleFactor": [{"project_type": "Others", "clinical_phase": None,
                        "work_scope_type": None, "period_name": "Planning",
                        "role_name": "Main staff", "role_factor": 1.00}],
        "Person": [{"person_id": s, "person_name": f"Person {s[-1]}",
                    "department": "Ops", "primary_role": "Main staff",
                    "capacity_fte": 1.00} for s in people],
        "Assignment": assignments,
        "PersonPeriodWeight": [],
        "Lists": [{"list_name": n, "value": v, "note_1": None}
                  for n, vs in B.LISTS for v in vs],
        "Config": [{"parameter": k, "value": v, "note": n} for k, v, n in B.CONFIG]}}


def asg(aid, pid, start, end, weight=1.00):
    return {"assignment_id": aid, "person_id": pid, "project_id": "PRJ-001",
            "role_name": "Main staff", "assign_start_date": start,
            "assign_end_date": end, "person_weight": weight}


def write(name, d):
    p = TMP / name
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return p


# KIM has no dates at all. The requirement, in one file.
BLANK = write("blank.prap.json", doc([asg("ASG-001", "PSN-001", None, None)]))
# The same assignment with the project's dates typed in. Must produce the same figures.
TYPED = write("typed.prap.json", doc([asg("ASG-001", "PSN-001", P_START, P_END)]))
# One blank date each way.
NO_START = write("nostart.prap.json", doc([asg("ASG-001", "PSN-001", None, "2027-06-30")]))
NO_END = write("noend.prap.json", doc([asg("ASG-001", "PSN-001", "2027-07-01", None)]))
# Two people on the same role, one dated and one not: the blank one still has to be
# counted as a sharer, or the dated one is charged the whole factor for the year.
SHARED = write("shared.prap.json", doc([
    asg("ASG-001", "PSN-001", None, None),
    asg("ASG-002", "PSN-002", P_START, P_END)]))

JAN, JUN, JUL, DEC = (2027 * 12 + m for m in (0, 5, 6, 11))


def months(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_timeout(1600)
    return pg.evaluate("""() => {
        const o = {}; for (const [k, v] of S.calc.persMonth) o[k] = v;
        return {pm: o, findings: S.model.findings
            .filter(f => f.sev === 'error' || f.sev === 'warning')
            .map(f => f.rule + ': ' + f.msg)};}""")


def ref(path):
    """The same plan through tools/prap_io.py, which implements the rule separately."""
    M = prap_io.Model(prap_io.read_json(path))
    return prap_io.calculate(M)["pers_month"]


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 900})
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — an assignment with no dates is on for the whole project")

    blank = months(pg, BLANK)
    typed = months(pg, TYPED)

    check(len(blank["pm"]) == 12,
          "twelve person-months, one for every month of the project",
          f"{len(blank['pm'])} months")
    check(abs(blank["pm"][f"PSN-001|{JAN}"] - 1.00) < 1e-9
          and abs(blank["pm"][f"PSN-001|{DEC}"] - 1.00) < 1e-9,
          "including January and December, at the full 1.00 FTE",
          f"Jan {blank['pm'][f'PSN-001|{JAN}']:.4f}, "
          f"Dec {blank['pm'][f'PSN-001|{DEC}']:.4f}")
    check(set(blank["pm"]) == set(typed["pm"])
          and all(abs(blank["pm"][k] - typed["pm"][k]) < 1e-9 for k in typed["pm"]),
          "AND IT IS IDENTICAL to the same assignment with the project's dates typed in "
          "— which is the whole requirement",
          f"{len(typed['pm'])} months compared, no difference")
    check(not blank["findings"],
          "a row with no dates raises no error and no warning: it is a normal row",
          "; ".join(blank["findings"][:2]))

    ns = months(pg, NO_START)
    check(len(ns["pm"]) == 6 and abs(ns["pm"][f"PSN-001|{JAN}"] - 1.00) < 1e-9
          and f"PSN-001|{JUL}" not in ns["pm"],
          "a blank START alone runs from the project's start to the date given",
          f"{len(ns['pm'])} months, Jan to Jun")

    ne = months(pg, NO_END)
    check(len(ne["pm"]) == 6 and abs(ne["pm"][f"PSN-001|{DEC}"] - 1.00) < 1e-9
          and f"PSN-001|{JUN}" not in ne["pm"],
          "and a blank END alone runs from the date given to the project's end",
          f"{len(ne['pm'])} months, Jul to Dec")

    sh = months(pg, SHARED)
    check(abs(sh["pm"][f"PSN-001|{JAN}"] - 0.50) < 1e-9
          and abs(sh["pm"][f"PSN-002|{JAN}"] - 0.50) < 1e-9,
          "a person with no dates COUNTS AS A SHARER — the two split the role factor "
          "rather than one of them carrying it whole",
          f"{sh['pm'][f'PSN-001|{JAN}']:.4f} and {sh['pm'][f'PSN-002|{JAN}']:.4f}")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\ntools/prap_io.py — the same plans, worked out separately")
for name, path, expect in (("no dates at all", BLANK, 1.00),
                           ("the project's dates typed in", TYPED, 1.00),
                           ("blank start only", NO_START, 1.00)):
    got = ref(path).get(("PSN-001", JAN))
    check(got is not None and abs(got - expect) < 1e-9,
          f"{name}: PSN-001 carries {expect:.2f} FTE in Jan 2027", f"got {got}")

got = ref(SHARED).get(("PSN-001", JAN))
check(got is not None and abs(got - 0.50) < 1e-9,
      "and the undated sharer is counted: 0.50 FTE each in Jan 2027", f"got {got}")

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
