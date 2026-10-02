"""Can this PC run the application? Ask the PC, on site.

    python tools\\check_pc.py                 with whatever Python started it
    runtime\\python.exe tools\\check_pc.py     with the runtime bundled beside the app

WHY IT PRINTS RATHER THAN WRITES, same as tools/check_share.py: the machine that has
to answer is inside a company network, and a result file often cannot leave one. So
this writes no report. A dozen lines on the screen and a short code, and a person can
read those out. Nothing in the output names the machine, the account, the domain or
any path - not as a courtesy, but because that is what makes the answer sayable out
loud without anybody having to review it first.

WHAT IT ANSWERS. Everything the application needs from a PC, and nothing else:

    a Python new enough                       3.9 or newer
    the standard library it uses              nineteen modules, no pip, no wheel
    a loopback socket it can listen on        the shell serves the page on 127.0.0.1
    a browser it can open                     the page has to appear somewhere
    somewhere to write beside itself          data\\ lives next to the application

A FAIL is something that stops the application. A WARN is something that does not -
the application runs, and one named thing about it is worse. They are reported apart
because a check that calls a survivable thing fatal is a check people learn to argue
with.

It does NOT answer whether the shared folder works - tools/check_share.py does that,
and the two are separate because they fail for different reasons and are fixed by
different people.

    python tools/check_pc.py                 the checks
    python tools/check_pc.py --where <dir>   also: can it write in THAT folder
"""

import hashlib
import os
import socket
import sys
import time

FINDINGS = []
NEEDED = ("base64 datetime errno getpass http json os pathlib queue re secrets shutil "
          "socket string sys threading time urllib webbrowser").split()


# FAIL means THE APPLICATION WILL NOT RUN. WARN means it runs and something is worse
# in a way worth naming. Keeping them apart matters more than it looks: the first
# version of this called a missing browser a FAIL, while its own explanation said the
# address can be pasted into one by hand - a check that contradicts itself teaches
# people to read past its verdict, and then the real FAIL goes past too.
def say(label, verdict, detail=""):
    FINDINGS.append((label, verdict, detail))
    print(f"  {label:<26} {verdict:<9} {detail}")


def check_python():
    v = sys.version_info
    ok = v >= (3, 9)
    say("python version", "PASS" if ok else "FAIL", f"{v[0]}.{v[1]}.{v[2]}")
    # Which Python this is matters more than it looks: if the answer is "the bundled
    # one" then nothing had to be installed here, which is the whole question.
    here = os.path.dirname(os.path.abspath(sys.executable)).replace("\\", "/")
    bundled = here.rstrip("/").endswith("/runtime")
    say("which python", "INFO",
        "the runtime bundled beside the application - nothing is installed on this PC"
        if bundled else "one already on this PC")


def check_stdlib():
    missing = []
    for m in NEEDED:
        try:
            __import__(m)
        except ImportError:
            missing.append(m)
    say("standard library", "PASS" if not missing else "FAIL",
        f"{len(NEEDED)} modules needed" if not missing else "missing " + ", ".join(missing))
    try:
        __import__("tkinter")
        say("tkinter", "INFO", "present - Windows file dialogs will be used")
    except ImportError:
        say("tkinter", "INFO",
            "absent - the application serves its own folder browser, which is expected "
            "with a bundled runtime and costs nothing")


def check_loopback():
    """The shell serves the page to the browser on 127.0.0.1. Endpoint security that
    forbids a local listening socket is the one failure that stops everything, and it
    is invisible until the application is run."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    except OSError as e:
        return say("loopback socket", "FAIL", f"refused ({type(e).__name__})")
    try:
        c = socket.create_connection(("127.0.0.1", port), timeout=5)
        conn, _ = s.accept()
        conn.close()
        c.close()
        say("loopback socket", "PASS", "listened on 127.0.0.1 and connected to it")
    except OSError as e:
        say("loopback socket", "FAIL", f"could listen but not connect ({type(e).__name__})")
    finally:
        s.close()


def check_browser():
    """Something has to open the page. This asks whether a browser is REGISTERED, and
    does not open one - a check that launches a window is a check nobody runs twice."""
    try:
        import webbrowser
        b = webbrowser.get()
        say("a browser to open", "PASS", type(b).__name__.replace("Windows", "the Windows default"))
    except Exception:
        say("a browser to open", "WARN",
            "none registered - the application still runs and prints its address, "
            "which can be pasted into a browser by hand")


def check_write(where, label):
    probe = os.path.join(where, ".prap-probe-%d-%d" % (os.getpid(), int(time.time() * 1000)))
    try:
        fd = os.open(probe, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError as e:
        # Not fatal, and saying so is the point: NR-DEP-09 has the application ASK
        # where to put data when it cannot write beside itself, at launch rather than
        # at the first Save.
        return say(label, "WARN", f"refused ({type(e).__name__}) - the application "
                                  "will ask where to keep data instead")
    try:
        os.close(fd)
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass
    say(label, "PASS", "created a file and removed it")


def app_folder():
    """The folder holding PM_APP.py: this one, or the one above it."""
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (here, os.path.dirname(here)):
        if os.path.isfile(os.path.join(cand, "PM_APP.py")):
            return cand
    return here            # not beside the application: answer for where we are


def main(argv):
    where = None
    if "--where" in argv:
        i = argv.index("--where")
        if i + 1 >= len(argv):
            print("\n  --where needs a folder after it.\n")
            return 2
        where = argv[i + 1]

    print()
    print("PM_APP  PC check".ljust(42) + time.strftime("%Y-%m-%d %H:%M"))
    print("  " + "-" * 62)

    check_python()
    check_stdlib()
    check_loopback()
    check_browser()
    # Where data\ goes, which is beside PM_APP.py. This file ships in two places -
    # tools\ in the repository, and the top of the application folder, where the
    # person who actually needs it will be - so the folder is FOUND rather than
    # computed from a fixed depth.
    app = app_folder()
    check_write(app, "write beside the app")
    if where:
        if os.path.isdir(where):
            check_write(where, "write in that folder")
        else:
            say("write in that folder", "FAIL", "it is not there, or not reachable")

    bad = [f for f in FINDINGS if f[1] == "FAIL"]
    warn = [f for f in FINDINGS if f[1] == "WARN"]
    print("  " + "-" * 62)
    if bad:
        verdict = "NO - see the FAIL lines above"
    elif warn:
        verdict = f"YES, with {len(warn)} thing(s) worth knowing (WARN above)"
    else:
        verdict = "YES - this PC can run it"
    print(f"  {'verdict':<26} {verdict}")
    digest = hashlib.sha256("|".join(f"{a}={b}" for a, b, _ in FINDINGS).encode()).digest()
    alpha = "0123456789ABCDEFGHJKMNPQRSTUVWXYZ"          # no I, L, O - they misread
    code = "".join(alpha[b % 33] for b in digest[:12])
    print(f"  {'code':<26} {code[:4]}-{code[4:8]}-{code[8:12]}")
    print()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
