"""Package Project Management APP for Windows, from Linux.

Produces the folder the plan describes and a zip of it - the delivery form decided at
N-14, a plain folder that runs in place rather than a self-extracting executable:

    PM_APP\\
      PM_APP.exe            Electron's launcher, renamed
      version.txt
      resources\\app\\       our source: core, ui, storage, shell, and the built page
      resources\\*.pak       Chromium's own resources
      ...
      (NO data\\ - so extracting an update over an existing folder cannot touch a plan)

    python tools/package_windows.py

Output: dist/PM_APP_v<ver>_win64.zip

WHAT THIS IS NOT: a tested Windows build. It is assembled on Linux from the official
win32-x64 distribution, and nothing here has ever run on Windows. That is R-N06, and it
is why N5.7 - launching it on a real company PC - is a task on the plan rather than an
afterthought. This package exists so that task can happen.
"""

import hashlib
import pathlib
import shutil
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STAGE = DIST / "PM_APP"
VERSION = "0.1"
ELECTRON = "43.4.0"

# What goes into resources/app. Only what the application runs - no tests, no
# documents, no dummy data. A package should contain the product and nothing else.
APP_FILES = [
    "package.json",
    "src/core", "src/ui", "src/storage/desktop", "src/shell/desktop",
]


def fetch_electron():
    out = subprocess.run(
        [shutil.which("node"), "-e",
         "const {downloadArtifact}=require('@electron/get');"
         f"downloadArtifact({{version:'{ELECTRON}',platform:'win32',arch:'x64',"
         "artifactName:'electron'}).then(p=>console.log(p));"],
        cwd=ROOT, capture_output=True, text=True, check=True)
    return pathlib.Path(out.stdout.strip())


def main():
    # The renderer page has to exist before it is packaged.
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_desktop.py")],
                   check=True, capture_output=True)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    print("unpacking the Windows distribution…")
    with zipfile.ZipFile(fetch_electron()) as z:
        z.extractall(STAGE)

    # The launcher carries the product's name, because that is what a user sees in the
    # taskbar, in Task Manager, and in whatever their security software reports.
    (STAGE / "electron.exe").rename(STAGE / "PM_APP.exe")

    # Files Electron ships that are not ours to hand anybody.
    for junk in ("LICENSE", "LICENSES.chromium.html", "version"):
        p = STAGE / junk
        if p.exists():
            p.unlink()

    app = STAGE / "resources" / "app"
    app.mkdir(parents=True)
    for rel in APP_FILES:
        src, dst = ROOT / rel, app / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    # The built renderer is gitignored, so it is copied explicitly.
    shutil.copy2(ROOT / "src/shell/desktop/index.html", app / "src/shell/desktop/index.html")

    (STAGE / "version.txt").write_text(f"{VERSION}\n", encoding="utf-8")
    (STAGE / "READ ME FIRST.txt").write_text(READ_ME, encoding="utf-8")

    DIST.mkdir(exist_ok=True)
    zip_path = DIST / f"PM_APP_v{VERSION}_win64.zip"
    print("zipping…")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(STAGE.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(DIST))

    sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    size = zip_path.stat().st_size
    print(f"\nWritten: {zip_path.relative_to(ROOT)}")
    print(f"  {size / 1e6:.1f} MB   sha256 {sha}")
    print(f"  unpacked: {sum(f.stat().st_size for f in STAGE.rglob('*') if f.is_file()) / 1e6:.0f} MB")
    print(f"  Electron {ELECTRON} win32-x64, assembled on Linux and NEVER RUN ON WINDOWS")


READ_ME = """Project Management APP (PM_APP) - test package v0.1
==================================================

WHAT THIS IS
    An early build, for one purpose: to find out whether your machine will let you
    run it at all. It is not finished software and it is not for planning with yet.

WHAT TO DO
    1. Extract this zip into a folder of your own - your Documents or your desktop.
       Do not put it in Program Files; it is not installed and does not want to be.
    2. Open the folder and double-click PM_APP.exe.
    3. Windows will probably say "Windows protected your PC" and name an unknown
       publisher. That is expected: the file is not code-signed. If you are willing,
       click "More info" and then "Run anyway".
    4. A window should open, titled Project Management APP, showing the same tabs and
       charts as the web application.
    5. Close it, and delete the whole folder. Nothing is left behind anywhere else.

PLEASE TELL ME WHAT HAPPENED
    * Did the zip extract, or was it blocked?
    * Did the SmartScreen warning appear, and did "Run anyway" work?
    * Did anti-virus quarantine or delete anything?
    * Did the window open, and how long did it take?
    * Anything else your machine said.

    A "no" at any step is a useful answer, not a failed test. It is exactly what this
    package exists to find out.

BEFORE YOU RUN IT
    Tell whoever looks after security or IT that you are doing this. A large unsigned
    executable arriving by e-mail and being run from a user folder is precisely the
    pattern their tools watch for, and it is better that they hear it from you first
    than that they see it on a dashboard afterwards.

WHAT IT DOES, AND DOES NOT DO
    Does      opens a window, shows the tabs, charts and tables, keeps everything it
              writes inside this folder.
    Does not  read your real data unless you ask it to, contact any network, write to
              the registry, add a Start-menu entry, or install anything.

    Deleting the folder removes it completely.

CAVEAT
    This package was assembled on Linux from the official Windows build of Electron.
    It has never been run on Windows by anybody. If it fails immediately, that is
    information too - please say so rather than assuming you did something wrong.
"""


if __name__ == "__main__":
    main()
