"""The change log: what was changed, when, by whom - and where it ends up.

  1. AN ENTRY CARRIES THE RECORD'S OWN IDENTIFIER, not its spreadsheet row number.
     `__row` is right for putting a change back and useless in a file read a month
     later, because inserting one row renumbers everything under it. PRJ-004 does not
     move.
  2. IT SURVIVES THE SAVE. S.pending is emptied at every save - that is what saving
     means - and the log is the opposite: only ever appended to, and a save is what
     WRITES it rather than what clears it.
  3. THE BROWSER ASKS WHO, ONCE. There is no account behind a local HTML file, so it
     asks at the first edit (not at load: someone who only reads a plan has nothing to
     attribute) and remembers the answer on that machine. It asks IN THE EDIT BAR - a
     modal would block the cell being typed into, and a floating card would sit on top
     of the table.
  4. THE DESKTOP APPLICATION DOES NOT ASK. It has the account name already, and it
     APPENDS to a CSV in its own audit folder at every save - one file a month, header
     written when the file is created, never rewritten.
  5. THE CSV IS ONE EXCEL WILL OPEN. A UTF-8 BOM so a Korean name is not mangled, CRLF
     line endings, doubled quotes, and a leading apostrophe on anything starting with
     = + - or @ so a note reading "=SUM(A1)" arrives as text and not as a formula.
  6. THE EXPORT CAN BE NARROWED BY DATE, and says how much it is about to hand over -
     an export that silently produces a header row and nothing else looks like an
     answer.

    python tools/test_audit.py
"""

import csv
import io
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.8.xlsx"
PKG = ROOT / "dist" / "PM_APP_py"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def edit_cell(pg, col, value, nth=0):
    pg.evaluate("""([c, v, n]) => {
        const t = [...document.querySelectorAll(
          "#t-proj td[data-sheet='Project'][data-col='" + c + "']")][n];
        t.scrollIntoView({block: 'center'});
        t.focus(); t.textContent = v;
        t.dispatchEvent(new Event('input', {bubbles: true}));
        t.blur();}""", [col, value, nth])
    pg.wait_for_timeout(600)


# ============================================================ the browser
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    ctx = browser.new_context(viewport={"width": 1500, "height": 950}, accept_downloads=True)
    pg = ctx.new_page()
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_selector("#tabs:not([hidden])", timeout=30000)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1200)

    print("1. the browser asks who, at the first edit and not before")
    check(pg.evaluate("() => el('whobox').hidden"),
          "loading a plan does not ask — there is nothing to attribute yet")
    edit_cell(pg, "project_name", "RENAMED BY TEST")
    check(not pg.evaluate("() => el('whobox').hidden"),
          "the first edit does ask, in the edit bar")
    check(pg.evaluate("""() => {
            const b = el('whobox').getBoundingClientRect();
            const t = document.querySelector("#t-proj td[data-sheet='Project']")
                        .getBoundingClientRect();
            return b.bottom <= t.top || b.top >= t.bottom
                   || b.right <= t.left || b.left >= t.right;}"""),
          "and it covers no part of the table it is asking about")
    pg.fill("#whoName", "Kim Soo-jin")
    pg.click("#whoOk")
    pg.wait_for_timeout(400)
    check(pg.evaluate("() => S.who") == "Kim Soo-jin", "and the answer is kept",
          pg.evaluate("() => S.who"))
    edit_cell(pg, "clinical_phase", "Phase 3")
    check(pg.evaluate("() => el('whobox').hidden"),
          "a second edit does not ask again")

    print("\n2. a save moves the changes into the log and empties the pending list")
    before = pg.evaluate("() => S.pending.length")
    pg.evaluate("() => saveEdits()")
    pg.wait_for_timeout(1200)
    if pg.evaluate("() => document.getElementById('confirm').open"):
        pg.click("#cfYes")
        pg.wait_for_timeout(900)
    after = pg.evaluate("() => ({pending: S.pending.length, audit: S.audit.length})")
    check(before == 2 and after["pending"] == 0 and after["audit"] == 2,
          "pending emptied, log kept",
          f"{before} pending → {after['pending']} pending, {after['audit']} logged")

    got = pg.evaluate("""() => S.audit.map(e => ({ref: e.ref, col: e.col,
        from: String(e.from), to: String(e.to), who: e.who, action: e.action,
        utc: utcStamp(e.at)}))""")
    check(all(e["ref"] == "PRJ-001" for e in got),
          "every entry names the RECORD, not the row",
          ", ".join(sorted({e["ref"] for e in got})))
    check(any(e["col"] == "project_name" and e["from"] and e["to"] == "RENAMED BY TEST"
              for e in got),
          "with the column, the previous value and the new one",
          str([e["col"] + ": " + e["from"] + " → " + e["to"] for e in got]))
    check(all(e["who"] == "Kim Soo-jin" for e in got) and
          all(len(e["utc"]) == 19 for e in got),
          "and who made it, and when in UTC", got[0]["utc"] + " UTC")

    print("\n3. what the application reported, and what was knowingly kept")
    r = pg.evaluate("""() => {
        const F = [{sev:'error',   rule:'V-19', sheet:'Project', row:7,
                    msg:'no standard for this phase'},
                   {sev:'warning', rule:'V-23', sheet:'RoleFactor', row:'',
                    msg:'role "Data Analyst, Snr" is uncosted'},
                   {sev:'fatal',   rule:'V-01', sheet:'Person', row:3,
                    msg:'a quote " and a comma, together'}];
        S.events.push(...findingEntries(F, ['V-19'], 'save', 'Kim Soo-jin'));
        return {n: S.events.length, kept: S.events.filter(e => e.kept === 'yes').length};}""")
    check(r["n"] == 3 and r["kept"] == 1,
          "findings are logged with the ones the user chose to keep marked",
          f"{r['n']} logged, {r['kept']} marked kept")

    print("\n4. the export is narrowed by date and says what it will hand over")
    pg.evaluate("() => { el('expMenu').open = true; renderAuditOffer(); }")
    pg.wait_for_timeout(250)
    full = pg.inner_text("#aCount")
    pg.fill("#aFrom", "2099-01-01")
    pg.wait_for_timeout(300)
    empty = pg.inner_text("#aCount")
    check("2 change(s)" in full and "0 change(s)" in empty
          and pg.evaluate("() => el('exportAuditBtn').disabled"),
          "the count follows the range, and an empty range cannot be exported",
          f"{full!r} → {empty!r}")
    pg.fill("#aFrom", "")
    pg.wait_for_timeout(300)

    print("\n5. a CSV that Excel opens correctly")
    with pg.expect_download() as dl:
        pg.click("#exportEventsBtn")
    path = pathlib.Path(dl.value.path())
    raw = path.read_bytes()
    text = path.read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    check(raw[:3] == b"\xef\xbb\xbf", "a UTF-8 BOM, so a non-ASCII name is not mangled")
    check(raw.count(b"\r\n") == len(rows), "CRLF line endings",
          f"{raw.count(chr(13).encode() + chr(10).encode())} of {len(rows)} lines")
    check(rows[0] == ["timestamp_utc", "who", "event", "severity", "rule", "sheet",
                      "row", "kept_by_user", "message"],
          "the header names every column asked for", str(rows[0]))
    quoted = [r for r in rows if r and 'a quote " and a comma, together' in r[-1]]
    check(len(quoted) == 1,
          "a message containing a quote AND a comma survives the round trip",
          quoted[0][-1] if quoted else "not found")

    inj = pg.evaluate("""() => csvField('=SUM(A1)') + '|' + csvField('+1') """
                      """+ '|' + csvField('-2') + '|' + csvField('@x')""")
    check(all(p.startswith("'") for p in inj.split("|")),
          "a value beginning = + - or @ is escaped, so Excel reads it as text", inj)

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

