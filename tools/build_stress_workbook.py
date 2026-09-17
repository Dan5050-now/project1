"""Build a workbook at any volume, so a requirement about volume can be measured.

    --projects N --people M   (default: the volume REQ-NFR-03 names, 100 x 150)

IT WAS WRITTEN TO SETTLE ONE ARGUMENT AND IS KEPT TO SETTLE THE NEXT. REQ-NFR-03 used to
name 100 projects and 1,000 people and say "tables of that height are virtualised"; X-04
of the UI component list recorded that virtualisation as built, and it never was. Rather
than build it or argue about it, fixtures were generated here and timed by
tools/measure_scale.py: the rendering budget turned out to be crossed at about 400 people,
so at R-47 the REQUIREMENT moved to 100 x 150 - the largest volume whose worst case is
still inside budget - and the virtualisation clause was removed.

So the default below is the amended figure, and the point of the flags is that the next
person to ask for more volume can price it in a few minutes instead of arguing about it.
NOTE WHICH FIGURE BINDS: both Overall tables sit on one tab, so the cost follows
(projects + people) rows x horizon months. 50 x 200 and 100 x 150 are the same 252 rows
and measure within 10 ms of each other; varying the project count alone answers nothing.

Nothing here is a scenario. It is bulk, shaped only enough to be realistic: staggered
starts so the concurrency is plausible, every clinical type and phase, and each person on
several projects. The figures are not meant to be read - the point is the SIZE.

    python tools/build_stress_workbook.py --keep
    python tools/build_stress_workbook.py --projects 100 --people 400 --keep

Output: templates/PRAP_SourceData_Stress_<projects>x<people>_v1.0.xlsx  (not committed)

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

# Defaults are the volume REQ-NFR-03 names since R-47. Override to measure another scale:
#     python tools/build_stress_workbook.py --projects 100 --people 400 --keep
# Assignments are derived rather than fixed, so the shape stays realistic at any size:
# each project is staffed by a handful of people, which is what decides how many projects
# one person ends up on once the pool is a given size.
N_PROJECTS = 100
N_PEOPLE = 150
ROLES_PER_PROJECT = 80          # only used at the old 1,000-person volume; see main()
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


def main(keep=False, n_projects=N_PROJECTS, n_people=N_PEOPLE, per_project=None):
    global OUT
    OUT = ROOT / "templates" / f"PRAP_SourceData_Stress_{n_projects}x{n_people}_v{VERSION}.xlsx"
    # A project is staffed by a handful of people, so the assignment count follows the
    # pool rather than the other way round: about six a project, which puts each person on
    # roughly the same number of projects whatever the size. The 80-a-project branch
    # exists only to reproduce the old 1,000-person measurements, where 8,000 assignments
    # was part of the figure REQ-NFR-03 named before R-47.
    if per_project is None:
        per_project = ROLES_PER_PROJECT if n_people >= 500 else 6
    rnd = random.Random(20260913)
    src = load_workbook(SOURCE)
    take = lambda s: [list(r) for r in src[s].iter_rows(min_row=2, values_only=True) if r[0]]
    pws_rows, role_rows, cfg_rows = take("PeriodFTEStandard"), take("RoleFactor"), take("Config")

    proj, per, ppl, asg = [], [], [], []
    base = date(2025, 1, 1)

    for i in range(n_projects):
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

    for i in range(n_people):
        sid = f"PSN-{i + 1:04d}"
        dept = DEPTS[i % len(DEPTS)]
        roles = OROLES if dept == "Business Systems" else ROLES
        ppl.append([sid, f"Person {i + 1:04d}", dept, roles[i % len(roles)],
                    rnd.choice([1.00] * 8 + [0.80, 0.60]), None, None,
                    "Stress fixture", None, None, None, None])

    # Order 8,000 assignments, spread so nobody is on an implausible number of projects.
    load = {f"PSN-{i + 1:04d}": 0 for i in range(n_people)}
    n = 0
    for i, prow in enumerate(proj):
        pid, t = prow[0], prow[2]
        roles = OROLES if t == "Others" else ROLES
        pool = sorted(rnd.sample(list(load), min(400, n_people)),
                      key=lambda x: load[x])[:per_project]
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
        f"   {n_projects} projects, {n_people} people, {len(asg)} assignments.",
        "   Bulk, not scenarios. The figures are not meant to be read - the point is the SIZE.",
        "   Built so a requirement about volume can be MEASURED rather than asserted.",
        f"   The Overall tab's two tables come to {n_projects + n_people} rows; at a 60-month",
        "   horizon that row count and that horizon together are what decide the cost.",
        "   Drive it with tools/measure_scale.py. REQ-NFR-03 names 100 x 150 since R-47.",
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


def _arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


if __name__ == "__main__":
    main("--keep" in sys.argv,
         _arg("--projects", N_PROJECTS), _arg("--people", N_PEOPLE),
         _arg("--per-project", None) if "--per-project" in sys.argv else None)
