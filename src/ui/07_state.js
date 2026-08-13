/* ============================================================ 7. state + filters */

const S = {
  model:null, calc:null, fileName:"", loadedAt:null, blank:false,
  from:null, to:null,                       // month keys
  // Each filter holds a SET of chosen values. Empty means "All" - which is both the
  // natural reading of "nothing narrowed" and what keeps every predicate below short.
  f:{type:new Set(), phase:new Set(), out:new Set(), proj:new Set(),
     pers:new Set(), role:new Set(), dept:new Set()},
  tab:"t-overall", expanded:new Set(), selProj:null, selPers:null, selAsg:null,
  pending:[], saved:0, snapshot:null, editedCells:new Set(), headers:{},
  genView:{pws:"matrix", rf:"matrix", lists:"matrix"},
};

/** A filter with nothing ticked narrows nothing. */
const anyOf = (set, v) => !set.size || set.has(v);

function activeProjects(){
  const M = S.model, out = [];
  for (const [pid, p] of Object.entries(M.projects)){
    if (!anyOf(S.f.type, p.project_type)) continue;
    if (!anyOf(S.f.phase, p.clinical_phase)) continue;
    if (!anyOf(S.f.out, p.outsourcing_type)) continue;
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

const TYPE_RANK = {"NewDrug CT":0, "Biosimilar CT":1, "Others":2};
function prank(pid){
  const p = S.model.projects[pid];
  return [TYPE_RANK[p.project_type] ?? 9, p.start_date ? p.start_date.getTime() : 0, pid];
}
const byRank = (a, b) => { const x = prank(a), y = prank(b);
  return x[0]-y[0] || x[1]-y[1] || (x[2] < y[2] ? -1 : 1); };