# ============================================================ the desktop shell
print("\n6. the desktop application: no question asked, and a file on disk")
if not PKG.exists():
    check(False, "dist/PM_APP_py is built", "run tools/build_python_app.py first")
else:
    home = pathlib.Path(tempfile.mkdtemp(prefix="pm-audit-"))
    app = home / "PM_APP"
    shutil.copytree(PKG, app, ignore=shutil.ignore_patterns("data"))
    proc = subprocess.Popen([sys.executable, str(app / "PM_APP.py"), "--no-browser"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            env={**os.environ, "DISPLAY": ""})
    url = key = None
    deadline = time.time() + 30
    while time.time() < deadline:
        line = proc.stdout.readline()
        if not line:
            break
        if "http://127.0.0.1" in line and "?k=" in line:
            url, key = line.strip().split("/?k=")[0], line.strip().split("/?k=")[1]
            break
    try:
        if not url:
            check(False, "the desktop application starts")
        else:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(executable_path=CHROME)
                pg = browser.new_page(viewport={"width": 1500, "height": 950})
                pg.set_default_timeout(20000)
                pg.on("dialog", lambda d: d.accept())
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(f"{url}/?k={key}")
                pg.wait_for_timeout(1400)
                if pg.locator("[data-name]").count():
                    pg.fill("[data-name]", "Kim Soo-jin")
                    pg.click("[data-ok]")
                    pg.wait_for_timeout(600)
                check(pg.evaluate("() => S.who") and pg.evaluate(
                          "() => el('whobox').hidden"),
                      "it knows who without asking — the browser's control never appears",
                      pg.evaluate("() => S.who"))
                pg.evaluate("""async (p) => {
                    const r = await window.__pm.call('file/openSource', {path: p});
                    await window.__pm.adoptBytes(r.name,
                      Uint8Array.from(atob(r.bytes), c => c.charCodeAt(0)));}""", str(DUMMY))
                pg.wait_for_timeout(2500)
                pg.click('nav [data-tab="t-proj"]')
                pg.wait_for_timeout(1200)
                for n, v in ((0, "ARCHIVED BY TEST"), (1, "SECOND EDIT")):
                    edit_cell(pg, "project_name", v, n)
                    pg.evaluate("() => saveEdits()")
                    pg.wait_for_timeout(1800)
                written = pg.evaluate("() => ({log: S.audit.length, done: S.archived})")
                check(written["log"] == 2 and written["done"] == 2,
                      "both saves reached the archive", str(written))
                browser.close()

            files = sorted(home.rglob("audit/*.csv"))
            check(len(files) == 1 and "changes" in files[0].name,
                  "one file, named for the month, in an audit folder",
                  files[0].name if files else "none written")
            if files:
                body = files[0].read_text(encoding="utf-8-sig").strip().splitlines()
                check(files[0].read_bytes()[:3] == b"\xef\xbb\xbf", "with a BOM")
                check(len(body) == 3 and body[0].startswith("timestamp_utc"),
                      "a header written ONCE, and one line per change APPENDED under it",
                      f"{len(body) - 1} entries under 1 header")
                check(sum(1 for ln in body if ln.startswith("timestamp_utc")) == 1,
                      "the second save appended rather than rewriting the file")
                check(all("Kim Soo-jin" in ln for ln in body[1:])
                      and "PRJ-001" in body[1] and "PRJ-002" in body[2],
                      "each line names who, and which record", body[1][:88])
    finally:
        proc.kill()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
