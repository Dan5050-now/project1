"""storage: the write claim - the Python port of src/storage/desktop/claim.js.

One writer at a time. Any number of readers. Nobody is ever blocked from LOOKING.

The claim is taken when a data value actually changes - not when the plan is opened,
and not when somebody clicks into a cell. That distinction is the whole reason this
file exists rather than a lock: a claim taken on open would let somebody who glanced
at a plan and went to lunch block the team for half an hour (U-N03).

The file format is byte-compatible with the Electron shell's, deliberately. The two
shells may end up on the same share during the changeover, and a claim only works if
everyone can read it.

Specification: PRAP_NewApp_Specification_v1.3.xlsx sheet 07.
"""

import json
import os
import socket
import time

from . import timefmt

HEARTBEAT_MS = 30_000                 # "is the holder alive?"        - N-23
EXPIRY_MS = 30 * 60_000               # "may somebody else take it?"  - Q-N16


def lock_path(ref):
    return f"{ref}.lock"


def machine():
    return socket.gethostname()


def status_of(held, now=None):
    """Two different questions, two different numbers.

    Keeping them apart is what makes a half-hour expiry comfortable rather than
    opaque: the application knows within thirty seconds that a holder has gone
    quiet, long before anyone may act on it, so it can say WHICH - a colleague
    mid-sentence, or one whose laptop died twenty minutes ago.
    """
    if not held:
        return "free"
    now = timefmt.now_ms() if now is None else now
    quiet = now - timefmt.parse(held.get("heartbeat") or held.get("since"))
    if quiet > EXPIRY_MS:
        return "expired"
    if quiet > HEARTBEAT_MS:
        return "silent"
    return "active"


def is_mine(held, identity):
    return bool(held) and held.get("name") == identity.get("name") \
        and held.get("machine") == machine()


def read_claim(ref):
    p = lock_path(ref)
    for attempt in range(2):
        if not os.path.exists(p):
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (ValueError, OSError):
            # A torn read of a file being rewritten by its holder's heartbeat is
            # possible, especially on a share. Reading twice costs nothing and
            # avoids reporting a live holder as an unreadable one.
            if attempt == 0:
                time.sleep(0.2)
    return {"name": "(unknown)", "department": "", "machine": "", "since": None,
            "heartbeat": timefmt.iso(), "unreadable": True}


def claim(ref, identity, app_version="1.0", now=None):
    """Take the claim, or report who holds it.

    The claim is made with an EXCLUSIVE CREATE, which fails if the file already
    exists. Not read-then-write: two sessions can both read "free" and both then
    write one, and each would believe it had won. Exclusive create is decided by the
    filesystem, has exactly one winner, and works over SMB.
    """
    now = timefmt.now_ms() if now is None else now
    body = {
        "name": identity.get("name"),
        "department": identity.get("department") or "",
        "machine": machine(),
        "pid": os.getpid(),
        "since": timefmt.iso(now),
        "heartbeat": timefmt.iso(now),
        "app_version": app_version,
    }

    try:
        fd = os.open(lock_path(ref), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False)
        return {"ok": True, "claim": body}

    # Somebody has it. Whether we may take it over depends on WHO and HOW LONG.
    held = read_claim(ref)
    state = status_of(held, now)

    # Your own crashed session, on your own machine: back at once. Thirty minutes
    # locked out of somebody else's plan is a policy; thirty minutes locked out of
    # your OWN is an obstruction (N-24).
    if is_mine(held, identity) and state != "active":
        return _take_over(ref, body, held, "your own earlier session")

    if state == "expired":
        return _take_over(ref, body, held, "an expired claim")

    return {"ok": False, "holder": held, "state": state, "freeAt": free_at(held),
            "message": blocked_message(held, state, free_at(held))}


def free_at(held):
    beat = timefmt.parse((held or {}).get("heartbeat") or (held or {}).get("since"))
    return timefmt.iso(beat + EXPIRY_MS) if beat else None


def _take_over(ref, body, previous, why):
    body["displaced"] = {"name": (previous or {}).get("name"), "why": why}
    with open(lock_path(ref), "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False)
    return {"ok": True, "claim": body, "displaced": previous, "why": why}


def refresh_claim(ref, identity):
    """The heartbeat. Rewrites the time inside the claim and NOTHING else - if the
    claim is no longer ours we stop, rather than stamping our name over somebody
    else's."""
    held = read_claim(ref)
    if not held or held.get("name") != identity.get("name") \
            or held.get("machine") != machine() or held.get("pid") != os.getpid():
        return {"ok": False, "holder": held}
    held["heartbeat"] = timefmt.iso()
    with open(lock_path(ref), "w", encoding="utf-8") as f:
        json.dump(held, f, ensure_ascii=False)
    return {"ok": True}


def release_claim(ref, identity):
    """Released on save-and-close, on discard, and on application close - NOT on
    save alone, which would hand the plan to somebody else mid-task (N-22)."""
    held = read_claim(ref)
    if held and (held.get("name") != identity.get("name")
                 or held.get("machine") != machine()
                 or held.get("pid") != os.getpid()):
        return {"ok": False, "holder": held}
    try:
        os.unlink(lock_path(ref))
    except OSError:
        pass
    return {"ok": True}


def holds_claim(ref, identity):
    """Does THIS session hold the claim? Used for what the window shows."""
    held = read_claim(ref)
    return bool(held) and held.get("name") == identity.get("name") \
        and held.get("machine") == machine() and held.get("pid") == os.getpid()


def may_write(ref, identity):
    """May this session WRITE to this plan? The guard before every save, and it is
    NOT the same question as holds_claim.

    Found by the Electron smoke test and ported with its reasoning intact: a
    brand-new plan has no claim on it, because the claim is taken when a value
    changes in an OPEN workspace and a plan being created was never opened. Guarding
    the save with "do we hold it" refused the very first save of every new plan.

    The question a save actually has to ask is whether somebody ELSE holds it: ours
    is fine, nobody's is fine, and theirs is the one case that must stop.
    """
    held = read_claim(ref)
    if not held:
        return True                                    # nobody has it
    if held.get("name") == identity.get("name") and held.get("machine") == machine():
        return True
    return status_of(held) == "expired"                # theirs, but long dead


def blocked_message(holder, state, free):
    """What a blocked colleague is told. The words are specified, so they live here
    rather than being invented at the screen: a message that names somebody and says
    when the plan frees is actionable, and "file in use" is not."""
    holder = holder or {}
    who = (f"{holder.get('name')} ({holder.get('department')})"
           if holder.get("department") else str(holder.get("name")))

    def t(s):
        ms = timefmt.parse(s)
        if not ms:
            return "an unknown time"
        return time.strftime("%H:%M", time.localtime(ms / 1000.0))

    if state == "active":
        return f"{who} is editing this plan. Started {t(holder.get('since'))}, active now."
    if state == "silent":
        return (f"{who} has been editing this plan since {t(holder.get('since'))}, but "
                f"their session has not responded since {t(holder.get('heartbeat'))}. "
                f"The plan becomes free at {t(free)}.")
    return (f"{holder.get('name')}'s session stopped responding at "
            f"{t(holder.get('heartbeat'))} and no longer holds this plan. You may "
            f"take over.")
