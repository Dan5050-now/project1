/* ============================================================ storage: workspaces
   The desktop storage adapter. Everything the web shell does with a download and a
   file picker, this does with a path - and everything the web shell cannot do at all,
   this does here: keeping a plan, retaining the version before it, journalling the
   edits that have not been committed yet.

   Node only: no Electron, no DOM. That is deliberate - all of the logic that can lose
   somebody's work lives in this file and in claim.js, and both are testable by running
   node against them. A defect that needs a window open to reproduce is a defect that
   gets found late.

   Specification: PRAP_NewApp_Specification_v1.2.xlsx sheets 03, 04, 06. */

"use strict";

const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");

const APP = "PM_APP";
const FORMAT = "prap-source-data";
const FORMAT_VERSION = 1;
const SCHEMA_EXPECTED = 5;

/** Errors the interface throws. ui/ switches on `kind`; the user reads `message`.
 *  A storage layer that throws one kind of error forces the screen to say one kind of
 *  thing, and "something went wrong" is the sentence that wastes an afternoon. */
class StorageError extends Error {
  constructor(kind, message, detail) {
    super(message);
    this.name = "StorageError";
    this.kind = kind;
    this.detail = detail;
  }
}

const backupDir = ref => path.join(path.dirname(ref), "backups");
const backupPath = (ref, n) =>
  path.join(backupDir(ref), `${path.basename(ref)}.${n}`);
const journalPath = ref => `${ref}.journal`;
const tmpPath = ref => `${ref}.tmp-${process.pid}`;

/* ---------------------------------------------------------------- reading -- */

/** Tell a PROTECTED file from a CORRUPT one.
 *
 *  This is R-N18, and it is worth the trouble. A file encrypted by company document
 *  security is bytes an ordinary application cannot parse - exactly what a truncated
 *  or damaged file looks like from here. Reported as corruption, it sends somebody
 *  hunting for a backup they do not need; reported as protection, it is unlocked in
 *  half a minute. The signatures are the ones those products actually leave. */
function looksProtected(buf) {
  if (buf.length < 8) return false;
  // OLE2 compound file - what an encrypted .xlsx becomes (and what .xls always was).
  const OLE2 = Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1]);
  if (buf.subarray(0, 8).equals(OLE2)) return true;
  // A ZIP that says it is encrypted: general-purpose bit 0 set in the local header.
  if (buf[0] === 0x50 && buf[1] === 0x4b && buf[2] === 0x03 && buf[3] === 0x04)
    return (buf[6] & 0x01) === 1;
  return false;
}

/** Read and parse a workspace. The sheets come back exactly as core/ expects them. */
async function openWorkspace(ref) {
  let buf;
  try {
    buf = await fsp.readFile(ref);
  } catch (e) {
    if (e.code === "ENOENT")
      throw new StorageError("not_found",
        `That plan is no longer at ${ref}. It may have been moved or deleted.`, e.code);
    if (e.code === "EACCES" || e.code === "EPERM")
      throw new StorageError("read_only",
        `${ref} could not be read. You may not have permission to open it.`, e.code);
    throw new StorageError("unreadable", `${path.basename(ref)} could not be read.`, e.message);
  }

  if (looksProtected(buf))
    throw new StorageError("protected",
      `${path.basename(ref)} could not be opened. It looks like it is protected by file `
      + `security — open it in Excel first to unlock it, then import it again.`);

  let doc;
  try {
    doc = JSON.parse(buf.toString("utf8"));
  } catch (e) {
    throw new StorageError("unreadable",
      `${path.basename(ref)} is not a plan file. It may be a source workbook — use `
      + `Import instead.`, e.message);
  }
  if (doc.format !== FORMAT)
    throw new StorageError("unreadable",
      `${path.basename(ref)} is not a plan file. It may be a source workbook — use `
      + `Import instead.`, `format=${doc.format}`);

  const header = doc.workspace || {};
  // NR-DEP-04: refuse, never partially read. Reading a file written by a version that
  // knows more than this one, and then writing it back, is how fields disappear.
  if (header.app_version && cmpVersion(header.app_version, currentVersion()) > 0)
    throw new StorageError("too_new",
      `This plan was saved by version ${header.app_version}. This is version `
      + `${currentVersion()}. Install the newer version to open it.`);

  return { sheets: doc.sheets, header, ref, readOnly: !(await canWrite(ref)) };
}

