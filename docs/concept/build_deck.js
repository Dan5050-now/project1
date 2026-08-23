// TEA concept overview -> PowerPoint.
// Palette and semantics inherited from the controlled workbooks so severity
// colours mean the same thing here as they do there.
const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";            // 13.33 x 7.5 -- set before any slide
pres.author = "Clinical Programming";
pres.title = "Tumor Evaluation Review Agent - Concept Overview";

// ---- palette (no leading #) ----
const INK   = "16201C";
const DEEP  = "1D4A3A";   // dominant
const DEEPD = "12301F";   // dark ground
const WASH  = "E3EDE7";
const MOSS  = "8FC4A9";   // light accent for dark slides
const PAPER = "FFFFFF";
const GROUND= "F7F8F5";
const RULE  = "D4DAD2";
const MUTE  = "5C665F";
const CRIT  = "8C2F39";
const MAJ   = "B06A1F";
const MIN   = "4A6B8A";

const HEAD = "Cambria";
const BODY = "Calibri";
const MONO = "Courier New";

const W = 13.33, H = 7.5, M = 0.62;

// ---------- helpers (fresh option objects every call) ----------
function chip(s, x, y, text, opt = {}) {
  const w = opt.w || 0.92, h = opt.h || 0.26;
  s.addText(text, {
    x, y, w, h,
    shape: pres.ShapeType.roundRect, rectRadius: 0.04,
    fill: { color: opt.fill || WASH },
    line: { color: opt.line || DEEP, width: opt.lw === undefined ? 0.75 : opt.lw,
            dashType: opt.dash || "solid" },
    fontFace: MONO, fontSize: opt.fs || 9, bold: true,
    color: opt.color || DEEP, align: "center", valign: "middle", margin: 0,
  });
}

function eyebrow(s, x, y, text, color) {
  s.addText(text.toUpperCase(), {
    x, y, w: 8, h: 0.26, fontFace: MONO, fontSize: 10, bold: true,
    color: color || DEEP, charSpacing: 1.6, margin: 0, valign: "middle",
  });
}

function title(s, text, opt = {}) {
  s.addText(text, {
    x: M, y: opt.y || 0.84, w: opt.w || W - 2 * M, h: opt.h || 0.86,
    fontFace: HEAD, fontSize: opt.fs || 32, bold: true,
    color: opt.color || INK, margin: 0, valign: "middle",
  });
}

function lede(s, text, opt = {}) {
  s.addText(text, {
    x: M, y: opt.y || 1.74, w: opt.w || 11.2, h: opt.h || 0.82,
    fontFace: BODY, fontSize: opt.fs || 14, color: opt.color || MUTE,
    margin: 0, lineSpacing: 19, valign: "top",
  });
}

function card(s, x, y, w, h, opt = {}) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.05,
    fill: { color: opt.fill || PAPER },
    line: { color: opt.line || RULE, width: opt.lw === undefined ? 1 : opt.lw },
    shadow: opt.shadow === false ? undefined
      : { type: "outer", angle: 90, blur: 8, offset: 0.04, color: "16201C", opacity: 0.1 },
  });
}

function darkSlide(kicker, headline, sub) {
  const s = pres.addSlide();
  s.background = { color: DEEPD };
  eyebrow(s, M, 2.5, kicker, MOSS);
  s.addText(headline, {
    x: M, y: 2.85, w: 10.4, h: 1.5, fontFace: HEAD, fontSize: 40, bold: true,
    color: PAPER, margin: 0, valign: "middle",
  });
  if (sub) {
    s.addText(sub, {
      x: M, y: 4.4, w: 9.6, h: 0.9, fontFace: BODY, fontSize: 15,
      color: WASH, margin: 0, lineSpacing: 21, valign: "top",
    });
  }
  return s;
}

function footer(s, n) {
  s.addText("TEA concept overview", {
    x: M, y: H - 0.56, w: 4, h: 0.24, fontFace: MONO, fontSize: 8,
    color: MUTE, margin: 0, valign: "middle",
  });
  s.addText(String(n), {
    x: W - M - 0.6, y: H - 0.56, w: 0.6, h: 0.24, fontFace: MONO, fontSize: 8,
    color: MUTE, align: "right", margin: 0, valign: "middle",
  });
}

