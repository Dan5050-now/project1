/* ============================== 13c. standard vs staffed (REQ-DSH-15, V-34)

   TWO FIGURES THAT CAN COME APART, AND THE PAIR IS NOT THE OBVIOUS ONE.

   The pair people reach for first - a project's month against the sum of its people -
   cannot differ. projMonth is built FROM the lines, so it IS that sum by construction,
   and the results export rests on it (REQ-OUT-06). Checking it would be checking that
   addition works.

   The pair that does come apart is what the project NEEDS against what it is BEING
   GIVEN. An all-automatic month has them equal: shareOut hands out exactly the demand's
   hundredths and the shares add to one (REQ-CAL-19). A manual figure - at either level -
   replaces the standard rather than adjusting it, and the two part company. Set a
   project needing 10.00 to 5.00, or cut one person's stated month, and the application
   drew a smaller project and said nothing. A study needing ten people and staffed with
   five looked exactly like a study that only ever needed five.

   THIS SECTION IS WHERE THAT IS SAID, and it is deliberately not a tab. A tab is the
   surface you only visit once you already suspect a problem, which is the wrong property
   for something whose whole danger is that it is silent. So the finding reaches the
   report, the load banner and the archived log by being a rule; the figure carries a
   mark wherever it is drawn; and this panel sits on the Overall tab, under the tiles,
   where somebody looking at the plan will meet it without going to find it.

   AND IT IS NOT A LIST YOU HAVE TO ACT ON SOMEWHERE ELSE. Every row opens a dialog
   carrying the month's own figures - the demand term by term, everybody on it, and the
   stated figures behind the gap AS EDITABLE CELLS. They are ordinary contenteditable
   cells over the MonthlyEstimate sheet, so the existing editing path validates, logs,
   marks and undoes them exactly as it does in a table: there is no second way to change
   a figure, which is the only way two ways cannot drift apart.

   BOTH DIRECTIONS, COUNTED SEPARATELY. Short of the standard is a project running on
   less than its kind usually takes; over it is one deliberately staffed heavier. They
   are different facts, and summing them would let three short in March cancel three over
   in April and report a plan as fine. */

/** Every project-month whose demand and applied figure differ, largest first.
 *  `pids` scopes it to the projects in view, so the panel and the tiles above it cannot
 *  disagree about how many there are. */
function gapRows(pids){
  const C = S.calc, want = new Set(pids || []);
  const out = [];
  for (const [qk, g] of (C.projGap || new Map())){
    const i = qk.lastIndexOf("|");
    const pid = qk.slice(0, i), k = +qk.slice(i + 1);
    if (want.size && !want.has(pid)) continue;
    out.push({pid, k, ...g});
  }
  out.sort((a, b) => Math.abs(b.gap) - Math.abs(a.gap) || (a.pid < b.pid ? -1 : 1));
  return out;
}

/** The gap on one project-month, or null. Used by the charts and the tables to mark a
 *  figure where it is drawn, so a shortfall does not depend on anybody hovering. */
function gapOf(pid, k){
  return (S.calc && S.calc.projGap && S.calc.projGap.get(pid + "|" + k)) || null;
}

/** The one line the chart pop-ups carry. Short and always in the same shape, because it
 *  sits under a period line that is already two facts long. */
function gapLine(pid, k){
  const g = gapOf(pid, k);
  if (!g) return "";
  return `<span class="${g.dir === "short" ? "gshort" : "gover"}">`
    + `${g.dir === "short" ? "&#9660; Short of" : "&#9650; Over"} the standard by `
    + `<b>${Math.abs(g.gap).toFixed(2)}</b></span>`
    + `<span class="tr"> &#183; needs ${g.demand.toFixed(2)}, staffed `
    + `${g.applied.toFixed(2)} (V-34)</span><br>`;
}

/** The same thing as a short trailing phrase, for a pop-up that lists SEVERAL projects.
 *  A person's month is made of every project they are on, and those projects need not be
 *  off their standard in the same direction or at all - so the tag sits against each
 *  project, exactly as the period tag does, rather than once against the bar. */
function gapTag(pid, k){
  const g = gapOf(pid, k);
  if (!g) return "";
  return `<span class="${g.dir === "short" ? "gshort" : "gover"}"> `
    + `&#183; ${g.dir === "short" ? "&#9660;" : "&#9650;"} `
    + `${Math.abs(g.gap).toFixed(2)} ${g.dir} of standard</span>`;
}

