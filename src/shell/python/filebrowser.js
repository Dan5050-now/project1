"use strict";
/* ======================================================= the file browser (R-63)
   The one way this shell chooses a file or a folder: Python lists the folder (fs/list),
   the page draws it, and Python opens whatever is chosen. No browser file interface is
   involved anywhere in this file (R-N21) - nothing here can read a file's contents.

   WHAT IT WAS, AND WHY THAT WAS NOT ENOUGH. A plain list: a folder icon or a page
   icon, a name, a date, a size, and a row of buttons for the places. It worked, and
   finding anything in it was work: which of six PRAP_SourceData files is the newest
   export, is this plan the team's or a copy, is somebody editing it right now, how
   deep is this folder and how do I get back two levels. Reported from the field as
   "make the file windows more graphical and useful". So:

     * A SIDEBAR OF PLACES, each with its own icon: My plans and Team plans first,
       because a plan in the wrong one loses every sharing rule (NR-STO-10); then the
       folders this person used lately; then this computer's own folders and drives.
     * A PATH BAR whose every segment is a button, with back, forward and up - so two
       levels up is one click, not two trips through "up".
     * EVERY FILE SHOWS WHAT IT IS: a coloured badge per type (XLSX, JSON, PLAN), the
       date it was last written AND how long ago that was, and files grouped Today /
       Yesterday / This week / This month / Older when listed newest first.
     * A PLAN SAYS WHO SAVED IT AND WHETHER SOMEBODY IS EDITING IT, before it is opened.
     * A FILTER BOX, a list or tiles view, a details pane for the file picked, the
       keyboard (arrows, Enter, Backspace, Alt+arrows), and a count of the files of
       other types the folder holds, so "my file is not there" has an answer.
     * SAVING NAMES THE FILE IN ITS OWN BOX and warns before replacing one.
     * IT REMEMBERS where each kind of window was last used and opens there again.

   makeFileBrowser() is handed what it needs from the bridge - the one route to the
   machine, and where this installation keeps plans - and returns browseFor(opts):
     title      the window's heading
     suffixes   the file types it offers (open); none means every file (save)
     folders    true for a SAVE: a folder is chosen, and `name` is written into it
     name       the suggested file name, for a save
     okLabel    the main button
     start      the folder to open in (otherwise where this kind was last used)
     kind       what "the same kind of window" means for remembering; defaults sensibly
   It resolves to the chosen full path, or null. */

