"""storage: workspaces - the Python port of src/storage/desktop/workspace.js.

Line for line the same protocol, because the protocol is the part that can lose
somebody's work: serialise, write to a temporary name in the same directory, flush
it to the physical disk, roll the current file into the version history, then
REPLACE the target in one atomic step.

Two things differ from the JavaScript, and both are Windows facts rather than
choices:

  * os.replace, never os.rename. On Windows a rename onto an existing file fails;
    os.replace is MoveFileEx with REPLACE_EXISTING, which is the atomic one.
  * the temporary name carries the process id, so two shells saving two different
    plans in one folder cannot collide - the same rule the JavaScript uses.

Standard library only (NR-DEP-05), no shell, no HTTP, no page. That is deliberate:
everything here is testable by running python against it, and a defect that needs a
window open to reproduce is a defect that gets found late.

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheets 03, 04, 06.
"""

import errno
import json
import os
import re
import shutil
from pathlib import Path

from . import timefmt

APP = "PM_APP"
FORMAT = "prap-source-data"
FORMAT_VERSION = 1
SCHEMA_EXPECTED = 13          # the layout core/ reads; kept in step with
                              # SCHEMA_EXPECTED in core/00_meta.js, which is the
                              # one the findings report quotes at the user (V-09)

_version = "1.0"


