/* The FTE calculation, as a slide deck.
 *
 *   node tools/build_fte_deck.js      ->  docs/PRAP_FTE_Calculation_v1.0.pptx
 *
 * Every figure in it was READ OUT OF THE RUNNING APPLICATION over
 * templates/PRAP_SourceData_Dummy_10x10_v1.5.xlsx - the six rows of Kim S. in
 * February 2027, the project total beside them, the absorption example. They are
 * transcribed here rather than computed, so if the arithmetic ever changes this file
 * is stale: re-trace before re-issuing rather than editing a number in place.
 *
 * Requires pptxgenjs. The deck is checked with the pptx skill's validate.py; this
 * sandbox has no working LibreOffice, so slides cannot be rasterised here and the
 * layout is verified geometrically instead.
 */
const pptxgen = require("pptxgenjs");

const P = {
  deep:   "0A2E2A",   // near-black teal — title + closing
  teal:   "0F5A52",   // dominant
  teal2:  "17796E",   // lighter teal for secondary chips
  tint:   "E4EFEC",   // pale card fill
  tint2:  "F2F7F5",
  ink:    "1B2422",
  mute:   "6B7674",
  faint:  "97A3A0",
  amber:  "B36A12",   // semantic only — "falls back to 1.00"
  amberBg:"FBF0DF",
  white:  "FFFFFF",
  line:   "D6E0DD",
};

const HEAD = "Cambria";
const BODY = "Calibri";
const MONO = "Courier New";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";           // 13.3 x 7.5
pres.author = "PRAP";
pres.title = "Anatomy of an FTE";

const W = 13.3, H = 7.5, M = 0.62;

// ---------------------------------------------------------------- helpers
function titleOf(s, text, sub) {
  s.addText(text, {
    x: M, y: 0.52, w: W - 2 * M, h: 0.72, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 34, bold: true, color: P.ink, align: "left",
  });
  if (sub) {
    s.addText(sub, {
      x: M, y: 1.24, w: W - 2 * M, h: 0.42, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 14.5, color: P.mute,
    });
  }
}

/** The motif: the four terms of the formula, with one lit. Repeated on every term slide. */
function formulaStrip(s, y, active, opts) {
  opts = opts || {};
  const terms = [
    { k: "period weight", w: 2.30 },
    { k: "role factor ÷ sharers", w: 3.15 },
    { k: "person weight", w: 2.30 },
    { k: "coverage", w: 1.90 },
  ];
  let x = opts.x === undefined ? M + 0.95 : opts.x;
  const h = opts.h || 0.52;
  s.addText("FTE =", {
    x: x - 0.95, y: y, w: 0.9, h: h, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 13, color: P.mute, align: "right", valign: "middle",
  });
  terms.forEach((t, i) => {
    const on = i === active;
    s.addShape(pres.ShapeType.roundRect, {
      x: x, y: y, w: t.w, h: h, rectRadius: 0.08,
      fill: { color: on ? P.teal : P.tint },
      line: { color: on ? P.teal : P.line, width: 0.75 },
    });
    s.addText(t.k, {
      x: x, y: y, w: t.w, h: h, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 11.5, bold: on,
      color: on ? P.white : P.mute, align: "center", valign: "middle",
    });
    x += t.w;
    if (i < terms.length - 1) {
      s.addText("×", {
        x: x, y: y, w: 0.36, h: h, isTextBox: true, margin: 0,
        fontFace: BODY, fontSize: 15, color: P.faint, align: "center", valign: "middle",
      });
      x += 0.36;
    }
  });
}

function stepBadge(s, x, y, n) {
  s.addShape(pres.ShapeType.ellipse, {
    x: x, y: y, w: 0.52, h: 0.52, fill: { color: P.teal }, line: { color: P.teal },
  });
  s.addText(n, {
    x: x, y: y, w: 0.52, h: 0.52, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 13, bold: true, color: P.white,
    align: "center", valign: "middle",
  });
}

