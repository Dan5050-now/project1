# PRAP / PM_APP v1.20 설계 검토 및 서버 전환 검토서

**개정 2판 (v2).** 1판은 `PM_APP_python_v1.20.zip` + 문서 3종만으로 작성했습니다. 2판은 `PRAP_documents_v2.54.zip`과 `PRAP_tools_v1.0.zip`을 추가로 받아 **도구를 실제로 실행하고 테스트를 돌려** 작성했습니다. 그 결과 **1판의 주요 판단 5건을 정정**하고, 대신 **1판에서는 확인할 수 없었던 강력한 긍정 증거와 새로운 공백**을 얻었습니다.

| 항목 | 내용 |
|---|---|
| 검토 대상 | `PM_APP_python_v1.20.zip` (Python shell 1.20 + 화면 1.50) — 1판과 **바이트 단위 동일** 확인 |
| 추가 입수 | NewApp Specification v1.5, NewApp Development Plan v1.13, `tools/` 46개 파일, `prap_contract.json`, `PRAP_Manifest.json`, 50×50 시나리오 워크북, `PRAP.html` |
| 검토 방법 | 소스 전체 정독 + 문서 6종 대조 + **테스트 스위트 37개 실행** + 엔진 일치성 실증 + 동시성 실측 |
| 검토 일자 | 2026-09-12 |
| 독자 | IT 비전문가 포함 |

---

## 0. 요약 — 2판의 결론

1. **계산이 맞다는 것이 이제 실증되었습니다.** 1판에서는 "확인할 도구가 없다"고 썼습니다. 이번에는 도구를 돌렸습니다. 배포된 PM_APP을 실제 브라우저로 구동해 **3,304개 person-month를 독립 참조 구현과 하나씩 비교한 결과 최대 오차 0.00e+00**, 전 항목 통과(0 failed)했습니다. 저장 계층은 80개 테스트 전부 통과했고, 여기에는 **"여덟 개 프로세스가 동시에 경쟁해 정확히 하나만 승리"** 까지 포함됩니다. 이것은 추측이 아니라 실행 결과입니다.

2. **1판의 핵심 전제가 틀렸습니다.** 1판은 *"동시 편집은 설계 범위 밖이고, 가정 A-06('한 번에 한 사람만')이 유효하다"* 고 썼습니다. **이는 구(舊) 웹앱 계획서(v2.54)의 내용이었습니다.** 데스크톱 앱을 지배하는 문서는 NewApp 계획서 v1.13과 NewApp 스펙 v1.5이고, 그쪽에서는 **가정 A-N03이 라운드 2에서 철회(WITHDRAWN)** 되었으며 *"공유 폴더를 쓰면 한 사람만 쓴다고 가정하는 것이 안전하지 않으므로, 애플리케이션은 더 이상 그 가정에 의존하지 않는다"* 고 명시합니다. 공유 사용은 **설계되어 있습니다** (스펙 `07_Sharing`, 계획서 `05a_Sharing`).

3. **그래서 문제의 성격이 바뀝니다 — 더 나쁜 쪽이 아니라, 더 고치기 쉬운 쪽으로.** 제가 1판에서 지적한 결함 3건은 "설계에 없던 것"이 아니라 **"설계되고 승인까지 받았는데 배선되지 않은 것"** 입니다. 각각 요구사항 번호가 붙어 있습니다 — **NR-STO-16**(정전 감지), **NR-STO-07**(복구), **NR-STO-15**(잠금 해제). 스펙은 제 지적을 정확히 예견하고 있었고, 저장 계층 함수도 이미 있고 테스트도 통과합니다. **빠진 것은 화면과 서버를 잇는 배선뿐입니다.**

4. **요청하신 레코드 단위 잠금은 여전히 구조 변경입니다.** 다만 근거가 더 분명해졌습니다. 스펙과 계획서가 **명시적으로 거부(N-20)** 하며 그 이유를 이렇게 씁니다 — *"한 계획의 서로 다른 부분을 두 사람이 동시에 편집하는 것은 다른 제품이고, 저장 형식이 갖고 있지 않은 병합 모델을 필요로 한다."* 제 1판 결론과 같은 결론이며, 이제 설계자 자신의 논리로 뒷받침됩니다.

5. **새로운, 그리고 가장 심각한 공백: `src/` 폴더가 없습니다.** `PM_APP` 안의 모든 파이썬 파일과 `index.html`은 **`tools/build_python_app.py`가 `src/`에서 생성하는 산출물**입니다. `src/`가 없으면 빌드도, 아키텍처 검사도, 저장 계층 테스트도 불가능하고, **무엇보다 배포본을 직접 고치면 다음 빌드가 그 수정을 조용히 덮어씁니다.** 1판에서 제가 드린 "이 파일을 고치세요"라는 권고는 **대상이 틀렸습니다.**

---

## 1. 1판에서 정정할 내용 — 먼저 밝힙니다

이 프로젝트의 문서 규율(은퇴한 규칙까지 이유와 함께 남기는 방식)을 따라, 무엇이 틀렸고 왜 틀렸는지 명시합니다.