class StorageError(Exception):
    """The errors the interface raises. The page switches on `kind`; the user reads
    `message`. A storage layer that raises one kind of error forces the screen to
    say one kind of thing, and "something went wrong" is the sentence that wastes an
    afternoon."""

    def __init__(self, kind, message, detail=None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.detail = detail

    def as_dict(self):
        return {"error": True, "kind": self.kind, "message": self.message,
                "detail": self.detail}


def current_version():
    return _version


def set_version(v):
    global _version
    _version = str(v)


def cmp_version(a, b):
    pa = [int(x) if x.isdigit() else 0 for x in str(a).split(".")]
    pb = [int(x) if x.isdigit() else 0 for x in str(b).split(".")]
    for i in range(max(len(pa), len(pb))):
        d = (pa[i] if i < len(pa) else 0) - (pb[i] if i < len(pb) else 0)
        if d:
            return -1 if d < 0 else 1
    return 0


# ------------------------------------------------------------------ where things go

def backup_dir(ref):
    return os.path.join(os.path.dirname(os.path.abspath(ref)), "backups")


def backup_path(ref, n):
    return os.path.join(backup_dir(ref), f"{os.path.basename(ref)}.{n}")


def journal_path(ref):
    return f"{ref}.journal"


def tmp_path(ref):
    return f"{ref}.tmp-{os.getpid()}"


# ------------------------------------------------------------------------ reading

OLE2 = bytes([0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1])


def looks_protected(buf: bytes) -> bool:
    """Tell a PROTECTED file from a CORRUPT one - R-N18.

    A file encrypted by company document security is bytes an ordinary application
    cannot parse, which is exactly what a truncated or damaged file looks like from
    here. Reported as corruption it sends somebody hunting for a backup they do not
    need; reported as protection it is unlocked in half a minute.
    """
    if len(buf) < 8:
        return False
    if buf[:8] == OLE2:                       # what an encrypted .xlsx becomes
        return True
    if buf[:4] == b"PK\x03\x04":              # a ZIP that says it is encrypted
        return (buf[6] & 0x01) == 1
    return False


def can_write(ref) -> bool:
    return os.access(os.path.dirname(os.path.abspath(ref)) or ".", os.W_OK)


def read_bytes(ref) -> bytes:
    """Read a file, and turn the failures into sentences rather than errno."""
    try:
        with open(ref, "rb") as f:
            return f.read()
    except FileNotFoundError as e:
        raise StorageError("not_found",
                           f"That file is no longer at {ref}. It may have been moved "
                           f"or deleted.", "ENOENT") from e
    except PermissionError as e:
        raise StorageError("read_only",
                           f"{ref} could not be read. You may not have permission to "
                           f"open it.", "EACCES") from e
    except OSError as e:
        raise StorageError("unreadable",
                           f"{os.path.basename(ref)} could not be read.", str(e)) from e


def open_workspace(ref):
    """Read and parse a workspace. The sheets come back exactly as core/ expects."""
    buf = read_bytes(ref)

    if looks_protected(buf):
        raise StorageError(
            "protected",
            f"{os.path.basename(ref)} could not be opened. It looks like it is "
            f"protected by file security - open it in Excel first to unlock it, then "
            f"import it again.")

    try:
        doc = json.loads(buf.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise StorageError("unreadable",
                           f"{os.path.basename(ref)} is not a plan file. It may be a "
                           f"source workbook - use Import instead.", str(e)) from e

    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        raise StorageError("unreadable",
                           f"{os.path.basename(ref)} is not a plan file. It may be a "
                           f"source workbook - use Import instead.",
                           f"format={doc.get('format') if isinstance(doc, dict) else '?'}")

    header = doc.get("workspace") or {}
    # NR-DEP-04: refuse, never partially read. Reading a file written by a version
    # that knows more than this one, and writing it back, is how fields disappear.
    if header.get("app_version") and cmp_version(header["app_version"],
                                                 current_version()) > 0:
        raise StorageError("too_new",
                           f"This plan was saved by version {header['app_version']}. "
                           f"This is version {current_version()}. Use the newer "
                           f"version to open it.")

    return {"sheets": doc.get("sheets"), "header": header, "ref": os.path.abspath(ref),
            "readOnly": not can_write(ref)}


# ------------------------------------------------------------------------ writing

def last_saved_of(ref):
    """What the file itself says it was last saved at, or None if it cannot say.

    A MODIFICATION TIME CANNOT BE TRUSTED FOR THIS. A share may round one to two
    seconds, so two saves inside the same tick are indistinguishable - and a check
    that cannot tell them apart is no check at all on the day it matters. The
    workspace states its own `last_saved` to the millisecond, written by the same
    code that writes the rest of the file, so it moves exactly when the content
    moves and never when it does not (NR-STO-16).
    """
    try:
        with open(ref, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return None
    return ((doc.get("workspace") or {}) if isinstance(doc, dict) else {}).get("last_saved")


def save_workspace(ref, sheets, header=None, holds_claim=None, retain=1, identity=None,
                   base_saved=None):
    """The save protocol, specification sheet 06, step for step.

    The order is the whole of it. A replace is atomic; a write is not. Power loss at
    any point leaves a readable workspace - the old one before the replace, the new
    one after it - and never half of each.

    `holds_claim` is passed in rather than looked up, so this function can be tested
    without a claim and so the caller cannot forget to check: there is no path
    through it that writes without asking.
    """
    header = header or {}
    if holds_claim is not None and not holds_claim(ref):
        raise StorageError("claim_lost",
                           "Your hold on this plan was taken over while you were "
                           "working. Nothing has been saved. Save As a copy to keep "
                           "your changes.")

    # NR-STO-16, at the point the bytes are actually written.
    #
    # The claim is not enough on its own: a session that has only READ a plan never
    # took one, so nothing stopped it writing over a colleague's newer save - and the
    # save reported success while doing it. The caller states which issue of the file
    # its figures came from; if the file is a different issue now, the save stops and
    # the colleague's work is still there.
    #
    # Optional, because it can only be checked when the caller can state it: a plan
    # being created has no previous issue to name.
    if base_saved:
        current = last_saved_of(ref)
        if current and current != base_saved:
            raise StorageError(
                "superseded",
                f"{os.path.basename(ref)} was saved by somebody else after you opened "
                f"it. Nothing has been saved, so their work is intact. Reload the plan "
                f"and make your change again, or Save As a copy to keep yours.",
                f"base={base_saved} current={current}")

    now = timefmt.iso()
    doc = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "workspace": {
            "app": APP,
            "app_version": current_version(),
            "schema_version": SCHEMA_EXPECTED,
            "created": header.get("created") or now,
            "last_saved": now,
            "last_saved_by": ({"name": identity.get("name"),
                               "department": identity.get("department")}
                              if identity else header.get("last_saved_by")),
            "imported_from": header.get("imported_from"),
        },
        "sheets": sheets,
    }
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(ref)) or ".", exist_ok=True)
    tmp = tmp_path(ref)
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())              # NR-STO-04: on the disk, not in a cache
    except OSError as e:
        _unlink(tmp)
        if e.errno == errno.ENOSPC:
            raise StorageError("no_space",
                               "There is not enough room to save. Nothing has been "
                               "changed - your previous save is intact.",
                               "ENOSPC") from e
        if e.errno in (errno.EACCES, errno.EPERM, errno.EROFS):
            raise StorageError("read_only",
                               f"{os.path.dirname(os.path.abspath(ref))} cannot be "
                               f"written to. Save As somewhere else, or ask for write "
                               f"access.", str(e.errno)) from e
        raise StorageError("unreadable",
                           f"The plan could not be saved: {e}", str(e.errno)) from e

    roll_versions(ref, retain)
    os.replace(tmp, ref)                      # NR-STO-05: atomic, and Windows-safe
    clear_journal(ref)                        # committed, so nothing is pending

    return {"savedAt": now, "ref": os.path.abspath(ref)}   # only NOW is it saved


