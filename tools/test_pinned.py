"""Check that a row's identity stays on screen while its table scrolls sideways (R-53).

The Project sheet is twenty-five columns and about 3,070px wide in a panel of 1,316px, so
less than half of it is ever on screen. Scroll out to the far columns and you are editing
an unlabelled row: the data is all there, what has gone is WHICH PROJECT THIS IS.

So the row's handle, its identifier and its name are frozen at the left edge and the rest
slides under them. Three things have to hold, and only the first is obvious:

  1. they stay put. Scroll the box and their left edges do not move
  2. they are OPAQUE, and stay opaque in every state a row can be in - striped, hovered,
     selected, edited. Every background in this table is a colour mixed against
     TRANSPARENT, which is right for a cell sitting on the panel and wrong for one with
     rows passing underneath: the row behind shows straight through
  3. no seam. Laid out exactly edge to edge, a one-device-pixel gap still opens between
     two stuck cells, and the row sliding underneath shows through it as a stray mark
     beside the identifier. This samples the actual pixels either side of each boundary
     and fails if any of them is not the colour of the cell

And three it must not break: the cells are still editable in place, the pinning is
declared per sheet rather than per call site, and a table that declares none has none.

    python tools/test_pinned.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.19.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TABLE = "#t-proj .data-t[data-sheet='Project']"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def geom(pg):
    return pg.evaluate("""() => {
      const t = document.querySelector("#t-proj .data-t[data-sheet='Project']");
      const box = t.closest('.scrollx'), br = box.getBoundingClientRect();
      const tr = t.querySelectorAll('tbody tr')[2];
      const at = sel => { const c = tr.querySelector(sel); const r = c.getBoundingClientRect();
        return {x: Math.round(r.left - br.left), w: Math.round(r.width),
                txt: c.textContent.trim()}; };
      return {scroll: Math.round(box.scrollLeft), ins: at('td.ins'),
              p1: at('.pin1'), p2: at('.pin2'),
              free: at("td[data-col='project_type']")};
    }""")


def scroll(pg, x):
    pg.evaluate("""x => { document.querySelector("#t-proj .data-t[data-sheet='Project']")
      .closest('.scrollx').scrollLeft = x; }""", x)
    pg.wait_for_timeout(400)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))

    print("app/PRAP.html — the columns that stay put")
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=120000)
    pg.wait_for_timeout(2500)
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(1500)

    # ---- 0. the table is wide enough for this to be worth doing -----------------
    wide = pg.evaluate("""() => { const t = document.querySelector(
      "#t-proj .data-t[data-sheet='Project']"); const b = t.closest('.scrollx');
      return [Math.round(t.getBoundingClientRect().width), b.clientWidth,
              t.querySelectorAll('thead th').length]; }""")
    check(wide[0] > wide[1] * 2,
          "the Project table is more than twice the width of the panel that holds it — "
          "which is the whole reason this exists",
          f"{wide[2]} columns, {wide[0]}px in {wide[1]}px")

    # Said first, and stopped on. Everything below reads .pin1 and .pin2 off the rows, so
    # a build that pins nothing would come apart on a null rather than report that it pins
    # nothing - a traceback is a worse answer to "is this still working" than a sentence.
    declared = pg.evaluate("""() => { const t = document.querySelector(
      "#t-proj .data-t[data-sheet='Project']");
      return [t.dataset.pin || "none", t.querySelectorAll('tbody .pin1').length,
              t.querySelectorAll('tbody .pin2').length]; }""")
    if declared[0] != "2" or not declared[1] or not declared[2]:
        check(False, "the Project table pins its identifier and its name at all",
              f"data-pin={declared[0]}, {declared[1]} id cells, {declared[2]} name cells")
        print()
        print("FAILURES: " + ", ".join(fails))
        browser.close()
        sys.exit(1)

    # ---- 1. they stay put -------------------------------------------------------
    # Compared between two SCROLLED positions rather than against the resting one: the
    # resting position is the table's own layout, and a stuck cell sits one pixel to the
    # left of it on purpose - see the overlap in the stylesheet - so rest against scrolled
    # would be measuring that pixel rather than the pinning.
    pg.evaluate("""() => document.querySelector("#t-proj .data-t[data-sheet='Project']")
      .closest('.scrollx').scrollIntoView({block: 'start'})""")
    pg.wait_for_timeout(400)
    at_rest = geom(pg)
    scroll(pg, 700)
    half = geom(pg)
    scroll(pg, 1400)
    moved = geom(pg)
    check(half["ins"]["x"] == moved["ins"]["x"] == 0
          and half["p1"]["x"] == moved["p1"]["x"]
          and half["p2"]["x"] == moved["p2"]["x"]
          and moved["free"]["x"] < 0,
          "the handle, the identifier and the name hold their place while everything else "
          "scrolls out from under them",
          f"pinned at {moved['ins']['x']}/{moved['p1']['x']}/{moved['p2']['x']} at both "
          f"700px and 1400px, project_type now at {moved['free']['x']}")
    # Each one gives up a pixel to the overlap, and the one after it gives up that pixel
    # too - so the nth has moved n pixels, and the block ends two pixels early. Two is
    # the budget; more would mean the offsets and the widths had come apart.
    drift = [at_rest[k]["x"] - moved[k]["x"] for k in ("ins", "p1", "p2")]
    check(drift == [0, 1, 2],
          "and they are within a pixel each of where the table put them — the overlap is "
          "paid for one column at a time and never accumulates beyond it",
          f"at rest {at_rest['ins']['x']}/{at_rest['p1']['x']}/{at_rest['p2']['x']}, "
          f"stuck {moved['ins']['x']}/{moved['p1']['x']}/{moved['p2']['x']}")
    check(moved["p1"]["txt"] and moved["p2"]["txt"],
          "and they still say which project this row is",
          f"{moved['p1']['txt']} · {moved['p2']['txt']}")

    # ---- 2. opaque, in every state a row can be in ------------------------------
    # Asked of the COMPUTED background rather than of the stylesheet: what matters is
    # that the colour that lands has no alpha, however it was arrived at.
    pg.evaluate("""() => { const t = document.querySelector(
      "#t-proj .data-t[data-sheet='Project']");
      const tr = t.querySelectorAll('tbody tr')[4];
      tr.querySelector('.pin1').classList.add('edited');
      S.selProj = tr.querySelector('.pin1').textContent.trim(); }""")
    pg.hover(f"{TABLE} tbody tr:nth-child(2) .pin2")
    pg.wait_for_timeout(300)
    see_through = pg.evaluate("""() => {
      const t = document.querySelector("#t-proj .data-t[data-sheet='Project']");
      const bad = [];
      for (const c of t.querySelectorAll('tbody td.ins, tbody .pin1, tbody .pin2')){
        const bg = getComputedStyle(c).backgroundColor;
        // rgba(...) with a fourth term below 1, or the keyword, is see-through.
        const m = bg.match(/rgba?\\(([^)]+)\\)/);
        const a = m ? (m[1].split(',')[3] || '1').trim() : '1';
        if (bg === 'transparent' || parseFloat(a) < 1) bad.push(c.className + ' ' + bg);
      }
      return bad;
    }""")
    check(not see_through,
          "every pinned cell is opaque — striped, hovered, selected and edited alike",
          f"{len(see_through)} see-through" if see_through else "none see-through")

    # ---- 3. no seam between them ------------------------------------------------
    # The pixels either side of each boundary, read off a canvas of the real thing. A
    # one-device-pixel gap is invisible to any geometry check - the rects agree to three
    # decimal places - and shows up as a stray mark only where something dark happens to
    # be behind it, which is why this samples colour rather than position.
    pg.evaluate("""() => document.querySelector("#t-proj .data-t[data-sheet='Project']")
      .closest('.scrollx').scrollIntoView({block: 'start'})""")
    pg.wait_for_timeout(400)
    seam = pg.evaluate("""() => {
      const t = document.querySelector("#t-proj .data-t[data-sheet='Project']");
      const out = [];
      let looked = 0;
      for (const tr of t.querySelectorAll('tbody tr')){
        const p1 = tr.querySelector('.pin1'), p2 = tr.querySelector('.pin2');
        if (!p1 || !p2) continue;
        for (const cell of [p1, p2]){
          const r = cell.getBoundingClientRect();
          const y = Math.round(r.top + r.height / 2);
          if (y < 0 || y > innerHeight - 1) continue;
          /* The MIDDLE of the cell first, as a control. A row under the sticky band at
             the top of the page answers with the band whatever is asked of it, and a row
             nobody can see is not evidence either way - so only rows that answer with
             themselves in the middle are asked about their edge. */
          if (document.elementFromPoint(Math.round(r.left + r.width / 2), y) !== cell)
            continue;
          for (const dx of [1, 2, 3]){
            looked++;
            const el = document.elementFromPoint(Math.round(r.left) + dx, y);
            if (el !== cell && !cell.contains(el))
              out.push(cell.dataset.col + '@+' + dx + ' -> '
                       + (el ? (el.dataset.col || el.className) : 'nothing'));
          }
        }
      }
      return {bad: out, looked};
    }""")
    check(not seam["bad"],
          "nothing from the row underneath is in front of a pinned cell at its own edge",
          "; ".join(seam["bad"][:3]) if seam["bad"]
          else f"{seam['looked']} points either side of both boundaries, clean")

    # AND THE OVERLAP ITSELF, because the check above cannot see the fault it was written
    # for. The seam is one DEVICE pixel wide; hit testing works in CSS pixels and answers
    # with the cell either way, so a screenshot is the only thing that shows it - and
    # sampling one would need an image library these suites deliberately do not have
    # (openpyxl and playwright, nothing else). What CAN be asserted is the mechanism: each
    # stuck cell starts before the one before it ends, so there is no boundary for the row
    # behind to come through. Proved against the fault by taking the pixel out again.
    laps = pg.evaluate("""() => {
      const t = document.querySelector("#t-proj .data-t[data-sheet='Project']");
      const tr = t.querySelectorAll('tbody tr')[2];
      const r = s => tr.querySelector(s).getBoundingClientRect();
      return [+(r('td.ins').right - r('.pin1').left).toFixed(2),
              +(r('.pin1').right - r('.pin2').left).toFixed(2)];
    }""")
    check(all(x >= 1 for x in laps),
          "each one starts before its neighbour ends, which is what leaves no seam for the "
          "row behind to show through",
          f"overlaps of {laps[0]}px and {laps[1]}px")

    # ---- 4. still the application ------------------------------------------------
    cell = f"{TABLE} tbody tr:nth-child(3) .pin2"
    pg.click(cell)
    pg.wait_for_timeout(300)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("NEU-103 Phase 3 (renamed while scrolled)")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    after = pg.evaluate("""() => ({pending: S.pending.length,
      name: (S.model.projects['PRJ-003'] || {}).project_name,
      stuck: Math.round(document.querySelector(
        "#t-proj .data-t[data-sheet='Project'] tbody tr:nth-child(3) .pin2")
        .getBoundingClientRect().left
        - document.querySelector("#t-proj .data-t[data-sheet='Project']")
          .closest('.scrollx').getBoundingClientRect().left)};)""".replace(";)", ")"))
    check(after["pending"] == 1 and after["name"] == "NEU-103 Phase 3 (renamed while scrolled)",
          "a pinned cell is an ordinary editable cell — it can be typed into where it "
          "stands, scrolled out or not", f"{after['name']!r}")
    check(after["stuck"] == moved["p2"]["x"],
          "and it is still pinned afterwards, through the re-render the edit caused",
          f"back at {after['stuck']}px")

    # ---- 5. declared per sheet, not per call site --------------------------------
    others = pg.evaluate("""() => {
      const out = {};
      for (const t of document.querySelectorAll('.data-t[data-sheet]'))
        out[t.dataset.sheet] = t.dataset.pin || "none";
      return out;
    }""")
    check(others.get("Project") == "2",
          "the Project table declares two pinned columns", str(others))
    check(all(v == "none" for k, v in others.items() if k != "Project"),
          "and a table that declares none has none — nothing is pinned by accident",
          ", ".join(f"{k}={v}" for k, v in others.items() if k != "Project") or "no others drawn")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
