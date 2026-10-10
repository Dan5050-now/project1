"""When nobody holds a role, the work does not disappear.

role_factor answers "what does this ROLE cost the project in this period". If nobody
is holding it, that cost is still there - it is done by whoever is left, who is then
under more pressure than the factor for their own role alone describes. Costed the old
way, a trial staffed without a Clinical Data Associator looked cheaper than one staffed
with it, purely because a post was never filled.

    effective(role) = factor(role)
                    + SUM factor(x) for every x with absorbed_by = role
                                    that NOBODY holds in this month

The fixture is one 'Others' project across 2027, one period at weight 1.00, and:

    Project lead   factor 1.00
    Other staff    factor 0.60, absorbed_by = Project lead

so a project lead ALONE carries 1.60, and one with an 'Other staff' beside them
carries 1.00. Every expected figure below is that arithmetic.

Four things that could each be got wrong:

  * the mapping is DATA. Clear absorbed_by and nothing is absorbed - which is what
    proves the two role names are not hidden in the code (REQ-CAL-06).
  * it is PER MONTH. Somebody arriving in July ends the cover in July, with nobody
    editing anything.
  * ONE HOP. An absent role whose absorber is also absent is not passed further along,
    and V-29 says so rather than the figure silently absorbing twice.
  * absorb_unstaffed_role_factor = 0 restores the previous arithmetic exactly.

    python tools/test_absorb.py
"""

import json
import pathlib
import math
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_absorb_"))

sys.path.insert(0, str(ROOT / "tools"))
import build_source_workbook as B                                    # noqa: E402
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


LEAD, OTHER, MAIN = "Project lead", "Other staff", "Main staff"
ANALYST = "Data Analyst"          # a fourth role, only the chain case needs it
F_ANALYST = 0.57
F_LEAD, F_OTHER, F_MAIN = 1.00, 0.60, 0.80
# REQ-CAL-19: the month's DEMAND. 6.00 divides cleanly by the factor sums below.
STANDARD = 6.00
# Every fixture staffs Main staff as well as the lead. Since schema 10 the demand is
# divided between the roles STAFFED, so an unstaffed role's work is redistributed
# whether or not anything covers for it - and with only ONE role staffed it would all
# land on that role either way, making absorption invisible. What absorbed_by decides
# now is WHO picks the work up, and showing that needs a second staffed role to not
# pick it up. MAIN is that role: it never covers for anything.
P_START, P_END = "2027-01-01", "2027-12-31"


def factors(absorbed=True, main_absorbed_by=None, chain=False):
    """The 'Others' roles, with Other staff covered by Project lead.

    `chain` adds a fourth role covered by Other staff - who is themselves absent. That is
    the one-hop case, and it needs a fourth role to be observable at all since schema 10:
    the demand is divided between the roles STAFFED, so with a single staffed role every
    absent factor lands on it whether the mapping says so or not.
    """
    rows = [(LEAD, F_LEAD, None),
            (OTHER, F_OTHER, LEAD if absorbed else None),
            (MAIN, F_MAIN, main_absorbed_by)]
    if chain:
        rows.append((ANALYST, F_ANALYST, OTHER))
    out = []
    for role, f, by in rows:
        out.append({"project_type": "Others", "clinical_phase": None,
                    "work_scope_type": None, "period_name": "Planning",
                    "role_name": role, "role_factor": f, "absorbed_by": by})
    return out


def doc(assignments, rf=None, absorb=1):
    config = [{"parameter": k,
               "value": (absorb if k == "absorb_unstaffed_role_factor" else v),
               "note": n} for k, v, n in B.CONFIG]
    return {"prap_format": "prap-source-data", "format_version": 1, "sheets": {
        "Project": [{"project_id": "PRJ-001", "project_name": "Internal work",
                     "project_type": "Others", "start_date": P_START,
                     "end_date": P_END, "status": "Active"}],
        "Milestone": [],
        "ProjectPeriod": [{"project_id": "PRJ-001", "period_name": "Planning",
                           "period_seq": 1, "period_start": P_START,
                           "period_end": P_END, "weight": 1.00}],
        "PeriodFTEStandard": [{"project_type": "Others", "clinical_phase": None,
                                  "work_scope_type": None, "period_name": "Planning",
                                  "standard_fte": STANDARD}],
        "RoleFactor": rf if rf is not None else factors(),
        "Person": [{"person_id": s, "person_name": f"Person {s[-1]}",
                    "department": "Ops", "primary_role": MAIN, "capacity_fte": 1.00}
                   for s in ("PSN-001", "PSN-002", "PSN-003")],
        "Assignment": assignments,
        "PersonPeriodWeight": [],
        "Lists": [{"list_name": n, "value": v, "note_1": None}
                  for n, vs in B.LISTS for v in vs],
        "Config": config}}


