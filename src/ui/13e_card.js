/* ============================================ one project or one person, on one card (R-67)

   The two source-data tabs are built for ENTERING a plan: a wide table of every field,
   and under it the panels of whichever row is selected. Reading one project there means
   scrolling a twenty-five column row sideways and then down through half a dozen panels,
   and reading one person the same. The request from the field was the other way round -
   click a name and see everything about that one, top to bottom, on one page.

   So a name in the Projects and People tables is a link, and it opens this card: one
   scrolling column holding what the tab spreads out - the figures that matter first, the
   two charts, the team or the assignments, the milestones and periods, the open issues,
   and every field of the record. READ-ONLY on purpose: the tables are where a plan is
   edited, and a second editing surface would be a second set of rules to keep in step.
   What it does offer is the way across - a person on a project's card opens that
   person's card, a project on a person's opens the project's, and Back returns - and the
   way back to the tab, with the row selected.

   THE NAME IS STILL EDITABLE. A link cannot also be the place a caret goes, so renaming
   moved to the pencil beside it (or F2 on the link). The pencil turns the cell back into
   the ordinary editable cell, with the value list and the same commit as any other, and
   the link comes back when the cell is left. */

let CARD = null;                  // {kind, id, back:[[kind, id], ...]} while it is open

const CARD_OF = {
  project: {sheet:"Project", tab:"t-proj", key:"project_id", name:"project_name"},
  person:  {sheet:"Person",  tab:"t-pers", key:"person_id",  name:"person_name"},
};
/** The column of each sheet whose cell opens a card. */
const CARD_NAME_COL = {Project:"project_name", Person:"person_name"};
const cardKind = sheet => sheet === "Project" ? "project" : sheet === "Person" ? "person" : null;

function cardRecord(kind, id){
  const M = S.model;
  if (!M || !CARD_OF[kind]) return null;
  return (kind === "project" ? M.projects : M.people)[id] || null;
}

/** Two letters for the round badge: the initials of the first two words that start with
 *  a letter - "DER-139 Phase 3" is DP, not D1 - or the first two letters of a one-word
 *  name, which is also what a Korean name written without a space gives. */
function monogram(s){
  const w = String(s || "").trim().split(/[\s\-_/.]+/).filter(x => /^\p{L}/u.test(x));
  if (!w.length) return "#";
  return (w.length > 1 ? w[0][0] + w[1][0] : w[0].slice(0, 2)).toUpperCase();
}

/* ------------------------------------------------------------------ the name cell */

/** The name cell of a saved project or person: the name as a link to its card, and a
 *  pencil to rename it. The cell keeps every attribute an editable cell carries, so the
 *  pencil only has to switch it on. */
function nameCellHTML(sheet, r, cls, tip){
  const kind = cardKind(sheet), col = CARD_NAME_COL[sheet], id = r[CARD_OF[kind].key];
  const v = r[col] === null || r[col] === undefined ? "" : String(r[col]);
  const what = kind === "project" ? "project" : "person";
  return `<td class="${cls} namecell" data-sheet="${att(sheet)}" data-row="${r.__row}" `
    + `data-col="${att(col)}" data-tip="${att(tip)}">`
    + `<button type="button" class="namelink" data-card="${kind}" data-cid="${att(id)}" `
    + `data-tip="${att(`<b>${esc(v || id)}</b><br>Click to open this ${what}'s card — `
      + `everything about it on one page.<br><span class="tr">&#9998; beside the name, or F2, `
      + `renames it</span>`)}">${v === "" ? `<i class="noname">no name</i>` : esc(v)}</button>`
    + `<button type="button" class="renbtn" data-rename tabindex="-1" aria-label="Rename" `
    + `data-tip="${att(`<b>Rename</b><br>Edit the ${what}'s name here, as any other cell.`)}">`
    + `</button></td>`;
}

/** The pencil: the cell becomes the ordinary editable cell, holding the plain value. */
function startRename(td){
  if (!td || td.isContentEditable || !td.dataset.sheet) return;
  const r = (S.model.raw[td.dataset.sheet] || []).find(x => x.__row === +td.dataset.row);
  td.dataset.link = td.innerHTML;
  td.textContent = r && r[td.dataset.col] !== null && r[td.dataset.col] !== undefined
    ? String(r[td.dataset.col]) : "";
  td.setAttribute("contenteditable", "true");
  td.classList.add("renaming");
  td.focus();
  const rg = document.createRange();
  rg.selectNodeContents(td);
  const sel = getSelection();
  sel.removeAllRanges();
  sel.addRange(rg);
}

