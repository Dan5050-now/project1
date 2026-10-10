/* ============================================================ 6a. import difference
   What a source workbook would CHANGE about a plan that already holds data.

   Loading a file over an empty plan is obvious: adopt it. Loading one over a plan
   somebody has been working in is not, and the honest answer is not a choice between
   "replace everything" and "cancel". Most of an updated workbook is the same as what
   is already there; what matters is the handful of rows that differ, and whether the
   person at the keyboard wants them.

   So this compares the two, sheet by sheet, and says:

       ADD          rows the file has and the plan does not
       CHANGE       rows both have, with the columns that differ and both values
       ONLY HERE    rows the plan has and the file does not - reported, never removed

   ONLY HERE is the one worth stating plainly (S-N04): an accepted sheet ADDS and
   CHANGES but never DELETES. A row somebody typed by hand survives an import of a
   workbook that never knew about it. Removing rows stays a separate, deliberate act,
   because the alternative silently destroys work whose only crime was being newer
   than the file.

   Pure: no DOM, no files, no dialogs. It takes two sets of parsed rows and returns a
   description of the difference, which is what makes it testable without a browser
   and what keeps the decision - who gets asked what - in ui/ where it belongs.

   Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 09; NR-IMP-02, S-N03, S-N04.  */

/* Which columns identify a row.
   Not KEY_COL: that names ONE column per sheet, which on a child sheet is a foreign
   key rather than an identity - every milestone of a project shares its project_id.
   These are the real composite keys, the same ones docs/prap_contract.json publishes,
   and tools/check_consistency.py holds the two to each other. */
/* ----------------------------------------------- the settings an import would change
   A Config row is not like any other row in the file, and comparing it as one misses
   what makes it dangerous. Every other sheet describes the PLAN - projects, people,
   who is on what - and replacing it is the whole point of an import. Config describes
   how the plan is READ: two of its settings switch calculation rules on and off, three
   more set the thresholds every allocation flag is measured against. Import a colleague's
   workbook to look at their projects and you silently take their thresholds with it, and
   every figure and every flag on your screen shifts for a reason that is nowhere on it.

   So the settings are compared on their own, by name, before and after - and what
   changed is put in front of the user rather than left as one sheet among ten in the
   full difference report. Nothing is refused: importing a file MEANS taking its
   settings, which is what makes the plan reproducible from the file alone. What was
   missing was being told.

   Pure, and here rather than in the shell, because both shells import. */
const CFG_EFFECT = {
  over_allocation_fte:         "moves every over-allocation flag",
  under_allocation_fte:        "moves every under-allocation flag",
  under_allocation_min_months: "moves every under-allocated run",
  split_shared_role_fte:       "CHANGES EVERY FIGURE for a shared role (REQ-CAL-14)",
  absorb_unstaffed_role_factor:"CHANGES EVERY FIGURE on a project with an unstaffed role (REQ-CAL-16)",
  fte_hours_per_month:         "changes the hours shown, not the FTE",
  capacity_unit:               "display only",
  default_horizon_months:      "display only — the months the dashboard opens on",
  schema_version:              "which structure the file was written to",
};

/** What importing this file would change about how the plan is read.
 *
 *  `before` and `after` are parameter -> value maps. Returns one entry per setting that
 *  differs, newest state last, with `kind` saying which of the three things happened:
 *  a value changed, the file adds a setting the application did not have, or the file is
 *  missing one the application had (where the built-in default takes over — V-30). */
function configChanges(before, after){
  const out = [];
  for (const k of [...new Set([...Object.keys(before || {}), ...Object.keys(after || {})])].sort()){
    const a = (before || {})[k], b = (after || {})[k];
    if (diffSame(a, b)) continue;
    const had = a !== undefined && a !== null && a !== "";
    const has = b !== undefined && b !== null && b !== "";
    out.push({parameter:k, from:a, to:b,
              kind: had && has ? "changed" : has ? "added" : "removed",
              effect: CFG_EFFECT[k] || ""});
  }
  return out;
}

const DIFF_KEY = {
  Project:              ["project_id"],
  Milestone:            ["project_id", "milestone_name", "milestone_date"],
  ProjectPeriod:        ["project_id", "period_name"],
  PeriodFTEStandard: ["project_type", "clinical_phase", "work_scope_type", "period_name"],
  RoleFactor:           ["project_type", "clinical_phase", "work_scope_type", "period_name",
                         "role_name"],
  IssueReview:          ["project_id", "month", "issue"],
  PeriodHighlight:      ["period_name"],
  Person:               ["person_id"],
  Assignment:           ["assignment_id"],
  PersonPeriodWeight:   ["assignment_id", "period_start"],
  // Schema 9. Keyed on all three: `scope` decides whether ref_id names a project
  // or an assignment, so ref_id + month alone would merge a project figure with an
  // assignment figure the moment the two identifiers ever collide.
  MonthlyEstimate:      ["scope", "ref_id", "month"],
  Lists:                ["list_name", "value"],
  Config:               ["parameter"],
};

/** One value, in a form two files can be compared in.
 *
 *  A date read from .xlsx is a Date; the same date in a .prap.json is a string. A
 *  weight may be 1.2 in one and "1.20" in the other. None of those are differences a
 *  person would call a difference, and a report full of them is a report nobody reads
 *  to the end. */
