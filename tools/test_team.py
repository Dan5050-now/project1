"""A project's team, changed in one place (R-66).

Asked for from the field: while looking at the whole picture - Resource by project on
Overall, or the project's Utilisation - change who is on the project directly, rather than
person by person on Source data (person), and have the change land in the people's own
assignments when Save is pressed.

What is checked:

  * The Team control is on every project row of Resource by project and on the project's
    Utilisation panel, and opens the team of THAT project without folding the row.
  * Each member's person, role, window and weight are there to change, with each
    person's load beside their name, and the least loaded offered first.
  * SWAPPING A PERSON moves the assignment to them: their own Assignments table on
    Source data (person) lists it at once, and the one they replaced no longer does.
  * Adding and removing work the same way; an edit that would introduce an error is
    refused, inside the dialog.
  * Every change is an ordinary pending edit: Leave without change undoes it, Save keeps
    it and writes it to the change log, and an exported workbook carries it.

    python tools/test_team.py
"""

import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.15.xlsx"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_team_"))
sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                         # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


TEAM = """p => S.model.raw.Assignment.filter(a => a.project_id === p)
    .map(a => [a.assignment_id, a.person_id, a.role_name])"""
MINE = """s => [...document.querySelectorAll('#t-pers .panel[data-panel="pers-asg"] tbody tr')]
    .map(r => r.dataset.id).filter(Boolean)"""

