"""Put a Python beside the application, so a PC that has none can still run it.

    python tools/bundle_runtime.py python-3.14.7-embed-amd64.zip

WHAT THIS IS FOR. Some staff PCs have no Python and no way to get one without a
request to IT. Windows publishes an EMBEDDABLE PACKAGE for exactly this: a zip of
python.exe, its DLLs and the standard library, which is unpacked rather than
installed. It touches no registry key, needs no administrator, changes no PATH, and
does not disturb a Python already on the machine. Deleting the folder removes it.

    https://www.python.org/downloads/windows/   ->  "Windows embeddable package"

The zip is not downloaded here. It comes through whatever channel the company allows,
and this tool takes the file once it has arrived.

THREE THINGS MAKE THIS WORK, AND ALL THREE ARE ALREADY TRUE:

  * The application imports nothing but the standard library (NR-DEP-05, enforced by
    tools/test_layers.py), so the missing pip does not matter.
  * The embeddable package HAS NO TKINTER - and the shell already expects that, and
    serves its own folder browser in the page instead. Nothing is lost but the
    Windows file dialog.
  * The embeddable package fixes sys.path with a ._pth file and ignores PYTHONPATH,
    which normally breaks `import pmapp`. PM_APP.py inserts its own folder itself, so
    it does not. That line is CHECKED below rather than assumed - it is load-bearing
    from a distance, and the kind of thing a tidy-up removes.

    python tools/bundle_runtime.py <zip>              into dist/PM_APP_py
    python tools/bundle_runtime.py <zip> --into <dir> into somewhere else
    python tools/bundle_runtime.py <zip> --replace    overwrite a runtime already there
    python tools/bundle_runtime.py <zip> --zip        and package it for handing out
    python tools/bundle_runtime.py <zip> --check-with <python>
                                                     ask THAT interpreter the checks,
                                                     instead of the bundled python.exe
                                                     - which is how they get run at
                                                     all on anything but Windows

EVERY CHECK BELOW HAS TO COME BACK BY ITSELF. Starting the application is not a
check: it serves a page, opens a browser and then waits for a person, so it never
returns - and a check that never returns takes the packaging down with it. That is
not hypothetical. An earlier version of this file asked the application for its
version before the option existed; the application ignored the unknown word, started
normally, and the run died on a timeout with no zip written and a login page on the
screen. Ask questions that answer and stop: -c one-liners, and PM_APP.py --version.

PACKAGE IT FROM HERE, NOT WITH build_python_app.py --zip. That one REBUILDS before it
packages, and a rebuild empties the folder - runtime and all - so the zip it writes has
no runtime in it and says nothing about that. It is the obvious command to reach for and
it silently produces the wrong thing, which is why the packaging lives here instead: this
one zips the folder as it stands, with the runtime in it, under a name that says so.
"""

import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_APP = ROOT / "dist" / "PM_APP_py"
NEEDED_LINE = "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))"


def die(*lines):
    print()
    for ln in lines:
        print("  " + ln)
    print()
    raise SystemExit(1)


def looks_embeddable(names):
    """An embeddable package, and not one of the things people reach for instead.

    The full installer is an .exe; the "Windows installer" zip and a source tarball
    both carry a Lib\\ tree. Saying which of those arrived is the difference between
    one more download and half an hour."""
    has_exe = any(n.lower() == "python.exe" for n in names)
    has_stdlib_zip = any(re.fullmatch(r"python\d+\.zip", n.lower()) for n in names)
    has_pth = any(n.lower().endswith("._pth") for n in names)
    has_lib_tree = any(n.lower().startswith(("lib/", "lib\\")) for n in names)
    return has_exe and has_stdlib_zip and has_pth and not has_lib_tree


def version_of(names):
    for n in names:
        m = re.fullmatch(r"python(\d)(\d+)\.zip", n.lower())
        if m:
            return f"{m.group(1)}.{m.group(2)}"
    return None


