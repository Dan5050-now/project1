"""Period derivation rules the plan defines (R-70).

Asked for from the field: Auto derivation on a project's Periods should work out each
period's start and end from rules the users define on General assumptions - a new section,
'Period derivation rules', next to Period colours, by project type - each date an
anchored milestone plus or minus days. Where a milestone is missing, the date is a
plausible one from the neighbours: a start the day after the previous period ends, an end
the day before the next one starts.

What is checked, with the fault put back where a guard could pass without working:

  * The sheet. Schema 17 carries PeriodRule, and the shipped files carry the standard
    rules for the three clinical types. A schema 16 file still opens - no rules, said as
    information - and is derived exactly as before, by the built-in rule.
  * The rule. Each date is its milestone plus its days; a start counts from a
    milestone's FIRST date and an end from its LAST; a missing start is the day after
    the previous period ends and a missing end the day before the next starts - the
    request's own example; the first period starts with the project and the last ends
    with it; a boundary unknown from both sides goes halfway; a period with neither
    milestone recorded is left out; one that would end before it starts is left out; an
    estimate is marked as one and a rule that names no milestone is not.
  * The same answer from the Python reference, case by case.
  * The section: beside Period colours; a button per type; every period of the type on a
    line, typed into in place - '+2' is 2 - with the milestone list offered; a period with
    no rule says so and offers one; the standard rules laid out where a type has none; a
    type's rules copied to another. V-41 says what a rule cannot do.
  * Auto derivation shows every date and how it was found before it writes; Cancel
    changes nothing; Apply writes exactly what was shown. A project loaded with no
    periods is derived by its type's rules, 'Others' included once it has some - and
    by the built-in rule when the rules are taken away, so the rules are shown to be
    what drives it.

    python tools/test_r70.py
"""

import pathlib
import sys
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                          # noqa: E402

APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.16.xlsx"
OLD = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.15.xlsx"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# The derivation run in the page on a made-up project, so every case is a statement about
# the rule and not about one fixture's dates. Dates go in and come out as YYYY-MM-DD.
PLAN = """a => { const D = s => s ? new Date(s + 'T00:00:00Z') : null;
  const ms = {}; for (const [k, v] of Object.entries(a.ms)) ms[k] = v.map(D).sort((x, y) => x - y);
  const proj = {project_type: a.type, start_date: D(a.start), end_date: D(a.end)};
  const d = deriveByRule(proj, ms, a.rules.map((r, i) => ({__row: i + 1, period_name: r[0],
    start_milestone: r[1], start_offset_days: r[2], end_milestone: r[3], end_offset_days: r[4]})),
    a.order);
  return {segs: d.segs.map(g => [g.name, ymd(g.start), ymd(g.end), g.how.start, g.how.end,
                                 g.est.start, g.est.end]),
          left: d.left.map(l => [l.name, l.why]), seams: d.seams}; }"""
ORDER = ["Before-Start-up", "Start-up", "Conduct (interim)", "Close-out (interim)",
         "Conduct (final)", "Close-out (final)", "After Close-out (final)"]
STD = [["Before-Start-up", None, None, "Protocol (v1)", 0],
       ["Start-up", "Protocol (v1)", 1, "First SIV", 0],
       ["Conduct (interim)", None, None, "interim DB lock", -92],
       ["Close-out (interim)", None, None, "interim DB lock", 0],
       ["Conduct (final)", None, None, "final DB lock", -92],
       ["Close-out (final)", None, None, "final DB lock", 0],
       ["After Close-out (final)", None, None, "Inspection", 0]]
MS = {"Protocol (v1)": ["2026-03-01"], "CTA submission": ["2026-04-15"],
      "First SIV": ["2026-09-01"], "interim DB lock": ["2027-06-30"],
      "final DB lock": ["2028-06-30"], "Inspection": ["2027-02-01", "2028-10-31"]}


