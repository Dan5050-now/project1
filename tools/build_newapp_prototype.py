"""Generate the PM_APP screen prototype - the Step N3 deliverable you can click.

The desktop application is the web application in a window, plus SIX SCREENS that have
no counterpart in the browser. Those six are what Step N3 has to get right, and a table
describing a dialog is a poor way to review a dialog.

So this builds them: static, self-contained, no logic behind them. Every string is the
one specified in PRAP_NewApp_Specification_v1.0.xlsx, so reviewing the prototype IS
reviewing the specification's wording.

    python tools/build_newapp_prototype.py

Output: app/PM_APP_Prototype_v0.1.html
"""

from pathlib import Path

VERSION = "0.1"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / f"PM_APP_Prototype_v{VERSION}.html"

# Every screen: id, menu label, the component ids it demonstrates, and its markup.
# Kept as data so the component list and this prototype cannot describe different sets.
SCREENS = []


def screen(sid, label, comps, body):
    SCREENS.append((sid, label, comps, body))


# ---- 1. identity ----------------------------------------------------------
screen("identity", "1 · Who are you", "NC-01, NC-02", """
<div class="dlg" style="max-width:440px">
  <h2>Project Management APP</h2>
  <p class="sub">Before you open a plan, tell us who you are.</p>
  <label>Your name
    <input value="Kim Min-jun" spellcheck="false">
    <span class="hint">Pre-filled from your Windows account. Change it if colleagues know you by another name.</span>
  </label>
  <label>Department
    <input value="Data Management" list="depts" spellcheck="false">
    <datalist id="depts"><option>Data Management</option><option>Biostatistics</option>
      <option>Clinical Operations</option></datalist>
    <span class="hint">Offered from the departments already in your plan.</span>
  </label>
  <p class="disclaim">This is how colleagues will see you when you are editing a plan.
     It is not a login and it is not checked.</p>
  <div class="acts"><button class="btn">Not me</button>
    <button class="btn primary">Continue</button></div>
</div>
<p class="ann"><b>Second launch onward</b> shows the same dialog pre-filled, and the primary
   button reads <b>Continue as Kim Min-jun</b> — one click. <b>Not me</b> is what a shared
   PC needs.</p>""")

# ---- 2. open --------------------------------------------------------------
screen("open", "2 · Open a plan", "NC-03, NC-04", """
<div class="dlg wide">
  <h2>Open a plan</h2>
  <div class="two">
    <div>
      <h3>Recent</h3>
      <ul class="recent">
        <li><b>Q3 resourcing.prap</b><span>data\\workspaces · saved 11:07 today by Kim Min-jun (Data Management)</span></li>
        <li><b>2027 pipeline.prap</b><span>\\\\srv-01\\plans · saved yesterday by Park Ji-woo (Biostatistics)</span>
            <em class="held">held by Park Ji-woo</em></li>
        <li><b>Biosimilar scenarios.prap</b><span>data\\workspaces · saved 4 Aug</span></li>
      </ul>
    </div>
    <div>
      <h3>Or start something</h3>
      <div class="cards">
        <button class="card"><b>New plan</b><span>Empty, with the standard vocabulary and settings</span></button>
        <button class="card"><b>Import source data…</b><span>An Excel workbook or a .prap.json</span></button>
        <button class="card"><b>Look at a source file…</b><span>Read it, change nothing, save nothing</span></button>
        <button class="card"><b>Open…</b><span>A plan somewhere else on disk</span></button>
      </div>
    </div>
  </div>
</div>
<p class="ann"><b>Look at a source file</b> is NR-IMP-05 — a workspace is optional, so
   "what does this file say?" needs no commitment. The third recent entry shows a plan
   somebody else is holding, <b>before</b> you open it rather than after.</p>""")

