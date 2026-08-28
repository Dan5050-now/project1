"""Generate the PM_APP working prototype - the real application, with real figures.

v0.1 of the prototype showed the eight new screens against grey placeholder blocks. That
was enough to review the WORDING of a dialog and useless for reviewing what the
application looks like when it is full of data.

This builds the honest version: app/PRAP.html itself - every tab, table, chart, filter
and figure, computed by the same engine that will ship - wrapped in the desktop chrome,
pre-loaded with the 62-project dummy dataset, with the eight new screens reachable as
overlays over the top of it.

Nothing is mocked except the eight dialogs, which have nothing behind them by design:
no file is read, no plan is opened, no claim is taken. Everything else is live.

    python tools/build_newapp_demo.py

Output: app/PM_APP_Prototype_v0.3.html
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

VERSION = "0.3"
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "PRAP.html"
DUMMY = ROOT / "templates" / "PRAP_SourceData_Dummy_v1.13.xlsx"
OUT = ROOT / "app" / f"PM_APP_Prototype_v{VERSION}.html"

# The eight screens come from the v0.1 prototype generator, so the two cannot drift
# apart and the component list keeps describing the same set.
_spec = importlib.util.spec_from_file_location(
    "proto", ROOT / "tools" / "build_newapp_prototype.py")
proto = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(proto)

# Desktop chrome and the overlay. Everything is scoped under #pm- ids or .pm- classes so
# it cannot reach into the application's own stylesheet; the .btn class is deliberately
# NOT re-declared, so the prototype's buttons are the application's buttons.
CHROME_CSS = """
/* ===================== PM_APP prototype chrome ==========================
   Added by tools/build_newapp_demo.py. Everything below is prototype dressing
   around the real application - it styles the window, not the product. */
#pm-title{position:sticky;top:0;z-index:60;text-align:center;padding:8px;font-size:12.5px;
  color:var(--ink2);background:var(--fill);border-bottom:1px solid var(--grid)}
#pm-menu{position:sticky;top:33px;z-index:60;display:flex;gap:18px;padding:7px 16px;
  font-size:12.5px;color:var(--ink2);background:var(--surface);
  border-bottom:1px solid var(--grid)}
#pm-menu span{cursor:default}
#pm-strip{position:sticky;top:66px;z-index:60;display:flex;gap:8px;align-items:center;
  flex-wrap:wrap;padding:8px 16px;background:var(--surface);
  border-bottom:1px solid var(--grid)}
.pm-pill{font-size:11.5px;padding:3px 10px;border-radius:999px;background:var(--fill);
  color:var(--ink2)}
.pm-pill.hold{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.pm-grow{flex:1}
#pm-demo{font-size:11.5px;color:var(--muted);padding:6px 16px;background:var(--page);
  border-bottom:1px solid var(--grid)}
/* The application's own file buttons are replaced by menus on the desktop (D-N02),
   so they are hidden here rather than left to contradict the menu bar. The theme
   toggle goes too: the desktop window follows Windows and offers no setting of its
   own (D-N09, changed at the Gate N3 review). */
#loadBtn,#expMenu,#themeBtn{display:none}

#pm-open{position:fixed;right:18px;bottom:18px;z-index:70}
#pm-ov{position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.42);
  backdrop-filter:blur(3px);display:none;overflow:auto}
#pm-ov.on{display:block}
#pm-ov-in{max-width:1000px;margin:26px auto;background:var(--page);border-radius:16px;
  padding:18px 22px 40px;box-shadow:0 30px 80px -20px rgba(0,0,0,.6)}
#pm-ov h1{font-size:16px;margin:0 0 2px}
#pm-ov .lead{font-size:12.5px;color:var(--muted);margin:0 0 14px}
#pm-nav{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
#pm-nav button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:999px;
  border:1px solid var(--grid);background:var(--surface);color:var(--ink2);cursor:pointer}
