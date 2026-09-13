# v1.21의 `src/`에 응급 수정을 영구 반영 — 결과

바로 앞 단계(`README-v1.21-패치적용.md`)에서는 **이미 배포된 `PM_APP/` 폴더를 직접 고쳤습니다.** 지금 바로 쓸 수 있는 대신 한 가지 빚이 남아 있었습니다. `PM_APP/`은 소스에서 **생성되는** 폴더라서, 다음번에 누군가 소스에서 빌드하면 그 수정이 조용히 사라진다는 것이었습니다. 이번에 v1.21의 `src/`와 `tools/`를 받아 **그 빚을 갚았습니다.** 이제 수정은 소스에 들어 있고, 빌드를 몇 번 다시 해도 살아남습니다.

| | |
|---|---|
| 받은 것 | `PRAP_source_src_tools.zip` (`src/` 45개, `tools/` 70개), `PRAP_relevant_docs.zip` |
| 출발점 | v1.21 소스 (엔진 v1.51, V-36 · unstaffed 표기 포함) |
| 결과 | **v1.21.1 소스** — 10개 파일, +767 / −48 줄 |
| 소스 패치 | `0002-v1.21-src-NR-STO-07-15-16.patch` (1,177줄) |
| 배포본 패치 | `PM_APP_v1.21_to_v1.21.1.patch` (이미 쓰고 있는 폴더용, 새로 생성) |
| 실행 패키지 | `PM_APP_python_v1.21.1.zip` — 14개 파일, 248 KB<br>`bc302b477891be2b2dcfec86c67ebe18b9ab2866f8eb9dfa8123bc0554ca559d` |
| 소스 패키지 | `PRAP_src_tools_v1.21.1.zip` — 115개 파일, 944 KB<br>`fd4dc69a7d092601c1f587990e1706f42646cc211ff0d6dbaeee8edb4b80a719` |

---

## 1. 먼저 확인한 것 — "이 소스가 정말 그 앱을 만드는가"

소스를 고치기 전에 반드시 확인해야 할 것이 하나 있었습니다. **받은 `src/`가 실제로 쓰고 있는 v1.21 앱을 만들어내는 소스인지**입니다. 이것이 맞지 않으면, 소스를 고쳐도 고쳐지는 대상이 다른 프로그램입니다.

받은 소스만으로 빌드해서 배포본과 한 글자씩 대조했습니다.

```
python tools/build_python_app.py   →  dist/PM_APP_py  (파일 14개)

배포된 v1.21 폴더와 sha256 비교:
  PM_APP.py              동일
  version.txt            동일
  READ ME FIRST.txt      동일
  app/index.html         동일   ← 70만 자의 화면 전체
  pmapp/ 파이썬 11개      동일
  ───────────────────────────────
  14개 파일 전부 바이트 단위로 동일
```

**받은 소스는 쓰고 있는 앱을 정확히 재현합니다.** 이 확인이 있기 때문에, 아래의 모든 차이는 "v1.21과 다른 무엇"이 아니라 **오직 이번 수정 때문에 생긴 차이**라고 말할 수 있습니다.

---

## 2. 적용 — 충돌 없음

앞 단계에서 예고한 대로, 패치가 손대는 파일(저장·셸)과 v1.21이 바꾼 파일(계산·표시)은 겹치지 않았습니다. 그래서 기계가 알아서 넣었고, 사람이 손으로 판단해 붙인 곳은 **한 곳도 없습니다.**

```
git am --3way 0001-wire-storage-operations-NR-STO-07-15-16.patch
  → Applying: fix(shell): wire the three storage operations nothing called
  → 충돌 0건,  7개 파일,  +484 / −27
```

그다음 빌드에서 이 수정이 실제로 화면에 실려 나가는지 확인했습니다.

```
빌드된 app/index.html 안에서:
  "ws/stat"          2회      ← 예전엔 0회
  "journal/write"    1회      ← 예전엔 0회
  "journal/clear"    1회      ← 예전엔 0회
  "claim/release"    1회      ← 예전엔 0회
v1.21 이 새로 넣은 것:
  V-36 규칙          7곳       보존
  unstaffed 표기     14곳      보존
  엔진 APP_VERSION   1.51      보존
```

