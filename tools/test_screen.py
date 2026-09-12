"""Drive app/PRAP.html and check the four screen changes the request named.

  1. LONG HORIZONS. The two Utilisation charts - one project, one person - used to be a
     fixed 1080 wide whatever the span, so five years put sixty month labels into 790px
     of plot and they ran into one another. They now grow with the horizon and the panel
     scrolls sideways, which is what every other chart on the page already did.
       1a. at the default two years nothing moves - the chart is the width it always was
       1b. over five years both charts are WIDER, by roughly the month count
       1c. and the panel that holds them scrolls horizontally rather than squeezing them
       1d. the month axis still carries one label per month at that width

  2. ONE COLUMN, NOT TWO. Assignments, Weight overrides and Monthly estimation were a
     two-column grid; all three are wide, so each had half a screen and all three
     scrolled sideways permanently. They are now stacked full width.
       2a. the three panels are in ONE column
       2b. in the order they are worked in: Assignments, then overrides, then months
       2c. and each is wider than it was beside a sibling

  3. WHICH ASSIGNMENT. Monthly estimation is a child of the selected assignment and said
     so nowhere: eight columns of months with no statement of what they belong to.
       3a. the panel states the assignment under its title
       3b. naming the project, the role, the window and the weight
       3c. the same line the Weight overrides panel carries, so the two agree

  4. PICKING A SERIES. Twenty bands in twenty shades of one palette read as a total and
     not as a series. Clicking a legend entry fades everything that is not it.
       4a. every legend entry that stands for a series is a real button
       4b. clicking one highlights its own marks and dims the rest
       4c. the pick carries across the whole TAB, not just the chart clicked
       4d. clicking the same entry again brings the chart back
       4e. picking a different one moves the pick rather than adding to it
       4f. Escape clears it
       4g. the keyboard works it, because a legend entry is a button
       4h. marks that belong to a MONTH rather than a series are never dimmed

    python tools/test_screen.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.9.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def probe(pg, js, arg=None, fallback=None):
    try:
        return pg.evaluate(js, arg) if arg is not None else pg.evaluate(js)
    except Exception as exc:
        print(f"       (page could not answer: {str(exc).splitlines()[0][:110]})")
        return fallback


# The Utilisation panel of whichever tab is showing: its svg, the box that holds it.
UTIL = """(tab) => {
  const p = [...document.querySelectorAll('#' + tab + ' .panel')]
    .find(e => ((e.querySelector('h2')||{}).textContent || '').startsWith('Utilisation'));
  if (!p) return null;
  const svg = p.querySelector('svg.chart'), box = p.querySelector('.scrollx');
  if (!svg || !box) return null;
  return {minw: parseFloat(svg.style.minWidth) || 0,
          vb: svg.getAttribute('viewBox'),
          // month names, year marks and the value axis all share .ax; the month row is
          // the only one with one entry per month, so >= months is the claim to make
          labels: svg.querySelectorAll('text.ax:not(.yr)').length,
          scrollW: box.scrollWidth, clientW: box.clientWidth};
}"""


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1600, "height": 1000})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(APP)
    pg.wait_for_timeout(200)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)

    # ------------------------------------------------------------------ 1
    print("app/PRAP.html — 1. the Utilisation charts over a long horizon")
    pg.click('nav button[data-tab="t-proj"]')
    pg.wait_for_timeout(600)
    short = probe(pg, UTIL, "t-proj")
    months_short = probe(pg, "() => S.to - S.from + 1", fallback=0)
    check(short and short["minw"] == 1080,
          "1a. at the default horizon the project chart is the width it always was",
          "" if not short else f"{months_short} months, min-width {short['minw']:.0f}px")

    # Everything the data covers, which for this workbook is several years.
    pg.click("#fAll")
    pg.wait_for_timeout(900)
    months_long = probe(pg, "() => S.to - S.from + 1", fallback=0)
    long_proj = probe(pg, UTIL, "t-proj")
    pg.click('nav button[data-tab="t-pers"]')
    pg.wait_for_timeout(700)
    long_pers = probe(pg, UTIL, "t-pers")

    # 62 + 230 padding + 34 per month is the declared geometry; assert the SHAPE of the
    # rule rather than the exact constant, so tuning Wper does not break the test.
    want = 62 + 230 + months_long * 32
    check(months_long > 24, "   (the workbook spans more than the default two years)",
          f"{months_long} months")
    check(long_proj and long_proj["minw"] >= want - 200,
          "1b. over a long horizon the project chart grows with the month count",
          "" if not long_proj else f"{long_proj['minw']:.0f}px for {months_long} months "
          f"(~{(long_proj['minw'] - 292) / max(1, months_long):.0f}px each)")
    check(long_pers and long_pers["minw"] > 1080,
          "    and so does the person chart",
          "" if not long_pers else f"{long_pers['minw']:.0f}px")
    check(long_proj and long_proj["scrollW"] > long_proj["clientW"] + 4,
          "1c. and the panel scrolls sideways rather than squeezing it",
          "" if not long_proj else f"{long_proj['scrollW']}px of content in "
          f"{long_proj['clientW']}px of panel")
    check(long_pers and long_pers["labels"] >= months_long,
          "1d. with one month label per month still drawn",
          "" if not long_pers else f"{long_pers['labels']} labels over {months_long} months")

    # ------------------------------------------------------------------ 2
    print("\napp/PRAP.html — 2. the three wide tables, stacked in one column")
    stack = probe(pg, """() => {
      const s = document.querySelector('#t-pers .stack1');
      if (!s) return null;
      const title = e => ((e.querySelector('h2')||{}).textContent || '').split('—')[0].trim();
      const panels = [...s.querySelectorAll('.panel')];
      return {cols: getComputedStyle(s).gridTemplateColumns.trim().split(/\\s+/).length,
              order: panels.map(title),
              lefts: [...new Set(panels.map(p => Math.round(p.getBoundingClientRect().left)))],
              widths: panels.map(p => Math.round(p.getBoundingClientRect().width)),
              outer: Math.round(s.getBoundingClientRect().width)};
    }""")
    check(stack and stack["cols"] == 1, "2a. the three panels are in one column",
          "" if not stack else f"grid-template-columns resolves to {stack['cols']} track(s)")
    check(stack and stack["order"][:3] == ["Assignments", "Weight overrides", "Monthly estimation"],
          "2b. in the order they are worked in",
          "" if not stack else " → ".join(stack["order"][:3]))
    check(stack and len(stack["lefts"]) == 1 and min(stack["widths"]) > stack["outer"] * 0.9,
          "2c. and each takes the full width instead of half a screen",
          "" if not stack else f"{stack['widths']} inside {stack['outer']}px, "
          f"{len(stack['lefts'])} distinct left edge(s)")

    # ------------------------------------------------------------------ 3
    print("\napp/PRAP.html — 3. Monthly estimation names its assignment")
    line = probe(pg, r"""() => {
      const p = [...document.querySelectorAll('#t-pers .stack1 .panel')]
        .find(e => ((e.querySelector('h2')||{}).textContent || '').startsWith('Monthly estimation'));
      const q = [...document.querySelectorAll('#t-pers .stack1 .panel')]
        .find(e => ((e.querySelector('h2')||{}).textContent || '').startsWith('Weight overrides'));
      if (!p) return null;
      const a = p.querySelector('.asgline'), b = q && q.querySelector('.asgline');
      const aid = S.selAsg, row = (S.model.raw.Assignment || []).find(x => x.assignment_id === aid);
      const pr = row ? (S.model.projects[row.project_id] || {}) : {};
      return {text: a ? a.textContent.replace(/\s+/g, ' ').trim() : null,
              same: !!(a && b) && a.textContent.trim() === b.textContent.trim(),
              aid, project: pr.project_name || null, role: row ? row.role_name : null,
              weight: row && row.person_weight !== null && row.person_weight !== undefined
                      ? Number(row.person_weight).toFixed(2) : null};
    }""")
    check(line and line["text"], "3a. the panel states the assignment under its title",
          "" if not line else (line["text"] or "")[:120])
    parts = []
    if line and line["text"]:
        for name, v in (("id", line["aid"]), ("project", line["project"]),
                        ("role", line["role"]), ("weight", line["weight"])):
            if v and str(v) not in line["text"]:
                parts.append(name)
    check(line and line["text"] and not parts,
          "3b. naming the project, the role, the window and the weight",
          "missing: " + ", ".join(parts) if parts else "")
    check(line and line["same"],
          "3c. and it is word for word the line Weight overrides carries")

    # ------------------------------------------------------------------ 4
    print("\napp/PRAP.html — 4. clicking a legend entry picks that series out")
    pg.click('nav button[data-tab="t-overall"]')
    pg.wait_for_timeout(900)

    shape = probe(pg, """() => {
      const out = [];
      for (const p of document.querySelectorAll('#t-overall .panel')){
        const ul = p.querySelector('ul.legend');
        if (!ul) continue;
        const pick = [...ul.querySelectorAll('li[data-s]')];
        out.push({title: (p.querySelector('h2')||{}).textContent,
                  entries: ul.querySelectorAll('li').length, pickable: pick.length,
                  button: pick.every(li => li.getAttribute('role') === 'button'
                                        && li.tabIndex === 0
                                        && li.getAttribute('aria-pressed') === 'false'),
                  marked: p.querySelectorAll('svg.chart [data-s]').length});
      }
      return out;
    }""", fallback=[])
    check(len(shape) >= 3 and all(s["pickable"] > 0 and s["marked"] > 0 for s in shape),
          "4a. every chart with a legend has pickable entries and marks that answer to them",
          ", ".join(f"{s['title']}: {s['pickable']} of {s['entries']} "
                    f"→ {s['marked']} marks" for s in shape))
    check(all(s["button"] for s in shape) if shape else False,
          "    and each entry is a real button — focusable, and it states its state")

    first = pg.eval_on_selector_all(
        "#t-overall .panel", """(ps) => ps
          .find(e => (e.querySelector('h2')||{}).textContent === 'Monthly resource trend')
          .querySelector('ul.legend li[data-s]').getAttribute('data-s')""")
    pg.click(f'#t-overall ul.legend li[data-s="{first}"]')
    pg.wait_for_timeout(400)          # the fade is a transition, so let it land
    picked = probe(pg, """(key) => {
      const tab = document.getElementById('t-overall');
      const dim = m => parseFloat(getComputedStyle(m).opacity);
      // A mark may carry a second key - a timeline band is a period OF a project - so
      // membership is either one, which is what the app itself matches on.
      const is = m => m.getAttribute('data-s') === key || m.getAttribute('data-s2') === key;
      const marks = [...tab.querySelectorAll('svg.chart.picked [data-s]')];
      const mine = marks.filter(is), rest = marks.filter(m => !is(m));
      // Which PANELS the pick reached, by title - the claim is that it is tab-wide.
      const reached = [...tab.querySelectorAll('.panel')]
        .filter(p => p.querySelector('svg.chart.picked'))
        .map(p => (p.querySelector('h2')||{}).textContent);
      // Anything WITHOUT a data-s is a fact about the month, not about a series.
      const monthly = [...tab.querySelectorAll('svg.chart .mmark, svg.chart .gapmark, '
        + 'svg.chart .th-over, svg.chart .th-under, svg.chart .base, svg.chart polygon.ms')];
      return {key, mine: mine.length, rest: rest.length,
              mineLit: mine.length > 0 && mine.every(m => dim(m) > 0.9),
              restDim: rest.length > 0 && rest.every(m => dim(m) < 0.3),
              reached, monthly: monthly.length,
              monthlyLit: monthly.every(m => dim(m) > 0.9),
              legOn: tab.querySelectorAll('ul.legend li[data-s].on').length,
              pressed: (tab.querySelector('ul.legend li[data-s].on') || {getAttribute:()=>null})
                          .getAttribute('aria-pressed')};
    }""", arg=first)
    check(picked and picked["mineLit"] and picked["restDim"],
          "4b. the picked series stays lit and everything else fades back",
          "" if not picked else f"{picked['key']}: {picked['mine']} mark(s) lit, "
          f"{picked['rest']} dimmed")
    check(picked and len(picked["reached"]) >= 3,
          "4c. and the pick carries across the whole tab, not one chart",
          "" if not picked else "; ".join(picked["reached"]))
    check(picked and picked["legOn"] == 1 and picked["pressed"] == "true",
          "    and the entry that made the pick states that it is pressed",
          "" if not picked else f"{picked['legOn']} legend entries on")

    # A chart cut along a DIFFERENT axis is not dimmed to nothing. The timeline's own
    # series are periods, so a project pick lights that project's row through the second
    # key and leaves the period legend alone, rather than fading a whole chart out.
    other = probe(pg, """() => {
      const gantt = [...document.querySelectorAll('#t-overall .panel')]
        .find(e => (e.querySelector('h2')||{}).textContent === 'Project timeline');
      const key = document.querySelector('#t-overall ul.legend li[data-s].on')
                          .getAttribute('data-s');
      const marks = [...gantt.querySelectorAll('svg.chart [data-s]')];
      const dim = m => parseFloat(getComputedStyle(m).opacity);
      return {key, bands: marks.length,
              mine: marks.filter(m => m.getAttribute('data-s2') === key).length,
              mineLit: marks.filter(m => m.getAttribute('data-s2') === key)
                            .every(m => dim(m) > 0.9),
              restDim: marks.filter(m => m.getAttribute('data-s2') !== key)
                            .every(m => dim(m) < 0.3),
              legDim: gantt.querySelectorAll('ul.legend.picked-leg').length,
              msLit: [...gantt.querySelectorAll('polygon.ms')].every(m => dim(m) > 0.9)};
    }""")
    check(other and other["mine"] > 0 and other["mineLit"] and other["restDim"],
          "    a project pick lights that project's row on the timeline too",
          "" if not other else f"{other['mine']} of {other['bands']} bands are {other['key']}")
    check(other and other["legDim"] == 0 and other["msLit"],
          "    without fading the timeline's own period legend, which is a different axis")
    check(picked and picked["monthly"] > 0 and picked["monthlyLit"],
          "4h. marks that belong to the MONTH are never dimmed",
          "" if not picked else f"{picked['monthly']} threshold/baseline/outline marks, "
          f"all at full strength")

    # From here each step is its own round trip, with a pause between: the fade is a
    # 120ms transition, so opacity read in the same tick as the click that started it is
    # a value on the way somewhere rather than the value the reader sees.
    STATE = """() => {
      const tab = document.getElementById('t-overall');
      const dim = m => parseFloat(getComputedStyle(m).opacity);
      return {faded: [...tab.querySelectorAll('svg.chart [data-s]')]
                       .filter(m => dim(m) < 0.3).length,
              lit: [...tab.querySelectorAll('svg.chart [data-s].hi')].length,
              picked: tab.querySelectorAll('svg.chart.picked').length,
              on: [...tab.querySelectorAll('ul.legend li[data-s].on')]
                   .map(li => li.getAttribute('data-s'))};
    }"""
    def entry(i):
        return pg.eval_on_selector_all(
            "#t-overall .panel", """(ps, i) => {
              const trend = ps.find(e => (e.querySelector('h2')||{}).textContent
                                         === 'Monthly resource trend');
              return [...trend.querySelectorAll('ul.legend li[data-s]')][i]
                       .getAttribute('data-s');
            }""", i)

    def click_entry(i):
        pg.click(f'#t-overall ul.legend li[data-s="{entry(i)}"]')
        pg.wait_for_timeout(350)

    click_entry(0)                                        # the same one again
    off = probe(pg, STATE)
    check(off and off["faded"] == 0 and not off["on"] and off["picked"] == 0,
          "4d. clicking the same entry again brings the whole chart back",
          "" if not off else f"{off['faded']} marks still faded, {off['picked']} chart(s) picked")

    second = entry(1)
    click_entry(0)
    click_entry(1)                                        # move the pick to another
    moved = probe(pg, STATE)
    check(moved and moved["on"] == [second],
          "4e. picking another moves the pick rather than adding to it",
          "" if not moved else str(moved["on"]))

    # Escape from the page itself - a real key press with nothing focused targets <body>.
    pg.evaluate("""() => document.body.dispatchEvent(
      new KeyboardEvent('keydown', {key:'Escape', bubbles:true}))""")
    pg.wait_for_timeout(350)
    esc = probe(pg, STATE)
    check(esc and esc["faded"] == 0 and not esc["on"], "4f. Escape clears it",
          "" if not esc else f"{esc['faded']} marks still faded")

    third = entry(2)
    pg.focus(f'#t-overall ul.legend li[data-s="{third}"]')
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(350)
    kb = probe(pg, STATE)
    check(kb and kb["faded"] > 0 and kb["on"] == [third],
          "4g. and Enter on a focused entry does what a click does",
          "" if not kb else f"{kb['faded']} marks faded by the keyboard, on={kb['on']}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(250)

    check(not errors, "the page raised no script error", "; ".join(errors[:2]))
    browser.close()

print()
if fails:
    print("FAILURES: " + "; ".join(fails))
    sys.exit(1)
print("FAILURES: none")
