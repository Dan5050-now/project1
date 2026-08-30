/* ==================================== 12b. manual monthly estimation (REQ-CAL-18)

   The assumptions are a good default and a poor last word. A trial two years in has a
   manager who knows what the next eight months actually take, and a standard period
   weight multiplied by a standard role factor is a worse answer than the one in their
   head. So a project, or one person's assignment to a project, can be switched to
   MANUAL: its monthly figures are then stated rather than worked out.

   Three decisions are worth stating here, because the panel below only makes sense once
   they are:

   ALL OR NOTHING. Switching to manual copies EVERY month across first, from the figures
   currently on screen, and the user then edits the ones they know better. Nothing has to
   remember which months were touched and no month carries a flag of its own. That was a
   deliberate choice over per-month marking: once a figure has been edited, "which months
   are still automatic" is a question with no useful answer - the automatic ones are only
   automatic until the assumptions beneath them change, at which point they would move
   under a plan somebody has already signed off. What the user takes on in exchange is
   responsibility for all of them, and the confirmation says so in those words.

   ONE WAY IN. estimation_type is not typed into the table like every other column - the
   cell refuses the edit and points here. Typing 'manual' into a cell would set the flag
   without copying anything across, so every month would read as missing and the project
   would drop to zero. The button is the only route because it is the only route that
   leaves the data in a state that means anything.

   IT IS AN EDIT LIKE ANY OTHER. The switch, the seeding and the discard all go through
   beginEditSession / S.pending, so they appear in the change log, they are undone by
   'Leave without change', and they reach the file only when the user presses Save. */

const isoMonth = k => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
const monthLabel = mm => {
  const [y, m] = String(mm || "").split("-");
  return m ? keyToLabel((+y) * 12 + (+m) - 1) : String(mm || "");
};
const estType = row =>
  String((row || {}).estimation_type || "").trim().toLowerCase() === "manual"
    ? "manual" : "automatic";

const EST_SHEET = {project:"Project", assignment:"Assignment"};
const estRow = (scope, id) =>
  ((S.model.raw[EST_SHEET[scope]] || []).find(r => r[KEY_COL[EST_SHEET[scope]]] === id)) || null;

/** The MonthlyEstimate rows belonging to one thing, oldest month first.
 *  Rows still being typed are included even before scope and ref_id are on them, so a
 *  row added by hand is visible in the panel that created it. */
function estRows(scope, id){
  return (S.model.raw.MonthlyEstimate || [])
    .filter(r => (r.scope === scope && r.ref_id === id)
              || (r.__new && !r.scope && !r.ref_id))
    .sort((a, b) => String(a.month || "").localeCompare(String(b.month || "")));
}

/** What this thing draws each month, and what the assumptions alone would have said.
 *
 *  `now` is the figure ON SCREEN - after any manual figure already in force - and it is
 *  what a switch to manual seeds from, so the figures do not jump at the moment of
 *  switching. `auto` is the untouched multiplication, kept on every line as it was worked
 *  out, and it is what the panel shows beside a stated figure so the difference between
 *  the two is readable rather than implied. */
function monthlyOf(scope, id){
  const now = new Map(), auto = new Map();
  for (const L of ((S.calc && S.calc.lines) || [])){
    if (scope === "project" ? L.project_id !== id : L.assignment_id !== id) continue;
    const k = isoMonth(L.month);
    now.set(k, (now.get(k) || 0) + L.fte);
    auto.set(k, (auto.get(k) || 0) + (L.auto ?? 0));
  }
  return {now, auto};
}

/* ------------------------------------------------------------------ the switch */

/** Ask, then do. Every change of calculation way goes through this - there is no path
 *  that changes one silently, which is the whole of the user's last requirement. */
