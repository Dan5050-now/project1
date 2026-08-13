/* ============================================================ 6. calculation
   load = project period weight x role factor x person weight x month coverage.
   Pure: no DOM, no file access. Spec sheet 05, verified against the worked example. */

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

  let lo = Infinity, hi = -Infinity;
  for (const a of M.assignments){
    const proj = M.projects[a.project_id];
    if (!proj || !M.people[a.person_id] || a.__bad) continue;
    const s = a.assign_start_date, e = a.assign_end_date || proj.end_date;
    if (!s || !e || a.__new) continue;              // an incomplete row contributes nothing
    const ph = CLINICAL_TYPES.has(proj.project_type) ? proj.clinical_phase : null;
    for (const [y, m] of monthsBetween(s, e)){
      const cov = coverage(y, m, s, e);
      if (cov <= 0) continue;
      const seg = periodAt(a.project_id, y, m);
      const pw = seg ? (num(seg.weight) ?? 1) : 1;                       // no period -> 1.00, V-12
      const rf = M.rf[[proj.project_type, ph, seg ? seg.period_name : null, a.role_name]] ?? 1;
      const v = pw * rf * personWeight(a, y, m) * cov;
      const k = monthKey(y, m);
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
  return {projMonth, persMonth, persProj, projPers, cell, who,
          lo:isFinite(lo)?lo:0, hi:isFinite(hi)?hi:0};
}

