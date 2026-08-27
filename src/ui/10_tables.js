/* ============================================================ 10. tables */

/** Month labels with the year shown where it changes, plus a divider at each year
 *  boundary. Repeating the year under all 24 columns is noise; showing it only at the
 *  first column and each January is the smallest mark that answers "which year is this".
 *  One helper so the three time charts label their axes identically. */
function monthAxis(o, G, xOf, bw, yLabel, yTick, yDiv0, yDiv1){
  G.forEach((k, i) => {
    const [mon, yr] = keyToLabel(k).split(" ");
    const cx = xOf(i) + bw / 2;
    o.push(`<text class="ax" x="${cx.toFixed(1)}" y="${yLabel}" text-anchor="middle">${mon}</text>`);
    if (i === 0 || k % 12 === 0){
      o.push(`<text class="ax yr" x="${cx.toFixed(1)}" y="${yTick}" text-anchor="middle">${yr}</text>`);
      if (i > 0){
        const dx = xOf(i) - (bw * 0.06);
        o.push(`<line class="yrdiv" x1="${dx.toFixed(1)}" y1="${yDiv0}" x2="${dx.toFixed(1)}" y2="${yDiv1}"/>`);
      }
    }
  });
}

function monthHead(){
  return grid().map(k => {
    const [mon, yr] = keyToLabel(k).split(" ");
    const tip = `<b>${keyToLabel(k)}</b><br>Each cell is that month's load in ${unitLabel()}: `
      + `period weight × role factor × person weight × the fraction of the month covered. `
      + `A partial month is prorated by calendar days.`;
    return `<th data-tip="${att(tip)}">${mon}<br><span class="sub">${yr}</span></th>`;
  }).join("");
}

function tableProjects(pids){
  const M = S.model, C = S.calc, G = grid();
  const listed = pids.slice().sort(byRank);
  let vmax = 0;
  for (const p of listed) for (const k of G) vmax = Math.max(vmax, C.projMonth.get(p+"|"+k) || 0);
  const body = [];
  for (const pid of listed){
    const open = S.expanded.has("p-"+pid);
    let tot = 0;
    const tds = G.map(k => {
      const v = C.projMonth.get(pid+"|"+k) || 0; tot += v;
      if (v <= 0.004) return '<td class="c z">&middot;</td>';
      const i = seqStep(v, vmax);
      return `<td class="c" style="background:${SEQ[i]};color:${i>6?"#fff":"var(--ink)"}">${fmt(v)}</td>`;
    }).join("");
    body.push(`<tr class="parent" data-k="p-${esc(pid)}" tabindex="0" role="button" `
      + `aria-expanded="${open}"><th class="rh"><span class="exp">${open?"&#9662;":"&#9656;"}</span>`
      + `<span class="nm">${esc(M.projects[pid].project_name)}</span>${typePill(pid)}${phasePill(pid)}`
      + `<span class="sub">${esc(pid)} &middot; starts ${ymd(M.projects[pid].start_date)}</span></th>`
      + `${tds}<td>${fmt(tot)}</td></tr>`);
    if (!open) continue;
    const rows = M.assignments.filter(a => a.project_id === pid)
      .sort((a,b) => (a.role_name||"").localeCompare(b.role_name||"") ||
                     (a.person_id||"").localeCompare(b.person_id||""));
    for (const a of rows){
      let dt = 0;
      const dtds = G.map(k => {
        const v = C.cell.get([pid, a.person_id, a.role_name, k].join("|")) || 0; dt += v;
        return v > 0.004 ? `<td class="c">${fmt(v)}</td>` : '<td class="c z">&middot;</td>';
      }).join("");
      if (dt <= 0.004) continue;
      body.push(`<tr class="child"><th class="rh">&#8627; `
        + `${esc((M.people[a.person_id]||{}).person_name || a.person_id)}`
        + `<span class="role">${esc(a.role_name)}</span></th>${dtds}<td>${fmt(dt)}</td></tr>`);
    }
  }
  let gt = 0;
  const gtds = G.map(k => {
    let s = 0; for (const p of listed) s += C.projMonth.get(p+"|"+k) || 0; gt += s;
    return `<td>${fmt(s)}</td>`;
  }).join("");
  body.push(`<tr class="grand"><th class="rh">All ${listed.length} projects</th>${gtds}<td>${fmt(gt)}</td></tr>`);
  return `<table class="grid-t"><thead><tr><th class="rh">Project</th>${monthHead()}`
    + `<th>Total</th></tr></thead><tbody>${body.join("")}</tbody></table>`;
}

