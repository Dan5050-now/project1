/* ============================================================ 6c. the audit trail

   WHAT WAS CHANGED, WHEN, BY WHOM, AND WHAT THE APPLICATION SAID ABOUT IT.

   This is not S.pending. The two look alike and answer opposite questions:

     S.pending   what is NOT SAVED YET. Emptied at every save, because that is what
                 saving means, and shown so 'Leave without change' has something to
                 put back.
     S.audit     what HAS HAPPENED. Only ever appended to, for the life of the session.
                 A save is what writes it out, never what clears it.

   THE IDENTIFIER IS THE RECORD'S OWN, NOT ITS ROW NUMBER. S.pending carries `__row`,
   which is the spreadsheet row an edit landed on - correct for putting a change back,
   useless in an archived log a month later, because inserting one row above renumbers
   everything below it. So every entry is stamped with the row's NATURAL KEY (the same
   one the import comparison matches on, DIFF_KEY), which is what a reader means by
   "which project": PRJ-004, or PSN-012 | 2027-03, or the four fields that identify one
   standard.

   THE TIMESTAMP IS UTC, and said to be. A log read in Seoul that was written in Boston
   has to be comparable, and the only way to do that without a timezone library is to
   write one zone and name it. The header column says so.

   WHAT IT IS NOT: tamper-proof. It lives in memory and is written to a file anyone can
   open. It is a record of what happened, kept so it can be read back and handed on -
   not an attestation that nothing else did. */

/** The natural key of a row, as text, for the audit trail.
 *
 *  Falls back to the row number when the key columns are empty, which happens on a row
 *  still being typed: "(row 14)" is a poor identifier and an honest one, and it is
 *  better than an empty cell that looks like a defect in the log. */
function auditRef(sheet, row){
  if (!row) return "";
  const keys = (typeof DIFF_KEY !== "undefined" && DIFF_KEY[sheet]) || [];
  const parts = keys.map(k => {
    const v = row[k];
    return v instanceof Date ? ymd(v) : (v === null || v === undefined ? "" : String(v));
  }).filter(x => x !== "");
  return parts.length ? parts.join(" | ") : (row.__row ? `(row ${row.__row})` : "");
}

/** One pending change, turned into the thing that gets archived.
 *
 *  Done at SAVE rather than at the keystroke, because the identifier has to be read off
 *  the row as it finally stands: rename a project and then edit one of its milestones,
 *  and the milestone's entry should carry the name the project actually has. */
function auditFrom(p, model, who){
  const rows = (model && model.raw && model.raw[p.sheet]) || [];
  const row = rows.find(r => r.__row === p.row);
  return {
    at: p.at instanceof Date ? p.at : new Date(),
    who: who || "",
    action: p.col === "(new row)" ? "insert"
          : p.col === "(deleted row)" ? "delete"
          : p.sheet === "(cascade)" ? "cascade" : "update",
    sheet: p.sheet,
    ref: auditRef(p.sheet, row),
    row: p.row,
    col: p.col,
    from: p.from,
    to: p.to,
  };
}

/** Everything that is about to be saved, as entries for the accumulated record.
 *  RETURNS them rather than storing them: this layer decides what an entry is, the
 *  layer above owns the list it goes on. */
function auditEntries(pending, model, who){
  return (pending || []).map(p => auditFrom(p, model, who));
}

/* The other half of the requirement: what the application REPORTED while the data was
   being changed. Findings are recomputed from scratch on every keystroke, so they have
   no history of their own - the same missing phase is "raised" thousands of times and
   was never raised at all. What is worth recording is the state of them at each save:
   these are the things that were outstanding at the moment somebody said "keep this".

   `kept` marks the ones the user was asked about and chose to save anyway, which is the
   single most useful line in an audit trail of a plan: not that a problem existed, but
   that a person saw it and decided. */
function findingEntries(findings, keptRules, why, who){
  const at = new Date(), kept = new Set(keptRules || []);
  return (findings || []).map(f => ({
    at, who: who || "", event: why,
    severity: f.sev, rule: f.rule, sheet: f.sheet, row: f.row || "",
    kept: kept.has(f.rule) ? "yes" : "",
    message: f.msg,
  }));
}

/* ------------------------------------------------------------------------ CSV */

/** One field, quoted the way every spreadsheet expects to read it back.
 *
 *  Excel's rules, not JSON's: a field containing a comma, a quote or a newline is
 *  wrapped in quotes and its own quotes are doubled. A leading =, +, - or @ is prefixed
 *  with an apostrophe, because a cell beginning with one of those is a FORMULA to Excel
 *  and this file is opened in Excel by definition - a project note reading "=SUM(A1)"
 *  should arrive as text, not as something the spreadsheet evaluates. */
function csvField(v){
  if (v === null || v === undefined) return "";
  let s = v instanceof Date ? v.toISOString() : String(v);
  if (/^[=+\-@]/.test(s)) s = "'" + s;
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

const csvRow = cells => cells.map(csvField).join(",");

/** UTC, to the second, in the shape a spreadsheet sorts correctly as text. */
const utcStamp = d => (d instanceof Date ? d : new Date(d))
  .toISOString().replace("T", " ").slice(0, 19);

const AUDIT_HEAD = ["timestamp_utc", "who", "action", "sheet", "record", "column",
                    "previous_value", "new_value"];
const EVENT_HEAD = ["timestamp_utc", "who", "event", "severity", "rule", "sheet", "row",
                    "kept_by_user", "message"];

const auditShow = v => v instanceof Date ? ymd(v)
  : (v === null || v === undefined ? "" : String(v));

/** Entries between two YYYY-MM-DD days, both inclusive, both optional.
 *
 *  Compared on the UTC DAY the entry carries rather than on a parsed local date, so the
 *  range a reader types means the same thing as the timestamps they are reading. */
function auditBetween(list, from, to){
  return list.filter(e => {
    const day = utcStamp(e.at).slice(0, 10);
    return (!from || day >= from) && (!to || day <= to);
  });
}

function auditCsv(list, from, to){
  const rows = auditBetween(list || [], from, to);
  return [csvRow(AUDIT_HEAD)].concat(rows.map(e => csvRow(
    [utcStamp(e.at), e.who, e.action, e.sheet, e.ref, e.col,
     auditShow(e.from), auditShow(e.to)]))).join("\r\n") + "\r\n";
}

function eventsCsv(list, from, to){
  const rows = auditBetween(list || [], from, to);
  return [csvRow(EVENT_HEAD)].concat(rows.map(e => csvRow(
    [utcStamp(e.at), e.who, e.event, e.severity, e.rule, e.sheet, e.row,
     e.kept, e.message]))).join("\r\n") + "\r\n";
}

/** The rows a shell appends to an archive file, WITHOUT the header - the header belongs
 *  to the file, written once when it is created, not to every batch added to it. */
function auditCsvRows(list){
  return (list || []).map(e => csvRow(
    [utcStamp(e.at), e.who, e.action, e.sheet, e.ref, e.col,
     auditShow(e.from), auditShow(e.to)]));
}
function eventsCsvRows(list){
  return (list || []).map(e => csvRow(
    [utcStamp(e.at), e.who, e.event, e.severity, e.rule, e.sheet, e.row,
     e.kept, e.message]));
}