function card(s, o) {
  s.addShape(pres.ShapeType.roundRect, {
    x: o.x, y: o.y, w: o.w, h: o.h, rectRadius: 0.06,
    fill: { color: o.fill || P.tint2 }, line: { color: o.line || P.line, width: 0.75 },
  });
}

/** The amber "if the lookup finds nothing" note. Semantic colour, used nowhere else. */
function fallback(s, o) {
  card(s, { x: o.x, y: o.y, w: o.w, h: o.h, fill: P.amberBg, line: "EBD9BC" });
  s.addText(
    [{ text: "If it finds nothing   ", options: { bold: true, color: P.amber } },
     { text: o.text, options: { color: P.ink } }],
    { x: o.x + 0.22, y: o.y + 0.13, w: o.w - 0.44, h: o.h - 0.26, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 12.5, valign: "middle" });
}

function sourceLine(s, x, y, w, text) {
  s.addText(text, {
    x: x, y: y, w: w, h: 0.3, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 10.5, color: P.faint,
  });
}

// ================================================================ 1. title
{
  const s = pres.addSlide();
  s.background = { color: P.deep };
  s.addText("PRAP  ·  how the numbers are made", {
    x: M, y: 1.55, w: 8, h: 0.34, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 11.5, color: "6FB5A8", charSpacing: 2,
  });
  s.addText("Anatomy of an FTE", {
    x: M, y: 2.0, w: 9.6, h: 1.35, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 58, bold: true, color: P.white,
  });
  s.addText(
    "Every figure the application draws is a sum of one small multiplication, " +
    "done once per assignment per month. This is that multiplication, where each " +
    "of its numbers comes from, and what happens when one is missing.",
    { x: M, y: 3.45, w: 7.9, h: 1.3, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15.5, color: "BFD4CF", lineSpacing: 24 });

  // the formula, quietly, as the thesis
  s.addText("FTE  =  period weight  ×  (role factor ÷ sharers)  ×  " +
            "person weight  ×  coverage",
    { x: M, y: 5.15, w: 11.6, h: 0.5, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 14, color: "8FC9BE" });

  const stamps = [["Engine", "core/06_calculate.js"], ["Schema", "8"],
                  ["1.00 FTE", "160 h / month"]];
  let sx = M;
  stamps.forEach(([k, v]) => {
    s.addText([{ text: k + "  ", options: { color: "6FB5A8" } },
               { text: v, options: { color: "9FBBB5" } }],
      { x: sx, y: 6.35, w: 3.5, h: 0.3, isTextBox: true, margin: 0,
        fontFace: MONO, fontSize: 10.5 });
    sx += 3.7;
  });
  s.addNotes("Every number in PRAP comes from one multiplication per assignment per " +
             "month. Everything else on screen is those numbers added up.");
}

// ================================================================ 2. the formula
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "One multiplication, four numbers",
    "Worked out once for every assignment, in every month that assignment touches.");

  card(s, { x: M, y: 2.0, w: W - 2 * M, h: 1.5, fill: P.tint2 });
  formulaStrip(s, 2.42, -1);

  const cols = [
    ["period weight", "How heavy this stretch of the project is.", "ProjectPeriod"],
    ["role factor ÷ sharers", "What the role costs, split between its holders.", "RoleFactor"],
    ["person weight", "How much of that person this project has.", "Assignment / override"],
    ["coverage", "How much of the calendar month is covered.", "computed"],
  ];
  const cw = (W - 2 * M - 3 * 0.3) / 4;
  cols.forEach(([k, d, src], i) => {
    const x = M + i * (cw + 0.3);
    s.addText(k, { x: x, y: 3.85, w: cw, h: 0.34, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 12, bold: true, color: P.teal });
    s.addText(d, { x: x, y: 4.22, w: cw, h: 0.8, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: P.ink });
    sourceLine(s, x, 5.0, cw, src);
  });

  card(s, { x: M, y: 5.65, w: W - 2 * M, h: 1.05, fill: P.tint });
  s.addText(
    [{ text: "Nothing else enters it. ", options: { bold: true } },
     { text: "There is no fifth hidden factor and no rounding step — and " +
             "capacity_fte is not in the multiplication at all. It is what a " +
             "person’s load is later compared against, never something it is scaled by.",
       options: {} }],
    { x: M + 0.28, y: 5.8, w: W - 2 * M - 0.56, h: 0.75, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, color: P.ink, valign: "middle" });
  s.addNotes("All four terms are resolved for the month, not once per assignment. " +
             "That is what lets figures move on their own when a period boundary is " +
             "crossed or a second person joins a role.");
}

