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

  /* Which roles are staffed on a project in a month, so the demand can be divided
     between them. Built from the same `sharers` pass as the divisor and the absorption
     test, for the same reason those two share it: three answers about one month must
     come from one picture of that month. */
  const rolesOn = new Map();                       // project|month -> Set(role)
  for (const kk of sharers.keys()){
    const [pid, role, k] = kk.split("\u0000");
    const q = pid + "\u0000" + k;
    if (!rolesOn.has(q)) rolesOn.set(q, new Set());
    rolesOn.get(q).add(role);
  }

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

  /** The month's demand in FTE, before this project's own adjustment (REQ-CAL-19).
   *
   *  PeriodWeightStandard holds it. The column is named `standard_fte` because that is
   *  what it is - a monthly FTE for a project of this type, phase and scope in this
   *  period - and it was called `weight` until schema 10, which is most of why it went
   *  unused for so long: a "weight" reads like something to multiply by, so the
   *  calculation multiplied by the PROJECT's weight and never asked the standards sheet
   *  anything at all. Every figure the application produced was therefore a relative
   *  shape with no magnitude behind it.
   *
   *  Missing, it falls back to 1.00 and V-19 reports it. That fallback is deliberately
   *  the OLD behaviour - the project month becomes its own period weight, exactly as
   *  before - so a file whose standards are incomplete degrades to figures its author
   *  will recognise rather than to zero. */
  const stdCache = new Map();
  function stdMonthly(proj, periodName){
    if (periodName === null || periodName === undefined) return 1;
    const key = proj.project_id + "\u0000" + periodName;
    if (stdCache.has(key)) return stdCache.get(key);
    const v = num(stdWeight(M, proj, periodName));
    const out = (v === null || v === undefined) ? 1 : v;
    stdCache.set(key, out);
    return out;
  }

  /** What the staffed roles add up to this month - the denominator the demand is
   *  divided by, so the shares come to one.
   *
   *  Summed over DISTINCT ROLES, not over people: the factor states what the role costs
   *  the project, and two people holding one role split that role's share rather than
   *  claiming it twice. Each role is counted at its EFFECTIVE factor, so a role covering
   *  for an absent one (REQ-CAL-16) is bigger here as well as in the numerator - the
   *  absorbed work moves to whoever covers it instead of spreading over everybody. */
  const demandCache = new Map();
  function roleDemand(proj, periodName, pid, k){
    const key = pid + "\u0000" + k;
    if (demandCache.has(key)) return demandCache.get(key);
    let t = 0;
    for (const role of (rolesOn.get(pid + "\u0000" + k) || []))
      t += effectiveFactor(proj, periodName, role, k);
    demandCache.set(key, t);
    return t;
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
  /* Every term of every person-month, kept as it is worked out.
     The results export has to be able to say HOW a figure was reached, and the only
     honest way to answer that is to record what the arithmetic actually used. Asked
     again afterwards, from the sheets, the explanation could drift from the figure it
     claims to explain - which is the one thing an export like this must never do. */
  const lines = [];

  const gaps = new Map();
  const noteGap = (proj, pn, role, pid) => {
    const key = [proj.project_type, proj.clinical_phase || "", scopeOf(proj) || "",
                 pn, role].join("\u0000");
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
      /* REQ-CAL-19. The STANDARD is the month's demand in FTE - what a project of this
         type, phase and scope takes in this period - and the project's own period weight
         adjusts it up or down for this particular study. The role factors then divide
         that demand between the roles ACTUALLY STAFFED, so the shares add to one and the
         project month equals the standard however many people are on it. An unstaffed
         role is not in the denominator, so its work lands on the others rather than
         disappearing; REQ-CAL-16 still decides WHERE it lands when a role names cover. */
      const denom = roleDemand(proj, seg ? seg.period_name : null, a.project_id, k);
      const stdF = stdMonthly(proj, seg ? seg.period_name : null);
      const frac = denom > 0 ? (rf / share) / denom : 0;
      const v = stdF * pw * frac * personWeight(a, y, m) * cov;
      lo = Math.min(lo, k); hi = Math.max(hi, k);

      const own = seg ? stdFactor(M, proj, seg.period_name, a.role_name) : undefined;
      const ppw = (M.ppw[a.assignment_id] || []).find(w =>
        w.period_start && w.period_end
        && w.period_start.getTime() <= Date.UTC(y, m, 1)
        && Date.UTC(y, m, 1) <= w.period_end.getTime());
      lines.push({
        month:k, project_id:a.project_id, person_id:a.person_id,
        assignment_id:a.assignment_id, role_name:a.role_name,
        period_name: seg ? seg.period_name : null,
        period_weight: pw, period_weight_source: seg ? "ProjectPeriod" : "none — V-12",
        standard_fte: stdF, role_share: frac,
        roles_staffed: (rolesOn.get(a.project_id + "\u0000" + k) || new Set()).size,
        role_factor: own, role_factor_effective: rf,
        absorbed: M.ABSORB && seg
          ? absorbedInto(M, proj, seg.period_name, a.role_name)
              .filter(r => !staffed(a.project_id, r, k))
          : [],
        sharers: share,
        person_weight: personWeight(a, y, m),
        person_weight_source: ppw ? "PersonPeriodWeight override" : "Assignment",
        coverage: cov, fte: v, auto: v, source: "automatic",
      });
    }
  }
  applyManual(M, lines);

  /* Every map is built HERE, from the lines, rather than accumulated as the lines were
     produced. Two things depend on it and neither would survive the maps being filled
     in first: a manual figure has to be able to change what the totals say, and the
     results export claims that every total is exactly the sum of its detail rows. Both
     are true by construction this way and would have to be maintained by hand the
     other way. */
  for (const L of lines){
    const k = L.month, v = L.fte;
    add(projMonth, L.project_id + "|" + k, v);
    add(persMonth, L.person_id + "|" + k, v);
    add(cell, [L.project_id, L.person_id, L.role_name, k].join("|"), v);
    const pk = L.person_id + "|" + k;
    if (!persProj.has(pk)) persProj.set(pk, new Map());
    persProj.get(pk).set(L.project_id, (persProj.get(pk).get(L.project_id) || 0) + v);
    const qk = L.project_id + "|" + k;
    if (!projPers.has(qk)) projPers.set(qk, new Map());
    projPers.get(qk).set(L.person_id, (projPers.get(qk).get(L.person_id) || 0) + v);
    if (!who.has(qk)) who.set(qk, []);
    who.get(qk).push([L.person_id, L.role_name]);
  }

  reportGaps(M, gaps);
  reportManual(M, lines);
  return {projMonth, persMonth, persProj, projPers, cell, who, sharers, shareCount,
          staffed, effectiveFactor, gaps, lines,
          lo:isFinite(lo)?lo:0, hi:isFinite(hi)?hi:0};
}

