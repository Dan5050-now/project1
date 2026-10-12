"""Today on every chart and month table, and a person's own project timeline (R-65).

Two requests from the field:

  1. "In all run-charts and tables of all tabs, present where the current time is." So
     every chart drawn over months carries one dashed line at today's day within its
     month, labelled Today; the Project timeline carries one across every row; the two
     month-column tables outline the current month's column and badge its heading; and
     Monthly estimation marks the current month's row.
  2. "In Source data (person), add the project timeline, so the selected person's
     projects can be seen." A Project timeline cut to the projects the person has an
     assignment on - whatever the filters say - with a bar under each row for when they
     are on it.

    python tools/test_now.py
"""

import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.15.xlsx"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


T = time.localtime()
NOWK = T.tm_year * 12 + T.tm_mon - 1
CHARTS = {
    "t-overall": ["trend", "timeline", "stack-proj", "stack-pers"],
    "t-proj": ["trend", "proj-timeline", "proj-util"],
    "t-pers": ["trend", "pers-util", "pers-timeline"],
}


def marks(pg, tab):
    return pg.evaluate("""t => Object.fromEntries([...document.querySelectorAll(
        '#' + t + ' .panel[data-panel]')].map(p => [p.dataset.panel,
        p.querySelectorAll('svg .nowmark').length]))""", tab)


def show(pg, tab):
    pg.click(f'nav [data-tab="{tab}"]')
    pg.wait_for_timeout(1200)


