/* ============================================================ 11. tab rendering */

function renderOverall(){
  const M = S.model, C = S.calc, G = grid();
  const pids = activeProjects(), sids = activePeople();
  let total = 0, over = 0;
  for (const p of pids) for (const k of G) total += C.projMonth.get(p+"|"+k) || 0;
  for (const s of sids) for (const k of G){
    const v = C.persMonth.get(s+"|"+k) || 0;
    if (v > M.OVER) over++;
  }
  let runs = 0;
  for (const s of sids){
    let run = 0;
    for (const k of G){
      const v = C.persMonth.get(s+"|"+k) || 0;
      if (v > 0 && v < M.UNDER) run++;
      else { if (run >= M.MINM) runs++; run = 0; }
    }
    if (run >= M.MINM) runs++;
  }
  const tiles = [
    ["Projects in view", pids.length, `of ${Object.keys(M.projects).length} in the file`, "",
     "Projects matching the current filters that draw resource somewhere in the horizon. Change the "
     + "filters or the horizon and this moves."],
    ["People in view", sids.length, `of ${Object.keys(M.people).length} in the file`, "",
     "People holding at least one assignment on a project in view."],
    ["Total demand", fmt(total), `${unitLabel()}-months over ${G.length} months`, "",
     `The sum of every monthly figure in view. One ${unitLabel()}-month is one person working a full `
     + `month. Table A and table B are the same numbers aggregated differently, so their totals agree.`],
    ["Over-allocated", over, `person-months above ${M.OVER.toFixed(2)} FTE`, "over",
     `How many person-months exceed the ceiling of ${M.OVER.toFixed(2)} FTE. The threshold is ABSOLUTE — `
     + "it is not scaled by anyone's capacity."],
    ["Under-allocation runs", runs, `${M.MINM}+ months below ${M.UNDER.toFixed(2)} FTE`, "under",
     `Stretches of ${M.MINM} or more consecutive months below ${M.UNDER.toFixed(2)} FTE. Counted as RUNS, `
     + "not months — three separate amber cells would look like three problems. A month at zero breaks a "
     + "run rather than continuing it: somebody with no assignments is unassigned, not under-allocated."],
  ].map(([l,v,s,c,h]) => `<div class="tile ${c}" data-tip="${att(`<b>${l}</b><br>${h}`)}">`
    + `<div class="tl">${l}</div>`
    + `<div class="tv">${c==="over"?"&#9650; ":c==="under"?"&#9660; ":""}${v}</div>`
    + `<div class="ts">${s}</div></div>`).join("");

  const scope = `${G.length} months &#183; ${pids.length} project(s) &#183; ${sids.length} people`;
  el("t-overall").innerHTML =
    `<div class="tiles">${tiles}</div>
    <div class="panel">
      <div class="phead"><h2>Monthly resource trend</h2>
        <span class="scope k">${scope}</span></div>
      <p class="cap">One line per project, sharing one baseline. The stacked charts below say what
        each month's total is made of; only lines say whether a given project is rising or falling,
        because in a stack every band's baseline moves with the bands beneath it.
        <strong>Hover any line</strong> for its total, mean and peak month.</p>
      <div class="scrollx fit">${projectLines(pids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>Project timeline</h2>
        <span class="scope k">${pids.length} project(s)</span></div>
      <p class="cap">One row per project, with its start, end and length under the name. Bands are
        coloured by period and shaded darker as the period weight rises. The two DB locks are red —
        they are what the period derivation hangs on. <strong>Hover any band or marker</strong> for detail.</p>
      <div class="scrollx xl">${chartGantt(pids.slice().sort(byRank))}</div></div>
    <div class="panel">
      <div class="phead"><h2>Monthly demand by project</h2>
        <span class="scope k">${scope}</span></div>
      <p class="cap">One band per project, ordered by total resource with the largest on the baseline.
        <strong>Hover any band</strong> for the project, its ${unitLabel()} that month and who is on it.</p>
      <div class="scrollx xl">${chartStacked(pids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>Resource by project</h2>
        <span class="scope k">${pids.length} project(s)</span></div>
      <p class="cap">Sorted NewDrug CT, then Biosimilar CT, then Others; earlier projects first.
        <strong>Click a project name</strong> to expand it to the people and roles on it.</p>
      <div class="scrollx xl">${tableProjects(pids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>Monthly demand by person</h2>
        <span class="scope k">${scope}</span></div>
      <p class="cap">The same months as <strong>Monthly demand by project</strong> above, cut the
        other way: one stacked band per person. The two charts total the same figure every month,
        because they are the same person-months summed along different axes. A segment is outlined
        where that person's own month crosses the ${M.OVER.toFixed(2)} ceiling or the
        ${M.UNDER.toFixed(2)} floor. <strong>Hover any band</strong> for the projects behind it.</p>
      <div class="scrollx xl">${chartPeople(sids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>Resource by person</h2>
        <span class="scope k">${sids.length} people</span></div>
      <p class="cap">Summed across every project. &#9650; above the ceiling, &#9660; below the floor.
        <strong>Click a person name</strong> to expand to their projects and roles.</p>
      <div class="scrollx xl">${tablePeople(sids)}</div>
      <p class="note">Under-allocation is counted as a run of ${M.MINM} or more consecutive months, not
        per month — the run is what matters, a single quiet month is not.</p></div>`;
}

