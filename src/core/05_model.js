/* ============================================================ 5. model + validation
   Every rule from spec sheet 04. The load never stops at the first problem: findings
   are collected and shown as one report (REQ-IMP-02).                            */

/* ---------------------------------------------------- the work scope, schema 6 --
   A project's workload depends on how much of the work it keeps: a trial run entirely
   in-house costs this team more than the same trial handed to a CRO. So the two
   standards tables are keyed on the work scope as well as on the type, the phase and
   the period.

   The three functions below are the whole of that rule, and they are together in one
   place on purpose. The scope is consulted from four directions - seeding a derived
   period, calculating a month, checking V-19, checking V-23 - and four copies of a
   fallback are four chances for the number on screen to differ from the number the
   validation was looking at.

       exact row for this project's scope   ->   use it
       no such row, but an EMPTY-scope row  ->   use that; it means "any scope"
       neither                              ->   undefined, and V-19 or V-23 says so

   An empty scope is not a missing value. It is a row that deliberately declines to
   distinguish, which is how a table of 84 useful rows stays 84 rather than becoming
   252 of which two thirds repeat their neighbour. */
const ANY_SCOPE = "";
const scopeOf = row => (row && row.work_scope_type) ? String(row.work_scope_type) : ANY_SCOPE;

/** The standard period weight for this project's own scope, or the any-scope row. */
function stdWeight(M, proj, periodName){
  const k = [proj.project_type, proj.clinical_phase];
  return M.pws[[...k, scopeOf(proj), periodName]]
      ?? M.pws[[...k, ANY_SCOPE, periodName]];
}

/** The role factor, the same way. 'Others' projects carry no phase, and the table
 *  stores them under a null phase, so the key is built from what the project has. */
function stdFactor(M, proj, periodName, roleName){
  const ph = CLINICAL_TYPES.has(proj.project_type) ? proj.clinical_phase : null;
  const k = [proj.project_type, ph];
  return M.rf[[...k, scopeOf(proj), periodName, roleName]]
      ?? M.rf[[...k, ANY_SCOPE, periodName, roleName]];
}

/** Which absent roles land on this one, if nobody holds them (REQ-CAL-16).
 *  The same two-step as stdFactor: the project's own scope first, then the any-scope
 *  row - so a mapping written once on the baseline covers every scope, exactly as a
 *  factor written once does. */
function absorbedInto(M, proj, periodName, roleName){
  const ph = CLINICAL_TYPES.has(proj.project_type) ? proj.clinical_phase : null;
  const k = [proj.project_type, ph];
  return M.rfAbsorb[[...k, scopeOf(proj), periodName, roleName]]
      ?? M.rfAbsorb[[...k, ANY_SCOPE, periodName, roleName]]
      ?? [];
}