---

## 3. 이번에 새로 찾아서 막은 구멍 — NR-STO-15의 나머지 절반

소스를 반영하면서 사양서(`PRAP_NewApp_Specification_v1.6.xlsx`)와 제 수정 내역을 한 줄씩 맞춰 읽다가, **제가 "해결했다"고 적어 놓은 요구사항이 실은 절반만 해결되어 있었다**는 것을 발견했습니다. 사양의 문장은 이렇게 두 부분으로 되어 있습니다.

> NR-STO-15 — 편집 권한은 저장·닫기, 변경 취소, 앱 종료 시 반납되며, **기다리고 있던 세션은 워크스페이스를 다시 열지 않고도 그것을 넘겨받을 것을 안내받는다.**

앞 절반(반납)은 고쳐져 있었습니다. 뒤 절반(안내)은 아니었습니다. 코드를 보면 30초마다 도는 확인 장치가 **"내가 권한을 들고 있을 때만"** 동작하게 되어 있어서, 정작 **기다리는 쪽은 아무 소식도 듣지 못했습니다.** 즉 이런 상황이었습니다.

| 시각 | 사용자 B(기다리는 쪽)가 실제로 겪던 일 |
|---|---|
| 09:10 | 수정하려 함 → *"읽기 전용 — 김민준님이 편집 중"* |
| 09:20 | A가 저장하고 끝냄 → **아무 안내 없음** |
| 09:20~ | B는 계속 읽기 전용이라고 믿음. 알아낼 방법은 **찍어서 다시 시도해 보는 것뿐** |

여러 사람이 한 계획서를 나눠 쓰는 환경에서는 이것이 실질적인 대기 비용입니다. 그래서 **나머지 절반도 구현했습니다.**

- 막혔을 때 **누가 들고 있는지 기억**해 둡니다(`blockedBy`).
- 그 상태에서 30초마다 **잠금이 풀렸는지만** 확인합니다.
- 풀렸으면 화면에 이렇게 알립니다. *"이 계획서는 이제 비어 있습니다 — 들고 있던 분이 끝냈습니다. 편집을 시작하시면 당신 것이 됩니다. **아무것도 다시 불러오지 않았으므로 화면은 보고 계셨던 그대로입니다.**"*

마지막 문장이 중요합니다. 사양의 S-N07은 *"막혀 있던 세션은 자기가 보던 화면을 유지한다"*고 정해 두었습니다. 그래서 이 안내는 **화면을 새로 고치지 않습니다.** 그리고 기다리는 동안 남이 저장해서 화면이 낡아진 경우라면, 이 안내는 물러나고 **"남이 저장했습니다 → 다시 불러오십시오"**(NR-STO-16)라는 더 강한 경고가 이깁니다. 둘이 동시에 말하면 사용자가 헷갈리기 때문입니다.

이 동작은 **말로만 두지 않고 시험으로 고정했습니다.** 다른 PC의 인스턴스가 남기는 잠금 파일을 손으로 만들어 두고, 편집이 실제로 거부되는지, 잠금을 지우면 안내가 뜨는지, 그때 화면이 다시 불려오지 않았는지를 브라우저에서 확인합니다.

```
being told the plan has freed, without reopening it
  ok   a colleague's claim blocks the edit, and the window remembers whose   blocked by A Colleague
  ok   AND WHEN THEY FINISH, THE WAITING SESSION IS OFFERED IT - without reopening
       the workspace (NR-STO-15)
       This plan is free now — whoever had it has finished with it. Start editing…
  ok   and nothing was reloaded, so the view it was reading is still there (S-N07)
```

### 그리고 더 오래 갇히는 경우 — 상대방의 PC가 죽었을 때

