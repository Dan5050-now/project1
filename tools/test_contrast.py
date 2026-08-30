"""Every text colour in the UI, measured against the surface it actually sits on.

A palette is easy to check by eye in one theme and easy to get wrong in the other, and
the failure is quiet: the text is still there, it is just harder to read than it looks
to whoever chose it. So the ratios are measured rather than judged - alpha composited
onto the first opaque ancestor, then WCAG AA applied at the size the text is actually
rendered at (3:1 for large, 4.5:1 for everything else).

Apple's own tertiaryLabel is around 3:1 on white, which is right for a glyph and thin
for the running text this page uses it on. The greys here are the same idea, lifted far
enough to clear AA while still reading as clearly subordinate.

    python tools/test_contrast.py
"""
from playwright.sync_api import sync_playwright
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = (ROOT / "app" / "PRAP.html").as_uri()
XLSX = str(ROOT / "templates" / "PRAP_SourceData_Dummy_10x10_v1.6.xlsx")
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

def rgba(s):
    n = [float(x) for x in s[s.index("(")+1:s.index(")")].split(",")]
    return (n[0], n[1], n[2], n[3] if len(n) > 3 else 1.0)

def over(fg, bg):                       # composite fg (with alpha) onto opaque bg
    a = fg[3]
    return tuple(fg[i]*a + bg[i]*(1-a) for i in range(3))

def lum(c):
    def f(x):
        x /= 255
        return x/12.92 if x <= .03928 else ((x+.055)/1.055)**2.4
    return .2126*f(c[0]) + .7152*f(c[1]) + .0722*f(c[2])

def ratio(a, b):
    L1, L2 = lum(a)+.05, lum(b)+.05
    return max(L1, L2)/min(L1, L2)

PROBE = """() => {
  const opaque = e => {
    for (let n = e; n; n = n.parentElement){
      const c = getComputedStyle(n).backgroundColor;
      const m = /rgba?\\(([^)]+)\\)/.exec(c);
      if (m && (m[1].split(',').length < 4 || parseFloat(m[1].split(',')[3]) > .95)) return c;
    }
    return getComputedStyle(document.body).backgroundColor;
  };
  const out = [];
  for (const [label, sel] of [["page heading","h1"],["version strip",".vers"],
      ["panel caption",".cap"],["panel note",".note"],["scope chip",".scope"],
      ["tile label",".tile .tl"],["tile sub",".tile .ts"],["table heading",".data-t thead th"],
      ["table cell",".data-t tbody td"],["tab (unselected)","nav button:not([aria-selected='true'])"],
      ["button label",".btn:not(.primary)"],["legend",".legend li"],["column badge",".drv"]]){
    const e = document.querySelector(sel);
    if (!e) continue;
    out.push([label, getComputedStyle(e).color, opaque(e), getComputedStyle(e).fontSize]);
  }
  return out;
}"""

bad = 0
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=CHROME)
    for scheme in ("light", "dark"):
        pg = b.new_page(viewport={"width":1400,"height":900}, color_scheme=scheme)
        pg.goto(APP); pg.wait_for_timeout(200)
        pg.set_input_files("#picker", XLSX); pg.wait_for_timeout(4500)
        print(f"== {scheme}")
        for label, fg, bg, size in pg.evaluate(PROBE):
            f, g = rgba(fg), rgba(bg)
            r = ratio(over(f, g[:3]), g[:3])
            px = float(size.replace("px", ""))
            need = 3.0 if px >= 18.66 else 4.5          # WCAG AA
            ok = r >= need
            bad += 0 if ok else 1
            print(f"   {label:20s} {size:>7s} {r:5.2f}:1  need {need}  {'ok' if ok else 'LOW'}")
        pg.close()
    b.close()
print()
print("FAILURES: none" if not bad else f"FAILURES ({bad} colours below AA)")
sys.exit(1 if bad else 0)
