# v1.21에 1단계 응급 수정 적용 — 결과

검토서 3판의 1단계 응급 수정(항목 5~13)을 **v1.21에 적용**했습니다.

| 항목 | 내용 |
|---|---|
| 출발 | `PM_APP_python_v1.21.zip` (계산 엔진 v1.51) |
| 결과 | **`PM_APP_python_v1.21.1.zip`** — 파일 14개, 243 KB |
| 빌드 패치 | `PM_APP_v1.21_to_v1.21.1.patch` (배포본 대상, 668줄) |
| 소스 패치 | `0001-wire-storage-operations-NR-STO-07-15-16.patch` (`src/` 대상, 기존) |
| sha256 | `e819b732ab360065d013a0ba1d9b6688cb7431826c28f460da3ee517d938f84c` |

---

## 1. 적용이 깨끗했던 이유 — 먼저 확인한 것

패치를 들이대기 전에 **v1.21이 무엇을 바꿨는지** 정확히 가렸습니다.

```
v1.21 이 바꾼 src 조각 (6개)          패치가 건드리는 파일 (5개)
  core/00_meta.js                       shell/python/bridge.js
  core/05_model.js                      shell/python/server.py
  core/06_calculate.js                  shell/python/paths.py
  ui/09_charts.js                       shell/python/chrome.html
  ui/10_tables.js                       storage/python/workspace.py
  ui/style.css
                        ⇒ 교집합 없음
```

그리고 실제로 대조해 확인했습니다.

```
v1.21 빌드 안에 PRAP 브랜치 src/ 의 조각이 그대로 들어 있는가:
  bridge.js        포함 (바이트 동일)
  chrome.html      포함 (바이트 동일)
  importdiff.js    포함 (바이트 동일)
파이썬 모듈 9개   → v1.20 과 sha256 동일
```

**즉 v1.21의 변경은 전부 계산·표시 쪽이고, 패치가 손대는 저장·셸 쪽은 한 글자도 바뀌지 않았습니다.** 충돌이 날 여지가 없었습니다.

---

## 2. 어떻게 적용했는가 — 그리고 그 한계

**v1.21의 `src/`는 전달되지 않았습니다.** 배포본(`PM_APP/`)만 왔습니다. 그래서 두 갈래로 처리했습니다.

| | 무엇을 | 쓸 수 있는 시점 |
|---|---|---|
| **① 배포본 직접 패치** | v1.21 폴더에 수정을 넣어 `v1.21.1` 생성 | **지금 바로** — 압축만 풀면 실행 |
| ② 소스 패치 (기존) | `src/` 대상. v1.21의 `src/`를 받으면 적용 | v1.21 소스 확보 후 |

구체적으로는 이렇게 했습니다.

1. **파이썬 모듈 3개 교체** — `server.py`·`paths.py`·`workspace.py`. v1.20과 바이트 동일하므로 수정본을 그대로 넣었습니다.
2. **화면 안의 조각 2개 교체** — `index.html`에 박혀 있는 `bridge.js`(32,176자 → 40,642자)와 `chrome.html`(2,189자 → 2,270자)을 텍스트 치환했습니다. 빌드가 이 둘을 **그대로 끼워넣는** 방식이라 치환이 성립합니다.
3. **`version.txt` → `1.21.1`**

> ⚠️ **반드시 알아두실 것.** 이것은 **생성 산출물을 직접 고친 것**입니다. 완전하고 테스트도 통과하지만, **다음번에 소스에서 빌드하면 이 수정은 사라집니다.** 영구 반영을 위해서는 v1.21의 `src/`에 ① 소스 패치를 적용해야 합니다.

---

## 3. 검증 — 패키지에서 다시 풀어서

압축을 새 폴더에 풀고 그 상태로 돌렸습니다.

### 결함이 사라졌는가

```
tools/test_python_app.py  →  0 failed

the wiring - an operation nobody calls is a requirement nobody met
  ok   the page actually calls ws/stat
  ok   the page actually calls journal/write
  ok   the page actually calls journal/clear
  ok   the page actually calls claim/release
  ok   releasing gives the plan back at once, not at its expiry
  ok   and opening another plan hands the first one back (NR-STO-15)
  ok   'Leave without change' hands the plan back too (NR-STO-15)
  ok   a pending edit is written to the journal (NR-STO-07)
  ok   committing or discarding clears it
  ok   the application notices the plan moved on beneath it (NR-STO-16)
  ok   AND THE SAVE IS REFUSED rather than replacing their work
  ok   and the window says so, so nobody quotes the figures on screen

tools/test_storage_py.py  →  80 passed, 0 failed
tools/test_shutdown.py    →  FAILURES: none
```

### 유실 시나리오 — 4판에서 v1.21이 실패했던 그 재현

| | v1.21 | **v1.21.1** |
|---|---|---|
| 09:41 B 의 저장 | 허용됨 | **거부됨** |
| 메시지 | 없음 | *"shared.prap was saved by somebody else after you opened it. Nothing has been saved, so their work is intact."* |
| 파일에 남은 프로젝트 | 3건 | **12건** |
| A 의 작업 9건 | **사라짐** | **보존됨** |

### v1.21이 새로 만든 것이 망가지지 않았는가

화면을 수정했으므로 이것을 반드시 확인해야 했습니다.

```
ok   EVERY FIGURE EQUALS THE PYTHON REFERENCE IMPLEMENTATION
     1227 person-months compared, worst difference 0.00e+00
ok   'Overall' draws   4 chart(s), 124 row(s)
ok   'Source data (project)' · '(person)' · 'General assumptions'  모두 정상

v1.21 신기능 'unstaffed' 표기:  ◦ 13.34 unstaffed        ← 보존됨
V-36 규칙:                      코드에 7곳                ← 보존됨
엔진 APP_VERSION:               1.51                      ← 보존됨
패치가 추가한 File → Reload plan:  존재                    ← 추가됨
스크립트 오류:                   없음
```

**v1.21의 새 기능과 계산 결과가 전혀 흔들리지 않았습니다.**

---

## 4. 남은 일

| 항목 | 상태 |
|---|---|
| **v1.21의 `src/` 확보** | **가장 중요** — 없으면 다음 빌드에서 이 수정이 사라집니다 |
| 결함 E (공유 워크플로 UI) | 폴더·안내문은 있으나 화면이 기본 위치로 제시하는 작업 남음 |
| 결함 F (배포 관문) | 사내 PC의 파이썬 설치 확인이 선행 |
| 결함 I (동봉 템플릿 구버전) | `Template_v1.6` → **`v1.16`** 으로 교체 (이 패치와 무관) |
| 윈도우 실측 | **전부 리눅스에서만 검증** (R-N06). 특히 SMB 이어쓰기와 `os.access()` 권한 판정 |

`base_saved` 방어는 **호출자가 판본을 밝힐 때만** 작동합니다(낙관적 동시성). 화면은 항상 밝히지만, API를 직접 부르는 다른 프로그램이 밝히지 않으면 검사할 근거가 없습니다.
