"""Capture what the five screen changes of R-45 look like, into output/.

Not a test - the two suites do that. This is so a reader can SEE them without
opening the application: five pictures, one per change.

    python tools/shots_screen.py
"""

import pathlib

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.10.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)


def panel(pg, tab, starts):
    return pg.evaluate_handle(
        """([tab, s]) => [...document.querySelectorAll('#' + tab + ' .panel')]
             .find(e => ((e.querySelector('h2')||{}).textContent || '').startsWith(s))""",
        [tab, starts])


def shot(handle, name):
    handle.as_element().screenshot(path=str(OUT / name))
    print(f"  {name}")


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 1000},
                          device_scale_factor=2)
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)

    print("output/ —")

    # 1. the utilisation chart over a long horizon: the panel scrolls, the labels fit
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(600)
    shot(panel(pg, "t-proj", "Utilisation"), "R45_1_utilisation_2y.png")
    pg.click("#fAll")
    pg.wait_for_timeout(900)
    shot(panel(pg, "t-proj", "Utilisation"), "R45_1_utilisation_long.png")

    # 2 + 3. the three wide tables stacked, and the assignment line under the title
    pg.click('nav button[data-tab="t-pers"]')
    pg.wait_for_timeout(800)
    pg.eval_on_selector(".stack1", "e => e.scrollIntoView({block:'start'})")
    pg.wait_for_timeout(400)
    shot(pg.evaluate_handle("() => document.querySelector('#t-pers .stack1')"),
         "R45_2_stacked_full_width.png")
    shot(pg.evaluate_handle(
        """() => [...document.querySelectorAll('#t-pers .stack1 .panel')]
             .find(e => ((e.querySelector('h2')||{}).textContent||'')
                          .startsWith('Monthly estimation'))"""),
         "R45_3_assignment_line.png")

    # 5. the two-line headings. The panel, with its table scrolled to the top - the
    # heading row is sticky, so a box left mid-scroll captures the rows and not it.
    pg.evaluate("""() => {
      const box = document.querySelector('#t-pers table.data-t[data-sheet="Assignment"]')
                          .closest('.scrollx');
      box.scrollTop = 0; box.scrollLeft = 0;
      box.closest('.panel').scrollIntoView({block:'center'});
    }""")
    pg.wait_for_timeout(500)
    shot(pg.evaluate_handle(
        """() => document.querySelector('#t-pers table.data-t[data-sheet="Assignment"]')
                         .closest('.panel')"""),
         "R45_5_headings.png")

    # 4. legend picking, before and after
    pg.click('nav button[data-tab="t-overall"]')
    pg.wait_for_timeout(900)
    shot(panel(pg, "t-overall", "Monthly demand by person"), "R45_4_stack_before.png")
    key = pg.eval_on_selector_all(
        "#t-overall .panel", """(ps) => ps
          .find(e => (e.querySelector('h2')||{}).textContent === 'Monthly demand by person')
          .querySelectorAll('ul.legend li[data-s]')[2].getAttribute('data-s')""")
    pg.click(f'#t-overall ul.legend li[data-s="{key}"]')
    pg.wait_for_timeout(500)
    shot(panel(pg, "t-overall", "Monthly demand by person"), "R45_4_stack_picked.png")

    # and the same pick reaching the other charts on the tab
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    pkey = pg.eval_on_selector_all(
        "#t-overall .panel", """(ps) => ps
          .find(e => (e.querySelector('h2')||{}).textContent === 'Monthly resource trend')
          .querySelectorAll('ul.legend li[data-s]')[1].getAttribute('data-s')""")
    pg.click(f'#t-overall ul.legend li[data-s="{pkey}"]')
    pg.wait_for_timeout(500)
    shot(panel(pg, "t-overall", "Monthly resource trend"), "R45_4_trend_picked.png")
    shot(panel(pg, "t-overall", "Project timeline"), "R45_4_timeline_picked.png")

    browser.close()
print("done")
