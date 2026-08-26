"""Drive app/PRAP.html and check the type-ahead value list behaves like a chooser.

It did not. The list is a fixed box anchored to the cell, and a capturing scroll
listener closed it on ANY scroll - including scrolling INSIDE the list itself, which
made a list taller than its box impossible to read to the bottom of. Dragging the
list's own scrollbar closed it a second way, by taking focus off the cell.

What is checked:

  1. it opens with nothing typed, offering the whole vocabulary
  2. the mouse wheel scrolls the list and leaves it open
  3. dragging the list's own scrollbar leaves it open, and the caret comes back
  4. a page scroll re-anchors the list to its cell instead of closing it
  5. matching is partial and order-independent, and ranks a typed prefix first
  6. a query matching nothing shows the whole list and says so, rather than vanishing
  7. Enter alone keeps what was TYPED; arrow-then-Enter picks from the list
  8. Escape closes it; clicking the field re-opens it; clicking away closes it
  9. clicking a value chooses it and commits through the normal edit path

    python tools/test_valuelist.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.11.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
LOC = "#t-proj .data-t[data-sheet='Project']"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def state(pg):
    return pg.evaluate("""() => {const b = document.getElementById('sugg');
        return {open: !b.hidden, n: b.querySelectorAll('.s').length, top: b.scrollTop,
                scrollable: b.scrollHeight > b.clientHeight,
                hint: (b.querySelector('.hint') || {}).textContent || ''};}""")


def options(pg, k=3):
    return pg.eval_on_selector_all("#sugg .s", f"es => es.slice(0, {k}).map(e => e.textContent)")


def anchor(pg):
    """The list's box, or None once it has closed - so a failure reports rather than crashes."""
    try:
        return pg.locator("#sugg").bounding_box()
    except Exception:
        return None


def typed(pg, text):
    pg.keyboard.press("Control+A")
    pg.keyboard.type(text)
    pg.wait_for_timeout(400)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1100)

    print("app/PRAP.html — type-ahead value list")
    name = pg.locator(f"{LOC} td[data-col='project_name']").first
    name.click()
    pg.wait_for_timeout(400)
    s = state(pg)
    check(s["open"] and s["n"] > 1 and s["scrollable"],
          "opens with nothing typed, and is long enough to need scrolling",
          f"{s['n']} options, scrollable={s['scrollable']}")

    box = anchor(pg)
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(3):
        pg.mouse.wheel(0, 60)
        pg.wait_for_timeout(150)
    s = state(pg)
    check(s["open"] and s["top"] > 0, "the wheel scrolls the list and leaves it open",
          f"open={s['open']} scrollTop={s['top']}")

    box = anchor(pg)
    during = back = False
    if box:
        pg.mouse.move(box["x"] + box["width"] - 3, box["y"] + 40)
        pg.mouse.down()
        pg.mouse.move(box["x"] + box["width"] - 3, box["y"] + 140)
        pg.wait_for_timeout(200)
        during = state(pg)["open"]
        pg.mouse.up()
        pg.wait_for_timeout(400)
        back = pg.evaluate("document.activeElement.dataset "
                           "&& document.activeElement.dataset.col === 'project_name'")
    else:
        name.click()
        pg.wait_for_timeout(400)
    check(during and state(pg)["open"] and back,
          "dragging its own scrollbar leaves it open, and the caret comes back",
          f"during={during} after={state(pg)['open']} focus restored={back}")

    top_before = pg.evaluate("document.getElementById('sugg').getBoundingClientRect().top")
    pg.mouse.move(400, 400)
    pg.mouse.wheel(0, 120)
    pg.wait_for_timeout(500)
    top_after = pg.evaluate("document.getElementById('sugg').getBoundingClientRect().top")
    check(state(pg)["open"] and abs(top_before - top_after) > 10,
          "a page scroll re-anchors the list rather than closing it",
          f"open={state(pg)['open']}, box moved {abs(top_before - top_after):.0f}px")

    typed(pg, "onv")
    sub = options(pg)
    typed(pg, "phase 1 onv")
    tok = options(pg)
    check(sub and tok and sub[0] == tok[0] == "ONV-101 Phase 1",
          "words match in any order, not only as one contiguous string",
          f"'onv' -> {sub[0]!r}; 'phase 1 onv' -> {tok[0]!r}")

    typed(pg, "111")
    ranked = options(pg, 1)
    check(ranked and ranked[0].lower().startswith("onv-111"),
          "a value the query starts is ranked above one that merely contains it",
          f"'111' -> {ranked}")

    typed(pg, "qqqzzz")
    s = state(pg)
    check(s["open"] and "nothing matches" in s["hint"],
          "a query matching nothing shows the whole list instead of vanishing",
          s["hint"].split("·")[0].strip())

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    check(not state(pg)["open"], "Escape closes it")
    pg.keyboard.press("Escape")            # again: cancel the edit, so nothing commits
    pg.wait_for_timeout(400)
    name.click()
    pg.wait_for_timeout(400)
    check(state(pg)["open"], "clicking the field re-opens it")
    pg.click("h1")
    pg.wait_for_timeout(500)
    check(not state(pg)["open"], "clicking outside the field closes it")

    # A value that is NOT in the list, committed with Enter. Nothing may be highlighted
    # by default, or Enter would silently swap in a value the user never chose.
    note = pg.locator(f"{LOC} td[data-col='project_category']").first
    note.click()
    pg.wait_for_timeout(400)
    typed(pg, "Zetamab")
    highlighted = pg.eval_on_selector_all("#sugg .s[aria-selected='true']", "es => es.length")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)
    kept = pg.locator(f"{LOC} td[data-col='project_category']").first.inner_text()
    check(highlighted == 0 and kept == "Zetamab",
          "Enter keeps what was typed when nothing is highlighted",
          f"{highlighted} highlighted, cell now {kept!r}")

    note.click()
    pg.wait_for_timeout(400)
    typed(pg, "a")
    first = options(pg, 1)
    pg.keyboard.press("ArrowDown")
    pg.wait_for_timeout(200)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(900)
    picked = pg.locator(f"{LOC} td[data-col='project_category']").first.inner_text()
    check(first and picked == first[0], "arrow-then-Enter picks from the list",
          f"picked {picked!r}, list offered {first}")


    cat = pg.locator(f"{LOC} td[data-col='project_category']").first
    was = cat.inner_text()
    cat.click()
    pg.wait_for_timeout(400)
    listed = pg.eval_on_selector_all("#sugg .s", "es => es.map(e => e.textContent)")
    want = next((v for v in listed if v != was), None)
    if want:
        pg.locator("#sugg .s", has_text=want).first.click()
        pg.wait_for_timeout(900)
    now = pg.locator(f"{LOC} td[data-col='project_category']").first.inner_text()
    check(now == want and not state(pg)["open"],
          "clicking a value chooses it, commits it and closes the list",
          f"{was!r} -> {now!r} (wanted {want!r})")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
