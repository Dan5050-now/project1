# 02. 물리 데이터 모델

대상 DBMS는 **PostgreSQL 16**입니다. 타입 표기는 PostgreSQL 기준이며, Django 모델로 옮길 때의 대응은 각 절 끝에 둡니다.

## 1. 모델링 결정

사양 단계에서 확정해야 했던 네 가지입니다.

### 1.1 분모 3종을 항목 수준에서 복제하지 않는다

[개념 03](../concept/03-core-concept-model.md) 3.4는 Due / Protocol / Forecast 세 기준을 모두 저장한다고 했습니다. **이것은 집계 수준(`metric_fact`)에서만 3배가 되고, 항목 수준에서는 1벌만 저장합니다.**

```
expectation_item        1벌   — 프로토콜상 생성 가능한 모든 항목
  └ stage_status        1벌   — 단계별 상태 + due_date + predicted_due_date
        │
        ├─ PROTOCOL  = status ≠ NOT_APPLICABLE, WAIVED 인 전체
        ├─ DUE       = status ∈ {PENDING, OVERDUE, DONE}
        └─ FORECAST  = PROTOCOL 중 predicted_due_date ≤ 기준일
```

세 기준이 **같은 행의 다른 해석**이므로 복제가 불필요합니다. `predicted_due_date` 한 컬럼이 Forecast 기준을 가능하게 합니다.

### 1.2 단계 상태는 SCD2로 이력을 가진다

스냅샷 시점의 화면을 재현하려면([개념 08](../concept/08-platform-services.md) 4.1) 항목 수준 이력이 필요합니다. `stage_status`에 `valid_from` / `valid_to`를 두고, 변경 시 기존 행을 닫고 새 행을 추가합니다.

비용은 행 수 증가입니다. 시험당 60만 항목 × 평균 3회 상태 변경 = 약 180만 행. PostgreSQL이 감당하는 규모이며, 현재 상태 조회는 부분 인덱스로 처리합니다.

대안(데이터를 재적재해 재계산)은 채택하지 않았습니다. 재현에 수십 분이 걸리면 비교 모드([개념 05](../concept/05-information-architecture.md) 4.2)가 사실상 못 쓰게 됩니다.

### 1.3 파티셔닝은 `trial_id` 해시로 한다

대용량 테이블 3개(`expectation_item`, `stage_status`, `metric_fact`)를 `trial_id` HASH 16 파티션으로 나눕니다. 시험 간 데이터량 편차가 크므로 LIST보다 HASH가 균등합니다.

시간 기준 파티셔닝은 하지 않습니다. 조회가 항상 시험 단위로 좁혀지므로 실익이 적고, 파티션 수만 늘어납니다.

### 1.4 도메인별 확장 속성은 JSONB로 둔다

`expectation_item.attributes`(JSONB)에 도메인 고유 속성을 담습니다. **자주 필터링하는 속성은 물리 컬럼으로 승격**합니다 ([개념 06](../concept/06-logical-data-model.md) 3.1). Phase 1에서 승격 대상은 `form_type`, `sae_flag`입니다.

## 2. 마스터

### 2.1 `trial`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | bigserial | PK | |
| `study_id` | varchar(50) | UNIQUE NOT NULL | 프로토콜 번호 |
| `title` | varchar(500) | | |
| `phase` | varchar(20) | | |
| `status` | varchar(20) | NOT NULL | `SETUP`/`ACTIVE`/`CLOSED` |
| `blinded` | boolean | NOT NULL DEFAULT true | 마스킹 적용 여부 |
| `timezone` | varchar(50) | NOT NULL DEFAULT 'UTC' | |
| `created_at` / `updated_at` | timestamptz | NOT NULL | |

### 2.2 `country` / `site`

| 테이블 | 주요 컬럼 |
|---|---|
| `country` | `id`, `trial_id` FK, `country_code` char(2), `name`. UNIQUE(`trial_id`, `country_code`) |
| `site` | `id`, `trial_id` FK, `country_id` FK, `site_code` varchar(50), `name`, `status`, `activated_on` date. UNIQUE(`trial_id`, `site_code`) |