이 절반을 구현하다 보니 **더 나쁜 경우**가 드러났습니다. 앞의 경우는 상대가 작업을 끝내면 잠금 파일이 지워지므로 적어도 끝이 있습니다. 그런데 **상대방의 PC가 그대로 꺼진 경우에는 잠금 파일을 지워 줄 사람이 없습니다.** 사양은 이 경우를 위해 **30분이 지나면 그 잠금은 효력을 잃는다**고 정해 두었고(Q-N16), 코드도 실제로 그때는 잠금을 가져가도록 되어 있습니다. 문제는 **아무도 그 사실을 알려주지 않는다**는 것이었습니다. 기다리는 사람은 30분이 지났다는 것도, 지금은 편집할 수 있다는 것도 모르고, "혹시 지금은 되나" 하고 **다시 눌러 봐야만** 알 수 있었습니다.

그래서 잠금이 **효력을 잃은 경우도** 같은 방식으로 알립니다. 다만 **문구는 다릅니다** — 일을 끝낸 동료와, 문장 중간에 노트북이 꺼진 동료는 같은 상황이 아니고, 후자는 자기 작업을 잃었을 수도 있기 때문입니다.

> *"이제 이 계획서를 편집할 수 있습니다 — A Colleague님이 30분 넘게 응답이 없어, 이 계획서는 더 이상 그분의 것으로 취급되지 않습니다. 아무것도 다시 불러오지 않았습니다. **그분의 편집이 중요한 것이었다면 먼저 연락해 보시는 것이 좋습니다.**"*

```
  ok   a holder whose machine died is not waited out in silence either
       (NR-STO-14, Q-N16)
       You can edit this plan now — A Colleague has gone quiet for over half an hour…
  ok   and acting on that offer really does hand the plan over   displaced A Colleague
```

마지막 검사는 **안내가 거짓이 아님**을 확인하는 것입니다. 안내만 띄우고 실제로는 여전히 막히는 것이 가장 나쁜 결과이므로, 안내를 보고 편집을 시작했을 때 잠금이 정말로 넘어오는지(그리고 넘어온 기록에 **밀려난 사람의 이름이 남는지**) 함께 확인합니다.

---

## 4. 또 하나 — 정전 복구 기록이 15% 확률로 버려지고 있었습니다 (공유 폴더에서는 사실상 항상)

전체 회귀를 돌리다가 **간헐적으로 실패하는 검사 하나**가 나왔습니다. 이런 것은 보통 "테스트가 예민해서"로 넘어가지만, 그러지 않고 원인을 끝까지 봤습니다. **결함이었습니다.**

문제가 된 규칙은 이렇습니다. 정전 대비 기록(저널)을 되돌려 줄 때, 그것이 **계획서보다 새로운지**를 **파일 수정시각**으로 비교하고 있었습니다.

```
if  저널의 수정시각  <=  계획서의 수정시각:   저널을 버린다
```

의도는 맞습니다 — 이미 대체된 숫자를 근거로 만든 편집을 되살리면 안 됩니다. 그런데 **두 파일이 같은 순간에 쓰이면 수정시각이 같아지고**, `<=` 때문에 **버려집니다.** 저널은 바로 **저장 직후에 쓰이는 물건**이므로, 이것은 드문 경우가 아니라 **흔한 경우**입니다. 짐작이 아니라 세어 봤습니다.

```
같은 조건을 200회 반복 (로컬 디스크):
  저널이 버려진 횟수:  30회  (15%)
  첫 유실 시 수정시각 차이:  0ms   ← 같은 순간에 쓰였다

윈도우 공유 폴더(SMB)의 성질을 재현하면:
  SMB 는 수정시각을 2초 단위로 반올림합니다
  → 저장 후 2초 안에 쓰인 저널은 전부 "같은 시각"으로 보입니다
  → 저널 버려짐   ← 정전 시 편집 내용 유실
```

