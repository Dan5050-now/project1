/* =============================================== the change log, in the web shell

   THE BROWSER CANNOT WRITE TO A FOLDER. A page opened from a file:// URL has no folder
   of its own and no way to append to one; the File System Access API exists, but it
   needs the user to grant a directory on every session and is not available everywhere
   this application has to run. So the browser keeps the record in memory for the
   session and hands it over as a file when asked - the same record, arriving by the
   only route a browser has.

   THE DESKTOP SHELL DOES have a folder, and replaces archiveAudit() with one that
   appends to it at every save. That is the whole of the seam: the editing code calls
   archiveAudit() and does not know which shell answered.

   Who is typing is asked for in ui/13b_audit_ui.js - a dialog is not storage. */

/** Called after every save. In the browser there is nowhere to archive TO, so this only
 *  keeps the count the export offer is drawn from; the desktop shell overrides it with
 *  one that writes to disk. */
function archiveAudit(){
  renderAuditOffer();
}

/* ------------------------------------------------------- handing the record over */

function auditFileName(kind, from, to){
  const base = (S.fileName || "PRAP").replace(/\.prap\.json$|\.json$|\.xlsx$/i, "");
  const span = from || to ? `_${from || "start"}_to_${to || "end"}` : "";
  return `${base}_${kind}${span}.csv`;
}

/** A CSV the way Excel wants it: a UTF-8 BOM, so a column of Korean or an accented name
 *  is not mangled when the file is opened by double-clicking it on Windows. Without it
 *  Excel reads the file in the system code page and the log becomes unreadable for
 *  exactly the users most likely to need it. */
function downloadCsv(name, text){
  const blob = new Blob(["﻿" + text], {type:"text/csv;charset=utf-8"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

function exportAudit(from, to){
  const n = auditBetween(S.audit, from, to).length;
  downloadCsv(auditFileName("ChangeLog", from, to), auditCsv(S.audit, from, to));
  return n;
}

function exportEvents(from, to){
  const n = auditBetween(S.events, from, to).length;
  downloadCsv(auditFileName("ErrorsAndWarnings", from, to), eventsCsv(S.events, from, to));
  return n;
}

