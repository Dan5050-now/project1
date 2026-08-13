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

  const start = proj.start_date, end = proj.end_date;
  const suS0 = protocol ? addDays(protocol, 1) : addMonths(cta, -1);
  const suS = suS0 > start ? suS0 : start;
  const suE = (siv && siv >= suS) ? siv : addDays(addMonths(suS, 4), -1);

  const later = (ms["Inspection"] || []).filter(d => d > fdbl);   // V-21, R-03
  const p7S = later.length ? new Date(Math.min(...later)) : null;
  const p7E = later.length ? new Date(Math.max(Math.max(...later), end.getTime())) : null;

  let cofS = addMonths(fdbl, -3);
  const cofE = p7S ? addDays(p7S, -1) : new Date(Math.max(fdbl.getTime(), end.getTime()));

  const segs = [];
  if (suS > start) segs.push(["Before-Start-up", start, addDays(suS, -1)]);
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

