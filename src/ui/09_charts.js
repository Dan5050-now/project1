/* ============================================================ 9. charts */

/* Every measurement the charts are drawn to, in one place.
 *
 * These used to be five separate lines of bare numbers spread through the file, and two
 * of them - the project stack and the person stack - carried IDENTICAL geometry that had
 * to be kept in step by hand. Changing the height of one stacked chart and forgetting
 * the other is the kind of mistake that looks like a rendering bug.
 *
 * They are SVG user units, not pixels. Each chart declares a viewBox of exactly these
 * dimensions and the browser scales it to whatever width the panel has, so a number here
 * changes the SHAPE of a chart, never its size on screen. `Wmin`/`Wbase`/`Wper` are for
 * the charts whose width grows with the horizon: W = max(Wmin, Wbase + months * Wper).
 * The four `pad` values are the margins around the plotting area - L for the value axis
 * (and, on the Gantt, the project names), B for the month axis, T for the unit label,
 * R for the threshold labels that sit outside the plot. */
const CHART = {
  // One row per project. The label gutter is what a single-project view does not need,
  // so it has its own pair: the whole gutter goes to the bands instead.
  gantt:  {W:1180, padT:34, padR:14, foot:30,
           rowh:42, rowhSingle:74, padL:220, padLSingle:26},
  // One line per project or person across the horizon.
  lines:  {Wmin:720, Wbase:96, Wper:46, H:300, padL:62, padR:16, padT:24, padB:46},
  // Stacked months - drawn TWICE, by project and by person, to the same geometry.
  // `headroom` lifts the top of the scale clear of the tallest stack.
  stack:  {Wmin:700, Wbase:90, Wper:74, H:600, padL:62, padR:14, padT:30, padB:52,
           headroom:1.08},
  // One project against the portfolio average, thresholds labelled down the right.
  single: {W:1080, H:300, padL:62, padR:230, padT:26, padB:44},
};

/** One row per project: period bands, milestone markers, a year grid.
 *  `opts.single` lays it out for ONE project - the heading already names it, so the row
 *  label gutter shrinks and the row itself gets the space instead. */
