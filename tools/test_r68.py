"""The timeline's years stay on screen, and projects can be filtered by status (R-68).

Asked for from the field:

  1) On the Overall tab's Project timeline the years along the top scrolled away with
     the rows, so further down every year line was an unlabelled rule and which one was
     2028 had to be remembered. They should stay fixed while the timeline scrolls.
  2) A filter on the project's status: projects not started yet, or already finished,
     make the page busy - choosing a status should leave only the projects that have it.

What is checked:

  * THE YEARS ARE A BAR OF THEIR OWN, sticky to the top of the timeline's scroll region:
    still at its top after the rows have scrolled a long way under it. Made un-sticky
    again, the same bar is carried off the top with the rows - so the check can fail.
  * Every label sits over its own year line, at rest and with the timeline scrolled
    sideways; Today is in the bar, clear of every year's label.
  * A one-project timeline, with nothing to scroll past, keeps its years in the drawing.
  * The status filter offers the statuses in the file in the order a project lives
    through them, and "(no status)" when some project has none; one status narrows every
    tab to the projects that have it, two widen it again (OR), and it narrows together
    with the other filters (AND). Reset filters clears it, and the calculated-FTE export
    says it was on.

    python tools/test_r68.py
"""

import pathlib
import sys
import tempfile

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
BIG = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.24.xlsx"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_r68_"))
TL = '#t-overall .panel[data-panel="timeline"]'

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


# Where the bar is against its scroll region, and each label against its year line.
GEOM = """sel => { const p = document.querySelector(sel), box = p.querySelector('.scrollx');
  const bar = box.querySelector('.gaxis'), svg = box.querySelector('svg.chart');
  if (!bar || !svg) return null;
  const s = svg.getBoundingClientRect(), k = s.width / svg.viewBox.baseVal.width;
  const lines = [...svg.querySelectorAll('line.grid')].map(l => s.left + (+l.getAttribute('x1')) * k);
  const labels = [...bar.querySelectorAll('.gy')].map(e => { const r = e.getBoundingClientRect();
    return {y: e.textContent, mid: r.left + r.width / 2}; });
  const off = labels.map((l, i) => Math.abs(l.mid - lines[i]));
  return {barTop: bar.getBoundingClientRect().top - box.getBoundingClientRect().top,
          scrollTop: box.scrollTop, scrollLeft: box.scrollLeft,
          years: labels.map(l => l.y), nLines: lines.length, worst: Math.max(0, ...off),
          inSvg: svg.querySelectorAll('text.ax').length}; }"""

