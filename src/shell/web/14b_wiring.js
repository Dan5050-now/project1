
/** Begin a plan with nothing in it but the standard vocabulary and settings. */
function startBlank(){
  try {
    adopt(blankSheets(), "New plan (not yet exported)", {
      blank: true,
      // The project tab, not Overall: Overall would open on an empty dashboard, and the
      // first thing to do is enter a project.
      tab: "t-proj",
      banner: "New plan started. Add your first project below — then its milestones, "
        + "your people, and who works on what. Period weights and role factors are "
        + "placeholders at 1.00 until you set them on General assumptions. Nothing is on "
        + "disk until you press Export.",
    });
  } catch (e){
    showBanner("bad", `Could not start a new plan: ${e.message}`);
    console.error(e);
  }
}

el("vers").textContent = `v${APP_VERSION} · expects source schema v${SCHEMA_EXPECTED}`;

/** REQ-VC-01 / REQ-VC-02: what this build was written against, and - once a workbook
 *  is loaded - whether that workbook agrees with it. */
function renderProvenance(){
  const short = BUILT_AGAINST.map(d =>
    `<span><span class="plabel">${esc(d.what.replace("Programming ","").replace("Source data ",""))}</span> `
    + `<span class="pv">v${esc(d.ver)}</span></span>`).join("");
  el("provSum").innerHTML =
    `<span><span class="plabel">Application</span> <span class="pv">v${APP_VERSION}</span></span>`
    + `<span class="plabel">built against</span>${short}`;

  const loaded = S.model ? num(S.model.config.schema_version) : null;
  const rows = BUILT_AGAINST.map(d =>
    `<tr><td>${esc(d.what)}</td><td><span class="pv">v${esc(d.ver)}</span></td>`
    + `<td><code>${esc(d.file)}</code></td><td>${esc(d.status)}</td></tr>`).join("");
  const loadedRow = S.model
    ? `<tr><td>Loaded workbook</td><td><span class="pv">schema v${loaded ?? "?"}</span></td>`
      + `<td><code>${esc(S.fileName)}</code></td>`
      + (String(loaded) === String(SCHEMA_EXPECTED)
          ? `<td class="ok">✓ matches the schema this application expects</td>`
          : `<td class="warn">▲ this application expects schema v${SCHEMA_EXPECTED} — see the findings report (V-09)</td>`)
      + `</tr>`
    : `<tr><td>Loaded workbook</td><td class="plabel">—</td><td colspan="2" class="plabel">nothing loaded yet</td></tr>`;
  el("provBody").innerHTML =
    `<div class="scrollx tall"><table><thead><tr><th>Controlled document</th><th>Version</th><th>File</th>`
    + `<th>Status</th></tr></thead><tbody>${rows}${loadedRow}</tbody></table></div>`
    + `<p class="note">These are the documents this build implements. The application does not read them —
       they are recorded here so a file on someone's disk can be traced back to the issue it was built
       from. tools/check_consistency.py verifies the list against the repository on every run.</p>`;
}
renderProvenance();
el("loadBtn").onclick = el("loadBtn2").onclick = () => el("picker").click();
el("startBtn").onclick = startBlank;
el("picker").onchange = e => { if (e.target.files[0]) loadFile(e.target.files[0]); };
/* The export menu. Each item closes it before acting, so the panel is not left hanging
   open over a banner that is reporting what just happened. */
const expDone = fn => () => { el("expMenu").open = false; fn(); };
el("exportBtn2").onclick = expDone(() => exportWorkbook(false));
el("exportJsonBtn").onclick = expDone(() => exportWorkbook(true));
el("exportCalcBtn").onclick = expDone(exportResults);
el("repClose").onclick = () => el("report").close();
el("cfgClose").onclick = () => el("cfgchg").close();
el("chgBtn").onclick = () => { renderChanges(); el("changes").showModal(); };
el("chgClose").onclick = () => el("changes").close();
el("chgBig").onclick = () => {
  const d = el("changes"), big = d.classList.toggle("big");
  el("chgBig").textContent = big ? "Exit full screen" : "Full screen";
  cueScrollers();                       // the box changed size, so its edge cues have too
};
el("themeBtn").onclick = () => {
  const r = document.documentElement;
  const dark = r.dataset.theme ? r.dataset.theme === "dark"
             : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark ? "light" : "dark";
};

