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

   WHERE THIS IS SAID, and how it stays loud behind a click (R-52).

   It was a panel under the tiles, on the ground that a surface you only visit once you
   already suspect a problem is the wrong place for something whose whole danger is that
   it is silent. Asked for from the field: move it onto Resource by project, which is the
   table the figures belong to, and open it from there. That is the right home - every
   month in this list is a cell in that table, and the two were a scroll apart - but it
   costs the one property the panel was placed for, so the cost is paid back rather than
   accepted.

   THE CONTROL CARRIES THE COUNT. The button in that panel's head does not read
   "Standard vs staffed"; it reads how many months are off the standard and in which
   direction, with the same arrow and the same colour the cells use. So the alarm is on
   screen without anything being opened, which is what the panel was there for, and the
   LIST - which nobody reads until they are investigating - is one click away. The tile
   above still counts it, every cell is still marked where it is drawn, and V-34 still
   carries it to the findings report, the load banner and the archived log.

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

/* ---------------------------------------------------------------- manager review (R-62)

   A month off its standard is a FINDING, and a finding a manager has looked at is not
   the same as one nobody has: "PRJ-007 is over by 0.9 in March - sponsor-funded extra
   cleaning" is a decision, and drawing it in the same alarm red as an unexamined one makes
   the real alarms harder to find. So each issue can carry a REVIEW (IssueReview sheet):
   'Confirmed - no issue' or 'Accepted' CLOSE it - it stays on screen, muted, with its
   reason - and 'To be fixed' keeps it open with a note of what is planned.

   A REVIEW COVERS THE FIGURES IT WAS MADE ON. gap_fte records the gap as reviewed; if
   the month's gap moves, the review no longer describes it and the issue is shown open
   again, marked 're-check', rather than staying closed on a decision about different
   numbers (V-40). */
const REVIEW_CLOSED = new Set(["confirmed - no issue", "accepted"]);
const REVIEW_STATUSES = ["Confirmed - no issue", "Accepted", "To be fixed"];

/** The review of one issue, and what it means now - or null if nobody has reviewed it. */
function reviewOf(pid, k, dir, gap){
  const r = ((S.model && S.model.reviews) || {})[`${pid}|${isoMonth(k)}|${dir}`];
  if (!r) return null;
  const status = String(r.status || "").trim();
  const was = num(r.gap_fte);
  const changed = was !== null && was !== undefined && gap !== undefined
    && Math.round(was * 100) !== Math.round(gap * 100);
  const closes = REVIEW_CLOSED.has(status.toLowerCase());
  return {row:r, status, closed: closes && !changed, changed, fix: /fix/i.test(status),
          rationale: r.rationale || "", by: r.reviewed_by || "", at: r.reviewed_at || ""};
}

/** One line for a pop-up: who decided what, and why. */
function reviewLine(rv){
  if (!rv) return "";
  return `<span class="tr">&#10003; ${esc(rv.status || "reviewed")}`
    + (rv.by ? ` by ${esc(rv.by)}` : "") + (rv.at ? `, ${esc(String(rv.at).slice(0, 16))}` : "")
    + (rv.changed ? ` &#183; <b>re-check: the gap has changed since</b>` : "")
    + (rv.rationale ? `<br>&#8220;${esc(rv.rationale)}&#8221;` : "") + `</span><br>`;
}

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
  /* AND THE MONTHS NOBODY IS ON (R-56). A month the project's periods ask for with
     nobody assigned is the widest gap there is - needs the whole standard, staffed at
     nothing - and it was the one this list and the control above it left out: the table
     drew it, in its own ◦ cells, and the alarm said nothing. Its own direction,
     'unstaffed', because the fix is different: there is no figure to change, somebody
     has to be assigned. */
  for (const [qk, u] of (C.projUnallocated || new Map())){
    if (!(u > 0.004)) continue;
    const i = qk.lastIndexOf("|");
    const pid = qk.slice(0, i), k = +qk.slice(i + 1);
    if (want.size && !want.has(pid)) continue;
    out.push({pid, k, demand: u, applied: 0, gap: -u, dir: "unstaffed"});
  }
  for (const r of out) r.rev = reviewOf(r.pid, r.k, r.dir, r.gap);
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

