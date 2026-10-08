"""What a project NEEDS against what it is BEING GIVEN (V-34, REQ-DSH-15).

Reported from the field as "a project's FTE differs from the sum of its people's". It
cannot: projMonth is built FROM the lines, so it IS that sum by construction, and the
results export rests on that (REQ-OUT-06). Section 1 below checks it anyway, in every
state the fixture can reach, because it is the premise everything else stands on.

The pair that DOES come apart is demand against applied. An automatic month has them
equal - shareOut hands out exactly the demand's hundredths and the shares add to one
(REQ-CAL-19). A figure stated by hand, at either level, replaces the standard rather than
adjusting it, and the application then simply drew a different project: a study needing
10.00 and staffed at 5.00 looked exactly like a study that only ever needed 5.00.

  1. THE MONTH IS ALWAYS ITS PEOPLE'S SUM. Automatic, project-manual, assignment-manual.
  2. AN AUTOMATIC PLAN HAS NO GAP AT ALL, so the rule cannot cry wolf on a file nobody
     has edited - which is what would make everyone learn to ignore it.
  3. BOTH DIRECTIONS, COUNTED APART AND NEVER NETTED. Five short in September and five
     over in October is not a plan in balance, and one signed figure would say it was.
  4. IT REPORTS AND NEVER REFUSES. A warning, so refuses() is false and Save is not
     gated: departing from the standard is the point of a manual figure.
  5. THE FIGURE IS MARKED WHERE IT IS DRAWN - in the table and on the chart - so a
     shortfall does not depend on somebody hovering or opening a panel.
  6. THE TILE COUNTS WHAT THE PANEL LISTS, from one function, so the two cannot disagree.
  7. THE DIALOG CARRIES THE FIGURES THAT CAUSED IT, EDITABLE, and they are ordinary
     contenteditable cells over MonthlyEstimate - so the one editing path validates,
     logs and undoes them. Changing one there closes the gap and redraws the dialog.

THE FIXTURE RUNS FROM THIS MONTH, not from a date written into the file. Section 6 reads
the marks DRAWN in Resource by project, and the table only draws the months in the
horizon - which defaults to twenty-four months starting with the current one. With the
three months hard-coded as 2026-09 to 2026-11, the first of them fell off the left edge of
that horizon the moment the calendar passed it, and the check looking for three marks found
the two that were still on screen. Every other check in this file kept passing, because
they read projGap and gapRows, which know nothing about the horizon. A fixture dated in the
past is a test that expires.

    python tools/test_gap.py
"""

import pathlib
import sys
import tempfile
from datetime import date, timedelta

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_gap_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []
BASE = prap_io.read_xlsx(ROOT / "templates" / "PRAP_SourceData_Template_v1.19.xlsx")

# The project runs for the three months beginning with THIS one, so it is inside the
# default horizon whenever this is run - see the note in the docstring above.
TODAY = date.today()
M0 = TODAY.year * 12 + TODAY.month - 1          # the application's month key for "now"
SEP, OCT = M0, M0 + 1                           # the short month, then the over one


