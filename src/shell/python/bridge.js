"use strict";
/* ============================================================ the Python bridge
   Everything the web shell did with a file picker and a download, routed through
   one local address instead.

   THE IMPORTANT PART IS WHAT IS MISSING. There is no <input type="file"> on this
   page, no drop handler, and no File API call anywhere in this file. Those three
   are the entire browser file interface, and on the machine this shell was written
   for, a company security control stops data crossing them (R-N21). So the data
   does not cross them: the user chooses a path, PYTHON opens the file, and the
   bytes arrive as ordinary page content from this page's own origin.

   The claim is taken HERE, on the first pending edit, because that is the moment a
   data value actually changes. Not on a click, not on a selection, not on a filter:
   a claim taken by a click would block a colleague for half an hour on account of
   somebody browsing (U-N03).

   Specification: PRAP_NewApp_Specification_v1.3.xlsx sheets 03, 07. */

(async () => {
  const KEY = document.querySelector('meta[name="pm-key"]')?.content || "";
  if (!KEY) return;                          // opened as a plain file: stay the web app

  const el = id => document.getElementById(id);
  const enc = new TextDecoder();

  /* ---- the one route to the machine ------------------------------------- */
  async function call(op, body) {
    const res = await fetch("/api/" + op, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-PM-Key": KEY },
      body: JSON.stringify(body || {}),
    });
    if (!res.ok) throw new Error(`${op} failed (${res.status})`);
    const j = await res.json();
    if (j.error) { const e = new Error(j.message); e.kind = j.kind; throw e; }
    return j.result;
  }

  /* ---- the window and the application go together ------------------------
     The console window IS the application; this page is its window. Closing the
     window and leaving the application running is not something anybody asked for,
     and it left a console sitting there owning a port, a claim on a plan nobody had
     open, and a data folder - which the next run then had to argue with.

     TWO MESSAGES, BECAUSE NEITHER IS ENOUGH ON ITS OWN.

     THE CLOSE MESSAGE is the one that matters and the one that is quick. `pagehide`
     is the event that actually fires when a tab is closed - `unload` does not, on a
     page the browser has put in its back/forward cache - and `keepalive` is what lets
     a fetch outlive the document that started it. sendBeacon cannot be used: it
     refuses custom headers, and every request here carries the key.

     THE HEARTBEAT is the backstop, for the times no close message arrives: the
     browser was killed, the machine slept. It is slow on purpose. A browser throttles
     timers in a tab nobody is looking at and can freeze one outright, so anything
     brisk here would shut the application down on somebody who left it in a
     background tab - see watch_clients() in server.py for the other half of this.

     `pagehide` fires on a RELOAD as well, and at that moment the two are
     indistinguishable. The server waits a few seconds before believing it, which is
     more than a reload needs to say hello again.

     FIRST, BEFORE ANY OF THE START-UP AWAITS. Everything below this point waits on the
     machine, and one of those waits is a person: a first run stops at the sign-in card
     until somebody types their name. Registering after that would mean the one case
     the complaint is really about - open it, look at it, close it again - never
     registered at all, so the console would sit there for ever having never seen a
     page. Liveness is not the start-up sequence's business. */
  const PAGE_ID = (crypto.randomUUID && crypto.randomUUID())
    || String(Date.now()) + Math.random().toString(16).slice(2);
  const ALIVE_MS = 20000;

  const alive = () => call("app/alive", { id: PAGE_ID }).catch(() => {});
  alive();
  setInterval(alive, ALIVE_MS);
  // And on the way back from being hidden, so a tab that was frozen for an hour says
  // so the moment it is looked at again rather than at the next tick.
  addEventListener("visibilitychange", () => { if (!document.hidden) alive(); });

  addEventListener("pagehide", () => {
    try {
      fetch("/api/app/bye", {
        method: "POST", keepalive: true,
        headers: { "Content-Type": "application/json", "X-PM-Key": KEY },
        body: JSON.stringify({ id: PAGE_ID }),
      }).catch(() => {});
    } catch (e) { /* the backstop has it */ }
  });


  const b64ToBytes = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  function bytesToB64(bytes) {
    let out = "";
    const u = new Uint8Array(bytes);
    for (let i = 0; i < u.length; i += 0x8000)
      out += String.fromCharCode.apply(null, u.subarray(i, i + 0x8000));
    return btoa(out);
  }

  /* ---- what this shell can do ------------------------------------------- */
  const caps = await call("caps");
  const where = await call("paths");
  el("pm-where").textContent = `v${where.version} · ${where.dataDir}`;

  let me = await call("identity/get");
  if (!me || !me.name) {
    me = await signIn(await call("identity/suggest"));
  }
  showWho();

  function showWho() {
    el("pm-who").textContent = me.department ? `${me.name} · ${me.department}` : me.name;
  }

  /* ---- the plan this session has open ----------------------------------- */
  let ref = null, holds = false;
  // NR-STO-16. `baseSaved` is the issue of the file this session's figures came from
  // - the plan's own last_saved, to the millisecond - and `stale` says the file has
  // moved on since. Kept here rather than in ui/ because this is the only layer that
  // knows there is a file at all. Not a modification time: a share may round one to
  // two seconds, and a check that cannot tell two saves apart is no check.
  let baseSaved = "", stale = false;
  // Who refused us, while we wait for them to finish (NR-STO-15).
  let blockedBy = null;
  const hushedShare = new Set();      // plans whose "not now" was meant

  function showFile() {
    el("pm-file").textContent = ref ? ref.split(/[\\/]/).pop() : "no plan open";
  }

  function showHold(state, text) {
    const p = el("pm-hold");
    if (!state) { p.hidden = true; return; }
    p.hidden = false;
    p.className = "pm-pill " + state;
    p.textContent = text;
  }


  /* ---- NR-STO-16: the plan can change on disk underneath a reader ---------
     Somebody who opened a plan at 09:00 and is still shown 09:00's figures at 11:00,
     after two saves by somebody else, may quote them in good faith - and if they then
     edit one cell and save, the newer work is replaced by figures that predate it and
     the save reports success. The claim does not stop it: a session that has not
     edited anything never took one.

     So the file is checked every ten seconds (S-N01, AGREED) and once more
     immediately before every save, which is the check that actually prevents the
     loss - and storage/ checks it again as the bytes go down, because a guard only in
     the window is a guard anything else can walk past. What is compared is the plan's
     own last_saved rather than its modification time: a share may round a modification
     time to two seconds, and a check that cannot tell two saves apart is no check. */
  const STALE_MS = 10000;

  /** Remember which issue of the file we are looking at. After every open and every
   *  save of our own - otherwise our own write reads as somebody else's. */
  async function noteBase(savedAt) {
    if (savedAt) { baseSaved = savedAt; return; }
    if (!ref) { baseSaved = ""; return; }
    try { baseSaved = (await call("ws/stat", { ref })).lastSaved || ""; }
    catch { baseSaved = ""; }
  }

  function sayStale(at) {
    stale = true;
    showHold("read", "Superseded — reload to edit");
    showBanner("bad", `Somebody else saved this plan${at ? " at " + at : ""}. The figures `
      + `on screen are from when you opened it, so saving now would replace their work. `
      + `Use File → Reload plan to catch up.`);
  }

  /** Has the file moved on since we read it? Reports it, and says so to the caller. */
  async function superseded() {
    if (!ref || !baseSaved) return false;
    let st;
    try { st = await call("ws/stat", { ref }); } catch { return false; }
    if (!st || !st.exists || !st.lastSaved) return false;
    if (st.lastSaved === baseSaved) return false;
    sayStale(new Date(st.lastSaved).toLocaleTimeString());
    return true;
  }

  setInterval(() => { if (ref && !stale) superseded(); }, STALE_MS);

  /** Read the plan again, from the top. The way out of STALE, and the only one:
   *  keeping the screen and saving over the newer file is the thing being prevented. */
  async function reloadPlan() {
    if (!ref) return;
    if (S.pending.length && !confirm(`${S.pending.length} change(s) are not committed. `
        + `Reloading this plan discards them. Continue?`)) return;
    const p = ref;
    stale = false;
    await openPlan(p);
  }

  /* ---- NR-STO-07: pending edits survive a crash ---------------------------
     The journal is the record of work that has not been committed, kept APART from
     the plan so a half-typed row is never committed data. It was being READ when a
     plan opened and never written, so there was never anything to find. How it is
     noticed is the paragraph below. */
  const JOURNAL_MS = 2000;
  let journalled = false, lastPending = -1;

  function noteJournal() {
    if (!ref || !caps.journal) return;
    // `S` is a top-level const, so it is a SCRIPT-scoped binding and not a
    // property of window - window.S is undefined however alive S is.
    const pending = (typeof S !== "undefined" && S.pending) || [];
    if (!pending.length) {
      // Committed or discarded: there is nothing to recover, and a journal left behind
      // would be offered back on the next open as though there were.
      if (journalled) { journalled = false; call("journal/clear", { ref }).catch(() => {}); }
      return;
    }
    journalled = true;
    call("journal/write", { ref, pending }).catch(() => {});
  }

  /* WATCHED, NOT HOOKED. The pending list is changed in a dozen places in ui/ - a cell
     edit, a row insert, a row delete, an identifier cascade, Save changes, Leave
     without change - and a journal that depends on having wrapped every one of them is
     a journal with holes in it, which is worse than none: it would be offered back as
     though it were complete. One timer that notices the count has moved cannot have
     holes, and it cannot be skipped by an exception raised somewhere else in a render.
     Two seconds, because this exists for the power cut rather than for the audit trail
     - S.audit is that - and a plan on a share does not want a write per keystroke. */
  setInterval(() => {
    const n = (typeof S !== "undefined" && S.pending) ? S.pending.length : 0;
    if (n === lastPending) return;
    lastPending = n;
    noteJournal();
  }, JOURNAL_MS);

  /* ---- NR-STO-15: a claim ends when the holder is finished with the plan --- */
  async function releaseClaim() {
    // Not guarded on `holds`. That flag is this window's belief about the claim, and
    // the whole point of releasing is to be right about the FILE: if the two have
    // drifted - a heartbeat lost it, a claim was taken by a path that did not set the
    // flag - guarding on the belief would leave the plan locked for half an hour.
    // release_claim() in storage/ checks ownership itself and a release of a claim
    // that is not ours, or not there, does nothing.
    if (!ref || !caps.claims) return;
    try { await call("claim/release", { ref }); } catch { /* going anyway */ }
    holds = false;
    showHold(null);
  }

  /* 'Leave without change' ends the claim: there is nothing left to protect, and a
     colleague waiting should not wait on a session that threw its own edits away
     (NR-STO-15).

     A LISTENER, NOT A WRAPPER. shell/web/14b_wiring.js does
     `el("discardBtn").onclick = discardEdits`, which captures the function ITSELF at
     bind time - so replacing window.discardEdits afterwards, the way
     beginEditSession() is replaced below, would leave the button calling the original
     and the claim would never come back. beginEditSession() is different because its
     callers name it at CALL time. addEventListener adds to the button without
     depending on which of the two it is, and the menu's 'Leave without change' goes
     through the same click. */
  el("discardBtn")?.addEventListener("click", () => { releaseClaim(); });

  /* ---- the claim, taken on the first DATA CHANGE ------------------------- */
  async function takeClaimOnEdit() {
    // Before the claim, because a stale view is refused for a different reason and the
    // person needs to hear that one: the claim may well be free, and taking it would
    // let them save figures that have already been replaced (NR-STO-16).
    if (stale) {
      showBanner("bad", "This plan has been saved by somebody else since you opened it. "
        + "Use File → Reload plan before editing — saving now would replace their work.");
      return false;
    }
    if (!ref || holds || !caps.claims) return true;
    let r;
    try { r = await call("claim/take", { ref }); }
    catch (e) { showBanner("bad", e.message); return false; }
    if (r.ok) {
      holds = true; blockedBy = null;
      showHold("hold", "You are editing this plan");
      return true;
    }
    blockedBy = r.holder?.name || "someone else";
    showHold("read", "Read-only — " + blockedBy);
    showBanner("bad", r.message);
    return false;
  }

  /* NR-STO-15's OTHER HALF: "a session waiting to edit is offered it without having
     to reopen the workspace". The thirty-second poll below only runs while we HOLD
     the claim, so a blocked session never learned the plan had freed - the person had
     to guess and try the edit again. Now the wait is watched, and the offer is made.

     S-N07 decides what the offer does NOT do: a blocked session that later gets the
     claim keeps whatever it was looking at rather than reloading and losing their
     place. It reloads only if the plan changed while they waited, and that is the
     STALE path, which says so itself - so this stays quiet while `stale` is set and
     lets that message win. */
  async function offerIfFreed() {
    if (!ref || holds || !blockedBy || stale || !caps.claims) return false;
    let held;
    try { held = await call("claim/read", { ref }); } catch { return false; }
    // An EXPIRED claim is as takeable as no claim at all (Q-N16), and it is the case
    // that strands somebody longest: the holder's machine died, so no release is ever
    // coming. Without this the person waits out the half hour and then has to guess
    // that guessing again might work. The wording differs because the situations do -
    // a colleague who finished is not a colleague whose laptop went off mid-sentence,
    // and the second one may have lost work of their own.
    if (held && held.state !== "expired") return false;         // still somebody's
    const who = blockedBy;
    blockedBy = null;
    showHold(null);
    showBanner("", held
      ? "You can edit this plan now — " + who + " has gone quiet for over half an "
        + "hour, so the plan no longer counts as theirs. Nothing has been reloaded. "
        + "Worth a word with them first if their edits mattered."
      : "This plan is free now — whoever had it has finished with it. "
        + "Start editing and it is yours. Nothing has been reloaded, so what is on "
        + "screen is still what you were looking at.");
    return true;
  }

  setInterval(offerIfFreed, 30000);

  // beginEditSession() is the application's own "a value is about to change" point -
  // the snapshot before the first pending edit. Wrapping it is what makes the claim
  // attach to a change rather than to a click, without touching ui/ at all.
  const origBegin = window.beginEditSession;
  if (typeof origBegin === "function") {
    window.beginEditSession = function (...a) {
      takeClaimOnEdit();
      return origBegin.apply(this, a);
    };
  }

  // Electron pushed "your claim was taken over" down a second channel. Here the
  // page asks, on the same clock the heartbeat runs on. One question every thirty
  // seconds costs nothing and needs no second channel to go wrong.
  setInterval(async () => {
    if (!ref || !holds) return;
    try {
      const r = await call("claim/holds", { ref });
      if (!r.holds) {
        holds = false;
        showHold("read", "Read-only");
        showBanner("bad", "Your hold on this plan was taken over while you were "
          + "working. Nothing has been saved. Use File → Save as to keep your changes.");
      }
    } catch { /* the application is stopping */ }
  }, 30000);

  /* ---- importing, WITHOUT the browser ever seeing a file ----------------- */
  // One entry in the menu, because there is one way in. It used to take a
  // forceBrowse flag so somebody could ask for the folder listing instead of the
  // native dialog; the native dialog is gone, so the flag and the second menu item
  // ("Import from a folder…") would have been two names for the same command.
  async function importSource() {
    let got = null;
    try {
      const p = await browseFor({
        title: "Choose source data",
        suffixes: [".xlsx", ".json"],
        okLabel: "Open",
      });
      if (!p) return;
      got = await call("file/openSource", { path: p });
    } catch (e) {
      showBanner("bad", e.message);
      return;
    }
    if (!got) return;                        // the dialog was cancelled
    await adoptBytes(got.name, b64ToBytes(got.bytes));
  }

  /** The web application's loadFile(), with the File taken out of it - and one thing
   *  put in. Same two readers; then importSourceOver decides between adopting the file
   *  and offering a difference report, because this shell has a PLAN open and the web
   *  application never does (NR-IMP-02). */
  async function adoptBytes(name, bytes) {
    document.body.classList.add("busy");
    try {
      // Same two phases the web shell announces, and for the same reason: both of them
      // hold the main thread for most of a second on a large workbook.
      showBanner("busy", `Reading ${name}…`);
      await paint();
      const sheets = /\.json$/i.test(name)
        ? readPrapJson(enc.decode(bytes))
        : await readWorkbook(bytes.buffer.slice(bytes.byteOffset,
                                                bytes.byteOffset + bytes.byteLength));
      showBanner("busy", `Building the plan from ${name}…`);
      await paint();
      if (typeof window.importSourceOver === "function")
        await window.importSourceOver(name, sheets);
      else adopt(sheets, name);
    } catch (e) {
      showBanner("bad", `Could not read that file: ${e.message}`);
      console.error(e);
    } finally {
      document.body.classList.remove("busy");
    }
  }

  // The web page's own ways in are removed rather than left to fail. A button that
  // opens a dialog and then silently loses the file is worse than no button: the
  // person who clicks it concludes the application is broken, and they are right.
  window.loadFile = async function (fileLike) {
    if (fileLike && typeof fileLike.arrayBuffer === "function") {
      // A real File can only have come from a picker this shell does not use.
      return adoptBytes(fileLike.name, new Uint8Array(await fileLike.arrayBuffer()));
    }
    return importSource(false);
  };
  el("picker")?.remove();
  const dropZone = el("drop");
  if (dropZone) {
    // Replacing the node drops every listener the web wiring attached to it, which
    // is the point: the drop handler read e.dataTransfer.files, and that is the
    // File API.
    const fresh = dropZone.cloneNode(true);
    dropZone.replaceWith(fresh);
    fresh.querySelector("#loadBtn2")?.remove();
    const btn = document.createElement("button");
    btn.className = "btn primary";
    btn.textContent = "Choose source data…";
    btn.onclick = () => importSource(false);
    fresh.appendChild(btn);
    const p = fresh.querySelector("p");
    if (p) p.textContent = "Choose an .xlsx source workbook or a .prap.json "
      + "interchange file. The file is read by the application on this machine and "
      + "never leaves it.";
  }
  el("loadBtn")?.remove();

  /* ---- workspaces -------------------------------------------------------- */
  async function openPlan(p) {
    try {
      // Finished with the plan we had, so its claim goes back now rather than at its
      // half-hour expiry (NR-STO-15). The server does this too; doing it here as well
      // keeps `holds` and the window honest even if the open then fails.
      if (ref && ref !== p) await releaseClaim();
      const w = await call("ws/open", { ref: p });
      ref = w.ref; holds = false; stale = false; blockedBy = null;
      adopt(w.sheets, ref.split(/[\\/]/).pop());
      showFile();
      showHold(w.readOnly ? "read" : null, "Read-only folder");
      const by = w.header.last_saved_by;
      if (by) showBanner("", `Last saved by ${by.name}`
        + (by.department ? ` (${by.department})` : "")
        + `, ${new Date(w.header.last_saved).toLocaleString()}.`);
      // The header already says it, so this costs no extra round trip.
      await noteBase(w.header.last_saved);           // for NR-STO-16
      await checkShared(by);
      journalled = false; lastPending = -1;
      const j = await call("journal/read", { ref });
      if (j) showBanner("bad", `This plan has ${j.pending?.length || 0} change(s) that `
        + `were never saved, from ${new Date(j.at).toLocaleString()}.`);
    } catch (e) {
      showBanner("bad", e.message);
    }
  }

  function sheetsNow() {
    const sheets = {};
    for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
    return sheets;
  }

  async function savePlan(as) {
    if (S.pending.length) {
      showBanner("bad", `${S.pending.length} change(s) are not yet committed. Press `
        + `Save changes or Leave without change first.`);
      return;
    }
    try {
      let out;
      if (!ref || as) {
        const suggested = (ref ? ref.split(/[\\/]/).pop() : null)
          || `${(S.fileName || "Plan").replace(/\.[^.]+$/, "")}.prap`;
        const p = await browseFor({ title: "Save the plan as", folders: true,
                                    name: suggested, okLabel: "Save" });
        if (!p) return;
        out = await call("ws/saveAs", { sheets: sheetsNow(), ref: p });
        if (!out) return;
        ref = out.ref;
      } else {
        // THE CHECK THAT PREVENTS THE LOSS. Between opening this plan and now,
        // somebody else may have saved theirs; writing on top would replace it with
        // figures that predate it, and the save would report success (NR-STO-16).
        if (await superseded()) return;
        // `baseSaved` goes with it: the guard above is this window's, and the one in
        // storage/ is the file's. Either alone leaves a way to lose the save.
        out = await call("ws/save", { ref, sheets: sheetsNow(), baseSaved });
      }
      await noteBase(out.savedAt);        // our own write is not somebody else's
      stale = false;
      showFile();
      showBanner("", `Saved to ${out.ref}.`);
    } catch (e) {
      showBanner("bad", e.message);
    }
  }

  /* ---- exporting --------------------------------------------------------- */
  // The browser's own download is left exactly as it was. A download is not an
  // upload, and the control that stopped importing does not touch it - so
  // exportWorkbook() from storage/web/export.js still runs, unmodified, with all of
  // its checks. This adds one thing it cannot do: put the file somewhere chosen.
  async function exportTo(asJson) {
    if (S.pending.length) {
      showBanner("bad", "Export held — there are changes that are not yet saved.");
      return;
    }
    const sheets = sheetsNow();
    const stamp = new Date().toISOString().slice(0, 10);
    const base = (S.fileName || "PRAP_SourceData.xlsx")
      .replace(/\.prap\.json$|\.json$|\.xlsx$/i, "");
    const name = `${base}_${stamp}${asJson ? ".prap.json" : ".xlsx"}`;
    let bytes;
    if (asJson) bytes = new TextEncoder().encode(buildPrapJson(sheets));
    else bytes = new Uint8Array(await buildXlsx(sheets).arrayBuffer());
    try {
      let out;
      const p = await browseFor({ title: "Export to", folders: true, name,
                                  okLabel: "Export" });
      if (!p) return;
      out = await call("file/export", { bytes: bytesToB64(bytes), path: p });
      if (out) showBanner("", `Exported to ${out.path}. The source file on disk is `
        + `untouched.`);
    } catch (e) {
      showBanner("bad", e.message);
    }
  }

  /* The calculated figures, put where the user chooses. The file is built by the same
     buildResults() the browser download uses, so the two cannot differ; this only adds
     the destination. Unsaved changes do NOT hold it up - a results file is a snapshot
     of what is on screen, and that is what somebody pressing it is asking for. */
  async function exportResultsTo() {
    const M = S.model, C = S.calc;
    if (!M || !C) { showBanner("bad", "Nothing to export yet — open a plan first."); return; }
    const months = grid();
    if (!months.length) {
      showBanner("bad", "Export held — the horizon covers no months. Widen it and try again.");
      return;
    }
    const named = Object.entries(S.f).filter(([, set]) => set.size)
      .map(([k, set]) => `${FILTER_LABEL[k] || k}: ${[...set].join(", ")}`);
    const sheets = buildResults(M, C, {
      months, projects: activeProjects(), people: activePeople(),
      filters: named.join(" · "), fileName: S.fileName,
      stamp: new Date().toISOString().slice(0, 16).replace("T", " "),
    });
    const day = new Date().toISOString().slice(0, 10);
    const base = (S.fileName || "PRAP").replace(/\.prap\.json$|\.json$|\.xlsx$/i, "");
    const name = `${base}_CalculatedFTE_${day}.xlsx`;
    const bytes = new Uint8Array(await buildXlsx(sheets).arrayBuffer());
    try {
      let out;
      const pth = await browseFor({ title: "Export calculated FTE to", folders: true,
                                    name, okLabel: "Export" });
      if (!pth) return;
      out = await call("file/export", { bytes: bytesToB64(bytes), path: pth });
      if (out) showBanner("", `Exported ${sheets.Detail.length - 1} assignment-month `
        + `row(s) to ${out.path}. This one is for reading — it cannot be imported back. `
        + `Your plan is untouched.`);
    } catch (e) {
      showBanner("bad", e.message);
    }
  }

  /* The notice's own two buttons. Bound once, by listener rather than by onclick -
     shell/web binds some buttons at load by assigning onclick, and a later assignment
     replaces a handler somebody else is relying on. */
  el("pm-share")?.querySelector("[data-move]")
    ?.addEventListener("click", () => { moveToShared(); });
  el("pm-share")?.querySelector("[data-dismiss]")
    ?.addEventListener("click", () => {
      if (ref) hushedShare.add(ref);      // "Not now" means not again for this plan
      el("pm-share").hidden = true;
    });

  /* ---- a plan where the sharing rules cannot reach it ---------------------
     A claim on a plan inside one person's folder protects nothing (NR-STO-10). The
     team folder was created at launch and carried a note saying so, and the page
     never mentioned either - so plans were saved where sharing could not work and
     the failure was invisible: no error, no warning, just colleagues emailing copies
     to each other and the application unable to know.

     THE TRIGGER IS NOT "the plan is private". Most private plans are private on
     purpose and a bar on every one of them would be noise, and then furniture. It is
     "the plan is private AND SOMEBODY ELSE SAVED IT" - which a plan in your own
     folder can only be if it was copied there by hand, which is the very failure
     this is about. Said once per plan; "Not now" means it. */
  async function checkShared(savedBy) {
    const bar = el("pm-share");
    if (!bar) return false;
    bar.hidden = true;
    if (!ref || hushedShare.has(ref)) return false;
    const other = savedBy && savedBy.name && me && savedBy.name !== me.name;
    if (!other) return false;
    let st;
    try { st = await call("ws/sharedState", { ref }); } catch { return false; }
    if (!st || !st.private || !st.target) return false;
    bar.querySelector("[data-text]").textContent =
      `This plan is in your own folder, where nobody else can open it - but `
      + `${savedBy.name} saved it, so it has been copied around by hand. Move it to `
      + `the team folder and the application can keep one writer at a time, and say `
      + `who is editing.`
      + (st.taken ? "  A plan of this name is already there, so this one would need "
                  + "renaming first." : "");
    bar.querySelector("[data-move]").disabled = Boolean(st.taken);
    bar.hidden = false;
    return true;
  }

  /** Move the open plan to where the team can reach it. Also the File menu item, for
   *  somebody who knows they want to share and has not been asked. */
  async function moveToShared() {
    if (!ref) return tell("Move plan", "<p class='pm-note'>No plan is open.</p>");
    let st;
    try { st = await call("ws/sharedState", { ref }); }
    catch (e) { return showBanner("bad", e.message); }
    if (!st.shared)
      return tell("Move plan", "<p class='pm-note'>This installation has no team "
                + "folder.</p>");
    if (!st.private)
      return tell("Move plan", "<p class='pm-note'>This plan is not in your own "
                + "folder, so colleagues can already open it.</p>");
    let out;
    try { out = await call("ws/moveToShared", { ref }); }
    catch (e) { return showBanner("bad", e.message); }
    el("pm-share").hidden = true;
    ref = out.ref;
    holds = false;
    showFile();
    showHold(null);
    showBanner("", "Moved to the team folder. Colleagues can open it now, and the "
      + "application will keep one writer at a time."
      + (out.versions ? `  ${out.versions} kept version(s) came with it.` : ""));
  }

  /* ---- the in-page folder browser ---------------------------------------- */
  /* Used when there is no tkinter, and whenever somebody wants to type a path -
     a share, say. It talks to fs/list, which returns names and sizes. No browser
     file interface is involved: nothing here can read a file's contents, and the
     page never asks it to. */
  /** Windows compares paths without regard to case, and a trailing separator means
   *  nothing; neither does the browser, so it is done here rather than hoped for. */
  function sameDir(a, b) {
    const tidy = x => String(x || "").replace(/[\\/]+$/, "").toLowerCase();
    return Boolean(a) && tidy(a) === tidy(b);
  }

  /** Your own folder and the team's, when the installation has both. */
  function places() {
    const out = [];
    if (where.workspaces)
      out.push({ label: "My plans", path: where.workspaces,
                 hint: "Your own folder. Nobody else can open what is in here." });
    if (where.shared)
      out.push({ label: "Team plans", path: where.shared,
                 hint: "Everybody can open these, and the application keeps one "
                     + "writer at a time. A plan the team works on belongs here." });
    return out;
  }

  function browseFor(opts) {
    return new Promise(resolve => {
      const back = document.createElement("div");
      back.className = "pm-back";
      back.innerHTML = `<div class="pm-box">
        <h3>${opts.title}</h3>
        <div class="pm-crumb" data-crumb></div>
        <div class="body"><ul class="pm-list" data-list></ul>
          <p class="pm-note" data-note></p></div>
        <div class="foot">
          <input class="pm-path" data-path placeholder="…or type a full path">
          <button class="btn" data-cancel>Cancel</button>
          <button class="btn primary" data-ok>${opts.okLabel || "Choose"}</button>
        </div></div>`;
      document.body.appendChild(back);
      const q = s => back.querySelector(s);
      let here = null, picked = null;

      const done = v => { back.remove(); document.removeEventListener("keydown", onKey);
                          resolve(v); };
      const onKey = e => { if (e.key === "Escape") done(null); };
      document.addEventListener("keydown", onKey);
      q("[data-cancel]").onclick = () => done(null);
      back.onclick = e => { if (e.target === back) done(null); };
      q("[data-ok]").onclick = () => {
        const typed = q("[data-path]").value.trim();
        if (typed) return done(typed);
        if (opts.folders) return done(here && opts.name ? join(here, opts.name) : null);
        done(picked);
      };
      const join = (d, n) => d.replace(/[\\/]+$/, "") + (d.includes("\\") ? "\\" : "/") + n;

      async function go(path) {
        let r;
        try { r = await call("fs/list", { path, suffixes: opts.suffixes }); }
        catch (e) { q("[data-note]").textContent = e.message; return; }
        here = r.path; picked = null;
        q("[data-crumb]").innerHTML = "";
        /* THE TWO PLACES THAT DECIDE WHETHER SHARING WORKS AT ALL, one click each.
           The team folder existed, was created at launch and carried a note saying
           what it was for - and the page never mentioned it, so every plan was saved
           into the person's own folder, where a claim protects nothing (NR-STO-10)
           and the whole one-writer-at-a-time design never comes into play. A folder
           nobody can find is a folder nobody uses. */
        for (const place of places()) {
          const b = document.createElement("button");
          b.className = "place" + (sameDir(r.path, place.path) ? " on" : "");
          b.textContent = place.label;
          b.title = place.hint;
          b.onclick = () => go(place.path);
          q("[data-crumb]").appendChild(b);
        }
        if (places().length) {
          const sep = document.createElement("span");
          sep.className = "sep";
          sep.textContent = "·";
          q("[data-crumb]").appendChild(sep);
        }
        for (const root of r.roots) {
          const b = document.createElement("button");
          b.textContent = root.name;
          b.onclick = () => go(root.path);
          q("[data-crumb]").appendChild(b);
        }
        if (r.parent) {
          const b = document.createElement("button");
          b.textContent = "↑ up";
          b.onclick = () => go(r.parent);
          q("[data-crumb]").appendChild(b);
        }
        const list = q("[data-list]");
        list.innerHTML = "";
        const head = document.createElement("li");
        head.innerHTML = `<span class="i">📂</span><span class="n">${r.path}</span>`;
        head.style.cursor = "default";
        list.appendChild(head);
        for (const e of r.entries) {
          const li = document.createElement("li");
          li.innerHTML = `<span class="i">${e.dir ? "📁" : "📄"}</span>`
            + `<span class="n"></span>`
            + `<span class="m">${e.dir ? "" : kb(e.size)}</span>`;
          li.querySelector(".n").textContent = e.name;
          li.onclick = () => {
            if (e.dir) return go(e.path);
            for (const other of list.querySelectorAll("li")) other.classList.remove("sel");
            li.classList.add("sel");
            picked = e.path;
            q("[data-path]").value = "";
          };
          li.ondblclick = () => { if (!e.dir) done(e.path); };
          list.appendChild(li);
        }
        q("[data-note]").textContent = r.error
          || (opts.folders ? `The file will be written into this folder as `
                             + `${opts.name || "the name you type"}.`
                           : `${r.entries.length} item(s). Double-click a file to `
                             + `choose it.`);
        if (opts.folders && opts.name) q("[data-path]").value = join(r.path, opts.name);
      }
      const kb = n => n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB`
                                   : `${Math.max(1, Math.round(n / 1024))} KB`;
      go(opts.start || where.workspaces || where.dataDir);
    });
  }

  /* ---- who you are -------------------------------------------------------- */
  function signIn(suggest) {
    return new Promise(resolve => {
      const back = document.createElement("div");
      back.className = "pm-back";
      back.innerHTML = `<div class="pm-box"><h3>Who is using this?</h3>
        <div class="body">
          <p class="pm-note" style="margin:0 0 12px">Your colleagues see this name
          when a plan you are editing is held, so they know whom to ask. It is kept
          on this machine only.</p>
          <label style="display:block;font-size:12.5px;margin-bottom:4px">Name</label>
          <input class="pm-path" data-name>
          <label style="display:block;font-size:12.5px;margin:12px 0 4px">Department</label>
          <input class="pm-path" data-dept>
        </div>
        <div class="foot"><button class="btn primary" data-ok>Continue</button></div>
      </div>`;
      document.body.appendChild(back);
      const q = s => back.querySelector(s);
      q("[data-name]").value = (suggest && suggest.name) || "";
      q("[data-dept]").value = (suggest && suggest.department) || "";
      q("[data-name]").focus();
      q("[data-ok]").onclick = async () => {
        const id = { name: q("[data-name]").value.trim() || "(unnamed)",
                     department: q("[data-dept]").value.trim() };
        const saved = await call("identity/set", { identity: id });
        back.remove();
        resolve(saved);
      };
    });
  }

  /* ---- the menu ----------------------------------------------------------- */
  for (const m of document.querySelectorAll("[data-menu]")) {
    m.querySelector("button").onclick = e => {
      e.stopPropagation();
      const open = m.classList.contains("open");
      for (const o of document.querySelectorAll("[data-menu]")) o.classList.remove("open");
      m.classList.toggle("open", !open);
    };
  }
  document.addEventListener("click", () => {
    for (const o of document.querySelectorAll("[data-menu]")) o.classList.remove("open");
  });

  document.addEventListener("click", async e => {
    const a = e.target.closest("[data-do]");
    if (!a) return;
    e.preventDefault();
    const what = a.dataset.do;
    if (what.startsWith("tab:")) return showTab(what.slice(4));
    switch (what) {
      case "new": await releaseClaim(); ref = null; holds = false; stale = false;
                  baseSaved = ""; showFile(); showHold(null); return startBlank();
      case "reload": return reloadPlan();
      case "moveToShared": return moveToShared();
      case "open": {
        const p = await browseFor({ title: "Open a plan", suffixes: [".prap"],
                                    okLabel: "Open" });
        return p && openPlan(p);
      }
      case "recent": return showRecent();
      case "save": return savePlan(false);
      case "saveAs": return savePlan(true);
      case "import": return importSource();
      case "export": return exportWorkbook(false);       // the browser download
      case "exportJson": return exportWorkbook(true);
      case "exportTo": return exportTo(false);
      case "exportCalc": return exportResults();          // the browser download
      case "exportCalcTo": return exportResultsTo();
      case "commit": return el("saveBtn")?.click();
      case "discard": return el("discardBtn")?.click();
      case "changes": return el("chgBtn")?.click();
      case "who": return showHolder();
      case "restore": return showVersions();
      case "signin": { me = await signIn(me); showWho(); return; }
      case "about": return showAbout();
      case "quit": {
        if (!confirm("Stop the application? Anything not saved is lost.")) return;
        await call("quit", {}).catch(() => {});
        document.body.innerHTML = "<p style='padding:40px;font:16px system-ui'>"
          + "Project Management APP has stopped. You can close this tab.</p>";
        return;
      }
      default: return;
    }
  });

  /* ---- the small dialogs -------------------------------------------------- */
  function tell(title, html) {
    const back = document.createElement("div");
    back.className = "pm-back";
    back.innerHTML = `<div class="pm-box"><h3>${title}</h3>
      <div class="body">${html}</div>
      <div class="foot"><button class="btn primary" data-ok>Close</button></div></div>`;
    document.body.appendChild(back);
    back.querySelector("[data-ok]").onclick = () => back.remove();
    back.onclick = e => { if (e.target === back) back.remove(); };
    return back;
  }

  async function showRecent() {
    const rows = await call("ws/recent", {});
    if (!rows.length) return tell("Open recent", "<p class='pm-note'>Nothing yet.</p>");
    const box = tell("Open recent", "<ul class='pm-list' data-r></ul>");
    const list = box.querySelector("[data-r]");
    for (const r of rows) {
      const li = document.createElement("li");
      const held = r.heldBy ? ` · held by ${r.heldBy.name}` : "";
      li.innerHTML = `<span class="i">${r.exists ? "📄" : "⚠"}</span>`
        + `<span class="n"></span><span class="m"></span>`;
      li.querySelector(".n").textContent = r.name;
      li.querySelector(".m").textContent = (r.exists ? "" : "missing") + held;
      li.onclick = () => { box.remove(); openPlan(r.full); };
      list.appendChild(li);
    }
  }

  async function showHolder() {
    if (!ref) return tell("Who is editing", "<p class='pm-note'>No plan is open.</p>");
    const r = await call("claim/read", { ref });
    tell("Who is editing", r ? `<p>${r.message}</p>`
      : "<p class='pm-note'>Nobody is editing this plan.</p>");
  }

  async function showVersions() {
    if (!ref) return tell("Previous versions", "<p class='pm-note'>No plan is open.</p>");
    const vs = await call("ws/versions", { ref });
    if (!vs.length) return tell("Previous versions",
      "<p class='pm-note'>No previous version has been kept yet. One is kept from "
      + "the first time you save over an existing plan.</p>");
    const box = tell("Previous versions", "<ul class='pm-list' data-v></ul>"
      + "<p class='pm-note'>Restoring loads the older figures as unsaved changes. "
      + "Nothing is overwritten until you save.</p>");
    for (const v of vs) {
      const li = document.createElement("li");
      li.innerHTML = `<span class="i">🕐</span><span class="n">Version before the `
        + `last save</span><span class="m">${new Date(v.at).toLocaleString()}</span>`;
      li.onclick = async () => {
        box.remove();
        const w = await call("ws/restore", { ref, n: v.n });
        adopt(w.sheets, ref.split(/[\\/]/).pop() + ` (version of `
          + `${new Date(v.at).toLocaleString()})`);
        showBanner("", "The previous version is loaded. Save to keep it.");
      };
      box.querySelector("[data-v]").appendChild(li);
    }
  }

  function showAbout() {
    tell("About Project Management APP", `<pre style="font:12.5px/1.7 ui-monospace,
      Consolas,monospace;white-space:pre-wrap;margin:0">Version        ${where.version}
Shell          Python (${caps.shell})
File dialogs   in the page
Application    ${where.appDir}
Data folder    ${where.dataDir}
Chosen by      ${where.rule}
Signed in as   ${me.name}${me.department ? " (" + me.department + ")" : ""}
Account        ${where.account}</pre>
      <p class="pm-note">The figures on every tab are produced by the same engine as
      the web application, byte for byte. This shell only decides where files go.</p>`);
  }

  /* ---- keyboard ----------------------------------------------------------- */
  document.addEventListener("keydown", e => {
    if (!(e.ctrlKey || e.metaKey)) return;
    if (e.key === "s") { e.preventDefault(); savePlan(e.shiftKey); }
    if (e.key === "o") { e.preventDefault(); document.querySelector('[data-do="open"]')?.click(); }
  });

  /* ---- the change log, archived ------------------------------------------
     Both halves of what the browser could only half do.

     WHO: taken from the account this shell already signed in with, so nobody is asked
     a question the machine can answer. The browser's dialog is never shown here.

     WHERE: an `audit` folder beside the workspaces, appended to at every save. The
     rows are built by the same core functions the browser's export uses, so the file
     on disk and the file a browser hands over have identical columns - one of them is
     just written a save at a time.

     A FAILED ARCHIVE MUST NOT FAIL THE SAVE. The plan is in memory and safe; losing
     the log entries would be worse than saying so quietly, so the entries stay in
     S.audit and the next save carries them too. S.archived is how far the file has
     got, so nothing is written twice and nothing is skipped. */
  S.who = me && me.name
    ? (me.department ? `${me.name} (${me.department})` : me.name)
    : "(not stated)";
  window.askWho = () => S.who;

  let archiving = false;
  window.archiveAudit = async function (why) {
    if (archiving) return;                    // a second save while the first is writing
    archiving = true;
    try {
      const changes = S.audit.slice(S.archived);
      const findings = S.events.slice(S.eventsArchived || 0);
      if (changes.length)
        await call("audit/append", {kind: "changes", rows: auditCsvRows(changes)});
      S.archived = S.audit.length;
      if (findings.length)
        await call("audit/append", {kind: "findings", rows: eventsCsvRows(findings)});
      S.eventsArchived = S.events.length;
    } catch (e) {
      // Said once, on the status strip, rather than in a dialog over the save the user
      // just completed - the save WORKED, and this is about the record of it.
      console.error("audit archive failed", e);
      showBanner("warn", "Saved — but the change log could not be written to the audit "
        + "folder. The entries are kept and the next save will write them too. "
        + (e && e.message ? e.message : ""));
    } finally {
      archiving = false;
    }
  };

  /* ---- how tall the window chrome is -------------------------------------
     Measured rather than assumed, and re-measured when it changes. Both bars wrap:
     the status strip has flex-wrap and a long file path pushes it onto a second line,
     and the menu bar wraps too on a narrow window. Every one of those changes the
     height the page's sticky band has to clear, so a constant here would be right
     until the moment it mattered. Written as CSS variables, because the rules that
     need them are in chrome.css where they can be read next to what they affect. */
  function fitChrome(){
    const t = el("pm-title"), s = el("pm-strip");
    const th = t ? t.offsetHeight : 0;
    const r = document.documentElement.style;
    r.setProperty("--pm-title-h", th + "px");
    r.setProperty("--pm-chrome", (th + (s ? s.offsetHeight : 0)) + "px");
  }
  fitChrome();
  if (window.ResizeObserver){
    const ro = new ResizeObserver(fitChrome);
    for (const id of ["pm-title", "pm-strip"]) { const n = el(id); if (n) ro.observe(n); }
  } else {
    addEventListener("resize", fitChrome);   // coarser, but never wrong by much
  }

  showFile();

  window.__pm = { call, openPlan, savePlan, reloadPlan, releaseClaim, noteJournal,
                  checkShared, moveToShared,
                  offerIfFreed,
                  superseded, importSource, adoptBytes, browseFor,
                  takeClaimOnEdit, pageId: PAGE_ID,
                  state: () => ({ ref, holds, stale, baseSaved, blockedBy, me, caps, where }) };
})();
