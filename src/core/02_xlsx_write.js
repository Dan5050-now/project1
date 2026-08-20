/* ============================================================ 2. XLSX write
   STORED entries only: valid ZIP, no compressor needed, and Excel reads it. The
   cost is file size, which for a workbook of this shape is a few hundred KB.   */

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++){
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(u8){
  let c = 0xFFFFFFFF;
  for (let i = 0; i < u8.length; i++) c = CRC_TABLE[(c ^ u8[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}
const TE = new TextEncoder();

function zipStored(entries){          // [{name, text}] -> Blob
  const chunks = [], dir = [];
  let offset = 0;
  const enc = s => TE.encode(s);
  for (const e of entries){
    const data = enc(e.text), crc = crc32(data), n = enc(e.name);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true);
    lh.setUint16(8, 0, true);                       // stored
    lh.setUint32(14, crc, true);
    lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true);
    lh.setUint16(26, n.length, true);
    chunks.push(new Uint8Array(lh.buffer), n, data);
    const cd = new DataView(new ArrayBuffer(46));
    cd.setUint32(0, 0x02014b50, true); cd.setUint16(4, 20, true); cd.setUint16(6, 20, true);
    cd.setUint16(10, 0, true);
    cd.setUint32(16, crc, true);
    cd.setUint32(20, data.length, true); cd.setUint32(24, data.length, true);
    cd.setUint16(28, n.length, true);
    cd.setUint32(42, offset, true);
    dir.push(new Uint8Array(cd.buffer), n);
    offset += 30 + n.length + data.length;
  }
  const dirSize = dir.reduce((s, d) => s + d.length, 0);
  const eo = new DataView(new ArrayBuffer(22));
  eo.setUint32(0, 0x06054b50, true);
  eo.setUint16(8, entries.length, true); eo.setUint16(10, entries.length, true);
  eo.setUint32(12, dirSize, true); eo.setUint32(16, offset, true);
  return new Blob([...chunks, ...dir, new Uint8Array(eo.buffer)],
                  {type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"});
}

const xesc = s => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");

/** The columns this application COMPUTES rather than reads. They are recomputed on every
 *  import (recomputeDerived), so a value typed into one is discarded and the disagreement
 *  reported as V-13. The template locks them for that reason, and an export has to carry
 *  the same lock or the guard rail disappears the first time a file goes round the loop. */
const DERIVED_COLS = {
  Project:    ["total_period_months"],
  Milestone:  ["project_name"],
  Assignment: ["person_name"],
};

/* Four cell styles, so a cell can be plain or a date and locked or not. An xf with no
   <protection> child is LOCKED by default, which is why only the editable ones say so. */
const ST_PLAIN = 0, ST_DATE = 1, ST_PLAIN_OPEN = 2, ST_DATE_OPEN = 3;

function sheetXml(rows, sheetName){
  // Header row first: it names the columns, so it is what decides which are locked.
  const hdr = (rows[0] || []).map(h => String(h ?? "").trim());
  const derived = new Set(DERIVED_COLS[sheetName] || []);
  const locked = hdr.map(h => derived.has(h));
  const out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'];
  rows.forEach((row, r) => {
    out.push(`<row r="${r+1}">`);
    row.forEach((v, c) => {
      if (v === null || v === undefined || v === "") return;
      const ref = colName(c) + (r + 1);
      const open = derived.size && r > 0 && !locked[c];     // the header row stays locked
      if (v instanceof Date){
        out.push(`<c r="${ref}" s="${open ? ST_DATE_OPEN : ST_DATE}"><v>${dateToSerial(v)}</v></c>`);
      } else if (typeof v === "number" && isFinite(v)){
        out.push(`<c r="${ref}"${open ? ` s="${ST_PLAIN_OPEN}"` : ""}><v>${v}</v></c>`);
      } else {
        out.push(`<c r="${ref}"${open ? ` s="${ST_PLAIN_OPEN}"` : ""} t="inlineStr">`
          + `<is><t xml:space="preserve">${xesc(v)}</t></is></c>`);
      }
    });
    out.push('</row>');
  });
  out.push('</sheetData>');
  // No password: a guard rail, not security. Rows can still be added, removed and sorted;
  // only the column set - which is the schema - is fixed.
  if (derived.size)
    out.push('<sheetProtection sheet="1" objects="0" scenarios="0" formatCells="0" '
      + 'formatColumns="0" formatRows="0" insertRows="0" deleteRows="0" sort="0" '
      + 'autoFilter="0" insertColumns="1" deleteColumns="1" '
      + 'selectLockedCells="0" selectUnlockedCells="0"/>');
  out.push('</worksheet>');
  return out.join("");
}
function colName(i){
  let s = "";
  for (i++; i > 0; i = Math.floor((i - 1) / 26)) s = String.fromCharCode(65 + (i - 1) % 26) + s;
  return s;
}

function buildXlsx(sheetsObj){
  const names = Object.keys(sheetsObj);
  const entries = [
    {name:"[Content_Types].xml", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
      '<Default Extension="xml" ContentType="application/xml"/>' +
      '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
      '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
      names.map((_,i)=>`<Override PartName="/xl/worksheets/sheet${i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>`).join("") +
      '</Types>'},
    {name:"_rels/.rels", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
      '</Relationships>'},
    {name:"xl/workbook.xml", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>' +
      names.map((n,i)=>`<sheet name="${xesc(n)}" sheetId="${i+1}" r:id="rId${i+1}"/>`).join("") +
      '</sheets></workbook>'},
    {name:"xl/_rels/workbook.xml.rels", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
      names.map((_,i)=>`<Relationship Id="rId${i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet${i+1}.xml"/>`).join("") +
      `<Relationship Id="rId${names.length+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
      '</Relationships>'},
    {name:"xl/styles.xml", text:
      '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
      '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
      '<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd"/></numFmts>' +
      '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>' +
      '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>' +
      '<borders count="1"><border/></borders>' +
      '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
      '<cellXfs count="4">' +
      '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
      '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' +
      // the two unlocked variants: an xf with no <protection> is locked by default, so
      // only the cells the reader may type into carry one
      '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyProtection="1">' +
      '<protection locked="0"/></xf>' +
      '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" ' +
      'applyProtection="1"><protection locked="0"/></xf>' +
      '</cellXfs>' +
      // Without a named default style, openpyxl warns and some readers substitute their
      // own. Cheap to include, and it is the difference between a file that opens
      // cleanly everywhere and one that opens with a complaint.
      '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
      '</styleSheet>'},
  ];
  names.forEach((n, i) => entries.push({name:`xl/worksheets/sheet${i+1}.xml`,
                                        text: sheetXml(sheetsObj[n], n)}));
  return zipStored(entries);
}

/* ---------------------------------------------- 2b. the JSON interchange file
   .xlsx is a ZIP of XML. A person opens it in Excel; a program that is not a
   spreadsheet - a script, an agent, a language model - mostly cannot open it at all,
   which made every artifact in this project unreadable to anything but Excel. The same
   data as plain text closes that: row OBJECTS keyed by column name, dates as
   yyyy-mm-dd, one file, no library. The application reads it and writes it, so text and
   workbook are interchangeable in both directions.

   Described in docs/prap_contract.json ("interchange_format") and produced on the
   command line by tools/prap_io.py. tools/test_interop.py proves the two agree.        */

const JSON_FORMAT = "prap-source-data";
const JSON_FORMAT_VERSION = 1;

/* -------------------------------------------- 2c. starting from nothing at all
   Not everyone arrives with a workbook. Someone sketching a plan for the first time
   has the projects in their head and nothing on disk, and telling them to go and
   generate a template first is a wall in front of the only thing they wanted to do.

   A blank start is not an EMPTY workbook. With no `Lists` there is no vocabulary, so
   every value typed is reported as unrecognised (V-11) and no field can offer a
   choice; with no `Config` there are no thresholds. So a blank start begins from the
   reference content of the delivered template - the value lists and the settings -
   and nothing else. The projects, people and assignments are what the user is here
   to enter.                                                                        */

/* SEED-BEGIN — generated by tools/build_app_seed.py from PRAP_SourceData_Template_v1.8.xlsx.
   The reference content of a blank start: the value lists and the settings, and
   nothing else. Do not edit by hand — rebuild it, or check_consistency.py fails.
   The weight and role-factor grids are NOT here: blankSheets() builds them from
   these lists, so a company that adds a role gets it without a regeneration. */
const SEED_LISTS = [
  ["project_type","NewDrug CT",null],
  ["project_type","Biosimilar CT (Healthy)",null],
  ["project_type","Biosimilar CT (Patient)",null],
  ["project_type","Others",null],
  ["clinical_phase","Phase 1",null],
  ["clinical_phase","Phase 2",null],
  ["clinical_phase","Phase 3",null],
  ["clinical_phase","Phase 4",null],
  ["work_scope_type","fully in-housed",null],
  ["work_scope_type","fully outsourced",null],
  ["work_scope_type","Partially outsourced (in-house for EDC)",null],
  ["outsourcing_type","Full outsourcing",null],
  ["outsourcing_type","Partial outsourcing",null],
  ["outsourcing_type","Full In-house",null],
  ["setup_party","by CRO",null],
  ["setup_party","by SB",null],
  ["EDC_system","Veeva EDC",null],
  ["EDC_system","Rave",null],
  ["EDC_system","eSOURCE",null],
  ["DataReviewSystem","Veeva DQS",null],
  ["DataReviewSystem","Medidata CDS",null],
  ["DataReviewSystem","No system (manual)",null],
  ["RBQM_system","CluePoints",null],
  ["RBQM_system","Medidata CDS",null],
  ["RBQM_system","No system (manual)",null],
  ["project_status","Planned",null],
  ["project_status","Active",null],
  ["project_status","On hold",null],
  ["project_status","Completed",null],
  ["milestone_name","Protocol (v1)",null],
  ["milestone_name","CTA submission",null],
  ["milestone_name","FPI",null],
  ["milestone_name","First SIV",null],
  ["milestone_name","LPI",null],
  ["milestone_name","interim DB lock cut-off",null],
  ["milestone_name","interim DB lock",null],
  ["milestone_name","final DB lock cut-off",null],
  ["milestone_name","final DB lock",null],
  ["milestone_name","Inspection",null],
  ["period_name_clinical","Before-Start-up",null],
  ["period_name_clinical","Start-up",null],
  ["period_name_clinical","Conduct (interim)",null],
  ["period_name_clinical","Close-out (interim)",null],
  ["period_name_clinical","Conduct (final)",null],
  ["period_name_clinical","Close-out (final)",null],
  ["period_name_clinical","After Close-out (final)",null],
  ["period_name_others","Planning",null],
  ["period_name_others","Develop",null],
  ["period_name_others","Close",null],
  ["role_clinical","Project oversight",null],
  ["role_clinical","Lead data manager",null],
  ["role_clinical","Clinical Data Associator",null],
  ["role_clinical","Clinical Database Programmer",null],
  ["role_clinical","Data Analyst",null],
  ["role_others","Project lead",null],
  ["role_others","Main staff",null],
  ["role_others","Other staff",null],
];
const SEED_CONFIG = [
  ["schema_version",6,"Structure version of this workbook. The application warns on a mismatch."],
  ["fte_hours_per_month",160,"Hours equal to 1.00 FTE: 8 h/day x 5 days/week x 20 days/month."],
  ["over_allocation_fte",1.5,"A person-month total above this is flagged as over-allocated. Absolute, not scaled by capacity (S2-01)."],
  ["under_allocation_fte",0.6,"A person-month total below this counts toward an under-allocated run. Absolute, not scaled by capacity (S2-01)."],
  ["under_allocation_min_months",3,"Consecutive months below the threshold before a run is flagged."],
  ["default_horizon_months",24,"Months shown when the dashboard opens."],
  ["capacity_unit","FTE","Display unit: 'FTE' or 'percent'."],
];
/* SEED-END */

const PLACEHOLDER = "Placeholder 1.00 — replace with your own figure";

function blankSheets(){
  const sheets = {};
  for (const s of REQUIRED_SHEETS) sheets[s] = [SHEET_HEADERS[s].slice()];
  for (const r of SEED_LISTS) sheets.Lists.push(r.slice());
  for (const r of SEED_CONFIG) sheets.Config.push(r.slice());

  /* The reference grids are BUILT from the lists just seeded rather than embedded, so a
     company that adds a role or a phase to `Lists` gets that combination here too,
     without anyone regenerating the application. Every figure starts at 1.00 and says
     so: an invented weight that looks like a company standard is worse than an obvious
     placeholder, because only one of the two gets questioned. */
  const listOf = n => SEED_LISTS.filter(r => r[0] === n).map(r => r[1]);
  const types = listOf("project_type");
  const ct = types.filter(t => CLINICAL_TYPES.has(t));
  const other = types.filter(t => !CLINICAL_TYPES.has(t));
  const phases = listOf("clinical_phase");
  const cPeriods = listOf("period_name_clinical"), oPeriods = listOf("period_name_others");
  const cRoles = listOf("role_clinical"), oRoles = listOf("role_others");

  /* Schema 6 keys both tables on the work scope too, and the grid is seeded with the
     scope column EMPTY - the row that applies to every scope. Seeding one row per scope
     would treble the grid to say the same thing three times, and the person filling it
     in would have to notice that two thirds of it was redundant before they could stop
     typing. Add a scope-specific row where a scope really does change the number. */
  for (const t of ct) for (const ph of phases) for (const p of cPeriods)
    sheets.PeriodWeightStandard.push([t, ph, null, p, 1.00, PLACEHOLDER]);
  for (const t of ct) for (const ph of phases) for (const p of cPeriods) for (const rn of cRoles)
    sheets.RoleFactor.push([t, ph, null, p, rn, 1.00, PLACEHOLDER]);
  // 'Others' projects carry no clinical phase, so their factors are keyed without one.
  for (const t of other) for (const p of oPeriods) for (const rn of oRoles)
    sheets.RoleFactor.push([t, null, null, p, rn, 1.00, PLACEHOLDER]);
  return sheets;
}

function readPrapJson(text){
  let doc;
  try { doc = JSON.parse(text); }
  catch (e){ throw new Error(`that file is not valid JSON — ${e.message}`); }
  if (doc.prap_format !== JSON_FORMAT)
    throw new Error(`not a PRAP interchange file. It must carry "prap_format": `
      + `"${JSON_FORMAT}" — a workbook exported from this application does.`);
  if (doc.format_version !== JSON_FORMAT_VERSION)
    throw new Error(`format_version is ${JSON.stringify(doc.format_version)}; this `
      + `application reads ${JSON_FORMAT_VERSION}.`);
  const src = doc.sheets || {};
  const missing = REQUIRED_SHEETS.filter(s => !Array.isArray(src[s]));
  if (missing.length)
    throw new Error(`sheet(s) missing or not an array: ${missing.join(", ")}. All `
      + `${REQUIRED_SHEETS.length} must be present, even where a sheet has no rows.`);
  const sheets = {};
  for (const s of REQUIRED_SHEETS){
    const hdr = SHEET_HEADERS[s];
    const rows = [hdr.slice()];
    src[s].forEach((r, i) => {
      // A column name outside the schema is refused, not ignored: a mistyped key
      // silently dropped is a value whoever wrote the file believes they supplied.
      const bad = Object.keys(r).filter(k => !hdr.includes(k));
      if (bad.length)
        throw new Error(`${s} row ${i+1} has unknown column(s) ${bad.join(", ")}. `
          + `Valid columns: ${hdr.join(", ")}.`);
      rows.push(hdr.map(h => r[h] === undefined ? null : r[h]));
    });
    sheets[s] = rows;
  }
  return sheets;
}

function buildPrapJson(sheetsObj){
  const out = {};
  for (const s of REQUIRED_SHEETS){
    const rows = sheetsObj[s] || [];
    const hdr = (rows[0] || []).map(h => txt(h));
    out[s] = rows.slice(1).map(r => {
      const rec = {};
      hdr.forEach((h, i) => {
        let v = r[i];
        if (v === null || v === undefined || v === "" || !h) return;
        if (v instanceof Date) v = ymd(v);
        rec[h] = v;
      });
      return rec;
    });
  }
  return JSON.stringify({
    prap_format: JSON_FORMAT,
    format_version: JSON_FORMAT_VERSION,
    schema_version: SCHEMA_EXPECTED,
    $comment: "PRAP source data as plain text. Drop this file straight back onto "
      + "app/PRAP.html, or convert it with tools/prap_io.py. Dates are yyyy-mm-dd. "
      + "Column meanings, value lists and validation rules: docs/prap_contract.json.",
    sheets: out,
  }, null, 1) + "\n";
}