function chartGantt(pids, opts){
  opts = opts || {};
  const M = S.model, C = S.calc;
  if (!pids.length) return `<p class="note">No projects match the current filters.</p>`;
  // The panel now scrolls vertically as well as horizontally, so every project in the
  // filter is drawn rather than the first 20. The scroll region is what makes that
  // readable - without it the panel would simply grow down the page.
  const rows = pids.slice();
  let lo = Infinity, hi = -Infinity;
  for (const p of rows){
    const pr = M.projects[p];
    if (pr.start_date) lo = Math.min(lo, pr.start_date.getTime());
    if (pr.end_date) hi = Math.max(hi, pr.end_date.getTime());
  }
  if (!isFinite(lo) || !isFinite(hi)) return `<p class="note">These projects carry no dates.</p>`;
  const span = Math.max(1, (hi - lo) / DAY);
  // One project needs no row label - the panel heading already names it, and the dates go
  // in the note - so the whole gutter goes to the bands instead.
  const K = CHART.gantt, W = K.W, padT = K.padT;
  const rowh = opts.single ? K.rowhSingle : K.rowh;
  const padL = opts.single ? K.padLSingle : K.padL;
  const H = padT + rowh * rows.length + K.foot, inner = W - padL - K.padR;
  const x = t => padL + ((t - lo) / DAY / span) * inner;
  let wmax = 0;
  for (const p of rows) for (const s of (M.periods[p] || [])) wmax = Math.max(wmax, num(s.weight) || 0);
  wmax = wmax || 1;

  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="Project timeline: one row per project, bands coloured by period">`];
  for (let y = new Date(lo).getUTCFullYear(); y <= new Date(hi).getUTCFullYear(); y++){
    const xx = x(Date.UTC(y, 0, 1));
    if (xx >= padL){
      o.push(`<line class="grid" x1="${xx.toFixed(1)}" y1="${padT-8}" x2="${xx.toFixed(1)}" y2="${H-22}"/>`);
      o.push(`<text class="ax" x="${xx.toFixed(1)}" y="${padT-12}" text-anchor="middle">${y}</text>`);
    }
  }
  rows.forEach((p, i) => {
    const pr = M.projects[p], y = padT + i * rowh;
    const months = (pr.start_date && pr.end_date)
      ? (pr.end_date.getUTCFullYear()-pr.start_date.getUTCFullYear())*12
        + (pr.end_date.getUTCMonth()-pr.start_date.getUTCMonth()) + 1 : 0;
    if (!opts.single){
      o.push(`<text class="rowlab" x="${padL-12}" y="${y+14}" text-anchor="end">`
        + `${esc(String(pr.project_name).slice(0,26))}</text>`);
      o.push(`<text class="rowsub" x="${padL-12}" y="${y+27}" text-anchor="end">`
        + `${ymd(pr.start_date)} &#8594; ${ymd(pr.end_date)} &middot; ${months} months</text>`);
    }
    for (const s of (M.periods[p] || [])){
      if (!s.period_start || !s.period_end) continue;      // a row still being filled in
      const x0 = x(s.period_start.getTime()), x1 = x(s.period_end.getTime());
      const w = Math.max(1.5, x1 - x0 - 2);
      const ms = monthsBetween(s.period_start, s.period_end);
      let tot = 0, n = 0;
      for (const [yy, mm] of ms){ tot += C.projMonth.get(p + "|" + monthKey(yy, mm)) || 0; n++; }
      const fte = n ? tot / n : 0;
      const tip = `<b>${esc(pr.project_name)}</b><br>${esc(s.period_name)}<br>`
        + `${ymd(s.period_start)} to ${ymd(s.period_end)}<br>period weight ${(num(s.weight)||0).toFixed(2)}`
        + `<br><b>${fte.toFixed(2)} FTE per month</b> on average across this period`;
      o.push(`<rect class="band" x="${x0.toFixed(1)}" y="${y+13}" width="${w.toFixed(1)}" `
        + `height="${rowh-20}" fill="${bandFill(s.period_name, num(s.weight)||0, wmax)}" rx="2" `
        + `data-tip="${att(tip)}"></rect>`);
      if (opts.single && w > 64)
        o.push(`<text class="bandsub" x="${(x0+w/2).toFixed(1)}" y="${(y+rowh-14).toFixed(1)}" `
          + `text-anchor="middle">${fte.toFixed(2)} FTE/mo</text>`);
      if (w > s.period_name.length * 5.7 + 12)
        o.push(`<text class="bandlab" x="${(x0+w/2).toFixed(1)}" y="${(y+rowh/2+5).toFixed(1)}" `
          + `text-anchor="middle">${esc(s.period_name)}</text>`);
    }
    for (const [nm, dates] of Object.entries(M.milestones[p] || {}))
      for (const d of dates){
        if (!d) continue;
        const xx = x(d.getTime()), key = KEY_MILESTONES.has(nm);
        const tip = `<b>${esc(pr.project_name)}</b><br>${esc(nm)}`
          + (key ? ` <span class="tr">&#183; sets a period boundary</span>` : "") + `<br>${ymd(d)}`;
        const w_ = key ? 6.5 : 5, h_ = key ? 11 : 9;
        o.push(`<polygon class="ms${key ? " key" : ""}" points="${(xx-w_).toFixed(1)},${y+1} `
          + `${(xx+w_).toFixed(1)},${y+1} ${xx.toFixed(1)},${y+1+h_}" data-tip="${att(tip)}"></polygon>`);
      }
  });
  o.push("</svg>");
  const seen = new Set();
  const leg = ['<ul class="legend">'];
  for (const p of rows) for (const s of (M.periods[p] || [])) seen.add(s.period_name);
  for (const n of [...CLINICAL_PERIODS, ...OTHER_PERIODS]) if (seen.has(n))
    leg.push(`<li><span class="sw" style="background:${PERIOD_HUE[n]}"></span>${esc(n)}</li>`);
  leg.push('<li><span class="sw tri"></span>milestone</li>');
  leg.push('<li><span class="sw tri key"></span>DB lock &#8212; sets a period boundary</li>');
  leg.push('<li class="hint">darker band = higher period weight</li></ul>');
  leg.push(`<p class="note">${opts.note || `All ${rows.length} project(s) in the current filter, `
    + `scrolling in both directions inside this panel.`}</p>`);
  return o.join("") + leg.join("");
}

/** Monthly resource as LINES, one per series.
 *
 *  The stacked charts answer "what is the total made of"; a stack cannot answer "is this
 *  one rising or falling", because every band's baseline moves with the bands beneath it.
 *  Lines share one baseline, so shape is comparable across series - which is the whole
 *  reason to draw the same numbers a second way.
 *
 *  `items` is [id, label, colour]; `valueAt(id, monthKey)` supplies the figure. Capped at
 *  LIMIT lines by total, because a chart of sixty lines is a texture, not a reading.
 */
