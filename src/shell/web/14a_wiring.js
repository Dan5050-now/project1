/* ============================================================ 14. wiring */

/* Re-rendering a panel replaces its DOM, and a fresh element starts at the top left.
   On a dashboard that is invisible. During data entry it is the difference between a
   usable table and an unusable one: commit one cell in a table twenty-two columns wide
   and every scroll box snaps back to the first row and the first column, so the next
   cell you meant to fill is off screen again. Every cell costs a re-scroll.

   Nothing but the user should move a scroll position, so it is captured and put back
   around every re-render. Changing tab still goes to the top, because that is the user
   moving somewhere else rather than the page moving underneath them.

   The key has to survive the DOM being rebuilt. A data table names itself by its sheet;
   everything else - the charts - is keyed by where it sits among the other keyless boxes
   in its own pane, which is stable for as long as the panels are. */
function scrollBoxes(){
  const out = new Map(), seen = {};
  for (const box of document.querySelectorAll(".scrollx")){
    const t = box.querySelector("table.data-t[data-sheet]");
    let key;
    if (t) key = "t:" + t.dataset.sheet;
    else {
      const id = (box.closest("section.tab") || {}).id || "doc";
      seen[id] = (seen[id] || 0) + 1;
      key = id + ":" + seen[id];
    }
    out.set(key, box);
  }
  return out;
}
function keepScroll(fn){
  const was = new Map();
  for (const [k, box] of scrollBoxes())
    if (box.scrollLeft || box.scrollTop) was.set(k, [box.scrollLeft, box.scrollTop]);
  const y = window.scrollY;
  fn();
  cueScrollers();
  for (const [k, box] of scrollBoxes()){
    const p = was.get(k);
    if (p){ box.scrollLeft = p[0]; box.scrollTop = p[1]; }
  }
  // The page itself moves too, because a re-render can change the height of the banner
  // above everything else. Clamped by the browser if the page got shorter.
  if (y && window.scrollY !== y) window.scrollTo({top:y});
}

/** Wrap every scroll region in its edge-cue element, and keep the cue current.
 *
 *  Done here rather than in each of the fifteen places that emit a `.scrollx`, because a
 *  render replaces the DOM wholesale and the wrapper would have to be re-emitted every
 *  time anyway. The listener is attached once per box and the box is re-created on each
 *  render, so there is nothing to remove. */
function cueScrollers(){
  for (const box of document.querySelectorAll(".scrollx")){
    let wrap = box.parentElement;
    if (!wrap || !wrap.classList.contains("cue")){
      wrap = document.createElement("div");
      wrap.className = "cue";
      box.parentNode.insertBefore(wrap, box);
      wrap.appendChild(box);
      wrap.appendChild(makeBar(box, "h"));
      wrap.appendChild(makeBar(box, "v"));
      box.addEventListener("scroll", () => paintCue(box), {passive:true});
    }
    paintCue(box);
  }
}

/* ---------------------------------------------------------------- scroll bars
   Drawn by the application, not by the browser.

   Every one of these regions is deliberately bounded on both axes, and a bounded
   region is only honest if the reader can SEE that there is more and reach it. The
   browser was asked to do that twice and did not: `scrollbar-width:thin` produced an
   overlay bar that occupies no layout space and fades out when idle, and dropping it
   so that ::-webkit-scrollbar would apply did not help either - on a build that uses
   overlay scrollbars the rule is ignored outright, and the bar measures zero however
   it is styled. Measured here: a plain div with overflow:scroll and an explicit
   ::-webkit-scrollbar height of 14px still reports offsetHeight - clientHeight === 0.

   So the region keeps its native scrolling - wheel, trackpad, keyboard, shift-wheel -
   the native bar is hidden, and this draws one that is always there while there is
   anywhere to go. One appearance on every machine, and nothing to detect.

   The bar is a child of the .cue wrapper rather than of the scrolling box, so it does
   not scroll away with the content it describes. */