/* ------------------------------------------------- the control, and the list behind it */

const GAP_SHOW = 500;     // rows drawn - a safety cap; a real plan lists far fewer

/** The control in Resource by project's head.
 *
 *  IT STATES THE FINDING, it does not merely name the screen behind it. "Standard vs
 *  staffed" would be a label; "3 short, 1 over" is the fact the old panel was on the page
 *  to deliver, and it is delivered without anything being opened - which is the whole of
 *  what moving the list into a dialog had to pay back (R-52).
 *
 *  It is drawn even when there is nothing to report, quietly and without a count. A
 *  control that comes and goes is one nobody learns the position of, and its absence
 *  cannot be told from a screen that has not been looked at; present and silent says
 *  "this was checked" where missing says nothing at all.
 */
function gapButton(pids){
  const all = gapRows(pids);
  const rows = all.filter(r => !(r.rev && r.rev.closed));
  const done = all.length - rows.length;
  /* The counts are the OPEN issues (R-62): a month a manager has confirmed or accepted is
     a decision, not an alarm, and counting it as one would make the alarm say less the
     more carefully the plan is reviewed. The reviewed ones are counted beside them, in
     the muted ink they are drawn in, so nothing disappears. */
  const tail = done ? `<span class="grev">&#10003; ${done} reviewed</span>` : "";
  if (!rows.length)
    return `<button class="btn tiny gapbtn" data-gapopen="1" data-tip="${att(
      "<b>Standard vs staffed</b><br>What each project needs against what it is being "
      + "given. " + (done ? `Every month off its standard in view has been reviewed and `
                            + `closed by a manager - open the list to read why.`
                          : "Nothing in view is off its standard, which is what an "
                            + "automatic month always does — the people on it divide "
                            + "the month rather than each adding to it."))
      }">${done ? `<span class="lbl">Off standard</span>${tail}` : "Standard vs staffed"}</button>`;
  const short = rows.filter(r => r.dir === "short").length;
  const over = rows.filter(r => r.dir === "over").length;
  const unst = rows.filter(r => r.dir === "unstaffed").length;
  return `<button class="btn tiny gapbtn on" data-gapopen="1" data-tip="${att(
    `<b>Standard vs staffed</b><br>${rows.length} project-month(s) are not being given `
    + "what the project's own standard says they need, and nobody has closed them. Short or "
    + "over: a figure stated by hand replaces the standard rather than adjusting it. Not "
    + "staffed: the project's periods ask for the month and nobody is assigned to it. "
    + (done ? `${done} more have been reviewed and closed by a manager. ` : "")
    + "Counted apart and never netted. Open it to see every one, review it, or change "
    + "what is behind it.")}">`
    /* The words first, so the two figures are read as what they are rather than as a
       pair of numbers in a button. Each part is its own element and the spacing is the
       flex gap: .btn.tiny is an inline-flex box, which DROPS the whitespace between its
       children, so spaces written into the string render as nothing - which is how this
       first went out reading "17 short&#183;49 overof standard". */
    + `<span class="lbl">Off standard</span>`
    + (short ? `<span class="gshort">&#9660; ${short} short</span>` : "")
    + (over ? `<span class="gover">&#9650; ${over} over</span>` : "")
    + (unst ? `<span class="gunst">&#9702; ${unst} not staffed</span>` : "")
    + tail + "</button>";
}

/** What the list is narrowed to, applied to the rows the model offers (R-53).
 *
 *  NARROWS THE LIST, NEVER THE COUNT. gapRows() is what the tile and the control in
 *  Resource by project's head read, and they must go on counting every month off its
 *  standard whatever is set here: a figure that moved when somebody narrowed their own
 *  view would be an alarm that lies, which is worse than no alarm. So this is applied in
 *  one place - where the rows are drawn - and nowhere else.
 */
