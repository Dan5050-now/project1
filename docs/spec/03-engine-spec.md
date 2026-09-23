# 03. 엔진 사양

세 엔진의 알고리즘 사양입니다. 이 문서의 의사코드가 [개념 15](../concept/15-metric-specification.md)의 계산식 명세를 구현 수준으로 옮긴 것이며, golden dataset([08](08-test-plan.md))이 이 사양의 검증 기준입니다.

## 1. 실행 모델

```
업로드 확정 / 설정 변경 / 수동 실행
        │
        ▼
 ① ExpectationEngine   기대 항목 생성·갱신
        ▼
 ② ProgressEngine      실적 매칭, 단계 상태 판정
        ▼
 ③ RollupEngine        MetricFact 산출
        ▼
   Snapshot state = READY
```

세 엔진은 **하나의 `engine_run` 안에서 순차 실행**됩니다. 중간 실패 시 스냅샷은 `FAILED`로 남고 이전 스냅샷이 계속 조회됩니다. 부분 반영은 하지 않습니다.

### 1.1 실행 단위와 트랜잭션

| 항목 | 방침 |
|---|---|
| 실행 단위 | 시험 1개 전체 |
| 트랜잭션 | 엔진별로 커밋. 스냅샷 `state`가 `READY`가 되기 전에는 조회에 노출되지 않음 |
| 동시 실행 | 시험당 1개. 진행 중 재요청은 큐잉 |
| 재실행 | 멱등. 같은 입력·좌표면 같은 결과 |

### 1.2 증분 실행

전체 재생성은 N-4 기준 15분이 걸리므로, 일상 업로드에서는 **영향 범위만 재계산**합니다.

| 트리거 | 재계산 범위 |
|---|---|
| Drop 확정 (DS01/DS02) | 해당 피험자의 전 항목 |
| Drop 확정 (DS03/DS04) | 해당 폼·쿼리 항목만 |
| 설정 변경 | 시험 전체 |
| 가정 변경 | 시험 전체 |
| 날짜 경과 (일 배치) | `status` 재판정만 (항목 생성 없음) |

마지막 행이 중요합니다. **아무 업로드가 없어도 날짜가 지나면 `PENDING`이 `OVERDUE`로 바뀝니다.** 일 1회 배치로 상태만 재판정합니다.

## 2. ExpectationEngine

### 2.1 입력과 출력

| 입력 | 출처 |
|---|---|
| 활성 `assumption_set` (visit_schedule, soa_activity, enrollment_plan) | 3.2 |
| 활성 `trial_config` (stage_setting, stage_scope_rule, subject_target_list) | 3.3 |
| `subject`, `visit_actual` | 마스터 |

출력은 `expectation_item` + `stage_status`(초기 상태)입니다.

### 2.2 주 알고리즘

```
function generate_expectations(trial, assumption, config):

    subjects = load_subjects(trial)                     # is_forecast 포함
    for subject in subjects:

        # ── 1. 방문 전개 ─────────────────────────────
        visits = []
        for vs in assumption.visit_schedule:
            if not condition_matches(vs.apply_condition, subject): continue
            if vs.apply_cohort and vs.apply_cohort != subject.cohort: continue

            actual = find_actual_visit(subject, vs.visit_code)
            visits.append(Visit(
                code        = vs.visit_code,
                target_on   = subject.anchor_on + vs.offset_days,
                window_start= target_on - vs.window_before,
                window_end  = target_on + vs.window_after,
                actual_on   = actual.visit_on if actual else None,
                occurred    = actual is not None and actual.status == 'OCCURRED'))

        visits += expand_unscheduled_visits(subject)    # 실적 기반 (2.4)

        # ── 2. 방문 항목 (VISIT 도메인) ───────────────
        for v in visits:
            upsert_item(domain='VISIT', subject=subject, visit=v,
                        match_key=key(subject, v.code, v.seq))

        # ── 3. 활동 항목 (EDC / SAMPLE / IMAGE) ───────
        for v in visits:
            if not visit_expected(subject, v, config):  continue   # 2.3
            for act in assumption.soa_activity.for_visit(v.code):
                if not condition_matches(act.apply_condition, subject): continue
                if act.target_list_id and subject not in target_list(act): continue

                for seq in 1..act.expected_count:
                    item = upsert_item(domain=domain_of(act.activity_type),
                                       subject=subject, visit=v,
                                       site=attribute_site(subject, v),  # 2.9
                                       activity_code=act.activity_code,
                                       repeat_seq=seq,
                                       form_type=act.form_type,
                                       sae_flag=act.sae_flag,
                                       match_key=key(subject, v.code, act.activity_code, seq))
                    init_stage_statuses(item, config)                # 2.5
```