function tablePeople(sids){
  const M = S.model, C = S.calc, G = grid();
  const listed = sids.slice().sort();
  let vmax = 0;
  for (const s of listed) for (const k of G) vmax = Math.max(vmax, C.persMonth.get(s+"|"+k) || 0);
  const body = [];
  for (const sid of listed){
    const open = S.expanded.has("s-"+sid);
    let tot = 0;
    const tds = G.map(k => {
      const v = C.persMonth.get(sid+"|"+k) || 0; tot += v;
      if (v > M.OVER) return `<td class="c over">&#9650; ${fmt(v)}</td>`;
      if (v > 0 && v < M.UNDER) return `<td class="c under">&#9660; ${fmt(v)}</td>`;
      if (v <= 0.004) return '<td class="c z">&middot;</td>';
      const i = seqStep(v, vmax);
      return `<td class="c" style="background:${SEQ[i]};color:${i>6?"#fff":"var(--ink)"}">${fmt(v)}</td>`;
    }).join("");
    const cap = num((M.people[sid]||{}).capacity_fte);
    body.push(`<tr class="parent" data-k="s-${esc(sid)}" tabindex="0" role="button" `
      + `aria-expanded="${open}"><th class="rh"><span class="exp">${open?"&#9662;":"&#9656;"}</span>`
      + `<span class="nm">${esc((M.people[sid]||{}).person_name || sid)}</span>`
      + `<span class="sub">${esc(sid)}${cap!==null&&cap!==undefined?` &middot; capacity ${cap.toFixed(2)} FTE`:""}`
      + ` &middot; ${esc((M.people[sid]||{}).department || "")}</span></th>${tds}<td>${fmt(tot)}</td></tr>`);
    if (!open) continue;
    const mine = M.assignments.filter(a => a.person_id === sid)
      .sort((a,b) => byRank(a.project_id, b.project_id));
    for (const a of mine){
      let dt = 0;
      const dtds = G.map(k => {
        const v = C.cell.get([a.project_id, sid, a.role_name, k].join("|")) || 0; dt += v;
        return v > 0.004 ? `<td class="c">${fmt(v)}</td>` : '<td class="c z">&middot;</td>';
      }).join("");
      if (dt <= 0.004) continue;
      body.push(`<tr class="child"><th class="rh">&#8627; `
        + `${esc((M.projects[a.project_id]||{}).project_name || a.project_id)}`
        + `${typePill(a.project_id)}${phasePill(a.project_id)}`
        + `<span class="role">${esc(a.role_name)}</span></th>${dtds}<td>${fmt(dt)}</td></tr>`);
    }
  }
  let gt = 0;
  const gtds = G.map(k => {
    let s = 0; for (const p of listed) s += C.persMonth.get(p+"|"+k) || 0; gt += s;
    return `<td>${fmt(s)}</td>`;
  }).join("");
  body.push(`<tr class="grand"><th class="rh">All ${listed.length} people</th>${gtds}<td>${fmt(gt)}</td></tr>`);
  return `<table class="grid-t"><thead><tr><th class="rh">Person</th>${monthHead()}`
    + `<th>Total</th></tr></thead><tbody>${body.join("")}</tbody></table>`;
}

/** Editable data table. Every cell is editable; edits are validated on entry. */
/** Value suggestions for a column: the Lists sheet where the column is backed by one,
 *  otherwise the distinct values already present in that column. The second half is what
 *  covers project_category, department and the rest - columns with no formal list but a
 *  real vocabulary that a typist should not have to remember or re-invent. */
