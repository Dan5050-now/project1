/* ======================================= who is making the changes, and what there is
   to hand over. Both are UI, kept out of storage/ - that is the seam the desktop shell
   replaces, and it should hold the file handling and nothing else.

   The desktop shell overrides askWho() with one that answers from the Windows account,
   so the control below never appears there. */

const WHO_KEY = "prap.who";

/** The name to stamp on entries, asked for once and then remembered.
 *
 *  Called at the first edit rather than at load, because somebody who only opens a plan
 *  to read it should never be asked who they are - there will be nothing to attribute. */
/* Shown in the edit bar the moment there is something to attribute, and put away as
   soon as it is answered. Nothing is blocked and nothing is covered: the bar is already
   on screen whenever there are unsaved changes, which is exactly when the question is
   worth asking, and it wraps like everything else in it. */
function askWho(){
  if (S.who) return S.who;
  let saved = null;
  try { saved = localStorage.getItem(WHO_KEY); } catch (e){ /* private mode: ask again */ }
  if (saved){ S.who = saved; return S.who; }
  const box = el("whobox");
  if (box) box.hidden = false;           // renderDirty() keeps it in step from here
  return S.who;
}

/** Remember it, or stop asking. Either way the control goes. */
function setWho(name){
  S.who = (name || "").trim() || "(not stated)";
  try { localStorage.setItem(WHO_KEY, S.who); } catch (e){ /* nothing to do */ }
  const box = el("whobox");
  if (box) box.hidden = true;
  renderAuditOffer();
  renderDirty();
}

/* --------------------------------------------------------------- the export offer */

/** How much there is to export, said on the menu itself.
 *
 *  A menu item that silently hands over an empty file is worse than one that is greyed
 *  out: the file arrives, it looks like the log, and it says nothing happened. This puts
 *  the count where the decision is made, and disables the item when there is nothing. */
function renderAuditOffer(){
  const c = el("aCount");
  if (!c) return;
  const from = (el("aFrom") || {}).value || "", to = (el("aTo") || {}).value || "";
  const a = auditBetween(S.audit, from, to).length;
  const e = auditBetween(S.events, from, to).length;
  const span = from || to ? " in that range" : "";
  c.textContent = S.audit.length || S.events.length
    ? `${a} change(s), ${e} finding(s)${span}`
    : "nothing recorded yet — the log starts at your first save";
  const setUp = (id, n) => {
    const b = el(id);
    if (!b) return;
    b.disabled = !n;
    b.classList.toggle("off", !n);
  };
  setUp("exportAuditBtn", a);
  setUp("exportEventsBtn", e);
}
