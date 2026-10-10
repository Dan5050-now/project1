"""Build docs/PRAP_FTE_계산설명서.pdf - how a monthly FTE is arrived at.

A reference document, so precision matters more than brevity. Every figure in it is
produced by tools/fte_examples.py, which runs the REAL engine (tools/prap_io.py) rather
than re-deriving anything by hand - the same reference implementation the browser is
held to on every test run. Re-running this after a rule changes produces a document that
still matches the application.

The page is written as HTML and printed by the headless Chromium that is already here
for the test suites. LibreOffice in this container has no Writer/Impress filters, so
nothing else can make a PDF.

    python tools/fte_examples.py --json     figures first
    python tools/build_fte_doc.py           then the document

Output: docs/PRAP_FTE_계산설명서.pdf  (and the .html beside it, for checking)
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "output" / "deck" / "fte_examples.json"
OUT_HTML = ROOT / "output" / "deck" / "fte_doc.html"
OUT_PDF = ROOT / "docs" / "PRAP_FTE_계산설명서.pdf"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

CSS = """
@page { size: A4; margin: 17mm 15mm 16mm 15mm; }
* { box-sizing: border-box; }
body { font-family: "WenQuanYi Zen Hei", "맑은 고딕", sans-serif;
       font-size: 10.2pt; line-height: 1.62; color: #1d3238; margin: 0; }
h1 { font-size: 21pt; color: #0B3C44; margin: 0 0 6pt; letter-spacing: -0.3pt; }
h2 { font-size: 13.5pt; color: #0B3C44; margin: 20pt 0 7pt;
     padding-top: 8pt; border-top: 1.4pt solid #0B3C44; break-after: avoid; }
h3 { font-size: 11.2pt; color: #026C7A; margin: 13pt 0 5pt; break-after: avoid; }
p  { margin: 0 0 7pt; }
.lead { color: #4a686e; font-size: 10.5pt; margin-bottom: 14pt; }
.cover { padding: 26pt 0 16pt; border-bottom: 2.4pt solid #028090; margin-bottom: 16pt; }
.kick { color: #028090; font-weight: 700; font-size: 9.6pt; letter-spacing: 1pt; }
table { border-collapse: collapse; width: 100%; margin: 8pt 0 10pt; font-size: 9.3pt; }
th { background: #0B3C44; color: #fff; text-align: left; padding: 5pt 7pt; font-weight: 700; }
td { border-bottom: 0.7pt solid #d8e5e8; padding: 4.6pt 7pt; vertical-align: top; }
tr:nth-child(even) td { background: #f5fafb; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
td.tot { font-weight: 700; background: #eaf4f5 !important; border-top: 1.2pt solid #9cc3c9; }
.f { background: #0B3C44; color: #fff; padding: 11pt 13pt; border-radius: 4pt;
     margin: 9pt 0 11pt; font-size: 10.4pt; line-height: 1.85; }
.f b { color: #62d6c0; }
.f .w { color: #a9cbd1; font-size: 9.2pt; }
.note { background: #f2f8f9; border-left: 3pt solid #028090; padding: 8pt 11pt;
        margin: 8pt 0 11pt; font-size: 9.5pt; }
.warn { background: #fdf2ed; border-left: 3pt solid #C2603F; padding: 8pt 11pt;
        margin: 8pt 0 11pt; font-size: 9.5pt; color: #7d3a22; }
.q { font-weight: 700; color: #0B3C44; font-size: 10.6pt; margin: 2pt 0 6pt; }
.sc { break-inside: avoid; margin-bottom: 15pt; }
.chg { color: #C2603F; font-weight: 700; }
.same { color: #6b8a90; }
.up { color: #0a7d63; font-weight: 700; }
.badge { display: inline-block; background: #028090; color: #fff; border-radius: 3pt;
         padding: 1.4pt 7pt; font-size: 9pt; font-weight: 700; margin-right: 6pt; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; }
.card { background: #f5fafb; border: 0.7pt solid #d2e2e5; border-radius: 4pt; padding: 9pt 11pt; }
.card h4 { margin: 0 0 4pt; font-size: 10pt; color: #0B3C44; }
.card p { margin: 0; font-size: 9.3pt; color: #33545b; }
.pb { break-before: page; }
code { font-family: "Courier New", monospace; background: #eef5f6; padding: 0.5pt 3pt;
       border-radius: 2pt; font-size: 9pt; }
.foot { margin-top: 22pt; padding-top: 7pt; border-top: 0.7pt solid #d2e2e5;
        color: #6b8a90; font-size: 8.6pt; }
"""


def rows_table(rows, total, base=None, label="과제 합계"):
    """One scenario's figures. Where a base is given, mark what moved."""
    out = ['<table><tr><th>담당자</th><th>역할</th><th class="n">월 FTE</th>'
           '<th class="n">기준 대비</th></tr>']
    prev = {r["person"]: r["fte"] for r in (base or [])}
    for r in rows:
        p = r["person"] or "?"
        d = ""
        if base is not None:
            if p not in prev:
                d = '<span class="up">신규</span>'
            else:
                gap = round(r["fte"] - prev[p], 2)
                d = ('<span class="same">변화 없음</span>' if abs(gap) < 0.005
                     else f'<span class="chg">{gap:+.2f}</span>')
        out.append(f'<tr><td>{p}</td><td>{r["role"] or ""}</td>'
                   f'<td class="n">{r["fte"]:.2f}</td><td class="n">{d}</td></tr>')
    bt = ""
    if base is not None:
        g = round(total - sum(prev.values()), 2)
        bt = ('<span class="same">변화 없음</span>' if abs(g) < 0.005
              else f'<span class="chg">{g:+.2f}</span>')
    out.append(f'<tr><td class="tot" colspan="2">{label}</td>'
               f'<td class="tot n">{total:.2f}</td><td class="tot n">{bt}</td></tr>')
    return "".join(out) + "</table>"


def build_html(E):
    b = E["base"]
    H = []
    a = H.append

    a(f"<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
      f"<title>PRAP FTE 계산 설명서</title><style>{CSS}</style></head><body>")

    # ---- 표지 -------------------------------------------------------------
    a("<div class='cover'><div class='kick'>PRAP · 계산 설명서</div>"
      "<h1>월 FTE는 어떻게 계산되는가</h1>"
      "<p class='lead'>과제별·인력별 월 투입량이 어떤 값에서, 어떤 순서로 나오는지와 "
      "— 같은 역할에 인원이 늘어날 때, 가중치를 조정할 때, 월 FTE를 직접 지정할 때 — "
      "무엇이 어떻게 달라지는지를 정리한 문서.</p>"
      "<p class='lead' style='margin:0'>이 문서의 모든 숫자는 애플리케이션과 같은 계산 "
      "엔진으로 실제 계산한 값이다. 손으로 푼 값은 하나도 없다.</p></div>")

    # ---- 1. 한눈에 -------------------------------------------------------
    a("<h2>1. 계산의 뼈대 — 두 단계</h2>")
    a("<p>FTE는 사람마다 따로 계산해서 더하는 방식이 <b>아니다</b>. "
      "먼저 <b>과제가 그 달에 필요로 하는 양</b>을 정하고, 그 양을 <b>배정된 사람들이 "
      "나눠 갖는다</b>. 이 순서가 이 애플리케이션 계산의 전부이며, 뒤에 나오는 모든 "
      "고려사항은 이 두 단계 중 어느 쪽을 건드리는가로 설명된다.</p>")
    a("<div class='grid'>"
      "<div class='card'><h4>1단계 — 과제의 달 (수요)</h4>"
      "<p>과제 종류·임상 단계·아웃소싱 범위·기간이 <b>표준 월 FTE</b>를 정하고, "
      "과제별 <b>기간 가중치</b>가 이를 조정한다. 사람은 아직 등장하지 않는다.</p></div>"
      "<div class='card'><h4>2단계 — 사람의 몫 (배분)</h4>"
      "<p>역할 비중·개인 가중치·참여 기간으로 각자의 <b>지분</b>을 구하고, "
      "지분 비율대로 1단계의 양을 나눈다. 더하는 것이 아니라 나누는 것이다.</p></div></div>")
    a("<div class='warn'><b>가장 흔한 오해.</b> 역할계수 × 개인 가중치 × 참여 비율을 "
      "곱해서 그 값을 FTE라고 읽으면 안 된다. 그 곱은 <b>지분</b>이지 업무량이 아니다. "
      "지분을 지분 합으로 나눈 <b>비율</b>에 과제의 달을 곱한 것이 FTE다.</div>")

    # ---- 2. 입력 ---------------------------------------------------------
    a("<h2>2. 계산에 쓰이는 정보</h2>")
    a("<p>모두 소스 워크북에 있는 값이다. 프로그램 안에 숨어 있는 상수는 없다.</p>")
    a("<table><tr><th>값</th><th>어디에 있나</th><th>무엇을 정하는가</th></tr>"
      "<tr><td><b>표준 월 FTE</b></td><td>PeriodFTEStandard</td>"
      "<td>과제 종류·임상 단계·아웃소싱 범위·기간별로 '이 정도가 표준'인 월 투입량. "
      "<b>과제의 달 크기를 정하는 값</b>이다.</td></tr>"
      "<tr><td><b>기간 가중치</b></td><td>ProjectPeriod.weight</td>"
      "<td>이 과제가 같은 종류의 보통 과제보다 무거운지 가벼운지. 1.00이 보통.</td></tr>"
      "<tr><td><b>과제 운영 비율</b></td><td>ProjectPeriod 기간</td>"
      "<td>그 달에 과제가 실제로 돌아간 비율. 10일에 끝나면 그 달은 1/3만 필요하다.</td></tr>"
      "<tr><td><b>역할 비중</b></td><td>RoleFactor.role_factor</td>"
      "<td>그 기간에 각 역할이 차지하는 비중. 총량을 더하는 값이 아니라 나누는 값.</td></tr>"
      "<tr><td><b>대체 역할</b></td><td>RoleFactor.absorbed_by</td>"
      "<td>그 역할에 아무도 없을 때 누가 대신 떠안는지.</td></tr>"
      "<tr><td><b>개인 가중치</b></td><td>Assignment.person_weight</td>"
      "<td>그 사람이 그 과제에 얼마나 붙어 있는지.</td></tr>"
      "<tr><td><b>기간별 가중치 조정</b></td><td>PersonPeriodWeight.weight_override</td>"
      "<td>특정 기간만 다른 값을 쓸 때. 곱하는 것이 아니라 <b>대체</b>한다.</td></tr>"
      "<tr><td><b>참여 기간</b></td><td>Assignment 시작·종료일</td>"
      "<td>비워두면 과제의 기간을 그대로 쓴다. 부분 참여일 때만 적는다.</td></tr>"
      "<tr><td><b>직접 지정값</b></td><td>MonthlyEstimate.fte</td>"
      "<td>계산 대신 직접 적은 월 FTE. 과제 단위와 배정 단위 두 가지가 있다.</td></tr>"
      "<tr><td><b>가용 capacity</b></td><td>Person.capacity_fte</td>"
      "<td><b>계산에 쓰이지 않는다.</b> 그 사람이 쓸 수 있는 시간을 적어두는 값이다.</td></tr>"
      "</table>")

    # ---- 3. 수식 ---------------------------------------------------------
    a("<h2>3. 수식</h2>")
    a("<h3>3.1 과제의 달 — 수요</h3>"
      "<div class='f'><b>수요</b> = 표준 월 FTE × 기간 가중치 × 그 달의 과제 운영 비율"
      "<br><span class='w'>사람과 무관하게 정해진다. 배정이 하나도 없어도 이 값은 존재한다.</span></div>")
    a("<h3>3.2 한 사람의 지분</h3>"
      "<div class='f'><b>지분</b> = ( 역할 비중 ÷ 그 역할을 맡은 인원수 ) × 개인 가중치 × 그 달 참여 비율"
      "<br><span class='w'>업무량이 아니라 나눌 때 쓰는 상대적인 크기다.</span></div>")
    a("<h3>3.3 배분</h3>"
      "<div class='f'><b>월 FTE</b> = 수요 × ( 자기 지분 ÷ 그 과제·그 달의 지분 합계 )"
      "<br><span class='w'>지분 합으로 나누므로 비율의 합은 언제나 1이 되고, "
      "따라서 사람들의 몫을 더하면 정확히 과제의 그 달이 된다.</span></div>")
    a("<div class='note'><b>단위.</b> 1.00 FTE = 월 160시간(하루 8시간 × 주 5일 × 4주). "
      "0.01 FTE는 약 1.6시간이며, 이것이 이 계획에서 의미를 갖는 가장 작은 단위다.</div>")

    # ---- 4. 기준 예제 ----------------------------------------------------
    a("<h2>4. 기준 예제 — 끝까지 풀어보기</h2>")
    a("<p>아래 모든 예제는 같은 과제 하나를 쓴다. "
      "<b>NewDrug CT · Phase 3 · 자체 수행</b>, 기간은 <b>Conduct (final)</b>, "
      "보고 있는 달은 <b>2026년 6월</b>이다.</p>")
    a("<table><tr><th>단계</th><th>값</th><th class='n'>결과</th></tr>"
      "<tr><td>표준 월 FTE</td><td>이 종류·단계·범위·기간의 기준표 값</td><td class='n'>3.47</td></tr>"
      "<tr><td>× 기간 가중치</td><td>보통 과제이므로 1.00</td><td class='n'>× 1.00</td></tr>"
      "<tr><td>× 운영 비율</td><td>6월 한 달 내내 진행</td><td class='n'>× 1.00</td></tr>"
      "<tr><td class='tot'>그 달의 수요</td><td class='tot'></td><td class='tot n'>3.47</td></tr>"
      "</table>")
    a("<p>세 사람이 각각 다른 역할을 맡고, 모두 이 과제에 온전히(가중치 1.00) 한 달 내내 "
      "참여한다. 각자의 지분은 곧 역할 비중이 된다.</p>")
    a("<table><tr><th>담당자</th><th>역할</th><th class='n'>역할 비중</th>"
      "<th class='n'>지분</th><th class='n'>비율</th><th class='n'>월 FTE</th></tr>"
      "<tr><td>김 O O</td><td>Lead data manager</td><td class='n'>1.26</td>"
      "<td class='n'>1.26</td><td class='n'>36.2%</td><td class='n'>1.26</td></tr>"
      "<tr><td>이 O O</td><td>Clinical Data Associator</td><td class='n'>1.37</td>"
      "<td class='n'>1.37</td><td class='n'>39.4%</td><td class='n'>1.36</td></tr>"
      "<tr><td>박 O O</td><td>Data Analyst</td><td class='n'>0.85</td>"
      "<td class='n'>0.85</td><td class='n'>24.4%</td><td class='n'>0.85</td></tr>"
      "<tr><td class='tot' colspan='3'>합계</td><td class='tot n'>3.48</td>"
      "<td class='tot n'>100%</td><td class='tot n'>3.47</td></tr></table>")
    a("<div class='note'>지분의 합(3.48)과 수요(3.47)가 다른 것은 정상이다. "
      "지분은 나누는 데 쓰는 상대적 크기일 뿐이고, 실제로 나눠지는 것은 수요 3.47이다. "
      "그래서 월 FTE 열의 합은 정확히 3.47이 된다.</div>")

    # ---- 5. 고려사항 -----------------------------------------------------
    a("<h2>5. 계산에서 고려되는 사항</h2>")
    a("<p>기준 예제에서 <b>한 번에 하나씩만</b> 바꿔 무엇이 달라지는지 본다. "
      "'기준 대비' 열은 4장의 기준 예제와 비교한 차이다.</p>")

    order = [("A", "같은 역할에 인원이 늘어날 때"), ("B", "개인 가중치를 조정할 때"),
             ("C", "기간 가중치를 조정할 때"), ("D", "달의 일부만 참여할 때"),
             ("G", "역할에 아무도 배정되지 않을 때"),
             ("E", "배정 단위로 월 FTE를 직접 지정할 때"),
             ("F", "과제 단위로 월 FTE를 직접 지정할 때"),
             ("H", "개인 capacity를 조정할 때")]
    for i, (k, heading) in enumerate(order, start=1):
        s = E[k]
        a(f"<div class='sc'><h3><span class='badge'>{i}</span>{heading}</h3>")
        a(f"<p class='q'>{s['question']}</p>")
        a(rows_table(s["rows"], s["total"], b["rows"]))
        a(f"<p>{s['note']}</p>")
        if k == "A":
            a("<div class='note'>역할 비중 1.26을 두 사람이 나눠 각각 0.63을 주장한다. "
              "한 사람이 빠지면 남은 사람이 다시 1.26을 온전히 주장하므로, "
              "누구도 손대지 않아도 원래대로 돌아간다.</div>")
        if k == "G":
            a("<div class='note'>Clinical Data Associator의 비중 1.37이 사라지지 않고 "
              "기준표에 적힌 대체 역할(Lead data manager)로 넘어가, 그 사람의 실효 비중이 "
              "1.26 + 1.37 = 2.63이 된다. 그래서 1.26이던 몫이 2.62로 늘었다. "
              "<b>한 단계만</b> 넘긴다 — 대체 역할마저 비어 있으면 더 넘기지 않고 경고로 알린다.</div>")
        if k == "E":
            a("<div class='warn'>배정 단위 지정은 그 사람의 몫만 대체하므로 "
              "과제 합계가 표준(3.47)과 달라진다(4.11). 이것은 오류가 아니라 "
              "누군가 의도한 결정이며, 앱은 '표준 대비 과부족'으로 따로 표시한다.</div>")
        if k == "F":
            a("<div class='note'>과제 단위 지정은 그 달 전체를 대체하고, 배정된 사람들은 "
              "원래 비율 그대로 다시 나눈다. 그래서 합계는 적은 값(5.00)과 정확히 같다. "
              "배정된 사람이 한 명도 없는 달에 적은 값은 나눠 줄 대상이 없어 적용되지 않고 "
              "경고로 알린다.</div>")
        if k == "H":
            a("<div class='note'>capacity는 과부하 판정에도 쓰이지 않는다. "
              "과부하·여유 기준은 개인별 capacity 비례가 아니라 <b>정해진 절대값</b>과 비교한다"
              "(기본값: 월 1.50 FTE 초과는 과부하, 0.60 미만이 3개월 연속이면 여유). "
              "capacity는 0.00~1.00 범위를 벗어나면 입력 단계에서 걸러진다.</div>")
        a("</div>")

    # ---- 6. 집계 ---------------------------------------------------------
    a("<h2>6. 집계 — 과제별과 인력별</h2>")
    a("<p>위에서 구한 것은 <b>배정 하나의 한 달</b> 값이다. 화면의 표는 이것을 두 방향으로 "
      "합친 것이다.</p>")
    a("<table><tr><th>보는 방향</th><th>합치는 대상</th><th>쓰임</th></tr>"
      "<tr><td><b>과제별 월 FTE</b></td><td>그 과제의 모든 배정</td>"
      "<td>과제가 그 달에 얼마나 필요한지. 자동 계산된 달이면 수요와 정확히 같다.</td></tr>"
      "<tr><td><b>인력별 월 FTE</b></td><td>그 사람의 모든 배정 (여러 과제에 걸쳐)</td>"
      "<td>한 사람이 그 달에 얼마나 바쁜지. <b>과부하·여유 판정은 이 값으로 한다.</b></td></tr>"
      "<tr><td><b>과제 × 사람 × 역할</b></td><td>합치지 않은 가장 작은 단위</td>"
      "<td>근거 확인용. 화면에서 과제 행을 펼치면 나온다.</td></tr></table>")
    a("<div class='note'>두 표는 같은 숫자를 다른 축으로 합친 것이므로 <b>전체 합계가 "
      "반드시 일치한다.</b> 다만 아직 아무도 배정되지 않은 과제의 필요량은 어느 사람에게도 "
      "속하지 않으므로 합계에 넣지 않고 따로 표시한다.</div>")

    # ---- 7. 반올림 -------------------------------------------------------
    a("<h2>7. 반올림 규칙</h2>")
    a("<p>모든 FTE는 <b>소수점 두 자리</b>다. 두 자리로 보여주는 것이 아니라 두 자리"
      "<b>인</b> 값이다.</p>")
    a("<p>반올림은 <b>과제의 달 하나에 대해 한 번만</b> 한다. 먼저 그 달을 두 자리로 정한 "
      "뒤, 그 값을 1/100 단위로 사람들에게 나눠 준다. 나머지가 생기면 소수 부분이 큰 쪽부터 "
      "하나씩 배분한다. 각자의 몫을 따로 반올림하면 합계가 어긋나므로 이 순서가 중요하다.</p>")
    a("<div class='note'>이 규칙 덕분에 <b>사람별 값을 더하면 반드시 과제의 달과 같아진다.</b> "
      "그 대신 개인의 값은 자기 항들의 정확한 곱과 최대 0.01까지 차이날 수 있다 — "
      "결과 파일에는 그 사실이 함께 적힌다.</div>")

    # ---- 8. 값이 없을 때 --------------------------------------------------
    a("<h2>8. 값이 비어 있을 때</h2>")
    a("<table><tr><th>없는 값</th><th>어떻게 처리하나</th></tr>"
      "<tr><td>표준 월 FTE</td><td>1.00으로 두고 <b>알려준다.</b> 그러면 그 달은 기간 "
      "가중치만큼이 되므로, 예전 방식과 같은 모양의 숫자가 나온다.</td></tr>"
      "<tr><td>기간 (어느 기간에도 속하지 않는 달)</td>"
      "<td>가중치를 1.00으로 두고 알려준다.</td></tr>"
      "<tr><td>역할 비중</td><td>알려준다. 조용히 1.00을 쓰면 틀린 값이 그대로 흘러가므로, "
      "이 경우는 오류로 다룬다.</td></tr>"
      "<tr><td>배정 시작·종료일</td><td>과제의 시작·종료일을 그대로 쓴다. "
      "대부분의 배정이 과제 전체 기간이므로 비워두는 것이 정상이다.</td></tr>"
      "<tr><td>수동 지정인데 그 달 값이 없음</td>"
      "<td>0.00으로 계산되며 <b>반드시 알려준다.</b> 값이 조용히 0이 되는 경우는 이 하나뿐이라 "
      "특별히 다룬다.</td></tr>"
      "<tr><td>없는 과제·사람을 가리키는 배정</td>"
      "<td>계산에서 빼고 알려준다.</td></tr></table>")

    a("<div class='foot'>이 문서의 모든 수치는 애플리케이션과 동일한 계산 엔진으로 "
      "산출되었다 (tools/fte_examples.py → tools/prap_io.py). "
      "예시 과제: NewDrug CT · Phase 3 · 자체 수행 · Conduct (final) · 2026년 6월.</div>")
    a("</body></html>")
    return "".join(H)


def main():
    if not DATA.exists():
        raise SystemExit("먼저 실행: python tools/fte_examples.py --json")
    E = json.loads(DATA.read_text(encoding="utf-8"))
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(E), encoding="utf-8")

    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=CHROME)
        pg = b.new_page()
        pg.goto(OUT_HTML.as_uri())
        pg.wait_for_timeout(700)
        OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
        pg.pdf(path=str(OUT_PDF), format="A4", print_background=True,
               margin={"top": "17mm", "bottom": "16mm", "left": "15mm", "right": "15mm"})
        b.close()
    kb = OUT_PDF.stat().st_size / 1024
    print(f"written: {OUT_PDF.relative_to(ROOT)}  ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
