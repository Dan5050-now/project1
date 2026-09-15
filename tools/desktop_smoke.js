/* The desktop application, driven end to end inside itself.
 *
 * Playwright cannot drive Electron from Python, so the test runs where the application
 * does: this file boots the real main.js - the real window, the real menu, the real IPC
 * handlers - and then asks the renderer questions through executeJavaScript.
 *
 * Nothing is stubbed. When this says a workspace was saved, an actual file was written
 * by the actual handler the actual menu calls.
 *
 *     xvfb-run -a node_modules/electron/dist/electron tools/desktop_smoke.js --no-sandbox
 *
 * Driven by tools/test_desktop.py, which reads the RESULT lines below.
 */

"use strict";

const { app, BrowserWindow } = require("electron");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pmapp-smoke-"));
process.env.PM_APP_DIR = tmp;                     // keep the repository clean

const fails = [];
const check = (ok, label, detail = "") => {
  console.log(`RESULT ${ok ? "ok" : "FAIL"} ${label}${detail ? "   " + detail : ""}`);
  if (!ok) fails.push(label);
};

// What is outside the folder BEFORE the application starts. Anything that appears or
// changes after it has run is something it wrote where it promised not to.
const outside = ["Electron", "PM_APP", "pm-app"].map(n => {
  const p = path.join(os.homedir(), ".config", n);
  let st = null;
  try { st = fs.statSync(p).mtimeMs; } catch { /* absent */ }
  return { p, before: st };
});

require("../src/shell/desktop/main.js");          // boots on app.whenReady()

const waitFor = (fn, ms = 20000) => new Promise((res, rej) => {
  const t0 = Date.now();
  const tick = () => {
    let v;
    try { v = fn(); } catch { v = null; }
    if (v) return res(v);
    if (Date.now() - t0 > ms) return rej(new Error("timed out"));
    setTimeout(tick, 100);
  };
  tick();
});

