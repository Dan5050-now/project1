# 15. 지표 계산 명세

*검토 반영 신규 문서 (요구사항 11)*

> 처리 조건과 계산식을 명확히 명세하여 **누가 언제 계산해도 같은 결과가 나오도록** 하는 것이 이 문서의 목적입니다.

## 1. 재현 가능성의 조건

같은 숫자가 다시 나오려면 다음 다섯 가지가 모두 고정되어야 합니다. 하나라도 빠지면 재현은 성립하지 않습니다.

| # | 고정 대상 | 어디서 보장하는가 |
|---|---|---|
| 1 | 입력 데이터 | Data Drop 불변 보존 + Snapshot ([08](08-platform-services.md) 4.1) |
| 2 | 기대 항목 생성 규칙 | Assumption Set 버전 ([13](13-trial-configuration.md)) |
| 3 | 처리 설정 (유예 기간, on/off, 범위) | Trial Config 버전 ([13](13-trial-configuration.md)) |
| 4 | **계산식** | **이 문서** |
| 5 | 기준 시점 | `as_of_date` |

계산 좌표는 다음과 같습니다.

```
metric_value = f(metric_code,
                 metric_definition_version,
                 snapshot_version,
                 assumption_version,
                 trial_config_version,
                 expected_basis,        # DUE | PROTOCOL | FORECAST
                 as_of_date,
                 filter)
```

**이 좌표 전체가 모든 계산 결과에 함께 저장되고, 화면과 export에 표시됩니다.**

## 2. 지표 정의 레코드

각 지표는 다음 구조로 **데이터베이스에 등록**됩니다. 문서가 아니라 데이터로 존재해야 앱이 스스로 설명할 수 있습니다.

| 필드 | 내용 |
|---|---|
| `metric_code` | 고유 코드. 예: `edc.entry.rate` |
| `version` | 정의 버전. 계산식이 바뀌면 증가 |
| `display_name_ko` / `display_name_en` | 표시명 |
| `definition_text` | 자연어 정의 한 문장 |
| `numerator_expr` | 분자 계산식 |
| `denominator_expr` | 분모 계산식 |
| `population_filter` | 모집단 조건 |
| `exclusion_rules` | 제외 규칙 목록 |
| `due_rule_ref` | 참조하는 Due 규칙 |
| `unit` | `COUNT` / `PERCENT` / `DAYS` |
| `rounding` | 반올림 규칙 |
| `null_policy` | 분모 0일 때의 처리 |
| `applicable_levels` | trial / country / site / subject |
| `threshold_warn` / `threshold_alert` | KRI 임계값 |
| `effective_from` / `effective_to` | 적용 기간 |

화면의 지표명 옆 `?` 아이콘이 이 레코드를 그대로 보여줍니다.

## 3. 공통 처리 규칙

모든 지표에 선행 적용되는 규칙입니다. 지표별 명세에서 반복하지 않습니다.

### 3.1 날짜와 기간

| 규칙 | 내용 |
|---|---|
| R-D1 | 유예 기간은 **달력일(calendar days)** 로 계산한다. 영업일 개념을 쓰지 않는다 |
| R-D2 | `due_date = trigger_date + grace_days` |
| R-D3 | 경과일 `aging = as_of_date - due_date`. 양수만 지연으로 간주 |
| R-D4 | 날짜 비교는 **날짜 단위**로 한다. 시각이 있어도 날짜로 절사한다 |
| R-D5 | 시간대는 `CFG01.TIMEZONE`을 기준으로 한다 |
| R-D6 | `due_date`와 `as_of_date`가 같은 날이면 **`PENDING`** (초과 아님) |

### 3.2 부분 날짜

`CFG01.PARTIAL_DATE_RULE` 설정을 따릅니다.

| 설정 | 처리 | 효과 |
|---|---|---|
| `LATEST` (기본) | `2026-03` → `2026-03-31` | 보수적. 지연으로 덜 잡힘 |
| `EARLIEST` | `2026-03` → `2026-03-01` | 공격적. 지연으로 더 잡힘 |
| `EXCLUDE` | 해당 항목을 분모에서 제외 | 정확하나 분모 축소 |

