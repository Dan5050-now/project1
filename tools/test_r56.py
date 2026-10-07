"""R-56: five things asked for from the field, each about finding your way.

  * THE FILTERS NAME PROJECTS AND PEOPLE. The Project and Person filter lists show the
    name, sorted by name, with a search box once the list is long - while the value
    behind each tick stays the identifier, which is what the filter and the export match.
  * A NEW PROJECT OR PERSON STAYS SELECTED. Adding one with + row makes it the
    selection, and it stays the selection through typing and through Save - so the
    milestones, periods and assignments entered next go to it and not to whichever row
    the + was pressed from.
  * RESOURCE BY PROJECT SAYS HOW EACH FIGURE WAS MADE: a pill per project (Auto,
    Manual, or Auto with some assignments stated) and a mark on every month that carries
    a stated figure.
  * IT CAN BE NARROWED TO ITS PROBLEMS - short, over, not staffed, stated by hand - and
    the narrowing reaches the rows only, never the alarm beside it.
  * NOT STAFFED IS COUNTED: the control in the panel head, the tile and the Standard vs
    staffed list all count the months a project needs and nobody is on.
  * Exported files are named with the date AND time, and an earlier stamp is not
    stacked on.

The Python edition's file browser - modified date, newest first - is checked in
tools/test_python_app.py, which runs that edition.

    python tools/test_r56.py
"""

import pathlib
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.11.xlsx"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_r56_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# A plan with all three kinds of problem: the fixture's stated figures put PRJ-001 and
# PRJ-007 off their standard, and taking every assignment off one project with no gap
# of its own leaves months nobody is on.
src = prap_io.read_xlsx(FIX)
gapped = {pid for (pid, _k) in prap_io.calculate(prap_io.Model(prap_io.read_xlsx(FIX)))["proj_gap"]}
GONE = next(p["project_id"] for p in src["Project"]
            if p["project_id"] not in gapped and str(p.get("status") or "") != "Completed"
            and any(a["project_id"] == p["project_id"] for a in src["Assignment"]))
src["Assignment"] = [a for a in src["Assignment"] if a["project_id"] != GONE]
keep = {a["assignment_id"] for a in src["Assignment"]}
for sh in ("PersonPeriodWeight", "MonthlyEstimate"):
    src[sh] = [r for r in src.get(sh, []) if not r.get("assignment_id") or r["assignment_id"] in keep]
PLAN = TMP / "plan.xlsx"
prap_io.write_xlsx(src, PLAN)

