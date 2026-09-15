/* ============================================================ 6. calculation
   A PROJECT-MONTH is    standard FTE x period weight x the part of the month it runs.
   A PERSON-MONTH  is    that month x this person's share of it, where the share is
                         (role factor / sharers) x person weight x coverage, measured
                         against everyone else's on the same project-month.

   The four factors decide a SHARE, not a total: they divide the month between the
   people on it rather than each adding to it (REQ-CAL-19 as amended by R-32). See
   shareOut() at the foot of this file for why.

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
const isoOf = k => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
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
  /* project|month -> the period that month falls in. Built from the LINES like every
     other map here, not looked up again with periodAt(): the period is what selected the
     standard FTE and the weight behind the figure, so reading it from anywhere else
     would let a tooltip name one period while the number beside it came from another.
     The WEIGHT comes with the name because the two are one fact: the period is which
     row of the plan applied, and the weight is what that row did to the figure. Naming
     the period without it answers half the question a reader is asking.

     Null where the month belongs to no period - V-12 reports that, and the charts say
     so rather than leaving a gap that reads as a defect in the chart. */
  const projPeriod = new Map();
  // project|month -> the DEMAND, which is what the project needs rather than what it is
  // getting. Taken off the lines like everything else here, so the figure V-34 compares
  // against is the one the arithmetic itself worked out.
  const projDemand = new Map();
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

  /** The month's demand in FTE, before this project's own adjustment (REQ-CAL-19).
   *
   *  PeriodFTEStandard holds it. The column is named `standard_fte` because that is
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
      const stdF = stdMonthly(proj, seg ? seg.period_name : null);
      /* The person's CLAIM on the month, not yet their figure. Normalising it against
         everybody else's happens once the whole project-month is known, in the second
         pass below - a share cannot be worked out from one line, because it is a
         proportion of the others. */
      const claim = (rf / share) * personWeight(a, y, m) * cov;
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
        standard_fte: stdF, claim,
        role_factor: own, role_factor_effective: rf,
        absorbed: M.ABSORB && seg
          ? absorbedInto(M, proj, seg.period_name, a.role_name)
              .filter(r => !staffed(a.project_id, r, k))
          : [],
        sharers: share,
        person_weight: personWeight(a, y, m),
        person_weight_source: ppw ? "PersonPeriodWeight override" : "Assignment",
        coverage: cov, fte: 0, auto: 0, source: "automatic",
      });
    }
  }
  shareOut(lines);
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
    if (!projPeriod.has(qk))
      projPeriod.set(qk, L.period_name ? {name:L.period_name, weight:L.period_weight} : null);
    if (!projDemand.has(qk)) projDemand.set(qk, L.demand_fte ?? 0);
  }

  /* WHAT THE PROJECT NEEDS AGAINST WHAT IT IS BEING GIVEN (V-34).
     These are the two figures that can come apart, and until now nothing said when they
     had. The pair people reach for first - the project's month against the sum of its
     people - CANNOT differ: projMonth is built from the lines a few lines above, so it
     is that sum by construction (REQ-OUT-06). The real pair is DEMAND against APPLIED.
     An all-automatic month has them equal, because shareOut hands out exactly the
     demand's hundredths and the shares add to one (REQ-CAL-19). A manual figure at
     either level breaks that, deliberately, and the application then simply drew a
     smaller project: a study needing 10.00 and staffed at 5.00 looked exactly like a
     study that only ever needed 5.00. That is the thing worth reporting - not an
     arithmetic fault, but a plan that has quietly stopped matching its own standard. */
  const projGap = new Map();
  for (const [qk, applied] of projMonth){
    const demand = projDemand.get(qk);
    if (demand === undefined) continue;
    const cents = toCents(applied) - toCents(demand);
    if (cents === 0) continue;
    projGap.set(qk, {demand, applied, gap: fromCents(cents),
                     dir: cents < 0 ? "short" : "over"});
  }

  /* V-36: what a project with NOBODY on it needs. Worked out here rather than in the
     validation for the same reason V-34 is - it is a figure, and the figure has to come
     from the arithmetic that would produce it, not from a second lookup that could
     drift from it. Every term below is the one an assignment with blank dates would
     get: projectWindow is what assignmentWindow falls back to, and the product is the
     one shareOut computes. So the number this rule reports is, to the hundredth, the
     number the project shows the moment somebody is assigned to it. */
  /* ASSIGNMENT ROWS, not lines. A project whose only assignments are broken is reported
     by the rule that broke them; adding this on top would be saying the same thing
     twice, and V-36 means one thing only - nobody has been assigned. Gathered in ONE
     pass rather than asked per project: the question is asked once for every project,
     and scanning the assignments inside that loop would be the product of the two. */
  const hasAssignment = new Set();
  for (const a of M.assignments) if (!a.__new) hasAssignment.add(a.project_id);

  /** Every month this project's own plan asks for, and what it asks for - from the
   *  PERIODS ALONE, with no reference to who is on it (REQ-CAL-19: the project-month IS
   *  its standard, and the people on it divide it).
   *
   *  ONE function, used by the rule that reports the demand and by the table that draws
   *  it. Two copies would eventually disagree, and the symptom would be a screen whose
   *  figure contradicts the finding sitting beside it - which is the class of defect
   *  this whole application is arranged to make impossible. */
  const projectDemand = (pid, proj) => {
    const out = [];
    const [ps, pe] = projectWindow(M, proj);
    if (!ps || !pe) return out;
    for (const [y, m] of monthsBetween(ps, pe)){
      const cov = coverage(y, m, ps, pe);
      if (cov <= 0) continue;
      const seg = periodAt(pid, y, m);
      const d = fromCents(toCents(stdMonthly(proj, seg ? seg.period_name : null)
                                 * (seg ? (num(seg.weight) ?? 1) : 1) * cov));
      if (d > 0) out.push([monthKey(y, m), d]);
    }
    return out;
  };

  /* WHAT THE PLAN ASKS FOR IN A MONTH NOBODY IS ON (R-49).
     Filled in ONLY where the calculation produced no figure at all. Where a month HAS
     lines, its demand is already projDemand, taken off those lines, and that figure
     stays exactly as it was - the two are not always equal, because the month_run a
     line carries is the greatest COVERAGE any assignment has in that month, while this
     is the project's own run. Recomputing a month that already has a figure would move
     numbers that nobody asked to move; filling in one that has none moves nothing. */
  const projUnallocated = new Map();          // project|month -> demand nobody is on

  const unstaffed = [];
  for (const [pid, proj] of Object.entries(M.projects || {})){
    if (proj.__bad || proj.__new) continue;
    // A project with no periods has no demand to state, and V-12 or V-16 already says
    // so. Inventing a figure for it would be worse than saying nothing.
    if (!((M.periods && M.periods[pid]) || []).length) continue;
    const months = projectDemand(pid, proj);

    for (const [k, d] of months){
      const qk = pid + "|" + k;
      // A month that already carries a figure keeps it, whatever this says.
      if (toCents(projMonth.get(qk) || 0) > 0) continue;
      projUnallocated.set(qk, d);
      lo = Math.min(lo, k); hi = Math.max(hi, k);
    }

    // ...and V-36 on top, for the project that has nobody on it at ALL.
    if (hasAssignment.has(pid)) continue;
    // Completed work that nobody was ever booked to is history, not a gap to fill. The
    // class of this rule is INCOMPLETE - "still being built, and the finding will
    // answer itself" - which a finished project will never do.
    if (String(proj.status || "").trim() === "Completed") continue;
    let total = 0, peak = 0, peakMonth = null, firstMonth = null;
    for (const [k, d] of months){
      total = fromCents(toCents(total) + toCents(d));
      if (firstMonth === null) firstMonth = isoOf(k);
      if (d > peak){ peak = d; peakMonth = isoOf(k); }
    }
    if (months.length)
      unstaffed.push({pid, months: months.length, total, peak, peakMonth, firstMonth});
  }

  reportGaps(M, gaps);
  reportManual(M, lines);
  reportDemandGap(M, projGap);
  reportUnstaffed(M, unstaffed);
  /* periodAt is handed out for the SAME reason projPeriod is built from the lines: so a
     screen naming the period a month falls in cannot name a different one from the
     period the figure used. projPeriod answers it for every month that produced a
     figure, which is nearly all of them; periodAt answers it for the months that did
     not - a manual project month with nobody assigned to it (V-32) has a stated figure
     and no line to read a period off. Two answers from one function rather than one
     answer and a second lookup that could drift from it. */
  return {projMonth, persMonth, persProj, projPers, cell, who, projPeriod, projGap,
          projUnallocated,
          sharers, periodAt, shareCount, staffed, effectiveFactor, gaps, lines,
          lo:isFinite(lo)?lo:0, hi:isFinite(hi)?hi:0};
}