// ================================================================ 3. the window
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "First: which months does this assignment touch?",
    "Resolved before any of the four terms — it decides which months exist at all.");

  stepBadge(s, M, 2.05, "00");

  s.addText("Both assignment dates are optional", {
    x: M + 0.8, y: 2.02, w: 6.4, h: 0.35, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 19, bold: true, color: P.ink });
  s.addText("A blank date means the project’s own, so an assignment with neither " +
    "runs for the whole project — which is what most assignments are. Fill them in " +
    "only for a partial involvement.",
    { x: M + 0.8, y: 2.45, w: 6.4, h: 1.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 14, color: P.ink, lineSpacing: 21 });

  s.addText("The project’s own window is its PERIODS", {
    x: M + 0.8, y: 3.55, w: 6.4, h: 0.35, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 19, bold: true, color: P.ink });
  s.addText("Earliest period_start to latest period_end. Not its milestones — " +
    "several of those mark moments inside the run rather than its edges, and taking " +
    "the window from them stretched projects across months belonging to no period.",
    { x: M + 0.8, y: 3.98, w: 6.4, h: 1.1, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 14, color: P.ink, lineSpacing: 21 });

  fallback(s, { x: M + 0.8, y: 5.25, w: 6.4, h: 0.85,
    text: "the project keeps its own typed start and end dates, and V-12 reports " +
          "that it has no periods." });

  // right: a small worked illustration of coverage
  card(s, { x: 8.15, y: 2.02, w: W - M - 8.15, h: 4.08, fill: P.tint2 });
  s.addText("Coverage, once the window is known", {
    x: 8.45, y: 2.28, w: 3.9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 15, bold: true, color: P.teal });
  s.addText("The fraction of that calendar month’s days the window actually covers.",
    { x: 8.45, y: 2.66, w: 3.9, h: 0.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: P.ink });

  s.addText("A full month", { x: 8.45, y: 3.35, w: 1.85, h: 0.3, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 12.5, color: P.mute });
  s.addText("1.0000", { x: 10.4, y: 3.35, w: 1.95, h: 0.3, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 13, bold: true, color: P.ink, align: "right" });

  s.addText("Ends 1 June", { x: 8.45, y: 3.78, w: 1.85, h: 0.3, isTextBox: true,
    margin: 0, fontFace: BODY, fontSize: 12.5, color: P.mute });
  s.addText("1 ÷ 30 = 0.0333", { x: 10.4, y: 3.78, w: 1.95, h: 0.3, isTextBox: true,
    margin: 0, fontFace: MONO, fontSize: 13, bold: true, color: P.ink, align: "right" });

  s.addText("This is what makes a part-month sharer contribute less with no special " +
    "case anywhere: their coverage is already smaller.",
    { x: 8.45, y: 4.4, w: 3.9, h: 1.0, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: P.mute, lineSpacing: 19 });
  s.addNotes("REQ-CAL-15 and REQ-CAL-17. The periods are the project.");
}

