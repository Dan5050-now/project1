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

  const cellFor = r => r
    ? `<td class="cell" contenteditable="true" data-sheet="MonthlyEstimate"
         data-row="${r.__row}" data-col="fte">${r.fte ?? ""}</td>`
    : `<td class="muted">—</td>`;

  const who = lines.map(L => {
    const r = manualAsg.get(L.assignment_id);
    return `<tr>
      <th class="rh"><span class="nm">${esc((M.people[L.person_id] || {}).person_name
        || L.person_id)}</span><span class="role">${esc(L.role_name || "")}</span></th>
      <td>${esc(L.assignment_id || "")}</td>
      <td>${r ? '<span class="est man">MANUAL</span>' : '<span class="est aut">auto</span>'}</td>
      <td class="num">${L.fte.toFixed(2)}</td>
      ${cellFor(r)}
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
           <td class="num">${applied.toFixed(2)}</td>${cellFor(projRow)}</tr></tbody></table>`
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
      <strong>Save</strong>.</p>`;
}
