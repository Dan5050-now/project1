"""Capture what REQ-DSH-19 is for, into output/.

Not a test - tools/test_pinned.py does that. The argument for freezing two columns is a
pair of pictures and nothing else: the same table, scrolled to the same place, with and
without them. Without, the rows on the right belong to nobody.

    python tools/shots_pinned.py

Output: output/pin_<n>_<what>.png
"""

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.20.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

PANEL = '#t-proj .panel[data-panel="projects"]'
SCROLLED = 1400          # far enough out that no unpinned column names the row


def shot(pg, name):
    pg.mouse.move(2, 2)                      # no pop-up over the picture
    pg.wait_for_timeout(300)
    pg.locator(PANEL).screenshot(path=str(OUT / name))
    print(f"  {name}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=120000)
    pg.wait_for_timeout(2500)
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(1500)

    print("output/ —")
    shot(pg, "pin_1_at_rest.png")

    pg.evaluate("""x => { document.querySelector("#t-proj .data-t[data-sheet='Project']")
      .closest('.scrollx').scrollLeft = x; }""", SCROLLED)
    pg.wait_for_timeout(500)
    shot(pg, "pin_2_scrolled.png")

    # THE SAME VIEW WITH THE FREEZING TURNED OFF, which is what it looked like before and
    # is the whole of the argument. Done by dropping the attribute the stylesheet hangs on,
    # so nothing else about the page changes between the two pictures.
    pg.evaluate("""() => { const t = document.querySelector(
      "#t-proj .data-t[data-sheet='Project']");
      t.dataset.pinWas = t.dataset.pin; delete t.dataset.pin; }""")
    pg.wait_for_timeout(400)
    shot(pg, "pin_3_scrolled_without.png")

    browser.close()