const drop = el("drop");
["dragenter","dragover"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.add("on"); }));
["dragleave","drop"].forEach(ev => drop.addEventListener(ev, e => {
  e.preventDefault(); drop.classList.remove("on"); }));
drop.addEventListener("drop", e => { const f = e.dataTransfer.files[0]; if (f) loadFile(f); });

for (const id of Object.keys(FILTER_KEY))
  el(id).addEventListener("change", () => {
    msSummary(el(id)); readFilters(); fitHorizon(); renderKeepingTab(); });

/* Clear one filter without hunting for the ticks that are still on. */
document.addEventListener("click", e => {
  const c = e.target.closest("[data-msclear]");
  if (!c) return;
  const d = el(c.dataset.msclear);
  for (const i of d.querySelectorAll("input")) i.checked = false;
  msSummary(d); readFilters(); fitHorizon(); renderKeepingTab();
});
/* One open at a time, and clicking anywhere else puts them all away - <details> keeps
   itself open otherwise, and seven panels left hanging over the page would bury it. */
document.addEventListener("click", e => {
  for (const d of document.querySelectorAll("details.ms"))
    if (d.open && !d.contains(e.target)) d.open = false;
});
document.addEventListener("keydown", e => {
  if (e.key !== "Escape") return;
  for (const d of document.querySelectorAll("details.ms")) d.open = false;
});
for (const id of ["fFrom","fTo"])
  el(id).addEventListener("change", () => { readFilters(); renderKeepingTab(); });
el("fAll").onclick = () => { S.from = S.calc.lo; S.to = S.calc.hi;
  if (S.to - S.from > 120) S.to = S.from + 120; writeHorizon(); renderKeepingTab(); };
el("fReset").onclick = () => {
  for (const id of Object.keys(FILTER_KEY)){
    for (const i of el(id).querySelectorAll("input")) i.checked = false;
    el(id).open = false;
    msSummary(el(id));
  }
  defaultHorizon(); readFilters(); renderKeepingTab();
};

