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

# ---- 2. the seam is small --------------------------------------------------
storage = list((SRC / "storage").rglob("*.js"))
lines = sum(len(p.read_text(encoding="utf-8").split("\n")) for p in storage)
check(storage and lines < 150,
      "storage/ is small enough to be a seam the desktop shell can replace",
      f"{len(storage)} file(s), {lines} lines: " + ", ".join(p.stem for p in storage))

core_lines = sum(len(p.read_text(encoding="utf-8").split("\n"))
                 for p in (SRC / "core").glob("*.js"))
check(core_lines > 1000,
      "and core/ is where the weight is — the shared engine, not a stub",
      f"{core_lines} lines")

# ---- 3. the build is complete and reproduces the verified file -------------
missing = [n for n in build_app.PARTS if not (SRC / n).exists()]
check(not missing, "every part the build names exists", "; ".join(missing[:3]) or
      f"{len(build_app.PARTS)} parts")

orphans = sorted({str(p.relative_to(SRC)).replace("\\", "/")
                  for p in SRC.rglob("*") if p.is_file()} - set(build_app.PARTS))
check(not orphans,
      "and nothing in src/ is left out of it — an unbuilt file is a file nobody runs",
      "; ".join(orphans[:3]) if orphans else f"{len(build_app.PARTS)} parts, all built")

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
