"""Five things a reviewer asked for, each of which is only true if you can see it.

  1. A DATE CELL OFFERS A CALENDAR, and stays typeable. Both halves: picking is what you
     want when the question is "is the 14th a Tuesday", typing is what you want on the
     twentieth row of a set you already know. So the panel is an offer laid beside the
     cell, never a gate in front of it.
  2. THE PERIOD GENERATOR IS OFFERED WHERE IT CAN RUN. Auto derivation on an 'Others'
     project could only ever answer no - the rule hangs on CTA submission and the DB
     locks, which an internal project does not have and never will. A control that
     refuses every time it is pressed teaches the reader the feature is broken.
     (The derivation ITSELF is checked in test_generate.py; this is about what is offered.)
  3. EVERY REGION THAT SCROLLS SAYS SO, WITH SOMETHING YOU CAN DRAG. The browser was
     asked twice for a bar and gave an overlay that occupies no layout space - measured
     here, a plain div with an explicit 14px ::-webkit-scrollbar still reports
     offsetHeight === clientHeight - so the application draws its own.
  4. THE STICKY BAND IS OPAQUE AND SEAMLESS. Two independently sticky bars left a
     hairline the page showed through, and 92% opacity let the rows underneath ghost
     through the text.
  5. MUST vs CONDITIONAL vs INCOMPLETE. Severity says how wrong something is; the class
     says what the application may do about it. Must refuses. Conditional asks at Save
     and the user may force it. Incomplete reports and says nothing else.
  6. A CONFIGURATION SETTING CANNOT BE DELETED, only changed. Nothing referenced a Config
     row, so nothing refused a deletion and nothing reported one - and every setting is
     read through a fallback, so a plan whose floor had been moved to 0.80 reverted to
     0.60 with every dependent figure changing and nothing saying why. V-30 covers the
     workbook that arrives without one.

    python tools/test_ui.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.13.xlsx"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def cell(pg, sheet, col):
    return pg.locator(f"td[data-sheet='{sheet}'][data-col='{col}']").first


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 860})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_timeout(4500)

    # ---- 1. the calendar -----------------------------------------------------
    print("1. a date cell offers a calendar, and stays typeable")
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1300)
    start = cell(pg, "Project", "start_date")
    was = start.inner_text()
    start.click()
    pg.wait_for_timeout(500)
    open_on_date = pg.evaluate("!document.getElementById('cal').hidden")
    month = pg.inner_text(".cmon") if pg.locator(".cmon").count() else ""
    check(open_on_date and month.endswith(was[:4]) and pg.locator(".calgrid .d.on").count() == 1,
          "it opens on the cell's own month, with that day marked",
          f"cell {was}, panel shows {month}")

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(250)
    cell(pg, "Project", "project_name").click()
    pg.wait_for_timeout(450)
    check(pg.evaluate("document.getElementById('cal').hidden"),
          "and only on a date column — a text cell gets the value list, not a calendar")

    start.click()
    pg.wait_for_timeout(500)
    before = pg.inner_text(".cmon")
    pg.locator(".cnav[data-step='1']").click()
    pg.wait_for_timeout(400)
    after_m = pg.inner_text(".cmon")
    pg.locator(".cnav[data-step='12']").click()
    pg.wait_for_timeout(400)
    check(after_m != before and pg.inner_text(".cmon") != after_m,
          "the month and the year both step",
          f"{before} → {after_m} → {pg.inner_text('.cmon')}")

    start.click()
    pg.wait_for_timeout(450)
    pg.locator(".calgrid button.d", has_text="15").first.click()
    pg.wait_for_timeout(800)
    picked = pg.evaluate("ymd(S.model.raw.Project[0].start_date)")
    check(picked.endswith("-15") and picked != was,
          "PICKING A DAY COMMITS IT, through the ordinary edit path",
          f"{was} → {picked}")

    start.click()
    pg.wait_for_timeout(450)
    pg.keyboard.press("Control+A")
    pg.keyboard.type(picked[:4] + "-02-03")
    pg.wait_for_timeout(500)
    steered = pg.inner_text(".cmon")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(800)
    check(steered.startswith("February")
          and pg.evaluate("ymd(S.model.raw.Project[0].start_date)").endswith("-02-03"),
          "AND TYPING STILL WORKS — what you type steers the grid rather than the "
          "other way round",
          f"panel followed to {steered}, cell now "
          f"{pg.evaluate('ymd(S.model.raw.Project[0].start_date)')}")
    pg.evaluate("discardEdits()")
    pg.wait_for_timeout(700)

    # ---- 2. the period generator --------------------------------------------
    print("\n2. the period generator that fits the project")
    offered = pg.evaluate("""() => {
        const out = {};
        for (const [pid, p] of Object.entries(S.model.projects)){
          if (out[p.project_type]) continue;
          S.selProj = pid; renderKeepingTab();
          const a = document.querySelector("[data-act='autoper']");
          out[p.project_type] = a ? (a.disabled ? "derivation (disabled)" : "derivation")
            : (document.querySelector("[data-act='blankper']") ? "standard periods" : "none");
        }
        return out;}""")
    trials = [t for t in offered if t != "Others"]
    check(all(offered[t] == "derivation" for t in trials)
          and offered.get("Others") == "standard periods",
          "every trial is offered the derivation; an 'Others' project is offered the "
          "generator that fits it instead",
          "; ".join(f"{t}: {v}" for t, v in offered.items()))

    # ---- 3. the drawn scroll bars -------------------------------------------
    print("\n3. every region that scrolls has a bar you can drag")
    for tab in ["Overall", "Source data (project)", "Source data (person)",
                "General assumptions"]:
        pg.click(f"text={tab}")
        pg.wait_for_timeout(1300)
        r = pg.evaluate("""() => {
            let over = 0, ok = 0, missing = [];
            for (const box of document.querySelectorAll('.scrollx')){
              if (!box.offsetParent) continue;
              if (box.scrollWidth - box.clientWidth <= 1) continue;
              over++;
              const bar = box.parentElement.querySelector('.sbar.h');
              if (bar && bar.firstChild && bar.classList.contains('on')
                  && bar.getBoundingClientRect().height > 4
                  && bar.firstChild.getBoundingClientRect().width > 10) ok++;
              else missing.push(box.className);
            }
            return {over, ok, missing};}""")
        check(r["over"] > 0 and r["ok"] == r["over"],
              f"{tab}: every sideways-scrolling region has a visible bar",
              f"{r['ok']}/{r['over']}" + (f"; missing {r['missing']}" if r["missing"] else ""))

    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1300)
    pg.evaluate("""() => { const b = [...document.querySelectorAll('.scrollx')]
        .find(e => e.offsetParent && e.scrollWidth - e.clientWidth > 200);
        b.id = 'pBox'; b.scrollLeft = 0;
        const bar = b.parentElement.querySelector('.sbar.h');
        if (!bar || !bar.firstChild) throw new Error('no drawn bar on a region that scrolls');
        bar.firstChild.id = 'pThumb';
        b.scrollIntoView({block:'center'}); }""")
    pg.wait_for_timeout(600)
    box0 = pg.evaluate("document.getElementById('pBox').scrollLeft")
    tb = pg.locator("#pThumb").bounding_box()
    pg.mouse.move(tb["x"] + tb["width"] / 2, tb["y"] + tb["height"] / 2)
    pg.mouse.down()
    pg.mouse.move(tb["x"] + tb["width"] / 2 + 240, tb["y"] + tb["height"] / 2, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(500)
    box1 = pg.evaluate("document.getElementById('pBox').scrollLeft")
    check(box1 > box0 + 100, "DRAGGING THE THUMB SCROLLS THE REGION",
          f"scrollLeft {box0} → {box1}")

    # ---- 4. the sticky band --------------------------------------------------
    print("\n4. the sticky band is opaque, and has no seam")
    pg.mouse.wheel(0, 1600)
    pg.wait_for_timeout(700)
    band = pg.evaluate("""() => {
        const sb = document.getElementById('stickybar');
        const r = sb.getBoundingClientRect(), cs = getComputedStyle(sb);
        const inBand = e => { let n = e; while (n){ if (n === sb) return true;
                                                    n = n.parentElement; } return false; };
        const leaks = [];
        for (const f of [0.08, 0.3, 0.5, 0.7, 0.95])
          for (const y of [1, r.height/2, r.height - 1]){
            const el = document.elementFromPoint(innerWidth*f, y);
            if (el && !inBand(el) && el.tagName !== 'HTML' && el.tagName !== 'BODY')
              leaks.push(el.tagName + '.' + String(el.className).slice(0, 18));
          }
        return {top: r.top, h: Math.round(r.height), bg: cs.backgroundColor,
                scrolled: window.scrollY, leaks: [...new Set(leaks)]};}""")
    check(band["scrolled"] > 800 and abs(band["top"]) < 0.5,
          "it stays at the top of a scrolled page", f"scrollY {band['scrolled']}")
    check(not band["leaks"],
          "AND NOTHING FROM THE PAGE SHOWS THROUGH IT — no gap between the bars, and "
          "no ghosting behind them",
          f"{band['h']}px tall, {band['bg']}"
          + (f"; showing through: {band['leaks']}" if band["leaks"] else ""))

    # ---- 5. must / conditional / incomplete ----------------------------------
    print("\n5. what an error is allowed to do")
    classes = pg.evaluate("""() => ({
        must: ruleClass('V-01'), cond: ruleClass('V-23'), inc: ruleClass('V-12'),
        v03: ruleClass('V-03'), unknown: ruleClass('V-99')})""")
    check(classes["must"] == "must" and classes["cond"] == "conditional"
          and classes["v03"] == "conditional" and classes["inc"] == "incomplete"
          and classes["unknown"] == "must",
          "the three classes are named in the CORE, and anything unclassified is must",
          f"{classes}")

    pg.click("text=Source data (person)")
    pg.wait_for_timeout(1300)
    role = cell(pg, "Assignment", "role_name")
    role.click()
    pg.wait_for_timeout(400)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("Regulatory affairs lead")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)
    kept = pg.evaluate("S.model.raw.Assignment[0].role_name")
    check(kept == "Regulatory affairs lead" and "Edit rejected" not in pg.inner_text("#banner"),
          "a CONDITIONAL error does not refuse the edit",
          f"role is now '{kept}', {pg.evaluate('S.pending.length')} pending, "
          f"save enabled={not pg.locator('#saveBtn').is_disabled()}")

    pg.click("#saveBtn")
    pg.wait_for_timeout(1000)
    asked = pg.evaluate("document.getElementById('confirm').open")
    rows = pg.locator("#cfBody tbody tr").count()
    check(asked and rows >= 1,
          "BUT SAVE ASKS, naming every one of them",
          f"dialog open={asked}, {rows} listed")

    pg.click("#cfNo")
    pg.wait_for_timeout(800)
    check(not pg.evaluate("document.getElementById('confirm').open")
          and pg.evaluate("S.saved") == 0 and pg.evaluate("S.pending.length") > 0,
          "'Go back' saves nothing and leaves the edit pending",
          f"saved={pg.evaluate('S.saved')}, pending={pg.evaluate('S.pending.length')}")

    pg.click("#saveBtn")
    pg.wait_for_timeout(900)
    pg.click("#cfYes")
    pg.wait_for_timeout(900)
    banner = pg.inner_text("#banner")
    check(pg.evaluate("S.saved") > 0 and "Saved" in banner and "confirmation" in banner,
          "AND 'SAVE ANYWAY' KEEPS IT, with the shortfall on the record",
          banner.strip().split("\n")[0][:120])

    # A second, harmless edit: the shortfall is unchanged, so there is nothing new to
    # accept and nothing to ask about. Asking again would train the user to click through
    # the dialog without reading it, which is worse than not asking at all.
    note = cell(pg, "Assignment", "note_1")
    note.click()
    pg.wait_for_timeout(400)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("checked with the study lead")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(800)
    pg.click("#saveBtn")
    pg.wait_for_timeout(900)
    check(not pg.evaluate("document.getElementById('confirm').open")
          and pg.evaluate("S.saved") > 1,
          "it does not ask again about something already accepted — the baseline moves "
          "with the save",
          f"saved={pg.evaluate('S.saved')}")

    pid = cell(pg, "Assignment", "project_id")
    was_pid = pid.inner_text()
    pid.click()
    pg.wait_for_timeout(400)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("PRJ-NOPE")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)
    check("Edit rejected" in pg.inner_text("#banner")
          and pg.evaluate("S.model.raw.Assignment[0].project_id") == was_pid
          and not pg.evaluate("document.getElementById('confirm').open"),
          "A MUST ERROR STILL REFUSES OUTRIGHT, with no dialog and no choice",
          pg.inner_text("#banner").strip().split("\n")[0][:80])

    # The report's own labelling, over one finding of each class - the live model happens
    # to carry only the conditional ones, and a check that cannot see the other two rows
    # is not checking the thing it is named after.
    pg.evaluate("""() => { renderReport([
        {sev:'error', rule:'V-01', sheet:'Assignment', row:1, msg:'a must'},
        {sev:'error', rule:'V-23', sheet:'RoleFactor', row:'', msg:'a conditional'},
        {sev:'error', rule:'V-12', sheet:'ProjectPeriod', row:'', msg:'an incomplete'},
        {sev:'warning', rule:'V-07', sheet:'Assignment', row:2, msg:'a warning'}]);
        document.getElementById('report').showModal(); }""")
    pg.wait_for_timeout(600)
    labels = pg.eval_on_selector_all("#repBody .cls", "es => es.map(e => e.textContent)")
    # Sorted by severity, then sheet, then row - so compare the set, not the order.
    check(sorted(labels) == ["may keep", "must fix", "still to come"],
          "and the findings report says which is which, next to the severity — and says "
          "nothing for a warning, which never refused anything",
          f"{labels}")
    pg.evaluate("document.getElementById('report').close()")

    # ---- 6. the Configuration table is a fixed set of rows -------------------
    print("\n6. a setting cannot be deleted, only changed")
    pg.click("text=General assumptions")
    pg.wait_for_timeout(1300)
    cfg = pg.evaluate("""() => {
        const t = document.querySelector("table.data-t[data-sheet='Config']");
        const other = [...document.querySelectorAll("table.data-t[data-sheet]")]
          .filter(x => x.offsetParent && x.dataset.sheet !== 'Config');
        return {rows: t.querySelectorAll('tbody tr').length,
                del: t.querySelectorAll('[data-del]').length,
                ins: t.querySelectorAll('[data-ins]').length,
                editable: t.querySelectorAll(
                  "td[data-col='value'][contenteditable='true']").length};}""")
    check(cfg["rows"] == 9 and cfg["del"] == 0 and cfg["ins"] == 0,
          "NEITHER 'Delete' NOR '+ row' IS OFFERED — the nine settings are read by name, "
          "so there is nothing to add and nothing that should be removed",
          f"{cfg['rows']} rows, {cfg['del']} delete, {cfg['ins']} insert")
    check(cfg["editable"] == cfg["rows"],
          "but every VALUE is still editable, which is what a user actually changes",
          f"{cfg['editable']} of {cfg['rows']} value cells")

    other = pg.evaluate("""() => { S.tab = 't-proj'; showTab('t-proj');
        const t = document.querySelector("table.data-t[data-sheet='Project']");
        return {del: t.querySelectorAll('[data-del]').length,
                ins: t.querySelectorAll('[data-ins]').length};}""")
    check(other["del"] > 0 and other["ins"] > 0,
          "and every other table keeps both controls — this is Config, not a new rule "
          "about tables in general",
          f"Project: {other['del']} delete, {other['ins']} insert")

    v30 = pg.evaluate("""() => {
        const raw = S.model.raw.Config;
        const keep = raw.map(r => ({...r}));
        for (const p of ['under_allocation_fte', 'split_shared_role_fte'])
          raw.splice(raw.findIndex(r => r.parameter === p), 1);
        const m = rebuild();
        const f = m.findings.filter(x => x.rule === 'V-30');
        S.model.raw.Config = keep; rebuild(true);
        return {n: f.length, sev: f[0] && f[0].sev, msg: (f[0] && f[0].msg) || ''};}""")
    check(v30["n"] == 1 and v30["sev"] == "information"
          and "under_allocation_fte = 0.6" in v30["msg"]
          and "split_shared_role_fte = 1" in v30["msg"],
          "V-30 REPORTS A SETTING THAT IS MISSING ANYWAY — from an older file or a "
          "hand-edited one — and names the default now in force",
          v30["msg"][:150] or "(nothing reported)")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\nFAILURES: " + (f"{len(fails)}" if fails else "none"))
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
