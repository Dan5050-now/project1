/* ============================================================ 8. render helpers */

const esc = s => String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const att = s => esc(s).replace(/"/g,"&quot;");
const el = id => document.getElementById(id);
const fmt = v => S.model.UNIT === "hours" ? (v * S.model.HOURS).toFixed(0) : v.toFixed(2);
const unitLabel = () => S.model.UNIT === "hours" ? "hours" : "FTE";

function typePill(pid){
  const t = S.model.projects[pid].project_type;
  const k = {"NewDrug CT":"nd","Biosimilar CT":"bs"}[t] || "ot";
  const tip = CLINICAL_TYPES.has(t)
    ? `<b>${esc(t)}</b><br>A clinical trial. Uses the seven-period set derived from milestone dates, and `
      + `takes its weights from the standard table for its type and phase.`
    : `<b>${esc(t)}</b><br>A non-trial project. Uses the three-period set — Planning, Develop, Close — `
      + `entered by hand, with hand-entered weights.`;
  return `<span class="ty ${k}" data-tip="${att(tip)}">${esc(t)}</span>`;
}
function phasePill(pid){
  const p = S.model.projects[pid];
  if (!CLINICAL_TYPES.has(p.project_type) || !p.clinical_phase) return "";
  const n = String(p.clinical_phase).replace("Phase ","");
  return `<span class="ph ph${n}">${esc(p.clinical_phase)}</span>`;
}

const SEQ = ["#cde2fb","#b7d3f6","#9ec5f4","#86b6ef","#6da7ec","#5598e7","#3987e5",
             "#2a78d6","#256abf","#1c5cab","#184f95"];
function seqStep(v, vmax){
  if (v <= 0 || vmax <= 0) return null;
  return Math.min(SEQ.length - 1, Math.round((v / vmax) * (SEQ.length - 1)));
}
const BASE7 = ["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#4a3aa7"];
const STEPS = [1.0,0.70,1.30,0.85,1.15,0.55,1.45,0.62];
function mix(hex, f){
  let r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  if (f >= 1){ const t = Math.min(1, f-1); r += (255-r)*t; g += (255-g)*t; b += (255-b)*t; }
  else { r *= f; g *= f; b *= f; }
  return "#" + [r,g,b].map(x => Math.max(0,Math.min(255,Math.round(x))).toString(16).padStart(2,"0")).join("");
}
const projColour = i => mix(BASE7[i % 7], STEPS[Math.floor(i / 7) % STEPS.length]);

/** A project's colour, fixed for the whole session.
 *
 *  Indexed by the project's place in the sorted list of ALL project ids, not by its
 *  position in whatever is being drawn. A colour that changes with the filter, or that
 *  means one project on one tab and another project on the next, is worse than no colour
 *  at all - the reader has to re-learn the key every time the view changes. */
let PCOL = null;
function projColourOf(pid){
  if (!PCOL || PCOL.__for !== S.model){
    PCOL = {__for: S.model};
    Object.keys(S.model.projects).sort().forEach((p, i) => { PCOL[p] = projColour(i); });
  }
  return PCOL[pid] || "var(--other)";
}

/** A person's colour, on the same terms: fixed for the session, keyed on their place in
 *  the sorted list of ALL people, so one person is one colour on every chart that splits
 *  by person. Offset into the palette so a person and a project drawn side by side are
 *  unlikely to collide. */
let SCOL = null;
function persColourOf(sid){
  if (!SCOL || SCOL.__for !== S.model){
    SCOL = {__for: S.model};
    Object.keys(S.model.people).sort().forEach((p, i) => { SCOL[p] = projColour(i + 3); });
  }
  return SCOL[sid] || "var(--other)";
}

const PERIOD_HUE = {
  "Before-Start-up":"#adaca6", "Start-up":"#d9472f",
  "Conduct (interim)":"#3fc795", "Close-out (interim)":"#f2b53d",
  "Conduct (final)":"#159068",  "Close-out (final)":"#d97e0a",
  "After Close-out (final)":"#6f6f68",
  "Planning":"#adaca6", "Develop":"#3fc795", "Close":"#d97e0a",
};
const bandFill = (n, w, wmax) => mix(PERIOD_HUE[n] || "#adaca6",
                                     1.14 - 0.24 * (wmax ? Math.min(w, wmax) / wmax : 0));

