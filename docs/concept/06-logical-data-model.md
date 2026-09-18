# 06. 논리 데이터 모델

이 문서는 개념 수준의 데이터 모델입니다. 물리 스키마(테이블 정의, 인덱스, 제약)는 사양 단계에서 확정합니다.

*개정 이력: v2 (검토 반영 — 상태 통합, 단계 그래프, TrialConfig, 표준 template, AI 행위자 구분)*

## 1. 모델의 층 구조

```
┌─────────────────────────────────────────────────────────┐
│ ⑤ Platform      User, Role, Permission, AuditLog,       │
│                 MetricDefinition, SavedView,             │
│                 AIAgent, AITask, AITaskRun               │
├─────────────────────────────────────────────────────────┤
│ ④ Analytics     MetricFact (집계 결과, 읽기 전용)        │
├─────────────────────────────────────────────────────────┤
│ ③ Tracking      ExpectationItem, StageStatus,            │
│                 IssueObject, Discrepancy,                │
│                 SDVVisit, Milestone, TimelineTask        │
├─────────────────────────────────────────────────────────┤
│ ② Assumption    AssumptionSet, SoAActivity,              │
│                 VisitSchedule,                           │
│                 TrialConfig, StageSetting,               │
│                 StageScopeRule, SubjectTargetList        │
├─────────────────────────────────────────────────────────┤
│ ① Master        Trial, Country, Site, Subject, Visit,    │
│                 ActivityDef, StageDef, Lab, CodeList     │
├─────────────────────────────────────────────────────────┤
│ ⓪ Ingestion     SourceSystem, Feed, SourceTemplate,      │
│                 MappingProfile, DataDrop,                │
│                 StagingRecord, ValidationFinding,        │
│                 Snapshot                                 │
└─────────────────────────────────────────────────────────┘
```

아래에서 위로 의존합니다. 층을 넘는 역방향 의존은 두지 않습니다.

## 2. 개념 ERD

### 2.1 마스터와 가정

```mermaid
erDiagram
    TRIAL ||--o{ COUNTRY : has
    COUNTRY ||--o{ SITE : has
    SITE ||--o{ SUBJECT : enrolls
    SUBJECT ||--o{ VISIT : attends
    TRIAL ||--o{ ASSUMPTION_SET : "versioned"
    TRIAL ||--o{ TRIAL_CONFIG : "versioned"
    ASSUMPTION_SET ||--o{ VISIT_SCHEDULE : defines
    ASSUMPTION_SET ||--o{ SOA_ACTIVITY : defines
    ASSUMPTION_SET ||--o{ ENROLLMENT_PLAN : defines
    TRIAL_CONFIG ||--o{ STAGE_SETTING : defines
    TRIAL_CONFIG ||--o{ STAGE_SCOPE_RULE : defines
    TRIAL_CONFIG ||--o{ QUERY_GRACE_SETTING : defines
    TRIAL_CONFIG ||--o{ SUBJECT_TARGET_LIST : defines
    TRIAL_CONFIG ||--o{ METRIC_SWITCH : defines
    VISIT_SCHEDULE ||--o{ SOA_ACTIVITY : "at visit"
    SOA_ACTIVITY }o--|| ACTIVITY_DEF : references
    SOA_ACTIVITY }o--o| SUBJECT_TARGET_LIST : "applies to"

    TRIAL {
        id pk
        string protocol_no
        string phase
        string status
    }
    SUBJECT {
        id pk
        string subject_no
        date enrolled_date
        date randomized_date
        string current_status
        json stratification "마스킹 대상"
    }
    VISIT {
        id pk
        string visit_name
        date target_date
        date window_start
        date window_end
        date actual_date
        int deviation_days
        string deviation_type "under|in|over|missed"
    }
    SOA_ACTIVITY {
        id pk
        string activity_type "FORM|SAMPLE|IMAGE"
        string activity_code "FORMID|KITTYPE|MODALITY"
        int expected_count
        boolean sae_flag
        json condition "코호트·층화 조건식"
        id target_list_id fk "지정 시 해당 피험자만"
    }
    STAGE_SETTING {
        id pk
        string domain
        string stage_code
        boolean enabled "false면 화면·집계·export에서 제외"
        string due_trigger
        string grace_days "정수 | N/A | DBL_BASED"
    }
    QUERY_GRACE_SETTING {
        id pk
        string query_owner "DM|CRA|MM|PV|DEFAULT"
        int open_grace_days
        int answered_grace_days
    }
    SUBJECT_TARGET_LIST {
        id pk
        string list_name
        string list_desc
        json subject_ids
    }
```