### 2.3 방문이 기대되는지 판정

```
function visit_expected(subject, visit, config):
    if subject.status in ('SCREEN_FAILED',):            return false
    if subject.discont_on and visit.target_on > subject.discont_on:
        rule = config.get('DISCONT_VISIT_RULE')
        if rule == 'ALL_NA':         return false
        if rule == 'FOLLOWUP_ONLY':  return visit.visit_type == 'FOLLOWUP'
        if rule == 'ALL_EXPECTED':   return true
    return true
```

기대되지 않는 방문의 항목은 **생성하되 `stage_status.status = NOT_APPLICABLE`** 로 둡니다. 생성 자체를 건너뛰면 "왜 이 방문이 집계에 없는가"를 드릴다운으로 설명할 수 없습니다.

### 2.4 비예정 방문

SoA로 예측할 수 없으므로 **실적이 들어온 뒤 기대 항목을 생성**합니다 ([개념 04](../concept/04-domain-concepts.md) 1.7).

```
function expand_unscheduled_visits(subject):
    for va in visit_actual.where(subject, unscheduled=true):
        yield Visit(code=va.visit_code, target_on=va.visit_on,
                    window_start=va.visit_on, window_end=va.visit_on,
                    actual_on=va.visit_on, occurred=true, seq=va.visit_seq)
```

윈도우를 실제 방문일로 두므로 **비예정 방문은 윈도우 이탈이 발생하지 않습니다.**

### 2.5 단계 상태 초기화

```
function init_stage_statuses(item, config):
    for sd in stage_def.for_domain(item.domain):
        setting = config.stage_setting[sd.stage_code]
        required = setting.enabled and scope_rule_applies(sd.stage_code, item, config)
        upsert_stage_status(item, sd.stage_code,
                            required=required,
                            status='NOT_APPLICABLE' if not required else 'NOT_DUE')
```

### 2.6 Forecast 피험자 생성

```
function materialize_forecast_subjects(trial, assumption, forecast_to):
    for plan in assumption.enrollment_plan:
        enrolled = count_subjects(plan.site_id, is_forecast=false)
        expected = projected_enrollment(plan, forecast_to)     # 2.7
        for n in 1..max(0, expected - enrolled):
            create_subject(site=plan.site_id, is_forecast=true,
                           anchor_on=projected_anchor(plan, n),
                           subject_code=f'FC-{plan.site_id}-{n}')
```

가상 피험자는 **실적 매칭 대상에서 제외**되고 `DUE`·`PROTOCOL` 기준 집계에도 포함되지 않습니다. `FORECAST` 기준에서만 나타납니다.

### 2.7 등록 예측 (Phase 1 범위)

Phase 1에서는 **선형 예측만** 구현합니다.

```
projected_enrollment(plan, to_date) =
    min(plan.target_n,
        floor(months_between(plan.start_on, to_date) * plan.rate_per_month))
```

실적 기반 추세 외삽은 Phase 2입니다 ([개념 07](../concept/07-prediction-and-analytics.md) 3장).

### 2.8 조건식 평가

`apply_condition`은 [개념 13](../concept/13-trial-configuration.md) 4.11의 제한된 문법입니다.

| 항목 | 사양 |
|---|---|
| 파싱 | 업로드 시점에 AST로 변환해 `jsonb`로 저장. 실행 시 재파싱하지 않음 |
| 허용 필드 | `SEX`, `COHORT`, `STRATA1`~`5`, `COUNTRY`, `SITEID`, `SUBJSTAT`, `ARM`, `VISITNUM` |
| 미지원 문법 | 업로드 거부 (`CHK-CFG-004`) |
| NULL 처리 | 피연산자가 NULL이면 조건은 **false**. `!=` 비교도 false |

마지막 행을 명시하는 이유는 `SEX != 'M'`이 `SEX`가 NULL인 피험자에게 true가 되면 기대 항목이 잘못 생성되기 때문입니다.

### 2.9 사이트 귀속과 이전 (검토 반영)

피험자의 사이트 이전이 발생할 수 있으므로([02](02-data-model.md) 1.4), 항목의 사이트는 **활동이 일어난 곳**으로 정합니다.

