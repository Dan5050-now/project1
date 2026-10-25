/* ================================================= the project team, in one place (R-66)

   Changing who is on a project used to mean visiting each person: open Source data
   (person), find them, find the assignment, change it - and again for the next one. That
   is the wrong way round for the question actually being asked, which is asked of the
   PROJECT, while looking at the whole picture: "PRJ-007 is over; take Lee off it and put
   Park on instead". So the team is edited where the project is looked at - from Resource
   by project on Overall and from the project's Utilisation on Source data (project) - in
   one dialog: swap a person, change a role, a window or a weight, take somebody off, or
   add somebody, with each person's load shown beside their name so the choice is made
   knowing who has room.

   IT IS THE ASSIGNMENT SHEET, EDITED THE ORDINARY WAY. Every change is a pending edit
   like a typed cell - the same edit session, the same re-validation that refuses an edit
   introducing an error, the same change log - so it shows at once on every tab, the
   person tab's Assignments table included, and is kept by Save or undone by Leave without
   change exactly as anything else is. Nothing here writes around that path. */

let TEAM = null;                  // the project the dialog is open on

/** Where in the horizon a project runs - the months its people's loads are judged over. */
function teamMonths(pid){
  const pr = S.model.projects[pid] || {}, G = grid();
  const k = d => d ? monthKey(d.getUTCFullYear(), d.getUTCMonth()) : null;
  const a = k(pr.start_date), b = k(pr.end_date);
  const ks = G.filter(m => (a === null || m >= a) && (b === null || m <= b));
  return ks.length ? ks : G;
}

/** A person's load over some months: mean, peak, and how many are over the ceiling. */
function teamLoad(sid, ks){
  const C = S.calc, M = S.model;
  let t = 0, peak = 0, over = 0;
  for (const k of ks){
    const v = C.persMonth.get(sid + "|" + k) || 0;
    t += v; peak = Math.max(peak, v); if (v > M.OVER) over++;
  }
  return {avg: ks.length ? t / ks.length : 0, peak, over};
}
const loadText = L => `avg ${fmt(L.avg)} · peak ${fmt(L.peak)}`
  + (L.over ? ` · over in ${L.over} mo` : "");

function teamDialog(){
  let d = el("teamdlg");
  if (d) return d;
  d = document.createElement("dialog");
  d.id = "teamdlg";
  d.className = "big";
  d.setAttribute("aria-labelledby", "teamTitle");
  d.innerHTML = `<div class="dlg-h"><strong id="teamTitle"></strong>
      <span class="tmpend" id="teamPend"></span>
      <button class="btn" id="teamSave" style="margin-left:auto">Save changes</button>
      <button class="btn primary" id="teamClose">Close</button></div>
    <div class="dlg-b" id="teamBody"></div>`;
  document.body.appendChild(d);
  d.querySelector("#teamClose").onclick = () => d.close();
  /* Save is the page's own Save - the one that asks about findings and writes the
     change log - so the dialog steps aside for it rather than saving by another route. */
  d.querySelector("#teamSave").onclick = () => { d.close(); el("saveBtn") && el("saveBtn").click(); };
  d.addEventListener("close", () => { TEAM = null; });
  d.addEventListener("change", e => {
    const f = e.target.closest("[data-tm]");
    if (f) teamField(f);
  });
  d.addEventListener("click", e => {
    const del = e.target.closest("[data-tmdel]");
    if (del) return teamRemove(+del.dataset.tmdel);
    if (e.target.closest("[data-tmadd]")) return teamAdd();
    const pick = e.target.closest("[data-tmpick]");
    if (pick){ el("tmP").value = pick.dataset.tmpick; el("tmP").focus(); }
  });
  return d;
}

/** Open the team of one project. */
function openTeam(pid){
  if (!S.model || !S.model.projects[pid]) return;
  TEAM = pid;
  const d = teamDialog();
  drawTeam();
  if (!d.open) d.showModal();
}

/** Redraw an open team dialog after any edit - its own or one made elsewhere. */
function teamRefresh(){ if (TEAM && el("teamdlg") && el("teamdlg").open) drawTeam(); }

function teamSay(kind, msg){
  const m = el("teamMsg");
  if (!m) return false;
  m.className = "tmmsg" + (kind ? " " + kind : "");
  m.textContent = msg;
  m.hidden = !msg;
  return false;
}