function renderProjTab(){
  const M = S.model;
  const pids = activeProjects().sort(byRank);
  const cols = entryCols("Project");
  if (!pids.length){
    // Nothing in the plan is a different situation from nothing matching the filters,
    // and only one of them is fixed by adding a row. Offer the row where it would help.
    // Drafts are counted separately because a row still being typed has not been parsed
    // into M.projects yet - it exists only in raw, and it is exactly the row the user is
    // looking at, so it has to be on screen even though nothing "matches".
    // `|| !hasKey` so a row saved without a project_id is still here: it is not a record,
    // so nothing above matched it, but it is exactly the row that needs repairing.
    const drafts = M.raw.Project.filter(r => r.__new || !hasKey("Project", r));
    // The draft becomes the selection, so a milestone added below inherits its
    // project_id - PARENT_OF seeds from S.selProj, and without this the child row would
    // be created with no parent at all.
    const draft = drafts.find(r => r.project_id) || drafts[0] || null;
    S.selProj = draft && draft.project_id ? draft.project_id : null;
    el("t-proj").innerHTML = Object.keys(M.projects).length
      ? `<div class="panel"><p class="note">No projects match the current filters. `
        + `<strong>Reset filters</strong> above to see them all.</p></div>`
      : `<div class="panel">
          <div class="phead"><h2>Projects</h2>
            <span class="scope k">${drafts.length ? `${drafts.length} being entered`
                                                  : "nothing yet"}</span></div>
          <p class="cap">${drafts.length
            ? `Fill the row in, then press <strong>Save</strong> — the timeline and the
               utilisation chart appear once the project is saved. The two tables below can
               be filled in as soon as it has an identifier.`
            : `There are no projects in this plan. <strong>+ row</strong> adds the first one.`}
            A clinical trial needs at least the identifier, name, type, phase and the two
            dates: the phase is what selects the standard period weights.</p>
          ${dataTable("Project", drafts, cols, "project_id", null)}</div>
        ${scratchProject(draft)}`;
    return;
  }
  if (!S.selProj || !pids.includes(S.selProj)) S.selProj = pids[0];
  const pid = S.selProj, pr = M.projects[pid];
  const keep = new Set(pids);
  const rows = M.raw.Project.filter(r => keep.has(r.project_id) || r.__new
                                      || !hasKey("Project", r));
  const util = chartProjectUtil(pid);
  const ms = M.raw.Milestone.filter(m => m.project_id === pid)
    .sort((a,b) => a.milestone_date - b.milestone_date);
  const per = (M.periods[pid] || []);
  const derived = per.some(p => p.__derived);

  el("t-proj").innerHTML =
    `<div class="panel">
      <div class="phead"><h2>Monthly resource trend</h2>
        <span class="scope k">${grid().length} months &#183; ${pids.length} project(s)</span></div>
      <p class="cap">One line per project, so the project selected below can be read against the
        others rather than on its own. <strong>Hover any line</strong> for its total, mean and
        peak month.</p>
      <div class="scrollx fit">${projectLines(pids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>Projects</h2>
        <span class="scope k">${rows.length} in the current filter</span></div>
      <p class="cap">Every field is editable — click a cell and type. Clicking a row also selects it,
        which drives the panels below. <strong>+ row</strong> inserts directly below that row.</p>
      ${dataTable("Project", rows, cols, "project_id", pid)}</div>
    <div id="projDetail">${projDetail(pid)}</div>`;
}

