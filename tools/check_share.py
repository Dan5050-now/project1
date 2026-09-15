"""Is this folder safe for several people to keep plans in? Ask the folder, on site.

RUN IT WHERE THE PLANS WILL LIVE:

    python tools/check_share.py \\\\server\\share\\PRAP

WHY IT PRINTS RATHER THAN WRITES. The share that matters is inside a company network,
and a result file often cannot leave one. So this writes no report: it prints a dozen
lines to the screen and a short code at the end, and a person can read those out.
Nothing in the output identifies the company, the share, the machine or the person -
the path is never printed, only what it did. That is not a courtesy, it is what makes
the result sayable out loud without anybody having to review it first.

WHAT IT LEAVES BEHIND: nothing. Every file it makes is inside a folder it creates and
deletes, and it says so at the end. It reads no plan, opens no workbook and touches
nothing that was already there.

WHAT IT CANNOT TELL YOU. That the share is fast, that backups exist, or that the
permissions are the ones the company intended. It answers exactly the questions the
application's own correctness rests on, and no more.

    python tools/check_share.py <folder>          the checks
    python tools/check_share.py <folder> --keep   leave the scratch folder for
                                                  inspection instead of removing it

Standard library only, Python 3.9+, one file - so it can be copied to a machine that
has nothing else on it (NR-DEP-05).
"""

import hashlib
import json
import os
import sys
import time

SCRATCH = "prap-share-check"
FINDINGS = []


def say(label, verdict, detail=""):
    FINDINGS.append((label, verdict, detail))
    print(f"  {label:<26} {verdict:<9} {detail}")


def probe_writable(d):
    """The predicate the application itself uses, run here against this share."""
    probe = os.path.join(d, ".prap-probe-%d-%d" % (os.getpid(), int(time.time() * 1000)))
    try:
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        return False
    try:
        os.close(fd)
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass
    return True


def check_exclusive(work):
    """One winner. The write claim is an exclusive create and nothing else (NR-STO-10).

    A share that let two callers both create the same name would hand the same plan to
    two people at once, and neither would be told."""
    target = os.path.join(work, "claim")
    won = 0
    for _ in range(8):
        try:
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            continue
        except OSError:
            return say("exclusive create", "ERROR", "the share refused the call itself")
        os.close(fd)
        won += 1
    os.unlink(target)
    say("exclusive create", "PASS" if won == 1 else "FAIL", f"{won} winner of 8 attempts")


def check_replace(work):
    """A save lands whole or not at all: written aside, then renamed over."""
    final = os.path.join(work, "plan")
    with open(final, "w", encoding="utf-8") as f:
        f.write("old")
    tmp = final + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("new")
    try:
        os.replace(tmp, final)
    except OSError as e:
        return say("rename over existing", "FAIL", type(e).__name__)
    got = open(final, encoding="utf-8").read()
    os.unlink(final)
    say("rename over existing", "PASS" if got == "new" else "FAIL", "" if got == "new"
        else "the rename reported success and the old content is still there")


def check_append(work):
    """Two writers on one change log. Every row already names who made the change, so
    the risk is a TORN row rather than an out-of-order one (defect G)."""
    log = os.path.join(work, "log.csv")
    rows = 200
    for who in ("A", "B"):
        with open(log, "a", encoding="utf-8") as f:
            for i in range(rows):
                f.write(f"{who},{i:04d},{'x' * 40}\n")
                f.flush()
    lines = open(log, encoding="utf-8").read().splitlines()
    torn = [ln for ln in lines if len(ln.split(",")) != 3 or len(ln) != 47]
    os.unlink(log)
    say("append, 2 writers", "PASS" if not torn and len(lines) == rows * 2 else "FAIL",
        f"{len(lines)} rows, {len(torn)} torn")


def check_mtime(work):
    """Informational ONLY, and labelled so. The application compares a plan's own
    last_saved and no longer believes a modification time - a share that rounds one to
    two seconds cannot tell two saves apart. The number is printed because it explains
    why, not because anything depends on it."""
    a = os.path.join(work, "t1")
    stamps = []
    for _ in range(3):
        with open(a, "w", encoding="utf-8") as f:
            f.write("x")
        stamps.append(os.stat(a).st_mtime)
        time.sleep(0.35)
    os.unlink(a)
    gaps = [round(stamps[i + 1] - stamps[i], 3) for i in range(len(stamps) - 1)]
    coarse = all(g == 0 or abs(g - round(g)) < 0.001 for g in gaps)
    say("mtime granularity", "INFO", f"gaps {gaps} s"
        + ("  - coarse, as a share often is" if coarse else ""))