/* ================================ the demand, shared out (REQ-CAL-19)

   A PROJECT-MONTH IS ITS STANDARD. standard_fte says what a project of this type, phase
   and work scope takes in this period, ProjectPeriod.weight adjusts it for this
   particular study, and that product is the month - not a ceiling it might reach, and
   not a figure the staffing can quietly reduce.

   So the people on it DIVIDE that month rather than each contributing to it. Everything
   that used to reduce the total now decides a share instead:

     role factor      what this role costs the project, relative to the other roles
     / sharers        two people holding one role hold it between them
     x person weight  a half-time commitment is half a claim on the month
     x coverage       somebody present for ten days has a tenth of a claim

   Those four make a CLAIM; the claim divided by the sum of the claims is the SHARE; the
   share times the demand is the figure. The shares add to one by construction, so the
   month always comes to the standard and the two utilisation charts cannot disagree.

   WHAT THIS MEANS, and it is the whole of the trade: a part-time person no longer makes
   the project cheaper, they push load onto whoever else is there. Under-staffing shows
   up on the PEOPLE, as months over the ceiling, and never as a project that costs less
   than the work it contains. That is the reading the reviewer chose; the alternative -
   where person_weight scales the month down and the shortfall is visible as a gap - is
   recorded in the plan against R-32 so the choice can be revisited without re-deriving
   it.

   THE DEMAND IS SCALED BY THE MONTH THE PROJECT ACTUALLY RUNS, taken as the largest
   coverage any of its people have. A project whose period ends on the 10th draws a third
   of a month, not a whole one; a project running all month draws all of it however
   part-time the people on it are. Without this every project would spike to a full
   standard month in the month it opened and the month it closed. */
