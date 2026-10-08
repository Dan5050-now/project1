"""Capture what REQ-DSH-18 looks like in the application, into output/.

Not a test - tools/test_zoom.py does that, and it asserts figures. This is so a reader can
SEE the thing the figures stand for: the same table before and after, at the two sizes
that made the feature worth building.

The point is the pair. "The entry table is capped at 340px on a page 1400px wide" is a
sentence; one picture of a sheet seen through a slot above the same sheet seen whole is
the argument.

    python tools/shots_zoom.py

Output: output/zoom_<n>_<what>.png
"""

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
SMALL = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.12.xlsx"
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.20.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)


def load(pg, path, wait):
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=120000)
    pg.wait_for_timeout(wait)


def tab(pg, name):
    pg.click(f'nav button[data-tab="{name}"]')
    pg.wait_for_timeout(1200)


def press(pg, tabid, name):
    # Through the DOM: the driver's own click scrolls the page first, and these pictures
    # are of the page as the reader left it.
    pg.evaluate("""a => document.querySelector(
      '#' + a.tab + ' .panel[data-panel="' + a.name + '"] button.zoombtn').click()""",
                {"tab": tabid, "name": name})
    pg.wait_for_timeout(700)


def shot(pg, name):
    pg.mouse.move(2, 2)                      # no pop-up hanging over the picture
    pg.wait_for_timeout(200)
    pg.screenshot(path=str(OUT / name))
    print(f"  {name}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)

    print("output/ —")
    load(pg, SMALL, 1200)
    tab(pg, "t-proj")
    pg.evaluate("() => window.scrollTo(0, 0)")
    pg.wait_for_timeout(250)

    # 1 and 2. THE WHOLE POINT, in two pictures: the Projects sheet in its panel, and the
    #    same sheet with the window. Full-page shots here rather than the panel alone,
    #    because what the second one has to show is the filter bar and the header GOING
    #    and the edit bar STAYING.
    shot(pg, "zoom_1_page.png")
    press(pg, "t-proj", "projects")
    shot(pg, "zoom_2_fullscreen.png")

    # 3. AND IT IS STILL THE APPLICATION. A cell being typed into, from inside it, with
    #    the unsaved-change count and Save live in the band above.
    cell = "#t-proj .panel[data-panel='projects'] td[data-col='project_name']"
    pg.locator(cell).nth(1).click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("CAR-102 Phase 2 — typed here")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    shot(pg, "zoom_3_editing.png")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # 4. THE 62-PROJECT PLAN, which is where the width is worth the most: twenty-four
    #    months of the month grid across the screen instead of scrolling for them.
    load(pg, BIG, 3000)
    press(pg, "t-overall", "table-proj")
    shot(pg, "zoom_4_month_grid.png")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # 5. TWO REGIONS IN ONE PANEL, the case the height-sharing rule exists for: a matrix
    #    of several hundred rows above a matrix of eight, and both readable.
    tab(pg, "t-gen")
    press(pg, "t-gen", "gen-rf")
    shot(pg, "zoom_5_two_matrices.png")

    browser.close()
