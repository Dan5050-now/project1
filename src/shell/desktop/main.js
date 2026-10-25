/* ============================================================ shell: the window
   The Electron main process. It owns the window, the menu, and the filesystem; the
   renderer owns everything a user looks at and can reach none of it except through
   preload.js.

   What this file is NOT: a place where numbers are decided. Every figure comes from
   core/, shared byte-for-byte with the web application. If a calculation appears in
   here, something has gone wrong.

   Specification: PRAP_NewApp_Specification_v1.2.xlsx sheets 05, 06, 07, 10. */

"use strict";

const { app, BrowserWindow, Menu, dialog, ipcMain, nativeTheme, shell } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const WS = require("../../storage/desktop/workspace.js");
const CL = require("../../storage/desktop/claim.js");
const PA = require("./paths.js");

const VERSION = readVersion();
WS.setVersion(VERSION);

let win = null;
let dataDir = null;
let appDir = null;

/* Electron's own housekeeping, moved inside the folder.
 *
 * Found by the smoke test, and it is exactly the defect the non-installed rule exists
 * to catch: left alone, Chromium writes its caches, GPU cache and crash dumps to
 * ~/.config/Electron (%APPDATA%\Electron on Windows). Over a megabyte of it, from an
 * application that promises to leave the machine unchanged and to disappear when its
 * folder is deleted (NR-DEP-06, NR-DEP-07).
 *
 * It has to happen HERE - at module load, before app is ready - because by the time
 * boot() runs, Chromium has already chosen where to put things. */
(function keepEverythingInside() {
  const dir = PA.defaultAppDir();
  const resolved = PA.resolveDataDir({ appDir: dir });
  const home = resolved.dir || require("node:os").tmpdir();
  const chromium = path.join(home, "chromium");
  try {
    fs.mkdirSync(chromium, { recursive: true });
    app.setPath("userData", chromium);
    app.setPath("sessionData", chromium);
    app.setPath("crashDumps", path.join(chromium, "crash"));
    app.setPath("logs", path.join(chromium, "logs"));
  } catch { /* if this fails the application still runs; it is tidiness, not function */ }
})();
let settings = { identity: null, window: null, recent: [], preferences: {} };
let openRef = null;                       // the workspace this session has open
let heartbeat = null;

function readVersion() {
  try {
    return fs.readFileSync(path.join(PA.defaultAppDir(), "version.txt"), "utf8").trim();
  } catch { return "1.0"; }
}

/* ------------------------------------------------------------------ launch -- */

function boot() {
  appDir = PA.defaultAppDir();
  const resolved = PA.resolveDataDir({ appDir });

  if (resolved.mustAsk) {
    // NR-DEP-09: a read-only folder is told about at launch, not discovered at the
    // first Save - which is the worst possible moment to find out.
    const chosen = dialog.showOpenDialogSync({
      title: "Where should Project Management APP keep your data?",
      message: `${appDir} cannot be written to, so this application cannot keep its `
             + `data beside itself. Choose a folder of your own.`,
      properties: ["openDirectory", "createDirectory"],
    });
    if (!chosen || !chosen[0]) { app.quit(); return; }
    dataDir = PA.ensure(path.join(chosen[0], "users", resolved.account));
    resolved.rule = "4 — chosen by you";
  } else {
    dataDir = PA.ensure(resolved.dir);
  }
  resolved.dir = dataDir;
  boot.resolved = resolved;

  WS.sweepTemp(dataDir);                          // an interrupted save left a .tmp
  WS.sweepTemp(path.join(dataDir, "workspaces"));
  settings = PA.readSettings(dataDir);

  createWindow();
}