const LINE_LIMIT = 12;
function chartLines(items, valueAt, opts){
  opts = opts || {};
  const G = grid();
  if (!G.length) return `<p class="note">The horizon is empty.</p>`;
  const totals = items.map(it => [it, G.reduce((t, k) => t + (valueAt(it[0], k) || 0), 0)])
    .filter(x => x[1] > 0.004).sort((a, b) => b[1] - a[1]);
  if (!totals.length) return `<p class="note">${esc(opts.empty || "Nothing draws resource inside this horizon.")}</p>`;
  const shown = totals.slice(0, LINE_LIMIT);
  const K = CHART.lines, H = K.H, padL = K.padL, padR = K.padR, padT = K.padT, padB = K.padB;
  const W = Math.max(K.Wmin, K.Wbase + G.length * K.Wper);
  const step = (W - padL - padR) / Math.max(1, G.length - 1 || 1);
  const xOf = i => G.length === 1 ? padL + (W - padL - padR) / 2 : padL + i * step;
  let vmax = 0;
  for (const [it] of shown) for (const k of G) vmax = Math.max(vmax, valueAt(it[0], k) || 0);
  vmax = (vmax || 1) * 1.12;
  const yOf = v => H - padB - (v / vmax) * (H - padB - padT);

  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="${att(opts.aria || "Monthly resource, one line per series")}">`];
  o.push(`<text class="ax" x="${padL-8}" y="${padT-8}" text-anchor="end">${unitLabel()}</text>`);
  for (let i = 0; i <= 4; i++){
    const v = vmax * i / 4, yy = yOf(v);
    o.push(`<line class="grid" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<text class="ax" x="${padL-8}" y="${(yy+3).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`);
  }
  // A reference line only where one applies to a SINGLE series' own value.
  if (opts.rule){
    const yy = yOf(opts.rule[0]);
    if (yy > padT && yy < H - padB){
      o.push(`<line class="halo" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR}" y2="${yy.toFixed(1)}"/>`);
      o.push(`<line class="th-over" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR}" y2="${yy.toFixed(1)}"/>`);
      // right-aligned at the plot edge: at the left it sits on top of the first months,
      // which is where the lines are densest
      o.push(`<text class="thlab th-over" x="${W-padR-2}" y="${(yy-7).toFixed(1)}" `
        + `text-anchor="end">${esc(opts.rule[1])}</text>`);
    }
  }
  for (const [[id, label, colour], total] of shown){
    const pts = G.map((k, i) => `${xOf(i).toFixed(1)},${yOf(valueAt(id, k) || 0).toFixed(1)}`).join(" ");
    let peak = -1, peakK = null;
    for (const k of G){ const v = valueAt(id, k) || 0; if (v > peak){ peak = v; peakK = k; } }
    const tip = `<b>${esc(label)}</b><br>`
      + `${fmt(total)} ${unitLabel()}-months over ${G.length} months`
      + `<br><span class="tr">mean ${fmt(total / G.length)} &#183; `
      + `peak ${fmt(peak)} in ${keyToLabel(peakK)}</span>`;
    // A hit strip under the stroke: a 2px line is almost impossible to hover deliberately.
    o.push(`<polyline class="lnhit" points="${pts}" data-tip="${att(tip)}"></polyline>`);
    o.push(`<polyline class="ln" points="${pts}" stroke="${colour}"></polyline>`);
    for (const [i, k] of G.entries()){
      const v = valueAt(id, k) || 0;
      if (v <= 0.004) continue;
      o.push(`<circle class="lndot" cx="${xOf(i).toFixed(1)}" cy="${yOf(v).toFixed(1)}" r="2.4" `
        + `fill="${colour}"></circle>`);
    }
  }
  monthAxis(o, G, i => xOf(i) - step / 2, step, H - padB + 17, H - padB + 32, padT, H - padB);
  o.push(`<line class="base" x1="${padL}" y1="${H-padB}" x2="${W-padR}" y2="${H-padB}"/></svg>`);
  const leg = ['<ul class="legend">'];
  for (const [[, label, colour]] of shown)
    leg.push(`<li><span class="sw ln" style="background:${colour}"></span>${esc(label)}</li>`);
  leg.push('</ul>');
  if (totals.length > shown.length)
    leg.push(`<p class="note">The ${LINE_LIMIT} largest by total are drawn; ${totals.length - shown.length} `
      + `more fall below them. Sixty lines on one axis is a texture, not a reading — use the filters `
      + `above to narrow it, or read the stacked chart for the total.</p>`);
  return o.join("") + leg.join("");
}