기본값을 `LATEST`로 둔 이유는, 불확실한 날짜 때문에 사이트를 지연으로 표시하는 것보다 놓치는 쪽이 낫다는 판단입니다. 잘못된 지연 판정은 신뢰를 잃습니다.

### 3.3 결측 처리

| 상황 | 처리 |
|---|---|
| 트리거 날짜 결측 | `due_date` 계산 불가 → 상태 `NOT_DUE`, **분모 제외**, 별도 "기한 산정 불가" 건수로 집계 |
| 완료 플래그 결측 | `N`으로 간주 |
| 완료 플래그 `Y`인데 완료일 결측 | **완료로 인정**. 단 일관성 경고 ([12](12-standard-source-templates.md) 5.4 X1) |
| 매칭 키 결측 | 항목 제외 + 검증 거부 |

"기한 산정 불가" 건수를 별도로 집계하는 것이 중요합니다. 조용히 분모에서 빠지면 지표가 이유 없이 좋아 보입니다.

### 3.4 나눗셈과 반올림

| 규칙 | 내용 |
|---|---|
| R-N1 | 분모가 0이면 결과는 **`N/A`**. 0%로 표시하지 않는다 |
| R-N2 | 비율은 소수점 첫째 자리까지 반올림 (`ROUND_HALF_UP`). 저장은 원시값 |
| R-N3 | 화면 표시와 저장값을 구분한다. 계산 중간에 반올림하지 않는다 |
| R-N4 | 롤업은 **항목 수준에서 합산 후 나눈다**. 하위 비율의 평균을 쓰지 않는다 |

R-N1이 특히 중요합니다. `0/0`을 0%로 표시하면 "전혀 진행 안 됨"으로 오해됩니다.

### 3.5 중복 처리

| 규칙 | 내용 |
|---|---|
| R-U1 | 동일 매칭 키의 복수 행이 있으면 **가장 진행된 상태**를 채택하고 중복을 보고한다 |
| R-U2 | 여러 Data Drop에 같은 키가 있으면 **최신 Drop**을 채택한다 |
| R-U3 | 같은 항목이 여러 소스에 있으면 Feed 우선순위 설정을 따른다 |

## 4. 단계 상태 판정 알고리즘

모든 A1 아키타입 항목에 공통 적용됩니다.

```
function determine_stage_status(item, stage, as_of_date, config):

    # 1. 단계 적용 여부
    if not config.stages[stage].enabled:
        return NOT_APPLICABLE
    if not scope_rule(stage).applies(item):
        return NOT_APPLICABLE

    # 2. 예외 처리 (분모 제외)
    if item.waiver[stage] is set:
        return WAIVED

    # 3. 완료 여부
    if item.completed_flag[stage] == 'Y':
        return DONE

    # 4. 기한 판정
    trigger_date = resolve_trigger(item, stage, config)
    if trigger_date is null:
        return NOT_DUE                 # 기한 산정 불가 (3.3)

    grace = config.stages[stage].grace_days
    if grace == 'N/A':
        return PENDING                 # investigator sign: OVERDUE 미사용

    due_date = trigger_date + grace
    if as_of_date <= due_date:
        return PENDING
    else:
        return OVERDUE
```

판정 순서가 중요합니다. **적용 여부 → 예외 → 완료 → 기한**의 순서이며, 이 순서를 바꾸면 결과가 달라집니다. 예를 들어 예외 판정을 완료 판정 뒤로 옮기면, 이미 완료된 항목이 예외로 분류되어 분모에서 빠지는 오류가 생깁니다.

## 5. 기본 계산식

[03](03-core-concept-model.md) 3.6의 공식입니다. 모든 A1 도메인에 동일 적용됩니다.