`TRIAL_CONFIG`가 별도 버전 단위로 분리된 것이 검토 반영 사항입니다. 유예 기간이나 단계 on/off는 시험 설계(SoA, 방문 스케줄)와 **변경 주기가 다르고 변경 주체도 다릅니다.** 하나로 묶으면 유예 기간 하나 바꾸려고 SoA 전체 버전이 올라갑니다.

### 2.2 추적 계층 — 모델의 심장

```mermaid
erDiagram
    EXPECTATION_ITEM ||--o{ STAGE_STATUS : "단계별"
    EXPECTATION_ITEM }o--|| SUBJECT : belongs
    EXPECTATION_ITEM }o--o| VISIT : "at"
    EXPECTATION_ITEM }o--|| ACTIVITY_DEF : "of type"
    EXPECTATION_ITEM ||--o{ ISSUE_OBJECT : "has"
    EXPECTATION_ITEM ||--o{ DISCREPANCY : "has"
    STAGE_STATUS }o--|| STAGE_DEF : "of"
    STAGE_DEF }o--o| STAGE_DEF : "predecessor"
    ISSUE_OBJECT }o--o| STAGE_STATUS : "waives"
    DATA_DROP ||--o{ EXPECTATION_ITEM : "actual 근거"

    EXPECTATION_ITEM {
        id pk
        string domain "EDC|SAMPLE|IMAGE|VISIT"
        json match_key "매칭 키 (입도 선언에 따름)"
        string expectation_basis "PROTOCOL|DUE|FORECAST 판정"
        id assumption_set_id fk
        id trial_config_id fk
        id snapshot_id fk
    }
    STAGE_STATUS {
        id pk
        string stage_code "entered|sdv|review|coding|sign|freeze|lock|..."
        boolean required
        date trigger_date
        date due_date "grace N/A 이면 null"
        datetime completed_at
        string status "NOT_APPLICABLE|NOT_DUE|PENDING|OVERDUE|DONE|WAIVED"
        string waiver_type "ISSUE_BLOCKED|PROTOCOL_EXEMPT|OPERATIONAL_WAIVER"
        string waiver_reason "필수"
        int aging_days
    }
    STAGE_DEF {
        id pk
        string domain
        string stage_code
        id predecessor_id fk "null이면 병행 그룹의 시작"
        string parallel_group "같은 값끼리 병행"
        boolean uses_overdue "false면 OVERDUE 미사용 (sign)"
    }
    ISSUE_OBJECT {
        id pk
        string issue_domain "QUERY|SAMPLE|IMAGE"
        string issue_type
        string issue_owner "DM|CRA|MM|PV"
        string issue_group "query group 축"
        string state "OPEN|ANSWERED|CLOSED|CANCELLED"
        date opened_at
        date due_date "owner별 유예 적용"
        boolean unresolvable "true면 대상 항목 WAIVED 전이"
        string referral_to
        date answered_at
        date closed_at
    }
    DISCREPANCY {
        id pk
        string kind "EDC_Y_NOT_RECEIVED|RECEIVED_NOT_IN_EDC|MATCHED_DISCREPANT|AMBIGUOUS_MATCH"
        string segment "CENTRAL|BIOANALYTICS|BICR|EDC_RTSM"
        string resolution_state
        id assignee fk
    }
```