print("R-65 — today, everywhere months are drawn; a person's own timeline")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    pg = b.new_page(viewport={"width": 1500, "height": 1000})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3500)
    pg.evaluate("k => { S.from = k - 3; S.to = k + 20; renderAll(); showTab('t-overall'); }", NOWK)
    pg.wait_for_timeout(1200)
    check(pg.evaluate("nowKey()") == NOWK, "the application's today is the machine's today",
          pg.evaluate("todayLabel()"))

    print("\n1. every chart carries today")
    for tab, panels in CHARTS.items():
        show(pg, tab)
        if tab == "t-proj":
            pg.evaluate("() => { S.selProj = 'PRJ-007'; renderAll(); showTab('t-proj'); }")
            pg.wait_for_timeout(1000)
        m = marks(pg, tab)
        missing = [p for p in panels if m.get(p) != 1]
        check(not missing, f"{tab}: ONE TODAY LINE ON EACH CHART - {', '.join(panels)}",
              str({p: m.get(p) for p in panels}))

    show(pg, "t-overall")
    # Where it sits: inside the current month's slot, at today's day within it.
    pos = pg.evaluate("""k => {
        const svg = document.querySelector('#t-overall .panel[data-panel="stack-proj"] svg');
        const ln = svg.querySelector('.nowln'); const x = +ln.getAttribute('x1');
        const G = grid(), i = G.indexOf(k);
        const vb = svg.viewBox.baseVal, K = CHART.stack;
        const W = Math.max(K.Wmin, K.Wbase + G.length * K.Wper), bw = (W - K.padL - K.padR) / G.length;
        const left = K.padL + i * bw + 3;
        return {x, left, right: left + bw - 8, frac: nowFrac()}; }""", NOWK)
    want = pos["left"] + (pos["right"] - pos["left"]) * pos["frac"]
    check(pos["left"] <= pos["x"] <= pos["right"] and abs(pos["x"] - want) < 1,
          "THE LINE IS IN THE CURRENT MONTH, at today's day within it",
          f"x {pos['x']:.1f} in [{pos['left']:.1f}, {pos['right']:.1f}]")
    lab = pg.evaluate("""() => [...document.querySelectorAll('#t-overall svg .nowlab')]
        .map(t => t.textContent)""")
    check(lab and all(t == "Today" for t in lab), "and each is labelled Today", f"{len(lab)} label(s)")
    tl = pg.evaluate("""() => { const svg = document.querySelector(
          '#t-overall .panel[data-panel="timeline"] svg');
        const ln = svg.querySelector('.nowln');
        return {y1: +ln.getAttribute('y1'), y2: +ln.getAttribute('y2'),
                h: svg.viewBox.baseVal.height}; }""")
    check(tl["y2"] - tl["y1"] > tl["h"] * 0.8,
          "on the Project timeline it runs through every row", str(tl))

    print("\n2. the month tables mark the current month")
    for panel in ("table-proj", "table-pers"):
        t = pg.evaluate("""p => { const tb = document.querySelector(
              '#t-overall .panel[data-panel="' + p + '"] table.grid-t');
            const hs = [...tb.querySelectorAll('thead th')];
            const i = hs.findIndex(h => h.classList.contains('now'));
            const rows = [...tb.querySelectorAll('tbody tr')];
            return {i, heads: hs.filter(h => h.classList.contains('now')).length,
                    tag: i >= 0 ? hs[i].innerText.replace(/\\s+/g, ' ') : '',
                    rows: rows.length,
                    marked: rows.filter(r => r.children[i] && r.children[i].classList.contains('now')).length,
                    stray: tb.querySelectorAll('tbody td.now').length}; }""", panel)
        mon = time.strftime("%b", T)
        check(t["heads"] == 1 and t["tag"].startswith("Today") and mon in t["tag"]
              and t["rows"] > 1 and t["marked"] == t["rows"] == t["stray"],
              f"{panel}: THE CURRENT MONTH'S COLUMN IS MARKED IN EVERY ROW, and only that column",
              f"{t['tag']} · {t['marked']} of {t['rows']} row(s)")

    show(pg, "t-proj")
    pg.evaluate("() => { S.selProj = 'PRJ-007'; renderAll(); showTab('t-proj'); }")
    pg.wait_for_timeout(1000)
    row = pg.evaluate("""() => [...document.querySelectorAll('#t-proj tr[data-now]')]
        .map(r => r.querySelector('td[data-col="month"]').textContent)""")
    check(row == [time.strftime("%Y-%m", T)],
          "MONTHLY ESTIMATION MARKS THE CURRENT MONTH'S ROW", str(row))

    # A horizon that starts after today has no today in it, and says nothing.
    pg.evaluate("k => { S.from = k + 2; S.to = k + 14; renderAll(); showTab('t-overall'); }", NOWK)
    pg.wait_for_timeout(1200)
    m = marks(pg, "t-overall")
    check(m.get("trend") == 0 and m.get("stack-proj") == 0
          and pg.locator("#t-overall th.now").count() == 0,
          "A HORIZON WITHOUT TODAY IN IT DRAWS NO LINE - none pinned to an edge", str(m))
    check(m.get("timeline") == 1,
          "while the Project timeline, which spans the projects' own dates, still does")
    pg.evaluate("k => { S.from = k - 3; S.to = k + 20; renderAll(); showTab('t-overall'); }", NOWK)
    pg.wait_for_timeout(800)

    print("\n3. a person's own project timeline")
    show(pg, "t-pers")
    sid = pg.evaluate("S.selPers")
    want = pg.evaluate("""s => { const a = S.model.assignments.filter(x => x.person_id === s
            && S.model.projects[x.project_id]);
        return {pids: [...new Set(a.map(x => x.project_id))].sort(byRank), n: a.length,
                name: S.model.people[s].person_name}; }""", sid)
    got = pg.evaluate("""() => { const p = document.querySelector(
          '#t-pers .panel[data-panel="pers-timeline"]');
        if (!p) return null;
        return {head: p.querySelector('h2').textContent,
                rows: [...p.querySelectorAll('rect.band')].map(r => r.dataset.s2)
                        .filter((v, i, a) => a.indexOf(v) === i),
                bars: p.querySelectorAll('rect.asgbar').length,
                legend: p.querySelector('.legend').innerText}; }""")
    check(got and want["name"] in got["head"] and sorted(got["rows"]) == sorted(want["pids"]),
          "THE PERSON TAB HAS A PROJECT TIMELINE OF EXACTLY THE PROJECTS THEY ARE ON",
          f"{got and got['head']}: {got and len(got['rows'])} of {len(want['pids'])}")
    check(got and got["bars"] == want["n"] and want["n"] > 0,
          "WITH A BAR FOR EACH OF THEIR ASSIGNMENTS - when they are on it",
          f"{got and got['bars']} bar(s), {want['n']} assignment(s)")
    check(got and f"when {want['name']} is on it" in got["legend"] and "today" in got["legend"],
          "and the legend says what the bar and the line are")
    span = pg.evaluate("""s => { const a = S.model.assignments.find(x => x.person_id === s
            && x.assign_start_date);
        if (!a) return null;
        const bar = [...document.querySelectorAll('#t-pers rect.asgbar')]
          .find(r => r.dataset.tip.includes(a.role_name) && r.dataset.tip.includes(ymd(a.assign_start_date)));
        return bar ? true : false; }""", sid)
    check(span is True, "a bar names the role and the dates it covers")

    # The filters above do not narrow it: it is about the person, not the view.
    other = want["pids"][-1]
    pg.evaluate("p => { S.f.proj = new Set(Object.keys(S.model.projects).filter(x => x !== p));"
                " renderAll(); showTab('t-pers'); }", other)
    pg.wait_for_timeout(1000)
    out = pg.evaluate("p => !activeProjects().includes(p)", other)
    rows = pg.evaluate("""() => [...document.querySelectorAll(
        '#t-pers .panel[data-panel="pers-timeline"] rect.band')].map(r => r.dataset.s2)""")
    check(out and other in rows, "A PROJECT FILTERED OUT ABOVE IS STILL ON THE PERSON'S TIMELINE",
          f"{other}: filtered out {out}, {'shown' if other in rows else 'missing'}")
    pg.evaluate("() => { S.f.proj = new Set(); renderAll(); showTab('t-pers'); }")
    pg.wait_for_timeout(800)

    lone = pg.evaluate("""() => { const busy = new Set(S.model.assignments.map(a => a.person_id));
        return Object.keys(S.model.people).find(p => !busy.has(p)) || null; }""")
    if lone is None:
        lone = pg.evaluate("""() => { const r = S.model.raw.Person[0];
            const s = {...r, __row: 9999, person_id: 'PSN-999', person_name: 'New Starter'};
            S.model.raw.Person.push(s); rebuild(true); return 'PSN-999'; }""")
    pg.evaluate("s => { S.selPers = s; renderAll(); showTab('t-pers'); }", lone)
    pg.wait_for_timeout(1000)
    txt = pg.inner_text('#t-pers .panel[data-panel="pers-timeline"]') \
        if pg.locator('#t-pers .panel[data-panel="pers-timeline"]').count() else ""
    check("has no assignment yet" in txt, "somebody on nothing is told so, not shown an empty chart")

    check(not errors, "no script error anywhere in the run", "; ".join(errors[:3]))
    b.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