```
S(stage) = { item ∈ population | status(item, stage) = S }

backlog(stage)   = |PENDING(stage)| + |OVERDUE(stage)|
completed(stage) = |DONE(stage)|
due(stage)       = backlog(stage) + completed(stage)
rate(stage)      = completed(stage) / due(stage)        if due > 0 else N/A
overdue(stage)   = |OVERDUE(stage)|
overdue_rate     = overdue(stage) / due(stage)          if due > 0 else N/A
waived(stage)    = |WAIVED(stage)|                      # 분모 밖

aging_median(stage)  = median({as_of - due_date | item ∈ OVERDUE(stage)})
aging_p90(stage)     = 90th percentile of the same set
```

### 5.1 분모 기준별 모집단

`expected_basis` 값에 따라 `population`이 달라집니다.

| `expected_basis` | population |
|---|---|
| `DUE` (기본) | 상태가 `PENDING` / `OVERDUE` / `DONE` 인 항목 |
| `PROTOCOL` | 프로토콜상 생성 가능한 전체 기대 항목 (`NOT_DUE` 포함, `NOT_APPLICABLE`·`WAIVED` 제외) |
| `FORECAST` | `PROTOCOL` 중 지정 시점 `forecast_to_date`까지 due가 될 것으로 예측되는 항목 |

세 값은 **모두 계산되어 저장**되며, 화면 토글은 저장된 값 사이의 전환입니다 ([03](03-core-concept-model.md) 3.4).

## 6. 지표 목록

### 6.1 EDC (D1)

| `metric_code` | 정의 | 분자 / 분모 |
|---|---|---|
| `edc.entry.due` | 입력 기한 도래 폼 수 | — / — (건수) |
| `edc.entry.backlog` | 미입력 backlog | `PENDING + OVERDUE` |
| `edc.entry.rate` | 입력률 | `completed(entered) / due(entered)` |
| `edc.entry.overdue` | 기한 초과 미입력 | `OVERDUE(entered)` |
| `edc.sdv.rate` | SDV율 | `completed(sdv) / due(sdv)` |
| `edc.review.rate` | 리뷰율 | `completed(review) / due(review)` · **단계 on/off 적용** |
| `edc.coding.rate` | 코딩율 | `completed(coding) / due(coding)` |
| `edc.sign.pending_all` | **미서명 건수 (전체)** | `count(sign 대상 AND SIGNFL != 'Y')` |
| `edc.sign.pending_sae` | **미서명 건수 (SAE)** | `count(sign 대상 AND SAEFL='Y' AND SIGNFL != 'Y')` |
| `edc.freeze.rate` | Freeze율 | `completed(freeze) / due(freeze)` |
| `edc.lock.rate` | Lock율 | `completed(lock) / due(lock)` |
| `edc.waived.count` | 예외 건수 | `WAIVED` 합계, `waiver_type`별 분해 |

> **`edc.sign.*`에는 rate가 없습니다.** 유예 기간이 없으므로 `due`를 정의할 수 없고, 따라서 비율도 정의할 수 없습니다. 건수만 제공합니다 ([04](04-domain-concepts.md) 1.5).

### 6.2 Query (D1-c)

| `metric_code` | 정의 |
|---|---|
| `query.total` | 기간 내 발행 전체 |
| `query.open` | `state = OPEN` |
| `query.answered` | `state = ANSWERED` |
| `query.closed` | `state = CLOSED` |
| `query.open.overdue` | `OPEN AND as_of > opened_at + grace(owner, OPEN)` |
| `query.answered.overdue` | `ANSWERED AND as_of > opened_at + grace(owner, ANSWERED)` |
| `query.aging.median` | `OPEN` 건의 `as_of - opened_at` 중앙값 |
| `query.cycle_time.median` | `CLOSED` 건의 `closed_at - opened_at` 중앙값 |

`grace(owner, state)`는 `CFG05`에서 조회하며, 소유자가 목록에 없으면 기본값 행을 사용합니다.

모든 query 지표는 `owner` 및 `query_group`별로 분해 가능합니다.

### 6.3 RTSM (D2)