| # | 1판의 서술 | 판정 | 정정 내용 |
|---|---|---|---|
| **C-1** | *"가정 A-06('한 번에 한 사람만')이 Standing = 현재도 유효"* | ❌ **철회** | 인용한 문서가 잘못되었습니다. A-06은 **웹앱** 계획서의 가정입니다. 데스크톱 앱의 대응 가정 **A-N03은 라운드 2에서 WITHDRAWN** 되었고, *"enforced by NR-STO-10 instead"* 로 대체되었습니다. 즉 데스크톱 앱은 단일 사용자를 **가정하지 않습니다.** |
| **C-2** | *"동시 편집과 권한이 Out of scope로 확정(Q-12)"* | ⚠️ **범위 정정** | 그 Out of scope는 **웹앱**(단일 HTML 파일)의 범위입니다. 데스크톱 앱은 공유를 **설계**합니다 — 스펙 `07_Sharing`이 4개 세션 상태(READING/EDITING/BLOCKED/STALE)와 7가지 사용자 메시지를 규정합니다. **다만 "레코드 단위" 잠금만은 별도로 명시 거부(N-20)** 되어 있어, 요청사항 b)에 대한 제 결론 자체는 유지됩니다. |
| **C-3** | *"결함 3(작업 유실)은 방지 절차가 없다"* | ⚠️ **더 정확하게** | 방지 절차는 **설계되어 있고 승인까지 받았습니다.** 스펙 `12_Open_Points`의 **S-N01: "정전 확인은 `stat()`을 10초마다 폴링한다 → AGREED"**. 요구사항 **NR-STO-16**: *"읽는 세션은 디스크에서 워크스페이스가 바뀐 것을 알아채고, 그렇다고 말하고, 재로드를 제안한다. 이미 대체된 수치를 현재 수치인 것처럼 절대 제시하지 않는다."* → **구현만 안 되었습니다.** 이것은 설계 누락이 아니라 **미구현 요구사항**이며, 훨씬 명확한 지적입니다. |
| **C-4** | *"결함 5: 모든 PC에 파이썬 설치 필요 (설계 미흡)"* | ⚠️ **경위 정정** | 의도적이고 **실측에 근거한** 선택입니다. **R-N20**: *"exe는 실행은 되지만 도착하지 못한다 — 이메일이 거부하고, 이메일이 유일한 경로다."* **R-N21**: *"데이터가 브라우저 파일 선택창으로 들어갈 수 없다."* 두 통제를 회사 PC에서 직접 측정한 뒤, **통제를 우회하지 않고 통제가 작용하는 대상 자체를 제거**하는 방식으로 답한 것입니다. **R-N01은 CLOSED** — *"파이썬 셸이 회사 PC에서 실행되었다."* 다만 **그것은 요청자 본인의 PC 1대**이므로, 다수 사용자 배포 시의 확인 필요성은 남습니다. |
| **C-5** | *"IT팀 질문 8번: GxP/CSV 검증 대상인지 확인 필요"* | ❌ **철회** | **이미 답이 있습니다.** 가정 **A-N11: "이 도구에는 어떤 내부 밸리데이션·적격성평가·기록보관 의무도 적용되지 않는다" — CONFIRMED at Q-N09.** 관련 위험 **R-N16**도 이에 따라 Low/Low로 하향되었습니다. 질문 목록에서 뺍니다. (단, 중앙 서버로 가면 *GxP*가 아니라 *사내 IT 변경관리* 대상이 될 수 있으므로 그 질문은 남깁니다.) |
| **C-6** | *"1단계 응급 수정: `index.html`, `server.py`, `workspace.py`를 고치세요"* | ❌ **대상 정정** | 그 파일들은 **생성 산출물**입니다. 수정은 `src/shell/python/server.py`, `src/storage/python/workspace.py`, `src/shell/python/bridge.js` 등에 들어가야 하고, **`src/`가 전달되지 않았습니다.** 배포본을 직접 고치면 다음 빌드가 되돌립니다. |

**정정 후에도 유지되는 1판의 판단**: 결함 2·3·4의 존재(요구사항 번호가 붙어 더 강해짐), 결함 1(사용자별 개인 폴더), 결함 6·7, 문서 지적 D-3·D-4·D-5, 그리고 **4부 전체 — 요청하신 a)b)는 중앙 서버 + DB 구조 변경이 필요하다**는 결론.

---

## 2. 이제 실증된 것 — 1판에서는 불가능했던 검증

### 2.1 계산이 맞습니다 (가장 중요한 확인)

배포된 `PM_APP`을 그대로 `dist/PM_APP_py`에 놓고, 실제 Chromium을 띄워 `tools/test_python_app.py`를 돌렸습니다.

```
the page
  ok   the page loads without a script error
  ok   THERE IS NO FILE INPUT ON THE PAGE (R-N21)   0 found
  ok   the web application's picker has been removed, not hidden
importing, without the browser seeing a file
  ok   Python read the workbook off the disk   131,666 bytes
  ok   the data is all there   50 projects, 50 people, 292 assignments
  ok   EVERY FIGURE EQUALS THE PYTHON REFERENCE IMPLEMENTATION
       3304 person-months compared, worst difference 0.00e+00
keeping it
  ok   the plan is on the disk   /tmp/pm-run-.../data/test.prap
  ok   and re-opening it gives back the identical figures   worst difference 0.00e+00
one writer at a time, on the live application
  ok   taking the claim writes a marker beside the plan
  ok   which names the person a blocked colleague should ask   Test Person (Verification)
getting data back out
  ok   and the exported workbook gives the same figures again   worst difference 0.00e+00
  ok   every row of it is its demand times its share, to the hundredth   1,580 rows checked
leaving the machine as it found it
  ok   nothing is written outside the application folder

0 failed
```

> **비유**: 1판에서는 *"저울이 정확하다고 적혀 있지만 분동(分銅)이 함께 오지 않았다"* 고 썼습니다. 이번에는 분동을 받아 **3,304번 달아봤고, 단 한 번도 어긋나지 않았습니다.**

**이것이 의미하는 바**: 계산 엔진은 **가장 값비싼 자산이며, 신뢰할 수 있습니다.** 나중에 서버로 옮길 때 "숫자가 조용히 달라지는" 최악의 사고(위험 N-03)를 막을 **기준선이 이제 손에 있습니다.**

### 2.2 저장 계층과 동시성 원시 기능이 견고합니다

```
tools/test_storage_py.py  →  80 passed, 0 failed
  ok    eight processes race, exactly one wins        ← 동시성의 핵심
  ok    and the winner is the one in the file
  ok    releasing frees it
  ok    somebody else's heartbeat does nothing
  ok    rule 4: a read-only folder means ASK, at launch
  ok    and it says so rather than failing at the first save
  ok    a journal older than the plan is not offered
```

`tools/test_shutdown.py` → **FAILURES: none** (수명주기·`--keep-running` 포함)

**여덟 개 프로세스가 경쟁해 정확히 하나만 이긴다**는 것은, 1판에서 칭찬한 `O_EXCL` 배타 생성 방식이 **말뿐이 아니라 실제로 검증되어 있다**는 뜻입니다.

### 2.3 검증 도구가 작동합니다

```
python3 tools/prap_io.py validate templates/PRAP_SourceData_Scenarios_50x50_v1.0.xlsx
  → 12 finding(s): 8 warning, 4 information   (오류 0건)
```

그리고 **앱이 보고한 findings 8건과 참조 구현이 보고한 warning 8건이 정확히 일치**했습니다. 즉 화면과 독립 검증기가 데이터 판정에서도 어긋나지 않습니다.

### 2.4 테스트 스위트 실행 결과 총괄

