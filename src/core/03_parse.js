/* ============================================================ 3. dates + parse
   Spec sheet 03: accept an Excel serial or an ISO yyyy-mm-dd string, normalise to a
   date with no time part, and never guess at any other format (REQ-NFR-05).     */

const EPOCH = Date.UTC(1899, 11, 30);      // Excel's 1900 leap-year bug included
function serialToDate(n){ return new Date(EPOCH + Math.round(n) * 86400000); }
function dateToSerial(d){ return Math.round((d.getTime() - EPOCH) / 86400000); }
function ymd(d){ return d ? d.toISOString().slice(0, 10) : ""; }
function parseDate(v){
  if (v === null || v === undefined || v === "") return null;
  if (v instanceof Date) return v;
  if (typeof v === "number") return serialToDate(v);
  const m = String(v).trim().match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? new Date(Date.UTC(+m[1], +m[2] - 1, +m[3])) : undefined;   // undefined = bad
}
function num(v){
  if (v === null || v === undefined || v === "") return null;
  if (typeof v === "number") return v;
  const n = Number(String(v).trim());
  return isFinite(n) ? n : undefined;
}
function txt(v){
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s === "" ? null : s;
}

const SHEET_COLS = {
  Project: {date:["start_date","end_date"], num:["planned_member_count","total_period_months"]},
  Milestone: {date:["milestone_date"], num:["milestone_seq"]},
  ProjectPeriod: {date:["period_start","period_end"], num:["period_seq","weight"]},
  PeriodWeightStandard: {date:[], num:["weight"]},
  RoleFactor: {date:[], num:["role_factor"]},
  Person: {date:["employment_start","employment_end"], num:["capacity_fte"]},
  Assignment: {date:["assign_start_date","assign_end_date"], num:["person_weight"]},
  PersonPeriodWeight: {date:["period_start","period_end"], num:["weight_override"]},
  Lists: {date:[], num:[]},
  Config: {date:[], num:[]},
};
const REQUIRED_SHEETS = Object.keys(SHEET_COLS);
/* The schema's own column order, independent of any one file. A workbook carries its
   headers, so the application takes them from what it loaded; the JSON interchange file
   carries row OBJECTS and has no column order at all, so it needs this. It is also the
   list a JSON file is checked against, which is how a mistyped column name is caught
   instead of silently ignored. tools/check_consistency.py holds it to the template. */
const SHEET_HEADERS = {
  Project:["project_id","project_name","project_type","project_category","clinical_phase",
    "work_scope_type","outsourcing_type","EDC_setup","DataReviewSystem_setup","RBQM_setup","DM_conduct",
    "EDC_system","DataReviewSystem","RBQM_system","planned_member_count","start_date",
    "end_date","total_period_months","status","note_1","note_2","note_3","note_4","note_5"],
  Milestone:["project_id","project_name","milestone_name","milestone_date","milestone_seq","note_1"],
  ProjectPeriod:["project_id","period_name","period_seq","period_start","period_end","weight","note_1"],
  PeriodWeightStandard:["project_type","clinical_phase","work_scope_type","period_name",
    "weight","note_1"],
  RoleFactor:["project_type","clinical_phase","work_scope_type","period_name","role_name",
    "role_factor","role_note"],
  Person:["person_id","person_name","department","primary_role","capacity_fte",
    "employment_start","employment_end","note_1","note_2","note_3","note_4","note_5"],
  Assignment:["assignment_id","person_id","person_name","project_id","role_name",
    "assign_start_date","assign_end_date","person_weight","note_1","note_2","note_3"],
  PersonPeriodWeight:["assignment_id","period_start","period_end","weight_override","reason"],
  Lists:["list_name","value","note_1"],
  Config:["parameter","value","note"],
};
/* Which project types are clinical trials.
   Schema 6 split 'Biosimilar CT' into '(Healthy)' and '(Patient)', and a fixed set of
   names would have to be edited again the next time a type is subdivided - in the code,
   by a programmer, for what is a change to a value list. So the question is asked of the
   NAME instead: anything that begins 'NewDrug CT' or 'Biosimilar CT' is a clinical trial
   and takes the seven clinical periods; everything else takes the three 'Others' ones.
   `has` rather than a bare function so every existing call site reads unchanged. */
