"""Drive app/PRAP.html and check that inserting and deleting rows actually works.

This exists because it once did not. The four CHILD tables - Milestones and Periods
under a project, Assignments and Weight overrides under a person - are the four that
render filtered to a selected parent, and all four failed in a way no screenshot would
show: the row was created in the data and never appeared on screen, or it was destroyed
by the next action, or a delete took two rows instead of one.

Four things are checked, each on all four tables:

  1. insert    - the new row appears on screen, not only in the data
  2. delete    - exactly one row goes, and the right one
  3. lifecycle - a new row can be filled in, saved, exported, and read back
  4. identity  - an edit stays attached to its own record when a row above it is deleted

    python tools/test_rows.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.8.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = ROOT / "output" / "test_rows_export.xlsx"

# Where each child table lives, and a valid row for it. The values are chosen to pass
# validation against the dummy data: 'After Close-out (final)' is the one clinical period
# PRJ-035 does not already have, and 'Project oversight' is a role with a factor defined
# for every period PRJ-001 runs through - otherwise V-23 would refuse the save, correctly.
TABLES = {
    "Milestone": ("Source data (project)", "#t-proj", {
        "milestone_name": "Inspection", "milestone_date": "2027-03-15"}),
    "ProjectPeriod": ("Source data (project)", "#t-proj", {
        "period_seq": "7", "period_name": "After Close-out (final)",
        "period_start": "2028-07-01", "period_end": "2028-09-30", "weight": "0.20"}),
    "Assignment": ("Source data (person)", "#t-pers", {
        "assignment_id": "ASG-950", "project_id": "PRJ-001", "role_name": "Project oversight",
        "assign_start_date": "2028-01-01", "assign_end_date": "2029-12-31",
        "person_weight": "0.20"}),
    "PersonPeriodWeight": ("Source data (person)", "#t-pers", {
        "assignment_id": "ASG-001", "period_start": "2029-06-01",
        "period_end": "2029-08-31", "weight_override": "0.25"}),
}

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def load(pg, path):
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(path))
    pg.wait_for_timeout(4500)


def fill(pg, loc, row, values):
    """Type into the new row's cells. Enter commits; Escape would revert."""
    for col, v in values.items():
        td = pg.locator(f"{loc} td[data-row='{row}'][data-col='{col}']")
        if td.count() == 0:                      # seeded parent columns are not editable
            continue
        td.first.click()
        pg.wait_for_timeout(120)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(v)
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(350)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html")
    print("insert and delete")
    load(pg, DUMMY)
    for sheet, (tab, pane, _) in TABLES.items():
        pg.click(f"text={tab}")
        pg.wait_for_timeout(800)
        loc = f"{pane} .data-t[data-sheet='{sheet}']"
        shown0 = pg.locator(f"{loc} tbody tr").count()
        model0 = pg.evaluate(f"S.model.raw['{sheet}'].length")
        pg.locator(f"{loc} button[data-ins]").first.click()
        pg.wait_for_timeout(1100)
        shown1 = pg.locator(f"{loc} tbody tr").count()
        check(shown1 == shown0 + 1, f"{sheet}: the inserted row is visible",
              f"rows on screen {shown0} -> {shown1}")
        pg.locator(f"{loc} button[data-del]").first.click()
        pg.wait_for_timeout(1100)
        shown2 = pg.locator(f"{loc} tbody tr").count()
        model2 = pg.evaluate(f"S.model.raw['{sheet}'].length")
        # one inserted then one deleted lands back on the starting count; taking two
        # rows for one click - the old defect - would land one below it
        check(shown2 == shown1 - 1 and model2 == model0,
              f"{sheet}: delete takes exactly one row",
              f"rows on screen {shown1} -> {shown2}, in the data {model0}+1 -> {model2}")
        pg.click("#discardBtn")
        pg.wait_for_timeout(1000)

    print("fill in, save, export, read back")
    load(pg, DUMMY)
    expected = {}
    for sheet, (tab, pane, values) in TABLES.items():
        pg.click(f"text={tab}")
        pg.wait_for_timeout(800)
        loc = f"{pane} .data-t[data-sheet='{sheet}']"
        expected[sheet] = pg.evaluate(f"S.model.raw['{sheet}'].length") + 1
        pg.locator(f"{loc} button[data-ins]").last.click()
        pg.wait_for_timeout(900)
        row = pg.evaluate(f"() => {{const r = S.model.raw['{sheet}'].find(x => x.__new); "
                          f"return r ? r.__row : null;}}")
        fill(pg, loc, row, values)
    pg.click("#saveBtn")
    pg.wait_for_timeout(1500)
    drafts = pg.evaluate("REQUIRED_SHEETS.reduce((n,s) => n + S.model.raw[s].filter(r => r.__new).length, 0)")
    errs = pg.evaluate("S.model.findings.filter(f => f.sev === 'error').length")
    check(drafts == 0 and errs == 0, "the four new rows save and validate",
          f"drafts left {drafts}, errors {errs}")

    TMP.parent.mkdir(exist_ok=True)
    if TMP.exists():
        TMP.unlink()
    with pg.expect_download() as dl:
        pg.click("#exportBtn")
    dl.value.save_as(str(TMP))
    pg.wait_for_timeout(400)

    load(pg, TMP)
    got = {s: pg.evaluate(f"S.model.raw['{s}'].length") for s in TABLES}
    check(got == expected, "the export carries them and re-imports cleanly",
          f"{got} vs {expected}")

    print("row identity across a delete")
    load(pg, DUMMY)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(900)
    loc = "#t-proj .data-t[data-sheet='Milestone']"
    target = pg.evaluate("""() => {
      const rs = [...document.querySelectorAll(
        "#t-proj .data-t[data-sheet='Milestone'] tbody tr")];
      const td = rs[rs.length - 1].querySelector("td[data-col='milestone_date']");
      const rec = S.model.raw.Milestone.find(x => x.__row === +td.dataset.row);
      return {row:+td.dataset.row, name:rec.milestone_name, pid:rec.project_id};
    }""")
    cell = pg.locator(f"{loc} tbody tr").last.locator("td[data-col='milestone_date']").first
    cell.click(click_count=3)
    pg.keyboard.type("2029-11-11")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    pg.locator(f"{loc} button[data-del]").first.click()      # delete a row ABOVE it
    pg.wait_for_timeout(1200)
    after = pg.evaluate(f"""() => {{
      const rec = S.model.raw.Milestone.find(x => x.__row === {target['row']});
      const td = document.querySelector(
        "#t-proj .data-t[data-sheet='Milestone'] td.edited");
      return {{name: rec && rec.milestone_name, pid: rec && rec.project_id,
               date: rec && rec.milestone_date && rec.milestone_date.toISOString().slice(0,10),
               marked: td && +td.dataset.row}};
    }}""")
    check(after["name"] == target["name"] and after["pid"] == target["pid"]
          and after["date"] == "2029-11-11" and after["marked"] == target["row"],
          "the edit stays on its own record", f"{after} vs {target}")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