# ---- 3. blocked -----------------------------------------------------------
screen("blocked", "3 · Somebody is editing", "NC-05, NC-06", """
<div class="dlg" style="max-width:520px">
  <h2>This plan is being edited</h2>
  <div class="holder">
    <div class="who"><b>Kim Min-jun</b><span>Data Management</span></div>
    <div class="when">Started 09:14 · <span class="live">active now</span></div>
  </div>
  <p>You can look at everything — figures, charts, filters and exports all work. Only
     saving into this plan is held while somebody else has it.</p>
  <div class="acts"><button class="btn">Copy name and department</button>
    <button class="btn primary">Open read-only</button></div>
</div>

<div class="dlg" style="max-width:520px">
  <h2>This plan is being edited</h2>
  <div class="holder silent">
    <div class="who"><b>Kim Min-jun</b><span>Data Management</span></div>
    <div class="when">Started 09:14 · <span class="dead">not responding since 09:22</span>
      · <b>free at 09:52</b></div>
  </div>
  <p>Their session has stopped answering. It may be a locked screen or a dropped
     connection — the plan becomes free half an hour after the last sign of life.</p>
  <div class="acts"><button class="btn">Copy name and department</button>
    <button class="btn">Wait</button><button class="btn primary">Open read-only</button></div>
</div>
<p class="ann">Two states, one dialog. The heartbeat is 30 seconds and the expiry is 30
   minutes, deliberately different numbers — so the application can tell a colleague
   mid-sentence from one whose laptop died, and say which.</p>""")

# ---- 4. stale -------------------------------------------------------------
screen("stale", "4 · The figures moved", "NC-07", """
<div class="bar stale">
  <span class="dot"></span>
  <span><b>Kim Min-jun saved this plan at 11:07.</b> The figures on screen are from 09:00.</span>
  <span class="grow"></span>
  <button class="btn small">Keep looking</button>
  <button class="btn small primary">Reload</button>
</div>
<div class="fake">
  <div class="fake-h">Overall · monthly FTE by project</div>
  <div class="fake-b"></div>
</div>
<p class="ann">Not a dialog — a strip above the content, because it must not interrupt
   and must not be dismissed by accident. Somebody who opened a plan at 09:00 and quotes
   its figures at 11:00 is the failure this prevents; blocking writers alone would not
   have caught it.</p>""")

# ---- 5. recovery ----------------------------------------------------------
screen("recover", "5 · Unsaved work found", "NC-08", """
<div class="dlg" style="max-width:480px">
  <h2>Unsaved changes were found</h2>
  <p><b>Q3 resourcing.prap</b> has <b>7 unsaved changes</b> from 16:41 yesterday.
     The application closed before they were saved.</p>
  <ul class="chg">
    <li><span>Projects</span> PRJ-004 · end_date · 2028-06-30 → 2028-09-30</li>
    <li><span>Periods</span> PRJ-004 · Close-out (final) · weight · 1.00 → 1.30</li>
    <li><span>Assignments</span> ASG-021 · person_weight · 0.40 → 0.60</li>
    <li class="more">and 4 more</li>
  </ul>
  <div class="acts"><button class="btn">Discard them</button>
    <button class="btn primary">Keep them</button></div>
</div>
<p class="ann">The list is the point. "Recover unsaved work?" with nothing shown asks
   somebody to gamble; showing what the changes were lets them decide. Kept changes
   arrive as pending edits — still undoable by <i>Leave without change</i>.</p>""")

# ---- 6. difference --------------------------------------------------------
screen("diff", "6 · What the import would change", "NC-09, NC-10", """
<div class="dlg wide">
  <h2>Update this plan from PRAP_SourceData_2026Q3.xlsx?</h2>
  <p class="sub">This plan already contains data. Choose what the file may change.</p>
  <table class="diff">
    <thead><tr><th>Sheet</th><th class="n">Add</th><th class="n">Change</th>
      <th class="n">Only here</th><th>Accept</th></tr></thead>
    <tbody>
      <tr><td>Project</td><td class="n">2</td><td class="n">4</td><td class="n">0</td>
        <td><input type="checkbox" checked></td></tr>
      <tr><td>Milestone</td><td class="n">17</td><td class="n">3</td><td class="n">1</td>
        <td><input type="checkbox" checked></td></tr>
      <tr class="care"><td>Person</td><td class="n">0</td><td class="n">0</td>
        <td class="n">12</td><td><input type="checkbox"></td></tr>
      <tr><td>Assignment</td><td class="n">5</td><td class="n">9</td><td class="n">3</td>
        <td><input type="checkbox"></td></tr>
    </tbody>
  </table>
  <p class="disclaim"><b>Only here</b> counts rows you added by hand that this file does
     not mention. Accepting a sheet never deletes them — an import adds and changes.</p>
  <div class="acts"><button class="btn">Don't update</button>
    <button class="btn primary">Apply the ticked sheets</button></div>
</div>
<p class="ann">Per sheet, not per row: a row-level choice across a thousand rows is a
   choice nobody makes (S-N03). The result arrives as a <b>pending edit</b>, so the whole
   import is undone by <i>Leave without change</i> — which is what makes getting this
   dialog wrong survivable.</p>""")

