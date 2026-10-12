"""Build the introduction deck - PRAP_소개자료.pptx - with pptxgenjs.

WRITTEN FOR A NON-TECHNICAL AUDIENCE. The deck explains what the application lets a
person DO, not how it is built. Rule numbers, schema versions, requirement ids and the
internals of the build all stay out of it; what goes in is the decision each screen
helps somebody make.

A tool rather than a one-off script, for the reason tools/package_source.py is one: the
few figures that do appear are the repository's own, and a deck typed by hand goes stale
the moment a version moves. Those figures are READ from the artefacts:

    개발계획서            requirement count
    prap_contract.json    sheets, columns, the application's version
    the repository        file counts, commit count, dates

Icons are rendered from react-icons to PNG at build time, so the deck carries no
dependency on a font the reader may not have.

    python tools/build_deck.py

Output: output/deck/PRAP_소개자료.pptx
"""

import json
import os
import pathlib
import subprocess
import sys

from openpyxl import load_workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECK = ROOT / "output" / "deck"
ICONS = DECK / "icons"


def facts():
    """The figures on the slides, taken from the artefacts rather than typed."""
    man = json.loads((ROOT / "docs" / "PRAP_Manifest.json").read_text())
    cur = {e["what"]: pathlib.Path(e["path"]).name for e in man["current"]}
    con = json.loads((ROOT / "docs" / "prap_contract.json").read_text())

    ws = load_workbook(ROOT / "docs" / cur["development_plan"], data_only=True)["03_Requirements"]
    reqs = sum(1 for r in range(5, ws.max_row + 1)
               if str(ws.cell(r, 1).value or "").replace("* ", "").startswith("REQ"))

    def sh(*cmd):
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.strip()

    return {
        "reqs": reqs,
        "rules": len(con["validation_rules"]),
        "sheets": len(con["sheets"]),
        "columns": sum(len(s["columns"]) for s in con["sheets"].values()),
        "appVer": con["application"]["version"],
        "appKB": round((ROOT / "app" / "PRAP.html").stat().st_size / 1024),
        "suites": len(list((ROOT / "tools").glob("test_*.py"))),
        "commits": int(sh("git", "rev-list", "--count", "HEAD") or 0),
        "since": sh("git", "log", "--reverse", "--format=%ad", "--date=short").split("\n")[0],
        "until": sh("git", "log", "-1", "--format=%ad", "--date=short"),
    }


def node_path():
    """Where the npm packages live, which differs between machines."""
    roots = []
    g = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True)
    if g.returncode == 0 and g.stdout.strip():
        roots.append(pathlib.Path(g.stdout.strip()))
    roots += [ROOT / "node_modules", pathlib.Path.home() / "node_modules"]
    roots += sorted(pathlib.Path("/tmp").glob("claude-*/**/scratchpad/node_modules"))[:4]
    found = [str(r) for r in roots if (r / "pptxgenjs").is_dir()]
    if not found:
        raise SystemExit("pptxgenjs was not found.  npm install pptxgenjs")
    return ":".join(found)


# Icon name (react-icons/fi) -> file stem. Feather icons: one weight, plain outlines,
# which is what keeps a slide calm when a dozen of them are on it.
ICON_SET = {
    "users": "FiUsers", "calendar": "FiCalendar", "trending": "FiTrendingUp",
    "alert": "FiAlertTriangle", "down": "FiTrendingDown", "grid": "FiGrid",
    "file": "FiFileText", "check": "FiCheckCircle", "eye": "FiEye",
    "sliders": "FiSliders", "share": "FiShare2", "clock": "FiClock",
    "layers": "FiLayers", "search": "FiSearch", "edit": "FiEdit3",
    "download": "FiDownload", "upload": "FiUpload", "monitor": "FiMonitor",
    "pie": "FiPieChart", "bar": "FiBarChart2", "map": "FiMap", "zap": "FiZap",
    "lock": "FiLock", "refresh": "FiRefreshCw", "help": "FiHelpCircle",
    "target": "FiTarget", "arrow": "FiArrowRight", "book": "FiBookOpen",
}

ICON_JS = r"""
const React = require("react");
const RD = require("react-dom/server");
const sharp = require("sharp");
const Fi = require("react-icons/fi");
const fs = require("fs");
const SET = __SET__, OUT = __OUT__;
(async () => {
  for (const [stem, spec] of Object.entries(SET)) {
    for (const [suffix, colour] of [["", "1F3A40"], ["_w", "FFFFFF"], ["_t", "028090"]]) {
      const Icon = Fi[spec];
      if (!Icon) { console.error("missing icon " + spec); continue; }
      const svg = RD.renderToStaticMarkup(
        React.createElement(Icon, { size: 320, color: "#" + colour, strokeWidth: 1.9 }));
      const buf = await sharp(Buffer.from(svg)).resize(320, 320).png().toBuffer();
      fs.writeFileSync(OUT + "/" + stem + suffix + ".png", buf);
    }
  }
  console.log("icons: " + Object.keys(SET).length * 3);
})();
"""


