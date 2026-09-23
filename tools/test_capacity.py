"""capacity_fte is how much of ONE PERSON there is: 0.00 to 1.00, and no further (V-35).

Reported from the field. It is the one figure on the Person sheet that has a hard
ceiling, and it did not have one: 1.5 went in, was believed, and showed up beside
everybody else's 1.00 as though it meant something.

WHY THIS ONE REFUSES WHEN ALMOST NOTHING ELSE DOES. Every other figure in this
application is a judgement somebody is entitled to make - a period weight, a role
factor, a stated month - and the rules about those REPORT rather than refuse, because
which of two deliberate numbers is wrong is not the application's business. A capacity
of 1.5 is not a judgement. There is no such thing as one and a half of a person; the
number is in the wrong unit, and the usual cause is hours typed into an FTE column.
Refusing it at the cell is the only moment at which the person who knows what they
meant is still there to be asked.

  1. THE RANGE IS 0.00 TO 1.00 INCLUSIVE. 1.00 is full-time. 0.50 is half a week. 0.00
     is somebody on the books who is not available at all, which is a true thing to say
     about a person on leave, so it is allowed.
  2. OUTSIDE IT IS REFUSED AT THE CELL, in both directions, with a message that says
     what the unit is and names the likely cause.
  3. A FILE THAT ALREADY BREAKS IT STILL OPENS. The save and edit checks compare the
     count of blocking findings before and after, so a rule broken by an incoming
     workbook is reported without locking anybody out of their own plan.
  4. THE OTHER TWO ENGINES AGREE. prap_io and verify_source_workbook raise the same
     rule at the same severity - the four-implementation rule applies to what the
     application REFUSES exactly as it applies to what it calculates.
  5. EXCEL REFUSES IT TOO. The template carries a decimal range on the column, so the
     figure is stopped where people actually type it.
  6. V-22 IS NOT DOUBLED UP. An out-of-range capacity raises V-35 and nothing else -
     reporting that 1.50 is also not below the under-allocation floor would be true and
     useless.

    python tools/test_capacity.py
"""

import pathlib
import sys
import tempfile

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TEMPLATE = ROOT / "templates" / "PRAP_SourceData_Template_v1.17.xlsx"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.11.xlsx"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_cap_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402
import verify_source_workbook as VSW                                 # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + str(detail) if detail else ''}")
    if not ok:
        fails.append(label)


def book_with(cap, name="bad.xlsx"):
    """The delivered fixture with one person's capacity set to `cap`."""
    S = prap_io.read_xlsx(DUMMY)
    S["Person"][0]["capacity_fte"] = cap
    out = TMP / name
    prap_io.write_xlsx(S, out)
    return out


def type_into(pg, col, value, nth=0):
    return pg.evaluate("""([c, v, n]) => {
        const t = [...document.querySelectorAll(
          "#t-pers td[data-sheet='Person'][data-col='" + c + "']")][n];
        if (!t) return "no cell";
        t.scrollIntoView({block: "center"});
        t.dataset.orig = t.textContent;
        t.focus(); t.textContent = v;
        t.dispatchEvent(new Event("input", {bubbles: true}));
        t.blur();
        return "typed";}""", [col, value, nth])


