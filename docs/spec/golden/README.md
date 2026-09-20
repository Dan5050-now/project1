# Golden Dataset — GOLD-001

[08. 테스트 계획](../08-test-plan.md)의 검증 기준입니다. **이 데이터로 계산한 결과가 `expected/`와 일치하지 않으면 빌드를 실패**시킵니다.

## 1. 구성

| 디렉터리 | 내용 |
|---|---|
| [`input/`](input/) | 시험 설정 6개 + 표준 dataset 4개 |
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

`E12`~`E16`(kit 유형 매칭, 결합형 파일, 증분 전송, timepoint)은 샘플·영상 도메인이므로 **Phase 2 golden dataset**에서 다룹니다.

## 5. 핵심 기대값

| 지표 | due | 완료 | rate |
|---|---|---|---|
| `edc.entry.rate` (trial) | 9 | 7 | **0.7778** |
| `edc.entry.rate` (S01) | 5 | 4 | 0.8000 |
| `edc.entry.rate` (S02) | 4 | 3 | 0.7500 |
| `edc.sdv.rate` (trial) | 4 | 0 | 0.0000 |
| `edc.coding.rate` (trial) | 1 | 0 | 0.0000 (예외 1건 제외) |
| `edc.lock.rate` (trial) | 0 | 0 | **공란 = N/A** |
| `rtsm.visit.rate` (trial) | 13 | 9 | 0.6923 |
| `edc.sign.pending_all` | — | — | **4건** |
| `edc.sign.pending_sae` | — | — | **1건** |

### 5.1 Simpson 검증

사이트별 rate는 0.8000과 0.7500이므로 **단순 평균은 0.7750**입니다. 전체 rate는 **0.7778**로 다릅니다.

이 차이가 [개념 03](../../concept/03-core-concept-model.md) 6.2의 롤업 규칙을 검증합니다. 앱이 0.7750을 내놓으면 **하위 비율을 평균한 것**이므로 구현이 틀린 것입니다.

## 6. 갱신 규칙

| 상황 | 절차 |
|---|---|
| 계산식 변경 | `metric_definition` 버전 증가 → golden 기대값 갱신 → 변경 근거 기록 |
| 경계 조건 추가 | 입력에 케이스 추가 → 기대값 추가 |
| 기대값이 틀렸음이 발견됨 | **기대값을 코드에 맞추지 않는다.** 어느 쪽이 옳은지 먼저 판정 |

마지막 행이 중요합니다. 테스트가 실패할 때 기대값을 고쳐 통과시키는 것은 golden dataset의 목적을 무너뜨립니다.
