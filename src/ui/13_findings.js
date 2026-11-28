
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
    `<div class="banner ${kind}">`
    + (kind === "busy" ? `<span class="spin" aria-hidden="true"></span>` : "")
    + `<strong>${esc(text)}</strong>`
    + (n ? ` ${esc(summary)}.` : "")
    + (cfgN ? `<span class="lk" id="openCfg">Which settings changed</span>` : "")
    /* Once a plan is open its findings have a tab of their own (R-69), where they can be
       sorted and fixed - and the way there stays in the band whatever it last said, with
       the count of what is open beside it, since the band is where the state of the data
       is read. The report is what a file that could not be opened still gets. */
    + (!el("tabs").hidden && S.model
        ? `<span class="lk" id="openIssues">Open data issues<span id="openIssuesN"></span></span>`
        : n ? `<span class="lk" id="openRep">Open full report</span>` : "")
    + `</div>`;
  const b = el("openRep");
  if (b) b.onclick = () => { renderReport(findings); el("report").showModal(); };
  const i = el("openIssues");
  if (i) i.onclick = () => { closeCard(); showTab("t-issues"); window.scrollTo({top:0}); };
  issueCount();
  cardEcho(kind, text + (n ? ` ${summary}.` : ""));   // and inside an open card (R-69)
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
  PeriodFTEStandard:"Standard period FTE for project types", RoleFactor:"Role factors",
  PeriodHighlight:"Period colours", PeriodRule:"Period derivation rules",
  Lists:"Value lists", Config:"Configuration",
  MonthlyEstimate:"Monthly estimation",
  "(cascade)":"Carried through automatically",
};
const TAB_OF = {
  Project:"Source data (project)", Milestone:"Source data (project)",
  ProjectPeriod:"Source data (project)", Person:"Source data (person)",
  Assignment:"Source data (person)", PersonPeriodWeight:"Source data (person)",
  PeriodFTEStandard:"General assumptions", RoleFactor:"General assumptions",
  PeriodHighlight:"General assumptions", PeriodRule:"General assumptions",
  Lists:"General assumptions", Config:"General assumptions",
  // Both, genuinely: a project figure is edited on one tab and an assignment figure on
  // the other. Naming one would send half the log to the wrong place.
  MonthlyEstimate:"Source data (project / person)",
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

/** A project's milestones as the derivation reads them - name to dates, earliest first -
 *  from the RAW rows, so a set just typed and not yet saved counts: the two buttons are
 *  meant to be used one after the other. */
function rawMilestones(pid){
  const ms = {};
  for (const m of S.model.raw.Milestone)
    if (m.project_id === pid && m.milestone_name && m.milestone_date instanceof Date)
      (ms[m.milestone_name] ||= []).push(m.milestone_date);
  for (const k of Object.keys(ms)) ms[k].sort((a, b) => a - b);
  return ms;
}

/** This project's periods, worked out from its milestones - by the Period derivation
 *  rules for its type where the plan states some (R-70), by the built-in rule otherwise -
 *  and SHOWN before they are written: every date, and how it was found. */
function autoPeriods(pid){
  const M = S.model, pr = M.projects[pid];
  if (!pr){
    showBanner("bad", `${pid} has not been saved yet. Save the project first — the `
      + `derivation reads its start and end dates.`);
    return;
  }
  const rules = rulesFor(M, pr.project_type);
  if (!rules && !CLINICAL_TYPES.has(pr.project_type)){
    showBanner("bad", `${pid} is a '${pr.project_type}' project, and there are no Period `
      + `derivation rules for that type on General assumptions. Add them there, or enter `
      + `Planning / Develop / Close by hand, with no gap and no overlap.`);
    return;
  }
  const plan = derivationPlan(pr, rawMilestones(pid), M);
  if (!plan || !plan.segs.length){
    const named = rules ? [...new Set(rules.flatMap(r => [r.start_milestone, r.end_milestone])
      .filter(Boolean))] : [];
    showBanner("bad", rules
      ? `Cannot derive periods for ${pid}: none of the milestones the rules for `
        + `'${pr.project_type}' count from is recorded for it (${named.join(", ")}). Add one `
        + `of them, or change the rules on General assumptions.`
      : `Cannot derive periods for ${pid}: the rule needs a 'CTA submission' date and at `
        + `least one DB lock (V-16). Add those milestones above, then try again.`);
    return;
  }
  openDerive(pid, plan);
}

/** The preview. An estimate is marked as one, the periods left out are named with the
 *  reason, and where two periods do not meet it is said - so what is written is what the
 *  reader agreed to, not what they found out about afterwards. */
function openDerive(pid, plan){
  const M = S.model, pr = M.projects[pid];
  const existing = M.raw.ProjectPeriod.filter(r => r.project_id === pid);
  const nd = (a, b) => Math.round((b - a) / DAY) + 1;
  const how = (t, e) => `<span class="dvhow${e ? " est" : ""}">${e ? `<span class="estpill">estimate</span> ` : ""}`
    + `${esc(t)}</span>`;
  const by = plan.source === "rules"
    ? `by the <strong>Period derivation rules</strong> for <strong>${esc(pr.project_type)}</strong> (General assumptions)`
    : `by the <strong>built-in rule</strong> — there are no Period derivation rules for ${esc(pr.project_type)}`;
  el("dvTitle").innerHTML = `Auto derivation — ${esc(pr.project_name || pid)} `
    + `<span class="tr">${esc(pid)}</span>`;
  const nEst = plan.segs.filter(g => g.est.start || g.est.end).length;
  el("dvBody").innerHTML =
    `<p class="cap">${plan.segs.length} period${plan.segs.length === 1 ? "" : "s"} worked out from this
      project's milestones ${by}.${nEst ? ` <strong>${nEst}</strong> of them rest on an estimate where
      a milestone is not recorded — marked below; check those dates.` : ""}</p>
     <div class="scrollx"><table class="data-t dvt"><thead><tr><th>Period</th><th>From</th><th>To</th>
       <th class="num">Days</th><th>Start — how it was found</th><th>End — how it was found</th>
       <th class="num">Standard weight</th></tr></thead><tbody>${plan.segs.map(g => {
        const w = stdWeight(M, pr, g.name);
        return `<tr><td><strong>${esc(g.name)}</strong></td>`
          + `<td class="${g.est.start ? "estd" : ""}">${ymd(g.start)}</td>`
          + `<td class="${g.est.end ? "estd" : ""}">${ymd(g.end)}</td>`
          + `<td class="num">${nd(g.start, g.end)}</td>`
          + `<td>${how(g.how.start, g.est.start)}</td><td>${how(g.how.end, g.est.end)}</td>`
          + `<td class="num">${w === undefined || w === null ? `<span class="muted">1.00 (none set)</span>`
                                                             : num(w).toFixed(2)}</td></tr>`;
      }).join("")}</tbody></table></div>`
    + (plan.left.length ? `<h3 class="dvh">Left out</h3><ul class="dvl">${plan.left.map(l =>
        `<li><strong>${esc(l.name)}</strong> — ${esc(l.why)}.</li>`).join("")}</ul>` : "")
    + (plan.seams.length ? `<h3 class="dvh">Where periods do not meet</h3><ul class="dvl warn">${plan.seams.map(x =>
        `<li><strong>${esc(x.a)}</strong> and <strong>${esc(x.b)}</strong>: `
        + (x.days > 0 ? `${x.days} day(s) between them belong to no period (V-12).`
                      : `they overlap by ${-x.days} day(s) (V-06) — an overlap is refused at Save.`)
        + `</li>`).join("")}</ul>` : "")
    + `<p class="note">${existing.length
        ? `<strong>Apply replaces the ${existing.length} period row(s) ${esc(pid)} has now.</strong> `
        : `${esc(pid)} has no period rows yet; these become its periods. `}`
      + `They are ordinary rows afterwards — edit any of them — and provisional until Save, like any `
      + `other change: <strong>Leave without change</strong> puts everything back.</p>`;
  const dlg = el("derivedlg");
  let done = false;
  const finish = ok => {
    if (done) return;
    done = true;
    if (dlg.open) dlg.close();
    if (ok) applyDerived(pid, plan);
  };
  el("dvYes").onclick = () => finish(true);
  el("dvNo").onclick = () => finish(false);
  dlg.onclose = () => finish(false);
  dlg.showModal();
  cueScrollers();
}

/** Write what the preview showed: the project's periods replaced by these, each at the
 *  standard weight for its type, phase and scope - through stdWeight, not straight at
 *  M.pws: schema 6 put the work scope in the key, and a lookup that leaves it out matches
 *  nothing and quietly derives every period at 1.00. */
function applyDerived(pid, plan){
  const M = S.model, pr = M.projects[pid];
  const existing = M.raw.ProjectPeriod.filter(r => r.project_id === pid);
  beginEditSession();
  for (const r of existing){
    M.raw.ProjectPeriod.splice(M.raw.ProjectPeriod.indexOf(r), 1);
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(deleted row)",
                    from:r.period_name, to:null});
  }
  plan.segs.forEach((g, i) => {
    const r = newRow("ProjectPeriod", {project_id:pid, period_name:g.name, period_seq:i + 1,
      period_start:g.start, period_end:g.end, weight: stdWeight(M, pr, g.name) ?? 1.00});
    S.pending.push({at:new Date(), sheet:"ProjectPeriod", row:r.__row, col:"(new row)",
                    from:null, to:`${g.name} ${ymd(g.start)}..${ymd(g.end)}`});
  });
  renderKeepingTab();
  const est = plan.segs.filter(g => g.est.start || g.est.end).map(g => g.name);
  showBanner(est.length || plan.seams.length ? "warn" : "",
    `Derived ${plan.segs.length} periods for ${pid} ${plan.source === "rules"
      ? `by the rules for ${pr.project_type}` : "by the built-in rule"}.`
    + (est.length ? ` Estimated where a milestone is missing: ${est.join(", ")}.` : "")
    + (plan.left.length ? ` Left out: ${plan.left.map(l => l.name).join(", ")}.` : "")
    + ` They are ordinary rows — edit any of them, then Save.`);
}

