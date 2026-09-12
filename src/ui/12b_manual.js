/* ==================================== 12b. manual monthly estimation (REQ-CAL-18)

   The assumptions are a good default and a poor last word. A trial two years in has a
   manager who knows what the next eight months actually take, and a standard monthly FTE
   shared out by standard role factors is a worse answer than the one in their head. So a project, or one person's assignment to a project, can be switched to
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
 *  switching. `auto` is what the ASSUMPTIONS ALONE said - the demand shared out, kept on
 *  every line as it was worked out - and it is what the panel shows beside a stated figure
 *  so the difference between the two is readable rather than implied. */
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

/** WHERE A MONTH'S AUTOMATIC FIGURE CAME FROM - the whole expression, term by term.
 *
 *  automatic_fte answers "what would the assumptions have said" and stops there, and a
 *  reader who disagrees with it has no way to find out which of six inputs they actually
 *  disagree with. Naming only the period answered one of the six. So the column now
 *  carries the arithmetic itself, with every term and its value:
 *
 *    project:  Before-Start-up (standard 1.02) × period weight (0.84)
 *                                              × month run (1.00) = 0.86
 *    person:   ...the same first line, then
 *              role factor (0.68) ÷ sharers (1) × person weight (0.31, no override)
 *                                 × month coverage (1.00) = 21.1% of it, 0.18
 *
 *  TWO HALVES ON THE PERSON'S, AND THE SPLIT IS NOT COSMETIC. Since R-32 a person's
 *  figure is NOT the product of those terms: the project's month is the demand, and the
 *  terms make a CLAIM which is normalised against everybody else's on that project-month
 *  to give a SHARE (REQ-CAL-19). Writing them as one product would read as an arithmetic
 *  the application does not do, and would be wrong by whatever the other claims came to.
 *  So the demand is closed off with its own '=', and the person's terms are shown ending
 *  in the PERCENTAGE of it they won.
 *
 *  Read off the LINES, which is where the figure itself came from, so no term named here
 *  can be a different one from the term the arithmetic used. One line per
 *  assignment-month, so the first is the only one; for a project-month the first line
 *  carries the standard, weight, month run and demand, which shareOut() writes onto every
 *  line of the group alike. */
function monthFacts(scope, id){
  const facts = new Map();
  for (const L of ((S.calc && S.calc.lines) || [])){
    if (scope === "project" ? L.project_id !== id : L.assignment_id !== id) continue;
    const k = isoMonth(L.month);
    if (!facts.has(k)) facts.set(k, L);
  }
  return facts;
}

const f2 = v => (num(v) ?? 0).toFixed(2);

/** The period a month falls in when NO line carries it.
 *
 *  It happens for one reason worth naming: a manual project month in which nobody is
 *  assigned (V-32) has a stated figure and no line at all. The period is still a fact of
 *  the project's own plan, so it is answered from the same function the calculation uses
 *  rather than left blank - a blank there reads as "no period", which is a different and
 *  much more alarming thing. */
function periodOfMonth(pid, mm){
  const [y, m] = String(mm || "").split("-").map(Number);
  if (!pid || !y || !m || !S.calc || !S.calc.periodAt) return null;
  const seg = S.calc.periodAt(pid, y, m - 1);
  return seg ? {name:seg.period_name, weight:num(seg.weight) ?? 1} : null;
}

/* Each term names what it IS as well as what it was worth, and says when the value is a
   fallback rather than something the workbook supplied. A bare '1.00' where a row is
   missing is indistinguishable from a genuine 1.00, which is the whole reason V-19 and
   V-23 exist - so the fallbacks say so and name their rule. */
function standardTerm(proj, periodName){
  const v = (proj && periodName) ? num(stdWeight(S.model, proj, periodName)) : null;
  return (v === null || v === undefined)
    ? "standard 1.00 by default — no row for this period, V-19"
    : `standard ${v.toFixed(2)}`;
}

/** The role factor, and the cover it is carrying if any (REQ-CAL-16). */
function roleTerm(L){
  const eff = num(L.role_factor_effective) ?? 1;
  const own = num(L.role_factor);
  if (own === null || own === undefined)
    return `role factor (${eff.toFixed(2)} by default — no row for this role, V-23)`;
  const extra = eff - own;
  return (extra > 0.0049 && (L.absorbed || []).length)
    ? `role factor (${own.toFixed(2)} + ${extra.toFixed(2)} absorbed from `
      + `${L.absorbed.join(", ")} = ${eff.toFixed(2)})`
    : `role factor (${own.toFixed(2)})`;
}