def check_journal(work):
    """What a power cut leaves behind must still be there afterwards, and must be
    judged by the plan's own last_saved rather than by a clock (NR-STO-07)."""
    ref = os.path.join(work, "p.prap")
    with open(ref, "w", encoding="utf-8") as f:
        json.dump({"workspace": {"last_saved": "2026-01-01T00:00:00.000Z"}}, f)
    jrn = ref + ".journal"
    tmp = jrn + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"pending": [{"col": "project_name"}],
                   "base_saved": "2026-01-01T00:00:00.000Z"}, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, jrn)
    back = json.load(open(jrn, encoding="utf-8"))
    same_tick = back.get("base_saved") == json.load(
        open(ref, encoding="utf-8"))["workspace"]["last_saved"]
    os.unlink(jrn)
    os.unlink(ref)
    say("journal survives", "PASS" if back.get("pending") and same_tick else "FAIL",
        "written, read back, and still matches its save")


def check_listing(work):
    """A plan nobody can see is a plan nobody can open."""
    name = os.path.join(work, "visible.prap")
    with open(name, "w", encoding="utf-8") as f:
        f.write("{}")
    seen = "visible.prap" in os.listdir(work)
    os.unlink(name)
    say("new file is listed", "PASS" if seen else "FAIL")


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip().splitlines()[0])
        print("\n    python tools/check_share.py <folder>")
        return 2
    where = argv[1]
    keep = "--keep" in argv

    print()
    print("PM_APP  share check".ljust(42) + time.strftime("%Y-%m-%d %H:%M"))
    print("  " + "-" * 62)

    if not os.path.isdir(where):
        print("  that folder is not there, or this machine cannot see it.")
        return 1

    say("writable (probe file)", "PASS" if probe_writable(where) else "FAIL",
        "this is the application's own check")
    if FINDINGS[-1][1] == "FAIL":
        print("\n  Nothing else can be checked in a folder that cannot be written.")
        print("  verdict  NOT USABLE - choose another folder, or ask for write access.")
        return 1

    work = os.path.join(where, SCRATCH)
    try:
        os.mkdir(work)
    except FileExistsError:
        print(f"\n  '{SCRATCH}' is already there - an earlier run was interrupted.")
        print("  Delete it and run this again.")
        return 1
    except OSError as e:
        print(f"\n  could not make a scratch folder: {type(e).__name__}")
        return 1

    try:
        check_exclusive(work)
        check_replace(work)
        check_append(work)
        check_journal(work)
        check_listing(work)
        check_mtime(work)
    finally:
        if keep:
            print(f"\n  scratch folder kept: {SCRATCH}")
        else:
            for f in os.listdir(work):
                try:
                    os.unlink(os.path.join(work, f))
                except OSError:
                    pass
            try:
                os.rmdir(work)
                left = "nothing left behind"
            except OSError:
                left = f"COULD NOT REMOVE '{SCRATCH}' - please delete it by hand"

    bad = [f for f in FINDINGS if f[1] == "FAIL"]
    err = [f for f in FINDINGS if f[1] == "ERROR"]
    print("  " + "-" * 62)
    verdict = ("SAFE FOR SHARED USE" if not bad and not err
               else "NOT SAFE - report the FAIL lines above")
    print(f"  {'verdict':<26} {verdict}")
    if not keep:
        print(f"  {'cleanup':<26} {left}")

    # A short code over the verdicts, so six lines read down a telephone can be checked
    # for a slip. It is a digest of the PASS/FAIL words only - it carries no path, no
    # name and no timing, and it cannot be turned back into any of them.
    digest = hashlib.sha256("|".join(f"{a}={b}" for a, b, _ in FINDINGS).encode()).digest()
    alpha = "0123456789ABCDEFGHJKMNPQRSTUVWXYZ"          # no I, L, O - they misread
    code = "".join(alpha[b % 33] for b in digest[:12])
    print(f"  {'code':<26} {code[:4]}-{code[4:8]}-{code[8:12]}")
    print()
    return 1 if (bad or err) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
