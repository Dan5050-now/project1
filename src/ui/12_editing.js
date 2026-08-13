/* ============================================================ 12. editing + IO */

/* An edit is provisional until confirmed. The change is applied to the model straight
   away - the numbers on screen must never disagree with the data on screen - but a
   snapshot taken before the FIRST pending edit lets 'Leave without change' put it all
   back. Nothing provisional can reach an export. */
function snapshotRaw(){
  const snap = {};
  for (const s of REQUIRED_SHEETS) snap[s] = S.model.raw[s].map(r => ({...r}));
  return snap;
}
function beginEditSession(){
  if (!S.snapshot) S.snapshot = snapshotRaw();
}
/** A row still being created is held out of validation - it is INCOMPLETE, not invalid,
 *  and reporting "project_id is empty" at every keystroke would be noise. Save is where
 *  that grace ends: a draft that now has content is promoted to an ordinary row and
 *  checked like one, and if that turns up an error the save is refused rather than
 *  quietly keeping a bad record. */
/* Errors that say "something which is NOT on this row is missing yet".
   A clinical trial saved before its milestones exist raises both of these by definition
   - and its milestones cannot be entered until it is saved, because the milestone table
   hangs off a SELECTED project. Refusing the save there is a deadlock: the row cannot be
   kept until its children exist, and its children cannot be created until it is kept.
   The specification already draws this line for drafts - a row still being built is
   INCOMPLETE, not invalid - so these stay in the findings report and are named in the
   banner; they simply do not refuse the save. Every other error still does, because
   every other error is something wrong with the row in front of you. */
const INCOMPLETE_RULES = new Set(["V-12","V-16"]);
const blocking = f => (f.sev === "error" || f.sev === "fatal") && !INCOMPLETE_RULES.has(f.rule);

/* What Save recalculates from the rows beneath a project.
 *
 *  A project's WINDOW is the span its milestones describe, and its PLANNED TEAM SIZE is
 *  the number of distinct people assigned to it. Both were typed by hand and could drift
 *  from the rows that actually say what they are.
 *
 *  Done at Save rather than at load, deliberately. Doing it on load would rewrite dates in
 *  a workbook somebody produced elsewhere, the moment they opened it, without their having
 *  asked for anything - and the delivered examples set a project start before its first
 *  milestone quite legitimately. At Save it is a consequence of an edit the user just
 *  made, and the banner names every value it changed.
 *
 *  Two guards, both about not destroying information:
 *    - a project with NO milestone dates keeps the window that was typed, because there
 *      is nothing to derive it from;
 *    - a project with NO assignments keeps the team size that was typed, because "nobody
 *      is assigned yet" is not the same statement as "this needs nobody".
 */
function deriveFromChildren(){
  const M = S.model, changed = [], undo = [];
  const set = (row, col, v, label) => {
    undo.push([row, col, row[col]]);
    row[col] = v;
    changed.push(label);
  };
  for (const p of M.raw.Project){
    const pid = p.project_id;
    if (!pid) continue;
    const dates = M.raw.Milestone
      .filter(m => m.project_id === pid && m.milestone_date instanceof Date)
      .map(m => m.milestone_date.getTime());
    if (dates.length){
      const lo = new Date(Math.min(...dates)), hi = new Date(Math.max(...dates));
      if (!(p.start_date instanceof Date) || +p.start_date !== +lo)
        set(p, "start_date", lo, `${pid} start ${ymd(lo)}`);
      if (!(p.end_date instanceof Date) || +p.end_date !== +hi)
        set(p, "end_date", hi, `${pid} end ${ymd(hi)}`);
    }
    const team = new Set(M.raw.Assignment
      .filter(a => a.project_id === pid && a.person_id).map(a => a.person_id));
    if (team.size && num(p.planned_member_count) !== team.size)
      set(p, "planned_member_count", team.size, `${pid} team ${team.size}`);
  }
  return {changed, undo};
}