function buildModel(sheets){
  const F = [];
  for (const s of REQUIRED_SHEETS){
    if (!sheets[s]) F.push({sev:"fatal", rule:"V-00", sheet:s, row:"",
      msg:`Sheet '${s}' not found. The workbook must contain all ${REQUIRED_SHEETS.length} sheets — `
        + `compare it against the delivered template.`});
  }
  if (F.some(f => f.sev === "fatal")) return {fatal:true, findings:F};

  const raw = {};
  for (const s of REQUIRED_SHEETS) raw[s] = toObjects(s, sheets[s], F);

  const M = {
    projects:{}, milestones:{}, periods:{}, people:{}, assignments:[],
    ppw:{}, pws:{}, rf:{}, rfRoles:{}, rfAbsorb:{}, lists:{}, config:{}, raw, findings:F,
  };
  for (const r of raw.Lists) if (r.list_name) (M.lists[r.list_name] ||= []).push(r.value);
  for (const r of raw.Config) if (r.parameter) M.config[r.parameter] = r.value;

  const cfg = (k, d) => { const v = num(M.config[k]); return (v === null || v === undefined) ? d : v; };
  M.OVER = cfg("over_allocation_fte", 1.50);
  M.UNDER = cfg("under_allocation_fte", 0.60);
  M.MINM = cfg("under_allocation_min_months", 3);
  M.HOURS = cfg("fte_hours_per_month", 160);
  M.HORIZON = cfg("default_horizon_months", 24);
  M.UNIT = M.config.capacity_unit || "FTE";
  /* Whether the role factor is divided between the people sharing a role. On by
     default, and a setting rather than a constant for one reason: it changes every
     figure a shared role ever produced, and somebody comparing this month's report
     with last year's needs to be able to turn it off, see the old number, and know
     that is where the difference came from. */
  M.SPLIT = cfg("split_shared_role_fte", 1) !== 0;
  /* Whether an unstaffed role's factor is absorbed by the role named to cover for it.
     A setting for the same reason SPLIT is one: it moves every figure on a project
     that is not fully staffed, and somebody comparing against last year's report has
     to be able to turn it off and see where the difference came from. */
  M.ABSORB = cfg("absorb_unstaffed_role_factor", 1) !== 0;

  const sv = num(M.config.schema_version);
  if (sv === null) F.push({sev:"warning", rule:"V-09", sheet:"Config", row:"",
    msg:`No schema_version in Config. Treating this file as version 1; columns added since may be missing.`});
  else if (sv !== SCHEMA_EXPECTED) F.push({sev:"warning", rule:"V-09", sheet:"Config", row:"",
    msg:`This file is schema version ${sv}; this application expects version ${SCHEMA_EXPECTED}. `
      + (sv < SCHEMA_EXPECTED ? `Columns added since version ${sv} may be missing.`
                              : `Columns added after version ${SCHEMA_EXPECTED} will be ignored — consider updating the application.`)});

  for (const p of raw.Project){
    if (!hasKey("Project", p)){ noKey(F, "Project", p, "project_id", "milestones and periods"); continue; }
    if (M.projects[p.project_id]) F.push({sev:"error", rule:"V-08", sheet:"Project", row:p.__row,
      msg:`project_id ${p.project_id} appears more than once.`});
    M.projects[p.project_id] = p;
  }
  for (const p of raw.Person){
    if (!hasKey("Person", p)){ noKey(F, "Person", p, "person_id", "assignments"); continue; }
    if (M.people[p.person_id]) F.push({sev:"error", rule:"V-08", sheet:"Person", row:p.__row,
      msg:`person_id ${p.person_id} appears more than once.`});
    M.people[p.person_id] = p;
  }
  for (const m of raw.Milestone){
    if (!m.project_id || !m.milestone_name || !m.milestone_date) continue;   // incomplete
    ((M.milestones[m.project_id] ||= {})[m.milestone_name] ||= []).push(m.milestone_date);
  }
  for (const k of Object.keys(M.milestones))
    for (const n of Object.keys(M.milestones[k])) M.milestones[k][n].sort((a,b)=>a-b);

  /* Schema 6: both standards tables are keyed on the WORK SCOPE as well.
     A row whose work_scope_type is EMPTY applies to EVERY scope. That is what keeps the
     tables a size a person can actually fill: PeriodWeightStandard would otherwise need
     one row per scope for every type, phase and period - 252 rows, of which two thirds
     would repeat their neighbour. So a project asks for its own scope first and falls
     back to the empty row, and only the scopes that really change a number need a row.
     The rule lives in stdWeight/stdFactor, once, so the calculation and the two
     validations cannot come to different conclusions about the same project. */
  for (const r of raw.PeriodWeightStandard)
    M.pws[[r.project_type, r.clinical_phase, scopeOf(r), r.period_name]] = num(r.weight);
  for (const r of raw.RoleFactor){
    M.rf[[r.project_type, r.clinical_phase, scopeOf(r), r.period_name, r.role_name]]
      = num(r.role_factor);
    (M.rfRoles[r.project_type] ||= new Set()).add(r.role_name);
    /* Who covers for this role when nobody holds it (REQ-CAL-16). Indexed the other
       way round - by the ABSORBING role - because that is the question the calculation
       asks: standing on the lead data manager, which absent roles land on me? */
    if (r.absorbed_by)
      (M.rfAbsorb[[r.project_type, r.clinical_phase, scopeOf(r), r.period_name,
                   r.absorbed_by]] ||= []).push(r.role_name);
  }

  // ---- periods: use what is in the file; derive where a trial has none -------
  for (const r of raw.ProjectPeriod){
    if (r.__new && !r.period_name) continue;
    (M.periods[r.project_id] ||= []).push(r);
  }
  for (const [pid, proj] of Object.entries(M.projects)){
    if (!M.periods[pid] && CLINICAL_TYPES.has(proj.project_type)){
      const derived = derivePeriods(proj, M.milestones[pid] || {});
      if (derived){
        M.periods[pid] = derived.map(d => ({...d, project_id:pid, __derived:true,
          weight: stdWeight(M, proj, d.period_name) ?? 1.00}));
      } else {
        F.push({sev:"error", rule:"V-16", sheet:"Project", row:proj.__row,
          msg:`Project ${pid} has no periods and cannot derive them — it is missing CTA submission `
            + `or a DB lock. Enter its periods by hand or add the milestone.`});
      }
    }
  }
  for (const k of Object.keys(M.periods)) M.periods[k].sort((a,b) => a.period_seq - b.period_seq);

  validate(M, F);
  recomputeDerived(M, F);
  return M;
}

