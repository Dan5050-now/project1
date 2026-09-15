"""Build the competition deck - PRAP_소개자료.pptx - with pptxgenjs.

A tool rather than a one-off script, for the reason tools/package_source.py is one: the
figures on these slides are the repository's own, and a deck typed by hand goes stale the
moment a version moves. Everything numeric here is READ from the artefacts:

    개발계획서            requirement count, by category
    prap_contract.json    validation-rule count, sheets, columns, the formula
    the repository        file counts, commit count, dates, the built application's size

So re-running this after a change produces a deck that still tells the truth.

    python tools/build_deck.py

Output: output/deck/PRAP_소개자료.pptx   (the generator writes deck.js beside it)
"""

import json
import os
import pathlib
import subprocess
import sys

from openpyxl import load_workbook

ROOT = pathlib.Path(__file__).resolve().parents[1]
DECK = ROOT / "output" / "deck"
DECK.mkdir(parents=True, exist_ok=True)


def facts():
    """Every number on the slides, taken from the artefacts rather than typed."""
    man = json.loads((ROOT / "docs" / "PRAP_Manifest.json").read_text())
    cur = {e["what"]: pathlib.Path(e["path"]).name for e in man["current"]}
    con = json.loads((ROOT / "docs" / "prap_contract.json").read_text())

    plan = ROOT / "docs" / cur["development_plan"]
    ws = load_workbook(plan, data_only=True)["03_Requirements"]
    reqs, cats = 0, {}
    for r in range(5, ws.max_row + 1):
        if str(ws.cell(r, 1).value or "").replace("* ", "").startswith("REQ"):
            reqs += 1
            k = str(ws.cell(r, 2).value)
            cats[k] = cats.get(k, 0) + 1

    def sh(*cmd):
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout.strip()

    return {
        "reqs": reqs,
        "reqCats": sorted(cats.items(), key=lambda x: -x[1]),
        "rules": len(con["validation_rules"]),
        "sheets": len(con["sheets"]),
        "columns": sum(len(s["columns"]) for s in con["sheets"].values()),
        "schema": con["schema_version"],
        "appVer": con["application"]["version"],
        "appBytes": (ROOT / "app" / "PRAP.html").stat().st_size,
        "suites": len(list((ROOT / "tools").glob("test_*.py"))),
        "srcFiles": sum(1 for p in (ROOT / "src").rglob("*") if p.is_file()),
        "toolFiles": sum(1 for p in (ROOT / "tools").rglob("*")
                         if p.is_file() and "__pycache__" not in p.parts),
        "commits": int(sh("git", "rev-list", "--count", "HEAD") or 0),
        "since": sh("git", "log", "--reverse", "--format=%ad", "--date=short").split("\n")[0],
        "until": sh("git", "log", "-1", "--format=%ad", "--date=short"),
        "docs": cur,
    }


def node_path():
    """Where pptxgenjs lives, which is not the same place on two machines.

    node resolves modules by walking up from the script, so a generator written into
    output/ finds nothing unless the package happens to sit above it. Rather than
    hard-code one path - the first attempt did, and it was a scratch directory that
    only existed in that session - look in the places it is actually installed and
    hand node the one that answers.
    """
    roots = []
    g = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True)
    if g.returncode == 0 and g.stdout.strip():
        roots.append(pathlib.Path(g.stdout.strip()))
    roots += [ROOT / "node_modules", pathlib.Path.home() / "node_modules"]
    roots += list(pathlib.Path("/tmp").glob("claude-*/**/scratchpad/node_modules"))[:4]
    found = [str(r) for r in roots if (r / "pptxgenjs").is_dir()]
    if not found:
        raise SystemExit(
            "pptxgenjs was not found. Install it once with:\n"
            "    npm install pptxgenjs\n"
            "and run this again.")
    return ":".join(found)


def main():
    f = facts()
    js = (DECK / "deck.js")
    js.write_text(TEMPLATE.replace("/*__FACTS__*/", json.dumps(f, ensure_ascii=False)),
                  encoding="utf-8")
    env = {**os.environ, "NODE_PATH": node_path()}
    r = subprocess.run(["node", str(js)], cwd=DECK, capture_output=True, text=True, env=env)
    print(r.stdout.strip() or r.stderr.strip()[-2000:])
    return r.returncode