/** V-31 and V-32: what a manual figure could not do.
 *
 *  Both are raised from the calculation for the same reason V-23 is - they are things
 *  that happened to a number, not facts about a sheet, and asking the sheets afterwards
 *  could produce an explanation that does not match the figure on screen. Rewritten
 *  each time so calculating twice does not report twice. */
function reportManual(M, lines){
  if (!M || !Array.isArray(M.findings)) return;
  for (let i = M.findings.length - 1; i >= 0; i--)
    if (M.findings[i].rule === "V-31" || M.findings[i].rule === "V-32") M.findings.splice(i, 1);

  const strays = M.__manualStrays || [];
  if (strays.length){
    const by = new Map();
    for (const [scope, id, mon] of strays){
      const k = scope + "|" + id;
      if (!by.has(k)) by.set(k, []);
      by.get(k).push(mon);
    }
    for (const [k, months] of by){
      const [scope, id] = k.split("|");
      M.findings.push({sev:"error", rule:"V-31", sheet:"MonthlyEstimate", row:"",
        msg:`${scope === "project" ? "Project" : "Assignment"} ${id} is set to MANUAL `
          + `but MonthlyEstimate has no figure for ${months.length} of its month(s): `
          + `${months.slice(0, 6).join(", ")}${months.length > 6 ? ", …" : ""}. Those `
          + `months are counted as 0.00. Switching to manual copies every calculated `
          + `month across, so a month with no figure is one that has since been removed `
          + `— put it back, or switch this back to automatic.`});
    }
  }

  // A project figure nobody can carry.
  const iso = k => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
  const carried = new Set();
  for (const L of lines) carried.add(L.project_id + "|" + iso(L.month));
  const orphan = new Map();
  for (const key of Object.keys(M.manual || {})){
    const [scope, id, mon] = key.split("|");
    if (scope !== "project" || !M.isManual("project", id)) continue;
    if (!(num(M.manual[key]) > 0)) continue;
    if (carried.has(id + "|" + mon)) continue;
    if (!orphan.has(id)) orphan.set(id, []);
    orphan.get(id).push(mon);
  }
  for (const [id, months] of orphan)
    M.findings.push({sev:"error", rule:"V-32", sheet:"MonthlyEstimate", row:"",
      msg:`Project ${id} has a manual figure for ${months.length} month(s) `
        + `(${months.slice(0, 6).join(", ")}${months.length > 6 ? ", …" : ""}) in which `
        + `nobody is assigned to it. A project's month is shared out among the people on `
        + `it, so there is nobody to give this to and it has NOT been applied — the `
        + `project would otherwise show a total that none of its people account for. `
        + `Assign somebody to those months, or remove the figure.`});
}

