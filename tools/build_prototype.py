"""Generate the Step 3 UI prototype - a static, self-contained HTML mock-up.

DESIGN ONLY. There is no parsing, no calculation and no import/export behind this
page: the figures are a snapshot computed here, in Python, and baked into the markup.
The only JavaScript is tab switching. The point is to review layout, components and
information hierarchy before any application code is written (plan sheet 08, task 3.1).

    python tools/build_prototype.py

Output: app/PRAP_Prototype_v0.1.html
"""

import calendar
from collections import defaultdict
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.4.xlsx"
OUT = ROOT / "app" / "PRAP_Prototype_v0.2.html"

APP_VERSION = "prototype v0.2"
SCHEMA_EXPECTED = 3
WIN_FROM, WIN_TO = (2027, 1), (2027, 12)      # the 12 months the mock-up shows

# ---- design tokens (validated: see dataviz palette reference) --------------
CAT_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
CAT_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9"]
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
       "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95"]


def rows(ws):
    hdr = [c.value for c in ws[1]]
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not all(v is None for v in r):
            yield dict(zip(hdr, r))


def d(v):
    return v.date() if hasattr(v, "date") else v


def months(a, b):
    y, m = a
    while (y, m) <= b:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def coverage(y, m, s, e):
    dm = calendar.monthrange(y, m)[1]
    lo, hi = max(date(y, m, 1), s), min(date(y, m, dm), e)
    return 0.0 if hi < lo else ((hi - lo).days + 1) / dm