function makeBar(box, axis){
  const bar = document.createElement("div");
  bar.className = "sbar " + axis;
  const thumb = document.createElement("div");
  thumb.className = "thumb";
  bar.appendChild(thumb);
  const horiz = axis === "h";
  const pos = e => horiz ? e.clientX : e.clientY;
  const span = () => horiz ? [box.scrollWidth, box.clientWidth] : [box.scrollHeight, box.clientHeight];
  const at = () => horiz ? box.scrollLeft : box.scrollTop;
  const to = v => { if (horiz) box.scrollLeft = v; else box.scrollTop = v; };

  let from = null, was = 0;
  const move = e => {
    if (from === null) return;
    const [sw, cw] = span();
    const track = (horiz ? bar.clientWidth : bar.clientHeight) - 4;
    const room = Math.max(1, track - thumbSize(sw, cw, track));
    to(was + (pos(e) - from) * (sw - cw) / room);
    e.preventDefault();
  };
  const up = () => {
    from = null;
    bar.classList.remove("dragging");
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", up);
  };
  thumb.addEventListener("pointerdown", e => {
    from = pos(e); was = at();
    bar.classList.add("dragging");
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    e.preventDefault(); e.stopPropagation();
  });
  // Clicking the track pages, the way a scrollbar has always done - and it is the
  // half of a scrollbar people reach for when the thumb is small.
  bar.addEventListener("pointerdown", e => {
    if (e.target === thumb) return;
    const r = bar.getBoundingClientRect();
    const [, cw] = span();
    const ahead = (horiz ? e.clientX - r.left : e.clientY - r.top)
                > (horiz ? thumb.offsetLeft + thumb.offsetWidth / 2
                         : thumb.offsetTop + thumb.offsetHeight / 2);
    to(at() + (ahead ? cw : -cw));
    e.preventDefault();
  });
  return bar;
}
function thumbSize(full, view, track){
  return Math.max(28, Math.round(track * view / Math.max(1, full)));
}

function paintCue(box){
  const w = box.parentElement;
  if (!w || !w.classList.contains("cue")) return;
  const x = box.scrollWidth - box.clientWidth, y = box.scrollHeight - box.clientHeight;
  w.classList.toggle("l", box.scrollLeft > 1);
  w.classList.toggle("r", x - box.scrollLeft > 1);
  w.classList.toggle("u", box.scrollTop > 1);
  w.classList.toggle("d", y - box.scrollTop > 1);

  // A region that is hidden, or not laid out yet, measures zero on both axes - which
  // is not the same statement as "everything fits", so no bar is drawn either way.
  const live = box.clientWidth > 0 && box.clientHeight > 0;
  const hOn = live && x > 1, vOn = live && y > 1;
  w.classList.toggle("hbar", hOn);
  w.classList.toggle("vbar", vOn);
  for (const bar of w.children){
    if (!bar.classList || !bar.classList.contains("sbar")) continue;
    const horiz = bar.classList.contains("h");
    bar.classList.toggle("on", horiz ? hOn : vOn);
    if (!(horiz ? hOn : vOn)) continue;
    const full = horiz ? box.scrollWidth : box.scrollHeight;
    const view = horiz ? box.clientWidth : box.clientHeight;
    const track = (horiz ? bar.clientWidth : bar.clientHeight) - 4;
    const size = thumbSize(full, view, track);
    const room = Math.max(1, track - size);
    const off = 2 + room * (horiz ? box.scrollLeft : box.scrollTop) / Math.max(1, full - view);
    const t = bar.firstChild;
    if (horiz){ t.style.width = size + "px"; t.style.left = off + "px"; }
    else      { t.style.height = size + "px"; t.style.top  = off + "px"; }
  }
}