def asg(aid, pid, role, start=None, end=None, weight=1.00):
    return {"assignment_id": aid, "person_id": pid, "project_id": "PRJ-001",
            "role_name": role, "assign_start_date": start, "assign_end_date": end,
            "person_weight": weight}


def write(name, d):
    p = TMP / name
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")
    return p


# The lead alone: nobody holds 'Other staff', so its 0.60 lands on them.
MAINER = asg("ASG-003", "PSN-003", MAIN)
ALONE = write("alone.prap.json", doc([asg("ASG-001", "PSN-001", LEAD), MAINER]))
# Both roles held: nothing to absorb.
BOTH = write("both.prap.json", doc([asg("ASG-001", "PSN-001", LEAD),
                                    asg("ASG-002", "PSN-002", OTHER), MAINER]))
# The same as ALONE, with the mapping cleared: the rule is data, so nothing happens.
NOMAP = write("nomap.prap.json", doc([asg("ASG-001", "PSN-001", LEAD), MAINER],
                                     rf=factors(absorbed=False)))
# 'Other staff' arrives in July: the cover must end that month, by itself.
ARRIVES = write("arrives.prap.json", doc([
    asg("ASG-001", "PSN-001", LEAD),
    asg("ASG-002", "PSN-002", OTHER, "2027-07-01", P_END), MAINER]))
# Two leads and no Other staff: the absorbed factor is shared like any other.
SHARED = write("shared.prap.json", doc([asg("ASG-001", "PSN-001", LEAD),
                                        asg("ASG-002", "PSN-002", LEAD), MAINER]))
# ONE HOP: Main staff is covered by Other staff, who is also absent. Main's factor
# must NOT reach the lead, and V-29 must say the work is uncounted.
CHAIN = write("chain.prap.json", doc([asg("ASG-001", "PSN-001", LEAD),
                                      asg("ASG-004", "PSN-002", MAIN)],
                                     rf=factors(chain=True)))
# The switch off.
OFF = write("off.prap.json", doc([asg("ASG-001", "PSN-001", LEAD), MAINER], absorb=0))

JAN, JUN, JUL = (2027 * 12 + m for m in (0, 5, 6))