function drawTeam(){
  const M = S.model, C = S.calc, pid = TEAM, pr = M.projects[pid];
  if (!pr) { el("teamdlg").close(); return; }
  const ks = teamMonths(pid), G = grid();
  const rows = (M.raw.Assignment || []).filter(a => a.project_id === pid && !a.__new)
    .sort((a, b) => String(a.role_name || "").localeCompare(String(b.role_name || ""))
      || String((M.people[a.person_id] || {}).person_name || a.person_id || "")
           .localeCompare(String((M.people[b.person_id] || {}).person_name || b.person_id || "")));
  const people = Object.keys(M.people).sort((a, b) =>
    String(M.people[a].person_name || a).localeCompare(String(M.people[b].person_name || b)));
  const load = Object.fromEntries(people.map(s => [s, teamLoad(s, ks)]));
  const roles = suggestionsFor("Assignment", "role_name", {project_id: pid});
  const ymdv = d => d instanceof Date ? ymd(d) : "";
  const peopleOpts = sel => people.map(s => `<option value="${att(s)}"${s === sel ? " selected" : ""}>`
    + `${esc(M.people[s].person_name || s)} — ${esc(loadText(load[s]))}</option>`).join("");
  const roleOpts = sel => [...new Set([...(sel ? [sel] : []), ...roles])].map(r =>
    `<option${r === sel ? " selected" : ""}>${esc(r)}</option>`).join("");
  const span = `${ymd(pr.start_date) || "?"} to ${ymd(pr.end_date) || "?"}`;
  const inView = ks === G ? "the months in view" : `${keyToLabel(ks[0])} – ${keyToLabel(ks[ks.length - 1])}`;

  el("teamTitle").textContent = `Team — ${pr.project_name} (${pid})`;
  const n = S.pending.length;
  el("teamPend").textContent = n ? `${n} unsaved change(s)` : "";
  el("teamSave").disabled = !n;

  const body = rows.map(a => {
    const share = ks.reduce((t, k) => t + (C.cell.get([pid, a.person_id, a.role_name, k].join("|")) || 0), 0)
      / Math.max(1, ks.length);
    const L = load[a.person_id] || {avg: 0, peak: 0, over: 0};
    const manual = M.isManual && M.isManual("assignment", a.assignment_id);
    return `<tr data-row="${a.__row}">
      <td><select data-tm="person_id" data-row="${a.__row}" aria-label="Person"${L.over
          ? ` class="tmover" title="${att(`Over the ${M.OVER.toFixed(2)} ceiling in ${L.over} of these months`)}"` : ""}
          >${peopleOpts(a.person_id)}</select>
        <span class="sub">${esc(a.assignment_id || "")}${manual ? ` · <span class="estb manual sm">manual</span>` : ""}</span></td>
      <td><select data-tm="role_name" data-row="${a.__row}" aria-label="Role">${roleOpts(a.role_name)}</select></td>
      <td><input type="date" data-tm="assign_start_date" data-row="${a.__row}" value="${ymdv(a.assign_start_date)}"
        aria-label="From" title="Empty = from the project's start"></td>
      <td><input type="date" data-tm="assign_end_date" data-row="${a.__row}" value="${ymdv(a.assign_end_date)}"
        aria-label="To" title="Empty = to the project's end"></td>
      <td><input type="number" step="0.05" min="0" data-tm="person_weight" data-row="${a.__row}"
        value="${a.person_weight ?? ""}" aria-label="Person weight"></td>
      <td class="num">${fmt(share)}</td>
      <td><button class="btn tiny danger" data-tmdel="${a.__row}">Remove</button></td></tr>`;
  }).join("");

  const members = new Set(rows.map(a => a.person_id));
  const room = people.filter(s => !members.has(s)).sort((a, b) => load[a].avg - load[b].avg).slice(0, 6);
  el("teamBody").innerHTML = `
    <p class="cap">Who is on <strong>${esc(pr.project_name)}</strong> (${esc(pr.project_type || "")}
      · ${span}). Change a person, a role, a window or a weight here and it is the same edit as
      typing it on <strong>Source data (person)</strong> — it shows on every tab at once and is kept
      when you press <strong>Save changes</strong>, or undone by <strong>Leave without change</strong>.
      Each person's load is over ${esc(inView)}, the part of this project inside the horizon, so you
      can see who has room — it is written beside every name, and a name in red is over the
      ceiling in some of them. Empty dates mean the whole project.</p>
    <p class="tmmsg" id="teamMsg" role="status" hidden></p>
    <table class="data-t tmt"><thead><tr><th>Person</th><th>Role</th><th>From</th><th>To</th>
      <th>Weight</th><th>On this project<br><span class="sub">avg FTE in view</span></th>
      <th></th></tr></thead>
      <tbody>${body || `<tr><td colspan="7" class="muted">Nobody is on this project yet — add somebody below.</td></tr>`}</tbody></table>
    <div class="tmadd">
      <h3>Add somebody</h3>
      <div class="tmform">
        <label class="ctl"><span>Person</span><select id="tmP"><option value="">— choose —</option>${peopleOpts("")}</select></label>
        <label class="ctl"><span>Role</span><select id="tmR">${roleOpts("")}</select></label>
        <label class="ctl"><span>From</span><input type="date" id="tmF" title="Empty = the project's start"></label>
        <label class="ctl"><span>To</span><input type="date" id="tmT" title="Empty = the project's end"></label>
        <label class="ctl"><span>Weight</span><input type="number" id="tmW" step="0.05" min="0" value="1"></label>
        <button class="btn primary" data-tmadd="1">Add to team</button>
      </div>
      ${room.length ? `<p class="tmroom"><span>Most room in these months:</span>${room.map(s =>
        `<button class="chip" data-tmpick="${att(s)}" title="${att(loadText(load[s]))}">`
        + `${esc(M.people[s].person_name || s)} <i>${fmt(load[s].avg)}</i></button>`).join("")}</p>` : ""}
    </div>`;
}