#pm-nav button.on{background:var(--accent);border-color:var(--accent);color:#fff}
#pm-ov section{display:none}
#pm-ov section.on{display:block}
#pm-ov h2{font-size:17px;margin:0 0 4px}
#pm-ov .sub{color:var(--ink2);margin:0 0 14px;font-size:13px}
#pm-ov h3{font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;
  color:var(--muted);margin:0 0 8px}
#pm-ov .dlg{background:var(--surface);border:1px solid var(--grid);border-radius:14px;
  box-shadow:var(--shadow);padding:20px;margin:0 0 14px}
#pm-ov .dlg.wide{max-width:760px}
#pm-ov label{display:block;margin:13px 0}
#pm-ov label input{display:block;width:100%;margin-top:5px;font:inherit;padding:8px 10px;
  border:1px solid var(--grid);border-radius:9px;background:var(--page);color:var(--ink)}
#pm-ov .hint{display:block;margin-top:4px;font-size:12px;color:var(--muted)}
#pm-ov .disclaim{font-size:12.5px;color:var(--ink2);background:var(--fill);
  padding:10px 12px;border-radius:9px;margin:15px 0 0}
#pm-ov .acts{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}
#pm-ov .two{display:grid;grid-template-columns:1fr 1fr;gap:24px}
#pm-ov .recent{list-style:none;margin:0;padding:0}
#pm-ov .recent li{padding:9px 11px;border-radius:9px}
#pm-ov .recent li:hover{background:var(--fill)}
#pm-ov .recent b{display:block;font-weight:600}
#pm-ov .recent span{display:block;font-size:12px;color:var(--muted)}
#pm-ov .recent .held{display:inline-block;margin-top:4px;font-size:11.5px;
  font-style:normal;background:var(--underbg);color:var(--underink);
  padding:2px 8px;border-radius:999px}
#pm-ov .cards{display:grid;gap:8px}
#pm-ov .card{text-align:left;font:inherit;padding:11px 13px;border-radius:9px;
  cursor:pointer;border:1px solid var(--grid);background:var(--surface);color:var(--ink)}
#pm-ov .card:hover{border-color:var(--accent)}
#pm-ov .card b{display:block}
#pm-ov .card span{font-size:12px;color:var(--muted)}
#pm-ov .holder{display:flex;justify-content:space-between;align-items:center;gap:16px;
  flex-wrap:wrap;background:var(--fill);border-radius:9px;padding:11px 13px;margin:6px 0 13px}
#pm-ov .holder.silent{background:var(--underbg)}
#pm-ov .holder.silent .when{color:var(--underink)}
#pm-ov .who{min-width:160px}
#pm-ov .who b{display:block;font-size:15px}
#pm-ov .who span{font-size:12px;color:var(--muted);white-space:nowrap}
#pm-ov .when{font-size:12.5px;color:var(--ink2);text-align:right}
#pm-ov .live{color:var(--good);font-weight:600}
#pm-ov .dead{color:var(--underink);font-weight:600}
#pm-ov .bar{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:9px;
  background:var(--underbg);color:var(--underink);margin-bottom:12px;flex-wrap:wrap}
#pm-ov .bar .dot{width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
#pm-ov .grow{flex:1}
#pm-ov .fake{background:var(--surface);border:1px solid var(--grid);border-radius:14px;
  overflow:hidden}
#pm-ov .fake-h{padding:10px 14px;border-bottom:1px solid var(--grid);font-size:12.5px;
  color:var(--muted)}
#pm-ov .fake-b{height:120px;background:repeating-linear-gradient(180deg,
  var(--fill) 0 1px,transparent 1px 26px)}
#pm-ov .fake-b.tall{height:210px}
#pm-ov .chg{list-style:none;margin:13px 0 0;padding:0;font-size:12.5px}
#pm-ov .chg li{padding:7px 10px;border-radius:8px;background:var(--fill);margin-bottom:5px;
  font-family:var(--f-mono)}
