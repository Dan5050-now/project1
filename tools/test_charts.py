"""Drive app/PRAP.html and check the two source-data charts show what they claim.

  Source data (project)
    1. a project timeline run-chart stands before the Utilisation panel, drawing this
       project's periods and milestones - the Overall tab's chart for one project
    2. its bands and markers carry the same pop-ups they do on the Overall tab

  Overall
    a. 'Monthly demand by person' is stacked by PERSON, and totals the same figure every
       month as 'Monthly demand by project' - they are the same person-months summed
       along different axes, so any disagreement is a bug in one of them
    b. each person keeps ONE colour

  Source data (project)
    c. Utilisation is stacked by PERSON, and each month's segments sum to the
       project-month the calculation holds

  Source data (person)
    d. a row drafted under one person does not appear on another person's tables
    e. Weight overrides is a child of the selected ASSIGNMENT, not of the person: it
       shows that assignment's windows and no others, its heading names the person, and
       it restates the assignment it belongs to
    3. the Utilisation bars are STACKED - one segment per project, not one bar per month
    4. the segments of a month sum to that person-month, and to the same figure the
       Overall tables show. A chart that disagrees with the table is worse than no chart
    5. each project keeps ONE colour, and the same colour it has on the Overall tab
    6. a segment's pop-up carries both halves: the project (name, milestones that month,
       this person's FTE on it) and the person (name, total FTE that month)

  Every tab
    f. a line chart stands as the FIRST panel, one coloured line per project (or per
       person on the person tab), and each line's stated total and peak month agree
       with the model
    g. every panel carries the same header shape: a title, and what it covers stated
       on the right

    python tools/test_charts.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.7.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def probe(pg, js, arg=None, fallback=None):
    """Evaluate in the page, but report a failure instead of a traceback when the build
    under test simply has not got the thing being asked about."""
    try:
        return pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
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

    print("app/PRAP.html — Overall: monthly demand by person")
    byperson = probe(pg, """() => {
      const pick = t => [...document.querySelectorAll('#t-overall .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent === t);
      const pers = pick('Monthly demand by person'), proj = pick('Monthly demand by project');
      if (!pers || !proj) return null;
      const cols = p => {
        const by = {};
        for (const r of p.querySelectorAll('rect.band'))
          (by[(+r.getAttribute('x')).toFixed(1)] ||= []).push(r);
        return by;
      };
      const A = cols(pers), B = cols(proj);
      const seg = [...pers.querySelectorAll('rect.band')];
      // heights are on one scale within a chart, so compare the two charts by TOTAL height
      const sum = c => Object.fromEntries(Object.entries(c).map(([x, rs]) =>
        [x, rs.reduce((t, r) => t + (+r.getAttribute('height')), 0)]));
      const a = sum(A), b = sum(B);
      const drift = Object.keys(a).filter(x => b[x] === undefined
        || Math.abs(a[x] - b[x]) > 0.6).map(x => [x, a[x], b[x]]);
      const perPerson = {};
      for (const r of seg){
        const nm = /^<b>(.*?)<\/b>/.exec(r.dataset.tip)[1];
        (perPerson[nm] ||= new Set()).add(r.getAttribute('fill'));
      }
      return {segments: seg.length, months: Object.keys(A).length,
              deepest: Math.max(...Object.values(A).map(v => v.length)),
              drift, split: Object.entries(perPerson).filter(([, s]) => s.size > 1).map(x => x[0]),
              legend: pers.querySelectorAll('.legend li').length};
    }""")
    check(byperson and byperson["segments"] > byperson["months"] and byperson["deepest"] > 1,
          "the Overall person chart is stacked, one segment per person",
          "" if not byperson else f"{byperson['segments']} segments over {byperson['months']} "
          f"months, deepest stack {byperson['deepest']}, {byperson['legend']} legend entries")
    check(byperson and not byperson["drift"],
          "it totals the same as 'Monthly demand by project', month for month",
          "" if not byperson else str(byperson["drift"][:2]))
    check(byperson and not byperson["split"], "each person has one colour",
          "" if not byperson else str(byperson["split"]))

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

    util = probe(pg, """() => {
      const p = [...document.querySelectorAll('#t-proj .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Utilisation'));
      const by = {};
      for (const r of p.querySelectorAll('rect.band'))
        (by[(+r.getAttribute('x')).toFixed(1)] ||= []).push(r);
      const bad = [];
      for (const col of Object.values(by)){
        const m = /<br>([A-Z][a-z]{2} \d{4}) &middot;|<br>([A-Z][a-z]{2} \d{4}) \u00b7/
          .exec(col[0].dataset.tip);
        const month = /([A-Z][a-z]{2} \d{4})/.exec(col[0].dataset.tip);
        const k = grid().find(g => keyToLabel(g) === month[1]);
        const real = S.calc.projMonth.get(S.selProj + '|' + k) || 0;
        let sum = 0;
        for (const r of col){
          const own = /<b>([\d.]+) FTE<\/b> on this project/.exec(r.dataset.tip);
          if (own) sum += parseFloat(own[1]);
        }
        if (Math.abs(sum - real) > 0.02) bad.push([month[1], sum, real]);
      }
      return {cols: Object.keys(by).length,
              deepest: Math.max(0, ...Object.values(by).map(v => v.length)), bad,
              legend: p.querySelectorAll('.legend li').length};
    }""")
    check(util and util["deepest"] > 1 and not util["bad"],
          "project Utilisation is stacked by person, and the segments sum to the project-month",
          "" if not util else f"deepest stack {util['deepest']} over {util['cols']} months, "
          f"{util['legend']} legend entries" + (f", drift {util['bad'][:2]}" if util["bad"] else ""))

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

    print("app/PRAP.html — Source data (person): the tables are scoped to the person")
    scoped = probe(pg, """() => {
      const grab = sh => [...document.querySelectorAll(
         `#t-pers .data-t[data-sheet='${sh}'] tbody tr`)]
         .map(tr => ((tr.querySelector("td:nth-child(2)")||{}).textContent || "").trim())
         .filter(t => t && !/^No rows/.test(t));
      const mine = sid => new Set(S.model.raw.Assignment
         .filter(a => a.person_id === sid).map(a => a.assignment_id));
      const out = [];
      for (const sid of Object.keys(S.model.people)){
        S.selPers = sid;
        document.getElementById("persDetail").innerHTML = persDetail(sid);
        const m = mine(sid);
        const asg = grab("Assignment").filter(a => !m.has(a));
        const ppw = grab("PersonPeriodWeight").filter(a => !m.has(a));
        if (asg.length || ppw.length) out.push([sid, asg, ppw]);
      }
      return out;
    }""")
    check(scoped == [], "every person's tables show only their own rows",
          "" if not scoped else str(scoped[:2]))

    # and a row drafted under one person must not follow you to the next
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(1000)
    for sheet in ("Assignment", "PersonPeriodWeight"):
        pg.locator(f"#t-pers .data-t[data-sheet='{sheet}'] button[data-ins]").last.click()
        pg.wait_for_timeout(700)
    first = pg.evaluate("S.selPers")
    pg.locator("#t-pers .data-t[data-sheet='Person'] tbody tr").nth(4) \
      .locator("td[data-col='person_id']").first.click()
    pg.wait_for_timeout(900)
    leaked = probe(pg, """() => {
      const grab = sh => [...document.querySelectorAll(
         `#t-pers .data-t[data-sheet='${sh}'] tbody tr`)]
         .map(tr => ((tr.querySelector("td:nth-child(2)")||{}).textContent || "").trim())
         .filter(t => t && !/^No rows/.test(t));
      const m = new Set(S.model.raw.Assignment
         .filter(a => a.person_id === S.selPers).map(a => a.assignment_id));
      return {sid: S.selPers,
              asg: grab("Assignment").filter(a => !m.has(a)),
              ppw: grab("PersonPeriodWeight").filter(a => !m.has(a))};
    }""")
    check(leaked and not leaked["asg"] and not leaked["ppw"],
          "a row drafted under one person does not follow you to the next",
          "" if not leaked else f"on {leaked['sid']}: {leaked['asg']} {leaked['ppw']}")

    print("app/PRAP.html — Weight overrides follows the selected assignment")
    pg.click("#discardBtn")
    pg.wait_for_timeout(900)
    pg.locator("#t-pers .data-t[data-sheet='Person'] tbody tr").first \
      .locator("td[data-col='person_id']").first.click()
    pg.wait_for_timeout(900)
    titles = probe(pg, """() => {
      const h = t => [...document.querySelectorAll('#t-pers .panel h2')]
        .find(e => e.textContent.startsWith(t));
      const pe = S.model.people[S.selPers];
      return {asg: (h('Assignments')||{}).textContent, ppw: (h('Weight overrides')||{}).textContent,
              want: `${pe.person_name} (${S.selPers})`};
    }""")
    check(titles and titles["asg"].endswith(titles["want"])
          and titles["ppw"].endswith(titles["want"]),
          "both headings name the selected person", str(titles))

    rows = pg.locator("#t-pers .data-t[data-sheet='Assignment'] tbody tr")
    wrong, seen = [], 0
    for i in range(rows.count()):
        aid = rows.nth(i).get_attribute("data-id")
        if not aid:
            continue
        rows.nth(i).locator("td[data-col='role_name']").first.click()
        pg.wait_for_timeout(500)
        got = probe(pg, """() => {
          const panel = [...document.querySelectorAll('#t-pers .panel')]
            .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Weight overrides'));
          const shown = [...document.querySelectorAll(
             "#t-pers .data-t[data-sheet='PersonPeriodWeight'] tbody tr")]
             .map(tr => ((tr.querySelector("td:nth-child(2)")||{}).textContent||"").trim())
             .filter(t => t && !/^No rows/.test(t));
          const real = S.model.raw.PersonPeriodWeight
             .filter(w => w.assignment_id === S.selAsg).map(w => w.assignment_id);
          const sel = document.querySelector(
             "#t-pers .data-t[data-sheet='Assignment'] tbody tr.sel");
          return {selAsg: S.selAsg, shown, real,
                  line: (panel.querySelector('.asgline')||{}).textContent
                          .replace(/\s+/g, " ").trim(),
                  highlighted: sel ? sel.dataset.id : null};
        }""")
        seen += 1
        if not got or got["selAsg"] != aid or got["shown"] != got["real"] \
           or got["highlighted"] != aid or aid not in got["line"]:
            wrong.append([aid, got])
    check(seen > 1 and not wrong,
          "every assignment shows its own windows, and only those",
          f"{seen} assignments checked" if not wrong else str(wrong[:1]))

    line = probe(pg, """() => {
      const panel = [...document.querySelectorAll('#t-pers .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent.startsWith('Weight overrides'));
      const a = S.model.raw.Assignment.find(x => x.assignment_id === S.selAsg);
      return {line: (panel.querySelector('.asgline')||{}).textContent.replace(/\s+/g, " ").trim(),
              project: (S.model.projects[a.project_id]||{}).project_name, role: a.role_name,
              weight: a.person_weight === null ? null : Number(a.person_weight).toFixed(2)};
    }""")
    check(line and line["project"] in line["line"] and line["role"] in line["line"]
          and (line["weight"] is None or line["weight"] in line["line"]) and "~" in line["line"],
          "it restates the assignment: project, role, dates and weight",
          "" if not line else line["line"][:110])

    # a new override row belongs to the assignment on screen
    pg.locator("#t-pers .data-t[data-sheet='PersonPeriodWeight'] button[data-ins]").last.click()
    pg.wait_for_timeout(900)
    seeded = probe(pg, """() => {const r = S.model.raw.PersonPeriodWeight.find(x => x.__new);
        return {aid: r && r.assignment_id, sel: S.selAsg};}""")
    check(seeded and seeded["aid"] == seeded["sel"],
          "a new override row is seeded with the selected assignment", str(seeded))
    pg.click("#discardBtn")
    pg.wait_for_timeout(800)

    print("app/PRAP.html — the monthly trend line chart")
    for tab, pane, kind in (("Overall", "#t-overall", "project"),
                            ("Source data (project)", "#t-proj", "project"),
                            ("Source data (person)", "#t-pers", "person")):
        pg.click(f"text={tab}")
        pg.wait_for_timeout(1300)
        got = probe(pg, """({pane, kind}) => {
          const first = document.querySelector(pane + " .panel");
          const svg = first && first.querySelector("svg.chart");
          if (!svg) return null;
          const lines = [...svg.querySelectorAll("polyline.ln")];
          const hits = [...svg.querySelectorAll("polyline.lnhit")];
          const G = grid();
          const bad = [];
          for (const h of hits){
            const t = h.dataset.tip;
            const name = /^<b>(.*?)<\/b>/.exec(t)[1];
            const total = parseFloat(/<b>(?:.*?)<\/b><br>([\d.]+) /.exec(t)[1]);
            const peakM = /peak [\d.]+ in ([A-Z][a-z]{2} \d{4})/.exec(t)[1];
            const id = kind === "project"
              ? Object.keys(S.model.projects).find(q =>
                  S.model.projects[q].project_name === name)
              : Object.keys(S.model.people).find(q =>
                  (S.model.people[q].person_name || q) === name);
            const at = k => kind === "project"
              ? (S.calc.projMonth.get(id + "|" + k) || 0)
              : (S.calc.persMonth.get(id + "|" + k) || 0);
            const real = G.reduce((x, k) => x + at(k), 0);
            let peak = -1, pk = null;
            for (const k of G){ const v = at(k); if (v > peak){ peak = v; pk = k; } }
            if (!id || Math.abs(real - total) > 0.02 || keyToLabel(pk) !== peakM)
              bad.push([name, total, real, peakM, pk && keyToLabel(pk)]);
          }
          const colour = kind === "project"
            ? (typeof projColourOf === "function" ? projColourOf : null)
            : (typeof persColourOf === "function" ? persColourOf : null);
          const strokes = new Set(lines.map(l => l.getAttribute("stroke")));
          return {title: (first.querySelector("h2")||{}).textContent,
                  lines: lines.length, hits: hits.length, dots: svg.querySelectorAll("circle.lndot").length,
                  distinct: strokes.size, legend: first.querySelectorAll(".legend li").length,
                  bad};
        }""", {"pane": pane, "kind": kind})
        check(got and got["lines"] > 1 and got["lines"] == got["hits"]
              and got["dots"] > got["lines"] and "trend" in (got["title"] or ""),
              f"{tab}: the first panel is a line chart, one line per {kind}",
              "" if not got else f"{got['title']!r}: {got['lines']} lines, {got['dots']} points, "
              f"{got['legend']} legend entries")
        check(got and got["distinct"] == got["lines"],
              f"{tab}: every line has its own colour",
              "" if not got else f"{got['distinct']} colours for {got['lines']} lines")
        check(got and not got["bad"],
              f"{tab}: each line's total and peak month agree with the model",
              "" if not got else str(got["bad"][:2]))

    shape = probe(pg, """() => {
      const bad = [];
      for (const tab of ["t-overall", "t-proj", "t-pers", "t-gen"]){
        for (const p of document.querySelectorAll("#" + tab + " .panel")){
          const h = p.querySelector(":scope > .phead > h2, :scope > h2");
          if (!h){ bad.push([tab, "panel with no heading"]); continue; }
          if (!h.parentElement.classList.contains("phead"))
            bad.push([tab, h.textContent.slice(0, 40) + " — heading not in a .phead"]);
        }
      }
      return bad;
    }""")
    check(shape == [], "every panel uses the same header shape",
          "" if not shape else str(shape[:3]))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