/** The person's weight, and the override if a window covered this month.
 *
 *  An override REPLACES person_weight for the months it covers - it does not multiply it
 *  (REQ-PSN-05). So the two are never shown as two factors of one product, however
 *  natural that reads: they are one term with two possible sources, and the cell says
 *  which source it took and what the other one said. */
function weightTerm(L){
  const eff = num(L.person_weight) ?? 0;
  if (L.person_weight_source !== "PersonPeriodWeight override")
    return `person weight (${eff.toFixed(2)}, no override)`;
  const a = (S.model.raw.Assignment || []).find(x => x.assignment_id === L.assignment_id);
  const own = a ? num(a.person_weight) : null;
  return `weight override (${eff.toFixed(2)}`
    + (own === null || own === undefined ? "" : `, replacing person weight ${own.toFixed(2)}`)
    + ")";
}

/** The whole derivation of one month, as one cell. */
function periodCell(scope, facts, proj, mm){
  const L = facts.get(mm);
  const pid = proj ? proj.project_id : null;
  if (!L){
    const p = periodOfMonth(pid, mm);
    if (!p || !p.name)
      return "no period covers this month — weighted ×1.00 by default (V-12)";
    return `${p.name} (${standardTerm(proj, p.name)}) × period weight (${f2(p.weight)})`
      + " — nobody is assigned this month, so there is nothing to share it out to (V-32)";
  }
  const head = L.period_name
    ? `${L.period_name} (${standardTerm(proj, L.period_name)})`
    : `no period, V-12 (standard ${f2(L.standard_fte)} by default)`;
  const demand = `${head} × period weight (${f2(L.period_weight)})`
    + ` × month run (${f2(L.month_run)}) = ${f2(L.demand_fte)}`;
  if (scope === "project") return demand;
  return `${demand} — the project's month\n`
    + `this person's claim: ${roleTerm(L)} ÷ sharers (${L.sharers}) `
    + `× ${weightTerm(L)} × coverage (${f2(L.coverage)}) `
    + `= ${(100 * (num(L.role_share) ?? 0)).toFixed(1)}% of it → ${f2(L.auto)}`;
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
         across as they stand now, to two decimal places
         (${total.toFixed(2)} FTE-months in total), and from then on those figures are
         used <em>instead of</em> the calculation. The copy is what stops the figures
         jumping: nothing moves by more than the rounding, which at
         ${S.model.HOURS} hours to the FTE is under an hour a month.</p>
       <p class="note"><strong>All of them become yours, not just the ones you edit.</strong>
         Changing a period weight, a role factor or a person's weight will no longer move
         any of these ${now.size} months. That is the point of switching, and it is also
         the thing to remember: from here on, keeping them right is your job.
         ${scope === "project"
           ? "A project figure is the whole month, and the people assigned that month are "
             + "scaled so they still add up to it."
           : "An assignment figure is this person's own contribution to this project, and "
             + "it replaces the share they would otherwise have been given."}</p>`
    : `<p class="cap">${name}</p>
       <p><strong>All ${have.length} stated month${have.length === 1 ? "" : "s"} will be
         deleted</strong> and the figures go back to being worked out from the assumptions
         — ${scope === "project"
              ? "standard FTE × period weight × the part of the month the project runs"
              : "the project's month, standard FTE × period weight, shared out by "
                + "(role factor ÷ sharers) × person weight × month coverage"}.</p>
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
function askEstimation(title, bodyHtml, yesLabel, go, onNo, noLabel){
  const dlg = el("estchg");
  el("estTitle").textContent = title;
  el("estYes").textContent = yesLabel;
  el("estNo").textContent = noLabel || "Go back";
  el("estBody").innerHTML = bodyHtml;
  let done = false;
  // `onNo` runs on the No button, on Escape and on the backdrop alike: a soft stop whose
  // "put it back" only worked from one of the three ways out would leave the edit
  // standing exactly when the user thought they had backed out of it.
  const finish = ok => { if (done) return; done = true; dlg.close();
                         if (ok) go(); else if (onNo) onNo(); };
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
                                           fte:round2(seed.get(mm)), edited_at:at});
      delete r.__new;                 // seeded complete, not a draft waiting to be typed
      S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${id} ${mm}`,
                      from:null, to:round2(seed.get(mm))});
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
                                         fte:round2(now.get(mm)), edited_at:at});
    delete r.__new;
    S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${id} ${mm}`,
                    from:null, to:round2(now.get(mm))});
  }
  rebuild(true);
  renderKeepingTab();
  showBanner("", `${add.length} month(s) were filled in for ${id} from the calculation `
    + `(${add[0]}${add.length > 1 ? ` … ${add[add.length - 1]}` : ""}). Edit any of them.`);
}