/* ================================ THE DECIMAL RULE (REQ-CAL-20)

   EVERY FTE FIGURE THIS APPLICATION PRODUCES IS A WHOLE NUMBER OF HUNDREDTHS.

   Not "displayed to two places" - IS. The rounding happens once, here, at the moment a
   person-month is decided, and every later reader sees the same number: the screen, the
   results export, the change log, the four independent implementations. A figure shown
   as 4.27 was 4.27 when it was worked out, not 4.2683 dressed up for the table.

   Two places because that is the granularity the plan is written in. At 160 hours to the
   FTE, 0.01 is 1.6 hours - the smallest edit that means anything to somebody staffing a
   study, and already the granularity a manual estimate is typed at (REQ-CAL-18). Keeping
   four places in the file was keeping precision the inputs never had.

   ROUNDING EACH SHARE INDEPENDENTLY WOULD NOT DO. Round 4.27/3 three times and the parts
   come to 4.26 or 4.29, never reliably to 4.27 - so the detail rows would stop summing to
   the month above them (REQ-OUT-06) and the shares would stop adding to one (REQ-CAL-19).
   On the 62-project fixture that missed on 644 of 1,629 project-months.

   So the month is rounded FIRST and its hundredths are then handed out: each line takes
   its floor, and the hundredths left over go to the lines with the largest remainders,
   one each. That is the largest-remainder method, and it makes both guarantees exact by
   construction rather than by tolerance.

   THE TIE-BREAK IS PART OF THE RULE, not an implementation detail. Four programs compute
   these figures and they must agree to the hundredth, so where two remainders are equal
   the extra hundredth goes to the line whose assignment_id sorts first - a total order
   that does not depend on array order, hash order, or the order rows happened to be read
   from a sheet. Without it two implementations could differ by 0.01 and both be "right".

   Integers throughout: hundredths are counted, never accumulated as fractions, so the
   arithmetic here cannot itself introduce the error it exists to remove. */
const CENTS = 100;
const toCents = v => Math.round((v || 0) * CENTS);
const fromCents = c => c / CENTS;

/** Share `totalCents` hundredths among `items` in proportion to `weight`, exactly.
 *  Returns cents per item, summing to totalCents with no residue. */
