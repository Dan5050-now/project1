"""Change it where you read it, and a list of what is wrong with the plan (R-69).

Asked for from the field, six things:

  1. The project and person cards were for reading only. Every value on them is now the
     same editable cell the tables use - so the same value lists, checks, change log and
     Save - with the team, the milestones and the periods changed in place.
  2. The two assumption matrices (Standard period FTE, Role factors) can be typed into
     directly: a figure changes where it is read, and an empty place adds one.
  3. A project's or person's name in Resource by project / by person opens its card.
  4. A Data issues tab: every finding and every allocation problem in the whole plan, by
     level and category, sortable and groupable, with the fix - the row, editable - under
     each one, and a decision (Accept) for what is deliberate.
  5. The version information is the first section of General assumptions.
  6. The findings banner and the save bar are one band.

What is checked, with the fault put back where a guard could pass without working:

  * Card: a Details value typed in changes the row, is counted, and Save on the card
    keeps it; a value the rules refuse is put back and the refusal is shown IN the card;
    Tab goes on to the next field after the redraw; a milestone added from the card is
    this project's, at the next order number, with the caret in it; the team's weight
    and a person's capacity change in place.
  * Matrices: every figure is the cell over its own row; a change moves the standard the
    calculation reads; text is refused; an empty place - made by deleting a row - offers
    to create it with the same key, and Leave without change takes it away again; a
    place the type never has (a clinical type's Planning) offers nothing; no value list.
  * Overall: the names open cards, and the row still folds open from anywhere else.
  * Data issues: every finding is listed and nothing else but allocation; the count on
    the tab is what is open and worth a look, red while anything must be fixed; levels,
    categories, the search and the grouping narrow and arrange it; sorting turns round;
    a must-fix made by breaking a row shows its row with the field marked, is put right
    there, and leaves the list as Resolved; Accept takes a warning out of the count and
    into the change log, and Undo puts it back; the page's filters change nothing here;
    a standard-vs-staffed issue opens its months; an over-allocation shows the person's
    weights to change.
  * Version information first on General assumptions, and not at the head of the page.
  * The banner and the save bar side by side in one band - stacked when the band's
    layout is taken away, so the check can fail.

    python tools/test_r69.py
"""

import pathlib
import sys

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


def type_into(pg, sel, text, key="Tab"):
    """Into a cell the way a person does it: click, select what is there, type, leave."""
    pg.locator(sel).first.click()
    pg.keyboard.press("Control+A")
    pg.keyboard.type(text)
    pg.keyboard.press(key)
    pg.wait_for_timeout(1100)