function projectLines(pids){
  const C = S.calc, M = S.model;
  return chartLines(pids.map(p => [p, M.projects[p].project_name, projColourOf(p)]),
    (p, k) => C.projMonth.get(p+"|"+k) || 0,
    {aria:"Monthly resource, one line per project",
     empty:"No project draws resource inside this horizon."});
}
function personLines(sids){
  const C = S.calc, M = S.model;
  return chartLines(sids.map(s => [s, (M.people[s]||{}).person_name || s, persColourOf(s)]),
    (s, k) => C.persMonth.get(s+"|"+k) || 0,
    {aria:"Monthly load, one line per person", rule:[M.OVER, `ceiling ${M.OVER.toFixed(2)}`],
     empty:"Nobody draws resource inside this horizon."});
}

function chartStacked(pids){
  const M = S.model, C = S.calc, G = grid();
  const tot = {};
  for (const p of pids){ tot[p] = 0; for (const k of G) tot[p] += C.projMonth.get(p+"|"+k) || 0; }
  const order = pids.filter(p => tot[p] > 0.004).sort((a,b) => tot[b]-tot[a] || (a<b?-1:1));
  if (!order.length) return `<p class="note">No resource falls inside this horizon.</p>`;
  const colour = {};
  for (const p of order) colour[p] = projColourOf(p);
  const K = CHART.stack, H = K.H, padL = K.padL, padB = K.padB, padT = K.padT;
  const W = Math.max(K.Wmin, K.Wbase + G.length * K.Wper);
  const bw = (W - padL - K.padR) / G.length;
  let vmax = 0;
  for (const k of G){ let s = 0; for (const p of order) s += C.projMonth.get(p+"|"+k) || 0; vmax = Math.max(vmax, s); }
  vmax = vmax || 1;
  const scale = (H - padB - padT) / (vmax * K.headroom);
  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="Monthly resource demand, one stacked band per project">`];
  o.push(`<text class="ax" x="${padL-8}" y="${padT-12}" text-anchor="end">${unitLabel()}</text>`);
  for (let i = 0; i <= 4; i++){
    const v = vmax * K.headroom * i / 4, yy = H - padB - v * scale;
    o.push(`<line class="grid" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-8}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<text class="ax" x="${padL-8}" y="${(yy+3).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`);
  }
  G.forEach((k, i) => {
    const x0 = padL + i * bw + 3;
    let base = H - padB;
    for (const p of order){
      const v = C.projMonth.get(p+"|"+k) || 0;
      if (v <= 0.004) continue;
      const h = v * scale;
      const crew = (C.who.get(p+"|"+k) || []).slice().sort();
      const list = crew.slice(0,8).map(([ps,role]) =>
        `&#183; ${esc((M.people[ps]||{}).person_name || ps)} <span class="tr">${esc(role)}</span>`).join("<br>");
      const tip = `<b>${esc(M.projects[p].project_name)}</b> `
        + `<span class="tr">${esc(M.projects[p].project_type)}</span><br>`
        + `${keyToLabel(k)} &#183; <b>${fmt(v)} ${unitLabel()}</b><br>`
        + `<span class="tr">${crew.length} ${crew.length===1?"person":"people"} this month</span><br>`
        + (list || "&#183; nobody assigned")
        + (crew.length > 8 ? `<br>&#183; and ${crew.length-8} more` : "");
      o.push(`<rect class="band" x="${x0.toFixed(1)}" y="${(base-h).toFixed(1)}" `
        + `width="${(bw-8).toFixed(1)}" height="${Math.max(0.6,h).toFixed(1)}" fill="${colour[p]}" `
        + `data-tip="${att(tip)}"></rect>`);
      base -= h;
    }
  });
  monthAxis(o, G, i => padL + i * bw + 3, bw - 8, H - padB + 17, H - padB + 32, padT, H - padB);
  o.push(`<line class="base" x1="${padL}" y1="${H-padB}" x2="${W-8}" y2="${H-padB}"/></svg>`);
  return o.join("");
}

/** The people to draw individually, biggest first, with the tail folded into one band.
 *  A thousand people is inside REQ-NFR-03; a thousand legend entries is not readable, so
 *  the same cap D-14 set for the old bar chart applies to the stack (REQ-DSH-09). */
const REST = "__rest";
function peopleOrder(sids, totalOf, limit){
  const t = sids.map(s => [s, totalOf(s)]).filter(x => x[1] > 0.004)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1));
  const head = t.slice(0, limit).map(x => x[0]);
  return {order: head.concat(t.length > limit ? [REST] : []),
          rest: t.slice(limit).map(x => x[0]), any: t.length > 0};
}
const persName = sid => sid === REST ? "" : (S.model.people[sid] || {}).person_name || sid;

