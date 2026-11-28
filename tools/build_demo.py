"""The web application with the dummy plan already in it - for trying it out.

    python tools/build_demo.py

Output: app/PRAP_Demo.html

app/PRAP.html opens empty and waits for a workbook. That is right for the product and
in the way of somebody who wants to see what it is like to USE: to walk the tabs, click
issues, filter, edit a cell, and notice what is awkward. This is the same file with the
62-project, 20-person dummy dataset loaded on opening, through readPrapJson() and
adopt() - the path a real .prap.json takes - so nothing about the application is bypassed
and every figure is computed by the engine that ships.

THE DATA IS FIXED AT BUILD TIME AND IT IS DUMMY DATA: templates/PRAP_SourceData_Dummy_*.
There is no way to put other data into this file except through the application's own
Load button, exactly as in app/PRAP.html; this build adds no route in. Everything else
is unchanged - Load, Export, Save changes, the change log - so a change made here behaves
exactly as it would in the product, and the source workbook is never touched.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "PRAP.html"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.23.xlsx"
OUT = ROOT / "app" / "PRAP_Demo.html"


def demo_json():
    """The dummy workbook as prap-source-data JSON, via the Python reference reader."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = Path(tf.name)
    subprocess.run([sys.executable, str(ROOT / "tools" / "prap_io.py"),
                    "to-json", str(DUMMY), "-o", str(tmp)],
                   check=True, capture_output=True)
    data = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.unlink()
    return data


BANNER_CSS = """
/* ---- the demo strip (tools/build_demo.py) ---- */
#demo-strip{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 16px;
  font-size:12.5px;background:var(--underbg);color:var(--underink);
  border-bottom:1px solid var(--grid)}
#demo-strip b{font-weight:700}
#demo-strip button{margin-left:auto;font:inherit;font-size:12px;padding:2px 10px;
  border-radius:999px;border:1px solid currentColor;background:none;color:inherit;
  cursor:pointer}
"""


def main():
    if not APP.exists():
        raise SystemExit("Build the application first:  python tools/build_app.py")
    html = APP.read_text(encoding="utf-8")
    data = demo_json()
    sheets = data["sheets"]
    rows = sum(len(v) for v in sheets.values())
    np, ns, na = (len(sheets["Project"]), len(sheets["Person"]), len(sheets["Assignment"]))

    html = html.replace("</style>", BANNER_CSS + "</style>", 1)
    strip = (f'<div id="demo-strip" role="note"><span><b>Demo</b> — loaded with dummy data '
             f'({np} projects, {ns} people, {na} assignments). Explore freely: edits stay '
             f'in this window until you export, and nothing is sent anywhere. '
             f'<b>Load</b> still opens a workbook of your own, as in the product.</span>'
             f'<button type="button" onclick="this.parentNode.remove()">Hide</button></div>')
    html = html.replace('<div class="wrap">', strip + '\n<div class="wrap">', 1)

    payload = json.dumps(json.dumps(data, separators=(",", ":"), default=str))
    boot = f"""
<script>
"use strict";
/* The dummy dataset (tools/build_demo.py), loaded through readPrapJson() and adopt() -
   the same path a real .prap.json takes. Nothing about the application is bypassed. */
const PRAP_DEMO = {payload};
try {{
  adopt(readPrapJson(PRAP_DEMO), "PRAP_SourceData_Dummy (demo).prap.json");
}} catch (e) {{
  console.error(e);
  const s = document.getElementById("demo-strip");
  if (s) s.textContent = "The demo data failed to load: " + e.message
    + " - use Load to open a workbook instead.";
}}
</script>
"""
    html = html.replace("</html>", boot + "</html>", 1)
    html = html.replace("<title>PRAP — Project Resource Assignment Program</title>",
                        "<title>PRAP — demo with dummy data</title>", 1)
    OUT.write_text(html, encoding="utf-8")
    print(f"Written: {OUT}")
    print(f"  {len(html):,} bytes · {rows} data rows · {np} projects · {ns} people · "
          f"{na} assignments, from {DUMMY.name}")


if __name__ == "__main__":
    main()