def esc(t):
    return (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- snapshot
def snapshot():
    wb = load_workbook(DUMMY, data_only=False)
    P = {r["project_id"]: r for r in rows(wb["Project"])}
    PER = defaultdict(list)
    for r in rows(wb["ProjectPeriod"]):
        PER[r["project_id"]].append(r)
    MS = defaultdict(list)
    for r in rows(wb["Milestone"]):
        MS[r["project_id"]].append(r)
    RF = {(r["project_type"], r["role_name"]): r["role_factor"] for r in rows(wb["RoleFactor"])}
    CT = {"NewDrug CT", "Biosimilar CT"}
    TYPE_RANK = {"NewDrug CT": 0, "Biosimilar CT": 1, "Others": 2}
    PSN = {r["person_id"]: r for r in rows(wb["Person"])}
    ASG = list(rows(wb["Assignment"]))
    PPW = defaultdict(list)
    for r in rows(wb["PersonPeriodWeight"]):
        PPW[r["assignment_id"]].append(r)
    CFG = {r["parameter"]: r["value"] for r in rows(wb["Config"])}

    grid = list(months(WIN_FROM, WIN_TO))

    def pweight(pid, y, m):
        for s in PER.get(pid, []):
            if d(s["period_start"]) <= date(y, m, 1) <= d(s["period_end"]):
                return s["weight"]
        return 1.00

    def wweight(a, y, m):
        for w in PPW.get(a["assignment_id"], []):
            if d(w["period_start"]) <= date(y, m, 1) <= d(w["period_end"]):
                return w["weight_override"]
        return a["person_weight"]

    proj_m = defaultdict(float)
    pers_m = defaultdict(float)
    cell_m = defaultdict(float)        # (project, person, role, y, m) -> FTE
    for a in ASG:
        pr = P.get(a["project_id"])
        if not pr or a["person_id"] not in PSN:
            continue
        s, e = d(a["assign_start_date"]), d(a["assign_end_date"]) or d(pr["end_date"])
        rf = RF[(pr["project_type"], a["role_name"])]
        for (y, m) in grid:
            cov = coverage(y, m, s, e)
            if cov <= 0:
                continue
            v = pweight(a["project_id"], y, m) * rf * wweight(a, y, m) * cov
            proj_m[(a["project_id"], y, m)] += v
            pers_m[(a["person_id"], y, m)] += v
            cell_m[(a["project_id"], a["person_id"], a["role_name"], y, m)] += v

    tot = defaultdict(float)
    for (pid, y, m), v in proj_m.items():
        tot[pid] += v
    top = [pid for pid, _ in sorted(tot.items(), key=lambda kv: -kv[1])[:10]]

    return dict(P=P, PER=PER, MS=MS, PSN=PSN, ASG=ASG, PPW=PPW, CFG=CFG, CT=CT,
                TYPE_RANK=TYPE_RANK, grid=grid, proj_m=proj_m, pers_m=pers_m,
                cell_m=cell_m, top=top, tot=tot)


S = snapshot()
GRID = S["grid"]
MLAB = [f"{calendar.month_abbr[m]}<br><span class='yr'>{y}</span>" for y, m in GRID]
OVER = float(S["CFG"]["over_allocation_fte"])
UNDER = float(S["CFG"]["under_allocation_fte"])
HOURS = float(S["CFG"]["fte_hours_per_month"])



CT = None  # set after snapshot


def is_ct(pid):
    return S["P"][pid]["project_type"] in S["CT"]


def prank(pid):
    """Requested order: NewDrug CT, then Biosimilar CT, then Others; earlier first."""
    pr = S["P"][pid]
    return (S["TYPE_RANK"].get(pr["project_type"], 9), d(pr["start_date"]), pid)


def phase_pill(pid):
    pr = S["P"][pid]
    if not is_ct(pid):
        return ''
    n = (pr["clinical_phase"] or "").replace("Phase ", "")
    return f'<span class="ph ph{n}">{esc(pr["clinical_phase"])}</span>'


def type_pill(pid):
    t = S["P"][pid]["project_type"]
    k = {"NewDrug CT": "nd", "Biosimilar CT": "bs"}.get(t, "ot")
    return f'<span class="ty {k}">{esc(t)}</span>'


def _mix(hex_, f):
    """Lighten (f>1) or darken (f<1) a hex colour, staying on its own hue."""
    r, g, b = (int(hex_[i:i + 2], 16) for i in (1, 3, 5))
    if f >= 1:
        t = min(1.0, f - 1.0)
        r, g, b = (int(c + (255 - c) * t) for c in (r, g, b))
    else:
        r, g, b = (int(c * f) for c in (r, g, b))
    return "#%02x%02x%02x" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


# The validated set caps at 8 hues. Per-project colour was asked for explicitly, so
# the palette is EXTENDED systematically: the seven validated hues, each stepped in
# lightness. Beyond the first seven, hue alone no longer separates reliably - the
# tooltip, the legend order and the table below carry identity.
BASE7 = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7"]
STEPS = [1.0, 0.70, 1.30, 0.85, 1.15, 0.55, 1.45, 0.62]


def proj_colour(i):
    return _mix(BASE7[i % 7], STEPS[(i // 7) % len(STEPS)])


def seq_step(v, vmax):
    if v <= 0 or vmax <= 0:
        return None
    i = min(len(SEQ) - 1, int(round((v / vmax) * (len(SEQ) - 1))))
    return i


# ---------------------------------------------------------------- charts
def chart_stacked():
    """Monthly demand, one band per project.

    Bands are ordered by total resource with the LARGEST AT THE BOTTOM, so the
    heaviest projects sit on the baseline where they are easiest to read. Every
    'Others' project is grey; clinical trials take the extended colour set.
    """
    order = sorted(S["P"], key=lambda pid: (-S["tot"].get(pid, 0.0), pid))
    active = [pid for pid in order if S["tot"].get(pid, 0.0) > 0.004]
    colour, ci = {}, 0
    for pid in active:
        if S["P"][pid]["project_type"] == "Others":
            colour[pid] = "var(--other)"
        else:
            colour[pid] = proj_colour(ci)
            ci += 1

    W, H = 1180, 300
    pad_l, pad_b, pad_t = 56, 46, 26
    bw = (W - pad_l - 14) / len(GRID)
    vmax = max(sum(S["proj_m"].get((pid, y, m), 0.0) for pid in active)
               for (y, m) in GRID) or 1
    scale = (H - pad_b - pad_t) / (vmax * 1.08)

    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" style="min-width:{W}px" role="img" '
           f'aria-label="Monthly resource demand, one stacked band per project">']
    out.append(f'<text class="ax" x="{pad_l - 44}" y="{pad_t - 10}">FTE</text>')
    for k in range(5):
        v = vmax * 1.08 * k / 4
        yy = H - pad_b - v * scale
        out.append(f'<line class="grid" x1="{pad_l}" y1="{yy:.1f}" x2="{W - 8}" y2="{yy:.1f}"/>')
        out.append(f'<text class="ax" x="{pad_l - 8}" y="{yy + 3:.1f}" text-anchor="end">{v:.0f}</text>')
    for i, (y, m) in enumerate(GRID):
        x = pad_l + i * bw + 3
        base = H - pad_b
        for pid in active:                       # largest first => lowest in the stack
            v = S["proj_m"].get((pid, y, m), 0.0)
            if v <= 0.004:
                continue
            h = v * scale
            out.append(f'<rect x="{x:.1f}" y="{base - h:.1f}" width="{bw - 8:.1f}" '
                       f'height="{max(0.6, h):.1f}" fill="{colour[pid]}">'
                       f'<title>{esc(S["P"][pid]["project_name"])} '
                       f'({esc(S["P"][pid]["project_type"])}) — '
                       f'{GRID[i][0]}-{GRID[i][1]:02d}: {v:.2f} FTE</title></rect>')
            base -= h
        out.append(f'<text class="ax" x="{x + (bw - 8) / 2:.1f}" y="{H - pad_b + 16}" '
                   f'text-anchor="middle">{calendar.month_abbr[m]}</text>')
    out.append(f'<text class="ax yr" x="{pad_l}" y="{H - pad_b + 30}">{GRID[0][0]}</text>')
    out.append(f'<line class="base" x1="{pad_l}" y1="{H - pad_b}" x2="{W - 8}" y2="{H - pad_b}"/>')
    out.append("</svg>")

    leg = ['<div class="legendbox"><ul class="legend proj">']
    for pid in active:
        leg.append(f'<li><span class="sw" style="background:{colour[pid]}"></span>'
                   f'{esc(S["P"][pid]["project_name"])}'
                   f'<span class="lv">{S["tot"][pid]:.1f}</span></li>')
    leg.append("</ul></div>")
    return "".join(out) + "".join(leg)


def chart_people():
    """One bar per person: mean load over the window, with both thresholds marked."""
    people = sorted(S["PSN"])
    vals = []
    for p in people:
        vs = [S["pers_m"].get((p, y, m), 0.0) for (y, m) in GRID]
        vals.append(sum(vs) / len(vs))
    W, H = 980, 240
    pad_l, pad_b, pad_t = 52, 52, 26
    bw = (W - pad_l - 12) / len(people)
    vmax = max(max(vals), OVER) * 1.15
    scale = (H - pad_b - pad_t) / vmax

    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
           f'aria-label="Mean monthly load per person over the window, against both thresholds">']
    for k in range(4):
        v = vmax * k / 3
        yy = H - pad_b - v * scale
        out.append(f'<line class="grid" x1="{pad_l}" y1="{yy:.1f}" x2="{W - 6}" y2="{yy:.1f}"/>')
        out.append(f'<text class="ax" x="{pad_l - 8}" y="{yy + 3:.1f}" text-anchor="end">{v:.1f}</text>')
    for p, v in zip(people, vals):
        i = people.index(p)
        x = pad_l + i * bw + 3
        h = v * scale
        breach = "over" if v > OVER else ("under" if v < UNDER else "")
        cls = f"bar {breach}" if breach else "bar"
        out.append(f'<rect class="{cls}" x="{x:.1f}" y="{H - pad_b - h:.1f}" '
                   f'width="{bw - 8:.1f}" height="{max(0, h):.1f}" rx="2">'
                   f'<title>{esc(S["PSN"][p]["person_name"])} ({p}) — mean {v:.2f} FTE'
                   f'{" · over ceiling" if breach == "over" else (" · under floor" if breach == "under" else "")}'
                   f'</title></rect>')
        if breach:
            out.append(f'<text class="flag {breach}" x="{x + (bw - 8) / 2:.1f}" '
                       f'y="{H - pad_b - h - 6:.1f}" text-anchor="middle">'
                       f'{"▲" if breach == "over" else "▼"} {v:.2f}</text>')
        out.append(f'<text class="ax rot" x="{x + (bw - 8) / 2:.1f}" y="{H - pad_b + 14}" '
                   f'text-anchor="middle">{p[-3:]}</text>')
    for v, lab, cls in ((OVER, f"over-allocation ceiling {OVER:.2f}", "th-over"),
                        (UNDER, f"under-allocation floor {UNDER:.2f}", "th-under")):
        yy = H - pad_b - v * scale
        out.append(f'<line class="halo" x1="{pad_l}" y1="{yy:.1f}" x2="{W - 6}" y2="{yy:.1f}"/>')
        out.append(f'<line class="{cls}" x1="{pad_l}" y1="{yy:.1f}" x2="{W - 6}" y2="{yy:.1f}"/>')
        out.append(f'<rect class="thbg" x="{pad_l + 2}" y="{yy - 14:.1f}" '
                   f'width="{7.0 * len(lab):.0f}" height="12" rx="2"/>')
        out.append(f'<text class="thlab {cls}" x="{pad_l + 6}" y="{yy - 4:.1f}">{lab}</text>')
    out.append(f'<line class="base" x1="{pad_l}" y1="{H - pad_b}" x2="{W - 6}" y2="{H - pad_b}"/>')
    out.append(f'<text class="ax" x="{pad_l - 44}" y="{pad_t - 2}">FTE</text>')
    out.append(f'<text class="ax" x="{pad_l}" y="{H - 8}">person (PSN-…)</text>')
    out.append("</svg>")
    return "".join(out)


def chart_gantt():
    """Timeline for 12 projects: period bands shaded by weight, milestone markers."""
    pids = S["top"] + [p for p in list(S["P"])[:60] if p not in S["top"]][:5]
    pids = pids[:12]
    lo = min(d(S["P"][p]["start_date"]) for p in pids)
    hi = max(d(S["P"][p]["end_date"]) for p in pids)
    span = (hi - lo).days or 1
    W, rowh, pad_l, pad_t = 980, 26, 150, 26
    H = pad_t + rowh * len(pids) + 30
    wmax = max((s["weight"] or 0) for p in pids for s in S["PER"][p]) or 1

    out = [f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
           f'aria-label="Project timeline: period bands shaded by weight, with milestone markers">']
    yr = lo.year
    while yr <= hi.year:
        x = pad_l + (date(yr, 1, 1) - lo).days / span * (W - pad_l - 14)
        if x >= pad_l:
            out.append(f'<line class="grid" x1="{x:.1f}" y1="{pad_t - 8}" x2="{x:.1f}" y2="{H - 22}"/>')
            out.append(f'<text class="ax" x="{x:.1f}" y="{pad_t - 12}" text-anchor="middle">{yr}</text>')
        yr += 1
    for i, p in enumerate(pids):
        y = pad_t + i * rowh
        out.append(f'<text class="rowlab" x="{pad_l - 10}" y="{y + 15}" text-anchor="end">'
                   f'{esc(S["P"][p]["project_name"][:22])}</text>')
        for s in sorted(S["PER"][p], key=lambda r: r["period_seq"]):
            x0 = pad_l + (d(s["period_start"]) - lo).days / span * (W - pad_l - 14)
            x1 = pad_l + (d(s["period_end"]) - lo).days / span * (W - pad_l - 14)
            step = SEQ[3 + min(7, int((s["weight"] / wmax) * 7))]
            out.append(f'<rect x="{x0:.1f}" y="{y + 4}" width="{max(1.5, x1 - x0 - 2):.1f}" '
                       f'height="{rowh - 10}" fill="{step}" rx="2">'
                       f'<title>{esc(s["period_name"])} · weight {s["weight"]:.2f} · '
                       f'{d(s["period_start"])} to {d(s["period_end"])}</title></rect>')
        for ms in S["MS"][p]:
            x = pad_l + (d(ms["milestone_date"]) - lo).days / span * (W - pad_l - 14)
            cls = "ms insp" if ms["milestone_name"] == "Inspection" else "ms"
            out.append(f'<circle class="{cls}" cx="{x:.1f}" cy="{y + rowh / 2 - 1:.1f}" r="3.2">'
                       f'<title>{esc(ms["milestone_name"])} · {d(ms["milestone_date"])}</title></circle>')
    out.append("</svg>")
    leg = ('<ul class="legend"><li><span class="sw ramp"></span>period weight, light = lower</li>'
           '<li><span class="sw dot"></span>milestone</li>'
           '<li><span class="sw dot insp"></span>inspection</li></ul>')
    return "".join(out) + leg


# ---------------------------------------------------------------- tables
def _cells(get, vmax=None, flag=False):
    tds, tot = [], 0.0
    for (y, m) in GRID:
        v = get(y, m)
        tot += v
        if flag and v > OVER:
            tds.append(f'<td class="c over">&#9650; {v:.2f}</td>')
        elif flag and 0 < v < UNDER:
            tds.append(f'<td class="c under">&#9660; {v:.2f}</td>')
        elif v > 0.004:
            i = seq_step(v, vmax) if vmax else None
            tds.append(f'<td class="c c{i}">{v:.2f}</td>' if i is not None
                       else f'<td class="c">{v:.2f}</td>')
        else:
            tds.append('<td class="c z">&middot;</td>')
    return tds, tot


def table_projects():
    """Sorted NewDrug CT, Biosimilar CT, Others; earlier project first.

    Clicking a project name expands it to the people and roles on it.
    """
    # The requested order puts all 34 NewDrug CT projects first, so a flat top-14
    # would never reach the other two types and the ordering could not be seen
    # working. The mock-up therefore samples the head of each type, in order, with
    # a marker row where rows are skipped. The real table lists all 62.
    ordered = sorted([p for p in S["P"] if S["tot"].get(p, 0.0) > 0.004], key=prank)
    listed, breaks, per_type = [], {}, {"NewDrug CT": 6, "Biosimilar CT": 4, "Others": 3}
    seen = {k: 0 for k in per_type}
    for pid in ordered:
        t = S["P"][pid]["project_type"]
        if seen[t] < per_type[t]:
            listed.append(pid)
        seen[t] += 1
    for t, n in per_type.items():
        skipped = seen[t] - n
        if skipped > 0:
            last = [q for q in listed if S["P"][q]["project_type"] == t][-1]
            breaks[last] = (t, skipped)
    vmax = max([S["proj_m"].get((p, y, m), 0.0) for p in listed for (y, m) in GRID] or [1])
    head = "".join(f"<th>{lab}</th>" for lab in MLAB)
    body = []
    for pid in listed:
        tds, tot = _cells(lambda y, m, p=pid: S["proj_m"].get((p, y, m), 0.0), vmax)
        body.append(
            f'<tr class="parent" data-k="p-{pid}" tabindex="0" role="button" '
            f'aria-expanded="false"><th class="rh"><span class="exp">&#9656;</span>'
            f'<span class="nm">{esc(S["P"][pid]["project_name"])}</span> '
            f'{type_pill(pid)}{phase_pill(pid)}'
            f'<span class="sub">{pid} &middot; starts {d(S["P"][pid]["start_date"])}</span></th>'
            f'{"".join(tds)}<td class="tot">{tot:.1f}</td></tr>')
        det = sorted([a for a in S["ASG"] if a["project_id"] == pid],
                     key=lambda a: (a["role_name"], a["person_id"]))
        for a in det:
            k = (pid, a["person_id"], a["role_name"])
            if not any(S["cell_m"].get(k + (y, m), 0.0) > 0.004 for (y, m) in GRID):
                continue
            dtds, dtot = _cells(lambda y, m, kk=k: S["cell_m"].get(kk + (y, m), 0.0))
            body.append(
                f'<tr class="child c-p-{pid}" hidden><th class="rh sub2">'
                f'&#8627; {esc(S["PSN"][a["person_id"]]["person_name"])}'
                f'<span class="role">{esc(a["role_name"])}</span></th>'
                f'{"".join(dtds)}<td class="tot">{dtot:.1f}</td></tr>')
        if pid in breaks:
            t, n = breaks[pid]
            body.append(f'<tr class="skip"><th class="rh">&hellip; {n} more {esc(t)} '
                        f'project{"s" if n != 1 else ""} in this position</th>'
                        f'<td class="c" colspan="{len(GRID) + 1}"></td></tr>')
    rest = [p for p in S["P"] if p not in listed]
    ocells, _ = _cells(lambda y, m: sum(S["proj_m"].get((p, y, m), 0.0) for p in rest))
    ocells = [c.replace('class="c c', 'class="c agg c').replace('class="c"', 'class="c agg"')
              for c in ocells]
    otot = sum(S["tot"].get(p, 0.0) for p in rest)
    body.append(f'<tr class="other"><th class="rh">Other <span class="sub">'
                f'{len(rest)} projects</span></th>{"".join(ocells)}'
                f'<td class="tot">{otot:.1f}</td></tr>')
    tcells, gtot = _cells(lambda y, m: sum(S["proj_m"].get((p, y, m), 0.0) for p in S["P"]))
    body.append(f'<tr class="grand"><th class="rh">All projects</th>'
                f'{"".join(t.replace(chr(34) + "c z" + chr(34), chr(34) + "z" + chr(34)) for t in tcells)}'
                f'<td class="tot">{gtot:.1f}</td></tr>')
    return (f'<table class="grid-t"><thead><tr><th class="rh">Project</th>{head}'
            f'<th class="tot">Total</th></tr></thead><tbody>{"".join(body)}</tbody></table>')


def table_people():
    """Clicking a person expands to their projects and roles.

    The detail rows carry the same order as the project table: NewDrug CT,
    Biosimilar CT, Others, then earlier project first.
    """
    head = "".join(f"<th>{lab}</th>" for lab in MLAB)
    body = []
    for sid in sorted(S["PSN"]):
        tds, tot = _cells(lambda y, m, p=sid: S["pers_m"].get((p, y, m), 0.0), flag=True)
        cap = S["PSN"][sid].get("capacity_fte") or 1.0
        pt = ' <span class="pt">part-time</span>' if cap < 1 else ""
        body.append(
            f'<tr class="parent" data-k="s-{sid}" tabindex="0" role="button" '
            f'aria-expanded="false"><th class="rh"><span class="exp">&#9656;</span>'
            f'<span class="nm">{esc(S["PSN"][sid]["person_name"])}</span>{pt}'
            f'<span class="sub">{sid} &middot; {cap:.2f} FTE &middot; '
            f'{esc(S["PSN"][sid]["department"])}</span></th>'
            f'{"".join(tds)}<td class="tot">{tot / len(GRID):.2f}</td></tr>')
        det = sorted([a for a in S["ASG"] if a["person_id"] == sid],
                     key=lambda a: prank(a["project_id"]))
        for a in det:
            k = (a["project_id"], sid, a["role_name"])
            if not any(S["cell_m"].get(k + (y, m), 0.0) > 0.004 for (y, m) in GRID):
                continue
            dtds, dtot = _cells(lambda y, m, kk=k: S["cell_m"].get(kk + (y, m), 0.0))
            body.append(
                f'<tr class="child c-s-{sid}" hidden><th class="rh sub2">'
                f'&#8627; {esc(S["P"][a["project_id"]]["project_name"])} '
                f'{type_pill(a["project_id"])}{phase_pill(a["project_id"])}'
                f'<span class="role">{esc(a["role_name"])}</span></th>'
                f'{"".join(dtds)}<td class="tot">{dtot / len(GRID):.2f}</td></tr>')
    return (f'<table class="grid-t"><thead><tr><th class="rh">Person</th>{head}'
            f'<th class="tot">Mean</th></tr></thead><tbody>{"".join(body)}</tbody></table>')


# ---------------------------------------------------------------- tiles
def tiles():
    over = sum(1 for (p, y, m), v in S["pers_m"].items() if v > OVER)
    under = sum(1 for (p, y, m), v in S["pers_m"].items() if 0 < v < UNDER)
    total = sum(S["proj_m"].values())
    active = len({p for (p, y, m) in S["proj_m"]})
    ppl = len({p for (p, y, m) in S["pers_m"]})
    items = [("Projects active in window", f"{active}", "of 62 in the file", ""),
             ("People assigned", f"{ppl}", "of 20 in the file", ""),
             ("Total demand", f"{total:,.0f}", f"FTE-months · {total * HOURS:,.0f} hours", ""),
             ("Over-allocated", f"{over}", "person-months above the ceiling", "over"),
             ("Under-allocated", f"{under}", "person-months below the floor", "under")]
    out = ['<div class="tiles">']
    for lab, val, sub, cls in items:
        icon = "▲ " if cls == "over" else ("▼ " if cls == "under" else "")
        out.append(f'<div class="tile {cls}"><div class="tl">{lab}</div>'
                   f'<div class="tv">{icon}{val}</div><div class="ts">{sub}</div></div>')
    out.append("</div>")
    return "".join(out)


# ---------------------------------------------------------------- source tabs
def project_tab():
    pid = S["top"][0]
    pr = S["P"][pid]
    cols = ["project_id", "project_name", "project_type", "project_category", "clinical_phase",
            "outsourcing_type", "EDC_setup", "EDC_system", "planned_member_count",
            "start_date", "end_date", "status"]
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = []
    for qid in S["top"][:9]:
        q = S["P"][qid]
        sel = ' class="sel"' if qid == pid else ""
        tds = "".join(f'<td contenteditable="false">{esc(d(q[c]) if "date" in c else (q[c] or "—"))}</td>'
                      for c in cols)
        body.append(f"<tr{sel}>{tds}</tr>")
    tbl = (f'<div class="scrollx"><table class="data-t"><thead><tr>{head}</tr></thead>'
           f'<tbody>{"".join(body)}</tbody></table></div>')

    mrows = "".join(
        f'<tr><td>{esc(m["milestone_name"])}</td><td>{d(m["milestone_date"])}</td>'
        f'<td>{m["milestone_seq"]}</td><td class="muted">{esc(m.get("note_1") or "—")}</td></tr>'
        for m in sorted(S["MS"][pid], key=lambda r: d(r["milestone_date"])))
    prows = "".join(
        f'<tr><td>{p["period_seq"]}</td><td>{esc(p["period_name"])}</td>'
        f'<td>{d(p["period_start"])}</td><td>{d(p["period_end"])}</td>'
        f'<td>{p["weight"]:.2f}</td><td class="muted">{esc(p.get("note_1") or "—")}</td></tr>'
        for p in sorted(S["PER"][pid], key=lambda r: r["period_seq"]))
    return tbl, mrows, prows, pr, pid


def person_tab():
    pid = "PSN-001"
    per = S["PSN"][pid]
    cols = ["person_id", "person_name", "department", "primary_role", "capacity_fte"]
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = []
    for qid, q in list(S["PSN"].items())[:9]:
        sel = ' class="sel"' if qid == pid else ""
        body.append(f"<tr{sel}>" + "".join(f"<td>{esc(q[c] if q[c] is not None else '—')}</td>"
                                           for c in cols) + "</tr>")
    tbl = (f'<div class="scrollx"><table class="data-t"><thead><tr>{head}</tr></thead>'
           f'<tbody>{"".join(body)}</tbody></table></div>')
    arows = "".join(
        f'<tr><td>{esc(a["assignment_id"])}</td>'
        f'<td>{esc(S["P"][a["project_id"]]["project_name"])}</td>'
        f'<td>{esc(a["role_name"])}</td><td>{d(a["assign_start_date"])}</td>'
        f'<td>{d(a["assign_end_date"])}</td><td>{a["person_weight"]:.2f}</td></tr>'
        for a in S["ASG"] if a["person_id"] == pid)
    orows = "".join(
        f'<tr><td>{esc(k)}</td><td>{d(w["period_start"])}</td><td>{d(w["period_end"])}</td>'
        f'<td>{w["weight_override"]:.2f}</td><td class="muted">{esc(w["reason"])}</td></tr>'
        for k, ws_ in S["PPW"].items() for w in ws_)

    vals = [S["pers_m"].get((pid, y, m), 0.0) for (y, m) in GRID]
    W, H, padl = 640, 116, 30
    vmax = max(max(vals), OVER) * 1.15
    bw = (W - padl) / len(vals)
    base, top = H - 18, 12
    strip = [f'<svg viewBox="0 0 {W} {H}" class="strip" role="img" '
             f'aria-label="Monthly load for the selected person against both thresholds">']
    for i, v in enumerate(vals):
        h = (v / vmax) * (base - top)
        breach = "over" if v > OVER else ("under" if 0 < v < UNDER else "")
        strip.append(f'<rect class="bar {breach}" x="{padl + i * bw + 2:.1f}" y="{base - h:.1f}" '
                     f'width="{bw - 4:.1f}" height="{max(0, h):.1f}" rx="2">'
                     f'<title>{GRID[i][0]}-{GRID[i][1]:02d}: {v:.2f} FTE</title></rect>')
        strip.append(f'<text class="ax tiny" x="{padl + i * bw + bw / 2:.1f}" y="{H - 5}" '
                     f'text-anchor="middle">{calendar.month_abbr[GRID[i][1]][0]}</text>')
    # thresholds drawn last, so they read over the bars rather than behind them
    for v, cls, lab in ((OVER, "th-over", f"{OVER:.2f}"), (UNDER, "th-under", f"{UNDER:.2f}")):
        y = base - (v / vmax) * (base - top)
        strip.append(f'<line class="halo" x1="{padl}" y1="{y:.1f}" x2="{W - 4}" y2="{y:.1f}"/>')
        strip.append(f'<line class="{cls}" x1="{padl}" y1="{y:.1f}" x2="{W - 4}" y2="{y:.1f}"/>')
        strip.append(f'<text class="thlab {cls}" x="{padl - 5}" y="{y + 3:.1f}" '
                     f'text-anchor="end">{lab}</text>')
    strip.append(f'<line class="base" x1="{padl}" y1="{base}" x2="{W - 4}" y2="{base}"/>')
    strip.append("</svg>")
    return tbl, arows, orows, per, pid, "".join(strip)


PTBL, MROWS, PROWS, PROJ, PPID = project_tab()
STBL, AROWS, OROWS, PERS, SPID, STRIP = person_tab()

# ---------------------------------------------------------------- page
CSS = """
:root{color-scheme:light dark;
 --page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;
 --grid:#e1e0d9;--base:#c3c2b7;--ring:rgba(11,11,11,.10);
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#4a3aa7;
 --other:#b8b7b0;
 --good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;
 --overbg:#fbe9e9;--underbg:#fdf3dd;--underink:#8a6100;--accent:#2a78d6;}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
 --page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;--muted:#898781;
 --grid:#2c2c2a;--base:#383835;--ring:rgba(255,255,255,.10);
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;
 --other:#5a5a55;--overbg:#3a1e1e;--underbg:#33290f;--underink:#fab219;--accent:#3987e5;}
 :root:where(:not([data-theme=light])) .ty.nd{background:#16283f;color:#8fbdf0}
 :root:where(:not([data-theme=light])) .ty.bs{background:#12302a;color:#6fcfae}
 :root:where(:not([data-theme=light])) .ph1{background:#3a2712;color:#f0b46a}
 :root:where(:not([data-theme=light])) .ph2{background:#12302a;color:#6fcfae}
 :root:where(:not([data-theme=light])) .ph3{background:#16283f;color:#8fbdf0}
 :root:where(:not([data-theme=light])) .ph4{background:#241f3d;color:#b3a6f2}}
:root[data-theme=dark]{--page:#0d0d0d;--surface:#1a1a19;--ink:#fff;--ink2:#c3c2b7;
 --grid:#2c2c2a;--base:#383835;--ring:rgba(255,255,255,.10);
 --s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;
 --other:#5a5a55;--overbg:#3a1e1e;--underbg:#33290f;--underink:#fab219;--accent:#3987e5;}
:root[data-theme=dark] .ty.nd{background:#16283f;color:#8fbdf0}
:root[data-theme=dark] .ty.bs{background:#12302a;color:#6fcfae}
:root[data-theme=dark] .ph1{background:#3a2712;color:#f0b46a}
:root[data-theme=dark] .ph2{background:#12302a;color:#6fcfae}
:root[data-theme=dark] .ph3{background:#16283f;color:#8fbdf0}
:root[data-theme=dark] .ph4{background:#241f3d;color:#b3a6f2}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);
 font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;}
.wrap{max-width:1120px;margin:0 auto;padding:0 16px 56px}
.proto{background:var(--warn);color:#0b0b0b;text-align:center;padding:6px 12px;
 font-size:12px;font-weight:600;letter-spacing:.02em}
header{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;
 padding:16px 0 10px;border-bottom:1px solid var(--ring)}
h1{font-size:17px;margin:0;font-weight:650}
.vers{color:var(--muted);font-size:12px}
.file{margin-left:auto;color:var(--ink2);font-size:12px}
.btn{border:1px solid var(--ring);background:var(--surface);color:var(--ink);
 border-radius:6px;padding:5px 11px;font-size:12.5px;cursor:default}
.btn.primary{background:var(--accent);color:#fff;border-color:transparent}
.banner{display:flex;gap:10px;align-items:center;margin:12px 0;padding:9px 12px;
 border-radius:8px;background:var(--underbg);border:1px solid var(--ring);font-size:13px}
.banner .lk{margin-left:auto;color:var(--accent);text-decoration:underline}
.dirty{display:flex;gap:8px;align-items:center;margin:10px 0;font-size:13px;color:var(--ink2)}
.dot-w{width:8px;height:8px;border-radius:50%;background:var(--warn);display:inline-block}
nav{display:flex;gap:2px;margin:14px 0 0;border-bottom:1px solid var(--ring)}
nav button{border:0;background:none;color:var(--ink2);padding:9px 15px;font-size:13.5px;
 cursor:pointer;border-bottom:2px solid transparent;font-family:inherit}
nav button[aria-selected=true]{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
section[hidden]{display:none}
.panel{background:var(--surface);border:1px solid var(--ring);border-radius:10px;
 padding:14px 16px;margin:16px 0}
.panel h2{font-size:13px;margin:0 0 3px;font-weight:650;letter-spacing:.01em}
.panel p.cap{margin:0 0 12px;color:var(--muted);font-size:12px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end}
.ctl label{display:block;font-size:11px;color:var(--muted);margin-bottom:3px}
.ctl select,.ctl input{font:inherit;font-size:12.5px;padding:5px 8px;border-radius:6px;
 border:1px solid var(--ring);background:var(--surface);color:var(--ink)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:10px;margin:16px 0}
.tile{background:var(--surface);border:1px solid var(--ring);border-radius:10px;padding:12px 14px}
.tile.over{background:var(--overbg)}.tile.under{background:var(--underbg)}
.tl{font-size:11.5px;color:var(--ink2)}
.tv{font-size:25px;font-weight:600;line-height:1.25;font-variant-numeric:tabular-nums}
.tile.over .tv{color:var(--crit)}.tile.under .tv{color:var(--underink)}
.ts{font-size:11px;color:var(--muted)}
.chart{width:100%;height:auto;display:block}
.strip{width:100%;max-width:640px;height:auto}
.grid{stroke:var(--grid);stroke-width:1}
.base{stroke:var(--base);stroke-width:1}
.ax{fill:var(--muted);font-size:10px}
.ax.tiny{font-size:8px}.ax.yr{font-size:9px}
.rowlab{fill:var(--ink2);font-size:11px}
.bar{fill:var(--s1)}.bar.over{fill:var(--crit)}.bar.under{fill:var(--warn)}
.flag{font-size:9.5px;font-weight:600}
.flag.over{fill:var(--crit)}.flag.under{fill:var(--underink)}
.halo{stroke:var(--surface);stroke-width:4;opacity:.9}
.th-over{stroke:var(--crit);stroke-width:1.5;stroke-dasharray:5 3}
.th-under{stroke:var(--warn);stroke-width:1.5;stroke-dasharray:5 3}
.thlab{font-size:9.5px;font-weight:600}
.thbg{fill:var(--surface);opacity:.85}.thlab.th-over{fill:var(--crit);stroke:none}
.thlab.th-under{fill:var(--underink);stroke:none}
.ms{fill:var(--ink2)}.ms.insp{fill:var(--s2)}
.legend{list-style:none;display:flex;flex-wrap:wrap;gap:6px 16px;margin:8px 0 0;padding:0;
 font-size:11.5px;color:var(--ink2)}
.legend .sw{width:11px;height:11px;border-radius:2px;display:inline-block;
 margin-right:6px;vertical-align:-1px}
.legend .sw.ramp{background:linear-gradient(90deg,#86b6ef,#184f95);width:34px}
.legend .sw.dot{border-radius:50%;background:var(--ink2);width:9px;height:9px}
.legend .sw.dot.insp{background:var(--s2)}
.scrollx{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:12px}
.grid-t th,.grid-t td{border:1px solid var(--grid);padding:4px 7px;text-align:right;
 font-variant-numeric:tabular-nums;white-space:nowrap}
.grid-t thead th{background:var(--page);color:var(--ink2);font-weight:600;font-size:10.5px;
 text-align:center;line-height:1.25}
.grid-t th.rh{text-align:left;font-weight:500;min-width:200px;position:sticky;left:0;
 background:var(--surface);z-index:1}
.grid-t thead th.rh{background:var(--page)}
.rh .sub{display:block;color:var(--muted);font-size:10px}
.rh .exp{color:var(--muted);margin-right:3px}
.pt{font-size:10px;color:var(--ink2);border:1px solid var(--ring);border-radius:9px;padding:0 5px}
td.c{min-width:52px}
td.z{color:var(--muted)}
td.over{background:var(--overbg);color:var(--crit);font-weight:600}
td.under{background:var(--underbg);color:var(--underink);font-weight:600}
tr.other td,tr.other th{color:var(--ink2)}
td.agg{background:var(--page);color:var(--ink2)}
tr.grand th,tr.grand td{border-top:2px solid var(--base);font-weight:650;background:var(--page)}
.tot{font-weight:600}
.data-t th,.data-t td{border:1px solid var(--grid);padding:5px 8px;text-align:left;white-space:nowrap}
.data-t thead th{background:var(--page);color:var(--ink2);font-weight:600;font-size:10.5px}
.data-t tr.sel td{background:color-mix(in srgb,var(--accent) 11%,transparent)}
.muted{color:var(--muted)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){.two{grid-template-columns:1fr}}
.note{font-size:11.5px;color:var(--muted);margin-top:9px}
.filterbar{background:var(--surface);border-color:var(--accent)}
.filterbar .scope{font-weight:400;font-size:11px;color:var(--muted);
 border:1px solid var(--ring);border-radius:9px;padding:1px 7px;margin-left:6px}
.btn.reset{border-color:var(--accent);color:var(--accent)}
.scrollx>.chart,.scrollx>.strip{display:block}
.legendbox{max-height:118px;overflow-y:auto;margin-top:8px;padding-right:6px;
 border-top:1px solid var(--ring)}
.legend.proj{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));
 gap:2px 14px;margin:8px 0 2px}
.legend.proj li{display:flex;align-items:center;gap:0}
.legend .lv{margin-left:auto;color:var(--muted);font-variant-numeric:tabular-nums;
 font-size:10.5px;padding-left:8px}
.ty{font-size:9.5px;border-radius:9px;padding:1px 6px;margin-left:6px;
 border:1px solid var(--ring);white-space:nowrap}
.ty.nd{background:#e7f0fb;color:#184f95}.ty.bs{background:#eaf7f1;color:#0d6b4a}
.ty.ot{background:var(--page);color:var(--ink2)}
.ph{font-size:9.5px;border-radius:9px;padding:1px 6px;margin-left:4px;font-weight:600;
 white-space:nowrap}
.ph1{color:#8a4b00;background:#fdf0e3}.ph2{color:#0d6b4a;background:#eaf7f1}
.ph3{color:#184f95;background:#e7f0fb}.ph4{color:#5b3ea8;background:#efeafb}
tr.parent{cursor:pointer}
tr.parent:hover th.rh{background:color-mix(in srgb,var(--accent) 8%,var(--surface))}
tr.parent .nm{font-weight:600}
tr.parent[aria-expanded=true] .exp{transform:rotate(90deg);display:inline-block}
tr.child th.rh.sub2{font-weight:400;padding-left:20px;color:var(--ink2);font-size:11.5px}
tr.child .role{color:var(--muted);font-size:10.5px;margin-left:6px}
tr.child td{background:color-mix(in srgb,var(--accent) 4%,var(--surface))}
tr.skip th,tr.skip td{background:var(--page);color:var(--muted);font-style:italic;
 font-size:11px;font-weight:400}
:root{--h0:#cde2fb;--h1:#b7d3f6;--h2:#9ec5f4;--h3:#86b6ef;--h4:#6da7ec;--h5:#5598e7;
 --h6:#3987e5;--h7:#2a78d6;--h8:#256abf;--h9:#1c5cab;--h10:#184f95;--hink:#0b0b0b;--hink2:#fff;}

@media(prefers-color-scheme:dark){:root:where(:not([data-theme=light])){
 --h0:#16233a;--h1:#182b48;--h2:#1a3355;--h3:#1c3c64;--h4:#1e4573;--h5:#215083;
 --h6:#245c98;--h7:#2a6cb4;--h8:#3180d4;--h9:#4a92e2;--h10:#6da7ec;--hink:#fff;--hink2:#fff;}}
:root[data-theme=dark]{
 --h0:#16233a;--h1:#182b48;--h2:#1a3355;--h3:#1c3c64;--h4:#1e4573;--h5:#215083;
 --h6:#245c98;--h7:#2a6cb4;--h8:#3180d4;--h9:#4a92e2;--h10:#6da7ec;--hink:#fff;--hink2:#0b0b0b;}

.c0{background:var(--h0)}.c1{background:var(--h1)}.c2{background:var(--h2)}
.c3{background:var(--h3)}.c4{background:var(--h4)}.c5{background:var(--h5)}
.c0,.c1,.c2,.c3,.c4,.c5{color:var(--hink)}
.c6{background:var(--h6)}.c7{background:var(--h7)}.c8{background:var(--h8)}
.c9{background:var(--h9)}.c10{background:var(--h10)}
.c6,.c7,.c8{color:#fff}.c9,.c10{color:var(--hink2)}
"""

JS = """
document.querySelectorAll('tr.parent').forEach(function(tr){
  function toggle(){
    var open = tr.getAttribute('aria-expanded') === 'true';
    tr.setAttribute('aria-expanded', open ? 'false' : 'true');
    document.querySelectorAll('tr.c-' + tr.dataset.k).forEach(function(c){ c.hidden = open; });
  }
  tr.addEventListener('click', toggle);
  tr.addEventListener('keydown', function(e){
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
  });
});
document.querySelectorAll('nav button').forEach(function(b){
  b.addEventListener('click',function(){
    document.querySelectorAll('nav button').forEach(function(x){x.setAttribute('aria-selected','false');});
    document.querySelectorAll('section.tab').forEach(function(s){s.hidden=true;});
    b.setAttribute('aria-selected','true');
    document.getElementById(b.dataset.tab).hidden=false;
    window.scrollTo({top:0});
  });
});
"""

html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PRAP — UI prototype v0.1</title>
<style>{CSS}</style>
<div class="proto">PROTOTYPE — layout and components only. Figures are a fixed snapshot;
nothing on this page loads, calculates or exports.</div>
<div class="wrap">
<header>
  <h1>Project Resource Assignment Program</h1>
  <span class="vers">{APP_VERSION} · expects source schema v{SCHEMA_EXPECTED}</span>
  <span class="file">PRAP_SourceData_Dummy_v1.3.xlsx · loaded 2026-08-01 09:14</span>
  <button class="btn">Load workbook</button>
  <button class="btn primary">Export</button>
</header>

<div class="banner"><strong>Last import: 0 errors, 1 information notice.</strong>
  PRJ-002 — an Inspection on or before the final DB lock is treated as a marker (V-21).
  <a class="lk" href="#">Open full report</a></div>

<div class="dirty"><span class="dot-w"></span> 3 unsaved edits — export to write them back
  to the workbook.</div>

<div class="panel filterbar">
  <h2>Horizon and filters <span class="scope">applies to every tab</span></h2>
  <p class="cap">One setting drives the whole page — the charts, both Overall tables and
    both source-data tabs. Opens on 24 months.</p>
  <div class="controls">
    <div class="ctl"><label>From</label><input value="2027-01" size="8"></div>
    <div class="ctl"><label>To</label><input value="2027-12" size="8"></div>
    <div class="ctl"><label>&nbsp;</label><button class="btn">Expand to all projects</button></div>
    <div class="ctl"><label>Project type</label><select><option>All</option>
      <option>NewDrug CT</option><option>Biosimilar CT</option><option>Others</option></select></div>
    <div class="ctl"><label>Project</label><select><option>All (62)</option></select></div>
    <div class="ctl"><label>Person</label><select><option>All (20)</option></select></div>
    <div class="ctl"><label>Role</label><select><option>All (13)</option></select></div>
    <div class="ctl"><label>Department</label><select><option>All (5)</option></select></div>
    <div class="ctl"><label>Unit</label><select><option>FTE</option><option>Hours</option></select></div>
    <div class="ctl"><label>&nbsp;</label><button class="btn reset">Reset filters</button></div>
  </div>
</div>

<nav role="tablist">
  <button role="tab" aria-selected="true" data-tab="t-overall">Overall</button>
  <button role="tab" aria-selected="false" data-tab="t-proj">Source data (project)</button>
  <button role="tab" aria-selected="false" data-tab="t-pers">Source data (person)</button>
</nav>

<section class="tab" id="t-overall">

  {tiles()}

  <div class="panel">
    <h2>Monthly demand by project</h2>
    <p class="cap">One band per project, ordered by total resource with the largest on
      the baseline. Every “Others” project is grey; trials take the extended colour set.
      Scroll the legend for the full list — with this many projects, identity comes from
      the legend order and the tooltip, not from hue alone.</p>
    <div class="scrollx">{chart_stacked()}</div>
  </div>

  <div class="panel">
    <h2>Resource by project</h2>
    <p class="cap">Sorted NewDrug CT, then Biosimilar CT, then Others; earlier projects
      first. <strong>Click a project name</strong> to expand it to the people and roles on
      it, and again to collapse.</p>
    <div class="scrollx">{table_projects()}</div>
  </div>

  <div class="panel">
    <h2>Mean load per person</h2>
    <p class="cap">Averaged over the window, against each threshold. Bars that breach are
      labelled with their value, so the flag never rests on colour alone.</p>
    <div class="scrollx">{chart_people()}</div>
  </div>

  <div class="panel">
    <h2>Resource by person</h2>
    <p class="cap">Summed across every project. ▲ above the ceiling, ▼ below the floor.
      <strong>Click a person name</strong> to expand it to their projects and roles, in the
      same order as the project table.</p>
    <div class="scrollx">{table_people()}</div>
    <p class="note">Under-allocation is reported as a run of three or more consecutive
      months, not per month — the run is what matters, a single quiet month is not.</p>
  </div>

  <div class="panel">
    <h2>Project timeline</h2>
    <p class="cap">Period bands shaded by weight. Trials with an interim DB lock show two
      Conduct stretches; a post-lock Inspection opens the final band.</p>
    <div class="scrollx">{chart_gantt()}</div>
  </div>
</section>

<section class="tab" id="t-proj" hidden>
  <div class="panel">
    <h2>Projects</h2>
    <p class="cap">All 23 columns, sortable and filterable. Every field is editable;
      changing an identifier cascades to the rows that reference it.</p>
    {PTBL}
    <p class="note">Showing 9 of 62 rows in this mock-up, with the selected row tinted. The real table lists all 62, sorted and filtered.</p>
  </div>
  <div class="two">
    <div class="panel">
      <h2>Milestones — {esc(PROJ['project_name'])}</h2>
      <p class="cap">Only CTA submission and the DB locks set period boundaries.</p>
      <table class="data-t"><thead><tr><th>milestone</th><th>date</th><th>seq</th>
        <th>note_1</th></tr></thead><tbody>{MROWS}</tbody></table>
    </div>
    <div class="panel">
      <h2>Periods — {esc(PROJ['project_name'])}</h2>
      <p class="cap">Derived from the milestones above.
        <button class="btn">Recompute periods</button></p>
      <table class="data-t"><thead><tr><th>seq</th><th>period</th><th>start</th><th>end</th>
        <th>weight</th><th>note_1</th></tr></thead><tbody>{PROWS}</tbody></table>
    </div>
  </div>
</section>

<section class="tab" id="t-pers" hidden>
  <div class="panel">
    <h2>People</h2>
    <p class="cap">Editable, same rules as the project table.</p>
    {STBL}
    <p class="note">Showing 9 of 20 rows in this mock-up.</p>
  </div>
  <div class="panel">
    <h2>Utilisation — {esc(PERS['person_name'])} ({SPID})</h2>
    <p class="cap">Monthly load across the window. Dashed lines are this person\u2019s ceiling and floor.</p>
    <div class="scrollx">{STRIP}</div>
  </div>
  <div class="two">
    <div class="panel">
      <h2>Assignments — {SPID}</h2>
      <table class="data-t"><thead><tr><th>id</th><th>project</th><th>role</th>
        <th>start</th><th>end</th><th>weight</th></tr></thead><tbody>{AROWS}</tbody></table>
    </div>
    <div class="panel">
      <h2>Weight overrides</h2>
      <p class="cap">Replaces person_weight for the window it covers.</p>
      <table class="data-t"><thead><tr><th>assignment</th><th>start</th><th>end</th>
        <th>override</th><th>reason</th></tr></thead><tbody>{OROWS}</tbody></table>
    </div>
  </div>
</section>
</div>
<script>{JS}</script>
"""

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(html, encoding="utf-8")
print(f"Written: {OUT}  ({len(html):,} bytes)")
