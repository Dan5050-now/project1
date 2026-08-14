/* The storage layer, and every way it can lose somebody's work.
 *
 * All of the risk in the desktop application is in two files - workspace.js and
 * claim.js - and none of it needs a window. So this runs them in plain Node, which
 * means the nastiest cases can actually be tested: killing a process mid-write, two
 * processes racing for the same claim, a heartbeat that stops.
 *
 * A defect that needs a GUI to reproduce is a defect found late.
 *
 *     node tools/test_storage.mjs
 */

import { execFileSync, spawnSync } from "node:child_process";
import { createRequire } from "node:module";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const WS = require(path.join(ROOT, "src/storage/desktop/workspace.js"));
const CL = require(path.join(ROOT, "src/storage/desktop/claim.js"));
const PA = require(path.join(ROOT, "src/shell/desktop/paths.js"));

const fails = [];
const check = (ok, label, detail = "") => {
  console.log(`  ${ok ? "ok  " : "FAIL"} ${label}${detail ? "   " + detail : ""}`);
  if (!ok) fails.push(label);
};

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "pmapp-"));
const ref = path.join(tmp, "Q3 resourcing.prap");
const ME = { name: "Kim Min-jun", department: "Data Management" };
const THEM = { name: "Park Ji-woo", department: "Biostatistics" };

const sheets = n => ({
  Project: Array.from({ length: n }, (_, i) => ({ project_id: `PRJ-${i + 1}`, project_name: `P${i}` })),
  Person: [{ person_id: "PSN-001", person_name: "Kim Min-jun", department: "Data Management" }],
});

console.log("src/storage/desktop — saving, versions, journals, and the write claim\n");

/* ---- 1. a save is atomic, and is only reported once it has landed --------- */
console.log("saving");
const r1 = await WS.saveWorkspace(ref, sheets(3), {}, { identity: ME });
check(fs.existsSync(ref) && r1.savedAt, "a workspace is written and reported saved",
      path.basename(ref));

const doc = JSON.parse(fs.readFileSync(ref, "utf8"));
check(doc.format === "prap-source-data" && doc.format_version === 1,
      "and it is still a prap-source-data file — prap_io.py and the agent guide read it "
      + "as it stands", `format=${doc.format} v${doc.format_version}`);
check(doc.workspace.app === "PM_APP" && doc.workspace.last_saved_by.name === ME.name,
      "with the workspace header additive beside the sheets, not inside them",
      `last saved by ${doc.workspace.last_saved_by.name} (${doc.workspace.last_saved_by.department})`);

const reopened = await WS.openWorkspace(ref);
check(JSON.stringify(reopened.sheets) === JSON.stringify(sheets(3)),
      "reopening gives back exactly what was saved",
      `${reopened.sheets.Project.length} projects`);

check(!fs.readdirSync(tmp).some(f => /\.tmp-\d+$/.test(f)),
      "and no temporary file is left behind by a completed save");

/* ---- 2. killed mid-write, repeatedly ------------------------------------- */
console.log("\ninterrupted saves");
const killer = path.join(tmp, "killer.mjs");
fs.writeFileSync(killer, `
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const WS = require(${JSON.stringify(path.join(ROOT, "src/storage/desktop/workspace.js"))});
const big = { Project: Array.from({length: 4000}, (_, i) => ({ project_id: "PRJ-" + i,
  project_name: "x".repeat(200) })) };
setTimeout(() => process.exit(9), Number(process.argv[3]));
await WS.saveWorkspace(process.argv[2], big, {}, {});
`);

let intact = 0, attempts = 12;
for (let i = 0; i < attempts; i++) {
  spawnSync(process.execPath, [killer, ref, String(1 + i * 2)], { timeout: 10_000 });
  try {
    const d = JSON.parse(fs.readFileSync(ref, "utf8"));
    // Wholly the old contents, or wholly the new. Never half of each.
    const n = d.sheets.Project.length;
    if (n === 3 || n === 4000) intact++;
  } catch { /* counted as not intact */ }
}
check(intact === attempts,
      "killed at twelve different moments during a save, the workspace is always "
      + "wholly old or wholly new", `${intact}/${attempts} readable and complete`);
await WS.sweepTemp(tmp);
check(!fs.readdirSync(tmp).some(f => /\.tmp-\d+$/.test(f)),
      "and the temporary files the kills left behind are swept at launch");

/* ---- 3. versions ---------------------------------------------------------- */
console.log("\nversions");
await WS.saveWorkspace(ref, sheets(3), {}, {});
await WS.saveWorkspace(ref, sheets(5), {}, {});
const vs = await WS.listVersions(ref);
check(vs.length === 1, "one previous version is retained, as Q-N07 asked", `${vs.length} kept`);
const back = await WS.restoreVersion(ref, 1);
check(back.sheets.Project.length === 3,
      "and it is the version before the current one", `${back.sheets.Project.length} projects`);
check(JSON.parse(fs.readFileSync(ref, "utf8")).sheets.Project.length === 5,
      "restoring does NOT overwrite the current file — the caller lands it as a "
      + "pending edit (S-N02)");