| 구분 | 개수 | 내용 |
|---|---|---|
| **완전 통과** | **14** | `test_python_app`, `test_storage_py`, `test_shutdown`, `test_absorb`, `test_blank`, `test_blankdates`, `test_derive`, `test_entry`, `test_gap`, `test_generate`, `test_lookup`, `test_nodates`, `test_roleshare`, `test_standard` |
| 픽스처 교체로 일부 실패 | 3 | `test_app`(핵심 일치성 검증은 통과, "파일이 깨끗하다"는 전제만 실패), `test_rows`, `test_valuelist` — **제품 결함이 아니라 제가 다른 워크북을 넣은 탓** |
| 누락 파일로 미실행 | 20 | 대부분 `PRAP_SourceData_Dummy_v1.18.xlsx` / `_10x10_v1.10.xlsx` 부재. `test_layers`는 `src/` 부재 |

**정직하게 밝히는 한계**: 예제 워크북 2종이 없어 50×50 시나리오 워크북으로 대체 투입했습니다. 대체가 정당한 이유는 `test_app`·`test_python_app`의 핵심 단정이 **"앱 결과 == 참조 구현 결과"** 라는 데이터 무관 비교이기 때문입니다. 반면 `test_rows`(ASG-001 존재 가정), `test_valuelist`('Compound A' 존재 가정)는 특정 데이터를 전제하므로 실패했고, **이 3건을 제품 결함으로 집계하지 않았습니다.**

---

## 3. 확인된 결함 — 개정판

1판의 결함 번호를 유지하되, 요구사항 번호와 실행 증거를 붙였습니다.

### 🔴 결함 A (신규, 최우선). `src/` 폴더가 없어 고칠 수 없습니다

`tools/build_python_app.py`를 읽어 확인한 생성 매핑입니다.

```
src/storage/python/timefmt.py    →  PM_APP/pmapp/storage/timefmt.py
src/storage/python/workspace.py  →  PM_APP/pmapp/storage/workspace.py
src/storage/python/claim.py      →  PM_APP/pmapp/storage/claim.py
src/shell/python/paths.py        →  PM_APP/pmapp/shell/paths.py
src/shell/python/files.py        →  PM_APP/pmapp/shell/files.py
src/shell/python/server.py       →  PM_APP/pmapp/shell/server.py
src/shell/python/launch.py       →  PM_APP/pmapp/shell/launch.py
src/core/* + src/ui/* + src/shell/python/{chrome,bridge,importdiff}
                                 →  PM_APP/app/index.html  (조립 생성)
```

실제 빌드 시도 결과:

```
FileNotFoundError: .../src/shell/python/chrome.css
```

> **비유**: 자동차와 정비 매뉴얼과 공구함까지 다 받았습니다. 그런데 **설계도면(`src/`)이 없습니다.** 공구로 분해는 할 수 있지만, 부품을 새로 깎을 수는 없습니다. 게다가 이 차는 **도면에서 매번 새로 조립되는 방식**이라, 완성차에 용접을 해두면 다음 조립 때 사라집니다.

**영향**

| 할 수 없는 일 | 이유 |
|---|---|
| 결함 B·C·D 수정 | 수정 대상이 `src/`에 있음. 배포본 직접 수정은 다음 빌드가 덮어씀 |
| `tools/build_python_app.py` 실행 | `src/` 부재 |
| `tools/test_layers.py` 실행 | 아키텍처 경계 검사("파이썬 모듈이 화면을 언급하면 빌드 실패") 불가 |
| `tools/package_windows.py` 실행 | `src/` 부재 |

### 🔴 결함 B (1판 결함 3). 정전 감지 미구현 — **NR-STO-16 미이행**

승인된 요구사항 원문:

> **NR-STO-16** — *"A reading session notices when the workspace has changed on disk beneath it, says so, and offers to reload. **It never presents figures it knows to be superseded as though they were current.**"*
>
> **S-N01** (스펙 `12_Open_Points`) — *"정전 확인은 `stat()`을 10초마다 폴링한다."* → **AGREED**
>
> **스펙 `07_Sharing`의 STALE 상태** — *"the file changed on disk, polled by `stat()` every 10 s … Editing is refused until it reloads."*

실측 확인 (새 zip 기준, 동적 호출 가능성까지 배제):

```
index.html 내 "ws/stat"   → 0회
index.html 내 call( 형태   → call("리터럴") 과 정의부 call(op, body) 뿐  (동적 호출 없음)
"stale" 검색 결과          → 전부 S.stale (UI 탭 재렌더링용) — 전혀 다른 개념
save_workspace 내 mtime/버전 확인 → 없음
```

즉 **설계된 STALE 상태 자체가 존재하지 않습니다.** 1판에 쓴 유실 시나리오가 그대로 성립합니다.

```
09:00  A가 편집 시작 (잠금 획득)
09:05  B가 "보기만" 함 → 잠금 없음, B 브라우저에 09:05 데이터
09:30  A가 저장
09:35  A 종료 → 잠금 해제
09:40  B가 한 칸 수정 → 잠금 획득 성공
09:41  B가 저장 → B의 09:05 데이터가 파일 전체를 덮어씀
       ⚠ A의 30분 작업이 경고 한 줄 없이 사라짐 — NR-STO-16이 막으려 한 바로 그 일
```

### 🔴 결함 C (1판 결함 4). 복구 기록 미구현 — **NR-STO-07 미이행**

> **NR-STO-07** — *"Edits pending at the moment of a crash or power loss are recovered on the next launch, and the user is asked whether to keep or discard them."*

```
index.html 내 "journal/write"  → 0회
index.html 내 "journal/read"   → 1회
```

**읽는 쪽만 있고 쓰는 쪽이 없습니다.** 그래서 프로그램은 파일을 열 때마다 "미저장 변경이 있나?"를 묻고 **영구히 "없다"는 답만 받습니다.**

그런데 **저장 계층 함수는 정확하고 테스트도 통과합니다.**

```
tools/test_storage_py.py  test_journal()
  → WS.write_journal() 을 직접 호출해서 검사 → 통과
  → 페이지가 journal/write 를 호출하는지 검사하는 테스트: tools/ 전체에 0건
```

이것이 세 결함의 공통 구조입니다.

| 요구사항 | 저장 계층 함수 | 함수 테스트 | 페이지 배선 | 배선 테스트 | 결과 |
|---|---|---|---|---|---|
| NR-STO-07 복구 | `write_journal()` 있음 | ✅ 통과 | ❌ 없음 | ❌ 없음 | 복구할 것이 없음 |
| NR-STO-15 해제 | `release_claim()` 있음 | ✅ 통과 | ❌ 없음 | ❌ 없음 | 종료 시에만 해제 |
| NR-STO-16 정전 | `WS.stat()` 있음 | — | ❌ 없음 | ❌ 없음 | 작업 유실 가능 |