마지막 줄이 이 문제의 무게입니다. **이 앱이 실제로 놓일 곳이 바로 윈도우 공유 폴더입니다.** 그 환경에서는 15%가 아니라, **저장 직후 2초 안에 쓰인 저널은 사실상 전부** 버려집니다. 즉 제가 이번에 배선한 NR-STO-07(정전 복구)은 **배선만으로는 작동하지 않는 상태**였습니다 — 기록은 쓰이지만, 되돌려 줄 때 버려집니다.

고친 방법은 **이미 같은 이유로 한 번 쓴 방법**입니다. 수정시각을 버리고, **계획서 자신이 말하는 저장 시각(`last_saved`)** 을 비교합니다. 저널을 쓸 때 "나는 이 판본을 보고 만들어졌다"를 함께 적어 두고, 되돌려 줄 때 **그 판본이 아직 그대로인지**만 봅니다.

| | 예전 (수정시각) | 지금 (판본 표시) |
|---|---|---|
| 저장 직후에 쓰인 저널 | **버려짐** (같은 시각) | **되돌려 줌** ✅ |
| 남이 그 뒤에 저장한 경우 | 버려짐 | 버려짐 ✅ |
| 폴더를 복사해 옮긴 경우 | **버려짐** (복사로 시각이 바뀜) | **되돌려 줌** ✅ (내용은 같은 판본) |
| 구버전이 남긴 저널 | 수정시각 규칙 | 수정시각 규칙 (비교할 근거가 그것뿐) |

세 번째 줄은 덤으로 고쳐진 것입니다. 공유 폴더를 다른 곳으로 복사하면 파일의 수정시각은 복사한 시각으로 바뀌지만 **내용은 같은 판본**입니다. 예전 규칙은 이 경우에도 저널을 버렸습니다.

**두 셸 모두 고쳤습니다.** 저널 파일 형식은 파이썬 셸과 Electron 셸이 **일부러 똑같이** 맞춰 놓은 것이고(같은 공유 폴더에 두 셸이 섞여 있을 수 있으므로), 한쪽만 고치면 그 약속이 깨집니다. 그리고 **테스트도 고쳤습니다** — 파이썬 쪽 검사에는 `time.sleep(0.02)`이 들어 있었고, 그것이 바로 이 규칙이 같은 순간을 견디지 못한다는 표시였습니다. 잠을 빼고, **SMB의 2초 반올림을 재현하는 검사**로 바꿨습니다.

```
tools/test_storage_py.py   →  83 passed, 0 failed   (기존 80 + 신규 3)
  ok   and which save it was made against, which is what makes it judgeable
  ok   a journal made against a superseded save is not offered
  ok   and one written in the same tick as its save IS offered, which is when a
       journal is actually written
  ok   a journal from an older version, with only times to go on, still obeys them

tools/test_storage.mjs     →  FAILURES: none
  ok   a journal made against a SUPERSEDED save is not offered
  ok   and one written in the same tick as its save IS offered
```

---

## 5. 검증 — 소스에서 빌드한 것으로

### 5.1 경계와 저장 계층

```
tools/test_layers.py      →  FAILURES: none
                             셸 7개 모듈 모두 표준 라이브러리만 사용 (NR-DEP-05)
                             계층은 계획서가 말하는 그 4개 (core, shell, storage, ui)
tools/test_storage_py.py  →  83 passed, 0 failed
                             8개 프로세스 동시 경쟁에서 승자 1명 (NR-STO-10)
```

`test_storage_py.py`의 검사 하나는 이번에 **고쳐서** 통과한 것이 아니라 **시험 자체를 고쳤습니다.** 저장되는 판본 번호를 `== 5`로 하드코딩해 두어서, 틀린 값을 틀린 값과 비교하며 통과하고 있었습니다. 지금은 엔진이 읽는 값(`core/00_meta.js`의 `SCHEMA_EXPECTED`)을 직접 읽어와 비교합니다.

### 5.2 실제 화면을 띄워서