function gapKept(rows){
  const f = S.gapf;
  const min = Math.abs(num(f.min) ?? 0);
  return rows.filter(r => (!f.dir || r.dir === f.dir)
                       && (!f.proj || r.pid === f.proj)
                       && (!f.rev || (f.rev === "closed") === !!(r.rev && r.rev.closed))
                       && Math.abs(r.gap) + 1e-9 >= min);
}

const gapNarrowed = () => !!(S.gapf.dir || S.gapf.proj || S.gapf.rev
                             || (num(S.gapf.min) ?? 0) > 0);

/** The controls. Three, and each answers a question somebody actually arrives with:
 *  which direction am I chasing, which project is this about, and what is big enough to
 *  be worth my morning. A fourth would be the month, and the horizon above the page
 *  already is that. */
function gapControls(all){
  const f = S.gapf;
  const projects = [...new Set(all.map(r => r.pid))]
    .sort((a, b) => (projectNameOf(a) || a) < (projectNameOf(b) || b) ? -1 : 1);
  const dir = [["", "All"], ["short", "&#9660; Short"], ["over", "&#9650; Over"],
               ["unstaffed", "&#9702; Not staffed"]]
    .map(([v, l]) => `<button class="btn tiny${f.dir === v ? " on" : ""}" `
      + `data-gapdir="${att(v)}">${l}</button>`).join("");
  const rev = [["", "Any review"], ["open", "Open"], ["closed", "&#10003; Reviewed"]]
    .map(([v, l]) => `<button class="btn tiny${(f.rev || "") === v ? " on" : ""}" `
      + `data-gaprev="${att(v)}">${l}</button>`).join("");
  return `<div class="gapf">
    <span class="vtog">${dir}</span>
    <span class="vtog">${rev}</span>
    <label class="ctl"><span>Project</span>
      <select id="gapfProj"><option value="">All (${projects.length})</option>
        ${projects.map(p => `<option value="${att(p)}"${f.proj === p ? " selected" : ""}>`
          + `${esc(projectNameOf(p) || p)}</option>`).join("")}</select></label>
    <label class="ctl"><span>Gap at least</span>
      <input id="gapfMin" type="number" min="0" step="0.25" inputmode="decimal"
        value="${att(f.min || "")}" placeholder="0.00"></label>
    ${gapNarrowed() ? `<button class="btn tiny" data-gapclear="1">Clear</button>` : ""}
  </div>`;
}

