/* =============================================== the change log, in the web shell

   THE ARCHIVE IS THE ONLY ROUTE OUT. Every saved change is appended to a CSV in the
   application's audit folder at the moment of saving, so there is nothing for the page
   to hand over afterwards - and an export button beside an archive that already has the
   file is two answers to one question, of which one is always the staler.

   That leaves this file as one function and a seam. archiveAudit() is called after every
   save; the shell with a folder writes to it, and a shell without one does nothing here
   but is still called, so the editing code above has a single name to call and does not
   know which shell answered. */

/** Called after every save. The desktop shell replaces this with one that appends to
 *  the shared audit folder. A shell with nowhere to write keeps the record in memory for
 *  the session and says so on the status line rather than silently dropping it. */
function archiveAudit(){
  /* nothing to do in a page that has no folder of its own */
}