```
tools/test_python_app.py  →  0 failed

  ok   EVERY FIGURE EQUALS THE PYTHON REFERENCE IMPLEMENTATION
       1,227 person-months compared, worst difference 0.00e+00
  ok   the page actually calls ws/stat / journal/write / journal/clear / claim/release
  ok   releasing gives the plan back at once, not at its expiry
  ok   and opening another plan hands the first one back (NR-STO-15)
  ok   'Leave without change' hands the plan back too (NR-STO-15)
  ok   a colleague's claim blocks the edit, and the window remembers whose
  ok   AND WHEN THEY FINISH, THE WAITING SESSION IS OFFERED IT (NR-STO-15)
  ok   and nothing was reloaded (S-N07)
  ok   a holder whose machine died is not waited out in silence either (Q-N16)
  ok   and acting on that offer really does hand the plan over
  ok   a pending edit is written to the journal (NR-STO-07)
  ok   committing or discarding clears it
  ok   the application notices the plan moved on beneath it (NR-STO-16)
  ok   AND THE SAVE IS REFUSED rather than replacing their work
  ok   and the window says so, so nobody quotes the figures on screen
  ok   no script error anywhere in the run
  ok   nothing is written outside the application folder
```

계산 결과가 **파이썬 독립 구현과 소수점 이하까지 정확히 일치**한다는 것(`0.00e+00`)은, 이 수정이 숫자를 단 하나도 건드리지 않았다는 뜻입니다.

### 5.3 일을 잃는 그 시나리오 — 다시 재현

검토서 4판에서 v1.21이 **실패했던** 재현을, 소스에서 빌드한 v1.21.1로 다시 돌렸습니다. 실제로 PM_APP 두 개를 띄우고 한 공유 폴더를 함께 쓰게 한 것입니다.

| 시각 | 일어난 일 | v1.21 | **v1.21.1 (소스 빌드)** |
|---|---|---|---|
| 09:00 | A가 프로젝트 3건 저장 | | |
| 09:05 | B가 열어 봄 | | 기준 시각 기록 |
| 09:30 | A가 12건으로 저장 (9건 추가) | | |
| 09:35 | A 종료 → 잠금 해제 | | True |
| 09:40 | B가 편집 시작 → 잠금 획득 | | True |
| 09:41 | **B가 저장** | 허용됨 | **거부됨** |
| | 파일에 남은 프로젝트 | 3건 | **12건** |
| | **A의 작업 9건** | **사라짐** | **보존됨 ✅** |

거부 메시지는 이렇습니다. *"shared.prap was saved by somebody else after you opened it. Nothing has been saved, so their work is intact. Reload the plan and make your change again, or Save As a copy to keep yours."* — **무엇이 일어났는지, 남의 일은 안전한지, 이제 무엇을 하면 되는지**를 한 문장에 담는 것이 이 메시지의 목적입니다.

### 5.4 전체 회귀 — 39개 스위트

```
38 통과 · 1 실패

실패 1건:  test_interop  "every file the manifest points at exists"
           → docs/PRAP_UI_Component_List_v2.2.xlsx
             docs/PRAP_AI_Agent_Guide_v1.0.xlsx     두 파일이 없음
```

이 한 건은 **이 수정과 무관합니다.** 손대지 않은 v1.21 소스에서도 똑같이 실패하며(대조해 확인했습니다), 원인은 **두 문서 파일이 업로드에 포함되지 않은 것**입니다. 귀사 저장소에는 있을 것으로 보이므로 확인만 부탁드립니다. 다만 한 가지는 짚어 둘 필요가 있습니다 — **AI Agent Guide는 `.md`로 배포되는데 manifest는 `.xlsx`를 가리키고 있습니다.** 이름이 어긋나 있을 가능성이 있고, 그렇다면 귀사 저장소에서도 같은 검사가 실패할 것입니다.

나머지 38개는 전부 통과했습니다. 계산·차트·표·필터·입력·검증·내보내기·가져오기 비교·종료 처리·저장 계층(파이썬 83건, Electron 전건)·아키텍처 경계가 모두 포함됩니다.

---

## 6. 무엇을 어떻게 쓰면 되는가

세 가지 형태로 준비했습니다. **하나만 고르시면 됩니다.**