# ---- 7. window ------------------------------------------------------------
screen("window", "7 · The window itself", "NC-11, NC-12, NC-13", """
<div class="win">
  <div class="title">Q3 resourcing • — Project Management APP</div>
  <div class="menu"><span>File</span><span>Edit</span><span>View</span><span>Plan</span><span>Help</span></div>
  <div class="strip">
    <span class="pill">Kim Min-jun · Data Management</span>
    <span class="pill hold">You are editing this plan</span>
    <span class="grow"></span>
    <span class="pill warn">7 unsaved changes</span>
    <button class="btn small">Show them</button>
    <button class="btn small">Leave without change</button>
    <button class="btn small primary">Save</button>
  </div>
  <div class="tabs"><span class="on">Overall</span><span>Source data (project)</span>
    <span>Source data (person)</span><span>General assumptions</span></div>
  <div class="fake-b tall"></div>
</div>
<p class="ann">Everything below the strip is the web application unchanged (N-11) — the
   twenty-five rounds of review are not thrown away. The title carries the plan name and
   a <b>•</b> for unsaved work; the version lives in About, because a version in the title
   is read once and then occupies space forever.</p>""")

# ---- 8. about -------------------------------------------------------------
screen("about", "8 · About", "NC-14", """
<div class="dlg" style="max-width:460px">
  <h2>Project Management APP</h2>
  <table class="kv">
    <tr><td>Version</td><td>1.0</td></tr>
    <tr><td>Source schema</td><td>v5</td></tr>
    <tr><td>Application folder</td><td><code>D:\\Tools\\PM_APP</code></td></tr>
    <tr><td>Data folder</td><td><code>D:\\Tools\\PM_APP\\data\\users\\kimmj</code></td></tr>
    <tr><td>Chosen by</td><td>rule 3 — writable <code>data\\</code> beside the application</td></tr>
    <tr><td>Signed in as</td><td>Kim Min-jun (Data Management)</td></tr>
  </table>
  <div class="acts"><button class="btn">Open the data folder</button>
    <button class="btn primary">Close</button></div>
</div>
<p class="ann"><b>Chosen by</b> is the row that earns this dialog. A portable application
   that will not say where its data went is a support problem, and the answer costs one
   line (NR-DEP-10).</p>""")