// =====================================================================
// 1 - TITLE
// =====================================================================
let s = pres.addSlide();
s.background = { color: DEEPD };
s.addText("Tumor Evaluation", {
  x: M, y: 1.95, w: 11.5, h: 0.87, fontFace: HEAD, fontSize: 50, bold: true,
  color: PAPER, margin: 0, valign: "middle",
});
s.addText("Review Agent", {
  x: M, y: 2.82, w: 11.5, h: 0.95, fontFace: HEAD, fontSize: 50, bold: true,
  color: MOSS, margin: 0, valign: "middle",
});
s.addText(
  "How the system is put together, what each part does, and who is responsible for it.",
  { x: M, y: 4.0, w: 8.8, h: 0.6, fontFace: BODY, fontSize: 16, color: WASH,
    margin: 0, lineSpacing: 23, valign: "top" });
let cx1 = M;
["RECIST 1.1 + iRECIST", "85 REVIEW POINTS", "83 LIVE"].forEach((t) => {
  const cw = t.length * 0.105 + 0.34;
  chip(s, cx1, 4.95, t, { w: cw, h: 0.3, fill: DEEPD, line: MOSS, color: MOSS, fs: 9 });
  cx1 += cw + 0.22;
});
s.addText("Concept overview  ·  derived from TEA-PLAN-001 v1.0.0 and TEA-SPEC-001 v1.2.0", {
  x: M, y: 6.5, w: 11, h: 0.3, fontFace: MONO, fontSize: 9, color: "6E7D72",
  margin: 0, valign: "middle" });
s.addNotes("This deck is an orientation map. It carries no independent authority: where it disagrees with the plan or the specification, those documents win.");

// =====================================================================
// 2 - WHAT IT DOES
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "What the agent does");
title(s, "It re-derives the response data, then argues with it");
lede(s, "Every subject, every timepoint. The agent recomputes what the data should say under the guideline and the protocol, compares that against what was collected, and reconciles the difference against the query history before showing anyone anything.");

const whatCards = [
  ["RE-DERIVE", "Sum of diameters, nadir, percent change, all four response components, best overall response, progression dates.", DEEP],
  ["DETECT", "85 review points across 7 families - arithmetic mismatches and guideline-conformance failures alike.", DEEP],
  ["RECONCILE", "Suppress duplicates of open queries. Judge whether a past answer already justified the data.", DEEP],
  ["EXPLAIN", "Five reviewer-facing texts per finding, plus a confidence rate saying how likely it is to be a correct query.", DEEP],
];
whatCards.forEach((c, i) => {
  const x = M + i * 3.0, y = 2.66;
  card(s, x, y, 2.78, 2.15);
  chip(s, x + 0.22, y + 0.24, c[0], { w: 1.35, h: 0.28, fs: 9 });
  s.addText(c[1], { x: x + 0.22, y: y + 0.68, w: 2.34, h: 1.35, fontFace: BODY,
    fontSize: 11.5, color: MUTE, margin: 0, lineSpacing: 16, valign: "top" });
});
card(s, M, 5.14, 11.85, 0.78, { fill: WASH, line: DEEP, shadow: false });
s.addText("The agent produces suspicions. A qualified person confirms every issue and issues every query manually.", {
  x: M + 0.3, y: 5.14, w: 11.25, h: 0.78, fontFace: BODY, fontSize: 13.5, italic: true,
  color: DEEP, margin: 0, valign: "middle" });
footer(s, 2);
s.addNotes("Note the last line: the agent has no write path to the EDC. That is what keeps it decision support rather than a system of record.");

// =====================================================================
// 3 - DIVIDER: organising idea
// =====================================================================
s = darkSlide("The organising idea", "Three clocks,\nrunning at different speeds",
  "Most confusion about this system comes from reading it as one long process. It is three, ticking at different rates with different people involved.");
s.addNotes("If someone is lost, ask which clock they are asking about. Nearly every 'when does that happen' question resolves immediately.");

// =====================================================================
// 4 - THREE CLOCKS
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Three clocks");
title(s, "Different cadence, different people, different output", { fs: 30 });