def make_icons(env):
    ICONS.mkdir(parents=True, exist_ok=True)
    js = DECK / "_icons.js"
    js.write_text(ICON_JS.replace("__SET__", json.dumps(ICON_SET))
                         .replace("__OUT__", json.dumps(str(ICONS))), encoding="utf-8")
    r = subprocess.run(["node", str(js)], cwd=DECK, capture_output=True, text=True, env=env)
    print(r.stdout.strip() or r.stderr.strip()[-800:])
    js.unlink(missing_ok=True)
    return r.returncode


def main():
    DECK.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "NODE_PATH": node_path()}
    if make_icons(env):
        return 1
    js = DECK / "deck.js"
    js.write_text(TEMPLATE.replace("/*__FACTS__*/", json.dumps(facts(), ensure_ascii=False)),
                  encoding="utf-8")
    r = subprocess.run(["node", str(js)], cwd=DECK, capture_output=True, text=True, env=env)
    print(r.stdout.strip() or r.stderr.strip()[-2500:])
    return r.returncode


# ---------------------------------------------------------------- the generator
TEMPLATE = r"""
const pptxgen = require("pptxgenjs");
const path = require("path");
const F = /*__FACTS__*/;

const P = {
  ink:   "0B3C44", deep: "072E34", teal: "028090", sea: "00A896", mint: "02C39A",
  warm:  "C2603F", warmBg: "FBEDE7", warmInk: "8A3A21",
  white: "FFFFFF", tint: "EAF4F5", tint2: "F5FAFB", line: "D2E2E5",
  body:  "23434A", muted: "5E7B81", gold: "E0A500",
};
const KR = "맑은 고딕";
const W = 13.333, H = 7.5, M = 0.62;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "PRAP";
pres.title = "PRAP 소개자료";

const shadow = () => ({ type: "outer", color: "0B3C44", blur: 16, offset: 3, angle: 90, opacity: 0.11 });
const ico = (n) => path.join(__dirname, "icons", n + ".png");

function slide(dark) {
  const s = pres.addSlide();
  s.background = { color: dark ? P.ink : P.white };
  return s;
}
function head(s, kicker, title, sub) {
  s.addText(kicker, { x: M, y: 0.40, w: 9, h: 0.28, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.teal, charSpacing: 1.2 });
  s.addText(title, { x: M, y: 0.70, w: 11.6, h: 0.62, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 29, bold: true, color: P.ink });
  if (sub) s.addText(sub, { x: M, y: 1.34, w: 11.6, h: 0.32, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12.5, color: P.muted });
}
function card(s, x, y, w, h, fill, noShadow) {
  const o = { x, y, w, h, rectRadius: 0.09, fill: { color: fill || P.tint2 },
    line: { color: P.line, width: 0.75 } };
  if (!noShadow) o.shadow = shadow();
  s.addShape(pres.ShapeType.roundRect, o);
}
// The motif: an outline icon inside a soft filled disc.
function disc(s, x, y, d, name, fill, white) {
  s.addShape(pres.ShapeType.ellipse, { x, y, w: d, h: d, fill: { color: fill } });
  const p = d * 0.27;
  s.addImage({ path: ico(name + (white ? "_w" : "_t")), x: x + p, y: y + p,
    w: d - 2 * p, h: d - 2 * p });
}
function foot(s, n) {
  s.addText("PRAP · 임상 과제 인력 배정 시뮬레이터", { x: M, y: 6.96, w: 7, h: 0.28,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 9, color: P.muted });
  s.addText(String(n), { x: W - M - 0.6, y: 6.96, w: 0.6, h: 0.28, isTextBox: true,
    margin: 0, align: "right", fontFace: KR, fontSize: 9, color: P.muted });
}

/* ═══════════════════════════════════════════════ 1. 표지 */
{
  const s = slide(true);
  s.addShape(pres.ShapeType.ellipse, { x: 8.9, y: -2.2, w: 7.2, h: 7.2,
    fill: { color: P.teal, transparency: 84 } });
  s.addShape(pres.ShapeType.ellipse, { x: 10.6, y: 3.2, w: 4.4, h: 4.4,
    fill: { color: P.mint, transparency: 88 } });

  s.addText("사내 AI 활용 · 개발 사례", { x: M, y: 1.5, w: 8, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 13, bold: true, color: P.mint, charSpacing: 1.4 });
  s.addText("PRAP", { x: M, y: 1.94, w: 8, h: 1.2, isTextBox: true, margin: 0,
    fontFace: "Arial", fontSize: 70, bold: true, color: P.white });
  s.addText("여러 임상 과제가 동시에 돌아갈 때,\n누가 언제 얼마나 일하게 되는지 미리 보는 도구", {
    x: M, y: 3.14, w: 8.4, h: 1.0, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 20, color: P.white, lineSpacing: 33 });

  const pts = [
    ["calendar", "월 단위로 앞을 본다"],
    ["users", "사람별로 합쳐서 본다"],
    ["lock", "PC 안에서만 돈다"],
  ];
  pts.forEach((p, i) => {
    const x = M + i * 2.75;
    disc(s, x, 4.62, 0.52, p[0], P.teal, true);
    s.addText(p[1], { x: x + 0.66, y: 4.62, w: 2.05, h: 0.52, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 12, color: P.tint });
  });
  s.addText(`개발 기간 ${F.since} ~ ${F.until}`, { x: M, y: 5.62, w: 8, h: 0.3,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 11, color: P.sea });
  s.addNotes("한 문장으로: 여러 과제가 동시에 돌아갈 때 사람별 부담을 월 단위로 미리 보는 도구입니다.");
}

/* ═══════════════════════════════════════════════ 2. 한 장 요약 */
{
  const s = slide(false);
  head(s, "OVERVIEW", "한 장으로 보는 PRAP");

  const cols = [
    ["help", "어떤 도구인가", P.teal,
     "과제별 계획을 엑셀 한 파일에 적어두면,\n앞으로 몇 달 동안 누가 얼마나 바쁠지를\n표와 그래프로 보여준다.\n\n설치가 필요 없고, 파일을 두 번 눌러\n여는 것으로 시작한다."],
    ["target", "어디에 쓰나", P.sea,
     "· 분기 인력 계획 수립\n· 신규 과제를 받을 여력 판단\n· 일정이 밀렸을 때 영향 확인\n· 특정 인력의 부담 점검\n· 과제별 투입 근거 설명"],
    ["zap", "무엇이 달라지나", P.mint,
     "여러 과제에 흩어져 있던 숫자를\n사람 기준으로 합쳐서 본다.\n\n문제가 생긴 뒤가 아니라\n생기기 전에 보인다."],
  ];
  cols.forEach((c, i) => {
    const x = M + i * 4.06, w = 3.78;
    card(s, x, 1.72, w, 2.92);
    disc(s, x + 0.26, 1.98, 0.6, c[0], c[2], true);
    s.addText(c[1], { x: x + 0.98, y: 1.98, w: w - 1.2, h: 0.6, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 15, bold: true, color: P.ink });
    s.addText(c[3], { x: x + 0.28, y: 2.72, w: w - 0.56, h: 1.82, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 11.5, color: P.body, lineSpacing: 19 });
  });

  card(s, M, 4.86, 12.09, 1.66, P.tint, true);
  s.addText("쓰는 사람", { x: M + 0.34, y: 5.06, w: 2, h: 0.28, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.teal });
  const who = [
    ["users", "리소스 담당자", "매월 배정 현황을 보고 다음 분기를 계획한다"],
    ["bar", "과제 리더", "자기 과제가 필요한 만큼 인력을 받고 있는지 본다"],
    ["book", "관리자", "포트폴리오 전체의 인력 부담을 한눈에 확인한다"],
  ];
  who.forEach((wh, i) => {
    const x = M + 0.34 + i * 3.92;
    disc(s, x, 5.42, 0.44, wh[0], P.white);
    s.addText(wh[1], { x: x + 0.56, y: 5.40, w: 3.2, h: 0.26, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 12, bold: true, color: P.ink });
    s.addText(wh[2], { x: x + 0.56, y: 5.66, w: 3.25, h: 0.42, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10, color: P.body, lineSpacing: 14 });
  });
  foot(s, 2);
  s.addNotes("데이터는 엑셀 파일에 그대로 남습니다. 앱은 그 파일을 읽어 보여줄 뿐이고, 원본은 늘 손에 있습니다.");
}

/* ═══════════════════════════════════════════════ 3. 개발 배경 */
{
  const s = slide(false);
  head(s, "개발 배경", "왜 필요했나", "이전에는 과제별로 표가 따로 있었고, 사람 기준으로 합친 그림이 없었다.");

  const pains = [
    ["layers", "과제는 겹쳐서 돌아간다", "한 사람이 여러 과제에 동시에 들어간다.\n각 표만 봐서는 겹치는 구간이 보이지 않는다."],
    ["trending", "부담이 일정하지 않다", "같은 과제라도 준비 기간과 진행 기간의\n부담이 다르고, 역할마다 또 다르다."],
    ["refresh", "일정은 자주 바뀐다", "한 번 만든 배정표는 금방 현실과 어긋나고,\n다시 만드는 데 또 시간이 든다."],
  ];
  pains.forEach((p, i) => {
    const y = 1.92 + i * 1.44;
    card(s, M, y, 6.5, 1.22, P.warmBg, true);
    disc(s, M + 0.26, y + 0.3, 0.6, p[0], P.warm, true);
    s.addText(p[1], { x: M + 1.0, y: y + 0.18, w: 5.3, h: 0.3, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 14, bold: true, color: P.warmInk });
    s.addText(p[2], { x: M + 1.0, y: y + 0.5, w: 5.35, h: 0.62, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 11, color: P.warmInk, lineSpacing: 16 });
  });

  s.addShape(pres.ShapeType.roundRect, { x: 7.52, y: 1.92, w: 5.18, h: 4.34,
    rectRadius: 0.09, fill: { color: P.ink }, line: { color: P.ink }, shadow: shadow() });
  disc(s, 7.86, 2.24, 0.56, "search", P.teal, true);
  s.addText("답하기 어려웠던 두 가지", { x: 8.56, y: 2.24, w: 3.9, h: 0.56, isTextBox: true,
    margin: 0, valign: "middle", fontFace: KR, fontSize: 14, bold: true, color: P.mint });

  s.addText("“다음 분기에 누가 과부하이고,\n어느 과제 때문인가?”", {
    x: 7.86, y: 3.06, w: 4.5, h: 0.86, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 15.5, bold: true, color: P.white, lineSpacing: 26 });
  s.addShape(pres.ShapeType.line, { x: 7.86, y: 4.06, w: 4.5, h: 0,
    line: { color: "1D5760", width: 1 } });
  s.addText("그리고 잘 드러나지 않는 쪽 —", { x: 7.86, y: 4.2, w: 4.5, h: 0.26,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 11, color: P.sea });
  s.addText("“몇 달째 여유가 있는 사람은\n누구인가?”", {
    x: 7.86, y: 4.5, w: 4.5, h: 0.86, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 15.5, bold: true, color: P.white, lineSpacing: 26 });
  s.addText("둘 다 사람 기준으로 합쳐야 답이 나오는 질문이다.", {
    x: 7.86, y: 5.6, w: 4.5, h: 0.4, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10.5, color: P.tint, lineSpacing: 15 });
  foot(s, 3);
  s.addNotes("이 두 질문이 개발의 출발점이었고, 개발계획서에 그대로 적혀 있습니다.");
}

/* ═══════════════════════════════════════════════ 4. 사용 흐름 */
{
  const s = slide(false);
  head(s, "사용 방법", "쓰는 순서는 네 단계", "엑셀을 쓸 줄 알면 별도 교육 없이 쓸 수 있도록 만들었다.");

  const steps = [
    ["edit", "① 계획을 적는다", "과제·기간·투입 인력을 엑셀 한 파일에 적는다.\n양식은 앱과 함께 제공된다."],
    ["upload", "② 파일을 연다", "앱에 파일을 끌어다 놓는다.\n잘못된 값이 있으면 한 번에 모두 알려준다."],
    ["eye", "③ 화면에서 본다", "과제별·사람별 월 단위 투입량을\n표와 그래프로 확인한다."],
    ["download", "④ 조정하고 내보낸다", "화면에서 바로 고치고 저장하면\n같은 양식의 엑셀로 나온다."],
  ];
  const cw = 2.92, gap = 0.16;
  steps.forEach((st, i) => {
    const x = M + i * (cw + gap);
    card(s, x, 1.94, cw, 2.5);
    disc(s, x + cw / 2 - 0.36, 2.2, 0.72, st[0], i % 2 ? P.sea : P.teal, true);
    s.addText(st[1], { x: x + 0.14, y: 3.06, w: cw - 0.28, h: 0.34, isTextBox: true,
      margin: 0, align: "center", fontFace: KR, fontSize: 13.5, bold: true, color: P.ink });
    s.addText(st[2], { x: x + 0.18, y: 3.46, w: cw - 0.36, h: 0.86, isTextBox: true,
      margin: 0, align: "center", fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 16 });
    if (i < 3) s.addImage({ path: ico("arrow_t"), x: x + cw + 0.01, y: 3.0, w: 0.14, h: 0.14 });
  });

  card(s, M, 4.68, 12.09, 1.62, P.tint, true);
  const notes = [
    ["lock", "회사 PC 안에서만", "설치·서버·인터넷 없이 파일 하나로 돈다. 자료가 밖으로 나가지 않는다."],
    ["file", "엑셀이 원본", "앱은 계산해서 보여줄 뿐, 기록은 늘 엑셀 파일에 남는다."],
    ["check", "틀린 값은 미리 알려줌", "빠진 날짜, 없는 과제 등을 열 때 한 번에 정리해 보여준다."],
  ];
  notes.forEach((n, i) => {
    const x = M + 0.3 + i * 3.94;
    disc(s, x, 4.96, 0.46, n[0], P.white);
    s.addText(n[1], { x: x + 0.58, y: 4.94, w: 3.2, h: 0.28, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 12, bold: true, color: P.ink });
    s.addText(n[2], { x: x + 0.58, y: 5.22, w: 3.28, h: 0.62, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10, color: P.body, lineSpacing: 14 });
  });
  foot(s, 4);
  s.addNotes("교육이 거의 필요 없다는 점이 중요합니다. 양식은 예시 파일과 함께 제공됩니다.");
}

/* ═══════════════════════════════════════════════ 5. 무엇을 보여주나 */
{
  const s = slide(false);
  head(s, "주요 화면", "무엇을 보여주는가",
       "62개 과제 · 20명 · 24개월을 한 화면에 올린 예시.");

  s.addImage({ path: path.join(__dirname, "01_demand_by_project.png"),
    x: M, y: 1.86, w: 7.7, h: 4.12 });
  s.addText("월별 전체 투입량 — 색 띠 하나가 과제 하나", {
    x: M, y: 6.02, w: 7.7, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10.5, color: P.muted });

  const reads = [
    ["trending", "전체가 늘고 있는지", "다음 해 여름에 인력 수요가 몰린다는 것이 막대 높이로 바로 보인다."],
    ["pie", "어느 과제 때문인지", "막대 안의 띠 하나가 과제 하나다. 어느 과제가 그 달을 밀어 올렸는지 짚을 수 있다."],
    ["users", "누구에게 몰리는지", "같은 기간을 사람 기준으로 다시 보면, 부담이 특정 인원에 쏠렸는지 드러난다."],
  ];
  reads.forEach((r, i) => {
    const y = 1.94 + i * 1.42;
    card(s, 8.56, y, 4.14, 1.24);
    disc(s, 8.8, y + 0.22, 0.5, r[0], P.teal, true);
    s.addText(r[1], { x: 9.42, y: y + 0.2, w: 3.1, h: 0.3, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 12.5, bold: true, color: P.ink });
    s.addText(r[2], { x: 8.8, y: y + 0.56, w: 3.72, h: 0.6, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10, color: P.body, lineSpacing: 14 });
  });
  s.addText("화면은 네 가지 — 전체 / 과제별 / 사람별 / 기준값", {
    x: 8.56, y: 6.2, w: 4.14, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10.5, bold: true, color: P.teal });
  foot(s, 5);
  s.addNotes("이 그래프 하나로 '언제 몰리는가'와 '무엇 때문인가'를 동시에 답합니다.");
}

/* ═══════════════════════════════════════════════ 6. 계산 방식 */
{
  const s = slide(false);
  head(s, "계산 방식", "숫자는 이렇게 나온다",
       "복잡한 수식 대신, 두 단계로 생각하면 된다.");

  card(s, M, 1.9, 5.9, 2.0);
  disc(s, M + 0.3, 2.16, 0.6, "target", P.teal, true);
  s.addText("① 과제가 그 달에 필요로 하는 일의 양", {
    x: M + 1.02, y: 2.16, w: 4.6, h: 0.6, isTextBox: true, margin: 0, valign: "middle",
    fontFace: KR, fontSize: 14, bold: true, color: P.ink });
  s.addText("과제 종류와 진행 단계에 따라 '이 정도가 표준'이라는 기준값을 미리 정해둔다.\n과제마다 조금씩 크고 작을 수 있어, 과제별 가중치로 조정한다.", {
    x: M + 0.3, y: 2.88, w: 5.3, h: 0.86, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 11, color: P.body, lineSpacing: 17 });

  card(s, M, 4.06, 5.9, 2.0);
  disc(s, M + 0.3, 4.32, 0.6, "users", P.sea, true);
  s.addText("② 그 일을 배정된 사람들이 나눠 갖는다", {
    x: M + 1.02, y: 4.32, w: 4.6, h: 0.6, isTextBox: true, margin: 0, valign: "middle",
    fontFace: KR, fontSize: 14, bold: true, color: P.ink });
  s.addText("맡은 역할의 비중, 근무 비율, 참여한 기간에 따라 몫이 정해진다.\n사람이 몇 명이든 과제가 필요로 하는 양은 그대로다 — 나누는 방식만 달라진다.", {
    x: M + 0.3, y: 5.04, w: 5.3, h: 0.86, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 11, color: P.body, lineSpacing: 17 });

  // 오른쪽: 한 달을 나누는 그림
  s.addShape(pres.ShapeType.roundRect, { x: 7.14, y: 1.9, w: 5.56, h: 4.16,
    rectRadius: 0.09, fill: { color: P.ink }, line: { color: P.ink }, shadow: shadow() });
  s.addText("예시 — 어떤 과제의 10월", { x: 7.48, y: 2.16, w: 4.9, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 13, bold: true, color: P.mint });
  s.addText("이 과제가 10월에 필요로 하는 일의 양", { x: 7.48, y: 2.54, w: 4.9, h: 0.26,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 10.5, color: P.tint });
  s.addText("1.86", { x: 7.48, y: 2.8, w: 1.5, h: 0.6, isTextBox: true, margin: 0,
    fontFace: "Arial", fontSize: 38, bold: true, color: P.white });
  s.addText("사람 1명 몫 = 1.00", { x: 9.0, y: 3.02, w: 3.3, h: 0.3, isTextBox: true,
    margin: 0, valign: "middle", fontFace: KR, fontSize: 11, color: P.sea });

  const split = [["김 O O", "주 담당", 0.86, P.mint], ["이 O O", "지원", 0.60, P.sea],
                 ["박 O O", "일부 기간", 0.40, P.teal]];
  const barX = 7.48, barW = 4.9;
  const total = 1.86;
  let cx = barX;
  split.forEach((sp) => {
    const w = barW * (sp[2] / total);
    s.addShape(pres.ShapeType.rect, { x: cx, y: 3.62, w, h: 0.4, fill: { color: sp[3] } });
    cx += w;
  });
  split.forEach((sp, i) => {
    const y = 4.18 + i * 0.5;
    s.addShape(pres.ShapeType.ellipse, { x: barX, y: y + 0.08, w: 0.16, h: 0.16,
      fill: { color: sp[3] } });
    s.addText(sp[0], { x: barX + 0.28, y, w: 1.3, h: 0.32, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 11.5, bold: true, color: P.white });
    s.addText(sp[1], { x: barX + 1.56, y, w: 1.7, h: 0.32, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 10.5, color: P.tint });
    s.addText(sp[2].toFixed(2), { x: barX + 3.3, y, w: 1.6, h: 0.32, isTextBox: true,
      margin: 0, align: "right", valign: "middle", fontFace: "Arial", fontSize: 13,
      bold: true, color: P.white });
  });
  s.addText("세 사람의 몫을 더하면 정확히 1.86 — 과제가 필요로 한 양과 같다.", {
    x: barX, y: 5.68, w: 4.9, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10.5, color: P.mint });
  foot(s, 6);
  s.addNotes("핵심은 '사람을 더 넣는다고 과제가 필요로 하는 양이 늘지 않는다'는 점입니다. 나누는 방식만 달라집니다.");
}

/* ═══════════════════════════════════════════════ 7. 무엇을 잡아내나 */
{
  const s = slide(false);
  head(s, "핵심 가치", "이런 것들을 미리 잡아낸다",
       "보고 있어야 보이는 것이 아니라, 열면 먼저 알려준다.");

  const finds = [
    ["alert", P.warm, "과부하", "한 사람의 월 투입량이 기준을 넘으면 표시하고 개수를 세어 준다.",
     "다음 분기 배정을 바꿀 근거가 된다"],
    ["down", P.gold, "여유 인력", "몇 달 연속으로 여유가 있는 사람을 찾아 준다.",
     "신규 과제를 누구에게 줄지 판단한다"],
    ["target", P.teal, "기준 대비 부족", "과제가 표준만큼 인력을 받고 있는지 대조한다.",
     "인력이 모자란 과제를 먼저 본다"],
    ["grid", P.sea, "아직 배정 안 된 과제", "사람이 한 명도 없는 과제도 필요한 양을 먼저 보여준다.",
     "새 과제의 소요를 미리 가늠한다"],
  ];
  finds.forEach((f, i) => {
    const col = i % 2, row = (i / 2) | 0;
    const x = M + col * 6.13, y = 1.96 + row * 2.2;
    card(s, x, y, 5.83, 1.92);
    disc(s, x + 0.28, y + 0.28, 0.66, f[0], f[1], true);
    s.addText(f[2], { x: x + 1.08, y: y + 0.28, w: 4.5, h: 0.4, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 15, bold: true, color: P.ink });
    s.addText(f[3], { x: x + 0.28, y: y + 1.04, w: 5.3, h: 0.4, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 11, color: P.body, lineSpacing: 16 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.28, y: y + 1.44, w: 5.3, h: 0.34,
      rectRadius: 0.05, fill: { color: P.tint }, line: { color: P.tint } });
    s.addText("→  " + f[4], { x: x + 0.42, y: y + 1.44, w: 5.05, h: 0.34, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, bold: true, color: P.teal });
  });
  foot(s, 7);
  s.addNotes("네 가지 모두 사람이 찾아내야 했던 것들입니다. 이제 파일을 열면 앱이 먼저 말해 줍니다.");
}

/* ═══════════════════════════════════════════════ 8. 만든 과정 */
{
  const s = slide(true);
  s.addText("개발 과정", { x: M, y: 0.40, w: 9, h: 0.28, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.mint, charSpacing: 1.2 });
  s.addText("AI로 만들되, 숫자는 믿을 수 있게", { x: M, y: 0.70, w: 11.6, h: 0.62,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 29, bold: true, color: P.white });
  s.addText("사람이 정하고 AI가 만들되, 틀린 채로 넘어가지 못하도록 단계마다 확인 장치를 두었다.", {
    x: M, y: 1.34, w: 11.6, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12.5, color: P.tint });

  const steps = [
    ["book", "무엇을 만들지 먼저 글로", "화면과 계산 규칙을 문서로 먼저 확정했다."],
    ["check", "단계마다 검토하고 승인", "승인 전에는 다음 단계로 넘어가지 않았다."],
    ["zap", "AI가 구현", "확정된 내용만 코드로 옮기게 했다."],
    ["refresh", "자동으로 다시 확인", "문서와 프로그램이 어긋나면 바로 드러나게 했다."],
  ];
  const cw = 2.92, gap = 0.16;
  steps.forEach((st, i) => {
    const x = M + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, { x, y: 1.86, w: cw, h: 2.22, rectRadius: 0.09,
      fill: { color: P.deep }, line: { color: "1D5760", width: 1 } });
    disc(s, x + cw / 2 - 0.34, 2.1, 0.68, st[0], P.teal, true);
    s.addText(st[1], { x: x + 0.14, y: 2.9, w: cw - 0.28, h: 0.5, isTextBox: true,
      margin: 0, align: "center", fontFace: KR, fontSize: 12.5, bold: true,
      color: P.white, lineSpacing: 17 });
    s.addText(st[2], { x: x + 0.18, y: 3.42, w: cw - 0.36, h: 0.54, isTextBox: true,
      margin: 0, align: "center", fontFace: KR, fontSize: 10, color: P.tint, lineSpacing: 14 });
    if (i < 3) s.addImage({ path: ico("arrow_w"), x: x + cw + 0.01, y: 2.9, w: 0.14, h: 0.14 });
  });

  s.addText("숫자를 믿을 수 있게 만든 방법", { x: M, y: 4.36, w: 6, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 14, bold: true, color: P.mint });
  const trust = [
    ["같은 계산을 여러 방식으로 따로 만들어 결과가 모두 일치할 때만 통과시켰다."],
    ["기준을 주장이 아니라 실제로 재서 정했다 — 규모별 응답 속도를 측정해 확인했다."],
    ["문서와 프로그램이 어긋나면 만들 때 바로 걸리도록 해두었다."],
  ];
  trust.forEach((t, i) => {
    const y = 4.74 + i * 0.52;
    s.addImage({ path: ico("check_w"), x: M, y: y + 0.04, w: 0.22, h: 0.22 });
    s.addText(t[0], { x: M + 0.36, y, w: 7.4, h: 0.32, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 11.5, color: P.tint });
  });

  const kp = [[String(F.reqs), "합의된 요구사항"], [String(F.suites), "자동 점검 항목"],
              [String(F.commits), "개선 이력"]];
  kp.forEach((k, i) => {
    const y = 4.42 + i * 0.7;
    s.addText(k[0], { x: 8.9, y, w: 1.3, h: 0.5, isTextBox: true, margin: 0, align: "right",
      valign: "middle", fontFace: "Arial", fontSize: 26, bold: true, color: P.white });
    s.addText(k[1], { x: 10.34, y, w: 2.4, h: 0.5, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 11, color: P.sea });
  });
  s.addText("8", { x: W - M - 0.6, y: 6.96, w: 0.6, h: 0.28, isTextBox: true,
    margin: 0, align: "right", fontFace: KR, fontSize: 9, color: P.muted });
  s.addNotes("요지는 'AI가 빨리 만든다'가 아니라 '틀린 채로 넘어가지 못하게 했다'입니다.");
}

/* ═══════════════════════════════════════════════ 9. 기대효과·확장 */
{
  const s = slide(false);
  head(s, "기대효과 · 향후 계획", "무엇이 좋아지고, 다음은 무엇인가");

  s.addText("기대효과", { x: M, y: 1.72, w: 5.9, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 15, bold: true, color: P.ink });
  const ba = [
    ["과제별 표를 사람 기준으로 손으로 합산", "사람별 월 합계가 자동으로 나온다"],
    ["문제가 생긴 뒤에 알게 됨", "몰리는 구간이 생기기 전에 보인다"],
    ["일정이 바뀌면 표를 다시 작성", "날짜만 고치면 바로 다시 계산된다"],
    ["숫자의 근거를 되짚기 어려움", "어떤 값에서 나왔는지 따라갈 수 있다"],
  ];
  ba.forEach((b, i) => {
    const y = 2.14 + i * 1.0;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 2.62, h: 0.8, rectRadius: 0.06,
      fill: { color: P.warmBg }, line: { color: "EDD3CA", width: 0.75 } });
    s.addText(b[0], { x: M + 0.14, y: y + 0.05, w: 2.34, h: 0.7, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, color: P.warmInk, lineSpacing: 14 });
    s.addImage({ path: ico("arrow_t"), x: M + 2.78, y: y + 0.31, w: 0.18, h: 0.18 });
    s.addShape(pres.ShapeType.roundRect, { x: M + 3.16, y, w: 2.74, h: 0.8, rectRadius: 0.06,
      fill: { color: P.tint }, line: { color: P.line, width: 0.75 } });
    s.addText(b[1], { x: M + 3.3, y: y + 0.05, w: 2.46, h: 0.7, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, color: P.ink, lineSpacing: 14 });
  });

  s.addText("향후 확장 계획", { x: 6.92, y: 1.72, w: 5.8, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 15, bold: true, color: P.ink });
  const road = [
    ["단기", "약 1~2주", P.teal, "배정되지 않은 과제의 필요량을 그래프에도 표시"],
    ["중기", "약 1~2개월", P.sea, "근무일·휴일 반영 · 두 가지 계획안을 나란히 비교"],
    ["장기", "별도 검토", P.mint, "여러 명이 동시에 쓰는 형태 · 인사 시스템 연계"],
  ];
  road.forEach((rd, i) => {
    const y = 2.14 + i * 1.34;
    card(s, 6.92, y, 5.79, 1.16);
    s.addShape(pres.ShapeType.roundRect, { x: 7.16, y: y + 0.22, w: 0.86, h: 0.34,
      rectRadius: 0.05, fill: { color: rd[2] } });
    s.addText(rd[0], { x: 7.16, y: y + 0.22, w: 0.86, h: 0.34, isTextBox: true, margin: 0,
      align: "center", valign: "middle", fontFace: KR, fontSize: 11, bold: true, color: P.white });
    s.addImage({ path: ico("clock_t"), x: 8.2, y: y + 0.29, w: 0.2, h: 0.2 });
    s.addText(rd[1], { x: 8.48, y: y + 0.22, w: 2, h: 0.34, isTextBox: true, margin: 0,
      valign: "middle", fontFace: KR, fontSize: 10.5, bold: true, color: P.teal });
    s.addText(rd[3], { x: 7.16, y: y + 0.64, w: 5.3, h: 0.42, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 15 });
  });
  s.addText("계산하는 부분과 보여주는 부분이 나뉘어 있어, 형태가 바뀌어도 숫자를 만드는 방식은 그대로 쓴다.", {
    x: 6.92, y: 6.1, w: 5.79, h: 0.44, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10, color: P.muted, lineSpacing: 14 });
  foot(s, 9);
  s.addNotes("기대효과는 '기대'입니다. 수작업 대비 절감 시간은 아직 측정하지 않았으므로 숫자로 말하지 않았습니다.");
}

/* ═══════════════════════════════════════════════ 10. Appendix */
{
  const s = slide(false);
  head(s, "APPENDIX", "주요 화면");

  const caps = [
    ["03_timeline.png", "과제 일정", "과제별 시작·종료와 단계별 구간. 어느 시기에 과제가 겹치는지 보인다."],
    ["05_resource_by_person.png", "사람별 월 투입량", "여러 과제를 합친 한 사람의 월별 부담. 과부하는 ▲, 여유는 ▼로 표시된다."],
    ["04_standard_vs_staffed.png", "기준 대비 투입", "과제가 표준만큼 받고 있는지. 줄을 누르면 그 달의 근거가 열린다."],
    ["07_project_utilisation.png", "과제별 추이", "선택한 과제의 월별 추이를 전체 평균과 함께 본다."],
  ];
  caps.forEach((c, i) => {
    const col = i % 2, row = (i / 2) | 0;
    const x = M + col * 6.13, y = 1.58 + row * 2.66;
    s.addText(c[1], { x, y, w: 5.83, h: 0.28, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 12.5, bold: true, color: P.teal });
    s.addImage({ path: path.join(__dirname, c[0]), x, y: y + 0.32, w: 5.83, h: 1.62 });
    s.addText(c[2], { x, y: y + 2.0, w: 5.83, h: 0.42, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 9.5, color: P.muted, lineSpacing: 14 });
  });
  foot(s, 10);
  s.addNotes("모두 실제 화면입니다. 예시 데이터는 62개 과제·20명 기준입니다.");
}

pres.writeFile({ fileName: "PRAP_소개자료.pptx" }).then(fn => console.log("written: " + fn));
"""

if __name__ == "__main__":
    raise SystemExit(main())