> **비유**: 건물에 스프링클러 배관과 물탱크가 완벽하게 설치되어 있고 수압 시험도 통과했습니다. **그런데 화재감지기와 배관을 잇는 전선이 연결되지 않았습니다.** 배관을 검사한 사람은 합격 판정을 내렸고, 그 판정은 옳습니다 — 검사 범위가 배관까지였기 때문입니다.

### 🔴 결함 D (1판 결함 2). 잠금 미해제 — **NR-STO-15 부분 미이행**

> **NR-STO-15** — *"The claim ends when the holder **saves and closes**, **discards their edits**, or closes the application."*

세 경로 중 **애플리케이션 종료만 구현**되어 있습니다(`app.shutdown()` → `release_claim`). `claim/release` API 호출 0회.

1판의 실측이 새 zip에서도 그대로 재현됩니다.

```
잠금 A 획득 → 성공, 현재 파일 = planA.prap
잠금 B 획득 → 성공, 현재 파일 = planB.prap
A의 잠금 파일이 아직 존재?     → True      ← 해제되지 않음
프로그램 종료 후 → A 잠김: True | B 잠김: False
```

원인은 `stop_heartbeat()`이 변수만 비우고 스레드를 멈추지 않는 것, 그리고 종료 시 해제 대상이 "현재 파일" 하나뿐인 것입니다. **계획 A는 30분 만료까지, 프로그램을 켜둔 채면 하루 종일 잠깁니다.**

### 🟠 결함 E (1판 결함 1). 기본 데이터 폴더가 사용자별로 분리됩니다

이것은 **스펙된 동작**입니다 — `10_Deployment`의 데이터 폴더 해결 규칙 3, 그리고 **S-N06 AGREED** (*"윈도우 계정명으로 키를 잡는다 — 선언된 이름은 편집 가능하고 충돌할 수 있다"*).

```
\\server\share\PM_APP\data\users\kim_ch\workspaces\
\\server\share\PM_APP\data\users\lee_sy\workspaces\
```

그런데 **`07_Sharing`은 여러 명이 같은 계획을 여는 것을 전제로 설계되어 있습니다.** 두 설계가 서로 당깁니다: 기본 위치는 개인별로 갈라놓고, 공유 규칙은 같은 파일을 볼 것을 가정합니다. 문서에는 **"개인 폴더에 있는 계획을 팀이 함께 열기까지의 워크플로"** 가 없습니다.