/** Spec sheet 03, "derived columns — read, do not trust".
 *  The template holds a formula, but an exported or hand-edited file may not, and the
 *  cached result of a formula that was never calculated is empty. So: compare what the
 *  file says (V-13 reports a mismatch), then let the master value win. */
function recomputeDerived(M, F){
  for (const m of M.raw.Milestone){
    const master = (M.projects[m.project_id] || {}).project_name ?? null;
    if (m.project_name && master && m.project_name !== master)
      F.push({sev:"warning", rule:"V-13", sheet:"Milestone", row:m.__row,
        msg:`Milestone row ${m.__row} records project_name '${m.project_name}' but `
          + `${m.project_id} is '${master}'. The master value is used.`});
    m.project_name = master;
  }
  for (const a of M.raw.Assignment) a.person_name = (M.people[a.person_id] || {}).person_name ?? null;
  for (const p of M.raw.Project){
    if (p.start_date && p.end_date)
      p.total_period_months = (p.end_date.getUTCFullYear() - p.start_date.getUTCFullYear()) * 12
        + (p.end_date.getUTCMonth() - p.start_date.getUTCMonth()) + 1;
  }
}

function validate(M, F){
  const add = (sev, rule, sheet, row, msg) => F.push({sev, rule, sheet, row, msg});

  // V-04, V-05, V-10, V-11, V-19 on projects
  for (const [pid, p] of Object.entries(M.projects)){
    const isCT = CLINICAL_TYPES.has(p.project_type);
    if (p.start_date && p.end_date && p.end_date < p.start_date)
      add("error","V-05","Project",p.__row,
        `Project ${pid}: end_date ${ymd(p.end_date)} is before start_date ${ymd(p.start_date)}.`);
    if (isCT && !p.project_category)
      add("warning","V-04","Project",p.__row,`Project ${pid} is a clinical trial with no product category.`);
    if (isCT && !p.clinical_phase)
      add("error","V-19","Project",p.__row,
        `Project ${pid} is a clinical trial with no clinical_phase, so its periods cannot be weighted.`);
    if (isCT) for (const c of ["EDC_setup","DataReviewSystem_setup","RBQM_setup"])
      if (p[c] === null) add("warning","V-10","Project",p.__row,`Project ${pid} has no ${c} recorded.`);
    for (const [col,list] of [["project_type","project_type"],
                              ["work_scope_type","work_scope_type"],
                              ["status","project_status"],["clinical_phase","clinical_phase"]]){
      const v = p[col];
      if (v && M.lists[list] && !M.lists[list].includes(v))
        add("warning","V-11","Project",p.__row,
          `Project ${pid}: ${col} '${v}' is not a known value. Valid: ${M.lists[list].join(", ")}.`);
    }
    /* V-26: the value schema 6 retired. Reported as itself rather than as a generic
       unknown value, because the remedy is a choice the file cannot make on the user's
       behalf - only they know whether the trial ran in healthy volunteers or in
       patients, and guessing would put a wrong weight on real work. */
    if (RETIRED_TYPES[p.project_type])
      add("error","V-26","Project",p.__row,
        `Project ${pid}: project_type '${p.project_type}' was split in schema 6. Change it to `
        + `${RETIRED_TYPES[p.project_type]} — and change the matching rows on `
        + `PeriodWeightStandard and RoleFactor too.`);
    /* V-25 was here, and is RETIRED at schema 7. It reported a project whose
       outsourcing_type contradicted its work_scope_type - a check that existed only
       because two columns sat on the same axis and just one of them drove the weights.
       outsourcing_scope_det is free text now: there is nothing left to contradict, and
       a rule that can no longer fire is a rule to remove rather than to leave standing
       and unexplained. */
  }

  // V-11 / V-20 / V-21 on milestones
  for (const [pid, mm] of Object.entries(M.milestones)){
    for (const [nm, dates] of Object.entries(mm)){
      if (M.lists.milestone_name && !M.lists.milestone_name.includes(nm))
        add("warning","V-11","Milestone","",`Project ${pid}: milestone '${nm}' is not in the standard list.`);
      if (nm !== "Inspection" && dates.length > 1)
        add("warning","V-20","Milestone","",
          `Project ${pid} records '${nm}' ${dates.length} times. Only 'Inspection' is expected to repeat.`);
    }
    const lock = (mm["final DB lock"] || mm["interim DB lock"] || [])[0];
    if (lock){
      const early = (mm["Inspection"] || []).filter(d => d <= lock);
      if (early.length) add("information","V-21","Milestone","",
        `Project ${pid}: ${early.length} Inspection date(s) on or before the final DB lock are treated `
        + `as markers inside the existing periods and do not open the final period.`);
    }
    // V-14, documented in the plan from v1.0 and reported from here on: a milestone
    // outside its project's own window, and the boundary milestones out of order. The
    // derivation reads them in sequence, so a swapped pair silently produces periods
    // nobody meant - which is a wrong answer rather than a visible gap.
    const proj = M.projects[pid];
    if (proj && proj.start_date && proj.end_date){
      for (const [nm, dates] of Object.entries(mm)) for (const dt of dates){
        if (dt >= proj.start_date && dt <= proj.end_date) continue;
        // An Inspection after the final DB lock is the one milestone MEANT to sit past
        // the project end: it opens 'After Close-out (final)' and the derivation extends
        // the timeline to reach it (V-21). Calling that 'outside the window' would be wrong.
        if (nm === "Inspection" && lock && dt > lock){
          add("information","V-14","Milestone","",
            `Project ${pid}: Inspection on ${ymd(dt)} falls after the project end `
            + `${ymd(proj.end_date)}; the timeline is extended to cover it and `
            + `'After Close-out (final)' runs to that date.`);
          continue;
        }
        add("warning","V-14","Milestone","",
          `Project ${pid}: '${nm}' on ${ymd(dt)} falls outside the project window `
          + `${ymd(proj.start_date)}..${ymd(proj.end_date)}.`);
      }
    }
    for (const [n1, n2] of MILESTONE_ORDER){
      if (!(mm[n1] && mm[n1].length && mm[n2] && mm[n2].length)) continue;
      const d1 = mm[n1][0], d2 = mm[n2][0];
      if (d2 >= d1) continue;
      // Out of order between milestones the derivation hangs on is an error; between
      // two markers it is a data-entry slip worth listing.
      add(DERIVATION_MILESTONES.has(n1) || DERIVATION_MILESTONES.has(n2)
          ? "error" : "warning","V-14","Milestone","",
        `Project ${pid}: '${n2}' (${ymd(d2)}) is before '${n1}' (${ymd(d1)}); the period `
        + `derivation reads these in order.`);
    }
  }

  // V-06, V-12, V-15, V-18 on periods
  for (const [pid, proj] of Object.entries(M.projects)){
    const segs = M.periods[pid];
    if (!segs || !segs.length){
      if (!F.some(f => f.rule === "V-16" && String(f.msg).includes(pid)))
        add("error","V-12","ProjectPeriod","",`Project ${pid} has no periods.`);
      continue;
    }
    const allowed = CLINICAL_TYPES.has(proj.project_type) ? CLINICAL_PERIODS : OTHER_PERIODS;
    const names = segs.map(s => s.period_name);
    for (const n of new Set(names)) if (names.filter(x => x === n).length > 1)
      add("error","V-18","ProjectPeriod","",
        `Project ${pid}: period_name '${n}' appears ${names.filter(x=>x===n).length} times; `
        + `(project_id, period_name) must be unique.`);
    const seqs = segs.map(s => s.period_seq);
    if (new Set(seqs).size !== seqs.length)
      add("error","V-18","ProjectPeriod","",`Project ${pid}: period_seq is duplicated.`);
    let prevEnd = null;
    for (const s of segs){
      if (!allowed.includes(s.period_name))
        add("error","V-15","ProjectPeriod","",
          `Project ${pid} is type '${proj.project_type}' but has a period named '${s.period_name}'. `
          + `Valid: ${allowed.join(", ")}.`);
      if (s.period_end < s.period_start)
        add("error","V-05","ProjectPeriod","",`Project ${pid} period ${s.period_seq}: end before start.`);
      if (prevEnd){
        const gap = Math.round((s.period_start - prevEnd) / DAY);
        if (gap > 1) add("warning","V-12","ProjectPeriod","",
          `Project ${pid}: ${gap-1} day(s) before period ${s.period_seq} belong to no period. `
          + `Those months are calculated at weight 1.00.`);
        else if (gap < 1) add("error","V-06","ProjectPeriod","",
          `Project ${pid}: periods overlap at ${s.period_name}.`);
      }
      prevEnd = s.period_end;
      if (CLINICAL_TYPES.has(proj.project_type) && proj.clinical_phase &&
          stdWeight(M, proj, s.period_name) === undefined)
        add("error","V-19","PeriodWeightStandard","",
          `Project ${pid}: no standard weight for ${proj.project_type} / ${proj.clinical_phase} / `
          + `${proj.work_scope_type || "any scope"} / ${s.period_name}. Add a row for that scope, `
          + `or one with work_scope_type empty to cover every scope.`);
    }
  }

  // V-01, V-02, V-03, V-07, V-08, V-13 on assignments
  const seen = new Set();
  for (const a of M.raw.Assignment){
    // A row the user is still creating is INCOMPLETE, not invalid (spec sheet 07). It
    // starts being checked once it carries an identifier.
    if (a.__new && !a.assignment_id) continue;
    // Saved without one, it is the same broken record as a project without a project_id:
    // no override can attach to it, and it cannot survive a round trip.
    if (!hasKey("Assignment", a)){ noKey(F, "Assignment", a, "assignment_id", "weight overrides"); continue; }
    if (seen.has(a.assignment_id))
      add("error","V-08","Assignment",a.__row,`assignment_id ${a.assignment_id} appears more than once.`);
    seen.add(a.assignment_id);
    const proj = M.projects[a.project_id];
    if (!proj){
      add("error","V-01","Assignment",a.__row,
        `Assignment ${a.assignment_id} refers to project ${a.project_id}, which does not exist.`);
      continue;
    }
    if (!M.people[a.person_id])
      add("error","V-02","Assignment",a.__row,
        `Assignment ${a.assignment_id} refers to person ${a.person_id}, which does not exist.`);
    const roles = M.rfRoles[proj.project_type];
    if (!roles || !roles.has(a.role_name))
      add("error","V-03","Assignment",a.__row,
        `Assignment ${a.assignment_id}: role '${a.role_name}' is not valid for a project of type `
        + `'${proj.project_type}'. Valid roles for this type: ${roles ? [...roles].join(", ") : "none defined"}.`);
    if (a.assign_end_date && a.assign_start_date && a.assign_end_date < a.assign_start_date)
      add("error","V-05","Assignment",a.__row,`Assignment ${a.assignment_id}: end before start.`);
    if (proj.end_date && a.assign_end_date && a.assign_end_date > proj.end_date)
      add("warning","V-07","Assignment",a.__row,
        `Assignment ${a.assignment_id} runs to ${ymd(a.assign_end_date)}, after project ${a.project_id} `
        + `ends on ${ymd(proj.end_date)}.`);
    const per = M.people[a.person_id];
    if (per && a.person_name && a.person_name !== per.person_name)
      add("warning","V-13","Assignment",a.__row,
        `Assignment ${a.assignment_id} records person_name '${a.person_name}' but ${a.person_id} is `
        + `'${per.person_name}'. The master value is used.`);
    // (recomputeDerived then overwrites it with the master — see spec sheet 03.)
    M.assignments.push(a);
  }

  // V-06 + V-24 on override windows: this is a child table of windows, and one
  // assignment may carry several. Both halves of that need a rule.
  for (const w of M.raw.PersonPeriodWeight){
    if (w.__new && !w.period_start) continue;
    (M.ppw[w.assignment_id] ||= []).push(w);
  }
  for (const [aid, wins] of Object.entries(M.ppw)){
    if (!seen.has(aid)){
      add("error","V-24","PersonPeriodWeight","",
        `${aid}: PersonPeriodWeight refers to an assignment that does not exist; its override is `
        + `silently ignored.`);
      continue;
    }
    wins.sort((a,b) => a.period_start - b.period_start);
    const starts = wins.map(w => +w.period_start);
    if (new Set(starts).size !== starts.length)
      add("error","V-24","PersonPeriodWeight","",
        `${aid}: two override windows share a period_start; (assignment_id, period_start) must be unique.`);
    for (let i = 1; i < wins.length; i++)
      if (wins[i].period_start <= wins[i-1].period_end)
        add("error","V-06","PersonPeriodWeight","",
          `${aid}: override windows overlap — ${ymd(wins[i-1].period_start)}..${ymd(wins[i-1].period_end)} `
          + `and ${ymd(wins[i].period_start)}..${ymd(wins[i].period_end)}. Which weight applies in the `
          + `shared months would depend on row order.`);
    for (const w of wins) if (w.period_end < w.period_start)
      add("error","V-05","PersonPeriodWeight","",`${aid}: override window ends before it starts.`);
  }

  // V-22: an absolute floor only means something if everyone can reach it
  for (const [sid, p] of Object.entries(M.people)){
    const cap = num(p.capacity_fte);
    if (cap !== null && cap !== undefined && cap < M.UNDER)
      add("warning","V-22","Person",p.__row,
        `${sid}: capacity ${cap.toFixed(2)} FTE is below the under-allocation floor of `
        + `${M.UNDER.toFixed(2)}, so this person can never clear it however fully they are booked.`);
  }

  /* ---- V-27: the assumption block for this project simply is not there ----
     V-19 is precise: it names the period, and it only looks at periods a project
     actually has. That leaves a gap at both ends. A project whose milestones are
     missing has NO periods, so V-19 does not look at it at all - and a project whose
     (type, phase, scope) combination was never entered in the assumptions is reported
     once per period rather than once, as the one thing that is wrong.

     This asks the blunter question first, on the PROJECT rather than on its periods:
     is there any standard for this project at all. It fires where V-19 cannot, and
     where both can, it says the useful sentence.

     V-28 stood here and asked the same question of the roles on the assignments. It is
     RETIRED at v2.32 - see the note below. */
  for (const [pid, proj] of Object.entries(M.projects)){
    if (!CLINICAL_TYPES.has(proj.project_type)) continue;      // 'Others' take manual weights
    if (!proj.clinical_phase) continue;                        // V-19 has already said so
    const any = (M.lists.period_name_clinical || CLINICAL_PERIODS)
      .some(pn => stdWeight(M, proj, pn) !== undefined);
    if (!any)
      add("error","V-27","PeriodWeightStandard",proj.__row,
        `Project ${pid} is ${proj.project_type} / ${proj.clinical_phase} / `
        + `${proj.work_scope_type || "any scope"}, and PeriodWeightStandard has NO rows for `
        + `that combination at all — not for any period. Every period of this project would `
        + `be weighted 1.00. Add the rows, or add ones with work_scope_type empty to cover `
        + `every scope.`);
  }

  /* V-28 is RETIRED at v2.32, and deliberately not reimplemented at any severity.
     It reported an assignment whose role had no RoleFactor row for the project's
     (project_type, clinical_phase, work_scope_type) at all. Everything it said was
     true. What it did not account for is WHEN it said it: an error refuses the edit
     that raised it (REQ-IMP-09), and unlike V-23 this one did not need the project to
     have any periods, so it fired on a project still being built - one whose milestones
     had not been entered yet, which is exactly when somebody is typing assignments in.
     The user then could not record who is on the project until the assumptions carried
     a factor for their role, which is backwards: the plan is the thing being written,
     and the assumptions are a standing document maintained separately.

     The gap it filled is real and is not being denied - a role with no factor is
     calculated at 1.00. V-03 still refuses a role that is not valid for the project
     type, and V-23 still reports a role with no factor for a period the project spans,
     which is the same finding at the point where it can be acted on. The id is not
     reused. */

  /* V-29: a role that has a factor, that nobody holds, and that nothing covers for.
     The direct consequence of REQ-CAL-16, and the reason it is worth reporting: the
     absorption rule exists because an unstaffed role makes a project look cheaper than
     it is. Where the role names somebody to cover, the figure is corrected. Where it
     names nobody, the same under-estimate is still there and nothing else would say
     so. Information rather than a warning: a project legitimately without a role is
     ordinary, and this is a note about what the figures do not include. */
  if (M.ABSORB) for (const [pid, proj] of Object.entries(M.projects)){
    const ph = CLINICAL_TYPES.has(proj.project_type) ? proj.clinical_phase : null;
    const held = new Set(M.assignments.filter(a => a.project_id === pid)
                                      .map(a => a.role_name));
    if (!held.size) continue;                       // nobody at all: V-08 covers that
    const periods = CLINICAL_TYPES.has(proj.project_type)
      ? (M.lists.period_name_clinical || CLINICAL_PERIODS)
      : (M.lists.period_name_others || OTHER_PERIODS);
    const roles = M.rfRoles[proj.project_type] || new Set();
    for (const role of roles){
      if (held.has(role)) continue;
      const pn = periods.find(x => stdFactor(M, proj, x, role) !== undefined);
      if (pn === undefined) continue;               // no factor: nothing is being lost
      const absorber = M.raw.RoleFactor.find(r =>
        r.role_name === role && r.project_type === proj.project_type && r.absorbed_by);
      if (absorber && held.has(absorber.absorbed_by)) continue;   // covered for
      add("information","V-29","RoleFactor","",
        `Project ${pid} has nobody in the role '${role}', which carries a factor for `
        + `${proj.project_type} / ${ph || "-"} / ${proj.work_scope_type || "any scope"}. `
        + (absorber
            ? `RoleFactor says ${absorber.absorbed_by} would cover it, but nobody holds that `
              + `role here either, so the work is not counted anywhere.`
            : `Nothing on RoleFactor names a role to cover for it, so its share of the work `
              + `is not counted. Set absorbed_by if somebody really picks it up.`));
    }
  }

  // V-23: a role factor missing for a period an assignment actually spans
  const need = new Map();
  for (const a of M.assignments){
    const proj = M.projects[a.project_id];
    if (!proj || !M.people[a.person_id]) continue;
    for (const s of (M.periods[a.project_id] || []))
      need.set([proj.project_type, proj.clinical_phase, scopeOf(proj), s.period_name,
                a.role_name].join(""), [proj, s.period_name, a.role_name]);
  }
  for (const [, [proj, pn, role]] of need){
    if (stdFactor(M, proj, pn, role) !== undefined) continue;
    const ph = CLINICAL_TYPES.has(proj.project_type) ? proj.clinical_phase : null;
    add("error","V-23","RoleFactor","",
      `No role factor for ${proj.project_type} / ${ph || "-"} / `
      + `${proj.work_scope_type || "any scope"} / ${pn} / ${role} — assignments covering that `
      + `period would be calculated at factor 1.00. Add a row for that scope, or one with `
      + `work_scope_type empty to cover every scope.`);
  }
}