/** And back to the link once the cell is left with nothing changed. A changed name has
 *  already been committed, which redraws the table and the link with it. */
function endRename(td){
  if (!td || !td.isConnected || !td.classList.contains("renaming")) return;
  if (document.activeElement === td) return;
  td.removeAttribute("contenteditable");
  td.classList.remove("renaming");
  td.innerHTML = td.dataset.link || esc(td.textContent);
  delete td.dataset.link;
}

/* ------------------------------------------------------------------ the dialog */

function cardDialog(){
  let d = el("carddlg");
  if (d) return d;
  d = document.createElement("dialog");
  d.id = "carddlg";
  d.className = "card";
  d.setAttribute("aria-labelledby", "cardTitle");
  d.innerHTML = `<div class="card-h">
      <button class="btn tiny" id="cardBack" data-cardback hidden>&#8249; Back</button>
      <div class="card-who" id="cardHead"></div>
      <div class="card-nav">
        <button class="btn tiny" id="cardPrev" data-cardstep="-1" aria-label="Previous">&#8249;</button>
        <span id="cardPos"></span>
        <button class="btn tiny" id="cardNext" data-cardstep="1" aria-label="Next">&#8250;</button>
      </div>
      <button class="btn" id="cardGo" data-cardgo></button>
      <button class="btn primary" id="cardClose">Close</button></div>
    <div class="card-b" id="cardBody" tabindex="-1"></div>`;
  document.body.appendChild(d);
  d.querySelector("#cardClose").onclick = () => d.close();
  d.addEventListener("close", () => { CARD = null; });
  d.addEventListener("click", e => {
    // The backdrop is the dialog itself: everything drawn is inside .card-h or .card-b.
    if (e.target === d) return d.close();
    if (e.target.closest("[data-cardback]")){
      const [kind, id] = CARD.back.pop() || [];
      if (kind) showCard(kind, id);
      return;
    }
    const st = e.target.closest("[data-cardstep]");
    if (st){
      const ids = cardOrder(CARD.kind), i = ids.indexOf(CARD.id);
      const j = i + +st.dataset.cardstep;
      if (i >= 0 && j >= 0 && j < ids.length){ CARD.back = []; showCard(CARD.kind, ids[j]); }
      return;
    }
    if (e.target.closest("[data-cardgo]")) cardGo();
  });
  /* Left and right step through the list. On the document rather than the dialog: a
     button that hides itself as it is pressed - Back, on the last step back - drops the
     focus to the body, and a listener on the dialog would never hear the next key. Not
     while another dialog has the keys, such as the team opened from the card. */
  document.addEventListener("keydown", e => {
    if (!d.open || (e.key !== "ArrowLeft" && e.key !== "ArrowRight")) return;
    const a = document.activeElement;
    if (a && a !== document.body && !d.contains(a)) return;
    if (e.target.closest && e.target.closest("input, select, textarea, [contenteditable='true']"))
      return;
    const b = el(e.key === "ArrowLeft" ? "cardPrev" : "cardNext");
    if (b && !b.disabled){ e.preventDefault(); b.click(); }
  });
  return d;
}

/** Open the card of one project or one person. `across` is set when it is opened from
 *  inside the card, which is what gives Back somewhere to go. */
function openCard(kind, id, across){
  if (!cardRecord(kind, id)) return;
  const back = across && CARD && !(CARD.kind === kind && CARD.id === id)
    ? [...CARD.back, [CARD.kind, CARD.id]] : across && CARD ? CARD.back : [];
  const d = cardDialog();
  CARD = {kind, id, back};
  if (!d.open) d.showModal();
  showCard(kind, id);
}

function showCard(kind, id){
  CARD.kind = kind; CARD.id = id;
  drawCard();
  const body = el("cardBody");
  body.scrollTop = 0;
  /* The focus goes to the page being read unless it is on a control that is still there
     to press again - Next, held down the list. A link in the old page, or Back once it
     has hidden itself, would otherwise leave it on nothing, and the arrow keys and Page
     Down would have nowhere to go. */
  const a = document.activeElement, d = el("carddlg");
  if (!a || !d.contains(a) || !a.offsetParent) body.focus({preventScroll:true});
}

