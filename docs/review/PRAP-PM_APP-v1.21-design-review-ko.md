# PRAP / PM_APP v1.21 설계 검토 — 4판

**개정 4판.** `PM_APP_python_v1.21.zip` + `PRAP_relevant_docs.zip`을 받아 재검토했습니다. 이전 3판(v1.20 기준)의 결론 중 **무엇이 해소되고 무엇이 그대로인지**를 실측으로 가렸습니다.

| 항목 | 내용 |
|---|---|
| 검토 대상 | `PM_APP` **1.21** (계산 엔진 **v1.51**) |
| 함께 받은 문서 | Development Plan **v2.60** · Programming Specification **v1.31** · AI Agent Guide · `PRAP.html` · Template **v1.6** · Dummy_10x10 **v1.9** |
| 검토 방법 | v1.20과 파일 단위 대조 + 실구동 + **유실 시나리오 재현** + 엔진 일치성 + 신기능 동작 확인 + 동봉 템플릿 검증 |
| 검토 일자 | 2026-09-13 |

> **이후 진행 상황 (이 검토서가 지적한 것에 대한 조치).** v1.21의 `src/`와 `tools/`를 받아 **세 공백(`ws/stat` · `journal/write` · `claim/release`)을 소스에 영구 반영**했고, 그 과정에서 요구사항 **NR-STO-15가 절반만 지켜져 있던 것**도 찾아 막았습니다. 결함 **I**(구버전 템플릿)는 Template **v1.16** 수령으로 해소되었습니다. 조치 내역과 검증 결과는 `fixes/README-v1.21-소스적용.md` 에 있습니다. 아래 2장·5장은 **조치 이전(받은 v1.21 그대로)의 상태**를 기록한 것으로 그대로 둡니다.

---

## 0. 한 장 요약

**결론 세 줄**

1. **v1.21은 좋은 개선이고, 제대로 만들어졌습니다.** 새 기능(배정 없는 프로젝트의 필요량 표시)이 실제로 작동하고, **계산 엔진은 기존 참조 구현과 1,227 person-month 전부 일치**하며, 배포본이 **자체 종단간 테스트를 0 failed로 통과**합니다.
2. **그러나 3판에서 지적한 동시성 결함 3건은 하나도 수정되지 않았습니다.** 파이썬 파일 9개가 **v1.20과 바이트 단위로 동일**하고, **공유 폴더 유실 시나리오를 v1.21에서 다시 재현했습니다** — A의 작업 9건이 경고 없이 사라졌습니다.
3. **새 문제 하나: 함께 온 템플릿이 7세대 뒤처진 구버전입니다.** `Template_v1.6`은 schema 5인데 현재는 12이고, 현재 검증기로 검사하면 **오류 2건**이 나며 그중 하나는 **애플리케이션이 행을 거부**합니다.

**실측 수치**

| | |
|---|---|
| v1.20 대비 변경된 파일 | **화면 1개뿐** (파이썬 9개 전부 동일) |
| 새 기능 동작 | ✅ `◦ 13.34 unstaffed` 표시 확인 |
| 엔진 일치성 | ✅ 1,227 person-month, 오차 0.00e+00 |
| v1.21 자체 테스트 | ✅ **0 failed** |
| `ws/stat` · `journal/write` · `claim/release` 호출 | **0회 · 0회 · 0회** (변화 없음) |
| 유실 재현 | ❌ **A의 9건 사라짐** (v1.20과 동일) |
| 동봉 템플릿 검증 | ❌ **오류 2건** (`[must]` 1건 포함) |

---

## 1. v1.21이 실제로 바꾼 것

### 1.1 무엇이 바뀌었나 — 파일 단위 대조

```
PM_APP.py                  동일
pmapp/shell/server.py      동일
pmapp/shell/paths.py       동일
pmapp/shell/files.py       동일
pmapp/shell/launch.py      동일
pmapp/storage/workspace.py 동일
pmapp/storage/claim.py     동일
pmapp/storage/timefmt.py   동일
version.txt                변경  (1.20 → 1.21)
READ ME FIRST.txt          변경  (변경 내역)
app/index.html             변경  (683,548 → 696,460 바이트)
```