# ============================================================ the browser
with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    ctx = browser.new_context(viewport={"width": 1500, "height": 950})
    pg = ctx.new_page()
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_selector("#tabs:not([hidden])", timeout=30000)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(1500)

    print("1. a delivered plan raises nothing")
    check(pg.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-35').length")
          == 0,
          "no V-35 on the fixture — every capacity in it is already between 0 and 1")

    print("\n2. what the cell accepts, and what it refuses")
    # Reset to a value NONE of the cases below is, so an accepted edit is a real change
    # rather than a no-op the test would read as a refusal. The fixture's own 1.00 is
    # one of the cases, which is exactly the trap.
    start = 0.8
    for value, want in (("1.5", False), ("40", False), ("-0.2", False), ("1.01", False),
                        ("1", True), ("1.0", True), ("0.5", True), ("0", True)):
        pg.evaluate("(v) => { S.model.raw.Person[0].capacity_fte = v; rebuild(true); "
                    "renderKeepingTab(); }", start)
        pg.wait_for_timeout(350)
        pg.evaluate("() => { el('banner').textContent = ''; }")
        type_into(pg, "capacity_fte", value)
        pg.wait_for_timeout(500)
        got = pg.evaluate("() => S.model.raw.Person[0].capacity_fte")
        took = got != start
        banner = pg.evaluate("() => el('banner').textContent || ''")
        if want:
            check(took and abs(float(got) - float(value)) < 1e-9,
                  f"{value:>5} is accepted", f"stored {got!r}")
        else:
            check(not took and "Edit rejected" in banner,
                  f"{value:>5} is refused at the cell, and the value is unchanged",
                  banner.split(".")[0][:66])
    pg.evaluate("(v) => { S.model.raw.Person[0].capacity_fte = v; rebuild(true); "
                "renderKeepingTab(); }", start)
    pg.wait_for_timeout(400)

    print("\n3. the message says what the unit is, and guesses the cause")
    pg.evaluate("() => { el('banner').textContent = ''; }")
    type_into(pg, "capacity_fte", "160")
    pg.wait_for_timeout(500)
    msg = pg.evaluate("() => el('banner').textContent || ''")
    check("how much of ONE PERSON there is" in msg,
          "it names the unit rather than only the bound")
    check("hours typed into an FTE column" in msg,
          "and names the usual cause: hours in an FTE column",
          "160 hours" in msg and "1.00 FTE" in msg)
    check("two assignments" in msg or "TWO ASSIGNMENTS" in msg,
          "and says what to do instead for somebody doing the work of two people")

    print("\n4. a file that ALREADY breaks it still opens")
    legacy = book_with(1.5, "legacy.xlsx")
    pg2 = ctx.new_page()
    pg2.set_default_timeout(25000)
    e2 = []
    pg2.on("pageerror", lambda e: e2.append(str(e)))
    pg2.goto(APP)
    pg2.set_input_files("#picker", str(legacy))
    pg2.wait_for_selector("#tabs:not([hidden])", timeout=30000)
    pg2.wait_for_timeout(1500)
    check(pg2.evaluate("() => Object.keys(S.model.people).length") == 10,
          "it opens, with every person in it — a rule broken by an incoming workbook "
          "reports, it does not lock somebody out of their own plan")
    got = pg2.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-35')"
                       ".map(f => f.sev)")
    check(got == ["error"], "and V-35 is raised against it, as an error", str(got))
    check(pg2.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-22'"
                       " && f.msg.indexOf('PSN-001') === 0).length") == 0,
          "V-22 is NOT also raised on that row — 1.50 being above the floor as well is "
          "true and useless")
    pg2.click("text=Source data (person)")
    pg2.wait_for_timeout(1200)
    n0 = pg2.evaluate("() => S.pending.length")
    type_into(pg2, "department", "Data Management X", 1)
    pg2.wait_for_timeout(600)
    check(pg2.evaluate("() => S.pending.length") == n0 + 1,
          "and an UNRELATED edit is still allowed — the check compares the count of "
          "blocking findings before and after, not whether any exist")

    check(not errors and not e2, "no uncaught errors in the page",
          "; ".join((errors + e2)[:2]))
    browser.close()

# ============================================================ the other engines
print("\n5. the other two engines raise the same rule at the same severity")
for cap in (1.5, -0.2):
    b = book_with(cap, f"eng{cap}.xlsx")
    M = prap_io.Model(prap_io.read_xlsx(b))
    prap_io.calculate(M)
    io_hits = [f for f in M.findings if f["rule"] == "V-35"]
    check(len(io_hits) == 1 and io_hits[0]["sev"] == "error",
          f"prap_io raises V-35 as an error for {cap}",
          io_hits[0]["msg"][:60] if io_hits else "nothing")

b = book_with(1.5, "vsw.xlsx")
import contextlib                                                    # noqa: E402
import io as _io                                                     # noqa: E402
buf = _io.StringIO()
with contextlib.redirect_stdout(buf):
    try:
        VSW.main(str(b))
    except SystemExit:
        pass
out = buf.getvalue()
check("V-35" in out, "verify_source_workbook reports V-35 too",
      next((ln.strip() for ln in out.splitlines() if "V-35" in ln), "")[:74])

# ============================================================ the workbook itself
print("\n6. Excel refuses it where people actually type it")
ws = load_workbook(TEMPLATE)["Person"]
dvs = [d for d in ws.data_validations.dataValidation if d.type == "decimal"]
check(len(dvs) == 1, "the template carries one decimal range on the Person sheet",
      f"{len(dvs)} found")
if dvs:
    d = dvs[0]
    check(d.operator == "between" and float(d.formula1) == 0.0 and float(d.formula2) == 1.0,
          "between 0.0 and 1.0", f"{d.formula1}..{d.formula2}")
    check("E" in str(d.sqref), "on the capacity_fte column", str(d.sqref))
    check(bool(d.errorTitle) and bool(d.error),
          "with a message of its own, not Excel's generic one", d.errorTitle)

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