function closeCard(){ const d = el("carddlg"); if (d && d.open) d.close(); }

/** Redraw an open card after an edit made anywhere - the team dialog opened from it is
 *  the usual one - at the same scroll position. */
function cardRefresh(){
  const d = el("carddlg");
  if (!CARD || !d || !d.open) return;
  const b = el("cardBody"), keep = b.scrollTop;
  drawCard();
  b.scrollTop = keep;
}

/** The order Previous and Next walk: the rows of the table the card was opened from, as
 *  they stand - filtered, in the order shown - or every record when that table is not
 *  drawn, as when the card was reached from the other tab's card. */
function cardOrder(kind){
  const K = CARD_OF[kind], ids = [];
  const t = document.querySelector(`#${K.tab} .data-t[data-sheet="${K.sheet}"]`);
  if (t) for (const tr of t.querySelectorAll("tbody tr[data-id]"))
    if (cardRecord(kind, tr.dataset.id) && !ids.includes(tr.dataset.id)) ids.push(tr.dataset.id);
  if (CARD && ids.includes(CARD.id)) return ids;
  return Object.keys(kind === "project" ? S.model.projects : S.model.people);
}

/** To the tab, with the row selected and its own panels underneath it in view. */
function cardGo(){
  if (!CARD) return;
  const {kind, id} = CARD, K = CARD_OF[kind];
  closeCard();
  if (kind === "project") S.selProj = id;
  else { S.selPers = id; S.selAsg = null; }
  showTab(K.tab); renderAll(); showTab(K.tab);
  const row = [...document.querySelectorAll(`#${K.tab} .data-t[data-sheet="${K.sheet}"] tbody tr`)]
    .find(tr => tr.dataset.id === id);
  if (row) row.scrollIntoView({block:"nearest"});
  const det = el(kind === "project" ? "projDetail" : "persDetail");
  if (det) det.scrollIntoView({block:"start"});
}

function drawCard(){
  const d = el("carddlg");
  if (!d || !d.open || !CARD) return;
  const rec = cardRecord(CARD.kind, CARD.id);
  if (!rec){ d.close(); return; }
  const isP = CARD.kind === "project", K = CARD_OF[CARD.kind];
  const body = el("cardBody");
  // The charts are drawn to the card's own width, as the page's are to the page's.
  const pad = parseFloat(getComputedStyle(body).paddingLeft) || 24;
  const room = body.clientWidth - 2 * pad - 18;
  body.innerHTML = withRoom(room, () => isP ? cardProject(CARD.id) : cardPerson(CARD.id));

  const name = rec[K.name] || CARD.id;
  const tint = isP ? projColourOf(CARD.id) : persColourOf(CARD.id);
  d.style.setProperty("--card-tint", tint);
  el("cardHead").innerHTML = `<span class="mono${isP ? " sq" : ""}" aria-hidden="true">`
    + `${esc(monogram(name))}</span><div class="card-tt"><span class="card-kind">`
    + `${isP ? "Project" : "Person"}</span><strong id="cardTitle">${esc(name)}</strong>`
    + `<span class="card-sub">${isP ? cardProjectSub(CARD.id) : cardPersonSub(CARD.id)}</span></div>`;
  const ids = cardOrder(CARD.kind), i = ids.indexOf(CARD.id);
  el("cardPrev").disabled = i <= 0;
  el("cardNext").disabled = i < 0 || i >= ids.length - 1;
  el("cardPos").textContent = i >= 0 ? `${i + 1} of ${ids.length}` : "";
  el("cardBack").hidden = !CARD.back.length;
  const go = el("cardGo");
  go.textContent = `Show on ${isP ? "Source data (project)" : "Source data (person)"}`;
  go.title = "Close the card and select this row on its tab, with its own panels in view";
  cueScrollers();
}

/* ------------------------------------------------------------------ shared pieces */

/** A small figure with its label, the card's equivalent of the Overall tiles. */
const cardKpi = (label, value, sub, cls, tip) =>
  `<div class="kpi${cls ? " " + cls : ""}"${tip ? ` data-tip="${att(tip)}"` : ""}>`
  + `<span class="kl">${label}</span><span class="kv">${value}</span>`
  + `<span class="ks">${sub || "&nbsp;"}</span></div>`;