function saveEdits(){
  if (!S.pending.length) return;
  // Before the check, so that what is validated is what will be kept; put back with the
  // drafts if the save is refused.
  const derived = deriveFromChildren();
  const drafts = [];
  for (const s of REQUIRED_SHEETS)
    // isSkeleton, not isBlankRow: an inserted row now arrives with an identifier and a
    // neutral weight already in it, so "blank" would never be true again and a row the
    // user has not touched would be promoted and then reported for what it is missing.
    for (const r of S.model.raw[s]) if (r.__new && !isSkeleton(s, r)) drafts.push(r);
  let pending = [];
  if (drafts.length){
    for (const r of drafts) delete r.__new;
    const probe = rebuild();
    const errs = probe.findings.filter(blocking);
    const was = (S.model.findings || []).filter(blocking);
    if (errs.length > was.length){
      for (const r of drafts) r.__new = true;
      for (const [row, col, was_] of derived.undo) row[col] = was_;    // and the derivation
      showBanner("bad", `Save refused — the new row${drafts.length===1?"" :"s"} would break a rule: `
        + `${errs[errs.length-1].msg} Correct it, or delete the row, then save.`);
      return;
    }
    pending = probe.findings.filter(f => INCOMPLETE_RULES.has(f.rule)
      && !(S.model.findings || []).some(g => g.rule === f.rule && g.msg === f.msg));
    rebuild(true);
    renderKeepingTab();
  } else if (derived.changed.length){
    rebuild(true);
    renderKeepingTab();
  }
  S.saved += S.pending.length;
  S.pending = [];
  S.snapshot = null;
  renderDirty();
  showBanner("", `Saved ${S.saved} change${S.saved===1?"":"s"} to the working data. `
    + (derived.changed.length
        ? `Recalculated from the rows beneath: ${derived.changed.slice(0, 6).join(", ")}`
          + `${derived.changed.length > 6 ? ` and ${derived.changed.length - 6} more` : ""}. `
        : "")
    + (pending.length
        ? `Still to come: ${pending[0].msg} `
        : "")
    + `They will be written to the file when you press Export. The file on disk is `
    + `still untouched until then.`);
}
function discardEdits(){
  if (!S.pending.length) return;
  const n = S.pending.length;
  for (const s of REQUIRED_SHEETS) S.model.raw[s] = S.snapshot[s].map(r => ({...r}));
  S.snapshot = null;
  S.pending = [];
  S.editedCells.clear();
  rebuild(true);
  renderKeepingTab();
  showBanner("", `${n} change${n===1?" was":"s were"} discarded. The data is back to how it was `
    + `${S.saved ? "after your last save" : "when the workbook was loaded"}.`);
}

function renderDirty(){
  const n = S.pending.length, bar = el("editbar");
  bar.hidden = !S.model;
  bar.classList.toggle("dirty", n > 0);
  el("saveBtn").disabled = el("discardBtn").disabled = el("chgBtn").disabled = (n === 0);
  if (!n && el("changes").open) el("changes").close();   // nothing left to show
  el("editstate").textContent = n
    ? `${n} unsaved change${n===1?"":"s"}`
    : (S.saved ? `${S.saved} saved change${S.saved===1?"":"s"} · nothing pending`
               : "no changes");
  el("guide").innerHTML = n
    ? `<strong>${n} change${n===1?"":"s"} not yet saved.</strong> They are applied on screen so you can
       see their effect, but they are <em>not final</em>. All ${n} pass validation — an edit that fails a
       rule is rejected at entry, so nothing invalid can be saved. <strong>Export is held</strong> until
       you choose.`
    : `<strong>Changes are temporary.</strong> Edits are applied on screen so you can see their effect,
       but they are <em>not final</em> until you choose. Click <strong>Save</strong> to keep them — only
       saved changes go into the exported file.`;
}