function makeFileBrowser({ call, where }) {
  const esc = s => String(s ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  /* ---- what a file is ----------------------------------------------------- */
  const TYPES = [
    { test: /\.prap$/i,       badge: "PLAN", cls: "pl", label: "PM_APP plan" },
    { test: /\.prap\.json$/i, badge: "JSON", cls: "js", label: "Interchange file (.prap.json)" },
    { test: /\.xlsx$/i,       badge: "XLSX", cls: "xl", label: "Excel workbook" },
    { test: /\.xls[mb]?$/i,   badge: "XLS",  cls: "xl", label: "Excel workbook (older format)" },
    { test: /\.json$/i,       badge: "JSON", cls: "js", label: "JSON file" },
    { test: /\.csv$/i,        badge: "CSV",  cls: "cs", label: "CSV text" },
    { test: /\.pdf$/i,        badge: "PDF",  cls: "pd", label: "PDF document" },
  ];
  function typeOf(name) {
    const t = TYPES.find(x => x.test.test(name));
    if (t) return t;
    const ext = (name.match(/\.([^.]{1,5})$/) || [])[1];
    return { badge: ext ? ext.toUpperCase() : "FILE", cls: "ot",
             label: ext ? `${ext.toUpperCase()} file` : "File" };
  }

  /* ---- icons, drawn rather than borrowed ----------------------------------
     Emoji were used before, and they are drawn by the system font: a different
     picture on every machine, and in colour that ignores the theme. These follow the
     theme and are the same everywhere. */
  const G = {
    folder: '<path d="M3 6.6A1.6 1.6 0 0 1 4.6 5h4.5l2 2h8.3A1.6 1.6 0 0 1 21 8.6v8.8A1.6 1.6 0 0 1 19.4 19H4.6A1.6 1.6 0 0 1 3 17.4z"/>',
    mine:   '<circle cx="12" cy="8.2" r="3.6"/><path d="M4.5 19.5c.9-3.6 4-5.6 7.5-5.6s6.6 2 7.5 5.6z"/>',
    team:   '<circle cx="8.6" cy="8.8" r="3"/><circle cx="16.4" cy="9.6" r="2.5"/><path d="M2.8 19c.7-3 3-4.8 5.8-4.8s5.1 1.8 5.8 4.8z"/><path d="M14.6 19c-.3-1.6-1-2.9-2-3.9 1-.8 2.3-1.2 3.8-1.2 2.4 0 4.3 1.5 4.9 4.1V19z"/>',
    recent: '<path d="M12 3.5a8.5 8.5 0 1 1-8.5 8.5h2.2A6.3 6.3 0 1 0 12 5.7z"/><path d="M11 7.5h2v4.6l3.2 1.9-1 1.7-4.2-2.5z"/><path d="M2.4 7.8 6.6 7l.8 4.2z"/>',
    home:   '<path d="M12 3.6 3 11h2.6v8.4h4.8v-5.2h3.2v5.2h4.8V11H21z"/>',
    desk:   '<path d="M3 4.8h18v11H3z"/><path d="M9 17.6h6l.8 2H8.2z"/>',
    docs:   '<path d="M6 3h8.5L19 7.5V21H6z"/>',
    down:   '<path d="M11 3.5h2v9.2l3.3-3.3 1.4 1.4-5.7 5.7-5.7-5.7 1.4-1.4 3.3 3.3z"/><path d="M4.5 18h15v2.2h-15z"/>',
    drive:  '<path d="M3.5 6.5h17v11h-17z"/>',
    back:   '<path d="M15.4 5 8.4 12l7 7 1.5-1.5-5.5-5.5 5.5-5.5z"/>',
    fwd:    '<path d="m8.6 5 7 7-7 7-1.5-1.5 5.5-5.5-5.5-5.5z"/>',
    up:     '<path d="M12 5.2 5 12.2l1.5 1.5 4.4-4.4V19h2.2V9.3l4.4 4.4 1.5-1.5z"/>',
    reload: '<path d="M17.7 6.3A8 8 0 1 0 20 12h-2.2a5.8 5.8 0 1 1-1.7-4.1L13 11h7V4z"/>',
    list:   '<path d="M4 5h16v2.4H4zm0 5.8h16v2.4H4zm0 5.8h16V19H4z"/>',
    tiles:  '<path d="M4 4h7v7H4zm9 0h7v7h-7zM4 13h7v7H4zm9 0h7v7h-7z"/>',
    search: '<path d="M10.5 4a6.5 6.5 0 0 1 5.2 10.4l4.4 4.4-1.4 1.4-4.4-4.4A6.5 6.5 0 1 1 10.5 4zm0 2.2a4.3 4.3 0 1 0 0 8.6 4.3 4.3 0 0 0 0-8.6z"/>',
    lock:   '<path d="M7.5 10V8a4.5 4.5 0 0 1 9 0v2H18v10H6V10zm2.2 0h4.6V8a2.3 2.3 0 0 0-4.6 0z"/>',
  };
  const svg = (g, cls = "") =>
    `<svg class="fb-g ${cls}" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor">${G[g]}</svg>`;
  /** A file's picture: a page with a folded corner, its type written across it. */
  function fileIcon(name, big) {
    const t = typeOf(name);
    return `<span class="fb-doc ${t.cls}${big ? " big" : ""}" aria-hidden="true">`
      + `<svg viewBox="0 0 24 30"><path class="pg" d="M2 1.5h13.5L22 8v20.5H2z"/>`
      + `<path class="fold" d="M15.5 1.5V8H22z"/></svg>`
      + `<b>${esc(t.badge)}</b></span>`;
  }
  const folderIcon = big => `<span class="fb-fold${big ? " big" : ""}">${svg("folder")}</span>`;

  /* ---- time, said two ways ------------------------------------------------
     The exact stamp stays on every row - 2026-10-07 14:32, local, the same shape
     everywhere so a column of them sorts by eye (R-56) - and how long ago that was is
     put beside it, because "which of these did I save this morning" is answered by
     the second, not the first. */
  const p2 = n => String(n).padStart(2, "0");
  const stamp = ms => {
    if (!ms) return "";
    const d = new Date(ms);
    return `${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())} `
      + `${p2(d.getHours())}:${p2(d.getMinutes())}`;
  };
  function ago(ms, now = Date.now()) {
    if (!ms) return "";
    const s = Math.round((now - ms) / 1000);
    if (s < 0) return "in the future";
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.round(s / 60)} min ago`;
    if (s < 86400) return `${Math.round(s / 3600)} h ago`;
    const days = Math.floor(s / 86400);
    if (days === 1) return "yesterday";
    if (days < 7) return `${days} days ago`;
    if (days < 60) return `${Math.round(days / 7)} wk ago`;
    if (days < 730) return `${Math.round(days / 30)} mo ago`;
    return `${Math.round(days / 365)} yr ago`;
  }
  /** Which band of the date-grouped listing a time falls in. */
  function band(ms, now = new Date()) {
    if (!ms) return "Older";
    const d0 = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    if (ms >= d0) return "Today";
    if (ms >= d0 - 86400000) return "Yesterday";
    const wk = d0 - ((now.getDay() + 6) % 7) * 86400000;          // since Monday
    if (ms >= wk) return "Earlier this week";
    if (ms >= new Date(now.getFullYear(), now.getMonth(), 1).getTime()) return "Earlier this month";
    return "Older";
  }
  const size = n => n == null ? "" : n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB`
    : `${Math.max(1, Math.round(n / 1024))} KB`;

  /* ---- paths ----------------------------------------------------------------- */
  const tidy = x => String(x || "").replace(/[\\/]+$/, "").toLowerCase();
  const sameDir = (a, b) => Boolean(a) && tidy(a) === tidy(b);
  const inside = (p, dir) => Boolean(dir) && (sameDir(p, dir)
    || tidy(p).startsWith(tidy(dir) + (dir.includes("\\") ? "\\" : "/")));
  const sepOf = p => (String(p).includes("\\") || /^[A-Za-z]:/.test(p) ? "\\" : "/");
  const join = (d, n) => String(d).replace(/[\\/]+$/, "") + sepOf(d) + n;
  const baseName = p => String(p).replace(/[\\/]+$/, "").split(/[\\/]/).pop() || p;
  const dirName = p => {
    const s = String(p).replace(/[\\/]+$/, ""), i = Math.max(s.lastIndexOf("\\"), s.lastIndexOf("/"));
    return i > 0 ? s.slice(0, i + (/^[A-Za-z]:$/.test(s.slice(0, i)) ? 1 : 0)) : (i === 0 ? "/" : s);
  };

  /** Your own folder and the team's, when the installation has both. */
  function places() {
    const out = [];
    if (where.workspaces)
      out.push({ label: "My plans", path: where.workspaces, icon: "mine",
                 hint: "Your own folder. Nobody else can open what is in here, so a plan "
                     + "here takes no editing hold and never times out." });
    if (where.shared)
      out.push({ label: "Team plans", path: where.shared, icon: "team",
                 hint: "Everybody can open these, and the application keeps one writer "
                     + "at a time. A plan the team works on belongs here." });
    return out;
  }

  /** The path as buttons. Inside My plans or Team plans the place's own name stands
   *  for everything above it - "Team plans › 2026 › Q4" says more than eight folders
   *  of installation path. A long path keeps its first and last three steps. */
  function crumbs(path) {
    const place = places().find(pl => inside(path, pl.path));
    const sep = sepOf(path);
    let root, rest;
    if (place) {
      root = { name: place.label, path: place.path, place: true };
      rest = String(path).slice(String(place.path).replace(/[\\/]+$/, "").length);
    } else if (/^\\\\/.test(path)) {
      const m = String(path).match(/^(\\\\[^\\]+\\[^\\]+)(.*)$/);
      root = { name: m ? m[1] : path, path: m ? m[1] : path };
      rest = m ? m[2] : "";
    } else if (/^[A-Za-z]:/.test(path)) {
      root = { name: path.slice(0, 2), path: path.slice(0, 2) + "\\" };
      rest = path.slice(2);
    } else {
      root = { name: "/", path: "/" };
      rest = String(path).slice(1);
    }
    const out = [root];
    let acc = root.path;
    for (const part of rest.split(/[\\/]+/).filter(Boolean)) {
      acc = acc.endsWith(sep) ? acc + part : acc + sep + part;
      out.push({ name: part, path: acc });
    }
    if (out.length > 5) return [out[0], { gap: true }, ...out.slice(-3)];
    return out;
  }

  /* ---- what is remembered between windows (this browser only) -------------- */
  const store = {
    get(k, d) { try { const v = localStorage.getItem("pm.fb." + k); return v == null ? d : JSON.parse(v); }
                catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem("pm.fb." + k, JSON.stringify(v)); } catch (e) { /* private mode */ } },
  };
  function rememberFolder(kind, dir) {
    if (!dir) return;
    store.set("last." + kind, dir);
    const recent = store.get("recent", []).filter(d => !sameDir(d, dir));
    recent.unshift(dir);
    store.set("recent", recent.slice(0, 6));
  }

  /* ======================================================== the window itself */
  return function browseFor(opts) {
    opts = opts || {};
    const save = Boolean(opts.folders);
    const kind = opts.kind || (save ? "save" : (opts.suffixes || []).join("") || "any");
    const accepts = (opts.suffixes || []).map(s => s.toLowerCase());
    const typesLine = accepts.length
      ? accepts.map(s => `${typeOf("x" + s).label} (${s})`).join(", ")
      : "";

    return new Promise(resolve => {
      const back = document.createElement("div");
      back.className = "pm-back fb-back";
      back.innerHTML = `<div class="pm-box fb" role="dialog" aria-modal="true"
          aria-label="${esc(opts.title || "Choose a file")}">
        <div class="fb-top">
          <h3>${esc(opts.title || "Choose a file")}</h3>
          ${typesLine ? `<span class="fb-types">Shows: ${esc(typesLine)}</span>` : ""}
        </div>
        <div class="fb-bar">
          <button class="fb-ic" data-nav="back" title="Back (Alt+←)">${svg("back")}</button>
          <button class="fb-ic" data-nav="fwd" title="Forward (Alt+→)">${svg("fwd")}</button>
          <button class="fb-ic" data-nav="up" title="Up one level (Backspace)">${svg("up")}</button>
          <nav class="fb-crumbs" data-crumbs aria-label="Folder path"></nav>
          <button class="fb-ic" data-nav="reload" title="Refresh">${svg("reload")}</button>
          <label class="fb-find">${svg("search")}<input data-find type="search"
            placeholder="Filter this folder" aria-label="Filter this folder"></label>
          <span class="fb-views" role="group" aria-label="View">
            <button class="fb-ic" data-view="list" title="List">${svg("list")}</button>
            <button class="fb-ic" data-view="tiles" title="Tiles">${svg("tiles")}</button>
          </span>
        </div>
        <div class="fb-main">
          <aside class="fb-side" data-side></aside>
          <section class="fb-pane">
            <div class="fb-files" data-files tabindex="0" role="listbox"
                 aria-label="Folders and files"></div>
            <p class="fb-note" data-note></p>
          </section>
          <aside class="fb-info" data-info></aside>
        </div>
        <div class="fb-foot">
          ${save
            ? `<label class="fb-name"><span>File name</span>
                 <input data-name spellcheck="false"></label>
               <span class="fb-in" data-in></span>`
            : `<input class="fb-path" data-path spellcheck="false"
                 placeholder="…or type a full path, e.g. \\\\server\\share\\plan.xlsx">`}
          <span class="fb-warn" data-warn hidden></span>
          <span class="pm-grow"></span>
          <button class="btn" data-cancel>Cancel</button>
          <button class="btn primary" data-ok>${esc(opts.okLabel || "Choose")}</button>
        </div></div>`;
      document.body.appendChild(back);
      const q = s => back.querySelector(s);

      let here = null, last = null, picked = null, cursor = -1;
      let order = store.get("order", { key: "date", desc: true });
      let view = store.get("view", "list");
      let find = "";
      const hist = [], ahead = [];
      // The double-click guard of R-57, kept: a folder opens on its first click and the
      // list is redrawn under the pointer, so the second click of a double-click must not
      // land on - and open - whatever row is now there.
      let drawnAt = 0, armed = null;
      const SETTLE = 450;

      const done = v => {
        if (v) rememberFolder(kind, save ? dirName(v) : (here || dirName(v)));
        back.remove();
        document.removeEventListener("keydown", onKey, true);
        resolve(v);
      };

      /* ---- choosing ----------------------------------------------------------- */
      function target() {
        if (save) {
          const n = q("[data-name]").value.trim();
          if (!n) return null;
          if (/[\\/]/.test(n)) return n;                     // a full path, typed
          return here ? join(here, n) : null;
        }
        const typed = q("[data-path]").value.trim();
        return typed || picked;
      }
      function refreshFoot() {
        const t = target();
        q("[data-ok]").disabled = !t;
        const w = q("[data-warn]");
        w.hidden = true;
        if (save && t && last) {
          const n = baseName(t);
          const hit = last.entries.find(e => !e.dir && e.name.toLowerCase() === n.toLowerCase()
                                              && sameDir(dirName(t), last.path));
          if (hit) {
            w.hidden = false;
            w.textContent = `${n} is already in this folder and will be replaced.`;
          }
        }
        if (save) q("[data-in]").textContent = here ? `in ${baseName(here) || here}` : "";
      }
      q("[data-ok]").onclick = () => { const t = target(); if (t) done(t); };
      q("[data-cancel]").onclick = () => done(null);
      back.onclick = e => { if (e.target === back) done(null); };
      if (save) {
        q("[data-name]").value = opts.name || "";
        q("[data-name]").oninput = refreshFoot;
      } else {
        q("[data-path]").oninput = refreshFoot;
      }

      /* ---- the keyboard --------------------------------------------------------- */
      function onKey(e) {
        if (!document.body.contains(back)) return;
        // The window owns the keyboard while it is open: Enter, Backspace and the arrows
        // mean something to the page underneath as well, and must not reach it.
        e.stopPropagation();
        const inField = e.target.matches && e.target.matches("input");
        if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); return done(null); }
        if (e.altKey && e.key === "ArrowLeft") { e.preventDefault(); return nav("back"); }
        if (e.altKey && e.key === "ArrowRight") { e.preventDefault(); return nav("fwd"); }
        if (e.altKey && e.key === "ArrowUp") { e.preventDefault(); return nav("up"); }
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
          e.preventDefault(); return q("[data-find]").focus();
        }
        if (inField && e.key !== "ArrowDown" && e.key !== "ArrowUp"
            && !(e.key === "Enter" && e.target.matches("[data-find]"))) {
          if (e.key === "Enter" && !q("[data-ok]").disabled) { e.preventDefault(); q("[data-ok]").click(); }
          return;
        }
        const rows = [...back.querySelectorAll("[data-row]")];
        if (e.key === "ArrowDown" || e.key === "ArrowUp") {
          e.preventDefault();
          if (!rows.length) return;
          cursor = Math.max(0, Math.min(rows.length - 1, cursor + (e.key === "ArrowDown" ? 1 : -1)));
          point(rows[cursor], true);
          q("[data-files]").focus();
        } else if (e.key === "Enter") {
          e.preventDefault();
          const r = rows[cursor];
          if (r) activate(r, true);
          else if (!q("[data-ok]").disabled) q("[data-ok]").click();
        } else if (e.key === "Backspace") {
          e.preventDefault(); nav("up");
        }
      }
      document.addEventListener("keydown", onKey, true);

      /* ---- moving about ----------------------------------------------------------- */
      function nav(how) {
        if (how === "back" && hist.length) { ahead.push(here); go(hist.pop(), true); }
        else if (how === "fwd" && ahead.length) { hist.push(here); go(ahead.pop(), true); }
        else if (how === "up" && last && last.parent) go(last.parent);
        else if (how === "reload" && here) go(here, true);
      }
      for (const b of back.querySelectorAll("[data-nav]")) b.onclick = () => nav(b.dataset.nav);
      for (const b of back.querySelectorAll("[data-view]"))
        b.onclick = () => { view = b.dataset.view; store.set("view", view); draw(); };
      q("[data-find]").oninput = e => { find = e.target.value.trim().toLowerCase(); draw(); };

      async function go(path, quiet) {
        let r;
        try { r = await call("fs/list", { path, suffixes: opts.suffixes }); }
        catch (e) { q("[data-note]").textContent = e.message; return; }
        if (!quiet && here && !sameDir(here, r.path)) { hist.push(here); ahead.length = 0; }
        here = r.path; last = r; picked = null; cursor = -1;
        if (!save) q("[data-path]").value = "";
        find = ""; q("[data-find]").value = "";
        // The R-57 guard starts HERE, at a change of folder - not at every redraw. A
        // filter or a sort redraws too, and a click straight after one is a real click.
        drawnAt = Date.now(); armed = null;
        side(); bar(); draw();
      }

      /* ---- the sidebar ------------------------------------------------------------ */
      function side() {
        const s = q("[data-side]");
        const group = (title, items) => items.length
          ? `<h4>${esc(title)}</h4>` + items.map(it => `<button class="fb-place${
              sameDir(here, it.path) ? " on" : ""}${it.place ? " place" : ""}" data-go="${esc(it.path)}"
              title="${esc(it.hint || it.path)}">${svg(it.icon)}<span>${esc(it.label)}</span></button>`).join("")
          : "";
        const pl = places().map(p => ({ ...p, place: true }));
        const recent = store.get("recent", [])
          .filter(d => !pl.some(p => sameDir(p.path, d)))
          .slice(0, 5)
          .map(d => ({ label: baseName(d) || d, path: d, icon: "recent", hint: d }));
        const roots = (last && last.roots) || [];
        const ICON = { Home: "home", Desktop: "desk", Documents: "docs", Downloads: "down" };
        const comp = roots.filter(r => ICON[r.name]).map(r => ({ label: r.name, path: r.path, icon: ICON[r.name] }));
        const drives = roots.filter(r => !ICON[r.name]).map(r => ({ label: r.name, path: r.path, icon: "drive" }));
        s.innerHTML = group("Plans", pl) + group("Recent folders", recent)
          + group("This computer", comp) + group("Drives", drives);
        for (const b of s.querySelectorAll("[data-go]")) b.onclick = () => go(b.dataset.go);
      }

      /* ---- the path bar ----------------------------------------------------------- */
      function bar() {
        const c = q("[data-crumbs]");
        c.innerHTML = crumbs(here).map((x, i, all) => x.gap
          ? `<span class="fb-gap" title="${esc(here)}">…</span><span class="fb-sep">›</span>`
          : `<button class="fb-crumb${x.place ? " place" : ""}${i === all.length - 1 ? " on" : ""}"
               data-go="${esc(x.path)}" title="${esc(x.path)}">${x.place ? svg(
                 places().find(p => p.label === x.name)?.icon || "folder") : ""}${esc(x.name)}</button>`
            + (i < all.length - 1 ? `<span class="fb-sep">›</span>` : "")).join("");
        for (const b of c.querySelectorAll("[data-go]")) b.onclick = () => go(b.dataset.go);
        c.scrollLeft = c.scrollWidth;
        q('[data-nav="back"]').disabled = !hist.length;
        q('[data-nav="fwd"]').disabled = !ahead.length;
        q('[data-nav="up"]').disabled = !(last && last.parent);
      }

      /* ---- the files ------------------------------------------------------------- */
      function sorted(list) {
        const k = order.key, d = order.desc ? -1 : 1;
        const by = {
          name: (a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }),
          date: (a, b) => (a.mtime || 0) - (b.mtime || 0) || a.name.localeCompare(b.name),
          size: (a, b) => (a.size || 0) - (b.size || 0),
          type: (a, b) => typeOf(a.name).label.localeCompare(typeOf(b.name).label)
                          || a.name.localeCompare(b.name),
        }[k];
        return list.slice().sort((a, b) => d * by(a, b));
      }

      function draw() {
        if (!last) return;
        for (const b of back.querySelectorAll("[data-view]"))
          b.classList.toggle("on", b.dataset.view === view);
        const box = q("[data-files]");
        box.className = `fb-files ${view}`;
        const keep = e => !find || e.name.toLowerCase().includes(find);
        const folders = sorted(last.entries.filter(e => e.dir && keep(e)));
        const files = sorted(last.entries.filter(e => !e.dir && keep(e)));
        const newest = files.reduce((m, e) => (e.mtime || 0) > (m ? m.mtime || 0 : -1) ? e : m, null);
        const arrow = k => order.key === k ? (order.desc ? " ▾" : " ▴") : "";
        let html = view === "list"
          ? `<div class="fb-head" role="presentation">
               <button data-sort="name" class="c-n${order.key === "name" ? " on" : ""}">Name${arrow("name")}</button>
               <button data-sort="date" class="c-d${order.key === "date" ? " on" : ""}">Modified${arrow("date")}</button>
               <button data-sort="type" class="c-t${order.key === "type" ? " on" : ""}">Type${arrow("type")}</button>
               <button data-sort="size" class="c-s${order.key === "size" ? " on" : ""}">Size${arrow("size")}</button>
             </div>` : "";
        const grouped = order.key === "date" && order.desc;
        let n = 0, lastBand = null;
        const row = e => {
          const t = e.dir ? null : typeOf(e.name);
          const held = e.plan && e.plan.heldBy && e.plan.heldBy.state !== "expired" ? e.plan.heldBy : null;
          const tags = (e === newest && files.length > 1 ? `<span class="pm-new" title="The most recently modified file in this folder">newest</span>` : "")
            + (held ? `<span class="fb-held" title="${esc(held.name)}${held.department ? " (" + esc(held.department) + ")" : ""} is editing this plan">${svg("lock")}${esc(held.name)} editing</span>` : "");
          const sub = e.dir ? "Folder"
            : e.plan && e.plan.savedBy ? `Saved by ${esc(e.plan.savedBy)}` : esc(t.label);
          const i = n++;
          if (view === "tiles")
            return `<div class="fb-row tile${e.dir ? " dir" : ""}" data-row="${i}" role="option"
                      data-fp="${esc(e.path)}" title="${esc(e.name)}">
                      ${e.dir ? folderIcon(true) : fileIcon(e.name, true)}
                      <span class="n">${esc(e.name)}</span>
                      <span class="w">${e.dir ? "Folder" : esc(ago(e.mtime))}</span>${tags ? `<span class="tg">${tags}</span>` : ""}
                    </div>`;
          return `<div class="fb-row${e.dir ? " dir" : ""}" data-row="${i}" role="option"
                    data-fp="${esc(e.path)}">
                    ${e.dir ? folderIcon() : fileIcon(e.name)}
                    <span class="c-n"><span class="n">${esc(e.name)}</span>${tags}
                      <span class="s">${sub}</span></span>
                    <span class="c-d"><span class="dt">${stamp(e.mtime)}</span>
                      <span class="ago">${esc(ago(e.mtime))}</span></span>
                    <span class="c-t">${e.dir ? "Folder" : esc(t.badge)}</span>
                    <span class="c-s sz">${e.dir ? "" : size(e.size)}</span>
                  </div>`;
        };
        if (folders.length) {
          if (grouped) html += `<div class="fb-band">Folders</div>`;
          html += folders.map(row).join("");
        }
        for (const e of files) {
          if (grouped) {
            const b = band(e.mtime);
            if (b !== lastBand) { html += `<div class="fb-band">${b}</div>`; lastBand = b; }
          }
          html += row(e);
        }
        if (!folders.length && !files.length) {
          html += `<div class="fb-empty">${folderIcon(true)}<p>${find
            ? `Nothing here matches “${esc(find)}”.`
            : accepts.length ? "No folders, and none of the files this window opens, are in this folder."
                             : "This folder is empty."}</p></div>`;
        }
        box.innerHTML = html;
        for (const b of box.querySelectorAll("[data-sort]"))
          b.onclick = ev => {
            ev.stopPropagation();
            const k = b.dataset.sort;
            order = order.key === k ? { key: k, desc: !order.desc }
                                    : { key: k, desc: k === "date" || k === "size" };
            store.set("order", order);
            draw();
          };
        const entries = folders.concat(files);
        for (const r of box.querySelectorAll("[data-row]")) {
          const e = entries[+r.dataset.row];
          r._entry = e;
          if (picked && e.path === picked) { r.classList.add("sel"); cursor = +r.dataset.row; }
          r.onclick = ev => {
            if (ev.detail > 1 || Date.now() - drawnAt < SETTLE) return;
            armed = r;
            cursor = +r.dataset.row;
            activate(r, false);
          };
          r.ondblclick = () => { if (!e.dir && armed === r) done(e.path); };
        }
        const shown = folders.length + files.length, all = last.entries.length;
        const bits = [];
        if (find) bits.push(`${shown} of ${all} item(s) match the filter.`);
        else bits.push(`${last.entries.filter(e => e.dir).length} folder(s), `
          + `${last.entries.filter(e => !e.dir).length} file(s).`);
        if (last.hidden) bits.push(`${last.hidden} other file(s) are not shown - this window `
          + `only offers ${accepts.join(", ")}.`);
        if (last.error) bits.unshift(last.error);
        else if (!save) bits.push("Double-click a file to choose it.");
        q("[data-note]").textContent = bits.join(" ");
        info(picked ? entries.find(e => e.path === picked) : null);
        refreshFoot();
      }

      /** A row pointed at by the keyboard: shown, and its details given. */
      function point(r, scroll) {
        for (const o of back.querySelectorAll("[data-row].kb")) o.classList.remove("kb");
        r.classList.add("kb");
        if (scroll) r.scrollIntoView({ block: "nearest" });
        if (!r._entry.dir) pick(r);
        else info(r._entry);
      }
      /** Click or Enter on a row: a folder opens; a file is picked (Enter also chooses). */
      function activate(r, enter) {
        const e = r._entry;
        if (e.dir) return go(e.path);
        pick(r);
        if (enter) done(save ? (q("[data-name]").value = e.name, target()) : e.path);
      }
      function pick(r) {
        const e = r._entry;
        for (const o of back.querySelectorAll("[data-row].sel")) o.classList.remove("sel");
        r.classList.add("sel");
        picked = e.path;
        if (save) q("[data-name]").value = e.name;
        else q("[data-path]").value = "";
        info(e);
        refreshFoot();
      }

      /* ---- the details pane ---------------------------------------------------- */
      function info(e) {
        const pane = q("[data-info]");
        if (!e) {
          const pl = places().find(p => inside(here, p.path));
          pane.innerHTML = `<div class="fb-card">${pl ? `<span class="fb-big">${svg(pl.icon)}</span>`
              : folderIcon(true)}
            <h5>${esc(pl && sameDir(here, pl.path) ? pl.label : baseName(here) || here)}</h5>
            <p class="fb-k">${pl ? esc(pl.hint) : "Folder"}</p>
            <dl><dt>Location</dt><dd class="fb-p">${esc(here)}</dd></dl>
            <p class="fb-tip">${save ? "Pick a file to reuse its name, or type a new one below."
              : "Pick a file to see its details."}</p></div>`;
          return;
        }
        const t = e.dir ? null : typeOf(e.name);
        const pl = e.plan || {};
        const held = pl.heldBy;
        pane.innerHTML = `<div class="fb-card">${e.dir ? folderIcon(true) : fileIcon(e.name, true)}
          <h5>${esc(e.name)}</h5>
          <p class="fb-k">${e.dir ? "Folder" : esc(t.label)}</p>
          <dl>
            ${e.dir ? "" : `<dt>Size</dt><dd>${size(e.size)}</dd>`}
            <dt>Modified</dt><dd>${stamp(e.mtime)}<br><span class="ago">${esc(ago(e.mtime))}</span></dd>
            ${pl.savedBy ? `<dt>Last saved by</dt><dd>${esc(pl.savedBy)}${pl.savedAt
                ? `<br><span class="ago">${esc(stamp(Date.parse(pl.savedAt)))}</span>` : ""}</dd>` : ""}
            ${held ? `<dt>Editing now</dt><dd class="fb-hold ${esc(held.state)}">${esc(held.name)}${
                held.department ? ` (${esc(held.department)})` : ""}<br><span class="ago">${
                held.state === "active" ? "active now" : held.state === "silent"
                ? "has gone quiet" : "hold has expired"}</span></dd>` : ""}
            <dt>Location</dt><dd class="fb-p">${esc(dirName(e.path))}</dd>
          </dl></div>`;
      }

      go(opts.start || store.get("last." + kind, null) || where.workspaces || where.dataDir);
      setTimeout(() => (save ? q("[data-name]") : q("[data-files]")).focus(), 0);
    });
  };
}
