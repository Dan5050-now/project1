# Golden Dataset — GOLD-001

[08. 테스트 계획](../08-test-plan.md)의 검증 기준입니다. **이 데이터로 계산한 결과가 `expected/`와 일치하지 않으면 빌드를 실패**시킵니다.

## 1. 구성

| 디렉터리 | 내용 |
|---|---|
| [`input/`](input/) | 시험 설정 7개 + 표준 dataset 4개 |
| [`expected/`](expected/) | 항목 수준 기대 상태, 지표 기대값, 검증 결과 기대값 |

기준 시각은 **`as_of = 2026-09-30`** 입니다 (`CFG01_TRIAL_SETTINGS.csv`).

## 2. 시험 설계

```
방문   V1 Baseline (offset 0)   V2 Cycle 1 (offset 14)   V3 Follow-up (offset 28)
       윈도우 모두 -3 / +3

SoA    V1 → DM(STANDARD), AE(LOG)
       V2 → VS(STANDARD), AE(LOG)
       V3 → VS(STANDARD), AE(LOG)

유예   entry 14 · sdv 60 · review 비활성 · coding 60 · sign N/A · freeze·lock DBL 기준
범위   sdv = VS만 (partial SDV) · coding = AE만 · sign/freeze/lock = 전체
예외   CODING_UNRESOLVABLE → coding 단계만 차단 (CFG10)
```

## 3. 피험자와 의도

| 피험자 | 사이트 | 상태 | 검증 의도 |
|---|---|---|---|
| G-001 | S01 | On treatment | 정상 진행 + 방문 윈도우 초과 + 중복 행 + 예외 처리 |
| G-002 | S01 | On treatment | 미입력 기한 초과 + 방문 미수행 |
| G-003 | S02 | On treatment | **기한일 == 기준일** 경계 |
| G-004 | S02 | Discontinued | **탈락 후 FOLLOWUP 방문 기대 유지** + 부분 날짜 + 서명 완료 |
| G-005 | S01 | Screen failed | **기준일 없음 → 항목 생성 안 됨** |
| G-006 | S01 | On treatment | **완료 플래그만 있고 완료일 없음** → 후속 단계 기한 미산출 |
| G-007 | S01 → **S02** (2026-07-10) | On treatment | **사이트 이전.** 전 항목이 S02로 이동 + 이전 시점 미종결 1건 |

## 4. 다루는 경계 조건

[개념 15](../../concept/15-metric-specification.md) 7.2의 경계 조건 중 Phase 1 범위입니다.

| # | 조건 | 어디서 |
|---|---|---|
| E1 | 분모 0 → `N/A` (0% 아님) | `lock` 단계 전체 |
| E2 | `due_on == as_of` → `PENDING` | G-003 V1 DM entry |
| E3 | 트리거 날짜 결측 → `NOT_DUE` | G-006 V1 AE coding |
| E4 | 완료 플래그 Y, 완료일 결측 → `DONE` + 경고 | G-006 V1 DM entry |
| E5 | 부분 날짜 `2026-07` → `LATEST` 적용 | G-004 V3 VS entry |
| E6 | 단계 비활성화 → **행 자체가 없음** | `review` |
| E7 | 예외 항목 → 분모 제외 + 별도 집계 | G-001 V1 AE |
| E8 | 동일 키 중복 → 진행된 상태 채택 + 보고 | G-001 V1 DM |
| E9 | 탈락 후 방문 → 설정에 따라 기대 유지 | G-004 V3 |
| E10 | 반복 폼(LOG) → entry 분모 제외, 이후 단계는 추적 | AE 전체 |
| E11 | investigator sign → rate 없음, 건수만 | `sign` |
| E17 | 완료일 없음 → 소요일수 미산출 | G-006 |
| E18 | 그 날짜를 쓰는 후속 단계 → 기한 미계산 | G-006 sign |
| **E19** | **기준일(anchor) 없음 → 항목 생성 안 됨** | G-005 |
| **E20** | **사이트 이전 → 전 항목이 새 사이트로 이동** | G-007 |