// ================================================================ 4. period weight
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "Period weight", "How heavy this stretch of the project is.");
  formulaStrip(s, 1.75, 0);

  stepBadge(s, M, 2.65, "01");
  s.addText("The period whose span contains the 1st of that month supplies its weight.",
    { x: M + 0.8, y: 2.62, w: 6.5, h: 0.6, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 15, color: P.ink, lineSpacing: 22 });
  sourceLine(s, M + 0.8, 3.28, 6.5, "ProjectPeriod.weight");

  s.addText("A project’s periods are its own rows — derived from its milestones " +
    "for a clinical trial, entered by hand for an ‘Others’ project.",
    { x: M + 0.8, y: 3.68, w: 6.5, h: 0.75, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 14, color: P.ink, lineSpacing: 21 });

  fallback(s, { x: M + 0.8, y: 4.62, w: 6.5, h: 1.0,
    text: "weight 1.00, and V-12 reports the gap. 1.00 is not a neutral choice — " +
          "it silently costs that month at full rate." });

  card(s, { x: 8.15, y: 2.6, w: W - M - 8.15, h: 3.55, fill: P.tint });
  s.addText("The one that surprises people", {
    x: 8.45, y: 2.85, w: 3.9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 15, bold: true, color: P.teal });
  s.addText(
    [{ text: "PeriodWeightStandard is not read here.", options: { bold: true } },
     { text: "\n\nIt is the assumption table the derivation uses to fill in " +
             "ProjectPeriod.weight. Once a period row exists, the calculation reads " +
             "that row.\n\nWhich is why an ‘Others’ project calculates " +
             "perfectly well with no standard rows anywhere.", options: {} }],
    { x: 8.45, y: 3.25, w: 3.9, h: 2.7, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: P.ink, lineSpacing: 20 });
  s.addNotes("Standards fill in the period rows; the calculation reads the period rows.");
}

// ================================================================ 5. role factor
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "Role factor", "What the ROLE costs the project — not what each person holding it costs.");
  formulaStrip(s, 1.75, 1);

  stepBadge(s, M, 2.65, "02");
  s.addText("Looked up on the full composition, in two steps: the project’s own " +
    "work scope first, then the row whose work_scope_type is empty, which stands for " +
    "every scope.",
    { x: M + 0.8, y: 2.6, w: 6.5, h: 0.9, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 14, color: P.ink, lineSpacing: 21 });

  card(s, { x: M + 0.8, y: 3.6, w: 6.5, h: 0.55, fill: P.tint });
  s.addText("project_type · clinical_phase · work_scope_type · " +
    "period_name · role_name",
    { x: M + 0.9, y: 3.6, w: 6.3, h: 0.55, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 10.5, color: P.teal, valign: "middle" });

  fallback(s, { x: M + 0.8, y: 4.35, w: 6.5, h: 1.05,
    text: "factor 1.00, and V-23 names the exact combination and counts the " +
          "person-months it affected." });

  // absorption
  card(s, { x: 8.15, y: 2.6, w: W - M - 8.15, h: 3.9, fill: P.tint2 });
  s.addText("Then: absorption", {
    x: 8.45, y: 2.82, w: 3.9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 15, bold: true, color: P.teal });
  s.addText("If another role names this one in absorbed_by and nobody at all holds it " +
    "that month, its factor is added here. One hop only.",
    { x: 8.45, y: 3.2, w: 3.9, h: 0.85, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: P.ink, lineSpacing: 20 });

  s.addText("Lead data manager, alone on a trial", {
    x: 8.45, y: 4.15, w: 3.9, h: 0.28, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11.5, color: P.mute });
  s.addText("1.23  +  0.49  =  1.72", {
    x: 8.45, y: 4.45, w: 3.9, h: 0.42, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 17, bold: true, color: P.teal });
  s.addText("own factor, plus the absent Clinical Data Associator’s", {
    x: 8.45, y: 4.88, w: 3.9, h: 0.5, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 11.5, color: P.faint });
  s.addText("Delivered as ROWS, not as names in the program — empty the column and " +
    "nothing is absorbed.",
    { x: 8.45, y: 5.5, w: 3.9, h: 0.75, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: P.mute, lineSpacing: 19 });
  s.addNotes("REQ-CAL-16. A trial run without a CDA still has the data to handle, and " +
             "it lands on the lead data manager.");
}