/** Apply one cell edit: coerce, validate, write to the model, recalculate. */
function applyEdit(sheet, rowNum, col, raw, tdEl){
  const M = S.model;
  const target = M.raw[sheet].find(r => r.__row === rowNum);
  if (!target) return;

  // A proxy column is resolved to the identifier it names, and the identifier is what
  // is written. Everything after this point sees an ordinary edit to an ordinary column.
  const px = proxyFor(sheet, col);
  if (px){
    if (raw.trim() === ""){ col = px.into; raw = ""; }
    else {
      const got = px.resolve(raw);
      if (got.error){ flashBad(tdEl, got.error); return; }
      if (got.value === target[px.into]){ tdEl.textContent = px.show(target) ?? ""; return; }
      col = px.into; raw = String(got.value);
    }
  }

  const spec = SHEET_COLS[sheet];
  let v = raw.trim() === "" ? null : raw.trim();
  if (v !== null && spec.date.includes(col)){
    const d = parseDate(v);
    if (d === undefined){ flashBad(tdEl, `'${raw}' is not a date. Use yyyy-mm-dd.`); return; }
    v = d;
  } else if (v !== null && spec.num.includes(col)){
    const n = num(v);
    if (n === undefined){ flashBad(tdEl, `'${raw}' is not a number.`); return; }
    v = n;
  }
  const before = target[col];
  beginEditSession();

  // REQ-IMP-10: changing an identifier that other sheets reference cascades to every
  // referencing row, after saying how many will change. Blocking the edit instead would
  // make the field read-only in all but name.
  //
  // Only on the sheet that OWNS the identifier. KEY_COL names the key column of every
  // sheet, but on a CHILD sheet that column is a FOREIGN key: PersonPeriodWeight
  // .assignment_id points at an assignment, it does not define one. Editing it re-points
  // this one row, and cascading would drag every other row that happens to share the old
  // value along with it - which on the overrides table means the sibling windows of the
  // assignment you just moved away from. OWNER is the same map deleteRow already uses
  // for the same reason.
  if (KEY_COL[sheet] === col && OWNER[col] === sheet && REFS[col]
      && before !== null && v !== null && v !== before){
    const hits = [];
    for (const [s2, c2] of REFS[col])
      for (const r of M.raw[s2]) if (r[c2] === before) hits.push([r, c2]);
    if (hits.length && !confirm(
        `${before} is referenced by ${hits.length} row(s) across `
        + `${[...new Set(REFS[col].map(x => x[0]))].join(", ")}.\n\n`
        + `Change it to ${v} and update them all?`)){
      tdEl.textContent = String(before);
      return;
    }
    for (const [r, c2] of hits) r[c2] = v;               // one atomic step
    if (hits.length) S.pending.push({at:new Date(), sheet:"(cascade)", row:"", col,
                                     from:before, to:v, n:hits.length});
  }
  target[col] = v;

  // Re-validate the whole model with the same rules as an import (REQ-IMP-09). An edit
  // that introduces an ERROR is rejected outright rather than left to surface later.
  const probe = rebuild();
  const newErrors = probe.findings.filter(f => f.sev === "error" || f.sev === "fatal");
  const oldErrors = (S.model.findings || []).filter(f => f.sev === "error" || f.sev === "fatal");
  if (newErrors.length > oldErrors.length){
    target[col] = before;
    rebuild(true);
    flashBad(tdEl, newErrors[newErrors.length - 1].msg);
    return;
  }
  S.pending.push({at:new Date(), sheet, row:rowNum, col, from:before, to:v});
  S.editedCells.add(`${sheet}|${rowNum}|${col}`);
  tdEl.classList.add("edited");
  rebuild(true);
  renderKeepingTab();

  // Pointing a child row at a parent that already has children is the normal way to add
  // a second override window, not a mistake - so this says what the row now sits beside
  // rather than asking anything. The rules that DO constrain it are V-06 and V-24, and
  // they are checked when the row is complete, so name them here while there is still
  // something to do about it.
  if (KEY_COL[sheet] === col && OWNER[col] && OWNER[col] !== sheet && v !== null && v !== before){
    const sibs = M.raw[sheet].filter(r => r[col] === v && r.__row !== rowNum).length;
    if (sibs) showBanner("", `${v} now carries ${sibs + 1} rows in ${sheet}`
      + (sheet === "PersonPeriodWeight"
          ? ` — that is allowed, and is how one assignment carries several windows. They must not
              overlap and no two may start on the same date (V-06, V-24); both are checked when you
              press Save.`
          : `. The other ${sibs} ${sibs === 1 ? "is" : "are"} untouched.`));
  }
}

function flashBad(tdEl, msg){
  const prev = tdEl.dataset.orig ?? "";
  tdEl.textContent = prev;
  showBanner("bad", `Edit rejected — ${msg}`);
}