def roll_versions(ref, retain=1):
    """Keep the previous version, and only as many as asked for.

    Q-N07 set the default at one, recorded with its consequence rather than
    silently: two bad saves in a row push the good version out of history (R-N19),
    which is why the Excel export stays the archive that matters.
    """
    if not os.path.exists(ref) or retain <= 0:
        return
    os.makedirs(backup_dir(ref), exist_ok=True)
    for n in range(retain, 1, -1):
        src, dst = backup_path(ref, n - 1), backup_path(ref, n)
        if os.path.exists(src):
            os.replace(src, dst)
    shutil.copyfile(ref, backup_path(ref, 1))


def list_versions(ref):
    out = []
    for n in range(1, 21):
        p = backup_path(ref, n)
        if not os.path.exists(p):
            break
        out.append({"n": n, "ref": p, "at": timefmt.iso(os.stat(p).st_mtime * 1000)})
    return out


def restore_version(ref, n=1):
    """Read a retained version. It does NOT overwrite the current one - the caller
    lands it as a pending edit, so a restore made by mistake costs nothing and a
    restore made deliberately goes through the same door as every other change."""
    p = backup_path(ref, int(n or 1))
    if not os.path.exists(p):
        raise StorageError("not_found", "There is no previous version of this plan kept.")
    doc = json.loads(Path(p).read_text(encoding="utf-8"))
    return {"sheets": doc.get("sheets"), "header": doc.get("workspace") or {}}


# ------------------------------------------------------------------------ journal

# Pending edits, kept APART from the committed workspace (N-08). That separation is
# what lets recovery offer them back without a half-typed row ever having been
# committed data.

def write_journal(ref, pending):
    """Write down what has not been committed yet, and WHICH SAVE it was made against.

    The version it was made against has to be recorded here, at writing time. A
    reader cannot work it out afterwards from modification times: see read_journal.
    """
    tmp = f"{journal_path(ref)}.tmp-{os.getpid()}"
    body = {"at": timefmt.iso(), "pending": pending, "base_saved": last_saved_of(ref)}
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, journal_path(ref))
    return {"ok": True}