// ================================================================ 6. sharers + person weight
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "Sharers, and person weight",
    "One divides the role’s cost; the other says how much of the person there is.");
  formulaStrip(s, 1.75, 1);

  // left: sharers
  card(s, { x: M, y: 2.65, w: 6.0, h: 3.85, fill: P.tint2 });
  stepBadge(s, M + 0.3, 2.9, "03");
  s.addText("Sharers", { x: M + 1.0, y: 2.92, w: 4.6, h: 0.4, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 20, bold: true, color: P.ink });
  s.addText("How many distinct people hold that same role, on that same project, in " +
    "that month. The factor is divided between them.",
    { x: M + 0.3, y: 3.55, w: 5.4, h: 0.85, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, color: P.ink, lineSpacing: 20 });
  s.addText("0.78  ÷  2  =  0.39 each", {
    x: M + 0.3, y: 4.45, w: 5.4, h: 0.42, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 16, bold: true, color: P.teal });
  s.addText("Per month, so one of two sharers leaving in June returns July to a full " +
    "share by itself. By people, so one person on two rows is one person and does not " +
    "halve their own load.",
    { x: M + 0.3, y: 4.98, w: 5.4, h: 1.2, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: P.mute, lineSpacing: 19 });

  // right: person weight
  card(s, { x: 6.95, y: 2.65, w: W - M - 6.95, h: 3.85, fill: P.tint2 });
  stepBadge(s, 7.25, 2.9, "04");
  s.addText("Person weight", { x: 7.95, y: 2.92, w: 4.6, h: 0.4, isTextBox: true,
    margin: 0, fontFace: HEAD, fontSize: 20, bold: true, color: P.ink });
  s.addText("If a PersonPeriodWeight window covers the 1st of the month, its " +
    "weight_override is used; otherwise the assignment’s own person_weight.",
    { x: 7.25, y: 3.55, w: 5.4, h: 0.9, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13.5, color: P.ink, lineSpacing: 20 });
  s.addText(
    [{ text: "The override REPLACES the weight ", options: { bold: true, color: P.teal } },
     { text: "for its months — it does not multiply it. That is the single thing " +
             "about this sheet most often got wrong.", options: { color: P.ink } }],
    { x: 7.25, y: 4.5, w: 5.4, h: 0.9, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, lineSpacing: 20 });

  fallback(s, { x: 7.25, y: 5.5, w: 5.4, h: 0.75,
    text: "a blank weight is 0.00 — the row contributes nothing." });
  s.addNotes("A weight is a fact only the planner knows; guessing 1.00 would invent load.");
}