`E12`~`E16`(kit 유형 매칭, 결합형 파일, 증분 전송, timepoint)은 샘플·영상 도메인이므로 **Phase 2 golden dataset**에서 다룹니다.

### 4.1 E7 — 예외 범위가 이슈 유형에 따라 달라진다

Q-003의 유형은 `CODING_UNRESOLVABLE`이고, `CFG10`은 이 유형이 **`coding` 단계만** 차단하도록 정의합니다.

| 대상 항목 | 단계 | 결과 |
|---|---|---|
| G-001 V1 AE | `coding` | **WAIVED** — 분모 제외 |
| G-001 V1 AE | `sign` | **PENDING** — 계속 추적 |

유형별 규칙이 없다면 이 항목의 모든 미완료 단계가 예외 처리되어 `sign`까지 분모에서 빠집니다. **그 차이를 잡는 것이 이 케이스의 목적**입니다.

### 4.2 E20 — 사이트 이전 귀속

G-007은 V1을 S01에서 받고 **2026-07-10에 S02로 이전**한 뒤 V2를 S02에서 받았습니다.

| 항목 | 귀속 | 근거 |
|---|---|---|
| V1 방문 · V1 DM (S01에서 수행) | **S02** | 전 항목이 현재 소속으로 이동 |
| V2 방문 · V2 VS | **S02** | 동일 |
| V3 방문 (미발생) | **S02** | 동일 |

`DS02`의 V1 행은 `SITEID = S01`로 남아 **실제 수행 사이트를 사실로 보관**하지만, 롤업에는 쓰이지 않습니다.

검증 지점은 두 가지입니다. **S01의 집계에 G-007이 전혀 나타나지 않아야** 하고, S02의 분자(입력 완료 2건)에 이전 전 입력분이 포함되어야 합니다.

#### 이전 시점 미종결 항목

이전일(07-10) 기준으로 G-007 V1 DM의 `sign`이 `PENDING`이었습니다. 운영 규칙은 **이전 전에 모든 pending을 종결하는 것**이므로 이것은 규칙 위반입니다.

앱은 막지 않고 **`X9` 경고**로 드러냅니다. 막으면 업무가 멈추고, 침묵하면 S02가 이유 없이 나빠 보입니다. `quality.transfer_with_open_items = 1`이 기대값입니다.

## 5. 핵심 기대값

| 지표 | due | 완료 | rate |
|---|---|---|---|
| `edc.entry.rate` (trial) | 11 | 9 | **0.8182** |
| `edc.entry.rate` (S01) | 5 | 4 | 0.8000 |
| `edc.entry.rate` (S02) | 6 | 5 | 0.8333 |
| `edc.sdv.rate` (trial) | 5 | 0 | 0.0000 |
| `edc.coding.rate` (trial) | 1 | 0 | 0.0000 (예외 1건 제외) |
| `edc.lock.rate` (trial) | 0 | 0 | **공란 = N/A** |
| `rtsm.visit.rate` (trial) | 16 | 11 | 0.6875 |
| `edc.sign.pending_all` | — | — | **7건** |
| `edc.sign.pending_sae` | — | — | **1건** |

### 5.1 Simpson 검증

사이트별 rate는 0.8000과 0.8333이므로 **단순 평균은 0.8167**(반올림)입니다. 전체 rate는 **0.8182**로 다릅니다.

이 차이가 [개념 03](../../concept/03-core-concept-model.md) 6.2의 롤업 규칙을 검증합니다. 앱이 0.8167을 내놓으면 **하위 비율을 평균한 것**이므로 구현이 틀린 것입니다.

## 6. 갱신 규칙

| 상황 | 절차 |
|---|---|
| 계산식 변경 | `metric_definition` 버전 증가 → golden 기대값 갱신 → 변경 근거 기록 |
| 경계 조건 추가 | 입력에 케이스 추가 → 기대값 추가 |
| 기대값이 틀렸음이 발견됨 | **기대값을 코드에 맞추지 않는다.** 어느 쪽이 옳은지 먼저 판정 |

마지막 행이 중요합니다. 테스트가 실패할 때 기대값을 고쳐 통과시키는 것은 golden dataset의 목적을 무너뜨립니다.