/** The body of that dialog. The panel this replaces carried the same thing. */
function gapList(pids){
  const M = S.model, all = gapRows(pids), rows = gapKept(all);
  const open = rows.filter(r => !(r.rev && r.rev.closed));
  const short = open.filter(r => r.dir === "short");
  const over = open.filter(r => r.dir === "over");
  const unst = open.filter(r => r.dir === "unstaffed");
  const closedN = rows.length - open.length;
  const projects = new Set(rows.map(r => r.pid));
  /* NOTHING TO REPORT AND NOTHING LEFT AFTER FILTERING ARE DIFFERENT ANSWERS, and only
     one of them is good news. Saying "every project is on its standard" to somebody who
     has just narrowed to one project and a 5.00 floor would be a plain untruth, and the
     way out - clear the filter - is not the way out of the other. */
  if (!rows.length && all.length)
    return gapControls(all)
      + `<p class="cap">All <strong>${all.length}</strong> of them are hidden by the
        filter above. <strong>Clear</strong> brings them back.</p>`;
  if (!rows.length)
    return `<p class="cap">Every project in view is drawing exactly what its own standard
      says it needs — <strong>standard FTE × period weight × the part of the month it
      runs</strong>. That is what an automatic month always does, because the people on
      it divide the month rather than each adding to it. A figure stated by hand, on a
      project or on one assignment, replaces the standard rather than adjusting it, and
      this is where the difference is listed when there is one.</p>`;

  /* By project ID, then month, both ascending (asked for after R-62): the list is read
     project by project, a run of months together, the way Resource by project lays them
     out. IDs compare as numbers where they hold them, so PRJ-2 comes before PRJ-10.
     Reviewed months stay in their place, drawn muted; the Open / Reviewed filter is what
     separates them. It used to be largest first, capped at 40 - which, sorted this way,
     would have cut whole projects off the end, so every month is drawn now. */
  const ordered = rows.slice().sort((x, y) =>
    String(x.pid).localeCompare(String(y.pid), undefined, {numeric: true})
    || x.k - y.k || String(x.dir).localeCompare(String(y.dir)));
  const body = ordered.slice(0, GAP_SHOW).map(r => {
    const pr = M.projects[r.pid] || {};
    const rv = r.rev;
    const revCell = !rv ? `<span class="muted">not reviewed</span>`
      : `<span class="revtag${rv.closed ? " done" : rv.changed ? " stale" : " fix"}">`
        + `${rv.changed ? "re-check &#183; " : rv.closed ? "&#10003; " : ""}${esc(rv.status)}</span>`
        + (rv.rationale ? `<span class="sub">${esc(rv.rationale)}</span>` : "");
    return `<tr class="gaprow ${r.dir}${rv && rv.closed ? " rev" : ""}" data-gap="${att(r.pid)}"
        data-gk="${r.k}" data-gapis="${att(r.dir)}" tabindex="0" role="button">
      <th class="rh"><span class="nm">${esc(pr.project_name || r.pid)}</span>
        <span class="sub">${esc(r.pid)}</span></th>
      <td>${keyToLabel(r.k)}</td>
      <td class="num">${r.demand.toFixed(2)}</td>
      <td class="num">${r.applied.toFixed(2)}</td>
      <td class="num ${r.dir}">${r.dir === "unstaffed" ? "&#9702; "
        : r.gap > 0 ? "&#9650; +" : "&#9660; "}${r.gap.toFixed(2)}</td>
      <td>${r.dir === "short" ? "short of the standard"
          : r.dir === "over" ? "over the standard" : "nobody is assigned"}</td>
      <td class="revcell">${revCell}</td>
      <td><button class="btn tiny" data-gap="${att(r.pid)}" data-gk="${r.k}"
        data-gapis="${att(r.dir)}">${rv ? "Open" : "Review"}</button></td></tr>`;
  }).join("");

  return `<p class="cap"><span class="scope k">${gapNarrowed()
      ? `${rows.length} of ${all.length} month(s)` : `${rows.length} month(s)`}
      across ${projects.size} project(s)</span><br>What each project <strong>needs</strong> — standard FTE × period
      weight × the part of the month it runs — against what it is actually
      <strong>being given</strong>. These are the two figures that can come apart. The
      project's month against the sum of its people cannot: the month is built from those
      people, so it is their sum by construction. A figure stated by hand replaces the
      standard rather than adjusting it, which is what puts these two out of step —
      <strong>deliberately</strong>, in every case, which is why this reports rather than
      refuses. <strong>Click any row</strong> to see the month and change the figures
      behind it.</p>
    ${gapControls(all)}
    <div class="gtot">
      <span class="gpill short">&#9660; ${short.length} month(s) short of the standard</span>
      <span class="gpill over">&#9650; ${over.length} month(s) over it</span>
      ${unst.length ? `<span class="gpill unstaffed">&#9702; ${unst.length} month(s) with
        nobody assigned</span>` : ""}
      ${closedN ? `<span class="gpill reviewed">&#10003; ${closedN} reviewed and closed</span>` : ""}
      <span class="tr">counted apart, never netted — three short in March and three over
        in April is not a plan in balance</span></div>
    <div class="scrollx lg"><table class="grid-t gapt">
      <thead><tr><th class="rh">Project</th><th>Month</th><th>Needs</th>
        <th>Staffed</th><th>Gap</th><th>Direction</th><th>Manager review</th><th></th></tr></thead>
      <tbody>${body}</tbody></table></div>
    ${rows.length > GAP_SHOW
      ? `<p class="note">Showing the first ${GAP_SHOW} of ${rows.length}, by project and month${
          gapNarrowed() ? ` that match the filter (${all.length} in all)` : ""}. The rest
         are in the findings report, which lists every one of them by project.</p>` : ""}
    <p class="note">V-34 reports this as a <strong>warning</strong>: it reaches the
      findings report, the load banner and the archived change log, and it never stops a
      save or asks a question. Departing from the standard is the point of a manual
      figure — somebody part way through a trial knows better than the assumptions — so
      the application says so and leaves the decision where it belongs.</p>`;
}

/* --------------------------------------------------------------- the list dialog */

/** Open the list. Drawn at the moment it is asked for, never kept up to date while shut:
 *  what it lists is derived entirely from S.calc, so there is nothing to keep. */
function openGaps(){
  el("gapsBody").innerHTML = gapList(activeProjects());
  const dlg = el("gapsdlg");
  if (!dlg.open) dlg.showModal();
  cueScrollers();          // the table inside it has a bounded region of its own
}

function closeGaps(){
  const dlg = el("gapsdlg");
  if (dlg.open) dlg.close();
}

/** Redraw it after an edit, for the reason gapRefresh() gives below: a list still
 *  showing the gap you have just closed reads as an edit that did nothing. This one also
 *  has to redraw when the gap was closed from the MONTH dialog on top of it, which is the
 *  ordinary way it happens. */
function gapsRefresh(){ if (el("gapsdlg").open) openGaps(); }

/* ------------------------------------------------------------- the month dialog */

let GAP_AT = null;         // {pid, k} while the dialog is open, so an edit can redraw it

/** Open the month, with the figures that caused the gap editable in place - and, since
 *  R-62, the manager's review of it. `dir` says WHICH issue when a caller knows; a cell
 *  in the table does not have to, because a month is short, over or unstaffed, never two
 *  of them at once. */
function openGap(pid, k, dir){
  const g = gapOf(pid, k);
  const u = (S.calc.projUnallocated && S.calc.projUnallocated.get(pid + "|" + k)) || 0;
  GAP_AT = {pid, k, dir: dir || (g ? g.dir : u > 0.004 ? "unstaffed" : "")};
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
function gapRefresh(){
  if (GAP_AT && el("gapdlg").open) drawGap();
  gapsRefresh();
}

function drawGap(){
  const M = S.model, {pid, k, dir} = GAP_AT;
  const pr = M.projects[pid] || {};
  const g = gapOf(pid, k);
  const mm = isoMonth(k);
  /* A month NOBODY IS ON (R-62 makes it openable): there is no figure to change, only an
     assignment to make - or a decision to record. */
  if (dir === "unstaffed"){
    const now = issueNow(pid, k, dir);
    el("gapTitle").innerHTML = `${esc(pr.project_name || pid)} `
      + `<span class="tr">${esc(pid)} &#183; ${keyToLabel(k)}</span>`;
    el("gapBody").innerHTML = `
      <div class="gapsum unstaffed">
        <div><span class="tl">Needs</span><span class="tv">${now ? now.demand.toFixed(2) : "0.00"}</span></div>
        <div><span class="tl">Staffed</span><span class="tv">0.00</span></div>
        <div><span class="tl">Gap</span><span class="tv">${now ? "&#9702; " + now.gap.toFixed(2) : "0.00"}</span></div>
        <div class="gapwhat">${now ? "The project's own periods ask for this month and nobody "
          + "is assigned to it." : "Somebody is assigned to this month now."}</div></div>
      ${reviewPanel(pid, k, dir)}
      <p class="cap">The fix, where there is one, is an assignment: open the project and add
        somebody on its <strong>Source data (person)</strong> tab.</p>`;
    return;
  }
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
    ${g ? reviewPanel(pid, k, g.dir) : ""}
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