function switchEstimation(scope, id){
  const row = estRow(scope, id);
  if (!row){
    showBanner("bad", `${id} is not saved yet, so its estimation type cannot be changed. `
      + `Fill the row in and press Save first.`);
    return;
  }
  const to = estType(row) === "manual" ? "automatic" : "manual";
  const {now, auto} = monthlyOf(scope, id);
  const have = estRows(scope, id).filter(r => r.scope === scope);
  const what = scope === "project" ? "Project" : "Assignment";
  const name = scope === "project"
    ? `${what} ${id} — ${esc((S.model.projects[id] || {}).project_name || "")}`
    : `${what} ${id} — ${esc(assignmentLabel(id))}`;
  const total = [...now.values()].reduce((a, b) => a + b, 0);

  const body = to === "manual"
    ? `<p class="cap">${name}</p>
       <p><strong>${now.size} month${now.size === 1 ? "" : "s"}</strong> will be copied
         across exactly as they stand now (${total.toFixed(2)} FTE-months in total), and
         from then on those figures are used <em>instead of</em> the calculation. Nothing
         moves at the moment you switch — the copy is what stops the figures jumping.</p>
       <p class="note"><strong>All of them become yours, not just the ones you edit.</strong>
         Changing a period weight, a role factor or a person's weight will no longer move
         any of these ${now.size} months. That is the point of switching, and it is also
         the thing to remember: from here on, keeping them right is your job.
         ${scope === "project"
           ? "A project figure is the whole month, and the people assigned that month are "
             + "scaled so they still add up to it."
           : "An assignment figure is this person's own contribution to this project, and "
             + "it replaces the multiplication outright."}</p>`
    : `<p class="cap">${name}</p>
       <p><strong>All ${have.length} stated month${have.length === 1 ? "" : "s"} will be
         deleted</strong> and the figures go back to being worked out from the assumptions
         — period weight × (role factor ÷ sharers) × person weight × month coverage.</p>
       <p class="note">There is nothing to come back to afterwards: the stated figures are
         removed, not set aside. This is still provisional like any other change, so
         <strong>Leave without change</strong> puts them back until you press Save — after
         Save they are gone.</p>`;

  askEstimation(to === "manual" ? "Switch to manual estimation?"
                                : "Switch back to automatic calculation?",
    body,
    to === "manual" ? "Switch to manual" : "Discard and recalculate",
    () => applyEstimationSwitch(scope, id, row, to, now));
}

/** The dialog. Its own, rather than the conditional-save one: those two questions are
 *  asked at different moments about different things, and a shared dialog whose heading
 *  changes underneath you is how a confirmation stops being read. */
function askEstimation(title, bodyHtml, yesLabel, go){
  const dlg = el("estchg");
  el("estTitle").textContent = title;
  el("estYes").textContent = yesLabel;
  el("estBody").innerHTML = bodyHtml;
  let done = false;
  const finish = ok => { if (done) return; done = true; dlg.close(); if (ok) go(); };
  el("estYes").onclick = () => finish(true);
  el("estNo").onclick = () => finish(false);
  dlg.onclose = () => finish(false);                  // Escape, and the backdrop
  dlg.showModal();
}

function applyEstimationSwitch(scope, id, row, to, seed){
  const M = S.model;
  beginEditSession();
  const from = estType(row);
  const at = new Date();
  S.pending.push({at, sheet:EST_SHEET[scope], row:row.__row, col:"estimation_type",
                  from, to});
  row.estimation_type = to;

  if (to === "manual"){
    const have = new Set(estRows(scope, id).filter(r => r.scope === scope).map(r => r.month));
    for (const mm of [...seed.keys()].sort()){
      if (have.has(mm)) continue;
      const r = newRow("MonthlyEstimate", {scope, ref_id:id, month:mm,
                                           fte:round4(seed.get(mm)), edited_at:at});
      delete r.__new;                 // seeded complete, not a draft waiting to be typed
      S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${id} ${mm}`,
                      from:null, to:round4(seed.get(mm))});
    }
  } else {
    const rows = M.raw.MonthlyEstimate;
    for (let i = rows.length - 1; i >= 0; i--){
      const r = rows[i];
      if (r.scope !== scope || r.ref_id !== id) continue;
      S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row,
                      col:`${id} ${r.month}`, from:r.fte, to:null});
      for (const k of [...S.editedCells])
        if (k.startsWith(`MonthlyEstimate|${r.__row}|`)) S.editedCells.delete(k);
      rows.splice(i, 1);
    }
  }
  rebuild(true);
  renderKeepingTab();
  showBanner("", to === "manual"
    ? `${id} is now estimated MANUALLY. ${seed.size} month(s) were copied from the `
      + `calculation as they stood; edit the ones you know better. This is provisional — `
      + `press Save to keep it.`
    : `${id} is back to AUTOMATIC calculation and its stated months were discarded. `
      + `This is provisional — 'Leave without change' puts them back until you Save.`);
}

/** Months the thing now spans that carry no stated figure — the case V-31 reports.
 *  It happens legitimately: extend a project's dates and the new months have never been
 *  stated. Filling them from the calculation is what the user would otherwise do by
 *  hand, so the button does it. */
function fillEstimates(scope, id){
  const {now} = monthlyOf(scope, id);
  const have = new Set(estRows(scope, id).filter(r => r.scope === scope).map(r => r.month));
  const add = [...now.keys()].sort().filter(mm => !have.has(mm));
  if (!add.length){
    showBanner("", `Every month ${id} covers already has a stated figure. Nothing added.`);
    return;
  }
  beginEditSession();
  const at = new Date();
  for (const mm of add){
    const r = newRow("MonthlyEstimate", {scope, ref_id:id, month:mm,
                                         fte:round4(now.get(mm)), edited_at:at});
    delete r.__new;
    S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${id} ${mm}`,
                    from:null, to:round4(now.get(mm))});
  }
  rebuild(true);
  renderKeepingTab();
  showBanner("", `${add.length} month(s) were filled in for ${id} from the calculation `
    + `(${add[0]}${add.length > 1 ? ` … ${add[add.length - 1]}` : ""}). Edit any of them.`);
}