const cardSec = (title, aside, inner, cls) =>
  `<section class="csec${cls ? " " + cls : ""}"><div class="csec-h"><h3>${title}</h3>`
  + `${aside ? `<span class="csec-a">${aside}</span>` : ""}</div>${inner}</section>`;

/** How far through its life something dated is: a track from start to end with today
 *  marked on it, and the words for where today falls. Without both dates there is no
 *  track, and `missing` is what is said instead - nothing, if it is empty. */
function cardLife(start, end, missing){
  if (!(start instanceof Date) || !(end instanceof Date) || end < start)
    return missing ? `<p class="note life-none">${missing}</p>` : "";
  const t = today().getTime(), a = start.getTime(), b = end.getTime();
  const f = Math.max(0, Math.min(1, (t - a) / Math.max(1, b - a)));
  const months = monthsBetween(start, end).length;
  const nowK = nowKey(), ka = monthKey(start.getUTCFullYear(), start.getUTCMonth());
  const kb = monthKey(end.getUTCFullYear(), end.getUTCMonth());
  const where = t < a ? `starts in ${ka - nowK} month(s)`
    : t > b ? `ended ${nowK - kb} month(s) ago`
    : `${Math.round(f * 100)}% through — month ${nowK - ka + 1} of ${months}`;
  return `<div class="life"><div class="life-ends"><span><b>${ymd(start)}</b> start</span>`
    + `<span class="life-mid">${months} months &#183; ${where}</span>`
    + `<span>end <b>${ymd(end)}</b></span></div>`
    + `<div class="life-track"><span class="life-fill" style="width:${(f * 100).toFixed(1)}%"></span>`
    + (t >= a && t <= b ? `<span class="life-now" style="left:${(f * 100).toFixed(1)}%" `
      + `data-tip="${att(`<b>Today</b><br>${todayLabel()}`)}"></span>` : "")
    + `</div></div>`;
}

/** A load against the two thresholds, as a bar: the floor and the ceiling marked on it. */
function cardMeter(v, vmax){
  const M = S.model, top = Math.max(vmax, M.OVER * 1.2, 0.01);
  const pct = x => `${Math.min(100, (x / top) * 100).toFixed(1)}%`;
  const cls = v > M.OVER ? "over" : v > 0 && v < M.UNDER ? "under" : "";
  return `<span class="meter ${cls}"><span class="mfill" style="width:${pct(v)}"></span>`
    + `<span class="mtick" style="left:${pct(M.UNDER)}"></span>`
    + `<span class="mtick hi" style="left:${pct(M.OVER)}"></span></span>`;
}

/** Every field of the record, in labelled groups - nothing the tables hold is missing
 *  from the card. Groups are named for what the fields are for; anything a later schema
 *  adds that no group names is shown under the last heading rather than dropped. */
function cardFields(sheet, rec, groups){
  const cols = entryCols(sheet), named = new Set(groups.flatMap(g => g[1]));
  const rest = cols.filter(c => !named.has(c));
  const all = groups.map(([t, cs]) => [t, cs.filter(c => cols.includes(c))]);
  if (rest.length) all[all.length - 1][1].push(...rest);
  return `<div class="fgroups">` + all.filter(g => g[1].length).map(([t, cs]) =>
    `<div class="fgroup"><h4>${esc(t)}</h4><dl>` + cs.map(c => {
      const v = rec[c];
      const s = v instanceof Date ? ymd(v) : v === null || v === undefined ? "" : String(v);
      return `<div class="f"><dt data-tip="${att(`${colHead(c)}<br>${COLUMN_HELP[c] || ""}`)}">`
        + `${esc(COLUMN_LABEL[c] || c)}</dt><dd${s === "" ? ' class="none"' : ""}>`
        + `${s === "" ? "—" : esc(s)}</dd></div>`;
    }).join("") + `</dl></div>`).join("") + `</div>`;
}

const cardDate = d => d instanceof Date ? ymd(d) : "";
/** An assignment's window in words, with the project's own dates where it leaves one open. */
function cardWindow(a){
  const pr = S.model.projects[a.project_id] || {};
  const f = cardDate(a.assign_start_date), t = cardDate(a.assign_end_date);
  return `${f || `<span class="muted">${cardDate(pr.start_date) || "start"}</span>`} &#8594; `
    + `${t || `<span class="muted">${cardDate(pr.end_date) || "end"}</span>`}`;
}

