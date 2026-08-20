"""What a new row arrives with, and whether the reader can tell there is more to see.

Three things, all about the moment a row is inserted or a panel is looked at.

  1. IDENTIFIERS are allocated one past the highest already in the sheet, so a row added
     today sorts and reads as the newest: project_id, person_id, assignment_id, and
     milestone_seq - which counts within its own project, not across the file.

  2. WEIGHTS start at 1.00, because 1.00 is the neutral multiplier. An empty weight is
     not neutral: it reads as 0.00 in the calculation, so a row left alone would
     contribute nothing at all and nothing on screen would say so.
     Checked on ProjectPeriod.weight, Person.capacity_fte, Assignment.person_weight and
     PersonPeriodWeight.weight_override.

  3. A row carrying ONLY what the application filled in is still an empty row: Save does
     not promote it and Export refuses to write it, because the user has not actually
     entered anything.

  4. Every scroll region says which way there is more, on all four edges, without relying
     on the browser to draw a scrollbar - overlay scrollbars stay hidden until you are
     already scrolling, which is exactly when you no longer need telling.

    python tools/test_newrow.py
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.2.xlsx"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def insert(pg, pane, sheet):
    loc = f"{pane} .data-t[data-sheet='{sheet}']"
    pg.locator(f"{loc} button[data-ins]").last.click()
    pg.wait_for_timeout(900)
    return pg.evaluate("s => S.model.raw[s].find(r => r.__new) || null", sheet)


def tail_number(v):
    import re
    m = re.search(r"(\d+)$", str(v or ""))
    return int(m.group(1)) if m else None


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME)
    pg = browser.new_page(viewport={"width": 1500, "height": 950})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — what a new row starts with")
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)

    # ---- 1. identifiers, one past the highest -------------------------------
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1100)
    highest = pg.evaluate("Math.max(...S.model.raw.Project.map(r => "
                          "+String(r.project_id).replace(/\\D+/g, '')))")
    row = insert(pg, "#t-proj", "Project")
    check(row and tail_number(row["project_id"]) == highest + 1,
          "Projects: a new row is given the next project_id, one past the highest",
          f"highest was {highest}, allocated {row and row['project_id']}")

    pid = pg.evaluate("S.selProj")
    seqs = pg.evaluate("p => S.model.raw.Milestone.filter(r => r.project_id === p && !r.__new)"
                       ".map(r => r.milestone_seq)", pid)
    row = insert(pg, "#t-proj", "Milestone")
    check(row and row["milestone_seq"] == max(seqs) + 1 and row["project_id"] == pid,
          "Milestones: milestone_seq continues THIS project's numbering",
          f"{pid} had {sorted(seqs)}, allocated {row and row['milestone_seq']}")

    row = insert(pg, "#t-proj", "ProjectPeriod")
    check(row and row["weight"] == 1,
          "Periods: weight starts at the neutral 1.00", f"weight={row and row['weight']}")

    pg.click("text=Source data (person)")
    pg.wait_for_timeout(1100)
    highest = pg.evaluate("Math.max(...S.model.raw.Person.map(r => "
                          "+String(r.person_id).replace(/\\D+/g, '')))")
    row = insert(pg, "#t-pers", "Person")
    check(row and tail_number(row["person_id"]) == highest + 1 and row["capacity_fte"] == 1,
          "People: the next person_id, and capacity_fte at 1.00",
          f"highest was {highest}, allocated {row and row['person_id']} "
          f"with capacity {row and row['capacity_fte']}")

    highest = pg.evaluate("Math.max(...S.model.raw.Assignment.filter(r => !r.__new)"
                          ".map(r => +String(r.assignment_id).replace(/\\D+/g, '')))")
    row = insert(pg, "#t-pers", "Assignment")
    check(row and tail_number(row["assignment_id"]) == highest + 1 and row["person_weight"] == 1,
          "Assignments: the next assignment_id, and person_weight at 1.00",
          f"highest was {highest}, allocated {row and row['assignment_id']} "
          f"at weight {row and row['person_weight']}")

    row = insert(pg, "#t-pers", "PersonPeriodWeight")
    check(row and row["weight_override"] == 1,
          "Weight overrides: weight_override starts at 1.00",
          f"weight_override={row and row['weight_override']}")

    # ---- 3. a row of nothing but defaults is still empty ---------------------
    pg.click("#saveBtn")
    pg.wait_for_timeout(1600)
    left = pg.evaluate("REQUIRED_SHEETS.reduce((n, s) => "
                       "n + S.model.raw[s].filter(r => r.__new).length, 0)")
    check(left == 6,
          "Save does not promote a row that holds nothing but the supplied values",
          f"{left} row(s) still drafts")

    pg.click("#exportBtn")
    pg.wait_for_timeout(1200)
    banner = pg.inner_text("#banner")
    check("blocked" in banner.lower() and "supplied" in banner and "lost" in banner,
          "Export refuses them too, and says why", banner.strip()[:100])

    # ---- 4. the edge cue -----------------------------------------------------
    pg.goto(APP)
    pg.wait_for_timeout(300)
    pg.set_input_files("#picker", str(DUMMY))
    pg.wait_for_timeout(4500)
    pg.click("text=Source data (project)")
    pg.wait_for_timeout(1300)
    boxes = pg.evaluate("""() => [...document.querySelectorAll('#t-proj .scrollx')].map(b => ({
        x: b.scrollWidth - b.clientWidth, y: b.scrollHeight - b.clientHeight,
        cue: b.parentElement.className}))""")
    wrapped = all("cue" in b["cue"] for b in boxes)
    right = all(("r" in b["cue"].split()) == (b["x"] > 1) for b in boxes)
    down = all(("d" in b["cue"].split()) == (b["y"] > 1) for b in boxes)
    check(wrapped and right and down,
          "every scroll region is wrapped, and shades exactly the edges that have more",
          f"{len(boxes)} region(s); "
          + ", ".join(f"{b['x']}x{b['y']} -> {b['cue']}" for b in boxes if b["x"] or b["y"]))

    after = pg.evaluate("""() => {const b = document.querySelector(
        "#t-proj .data-t[data-sheet='Project']").closest('.scrollx');
        b.scrollLeft = b.scrollWidth - b.clientWidth;
        return b;}""")
    pg.wait_for_timeout(400)
    cls = pg.evaluate("""() => document.querySelector("#t-proj .data-t[data-sheet='Project']")
        .closest('.scrollx').parentElement.className.split(' ')""")
    check("l" in cls and "r" not in cls,
          "scrolled to the right edge, the shade moves to the left — it always means "
          "'more this way'", " ".join(cls))

    # A box with nothing hidden must not be decorated, or the cue means nothing. Only
    # the pane on screen is measured: a hidden one has no width, so every box in it
    # would look overflow-free whatever it really holds.
    quiet = pg.evaluate("""() => [...document.querySelectorAll('#t-proj .scrollx')]
        .filter(b => b.scrollWidth <= b.clientWidth + 1 && b.scrollHeight <= b.clientHeight + 1)
        .every(b => b.parentElement.className.trim() === 'cue')""")
    check(quiet, "a region with nothing hidden carries no shade at all")

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
