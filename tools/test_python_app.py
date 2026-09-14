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
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.18.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# Enough state for discardEdits() to run: it puts the snapshot back, so there has to
# be one. Kept out of the call site because it is scaffolding, not the check.
DISCARD_SETUP = """() => {
    S.snapshot = {};
    for (const s of REQUIRED_SHEETS) S.snapshot[s] = S.model.raw[s].map(r => ({...r}));
    S.pending.push({at: new Date(), sheet: 'Project', row: 1,
                    col: 'project_name', from: 'x', to: 'y'});
    renderDirty();
}"""

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
    # Copy the APPLICATION, not whatever a previous run left beside it. data/ is the
    # user's folder; carrying one in means this test starts signed in as somebody a
    # different test invented, and the identity checks below then pass or fail on
    # leftovers rather than on the run in front of them.
    shutil.copytree(PKG, app_dir, ignore=shutil.ignore_patterns("data"))
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

            # ---- THE WIRING ---------------------------------------------------
            # Three operations existed in the shell, were tested at the storage layer,
            # and were called by nothing. The storage tests passed and the figures were
            # right, so nothing failed - which is exactly why these checks are here and
            # not only there. A function with no caller is a requirement with no
            # implementation (NR-STO-07, NR-STO-15, NR-STO-16).
            print("\nthe wiring - an operation nobody calls is a requirement nobody met")
            page_src = (PKG / "app" / "index.html").read_text(encoding="utf-8")
            for op in ("ws/stat", "journal/write", "journal/clear", "claim/release"):
                check(f'"{op}"' in page_src, f"the page actually calls {op}")

            # Release, which NR-STO-15 says happens the moment the holder is finished.
            pg.evaluate("(p) => window.__pm.call('claim/release', {ref: p})", plan)
            check(not os.path.exists(plan + ".lock"),
                  "releasing gives the plan back at once, not at its expiry")

            # Moving to ANOTHER plan is being finished with this one. Until the beat
            # could be stopped, the old plan stayed claimed for half an hour by a
            # session that had left it.
            other = str(home / "PM_APP" / "data" / "other.prap")
            pg.evaluate("""async (b) => {
                const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                await window.__pm.call('ws/saveAs', {sheets, ref: b});
            }""", other)
            pg.evaluate("(p) => window.__pm.call('claim/take', {ref: p})", plan)
            check(os.path.exists(plan + ".lock"), "claimed again, to move away from it")
            pg.evaluate("(b) => window.__pm.openPlan(b)", other)
            pg.wait_for_timeout(1500)
            check(not os.path.exists(plan + ".lock"),
                  "and opening another plan hands the first one back (NR-STO-15)")


            # 'Leave without change' - the path that was quietly broken while this was
            # a wrapper rather than a listener: shell/web binds the button to the
            # function itself, so replacing the global afterwards left the button
            # calling the original and the claim never came back.
            # Back on `plan`, because the check above left the window on `other` and a
            # release is about the plan the window actually has open.
            pg.evaluate("(p) => window.__pm.openPlan(p)", plan)
            pg.wait_for_timeout(1200)
            pg.evaluate("(p) => window.__pm.call('claim/take', {ref: p})", plan)
            pg.evaluate(DISCARD_SETUP)
            pg.wait_for_timeout(300)
            pg.evaluate("() => document.getElementById('discardBtn').click()")
            pg.wait_for_timeout(1500)
            check(not os.path.exists(plan + ".lock"),
                  "'Leave without change' hands the plan back too (NR-STO-15)")
            # ---- NR-STO-15's OTHER HALF: the wait is watched -----------------
            # "...and a session waiting to edit is offered it without having to reopen
            # the workspace". The first half - the release - is checked above. The
            # second half was missing: the thirty-second poll only ran while a session
            # HELD the claim, so a blocked one learned nothing and the person had to
            # guess and try the edit again. Somebody else's claim is written by hand
            # here because that is precisely what a second PC's instance leaves behind.
            print("\nbeing told the plan has freed, without reopening it")
            pg.evaluate("(p) => window.__pm.openPlan(p)", plan)
            pg.wait_for_timeout(1200)
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
            pathlib.Path(plan + ".lock").write_text(json.dumps(
                {"name": "A Colleague", "department": "Elsewhere",
                 "machine": "OTHER-PC", "since": stamp, "heartbeat": stamp}),
                encoding="utf-8")
            refused = pg.evaluate("() => window.__pm.takeClaimOnEdit()")
            whose = pg.evaluate("() => window.__pm.state().blockedBy")
            check(refused is False and whose == "A Colleague",
                  "a colleague's claim blocks the edit, and the window remembers whose",
                  f"blocked by {whose}")
            os.remove(plan + ".lock")
            offered = pg.evaluate("() => window.__pm.offerIfFreed()")
            banner = pg.evaluate("() => document.getElementById('banner').textContent")
            check(offered is True and "free now" in banner,
                  "AND WHEN THEY FINISH, THE WAITING SESSION IS OFFERED IT - without "
                  "reopening the workspace (NR-STO-15)", banner.strip()[:90])
            check(pg.evaluate("() => window.__pm.state().blockedBy") is None
                  and pg.evaluate("() => window.__pm.state().stale") is False,
                  "and nothing was reloaded, so the view it was reading is still there "
                  "(S-N07)")

            # The case that strands somebody longest: the holder's machine died, so no
            # release is ever coming. An expired claim is as takeable as none (Q-N16),
            # and saying nothing leaves the person waiting out the half hour and then
            # guessing.
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + ".000Z"
            pathlib.Path(plan + ".lock").write_text(json.dumps(
                {"name": "A Colleague", "department": "Elsewhere",
                 "machine": "OTHER-PC", "since": stamp, "heartbeat": stamp}),
                encoding="utf-8")
            pg.evaluate("() => window.__pm.takeClaimOnEdit()")   # blocked again
            dead = time.strftime("%Y-%m-%dT%H:%M:%S",
                                 time.gmtime(time.time() - 40 * 60)) + ".000Z"
            pathlib.Path(plan + ".lock").write_text(json.dumps(
                {"name": "A Colleague", "department": "Elsewhere",
                 "machine": "OTHER-PC", "since": dead, "heartbeat": dead}),
                encoding="utf-8")
            was = pg.evaluate("() => window.__pm.state().blockedBy")
            gone = pg.evaluate("() => window.__pm.offerIfFreed()")
            banner2 = pg.evaluate("() => document.getElementById('banner').textContent")
            check(gone is True and "gone quiet" in banner2 and was == "A Colleague",
                  "a holder whose machine died is not waited out in silence either "
                  "(NR-STO-14, Q-N16)", banner2.strip()[:90])
            took = pg.evaluate("() => window.__pm.takeClaimOnEdit()")
            held_by = json.loads(pathlib.Path(plan + ".lock").read_text(encoding="utf-8"))
            check(took is True and held_by["name"] == "Test Person"
                  and (held_by.get("displaced") or {}).get("name") == "A Colleague",
                  "and acting on that offer really does hand the plan over",
                  f"displaced {(held_by.get('displaced') or {}).get('name')}")
            pg.evaluate("() => window.__pm.releaseClaim()")

            # ---- a plan where the sharing rules cannot reach it (defect E) ----
            # The team folder was created at launch and carried a note saying what it
            # was for, and the page never mentioned either - so plans went into the
            # person's own folder, where a claim protects nothing (NR-STO-10) and
            # every sharing rule in the application is dead code. Checked from the
            # page, because a folder nobody is shown is a folder nobody uses.
            print("\na plan nobody else can open")
            w = pg.evaluate("() => window.__pm.state().where")
            check(bool(w.get("shared")) and bool(w.get("workspaces")),
                  "the page is told both places", f"{os.path.basename(w['shared'] or '')}")

            mine_ref = os.path.join(w["workspaces"], "team-copy.prap")
            pg.evaluate("""async (p) => {
                const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                await window.__pm.call('ws/saveAs', {sheets, ref: p});
                await window.__pm.openPlan(p);
            }""", mine_ref)
            pg.wait_for_timeout(1200)

            shown = pg.evaluate("() => window.__pm.checkShared("
                                "{name: 'A Colleague', department: 'Elsewhere'})")
            bar = pg.evaluate("() => { const b = document.getElementById('pm-share');"
                              "return {hidden: b.hidden, text: b.querySelector("
                              "'[data-text]').textContent}; }")
            check(shown is True and bar["hidden"] is False,
                  "A PLAN IN YOUR OWN FOLDER THAT SOMEBODY ELSE SAVED IS FLAGGED - it "
                  "can only have got there by hand (NR-STO-10)")
            check("A Colleague" in bar["text"] and "team folder" in bar["text"],
                  "and it names who, and what to do about it", bar["text"][:80])

            # The trigger is not "private" - most private plans are private on purpose
            # and a bar on every one of them would be furniture within a week.
            quiet = pg.evaluate("() => window.__pm.checkShared("
                                "{name: 'Test Person', department: 'Verification'})")
            check(quiet is False,
                  "a plan of your own that only you have saved is NOT nagged about")

            pg.evaluate("() => document.querySelector('#pm-share [data-dismiss]').click()")
            again = pg.evaluate("() => window.__pm.checkShared({name: 'A Colleague'})")
            check(again is False
                  and pg.evaluate("() => document.getElementById('pm-share').hidden"),
                  "'Not now' means not again for that plan")

            # And the move itself, which is the only thing that actually fixes it.
            other_ref = os.path.join(w["workspaces"], "team-copy-2.prap")
            pg.evaluate("""async (p) => {
                const sheets = {};
                for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
                await window.__pm.call('ws/saveAs', {sheets, ref: p});
                await window.__pm.openPlan(p);
            }""", other_ref)
            pg.wait_for_timeout(1000)
            pg.evaluate("() => window.__pm.checkShared({name: 'A Colleague'})")
            pg.evaluate("() => window.__pm.moveToShared()")
            pg.wait_for_timeout(1500)
            moved_to = os.path.join(w["shared"], "team-copy-2.prap")
            check(os.path.exists(moved_to) and not os.path.exists(other_ref),
                  "MOVING IT PUTS IT WHERE COLLEAGUES CAN OPEN IT, and does not leave "
                  "a twin behind for somebody to keep editing")
            check(pg.evaluate("() => window.__pm.state().ref") == moved_to
                  and pg.evaluate("() => document.getElementById('pm-share').hidden"),
                  "and the window follows the plan it moved")

            # The other half of the fix: the place is one click away in the browser,
            # so the right choice can be made before anything goes wrong.
            pg.evaluate("() => { window.__pm.browseFor({title: 'x'}); }")
            pg.wait_for_timeout(900)
            chips = pg.eval_on_selector_all(
                ".pm-back .pm-crumb button.place", "es => es.map(e => e.textContent)")
            check(chips == ["My plans", "Team plans"],
                  "the file browser offers both places by name", ", ".join(chips))
            pg.evaluate("() => document.querySelector('.pm-back [data-cancel]').click()")
            pg.wait_for_timeout(300)

            menu2 = pg.eval_on_selector_all(
                "#pm-title .pm-menu a[data-do]", "es => es.map(e => e.dataset.do)")
            check("moveToShared" in menu2,
                  "and the File menu offers the move to somebody who already knows "
                  "they want it")

            pg.evaluate("(p) => window.__pm.openPlan(p)", plan)
            pg.wait_for_timeout(1000)

            # ---- the journal: something to recover ---------------------------
            print("\nwhat a power cut leaves behind")
            pg.evaluate("(p) => window.__pm.openPlan(p)", plan)
            pg.wait_for_timeout(1200)
            pg.evaluate("""() => {
                S.pending.push({at: new Date(), sheet: 'Project', row: 1,
                                col: 'project_name', from: 'before', to: 'after'});
                renderDirty();
            }""")
            pg.wait_for_timeout(4000)                 # past the journal watcher
            jrn = plan + ".journal"
            check(os.path.exists(jrn),
                  "a pending edit is written to the journal, so a crash has something "
                  "to offer back (NR-STO-07)")
            if os.path.exists(jrn):
                j = json.loads(pathlib.Path(jrn).read_text(encoding="utf-8"))
                check(len(j.get("pending") or []) == 1
                      and j["pending"][0]["col"] == "project_name",
                      "and it is the edit itself, not a count",
                      f"{len(j.get('pending') or [])} row(s)")
            pg.evaluate("() => { S.pending.length = 0; renderDirty(); }")
            pg.wait_for_timeout(4000)
            check(not os.path.exists(jrn),
                  "committing or discarding clears it, so nothing stale is offered back")

            # ---- STALE: the check that prevents the lost update --------------
            # The one that actually loses work. A session that has only READ a plan
            # holds no claim, so nothing stops it saving over a colleague's newer save
            # - and the save reported success while doing it.
            print("\nwhen somebody else has saved it since you looked")
            pg.evaluate("(p) => window.__pm.openPlan(p)", plan)
            pg.wait_for_timeout(1200)
            doc_before = pathlib.Path(plan).read_text(encoding="utf-8")
            newer = json.loads(doc_before)
            newer["sheets"]["Project"] = newer["sheets"]["Project"][:1]
            # A colleague's save moves the plan's own last_saved, which is what the
            # check compares - a modification time alone can be rounded by a share.
            newer["workspace"]["last_saved"] = "2099-01-01T00:00:00.000Z"
            newer["workspace"]["last_saved_by"] = {"name": "A Colleague",
                                                   "department": "Elsewhere"}
            pathlib.Path(plan).write_text(json.dumps(newer), encoding="utf-8")
            later = time.time() + 30                  # unambiguously after we read it
            os.utime(plan, (later, later))
            colleagues = pathlib.Path(plan).read_text(encoding="utf-8")

            check(pg.evaluate("() => window.__pm.superseded()") is True,
                  "the application notices the plan moved on beneath it (NR-STO-16)")
            pg.evaluate("() => window.__pm.savePlan(false)")
            pg.wait_for_timeout(1500)
            check(pathlib.Path(plan).read_text(encoding="utf-8") == colleagues,
                  "AND THE SAVE IS REFUSED rather than replacing their work",
                  "the colleague's file is untouched")
            check(pg.evaluate("() => window.__pm.state().stale") is True,
                  "and the window says so, so nobody quotes the figures on screen")

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

            # ---- the OTHER export: the calculated figures ----------------------
            # This shell reaches it through the File menu rather than a button, so the
            # menu is what is checked - an item nobody can find is not a feature.
            menu = pg.eval_on_selector_all(
                "#pm-title .pm-menu a[data-do]", "es => es.map(e => e.dataset.do)")
            check("exportCalc" in menu and "exportCalcTo" in menu and "export" in menu,
                  "the File menu offers the calculated figures as well as the plan",
                  ", ".join(m for m in menu if m.startswith("export")))

            calc = str(home / "calculated.xlsx")
            wrote2 = pg.evaluate("""async (p) => {
                const named = Object.entries(S.f).filter(([, x]) => x.size)
                  .map(([k, x]) => k + ": " + [...x].join(", "));
                const sheets = buildResults(S.model, S.calc, {
                    months: grid(), projects: activeProjects(), people: activePeople(),
                    filters: named.join(" · "), fileName: S.fileName, stamp: "test"});
                const u = new Uint8Array(await buildXlsx(sheets).arrayBuffer());
                let s = ''; for (let i = 0; i < u.length; i += 0x8000)
                    s += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
                const r = await window.__pm.call('file/export', {bytes: btoa(s), path: p});
                return {size: r.size, detail: sheets.Detail.length - 1,
                        sheets: Object.keys(sheets)};
            }""", calc)
            check(os.path.exists(calc) and wrote2["detail"] > 0
                  and wrote2["sheets"][0] == "00_ReadMe",
                  "and it writes them, through the same builder the web shell uses",
                  f"{wrote2['size']:,} bytes, {wrote2['detail']:,} assignment-month rows, "
                  f"{len(wrote2['sheets'])} sheets")

            from openpyxl import load_workbook as _lw
            cwb = _lw(calc)
            det = list(cwb["Detail"].iter_rows(values_only=True))
            hdr = det[0]
            # Against automatic_fte rather than fte: a row whose figure was STATED
            # (REQ-CAL-18) is deliberately not the product of its terms - that is what
            # manual means - and every row carries what the assumptions alone would have
            # produced, so the multiplication is still checkable on all of them.
            # REQ-CAL-19: the project-month IS its demand, and role_share is this
            # person's slice of it. person_weight and coverage are inside the share
            # rather than multiplied after it, which is what makes the shares add to one.
            fte, dem, share = (hdr.index(c) for c in
                               ("automatic_fte", "demand_fte", "role_share"))
            # To the hundredth (REQ-CAL-20): the month's hundredths go out by largest
            # remainder, so a row takes its floor or its floor plus one and sits within a
            # full hundredth of the exact product by design.
            bad = [r for r in det[1:] if abs(r[dem] * r[share] - r[fte]) > 0.01 + 1e-9]
            check(not bad,
                  "every row of it is its demand times its share, to the hundredth",
                  f"{len(det) - 1:,} rows checked")

            check(not errors, "no script error anywhere in the run",
                  "; ".join(errors[:3]))
            browser.close()

        # ---- nothing left outside its own folder -----------------------------
        print("\nleaving the machine as it found it")
        # The two files this test asked the application to write are not strays: the
        # point of the check is that NOTHING ELSE appeared.
        asked_for = {pathlib.Path(out), pathlib.Path(calc)}
        stray = [p for p in home.rglob("*") if p.is_file()
                 and not str(p).startswith(str(app_dir))
                 and p not in asked_for]
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