const CLINICAL_TYPES = {
  has: t => /^(NewDrug CT|Biosimilar CT)/.test(String(t ?? "")),
};
/* The value schema 6 retired. Named here so a file carrying it gets a sentence that says
   what to do, rather than the generic "not in the value list" - which is true, unhelpful,
   and identical to the message for a typo. */
const RETIRED_TYPES = {
  "Biosimilar CT": "Biosimilar CT (Healthy) or Biosimilar CT (Patient)",
};
const CLINICAL_PERIODS = ["Before-Start-up","Start-up","Conduct (interim)","Close-out (interim)",
                          "Conduct (final)","Close-out (final)","After Close-out (final)"];
const OTHER_PERIODS = ["Planning","Develop","Close"];
const KEY_MILESTONES = new Set(["interim DB lock","final DB lock"]);
/* V-14's ordering half. Stated as PAIRS, not as one chain, because the ten milestone
   names are not totally ordered in a real trial: an INTERIM database lock is precisely
   the one taken while recruitment is still running, so it may fall either side of LPI,
   and a chain would report every such trial as an error. Only these pairs are ordered
   by definition. */
const MILESTONE_ORDER = [
  ["Protocol (v1)","CTA submission"], ["CTA submission","First SIV"],
  ["First SIV","FPI"], ["FPI","LPI"],
  ["interim DB lock cut-off","interim DB lock"], ["interim DB lock","final DB lock"],
  ["final DB lock cut-off","final DB lock"], ["CTA submission","final DB lock"],
];
// The derivation hangs on these three; out of order between them is an error, because
// the periods it computes would be wrong rather than merely surprising.
const DERIVATION_MILESTONES = new Set(["CTA submission","interim DB lock","final DB lock"]);
// The identifier of each sheet, and everywhere that identifier is referenced.
// Editing one has to rewrite the others (REQ-IMP-10); a new row without one blocks export.
const KEY_COL = {Project:"project_id", Person:"person_id", Assignment:"assignment_id",
                 Milestone:"project_id", ProjectPeriod:"project_id",
                 PersonPeriodWeight:"assignment_id", Config:"parameter", Lists:"list_name",
                 PeriodWeightStandard:"project_type", RoleFactor:"project_type"};
// Which sheet OWNS each identifier. KEY_COL names the key column of every sheet, but
// on a child sheet that column is a FOREIGN key - Milestone.project_id points at a
// project, it does not define one. Deleting a milestone must not go looking for rows
// that reference "its" project_id and refuse on their account.
/* What each column means, shown on its heading. These definitions come from the plan's
   data model - the point is that someone filling in the workbook should not have to
   open a specification to find out what a column is for. */