/** Monthly demand, one stacked band per PERSON - the same figures the project chart above
 *  draws, cut the other way. The two totals agree month for month, because they are the
 *  same person-months summed along different axes. */
function chartPeople(sids){
  const M = S.model, C = S.calc, G = grid();
  const LIMIT = 20;
  const {order, rest, any} = peopleOrder(sids, s => {
    let t = 0; for (const k of G) t += C.persMonth.get(s+"|"+k) || 0; return t;
  }, LIMIT);
  if (!any) return `<p class="note">Nobody draws resource inside this horizon.</p>`;
  const restSet = new Set(rest);

  const K = CHART.stack, H = K.H, padL = K.padL, padB = K.padB, padT = K.padT;
  const W = Math.max(K.Wmin, K.Wbase + G.length * K.Wper);
  const bw = (W - padL - K.padR) / G.length;
  let vmax = 0;
  for (const k of G){
    let sum = 0;
    for (const s of sids) sum += C.persMonth.get(s+"|"+k) || 0;
    vmax = Math.max(vmax, sum);
  }
  vmax = vmax || 1;
  const scale = (H - padB - padT) / (vmax * K.headroom);
  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="Monthly resource demand, one stacked band per person">`];
  o.push(`<text class="ax" x="${padL-8}" y="${padT-12}" text-anchor="end">${unitLabel()}</text>`);
  for (let i = 0; i <= 4; i++){
    const v = vmax * K.headroom * i / 4, yy = H - padB - v * scale;
    o.push(`<line class="grid" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-8}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<text class="ax" x="${padL-8}" y="${(yy+3).toFixed(1)}" text-anchor="end">${fmt(v)}</text>`);
  }
  G.forEach((k, i) => {
    const x0 = padL + i * bw + 3;
    let month = 0;
    for (const s of sids) month += C.persMonth.get(s+"|"+k) || 0;
    let base = H - padB;
    for (const s of order){
      const v = s === REST
        ? rest.reduce((t, r) => t + (C.persMonth.get(r+"|"+k) || 0), 0)
        : (C.persMonth.get(s+"|"+k) || 0);
      if (v <= 0.004) continue;
      const h = v * scale;
      const projs = [...(C.persProj.get(s+"|"+k) || new Map())]
        .sort((a, b) => b[1] - a[1]);
      const cap = s === REST ? null : num((M.people[s] || {}).capacity_fte);
      const tip = s === REST
        ? `<b>the other ${rest.length} people</b><br>${keyToLabel(k)} &#183; `
          + `<b>${fmt(v)} ${unitLabel()}</b> between them`
          + `<br><span class="tr">shown as one band — see the table below for each of them</span>`
        : `<b>${esc(persName(s))}</b> <span class="tr">${esc(s)}</span><br>`
          + `${keyToLabel(k)} &#183; <b>${fmt(v)} ${unitLabel()}</b>`
          + `<span class="tr"> &#183; ${month > 0 ? (100*v/month).toFixed(0) : 0}% of the month</span>`
          + (cap ? `<span class="tr"> &#183; capacity ${cap.toFixed(2)}</span>` : "")
          + (v > M.OVER ? `<br><span class="tr">above the ${M.OVER.toFixed(2)} ceiling</span>`
             : v < M.UNDER ? `<br><span class="tr">below the ${M.UNDER.toFixed(2)} floor</span>` : "")
          + `<br>${projs.slice(0,6).map(([q, qv]) =>
                `&#183; ${esc(M.projects[q].project_name)} <span class="tr">${fmt(qv)}</span>`).join("<br>")}`
          + (projs.length > 6 ? `<br>&#183; and ${projs.length-6} more` : "")
          + `<hr>${keyToLabel(k)} across everyone in view: <b>${fmt(month)} ${unitLabel()}</b>`;
      // A person over the ceiling is outlined, so the flag never rests on colour alone (D-04).
      const breach = s !== REST && (v > M.OVER || v < M.UNDER);
      o.push(`<rect class="band${breach ? (v > M.OVER ? " brOver" : " brUnder") : ""}" `
        + `x="${x0.toFixed(1)}" y="${(base-h).toFixed(1)}" `
        + `width="${(bw-8).toFixed(1)}" height="${Math.max(0.6,h).toFixed(1)}" `
        + `fill="${s === REST ? "var(--other)" : persColourOf(s)}" data-tip="${att(tip)}"></rect>`);
      base -= h;
    }
  });
  monthAxis(o, G, i => padL + i * bw + 3, bw - 8, H - padB + 17, H - padB + 32, padT, H - padB);
  o.push(`<line class="base" x1="${padL}" y1="${H-padB}" x2="${W-8}" y2="${H-padB}"/></svg>`);
  const leg = ['<ul class="legend">'];
  for (const s of order)
    leg.push(`<li><span class="sw" style="background:${s === REST ? "var(--other)" : persColourOf(s)}"></span>`
      + `${esc(s === REST ? `the other ${rest.length} people` : persName(s))}</li>`);
  leg.push(`<li class="hint">outlined segment = that person is over ${M.OVER.toFixed(2)} or `
    + `under ${M.UNDER.toFixed(2)} FTE that month</li></ul>`);
  if (rest.length)
    leg.push(`<p class="note">${LIMIT} most loaded people shown individually; the remaining `
      + `${rest.length} are one band. ${rest.length + LIMIT} legend entries at this width would `
      + `be unreadable (REQ-DSH-09).</p>`);
  return o.join("") + leg.join("");
}