```
function attribute_site(subject, visit):
    if visit.occurred:
        return visit_actual.site_id                      # DS02의 SITEID
    h = subject_site_history.covering(visit.target_on)
    return h.site_id if h else subject.site_id
```

#### 이전 감지

```
function detect_transfer(subject, drop_row):
    if drop_row.SITEID == subject.site_id:  return
    close_current_history(subject, valid_to = drop.src_extract_on - 1)
    open_history(subject, site = drop_row.SITEID,
                 valid_from = drop.src_extract_on, source_drop = drop)
    subject.site_id = drop_row.SITEID
    audit(action='UPDATE', entity='Subject', actor_type='ENGINE',
          reason=f'Site transfer detected: {old} → {new}')
    reattribute_pending_items(subject)
```

#### 재귀속 범위

```
function reattribute_pending_items(subject):
    for item in items(subject) where not item.visit.occurred:
        item.site_id, item.country_id = attribute_site(subject, item.visit)
```

**발생한 방문의 항목은 건드리지 않습니다.** Site A에서 수행된 방문의 폼은 이후 이전이 있어도 A의 backlog로 남습니다.

#### 과거 스냅샷

이전은 **과거 `metric_fact`를 바꾸지 않습니다.** 이전 전에 생성된 스냅샷은 그 당시 귀속을 유지하며, 이것이 [개념 08](../concept/08-platform-services.md) 4.2 규칙 3과 일관됩니다. 비교 모드에서 사이트별 수치가 달라 보일 수 있으므로, 이전이 있었던 피험자를 포함하는 비교에는 안내를 표시합니다.

#### 한계

실제 이전일이 아니라 **앱이 인지한 시점**이 기준입니다. 표준 파일에 이전일 컬럼이 없기 때문이며, 미발생 방문의 귀속에 최대 한 전송 주기의 오차가 생길 수 있습니다 (S-02-5).

## 3. ProgressEngine

### 3.1 매칭

```
function match_actuals(trial, drop):
    key_spec = drop.feed.match_key                       # 선언된 매칭 키
    for rec in staging_record.accepted(drop):
        key = normalize_key(rec, key_spec)
        item = find_item(trial, domain_of(drop), key)

        if item is None:
            if is_expected_side(rec):                    # EDC측에 존재
                record_discrepancy('RECEIVED_NOT_IN_EDC', rec)
            else:
                record_discrepancy('AMBIGUOUS_MATCH', rec)
            continue

        if count_items(trial, key) > 1:
            record_discrepancy('AMBIGUOUS_MATCH', rec); continue

        apply_actual(item, rec)
```

#### 매칭 키 정규화

```
normalize_key(rec, spec) = join('|', [upper(trim(rec[f])) for f in spec.fields])
match_key_hash          = sha256(match_key)
```

대소문자와 공백 차이로 매칭이 실패하는 것을 막습니다. 다만 **정규화로 서로 다른 값이 같아지는 경우**(예: `01`과 `1`)는 정규화하지 않습니다. 숫자 패딩 차이는 매핑 단계에서 처리합니다.

### 3.2 단계 상태 판정

[개념 15](../concept/15-metric-specification.md) 4장의 알고리즘입니다. **판정 순서가 결과를 좌우하므로 순서를 고정합니다.**

```
function determine_status(item, stage, as_of, config):

    setting = config.stage_setting[stage]

    # ① 적용 여부
    if not setting.enabled:                       return NOT_APPLICABLE
    if not scope_rule_applies(stage, item):       return NOT_APPLICABLE

    # ② 예외
    if item.waiver[stage]:                        return WAIVED

    # ③ 완료
    if item.completed_flag[stage]:                return DONE

    # ④ 기한
    trigger = resolve_trigger(item, stage, config)
    if trigger is None:                           return NOT_DUE      # 기한 산정 불가

    if setting.grace_days == 'N/A':               return PENDING      # sign
    grace = parse_grace(setting.grace_days, config)
    due   = trigger + grace
    return PENDING if as_of <= due else OVERDUE
```

### 3.3 트리거 해석

```
function resolve_trigger(item, stage, config):
    t = config.stage_setting[stage].due_trigger
    match t:
        'WINDOW_END'        -> item.visit.window_end            # VISIT/occurred
        'VISIT_DATE'        -> item.visit.actual_on
        'ENTRY_DONE'        -> entry_date(item)                 # 3.3.1
        'SIGN_DONE'         -> item.stage['sign'].completed_at?.date
        'ALL_STAGES_DONE'   -> max(completed_at of post_entry stages) if all done else None
        'COLLECTION_DATE'   -> item.attributes['coll_on']
        'IMAGE_DATE'        -> item.attributes['img_on']
        'QUERY_OPENED'      -> issue.opened_on
```