/* Two places, and the unit is the reason. A stated figure is a figure somebody has
   decided on, and it lands in a cell they then read and edit - 0.8814374999 is not a
   number anybody states. Two places is also the finest edit that means anything in the
   unit people actually think in: at 160 hours to the FTE, 0.01 is 1.6 hours, and there
   is no useful answer to what 0.0001 FTE would be. The cost is that a month can move by
   up to half a unit in the last place when it is copied across - 0.005 FTE, about 48
   minutes - which is the trade being made deliberately, not an oversight. Nothing stops
   a typed figure carrying more places; this is only what the SEED is written to. */
const round2 = v => Math.round((v ?? 0) * 100) / 100;

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
  const facts = monthFacts(scope, id);
  const ownPid = scope === "project" ? id
    : (((S.model.raw.Assignment || []).find(a => a.assignment_id === id) || {}).project_id
       || null);
  // The project RECORD, not just its identifier: standardTerm re-asks PeriodFTEStandard
  // to tell a genuine 1.00 from the 1.00 a missing row falls back to, and that lookup is
  // keyed on the project's type, phase and work scope.
  const ownProj = ownPid ? (S.model.projects[ownPid] || null) : null;
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
                                 : `${now.size} calculated month(s)`}</span></div>
    ${/* WHICH assignment this is, under the title. The heading names the assignment_id
         and nothing else, and ASG-203 is not a fact anybody carries around - the
         project, the role, the window and the weight are what make one of a person's
         five assignments recognisable. Drawn by the same function the Weight overrides
         panel uses, because the two now sit one under the other and two versions of
         this line that had drifted would be visible on one screen. */
      scope === "assignment" ? assignmentLine(id) : ""}`;

  if (!on)
    return `<div class="panel">${head}
      <p class="cap">This ${what}'s months are <strong>calculated</strong>:
        ${scope === "project"
          ? "<strong>standard FTE × period weight × the part of the month this project "
            + "runs</strong>, month by month. The standard is what a project of this type, "
            + "phase and work scope takes in this period; the period weight is this "
            + "project's own adjustment to it. Who is assigned decides how the month is "
            + "<em>divided</em>, not how large it is."
          : "the project's month — <strong>standard FTE × period weight</strong> — divided "
            + "among the people on it, and this is this person's share of it. The share is "
            + "<strong>(role factor ÷ sharers) × person weight × month coverage</strong> "
            + "measured against everyone else's, so the shares always add to one."}
        ${totalAuto.toFixed(2)} FTE-months across ${now.size} month(s). Change an
        assumption and every one of them follows.</p>
      <p class="note">Switch to <strong>manual</strong> if you have better information
        than the assumptions do — a ${what} part way through, where what it has actually
        taken is known. Switching copies these ${now.size} figures across as they stand,
        rounded to two places — 0.01 FTE is ${(S.model.HOURS / 100).toFixed(1)} hours, and
        there is no useful edit finer than that — so nothing jumps, and you then edit the
        ones you know better. The application asks before it does either.</p>
      ${manualElsewhere(scope, id)}</div>`;

  /* THE MONTHS THIS PANEL STATES THAT ITS PROJECT OVERRODE (V-33).
     Said HERE as well as in the findings report, because this is the table the figures
     were typed into and the only place the two numbers can be put side by side. The
     report is where it is recorded; this is where it is noticed. */
  const clashes = scope === "assignment"
    ? ((S.calc && S.calc.lines) || []).filter(L =>
        L.assignment_id === id && L.overridden_by_project)
    : [];
  const clashNote = clashes.length
    ? `<div class="estclash"><strong>${clashes.length} of these month(s) are not the
         figure this person is given.</strong> ${esc((S.model.projects[
           (clashes[0] || {}).project_id] || {}).project_name || "The project")} has a
         MANUAL figure for those months, and a project's month is the whole month — the
         people on it are scaled so they still add up to it, so the project's figure
         wins.
       <table class="data-t" style="margin-top:6px"><thead><tr><th>month</th>
         <th>stated here</th><th>actually given</th><th>the project's month</th></tr>
         </thead><tbody>${clashes.slice(0, 8).map(L =>
           `<tr><td>${esc(monthLabel(isoMonth(L.month)))}</td>`
           + `<td class="num">${L.stated_assignment_fte.toFixed(2)}</td>`
           + `<td class="num"><strong>${L.fte.toFixed(2)}</strong></td>`
           + `<td class="num">${(L.manual_project_total ?? 0).toFixed(2)}</td></tr>`)
           .join("")}</tbody></table>
       ${clashes.length > 8 ? `<p class="note">and ${clashes.length - 8} more.</p>` : ""}
       <p class="note">To make these figures the ones that are used, change the
         project's month to one that leaves room for them, or switch this assignment
         back to automatic and let it take its share. <strong>V-33</strong> reports it
         in the findings and in the change log either way.</p></div>`
    : "";

  return `<div class="panel">${head}
    ${clashNote}
    <p class="cap">These figures are <strong>stated, not calculated</strong>.
      ${scope === "project"
        ? "Each one is the whole project for that month, and the people assigned that "
          + "month are scaled so they still add up to it."
        : "Each one is this person's own contribution to this project for that month, "
          + "and it replaces the share they would otherwise have been given."}
      <code>automatic_fte</code> beside it is what the assumptions alone would have said,
      so the departure is readable: <strong>${totalNow.toFixed(2)}</strong> stated against
      <strong>${totalAuto.toFixed(2)}</strong> calculated across ${now.size} month(s).
      <code>period</code> carries the <strong>whole derivation of that month, term by
      term</strong> — the period it falls in, the standard that period selects, this
      project's weight and how much of the month it ran${scope === "project" ? "" :
        ", then this person's claim on it: role factor ÷ sharers × person weight × month "
        + "coverage, ending in the percentage of the project's month it won. Those terms "
        + "make a CLAIM, not a figure: the shares are measured against each other, so the "
        + "product is a proportion of the month rather than the month itself. "
        + "<code>sharers</code> repeats the divisor on its own, where it can be sorted "
        + "and filtered"}. Looked up, not stored.</p>
    ${missing.length ? `<p class="note bad">${missing.length} month(s) this ${what} covers
      have <strong>no stated figure</strong> (${esc(missing.slice(0, 6).join(", "))}${
      missing.length > 6 ? ", …" : ""}) and are counted as <strong>0.00</strong> — V-31.
      Either fill them in with the button above, or switch back to automatic.</p>` : ""}
    ${stray.length ? `<p class="note">${stray.length} stated month(s) fall outside the
      months this ${what} covers (${esc(stray.map(r => r.month).slice(0, 6).join(", "))}${
      stray.length > 6 ? ", …" : ""}). They are kept but not used${
      scope === "project" ? " — a project month with nobody assigned has nobody to share "
        + "it out to, which V-32 reports" : ""}.</p>` : ""}
    ${filterTable("MonthlyEstimate", rows,
      scope === "project"
        ? ["month", "fte", "automatic_fte", "difference", "period", "edited_at", "note_1"]
        : ["month", "fte", "automatic_fte", "difference", "period", "sharers",
           "edited_at", "note_1"],
      null, null,
      // Two places, like every other figure (REQ-CAL-20). These were the last four-place
      // numbers on screen, and the difference between a stated 2.41 and an "automatic"
      // 2.4120 read as a discrepancy the user had caused rather than as four decimals
      // nothing else in the application uses.
      {automatic_fte: r => auto.has(r.month) ? auto.get(r.month).toFixed(2) : "",
       difference: r => {
         if (!auto.has(r.month) || r.fte === null || r.fte === undefined) return "";
         const dd = Number(r.fte) - auto.get(r.month);
         return (dd >= 0 ? "+" : "") + dd.toFixed(2);
       },
       period: r => r.month ? periodCell(scope, facts, ownProj, r.month) : "",
       // Only on the assignment panel. A project's month is divided between SEVERAL
       // roles, each with its own count, so one number against the project's month
       // would be an average of things that are not comparable - and the divisor is a
       // fact about one person's share, which is what this panel is.
       sharers: r => {
         const f = facts.get(r.month);
         if (!f || !f.sharers) return "";
         return `${f.sharers}` + (f.sharers === 1 ? " (only holder)" : " share this role");
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
