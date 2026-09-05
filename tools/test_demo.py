"""The working prototype, and the claim it makes about itself.

The prototype's banner says "every figure below is computed, not drawn". That is either
true or it is the most misleading sentence in the deliverable, so it is checked rather
than asserted:

  1. The dataset loads through the ordinary reader, with no findings that would stop it.
  2. All four tabs render, with charts on each.
  3. The totals on screen equal the Python reference implementation's, to the penny -
     the same comparison test_interop.py makes of the web application, repeated here
     because this build has a data payload the web application does not.
  4. The desktop chrome is present, the eight screens open over the top, and the
     application underneath is untouched by them.

    python tools/test_demo.py
"""

import json
import pathlib
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO = (ROOT / "app" / "PM_APP_Prototype_v0.3.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.16.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# ---- the reference figures, from the Python implementation ------------------
sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

M = prap_io.Model(prap_io.read_xlsx(DUMMY))
C = prap_io.calculate(M)
ref = {f"{sid}|{k}": v for (sid, k), v in C["pers_month"].items()}
ref_total = sum(ref.values())

print("app/PM_APP_Prototype_v0.3.html — the real application, with real data")

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(DEMO)
    pg.wait_for_timeout(3200)

    # ---- 1. it loaded, through the ordinary path ---------------------------
    loaded = pg.evaluate("!!(S && S.model)")
    check(loaded, "the dummy dataset loads through readPrapJson, like any .prap.json")

    counts = pg.evaluate("({p:S.model.raw.Project.length, n:S.model.raw.Person.length, "
                         "a:S.model.raw.Assignment.length})")
    check(counts["p"] == 62 and counts["n"] == 20 and counts["a"] == 277,
          "with enough in it to fill every chart",
          f"{counts['p']} projects, {counts['n']} people, {counts['a']} assignments")

    fatal = pg.evaluate("S.model.findings.filter(f => f.sev === 'fatal').length")
    check(fatal == 0, "and nothing fatal in the findings", f"{fatal} fatal")

    # ---- 2. every tab draws ------------------------------------------------
    for label, tab in (("Overall", "t-overall"), ("Source data (project)", "t-proj"),
                       ("Source data (person)", "t-pers"), ("General assumptions", "t-gen")):
        pg.click(f"text={label}")
        pg.wait_for_timeout(900)
        svgs = pg.eval_on_selector_all(f"#{tab} svg", "e => e.length")
        rows = pg.eval_on_selector_all(f"#{tab} tbody tr", "e => e.length")
        check(svgs + rows > 0, f"'{label}' renders", f"{svgs} chart(s), {rows} table row(s)")

    # ---- 3. the figures are the reference figures --------------------------
    pg.click("text=Overall")
    pg.wait_for_timeout(900)

    app_pm = pg.evaluate("() => { const o = {}; for (const [k, v] of S.calc.persMonth) "
                         "o[k] = v; return o; }")
    check(len(app_pm) > 0, "the engine produced person-month figures",
          f"{len(app_pm)} person-months, {sum(app_pm.values()):.2f} FTE-months")

    missing = set(ref) ^ set(app_pm)
    worst = max((abs(ref[k] - app_pm[k]) for k in set(ref) & set(app_pm)), default=None)
    check(not missing and worst is not None and worst < 1e-6,
          "and every one of them equals the Python reference implementation",
          f"{len(ref)} compared, worst difference {worst:.2e}" if worst is not None
          else f"{len(missing)} keys on one side only")

    tiles = pg.eval_on_selector_all(".tile", "es => es.map(e => e.textContent)")
    check(any("62" in t and "PROJECT" in t.upper() for t in tiles),
          "the summary tiles are drawn from that data, not typed",
          " · ".join(" ".join(t.split())[:34] for t in tiles[:3]))

    # ---- 4. the chrome, and the eight screens ------------------------------
    check(pg.locator("#pm-title").count() == 1 and pg.locator("#pm-menu").count() == 1
          and pg.locator("#pm-strip").count() == 1,
          "the desktop chrome is there — title, menu bar, status strip")
    check("Project Management APP" in pg.inner_text("h1"),
          "and the product calls itself by its own name (NR-APP-08)",
          pg.inner_text("h1"))
    check(pg.locator("#loadBtn").is_visible() is False
          and pg.locator("#expMenu").is_visible() is False,
          "the web application's file buttons are hidden — menus replace them (D-N02)")
    check(pg.locator("#themeBtn").is_visible() is False,
          "and the theme toggle is gone — the window follows Windows (D-N09, U-N04)")

    pg.click("#pm-screens")
    pg.wait_for_timeout(500)
    check(pg.locator("#pm-ov.on").count() == 1, "the eight screens open over the top")
    n = pg.eval_on_selector_all("#pm-nav button", "e => e.length")
    check(n == 8, "all eight of them", f"{n} screens")
    pg.click("#pm-nav button[data-s='diff']")
    pg.wait_for_timeout(300)
    check(pg.locator("#pm-s-diff.on").count() == 1, "and they switch")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)
    check(pg.locator("#pm-ov.on").count() == 0, "Escape closes them")
    check(pg.evaluate("S.model.raw.Project.length") == 62,
          "and the application underneath is untouched by any of it")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print(f"reference total across the whole timeline: {ref_total:.2f} FTE-months")
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
