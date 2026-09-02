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

function derivePeriods(proj, ms){
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

