/* ============================================== 6b. the calculated-results workbook

   A second thing the application can export, and the opposite of the first.

   The SOURCE export is the plan, and its whole purpose is to come back: it round-trips,
   the application reads it again, and nothing in it is derived. This one is the
   ANSWER - the monthly figures, for a spreadsheet, a report or somebody else's model -
   and it deliberately does not round-trip. Re-importing it would be meaningless, so the
   file says so on its first sheet rather than leaving somebody to find out.

   The point of separating them is that they answer different questions and are wrong
   in different ways. A source file with a derived column in it invites somebody to edit
   the derived column. A results file that pretends to be source data invites somebody
   to import it and lose their plan.

   WHAT IS IN IT. Everything the Overall tab shows, plus the working behind it:

     00_ReadMe      what this file is, what it is not, and the formula
     Summary        the tiles - projects, people, total demand, the flags
     ProjectMonth   one row per project per month
     PersonMonth    one row per person per month employed, against their capacity
     Detail         one row per ASSIGNMENT per month, with every term of the
                    multiplication that produced it
     Flags          the over-allocated months and under-allocated runs
     Assumptions    the settings in force when the figures were produced

   Detail is the sheet that makes the rest checkable: every figure on ProjectMonth and
   PersonMonth is a sum of its rows, and each of those rows carries the four numbers it
   was made from. Somebody who disagrees with a total can find out why without opening
   the application.

   Pure - it builds rows, and knows nothing about files or the DOM. Both shells export
   through it, so a figure cannot differ between them. */

const RESULT_SHEETS = ["00_ReadMe", "Summary", "ProjectMonth", "PersonMonth",
                       "Detail", "Flags", "Assumptions"];

/** Which settings changed the figures, as opposed to how they are displayed. */
const CFG_AFFECTS = {
  split_shared_role_fte:        "CHANGES FIGURES — a shared role's factor is divided",
  absorb_unstaffed_role_factor: "CHANGES FIGURES — an unstaffed role's factor is absorbed",
  over_allocation_fte:          "flags only — the over-allocation ceiling",
  under_allocation_fte:         "flags only — the under-allocation floor",
  under_allocation_min_months:  "flags only — months below the floor before a run",
  fte_hours_per_month:          "display only — FTE to hours",
  capacity_unit:                "display only",
  default_horizon_months:       "display only — the months the dashboard opens on",
  schema_version:               "the structure the source workbook was written to",
};

/** Build every sheet of the results workbook.
 *
 *  `scope` is what the user is looking at: the months, the projects and the people the
 *  Overall tab currently has in view, and the words describing any filter. The export
 *  follows the screen deliberately - somebody who has filtered to one department and
 *  presses export means that department - and the ReadMe says so in full, so a file
 *  that left the building can still explain what it does and does not cover.
 */