function projDetail(pid){
  const M = S.model, pr = M.projects[pid];
  /* Clicking a row that has not been saved yet makes its identifier the selection, and
     the model does not know that identifier: the timeline and the utilisation chart need
     a RECORD - dates, a name, a calculation - and a draft has none of that. It used to
     throw here, which took the whole re-render with it and left the tab as it was, so
     the click appeared to do nothing at all. Fall back to the panels a plan being typed
     from scratch uses, which are built for exactly this state. */
  if (!pr) return scratchProject(M.raw.Project.find(r => r.project_id === pid) || null);
  const util = chartProjectUtil(pid);
  // `|| m.__new` so a row the user just created is visible even before its parent key
  // is filled in. Seeding usually covers it; this covers the case where it cannot.
  const ms = childrenOf(M.raw.Milestone, "project_id", pid)
    .sort((a,b) => (a.milestone_date||0) - (b.milestone_date||0));
  const per = (M.periods[pid] || []);
  const derived = per.some(p => p.__derived);
  return `<div class="panel">
      <div class="phead"><h2>Project timeline — ${esc(pr.project_name)}</h2>
        <span class="scope k">${per.length} period(s) &#183; ${ms.length} milestone(s)</span></div>
      <p class="cap">The same run-chart as the Overall tab, for this project alone: one band per
        period, coloured by period and shaded darker as the period weight rises, with every
        milestone marked. The two DB locks are red — they are what the period derivation hangs on.
        <strong>Hover any band or marker</strong> for its dates, weight and average load.</p>
      <div class="scrollx fit">${chartGantt([pid], {single:true,
        note:`${ymd(pr.start_date)} &#8594; ${ymd(pr.end_date)}`
           + (pr.total_period_months ? ` &middot; ${pr.total_period_months} months` : "")
           + ` &middot; ${(M.periods[pid] || []).length} period(s). Edit the two tables below and `
           + `this redraws.`})}</div></div>
    <div class="panel">
      <div class="phead"><h2>Utilisation — ${esc(pr.project_name)}</h2>
        <span class="scope k">${grid().length} months &#183; stacked by person</span></div>
      <p class="cap">Monthly resource for the selected project, <strong>each bar split into the
        people who make it up</strong>. A project has no absolute ceiling or floor, so the reference
        lines are <strong>relative</strong>: twice and half the average an active project draws across
        the portfolio (${util.portAvg.toFixed(2)} FTE), plus this project's own average over its full
        life (${util.ownAvg.toFixed(2)} FTE). They are context, not pass or fail.
        <strong>Hover any segment</strong> for that person's role and share of the month.</p>
      <div class="scrollx fit">${util.svg}</div></div>
    <div class="two">
      <div class="panel">
        <div class="phead"><h2>Milestones — ${esc(pr.project_name)}</h2>
          <button class="btn tiny" data-act="blankms" data-pid="${att(pid)}"
            data-tip="${att(HELP.blankms)}">Blank list</button>
          <span class="scope k">${ms.length} row(s)</span></div>
        <p class="cap">CTA submission and the DB locks set the period boundaries.
          <strong>Blank list</strong> lays out the standard milestone names with their dates
          empty, so only the dates have to be typed.</p>
        ${dataTable("Milestone", ms, ["milestone_name","milestone_date","milestone_seq","note_1"])}</div>
      <div class="panel">
        <div class="phead"><h2>Periods — ${esc(pr.project_name)}</h2>
          <button class="btn tiny" data-act="autoper" data-pid="${att(pid)}"
            data-tip="${att(HELP.autoper)}">Auto derivation</button>
          <span class="scope k">${per.length} row(s)${derived ? " &#183; derived" : ""}</span></div>
        <p class="cap">${derived ? "Derived from the milestones above." : "As entered in the workbook."}
          Names are unique within a project, so <code>project_id + period_name</code> identifies a row.</p>
        ${derived
          ? `<p class="note">These periods were DERIVED from the milestones above because the workbook
             carries none for this project. Adding a row here starts a hand-entered set, which the
             application will then use as given.</p>`
          : ""}
        ${dataTable("ProjectPeriod", childrenOf(M.raw.ProjectPeriod, "project_id", pid),
          ["project_id","period_name","period_seq","period_start","period_end","weight","note_1"])}
        </div>
    </div>`;
}

/* The child sections while their parent is still being typed.
 *
 *  The full detail panel needs a parent RECORD: dates for the timeline, a name for every
 *  heading, a calculation to draw. A row still being entered has none of that - it is not
 *  even parsed into the model yet. But the SECTIONS have to be on screen from the start.
 *  A plan is entered top down, and a Milestones table that only appears once the project
 *  is saved reads as a Milestones table that does not exist; someone building their first
 *  plan has no way to know it is coming.
 *
 *  So the tables are drawn from the beginning, scoped to the draft's own identifier the
 *  moment it has one, and locked with the reason until it does.
 */
function scratchProject(draft){
  const M = S.model;
  const pid = draft ? draft.project_id : null;
  const who = draft && draft.project_name ? ` — ${esc(draft.project_name)}`
            : pid ? ` — ${esc(pid)}` : "";
  const lock = pid ? null
    : (draft ? "Give the project above a project_id first — a milestone attaches to it by "
             + "that identifier, and a row with nothing to attach to is dropped when the "
             + "file is read back."
             : "Add a project above first. Milestones and periods belong to one.");
  const ms = pid ? childrenOf(M.raw.Milestone, "project_id", pid)
                 : [];
  const per = pid ? childrenOf(M.raw.ProjectPeriod, "project_id", pid) : [];
  return `<div class="two">
      <div class="panel">
        <div class="phead"><h2>Milestones${who}</h2>
          ${pid ? `<button class="btn tiny" data-act="blankms" data-pid="${att(pid)}"
            data-tip="${att(HELP.blankms)}">Blank list</button>` : ""}
          <span class="scope k">${ms.length} row(s)</span></div>
        <p class="cap">CTA submission and a DB lock are the two the period derivation hangs
          on — enter those and the seven clinical periods are computed for you. The other
          eight names are markers.</p>
        ${dataTable("Milestone", ms, ["milestone_name","milestone_date","milestone_seq","note_1"],
                    null, null, null, lock)}</div>
      <div class="panel">
        <div class="phead"><h2>Periods${who}</h2>
          ${pid ? `<button class="btn tiny" data-act="autoper" data-pid="${att(pid)}"
            data-tip="${att(HELP.autoper)}">Auto derivation</button>` : ""}
          <span class="scope k">${per.length} row(s)</span></div>
        <p class="cap">Leave this empty for a clinical trial and let the milestones derive it.
          An <code>Others</code> project is not derived — enter Planning / Develop / Close
          here yourself, with no gap and no overlap.</p>
        ${dataTable("ProjectPeriod", per,
          ["project_id","period_name","period_seq","period_start","period_end","weight","note_1"],
          null, null, null, lock)}</div>
    </div>`;
}

function scratchPerson(draft){
  const M = S.model;
  const sid = draft ? draft.person_id : null;
  const who = draft && draft.person_name ? ` — ${esc(draft.person_name)}`
            : sid ? ` — ${esc(sid)}` : "";
  const lock = sid ? null
    : (draft ? "Give the person above a person_id first — an assignment attaches to it by "
             + "that identifier."
             : "Add a person above first. An assignment is one person on one project.");
  const asg = sid ? childrenOf(M.raw.Assignment, "person_id", sid) : [];
  const aid = selectedAssignment(asg);
  const ppw = aid ? M.raw.PersonPeriodWeight.filter(w =>
    w.assignment_id === aid || (w.__new && !w.assignment_id)) : [];
  return `<div class="two">
      <div class="panel">
        <div class="phead"><h2>Assignments${who}</h2>
          <span class="scope k">${asg.length} row(s)</span></div>
        <p class="cap">One row per person + project + role. Type the project NAME and
          <code>project_id</code> follows. <strong>+ row</strong> allocates the next
          <code>assignment_id</code>, and clicking a row selects it for the overrides beside.</p>
        ${dataTable("Assignment", asg,
          ["assignment_id","project_name","project_id","role_name","assign_start_date",
           "assign_end_date","person_weight","note_1","note_2","note_3"],
          "assignment_id", aid, null, lock)}</div>
      <div class="panel">
        <div class="phead"><h2>Weight overrides${who}</h2>
          <span class="scope k">${ppw.length} window(s)</span></div>
        <p class="cap">Only needed where someone's share of a project CHANGES for a stretch of
          months. The window <strong>replaces</strong> <code>person_weight</code> for the months
          it covers — it does not multiply it — and belongs to the assignment selected beside.</p>
        ${dataTable("PersonPeriodWeight", ppw,
          ["assignment_id","project_name","role_name","period_start","period_end",
           "weight_override","reason"], null, null,
          {project_name: r => {
             const a = assignmentById(r.assignment_id);
             return a ? projectNameOf(a.project_id) : "";
           },
           role_name: r => {
             const a = assignmentById(r.assignment_id);
             return a ? (a.role_name ?? "") : "";
           }},
          aid ? null : "Add an assignment beside first — an override belongs to one.")}</div>
    </div>`;
}

function renderPersTab(){
  const M = S.model;
  // listedPeople, not activePeople: somebody entered but not yet assigned to anything
  // still belongs on the tab where you assign them.
  const sids = listedPeople().sort();
  const cols = entryCols("Person");
  if (!sids.length){
    const drafts = M.raw.Person.filter(r => r.__new || !hasKey("Person", r));
    // As on the project tab: the draft becomes the selection, so an assignment added
    // below inherits its person_id instead of being created with no parent.
    const draft = drafts.find(r => r.person_id) || drafts[0] || null;
    S.selPers = draft && draft.person_id ? draft.person_id : null;
    el("t-pers").innerHTML = Object.keys(M.people).length
      ? `<div class="panel"><p class="note">Nobody matches the current filters. `
        + `<strong>Reset filters</strong> above to see everyone.</p></div>`
      : `<div class="panel">
          <div class="phead"><h2>People</h2>
            <span class="scope k">${drafts.length ? `${drafts.length} being entered`
                                                  : "nothing yet"}</span></div>
          <p class="cap">${drafts.length
            ? `Fill the row in, then press <strong>Save</strong> — the utilisation chart
               appears once the person is saved. The two tables below can be filled in as
               soon as they have an identifier.`
            : `There is nobody in this plan yet. <strong>+ row</strong> adds the first
               person.`} Their assignments — which project, which role, how much of them —
            are entered below.</p>
          ${dataTable("Person", drafts, cols, "person_id", null)}</div>
        ${scratchPerson(draft)}`;
    return;
  }
  if (!S.selPers || !sids.includes(S.selPers)) S.selPers = sids[0];
  const sid = S.selPers, pe = M.people[sid];
  const keepP = new Set(sids);

  const prows = M.raw.Person.filter(r => keepP.has(r.person_id) || r.__new
                                      || !hasKey("Person", r));
  el("t-pers").innerHTML =
    `<div class="panel">
      <div class="phead"><h2>Monthly load trend</h2>
        <span class="scope k">${grid().length} months &#183; ${sids.length} people</span></div>
      <p class="cap">One line per person, sharing one baseline, with the over-allocation ceiling
        marked. The stacked chart below the selection says what one person's month is made of;
        these lines say who is rising and who is falling.
        <strong>Hover any line</strong> for its total, mean and peak month.</p>
      <div class="scrollx fit">${personLines(sids)}</div></div>
    <div class="panel">
      <div class="phead"><h2>People</h2>
        <span class="scope k">${prows.length} in the current filter</span></div>
      <p class="cap">Editable, same rules as the project table — clicking a row selects it, and
        <strong>+ row</strong> inserts directly below.</p>
      ${dataTable("Person", prows, cols, "person_id", sid)}</div>
    <div id="persDetail">${persDetail(sid)}</div>`;
}

function persDetail(sid){
  const M = S.model, pe = M.people[sid];
  if (!pe) return scratchPerson(M.raw.Person.find(r => r.person_id === sid) || null);
  // From raw, not from M.assignments: the model's array is rebuilt by validate() and
  // excludes anything it rejected, so a row being repaired would vanish while edited.
  const asg = childrenOf(M.raw.Assignment, "person_id", sid);
  // PersonPeriodWeight is a child of ASSIGNMENT, not of person, so it follows the
  // assignment selected above it - the same relationship Milestones and Periods have to
  // the project selected above them. Scoping it to the person instead showed every
  // window this person carries across every project at once, which is a list of things
  // that have nothing to do with each other.
  const aid = selectedAssignment(asg);
  return `<div class="panel">
      <div class="phead"><h2>Utilisation — ${esc(pe.person_name)} (${esc(sid)})</h2>
        <span class="scope k">${grid().length} months &#183; stacked by project</span></div>
      <p class="cap">Monthly load across the horizon, <strong>each bar split into the projects that
        make it up</strong> — the total says whether this person is over the ceiling, the split says
        because of what. Every project keeps the same colour here as on the Overall tab.
        <strong>Hover any segment</strong> for that project's milestones and share of the month, and
        for the person's total. Dashed lines are the ceiling and floor — the same two figures for
        everyone, since both thresholds are absolute.</p>
      <div class="scrollx fit">${chartPersonStrip(sid)}</div></div>
    <div class="two">
      <div class="panel">
        <div class="phead"><h2>Assignments — ${esc(pe.person_name)} (${esc(sid)})</h2>
          <span class="scope k">${asg.length} row(s)</span></div>
        <p class="cap">Fill in <code>project_name</code> — <code>project_id</code> is derived from it.
          Editing the identifier directly still works and the name follows instead.
          <strong>Clicking a row selects it</strong>, which drives the overrides beside it.
          <strong>+ row</strong> allocates the next <code>assignment_id</code>.</p>
        ${dataTable("Assignment", asg,
          ["assignment_id","project_name","project_id","role_name","assign_start_date",
           "assign_end_date","person_weight","note_1","note_2","note_3"],
          "assignment_id", aid)}</div>
      <div id="asgDetail">${overridesPanel(sid)}</div>
    </div>`;
}

/** The overrides beside the Assignments table, in their own element.
 *
 *  Separate so that selecting an assignment can redraw THIS and nothing else. Redrawing
 *  the whole person panel would rebuild the Assignments table too - and clicking a cell
 *  both selects the row and puts the caret in it, so the cell would be replaced under the
 *  caret and the edit could never be typed. The project and person tables avoid this by
 *  living outside the panel they drive; this table drives a panel beside it, so the
 *  boundary has to be drawn here instead. */
function overridesPanel(sid){
  const M = S.model, pe = M.people[sid];
  const asg = childrenOf(M.raw.Assignment, "person_id", sid);
  const aid = selectedAssignment(asg);
  const sel = asg.find(a => a.assignment_id === aid) || null;
  const ppw = M.raw.PersonPeriodWeight.filter(w =>
    (aid && w.assignment_id === aid) || (w.__new && !w.assignment_id));
  // A blank assignment date means the PROJECT's date (REQ-CAL-15), so the window shown
  // is the one actually used. Marked, because "2027-01-01 ~ 2029-06-30" typed into the
  // row and the same pair inherited from the project are different facts, and somebody
  // deciding whether to edit the row needs to know which they are looking at.
  const span = sel ? (() => {
    const pr = M.projects[sel.project_id] || {};
    const s = sel.assign_start_date || pr.start_date;
    const e = sel.assign_end_date || pr.end_date;
    const whole = !sel.assign_start_date && !sel.assign_end_date;
    return `${ymd(s) || "—"} ~ ${ymd(e) || "—"}`
      + (whole ? " · the whole project" : "");
  })() : "";
  return `<div class="panel">
      <div class="phead"><h2>Weight overrides — ${esc(pe.person_name)} (${esc(sid)})</h2>
        <span class="scope k">${ppw.length} window(s)</span></div>
      ${sel
        ? `<p class="asgline"><strong>Assignment (${esc(sel.assignment_id ?? "—")})</strong>: `
          + `${esc((M.projects[sel.project_id] || {}).project_name ?? sel.project_id ?? "—")} / `
          + `${esc(sel.role_name ?? "—")} / ${span} / weight `
          + `${sel.person_weight === null || sel.person_weight === undefined
               ? "—" : Number(sel.person_weight).toFixed(2)}</p>`
        : `<p class="asgline muted">No assignment selected — click a row in Assignments.</p>`}
      <p class="cap">Replaces <code>person_weight</code> for the window it covers, for
        <strong>this assignment only</strong>. One assignment may carry several
        non-overlapping windows.</p>
      ${dataTable("PersonPeriodWeight", ppw,
        ["assignment_id","project_name","role_name","period_start","period_end",
         "weight_override","reason"], null, null,
        {project_name: r => {
           const a = assignmentById(r.assignment_id);
           return a ? projectNameOf(a.project_id) : "";
         },
         role_name: r => {
           const a = assignmentById(r.assignment_id);
           return a ? (a.role_name ?? "") : "";
         }})}</div>`;
}

/* The assignment a window points at, and the project it names — read from RAW rather
   than from the validated model.
   M.assignments excludes anything still being entered, and M.projects excludes a project
   that has not been saved, so the two lookup columns beside a window went blank until the
   user pressed Save on the table above. Those columns exist precisely so that, while
   typing, you can see the window is attached to the right piece of work; blank at exactly
   that moment is when they are least useful. */
const assignmentById = aid =>
  (S.model.raw.Assignment || []).find(a => a.assignment_id === aid) || null;
const projectNameOf = pid =>
  (S.model.projects[pid] || {}).project_name
  || ((S.model.raw.Project || []).find(p => p.project_id === pid) || {}).project_name || "";

/** The assignment the overrides table hangs off: the one clicked, while it is still one
 *  of the rows on screen, otherwise the first. Held in S rather than derived each time,
 *  so it survives an edit that re-renders the panel. */
function selectedAssignment(asg){
  const ids = asg.map(a => a.assignment_id).filter(Boolean);
  if (!ids.includes(S.selAsg)) S.selAsg = ids[0] ?? null;
  return S.selAsg;
}

/* What an empty work_scope_type says on screen. Blank would read as "not filled in
   yet", which is the opposite of what it means: the row applies to every scope, on
   purpose, and it is usually the only row there is. */
const scopeLabel = r => r.work_scope_type ? String(r.work_scope_type) : "any scope";

function wmatrix(rows, keyOf, labelOf, colKey, valKey){
  const cols = [], keys = [], grid = {};
  let vmax = 0;
  for (const r of rows){
    if (!cols.includes(r[colKey])) cols.push(r[colKey]);
    const k = keyOf(r).join(" · ");
    if (!keys.includes(k)) keys.push(k);
    grid[k + "||" + r[colKey]] = num(r[valKey]);
    vmax = Math.max(vmax, num(r[valKey]) || 0);
  }
  const head = cols.map(c => `<th>${esc(c)}</th>`).join("");
  const body = keys.map(k => {
    const [nm, sub] = labelOf(k);
    const tds = cols.map(c => {
      const v = grid[k + "||" + c];
      if (v === undefined || v === null) return '<td class="c z">&middot;</td>';
      const i = seqStep(v, vmax);
      return `<td class="c" style="background:${SEQ[i]};color:${i>6?"#fff":"var(--ink)"}">${v.toFixed(2)}</td>`;
    }).join("");
    return `<tr><th class="rh"><span class="nm">${esc(nm)}</span>`
      + `<span class="sub">${esc(sub)}</span></th>${tds}</tr>`;
  }).join("");
  return `<table class="grid-t"><thead><tr><th class="rh">&nbsp;</th>${head}</tr></thead>`
    + `<tbody>${body}</tbody></table>`;
}