### 2.3 `subject`

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `id` | bigserial | PK | |
| `trial_id` | bigint | FK NOT NULL | |
| `site_id` | bigint | FK NOT NULL | |
| `subject_code` | varchar(50) | NOT NULL | `DS01.SUBJID` |
| `status` | varchar(30) | NOT NULL | `CFG09` 코드 |
| `screened_on`, `enrolled_on`, `randomized_on` | date | | |
| `anchor_on` | date | | 방문 윈도우 기준일. `CFG01.ANCHOR_RULE`로 결정 |
| `last_visit_on` | date | | |
| `discont_on` | date | | |
| `discont_reason` | varchar(200) | | |
| `cohort` | varchar(50) | | 조건식 평가에 사용 |
| `sex` | varchar(10) | | 조건식 평가에 사용 |
| `strata` | jsonb | | **마스킹 대상** |
| `arm` | varchar(50) | | **마스킹 대상** |
| `is_forecast` | boolean | NOT NULL DEFAULT false | 등록 계획에서 생성된 가상 피험자 |

UNIQUE(`trial_id`, `subject_code`). INDEX(`trial_id`, `site_id`, `status`).

`is_forecast`가 Forecast 기준의 출발점입니다. 가상 피험자는 **실적 매칭 대상에서 제외**되며 화면에서 별도 표시됩니다.

### 2.4 `visit_actual`

실제 발생한 방문입니다. 예정 방문은 `expectation_item`으로 생성되므로 여기 두지 않습니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | bigserial | |
| `trial_id`, `subject_id` | bigint FK | |
| `visit_code` | varchar(50) | `CFG02.VISITID`와 대조 |
| `visit_on` | date | 실제 방문일 |
| `status` | varchar(20) | `OCCURRED`/`NOT_DONE`/`CANCELLED` |
| `unscheduled` | boolean | |
| `visit_seq` | int | 비예정 방문 순번 |
| `source_drop_id` | bigint FK | 근거 Drop |

UNIQUE(`subject_id`, `visit_code`, `visit_seq`).

### 2.5 `activity_def` / `stage_def`

| 테이블 | 설명 |
|---|---|
| `activity_def` | `trial_id`, `activity_type`(`FORM`/`SAMPLE`/`IMAGE`), `activity_code`, `name`, `form_type`(`STANDARD`/`LOG`), `sae_flag` |
| `stage_def` | `domain`, `stage_code`, `seq`, `predecessor_code`, `parallel_group`, `uses_overdue` boolean |

`stage_def`는 **시험 무관 전역 마스터**입니다. EDC의 병행 구조가 여기 표현됩니다.

| domain | stage_code | predecessor | parallel_group | uses_overdue |
|---|---|---|---|---|
| EDC | `entered` | — | — | true |
| EDC | `sdv` | `entered` | `post_entry` | true |
| EDC | `review` | `entered` | `post_entry` | true |
| EDC | `coding` | `entered` | `post_entry` | true |
| EDC | `freeze` | `entered` | `post_entry` | true |
| EDC | `sign` | `entered` | `post_entry` | **false** |
| EDC | `lock` | `post_entry` 전체 | — | true |
| VISIT | `occurred` | — | — | true |

`sign`의 `uses_overdue = false`가 [개념 04](../concept/04-domain-concepts.md) 1.5의 특수 처리를 담습니다.

### 2.6 `code_list`

`trial_id`, `list_type`, `code`, `label`, `sort_order`, `active`. UNIQUE(`trial_id`, `list_type`, `code`).

## 3. 가정과 설정

### 3.1 `assumption_set` / `trial_config`

둘 다 같은 구조의 버전 헤더입니다.

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | bigserial | |
| `trial_id` | bigint FK | |
| `version` | int | 시험 내 증가 |
| `state` | varchar(20) | `DRAFT`/`ACTIVE`/`SUPERSEDED` |
| `effective_from` | date | |
| `created_by`, `created_at` | | |
| `change_reason` | text | **필수** |

UNIQUE(`trial_id`, `version`). 시험당 `state='ACTIVE'`인 행은 최대 1개 (부분 UNIQUE 인덱스).

### 3.2 가정 하위 테이블

