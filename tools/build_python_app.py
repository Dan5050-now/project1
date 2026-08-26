"""Build the Python shell of Project Management APP from the same src/ as the rest.

    core/ + ui/ + shell/python/ + storage/python/   ->   dist/PM_APP_py/

Everything above the storage line is the web application, built from the same parts
in the same order (decision N-05). What differs is the shell around it, and one
thing inside it:

  * the window chrome - a menu drawn in the page, because there is no Electron menu
    bar to draw one for us, plus the status strip and the file browser
  * a bridge that routes the file operations through 127.0.0.1 instead of a picker
  * NO src/storage/web/load.js. That file is the browser's file interface, which is
    the thing a company control stops on the target machine (R-N21). It is left out
    rather than left in and broken.

storage/web/export.js stays exactly where it is: a download is not an upload, the
control does not touch it, and every check it performs before writing a workbook is
worth keeping.

    python tools/build_python_app.py            build into dist/PM_APP_py
    python tools/build_python_app.py --zip      and package it for e-mail

Output: dist/PM_APP_py/ and, with --zip, dist/PM_APP_python_v<version>.zip
"""

import argparse
import hashlib
import importlib.util
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "dist" / "PM_APP_py"
VERSION = "0.7"

_spec = importlib.util.spec_from_file_location("build_app", ROOT / "tools" / "build_app.py")
build_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_app)

# The browser's file interface. Left out on purpose - see the module docstring.
WEB_ONLY = {"storage/web/load.js"}

# src path -> package path. The repository keeps layers side by side; a shipped
# Python program needs a package tree, and this is the whole of the difference.
MODULES = {
    "storage/python/timefmt.py": "pmapp/storage/timefmt.py",
    "storage/python/workspace.py": "pmapp/storage/workspace.py",
    "storage/python/claim.py": "pmapp/storage/claim.py",
    "shell/python/paths.py": "pmapp/shell/paths.py",
    "shell/python/files.py": "pmapp/shell/files.py",
    "shell/python/server.py": "pmapp/shell/server.py",
    "shell/python/launch.py": "pmapp/shell/launch.py",
}

ENTRY = '''"""Project Management APP - start here.

Double-click this file, or run it from a command prompt:

    python PM_APP.py

It opens in your browser, at an address only this machine can reach. Keep the
console window open while you work; closing it stops the application.
"""

import os
import sys

if sys.version_info < (3, 9):
    raise SystemExit(
        "Project Management APP needs Python 3.9 or newer.\\n"
        f"This is Python {sys.version.split()[0]}.")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pmapp.shell.launch import main            # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
'''

READ_ME = """PROJECT MANAGEMENT APP - Python edition
=======================================

WHY THIS VERSION EXISTS

  Two company controls shaped it, and neither is worked around:

    * an executable cannot be sent through e-mail. This edition is plain Python
      text - you can read every line of it before running it.
    * data cannot be fed into a web page through the browser's file picker. This
      edition never asks the browser for a file. You choose a path, Python opens
      the file, and the figures appear. There is no upload, so there is nothing
      for an upload control to stop.


WHAT YOU NEED

  Python 3.9 or newer. You said 3.14, which is fine.
  Check with:   python --version


HOW TO START IT

  1. Extract this whole folder somewhere of your own - your Documents folder is
     ideal. Keep the folders inside it as they are.
  2. Double-click PM_APP.py.
       If Windows asks what to open it with, choose Python.
       From a command prompt this also works:   python PM_APP.py
  3. A black console window appears and your browser opens the application.
  4. KEEP THE CONSOLE WINDOW OPEN while you work. Closing it stops the
     application; that is how you shut it down.


WHERE YOUR DATA GOES

  In a folder called data\\ beside PM_APP.py, under your own account name. It is
  never sent anywhere. Help -> About shows the exact path.

  Delete this folder and the application is gone. It installs nothing, writes
  nothing to the registry, and leaves nothing behind.


HOW TO GET YOUR SOURCE DATA IN

  File -> Import source data...      choose your .xlsx workbook
  File -> Import from a folder...    same thing, with a folder list inside the
                                     page - use this for a network share, or if
                                     the first one does nothing

  Both read the file with Python. Neither goes near the browser's file picker.


HOW TO GET DATA OUT

  File -> Export to Excel            saves to your Downloads folder
  File -> Export to a folder...      saves where you choose


IS IT SAFE TO RUN?

  It listens on 127.0.0.1 only, which is this machine talking to itself; nothing
  on the network can reach it, and Windows Firewall does not prompt for it. The
  port is chosen fresh each time, and every request must carry a key generated
  at start-up and never written to disk.

  It uses nothing but the Python standard library. There is no pip install, no
  download, and no network access of any kind.


IF SOMETHING GOES WRONG

  Send back what the console window says. That is where every error is written.
"""