function renderKeepingTab(){
  keepScroll(() => { renderAll(); showTab(S.tab); });
}
function showTab(id){
  S.tab = id;
  for (const b of document.querySelectorAll("nav button"))
    b.setAttribute("aria-selected", String(b.dataset.tab === id));
  for (const s of document.querySelectorAll("section.tab")) s.hidden = (s.id !== id);
  /* cueScrollers, not paintCue: a hidden pane measures zero, so its bars were sized
     against nothing and have to be redone now it is on screen - and a render that did
     not go through keepScroll leaves fresh .scrollx elements with no wrapper at all, so
     there would be no bar to redo. Wrapping is idempotent and skips what is already
     wrapped, which makes this the cheap way to be certain rather than a second path
     that has to be kept in step with the first. */
  cueScrollers();
}

const FILTER_KEY = {fType:"type", fPhase:"phase", fOut:"out", fProj:"proj",
                    fPers:"pers", fRole:"role", fDept:"dept"};

function fillFilters(){
  const M = S.model;
  const set = (id, vals) => {
    const d = el(id), keep = S.f[FILTER_KEY[id]];
    // A value that has gone from the file cannot stay selected, or the page would be
    // filtered by something the reader can no longer see or clear.
    for (const v of [...keep]) if (!vals.includes(v)) keep.delete(v);
    d.querySelector(".msp").innerHTML =
      `<button class="btn tiny msclear" data-msclear="${att(id)}">Clear</button>`
      + vals.map(v => `<label><input type="checkbox" value="${att(v)}"`
          + `${keep.has(v) ? " checked" : ""}>${esc(v)}</label>`).join("");
    msSummary(d);
  };
  set("fType", [...new Set(Object.values(M.projects).map(p => p.project_type))].filter(Boolean));
  set("fPhase", [...new Set(Object.values(M.projects).map(p => p.clinical_phase))].filter(Boolean));
  set("fOut", [...new Set(Object.values(M.projects).map(p => p.work_scope_type))].filter(Boolean));
  set("fProj", Object.keys(M.projects).sort());
  set("fPers", Object.keys(M.people).sort());
  set("fRole", [...new Set(M.assignments.map(a => a.role_name))].filter(Boolean).sort());
  set("fDept", [...new Set(Object.values(M.people).map(p => p.department))].filter(Boolean).sort());
}

/** What the closed control says: All, the single value, or how many were chosen. */
function msSummary(d){
  const on = [...d.querySelectorAll("input:checked")].map(i => i.value);
  const sum = d.querySelector("summary");
  sum.textContent = on.length === 0 ? "All"
                  : on.length === 1 ? on[0]
                  : `${on.length} selected`;
  sum.title = on.length > 1 ? on.join(", ") : "";
  sum.classList.toggle("on", on.length > 0);
}
function readFilters(){
  for (const [id, key] of Object.entries(FILTER_KEY))
    S.f[key] = new Set([...el(id).querySelectorAll("input:checked")].map(i => i.value));
  const pk = s => { const m = String(s).match(/^(\d{4})-(\d{2})$/); return m ? (+m[1])*12 + (+m[2]-1) : null; };
  const a = pk(el("fFrom").value), b = pk(el("fTo").value);
  if (a !== null) S.from = a;
  if (b !== null) S.to = b;
  if (S.to < S.from) S.to = S.from;
  if (S.to - S.from > 120) S.to = S.from + 120;         // a table 10 years wide helps nobody
  writeHorizon();
}
function writeHorizon(){
  const s = k => `${Math.floor(k/12)}-${String(k%12+1).padStart(2,"0")}`;
  el("fFrom").value = s(S.from); el("fTo").value = s(S.to);
}
/** Pull the horizon in to the months the CURRENT filters actually reach.
 *
 *  Narrow to one project type and the window is still the one the whole portfolio needed,
 *  so a two-year span goes mostly empty and the reader is looking at a chart of nothing
 *  with no way to tell whether that is the answer or the view. The From and To boxes stay
 *  editable and are left alone when the user is the one changing them - this runs only
 *  when a filter DROPDOWN moves.
 *
 *  A filter that matches nothing leaves the window where it was: jumping to an arbitrary
 *  span would hide the fact that the filter is the reason nothing is on screen.
 */
