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

  /* ---- the claim, taken on the first DATA CHANGE ------------------------- */
  async function takeClaimOnEdit() {
    if (!ref || holds || !caps.claims) return true;
    let r;
    try { r = await call("claim/take", { ref }); }
    catch (e) { showBanner("bad", e.message); return false; }
    if (r.ok) {
      holds = true;
      showHold("hold", "You are editing this plan");
      return true;
    }
    showHold("read", "Read-only — " + (r.holder?.name || "someone else"));
    showBanner("bad", r.message);
    return false;
  }

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
  async function importSource(forceBrowse) {
    let got = null;
    try {
      if (caps.nativeDialogs && !forceBrowse) {
        got = await call("file/openSource", {});
      } else {
        const p = await browseFor({
          title: "Choose source data",
          suffixes: [".xlsx", ".json"],
          okLabel: "Open",
        });
        if (!p) return;
        got = await call("file/openSource", { path: p });
      }
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
    try {
      showBanner("", `Reading ${name}…`);
      const sheets = /\.json$/i.test(name)
        ? readPrapJson(enc.decode(bytes))
        : await readWorkbook(bytes.buffer.slice(bytes.byteOffset,
                                                bytes.byteOffset + bytes.byteLength));
      if (typeof window.importSourceOver === "function")
        await window.importSourceOver(name, sheets);
      else adopt(sheets, name);
    } catch (e) {
      showBanner("bad", `Could not read that file: ${e.message}`);
      console.error(e);
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
      const w = await call("ws/open", { ref: p });
      ref = w.ref; holds = false;
      adopt(w.sheets, ref.split(/[\\/]/).pop());
      showFile();
      showHold(w.readOnly ? "read" : null, "Read-only folder");
      const by = w.header.last_saved_by;
      if (by) showBanner("", `Last saved by ${by.name}`
        + (by.department ? ` (${by.department})` : "")
        + `, ${new Date(w.header.last_saved).toLocaleString()}.`);
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
        if (caps.nativeDialogs) {
          out = await call("ws/saveAs", { sheets: sheetsNow(), suggested });
        } else {
          const p = await browseFor({ title: "Save the plan as", folders: true,
                                      name: suggested, okLabel: "Save" });
          if (!p) return;
          out = await call("ws/saveAs", { sheets: sheetsNow(), ref: p });
        }
        if (!out) return;
        ref = out.ref;
      } else {
        out = await call("ws/save", { ref, sheets: sheetsNow() });
      }
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
      if (caps.nativeDialogs) {
        out = await call("file/export", { bytes: bytesToB64(bytes), suggested: name });
      } else {
        const p = await browseFor({ title: "Export to", folders: true, name,
                                    okLabel: "Export" });
        if (!p) return;
        out = await call("file/export", { bytes: bytesToB64(bytes), path: p });
      }
      if (out) showBanner("", `Exported to ${out.path}. The source file on disk is `
        + `untouched.`);
    } catch (e) {
      showBanner("bad", e.message);
    }
  }

  /* ---- the in-page folder browser ---------------------------------------- */
  /* Used when there is no tkinter, and whenever somebody wants to type a path -
     a share, say. It talks to fs/list, which returns names and sizes. No browser
     file interface is involved: nothing here can read a file's contents, and the
     page never asks it to. */
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
      case "new": ref = null; holds = false; showFile(); showHold(null); return startBlank();
      case "open": {
        let p = caps.nativeDialogs ? await call("ws/openDialog", {}) : null;
        if (!caps.nativeDialogs)
          p = await browseFor({ title: "Open a plan", suffixes: [".prap"],
                                okLabel: "Open" });
        return p && openPlan(p);
      }
      case "recent": return showRecent();
      case "save": return savePlan(false);
      case "saveAs": return savePlan(true);
      case "import": return importSource(false);
      case "importBrowse": return importSource(true);
      case "export": return exportWorkbook(false);       // the browser download
      case "exportJson": return exportWorkbook(true);
      case "exportTo": return exportTo(false);
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
File dialogs   ${caps.nativeDialogs ? "native" : "in the page"}
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

  showFile();
  window.__pm = { call, openPlan, savePlan, importSource, adoptBytes, browseFor,
                  takeClaimOnEdit, state: () => ({ ref, holds, me, caps, where }) };
})();
