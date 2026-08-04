"""Drive app/PRAP.html and check the two source-data charts show what they claim.

  Source data (project)
    1. a project timeline run-chart stands before the Utilisation panel, drawing this
       project's periods and milestones - the Overall tab's chart for one project
    2. its bands and markers carry the same pop-ups they do on the Overall tab

  Source data (person)
    3. the Utilisation bars are STACKED - one segment per project, not one bar per month
    4. the segments of a month sum to that person-month, and to the same figure the
       Overall tables show. A chart that disagrees with the table is worse than no chart
    5. each project keeps ONE colour, and the same colour it has on the Overall tab
    6. a segment's pop-up carries both halves: the project (name, milestones that month,
       this person's FTE on it) and the person (name, total FTE that month)

    python tools/test_charts.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.0.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def probe(pg, js, fallback=None):
    """Evaluate in the page, but report a failure instead of a traceback when the build
    under test simply has not got the thing being asked about."""
    try:
        return pg.evaluate(js)
    except Exception as exc:
        print(f"       (page could not answer: {str(exc).splitlines()[0][:90]})")
        return fallback


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)

    print("app/PRAP.html — Source data (project): project timeline")
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1300)
    order = pg.eval_on_selector_all("#t-proj .panel h2", "es => es.map(e => e.textContent)")
    ti = next((i for i, h in enumerate(order) if h.startswith("Project timeline")), -1)
    ui = next((i for i, h in enumerate(order) if h.startswith("Utilisation")), -1)
    check(ti >= 0 and ui >= 0 and ti < ui,
          "the timeline panel stands before the Utilisation panel", " | ".join(order))

    drawn = probe(pg, """() => {
      const p = [...document.querySelectorAll('#t-proj .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Project timeline'));
      if (!p) return null;
      const svg = p.querySelector('svg');
      return {bands: svg.querySelectorAll('rect.band').length,
              marks: svg.querySelectorAll('polygon.ms').length,
              locks: svg.querySelectorAll('polygon.ms.key').length,
              legend: p.querySelectorAll('.legend li').length,
              tips: [...svg.querySelectorAll('[data-tip]')].length};
    }""")
    want = probe(pg, """() => {
      const pid = S.selProj;
      const per = (S.model.periods[pid] || []).filter(s => s.period_start && s.period_end).length;
      let ms = 0;
      for (const d of Object.values(S.model.milestones[pid] || {})) ms += d.filter(Boolean).length;
      return {per, ms};
    }""")
    check(drawn and drawn["bands"] == want["per"] and drawn["marks"] == want["ms"]
          and drawn["locks"] > 0 and drawn["tips"] == want["per"] + want["ms"],
          "it draws every period and every milestone, each with a pop-up",
          f"{drawn} against {want} in the data")

    print("app/PRAP.html — Source data (person): utilisation stacked by project")
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(1300)
    stack = probe(pg, """() => {
      const p = [...document.querySelectorAll('#t-pers .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Utilisation'));
      const svg = p.querySelector('svg');
      const bands = [...svg.querySelectorAll('rect.band')];
      const byCol = {};
      for (const r of bands) (byCol[r.getAttribute('x')] ||= []).push(r);
      return {segments: bands.length,
              columns: Object.keys(byCol).length,
              deepest: Math.max(...Object.values(byCol).map(v => v.length)),
              colours: new Set(bands.map(r => r.getAttribute('fill'))).size,
              legend: p.querySelectorAll('.legend li').length};
    }""")
    check(stack and stack["segments"] > stack["columns"] and stack["deepest"] > 1,
          "the bars are split into per-project segments",
          "" if not stack else f"{stack['segments']} segments over {stack['columns']} months, "
          f"deepest stack {stack['deepest']}")

    agree = probe(pg, """() => {
      const p = [...document.querySelectorAll('#t-pers .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Utilisation'));
      const svg = p.querySelector('svg');
      const byCol = {};
      for (const r of svg.querySelectorAll('rect.band'))
        (byCol[r.getAttribute('x')] ||= []).push(r);
      // the pop-up states the month and the person's total; both must match the model
      const bad = [];
      for (const col of Object.values(byCol)){
        const tip = col[0].dataset.tip;
        const month = /<br>([A-Z][a-z]{2} \\d{4})<br>/.exec(tip);
        const total = /Total this month: <b>([\\d.]+)/.exec(tip);
        if (!month || !total){ bad.push(['unparsable', tip.slice(0, 60)]); continue; }
        const k = grid().find(g => keyToLabel(g) === month[1]);
        const real = S.calc.persMonth.get(S.selPers + '|' + k) || 0;
        if (Math.abs(real - parseFloat(total[1])) > 0.005)
          bad.push([month[1], parseFloat(total[1]), real]);
        // and the segments of that column must sum to it
        let sum = 0;
        for (const r of col){
          const own = /<b>([\\d.]+) FTE<\\/b> on this project/.exec(r.dataset.tip);
          if (own) sum += parseFloat(own[1]);
        }
        if (Math.abs(sum - real) > 0.02) bad.push([month[1], 'segments', sum, real]);
      }
      return bad;
    }""")
    check(agree == [], "every month's segments sum to the person-month the model holds",
          "" if not agree else str(agree[:2]))

    colours = probe(pg, """() => {
      const p = [...document.querySelectorAll('#t-pers .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Utilisation'));
      const perProject = {};
      for (const r of p.querySelectorAll('rect.band')){
        const nm = /^<b>(.*?)<\\/b>/.exec(r.dataset.tip)[1];
        (perProject[nm] ||= new Set()).add(r.getAttribute('fill'));
      }
      const names = Object.keys(perProject);
      if (!names.length) return null;
      const split = Object.entries(perProject).filter(([, s]) => s.size > 1);
      // and the Overall stacked chart must use the same colour for the same project
      const pid = Object.keys(S.model.projects)
        .find(q => S.model.projects[q].project_name === names[0]);
      return {split, mine: [...perProject[names[0]]][0],
              overall: typeof projColourOf === "function" ? projColourOf(pid) : "(no such function)"};
    }""")
    check(colours and not colours["split"] and colours["mine"] == colours["overall"],
          "each project has one colour here, and the same one the Overall tab uses",
          "" if not colours else f"{colours['mine']} here, {colours['overall']} on Overall"
          + (f"; split: {colours['split']}" if colours["split"] else ""))

    # the pop-up: both halves, and a month that really does carry a milestone
    idx = probe(pg, """() => [...document.querySelectorAll('#t-pers svg rect.band')]
        .findIndex(r => !/none this month/.test(r.dataset.tip))""")
    check(idx is not None and idx >= 0,
          "at least one segment falls in a month carrying a milestone")
    tip = ""
    if idx is not None and idx >= 0:
        seg = pg.locator("#t-pers svg rect.band").nth(idx)
        seg.scroll_into_view_if_needed()
        pg.wait_for_timeout(300)
        seg.hover()
        pg.wait_for_timeout(700)
        tip = pg.inner_text("#tip")
    facts = probe(pg, """() => {
      const r = [...document.querySelectorAll('#t-pers svg rect.band')]
        .find(x => !/none this month/.test(x.dataset.tip));
      const nm = /^<b>(.*?)<\\/b>/.exec(r.dataset.tip)[1];
      return {project: nm, person: (S.model.people[S.selPers]||{}).person_name, id: S.selPers};
    }""")
    facts = facts or {"project": "\u0000", "person": "\u0000", "id": "\u0000"}
    have = {
        "project name": facts["project"] in tip,
        "project milestone": "Project milestone:" in tip and "none this month" not in tip,
        "this person's FTE on it": "on this project" in tip,
        "person name": facts["person"] in tip and facts["id"] in tip,
        "total FTE": "Total this month:" in tip,
    }
    check(all(have.values()), "the pop-up carries both halves",
          ", ".join(k for k, v in have.items() if not v) or tip.replace("\n", " | ")[:120])

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
