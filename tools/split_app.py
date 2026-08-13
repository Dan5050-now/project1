"""One-shot: carve app/PRAP.html into src/ along the boundaries it already has.

The single file was written in fourteen numbered sections, and those sections already
draw the line this refactor needs: sections 1-6 decide numbers, 7-13 draw them, 14 wires
the browser to both, and two functions - one that reads a file, one that writes one -
are the whole of what a desktop shell would replace.

Nothing is rewritten. Every byte keeps its position in the concatenation, which is what
lets tools/build_app.py reproduce the committed file exactly rather than merely
equivalently. A refactor that has to be argued for is a refactor nobody can check.

    python tools/split_app.py        (run once; build_app.py is the one used afterwards)
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
APP = ROOT / "app" / "PRAP.html"

# (path, first line, last line) - 1-based and inclusive, in file order.
# The three boundaries that are NOT section boundaries are the two storage functions
# and the head/style/body split; everything else is a banner comment in the original.
PARTS = [
    ("shell/web/page.head.html",        1,    17),   # doctype .. <style>
    ("ui/style.css",                   18,   586),   # the stylesheet
    ("shell/web/page.body.html",      587,   705),   # </style> .. <script> "use strict";
    ("core/00_meta.js",               706,   726),   # version constants, provenance
    ("core/01_xlsx_read.js",          727,   837),
    ("core/02_xlsx_write.js",         838,  1192),
    ("core/03_parse.js",             1193,  1447),   # dates, parse, JSON interchange
    ("core/04_derive.js",            1448,  1498),   # period derivation
    ("core/05_model.js",             1499,  1823),   # model + validation V-00..V-24
    ("core/06_calculate.js",         1824,  1908),   # the monthly engine
    ("ui/07_state.js",               1909,  1979),
    ("ui/08_render.js",              1980,  2058),
    ("ui/09_charts.js",              2059,  2582),
    ("ui/10_tables.js",              2583,  2972),
    ("ui/11_tabs.js",                2973,  3563),
    ("ui/12_editing.js",             3564,  3910),   # section 12 up to the export
    ("storage/web/export.js",        3911,  3959),   # exportWorkbook - writes a file
    ("ui/13_findings.js",            3960,  4150),
    ("shell/web/14a_wiring.js",      4151,  4380),
    ("storage/web/load.js",          4381,  4392),   # loadFile - reads a file
    ("shell/web/14b_wiring.js",      4393,  4864),
    ("shell/web/page.tail.html",     4865,  4865),   # </html>
]


def main():
    lines = APP.read_text(encoding="utf-8").split("\n")
    # A trailing newline makes split() produce one empty last element; keep it out of
    # the ranges and let build_app.py put it back, so line numbers stay honest.
    trailing = lines and lines[-1] == ""
    if trailing:
        lines = lines[:-1]
    if len(lines) != PARTS[-1][2]:
        raise SystemExit(f"expected {PARTS[-1][2]} lines, found {len(lines)}")

    covered = 0
    for path, first, last in PARTS:
        if first != covered + 1:
            raise SystemExit(f"gap or overlap before {path}: {covered} then {first}")
        covered = last
        out = SRC / path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines[first - 1:last]) + "\n", encoding="utf-8")
        print(f"  {path:34} {last - first + 1:5} lines")
    print(f"\n{len(PARTS)} parts, {covered} lines, no gaps.")


if __name__ == "__main__":
    main()