/* ------------------------------------------------------- the review, in the dialog (R-62) */

/** The issue the dialog is on, as figures: what it needs, what it is given, the gap. */
function issueNow(pid, k, dir){
  if (dir === "unstaffed"){
    const u = (S.calc.projUnallocated && S.calc.projUnallocated.get(pid + "|" + k)) || 0;
    return u > 0.004 ? {demand:u, applied:0, gap:-u} : null;
  }
  const g = gapOf(pid, k);
  return g && g.dir === dir ? g : null;
}

/** The months either side of `k` that carry the same issue on the same project - one
 *  run, so a decision about "the four months PRJ-007 is over in 2027" is one decision. */
function issueRun(pid, k, dir){
  const ks = new Set(gapRows([pid]).filter(r => r.dir === dir).map(r => r.k));
  if (!ks.has(k)) return [k];
  let lo = k, hi = k;
  while (ks.has(lo - 1)) lo--;
  while (ks.has(hi + 1)) hi++;
  const out = [];
  for (let m = lo; m <= hi; m++) out.push(m);
  return out;
}

/** The name this browser already knows, without asking for it: the review form says who
 *  confirmed the issue, and that is usually - not always - the person at the keyboard. */
function knownWho(){
  if (S.who && S.who !== "(not stated)") return S.who;
  let v = "";
  try { v = localStorage.getItem(WHO_KEY) || ""; } catch (e){ /* private mode */ }
  return v === "(not stated)" ? "" : v;
}