`STAGE_DEF`의 `predecessor_id`와 `parallel_group`이 EDC의 병행 구조를 표현합니다 ([04](04-domain-concepts.md) 1.2). `uses_overdue = false`가 investigator sign의 특수 처리를 담습니다.

**핵심은 `EXPECTATION_ITEM` + `STAGE_STATUS` 조합입니다.** 이 두 테이블이 EDC의 7개 단계, 샘플의 5단계, 영상의 5단계를 **전부** 담습니다. 도메인마다 테이블을 만들지 않습니다.

### 2.3 계획 계층 (A3, A4)

```mermaid
erDiagram
    SITE ||--o{ SDV_VISIT : "planned at"
    SDV_VISIT ||--o{ SDV_RESOURCE : "assigns"
    SDV_RESOURCE }o--|| USER : "CRA"
    TRIAL ||--o{ MILESTONE : has
    TRIAL ||--o{ TIMELINE_TASK : has
    TIMELINE_TASK }o--o| TIMELINE_TASK : "depends on"
    TIMELINE_TASK ||--o{ COMPLETION_CONDITION : requires
    COMPLETION_CONDITION }o--o| METRIC_DEFINITION : "evaluates"

    SDV_VISIT {
        id pk
        date planned_date
        date actual_date
        string status "TENTATIVE|ARRANGED|COMPLETED|CANCELLED"
        string visit_type
        int planned_days
        string cancel_reason
    }
    SDV_RESOURCE {
        id pk
        id cra_user_id fk
        decimal allocated_days
        int daily_capacity "폼/일"
    }
    MILESTONE {
        id pk
        string name
        string milestone_type
        date planned_date
        date actual_date
        string status "PLANNED|IN_PROGRESS|COMPLETED|AT_RISK|MISSED"
        int variance_days
    }
    TIMELINE_TASK {
        id pk
        string category
        string sub_category
        string name
        int round
        date start_date
        date end_date
        json related_functions
        string status
    }
```

### 2.4 유입 계층

```mermaid
erDiagram
    SOURCE_SYSTEM ||--o{ FEED : provides
    SOURCE_TEMPLATE ||--o{ FEED : "target schema"
    FEED ||--o{ MAPPING_PROFILE : "versioned"
    FEED ||--o{ DATA_DROP : receives
    DATA_DROP ||--o{ STAGING_RECORD : contains
    DATA_DROP ||--o{ VALIDATION_FINDING : produces
    DATA_DROP }o--|| SNAPSHOT : "included in"
    MAPPING_PROFILE ||--o{ DATA_DROP : "applied to"

    SOURCE_SYSTEM {
        id pk
        string name "Rave|IRT|CentralLab-A|BICR-B"
        string kind "EDC|RTSM|LAB|IMAGING|MANUAL"
        string ingestion_mode "FILE|API"
    }
    DATA_DROP {
        id pk
        string filename
        string file_hash
        datetime uploaded_at
        id uploaded_by fk
        int rows_total
        int rows_accepted
        int rows_rejected
        string state "UPLOADED|VALIDATED|PROMOTED|REJECTED"
    }
    SNAPSHOT {
        id pk
        datetime as_of
        string label
        boolean is_official
        id assumption_set_id fk
        id trial_config_id fk
    }
    SOURCE_TEMPLATE {
        id pk
        string dataset_code "DS01..DS10"
        string version
        json column_spec
        json match_key_spec "매칭 키 입도"
    }
    VALIDATION_FINDING {
        id pk
        string check_code "S1..S5|C1..C4|I1..I5|X1..X5"
        string severity "REJECT|WARN"
        int source_row_no
        string message
    }
```

`SOURCE_SYSTEM.ingestion_mode`가 파일 업로드와 API 커넥터를 같은 자리에서 교체 가능하게 만드는 지점입니다. 확정된 전제(파일 우선, 커넥터 확장)가 이 한 필드로 구현됩니다.

