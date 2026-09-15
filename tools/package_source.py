"""Package the development source - src/ and tools/ - as one zip of plain text.

Asked for more than once, so it is a tool rather than a command somebody retypes. What
goes in is what is WRITTEN; everything generated from it is left out, which is the whole
distinction the archive is for:

    in      src/     the application by layer - core / ui / storage / shell
            tools/   the builders, the reference implementation, the checker, the suites
    out     app/PRAP.html, docs/, templates/, dist/   all built from the above
            __pycache__ and .pyc                      build droppings

THE ARCHIVE IS CHECKED BEFORE IT IS WRITTEN, not trusted afterwards. It is extracted to a
temporary folder and `python tools/build_app.py` is run there; unless the result is
BYTE-IDENTICAL to the committed app/PRAP.html, nothing is written and the reason is
printed. An archive of source that cannot rebuild the application is not a deliverable,
and the way to know is to try it rather than to reason about it.

    python tools/package_source.py
    python tools/package_source.py --no-verify     skip the rebuild (faster, weaker)

Output: dist/PRAP_source_src_tools.zip
"""

import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "PRAP_source_src_tools.zip"
TREES = ("src", "tools")

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_SUFFIX = {".pyc", ".pyo"}

NOTE = """PRAP / Project Management APP - development source
==================================================

WHAT IS IN HERE

  src/     the application, split by layer. core/ decides the numbers and touches
           no DOM; ui/ draws them; storage/ moves bytes; shell/ is the surround -
           web, desktop and python. app/PRAP.html is BUILT from these parts and is
           not in this archive.
  tools/   everything that builds, checks and tests the above: the document
           generators, the reference implementation (prap_io.py), the consistency
           checker, and the test suites.

WHAT IS NOT IN HERE

  The built application (app/PRAP.html), the generated documents (docs/), the
  workbooks (templates/) and the packaged desktop editions (dist/). All of them
  are produced from what IS here - nothing in this archive is generated, and
  nothing generated is in it.

HOW TO REBUILD THE APPLICATION FROM THIS

  python tools/build_app.py            -> app/PRAP.html, from src/ in 29 parts
  python tools/build_python_app.py     -> dist/PM_APP_py, the desktop edition
  python tools/check_consistency.py    -> holds every document to every other
  python tools/test_<name>.py          -> 38 suites, each standalone

  build_app.py rebuilds app/PRAP.html BYTE-IDENTICALLY from src/, and this archive
  was not written until that was demonstrated from a fresh extract of itself.

NEEDS

  Python 3.9+ for the shells. The generators additionally need openpyxl, and the
  browser-driving suites need playwright. The APPLICATION itself needs neither:
  it is one HTML file with no third-party library of any kind, including its own
  hand-written .xlsx reader and writer.

No executable is included. Everything here is plain text.
"""


def collect():
    out = []
    for top in TREES:
        for p in sorted((ROOT / top).rglob("*")):
            if not p.is_file():
                continue
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.suffix in SKIP_SUFFIX:
                continue
            out.append(p)
    return out


# A fixed timestamp for every entry, so the archive is REPRODUCIBLE: the same source
# tree gives the same bytes and therefore the same sha256, on any machine and after any
# checkout. Without it the zip carries each file's mtime, which a fresh clone or a
# container restart rewrites - so two archives of identical content hashed differently
# and the hash said nothing about the content. It happened between two builds of this
# very file, one sha quoted to the reviewer and a different one produced an hour later
# from the same commit. 1980-01-01 is the earliest a zip can store.
EPOCH = (1980, 1, 1, 0, 0, 0)


def write(files, dst):
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        def add(name, data):
            info = zipfile.ZipInfo(name, date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16          # and fixed permissions with it
            # compresslevel HERE, not on the ZipFile: writestr() with a ZipInfo ignores
            # the archive's setting and falls back to the default, which cost 3 KB.
            z.writestr(info, data, compresslevel=9)

        add("READ ME FIRST.txt", NOTE.encode("utf-8"))
        for p in files:                                # collect() already sorts
            add(str(p.relative_to(ROOT)), p.read_bytes())


def verify(dst):
    """Extract it somewhere else and rebuild the application from it.

    The check that matters is BYTE-IDENTITY against the committed file, because that is
    the guarantee the repository already makes about src/ - if the archive cannot keep
    it, the archive is missing something.
    """
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="prap-src-"))
    try:
        with zipfile.ZipFile(dst) as z:
            z.extractall(tmp)
        r = subprocess.run([sys.executable, str(tmp / "tools" / "build_app.py")],
                           cwd=tmp, capture_output=True, text=True)
        if r.returncode != 0:
            return False, (r.stdout + r.stderr).strip().splitlines()[-1][:200]
        rebuilt = tmp / "app" / "PRAP.html"
        if not rebuilt.exists():
            return False, "the build reported success but wrote no app/PRAP.html"
        a, b = rebuilt.read_bytes(), (ROOT / "app" / "PRAP.html").read_bytes()
        if a != b:
            return False, (f"rebuilt {len(a):,} bytes, committed {len(b):,} - "
                           f"NOT byte-identical")
        return True, f"{len(a):,} bytes, byte-identical to the committed app/PRAP.html"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(check=True):
    files = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    staged = OUT.with_suffix(".zip.staged")
    write(files, staged)

    if check:
        ok, detail = verify(staged)
        print(f"  {'ok  ' if ok else 'FAIL'} rebuilds from a fresh extract   {detail}")
        if not ok:
            staged.unlink(missing_ok=True)
            print("\nNothing written. Fix the above and run again.")
            return 1

    staged.replace(OUT)
    size = OUT.stat().st_size
    counts = {t: sum(1 for p in files if p.parts[len(ROOT.parts)] == t) for t in TREES}
    print(f"\nPackaged  {OUT.relative_to(ROOT)}")
    print(f"  {len(files)} files ("
          + ", ".join(f"{n} under {t}/" for t, n in counts.items())
          + ") + READ ME FIRST.txt")
    print(f"  size    {size:,} bytes ({size / 1024:.0f} KB)")
    print(f"  sha256  {hashlib.sha256(OUT.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--no-verify" not in sys.argv))