**선행 단계가 미완료면 트리거가 NULL이 되어 `NOT_DUE`가 됩니다.** 입력되지 않은 폼이 SDV backlog로 잡히지 않는 이유가 이것입니다.

#### 3.3.1 반복 폼(LOG)의 입력일

반복 폼은 entry 단계가 `NOT_APPLICABLE`입니다 ([개념 04](../concept/04-domain-concepts.md) 1.7). 그러나 **`ENTERDT`는 후속 단계의 트리거로 사용됩니다.**

```
function entry_date(item):
    if item.form_type == 'LOG':  return item.attributes['entered_on']   # DS03.ENTERDT
    return item.stage['entered'].completed_at?.date
```

분모에서 빠지는 것과 날짜가 없는 것은 다릅니다. LOG 폼의 코딩 기한은 그 폼이 입력된 날부터 계산되어야 합니다.

#### 3.3.2 `sign` 단계의 트리거

`sign`은 유예 기간이 없지만 **트리거는 `ENTRY_DONE`을 사용**합니다. 입력되지 않은 폼을 미서명으로 세면 backlog가 실제보다 크게 잡히기 때문입니다.

```
entry 미완료  → sign = NOT_DUE       (미서명 건수에 포함되지 않음)
entry 완료    → sign = PENDING       (미서명 건수에 포함)
서명 완료     → sign = DONE
```

### 3.4 유예 기간 파싱

```
function parse_grace(value, config):
    if value == 'N/A':        return NONE
    if value == 'DBL_BASED':  return config.DBL_PLANNED_DT - trigger   # 음수 가능
    return int(value)  # 달력일
```

`DBL_BASED`는 기한이 **고정일**이 되는 특수 경우입니다. `due = DBL_PLANNED_DT`로 직접 설정합니다.

### 3.5 Forecast 기한 산출

`FORECAST` 기준을 위해 각 단계에 예측 기한을 함께 계산합니다.

```
function predicted_due(item, stage, config):
    trigger = resolve_trigger(item, stage, config)
    if trigger: return trigger + parse_grace(...)

    # 실적이 없으면 계획에서 추정
    base = item.visit.target_on                      # 예정 방문일
    return base + cumulative_grace(stage, config)    # 선행 단계 유예의 합
```

`cumulative_grace`는 선행 단계 유예 기간의 합입니다. 예를 들어 SDV의 예측 기한은 `예정 방문일 + entry 유예(14) + SDV 유예(60)`입니다.

### 3.6 쿼리 기한

```
function query_due(issue, config):
    g = config.query_grace[issue.issue_owner] ?? config.query_grace['DEFAULT']
    return issue.opened_on + (g.open if issue.state=='OPEN' else g.answered)
```

### 3.7 예외(WAIVED) 전이 (검토 반영)

초안은 해결 불가 이슈가 **항목의 미완료 required 단계 전부**를 예외 처리한다고 했습니다. 검토 결과 **이슈 유형에 따라 차단 수준이 다르다**는 것이 확인되어, 유형 기반 규칙으로 바꿉니다.

#### 차단 범위는 설정에서 온다

```
function blocked_stages(issue, config):
    rule = config.issue_waiver_rule[issue.issue_domain][issue.issue_type]
    if rule is None:                          return []          # 기본값: 예외 처리 없음
    if rule.blocked_stages == ['ALL_INCOMPLETE']:
        return incomplete_required_stages(issue.item)
    return [s for s in rule.blocked_stages
              if is_required(issue.item, s) and not is_done(issue.item, s)]
```

규칙은 `CFG10`으로 시험마다 정의합니다 ([13](../concept/13-trial-configuration.md) 4.11).

| `ISSUE_TYPE` | `BLOCKED_STAGES` | 의미 |
|---|---|---|
| `CODING_UNRESOLVABLE` | `coding` | 코딩만 불가. 입력·SDV·서명은 진행됨 |
| `SOURCE_MISSING` | `sdv` | 원자료 부재로 SDV만 불가 |
| `DATA_UNAVAILABLE` | `ALL_INCOMPLETE` | 데이터 자체가 없어 이후 전부 불가 |
| `HEMOLYSIS` *(Phase 2)* | `analyzed` | 수령은 되었고 분석만 불가 |
| `LOST_IN_TRANSIT` *(Phase 2)* | `ALL_INCOMPLETE` | 검체 자체가 없음 |