const LIST_FOR = {
  project_type:"project_type", clinical_phase:"clinical_phase",
  work_scope_type:"work_scope_type", status:"project_status",
  EDC_setup:"setup_party", DataReviewSystem_setup:"setup_party",
  RBQM_setup:"setup_party", DM_conduct:"setup_party",
  EDC_system:"EDC_system", DataReviewSystem:"DataReviewSystem", RBQM_system:"RBQM_system",
  milestone_name:"milestone_name",
};
/** A column the user TYPES INTO that is not stored on the row it appears in.
 *
 *  On the Assignments table the project is identified by project_id, and 'PRJ-014' is
 *  not what anyone knows a project by. So project_name is the field to fill in, and the
 *  identifier is derived from it: type a name, and project_id follows. Editing
 *  project_id directly still works and the name follows instead - the two are one field
 *  seen from two ends, not a field and a copy of it.
 *
 *  The name is never written onto the Assignment row. The Assignment sheet has no such
 *  column, so a stored copy could not survive an export and re-import, and it would be a
 *  second version of a fact the Project sheet already owns. */
const PROXY = {
  Assignment: {
    project_name: {
      into: "project_id",
      show: r => (S.model.projects[r.project_id] || {}).project_name ?? "",
      options: () => Object.values(S.model.projects)
        .map(p => p.project_name).filter(v => v !== null && v !== undefined && v !== "")
        .map(String).sort(),
      resolve(name){
        const want = String(name).trim().toLowerCase();
        const hits = Object.values(S.model.projects)
          .filter(p => String(p.project_name ?? "").trim().toLowerCase() === want);
        if (hits.length === 1) return {value: hits[0].project_id};
        if (hits.length) return {error: `More than one project is called '${name}'. `
          + `Enter the project_id instead — that is the field that has to be unique.`};
        const near = this.options().filter(o => o.toLowerCase().includes(want)).slice(0, 3);
        return {error: `No project is called '${name}'.`
          + (near.length ? ` Did you mean ${near.map(o => `'${o}'`).join(", ")}?`
                         : ` Add the project on the Source data (project) tab first.`)};
      },
    },
  },
};
const proxyFor = (sheet, col) => (PROXY[sheet] || {})[col];

/** The rows of a child sheet that belong to the selected parent.
 *
 *  A row still being DRAFTED is admitted only while its parent key is empty. The moment
 *  it names a parent it belongs to that parent and to no other. The earlier rule was a
 *  bare `|| r.__new`, added so a new row would be visible before its key was filled in;
 *  because it was unconditional it put a row drafted under one person on EVERY other
 *  person's tab - and on the overrides table, where the project and role columns are
 *  looked up from the assignment, that row then described someone else's work. */
/* A child table is shown filtered to the parent selected above it. A row that carries
   NO parent key belongs to no parent, so no filter would ever show it - and a row that
   cannot be seen cannot be repaired or deleted, only silently dropped on the next round
   trip. It is shown wherever the user is instead, which is the only place they can act
   on it. (Drafts are the common case: a row seeded with its parent covers most of them,
   this covers the rest, and a keyless row that reached the file covers the last.) */
const childrenOf = (rows, col, val) =>
  rows.filter(r => r[col] === val || !r[col]);

/** Sheets whose key is allocated for the user when a row is inserted. An assignment_id
 *  carries no meaning beyond being unique, so making someone invent one is asking them
 *  to do the machine's job - and to do it wrong, since the row is rejected at Save if
 *  the number collides with one already in the file. */
/* Every column of a sheet the user may type into: the schema's own order, minus the
   derived ones. The project and people tables used to show a curated subset, which reads
   more calmly - and means five Project columns have no home anywhere in the application.
   That was survivable while every plan arrived as a workbook someone had filled in
   elsewhere. It is not survivable now that a plan can be BUILT here: a field with no home
   is a field that can never be entered, and V-10 would warn about it forever. */
const entryCols = sheet =>
  SHEET_HEADERS[sheet].filter(c => !(DERIVED_COLS[sheet] || []).includes(c));