| | 무엇인가 | 언제 이것을 고르는가 |
|---|---|---|
| **① 실행 패키지**<br>`PM_APP_python_v1.21.1.zip` | 압축만 풀면 되는 완성본 | **그냥 쓰고 싶을 때.** 공유 폴더에 풀어 놓으면 끝 |
| **② 소스 패키지**<br>`PRAP_src_tools_v1.21.1.zip` | 수정이 반영된 `src/` + `tools/` | **앞으로 계속 개발할 때.** 이것이 정본 |
| **③ 패치 2종** | 지금 가진 것에 얹는 차이 | 이미 손댄 것이 있어 골라 넣어야 할 때 |

③의 두 패치는 대상이 다릅니다. 헷갈리기 쉬운 부분이라 적어 둡니다.

```
0002-v1.21-src-NR-STO-07-15-16.patch      ← src/ 와 tools/ 에 적용 (정본)
      git am --3way 0002-*.patch
      python tools/build_python_app.py       ← 그다음 반드시 빌드

PM_APP_v1.21_to_v1.21.1.patch             ← 이미 배포된 PM_APP/ 폴더에 적용
      patch -p1 < PM_APP_v1.21_to_v1.21.1.patch
      단, app/index.html 은 이 패치에 없습니다 (70만 자의 생성 파일)
      → 위 ①의 app/index.html 로 교체하거나, 소스에서 빌드하십시오
```

> **권장은 ②입니다.** ①은 편하지만 **다시 빌드하면 사라지는 종류의 편함**이 아니라는 점만 확실히 해 두시면 됩니다 — ①은 ②로부터 빌드한 것이므로 둘은 같은 내용입니다. 다만 앞으로 기능을 더 붙이실 것이므로, 팀의 원본으로 삼아야 할 것은 ②입니다.

---

## 7. 여전히 남은 일

이 수정으로 **데이터를 잃는 결함은 닫혔습니다.** 그러나 검토서가 지적한 것 중 이 패치의 범위가 아닌 것들이 남아 있습니다. 숨기지 않고 적어 둡니다.

| 항목 | 상태 | 왜 여기서 하지 않았는가 |
|---|---|---|
| 결함 E — 공유 워크플로 UI | **미완** | 폴더(`data\shared\workspaces\`)와 안내문은 만들어졌지만, 화면이 이 폴더를 **기본 위치로 제시**하는 작업이 남았습니다. 화면 설계 변경이라 응급 수정의 범위를 넘습니다 |
| 결함 F — 파이썬 설치 관문 | **미확인** | 사내 PC에 파이썬이 있는지는 코드로 알 수 없습니다. 확인 후 결정할 사항입니다 |
| 윈도우 실측 (R-N06) | **미실시** | 모든 검증이 리눅스에서 이루어졌습니다. 특히 **SMB 공유에서의 이어쓰기 원자성**과 `os.access()`의 권한 판정 정확도는 윈도우 공유 폴더에서 직접 재 보아야 합니다 |
| 여러 사람 동시 편집(서버형) | **설계 단계** | 요청하신 "레코드 단위 차단"은 현재 구조(계획서 파일 1개당 편집자 1명)와 다른 설계입니다. 검토서 5장에 별도로 정리해 두었습니다 |

마지막으로 한 가지 성질을 기억해 두시는 것이 좋습니다. 남의 저장을 덮어쓰지 못하게 막는 장치(`base_saved`)는 **저장하려는 쪽이 "나는 이 판본을 보고 있었다"고 밝힐 때만** 작동합니다. 화면은 항상 밝히므로 사람이 쓰는 경로는 안전합니다. 그러나 나중에 다른 프로그램이 이 앱의 API를 직접 부르게 만든다면, **그 프로그램도 판본을 밝혀야 합니다.** 밝히지 않으면 검사할 근거가 없어 그대로 저장됩니다. 이것은 낙관적 동시성 제어의 일반적인 성질이며, 고장이 아니라 **약속**입니다.