HEAD = '#t-overall .panel[data-panel="table-proj"]'
ROWS = f"() => [...document.querySelectorAll('{HEAD} tr.parent')].map(t => t.dataset.k.slice(2))"

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    pg.set_default_timeout(20000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(PLAN))
    pg.wait_for_timeout(3500)

    # ---- 1. filters by name -------------------------------------------------------
    print("app/PRAP.html — R-56\n\n1. the Project and Person filters list names")
    names = {p["project_id"]: p["project_name"] for p in src["Project"]}
    people = {p["person_id"]: p["person_name"] for p in src["Person"]}
    for fid, want in (("fProj", names), ("fPers", people)):
        got = pg.eval_on_selector_all(f"#{fid} label[data-find]",
                                      "es => es.map(l => [l.textContent.trim(), "
                                      "l.querySelector('input').value])")
        check(got and all(want.get(v) == t for t, v in got)
              and [t for t, _ in got] == sorted((t for t, _ in got), key=str.lower),
              f"{fid}: EVERY ENTRY IS THE NAME, sorted by name, with the identifier behind it",
              ", ".join(t for t, _ in got[:3]) + " …")
    pg.click("#fProj summary")
    pg.wait_for_timeout(300)
    pick = sorted(names.items(), key=lambda kv: kv[1].lower())[1]
    pg.fill("#fProj .msq", pick[1][:6].lower())
    pg.wait_for_timeout(200)
    shown = pg.eval_on_selector_all("#fProj label[data-find]:not([hidden])",
                                    "es => es.map(l => l.textContent.trim())")
    check(pick[1] in shown and len(shown) < len(names),
          "a long list has a search box, and it narrows the list without ticking anything",
          f"'{pick[1][:6].lower()}' -> {shown}")
    check(pg.evaluate("S.f.proj.size") == 0, "searching filters nothing")
    pg.fill("#fProj .msq", pick[0].lower())
    pg.wait_for_timeout(200)
    shown = pg.eval_on_selector_all("#fProj label[data-find]:not([hidden])",
                                    "es => es.map(l => l.textContent.trim())")
    check(shown == [pick[1]], "and it finds a project by its identifier as well", str(shown))
    pg.locator(f"#fProj input[value='{pick[0]}']").check()
    pg.wait_for_timeout(900)
    check(pg.inner_text("#fProj summary").strip() == pick[1]
          and pg.evaluate("[...S.f.proj]") == [pick[0]],
          "THE CLOSED CONTROL SAYS THE NAME, and the filter still holds the identifier",
          f"summary '{pg.inner_text('#fProj summary').strip()}', S.f.proj {pg.evaluate('[...S.f.proj]')}")
    pg.evaluate("() => { S.f.proj = new Set(); fillFilters(); renderAll(); showTab('t-overall'); }")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(600)

    # ---- 2. Resource by project ----------------------------------------------------
    print("\n2. Resource by project says how each figure was made")
    pills = pg.evaluate(f"""() => Object.fromEntries([...document.querySelectorAll(
        '{HEAD} tr.parent')].map(t => [t.dataset.k.slice(2),
        (t.querySelector('.estb') || {{}}).textContent]))""")
    truth = pg.evaluate("""() => Object.fromEntries(Object.keys(S.model.projects).map(p => [p,
        S.model.isManual('project', p) ? 'manual'
        : S.model.assignments.some(a => a.project_id === p
            && S.model.isManual('assignment', a.assignment_id)) ? 'mixed' : 'auto']))""")
    want_txt = {"manual": "Manual", "auto": "Auto"}
    bad = [p for p, k in truth.items() if p in pills and (
        pills[p] != want_txt[k] if k != "mixed" else not str(pills[p]).startswith("Auto · "))]
    check(pills and not bad and {"manual", "auto"} <= set(truth.values()),
          "EVERY PROJECT SAYS WHETHER ITS FIGURES ARE AUTOMATIC OR STATED",
          ", ".join(f"{p} {pills[p]}" for p in sorted(pills)[:4]) + (f"; wrong: {bad}" if bad else ""))
    marked = set(pg.eval_on_selector_all(f"{HEAD} td.c.man",
                                         "es => es.map(e => e.closest('tr').dataset.k.slice(2))"))
    stated = set(pg.evaluate("""() => { const G = new Set(grid()), out = new Set();
        for (const L of S.calc.lines) if ((L.manual_assignment || L.manual_project)
            && G.has(L.month) && activeProjects().includes(L.project_id)) out.add(L.project_id);
        return [...out]; }"""))
    check(stated and marked == stated,
          "and every month carrying a stated figure is marked, on exactly those projects",
          f"marked on {sorted(marked)}")

    print("\n3. it narrows to its problems, and the alarm does not move")
    before_btn = pg.inner_text(f"{HEAD} .gapbtn")
    all_rows = pg.evaluate(ROWS)
    expect = pg.evaluate("""() => { const G = grid(), man = manualMonths(), o = {};
        for (const p of activeProjects()) o[p] = [...projIssues(p, G, man)]; return o; }""")
    for value, test in (("issues", lambda s: {"short", "over", "unstaffed"} & set(s)),
                        ("short", lambda s: "short" in s), ("over", lambda s: "over" in s),
                        ("unstaffed", lambda s: "unstaffed" in s),
                        ("manual", lambda s: "manual" in s)):
        pg.select_option("#projIssue", value)
        pg.wait_for_timeout(700)
        got = pg.evaluate(ROWS)
        want = [p for p in all_rows if test(expect[p])]
        check(got == want and (value == "short" or got),
              f"Show '{value}' lists exactly the projects with it in these months",
              f"{got}")
    pg.select_option("#projIssue", "unstaffed")
    pg.wait_for_timeout(600)
    check(pg.inner_text(f"{HEAD} .gapbtn") == before_btn,
          "THE CONTROL BESIDE IT STILL COUNTS EVERYTHING — narrowing is for the rows",
          before_btn.replace("\n", " "))
    check(GONE in pg.evaluate(ROWS), f"and {GONE}, which nobody is on, is a 'not staffed' project")
    pg.select_option("#projIssue", "")
    pg.wait_for_timeout(600)
    check(pg.evaluate(ROWS) == all_rows, "All projects brings the full table back")

    print("\n4. not staffed is counted, in all three places")
    n_un = pg.evaluate("""() => { let n = 0; const want = new Set(activeProjects());
        for (const [q, u] of S.calc.projUnallocated)
          if (u > 0.004 && want.has(q.slice(0, q.lastIndexOf('|')))) n++; return n; }""")
    btn = pg.inner_text(f"{HEAD} .gapbtn")
    tile = pg.evaluate("""() => [...document.querySelectorAll('#t-overall .tile')]
        .find(t => t.textContent.includes('Off their standard')).querySelector('.ts').textContent""")
    check(n_un > 0 and f"{n_un} not staffed" in btn,
          "THE CONTROL SAYS HOW MANY MONTHS ARE NOT STAFFED", btn.replace("\n", " "))
    check(f"{n_un} not staffed" in tile, "and so does the tile", tile)
    pg.click(f"{HEAD} .gapbtn")
    pg.wait_for_timeout(800)
    pg.click('#gapsdlg [data-gapdir="unstaffed"]')
    pg.wait_for_timeout(600)
    rows = pg.eval_on_selector_all("#gapsdlg tr.gaprow", "es => es.map(e => e.className)")
    check(len(rows) == min(n_un, 40) and all("unstaffed" in c for c in rows),
          "and the list has them, under their own direction", f"{len(rows)} row(s)")
    pg.locator("#gapsdlg tr.gaprow").first.click()
    pg.wait_for_timeout(1200)
    check(pg.evaluate("S.tab") == "t-proj" and pg.evaluate("S.selProj") == GONE
          and not pg.evaluate("el('gapsdlg').open"),
          "a not-staffed month takes you to the project, where people are assigned",
          f"tab {pg.evaluate('S.tab')}, selected {pg.evaluate('S.selProj')}")

    # ---- 5. a new row stays selected ---------------------------------------------------
    print("\n5. a new project or person stays the selection")
    for tab, pane, sheet, key, sel, name_col in (
            ("Source data (project)", "#t-proj", "Project", "project_id", "selProj", "project_name"),
            ("Source data (person)", "#t-pers", "Person", "person_id", "selPers", "person_name")):
        pg.click(f"text={tab}")
        pg.wait_for_timeout(900)
        was = pg.evaluate(f"S.{sel}")
        pg.locator(f"{pane} .data-t[data-sheet='{sheet}'] button[data-ins]").first.click()
        pg.wait_for_timeout(900)
        new = pg.evaluate(f"(S.model.raw.{sheet}.find(r => r.__new) || {{}}).{key}")
        check(new and pg.evaluate(f"S.{sel}") == new,
              f"{sheet}: THE ROW JUST ADDED IS THE SELECTION", f"{was} -> {pg.evaluate(f'S.{sel}')}")
        cell = pg.locator(f"{pane} tr[data-id='{new}'] td[data-col='{name_col}']")
        cell.click()
        pg.wait_for_timeout(300)
        pg.keyboard.press("Control+A")
        pg.keyboard.type("ZZ new")
        pg.keyboard.press("Escape")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(900)
        check(pg.evaluate(f"S.{sel}") == new, f"{sheet}: and stays it while it is filled in")
        pg.click("#saveBtn")
        pg.wait_for_timeout(1500)
        check(pg.evaluate(f"S.{sel}") == new
              and pg.locator(f"{pane} tr.sel[data-id='{new}']").count() == 1,
              f"{sheet}: AND AFTER SAVE — the row is still selected, not the first in the list",
              f"selected {pg.evaluate(f'S.{sel}')}")
        if sheet == "Project":
            # The reason it matters: the next thing typed is the project's details.
            pg.locator("#t-proj .data-t[data-sheet='Milestone'] button[data-ins]").first.click()
            pg.wait_for_timeout(900)
            ms = pg.evaluate("(S.model.raw.Milestone.find(r => r.__new) || {}).project_id")
            check(ms == new, "a milestone added next belongs to the NEW project", str(ms))

    # Renaming the selected new row's identifier moves the selection with it.
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(800)
    cur = pg.evaluate("S.selProj")
    cell = pg.locator(f"#t-proj tr[data-id='{cur}'] td[data-col='project_id']")
    cell.click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("Control+A")
    pg.keyboard.type("PRJ-NEW-X")
    pg.keyboard.press("Escape")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1200)
    check(pg.evaluate("S.selProj") == "PRJ-NEW-X",
          "renaming its identifier keeps it selected under the new one",
          str(pg.evaluate("S.selProj")))

    # ---- 6. file names ------------------------------------------------------------------
    print("\n6. exported files are named with the date and time")
    got = pg.evaluate("""() => [fileStamp(new Date(2026, 9, 7, 9, 5)),
        fileBase('Plan_2026-10-04_2026-10-07.xlsx'), fileBase('Plan_CalculatedFTE_2026-10-07_0905.xlsx'),
        fileBase('My plan.prap.json'), fileBase(null, 'PRAP')]""")
    check(got == ["2026-10-07_0905", "Plan", "Plan", "My plan", "PRAP"],
          "THE STAMP CARRIES THE TIME, and an earlier stamp is taken off rather than stacked",
          str(got))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