function buildResults(M, C, scope){
  const months = scope.months, mset = new Set(months);
  const projSet = new Set(scope.projects), persSet = new Set(scope.people);
  const HOURS = M.HOURS;
  const r4 = v => Math.round(v * 10000) / 10000;
  const r2 = v => Math.round(v * 100) / 100;
  const label = k => keyToLabel(k);
  const iso = k => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;

  // ---- Detail: one row per assignment per month, with its whole multiplication ----
  const detail = [["month", "month_iso", "project_id", "project_name", "project_type",
                   "clinical_phase", "work_scope_type", "period_name",
                   /* REQ-CAL-19: where the figure gets its SIZE. standard_fte is
                      the month's demand for a project of this type, phase and
                      scope; period_weight adjusts it for this study; role_share is
                      this person's slice of it, over the roles actually staffed. */
                   "standard_fte", "period_weight", "month_run", "demand_fte",
                   "period_weight_from", "role_share",
                   "person_id", "person_name", "department", "role_name",
                   "role_factor", "role_factor_effective", "absorbed_from",
                   "sharers", "person_weight", "person_weight_from",
                   "month_coverage", "fte", "hours", "assignment_id",
                   /* REQ-CAL-18. Four columns rather than one flag, because "this figure
                      was stated" is not the whole answer a reader needs: they need to
                      know at WHICH level it was stated - a project figure and an
                      assignment figure are different claims about different things -
                      what the assumptions would have said instead, and, where a project
                      total was shared out, the factor this person's share was multiplied
                      by. Without the last one a person whose figure moved has no way to
                      find out why, because nothing they own changed. */
                   "estimation", "automatic_fte", "project_manual_total", "project_scale"]];
  for (const L of C.lines){
    if (!mset.has(L.month) || !projSet.has(L.project_id) || !persSet.has(L.person_id)) continue;
    const p = M.projects[L.project_id] || {}, who = M.people[L.person_id] || {};
    detail.push([
      label(L.month), iso(L.month), L.project_id, p.project_name ?? null,
      p.project_type ?? null, p.clinical_phase ?? null, p.work_scope_type ?? null,
      L.period_name, r4(L.standard_fte ?? 1), r4(L.period_weight),
      r4(L.month_run ?? 1), r4(L.demand_fte ?? 0), L.period_weight_source,
      r4(L.role_share ?? 0),
      L.person_id, who.person_name ?? null, who.department ?? null, L.role_name,
      L.role_factor === undefined ? null : r4(L.role_factor),
      r4(L.role_factor_effective),
      L.absorbed.length ? L.absorbed.join(", ") : null,
      L.sharers, r4(L.person_weight), L.person_weight_source,
      r4(L.coverage), r4(L.fte), r2(L.fte * HOURS), L.assignment_id,
      L.source, r4(L.auto ?? 0),
      L.manual_project_total === undefined ? null : r4(L.manual_project_total),
      L.project_scale === undefined ? null : r4(L.project_scale),
    ]);
  }

  /* ---- the two monthly sheets, SUMMED FROM THE DETAIL ROWS ABOVE ----------------
     Not from the calculation's own totals, for two reasons, and the second one is a
     correctness matter rather than a tidiness one.

     Every figure in this file is rounded to four places. Add up a column of rounded
     numbers and you do not get the rounded total - so totals taken from the engine
     would sit a thousandth away from the rows they are supposed to be the sum of, and
     a reader who added the column would find the file disagreeing with itself. In a
     workbook whose entire purpose is to be checked, that is the wrong way round.

     And the engine's totals cover EVERY assignment, while this file covers what is in
     view. Filter to one department and a project-month taken from the engine would
     still carry the people the filter removed - a total larger than the rows beneath
     it, with nothing to say why. Summing the detail cannot make that mistake. */
  const pAcc = new Map(), sAcc = new Map();
  const bump = (map, key, fte, other) => {
    let e = map.get(key);
    if (!e) map.set(key, e = {fte:0, others:new Set()});
    e.fte += fte;
    e.others.add(other);
  };
  /* By NAME, not by position. These were hard-coded indices into the header above,
     which is fine until the header grows - and REQ-CAL-19 grew it by four columns in the
     middle, silently turning `fte` into `person_weight`. A totals sheet built from the
     wrong column is the one defect this file exists to make impossible, so the column
     numbers are read from the header rather than counted by hand. */
  const col = Object.fromEntries(detail[0].map((h, i) => [h, i]));
  for (const row of detail.slice(1)){
    const k = row[col.month_iso], pid = row[col.project_id];
    const sid = row[col.person_id], fte = row[col.fte];
    bump(pAcc, k + "|" + pid, fte, sid);
    bump(sAcc, k + "|" + sid, fte, pid);
  }

  /* ---- STANDARD AGAINST STAFFED, on the same row (R-55) ---------------------------
     The figures above say what each project is GIVEN. Without what it NEEDS beside
     them, the file cannot answer the first question anybody analysing it asks - which
     projects are short - and the obvious way to get it from Detail is a trap: demand_fte
     is repeated on every person's row, so adding it up multiplies a project's demand by
     its headcount. So the project's own figures are put here, once per project-month,
     taken from the calculation rather than recomputed:

       demand_fte    what the project's standard asks for that month (REQ-CAL-19)
       staffed_fte   what its people are given in all, WHOLE PROJECT, whatever the filter
       gap_fte       staffed_fte - demand_fte: negative is short, positive is over
       gap_dir       short / over / unallocated, or empty where they agree

     staffed_fte is the WHOLE project's and fte is the part of it in view. Unfiltered
     they are the same number; filtered to one department they are not, and the gap has
     to be the project's real gap rather than one invented by the filter - a project is
     not short because the reader chose not to look at half of its people.

     A MONTH NOBODY IS ON IS A ROW TOO. Before this a project-month without a figure was
     skipped, which made the largest shortfall of all - a project nobody is assigned to
     (V-36, R-49) - the one the file could not show. It comes from projUnallocated, the
     same map the tables draw, with fte 0, staffed 0 and the whole demand as its gap. */
  const projMonth = [["month", "month_iso", "project_id", "project_name", "project_type",
                      "clinical_phase", "work_scope_type", "status", "period_name",
                      "demand_fte", "staffed_fte", "gap_fte", "gap_dir",
                      "fte", "hours", "people"]];
  const unalloc = C.projUnallocated || new Map(), demandOf = C.projDemand || new Map();
  const gapsOf = C.projGap || new Map(), stOf = C.projMonth || new Map();
  const projDir = new Map();                   // pid|k -> {dir, gap}, for Flags and Summary
  for (const pid of scope.projects){
    const p = M.projects[pid] || {};
    for (const k of months){
      const e = pAcc.get(iso(k) + "|" + pid), qk = pid + "|" + k;
      const un = unalloc.get(qk);
      if (!e && un === undefined) continue;    // a month it does not run in is not a row
      const seg = (M.periods[pid] || []).find(s =>
        s.period_start && s.period_end
        && s.period_start.getTime() <= Date.UTC(Math.floor(k / 12), k % 12, 1)
        && Date.UTC(Math.floor(k / 12), k % 12, 1) <= s.period_end.getTime());
      const g = gapsOf.get(qk);
      const demand = un !== undefined ? un : (demandOf.has(qk) ? demandOf.get(qk) : null);
      const staffed = un !== undefined ? 0 : (stOf.has(qk) ? stOf.get(qk) : null);
      const gap = un !== undefined ? -un : g ? g.gap : demand === null ? null : 0;
      const dir = un !== undefined ? "unallocated" : g ? g.dir : null;
      if (dir) projDir.set(qk, {dir, gap});
      projMonth.push([label(k), iso(k), pid, p.project_name ?? null,
        p.project_type ?? null, p.clinical_phase ?? null, p.work_scope_type ?? null,
        p.status ?? null, seg ? seg.period_name : null,
        demand === null ? null : r4(demand), staffed === null ? null : r4(staffed),
        gap === null ? null : r4(gap), dir,
        e ? r4(e.fte) : 0, e ? r2(e.fte * HOURS) : 0, e ? e.others.size : 0]);
    }
  }

  const persMonth = [["month", "month_iso", "person_id", "person_name", "department",
                      "primary_role", "capacity_fte", "fte", "hours", "projects",
                      "vs_capacity", "flag"]];
  const persFte = new Map();                   // used by Flags and Summary alike
  /* A MONTH SOMEBODY IS EMPLOYED AND ON NOTHING IS A ROW TOO (R-55), with fte 0 and the
     flag 'unassigned'. Without it the file could say who is overloaded and never who is
     free - and "who could take this on" is the next question after "what is short".
     Only months inside employment_start..employment_end, so somebody who has left is
     not offered as spare capacity. Not under-allocated: a month on nothing is a
     different statement, and it breaks an under-allocation run rather than extending
     it, exactly as the Overall tab counts them. */
  const employed = (who, k) => {
    const first = Date.UTC(Math.floor(k / 12), k % 12, 1);
    const last = Date.UTC(Math.floor(k / 12), k % 12 + 1, 0);
    const s = who.employment_start, f = who.employment_end;
    return !(s instanceof Date && s.getTime() > last)
        && !(f instanceof Date && f.getTime() < first);
  };
  for (const sid of scope.people){
    const who = M.people[sid] || {};
    const cap = num(who.capacity_fte);
    for (const k of months){
      const e = sAcc.get(iso(k) + "|" + sid);
      if (!e){
        if (employed(who, k))
          persMonth.push([label(k), iso(k), sid, who.person_name ?? null,
            who.department ?? null, who.primary_role ?? null, cap,
            0, 0, 0, cap ? 0 : null, "unassigned"]);
        continue;
      }
      const v = r4(e.fte);
      persFte.set(sid + "|" + k, v);
      persMonth.push([label(k), iso(k), sid, who.person_name ?? null,
        who.department ?? null, who.primary_role ?? null, cap,
        v, r2(e.fte * HOURS), e.others.size,
        cap ? r4(v / cap) : null,
        v > M.OVER ? "over" : v < M.UNDER ? "under" : null]);
    }
  }

  // ---- Flags: exactly what the Overall tab counts ---------------------------------
  /* project_id and project_name were added for the project flags below (R-55). Every
     column is on every row and the ones that do not apply are empty, so a reader can
     filter the sheet on `kind` without the columns changing meaning underneath them. */
  const flags = [["kind", "person_id", "person_name", "project_id", "project_name",
                  "from", "to", "months", "fte", "threshold"]];
  let over = 0, runs = 0;
  for (const sid of scope.people){
    const who = M.people[sid] || {};
    let run = [];
    for (const k of months){
      const v = persFte.get(sid + "|" + k) || 0;
      if (v > M.OVER){
        over++;
        flags.push(["over-allocated", sid, who.person_name ?? null, null, null,
                    label(k), label(k), 1, r4(v), M.OVER]);
      }
      // A month a person is not on anything at all is not an under-allocated month -
      // they are unassigned, which is a different statement and breaks the run rather
      // than continuing it. The Overall tab counts runs the same way.
      if (v > 0 && v < M.UNDER) run.push(k);
      else {
        if (run.length >= M.MINM){
          runs++;
          flags.push(["under-allocated run", sid, who.person_name ?? null, null, null,
                      label(run[0]), label(run[run.length - 1]), run.length, null, M.UNDER]);
        }
        run = [];
      }
    }
    if (run.length >= M.MINM){
      runs++;
      flags.push(["under-allocated run", sid, who.person_name ?? null, null, null,
                  label(run[0]), label(run[run.length - 1]), run.length, null, M.UNDER]);
    }
  }

  /* The PROJECT flags (R-55): a run of consecutive months a project is off its standard
     the same way, one row per run. A run rather than a row per month because the same
     shortfall for eight months is one fact about the plan, and eight rows of it would
     outweigh everything else on the sheet. fte is the run's gap in total, as a positive
     amount - the kind already says which way. Short and over are never netted (V-34),
     so a project short in March and over in April is two rows, not one row of nothing. */
  const PKIND = {short:"short of standard", over:"over standard",
                 unallocated:"unallocated demand"};
  const pTot = {short:[0, 0], over:[0, 0], unallocated:[0, 0]};   // [cents, months]
  for (const pid of scope.projects){
    const p = M.projects[pid] || {};
    let run = null;
    const close = () => {
      if (!run) return;
      flags.push([PKIND[run.dir], null, null, pid, p.project_name ?? null,
                  label(run.from), label(run.to), run.n, fromCents(run.cents), null]);
      run = null;
    };
    for (const k of months){
      const d = projDir.get(pid + "|" + k);
      if (!d){ close(); continue; }
      const c = Math.abs(toCents(d.gap));
      pTot[d.dir][0] += c; pTot[d.dir][1]++;
      if (run && run.dir === d.dir && run.to === k - 1){ run.to = k; run.n++; run.cents += c; }
      else { close(); run = {dir:d.dir, from:k, to:k, n:1, cents:c}; }
    }
    close();
  }

  // ---- Summary: the tiles, as figures somebody can paste into a report ------------
  // Summed from the same rounded rows, so the Summary total is exactly the total of
  // the Detail column and exactly the total of each monthly sheet.
  let total = 0;
  for (const row of detail.slice(1)) total += row[col.fte];
  const pcol = Object.fromEntries(projMonth[0].map((h, i) => [h, i]));
  let stdCents = 0;
  for (const row of projMonth.slice(1)) stdCents += toCents(row[pcol.demand_fte] || 0);
  const stdTotal = fromCents(stdCents);
  const summary = [["measure", "value", "unit", "note"],
    ["Months in view", months.length, "months",
     `${label(months[0])} to ${label(months[months.length - 1])}`],
    ["Projects in view", scope.projects.length, "projects",
     `of ${Object.keys(M.projects).length} in the source file`],
    ["People in view", scope.people.length, "people",
     `of ${Object.keys(M.people).length} in the source file`],
    ["Total demand", r4(total), "FTE-months",
     "the STAFFED figure: the sum of every person-month in this file"],
    ["Total demand", r2(total * HOURS), "hours",
     `at ${HOURS} hours to 1.00 FTE`],
    ["Over-allocated", over, "person-months", `above ${M.OVER} FTE`],
    ["Under-allocation runs", runs, "runs",
     `${M.MINM}+ consecutive months below ${M.UNDER} FTE`],
    /* R-55: the project side, summed from ProjectMonth so the two cannot disagree. */
    ["Standard demand", r4(stdTotal), "FTE-months",
     "what the projects' own standards ask for (ProjectMonth.demand_fte, whole projects)"],
    ["Short of standard", pTot.short[1], "project-months",
     `${fromCents(pTot.short[0]).toFixed(2)} FTE-months below the standard in all`],
    ["Over standard", pTot.over[1], "project-months",
     `${fromCents(pTot.over[0]).toFixed(2)} FTE-months above the standard in all`],
    ["Unallocated demand", pTot.unallocated[1], "project-months",
     `${fromCents(pTot.unallocated[0]).toFixed(2)} FTE-months that nobody is assigned to`],
    ["Detail rows", detail.length - 1, "assignment-months",
     "each one a single multiplication; the two monthly sheets are their sums"],
  ];

  // ---- Assumptions: what shaped the figures ---------------------------------------
  const assumptions = [["parameter", "value", "what it affected", "note"]];
  for (const r of M.raw.Config){
    if (!r.parameter) continue;
    assumptions.push([r.parameter, r.value ?? null,
                      CFG_AFFECTS[r.parameter] || "", r.note ?? null]);
  }

  // ---- ReadMe ----------------------------------------------------------------------
  const readme = [["PRAP — calculated monthly FTE"], [],
    ["WHAT THIS FILE IS"],
    ["The figures the application worked out, for reading, reporting or analysis "
     + "somewhere else."],
    [],
    ["WHAT IT IS NOT"],
    ["It is NOT a source workbook and CANNOT be imported. Everything in it is derived; "
     + "there is nothing here to edit and feed back. To keep working on the plan, "
     + "export the source data instead — that is the other item on the export menu, and "
     + "it round-trips."],
    [],
    ["HOW EVERY FIGURE WAS MADE"],
    ["FTE  =  demand_fte  ×  role_share,  ROUNDED TO A WHOLE NUMBER OF HUNDREDTHS,  "
     + "where  demand_fte = standard_fte  ×  period weight  ×  month_run"],
    ["The rounding is part of the rule and not a presentation choice (REQ-CAL-20). Every "
     + "figure this application produces is a whole number of hundredths, because at 160 "
     + "hours to the FTE 0.01 is 1.6 hours and the plan is not written finer than that. "
     + "So a row's fte is its demand times its share IN WHOLE HUNDREDTHS: each row takes "
     + "its floor, and the hundredths left over go to the rows with the largest "
     + "remainders. A row can therefore sit up to 0.01 from the exact product."],
    ["What is exact, and what this sheet is for: THE ROWS OF ONE PROJECT-MONTH ADD UP TO "
     + "demand_fte EXACTLY, to the hundredth, with nothing left over. The month's "
     + "hundredths are handed out by largest remainder rather than each row being "
     + "rounded on its own - round three shares of 4.27 separately and they come to 4.26 "
     + "or 4.28, and the sheet would not reconcile."],
    ["standard_fte", "the month's DEMAND for a project of this type, phase and work scope in this period, from PeriodFTEStandard. A magnitude in FTE: 4.02 means the period takes about four full-time people a month."],
    ["period weight", "this project's own adjustment to that standard, from ProjectPeriod. 1.00 means an ordinary project of its kind."],
    ["month_run", "how much of the month the project actually ran, taken as the largest "
     + "coverage any of its people have. A project whose period ends on the 10th draws a "
     + "third of a month, not a whole one."],
    ["demand_fte", "the project's whole month: standard_fte x period weight x month_run. "
     + "EVERY ROW OF ONE PROJECT-MONTH CARRIES THE SAME FIGURE, and the fte column of "
     + "those rows adds up to exactly it."],
    ["role_share", "this person's slice of that demand. Their role's factor, divided by "
     + "the people holding that role, times their person weight, times their own "
     + "coverage - over the sum of the same product for everybody on the project that "
     + "month. THE SHARES ADD TO ONE, so the month is the demand however many people "
     + "are on it: an unstaffed role's work lands on the others, and a part-time person "
     + "pushes load onto their colleagues rather than making the project cheaper."],
    ["Worked out once per assignment per month. The 'Detail' sheet is one row per "
     + "assignment per month with all four numbers in it; ProjectMonth and PersonMonth "
     + "are those rows summed by project and by person. Nothing else enters the "
     + "multiplication — capacity_fte is what a person's load is compared against, "
     + "never something it is scaled by."],
    [],
    ["WHERE A FIGURE WAS STATED RATHER THAN CALCULATED"],
    ["Not every figure here came from that multiplication. A project, or one person's "
     + "assignment to a project, can be set to MANUAL, and its monthly FTE is then "
     + "stated by whoever knows the work rather than worked out from the assumptions. "
     + "The 'estimation' column on Detail says which every row is:"],
    ["automatic", "the multiplication above, and nothing else."],
    ["manual (assignment)", "this person's own contribution to this project that month "
     + "was stated outright. The four terms are still shown, but they describe what "
     + "WOULD have been calculated — they no longer produce the fte beside them."],
    ["manual (project, shared out)", "the project's whole month was stated, and every "
     + "person on it that month was scaled by 'project_scale' so they still add up to "
     + "'project_manual_total'. That is why a person's figure can move without anything "
     + "about that person changing."],
    ["automatic_fte", "on EVERY row, what the assumptions alone would have produced. On "
     + "an automatic row it equals fte; on a stated one, the difference between the two "
     + "is the size of the departure being made."],
    ["Manual is all or nothing for the thing it is set on: switching to it copies every "
     + "calculated month across first, so there is no half-manual run and no month "
     + "carries a flag of its own."],
    [],
    ["WHERE A FIGURE CAN BE SHORT OF AN ASSUMPTION"],
    ["period_weight_from says 'none — V-12' where the month fell in no period and was "
     + "weighted 1.00. role_factor is empty where RoleFactor had no row for that "
     + "combination and the factor was taken as 1.00 (V-23). Both are reported in the "
     + "application's findings, and both mean the figure is short of something rather "
     + "than wrong in itself."],
    [],
    ["STANDARD AGAINST STAFFED — WHICH PROJECTS ARE SHORT OR OVER"],
    ["ProjectMonth carries what each project NEEDS beside what it is GIVEN, once per "
     + "project-month. Use these columns for any question about shortage or excess - "
     + "never add up demand_fte on Detail, which repeats the project's demand on every "
     + "person's row and so multiplies it by the headcount."],
    ["demand_fte", "what the project's standard asks for that month: standard_fte x "
     + "period weight x month_run."],
    ["staffed_fte", "what the project's people are given that month, ALL of them, "
     + "whatever filter was on when this file was exported."],
    ["gap_fte", "staffed_fte - demand_fte. Negative is short of the standard, positive "
     + "is over it, 0 is on it. An all-automatic month is always 0: the people divide "
     + "the demand exactly. A gap only appears where somebody stated a figure by hand "
     + "(V-34) or nobody is assigned at all (V-36)."],
    ["gap_dir", "short / over / unallocated, or empty where demand and staffed agree. "
     + "'unallocated' is a month the project's periods ask for and nobody is on: fte 0, "
     + "people 0, and the whole demand as the gap."],
    ["fte", "the part of staffed_fte that is IN VIEW. Unfiltered it equals staffed_fte; "
     + "filtered to some people it is their share only, and the gap is still the "
     + "project's own."],
    ["PersonMonth has a row for every month a person is employed, including the months "
     + "they are on nothing: fte 0 and flag 'unassigned'. That is spare capacity, and it "
     + "is the place to look for somebody to cover a shortfall."],
    ["The Flags sheet lists the same thing as runs: one row per project per stretch of "
     + "consecutive months off the standard the same way, with the run's gap in total. "
     + "Short and over are never netted against each other."],
    [],
    ["WHAT IS COVERED"],
    ["This file holds what was ON SCREEN when it was exported — the horizon and any "
     + "filters. Anything outside them is not here."],
    ["Horizon", months.length ? `${label(months[0])} to ${label(months[months.length - 1])}` : "(none)"],
    ["Projects", `${scope.projects.length} of ${Object.keys(M.projects).length}`],
    ["People", `${scope.people.length} of ${Object.keys(M.people).length}`],
    ["Filters", scope.filters || "none — everything in the file"],
    [],
    ["PROVENANCE"],
    ["Source file", scope.fileName || "(unsaved plan)"],
    ["Exported", scope.stamp],
    ["Application", `PRAP ${APP_VERSION}`],
    ["Source schema", String(M.config.schema_version ?? "(not stated)")],
    ["Unresolved findings",
     `${(M.findings || []).filter(f => f.sev === "error" || f.sev === "fatal").length} error(s), `
     + `${(M.findings || []).filter(f => f.sev === "warning").length} warning(s) — `
     + `see the application's findings report`],
  ];

  return {"00_ReadMe": readme, Summary: summary, ProjectMonth: projMonth,
          PersonMonth: persMonth, Detail: detail, Flags: flags,
          Assumptions: assumptions};
}