function chartProjectUtil(pid){
  const M = S.model, C = S.calc, G = grid();
  const act = [...C.projMonth.values()].filter(v => v > 0.004);
  const portAvg = act.length ? act.reduce((a,b)=>a+b,0) / act.length : 1;
  const upper = 2 * portAvg, lower = 0.5 * portAvg;
  const own = [];
  for (const [k, v] of C.projMonth) if (k.startsWith(pid + "|") && v > 0.004) own.push(v);
  const ownAvg = own.length ? own.reduce((a,b)=>a+b,0) / own.length : 0;
  const vals = G.map(k => C.projMonth.get(pid+"|"+k) || 0);
  const K = CHART.single, W = K.W, H = K.H, padL = K.padL, padR = K.padR;
  const vmax = Math.max(Math.max(...vals, upper), 0.01) * 1.18;
  const bw = (W - padL - padR) / Math.max(1, G.length);
  const base = H - K.padB, top = K.padT;
  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="Monthly resource for this project against the portfolio average">`];
  o.push(`<text class="ax" x="${padL-8}" y="${top-11}" text-anchor="end">${unitLabel()}</text>`);
  for (let i = 0; i <= 3; i++){
    const gv = vmax * i / 3, gy = base - (gv/vmax) * (base-top);
    o.push(`<line class="grid" x1="${padL}" y1="${gy.toFixed(1)}" x2="${W-padR+4}" y2="${gy.toFixed(1)}"/>`);
    o.push(`<text class="ax" x="${padL-8}" y="${(gy+3).toFixed(1)}" text-anchor="end">${fmt(gv)}</text>`);
  }
  // Stacked by PERSON. The bar height is the project's month either way; the split says
  // who it is made of, which is the question the bare bar could not answer. Order is by
  // total over the horizon so the stack does not reshuffle month to month.
  const {order, rest} = peopleOrder(Object.keys(M.people), sid => {
    let t = 0;
    for (const k of G) t += (C.projPers.get(pid+"|"+k) || new Map()).get(sid) || 0;
    return t;
  }, 20);
  G.forEach((k, i) => {
    const total = vals[i];
    const bys = C.projPers.get(pid+"|"+k) || new Map();
    const x0 = padL + i * bw + 2, w = bw - 4;
    // The month's standing against the reference lines belongs to the TOTAL, so it is
    // drawn once behind the stack rather than coloured into any one person's segment.
    if (total > upper || (total > 0 && total < lower)){
      const h = (total/vmax) * (base-top);
      o.push(`<rect class="mmark ${total > upper ? "over" : "under"}" x="${(x0-2).toFixed(1)}" `
        + `y="${(base-h-3).toFixed(1)}" width="${(w+4).toFixed(1)}" height="${(h+3).toFixed(1)}" rx="3"/>`);
    }
    const roles = new Map();
    for (const [ps, rn] of (C.who.get(pid+"|"+k) || [])) roles.set(ps, rn);
    let acc = 0;
    for (const sid of order){
      const v = sid === REST
        ? rest.reduce((t, r) => t + (bys.get(r) || 0), 0)
        : (bys.get(sid) || 0);
      if (v <= 0.004) continue;
      const y1 = base - (acc/vmax) * (base-top);
      acc += v;
      const y0 = base - (acc/vmax) * (base-top);
      const tip = sid === REST
        ? `<b>the other ${rest.length} people</b><br>${keyToLabel(k)} &#183; `
          + `<b>${fmt(v)} ${unitLabel()}</b> between them`
        : `<b>${esc(persName(sid))}</b> <span class="tr">${esc(sid)}</span>`
          + (roles.get(sid) ? `<br><span class="tr">${esc(roles.get(sid))}</span>` : "")
          + `<br>${keyToLabel(k)} &#183; <b>${fmt(v)} ${unitLabel()}</b> on this project`
          + `<span class="tr"> &#183; ${total > 0 ? (100*v/total).toFixed(0) : 0}% of the month</span>`
          + `<hr><b>${esc(M.projects[pid].project_name)}</b><br>`
          + `Total this month: <b>${fmt(total)} ${unitLabel()}</b>`
          + `<span class="tr"> across ${bys.size} ${bys.size === 1 ? "person" : "people"} `
          + `&#183; this project averages ${ownAvg.toFixed(2)}, an active project ${portAvg.toFixed(2)}</span>`;
      o.push(`<rect class="band" x="${x0.toFixed(1)}" y="${y0.toFixed(1)}" `
        + `width="${w.toFixed(1)}" height="${Math.max(0.8, y1-y0).toFixed(1)}" `
        + `fill="${sid === REST ? "var(--other)" : persColourOf(sid)}" data-tip="${att(tip)}"></rect>`);
    }
  });
  monthAxis(o, G, i => padL + i * bw, bw, H - 21, H - 6, top, base);
  for (const [v, cls, lab] of [[upper,"th-over",`2 × portfolio avg — ${upper.toFixed(2)}`],
                               [lower,"th-under",`0.5 × portfolio avg — ${lower.toFixed(2)}`],
                               [ownAvg,"th-own",`this project avg — ${ownAvg.toFixed(2)}`]]){
    if (v <= 0) continue;
    const yy = base - (v/vmax) * (base-top);
    o.push(`<line class="halo" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR+4}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<line class="${cls}" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR+4}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<text class="thlab ${cls}" x="${W-padR+8}" y="${(yy+3).toFixed(1)}">${lab}</text>`);
  }
  o.push(`<line class="base" x1="${padL}" y1="${base}" x2="${W-padR+4}" y2="${base}"/></svg>`);
  const leg = ['<ul class="legend">'];
  for (const sid of order)
    leg.push(`<li><span class="sw" style="background:${sid === REST ? "var(--other)" : persColourOf(sid)}"></span>`
      + `${esc(sid === REST ? `the other ${rest.length} people` : persName(sid))}</li>`);
  leg.push(`<li class="hint">tinted outline = the month's TOTAL crosses a reference line</li></ul>`);
  return {svg:o.join("") + (order.length ? leg.join("") : ""), portAvg, ownAvg};
}