**파이썬 껍데기는 한 줄도 바뀌지 않았습니다.** 바뀐 것은 화면 하나이고, 계산 엔진이 v1.50 → **v1.51**로 올라갔습니다.

### 1.2 새 기능 — 배정 없는 프로젝트가 필요량을 말합니다

변경 내역의 설명을 옮기면 이렇습니다.

> *"프로젝트를 추가하고 기간을 정해도, 첫 사람을 배정하기 전까지 그 프로젝트는 **목록에는 있으나 비어 있습니다.** 모든 월이 빈칸입니다. **빈칸의 행은 비용이 들지 않는 프로젝트처럼 보이지, 아직 아무도 배정하지 않은 프로젝트처럼 보이지 않습니다** — 누구를 붙일지 결정할 때 봐야 하는 것과 정반대입니다."*

> **비유**: 식당 예약표에 "3번 테이블 — 6인 예약"이라고 적혀야 하는데 **빈칸**으로 남아 있었습니다. 빈칸은 "예약 없음"처럼 보이지만 실제로는 "예약은 있고 담당 서버만 안 정했음"이었습니다. 이제 **"6인 필요"** 라고 적어줍니다.

**실제로 작동하는지 확인했습니다.** 더미 데이터에서 한 프로젝트의 배정을 모두 지워보니, 변경 내역이 약속한 그대로 나타났습니다.

```
◦ 13.34 unstaffed
```

고리 표시(`◦`)와 함께 **별도 줄에** 합계가 붙습니다.

**그리고 가장 중요한 주장을 검증했습니다** — *"어떤 합계에도 더해지지 않아 프로젝트 표와 인원 표가 전과 똑같이 일치한다"*.

```
tools/test_app.py  (v1.51 엔진 × Dummy v1.18)
  ok   calculation matches the reference on all 1227 person-months
  ok   V-34 agrees with the reference on all 72 project-month(s) off their standard
  ok   export re-imports with no findings above information
FAILURES: none
```

**기존 참조 구현(`prap_io` v1.0)과 1,227건 전부 일치**했습니다. 즉 *"이미 가진 어떤 수치도 움직이지 않는다"* 는 주장이 사실입니다. 표시만 바뀌고 계산은 건드리지 않았습니다. **버전을 올리면서 숫자가 조용히 달라지는 것이 이 프로젝트에서 가장 위험한 사고인데, 그것이 일어나지 않았음을 확인했습니다.**

### 1.3 새 검증 규칙 V-36 — 문서와 코드가 일치합니다

스펙 v1.31에 이렇게 정의되어 있습니다.

> **V-36** | Information | *"기간은 있으나 배정 행이 전혀 없는 프로젝트. 계산에서 발생, 프로젝트당 하나. **INCOMPLETE로 분류되어 거부하지도 묻지도 않는다.**"*

변경 내역의 *"그것은 안내일 뿐 그 이상이 아니다. 편집을 거부하지 않고, 저장을 막지 않고, 질문하지 않는다"* 와 정확히 같습니다. **스펙과 코드가 어긋나지 않았습니다.**

### 1.4 부수적으로 좋아진 것 — 검증 심각도에 등급이 생겼습니다

검증기 출력에 이전에 없던 표기가 보입니다.

```
error       [must]        V-19  ...
error       [conditional] V-23  ...
1 of them are [must]: the application refuses those rows until they are corrected.
The rest it reports, and asks about at Save.
```

**"오류"를 한 덩어리로 묶지 않고 "거부하는 것"과 "보고하고 저장 때 묻는 것"으로 갈랐습니다.** 사용자가 무엇을 지금 고쳐야 하는지 알 수 있게 되었으므로 실질적인 개선입니다.

---

## 2. 그대로 남은 것 — 3판 지적의 현재 상태

### 2.1 결함 B·C·D는 손대지 않았습니다

파이썬 파일이 전부 동일하므로 예상되는 결과였고, 화면에서도 확인했습니다.