const round4 = v => Math.round((v ?? 0) * 10000) / 10000;

/** How an assignment reads when it has to be named rather than selected. */
function assignmentLabel(aid){
  const a = (S.model.raw.Assignment || []).find(x => x.assignment_id === aid);
  if (!a) return aid;
  const who = (S.model.people[a.person_id] || {}).person_name || a.person_id || "—";
  const what = projectNameOf(a.project_id) || a.project_id || "—";
  return `${who} / ${what} / ${a.role_name || "—"}`;
}

/* ------------------------------------------------------------------- the panel */

/** The Monthly estimation panel, drawn the same way for both levels.
 *
 *  The table is the ordinary editable one, over the MonthlyEstimate sheet, so a stated
 *  figure is edited, validated, logged and undone exactly like every other cell in the
 *  application. What is added to it is the comparison: beside each stated figure, what
 *  the assumptions alone would have produced, and the difference. A manual plan whose
 *  panel did not show what it departed from would be a set of numbers with no argument
 *  attached to them. */
function manualPanel(scope, id){
  const row = estRow(scope, id);
  if (!row) return "";
  const on = estType(row) === "manual";
  const {now, auto} = monthlyOf(scope, id);
  const rows = estRows(scope, id);
  const mine = rows.filter(r => r.scope === scope);
  const missing = [...now.keys()].filter(mm => !mine.some(r => r.month === mm));
  const stray = mine.filter(r => r.month && !now.has(r.month));
  const what = scope === "project" ? "project" : "assignment";
  const totalNow = [...now.values()].reduce((a, b) => a + b, 0);
  const totalAuto = [...auto.values()].reduce((a, b) => a + b, 0);

  const head = `<div class="phead"><h2>Monthly estimation — ${esc(id)}</h2>
      <span class="est ${on ? "man" : "aut"}">${on ? "MANUAL" : "AUTOMATIC"}</span>
      <button class="btn tiny ${on ? "" : "primary"}" data-act="estswitch"
        data-scope="${att(scope)}" data-id="${att(id)}"
        data-tip="${att(on ? HELP.estauto : HELP.estman)}"
        >${on ? "Switch to automatic" : "Switch to manual"}</button>
      ${on && missing.length
        ? `<button class="btn tiny" data-act="estfill" data-scope="${att(scope)}"
             data-id="${att(id)}" data-tip="${att(HELP.estfill)}"
             >Fill ${missing.length} missing month(s)</button>` : ""}
      <span class="scope k">${on ? `${mine.length} stated month(s)`
                                 : `${now.size} calculated month(s)`}</span></div>`;

  if (!on)
    return `<div class="panel">${head}
      <p class="cap">This ${what}'s months are <strong>calculated</strong>: period weight
        × (role factor ÷ sharers) × person weight × month coverage, month by month —
        ${totalAuto.toFixed(2)} FTE-months across ${now.size} month(s). Change an
        assumption and every one of them follows.</p>
      <p class="note">Switch to <strong>manual</strong> if you have better information
        than the assumptions do — a ${what} part way through, where what it has actually
        taken is known. Switching copies these ${now.size} figures across as they stand,
        so nothing jumps, and you then edit the ones you know better. The application
        asks before it does either.</p>
      ${manualElsewhere(scope, id)}</div>`;

  return `<div class="panel">${head}
    <p class="cap">These figures are <strong>stated, not calculated</strong>.
      ${scope === "project"
        ? "Each one is the whole project for that month, and the people assigned that "
          + "month are scaled so they still add up to it."
        : "Each one is this person's own contribution to this project for that month, "
          + "and it replaces the multiplication outright."}
      <code>automatic_fte</code> beside it is what the assumptions alone would have said,
      so the departure is readable: <strong>${totalNow.toFixed(2)}</strong> stated against
      <strong>${totalAuto.toFixed(2)}</strong> calculated across ${now.size} month(s).</p>
    ${missing.length ? `<p class="note bad">${missing.length} month(s) this ${what} covers
      have <strong>no stated figure</strong> (${esc(missing.slice(0, 6).join(", "))}${
      missing.length > 6 ? ", …" : ""}) and are counted as <strong>0.00</strong> — V-31.
      Either fill them in with the button above, or switch back to automatic.</p>` : ""}
    ${stray.length ? `<p class="note">${stray.length} stated month(s) fall outside the
      months this ${what} covers (${esc(stray.map(r => r.month).slice(0, 6).join(", "))}${
      stray.length > 6 ? ", …" : ""}). They are kept but not used${
      scope === "project" ? " — a project month with nobody assigned has nobody to share "
        + "it out to, which V-32 reports" : ""}.</p>` : ""}
    ${dataTable("MonthlyEstimate", rows,
      ["month", "fte", "automatic_fte", "difference", "edited_at", "note_1"],
      null, null,
      {automatic_fte: r => auto.has(r.month) ? auto.get(r.month).toFixed(4) : "",
       difference: r => {
         if (!auto.has(r.month) || r.fte === null || r.fte === undefined) return "";
         const dd = Number(r.fte) - auto.get(r.month);
         return (dd >= 0 ? "+" : "") + dd.toFixed(4);
       }})}
    ${manualElsewhere(scope, id)}</div>`;
}

