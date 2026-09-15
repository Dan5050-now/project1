# 06. 논리 데이터 모델

이 문서는 개념 수준의 데이터 모델입니다. 물리 스키마(테이블 정의, 인덱스, 제약)는 사양 단계에서 확정합니다.

## 1. 모델의 층 구조

```
┌─────────────────────────────────────────────────────────┐
│ ⑤ Platform      User, Role, Permission, AuditLog,       │
│                 MetricDefinition, SavedView              │
├─────────────────────────────────────────────────────────┤
│ ④ Analytics     MetricFact (집계 결과, 읽기 전용)        │
├─────────────────────────────────────────────────────────┤
│ ③ Tracking      ExpectationItem, StageStatus,            │
│                 IssueObject, Discrepancy,                │
│                 SDVVisit, Milestone, TimelineTask        │
├─────────────────────────────────────────────────────────┤
│ ② Assumption    AssumptionSet, SoAActivity,              │
│                 VisitSchedule, StageScopeRule            │
├─────────────────────────────────────────────────────────┤
│ ① Master        Trial, Country, Site, Subject, Visit,    │
│                 FormDef, SampleType, ImageModality, Lab  │
├─────────────────────────────────────────────────────────┤
│ ⓪ Ingestion     SourceSystem, Feed, MappingProfile,      │
│                 DataDrop, StagingRecord, Snapshot        │
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
    ASSUMPTION_SET ||--o{ VISIT_SCHEDULE : defines
    ASSUMPTION_SET ||--o{ SOA_ACTIVITY : defines
    ASSUMPTION_SET ||--o{ STAGE_SCOPE_RULE : defines
    ASSUMPTION_SET ||--o{ ENROLLMENT_PLAN : defines
    VISIT_SCHEDULE ||--o{ SOA_ACTIVITY : "at visit"
    SOA_ACTIVITY }o--|| ACTIVITY_DEF : references

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
        int expected_count
        json condition "코호트·층화 조건"
    }
```

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
    ISSUE_OBJECT }o--o| STAGE_STATUS : "blocks"
    DATA_DROP ||--o{ EXPECTATION_ITEM : "actual 근거"

    EXPECTATION_ITEM {
        id pk
        string domain "EDC|SAMPLE|IMAGE|VISIT"
        string item_key "매칭 키"
        string expectation_type "CONFIRMED|FORECAST"
        id assumption_set_id fk
        id snapshot_id fk
    }
    STAGE_STATUS {
        id pk
        string stage_code "entered|sdv|coded|..."
        boolean required
        date due_date
        datetime completed_at
        string status "NOT_APPLICABLE|NOT_DUE|PENDING|OVERDUE|DONE|BLOCKED|WAIVED"
        int aging_days
    }
    ISSUE_OBJECT {
        id pk
        string issue_domain "QUERY|SAMPLE|IMAGE"
        string issue_type
        string issue_group "query group 축"
        string state "OPEN|ANSWERED|CLOSED|CANCELLED"
        boolean blocking
        string referral_to
        datetime opened_at
        datetime closed_at
    }
    DISCREPANCY {
        id pk
        string kind "NOT_RECEIVED|NOT_EXPECTED|DISCREPANT|AMBIGUOUS"
        string resolution_state
        id assignee fk
    }
```

**핵심은 `EXPECTATION_ITEM` + `STAGE_STATUS` 조합입니다.** 이 두 테이블이 EDC의 7개 지표, 샘플의 7단계, 영상의 5단계를 **전부** 담습니다. 도메인마다 테이블을 만들지 않습니다.

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
    FEED ||--o{ MAPPING_PROFILE : "versioned"
    FEED ||--o{ DATA_DROP : receives
    DATA_DROP ||--o{ STAGING_RECORD : contains
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
    }
```

`SOURCE_SYSTEM.ingestion_mode`가 파일 업로드와 API 커넥터를 같은 자리에서 교체 가능하게 만드는 지점입니다. 확정된 전제(파일 우선, 커넥터 확장)가 이 한 필드로 구현됩니다.

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
        datetime occurred_at
        id actor_user_id fk
        string action "CREATE|UPDATE|DELETE|LOGIN|EXPORT"
        string entity_type
        string entity_id
        json old_value
        json new_value
        string reason
        string source "UI|IMPORT|ENGINE"
    }
```

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
MetricFact(snapshot_id, assumption_version, metric_code,
           trial_id, country_id, site_id, subject_id,
           domain, stage_code,
           due_count, completed_count, backlog_count, overdue_count, rate)
```

> **권고.** **둡니다.** 두 가지 이유입니다. 첫째, 대시보드 응답 속도가 사용자 채택을 좌우합니다. 둘째, 요구사항 C6(외부 BI 도구로 export)의 대상이 바로 이 테이블입니다. 이 구조를 그대로 내보내면 Power BI나 Tableau에서 별도 가공 없이 사용할 수 있습니다.

## 4. 엔티티 요약

| 층 | 엔티티 | 역할 |
|---|---|---|
| ⓪ | `SourceSystem`, `Feed`, `MappingProfile` | 유입 경로 정의 |
| ⓪ | `DataDrop`, `StagingRecord`, `Snapshot` | 불변 유입 단위와 시점 |
| ① | `Trial`, `Country`, `Site`, `Subject`, `Visit` | 계층 마스터 |
| ① | `ActivityDef`(FormDef/SampleType/ImageModality), `Lab` | 활동 정의 |
| ② | `AssumptionSet` | 가정의 버전 단위 |
| ② | `VisitSchedule`, `SoAActivity`, `StageScopeRule`, `EnrollmentPlan` | 기대 생성 규칙 |
| ③ | `ExpectationItem`, `StageStatus` | **추적의 핵심** |
| ③ | `IssueObject`, `Discrepancy` | 이슈와 불일치 |
| ③ | `SDVVisit`, `SDVResource` | SDV 계획 (A3) |
| ③ | `Milestone`, `TimelineTask`, `CompletionCondition` | 타임라인 (A4) |
| ④ | `MetricFact` | 사전 집계, BI export 대상 |
| ⑤ | `User`, `Role`, `Permission`, `DataScope`, `UserRole` | 권한 |
| ⑤ | `AuditLog` | 감사 추적 |
| ⑤ | `MetricDefinition`, `SavedView` | 지표 정의, 사용자 뷰 |

## 5. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-06-1 | **3.1 통합 EXPECTATION_ITEM 모델 채택 여부** — 구조 전체를 좌우 | 통합 모델 채택 |
| DP-06-2 | 3.2 스냅샷 하이브리드 방식 채택 여부 | 하이브리드 |
| DP-06-3 | 3.3 expected 물리화 채택 여부 | 물리화 |
| DP-06-4 | 예상 데이터 규모는 어느 정도인가 (시험 수 × 피험자 수 × 방문 수 × 폼 수) | 파악 필요 — 파티셔닝 설계에 직결 |
| DP-06-5 | 다중 시험을 하나의 DB에 둘 것인가, 시험별 분리할 것인가 | **하나의 DB + trial_id 분리** |