| 테이블 | 주요 컬럼 | 원본 |
|---|---|---|
| `visit_schedule` | `assumption_set_id`, `visit_code`, `visit_name`, `visit_num`, `visit_type`, `offset_days`, `window_before`, `window_after`, `apply_cohort`, `apply_condition` | `CFG02` |
| `soa_activity` | `assumption_set_id`, `visit_code`, `activity_type`, `activity_code`, `expected_count`, `form_type`, `sae_flag`, `apply_condition`, `target_list_id` | `CFG03` |
| `enrollment_plan` | `assumption_set_id`, `site_id`, `target_n`, `start_on`, `rate_per_month` | — |

### 3.3 설정 하위 테이블

| 테이블 | 주요 컬럼 | 원본 |
|---|---|---|
| `stage_setting` | `trial_config_id`, `domain`, `stage_code`, `enabled`, `due_trigger`, `grace_days` varchar(20) | `CFG04` |
| `query_grace_setting` | `trial_config_id`, `query_owner`, `open_grace_days`, `answered_grace_days` | `CFG05` |
| `stage_scope_rule` | `trial_config_id`, `stage_code`, `scope_type`, `scope_value`, `apply_condition` | `CFG06` |
| `subject_target_list` | `trial_config_id`, `list_name`, `list_desc` | `CFG07` |
| `subject_target_member` | `list_id`, `subject_code` | `CFG07` |
| `metric_switch` | `trial_config_id`, `metric_code`, `enabled`, `reason` | `CFG08` |

`stage_setting.grace_days`를 varchar로 둔 것은 `N/A`와 `DBL_BASED` 특수값 때문입니다 ([개념 13](../concept/13-trial-configuration.md) 4.4). 파싱은 엔진에서 하며, 업로드 시 형식을 검증합니다.

## 4. 유입

### 4.1 `source_system` / `feed` / `source_template` / `mapping_profile`

| 테이블 | 주요 컬럼 |
|---|---|
| `source_system` | `trial_id`, `name`, `kind`(`EDC`/`RTSM`/`LAB`/`IMAGING`/`MANUAL`), `ingestion_mode`(`FILE`/`API`) |
| `source_template` | `dataset_code`, `version`, `column_spec` jsonb, `match_key_spec` jsonb — **시험 무관 전역** |
| `feed` | `trial_id`, `source_system_id`, `dataset_code`, `match_key` jsonb, `trust_level` |
| `mapping_profile` | `feed_id`, `version`, `column_map` jsonb, `code_map` jsonb, `state` |

`feed.match_key`가 [개념 03](../concept/03-core-concept-model.md) 5.2의 매칭 키 선언입니다. 권고 입도에 미달하면 `trust_level='CAUTION'`으로 설정되고 화면에 경고가 표시됩니다.

### 4.2 `data_drop`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | bigserial | |
| `trial_id`, `feed_id` | bigint FK | |
| `filename` | varchar(500) | |
| `file_hash` | char(64) | SHA-256. 중복 감지 |
| `template_version`, `mapping_version` | varchar(20) | 해석에 사용된 버전 |
| `src_system`, `src_file_ref` | varchar | 출처 메타데이터 |
| `src_extract_on` | date | **vendor 원본 추출 기준일** |
| `prepared_by`, `prepared_on` | varchar/date | 미기입 시 업로더·업로드일로 자동 기록 |
| `transfer_type` | varchar(20) | `CUMULATIVE`/`INCREMENTAL` |
| `period_from`, `period_to` | date | 증분 시 필수 |
| `declared_row_count` | int | Header의 `ROW_COUNT` |
| `rows_total`, `rows_accepted`, `rows_rejected`, `rows_warned` | int | |
| `state` | varchar(20) | `UPLOADED`/`VALIDATED`/`PROMOTED`/`REJECTED` |
| `uploaded_by`, `uploaded_at` | | |

INDEX(`trial_id`, `feed_id`, `uploaded_at` DESC). UNIQUE(`feed_id`, `file_hash`) — 동일 파일 재업로드 차단(경고 후 강제 허용 가능).

### 4.3 `staging_record` / `validation_finding`