| 호출 | v1.20 | **v1.21** |
|---|---|---|
| `ws/stat` (정전 감지) | 0회 | **0회** |
| `journal/write` (복구 기록) | 0회 | **0회** |
| `journal/clear` | 0회 | **0회** |
| `claim/release` (잠금 반납) | 0회 | **0회** |
| `superseded`·`lastSaved`·`baseSaved` 언급 | 0 | **0** |

그리고 **추측이 아니라 재현했습니다.** 3판에서 유실을 증명했던 그 시나리오(공유 폴더에 PM_APP 두 인스턴스)를 v1.21에 돌렸습니다.

```
09:00  A 가 계획 생성 후 저장 — 프로젝트 3건
09:05  B 가 열어 봄 — 3건 (잠금 없음)
09:30  A 가 저장 — 프로젝트 12건 (9건 추가)
09:35  A 정상 종료 → 잠금 해제됨: True
09:40  B 가 편집 시작 → 잠금 획득: True
09:41  B 가 저장 → 허용됨
══════════════════════════════════════════════════
파일에 남은 프로젝트: 3건   (A 가 저장한 것은 12건)
A 의 작업 9건: 사라짐  ❌
══════════════════════════════════════════════════
```

**v1.20과 완전히 같은 결과입니다.**

### 2.2 나머지 지적도 그대로입니다

```
결함 D  계획 이동 시 이전 잠금 → A 의 잠금 파일이 아직 존재: True
        종료 후 → A 잠김: True | B 잠김: False
결함 9  workspace.py SCHEMA_EXPECTED = 5   (화면 core = 12 → 불일치 여전)
결함 H  BLOCKING_OPS 존재: False           (대화상자가 전역 락 안에서 실행)
항목 13 shared_dir() 존재: False           (공유 계획 폴더 미구현)
```

### 2.3 왜 v1.21의 테스트는 통과하는가 — 이것이 핵심입니다

배포된 v1.21을 자체 종단간 테스트에 넣으면 **0 failed**로 통과합니다.

```
one writer at a time, on the live application
  ok   taking the claim writes a marker beside the plan
  ok   which names the person a blocked colleague should ask
  ok   and the page can see that it holds it
...
0 failed
```

**테스트 스위트가 세 공백을 검사하지 않기 때문에 통과합니다.** 잠금을 *잡는* 것은 검사하지만 *놓는* 것은 검사하지 않고, 정전 감지와 복구 기록은 검사 항목 자체가 없습니다.

> **비유**: 자동차 검사에서 **브레이크를 밟으면 멈추는지**는 보지만 **주차 브레이크를 풀면 풀리는지**는 보지 않습니다. 그래서 주차 브레이크가 안 풀리는 차가 매번 검사를 통과합니다. 검사표에 그 항목이 없기 때문입니다.

**이것이 3판에서 12번 항목(배선 테스트 추가)을 권고한 이유이고, v1.21이 나온 뒤에도 그 권고가 유효한 이유입니다.**

---

## 3. 새로 발견한 문제

### 🔴 새 결함 I. 함께 온 템플릿이 7세대 뒤처진 구버전입니다

```
PRAP_SourceData_Template_v1.6.xlsx      시트 11개   schema_version = 5
PRAP_SourceData_Dummy_10x10_v1.9.xlsx   시트 12개   schema_version = 11
현재 애플리케이션이 기대하는 값                      schema_version = 12
```

이전 업로드에 있던 것은 `Template_v1.16`(schema 12)였습니다. **이번에 온 것은 `v1.16`이 아니라 `v1.6`입니다** — 한 글자 차이지만 7세대 전 파일입니다.

**추측이 아니라 검사해봤습니다.**

```
python3 tools/prap_io.py validate PRAP_SourceData_Template_v1.6.xlsx

  error  [must]        V-19  PeriodFTEStandard  PRJ-001: no standard weight for
                             NewDrug CT / Phase 1 / any scope / Start-up.
  error  [conditional] V-23  RoleFactor         No role factor for ... Lead data
                             manager — 4 person-month(s) were calculated at
                             factor 1.00 instead.
  warning              V-09  Config             This file is schema version 5;
                             this build expects 12.

4 finding(s): 2 error, 1 warning, 1 information
1 of them are [must]: the application refuses those rows until they are corrected.
```

