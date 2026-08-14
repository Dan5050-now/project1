"""Build the desktop renderer page from the same src/ the web application uses.

    core/ + ui/ + shell/desktop/  ->  src/shell/desktop/index.html

The page is the web application: the same engine, the same tabs, tables, charts and
editing behaviour, built from the same parts in the same order (decision N-05). What
differs is the shell around it -

  * the window chrome: title, status strip, and the file buttons removed because the
    menu bar replaces them (D-N02); the theme toggle removed because the window follows
    Windows (D-N09)
  * a bridge that routes Load and Export through window.pmapp instead of a file picker
    and a download

and nothing else. Every divergence is on sheet 03 of the approved component list.

    python tools/build_desktop.py

Output: src/shell/desktop/index.html
"""

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = SRC / "shell" / "desktop" / "index.html"

# The same parts as the web build, in the same order, EXCEPT the two storage functions
# and the web page's own head/tail - which is precisely the seam the plan described.
import importlib.util                                                # noqa: E402
_spec = importlib.util.spec_from_file_location("build_app", ROOT / "tools" / "build_app.py")
build_app = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_app)

WEB_ONLY = {"storage/web/export.js", "storage/web/load.js"}

CHROME_CSS = """
/* ===================== PM_APP desktop chrome =============================
   The window, not the product. Everything below this line styles the frame
   around the application; nothing in it decides a number. */
#pm-title{position:sticky;top:0;z-index:60;text-align:center;padding:8px;
  font-size:12.5px;color:var(--ink2);background:var(--fill);
  border-bottom:1px solid var(--grid);-webkit-app-region:drag}
#pm-strip{position:sticky;top:33px;z-index:60;display:flex;gap:8px;align-items:center;
  flex-wrap:wrap;padding:8px 16px;background:var(--surface);
  border-bottom:1px solid var(--grid)}
.pm-pill{font-size:11.5px;padding:3px 10px;border-radius:999px;background:var(--fill);
  color:var(--ink2)}
.pm-pill.hold{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good)}
.pm-pill.read{background:var(--underbg);color:var(--underink)}
.pm-grow{flex:1}
/* D-N02: the menu bar replaces these. D-N09: the window follows Windows. */
#loadBtn,#loadBtn2,#exportBtn,#exportJsonBtn,#themeBtn{display:none}
"""

CHROME_HTML = """
<div id="pm-title">Project Management APP</div>
<div id="pm-strip">
  <span class="pm-pill" id="pm-who">not signed in</span>
  <span class="pm-pill" id="pm-hold" hidden></span>
  <span class="pm-grow"></span>
  <span class="pm-pill" id="pm-where"></span>
</div>
"""