| 테이블 | 주요 컬럼 |
|---|---|
| `staging_record` | `drop_id`, `source_row_no`, `raw` jsonb, `normalized` jsonb, `state`(`ACCEPTED`/`REJECTED`), `match_key_hash` |
| `validation_finding` | `drop_id`, `check_code`, `severity`(`REJECT`/`WARN`), `source_row_no`, `field`, `message` |

`staging_record.raw`에 **원본 행을 그대로 보존**합니다. 매핑이나 template이 바뀐 뒤에도 원본 해석이 가능해야 하기 때문입니다.

### 4.4 `snapshot`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id` | bigserial | |
| `trial_id` | bigint FK | |
| `as_of` | timestamptz | 계산 기준 시각 |
| `label` | varchar(200) | |
| `is_official` | boolean | 공식 스냅샷 여부 |
| `assumption_set_id`, `trial_config_id` | bigint FK | 계산에 사용된 버전 |
| `metric_def_version` | int | 지표 정의 버전 |
| `engine_run_id` | bigint FK | 생성한 엔진 실행 |
| `state` | varchar(20) | `BUILDING`/`READY`/`FAILED` |

INDEX(`trial_id`, `as_of` DESC), 부분 INDEX(`trial_id`) WHERE `is_official`.

## 5. 추적 (핵심)

### 5.1 `expectation_item`

```sql
CREATE TABLE expectation_item (
    id              bigserial,
    trial_id        bigint      NOT NULL,
    domain          varchar(10) NOT NULL,   -- EDC | VISIT | SAMPLE | IMAGE
    subject_id      bigint      NOT NULL,
    site_id         bigint      NOT NULL,
    country_id      bigint      NOT NULL,   -- 롤업 비정규화
    visit_code      varchar(50),
    visit_num       numeric(6,2),
    activity_code   varchar(50),
    repeat_seq      int         NOT NULL DEFAULT 1,
    match_key       varchar(300) NOT NULL,  -- 정규화된 매칭 키 문자열
    match_key_hash  char(64)     NOT NULL,
    origin          varchar(10)  NOT NULL,  -- CONFIRMED | FORECAST
    form_type       varchar(10),            -- STANDARD | LOG  (승격 컬럼)
    sae_flag        boolean      NOT NULL DEFAULT false,
    attributes      jsonb        NOT NULL DEFAULT '{}',
    assumption_set_id bigint     NOT NULL,
    trial_config_id   bigint     NOT NULL,
    created_at      timestamptz  NOT NULL,
    PRIMARY KEY (trial_id, id)
) PARTITION BY HASH (trial_id);
```

| 인덱스 | 목적 |
|---|---|
| UNIQUE(`trial_id`, `domain`, `match_key_hash`, `assumption_set_id`, `trial_config_id`) | 중복 생성 방지 |
| (`trial_id`, `site_id`, `domain`) | 사이트 롤업 |
| (`trial_id`, `subject_id`) | Subject 360 |

`country_id`와 `site_id`를 비정규화한 것은 롤업 조인을 없애기 위함입니다. 피험자의 사이트 이전은 발생하지 않는다고 전제합니다.

### 5.2 `stage_status`

```sql
CREATE TABLE stage_status (
    id                bigserial,
    trial_id          bigint      NOT NULL,
    item_id           bigint      NOT NULL,
    stage_code        varchar(20) NOT NULL,
    required          boolean     NOT NULL,
    trigger_on        date,
    due_on            date,                    -- grace='N/A'이면 NULL
    predicted_due_on  date,                    -- FORECAST 기준용
    completed_at      timestamptz,
    status            varchar(20) NOT NULL,    -- NOT_APPLICABLE|NOT_DUE|PENDING|OVERDUE|DONE|WAIVED
    waiver_type       varchar(30),             -- ISSUE_BLOCKED|PROTOCOL_EXEMPT|OPERATIONAL_WAIVER
    waiver_reason     text,
    source_drop_id    bigint,
    valid_from        timestamptz NOT NULL,
    valid_to          timestamptz,             -- NULL이면 현재 행
    PRIMARY KEY (trial_id, id)
) PARTITION BY HASH (trial_id);
```

| 인덱스 | 목적 |
|---|---|
| UNIQUE(`trial_id`, `item_id`, `stage_code`) WHERE `valid_to` IS NULL | 현재 행 유일성 |
| (`trial_id`, `stage_code`, `status`) WHERE `valid_to` IS NULL | 집계 |
| (`trial_id`, `item_id`) | 드릴다운 |
| (`trial_id`, `valid_from`, `valid_to`) | 시점 조회 |