**따라서 이것은 결함이라기보다 설계 공백입니다** — 공유할 계획을 어디에 두고 어떻게 찾아가는지를 정하는 **한 줄의 운영 규칙**이 빠져 있습니다. (예: `data\shared\workspaces\`를 만들고 "최근 목록"에 고정)

### 🟠 결함 F (1판 결함 5·6 통합). 배포 관문

| 항목 | 상태 |
|---|---|
| 파이썬 필요 | 의도적 선택(R-N20/R-N21, C-4 참조). **요청자 PC 1대에서는 실행 확인(R-N01 CLOSED)** |
| 다수 사용자 PC | **미확인.** 회사 표준 PC에 Python 3.9+ 와 tkinter가 있는지는 별개 문제 |
| `package_windows.py` | **도움이 안 됩니다.** 이것은 폐기된 Electron 경로(PM_APP.exe + Chromium)를 묶는 스크립트이고, `VERSION = "0.1"`, 그리고 스스로 *"이것은 테스트된 윈도우 빌드가 아니다. 윈도우에서 실행된 적이 없다(R-N06)"* 고 밝힙니다 |
| `os.access()` 쓰기 판정 | 1판 지적 유지. 단 `test_storage_py`의 *"rule 4: 읽기 전용 폴더는 실행 시점에 묻는다"* 는 통과 — **리눅스에서는** 정확합니다. 윈도우 ACL에서의 부정확성은 여전히 미검증(R-N06) |

### 🟡 결함 G (1판 결함 7). 변경 이력 동시 이어쓰기

1판 지적 유지. `test_audit.py`가 있으나 **예제 워크북 부재로 실행하지 못했습니다.** 윈도우 SMB에서의 이어쓰기 원자성은 여전히 미검증입니다.

---

## 4. 문서 검토 — 개정판

### 4.1 1판 지적의 처리

| # | 1판 지적 | 2판 판정 |
|---|---|---|
| D-1 | 파이썬 버전의 설계서가 없다 | ✅ **해소** — NewApp Specification v1.5 입수. 품질 매우 높음 |
| D-2 | 계획서가 파이썬 버전을 반영하지 못했다 | ✅ **철회** — NewApp 계획서 v1.13이 반영하고 있었습니다. 소켓 문제도 `05a_Python_Shell`에서 6개 통제와 함께 정면 답변 |
| D-3 | 규모 재기준(100/1,000)의 실측 기록이 없다 | ⚠️ **유지** — 다만 50×50 / 292 배정 / 3,304 person-month에서는 정상 동작 확인 |
| D-4 | 스키마 버전 불일치 (화면 12 / 파이썬 5) | ⚠️ **유지** — 새 zip에서도 동일 |
| D-5 | 버전 번호가 두 개 (1.20 / 1.50) | ⚠️ **유지 + 확대** (아래 D-6) |

### 4.2 신규 문서 지적

| # | 지적 | 근거 |
|---|---|---|
| **D-6** | **파이썬 셸이 올라탄 스펙 개정판이 미승인 상태입니다** | 스펙 v1.5 표지: *"Status: **v1.2 APPROVED** 2026-08-13 and still governing. THIS ISSUE, **v1.3**, adds change C-N02 - the Python shell - and **AWAITS APPROVAL**"*. 버전 이력의 최신 행은 **1.4 "Awaiting approval"** 이고, **v1.5 행 자체가 없습니다.** 파일명은 v1.5, 표지 버전 필드는 v1.5, 상태 문구는 v1.3 — **세 값이 어긋납니다.** Gate N1~N3를 승인 기록과 함께 엄격히 닫아온 프로젝트에서, **실제 배포되는 경로가 미승인 개정판에 놓여 있는 것**은 짚어야 합니다 (서류 지연일 가능성이 큽니다). |
| **D-7** | **매니페스트가 `exists: true`로 선언한 11개 중 4개가 실제로 없습니다** | 검증 스크립트 실행 결과: 7개는 **sha256까지 일치**(진본 확인), 누락 4개는 `PRAP_UI_Component_List_v1.0.xlsx`, `PRAP_SourceData_Dummy_v1.18.xlsx`, `PRAP_SourceData_Dummy_10x10_v1.10.xlsx`, `PRAP_AI_Agent_Guide_v1.0.xlsx`. 가이드가 *"파일명 정렬이 아니라 이 매니페스트로 문서를 찾으라"* 고 지시하므로, 매니페스트가 없는 파일을 있다고 말하는 것은 **지시를 따르는 사람을 오도합니다.** |
| **D-8** | 코드가 참조하는 스펙 버전이 실물과 다릅니다 | 코드 7개 파일 전부가 `PRAP_NewApp_Specification_v1.3.xlsx`를 참조. 전달된 것은 **v1.5**. |
| **D-9** | NewApp 계획서 표지의 웹앱 정보가 낡았습니다 | *"Does NOT govern: app/PRAP.html (application **v1.24**), which remains under PRAP_Development_Plan_**v2.26**.xlsx"* → 실제는 앱 **v1.50**, 계획서 **v2.54**. |

### 4.3 문서에 대한 총평 (상향)

1판에서 "품질이 상당히 높다"고 썼는데, **NewApp 스펙과 계획서를 보고 평가를 올립니다.** 특히 인상적인 대목:

- **`07_Sharing`의 "What this deliberately is not"** — 무엇을 만들지 않을지와 그 이유를 적었습니다. *"레코드 단위 잠금은 두 사람의 편집을 병합한다는 뜻이고, 저장 형식이 표현할 수 없으며, 다른 제품이다(N-20)."*
- **`08_Identity`의 자기 제한** — *"이름 입력란이 로그인처럼 보이면 **반드시** 로그인으로 읽힐 것이고, 누군가 그것이 누가 무엇을 했는지 증명한다고 믿는 순간 오도한 것이 된다. 그 한계는 오도할 수 있는 지점에 놓여야 한다."* 요구사항 NR-USR-08로 못박았습니다. **자기 기능의 한계를 요구사항으로 만든 설계는 드뭅니다.**
- **R-N14** — *"공유 폴더의 캐싱이 잠금이나 정전 확인을 무력화해 두 세션이 모두 자기가 보유한다고 믿는 경우. 편의가 아니라 **보증 자체를 깨뜨리는 유일한 실패**."* 3중 방어를 적었습니다.

---

## 5. 요청사항 a) b) — 서버 전환 설계

전제: **중앙 서버 + 데이터베이스 재구축.** 1판의 4부가 대체로 유지되며, 근거가 강화되고 일부가 조정됩니다.

### 5.1 왜 구조 변경인가 — 근거 교체

1판은 *"Out of scope로 확정되어 있다"* 를 근거로 들었습니다. **더 정확한 근거로 교체합니다.**

**① 설계자가 명시적으로 거부했고, 이유를 남겼습니다 (N-20)**

> *"Row-level or section-level locking — Two people editing different parts of one plan at the same time is **a different product**, and it needs **a merge model the storage format does not have**. The claim covers the whole workspace (N-20)."*
>
> *"Merging two people's changes — Out of scope, and it would **change the file format.**"*

**② 그리고 이렇게 덧붙였습니다**

> *"The requirement you gave - block other sessions from updating while somebody is editing - **is met in full** by the whole-workspace claim. Everything above that line would be **building a collaborative editor, which is a different tool.**"*

즉 **2026-08-13에 주신 지시("한 사람이 편집 중이면 다른 세션은 업데이트 금지")는 현재 구조로 이미 충족**되어 있고, 이번에 주신 요구("여러 명 동시 편집 + 레코드 단위 잠금")는 **그 선을 넘는 새 요구**입니다. 요구가 바뀐 것이지 구현이 부실한 것이 아닙니다.

**③ 관리자 권한은 현 구조에서 물리적으로 불가능합니다** (1판 유지, 스펙이 뒷받침)

스펙 `08_Identity`가 직접 말합니다 — *"Declared, not authenticated. … **It is not a login, it controls no access**, and nothing in it should ever be relied on as evidence of who did what (NR-USR-08)."*

거기에 서버가 **사용자 자신의 PC에서 사용자 권한으로** 돌고, 데이터는 공유 폴더의 평문 JSON입니다. 화면에서 버튼을 숨겨도 메모장으로 열어 고칠 수 있습니다.

**④ 그러나 버릴 것은 거의 없고, 이제 그것이 실증되었습니다**

| 자산 | 재사용 | 2판에서 추가된 근거 |
|---|---|---|
| **계산 엔진** | ♻️ 그대로 | **3,304 person-month 실측 일치 (오차 0.00e+00).** 서버 이관 시 회귀 기준선으로 사용 가능 |
| **화면 전체** | ♻️ 거의 그대로 | `test_app` 통과. 탭·차트 모두 정상 렌더링 확인 |
| **데이터 모델** | ♻️ DB 테이블로 번역 | `prap_contract.json` 입수 — **기계 판독 가능한 스키마 계약**이 있어 DB 스키마 자동 생성이 현실적 |
| **검증 규칙 36개** | ♻️ 그대로 | `prap_io.py` 입수 — **파이썬 구현이 이미 존재.** 서버측 재검증(1판 ⑤항)의 **상당 부분이 이미 끝나 있습니다** |
| 잠금 판단 로직 | 🔄 DB 잠금 테이블로 | 설계 사상(30초/30분, 실명 안내) 계승. `claim.py`는 80개 테스트 통과 |
| 저장 절차 | 🔄 DB 트랜잭션으로 | — |
| 로컬 HTTP 서버 | 🔄 실제 서버로 승격 | API 28개가 출발점 |
| 파일 선택 창 | 🗑️ 불필요 | — |

**`prap_io.py`(1,411행)의 입수는 일정에 직접 영향을 줍니다.** 1판 로드맵의 2단계에 있던 "계산·검증 로직을 파이썬으로 옮기기"가 **이미 존재하는 것을 붙이는 일**로 바뀝니다.

### 5.2 목표 구조

```
[ 사용자 A 브라우저 ] ┐
[ 사용자 B 브라우저 ] ├── HTTPS ──▶ [ 사내 서버 1대 ]
[ 사용자 C 브라우저 ] ┘               ├ 웹 서버 (IIS 또는 nginx)
  └ 화면 + 계산 엔진                   ├ 애플리케이션 (Python / FastAPI)
    (index.html 재사용)                │   ├ 인증·권한 확인
                                       │   ├ 레코드 잠금 관리     ← 요청 b)
                                       │   ├ 검증 재실행 (prap_io.py 재사용)
                                       │   └ 변경 이력 기록
                                       ├ 데이터베이스 (PostgreSQL)
                                       │   ├ 업무 데이터 (10개 시트 → 테이블)
                                       │   ├ 잠금 / 사용자·권한 / 변경이력
                                       │   └ 가정값 버전
                                       └ 사내 AD 연동 (로그인)
