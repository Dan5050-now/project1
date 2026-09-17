"""Build a source workbook that exercises the FEATURES, one scenario at a time.

The two delivered dummies are plans: they are shaped like real work and they validate
clean. That makes them good for reading figures and poor for exercising the application,
because the interesting cases - a month stated by hand, a role nobody holds, a person on
two override windows - are scattered through them if they are there at all.

This file is the other thing. Every project is ONE scenario, named after it, with a note
on the row saying what to look at and where. Nothing is random and nothing is filler: if
a row is here, it is here to make something happen on screen.

    python tools/build_scenario_workbook.py

Output: templates/PRAP_SourceData_Scenarios_v<version>.xlsx

WHAT IT DOES NOT DO. It does not trip the ERROR-class rules that reject a row - an
unknown project_id on an assignment, a role with no factor, a date that ends before it
starts. Those need a file that is broken on purpose, and a broken file cannot also be the
one you click through to see the application work. The rules reported here are the ones
that leave a usable plan behind: warnings, information, and the two manual-estimate rules
that report a figure rather than reject a row.

The standards - PeriodFTEStandard, RoleFactor, Lists, Config - are taken from the
delivered dummy rather than re-derived, so this file costs its work by exactly the same
assumptions as everything else.
"""

import importlib.util
import pathlib
from datetime import date

from dateutil.relativedelta import relativedelta as rd
from openpyxl import Workbook, load_workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERSION = "1.0"
SOURCE = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.10.xlsx"
OUT = ROOT / "templates" / f"PRAP_SourceData_Scenarios_v{VERSION}.xlsx"
LARGE_VERSION = "1.0"
LARGE_OUT = ROOT / "templates" / f"PRAP_SourceData_Scenarios_50x50_v{LARGE_VERSION}.xlsx"