/** The milestones a project passes in one month, as "name (date)" strings. */
function milestonesIn(pid, k){
  const y = Math.floor(k / 12), m = k % 12, out = [];
  for (const [nm, dates] of Object.entries((S.model.milestones[pid] || {})))
    for (const d of dates)
      if (d && d.getUTCFullYear() === y && d.getUTCMonth() === m) out.push([nm, d]);
  return out.sort((a, b) => a[1] - b[1]);
}

/** Monthly load for one person, each bar split into the projects that make it up.
 *
 *  The total on its own answers "is this person over the ceiling"; it cannot answer
 *  "because of what", which is the question anyone actually has next. Each segment is
 *  the project's own colour - the same colour it carries on the Overall tab - and its
 *  pop-up carries both halves: the project side of that month, and the person's total. */
function chartPersonStrip(sid){
  const M = S.model, C = S.calc, G = grid();
  const vals = G.map(k => C.persMonth.get(sid+"|"+k) || 0);
  const person = (M.people[sid] || {}).person_name || sid;
  const cap = num((M.people[sid] || {}).capacity_fte);

  // Stacking order: biggest contributor over the horizon at the bottom, so the bars read
  // consistently month to month instead of reshuffling wherever a project ends.
  const totals = new Map();
  for (const k of G)
    for (const [p, v] of (C.persProj.get(sid+"|"+k) || new Map()))
      totals.set(p, (totals.get(p) || 0) + v);
  const order = [...totals.entries()].filter(([, v]) => v > 0.004)
    .sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1)).map(x => x[0]);

  const W = 1080, H = 300, padL = 62, padR = 175;
  const vmax = Math.max(Math.max(...vals, M.OVER), 0.01) * 1.15;
  const bw = (W - padL - padR) / Math.max(1, G.length);
  const base = H - 44, top = 26;
  const o = [`<svg viewBox="0 0 ${W} ${H}" class="chart" style="min-width:${W}px" role="img" `
    + `aria-label="Monthly load for the selected person, split by project, against both thresholds">`];
  o.push(`<text class="ax" x="${padL-8}" y="${top-11}" text-anchor="end">${unitLabel()}</text>`);
  for (let i = 0; i <= 3; i++){
    const gv = vmax * i / 3, gy = base - (gv/vmax) * (base-top);
    o.push(`<line class="grid" x1="${padL}" y1="${gy.toFixed(1)}" x2="${W-padR+4}" y2="${gy.toFixed(1)}"/>`);
    o.push(`<text class="ax" x="${padL-8}" y="${(gy+3).toFixed(1)}" text-anchor="end">${fmt(gv)}</text>`);
  }
  G.forEach((k, i) => {
    const total = vals[i];
    const byp = C.persProj.get(sid+"|"+k) || new Map();
    const x0 = padL + i * bw + 2, w = bw - 4;
    // The month's standing, drawn once behind the stack: a segment cannot carry it,
    // because over-allocation is a property of the TOTAL, not of any one project.
    if (total > M.OVER || (total > 0 && total < M.UNDER)){
      const h = (total/vmax) * (base-top);
      o.push(`<rect class="mmark ${total > M.OVER ? "over" : "under"}" x="${(x0-2).toFixed(1)}" `
        + `y="${(base-h-3).toFixed(1)}" width="${(w+4).toFixed(1)}" height="${(h+3).toFixed(1)}" rx="3"/>`);
    }
    let acc = 0;
    for (const p of order){
      const v = byp.get(p) || 0;
      if (v <= 0.004) continue;
      const y1 = base - (acc/vmax) * (base-top);
      acc += v;
      const y0 = base - (acc/vmax) * (base-top);
      const ms = milestonesIn(p, k);
      const share = total > 0 ? (100 * v / total) : 0;
      const tip = `<b>${esc(M.projects[p].project_name)}</b> `
        + `<span class="tr">${esc(M.projects[p].project_type)}</span><br>`
        + `${keyToLabel(k)}<br>`
        + `Project milestone: ${ms.length
            ? ms.map(([nm, d]) => `${esc(nm)} <span class="tr">${ymd(d)}</span>`).join("<br>"
              + "&nbsp;".repeat(10))
            : `<span class="tr">none this month</span>`}<br>`
        + `<b>${fmt(v)} ${unitLabel()}</b> on this project `
        + `<span class="tr">&#183; ${share.toFixed(0)}% of the month</span>`
        + `<hr><b>${esc(person)}</b> <span class="tr">${esc(sid)}</span><br>`
        + `Total this month: <b>${fmt(total)} ${unitLabel()}</b>`
        + `<span class="tr"> across ${byp.size} project${byp.size === 1 ? "" : "s"}`
        + (cap ? ` &#183; capacity ${cap.toFixed(2)}` : "") + `</span>`
        + (total > M.OVER ? `<br><span class="tr">above the ${M.OVER.toFixed(2)} ceiling</span>`
           : total < M.UNDER ? `<br><span class="tr">below the ${M.UNDER.toFixed(2)} floor</span>` : "");
      o.push(`<rect class="band" x="${x0.toFixed(1)}" y="${y0.toFixed(1)}" `
        + `width="${w.toFixed(1)}" height="${Math.max(0.8, y1-y0).toFixed(1)}" `
        + `fill="${projColourOf(p)}" data-tip="${att(tip)}"></rect>`);
    }
  });
  monthAxis(o, G, i => padL + i * bw, bw, H - 21, H - 6, top, base);
  for (const [v, cls, lab] of [[M.OVER,"th-over",`ceiling ${M.OVER.toFixed(2)}`],
                               [M.UNDER,"th-under",`floor ${M.UNDER.toFixed(2)}`]]){
    const yy = base - (v/vmax) * (base-top);
    o.push(`<line class="halo" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR+4}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<line class="${cls}" x1="${padL}" y1="${yy.toFixed(1)}" x2="${W-padR+4}" y2="${yy.toFixed(1)}"/>`);
    o.push(`<text class="thlab ${cls}" x="${W-padR+8}" y="${(yy+3).toFixed(1)}">${lab}</text>`);
  }
  o.push(`<line class="base" x1="${padL}" y1="${base}" x2="${W-padR+4}" y2="${base}"/></svg>`);
  if (!order.length)
    return o.join("") + `<p class="note">This person draws no resource inside the horizon.</p>`;
  const leg = ['<ul class="legend">'];
  for (const p of order)
    leg.push(`<li><span class="sw" style="background:${projColourOf(p)}"></span>`
      + `${esc(M.projects[p].project_name)}</li>`);
  leg.push(`<li class="hint">tinted outline = the month's TOTAL is over the ceiling or `
    + `under the floor</li></ul>`);
  return o.join("") + leg.join("");
}