/* ------------------------------------------- the rules themselves (R-70, General assumptions) */

/** A rule row added from the table, for one period of one type, counted at once: its
 *  key is whole, and the milestones are typed into it next. */
function addPeriodRule(type, period){
  if (!type || !period) return null;
  beginEditSession();
  const r = newRow("PeriodRule", {project_type:type, period_name:period});
  delete r.__new;
  S.pending.push({at:new Date(), sheet:"PeriodRule", row:r.__row, col:"(new row)",
                  from:null, to:`${type} · ${period}`});
  return r;
}

/** The rules the template ships, laid out for a type that has none - the same rows for
 *  every clinical type, as the template carries them; a clinical type the template does
 *  not know takes the first clinical type's. 'Others' has no standard rules to lay out. */
function layOutStandardRules(type){
  const seed = (typeof SEED_PRULE !== "undefined" ? SEED_PRULE : []);
  const ct = CLINICAL_TYPES.has(type);
  let rows = seed.filter(r => r[0] === type);
  if (!rows.length){
    const like = seed.find(r => CLINICAL_TYPES.has(r[0]) === ct);
    rows = like ? seed.filter(r => r[0] === like[0]) : [];
  }
  if (!rows.length){
    showBanner("bad", `There are no standard rules for '${type}' to lay out — add a rule for `
      + `each of its periods from the table.`);
    return;
  }
  beginEditSession();
  const cols = SHEET_HEADERS.PeriodRule;
  for (const v of rows){
    const r = newRow("PeriodRule", Object.fromEntries(cols.map((c, i) => [c, v[i] ?? null])));
    r.project_type = type;
    delete r.__new;
    S.pending.push({at:new Date(), sheet:"PeriodRule", row:r.__row, col:"(new row)",
                    from:null, to:`${type} · ${r.period_name}`});
  }
  rebuild(true);
  renderKeepingTab();
  showBanner("", `Laid out the ${rows.length} standard period derivation rules for ${type}. `
    + `Change any of them in the table; Auto derivation on a ${type} project uses them from now on.`);
}