```

**덤으로 해결되는 것**: 업데이트가 서버 1곳만 / 각 PC 파이썬 설치 불필요(결함 F) / 작업 유실 구조적 불가(결함 B) / 이력 깨짐 불가(결함 G) / 모두가 같은 숫자를 봄.

### 5.3 구성요소 (1판 유지, 변경점만)

- **DB: PostgreSQL 권장** — 행 단위 잠금, 트랜잭션 신뢰도, 무료. 사내에 SQL Server가 이미 운영 중이고 DBA가 있다면 SQL Server로 바꿔도 설계는 그대로 성립.
- **앱 서버: Python + FastAPI 권장** — **근거 강화**: `prap_io.py`가 파이썬이므로 검증·계산 재사용이 즉시 가능.
- **서버: 사내 VM 1대, Windows Server 2019/2022, 4 vCPU / 16GB / 100GB SSD**, 일 1회 전체 + 시간별 증분 백업.
- **모든 업무 테이블에 `row_version`** — 결함 B가 다시 생기지 않게 하는 이중 안전장치.
- **인증: 사내 AD 연동 권장** (1판 유지). 이유는 보안이 아니라 **운영 부담** — 자체 계정은 비밀번호 초기화와 퇴사자 정리를 담당자가 영구히 처리해야 합니다.

### 5.4 IT팀 확인 질문 — 8개 → 7개 (C-5 반영)

1. 사내 웹 애플리케이션에서 **Windows 통합 인증(Kerberos/NTLM) 또는 LDAP 조회**를 쓸 수 있습니까? 승인 절차는?
2. 그 용도의 **서비스 계정**을 발급받을 수 있습니까?
3. 권한 구분용 **AD 보안 그룹**(`PRAP-Admins`, `PRAP-Editors`)을 신규 생성할 수 있습니까? 구성원 변경은 누가?
4. 사내 **가상 서버(VM) 1대**를 받을 수 있습니까? 사양·OS·백업 정책은?
5. 사내 **HTTPS 인증서**를 발급받을 수 있습니까? (`https://prap.사내도메인`)
6. **PostgreSQL 설치**에 제약이 있습니까? 이미 표준 DB가 지정되어 있습니까?
7. 사내 웹 애플리케이션 도입 시 거쳐야 하는 **IT 변경관리·보안 검토** 절차와 소요 기간은?
   - ※ 1판의 8번(GxP/CSV 검증)은 **철회**합니다 — A-N11 "이 도구에 밸리데이션 의무 없음"이 Q-N09에서 이미 확인되었습니다. 단, *중앙 서버가 되면* 사내 IT 변경관리 대상이 될 수 있으므로 7번에 포함했습니다.
8. **(추가)** 사내 표준 PC에 **Python 3.9+ 와 tkinter**가 설치되어 있습니까? (전환 기간 중 파이썬 방식을 여러 명이 쓸 수 있는지 판단용 — 결함 F)

### 5.5 요청 b) 레코드 단위 잠금 설계 — 1판 유지

잠금 단위 2종(**프로젝트 잠금** = 프로젝트 행 + 마일스톤·기간·월별추정 + **그 프로젝트의 모든 배정**, **배정 잠금** = 배정 1행 + 가중치 창 + 월별추정), 부모 프로젝트에 **의도 표시(intent)**, `UNIQUE (scope, record_id, mode)` 제약으로 DB가 승자를 판정하는 **다중 단위 잠금(multi-granularity locking)** 설계입니다.

**2판에서 근거가 강화된 부분**: 프로젝트 잠금이 하위 배정을 포함해야 하는 이유를 `prap_io.py`로 재확인했습니다. 기간 경계가 바뀌면 각 월의 `period_weight`가 바뀌고, `monthly_load_fte = period_weight × role_factor × person_weight × month_coverage`이므로 **그 프로젝트 모든 배정의 월별 FTE가 재계산**됩니다. 실측에서 V-34가 71개 project-month에 대해 "표준 대비 차이"를 보고한 것이 이 연쇄의 규모를 보여줍니다.

**동작 표** (주신 예시 2개 포함)

| # | 요청 | 현재 잠금 | 결과 | 메시지 |
|---|---|---|---|---|
| 1 | A가 `PRJ-001` 기간 수정 | 없음 | ✅ 허용 | "PRJ-001을 편집 중입니다" |
| 2 | **B가 `PRJ-001` 기간/월 FTE 수정** | A가 PRJ-001 | ❌ **차단** | **"김OO(DM팀)이 PRJ-001을 편집 중입니다. 11:31 시작, 활동 중."** ← 요청 예시 1 |
| 3 | B가 `ASG-007` 수정 | A가 PRJ-001 | ❌ 차단 | "김OO이 PRJ-001 전체를 편집 중" |
| 4 | B가 `ASG-007` 수정 | 없음 | ✅ 허용 | PRJ-001에 의도 표시 |
| 5 | **C가 같은 `ASG-007` 수정** | B가 ASG-007 | ❌ **차단** | **"이OO(DM팀)이 이 배정을 편집 중입니다"** ← 요청 예시 2 |
| 6 | C가 **다른** `ASG-009` 수정 | B가 ASG-007 | ✅ 허용 | — **진짜 동시 편집 지점** |
| 7 | A가 `PRJ-001` 전체 수정 | B가 ASG-007 | ❌ 차단 | "이OO이 이 프로젝트의 배정을 편집 중" |
| 8 | D가 `PRJ-002` 수정 | 위 전부 | ✅ 허용 | — 완전 독립 |

**잠금 규칙은 기존 설계 사상을 그대로 계승합니다** — 값이 실제로 바뀔 때 획득(NR-STO-10), 30초 생존신호 / 30분 만료 분리(NR-STO-14), 자기 세션 즉시 복구(NR-STO-19), 실명+부서+시작시각+해제예정 메시지(NR-STO-12). **이 사상은 80개 테스트로 검증된 것이므로 새로 발명할 것이 없습니다.**