function createWindow() {
  const w = settings.window || {};
  win = new BrowserWindow({
    width: w.width || 1500,
    height: w.height || 950,
    x: onScreen(w) ? w.x : undefined,            // an off-screen position is ignored
    y: onScreen(w) ? w.y : undefined,
    title: "Project Management APP",
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#000000" : "#f2f2f7",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,                    // NR-SEC-02
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  });

  Menu.setApplicationMenu(buildMenu());
  win.loadFile(path.join(__dirname, "index.html"));
  win.on("close", onClose);
  win.on("closed", () => { win = null; });
}

const onScreen = w =>
  Number.isFinite(w.x) && Number.isFinite(w.y) && w.x > -2000 && w.y > -2000;

function onClose() {
  // The claim is released on the way out - NOT on save alone, which would hand the
  // plan to somebody else mid-task (N-22).
  if (openRef && settings.identity) {
    try { CL.releaseClaim(openRef, settings.identity); } catch { /* going anyway */ }
  }
  if (win && !win.isDestroyed()) {
    const b = win.getBounds();
    settings.window = { width: b.width, height: b.height, x: b.x, y: b.y };
    try { PA.writeSettings(dataDir, settings); } catch { /* going anyway */ }
  }
}

/* -------------------------------------------------------------------- menu -- */

function buildMenu() {
  const send = what => () => win?.webContents.send("menu", what);
  return Menu.buildFromTemplate([
    { label: "File", submenu: [
      { label: "New plan", accelerator: "CmdOrCtrl+N", click: send("new") },
      { label: "Open…", accelerator: "CmdOrCtrl+O", click: send("open") },
      { label: "Open recent", submenu: recentMenu() },
      { type: "separator" },
      { label: "Save", accelerator: "CmdOrCtrl+S", click: send("save") },
      { label: "Save As…", accelerator: "CmdOrCtrl+Shift+S", click: send("saveAs") },
      { label: "Close plan", click: send("close") },
      { type: "separator" },
      { label: "Import source data…", click: send("import") },
      { label: "Look at a source file…", click: send("look") },
      { label: "Export to Excel", click: send("export") },
      { label: "Export JSON", click: send("exportJson") },
      { type: "separator" },
      { role: "quit" },
    ]},
    { label: "Edit", submenu: [
      { label: "Save changes", click: send("commit") },
      { label: "Leave without change", click: send("discard") },
      { label: "Show unsaved changes", click: send("changes") },
    ]},
    { label: "View", submenu: [
      { label: "Overall", click: send("tab:t-overall") },
      { label: "Source data (project)", click: send("tab:t-proj") },
      { label: "Source data (person)", click: send("tab:t-pers") },
      { label: "General assumptions", click: send("tab:t-gen") },
      { type: "separator" },
      { role: "reload" }, { role: "toggleDevTools" },
    ]},
    { label: "Plan", submenu: [
      { label: "Who is editing…", click: send("who") },
      { label: "Restore previous version…", click: send("restore") },
      { label: "Plan properties", click: send("props") },
    ]},
    { label: "Help", submenu: [
      { label: "About Project Management APP", click: about },
      { label: "Open the data folder", click: () => shell.openPath(dataDir) },
    ]},
  ]);
}

function recentMenu() {
  const items = (settings.recent || []).map(r => ({
    label: r.name,
    click: () => win?.webContents.send("menu", "open:" + PA.fromPortable(r.ref, appDir)),
  }));
  return items.length ? items : [{ label: "(nothing yet)", enabled: false }];
}

function about() {
  const r = boot.resolved || {};
  dialog.showMessageBox(win, {
    type: "info",
    title: "About Project Management APP",
    message: "Project Management APP",
    detail: [
      `Version           ${VERSION}`,
      `Source schema     v${WS.SCHEMA_EXPECTED}`,
      `Application       ${appDir}`,
      `Data folder       ${dataDir}`,
      `Chosen by rule    ${r.rule || "unknown"}`,
      settings.identity
        ? `Signed in as      ${settings.identity.name} (${settings.identity.department})`
        : "Signed in as      (not yet)",
    ].join("\n"),
    buttons: ["Close"],
  });
}

