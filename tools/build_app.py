"""Build app/PRAP.html from the sources in src/.

The web application stops being a hand-written file and becomes a build output. That is
the whole of task N2.1: the same source tree can then also be built into the desktop
application, so the two can never disagree about a number (decision N-05).

    python tools/build_app.py            write app/PRAP.html
    python tools/build_app.py --check    verify the committed file matches, write nothing

--check is the guarantee this refactor rests on. The parts are concatenated in the order
they were carved, so the output is BYTE-IDENTICAL to the file that passed all thirteen
suites - not merely equivalent to it. An equivalent file has to be argued for; an
identical one does not.

Layers, and why the boundaries are where they are:

    core/       decides numbers    - parse, validate, derive periods, calculate load,
                                     read and write xlsx and JSON. No DOM, no files.
    ui/         draws them         - tables, charts, filters, the provisional-edit model
    storage/    puts bytes         - two functions: one reads a file, one writes one.
                somewhere            This is the whole of what the desktop shell replaces
    shell/web/  wires it to a      - the page markup, the event wiring, the build target
                browser
"""

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "app" / "PRAP.html"

# In build order. core before ui before storage before shell is not merely tidy: it is
# the order the original file already had, so the output is identical rather than
# equivalent. Anything that must move later is a change of behaviour, and will show up
# here as a --check failure rather than as a surprise in the browser.
PARTS = [
    "shell/web/page.head.html",
    "ui/style.css",
    "shell/web/page.body.html",
    "core/00_meta.js",
    "core/01_xlsx_read.js",
    "core/02_xlsx_write.js",
    "core/03_parse.js",
    "core/04_derive.js",
    "core/05_model.js",
    "core/06_calculate.js",
    "ui/07_state.js",
    "ui/08_render.js",
    "ui/09_charts.js",
    "ui/10_tables.js",
    "ui/11_tabs.js",
    "ui/12_editing.js",
    "storage/web/export.js",
    "ui/13_findings.js",
    "shell/web/14a_wiring.js",
    "storage/web/load.js",
    "shell/web/14b_wiring.js",
    "shell/web/page.tail.html",
]


def render():
    """The whole build. Concatenation, and nothing else - deliberately.

    A build step that transforms its input is a build step that can introduce a defect
    the sources do not contain. Until there is a second shell to build, there is nothing
    for it to do but join the parts back together.
    """
    out = []
    for name in PARTS:
        p = SRC / name
        if not p.exists():
            raise SystemExit(f"missing source part: src/{name}")
        text = p.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        out.append(text)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="compare against the committed file and write nothing")
    args = ap.parse_args()

    built = render()
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else None

    if args.check:
        if current is None:
            print(f"FAIL  {OUT.relative_to(ROOT)} does not exist")
            return 1
        if built == current:
            print(f"ok    {OUT.relative_to(ROOT)} is byte-identical to a build from src/ "
                  f"({len(built):,} bytes, {len(PARTS)} parts)")
            return 0
        # Say WHERE, not just that. A diff of two 260 KB files helps nobody.
        b, c = built.split("\n"), current.split("\n")
        for i, (x, y) in enumerate(zip(b, c), start=1):
            if x != y:
                print(f"FAIL  first difference at line {i}\n"
                      f"        built:     {x[:90]}\n"
                      f"        committed: {y[:90]}")
                return 1
        print(f"FAIL  lengths differ: built {len(b)} lines, committed {len(c)} lines")
        return 1

    OUT.write_text(built, encoding="utf-8")
    verb = "unchanged" if built == current else "written"
    print(f"{verb}: {OUT.relative_to(ROOT)}  ({len(built):,} bytes from {len(PARTS)} parts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