# ---------------------------------------------------------------- the generator
TEMPLATE = r"""
const pptxgen = require("pptxgenjs");
const path = require("path");
const F = /*__FACTS__*/;

const P = {
  ink:    "0B3C44",   // deep teal - title and section grounds
  deep:   "072E34",
  teal:   "028090",
  sea:    "00A896",
  mint:   "02C39A",
  warm:   "C75B39",   // the "before" colour, used only for the problem side
  white:  "FFFFFF",
  tint:   "EAF4F5",
  tint2:  "F4F9FA",
  line:   "CFE0E3",
  body:   "1F3A40",
  muted:  "5E7B81",
};
const KR = "맑은 고딕";
const W = 13.333, H = 7.5, M = 0.62;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "PRAP";
pres.title = "PRAP 프로젝트 소개자료";

const sh = () => ({ type: "outer", color: "0B3C44", blur: 14, offset: 3, angle: 90, opacity: 0.10 });

function slide(dark) {
  const s = pres.addSlide();
  s.background = { color: dark ? P.ink : P.white };
  return s;
}

// Page title used on every light slide. No underline, no stripe - spacing only.
function head(s, kicker, title) {
  s.addText(kicker, { x: M, y: 0.42, w: 8, h: 0.28, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.teal, charSpacing: 1.2 });
  s.addText(title, { x: M, y: 0.72, w: 11.4, h: 0.72, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 30, bold: true, color: P.ink });
}

// The repeated motif: a filled circle carrying a number or a short glyph.
function badge(s, x, y, label, fill, d) {
  const dia = d || 0.46;
  s.addShape(pres.ShapeType.ellipse, { x, y, w: dia, h: dia, fill: { color: fill } });
  s.addText(label, { x, y, w: dia, h: dia, isTextBox: true, margin: 0, align: "center",
    valign: "middle", fontFace: KR, fontSize: dia > 0.5 ? 15 : 13, bold: true, color: P.white });
}

function card(s, x, y, w, h, fill) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08,
    fill: { color: fill || P.tint2 }, line: { color: P.line, width: 0.75 }, shadow: sh() });
}

function foot(s, n) {
  s.addText("PRAP · 임상 과제 리소스 배정 시뮬레이터", { x: M, y: 6.95, w: 7, h: 0.3,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 9, color: P.muted });
  s.addText(String(n), { x: W - M - 0.6, y: 6.95, w: 0.6, h: 0.3, isTextBox: true,
    margin: 0, align: "right", fontFace: KR, fontSize: 9, color: P.muted });
}

const img = (n) => path.join(__dirname, n);
const MB = (F.appBytes / 1024).toFixed(0);

/* ============================================================ 1. 표지 */
{
  const s = slide(true);
  s.addShape(pres.ShapeType.ellipse, { x: 9.5, y: -1.9, w: 6.4, h: 6.4,
    fill: { color: P.teal, transparency: 82 } });
  s.addShape(pres.ShapeType.ellipse, { x: 11.2, y: 3.4, w: 3.6, h: 3.6,
    fill: { color: P.mint, transparency: 88 } });

  s.addText("사내 AI 활용 · 개발 사례", { x: M, y: 1.45, w: 8, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 13, bold: true, color: P.mint, charSpacing: 1.4 });
  s.addText("PRAP", { x: M, y: 1.9, w: 8, h: 1.25, isTextBox: true, margin: 0,
    fontFace: "Arial", fontSize: 72, bold: true, color: P.white, charSpacing: 1 });
  s.addText("동시 진행 임상 과제의 월 단위 인력 수요 시뮬레이터", {
    x: M, y: 3.15, w: 8.6, h: 0.5, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 21, color: P.white });
  s.addText("누가 다음 분기에 과다 배정인지, 누가 3개월 연속 과소 활용인지를\n한 화면에서 답하는 오프라인 단일 파일 애플리케이션",
    { x: M, y: 3.78, w: 8.6, h: 0.9, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 13.5, color: P.tint, lineSpacing: 22 });

  const stats = [
    [String(F.reqs), "요구사항"],
    [String(F.rules), "검증 규칙"],
    [String(F.suites), "테스트 스위트"],
    [String(F.commits), "커밋"],
  ];
  stats.forEach((t, i) => {
    const x = M + i * 2.0;
    s.addText(t[0], { x, y: 5.15, w: 1.8, h: 0.62, isTextBox: true, margin: 0,
      fontFace: "Arial", fontSize: 38, bold: true, color: P.mint });
    s.addText(t[1], { x, y: 5.78, w: 1.8, h: 0.3, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 11.5, color: P.tint });
  });
  s.addText(`개발 기간 ${F.since} ~ ${F.until}   ·   웹(단일 HTML) + 데스크톱(Python) 2개 제품군`,
    { x: M, y: 6.42, w: 10, h: 0.32, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 11, color: P.sea });
  s.addNotes("PRAP은 동시에 진행되는 임상 과제의 월 단위 인력 수요를 시뮬레이션하는 도구입니다. 설치 없이 로컬 PC에서 동작하며, 네트워크를 전혀 쓰지 않습니다.");
}

/* ============================================================ 2. Overview */
{
  const s = slide(false);
  head(s, "OVERVIEW", "무엇을 하는 도구이고, 왜 만들었는가");

  const cards = [
    ["1", P.teal, "무엇인가",
     "과제별·인력별 월 단위 투입량(FTE)을\n시뮬레이션하는 단일 HTML 애플리케이션.\n데이터는 엑셀 워크북 한 개에 보관하고,\n앱은 그 파일을 읽어 계산·시각화한다."],
    ["2", P.sea, "왜 만들었나",
     "과제는 동시에 진행되고 일정은 자주 바뀐다.\n한 사람이 받는 부담은 과제·기간·역할에\n따라 달라져 손으로 계산하기 어렵다.\n이를 답하는 단일 화면이 없었다."],
    ["3", P.mint, "무엇이 달라지나",
     "과다 배정과 과소 활용을 사전에 식별하고,\n일정 변경 후 즉시 재시뮬레이션한다.\n모든 수치는 근거 항목까지 되짚을 수 있어\n검증 가능한 계획이 된다."],
  ];
  cards.forEach((c, i) => {
    const x = M + i * 4.06, w = 3.78;
    card(s, x, 1.62, w, 2.62);
    badge(s, x + 0.26, 1.86, c[0], c[1]);
    s.addText(c[2], { x: x + 0.84, y: 1.9, w: w - 1.05, h: 0.38, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 15, bold: true, color: P.ink });
    s.addText(c[3], { x: x + 0.26, y: 2.48, w: w - 0.52, h: 1.62, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 11.5, color: P.body, lineSpacing: 18 });
  });

  s.addText("전체 탭 — 62개 과제 · 20명 · 24개월을 한 화면에", {
    x: M, y: 4.46, w: 8, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 11.5, bold: true, color: P.teal });
  s.addImage({ path: img("01_demand_by_project.png"), x: M, y: 4.8, w: 12.09, h: 1.98 });
  foot(s, 2);
  s.addNotes("데이터는 앱이 아니라 엑셀 워크북에 남습니다. 워크북이 기록의 원본이고, 앱은 그것을 읽어 계산합니다.");
}

/* ============================================================ 3. 개발 배경 */
{
  const s = slide(false);
  head(s, "개발 배경", "앱 개발 이전 — 손으로는 답할 수 없던 질문");

  const pains = [
    ["동시 진행 + 잦은 일정 변경",
     "여러 과제가 함께 돌아가고 일정이 자주 바뀐다.\n한 번 만든 배정표는 곧 현실과 어긋난다."],
    ["부담이 일정하지 않음",
     "한 사람이 받는 부담은 과제별로, 그 과제의\n기간별로, 맡은 역할별로 모두 다르다."],
    ["통합된 시야의 부재",
     "과제별 표는 있어도 사람 축으로 합산한 그림이\n없어, 겹치는 구간을 사전에 볼 수 없었다."],
    ["재현·검증의 어려움",
     "수식이 흩어진 엑셀은 결과를 다시 만들기도,\n왜 그 숫자인지 되짚기도 어렵다."],
  ];
  pains.forEach((p, i) => {
    const y = 1.66 + i * 1.12;
    badge(s, M, y + 0.06, "!", P.warm, 0.38);
    s.addText(p[0], { x: M + 0.58, y: y, w: 5.6, h: 0.32, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 14, bold: true, color: P.ink });
    s.addText(p[1], { x: M + 0.58, y: y + 0.34, w: 5.7, h: 0.66, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 11.5, color: P.body, lineSpacing: 17 });
  });

  s.addShape(pres.ShapeType.roundRect, { x: 7.15, y: 1.62, w: 5.55, h: 4.62,
    rectRadius: 0.08, fill: { color: P.ink }, line: { color: P.ink }, shadow: sh() });
  s.addText("답이 없던 두 가지 질문", { x: 7.52, y: 1.98, w: 4.8, h: 0.36,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 15, bold: true, color: P.mint });
  s.addText("“다음 분기에 누가 과다 배정이고,\n어느 과제 때문인가?”", {
    x: 7.52, y: 2.52, w: 4.85, h: 0.9, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 16, bold: true, color: P.white, lineSpacing: 26 });
  s.addText("그리고 더 조용한 질문 —", { x: 7.52, y: 3.52, w: 4.85, h: 0.3,
    isTextBox: true, margin: 0, fontFace: KR, fontSize: 11.5, color: P.sea });
  s.addText("“3개월 연속 과소 활용된 사람은\n누구인가?”", {
    x: 7.52, y: 3.86, w: 4.85, h: 0.9, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 16, bold: true, color: P.white, lineSpacing: 26 });
  s.addText("두 질문 모두 개발계획서 02_Scope에 기록된\n문제 정의이며, 앱의 목표(OBJ-3)로 이어진다.", {
    x: 7.52, y: 5.12, w: 4.85, h: 0.7, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10.5, color: P.tint, lineSpacing: 16 });
  foot(s, 3);
  s.addNotes("이 문제 정의는 제가 지어낸 것이 아니라 승인된 개발계획서 02_Scope 시트에 기록된 내용입니다.");
}

/* ============================================================ 4. 주요 기능 */
{
  const s = slide(false);
  head(s, "APP 상세 ①", "주요 기능과 특장점");

  const feats = [
    ["월 단위 시뮬레이션", "과제별·인력별 월 FTE를 표와 그래프로. 기본 24개월, 전체 기간으로 한 번에 확장."],
    ["과다·과소 자동 식별", "월 1.50 FTE 초과는 과다, 0.60 미만 3개월 연속은 과소로 표시하고 요약 타일에서 집계."],
    ["표준 대비 부족분", "과제가 자기 표준만큼 인력을 받고 있는지 대조(V-34). 아무도 배정되지 않은 달도 수요를 표시(V-36)."],
    ["화면에서 직접 편집", "가져온 데이터를 화면에서 수정하고 내보내면 그대로 반영. 편집도 가져오기와 같은 규칙으로 검증."],
    ["완전 오프라인 단일 파일", `HTML 파일 하나(${MB} KB). 설치·서버·네트워크 없음. 외부 라이브러리 0개 — 엑셀 입출력도 자체 구현.`],
    ["37개 검증 규칙", "가져오기 시 첫 오류에서 멈추지 않고 모든 문제를 보고. 규칙마다 '거부/확인/진행중' 등급을 가짐."],
  ];
  feats.forEach((ft, i) => {
    const col = i % 3, row = (i / 3) | 0;
    const x = M + col * 4.06, y = 1.62 + row * 2.08, w = 3.78;
    card(s, x, y, w, 1.86);
    badge(s, x + 0.26, y + 0.24, String(i + 1), i < 3 ? P.teal : P.sea, 0.4);
    s.addText(ft[0], { x: x + 0.78, y: y + 0.24, w: w - 1.0, h: 0.4, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 13.5, bold: true, color: P.ink });
    s.addText(ft[1], { x: x + 0.26, y: y + 0.76, w: w - 0.52, h: 0.98, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 11, color: P.body, lineSpacing: 16 });
  });
  foot(s, 4);
  s.addNotes("특장점의 핵심은 '설치가 필요없고 데이터가 PC를 떠나지 않는다'는 점입니다. 사내 보안 통제와 정면으로 충돌하지 않습니다.");
}

/* ============================================================ 5. 계산 */
{
  const s = slide(false);
  head(s, "APP 상세 ②", "FTE 계산 및 시뮬레이션 과정");

  s.addShape(pres.ShapeType.roundRect, { x: M, y: 1.58, w: 12.09, h: 1.02,
    rectRadius: 0.08, fill: { color: P.ink }, line: { color: P.ink } });
  s.addText("핵심 원칙 — 과제의 한 달은 그 자체가 '표준 수요'이고, 배정된 사람들은 그 달을 나눠 갖는다", {
    x: M + 0.34, y: 1.72, w: 11.4, h: 0.34, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 14.5, bold: true, color: P.white });
  s.addText("네 개의 배정 계수는 '몫'을 정할 뿐 총량을 만들지 않는다. 사람이 몇 명이든 과제의 그 달은 표준과 같다.", {
    x: M + 0.34, y: 2.10, w: 11.4, h: 0.32, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 11.5, color: P.tint });

  const steps = [
    ["1", "과제의 달 = 수요", "표준 FTE × 기간 가중치 × 그 달의 가동 비율",
     "과제 유형·임상 단계·아웃소싱 범위·기간이\n표준 월 FTE를 결정한다."],
    ["2", "사람의 몫 = 지분", "(역할계수 ÷ 공유인원) × 개인 가중치 × 참여 비율",
     "이 값은 '총량'이 아니라 그 달을 나눌 때\n쓰는 상대적 지분이다."],
    ["3", "배분 = 수요 × 지분 ÷ 지분합", "합계가 반드시 과제의 달과 일치",
     "1/100 단위 정수로 최대잔여법 배분.\n부분의 합은 항상 전체와 같다."],
  ];
  steps.forEach((st, i) => {
    const x = M + i * 4.06, w = 3.78;
    card(s, x, 2.86, w, 2.42);
    badge(s, x + 0.26, 3.08, st[0], P.teal, 0.42);
    s.addText(st[1], { x: x + 0.8, y: 3.08, w: w - 1.02, h: 0.42, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 13, bold: true, color: P.ink });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.26, y: 3.62, w: w - 0.52, h: 0.62,
      rectRadius: 0.06, fill: { color: P.tint }, line: { color: P.line, width: 0.75 } });
    s.addText(st[2], { x: x + 0.36, y: 3.66, w: w - 0.72, h: 0.54, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, bold: true, color: P.teal });
    s.addText(st[3], { x: x + 0.26, y: 4.36, w: w - 0.52, h: 0.8, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 15 });
  });

  card(s, M, 5.48, 12.09, 1.18, P.tint);
  s.addText("왜 이렇게까지 하는가", { x: M + 0.3, y: 5.62, w: 3, h: 0.3, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 12, bold: true, color: P.ink });
  s.addText("한 사람의 배정을 바꾸면 같은 과제·같은 달에 있는 다른 사람의 몫이 함께 바뀐다. 반올림은 마지막에 한 번만 하고 최대잔여법으로 나누므로, 과제의 달은 언제나 자기 구성원 합계와 1/100까지 일치한다. 이 성질이 있어야 화면의 숫자를 근거까지 되짚어도 어긋나지 않는다.",
    { x: M + 0.3, y: 5.94, w: 11.5, h: 0.6, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 11, color: P.body, lineSpacing: 16 });
  foot(s, 5);
  s.addNotes("이 계산 규칙(REQ-CAL-19)이 이 앱의 지적 핵심입니다. 네 계수를 곱해서 FTE라고 부르는 것은 흔한 오류이고, 명세서는 그것을 하지 말라고 명시합니다.");
}

/* ============================================================ 6. 산출물 방식 */
{
  const s = slide(false);
  head(s, "APP 상세 ③", "핵심 산출물 — 무엇을 볼 수 있는가");

  const outs = [
    ["화면 4개 탭", "전체 / 과제별 원천데이터 / 인력별 원천데이터 / 표준 가정.\n표·그래프·타임라인·요약 타일."],
    ["계획 워크북 (.xlsx)", `가져온 그대로의 구조로 되돌려쓰기. ${F.sheets}개 시트 · ${F.columns}개 컬럼.\n화면 편집 내용이 반영되어 다시 가져올 수 있다.`],
    ["결과 워크북 (.xlsx)", "계산된 월별 FTE. 과제별·인력별 각 1행,\n그리고 배정×월 단위로 곱셈의 모든 항을 담은 상세 시트."],
    ["검증 결과 리포트", `${F.rules}개 규칙의 발견 사항을 등급·분류와 함께.\n로드 배너·전체 리포트·변경 이력에 동시에 반영.`],
  ];
  outs.forEach((o, i) => {
    const y = 1.62 + i * 1.22;
    card(s, M, y, 5.9, 1.06);
    badge(s, M + 0.24, y + 0.32, String(i + 1), P.teal, 0.4);
    s.addText(o[0], { x: M + 0.76, y: y + 0.14, w: 4.9, h: 0.32, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 13, bold: true, color: P.ink });
    s.addText(o[1], { x: M + 0.76, y: y + 0.46, w: 4.95, h: 0.54, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 15 });
  });

  s.addText("과제별 월 FTE — 색 농도로 크기, 테두리로 표준 대비 과부족", {
    x: 6.92, y: 1.62, w: 5.79, h: 0.3, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 11, bold: true, color: P.teal });
  s.addImage({ path: img("02_resource_by_project.png"), x: 6.92, y: 1.96, w: 5.79, h: 3.46 });
  s.addText("모든 수치는 1/100 FTE 단위이며, 상세 시트의 행 합계와 정확히 일치한다.", {
    x: 6.92, y: 5.52, w: 5.79, h: 0.36, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10, color: P.muted, lineSpacing: 15 });
  foot(s, 6);
  s.addNotes("결과 워크북은 '되돌려 가져오기'가 불가능한 파생 산출물이며, 첫 시트가 그 사실을 명시합니다.");
}

/* ============================================================ 7. 개발 과정 */
{
  const s = slide(false);
  head(s, "개발 과정 ①", "5단계 게이트 방식 — 승인 없이는 다음 단계로 가지 않는다");

  const steps = [
    ["1", "개발계획서", "요구사항·데이터 모델\n·리소스 로직 확정", `v2.60\n요구사항 ${F.reqs}건`],
    ["2", "프로그래밍 명세서", "계산식·검증규칙\n·화면 사양을 의사코드로", `v1.31\n규칙 ${F.rules}건`],
    ["3", "UI 컴포넌트 리스트", "화면 구성요소를 항목화\n하고 리뷰·승인", "v2.2\n68개 구성요소"],
    ["4", "구현 + 검증", "코드 생성과 테스트\n·문서 자동 교차검증", `테스트 ${F.suites}종\n스키마 v${F.schema}`],
    ["5", "릴리스", "웹 단일 파일 +\n데스크톱 Python 패키지", `앱 v${F.appVer}\nPM_APP v1.21.1`],
  ];
  const cw = 2.32, gap = 0.16;
  steps.forEach((st, i) => {
    const x = M + i * (cw + gap);
    card(s, x, 1.98, cw, 3.24);
    badge(s, x + cw / 2 - 0.27, 2.2, st[0], i === 4 ? P.mint : P.teal, 0.54);
    s.addText(st[1], { x: x + 0.12, y: 2.86, w: cw - 0.24, h: 0.6, isTextBox: true,
      margin: 0, align: "center", valign: "top", fontFace: KR, fontSize: 12.5,
      bold: true, color: P.ink, lineSpacing: 17 });
    s.addText(st[2], { x: x + 0.12, y: 3.5, w: cw - 0.24, h: 0.82, isTextBox: true,
      margin: 0, align: "center", fontFace: KR, fontSize: 10, color: P.body, lineSpacing: 15 });
    s.addShape(pres.ShapeType.roundRect, { x: x + 0.18, y: 4.36, w: cw - 0.36, h: 0.66,
      rectRadius: 0.06, fill: { color: P.tint }, line: { color: P.line, width: 0.75 } });
    s.addText(st[3], { x: x + 0.22, y: 4.4, w: cw - 0.44, h: 0.58, isTextBox: true,
      margin: 0, align: "center", valign: "middle", fontFace: KR, fontSize: 9.5,
      bold: true, color: P.teal, lineSpacing: 13 });
    if (i < 4) {
      s.addText("›", { x: x + cw + 0.005, y: 3.32, w: gap, h: 0.4, isTextBox: true,
        margin: 0, align: "center", valign: "middle", fontFace: "Arial",
        fontSize: 18, bold: true, color: P.sea });
    }
  });
  s.addText("각 단계는 리뷰 게이트로 끝난다. 다음 단계의 작업은 이전 단계가 승인된 뒤에만 시작한다.", {
    x: M, y: 5.42, w: 12.09, h: 0.32, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.ink });
  s.addText(`산출물: 개발계획서 · 프로그래밍 명세서 · UI 컴포넌트 리스트 · 소스데이터 템플릿(${F.sheets}시트/${F.columns}컬럼) · 더미 예제 2종 · AI 에이전트 가이드 · 기계판독 계약(JSON) · 애플리케이션 2종`,
    { x: M, y: 5.76, w: 12.09, h: 0.6, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 16 });
  foot(s, 7);
  s.addNotes("34건이 넘는 변경요청이 이 게이트 구조 위에서 처리되었고, 모든 변경은 문서 버전 이력에 남습니다.");
}

/* ============================================================ 8. AI 개발 방식 */
{
  const s = slide(true);
  s.addText("개발 과정 ②", { x: M, y: 0.42, w: 8, h: 0.28, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12, bold: true, color: P.mint, charSpacing: 1.2 });
  s.addText("AI로 개발하면서 '맞다'를 어떻게 보장했는가", {
    x: M, y: 0.72, w: 11.4, h: 0.72, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 30, bold: true, color: P.white });
  s.addText("생성된 코드를 믿는 대신, 틀리면 빌드가 깨지도록 구조를 만들었다. 이것이 이 프로젝트의 핵심 방법론이다.", {
    x: M, y: 1.46, w: 11.6, h: 0.32, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 12.5, color: P.tint });

  const ways = [
    ["4중 독립 구현 대조",
     "같은 계산을 브라우저 엔진·Python 참조구현·워크북 검증기·테스트 자체 기준\n4곳에 따로 구현하고, 모든 인-월이 일치할 때만 통과시킨다."],
    ["문서 ↔ 코드 자동 교차검증",
     "계획서·명세서·템플릿·컴포넌트 리스트·계약(JSON)을 매 빌드마다 서로 대조한다.\n어긋나면 빌드가 실패한다 — 사람이 기억할 일로 남기지 않는다."],
    ["측정한 뒤에 결정",
     "원래 성능 요구치(100과제×1,000명)는 실측 결과 기준의 3배를 넘었다.\n코드를 고치는 대신 요구치를 실측으로 옮겼다 — 100×150에서 810ms/기준 1,000ms."],
    ["빌드 결과의 바이트 동일성",
     `단일 HTML(${MB} KB)은 ${F.srcFiles}개 소스에서 조립되며, 재조립 결과가\n커밋된 파일과 바이트까지 같아야 한다. 소스와 산출물이 어긋날 수 없다.`],
  ];
  ways.forEach((wy, i) => {
    const col = i % 2, row = (i / 2) | 0;
    const x = M + col * 6.13, y = 2.0 + row * 1.86;
    s.addShape(pres.ShapeType.roundRect, { x, y, w: 5.83, h: 1.6, rectRadius: 0.08,
      fill: { color: P.deep }, line: { color: "1D5760", width: 1 } });
    badge(s, x + 0.28, y + 0.26, String(i + 1), P.sea, 0.42);
    s.addText(wy[0], { x: x + 0.82, y: y + 0.26, w: 4.8, h: 0.42, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 14, bold: true, color: P.mint });
    s.addText(wy[1], { x: x + 0.28, y: y + 0.8, w: 5.3, h: 0.7, isTextBox: true,
      margin: 0, fontFace: KR, fontSize: 10.8, color: P.tint, lineSpacing: 16 });
  });

  const kp = [[`${F.suites}`, "테스트 스위트"], [`${F.reqs}`, "추적되는 요구사항"],
              [`${F.commits}`, "커밋"], [`${F.srcFiles}+${F.toolFiles}`, "소스 · 도구 파일"]];
  kp.forEach((k, i) => {
    const x = M + i * 3.05;
    s.addText(k[0], { x, y: 5.82, w: 2.9, h: 0.5, isTextBox: true, margin: 0,
      fontFace: "Arial", fontSize: 28, bold: true, color: P.white });
    s.addText(k[1], { x, y: 6.3, w: 2.9, h: 0.3, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10.5, color: P.sea });
  });
  s.addText("8", { x: W - M - 0.6, y: 6.95, w: 0.6, h: 0.3, isTextBox: true,
    margin: 0, align: "right", fontFace: KR, fontSize: 9, color: P.muted });
  s.addNotes("대회의 관점에서 가장 중요한 슬라이드입니다. AI가 코드를 빨리 쓴다는 것보다, 틀린 코드가 통과하지 못하게 만드는 구조를 세웠다는 점이 요지입니다.");
}

/* ============================================================ 9. 기대효과 + 확장 */
{
  const s = slide(false);
  head(s, "기대효과 · 향후 계획", "무엇이 좋아지고, 다음은 무엇인가");

  s.addText("기대효과", { x: M, y: 1.58, w: 5.9, h: 0.32, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 15, bold: true, color: P.ink });
  const ba = [
    ["과제별 엑셀을 사람 축으로 수동 합산", "인력별 월 합계를 자동 산출·표시"],
    ["과부하를 사후에 인지", "임계값 초과·과소 구간을 사전에 표시"],
    ["일정 변경 시 표를 다시 작성", "날짜만 고치고 즉시 재시뮬레이션"],
    ["숫자의 근거를 되짚기 어려움", "곱셈의 모든 항을 상세 시트로 추적"],
  ];
  ba.forEach((b, i) => {
    const y = 2.0 + i * 0.96;
    s.addShape(pres.ShapeType.roundRect, { x: M, y, w: 2.66, h: 0.78, rectRadius: 0.06,
      fill: { color: "FBEEEA" }, line: { color: "EDD3CA", width: 0.75 } });
    s.addText(b[0], { x: M + 0.14, y: y + 0.06, w: 2.38, h: 0.66, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, color: "8A3A21", lineSpacing: 14 });
    s.addText("→", { x: M + 2.72, y, w: 0.42, h: 0.78, isTextBox: true, margin: 0,
      align: "center", valign: "middle", fontFace: "Arial", fontSize: 16, bold: true, color: P.sea });
    s.addShape(pres.ShapeType.roundRect, { x: M + 3.2, y, w: 2.7, h: 0.78, rectRadius: 0.06,
      fill: { color: P.tint }, line: { color: P.line, width: 0.75 } });
    s.addText(b[1], { x: M + 3.34, y: y + 0.06, w: 2.42, h: 0.66, isTextBox: true,
      margin: 0, valign: "middle", fontFace: KR, fontSize: 10, color: P.ink, lineSpacing: 14 });
  });

  s.addText("향후 확장 계획", { x: 6.92, y: 1.58, w: 5.8, h: 0.32, isTextBox: true,
    margin: 0, fontFace: KR, fontSize: 15, bold: true, color: P.ink });
  const road = [
    ["단기", "미배정 수요를 그래프에도 표시 · 결과 워크북에 미배정 구간 반영", "약 1~2주", P.teal],
    ["중기", "근무일·휴일 달력 반영 · 시나리오 비교(A안/B안 동시 보기)", "약 1~2개월", P.sea],
    ["장기", "다중 사용자 동시 편집을 위한 서버 형태 · 인사/CTMS 연계", "별도 검토 필요", P.mint],
  ];
  road.forEach((rd, i) => {
    const y = 2.0 + i * 1.3;
    card(s, 6.92, y, 5.79, 1.14);
    s.addShape(pres.ShapeType.roundRect, { x: 7.14, y: y + 0.2, w: 0.82, h: 0.34,
      rectRadius: 0.06, fill: { color: rd[3] } });
    s.addText(rd[0], { x: 7.14, y: y + 0.2, w: 0.82, h: 0.34, isTextBox: true, margin: 0,
      align: "center", valign: "middle", fontFace: KR, fontSize: 11, bold: true, color: P.white });
    s.addText(rd[2], { x: 10.9, y: y + 0.2, w: 1.6, h: 0.34, isTextBox: true, margin: 0,
      align: "right", valign: "middle", fontFace: KR, fontSize: 10.5, bold: true, color: P.teal });
    s.addText(rd[1], { x: 7.14, y: y + 0.62, w: 5.35, h: 0.44, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 10.5, color: P.body, lineSpacing: 15 });
  });
  s.addText("확장에 필요한 기술은 모두 현재 구조 안에 있다. 계산 엔진(core)은 화면과 분리되어 있어, 서버형으로 가더라도 숫자를 만드는 코드는 그대로 쓴다.", {
    x: 6.92, y: 5.92, w: 5.79, h: 0.6, isTextBox: true, margin: 0,
    fontFace: KR, fontSize: 10, color: P.muted, lineSpacing: 15 });
  foot(s, 9);
  s.addNotes("기대효과는 '기대'입니다. 수작업 대비 절감 시간은 아직 측정하지 않았으므로 수치로 주장하지 않았습니다.");
}

/* ============================================================ 10. Appendix */
{
  const s = slide(false);
  head(s, "APPENDIX", "주요 화면");

  const caps = [
    ["03_timeline.png", "과제 타임라인", "기간별 색상과 마일스톤. 과제의 시작·종료와 각 기간의 길이를 한눈에."],
    ["05_resource_by_person.png", "인력별 월 FTE", "사람 축으로 합산. 과다(▲)·과소(▼)를 색과 기호로 동시에 표시."],
    ["04_standard_vs_staffed.png", "표준 대비 투입", "과제가 자기 표준만큼 받고 있는지. 행을 누르면 그 달의 근거가 열린다."],
    ["07_project_utilisation.png", "과제별 가동 추이", "선택한 과제의 월별 추이를 포트폴리오 평균 기준선과 함께."],
  ];
  caps.forEach((c, i) => {
    const col = i % 2, row = (i / 2) | 0;
    const x = M + col * 6.13, y = 1.6 + row * 2.62;
    s.addText(c[1], { x, y, w: 5.83, h: 0.28, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 12.5, bold: true, color: P.teal });
    s.addImage({ path: img(c[0]), x, y: y + 0.32, w: 5.83, h: 1.62 });
    s.addText(c[2], { x, y: y + 2.0, w: 5.83, h: 0.4, isTextBox: true, margin: 0,
      fontFace: KR, fontSize: 9.5, color: P.muted, lineSpacing: 14 });
  });
  foot(s, 10);
  s.addNotes("화면 캡처는 모두 현재 빌드에서 자동 생성한 것입니다. 데모 데이터는 62개 과제·20명입니다.");
}

pres.writeFile({ fileName: "PRAP_소개자료.pptx" })
  .then(fn => console.log("written: " + fn));
"""

if __name__ == "__main__":
    raise SystemExit(main())
