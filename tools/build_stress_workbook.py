"""Build a workbook at exactly the volume REQ-NFR-03 names, to measure against it.

    100 projects, 1,000 people, order 8,000 assignments, a 60-month horizon.

That requirement also says "tables of that height are virtualised", and X-04 of the UI
component list recorded virtualisation as built. It was never built. This file exists so
the question "does that matter" is answered by measurement rather than by argument.

Nothing here is a scenario. It is bulk, shaped only enough to be realistic: staggered
starts so the concurrency is plausible, every clinical type and phase, and each person on
several projects. The figures are not meant to be read - the point is the SIZE.

    python tools/build_stress_workbook.py

Output: templates/PRAP_SourceData_Stress_1000_v1.0.xlsx  (not committed - see below)

DELIBERATELY NOT COMMITTED by default. It is roughly a megabyte of generated filler that
tells a reader nothing the generator does not, and the repository already carries four
workbooks that are worth reading. Pass --keep to write it anyway.
"""

import importlib.util
import pathlib
import random
import sys
from datetime import date

from dateutil.relativedelta import relativedelta as rd
from openpyxl import Workbook, load_workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "1.0"
SOURCE = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.10.xlsx"
OUT = ROOT / "templates" / f"PRAP_SourceData_Stress_1000_v{VERSION}.xlsx"

_spec = importlib.util.spec_from_file_location("bsw", ROOT / "tools" / "build_source_workbook.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

N_PROJECTS = 100
N_PEOPLE = 1000
HORIZON_MONTHS = 60

ROLES = ["Project oversight", "Lead data manager", "Clinical Data Associator",
         "Clinical Database Programmer", "Data Analyst"]
OROLES = ["Project lead", "Main staff", "Other staff"]
TYPES = [("NewDrug CT", ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]),
         ("Biosimilar CT (Healthy)", ["Phase 1", "Phase 3"]),
         ("Biosimilar CT (Patient)", ["Phase 1", "Phase 3"]),
         ("Others", [None])]
SCOPES = ["fully in-housed", "fully outsourced", "Partially outsourced (in-house for EDC)"]
DEPTS = ["Clinical Operations", "Data Management", "Programming", "Biostatistics",
         "Business Systems"]


def eom(d):
    return (d + rd(months=1)).replace(day=1) - rd(days=1)


def main(keep=False):
    rnd = random.Random(20260913)
    src = load_workbook(SOURCE)
    take = lambda s: [list(r) for r in src[s].iter_rows(min_row=2, values_only=True) if r[0]]
    pws_rows, role_rows, cfg_rows = take("PeriodFTEStandard"), take("RoleFactor"), take("Config")

    proj, per, ppl, asg = [], [], [], []
    base = date(2025, 1, 1)

    for i in range(N_PROJECTS):
        pid = f"PRJ-{i + 1:03d}"
        t, phases = TYPES[i % len(TYPES)]
        phase = phases[i % len(phases)]
        # Staggered across four years so the concurrency is plausible rather than all
        # hundred running at once, which no organisation does and which would make every
        # person permanently over the ceiling (REQ-CAL-19: the demand is the project's).
        start = (base + rd(months=rnd.randrange(0, 48))).replace(day=1)
        spans = ([("Planning", 3), ("Develop", rnd.randint(6, 12)), ("Close", 2)]
                 if t == "Others" else
                 [("Before-Start-up", 2), ("Start-up", 4),
                  ("Conduct (interim)", rnd.randint(5, 9)), ("Close-out (interim)", 2),
                  ("Conduct (final)", rnd.randint(5, 10)), ("Close-out (final)", 3)])
        cur = start
        for seq, (nm, months) in enumerate(spans, start=1):
            end = eom(cur + rd(months=months - 1))
            per.append([pid, nm, seq, cur, end, round(rnd.uniform(0.80, 1.25), 2), None])
            cur = end + rd(days=1)
        pend = per[-1][4]
        proj.append([pid, f"{pid} {t.split()[0]} study", t,
                     None if t == "Others" else f"Compound {chr(65 + i % 26)}", phase,
                     rnd.choice(SCOPES), None, "by SB", "by SB", "by SB", "by SB",
                     "Veeva EDC", "Veeva DQS", "CluePoints", None, start, pend, None,
                     "Active", "automatic", "Stress fixture - bulk, not a scenario",
                     None, None, None, None])

    for i in range(N_PEOPLE):
        sid = f"PSN-{i + 1:04d}"
        dept = DEPTS[i % len(DEPTS)]
        roles = OROLES if dept == "Business Systems" else ROLES
        ppl.append([sid, f"Person {i + 1:04d}", dept, roles[i % len(roles)],
                    rnd.choice([1.00] * 8 + [0.80, 0.60]), None, None,
                    "Stress fixture", None, None, None, None])

    # Order 8,000 assignments, spread so nobody is on an implausible number of projects.
    load = {f"PSN-{i + 1:04d}": 0 for i in range(N_PEOPLE)}
    n = 0
    per_project = max(1, round(8000 / N_PROJECTS))
    for i, prow in enumerate(proj):
        pid, t = prow[0], prow[2]
        roles = OROLES if t == "Others" else ROLES
        pool = sorted(rnd.sample(list(load), 400), key=lambda x: load[x])[:per_project]
        for k in range(per_project):
            sid = pool[k % len(pool)]
            load[sid] += 1
            n += 1
            asg.append([f"ASG-{n:05d}", sid, None, pid, roles[k % len(roles)],
                        None, None, round(rnd.uniform(0.15, 0.55), 2), "automatic",
                        "Stress fixture", None, None])

    wb = Workbook()
    wb.remove(wb.active)
    list_rows, list_ranges = [], {}
    r = 2
    for name, values in B.LISTS:
        for v in values:
            list_rows.append((name, v, None))
        list_ranges[name] = f"Lists!$B${r}:$B${r + len(values) - 1}"
        r += len(values)

    B.add_readme(wb, "stress", [
        "",
        "WHAT THIS FILE IS",
        f"   The volume REQ-NFR-03 names: {N_PROJECTS} projects, {N_PEOPLE} people, "
        f"{len(asg)} assignments.",
        "   Bulk, not scenarios. The figures are not meant to be read - the point is the SIZE.",
        "   Built to answer one question by measurement: does the absence of row",
        "   virtualisation (component X-04) matter at the volume the requirement names?",
    ])
    B.write_sheet(wb, "Project", proj, None, list_ranges)
    B.write_sheet(wb, "Milestone", [], None, list_ranges)
    B.write_sheet(wb, "ProjectPeriod", per, None, list_ranges)
    B.write_sheet(wb, "PeriodFTEStandard", pws_rows, None, list_ranges)
    B.write_sheet(wb, "RoleFactor", role_rows, None, list_ranges)
    B.write_sheet(wb, "Person", ppl, None, list_ranges)
    B.write_sheet(wb, "Assignment", asg, None, list_ranges)
    B.write_sheet(wb, "PersonPeriodWeight", [], None, list_ranges)
    B.write_sheet(wb, "MonthlyEstimate", [], None, list_ranges)
    B.write_sheet(wb, "Lists", list_rows, None, list_ranges)
    B.write_sheet(wb, "Config", cfg_rows, None, list_ranges)
    wb.save(OUT)
    print(f"Written: {OUT}")
    print(f"  {len(proj)} projects | {len(ppl)} people | {len(asg)} assignments | "
          f"{len(per)} periods | {OUT.stat().st_size:,} bytes")
    if not keep:
        print("  (pass --keep to leave it on disk; it is generated filler, not a deliverable)")


if __name__ == "__main__":
    main("--keep" in sys.argv)
