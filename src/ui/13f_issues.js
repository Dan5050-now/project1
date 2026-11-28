/* ======================================================= the Data issues tab (R-69)

   WHAT IS WRONG WITH THE PLAN, IN ONE PLACE, WITH THE WAY TO PUT IT RIGHT.

   Every rule the plan is checked against already reports - into M.findings, rebuilt on
   every edit - and until now the reports reached the reader as one line in a banner
   ("3 errors, 14 warnings") and a modal table to read and close. Reading is half the
   job. The other half is getting to the row, which meant knowing which tab it is on,
   finding it there, and remembering what was wrong with it by the time you did.

   So the findings are a worklist here:

     LEVEL      what the application does about it: MUST FIX is refused until it is
                corrected, MAY KEEP is asked about at Save, a WARNING never stops
                anything, STILL TO COME answers itself, a NOTE is for information.
     CATEGORY   which part of the plan it is about.
     RECORD     the project, person or assumption table it is on - a link to the card.

   sortable and groupable by any of them, narrowed by level, category or a search, and
   each with its fix underneath it: the very row it is about, editable where it stands
   through the same cells as everywhere else - so the same value lists, validation,
   change log and Save - and, where the application already has one, the one-step fix:
   derive the periods, lay out the standard milestones, switch a figure back to
   automatic, review the months a project is off its standard.

   AND A DECISION, where a decision is what is wanted. A warning is not a fault - it is
   the application pointing at something that may well be deliberate - and a list that
   cannot be worked down is a list nobody reads twice. ACCEPT takes an issue out of the
   open count: in this session at once, and into the change log with the next Save, as
   kept_by_user, which is the line an audit trail exists for. It is a decision about
   THESE figures: the issue comes back if what it says changes, and when the plan is
   opened again. A must-fix cannot be accepted - the application refuses it, and so
   would the file.

   NOT NARROWED BY THE FILTERS. They choose what the page shows; an issue is in the file
   whatever the page is showing, and a list of problems that quietly left some out would
   be worse than none. Allocation is the one category the findings do not carry, so it is
   worked out here, from the same thresholds as the Overall tiles - from this month on,
   because a month that has gone by is history, not something to fix. */

const ISSUE_LEVELS = [
  {id:"must", label:"Must fix", help:"Something is wrong with the row itself. An edit that "
    + "would cause one is refused, and Save is held while one stands — correct it."},
  {id:"keep", label:"May keep", help:"The row is sound, but something it depends on is "
    + "missing, so the figures that need it are short an assumption. Save asks before "
    + "keeping it; going ahead is your decision."},
  {id:"warn", label:"Warning", help:"Probably not what was meant, or worth knowing before "
    + "the plan is used. It never refuses anything."},
  {id:"soon", label:"Still to come", help:"A row that is not finished yet. It answers itself "
    + "as you carry on entering, and never refuses or asks."},
  {id:"note", label:"Note", help:"For information: what the application did with something "
    + "in the file, or a figure worth knowing."},
];
const ISSUE_CATS = [
  {id:"proj", label:"Projects", help:"A project, its milestones or its periods."},
  {id:"pers", label:"People & assignments", help:"A person, an assignment or a weight override."},
  {id:"std",  label:"Standard vs staffed", help:"A project not given what its own standard "
    + "says it needs (V-34, V-36), and reviews that no longer describe their month (V-40)."},
  {id:"load", label:"Allocation", help:"A person above the ceiling, or below the floor for a "
    + "run of months, from this month on — against the thresholds in Configuration."},
  {id:"fig",  label:"Stated figures", help:"A monthly figure entered by hand that could not be "
    + "applied as it stands (V-31 – V-33)."},
  {id:"asm",  label:"Assumptions", help:"The standards, role factors, colours, value lists and "
    + "settings on General assumptions."},
  {id:"book", label:"Workbook", help:"The file itself — its sheets and its schema version."},
];
const ISSUE_LV = Object.fromEntries(ISSUE_LEVELS.map((l, i) => [l.id, {...l, rank:i}]));
const ISSUE_CAT = Object.fromEntries(ISSUE_CATS.map((c, i) => [c.id, {...c, rank:i}]));
const ISSUE_GROUPS = [["level", "Level"], ["cat", "Category"], ["rec", "Record"], ["none", "None"]];

const ISSUE_SHEET_CAT = {
  Project:"proj", Milestone:"proj", ProjectPeriod:"proj",
  Person:"pers", Assignment:"pers", PersonPeriodWeight:"pers",
  MonthlyEstimate:"fig",
  PeriodFTEStandard:"asm", RoleFactor:"asm", Lists:"asm", Config:"asm", PeriodHighlight:"asm",
  PeriodRule:"asm",
};
/* The field a rule is about, where its message does not name the column itself - the
   editor puts these first and marks them. Every other rule names its column in so many
   words, and the message is searched for it. */
const ISSUE_FOCUS = {
  "V-01":["project_id"], "V-02":["person_id"], "V-03":["role_name"],
  "V-04":["project_category"], "V-07":["assign_end_date"],
  "V-05":["start_date", "end_date", "assign_start_date", "assign_end_date",
          "period_start", "period_end"],
  "V-06":["period_start", "period_end"], "V-15":["period_name"],
  "V-18":["period_name", "period_seq"], "V-19":["clinical_phase"], "V-26":["project_type"],
  "V-22":["capacity_fte"], "V-35":["capacity_fte"],
  "V-37":["milestone_highlight"], "V-38":["period_highlight"],
};
/* Which columns say WHICH row it is, kept beside the focus columns in a wide sheet. */
const ISSUE_IDENT = {
  Project:["project_id", "project_name"], Person:["person_id", "person_name"],
  Assignment:["assignment_id", "project_id", "person_id", "role_name"],
};
/* Where on General assumptions each assumption sheet is changed. */
const ISSUE_GEN_PANEL = {
  PeriodFTEStandard:["gen-pws", "Standard period FTE"], RoleFactor:["gen-rf", "Role factors"],
  PeriodHighlight:["gen-phl", "Period colours"], Config:["gen-cfg", "Configuration"],
  PeriodRule:["gen-prule", "Period derivation rules"],
  Lists:["gen-lists", "Value lists"],
};