/* ------------------------------------------------------------------- wiring - */

const ident = () => settings.identity || { name: PA.accountName(), department: "" };

ipcMain.handle("caps", () =>
  ({ workspaces: true, versions: true, claims: true, journal: true }));

ipcMain.handle("paths", () => ({
  appDir, dataDir, version: VERSION,
  rule: (boot.resolved || {}).rule, account: PA.accountName(),
}));

ipcMain.handle("identity:suggest", () => ({ name: PA.accountName(), department: "" }));
ipcMain.handle("identity:get", () => settings.identity);
ipcMain.handle("identity:set", (_e, id) => {
  settings.identity = { name: String(id.name || "").trim(),
                        department: String(id.department || "").trim() };
  PA.writeSettings(dataDir, settings);
  return settings.identity;
});

ipcMain.handle("ws:open", async (_e, ref) => {
  const full = PA.fromPortable(ref, appDir);
  const out = await WS.openWorkspace(full);
  openRef = full;
  settings = PA.addRecent(settings, full, appDir,
                          { savedBy: out.header.last_saved_by || null });
  PA.writeSettings(dataDir, settings);
  Menu.setApplicationMenu(buildMenu());
  return out;
});

ipcMain.handle("ws:openDialog", async () => {
  const r = dialog.showOpenDialogSync(win, {
    title: "Open a plan",
    defaultPath: path.join(dataDir, "workspaces"),
    filters: [{ name: "Plans", extensions: ["prap"] }],
    properties: ["openFile"],
  });
  return r && r[0] ? r[0] : null;
});

ipcMain.handle("ws:save", async (_e, ref, sheets, header) => {
  const full = PA.fromPortable(ref, appDir);
  const out = await WS.saveWorkspace(full, sheets, header || {}, {
    holdsClaim: r => CL.mayWrite(r, ident()),   // 'nobody else has it', not 'we have it'
    retain: settings.preferences?.retain_versions ?? 1,
    identity: ident(),
  });
  settings = PA.addRecent(settings, full, appDir, { savedBy: ident() });
  PA.writeSettings(dataDir, settings);
  return out;
});

ipcMain.handle("ws:saveAs", async (_e, sheets, header, suggested) => {
  const p = dialog.showSaveDialogSync(win, {
    title: "Save the plan as",
    defaultPath: path.join(dataDir, "workspaces", suggested || "Untitled.prap"),
    filters: [{ name: "Plans", extensions: ["prap"] }],
  });
  if (!p) return null;
  const out = await WS.saveWorkspace(p, sheets, header || {},
                                     { retain: 1, identity: ident() });
  openRef = p;
  settings = PA.addRecent(settings, p, appDir, { savedBy: ident() });
  PA.writeSettings(dataDir, settings);
  Menu.setApplicationMenu(buildMenu());
  return out;
});

ipcMain.handle("ws:recent", async () => {
  // NR-STO-12 / U-N01: say "held by" BEFORE the plan is opened, not after. One small
  // read per entry, which the reviewer agreed is worth it.
  const out = [];
  for (const r of settings.recent || []) {
    const full = PA.fromPortable(r.ref, appDir);
    const held = await CL.readClaim(full).catch(() => null);
    out.push({ ...r, full, exists: fs.existsSync(full),
               heldBy: held ? { name: held.name, department: held.department,
                                state: CL.statusOf(held) } : null });
  }
  return out;
});

ipcMain.handle("ws:versions", (_e, ref) => WS.listVersions(PA.fromPortable(ref, appDir)));
ipcMain.handle("ws:restore", (_e, ref, n) => WS.restoreVersion(PA.fromPortable(ref, appDir), n));
ipcMain.handle("ws:stat", (_e, ref) => WS.stat(PA.fromPortable(ref, appDir)));

