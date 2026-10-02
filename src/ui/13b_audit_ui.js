/* ============================================================ who is making the changes

   The name every entry in the change log is stamped with. UI, kept out of storage/ -
   that is the seam the desktop shell replaces, and it should hold the file handling and
   nothing else.

   The desktop shell overrides askWho() with one that answers from the account it signed
   in with, so the control below never appears there. */

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
  renderDirty();
}
