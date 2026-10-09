"""The second export: the calculated figures, not the plan.

Two exports that must never be confused with each other. The SOURCE export is the plan
and its whole point is to come back; this one is the ANSWER, for a spreadsheet or a
report, and it deliberately does not round-trip.

What is checked, and why each one matters:

  * BOTH are on the export menu, described so the choice can be made without trying it.
  * The results file carries seven sheets, and the first one says it cannot be imported -
    because somebody will try, and finding out by losing a plan is the wrong way to learn.
  * IT ADDS UP. Every project-month and every person-month is EXACTLY the sum of its
    Detail rows, and the Summary total is exactly the sum of both. A workbook whose
    purpose is to be checked must survive being checked: add the column, get the total.
  * EVERY DETAIL ROW IS ITS OWN MULTIPLICATION - period weight x (factor / sharers) x
    person weight x coverage - so a reader who disagrees with a figure can see which of
    the four numbers they disagree with.
  * IT FOLLOWS THE SCREEN. Filter to one person and the file holds that person, with the
    filter named on the ReadMe, and the project totals fall to match. A file that
    silently held more than the screen would be the worse failure of the two.
  * The figures equal the independent Python reference, to rounding.
  * The source export still round-trips, and is untouched by any of this.

    python tools/test_results.py
"""

import calendar
import pathlib
import sys
from datetime import date, timedelta
import tempfile
from collections import defaultdict

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
FIX = ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.14.xlsx"
TMP = pathlib.Path(tempfile.mkdtemp(prefix="prap_results_"))

sys.path.insert(0, str(ROOT / "tools"))
import prap_io                                                       # noqa: E402

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


def sheet(wb, name):
    it = wb[name].iter_rows(values_only=True)
    hdr = next(it)
    return [dict(zip(hdr, r)) for r in it]


def export(pg, item, name):
    pg.click("#exportBtn")
    pg.wait_for_timeout(300)
    with pg.expect_download() as dl:
        pg.click(item)
    out = TMP / name
    dl.value.save_as(out)
    return out