**두 가지가 나쁩니다.**

**① `[must]` 오류** — 애플리케이션이 해당 행을 **거부**합니다. 템플릿을 받아 작업을 시작하려는 사람이 첫 단계에서 막힙니다.

**② V-23이 더 위험합니다** — *"4 person-month가 factor 1.00으로 계산되었습니다."* AI Agent Guide가 이 규칙에 대해 직접 경고합니다 — *"빠진 factor는 V-23 오류다. 그렇지 않으면 계산이 조용히 1.00을 쓰게 된다."*

> **비유**: 환율표가 빠진 회계 장부를 받았는데, 프로그램이 멈추지 않고 **환율을 1:1로 가정해서** 계산을 계속합니다. 숫자는 나오고, 틀렸다는 표시는 경고 목록 안에 묻힙니다.

**조치는 간단합니다** — `Template_v1.16`(schema 12)으로 교체하면 됩니다. 이전 업로드에 있던 파일입니다.

### 🟠 새 결함 J. 파이썬 셸을 규정하는 문서가 다시 빠졌습니다

이번 `PRAP_relevant_docs.zip`에 들어온 것과 빠진 것입니다.

| 문서 | 이번 | 지배 대상 |
|---|---|---|
| Development Plan v2.60 | ✅ | **웹앱** (`PRAP.html`) |
| Programming Specification v1.31 | ✅ | 데이터·검증·계산 (양쪽 공용) |
| AI Agent Guide | ✅ | AI 에이전트 |
| **NewApp Specification** (v1.5) | ❌ **없음** | **파이썬 셸 — NR-STO-07/15/16 정의** |
| **NewApp Development Plan** (v1.13) | ❌ **없음** | **파이썬 셸 — 공유 모델** |
| `tools/` · `src/` · 매니페스트 · 계약 파일 | ❌ 없음 | 검증·빌드 |

**이것이 왜 중요한가.** 들어온 Development Plan v2.60은 여전히 이렇게 씁니다.

> **Out of scope** — *"Multi-user concurrent editing, or any server / database component"* (Confirmed Q-12)
> **가정 A-06** — *"한 번에 한 사람만 워크북을 관리한다"* (상태: **Standing**)

**이 패키지만 받은 사람은 "동시 편집은 설계 범위 밖"이라고 결론 내립니다 — 그리고 그 결론은 틀립니다.** 파이썬 데스크톱 앱을 지배하는 NewApp 문서에서는 대응 가정 **A-N03이 철회(WITHDRAWN)** 되었고, 공유 사용이 `07_Sharing`에 설계되어 있습니다.

**제가 1판에서 정확히 이 함정에 빠졌습니다.** 웹앱 계획서를 근거로 "동시 편집은 범위 밖"이라고 썼고, 2판에서 NewApp 문서를 받은 뒤 철회했습니다. **이번 패키지는 그 함정을 다시 놓아둔 상태입니다.**

### 🟡 새 결함 K. 계획서 표지가 앱 버전보다 26판 뒤처져 있습니다

```
계획서 v2.60 표지:  "Application v1.25"
실제 앱:             APP_VERSION = "1.51"  (PRAP.html · PM_APP/app/index.html 모두)
파이썬 셸:           1.21
```

계산 엔진이 **v1.25 → v1.51**로 26판 올라갔는데 표지가 갱신되지 않았습니다. 어느 문서가 어느 코드를 설명하는지 판단할 근거가 흐려집니다.

**다만 좋은 점도 확인했습니다** — `PRAP.html`과 `PM_APP/app/index.html`의 `APP_VERSION`이 **둘 다 1.51로 일치**합니다. 두 제품이 같은 엔진을 쓴다는 원칙(N-05)이 지켜지고 있습니다.

---

## 4. 두 가지 질문에 대한 답 — 갱신

### 4.1 "공유 폴더 운영 환경에서 쓸 수 있는가"