const AUTO_KEY = new Set(["Project","Person","Assignment"]);
// Where to start when the sheet is empty and there is no house style to copy - which is
// every sheet, in a plan started blank.
const FIRST_KEY = {Project:["PRJ-", 3], Person:["PSN-", 3], Assignment:["ASG-", 3]};

/** The next identifier in the pattern the sheet already uses: the LARGEST number in it,
 *  plus one.
 *
 *  It used to allocate the smallest UNUSED number, so that a file whose ids ran 1..46 and
 *  then jumped to 901 for a handful of hand-placed rows would not start climbing from
 *  902. That reasoning was about tidiness; running one past the end is about being able
 *  to tell at a glance which rows you added today, and it is what was asked for. A gap
 *  left by a deleted row now stays a gap, which is the ordinary behaviour of an
 *  identifier sequence anywhere else. */
function nextKey(sheet, col){
  if (!col) return null;
  const used = new Set();
  let prefix = null, width = 3;
  for (const r of (S.model.raw[sheet] || [])){
    const v = r[col];
    if (v === null || v === undefined || String(v).trim() === "") continue;
    const m = /^(.*?)(\d+)$/.exec(String(v).trim());
    if (!m) continue;
    if (prefix === null){ prefix = m[1]; width = m[2].length; }
    if (m[1] === prefix) used.add(+m[2]);
  }
  if (prefix === null){
    // Nothing to follow. In a loaded workbook that means the sheet is empty and the
    // house style is unknown, so the user names the row. But in a plan started blank
    // EVERY sheet starts empty, and the first assignment would then be the one row the
    // application refuses to name - having named every one after it. So the sheets that
    // allocate their own keys carry a pattern to start from.
    const p = FIRST_KEY[sheet];
    return p ? p[0] + String(1).padStart(p[1], "0") : null;
  }
  const n = Math.max(0, ...used) + 1;
  // A sequence that has outgrown its width keeps counting rather than truncating.
  return prefix + String(n).padStart(width, "0");
}

/* What a new row starts with, beyond its identifier and its parent key.
 *
 *  Two kinds of value, for two reasons.
 *
 *  A SEQUENCE continues its parent's own numbering, so the row lands at the end of the
 *  list it belongs to rather than at position "blank", which sorts first.
 *
 *  A WEIGHT starts at 1.00, because 1.00 is the neutral multiplier: a period nobody has
 *  weighted yet must not silently scale the load up or down, a person is available for
 *  one full FTE until told otherwise, and someone put on a project is on it fully until
 *  someone says what share. Starting them empty means starting them at ZERO, since an
 *  empty weight reads as 0.00 in the calculation - a row that quietly contributes
 *  nothing is worse than one that contributes too much, because nothing draws the eye. */
const NEW_ROW = {
  Milestone:          {milestone_seq: () => nextSeq("Milestone", "milestone_seq",
                                                    "project_id", S.selProj)},
  // ProjectPeriod has no period_id: the sheet is keyed on (project_id, period_name) and
  // period_seq is what carries the ORDER. So that is the number allocated here, one past
  // the highest in this project, exactly as milestone_seq is.
  ProjectPeriod:      {period_seq: () => nextSeq("ProjectPeriod", "period_seq",
                                                 "project_id", S.selProj),
                       weight: 1.00},
  Person:             {capacity_fte: 1.00},
  Assignment:         {person_weight: 1.00},
  PersonPeriodWeight: {weight_override: 1.00},
};

/** One past the highest sequence number among a parent's own children. */
function nextSeq(sheet, col, parentCol, parentVal){
  let max = 0;
  for (const r of (S.model.raw[sheet] || [])){
    if (parentCol && parentVal !== null && parentVal !== undefined
        && r[parentCol] !== parentVal) continue;
    const n = num(r[col]);
    if (n !== null && n !== undefined && isFinite(n)) max = Math.max(max, n);
  }
  return max + 1;
}

/** The columns a new row is given without the user typing anything: its identifier, its
 *  parent key, and the defaults above. A row carrying ONLY those is still an empty row -
 *  the application filled it in, not the user - so it stays out of validation and out of
 *  the export until something else is entered. */