/** Which OTHER level is manual on the same work.
 *
 *  A project total can be manual for two quite different reasons - somebody stated the
 *  project's month, or somebody stated one person's contribution to it - and the figure
 *  looks identical either way. So the project panel names the assignments that are
 *  manual, by assignment_id and by who they are, and the assignment panel says when the
 *  project above it is stated too. Without this the honest question "why is this figure
 *  what it is" has no answer on the screen that shows the figure. */
function manualElsewhere(scope, id){
  const M = S.model;
  if (scope === "project"){
    const man = (M.raw.Assignment || [])
      .filter(a => a.project_id === id && estType(a) === "manual");
    if (!man.length) return "";
    return `<p class="note"><strong>${man.length} assignment(s) on this project are
      themselves manual</strong>, so part of every month below is stated at the personal
      level rather than the project level:</p>
      <ul class="estlist">${man.map(a =>
        `<li><code>${esc(a.assignment_id)}</code> — ${esc(assignmentLabel(a.assignment_id))}
          <button class="btn tiny" data-act="gopers" data-sid="${att(a.person_id)}"
            data-aid="${att(a.assignment_id)}">Open</button></li>`).join("")}</ul>`;
  }
  const a = (M.raw.Assignment || []).find(x => x.assignment_id === id);
  if (!a || estType(M.projects[a.project_id] || {}) !== "manual") return "";
  return `<p class="note"><strong>The project this belongs to
    (<code>${esc(a.project_id)}</code>) is manual too.</strong> Its stated month is the
    whole project, so this assignment's figure is scaled along with everyone else's to add
    up to it — what you type here decides this person's SHARE of that month, not the
    month's total.
    <button class="btn tiny" data-act="goproj" data-pid="${att(a.project_id)}"
      >Open the project</button></p>`;
}
