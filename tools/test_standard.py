"""Where a figure gets its SIZE: the standard monthly FTE (REQ-CAL-19).

Reported from the field, and correct: PeriodFTEStandard never reached the calculation.
It seeded a derived period's weight and it fed V-19, and that was all. Every figure the
application produced came from ProjectPeriod.weight times the role factors — a relative
SHAPE with no magnitude behind it. Worse, the delivered data seeded the project weight
FROM the standard, so the two columns held the same number twice and reading both would
have squared it.

The standard is the month's DEMAND in FTE for a project of this type, phase and work
scope in this period. The project's own period weight adjusts it for that particular
study. The role factors then divide the demand between the roles ACTUALLY STAFFED:

    FTE = standard_fte x period weight x role_share x person weight x month coverage

    role_share = (this role's effective factor / people holding it)
                 -------------------------------------------------
                 (sum of the effective factors of the roles staffed this month)

Every fixture below is small enough to work out by hand, and the expected figure is
written next to the check rather than read back out of the application.

  * THE REVIEWER'S OWN EXAMPLE, to the digit: NewDrug CT Start-up standard 4.02, project
    weight 1.00, two people whose role factors are 0.6 and 0.4 -> the project month is
    4.02 and the two people carry 2.41 and 1.61.
  * THE SHARES ADD TO ONE, so a fully committed project-month IS standard x period
    weight — whatever the factors happen to sum to, and however many roles are staffed.
  * THE PROJECT WEIGHT ADJUSTS, it no longer supplies the magnitude: at 0.50 the same
    month is half. Two different projects on one standard differ by exactly their weights.
  * AN UNSTAFFED ROLE'S WORK LANDS ON THE OTHERS rather than lowering the project.
  * PERSON WEIGHT MOVES LOAD RATHER THAN LOWERING THE MONTH. A part-time commitment is a
    smaller CLAIM on the month, so their colleagues pick the rest up; the project is its
    standard either way. Under-staffing shows on the PEOPLE, never as a cheaper project.
  * A MISSING STANDARD falls back to 1.00 and V-19 says so — deliberately the old
    behaviour, so an incomplete standards sheet degrades to figures its author recognises
    rather than to zero.
  * The browser and tools/prap_io.py agree on all of it.

    python tools/test_standard.py
"""

import pathlib
import sys
import tempfile
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_std_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []
BASE = prap_io.read_xlsx(ROOT / "templates" / "PRAP_SourceData_Template_v1.14.xlsx")
MONTH = date(2026, 9, 1)
K = 2026 * 12 + 8                      # the month key for 2026-09


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def fixture(name, *, std=4.02, weight=1.00, roles=(("Lead data manager", 0.6),
                                                   ("Data Analyst", 0.4)),
            staff=None, person_weights=None, absorbed=None):
    """One project, one month, whatever roles and people the case needs.

    `roles` defines the RoleFactor rows; `staff` names which of them are actually held
    (default: all of them, one person each). Everything runs for the whole of 2026-09,
    so month coverage is exactly 1.00 and cannot muddy an expected figure.
    """
    staff = list(roles and [r for r, _ in roles]) if staff is None else list(staff)
    person_weights = person_weights or {}
    S = {k: (list(v) if isinstance(v, list) else v) for k, v in BASE.items()}
    S["Project"] = [{"project_id": "PRJ-A", "project_name": "A",
                     "project_type": "NewDrug CT", "clinical_phase": "Phase 3",
                     "work_scope_type": "fully in-housed",
                     "start_date": MONTH, "end_date": date(2026, 9, 30),
                     "status": "Active", "__row": 2}]
    S["Milestone"] = []
    S["ProjectPeriod"] = [{"project_id": "PRJ-A", "period_name": "Start-up",
                           "period_seq": 1, "period_start": MONTH,
                           "period_end": date(2026, 9, 30), "weight": weight, "__row": 2}]
    S["PeriodFTEStandard"] = ([] if std is None else
        [{"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
          "work_scope_type": None, "period_name": "Start-up",
          "standard_fte": std, "__row": 2}])
    S["RoleFactor"] = [
        {"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
         "work_scope_type": None, "period_name": "Start-up", "role_name": rn,
         "role_factor": rf, "absorbed_by": (absorbed or {}).get(rn), "__row": 2 + i}
        for i, (rn, rf) in enumerate(roles)]
    S["Person"], S["Assignment"] = [], []
    for i, rn in enumerate(staff, start=1):
        S["Person"].append({"person_id": f"PSN-{i}", "person_name": f"P{i}",
                            "capacity_fte": 1.0, "__row": 1 + i})
        S["Assignment"].append({"assignment_id": f"ASG-{i}", "person_id": f"PSN-{i}",
                                "project_id": "PRJ-A", "role_name": rn,
                                "person_weight": person_weights.get(f"PSN-{i}", 1.0),
                                "__row": 1 + i})
    S["PersonPeriodWeight"] = []
    S["MonthlyEstimate"] = []
    out = TMP / f"{name}.xlsx"
    prap_io.write_xlsx(S, out)
    return out


def figures(path):
    """The project month and each person-month, from the Python implementation."""
    M = prap_io.Model(prap_io.read_xlsx(path))
    C = prap_io.calculate(M)
    return (C["proj_month"].get(("PRJ-A", K), 0.0),
            {sid: v for (sid, k), v in C["pers_month"].items() if k == K},
            M)


print("the standard monthly FTE — where a figure gets its size")

