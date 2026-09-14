"""shell: the local server - what Electron's main process used to be.

The page is the web application, unchanged: the same core/, the same ui/, the same
figures. What changed is what sits underneath it. Electron gave the page a preload
bridge over IPC; this gives it the same operations over HTTP on 127.0.0.1. The list
is identical, deliberately - specification sheet 03 defines it, and neither shell
may quietly grow an operation the other does not have.

    page  --fetch-->  127.0.0.1:<port>/api/...  -->  storage/python  -->  disk

WHY THIS IS SAFE, WHICH IS A FAIR QUESTION TO ASK OF A PROGRAM THAT OPENS A SOCKET
ON A COMPANY LAPTOP. This is a divergence from NR-SEC-01, which said the shell opens
no socket, so it is answered rather than waved past:

  * it listens on 127.0.0.1 only, never on the network interface. Nothing outside
    the machine can reach it, and Windows Firewall does not prompt for loopback.
  * the port is chosen by the operating system at start, not fixed.
  * every request must carry a 32-byte key generated at start and never written to
    disk. Another program on the machine cannot guess it, and another WEB PAGE
    cannot read it - it lives in this page's own DOM, which same-origin policy keeps
    to itself.
  * the Host header must be a loopback address, which is what stops a hostile site
    resolving its own name to 127.0.0.1 and talking to us in the user's browser.
  * a cross-site request is refused outright: no CORS header is ever sent, and any
    Origin or Sec-Fetch-Site that is not our own is rejected before it reaches an
    operation.
  * it serves exactly one page and one API. There is no path that maps a URL to a
    file on disk, so there is nothing to escape from with "..".

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheets 03, 05, 06, 07, 10.
"""

import base64
import json
import os
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import files as F
from . import paths as PA
from ..storage import claim as CL
from ..storage import workspace as WS

LOOPBACK = ("127.0.0.1", "localhost", "[::1]", "::1")