**결함 D 재발 방지 3중 장치**: ① 다른 레코드로 이동 시 이전 잠금 필수 해제 ② `expires_at` 기준 자동 만료 ③ **관리자용 "현재 잠금 목록" 화면 + 강제 해제** (현재 전혀 없는 수단).

**놓치기 쉬운 문제 — "사람" 축 충돌** (1판 유지): 한 인원의 서로 다른 배정을 두 사람이 각각 정당하게 수정하면 그 인원의 월 합계가 과다배정에 접근하는데 **둘 다 자기 화면에서는 볼 수 없습니다.** 잠금으로 풀 문제가 아니라 알려주기로 풀어야 합니다 — 저장 시 해당 인원 전체 합계 재계산 후 경고(막지 않음), 같은 인원의 다른 배정 편집 중이면 정보성 안내, 과다배정 목록 상시 노출.

### 5.6 요청 a) 관리자 권한 분리 — 1판 유지

권한 3단계(**관리자** 전부 + General assumptions 수정 + 사용자·권한 관리 + 잠금 강제해제 / **편집자** 업무 데이터 편집, 가정값은 읽기만 / **조회자** 읽기·내보내기만).

**General assumptions = 4개 테이블** (코드에서 확인): `PeriodFTEStandard`(88행), `RoleFactor`(430행), `Lists`, `Config`. 실측에서 이 탭이 **184행**을 렌더링하는 것을 확인했습니다.

> **비유**: 이 4개는 **환율표**입니다. 개별 프로젝트 데이터가 "금액"이라면 이것은 환산 환율입니다. **한 칸 바꾸면 회사 모든 장부의 숫자가 동시에 바뀝니다.** 관리자만 만지게 하려는 판단은 정확합니다.

**가정값은 잠금이 아니라 버전으로**: 수정 시 새 버전 저장(덮어쓰지 않음) → 적용 전 **영향 범위 표시**("프로젝트 62개, 인원 20명의 FTE가 바뀝니다. 새로 과다배정 3명: …") → 편집 중 사용자에게 알림 → 과거 버전 보존으로 "지난달 보고서는 어느 기준이었나"에 답변 가능.

**권한 확인은 반드시 서버에서** — 화면 버튼 숨김은 친절함이지 보안이 아닙니다. 4개 테이블을 수정하는 모든 API가 권한을 확인하고, 거부 기록을 이력에 남기고, 일반 사용자에게 DB 직접 접근을 주지 않습니다.

### 5.7 로드맵 — 개정

`prap_io.py`와 `prap_contract.json` 확보로 2단계가 단축되고, `src/` 부재로 **0단계가 더 중요해졌습니다.**

| 단계 | 내용 | 1판 | **2판** | 변경 이유 |
|---|---|---|---|---|
| **0** | **`src/` 확보** + 매니페스트 누락 4건 + IT 질문 8개 답변 + 서버·DB 승인 | 2~3주 | **2~3주** | `src/` 확보가 **모든 것의 선행 조건**으로 격상 |
| **1** | 응급 수정 (결함 B·C·D = NR-STO-16/07/15 배선) — **`src/`에서** | 3~5일 | **3~5일** | 대상이 `src/`로 정정. 저장 계층 함수는 이미 있고 테스트 통과 |
| **2** | 서버 골격 + DB + 데이터 이관 + 검증 이식 | 3~4주 | **2~3주** | `prap_io.py`(검증 36개 파이썬 구현)와 `prap_contract.json`(기계판독 스키마) 확보로 단축 |
| **3** | 인증·권한 — **요청 a) 완료** | 2~3주 | 2~3주 | 변경 없음 |
| **4** | 레코드 잠금 — **요청 b) 완료** | 2~3주 | 2~3주 | 변경 없음 |
| **5** | 검증·이관 (다중 사용자 / 규모 100·1,000·60개월 / 교육) | 2~3주 | 2~3주 | **회귀 기준선 확보**(3,304 person-month)로 위험 감소 |
| | **합계** | 3~4개월 | **약 3개월** | |

**1단계를 먼저 하시라는 권고는 유지되며, 근거가 강해졌습니다.** 저장 계층 함수(`write_journal`, `release_claim`, `WS.stat`)가 **모두 이미 존재하고 테스트를 통과**하므로, 1단계는 "만들기"가 아니라 **"연결하기"** 입니다. 3~4주가 아니라 3~5일인 이유입니다. 단, **`src/` 없이는 착수할 수 없습니다.**

### 5.8 위험 — 개정

| ID | 위험 | 가능성 | 영향 | 2판 변경 |
|---|---|---|---|---|
| **N-00** | **`src/` 미확보로 아무것도 고칠 수 없음** | — | **차단** | **신규, 최우선.** 현재 발생 중인 상태 |
| N-01 | IT팀 승인 지연 | 높음 | 높음 | 유지. 여전히 가장 큰 **일정** 위험 |
| N-02 | 규모 미검증 (100/1,000/60개월) | 중 | 높음 | **완화** — 50×50 / 3,304 person-month 정상 확인. 다만 목표 규모의 일부 |
| N-03 | 계산 엔진 이관 시 숫자가 달라짐 | 중 | 매우 높음 | **크게 완화** — 회귀 기준선(3,304 person-month, 오차 0.00e+00)이 손에 있고 `prap_io.py`가 정답 역할을 합니다 |
| ~~N-04~~ | ~~GxP/CSV 검증 대상~~ | — | — | **철회** (A-N11 / Q-N09) |
| N-05 | 레코드 잠금이 실사용에서 답답함 | 중 | 중 | 유지 |
| N-06 | 파일 방식 사용자의 저항 | 중 | 낮음 | 유지 — 엑셀 가져오기·내보내기를 끝까지 유지 |
| **N-07** | **미승인 스펙 개정판 위에서 개발** | 중 | 중 | **신규** (D-6). 스펙 v1.3~v1.5가 Awaiting approval. 서류 정리 필요 |

---

## 6. 즉시 조치 권고 — 개정

### 🔴 이번 주

| # | 조치 | 비고 |
|---|---|---|
| 1 | **`src/` 폴더 전체를 확보하십시오** | **1순위.** 없으면 결함 B·C·D를 고칠 수 없고, 빌드·아키텍처 검사도 불가 (결함 A) |
| 2 | **공유 폴더에서 "같은 계획 파일을 여러 명이 편집"하는 사용 중단** | 결함 B — **NR-STO-16이 막으려 한 유실이 경고 없이** 발생 |
| 3 | 매니페스트 누락 4건 확보 | 예제 워크북 2종은 **테스트 20개를 막고 있는 원인** (D-7) |
| 4 | IT팀에 질문 8개 전달 | 답변 대기가 일정 병목 (N-01) |