ipcMain.handle("claim:take", async (_e, ref) => {
  const full = PA.fromPortable(ref, appDir);
  const r = await CL.claim(full, ident(), { appVersion: VERSION });
  if (r.ok) startHeartbeat(full);
  else r.message = CL.blockedMessage(r.holder, r.state, r.freeAt);
  return r;
});

ipcMain.handle("claim:read", async (_e, ref) => {
  const held = await CL.readClaim(PA.fromPortable(ref, appDir));
  if (!held) return null;
  const state = CL.statusOf(held);
  return { holder: held, state, freeAt: CL.freeAt(held),
           message: CL.blockedMessage(held, state, CL.freeAt(held)) };
});

ipcMain.handle("claim:release", async (_e, ref) => {
  stopHeartbeat();
  return CL.releaseClaim(PA.fromPortable(ref, appDir), ident());
});

ipcMain.handle("claim:holds", (_e, ref) =>
  CL.holdsClaim(PA.fromPortable(ref, appDir), ident()));

/** The heartbeat: thirty seconds, whatever the expiry is. Keeping the two apart is
 *  what lets the application tell a colleague mid-sentence from one whose laptop died
 *  twenty minutes ago, and say which (N-23). */
function startHeartbeat(ref) {
  stopHeartbeat();
  heartbeat = setInterval(async () => {
    const r = await CL.refreshClaim(ref, ident()).catch(() => ({ ok: false }));
    if (!r.ok) {
      stopHeartbeat();
      win?.webContents.send("claim:lost", r.holder || null);
    }
  }, CL.HEARTBEAT_MS);
}

function stopHeartbeat() {
  if (heartbeat) clearInterval(heartbeat);
  heartbeat = null;
}

ipcMain.handle("journal:write", (_e, ref, pending) =>
  WS.writeJournal(PA.fromPortable(ref, appDir), pending));
ipcMain.handle("journal:read", (_e, ref) => WS.readJournal(PA.fromPortable(ref, appDir)));
ipcMain.handle("journal:clear", (_e, ref) => WS.clearJournal(PA.fromPortable(ref, appDir)));

ipcMain.handle("file:openSource", async () => {
  // NR-IMP-05: a look, with no workspace created and nothing left behind.
  const r = dialog.showOpenDialogSync(win, {
    title: "Look at a source file",
    filters: [{ name: "Source data", extensions: ["xlsx", "json"] }],
    properties: ["openFile"],
  });
  if (!r || !r[0]) return null;
  const buf = fs.readFileSync(r[0]);
  if (WS.looksProtected(buf))
    return { error: "protected", name: path.basename(r[0]),
             message: `${path.basename(r[0])} could not be opened. It looks like it is `
                    + `protected by file security — open it in Excel first to unlock it, `
                    + `then import it again.` };
  return { name: path.basename(r[0]), path: r[0], bytes: buf.buffer.slice(
             buf.byteOffset, buf.byteOffset + buf.byteLength) };
});

ipcMain.handle("file:export", async (_e, bytes, suggested) => {
  const p = dialog.showSaveDialogSync(win, {
    title: "Export", defaultPath: path.join(dataDir, suggested || "export.xlsx") });
  if (!p) return null;
  fs.writeFileSync(p, Buffer.from(bytes));
  return { path: p };
});

/* ------------------------------------------------------------------ lifecycle */

app.whenReady().then(boot);
app.on("window-all-closed", () => { stopHeartbeat(); app.quit(); });
app.on("activate", () => { if (!BrowserWindow.getAllWindows().length) createWindow(); });

// NR-SEC-01: nothing here opens a socket, and nothing may navigate away from the file
// it was loaded with. A page that cannot leave is a page that cannot fetch.
app.on("web-contents-created", (_e, contents) => {
  contents.setWindowOpenHandler(() => ({ action: "deny" }));
  contents.on("will-navigate", e => e.preventDefault());
});

module.exports = { boot, buildMenu };          // for the smoke test
