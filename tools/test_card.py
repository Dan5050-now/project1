"""The whole window, and one project or one person on one card (R-67).

Asked for from the field: the page used all of a wide screen except two broad grey
margins; and on the two source-data tabs, clicking a project's or a person's NAME should
open everything about that one, top to bottom, in a single scrolling pop-up.

What is checked:

  * THE PAGE IS THE WINDOW. No 1400px column: the content runs edge to edge less a
    gutter, and the charts are DRAWN to the width they get - their text stays the size
    it was designed at instead of being blown up 1.6x across a 1920px screen. Put the
    old fixed width back and the measured text grows past that, so the check can fail.
    A narrower window redraws them, and the page never scrolls sideways.
  * A saved name is a link; a row still being typed keeps a plain cell.
  * The card: the record's name and identifier, the headline figures, both charts drawn
    to the card's width, the team or the assignments, milestones, periods, the open
    issues, and EVERY field the table holds, each with the value the table holds.
  * Pop-ups work inside it. A modal sits above the page's pop-up layer, so the pop-up has
    to move into the dialog - shown by putting it back on the body and watching the
    dialog cover it.
  * Across and back: a person on a project's card opens theirs, Back returns; Previous
    and Next walk the table's order; "Show on" closes it onto the row; Escape and the
    backdrop close it.
  * Renaming still works, through the pencil or F2, with the same commit and the same
    Escape as any cell - and the card follows an edit made while it is open.

    python tools/test_card.py
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


# How big a chart's axis text comes out on screen, against the 11.5 it is set at.
TEXT_SCALE = """sel => { const t = document.querySelector(sel + ' svg.chart text.ax');
  if (!t) return null;
  const svg = t.ownerSVGElement, r = svg.getBoundingClientRect();
  return r.width / svg.viewBox.baseVal.width; }"""
P = "#t-proj .data-t[data-sheet='Project']"
Q = "#t-pers .data-t[data-sheet='Person']"

print("R-67 — the whole window, and a card for one project or one person")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3500)

    # ------------------------------------------------------------------ 1
    print("\n1. the page is the window")
    w = pg.evaluate("""() => { const w = document.querySelector('.wrap'),
        p = document.querySelector('#t-overall .panel');
        return {max: getComputedStyle(w).maxWidth, wrap: w.getBoundingClientRect().width,
                vw: document.documentElement.clientWidth, panel: p.getBoundingClientRect().width}; }""")
    check(w["max"] == "none" and abs(w["wrap"] - w["vw"]) < 1,
          "NO 1400px COLUMN — the content runs the width of the window", str(w))
    check(w["panel"] > w["vw"] - 80, "and a panel takes all of it but the gutters",
          f"panel {w['panel']:.0f}px of {w['vw']}px")
    sc = pg.evaluate(TEXT_SCALE, '#t-overall .panel[data-panel="trend"]')
    check(sc is not None and 0.9 <= sc <= 1.1,
          "THE CHARTS ARE DRAWN TO THAT WIDTH — their text at the size it was designed",
          f"scale {sc:.2f}" if sc else "no chart")
    # The fault put back: a chart drawn to its own fixed width, stretched to the panel.
    old = pg.evaluate("""() => { const box = document.querySelector(
          '#t-overall .panel[data-panel="trend"] .scrollx');
        const was = box.innerHTML;
        box.innerHTML = withRoom(0, () => projectLines(activeProjects()));
        const t = box.querySelector('svg.chart'), r = t.getBoundingClientRect();
        const s = r.width / t.viewBox.baseVal.width;
        box.innerHTML = was;
        return s; }""")
    check(old > 1.3, "   (drawn at its fixed width instead, the same chart's text is scaled up "
          "— the oversized text this replaces)", f"scale {old:.2f}")
    pg.set_viewport_size({"width": 1280, "height": 900})
    pg.wait_for_timeout(1200)
    sc2 = pg.evaluate(TEXT_SCALE, '#t-overall .panel[data-panel="trend"]')
    wide = pg.evaluate("document.documentElement.scrollWidth - innerWidth")
    check(sc2 is not None and 0.9 <= sc2 <= 1.1 and wide <= 0,
          "a narrower window redraws them, and the page never scrolls sideways",
          f"scale {sc2:.2f}, page overflow {wide}px" if sc2 else "no chart")
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.wait_for_timeout(1200)

    # ------------------------------------------------------------------ 2
    print("\n2. a saved name is a link")
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(1000)
    links = pg.evaluate(f"""() => [...document.querySelectorAll("{P} tbody tr[data-id]")]
        .filter(tr => S.model.projects[tr.dataset.id]).map(tr => {{
          const td = tr.querySelector("td[data-col='project_name']");
          return !!td.querySelector('.namelink') && !td.isContentEditable; }})""")
    check(links and all(links), "EVERY SAVED PROJECT'S NAME IS A LINK, and not a caret target",
          f"{sum(links)} of {len(links)}")
    pg.click('nav button[data-tab="t-pers"]')
    pg.wait_for_timeout(900)
    plinks = pg.evaluate(f"""() => [...document.querySelectorAll("{Q} tbody tr[data-id]")]
        .filter(tr => S.model.people[tr.dataset.id])
        .map(tr => !!tr.querySelector("td[data-col='person_name'] .namelink"))""")
    check(plinks and all(plinks), "and every saved person's", f"{sum(plinks)} of {len(plinks)}")
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(900)
    pg.locator(f"{P} button[data-ins]").first.click()
    pg.wait_for_timeout(900)
    draft = pg.evaluate(f"""() => {{ const r = S.model.raw.Project.find(r => r.__new);
        const td = document.querySelector("{P} tr[data-id='" + r.project_id + "'] td[data-col='project_name']");
        return {{link: !!td.querySelector('.namelink'), ce: td.getAttribute('contenteditable')}}; }}""")
    check(not draft["link"] and draft["ce"] == "true",
          "a row still being typed keeps the plain cell — it has no record to show yet", str(draft))
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(1000)

    # ------------------------------------------------------------------ 3
    print("\n3. the project's card")
    pid = pg.evaluate(f"""() => [...document.querySelectorAll("{P} tbody tr[data-id]")]
        .map(tr => tr.dataset.id).filter(id => S.model.projects[id])[2]""")
    pg.locator(f"{P} tr[data-id='{pid}'] .namelink").click()
    pg.wait_for_timeout(900)
    st = pg.evaluate("""() => ({open: !!el('carddlg') && el('carddlg').open, card: CARD && CARD.id,
        sel: S.selProj, title: el('cardTitle').textContent,
        id: (document.querySelector('#cardHead .idchip') || {}).textContent})""")
    name = pg.evaluate("p => S.model.projects[p].project_name", pid)
    check(st["open"] and st["card"] == pid and st["title"] == name and st["id"] == pid,
          "CLICKING THE NAME OPENS THAT PROJECT'S CARD, named and identified", str(st))
    check(st["sel"] == pid and pg.locator(f"{P} tr.sel[data-id='{pid}']").count() == 1,
          "and selects its row, as any click on the row does", str(st["sel"]))
    secs = pg.eval_on_selector_all("#cardBody .csec h3", "hs => hs.map(h => h.textContent)")
    # R-69: the record comes first, now that it is where the record is changed.
    want = ["Details", "Team", "Milestones", "Periods", "Monthly resource", "Timeline",
            "Issues — standard vs staffed"]
    check(secs == want, "the sections, top to bottom", " · ".join(secs))
    check(pg.locator("#cardBody .kpis .kpi").count() == 6, "six headline figures above them")
    n_asg = pg.evaluate("p => S.model.assignments.filter(a => a.project_id === p).length", pid)
    team_rows = pg.evaluate("""() => { const s = [...document.querySelectorAll('#cardBody .csec')]
        .find(s => s.querySelector('h3').textContent === 'Team');
        return s ? s.querySelectorAll('tbody tr').length : -1; }""")
    check(team_rows == n_asg and team_rows > 0, "the team: one row per assignment",
          f"{team_rows} rows, {n_asg} assignments")
    # Each one the editable cell over the project's own row (R-69) - estimation_type
    # excepted, which has one way in and shows it as a button beside the value.
    fields = pg.evaluate("""p => { const r = S.model.raw.Project.find(x => x.project_id === p), out = [];
        const got = Object.fromEntries([...document.querySelectorAll('#cardBody .fgroup .ftab tr')]
          .map(tr => [tr.querySelector('th').textContent, tr.querySelector('td')]));
        for (const c of entryCols('Project')){
          const td = got[COLUMN_LABEL[c] || c];
          if (!td){ out.push(c + ': missing'); continue; }
          if (c === 'estimation_type'){
            if (!td.textContent.includes(r.estimation_type || 'automatic')
                || !td.querySelector('[data-act="estswitch"]')) out.push(c + ': ' + td.textContent);
            continue;
          }
          const v = r[c], want = v instanceof Date ? ymd(v) : (v === null || v === undefined ? '' : String(v));
          if (td.textContent !== want) out.push(c + ': ' + td.textContent + ' != ' + want);
          if (!td.isContentEditable || td.dataset.sheet !== 'Project' || td.dataset.col !== c
              || +td.dataset.row !== r.__row) out.push(c + ': not the editable cell over its row');
        }
        return {n: entryCols('Project').length, bad: out}; }""", pid)
    check(not fields["bad"], f"EVERY ONE OF THE {fields['n']} FIELDS, with the value the table holds "
          "— each one a cell to type into, over the project's own row", "; ".join(fields["bad"][:3]))
    ch = pg.evaluate("""() => { const b = el('cardBody'), cs = getComputedStyle(b);
        const room = b.clientWidth - 2 * parseFloat(cs.paddingLeft) - 18;
        return {n: b.querySelectorAll('svg.chart').length, room,
          vb: [...b.querySelectorAll('svg.chart')].map(s => s.viewBox.baseVal.width),
          tall: b.scrollHeight > b.clientHeight + 50,
          fits: el('carddlg').getBoundingClientRect().height <= innerHeight * 0.93}; }""")
    check(ch["n"] == 2 and all(v >= ch["room"] - 1 for v in ch["vb"]),
          "both charts, drawn to the card's own width", f"viewBox {ch['vb']} for {ch['room']:.0f}")
    check(ch["tall"] and ch["fits"], "ONE PAGE, READ DOWNWARDS — the card scrolls inside a dialog "
          "that fits the window", str({k: ch[k] for k in ('tall', 'fits')}))

    # ------------------------------------------------------------------ 4
    print("\n4. pop-ups inside it")
    # The charts follow the record since R-69, so the first one is scrolled to.
    pg.evaluate("document.querySelector('#cardBody svg.chart').scrollIntoView({block: 'center'})")
    pg.wait_for_timeout(300)
    box = pg.locator("#cardBody svg.chart rect[data-tip]").first.bounding_box()
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] - 2)
    pg.wait_for_timeout(300)
    # Whether the pop-up is what is drawn at its own centre. It takes no pointer events,
    # so for the moment of asking it is given them: elementFromPoint passes straight
    # through anything that has none.
    pg.evaluate("""() => { window.onTopNow = t => { t.style.pointerEvents = 'auto';
        const r = t.getBoundingClientRect();
        const at = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
        t.style.pointerEvents = ''; return !!at && t.contains(at); }; }""")
    tip = pg.evaluate("""() => { const t = el('tip');
        return {shown: !t.hidden, host: t.parentNode.id, onTop: onTopNow(t)}; }""")
    check(tip["shown"] and tip["host"] == "carddlg" and tip["onTop"],
          "A CHART'S POP-UP SHOWS ON TOP OF THE CARD — it is moved into the dialog", str(tip))
    hid = pg.evaluate("() => { const t = el('tip'); document.body.appendChild(t); return onTopNow(t); }")
    check(not hid, "   (left on the body, the same pop-up is drawn behind the dialog)",
          f"visible={hid}")
    pg.mouse.move(5, 5)
    pg.wait_for_timeout(200)

    # ------------------------------------------------------------------ 5
    print("\n5. across, back, and through the list")
    person = pg.evaluate("""() => { const b = document.querySelector(
        "#cardBody .plink[data-card='person']"); return b.dataset.cid; }""")
    pg.locator("#cardBody .plink[data-card='person']").first.click()
    pg.wait_for_timeout(700)
    pc = pg.evaluate("""() => ({card: CARD.kind + ':' + CARD.id, back: !el('cardBack').hidden,
        title: el('cardTitle').textContent,
        projects: [...document.querySelectorAll("#cardBody .plink[data-card='project']")]
          .map(b => b.dataset.cid)})""")
    check(pc["card"] == f"person:{person}" and pc["back"] and pid in pc["projects"],
          "A PERSON ON THE TEAM OPENS THEIR CARD, which lists the project they came from",
          f"{pc['title']} — {len(pc['projects'])} project(s)")
    secs = pg.eval_on_selector_all("#cardBody .csec h3", "hs => hs.map(h => h.textContent)")
    check(secs == ["Details", "Assignments", "Monthly load", "Project timeline"],
          "a person's sections", " · ".join(secs))
    pg.click("#cardBack")
    pg.wait_for_timeout(600)
    check(pg.evaluate("CARD.kind + ':' + CARD.id") == f"project:{pid}"
          and pg.evaluate("el('cardBack').hidden"), "Back returns to the project")
    order = pg.evaluate(f"""() => [...document.querySelectorAll("{P} tbody tr[data-id]")]
        .map(tr => tr.dataset.id).filter(id => S.model.projects[id])""")
    pg.keyboard.press("ArrowRight")
    pg.wait_for_timeout(600)
    nxt = pg.evaluate("CARD.id")
    check(nxt == order[order.index(pid) + 1],
          "NEXT IS THE NEXT ROW OF THE TABLE — the arrow key steps to it", f"{pid} -> {nxt}")
    pg.evaluate("p => openCard('project', p)", order[0])
    pg.wait_for_timeout(500)
    check(pg.evaluate("el('cardPrev').disabled") and not pg.evaluate("el('cardNext').disabled"),
          "and Previous is off on the first row", pg.inner_text("#cardPos"))

    pg.locator("#cardBody .plink[data-card='person']").first.click()
    pg.wait_for_timeout(600)
    sid = pg.evaluate("CARD.id")
    pg.click("#cardGo")
    pg.wait_for_timeout(1200)
    go = pg.evaluate("""() => ({open: el('carddlg').open, tab: S.tab, sel: S.selPers})""")
    check(not go["open"] and go["tab"] == "t-pers" and go["sel"] == sid
          and pg.locator(f"{Q} tr.sel[data-id='{sid}']").count() == 1,
          "SHOW ON SOURCE DATA (PERSON) closes it onto that person's row", str(go))
    pg.locator(f"{Q} tr[data-id='{sid}'] .namelink").click()
    pg.wait_for_timeout(600)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    esc_closed = not pg.evaluate("el('carddlg').open")
    pg.locator(f"{Q} tr[data-id='{sid}'] .namelink").click()
    pg.wait_for_timeout(600)
    pg.mouse.click(6, 540)
    pg.wait_for_timeout(400)
    check(esc_closed and not pg.evaluate("el('carddlg').open"),
          "Escape closes it, and so does a click beside it")

    # ------------------------------------------------------------------ 6
    print("\n6. renaming, and the card following an edit")
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(900)
    rid = order[1]
    cell = pg.locator(f"{P} tr[data-id='{rid}'] td[data-col='project_name']")
    was = pg.evaluate("p => S.model.projects[p].project_name", rid)
    cell.hover()
    cell.locator(".renbtn").click()
    pg.wait_for_timeout(400)
    st = pg.evaluate("""() => { const a = document.activeElement;
        return {col: a.dataset.col, ce: a.isContentEditable, text: a.textContent,
                list: !el('sugg').hidden}; }""")
    check(st["col"] == "project_name" and st["ce"] and st["text"] == was and st["list"],
          "THE PENCIL MAKES IT THE ORDINARY CELL — the plain name, the caret, the value list", str(st))
    n0 = pg.evaluate("S.pending.length")
    pg.keyboard.press("Control+A")
    pg.keyboard.type(was + " (renamed)")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1300)
    rn = pg.evaluate("""p => ({raw: S.model.raw.Project.find(r => r.project_id === p).project_name,
        link: (document.querySelector("#t-proj .data-t[data-sheet='Project'] tr[data-id='" + p
               + "'] .namelink") || {}).textContent, pending: S.pending.length})""", rid)
    check(rn["raw"] == was + " (renamed)" and rn["link"] == rn["raw"] and rn["pending"] == n0 + 1,
          "Enter commits it as one pending edit, and the link comes back with the new name", str(rn))
    cell.hover()
    cell.locator(".renbtn").click()
    pg.wait_for_timeout(300)
    pg.keyboard.type("zzz")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    ec = pg.evaluate("""p => { const td = document.querySelector(
          "#t-proj .data-t[data-sheet='Project'] tr[data-id='" + p + "'] td[data-col='project_name']");
        return {link: !!td.querySelector('.namelink'), ce: td.isContentEditable,
                pending: S.pending.length,
                raw: S.model.raw.Project.find(r => r.project_id === p).project_name}; }""", rid)
    check(ec["link"] and not ec["ce"] and ec["pending"] == n0 + 1 and ec["raw"] == was + " (renamed)",
          "Escape, as in any cell, puts it back — and the link returns with nothing changed", str(ec))
    pg.locator(f"{P} tr[data-id='{rid}'] .namelink").focus()
    pg.keyboard.press("F2")
    pg.wait_for_timeout(300)
    check(pg.evaluate("document.activeElement.classList.contains('renaming')"),
          "F2 on the link renames it too")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    pg.locator(f"{P} tr[data-id='{rid}'] .namelink").click()
    pg.wait_for_timeout(800)
    pg.locator("#cardBody [data-team]").click()
    pg.wait_for_timeout(700)
    stack = pg.evaluate("el('teamdlg').open && el('carddlg').open")
    inp = pg.locator("#teamBody input[data-tm='person_weight']").first
    asg = pg.evaluate("""() => { const r = +document.querySelector(
        "#teamBody input[data-tm='person_weight']").dataset.row;
        return S.model.raw.Assignment.find(a => a.__row === r).assignment_id; }""")
    inp.fill("0.77")
    inp.dispatch_event("change")
    pg.wait_for_timeout(1300)
    pg.click("#teamClose")
    pg.wait_for_timeout(500)
    shows = pg.evaluate("""a => { const s = [...document.querySelectorAll('#cardBody .csec')]
        .find(s => s.querySelector('h3').textContent === 'Team');
        return el('carddlg').open && !!s && [...s.querySelectorAll('tbody tr')]
          .some(tr => tr.textContent.includes('0.77')); }""", asg)
    check(stack and shows, "THE CARD FOLLOWS AN EDIT — a weight changed in the team dialog it "
          "opened is in its Team table when that closes", f"stacked={stack}, shown={shows}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(1000)
    check(pg.evaluate("p => S.model.projects[p].project_name", rid) == was,
          "Leave without change undoes the rename like any other edit")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    b.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