await WS.saveWorkspace(ref, sheets(9), {}, {});
check((await WS.listVersions(ref)).length === 1
      && (await WS.restoreVersion(ref, 1)).sheets.Project.length === 5,
      "a third save pushes the oldest out — which is R-N19, recorded rather than hidden");

/* ---- 4. journal and recovery ---------------------------------------------- */
console.log("\npending edits");
await WS.writeJournal(ref, [{ sheet: "Project", row: 2, col: "end_date",
                              from: "2028-06-30", to: "2028-09-30" }]);
check((await WS.readJournal(ref))?.pending.length === 1,
      "pending edits are journalled beside the workspace, never into it");
await WS.saveWorkspace(ref, sheets(9), {}, {});
check((await WS.readJournal(ref)) === null,
      "a committed save clears them — they are no longer pending");

await WS.writeJournal(ref, [{ sheet: "Project" }]);
fs.utimesSync(WS.journalPath(ref), new Date(Date.now() - 60_000), new Date(Date.now() - 60_000));
check((await WS.readJournal(ref)) === null,
      "a journal OLDER than its workspace is not offered — those edits were made "
      + "against figures that have since been replaced");

/* ---- 5. a protected file is not a corrupt one ----------------------------- */
console.log("\nfiles that cannot be read");
const enc = path.join(tmp, "protected.prap");
fs.writeFileSync(enc, Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0, 0]));
let kind = null, msg = "";
try { await WS.openWorkspace(enc); } catch (e) { kind = e.kind; msg = e.message; }
check(kind === "protected" && /protected by file security/.test(msg),
      "an encrypted file reports itself as PROTECTED, not as corrupt (R-N18)",
      msg.slice(0, 72) + "…");

const notPlan = path.join(tmp, "notes.prap");
fs.writeFileSync(notPlan, "just some text");
kind = null;
try { await WS.openWorkspace(notPlan); } catch (e) { kind = e.kind; }
check(kind === "unreadable", "and something that is not a plan says which it is");

const newer = path.join(tmp, "newer.prap");
fs.writeFileSync(newer, JSON.stringify({ format: "prap-source-data", format_version: 1,
  workspace: { app_version: "9.9" }, sheets: {} }));
kind = null;
try { await WS.openWorkspace(newer); } catch (e) { kind = e.kind; }
check(kind === "too_new",
      "a workspace from a newer version is refused, not partially read (NR-DEP-04)");

/* ---- 6. the claim: only one winner, ever ---------------------------------- */
console.log("\nthe write claim");
const c1 = await CL.claim(ref, ME);
check(c1.ok, "the first session to change a value takes the claim");

const c2 = await CL.claim(ref, THEM);
check(!c2.ok && c2.holder.name === ME.name && c2.state === "active",
      "a second session is refused, and told who holds it",
      CL.blockedMessage(c2.holder, c2.state, c2.freeAt));

check(await CL.holdsClaim(ref, ME) === true, "the holder still holds it");

// The race, run for real: N processes attempting the claim at the same instant.
await CL.releaseClaim(ref, ME);
const racer = path.join(tmp, "racer.mjs");
fs.writeFileSync(racer, `
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const CL = require(${JSON.stringify(path.join(ROOT, "src/storage/desktop/claim.js"))});
const r = await CL.claim(process.argv[2], { name: "racer-" + process.argv[3], department: "" });
console.log(r.ok ? "WON" : "lost");
`);
let wins = 0, racers = 8;
const kids = [];
for (let i = 0; i < racers; i++)
  kids.push(new Promise(res => {
    const { spawn } = require("node:child_process");
    const p = spawn(process.execPath, [racer, ref, String(i)]);
    let out = "";
    p.stdout.on("data", d => { out += d; });
    p.on("close", () => res(out.includes("WON")));
  }));
for (const won of await Promise.all(kids)) if (won) wins++;
check(wins === 1,
      "eight processes attempting it together — EXACTLY ONE wins",
      `${wins} winner(s) of ${racers}`);
fs.unlinkSync(CL.lockPath(ref));

/* ---- 7. heartbeat, expiry, and your own crashed session -------------------- */
console.log("\nliveness");
await CL.claim(ref, ME);
const held = await CL.readClaim(ref);
check(CL.statusOf(held) === "active", "a fresh claim is active");

const age = ms => {
  const c = JSON.parse(fs.readFileSync(CL.lockPath(ref), "utf8"));
  c.heartbeat = new Date(Date.now() - ms).toISOString();
  fs.writeFileSync(CL.lockPath(ref), JSON.stringify(c));
};

age(60_000);
check(CL.statusOf(await CL.readClaim(ref)) === "silent",
      "thirty seconds without a heartbeat and it is SILENT — known within half a "
      + "minute, whatever the expiry is (N-23)");
const still = await CL.claim(ref, THEM);
check(!still.ok && still.state === "silent" && still.freeAt,
      "a colleague is told when it frees, not merely that it is held",
      CL.blockedMessage(still.holder, still.state, still.freeAt).slice(0, 96) + "…");