/** One type's rules copied over another's - which is replaced, after asking, so the two
 *  read the same afterwards rather than a mixture. */
function copyPeriodRules(from, to){
  const M = S.model;
  const src = M.raw.PeriodRule.filter(r => r.project_type === from);
  const old = M.raw.PeriodRule.filter(r => r.project_type === to);
  if (!src.length || !to || from === to) return;
  if (old.length && !confirm(`${to} has ${old.length} rule(s) of its own.\n\n`
      + `Replace them with the ${src.length} rule(s) of ${from}?\n`
      + `This is provisional — 'Leave without change' puts them back.`)) return;
  beginEditSession();
  for (const r of old){
    M.raw.PeriodRule.splice(M.raw.PeriodRule.indexOf(r), 1);
    S.pending.push({at:new Date(), sheet:"PeriodRule", row:r.__row, col:"(deleted row)",
                    from:`${to} · ${r.period_name}`, to:null});
  }
  for (const s of src){
    const r = newRow("PeriodRule", Object.fromEntries(SHEET_HEADERS.PeriodRule.map(c => [c, s[c] ?? null])));
    r.project_type = to;
    delete r.__new;
    S.pending.push({at:new Date(), sheet:"PeriodRule", row:r.__row, col:"(new row)",
                    from:null, to:`${to} · ${r.period_name}`});
  }
  S.genView.prule = to;
  rebuild(true);
  renderKeepingTab();
  showBanner("", `Copied the ${src.length} period derivation rule(s) of ${from} to ${to}.`);
}