function issueLevel(f){
  if (f.lv) return f.lv;
  if (f.sev === "fatal") return "must";
  if (f.sev === "error") return {conditional:"keep", incomplete:"soon"}[ruleClass(f.rule)] || "must";
  return f.sev === "warning" ? "warn" : "note";
}

function issueCat(f){
  if (f.load) return "load";
  if (f.rule === "V-34" || f.rule === "V-36" || f.rule === "V-40") return "std";
  if (f.sev === "fatal" || f.rule === "V-09") return "book";
  return ISSUE_SHEET_CAT[f.sheet] || "book";
}

/* ------------------------------------------------------------- which record it is on */

/** Every project, person and assignment identifier in the plan, as one expression that
 *  finds them in a message - longest first, and only as whole identifiers, so PRJ-01 is
 *  never read out of PRJ-010. Built once per model. */
let ISSUE_IDX = null;
function issueIdIndex(){
  const M = S.model;
  if (ISSUE_IDX && ISSUE_IDX.model === M) return ISSUE_IDX;
  const kind = new Map();
  for (const id of Object.keys(M.projects)) kind.set(id, "project");
  for (const id of Object.keys(M.people)) if (!kind.has(id)) kind.set(id, "person");
  for (const a of M.raw.Assignment || []){
    const id = a.assignment_id === null || a.assignment_id === undefined ? "" : String(a.assignment_id);
    if (id && !kind.has(id)) kind.set(id, "assignment");
  }
  const ids = [...kind.keys()].filter(Boolean).sort((a, b) => b.length - a.length)
    .map(s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = ids.length ? new RegExp(`(?<![\\w-])(${ids.join("|")})(?![\\w-])`, "g") : null;
  return (ISSUE_IDX = {model: M, kind, re});
}

/** The row a finding names, where it names one. V-27 is reported against the PROJECT's
 *  row number on the standards sheet, so its row number is not a row of that sheet. */
function issueRow(f){
  if (!f.sheet || !(f.row > 0) || f.rule === "V-27" || f.load) return null;
  const rows = S.model.raw[f.sheet];
  return rows ? rows.find(r => r.__row === f.row) || null : null;
}

/** The projects, people and assignments an issue is about: off the row it names, and out
 *  of its message - "Assignment ASG-014 refers to project PRJ-022" is about both. Only
 *  records that exist can be opened, so an identifier that names nothing is left out. */
function issueRecords(it){
  const M = S.model, out = {project:[], person:[], assignment:[]};
  const put = (k, id) => {
    if (id === null || id === undefined || id === "") return;
    const s = String(id);
    if (out[k] && !out[k].includes(s)) out[k].push(s);
  };
  if (it.sid) put("person", it.sid);
  const r = it.raw;
  if (r){
    if (it.sheet === "Project") put("project", r.project_id);
    else if (it.sheet === "Person") put("person", r.person_id);
    else {
      put("assignment", r.assignment_id);
      put("project", r.project_id);
      put("person", r.person_id);
    }
  }
  const X = issueIdIndex();
  if (X.re) for (const m of it.msg.matchAll(X.re)) put(X.kind.get(m[1]), m[1]);
  for (const aid of out.assignment){
    const a = (M.raw.Assignment || []).find(x => String(x.assignment_id) === aid);
    if (a){ put("project", a.project_id); put("person", a.person_id); }
  }
  out.project = out.project.filter(id => M.projects[id]);
  out.person = out.person.filter(id => M.people[id]);
  return out;
}

/** What an issue is grouped under in "Record": its project, else its person, else the
 *  sheet - an assumption table is a record of its own. */
function issueHome(it){
  const M = S.model;
  if (it.rec.project.length){
    const id = it.rec.project[0];
    return {kind:"project", id, label: M.projects[id].project_name || id};
  }
  if (it.rec.person.length){
    const id = it.rec.person[0];
    return {kind:"person", id, label: M.people[id].person_name || id};
  }
  const s = it.sheet && it.sheet !== "Workbook" ? (SECTION[it.sheet] || it.sheet) : "The workbook";
  return {kind:"sheet", id: it.sheet || "", label: s};
}

/** The first sentence, which is what the rule found; the rest - why it matters and what
 *  to do - is under it, opened. */
function issueHead(msg){
  const s = String(msg).replace(/\s+/g, " ").trim();
  const m = s.match(/^(.+?[.!?])(?=\s+[A-Z(‘'"“]|$)/);
  let h = m ? m[1] : s;
  if (h.length > 210) h = h.slice(0, 196).replace(/\s+\S*$/, "") + " …";
  return h;
}

function issueHash(s){
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++){ h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return (h >>> 0).toString(36);
}

/* ------------------------------------------------------------- allocation */

/** Months as runs: "Jan 2027 – Jun 2027, Sep 2027". */
function monthRuns(ks){
  const out = [];
  for (let i = 0; i < ks.length; i++){
    let j = i;
    while (j + 1 < ks.length && ks[j + 1] === ks[j] + 1) j++;
    out.push(i === j ? keyToLabel(ks[i]) : `${keyToLabel(ks[i])} – ${keyToLabel(ks[j])}`);
    i = j;
  }
  return out;
}

/** A person above the ceiling, and a person below the floor for a run of months -
 *  measured the way the Overall tiles measure them (absolute thresholds, a month at
 *  nothing ending a run), over every month from this one to the end of the plan. One
 *  issue per person for each, with the months named inside it. */
function loadIssues(){
  const M = S.model, C = S.calc, out = [];
  if (!C || !C.persMonth) return out;
  const from = Math.max(nowKey(), C.lo), to = C.hi;
  if (!(to >= from)) return out;
  for (const [sid, p] of Object.entries(M.people)){
    const name = p.person_name || sid, over = [], runs = [];
    let run = null, peak = 0, peakK = null;
    const close = () => { if (run && run.b - run.a + 1 >= M.MINM) runs.push(run); run = null; };
    for (let k = from; k <= to; k++){
      const v = C.persMonth.get(sid + "|" + k) || 0;
      if (v > M.OVER){
        over.push(k);
        if (v > peak){ peak = v; peakK = k; }
      }
      if (v > 0 && v < M.UNDER){
        if (!run) run = {a:k, b:k, lo:v};
        else { run.b = k; run.lo = Math.min(run.lo, v); }
      } else close();
    }
    close();
    if (over.length){
      const shown = monthRuns(over);
      out.push({load:"over", lv:"warn", sev:"warning", rule:"Load", sheet:"Person", row:p.__row,
        sid, peakK, months: over,
        msg:`${name} is above the ${M.OVER.toFixed(2)} FTE ceiling in ${over.length} month(s) `
          + `from this month on, at ${peak.toFixed(2)} at most, in ${keyToLabel(peakK)}. `
          + `The months: ${shown.slice(0, 6).join(", ")}${shown.length > 6 ? ", …" : ""}. The `
          + `ceiling is absolute — it is not scaled by anyone's capacity — so the load comes `
          + `down by lowering a weight or shortening an assignment, below. Accept it if it is `
          + `meant.`});
    }
    if (runs.length){
      const low = Math.min(...runs.map(r => r.lo));
      out.push({load:"under", lv:"note", sev:"information", rule:"Load", sheet:"Person",
        row:p.__row, sid, peakK: runs[0].a, months: [],
        msg:`${name} is below the ${M.UNDER.toFixed(2)} FTE floor for ${runs.length} run(s) `
          + `of ${M.MINM} or more months from this month on, at ${low.toFixed(2)} at the `
          + `lowest. ${runs.slice(0, 4).map(r => `${keyToLabel(r.a)} – ${keyToLabel(r.b)} `
            + `(${r.b - r.a + 1} months)`).join(", ")}${runs.length > 4 ? ", …" : ""}. A `
          + `month with nothing in it ends a run: somebody on nothing is unassigned, not `
          + `under-allocated.`});
    }
  }
  return out;
}

/* ------------------------------------------------------------- the list itself */

let ISSUE_CACHE = null;
/** Every issue in the plan as it stands, worked out once per model - the tab, its count
 *  in the tab bar and the banner's link all ask, often in the same moment. */
function issues(){
  if (!S.model || !S.calc) return [];
  const c = ISSUE_CACHE, F = S.model.findings || [];
  if (c && c.model === S.model && c.calc === S.calc && c.n === F.length
      && c.ack === S.issueAckV && c.now === nowKey()) return c.list;
  const list = F.map(f => ({sev:f.sev, rule:f.rule, sheet:f.sheet, row:f.row,
                            msg:String(f.msg ?? ""), raw:issueRow(f)}))
    .concat(loadIssues());
  const seen = new Set();
  for (const it of list){
    it.lv = issueLevel(it);
    it.cat = issueCat(it);
    it.rec = issueRecords(it);
    it.home = issueHome(it);
    it.head = issueHead(it.msg);
    it.key = [it.rule, it.sheet, it.row, it.msg].join("\u0000");
    it.acc = S.issueAck.get(it.key) || null;
    let id = "i" + issueHash(it.key);
    while (seen.has(id)) id += "x";
    seen.add(id);
    it.id = id;
    it.sig = [it.rule, it.load || "", it.sheet, it.row, it.home.kind, it.home.id].join("|");
    it.find = [it.rule, it.msg, it.home.label, it.home.id, ISSUE_LV[it.lv].label,
               ISSUE_CAT[it.cat].label].join(" ").toLowerCase();
  }
  ISSUE_CACHE = {model:S.model, calc:S.calc, n:F.length, ack:S.issueAckV, now:nowKey(), list};
  return list;
}

/** The number on the tab: what is open and worth a look - must fix, may keep and
 *  warnings. Red while anything must be fixed. */
function issueCount(){
  const b = el("issueCount");
  if (!b) return;
  if (!S.model || !S.calc){ b.hidden = true; return; }
  const ln = el("openIssuesN");
  const open = issues().filter(it => !it.acc);
  const must = open.filter(it => it.lv === "must").length;
  const n = open.filter(it => it.lv === "must" || it.lv === "keep" || it.lv === "warn").length;
  b.hidden = !n;
  b.textContent = n;
  b.classList.toggle("must", must > 0);
  if (ln) ln.textContent = n ? ` (${n})` : "";
  b.parentNode.dataset.tip = `<b>Data issues</b><br>${n ? `${n} open: ${must} must fix, `
    + `${open.filter(it => it.lv === "keep").length} may keep, `
    + `${open.filter(it => it.lv === "warn").length} warning(s)` : "nothing that needs a look"}`
    + `<br><span class="tr">${open.length - n} still to come or noted</span>`;
}

const issueAcceptable = it => it.lv !== "must";

function issueSorter(){
  const V = S.issueView, d = V.dir;
  const by = {
    level: (a, b) => ISSUE_LV[a.lv].rank - ISSUE_LV[b.lv].rank,
    cat: (a, b) => ISSUE_CAT[a.cat].rank - ISSUE_CAT[b.cat].rank,
    rec: (a, b) => a.home.label.localeCompare(b.home.label, undefined, {numeric:true})
                   || a.home.id.localeCompare(b.home.id, undefined, {numeric:true}),
    rule: (a, b) => (parseInt(String(a.rule).slice(2), 10) || 999)
                    - (parseInt(String(b.rule).slice(2), 10) || 999),
    issue: (a, b) => a.head.localeCompare(b.head),
  };
  const first = by[V.sort] || by.level;
  return (a, b) => d * first(a, b) || by.level(a, b) || by.cat(a, b) || by.rec(a, b)
    || by.rule(a, b) || by.issue(a, b);
}

/* ------------------------------------------------------------- drawing */

function renderIssuesTab(){
  const box = el("t-issues");
  if (!box) return;
  if (!S.model){ box.innerHTML = ""; return; }
  const V = S.issueView, all = issues(), open = all.filter(it => !it.acc);
  const nLv = id => open.filter(it => it.lv === id).length;
  const nCat = id => open.filter(it => it.cat === id).length;
  const narrowed = V.lv.size || V.cat.size || V.q.trim();
  const lvChips = ISSUE_LEVELS.map(l => {
    const n = nLv(l.id), on = V.lv.has(l.id);
    return `<button type="button" class="ichip lv-${l.id}${on ? " on" : ""}${n ? "" : " zero"}" `
      + `data-iss-lv="${l.id}" aria-pressed="${on}" data-tip="${att(`<b>${l.label}</b><br>${l.help}`
        + `<br><span class="tr">click to show only these; click again to show all</span>`)}">`
      + `<span class="idot"></span>${l.label}<b>${n}</b></button>`;
  }).join("");
  const catChips = ISSUE_CATS.filter(c => nCat(c.id) || V.cat.has(c.id)).map(c => {
    const on = V.cat.has(c.id);
    return `<button type="button" class="btn tiny icat${on ? " on" : ""}" data-iss-cat="${c.id}" `
      + `aria-pressed="${on}" data-tip="${att(`<b>${c.label}</b><br>${c.help}`)}">${esc(c.label)}`
      + ` <span class="n">${nCat(c.id)}</span></button>`;
  }).join("");
  const acc = all.length - open.length;
  box.innerHTML = `<div class="panel ipanel" data-panel="iss">
      <div class="phead"><h2>Data issues</h2>
        <span class="scope">the whole plan — not narrowed by the filters</span>
        <span class="scope k">${open.length} open${acc ? ` &#183; ${acc} accepted` : ""}</span></div>
      <p class="cap">Everything the plan's checks have found, as a list to work down. Open one to read
        all of it and to put it right where it stands — the row it is about is editable right there,
        through the same checks and the same <strong>Save</strong> as everywhere else. A warning or a
        note that is deliberate can be <strong>accepted</strong>: it leaves the open count for this
        session, and the decision is written to the change log with the next Save.</p>
      <div class="ichips" role="group" aria-label="Show issues of this level">${lvChips}</div>
      <div class="itools">
        <span class="ilabel">Group by</span>
        <span class="vtog">${ISSUE_GROUPS.map(([g, t]) =>
          `<button type="button" class="btn tiny${V.group === g ? " on" : ""}" data-iss-group="${g}" `
          + `aria-pressed="${V.group === g}">${t}</button>`).join("")}</span>
        ${catChips ? `<span class="ilabel">Category</span><span class="icats">${catChips}</span>` : ""}
        <input type="search" id="issueQ" class="iq" placeholder="Search issues, records, rules…"
          aria-label="Search the issues" value="${att(V.q)}">
        ${narrowed ? `<button type="button" class="btn tiny" data-iss-clear>Show all</button>` : ""}
      </div>
      <div id="issueList">${issueListHTML()}</div>
    </div>`;
}

/** The list alone - what the search box redraws as it is typed into, so the box keeps
 *  its caret. */
function drawIssueList(){
  const l = el("issueList");
  if (l){ l.innerHTML = issueListHTML(); cueScrollers(); }
}

function issueListHTML(){
  const V = S.issueView, all = issues();
  /* The issue that was open has gone. If it has only CHANGED - a gap that is smaller now,
     a run that is shorter - it is the same issue in other words, and it stays open; if
     it has gone altogether, the fix worked, and that is worth saying. */
  if (V.open && !all.some(it => it.id === V.open)){
    const next = all.find(it => it.sig === V.openSig);
    if (next) V.open = next.id;
    else { V.done = V.openHead || "that issue"; V.open = null; }
  }
  if (!all.length)
    return `<div class="iempty"><span class="iok" aria-hidden="true">&#10003;</span>`
      + `<div><strong>No data issues.</strong> The plan passes every rule, and nobody is above `
      + `the ceiling or under the floor from this month on.</div></div>`;
  const q = V.q.trim().toLowerCase();
  const shown = all.filter(it => (!V.lv.size || V.lv.has(it.lv))
    && (!V.cat.size || V.cat.has(it.cat)) && (!q || it.find.includes(q)));
  const done = V.done ? `<p class="idone" role="status">&#10003; <strong>Resolved</strong> — `
    + `${esc(V.done)}</p>` : "";
  if (!shown.length)
    return done + `<div class="iempty"><div>No issue matches what is chosen above. `
      + `<button type="button" class="btn tiny" data-iss-clear>Show all</button></div></div>`;
  const sort = issueSorter();
  const open = shown.filter(it => !it.acc).sort(sort), acc = shown.filter(it => it.acc).sort(sort);
  const groups = [];
  if (V.group === "none") groups.push([null, open]);
  else {
    const keyOf = V.group === "level" ? it => it.lv : V.group === "cat" ? it => it.cat
      : it => it.home.kind + "|" + it.home.id;
    const by = new Map();
    for (const it of open){
      const k = keyOf(it);
      if (!by.has(k)) by.set(k, []);
      by.get(k).push(it);
    }
    const order = V.group === "level" ? (a, b) => ISSUE_LV[a].rank - ISSUE_LV[b].rank
      : V.group === "cat" ? (a, b) => ISSUE_CAT[a].rank - ISSUE_CAT[b].rank
      : (a, b) => {
          const x = by.get(a)[0].home, y = by.get(b)[0].home;
          const r = k => k.kind === "project" ? 0 : k.kind === "person" ? 1 : 2;
          return r(x) - r(y) || x.label.localeCompare(y.label, undefined, {numeric:true});
        };
    for (const k of [...by.keys()].sort(order)) groups.push([k, by.get(k)]);
  }
  if (acc.length) groups.push(["__acc", acc]);
  const arrow = c => V.sort === c ? `<span class="sarr">${V.dir > 0 ? "&#9650;" : "&#9660;"}</span>` : "";
  const th = (c, t, cls) => `<th class="${cls || ""}" aria-sort="${V.sort === c ? (V.dir > 0
      ? "ascending" : "descending") : "none"}"><button type="button" class="isort" data-iss-sort="${c}">`
    + `${t}${arrow(c)}</button></th>`;
  return done + `<div class="scrollx free"><table class="isst">
    <thead><tr>${th("level", "Level", "ilv")}${th("cat", "Category", "icat-h")}
      ${th("rec", "Record", "irec")}${th("issue", "Issue", "ihead")}${th("rule", "Rule", "irule")}
      <th class="iact"></th></tr></thead>
    ${groups.map(([k, rows]) => `<tbody>${k === null ? "" : issueGroupHead(k, rows)}`
      + rows.map(issueRowHTML).join("") + `</tbody>`).join("")}
  </table></div>`;
}

function issueGroupHead(k, rows){
  const V = S.issueView;
  let title, sub = "";
  if (k === "__acc"){
    title = `<span class="ig-t">Accepted</span>`;
    sub = "kept as they are this session — Undo puts one back";
  } else if (V.group === "level"){
    title = `<span class="lvpill lv-${k}">${ISSUE_LV[k].label}</span>`;
    sub = ISSUE_LV[k].help;
  } else if (V.group === "cat"){
    title = `<span class="ig-t">${esc(ISSUE_CAT[k].label)}</span>`;
    sub = ISSUE_CAT[k].help;
  } else {
    const h = rows[0].home;
    title = h.kind === "sheet" ? `<span class="ig-t">${esc(h.label)}</span>`
      : `<span class="mono xs${h.kind === "project" ? " sq" : ""}" style="--card-tint:`
        + `${h.kind === "project" ? projColourOf(h.id) : persColourOf(h.id)}">${esc(monogram(h.label))}</span>`
        + cardLink(h.kind, h.id, h.label, "ig-t") + `<span class="idchip">${esc(h.id)}</span>`;
    const n = {};
    for (const it of rows) n[it.lv] = (n[it.lv] || 0) + 1;
    sub = ISSUE_LEVELS.filter(l => n[l.id]).map(l => `${n[l.id]} ${l.label.toLowerCase()}`).join(" &#183; ");
    return `<tr class="igrp"><th colspan="6"><span class="ig">${title}<span class="ig-n">${rows.length}</span>`
      + `<span class="ig-s">${sub}</span></span></th></tr>`;
  }
  return `<tr class="igrp"><th colspan="6"><span class="ig">${title}<span class="ig-n">${rows.length}</span>`
    + `<span class="ig-s">${esc(sub)}</span></span></th></tr>`;
}

function issueRecordHTML(it){
  const h = it.home;
  if (h.kind === "sheet"){
    const g = ISSUE_GEN_PANEL[h.id];
    return g ? `<button type="button" class="namelink" data-iss-go="${g[0]}" data-tip="${att(
        `<b>${esc(g[1])}</b><br>Open it on General assumptions`)}">${esc(h.label)}</button>`
      : `<span class="muted">${esc(h.label)}</span>`;
  }
  const more = it.rec.project.length + it.rec.person.length - 1;
  return cardLink(h.kind, h.id, h.label) + `<span class="sub">${esc(h.id)}`
    + `${more > 0 ? ` &#183; +${more} more` : ""}</span>`;
}

function issueRowHTML(it){
  const V = S.issueView, open = V.open === it.id, L = ISSUE_LV[it.lv];
  const fixable = issueFixable(it);
  const acc = it.acc ? `<span class="iacc">&#10003; Accepted${it.acc.who ? ` by ${esc(it.acc.who)}` : ""}`
    + ` at ${String(it.acc.at.getHours()).padStart(2, "0")}:${String(it.acc.at.getMinutes()).padStart(2, "0")}`
    + `</span>` : "";
  return `<tr class="iss lv-${it.lv}${it.acc ? " acc" : ""}${open ? " open" : ""}" data-iss="${it.id}">`
    + `<td class="ilv"><span class="lvpill lv-${it.lv}" data-tip="${att(`<b>${L.label}</b><br>${L.help}`)}">`
    + `${L.label}</span></td>`
    + `<td class="icat-c">${esc(ISSUE_CAT[it.cat].label)}</td>`
    + `<td class="irec">${issueRecordHTML(it)}</td>`
    + `<td class="ihead"><span class="itext">${esc(it.head)}</span>${acc}</td>`
    + `<td class="irule"><code>${esc(it.rule)}</code></td>`
    + `<td class="iact"><button type="button" class="btn tiny${open ? " on" : ""}" data-iss-open="${it.id}" `
    + `aria-expanded="${open}">${fixable ? "Fix here" : "Details"}<span class="caret" aria-hidden="true">`
    + `${open ? "&#9652;" : "&#9662;"}</span></button>`
    + (issueAcceptable(it)
        ? it.acc ? `<button type="button" class="btn tiny" data-iss-unacc="${it.id}" data-tip="${att(
            "<b>Undo</b><br>Put it back among the open issues.")}">Undo</button>`
          : `<button type="button" class="btn tiny" data-iss-acc="${it.id}" data-tip="${att(
            "<b>Accept</b><br>Keep it as it is. It leaves the open count for this session, and the "
            + "decision goes into the change log with the next Save. It comes back if what it says "
            + "changes, and when the plan is opened again.")}">Accept</button>`
        : `<span class="inoacc" data-tip="${att("<b>Must be fixed</b><br>The application refuses this, "
            + "so it cannot be accepted — correct it.")}">&#8212;</span>`)
    + `</td></tr>`
    + (open ? `<tr class="issx lv-${it.lv}"><td colspan="6">${issueFixHTML(it)}</td></tr>` : "");
}

/* ------------------------------------------------------------- the fix */

/** The rows an issue is about, to change in place - or null where there is nothing to
 *  type into (a missing sheet, a setting the file did not carry). */
function issueEditRows(it){
  const M = S.model, pid = it.rec.project[0];
  if (it.load || it.cat === "std") return null;
  if (it.raw){
    // A duplicate is about every row that shares the identifier, not the one it names.
    if (it.rule === "V-08" && KEY_COL[it.sheet]){
      const kc = KEY_COL[it.sheet], kv = it.raw[kc];
      return {sheet: it.sheet, rows: (M.raw[it.sheet] || []).filter(r => r[kc] === kv)};
    }
    return {sheet: it.sheet, rows: [it.raw]};
  }
  if ((it.sheet === "Milestone" || it.sheet === "ProjectPeriod") && pid)
    return {sheet: it.sheet, rows: (M.raw[it.sheet] || []).filter(r => r.project_id === pid)};
  if (it.sheet === "PersonPeriodWeight" && it.rec.assignment[0])
    return {sheet: it.sheet, rows: (M.raw.PersonPeriodWeight || [])
      .filter(r => String(r.assignment_id) === it.rec.assignment[0])};
  return null;
}

function issueFixable(it){
  return !!(it.load || it.cat === "std" || issueEditRows(it) || issueQuick(it));
}

/** The columns to show: a narrow sheet whole, with the ones the issue is about marked; a
 *  wide one as the columns that say which row it is plus the ones it is about - unless
 *  nothing says which those are, and then the whole row. */
function issueCols(sheet, it){
  const cols = entryCols(sheet);
  const focus = new Set((ISSUE_FOCUS[it.rule] || []).filter(c => cols.includes(c)));
  for (const c of cols)
    if (new RegExp(`(^|[^\\w])${c.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}([^\\w]|$)`).test(it.msg))
      focus.add(c);
  if (cols.length <= 9 || !focus.size) return {cols, focus};
  const ident = (ISSUE_IDENT[sheet] || [KEY_COL[sheet]]).filter(c => c && cols.includes(c));
  return {cols: [...new Set([...ident, ...cols.filter(c => focus.has(c))])], focus};
}

/** The row a message names, among the several shown - "Inspection on 2028-06-01",
 *  "overlap at Conduct (final)" - so the eye goes to it first. By its name, and by its
 *  date as well where the message carries one, so 'final DB lock' is not read out of
 *  'final DB lock cut-off'. */
function issueHit(it, r){
  const nm = r.milestone_name ?? r.period_name;
  if (nm === null || nm === undefined || String(nm).trim().length < 3) return false;
  const re = new RegExp(`(^|[\\s'"(])${String(nm).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`
    + `(?=$|[\\s'".,;:)])`);
  if (!re.test(it.msg)) return false;
  const d = r.milestone_date ?? r.period_start;
  return !(d instanceof Date) || !/\d{4}-\d{2}-\d{2}/.test(it.msg) || it.msg.includes(ymd(d));
}

function issueEditor(it){
  const E = issueEditRows(it);
  if (!E) return "";
  const {sheet, rows} = E;
  if (!rows.length)
    return `<p class="note">There are no ${esc((SECTION[sheet] || sheet).toLowerCase())} rows for this yet.</p>`;
  const {cols, focus} = issueCols(sheet, it);
  return `<div class="ctwrap"><table class="ct cedit ied"><thead><tr>${cols.map(c =>
      `<th class="${focus.has(c) ? "focus" : ""}" data-tip="${att(`${colHead(c)}<br>${COLUMN_HELP[c] || ""}`)}">`
      + `${esc(COLUMN_LABEL[c] || c)}</th>`).join("")}<th></th></tr></thead><tbody>`
    + rows.map(r => `<tr${rows.length > 1 && issueHit(it, r) ? ' class="hit"' : ""}>`
      + `${cols.map(c => c === "estimation_type" ? cardEstCell(sheet, r)
        : cardCell(sheet, r, c, "", focus.has(c) ? "focus" : "")).join("")}`
      + `${cardDel(sheet, r, "row")}</tr>`).join("")
    + `</tbody></table></div>`;
}

/** A person's assignments, to bring a load down: the weight and the window change here,
 *  and the share each one puts on the worst month says which to change. */
function issueLoadEditor(it){
  const M = S.model, C = S.calc, sid = it.sid, k = it.peakK;
  const rows = (M.raw.Assignment || []).filter(a => a.person_id === sid);
  if (!rows.length) return `<p class="note">No assignment to change.</p>`;
  return `<div class="ctwrap"><table class="ct cedit ied"><thead><tr><th>Project</th><th>Role</th>
      <th>From</th><th>To</th><th class="num">Weight</th>
      <th class="num">In ${esc(keyToLabel(k))}<span class="sub">FTE</span></th><th></th></tr></thead><tbody>`
    + rows.map(a => {
        const pr = M.projects[a.project_id] || {};
        const v = C.cell.get([a.project_id, sid, a.role_name, k].join("|")) || 0;
        return `<tr><td>${M.projects[a.project_id] ? cardLink("project", a.project_id,
            pr.project_name || a.project_id) : `<span class="muted">${esc(a.project_id || "")}</span>`}`
          + `<span class="sub">${esc(a.assignment_id || "")}</span></td>`
          + cardCell("Assignment", a, "role_name")
          + cardCell("Assignment", a, "assign_start_date", `from ${cardDate(pr.start_date) || "the start"}`)
          + cardCell("Assignment", a, "assign_end_date", `to ${cardDate(pr.end_date) || "the end"}`)
          + cardCell("Assignment", a, "person_weight", "", "num focus")
          + `<td class="num">${v > 0.004 ? v.toFixed(2) : `<span class="muted">—</span>`}</td>`
          + cardDel("Assignment", a, "assignment") + `</tr>`;
      }).join("") + `</tbody></table></div>`;
}

/** The one-step fixes the application already has, offered where they apply. */
function issueQuick(it){
  const M = S.model, pid = it.rec.project[0], pr = pid ? M.projects[pid] : null, out = [];
  const r = it.rule;
  if (pr && (r === "V-12" || r === "V-16" || r === "V-06" || r === "V-15" || r === "V-18"
             || (r === "V-05" && it.sheet === "ProjectPeriod")))
    out.push(periodGenButton(pr, pid));
  if (pr && (r === "V-16" || r === "V-14" || r === "V-20" || r === "V-21"))
    out.push(`<button class="btn tiny" data-act="blankms" data-pid="${att(pid)}" `
      + `data-tip="${att(HELP.blankms)}">Blank milestone list</button>`);
  if (r === "V-31" || r === "V-32" || r === "V-33"){
    const asg = /^Assignment\b/.test(it.msg) && it.rec.assignment[0];
    const scope = asg ? "assignment" : "project", id = asg ? it.rec.assignment[0] : pid;
    if (id) out.push(`<button class="btn tiny" data-act="estswitch" data-scope="${scope}" `
      + `data-id="${att(id)}" data-tip="${att("<b>Switch how the figures are made</b><br>Asks first, "
        + "and copies the months across so nothing jumps.")}">Switch to automatic&#8230;</button>`);
  }
  if (pr && it.cat === "std")
    out.push(`<button class="btn tiny" data-team="${att(pid)}">Change team</button>`);
  const g = r === "V-03" || r === "V-23" || r === "V-29" ? ISSUE_GEN_PANEL.RoleFactor
    : r === "V-19" || r === "V-27" ? ISSUE_GEN_PANEL.PeriodFTEStandard
    : !it.raw && ISSUE_GEN_PANEL[it.sheet] ? ISSUE_GEN_PANEL[it.sheet]
    : r === "V-30" ? ISSUE_GEN_PANEL.Config : null;
  if (g) out.push(`<button class="btn tiny" data-iss-go="${g[0]}">Open ${esc(g[1])}</button>`);
  if (r === "V-09") out.push(`<button class="btn tiny" data-iss-go="gen-ver">Version information</button>`);
  return out.join("");
}

function issueFixHTML(it){
  const M = S.model, pid = it.rec.project[0];
  const L = ISSUE_LV[it.lv];
  let body = "";
  if (it.load) body = issueLoadEditor(it);
  else if (it.cat === "std" && pid){
    const rows = gapRows([pid]);
    /* V-40 is about ONE month's review. Where that month is still off its standard it is
       a row like any other; where it is not, the review is all that is left of it, and
       the month is opened by itself - to clear the review or keep it as history. */
    const mm = it.rule === "V-40" ? (it.msg.match(/,\s(\d{4})-(\d{2}):/) || []) : [];
    const mine = mm[0] ? rows.filter(x => isoMonth(x.k) === `${mm[1]}-${mm[2]}`) : rows;
    const was = (it.msg.match(/when it was (short|over|unstaffed)/) || [])[1] || "";
    body = (mine.length ? gapMonthsTable(pid, mine, "scrollx tall")
        : mm[0] ? `<p class="note">${keyToLabel(+mm[1] * 12 + +mm[2] - 1)} is not off its standard any
            more. <button type="button" class="btn tiny" data-gap="${att(pid)}"
            data-gk="${+mm[1] * 12 + +mm[2] - 1}" data-gapis="${was}">Open the month</button></p>`
        : `<p class="note">No month of this project is off its standard now.</p>`)
      + `<p class="note">Click a month to change the figures behind it, and to record the
          decision — <strong>Confirmed</strong>, <strong>Accepted</strong> or
          <strong>To be fixed</strong> — which is kept in the file.</p>`;
  } else body = issueEditor(it);
  const quick = issueQuick(it);
  const open = (kind, id, name) => `<button type="button" class="btn tiny" data-card="${kind}" `
    + `data-cid="${att(id)}" data-tip="${att(`<b>${esc(name)}</b><br>Open this ${kind}'s page — `
      + `everything about it, and every field to change.`)}">Open ${esc(name)} &#8599;</button>`;
  const links = it.rec.project.map(id => open("project", id, M.projects[id].project_name || id))
    .concat(it.rec.person.map(id => open("person", id, M.people[id].person_name || id)))
    .slice(0, 4).join("");
  return `<div class="ifix">
      <p class="imsg"><span class="lvpill lv-${it.lv}">${L.label}</span> <code>${esc(it.rule)}</code>
        ${esc(it.msg)}</p>
      ${body}
      ${quick || links ? `<div class="iacts">${quick}${links}</div>` : ""}
      ${body && !it.load && it.cat !== "std" ? `<p class="note">Type a new value in any cell —
        it is checked as it is entered, and kept as an unsaved change until you
        <strong>Save</strong>. The issue leaves this list as soon as it is put right.</p>` : ""}
    </div>`;
}

/* ------------------------------------------------------------- what the tab does */

function issueGo(panel){
  showTab("t-gen");
  const p = document.querySelector(`#t-gen .panel[data-panel="${panel}"]`);
  if (!p) return;
  if (panel === "gen-ver"){ const d = el("prov"); if (d) d.open = true; }
  p.scrollIntoView({block:"start"});
}

function issueAccept(id, on){
  const it = issues().find(x => x.id === id);
  if (!it || (on && !issueAcceptable(it))) return;
  const f = {sev:it.sev, rule:it.rule, sheet:it.sheet, row:it.row, msg:it.msg};
  if (on){
    S.issueAck.set(it.key, {who: S.who || "", at: new Date()});
    S.events.push(...findingEntries([f], [it.rule], "accepted on Data issues", S.who));
  } else {
    S.issueAck.delete(it.key);
    S.events.push(...findingEntries([f], [], "acceptance withdrawn on Data issues", S.who));
  }
  S.issueAckV++;
  if (S.issueView.open === id) S.issueView.open = null;
  keepScroll(() => renderTab("t-issues"));
  issueCount();
}

document.addEventListener("click", e => {
  if (!e.target.closest || !e.target.closest("#t-issues")) return;
  const V = S.issueView;
  const t = e.target.closest("[data-iss-open], [data-iss-acc], [data-iss-unacc], [data-iss-sort], "
    + "[data-iss-group], [data-iss-lv], [data-iss-cat], [data-iss-clear], [data-iss-go]");
  if (t){
    e.stopPropagation();
    V.done = "";
    const d = t.dataset, attr = [...t.attributes].find(a => a.name.startsWith("data-iss-"));
    if (d.issGo) return issueGo(d.issGo);
    if (d.issAcc) return issueAccept(d.issAcc, true);
    if (d.issUnacc) return issueAccept(d.issUnacc, false);
    if (d.issOpen){
      const it = issues().find(x => x.id === d.issOpen);
      V.open = V.open === d.issOpen || !it ? null : d.issOpen;
      if (it){ V.openHead = it.head; V.openSig = it.sig; }
      keepScroll(drawIssueList);
      const b = document.querySelector(`#t-issues [data-iss-open="${d.issOpen}"]`);
      if (b){
        b.focus({preventScroll:true});
        const x = b.closest("tr").nextElementSibling;
        (x && x.classList.contains("issx") ? x : b).scrollIntoView({block:"nearest"});
      }
      return;
    }
    if (d.issSort){
      if (V.sort === d.issSort) V.dir = -V.dir; else { V.sort = d.issSort; V.dir = 1; }
    }
    if (d.issGroup) V.group = d.issGroup;
    if (d.issLv) V.lv.has(d.issLv) ? V.lv.delete(d.issLv) : V.lv.add(d.issLv);
    if (d.issCat) V.cat.has(d.issCat) ? V.cat.delete(d.issCat) : V.cat.add(d.issCat);
    if ("issClear" in d){ V.lv.clear(); V.cat.clear(); V.q = ""; }
    keepScroll(() => renderTab("t-issues"));
    // The control just pressed has been drawn again; the focus goes back to it.
    const again = attr && document.querySelector(`#t-issues [${attr.name}`
      + `${attr.value ? `="${CSS.escape(attr.value)}"` : ""}]`);
    if (again) again.focus({preventScroll:true});
    return;
  }
  /* A click on the row itself - not on anything in it that does something of its own -
     opens it, as the button at its end does. */
  const tr = e.target.closest("tr.iss");
  if (tr && !e.target.closest("button, a, input, [contenteditable='true']")){
    const b = tr.querySelector("[data-iss-open]");
    if (b) b.click();
  }
});

/* The search answers as it is typed; only the list is redrawn, so the box keeps its
   caret. */
document.addEventListener("input", e => {
  if (e.target.id !== "issueQ") return;
  S.issueView.q = e.target.value;
  S.issueView.done = "";
  drawIssueList();
});
