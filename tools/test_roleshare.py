"""The rule that a shared role is a shared cost.

Two data managers on one trial do not cost the trial two data managers. The role
factor is what the ROLE costs the project in a period, so where several people hold
the same role on the same project in the same month, they divide it.

That sentence is easy to agree with and easy to implement three subtly different
ways, so this test pins the exact one - on a plan small enough that every figure can
be worked out by hand before the application is asked:

  * one person holding a role gets the whole factor
  * two people holding it get half each, and the PROJECT's total is unchanged - which
    is the property that matters, and the one a per-assignment divisor would break
  * the count is per MONTH, so when one of two sharers leaves, the other returns to a
    full share the following month with nobody editing anything
  * the count is of PEOPLE, not rows
  * a person's own person_weight still applies on top, untouched
  * split_shared_role_fte = 0 restores the old arithmetic exactly

Checked in the browser and in tools/prap_io.py, which arrived at the rule separately.

    python tools/test_roleshare.py
"""

import json
import pathlib
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_share_"))

sys.path.insert(0, str(ROOT / "tools"))
import build_source_workbook as B                                    # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# ---------------------------------------------------------------- the fixture
# One 'Others' project, because they take hand-entered periods and weights - so
# every number below is chosen here rather than looked up, and the expected answer
# can be written down.
#
#   period weight  1.00 for the whole of 2027 (one period, 'Planning')
#   role factor    2.00 for 'Main staff'      (chosen, not defaulted)
#   person weight  1.00 for everybody
#
# So one person alone on the role costs 1.00 x 2.00 x 1.00 = 2.00 FTE in a full month.
PERIOD_W = 1.00
ROLE_F = 2.00
# REQ-CAL-19: the month's DEMAND in FTE. Before schema 10 the standards sheet was left
# empty here and the role factor supplied the magnitude; now the factor decides only how
# the demand is SPLIT, so a fixture without a standard would be testing the 1.00
# fallback rather than the rule.
STANDARD = 4.00


def sheets(assignments, split=1):
    lists = [[n, v, None] for n, vs in B.LISTS for v in vs]
    config = [[k, v, ""] for k, v, _ in B.CONFIG]
    config = [[k, (split if k == "split_shared_role_fte" else v), n] for k, v, n in config]
    return {
        "Project": [{"project_id": "PRJ-001", "project_name": "Internal work",
                     "project_type": "Others", "start_date": "2027-01-01",
                     "end_date": "2027-12-31", "status": "Active"}],
        "Milestone": [],
        "ProjectPeriod": [{"project_id": "PRJ-001", "period_name": "Planning",
                           "period_seq": 1, "period_start": "2027-01-01",
                           "period_end": "2027-12-31", "weight": PERIOD_W}],
        "PeriodWeightStandard": [{"project_type": "Others", "clinical_phase": None,
                                  "work_scope_type": None, "period_name": "Planning",
                                  "standard_fte": STANDARD}],
        "RoleFactor": [{"project_type": "Others", "clinical_phase": None,
                        "work_scope_type": None, "period_name": "Planning",
                        "role_name": "Main staff", "role_factor": ROLE_F}],
        "Person": [{"person_id": p, "person_name": f"Person {p[-1]}",
                    "department": "Ops", "primary_role": "Main staff",
                    "capacity_fte": 1.00} for p in ("PSN-001", "PSN-002", "PSN-003")],
        "Assignment": assignments,
        "PersonPeriodWeight": [],
        "Lists": [{"list_name": a, "value": b, "note_1": c} for a, b, c in lists],
        "Config": [{"parameter": a, "value": b, "note": c} for a, b, c in config],
    }


def asg(aid, pid, role, start, end, weight=1.00):
    return {"assignment_id": aid, "person_id": pid, "project_id": "PRJ-001",
            "role_name": role, "assign_start_date": start, "assign_end_date": end,
            "person_weight": weight}