const clocks = [
  ["ONCE - FOR THE PRODUCT", "Build the agent",
   "Six delivery steps, each with an approval gate. Produces the engine, the rule pack and the web application.",
   [["Runs", "Once, then change-controlled"], ["Owns", "Clinical programming + CDM"], ["Yields", "Software and a frozen rule pack"]]],
  ["ONCE - PER STUDY", "Configure for a trial",
   "The intake assistant reads the protocol, proposes every parameter the rules depend on, and waits for a human to confirm each one.",
   [["Runs", "Before the first review run"], ["Owns", "Study data manager + medical monitor"], ["Yields", "A signed-off configuration"]]],
  ["EVERY - DATA CUT", "Review the data",
   "Ingest, derive, run the rules, reconcile against past queries, score confidence, write the narrative.",
   [["Runs", "On demand, per data cut"], ["Owns", "Whoever reviews that study"], ["Yields", "Findings and draft query text"]]],
];
clocks.forEach((c, i) => {
  const x = M + i * 4.03, y = 1.80, w = 3.78;
  card(s, x, y, w, 4.3);
  chip(s, x + 0.24, y + 0.26, c[0], { w: 2.15, h: 0.28, fs: 8 });
  s.addText(c[1], { x: x + 0.24, y: y + 0.68, w: w - 0.48, h: 0.42, fontFace: HEAD,
    fontSize: 19, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(c[2], { x: x + 0.24, y: y + 1.16, w: w - 0.48, h: 1.15, fontFace: BODY,
    fontSize: 11.5, color: MUTE, margin: 0, lineSpacing: 16, valign: "top" });
  s.addShape(pres.ShapeType.line, { x: x + 0.24, y: y + 2.18, w: w - 0.48, h: 0,
    line: { color: RULE, width: 1 } });
  c[3].forEach(([k, v], j) => {
    const ry = y + 2.38 + j * 0.62;
    s.addText(k.toUpperCase(), { x: x + 0.24, y: ry, w: 0.85, h: 0.24, fontFace: MONO,
      fontSize: 8, color: MUTE, margin: 0, valign: "top" });
    s.addText(v, { x: x + 1.12, y: ry, w: w - 1.36, h: 0.55, fontFace: BODY,
      fontSize: 11, color: INK, margin: 0, lineSpacing: 14, valign: "top" });
  });
});
footer(s, 4);
s.addNotes("Clock one is where we are now, at Step 2. Clocks two and three do not start until the software exists.");

// =====================================================================
// 5 - THE ARCHITECTURAL RULE
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "The rule that explains everything else");
title(s, "Code computes. The model explains.");
lede(s, "Every number and every verdict comes from ordinary deterministic code. This single split is why the same verdicts come out of a commercial API and a locally hosted model, and why validation stays tractable.", { w: 11.4 });

card(s, M, 2.62, 5.75, 2.95, { fill: PAPER });
chip(s, M + 0.3, 2.88, "DETERMINISTIC", { w: 1.8, h: 0.28, fs: 9 });
s.addText("The model never...", { x: M + 0.3, y: 3.32, w: 5.1, h: 0.32, fontFace: HEAD,
  fontSize: 17, bold: true, color: INK, margin: 0, valign: "middle" });
s.addText([
  { text: "does arithmetic, percent change or nadir selection", options: { bullet: true, breakLine: true } },
  { text: "creates, deletes or overrides a finding", options: { bullet: true, breakLine: true } },
  { text: "decides a response category", options: { bullet: true, breakLine: true } },
  { text: "suppresses a critical finding", options: { bullet: true, breakLine: true } },
  { text: "sets the confidence rate directly", options: { bullet: true } },
], { x: M + 0.36, y: 3.74, w: 5.05, h: 1.72, fontFace: BODY, fontSize: 12,
     color: MUTE, margin: 0, paraSpaceAfter: 6, valign: "top" });

card(s, M + 6.1, 2.62, 5.75, 2.95, { fill: WASH, line: DEEP });
chip(s, M + 6.4, 2.88, "LLM-ASSISTED", { w: 1.75, h: 0.28, fs: 9, fill: PAPER, dash: "dash" });
s.addText("The model does...", { x: M + 6.4, y: 3.32, w: 5.1, h: 0.32, fontFace: HEAD,
  fontSize: 17, bold: true, color: INK, margin: 0, valign: "middle" });
s.addText([
  { text: "write the reviewer-facing explanation from validated evidence", options: { bullet: true, breakLine: true } },
  { text: "draft the query in the sponsor's house style", options: { bullet: true, breakLine: true } },
  { text: "read free text - lesion descriptions, query answers", options: { bullet: true, breakLine: true } },
  { text: "judge where the guideline itself asks for judgement", options: { bullet: true } },
], { x: M + 6.46, y: 3.74, w: 5.05, h: 1.72, fontFace: BODY, fontSize: 12,
     color: MUTE, margin: 0, paraSpaceAfter: 6, valign: "top" });

s.addText("If the model is unavailable the run still completes. Every LLM task has a deterministic template fallback - the findings get plainer, never wrong.", {
  x: M, y: 5.78, w: 11.85, h: 0.55, fontFace: BODY, fontSize: 12.5, italic: true,
  color: DEEP, margin: 0, valign: "middle" });
footer(s, 5);
s.addNotes("This is the answer to 'can we trust an LLM with endpoint-critical data'. It never touches the verdict.");

// =====================================================================
// 6 - DIVIDER: development
// =====================================================================
s = darkSlide("Clock one", "Building it", "Six steps, strictly sequential, because each one's output is the next one's input. The gates are the real schedule risk - not the build effort.");
s.addNotes("Step 1 is approved. Step 2 is in review round 2.");

// =====================================================================
// 7 - DELIVERY STEPS
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Development process");
title(s, "Six steps and the gates between them");

const steps = [
  ["STEP 1", "Development plan", "TEA-PLAN-001", "Approved 17 Aug", "done"],
  ["STEP 2", "Programming spec", "TEA-SPEC-001", "Rules done; wording next", "now"],
  ["STEP 3", "Prototype output", "Dummy dataset", "Findings read by humans", ""],
  ["STEP 4", "UI design", "8 screens", "No code before approval", ""],
  ["STEP 5", "Code generation", "Engine, rules, app", "Validation package", ""],
  ["STEP 6", "Finalisation", "UAT on a real study", "Release 1.0.0", ""],
];
const sw = 1.86, sgap = 0.14, sx0 = M;
steps.forEach((st, i) => {
  const x = sx0 + i * (sw + sgap), y = 2.0;
  const done = st[4] === "done", now = st[4] === "now";
  card(s, x, y, sw, 2.15, {
    fill: done ? DEEP : (now ? WASH : PAPER),
    line: done ? DEEP : (now ? DEEP : RULE),
    lw: now ? 1.75 : 1,
  });
  s.addText(st[0], { x: x + 0.16, y: y + 0.16, w: sw - 0.32, h: 0.24, fontFace: MONO,
    fontSize: 9, bold: true, color: done ? MOSS : (now ? DEEP : MUTE), margin: 0, valign: "middle" });
  s.addText(st[1], { x: x + 0.16, y: y + 0.46, w: sw - 0.32, h: 0.6, fontFace: HEAD,
    fontSize: 14, bold: true, color: done ? PAPER : INK, margin: 0, valign: "top" });
  s.addText(st[2], { x: x + 0.16, y: y + 1.16, w: sw - 0.32, h: 0.3, fontFace: BODY,
    fontSize: 10.5, color: done ? WASH : MUTE, margin: 0, valign: "top" });
  s.addText(st[3], { x: x + 0.16, y: y + 1.5, w: sw - 0.32, h: 0.5, fontFace: BODY,
    fontSize: 10, color: done ? MOSS : (now ? MAJ : MUTE), margin: 0, lineSpacing: 13, valign: "top" });
  if (i < 5) {
    const gx = x + sw + sgap / 2;
    s.addShape(pres.ShapeType.ellipse, { x: gx - 0.075, y: y + 1.0, w: 0.15, h: 0.15,
      fill: { color: GROUND }, line: { color: DEEP, width: 1.25 } });
  }
});
const gates = ["CDM + MM", "rule pack frozen", "output accepted", "design approved", "tests green"];
gates.forEach((g, i) => {
  const gx = sx0 + (i + 1) * (sw + sgap) - sgap / 2;
  s.addText("GATE\n" + g, { x: gx - 0.85, y: 4.28, w: 1.7, h: 0.55, fontFace: MONO,
    fontSize: 7.5, color: MUTE, align: "center", margin: 0, lineSpacing: 10, valign: "top" });
});
s.addText("The rule pack freezes at the Step 2 gate. That makes the specification review the most consequential meeting in the schedule.", {
  x: M, y: 5.35, w: 11.85, h: 0.5, fontFace: BODY, fontSize: 13, italic: true,
  color: DEEP, margin: 0, valign: "middle" });
footer(s, 7);
s.addNotes("Steps 3 and 6 need a pilot study chosen. That decision is still open.");

// =====================================================================
// 8 - DIVIDER: review run
// =====================================================================
s = darkSlide("Clocks two and three", "Inside one review run",
  "Eleven components in a fixed order. Four phases, from reading the protocol once per study to recording what the reviewer decided.");

// =====================================================================
// 9 - PIPELINE
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Process flow");
title(s, "Eleven components, four phases");

const phases = [
  ["SET UP", "Once per study", [["AC-11", "Protocol intake", "llm"]],
   "Summarises every parameter the rules depend on, for a human to confirm."],
  ["DERIVE", "Every run", [["AC-01", "Ingestion", "det"], ["AC-02", "Config resolve", "det"], ["AC-03", "Derivations", "det"]],
   "Maps the export to the canonical model, then computes the arithmetic every rule depends on."],
  ["DETECT", "Every run", [["AC-04", "Rule engine", "det"], ["AC-05", "Adjudicator", "llm"]],
   "Runs the 83 live review points. The model only judges where the guideline asks for judgement."],
  ["ASSEMBLE", "Every run", [["AC-06", "Query reconcile", "hyb"], ["AC-07", "Confidence", "det"], ["AC-08", "Narrative", "llm"], ["AC-09", "Reporting", "det"], ["AC-10", "Feedback", "det"]],
   "Where hundreds of raw findings become a ranked worklist a person can actually work through."],
];
const pw = [2.35, 2.95, 2.35, 3.85], pgap = 0.16;
let px = M;
phases.forEach((ph, i) => {
  const y = 1.95, w = pw[i], h = 2.92;
  card(s, px, y, w, h);
  s.addText(ph[0], { x: px + 0.2, y: y + 0.18, w: w - 0.4, h: 0.3, fontFace: HEAD,
    fontSize: 16, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(ph[1], { x: px + 0.2, y: y + 0.5, w: w - 0.4, h: 0.22, fontFace: MONO,
    fontSize: 8, color: MUTE, margin: 0, valign: "middle" });
  const cols = ph[2].length > 3 ? 2 : 1;
  ph[2].forEach((c, j) => {
    const cw = cols === 2 ? (w - 0.5) / 2 : w - 0.4;
    const cx = px + 0.2 + (cols === 2 ? (j % 2) * (cw + 0.1) : 0);
    const cy = y + 0.84 + (cols === 2 ? Math.floor(j / 2) : j) * 0.42;
    const mode = c[2];
    chip(s, cx, cy, c[0] + "  " + c[1], {
      w: cw, h: 0.34, fs: 8,
      fill: mode === "det" ? PAPER : WASH,
      dash: mode === "det" ? "solid" : (mode === "hyb" ? "sysDash" : "dash"),
      lw: 1,
    });
  });
  const listH = (cols === 2 ? Math.ceil(ph[2].length / 2) : ph[2].length) * 0.42;
  s.addText(ph[3], { x: px + 0.2, y: y + 0.92 + listH, w: w - 0.4, h: h - 1.1 - listH,
    fontFace: BODY, fontSize: 10.5, color: MUTE, margin: 0, lineSpacing: 14, valign: "top" });
  if (i < 3) {
    s.addShape(pres.ShapeType.rightArrow, {
      x: px + w + 0.02, y: y + 1.5, w: 0.12, h: 0.2,
      fill: { color: DEEP }, line: { color: DEEP, width: 0 } });
  }
  px += w + pgap;
});
s.addText("Plain outline = deterministic code   \u00b7   Tinted + dashed = LLM-assisted   \u00b7   Mixed dash = hybrid", {
  x: M, y: 5.05, w: 11.85, h: 0.3, fontFace: BODY, fontSize: 11.5, color: MUTE,
  margin: 0, valign: "middle" });
s.addText("Order runs left to right. Nothing downstream can change a verdict computed upstream.", {
  x: M, y: 5.42, w: 11.85, h: 0.3, fontFace: BODY, fontSize: 11.5, italic: true,
  color: DEEP, margin: 0, valign: "middle" });
footer(s, 9);
s.addNotes("AC-06 is hybrid: deterministic matching on rule id and field, with the model reading free-text query answers.");

// =====================================================================
// 10 - DIVIDER: data
// =====================================================================
s = darkSlide("Source data to output data", "Where the data comes from,\nand where it goes",
  "Five sources, one canonical model, one finding record - and two loops that close the system.");

// =====================================================================
// 11 - LINEAGE
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Data relationship");
title(s, "From EDC export to an issued query");

const lanes = [
  ["SOURCE DATA", PAPER, RULE, [
    "Veeva EDC export", "CRF specification", "Protocol + imaging charter",
    "Query report", "Cross-domain data"]],
  ["CANONICAL MODEL", WASH, DEEP, [
    "TEA-CTR-001", "12 entities", "Units normalised",
    "Lesion identity resolved", "No source field names"]],
  ["AGENT COMPUTATION", PAPER, RULE, [
    "D-01 ... D-10 derivations", "83 live review points",
    "7 rule families", "Confidence rate", "Cascade grouping"]],
  ["OUTPUT DATA", WASH, DEEP, [
    "TEA-CTR-002 finding", "Severity + confidence",
    "Evidence + trace", "Five reviewer texts", "Coverage report"]],
  ["HUMAN ACTION", PAPER, RULE, [
    "Review and disposition", "Approved query text",
    "Issued manually", "Never automatic", "Site answers"]],
];
const lw2 = 2.28, lgap = 0.15;
lanes.forEach((ln, i) => {
  const x = M + i * (lw2 + lgap), y = 1.95, h = 2.85;
  card(s, x, y, lw2, h, { fill: ln[1], line: ln[2], lw: ln[2] === DEEP ? 1.25 : 1 });
  s.addText(ln[0], { x: x + 0.16, y: y + 0.16, w: lw2 - 0.32, h: 0.24, fontFace: MONO,
    fontSize: 8, bold: true, color: DEEP, margin: 0, valign: "middle" });
  ln[3].forEach((it, j) => {
    const isLast = i === 4 && j === 3;
    s.addText(it, { x: x + 0.16, y: y + 0.52 + j * 0.44, w: lw2 - 0.32, h: 0.4,
      fontFace: BODY, fontSize: 10.5, color: isLast ? CRIT : INK, margin: 0,
      bold: isLast, lineSpacing: 13, valign: "top" });
  });
  if (i < 4) {
    s.addShape(pres.ShapeType.rightArrow, { x: x + lw2 + 0.015, y: y + 1.3, w: 0.12, h: 0.2,
      fill: { color: DEEP }, line: { color: DEEP, width: 0 } });
  }
});
// two return paths, as a band rather than lines a label would cut in half
card(s, M, 5.0, 11.85, 1.28, { fill: WASH, line: DEEP, shadow: false });
s.addText("TWO LOOPS CLOSE THE SYSTEM", { x: M + 0.3, y: 5.14, w: 5, h: 0.24,
  fontFace: MONO, fontSize: 8.5, bold: true, color: DEEP, margin: 0, valign: "middle" });
[["Site answers return as source data at the next data cut, where the reconciler judges whether the answer justified the data.", 5.48],
 ["Reviewer dispositions tune the confidence model, so a rule people keep rejecting is down-weighted without a rule release.", 5.83],
].forEach(([t, ly]) => {
  s.addShape(pres.ShapeType.leftArrow, { x: M + 0.3, y: ly + 0.06, w: 0.22, h: 0.16,
    fill: { color: DEEP }, line: { color: DEEP, width: 0 } });
  s.addText(t, { x: M + 0.66, y: ly, w: 10.9, h: 0.3, fontFace: BODY, fontSize: 11.5,
    color: INK, margin: 0, valign: "middle" });
});
footer(s, 11);
s.addNotes("The red text in the last lane is the boundary: the agent has no write path to any external system.");

// =====================================================================
// 12 - ROLES
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Roles and responsibilities");
title(s, "Who owns what, on which clock");

const rows = [
  [{ text: "ACTIVITY" }, { text: "CLOCK" }, { text: "LEADS" }, { text: "APPROVES" }],
  ["Define review points and severities", "Build", "Clinical data management", "Medical monitor"],
  ["Agree confidence base rates", "Build", "Clinical data management", "Medical monitor"],
  ["Implement engine, rules and application", "Build", "Clinical programming", "CDM at each gate"],
  ["Validation package and change control", "Build", "Quality / validation", "Quality / validation"],
  ["Approve model hosting and data egress", "Build", "IT security / privacy", "IT security / privacy"],
  ["Confirm protocol parameter checkpoints", "Per study", "Study data manager", "Medical monitor"],
  ["Map the CRF, verify field availability", "Per study", "Clinical programming", "Study data manager"],
  ["Trigger a run and triage findings", "Per data cut", "Study data manager", "-"],
  ["Adjudicate clinical judgement findings", "Per data cut", "Medical monitor", "Medical monitor"],
  ["Edit and issue the query into the EDC", "Per data cut", "Study data manager", "Study data manager"],
  ["Answer the query, correct the data", "Per data cut", "Investigator site", "Investigator site"],
  ["Review rule performance and retune", "Per data cut", "Clinical data management", "Medical monitor"],
];
const tableRows = rows.map((r, i) => {
  if (i === 0) {
    return r.map((c) => ({
      text: c.text,
      options: { fontFace: MONO, fontSize: 8.5, bold: true, color: DEEP,
                 fill: { color: WASH }, valign: "middle" },
    }));
  }
  return r.map((c, j) => ({
    text: c,
    options: {
      fontFace: j === 1 ? MONO : BODY,
      fontSize: j === 1 ? 8.5 : 10.5,
      bold: j === 0,
      color: j === 0 ? INK : (j === 1 ? DEEP : MUTE),
      fill: { color: i % 2 ? PAPER : GROUND },
      valign: "middle",
    },
  }));
});
s.addTable(tableRows, {
  x: M, y: 1.80, w: 11.85, colW: [4.15, 1.5, 3.1, 3.1],
  rowH: 0.3, border: { type: "solid", color: RULE, pt: 0.5 },
  margin: [3, 7, 3, 7],
});
s.addText("These are responsibilities, not system permissions. Release 1 does not enforce role-based access - anyone may review and approve, because no query is issued automatically.", {
  x: M, y: 6.28, w: 11.85, h: 0.5, fontFace: BODY, fontSize: 12, italic: true,
  color: DEEP, margin: 0, lineSpacing: 16, valign: "middle" });
footer(s, 12);
s.addNotes("OQ-08 settled this at the Step 1 review: review and issuing are often the same person, so strict segregation would add friction without adding control.");

// =====================================================================
// 13 - IDENTIFIER DECODER
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "Reading the documents");
title(s, "What each identifier means");
lede(s, "Identifiers appear constantly across the workbooks. This is which document owns each family.", { w: 11.4, h: 0.4, y: 1.74 });

const dec = [
  ["OBJ / FR / NFR / REG", "Development plan", "Objectives and requirements. Approved, and the parent of everything else."],
  ["AC-01 ... AC-11", "Components", "The eleven runtime parts, in pipeline order."],
  ["D-01 ... D-10", "Derivations", "The arithmetic. One wrong here makes many rules wrong together."],
  ["TE-XX-000", "Review points", "The 85 rules by family. Ids are permanent and never reused, even when retired."],
  ["ID-01 ... ID-08", "Interpretations", "Where the guideline is silent. Each has a default, confirmed per study."],
  ["TEA-CTR-001 / 002", "Data contracts", "What goes in, what comes out. Adapters target these, not each other."],
  ["P-ADJ / P-MATCH / P-NARRATE", "Prompt contracts", "Every model call, with its required output schema."],
  ["G-01 ... G-07", "Guardrails", "What the model is structurally prevented from doing."],
];
dec.forEach((d, i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.0, y = 2.32 + row * 1.02;
  card(s, x, y, 5.82, 0.88, { shadow: false });
  s.addText(d[0], { x: x + 0.18, y: y + 0.12, w: 2.5, h: 0.24, fontFace: MONO,
    fontSize: 8.5, bold: true, color: DEEP, margin: 0, valign: "middle" });
  s.addText(d[1], { x: x + 2.75, y: y + 0.12, w: 2.9, h: 0.24, fontFace: BODY,
    fontSize: 11.5, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(d[2], { x: x + 0.18, y: y + 0.4, w: 5.46, h: 0.42, fontFace: BODY,
    fontSize: 10, color: MUTE, margin: 0, lineSpacing: 13, valign: "top" });
});
footer(s, 13);

// =====================================================================
// 14 - FIVE THINGS
// =====================================================================
s = pres.addSlide(); s.background = { color: GROUND };
eyebrow(s, M, 0.52, "If you read nothing else");
title(s, "Five things that decide whether this works");

const five = [
  ["The deterministic split holds, or it doesn't", "It is what makes local hosting, reproducibility and validation possible at once. Erode it and all three go."],
  ["Silence is a feature", "A reviewer handed 400 findings reviews none. Deduplication, reconciliation and ranking are load-bearing, not polish."],
  ["Confidence must be calibrated, not asserted", "A confidence rate people learn to distrust is worse than none - it invites issuing queries unread."],
  ["Coverage has to be published", "The danger is assuming the agent checked something it never checked. Every run states what was not evaluated."],
  ["The rule pack must stay cheap to change", "Adding a review point is a declarative change with its own tests. The moment it needs engine surgery, the catalog stops growing."],
];
five.forEach((f, i) => {
  const y = 1.85 + i * 0.98;
  s.addShape(pres.ShapeType.ellipse, { x: M, y: y + 0.01, w: 0.42, h: 0.42,
    fill: { color: DEEP }, line: { color: DEEP, width: 0 } });
  s.addText(String(i + 1), { x: M, y: y + 0.01, w: 0.42, h: 0.42, fontFace: MONO,
    fontSize: 11, bold: true, color: PAPER, align: "center", margin: 0, valign: "middle" });
  s.addText(f[0], { x: M + 0.66, y: y + 0.04, w: 11.0, h: 0.32, fontFace: HEAD,
    fontSize: 15, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(f[1], { x: M + 0.66, y: y + 0.38, w: 11.0, h: 0.42, fontFace: BODY,
    fontSize: 11.5, color: MUTE, margin: 0, lineSpacing: 15, valign: "top" });
});
footer(s, 14);

// =====================================================================
// 15 - STATUS / CLOSE
// =====================================================================
s = pres.addSlide(); s.background = { color: DEEPD };
eyebrow(s, M, 1.5, "Where we are", MOSS);
s.addText("Step 2, part-done", {
  x: M, y: 1.85, w: 11, h: 0.85, fontFace: HEAD, fontSize: 38, bold: true,
  color: PAPER, margin: 0, valign: "middle" });

const status = [
  ["RULES SETTLED", "All 85 rules dispositioned over two rounds. Logic, severities and confidence base rates confirmed; 2 rules retired."],
  ["OPEN NOW", "Rule_Messages - the query wording a site actually reads. Reviewed on its own, by people who talk to sites."],
  ["THEN", "The rule pack freezes and Step 3 begins: prototype output on a curated dummy dataset."],
];
status.forEach((st, i) => {
  const x = M + i * 4.03, y = 3.1;
  s.addShape(pres.ShapeType.roundRect, { x, y, w: 3.78, h: 1.85, rectRadius: 0.05,
    fill: { color: "18452F" }, line: { color: "2C5C44", width: 1 } });
  s.addText(st[0], { x: x + 0.24, y: y + 0.22, w: 3.3, h: 0.26, fontFace: MONO,
    fontSize: 9, bold: true, color: MOSS, margin: 0, valign: "middle" });
  s.addText(st[1], { x: x + 0.24, y: y + 0.6, w: 3.3, h: 1.05, fontFace: BODY,
    fontSize: 12, color: WASH, margin: 0, lineSpacing: 16, valign: "top" });
});
s.addText("This overview is derived from the controlled documents and carries no independent authority.\nWhere it disagrees with TEA-PLAN-001 or TEA-SPEC-001, those documents win.", {
  x: M, y: 5.5, w: 11, h: 0.7, fontFace: BODY, fontSize: 12, color: "9FB3A6",
  margin: 0, lineSpacing: 17, valign: "top" });
s.addNotes("Close by naming the next decision: reviewing the query wording in Rule_Messages. Nothing freezes until that is accepted.");

pres.writeFile({ fileName: "/home/user/project1/docs/concept/TEA-concept-overview.pptx" })
  .then((f) => console.log("written:", f));