function autoFilled(sheet){
  const out = new Set(Object.keys(NEW_ROW[sheet] || {}));
  if (KEY_COL[sheet]) out.add(KEY_COL[sheet]);
  const p = PARENT_OF[sheet];
  if (p) out.add(p()[0]);
  return out;
}
function isSkeleton(sheet, r){
  const auto = autoFilled(sheet);
  return (S.headers[sheet] || []).every(h => {
    if (auto.has(h)) return true;
    const v = r[h];
    return v === null || v === undefined || String(v).trim() === "";
  });
}

function suggestionsFor(sheet, col, row){
  const M = S.model;
  const px = proxyFor(sheet, col);
  if (px) return px.options();
  const named = LIST_FOR[col];
  if (named && M.lists[named]) return M.lists[named].map(String);
  // period_name and role_name depend on the project's TYPE, so the valid set is not one
  // list but two. Narrow it by the row's own project where that is knowable.
  if (col === "period_name" || col === "role_name"){
    const pid = row && (row.project_id ||
      (row.assignment_id && (M.assignments.find(a => a.assignment_id === row.assignment_id) || {}).project_id));
    const ty = pid && (M.projects[pid] || {}).project_type;
    const kind = col === "period_name" ? "period_name" : "role";
    if (ty) return (M.lists[`${kind}_${CLINICAL_TYPES.has(ty) ? "clinical" : "others"}`] || []).map(String);
    return [...(M.lists[`${kind}_clinical`] || []), ...(M.lists[`${kind}_others`] || [])].map(String);
  }
  if (SHEET_COLS[sheet] && (SHEET_COLS[sheet].date.includes(col))) return [];
  const seen = new Set();
  for (const r of (M.raw[sheet] || [])){
    const v = r[col];
    if (v !== null && v !== undefined && !(v instanceof Date) && String(v).trim() !== "")
      seen.add(String(v));
  }
  return seen.size > 1 && seen.size <= 400 ? [...seen].sort() : [];
}

/** One editable table.
 *  `derived` maps a display-only column to a lookup - shown for context, never typed
 *  into, because the master row is the truth and V-13 exists to say so. */
/* Sheets whose ROW SET is fixed by the schema, not by the user.
 *
 *  Config is the only one today. Its nine settings are read BY NAME - a tenth row nobody
 *  reads does nothing, and a missing row silently hands the figure to a built-in default.
 *  So there is nothing to add and nothing that should be removed: what a user changes
 *  here is a VALUE, and the value cell is as editable as any other.
 *
 *  Deleting one of them was the sharp edge. It could not be refused - nothing references
 *  a Config row, so V-17 had no hold on it - and it raised nothing, so a plan whose
 *  under-allocation floor had been moved to 0.80 would revert to 0.60 with every
 *  dependent figure changing and nothing on screen saying why. Removing the control is a
 *  better answer than confirming it: there was never a good reason to press it.
 *
 *  '+ row' goes with it, and for the same reason rather than for symmetry - offering a
 *  way to create a row that can then never be removed would be a worse trap than the one
 *  being closed. V-30 covers the case where a row is missing anyway, from an older file
 *  or a hand-edited one. */
const FIXED_ROWS = new Set(["Config"]);
const FIXED_ROWS_WHY = "These settings are a fixed set — change a value, and it applies "
  + "everywhere. Rows cannot be added or removed: each one is read by name, so a new row "
  + "would do nothing and a missing one would hand the figure to a built-in default.";

