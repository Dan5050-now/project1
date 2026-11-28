/* ============================================================ 4. period derivation
   Spec sheet 05. A recorded milestone beats the month offset (REQ-CAL-13); boundaries
   apply in order and a period squeezed to nothing is dropped (REQ-CAL-12, C-11).  */

const DAY = 86400000;
function addMonths(d, n){
  const y = d.getUTCFullYear(), m = d.getUTCMonth(), day = d.getUTCDate();
  const last = new Date(Date.UTC(y, m + n + 1, 0)).getUTCDate();
  return new Date(Date.UTC(y, m + n, Math.min(day, last)));   // clamps 31 Mar -1m -> 28/29 Feb
}
const addDays = (d, n) => new Date(d.getTime() + n * DAY);

/** A project's periods, worked out from its milestones.
 *
 *  BY THE PLAN'S OWN RULES WHERE IT HAS SOME (schema 17, R-70): `M` is the model, and a
 *  project whose type has rows on the PeriodRule sheet is derived by them - see
 *  deriveByRule() below. Otherwise a clinical trial is derived by the BUILT-IN rule,
 *  which is what every plan written before schema 17 was derived by and is therefore
 *  kept exactly as it was: a plan that has not stated rules must not see its periods
 *  move because the application learned to read them. Called with no model at all, as
 *  the oldest callers do, it is the built-in rule. */
function derivePeriods(proj, ms, M){
  const plan = derivationPlan(proj, ms, M);
  return plan && plan.segs.length
    ? plan.segs.map((g, i) => ({period_name:g.name, period_seq:i + 1,
                                period_start:g.start, period_end:g.end}))
    : null;
}

/** The rules a project of this type is derived by, in the order its periods run - or
 *  null where the plan states none for the type. */
function rulesFor(M, type){
  const rows = M && M.periodRules && M.periodRules[type];
  return rows && rows.length ? rows : null;
}

/** The whole derivation with its working shown: each period's dates and how each was
 *  found, the periods left out and why, and where neighbours do not meet. `source` says
 *  which recipe it was - the plan's rules for this type, or the built-in one. */
function derivationPlan(proj, ms, M){
  const rules = rulesFor(M, proj.project_type);
  if (rules) return deriveByRule(proj, ms, rules, periodOrder(M, proj.project_type));
  if (M && !CLINICAL_TYPES.has(proj.project_type)) return null;
  const segs = derivePeriodsBuiltIn(proj, ms);
  return segs ? {source:"built-in", segs: segs.map(g => ({name:g.period_name,
      start:g.period_start, end:g.period_end, how:{start:"the built-in rule", end:"the built-in rule"},
      est:{start:false, end:false}})), left:[], seams:[]} : null;
}

/** The periods of a type, in the order a project lives through them: the plan's own list
 *  for the type where it has one, the schema's otherwise. */
function periodOrder(M, type){
  const ct = CLINICAL_TYPES.has(type);
  const own = M && M.lists && M.lists[ct ? "period_name_clinical" : "period_name_others"];
  return own && own.length ? own.map(String) : (ct ? CLINICAL_PERIODS : OTHER_PERIODS);
}

/* ================================== period derivation BY THE PLAN'S RULES (R-70)

   The built-in rule is one recipe, written into the code: Start-up from the protocol or
   a month before CTA submission, close-out three months before the lock, and so on. A
   team that runs its trials differently had no way to say so except to type every
   period by hand on every project. So the recipe can be stated on the PeriodRule sheet,
   per project type - which is where it belongs, beside the other standards the plan
   reads - and General assumptions is where it is changed.

   WHAT A RULE SAYS. Each period's start is a milestone plus or minus a number of days,
   and so is its end: −1 the day before, 1 the day after, 0 the day itself. A milestone
   recorded more than once (Inspection) gives a start its FIRST date and an end its LAST.

   WHAT HAPPENS WHEN THE PROJECT CANNOT ANSWER IT - which is the ordinary case on a plan
   being entered, and was the request's second half:
     - A period NEITHER of whose milestones is recorded is a period this project does not
       have - no interim DB lock, no interim close-out - and is left out.
     - A date whose milestone is not recorded, or that names none, is found from the
       neighbours: a start is the day after the previous period ends, an end the day
       before the next one starts. The first period starts with the project, the last
       ends with it.
     - A boundary unknown from BOTH sides - this period's end and the next one's start -
       is put halfway between the dates either side of it. An estimate, and shown as one.
     - A period that still has no start or end, or would end before it starts, is left
       out and the reason given.
   Every date carries how it was found, so the preview shows which dates are the
   milestones' and which are estimates - an estimate presented as a fact is the one
   thing a derivation must not do. */