#pm-ov .chg li span{display:inline-block;min-width:104px;color:var(--muted);
  font-family:var(--f-ui)}
#pm-ov .chg .more{background:none;color:var(--muted);font-family:var(--f-ui)}
#pm-ov table.diff{width:100%;border-collapse:collapse;margin:8px 0 0;font-size:13px}
#pm-ov table.diff th{text-align:left;font-size:11.5px;text-transform:uppercase;
  letter-spacing:.04em;color:var(--muted);font-weight:600;padding:6px 10px;
  border-bottom:1px solid var(--grid)}
#pm-ov table.diff td{padding:8px 10px;border-bottom:1px solid var(--grid)}
#pm-ov table.diff .n{text-align:right;font-variant-numeric:tabular-nums}
#pm-ov table.diff tr.care td{background:var(--underbg);color:var(--underink)}
#pm-ov table.kv{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
#pm-ov table.kv td{padding:7px 0;border-bottom:1px solid var(--grid);vertical-align:top}
#pm-ov table.kv td:first-child{color:var(--muted);width:150px}
#pm-ov .win{background:var(--surface);border:1px solid var(--grid);border-radius:14px;
  overflow:hidden}
#pm-ov .win .title{text-align:center;padding:9px;font-size:12.5px;color:var(--ink2);
  border-bottom:1px solid var(--grid);background:var(--fill)}
#pm-ov .win .menu{display:flex;gap:18px;padding:7px 14px;font-size:12.5px;
  color:var(--ink2);border-bottom:1px solid var(--grid)}
#pm-ov .strip{display:flex;gap:8px;align-items:center;padding:9px 14px;flex-wrap:wrap;
  border-bottom:1px solid var(--grid)}
#pm-ov .pill{font-size:11.5px;padding:3px 10px;border-radius:999px;background:var(--fill);
  color:var(--ink2)}
#pm-ov .pill.hold{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
#pm-ov .pill.warn{background:var(--underbg);color:var(--underink)}
#pm-ov .tabs{display:flex;gap:4px;padding:8px 14px;border-bottom:1px solid var(--grid);
  font-size:12.5px}
#pm-ov .tabs span{padding:5px 12px;border-radius:999px;color:var(--ink2)}
#pm-ov .tabs .on{background:var(--fill);color:var(--ink);font-weight:600}
#pm-ov .ann{max-width:760px;font-size:12.5px;color:var(--ink2);
  border-left:2px solid var(--accent);padding:2px 0 2px 14px;margin:14px 0 0}
#pm-ov .ann b{color:var(--ink)}
"""


def chrome_html():
    return """
<div id="pm-title">Q3 resourcing — Project Management APP</div>
<div id="pm-menu"><span>File</span><span>Edit</span><span>View</span><span>Plan</span>
  <span>Help</span></div>
<div id="pm-strip">
  <span class="pm-pill">Kim Min-jun · Data Management</span>
  <span class="pm-pill hold">You are editing this plan</span>
  <span class="pm-grow"></span>
  <button class="btn" id="pm-screens">The eight new screens</button>
</div>
<div id="pm-demo">Prototype — the application below is real and every figure in it is
  computed from the 62-project dummy dataset. The window chrome above and the eight
  screens are dressing: no file is read, no plan is opened, no claim is taken.</div>
"""


def overlay_html():
    nav = "".join(f'<button data-s="{sid}">{label}</button>'
                  for sid, label, _, _ in proto.SCREENS)
    secs = "".join(
        f'<section id="pm-s-{sid}"><h2>{label.split(" · ")[1]}</h2>'
        f'<p class="sub">Components {comps}</p>{body}</section>'
        for sid, label, comps, body in proto.SCREENS)
    return f"""
<div id="pm-ov"><div id="pm-ov-in">
  <div style="display:flex;align-items:baseline;gap:12px">
    <h1>The eight new screens</h1><span class="pm-grow"></span>
    <button class="btn" id="pm-close">Close</button>
  </div>
  <p class="lead">Static. Nothing here works — every string is the one specified at
     Gate N2, so reviewing these is reviewing that wording. Close this to go back to
     the live application.</p>
  <div id="pm-nav">{nav}</div>
  {secs}