| `metric_code` | 정의 |
|---|---|
| `rtsm.subject.count` | 상태별 피험자 수 |
| `rtsm.visit.due` | 기한 도래 방문 수 |
| `rtsm.visit.completed` | 발생 방문 수 |
| `rtsm.visit.rate` | 방문 수행률 |
| `rtsm.visit.deviation.under` | 윈도우 조기 방문 수 |
| `rtsm.visit.deviation.over` | 윈도우 지연 방문 수 |
| `rtsm.visit.missed` | 윈도우 경과 미수행 수 |
| `rtsm.visit.compliance_rate` | `윈도우 내 방문 / 전체 발생 방문` |

### 6.4 Sample (D4)

| `metric_code` | 정의 |
|---|---|
| `sample.collected.rate` | `completed(collected) / due(collected)` |
| `sample.central.received.rate` | `completed(received_central) / due(received_central)` |
| `sample.central.backlog` | 채취되었으나 central lab 미도착 |
| `sample.bioanalytics.received.rate` | bioanalytics 도착률 |
| `sample.analyzed.rate` | 분석 완료율 |
| `sample.recon.edc_y_not_received` | 불일치 유형 1 건수 |
| `sample.recon.received_not_in_edc` | 불일치 유형 2 건수 |
| `sample.recon.discrepant` | 불일치 유형 3 건수 |
| `sample.recon.ambiguous` | 불일치 유형 4 건수 |
| `sample.recon.status` | `ALL_RECONCILED` / `PENDING_ISSUE` |
| `sample.issue.open` | 미해결 샘플 이슈 수 |
| `sample.waived.count` | 예외 건수 (분실·용혈 등) |

### 6.5 Image (D5)

| `metric_code` | 정의 |
|---|---|
| `image.taken.rate` | `completed(taken) / due(taken)` |
| `image.uploaded.rate` | `completed(uploaded) / due(uploaded)` |
| `image.uploaded.backlog` | 획득되었으나 미업로드 |
| `image.qc.pass_rate` | `QC passed / QC 수행` |
| `image.qc.fail_rate` | `QC failed / QC 수행` — **KRI 후보** |
| `image.read.rate` | 판독 완료율 |
| `image.recon.*` | 샘플과 동일 4유형 |

### 6.6 SDV Plan (D3)

| `metric_code` | 정의 |
|---|---|
| `sdv.visit.planned` | 계획 방문 수 (`TENTATIVE` + `ARRANGED`) |
| `sdv.visit.completed` | 완료 방문 수 |
| `sdv.visit.cancelled` | 취소 방문 수 |
| `sdv.capacity` | `Σ(planned_days × cra_count × daily_capacity)` |
| `sdv.forecast_volume` | `현재 sdv backlog + 예측 신규 SDV 대상` (Forecast 기준) |
| `sdv.adequacy_ratio` | `sdv.capacity / sdv.forecast_volume` |
| `sdv.adequacy_verdict` | `<0.8 UNDER` / `0.8~1.2 ADEQUATE` / `>1.2 OVER` |
| `sdv.days_since_last_visit` | 사이트별 마지막 SDV 방문 이후 경과일 — KRI 후보 |

### 6.7 Timeline (D6)

| `metric_code` | 정의 |
|---|---|
| `timeline.milestone.variance` | `actual_date - planned_date` |
| `timeline.milestone.at_risk` | 예측상 달성 어려운 마일스톤 수 |
| `timeline.milestone.missed` | 기한 경과 미달성 수 |
| `timeline.task.on_time_rate` | 기한 내 완료 task 비율 |
| `timeline.dbl_readiness.projected_date` | 현재 소진 속도 기준 DBL 가능 예상일 |

`timeline.dbl_readiness.projected_date`는 예측 지표이므로 [07](07-prediction-and-analytics.md) 4장의 표현 규칙(구간 추정, 근거 표시, 시각적 구분)이 적용됩니다.

### 6.8 데이터 품질