def page():
    """The application page: the same parts, in the same order, minus the browser's
    file interface, plus this shell's chrome."""
    chrome_css = (SRC / "shell" / "python" / "chrome.css").read_text(encoding="utf-8")
    chrome_html = (SRC / "shell" / "python" / "chrome.html").read_text(encoding="utf-8")
    bridge = (SRC / "shell" / "python" / "bridge.js").read_text(encoding="utf-8")
    # The difference report is wired into THIS shell only. Its engine lives in
    # core/06a_diff.js and is shared; the screen is not, because the web application
    # is feature-frozen (N-06) and has no workspace to merge into.
    diff = (SRC / "shell" / "python" / "importdiff.js").read_text(encoding="utf-8")

    parts = []
    for name in build_app.PARTS:
        if name in WEB_ONLY:
            continue
        text = (SRC / name).read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        if name == "shell/web/page.head.html":
            text = text.replace(
                "<title>PRAP — Project Resource Assignment Program</title>",
                '<title>Project Management APP</title>\n'
                '<meta name="pm-key" content="__PM_KEY__">', 1)
        if name == "ui/style.css":
            text += chrome_css
        if name == "shell/web/page.body.html":
            text = text.replace('<div class="wrap">', chrome_html + '\n<div class="wrap">', 1)
        if name == "shell/web/page.tail.html":
            text = (f"<script>\n{diff}</script>\n"
                    f"<script>\n{bridge}</script>\n" + text)
        parts.append(text)

    html = "".join(parts).replace(
        "<h1>Project Resource Assignment Program</h1>",
        "<h1>Project Management APP</h1>", 1)
    return html, len(parts)


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "app").mkdir(parents=True)
    (OUT / "pmapp" / "shell").mkdir(parents=True)
    (OUT / "pmapp" / "storage").mkdir(parents=True)

    html, n = page()
    (OUT / "app" / "index.html").write_text(html, encoding="utf-8")

    for src, dst in MODULES.items():
        (OUT / dst).write_text((SRC / src).read_text(encoding="utf-8"), encoding="utf-8")

    for pkg, what in (("pmapp", "Project Management APP - the Python shell."),
                      ("pmapp/shell", "The shell: where files go, and how the page "
                                      "reaches them."),
                      ("pmapp/storage", "Storage: workspaces, versions, journals, "
                                        "the write claim.")):
        (OUT / pkg / "__init__.py").write_text(f'"""{what}"""\n', encoding="utf-8")

    (OUT / "PM_APP.py").write_text(ENTRY, encoding="utf-8")
    (OUT / "version.txt").write_text(VERSION + "\n", encoding="utf-8")
    (OUT / "READ ME FIRST.txt").write_text(READ_ME, encoding="utf-8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    total = sum(p.stat().st_size for p in files)
    print(f"Built  {OUT.relative_to(ROOT)}")
    print(f"  page          app/index.html   {len(html):,} bytes from {n} parts "
          f"({len(WEB_ONLY)} web-only part left out)")
    py = [p for p in OUT.rglob("*.py")]
    print(f"  python        {len(py)} files, "
          f"{sum(p.stat().st_size for p in py):,} bytes")
    print(f"  altogether    {len(files)} files, {total / 1024:.0f} KB")
    return files


def package(files):
    zip_path = ROOT / "dist" / f"PM_APP_python_v{VERSION}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            z.write(p, pathlib.Path("PM_APP") / p.relative_to(OUT))
    h = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"\nPackaged  {zip_path.relative_to(ROOT)}")
    print(f"  size    {zip_path.stat().st_size / 1024:.0f} KB")
    print(f"  sha256  {h}")
    return zip_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--zip", action="store_true", help="package it for e-mail")
    args = ap.parse_args()
    files = build()
    if args.zip:
        package(files)


if __name__ == "__main__":
    main()