function fitHorizon(){
  const C = S.calc;
  if (!C) return false;
  const pids = new Set(activeProjects()), sids = new Set(activePeople());
  let lo = Infinity, hi = -Infinity;
  const scan = (map, keep) => {
    for (const [key, v] of map){
      if (!(v > 1e-9)) continue;
      const i = key.lastIndexOf("|");
      if (!keep.has(key.slice(0, i))) continue;
      const k = +key.slice(i + 1);
      if (k < lo) lo = k;
      if (k > hi) hi = k;
    }
  };
  scan(C.projMonth, pids);
  scan(C.persMonth, sids);
  if (!isFinite(lo) || !isFinite(hi)) return false;
  if (hi - lo > 120) hi = lo + 120;            // a table ten years wide helps nobody
  S.from = lo; S.to = hi;
  writeHorizon();
  return true;
}

function defaultHorizon(){
  const M = S.model, C = S.calc;
  const now = new Date();
  const today = monthKey(now.getUTCFullYear(), now.getUTCMonth());
  const span = Math.max(1, M.HORIZON);
  // Nothing draws resource yet - a plan started blank, or a file with no assignments.
  // C.lo and C.hi are both 0 then, and anchoring to them would open the page in year 0.
  if (!C.hi){ S.from = today; S.to = today + span - 1; writeHorizon(); return; }
  let from = today;
  if (from < C.lo || from > C.hi) from = C.lo;          // demo data may not span today
  S.from = from;
  S.to = Math.min(C.hi, from + span - 1);
  writeHorizon();
}

/** Take a parsed set of sheets as the workbook now on screen.
 *
 *  Shared by every way in - an .xlsx, a .prap.json, and a plan started blank - so a
 *  blank start is not a lesser mode with its own rules. It opens exactly the tabs an
 *  upload opens, validates by the same rules and exports through the same path; the
 *  only difference is what is in the sheets when it begins.
 */
function adopt(sheets, name, opts){
  opts = opts || {};
  S.headers = {};
  for (const s of REQUIRED_SHEETS)
    S.headers[s] = ((sheets[s] || [])[0] || []).map(h => txt(h)).filter(Boolean);
  const M = buildModel(sheets);
  if (M.fatal){
    showBanner("bad", "The workbook could not be loaded.", M.findings);
    renderReport(M.findings); el("report").showModal();
    return false;
  }
  S.model = M; S.calc = calculate(M);
  S.fileName = name; S.loadedAt = new Date(); S.blank = !!opts.blank;
  S.pending = []; S.saved = 0; S.snapshot = null; S.baseFindings = M.findings.slice();
  S.editedCells.clear(); S.expanded.clear();
  S.selProj = null; S.selPers = null; S.selAsg = null;
  defaultHorizon();
  fillFilters();
  el("empty").hidden = true; el("tabs").hidden = false; el("filterbar").hidden = false;
  el("editbar").hidden = false;
  el("exportBtn").disabled = el("exportJsonBtn").disabled = false;
  const tz = -new Date().getTimezoneOffset() / 60;
  const tzName = (Intl.DateTimeFormat().resolvedOptions().timeZone || "").split("/").pop() || "local";
  const stamp = S.loadedAt.toISOString().slice(0,16).replace("T"," ");
  el("fileline").innerHTML = `${esc(name)} · ${opts.blank ? "started" : "loaded"} ${stamp} `
    + `<span class="tz">(GMT${tz>=0?"+":""}${tz}, ${esc(tzName)})</span>`;
  renderProvenance();
  const errs = M.findings.filter(f => f.sev === "error").length;
  showBanner(errs ? "bad" : "", opts.banner || (errs ? "Loaded with problems." : "Loaded cleanly."),
             M.findings);
  renderAll(); showTab(opts.tab || S.tab);
  cueScrollers();
  return true;
}