print("R-66 — a project's team, changed in one place")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    pg = b.new_context(accept_downloads=True, viewport={"width": 1500, "height": 1000}).new_page()
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3500)
    P = '#t-overall .panel[data-panel="table-proj"]'

    print("\n1. where it opens from")
    n_rows = pg.locator(f"{P} tr.parent").count()
    n_btn = pg.locator(f"{P} tr.parent [data-team]").count()
    check(n_rows > 1 and n_btn == n_rows, "EVERY PROJECT ROW OF RESOURCE BY PROJECT HAS A TEAM BUTTON",
          f"{n_btn} of {n_rows}")
    pid = "PRJ-001"
    row = pg.locator(f'{P} tr.parent[data-k="p-{pid}"]')
    was = row.get_attribute("aria-expanded")
    row.locator("[data-team]").click()
    pg.wait_for_timeout(700)
    check(pg.evaluate("el('teamdlg') && el('teamdlg').open")
          and pid in pg.inner_text("#teamTitle")
          and pg.locator(f'{P} tr.parent[data-k="p-{pid}"]').get_attribute("aria-expanded") == was,
          "it opens that project's team, and does not fold the row", pg.inner_text("#teamTitle"))
    team = pg.evaluate(TEAM, pid)
    shown = pg.eval_on_selector_all("#teamBody tbody tr[data-row]", "es => es.length")
    check(shown == len(team) and len(team) >= 2,
          "EVERY MEMBER IS LISTED, with person, role, window and weight to change",
          f"{shown} of {len(team)}")
    opt = pg.eval_on_selector_all("#teamBody select[data-tm='person_id'] option",
                                  "es => es.slice(0, 2).map(o => o.textContent)")
    check(opt and all("avg" in o and "peak" in o for o in opt),
          "each person is offered with their load beside their name", opt[0] if opt else "")
    room = pg.eval_on_selector_all("#teamBody .tmroom [data-tmpick]", "es => es.map(e => e.dataset.tmpick)")
    avgs = pg.evaluate("""ids => { const ks = teamMonths('PRJ-001');
        return ids.map(s => teamLoad(s, ks).avg); }""", room)
    check(room and avgs == sorted(avgs) and not set(room) & {t[1] for t in team},
          "AND THE PEOPLE WITH MOST ROOM ARE SUGGESTED FIRST - none already on it",
          ", ".join(f"{s} {a:.2f}" for s, a in zip(room, avgs)))
    pg.click("#teamClose")
    pg.wait_for_timeout(300)

    pg.evaluate("p => { S.selProj = p; renderAll(); showTab('t-proj'); }", pid)
    pg.wait_for_timeout(1200)
    pg.click('#t-proj .panel[data-panel="proj-util"] [data-team]')
    pg.wait_for_timeout(700)
    check(pg.evaluate("el('teamdlg').open") and pid in pg.inner_text("#teamTitle"),
          "THE PROJECT'S UTILISATION PANEL OPENS THE SAME TEAM")

    print("\n2. swapping a person")
    aid, old, role = team[0]
    new = pg.evaluate("""([p, s]) => Object.keys(S.model.people).find(x => x !== s
        && !S.model.raw.Assignment.some(a => a.project_id === p && a.person_id === x))""", [pid, old])
    sel = pg.locator(f"#teamBody tr[data-row] select[data-tm='person_id']").first
    row_aid = pg.evaluate("() => { const r = +document.querySelector('#teamBody tr[data-row]').dataset.row;"
                          " return S.model.raw.Assignment.find(a => a.__row === r).assignment_id; }")
    old = pg.evaluate("a => S.model.raw.Assignment.find(x => x.assignment_id === a).person_id", row_aid)
    before_util = pg.evaluate("""() => { const o = {}; for (const [k, v] of S.calc.projMonth)
        if (k.startsWith('PRJ-001|')) o[k] = v; return o; }""")
    sel.select_option(new)
    pg.wait_for_timeout(1000)
    now = pg.evaluate("a => S.model.raw.Assignment.find(x => x.assignment_id === a).person_id", row_aid)
    check(now == new and pg.evaluate("S.pending.length") > 0,
          "CHOOSING ANOTHER PERSON MOVES THE ASSIGNMENT TO THEM - as a pending edit",
          f"{row_aid}: {old} -> {now}")
    check("replaced by" in pg.inner_text("#teamMsg") and "unsaved" in pg.inner_text("#teamPend"),
          "and the dialog says what happened and that it is not saved yet",
          pg.inner_text("#teamMsg")[:80])
    check(pg.evaluate("p => S.calc.cell && [...S.calc.cell.keys()].some(k => k.startsWith('PRJ-001|' + p + '|'))", new),
          "the figures move at once: the new person now carries months on the project")
    pg.click("#teamClose")
    pg.wait_for_timeout(300)
    pg.evaluate("s => { S.selPers = s; renderAll(); showTab('t-pers'); }", new)
    pg.wait_for_timeout(1200)
    check(row_aid in pg.evaluate(MINE, new),
          "THE NEW PERSON'S OWN ASSIGNMENTS TABLE ON SOURCE DATA (PERSON) LISTS IT",
          f"{new}: {pg.evaluate(MINE, new)}")
    pg.evaluate("s => { S.selPers = s; renderAll(); showTab('t-pers'); }", old)
    pg.wait_for_timeout(1200)
    check(row_aid not in pg.evaluate(MINE, old), "and the person replaced no longer does")

    print("\n3. adding, removing, and a change that is refused")
    pg.evaluate("p => openTeam(p)", pid)
    pg.wait_for_timeout(600)
    n0 = len(pg.evaluate(TEAM, pid))
    add = room[0] if room[0] != new else room[1]
    pg.select_option("#tmP", add)
    roles = pg.eval_on_selector_all("#tmR option", "es => es.map(e => e.value)")
    pg.select_option("#tmR", roles[0])
    pg.click("#teamBody [data-tmadd]")
    pg.wait_for_timeout(1000)
    team2 = pg.evaluate(TEAM, pid)
    added = [t for t in team2 if t[1] == add]
    check(len(team2) == n0 + 1 and added and added[0][0].startswith("ASG-"),
          "ADD TO TEAM CREATES THE ASSIGNMENT, numbered like the rest",
          f"{added[0][0] if added else '-'} for {add}")
    pg.click("#teamBody [data-tmadd]")                # nobody chosen now
    pg.wait_for_timeout(300)
    # A window ending before it starts is an error, and refused where it is typed.
    r0 = pg.evaluate("() => +document.querySelector('#teamBody tr[data-row]').dataset.row")
    pg.fill(f"#teamBody input[data-tm='assign_start_date'][data-row='{r0}']", "2030-01-01")
    pg.locator(f"#teamBody input[data-tm='assign_start_date'][data-row='{r0}']").dispatch_event("change")
    pg.wait_for_timeout(300)
    pg.fill(f"#teamBody input[data-tm='assign_end_date'][data-row='{r0}']", "2020-01-01")
    pg.locator(f"#teamBody input[data-tm='assign_end_date'][data-row='{r0}']").dispatch_event("change")
    pg.wait_for_timeout(800)
    msg = pg.inner_text("#teamMsg")
    end = pg.evaluate("r => { const a = S.model.raw.Assignment.find(x => x.__row === r); "
                      "return a.assign_end_date ? ymd(a.assign_end_date) : null; }", r0)
    check(msg.startswith("Not changed") and end != "2020-01-01",
          "AN EDIT THAT WOULD INTRODUCE AN ERROR IS REFUSED, and said inside the dialog", msg[:90])
    rm = pg.evaluate("a => S.model.raw.Assignment.find(x => x.assignment_id === a).__row", added[0][0])
    pg.click(f"#teamBody [data-tmdel='{rm}']")
    pg.wait_for_timeout(1000)
    check(len(pg.evaluate(TEAM, pid)) == n0 and "off the team" in pg.inner_text("#teamMsg"),
          "REMOVE TAKES SOMEBODY OFF", pg.inner_text("#teamMsg")[:70])
    held = pg.evaluate("""() => { const w = S.model.raw.PersonPeriodWeight.find(x => x.assignment_id);
        const a = w && S.model.raw.Assignment.find(x => x.assignment_id === w.assignment_id);
        return a ? [a.project_id, a.__row, a.assignment_id] : null; }""")
    if held:
        pg.evaluate("p => openTeam(p)", held[0])
        pg.wait_for_timeout(600)
        pg.click(f"#teamBody [data-tmdel='{held[1]}']")
        pg.wait_for_timeout(600)
        check("cannot be removed" in pg.inner_text("#teamMsg")
              and pg.evaluate("a => S.model.raw.Assignment.some(x => x.assignment_id === a)", held[2]),
              "one with weight windows or stated months is not deleted - and says why",
              pg.inner_text("#teamMsg")[:90])

    print("\n4. Leave without change, and Save")
    pending = pg.evaluate("S.pending.length")
    pg.click("#teamClose")
    pg.wait_for_timeout(300)
    pg.click("#discardBtn")
    pg.wait_for_timeout(1200)
    back = pg.evaluate("a => S.model.raw.Assignment.find(x => x.assignment_id === a).person_id", row_aid)
    check(pending > 0 and back == old and pg.evaluate("S.pending.length") == 0,
          "LEAVE WITHOUT CHANGE PUTS THE TEAM BACK", f"{row_aid} is {back} again")

    pg.evaluate("p => openTeam(p)", pid)
    pg.wait_for_timeout(600)
    pg.locator(f"#teamBody select[data-tm='person_id']").first.select_option(new)
    pg.wait_for_timeout(900)
    pg.click("#teamSave")
    pg.wait_for_timeout(1500)
    for sel_ in ("#cfYes", "#saveAnyway"):
        if pg.locator(sel_).count() and pg.locator(sel_).is_visible():
            pg.click(sel_)
            pg.wait_for_timeout(1200)
    audit = [a for a in pg.evaluate("S.audit") if a.get("sheet") == "Assignment" and a.get("col") == "person_id"]
    check(pg.evaluate("S.pending.length") == 0 and audit and audit[-1]["to"] == new,
          "SAVE CHANGES KEEPS IT, AND THE CHANGE LOG RECORDS WHO WAS PUT ON",
          f"{audit[-1]['from']} -> {audit[-1]['to']}" if audit else "no entry")
    with pg.expect_download() as dl:
        pg.click("#exportBtn")
        pg.click("#exportBtn2")
    out = TMP / "team.xlsx"
    dl.value.save_as(out)
    src = prap_io.read_xlsx(out)
    got = next((a["person_id"] for a in src["Assignment"] if a["assignment_id"] == row_aid), None)
    check(got == new, "AND THE EXPORTED WORKBOOK CARRIES IT", f"{row_aid}: {got}")

    check(not errors, "no script error anywhere in the run", "; ".join(errors[:3]))
    b.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