document.addEventListener("click", e => {
  const tab = e.target.closest("nav button");
  if (tab){ showTab(tab.dataset.tab); window.scrollTo({top:0}); return; }
  const parent = e.target.closest("tr.parent");
  if (parent){
    const k = parent.dataset.k;
    S.expanded.has(k) ? S.expanded.delete(k) : S.expanded.add(k);
    renderKeepingTab(); return;
  }
  const vt = e.target.closest("[data-setview]");
  if (vt){
    const [id, mode] = vt.dataset.setview.split("|");
    S.genView[id] = mode;
    keepScroll(renderGenTab);
    return;
  }
  const act = e.target.closest("[data-act]");
  if (act){
    e.stopPropagation();
    if (act.dataset.act === "blankms") blankMilestones(act.dataset.pid);
    if (act.dataset.act === "autoper") autoPeriods(act.dataset.pid);
    if (act.dataset.act === "blankper") blankPeriods(act.dataset.pid);
    if (act.dataset.act === "estswitch") switchEstimation(act.dataset.scope, act.dataset.id);
    if (act.dataset.act === "estfill") fillEstimates(act.dataset.scope, act.dataset.id);
    /* The two levels of a manual figure are on different tabs, and the question the
       panel raises - "which assignment is stated, and what does it say" - is only
       answerable on the other one. So it takes you there, with the row already
       selected, rather than naming it and leaving you to find it. */
    if (act.dataset.act === "gopers"){
      S.selPers = act.dataset.sid;
      S.selAsg = act.dataset.aid;
      showTab("t-pers"); renderAll(); showTab("t-pers");
    }
    if (act.dataset.act === "goproj"){
      S.selProj = act.dataset.pid;
      showTab("t-proj"); renderAll(); showTab("t-proj");
    }
    return;
  }
  const ins = e.target.closest("[data-ins]");
  if (ins){
    e.stopPropagation();
    const sheet = ins.dataset.ins, after = +ins.dataset.after;
    const rows = S.model.raw[sheet];
    const i = rows.findIndex(r => r.__row === after);
    const blank = {__row: Math.max(0, ...rows.map(r => r.__row)) + 1, __new:true};
    for (const h of (S.headers[sheet] || [])) blank[h] = null;
    if (PARENT_OF[sheet]){
      const [col, val] = PARENT_OF[sheet]();
      if (val) blank[col] = val;
    }
    if (AUTO_KEY.has(sheet)){
      const id = nextKey(sheet, KEY_COL[sheet]);
      if (id) blank[KEY_COL[sheet]] = id;
    }
    for (const [col, v] of Object.entries(NEW_ROW[sheet] || {}))
      if (S.headers[sheet] && S.headers[sheet].includes(col))
        blank[col] = typeof v === "function" ? v() : v;
    rows.splice(i + 1, 0, blank);                        // directly below, not appended
    beginEditSession();
    S.pending.push({at:new Date(), sheet, row:blank.__row, col:"(new row)",
                    from:null, to:""});
    // Deliberately no rebuild: a row with every cell empty is INCOMPLETE, not invalid,
    // and the parser skips blank rows. It becomes real when a field is filled, and the
    // export guard refuses to write one that still has no identifier.
    renderKeepingTab();
    return;
  }
  const del = e.target.closest("[data-del]");
  if (del){
    e.stopPropagation();
    deleteRow(del.dataset.del, +del.dataset.row);
    return;
  }
  const row = e.target.closest(".data-t tbody tr");
  if (row && row.dataset.id) keepScroll(() => {
    const sheet = row.closest(".data-t").dataset.sheet;
    // Re-render the DEPENDENT panels only. Re-rendering the table itself would replace
    // the cell the click just put the caret in, so the edit could never be typed.
    if (sheet === "Project" && S.selProj !== row.dataset.id){
      S.selProj = row.dataset.id;
      for (const tr of row.parentNode.children) tr.classList.toggle("sel", tr === row);
      const d = el("projDetail"); if (d) d.innerHTML = projDetail(S.selProj);
    }
    if (sheet === "Person" && S.selPers !== row.dataset.id){
      S.selPers = row.dataset.id;
      S.selAsg = null;                   // a different person has different assignments
      for (const tr of row.parentNode.children) tr.classList.toggle("sel", tr === row);
      const d = el("persDetail"); if (d) d.innerHTML = persDetail(S.selPers);
    }
    // Selecting an assignment drives the overrides table beside it. Only the panels that
    // depend on it are redrawn - re-rendering the Assignments table would replace the
    // cell the click just put the caret in, so the edit could never be typed.
    if (sheet === "Assignment" && S.selAsg !== row.dataset.id){
      S.selAsg = row.dataset.id;
      for (const tr of row.parentNode.children) tr.classList.toggle("sel", tr === row);
      const d = el("asgDetail"); if (d) d.innerHTML = overridesPanel(S.selPers);
    }
  });
});

// Clicking a cell that ALREADY has the caret fires no focusin, so after Escape has
// dismissed the list there would be no way to ask for it again without clicking away
// and back. A click in the field re-opens it; SUGG.open is a no-op if it is already
// showing for that cell.
document.addEventListener("click", e => {
  const td = e.target.closest('td[contenteditable="true"]');
  if (td){ SUGG.open(td); CAL.open(td); }
});
document.addEventListener("focusin", e => {
  const td = e.target.closest('td[contenteditable="true"]');
  if (!td) return;
  // Only on a FRESH focus. Focus is also restored programmatically after a scrollbar
  // drag on the suggestion list, and re-recording `orig` there would make Escape revert
  // to the half-typed text instead of the value the cell started with.
  if (!SUGG.owns(td)) td.dataset.orig = td.textContent;
  SUGG.open(td);
  CAL.open(td);
});
document.addEventListener("focusout", e => {
  const td = e.target.closest('td[contenteditable="true"]');
  if (!td) return;
  /* Close on a delay, and only if the panel is still THIS cell's. Clicking straight
     from one cell to the next opens the panel for the new one before this timer fires,
     and an unconditional close would then shut the panel that had just been opened -
     which looked exactly like "it only works every other click". */
  setTimeout(() => { if (!SUGG.holding && SUGG.owns(td)) SUGG.close(); }, 120);
  setTimeout(() => { if (!CAL.holding && CAL.owns(td)) CAL.close(); }, 120);
  const now = td.textContent;
  if (now === td.dataset.orig) return;
  applyEdit(td.dataset.sheet, +td.dataset.row, td.dataset.col, now, td);
});
document.addEventListener("keydown", e => {
  const td = e.target.closest('td[contenteditable="true"]');
  if (!td) return;
  if (SUGG.key(e)) return;                       // the list takes the key first
  if (CAL.key(e)) return;
  if (e.key === "Enter"){ e.preventDefault(); SUGG.close(); CAL.close(); td.blur(); }
  if (e.key === "Escape"){ td.textContent = td.dataset.orig ?? ""; SUGG.close(); CAL.close(); td.blur(); }
});
// A pop-up over the cell you are typing into is in the way, so it goes.
document.addEventListener("input", e => {
  if (e.target.closest('td[contenteditable="true"]')){ el("tip").hidden = true; }
});