CSS = """
:root{color-scheme:light dark;
  --page:#f2f2f7;--surface:#fff;--ink:#1d1d1f;--ink2:rgba(60,60,67,.78);
  --muted:rgba(60,60,67,.62);--grid:rgba(60,60,67,.13);--fill:rgba(120,120,128,.12);
  --accent:#0066cc;--good:#248a3d;--warn:#ff9500;--crit:#d70015;
  --underbg:#fff6e0;--underink:#9a5b00;--overbg:#ffeceb;
  --shadow:0 1px 2px rgba(0,0,0,.05),0 6px 18px -6px rgba(0,0,0,.10);
  --r:10px;--r-lg:14px;
  --f:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{
  --page:#000;--surface:#1c1c1e;--ink:#f5f5f7;--ink2:rgba(235,235,245,.70);
  --muted:rgba(235,235,245,.50);--grid:rgba(235,235,245,.16);
  --fill:rgba(120,120,128,.24);--accent:#4da3ff;--underbg:#3a2c05;--underink:#ffd60a;
  --overbg:#3a1210;}}
*{box-sizing:border-box}
body{margin:0;font:14px/1.5 var(--f);background:var(--page);color:var(--ink)}
header{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--page) 88%,transparent);
  backdrop-filter:saturate(180%) blur(20px);border-bottom:1px solid var(--grid);
  padding:12px 22px;display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
header h1{font-size:16px;margin:0;letter-spacing:-.01em}
header .v{color:var(--muted);font-size:12px}
nav{display:flex;gap:6px;flex-wrap:wrap;padding:12px 22px 0}
nav button{font:inherit;font-size:12.5px;padding:6px 12px;border-radius:999px;
  border:1px solid var(--grid);background:var(--surface);color:var(--ink2);cursor:pointer}
nav button.on{background:var(--accent);border-color:var(--accent);color:#fff}
main{padding:18px 22px 60px;max-width:1000px}
section{display:none}section.on{display:block}
h2{font-size:17px;margin:0 0 4px;letter-spacing:-.01em}
h3{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);margin:0 0 8px}
.sub{color:var(--ink2);margin:0 0 16px}
.dlg{background:var(--surface);border:1px solid var(--grid);border-radius:var(--r-lg);
  box-shadow:var(--shadow);padding:22px;margin:0 0 16px}
.dlg.wide{max-width:760px}
label{display:block;margin:14px 0}
label input{display:block;width:100%;margin-top:5px;font:inherit;padding:8px 10px;
  border:1px solid var(--grid);border-radius:var(--r);background:var(--page);color:var(--ink)}
.hint{display:block;margin-top:4px;font-size:12px;color:var(--muted)}
.disclaim{font-size:12.5px;color:var(--ink2);background:var(--fill);padding:10px 12px;
  border-radius:var(--r);margin:16px 0 0}
.acts{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}
.btn{font:inherit;font-size:13px;padding:7px 14px;border-radius:var(--r);cursor:pointer;
  border:1px solid var(--grid);background:var(--surface);color:var(--ink)}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn.small{font-size:12px;padding:5px 10px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:26px}
.recent{list-style:none;margin:0;padding:0}
.recent li{padding:10px 12px;border-radius:var(--r);border:1px solid transparent}
.recent li:hover{background:var(--fill)}
.recent b{display:block;font-weight:600}
.recent span{display:block;font-size:12px;color:var(--muted)}
.recent .held{display:inline-block;margin-top:4px;font-size:11.5px;font-style:normal;
  background:var(--underbg);color:var(--underink);padding:2px 8px;border-radius:999px}
.cards{display:grid;gap:8px}
.card{text-align:left;font:inherit;padding:12px 14px;border-radius:var(--r);cursor:pointer;
  border:1px solid var(--grid);background:var(--surface);color:var(--ink)}
.card:hover{border-color:var(--accent)}
.card b{display:block}.card span{font-size:12px;color:var(--muted)}
.holder{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;
  background:var(--fill);border-radius:var(--r);padding:12px 14px;margin:6px 0 14px}
.holder.silent{background:var(--underbg)}
.holder.silent .when{color:var(--underink)}
.who{min-width:160px}
.who b{display:block;font-size:15px}
.who span{font-size:12px;color:var(--muted);white-space:nowrap}
.when{font-size:12.5px;color:var(--ink2);text-align:right}
.live{color:var(--good);font-weight:600}
.dead{color:var(--underink);font-weight:600}
.bar{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:var(--r);
  background:var(--underbg);color:var(--underink);margin-bottom:12px}
.bar .dot{width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
.grow{flex:1}
.fake{background:var(--surface);border:1px solid var(--grid);border-radius:var(--r-lg);overflow:hidden}
.fake-h{padding:10px 14px;border-bottom:1px solid var(--grid);font-size:12.5px;color:var(--muted)}
.fake-b{height:120px;background:repeating-linear-gradient(180deg,var(--fill) 0 1px,transparent 1px 26px)}
.fake-b.tall{height:220px}
.chg{list-style:none;margin:14px 0 0;padding:0;font-size:12.5px}
.chg li{padding:7px 10px;border-radius:8px;background:var(--fill);margin-bottom:5px;
  font-family:ui-monospace,Menlo,Consolas,monospace}
.chg li span{display:inline-block;min-width:104px;color:var(--muted);font-family:var(--f)}
.chg .more{background:none;color:var(--muted);font-family:var(--f)}
table.diff{width:100%;border-collapse:collapse;margin:8px 0 0;font-size:13px}
table.diff th{text-align:left;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;
  color:var(--muted);font-weight:600;padding:6px 10px;border-bottom:1px solid var(--grid)}
table.diff td{padding:8px 10px;border-bottom:1px solid var(--grid)}
table.diff .n{text-align:right;font-variant-numeric:tabular-nums}
table.diff tr.care td{background:var(--underbg);color:var(--underink)}
table.kv{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
table.kv td{padding:7px 0;border-bottom:1px solid var(--grid);vertical-align:top}
table.kv td:first-child{color:var(--muted);width:150px}
code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.win{background:var(--surface);border:1px solid var(--grid);border-radius:var(--r-lg);
  overflow:hidden;box-shadow:var(--shadow)}
.win .title{text-align:center;padding:9px;font-size:12.5px;color:var(--ink2);
  border-bottom:1px solid var(--grid);background:var(--fill)}
.win .menu{display:flex;gap:18px;padding:7px 14px;font-size:12.5px;color:var(--ink2);
  border-bottom:1px solid var(--grid)}
.strip{display:flex;gap:8px;align-items:center;padding:9px 14px;border-bottom:1px solid var(--grid);
  flex-wrap:wrap}
.pill{font-size:11.5px;padding:3px 10px;border-radius:999px;background:var(--fill);color:var(--ink2)}
.pill.hold{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.pill.warn{background:var(--underbg);color:var(--underink)}
.tabs{display:flex;gap:4px;padding:8px 14px;border-bottom:1px solid var(--grid);font-size:12.5px}
.tabs span{padding:5px 12px;border-radius:999px;color:var(--ink2)}
.tabs .on{background:var(--fill);color:var(--ink);font-weight:600}
.ann{max-width:760px;font-size:12.5px;color:var(--ink2);border-left:2px solid var(--accent);
  padding:2px 0 2px 14px;margin:16px 0 0}
.ann b{color:var(--ink)}
"""


