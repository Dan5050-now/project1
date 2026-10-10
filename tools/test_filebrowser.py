"""The file windows, and the session that cannot time out (R-63) - on the live
Python edition, with a browser in front of it.

Two requests from the field, checked together because both live in the window chrome
of the Python edition:

  1. "Make the file search windows more graphical and useful." The in-page browser
     gains a sidebar of places, a path bar with back / forward / up, a picture and a
     coloured type badge per file, the date AND how long ago, date bands, a filter
     box, list and tiles, a details pane, the keyboard, who saved a plan and who is
     editing it, a save box that warns before replacing, and it remembers where it
     was. What it already guaranteed still holds: newest first (R-56), and a
     double-click opens the folder it was on (R-57).
  2. "Session time-out shouldn't apply to a private file, and a time-out should be a
     pop-up." A plan in My plans takes no hold - no marker, no heartbeat, nothing to
     lapse. A plan anywhere else keeps the one-writer rule, and when its hold lapses
     and a colleague takes over, a pop-up says so and offers the safe way on.

    python tools/build_python_app.py && python tools/test_filebrowser.py
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "dist" / "PM_APP_py"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.14.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def iso(t):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + ".000Z"


def colleague_lock(plan, name="A Colleague", dept="Elsewhere", when=None):
    t = iso(when or time.time())
    pathlib.Path(plan + ".lock").write_text(json.dumps(
        {"name": name, "department": dept, "machine": "OTHER-PC", "pid": 1,
         "since": t, "heartbeat": t}), encoding="utf-8")


ROWS = """() => [...document.querySelectorAll('.fb [data-row]')].map(r => r._entry.name)"""


def browse(pg, opts):
    """Open the browser with these options; its answer lands in window.__got."""
    pg.evaluate("""o => { window.__got = 'pending';
        window.__pm.browseFor(o).then(v => { window.__got = v; }); }""", opts)
    pg.wait_for_selector(".fb [data-files]")
    pg.wait_for_timeout(700)


def cancel(pg):
    if pg.locator(".fb").count():
        pg.click(".fb [data-cancel]")
        pg.wait_for_timeout(300)


def main():
    if not (PKG / "PM_APP.py").exists():
        raise SystemExit("Build it first:  python tools/build_python_app.py")
    home = pathlib.Path(tempfile.mkdtemp(prefix="pm-fb-"))
    app_dir = home / "PM_APP"
    shutil.copytree(PKG, app_dir, ignore=shutil.ignore_patterns("data"))
    proc = subprocess.Popen([sys.executable, str(app_dir / "PM_APP.py"), "--no-browser"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**os.environ, "DISPLAY": "", "HOME": str(home)})
    url = key = None
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if "http://127.0.0.1" in line and "?k=" in line:
            url, key = line.strip().split("/?k=")
            break
    if not url:
        proc.kill()
        raise SystemExit("the application did not start")

    # A folder of things to find, OUTSIDE the application's own folders.
    tree = home / "Work"
    (tree / "Exports").mkdir(parents=True)
    (tree / "Sub" / "Deep" / "Deeper").mkdir(parents=True)
    (tree / "Sub" / "Other").mkdir(parents=True)
    now = time.time()
    files = {"old_plan.xlsx": now - 400 * 86400, "week_plan.xlsx": now - 2 * 3600,
             "today_plan.xlsx": now - 60, "data.prap.json": now - 30 * 86400,
             "notes.txt": now - 10}
    for n, t in files.items():
        (tree / "Exports" / n).write_bytes(b"x" * (2048 if n.endswith("xlsx") else 300))
        os.utime(tree / "Exports" / n, (t, t))
    (tree / "Exports" / "today_plan.xlsx.lock").write_text("{}")
    (tree / "Sub" / "inside.xlsx").write_bytes(b"x")

    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(executable_path=CHROME if os.path.isfile(CHROME) else None)
            pg = b.new_page(viewport={"width": 1440, "height": 950})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("dialog", lambda d: d.accept())
            pg.goto(f"{url}/?k={key}")
            pg.wait_for_timeout(1500)
            if pg.locator("[data-name]").count():
                pg.fill("[data-name]", "Test Person")
                pg.fill("[data-dept]", "Verification")
                pg.click("[data-ok]")
                pg.wait_for_timeout(600)
            where = pg.evaluate("() => window.__pm.state().where")
            exports = str(tree / "Exports")

            # ================================================== 1. the file windows
            print("1. the file windows (R-63)")
            browse(pg, {"title": "Choose source data", "suffixes": [".xlsx", ".json"],
                        "okLabel": "Open", "start": exports})
            side = pg.eval_on_selector_all(".fb-side", "es => es.map(e => e.innerText)")[0]
            places = pg.eval_on_selector_all(".fb-place.place span", "es => es.map(e => e.textContent)")
            check(places == ["My plans", "Team plans"] and "THIS COMPUTER" in side.upper()
                  and "Home" in side,
                  "A SIDEBAR OF PLACES - the two plan folders first, then this computer",
                  " · ".join(places))
            names = pg.evaluate(ROWS)
            check(names == ["today_plan.xlsx", "week_plan.xlsx", "data.prap.json", "old_plan.xlsx"],
                  "newest first, as before (R-56)", " > ".join(names))
            row0 = pg.evaluate("""() => { const r = document.querySelector('.fb [data-row]');
                return {dt: r.querySelector('.dt').textContent, ago: r.querySelector('.ago').textContent,
                        badge: r.querySelector('.fb-doc b').textContent,
                        newest: !!r.querySelector('.pm-new')}; }""")
            want = time.strftime("%Y-%m-%d %H:%M", time.localtime(files["today_plan.xlsx"]))
            check(row0["dt"] == want and row0["ago"] in ("just now", "1 min ago")
                  and row0["badge"] == "XLSX" and row0["newest"],
                  "EVERY FILE SAYS WHAT IT IS AND WHEN - a type badge, the exact time and how "
                  "long ago, and the newest marked", f"{row0['badge']} {row0['dt']} · {row0['ago']}")
            badges = pg.eval_on_selector_all(".fb [data-row] .fb-doc b", "es => es.map(e => e.textContent)")
            kinds = pg.eval_on_selector_all(".fb [data-row] .fb-doc", "es => es.map(e => e.className)")
            check(badges[2] == "JSON" and "js" in kinds[2] and "xl" in kinds[0],
                  "an interchange file is badged and coloured apart from a workbook",
                  ", ".join(badges))
            bands = pg.eval_on_selector_all(".fb .fb-band", "es => es.map(e => e.textContent)")
            # Said the way the window decides it, so a run that crosses midnight still agrees.
            first = ("Today" if time.localtime(files["today_plan.xlsx"]).tm_yday
                     == time.localtime().tm_yday else "Yesterday")
            check(bands and bands[0] == first and bands[-1] == "Older",
                  "FILES ARE GROUPED BY WHEN - Today first, Older last", " / ".join(bands))
            note = pg.inner_text(".fb [data-note]")
            check("1 other file(s) are not shown" in note and "today_plan.xlsx.lock" not in str(names),
                  "the files of other types are counted, not silently missing - and the "
                  "application's own side files are not offered", note[:90])

            pg.click(".fb [data-sort='name']")
            pg.wait_for_timeout(400)
            check(pg.evaluate(ROWS) == sorted(names, key=str.lower),
                  "Name sorts by name", " > ".join(pg.evaluate(ROWS)))
            pg.click(".fb [data-sort='date']")
            pg.wait_for_timeout(400)

            pg.fill(".fb [data-find]", "week")
            pg.wait_for_timeout(300)
            check(pg.evaluate(ROWS) == ["week_plan.xlsx"]
                  and "1 of 4 item(s) match" in pg.inner_text(".fb [data-note]"),
                  "THE FILTER BOX NARROWS THE FOLDER as you type",
                  pg.inner_text(".fb [data-note]")[:60])
            pg.fill(".fb [data-find]", "")
            pg.wait_for_timeout(300)

            pg.locator(".fb [data-row]", has_text="old_plan.xlsx").click()
            pg.wait_for_timeout(300)
            info = pg.inner_text(".fb [data-info]")
            check("old_plan.xlsx" in info and "Excel workbook" in info and "2 KB" in info
                  and "Modified" in info and exports in info.replace("\n", ""),
                  "A FILE PICKED SHOWS ITS DETAILS - type, size, date, where",
                  " | ".join(info.split("\n")[:4]))
            check(not pg.is_disabled(".fb [data-ok]"), "and Open is ready")

            pg.click(".fb [data-view='tiles']")
            pg.wait_for_timeout(300)
            tiles = pg.locator(".fb .fb-row.tile").count()
            check(tiles == 4, "THE TILES VIEW draws the same files as cards", f"{tiles} tile(s)")
            pg.click(".fb [data-view='list']")
            pg.wait_for_timeout(300)
            cancel(pg)

            # ---- moving about: the path bar, back / forward / up, the keyboard -----
            browse(pg, {"title": "x", "suffixes": [".xlsx"], "start": str(tree)})
            pg.locator(".fb [data-row]", has_text="Sub").first.click()
            pg.wait_for_timeout(800)
            pg.locator(".fb [data-row]", has_text="Deep").first.click()
            pg.wait_for_timeout(800)
            crumbs = pg.eval_on_selector_all(".fb .fb-crumb", "es => es.map(e => e.textContent.trim())")
            check(crumbs[-3:] == ["Work", "Sub", "Deep"],
                  "THE PATH BAR NAMES EVERY STEP, each one a button", " › ".join(crumbs))
            pg.locator(".fb .fb-crumb", has_text="Work").click()
            pg.wait_for_timeout(800)
            at = lambda: pg.eval_on_selector_all(".fb .fb-crumb", "es => es.map(e => e.textContent.trim())")[-1]
            check(at() == "Work", "two levels up is one click on the path")
            pg.click(".fb [data-nav='back']")
            pg.wait_for_timeout(800)
            back1 = at()
            pg.click(".fb [data-nav='fwd']")
            pg.wait_for_timeout(800)
            check(back1 == "Deep" and at() == "Work", "and Back and Forward retrace it",
                  f"back → {back1}, forward → {at()}")
            pg.click(".fb [data-files]")
            pg.keyboard.press("ArrowDown")
            pg.keyboard.press("ArrowDown")
            aim = pg.evaluate("() => document.querySelector('.fb [data-row].kb')._entry.name")
            pg.keyboard.press("Enter")
            pg.wait_for_timeout(800)
            check(at() == aim, "THE KEYBOARD WORKS - arrows move, Enter opens a folder", at())
            pg.keyboard.press("Backspace")
            pg.wait_for_timeout(800)
            check(at() == "Work", "and Backspace goes up")
            cancel(pg)

            # R-57, on the new screen: a double-click opens THAT folder.
            browse(pg, {"title": "x", "suffixes": [".xlsx"], "start": str(tree)})
            bb = pg.locator(".fb [data-row]", has_text="Sub").first.bounding_box()
            x, y = bb["x"] + 80, bb["y"] + bb["height"] / 2
            pg.mouse.click(x, y)
            pg.wait_for_timeout(150)
            pg.mouse.click(x, y, click_count=2)
            pg.wait_for_timeout(900)
            check(at() == "Sub" and {"Deep", "Other", "inside.xlsx"} <= set(pg.evaluate(ROWS)),
                  "a double-click on a folder opens that folder and lists what is in it (R-57)",
                  f"{at()}: {pg.evaluate(ROWS)}")
            pg.wait_for_timeout(500)
            pg.locator(".fb [data-row]", has_text="inside.xlsx").dblclick()
            pg.wait_for_timeout(500)
            check(str(pg.evaluate("window.__got")).endswith("inside.xlsx"),
                  "and a double-click on a file chooses it", str(pg.evaluate("window.__got")))

            # ---- it remembers ---------------------------------------------------------
            browse(pg, {"title": "x", "suffixes": [".xlsx"]})
            check(at() == "Sub", "IT OPENS WHERE THIS KIND OF WINDOW WAS LAST USED", at())
            recent = pg.eval_on_selector_all(".fb .fb-place", "es => es.map(e => e.textContent.trim())")
            check("Sub" in recent, "and the folder is under Recent folders", ", ".join(recent))
            cancel(pg)

            # ---- saving: the name in its own box, and a warning before replacing ------
            browse(pg, {"title": "Export to", "folders": True, "name": "old_plan.xlsx",
                        "okLabel": "Export", "start": exports})
            warn = pg.inner_text(".fb [data-warn]") if pg.is_visible(".fb [data-warn]") else ""
            check(pg.input_value(".fb [data-name]") == "old_plan.xlsx"
                  and "will be replaced" in warn,
                  "SAVING NAMES THE FILE IN ITS OWN BOX, and warns before replacing one", warn)
            pg.fill(".fb [data-name]", "fresh.xlsx")
            pg.wait_for_timeout(200)
            check(not pg.is_visible(".fb [data-warn]"), "a new name is not warned about")
            pg.click(".fb [data-ok]")
            pg.wait_for_timeout(400)
            check(pg.evaluate("window.__got") == os.path.join(exports, "fresh.xlsx"),
                  "and Save answers the folder on screen plus that name",
                  str(pg.evaluate("window.__got")))

            # ---- a plan says who saved it and who is editing it ----------------------
            team = where["shared"]
            os.makedirs(team, exist_ok=True)
            plan = os.path.join(team, "Team_plan.prap")
            pathlib.Path(plan).write_text(json.dumps({
                "format": "prap-source-data", "format_version": 1,
                "workspace": {"app": "PM_APP", "last_saved": iso(now - 3600),
                              "last_saved_by": {"name": "Saver Kim", "department": "DM"}},
                "sheets": {}}, indent=1), encoding="utf-8")
            colleague_lock(plan, "Editor Lee", "Stats")
            browse(pg, {"title": "Open a plan", "suffixes": [".prap"], "start": team})
            row = pg.locator(".fb [data-row]", has_text="Team_plan.prap").first
            txt = row.inner_text() if row.count() else ""
            check("Saved by Saver Kim" in txt and "Editor Lee editing" in txt
                  and row.locator(".fb-doc b").inner_text() == "PLAN",
                  "A PLAN SAYS WHO SAVED IT AND WHO IS EDITING IT, before it is opened",
                  " ".join(txt.split())[:90])
            row.click()
            pg.wait_for_timeout(300)
            info = pg.inner_text(".fb [data-info]")
            check("Editing now" in info and "Editor Lee (Stats)" in info and "Saver Kim" in info,
                  "and its details say so in full", " | ".join(info.split("\n")[-6:]))
            check(pg.eval_on_selector_all(".fb .fb-crumb.place", "es => es.map(e => e.textContent.trim())")
                  == ["Team plans"], "inside Team plans the path starts at the place's own name")
            cancel(pg)
            os.remove(plan + ".lock")

            # ============================================ 2. sessions and time-outs
            print("\n2. a plan of your own cannot time out; a team plan says so when it does")
            pg.evaluate("""async p => {
                const got = await window.__pm.call('file/openSource', {path: p});
                await window.__pm.adoptBytes(got.name,
                    Uint8Array.from(atob(got.bytes), c => c.charCodeAt(0)));
            }""", str(DUMMY))
            pg.wait_for_timeout(2500)
            save_as = """async p => { const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                await window.__pm.call('ws/saveAs', {sheets, ref: p}); }"""
            mine = os.path.join(where["workspaces"], "Mine.prap")
            pg.evaluate(save_as, mine)
            pg.evaluate("p => window.__pm.openPlan(p)", mine)
            pg.wait_for_timeout(1200)
            pill = pg.inner_text("#pm-hold") if pg.is_visible("#pm-hold") else ""
            check(pg.evaluate("() => window.__pm.state().privatePlan") is True
                  and "no time-out" in pill,
                  "A PLAN IN MY PLANS IS KNOWN AS YOUR OWN, and the strip says it cannot time out",
                  pill)
            took = pg.evaluate("p => window.__pm.call('claim/take', {ref: p})", mine)
            ok = pg.evaluate("() => window.__pm.takeClaimOnEdit()")
            check(took.get("private") is True and ok is True and not os.path.exists(mine + ".lock")
                  and pg.evaluate("() => window.__pm.state().holds") is False,
                  "IT TAKES NO HOLD - no marker beside it, no heartbeat, nothing to lapse",
                  f"lock file: {os.path.exists(mine + '.lock')}")
            deep = os.path.join(where["workspaces"], "2026", "Q4.prap")
            os.makedirs(os.path.dirname(deep), exist_ok=True)
            pg.evaluate(save_as, deep)
            took = pg.evaluate("p => window.__pm.call('claim/take', {ref: p})", deep)
            check(took.get("private") is True and not os.path.exists(deep + ".lock"),
                  "and the same in a folder inside My plans")
            check(pg.evaluate("() => window.__pm.checkHold()") is False
                  and not pg.is_visible(".pm-alert"),
                  "so the time-out check has nothing to report on it")

            team_plan = os.path.join(team, "Shared.prap")
            pg.evaluate(save_as, team_plan)
            pg.evaluate("p => window.__pm.openPlan(p)", team_plan)
            pg.wait_for_timeout(1200)
            ok = pg.evaluate("() => window.__pm.takeClaimOnEdit()")
            check(ok is True and os.path.exists(team_plan + ".lock")
                  and pg.evaluate("() => window.__pm.state().holds") is True
                  and pg.evaluate("() => window.__pm.state().privatePlan") is False,
                  "A TEAM PLAN STILL TAKES THE HOLD - one writer at a time is unchanged")
            colleague_lock(team_plan)                     # our hold lapsed; they took it
            pg.evaluate("() => document.dispatchEvent(new Event('visibilitychange', {bubbles: true}))")
            pg.wait_for_timeout(1500)
            alert = pg.inner_text(".pm-alert") if pg.is_visible(".pm-alert") else ""
            check("timed out" in alert and "A Colleague (Elsewhere)" in alert
                  and "Nothing on screen is lost" in alert,
                  "WHEN THE HOLD LAPSES, A POP-UP SAYS SO - who took over, and that nothing on "
                  "screen is lost - the moment the window is looked at again",
                  " ".join(alert.split())[:110])
            btns = pg.eval_on_selector_all(".pm-alert .foot .btn", "es => es.map(e => e.textContent)")
            check(btns == ["Reload the team's plan", "Decide later", "Save my version to My plans"]
                  and "primary" in pg.get_attribute(".pm-alert [data-keep]", "class"),
                  "with the three ways on, the safe one as the main button", " | ".join(btns))
            check(pg.is_visible("#pm-keep") and "timed out" in pg.inner_text("#pm-hold"),
                  "and the bar and the strip say it too, for after it is closed")
            pg.click(".pm-alert [data-later]")
            pg.wait_for_timeout(300)
            pg.evaluate("() => window.__pm.checkHold()")
            pg.wait_for_timeout(500)
            check(not pg.is_visible(".pm-alert"), "said once, not every thirty seconds")

            # Again, and this time take the way out it offers.
            os.remove(team_plan + ".lock")
            pg.evaluate("p => window.__pm.openPlan(p)", team_plan)
            pg.wait_for_timeout(1200)
            pg.evaluate("() => window.__pm.takeClaimOnEdit()")
            colleague_lock(team_plan)
            theirs = pathlib.Path(team_plan).read_text(encoding="utf-8")
            check(pg.evaluate("() => window.__pm.checkHold()") is True and pg.is_visible(".pm-alert"),
                  "the thirty-second check finds it too")
            before = set(os.listdir(where["workspaces"]))
            pg.click(".pm-alert [data-keep]")
            pg.wait_for_timeout(1800)
            new = sorted(set(os.listdir(where["workspaces"])) - before)
            st = pg.evaluate("() => window.__pm.state()")
            check(len(new) == 1 and new[0].endswith(".prap") and st["privatePlan"] is True
                  and pathlib.Path(team_plan).read_text(encoding="utf-8") == theirs
                  and "no time-out" in pg.inner_text("#pm-hold"),
                  "ITS MAIN BUTTON KEEPS YOUR WORK IN MY PLANS - where it cannot time out - and "
                  "the team's plan is untouched", ", ".join(new))

            check(not errors, "no script error anywhere in the run", "; ".join(errors[:2]))
            b.close()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        if proc.stdout:
            proc.stdout.close()
        shutil.rmtree(home, ignore_errors=True)

    print(f"\nFAILURES: {'none' if not fails else len(fails)}")
    for f in fails:
        print(f"  FAILED  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