BRIDGE = r"""
<script>
"use strict";
/* ============================================================ the desktop bridge
   Everything the web shell did with a picker and a download, routed through
   window.pmapp - which is the only thing the renderer can reach (preload.js).

   The claim is taken HERE, on the first pending edit, because that is the moment a
   data value actually changes. Not on a click, not on a selection, not on a filter:
   a claim taken by a click would block a colleague for half an hour on account of
   somebody browsing (U-N03). */

(async () => {
  const api = window.pmapp;
  if (!api) return;                       // opened in a browser: stay the web app

  const caps = await api.capabilities();
  const paths = await api.paths();
  const el = id => document.getElementById(id);
  el("pm-where").textContent = `v${paths.version} · ${paths.dataDir}`;

  /* ---- who is at the keyboard (NR-USR-01..04) --------------------------- */
  let me = await api.identity.get();
  if (!me) me = await api.identity.suggest();
  await api.identity.set(me);
  el("pm-who").textContent = me.department ? `${me.name} · ${me.department}` : me.name;

  /* ---- the claim, taken on the first DATA CHANGE ------------------------ */
  let ref = null, holds = false;

  async function takeClaimOnEdit() {
    if (!ref || holds || !caps.claims) return true;
    const r = await api.claim.take(ref);
    if (r.ok) {
      holds = true;
      el("pm-hold").hidden = false;
      el("pm-hold").className = "pm-pill hold";
      el("pm-hold").textContent = "You are editing this plan";
      return true;
    }
    el("pm-hold").hidden = false;
    el("pm-hold").className = "pm-pill read";
    el("pm-hold").textContent = "Read-only — " + r.holder.name;
    showBanner("bad", r.message);
    return false;
  }

  // beginEditSession() is the application's own "a value is about to change" point -
  // the snapshot before the first pending edit. Wrapping it is what makes the claim
  // attach to a change rather than to a click, without touching ui/ at all.
  const origBegin = window.beginEditSession;
  window.beginEditSession = function (...a) {
    takeClaimOnEdit();
    return origBegin.apply(this, a);
  };

  api.on("claim:lost", holder => {
    holds = false;
    showBanner("bad", "Your hold on this plan was taken over while you were working. "
      + "Nothing has been saved. Save As a copy to keep your changes.");
  });

  /* ---- the menu ---------------------------------------------------------- */
  api.on("menu", async what => {
    if (what.startsWith("tab:")) return showTab(what.slice(4));
    if (what.startsWith("open:")) return openWorkspace(what.slice(5));
    switch (what) {
      case "new": return startBlank();
      case "open": {
        const p = await api.workspace.openDialog();
        return p && openWorkspace(p);
      }
      case "save": return saveWorkspace();
      case "commit": return el("saveBtn")?.click();
      case "discard": return el("discardBtn")?.click();
      case "changes": return el("chgBtn")?.click();
      case "export": return exportWorkbook(false);
      case "exportJson": return exportWorkbook(true);
      default: return;
    }
  });

  async function openWorkspace(p) {
    try {
      const w = await api.workspace.open(p);
      ref = w.ref;
      adopt(w.sheets, w.ref.split(/[\\/]/).pop());
      const by = w.header.last_saved_by;
      if (by) showBanner("", `Last saved by ${by.name}`
        + (by.department ? ` (${by.department})` : "")
        + `, ${new Date(w.header.last_saved).toLocaleString()}.`);
    } catch (e) {
      showBanner("bad", e.message || String(e));
    }
  }

  async function saveWorkspace() {
    const sheets = {};
    for (const s of REQUIRED_SHEETS) sheets[s] = rawToRows(s);
    try {
      if (!ref) {
        const r = await api.workspace.saveAs(sheets, {}, "Untitled.prap");
        if (!r) return;
        ref = r.ref;
      } else {
        await api.workspace.save(ref, sheets, {});
      }
      showBanner("", "Saved.");
    } catch (e) {
      showBanner("bad", e.message || String(e));
    }
  }

  window.__pm = { openWorkspace, saveWorkspace, takeClaimOnEdit,
                  state: () => ({ ref, holds, me, caps, paths }) };
})();
</script>
"""


def main():
    parts = []
    for name in build_app.PARTS:
        if name in WEB_ONLY:
            continue
        text = (SRC / name).read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        if name == "ui/style.css":
            text += CHROME_CSS
        if name == "shell/web/page.body.html":
            text = text.replace('<div class="wrap">', CHROME_HTML + '\n<div class="wrap">', 1)
        if name == "shell/web/page.head.html":
            text = text.replace("<title>PRAP — Project Resource Assignment Program</title>",
                                "<title>Project Management APP</title>", 1)
        if name == "shell/web/page.tail.html":
            text = BRIDGE + text
        parts.append(text)

    html = "".join(parts).replace(
        "<h1>Project Resource Assignment Program</h1>",
        "<h1>Project Management APP</h1>", 1)
    OUT.write_text(html, encoding="utf-8")
    print(f"Written: {OUT.relative_to(ROOT)}  ({len(html):,} bytes from "
          f"{len(parts)} parts, {len(WEB_ONLY)} web-only parts left out)")


if __name__ == "__main__":
    main()