function largestRemainder(items, totalCents){
  const n = items.length;
  if (!n) return [];
  if (totalCents <= 0) return items.map(() => 0);
  const sum = items.reduce((t, it) => t + (it.weight > 0 ? it.weight : 0), 0);
  if (!(sum > 0)) return items.map(() => 0);
  const exact = items.map(it => (it.weight > 0 ? it.weight : 0) / sum * totalCents);
  const out = exact.map(v => Math.floor(v));
  let left = totalCents - out.reduce((a, b) => a + b, 0);
  // Biggest remainder first; ties by the caller's key, which is a total order.
  const order = items.map((it, i) => i).sort((a, b) => {
    const ra = exact[a] - out[a], rb = exact[b] - out[b];
    if (rb !== ra) return rb - ra;
    return items[a].key < items[b].key ? -1 : items[a].key > items[b].key ? 1 : 0;
  });
  // `left` can exceed the number of lines only if the weights are degenerate; going
  // round again rather than stopping keeps the total exact in that case too.
  for (let i = 0; left > 0; i++, left--) out[order[i % n]]++;
  return out;
}

function shareOut(lines){
  const groups = new Map();
  for (const L of lines){
    const k = L.project_id + "\u0000" + L.month;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(L);
  }
  for (const group of groups.values()){
    let claims = 0, ran = 0;
    for (const L of group){ claims += L.claim; ran = Math.max(ran, L.coverage); }
    // The month, rounded once. Everything below divides THIS, so the parts cannot come
    // to anything else.
    const demandCents = toCents(group[0].standard_fte * group[0].period_weight * ran);
    const demand = fromCents(demandCents);
    const cents = largestRemainder(
      group.map(L => ({weight: claims > 0 ? L.claim : 0, key: L.assignment_id || ""})),
      demandCents);
    group.forEach((L, i) => {
      L.role_share = claims > 0 ? L.claim / claims : 0;
      L.month_run = ran;
      L.demand_fte = demand;
      L.fte = L.auto = fromCents(cents[i]);
    });
  }
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
    if (M.findings[i].rule === "V-31" || M.findings[i].rule === "V-32"
        || M.findings[i].rule === "V-33") M.findings.splice(i, 1);

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

  /* V-33: A PERSON'S STATED FIGURE THAT THE PROJECT'S OWN FIGURE OVERRODE.
     REQ-CAL-18 makes the project figure the mother figure: it is the whole month, and
     the people on it are scaled so they still add up to it. That is deliberate and it is
     what keeps the two utilisation charts agreeing. What it also means is that somebody
     can type 2.00 against their own name and be given 1.73, because a colleague's figure
     and theirs together had to come to the project's month - and until now the
     application did that silently. The figure in the sheet said one thing and the figure
     on the chart said another, with nothing connecting them.
     Reported rather than refused: both numbers are things a person deliberately typed,
     and which of them is wrong is not the application's judgement to make. */
  const clash = new Map();
  for (const L of lines || []){
    if (!L.overridden_by_project) continue;
    const k = L.assignment_id;
    if (!clash.has(k)) clash.set(k, []);
    clash.get(k).push([isoOf(L.month), L.stated_assignment_fte, L.fte,
                       L.manual_project_total]);
  }
  for (const [aid, ms] of clash){
    const show = ms.slice(0, 4).map(([mo, was, now]) =>
      `${mo}: stated ${was.toFixed(2)}, applied ${now.toFixed(2)}`).join("; ");
    M.findings.push({sev:"warning", rule:"V-33", sheet:"MonthlyEstimate", row:"",
      msg:`Assignment ${aid} states a monthly figure that its PROJECT'S own manual `
        + `figure overrode in ${ms.length} month(s) — ${show}`
        + `${ms.length > 4 ? ", …" : ""}. The project figure is the whole month and the `
        + `people on it are scaled to add up to it, so the stated figure for this person `
        + `is not what they are given. Either change the project's figure to one that `
        + `leaves room for this person's, or take this assignment off manual and let it `
        + `take its share.`});
  }
}