def main():
    nav = "".join(f'<button data-s="{sid}">{label}</button>' for sid, label, _, _ in SCREENS)
    secs = "".join(
        f'<section id="s-{sid}"><h2>{label.split(" · ")[1]}</h2>'
        f'<p class="sub">Components {comps}</p>{body}</section>'
        for sid, label, comps, body in SCREENS)
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PM_APP screen prototype v{VERSION}</title>
<!--
  Project Management APP - screen prototype, Step N3 deliverable.

  STATIC. Nothing here works: no file is read, no plan is opened, no claim is taken.
  It exists so the eight screens that have no counterpart in the web application can be
  looked at rather than read about. Every string is the one specified in
  PRAP_NewApp_Specification_v1.0.xlsx - so reviewing this IS reviewing that wording.

  Generated by tools/build_newapp_prototype.py. Do not edit by hand.
-->
<style>{CSS}</style>
<header>
  <h1>Project Management APP — screen prototype</h1>
  <span class="v">v{VERSION} · Step N3 · static, nothing works</span>
</header>
<nav>{nav}</nav>
<main>{secs}</main>
<script>
"use strict";
const secs = [...document.querySelectorAll("section")];
const btns = [...document.querySelectorAll("nav button")];
function show(id){{
  secs.forEach(s => s.classList.toggle("on", s.id === "s-" + id));
  btns.forEach(b => b.classList.toggle("on", b.dataset.s === id));
  location.hash = id;
}}
btns.forEach(b => b.onclick = () => show(b.dataset.s));
show(location.hash.slice(1) || "{SCREENS[0][0]}");
</script>
</html>
"""
    OUT.write_text(html, encoding="utf-8")
    print(f"Written: {OUT}  ({len(html):,} bytes, {len(SCREENS)} screens)")


if __name__ == "__main__":
    main()