function dataTable(sheet, rows, cols, selKey, selVal, derived, lock){
  derived = derived || {};
  const head = `<th class="ins" data-tip="${att(HELP.rowactions)}">Row</th>`
    + cols.map(c => {
        const h = COLUMN_HELP[c], px = proxyFor(sheet, c);
        const d = derived[c] ? " · shown for context, looked up from its master row and not editable"
          : px ? ` · type the name here and ${esc(px.into)} follows. Not stored on this row — `
               + `the master row owns it.` : "";
        return `<th${h || d ? ` class="hasinfo" data-tip="${att(`<b>${esc(c)}</b><br>${(h||"")}${d}`)}"` : ""}>`
          + `${esc(c)}${derived[c] ? ' <span class="drv">lookup</span>'
                       : px ? ' <span class="drv ent">sets ' + esc(px.into) + '</span>' : ""}</th>`;
      }).join("");
  const body = rows.map(r => {
    const sel = (selKey && r[selKey] === selVal) ? ' class="sel"' : "";
    const tds = cols.map(c => {
      if (derived[c]){
        const dv = derived[c](r) ?? "";
        return `<td class="muted drvcell" data-tip="${att(`<b>${esc(c)}</b><br>${esc(dv) || "&mdash;"}`
          + `<br><span class="tr">looked up, not stored on this row</span>`)}">${esc(dv)}</td>`;
      }
      const px = proxyFor(sheet, c);
      if (px){
        const pv = px.show(r) ?? "";
        const marked = S.editedCells.has(`${sheet}|${r.__row}|${px.into}`) ? " edited" : "";
        return `<td class="cell${marked}" contenteditable="true" data-sheet="${att(sheet)}" `
          + `data-row="${r.__row}" data-col="${att(c)}" data-tip="${att(
              `<b>${esc(c)}</b><br>${pv === "" ? "<i>empty</i>" : esc(pv)}`
              + `<br><span class="tr">typing a name here sets ${esc(px.into)}</span>`)}">${esc(pv)}</td>`;
      }
      const v = r[c];
      const disp = v instanceof Date ? ymd(v) : (v === null || v === undefined ? "" : v);
      const marked = S.editedCells.has(`${sheet}|${r.__row}|${c}`) ? " edited" : "";
      const help = COLUMN_HELP[c] ? `<br><span class="tr">${esc(COLUMN_HELP[c])}</span>` : "";
      const tip = `<b>${esc(c)}</b><br>${disp === "" ? "<i>empty</i>" : esc(disp)}${help}`;
      return `<td class="cell${marked}" contenteditable="true" data-sheet="${att(sheet)}" `
        + `data-row="${r.__row}" data-col="${att(c)}" data-tip="${att(tip)}">${esc(disp)}</td>`;
    }).join("");
    return `<tr${sel} data-id="${att(r[selKey] ?? "")}">`
      + (FIXED_ROWS.has(sheet)
          ? `<td class="ins muted" data-tip="${att(HELP.fixedrows)}">&#8212;</td>`
          : `<td class="ins"><button class="btn tiny" data-ins="${att(sheet)}" data-after="${r.__row}"`
            + ` data-tip="${att(HELP.insert)}">+ row</button>`
            + `<button class="btn tiny danger" data-del="${att(sheet)}" data-row="${r.__row}"`
            + ` data-tip="${att(HELP.del)}">Delete</button></td>`)
      + `${tds}</tr>`;
  }).join("");
  // A locked table has a reason instead of a + row: a child row whose parent does not
  // exist yet has nothing to attach to, and would be dropped when the file is read back.
  // Saying so where the button would have been beats offering a button that creates a
  // row nobody can rescue.
  const empty = rows.length ? "" : FIXED_ROWS.has(sheet)
    ? `<tr><td class="ins muted">&#8212;</td>`
      + `<td class="muted" colspan="${cols.length}">${esc(FIXED_ROWS_WHY)}</td></tr>`
    : lock
    ? `<tr><td class="ins muted">—</td>`
      + `<td class="muted" colspan="${cols.length}">${esc(lock)}</td></tr>`
    : `<tr><td class="ins"><button class="btn tiny" data-ins="${att(sheet)}" data-after="0" `
      + `data-tip="${att(HELP.insert)}">+ row</button></td>`
      + `<td class="muted" colspan="${cols.length}">No rows. Use <strong>+ row</strong> to add one.</td></tr>`;
  return `<div class="scrollx tall"><table class="data-t" data-sheet="${att(sheet)}">`
    + `<thead><tr>${head}</tr></thead><tbody>${body}${empty}</tbody></table></div>`;
}

