/* ================================================================ storage: claim
   One writer at a time. Any number of readers. Nobody is ever blocked from LOOKING.

   The claim is taken when a data value actually changes - not when the plan is opened,
   and not when somebody clicks into a cell. That distinction is the whole reason this
   file exists rather than a lock: a claim taken on open would let somebody who glanced
   at a plan and went to lunch block the team for half an hour.

   Specification: PRAP_NewApp_Specification_v1.2.xlsx sheet 07.
   Node only, so the race can be tested by running two processes rather than two
   windows. */

"use strict";

const fs = require("node:fs");
const fsp = require("node:fs/promises");
const os = require("node:os");

const HEARTBEAT_MS = 30_000;               // "is the holder alive?"      - N-23
const EXPIRY_MS = 30 * 60_000;             // "may somebody else take it?" - Q-N16

const lockPath = ref => `${ref}.lock`;

/** Two different questions, two different numbers.
 *
 *  Keeping them apart is what makes a half-hour expiry comfortable rather than opaque:
 *  the application knows within thirty seconds that a holder has gone quiet, long
 *  before anyone may act on it, so it can say WHICH - a colleague mid-sentence, or one
 *  whose laptop died twenty minutes ago. One message for both would be useless. */
function statusOf(claim, now = Date.now()) {
  if (!claim) return "free";
  const beat = Date.parse(claim.heartbeat || claim.since || 0);
  const quiet = now - beat;
  if (quiet > EXPIRY_MS) return "expired";
  if (quiet > HEARTBEAT_MS) return "silent";
  return "active";
}

const isMine = (claim, identity) =>
  !!claim && claim.name === identity.name && claim.machine === machine();

const machine = () => os.hostname();

async function readClaim(ref) {
  const p = lockPath(ref);
  for (let attempt = 0; attempt < 2; attempt++) {
    if (!fs.existsSync(p)) return null;
    try {
      return JSON.parse(await fsp.readFile(p, "utf8"));
    } catch {
      // A torn read of a file being rewritten by its holder's heartbeat is possible,
      // especially on a share. Reading twice costs nothing and avoids reporting a
      // live holder as an unreadable one.
      await new Promise(r => setTimeout(r, attempt === 0 ? 200 : 0));
    }
  }
  return { name: "(unknown)", department: "", machine: "", since: null,
           heartbeat: new Date().toISOString(), unreadable: true };
}

/** Take the claim, or report who holds it.
 *
 *  The claim is made with an exclusive create - 'wx' - which FAILS if the file already
 *  exists. Not read-then-write: two sessions can both read "free" and both then write
 *  one, and each would believe it had won. Exclusive create is decided by the
 *  filesystem, has exactly one winner, and works over SMB. */
async function claim(ref, identity, opts = {}) {
  const { now = Date.now() } = opts;
  const body = {
    name: identity.name,
    department: identity.department || "",
    machine: machine(),
    pid: process.pid,
    since: new Date(now).toISOString(),
    heartbeat: new Date(now).toISOString(),
    app_version: opts.appVersion || "1.0",
  };

  try {
    const fh = await fsp.open(lockPath(ref), "wx");
    await fh.writeFile(JSON.stringify(body), "utf8");
    await fh.close();
    return { ok: true, claim: body };
  } catch (e) {
    if (e.code !== "EEXIST") throw e;
  }

  // Somebody has it. Whether we may take it over depends on WHO and HOW LONG.
  const held = await readClaim(ref);
  const state = statusOf(held, now);

  // Your own crashed session, on your own machine: back at once. Thirty minutes locked
  // out of somebody else's plan is a policy; thirty minutes locked out of your OWN is
  // an obstruction (N-24).
  if (isMine(held, identity) && state !== "active")
    return takeOver(ref, body, held, "your own earlier session");

  if (state === "expired")
    return takeOver(ref, body, held, "an expired claim");

  return { ok: false, holder: held, state, freeAt: freeAt(held) };
}

function freeAt(claim) {
  const beat = Date.parse(claim?.heartbeat || claim?.since || 0);
  return beat ? new Date(beat + EXPIRY_MS).toISOString() : null;
}

async function takeOver(ref, body, previous, why) {
  body.displaced = { name: previous?.name ?? null, why };
  await fsp.writeFile(lockPath(ref), JSON.stringify(body), "utf8");
  return { ok: true, claim: body, displaced: previous, why };
}

/** The heartbeat. Rewrites the time inside the claim, and NOTHING else - if the claim
 *  is no longer ours we stop rather than stamping our name over somebody else's. */
async function refreshClaim(ref, identity) {
  const held = await readClaim(ref);
  if (!held || held.name !== identity.name || held.machine !== machine() ||
      held.pid !== process.pid)
    return { ok: false, holder: held };
  held.heartbeat = new Date().toISOString();
  await fsp.writeFile(lockPath(ref), JSON.stringify(held), "utf8");
  return { ok: true };
}

/** Released on save-and-close, on discard, and on application close - NOT on save
 *  alone, which would hand the plan to somebody else mid-task (N-22). */
async function releaseClaim(ref, identity) {
  const held = await readClaim(ref);
  if (held && (held.name !== identity.name || held.machine !== machine() ||
               held.pid !== process.pid))
    return { ok: false, holder: held };
  try { await fsp.unlink(lockPath(ref)); } catch { /* already gone */ }
  return { ok: true };
}

/** Does THIS session hold the claim? Used for what the window shows. */
async function holdsClaim(ref, identity) {
  const held = await readClaim(ref);
  return !!held && held.name === identity.name && held.machine === machine()
         && held.pid === process.pid;
}

/** May this session WRITE to this plan? The guard before every save, and it is NOT the
 *  same question as holdsClaim.
 *
 *  Found by the smoke test: a brand-new plan has no claim on it, because the claim is
 *  taken when a value changes in an OPEN workspace and a plan being created was never
 *  opened. Guarding the save with "do we hold it" refused the very first save of every
 *  new plan - which would have been discovered by the first person to make one.
 *
 *  The question a save actually has to ask is whether somebody ELSE holds it: ours is
 *  fine, nobody's is fine, and theirs is the one case that must stop. */
async function mayWrite(ref, identity) {
  const held = await readClaim(ref);
  if (!held) return true;                          // nobody has it
  if (held.name === identity.name && held.machine === machine()) return true;
  return statusOf(held) === "expired";             // theirs, but long dead
}

/** What a blocked colleague is told. The words are specified, so they live here rather
 *  than being invented at the screen: a message that names somebody and says when the
 *  plan frees is actionable, and "file in use" is not. */
function blockedMessage(holder, state, free) {
  const who = holder.department ? `${holder.name} (${holder.department})` : holder.name;
  const t = s => s ? new Date(s).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                   : "an unknown time";
  if (state === "active")
    return `${who} is editing this plan. Started ${t(holder.since)}, active now.`;
  if (state === "silent")
    return `${who} has been editing this plan since ${t(holder.since)}, but their `
         + `session has not responded since ${t(holder.heartbeat)}. The plan becomes `
         + `free at ${t(free)}.`;
  return `${holder.name}'s session stopped responding at ${t(holder.heartbeat)} and no `
       + `longer holds this plan. You may take over.`;
}

module.exports = {
  HEARTBEAT_MS, EXPIRY_MS,
  lockPath, readClaim, claim, refreshClaim, releaseClaim, holdsClaim, mayWrite,
  statusOf, isMine, freeAt, blockedMessage, machine,
};