/* ================================================ manual figures (REQ-CAL-18)

   Sometimes the assumptions are not the best information available. A trial two years
   in has a manager who knows what it actually takes, and a standard weight multiplied
   by a standard factor is a worse answer than the one in their head. So a project or an
   assignment can be set to MANUAL, and its monthly figures are then stated rather than
   worked out.

   MANUAL IS ALL-OR-NOTHING for the thing it is set on, and that is the user's own
   decision recorded in the plan: switching to manual copies every calculated month
   across first, so the figures do not jump and there is no such thing as a half-manual
   run. Nothing has to remember which months were touched, no month carries its own
   flag, and switching back discards the lot. What the user takes on in exchange is
   responsibility for all of them, which the application says when it asks.

   TWO LEVELS, applied in that order:

     ASSIGNMENT   the figure IS that person's contribution to that project. It replaces
                  the multiplication outright.
     PROJECT      the figure is the project's whole month, and the people on it are
                  SCALED so they still add up to it. A project total that did not equal
                  the sum of its people would put the two utilisation charts in
                  disagreement and cost the results export its one real guarantee - and
                  the scaling factor is recorded on every line, so a person can always
                  find out why their figure moved.

   A project figure with nobody assigned that month cannot be distributed to anybody, so
   it is NOT applied - V-32 reports it rather than the application inventing a carrier
   for the work or quietly breaking the sum. */
function applyManual(M, lines){
  if (!M.manual) return;
  const iso = k => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
  const strays = [];

  // ---- assignment level ----------------------------------------------------
  for (const L of lines){
    if (!M.isManual("assignment", L.assignment_id)) continue;
    const key = `assignment|${L.assignment_id}|${iso(L.month)}`;
    const v = M.manual[key];
    L.manual_assignment = true;
    if (v === undefined || v === null){
      strays.push(["assignment", L.assignment_id, iso(L.month)]);
      L.fte = 0;
      L.source = "manual (assignment) — NO FIGURE GIVEN";
    } else {
      L.fte = v;
      L.source = "manual (assignment)";
      L.manual_at = M.manualAt[key] ?? null;
    }
  }

  // ---- project level, on top ------------------------------------------------
  const byProjMonth = new Map();
  for (const L of lines){
    if (!M.isManual("project", L.project_id)) continue;
    const k = L.project_id + "|" + L.month;
    if (!byProjMonth.has(k)) byProjMonth.set(k, []);
    byProjMonth.get(k).push(L);
  }
  for (const [k, group] of byProjMonth){
    const [pid, mk] = [k.slice(0, k.lastIndexOf("|")), +k.slice(k.lastIndexOf("|") + 1)];
    const key = `project|${pid}|${iso(mk)}`;
    const want = M.manual[key];
    for (const L of group) L.manual_project = true;
    if (want === undefined || want === null){
      strays.push(["project", pid, iso(mk)]);
      for (const L of group){ L.fte = 0; L.source = "manual (project) — NO FIGURE GIVEN"; }
      continue;
    }
    const have = group.reduce((t, L) => t + L.fte, 0);
    if (Math.abs(have) < 1e-9){
      // Nobody to give it to. Reported by V-32; the figure is not applied, because the
      // alternative is a project total no person on the project accounts for.
      continue;
    }
    const scale = want / have;
    for (const L of group){
      L.fte *= scale;
      L.project_scale = scale;
      L.manual_project_total = want;
      L.source = L.manual_assignment ? "manual (assignment, scaled to the project figure)"
                                     : "manual (project, shared out)";
      L.manual_at = M.manualAt[key] ?? L.manual_at ?? null;
    }
  }
  M.__manualStrays = strays;
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