| 사용 방식 | 판정 | 3판 대비 |
|---|---|---|
| 1인이 자기 PC에서 사용 | ✅ **바로 가능** | 변화 없음 (오히려 v1.21로 개선) |
| 공유 폴더 배포 + 각자 자기 데이터 편집 | ⚠️ 조건부 가능 | 변화 없음 |
| **여러 명이 같은 계획 파일을 편집** | ❌ **중단 권고** | **변화 없음 — 유실 재현됨** |
| 동시 편집 + 관리자 권한 분리 | ❌ 현 구조로 불가능 | 변화 없음 |

**세 번째 줄이 바뀌지 않았다는 것이 이번 검토의 핵심입니다.** v1.21은 화면을 좋게 만들었지만, 공유 사용을 막고 있는 것은 화면이 아닙니다.

### 4.2 "다른 Claude에게 넘겨 운영할 수 있는가"

**3판보다 나빠졌습니다.** 이전 패키지에는 `tools/` 46개와 `src/` 45개가 있었는데 이번에는 없고, 파이썬 셸의 설계서도 없고, **템플릿은 구버전**입니다.

새 담당자가 이 패키지만 받으면:

| 하려는 일 | 가능한가 |
|---|---|
| 앱 실행 | ✅ 가능 |
| 데이터 검증 | ❌ `prap_io.py` 없음 |
| 코드 수정 | ❌ `src/` 없음 (배포본은 생성 산출물) |
| 파이썬 셸의 설계 의도 파악 | ❌ NewApp 문서 없음 |
| 템플릿으로 작업 시작 | ⚠️ **오류 2건** (구버전) |
| 동시 편집 범위 판단 | ❌ **틀린 결론에 이름** (결함 J) |

**전달 시 반드시 함께 보내야 할 것** (이전 업로드에 모두 있던 파일들입니다):

1. `PRAP_NewApp_Specification_v1.5.xlsx` · `PRAP_NewApp_Development_Plan_v1.13.xlsx`
2. `tools/` 폴더 (`prap_io.py` + 테스트)
3. `src/` 폴더 (45개 파일)
4. `PRAP_SourceData_Template_v1.16.xlsx` ← **v1.6이 아니라 v1.16**
5. `prap_contract.json` · `PRAP_Manifest.json`

### 4.3 서버 전환 설계 (요청 a·b) — 3판 유지

**결론과 설계는 바뀌지 않았습니다.** 요청하신 **레코드 단위 잠금은 여전히 구조 변경**이며, 스펙이 N-20에서 *"다른 제품이고, 저장 형식이 갖고 있지 않은 병합 모델을 필요로 한다"* 고 명시한 그대로입니다.

3판 5부의 설계(PostgreSQL + FastAPI + AD 연동, 다중 단위 잠금 8행 동작표, 권한 3단계, 가정값 버전 관리, 약 2.5~3개월 로드맵)를 그대로 유지합니다. **v1.21이 그 판단에 영향을 주는 요소는 없었습니다.**

다만 **재사용 자산의 근거가 한 겹 더 쌓였습니다** — v1.50에서 v1.51로 엔진이 올라가면서도 참조 구현과 1,227건 전부 일치했습니다. 즉 **이 계산 엔진은 버전이 올라가도 숫자가 흔들리지 않는다는 실적**이 생겼습니다. 서버로 옮길 때 가장 무서운 위험(N-03)이 그만큼 더 완화됩니다.

---

## 5. 즉시 조치 권고

### 🔴 이번 주

| # | 조치 | 근거 |
|---|---|---|
| 1 | **공유 폴더에서 "같은 계획 파일을 여러 명이 편집"하는 사용 중단** | v1.21에서 유실 **재현됨**. 경고 없이 사라집니다 |
| 2 | **동봉 템플릿을 `v1.16`(schema 12)으로 교체** | `v1.6`은 오류 2건, `[must]` 거부 1건, V-23 factor 1.00 (결함 I) |
| 3 | **1단계 응급 수정 패치 적용** | 이미 만들어 두었습니다 — `docs/review/fixes/` 의 패치. v1.21에 그대로 적용 가능 |
| 4 | IT팀 질문 8개 전달 | 3판 5.4절. 여전히 일정 병목 |

