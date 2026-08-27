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

Then two more on the Assignments table specifically:

  5. auto key  - + row allocates the next free assignment_id, and two inserts differ
  6. proxy     - typing a project NAME sets project_id; a name that matches nothing is
                 refused; editing the identifier still drives the name the other way

And one on Weight overrides:

  7. re-point  - changing assignment_id on an override row moves THAT ROW ONLY. It is a
                 foreign key, and cascading it would drag the sibling windows of the
                 assignment being moved away from. A second window on one assignment is
                 the normal case; only an overlapping one is refused.

    python tools/test_rows.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.13.xlsx"
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


def rows_on_screen(pg, loc):
    """Real rows only. An empty table draws one placeholder row inviting you to add one,
    and counting that as data makes 0 -> 1 look like no change."""
    return pg.locator(f"{loc} tbody tr td[data-col]").evaluate_all(
        "es => new Set(es.map(e => e.dataset.row)).size")


def select_assignment_with_overrides(pg):
    """Weight overrides hangs off the ASSIGNMENT selected above it, so put the assignment
    that actually carries windows on screen before probing that table."""
    aid = pg.evaluate("""() => {
      const mine = new Set(S.model.raw.Assignment
        .filter(a => a.person_id === S.selPers).map(a => a.assignment_id));
      const w = S.model.raw.PersonPeriodWeight.find(x => mine.has(x.assignment_id));
      return w ? w.assignment_id : null;
    }""")
    if aid:
        pg.locator(f"#t-pers .data-t[data-sheet='Assignment'] tbody tr[data-id='{aid}'] "
                   "td[data-col='role_name']").first.click()
        pg.wait_for_timeout(700)
    return aid


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
    prompts = []                       # confirm() dialogs the app raises
    pg.on("dialog", lambda d: (prompts.append(d.message), d.accept()))

    print("app/PRAP.html")
    print("insert and delete")
    load(pg, DUMMY)
    for sheet, (tab, pane, _) in TABLES.items():
        pg.click(f"text={tab}")
        pg.wait_for_timeout(800)
        loc = f"{pane} .data-t[data-sheet='{sheet}']"
        if sheet == "PersonPeriodWeight":
            select_assignment_with_overrides(pg)
        shown0 = rows_on_screen(pg, loc)
        model0 = pg.evaluate(f"S.model.raw['{sheet}'].length")
        pg.locator(f"{loc} button[data-ins]").first.click()
        pg.wait_for_timeout(1100)
        shown1 = rows_on_screen(pg, loc)
        check(shown1 == shown0 + 1, f"{sheet}: the inserted row is visible",
              f"rows on screen {shown0} -> {shown1}")
        pg.locator(f"{loc} button[data-del]").first.click()
        pg.wait_for_timeout(1100)
        shown2 = rows_on_screen(pg, loc)
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
        # Overrides hang off the SELECTED assignment, so point the selection at the one
        # this row is going to name. Without that, typing its assignment_id re-points the
        # row to an assignment that is not on screen and it leaves the panel mid-fill -
        # correct behaviour (that is what the re-pointing section below proves), but it
        # meant the rest of the row was never typed. The previous build then promoted a
        # window with no dates and no weight in it; isSkeleton now declines to, which is
        # what surfaced this.
        if sheet == "PersonPeriodWeight":
            want = values["assignment_id"]
            pg.locator(f"{pane} .data-t[data-sheet='Assignment'] tbody tr[data-id='{want}'] "
                       "td[data-col='role_name']").first.click()
            pg.wait_for_timeout(700)
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

    print("Assignments: the key is allocated, the project is named")
    load(pg, DUMMY)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    loc = "#t-pers .data-t[data-sheet='Assignment']"
    before = set(pg.evaluate("S.model.raw.Assignment.map(r => r.assignment_id).filter(Boolean)"))
    pg.locator(f"{loc} button[data-ins]").last.click()
    pg.wait_for_timeout(1000)
    first = pg.evaluate("() => {const r = S.model.raw.Assignment.find(x => x.__new); "
                        "return r ? {row: r.__row, id: r.assignment_id} : {};}")
    pg.locator(f"{loc} button[data-ins]").last.click()
    pg.wait_for_timeout(1000)
    ids = pg.evaluate("S.model.raw.Assignment.filter(r => r.__new).map(r => r.assignment_id)")
    check(first.get("id") and first["id"] not in before and len(set(ids)) == len(ids) == 2,
          "+ row allocates a free assignment_id", f"allocated {ids}")

    def type_into(row, col, text):
        td = pg.locator(f"{loc} td[data-row='{row}'][data-col='{col}']")
        td.first.click()
        pg.wait_for_timeout(150)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(text)
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(600)

    row = first["row"]
    want = pg.evaluate("() => {const p = Object.values(S.model.projects)"
                       ".find(p => p.project_type !== 'Others');"
                       " return [p.project_name, p.project_id];}")
    type_into(row, "project_name", want[0])
    got = pg.evaluate(f"""() => {{const r = S.model.raw.Assignment.find(x => x.__row === {row});
        const td = document.querySelector(
          "{loc} td[data-row='{row}'][data-col='project_id']");
        return {{pid: r.project_id, stored: r.project_name, shown: td && td.textContent}};}}""")
    check(got["pid"] == want[1] and got["shown"] == want[1] and got["stored"] in (None, ""),
          "typing a project name sets project_id and stores no copy of the name",
          f"{want[0]!r} -> {got}")

    type_into(row, "project_name", "No Such Project At All")
    kept = pg.evaluate(f"S.model.raw.Assignment.find(x => x.__row === {row}).project_id")
    check(kept == want[1] and "No project is called" in pg.inner_text("#banner"),
          "a name matching no project is refused and the identifier kept",
          pg.inner_text("#banner")[:90].replace(chr(10), " "))

    other = pg.evaluate("() => {const p = Object.values(S.model.projects)"
                        ".filter(p => p.project_type !== 'Others')[1];"
                        " return [p.project_id, p.project_name];}")
    type_into(row, "project_id", other[0])
    shown = pg.locator(f"{loc} td[data-row='{row}'][data-col='project_name']").first.inner_text()
    check(shown == other[1], "editing the identifier drives the name the other way",
          f"{other[0]} -> {shown!r}")

    print("Weight overrides: re-pointing a row moves that row only")
    load(pg, DUMMY)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    ploc = "#t-pers .data-t[data-sheet='PersonPeriodWeight']"
    select_assignment_with_overrides(pg)
    prompts.clear()
    start = pg.evaluate("S.model.raw.PersonPeriodWeight.map(r => [r.__row, r.assignment_id])")
    # the first row's assignment, and a DIFFERENT one that already has a window
    src = start[0][1]
    dst = next((a for _, a in start if a != src), None)
    check(dst is not None, "the fixture has two assignments carrying overrides", str(start))
    sibs_before = sum(1 for _, a in start if a == src)
    td = pg.locator(f"{ploc} td[data-row='{start[0][0]}'][data-col='assignment_id']")
    td.first.click()
    pg.wait_for_timeout(150)
    pg.keyboard.press("Control+A")
    pg.keyboard.type(dst)
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    after = pg.evaluate("S.model.raw.PersonPeriodWeight.map(r => [r.__row, r.assignment_id])")
    left = sum(1 for _, a in after if a == src)
    check(left == sibs_before - 1 and not prompts,
          "re-pointing an override row leaves its former siblings alone",
          f"{src}: {sibs_before} -> {left} rows, {len(prompts)} prompt(s); {after}")
    # and the move states what the row has joined, rather than warning about it
    note = pg.inner_text("#banner")
    check(dst in note and "several windows" in note,
          "moving a row onto an assignment that already has windows explains itself",
          note[:110].replace(chr(10), " "))

    # and a genuinely overlapping second window is still refused
    load(pg, DUMMY)
    pg.click("text=Source data (person)")
    pg.wait_for_timeout(900)
    select_assignment_with_overrides(pg)
    pg.locator(f"{ploc} button[data-ins]").last.click()
    pg.wait_for_timeout(900)
    nrow = pg.evaluate("() => S.model.raw.PersonPeriodWeight.find(x => x.__new).__row")
    # the window to collide with must be one of THIS assignment's, since that is what the
    # table now shows and what the new row was seeded with
    host = pg.evaluate("() => {const r = S.model.raw.PersonPeriodWeight"
                       ".find(x => !x.__new && x.assignment_id === S.selAsg);"
                       " return [r.assignment_id, r.period_start.toISOString().slice(0,10),"
                       " r.period_end.toISOString().slice(0,10)];}")

    def ptype(col, text):
        c = pg.locator(f"{ploc} td[data-row='{nrow}'][data-col='{col}']")
        c.first.click()
        pg.wait_for_timeout(140)
        pg.keyboard.press("Control+A")
        pg.keyboard.type(text)
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(550)

    ptype("period_start", host[1])          # exactly on top of the existing window
    ptype("period_end", host[2])
    ptype("weight_override", "0.40")
    pg.click("#saveBtn")
    pg.wait_for_timeout(1400)
    check("Save refused" in pg.inner_text("#banner"),
          "an overlapping window is still refused at Save",
          pg.inner_text("#banner")[:110].replace(chr(10), " "))

    print("every scroll region is bounded on both axes")
    for tab in ("Overall", "Source data (project)", "Source data (person)",
                "General assumptions"):
        pg.click(f"text={tab}")
        pg.wait_for_timeout(900)
        bad = pg.evaluate("""() => [...document.querySelectorAll('.scrollx')]
            .filter(e => e.offsetParent !== null)
            .map(e => {const c = getComputedStyle(e);
                       return {cls: e.className, x: c.overflowX, y: c.overflowY,
                               mh: c.maxHeight};})
            .filter(r => !['auto','scroll'].includes(r.x)
                      || !['auto','scroll'].includes(r.y) || r.mh === 'none')""")
        check(not bad, f"{tab}: both axes scroll in every panel",
              "" if not bad else str(bad[:2]))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
