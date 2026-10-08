"""Check that a section given the whole screen is still the application, not a picture of it.

The feature is a class on a panel and nothing else - see src/ui/11b_zoom.js for why it is
not a dialog and why nothing is moved. That design makes one promise worth testing hard:
because the panel never leaves the DOM, everything that worked on the page works here, and
because a render replaces the panel, the state has to be put back on a DIFFERENT ELEMENT
with the same name afterwards. Both halves are load-bearing and neither is visible from
reading the CSS.

What is checked:

  1. every panel with a bounded region offers the control, and a panel with nothing to
     enlarge does not - a control that does nothing teaches the reader the feature is broken
  2. it is actually bigger: wider than the 1400px column and taller than the 340px a data
     table is capped at on the page
  3. THE EDIT BAR AND THE TABS STAY REACHABLE. A full screen that hides Save is a trap -
     you fill in a wide table and have nowhere to commit it
  4. a cell can be edited from inside it, and the section is still full screen afterwards,
     with the edit pending - this is the re-render the state has to survive
  5. Save works from inside it, and the figure goes in
  6. Escape closes it, and the page comes back to where it was
  7. changing tab closes it - a section belongs to the tab it is on, and a hidden pane
     draws nothing
  8. selecting a different row KEEPS it: the panel is named, not indexed, so "Periods"
     stays "Periods" when its heading changes to another project's name
  9. a redraw that is not a whole-page render - the Matrix/Rows toggle - keeps it open.
     That path once went straight to its renderer and skipped the state entirely
 10. loading a plan closes it, so a load's findings banner cannot appear behind it
 11. a panel with two regions shares the height, and neither is squeezed to nothing
 12. the region ENDS inside the section, with its drawn bar at the foot of the last row -
     a region 3,350px past the bottom of the panel reads as success in every other check
     here, because the panel is the window and the region is wide and "taller"

Four of these were written after a deliberate breach got past an earlier draft of this
file: the sticky band left in the flow (the driver had scrolled the page, so the band was
pinned at the top by its own rule and the check could not tell), the Matrix/Rows path, a
tab change that redraws nothing, and the region's own height. Each is now driven in the
state that exposes it, which is why the clicking is done through the DOM rather than
through the driver.

    python tools/test_zoom.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
SMALL = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.12.xlsx"
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.20.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

PANEL = ".panel[data-panel='%s']"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def tab(pg, name):
    pg.click(f'nav button[data-tab="{name}"]')
    pg.wait_for_timeout(1100)


def box(pg, tabid, name):
    """The panel's own geometry and that of the first region inside it."""
    return pg.evaluate("""a => {
      const p = document.querySelector('#' + a.tab + ' .panel[data-panel="' + a.name + '"]');
      if (!p) return null;
      const s = p.querySelector('.scrollx');
      const r = p.getBoundingClientRect();
      return {w: Math.round(r.width), h: Math.round(r.height), top: Math.round(r.top),
              zoom: p.classList.contains('zoom'),
              bw: s ? s.clientWidth : 0, bh: s ? s.clientHeight : 0};
    }""", {"tab": tabid, "name": name})


