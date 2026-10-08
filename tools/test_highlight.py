"""A milestone marked in a colour, and the mark found where it was asked for.

Schema 13 adds Milestone.milestone_highlight. What a user asked for is simple - "let me
pick a colour and have that milestone stand out on the timeline" - and what makes it
worth a test of its own is that the mark has to survive four separate journeys to be any
use: out of the workbook, into the model, onto two different charts, and back into the
file when the plan is exported. A colour that reaches the Overall tab and not the
project's own tab is a feature that works in the demo and fails in the room.

  1. the column is read, and only a value naming a colour is believed
  2. BOTH timelines draw the marker in that colour - Overall and Source data (project)
  3. the legend says what the FILE calls the colour, not the word "red"
  4. the milestone table shows the colour in its cell, and the cell still reads back as
     the plain value - the chip is drawn, not stored
  5. a value naming no colour is V-37, and the milestone draws unmarked rather than
     silently dropping the mark
  6. an empty column is exactly what it was before schema 13: no mark, no finding

The round trip - workbook to JSON to workbook with the colour intact - is not repeated
here: the column is part of the sheet's headers, so tools/test_interop.py carries it
through both forms against the same fixture, and a check that only looked like it was
testing the round trip would be worse than none.

    python tools/build_app.py && python tools/test_highlight.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.13.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def load(pg, path):
    """Load a workbook, saying yes if the page asks before replacing unsaved edits."""
    pg.set_input_files("input[type=file]", str(path))
    pg.wait_for_timeout(600)
    if pg.evaluate("() => !!(document.getElementById('replace') || {}).open"):
        pg.click("#rpYes")
    pg.wait_for_timeout(2400)


def main():
    if not DUMMY.exists():
        raise SystemExit(f"missing {DUMMY} - run python tools/build_source_workbook.py")
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME)
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(APP)
        pg.wait_for_timeout(700)
        pg.set_input_files("input[type=file]", str(DUMMY))
        pg.wait_for_timeout(2500)

        print("app/PRAP.html - a milestone marked in a colour")

        # ---- 1. the column reaches the model -------------------------------
        marked = pg.evaluate("Object.keys(S.model.msHighlight).length")
        labels = pg.evaluate("S.model.hlLabels")
        check(marked > 0 and labels, "the workbook's colours reach the model",
              f"{marked} project(s), {labels}")

        # ---- 2. the Overall timeline draws them ----------------------------
        overall = pg.evaluate(
            "document.querySelectorAll('#t-overall polygon.ms[class*=hl-]').length")
        check(overall > 0, "THE OVERALL TIMELINE DRAWS THE MARKER IN THAT COLOUR",
              f"{overall} marked marker(s)")
        fill = pg.evaluate("""() => {
            const el = document.querySelector('#t-overall polygon.ms[class*=hl-]');
            return el ? getComputedStyle(el).fill : null; }""")
        plain = pg.evaluate("""() => {
            const el = [...document.querySelectorAll('#t-overall polygon.ms')]
              .find(e => !/hl-|key/.test(e.className.baseVal));
            return el ? getComputedStyle(el).fill : null; }""")
        check(fill and plain and fill != plain,
              "and it is a DIFFERENT colour from an unmarked milestone - the mark is "
              "visible, not merely recorded", f"{fill} vs {plain}")

        # ---- 3. the legend speaks the file's own words ---------------------
        leg = pg.evaluate("""() => [...document.querySelectorAll('#t-overall .legend li')]
            .map(l => l.textContent.trim())""")
        want = list(pg.evaluate("Object.values(S.model.hlLabels)"))
        check(all(any(w in t for t in leg) for w in want),
              "the legend names the colour as the FILE names it, not as 'red'",
              "; ".join(w for w in want))
        check(not any("Highlight" in t and t.strip() in ("red", "orange") for t in leg),
              "and it lists only the colours in use", f"{len(leg)} legend entries")

        # ---- 4. the project's own tab, and the table cell ------------------
        pid = pg.evaluate("Object.keys(S.model.msHighlight)[0]")
        pg.click("text=Source data (project)")
        pg.wait_for_timeout(1300)
        pg.click(f'#t-proj tr[data-id="{pid}"] td.cell')
        pg.wait_for_timeout(1300)
        own = pg.evaluate("document.querySelectorAll('#t-proj polygon.ms[class*=hl-]').length")
        check(own > 0, "THE PROJECT'S OWN TIMELINE DRAWS IT TOO - the same mark on both "
                       "tabs, which is what was asked for", f"{own} marked marker(s)")
        cell = pg.evaluate("""() => {
            const td = document.querySelector('#t-proj td.cell[data-hl]');
            if (!td) return null;
            return {hl: td.dataset.hl, text: td.textContent,
                    chip: getComputedStyle(td, '::before').backgroundColor}; }""")
        check(cell and cell["hl"], "the milestone table marks the cell", str(cell))
        check(cell and "Highlight" in cell["text"] and "\\u200b" not in cell["text"],
              "AND THE CELL STILL READS BACK AS THE PLAIN VALUE - the chip is drawn, "
              "never stored, so editing the cell cannot pick it up",
              repr(cell["text"]) if cell else "")

        # ---- 5. a value naming no colour -----------------------------------
        bad = pg.evaluate("""() => {
            const r = S.model.raw.Milestone.find(m => m.milestone_highlight);
            r.milestone_highlight = 'Hilight (Read)';
            rebuild(true); renderKeepingTab();
            return S.model.findings.filter(f => f.rule === 'V-37').length; }""")
        check(bad >= 1, "A VALUE NAMING NO COLOUR IS REPORTED (V-37), not silently "
                        "dropped - an unmarked milestone looks exactly like one nobody "
                        "marked", f"{bad} finding(s)")
        drawn = pg.evaluate(
            "document.querySelectorAll('#t-proj polygon.ms[class*=hl-]').length")
        check(drawn < own, "and that milestone draws unmarked rather than guessing",
              f"{drawn} left of {own}")

        # ---- 6. and an empty column is the old behaviour --------------------
        clean = pg.evaluate("""() => {
            for (const m of S.model.raw.Milestone) m.milestone_highlight = null;
            rebuild(true); renderKeepingTab();
            return {hl: Object.keys(S.model.msHighlight).length,
                    v37: S.model.findings.filter(f => f.rule === 'V-37').length,
                    ms: document.querySelectorAll('polygon.ms').length}; }""")
        check(clean["hl"] == 0 and clean["v37"] == 0 and clean["ms"] > 0,
              "an empty column is exactly what it was before schema 13: no mark, no "
              "finding, every milestone still drawn", str(clean))

        # ---- 7. periods (schema 14, R-59) -------------------------------------
        # A fresh load: the milestone checks above edited the model in place.
        print("\nperiods - drawn gray unless a colour is chosen")
        load(pg, DUMMY)
        # This section is about the PROJECT'S own column (R-59), so the default colours
        # (R-60, section 8) are taken away first: with them on, an unmarked period is
        # not gray, and every count below would be measuring the defaults instead.
        pg.evaluate("() => { S.model.raw.PeriodHighlight = []; rebuild(true); renderKeepingTab(); }")
        pg.wait_for_timeout(600)
        pg.click('button[role=tab][data-tab="t-overall"]')
        pg.wait_for_timeout(700)
        bands = pg.evaluate("""() => {
            const all = [...document.querySelectorAll(
              '#t-overall .panel[data-panel="timeline"] rect.band')];
            const fill = e => getComputedStyle(e).fill;
            const hl = all.filter(e => e.classList.contains('hl'));
            const plain = all.filter(e => !e.classList.contains('hl'));
            const isGray = c => { const m = c.match(/\\d+/g).map(Number);
                                  return Math.max(...m) - Math.min(...m) <= 8; };
            return {hl: hl.length, plain: plain.length,
                    plainGray: plain.every(e => isGray(fill(e))),
                    hlFill: hl.length ? fill(hl[0]) : null,
                    hlGray: hl.length ? isGray(fill(hl[0])) : null,
                    want: S.model.raw.ProjectPeriod.filter(r => hlToken(r.period_highlight)
                      && activeProjects().includes(r.project_id)).length}; }""")
        check(bands["plain"] > 0 and bands["plainGray"],
              "A PERIOD WITH NO HIGHLIGHT IS DRAWN GRAY - every one of them",
              f"{bands['plain']} band(s)")
        check(bands["hl"] == bands["want"] and bands["hl"] > 0 and bands["hlGray"] is False,
              "A PERIOD WITH A HIGHLIGHT IS DRAWN IN ITS COLOUR, and it is not gray",
              f"{bands['hl']} of {bands['want']} marked period(s), {bands['hlFill']}")
        leg = pg.evaluate("""() => [...document.querySelectorAll('#t-overall .legend li')]
            .map(l => l.textContent.trim())""")
        want = list(pg.evaluate("Object.values(S.model.perHlLabels)"))
        check(want and all(any(w in t and "period" in t for t in leg) for w in want),
              "the legend names the period colour as the FILE names it", "; ".join(want))

        ppid = pg.evaluate("""S.model.raw.ProjectPeriod.find(r =>
            hlToken(r.period_highlight)).project_id""")
        pg.click("text=Source data (project)")
        pg.wait_for_timeout(1200)
        pg.evaluate("p => { S.selProj = p; renderAll(); showTab('t-proj'); }", ppid)
        pg.wait_for_timeout(1200)
        own = pg.evaluate("document.querySelectorAll('#t-proj rect.band.hl').length")
        check(own > 0, "THE PROJECT'S OWN TIMELINE DRAWS IT TOO", f"{own} on {ppid}")
        cell = pg.evaluate("""() => {
            const td = document.querySelector(
              "#t-proj td.cell[data-col='period_highlight'][data-hl]");
            return td ? {hl: td.dataset.hl, text: td.textContent} : null; }""")
        check(cell and cell["hl"] and "Highlight" in cell["text"],
              "the Periods table has the Highlight column, with the colour in the cell",
              str(cell))
        offered = pg.evaluate("""() => (S.model.lists.period_highlight || []).length""")
        check(offered == 5, "and the five colours to choose from, from the Lists sheet",
              f"{offered} value(s)")

        # Choosing a colour through the cell, as a user would, recolours the band.
        row = pg.evaluate("""p => S.model.raw.ProjectPeriod.find(r => r.project_id === p
            && !hlToken(r.period_highlight)).__row""", ppid)
        td = pg.locator(f"#t-proj td.cell[data-col='period_highlight'][data-row='{row}']")
        td.click()
        pg.wait_for_timeout(300)
        pg.keyboard.press("Control+A")
        pg.keyboard.type("Highlight (Red)")
        pg.keyboard.press("Escape")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(1000)
        red = pg.evaluate("document.querySelectorAll('#t-proj rect.band.hl-red').length")
        check(red == 1, "TYPING A COLOUR INTO THE CELL RECOLOURS THAT PERIOD at once",
              f"{red} red band(s)")
        figs = pg.evaluate("""() => { const o = {}; for (const [k, v] of S.calc.projMonth)
            o[k] = v; return o; }""")
        pg.evaluate("""p => { for (const r of S.model.raw.ProjectPeriod) r.period_highlight = null;
            rebuild(true); renderKeepingTab(); }""", ppid)
        pg.wait_for_timeout(600)
        after = pg.evaluate("""() => { const o = {}; for (const [k, v] of S.calc.projMonth)
            o[k] = v; return o; }""")
        check(figs == after, "a highlight moves no figure", f"{len(figs)} project-months")
        bad = pg.evaluate("""() => {
            const r = S.model.raw.ProjectPeriod.find(x => x.period_name);
            r.period_highlight = 'Highlite (Purpel)';
            rebuild(true); renderKeepingTab();
            return S.model.findings.filter(f => f.rule === 'V-38').length; }""")
        check(bad == 1, "A VALUE NAMING NO COLOUR IS REPORTED (V-38), and the period stays gray",
              f"{bad} finding(s)")

        # ---- 8. default colours from General assumptions (schema 15, R-60) ------
        print("\nperiod colours as an assumption - and a project's own choice wins")
        load(pg, DUMMY)
        pg.click('button[role=tab][data-tab="t-overall"]')
        pg.wait_for_timeout(700)
        TL = "#t-overall .panel[data-panel=\"timeline\"] rect.band"
        # What every band SHOULD be, worked out from the rows rather than from the code
        # that draws them: the project's own colour, else the default, else gray.
        # Keyed by project and period name (the band carries both as data-s2 / data-s),
        # because the chart orders its rows by type and date and the model does not.
        expect = """() => {
            const def = {};
            for (const r of S.model.raw.PeriodHighlight)
              if (r.period_name && !(r.period_name in def)) def[r.period_name] = hlToken(r.period_highlight);
            const out = {};
            for (const p of activeProjects()) for (const s of (S.model.periods[p] || [])){
              if (!s.period_start || !s.period_end) continue;
              out[p + '|' + s.period_name] = hlToken(s.period_highlight) || def[s.period_name] || "";
            }
            return out; }"""
        drawn = """(sel) => Object.fromEntries([...document.querySelectorAll(sel)].map(e =>
            [e.dataset.s2 + '|' + e.dataset.s,
             ([...e.classList].find(c => c.startsWith('hl-')) || '').slice(3)]))"""
        want, got = pg.evaluate(expect), pg.evaluate(drawn, TL)
        check(want and got == want and len(set(want.values())) > 2,
              "EVERY BAND TAKES ITS PROJECT'S COLOUR, ELSE THE DEFAULT FOR ITS PERIOD NAME, "
              "ELSE GRAY", f"{len(got)} band(s): " + ", ".join(sorted(set(got.values()) - {''})))
        own = pg.evaluate("""() => { const r = S.model.raw.ProjectPeriod.find(x =>
            hlToken(x.period_highlight) && S.model.periodHl[x.period_name]
            && hlToken(x.period_highlight) !== S.model.periodHl[x.period_name]);
            return r ? [r.project_id, r.period_name, hlToken(r.period_highlight),
                        S.model.periodHl[r.period_name]] : null; }""")
        check(own and got.get(own[0] + "|" + own[1]) == own[2],
              "a project's own colour beats the default for its period",
              f"{own[0]} {own[1]}: {own[2]} over the default {own[3]}" if own else "none in fixture")

        # Edited on the General assumptions tab, through the cell, as a user would.
        pg.click("text=General assumptions")
        pg.wait_for_timeout(900)
        row = pg.evaluate("""() => S.model.raw.PeriodHighlight.find(r =>
            r.period_name === 'Start-up').__row""")
        td = pg.locator(f"#t-gen td.cell[data-sheet='PeriodHighlight'][data-col='period_highlight']"
                        f"[data-row='{row}']")
        td.click()
        pg.wait_for_timeout(300)
        pg.keyboard.press("Control+A")
        pg.keyboard.type("Highlight (Yellow)")
        pg.keyboard.press("Escape")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(1000)
        pg.click('button[role=tab][data-tab="t-overall"]')
        pg.wait_for_timeout(900)
        got = pg.evaluate(drawn, TL)
        su = {k: v for k, v in got.items() if k.endswith("|Start-up")}
        own_su = pg.evaluate("""() => S.model.raw.ProjectPeriod.filter(r =>
            r.period_name === 'Start-up' && hlToken(r.period_highlight)).length""")
        check(pg.evaluate(expect) == got and su
              and sum(v == "yellow" for v in su.values()) == len(su) - own_su,
              "CHANGING A DEFAULT ON GENERAL ASSUMPTIONS RECOLOURS THAT PERIOD ON EVERY PROJECT "
              "that has not chosen its own",
              f"{sum(v == 'yellow' for v in su.values())} of {len(su)} Start-up band(s) now yellow")

        # A trial whose periods are DERIVED has no rows to hold a colour - the default
        # still reaches it, which is the case the project-level column could not cover.
        der = pg.evaluate("""() => {
            const p = activeProjects().find(x => CLINICAL_TYPES.has(S.model.projects[x].project_type));
            S.model.raw.ProjectPeriod = S.model.raw.ProjectPeriod.filter(r => r.project_id !== p);
            rebuild(true); renderKeepingTab();
            const segs = S.model.periods[p] || [];
            return {p, derived: segs.length > 0 && segs.every(s => s.__derived)}; }""")
        pg.wait_for_timeout(700)
        want, got = pg.evaluate(expect), pg.evaluate(drawn, TL)
        check(der["derived"] and got == want,
              "periods DERIVED from milestones take the default colours too",
              f"{der['p']} now derived")

        bad = pg.evaluate("""() => {
            S.model.raw.PeriodHighlight.push({__row: 9001, period_name: 'Start-up',
                                              period_highlight: 'Highlight (Blue)', note_1: null},
                                             {__row: 9002, period_name: 'Lunch',
                                              period_highlight: 'Highlight (Red)', note_1: null},
                                             {__row: 9003, period_name: 'Close',
                                              period_highlight: 'Purpel', note_1: null});
            rebuild(true); renderKeepingTab();
            return S.model.findings.filter(f => f.rule === 'V-39').map(f => f.msg); }""")
        kinds = [any("more than one" in m and "Start-up" in m for m in bad),
                 any("not a period name" in m and "Lunch" in m for m in bad),
                 any("names no colour" in m and "Purpel" in m for m in bad)]
        check(all(kinds),
              "V-39 REPORTS A DEFAULT THAT CANNOT BE APPLIED - a name given twice, a name "
              "neither period list knows, a value naming no colour", f"{len(bad)} finding(s)")

        # An older workbook - schema 14, no PeriodHighlight sheet - still opens.
        older = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.12.xlsx"
        if older.exists():
            load(pg, older)
            st = pg.evaluate("""() => ({rows: S.model.raw.PeriodHighlight.length,
                fatal: S.model.findings.filter(f => f.sev === 'fatal').length,
                v09: S.model.findings.some(f => f.rule === 'V-09' && f.sheet === 'PeriodHighlight')})""")
            check(st["rows"] == 0 and st["fatal"] == 0 and st["v09"],
                  "A WORKBOOK FROM BEFORE SCHEMA 15 STILL OPENS - no defaults, said once as "
                  "information, nothing refused", str(st))
        blank = pg.evaluate("""() => { const s = blankSheets();
            return s.PeriodHighlight.slice(1).filter(r => r[1]).length; }""")
        check(blank >= 4, "a plan started blank arrives with the same default colours",
              f"{blank} coloured default(s)")

        check(not errors, "no script error anywhere in the run", "; ".join(errors[:3]))
        b.close()

    print(f"\nFAILURES: {', '.join(fails) if fails else 'none'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