age(31 * 60_000);
check(CL.statusOf(await CL.readClaim(ref)) === "expired", "thirty minutes and it EXPIRES");
const taken = await CL.claim(ref, THEM);
check(taken.ok && taken.displaced.name === ME.name,
      "after which anybody may take it over, naming whose claim they displaced",
      `displaced ${taken.displaced.name}`);

// Your own crashed session, on your own machine.
fs.unlinkSync(CL.lockPath(ref));
await CL.claim(ref, ME);
age(45_000);                                   // silent, nowhere near expired
const mine = await CL.claim(ref, ME);
check(mine.ok && /your own/.test(mine.why || ""),
      "and your OWN stalled session is reclaimable at once — no half-hour wait to get "
      + "back into your own plan (NR-STO-19)", mine.why);

/* ---- 8. the claim is what stands between two people and a lost afternoon --- */
console.log("\nsaving without the claim");
fs.unlinkSync(CL.lockPath(ref));
await CL.claim(ref, THEM);                     // somebody else has it now
let refused = null;
try {
  await WS.saveWorkspace(ref, sheets(99), {}, {
    holdsClaim: r => CL.mayWrite(r, ME), identity: ME });
} catch (e) { refused = e; }
check(refused?.kind === "claim_lost",
      "a save is refused when the claim was displaced beneath it", refused?.message.slice(0, 70) + "…");
check(JSON.parse(fs.readFileSync(ref, "utf8")).sheets.Project.length === 9,
      "and the plan on disk is untouched by the refusal");

// The distinction the smoke test found: a save must ask "does somebody ELSE hold it",
// not "do we hold it". A brand-new plan has no claim at all, and guarding it the wrong
// way refused the first save of every plan ever created.
fs.unlinkSync(CL.lockPath(ref));
const fresh = path.join(tmp, "brand new.prap");
let ok1 = true;
try {
  await WS.saveWorkspace(fresh, sheets(2), {}, { holdsClaim: r => CL.mayWrite(r, ME) });
} catch { ok1 = false; }
check(ok1 && fs.existsSync(fresh),
      "a plan nobody has claimed - a brand-new one - saves without objection");

/* ---- 9. where the data folder goes ---------------------------------------- */
console.log("\nthe data folder");
const appDir = path.join(tmp, "PM_APP");
fs.mkdirSync(appDir, { recursive: true });
const byArg = PA.resolveDataDir({ argv: ["node", "--data=" + tmp], env: {}, appDir });
check(byArg.rule.startsWith("1") && byArg.dir.startsWith(tmp),
      "--data wins, because it is what a personal shortcut carries", byArg.rule);
const byEnv = PA.resolveDataDir({ argv: [], env: { PRAP_DATA: tmp }, appDir });
check(byEnv.rule.startsWith("2"), "then PRAP_DATA", byEnv.rule);
const beside = PA.resolveDataDir({ argv: [], env: {}, appDir });
check(beside.rule.startsWith("3") && beside.dir.includes(path.join("data", "users")),
      "then data\\users\\<account> beside the application — so a shared copy gives "
      + "each person their own without asking (NR-DEP-15)",
      path.relative(appDir, beside.dir));

const asks = PA.resolveDataDir({ argv: [], env: {}, appDir, canWrite: () => false });
check(asks.mustAsk && asks.rule.startsWith("4"),
      "and a read-only folder asks rather than failing at the first Save (NR-DEP-09)",
      asks.rule);

// The real permission check, where the process is not privileged enough to defeat it.
// Running as root - which is how this sandbox runs - accessSync(W_OK) succeeds on a
// directory whose mode forbids writing, so the case is reported as unexercised rather
// than quietly passed.
const readOnlyDir = path.join(tmp, "ro");
fs.mkdirSync(readOnlyDir, { recursive: true });
fs.chmodSync(readOnlyDir, 0o500);
const asRoot = typeof process.getuid === "function" && process.getuid() === 0;
if (asRoot) {
  console.log("  --   the real permission check is NOT exercised here: this process is "
            + "root, and root writes where the mode says it may not. First proven on a "
            + "real machine at N5.6.");
} else {
  check(PA.resolveDataDir({ argv: [], env: {}, appDir: readOnlyDir }).mustAsk,
        "and the real permission check agrees with the injected one");
}
fs.chmodSync(readOnlyDir, 0o700);

const st = PA.addRecent({ recent: [] }, path.join(appDir, "data", "users", "kim", "a.prap"), appDir);
check(!path.isAbsolute(st.recent[0].ref) && st.recent[0].ref.includes("/"),
      "a recent plan inside the folder is remembered RELATIVELY, so copying the folder "
      + "elsewhere does not break the list (NR-DEP-08)", st.recent[0].ref);
const st2 = PA.addRecent({ recent: [] }, path.join(tmp, "elsewhere.prap"), appDir);
check(path.isAbsolute(st2.recent[0].ref),
      "and one outside it is remembered absolutely, because it has to be");

fs.rmSync(tmp, { recursive: true, force: true });
console.log(`\nFAILURES: ${fails.length ? fails.join(", ") : "none"}`);
process.exit(fails.length ? 1 : 0);
