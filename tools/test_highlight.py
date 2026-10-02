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
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.11.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


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

        check(not errors, "no script error anywhere in the run", "; ".join(errors[:3]))
        b.close()

    print(f"\nFAILURES: {', '.join(fails) if fails else 'none'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