def read_journal(ref):
    p = journal_path(ref)
    if not os.path.exists(p):
        return None
    try:
        j = json.loads(Path(p).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None                           # a torn journal is no journal
    # Only offer it if it was made against the plan AS IT STANDS. Otherwise the edits
    # were made against figures that have since been replaced, and applying them would
    # put them somewhere they were never made.
    #
    # WHAT THIS USED TO COMPARE, AND WHY IT HAD TO CHANGE. It compared modification
    # times: offer the journal if it is newer than the plan. Two files saved in the
    # same tick have the SAME time, and `<=` then threw the journal away - so a
    # journal written just after a save was discarded, which is precisely when one is
    # written. Measured here: 30 of 200 on a local disk, and on a Windows share it is
    # not a race at all but the normal case, because SMB rounds a modification time to
    # two seconds and every journal written within two seconds of a save looks equal.
    # A share is where this application lives (NR-DEP-09), and a recovery journal that
    # is thrown away is NR-STO-07 unimplemented rather than implemented. So the plan's
    # own last_saved is compared instead - the same token, for the same reason, as the
    # superseded-save check in save_workspace.
    if os.path.exists(ref):
        if "base_saved" in j:
            if j["base_saved"] != last_saved_of(ref):
                return None
        elif os.stat(p).st_mtime <= os.stat(ref).st_mtime:
            return None          # written by an older version: times are all there is
    return j


def clear_journal(ref):
    _unlink(journal_path(ref))
    return {"ok": True}


# -------------------------------------------------------------------- housekeeping

_TMP = re.compile(r"\.tmp-\d+$")


def move_plan(src, dst):
    """Move a plan and everything that belongs to it - or move nothing at all.

    A PLAN IS FOUR KINDS OF FILE, and only the first one has the name people know:

        X.prap                  the plan
        X.prap.journal          edits made and not yet committed
        X.prap.lock             who is editing it - NOT moved, see below
        backups/X.prap.1 ..     the versions kept behind it

    A rename would carry the first and abandon the rest, and the person would find
    out when they went looking for a previous version they had been told was kept.

    COPY, VERIFY, THEN REMOVE - never rename and hope. The destination is written
    beside itself and renamed into place, read back, and compared with what was read
    from the source; the source is deleted only once every piece is known to have
    arrived. If anything goes wrong at any point, whatever reached the destination is
    removed again and the source is left exactly as it was: a half-moved plan is
    worse than one that did not move.

    THE CLAIM IS NOT MOVED. It names a machine and a process against a path, and the
    path is changing. The caller releases it before calling and takes it again at the
    new location, which is also what makes the move visible to anybody waiting.
    """
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if src == dst:
        raise StorageError("same", "That plan is already there.")
    if not os.path.exists(src):
        raise StorageError("missing", f"{os.path.basename(src)} is not there any more.")
    for occupied in (dst, journal_path(dst)):
        if os.path.exists(occupied):
            raise StorageError("exists",
                f"There is already a plan called {os.path.basename(dst)} in the team "
                f"folder. Nothing has been moved. Rename yours, or open theirs and "
                f"check it is not the same plan twice.",
                occupied)

    body = read_bytes(src)
    landed = []                       # everything created, in case it must be undone

    def land(target, data):
        tmp = tmp_path(target)
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        landed.append(target)
        if open(target, "rb").read() != data:
            raise StorageError("verify", f"{os.path.basename(target)} did not arrive "
                                         "intact. Nothing has been moved.")

    try:
        land(dst, body)
        jrn = journal_path(src)
        if os.path.exists(jrn):
            land(journal_path(dst), open(jrn, "rb").read())
        kept = []
        for n in range(1, 21):
            b = backup_path(src, n)
            if not os.path.exists(b):
                break
            kept.append((n, open(b, "rb").read()))
        if kept:
            os.makedirs(backup_dir(dst), exist_ok=True)
            for n, data in kept:
                land(backup_path(dst, n), data)
    except OSError as e:
        for t in landed:
            _unlink(t)
        raise StorageError("copy", "The plan could not be written to the team folder, "
                                   "so nothing has been moved.", type(e).__name__)
    except StorageError:
        for t in landed:
            _unlink(t)
        raise

    # Everything is at the destination and verified. Only now does the original go.
    _unlink(journal_path(src))
    for n in range(1, 21):
        b = backup_path(src, n)
        if not os.path.exists(b):
            break
        _unlink(b)
    _unlink(src)
    return {"ok": True, "ref": dst, "versions": len(kept),
            "journal": os.path.exists(journal_path(dst))}


def sweep_temp(directory):
    """A leftover .tmp-<pid> means a save was interrupted. The workspace itself is
    intact by construction, so there is nothing to repair and nothing to tell the
    user - only a file to remove."""
    n = 0
    try:
        names = os.listdir(directory)
    except OSError:
        return 0
    for name in names:
        if _TMP.search(name):
            _unlink(os.path.join(directory, name))
            n += 1
    return n


def stat(ref):
    try:
        st = os.stat(ref)
        return {"exists": True, "mtime": st.st_mtime * 1000, "size": st.st_size}
    except OSError:
        return {"exists": False, "mtime": 0, "size": 0}


def _unlink(p):
    try:
        os.unlink(p)
    except OSError:
        pass