const COLUMN_HELP = {
  project_id:"Unique identifier for the project. Editing it cascades to every row that references it.",
  project_name:"Display name. Shown wherever the project appears.",
  project_type:"'NewDrug CT', 'Biosimilar CT (Healthy)', 'Biosimilar CT (Patient)' or 'Others'. Everything but 'Others' is a clinical trial: they share one period set and differ in their weights.",
  project_category:"Product name. Required for either clinical trial type (V-04).",
  clinical_phase:"Phase 1 to 4. With the project type and the work scope it selects the standard period weights and role factors.",
  work_scope_type:"How much of the work is done in-house. Part of the key into PeriodWeightStandard and RoleFactor: a standards row with this column EMPTY applies to every scope, so only the scopes that really differ need their own row.",
  outsourcing_type:"Full outsourcing, Partial outsourcing, or Full In-house. Descriptive only — work_scope_type is what the weights are keyed on (V-25).",
  EDC_setup:"Who sets up EDC — by CRO or by SB.",
  DataReviewSystem_setup:"Who sets up the data review system.",
  RBQM_setup:"Who sets up RBQM.",
  DM_conduct:"Who reviews the data.",
  EDC_system:"EDC system in use.",
  planned_member_count:"Planned team size. Compared against the assignments actually recorded.",
  start_date:"Project start. Accepts yyyy-mm-dd or a real Excel date — an ambiguous format like 03/04/2026 is rejected, never guessed at.",
  end_date:"Planned project end. Used as the assignment end when an assignment has none.",
  total_period_months:"DERIVED. Recomputed from the dates on import; the value in the file is not trusted.",
  status:"Planned, Active, On hold or Completed.",
  milestone_name:"From the standard list of ten. 'Inspection' may appear on several rows; nothing else should (V-20).",
  milestone_date:"Planned date. CTA submission and the DB locks are what the period derivation hangs on.",
  milestone_seq:"Display order along the timeline.",
  period_name:"One of the seven clinical periods, or the three 'Others' periods. UNIQUE within a project — with project_id it identifies the row.",
  period_seq:"Orders the periods along the timeline. Carries order, not identity.",
  period_start:"Inclusive. Periods must not overlap or leave a gap (V-06, V-12).",
  period_end:"Inclusive.",
  weight:"Effort multiplier for this period. Multiplied by the role factor, the person weight and the month coverage.",
  weight_override:"REPLACES person_weight for the months this window covers — it does not multiply it.",
  role_name:"Must exist in RoleFactor for this project's type (V-03).",
  role_factor:"What one person in this role costs the project per month, before their own weight and the period weight. Keyed on type, phase, work scope, period and role.",
  role_note:"Free text. The basis for the factor.",
  person_id:"Unique identifier for the person. Editing it cascades to every assignment that references it.",
  person_name:"Display name. On Assignment this is DERIVED and recomputed from the master row.",
  department:"Grouping used by the dashboard filters.",
  primary_role:"Usual role. An assignment can override it.",
  capacity_fte:"How much this person is available for, in FTE. Shown for context — the allocation thresholds are absolute and are NOT scaled by it.",
  assignment_id:"Unique identifier. One row per person + project + role.",
  assign_start_date:"When this person starts on this project.",
  assign_end_date:"When they finish. Empty means the project's own end date.",
  person_weight:"How much of this person goes to this project, as a fraction. A PersonPeriodWeight window replaces it for the months it covers.",
  parameter:"The setting's name. The application reads these on load.",
  value:"The setting's value. A value that fails coercion is an error — a threshold read as text would silently disable a flag.",
  note:"Free text.",
  reason:"Why the weight differs for this window, e.g. part-time or covering a peak.",
  note_1:"Free text. Carried through export unchanged and never read by the calculation.",
};
const HELP = {
  rowactions:"<b>Row actions</b><br>Insert a new row directly below this one, or delete this row. "
    + "Both are provisional — 'Leave without change' undoes them.",
  insert:"<b>Insert a row</b><br>Adds a blank row directly below this one, so it lands where you are "
    + "looking rather than at the bottom of the table. A row with no identifier will block the export "
    + "until you fill one in.",
  blankms:"<b>Blank list</b><br>Lays out the standard milestone names for this project with "
    + "their dates left empty, so only the dates have to be typed. Names already listed are "
    + "not repeated, and any you do not need can be deleted. The rows are ordinary rows - "
    + "provisional until Save, like anything else.",
  autoper:"<b>Auto derivation</b><br>Builds this project's periods from its milestones, by "
    + "the rule in the development plan: Start-up opens the day after Protocol (v1) or a "
    + "month before CTA submission, closes at First SIV or four months later; an interim DB "
    + "lock splits the conduct stretch in two; Close-out (final) starts three months before "
    + "the final DB lock; and an Inspection after that lock opens After Close-out (final). "
    + "Each period takes the standard weight for this project's type and phase. They are "
    + "ORDINARY ROWS afterwards - edit any of them, and Save when you are happy. Needs CTA "
    + "submission and a DB lock (V-16), and applies to clinical trials only.",
  del:"<b>Delete this row</b><br>Refused if anything still references it, naming what does (V-17). "
    + "A delete is never cascaded. Provisional like any other change — 'Leave without change' puts it back.",
};