/** True when the parser would discard this row: every mapped column empty. */
function isBlankRow(sheet, r){
  return (S.headers[sheet] || []).every(h => {
    const v = r[h];
    return v === null || v === undefined || String(v).trim() === "";
  });
}

/** Rebuild model+calc from the current raw rows. `commit` writes it back to state.
 *
 *  Two things make this more than a re-parse.
 *
 *  The parser SKIPS blank rows - right for an imported file, where a blank line is not a
 *  record, and wrong for a row the user just created and has not filled in yet. Such a
 *  row is held out of the parse and put back at its own position afterwards, so an edit
 *  or a delete elsewhere cannot destroy it.
 *
 *  The parser also NUMBERS rows by position (__row = spreadsheet line). Deleting a row
 *  shifts every row below it, so re-parsing would hand those rows new identities while
 *  S.pending, S.editedCells and the rendered cells still name the old ones. Identity is
 *  therefore restored from the rows that were fed in, position by position - which is
 *  exact, because exactly the non-held rows were emitted, in order. */
function rebuild(commit){
  const kept = {}, held = {}, sheets = {};
  for (const s of REQUIRED_SHEETS){
    const rows = S.model.raw[s] || [];
    kept[s] = []; held[s] = [];
    rows.forEach((r, i) => {
      if (r.__new || isBlankRow(s, r)) held[s].push([i, r]); else kept[s].push(r);
    });
    sheets[s] = rawToRows(s, kept[s]);
  }
  const m = buildModel(sheets);
  for (const s of REQUIRED_SHEETS){
    m.raw[s].forEach((r, i) => { if (kept[s][i]) r.__row = kept[s][i].__row; });
    for (const [i, r] of held[s]) m.raw[s].splice(i, 0, r);
  }
  if (commit){ S.model = m; S.calc = calculate(m); }
  return m;
}

/** Model rows -> the row-array shape readWorkbook produces, so rebuild and export share
 *  one path. Export passes nothing and gets every row; rebuild passes the rows it wants
 *  the parser to see. */
function rawToRows(sheet, rows){
  const hdr = S.headers[sheet] || [];
  const out = [hdr.slice()];
  for (const r of (rows || S.model.raw[sheet])) out.push(hdr.map(h => r[h] ?? null));
  return out;
}

/** V-17: a row that is still referenced cannot be deleted, and a delete NEVER cascades.
 *  Losing fourteen assignments to one keystroke is unrecoverable in a way that a
 *  cascaded rename is not - which is why editing an identifier cascades and this does
 *  the opposite. The deletion itself is provisional like any other change. */
function deleteRow(sheet, rowNum){
  const M = S.model;
  const rows = M.raw[sheet];
  const i = rows.findIndex(r => r.__row === rowNum);
  if (i < 0) return;
  const r = rows[i];
  const key = KEY_COL[sheet], val = r[key];

  if (OWNER[key] === sheet && val && REFS[key]){
    const by = {};
    for (const [s2, c2] of REFS[key]){
      const n = M.raw[s2].filter(x => x[c2] === val).length;
      if (n) by[s2] = n;
    }
    const total = Object.values(by).reduce((a, b) => a + b, 0);
    if (total){
      showBanner("bad", `${val} cannot be deleted — ${total} row(s) still refer to it: `
        + `${Object.entries(by).map(([s2, n]) => `${n} in ${s2}`).join(", ")}. `
        + `Delete or re-point those first. A delete is never cascaded, because losing them to `
        + `one keystroke could not be undone.`);
      return;
    }
  }

  beginEditSession();
  rows.splice(i, 1);
  for (const k of [...S.editedCells]) if (k.startsWith(`${sheet}|${rowNum}|`)) S.editedCells.delete(k);
  S.pending.push({at:new Date(), sheet, row:rowNum, col:"(deleted row)",
                  from:val ?? "(blank row)", to:null});
  rebuild(true);
  renderKeepingTab();
  showBanner("", `Deleted ${val ? `${val} from ${sheet}` : `a blank row from ${sheet}`}. `
    + `This is provisional — 'Leave without change' puts it back.`);
}