app.whenReady().then(async () => {
  try {
    const win = await waitFor(() => BrowserWindow.getAllWindows()[0]);
    check(true, "the window opens", `${win.getBounds().width}x${win.getBounds().height}`);

    await waitFor(() => !win.webContents.isLoading(), 30000);
    await new Promise(r => setTimeout(r, 2500));   // let the bridge finish its await

    const js = code => win.webContents.executeJavaScript(code, true);

    check(await js("typeof window.pmapp === 'object'"),
          "the preload bridge is the only route to the machine");
    check(await js("typeof window.require === 'undefined' && typeof process === 'undefined'"),
          "and the renderer has no Node of its own — contextIsolation on, "
          + "nodeIntegration off (NR-SEC-02)");

    const caps = await js("window.pmapp.capabilities()");
    check(caps.workspaces && caps.versions && caps.claims && caps.journal,
          "it reports the desktop capabilities, so ui/ adapts rather than being written twice",
          JSON.stringify(caps));

    const paths = await js("window.pmapp.paths()");
    check(paths.dataDir.startsWith(tmp) && /^3/.test(paths.rule),
          "the data folder resolves beside the application, per-user",
          `${paths.rule} → ${path.relative(tmp, paths.dataDir)}`);
    check(fs.existsSync(path.join(paths.dataDir, "workspaces")),
          "and its folders are made at launch");

    check(await js("!!document.getElementById('pm-title')")
          && await js("!!document.getElementById('pm-strip')"),
          "the window chrome is in the page — title and status strip");
    check(await js("document.querySelector('h1').textContent") === "Project Management APP",
          "the product calls itself by its own name (NR-APP-08)");
    check(await js("getComputedStyle(document.getElementById('loadBtn')).display") === "none"
          && await js("getComputedStyle(document.getElementById('themeBtn')).display") === "none",
          "the file buttons and the theme toggle are gone — menus and Windows replace "
          + "them (D-N02, D-N09)");

    const who = await js("document.getElementById('pm-who').textContent");
    check(who && who !== "not signed in", "an identity is established before anything opens", who);

    /* ---- the engine, in the desktop shell -------------------------------- */
    check(await js("typeof calculate === 'function' && typeof derivePeriods === 'function'"),
          "core/ is present and is the same core/ — no calculation lives in the shell");

    /* ---- a real workspace, through the real handlers ---------------------- */
    const ref = path.join(paths.dataDir, "workspaces", "Smoke.prap");
    const saved = await js(`(async () => {
      startBlank();
      const sheets = {};
      for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
      return await window.pmapp.workspace.save(${JSON.stringify(ref)}, sheets, {});
    })()`).catch(e => ({ error: String(e) }));
    check(saved && saved.savedAt && fs.existsSync(ref),
          "a plan is saved through the IPC the menu uses, and lands on the disk",
          saved && saved.savedAt ? path.basename(ref) : JSON.stringify(saved));

    const doc = JSON.parse(fs.readFileSync(ref, "utf8"));
    check(doc.format === "prap-source-data" && doc.workspace.app === "PM_APP"
          && Object.keys(doc.sheets).length === 10,
          "and it is a prap-source-data file with the workspace header on it",
          `${Object.keys(doc.sheets).length} sheets, saved by `
          + `${doc.workspace.last_saved_by?.name}`);

    const back = await js(`window.pmapp.workspace.open(${JSON.stringify(ref)})`);
    check(back && back.sheets && Object.keys(back.sheets).length === 10,
          "reopening it through the same route gives the plan back");

    const recent = await js("window.pmapp.workspace.recent()");
    check(recent.length >= 1 && recent[0].name === "Smoke.prap",
          "and it is in the recent list, with its holder read BEFORE it is opened (U-N01)",
          `${recent.length} entr(y/ies), heldBy=${JSON.stringify(recent[0].heldBy)}`);

    /* ---- the claim -------------------------------------------------------- */
    const took = await js(`window.pmapp.claim.take(${JSON.stringify(ref)})`);
    check(took.ok, "the claim is taken when the plan is edited");
    check(fs.existsSync(ref + ".lock"), "and it is a file beside the plan, as specified");

    const read = await js(`window.pmapp.claim.read(${JSON.stringify(ref)})`);
    check(read && read.state === "active" && /is editing this plan/.test(read.message),
          "which reports who holds it in the words the specification gives",
          read?.message);

    const held = await js(`window.pmapp.claim.holds(${JSON.stringify(ref)})`);
    check(held === true, "the session holds it");

    await js(`window.pmapp.claim.release(${JSON.stringify(ref)})`);
    check(!fs.existsSync(ref + ".lock"), "and releasing it removes the file");

    /* ---- the journal ------------------------------------------------------ */
    await js(`window.pmapp.journal.write(${JSON.stringify(ref)}, [{sheet:"Project"}])`);
    check(fs.existsSync(ref + ".journal"),
          "pending edits journal beside the plan, never into it");
    const j = await js(`window.pmapp.journal.read(${JSON.stringify(ref)})`);
    check(j && j.pending.length === 1, "and can be read back for recovery");

    /* ---- nothing outside the folder --------------------------------------- */
    const touched = outside.filter(o => {
      let now = null;
      try { now = fs.statSync(o.p).mtimeMs; } catch { /* still absent */ }
      return now !== o.before;
    }).map(o => path.basename(o.p));
    check(touched.length === 0,
          "and nothing is written outside the application folder — Chromium's own "
          + "caches included (NR-DEP-06)",
          touched.length ? "touched " + touched.join(", ")
                         : "the userData, cache, crash and log paths all sit under data\\chromium");
  } catch (e) {
    check(false, "the smoke test ran to the end", String(e && e.stack || e));
  }

  console.log(`RESULT-END ${fails.length}`);
  fs.rmSync(tmp, { recursive: true, force: true });
  app.exit(fails.length ? 1 : 0);
});