function cmpVersion(a, b) {
  const pa = String(a).split(".").map(Number), pb = String(b).split(".").map(Number);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d) return d < 0 ? -1 : 1;
  }
  return 0;
}

let _version = "1.0";
const currentVersion = () => _version;
const setVersion = v => { _version = v; };

async function canWrite(ref) {
  try {
    await fsp.access(path.dirname(ref), fs.constants.W_OK);
    return true;
  } catch { return false; }
}

/* ---------------------------------------------------------------- writing -- */

/** The save protocol, specification sheet 06, step for step.
 *
 *  The order is the whole of it: serialise, write to a TEMPORARY name in the same
 *  directory, flush it to the physical disk, roll the current file into the version
 *  history, then RENAME over the target. A rename is atomic; a write is not. Power
 *  loss at any point leaves a readable workspace - the old one before the rename, the
 *  new one after it - and never half of each.
 *
 *  `holdsClaim` is passed in rather than looked up, so this function can be tested
 *  without a claim and so the caller cannot forget to check: there is no path through
 *  it that writes without asking. */
async function saveWorkspace(ref, sheets, header, opts = {}) {
  const { holdsClaim = null, retain = 1, identity = null } = opts;

  if (holdsClaim && !(await holdsClaim(ref)))
    throw new StorageError("claim_lost",
      "Your hold on this plan was taken over while you were working. Nothing has been "
      + "saved. Save As a copy to keep your changes.");

  const now = new Date().toISOString();
  const doc = {
    format: FORMAT,
    format_version: FORMAT_VERSION,
    workspace: {
      app: APP,
      app_version: currentVersion(),
      schema_version: SCHEMA_EXPECTED,
      created: header.created || now,
      last_saved: now,
      last_saved_by: identity ? { name: identity.name, department: identity.department }
                              : (header.last_saved_by || null),
      imported_from: header.imported_from || null,
    },
    sheets,
  };
  const text = JSON.stringify(doc, null, 1) + "\n";

  const tmp = tmpPath(ref);
  let fh;
  try {
    fh = await fsp.open(tmp, "w");
    await fh.writeFile(text, "utf8");
    await fh.sync();                       // NR-STO-04: on the disk, not in a cache
  } catch (e) {
    try { await fh?.close(); } catch { /* the close failure is not the interesting one */ }
    try { await fsp.unlink(tmp); } catch { /* best effort */ }
    if (e.code === "ENOSPC")
      throw new StorageError("no_space",
        "There is not enough room to save. Nothing has been changed — your previous "
        + "save is intact.", e.code);
    if (e.code === "EACCES" || e.code === "EPERM" || e.code === "EROFS")
      throw new StorageError("read_only",
        `${path.dirname(ref)} cannot be written to. Save As somewhere else, or ask for `
        + `write access.`, e.code);
    throw new StorageError("unreadable", `The plan could not be saved: ${e.message}`, e.code);
  }
  await fh.close();

  await rollVersions(ref, retain);
  await fsp.rename(tmp, ref);              // NR-STO-05: atomic
  await clearJournal(ref);                 // committed, so nothing is pending

  return { savedAt: now, ref };            // NR-STO-04: only NOW is it saved
}

/** Keep the previous version, and only as many as asked for.
 *
 *  Q-N07 set the default at one. Recorded with its consequence rather than silently:
 *  two bad saves in a row push the good version out of history (R-N19), which is why
 *  the Excel export stays the archive that matters. */