**CHECK 제약**

```sql
CHECK (status <> 'WAIVED' OR waiver_reason IS NOT NULL)
CHECK (status NOT IN ('PENDING','OVERDUE','DONE') OR required)
```

첫 번째가 [개념 03](../concept/03-core-concept-model.md) 3.3의 "예외에는 사유 필수"를 DB 수준에서 강제합니다.

### 5.3 `issue_object`

| 컬럼 | 타입 | 설명 |
|---|---|---|
| `id`, `trial_id` | | |
| `issue_domain` | varchar(10) | `QUERY`/`SAMPLE`/`IMAGE` |
| `external_id` | varchar(100) | `DS04.QUERYID` |
| `subject_id`, `site_id`, `country_id` | bigint | 롤업 비정규화 |
| `item_id` | bigint | 연결된 항목 (있으면) |
| `issue_owner` | varchar(20) | `DM`/`CRA`/`MM`/`PV` |
| `issue_group`, `issue_type` | varchar(50) | 분해 축 |
| `state` | varchar(20) | `OPEN`/`ANSWERED`/`CLOSED`/`CANCELLED` |
| `opened_on`, `answered_on`, `closed_on` | date | |
| `due_on` | date | 소유자별 유예 적용 |
| `unresolvable` | boolean | true면 대상 항목 `WAIVED` 전이 |
| `valid_from`, `valid_to` | timestamptz | SCD2 |

UNIQUE(`trial_id`, `issue_domain`, `external_id`) WHERE `valid_to` IS NULL.

## 6. 분석

### 6.1 `metric_fact`

```sql
CREATE TABLE metric_fact (
    id                  bigserial,
    trial_id            bigint      NOT NULL,
    snapshot_id         bigint      NOT NULL,
    metric_code         varchar(50) NOT NULL,
    metric_def_version  int         NOT NULL,
    basis               varchar(10) NOT NULL,   -- DUE | PROTOCOL | FORECAST
    forecast_to         date,                   -- basis=FORECAST일 때
    level               varchar(10) NOT NULL,   -- TRIAL|COUNTRY|SITE|SUBJECT
    country_id          bigint,
    site_id             bigint,
    subject_id          bigint,
    domain              varchar(10),
    stage_code          varchar(20),
    group_key           varchar(100),           -- query owner 등 분해 축
    due_count           int NOT NULL DEFAULT 0,
    completed_count     int NOT NULL DEFAULT 0,
    backlog_count       int NOT NULL DEFAULT 0,
    overdue_count       int NOT NULL DEFAULT 0,
    waived_count        int NOT NULL DEFAULT 0,
    rate                numeric(6,4),           -- NULL = N/A
    aging_median        numeric(8,2),
    aging_p90           numeric(8,2),
    PRIMARY KEY (trial_id, id)
) PARTITION BY HASH (trial_id);
```

UNIQUE(`trial_id`, `snapshot_id`, `metric_code`, `basis`, `level`, COALESCE(`country_id`,0), COALESCE(`site_id`,0), COALESCE(`subject_id`,0), COALESCE(`stage_code`,''), COALESCE(`group_key`,'')).

`rate`가 NULL이면 `N/A`입니다. **0과 NULL을 구분하는 것이 [개념 15](../concept/15-metric-specification.md) R-N1의 구현**입니다.

### 6.2 `metric_definition`

`metric_code`, `version`, `display_name_ko`, `display_name_en`, `definition_text`, `numerator_expr`, `denominator_expr`, `population_filter`, `exclusion_rules` jsonb, `due_rule_ref`, `unit`, `rounding`, `null_policy`, `applicable_levels` jsonb, `threshold_warn`, `threshold_alert`, `effective_from`, `effective_to`.

UNIQUE(`metric_code`, `version`).

## 7. 플랫폼

### 7.1 권한