/* ---- type-ahead ---- */
const SUGG = (() => {
  const box = el("sugg");
  let cell = null, items = [], idx = -1;
  const api = {holding:false};

  /** Every run of every token, merged, so each matched fragment is marked - not just
   *  the first one and not just a single contiguous stretch. */
  function markup(v, toks){
    const lv = v.toLowerCase(), spans = [];
    for (const t of toks){
      for (let i = lv.indexOf(t); i >= 0; i = lv.indexOf(t, i + t.length)) spans.push([i, i + t.length]);
    }
    if (!spans.length) return esc(v);
    spans.sort((a, b) => a[0] - b[0]);
    const merged = [spans[0]];
    for (const s of spans.slice(1)){
      const last = merged[merged.length - 1];
      if (s[0] <= last[1]) last[1] = Math.max(last[1], s[1]);
      else merged.push(s);
    }
    let out = "", at = 0;
    for (const [a, z] of merged){
      out += esc(v.slice(at, a)) + "<mark>" + esc(v.slice(a, z)) + "</mark>";
      at = z;
    }
    return out + esc(v.slice(at));
  }

  /** Anchor the box to its cell. Separate from render() because a scroll has to
   *  re-anchor without rebuilding the list - rebuilding would throw away where the
   *  reader had scrolled to, which is the very thing they were doing. */
  function place(){
    const r = cell.getBoundingClientRect();
    box.style.left = Math.max(8, Math.min(r.left, innerWidth - box.offsetWidth - 8)) + "px";
    box.style.top = (r.bottom + box.offsetHeight > innerHeight - 8
      ? Math.max(8, r.top - box.offsetHeight - 4) : r.bottom + 4) + "px";
  }

  function render(q){
    // Tokens, matched in ANY ORDER: 'phase 1 onv' should find 'ONV-101 Phase 1'. Someone
    // searching a list types the parts they remember, not the string as it was written.
    const ql = q.trim().toLowerCase();
    const toks = ql.split(/\s+/).filter(Boolean);
    let hits = items;
    if (toks.length){
      // Ranked, because token matching casts a wide net: typing '1' matches every
      // 'Phase 1' AND every 'ONV-111'. What was typed as a prefix comes first, then what
      // contains it whole, then the rest - each group in the list's own order, so the
      // ordering is stable and the thing most likely meant is at the top.
      const rank = v => {
        const lv = v.toLowerCase();
        return lv.startsWith(ql) ? 0 : lv.includes(ql) ? 1 : 2;
      };
      hits = items.filter(v => {
        const lv = v.toLowerCase();
        return toks.every(t => lv.includes(t));
      });
      hits = hits.map((v, i) => [rank(v), i, v]).sort((a, b) => a[0] - b[0] || a[1] - b[1])
                 .map(x => x[2]);
    }
    // Nothing matched is not a reason to take the chooser away - it leaves the reader
    // with no list and no way back to one. Show the whole vocabulary and say so.
    const none = toks.length > 0 && hits.length === 0;
    if (none) hits = items;
    hits = hits.slice(0, 60);
    if (!hits.length){ box.hidden = true; return; }
    // NOTHING is highlighted until an arrow key highlights it. Enter must commit what was
    // TYPED - highlighting the first row by default would make Enter silently swap in a
    // value the user never chose, which is exactly what a free-text column must not do.
    // The old code clamped idx up to 0 here; it only escaped notice because a query that
    // matched nothing used to hide the list, taking Enter out of its reach.
    idx = idx < 0 ? -1 : Math.min(idx, hits.length - 1);
    box.innerHTML = hits.map((v, i) =>
      `<div class="s" role="option" data-v="${att(v)}" aria-selected="${i === idx}">`
      + `${none ? esc(v) : markup(v, toks)}</div>`).join("")
      + `<div class="hint">`
      + (none ? `nothing matches that \u2014 showing all ${items.length}`
              : `${hits.length}${hits.length === 60 ? "+" : ""} match${hits.length === 1 ? "" : "es"}`)
      + ` &middot; \u2191\u2193 then Enter picks one &middot; Enter alone keeps what you typed`
      + ` &middot; Esc closes</div>`;
    box.hidden = false;
    place();
  }

  api.open = td => {
    // Already open on this cell: leave it exactly as it is. Re-opening would reset the
    // filter and the scroll position, and this runs again whenever focus is restored
    // after a scrollbar drag.
    if (cell === td && !box.hidden) return;
    cell = td; idx = -1;
    const row = (S.model.raw[td.dataset.sheet] || []).find(r => r.__row === +td.dataset.row);
    items = suggestionsFor(td.dataset.sheet, td.dataset.col, row);
    if (!items.length){ box.hidden = true; cell = null; return; }
    // Opening shows the WHOLE vocabulary. Filtering by the value already in the cell
    // would narrow it to that one value, which is the opposite of what a chooser is for.
    // Re-opening part-way through typing is the other case, and there the filter is the
    // point, so it is kept.
    const typed = td.textContent;
    render(typed !== (td.dataset.orig ?? "") ? typed : "");
  };
  api.close = () => { box.hidden = true; cell = null; idx = -1; api.holding = false; };
  api.owns = td => cell === td && !box.hidden;
  api.key = e => {
    if (!cell || box.hidden) return false;
    const opts = [...box.querySelectorAll(".s")];
    if (!opts.length) return false;
    if (e.key === "ArrowDown" || e.key === "ArrowUp"){
      e.preventDefault();
      idx = (idx + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
      opts.forEach((o, i) => o.setAttribute("aria-selected", String(i === idx)));
      opts[idx].scrollIntoView({block:"nearest"});
      return true;
    }
    if (e.key === "Enter" && idx >= 0){ e.preventDefault(); choose(opts[idx].dataset.v); return true; }
    if (e.key === "Escape"){ e.preventDefault(); api.close(); return true; }
    return false;
  };
  function choose(v){
    const td = cell;
    api.close();
    td.textContent = v;
    td.blur();                                   // blur commits through the normal edit path
  }
  box.addEventListener("mousedown", e => {       // before focusout, or the cell is already gone
    // Held for the whole press, not just for a click on an option. Dragging the list's
    // OWN scrollbar takes focus off the cell, and the focusout handler would close the
    // list underneath the hand that is scrolling it. `holding` is what tells it not to.
    api.holding = true;
    const s = e.target.closest(".s");
    if (s){ e.preventDefault(); choose(s.dataset.v); api.holding = false; }
  });
  addEventListener("mouseup", () => {
    if (!api.holding) return;
    api.holding = false;
    // Put the caret back where the user left it, so the arrow keys, Enter and the
    // eventual commit-on-blur all still work after a scrollbar drag.
    if (cell && !box.hidden) cell.focus({preventScroll:true});
  });
  document.addEventListener("input", e => {
    const td = e.target.closest('td[contenteditable="true"]');
    if (td && td === cell) render(td.textContent);
  });
  /* The box is position:fixed and anchored to its cell, so a scroll that MOVES the cell
     has to be answered. Scrolling INSIDE the box is not that - it is the reader working
     through the list, and closing on it makes a list taller than the box impossible to
     reach the bottom of. So: ignore the box's own scrolling, and elsewhere re-anchor
     rather than close, closing only once the cell itself has gone off screen. */
  addEventListener("scroll", e => {
    if (!cell || box.hidden) return;
    const t = e.target;
    if (t === box || (t && t.nodeType === 1 && box.contains(t))) return;
    const r = cell.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) api.close();
    else place();
  }, true);
  return api;
})();

