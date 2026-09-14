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


def main(argv):
    rest, flags, app = [], set(), DEFAULT_APP
    it = iter(argv[1:])
    for a in it:
        if a == "--into":
            nxt = next(it, None)
            if nxt is None:
                die("--into needs a folder after it.")
            app = pathlib.Path(nxt)
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

    # If this IS Windows, do not describe the result - run it.
    exe = runtime / "python.exe"
    if os.name == "nt" and exe.is_file():
        def ran(*a):
            r = subprocess.run([str(exe), *a], capture_output=True, text=True, timeout=120)
            return r.returncode == 0, (r.stdout or r.stderr).strip()
        ok, out = ran("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
        print(f"  it runs   {out if ok else 'NO - ' + out}")
        mods = ("base64 datetime errno getpass http json os pathlib queue re secrets "
                "shutil socket string sys threading time urllib webbrowser").split()
        ok2, out2 = ran("-c", "import " + ", ".join(mods) + "; print('all present')")
        print(f"  stdlib    {out2 if ok2 else 'MISSING - ' + out2}")
        ok3, _ = ran("-c", "import tkinter")
        print("  tkinter   " + ("present" if ok3 else
              "absent - the app serves its own folder browser instead, as expected"))
        ok4, out4 = ran(str(app / "PM_APP.py"), "--version")
        if not ok4:
            print(f"  START     NO - {out4.splitlines()[-1] if out4 else 'no output'}")
    else:
        print( "  not run   this is not Windows, so python.exe was unpacked and")
        print( "            checked for shape only. Run tools/check_pc.py with it on")
        print(f"            a Windows PC:  runtime\\python.exe tools\\check_pc.py")

    print()
    print("  Give people the whole folder. PM_APP.cmd finds this runtime by itself,")
    print("  and nothing is installed on their PC.")
    print()
    print("  Rebuilding the application empties that folder, runtime and all. Run this")
    print("  again after any  python tools/build_python_app.py .")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