_spec = importlib.util.spec_from_file_location("bsw", ROOT / "tools" / "build_source_workbook.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)

CLIN = ["Before-Start-up", "Start-up", "Conduct (interim)", "Close-out (interim)",
        "Conduct (final)", "Close-out (final)", "After Close-out (final)"]
OTHER_P = ["Planning", "Develop", "Close"]
ROLES = ["Project oversight", "Lead data manager", "Clinical Data Associator",
         "Clinical Database Programmer", "Data Analyst"]
OROLES = ["Project lead", "Main staff", "Other staff"]

# Every scenario in the file, in the order the projects appear. The README sheet is
# written from this list, so a scenario cannot be added without being documented.
SCENARIOS = []


def scenario(pid, what, look):
    SCENARIOS.append((pid, what, look))
    return pid


def eom(d):
    return (d + rd(months=1)).replace(day=1) - rd(days=1)


def periods(pid, start, spans, weights=None):
    """spans: [(period_name, months)] laid end to end from `start`, no gap, no overlap."""
    out, cur = [], start
    for seq, (name, months) in enumerate(spans, start=1):
        end = eom(cur + rd(months=months - 1))
        w = (weights or {}).get(name, 1.00)
        out.append([pid, name, seq, cur, end, w, None])
        cur = end + rd(days=1)
    return out, out[-1][4]


def months_between(a, b):
    out, cur = [], date(a.year, a.month, 1)
    while cur <= b:
        out.append(f"{cur.year:04d}-{cur.month:02d}")
        cur += rd(months=1)
    return out


def main(size="small"):
    """size 'small': the 12 hand-built scenario projects alone.
       size 'large': the same scenarios, plus enough generated work to reach 50 and 50."""
    src = load_workbook(SOURCE)
    take = lambda s: [list(r) for r in src[s].iter_rows(min_row=2, values_only=True) if r[0]]
    pws_rows, role_rows = take("PeriodFTEStandard"), take("RoleFactor")
    cfg_rows = take("Config")

    # The standard for a project-month, looked up the way the application looks it up:
    # an exact work-scope match first, then the row that leaves work_scope_type blank,
    # which is the "applies to every scope" row.
    std = {}
    for t, ph, sc, pn, v, _ in pws_rows:
        std[(t, ph, sc, pn)] = v

    def standard(t, ph, sc, pn):
        return std.get((t, ph, sc, pn), std.get((t, ph, None, pn), 1.00))

    proj, mile, per, ppl, asg, ppw, est = [], [], [], [], [], [], []

    def project(pid, name, ptype, phase, start, spans, weights=None, status="Active",
                estimation="automatic", category="Scenario product", scope="fully in-housed",
                note=None, total_months=None):
        p, end = periods(pid, start, spans, weights)
        per.extend(p)
        proj.append([pid, name, ptype, category, phase, scope, None,
                     "by SB", "by SB", "by SB", "by SB",
                     "Veeva EDC", "Veeva DQS", "CluePoints", None,
                     start, end, total_months, status, estimation, note,
                     None, None, None, None])
        return end

    def person(sid, nm, dept, role, cap, note=None):
        ppl.append([sid, nm, dept, role, cap, None, None, note, None, None, None, None])
        return sid

    def assign(aid, sid, pid, role, w, s=None, e=None, estimation="automatic", note=None):
        asg.append([aid, sid, None, pid, role, s, e, w, estimation, note, None, None])
        return aid

    # ================================================================ projects
    base = date(2026, 1, 1)
    CT7 = [("Before-Start-up", 2), ("Start-up", 4), ("Conduct (interim)", 6),
           ("Close-out (interim)", 2), ("Conduct (final)", 6), ("Close-out (final)", 3),
           ("After Close-out (final)", 1)]

    p1 = scenario("SCN-001", "The baseline: every clinical period, every role staffed, "
                  "all figures calculated.",
                  "Overall > Monthly demand by project. Source data (project) > "
                  "Periods, to see the standard beside each weight.")
    e1 = project(p1, "SCN-001 Baseline trial", "NewDrug CT", "Phase 3", base, CT7,
                 note="SCENARIO. Nothing unusual - read this one first, the others are "
                      "departures from it.")

    p2 = scenario("SCN-002", "A project STATED BY HAND, below what its own standard asks "
                  "for. Trips V-34 short.",
                  "Overall > Standard vs staffed. The month is marked on the chart and "
                  "in Resource by project; click it to open the figures behind it.")
    e2 = project(p2, "SCN-002 Stated below standard", "NewDrug CT", "Phase 1", base, CT7,
                 estimation="manual",
                 note="SCENARIO. estimation_type = manual, with figures deliberately "
                      "smaller than the standard - V-34 short.")

    p3 = scenario("SCN-003", "The same, stated ABOVE the standard. Trips V-34 over.",
                  "Overall > Standard vs staffed - the two directions are counted "
                  "separately and never netted off.")
    e3 = project(p3, "SCN-003 Stated above standard", "Biosimilar CT (Healthy)", "Phase 3",
                 base, CT7, estimation="manual",
                 note="SCENARIO. estimation_type = manual, figures above the standard - V-34 over.")

    p4 = scenario("SCN-004", "A project figure stated by hand OVER an assignment figure "
                  "also stated by hand. Trips V-33.",
                  "Source data (person) > PSN-004 > Monthly estimation. The stated "
                  "figure and the one actually given are both shown.")
    e4 = project(p4, "SCN-004 Two manual levels", "Biosimilar CT (Patient)", "Phase 1",
                 base, CT7, estimation="manual",
                 note="SCENARIO. Both levels manual. The project figure is the mother "
                      "figure and the people on it are scaled to it (REQ-CAL-18) - V-33.")

    p5 = scenario("SCN-005", "An assignment on manual with a month that has NO figure. "
                  "Trips V-31.",
                  "Source data (person) > PSN-005 > Monthly estimation, and the 'Fill "
                  "the missing months' button.")
    e5 = project(p5, "SCN-005 Missing stated month", "NewDrug CT", "Phase 2", base, CT7,
                 note="SCENARIO. One assignment here is manual with a month left "
                      "unstated - V-31. Its Inspection is also early - V-21.")

    p6 = scenario("SCN-006", "A project figure for a month with NOBODY assigned. "
                  "Trips V-32 - it cannot be shared out, so it is not applied.",
                  "The findings report, and Source data (project) > Monthly estimation.")
    e6 = project(p6, "SCN-006 Figure with nobody on it", "NewDrug CT", "Phase 4", base,
                 CT7, estimation="manual",
                 note="SCENARIO. Manual figures run the whole project; the staffing "
                      "stops half way, so the later figures cannot be shared out - V-32.")

    p7 = scenario("SCN-007", "An 'Others' project: three hand-entered periods, three "
                  "'Others' roles, no milestone derivation.",
                  "Source data (project) > Periods. The derivation button offers "
                  "'Standard periods' here, not 'Auto derivation'.")
    e7 = project(p7, "SCN-007 Internal project", "Others", None, base,
                 [("Planning", 3), ("Develop", 8), ("Close", 2)],
                 category=None, note="SCENARIO. An 'Others' project: no clinical phase, no product, "
                                     "and periods entered by hand.")

    p8 = scenario("SCN-008", "A role NOBODY holds, whose factor is picked up by another "
                  "role (REQ-CAL-16).",
                  "Source data (project) > Utilisation. Clinical Data Associator is "
                  "unstaffed; its factor lands on the Lead data manager.")
    e8 = project(p8, "SCN-008 Unstaffed role absorbed", "NewDrug CT", "Phase 2", base, CT7,
                 note="SCENARIO. No Clinical Data Associator is assigned; "
                      "RoleFactor.absorbed_by sends that work to the Lead data manager.")

    p9 = scenario("SCN-009", "One role held by THREE people at once, so each claims a "
                  "third of what one would.",
                  "Source data (person) > Monthly estimation > 'Sharing this role'. "
                  "The project's month does not move when a sharer is added.")
    e9 = project(p9, "SCN-009 Three share one role", "NewDrug CT", "Phase 3", base, CT7,
                 note="SCENARIO. Three people hold Clinical Data Associator, so each "
                      "claims a third of the factor. A milestone is also duplicated - V-20.")

    p10 = scenario("SCN-010", "A project with NO assignments at all.",
                   "Resource by project - it draws nothing, and says so rather than "
                   "disappearing.")
    e10 = project(p10, "SCN-010 Nobody assigned", "Others", None, base,
                  [("Planning", 2), ("Develop", 6), ("Close", 2)], category=None,
                  status="Planned",
                  note="SCENARIO. No assignments at all - it draws nothing and says so "
                       "rather than disappearing from the tables.")

    p11 = scenario("SCN-011", "A derived column that DISAGREES with its master row. "
                   "Trips V-13 - the file is read, then the master value wins.",
                   "The findings report. A milestone here records the wrong "
                   "project_name; Project is the master and is used.")
    e11 = project(p11, "SCN-011 Derived disagreement", "NewDrug CT", "Phase 3", base, CT7,
                  total_months=99,
                  note="SCENARIO. One milestone row carries a stale project_name - V-13. "
                       "total_period_months also says 99; that one is recomputed in "
                       "silence, because the file's value is never trusted for it.")

    p12 = scenario("SCN-012", "A clinical trial with NO product recorded. Trips V-04.",
                   "The findings report - a warning, not a refusal: the plan is still "
                   "costed.")
    e12 = project(p12, "SCN-012 No product named", "NewDrug CT", "Phase 1", base, CT7,
                  category=None,
                  note="SCENARIO. A clinical trial with no product recorded - V-04. "
                       "A warning, not a refusal: the plan is still costed.")

    # ---- milestones, on the baseline and one with an early inspection ----------
    def milestones(pid, start, early_inspection=False, duplicate=False):
        seq = 0
        m = [("Protocol (v1)", start),
             ("CTA submission", start + rd(months=1)),
             ("First SIV", start + rd(months=5)),
             ("FPI", start + rd(months=6)),
             ("LPI", start + rd(months=11)),
             ("interim DB lock cut-off", start + rd(months=11)),
             ("interim DB lock", start + rd(months=12)),
             ("final DB lock cut-off", start + rd(months=19)),
             ("final DB lock", start + rd(months=20)),
             ("Inspection", start + rd(months=(8 if early_inspection else 22)))]
        if duplicate:
            m.append(("FPI", start + rd(months=7)))
        for nm, d in sorted(m, key=lambda kv: kv[1]):
            seq += 1
            mile.append([pid, None, nm, d, seq,
                         "DELIBERATE: a second FPI, which V-20 reports" if duplicate and nm == "FPI"
                         and d == start + rd(months=7) else None])

    milestones(p1, base)
    scenario("SCN-013", "An Inspection BEFORE the final DB lock, which does not open the "
             "after-close-out period. Trips V-21, for information.",
             "The findings report, and Overall > Project timeline (SCN-005).")
    milestones(p5, base, early_inspection=True)
    scenario("SCN-014", "A milestone name recorded TWICE on one project. Trips V-20.",
             "The findings report, and Source data (project) > Milestones (SCN-009).")
    milestones(p9, base, duplicate=True)
    milestones(p11, base)
    scenario("PSN-002/3", "A capacity BELOW the under-allocation floor, so the person "
             "can never clear it however fully they are booked. Trips V-22.",
             "The findings report. 0.50 and 0.00 are both legal capacities - V-35 "
             "bounds the column at 0.00 to 1.00 - and both are under the 0.60 floor.")
    scenario("PSN-001", "A person over the 1.50 FTE ceiling, on four projects at once.",
             "Overall > Resource by person, and Source data (person) > Utilisation: "
             "the bar is outlined where the month crosses a threshold.")
    scenario("BLK-xxx", "A milestone dated AFTER the project's own end, which extends "
             "the timeline rather than being dropped. Trips V-14, for information. "
             "(Large set only.)",
             "The findings report, and Overall > Project timeline.")
    scenario("(several)", "A role that carries a factor and that NOBODY holds and "
             "nothing covers for. Trips V-29, for information - it is work not being "
             "counted.",
             "The findings report. Distinct from SCN-008, where the unstaffed role IS "
             "covered and so is not reported.")
    # A DERIVED column that disagrees with its master row. project_name on Milestone is
    # looked up from Project; a file written before the project was renamed still carries
    # the old one, which is the case V-13 exists for. Set on one row only, so the finding
    # names a row rather than a sheet.
    for row in mile:
        if row[0] == p11:
            row[1] = "SCN-011 under its OLD name"
            row[5] = "DELIBERATE: a stale project_name, which V-13 reports before the "\
                     "master value is used."
            break

    # ================================================================== people
    person("PSN-001", "Over Allocated", "Data Management", "Lead data manager", 1.00,
           "Deliberately on five projects at once - crosses the 1.50 ceiling.")
    person("PSN-002", "Half Timer", "Data Management", "Clinical Data Associator", 0.50,
           "capacity_fte 0.50. Capacity is context only - the thresholds are absolute.")
    person("PSN-003", "On The Books", "Clinical Operations", "Project oversight", 0.00,
           "capacity_fte 0.00 - on the books and not available. A legal value, and the "
           "bottom of the range V-35 enforces.")
    person("PSN-004", "Manual Figures", "Data Management", "Lead data manager", 1.00,
           "Carries an assignment-level manual estimate that the project figure overrides.")
    person("PSN-005", "Missing Month", "Programming", "Clinical Database Programmer", 1.00,
           "Manual, with one month left unstated.")
    person("PSN-006", "One Window", "Biostatistics", "Data Analyst", 1.00,
           "One PersonPeriodWeight window.")
    person("PSN-007", "Two Windows", "Biostatistics", "Data Analyst", 1.00,
           "TWO override windows on one assignment - which is why the override key "
           "includes the dates.")
    person("PSN-008", "Part Of Project", "Clinical Operations", "Project oversight", 1.00,
           "Assignment dates inside the project's own - joins late, leaves early.")
    person("PSN-009", "Whole Project", "Clinical Operations", "Project oversight", 1.00,
           "Both assignment dates BLANK, which means the project's own dates.")
    person("PSN-010", "Under Allocated", "Programming", "Data Analyst", 1.00,
           "One small assignment - a run below the 0.60 floor.")
    person("PSN-011", "Sharer Two", "Data Management", "Clinical Data Associator", 1.00,
           "Shares a role with PSN-012 and PSN-002.")
    person("PSN-012", "Sharer Three", "Data Management", "Clinical Data Associator", 1.00,
           "The third holder of that role.")
    person("PSN-013", "No Work", "Business Systems", "Data Analyst", 1.00,
           "No assignments at all - appears in the tables and draws nothing.")

    # ============================================================= assignments
    n = [0]

    def aid():
        n[0] += 1
        return f"ASG-{n[0]:03d}"

    # A pool to rotate through, so the load SPREADS. `PSN-{(i % 9) + 1}` was the first
    # attempt and it put PSN-001 on the first role of every project, which took them to
    # 15 FTE - a person so over the ceiling that it reads as a bug rather than a
    # scenario. REQ-CAL-19 is why: a project-month IS its standard, divided among the
    # people on it, so a project staffed thinly gives each of them a large share.
    pool = [f"PSN-{i:03d}" for i in (6, 7, 8, 9, 10, 11, 12, 13)]
    turn = [0]

    def next_person():
        sid = pool[turn[0] % len(pool)]
        turn[0] += 1
        return sid

    # SCN-001: every clinical role staffed, so the month divides five ways
    for role in ROLES:
        assign(aid(), next_person(), p1, role, 0.30)
    # SCN-002/003: staffed so the manual figures have somebody to land on
    for pid in (p2, p3):
        for role in ROLES:
            assign(aid(), next_person(), pid, role, 0.30)
    # SCN-004: PSN-004 on manual, beside colleagues
    a_manual = assign(aid(), "PSN-004", p4, "Lead data manager", 0.40,
                      estimation="manual",
                      note="Assignment-level manual. The project is manual too, so this "
                           "figure is scaled to the project's month - V-33.")
    for role in ["Project oversight", "Clinical Data Associator", "Data Analyst"]:
        assign(aid(), next_person(), p4, role, 0.30)
    # SCN-005: manual with a gap
    a_gap = assign(aid(), "PSN-005", p5, "Clinical Database Programmer", 0.40,
                   estimation="manual",
                   note="One month of this assignment has no stated figure - V-31.")
    for role in ["Project oversight", "Lead data manager", "Data Analyst"]:
        assign(aid(), next_person(), p5, role, 0.30)
    # SCN-006: staffed only in the first half, so a later project figure has nobody
    assign(aid(), next_person(), p6, "Lead data manager", 0.30,
           s=base, e=eom(base + rd(months=5)),
           note="Leaves half way through, which is what leaves the later project "
                "figures with nobody to share out to - V-32.")
    # SCN-007: the three 'Others' roles
    for role in OROLES:
        assign(aid(), next_person(), p7, role, 0.30)
    # SCN-008: Clinical Data Associator deliberately absent, so its factor is absorbed
    for role in ["Project oversight", "Lead data manager", "Clinical Database Programmer",
                 "Data Analyst"]:
        assign(aid(), next_person(), p8, role, 0.25)
    # SCN-009: three people on one role
    for sid in ("PSN-002", "PSN-011", "PSN-012"):
        assign(aid(), sid, p9, "Clinical Data Associator", 0.40,
               note="One of three holders of this role - the factor is divided by three.")
    for role in ["Project oversight", "Lead data manager", "Data Analyst"]:
        assign(aid(), next_person(), p9, role, 0.30)
    # SCN-011 / SCN-012: ordinary staffing, so the warning is the only oddity
    for pid in (p11, p12):
        for role in ROLES[:4]:
            assign(aid(), next_person(), pid, role, 0.30)

    # windows, partial dates, whole project, under-allocation
    a_one = assign(aid(), "PSN-006", p1, "Data Analyst", 0.60,
                   note="Carries ONE override window.")
    a_two = assign(aid(), "PSN-007", p1, "Data Analyst", 0.60,
                   note="Carries TWO override windows, which is why the key includes "
                        "the dates.")
    assign(aid(), "PSN-008", p1, "Project oversight", 0.40,
           s=base + rd(months=4), e=eom(base + rd(months=15)),
           note="Joins four months in and leaves early - a partial involvement.")
    assign(aid(), "PSN-009", p1, "Project oversight", 0.40,
           note="Both dates BLANK, so this is the project's own window (REQ-CAL-15).")
    assign(aid(), "PSN-010", p7, "Other staff", 0.05,
           note="One small commitment and nothing else - a run under the 0.60 floor.")

    # PSN-001 across four projects, which is what takes them over the ceiling. The role
    # must be one the project's TYPE has a factor for: a clinical role on an 'Others'
    # project is V-03 and V-23, an error, and belongs in a file broken on purpose.
    for pid in (p1, p2, p3, p9):
        assign(aid(), "PSN-001", pid, "Lead data manager", 0.50,
               note="One of four projects PSN-001 is on - together they cross the "
                    "1.50 FTE ceiling.")
    assign(aid(), "PSN-003", p7, "Project lead", 0.30,
           note="capacity 0.00 and still assignable - capacity is context, not a limit.")

    ppw.append([a_one, base + rd(months=6), eom(base + rd(months=8)), 0.20,
                "Part-time for a quarter - REPLACES person_weight, does not multiply it"])
    ppw.append([a_two, base + rd(months=3), eom(base + rd(months=5)), 0.15,
                "First window: reduced"])
    ppw.append([a_two, base + rd(months=9), eom(base + rd(months=11)), 0.90,
                "Second window on the SAME assignment: covering a peak"])

    # ======================================================= monthly estimates
    def stated(scope, ref, ms, figures, note_first=None):
        for i, (mm, v) in enumerate(zip(ms, figures)):
            est.append([scope, ref, mm, v, note_first if i == 0 else None])

    # Each month's DEMAND, so a figure stated "below" or "above" the standard really is,
    # by a stated proportion, rather than by a number somebody guessed.
    def demand(pid, ptype, phase, scope="fully in-housed"):
        out = {}
        for row in per:
            if row[0] != pid:
                continue
            _, pn, _, ps, pe, w, _ = row
            for mm in months_between(ps, pe):
                out[mm] = round(standard(ptype, phase, scope, pn) * (w or 1.0), 2)
        return out

    def at(d, ms, factor):
        return [round(d.get(m, 1.0) * factor, 2) for m in ms]

    m2 = months_between(base, e2)
    d2 = demand(p2, "NewDrug CT", "Phase 1")
    stated("project", p2, m2, at(d2, m2, 0.55),
           "Stated at 55% of what this project's own standard asks for - V-34 short.")
    m3 = months_between(base, e3)
    d3 = demand(p3, "Biosimilar CT (Healthy)", "Phase 3")
    stated("project", p3, m3, at(d3, m3, 1.60),
           "Stated at 160% of the standard - V-34 over. The two directions are counted "
           "apart and never netted off.")
    m4 = months_between(base, e4)
    d4 = demand(p4, "Biosimilar CT (Patient)", "Phase 1")
    stated("project", p4, m4, at(d4, m4, 1.00),
           "The project figure - the mother figure the people on it are scaled to.")
    stated("assignment", a_manual, m4, [2.00] * len(m4),
           "Stated 2.00 every month; the project figure scales it, which V-33 reports.")
    m5 = months_between(base, e5)
    stated("assignment", a_gap, m5[:4] + m5[5:], [0.45] * (len(m5) - 1),
           "Every month but one - the gap is deliberate, and V-31 reports it.")
    m6 = months_between(base, e6)
    d6 = demand(p6, "NewDrug CT", "Phase 4")
    stated("project", p6, m6, at(d6, m6, 1.00),
           "The later months have nobody assigned, so they cannot be shared out - V-32.")

    # ====================================================== bulk, for the large set
    #
    # The scenarios above are the point of the file; this is the PORTFOLIO they sit in,
    # so that 50 projects and 50 people is a realistic load rather than twelve special
    # cases padded out.
    #
    # STARTS ARE STAGGERED ACROSS FOUR YEARS, and that is not cosmetic. REQ-CAL-19 makes
    # a project-month its own standard, divided among whoever is on it, so the load a
    # person carries is set by how many projects run AT ONCE, not by how many exist. Fifty
    # projects all starting together would put every person permanently over the ceiling
    # and the file would read as broken. Staggered, about a third overlap at any time.
    if size == "large":
        import collections
        import random
        rnd = random.Random(20260912)          # fixed, so the file is reproducible
        TYPES = [("NewDrug CT", ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]),
                 ("Biosimilar CT (Healthy)", ["Phase 1", "Phase 3"]),
                 ("Biosimilar CT (Patient)", ["Phase 1", "Phase 3"]),
                 ("Others", [None])]
        SCOPES = ["fully in-housed", "fully outsourced",
                  "Partially outsourced (in-house for EDC)"]
        STATUS = ["Active"] * 6 + ["Planned"] * 2 + ["On hold", "Completed"]
        FIRST = ["Nam", "Baek", "Shin", "Koo", "Ryu", "Moon", "Jang", "Hwang", "Cho",
                 "Song", "Yang", "Bae", "Noh", "Gil", "Sun", "Pyo", "Wi", "Ji"]
        LAST = list("ABCDEFGHJKLMNPRSTWY")
        DEPTS = ["Clinical Operations", "Data Management", "Programming",
                 "Biostatistics", "Business Systems"]

        while len(ppl) < 50:
            i = len(ppl) + 1
            nm = f"{FIRST[i % len(FIRST)]} {LAST[i % len(LAST)]}."
            dept = DEPTS[i % len(DEPTS)]
            role = (OROLES if dept == "Business Systems" else ROLES)[i % 3]
            cap = rnd.choice([1.00] * 7 + [0.80, 0.80, 0.60])
            person(f"PSN-{i:03d}", nm, dept, role, cap,
                   "Portfolio staff - not a scenario.")

        load = collections.Counter()
        for a in asg:                       # the scenario assignments already placed
            load[a[1]] += 1
        bulk_n = 50 - len(proj)
        for i in range(bulk_n):
            pid = f"BLK-{i + 1:03d}"
            t, phases = TYPES[i % len(TYPES)]
            phase = phases[i % len(phases)]
            start = date(2025, 1, 1) + rd(months=rnd.randrange(0, 96))
            start = start.replace(day=1)
            if t == "Others":
                spans = [("Planning", rnd.randint(2, 4)), ("Develop", rnd.randint(5, 10)),
                         ("Close", rnd.randint(1, 3))]
            else:
                spans = [("Before-Start-up", rnd.randint(1, 3)),
                         ("Start-up", rnd.randint(3, 5)),
                         ("Conduct (interim)", rnd.randint(4, 9)),
                         ("Close-out (interim)", rnd.randint(1, 3)),
                         ("Conduct (final)", rnd.randint(4, 10)),
                         ("Close-out (final)", rnd.randint(2, 4))]
                if i % 4 == 0:
                    spans.append(("After Close-out (final)", rnd.randint(1, 2)))
            weights = {n: round(rnd.uniform(0.80, 1.30), 2) for n, _ in spans}
            end = project(pid, f"{pid} {t.split()[0]} study", t, phase, start, spans,
                          weights=weights, status=rnd.choice(STATUS),
                          scope=rnd.choice(SCOPES),
                          category=None if t == "Others" else f"Compound {chr(65 + i % 26)}",
                          note="Portfolio project - not a scenario.")
            if t != "Others" and i % 3 == 0:
                milestones(pid, start)

            # EVERY project is staffed from the whole pool, and EVERY person ends up on
            # several projects, which is what the request asked for and what makes the
            # person tab worth looking at.
            roles = OROLES if t == "Others" else ROLES
            pool50 = [f"PSN-{k:03d}" for k in range(6, len(ppl) + 1)]  # 1-5 are scenarios
            for role in roles:
                # The least-loaded person, with a random tie-break so the same few are
                # not always first. Random choice alone put one person on twelve projects
                # and another on one.
                sid = min(sorted(pool50, key=lambda _: rnd.random()),
                          key=lambda x: load[x])
                load[sid] += 1
                part = rnd.random() < 0.18
                assign(aid(), sid, pid, role, round(rnd.uniform(0.20, 0.60), 2),
                       s=start + rd(months=2) if part else None,
                       e=eom(end - rd(months=2)) if part else None,
                       note="Portfolio assignment." if not part
                            else "Portfolio assignment, joining late and leaving early.")
                # A second holder on some roles - the role factor is then divided
                # between them (REQ-CAL-14), so the project's month does not move.
                if rnd.random() < 0.35:
                    sid2 = min(sorted([x for x in pool50 if x != sid],
                                      key=lambda _: rnd.random()),
                               key=lambda x: load[x])
                    load[sid2] += 1
                    assign(aid(), sid2, pid, role, round(rnd.uniform(0.20, 0.50), 2),
                           note="Shares this role with a colleague - the factor is "
                                "divided between them.")

    # ==================================================================== write
    wb = Workbook()
    wb.remove(wb.active)
    list_rows, list_ranges = [], {}
    r = 2
    for name, values in B.LISTS:
        for v in values:
            list_rows.append((name, v, None))
        list_ranges[name] = f"Lists!$B${r}:$B${r + len(values) - 1}"
        r += len(values)

    # `facts` is a list of LINES appended to the standard README body.
    facts = [
        "",
        "WHAT THIS FILE IS",
        f"   A test bed, not a plan. {len(SCENARIOS)} scenarios across {len(proj)} projects and "
        f"{len(ppl)} people.",
        "   Every project is ONE scenario and is named after it; the note on each row says what",
        "   it is for. Nothing here is random and nothing is filler.",
        "",
        f"   {len(proj)} projects | {len(ppl)} people | {len(asg)} assignments | "
        f"{len(ppw)} override windows | {len(est)} stated months",
        "",
        "WHAT IT DELIBERATELY DOES NOT DO",
        "   It does not carry the ERROR-class problems that make the application reject a row -",
        "   an assignment pointing at a project that does not exist, a role with no factor, a",
        "   date that ends before it starts. Those need a file that is broken on purpose, and a",
        "   broken file cannot also be the one you click through to watch the application work.",
        "   The rules reported here are the ones that leave a usable plan behind.",
        "",
        "   The weights and role factors are ILLUSTRATIVE. Replace them before drawing any",
        "   conclusion from the output.",
        "",
        "IF YOU ARE AN AI AGENT READING THIS FILE",
        "   docs/prap_contract.json is the machine-readable contract: every sheet, column,",
        "   value list and validation rule, with the severity each one carries. Read it before",
        "   writing to this workbook - it is what stops a plausible-looking column name being",
        "   silently ignored.",
        "",
        "   To check a file without a browser:",
        "      python tools/verify_source_workbook.py <file.xlsx>     full validation + figures",
        "      python tools/prap_io.py validate <file>                .xlsx or .prap.json",
        "",
        "   Every project note_1 says whether the row is a SCENARIO or portfolio filler, so the",
        "   interesting rows can be found without reading this sheet.",
        "",
        "   The figures are checked by four independent implementations that must agree - the",
        "   browser engine, tools/prap_io.py, tools/verify_source_workbook.py and the reference",
        "   inside tools/test_app.py. If your own arithmetic disagrees with all four, it is",
        "   probably yours; REQ-CAL-19 is the rule most often got wrong (a project-month IS its",
        "   standard, and the people on it DIVIDE it - they do not each add to it).",
        "",
        "WHAT EACH PROJECT IS FOR",
    ]
    for pid, what, look in SCENARIOS:
        facts.append(f"   {pid}  {what}")
        facts.append(f"            Look at: {look}")
        facts.append("")
    B.add_readme(wb, "scenarios", facts)

    B.write_sheet(wb, "Project", proj, None, list_ranges)
    B.write_sheet(wb, "Milestone", mile, None, list_ranges)
    B.write_sheet(wb, "ProjectPeriod", per, None, list_ranges)
    B.write_sheet(wb, "PeriodFTEStandard", pws_rows, None, list_ranges)
    B.write_sheet(wb, "RoleFactor", role_rows, None, list_ranges)
    B.write_sheet(wb, "Person", ppl, None, list_ranges)
    B.write_sheet(wb, "Assignment", asg, None, list_ranges)
    B.write_sheet(wb, "PersonPeriodWeight", ppw, None, list_ranges)
    B.write_sheet(wb, "MonthlyEstimate", est, None, list_ranges)
    B.write_sheet(wb, "Lists", list_rows, None, list_ranges)
    B.write_sheet(wb, "Config", cfg_rows, None, list_ranges)
    out = OUT if size == "small" else LARGE_OUT
    wb.save(out)
    print(f"Written: {out}")
    print(f"  {len(SCENARIOS)} scenarios | {len(proj)} projects | {len(ppl)} people | "
          f"{len(asg)} assignments | {len(ppw)} override windows | {len(est)} stated months")


if __name__ == "__main__":
    import sys
    main("large" if "--large" in sys.argv else "small")