`SOURCE_TEMPLATE`이 [12](12-standard-source-templates.md)의 표준 형식을 데이터로 보유합니다. 컬럼 명세와 매칭 키 입도가 코드가 아니라 데이터로 존재해야, template이 개정되어도 코드를 고치지 않습니다.

`VALIDATION_FINDING`은 [12](12-standard-source-templates.md) 5장의 점검 결과를 원본 행 번호와 함께 보존합니다. 이 테이블이 향후 AI 검증 보조의 입력이 됩니다 ([14](14-ai-extensibility.md) 3.1).

### 2.5 플랫폼 계층

```mermaid
erDiagram
    USER ||--o{ USER_ROLE : has
    USER_ROLE }o--|| ROLE : "of"
    USER_ROLE }o--o| DATA_SCOPE : "limited by"
    ROLE ||--o{ PERMISSION : grants
    PERMISSION }o--|| MODULE : "on"
    USER ||--o{ AUDIT_LOG : generates
    USER ||--o{ SAVED_VIEW : owns

    PERMISSION {
        id pk
        string module_code "D1|D2|D3|D4|D5|D6|ADMIN"
        string access_level "NONE|READ|WRITE"
        boolean unblinded "눈가림 해제 권한"
    }
    DATA_SCOPE {
        id pk
        json trial_ids
        json country_ids
        json site_ids
    }
    AUDIT_LOG {
        id pk
        datetime occurred_at "UTC, 서버 생성"
        string actor_type "HUMAN|AI|ENGINE"
        id actor_user_id fk "actor_type=HUMAN"
        id actor_agent_id fk "actor_type=AI"
        string actor_engine "actor_type=ENGINE"
        id ai_run_id fk "AI 실행 참조"
        id initiated_by fk "AI를 실행시킨 사람"
        string action "CREATE|UPDATE|DELETE|LOGIN|EXPORT|IMPORT|ENGINE_RUN"
        string entity_type
        string entity_id
        json old_value
        json new_value
        string reason
        string source "UI|IMPORT|API|ENGINE|AI"
        id approved_by fk
        datetime approved_at
    }
```

### 2.6 AI 계층

```mermaid
erDiagram
    AI_AGENT ||--o{ AI_AGENT_GRANT : has
    AI_AGENT_GRANT }o--|| AI_TASK : "for"
    AI_AGENT_GRANT }o--o| DATA_SCOPE : "limited by"
    AI_AGENT ||--o{ AI_TASK_RUN : executes
    AI_TASK ||--o{ AI_TASK_RUN : "of"
    AI_TASK_RUN ||--o{ AI_TOOL_CALL : makes
    AI_TASK_RUN ||--o{ AUDIT_LOG : "produces"
    AI_TASK_RUN ||--o{ AI_PROPOSAL : creates
    AI_PROPOSAL }o--o| USER : "approved by"

    AI_TASK {
        id pk
        string task_code
        string version
        string required_level "READ_ONLY..DATA_CREATE"
        json input_schema
        json output_schema
        boolean approval_required
        string deterministic_fallback
    }
    AI_TASK_RUN {
        id pk
        id agent_id fk
        string task_code
        string task_version
        id initiated_by fk
        string provider
        string model_identifier
        datetime started_at
        datetime finished_at
        json input_ref
        json output_ref
        int records_affected
        string status "SUCCEEDED|FAILED|REJECTED_BY_POLICY"
    }
    AI_PROPOSAL {
        id pk
        string target_entity_type
        string target_entity_id
        json proposed_change
        string state "PENDING|APPROVED|REJECTED"
    }
```

이 계층은 [14](14-ai-extensibility.md)의 구조를 데이터 모델로 옮긴 것입니다. **AI가 없어도 이 테이블들은 비어 있을 뿐 앱은 정상 동작합니다.**

## 3. 핵심 설계 결정

### 3.1 왜 도메인별 테이블을 만들지 않는가