def write(name, doc):
    p = TMP / name
    p.write_text(json.dumps({"prap_format": "prap-source-data", "format_version": 1,
                             "sheets": doc}, indent=1), encoding="utf-8")
    return p


ALONE = write("alone.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31")]))

# The same work, staffed by two people for the whole year.
PAIR = write("pair.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31"),
    asg("ASG-002", "PSN-002", "Main staff", "2027-01-01", "2027-12-31")]))

# Two for the first half, one for the second: the divisor has to move in July.
LEAVER = write("leaver.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31"),
    asg("ASG-002", "PSN-002", "Main staff", "2027-01-01", "2027-06-30")]))

# One person, two rows - a role held once, recorded twice. Must not halve.
TWICE = write("twice.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-06-30"),
    asg("ASG-002", "PSN-001", "Main staff", "2027-07-01", "2027-12-31")]))

# Two people on DIFFERENT roles: nothing is shared, so nothing is divided.
ROLES = write("roles.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31"),
    asg("ASG-002", "PSN-002", "Project lead", "2027-01-01", "2027-12-31")]))

# Different person weights, same role: the division is by HEADCOUNT, and each
# person's own weight then applies to their half.
WEIGHTED = write("weighted.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31", 1.00),
    asg("ASG-002", "PSN-002", "Main staff", "2027-01-01", "2027-12-31", 0.50)]))

# The same pair, with the split turned off - the arithmetic of every version before
# this one, kept reachable so an old figure can be reproduced and compared.
OFF = write("off.prap.json", sheets([
    asg("ASG-001", "PSN-001", "Main staff", "2027-01-01", "2027-12-31"),
    asg("ASG-002", "PSN-002", "Main staff", "2027-01-01", "2027-12-31")], split=0))

MAR = 2027 * 12 + 2            # a full month, nothing starting or ending in it
SEP = 2027 * 12 + 8