/* ------------------------------------------------------------------ a project */

function cardProjectSub(pid){
  const pr = S.model.projects[pid];
  return `<span class="idchip">${esc(pid)}</span>${typePill(pid)}${phasePill(pid)}`
    + (pr.work_scope_type ? `<span class="scope">${esc(pr.work_scope_type)}</span>` : "")
    + (pr.status ? `<span class="scope k">${esc(pr.status)}</span>` : "")
    + estimationPill(pid);
}

function cardProject(pid){
  const M = S.model, C = S.calc, pr = M.projects[pid], G = grid(), U = unitLabel();
  let tot = 0, peak = 0, peakK = null, active = 0;
  for (const k of G){
    const v = C.projMonth.get(pid + "|" + k) || 0;
    tot += v;
    if (v > 0.004) active++;
    if (v > peak){ peak = v; peakK = k; }
  }
  const nk = nowKey(), nowV = C.projMonth.get(pid + "|" + nk) || 0;
  const per = periodOf(pid, nk);
  const team = M.assignments.filter(a => a.project_id === pid);
  const people = [...new Set(team.map(a => a.person_id))];
  const issues = gapRows([pid]), open = issues.filter(r => !(r.rev && r.rev.closed));
  const n = d => open.filter(r => r.dir === d).length;
  const planned = num(pr.planned_member_count);

  const kpis = `<div class="kpis">`
    + cardKpi("Team", people.length, `${team.length} assignment(s)`
        + (planned !== null && planned !== undefined ? ` &#183; planned ${planned}` : ""), "",
        "<b>Team</b><br>The distinct people with an assignment on this project, and how many "
        + "assignments they hold between them.")
    + cardKpi("This month", nowV > 0.004 ? fmt(nowV) : "—",
        `${keyToLabel(nk)}${per ? ` &#183; ${esc(per.name)}` : ""}`, "now",
        `<b>${keyToLabel(nk)}</b><br>What the project draws in the current month, and the period `
        + `it is in.`)
    + cardKpi("Average a month", active ? fmt(tot / active) : "—",
        `${U} over ${active} active month(s) in view`)
    + cardKpi("Peak month", peak > 0.004 ? fmt(peak) : "—", peakK !== null && peak > 0.004
        ? keyToLabel(peakK) : "nothing in view")
    + cardKpi("Total in view", fmt(tot), `${U}-months over ${G.length} months`)
    + cardKpi("Off the standard", open.length,
        open.length ? `${n("short")} short &#183; ${n("over")} over`
          + (n("unstaffed") ? ` &#183; ${n("unstaffed")} not staffed` : "")
          + (issues.length - open.length ? ` &#183; &#10003; ${issues.length - open.length} reviewed` : "")
        : issues.length ? `all ${issues.length} reviewed` : "every month on its standard",
        open.length ? "gap" : "ok",
        "<b>Off the standard</b><br>Months where what this project needs is not what it is "
        + "given (V-34), still open. Each one is listed under Issues below.")
    + `</div>`;

  const util = chartProjectUtil(pid);
  const ms = Object.entries(M.milestones[pid] || {})
    .flatMap(([nm, ds]) => ds.filter(Boolean).map(d => [nm, d]))
    .sort((a, b) => a[1] - b[1]);
  const nowT = today().getTime();
  const nextMs = ms.find(([, d]) => d.getTime() >= nowT);
  const msList = ms.length ? `<ol class="mslist">` + ms.map(([nm, d]) => {
      const hl = (M.msHighlight[pid] || {})[`${nm}|${ymd(d)}`] || "";
      const key = KEY_MILESTONES.has(nm), past = d.getTime() < nowT;
      return `<li class="${past ? "past" : "next"}`
        + `${nextMs && nextMs[0] === nm && +nextMs[1] === +d ? " upcoming" : ""}">`
        + `<span class="dot${key ? " key" : ""}"${hl ? ` style="background:${HIGHLIGHT_FILL[hl]}"` : ""}></span>`
        + `<span class="mnm">${esc(nm)}${key ? ` <span class="tr">sets a period boundary</span>` : ""}</span>`
        + `<span class="mdt">${ymd(d)}</span></li>`;
    }).join("") + `</ol>` : `<p class="note">No milestones are dated yet.</p>`;

  const per2 = (M.periods[pid] || []).slice()
    .sort((a, b) => (a.period_start || 0) - (b.period_start || 0));
  const perRows = per2.map(s => {
    const {hl} = periodColour(s), w = num(s.weight);
    const std = num(stdWeight(M, pr, s.period_name));
    const on = per && per.name === s.period_name;
    return `<tr${on ? ' class="on"' : ""}><td><span class="chip"${hl ? ` style="background:${HIGHLIGHT_FILL[hl]}"` : ""}>`
      + `</span>${esc(s.period_name)}${on ? ` <span class="nowpill">now</span>` : ""}</td>`
      + `<td>${cardDate(s.period_start)} &#8594; ${cardDate(s.period_end)}</td>`
      + `<td class="num">${w === null || w === undefined ? "—" : w.toFixed(2)}</td>`
      + `<td class="num">${std === null || std === undefined ? `<span class="muted">none</span>`
          : std.toFixed(2) + (w === null || w === undefined ? "" : ` <span class="muted">&#8594; ${(std * w).toFixed(2)}</span>`)}</td></tr>`;
  }).join("");

  const ks = teamMonths(pid);
  const teamRows = team.slice().sort((a, b) =>
      String(a.role_name || "").localeCompare(String(b.role_name || ""))
      || String((M.people[a.person_id] || {}).person_name || "").localeCompare(
         String((M.people[b.person_id] || {}).person_name || "")))
    .map(a => {
      const pe = M.people[a.person_id] || {}, L = teamLoad(a.person_id, ks);
      const here = ks.reduce((t, k) => t + (C.cell.get([pid, a.person_id, a.role_name, k].join("|")) || 0), 0)
        / Math.max(1, ks.length);
      const manual = M.isManual && M.isManual("assignment", a.assignment_id);
      return `<tr><td><button type="button" class="plink" data-card="person" data-cid="${att(a.person_id)}">`
        + `<span class="mono xs" style="--card-tint:${persColourOf(a.person_id)}">`
        + `${esc(monogram(pe.person_name || a.person_id))}</span>${esc(pe.person_name || a.person_id)}</button>`
        + `<span class="sub">${esc(pe.department || "")}</span></td>`
        + `<td>${esc(a.role_name || "")}${manual ? ` <span class="estb manual sm">manual</span>` : ""}</td>`
        + `<td>${cardWindow(a)}</td>`
        + `<td class="num">${a.person_weight === null || a.person_weight === undefined ? "—" : Number(a.person_weight).toFixed(2)}</td>`
        + `<td class="num">${fmt(here)}</td>`
        + `<td class="load">${cardMeter(L.avg, L.peak)}<span class="sub">avg ${fmt(L.avg)} &#183; peak ${fmt(L.peak)}`
        + `${L.over ? ` &#183; <b class="gover">&#9650; over in ${L.over} mo</b>` : ""}</span></td></tr>`;
    }).join("");

  const issueRows = open.slice().sort((a, b) => a.k - b.k).map(r => {
    const g = r.dir === "short" ? ["gshort", "&#9660; short"] : r.dir === "over" ? ["gover", "&#9650; over"]
      : ["gunst", "&#9702; not staffed"];
    return `<tr class="gaprow ${r.dir}" data-gap="${att(pid)}" data-gk="${r.k}" data-gapis="${r.dir}" `
      + `tabindex="0" role="button"><td>${keyToLabel(r.k)}</td><td class="${g[0]}">${g[1]}</td>`
      + `<td class="num">${r.demand.toFixed(2)}</td><td class="num">${r.applied.toFixed(2)}</td>`
      + `<td class="num ${g[0]}">${Math.abs(r.gap).toFixed(2)}</td>`
      + `<td>${r.rev ? `<span class="revtag ${r.rev.fix ? "fix" : r.rev.changed ? "stale" : "done"}">`
        + `${esc(r.rev.status || "reviewed")}</span>` : `<span class="muted">not reviewed</span>`}</td></tr>`;
  }).join("");

  return `${cardLife(pr.start_date, pr.end_date,
      "The start or end date is not entered yet, so there is no span to draw.")}
    ${kpis}
    ${cardSec("Monthly resource", `${G.length} months &#183; stacked by person`,
      `<div class="scrollx fit">${util.svg}</div>`)}
    ${cardSec("Timeline", `${per2.length} period(s) &#183; ${ms.length} milestone(s)`,
      `<div class="scrollx fit">${chartGantt([pid], {single:true,
        note:`${ymd(pr.start_date)} &#8594; ${ymd(pr.end_date)}`})}</div>`)}
    ${cardSec("Team", `<button class="btn tiny primary" data-team="${att(pid)}">Change team</button>`,
      teamRows ? `<div class="ctwrap"><table class="ct"><thead><tr><th>Person</th><th>Role</th>
        <th>On the project</th><th class="num">Weight</th><th class="num">${U} here<span class="sub">avg in view</span></th>
        <th>Their whole load<span class="sub">over this project's months</span></th></tr></thead>
        <tbody>${teamRows}</tbody></table></div>`
      : `<p class="note">Nobody is on this project yet. <strong>Change team</strong> adds somebody.</p>`)}
    <div class="csplit">
      ${cardSec("Milestones", `${ms.length}`, msList)}
      ${cardSec("Periods", `${per2.length}${per2.some(p => p.__derived) ? " &#183; derived" : ""}`,
        per2.length ? `<div class="ctwrap"><table class="ct"><thead><tr><th>Period</th><th>Dates</th>
          <th class="num">Weight</th><th class="num">Standard<span class="sub">a month</span></th></tr></thead>
          <tbody>${perRows}</tbody></table></div>`
        : `<p class="note">No periods yet.</p>`)}
    </div>
    ${cardSec("Issues — standard vs staffed", open.length ? `${open.length} open` : "none open",
      open.length ? `<div class="ctwrap"><table class="ct gapt"><thead><tr><th>Month</th><th>Issue</th>
        <th class="num">Needs</th><th class="num">Staffed</th><th class="num">Gap</th><th>Review</th></tr></thead>
        <tbody>${issueRows}</tbody></table></div>
        <p class="note">Click a month to see the figures behind it and to record a review.</p>`
      : `<p class="note">${issues.length ? `Every issue on this project has been reviewed and closed.`
                                         : `Every month in the plan is staffed at its standard.`}</p>`)}
    ${cardSec("All fields", "as in the Projects table", cardFields("Project", pr, [
      ["Identity", ["project_id", "project_name", "project_type", "project_category",
                    "clinical_phase", "work_scope_type", "status"]],
      ["Plan", ["start_date", "end_date", "total_period_months", "planned_member_count",
                "estimation_type"]],
      ["Set-up", ["outsourcing_scope_det", "EDC_setup", "EDC_system", "DataReviewSystem_setup",
                  "DataReviewSystem", "RBQM_setup", "RBQM_system", "DM_conduct"]],
      ["Notes", ["note_1", "note_2", "note_3", "note_4", "note_5"]],
    ]))}`;
}

/* ------------------------------------------------------------------ a person */

function cardPersonSub(sid){
  const pe = S.model.people[sid], cap = num(pe.capacity_fte);
  return `<span class="idchip">${esc(sid)}</span>`
    + (pe.department ? `<span class="scope">${esc(pe.department)}</span>` : "")
    + (pe.primary_role ? `<span class="scope k">${esc(pe.primary_role)}</span>` : "")
    + (cap !== null && cap !== undefined ? `<span class="scope">capacity ${cap.toFixed(2)} FTE</span>` : "");
}

function cardPerson(sid){
  const M = S.model, C = S.calc, pe = M.people[sid], G = grid(), U = unitLabel();
  let tot = 0, peak = 0, peakK = null, over = 0, under = 0;
  for (const k of G){
    const v = C.persMonth.get(sid + "|" + k) || 0;
    tot += v;
    if (v > peak){ peak = v; peakK = k; }
    if (v > M.OVER) over++;
    else if (v > 0.004 && v < M.UNDER) under++;
  }
  const nk = nowKey(), nowV = C.persMonth.get(sid + "|" + nk) || 0;
  const mine = M.assignments.filter(a => a.person_id === sid);
  const pids = [...new Set(mine.map(a => a.project_id))].filter(p => M.projects[p]);
  const nowOn = [...(C.persProj.get(sid + "|" + nk) || new Map())].filter(([, v]) => v > 0.004).length;

  const kpis = `<div class="kpis">`
    + cardKpi("Projects", pids.length, `${mine.length} assignment(s) &#183; ${nowOn} active now`)
    + cardKpi("This month", fmt(nowV), `${keyToLabel(nk)}`
        + `<span class="kmeter">${cardMeter(nowV, peak)}</span>`,
        nowV > M.OVER ? "over now" : nowV > 0.004 && nowV < M.UNDER ? "under now" : "now",
        `<b>${keyToLabel(nk)}</b><br>This person's load in the current month, against the `
        + `${M.UNDER.toFixed(2)} floor and the ${M.OVER.toFixed(2)} ceiling marked on the bar.`)
    + cardKpi("Average a month", fmt(G.length ? tot / G.length : 0), `${U} over ${G.length} months in view`)
    + cardKpi("Peak month", fmt(peak), peakK !== null && peak > 0.004 ? keyToLabel(peakK) : "nothing in view",
        peak > M.OVER ? "over" : "")
    + cardKpi("Over the ceiling", over ? `&#9650; ${over}` : "0",
        `month(s) above ${M.OVER.toFixed(2)} FTE`, over ? "over" : "ok")
    + cardKpi("Under the floor", under ? `&#9660; ${under}` : "0",
        `month(s) below ${M.UNDER.toFixed(2)} FTE`, under ? "under" : "ok")
    + `</div>`;

  const {assign} = personSpans(sid);
  const asgRows = mine.slice().sort((a, b) => byRank(a.project_id, b.project_id)).map(a => {
    const pr = M.projects[a.project_id] || {};
    let t = 0;
    for (const k of G) t += C.cell.get([a.project_id, sid, a.role_name, k].join("|")) || 0;
    const manual = M.isManual && M.isManual("assignment", a.assignment_id);
    return `<tr><td><button type="button" class="plink" data-card="project" data-cid="${att(a.project_id)}">`
      + `<span class="mono xs sq" style="--card-tint:${projColourOf(a.project_id)}">`
      + `${esc(monogram(pr.project_name || a.project_id))}</span>${esc(pr.project_name || a.project_id)}</button>`
      + `<span class="sub">${esc(a.project_id)}${M.projects[a.project_id] ? " &#183; " + esc(pr.project_type || "") : ""}</span></td>`
      + `<td>${esc(a.role_name || "")}${manual ? ` <span class="estb manual sm">manual</span>` : ""}</td>`
      + `<td>${cardWindow(a)}</td>`
      + `<td class="num">${a.person_weight === null || a.person_weight === undefined ? "—" : Number(a.person_weight).toFixed(2)}</td>`
      + `<td class="num">${fmt(G.length ? t / G.length : 0)}</td>`
      + `<td class="num">${fmt(t)}</td></tr>`;
  }).join("");

  return `${cardLife(pe.employment_start, pe.employment_end, "")}
    ${kpis}
    ${cardSec("Monthly load", `${G.length} months &#183; stacked by project`,
      `<div class="scrollx fit">${chartPersonStrip(sid)}</div>`)}
    ${cardSec("Project timeline", `${pids.length} project(s)`,
      pids.length ? `<div class="scrollx fit">${chartGantt(pids.slice().sort(byRank), {assign,
          who: pe.person_name || sid, note: `The bar under each row is when ${esc(pe.person_name || sid)} is on it.`})}</div>`
      : `<p class="note">No assignment yet.</p>`)}
    ${cardSec("Assignments", `${mine.length}`,
      asgRows ? `<div class="ctwrap"><table class="ct"><thead><tr><th>Project</th><th>Role</th>
        <th>On the project</th><th class="num">Weight</th><th class="num">${U} a month<span class="sub">avg in view</span></th>
        <th class="num">${U}-months<span class="sub">in view</span></th></tr></thead>
        <tbody>${asgRows}</tbody></table></div>`
      : `<p class="note">No assignment yet. Assignments are entered on Source data (person).</p>`)}
    ${cardSec("All fields", "as in the People table", cardFields("Person", pe, [
      ["Identity", ["person_id", "person_name", "department", "primary_role"]],
      ["Capacity", ["capacity_fte", "employment_start", "employment_end"]],
      ["Notes", ["note_1", "note_2", "note_3", "note_4", "note_5"]],
    ]))}`;
}