def case(pg, rules, ms, start="2026-01-01", end="2028-12-31", typ="NewDrug CT"):
    return pg.evaluate(PLAN, {"rules": rules, "ms": ms, "start": start, "end": end,
                              "type": typ, "order": ORDER})


def py_case(rules, ms, start="2026-01-01", end="2028-12-31"):
    D = date.fromisoformat
    got = prap_io.derive_by_rule(
        {"start_date": D(start) if start else None, "end_date": D(end) if end else None},
        {k: sorted(D(x) for x in v) for k, v in ms.items()},
        [{"__row": i + 1, "period_name": r[0], "start_milestone": r[1],
          "start_offset_days": r[2], "end_milestone": r[3], "end_offset_days": r[4]}
         for i, r in enumerate(rules)], ORDER)
    return [[g["period_name"], g["period_start"].isoformat(), g["period_end"].isoformat()]
            for g in (got or [])]


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)

    # ------------------------------------------------------------------ 1
    print("\n1. the sheet, and a file from before it")
    pg.set_input_files("#picker", str(OLD))
    pg.wait_for_timeout(3000)
    old = pg.evaluate("""() => { const pid = Object.keys(S.model.projects)
          .find(p => CLINICAL_TYPES.has(S.model.projects[p].project_type));
        const pr = S.model.projects[pid];
        const d = derivationPlan(pr, S.model.milestones[pid], S.model);
        const b = derivePeriodsBuiltIn(pr, S.model.milestones[pid]);
        return {info: S.model.findings.filter(f => f.rule === 'V-09' && f.sheet === 'PeriodRule')
                  .map(f => f.sev + ': ' + f.msg.slice(0, 60)),
                rules: S.model.raw.PeriodRule.length, src: d.source,
                same: JSON.stringify(d.segs.map(g => [g.name, ymd(g.start), ymd(g.end)]))
                  === JSON.stringify(b.map(g => [g.period_name, ymd(g.period_start), ymd(g.period_end)]))}; }""")
    check(len(old["info"]) == 1 and old["info"][0].startswith("information")
          and old["rules"] == 0,
          "A SCHEMA 16 FILE STILL OPENS — it has no rules, and that is said as information",
          old["info"][0] if old["info"] else "")
    check(old["src"] == "built-in" and old["same"],
          "and it is derived exactly as before, by the built-in rule")
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3000)
    st = pg.evaluate("""() => ({cols: SHEET_HEADERS.PeriodRule, later: LATER_SHEETS.PeriodRule,
        v09: S.model.findings.filter(f => f.rule === 'V-09').length,
        types: Object.fromEntries(Object.entries(S.model.periodRules).map(([k, v]) => [k, v.length])),
        v41: S.model.findings.filter(f => f.rule === 'V-41').length})""")
    check(st["cols"] == ["project_type", "period_name", "start_milestone", "start_offset_days",
                         "end_milestone", "end_offset_days", "note_1"] and st["later"] == 17
          and st["v09"] == 0,
          "SCHEMA 17 CARRIES PeriodRule, and the shipped file opens without a word about it",
          " · ".join(st["cols"]))
    check(st["types"] == {"NewDrug CT": 7, "Biosimilar CT (Healthy)": 7,
                          "Biosimilar CT (Patient)": 7} and st["v41"] == 0,
          "with the standard rules for the three clinical types, every one sound", str(st["types"]))

    # ------------------------------------------------------------------ 2
    print("\n2. the rule")
    r = case(pg, STD, MS)
    by = {s[0]: s for s in r["segs"]}
    check(by["Start-up"][1:3] == ["2026-03-02", "2026-09-01"]
          and by["Start-up"][3] == "Protocol (v1) + 1 day" and by["Start-up"][4] == "First SIV",
          "EACH DATE IS ITS MILESTONE PLUS ITS DAYS — Start-up the day after Protocol (v1), to "
          "First SIV", str(by["Start-up"][1:5]))
    check(by["Conduct (interim)"][2] == "2027-03-30" and by["Close-out (interim)"][1:3]
          == ["2027-03-31", "2027-06-30"],
          "−92 is 92 days before: Conduct (interim) ends then, Close-out (interim) runs to the lock",
          f"{by['Conduct (interim)'][1:3]} {by['Close-out (interim)'][1:3]}")
    check(by["Before-Start-up"][1:3] == ["2026-01-01", "2026-03-01"]
          and by["Before-Start-up"][3] == "the project's start" and not by["Before-Start-up"][5],
          "the first period starts with the project — the rule names no milestone, so that is "
          "the rule's own date, not an estimate", str(by["Before-Start-up"][1:6]))
    check(by["After Close-out (final)"][1:3] == ["2028-07-01", "2028-10-31"],
          "a milestone recorded twice gives an end its LAST date (the second Inspection)",
          str(by["After Close-out (final)"][1:3]))
    check(by["Conduct (final)"][3] == "the day after Close-out (interim) ends"
          and not by["Conduct (final)"][5] and r["left"] == [] and r["seams"] == [],
          "an empty start follows the previous period; seven periods, meeting end to end")

    # The request's own example, one side at a time. Conduct (interim) starts at First
    # SIV + 1 and First SIV is not recorded: it starts the day after the previous period
    # ends. Then its END milestone is the one missing: it ends the day before the next
    # period starts.
    ex = [["Start-up", "Protocol (v1)", 1, "CTA submission", 120],
          ["Conduct (interim)", "First SIV", 1, "interim DB lock", -92],
          ["Close-out (interim)", None, None, "interim DB lock", 0]]
    ms2 = {k: v for k, v in MS.items() if k != "First SIV"}
    r = case(pg, ex, ms2)
    ci = {s[0]: s for s in r["segs"]}["Conduct (interim)"]
    check(ci[1] == "2026-08-14" and "the day after Start-up ends" in ci[3]
          and "'First SIV' not recorded" in ci[3] and ci[5] and not ci[6],
          "THE REQUEST'S EXAMPLE: First SIV missing, Conduct (interim) starts the day after the "
          "previous period ends — and that start is marked as an estimate", f"{ci[1]}: {ci[3]}")
    check(py_case(ex, ms2) == [s[:3] for s in r["segs"]],
          "the Python reference derives the same, date for date")
    ex2 = [["Start-up", "Protocol (v1)", 1, "First SIV", 0],
           ["Conduct (interim)", "First SIV", 1, "interim DB lock cut-off", 0],
           ["Close-out (interim)", "interim DB lock", -60, "interim DB lock", 0]]
    r = case(pg, ex2, MS)
    ci = {s[0]: s for s in r["segs"]}["Conduct (interim)"]
    check(ci[1] == "2026-09-02" and ci[2] == "2027-04-30"
          and "the day before Close-out (interim) starts" in ci[4]
          and "'interim DB lock cut-off' not recorded" in ci[4] and ci[6] and not ci[5],
          "and with its END milestone missing, it ends the day before the next period starts",
          f"{ci[2]}: {ci[4]}")
    check(py_case(ex2, MS) == [s[:3] for s in r["segs"]], "the Python reference agrees")

    # Neither side of a boundary known: halfway.
    hw = [["Start-up", "Protocol (v1)", 1, "First SIV", 0],
          ["Conduct (final)", None, None, "final DB lock", -92],
          ["Close-out (final)", None, None, "final DB lock", 0]]
    ms3 = {k: v for k, v in MS.items() if k not in ("First SIV",)}
    r = case(pg, hw, ms3)
    su, cf = r["segs"][0], r["segs"][1]
    # Start-up opens 2026-03-02 and Conduct (final) ends 2028-03-30: 759 days apart, so
    # the boundary falls 379 days in.
    check(su[2] == "2027-03-16" and cf[1] == "2027-03-17" and su[6] and cf[5]
          and "halfway" in su[4],
          "A BOUNDARY UNKNOWN FROM BOTH SIDES GOES HALFWAY — and both sides are marked estimates",
          f"Start-up to {su[2]}, Conduct (final) from {cf[1]}")
    check(py_case(hw, ms3) == [s[:3] for s in r["segs"]], "the Python reference agrees")

    # A study with no interim lock and no later inspection.
    ms4 = {k: v for k, v in MS.items() if k not in ("interim DB lock", "Inspection")}
    r = case(pg, STD, ms4)
    names = [s[0] for s in r["segs"]]
    left = dict(r["left"])
    check(names == ["Before-Start-up", "Start-up", "Conduct (final)", "Close-out (final)"]
          and "interim DB lock" in left.get("Conduct (interim)", "")
          and "Inspection" in left.get("After Close-out (final)", ""),
          "A PERIOD WITH NEITHER MILESTONE RECORDED IS LEFT OUT — no interim lock, no interim "
          "periods — with the reason", " · ".join(names))
    check(r["segs"][2][1] == "2026-09-02",
          "and Conduct (final) then follows Start-up directly", r["segs"][2][1])
    check(py_case(STD, ms4) == [s[:3] for s in r["segs"]], "the Python reference agrees")

    # The last period's milestone missing: it ends with the project.
    r = case(pg, [["Start-up", "Protocol (v1)", 1, "First SIV", 0],
                  ["Close-out (final)", "final DB lock", -91, "database freeze", 0]], MS)
    cf = r["segs"][-1]
    check(cf[1] == "2028-03-31" and cf[2] == "2028-12-31" and "the project's end" in cf[4]
          and "'database freeze' not recorded" in cf[4] and cf[6],
          "a last period whose milestone is missing ends with the project — as an estimate",
          f"{cf[2]}: {cf[4]}")
    r = case(pg, [["Start-up", "First SIV", 0, "Protocol (v1)", 0]], MS)
    check(not r["segs"] and "before it starts" in dict(r["left"]).get("Start-up", ""),
          "a period that would end before it starts is left out, and said so",
          dict(r["left"]).get("Start-up", "")[:60])

    # ------------------------------------------------------------------ 3
    print("\n3. the section on General assumptions")
    pg.click("nav button[data-tab='t-gen']")
    pg.wait_for_timeout(900)
    lay = pg.evaluate("""() => { const a = document.querySelector("#t-gen [data-panel='gen-phl']"),
          b = document.querySelector("#t-gen [data-panel='gen-prule']");
        return {h2: b && b.querySelector('h2').textContent,
                beside: !!a && !!b && Math.abs(a.getBoundingClientRect().top - b.getBoundingClientRect().top) < 2
                  && a.getBoundingClientRect().right <= b.getBoundingClientRect().left,
                types: [...b.querySelectorAll('[data-prtype]')].map(x => x.dataset.prtype),
                lines: [...b.querySelectorAll('.prt tbody tr')].map(tr => tr.querySelector('.pn').textContent)}; }""")
    check(lay["h2"] == "Period derivation rules" and lay["beside"],
          "'PERIOD DERIVATION RULES' SITS NEXT TO PERIOD COLOURS", str(lay["beside"]))
    check(lay["types"] == ["NewDrug CT", "Biosimilar CT (Healthy)", "Biosimilar CT (Patient)", "Others"]
          and lay["lines"] == ORDER,
          "by project type, every period of the type on a line, in the order a project runs",
          " · ".join(lay["types"]))
    sel = "#t-gen .prt tr:has(th.pn:text-is('Start-up')) td[data-col='start_offset_days']"
    pg.locator(sel).click()
    pg.keyboard.press("Control+A")
    pg.keyboard.type("+2")
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(900)
    st = pg.evaluate("""() => ({v: S.model.raw.PeriodRule.find(r => r.project_type === 'NewDrug CT'
          && r.period_name === 'Start-up').start_offset_days, n: S.pending.length,
        shown: document.querySelector("#t-gen .prt tr:nth-child(2) td[data-col='start_offset_days']").textContent,
        rule: S.model.periodRules['NewDrug CT'].find(r => r.period_name === 'Start-up').start_offset_days})""")
    check(st["v"] == 2 and st["n"] == 1 and st["shown"] == "+2" and st["rule"] == 2,
          "A RULE IS TYPED INTO IN PLACE — '+2' is 2, shown with its sign, and the derivation "
          "reads it at once", str(st))
    pg.locator("#t-gen .prt tr:has(th.pn:text-is('Conduct (final)')) td[data-col='start_milestone']").click()
    pg.wait_for_timeout(500)
    offered = pg.evaluate("() => el('sugg').hidden ? [] : [...el('sugg').querySelectorAll('.s')].map(s => s.dataset.v)")
    check("First SIV" in offered and "final DB lock" in offered,
          "a milestone cell offers the milestone list", f"{len(offered)} offered")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pg.click("#t-gen [data-prtype='Others']")
    pg.wait_for_timeout(600)
    st = pg.evaluate("""() => ({lines: [...document.querySelectorAll('#t-gen .prt tbody tr')]
          .map(tr => [tr.querySelector('.pn').textContent, tr.classList.contains('norule')]),
        std: !!document.querySelector("#t-gen [data-act='prulestd']")})""")
    check(st["lines"] == [["Planning", True], ["Develop", True], ["Close", True]] and not st["std"],
          "'Others' has no rules: each of its periods says so — and there is no standard to lay out",
          str(st["lines"]))
    pg.click("#t-gen [data-act='pruleadd'][data-period='Planning']")
    pg.wait_for_timeout(900)
    st = pg.evaluate("""() => ({focus: document.activeElement.dataset.col,
        rows: S.model.raw.PeriodRule.filter(r => r.project_type === 'Others').map(r => r.period_name),
        draft: S.model.raw.PeriodRule.some(r => r.__new)})""")
    check(st["rows"] == ["Planning"] and st["focus"] == "end_milestone" and not st["draft"],
          "+ Add a rule makes the row, with the caret in its end milestone", str(st))
    pg.keyboard.type("CTA submission")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)
    check(pg.evaluate("Object.keys(S.model.periodRules).includes('Others')"),
          "and 'Others' is derived by rules from then on")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)
    pg.click("#t-gen [data-prtype='Biosimilar CT (Patient)']")
    pg.wait_for_timeout(500)
    pg.evaluate("""() => { const rows = S.model.raw.PeriodRule.filter(r => r.project_type === 'Biosimilar CT (Patient)');
        for (const r of rows) S.model.raw.PeriodRule.splice(S.model.raw.PeriodRule.indexOf(r), 1);
        rebuild(true); renderKeepingTab(); }""")
    pg.wait_for_timeout(900)
    pg.click("#t-gen [data-act='prulestd']")
    pg.wait_for_timeout(1000)
    st = pg.evaluate("""() => ({n: S.model.raw.PeriodRule.filter(r => r.project_type === 'Biosimilar CT (Patient)').length,
        same: JSON.stringify(S.model.raw.PeriodRule.filter(r => r.project_type === 'Biosimilar CT (Patient)')
            .map(r => [r.period_name, r.start_milestone, r.start_offset_days, r.end_milestone, r.end_offset_days]))
          === JSON.stringify(SEED_PRULE.filter(r => r[0] === 'NewDrug CT').map(r => [r[1], r[2], r[3], r[4], r[5]])),
        pend: S.pending.length})""")
    check(st["n"] == 7 and st["same"] and st["pend"] == 7,
          "A CLINICAL TYPE WITH NO RULES IS OFFERED THE STANDARD ONES — laid out as seven "
          "ordinary unsaved rows", str(st))
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)
    pg.click("#t-gen [data-prtype='NewDrug CT']")
    pg.wait_for_timeout(500)
    pg.evaluate("""() => { const r = S.model.raw.PeriodRule.find(r => r.project_type === 'NewDrug CT'
          && r.period_name === 'Close-out (final)'); r.end_offset_days = 14; rebuild(true); renderKeepingTab(); }""")
    pg.wait_for_timeout(800)
    pg.select_option("#pruleCopy", "Biosimilar CT (Healthy)")
    pg.wait_for_timeout(1000)
    st = pg.evaluate("""() => { const k = t => JSON.stringify(S.model.raw.PeriodRule.filter(r => r.project_type === t)
          .map(r => [r.period_name, r.start_milestone, r.start_offset_days, r.end_milestone, r.end_offset_days]));
        return {same: k('NewDrug CT') === k('Biosimilar CT (Healthy)'), shown: S.genView.prule}; }""")
    check(st["same"] and st["shown"] == "Biosimilar CT (Healthy)",
          "A TYPE'S RULES CAN BE COPIED TO ANOTHER — which then reads the same", str(st))
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)

    bad = pg.evaluate("""() => { window.R70 = [];
        const add = o => { const r = newRow('PeriodRule', o); delete r.__new; R70.push(r); };
        add({project_type: 'NewDrug CT', period_name: 'Start-up', end_milestone: 'First SIV'});
        add({project_type: 'NewDrug CT', period_name: 'Planning', end_milestone: 'First SIV'});
        add({project_type: 'Others', period_name: 'Develop', end_milestone: 'Kick-off'});
        add({project_type: 'Others', period_name: 'Close', start_offset_days: 5, end_milestone: 'CTA submission'});
        rebuild(true);
        return S.model.findings.filter(f => f.rule === 'V-41').map(f => f.msg); }""")
    want = ["more than once", "is not one of the periods", "not in the milestone list",
            "from no milestone"]
    check(all(any(w in m for m in bad) for w in want) and len(bad) == 4,
          "V-41 SAYS WHAT A RULE CANNOT DO — given twice, a period of another type, a milestone "
          "nobody records, days from nothing", f"{len(bad)} finding(s)")
    pg.evaluate("""() => { S.model.raw.PeriodRule = S.model.raw.PeriodRule.filter(r => !R70.includes(r));
        rebuild(true); renderKeepingTab(); }""")
    pg.wait_for_timeout(800)

    # ------------------------------------------------------------------ 4
    print("\n4. Auto derivation, and a project with no periods")
    pg.set_input_files("#picker", str(FIX))          # the file as shipped, afresh
    pg.wait_for_timeout(3000)
    pid = pg.evaluate("""() => Object.keys(S.model.projects).find(p =>
        S.model.projects[p].project_type === 'NewDrug CT')""")
    pg.evaluate("""p => { const ms = S.model.raw.Milestone.find(m => m.project_id === p
        && m.milestone_name === 'First SIV'); if (ms) S.model.raw.Milestone.splice(S.model.raw.Milestone.indexOf(ms), 1);
        rebuild(true); S.selProj = p; renderAll(); showTab('t-proj'); }""", pid)
    pg.wait_for_timeout(900)
    before = pg.evaluate("p => JSON.stringify(S.model.raw.ProjectPeriod.filter(r => r.project_id === p))", pid)
    pg.click("#t-proj [data-panel='proj-per'] [data-act='autoper']")
    pg.wait_for_timeout(800)
    dv = pg.evaluate("""p => { const d = derivationPlan(S.model.projects[p], rawMilestones(p), S.model);
        const rows = [...document.querySelectorAll('#dvBody .dvt tbody tr')];
        return {open: el('derivedlg').open,
          shown: rows.map(tr => [...tr.children].slice(0, 3).map(td => td.textContent)),
          want: d.segs.map(g => [g.name, ymd(g.start), ymd(g.end)]),
          est: document.querySelectorAll('#dvBody .estpill').length,
          estWant: d.segs.reduce((n, g) => n + (g.est.start ? 1 : 0) + (g.est.end ? 1 : 0), 0),
          replace: el('dvBody').textContent.includes('replaces the')}; }""", pid)
    check(dv["open"] and dv["shown"] == dv["want"] and dv["replace"],
          "AUTO DERIVATION SHOWS EVERY PERIOD AND ITS DATES FIRST — and that it will replace "
          "the project's own", f"{len(dv['shown'])} periods")
    check(dv["est"] == dv["estWant"] and dv["est"] > 0,
          "with First SIV missing, the dates that rest on an estimate are marked",
          f"{dv['est']} estimate(s)")
    pg.click("#dvNo")
    pg.wait_for_timeout(500)
    check(pg.evaluate("p => JSON.stringify(S.model.raw.ProjectPeriod.filter(r => r.project_id === p))", pid)
          == before and pg.evaluate("S.pending.length") == 0, "Cancel changes nothing")
    pg.click("#t-proj [data-panel='proj-per'] [data-act='autoper']")
    pg.wait_for_timeout(800)
    pg.click("#dvYes")
    pg.wait_for_timeout(1200)
    got = pg.evaluate("""p => S.model.raw.ProjectPeriod.filter(r => r.project_id === p)
        .sort((a, b) => a.period_seq - b.period_seq).map(r => [r.period_name, ymd(r.period_start), ymd(r.period_end)])""", pid)
    check(got == dv["want"], "APPLY WRITES EXACTLY WHAT WAS SHOWN", f"{len(got)} rows")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)

    # Loaded with no periods: derived by the type's rules - and by the built-in rule once
    # the rules are taken away, so it is the rules that decide.
    st = pg.evaluate("""p => { S.model.raw.ProjectPeriod = S.model.raw.ProjectPeriod.filter(r => r.project_id !== p);
        rebuild(true);
        const ruled = S.model.periods[p].map(g => [g.period_name, ymd(g.period_start), ymd(g.period_end), !!g.__derived]);
        const want = derivationPlan(S.model.projects[p], S.model.milestones[p], S.model).segs.map(g => [g.name, ymd(g.start), ymd(g.end), true]);
        const keep = S.model.raw.PeriodRule.slice();
        S.model.raw.PeriodRule = S.model.raw.PeriodRule.filter(r => r.project_type !== 'NewDrug CT');
        rebuild(true);
        const builtin = S.model.periods[p].map(g => [g.period_name, ymd(g.period_start), ymd(g.period_end), !!g.__derived]);
        S.model.raw.PeriodRule = keep; rebuild(true);
        return {ruled, want, builtin}; }""", pid)
    check(st["ruled"] == st["want"] and st["ruled"],
          "A PROJECT WITH NO PERIODS OF ITS OWN IS DERIVED BY ITS TYPE'S RULES", f"{len(st['ruled'])} periods")
    check(st["builtin"] != st["ruled"] and st["builtin"],
          "   (and by the built-in rule once they are taken away, so the check above can fail)")
    other = pg.evaluate("""() => { const p = Object.keys(S.model.projects).find(k =>
          S.model.projects[k].project_type === 'Others');
        S.model.raw.ProjectPeriod = S.model.raw.ProjectPeriod.filter(r => r.project_id !== p);
        rebuild(true);
        const none = !S.model.periods[p] && S.model.findings.some(f => f.rule === 'V-12' && f.msg.includes(p));
        const ms = Object.keys(S.model.milestones[p] || {});
        const r = newRow('PeriodRule', {project_type: 'Others', period_name: 'Planning', end_milestone: ms[0] || 'CTA submission'});
        delete r.__new; rebuild(true);
        return {none, ruled: (S.model.periods[p] || []).map(g => g.period_name), ms}; }""")
    check(other["none"] and other["ruled"] == ["Planning"] if other["ms"] else other["none"],
          "an 'Others' project has no derived periods until its type has rules, then it does",
          str(other))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    b.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