// ================================================================ 7. worked example
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "Worked through: Kim S., February 2027",
    "PSN-001 is on six projects that month. Each row is one assignment’s multiplication.");

  const rows = [
    [{ text: "Project", options: { bold: true } },
     { text: "Period that month", options: { bold: true } },
     { text: "Period wt", options: { bold: true, align: "right" } },
     { text: "Role factor", options: { bold: true, align: "right" } },
     { text: "÷ sharers", options: { bold: true, align: "right" } },
     { text: "Person wt", options: { bold: true, align: "right" } },
     { text: "Cov.", options: { bold: true, align: "right" } },
     { text: "FTE", options: { bold: true, align: "right" } }],
    ["PRJ-001  Biosimilar (Healthy) Ph1", "Close-out (final)", "0.95", "0.76", "1", "0.31", "1.00", "0.2238"],
    ["PRJ-002  Biosimilar (Patient) Ph2", "Conduct (interim)", "1.01", "0.78", "2", "0.75", "1.00", "0.2954"],
    ["PRJ-003  NewDrug CT Ph3", "Conduct (final)", "1.38", "0.84", "1", "0.31", "1.00", "0.3594"],
    ["PRJ-005  Biosimilar (Patient) Ph1", "Conduct (interim)", "0.92", "0.74", "1", "0.26", "1.00", "0.1770"],
    ["PRJ-007  Biosimilar (Healthy) Ph3", "Conduct (interim)", "0.82", "0.84", "1", "0.29", "1.00", "0.1998"],
    ["PRJ-009  Others — CDISC migration", "Planning (hand-entered)", "0.80", "1.10", "1", "0.39", "1.00", "0.3432"],
  ].map((r, i) => r.map((c, j) => {
    const cell = typeof c === "string" ? { text: c } : c;
    const o = Object.assign({}, cell.options || {});
    o.align = j >= 2 ? "right" : "left";
    o.fontFace = j >= 2 ? MONO : BODY;
    o.fontSize = i === 0 ? 10 : 11;
    o.color = i === 0 ? P.faint : P.ink;
    if (i === 0) o.bold = true;
    if (j === 7 && i > 0) { o.bold = true; o.color = P.teal; }
    return { text: cell.text, options: o };
  }));
  // the total is drawn as its own band below the table

  s.addTable(rows, {
    x: M, y: 1.85, w: W - 2 * M, colW: [3.25, 2.15, 0.92, 0.98, 0.92, 0.92, 0.72, 1.2],
    rowH: 0.34, border: { type: "solid", color: P.line, pt: 0.5 },
    fill: { color: P.white }, valign: "middle", margin: 0.06,
  });
  // tint the total row
  s.addShape(pres.ShapeType.rect, {
    x: M, y: 1.85 + 0.34 * 7 + 0.03, w: W - 2 * M, h: 0.36,
    fill: { color: P.teal }, line: { color: P.teal },
  });
  s.addText("Monthly personal FTE — PSN-001, Feb 2027", {
    x: M + 0.1, y: 1.85 + 0.34 * 7 + 0.03, w: 8.5, h: 0.36, isTextBox: true, margin: 0,
    fontFace: BODY, fontSize: 12, bold: true, color: P.white, valign: "middle" });
  s.addText("1.5986", {
    x: W - M - 1.3, y: 1.85 + 0.34 * 7 + 0.03, w: 1.2, h: 0.36, isTextBox: true,
    margin: 0, fontFace: MONO, fontSize: 13.5, bold: true, color: P.white,
    align: "right", valign: "middle" });

  card(s, { x: M, y: 4.95, w: W - 2 * M, h: 1.55, fill: P.tint2 });
  s.addText(
    [{ text: "Read one row across.  ", options: { bold: true, color: P.teal } },
     { text: "PRJ-002 is  1.01 × (0.78 ÷ 2) × 0.75 × 1.00 = 0.2954. " +
             "Its factor is halved because a second person holds Project oversight on " +
             "that project that month, and its person weight comes from a " +
             "PersonPeriodWeight row rather than the assignment.\n" +
             "PRJ-009 is an ‘Others’ project: its 0.80 was typed into " +
             "ProjectPeriod, and no PeriodWeightStandard row exists for it anywhere.",
       options: { color: P.ink } }],
    { x: M + 0.28, y: 5.12, w: W - 2 * M - 0.56, h: 1.25, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, lineSpacing: 19 });
  s.addNotes("Read out of the running application over the 10x10 dummy set.");
}

// ================================================================ 8. the two totals
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "The two totals you actually read",
    "The same person-months, added along different axes — which is why they can never disagree.");

  const boxes = [
    { x: M, t: "Monthly personal FTE", v: "1.5986", u: "FTE",
      w: "PSN-001, Feb 2027 — the six rows on the last slide",
      d: "Sum of that person’s assignments for the month, across every project. " +
         "This is what the person utilisation chart plots, and what the over- and " +
         "under-allocation flags are measured against — the only place " +
         "capacity_fte is used." },
    { x: 6.95, t: "Monthly project FTE", v: "2.1095", u: "FTE",
      w: "PRJ-003, Feb 2027 — five people, of whom PSN-001 gave 0.3594",
      d: "Sum of that project’s assignments for the month, across every person. " +
         "This is what the project utilisation chart plots, stacked by person, and " +
         "what the timeline band tooltips report." },
  ];
  boxes.forEach(b => {
    card(s, { x: b.x, y: 2.0, w: 5.73, h: 3.35, fill: P.tint2 });
    s.addText(b.t, { x: b.x + 0.32, y: 2.25, w: 5.1, h: 0.36, isTextBox: true, margin: 0,
      fontFace: HEAD, fontSize: 19, bold: true, color: P.ink });
    s.addText([{ text: b.v, options: { fontSize: 42, bold: true, color: P.teal } },
               { text: "  " + b.u, options: { fontSize: 16, color: P.mute } }],
      { x: b.x + 0.32, y: 2.7, w: 5.1, h: 0.8, isTextBox: true, margin: 0,
        fontFace: MONO });
    s.addText(b.w, { x: b.x + 0.32, y: 3.52, w: 5.1, h: 0.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 11.5, color: P.faint });
    s.addText(b.d, { x: b.x + 0.32, y: 4.0, w: 5.1, h: 1.2, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 12.5, color: P.ink, lineSpacing: 19 });
  });

  card(s, { x: M, y: 5.62, w: W - 2 * M, h: 1.05, fill: P.tint });
  s.addText(
    [{ text: "Everything else is these two, filtered.  ", options: { bold: true, color: P.teal } },
     { text: "Total demand is every person-month in the current filter and horizon " +
             "added up. Change a filter and all of it is recomputed — none of it " +
             "is stored, and none is written to the workbook.", options: { color: P.ink } }],
    { x: M + 0.28, y: 5.78, w: W - 2 * M - 0.56, h: 0.75, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, valign: "middle" });
  s.addNotes("Across its whole timeline the ten-project set comes to 346.59 FTE-months.");
}

