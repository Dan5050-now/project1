/* ============================================================ 7. state + filters */

const S = {
  model:null, calc:null, fileName:"", loadedAt:null, blank:false,
  from:null, to:null,                       // month keys
  // Each filter holds a SET of chosen values. Empty means "All" - which is both the
  // natural reading of "nothing narrowed" and what keeps every predicate below short.
  f:{type:new Set(), phase:new Set(), out:new Set(), proj:new Set(),
     pers:new Set(), role:new Set(), dept:new Set()},
  tab:"t-overall", expanded:new Set(), selProj:null, selPers:null, selAsg:null,
  /* Which tabs no longer match the model. Three of the four panes are hidden at any
     moment, so renderAll() marks them all stale and draws only the one on screen;
     showTab() draws a pane the moment it is asked for. See renderAll() in 11_tabs.js
     for what this is and is not worth. */
  stale:new Set(),
  pending:[], saved:0, snapshot:null, editedCells:new Set(), headers:{},
  // The findings as of the last point the user said 'keep this' - a load, or a
  // save. What a batch of edits LEAVES unresolved is measured against this, not
  // against the live model, which already carries the consequences of every
  // keystroke since.
  baseFindings:[],
  // What the last import changed about the SETTINGS, as opposed to the plan.
  cfgChanges:[],
  genView:{pws:"matrix", rf:"matrix", lists:"matrix"},
  /* PER-COLUMN filters on the editable tables: sheet -> column -> Set of kept values.
     Separate from S.f above, which is the horizon-wide filter bar and narrows the whole
     page. These narrow ONE TABLE, the way a spreadsheet's column filter does, and they
     do not touch the charts or the figures - a project filtered out of the table below
     is still in the totals above it, because it is still in the plan. */
  colf:{},
  /* The accumulated record of what was changed, and of what the application reported
     while it was being changed. Unlike S.pending, which is emptied at every save because
     its job is "what is not saved yet", this is only ever appended to for the life of
     the session, and a save is what writes it out rather than what clears it. */
  /* `archived` / `eventsArchived` are how far each list has been written out, so a
     shell that archives incrementally appends only what is new - and, if a write fails,
     retries the same entries at the next save instead of losing or duplicating them. */
  audit:[], events:[], who:null, archived:0, eventsArchived:0,
};

/** A filter with nothing ticked narrows nothing. */
const anyOf = (set, v) => !set.size || set.has(v);

function activeProjects(){
  const M = S.model, out = [];
  for (const [pid, p] of Object.entries(M.projects)){
    if (!anyOf(S.f.type, p.project_type)) continue;
    if (!anyOf(S.f.phase, p.clinical_phase)) continue;
    // Schema 7: the scope filter follows work_scope_type, the field the calculation
    // reads. outsourcing_scope_det replaced outsourcing_type and is free text - a
    // drop-down built from whatever sentences people have typed is not a filter.
    if (!anyOf(S.f.out, p.work_scope_type)) continue;
    if (!anyOf(S.f.proj, pid)) continue;
    if (S.f.pers.size && !M.assignments.some(a => a.project_id === pid && S.f.pers.has(a.person_id)))
      continue;
    if (S.f.role.size && !M.assignments.some(a => a.project_id === pid && S.f.role.has(a.role_name)))
      continue;
    if (S.f.dept.size && !M.assignments.some(a => a.project_id === pid &&
        S.f.dept.has((M.people[a.person_id] || {}).department))) continue;
    out.push(pid);
  }
  return out;
}
function activePeople(){
  const M = S.model, projs = new Set(activeProjects()), out = [];
  for (const [sid, p] of Object.entries(M.people)){
    if (!anyOf(S.f.pers, sid)) continue;
    if (!anyOf(S.f.dept, p.department)) continue;
    if (S.f.role.size && !M.assignments.some(a => a.person_id === sid && S.f.role.has(a.role_name)))
      continue;
    if (!M.assignments.some(a => a.person_id === sid && projs.has(a.project_id))) continue;
    out.push(sid);
  }
  return out;
}
/* Everyone the PERSON TAB should list, which is not the same as everyone drawing load.
   activePeople() answers "who is on a project in view" and is what the dashboard needs.
   On a data-entry tab that rule hides the person you have just created, because they
   have no assignment yet - and a row you cannot see is a row you cannot fill in. */
function listedPeople(){
  const M = S.model, out = [];
  for (const [sid, p] of Object.entries(M.people)){
    if (!anyOf(S.f.pers, sid)) continue;
    if (!anyOf(S.f.dept, p.department)) continue;
    if (S.f.role.size && !M.assignments.some(a => a.person_id === sid && S.f.role.has(a.role_name)))
      continue;
    out.push(sid);
  }
  return out;
}
const grid = () => { const g = []; for (let k = S.from; k <= S.to; k++) g.push(k); return g; };

/* Sort order for the project lists: new-drug trials, then biosimilars, then everything
   else. Schema 6 split the biosimilar type in two, so the rank is taken from the START
   of the name rather than from an exact match - otherwise both new types would fall to
   the catch-all and sort after 'Others'. */
const TYPE_RANK = [[/^NewDrug CT/, 0], [/^Biosimilar CT/, 1], [/^Others$/, 2]];
const typeRank = t => (TYPE_RANK.find(([re]) => re.test(String(t ?? ""))) || [null, 9])[1];
function prank(pid){
  const p = S.model.projects[pid];
  return [typeRank(p.project_type), p.start_date ? p.start_date.getTime() : 0, pid];
}
const byRank = (a, b) => { const x = prank(a), y = prank(b);
  return x[0]-y[0] || x[1]-y[1] || (x[2] < y[2] ? -1 : 1); };

