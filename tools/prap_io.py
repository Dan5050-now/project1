"""The bridge between a PRAP source workbook and plain text, for programs and AI agents.

The application reads .xlsx, which is a ZIP of XML. A language model cannot write one,
and most agent runtimes cannot read one without a spreadsheet library. That made every
artifact in this project opaque to anything except a human with Excel. This tool closes
that gap in four commands:

    python tools/prap_io.py to-json  <file.xlsx>       -o <file.prap.json>
    python tools/prap_io.py to-xlsx  <file.prap.json>  -o <file.xlsx>
    python tools/prap_io.py validate <file>            [--json]
    python tools/prap_io.py calculate <file> --by person|project|cell
                                             [--from YYYY-MM --to YYYY-MM] [--flags] [--json]

`validate` and `calculate` implement the same rules and the same formula as
app/PRAP.html, so an agent can check its own draft without a browser.
tools/test_interop.py proves the two agree - finding for finding and figure for figure -
on both worked examples. If they ever stop agreeing, that test fails.

The JSON form is described in docs/prap_contract.json under "interchange_format" and in
docs/PRAP_AI_Agent_Guide.md. It is the whole workbook as row objects keyed by column
name, with dates as yyyy-mm-dd strings.
"""

import argparse
import calendar
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_source_workbook as B                                      # noqa: E402

FORMAT_NAME = "prap-source-data"
FORMAT_VERSION = 1
SHEET_ORDER = list(B.SHEETS.keys())
HEADERS = {s: [c for c, _, _ in cols] for s, cols in B.SHEETS.items()}
DATE_COLS = {s: set(B.DATE_COLS.get(s, [])) for s in SHEET_ORDER}
NUM_COLS = {
    "Project": {"planned_member_count", "total_period_months"},
    "Milestone": {"milestone_seq"},
    "ProjectPeriod": {"period_seq", "weight"},
    "PeriodWeightStandard": {"weight"},
    "RoleFactor": {"role_factor"},
    "Person": {"capacity_fte"},
    "Assignment": {"person_weight"},
    "PersonPeriodWeight": {"weight_override"},
    "Lists": set(), "Config": set(),
}
CLINICAL_TYPES = {"NewDrug CT", "Biosimilar CT"}
CLINICAL_PERIODS = ["Before-Start-up", "Start-up", "Conduct (interim)", "Close-out (interim)",
                    "Conduct (final)", "Close-out (final)", "After Close-out (final)"]
OTHER_PERIODS = ["Planning", "Develop", "Close"]

# V-14's ordering half. Stated as PAIRS, not as one chain, because the ten milestone
# names are not totally ordered in real trials: an INTERIM database lock is precisely the
# one taken while recruitment continues, so it may fall either side of LPI, and a chain
# would report every such trial. Only the pairs below are ordered by definition.
MILESTONE_ORDER = [
    ("Protocol (v1)", "CTA submission"),
    ("CTA submission", "First SIV"),
    ("First SIV", "FPI"),
    ("FPI", "LPI"),
    ("interim DB lock cut-off", "interim DB lock"),
    ("interim DB lock", "final DB lock"),
    ("final DB lock cut-off", "final DB lock"),
    ("CTA submission", "final DB lock"),
]
# The derivation hangs on these three; out of order between them is an error, because the
# periods it computes would be wrong rather than merely surprising.
DERIVATION_MILESTONES = {"CTA submission", "interim DB lock", "final DB lock"}


class Problem(Exception):
    """A file we refuse to read, as opposed to a finding about data we did read."""


# =============================================================== 1. reading
def _as_date(v, where):
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):                     # Excel serial, 1900 leap-year bug
        return date(1899, 12, 30) + timedelta(days=int(round(v)))
    s = str(v).strip()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise Problem(f"{where}: '{s}' is not a date. Write yyyy-mm-dd - an ambiguous "
                      f"format such as 03/04/2026 is never guessed at.")


def _as_num(v):
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _coerce(sheet, rows):
    out = []
    for i, r in enumerate(rows, start=2):
        rec = {}
        for col, v in r.items():
            if isinstance(v, str):
                v = v.strip() or None
            if col in DATE_COLS[sheet]:
                v = _as_date(v, f"{sheet} row {i}, {col}")
            elif col in NUM_COLS[sheet]:
                v = _as_num(v)
            rec[col] = v
        rec["__row"] = i
        out.append(rec)
    return out