/** One field of one assignment, changed - the edit path of applyEdit(), without a cell. */
function teamField(f){
  const r = (S.model.raw.Assignment || []).find(x => x.__row === +f.dataset.row);
  if (!r) return;
  const col = f.dataset.tm;
  let v = f.value === "" ? null : f.value;
  if (v !== null && (col === "assign_start_date" || col === "assign_end_date")){
    v = parseDate(v);
    if (v === undefined){ drawTeam(); return teamSay("bad", "That is not a date."); }
  }
  if (v !== null && col === "person_weight"){
    v = num(v);
    if (v === undefined || v < 0){ drawTeam(); return teamSay("bad", "The weight is a number, 0 or more."); }
  }
  teamSet(r, col, v);
}

function teamSet(r, col, v){
  const before = r[col];
  const same = (before instanceof Date && v instanceof Date) ? +before === +v : before === v;
  if (same) return true;
  beginEditSession();
  r[col] = v;
  // The same guard as a typed cell: an edit that introduces an ERROR is refused outright.
  const probe = rebuild();
  const newErr = probe.findings.filter(blocking), oldErr = (S.model.findings || []).filter(blocking);
  if (newErr.length > oldErr.length){
    r[col] = before;
    rebuild(true);
    drawTeam();
    return teamSay("bad", "Not changed: " + newErr[newErr.length - 1].msg);
  }
  S.pending.push({at: new Date(), sheet: "Assignment", row: r.__row, col, from: before, to: v});
  S.editedCells.add(`Assignment|${r.__row}|${col}`);
  rebuild(true);
  renderKeepingTab();               // redraws this dialog too, through teamRefresh()
  const who = id => (S.model.people[id] || {}).person_name || id;
  teamSay("ok", col === "person_id"
    ? `${who(before)} is replaced by ${who(v)} on ${r.assignment_id}. Press Save changes to keep it.`
    : `${r.assignment_id}: ${col.replace(/_/g, " ")} changed. Press Save changes to keep it.`);
  return true;
}

function teamAdd(){
  const M = S.model, pid = TEAM;
  const person = el("tmP").value, role = el("tmR").value;
  if (!person) return teamSay("bad", "Choose who to add.");
  if (!role) return teamSay("bad", "Choose their role.");
  const from = el("tmF").value ? parseDate(el("tmF").value) : null;
  const to = el("tmT").value ? parseDate(el("tmT").value) : null;
  if (from === undefined || to === undefined) return teamSay("bad", "A date is not a date.");
  const w = el("tmW").value === "" ? 1 : num(el("tmW").value);
  if (w === undefined || w < 0) return teamSay("bad", "The weight is a number, 0 or more.");
  beginEditSession();
  const id = nextKey("Assignment", "assignment_id");
  const want = {assignment_id: id, person_id: person, project_id: pid, role_name: role,
                assign_start_date: from, assign_end_date: to, person_weight: w};
  const r = newRow("Assignment", {});
  delete r.__new;                   // complete, not a draft waiting for the rest of it
  Object.assign(r, want);
  const probe = rebuild();
  const newErr = probe.findings.filter(blocking), oldErr = (M.findings || []).filter(blocking);
  if (newErr.length > oldErr.length){
    M.raw.Assignment.splice(M.raw.Assignment.indexOf(r), 1);
    rebuild(true);
    return teamSay("bad", "Not added: " + newErr[newErr.length - 1].msg);
  }
  S.pending.push({at: new Date(), sheet: "Assignment", row: r.__row, col: "(new row)",
                  from: null, to: `${id} ${person} ${role}`});
  for (const [c, v] of Object.entries(want)){
    if (v === null) continue;
    S.pending.push({at: new Date(), sheet: "Assignment", row: r.__row, col: c, from: null, to: v});
    S.editedCells.add(`Assignment|${r.__row}|${c}`);
  }
  rebuild(true);
  renderKeepingTab();
  teamSay("ok", `${(M.people[person] || {}).person_name || person} is on the team as ${role} `
    + `(${id}). Press Save changes to keep it.`);
}

function teamRemove(rowNum){
  const M = S.model;
  const r = (M.raw.Assignment || []).find(x => x.__row === rowNum);
  if (!r) return;
  /* An assignment with weight windows or stated months is not deleted from here: those
     rows would be left pointing at nothing, and a delete is never cascaded (deleteRow
     says the same). Said IN the dialog - the page banner is behind it. */
  const held = REFS.assignment_id.map(([s, c]) => [s, (M.raw[s] || []).filter(x => x[c] === r.assignment_id).length])
    .filter(([, n]) => n);
  if (held.length)
    return teamSay("bad", `${r.assignment_id} cannot be removed here: ${held.map(([s, n]) => `${n} row(s) in ${s}`)
      .join(" and ")} belong to it. Remove those first on Source data (person), or set its To date `
      + `to end it instead.`);
  const who = (M.people[r.person_id] || {}).person_name || r.person_id;
  deleteRow("Assignment", rowNum);
  teamSay("ok", `${who} is off the team (${r.assignment_id}). Press Save changes to keep it.`);
}