표의 값은 예시이며 **실무 확정이 필요**합니다 (S-02-6).

#### 규칙이 없으면 예외 처리하지 않는다

이것이 이 절에서 가장 중요한 결정입니다.

```
rule 없음  →  blocked_stages = []  →  항목은 backlog에 그대로 남음
```

규칙 없는 유형을 `ALL_INCOMPLETE`로 폴백하지 않는 이유는 방향 때문입니다. **예외 처리는 분모를 줄이는 동작**이고, 분모가 조용히 줄면 지표가 이유 없이 좋아 보입니다. 반대로 예외 처리를 못 하면 backlog가 남아 눈에 띕니다. **틀릴 때 눈에 띄는 쪽으로 기울이는 것**이 맞습니다.

규칙이 없는 유형의 해결 불가 이슈는 **"예외 규칙 미정의" 목록**으로 화면에 노출해 설정 보완을 유도합니다.

#### 전이

```
function apply_unresolvable_issue(issue, config):
    if not issue.unresolvable:  return
    if issue.item_id is None:   return

    stages = blocked_stages(issue, config)
    if not stages:
        record_quality_finding('WAIVER_RULE_UNDEFINED', issue)
        return

    for stage in stages:
        set_status(issue.item_id, stage, WAIVED,
                   waiver_type = config.issue_waiver_rule[...].waiver_type or 'ISSUE_BLOCKED',
                   waiver_reason = f'Issue {issue.external_id} ({issue.issue_type})')
        audit(action='UPDATE', reason=waiver_reason, actor_type='ENGINE')
```

**자동 전이는 `unresolvable=true`가 사람에 의해 설정된 뒤에만 일어납니다** ([개념 03](../concept/03-core-concept-model.md) 4.3). 엔진이 스스로 항목을 분모에서 빼지 않습니다.

#### 해제

이슈의 `unresolvable`이 `false`로 되돌아가면 해당 단계의 `WAIVED`를 해제하고 재판정합니다. 해제도 감사 로그에 남습니다.

#### 건별 단계 지정은 Phase 2

사용자가 **이슈 건마다 차단 단계를 직접 고르는 방식**은 Phase 1에서 구현하지 않습니다 (S-03-6). 유형 기반 규칙으로 대부분의 경우가 표현되며, 건별 예외는 운영 부담과 감사 복잡도를 함께 키웁니다.

### 3.8 SCD2 갱신

```
function set_status(item, stage, new_status, ...):
    cur = current_row(item, stage)
    if cur and unchanged(cur, new_status, ...):  return      # 변경 없으면 no-op
    if cur: cur.valid_to = now()
    insert_row(item, stage, new_status, valid_from=now(), valid_to=NULL)
```

`unchanged` 비교가 중요합니다. 이것이 없으면 일 배치마다 전 행이 복제되어 이력이 폭증합니다.

## 4. RollupEngine

### 4.1 집계 순서

```
for basis in (DUE, PROTOCOL, FORECAST):
    for level in (SUBJECT, SITE, COUNTRY, TRIAL):
        aggregate(basis, level)
```

**하위 레벨에서 상위 레벨로 합산**하되, 비율은 항상 원시 카운트에서 재계산합니다 ([개념 15](../concept/15-metric-specification.md) R-N4).

```
rate = completed_count / due_count    if due_count > 0 else NULL
```

### 4.2 기준별 모집단

```
DUE      : status ∈ {PENDING, OVERDUE, DONE}
PROTOCOL : status ∉ {NOT_APPLICABLE, WAIVED}
FORECAST : PROTOCOL 중 predicted_due_on ≤ forecast_to
```

세 경우 모두 `waived_count`는 별도로 집계되어 병기됩니다.

### 4.3 investigator sign 특례

`stage_def.uses_overdue = false`인 단계는 **rate를 계산하지 않습니다.**

```
if not stage_def.uses_overdue:
    emit_fact(metric='edc.sign.pending_all',
              due_count=NULL, rate=NULL,
              backlog_count=count(required AND NOT completed))
    emit_fact(metric='edc.sign.pending_sae', ... filter sae_flag=true)
    return
```

`due_count`와 `rate`를 NULL로 두는 것이 중요합니다. 0으로 두면 화면에서 0%로 표시됩니다.

