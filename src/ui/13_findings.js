
/* ============================================================ 13. findings report */

function showBanner(kind, text, findings){
  const n = findings ? findings.length : 0;
  const counts = {};
  if (findings) for (const f of findings) counts[f.sev] = (counts[f.sev] || 0) + 1;
  // 'information' is uncountable - "3 informations" is not English, and this string is
  // read every time a file is opened.
  const plural = (k, v) => v === 1 || k === "information" ? k : k + "s";
  const summary = n
    ? Object.entries(counts).map(([k,v]) => `${v} ${plural(k, v)}`).join(", ")
    : "";
  const cfgN = (S.cfgChanges || []).length;
  el("banner").innerHTML =
    `<div class="banner ${kind}"><strong>${esc(text)}</strong>`
    + (n ? ` ${esc(summary)}.` : "")
    + (cfgN ? `<span class="lk" id="openCfg">Which settings changed</span>` : "")
    + (n ? `<span class="lk" id="openRep">Open full report</span>` : "")
    + `</div>`;
  const b = el("openRep");
  if (b) b.onclick = () => { renderReport(findings); el("report").showModal(); };
  const c = el("openCfg");
  if (c) c.onclick = () => { renderCfgChanges(); el("cfgchg").showModal(); };
}

/** The settings this import brought with it, and what each one does.
 *
 *  Its own screen rather than a sheet in the full difference report, because it answers
 *  a different question. The difference report asks "what is in this file that is not in
 *  my plan" - rows of work, which is what an import is FOR. This asks "what will now be
 *  read differently", which is a question about every figure on the page at once, and it
 *  has to be answerable without hunting for the Config sheet among ten others. */
function renderCfgChanges(){
  const rows = S.cfgChanges || [];
  const WORD = {changed:"changed", added:"added by this file",
                removed:"not in this file"};
  el("cfgBody").innerHTML =
    `<p class="cap">Importing a workbook takes its settings as well as its rows — that is
      deliberate, and it is what makes a plan reproducible from the file alone. Nothing
      here was refused. It is listed because these are the figures the whole page is read
      against, and a change to one of them moves numbers that are nowhere near this
      table.</p>`
    + `<table class="data-t"><thead><tr><th>setting</th><th></th><th>was</th><th>now</th>
        <th>what it affects</th></tr></thead><tbody>${rows.map(c =>
        `<tr><td><code>${esc(c.parameter)}</code></td>`
        + `<td><span class="cls ${c.kind === "changed" ? "conditional" : "incomplete"}">`
        + `${esc(WORD[c.kind])}</span></td>`
        + `<td>${esc(diffShown(c.from))}</td><td><strong>${esc(diffShown(c.to))}</strong></td>`
        + `<td style="white-space:normal">${esc(c.effect)}</td></tr>`).join("")}</tbody></table>`
    + (rows.some(c => c.kind === "removed")
        ? `<p class="cap"><strong>Not in this file</strong> means the setting has no row in
           the workbook you just loaded, so the application's own built-in default is now
           in force — V-30 in the findings report names it.</p>`
        : "");
}

const CLS_LABEL = {must:"must fix", conditional:"may keep", incomplete:"still to come"};

function renderReport(findings){
  const order = {fatal:0, error:1, warning:2, information:3};
  const rows = findings.slice().sort((a,b) =>
    (order[a.sev]-order[b.sev]) || String(a.sheet).localeCompare(String(b.sheet)) ||
    (a.row||0)-(b.row||0));
  /* SEVERITY says how wrong it is; CLASS says what the application will do about it,
     and the second is what a reader actually wants from this table - "will this stop me
     saving, or not". Only errors carry one: a warning or a note never refused anything,
     so labelling them would suggest a choice that was never there. */
  const cls = f => (f.sev === "error" || f.sev === "fatal") ? ruleClass(f.rule) : "";
  el("repBody").innerHTML = rows.length
    ? `<table class="data-t"><thead><tr><th>severity</th><th>refuses?</th><th>rule</th>
        <th>sheet</th><th>row</th><th>finding</th></tr></thead><tbody>${rows.map(f =>
        `<tr><td><span class="sev ${f.sev}">${f.sev}</span></td>`
        + `<td>${cls(f) ? `<span class="cls ${cls(f)}">${CLS_LABEL[cls(f)]}</span>`
              : ""}</td>`
        + `<td>${esc(f.rule)}</td>`
        + `<td>${esc(f.sheet)}</td><td>${f.row || ""}</td>`
        + `<td style="white-space:normal">${esc(f.msg)}</td></tr>`).join("")}</tbody></table>`
      + `<p class="cap"><strong>must fix</strong> — something is wrong with the row
         itself, and it is refused until you correct it. <strong>may keep</strong> — the
         row is sound but something it depends on is missing, so the figures that need it
         are short an assumption; Save asks before keeping these, and going ahead is your
         decision. <strong>still to come</strong> — the row is not finished yet and this
         will answer itself as you carry on entering; nothing is refused and nothing is
         asked.</p>`
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

/** The standard period names for a project the derivation does not reach, laid out with
 *  their dates blank - the same idea as 'Blank list' on the milestones.
 *
 *  An 'Others' project has no milestone rule to hang a derivation on, so its periods are
 *  entered by hand. That does not mean starting from an empty table: the three names are
 *  standing vocabulary on the Lists sheet, and typing them out again on every project is
 *  transcription, not judgement. What the user actually has to decide is the dates. */
function blankPeriods(pid){
  const M = S.model, pr = M.projects[pid];
  const names = M.lists.period_name_others || OTHER_PERIODS;
  const have = new Set(M.raw.ProjectPeriod.filter(r => r.project_id === pid)
    .map(r => r.period_name));
  const add = names.filter(n => !have.has(n));
  if (!add.length){
    showBanner("", `Every standard period is already listed for ${pid}. Nothing added.`);
    return;
  }
  beginEditSession();
  let seq = nextSeq("ProjectPeriod", "period_seq", "project_id", pid);
  for (const n of add){
    const r = newRow("ProjectPeriod", {project_id:pid, period_name:n, period_seq:seq++,
                                       weight:1.00});
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(new row)",
                    from:null, to:n});
  }
  renderKeepingTab();
  showBanner("", `Added ${add.length} standard period${add.length===1?"":"s"} to ${pid} at `
    + `weight 1.00, with the dates blank. Fill in the dates — they must run one after `
    + `another with no gap, because a month in no period is calculated at weight 1.00 `
    + `(V-12), and the project's own window is the span they cover (REQ-CAL-17).`);
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
      // Through stdWeight, not straight at M.pws: schema 6 put the work scope in the
      // key, and a lookup that leaves it out matches nothing and quietly derives every
      // period at 1.00 - which is what happened, and what the suite caught.
      weight: stdWeight(M, pr, d.period_name) ?? 1.00});
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(new row)",
                    from:null, to:`${d.period_name} ${ymd(d.period_start)}..${ymd(d.period_end)}`});
  }
  renderKeepingTab();
  const scope = pr.work_scope_type ? ` / ${pr.work_scope_type}` : "";
  const w = stdWeight(M, pr, segs[0].period_name) === undefined
    ? " No standard weights exist for this type, phase and scope, so every period is at"
      + " 1.00 — set them on General assumptions."
    : ` Each period carries the standard weight for ${pr.project_type} / `
      + `${pr.clinical_phase}${scope}.`;
  showBanner("", `Derived ${segs.length} periods for ${pid} from its milestones.${w} `
    + `They are ordinary rows — edit any of them, then Save.`);
}