class App:
    """Everything one running application knows. One instance, one window's worth."""

    def __init__(self, app_dir=None, data_dir=None, version="1.0", page=None):
        self.app_dir = app_dir or PA.default_app_dir()
        self.version = version
        WS.set_version(version)
        self.page = page                      # the built index.html, as text
        self.key = secrets.token_urlsafe(32)
        self.data_dir = data_dir
        # Settled with data_dir; declared here so the audit operations can ask for it
        # before the folder has been resolved, which happens when resolution has to
        # stop and ask the user where to put it.
        self.data_root = None
        self.resolved = {}
        self.settings = dict(PA.DEFAULT_SETTINGS)
        self.open_ref = None
        self.dialogs = F.DialogPump()
        self.stop = threading.Event()
        self._heartbeat = None
        # The beat's OWN stop, not the application's. Setting _heartbeat to None
        # did not end the thread: it waited on the application-wide event, so a
        # beat started for one plan went on refreshing THAT plan's claim after
        # the session had moved to another one - and the first plan stayed
        # claimed until its half-hour expiry, with nobody holding it (NR-STO-15).
        self._beat_stop = None
        self._lock = threading.RLock()
        self.claim_lost = None                # set when a heartbeat finds it gone
        # WHO IS ACTUALLY LOOKING AT IT (NR-DEP-17). page id -> last seen, monotonic.
        # The console window is the application; the browser is its window. Closing the
        # window and leaving the application running is not something anybody asked for,
        # and the console then sits there owning a port and a claim on a plan nobody has
        # open. See watch_clients() for how the two are told apart.
        self.clients = {}
        self.ever_seen = False
        self.keep_running = False             # --keep-running, for a headless run

    # -------------------------------------------------------------- start-up

    def settle_data_dir(self, chosen=None):
        r = PA.resolve_data_dir(app_dir=self.app_dir)
        if r["mustAsk"]:
            if chosen:
                r["dir"] = os.path.join(chosen, "users", r["account"])
                r["rule"] = "4 - chosen by you"
                r["mustAsk"] = False
            else:
                self.resolved = r
                return r
        # The installation root first, because the shared folder is created beside
        # users/ and ensure() needs to be told where that is.
        self.data_root = r.get("root") or os.path.dirname(os.path.dirname(r["dir"]))
        self.data_dir = PA.ensure(r["dir"], self.data_root)
        r["dir"] = self.data_dir
        # The change log lives at the root so everyone's entries are in one folder.
        self.resolved = r
        WS.sweep_temp(self.data_dir)          # an interrupted save left a .tmp
        WS.sweep_temp(os.path.join(self.data_dir, "workspaces"))
        self.settings = PA.read_settings(self.data_dir)
        return r

    # -------------------------------------------------------------- identity

    def identity(self):
        return self.settings.get("identity") or {"name": PA.account_name(),
                                                 "department": ""}

    def save_settings(self):
        if self.data_dir:
            PA.write_settings(self.data_dir, self.settings)

    # ------------------------------------------------------------- heartbeat

    def start_heartbeat(self, ref):
        """Thirty seconds, whatever the expiry is. Keeping the two apart is what
        lets the application tell a colleague mid-sentence from one whose laptop
        died twenty minutes ago, and say which (N-23)."""
        self.stop_heartbeat()
        self.claim_lost = None
        stop = threading.Event()          # this beat's own; see _beat_stop above

        def beat():
            while not self.stop.is_set():
                # Waiting on the BEAT's event rather than the application's is what
                # lets stop_heartbeat() end it at once instead of up to thirty
                # seconds later.
                if stop.wait(CL.HEARTBEAT_MS / 1000.0):
                    return
                if self.stop.is_set():
                    return
                try:
                    r = CL.refresh_claim(ref, self.identity())
                except OSError:
                    r = {"ok": False, "holder": None}
                if not r.get("ok"):
                    self.claim_lost = r.get("holder")
                    return

        self._beat_stop = stop
        self._heartbeat = threading.Thread(target=beat, daemon=True,
                                           name="pm-heartbeat")
        self._heartbeat.start()

    def stop_heartbeat(self):
        """Actually stop it, rather than forgetting about it."""
        beat_stop, self._beat_stop, self._heartbeat = self._beat_stop, None, None
        if beat_stop is not None:
            beat_stop.set()

    def release_open_claim(self):
        """Give the plan this session holds back, and stop beating for it.

        NR-STO-15 ends a claim when the holder saves and closes, discards, or closes
        the application. Moving to ANOTHER plan is the first of those in everything
        but name - the session is finished with the old one - and until this existed
        the old plan stayed claimed for half an hour after the person had left it.
        release_claim() checks ownership itself, so this is safe to call when the
        claim is somebody else's or already gone."""
        self.stop_heartbeat()
        ref, self.open_ref = self.open_ref, None
        if not ref:
            return None
        try:
            return CL.release_claim(ref, self.identity())
        except OSError:
            return None

    # --------------------------------------------------- who has the page open

    def client_here(self, cid):
        """A page saying it is still there. Also the first thing it ever says."""
        if not cid:
            return
        with self._lock:
            self.clients[str(cid)] = time.monotonic()
            self.ever_seen = True

    def client_gone(self, cid):
        """A page saying it is closing. Sent from pagehide, which fires on a RELOAD
        as well as on a close - the two are indistinguishable at this moment, and
        that is what GRACE below is for."""
        with self._lock:
            self.clients.pop(str(cid), None)

    def watch_clients(self, grace=4.0, stale=900.0, tick=0.5):
        """Stop when the last page has gone, and not before.

        TWO SIGNALS, BECAUSE NEITHER IS ENOUGH ON ITS OWN.

        THE CLOSE MESSAGE is the one that matters and the one that is quick: the page
        sends it from pagehide, so clicking the browser's X stops this in about
        `grace` seconds. It is not trusted immediately, because pagehide fires on a
        RELOAD too, and a reload that killed the application would make F5 a way of
        losing your work. `grace` is the window a reloading page has to say hello
        again; it only has to survive one page load.

        THE HEARTBEAT is the backstop, for the times no close message arrives - the
        browser was killed, the machine slept, the process was taken down. It is
        deliberately SLOW to give up: `stale` is fifteen minutes. A browser throttles
        timers in a tab nobody is looking at, hard, and can freeze one altogether for
        minutes at a time - so a short timeout here would quietly shut the application
        down on somebody who had left it open in a background tab, which is worse than
        the console outliving the window by a quarter of an hour on the rare occasion
        the browser dies without a word.

        NOTHING HAPPENS BEFORE THE FIRST PAGE CONNECTS. A slow browser, a machine that
        opens the URL by hand, `--no-browser` for the tests: none of those should be a
        countdown to shutting down."""
        if self.keep_running:
            return
        empty_since = None
        while not self.stop.wait(tick):
            now = time.monotonic()
            with self._lock:
                for cid, seen in list(self.clients.items()):
                    if now - seen > stale:
                        self.clients.pop(cid, None)
                live = len(self.clients)
                started = self.ever_seen
            if not started or live:
                empty_since = None
                continue
            if empty_since is None:
                empty_since = now
            elif now - empty_since >= grace:
                print("\nThe application's page was closed, so it is stopping. "
                      "Run PM_APP again to carry on.")
                self.shutdown()
                return

    def shutdown(self):
        # The claim goes on the way out - NOT on save alone, which would hand the
        # plan to somebody else mid-task (N-22).
        if self.open_ref:
            try:
                CL.release_claim(self.open_ref, self.identity())
            except OSError:
                pass
        try:
            self.save_settings()
        except OSError:
            pass
        self.stop.set()