### 🟠 1단계 응급 수정 (3~5일, `src/` 확보 후)

| # | 수정 | 대상 (`src/` 기준) | 요구사항 | 효과 |
|---|---|---|---|---|
| 5 | 저장 직전 `ws/stat` 확인 + STALE 상태 도입 (10초 폴링) | `src/shell/python/bridge.js` | **NR-STO-16**, S-N01 | **결함 B 해소 — 작업 유실 방지** |
| 6 | `journal/write` 배선 (편집 발생 시 기록) | `src/shell/python/bridge.js` | **NR-STO-07** | 복구 기능이 실제 작동 |
| 7 | `claim/release` 배선 (저장&닫기 / 변경취소 시) | `src/shell/python/bridge.js` | **NR-STO-15** | 잠금 즉시 반납 |
| 8 | `stop_heartbeat()`이 실제로 스레드를 멈추게 + 계획 이동 시 이전 잠금 해제 | `src/shell/python/server.py` | NR-STO-15 | **결함 D 해소 — 30분 잠김 방지** |
| 9 | `SCHEMA_EXPECTED` 5 → 12 | `src/storage/python/workspace.py` | — | D-4 시한폭탄 제거 |
| 10 | 변경 이력을 사용자별 파일로 분리 | `src/shell/python/server.py` | — | 결함 G 완화 (SMB 이어쓰기) |
| 11 | **위 수정에 대한 배선 테스트 추가** | `tools/test_python_app.py` | — | **세 결함이 테스트되지 않았던 것이 원인.** 배선 테스트 없이 고치면 또 빠집니다 |
| 12 | 공유 계획 위치 운영 규칙 신설 (예: `data\shared\workspaces\`) | 문서 + `paths.py` | — | 결함 E 해소 |

### 🟡 문서 정리

| # | 조치 |
|---|---|
| 13 | **스펙 v1.3~v1.5 승인 처리** — 파이썬 셸이 미승인 개정판에 올라가 있습니다 (D-6, N-07) |
| 14 | 스펙 v1.5의 표지 상태 문구와 버전 이력을 실제 버전에 맞추기 (v1.5 행 신설) |
| 15 | `PRAP_Manifest.json` 재생성 — 없는 파일을 `exists: true`로 선언하지 않도록 (D-7) |
| 16 | 코드 주석의 스펙 참조를 v1.3 → 실제 버전으로 (D-8) |
| 17 | 버전 번호 통일 — `version.txt`(1.20) / `APP_VERSION`(1.50) 중 제품 버전 확정 (D-5) |
| 18 | NewApp 계획서 표지의 웹앱 정보 갱신 (v1.24/v2.26 → v1.50/v2.54) (D-9) |
| 19 | 규모 재기준(100/1,000/60개월) 실측 기록 추가 (D-3) |

---

## 부록. 2판의 실행 증거

### A. 계산 엔진 일치성 — 배포된 PM_APP, 실제 브라우저

```
tools/test_python_app.py  (배포본을 dist/PM_APP_py 로, 50x50 시나리오 투입)
  ok  THERE IS NO FILE INPUT ON THE PAGE (R-N21)   0 found
  ok  the data is all there   50 projects, 50 people, 292 assignments
  ok  EVERY FIGURE EQUALS THE PYTHON REFERENCE IMPLEMENTATION
      3304 person-months compared, worst difference 0.00e+00
  ok  re-opening it gives back the identical figures      worst difference 0.00e+00
  ok  the exported workbook gives the same figures again  worst difference 0.00e+00
  ok  every row of it is its demand times its share       1,580 rows checked
  ok  nothing is written outside the application folder
0 failed
```

### B. 저장 계층 · 수명주기

```
tools/test_storage_py.py  →  80 passed, 0 failed
  ok  eight processes race, exactly one wins
  ok  releasing frees it
  ok  rule 4: a read-only folder means ASK, at launch
tools/test_shutdown.py    →  FAILURES: none
```

### C. 검증 도구 · 앱-참조 판정 일치

```
tools/prap_io.py validate ...Scenarios_50x50_v1.0.xlsx
  →  12 finding(s): 8 warning, 4 information   (오류 0건)
tools/test_app.py 에서 앱이 보고한 findings   →  8건 (warning 이상)
  ⇒ 화면과 독립 검증기가 판정에서도 일치
```

### D. 미배선 3건 — 새 zip 재검증, 동적 호출 배제

```
index.html:  "journal/write" 0회   "ws/stat" 0회   "claim/release" 0회
             "journal/read"  1회   "claim/take" 1회  "claim/holds" 1회
call( 의 형태: call("리터럴") 과 정의부 call(op, body) 뿐  → 동적 호출 없음
"stale" 검색: 전부 S.stale (UI 탭 재렌더링) → NR-STO-16 과 무관
tools/ 전체에서 "journal/write" 검사 테스트: 0건
```

### E. 잠금 미해제 재현

```
잠금 A 획득: True   현재 파일 = planA.prap
잠금 B 획득: True   현재 파일 = planB.prap
A의 잠금 파일이 아직 존재?  → True
프로그램 종료 후 → A 잠김: True | B 잠김: False
```

### F. 빌드 불가 · 매니페스트 검증

```
python3 tools/build_python_app.py
  →  FileNotFoundError: .../src/shell/python/chrome.css

매니페스트 선언 11개 항목:
  [있음] 7개  (전부 sha256 일치 — 진본 확인)
  [없음] 4개  UI_Component_List_v1.0 / SourceData_Dummy_v1.18
              / SourceData_Dummy_10x10_v1.10 / AI_Agent_Guide_v1.0.xlsx
```

### G. 코드 동일성

```
새 zip 과 1판 zip:  PM_APP.py / version.txt / app/index.html
                    server.py / claim.py / workspace.py  → 전부 동일
⇒ 1판의 코드 지적은 모두 현재 배포본에 그대로 적용됩니다
```

---

*2판은 도구 46개 중 실행 가능한 전부와 테스트 37개를 실제로 돌려 작성했습니다. 완전 통과 14개, 픽스처 교체로 인한 부분 실패 3개(제품 결함 아님), 누락 파일로 미실행 20개입니다. 예제 워크북 2종이 없어 50×50 시나리오 워크북으로 대체했고, 그 대체가 정당한 경우와 정당하지 않은 경우를 본문에 구분해 밝혔습니다.*