/* ------------------------------------------------------------------- the panel */

const GAP_SHOW = 40;      // rows drawn; the rest are counted, not listed

function gapPanel(pids){
  const M = S.model, rows = gapRows(pids);
  const short = rows.filter(r => r.dir === "short");
  const over = rows.filter(r => r.dir === "over");
  const projects = new Set(rows.map(r => r.pid));
  if (!rows.length)
    return `<div class="panel" id="gappanel">
      <div class="phead"><h2>Standard vs staffed</h2>
        <span class="scope k">nothing to report</span></div>
      <p class="cap">Every project in view is drawing exactly what its own standard says
        it needs — <strong>standard FTE × period weight × the part of the month it
        runs</strong>. That is what an automatic month always does, because the people on
        it divide the month rather than each adding to it. A figure stated by hand, on a
        project or on one assignment, replaces the standard rather than adjusting it, and
        this panel is where the difference is listed when there is one.</p></div>`;

  const body = rows.slice(0, GAP_SHOW).map(r => {
    const pr = M.projects[r.pid] || {};
    return `<tr class="gaprow ${r.dir}" data-gap="${att(r.pid)}" data-gk="${r.k}"
        tabindex="0" role="button">
      <th class="rh"><span class="nm">${esc(pr.project_name || r.pid)}</span>
        <span class="sub">${esc(r.pid)}</span></th>
      <td>${keyToLabel(r.k)}</td>
      <td class="num">${r.demand.toFixed(2)}</td>
      <td class="num">${r.applied.toFixed(2)}</td>
      <td class="num ${r.dir}">${r.gap > 0 ? "&#9650; +" : "&#9660; "}${r.gap.toFixed(2)}</td>
      <td>${r.dir === "short" ? "short of the standard" : "over the standard"}</td>
      <td><button class="btn tiny" data-gap="${att(r.pid)}" data-gk="${r.k}"
        >Check and fix</button></td></tr>`;
  }).join("");

  return `<div class="panel" id="gappanel">
    <div class="phead"><h2>Standard vs staffed</h2>
      <span class="scope k">${rows.length} month(s) across ${projects.size}
        project(s)</span></div>
    <p class="cap">What each project <strong>needs</strong> — standard FTE × period
      weight × the part of the month it runs — against what it is actually
      <strong>being given</strong>. These are the two figures that can come apart. The
      project's month against the sum of its people cannot: the month is built from those
      people, so it is their sum by construction. A figure stated by hand replaces the
      standard rather than adjusting it, which is what puts these two out of step —
      <strong>deliberately</strong>, in every case, which is why this reports rather than
      refuses. <strong>Click any row</strong> to see the month and change the figures
      behind it.</p>
    <div class="gtot">
      <span class="gpill short">&#9660; ${short.length} month(s) short of the standard</span>
      <span class="gpill over">&#9650; ${over.length} month(s) over it</span>
      <span class="tr">counted apart, never netted — three short in March and three over
        in April is not a plan in balance</span></div>
    <div class="scrollx lg"><table class="grid-t gapt">
      <thead><tr><th class="rh">Project</th><th>Month</th><th>Needs</th>
        <th>Staffed</th><th>Gap</th><th>Direction</th><th></th></tr></thead>
      <tbody>${body}</tbody></table></div>
    ${rows.length > GAP_SHOW
      ? `<p class="note">Showing the ${GAP_SHOW} largest of ${rows.length}. The rest are
         in the findings report, which lists every one of them by project.</p>` : ""}
    <p class="note">V-34 reports this as a <strong>warning</strong>: it reaches the
      findings report, the load banner and the archived change log, and it never stops a
      save or asks a question. Departing from the standard is the point of a manual
      figure — somebody part way through a trial knows better than the assumptions — so
      the application says so and leaves the decision where it belongs.</p></div>`;
}

/* ------------------------------------------------------------------ the dialog */

let GAP_AT = null;         // {pid, k} while the dialog is open, so an edit can redraw it

/** Open the month, with the figures that caused the gap editable in place. */
function openGap(pid, k){
  GAP_AT = {pid, k};
  drawGap();
  const dlg = el("gapdlg");
  if (!dlg.open) dlg.showModal();
}