CHECK_TIMEOUT = 60
STDLIB = ("base64 datetime errno getpass http json os pathlib queue re secrets "
          "shutil socket string sys threading time urllib webbrowser").split()


def run_one(exe, args, timeout=CHECK_TIMEOUT):
    """Run one question and always come back - with an answer, or with why not.

    Nothing a check does may end the run. A hang, a missing DLL, a file that is not
    an executable at all: each of those is something to PRINT, not something to fall
    over on, because the packaging below still has to happen either way."""
    try:
        r = subprocess.run([str(exe), *args], capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return False, (f"no answer in {timeout} seconds - it did not stop by itself, "
                       f"so it was stopped")
    except OSError as e:
        return False, f"could not be run - {e}"
    out = (r.stdout or "").strip() or (r.stderr or "").strip()
    return r.returncode == 0, out or "(no output)"


def verify(exe, app):
    """Four questions for an interpreter, as a list of (label, what to print, passed).

    THE INTERPRETER IS AN ARGUMENT so that this can be run anywhere. main() passes
    the bundled python.exe, on Windows, where that is the only thing worth asking;
    the tests pass the Python they are running on, on any machine. The check that
    shipped broken was inside `if os.name == "nt"`, so no test on this side could
    ever reach it - being callable is the point of this function, not tidiness.

    tkinter is asked about but never counted as a failure: the embeddable package
    has none, the shell knows that and serves its own folder browser instead."""
    out = []

    ok, txt = run_one(exe, ["-c",
                            "import sys; print('.'.join(map(str, sys.version_info[:3])))"])
    out.append(("it runs", txt if ok else "NO - " + txt, ok))

    ok, txt = run_one(exe, ["-c", "import " + ", ".join(STDLIB) + "; print('all present')"])
    out.append(("stdlib", txt if ok else "MISSING - " + txt, ok))

    ok, _ = run_one(exe, ["-c", "import tkinter"])
    out.append(("tkinter", "present" if ok else
                "absent - the app serves its own folder browser instead, as expected",
                True))

    entry = app / "PM_APP.py"
    launch = app / "pmapp" / "shell" / "launch.py"
    if not launch.is_file() or "--version" not in launch.read_text(encoding="utf-8"):
        # Older build in the folder. Asking anyway would START it and hang, which is
        # the very thing this file exists to not do.
        out.append(("START", "not checked - this build has no --version to ask with; "
                             "rebuild with tools/build_python_app.py", True))
        return out
    ok, txt = run_one(exe, [str(entry), "--version"])
    out.append(("START", txt if ok else "NO - " + (txt.splitlines()[-1] if txt else txt), ok))
    return out


def main(argv):
    rest, flags, app, check_with = [], set(), DEFAULT_APP, None
    it = iter(argv[1:])
    for a in it:
        if a == "--into":
            nxt = next(it, None)
            if nxt is None:
                die("--into needs a folder after it.")
            app = pathlib.Path(nxt)
        elif a == "--check-with":
            nxt = next(it, None)
            if nxt is None:
                die("--check-with needs the path of a python after it.")
            check_with = pathlib.Path(nxt)
        elif a.startswith("--"):
            flags.add(a)
        else:
            rest.append(a)
    if not rest:
        print(__doc__.strip().splitlines()[0])
        print("\n    python tools/bundle_runtime.py <embeddable zip>")
        return 2
    src = pathlib.Path(rest[0])

    if not src.is_file():
        die(f"{src} is not there.")
    if not zipfile.is_zipfile(src):
        die(f"{src.name} is not a zip file.",
            "The embeddable package is a .zip - the one whose name ends -embed-amd64.zip.",
            "The .exe on that page is the installer, which is the other thing.")
    if not app.is_dir():
        die(f"{app} is not there. Build the application first:",
            "    python tools/build_python_app.py")
    if not (app / "PM_APP.py").is_file():
        die(f"{app} does not look like the application - no PM_APP.py in it.")

    entry = (app / "PM_APP.py").read_text(encoding="utf-8")
    if NEEDED_LINE not in entry:
        die("PM_APP.py no longer puts its own folder on sys.path.",
            "An embeddable Python fixes sys.path from its ._pth file and ignores",
            "PYTHONPATH, so without that line `import pmapp` fails and the",
            "application does not start. Nothing has been unpacked.",
            "",
            f"    expected: {NEEDED_LINE}")

    with zipfile.ZipFile(src) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        if not looks_embeddable(names):
            die(f"{src.name} is not a Windows embeddable package.",
                "It should contain python.exe, pythonXY.zip and a ._pth file, and no",
                "Lib\\ folder. What arrived has:",
                "    " + ", ".join(sorted(names)[:6]) + (" ..." if len(names) > 6 else ""))
        ver = version_of(names)
        runtime = app / "runtime"
        if runtime.exists():
            if "--replace" not in flags:
                die(f"{runtime} is already there.",
                    "Run again with --replace to overwrite it.")
            shutil.rmtree(runtime)
        runtime.mkdir(parents=True)
        z.extractall(runtime)

    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    files = sorted(p for p in runtime.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in files)

    print()
    print(f"Runtime bundled into {runtime}")
    print(f"  from      {src.name}")
    print(f"  sha256    {digest}")
    print(f"  python    {ver or 'unknown'}   (the application needs 3.9 or newer)")
    print(f"  files     {len(files)}, {size / 1048576:.1f} MB")

    # If this IS Windows, do not describe the result - ask it. --check-with names a
    # different interpreter to ask, which is the only way these checks can be run at
    # all on a machine where the bundled python.exe is just a file sitting there.
    exe = runtime / "python.exe"
    failed = []
    asking = check_with or (exe if os.name == "nt" and exe.is_file() else None)
    if asking:
        for label, text, ok in verify(asking, app):
            print(f"  {label:<9} {text}")
            if not ok:
                failed.append(label)
    else:
        print( "  not run   this is not Windows, so python.exe was unpacked and")
        print( "            checked for shape only. Run tools/check_pc.py with it on")
        print(f"            a Windows PC:  runtime\\python.exe tools\\check_pc.py")

    print()
    print("  Give people the whole folder. PM_APP.cmd finds this runtime by itself,")
    print("  and nothing is installed on their PC.")
    if "--zip" in flags:
        version = "unknown"
        vt = app / "version.txt"
        if vt.is_file():
            version = vt.read_text(encoding="utf-8").strip() or version
        out = app.parent / f"PM_APP_python_v{version}_with_runtime.zip"
        skip_dirs = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
        wanted = [q for q in sorted(app.rglob("*")) if q.is_file()
                  and not any(part in skip_dirs for part in q.relative_to(app).parts)
                  and q.suffix not in {".pyc", ".pyo"}]
        dropped = sum(1 for q in app.rglob("*") if q.is_file()) - len(wanted)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for f in wanted:
                z.write(f, pathlib.Path("PM_APP") / f.relative_to(app))
        print()
        print(f"Packaged  {out.name}")
        print(f"  size    {out.stat().st_size / 1048576:.1f} MB")
        print(f"  files   {len(wanted)}"
              + (f", and {dropped} build dropping(s) left out" if dropped else ""))
        print(f"  sha256  {hashlib.sha256(out.read_bytes()).hexdigest()}")
        print( "  This is the one to hand out - the runtime is inside it.")

    print()
    print("  Rebuilding the application empties that folder, runtime and all. Run this")
    print("  again after any  python tools/build_python_app.py .")
    print()
    if failed:
        # Said last, and after the packaging, because the packaging is the part that
        # must not be skipped - and because the last line is the one that gets read.
        print(f"  NOT READY TO HAND OUT: {', '.join(failed)} did not pass. The folder")
        print( "  and any zip above were still written, so nothing is lost - but find")
        print( "  out what that answer means before anybody else is given this.")
        print()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