/* ---- the calendar ----------------------------------------------------------
   A date column offers a month grid, and stays fully typeable while it is open.

   Both halves matter. Picking is what you want for a date you are reading off a plan
   in front of you, where "is the 14th a Tuesday" is the actual question; typing is what
   you want for the twentieth row of a set you already know, where a grid is four clicks
   to say something you could have said in eight keystrokes. So this is an OFFER laid
   beside the cell, never a gate in front of it: the caret stays in the cell, every key
   still reaches it, and what you type steers the grid rather than the other way round.

   Deliberately not <input type="date">. It would bring a native picker for nothing, and
   take the cell's own behaviour with it - one editing model for text cells and another
   for date cells, a different keyboard contract, a browser-dependent display format, and
   no way to leave a date deliberately blank the way the rest of the table does. */
const CAL = (() => {
  const box = el("cal");
  const DOW = ["Mo","Tu","We","Th","Fr","Sa","Su"];
  const MON = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"];
  let cell = null, shown = null;                 // shown: the month on display
  const api = {holding:false};

  const isDate = td => (SHEET_COLS[td.dataset.sheet] || {date:[]}).date.includes(td.dataset.col);
  const readCell = () => {
    const d = parseDate((cell.textContent || "").trim());
    return d instanceof Date ? d : null;
  };
  const firstOf = d => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1));

  function place(){
    const r = cell.getBoundingClientRect();
    box.style.left = Math.max(8, Math.min(r.left, innerWidth - box.offsetWidth - 8)) + "px";
    box.style.top = (r.bottom + box.offsetHeight > innerHeight - 8
      ? Math.max(8, r.top - box.offsetHeight - 4) : r.bottom + 4) + "px";
  }

  function render(){
    const picked = readCell();
    // What is being typed steers the grid: type 2029 and the calendar is already there.
    if (picked) shown = firstOf(picked);
    const y = shown.getUTCFullYear(), m = shown.getUTCMonth();
    const lead = (new Date(Date.UTC(y, m, 1)).getUTCDay() + 6) % 7;    // weeks start Monday
    const days = new Date(Date.UTC(y, m + 1, 0)).getUTCDate();
    const todayKey = ymd(new Date());
    const cells = [];
    for (let i = 0; i < lead; i++) cells.push('<div class="d off"></div>');
    for (let n = 1; n <= days; n++){
      const k = ymd(new Date(Date.UTC(y, m, n)));
      const cls = "d" + (picked && k === ymd(picked) ? " on" : "")
                      + (k === todayKey ? " today" : "");
      cells.push(`<button type="button" class="${cls}" data-d="${k}">${n}</button>`);
    }
    box.innerHTML =
      `<div class="calhead">`
      + `<button type="button" class="cnav" data-step="-12" title="Previous year">&#171;</button>`
      + `<button type="button" class="cnav" data-step="-1" title="Previous month">&#8249;</button>`
      + `<span class="cmon">${MON[m]} ${y}</span>`
      + `<button type="button" class="cnav" data-step="1" title="Next month">&#8250;</button>`
      + `<button type="button" class="cnav" data-step="12" title="Next year">&#187;</button>`
      + `</div>`
      + `<div class="calgrid">${DOW.map(d => `<div class="dow">${d}</div>`).join("")}`
      + cells.join("") + `</div>`
      + `<div class="calfoot">`
      + `<button type="button" class="btn tiny" data-d="${att(todayKey)}">Today</button>`
      + `<button type="button" class="btn tiny" data-d="">Clear</button>`
      + `<span class="hint">or type it: YYYY-MM-DD</span></div>`;
    box.hidden = false;
    place();
  }

  api.open = td => {
    if (!isDate(td)){ if (cell !== td) api.close(); return; }
    if (cell === td && !box.hidden) return;
    cell = td;
    shown = firstOf(readCell() || new Date());
    render();
  };
  api.close = () => { box.hidden = true; cell = null; api.holding = false; };
  api.owns = td => cell === td && !box.hidden;
  api.key = e => {
    if (!cell || box.hidden) return false;
    if (e.key === "Escape"){ e.preventDefault(); api.close(); return true; }
    // PageUp/PageDown step the month without disturbing the caret. The arrow keys are
    // left to the text, because the caret is in the cell and moving it is what they mean
    // there - a grid that stole them would break typing to make picking prettier.
    if (e.key === "PageUp" || e.key === "PageDown"){
      e.preventDefault();
      step(e.key === "PageDown" ? 1 : -1);
      return true;
    }
    return false;
  };
  function step(n){
    const at = readCell();
    if (at) shown = firstOf(at);
    shown = new Date(Date.UTC(shown.getUTCFullYear(), shown.getUTCMonth() + n, 1));
    // Re-rendered from `shown` alone: with a date in the cell, render() would snap the
    // grid straight back to it and the arrows would appear not to work.
    const keep = cell.textContent;
    cell.textContent = "";
    render();
    cell.textContent = keep;
  }
  function choose(v){
    const td = cell;
    api.close();
    td.textContent = v;
    td.blur();                                   // blur commits through the normal path
  }
  box.addEventListener("mousedown", e => {
    api.holding = true;                          // hold focus while the panel is used
    const nav = e.target.closest(".cnav");
    if (nav){ e.preventDefault(); step(+nav.dataset.step); api.holding = false;
              if (cell) cell.focus({preventScroll:true}); return; }
    const d = e.target.closest("[data-d]");
    if (d){ e.preventDefault(); choose(d.dataset.d); api.holding = false; }
  });
  addEventListener("mouseup", () => {
    if (!api.holding) return;
    api.holding = false;
    if (cell && !box.hidden) cell.focus({preventScroll:true});
  });
  document.addEventListener("input", e => {
    const td = e.target.closest('td[contenteditable="true"]');
    if (td && td === cell) render();
  });
  addEventListener("scroll", e => {
    if (!cell || box.hidden) return;
    const t = e.target;
    if (t === box || (t && t.nodeType === 1 && box.contains(t))) return;
    const r = cell.getBoundingClientRect();
    if (r.bottom < 0 || r.top > innerHeight || r.right < 0 || r.left > innerWidth) api.close();
    else place();
  }, true);
  return api;
})();