// ================================================================ 9. what moves a figure
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "What can move a figure",
    "Five settings on the Config sheet. Two change the arithmetic itself.");

  const rows = [
    ["split_shared_role_fte", "1", true,
     "Set to 0 and each holder of a shared role is charged the whole factor instead of a share. Term 03 disappears."],
    ["absorb_unstaffed_role_factor", "1", true,
     "Set to 0 and an unstaffed role simply costs nothing. On, its factor lands on whoever covers for it."],
    ["over_allocation_fte", "1.50", false,
     "The monthly personal FTE above which a month is flagged. Absolute — not scaled by anyone’s capacity."],
    ["under_allocation_fte  /  _min_months", "0.60 / 3", false,
     "The floor, and how many consecutive months below it before a run is reported. Also absolute."],
    ["fte_hours_per_month", "160", false,
     "Display only. The FTE figure times this is the hours figure; the person-months do not move."],
  ];
  let y = 1.95;
  rows.forEach(([k, def, moves, d]) => {
    card(s, { x: M, y: y, w: W - 2 * M, h: 0.83,
              fill: moves ? P.tint : P.tint2, line: moves ? "C3DAD4" : P.line });
    s.addText(k, { x: M + 0.28, y: y + 0.1, w: 4.0, h: 0.3, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 11.5, bold: true, color: P.ink });
    s.addText("default " + def, { x: M + 0.28, y: y + 0.42, w: 4.0, h: 0.28,
      isTextBox: true, margin: 0, fontFace: BODY, fontSize: 11, color: P.faint });
    if (moves) {
      s.addShape(pres.ShapeType.roundRect, {
        x: M + 4.35, y: y + 0.24, w: 1.72, h: 0.35, rectRadius: 0.06,
        fill: { color: P.teal }, line: { color: P.teal } });
      s.addText("moves figures", { x: M + 4.35, y: y + 0.24, w: 1.72, h: 0.35,
        isTextBox: true, margin: 0, fontFace: BODY, fontSize: 10.5, bold: true,
        color: P.white, align: "center", valign: "middle" });
    }
    s.addText(d, { x: M + 6.25, y: y + 0.1, w: W - 2 * M - 6.5, h: 0.65,
      isTextBox: true, margin: 0, fontFace: BODY, fontSize: 12.5, color: P.ink,
      valign: "middle", lineSpacing: 18 });
    y += 0.95;
  });
  s.addNotes("An import takes the file's Config with it, which is why the application " +
             "now names any setting an import changed.");
}

