
/* ============================================================ 13. findings report */

function showBanner(kind, text, findings){
  const n = findings ? findings.length : 0;
  const counts = {};
  if (findings) for (const f of findings) counts[f.sev] = (counts[f.sev] || 0) + 1;
  const summary = n
    ? Object.entries(counts).map(([k,v]) => `${v} ${k}${v===1?"":"s"}`).join(", ")
    : "";
  el("banner").innerHTML =
    `<div class="banner ${kind}"><strong>${esc(text)}</strong>`
    + (n ? ` ${esc(summary)}.<span class="lk" id="openRep">Open full report</span>` : "")
    + `</div>`;
  const b = el("openRep");
  if (b) b.onclick = () => { renderReport(findings); el("report").showModal(); };
}

function renderReport(findings){
  const order = {fatal:0, error:1, warning:2, information:3};
  const rows = findings.slice().sort((a,b) =>
    (order[a.sev]-order[b.sev]) || String(a.sheet).localeCompare(String(b.sheet)) ||
    (a.row||0)-(b.row||0));
  el("repBody").innerHTML = rows.length
    ? `<table class="data-t"><thead><tr><th>severity</th><th>rule</th><th>sheet</th><th>row</th>
        <th>finding</th></tr></thead><tbody>${rows.map(f =>
        `<tr><td><span class="sev ${f.sev}">${f.sev}</span></td><td>${esc(f.rule)}</td>`
        + `<td>${esc(f.sheet)}</td><td>${f.row || ""}</td>`
        + `<td style="white-space:normal">${esc(f.msg)}</td></tr>`).join("")}</tbody></table>`
    : `<p class="cap">Nothing to report — the workbook passed every rule.</p>`;
}

/* The name a sheet goes by on screen. The pending list records the SHEET a change
   landed on, which is the right key to keep, but "PersonPeriodWeight" is not what the
   panel over that table is called - and the whole point of the log is being able to walk
   back to the thing you changed. */
const SECTION = {
  Project:"Projects", Milestone:"Milestones", ProjectPeriod:"Periods",
  Person:"People", Assignment:"Assignments", PersonPeriodWeight:"Weight overrides",
  PeriodWeightStandard:"Standard period weights", RoleFactor:"Role factors",
  Lists:"Value lists", Config:"Configuration",
  "(cascade)":"Carried through automatically",
};
const TAB_OF = {
  Project:"Source data (project)", Milestone:"Source data (project)",
  ProjectPeriod:"Source data (project)", Person:"Source data (person)",
  Assignment:"Source data (person)", PersonPeriodWeight:"Source data (person)",
  PeriodWeightStandard:"General assumptions", RoleFactor:"General assumptions",
  Lists:"General assumptions", Config:"General assumptions",
};

/** Every change waiting to be saved, newest first.
 *
 *  Newest first because the question this answers is almost always "what did I just do" -
 *  the edit you are unsure about is the one you made a moment ago, not the one from ten
 *  minutes back. The first row is tinted for the same reason.
 */
function renderChanges(){
  const rows = S.pending.slice().reverse();
  const val = v => {
    if (v === null || v === undefined || v === "") return `<span class="empty">(empty)</span>`;
    if (v instanceof Date) return esc(ymd(v));
    return esc(v);
  };
  const when = d => d instanceof Date
    ? `${String(d.getHours()).padStart(2,"0")}:${String(d.getMinutes()).padStart(2,"0")}`
      + `:${String(d.getSeconds()).padStart(2,"0")}`
    : "";
  el("chgTitle").textContent = `Unsaved changes — ${S.pending.length}`;
  el("chgBody").innerHTML = rows.length
    ? `<p class="cap">Newest first. Nothing here has reached the file: <strong>Save</strong>
        keeps them in the working data, <strong>Leave without change</strong> puts every one
        of them back, and neither writes to disk until you press Export.</p>
       <div class="scrollx"><table class="data-t chg">
        <thead><tr><th>time</th><th>tab</th><th>section</th><th>row</th><th>item</th>
          <th>before</th><th>after</th></tr></thead>
        <tbody>${rows.map(c =>
        `<tr><td class="when">${when(c.at)}</td>`
        + `<td>${esc(TAB_OF[c.sheet] || "")}</td>`
        + `<td>${esc(SECTION[c.sheet] || c.sheet)}</td>`
        + `<td class="num">${c.row === "" || c.row === undefined ? "" : c.row}</td>`
        + `<td><code>${esc(c.col)}</code></td>`
        + `<td class="was">${val(c.from)}</td>`
        + `<td class="now">${val(c.to)}</td></tr>`).join("")}</tbody></table></div>`
    : `<p class="cap">Nothing is waiting to be saved.</p>`;
  cueScrollers();
}

