"""Capture where Standard vs staffed now lives (R-52), into output/.

Not a test - tools/test_gap.py does that. This is so a reader can see the thing the
requirement argues about: the control states the finding, so the alarm is on the page with
nothing opened, and the list is what is a click away.

The three pictures are the three states, in order: the head of Resource by project with
nothing opened, the list, and a month opened on top of the list without losing it.

    python tools/shots_gap.py

Output: output/gap_<n>_<what>.png
"""

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.13.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

PANEL = '#t-overall .panel[data-panel="table-proj"]'


def shot(pg, target, name):
    pg.mouse.move(2, 2)                     # no pop-up hanging over the picture
    pg.wait_for_timeout(250)
    (pg if target is None else pg.locator(target)).screenshot(path=str(OUT / name))
    print(f"  {name}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=2)
    pg.goto(APP)
    pg.wait_for_timeout(250)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_function("() => !document.getElementById('tabs').hidden", timeout=60000)
    pg.wait_for_timeout(1400)

    print("output/ —")

    # 1. THE WHOLE ARGUMENT IN ONE STRIP. The head alone, because what has to be seen is
    #    that the count is readable without anything being opened - a picture of the
    #    whole page would make the point about the page rather than about the control.
    shot(pg, f"{PANEL} .phead", "gap_1_control.png")

    # 2. THE LIST, which is what the click is for.
    pg.evaluate(f"""() => document.querySelector('{PANEL} .phead .gapbtn').click()""")
    pg.wait_for_timeout(800)
    shot(pg, None, "gap_2_list.png")

    # 3. NARROWED (R-53). The reading under the controls is a consequence of what is set
    #    in them - "17 of 66" - while the control in the panel head behind goes on saying
    #    66, because that one is the alarm. Both are in this picture on purpose.
    pg.evaluate("""() => document.querySelector('[data-gapdir="short"]').click()""")
    pg.wait_for_timeout(700)
    shot(pg, None, "gap_4_narrowed.png")
    pg.evaluate("""() => document.querySelector('[data-gapclear]').click()""")
    pg.wait_for_timeout(600)

    # 4. AND A MONTH ON TOP OF IT, not instead of it: Escape comes back to the list,
    #    which is where the next month somebody wants to look at is.
    pg.evaluate("() => document.querySelector('#gapsBody tr.gaprow').click()")
    pg.wait_for_timeout(900)
    shot(pg, None, "gap_3_month_on_top.png")

    browser.close()