| 테이블 | 주요 컬럼 |
|---|---|
| `app_user` | Django `auth_user` 확장. `employee_id`, `active`, `last_login_at` |
| `role` | `name`, `description`, `is_template` |
| `role_permission` | `role_id`, `module_code`, `access_level`(`NONE`/`READ`/`WRITE`), `unblinded` boolean |
| `user_role` | `user_id`, `role_id`, `trial_id`, `data_scope_id` |
| `data_scope` | `country_ids` jsonb, `site_ids` jsonb |

`user_role`이 `trial_id`를 가지므로 **한 사용자가 시험마다 다른 역할**을 가질 수 있습니다 ([개념 08](../concept/08-platform-services.md) 2.3).

### 7.2 `audit_log`

```sql
CREATE TABLE audit_log (
    id            bigserial PRIMARY KEY,
    occurred_at   timestamptz NOT NULL DEFAULT now(),
    trial_id      bigint,
    actor_type    varchar(10) NOT NULL,   -- HUMAN | AI | ENGINE
    actor_user_id bigint,
    actor_agent_id bigint,
    actor_engine  varchar(50),
    ai_run_id     bigint,
    initiated_by  bigint,
    action        varchar(20) NOT NULL,
    entity_type   varchar(50) NOT NULL,
    entity_id     varchar(100),
    old_value     jsonb,
    new_value     jsonb,
    reason        text,
    source        varchar(20) NOT NULL,   -- UI|IMPORT|API|ENGINE|AI
    approved_by   bigint,
    approved_at   timestamptz
);
```

**append-only 강제.** 애플리케이션 DB 롤에 `UPDATE`, `DELETE` 권한을 부여하지 않습니다.

```sql
REVOKE UPDATE, DELETE ON audit_log FROM app_role;
```

CHECK 제약으로 행위자 일관성을 강제합니다.

```sql
CHECK (
  (actor_type='HUMAN'  AND actor_user_id  IS NOT NULL) OR
  (actor_type='AI'     AND actor_agent_id IS NOT NULL) OR
  (actor_type='ENGINE' AND actor_engine   IS NOT NULL)
)
```

INDEX(`trial_id`, `occurred_at` DESC), (`entity_type`, `entity_id`), (`actor_type`, `occurred_at` DESC).

### 7.3 `engine_run`

| 컬럼 | 설명 |
|---|---|
| `id`, `trial_id` | |
| `engine` | `EXPECTATION`/`PROGRESS`/`ROLLUP` |
| `trigger` | `UPLOAD`/`CONFIG_CHANGE`/`MANUAL`/`SCHEDULE` |
| `assumption_set_id`, `trial_config_id`, `snapshot_id` | 사용한 좌표 |
| `started_at`, `finished_at` | |
| `items_created`, `items_updated`, `statuses_changed` | 영향 범위 |
| `state` | `RUNNING`/`SUCCEEDED`/`FAILED` |
| `error_detail` | text |

엔진 실행은 **행 단위가 아니라 실행 단위로** 감사 로그를 남깁니다 ([개념 08](../concept/08-platform-services.md) 3.3).

### 7.4 `saved_view`

`user_id`, `trial_id`, `name`, `module_code`, `filters` jsonb, `shared` boolean.

## 8. Django 매핑 요약

| 사양 | Django |
|---|---|
| 파티션 테이블 | `Meta.managed = False` + 수동 마이그레이션 (`RunSQL`) |
| SCD2 | 커스텀 매니저 (`current()` / `as_of(ts)`) |
| 부분 UNIQUE 인덱스 | `UniqueConstraint(condition=Q(valid_to__isnull=True))` |
| CHECK 제약 | `CheckConstraint` |
| JSONB | `models.JSONField` |
| append-only | DB 권한 + `save()`/`delete()` 오버라이드로 차단 |

## 9. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-02-1 | 파티션 수 16이 적절한가 | 시험 수 20개 미만이면 충분. 재파티셔닝 절차 필요 |
| S-02-2 | `stage_status` SCD2의 보존 기간 | 시험 종료 후 정책에 따름 (DP-08-6) |
| S-02-3 | 피험자 사이트 이전을 허용할 것인가 | **불허 전제.** 허용 시 비정규화 컬럼 갱신 로직 필요 |
| S-02-4 | `match_key` 문자열 길이 300이 충분한가 | 샘플 도메인 추가 시 재검토 |