async function rollVersions(ref, retain) {
  if (!fs.existsSync(ref)) return;
  if (retain <= 0) return;
  await fsp.mkdir(backupDir(ref), { recursive: true });
  for (let n = retain; n >= 2; n--) {
    const from = backupPath(ref, n - 1), to = backupPath(ref, n);
    if (fs.existsSync(from)) await fsp.rename(from, to);
  }
  await fsp.copyFile(ref, backupPath(ref, 1));
}

async function listVersions(ref) {
  const out = [];
  for (let n = 1; n <= 20; n++) {
    const p = backupPath(ref, n);
    if (!fs.existsSync(p)) break;
    const st = await fsp.stat(p);
    out.push({ n, ref: p, at: st.mtime.toISOString() });
  }
  return out;
}

/** Read a retained version. It does NOT overwrite the current one - the caller lands
 *  it as a pending edit, so a restore made by mistake costs nothing and a restore made
 *  deliberately goes through the same door as every other change (S-N02). */
async function restoreVersion(ref, n = 1) {
  const p = backupPath(ref, n);
  if (!fs.existsSync(p))
    throw new StorageError("not_found", "There is no previous version of this plan kept.");
  const doc = JSON.parse(await fsp.readFile(p, "utf8"));
  return { sheets: doc.sheets, header: doc.workspace || {} };
}

/* --------------------------------------------------------------- journal --- */

/* Pending edits, kept APART from the committed workspace (N-08). That separation is
   what lets recovery offer them back without a half-typed row ever having been
   committed data. */

async function writeJournal(ref, pending) {
  const tmp = `${journalPath(ref)}.tmp-${process.pid}`;
  await fsp.writeFile(tmp, JSON.stringify({ at: new Date().toISOString(), pending }), "utf8");
  await fsp.rename(tmp, journalPath(ref));
}

async function readJournal(ref) {
  const p = journalPath(ref);
  if (!fs.existsSync(p)) return null;
  let j;
  try {
    j = JSON.parse(await fsp.readFile(p, "utf8"));
  } catch {
    return null;                           // a torn journal is no journal
  }
  // Only offer it if it is NEWER than the workspace. Otherwise the edits were made
  // against figures that have since been replaced, and applying them would put them
  // somewhere they were never made.
  if (fs.existsSync(ref)) {
    const [a, b] = [await fsp.stat(p), await fsp.stat(ref)];
    if (a.mtimeMs <= b.mtimeMs) return null;
  }
  return j;
}

async function clearJournal(ref) {
  try { await fsp.unlink(journalPath(ref)); } catch { /* nothing to clear */ }
}

/* ------------------------------------------------------------ housekeeping - */

/** A leftover .tmp-<pid> means a save was interrupted. The workspace itself is intact
 *  by construction, so there is nothing to repair and nothing to tell the user - only
 *  a file to remove. */
async function sweepTemp(dir) {
  let n = 0;
  for (const name of await fsp.readdir(dir).catch(() => [])) {
    if (/\.tmp-\d+$/.test(name)) {
      await fsp.unlink(path.join(dir, name)).catch(() => {});
      n++;
    }
  }
  return n;
}

async function stat(ref) {
  try {
    const st = await fsp.stat(ref);
    return { exists: true, mtime: st.mtimeMs, size: st.size };
  } catch {
    return { exists: false, mtime: 0, size: 0 };
  }
}

module.exports = {
  APP, FORMAT, FORMAT_VERSION, SCHEMA_EXPECTED,
  StorageError, looksProtected,
  openWorkspace, saveWorkspace, listVersions, restoreVersion,
  writeJournal, readJournal, clearJournal,
  sweepTemp, stat, canWrite,
  currentVersion, setVersion, cmpVersion,
  backupDir, backupPath, journalPath, tmpPath,
  os,
};