### 🟠 패치 적용에 대해

3판 검토 후 만든 패치가 **v1.21에도 그대로 적용됩니다** — 수정 대상인 파이썬 파일 9개가 v1.20과 바이트 단위로 동일하기 때문입니다. 다만 화면(`bridge.js`)은 v1.21에서 바뀌었으므로 **그 부분은 충돌 확인이 필요**합니다.

```bash
git checkout claude/project-resource-assignment-app-1vjdzh
git am docs/review/fixes/0001-wire-storage-operations-NR-STO-07-15-16.patch
# bridge.js 충돌 시: 3-way 병합 (v1.21 변경은 화면 표시, 패치는 저장 배선이라 겹치지 않음)
python3 tools/build_python_app.py && python3 tools/test_python_app.py
```

### 🟡 문서 정리

| # | 조치 |
|---|---|
| 5 | 배포 패키지에 **NewApp Specification·Development Plan 포함** (결함 J — 없으면 잘못된 결론에 이릅니다) |
| 6 | 계획서 v2.60 표지의 `Application v1.25` → **v1.51** (결함 K) |
| 7 | 계획서 v2.60의 A-06 / Out of scope 2항목에 **"데스크톱 앱은 NewApp 문서가 지배함"** 주석 추가 |
| 8 | `workspace.py` `SCHEMA_EXPECTED` 5 → 12 (결함 9 · 패치에 포함) |
| 9 | AI Agent Guide §5.1 공식에 `standard_fte`와 REQ-CAL-19 정규화 반영 (3판 D-10) |

---

## 부록. 4판의 실행 증거

### A. v1.20 대비 변경 범위
```
파이썬 9개 파일 → 전부 sha256 동일
화면 index.html → 683,548 → 696,460 바이트
엔진 APP_VERSION → 1.50 → 1.51
version.txt → 1.20 → 1.21
```

### B. 새 기능 동작
```
더미 데이터에서 PRJ-001 의 배정을 모두 제거 → 화면에 표시됨:
  ◦ 13.34 unstaffed
스크립트 오류: 없음
스펙 v1.31: V-36 | Information | "INCOMPLETE 로 분류되어 거부하지도 묻지도 않는다"
```

### C. 엔진 일치성 (버전 상승에도 숫자 불변)
```
tools/test_app.py  (v1.51 × Dummy v1.18)
  ok  calculation matches the reference on all 1227 person-months
  ok  V-34 agrees with the reference on all 72 project-month(s)
  ok  export re-imports with no findings above information
FAILURES: none
```

### D. 배포된 v1.21 자체 테스트
```
tools/test_python_app.py  →  0 failed
  (단, 이 스위트는 claim 반납·정전 감지·복구 기록을 검사하지 않습니다)
```

### E. 세 공백 — 변화 없음
```
ws/stat 0회 · journal/write 0회 · journal/clear 0회 · claim/release 0회
superseded·lastSaved·baseSaved 언급 0
workspace.py SCHEMA_EXPECTED = 5   BLOCKING_OPS 없음   shared_dir() 없음
```

### F. 유실 재현 (v1.21)
```
A 저장 12건 → B 저장 "허용됨" → 파일 최종 3건 → A 의 9건 사라짐
```

### G. 동봉 템플릿 검증
```
Template_v1.6      (schema 5)   → 2 error (V-19 [must], V-23), 1 warning (V-09)
Dummy_10x10_v1.9   (schema 11)  → 3 warning (V-09 포함), 오류 없음
```

---

*4판은 v1.21을 v1.20과 파일 단위로 대조하고, 실제로 구동해 신기능·엔진 일치성·자체 테스트를 확인하고, 3판의 유실 재현을 v1.21에 다시 돌려 작성했습니다. 3판의 설계 결론(서버 전환, 레코드 단위 잠금)은 유지되며, 새로 발견한 것은 동봉 템플릿의 구버전 문제와 파이썬 셸 설계서의 재누락입니다.*
