/* ============================================================ 6. calculation
   load = project period weight x (role factor / people sharing the role)
          x person weight x month coverage.

   Pure: no DOM, no file access. Spec sheet 05, verified against the worked example. */

/** The months an assignment covers.
 *
 *  BOTH DATES ARE OPTIONAL, and a blank one means the project's own (REQ-CAL-15).
 *  Most people are on a project for the whole of it; only a partial involvement is
 *  worth writing down, and asking for two dates that simply repeat the project's is
 *  asking somebody to copy the same pair onto every row and to keep them in step
 *  afterwards.
 *
 *  The end date already worked this way. The start did not: a blank one made the
 *  assignment contribute NOTHING, silently, which is the worst of the three possible
 *  behaviours - the row is on screen, the person looks unassigned, and no finding
 *  says why.
 *
 *  One function, called by the sharing pre-pass and by the calculation itself, so the
 *  months a person is counted IN cannot differ from the months they are counted
 *  AMONG. Two copies of this would eventually disagree, and the symptom would be a
 *  role share that does not add up to one. */
function assignmentWindow(M, proj, a){
  const [ps, pe] = projectWindow(M, proj);
  return [a.assign_start_date || ps,
          a.assign_end_date   || pe];
}

/** How long the project runs, for the purpose of working out a number.
 *
 *  THE PERIODS ARE THE PROJECT (REQ-CAL-17). Milestones are reference dates - the
 *  derivation reads them to lay the periods out, and several of them are markers that
 *  sit INSIDE the run rather than bounding it. The periods are the run itself: one
 *  after another, and the only thing any weight in this calculation is attached to.
 *
 *  Taking the window from the milestones instead put the two out of step wherever a
 *  milestone fell outside the periods it produced. Those months belonged to no period,
 *  so periodAt returned nothing and they were costed at weight 1.00 - the project
 *  drawing resource in months its own plan does not cover, and the utilisation chart
 *  growing a flat shoulder at each end that no period justified.
 *
 *  A project with NO periods keeps its own typed dates, because there is nothing to
 *  take a window from and refusing to calculate it at all would be worse: that is a
 *  plan somebody is part way through entering, and V-12 already says so. */
function projectWindow(M, proj){
  let lo = null, hi = null;
  for (const s of ((M && M.periods && M.periods[proj.project_id]) || [])){
    if (s.period_start instanceof Date && (lo === null || s.period_start < lo)) lo = s.period_start;
    if (s.period_end   instanceof Date && (hi === null || s.period_end   > hi)) hi = s.period_end;
  }
  return [lo || proj.start_date, hi || proj.end_date];
}

function monthsBetween(a, b){
  const out = [];
  let y = a.getUTCFullYear(), m = a.getUTCMonth();
  const ey = b.getUTCFullYear(), em = b.getUTCMonth();
  while (y < ey || (y === ey && m <= em)){ out.push([y, m]); if (++m === 12){ m = 0; y++; } }
  return out;
}
function monthKey(y, m){ return y * 12 + m; }
function keyToLabel(k){
  const y = Math.floor(k / 12), m = k % 12;
  return ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][m] + " " + y;
}
function coverage(y, m, s, e){
  const days = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
  const m0 = Date.UTC(y, m, 1), m1 = Date.UTC(y, m, days);
  const lo = Math.max(m0, s.getTime()), hi = Math.min(m1, e.getTime());
  return hi < lo ? 0 : ((hi - lo) / DAY + 1) / days;
}