| `metric_code` | 정의 |
|---|---|
| `quality.drop.rejected_rows` | 업로드 거부 행 수 |
| `quality.drop.warning_rows` | 경고 행 수 |
| `quality.unmatched.count` | 매칭 실패 건수 |
| `quality.due_undeterminable` | 기한 산정 불가 건수 (3.3) |
| `quality.regression.count` | 이전 Drop 대비 역행 건수 ([12](12-standard-source-templates.md) 5.4 X4) |

이 지표들은 **앱 자신의 데이터 품질을 보여줍니다.** 사용자가 지표를 얼마나 신뢰해도 되는지 판단하는 근거입니다.

## 7. 명세의 검증

계산식이 문서와 코드에서 일치함을 지속적으로 확인합니다.

### 7.1 Golden Dataset

| 항목 | 내용 |
|---|---|
| 구성 | 소규모 합성 데이터 + 기대 결과값 |
| 범위 | 모든 지표, 모든 경계 조건 (분모 0, 부분 날짜, 예외, 결측, 중복) |
| 실행 | CI에서 매 빌드마다 실행 |
| 불일치 시 | 빌드 실패 |

### 7.2 경계 조건 목록

명세가 답해야 하는 까다로운 경우들입니다. 각각 golden dataset에 케이스로 존재해야 합니다.

| # | 경계 조건 | 기대 동작 |
|---|---|---|
| E1 | 분모 0 | `N/A` (0% 아님) |
| E2 | `due_date == as_of_date` | `PENDING` |
| E3 | 트리거 날짜 결측 | `NOT_DUE` + 별도 집계 |
| E4 | 완료 플래그 Y, 완료일 결측 | `DONE` + 경고 |
| E5 | 부분 날짜 `2026-03` | `PARTIAL_DATE_RULE` 적용 |
| E6 | 단계 `enabled = N` | 지표 자체가 사라짐 (0% 아님) |
| E7 | 예외 항목 | 분모 제외 + `waived` 별도 집계 |
| E8 | 동일 키 중복 행 | 최진행 상태 채택 + 중복 보고 |
| E9 | 탈락 후 방문 | 설정에 따라 `NOT_APPLICABLE` |
| E10 | 반복 폼 | entry 분모 제외, 이후 단계는 추적 |
| E11 | investigator sign | `rate` 없음, 건수만 |
| E12 | kit 유형 미구분 소스 | 경고 + reconciliation 신뢰도 낮음 표시 |

### 7.3 명세 변경 절차

계산식이 바뀌는 것은 **지표의 의미가 바뀌는 것**입니다. 다음 절차를 따릅니다.

```
① 변경 제안 (사유와 영향 범위 기술)
      ↓
② 영향 분석 — 과거 데이터로 재계산 시 값이 얼마나 달라지는가
      ↓
③ 승인 (지표 소유자)
      ↓
④ metric_definition_version 증가, effective_from 설정
      ↓
⑤ golden dataset 갱신
      ↓
⑥ 배포 — 과거 스냅샷은 과거 정의로 계산된 값 유지
```

⑥이 핵심입니다. **정의를 바꿨다고 과거 리포트의 숫자가 바뀌지 않습니다.** 화면에는 어느 정의 버전으로 계산된 값인지 표시됩니다.

## 8. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-15-1 | 3.2 부분 날짜 기본 규칙을 `LATEST`로 할 것인가 | `LATEST` 권고 |
| DP-15-2 | 3.5 R-U1(중복 시 최진행 상태 채택)이 타당한가 | 타당 |
| DP-15-3 | 6장 지표 목록에서 빠진 것이 있는가 | 실무 검토 필요 |
| DP-15-4 | 7.2의 경계 조건 12개 외에 추가할 것이 있는가 | 개발 중 추가 |
| DP-15-5 | 지표 소유자(정의 변경 승인자)를 누구로 할 것인가 | 기능별 리드 |
| DP-15-6 | 3.4 R-N2 반올림 자리수 | 소수점 첫째 자리 |