def press(pg, tabid, name):
    """Through the DOM, not through the driver.

    Playwright's own click scrolls the target into view first, which silently undoes any
    scroll position the test has just set - and the scroll position is the whole of what
    checks 2 and 3 are about. An earlier version used pg.click() here and passed against
    a build with the sticky band left in the flow, because the driver had scrolled the
    page 565px and the band was pinned at the top by its ordinary rule.
    """
    pg.evaluate("""a => document.querySelector(
      '#' + a.tab + ' .panel[data-panel="' + a.name + '"] button.zoombtn').click()""",
                {"tab": tabid, "name": name})
    pg.wait_for_timeout(500)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — one section, the whole screen")
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(SMALL))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=60000)
    pg.wait_for_timeout(1200)

    # ---- 1. the control is offered exactly where it can do something ----------
    offered = pg.evaluate("""() => {
      const out = {with: [], without: []};
      for (const t of ['t-overall','t-proj','t-pers','t-gen']){
        for (const p of document.querySelectorAll('#' + t + ' .panel[data-panel]')){
          const head = p.querySelector(':scope > .phead');
          if (!head) continue;
          const has = !!head.querySelector(':scope > button.zoombtn');
          (p.querySelector('.scrollx') ? out.with : out.without)
            .push(t + '/' + p.dataset.panel + (has ? '' : ' MISSING'));
          if (!p.querySelector('.scrollx') && has) out.without.push(t + '/' + p.dataset.panel + ' SPURIOUS');
        }
      }
      return out;
    }""")
    # Only the tab on screen is rendered, so this names what is drawn now; the sweep over
    # all four tabs below is what covers the rest.
    check(not any("MISSING" in x for x in offered["with"]),
          "every panel with a bounded region carries the control",
          f"{len(offered['with'])} on the open tab")
    check(not any("SPURIOUS" in x for x in offered["without"]),
          "and a panel with nothing to enlarge carries none")

    seen = {}
    for t in ("t-overall", "t-proj", "t-pers", "t-gen"):
        tab(pg, t)
        seen[t] = pg.evaluate("""t => [...document.querySelectorAll(
          '#' + t + " .panel[data-panel] > .phead > button.zoombtn")].map(b => b.dataset.zoom)""", t)
    total = sum(len(v) for v in seen.values())
    check(total >= 20, "the control is on every tab",
          " · ".join(f"{k.replace('t-','')} {len(v)}" for k, v in seen.items()))

    # ---- 2. it is actually bigger --------------------------------------------
    tab(pg, "t-proj")
    # FROM THE TOP OF THE PAGE, which is where this is usually pressed and the only
    # position that tests anything. Further down, the sticky band is already pinned at
    # y=0 by its own rule, so a section that failed to lift it would still look right -
    # an earlier version of this test passed against exactly that fault because clicking
    # the control had happened to scroll the page 565px first.
    pg.evaluate("() => window.scrollTo(0, 0)")
    pg.wait_for_timeout(250)
    before = box(pg, "t-proj", "projects")
    press(pg, "t-proj", "projects")
    after = box(pg, "t-proj", "projects")
    check(after["zoom"] and after["w"] > before["w"] and after["bh"] > before["bh"],
          "the section is wider than the page column and taller than the table cap",
          f"{before['w']}x{before['bh']} -> {after['w']}x{after['bh']}")
    check(after["w"] == 1600, "it takes the whole window width, not the 1400px column",
          f"{after['w']}px of 1600")

    # ---- 3. the edit bar and the tabs stay reachable --------------------------
    # Asked of the PIXELS, not of the stylesheet: a control is reachable when the topmost
    # thing at its own centre is the control. Reading `position: fixed` back off the band
    # would only confirm that a rule exists.
    def reachable(pg):
        return pg.evaluate("""() => {
          const hit = id => { const e = document.getElementById(id);
            const r = e.getBoundingClientRect();
            if (!(r.width > 0 && r.top >= 0 && r.bottom <= innerHeight)) return 'off screen';
            const q = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
            return q && (q === e || e.contains(q)) ? 'in front' : 'covered'; };
          const bar = document.getElementById('stickybar').getBoundingClientRect();
          const p = document.querySelector('.panel.zoom').getBoundingClientRect();
          return {save: hit('saveBtn'), tabs: hit('tabs'), barTop: Math.round(bar.top),
                  gap: Math.round(p.top) - Math.round(bar.bottom), scroll: Math.round(scrollY)};
        }""")

    for where, label in ((None, "from the top of the page"), (600, "with the page scrolled")):
        if where is not None:
            pg.keyboard.press("Escape")
            pg.wait_for_timeout(300)
            pg.evaluate("y => window.scrollTo(0, y)", where)
            pg.wait_for_timeout(250)
            press(pg, "t-proj", "projects")
        r = reachable(pg)
        check(r["save"] == "in front" and r["tabs"] == "in front"
              and r["barTop"] == 0 and r["gap"] == 0,
              f"Save and the tabs stay in front, and the section starts under them, {label}",
              f"save {r['save']}, tabs {r['tabs']}, band at y={r['barTop']}, "
              f"section {r['gap']:+d}px from it")

    # ---- 4. and 5. editing, then saving, from inside it -----------------------
    cell = "#t-proj .panel[data-panel='projects'] td[data-col='project_name']"
    pg.locator(cell).nth(1).click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("CAR-102 Phase 2 (typed full screen)")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    st = pg.evaluate("""() => ({
      zoom: !!document.querySelector("#t-proj .panel[data-panel='projects'].zoom"),
      body: document.body.classList.contains('zoomed'),
      pending: S.pending.length,
      canSave: !document.getElementById('saveBtn').disabled})""")
    check(st["zoom"] and st["body"] and st["pending"] == 1 and st["canSave"],
          "a cell can be typed into from inside it, and the section survives the re-render",
          f"pending={st['pending']}")

    pg.click("#saveBtn")
    pg.wait_for_timeout(1200)
    saved = pg.evaluate("""() => ({
      pending: S.pending.length, saved: S.saved,
      zoom: !!document.querySelector("#t-proj .panel[data-panel='projects'].zoom"),
      value: (S.model.projects['PRJ-002'] || {}).project_name})""")
    check(saved["pending"] == 0 and saved["saved"] >= 1
          and saved["value"] == "CAR-102 Phase 2 (typed full screen)" and saved["zoom"],
          "Save commits from inside it and the section stays open",
          f"saved={saved['saved']}, value={saved['value']!r}")

    # ---- 6. Escape ------------------------------------------------------------
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    out = pg.evaluate("""() => ({
      any: document.querySelectorAll('.panel.zoom').length,
      body: document.body.classList.contains('zoomed'),
      zoom: S.zoom,
      pos: getComputedStyle(document.getElementById('stickybar')).position,
      scroll: getComputedStyle(document.body).overflow})""")
    check(out["any"] == 0 and not out["body"] and out["zoom"] is None
          and out["pos"] == "sticky",
          "Escape gives the page back, with nothing left behind",
          f"band is {out['pos']} again, body overflow {out['scroll']}")

    # ---- 7. changing tab closes it -------------------------------------------
    press(pg, "t-proj", "projects")
    tab(pg, "t-overall")
    gone = pg.evaluate("""() => ({any: document.querySelectorAll('.panel.zoom').length,
      body: document.body.classList.contains('zoomed'), zoom: S.zoom})""")
    check(gone["any"] == 0 and not gone["body"] and gone["zoom"] is None,
          "changing tab closes it — a hidden pane draws nothing, and the page must come back")

    # ---- 7b. and when the tab it moves to is NOT redrawn ----------------------
    # The case above is the easy one: an edit had marked every pane stale, so arriving at
    # the other tab rebuilt it, and a rebuild puts the state right by itself. With both
    # panes already current, showTab changes nothing but which one is hidden - and that is
    # the path where a section left open would stay open on a pane that draws nothing,
    # with the page parked behind it and no way back.
    tab(pg, "t-proj")
    fresh = pg.evaluate("() => S.stale.has('t-overall')")
    press(pg, "t-proj", "projects")
    tab(pg, "t-overall")
    quiet = pg.evaluate("""() => ({any: document.querySelectorAll('.panel.zoom').length,
      body: document.body.classList.contains('zoomed'), zoom: S.zoom,
      scrolls: getComputedStyle(document.body).overflow !== 'hidden'})""")
    check(fresh is False and quiet["any"] == 0 and not quiet["body"]
          and quiet["zoom"] is None and quiet["scrolls"],
          "and it closes on a tab change that redraws nothing at all",
          "the pane it moves to was already current, so nothing was rebuilt"
          if fresh is False else "the pane it moves to was STALE — this proved nothing")

    # ---- 8. the name, not the position ---------------------------------------
    tab(pg, "t-proj")
    press(pg, "t-proj", "proj-per")
    first = pg.evaluate("() => document.querySelector('.panel.zoom h2').textContent")
    pg.evaluate("""() => { S.selProj = 'PRJ-003'; renderKeepingTab(); }""")
    pg.wait_for_timeout(900)
    second = pg.evaluate("""() => { const p = document.querySelector('.panel.zoom');
      return p ? p.dataset.panel + '|' + p.querySelector('h2').textContent : null; }""")
    check(second is not None and second.startswith("proj-per|") and second != "proj-per|" + first,
          "selecting a different project keeps the SECTION open and follows it",
          f"{first!r} -> {(second or '').split('|', 1)[-1]!r}")

    # ---- 10. two regions in one panel ----------------------------------------
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    tab(pg, "t-gen")
    press(pg, "t-gen", "gen-rf")
    two = pg.evaluate("""() => [...document.querySelectorAll('.panel.zoom .scrollx')]
      .map(s => s.clientHeight)""")
    check(len(two) == 2 and min(two) > 100,
          "a panel holding two matrices shares the height and squeezes neither",
          f"{two[0]}px and {two[1]}px" if len(two) == 2 else f"{len(two)} region(s)")

    # ---- 10b. a redraw that is not a whole-page render ------------------------
    # Role factors switches between Matrix and Rows by redrawing its own pane, which for a
    # while was the one path to a new DOM that did not go through the place the state is
    # put back - so the section gave the page back as the view changed. The rest of the
    # suite could not see it: every other check drives a render through a tab change, an
    # edit or a load.
    pg.click("#t-gen .panel[data-panel='gen-rf'] [data-setview='rf|rows']")
    pg.wait_for_timeout(900)
    held = pg.evaluate("""() => { const p = document.querySelector('.panel.zoom');
      return {name: p ? p.dataset.panel : null,
              rows: !!document.querySelector("#t-gen .panel[data-panel='gen-rf'] "
                    + ".data-t[data-sheet='RoleFactor']")}; }""")
    check(held["name"] == "gen-rf" and held["rows"],
          "switching that panel between Matrix and Rows redraws it without closing it",
          f"still open on {held['name']!r}, now showing the editable rows={held['rows']}")
    pg.click("#t-gen .panel[data-panel='gen-rf'] [data-setview='rf|matrix']")
    pg.wait_for_timeout(700)

    # ---- 9. a load closes it --------------------------------------------------
    # The save above means the second load asks before replacing the plan, which is the
    # application doing its job; say yes and carry on.
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_timeout(600)
    if pg.evaluate("() => document.getElementById('replace').open"):
        pg.click("#rpYes")
    pg.wait_for_timeout(6000)
    # To the top first: a load keeps the page's scroll, so the banner may be above the
    # viewport, and elementFromPoint outside the viewport answers nothing at all. Whether
    # the banner is SCROLLED to is a different question from whether it is COVERED, and
    # this check is only the second one.
    pg.evaluate("() => window.scrollTo(0, 0)")
    pg.wait_for_timeout(250)
    loaded = pg.evaluate("""() => ({any: document.querySelectorAll('.panel.zoom').length,
      body: document.body.classList.contains('zoomed'), zoom: S.zoom,
      // What the load has to say, and whether anything is drawn over it. Not "is it in
      // the viewport" - the page keeps its scroll across a load, which is a different
      // question and not this one's - but whether the top-most element at the banner's
      // own position is the banner.
      banner: (() => { const b = document.getElementById('banner');
        const r = b.getBoundingClientRect();
        if (!b.textContent.trim() || !r.height) return 'nothing to say';
        const hit = document.elementFromPoint(r.left + 8, r.top + r.height / 2);
        return hit && b.contains(hit) ? 'in front' : 'COVERED'; })()})""")
    check(loaded["any"] == 0 and not loaded["body"] and loaded["zoom"] is None
          and loaded["banner"] != "COVERED",
          "loading a plan closes it, so the load's own report cannot appear behind it",
          f"the banner is {loaded['banner']}")

    # ---- 11. the big plan, where this is actually for -------------------------
    tab(pg, "t-overall")
    small = box(pg, "t-overall", "table-proj")
    press(pg, "t-overall", "table-proj")
    large = box(pg, "t-overall", "table-proj")
    check(large["bw"] > small["bw"] and large["bh"] >= small["bh"],
          "and on the 62-project plan the month grid gains width as well as height",
          f"{small['bw']}x{small['bh']} -> {large['bw']}x{large['bh']}")
    fits = pg.evaluate("""() => {
      const p = document.querySelector('.panel.zoom').getBoundingClientRect();
      return {right: Math.round(p.right) - innerWidth, bottom: Math.round(p.bottom) - innerHeight};
    }""")
    check(fits["right"] == 0 and fits["bottom"] == 0,
          "the section is exactly the window — no strip of page showing, nothing off the edge",
          f"right {fits['right']:+d}, bottom {fits['bottom']:+d}")

    # ---- 11b. the region is BOUNDED, and its scrollbar is at the foot of it ----
    # The failure this is for looks like success in every height the rest of the suite
    # reads: the panel is the window, the region is wide, and the region is "taller". It is
    # taller by 4,105px on this plan, overflowing the panel by 3,350 with the drawn
    # scrollbar - a child of the wrapper, not of the box - stranded that far below the last
    # row it is supposed to describe. REQ-DSH-13 is the rule being broken: a region that
    # does not end on screen cannot show the reader there is more.
    held = pg.evaluate("""() => {
      const p = document.querySelector('.panel.zoom');
      const cs = getComputedStyle(p), r = p.getBoundingClientRect();
      const floor = r.bottom - parseFloat(cs.paddingBottom);
      return [...p.querySelectorAll('.scrollx')].map(s => {
        const q = s.getBoundingClientRect();
        const bar = s.parentElement.querySelector('.sbar.h');
        return {over: Math.round(q.bottom - floor),
                bar: bar ? Math.round(bar.getBoundingClientRect().bottom - q.bottom) : 0};
      });
    }""")
    check(held and all(abs(x["over"]) <= 1 and abs(x["bar"]) <= 4 for x in held),
          "the region ends inside the section, with its drawn bar at the foot of it",
          "; ".join(f"{x['over']:+d}px past the panel, bar {x['bar']:+d}px from the last row"
                    for x in held))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