def first(n):
    """The first day of the month n months after the start."""
    m = M0 + n
    return date(m // 12, m % 12 + 1, 1)


def last(n):
    """The last day of that month."""
    nxt = first(n + 1)
    return date(nxt.year, nxt.month, 1) - timedelta(days=1)


def mkey(n):
    """How MonthlyEstimate writes it: YYYY-MM."""
    d = first(n)
    return f"{d.year}-{d.month:02d}"


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def fixture():
    """Two projects, each needing 10.00 a month through Start-up, two people apiece."""
    S = {k: (list(v) if isinstance(v, list) else v) for k, v in BASE.items()}
    S["Project"] = [{"project_id": pid, "project_name": nm, "project_type": "NewDrug CT",
                     "clinical_phase": "Phase 3", "work_scope_type": "fully in-housed",
                     "project_category": "Onc", "start_date": first(0),
                     "end_date": last(2), "status": "Active", "__row": 2 + i}
                    for i, (pid, nm) in enumerate([("PRJ-A", "Alpha"), ("PRJ-B", "Bravo")])]
    S["Milestone"] = []
    S["ProjectPeriod"] = [{"project_id": pid, "period_name": "Start-up", "period_seq": 1,
                           "period_start": first(0), "period_end": last(2),
                           "weight": 1.0, "__row": 2 + i}
                          for i, pid in enumerate(["PRJ-A", "PRJ-B"])]
    S["PeriodFTEStandard"] = [{"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
                               "work_scope_type": None, "period_name": "Start-up",
                               "standard_fte": 10.0, "__row": 2}]
    S["RoleFactor"] = [{"project_type": "NewDrug CT", "clinical_phase": "Phase 3",
                        "work_scope_type": None, "period_name": "Start-up",
                        "role_name": rn, "role_factor": rf, "absorbed_by": None,
                        "__row": 2 + i}
                       for i, (rn, rf) in enumerate([("Lead data manager", 0.6),
                                                     ("Data Analyst", 0.4)])]
    S["Person"] = [{"person_id": f"PSN-00{i}", "person_name": nm, "capacity_fte": 1.0,
                    "department": "Data Management", "__row": 1 + i}
                   for i, nm in enumerate(["Kim Soo-jin", "Park Ji-ho",
                                           "Lee Eun-bi", "Choi Min-seok"], start=1)]
    S["Assignment"] = [
        {"assignment_id": "ASG-001", "person_id": "PSN-001", "project_id": "PRJ-A",
         "role_name": "Lead data manager", "person_weight": 1.0, "__row": 2},
        {"assignment_id": "ASG-002", "person_id": "PSN-002", "project_id": "PRJ-A",
         "role_name": "Data Analyst", "person_weight": 1.0, "__row": 3},
        {"assignment_id": "ASG-003", "person_id": "PSN-003", "project_id": "PRJ-B",
         "role_name": "Lead data manager", "person_weight": 1.0, "__row": 4},
        {"assignment_id": "ASG-004", "person_id": "PSN-004", "project_id": "PRJ-B",
         "role_name": "Data Analyst", "person_weight": 1.0, "__row": 5}]
    S["PersonPeriodWeight"] = []
    S["MonthlyEstimate"] = []
    out = TMP / "gap.xlsx"
    prap_io.write_xlsx(S, out)
    return out


BOOK = fixture()

SUMS = """() => {
    const bad = [];
    for (const [qk, v] of S.calc.projMonth){
      const i = qk.lastIndexOf('|');
      const pid = qk.slice(0, i), k = +qk.slice(i + 1);
      let s = 0;
      for (const L of S.calc.lines) if (L.project_id === pid && L.month === k) s += L.fte;
      if (Math.abs(s - v) > 1e-9) bad.push([qk, v, s]);
    }
    return bad;}"""

GAPS = """() => [...S.calc.projGap].map(([k, g]) =>
    [k, g.demand, g.applied, +g.gap.toFixed(2), g.dir])"""


def set_fte(pg, scope, ref, month, v):
    pg.evaluate("""([sc, ref, mm, v]) => {
        const r = S.model.raw.MonthlyEstimate.find(
          x => x.scope === sc && x.ref_id === ref && String(x.month) === mm);
        r.fte = v; rebuild(true); renderKeepingTab();}""", [scope, ref, month, v])
    pg.wait_for_timeout(900)


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_context(viewport={"width": 1560, "height": 1000}).new_page()
    pg.set_default_timeout(30000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.set_input_files("#picker", str(BOOK))
    pg.wait_for_selector("#tabs:not([hidden])", timeout=40000)
    pg.wait_for_timeout(1500)

    # Said out loud, because section 6 depends on it and depended on it silently before:
    # the marks it looks for are only drawn for months the table draws.
    span = pg.evaluate("() => [S.from, S.to]")
    check(span[0] <= SEP and span[1] >= SEP + 2,
          "all three of the fixture's months are inside the default horizon — the table "
          "only draws what is in it, so a month outside it has no mark to find",
          f"horizon {span[0]}..{span[1]}, fixture {SEP}..{SEP + 2}")

    print("1. an automatic plan is exactly its standard, and reports nothing")
    check(pg.evaluate(SUMS) == [],
          "every project-month equals the sum of its own people — the pair that CANNOT "
          "differ, because the month is built from them")
    check(pg.evaluate("() => S.calc.projGap.size") == 0,
          "and no month is off its standard: the shares add to one by construction "
          "(REQ-CAL-19), so an untouched file raises nothing")
    check(pg.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-34').length") == 0,
          "so V-34 cannot cry wolf on a plan nobody has edited — which is what teaches "
          "people to ignore a rule")

    print("\n2. a manual PROJECT below its standard: short, and said so")
    pg.click('nav [data-tab="t-proj"]')
    pg.wait_for_timeout(900)
    pg.evaluate("() => { S.selProj = 'PRJ-A'; renderKeepingTab(); }")
    pg.wait_for_timeout(700)
    pg.evaluate("() => switchEstimation('project', 'PRJ-A')")
    pg.wait_for_timeout(300)
    pg.click("#estYes")
    pg.wait_for_timeout(1200)
    set_fte(pg, "project", "PRJ-A", mkey(0), 5.00)
    g = dict((r[0], r) for r in pg.evaluate(GAPS))
    check(g.get("PRJ-A|" + str(SEP)) == ["PRJ-A|" + str(SEP), 10, 5, -5.0, "short"],
          "needs 10.00, given 5.00, short by 5.00", str(g.get("PRJ-A|" + str(SEP))))
    check(pg.evaluate(SUMS) == [],
          "and the month is STILL exactly its people's sum — they were scaled to the "
          "stated figure, which is what REQ-CAL-18 does")

    print("\n3. both directions, counted apart and never netted")
    set_fte(pg, "project", "PRJ-A", mkey(1), 15.00)
    rows = pg.evaluate("() => gapRows(activeProjects()).map(r => [r.pid, r.k, r.dir, "
                       "+r.gap.toFixed(2)])")
    short = [r for r in rows if r[2] == "short"]
    over = [r for r in rows if r[2] == "over"]
    check(len(short) == 1 and len(over) == 1,
          "five short in September and five over in October is TWO findings",
          f"{len(short)} short, {len(over)} over")
    check(abs(sum(r[3] for r in rows)) < 1e-9,
          "even though they sum to zero — which is exactly why a net figure is never "
          "shown: it would report this plan as in balance",
          f"net {sum(r[3] for r in rows):.2f}")
    panel = pg.evaluate("() => gapList(activeProjects())")
    check(panel.count("month(s) short of the standard") == 1
          and panel.count("month(s) over it") == 1,
          "and the list says each direction in its own words, side by side")

    # ---- R-52: the list moved into a dialog, so the CONTROL has to carry the alarm ----
    # The list used to be a panel under the tiles, on the ground that something whose
    # danger is being silent must not sit behind a click. It now opens from Resource by
    # project's own head - the right home, since every month in it is a cell in that
    # table - and what that move costs is paid back by the button saying the count rather
    # than naming the screen. If it ever reads as a plain label again, this says so.
    pg.click('nav [data-tab="t-overall"]')
    pg.wait_for_timeout(1400)
    # r""" because the JS carries a regex: \s in an ordinary Python string is an invalid
    # escape, which still works and still warns - and tools/test_layers.py fails the build
    # on a warning, because a build the preparer is told to trust must not print one.
    btn = pg.evaluate(r"""() => { const b = document.querySelector(
      '#t-overall .panel[data-panel="table-proj"] .phead .gapbtn');
      return b ? {txt: b.innerText.replace(/\s+/g, ' ').trim(),
                  on: b.classList.contains('on')} : null; }""")
    check(btn and btn["on"] and "1 short" in btn["txt"] and "1 over" in btn["txt"],
          "the control in Resource by project's head STATES the finding, it does not just "
          "name the screen behind it", btn["txt"] if btn else "no control")
    check(pg.evaluate("() => !document.getElementById('gappanel')"),
          "and the panel it replaced is gone from the tab")
    pg.click('#t-overall .panel[data-panel="table-proj"] .phead .gapbtn')
    pg.wait_for_timeout(700)
    opened = pg.evaluate("""() => ({open: document.getElementById('gapsdlg').open,
      rows: document.querySelectorAll('#gapsBody tr.gaprow').length})""")
    check(opened["open"] and opened["rows"] == 2,
          "clicking it opens the list, with every month in it",
          f"{opened['rows']} row(s)")
    # A row opens the MONTH on top of the list, and one Escape comes back to the list -
    # which is where the next month you want to look at is.
    pg.click("#gapsBody tr.gaprow")
    pg.wait_for_timeout(800)
    stack = pg.evaluate("""() => ({list: document.getElementById('gapsdlg').open,
      month: document.getElementById('gapdlg').open,
      top: (document.elementFromPoint(innerWidth / 2, innerHeight / 2)
            .closest('dialog') || {}).id})""")
    check(stack["list"] and stack["month"] and stack["top"] == "gapdlg",
          "a row opens the month ON TOP of the list, not instead of it")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(600)
    back = pg.evaluate("""() => ({list: document.getElementById('gapsdlg').open,
      month: document.getElementById('gapdlg').open})""")
    check(back["list"] and not back["month"],
          "and Escape comes back to the list rather than to the page")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    check(not pg.evaluate("() => document.getElementById('gapsdlg').open"),
          "a second Escape closes the list")
    # The tile above opens the same thing, so there is one list and not two.
    pg.click("#t-overall .tile.gap")
    pg.wait_for_timeout(700)
    check(pg.evaluate("() => document.getElementById('gapsdlg').open"),
          "the tile opens the same list — one list, reached two ways")

    # ---- R-53: the list can be narrowed, and the ALARM must not move with it --------
    # Three controls, each answering a question somebody arrives with. The one that has
    # to be held hardest is the last check here: narrowing a view must never change what
    # the tile and the control in the panel head report, or the alarm would be lying
    # about the plan to suit whoever last touched a drop-down.
    def nrows():
        return pg.evaluate("() => document.querySelectorAll('#gapsBody tr.gaprow').length")

    def alarm():
        # r""" again: the JS carries a regex, and \s in an ordinary Python string is an
        # invalid escape that test_layers.py fails the build on.
        return pg.evaluate(r"""() => { const b = document.querySelector(
          '#t-overall .panel[data-panel="table-proj"] .phead .gapbtn');
          const tile = [...document.querySelectorAll('#t-overall .tile')]
            .find(x => /OFF THEIR STANDARD/i.test(x.innerText));
          return [b.innerText.replace(/\s+/g, ' ').trim(),
                  tile.innerText.replace(/\s+/g, ' ').trim()]; }""")

    before = alarm()
    check(nrows() == 2, "both months are listed to begin with", f"{nrows()} row(s)")
    pg.click('[data-gapdir="short"]')
    pg.wait_for_timeout(600)
    only = pg.evaluate("""() => [...new Set([...document.querySelectorAll('#gapsBody tr.gaprow')]
      .map(r => r.classList.contains('short') ? 'short' : 'over'))]""")
    check(nrows() == 1 and only == ["short"],
          "narrowing to SHORT leaves the short one and nothing else", str(only))
    check(pg.evaluate("() => (document.querySelector('#gapsBody .scope')||{}).textContent")
          .replace("\n", " ").split("across")[0].strip().startswith("1 of 2"),
          "and the heading says how many of how many, so a narrowed list cannot read as "
          "the whole of it")
    # Redrawn first, deliberately. Narrowing the list does not redraw the panel behind it,
    # so reading the control straight after would pass against a build where the count
    # DOES follow the filter - it would simply be showing a stale figure. The page is put
    # through a full render, and only then asked.
    pg.evaluate("() => renderKeepingTab()")
    pg.wait_for_timeout(900)
    check(alarm() == before,
          "THE TILE AND THE CONTROL DO NOT MOVE, through a full redraw with the filter "
          "still on. They are the alarm; a figure that followed somebody's drop-down "
          "would be an alarm that lies", str(alarm()))
    check(nrows() == 1, "and the list is still narrowed after that redraw", f"{nrows()} row(s)")

    pg.click('[data-gapdir="over"]')
    pg.wait_for_timeout(600)
    check(nrows() == 1, "and OVER leaves the other one", f"{nrows()} row(s)")
    # Both gaps so far belong to PRJ-A, so the project control cannot empty the list on
    # its own here - it is the one that CAN, combined with a floor, and the message when
    # it does is what matters.
    opts = pg.evaluate("""() => [...document.querySelectorAll('#gapfProj option')]
      .map(o => o.value)""")
    check(opts == ["", "PRJ-A"],
          "the project control offers only the projects that actually have a gap — a list "
          "of sixty-two projects to narrow two rows would be a worse screen", str(opts))
    pg.select_option("#gapfProj", "PRJ-A")
    pg.wait_for_timeout(600)
    check(nrows() == 1, "picking the one project that has them changes nothing, which is "
                        "the honest answer")
    pg.fill("#gapfMin", "99")
    pg.wait_for_timeout(700)
    check(nrows() == 0, "and a floor nothing reaches empties it")
    body = pg.evaluate("() => el('gapsBody').innerText")
    check("hidden by the filter" in body and "Clear" in body,
          "and it says they are HIDDEN rather than that there is nothing to report — the "
          "two are different answers and only one of them is good news")
    pg.click("[data-gapclear]")
    pg.wait_for_timeout(600)
    check(nrows() == 2 and alarm() == before,
          "Clear brings them all back", f"{nrows()} row(s)")

    # The smallest-gap field answers as it is typed, and keeps the caret.
    pg.fill("#gapfMin", "4")
    pg.wait_for_timeout(700)
    kept = pg.evaluate("() => document.activeElement.id")
    check(nrows() == 2 and kept == "gapfMin",
          "a floor of 4.00 keeps both 5.00 gaps, and the field keeps the focus as it is "
          "typed into", f"{nrows()} row(s), focus on {kept!r}")
    pg.fill("#gapfMin", "6")
    pg.wait_for_timeout(700)
    check(nrows() == 0, "a floor of 6.00 keeps neither")
    pg.click("[data-gapclear]")
    pg.wait_for_timeout(600)

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)

    print("\n4. an assignment can do it too, and V-34 reports either")
    pg.click('nav [data-tab="t-pers"]')
    pg.wait_for_timeout(900)
    pg.evaluate("() => { S.selPers='PSN-003'; S.selAsg='ASG-003'; renderKeepingTab(); }")
    pg.wait_for_timeout(700)
    pg.evaluate("() => switchEstimation('assignment', 'ASG-003')")
    pg.wait_for_timeout(300)
    pg.click("#estYes")
    pg.wait_for_timeout(1200)
    set_fte(pg, "assignment", "ASG-003", mkey(1), 14.00)
    g = dict((r[0], r) for r in pg.evaluate(GAPS))
    check(g.get("PRJ-B|" + str(OCT)) and g["PRJ-B|" + str(OCT)][4] == "over"
          and g["PRJ-B|" + str(OCT)][1] == 10,
          "PRJ-B is over its standard with no project figure at all — one person's "
          "stated month did it", str(g.get("PRJ-B|" + str(OCT))))
    check(pg.evaluate(SUMS) == [], "and that month is still its people's sum too")
    got = pg.evaluate("""() => (S.model.findings||[]).filter(f => f.rule === 'V-34')
        .map(f => [f.sev, f.msg])""")
    check(len(got) == 2 and all(s == "warning" for s, _ in got),
          "one finding per PROJECT, not per month — 24 months of one decision is one "
          "decision", f"{len(got)} findings")
    check(any("SHORT" in m and "OVER" in m for _, m in got),
          "and a project with months both ways names both in the one finding")

    print("\n5. it reports; it never refuses and never gates a save")
    check(pg.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-34')"
                      ".every(f => !refuses(f))"),
          "refuses() is false for every one of them — warnings are not errors, and "
          "departing from the standard is the POINT of a manual figure")
    check(pg.evaluate("() => !(S.model.findings||[]).filter(blocking).length"),
          "nothing is blocking, so Save is not held")

    print("\n6. the figure is marked where it is DRAWN, not only where it is explained")
    pg.click('nav [data-tab="t-overall"]')
    pg.wait_for_timeout(1600)
    marks = pg.evaluate("""() => [...document.querySelectorAll('#t-overall td.c.gapc')]
        .map(t => [t.dataset.gap, t.dataset.gk, t.className.includes('short') ? 'short'
                                                                             : 'over'])""")
    check(len(marks) == 3 and sorted(m[2] for m in marks) == ["over", "over", "short"],
          "every gap month carries a mark in Resource by project", str(marks))
    check(pg.evaluate("""() => [...document.querySelectorAll('#t-overall td.c.gapc')]
            .every(t => t.dataset.gap && t.dataset.gk)"""),
          "and each one opens its own month rather than the panel in general")
    # THE CHARACTER, not merely "something". This asked whether ::after content was
    # non-empty, and passed for weeks while those cells printed the text \25B2 - a
    # doubled backslash in the stylesheet, so the escape was never an escape. A mark that
    # is present but says the wrong thing is exactly what "non-empty" cannot see, and it
    # is the failure D-04 is about: where amber and red are the confusable pair, the arrow
    # is the whole of what tells the two directions apart.
    arrows = pg.evaluate("""() => {
        const out = {};
        for (const dir of ['short', 'over']){
          const t = document.querySelector('#t-overall td.c.gapc.' + dir);
          out[dir] = t ? getComputedStyle(t, '::after').content.replace(/^"|"$/g, '')
                       : 'no such cell';
        }
        return out;}""")
    check(arrows.get("short") == "\u25bc" and arrows.get("over") == "\u25b2",
          "carrying an ARROW as well as a colour — amber and red are the confusable "
          "pair, and they are the two directions (D-04)",
          f"short {arrows.get('short')!r}, over {arrows.get('over')!r}")

    print("\n7. the tile counts what the panel lists")
    tile = pg.evaluate("""() => {
        const t = [...document.querySelectorAll('#t-overall .tile')]
          .find(x => x.querySelector('.tl').textContent.includes('Off their standard'));
        return t ? [t.querySelector('.tv').textContent.trim(),
                    t.querySelector('.ts').textContent.trim()] : null;}""")
    check(tile and tile[0] == "3" and "2 short" not in tile[1],
          "the tile totals the same rows the panel draws", str(tile))
    check(tile and tile[1] == "1 short · 2 over",
          "and splits them by direction rather than netting them", str(tile))

    print("\n8. the dialog carries the figures that caused it, and they are editable")
    pg.evaluate("k => openGap('PRJ-A', k)", SEP)
    pg.wait_for_timeout(700)
    body = pg.evaluate("() => el('gapBody').innerText")
    check(pg.evaluate("() => el('gapdlg').open"), "it opens")
    check("10.00" in body and "5.00" in body and "-5.00" in body,
          "naming what it needs, what it is given, and the gap")
    check("standard 10.00" in body and "period weight (1.00)" in body,
          "with the demand term by term, the same derivation the estimation panel shows")
    cells = pg.evaluate("""() => [...el('gapBody')
        .querySelectorAll('td[contenteditable="true"]')]
        .map(t => [t.dataset.sheet || null, t.dataset.gapnew || null,
                   t.textContent.trim()])""")
    check(cells[0] == ["MonthlyEstimate", None, "5"],
          "and the project's stated month as an ORDINARY editable cell over "
          "MonthlyEstimate — one editing path, not a second one to keep in step",
          str(cells[0]))
    # The people on it are automatic here, so they have no row to write through. Their
    # cells offer to CREATE one instead - checked in section 10.
    check(len(cells) == 3 and all(c[1] for c in cells[1:]),
          "and every other Stated cell is editable too", str(cells))

    print("\n9. changing it there closes the gap, through the ordinary edit path")
    before = pg.evaluate("() => S.pending.length")
    pg.evaluate("""() => {
        const t = el('gapBody').querySelector('td[contenteditable="true"]');
        t.dataset.orig = t.textContent;
        t.focus(); t.textContent = '10';
        t.dispatchEvent(new Event('input', {bubbles: true}));
        t.blur();}""")
    pg.wait_for_timeout(1200)
    check(pg.evaluate("k => S.calc.projGap.has('PRJ-A|' + k)", SEP) is False,
          "September is back on its standard")
    check(pg.evaluate("() => S.pending.length") == before + 1,
          "and the edit is in the pending list like any other — logged, listed under "
          "Show details, undone by Leave without change",
          f"{before} → {pg.evaluate('() => S.pending.length')}")
    check("0.00" in pg.evaluate("() => el('gapBody').innerText")
          and pg.evaluate("() => el('gapdlg').open"),
          "and the dialog redrew itself rather than still showing the gap just closed")
    pg.evaluate("() => closeGap()")
    pg.wait_for_timeout(300)
    check(pg.evaluate("() => !el('gapdlg').open"), "Close closes it")

    print("\n10. a person still on AUTO can be given a figure here too")
    pg.evaluate("k => openGap('PRJ-B', k)", OCT)
    pg.wait_for_timeout(700)
    cells = pg.evaluate("""() => [...el('gapBody').querySelectorAll('td.cell')]
        .map(t => [t.dataset.gapnew || ('row ' + t.dataset.row), t.isContentEditable])""")
    check(len(cells) == 2 and all(c[1] for c in cells)
          and any(c[0] == "ASG-004" for c in cells),
          "every Stated cell is editable, including the automatic person's — a dash "
          "there said the screen was read-only on the figure most worth changing",
          str(cells))
    n0 = pg.evaluate("() => S.pending.length")
    pg.evaluate("""() => { const t = el('gapBody')
        .querySelector('td[data-gapnew="ASG-004"]');
        t.focus(); t.dispatchEvent(new Event('focusin', {bubbles: true}));
        t.textContent = '3.5';
        t.dispatchEvent(new Event('focusout', {bubbles: true}));}""")
    pg.wait_for_timeout(800)
    # IT ASKS, and it has to: writing one row against an automatic assignment is a figure
    # nothing reads, and setting the flag without seeding counts every other month as
    # 0.00 (REQ-CAL-18). The switch, the seeding and the typed figure go together.
    check(pg.evaluate("() => el('estchg').open"),
          "typing on an automatic person ASKS before anything is written — stating one "
          "month means owning every month (REQ-CAL-18)")
    check("all 3" in pg.evaluate("() => el('estBody').innerText")
          and "3.50" in pg.evaluate("() => el('estBody').innerText"),
          "naming how many months it will state and what this one becomes",
          pg.evaluate("() => el('estBody').innerText").split(".")[1][:90])
    check(pg.evaluate("() => S.pending.length") == n0,
          "and nothing is written while the question is open")
    pg.click("#estYes")
    pg.wait_for_timeout(1500)
    got = pg.evaluate("""() => ({
        type: S.model.raw.Assignment.find(a => a.assignment_id === 'ASG-004')
                .estimation_type,
        months: S.model.raw.MonthlyEstimate
          .filter(r => r.scope === 'assignment' && r.ref_id === 'ASG-004')
          .map(r => [r.month, r.fte]).sort()})""")
    check(got["type"] == "manual" and len(got["months"]) == 3,
          "every month is seeded, not just the one typed — the other two would count as "
          "0.00 otherwise, which is the one change that silently zeroes a figure",
          str(got["months"]))
    check(dict(got["months"])[mkey(1)] == 3.5,
          "and the month typed carries what was typed", str(got["months"]))
    check(pg.evaluate("() => S.pending.length") - n0 == 5,
          "logged as what it is: the switch, three seeded months, and the one change",
          f"{pg.evaluate('() => S.pending.length') - n0} entries")
    check(pg.evaluate("() => el('gapdlg').open")
          and "MANUAL" in pg.evaluate("() => el('gapBody').innerText"),
          "the dialog redrew and now shows that person as MANUAL")

    print("\n11. already manual with no figure for this month (V-31) does NOT ask")
    pg.evaluate("""mk => { const rs = S.model.raw.MonthlyEstimate;
        const i = rs.findIndex(r => r.scope === 'assignment' && r.ref_id === 'ASG-004'
                                 && r.month === mk);
        rs.splice(i, 1); rebuild(true); renderKeepingTab();}""", mkey(2))
    pg.wait_for_timeout(900)
    check(pg.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-31').length")
          == 1, "the missing month is V-31 — counted as 0.00 until it is filled in")
    pg.evaluate("k => openGap('PRJ-B', k)", M0 + 2)
    pg.wait_for_timeout(700)
    n1 = pg.evaluate("() => S.pending.length")
    pg.evaluate("""() => { const t = el('gapBody')
        .querySelector('td[data-gapnew="ASG-004"]');
        t.focus(); t.dispatchEvent(new Event('focusin', {bubbles: true}));
        t.textContent = '2';
        t.dispatchEvent(new Event('focusout', {bubbles: true}));}""")
    pg.wait_for_timeout(1000)
    check(not pg.evaluate("() => el('estchg').open"),
          "no question this time: the months are already this person's, so asking would "
          "be asking permission for something already given")
    check(pg.evaluate("""mk => S.model.raw.MonthlyEstimate.filter(
            r => r.scope === 'assignment' && r.ref_id === 'ASG-004'
              && r.month === mk).map(r => r.fte)""", mkey(2)) == [2],
          "the figure is simply written")
    check(pg.evaluate("() => S.pending.length") - n1 == 1,
          "as one ordinary logged edit")

    print("\n12. and a figure that is not one is refused, not written")
    # PRJ-A in October: its two people were never switched, so both their cells are
    # still offering to create a row - which is the path being checked.
    pg.evaluate("k => openGap('PRJ-A', k)", OCT)
    pg.wait_for_timeout(700)
    n2 = pg.evaluate("() => S.pending.length")
    before_rows = pg.evaluate("() => S.model.raw.MonthlyEstimate.length")
    got = pg.evaluate("""() => { const t = el('gapBody')
        .querySelector('td[data-gapnew="ASG-002"]');
        if (!t) return 'no creating cell to type into';
        t.focus(); t.dispatchEvent(new Event('focusin', {bubbles: true}));
        t.textContent = 'abc';
        t.dispatchEvent(new Event('focusout', {bubbles: true}));
        return 'typed';}""")
    check(got == "typed", "the automatic person's cell is there to type into", got)
    pg.wait_for_timeout(800)
    check(not pg.evaluate("() => el('estchg').open"),
          "nonsense does not even get as far as the question")
    check(pg.evaluate("() => S.model.raw.MonthlyEstimate.length") == before_rows
          and pg.evaluate("() => S.pending.length") == n2,
          "no row created and nothing logged")
    check("not a figure" in pg.evaluate("() => el('banner').textContent || ''"),
          "and it says why, in the words the rest of the application uses",
          pg.evaluate("() => (el('banner').textContent || '').slice(0, 70)"))
    pg.evaluate("() => closeGap()")
    pg.wait_for_timeout(300)

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print("\nFAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