with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=CHROME, downloads_path=str(TMP))
    ctx = browser.new_context(accept_downloads=True)
    pg = ctx.new_page()
    pg.set_viewport_size({"width": 1500, "height": 950})
    pg.set_default_timeout(25000)
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())

    print("app/PRAP.html — exporting the figures rather than the plan")
    pg.goto(APP)
    pg.wait_for_timeout(400)
    check(pg.eval_on_selector("#expMenu", "e => e.classList.contains('off')"),
          "with nothing loaded there is nothing to export, and the menu says so")

    pg.set_input_files("#picker", str(FIX))
    pg.wait_for_timeout(3500)
    pg.click("#exportBtn")
    pg.wait_for_timeout(400)
    items = pg.eval_on_selector_all(".expitem", "es => es.map(e => e.innerText)")
    # By what each item IS, not by how many there are. The menu gained the two change-log
    # exports at plan v2.44, and a count would have to be edited every time the menu
    # grows - which teaches whoever edits it to stop reading the assertion.
    plan_items = [t for t in items if "Source data" in t]
    figures = [t for t in items if "Calculated monthly FTE" in t]
    check(len(plan_items) == 2 and len(figures) == 1
          and any("Cannot be imported back" in t for t in figures),
          "THE MENU OFFERS BOTH, and says which one comes back and which does not",
          " | ".join(t.split("\n")[0] for t in items))
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(200)

    res = export(pg, "#exportCalcBtn", "calc.xlsx")
    check(res.name.endswith(".xlsx") and res.stat().st_size > 20000,
          "the calculated export downloads", f"{res.stat().st_size:,} bytes")

    wb = load_workbook(res)
    want = ["00_ReadMe", "Summary", "ProjectMonth", "PersonMonth", "Detail", "Flags",
            "Assumptions"]
    check(wb.sheetnames == want, "seven sheets, ReadMe first",
          ", ".join(wb.sheetnames))

    readme = " ".join(str(c.value or "") for r in wb["00_ReadMe"].iter_rows() for c in r)
    check("CANNOT be imported" in readme and "FTE  =  demand_fte" in readme
          and "V-12" in readme and "V-23" in readme,
          "the ReadMe says it cannot be imported, gives the formula, and names where a "
          "figure can be short of an assumption")

    detail = sheet(wb, "Detail")
    pmn = sheet(wb, "ProjectMonth")
    smn = sheet(wb, "PersonMonth")
    summ = sheet(wb, "Summary")

    # ---- it adds up -------------------------------------------------------------
    byproj, bypers = defaultdict(float), defaultdict(float)
    for r in detail:
        byproj[(r["month_iso"], r["project_id"])] += r["fte"]
        bypers[(r["month_iso"], r["person_id"])] += r["fte"]
    bad = [k for k, v in byproj.items()
           if abs(v - next((x["fte"] for x in pmn
                            if x["month_iso"] == k[0] and x["project_id"] == k[1]), 0)) > 1e-9]
    # Rows with no person on them (gap_dir 'unallocated', R-55) have no detail to sum.
    check(not bad and len(byproj) == sum(1 for r in pmn if r["gap_dir"] != "unallocated"),
          "EVERY PROJECT-MONTH IS EXACTLY THE SUM OF ITS DETAIL ROWS",
          f"{len(pmn)} project-months" + (f"; {len(bad)} differ" if bad else ""))
    bad = [k for k, v in bypers.items()
           if abs(v - next((x["fte"] for x in smn
                            if x["month_iso"] == k[0] and x["person_id"] == k[1]), 0)) > 1e-9]
    check(not bad and len(bypers) == sum(1 for r in smn if r["flag"] != "unassigned"),
          "and every person-month too",
          f"{len(smn)} person-months" + (f"; {len(bad)} differ" if bad else ""))

    td = sum(r["fte"] for r in detail)
    tp = sum(r["fte"] for r in pmn)
    ts = sum(r["fte"] for r in smn)
    tot = next(r["value"] for r in summ
               if r["measure"] == "Total demand" and r["unit"] == "FTE-months")
    check(max(abs(x - td) for x in (tp, ts, tot)) < 1e-9,
          "and all four totals in the file are the same number",
          f"detail {td:.4f}, project {tp:.4f}, person {ts:.4f}, summary {tot:.4f}")

    # ---- each row is its own multiplication ---------------------------------------
    # A row whose figure was STATED is deliberately not the product of its four terms -
    # that is what manual means. So the multiplication is checked against automatic_fte,
    # which every row carries: on an automatic row it IS the figure, and on a stated one
    # it is what the assumptions would have said. Checking it this way tests both the
    # arithmetic and the claim the file makes about which rows are which.
    def product(r):
        # REQ-CAL-19. The project-month IS its demand - standard x period weight x the
        # month it ran - and role_share is this person's slice of that. person_weight
        # and month_coverage are inside role_share now rather than multiplied after it,
        # which is what makes the shares add to one.
        return r["demand_fte"] * r["role_share"]

    auto = [r for r in detail if r["estimation"] == "automatic"]
    stated = [r for r in detail if r["estimation"] != "automatic"]
    # To the HUNDREDTH, not to fifteen places. Since REQ-CAL-20 a row's figure is its
    # demand times its share ROUNDED, and the month's hundredths are handed out by
    # largest remainder rather than each row rounding on its own - so a row takes either
    # its floor or its floor plus a hundredth, and sits up to a FULL hundredth off the
    # exact product. (Measured on the 62-project fixture: worst 0.0070.) What is exact is checked
    # immediately below: the rows of a project-month add to the demand with nothing
    # left over, which is the property the sheet is actually read for.
    bad = [r for r in detail if abs(product(r) - r["automatic_fte"]) > 0.01 + 1e-9]
    check(not bad,
          "EVERY DETAIL ROW IS ITS OWN TWO NUMBERS — demand x share to the hundredth, "
          "and both are on it without the application",
          f"{len(detail)} rows" + (f"; {len(bad)} do not reconcile" if bad else ""))

    # ---- and the shares of one project-month add to exactly one ---------------------
    grp = {}
    for r in detail:
        grp.setdefault((r["month_iso"], r["project_id"]), []).append(r)
    auto = [(k, v) for k, v in grp.items()
            if all(x["estimation"] == "automatic" for x in v)]
    bad = [k for k, v in auto if abs(sum(x["role_share"] for x in v) - 1) > 5e-4]
    check(auto and not bad,
          "THE SHARES OF A PROJECT-MONTH ADD TO EXACTLY ONE — which is what makes the "
          "month its demand however many people are on it",
          f"{len(auto)} automatic project-month(s)" + (f"; {len(bad)} differ" if bad else ""))
    bad = [k for k, v in auto
           if abs(sum(x["fte"] for x in v) - v[0]["demand_fte"]) > 5e-4]
    check(not bad,
          "AND THE PROJECT MONTH IS ITS DEMAND — standard_fte x period weight x month_run, "
          "not a figure the staffing quietly reduced",
          f"{len(auto)} checked" + (f"; {len(bad)} differ" if bad else ""))

    # ---- and the standard is what gives a figure its size --------------------------
    check(all(r["standard_fte"] is not None and r["standard_fte"] > 0 for r in detail)
          and max(r["standard_fte"] for r in detail) > 1.5,
          "THE STANDARD MONTHLY FTE IS ON EVERY ROW, and carries a real magnitude — the "
          "figure it produces is a quantity of work, not a relative shape",
          f"standard_fte ranges {min(r['standard_fte'] for r in detail):.2f} to "
          f"{max(r['standard_fte'] for r in detail):.2f} FTE")
    shared = [r for r in detail if r["sharers"] > 1]
    absorbed = [r for r in detail if r["absorbed_from"]]
    check(shared and all(r["role_factor_effective"] / r["sharers"] < r["role_factor_effective"]
                         for r in shared),
          "the working shows a shared role being divided",
          f"{len(shared)} row(s) with more than one holder")
    check(all(r["role_factor_effective"] > (r["role_factor"] or 0) for r in absorbed)
          if absorbed else True,
          "and an absorbed factor as larger than the role's own",
          f"{len(absorbed)} row(s) carrying an absorbed factor")

    # ---- against the reference ------------------------------------------------------
    M = prap_io.Model(prap_io.read_xlsx(FIX))
    C = prap_io.calculate(M)
    ref = defaultdict(float)
    for (sid, k), v in C["pers_month"].items():
        ref[(f"{k // 12}-{(k % 12) + 1:02d}", sid)] += v
    worst = max(abs(v - ref.get(k, 0)) for k, v in bypers.items())
    check(worst < 1e-3,
          "and the figures are the Python reference implementation's, to rounding",
          f"{len(bypers)} person-months, worst difference {worst:.2e}")

    # ---- it follows the screen ------------------------------------------------------
    who = smn[0]["person_id"]
    pg.evaluate("""(sid) => { S.f.pers = new Set([sid]); fillFilters(); renderAll();
                              showTab(S.tab); }""", who)
    pg.wait_for_timeout(900)
    res2 = export(pg, "#exportCalcBtn", "calc_filtered.xlsx")
    wb2 = load_workbook(res2)
    d2, s2 = sheet(wb2, "Detail"), sheet(wb2, "PersonMonth")
    rm2 = " ".join(str(c.value or "") for r in wb2["00_ReadMe"].iter_rows() for c in r)
    check(d2 and {r["person_id"] for r in d2} == {who}
          and {r["person_id"] for r in s2} == {who},
          "FILTER TO ONE PERSON AND THE FILE HOLDS THAT PERSON",
          f"{len(d2)} detail row(s), {len({r['person_id'] for r in d2})} person")
    check(f"Person: {who}" in rm2,
          "with the filter named on the ReadMe, so the file explains its own scope",
          next((str(c.value) for r in wb2["00_ReadMe"].iter_rows() for c in r
                if c.value and "Person:" in str(c.value)), "(not named)"))
    byproj2 = defaultdict(float)
    for r in d2:
        byproj2[(r["month_iso"], r["project_id"])] += r["fte"]
    p2 = sheet(wb2, "ProjectMonth")
    bad = [k for k, v in byproj2.items()
           if abs(v - next((x["fte"] for x in p2
                            if x["month_iso"] == k[0] and x["project_id"] == k[1]), 0)) > 1e-9]
    check(not bad,
          "and the project totals fall to match — they are not the unfiltered ones",
          f"{len(p2)} project-month(s), all equal to the rows beneath them")
    pg.evaluate("() => { S.f.pers = new Set(); fillFilters(); renderAll(); showTab(S.tab); }")
    pg.wait_for_timeout(700)

    # ---- the source export is untouched ---------------------------------------------
    src = export(pg, "#exportBtn2", "source.xlsx")
    back = prap_io.read_xlsx(src)
    check(len(back["Project"]) == 10 and len(back["Assignment"]) == 48
          and set(back) == set(prap_io.SHEET_ORDER),
          "THE SOURCE EXPORT STILL ROUND-TRIPS, with every sheet the reader expects",
          f"{sum(len(v) for v in back.values() if isinstance(v, list))} rows across "
          f"{len(back)} sheets")

    # ---- R-55: standard against staffed, on the file -----------------------------------
    # A plan with all three kinds in it. The fixture already has stated figures that
    # leave projects short and over their standard (V-34); taking every assignment off
    # one active project adds months nobody is on (V-36), which the file used to drop.
    print("\n  R-55 — what each project NEEDS beside what it is GIVEN")
    src2 = prap_io.read_xlsx(FIX)
    # One with no gap of its own, so removing it leaves the short and over months intact.
    gapped = {pid for (pid, _k) in prap_io.calculate(prap_io.Model(src2))["proj_gap"]}
    gone = next(p["project_id"] for p in src2["Project"]
                if str(p.get("status") or "") != "Completed" and p["project_id"] not in gapped
                and any(a["project_id"] == p["project_id"] for a in src2["Assignment"]))
    src2["Assignment"] = [a for a in src2["Assignment"] if a["project_id"] != gone]
    for sh in ("PersonPeriodWeight", "MonthlyEstimate"):
        if sh in src2:
            keep = {a["assignment_id"] for a in src2["Assignment"]}
            src2[sh] = [r for r in src2[sh]
                        if not r.get("assignment_id") or r["assignment_id"] in keep]
    # And two people whose employment does not cover the whole horizon - one leaving,
    # one joining - so "employed months only" has something to be wrong about.
    t = date.today()
    def month_end(n):
        y, m = divmod(t.month - 1 + n, 12)
        y += t.year
        return date(y, m + 1, calendar.monthrange(y, m + 1)[1])
    leaver, joiner = src2["Person"][-1], src2["Person"][-2]
    leaver["employment_end"] = month_end(3)
    joiner["employment_start"] = month_end(5) + timedelta(days=1)
    fix2 = TMP / "unstaffed.xlsx"
    prap_io.write_xlsx(src2, fix2)
    pg.set_input_files("#picker", str(fix2))
    pg.wait_for_timeout(3500)
    pg.evaluate("() => { S.f.pers = new Set(); fillFilters(); renderAll(); showTab(S.tab); }")
    pg.wait_for_timeout(500)
    view = set(pg.evaluate("() => grid().map(k => `${Math.floor(k/12)}-${String(k%12+1).padStart(2,'0')}`)"))
    inview = set(pg.evaluate("() => activeProjects()"))
    wb3 = load_workbook(export(pg, "#exportCalcBtn", "calc_gap.xlsx"))
    p3, f3, s3 = sheet(wb3, "ProjectMonth"), sheet(wb3, "Flags"), sheet(wb3, "Summary")
    rm3 = " ".join(str(c.value or "") for r in wb3["00_ReadMe"].iter_rows() for c in r)

    M3 = prap_io.Model(src2)
    C3 = prap_io.calculate(M3)
    want_gap = {(prap_io.iso_month(k), pid): g for (pid, k), g in C3["proj_gap"].items()
                if prap_io.iso_month(k) in view and pid in inview}
    want_un = {(prap_io.iso_month(k), pid): d for (pid, k), d in C3["proj_unallocated"].items()
               if prap_io.iso_month(k) in view and pid in inview}
    got = {(r["month_iso"], r["project_id"]): r for r in p3}

    check(all(k in p3[0] for k in ("demand_fte", "staffed_fte", "gap_fte", "gap_dir")),
          "PROJECTMONTH CARRIES demand_fte, staffed_fte, gap_fte AND gap_dir")
    bad = [k for k, r in got.items()
           if r["demand_fte"] is None
           or abs(r["staffed_fte"] - r["demand_fte"] - r["gap_fte"]) > 1e-9]
    check(not bad, "on every row the gap IS staffed minus demand",
          f"{len(got)} rows" + (f"; {len(bad)} do not" if bad else ""))
    bad = [k for k, r in got.items()
           if r["gap_dir"] != "unallocated" and abs(r["fte"] - r["staffed_fte"]) > 1e-9]
    check(not bad, "and unfiltered, the figure in view is the whole project's",
          f"{len(bad)} differ" if bad else "")

    have_gap = {k: r for k, r in got.items() if r["gap_dir"] in ("short", "over")}
    bad = [k for k in set(want_gap) | set(have_gap)
           if k not in want_gap or k not in have_gap
           or have_gap[k]["gap_dir"] != want_gap[k]["dir"]
           or abs(have_gap[k]["gap_fte"] - want_gap[k]["gap"]) > 1e-9]
    check(want_gap and not bad,
          "EVERY PROJECT-MONTH OFF ITS STANDARD IS ON THE FILE, short or over, with the "
          "gap the Python reference finds (V-34)",
          f"{len(want_gap)} project-month(s)" + (f"; {len(bad)} differ" if bad else ""))
    have_un = {k: r for k, r in got.items() if r["gap_dir"] == "unallocated"}
    bad = [k for k in set(want_un) | set(have_un)
           if k not in want_un or k not in have_un
           or abs(have_un[k]["demand_fte"] - want_un[k]) > 1e-9
           or have_un[k]["fte"] != 0 or have_un[k]["people"] != 0
           or abs(have_un[k]["gap_fte"] + want_un[k]) > 1e-9]
    check(want_un and not bad and any(k[1] == gone for k in have_un),
          "A MONTH NOBODY IS ON IS A ROW, with fte 0 and the whole demand as its gap — "
          "the largest shortfall is no longer the one the file cannot show (V-36)",
          f"{len(want_un)} month(s), {gone} among them" + (f"; {len(bad)} differ" if bad else ""))

    pflags = [r for r in f3 if r["project_id"]]
    for kind, dir_ in (("short of standard", "short"), ("over standard", "over"),
                       ("unallocated demand", "unallocated")):
        rows = [r for r in got.values() if r["gap_dir"] == dir_]
        fl = [r for r in pflags if r["kind"] == kind]
        check(rows and sum(r["months"] for r in fl) == len(rows)
              and abs(sum(r["fte"] for r in fl) - sum(abs(r["gap_fte"]) for r in rows)) < 1e-6,
              f"Flags '{kind}': its runs cover exactly the {dir_} months, and add to their gap",
              f"{len(fl)} run(s) over {len(rows)} month(s)")
    check(all(r["person_id"] is None for r in pflags)
          and all(r["project_id"] is None for r in f3 if r["person_id"]),
          "a flag names a person or a project, never both")
    summ3 = {(r["measure"], r["unit"]): r["value"] for r in s3}
    std = sum(r["demand_fte"] for r in got.values())
    check(abs(summ3[("Standard demand", "FTE-months")] - std) < 1e-6
          and summ3[("Short of standard", "project-months")]
          == sum(r["gap_dir"] == "short" for r in got.values())
          and summ3[("Unallocated demand", "project-months")] == len(have_un),
          "the Summary's project figures are ProjectMonth's, summed",
          f"standard demand {std:.2f} FTE-months")
    check("never add up demand_fte on Detail" in rm3 and "gap_fte" in rm3,
          "THE README WARNS AGAINST SUMMING demand_fte ON DETAIL, and defines the gap columns")

    # Filtered to one person, the gap is still the project's own - a project is not short
    # because the reader chose not to look at the rest of its people.
    who3 = next(r["person_id"] for r in sheet(wb3, "Detail")
                if (r["month_iso"], r["project_id"]) in have_gap)
    pg.evaluate("""(sid) => { S.f.pers = new Set([sid]); fillFilters(); renderAll();
                              showTab(S.tab); }""", who3)
    pg.wait_for_timeout(900)
    p4 = sheet(load_workbook(export(pg, "#exportCalcBtn", "calc_gap_one.xlsx")), "ProjectMonth")
    both = [(r, got[(r["month_iso"], r["project_id"])]) for r in p4
            if (r["month_iso"], r["project_id"]) in got and r["gap_dir"] != "unallocated"]
    check(both and all(a["gap_fte"] == b["gap_fte"] and a["staffed_fte"] == b["staffed_fte"]
                       for a, b in both)
          and any(a["fte"] < a["staffed_fte"] for a, _ in both),
          "FILTERED TO ONE PERSON, THE GAP IS STILL THE PROJECT'S — fte falls to their part, "
          "staffed_fte and gap_fte do not",
          f"{len(both)} project-month(s)")
    pg.evaluate("() => { S.f.pers = new Set(); fillFilters(); renderAll(); showTab(S.tab); }")
    pg.wait_for_timeout(500)

    # Spare capacity: a month somebody is employed and on nothing is a row, so the file
    # can say who is free as well as who is overloaded - and only while employed.
    s3m = sheet(wb3, "PersonMonth")
    idle = [r for r in s3m if r["flag"] == "unassigned"]
    det3 = {(r["month_iso"], r["person_id"]) for r in sheet(wb3, "Detail")}
    def employed(p, iso):
        y, m = map(int, iso.split("-"))
        first, last = date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])
        s_, e_ = p.get("employment_start"), p.get("employment_end")
        s_ = s_.date() if hasattr(s_, "date") else s_
        e_ = e_.date() if hasattr(e_, "date") else e_
        return not (s_ and s_ > last) and not (e_ and e_ < first)
    roster = {p["person_id"]: p for p in src2["Person"]}
    # Every month a person is employed, plus any month they carry work in whether or
    # not they are - an assignment past somebody's leaving date still produces figures,
    # and dropping them would hide exactly the month that needs fixing.
    want_rows = {(iso, sid) for sid in {r["person_id"] for r in s3m}
                 for iso in view if employed(roster[sid], iso)} | {
                (r["month_iso"], r["person_id"]) for r in s3m if r["flag"] != "unassigned"}
    have_rows = {(r["month_iso"], r["person_id"]) for r in s3m}
    gone_idle = [r for r in idle if not employed(roster[r["person_id"]], r["month_iso"])]
    check(idle and all(r["fte"] == 0 and r["projects"] == 0 for r in idle)
          and not any((r["month_iso"], r["person_id"]) in det3 for r in idle),
          "A MONTH SOMEBODY IS ON NOTHING IS A ROW — fte 0, flag 'unassigned', and no "
          "assignment behind it: the file now says who is free",
          f"{len(idle)} unassigned person-month(s)")
    check(have_rows == want_rows and not gone_idle
          and any(not employed(roster[leaver["person_id"]], iso) for iso in view)
          and any(not employed(roster[joiner["person_id"]], iso) for iso in view),
          "and exactly the months each person is EMPLOYED — nobody who has left is "
          "offered as spare capacity",
          f"{len(have_rows)} person-months" + (
              f"; {len(have_rows - want_rows)} extra, {len(want_rows - have_rows)} missing"
              if have_rows != want_rows else ""))

    check(not errors, "no uncaught errors in the page", "; ".join(errors[:2]))
    browser.close()

print(f"\nFAILURES: {'none' if not fails else len(fails)}")
for f in fails:
    print(f"  FAILED  {f}")
sys.exit(1 if fails else 0)
