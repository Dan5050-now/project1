"""The layer boundaries in src/, checked rather than asserted.

Splitting a file into folders proves nothing on its own - the folders are only worth
having if the code in them respects the line they draw. Two applications will share
core/, and the moment core/ touches a browser it stops being shareable, quietly, and
nobody notices until the desktop shell will not start.

  1. core/ never touches the DOM, the window, or a file. It decides numbers, and it
     could run in any JavaScript there is - which is what NR-PAR-01 needs of it.
  2. storage/ is small. It is the seam the desktop shell replaces, and a seam that
     grows to a thousand lines is not a seam.
  3. Every part named in the build is present, in order, with no gaps - and the file it
     builds is the one that was verified.

    python tools/test_layers.py
"""

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(ROOT / "tools"))
import build_app                                                     # noqa: E402

# Names that only exist because a browser is present. If core/ mentions one of these it
# has stopped being the shared engine and become part of the web application.
BROWSER = [
    (r"\bdocument\.", "document"),
    (r"\bwindow\.", "window"),
    (r"\blocalStorage\b", "localStorage"),
    (r"\bnavigator\.", "navigator"),
    (r"\balert\(", "alert()"),
    (r"\bconfirm\(", "confirm()"),
    (r"\bURL\.createObjectURL\b", "URL.createObjectURL"),
    (r"\baddEventListener\(", "addEventListener"),
    (r"\bel\(\"", "el(\"...\")  - the DOM lookup helper"),
]
# DOMParser, TextDecoder, Blob, DecompressionStream and TextEncoder are deliberately NOT
# on that list. They are web-platform APIs, but Node has had all of them for years, so
# core/ keeps working in the desktop shell. That is the actual test - would this run
# there - not whether the name sounds like a browser.

fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{'   ' + detail if detail else ''}")
    if not ok:
        fails.append(label)


print("src/ — the layer boundaries")

# ---- 1. core/ is portable --------------------------------------------------
offenders = []
for p in sorted((SRC / "core").glob("*.js")):
    text = p.read_text(encoding="utf-8")
    # Comments discuss the browser constantly and legitimately; only code counts.
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    for pattern, name in BROWSER:
        if re.search(pattern, code):
            offenders.append(f"{p.relative_to(SRC)} uses {name}")

check(not offenders,
      "core/ touches no DOM, no window, no dialogs — so both applications can share it",
      "; ".join(offenders[:3]) if offenders else
      f"{len(list((SRC / 'core').glob('*.js')))} files clean")

# ---- 2. the seam is small, and the implementations sit behind it -----------
web_storage = list((SRC / "storage" / "web").rglob("*.js"))
web_lines = sum(len(p.read_text(encoding="utf-8").split("\n")) for p in web_storage)
check(web_storage and web_lines < 150,
      "the web shell's storage is small enough to be a seam — two functions, one that "
      "reads a file and one that writes one",
      f"{len(web_storage)} file(s), {web_lines} lines")

desk_storage = list((SRC / "storage" / "desktop").rglob("*.js"))
desk_lines = sum(len(p.read_text(encoding="utf-8").split("\n")) for p in desk_storage)
check(desk_storage and desk_lines > 200,
      "and the desktop implementation behind the same seam is where the work is",
      f"{len(desk_storage)} file(s), {desk_lines} lines: "
      + ", ".join(p.stem for p in desk_storage))

# The desktop modules are Node, not a browser. If one reaches for the DOM it has been
# written in the wrong layer, and it will fail in the main process where there is none.
NODE_ONLY = [(r"\bdocument\.", "document"), (r"\bwindow\.", "window"),
             (r"\blocalStorage\b", "localStorage")]
leaks = []
for p in desk_storage + list((SRC / "shell" / "desktop").glob("*.js")):
    code = re.sub(r"/\*.*?\*/", "", p.read_text(encoding="utf-8"), flags=re.S)
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    for pattern, name in NODE_ONLY:
        if re.search(pattern, code):
            leaks.append(f"{p.name} uses {name}")
