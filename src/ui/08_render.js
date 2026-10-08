/* ============================================================ 8. render helpers */

const esc = s => String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const att = s => esc(s).replace(/"/g,"&quot;");
const el = id => document.getElementById(id);
const fmt = v => S.model.UNIT === "hours" ? (v * S.model.HOURS).toFixed(0) : v.toFixed(2);
const unitLabel = () => S.model.UNIT === "hours" ? "hours" : "FTE";

/* Yield long enough for the browser to actually PAINT.
 *
 * A single `await` is not enough. Resolving a promise runs the continuation as a
 * microtask, which is still inside the current frame - so a "Reading…" banner written
 * just before a one-second parse is in the DOM the whole time and on screen for none of
 * it. Two animation frames is the guarantee: the first is scheduled before the next
 * paint, the second cannot run until that paint has happened.
 *
 * The setTimeout is not a belt-and-braces duplicate. In a backgrounded tab rAF does not
 * fire at all, and a load waiting on it would hang until the tab was looked at again;
 * whichever lands first wins, and the flag makes the loser a no-op.
 *
 * It lives here, in the render helpers, rather than beside the file reader that wanted
 * it first: the Python shell builds without storage/web/load.js and needs this too. */
function paint(){
  return new Promise(done => {
    let settled = false;
    const go = () => { if (!settled){ settled = true; done(); } };
    requestAnimationFrame(() => requestAnimationFrame(go));
    setTimeout(go, 60);
  });
}

function typePill(pid){
  const t = S.model.projects[pid].project_type;
  const k = /^NewDrug CT/.test(t) ? "nd" : /^Biosimilar CT/.test(t) ? "bs" : "ot";
  const tip = CLINICAL_TYPES.has(t)
    ? `<b>${esc(t)}</b><br>A clinical trial. Uses the seven-period set derived from milestone dates, and `
      + `takes its weights from the standard table for its type, phase and work scope.`
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

/* The five highlight colours, as the stylesheet knows them (schema 13). Named here so
   the chart, the legend and the table cell all reach for one definition, and defined as
   CSS variables rather than hexes so each theme can pick a shade that reads on its own
   ground - a yellow that works on white disappears on black. */
const HIGHLIGHT_FILL = {red:"var(--hl-red)", yellow:"var(--hl-yellow)", blue:"var(--hl-blue)",
                        green:"var(--hl-green)", orange:"var(--hl-orange)"};

/* A PERIOD IS DRAWN GRAY UNLESS SOMEBODY CHOSE ITS COLOUR (R-59, schema 14). The bands
   used to take a hue per period name (O-10); asked from the field, the colour now belongs
   to the user: ProjectPeriod.period_highlight picks one of the five, and an unmarked
   period is a quiet gray so the marked ones are what the eye finds. Weight still shades
   both - lighter for a light period, darker for a heavy one - so nothing the old
   colouring said about weight is lost; the period's NAME is on the band and in its
   pop-up. */
const PERIOD_GRAY = "#c4c4c9";
const weightStep = (w, wmax) => (wmax ? Math.min(w, wmax) / wmax : 0);
const bandFill = (n, w, wmax) => mix(PERIOD_GRAY, 1.06 - 0.20 * weightStep(w, wmax));
/** The fill of one period band, as a style string: its chosen colour, or the gray. */
function periodBandStyle(seg, wmax){
  const w = num(seg.weight) || 0, hl = hlToken(seg.period_highlight);
  return hl
    ? {hl, style:`fill:${HIGHLIGHT_FILL[hl]};fill-opacity:${(0.78 + 0.22 * weightStep(w, wmax)).toFixed(2)}`}
    : {hl:"", style:`fill:${bandFill(seg.period_name, w, wmax)}`};
}