/** V-36: a project that has periods, and nobody assigned to it at all.
 *
 *  WHAT IT IS FOR, STATED FROM WHAT THE SCREEN ACTUALLY DOES rather than from what it
 *  was assumed to do - the first wording of this rule got it wrong and the screenshots
 *  corrected it. A project created and given its periods IS listed: it has a row in
 *  Resource by project, it is drawn on the timeline, and it counts in the projects
 *  tile. What it has is a row of BLANKS - every month empty, nothing on the demand
 *  charts, no legend entry, and no line in Standard vs staffed.
 *
 *  That is worse than being absent, and it is the same failure V-34 was written for: a
 *  row of blanks reads as a project that costs nothing, exactly as a study needing
 *  10.00 and staffed at 5.00 read as a study that only ever needed 5.00. The figure is
 *  computable the whole time - type, phase, scope and periods are all the standard
 *  needs - and REQ-CAL-19 is explicit that the project-month IS its standard and the
 *  people on it DIVIDE it. A divisor of nobody does not make the demand nought.
 *
 *  AND NOTHING ELSE REPORTED IT. V-34 compares demand against applied, which is exactly
 *  this gap at its widest - but V-34 is built from projGap, which is built from
 *  projMonth, which is built from the LINES. No assignment, no line, no entry, no
 *  finding. The one project that is short by the whole of its standard was the only
 *  shortfall the shortfall rule could not see.
 *
 *  INFORMATION, AND CLASSED INCOMPLETE. Both on purpose. A project with nobody on it
 *  yet is not a fault - it is the state every project is in for the minute after it is
 *  created, exactly as a person with no assignment is (plan v2.52) - so it must never
 *  refuse an edit, never block a save, and never ask a question. `incomplete` is the
 *  class for a row still being built whose finding will answer itself, and this one
 *  answers itself the moment anybody is assigned. Information rather than warning for
 *  the same reason V-29 and V-30 are: the file is not malformed and the application is
 *  doing the only sensible thing with it.
 *
 *  IT CARRIES THE FIGURE, which is the whole point of raising it from the calculation.
 *  "PRJ-099 has no assignments" tells a planner something they can see; "PRJ-099 needs
 *  1.86 FTE in 2026-10 and 27.35 FTE-months over 24 months, and none of it is staffed"
 *  tells them what it will cost them to fix.
 *
 *  One finding per PROJECT, like V-34: the months are named inside it, and twenty-four
 *  findings for one un-started study would bury every other rule in the report. */
function reportUnstaffed(M, rows){
  if (!M || !Array.isArray(M.findings)) return;
  for (let i = M.findings.length - 1; i >= 0; i--)
    if (M.findings[i].rule === "V-36") M.findings.splice(i, 1);
  for (const r of rows){
    M.findings.push({sev:"information", rule:"V-36", sheet:"Project", row:"",
      msg:`Project ${r.pid} has periods but NOBODY ASSIGNED TO IT. It is listed in `
        + `Resource by project and drawn on the timeline, but EVERY ONE OF ITS MONTHS IS `
        + `EMPTY, and it adds nothing to the demand charts - a row of blanks, which `
        + `reads as a project that costs nothing rather than one nobody has been put on `
        + `yet. Its own standard says it needs ${r.total.toFixed(2)} FTE-months across `
        + `${r.months} month(s), from ${r.firstMonth}, peaking at `
        + `${r.peak.toFixed(2)} FTE in ${r.peakMonth}. That demand is real and `
        + `unallocated: a project-month IS its standard and the people on it divide it `
        + `(REQ-CAL-19), so having nobody on it does not make the figure nought - it `
        + `leaves it unstated. Assign somebody and the project fills in across every `
        + `table and chart, at exactly these figures. This is a note, not a fault: it is `
        + `the state every project is in until its first assignment, so it never refuses `
        + `an edit and never questions a save.`});
  }
}

/** V-34: a project that is no longer being given what its own standard says it needs.
 *
 *  REPORTED, NEVER REFUSED, AND NEVER A GATE. The severity is `warning` on purpose:
 *  refuses() only acts on errors, so this reaches the findings report, the load banner,
 *  the archived change log and the results export without stopping a save or asking a
 *  question. Departing from the standard is the entire point of REQ-CAL-18 - a manager
 *  part way through a trial knows better than the assumptions - so the application has
 *  no business calling it wrong. What it does have business doing is SAYING SO, because
 *  the departure is otherwise completely silent.
 *
 *  BOTH DIRECTIONS, AND THEY ARE NOT THE SAME FACT. Short of the standard is a project
 *  being asked to run on less than its kind usually takes; over it is a project
 *  deliberately staffed heavier. Summed together they would cancel - a project three
 *  short in March and three over in April would report as fine - so they are counted and
 *  named separately and the net is never shown on its own.
 *
 *  One finding per PROJECT rather than per month: twenty-four consecutive months of the
 *  same manual decision is one decision, and twenty-four findings would bury every other
 *  rule in the report. The months are named inside it. */