check(not leaks,
      "the desktop storage and shell are Node only — no DOM in the main process",
      "; ".join(leaks[:3]) if leaks else
      f"{len(desk_storage) + len(list((SRC / 'shell' / 'desktop').glob('*.js')))} files clean")

core_lines = sum(len(p.read_text(encoding="utf-8").split("\n"))
                 for p in (SRC / "core").glob("*.js"))
check(core_lines > 1000,
      "and core/ is where the weight is — the shared engine, not a stub",
      f"{core_lines} lines")

# ---- 3. the build is complete and reproduces the verified file -------------
missing = [n for n in build_app.PARTS if not (SRC / n).exists()]
check(not missing, "every part the build names exists", "; ".join(missing[:3]) or
      f"{len(build_app.PARTS)} parts")

# Every file in src/ must be reached by SOMETHING. The web build takes most of them;
# the desktop build takes the same minus the two web storage functions; and the desktop
# main process requires its own modules directly rather than being concatenated.
DESKTOP_ONLY = {"storage/desktop", "shell/desktop"}
BUILT_PAGES = {"shell/desktop/index.html"}          # emitted by build_desktop.py

# The Python shell is not concatenated - it is copied into a package tree - so its
# files are named by tools/build_python_app.py rather than by build_app.PARTS. Read
# that list rather than trusting a folder name, so a Python file nobody ships still
# shows up here as an orphan.
_pyspec = importlib.util.spec_from_file_location(
    "build_python_app", ROOT / "tools" / "build_python_app.py")
build_python_app = importlib.util.module_from_spec(_pyspec)
_pyspec.loader.exec_module(build_python_app)
PYTHON_PARTS = set(build_python_app.MODULES) | {
    "shell/python/bridge.js", "shell/python/chrome.css", "shell/python/chrome.html"}

reachable = set(build_app.PARTS) | BUILT_PAGES | PYTHON_PARTS
orphans = sorted(
    n for n in (str(p.relative_to(SRC)).replace("\\", "/")
                for p in SRC.rglob("*") if p.is_file())
    if n not in reachable and not any(n.startswith(d + "/") for d in DESKTOP_ONLY))
check(not orphans,
      "and nothing in src/ is left out of a build — an unbuilt file is a file nobody runs",
      "; ".join(orphans[:3]) if orphans else
      f"{len(build_app.PARTS)} web parts, the desktop modules, "
      f"{len(PYTHON_PARTS)} Python-shell parts")

# NR-DEP-05, and it is the requirement the whole delivery route rests on: the Python
# shell must run on a machine where nobody may install anything. One import of a
# package that is not in the standard library turns "double-click it" into "raise a
# ticket", so the imports are read rather than promised.
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {"pmapp"}
third_party = []
for rel in sorted(build_python_app.MODULES):
    src_text = (SRC / rel).read_text(encoding="utf-8")
    for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", src_text,
                         re.M):
        mod = m.group(1)
        if mod not in STDLIB and not src_text[m.start():m.end()].lstrip().startswith(
                ("from .", "from ..")):
            third_party.append(f"{rel} imports {mod}")
check(not third_party,
      "the Python shell imports nothing but the standard library (NR-DEP-05)",
      "; ".join(third_party[:3]) if third_party else
      f"{len(build_python_app.MODULES)} modules, no pip install")

py_dom = [rel for rel in build_python_app.MODULES
          if re.search(r"\bdocument\.|\bwindow\.", (SRC / rel).read_text(encoding="utf-8"))]
check(not py_dom,
      "and it decides where files go, never what a number is",
      "; ".join(py_dom[:3]) if py_dom else
      f"{len(build_python_app.MODULES)} modules, no page in any of them")

built = build_app.render()
current = (ROOT / "app" / "PRAP.html").read_text(encoding="utf-8")
check(built == current,
      "the file the build produces is byte-identical to the one the 13 suites verified",
      f"{len(built):,} bytes")

layers = {n.split("/")[0] for n in build_app.PARTS}
check(layers == {"core", "ui", "storage", "shell"},
      "and the four layers the plan names are the four that exist",
      ", ".join(sorted(layers)))

print()
print("FAILURES: " + (", ".join(fails) if fails else "none"))
sys.exit(1 if fails else 0)