대안은 `EDCForm`, `Sample`, `Image` 테이블을 각각 만드는 것입니다. 이 방식의 문제는 다음과 같습니다.

| 항목 | 도메인별 테이블 | 통합 EXPECTATION_ITEM |
|---|---|---|
| 지표 계산 코드 | 도메인마다 별도 구현 | **한 벌** |
| 도메인 추가 (예: ePRO) | 새 테이블 + 새 코드 | **설정만 추가** |
| 크로스 도메인 조회 (Subject 360) | UNION 쿼리 필요 | **단일 쿼리** |
| 도메인 고유 속성 | 컬럼으로 자연스러움 | JSON 확장 필드 필요 |
| 쿼리 성능 | 테이블이 작아 유리 | 파티셔닝 필요 |

마지막 두 행이 통합 모델의 비용입니다. 그러나 이 앱의 본질이 **여섯 도메인을 가로지르는 통합 뷰**라는 점을 고려하면 통합 모델의 이점이 명확히 큽니다. 성능은 `(trial_id, domain, snapshot_id)` 파티셔닝과 ④층의 사전 집계로 해결합니다.

> **권고.** 통합 `EXPECTATION_ITEM` + `STAGE_STATUS` 모델을 채택합니다. 도메인 고유 속성은 `attributes` JSON 컬럼에 두되, **자주 필터링하는 속성은 물리 컬럼으로 승격**합니다.

### 3.2 스냅샷을 어떻게 저장할 것인가

세 가지 방식이 있습니다.

| 방식 | 저장 | 장점 | 단점 |
|---|---|---|---|
| 전체 복사 | 스냅샷마다 전체 행 복제 | 조회 단순, 빠름 | 저장 용량 급증 |
| 이벤트 소싱 | 변경 이벤트만 저장, 조회 시 재생 | 저장 효율 | 조회 복잡, 느림 |
| **하이브리드** | 현재 상태 + 변경 이력(bitemporal) + 공식 스냅샷만 물리 복제 | 균형 | 구현 복잡도 중간 |

> **권고.** **하이브리드**를 채택합니다. 구체적으로는 상태 테이블에 `valid_from` / `valid_to`를 두어 시점 조회를 지원하고, 주간 리뷰나 DBL처럼 **공식 리포트의 기준이 되는 시점만 물리 스냅샷으로 고정**합니다(`SNAPSHOT.is_official = true`). 이렇게 하면 일상 조회는 가볍고, 재현이 필요한 시점은 완벽히 보존됩니다.

### 3.3 Expected를 저장할 것인가 계산할 것인가

| 방식 | 장점 | 단점 |
|---|---|---|
| 매번 계산 | 저장 없음, 가정 변경 즉시 반영 | 느림, 과거 시점 재현 어려움 |
| **저장(materialize)** | 빠름, 재현 가능, 감사 추적 가능 | 재생성 작업 필요 |

> **권고.** **저장**합니다. `EXPECTATION_ITEM`을 실제 행으로 물리화합니다. 이유는 원칙 4.2 때문입니다. expected가 행으로 존재해야 감사 추적이 붙고, 버전이 붙고, "이 항목이 왜 기대되었는가"를 역추적할 수 있습니다. 가정이 바뀌면 배치 작업으로 재생성하고, 재생성 자체를 감사 로그에 남깁니다.

### 3.4 Analytics 계층을 둘 것인가

④층 `MetricFact`는 롤업 결과를 미리 계산해 저장하는 층입니다. 개념적으로는 star schema의 fact table입니다.

```
MetricFact(snapshot_id, assumption_version, trial_config_version,
           metric_code, metric_definition_version,
           expected_basis,                      -- DUE | PROTOCOL | FORECAST
           trial_id, country_id, site_id, subject_id,
           domain, stage_code,
           due_count, completed_count, backlog_count,
           overdue_count, waived_count, rate,
           aging_median, aging_p90)
```