# ---------------------------------------------------------------- the operations

def operations(app):
    """The thirteen operations of specification sheet 03, plus the four this shell
    needs that Electron got from its own dialogs. Each takes a decoded JSON body and
    returns something JSON can carry."""

    def full(ref):
        return PA.from_portable(ref, app.app_dir)

    def caps(_):
        return {"workspaces": True, "versions": True, "claims": True, "journal": True,
                "shell": "python", "nativeDialogs": app.dialogs.enabled,
                "browse": True, "upload": False}

    def paths(_):
        return {"appDir": app.app_dir, "dataDir": app.data_dir,
                "version": app.version, "rule": app.resolved.get("rule"),
                "account": PA.account_name(),
                "workspaces": os.path.join(app.data_dir or "", "workspaces"),
                # Where plans the team edits together live. The page offers it as a
                # place to open from and save to, because a claim on a plan inside one
                # person's folder protects nothing (NR-STO-10).
                "shared": (os.path.join(PA.shared_dir(app.data_root), "workspaces")
                           if app.data_root else None)}

    # ---- identity -------------------------------------------------------
    def identity_get(_):
        return app.settings.get("identity")

    def identity_suggest(_):
        return {"name": PA.account_name(), "department": ""}

    def identity_set(b):
        app.settings["identity"] = {
            "name": str((b.get("identity") or {}).get("name") or "").strip(),
            "department": str((b.get("identity") or {}).get("department") or "").strip()}
        app.save_settings()
        return app.settings["identity"]

    # ---- workspaces -----------------------------------------------------
    def ws_open(b):
        p = full(b["ref"])
        # Opening another plan finishes with this one, so its claim goes back now
        # rather than at its expiry (NR-STO-15).
        if app.open_ref and os.path.abspath(app.open_ref) != os.path.abspath(p):
            app.release_open_claim()
        out = WS.open_workspace(p)
        app.open_ref = p
        app.settings = PA.add_recent(app.settings, p, app.app_dir,
                                     {"savedBy": out["header"].get("last_saved_by")})
        app.save_settings()
        return out

    def ws_shared_state(b):
        """Is the open plan somewhere the sharing rules can actually work?

        A claim on a plan inside one person's folder protects nothing (NR-STO-10), so
        the page needs to be able to say so - and to say it at the moment it matters
        rather than in a note nobody opens. This answers three things and judges none
        of them; the page decides what is worth saying.
        """
        ref = b.get("ref") or app.open_ref
        shared = (os.path.join(PA.shared_dir(app.data_root), "workspaces")
                  if app.data_root else None)
        if not ref or not shared:
            return {"private": False, "shared": shared, "target": None}
        ref = os.path.abspath(full(ref))
        mine = os.path.abspath(os.path.join(app.data_dir or "", "workspaces"))
        private = os.path.dirname(ref) == mine
        target = os.path.join(shared, os.path.basename(ref)) if private else None
        return {"private": private, "shared": shared, "target": target,
                "taken": bool(target and os.path.exists(target))}

    def ws_move_to_shared(b):
        """Move the open plan into the folder the whole team can reach.

        The claim goes back first. It names a machine and a process against a PATH,
        and the path is about to change - and releasing it is also what lets anybody
        who was blocked find out, without them reopening anything (NR-STO-15).
        """
        if not app.data_root:
            raise WS.StorageError("noshared", "There is no team folder on this "
                                              "installation.")
        src = os.path.abspath(full(b["ref"]))
        dst = os.path.join(PA.shared_dir(app.data_root), "workspaces",
                           os.path.basename(src))
        if app.open_ref and os.path.abspath(app.open_ref) == src:
            app.release_open_claim()
        out = WS.move_plan(src, dst)
        app.open_ref = out["ref"]
        app.settings = PA.add_recent(app.settings, out["ref"], app.app_dir)
        app.save_settings()
        return out

    def ws_open_dialog(_):
        return app.dialogs.ask("open", title="Open a plan",
                               initialdir=os.path.join(app.data_dir or "", "workspaces"),
                               filetypes=[("Plans", "*.prap"), ("All files", "*.*")])

    def ws_save(b):
        p = full(b["ref"])
        out = WS.save_workspace(
            p, b["sheets"], b.get("header") or {},
            holds_claim=lambda r: CL.may_write(r, app.identity()),
            retain=app.settings.get("preferences", {}).get("retain_versions", 1),
            identity=app.identity(),
            # Which issue of the file the page's figures came from, so a save cannot
            # land on top of a newer one (NR-STO-16). Absent for a caller that
            # cannot say - a plan being created has no previous issue.
            base_saved=b.get("baseSaved"))
        app.open_ref = p
        app.settings = PA.add_recent(app.settings, p, app.app_dir,
                                     {"savedBy": app.identity()})
        app.save_settings()
        return out

    def ws_save_as(b):
        p = b.get("ref")
        if not p:
            p = app.dialogs.ask("save", title="Save the plan as",
                                initialdir=os.path.join(app.data_dir or "", "workspaces"),
                                initialfile=b.get("suggested") or "Untitled.prap",
                                defaultextension=".prap",
                                filetypes=[("Plans", "*.prap")])
        if not p:
            return None
        if not os.path.splitext(p)[1]:
            p += ".prap"
        # The dialog above ran without the lock; everything that touches shared
        # state is inside it.
        with app._lock:
            out = WS.save_workspace(p, b["sheets"], b.get("header") or {},
                                    retain=1, identity=app.identity())
            app.open_ref = out["ref"]
            app.settings = PA.add_recent(app.settings, out["ref"], app.app_dir,
                                         {"savedBy": app.identity()})
            app.save_settings()
        return out

    def ws_recent(_):
        # NR-STO-12 / U-N01: say "held by" BEFORE the plan is opened, not after. One
        # small read per entry, which the reviewer agreed is worth it.
        out = []
        for r in app.settings.get("recent") or []:
            p = full(r["ref"])
            held = None
            try:
                held = CL.read_claim(p)
            except OSError:
                pass
            out.append({**r, "full": p, "exists": os.path.exists(p),
                        "heldBy": ({"name": held.get("name"),
                                    "department": held.get("department"),
                                    "state": CL.status_of(held)} if held else None)})
        return out

    def ws_versions(b):
        return WS.list_versions(full(b["ref"]))

    def ws_restore(b):
        return WS.restore_version(full(b["ref"]), b.get("n", 1))

    def ws_stat(b):
        p = full(b["ref"])
        out = dict(WS.stat(p))
        # What the file says about ITSELF, which is what a staleness check can trust;
        # the modification time beside it is only the cheap hint that something moved.
        out["lastSaved"] = WS.last_saved_of(p)
        return out

    # ---- the claim ------------------------------------------------------
    def claim_take(b):
        p = full(b["ref"])
        # Same rule from the other side: a claim on a new plan gives up the old one.
        if app.open_ref and os.path.abspath(app.open_ref) != os.path.abspath(p):
            app.release_open_claim()
        r = CL.claim(p, app.identity(), app_version=app.version)
        if r.get("ok"):
            app.open_ref = p
            app.start_heartbeat(p)
        return r

    def claim_read(b):
        held = CL.read_claim(full(b["ref"]))
        if not held:
            return None
        state = CL.status_of(held)
        return {"holder": held, "state": state, "freeAt": CL.free_at(held),
                "message": CL.blocked_message(held, state, CL.free_at(held))}

    def claim_release(b):
        p = full(b["ref"])
        app.stop_heartbeat()
        r = CL.release_claim(p, app.identity())
        # So the claim is not chased again on the way out, and so holds_claim() and
        # the window agree about what this session is holding.
        if app.open_ref and os.path.abspath(app.open_ref) == os.path.abspath(p):
            app.open_ref = None
        return r

    def claim_holds(b):
        # Also the moment the page learns a heartbeat lost the claim, which is how
        # this shell replaces Electron's push notification without a second channel.
        return {"holds": CL.holds_claim(full(b["ref"]), app.identity()),
                "lost": app.claim_lost}

    # ---- the journal ----------------------------------------------------
    def journal_write(b):
        return WS.write_journal(full(b["ref"]), b.get("pending"))

    def journal_read(b):
        return WS.read_journal(full(b["ref"]))

    def journal_clear(b):
        return WS.clear_journal(full(b["ref"]))

    # ---- files: the whole point of this shell ---------------------------
    def file_open_source(b):
        """Read a source workbook and hand the bytes to the page.

        THIS is the operation R-N21 made necessary. The page does not open the file
        and never sees a browser file interface; Python opens it, and what crosses
        into the page is ordinary page content from its own origin.
        """
        p = b.get("path")
        if not p:
            p = app.dialogs.ask("open", title="Choose source data",
                                initialdir=b.get("initialdir"),
                                filetypes=[("Source data", "*.xlsx *.json"),
                                           ("Excel workbook", "*.xlsx"),
                                           ("Interchange file", "*.json"),
                                           ("All files", "*.*")])
        if not p:
            return None
        p = os.path.abspath(os.path.expanduser(p))
        buf = WS.read_bytes(p)
        if WS.looks_protected(buf):
            raise WS.StorageError(
                "protected",
                f"{os.path.basename(p)} could not be opened. It looks like it is "
                f"protected by file security - open it in Excel first to unlock it, "
                f"then import it again.")
        return {"name": os.path.basename(p), "path": p, "size": len(buf),
                "bytes": base64.b64encode(buf).decode("ascii")}

    def file_export(b):
        """Write bytes the page produced to a file the user chose.

        The browser's own download still works and is left in place - a download is
        not an upload, and R-N21 does not touch it. This is here so an export can
        land beside the plan instead of in the Downloads folder.
        """
        p = b.get("path")
        if not p:
            p = app.dialogs.ask("save", title="Export",
                                initialdir=app.data_dir,
                                initialfile=b.get("suggested") or "export.xlsx")
        if not p:
            return None
        p = os.path.abspath(os.path.expanduser(p))
        data = base64.b64decode(b.get("bytes") or "")
        tmp = f"{p}.tmp-{os.getpid()}"
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)
        return {"path": p, "size": len(data)}

    def fs_list(b):
        """The folder listing, for a Python without tkinter and for typing a path."""
        return F.listing(b.get("path"), b.get("suffixes"))

    # ---- the change-log archive -----------------------------------------
    # ONE FOLDER FOR THE INSTALLATION, beside users/ rather than inside any one person's
    # folder: a change log split per person answers "what did I do" and not "what
    # happened to this plan", and on a shared deployment only the second question is
    # worth asking. Every row names who made the change, so putting them together loses
    # nothing and gains the ordering between people.
    #
    # Appended to at every save, never rewritten. One file a month, so a year of work
    # is twelve readable files rather than one that grows without limit or a thousand
    # that nobody can search; and the header goes in when the file is CREATED, because
    # a header repeated at every append is a header in the middle of the data.
    #
    # Append mode is what makes this safe against the two things that actually happen:
    # two copies of the application running at once, and the machine being turned off
    # mid-save. A short line appended with one write() call is not interleaved by the
    # operating system, and a file that is only ever extended cannot be truncated by a
    # crash - the worst case is a final line that was never finished.
    AUDIT_HEADERS = {
        "changes": "timestamp_utc,who,action,sheet,record,column,previous_value,new_value",
        "findings": "timestamp_utc,who,event,severity,rule,sheet,row,kept_by_user,message",
    }

    def audit_append(b):
        kind = str(b.get("kind") or "changes")
        if kind not in AUDIT_HEADERS:
            raise ValueError("kind must be 'changes' or 'findings'")
        rows = b.get("rows") or []
        if not rows:
            return {"ok": True, "written": 0}
        if not app.data_dir:
            raise ValueError("no data folder has been settled yet")
        folder = PA.audit_dir(app.data_root)
        month = time.strftime("%Y-%m", time.gmtime())      # the file is named in UTC too
        # ONE FILE PER PERSON PER MONTH, in the installation's one audit folder.
        #
        # The folder stays shared, so "what happened to this plan" is still answerable
        # by reading a month's files together - every row already carries the time and
        # who made the change, which is what the ordering needs. What is NOT safe is
        # two sessions appending to ONE file across a network share: Python buffers
        # text, SMB does not promise an append is atomic, and a torn line in the file
        # kept precisely to be trusted is the worst place to have one. Separate files
        # cannot interleave at all, and the account name is the same key the data
        # folder is filed under (S-N06), so nothing new has to be decided.
        path = os.path.join(folder, "PRAP_%s_%s_%s.csv" % (kind, month,
                                                           PA.account_name()))
        fresh = not os.path.exists(path) or os.path.getsize(path) == 0
        # newline="" so csv-shaped text keeps the CRLF the rows already carry, on every
        # platform; utf-8-sig on a NEW file so Excel opens a Korean name correctly.
        with open(path, "a", encoding="utf-8-sig" if fresh else "utf-8",
                  newline="") as fh:
            if fresh:
                fh.write(AUDIT_HEADERS[kind] + "\r\n")
            for r in rows:
                fh.write(str(r) + "\r\n")
            fh.flush()                    # out of Python's buffer before the call ends
        return {"ok": True, "written": len(rows), "path": path, "created": fresh}

    def audit_where(_):
        folder = PA.audit_dir(app.data_root) if app.data_root else ""
        try:
            files = sorted(f for f in os.listdir(folder) if f.endswith(".csv"))
        except OSError:
            files = []
        return {"dir": folder, "files": files}

    def app_quit(_):
        threading.Timer(0.2, app.shutdown).start()
        return {"ok": True}

    def app_alive(b):
        """The page saying it is open. Sent once on load and then on a slow timer."""
        app.client_here(b.get("id"))
        return {"ok": True}

    def app_bye(b):
        """The page saying it is closing. From pagehide - which fires on a reload
        too, so watch_clients() waits a moment before believing it."""
        app.client_gone(b.get("id"))
        return {"ok": True}

    return {
        "caps": caps,
        "paths": paths,
        "identity/get": identity_get,
        "identity/set": identity_set,
        "identity/suggest": identity_suggest,
        "ws/open": ws_open,
        "ws/openDialog": ws_open_dialog,
        "ws/save": ws_save,
        "ws/saveAs": ws_save_as,
        "ws/recent": ws_recent,
        "ws/versions": ws_versions,
        "ws/restore": ws_restore,
        "ws/stat": ws_stat,
        "claim/take": claim_take,
        "ws/sharedState": ws_shared_state,
        "ws/moveToShared": ws_move_to_shared,
        "claim/read": claim_read,
        "claim/release": claim_release,
        "claim/holds": claim_holds,
        "journal/write": journal_write,
        "journal/read": journal_read,
        "journal/clear": journal_clear,
        "file/openSource": file_open_source,
        "file/export": file_export,
        "fs/list": fs_list,
        "audit/append": audit_append,
        "audit/where": audit_where,
        "quit": app_quit,
        "app/alive": app_alive,
        "app/bye": app_bye,
    }