function calculate(M){
  const projMonth = new Map(), persMonth = new Map(), cell = new Map(), who = new Map();
  // A person-month split by project. persMonth is the total; this is what it is made OF,
  // which is what the person utilisation chart draws and what its pop-up reads.
  const persProj = new Map();          // person|month -> Map(project_id -> FTE)
  const projPers = new Map();          // project|month -> Map(person_id -> FTE)
  const add = (map, k, v) => map.set(k, (map.get(k) || 0) + v);

  const periodAt = (pid, y, m) => {
    const first = Date.UTC(y, m, 1);
    for (const s of (M.periods[pid] || [])){
      if (!s.period_start || !s.period_end) continue;   // an incomplete row has no window
      if (s.period_start.getTime() <= first && first <= s.period_end.getTime()) return s;
    }
    return null;
  };
  const personWeight = (a, y, m) => {
    const first = Date.UTC(y, m, 1);
    for (const w of (M.ppw[a.assignment_id] || [])){
      if (!w.period_start || !w.period_end) continue;   // an incomplete row has no window
      if (w.period_start.getTime() <= first && first <= w.period_end.getTime())
        return num(w.weight_override) ?? 0;
    }
    return num(a.person_weight) ?? 0;
  };

  /* ---------------------------------------------- who shares a role, and when
     The role factor is what the ROLE costs the project in a period - not what each
     person holding it costs. Put two data managers on one trial and the old
     arithmetic charged the project for two full data managers, so the same work
     appeared to cost twice as much simply because it was staffed by two people.

     So the factor is divided between the people holding that role on that project.
     Counted PER MONTH rather than once per assignment, because that is the only
     count that conserves the total: when one of two sharers leaves in June, July
     must return to a full share by itself, without anybody editing anything.

     Distinct PEOPLE, not rows - two rows for one person on the same project and
     role are one person doing one job, and must not halve their own load. Anyone
     whose assignment touches the month counts as a sharer for that month; a
     part-month sharer already contributes less through their own coverage. */
  /* Built ALWAYS, and read two ways. How many people hold a role in a month is the
     divisor; WHETHER anybody holds it is what decides absorption (REQ-CAL-16). One
     pass, so the two answers cannot come from different pictures of the same month. */
  const sharers = new Map();                       // project|role|month -> Set(person)
  const roleKey = (pid, role, k) => pid + "\u0000" + role + "\u0000" + k;
  const shareKey = (a, k) => roleKey(a.project_id, a.role_name, k);
  for (const a of M.assignments){
    const proj = M.projects[a.project_id];
    if (!proj || !M.people[a.person_id] || a.__bad || a.__new) continue;
    const [s, e] = assignmentWindow(M, proj, a);
    if (!s || !e) continue;
    for (const [y, m] of monthsBetween(s, e)){
      if (coverage(y, m, s, e) <= 0) continue;
      const kk = shareKey(a, monthKey(y, m));
      if (!sharers.has(kk)) sharers.set(kk, new Set());
      sharers.get(kk).add(a.person_id);
    }
  }
  const shareCount = (a, k) =>
    M.SPLIT ? ((sharers.get(shareKey(a, k)) || {size:1}).size || 1) : 1;
  const staffed = (pid, role, k) => sharers.has(roleKey(pid, role, k));

  /** The factor this role carries THIS MONTH: its own, plus the factor of any role
   *  that names it as cover and that nobody is holding (REQ-CAL-16).
   *
   *  A trial run without a Clinical Data Associator still has the data to handle. It
   *  lands on the lead data manager, who is then under more pressure than the factor
   *  for their own role alone describes - and the project, costed without it, looks
   *  cheaper than it is. That is the under-estimate this corrects.
   *
   *  Per month, like everything else here: a role staffed from March is absent in
   *  February, and the cover ends when somebody arrives, with nobody editing anything.
   *
   *  ONE HOP, deliberately. If the absorbing role is itself unstaffed the work is not
   *  passed further along - there is nobody to pass it to, and a chain would quietly
   *  pile three absent roles onto whoever happened to be left. V-29 reports that case
   *  rather than inventing an answer for it. */
  function effectiveFactor(proj, periodName, roleName, k){
    let rf = stdFactor(M, proj, periodName, roleName) ?? 1;
    if (!M.ABSORB) return rf;
    for (const absent of absorbedInto(M, proj, periodName, roleName)){
      if (staffed(proj.project_id, absent, k)) continue;      // somebody is doing it
      rf += stdFactor(M, proj, periodName, absent) ?? 0;
    }
    return rf;
  }

  /* ---------------------------------------------------- V-23, from the arithmetic
     A missing role factor is not a fact about the RoleFactor sheet; it is something
     that happened to a number. So it is recorded here, as it happens, by the exact
     composition the lookup used - project type, clinical phase, work scope, period
     name, role - and only where the lookup actually fed a person-month.

     Asked the other way round, as it used to be, the answer was wrong twice over: it
     walked every period of the project rather than the months an assignment reaches,
     so it reported combinations no figure ever needed; and it ran before the
     calculation, which made it an error about the DATA and therefore something that
     could refuse an edit. It is neither. It is the calculation reporting what it had
     to guess at. */
  const gaps = new Map();
  const noteGap = (proj, pn, role, pid) => {
    const key = [proj.project_type, proj.clinical_phase || "", scopeOf(proj) || "",
                 pn, role].join(" ");
    let g = gaps.get(key);
    if (!g) gaps.set(key, g = {proj, periodName:pn, role, projects:new Set(), months:0});
    g.projects.add(pid);
    g.months++;
  };

  let lo = Infinity, hi = -Infinity;
  for (const a of M.assignments){
    const proj = M.projects[a.project_id];
    if (!proj || !M.people[a.person_id] || a.__bad) continue;
    const [s, e] = assignmentWindow(M, proj, a);
    // Only a row still being typed, or a project with no dates of its own, contributes
    // nothing now - a blank assignment date means the project's, not zero.
    if (!s || !e || a.__new) continue;
    for (const [y, m] of monthsBetween(s, e)){
      const cov = coverage(y, m, s, e);
      if (cov <= 0) continue;
      const seg = periodAt(a.project_id, y, m);
      const pw = seg ? (num(seg.weight) ?? 1) : 1;                       // no period -> 1.00, V-12
      // Schema 6: the project's own work scope first, then the any-scope row. One
      // function, shared with the validation, so the figure and the finding agree.
      const k = monthKey(y, m);
      // A month in no period at all is V-12's finding, not this one - there is no period
      // name to be missing a factor FOR, and saying both would be saying it twice.
      if (seg && stdFactor(M, proj, seg.period_name, a.role_name) === undefined)
        noteGap(proj, seg.period_name, a.role_name, a.project_id);
      const rf = effectiveFactor(proj, seg ? seg.period_name : null, a.role_name, k);
      const share = shareCount(a, k);       // how many people hold this role this month
      const v = pw * (rf / share) * personWeight(a, y, m) * cov;
      lo = Math.min(lo, k); hi = Math.max(hi, k);
      add(projMonth, a.project_id + "|" + k, v);
      add(persMonth, a.person_id + "|" + k, v);
      add(cell, [a.project_id, a.person_id, a.role_name, k].join("|"), v);
      const pk = a.person_id + "|" + k;
      if (!persProj.has(pk)) persProj.set(pk, new Map());
      const byp = persProj.get(pk);
      byp.set(a.project_id, (byp.get(a.project_id) || 0) + v);
      const qk = a.project_id + "|" + k;                 // the same split seen the other way
      if (!projPers.has(qk)) projPers.set(qk, new Map());
      const bys = projPers.get(qk);
      bys.set(a.person_id, (bys.get(a.person_id) || 0) + v);
      const wk = a.project_id + "|" + k;
      if (!who.has(wk)) who.set(wk, []);
      who.get(wk).push([a.person_id, a.role_name]);
    }
  }
  reportGaps(M, gaps);
  return {projMonth, persMonth, persProj, projPers, cell, who, sharers, shareCount,
          staffed, effectiveFactor, gaps,
          lo:isFinite(lo)?lo:0, hi:isFinite(hi)?hi:0};
}

