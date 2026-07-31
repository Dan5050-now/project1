"""Validate a PRAP source workbook against the rules baselined in the plan.

Implements enough of the calculation engine to prove the data is coherent and that
the dummy file demonstrates what its README claims. Doubles as a reference
implementation for the Step 4 calculation layer.

    python tools/verify_source_workbook.py templates/PRAP_SourceData_Dummy_v1.0.xlsx
"""

import calendar
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from openpyxl import load_workbook

CLINICAL_PERIODS = ["Before-Start-up", "Start-up", "Conduct",
                    "Close-out (interim)", "Close-out (final)"]
OTHER_PERIODS = ["Planning", "Develop", "Close"]


def rows(ws):
    hdr = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if all(v is None for v in r):
            continue
        yield dict(zip(hdr, r))


def d(v):
    return v.date() if hasattr(v, "date") else v


def months_between(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def coverage(y, m, s, e):
    days = calendar.monthrange(y, m)[1]
    m0, m1 = date(y, m, 1), date(y, m, days)
    lo, hi = max(m0, s), min(m1, e)
    return 0.0 if hi < lo else ((hi - lo).days + 1) / days


def main(path):
    wb = load_workbook(path, data_only=False)
    P = {r["project_id"]: r for r in rows(wb["Project"])}
    MS = defaultdict(dict)
    for r in rows(wb["Milestone"]):
        MS[r["project_id"]][r["milestone_name"]] = d(r["milestone_date"])
    PER = defaultdict(list)
    for r in rows(wb["ProjectPeriod"]):
        PER[r["project_id"]].append(r)
    RF = {(r["project_type"], r["role_name"]): r["role_factor"] for r in rows(wb["RoleFactor"])}
    PWS = {(r["clinical_phase"], r["period_name"]): r["weight"] for r in rows(wb["PeriodWeightStandard"])}
    PSN = {r["person_id"]: r for r in rows(wb["Person"])}
    ASG = list(rows(wb["Assignment"]))
    PPW = defaultdict(list)
    for r in rows(wb["PersonPeriodWeight"]):
        PPW[r["assignment_id"]].append(r)
    CFG = {r["parameter"]: r["value"] for r in rows(wb["Config"])}
    LISTS = defaultdict(set)
    for r in rows(wb["Lists"]):
        LISTS[r["list_name"]].add(r["value"])

    errors, warnings = [], []

    # ---- referential integrity (V-01, V-02, V-03, V-08) ----
    for a in ASG:
        if a["project_id"] not in P:
            errors.append(f"V-01 {a['assignment_id']}: unknown project {a['project_id']}")
            continue
        if a["person_id"] not in PSN:
            errors.append(f"V-02 {a['assignment_id']}: unknown person {a['person_id']}")
        ptype = P[a["project_id"]]["project_type"]
        if (ptype, a["role_name"]) not in RF:
            errors.append(f"V-03 {a['assignment_id']}: role '{a['role_name']}' not valid for {ptype}")
    ids = [a["assignment_id"] for a in ASG]
    if len(ids) != len(set(ids)):
        errors.append("V-08: duplicate assignment_id")

    # ---- period coverage, ordering, naming (V-06, V-12, V-15, V-18) ----
    for pid, proj in P.items():
        segs = sorted(PER.get(pid, []), key=lambda r: r["period_seq"])
        if not segs:
            errors.append(f"V-12 {pid}: no periods")
            continue
        allowed = CLINICAL_PERIODS if proj["project_type"] == "Clinical Trial" else OTHER_PERIODS
        seqs = [s["period_seq"] for s in segs]
        if len(seqs) != len(set(seqs)):
            errors.append(f"V-18 {pid}: duplicate period_seq")
        prev_end = None
        for s in segs:
            if s["period_name"] not in allowed:
                errors.append(f"V-15 {pid}: '{s['period_name']}' not in the {proj['project_type']} set")
            ps, pe = d(s["period_start"]), d(s["period_end"])
            if pe < ps:
                errors.append(f"V-05 {pid} seq {s['period_seq']}: end before start")
            if prev_end is not None:
                gap = (ps - prev_end).days
                if gap > 1:
                    errors.append(f"V-12 {pid}: {gap - 1}-day GAP before seq {s['period_seq']}")
                elif gap < 1:
                    errors.append(f"V-06 {pid}: OVERLAP at seq {s['period_seq']}")
            prev_end = pe
        pstart, pend = d(proj["start_date"]), d(proj["end_date"])
        if d(segs[0]["period_start"]) > pstart:
            warnings.append(f"V-12 {pid}: periods start after the project does")
        if d(segs[-1]["period_end"]) < pend:
            warnings.append(f"V-12 {pid}: periods end before the project does")

    # ---- weights present (V-19) ----
    for pid, proj in P.items():
        if proj["project_type"] != "Clinical Trial":
            continue
        ph = proj["clinical_phase"]
        if not ph:
            errors.append(f"V-19 {pid}: clinical trial with no clinical_phase")
            continue
        for s in PER.get(pid, []):
            if (ph, s["period_name"]) not in PWS:
                errors.append(f"V-19 {pid}: no standard weight for {ph} / {s['period_name']}")

    # ---- list membership (V-11) ----
    for pid, proj in P.items():
        for col, lname in [("project_type", "project_type"), ("outsourcing_type", "outsourcing_type"),
                           ("status", "project_status")]:
            v = proj.get(col)
            if v and v not in LISTS[lname]:
                warnings.append(f"V-11 {pid}: '{v}' not in list {lname}")
    for pid, mm in MS.items():
        for nm in mm:
            if nm not in LISTS["milestone_name"]:
                warnings.append(f"V-11 {pid}: milestone '{nm}' not in the standard list")

    # ---- monthly simulation ----
    def period_weight(pid, y, m):
        for s in PER.get(pid, []):
            if d(s["period_start"]) <= date(y, m, 1) <= d(s["period_end"]):
                return s["weight"]
        return 1.00

    def person_weight(a, y, m):
        for w in PPW.get(a["assignment_id"], []):
            if d(w["period_start"]) <= date(y, m, 1) <= d(w["period_end"]):
                return w["weight_override"]
        return a["person_weight"]

    load = defaultdict(float)          # (person, y, m) -> FTE
    horizon = set()
    for a in ASG:
        if a["project_id"] not in P or a["person_id"] not in PSN:
            continue
        proj = P[a["project_id"]]
        s = d(a["assign_start_date"])
        e = d(a["assign_end_date"]) or d(proj["end_date"])
        rf = RF[(proj["project_type"], a["role_name"])]
        for y, m in months_between(s, e):
            cov = coverage(y, m, s, e)
            if cov <= 0:
                continue
            v = period_weight(a["project_id"], y, m) * rf * person_weight(a, y, m) * cov
            load[(a["person_id"], y, m)] += v
            horizon.add((y, m))

    over_fte = float(CFG["over_allocation_fte"])
    under_fte = float(CFG["under_allocation_fte"])
    min_months = int(CFG["under_allocation_min_months"])

    over = sorted([(p, y, m, v) for (p, y, m), v in load.items() if v > over_fte],
                  key=lambda t: (t[0], t[1], t[2]))

    runs = []
    for pid_ in sorted(PSN):
        seq = sorted([(y, m) for (p, y, m) in load if p == pid_])
        if not seq:
            continue
        cur = []
        for y, m in months_between(date(*seq[0], 1), date(*seq[-1], 1)):
            v = load.get((pid_, y, m), 0.0)
            if 0 < v < under_fte:
                cur.append((y, m, v))
            else:
                if len(cur) >= min_months:
                    runs.append((pid_, cur[0][:2], len(cur)))
                cur = []
        if len(cur) >= min_months:
            runs.append((pid_, cur[0][:2], len(cur)))

    # ---- report ----
    print(f"File: {Path(path).name}")
    print(f"  projects {len(P)} | people {len(PSN)} | assignments {len(ASG)} | "
          f"periods {sum(len(v) for v in PER.values())} | months spanned {len(horizon)}")
    print()
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e_ in errors:
            print("   ", e_)
    else:
        print("ERRORS: none - referential integrity, period coverage and weights all check out.")
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print("   ", w)
    else:
        print("WARNINGS: none.")

    print(f"\nOVER-ALLOCATION (> {over_fte} FTE): {len(over)} person-months")
    for p, y, m, v in over[:8]:
        print(f"    {p} {y}-{m:02d}  {v:.2f} FTE")
    if len(over) > 8:
        print(f"    ... and {len(over) - 8} more")

    print(f"\nUNDER-ALLOCATION (< {under_fte} FTE for >= {min_months} months): {len(runs)} runs")
    for p, (y, m), n in runs:
        print(f"    {p} from {y}-{m:02d}, {n} months")

    peak = max(load.items(), key=lambda kv: kv[1]) if load else None
    if peak:
        (p, y, m), v = peak
        print(f"\nPeak person-month: {p} {y}-{m:02d} at {v:.2f} FTE "
              f"({v * float(CFG['fte_hours_per_month']):.0f} hours)")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  "templates/PRAP_SourceData_Dummy_v1.0.xlsx"))
