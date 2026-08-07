"""Check that nothing but the user moves a scroll position.

Committing a cell re-renders the panel it lives in, and a freshly built element starts at
the top left. On a dashboard that is invisible. During data entry it is the difference
between a usable table and an unusable one: fill one cell in a table twenty-two columns
wide, and every scroll box snaps back to the first row and the first column, so the next
cell you meant to fill is off screen again. Every single cell costs a re-scroll.

A note on how this is driven. Playwright's own click scrolls the target into view first,
and Chromium's scrollIntoView walks up and scrolls EVERY scrollable ancestor - so a
naive click on an off-screen cell moves the box before the application has run a line,
and the test would be measuring the driver rather than the page. Two ways round it:
where a real click is what matters, the box is read AFTER the click has settled and the
cell is on screen by construction; where the click itself is the action under test, it
is dispatched through the DOM, which does not scroll.

What is checked:

  1. committing with Enter leaves both scroll offsets where they were
  2. committing by clicking away (blur, not Enter) does the same
  3. so does inserting a row, and so does Save
  4. the page's own scroll position survives a re-render
  5. a tall table (289 role factors) holds its vertical position too
  6. the cell just filled is still on screen afterwards, which is what the bug cost
  7. changing tab still takes the page to the top - that is the user moving somewhere
     else, not the page moving underneath them

    python tools/test_scroll.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.9.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PROJ = "#t-proj .data-t[data-sheet='Project']"
RF = "#t-gen .data-t[data-sheet='RoleFactor']"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def where(pg, sel):
    return pg.evaluate("""sel => {const b = document.querySelector(sel).closest('.scrollx');
        return {l: b.scrollLeft, t: b.scrollTop, canX: b.scrollWidth > b.clientWidth + 4,
                canY: b.scrollHeight > b.clientHeight + 4, win: window.scrollY};}""", sel)


def put(pg, sel, left, top):
    pg.evaluate("""a => {const b = document.querySelector(a.sel).closest('.scrollx');
        b.scrollLeft = a.left; b.scrollTop = a.top;}""", {"sel": sel, "left": left, "top": top})
    pg.wait_for_timeout(250)


def same(a, b):
    return a["l"] == b["l"] and a["t"] == b["t"]


def moved(p):
    """A check that starts at 0,0 proves nothing - it cannot tell 'kept' from 'reset'."""
    return p["l"] > 0 or p["t"] > 0


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1400, "height": 800})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — scroll position across a re-render")
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1200)

    start = where(pg, PROJ)
    check(start["canX"] and start["canY"],
          "the Project table is wide enough and tall enough for this to matter",
          f"scrolls in x={start['canX']} y={start['canY']}")

    # ---- 1. Enter -----------------------------------------------------------
    # A far-right column on a row down the table: reaching it scrolls the box on both
    # axes, which is exactly the state the bug threw away.
    cell = pg.locator(f"{PROJ} td[data-col='note_1']").nth(6)
    cell.click()
    pg.wait_for_timeout(400)
    before = where(pg, PROJ)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("checked")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    after = where(pg, PROJ)
    check(moved(before) and same(before, after),
          "committing a cell with Enter leaves the scroll alone",
          f"({before['l']}, {before['t']}) -> ({after['l']}, {after['t']})")

    # ---- 6. and the cell is still where the user left it ---------------------
    visible = pg.evaluate("""sel => {const b = document.querySelector(sel).closest('.scrollx');
        const td = [...b.querySelectorAll("td[data-col='note_1']")][6];
        if (!td) return false;
        const r = b.getBoundingClientRect(), q = td.getBoundingClientRect();
        return q.left >= r.left - 1 && q.right <= r.right + 1
            && q.top >= r.top - 1 && q.bottom <= r.bottom + 1;}""", PROJ)
    check(visible, "the cell just filled is still on screen afterwards")

    # ---- 2. blur ------------------------------------------------------------
    cell = pg.locator(f"{PROJ} td[data-col='note_1']").nth(7)
    cell.click()
    pg.wait_for_timeout(400)
    before = where(pg, PROJ)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("also checked")
    pg.click("h1")                              # commit by leaving the field, not by Enter
    pg.wait_for_timeout(1200)
    after = where(pg, PROJ)
    check(moved(before) and same(before, after),
          "committing by clicking away does the same",
          f"({before['l']}, {before['t']}) -> ({after['l']}, {after['t']})")

    # ---- 3. insert a row, and Save ------------------------------------------
    # Dispatched through the DOM: the + row button lives in the first column, so a
    # driver click would scroll the box back to the left before the handler ran.
    put(pg, PROJ, 480, 90)
    before = where(pg, PROJ)
    pg.evaluate("""sel => document.querySelectorAll(sel + " button[data-ins]")[2].click()""", PROJ)
    pg.wait_for_timeout(1200)
    after = where(pg, PROJ)
    check(moved(before) and same(before, after),
          "inserting a row leaves the scroll alone",
          f"({before['l']}, {before['t']}) -> ({after['l']}, {after['t']})")

    pg.evaluate("""sel => document.querySelectorAll(sel + " button[data-del]")[3].click()""", PROJ)
    pg.wait_for_timeout(1200)
    put(pg, PROJ, 540, 70)
    before = where(pg, PROJ)
    pg.click("#saveBtn")                        # the edit bar is sticky - always in view
    pg.wait_for_timeout(1500)
    after = where(pg, PROJ)
    check(moved(before) and same(before, after), "Save leaves the scroll alone",
          f"({before['l']}, {before['t']}) -> ({after['l']}, {after['t']})")

    # ---- 4. the page's own scroll -------------------------------------------
    pg.evaluate("window.scrollTo(0, 900)")
    pg.wait_for_timeout(300)
    y0 = pg.evaluate("window.scrollY")
    cell = pg.locator(f"{PROJ} td[data-col='note_1']").nth(8)
    cell.click()
    pg.wait_for_timeout(400)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("third")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    y1 = pg.evaluate("window.scrollY")
    check(y0 > 0 and abs(y0 - y1) <= 4, "the page's own scroll survives the re-render",
          f"{y0} -> {y1}")

    # ---- 5. a genuinely tall table ------------------------------------------
    pg.click("text=General assumptions")
    pg.wait_for_timeout(1200)
    # Role factors open as a matrix, which is how a standard reads; the editable form is
    # one row per combination, and that is the one worth 289 rows of scrolling.
    pg.click("[data-setview='rf|rows']")
    pg.wait_for_timeout(1200)
    rf = where(pg, RF)
    check(rf["canY"], "the role-factor table is tall enough to scroll", f"y={rf['canY']}")
    put(pg, RF, 0, 900)
    before = where(pg, RF)
    row = pg.evaluate("""sel => {const b = document.querySelector(sel).closest('.scrollx');
        const r = b.getBoundingClientRect();
        const td = [...b.querySelectorAll("td[data-col='role_note']")].find(x => {
          const q = x.getBoundingClientRect();
          return q.top >= r.top - 1 && q.bottom <= r.bottom + 1;});
        return td ? td.dataset.row : null;}""", RF)
    if row:
        pg.locator(f"{RF} td[data-row='{row}'][data-col='role_note']").click()
        pg.wait_for_timeout(300)
        before = where(pg, RF)
        pg.keyboard.press("Control+A")
        pg.keyboard.type("our own figure")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(1400)
        after = where(pg, RF)
        check(moved(before) and same(before, after),
              "a row 900px down a tall table stays where it was",
              f"row {row}: ({before['l']}, {before['t']}) -> ({after['l']}, {after['t']})")
    else:
        check(False, "a row 900px down a tall table stays where it was",
              "no visible role_note cell to type into")

    # ---- 7. changing tab is the user moving somewhere else -------------------
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1000)
    check(pg.evaluate("window.scrollY") == 0,
          "changing tab still takes the page to the top — that is the user moving, "
          "not the page moving underneath them")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
