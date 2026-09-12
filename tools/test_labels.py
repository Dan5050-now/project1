"""Drive app/PRAP.html and check every table heading says what the column MEANS.

The tables have always shown the workbook's own column names, which is right - the
screen and the file are the same thing - and, on its own, not enough: `work_scope_type`,
`outsourcing_scope_det`, `absorbed_by` and `ref_id` read perfectly well to whoever wrote
the schema and not at all to the person filling the plan in. The meaning existed, in the
heading's pop-up, which is to say it was invisible to anyone who did not know to hover.

Each heading now carries both lines.

  1. every heading on every editable table leads with a plain name
  2. and still carries the column's own name under it, so the screen can be matched to
     the spreadsheet, quoted in a mail, or looked up in the specification
  3. the two are DIFFERENT - a label that is just the identifier again is an entry
     somebody forgot to write
  4. the plain name is real English: no underscores, not a bare lower-case token
  5. the map covers every column the workbook has, not only the ones on screen today
  6. and the pop-ups say it the same way - heading, cell and filter button alike, so it
     is learned once
  7. nothing that was clickable moved: the filter buttons are still in the headings
  8. and the identifier is still what the editing machinery writes back through

    python tools/test_labels.py
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


# Every heading of every editable table on the two source-data tabs, plus the assumptions
# tab - the row-actions column excepted, which is a control and not a field.
HEADS = """() => {
  const out = [];
  for (const t of document.querySelectorAll('table.data-t[data-sheet]'))
    for (const th of t.querySelectorAll('thead th')){
      if (th.classList.contains('ins')) continue;
      const lab = th.querySelector('.lab'), cid = th.querySelector('.cid');
      out.push({sheet: t.dataset.sheet,
                lab: lab ? lab.textContent.trim() : null,
                cid: cid ? cid.textContent.trim() : null,
                labFirst: !!(lab && cid) && !!(lab.compareDocumentPosition(cid) & 4),
                tip: th.getAttribute('data-tip') || '',
                fbtn: th.querySelectorAll('.fbtn').length});
    }
  return out;
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

    heads = []
    for tab in ("t-proj", "t-pers", "t-gen"):
        pg.click(f'nav button[data-tab="{tab}"]')
        pg.wait_for_timeout(700)
        heads += pg.evaluate(HEADS)

    print("app/PRAP.html — every heading says what the column means")
    missing = sorted({f"{h['sheet']}.{h['cid']}" for h in heads if not h["lab"]})
    check(heads and not missing, "1. every heading leads with a plain name",
          f"{len(heads)} headings over {len({h['sheet'] for h in heads})} sheets"
          if not missing else "no label: " + ", ".join(missing[:6]))
    nocid = [h for h in heads if not h["cid"]]
    check(heads and not nocid,
          "2. and carries the column's own name under it",
          "" if not nocid else f"{len(nocid)} heading(s) lost the identifier")
    check(all(h["labFirst"] for h in heads if h["lab"] and h["cid"]),
          "   with the plain name first — it is the one a reader reads")

    same = sorted({f"{h['sheet']}.{h['cid']}" for h in heads
                   if h["lab"] and h["cid"] and h["lab"] == h["cid"]})
    check(not same, "3. the label is never just the identifier again",
          ", ".join(same[:6]))
    ugly = sorted({h["lab"] for h in heads if h["lab"]
                   and ("_" in h["lab"] or h["lab"] == h["lab"].lower()
                        and h["lab"] not in ("note",))})
    check(not ugly, "4. and reads as English, not as a token", ", ".join(sorted(ugly)[:6]))

    # The map must cover the SCHEMA, not only the columns some tab happens to draw today.
    gaps = pg.evaluate("""() => {
      const out = [];
      for (const [sheet, cols] of Object.entries(SHEET_HEADERS))
        for (const c of cols) if (!COLUMN_LABEL[c]) out.push(sheet + '.' + c);
      // and the read-only columns the app adds beside the stored ones
      for (const c of ['standard_fte','automatic_fte','difference','period','sharers'])
        if (!COLUMN_LABEL[c]) out.push('(lookup).' + c);
      return out;
    }""")
    check(not gaps, "5. the map covers every column in the schema", ", ".join(gaps[:8]))

    # One head, said the same way everywhere it is said.
    tips = pg.evaluate("""() => {
      const t = document.querySelector('#t-pers table.data-t[data-sheet="Person"]');
      const th = [...t.querySelectorAll('thead th')]
        .find(x => (x.querySelector('.cid')||{}).textContent === 'capacity_fte');
      const i = [...t.querySelectorAll('thead th')].indexOf(th);
      const td = t.querySelector('tbody tr').querySelectorAll('td')[i];
      const fb = th.querySelector('.fbtn');
      return {head: th.getAttribute('data-tip') || '', cell: td.getAttribute('data-tip') || '',
              filt: fb ? fb.getAttribute('data-tip') || '' : '',
              col: td.getAttribute('data-col'), edit: td.isContentEditable};
    }""")
    want = "<b>Capacity in FTE</b> <span class=\"tr\">capacity_fte</span>"
    check(tips and tips["head"].startswith(want) and tips["cell"].startswith(want),
          "6. the heading and the cell say it the same way",
          "" if not tips else tips["cell"][:70])
    check(tips and (not tips["filt"] or "Capacity in FTE" in tips["filt"]
                    or "Filter" in tips["filt"]),
          "   and so does the filter button")
    check(all(h["fbtn"] <= 1 for h in heads)
          and any(h["fbtn"] == 1 for h in heads),
          "7. the filter buttons are still in the headings",
          f"{sum(h['fbtn'] for h in heads)} filter button(s)")
    check(tips and tips["col"] == "capacity_fte" and tips["edit"],
          "8. and the cell still writes back through the identifier",
          "" if not tips else f"data-col={tips['col']}, editable={tips['edit']}")

    check(not errors, "the page raised no script error", "; ".join(errors[:2]))
    browser.close()

print()
if fails:
    print("FAILURES: " + "; ".join(fails))
    sys.exit(1)
print("FAILURES: none")