print("R-68 — the timeline's years stay on screen; a filter on project status")
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME, downloads_path=str(TMP))
    ctx = b.new_context(accept_downloads=True, viewport={"width": 1500, "height": 950})
    pg = ctx.new_page()
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.wait_for_timeout(400)
    pg.set_input_files("#picker", str(BIG))
    pg.wait_for_timeout(4500)

    # ------------------------------------------------------------------ 1
    print("\n1. the years stay on screen")
    pg.locator(TL).scroll_into_view_if_needed()
    g0 = pg.evaluate(GEOM, TL)
    check(g0 and g0["years"] and len(g0["years"]) == g0["nLines"] and g0["inSvg"] == 0,
          "THE YEARS ARE A BAR OF THEIR OWN — one label per year line, none left in the drawing",
          f"{g0['years']}" if g0 else "no bar")
    check(g0 and g0["worst"] <= 1.5, "and each label is centred over its own line",
          f"worst {g0['worst']:.2f}px" if g0 else "")
    pg.evaluate("s => { document.querySelector(s + ' .scrollx').scrollTop = 1200; }", TL)
    pg.wait_for_timeout(300)
    g1 = pg.evaluate(GEOM, TL)
    check(g1 and g1["scrollTop"] > 600 and abs(g1["barTop"]) <= 1,
          "SCROLLED A LONG WAY DOWN, THE BAR IS STILL AT THE TOP OF THE TIMELINE",
          f"scrolled {g1['scrollTop']}px, bar at {g1['barTop']:.1f}px" if g1 else "")
    seen = pg.evaluate("""s => { const e = document.querySelector(s + ' .gaxis .gy'),
        r = e.getBoundingClientRect(), at = document.elementFromPoint(r.left + r.width / 2,
        r.top + r.height / 2); return !!at && e.contains(at); }""", TL)
    check(seen, "and its labels are what is on screen there, in front of the rows")
    gone = pg.evaluate("""s => { const bar = document.querySelector(s + ' .gaxis');
        bar.style.position = 'static';
        const box = document.querySelector(s + ' .scrollx');
        const t = bar.getBoundingClientRect().top - box.getBoundingClientRect().top;
        bar.style.position = ''; return t; }""", TL)
    check(gone < -600, "   (not held there, the same bar is carried off with the rows)",
          f"{gone:.0f}px above the region")

    now = pg.evaluate("""s => { const t = document.querySelector(s + ' .gaxis .gnow');
        if (!t) return null; const r = t.getBoundingClientRect();
        const hit = [...document.querySelectorAll(s + ' .gaxis .gy')].filter(e => {
          const q = e.getBoundingClientRect();
          return q.left < r.right && q.right > r.left; }).map(e => e.textContent);
        return {text: t.textContent, hit}; }""", TL)
    check(now and now["text"] == "Today" and not now["hit"],
          "Today is in the bar too, clear of every year's label", str(now))

    pg.set_viewport_size({"width": 1100, "height": 900})
    pg.wait_for_timeout(1200)
    pg.locator(TL).scroll_into_view_if_needed()
    pg.evaluate("s => { const b = document.querySelector(s + ' .scrollx'); b.scrollLeft = 160; b.scrollTop = 500; }", TL)
    pg.wait_for_timeout(300)
    g2 = pg.evaluate(GEOM, TL)
    check(g2 and g2["scrollLeft"] > 100 and g2["worst"] <= 1.5 and abs(g2["barTop"]) <= 1,
          "SCROLLED SIDEWAYS AS WELL, every label still sits over its own line",
          f"scrollLeft {g2['scrollLeft']}, worst {g2['worst']:.2f}px" if g2 else "")
    pg.set_viewport_size({"width": 1500, "height": 950})
    pg.wait_for_timeout(1200)

    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(1000)
    single = pg.evaluate("""() => { const p = document.querySelector('#t-proj .panel[data-panel="proj-timeline"]');
        return {bar: !!p.querySelector('.gaxis'), years: p.querySelectorAll('svg text.ax').length}; }""")
    check(not single["bar"] and single["years"] >= 1,
          "a one-project timeline has nothing to scroll past, and keeps its years in the drawing",
          str(single))
    pg.click('nav button[data-tab="t-pers"]')
    pg.wait_for_timeout(1000)
    check(pg.locator('#t-pers .panel[data-panel="pers-timeline"] .gaxis').count() == 1,
          "the person's own Project timeline has the bar too")
    pg.click('nav button[data-tab="t-overall"]')
    pg.wait_for_timeout(800)

    # ------------------------------------------------------------------ 2
    print("\n2. a filter on project status")
    order = pg.evaluate("""() => { const c = [...document.querySelectorAll('#filterbar .ctl')]
        .map(e => (e.querySelector('.lbl, label') || {}).textContent || '');
        return c.map(t => t.trim()).filter(Boolean); }""")
    i = order.index("Project status") if "Project status" in order else -1
    check(i > 0 and order[i - 1] == "Work scope" and order[i + 1] == "Project",
          "THE FILTER BAR HAS A PROJECT STATUS FILTER, beside the project's other attributes",
          " · ".join(order))
    pg.click("#fStatus summary")
    pg.wait_for_timeout(300)
    opts = pg.eval_on_selector_all("#fStatus .msp label", "ls => ls.map(l => l.textContent)")
    inFile = pg.evaluate("[...new Set(Object.values(S.model.projects).map(statusOf))]")
    check(opts == [s for s in ["Planned", "Active", "On hold", "Completed"] if s in inFile]
          and sorted(opts) == sorted(inFile),
          "it offers the statuses in the file, in the order a project lives through them",
          " · ".join(opts))

    def pick(*vals):
        for v in vals:
            pg.locator("#fStatus .msp label", has_text=v).locator("input").check()
            pg.wait_for_timeout(900)

    def shown():
        return pg.evaluate("""() => ({
          active: activeProjects().length,
          statuses: [...new Set(activeProjects().map(p => statusOf(S.model.projects[p])))].sort(),
          timeline: document.querySelectorAll('#t-overall .panel[data-panel="timeline"] svg text.rowlab').length,
          table: document.querySelectorAll('#t-overall .panel[data-panel="table-proj"] tr.parent').length,
          tile: +[...document.querySelectorAll('#t-overall .tile')]
                  .find(t => t.textContent.includes('Projects in view')).querySelector('.tv').textContent})""")

    n_active = pg.evaluate("Object.values(S.model.projects).filter(p => p.status === 'Active').length")
    pick("Active")
    s1 = shown()
    check(s1["statuses"] == ["Active"] and s1["active"] == n_active == s1["tile"] == s1["timeline"],
          "CHOOSING ACTIVE LEAVES ONLY THE ACTIVE PROJECTS — the tile, the timeline and the "
          "lists agree", f"{n_active} active of {len(pg.evaluate('Object.keys(S.model.projects)'))}; {s1}")
    check(s1["table"] <= n_active and pg.inner_text("#fStatus summary").strip() == "Active",
          "and the closed control says what it is narrowed to", pg.inner_text("#fStatus summary"))
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(1000)
    rows = pg.evaluate("""() => [...document.querySelectorAll("#t-proj .data-t[data-sheet='Project'] tbody tr[data-id]")]
        .map(tr => S.model.projects[tr.dataset.id] ? S.model.projects[tr.dataset.id].status : 'draft')""")
    check(rows and set(rows) == {"Active"},
          "the Projects table on Source data (project) lists only them too", f"{len(rows)} rows")
    pg.click('nav button[data-tab="t-overall"]')
    pg.wait_for_timeout(800)

    pg.click("#fStatus summary")
    pg.wait_for_timeout(200)
    pick("Planned")
    s2 = shown()
    n_two = pg.evaluate("Object.values(S.model.projects).filter(p => ['Active','Planned'].includes(p.status)).length")
    check(s2["statuses"] == ["Active", "Planned"] and s2["active"] == n_two,
          "A SECOND STATUS WIDENS IT — Active or Planned", f"{n_two} projects")
    pg.click("#fType summary")
    pg.wait_for_timeout(200)
    t0 = pg.eval_on_selector("#fType .msp label input", "i => i.value")
    pg.locator("#fType .msp label input").first.check()
    pg.wait_for_timeout(900)
    both = pg.evaluate("""t => ({got: activeProjects().length,
        want: Object.values(S.model.projects).filter(p => ['Active','Planned'].includes(p.status)
          && p.project_type === t).length})""", t0)
    check(both["got"] == both["want"] and both["got"] < n_two,
          "and narrows TOGETHER with the other filters", f"{t0}: {both}")

    pg.click("#exportBtn")
    pg.wait_for_timeout(300)
    with pg.expect_download() as dl:
        pg.click("#exportCalcBtn")
    out = TMP / "calc.xlsx"
    dl.value.save_as(out)
    readme = " ".join(str(c.value or "") for r in load_workbook(out)["00_ReadMe"].iter_rows() for c in r)
    check("Project status: Active, Planned" in readme or "Project status: Planned, Active" in readme,
          "THE CALCULATED-FTE EXPORT SAYS THE STATUS FILTER WAS ON",
          readme[readme.find("Project status"):][:60])

    pg.click("#fReset")
    pg.wait_for_timeout(1200)
    check(pg.evaluate("S.f.status.size") == 0 and pg.inner_text("#fStatus summary").strip() == "All"
          and pg.evaluate("activeProjects().length") == len(pg.evaluate("Object.keys(S.model.projects)")),
          "Reset filters clears it, with the rest")

    lone = pg.evaluate("""() => { const r = S.model.raw.Project[0]; r.status = null; rebuild(true);
        fillFilters(); renderKeepingTab(); return r.project_id; }""")
    pg.wait_for_timeout(1000)
    pg.click("#fStatus summary")
    pg.wait_for_timeout(200)
    opts = pg.eval_on_selector_all("#fStatus .msp label", "ls => ls.map(l => l.textContent)")
    pick("(no status)")
    got = pg.evaluate("activeProjects()")
    check(opts[-1] == "(no status)" and got == [lone],
          "A PROJECT WITH NO STATUS IS STILL REACHABLE — '(no status)', last, lists exactly it",
          f"{opts} -> {got}")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    b.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
