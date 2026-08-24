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
   the reference content of a blank start: the value lists, the settings, and the
   DEFAULT ASSUMPTIONS. Do not edit by hand — rebuild it, or check_consistency
   fails. blankSheets() still BUILDS the two grids from the value lists, so a
   company that adds a role gets that combination without a regeneration; these
   rows supply the figure wherever there is one, and 1.00 where there is not. */
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
  ["split_shared_role_fte",1,"1 = when several people hold the same role on one project in a month, the role factor is divided between them. 0 = each is charged the whole factor, which is how versions before this one behaved."],
];
const SEED_PWS = [
  ["NewDrug CT","Phase 1",null,"Before-Start-up",0.6,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)",1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)",1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)",1.4,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up",0.7,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up",1.4,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)",1.1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)",1.1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)",1.5,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)",0.9,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up",1.6,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)",1.4,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)",1.7,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)",1.02,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up",0.5,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up",1.1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)",0.9,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)",1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)",0.9,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up",0.51,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)",0.85,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)",0.85,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up",0.59,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)",1.27,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up",1.36,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)",1.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)",0.87,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up",0.42,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)",0.85,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)",0.61,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up",0.55,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up",1.2,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)",0.92,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)",0.92,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)",1.29,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up",0.64,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up",1.29,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)",1.01,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)",1.2,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)",1.01,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)",1.38,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up",1.47,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)",1.29,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)",1.56,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up",0.46,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up",1.01,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)",0.92,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)",0.66,"Default assumption - replace with your own figure"],
];
const SEED_RF = [
  ["NewDrug CT","Phase 1",null,"Before-Start-up","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Before-Start-up","Lead data manager",0.91,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Before-Start-up","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Before-Start-up","Clinical Database Programmer",0.73,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Before-Start-up","Data Analyst",0.34,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up","Lead data manager",1.37,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up","Clinical Data Associator",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up","Clinical Database Programmer",1.57,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Start-up","Data Analyst",0.51,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)","Lead data manager",1.14,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)","Clinical Data Associator",1.23,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)","Clinical Database Programmer",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (interim)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)","Lead data manager",1.25,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)","Clinical Data Associator",1.04,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)","Clinical Database Programmer",1.04,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (interim)","Data Analyst",1.11,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)","Lead data manager",1.14,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)","Clinical Data Associator",1.23,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)","Clinical Database Programmer",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Conduct (final)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)","Lead data manager",1.37,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)","Clinical Data Associator",0.85,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)","Clinical Database Programmer",1.15,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"Close-out (final)","Data Analyst",1.28,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)","Project oversight",0.61,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)","Lead data manager",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)","Clinical Database Programmer",0.42,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 1",null,"After Close-out (final)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up","Lead data manager",0.96,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up","Clinical Data Associator",0.5,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up","Clinical Database Programmer",0.77,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Before-Start-up","Data Analyst",0.36,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up","Lead data manager",1.44,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up","Clinical Data Associator",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up","Clinical Database Programmer",1.65,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Start-up","Data Analyst",0.54,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)","Lead data manager",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)","Clinical Data Associator",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)","Clinical Database Programmer",0.88,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (interim)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)","Lead data manager",1.32,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)","Clinical Data Associator",1.1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)","Clinical Database Programmer",1.1,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (interim)","Data Analyst",1.17,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)","Lead data manager",1.2,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)","Clinical Data Associator",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)","Clinical Database Programmer",0.88,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Conduct (final)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)","Lead data manager",1.44,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)","Clinical Data Associator",0.9,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)","Clinical Database Programmer",1.21,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"Close-out (final)","Data Analyst",1.35,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)","Project oversight",0.64,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)","Lead data manager",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)","Clinical Data Associator",0.5,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)","Clinical Database Programmer",0.44,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 2",null,"After Close-out (final)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up","Lead data manager",1.01,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up","Clinical Data Associator",0.53,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up","Clinical Database Programmer",0.81,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Before-Start-up","Data Analyst",0.38,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up","Project oversight",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up","Lead data manager",1.51,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up","Clinical Data Associator",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up","Clinical Database Programmer",1.73,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Start-up","Data Analyst",0.57,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)","Project oversight",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)","Lead data manager",1.26,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)","Clinical Data Associator",1.37,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)","Clinical Database Programmer",0.92,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (interim)","Data Analyst",0.85,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)","Project oversight",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)","Lead data manager",1.39,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)","Clinical Data Associator",1.16,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)","Clinical Database Programmer",1.16,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (interim)","Data Analyst",1.23,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)","Project oversight",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)","Lead data manager",1.26,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)","Clinical Data Associator",1.37,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)","Clinical Database Programmer",0.92,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Conduct (final)","Data Analyst",0.85,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)","Project oversight",0.84,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)","Lead data manager",1.51,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)","Clinical Data Associator",0.95,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)","Clinical Database Programmer",1.27,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"Close-out (final)","Data Analyst",1.42,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)","Project oversight",0.67,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)","Lead data manager",0.88,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)","Clinical Data Associator",0.53,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)","Clinical Database Programmer",0.46,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 3",null,"After Close-out (final)","Data Analyst",0.85,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up","Project oversight",0.65,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up","Lead data manager",0.86,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up","Clinical Data Associator",0.45,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up","Clinical Database Programmer",0.69,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Before-Start-up","Data Analyst",0.32,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up","Lead data manager",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up","Clinical Data Associator",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up","Clinical Database Programmer",1.49,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Start-up","Data Analyst",0.49,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)","Lead data manager",1.08,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)","Clinical Data Associator",1.17,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)","Clinical Database Programmer",0.79,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (interim)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)","Lead data manager",1.19,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)","Clinical Data Associator",0.99,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)","Clinical Database Programmer",0.99,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (interim)","Data Analyst",1.05,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)","Lead data manager",1.08,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)","Clinical Data Associator",1.17,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)","Clinical Database Programmer",0.79,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Conduct (final)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)","Lead data manager",1.3,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)","Clinical Data Associator",0.81,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)","Clinical Database Programmer",1.09,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"Close-out (final)","Data Analyst",1.22,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)","Project oversight",0.58,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)","Lead data manager",0.76,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)","Clinical Data Associator",0.45,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)","Clinical Database Programmer",0.4,"Default assumption - replace with your own figure"],
  ["NewDrug CT","Phase 4",null,"After Close-out (final)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up","Project oversight",0.65,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up","Lead data manager",0.87,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up","Clinical Data Associator",0.45,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up","Clinical Database Programmer",0.69,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Before-Start-up","Data Analyst",0.32,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up","Lead data manager",1.3,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up","Clinical Data Associator",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up","Clinical Database Programmer",1.49,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Start-up","Data Analyst",0.49,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)","Lead data manager",1.08,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)","Clinical Data Associator",1.17,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)","Clinical Database Programmer",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (interim)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)","Lead data manager",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)","Clinical Data Associator",0.99,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)","Clinical Database Programmer",0.99,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (interim)","Data Analyst",1.06,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)","Lead data manager",1.08,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)","Clinical Data Associator",1.17,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)","Clinical Database Programmer",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Conduct (final)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)","Lead data manager",1.3,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)","Clinical Data Associator",0.81,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)","Clinical Database Programmer",1.09,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"Close-out (final)","Data Analyst",1.22,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)","Project oversight",0.58,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)","Lead data manager",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)","Clinical Data Associator",0.45,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)","Clinical Database Programmer",0.4,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 1",null,"After Close-out (final)","Data Analyst",0.73,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up","Lead data manager",0.91,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up","Clinical Database Programmer",0.73,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Before-Start-up","Data Analyst",0.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up","Lead data manager",1.37,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up","Clinical Data Associator",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up","Clinical Database Programmer",1.57,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Start-up","Data Analyst",0.51,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)","Lead data manager",1.14,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)","Clinical Data Associator",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)","Clinical Database Programmer",0.84,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (interim)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)","Lead data manager",1.25,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)","Clinical Data Associator",1.04,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)","Clinical Database Programmer",1.04,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (interim)","Data Analyst",1.11,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)","Lead data manager",1.14,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)","Clinical Data Associator",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)","Clinical Database Programmer",0.84,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Conduct (final)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)","Project oversight",0.76,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)","Lead data manager",1.37,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)","Clinical Data Associator",0.85,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)","Clinical Database Programmer",1.15,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"Close-out (final)","Data Analyst",1.28,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)","Project oversight",0.61,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)","Lead data manager",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)","Clinical Database Programmer",0.42,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 2",null,"After Close-out (final)","Data Analyst",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up","Project oversight",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up","Lead data manager",0.96,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up","Clinical Data Associator",0.5,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up","Clinical Database Programmer",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Before-Start-up","Data Analyst",0.36,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up","Lead data manager",1.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up","Clinical Data Associator",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up","Clinical Database Programmer",1.65,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Start-up","Data Analyst",0.54,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)","Lead data manager",1.2,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)","Clinical Data Associator",1.3,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)","Clinical Database Programmer",0.88,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (interim)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)","Lead data manager",1.32,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)","Clinical Data Associator",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)","Clinical Database Programmer",1.1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (interim)","Data Analyst",1.17,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)","Lead data manager",1.2,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)","Clinical Data Associator",1.3,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)","Clinical Database Programmer",0.88,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Conduct (final)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)","Project oversight",0.8,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)","Lead data manager",1.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)","Clinical Data Associator",0.9,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)","Clinical Database Programmer",1.21,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"Close-out (final)","Data Analyst",1.35,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)","Project oversight",0.64,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)","Lead data manager",0.84,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)","Clinical Data Associator",0.5,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)","Clinical Database Programmer",0.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 3",null,"After Close-out (final)","Data Analyst",0.81,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up","Project oversight",0.62,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up","Lead data manager",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up","Clinical Data Associator",0.43,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up","Clinical Database Programmer",0.66,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Before-Start-up","Data Analyst",0.31,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up","Lead data manager",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up","Clinical Data Associator",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up","Clinical Database Programmer",1.41,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Start-up","Data Analyst",0.46,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)","Lead data manager",1.03,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)","Clinical Data Associator",1.11,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)","Clinical Database Programmer",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (interim)","Data Analyst",0.69,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)","Lead data manager",1.13,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)","Clinical Data Associator",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)","Clinical Database Programmer",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (interim)","Data Analyst",1,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)","Lead data manager",1.03,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)","Clinical Data Associator",1.11,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)","Clinical Database Programmer",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Conduct (final)","Data Analyst",0.69,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)","Project oversight",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)","Lead data manager",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)","Clinical Data Associator",0.77,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)","Clinical Database Programmer",1.03,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"Close-out (final)","Data Analyst",1.15,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)","Project oversight",0.55,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)","Lead data manager",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)","Clinical Data Associator",0.43,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)","Clinical Database Programmer",0.38,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Healthy)","Phase 4",null,"After Close-out (final)","Data Analyst",0.69,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up","Project oversight",0.67,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up","Lead data manager",0.89,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up","Clinical Database Programmer",0.72,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Before-Start-up","Data Analyst",0.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up","Lead data manager",1.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up","Clinical Data Associator",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up","Clinical Database Programmer",1.54,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Start-up","Data Analyst",0.5,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)","Lead data manager",1.12,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)","Clinical Data Associator",1.21,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)","Clinical Database Programmer",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (interim)","Data Analyst",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)","Lead data manager",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)","Clinical Data Associator",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)","Clinical Database Programmer",1.02,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (interim)","Data Analyst",1.09,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)","Lead data manager",1.12,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)","Clinical Data Associator",1.21,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)","Clinical Database Programmer",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Conduct (final)","Data Analyst",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)","Lead data manager",1.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)","Clinical Data Associator",0.84,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)","Clinical Database Programmer",1.13,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"Close-out (final)","Data Analyst",1.26,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)","Project oversight",0.6,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)","Lead data manager",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)","Clinical Data Associator",0.47,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)","Clinical Database Programmer",0.41,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 1",null,"After Close-out (final)","Data Analyst",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up","Lead data manager",0.94,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up","Clinical Data Associator",0.49,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up","Clinical Database Programmer",0.75,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Before-Start-up","Data Analyst",0.35,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up","Project oversight",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up","Lead data manager",1.41,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up","Clinical Data Associator",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up","Clinical Database Programmer",1.62,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Start-up","Data Analyst",0.53,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)","Project oversight",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)","Lead data manager",1.18,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)","Clinical Data Associator",1.27,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)","Clinical Database Programmer",0.86,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (interim)","Data Analyst",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)","Project oversight",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)","Lead data manager",1.29,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)","Clinical Data Associator",1.08,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)","Clinical Database Programmer",1.08,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (interim)","Data Analyst",1.15,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)","Project oversight",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)","Lead data manager",1.18,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)","Clinical Data Associator",1.27,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)","Clinical Database Programmer",0.86,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Conduct (final)","Data Analyst",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)","Project oversight",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)","Lead data manager",1.41,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)","Clinical Data Associator",0.88,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)","Clinical Database Programmer",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"Close-out (final)","Data Analyst",1.32,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)","Project oversight",0.63,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)","Lead data manager",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)","Clinical Data Associator",0.49,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)","Clinical Database Programmer",0.43,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 2",null,"After Close-out (final)","Data Analyst",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up","Project oversight",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up","Lead data manager",0.99,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up","Clinical Data Associator",0.51,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up","Clinical Database Programmer",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Before-Start-up","Data Analyst",0.37,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up","Project oversight",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up","Lead data manager",1.48,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up","Clinical Data Associator",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up","Clinical Database Programmer",1.7,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Start-up","Data Analyst",0.56,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)","Project oversight",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)","Lead data manager",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)","Clinical Data Associator",1.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)","Clinical Database Programmer",0.91,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (interim)","Data Analyst",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)","Project oversight",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)","Lead data manager",1.36,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)","Clinical Data Associator",1.13,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)","Clinical Database Programmer",1.13,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (interim)","Data Analyst",1.2,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)","Project oversight",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)","Lead data manager",1.23,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)","Clinical Data Associator",1.34,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)","Clinical Database Programmer",0.91,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Conduct (final)","Data Analyst",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)","Project oversight",0.82,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)","Lead data manager",1.48,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)","Clinical Data Associator",0.93,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)","Clinical Database Programmer",1.25,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"Close-out (final)","Data Analyst",1.39,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)","Project oversight",0.66,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)","Lead data manager",0.86,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)","Clinical Data Associator",0.51,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)","Clinical Database Programmer",0.45,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 3",null,"After Close-out (final)","Data Analyst",0.83,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up","Project oversight",0.64,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up","Lead data manager",0.85,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up","Clinical Data Associator",0.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up","Clinical Database Programmer",0.68,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Before-Start-up","Data Analyst",0.32,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up","Lead data manager",1.27,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up","Clinical Data Associator",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up","Clinical Database Programmer",1.46,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Start-up","Data Analyst",0.48,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)","Lead data manager",1.06,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)","Clinical Data Associator",1.15,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)","Clinical Database Programmer",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (interim)","Data Analyst",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)","Lead data manager",1.16,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)","Clinical Data Associator",0.97,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)","Clinical Database Programmer",0.97,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (interim)","Data Analyst",1.03,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)","Lead data manager",1.06,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)","Clinical Data Associator",1.15,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)","Clinical Database Programmer",0.78,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Conduct (final)","Data Analyst",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)","Project oversight",0.71,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)","Lead data manager",1.27,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)","Clinical Data Associator",0.79,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)","Clinical Database Programmer",1.07,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"Close-out (final)","Data Analyst",1.19,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)","Project oversight",0.56,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)","Lead data manager",0.74,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)","Clinical Data Associator",0.44,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)","Clinical Database Programmer",0.39,"Default assumption - replace with your own figure"],
  ["Biosimilar CT (Patient)","Phase 4",null,"After Close-out (final)","Data Analyst",0.71,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Planning","Project lead",1.1,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Planning","Main staff",0.63,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Planning","Other staff",0.42,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Develop","Project lead",1,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Develop","Main staff",1.08,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Develop","Other staff",0.77,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Close","Project lead",0.9,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Close","Main staff",0.81,"Default assumption - replace with your own figure"],
  ["Others",null,null,"Close","Other staff",0.7,"Default assumption - replace with your own figure"],
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
     typing. Add a scope-specific row where a scope really does change the number.

     THE FIGURES ARE THE DELIVERED DEFAULTS, not a placeholder. A blank start used to
     fill both grids with 1.00, which reads as a starting point but is not one: at 1.00
     everywhere the period weight and the role factor cancel out of the arithmetic, so
     the application produced numbers that looked like an answer and were not one. The
     defaults come from SEED_PWS and SEED_RF, which are read out of the delivered
     template - so the workbook and the application hold the same assumptions by
     construction rather than by anybody remembering.

     The GRID is still built from the value lists rather than from the seed, so a
     company that adds a role or a phase gets that combination without waiting for a
     new build. It simply arrives at 1.00, marked as a placeholder, because nobody has
     supplied a figure for a role nobody had yesterday. */
  const seededW = new Map(SEED_PWS.map(r => [[r[0], r[1], r[3]].join("\u0000"), r]));
  const seededF = new Map(SEED_RF.map(r => [[r[0], r[1], r[3], r[4]].join("\u0000"), r]));
  const wOf = (t, ph, p) => seededW.get([t, ph, p].join("\u0000"));
  const fOf = (t, ph, p, rn) => seededF.get([t, ph, p, rn].join("\u0000"));

  for (const t of ct) for (const ph of phases) for (const p of cPeriods){
    const s = wOf(t, ph, p);
    sheets.PeriodWeightStandard.push(s ? s.slice()
                                       : [t, ph, null, p, 1.00, PLACEHOLDER]);
  }
  for (const t of ct) for (const ph of phases) for (const p of cPeriods) for (const rn of cRoles){
    const s = fOf(t, ph, p, rn);
    sheets.RoleFactor.push(s ? s.slice() : [t, ph, null, p, rn, 1.00, PLACEHOLDER]);
  }
  // 'Others' projects carry no clinical phase, so their factors are keyed without one.
  for (const t of other) for (const p of oPeriods) for (const rn of oRoles){
    const s = fOf(t, null, p, rn);
    sheets.RoleFactor.push(s ? s.slice() : [t, null, null, p, rn, 1.00, PLACEHOLDER]);
  }
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