</div></div>
<script>
"use strict";
(() => {{
  const ov = document.getElementById("pm-ov");
  const secs = [...ov.querySelectorAll("section")];
  const btns = [...document.querySelectorAll("#pm-nav button")];
  const show = id => {{
    secs.forEach(s => s.classList.toggle("on", s.id === "pm-s-" + id));
    btns.forEach(b => b.classList.toggle("on", b.dataset.s === id));
  }};
  btns.forEach(b => b.onclick = () => show(b.dataset.s));
  document.getElementById("pm-screens").onclick = () => {{
    ov.classList.add("on"); show("{proto.SCREENS[0][0]}"); ov.scrollTop = 0;
  }};
  document.getElementById("pm-close").onclick = () => ov.classList.remove("on");
  ov.addEventListener("click", e => {{ if (e.target === ov) ov.classList.remove("on"); }});
  addEventListener("keydown", e => {{ if (e.key === "Escape") ov.classList.remove("on"); }});
}})();
</script>
"""


def demo_json():
    """The dummy workbook as prap-source-data JSON, via the same reader the app uses."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        tmp = Path(tf.name)
    subprocess.run([sys.executable, str(ROOT / "tools" / "prap_io.py"),
                    "to-json", str(DUMMY), "-o", str(tmp)],
                   check=True, capture_output=True)
    data = json.loads(tmp.read_text(encoding="utf-8"))
    tmp.unlink()
    return data


def main():
    html = APP.read_text(encoding="utf-8")
    data = demo_json()
    rows = sum(len(v) for v in data["sheets"].values())

    # 1. chrome stylesheet, appended to the application's own so it can use its variables
    html = html.replace("</style>", CHROME_CSS + "</style>", 1)

    # 2. chrome markup, above the application
    html = html.replace('<div class="wrap">', chrome_html() + '\n<div class="wrap">', 1)

    # 3. the overlay and the dataset, after the application's script has defined adopt()
    payload = json.dumps(json.dumps(data, separators=(",", ":")))
    boot = f"""
<script>
"use strict";
/* The dummy dataset, loaded through readPrapJson() - the same path a real .prap.json
   takes. Nothing about the application is bypassed to make this work, which is the
   point: if a figure here is wrong, it is wrong in the product too. */
const PM_DEMO = {payload};
try {{
  adopt(readPrapJson(PM_DEMO), "Q3 resourcing.prap");
  showBanner("", "Prototype loaded from the 62-project dummy dataset — "
    + "{rows} rows across ten sheets. Every figure below is computed, not drawn.");
}} catch (e) {{
  console.error(e);
  document.getElementById("pm-demo").textContent =
    "The demo dataset failed to load: " + e.message;
}}
</script>
"""
    html = html.replace("</html>", overlay_html() + boot + "</html>", 1)

    # 4. the product's own name, inside the product (NR-APP-08). The web application
    #    keeps its name; this build is the desktop one, and a prototype that calls
    #    itself by the other product's name is a prototype of the wrong thing.
    html = html.replace(
        "<title>PRAP — Project Resource Assignment Program</title>",
        f"<title>Project Management APP — working prototype v{VERSION}</title>", 1)
    html = html.replace(
        "<h1>Project Resource Assignment Program</h1>",
        "<h1>Project Management APP</h1>", 1)

    OUT.write_text(html, encoding="utf-8")
    print(f"Written: {OUT}")
    print(f"  {len(html):,} bytes · {rows} data rows · "
          f"{len(data['sheets']['Project'])} projects · "
          f"{len(data['sheets']['Person'])} people · "
          f"{len(data['sheets']['Assignment'])} assignments · "
          f"{len(proto.SCREENS)} overlay screens")


if __name__ == "__main__":
    main()