/* --------------------------------------------- the two generators on the project tab
   Both produce ORDINARY ROWS. Nothing here is locked, computed on the fly or special in
   any way afterwards: the point is to save the typing, not to take the decision away.
   Both are provisional like every other edit, so 'Leave without change' undoes them. */

/** A blank row for `sheet`, with its parent key already on it. */
function newRow(sheet, seed){
  const rows = S.model.raw[sheet];
  const r = {__row: rows.reduce((n, x) => Math.max(n, x.__row), 0) + 1, __new:true};
  for (const h of (S.headers[sheet] || [])) r[h] = null;
  Object.assign(r, seed);
  rows.push(r);
  return r;
}

/** The standard milestone names, laid out with their dates empty. */
function blankMilestones(pid){
  const M = S.model;
  const names = M.lists.milestone_name || [];
  if (!names.length){
    showBanner("bad", "The Lists sheet carries no milestone_name values, so there is no "
      + "standard list to lay out. Add them on General assumptions.");
    return;
  }
  // Names already there are not repeated - the button is for filling the gaps, and a
  // second 'CTA submission' would be a duplicate the file has a rule against (V-20).
  const have = new Set(M.raw.Milestone.filter(m => m.project_id === pid)
    .map(m => m.milestone_name));
  const add = names.filter(n => !have.has(n));
  if (!add.length){
    showBanner("", `Every standard milestone is already listed for ${pid}. Nothing added.`);
    return;
  }
  beginEditSession();
  let seq = nextSeq("Milestone", "milestone_seq", "project_id", pid);
  for (const n of add){
    const r = newRow("Milestone", {project_id:pid, milestone_name:n, milestone_seq:seq++});
    S.pending.push({at:new Date(), sheet:"Milestone", row:r.__row, col:"(new row)",
                    from:null, to:n});
  }
  renderKeepingTab();
  showBanner("", `Added ${add.length} standard milestone${add.length===1?"":"s"} to ${pid}, `
    + `with the dates blank. Fill in the dates that apply and delete the rows that do not — `
    + `a milestone with no date is ignored by the calculation either way.`);
}

/** This project's periods, built from its milestones by the rule in the plan. */
function autoPeriods(pid){
  const M = S.model, pr = M.projects[pid];
  if (!pr){
    showBanner("bad", `${pid} has not been saved yet. Save the project first — the `
      + `derivation reads its start and end dates.`);
    return;
  }
  if (!CLINICAL_TYPES.has(pr.project_type)){
    showBanner("bad", `${pid} is a '${pr.project_type}' project. The derivation is defined `
      + `for clinical trials only, because it hangs on CTA submission and the DB locks. `
      + `Enter Planning / Develop / Close by hand, with no gap and no overlap.`);
    return;
  }
  // From RAW, so a set of milestones just typed and not yet saved still counts - which is
  // the ordinary case, since the two buttons are meant to be used one after the other.
  const ms = {};
  for (const m of M.raw.Milestone)
    if (m.project_id === pid && m.milestone_name && m.milestone_date instanceof Date)
      (ms[m.milestone_name] ||= []).push(m.milestone_date);
  for (const k of Object.keys(ms)) ms[k].sort((a, b) => a - b);

  const segs = derivePeriods(pr, ms);
  if (!segs){
    showBanner("bad", `Cannot derive periods for ${pid}: the rule needs a 'CTA submission' `
      + `date and at least one DB lock (V-16). Add those milestones above, then try again.`);
    return;
  }
  const existing = M.raw.ProjectPeriod.filter(r => r.project_id === pid);
  if (existing.length && !confirm(
      `${pid} already has ${existing.length} period row(s).\n\n`
      + `Replace them with the ${segs.length} derived from its milestones?\n`
      + `This is provisional — 'Leave without change' puts them back.`)) return;

  beginEditSession();
  for (const r of existing){
    M.raw.ProjectPeriod.splice(M.raw.ProjectPeriod.indexOf(r), 1);
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(deleted row)",
                    from:r.period_name, to:null});
  }
  for (const d of segs){
    const r = newRow("ProjectPeriod", {
      project_id:pid, period_name:d.period_name, period_seq:d.period_seq,
      period_start:d.period_start, period_end:d.period_end,
      weight: M.pws[[pr.project_type, pr.clinical_phase, d.period_name]] ?? 1.00});
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(new row)",
                    from:null, to:`${d.period_name} ${ymd(d.period_start)}..${ymd(d.period_end)}`});
  }
  renderKeepingTab();
  const w = M.pws[[pr.project_type, pr.clinical_phase, segs[0].period_name]] === undefined
    ? " No standard weights exist for this type and phase, so every period is at 1.00 —"
      + " set them on General assumptions."
    : ` Each period carries the standard weight for ${pr.project_type} / ${pr.clinical_phase}.`;
  showBanner("", `Derived ${segs.length} periods for ${pid} from its milestones.${w} `
    + `They are ordinary rows — edit any of them, then Save.`);
}