/* A row becomes a RECORD when it carries its sheet's identifier, and not before.
 *
 * This had teeth. A project saved with every field filled in EXCEPT project_id used to be
 * indexed as M.projects[null] - which JavaScript turns into the string key "null". The
 * application then believed in a project called "null": it appeared in the filter, it
 * became the selection, and the row filter `keep.has(r.project_id)` compared the set
 * {"null"} against the row's actual null and missed - so the table the user had just
 * typed into reported "No rows. Use + row to add one." Its milestones and periods went
 * looking for a parent named "null" and found none, and a row added there was stamped
 * with "null" too. The same happened to a person with no person_id, which is why the
 * Assignments table beneath them offered nothing to fill in.
 *
 * So: a row with no identifier is not indexed, is reported, and STAYS ON SCREEN, because
 * it is the row the user is in the middle of repairing. */
const hasKey = (sheet, r) => {
  const k = KEY_COL[sheet];
  if (!k) return true;
  const v = r[k];
  return !(v === null || v === undefined || String(v).trim() === "");
};
function noKey(F, sheet, r, col, owns){
  F.push({sev:"error", rule:"V-08", sheet, row:r.__row,
    msg:`A row on ${sheet} has no ${col}. Nothing can reference it, its ${owns} have `
      + `nothing to attach to, and it would be lost when the file is read back. Fill in `
      + `${col} or delete the row.`});
}

const OWNER = {project_id:"Project", person_id:"Person", assignment_id:"Assignment"};
/* A child table is shown filtered to the parent selected above it. A new row therefore
   has to INHERIT that parent, or it fails the very filter that decides whether it is
   visible - the row exists but can never be seen or filled in. The specification says
   this ("pre-fill the parent key where the table is a child of a selection"); it was
   specified and not implemented. */
const PARENT_OF = {
  Milestone:          () => ["project_id", S.selProj],
  ProjectPeriod:      () => ["project_id", S.selProj],
  Assignment:         () => ["person_id", S.selPers],
  // The override table hangs off the SELECTED assignment, so a row created in it belongs
  // to that assignment - seeding the person's first one would file it under a different
  // project from the one on screen.
  PersonPeriodWeight: () => {
    if (S.selAsg) return ["assignment_id", S.selAsg];
    // From raw, not from M.assignments: the validated array excludes anything still
    // being entered, so on a plan being typed from scratch the only assignment on
    // screen would not be found, and the override would be created parentless.
    const first = S.model.raw.Assignment.find(a => a.person_id === S.selPers && a.assignment_id);
    return ["assignment_id", first ? first.assignment_id : null];
  },
};
const REFS = {
  project_id: [["Milestone","project_id"],["ProjectPeriod","project_id"],["Assignment","project_id"]],
  person_id:  [["Assignment","person_id"]],
  assignment_id: [["PersonPeriodWeight","assignment_id"]],
};

/** Rows -> objects keyed by header, with per-column coercion. Findings collected. */
function toObjects(sheet, rows, F){
  if (!rows || !rows.length){ return []; }
  const hdr = (rows[0] || []).map(h => txt(h));
  const spec = SHEET_COLS[sheet];
  const out = [];
  for (let r = 1; r < rows.length; r++){
    const raw = rows[r] || [];
    if (raw.every(v => v === null || v === undefined || v === "")) continue;  // blank row: skip
    const o = {__row: r + 1};
    let bad = false;
    hdr.forEach((h, i) => {
      if (!h) return;
      let v = raw[i];
      if (spec.date.includes(h)){
        const d = parseDate(v);
        if (d === undefined){
          F.push({sev:"error", rule:"V-00", sheet, row:r+1,
            msg:`${sheet} row ${r+1}: '${v}' is not a date. Use yyyy-mm-dd or a real Excel date — `
              + `a format like 03/04/2026 is ambiguous and is never guessed at.`});
          bad = true; v = null;
        } else v = d;
      } else if (spec.num.includes(h)){
        const n = num(v);
        if (n === undefined){
          F.push({sev:"error", rule:"V-00", sheet, row:r+1,
            msg:`${sheet} row ${r+1}: '${v}' is not a number in column ${h}.`});
          bad = true; v = null;
        } else v = n;
      } else {
        v = (typeof v === "number") ? String(v) : txt(v);
      }
      o[h] = v;
    });
    o.__bad = bad;
    out.push(o);
  }
  return out;
}