# ------------------------------------------------------------------- the handler

# The operations that can stop and wait for somebody to choose a file. They run
# WITHOUT the application lock (see do_POST), so each one takes it itself around
# whatever it changes - which for three of the four is nothing at all: they read a
# path, or bytes, and hand them back.
BLOCKING_OPS = {"ws/openDialog", "ws/saveAs", "file/openSource", "file/export"}


def make_handler(app):
    ops = operations(app)

    class Handler(BaseHTTPRequestHandler):
        server_version = "PM_APP"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        # -------------------------------------------------------- guards

        def _host_is_loopback(self):
            host = (self.headers.get("Host") or "").split(":")[0].strip("[]")
            return host in ("127.0.0.1", "localhost", "::1")

        def _origin_is_ours(self):
            origin = self.headers.get("Origin")
            if origin:
                try:
                    h = urllib.parse.urlparse(origin).hostname or ""
                except ValueError:
                    return False
                if h not in ("127.0.0.1", "localhost", "::1"):
                    return False
            site = self.headers.get("Sec-Fetch-Site")
            return site in (None, "same-origin", "none")

        def _key_ok(self, given):
            return bool(given) and secrets.compare_digest(str(given), app.key)

        # ---------------------------------------------------------- GET

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            if not self._host_is_loopback():
                return self._text(403, "Not for you.")
            if u.path in ("/", "/index.html"):
                q = urllib.parse.parse_qs(u.query)
                if not self._key_ok((q.get("k") or [None])[0]):
                    return self._text(403, "This page is opened by the application, "
                                           "not by a bookmark. Start PM_APP again.")
                page = app.page.replace("__PM_KEY__", app.key)
                return self._bytes(200, page.encode("utf-8"),
                                   "text/html; charset=utf-8", nostore=True)
            if u.path == "/favicon.ico":
                return self._bytes(204, b"", "image/x-icon")
            # There is no path here that maps a URL onto a file. Nothing to escape.
            return self._text(404, "No such page.")

        # --------------------------------------------------------- POST

        def do_POST(self):
            u = urllib.parse.urlparse(self.path)
            if not self._host_is_loopback():
                return self._json(403, {"error": True, "kind": "forbidden",
                                        "message": "Not for you."})
            if not self._origin_is_ours():
                return self._json(403, {"error": True, "kind": "forbidden",
                                        "message": "Cross-site request refused."})
            if not self._key_ok(self.headers.get("X-PM-Key")):
                return self._json(403, {"error": True, "kind": "forbidden",
                                        "message": "Wrong key."})
            if not u.path.startswith("/api/"):
                return self._json(404, {"error": True, "kind": "not_found",
                                        "message": "No such operation."})

            name = u.path[len("/api/"):]
            op = ops.get(name)
            if op is None:
                return self._json(404, {"error": True, "kind": "not_found",
                                        "message": f"No operation called {name}."})

            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                n = 0
            if n > 256 * 1024 * 1024:
                return self._json(413, {"error": True, "kind": "too_big",
                                        "message": "That is too large to send."})
            raw = self.rfile.read(n) if n else b"{}"
            try:
                body = json.loads(raw.decode("utf-8")) if raw.strip() else {}
            except (ValueError, UnicodeDecodeError):
                return self._json(400, {"error": True, "kind": "bad_request",
                                        "message": "Unreadable request."})

            try:
                if name in BLOCKING_OPS:
                    # A dialog waits for a PERSON - up to ten minutes (files.py). Held
                    # under the one application lock, that queued every other request
                    # behind it: the page's own claim check, its liveness ping, a second
                    # window. The window looked frozen because it was. These four take
                    # the lock themselves, around the part that touches shared state.
                    result = op(body if isinstance(body, dict) else {})
                else:
                    with app._lock:
                        result = op(body if isinstance(body, dict) else {})
            except WS.StorageError as e:
                return self._json(200, e.as_dict())
            except OSError as e:
                return self._json(200, {"error": True, "kind": "unreadable",
                                        "message": str(e)})
            except Exception as e:                      # noqa: BLE001
                # An unexpected failure is reported to the page as a sentence rather
                # than as a dead request. The console keeps the detail.
                self.log_error("%s failed: %r", name, e)
                return self._json(200, {"error": True, "kind": "internal",
                                        "message": f"{name} failed: {e}"})
            return self._json(200, {"ok": True, "result": result})

        # ------------------------------------------------------ replies

        def _json(self, code, obj):
            self._bytes(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8", nostore=True)

        def _text(self, code, text):
            self._bytes(code, text.encode("utf-8"), "text/plain; charset=utf-8")

        def _bytes(self, code, data, ctype, nostore=False):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if nostore:
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if data:
                self.wfile.write(data)

        def log_message(self, fmt, *args):
            # Silent by default: the console window is the user's "it is running"
            # light, and a line per request turns it into noise they learn to ignore.
            if os.environ.get("PM_APP_VERBOSE"):
                super().log_message(fmt, *args)

    return Handler


def serve(app, host="127.0.0.1", port=0):
    """Bind, and return the running server. Loopback only, port chosen by the OS."""
    httpd = ThreadingHTTPServer((host, port), make_handler(app))
    httpd.daemon_threads = True
    return httpd