function reportDemandGap(M, projGap){
  if (!M || !Array.isArray(M.findings)) return;
  for (let i = M.findings.length - 1; i >= 0; i--)
    if (M.findings[i].rule === "V-34") M.findings.splice(i, 1);

  const by = new Map();
  for (const [qk, g] of projGap){
    const pid = qk.slice(0, qk.lastIndexOf("|"));
    if (!by.has(pid)) by.set(pid, []);
    by.get(pid).push([isoOf(+qk.slice(qk.lastIndexOf("|") + 1)), g]);
  }
  for (const [pid, ms] of by){
    ms.sort((a, b) => a[0] < b[0] ? -1 : 1);
    const short = ms.filter(([, g]) => g.dir === "short");
    const over = ms.filter(([, g]) => g.dir === "over");
    const worst = ms.slice().sort((a, b) =>
      Math.abs(b[1].gap) - Math.abs(a[1].gap))[0];
    const parts = [];
    if (short.length) parts.push(`${short.length} month(s) SHORT of it by up to `
      + `${Math.max(...short.map(([, g]) => -g.gap)).toFixed(2)}`);
    if (over.length) parts.push(`${over.length} month(s) OVER it by up to `
      + `${Math.max(...over.map(([, g]) => g.gap)).toFixed(2)}`);
    M.findings.push({sev:"warning", rule:"V-34", sheet:"MonthlyEstimate", row:"",
      msg:`Project ${pid} is not being given what its own standard says it needs: `
        + `${parts.join(", and ")} FTE. Worst is ${worst[0]}, which needs `
        + `${worst[1].demand.toFixed(2)} and is getting ${worst[1].applied.toFixed(2)}. `
        + `A manual figure - on the project or on one of its assignments - replaces the `
        + `standard rather than adjusting it, so this is what somebody decided rather `
        + `than a fault. It is reported because it is otherwise invisible: the charts `
        + `simply draw a ${short.length && !over.length ? "smaller"
            : over.length && !short.length ? "larger" : "different"} project, which `
        + `looks exactly like a project that was always that size. Open Standard vs `
        + `staffed on the Overall tab to see every month and change the figures behind `
        + `them.`});
  }
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
      // Rounded like everything else (REQ-CAL-20). The panel types these at two places,
      // but the sheet is a spreadsheet and a hand-edited cell can hold 0.123456.
      L.fte = fromCents(toCents(v));
      L.source = "manual (assignment)";
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
    /* The stated month, shared out to the hundredth (REQ-CAL-20). Scaling each line and
       leaving it there would put the people a fraction off the figure the user typed -
       and a project total that its own people do not add up to is precisely what
       REQ-CAL-18 exists to prevent. Same rule as shareOut(): round the month once, hand
       out its hundredths by largest remainder. */
    const scale = want / have;
    const wantCents = toCents(want);
    const cents = largestRemainder(
      group.map(L => ({weight: L.fte, key: L.assignment_id || ""})), wantCents);
    group.forEach((L, i) => {
      /* WHAT THE PERSON ASKED FOR, BEFORE THE PROJECT OVERRODE IT (V-33).
         A stated assignment figure is applied first and then scaled to the project's
         stated month, so a person can type 2.00 and be given 1.73 - the project figure
         is the mother figure and wins, which is REQ-CAL-18 working as specified. What
         was missing is that nothing SAID so. Kept on the line here, where both numbers
         are in hand, so the screen and the findings report can both name it. */
      if (L.manual_assignment && toCents(L.fte) !== cents[i]){
        L.stated_assignment_fte = L.fte;
        L.overridden_by_project = true;
      }
      L.fte = fromCents(cents[i]);
      L.project_scale = scale;
      L.manual_project_total = fromCents(wantCents);
      L.source = L.manual_assignment ? "manual (assignment, scaled to the project figure)"
                                     : "manual (project, shared out)";
    });
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

