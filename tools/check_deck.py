"""Geometry and fit checks for a .pptx, for when nothing can render it.

The usual visual QA is: convert to images and look. This container has LibreOffice
WITHOUT the Impress module - the presentation filters are simply absent, so nothing here
can open a .pptx to draw it, and a deck could ship with text hanging off the slide and
nobody would know. This reads the slide XML and measures instead.

What it can check, and does:

  * every shape inside the slide, with a margin the deck claims to keep
  * text boxes that overlap another text box (not shapes - cards are MEANT to sit under
    their text, so only text-on-text is reported)
  * text that will not fit its own box, estimated from character widths

What it cannot: kerning, real line breaking, or anything about how a font the container
does not have will actually set. Korean here is measured at one em per glyph, which is
right for Hangul and wrong for the Latin mixed into it, so the estimate is deliberately
generous - it reports what is clearly over, not what is marginal.

    python tools/check_deck.py output/deck/PRAP_소개자료.pptx
"""

import math
import pathlib
import re
import sys
import zipfile

EMU = 914400.0            # EMU per inch
SLIDE_W, SLIDE_H = 13.333, 7.5
MARGIN = 0.5              # the deck's own claim
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def em_width(ch):
    """Width of one character in em. Hangul and CJK are full width; the rest are not."""
    o = ord(ch)
    if (0xAC00 <= o <= 0xD7A3) or (0x3130 <= o <= 0x318F) or (0x4E00 <= o <= 0x9FFF):
        return 1.0
    if ch in " iljt.,:;'!|":
        return 0.30
    if ch.isupper() or ch.isdigit():
        return 0.60
    return 0.52


def fits(text, w_in, h_in, size_pt, line_pt):
    """Rough: does `text` fit a box of this size? Returns (ok, lines_needed, lines_fit)."""
    usable_pt = max(w_in * 72 - 6, 12)          # 3pt of inset either side
    need = 0
    for para in str(text).split("\n"):
        wide = sum(em_width(c) for c in para) * size_pt
        need += max(1, math.ceil(wide / usable_pt))
    have = max(1, int((h_in * 72 + 1) // line_pt))
    return need <= have, need, have


def boxes(xml):
    """Every shape: (name, x, y, w, h, text, size_pt, line_pt, is_textbox)."""
    import defusedxml.ElementTree as ET
    root = ET.fromstring(xml)
    out = []
    for sp in root.iter(f"{{{NS['p']}}}sp"):
        nv = sp.find(f".//{{{NS['p']}}}nvSpPr/{{{NS['p']}}}cNvPr")
        name = nv.get("name", "?") if nv is not None else "?"
        off = sp.find(f".//{{{NS['a']}}}off")
        ext = sp.find(f".//{{{NS['a']}}}ext")
        if off is None or ext is None:
            continue
        x, y = int(off.get("x")) / EMU, int(off.get("y")) / EMU
        w, h = int(ext.get("cx")) / EMU, int(ext.get("cy")) / EMU
        tx = sp.find(f".//{{{NS['p']}}}txBody")
        is_tb = sp.find(f".//{{{NS['p']}}}nvSpPr/{{{NS['p']}}}cNvSpPr") is not None and \
            sp.find(f".//{{{NS['p']}}}nvSpPr/{{{NS['p']}}}cNvSpPr").get("txBox") == "1"
        text, size, line = "", 0, 0
        if tx is not None:
            paras = []
            for p in tx.iter(f"{{{NS['a']}}}p"):
                paras.append("".join(t.text or "" for t in p.iter(f"{{{NS['a']}}}t")))
                for rpr in p.iter(f"{{{NS['a']}}}rPr"):
                    if rpr.get("sz"):
                        size = max(size, int(rpr.get("sz")) / 100)
                for ln in p.iter(f"{{{NS['a']}}}lnSpc"):
                    pts = ln.find(f"{{{NS['a']}}}spcPts")
                    if pts is not None:
                        line = max(line, int(pts.get("val")) / 100)
            text = "\n".join(paras)
        out.append((name, x, y, w, h, text, size or 12, line or (size or 12) * 1.22, is_tb))
    for pic in root.iter(f"{{{NS['p']}}}pic"):
        off = pic.find(f".//{{{NS['a']}}}off")
        ext = pic.find(f".//{{{NS['a']}}}ext")
        if off is None or ext is None:
            continue
        out.append(("[image]", int(off.get("x")) / EMU, int(off.get("y")) / EMU,
                    int(ext.get("cx")) / EMU, int(ext.get("cy")) / EMU, "", 12, 14, False))
    return out


def overlap(a, b):
    ax, ay, aw, ah = a[1], a[2], a[3], a[4]
    bx, by, bw, bh = b[1], b[2], b[3], b[4]
    ox = min(ax + aw, bx + bw) - max(ax, bx)
    oy = min(ay + ah, by + bh) - max(ay, by)
    return ox > 0.04 and oy > 0.04, ox, oy


def main(path):
    z = zipfile.ZipFile(path)
    names = sorted((n for n in z.namelist()
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                   key=lambda n: int(re.search(r"(\d+)", n.split("/")[-1]).group(1)))
    problems = 0
    for i, n in enumerate(names, 1):
        bs = boxes(z.read(n))
        msgs = []
        for b in bs:
            name, x, y, w, h, text, size, line, is_tb = b
            if x < -0.02 or y < -0.02 or x + w > SLIDE_W + 0.02 or y + h > SLIDE_H + 0.02:
                # a deliberate bleed shape is fine; text off the slide is not
                if text.strip():
                    msgs.append(f"OFF-SLIDE  {name!r} at ({x:.2f},{y:.2f}) {w:.2f}x{h:.2f}")
            elif text.strip() and (x < MARGIN - 0.02 or x + w > SLIDE_W - MARGIN + 0.02):
                msgs.append(f"margin     {name!r} x={x:.2f}..{x + w:.2f} (want {MARGIN}..{SLIDE_W - MARGIN})")
            if text.strip():
                ok, need, have = fits(text, w, h, size, line)
                if not ok and need > have + 0.5:
                    msgs.append(f"OVERFLOW   {name!r} {size:.0f}pt needs {need} lines, "
                                f"box holds {have}  [{text[:38].replace(chr(10), ' / ')}...]")
        texts = [b for b in bs if b[8] and b[5].strip()]
        for a in range(len(texts)):
            for c in range(a + 1, len(texts)):
                hit, ox, oy = overlap(texts[a], texts[c])
                if hit and ox > 0.12 and oy > 0.12:
                    msgs.append(f"overlap    {texts[a][0]!r} x {texts[c][0]!r} "
                                f"({ox:.2f}\" x {oy:.2f}\")")
        print(f"slide {i:2}  {len(bs):3} shapes  " + ("ok" if not msgs else f"{len(msgs)} issue(s)"))
        for m in msgs:
            print("          " + m)
        problems += len(msgs)
    print(f"\n{problems} issue(s) across {len(names)} slides")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "output/deck/PRAP_소개자료.pptx"))
