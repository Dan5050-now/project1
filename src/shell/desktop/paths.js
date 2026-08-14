/* ============================================================== shell: where things live
   The portable rule says everything lives in one folder. Data safety says an update
   must not be able to delete a plan. Those pull against each other, and this file is
   where they are resolved.

       PM_APP\                      copy this anywhere; delete it to remove the app
         PM_APP.exe                 \
         resources\                  |  replaced wholesale by an update
         version.txt                /
         data\                      NEVER touched by an update - not in the zip
           users\<account>\
             settings.json
             workspaces\
             backups\

   Specification: PRAP_NewApp_Specification_v1.2.xlsx sheet 10.  Node only. */

"use strict";

const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

/** Where the data folder is, resolved in ONE fixed order, and the answer says which
 *  rule chose it. A portable application that will not say where its data went is a
 *  support problem, and the answer costs one line on a dialog (NR-DEP-10). */
function resolveDataDir(opts = {}) {
  const {
    argv = process.argv,
    env = process.env,
    appDir = defaultAppDir(),
    account = accountName(env),
    // Injectable ONLY so the read-only case can be tested. A process running as an
    // administrator - or as root, which is how the test suite runs here - can write to
    // a directory whose permissions forbid it, so the real predicate cannot be made to
    // say no. The alternative is leaving NR-DEP-09 untested until somebody meets it on
    // a share, which is the worst possible moment.
    canWrite = writable,
  } = opts;

  // 1. --data=<path> - how a personal shortcut carries it. Explicit, visible, and the
  //    user's rather than the application's.
  const arg = argv.find(a => a.startsWith("--data="));
  if (arg) return settle(arg.slice(7), "1 — the --data argument", account, opts);

  // 2. PRAP_DATA - for a site that sets it centrally.
  if (env.PRAP_DATA) return settle(env.PRAP_DATA, "2 — the PRAP_DATA variable", account, opts);

  // 3. data\ beside the application, if writable. The ordinary case, single-user or
  //    shared: Q-N15 says the share would be writable, so each person simply gets
  //    their own folder under it (NR-DEP-15) and nobody is asked anything.
  const beside = path.join(appDir, "data");
  if (canWrite(appDir) || canWrite(beside))
    return settle(beside, "3 — writable data\\ beside the application", account, opts);

  // 4. Ask. The caller shows the dialog; this only reports that it must.
  return { dir: null, rule: "4 — ask the user", account, mustAsk: true, appDir };
}

function settle(root, rule, account, opts) {
  const dir = opts.perUser === false ? root : path.join(root, "users", account);
  return { dir, rule, account, mustAsk: false, appDir: opts.appDir || defaultAppDir() };
}

/** The Windows account name, not the declared one.
 *
 *  The declared name is editable and could collide - two people may both be "Kim" -
 *  while the account name is unique on the machine and stable. The declared name is
 *  what colleagues see; the account name is what files are filed under (S-N06). */
function accountName(env = process.env) {
  const raw = env.USERNAME || env.USER || os.userInfo().username || "user";
  return raw.replace(/[^A-Za-z0-9._-]/g, "_") || "user";
}

function defaultAppDir() {
  // In a packaged application this is the folder holding the executable; running from
  // source it is the repository root. Both are "the folder the application is in".
  return process.env.PM_APP_DIR
      || (process.resourcesPath && !/node_modules/.test(process.resourcesPath)
            ? path.dirname(process.resourcesPath)
            : path.resolve(__dirname, "..", "..", ".."));
}

function writable(dir) {
  try {
    fs.accessSync(dir, fs.constants.W_OK);
    return true;
  } catch { return false; }
}

/** Create the folders the resolved location needs. Called once at launch. */
function ensure(dataDir) {
  for (const d of [dataDir, path.join(dataDir, "workspaces"), path.join(dataDir, "backups")])
    fs.mkdirSync(d, { recursive: true });
  return dataDir;
}

const settingsPath = dataDir => path.join(dataDir, "settings.json");

function readSettings(dataDir) {
  try {
    return JSON.parse(fs.readFileSync(settingsPath(dataDir), "utf8"));
  } catch {
    return { identity: null, window: null, recent: [], preferences: {} };
  }
}

function writeSettings(dataDir, settings) {
  const tmp = `${settingsPath(dataDir)}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, JSON.stringify(settings, null, 1), "utf8");
  fs.renameSync(tmp, settingsPath(dataDir));
}

/** Recent workspaces: at least ten, most recent first, per user, and stored RELATIVE
 *  to the application folder wherever they can be - so copying the folder to another
 *  machine or drive letter does not break the list (NR-DEP-08). */
function addRecent(settings, ref, appDir, meta = {}) {
  const rel = toPortable(ref, appDir);
  const rest = (settings.recent || []).filter(r => r.ref !== rel);
  settings.recent = [{ ref: rel, name: path.basename(ref), at: new Date().toISOString(),
                       ...meta }, ...rest].slice(0, 10);
  return settings;
}

function toPortable(ref, appDir) {
  const rel = path.relative(appDir, ref);
  return rel && !rel.startsWith("..") && !path.isAbsolute(rel) ? rel.split(path.sep).join("/")
                                                              : ref;
}

const fromPortable = (ref, appDir) =>
  path.isAbsolute(ref) ? ref : path.resolve(appDir, ref);

module.exports = {
  resolveDataDir, accountName, defaultAppDir, writable, ensure,
  settingsPath, readSettings, writeSettings,
  addRecent, toPortable, fromPortable,
};