function diffValue(v){
  if (v === null || v === undefined || v === "") return null;
  if (v instanceof Date) return "d:" + ymd(v);
  if (typeof v === "number") return "n:" + v;
  const s = String(v).trim();
  if (s === "") return null;
  const n = Number(s);
  return (s !== "" && Number.isFinite(n)) ? "n:" + n : "s:" + s;
}

const diffSame = (a, b) => diffValue(a) === diffValue(b);

/** How a value reads in the report. Null becomes a visible word, because a cell that
 *  is being emptied is a change and "" would look like the report had a gap in it. */
function diffShown(v){
  if (v === null || v === undefined || v === "") return "(empty)";
  if (v instanceof Date) return ymd(v);
  return String(v);
}

const diffKeyOf = (sheet, row) =>
  (DIFF_KEY[sheet] || []).map(k => String(diffValue(row[k]))).join("\u0000");

/** Compare a plan against a source file.
 *
 *  Both sides are the parsed rows - what buildModel puts in M.raw - so the file has
 *  already been read, coerced and validated by the time it gets here. Anything the
 *  application DERIVES is left out of the comparison entirely: a stale total in a
 *  hand-edited workbook is not a change worth reporting, and must never become the
 *  truth (NR-IMP-08). */
function importDiff(currentRaw, incomingRaw){
  const out = {};
  for (const sheet of REQUIRED_SHEETS){
    const derived = new Set(DERIVED_COLS[sheet] || []);
    const cols = (SHEET_HEADERS[sheet] || []).filter(c => !derived.has(c));
    const mine = new Map(), theirs = new Map();
    for (const r of (currentRaw[sheet] || [])){
      if (r.__new) continue;                  // a row still being typed is not a row yet
      mine.set(diffKeyOf(sheet, r), r);
    }
    for (const r of (incomingRaw[sheet] || [])) theirs.set(diffKeyOf(sheet, r), r);

    const add = [], change = [], onlyHere = [];
    let same = 0;
    for (const [k, r] of theirs){
      const here = mine.get(k);
      if (!here){ add.push(r); continue; }
      const diffs = [];
      for (const c of cols)
        if (!diffSame(here[c], r[c]))
          diffs.push({col:c, from:here[c], to:r[c]});
      if (diffs.length) change.push({key:k, row:here, incoming:r, cols:diffs});
      else same++;
    }
    for (const [k, r] of mine) if (!theirs.has(k)) onlyHere.push(r);

    out[sheet] = {sheet, key:DIFF_KEY[sheet] || [], cols, add, change, onlyHere, same,
                  touched: add.length + change.length};
  }
  return out;
}

/** Is there anything to decide? A file identical to the plan produces a report with
 *  nothing in it, and asking somebody to approve nothing is worse than saying so. */
const importDiffEmpty = d =>
  Object.values(d).every(s => s.touched === 0);

/** A one-line description of a row, for the report. The key columns, because they are
 *  what identifies it, plus the name column where the sheet has one - "PRJ-014" alone
 *  tells nobody which project is about to change. */
function diffLabel(sheet, row){
  const parts = (DIFF_KEY[sheet] || []).map(k => diffShown(row[k]));
  for (const extra of ["project_name", "person_name", "role_name"])
    if (!(DIFF_KEY[sheet] || []).includes(extra) && row[extra])
      parts.push(String(row[extra]));
  return parts.join(" · ") || "(row)";
}

/** Apply the sheets the user accepted, as PENDING EDITS.
 *
 *  Pending, not committed, so the whole import goes back with 'Leave without change'
 *  and is kept with 'Save' - the same door as every other change (S-N02). An import
 *  that could not be undone would be the one edit in the application that demanded to
 *  be right first time.
 *
 *  ADDS and CHANGES only. onlyHere rows are never touched: see the note at the top. */
function importApply(diff, accepted, hooks){
  hooks = hooks || {};
  const begin = hooks.begin || (typeof beginEditSession === "function" ? beginEditSession : null);
  const make = hooks.newRow || (typeof newRow === "function" ? newRow : null);
  const note = hooks.note || (e => { if (typeof S === "object" && S.pending) S.pending.push(e); });
  if (begin) begin();

  let added = 0, changed = 0, cells = 0;
  for (const sheet of REQUIRED_SHEETS){
    if (!accepted.has(sheet)) continue;
    const d = diff[sheet];
    if (!d) continue;

    for (const r of d.add){
      const seed = {};
      for (const c of d.cols) seed[c] = r[c] ?? null;
      const created = make(sheet, seed);
      // An imported row is COMPLETE, so it must not carry the draft marker newRow
      // sets: a draft is held out of validation and contributes nothing to the
      // calculation, which would make an imported assignment silently weightless.
      delete created.__new;
      note({at:new Date(), sheet, row:created.__row, col:"(imported row)",
            from:null, to:diffLabel(sheet, r)});
      added++;
    }

    for (const ch of d.change){
      for (const one of ch.cols){
        ch.row[one.col] = one.to;
        note({at:new Date(), sheet, row:ch.row.__row, col:one.col,
              from:one.from, to:one.to});
        cells++;
      }
      changed++;
    }
  }
  return {added, changed, cells};
}