function deriveByRule(proj, ms, rules, order){
  const first = n => (n && ms[n] && ms[n].length) ? ms[n][0] : null;
  const last = n => (n && ms[n] && ms[n].length) ? ms[n][ms[n].length - 1] : null;
  const days = v => { const n = num(v); return n === null || n === undefined ? 0 : Math.round(n); };
  const say = (m, n) => `${m}${n > 0 ? ` + ${n} day${n === 1 ? "" : "s"}`
                               : n < 0 ? ` − ${-n} day${n === -1 ? "" : "s"}` : ""}`;
  const rank = n => { const i = order.indexOf(n); return i < 0 ? order.length : i; };
  const rows = rules.slice().sort((a, b) => rank(a.period_name) - rank(b.period_name)
    || (a.__row || 0) - (b.__row || 0));
  const segs = [], left = [];
  for (const r of rows){
    const sm = r.start_milestone || null, em = r.end_milestone || null;
    const sd = first(sm), ed = last(em);
    if (!sd && !ed){
      const named = [sm, em].filter(Boolean);
      left.push({name:r.period_name, why: named.length
        ? `${named.map(n => `'${n}'`).join(" and ")} ${named.length > 1 ? "are" : "is"} not recorded for this project`
        : "its rule names no milestone"});
      continue;
    }
    const so = days(r.start_offset_days), eo = days(r.end_offset_days);
    segs.push({name:r.period_name,
      start: sd ? addDays(sd, so) : null, end: ed ? addDays(ed, eo) : null,
      how: {start: sd ? say(sm, so) : null, end: ed ? say(em, eo) : null},
      /* An ESTIMATE is a date whose rule named a milestone the project has not recorded
         (or one placed halfway, below). A rule that names none means "follow the
         neighbour" on purpose - that date is the rule's, not a guess. */
      est: {start: !!(sm && !sd), end: !!(em && !ed)},
      miss: {start: sm && !sd ? sm : null, end: em && !ed ? em : null}});
  }
  if (!segs.length) return {source:"rules", segs:[], left, seams:[]};
  const pS = proj.start_date instanceof Date ? proj.start_date : null;
  const pE = proj.end_date instanceof Date ? proj.end_date : null;
  const a0 = segs[0], z = segs[segs.length - 1];
  const why = (g, side) => g.miss[side] ? ` ('${g.miss[side]}' not recorded)` : "";
  if (!a0.start && pS){ a0.start = pS; a0.how.start = "the project's start" + why(a0, "start"); }
  if (!z.end && pE){ z.end = pE; z.how.end = "the project's end" + why(z, "end"); }
  for (let moved = true; moved; ){
    moved = false;
    for (let i = 1; i < segs.length; i++)
      if (!segs[i].start && segs[i - 1].end){
        segs[i].start = addDays(segs[i - 1].end, 1);
        segs[i].how.start = `the day after ${segs[i - 1].name} ends` + why(segs[i], "start");
        moved = true;
      }
    for (let i = segs.length - 2; i >= 0; i--)
      if (!segs[i].end && segs[i + 1].start){
        segs[i].end = addDays(segs[i + 1].start, -1);
        segs[i].how.end = `the day before ${segs[i + 1].name} starts` + why(segs[i], "end");
        moved = true;
      }
    if (moved) continue;
    for (let i = 0; i < segs.length - 1; i++){
      const a = segs[i], b = segs[i + 1];
      if (!a.end && !b.start && a.start && b.end && b.end >= a.start){
        a.end = addDays(a.start, Math.floor(Math.round((b.end - a.start) / DAY) / 2));
        b.start = addDays(a.end, 1);
        a.how.end = `halfway to the end of ${b.name}` + why(a, "end");
        b.how.start = `halfway from the start of ${a.name}` + why(b, "start");
        a.est.end = b.est.start = true;
        moved = true;
      }
    }
  }
  const out = [];
  for (const g of segs){
    if (!g.start || !g.end){
      const side = !g.start ? "start" : "end";
      left.push({name:g.name, why: `its ${side} cannot be placed — `
        + (g.miss[side] ? `'${g.miss[side]}' is not recorded` : `its rule names no milestone for it`)
        + ` and ${side === "start" ? "nothing comes before it, and the project has no start date"
                                    : "nothing follows it, and the project has no end date"}`});
      continue;
    }
    if (g.end < g.start){
      left.push({name:g.name, why: `it would end (${ymd(g.end)}) before it starts (${ymd(g.start)})`});
      continue;
    }
    out.push(g);
  }
  /* Where two periods that were each placed by their own rule do not meet. Not mended:
     which of the two is right is the rule-writer's call, and the rows written are
     ordinary rows, so V-12 and V-06 go on reporting it until somebody decides. */
  const seams = [];
  for (let i = 1; i < out.length; i++){
    const gap = Math.round((out[i].start - out[i - 1].end) / DAY) - 1;
    if (gap) seams.push({a:out[i - 1].name, b:out[i].name, days:gap});
  }
  return {source:"rules", segs: out, left, seams};
}