# ---- the reviewer's own example -------------------------------------------------
p = fixture("reviewer")
proj, per, _ = figures(p)
check(abs(proj - 4.02) < 5e-4 and abs(per["PSN-1"] - 2.412) < 5e-4
      and abs(per["PSN-2"] - 1.608) < 5e-4,
      "THE REVIEWER'S EXAMPLE, to the digit — standard 4.02, project weight 1.00, role "
      "factors 0.6 and 0.4",
      f"project {proj:.4f} (want 4.02); {per['PSN-1']:.4f} (want 2.412) and "
      f"{per['PSN-2']:.4f} (want 1.608)")

# ---- the shares add to one, whatever the factors are ----------------------------
odd = (("Project oversight", 0.84), ("Lead data manager", 1.51),
       ("Clinical Data Associator", 0.84), ("Clinical Database Programmer", 1.73),
       ("Data Analyst", 0.57))                          # sums to 5.49, not to 1
proj, per, _ = figures(fixture("five_roles", roles=odd))
check(abs(proj - 4.02) < 5e-4 and abs(sum(per.values()) - 4.02) < 5e-4,
      "THE SHARES ADD TO ONE even though the factors sum to 5.49 — the project month is "
      "the standard, not the standard times the factors",
      f"project {proj:.4f} over {len(per)} people, summing to {sum(per.values()):.4f}")
big, top = max(per.values()), max(f for _, f in odd)     # 1.73, the programmer
check(abs(big - 4.02 * top / 5.49) < 5e-4,
      "and the largest factor takes the largest slice, in proportion",
      f"largest share {big:.4f}, want {4.02 * top / 5.49:.4f} (factor {top} of 5.49)")

# ---- the project weight adjusts, it does not supply the magnitude ---------------
half, _, _ = figures(fixture("half", weight=0.50))
onefifth, _, _ = figures(fixture("heavy", weight=1.20))
check(abs(half - 2.01) < 5e-4 and abs(onefifth - 4.824) < 5e-4,
      "THE PROJECT'S OWN WEIGHT ADJUSTS THE STANDARD — 0.50 halves the month, 1.20 "
      "raises it by a fifth",
      f"weight 0.50 -> {half:.4f} (want 2.01); weight 1.20 -> {onefifth:.4f} (want 4.824)")

# ---- an unstaffed role's work lands on the others -------------------------------
proj, per, _ = figures(fixture("understaffed", roles=odd,
                               staff=["Lead data manager", "Clinical Data Associator"]))
check(abs(proj - 4.02) < 5e-4,
      "AN UNSTAFFED ROLE DOES NOT MAKE THE PROJECT CHEAPER — two of five roles held, and "
      "the month is still the standard",
      f"project {proj:.4f} over 2 people (want 4.02)")
check(abs(per["PSN-1"] - 4.02 * 1.51 / (1.51 + 0.84)) < 5e-4,
      "the two of them carry it between them, in proportion to their own factors",
      f"{per['PSN-1']:.4f} and {per['PSN-2']:.4f}")

# ---- person weight moves the load, it does not lower the month ------------------
# Claims: PSN-1 = 0.6 x 1.00 = 0.60; PSN-2 = 0.4 x 0.40 = 0.16. Sum 0.76.
# Shares 0.60/0.76 and 0.16/0.76 of a month that is still 4.02.
proj, per, _ = figures(fixture("parttime", person_weights={"PSN-2": 0.40}))
want1, want2 = 4.02 * 0.60 / 0.76, 4.02 * 0.16 / 0.76
check(abs(proj - 4.02) < 5e-4 and abs(per["PSN-1"] - want1) < 5e-4
      and abs(per["PSN-2"] - want2) < 5e-4,
      "PERSON WEIGHT MOVES LOAD ONTO THE OTHERS, it does not lower the month — the "
      "part-timer's colleague picks the work up, and the project is still its standard",
      f"project {proj:.4f} (want 4.02); the full-timer goes 2.4120 -> {per['PSN-1']:.4f}, "
      f"the 0.40 person {per['PSN-2']:.4f}")

# ---- a missing standard degrades to the old behaviour ---------------------------
proj, _, M = figures(fixture("nostandard", std=None, weight=1.30))
v19 = [f for f in M.findings if f["rule"] == "V-19"]
check(abs(proj - 1.30) < 5e-4 and v19,
      "A MISSING STANDARD FALLS BACK TO 1.00 and V-19 names it — the project month "
      "becomes its own period weight, which is exactly what it was before this change",
      f"project {proj:.4f} (want 1.30, the period weight alone); "
      f"{len(v19)} V-19 finding(s)")

# ---- and the browser agrees on every one of them --------------------------------
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page()
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    worst, n = 0.0, 0
    for name in ("reviewer", "five_roles", "half", "heavy", "understaffed", "parttime",
                 "nostandard"):
        path = TMP / f"{name}.xlsx"
        pg.goto(APP)
        pg.wait_for_timeout(200)
        pg.set_input_files("#picker", str(path))
        pg.wait_for_timeout(1800)
        app = pg.evaluate("() => { const o = {}; for (const [k, v] of S.calc.persMonth) "
                          "o[k] = v; return o; }")
        _, ref, _ = figures(path)
        for sid, v in ref.items():
            worst = max(worst, abs(v - app.get(f"{sid}|{K}", 0.0)))
            n += 1
    check(worst < 1e-9,
          "THE BROWSER AND tools/prap_io.py AGREE on every figure above — four "
          "implementations were changed, and they must not have drifted",
          f"{n} person-months across 7 fixtures, worst difference {worst:.2e}")
    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