### 4.4 쿼리 집계

`group_key`에 `issue_owner`를 넣어 소유자별 분해를 저장합니다. 전체 합계 행은 `group_key = NULL`로 별도 생성합니다.

### 4.5 지표 on/off

```
if not config.metric_switch[metric_code].enabled:
    skip                      # 행 자체를 만들지 않음
```

**0이나 NULL 행을 만들지 않고 아예 생성하지 않습니다.** 화면은 `metric_fact`에 없는 지표를 표시하지 않으므로, 이것만으로 [개념 04](../concept/04-domain-concepts.md) 1.4가 구현됩니다.

## 5. 지표 산출 대상 (Phase 1)

| metric_code | 단계 | rate | 비고 |
|---|---|---|---|
| `edc.entry.*` | `entered` | O | |
| `edc.sdv.*` | `sdv` | O | partial SDV 범위 적용 |
| `edc.review.*` | `review` | O | 시험별 on/off |
| `edc.coding.*` | `coding` | O | |
| `edc.sign.pending_all` | `sign` | **X** | 건수만 |
| `edc.sign.pending_sae` | `sign` | **X** | 건수만 |
| `edc.freeze.*` | `freeze` | O | |
| `edc.lock.*` | `lock` | O | |
| `edc.waived.count` | 전 단계 | X | `waiver_type`별 분해 |
| `query.*` | — | X | 상태별 건수, overdue, aging |
| `rtsm.visit.*` | `occurred` | O | 윈도우 이탈 포함 |
| `rtsm.subject.count` | — | X | 상태별 |
| `quality.*` | — | X | 업로드 품질 |

각 `*`는 `due`, `backlog`, `completed`, `rate`, `overdue`, `aging_median`, `aging_p90`입니다.

## 6. 성능 설계

| 요구 | 설계 |
|---|---|
| N-1 화면 2초 | 화면은 `metric_fact`만 조회. 원본 집계 금지 |
| N-2 드릴다운 1초 | `stage_status` 현재 행 부분 인덱스 + 커서 페이징 |
| N-4 재생성 15분 | 항목 생성은 `COPY` 벌크, 상태 판정은 set 기반 UPDATE |

### 6.1 집계 쿼리 형태

```sql
INSERT INTO metric_fact (...)
SELECT :snapshot_id, 'edc.entry.rate', :ver, 'DUE', 'SITE',
       i.country_id, i.site_id, NULL, 'EDC', 'entered', NULL,
       count(*) FILTER (WHERE s.status IN ('PENDING','OVERDUE','DONE')),
       count(*) FILTER (WHERE s.status = 'DONE'),
       ...
FROM stage_status s
JOIN expectation_item i ON i.id = s.item_id AND i.trial_id = s.trial_id
WHERE s.trial_id = :trial AND s.valid_to IS NULL
  AND s.stage_code = 'entered' AND i.origin = 'CONFIRMED'
GROUP BY i.country_id, i.site_id;
```

항목별 루프를 돌지 않고 **단일 집계 쿼리**로 처리합니다. Python 루프는 항목 생성에만 씁니다.

## 7. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-03-1 | 3.5 `cumulative_grace`가 병행 단계에서 타당한가 | 병행 단계는 `entered` 유예 + 자기 유예로 계산 |
| S-03-2 | 증분 실행의 영향 범위 판정 정확도 | Phase 1은 **피험자 단위 재계산**으로 안전하게 시작 |
| S-03-3 | 일 배치 실행 시각 | 시험 기준 시간대 06:00 |
| S-03-4 | 가상 피험자 코드 체계 (`FC-`) 충돌 가능성 | 실제 피험자 코드와 겹치면 업로드 시 거부 |
| S-03-5 | 기준일(anchor) 없는 피험자 처리 | **항목 생성하지 않음.** 별도 "기준일 없음" 건수로 집계 (golden E19) |
| ~~S-03-6~~ | ~~`blocked_stages`를 건별 단계 지정 방식으로 확장~~ | **확정 — Phase 2 이후.** 유형 기반 규칙(3.7)으로 Phase 1 대응 |
| S-03-7 | `CFG10` 규칙 미정의 시 예외 처리하지 않는 방침에 동의하는가 | **동의 권고** (3.7) |
| S-03-8 | 사이트 이전 시 비교 모드 안내 문구 | 이전 포함 비교에 배너 표시 (2.9) |