// ================================================================ 10. quietly wrong
{
  const s = pres.addSlide();
  s.background = { color: P.white };
  titleOf(s, "Where a figure can be quietly wrong",
    "Three lookups fall back to 1.00 — exactly the value that makes a term vanish from a product.");

  const cards = [
    ["V-12", "A month in no period", "The month is costed at full weight, 1.00, as though the period plan covered it."],
    ["V-23", "A role with no factor", "Names the exact composition, and counts the person-months that came out at 1.00."],
    ["V-30", "A setting missing from Config", "A built-in default is in force rather than the plan’s own value."],
  ];
  const cw = (W - 2 * M - 2 * 0.35) / 3;
  cards.forEach(([rule, t, d], i) => {
    const x = M + i * (cw + 0.35);
    card(s, { x: x, y: 2.05, w: cw, h: 2.5, fill: P.amberBg, line: "EBD9BC" });
    s.addShape(pres.ShapeType.roundRect, {
      x: x + 0.28, y: 2.32, w: 0.85, h: 0.36, rectRadius: 0.06,
      fill: { color: P.amber }, line: { color: P.amber } });
    s.addText(rule, { x: x + 0.28, y: 2.32, w: 0.85, h: 0.36, isTextBox: true,
      margin: 0, fontFace: MONO, fontSize: 12, bold: true, color: P.white,
      align: "center", valign: "middle" });
    s.addText(t, { x: x + 0.28, y: 2.85, w: cw - 0.56, h: 0.6, isTextBox: true,
      margin: 0, fontFace: HEAD, fontSize: 17, bold: true, color: P.ink });
    s.addText(d, { x: x + 0.28, y: 3.5, w: cw - 0.56, h: 0.9, isTextBox: true,
      margin: 0, fontFace: BODY, fontSize: 12.5, color: P.ink, lineSpacing: 19 });
  });

  card(s, { x: M, y: 4.8, w: W - 2 * M, h: 1.55, fill: P.tint2 });
  s.addText(
    [{ text: "None of the three refuses your data.\n", options: { bold: true, color: P.teal, fontSize: 15 } },
     { text: "They are reported at full severity and the rows are kept, because a " +
             "missing assumption is a fact about a document somebody else maintains — " +
             "not a fault in the row you just typed. A convenient fallback is dangerous " +
             "precisely because the resulting number looks exactly like an answer.",
       options: { color: P.ink, fontSize: 13 } }],
    { x: M + 0.32, y: 4.98, w: W - 2 * M - 0.64, h: 1.2, isTextBox: true, margin: 0,
      fontFace: BODY, lineSpacing: 20 });
  s.addNotes("Must / conditional / incomplete: only 'must' errors refuse a row.");
}

// ================================================================ 11. closing
{
  const s = pres.addSlide();
  s.background = { color: P.deep };
  s.addText("In one line", {
    x: M, y: 1.75, w: 8, h: 0.34, isTextBox: true, margin: 0,
    fontFace: MONO, fontSize: 11.5, color: "6FB5A8", charSpacing: 2 });
  s.addText("Four numbers, once per assignment per month. Everything else is a sum.", {
    x: M, y: 2.2, w: 10.6, h: 1.6, isTextBox: true, margin: 0,
    fontFace: HEAD, fontSize: 36, bold: true, color: P.white, lineSpacing: 46 });

  s.addText("FTE  =  period weight  ×  (role factor ÷ sharers)  ×  " +
            "person weight  ×  coverage",
    { x: M, y: 4.05, w: 11.8, h: 0.5, isTextBox: true, margin: 0,
      fontFace: MONO, fontSize: 15, color: "8FC9BE" });

  s.addText("Every figure in this deck was read out of the running application over " +
    "PRAP_SourceData_Dummy_10x10_v1.5.xlsx. The same numbers are produced " +
    "independently by two Python implementations, and all 1,227 person-months of the " +
    "62-project set are compared between the four on every test run.",
    { x: M, y: 4.95, w: 9.4, h: 1.4, isTextBox: true, margin: 0,
      fontFace: BODY, fontSize: 13, color: "9FBBB5", lineSpacing: 21 });
  s.addNotes("Four implementations: the browser engine, prap_io.py, " +
             "verify_source_workbook.py, and test_app.py's own reference.");
}

pres.writeFile({ fileName: "docs/PRAP_FTE_Calculation_v1.0.pptx" })
  .then(f => console.log("written:", f));