def read_xlsx(path):
    """Workbook -> {sheet: [row dict]}. Blank rows are skipped, as the application does."""
    wb = load_workbook(path, data_only=True)
    missing = [s for s in SHEET_ORDER if s not in wb.sheetnames]
    if missing:
        raise Problem(f"{Path(path).name}: sheet(s) not found: {', '.join(missing)}. "
                      f"Compare the file against templates/PRAP_SourceData_Template_"
                      f"v{B.TEMPLATE_VERSION}.xlsx.")
    sheets = {}
    for s in SHEET_ORDER:
        ws = wb[s]
        hdr = [c.value for c in ws[1]]
        rows = []
        for raw in ws.iter_rows(min_row=2, values_only=True):
            if all(v is None or v == "" for v in raw):
                continue
            rows.append({h: v for h, v in zip(hdr, raw) if h})
        sheets[s] = _coerce(s, rows)
    return sheets


def read_json(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("prap_format") != FORMAT_NAME:
        raise Problem(f"{Path(path).name}: not a PRAP interchange file — expected "
                      f'"prap_format": "{FORMAT_NAME}".')
    if doc.get("format_version") != FORMAT_VERSION:
        raise Problem(f"{Path(path).name}: format_version {doc.get('format_version')!r}; "
                      f"this build writes and reads {FORMAT_VERSION}.")
    src = doc.get("sheets") or {}
    missing = [s for s in SHEET_ORDER if s not in src]
    if missing:
        raise Problem(f"{Path(path).name}: sheets missing: {', '.join(missing)}. All "
                      f"{len(SHEET_ORDER)} must be present, even if empty.")
    sheets = {}
    for s in SHEET_ORDER:
        rows = src[s] or []
        for i, r in enumerate(rows, start=1):
            # A column name that is not in the schema is refused rather than ignored: a
            # typo silently dropped is a value the user believes they supplied.
            bad = [k for k in r if k not in HEADERS[s]]
            if bad:
                raise Problem(f"{Path(path).name}: {s} row {i} has unknown column(s) "
                              f"{', '.join(sorted(bad))}. Valid: {', '.join(HEADERS[s])}.")
        sheets[s] = _coerce(s, [dict(r) for r in rows])
    return sheets


def read_any(path):
    p = Path(path)
    if p.suffix.lower() == ".json":
        return read_json(p)
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        return read_xlsx(p)
    raise Problem(f"{p.name}: expected .xlsx or .prap.json.")


# =============================================================== 2. writing
def _plain(v):
    if isinstance(v, datetime):
        v = v.date()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def to_json_doc(sheets):
    out = {}
    for s in SHEET_ORDER:
        rows = []
        for r in sheets[s]:
            rec = {}
            for col in HEADERS[s]:
                v = _plain(r.get(col))
                if v is not None and v != "":
                    rec[col] = v
            rows.append(rec)
        out[s] = rows
    return {
        "prap_format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "schema_version": B.SCHEMA_VERSION,
        "$comment": "PRAP source data as plain text. Load into app/PRAP.html directly, or "
                    "convert with tools/prap_io.py. Dates are yyyy-mm-dd. Column meanings "
                    "and rules: docs/prap_contract.json.",
        "sheets": out,
    }


def write_json(sheets, path):
    Path(path).write_text(json.dumps(to_json_doc(sheets), indent=1, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def write_xlsx(sheets, path):
    """A minimal, unstyled workbook with the schema's sheets and column order.

    Deliberately not the styled template: this is a data carrier, and the application
    reads only the values. Dates are written as real dates so Excel shows them as dates.
    """
    wb = Workbook()
    wb.remove(wb.active)
    for s in SHEET_ORDER:
        ws = wb.create_sheet(s)
        ws.append(HEADERS[s])
        for r in sheets[s]:
            ws.append([r.get(c) for c in HEADERS[s]])
        for col in DATE_COLS[s]:
            i = HEADERS[s].index(col) + 1
            for cell in ws[get_column_letter(i)][1:]:
                cell.number_format = "yyyy-mm-dd"
        ws.freeze_panes = "A2"
    wb.save(path)


# =============================================================== 3. the model
def month_key(y, m):
    return y * 12 + m


def key_label(k):
    return f"{calendar.month_abbr[k % 12 + 1]} {k // 12}"


def key_ym(k):
    return k // 12, k % 12 + 1


def parse_ym(s):
    y, m = s.split("-")
    return month_key(int(y), int(m) - 1)


def months_between(a, b):
    y, m = a.year, a.month
    while (y, m) <= (b.year, b.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def coverage(y, m, s, e):
    days = calendar.monthrange(y, m)[1]
    lo, hi = max(date(y, m, 1), s), min(date(y, m, days), e)
    return 0.0 if hi < lo else ((hi - lo).days + 1) / days


def add_months(d, n):
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def derive_periods(proj, ms):
    """The clinical period derivation, identical to derivePeriods() in the application."""
    get = lambda n: (ms.get(n) or [None])[0]                            # noqa: E731
    protocol, cta = get("Protocol (v1)"), get("CTA submission")
    siv = get("First SIV") or get("FPI")
    idbl = get("interim DB lock")
    fdbl = get("final DB lock") or idbl
    if not cta or not fdbl:
        return None
    start, end = proj["start_date"], proj["end_date"]
    su_s0 = (protocol + timedelta(days=1)) if protocol else add_months(cta, -1)
    su_s = max(su_s0, start)
    su_e = siv if (siv and siv >= su_s) else add_months(su_s, 4) - timedelta(days=1)
    later = [d for d in (ms.get("Inspection") or []) if d > fdbl]
    p7_s = min(later) if later else None
    p7_e = max(max(later), end) if later else None
    cof_s = add_months(fdbl, -3)
    cof_e = (p7_s - timedelta(days=1)) if p7_s else max(fdbl, end)
    segs = []
    if su_s > start:
        segs.append(["Before-Start-up", start, su_s - timedelta(days=1)])
    segs.append(["Start-up", su_s, su_e])
    if idbl and idbl < fdbl:
        coi_s = add_months(idbl, -3)
        segs.append(["Conduct (interim)", su_e + timedelta(days=1), coi_s - timedelta(days=1)])
        segs.append(["Close-out (interim)", coi_s, idbl])
        cof_s = max(cof_s, idbl + timedelta(days=1))
        segs.append(["Conduct (final)", idbl + timedelta(days=1), cof_s - timedelta(days=1)])
    else:
        segs.append(["Conduct (final)", su_e + timedelta(days=1), cof_s - timedelta(days=1)])
    segs.append(["Close-out (final)", cof_s, cof_e])
    if p7_s:
        segs.append(["After Close-out (final)", p7_s, p7_e])
    kept = [s for s in segs if s[2] >= s[1]]
    return [{"period_name": n, "period_seq": i + 1, "period_start": s, "period_end": e,
             "__derived": True} for i, (n, s, e) in enumerate(kept)]


class Model:
    def __init__(self, sheets):
        self.raw = sheets
        self.findings = []
        self.lists = defaultdict(list)
        for r in sheets["Lists"]:
            if r.get("list_name"):
                self.lists[r["list_name"]].append(r.get("value"))
        self.config = {r["parameter"]: r.get("value")
                       for r in sheets["Config"] if r.get("parameter")}
        cfg = lambda k, d: (_as_num(self.config.get(k)) if self.config.get(k) is not None  # noqa
                            else None) or d
        self.OVER = cfg("over_allocation_fte", 1.50)
        self.UNDER = cfg("under_allocation_fte", 0.60)
        self.MINM = int(cfg("under_allocation_min_months", 3))
        self.HOURS = cfg("fte_hours_per_month", 160)

        sv = _as_num(self.config.get("schema_version"))
        if sv is None:
            self.add("warning", "V-09", "Config", "", "No schema_version in Config.")
        elif int(sv) != B.SCHEMA_VERSION:
            self.add("warning", "V-09", "Config", "",
                     f"This file is schema version {int(sv)}; this build expects "
                     f"{B.SCHEMA_VERSION}.")

        self.projects, self.people = {}, {}
        for p in sheets["Project"]:
            if p.get("project_id") in self.projects:
                self.add("error", "V-08", "Project", p["__row"],
                         f"project_id {p['project_id']} appears more than once.")
            self.projects[p.get("project_id")] = p
        for p in sheets["Person"]:
            if p.get("person_id") in self.people:
                self.add("error", "V-08", "Person", p["__row"],
                         f"person_id {p['person_id']} appears more than once.")
            self.people[p.get("person_id")] = p

        self.milestones = defaultdict(lambda: defaultdict(list))
        for m in sheets["Milestone"]:
            if m.get("project_id") and m.get("milestone_name") and m.get("milestone_date"):
                self.milestones[m["project_id"]][m["milestone_name"]].append(m["milestone_date"])
        for pid in self.milestones:
            for n in self.milestones[pid]:
                self.milestones[pid][n].sort()

        self.pws = {(r.get("project_type"), r.get("clinical_phase"), r.get("period_name")):
                    _as_num(r.get("weight")) for r in sheets["PeriodWeightStandard"]}
        self.rf, self.rf_roles = {}, defaultdict(set)
        for r in sheets["RoleFactor"]:
            self.rf[(r.get("project_type"), r.get("clinical_phase"),
                     r.get("period_name"), r.get("role_name"))] = _as_num(r.get("role_factor"))
            self.rf_roles[r.get("project_type")].add(r.get("role_name"))

        self.periods = defaultdict(list)
        for r in sheets["ProjectPeriod"]:
            self.periods[r.get("project_id")].append(r)
        for pid, proj in self.projects.items():
            if pid not in self.periods and proj.get("project_type") in CLINICAL_TYPES:
                got = derive_periods(proj, self.milestones.get(pid, {}))
                if got:
                    for d in got:
                        d["project_id"] = pid
                        d["weight"] = self.pws.get(
                            (proj.get("project_type"), proj.get("clinical_phase"),
                             d["period_name"]), 1.00)
                    self.periods[pid] = got
                else:
                    self.add("error", "V-16", "Project", proj.get("__row", ""),
                             f"Project {pid} has no periods and cannot derive them - it is "
                             f"missing CTA submission or a DB lock.")
        for pid in self.periods:
            self.periods[pid].sort(key=lambda s: (s.get("period_seq") or 0))

        self.ppw = defaultdict(list)
        for w in sheets["PersonPeriodWeight"]:
            self.ppw[w.get("assignment_id")].append(w)
        self.assignments = []
        validate(self)
        recompute_derived(self)

    def add(self, sev, rule, sheet, row, msg):
        self.findings.append({"sev": sev, "rule": rule, "sheet": sheet,
                              "row": row, "msg": msg})


def recompute_derived(M):
    for m in M.raw["Milestone"]:
        master = (M.projects.get(m.get("project_id")) or {}).get("project_name")
        if m.get("project_name") and master and m["project_name"] != master:
            M.add("warning", "V-13", "Milestone", m["__row"],
                  f"Milestone row {m['__row']} records project_name "
                  f"'{m['project_name']}' but {m['project_id']} is '{master}'.")
        m["project_name"] = master
    for a in M.raw["Assignment"]:
        a["person_name"] = (M.people.get(a.get("person_id")) or {}).get("person_name")
    for p in M.raw["Project"]:
        if p.get("start_date") and p.get("end_date"):
            p["total_period_months"] = ((p["end_date"].year - p["start_date"].year) * 12
                                        + p["end_date"].month - p["start_date"].month + 1)


def validate(M):
    for pid, p in M.projects.items():
        is_ct = p.get("project_type") in CLINICAL_TYPES
        if p.get("start_date") and p.get("end_date") and p["end_date"] < p["start_date"]:
            M.add("error", "V-05", "Project", p["__row"],
                  f"Project {pid}: end_date {p['end_date']} is before start_date "
                  f"{p['start_date']}.")
        if is_ct and not p.get("project_category"):
            M.add("warning", "V-04", "Project", p["__row"],
                  f"Project {pid} is a clinical trial with no product category.")
        if is_ct and not p.get("clinical_phase"):
            M.add("error", "V-19", "Project", p["__row"],
                  f"Project {pid} is a clinical trial with no clinical_phase.")
        if is_ct:
            for c in ("EDC_setup", "DataReviewSystem_setup", "RBQM_setup"):
                if p.get(c) is None:
                    M.add("warning", "V-10", "Project", p["__row"],
                          f"Project {pid} has no {c} recorded.")
        for col, lst in (("project_type", "project_type"), ("outsourcing_type", "outsourcing_type"),
                         ("status", "project_status"), ("clinical_phase", "clinical_phase")):
            v = p.get(col)
            if v and M.lists.get(lst) and v not in M.lists[lst]:
                M.add("warning", "V-11", "Project", p["__row"],
                      f"Project {pid}: {col} '{v}' is not a known value.")

    for pid, mm in M.milestones.items():
        for nm, dates in mm.items():
            if M.lists.get("milestone_name") and nm not in M.lists["milestone_name"]:
                M.add("warning", "V-11", "Milestone", "",
                      f"Project {pid}: milestone '{nm}' is not in the standard list.")
            if nm != "Inspection" and len(dates) > 1:
                M.add("warning", "V-20", "Milestone", "",
                      f"Project {pid} records '{nm}' {len(dates)} times.")
        lock = (mm.get("final DB lock") or mm.get("interim DB lock") or [None])[0]
        if lock:
            early = [d for d in mm.get("Inspection", []) if d <= lock]
            if early:
                M.add("information", "V-21", "Milestone", "",
                      f"Project {pid}: {len(early)} Inspection date(s) on or before the "
                      f"final DB lock are treated as markers.")
        # V-14: a milestone outside its project's own window, and boundary milestones
        # out of order. Documented in the plan from v1.0 and reported from app v1.16.
        proj = M.projects.get(pid)
        if proj and proj.get("start_date") and proj.get("end_date"):
            for nm, dates in mm.items():
                for dt in dates:
                    if proj["start_date"] <= dt <= proj["end_date"]:
                        continue
                    # An Inspection after the final DB lock is the one milestone that is
                    # MEANT to sit past the project end: it opens 'After Close-out (final)'
                    # and the derivation extends the timeline to reach it (V-21). Saying
                    # 'outside the window' about that would be wrong, not merely noisy.
                    if nm == "Inspection" and lock and dt > lock:
                        M.add("information", "V-14", "Milestone", "",
                              f"Project {pid}: Inspection on {dt} falls after the project "
                              f"end {proj['end_date']}; the timeline is extended to cover "
                              f"it and 'After Close-out (final)' runs to that date.")
                        continue
                    M.add("warning", "V-14", "Milestone", "",
                          f"Project {pid}: '{nm}' on {dt} falls outside the project window "
                          f"{proj['start_date']}..{proj['end_date']}.")
        for n1, n2 in MILESTONE_ORDER:
            if not (mm.get(n1) and mm.get(n2)):
                continue
            d1, d2 = mm[n1][0], mm[n2][0]
            if d2 >= d1:
                continue
            sev = ("error" if {n1, n2} & DERIVATION_MILESTONES else "warning")
            M.add(sev, "V-14", "Milestone", "",
                  f"Project {pid}: '{n2}' ({d2}) is before '{n1}' ({d1}); the period "
                  f"derivation reads these in order.")

    for pid, proj in M.projects.items():
        segs = M.periods.get(pid)
        if not segs:
            if not any(f["rule"] == "V-16" and pid in f["msg"] for f in M.findings):
                M.add("error", "V-12", "ProjectPeriod", "", f"Project {pid} has no periods.")
            continue
        allowed = CLINICAL_PERIODS if proj.get("project_type") in CLINICAL_TYPES else OTHER_PERIODS
        names = [s.get("period_name") for s in segs]
        for n in set(names):
            if names.count(n) > 1:
                M.add("error", "V-18", "ProjectPeriod", "",
                      f"Project {pid}: period_name '{n}' appears {names.count(n)} times.")
        seqs = [s.get("period_seq") for s in segs]
        if len(set(seqs)) != len(seqs):
            M.add("error", "V-18", "ProjectPeriod", "",
                  f"Project {pid}: period_seq is duplicated.")
        prev_end = None
        for s in segs:
            if s.get("period_name") not in allowed:
                M.add("error", "V-15", "ProjectPeriod", "",
                      f"Project {pid} is type '{proj.get('project_type')}' but has a period "
                      f"named '{s.get('period_name')}'.")
            if s.get("period_end") and s.get("period_start") and s["period_end"] < s["period_start"]:
                M.add("error", "V-05", "ProjectPeriod", "",
                      f"Project {pid} period {s.get('period_seq')}: end before start.")
            if prev_end and s.get("period_start"):
                gap = (s["period_start"] - prev_end).days
                if gap > 1:
                    M.add("warning", "V-12", "ProjectPeriod", "",
                          f"Project {pid}: {gap - 1} day(s) before period "
                          f"{s.get('period_seq')} belong to no period.")
                elif gap < 1:
                    M.add("error", "V-06", "ProjectPeriod", "",
                          f"Project {pid}: periods overlap at {s.get('period_name')}.")
            prev_end = s.get("period_end")
            if (proj.get("project_type") in CLINICAL_TYPES and proj.get("clinical_phase")
                    and (proj["project_type"], proj["clinical_phase"],
                         s.get("period_name")) not in M.pws):
                M.add("error", "V-19", "PeriodWeightStandard", "",
                      f"Project {pid}: no standard weight for {proj['project_type']} / "
                      f"{proj['clinical_phase']} / {s.get('period_name')}.")

    seen = set()
    for a in M.raw["Assignment"]:
        aid = a.get("assignment_id")
        if aid in seen:
            M.add("error", "V-08", "Assignment", a["__row"],
                  f"assignment_id {aid} appears more than once.")
        seen.add(aid)
        proj = M.projects.get(a.get("project_id"))
        if not proj:
            M.add("error", "V-01", "Assignment", a["__row"],
                  f"Assignment {aid} refers to project {a.get('project_id')}, which does "
                  f"not exist.")
            continue
        if a.get("person_id") not in M.people:
            M.add("error", "V-02", "Assignment", a["__row"],
                  f"Assignment {aid} refers to person {a.get('person_id')}, which does "
                  f"not exist.")
        roles = M.rf_roles.get(proj.get("project_type"))
        if not roles or a.get("role_name") not in roles:
            M.add("error", "V-03", "Assignment", a["__row"],
                  f"Assignment {aid}: role '{a.get('role_name')}' is not valid for a "
                  f"project of type '{proj.get('project_type')}'.")
        if (a.get("assign_end_date") and a.get("assign_start_date")
                and a["assign_end_date"] < a["assign_start_date"]):
            M.add("error", "V-05", "Assignment", a["__row"], f"Assignment {aid}: end before start.")
        if proj.get("end_date") and a.get("assign_end_date") and a["assign_end_date"] > proj["end_date"]:
            M.add("warning", "V-07", "Assignment", a["__row"],
                  f"Assignment {aid} runs to {a['assign_end_date']}, after project "
                  f"{a.get('project_id')} ends on {proj['end_date']}.")
        per = M.people.get(a.get("person_id"))
        if per and a.get("person_name") and a["person_name"] != per.get("person_name"):
            M.add("warning", "V-13", "Assignment", a["__row"],
                  f"Assignment {aid} records person_name '{a['person_name']}' but "
                  f"{a.get('person_id')} is '{per.get('person_name')}'.")
        M.assignments.append(a)

    for aid, wins in M.ppw.items():
        if aid not in seen:
            M.add("error", "V-24", "PersonPeriodWeight", "",
                  f"{aid}: PersonPeriodWeight refers to an assignment that does not exist.")
            continue
        wins.sort(key=lambda w: (w.get("period_start") or date.min))
        starts = [w.get("period_start") for w in wins]
        if len(set(starts)) != len(starts):
            M.add("error", "V-24", "PersonPeriodWeight", "",
                  f"{aid}: two override windows share a period_start.")
        for a1, a2 in zip(wins, wins[1:]):
            if (a1.get("period_end") and a2.get("period_start")
                    and a2["period_start"] <= a1["period_end"]):
                M.add("error", "V-06", "PersonPeriodWeight", "",
                      f"{aid}: override windows overlap - {a1['period_start']}.."
                      f"{a1['period_end']} and {a2['period_start']}..{a2['period_end']}.")
        for w in wins:
            if w.get("period_end") and w.get("period_start") and w["period_end"] < w["period_start"]:
                M.add("error", "V-05", "PersonPeriodWeight", "",
                      f"{aid}: override window ends before it starts.")

    for sid, p in M.people.items():
        cap = _as_num(p.get("capacity_fte"))
        if cap is not None and cap < M.UNDER:
            M.add("warning", "V-22", "Person", p["__row"],
                  f"{sid}: capacity {cap:.2f} FTE is below the under-allocation floor of "
                  f"{M.UNDER:.2f}.")

    need = {}
    for a in M.assignments:
        proj = M.projects.get(a.get("project_id"))
        if not proj or a.get("person_id") not in M.people:
            continue
        ph = proj.get("clinical_phase") if proj.get("project_type") in CLINICAL_TYPES else None
        for s in M.periods.get(a.get("project_id"), []):
            k = (proj.get("project_type"), ph, s.get("period_name"), a.get("role_name"))
            need[k] = k
    for k in need:
        if k not in M.rf:
            M.add("error", "V-23", "RoleFactor", "",
                  f"No role factor for {k[0]} / {k[1] or '-'} / {k[2]} / {k[3]}.")


# =============================================================== 4. calculation
def calculate(M):
    proj_month = defaultdict(float)
    pers_month = defaultdict(float)
    cell = defaultdict(float)
    pers_proj = defaultdict(lambda: defaultdict(float))
    lo, hi = None, None

    def period_at(pid, y, m):
        first = date(y, m, 1)
        for s in M.periods.get(pid, []):
            if s.get("period_start") and s.get("period_end") \
                    and s["period_start"] <= first <= s["period_end"]:
                return s
        return None

    def person_weight(a, y, m):
        first = date(y, m, 1)
        for w in M.ppw.get(a.get("assignment_id"), []):
            if w.get("period_start") and w.get("period_end") \
                    and w["period_start"] <= first <= w["period_end"]:
                return _as_num(w.get("weight_override")) or 0.0
        return _as_num(a.get("person_weight")) or 0.0

    for a in M.assignments:
        proj = M.projects.get(a.get("project_id"))
        if not proj or a.get("person_id") not in M.people:
            continue
        s = a.get("assign_start_date")
        e = a.get("assign_end_date") or proj.get("end_date")
        if not s or not e:
            continue
        ph = proj.get("clinical_phase") if proj.get("project_type") in CLINICAL_TYPES else None
        for y, m in months_between(s, e):
            cov = coverage(y, m, s, e)
            if cov <= 0:
                continue
            seg = period_at(a["project_id"], y, m)
            pw = (_as_num(seg.get("weight")) if seg else None)
            pw = 1.0 if pw is None else pw
            rf = M.rf.get((proj.get("project_type"), ph,
                           seg.get("period_name") if seg else None, a.get("role_name")))
            rf = 1.0 if rf is None else rf
            v = pw * rf * person_weight(a, y, m) * cov
            k = month_key(y, m - 1)
            lo = k if lo is None else min(lo, k)
            hi = k if hi is None else max(hi, k)
            proj_month[(a["project_id"], k)] += v
            pers_month[(a["person_id"], k)] += v
            pers_proj[(a["person_id"], k)][a["project_id"]] += v
            cell[(a["project_id"], a["person_id"], a.get("role_name"), k)] += v
    return {"proj_month": proj_month, "pers_month": pers_month, "pers_proj": pers_proj,
            "cell": cell, "lo": lo or 0, "hi": hi or 0}


def flags(M, C):
    """Over-allocated months and under-allocated runs, exactly as the dashboard marks them."""
    out = []
    people = sorted({sid for sid, _ in C["pers_month"]})
    for sid in people:
        run = []
        for k in range(C["lo"], C["hi"] + 1):
            v = C["pers_month"].get((sid, k), 0.0)
            if v > M.OVER:
                out.append({"kind": "over", "person_id": sid, "month": key_label(k),
                            "fte": round(v, 4), "threshold": M.OVER})
            if v < M.UNDER:
                run.append(k)
            else:
                if len(run) >= M.MINM:
                    out.append({"kind": "under_run", "person_id": sid,
                                "from": key_label(run[0]), "to": key_label(run[-1]),
                                "months": len(run), "threshold": M.UNDER})
                run = []
        if len(run) >= M.MINM:
            out.append({"kind": "under_run", "person_id": sid, "from": key_label(run[0]),
                        "to": key_label(run[-1]), "months": len(run), "threshold": M.UNDER})
    return out


# =============================================================== 5. the CLI
def _load(path):
    sheets = read_any(path)
    return sheets, Model(sheets)


def cmd_to_json(args):
    sheets = read_any(args.file)
    out = args.out or str(Path(args.file).with_suffix("")) + ".prap.json"
    write_json(sheets, out)
    print(f"wrote {out}  ({sum(len(v) for v in sheets.values())} rows across "
          f"{len(sheets)} sheets)")


def cmd_to_xlsx(args):
    sheets = read_any(args.file)
    out = args.out or str(Path(args.file).name).replace(".prap.json", "") + ".xlsx"
    write_xlsx(sheets, out)
    print(f"wrote {out}  ({sum(len(v) for v in sheets.values())} rows across "
          f"{len(sheets)} sheets)")


SEV_ORDER = {"fatal": 0, "error": 1, "warning": 2, "information": 3}


def cmd_validate(args):
    _, M = _load(args.file)
    F = sorted(M.findings, key=lambda f: (SEV_ORDER.get(f["sev"], 9), f["rule"]))
    if args.json:
        print(json.dumps({"file": str(args.file), "findings": F,
                          "counts": {s: sum(1 for f in F if f["sev"] == s)
                                     for s in ("fatal", "error", "warning", "information")}},
                         indent=1, ensure_ascii=False))
    else:
        counts = defaultdict(int)
        for f in F:
            counts[f["sev"]] += 1
        for f in F:
            row = f"row {f['row']}" if f["row"] else ""
            print(f"  {f['sev']:<11} {f['rule']}  {f['sheet']:<20} {row:<9} {f['msg']}")
        print()
        by_sev = ", ".join(f"{counts[s]} {s}"
                           for s in ("fatal", "error", "warning", "information") if counts[s])
        print(f"{len(F)} finding(s): {by_sev}" if F else "0 findings — the file is clean.")
    return 1 if any(f["sev"] in ("fatal", "error") for f in F) else 0


def cmd_calculate(args):
    _, M = _load(args.file)
    C = calculate(M)
    lo = parse_ym(args.frm) if args.frm else C["lo"]
    hi = parse_ym(args.to) if args.to else C["hi"]
    months = list(range(lo, hi + 1))
    hours = args.unit == "hours"
    conv = (lambda v: v * M.HOURS) if hours else (lambda v: v)

    if args.by == "cell":
        rowsrc = {}
        for (pid, sid, role, k), v in C["cell"].items():
            rowsrc.setdefault((pid, sid, role), {})[k] = v
        label = ("project_id", "person_id", "role_name")
    else:
        src = C["proj_month"] if args.by == "project" else C["pers_month"]
        rowsrc = {}
        for (i, k), v in src.items():
            rowsrc.setdefault((i,), {})[k] = v
        label = ("project_id",) if args.by == "project" else ("person_id",)

    table = []
    for keys in sorted(rowsrc):
        rec = dict(zip(label, keys))
        rec["months"] = {key_label(k): round(conv(rowsrc[keys].get(k, 0.0)), 4)
                         for k in months if rowsrc[keys].get(k)}
        rec["total"] = round(sum(conv(rowsrc[keys].get(k, 0.0)) for k in months), 4)
        if rec["months"]:
            table.append(rec)

    payload = {"file": str(args.file), "by": args.by, "unit": "hours" if hours else "FTE",
               "from": key_label(lo), "to": key_label(hi), "rows": table}
    if args.flags:
        payload["flags"] = flags(M, C)
        payload["thresholds"] = {"over_allocation_fte": M.OVER,
                                 "under_allocation_fte": M.UNDER,
                                 "under_allocation_min_months": M.MINM}
    if args.json:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
        return 0

    head = "  ".join(label)
    print(f"{args.by} load, {payload['unit']}, {payload['from']} .. {payload['to']}")
    print()
    for rec in table:
        who = "  ".join(str(rec[c]) for c in label)
        print(f"  {who:<52} total {rec['total']:>9.2f}")
        for mk, v in rec["months"].items():
            print(f"      {mk:<10} {v:>8.2f}")
    if args.flags:
        print()
        for f in payload["flags"]:
            if f["kind"] == "over":
                print(f"  OVER   {f['person_id']}  {f['month']}  {f['fte']:.2f} FTE "
                      f"(ceiling {f['threshold']:.2f})")
            else:
                print(f"  UNDER  {f['person_id']}  {f['from']} .. {f['to']} "
                      f"({f['months']} months below {f['threshold']:.2f})")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="prap_io", description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Column meanings, value lists and every validation rule: "
               "docs/prap_contract.json and docs/PRAP_AI_Agent_Guide.md")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("to-json", help="workbook -> PRAP JSON interchange file")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_to_json)

    p = sub.add_parser("to-xlsx", help="PRAP JSON interchange file -> workbook")
    p.add_argument("file")
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_to_xlsx)

    p = sub.add_parser("validate", help="report every validation finding, as the app does")
    p.add_argument("file")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("calculate", help="monthly load, by person, project or cell")
    p.add_argument("file")
    p.add_argument("--by", choices=("person", "project", "cell"), default="person")
    p.add_argument("--from", dest="frm", metavar="YYYY-MM")
    p.add_argument("--to", metavar="YYYY-MM")
    p.add_argument("--unit", choices=("FTE", "hours"), default="FTE")
    p.add_argument("--flags", action="store_true",
                   help="also list over-allocated months and under-allocated runs")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_calculate)

    args = ap.parse_args(argv)
    try:
        return args.fn(args) or 0
    except Problem as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
