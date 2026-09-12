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

    python tools/test_gap.py
"""

import pathlib
import sys
import tempfile
from datetime import date

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_gap_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []
BASE = prap_io.read_xlsx(ROOT / "templates" / "PRAP_SourceData_Template_v1.15.xlsx")
SEP = 2026 * 12 + 8
OCT = 2026 * 12 + 9


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def fixture():
    """Two projects, each needing 10.00 a month through Start-up, two people apiece."""
    S = {k: (list(v) if isinstance(v, list) else v) for k, v in BASE.items()}
    S["Project"] = [{"project_id": pid, "project_name": nm, "project_type": "NewDrug CT",
                     "clinical_phase": "Phase 3", "work_scope_type": "fully in-housed",
                     "project_category": "Onc", "start_date": date(2026, 9, 1),
                     "end_date": date(2026, 11, 30), "status": "Active", "__row": 2 + i}
                    for i, (pid, nm) in enumerate([("PRJ-A", "Alpha"), ("PRJ-B", "Bravo")])]
    S["Milestone"] = []
    S["ProjectPeriod"] = [{"project_id": pid, "period_name": "Start-up", "period_seq": 1,
                           "period_start": date(2026, 9, 1), "period_end": date(2026, 11, 30),
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
    set_fte(pg, "project", "PRJ-A", "2026-09", 5.00)
    g = dict((r[0], r) for r in pg.evaluate(GAPS))
    check(g.get("PRJ-A|" + str(SEP)) == ["PRJ-A|" + str(SEP), 10, 5, -5.0, "short"],
          "needs 10.00, given 5.00, short by 5.00", str(g.get("PRJ-A|" + str(SEP))))
    check(pg.evaluate(SUMS) == [],
          "and the month is STILL exactly its people's sum — they were scaled to the "
          "stated figure, which is what REQ-CAL-18 does")

    print("\n3. both directions, counted apart and never netted")
    set_fte(pg, "project", "PRJ-A", "2026-10", 15.00)
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
    panel = pg.evaluate("() => gapPanel(activeProjects())")
    check(panel.count("month(s) short of the standard") == 1
          and panel.count("month(s) over it") == 1,
          "and the panel says each direction in its own words, side by side")

    print("\n4. an assignment can do it too, and V-34 reports either")
    pg.click('nav [data-tab="t-pers"]')
    pg.wait_for_timeout(900)
    pg.evaluate("() => { S.selPers='PSN-003'; S.selAsg='ASG-003'; renderKeepingTab(); }")
    pg.wait_for_timeout(700)
    pg.evaluate("() => switchEstimation('assignment', 'ASG-003')")
    pg.wait_for_timeout(300)
    pg.click("#estYes")
    pg.wait_for_timeout(1200)
    set_fte(pg, "assignment", "ASG-003", "2026-10", 14.00)
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
    check(pg.evaluate("""() => {
            const t = document.querySelector('#t-overall td.c.gapc');
            const s = getComputedStyle(t, '::after').content;
            return s && s !== 'none' && s !== 'normal';}"""),
          "carrying an arrow as well as a colour — amber and red are the confusable "
          "pair, and they are the two directions (D-04)")

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
    pg.evaluate("() => openGap('PRJ-A', 2026 * 12 + 8)")
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
    check(pg.evaluate("() => S.calc.projGap.has('PRJ-A|' + (2026 * 12 + 8))") is False,
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
    pg.evaluate("() => openGap('PRJ-B', 2026 * 12 + 9)")
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
    check(dict(got["months"])["2026-10"] == 3.5,
          "and the month typed carries what was typed", str(got["months"]))
    check(pg.evaluate("() => S.pending.length") - n0 == 5,
          "logged as what it is: the switch, three seeded months, and the one change",
          f"{pg.evaluate('() => S.pending.length') - n0} entries")
    check(pg.evaluate("() => el('gapdlg').open")
          and "MANUAL" in pg.evaluate("() => el('gapBody').innerText"),
          "the dialog redrew and now shows that person as MANUAL")

    print("\n11. already manual with no figure for this month (V-31) does NOT ask")
    pg.evaluate("""() => { const rs = S.model.raw.MonthlyEstimate;
        const i = rs.findIndex(r => r.scope === 'assignment' && r.ref_id === 'ASG-004'
                                 && r.month === '2026-11');
        rs.splice(i, 1); rebuild(true); renderKeepingTab();}""")
    pg.wait_for_timeout(900)
    check(pg.evaluate("() => (S.model.findings||[]).filter(f => f.rule === 'V-31').length")
          == 1, "the missing month is V-31 — counted as 0.00 until it is filled in")
    pg.evaluate("() => openGap('PRJ-B', 2026 * 12 + 10)")
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
    check(pg.evaluate("""() => S.model.raw.MonthlyEstimate.filter(
            r => r.scope === 'assignment' && r.ref_id === 'ASG-004'
              && r.month === '2026-11').map(r => r.fte)""") == [2],
          "the figure is simply written")
    check(pg.evaluate("() => S.pending.length") - n1 == 1,
          "as one ordinary logged edit")

    print("\n12. and a figure that is not one is refused, not written")
    # PRJ-A in October: its two people were never switched, so both their cells are
    # still offering to create a row - which is the path being checked.
    pg.evaluate("() => openGap('PRJ-A', 2026 * 12 + 9)")
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
