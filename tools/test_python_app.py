"""The Python shell, running, with a browser in front of it.

test_storage_py.py proves the parts. This proves the thing: a real server started
from the packaged folder, a real Chromium pointed at it, a real workbook read from
disk by Python, and the figures on screen compared against the independent Python
reference implementation.

Two claims matter more than the rest, and both are checked on the live page rather
than argued for:

  * THERE IS NO FILE INPUT. Not hidden, not disabled - absent. The whole reason this
    shell exists is that the browser's file interface is stopped on the target
    machine (R-N21), and a shell that still contains one is a shell that will one
    day use it.
  * THE FIGURES ARE THE SAME FIGURES. The engine is shared with the web application
    by construction, but "by construction" is what people say before they find the
    difference. 1,225 person-months, compared one at a time.

    python tools/build_python_app.py && python tools/test_python_app.py
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "dist" / "PM_APP_py"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.10.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def post(url, op, body, key=None, headers=None):
    req = urllib.request.Request(f"{url}/api/{op}", method="POST",
                                 data=json.dumps(body or {}).encode())
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("X-PM-Key", key)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None


def main():
    if not (PKG / "PM_APP.py").exists():
        raise SystemExit("Build it first:  python tools/build_python_app.py")
    if not DUMMY.exists():
        raise SystemExit(f"missing {DUMMY}")

    home = pathlib.Path(tempfile.mkdtemp(prefix="pm-run-"))
    app_dir = home / "PM_APP"
    shutil.copytree(PKG, app_dir)
    print(f"running from {app_dir}")

    proc = subprocess.Popen([sys.executable, str(app_dir / "PM_APP.py"), "--no-browser"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**os.environ, "DISPLAY": ""})
    url = key = None
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if "http://127.0.0.1" in line and "?k=" in line:
            full = line.strip()
            url, key = full.split("/?k=")[0], full.split("/?k=")[1]
            break
    if not url:
        proc.kill()
        raise SystemExit("the application did not start")
    print(f"listening at {url}\n")

    # ---- the reference figures, from the independent implementation --------
    sys.path.insert(0, str(ROOT / "tools"))
    import prap_io                                                   # noqa: E402
    M = prap_io.Model(prap_io.read_xlsx(DUMMY))
    C = prap_io.calculate(M)
    ref = {f"{sid}|{k}": v for (sid, k), v in C["pers_month"].items()}

    try:
        print("the socket, and who may talk to it")
        code, _ = post(url, "caps", {})
        check(code == 403, "no key, no answer", f"HTTP {code}")
        code, _ = post(url, "caps", {}, key="wrong-key-entirely")
        check(code == 403, "a wrong key is no better", f"HTTP {code}")
        code, body = post(url, "caps", {}, key=key)
        check(code == 200 and body["result"]["shell"] == "python",
              "the right key gets an answer")
        check(body["result"]["upload"] is False,
              "and the answer says plainly that this shell does not upload")

        code, _ = post(url, "caps", {}, key=key,
                       headers={"Origin": "https://evil.example"})
        check(code == 403, "another site is refused, key or no key", f"HTTP {code}")
        code, _ = post(url, "caps", {}, key=key,
                       headers={"Sec-Fetch-Site": "cross-site"})
        check(code == 403, "and so is a cross-site fetch", f"HTTP {code}")

        req = urllib.request.Request(f"{url}/api/caps", method="POST", data=b"{}")
        req.add_header("X-PM-Key", key)
        req.add_header("Host", "attacker.example")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        check(code == 403, "a name that is not loopback is refused (DNS rebinding)",
              f"HTTP {code}")

        code, _ = post(url, "no/such/thing", {}, key=key)
        check(code == 404, "an operation that does not exist is a 404")

        try:
            with urllib.request.urlopen(f"{url}/", timeout=10) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        check(code == 403, "the page itself needs the key too", f"HTTP {code}")

        for probe in ("/../version.txt", "/app/index.html", "/pmapp/shell/server.py"):
            try:
                with urllib.request.urlopen(f"{url}{probe}", timeout=10) as r:
                    code = r.status
            except urllib.error.HTTPError as e:
                code = e.code
            check(code == 404, f"nothing is served from disk: {probe}", f"HTTP {code}")

        # ---- the page ------------------------------------------------------
        print("\nthe page")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=CHROME)
            pg = browser.new_page(viewport={"width": 1500, "height": 1000})
            errors = []
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"{url}/?k={key}")
            pg.wait_for_timeout(1500)

            # The sign-in box opens on a first run, because nobody is signed in yet.
            if pg.locator("[data-name]").count():
                pg.fill("[data-name]", "Test Person")
                pg.fill("[data-dept]", "Verification")
                pg.click("[data-ok]")
                pg.wait_for_timeout(600)
            check(not errors, "the page loads without a script error",
                  "; ".join(errors[:2]))

            n_inputs = pg.eval_on_selector_all("input[type=file]", "e => e.length")
            check(n_inputs == 0, "THERE IS NO FILE INPUT ON THE PAGE (R-N21)",
                  f"{n_inputs} found")
            check(pg.evaluate("!!window.__pm"), "the bridge is up")
            check(pg.evaluate("!document.querySelector('#picker')"),
                  "the web application's picker has been removed, not hidden")
            check(pg.locator("#pm-title").count() == 1
                  and pg.locator("#pm-strip").count() == 1,
                  "the window chrome is there - menu and status strip")
            check("Project Management APP" in pg.inner_text("h1"),
                  "and it calls itself by its own name (NR-APP-08)")
            who = pg.inner_text("#pm-who")
            check("Test Person" in who, "who is at the keyboard is on screen", who)

            # ---- import: Python reads the file, the page never asks --------
            print("\nimporting, without the browser seeing a file")
            got = pg.evaluate("""async (p) => {
                const r = await window.__pm.call('file/openSource', {path: p});
                return {name: r.name, size: r.size, bytes: r.bytes.length};
            }""", str(DUMMY))
            check(got["size"] == DUMMY.stat().st_size,
                  "Python read the workbook off the disk",
                  f"{got['name']}, {got['size']:,} bytes")

            pg.evaluate("""async (p) => {
                const r = await window.__pm.call('file/openSource', {path: p});
                const bytes = Uint8Array.from(atob(r.bytes), c => c.charCodeAt(0));
                await window.__pm.adoptBytes(r.name, bytes);
            }""", str(DUMMY))
            pg.wait_for_timeout(2500)

            check(pg.evaluate("!!(S && S.model)"),
                  "and the page read it with the same reader as always")
            counts = pg.evaluate("({p:S.model.raw.Project.length, "
                                 "n:S.model.raw.Person.length, "
                                 "a:S.model.raw.Assignment.length})")
            check(counts["p"] > 0 and counts["n"] > 0,
                  "the data is all there",
                  f"{counts['p']} projects, {counts['n']} people, "
                  f"{counts['a']} assignments")
            fatal = pg.evaluate("S.model.findings.filter(f => f.sev === 'fatal').length")
            check(fatal == 0, "with nothing fatal in the findings")

            # ---- the figures ------------------------------------------------
            app_pm = pg.evaluate("() => { const o = {}; for (const [k, v] of "
                                 "S.calc.persMonth) o[k] = v; return o; }")
            missing = set(ref) ^ set(app_pm)
            worst = max((abs(ref[k] - app_pm[k]) for k in set(ref) & set(app_pm)),
                        default=None)
            check(not missing and worst is not None and worst < 1e-9,
                  "EVERY FIGURE EQUALS THE PYTHON REFERENCE IMPLEMENTATION",
                  f"{len(ref)} person-months compared, worst difference "
                  f"{worst:.2e}" if worst is not None else f"{len(missing)} unmatched")

            for label, tab in (("Overall", "t-overall"),
                               ("Source data (project)", "t-proj"),
                               ("Source data (person)", "t-pers"),
                               ("General assumptions", "t-gen")):
                pg.click(f'button[role=tab][data-tab="{tab}"]')
                pg.wait_for_timeout(700)
                svgs = pg.eval_on_selector_all(f"#{tab} svg", "e => e.length")
                rows = pg.eval_on_selector_all(f"#{tab} tbody tr", "e => e.length")
                check(svgs + rows > 0, f"'{label}' draws",
                      f"{svgs} chart(s), {rows} row(s)")

            # ---- saving, and reading it back --------------------------------
            print("\nkeeping it, which is the other half of why this exists")
            plan = str(home / "PM_APP" / "data" / "test.prap")
            saved = pg.evaluate("""async (p) => {
                const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                return window.__pm.call('ws/saveAs', {sheets, ref: p});
            }""", plan)
            check(os.path.exists(plan), "the plan is on the disk", plan)
            doc = json.loads(pathlib.Path(plan).read_text(encoding="utf-8"))
            check(doc["format"] == "prap-source-data" and doc["format_version"] == 1,
                  "in the interchange format both applications read")
            check(doc["workspace"]["last_saved_by"]["name"] == "Test Person",
                  "stamped with who saved it")

            pg.evaluate("""async (p) => {
                const w = await window.__pm.call('ws/open', {ref: p});
                adopt(w.sheets, 'reopened');
            }""", plan)
            pg.wait_for_timeout(2000)
            again = pg.evaluate("() => { const o = {}; for (const [k, v] of "
                                "S.calc.persMonth) o[k] = v; return o; }")
            worst2 = max((abs(ref[k] - again[k]) for k in set(ref) & set(again)),
                         default=None)
            check(set(again) == set(ref) and worst2 is not None and worst2 < 1e-9,
                  "and re-opening it gives back the identical figures",
                  f"worst difference {worst2:.2e}" if worst2 is not None else "")

            # ---- the claim ---------------------------------------------------
            print("\none writer at a time, on the live application")
            took = pg.evaluate("(p) => window.__pm.call('claim/take', {ref: p})", plan)
            check(took["ok"] and os.path.exists(plan + ".lock"),
                  "taking the claim writes a marker beside the plan")
            held = json.loads(pathlib.Path(plan + ".lock").read_text(encoding="utf-8"))
            check(held["name"] == "Test Person" and held["department"] == "Verification",
                  "which names the person a blocked colleague should ask",
                  f"{held['name']} ({held['department']})")
            holds = pg.evaluate("(p) => window.__pm.call('claim/holds', {ref: p})", plan)
            check(holds["holds"], "and the page can see that it holds it")

            # ---- export ------------------------------------------------------
            print("\ngetting data back out")
            out = str(home / "exported.xlsx")
            wrote = pg.evaluate("""async (p) => {
                const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                const blob = buildXlsx(sheets);
                const u = new Uint8Array(await blob.arrayBuffer());
                let s = ''; for (let i = 0; i < u.length; i += 0x8000)
                    s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
                return window.__pm.call('file/export', {bytes: btoa(s), path: p});
            }""", out)
            check(os.path.exists(out) and wrote["size"] > 5000,
                  "an Excel workbook is written where it was asked to go",
                  f"{wrote['size']:,} bytes")
            back = prap_io.Model(prap_io.read_xlsx(pathlib.Path(out)))
            C2 = prap_io.calculate(back)
            ref2 = {f"{sid}|{k}": v for (sid, k), v in C2["pers_month"].items()}
            worst3 = max((abs(ref[k] - ref2[k]) for k in set(ref) & set(ref2)),
                         default=None)
            check(set(ref2) == set(ref) and worst3 is not None and worst3 < 1e-9,
                  "and the exported workbook gives the same figures again",
                  f"worst difference {worst3:.2e}" if worst3 is not None else "")

            check(not errors, "no script error anywhere in the run",
                  "; ".join(errors[:3]))
            browser.close()

        # ---- nothing left outside its own folder -----------------------------
        print("\nleaving the machine as it found it")
        stray = [p for p in home.rglob("*") if p.is_file()
                 and not str(p).startswith(str(app_dir))
                 and p != pathlib.Path(out)]
        check(not stray, "nothing is written outside the application folder",
              "; ".join(str(p) for p in stray[:3]))
        check((app_dir / "data").is_dir(), "the data folder is beside the application")

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(home, ignore_errors=True)

    print(f"\n{len(fails)} failed")
    for f in fails:
        print(f"  FAILED  {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