function closeGap(){
  GAP_AT = null;
  const dlg = el("gapdlg");
  if (dlg.open) dlg.close();
}

/** Redraw the open dialog after an edit. Called from the render path, so a figure
 *  changed in the dialog moves the numbers IN the dialog as well as behind it - a panel
 *  that kept showing the gap you had just closed would read as an edit that did nothing. */
function gapRefresh(){ if (GAP_AT && el("gapdlg").open) drawGap(); }

function drawGap(){
  const M = S.model, {pid, k} = GAP_AT;
  const pr = M.projects[pid] || {};
  const g = gapOf(pid, k);
  const mm = isoMonth(k);
  const lines = ((S.calc && S.calc.lines) || [])
    .filter(L => L.project_id === pid && L.month === k)
    .sort((a, b) => (a.role_name || "").localeCompare(b.role_name || ""));
  const applied = lines.reduce((t, L) => t + L.fte, 0);
  const demand = g ? g.demand : (lines[0] || {}).demand_fte ?? 0;

  el("gapTitle").innerHTML = `${esc(pr.project_name || pid)} `
    + `<span class="tr">${esc(pid)} &#183; ${keyToLabel(k)}</span>`;

  /* THE FIGURES THAT CAN ACTUALLY BE CHANGED, and nothing else offered as if it could.
     A gap has exactly two possible authors: the project's own stated month, or a stated
     month on one of its assignments. Whichever is present is what appears here as an
     editable cell; where the project is automatic there is no project row to edit and
     saying so beats showing a disabled box. */
  const projRow = (M.raw.MonthlyEstimate || []).find(r =>
    r.scope === "project" && r.ref_id === pid && String(r.month) === mm);
  const manualAsg = new Map();
  for (const r of (M.raw.MonthlyEstimate || []))
    if (r.scope === "assignment" && String(r.month) === mm) manualAsg.set(r.ref_id, r);

  /* EDITABLE IN ALL THREE STATES, and the three are genuinely different.
     A row that EXISTS is an ordinary cell over MonthlyEstimate: data-sheet, data-row,
     data-col, and the application's one editing path does the rest.
     A row that does NOT exist cannot be one - there is no __row to write through - so
     the cell carries what it needs to CREATE it instead, and its own handler. Leaving it
     as a dash was the defect: the figure a reader most wants to change on this screen is
     the one on an automatic person, and the dash said the screen was read-only for them.
     WHAT IT CANNOT DO IS QUIETLY WRITE ONE ROW. An assignment that is automatic ignores
     MonthlyEstimate entirely, so a lone row would be a figure that did nothing; and
     setting estimation_type without seeding the other months would count every one of
     them as 0.00 (REQ-CAL-18) - the one change in this application that silently zeroes
     a figure. So typing on an automatic person asks first, then seeds every month and
     applies what was typed. Already-manual with no row for this month is the V-31 case
     and needs no question: the months are already the user's. */
  const cellFor = (r, aid, live) => r
    ? `<td class="cell" contenteditable="true" data-sheet="MonthlyEstimate"
         data-row="${r.__row}" data-col="fte">${r.fte ?? ""}</td>`
    : `<td class="cell gapnew" contenteditable="true" data-gapnew="${att(aid || "")}"
         data-gapmonth="${att(mm)}" data-gapman="${live ? "1" : ""}"
         data-tip="${att(`<b>Not stated yet</b><br>`
           + (live ? `This month carries no figure, so it counts as <b>0.00</b> (V-31). `
                   + `Type one here.`
                   : `This person's months on this project are CALCULATED. Type a figure `
                   + `and the application will offer to state them all — it has to, `
                   + `because stating one month means owning every month (REQ-CAL-18).`))}"
       ></td>`;

  const who = lines.map(L => {
    const r = manualAsg.get(L.assignment_id);
    // MANUAL is a property of the ASSIGNMENT, not of whether this month happens to carry
    // a figure. Reading it off the row made an assignment on manual with a month missing
    // (V-31) show as 'auto', which is the opposite of what is wrong with it.
    const a = (M.raw.Assignment || []).find(x => x.assignment_id === L.assignment_id);
    const live = estType(a) === "manual";
    return `<tr>
      <th class="rh"><span class="nm">${esc((M.people[L.person_id] || {}).person_name
        || L.person_id)}</span><span class="role">${esc(L.role_name || "")}</span></th>
      <td>${esc(L.assignment_id || "")}</td>
      <td>${live ? '<span class="est man">MANUAL</span>'
                 : '<span class="est aut">auto</span>'}</td>
      <td class="num">${L.fte.toFixed(2)}${L.overridden_by_project
        ? `<span class="ovr" data-tip="${att(`<b>V-33</b><br>Stated `
            + `${(L.stated_assignment_fte ?? 0).toFixed(2)}, given `
            + `${L.fte.toFixed(2)}.<br>The project's own stated month is the WHOLE `
            + `month, so the people on it are scaled to add up to it (REQ-CAL-18) — `
            + `the project's figure wins.<br><span class="tr">change the project's `
            + `month above to one that leaves room for this</span>`)}">&#9888;</span>`
        : ""}</td>
      ${/* Applied and Stated differing on the same row, with nothing to say why, is the
            silence V-33 was added to end - and repeating it here costs one glyph. The
            project's stated month is the mother figure and scales everyone on it, so a
            person can state 4.00 and be given 2.50 with neither figure being wrong. */
        cellFor(r, L.assignment_id, live)}
      <td><button class="btn tiny" data-act="gopers" data-sid="${att(L.person_id)}"
        data-aid="${att(L.assignment_id)}">Open</button></td></tr>`;
  }).join("");

  el("gapBody").innerHTML = `
    <div class="gapsum ${g ? g.dir : ""}">
      <div><span class="tl">Needs</span><span class="tv">${demand.toFixed(2)}</span></div>
      <div><span class="tl">Staffed</span><span class="tv">${applied.toFixed(2)}</span></div>
      <div><span class="tl">Gap</span><span class="tv">${g
        ? (g.gap > 0 ? "&#9650; +" : "&#9660; ") + g.gap.toFixed(2)
        : "0.00"}</span></div>
      <div class="gapwhat">${g
        ? (g.dir === "short"
            ? "This project is being asked to run on less than its kind usually takes in "
              + "this period."
            : "This project is deliberately staffed heavier than its kind usually is in "
              + "this period.")
        : "This month now matches its standard."}</div></div>
    <p class="cap">What it needs is
      <strong>${periodCell("project", monthFacts("project", pid), pr, mm)}</strong>.
      What it is given is the ${lines.length} figure(s) below added up — the month is
      built from them, so it always equals their sum. Change a MANUAL figure here and
      everything behind this dialog follows.</p>
    ${projRow
      ? `<p class="note"><strong>This project's own month is stated by hand.</strong> It
         is the whole month, and the people below are scaled so they still add up to it
         (REQ-CAL-18) — so this is the figure to change first.</p>
         <table class="grid-t gapt"><thead><tr><th class="rh">The project's stated month</th>
           <th>Applied</th><th>Change it here</th></tr></thead>
         <tbody><tr><th class="rh">${esc(pid)} &#183; ${esc(mm)}</th>
           <td class="num">${applied.toFixed(2)}</td>
           ${cellFor(projRow, null, true)}</tr></tbody></table>`
      : `<p class="note">This project is on <strong>automatic</strong> estimation, so it
         has no stated month of its own — the gap comes from the assignment figures
         below. Change one of those, or switch the assignment back to automatic and let
         it take its share.</p>`}
    <table class="grid-t gapt"><thead><tr><th class="rh">Who is on it</th>
      <th>Assignment</th><th>Estimation</th><th>Applied</th><th>Stated (edit here)</th>
      <th></th></tr></thead>
      <tbody>${who || `<tr><td class="muted" colspan="6">Nobody is assigned to this
        project this month — V-32.</td></tr>`}</tbody></table>
    <p class="note">Edits here are the same edits as anywhere else in the application:
      validated as you leave the cell, listed under <strong>Show details</strong>, undone
      by <strong>Leave without change</strong>, and written only when you press
      <strong>Save</strong>. A person still on <strong>auto</strong> can be given a
      figure too — type in their <code>Stated</code> cell and the application will offer
      to state all of their months, because stating one means owning every one.</p>`;
}

/* ------------------------------ stating a month that has no row yet (REQ-CAL-18) */

/** A figure typed into a Stated cell that has no MonthlyEstimate row behind it.
 *
 *  TWO CASES, AND ONLY ONE OF THEM ASKS.
 *
 *  ALREADY MANUAL, month missing: this is V-31 - the thing covers a month it never
 *  stated, which counts as 0.00. The months are already the user's, so filling one in is
 *  an ordinary edit and a dialog would be asking permission for something already
 *  granted. The 'Fill missing month(s)' button does exactly this in bulk.
 *
 *  STILL AUTOMATIC: this ASKS, and it has to. estimation_type has one way in for a
 *  reason (REQ-CAL-18): writing a single MonthlyEstimate row against an automatic
 *  assignment produces a figure that is read by nothing, and setting the flag without
 *  seeding the other months counts every one of them as 0.00 - the one change in this
 *  application that silently zeroes a figure. So the switch, the seeding and the typed
 *  figure happen together, after one question that says so, or none of them happen.
 *
 *  Everything below goes through beginEditSession / S.pending, so it is listed under
 *  Show details, undone by Leave without change, archived at Save, and it reaches the
 *  file only when the user presses Save - exactly like a cell typed in a table. */
function stateMonth(td){
  const aid = td.dataset.gapnew, mm = td.dataset.gapmonth;
  const raw = td.textContent.trim();
  const back = () => { td.textContent = ""; };
  if (!raw || !aid) return back();
  const v = num(raw);
  if (v === undefined || v === null || v < 0){
    back();
    showBanner("bad", `Edit rejected — '${raw}' is not a figure. Type a monthly FTE, `
      + `such as 1.25. It cannot be negative: a month somebody does not work is 0.00.`);
    return;
  }
  const a = (S.model.raw.Assignment || []).find(x => x.assignment_id === aid);
  if (!a) return back();

  if (estType(a) === "manual"){ writeMonth(aid, mm, round2(v), null); return; }

  const {now} = monthlyOf("assignment", aid);
  const total = [...now.values()].reduce((x, y) => x + y, 0);
  back();                                   // the dialog owns the figure from here
  askEstimation(`State ${assignmentLabel(aid)} by hand?`,
    `<p class="cap">Assignment ${esc(aid)} &#183; ${esc(monthLabel(mm))}</p>
     <p>This assignment's months are <strong>calculated</strong> today. Stating one means
       stating <strong>all ${now.size}</strong> of them: they will be copied across as
       they stand (${total.toFixed(2)} FTE-months in total, to two decimal places), and
       <strong>${esc(monthLabel(mm))}</strong> will then be set to the
       <strong>${round2(v).toFixed(2)}</strong> you typed.</p>
     <p class="note">The copy is what stops the other months jumping — nothing else moves
       by more than the rounding. <strong>All of them become yours, not just this one.</strong>
       Changing a period weight, a role factor or this person's weight will no longer move
       any of them. That is what stating a figure means, and it is why this asks.</p>`,
    "State them, and set this month",
    () => {
      applyEstimationSwitch("assignment", aid, a, "manual", now);
      writeMonth(aid, mm, round2(v), now.get(mm) ?? null);
    },
    null, "Leave it calculated");
}

/** Put a figure on one assignment-month, creating the row if the seeding did not. */
function writeMonth(aid, mm, v, seeded){
  const at = new Date();
  beginEditSession();
  let r = (S.model.raw.MonthlyEstimate || []).find(x =>
    x.scope === "assignment" && x.ref_id === aid && String(x.month) === mm);
  if (!r){
    r = newRow("MonthlyEstimate", {scope:"assignment", ref_id:aid, month:mm, fte:v});
    delete r.__new;                 // complete, not a draft waiting for the rest of it
    S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${aid} ${mm}`,
                    from:null, to:v});
  } else if (round2(r.fte) !== v){
    // The seeding has just written this month at the calculated figure; what is logged
    // is the move FROM that TO what was typed, which is the change somebody made.
    S.pending.push({at, sheet:"MonthlyEstimate", row:r.__row, col:`${aid} ${mm}`,
                    from:seeded === null ? r.fte : round2(seeded), to:v});
    r.fte = v;
  }
  S.editedCells.add(`MonthlyEstimate|${r.__row}|fte`);
  rebuild(true);
  renderKeepingTab();
  showBanner("", `${assignmentLabel(aid)} — ${monthLabel(mm)} is now stated at `
    + `${v.toFixed(2)}. This is provisional; press Save to keep it.`);
}