/* Information pop-up. Hover shows it transiently; CLICK PINS it so it can be read
   without holding the mouse still - which is also what makes it usable on a touch
   screen and from the keyboard, where there is no hover at all. Escape or a click
   elsewhere releases the pin. */
(function(){
  const tip = el("tip");
  let pinned = null, last = {x:0, y:0};
  const place = (x, y) => {
    const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
    let nx = x + pad, ny = y + pad;
    if (nx + w > innerWidth - 8) nx = x - w - pad;
    if (ny + h > innerHeight - 8) ny = y - h - pad;
    tip.style.left = Math.max(8, nx) + "px";
    tip.style.top = Math.max(8, ny) + "px";
  };
  const show = (html, x, y, isPin) => {
    tip.innerHTML = html + (isPin ? `<span class="tipclose">click anywhere to close</span>` : "");
    tip.hidden = false;
    tip.classList.toggle("pinned", !!isPin);
    place(x, y);
  };
  const hide = () => { if (!pinned){ tip.hidden = true; tip.classList.remove("pinned"); } };

  document.addEventListener("mouseover", e => {
    const el_ = e.target.closest("[data-tip]");
    if (!el_ || pinned) return;
    last = {x:e.clientX, y:e.clientY};
    show(el_.dataset.tip, last.x, last.y, false);
  });
  document.addEventListener("mousemove", e => {
    last = {x:e.clientX, y:e.clientY};
    if (!tip.hidden && !pinned) place(last.x, last.y);
  });
  document.addEventListener("mouseout", e => { if (e.target.closest("[data-tip]")) hide(); });

  document.addEventListener("click", e => {
    const el_ = e.target.closest("[data-tip]");
    // A control with its own job keeps it; the pop-up is explanation, not the action.
    const isControl = e.target.closest("button, a, select, input, summary, [contenteditable='true']");
    if (el_ && !isControl){
      e.stopPropagation();
      pinned = (pinned === el_) ? null : el_;
      if (pinned) show(el_.dataset.tip, e.clientX, e.clientY, true);
      else hide();
      return;
    }
    if (pinned){ pinned = null; tip.hidden = true; tip.classList.remove("pinned"); }
  }, true);

  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && pinned){ pinned = null; tip.hidden = true; tip.classList.remove("pinned"); }
  });
  // Keyboard users get the same information on focus, since they never hover.
  document.addEventListener("focusin", e => {
    const el_ = e.target.closest("[data-tip]");
    if (!el_ || pinned) return;
    const r = el_.getBoundingClientRect();
    show(el_.dataset.tip, r.left + r.width / 2, r.bottom, false);
  });
  document.addEventListener("focusout", e => { if (e.target.closest("[data-tip]")) hide(); });
})();

document.addEventListener("change", e => {
  if (e.target.id === "unitSel"){
    S.model.UNIT = e.target.value;
    S.model.config.capacity_unit = e.target.value;
    renderKeepingTab();
  }
});

el("saveBtn").onclick = saveEdits;
el("discardBtn").onclick = discardEdits;
addEventListener("beforeunload", e => {
  // REQ-IMP-08. Saved-but-not-exported changes count too: they exist only in memory.
  if (S.pending.length || S.saved){ e.preventDefault(); e.returnValue = ""; }
});
</script>