function derivePeriodsBuiltIn(proj, ms){
  const get = n => (ms[n] && ms[n][0]) || null;
  const protocol = get("Protocol (v1)"), cta = get("CTA submission");
  const siv = get("First SIV") || get("FPI");
  const idbl = get("interim DB lock");
  const fdbl = get("final DB lock") || idbl;
  if (!cta || !fdbl) return null;                              // V-16

  /* THE PROJECT'S OWN DATES ARE OPTIONAL HERE, and a blank one is not an error.
     This runs on a trial that carries no periods, which is very often a plan somebody
     is part way through entering or has built by hand from the milestones outward -
     and REQ-CAL-17 says the periods ARE the project, so the dates are a consequence of
     this derivation at least as much as an input to it. Requiring them made a file that
     could not be opened at all: `end.getTime()` threw, the exception escaped
     buildModel, and the whole load failed with a raw JavaScript message naming no
     project. A blank `start_date` was worse for being quiet - `suS0 > null` compares
     against zero and is therefore always true, so no floor was applied AND a
     Before-Start-up period was emitted running from null, which then travelled into
     the calculation looking like an ordinary row.

     Both dates are floors, and nothing more: start stops start-up opening before the
     project does, end stops close-out finishing before it ends. Absent, there is simply
     no floor, and the milestones alone describe the run - which is what a file with
     milestones and no dates is actually saying. Save writes the resulting window back
     into the project (REQ-CAL-17), so the blank fills itself in. */
  const start = proj.start_date instanceof Date ? proj.start_date : null;
  const end   = proj.end_date   instanceof Date ? proj.end_date   : null;
  const suS0 = protocol ? addDays(protocol, 1) : addMonths(cta, -1);
  const suS = (start && start > suS0) ? start : suS0;
  const suE = (siv && siv >= suS) ? siv : addDays(addMonths(suS, 4), -1);

  const later = (ms["Inspection"] || []).filter(d => d > fdbl);   // V-21, R-03
  const p7S = later.length ? new Date(Math.min(...later)) : null;
  const p7E = later.length
    ? new Date(end ? Math.max(Math.max(...later), end.getTime()) : Math.max(...later))
    : null;

  let cofS = addMonths(fdbl, -3);
  const cofE = p7S ? addDays(p7S, -1)
             : (end ? new Date(Math.max(fdbl.getTime(), end.getTime())) : fdbl);

  const segs = [];
  if (start && suS > start) segs.push(["Before-Start-up", start, addDays(suS, -1)]);
  segs.push(["Start-up", suS, suE]);
  if (idbl && idbl < fdbl){                                    // R-11: the split case
    const coiS = addMonths(idbl, -3);
    segs.push(["Conduct (interim)", addDays(suE, 1), addDays(coiS, -1)]);
    segs.push(["Close-out (interim)", coiS, idbl]);
    if (addDays(idbl, 1) > cofS) cofS = addDays(idbl, 1);
    segs.push(["Conduct (final)", addDays(idbl, 1), addDays(cofS, -1)]);
  } else {
    segs.push(["Conduct (final)", addDays(suE, 1), addDays(cofS, -1)]);
  }
  segs.push(["Close-out (final)", cofS, cofE]);
  if (p7S) segs.push(["After Close-out (final)", p7S, p7E]);

  return segs.filter(s => s[2] >= s[1])
             .map((s, i) => ({period_name:s[0], period_seq:i+1, period_start:s[1], period_end:s[2]}));
}