/** V-23, written onto the model once the calculation knows what it needed.
 *
 *  Rewritten so the SAME model can be calculated twice without the finding appearing
 *  twice: the previous set is dropped first. Every other finding is produced once, by
 *  buildModel; this one is produced by whoever calls calculate, and that is not always
 *  exactly once.
 *
 *  Still an ERROR, because the figures really are wrong - a role calculated at 1.00 is
 *  not an approximation of the right answer, it is a different answer. What changed is
 *  only where it comes from, and therefore what it can do: a finding that exists only
 *  after the arithmetic cannot refuse the edit that led to it. */
function reportGaps(M, gaps){
  if (!M || !Array.isArray(M.findings)) return;
  for (let i = M.findings.length - 1; i >= 0; i--)
    if (M.findings[i].rule === "V-23") M.findings.splice(i, 1);
  for (const g of [...gaps.values()].sort((a, b) => a.months - b.months)){
    const ph = CLINICAL_TYPES.has(g.proj.project_type) ? g.proj.clinical_phase : null;
    const pl = [...g.projects];
    M.findings.push({sev:"error", rule:"V-23", sheet:"RoleFactor", row:"",
      msg:`No role factor for ${g.proj.project_type} / ${ph || "-"} / `
        + `${g.proj.work_scope_type || "any scope"} / ${g.periodName} / ${g.role} — `
        + `${g.months} person-month(s) on ${pl.length} project(s) `
        + `(${pl.slice(0, 3).join(", ")}${pl.length > 3 ? ", …" : ""}) were calculated at `
        + `factor 1.00 instead. Add a row for that scope, or one with work_scope_type `
        + `empty to cover every scope. Your data is kept either way — this says the `
        + `figures are short of an assumption, not that the rows are wrong.`});
  }
}