with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME, headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3500)

    # ------------------------------------------------------------------ 6 and 5
    print("\n1. one band for the findings and the save bar; the version on its own tab")
    band = pg.evaluate("""() => { const b = el('databand'), n = el('banner'), e = el('editbar');
        return {inBand: n.parentNode === b && e.parentNode === b,
                sticky: !!b.closest('#stickybar'),
                topN: Math.round(n.getBoundingClientRect().top),
                topE: Math.round(e.getBoundingClientRect().top),
                leftN: n.getBoundingClientRect().left, leftE: e.getBoundingClientRect().left}; }""")
    check(band["inBand"] and band["sticky"], "THE BANNER AND THE SAVE BAR ARE ONE BAND, held at the "
          "top with the tabs", str(band))
    check(band["topN"] == band["topE"] and band["leftN"] < band["leftE"],
          "side by side: what the checks found, then what is waiting to be saved",
          f"tops {band['topN']} / {band['topE']}")
    stacked = pg.evaluate("""() => { const b = el('databand'); b.style.display = 'block';
        const t = [el('banner').getBoundingClientRect().top, el('editbar').getBoundingClientRect().top];
        b.style.display = ''; return t[0] !== t[1]; }""")
    check(stacked, "   (without the band's layout the two stack, so the check above can fail)")
    head_prov = pg.evaluate("() => { const p = el('prov'); return !!p && !p.closest('section.tab'); }")
    pg.click("nav button[data-tab='t-gen']")
    pg.wait_for_timeout(800)
    gv = pg.evaluate("""() => { const first = document.querySelector('#t-gen > .panel');
        return {panel: first && first.dataset.panel, h2: first && first.querySelector('h2').textContent,
                prov: !!first && !!first.querySelector('#prov'),
                ver: !!first && first.textContent.includes('v' + APP_VERSION)}; }""")
    check(not head_prov and gv["panel"] == "gen-ver" and gv["h2"] == "Version information"
          and gv["prov"] and gv["ver"],
          "VERSION INFORMATION IS THE FIRST SECTION OF GENERAL ASSUMPTIONS, not at the head of "
          "the page", str(gv))

    # ------------------------------------------------------------------ 3
    print("\n2. Overall: the names open their cards")
    pg.click("nav button[data-tab='t-overall']")
    pg.wait_for_timeout(800)
    links = pg.evaluate("""() => ({proj: document.querySelectorAll(
        "#t-overall tr.parent [data-card='project']").length,
        pers: document.querySelectorAll("#t-overall [data-card='person']").length,
        rows: document.querySelectorAll("#t-overall tr.parent").length})""")
    check(links["proj"] > 0 and links["pers"] > 0,
          "every project row of Resource by project, and the people, carry a link", str(links))
    pid = pg.evaluate("""() => document.querySelector("#t-overall tr.parent [data-card='project']")
        .dataset.cid""")
    exp0 = pg.evaluate("S.expanded.size")
    pg.locator(f"#t-overall tr.parent [data-card='project'][data-cid='{pid}']").first.click()
    pg.wait_for_timeout(900)
    st = pg.evaluate("() => ({open: el('carddlg').open, kind: CARD && CARD.kind, id: CARD && CARD.id, "
                     "exp: S.expanded.size})")
    check(st["open"] and st["kind"] == "project" and st["id"] == pid and st["exp"] == exp0,
          "CLICKING A PROJECT'S NAME OPENS ITS CARD — and does not fold the row open", str(st))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    pg.locator(f"#t-overall tr.parent:has([data-cid='{pid}']) th .sub").first.click()
    pg.wait_for_timeout(700)
    check(pg.evaluate("S.expanded.size") == exp0 + 1 and not pg.evaluate("el('carddlg').open"),
          "anywhere else on the row still folds it open")
    sid = pg.evaluate("""() => { const b = [...document.querySelectorAll("#t-overall [data-card='person']")]
        .find(x => x.offsetParent); return b && b.dataset.cid; }""")
    pg.locator(f"#t-overall [data-card='person'][data-cid='{sid}']").first.click()
    pg.wait_for_timeout(800)
    check(pg.evaluate("el('carddlg').open && CARD.kind === 'person' && CARD.id") == sid,
          "and a person's name opens theirs", sid or "")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)

    # ------------------------------------------------------------------ 1
    print("\n3. the card is where the record is changed")
    pg.evaluate("p => openCard('project', p)", pid)
    pg.wait_for_timeout(900)
    pm = "#cardBody td.ccell[data-sheet='Project'][data-col='planned_member_count']"
    was = pg.evaluate("p => S.model.raw.Project.find(r => r.project_id === p).planned_member_count", pid)
    new = 9 if was != 9 else 8
    type_into(pg, pm, str(new))
    st = pg.evaluate("""p => ({v: S.model.raw.Project.find(r => r.project_id === p).planned_member_count,
        n: S.pending.length, save: el('cardSave').textContent, prim: el('cardSave').classList.contains('primary'),
        mark: !!document.querySelector("#cardBody td.ccell.edited[data-col='planned_member_count']"),
        focus: document.activeElement && el('carddlg').contains(document.activeElement)
          && document.activeElement !== el('cardBody')})""", pid)
    check(st["v"] == new and st["n"] == 1, "A VALUE TYPED ON THE CARD CHANGES THE ROW, and is an "
          "unsaved change like any other", str(st))
    check(st["save"] == "Save 1 change" and st["prim"] and st["mark"],
          "the card's own Save says so, and the field is marked as changed", st["save"])
    check(st["focus"], "Tab goes on to the next field after the card is redrawn — the caret is not "
          "dropped on the page")
    end = "#cardBody td.ccell[data-sheet='Project'][data-col='end_date']"
    before = pg.evaluate(f"document.querySelector(\"{end}\").textContent")
    type_into(pg, end, "2000-01-01", "Enter")
    st = pg.evaluate(f"""() => ({{cell: document.querySelector("{end}").textContent,
        n: S.pending.length, msg: el('cardMsg').hidden ? '' : el('cardMsg').textContent,
        bad: el('cardMsg').classList.contains('bad')}})""")
    check(st["cell"] == before and st["n"] == 1 and st["bad"] and "rejected" in st["msg"],
          "A VALUE THE RULES REFUSE IS PUT BACK, and the refusal is said inside the card",
          st["msg"][:90])
    seq = pg.evaluate("p => nextSeq('Milestone', 'milestone_seq', 'project_id', p)", pid)
    pg.click("#cardBody [data-cardadd='Milestone']")
    pg.wait_for_timeout(1000)
    st = pg.evaluate("""p => { const a = document.activeElement, r = S.model.raw.Milestone
          .find(x => x.__row === +a.dataset.row);
        return {col: a.dataset.col, sheet: a.dataset.sheet, pid: r && r.project_id,
                seq: r && r.milestone_seq, n: S.pending.length}; }""", pid)
    check(st["sheet"] == "Milestone" and st["col"] == "milestone_name" and st["pid"] == pid
          and st["seq"] == seq and st["n"] == 2,
          "+ ADD ON MILESTONES MAKES ONE FOR THIS PROJECT, at the next order number, with the caret "
          "in it", str(st))
    pg.keyboard.type("Interim analysis")
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(1000)
    pg.keyboard.type("2026-09-15")
    pg.keyboard.press("Tab")
    pg.wait_for_timeout(1000)
    ms = pg.evaluate("""p => S.model.raw.Milestone.filter(m => m.project_id === p
        && m.milestone_name === 'Interim analysis').map(m => ymd(m.milestone_date))""", pid)
    check(ms == ["2026-09-15"], "its name and date typed straight in, one after the other", str(ms))
    w = "#cardBody td.ccell[data-sheet='Assignment'][data-col='person_weight']"
    arow = pg.evaluate(f"+document.querySelector(\"{w}\").dataset.row")
    type_into(pg, w, "0.66")
    check(pg.evaluate(f"S.model.raw.Assignment.find(a => a.__row === {arow}).person_weight") == 0.66,
          "a weight on the team changes in place")
    n = pg.evaluate("S.pending.length")
    pg.click("#cardSave")
    pg.wait_for_timeout(1500)
    st = pg.evaluate("() => ({n: S.pending.length, saved: S.saved, open: el('carddlg').open, "
                     "save: el('cardSave').disabled})")
    check(st["n"] == 0 and st["saved"] >= n and st["open"] and st["save"],
          "SAVE ON THE CARD KEEPS THEM — the page's own Save, with the card left open", str(st))
    pg.evaluate("s => openCard('person', s)", sid)
    pg.wait_for_timeout(800)
    cap = "#cardBody td.ccell[data-sheet='Person'][data-col='capacity_fte']"
    type_into(pg, cap, "0.8")
    check(pg.evaluate("s => S.model.raw.Person.find(r => r.person_id === s).capacity_fte", sid) == 0.8,
          "a person's capacity changes on their card")
    st = pg.evaluate("""() => [...document.querySelectorAll('#cardBody .csec')]
        .filter(s => s.querySelector('h3').textContent === 'Assignments')
        .map(s => s.querySelectorAll("td.ccell[data-sheet='Assignment']").length)[0]""")
    check((st or 0) > 0, "and their assignments are cells to type into", str(st))
    # Closed by its function: Escape goes to the calendar the next field opened first.
    pg.evaluate("closeCard()")
    pg.wait_for_timeout(300)
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(800)

    # ------------------------------------------------------------------ 2
    print("\n4. the assumption matrices")
    pg.click("nav button[data-tab='t-gen']")
    pg.wait_for_timeout(800)
    mx = pg.evaluate("""() => { const t = document.querySelector("#t-gen [data-panel='gen-pws'] table.grid-t");
        const cells = [...t.querySelectorAll('td.mx')];
        return {n: cells.length, rows: S.model.raw.PeriodFTEStandard.length,
          over: cells.every(td => { const r = S.model.raw.PeriodFTEStandard.find(x => x.__row === +td.dataset.row);
            return r && td.dataset.col === 'standard_fte' && td.isContentEditable
              && Math.abs((num(r.standard_fte) ?? NaN) - +td.textContent) < 0.006; })}; }""")
    check(mx["n"] == mx["rows"] and mx["over"],
          "EVERY FIGURE IN STANDARD PERIOD FTE IS THE CELL OVER ITS OWN ROW", str(mx))
    # A figure some project actually reads: its type and phase, and the standard it gets now.
    cell = pg.evaluate("""() => { for (const td of document.querySelectorAll("#t-gen [data-panel='gen-pws'] td.mx")){
          const r = S.model.raw.PeriodFTEStandard.find(x => x.__row === +td.dataset.row);
          const pr = Object.values(S.model.projects).find(p => p.project_type === r.project_type
            && p.clinical_phase === r.clinical_phase && stdWeight(S.model, p, r.period_name) === num(r.standard_fte));
          if (pr) return {row: r.__row, period: r.period_name, pid: pr.project_id};
        } return {row: null, period: null, pid: null}; }""")
    sel = f"#t-gen [data-panel='gen-pws'] td.mx[data-row='{cell['row']}']"
    type_into(pg, sel, "7.77")
    st = pg.evaluate("""c => ({raw: S.model.raw.PeriodFTEStandard.find(x => x.__row === c.row).standard_fte,
        std: c.pid ? stdWeight(S.model, S.model.projects[c.pid], c.period) : null, n: S.pending.length,
        list: !el('sugg').hidden,
        focus: !!document.activeElement.closest("[data-panel='gen-pws']")})""", cell)
    check(st["raw"] == 7.77 and st["n"] == 1, "A FIGURE TYPED IN THE MATRIX CHANGES ITS ROW", str(st))
    check(cell["pid"] is not None and st["std"] == 7.77,
          "and the standard the calculation reads for a project of that kind",
          f"{cell['pid']} {cell['period']}: {st['std']}")
    check(not st["list"] and st["focus"], "no list of every other figure over it, and Tab goes on "
          "along the matrix", str(st))
    type_into(pg, sel, "lots", "Enter")
    check(pg.evaluate("c => S.model.raw.PeriodFTEStandard.find(x => x.__row === c.row).standard_fte", cell)
          == 7.77 and "rejected" in pg.evaluate("el('banner').textContent"),
          "text that is not a figure is refused and the figure put back")
    bad = pg.evaluate("""() => [...document.querySelectorAll("#t-gen td.mk")].filter(td => {
        const k = JSON.parse(td.dataset.keys);
        return !(CLINICAL_TYPES.has(k.project_type) ? CLINICAL_PERIODS : OTHER_PERIODS)
          .includes(k.period_name); }).length""")
    check(bad == 0, "no empty place is offered for a period the type never has")
    held = pg.evaluate("""() => { const t = document.querySelector("#t-gen [data-panel='gen-pws'] table.grid-t");
        const heads = [...t.querySelectorAll('thead th')].map(th => th.textContent);
        let n = 0;
        for (const tr of t.querySelectorAll('tbody tr')) [...tr.children].forEach((td, i) => {
          if (OTHER_PERIODS.includes(heads[i]) && td.matches('td.z:not(.mk)') && /CT/.test(tr.textContent)) n++; });
        return n; }""")
    check(held > 0, "   (those places are there - a clinical type's Planning, Develop, Close - and offer "
          "only a dot, so the check above can fail)", f"{held} held back")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(800)
    gone = pg.evaluate("""() => { const r = S.model.raw.PeriodFTEStandard.find(x =>
          CLINICAL_TYPES.has(x.project_type) && x.period_name === 'Start-up');
        const keep = {project_type: r.project_type, clinical_phase: r.clinical_phase,
          work_scope_type: r.work_scope_type ?? null, period_name: r.period_name, v: r.standard_fte};
        deleteRow('PeriodFTEStandard', r.__row); return keep; }""")
    pg.wait_for_timeout(1000)
    mk = pg.evaluate("""g => [...document.querySelectorAll("#t-gen [data-panel='gen-pws'] td.mk")]
        .map(td => JSON.parse(td.dataset.keys)).filter(k => k.project_type === g.project_type
          && k.clinical_phase === g.clinical_phase && (k.work_scope_type ?? null) === g.work_scope_type
          && k.period_name === g.period_name).length""", gone)
    check(mk == 1, "A ROW TAKEN AWAY LEAVES AN EMPTY PLACE that offers to make it again, with its key",
          str(gone))
    n0 = pg.evaluate("S.model.raw.PeriodFTEStandard.length")
    pg.evaluate("""g => { const td = [...document.querySelectorAll("#t-gen [data-panel='gen-pws'] td.mk")]
        .find(td => { const k = JSON.parse(td.dataset.keys); return k.project_type === g.project_type
          && k.clinical_phase === g.clinical_phase && (k.work_scope_type ?? null) === g.work_scope_type
          && k.period_name === g.period_name; });
        td.setAttribute('data-r69', '1'); }""", gone)
    type_into(pg, "#t-gen td.mk[data-r69]", "3.33")
    st = pg.evaluate("""g => { const r = S.model.raw.PeriodFTEStandard.filter(x =>
          x.project_type === g.project_type && x.clinical_phase === g.clinical_phase
          && (x.work_scope_type ?? null) === g.work_scope_type && x.period_name === g.period_name);
        return {n: S.model.raw.PeriodFTEStandard.length, rows: r.length, v: r[0] && r[0].standard_fte,
                draft: r[0] && !!r[0].__new, last: S.pending[S.pending.length - 1].col}; }""", gone)
    check(st["n"] == n0 + 1 and st["rows"] == 1 and st["v"] == 3.33 and not st["draft"]
          and st["last"] == "(new row)",
          "A FIGURE TYPED INTO IT MAKES THE ROW — the same key, complete, and counted at once", str(st))
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)
    back = pg.evaluate("""g => S.model.raw.PeriodFTEStandard.filter(x => x.project_type === g.project_type
        && x.clinical_phase === g.clinical_phase && (x.work_scope_type ?? null) === g.work_scope_type
        && x.period_name === g.period_name).map(x => x.standard_fte)""", gone)
    check(back == [gone["v"]], "Leave without change puts the original row back", str(back))
    rf = pg.evaluate("""() => { const td = document.querySelector("#t-gen [data-panel='gen-rf'] td.mx");
        return {row: +td.dataset.row, sheet: td.dataset.sheet, col: td.dataset.col}; }""")
    type_into(pg, f"#t-gen [data-panel='gen-rf'] td.mx[data-row='{rf['row']}']", "1.23")
    check(rf["sheet"] == "RoleFactor" and rf["col"] == "role_factor"
          and pg.evaluate(f"S.model.raw.RoleFactor.find(x => x.__row === {rf['row']}).role_factor") == 1.23,
          "a role factor changes in its matrix too", str(rf))
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(800)

    # ------------------------------------------------------------------ 4
    print("\n5. the Data issues tab")
    tabs = pg.eval_on_selector_all("nav button[data-tab]", "bs => bs.map(b => b.dataset.tab)")
    check(tabs[-1] == "t-issues", "a tab of its own, after the four", " · ".join(tabs))
    pg.click("nav button[data-tab='t-issues']")
    pg.wait_for_timeout(900)
    st = pg.evaluate("""() => { const all = issues(), open = all.filter(i => !i.acc);
        const want = open.filter(i => ['must','keep','warn'].includes(i.lv)).length;
        return {rows: document.querySelectorAll('#t-issues tr.iss').length, all: all.length,
          findings: S.model.findings.length, load: all.filter(i => i.load).length,
          badge: el('issueCount').hidden ? 0 : +el('issueCount').textContent, want,
          red: el('issueCount').classList.contains('must')}; }""")
    check(st["rows"] == st["all"] and st["all"] == st["findings"] + st["load"],
          "EVERY FINDING IN THE PLAN IS LISTED, and the allocation problems beside them", str(st))
    check(st["badge"] == st["want"] and st["badge"] > 0 and not st["red"],
          "the tab's count is what is open and worth a look — not red while nothing must be fixed",
          str(st["badge"]))
    over = pg.evaluate("""() => { const M = S.model, C = S.calc, nk = Math.max(nowKey(), C.lo), out = [];
        for (const sid of Object.keys(M.people)){
          for (let k = nk; k <= C.hi; k++) if ((C.persMonth.get(sid + '|' + k) || 0) > M.OVER){ out.push(sid); break; }
        }
        const got = issues().filter(i => i.load === 'over').map(i => i.sid);
        return {want: out.sort(), got: got.sort()}; }""")
    check(over["want"] == over["got"] and over["got"],
          "everybody above the ceiling from this month on has an issue, and nobody else",
          f"{len(over['got'])} people")
    pg.evaluate("() => { const f = S.f.proj; f.add(Object.keys(S.model.projects)[0]); renderKeepingTab(); }")
    pg.wait_for_timeout(900)
    check(pg.evaluate("document.querySelectorAll('#t-issues tr.iss').length") == st["rows"],
          "NOT NARROWED BY THE PAGE'S FILTERS — an issue is in the file whatever the page shows")
    pg.evaluate("() => { S.f.proj.clear(); renderKeepingTab(); }")
    pg.wait_for_timeout(900)

    lv = pg.evaluate("() => issues().filter(i => !i.acc && i.lv === 'note').length")
    pg.click("#t-issues [data-iss-lv='note']")
    pg.wait_for_timeout(500)
    st = pg.evaluate("""() => ({rows: document.querySelectorAll('#t-issues tr.iss').length,
        lvs: [...new Set([...document.querySelectorAll('#t-issues tr.iss')].map(t => t.className.match(/lv-(\\w+)/)[1]))],
        on: document.querySelector("#t-issues [data-iss-lv='note']").getAttribute('aria-pressed')})""")
    check(st["rows"] == lv and st["lvs"] == ["note"] and st["on"] == "true",
          "A LEVEL CHOSEN SHOWS ONLY THAT LEVEL", str(st))
    pg.click("#t-issues [data-iss-clear]")
    pg.wait_for_timeout(400)
    pg.click("#t-issues [data-iss-cat='load']")
    pg.wait_for_timeout(400)
    cats = pg.evaluate("""() => [...new Set([...document.querySelectorAll('#t-issues tr.iss')]
        .map(t => issues().find(i => i.id === t.dataset.iss).cat))]""")
    check(cats == ["load"], "a category the same", str(cats))
    pg.click("#t-issues [data-iss-clear]")
    pg.wait_for_timeout(400)
    who = pg.evaluate("() => issues().find(i => i.load).home.label")
    pg.fill("#issueQ", who)
    pg.wait_for_timeout(400)
    st = pg.evaluate("""q => ({rows: [...document.querySelectorAll('#t-issues tr.iss')]
          .map(t => issues().find(i => i.id === t.dataset.iss).find.includes(q.toLowerCase())),
        focus: document.activeElement.id})""", who)
    check(st["rows"] and all(st["rows"]) and st["focus"] == "issueQ",
          "the search narrows it as it is typed, and keeps its caret", f"'{who}': {len(st['rows'])} row(s)")
    pg.fill("#issueQ", "")
    pg.wait_for_timeout(300)
    pg.click("#t-issues [data-iss-group='rec']")
    pg.wait_for_timeout(500)
    st = pg.evaluate("""() => { const heads = document.querySelectorAll('#t-issues tr.igrp').length;
        const homes = new Set(issues().filter(i => !i.acc).map(i => i.home.kind + '|' + i.home.id)).size;
        return {heads, homes}; }""")
    check(st["heads"] == st["homes"] and st["heads"] > 1, "GROUPED BY RECORD — one heading for each "
          "project, person or table with something open", str(st))
    pg.click("#t-issues [data-iss-group='level']")
    pg.wait_for_timeout(300)
    pg.click("#t-issues [data-iss-group='none']")
    pg.wait_for_timeout(300)
    first = pg.evaluate("() => document.querySelector('#t-issues tr.iss').className")
    pg.click("#t-issues [data-iss-sort='level']")
    pg.wait_for_timeout(300)
    last = pg.evaluate("() => document.querySelector('#t-issues tr.iss').className")
    check("lv-warn" in first and "lv-note" in last,
          "sorting by level, and again the other way round", f"{first.split()[1]} -> {last.split()[1]}")
    pg.click("#t-issues [data-iss-group='level']")
    pg.wait_for_timeout(300)

    # A must-fix, made the way a file arrives with one: a clinical project's phase taken
    # out underneath the editor, which would never let it be typed.
    brk = pg.evaluate("""() => { const r = S.model.raw.Project.find(p => CLINICAL_TYPES.has(p.project_type));
        r.clinical_phase = null; rebuild(true); renderKeepingTab(); return r.project_id; }""")
    pg.wait_for_timeout(1000)
    st = pg.evaluate("""p => { const it = issues().find(i => i.rule === 'V-19' && i.sheet === 'Project'
          && i.rec.project.includes(p));
        return {it: !!it, lv: it && it.lv, red: el('issueCount').classList.contains('must'),
          first: document.querySelector('#t-issues tr.iss').className,
          acc: it ? !!document.querySelector(`#t-issues [data-iss-acc="${it.id}"]`) : null, id: it && it.id}; }""", brk)
    check(st["it"] and st["lv"] == "must" and st["red"] and "lv-must" in st["first"],
          "A MUST-FIX GOES TO THE TOP, AND THE TAB'S COUNT TURNS RED", str(st))
    check(st["acc"] is False, "it cannot be accepted — only put right")
    pg.click(f"#t-issues [data-iss-open='{st['id']}']")
    pg.wait_for_timeout(600)
    ed = pg.evaluate("""() => { const x = document.querySelector('#t-issues tr.issx');
        const f = x && x.querySelector("td.ccell.focus[data-sheet='Project'][data-col='clinical_phase']");
        return {open: !!x, focus: !!f, cols: x ? [...x.querySelectorAll('.ied th')].map(t => t.textContent) : []}; }""")
    check(ed["open"] and ed["focus"], "FIX HERE SHOWS THE PROJECT'S ROW, the field it is about marked",
          " · ".join(ed["cols"]))
    type_into(pg, "#t-issues tr.issx td.ccell[data-col='clinical_phase']", "Phase 2", "Enter")
    st = pg.evaluate("""p => ({left: issues().some(i => i.rule === 'V-19' && i.rec.project.includes(p)),
        done: (document.querySelector('#t-issues .idone') || {}).textContent || '',
        red: el('issueCount').classList.contains('must'), n: S.pending.length})""", brk)
    check(not st["left"] and "Resolved" in st["done"] and not st["red"] and st["n"] == 1,
          "PUT RIGHT THERE, IT LEAVES THE LIST — said as Resolved — as an ordinary unsaved change",
          st["done"][:70])
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(900)
    pg.evaluate("p => { S.model.raw.Project.find(r => r.project_id === p).clinical_phase = 'Phase 2'; "
                "rebuild(true); renderKeepingTab(); }", brk)
    pg.wait_for_timeout(900)

    warn = pg.evaluate("() => issues().find(i => i.lv === 'warn').id")
    b0 = pg.evaluate("+el('issueCount').textContent")
    e0 = pg.evaluate("S.events.length")
    pg.click(f"#t-issues [data-iss-acc='{warn}']")
    pg.wait_for_timeout(500)
    st = pg.evaluate("""w => { const it = issues().find(i => i.id === w);
        const grp = [...document.querySelectorAll('#t-issues tr.igrp')].pop();
        const ev = S.events[S.events.length - 1];
        return {acc: !!(it && it.acc), badge: +el('issueCount').textContent, grp: grp.textContent,
          ev: ev && ev.event, kept: ev && ev.kept, n: S.events.length}; }""", warn)
    check(st["acc"] and st["badge"] == b0 - 1 and st["grp"].startswith("Accepted"),
          "ACCEPT TAKES A WARNING OUT OF THE OPEN COUNT, into Accepted", str(st))
    check(st["n"] == e0 + 1 and st["kept"] == "yes" and "accepted" in st["ev"],
          "and the decision goes into the change log as kept by the user", str(st["ev"]))
    pg.click(f"#t-issues [data-iss-unacc='{warn}']")
    pg.wait_for_timeout(500)
    check(pg.evaluate("+el('issueCount').textContent") == b0 and
          not pg.evaluate("w => !!issues().find(i => i.id === w).acc", warn),
          "Undo puts it back")

    std = pg.evaluate("() => (issues().find(i => i.cat === 'std') || {}).id")
    if std:
        pg.click(f"#t-issues [data-iss-open='{std}']")
        pg.wait_for_timeout(600)
        rows = pg.evaluate("() => document.querySelectorAll('#t-issues tr.issx tr.gaprow[data-gap]').length")
        pg.locator("#t-issues tr.issx tr.gaprow[data-gap]").first.click()
        pg.wait_for_timeout(800)
        check(rows > 0 and pg.evaluate("el('gapdlg').open"),
              "A STANDARD-VS-STAFFED ISSUE LISTS ITS MONTHS, each opening the month and its review",
              f"{rows} month(s)")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)
    else:
        check(False, "the fixture has a standard-vs-staffed issue")
    # A milestone outside the standard list (V-11) - put in underneath the editor, as a
    # file brings one - is reported against the project's milestones as a whole.
    mp = pg.evaluate("""() => { const p = Object.keys(S.model.projects).find(k =>
          S.model.raw.Milestone.filter(m => m.project_id === k).length > 2);
        const r = newRow('Milestone', {project_id: p, milestone_name: 'Board review',
          milestone_date: new Date(Date.UTC(2027, 2, 1)), milestone_seq: 99});
        delete r.__new; rebuild(true); renderKeepingTab(); return p; }""")
    pg.wait_for_timeout(900)
    v11 = pg.evaluate("""p => (issues().find(i => i.rule === 'V-11' && i.sheet === 'Milestone'
        && i.rec.project.includes(p) && i.msg.includes('Board review')) || {}).id""", mp)
    if v11:
        pg.click(f"#t-issues [data-iss-open='{v11}']")
        pg.wait_for_timeout(600)
    hits = pg.evaluate("""() => ({hit: [...document.querySelectorAll('#t-issues tr.issx .ied tr.hit')]
        .map(tr => tr.querySelector("[data-col='milestone_name']").textContent),
        rows: document.querySelectorAll('#t-issues tr.issx .ied tbody tr').length})""")
    check(bool(v11) and hits["hit"] == ["Board review"] and hits["rows"] > 2,
          "AMONG A PROJECT'S MILESTONES, THE ONE THE ISSUE NAMES IS MARKED", str(hits))
    pg.evaluate("""() => { const i = S.model.raw.Milestone.findIndex(m => m.milestone_name === 'Board review');
        S.model.raw.Milestone.splice(i, 1); rebuild(true); renderKeepingTab(); }""")
    pg.wait_for_timeout(900)
    ov = pg.evaluate("() => issues().find(i => i.load === 'over')")
    pg.click(f"#t-issues [data-iss-open='{ov['id']}']")
    pg.wait_for_timeout(600)
    st = pg.evaluate("""s => { const x = document.querySelector('#t-issues tr.issx');
        const w = [...x.querySelectorAll("td.ccell[data-sheet='Assignment'][data-col='person_weight']")];
        return {n: w.length, want: S.model.raw.Assignment.filter(a => a.person_id === s).length}; }""", ov["sid"])
    check(st["n"] == st["want"] and st["n"] > 0,
          "AN OVER-ALLOCATION SHOWS THE PERSON'S ASSIGNMENTS, their weights to change", str(st))
    open_link = pg.locator("#t-issues tr.issx [data-card='person']").first
    open_link.click()
    pg.wait_for_timeout(800)
    check(pg.evaluate("el('carddlg').open && CARD.id") == ov["sid"], "and opens their card")
    pg.evaluate("closeCard()")
    pg.wait_for_timeout(300)
    pg.click("nav button[data-tab='t-overall']")
    pg.wait_for_timeout(600)
    lk = pg.evaluate("() => ({n: (el('openIssuesN') || {}).textContent, badge: el('issueCount').textContent})")
    pg.click("#openIssues")
    pg.wait_for_timeout(700)
    check(pg.evaluate("S.tab") == "t-issues" and lk["n"] == f" ({lk['badge']})",
          "THE BAND KEEPS THE WAY TO THE TAB, with the open count, whatever it last said", str(lk))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    b.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