def load(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_timeout(1600)
    return pg.evaluate("""() => {
        const o = {}; for (const [k, v] of S.calc.persMonth) o[k] = v;
        return {pm: o, rules: S.model.findings.map(f => f.sev + '|' + f.rule),
                msgs: S.model.findings.filter(f => f.rule === 'V-29').map(f => f.msg)};}""")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 900})
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — an unstaffed role's work lands on whoever covers for it")

    # Every figure below is STANDARD x (this role's effective factor) / (the sum of the
    # effective factors of the roles STAFFED that month). Written out rather than
    # abbreviated, so a reader can check each one against the sentence above it.
    # REQ-CAL-20 rounds every figure to a whole number of hundredths, so the expectation
    # does too. The month's hundredths are handed out by largest remainder, which here
    # agrees with rounding each share on its own - checked, below, by requiring the three
    # to sum to the standard exactly.
    share = lambda eff, den: math.floor(STANDARD * eff / den * 100 + 0.5) / 100  # noqa: E731
    ALL3 = F_LEAD + F_OTHER + F_MAIN                                     # 2.40

    both = load(pg, BOTH)
    check(abs(both["pm"][f"PSN-001|{JAN}"] - share(F_LEAD, ALL3)) < 1e-9,
          "with all three roles held, the lead carries their own factor and no more",
          f"{both['pm'][f'PSN-001|{JAN}']:.4f}, expected {share(F_LEAD, ALL3):.4f}")

    alone = load(pg, ALONE)
    check(abs(alone["pm"][f"PSN-001|{JAN}"] - share(F_LEAD + F_OTHER, ALL3)) < 1e-9,
          "WITH NOBODY IN 'Other staff', ITS FACTOR LANDS ON THE LEAD — who goes from "
          f"{share(F_LEAD, ALL3):.2f} to {share(F_LEAD + F_OTHER, ALL3):.2f} while the "
          "project month does not move",
          f"{alone['pm'][f'PSN-001|{JAN}']:.4f}, expected "
          f"{share(F_LEAD + F_OTHER, ALL3):.4f}")
    check(abs(alone["pm"][f"PSN-003|{JAN}"] - share(F_MAIN, ALL3)) < 1e-9,
          "and Main staff, who covers for nobody, carries exactly what they did before",
          f"{alone['pm'][f'PSN-003|{JAN}']:.4f}, expected {share(F_MAIN, ALL3):.4f}")
    said = " | ".join(alone["msgs"])
    check(OTHER not in said,
          "V-29 stays quiet about a role that IS covered",
          said[:120] or "(nothing reported)")

    nomap = load(pg, NOMAP)
    check(abs(nomap["pm"][f"PSN-001|{JAN}"] - share(F_LEAD, F_LEAD + F_MAIN)) < 1e-9
          and abs(nomap["pm"][f"PSN-003|{JAN}"] - share(F_MAIN, F_LEAD + F_MAIN)) < 1e-9,
          "CLEAR absorbed_by AND THE WORK SPREADS INSTEAD OF BEING DIRECTED — the mapping "
          "is DATA, and what it decides now is WHO picks the absent role up, not whether "
          "anybody does",
          f"lead {nomap['pm'][f'PSN-001|{JAN}']:.4f} (was "
          f"{share(F_LEAD + F_OTHER, ALL3):.4f} with the mapping), main "
          f"{nomap['pm'][f'PSN-003|{JAN}']:.4f}")
    check(any(r == "information|V-29" for r in nomap["rules"]),
          "and V-29 reports the role nothing covers for",
          "; ".join(m[:80] for m in nomap["msgs"][:1]))

    arr = load(pg, ARRIVES)
    check(abs(arr["pm"][f"PSN-001|{JUN}"] - share(F_LEAD + F_OTHER, ALL3)) < 1e-9
          and abs(arr["pm"][f"PSN-001|{JUL}"] - share(F_LEAD, ALL3)) < 1e-9,
          "the cover is PER MONTH: it ends the month somebody arrives, by itself",
          f"June {arr['pm'][f'PSN-001|{JUN}']:.4f}, July {arr['pm'][f'PSN-001|{JUL}']:.4f}")

    sh = load(pg, SHARED)
    check(abs(sh["pm"][f"PSN-001|{JAN}"] - share(F_LEAD + F_OTHER, ALL3) / 2) < 1e-9,
          "two leads share the absorbed factor like any other — the project's total "
          "does not move",
          f"{sh['pm'][f'PSN-001|{JAN}']:.4f} each, expected "
          f"{share(F_LEAD + F_OTHER, ALL3) / 2:.4f}")

    # ONE HOP. Data Analyst is covered by Other staff, who is absent too. The analyst's
    # factor must stop there and never reach the lead, so the lead's effective factor is
    # F_LEAD + F_OTHER and NOT F_LEAD + F_OTHER + F_ANALYST.
    ch = load(pg, CHAIN)
    one_hop = share(F_LEAD + F_OTHER, F_LEAD + F_OTHER + F_MAIN)
    two_hops = share(F_LEAD + F_OTHER + F_ANALYST,
                     F_LEAD + F_OTHER + F_ANALYST + F_MAIN)
    check(abs(ch["pm"][f"PSN-001|{JAN}"] - one_hop) < 1e-9,
          "ONE HOP: an absent role covered by another ABSENT role does not reach the "
          "lead — the work is not passed along a chain",
          f"{ch['pm'][f'PSN-001|{JAN}']:.4f}, expected {one_hop:.4f} "
          f"and not {two_hops:.4f}")
    check(any(r == "information|V-29" for r in ch["rules"]),
          "and V-29 names the role whose work reaches nobody",
          "; ".join(m[:90] for m in ch["msgs"][:1]))

    off = load(pg, OFF)
    check(abs(off["pm"][f"PSN-001|{JAN}"] - share(F_LEAD, F_LEAD + F_MAIN)) < 1e-9,
          "absorb_unstaffed_role_factor = 0 turns the direction off — the absent role's "
          "work still has to go somewhere, and spreads over the staffed roles instead",
          f"{off['pm'][f'PSN-001|{JAN}']:.4f}, expected "
          f"{share(F_LEAD, F_LEAD + F_MAIN):.4f}")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\ntools/prap_io.py — the same plans, worked out separately")
_ALL3 = F_LEAD + F_OTHER + F_MAIN
_two = F_LEAD + F_MAIN
# Rounded to hundredths, as REQ-CAL-20 has the application do.
_r2 = lambda v: math.floor(v * 100 + 0.5) / 100                          # noqa: E731
for name, path, expect in (
        ("all three roles held", BOTH, _r2(STANDARD * F_LEAD / _ALL3)),
        ("nobody in Other staff", ALONE, _r2(STANDARD * (F_LEAD + F_OTHER) / _ALL3)),
        ("the mapping cleared", NOMAP, _r2(STANDARD * F_LEAD / _two)),
        ("one hop only", CHAIN, _r2(STANDARD * (F_LEAD + F_OTHER) / _ALL3)),
        ("absorption off", OFF, _r2(STANDARD * F_LEAD / _two))):
    M = prap_io.Model(prap_io.read_json(path))
    got = prap_io.calculate(M)["pers_month"].get(("PSN-001", JAN))
    check(got is not None and abs(got - expect) < 1e-9,
          f"{name}: the lead carries {expect:.2f} FTE in Jan 2027", f"got {got}")

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