def load(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_timeout(1800)
    return pg.evaluate("""() => {
        const o = {pers: {}, proj: {}};
        for (const [k, v] of S.calc.persMonth) o.pers[k] = v;
        for (const [k, v] of S.calc.projMonth) o.proj[k] = v;
        o.findings = S.model.findings.filter(f => f.sev !== 'information').length;
        return o;}""")


def ref(path):
    """The same plan through tools/prap_io.py, which implements the rule separately.

    Imported rather than run through the command line, so the comparison is against
    the model itself rather than against a formatted report.
    """
    import prap_io
    M = prap_io.Model(prap_io.read_json(path))
    return prap_io.calculate(M)["pers_month"]


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    print("app/PRAP.html — a shared role is a shared cost")

    a = load(pg, ALONE)
    solo = a["pers"][f"PSN-001|{MAR}"]
    check(abs(solo - STANDARD * PERIOD_W) < 1e-9,
          "ONE PERSON HOLDING THE ONLY STAFFED ROLE CARRIES THE WHOLE MONTH — the demand "
          "is the standard, and their share of it is all of it (REQ-CAL-19). The role "
          "factor sets no magnitude here; with one role staffed there is nothing to "
          "divide, so 2.00 and 0.20 would both give this same figure",
          f"{solo:.4f} FTE in Mar 2027, expected {STANDARD * PERIOD_W:.4f}")

    p = load(pg, PAIR)
    one, two = p["pers"][f"PSN-001|{MAR}"], p["pers"][f"PSN-002|{MAR}"]
    check(abs(one - solo / 2) < 1e-9 and abs(two - solo / 2) < 1e-9,
          "two people holding it carry half each",
          f"{one:.4f} and {two:.4f}, expected {solo / 2:.4f} each")
    check(abs(p["proj"][f"PRJ-001|{MAR}"] - a["proj"][f"PRJ-001|{MAR}"]) < 1e-9,
          "AND THE PROJECT COSTS THE SAME — the work did not double because two "
          "people did it",
          f"{p['proj'][f'PRJ-001|{MAR}']:.4f} vs {a['proj'][f'PRJ-001|{MAR}']:.4f}")

    l = load(pg, LEAVER)
    check(abs(l["pers"][f"PSN-001|{MAR}"] - solo / 2) < 1e-9,
          "while two share it, each carries half",
          f"{l['pers'][f'PSN-001|{MAR}']:.4f} in March")
    check(abs(l["pers"][f"PSN-001|{SEP}"] - solo) < 1e-9,
          "and when one leaves, the other is back to a full share the next month — "
          "counted per month, so nobody has to edit anything",
          f"{l['pers'][f'PSN-001|{SEP}']:.4f} in September, expected {solo:.4f}")

    t = load(pg, TWICE)
    check(abs(t["pers"][f"PSN-001|{MAR}"] - solo) < 1e-9
          and abs(t["pers"][f"PSN-001|{SEP}"] - solo) < 1e-9,
          "one person recorded on two rows is still one person",
          f"{t['pers'][f'PSN-001|{MAR}']:.4f} then {t['pers'][f'PSN-001|{SEP}']:.4f}")

    # Two DIFFERENT roles do not share a factor - but since schema 10 they do divide the
    # project's demand between them, in proportion to their factors. 'Project lead' has no
    # RoleFactor row on this fixture, so it falls back to 1.00 against Main staff's 2.00:
    # two thirds and one third of a month that is still exactly the standard.
    r = load(pg, ROLES)
    lead, main_ = r["pers"][f"PSN-002|{MAR}"], r["pers"][f"PSN-001|{MAR}"]
    check(abs(main_ - solo * 2 / 3) < 1e-9 and abs(lead - solo / 3) < 1e-9,
          "TWO PEOPLE ON DIFFERENT ROLES SHARE NO FACTOR, but they do divide the month "
          "between them in proportion to their factors — 2.00 against 1.00",
          f"{main_:.4f} and {lead:.4f} of a {solo:.4f} month")
    check(abs(r["proj"][f"PRJ-001|{MAR}"] - solo) < 1e-9,
          "and the project month is unchanged by how many roles are on it",
          f"{r['proj'][f'PRJ-001|{MAR}']:.4f} vs {solo:.4f} with one role")

    w = load(pg, WEIGHTED)
    check(abs(w["pers"][f"PSN-001|{MAR}"] - solo / 2) < 1e-9
          and abs(w["pers"][f"PSN-002|{MAR}"] - solo / 2 * 0.50) < 1e-9,
          "the division is by headcount; each person's own weight applies to their half",
          f"{w['pers'][f'PSN-001|{MAR}']:.4f} at weight 1.00, "
          f"{w['pers'][f'PSN-002|{MAR}']:.4f} at weight 0.50")

    o = load(pg, OFF)
    check(abs(o["pers"][f"PSN-001|{MAR}"] - solo) < 1e-9
          and abs(o["proj"][f"PRJ-001|{MAR}"] - solo * 2) < 1e-9,
          "split_shared_role_fte = 0 restores the arithmetic of every earlier version",
          f"{o['pers'][f'PSN-001|{MAR}']:.4f} each, {o['proj'][f'PRJ-001|{MAR}']:.4f} "
          f"for the project")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

# ---- and the same conclusions from the independent implementation ------------
print("\ntools/prap_io.py — the same plans, worked out separately")
for name, path, expect in (("one person alone", ALONE, STANDARD * PERIOD_W),
                           ("two people sharing", PAIR, STANDARD * PERIOD_W / 2),
                           ("the split turned off", OFF, STANDARD * PERIOD_W)):
    got = ref(path).get(("PSN-001", MAR))
    check(got is not None and abs(got - expect) < 1e-9,
          f"{name}: PSN-001 carries {expect:.4f} FTE in Mar 2027", f"got {got}")

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