`expected_basis`가 행 단위로 들어가 있으므로 **세 기준의 값이 모두 저장**됩니다. 화면 토글은 이 컬럼의 필터 전환일 뿐이며 재계산이 일어나지 않습니다 ([03](03-core-concept-model.md) 3.4). Export 시에는 세 기준이 모두 포함되어 외부 BI 도구에서도 같은 전환이 가능합니다.

`waived_count`가 별도 컬럼인 것도 중요합니다. 분모 밖이지만 반드시 함께 보여야 하기 때문입니다.

> **권고.** **둡니다.** 두 가지 이유입니다. 첫째, 대시보드 응답 속도가 사용자 채택을 좌우합니다. 둘째, 요구사항 C6(외부 BI 도구로 export)의 대상이 바로 이 테이블입니다. 이 구조를 그대로 내보내면 Power BI나 Tableau에서 별도 가공 없이 사용할 수 있습니다.

## 4. 엔티티 요약

| 층 | 엔티티 | 역할 |
|---|---|---|
| ⓪ | `SourceSystem`, `Feed`, `SourceTemplate`, `MappingProfile` | 유입 경로와 표준 형식 |
| ⓪ | `DataDrop`, `StagingRecord`, `ValidationFinding`, `Snapshot` | 불변 유입 단위, 검증 결과, 시점 |
| ① | `Trial`, `Country`, `Site`, `Subject`, `Visit` | 계층 마스터 |
| ① | `ActivityDef`, `StageDef`, `Lab`, `CodeList` | 활동·단계·코드 정의 |
| ② | `AssumptionSet` | 시험 설계 가정의 버전 단위 |
| ② | `VisitSchedule`, `SoAActivity`, `EnrollmentPlan` | 기대 생성 규칙 |
| ② | **`TrialConfig`** | **처리 설정의 버전 단위** |
| ② | `StageSetting`, `StageScopeRule`, `QueryGraceSetting`, `SubjectTargetList`, `MetricSwitch` | 유예 기간, 범위, 대상, on/off |
| ③ | `ExpectationItem`, `StageStatus` | **추적의 핵심** |
| ③ | `IssueObject`, `Discrepancy` | 이슈와 불일치 |
| ③ | `SDVVisit`, `SDVResource` | SDV 계획 (A3) |
| ③ | `Milestone`, `TimelineTask`, `CompletionCondition` | 타임라인 (A4) |
| ④ | `MetricFact` | 사전 집계, BI export 대상 |
| ⑤ | `User`, `Role`, `Permission`, `DataScope`, `UserRole` | 권한 |
| ⑤ | `AuditLog` | 감사 추적 (행위자 구분 포함) |
| ⑤ | `MetricDefinition`, `SavedView` | 지표 정의, 사용자 뷰 |
| ⑤ | `AIAgent`, `AIAgentGrant`, `AITask`, `AITaskRun`, `AIToolCall`, `AIProposal` | AI 확장 ([14](14-ai-extensibility.md)) |

## 5. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-06-1 | **3.1 통합 EXPECTATION_ITEM 모델 채택 여부** — 구조 전체를 좌우 | 통합 모델 채택 |
| DP-06-2 | 3.2 스냅샷 하이브리드 방식 채택 여부 | 하이브리드 |
| DP-06-3 | 3.3 expected 물리화 채택 여부 | 물리화 |
| DP-06-4 | 예상 데이터 규모는 어느 정도인가 (시험 수 × 피험자 수 × 방문 수 × 폼 수) | 파악 필요 — 파티셔닝 설계에 직결 |
| DP-06-5 | 다중 시험을 하나의 DB에 둘 것인가, 시험별 분리할 것인가 | **하나의 DB + trial_id 분리** |
| DP-06-6 | `TrialConfig`를 `AssumptionSet`과 분리하는 것에 동의하는가 | **분리 권고** (2.1) |
| DP-06-7 | `MetricFact`에 3종 기준을 모두 저장하면 행 수가 3배가 된다. 허용 가능한가 | 허용 권고 — 토글 즉시성이 더 중요 |
