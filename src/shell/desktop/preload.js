/* ============================================================ shell: the bridge
   The only route between the page and the machine.

   contextIsolation is on and nodeIntegration is off (NR-SEC-02), so the renderer -
   which is the web application, unchanged - cannot touch the filesystem. Everything it
   is allowed to do is on this list, and nothing on this list takes a function or a
   path the main process does not check.

   That is what makes it safe to open a workspace somebody else wrote: a crafted file
   is data, and data cannot reach fs from here. */

"use strict";

const { contextBridge, ipcRenderer } = require("electron");

const call = (channel, ...args) => ipcRenderer.invoke(channel, ...args);

contextBridge.exposeInMainWorld("pmapp", {
  /* what this shell can do - ui/ asks rather than assuming (specification sheet 03) */
  capabilities: () => call("caps"),

  /* who is at the keyboard */
  identity: {
    get: () => call("identity:get"),
    set: id => call("identity:set", id),
    suggest: () => call("identity:suggest"),
  },

  /* where things are, and which rule chose it - shown in About (NR-DEP-10) */
  paths: () => call("paths"),

  /* workspaces */
  workspace: {
    open: ref => call("ws:open", ref),
    openDialog: () => call("ws:openDialog"),
    save: (ref, sheets, header) => call("ws:save", ref, sheets, header),
    saveAs: (sheets, header, suggested) => call("ws:saveAs", sheets, header, suggested),
    recent: () => call("ws:recent"),
    versions: ref => call("ws:versions", ref),
    restore: (ref, n) => call("ws:restore", ref, n),
    stat: ref => call("ws:stat", ref),
  },

  /* the write claim - taken on the first DATA CHANGE, not on a click */
  claim: {
    take: ref => call("claim:take", ref),
    read: ref => call("claim:read", ref),
    release: ref => call("claim:release", ref),
    holds: ref => call("claim:holds", ref),
  },

  /* pending edits, kept apart from the committed workspace */
  journal: {
    write: (ref, pending) => call("journal:write", ref, pending),
    read: ref => call("journal:read", ref),
    clear: ref => call("journal:clear", ref),
  },

  /* import and export - NR-IMP-05 opens a source file with no workspace at all */
  file: {
    openSource: () => call("file:openSource"),
    export: (bytes, suggested) => call("file:export", bytes, suggested),
  },

  /* one-way notices from the main process: menu commands, and the heartbeat tick */
  on: (event, fn) => {
    const allowed = new Set(["menu", "claim:lost", "tick"]);
    if (!allowed.has(event)) return;
    ipcRenderer.on(event, (_e, payload) => fn(payload));
  },
});