function reviewPanel(pid, k, dir){
  const now = issueNow(pid, k, dir);
  if (!now) return "";
  const rv = reviewOf(pid, k, dir, now.gap);
  const run = issueRun(pid, k, dir);
  const words = {short:"short of its standard", over:"over its standard",
                 unstaffed:"with nobody assigned"}[dir] || dir;
  const opts = [["", "Not reviewed"], ...REVIEW_STATUSES.map(x => [x, x])]
    .map(([v, l]) => `<option value="${att(v)}"${rv && rv.status === v ? " selected" : ""}>`
      + `${esc(l)}</option>`).join("");
  /* The whole run is offered ticked for a first review - a run is usually one decision -
     and unticked once there is one, so changing or removing it touches this month unless
     asked: its neighbours may carry decisions of their own. */
  return `<div class="revbox ${rv ? (rv.closed ? "closed" : rv.changed ? "stale" : "open") : "none"}">
    <h3>Manager review</h3>
    <p class="revnow">${rv
      ? `<b>${rv.closed ? "&#10003; " : ""}${esc(rv.status)}</b>`
        + (rv.by ? ` by ${esc(rv.by)}` : "") + (rv.at ? `, ${esc(String(rv.at))}` : "")
        + (rv.rationale ? `<br>&#8220;${esc(rv.rationale)}&#8221;` : "")
        + (rv.changed ? `<br><b class="restale">Re-check:</b> this was reviewed at a gap of `
            + `${(num(rv.row.gap_fte) || 0).toFixed(2)}; it is ${now.gap.toFixed(2)} now, so `
            + `the review no longer closes it.` : "")
      : `Not reviewed yet. This month is ${words} by <b>${Math.abs(now.gap).toFixed(2)}</b> FTE.`}</p>
    <div class="revform">
      <label class="ctl"><span>Decision</span><select id="revStatus">${opts}</select></label>
      <label class="ctl"><span>Manager</span><input id="revBy" type="text"
        placeholder="who confirmed it" value="${att(rv && rv.by ? rv.by : knownWho())}"></label>
      <label class="ctl wide"><span>Reason (shown to anybody who opens this issue)</span>
        <textarea id="revWhy" rows="2">${esc(rv ? rv.rationale : "")}</textarea></label>
      ${run.length > 1 ? `<label class="chk"><input type="checkbox" id="revRun"${rv ? "" : " checked"}>
        Apply to the whole run: the ${run.length} consecutive months
        ${keyToLabel(run[0])} to ${keyToLabel(run[run.length - 1])} that are ${words}</label>` : ""}
      <p class="revmsg" id="revMsg" role="alert" hidden></p>
      <div class="revbtns">
        <button class="btn primary" data-revsave="1">Save review</button>
        ${rv ? `<button class="btn" data-revclear="1">Remove review</button>` : ""}
        <span class="tr">or change the data instead:</span>
        <button class="btn" data-act="goproj" data-pid="${att(pid)}">Open the project</button>
      </div>
    </div>
    <p class="note"><b>Confirmed - no issue</b> and <b>Accepted</b> close the issue: it stays
      on every screen, muted, and its reason is shown whenever it is opened.
      <b>To be fixed</b> keeps it open, with your note. A review covers the figures it was
      made on - if the gap changes, it asks for a fresh look. Recorded like any other edit:
      press <b>Save</b> to keep it.</p>
  </div>`;
}

/** Write the review for the month in the dialog - or its whole run - as IssueReview rows,
 *  through the same pending list every other edit goes through, so Save, Leave without
 *  change and the change log treat it exactly as they treat a typed cell. */
function saveReview(){
  if (!GAP_AT) return;
  const {pid, k, dir} = GAP_AT;
  const status = el("revStatus").value;
  const why = el("revWhy").value.trim();
  if (!status) return clearReview();
  if (REVIEW_CLOSED.has(status.toLowerCase()) && !why){
    /* Said IN the box, not on the page banner: the banner is behind this dialog, and a
       refusal nobody can see reads as a button that does nothing. */
    const m = el("revMsg");
    if (m){
      m.textContent = `'${status}' closes the issue, so it needs a reason - the reason is `
        + `what makes a closed issue checkable by anybody who opens it later.`;
      m.hidden = false;
    }
    el("revWhy").classList.add("bad");
    el("revWhy").focus();
    return;
  }
  const by = el("revBy") ? el("revBy").value.trim() : "";
  const months = el("revRun") && el("revRun").checked ? issueRun(pid, k, dir) : [k];
  beginEditSession();
  const p2 = n => String(n).padStart(2, "0"), d = new Date();
  const at = `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} `
    + `${p2(d.getHours())}:${p2(d.getMinutes())}`;
  let n = 0;
  for (const m of months){
    const now = issueNow(pid, m, dir);
    if (!now) continue;
    const mm = isoMonth(m);
    const want = {status, rationale: why || null, gap_fte: Math.round(now.gap * 100) / 100,
                  reviewed_by: by || knownWho() || null, reviewed_at: at};
    let r = S.model.raw.IssueReview.find(x => x.project_id === pid
      && String(x.month).slice(0, 7) === mm && String(x.issue).trim().toLowerCase() === dir);
    if (!r){
      r = newRow("IssueReview", {project_id: pid, month: mm, issue: dir});
      delete r.__new;                 // complete, not a draft waiting for the rest of it
      S.pending.push({at: new Date(), sheet: "IssueReview", row: r.__row, col: "(new row)",
                      from: null, to: `${pid} ${mm} ${dir}`});
    }
    for (const [c, v] of Object.entries(want)){
      if (r[c] === v) continue;
      S.pending.push({at: new Date(), sheet: "IssueReview", row: r.__row, col: c,
                      from: r[c] ?? null, to: v});
      r[c] = v;
    }
    n++;
  }
  rebuild(true);
  renderKeepingTab();
  showBanner("", `Review recorded on ${n} month(s) of ${pid}: ${status}. Press Save to keep it.`);
}

function clearReview(){
  if (!GAP_AT) return;
  const {pid, k, dir} = GAP_AT;
  // The same reach as Save: a run reviewed as one decision is withdrawn as one.
  const months = el("revRun") && el("revRun").checked ? issueRun(pid, k, dir) : [k];
  let n = 0;
  for (const m of months){
    const mm = isoMonth(m);
    const r = S.model.raw.IssueReview.find(x => x.project_id === pid
      && String(x.month).slice(0, 7) === mm && String(x.issue).trim().toLowerCase() === dir);
    if (!r) continue;
    deleteRow("IssueReview", r.__row);
    n++;
  }
  if (n) showBanner("", `Review removed from ${n} month(s) of ${pid}; the issue is open `
    + `again. Press Save to keep it.`);
}
