"""The window and the application go together (NR-DEP-17).

Reported from the field: running the desktop edition opens a console window, and
closing the browser left it open. The console then sits there owning a port, a claim
on a plan nobody has open, and a data folder the next run has to argue with - and the
only way to be rid of it is to know it is there and close it by hand.

The console IS the application; the page is its window. Closing the window now stops
the application, a few seconds later. What makes this more than one line is everything
it must NOT do:

  1. NOT BEFORE A PAGE HAS EVER CONNECTED. A slow browser, a machine where the URL is
     pasted in by hand, --no-browser for the tests: none of those is a countdown.
  2. NOT ON A RELOAD. `pagehide` fires on a reload exactly as it does on a close, and
     at that moment the two are indistinguishable - so the close message is not
     believed until a grace period has passed without anybody saying hello again. If it
     were, F5 would be a way of losing your work.
  3. NOT WHILE ANOTHER PAGE IS STILL OPEN. Two tabs, close one, it carries on.
  4. NOT WHILE SOMEBODY IS STILL SIGNING IN. Liveness is registered BEFORE the
     start-up awaits, because one of those waits is a person typing their name - and
     "open it, look at it, close it again" is the case the complaint is actually
     about. Registering afterwards would mean that case never registered at all.
  5. NOT AT ALL, with --keep-running, for a headless run or for somebody who wants to
     shut one browser window and open another.

And what it must do: stop, within seconds, when the last page goes.

    python tools/test_shutdown.py
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
PKG = ROOT / "dist" / "PM_APP_py"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + str(detail) if detail else ''}")
    if not ok:
        fails.append(label)


def start(extra=()):
    """A fresh installation in its own folder, with no browser opened for it."""
    home = pathlib.Path(tempfile.mkdtemp(prefix="pm-shut-"))
    app = home / "PM_APP"
    shutil.copytree(PKG, app, ignore=shutil.ignore_patterns("data"))
    proc = subprocess.Popen(
        [sys.executable, str(app / "PM_APP.py"), "--no-browser", *extra],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        env={**os.environ, "DISPLAY": ""})
    url = key = None
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if "http://127.0.0.1" in line and "?k=" in line:
            url = line.strip().split("/?k=")[0]
            key = line.strip().split("/?k=")[1]
            break
    return proc, url, key


def still_up(proc, secs):
    """True if it is STILL RUNNING after `secs`. Waits on the process rather than
    polling a pid, so a shutdown part way through the window is caught immediately."""
    try:
        proc.wait(timeout=secs)
        return False
    except subprocess.TimeoutExpired:
        return True


def sign_in(pg):
    if pg.locator("[data-name]").count():
        pg.fill("[data-name]", "Kim Soo-jin")
        pg.click("[data-ok]")
        pg.wait_for_timeout(1000)


if not PKG.exists():
    check(False, "dist/PM_APP_py is built", "run tools/build_python_app.py first")
    print("\nFAILURES: " + ", ".join(fails))
    sys.exit(1)

proc, url, key = start()
print("1. before any page has connected")
check(url is not None, "it starts and prints its address")
check(still_up(proc, 8),
      "and stays up with nothing connected — a slow browser, or a URL somebody is "
      "about to paste in, is not a reason to give up")

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.set_default_timeout(20000)
    pg.goto(f"{url}/?k={key}")
    pg.wait_for_timeout(2500)

    print("\n2. a page is open, and liveness does not wait for the person")
    check(pg.locator("[data-name]").count() > 0,
          "a first run stops at the sign-in card, which waits on a HUMAN")
    check(still_up(proc, 8),
          "and it stays up while that card is showing — registered before the "
          "start-up awaits, or 'open it, look at it, close it' would never register")
    sign_in(pg)
    check(pg.evaluate("() => !!(window.__pm && window.__pm.pageId)"),
          "once signed in the bridge is up and the page has an identity of its own")
    check(still_up(proc, 6), "and it stays up while the page is open")

    print("\n3. a RELOAD must not kill it")
    pg.reload()
    pg.wait_for_timeout(2500)
    sign_in(pg)
    check(still_up(proc, 9),
          "still up after a reload — pagehide fires on a reload exactly as on a "
          "close, and F5 must never be a way of losing your work")

    print("\n4. a SECOND page, and closing one of them")
    pg2 = ctx.new_page()
    pg2.goto(f"{url}/?k={key}")
    pg2.wait_for_timeout(2000)
    pg2.close()
    time.sleep(0.5)
    check(still_up(proc, 9), "closing one of two pages leaves it up")

    print("\n5. closing the LAST page stops it")
    t0 = time.time()
    pg.close()
    gone = not still_up(proc, 30)
    check(gone, "the application stopped by itself",
          f"after {time.time() - t0:.1f}s")
    browser.close()

out = proc.stdout.read() if proc.stdout else ""
check("page was closed" in out,
      "and said why, rather than vanishing",
      next((ln for ln in out.splitlines() if "closed" in ln), "").strip()[:70])

print("\n6. --keep-running opts out of all of it")
proc2, url2, key2 = start(["--keep-running"])
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page()
    pg.goto(f"{url2}/?k={key2}")
    pg.wait_for_timeout(2000)
    sign_in(pg)
    pg.close()
    browser.close()
check(still_up(proc2, 14),
      "still up after the page closed — a headless run, or one browser window shut "
      "and another opened, is a thing somebody may want")
proc2.kill()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