/* The two weight sheets and the value lists are shown as MATRICES because that is how
   they read - 289 role-factor rows flat is a list nobody scans, and a role's shape
   across the periods is the point of keying it that way. But a matrix cannot carry row
   actions: one matrix row is six or seven workbook rows. So each has both views, and
   the toggle decides which. Reading and editing want different shapes; this stops one
   compromising the other. */
function viewToggle(id, label){
  const rows = S.genView[id] === "rows";
  return `<span class="vtog" data-view="${id}">`
    + `<button class="btn tiny${rows ? "" : " on"}" data-setview="${id}|matrix">Matrix</button>`
    + `<button class="btn tiny${rows ? " on" : ""}" data-setview="${id}|rows">Rows &amp; editing</button>`
    + `</span>`;
}

function renderGenTab(){
  const M = S.model;
  const pwsRows = M.raw.PeriodWeightStandard, rfRows = M.raw.RoleFactor;
  const pws = S.genView.pws === "rows"
    ? dataTable("PeriodWeightStandard", pwsRows,
        ["project_type","clinical_phase","work_scope_type","period_name","weight","note_1"])
    : `<div class="scrollx tall">${wmatrix(pwsRows,
        r => [r.project_type, r.clinical_phase, scopeLabel(r)],
        k => { const p = k.split(" · "); return [p[1] + " · " + p[2], p[0]]; },
        "period_name", "weight")}</div>`;

  const ct = rfRows.filter(r => CLINICAL_TYPES.has(r.project_type));
  const ot = rfRows.filter(r => !CLINICAL_TYPES.has(r.project_type));
  const rf = S.genView.rf === "rows"
    ? dataTable("RoleFactor", rfRows,
        ["project_type","clinical_phase","work_scope_type","period_name","role_name",
         "role_factor","role_note"])
    : `<div class="scrollx tall">${wmatrix(ct,
        r => [r.project_type, r.clinical_phase, scopeLabel(r), r.role_name],
        k => { const p = k.split(" · "); return [p[3], p[0] + " · " + p[1] + " · " + p[2]]; },
        "period_name", "role_factor")}</div>
       <h2 class="subhead">Role factors — Others</h2>
       <div class="scrollx">${wmatrix(ot, r => [r.project_type, r.role_name],
        k => { const p = k.split(" · "); return [p[1], p[0]]; }, "period_name", "role_factor")}</div>`;

  const grouped = {};
  for (const r of M.raw.Lists) (grouped[r.list_name] ||= []).push(String(r.value));
  const lists = S.genView.lists === "rows"
    ? dataTable("Lists", M.raw.Lists, ["list_name","value","note_1"])
    : `<div class="scrollx tall"><table class="data-t"><thead><tr><th>list_name</th><th>values</th>
        <th>n</th></tr></thead><tbody>${Object.entries(grouped).map(([k, v]) =>
        `<tr><td>${esc(k)}</td><td class="vals">${esc(v.join(", "))}</td>`
        + `<td class="num">${v.length}</td></tr>`).join("")}</tbody></table></div>`;

  el("t-gen").innerHTML =
    `<div class="panel">
      <div class="phead"><h2>Standard period weights</h2>
        <span class="scope">PeriodWeightStandard</span>${viewToggle("pws")}</div>
      <p class="cap">The weight every clinical trial period is multiplied by, selected by the project's
        type and clinical phase. The matrix is how a standard reads — across, not down. Switch to
        <strong>Rows &amp; editing</strong> to add, change or delete individual rows.
        <strong>Others</strong> projects take hand-entered weights instead.</p>
      ${pws}</div>
    <div class="panel">
      <div class="phead"><h2>Role factors</h2>
        <span class="scope">RoleFactor</span>
        <span class="scope k">${rfRows.length} row(s)</span>${viewToggle("rf")}</div>
      <p class="cap">What one person in this role costs the project per month, before their own weight
        and the period weight. Keyed on type, phase, period and role — read a row across to see how a
        role's burden moves over the life of a project. ${rfRows.length} rows in all.</p>
      ${rf}</div>
    <div class="two">
      <div class="panel">
        <div class="phead"><h2>Configuration</h2>
          <span class="scope">Config</span>
          <span class="scope k">${M.raw.Config.length} setting(s)</span></div>
        <p class="cap">The thresholds and settings the whole page reads. Both allocation thresholds are
          absolute — they are not scaled by anyone's capacity.</p>
        ${dataTable("Config", M.raw.Config, ["parameter","value","note"])}
        <div class="controls" style="margin-top:10px">
          <div class="ctl"><label>Display unit</label><select id="unitSel">
            <option${M.UNIT!=="hours"?" selected":""}>FTE</option>
            <option${M.UNIT==="hours"?" selected":""}>hours</option></select></div></div></div>
      <div class="panel">
        <div class="phead"><h2>Value lists</h2>
          <span class="scope">Lists</span>
          <span class="scope k">${Object.keys(grouped).length} list(s)</span>${viewToggle("lists")}</div>
        <p class="cap">What each list-typed column will accept — and what the type-ahead offers you
          while editing. A value outside its list is kept and reported (V-11), never dropped.</p>
        ${lists}</div>
    </div>`;
}

function renderAll(){
  renderOverall(); renderProjTab(); renderPersTab(); renderGenTab();
  renderDirty();
}

