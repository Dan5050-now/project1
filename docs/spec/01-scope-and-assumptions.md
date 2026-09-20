# 01. 범위와 전제

## 1. 구현 범위

### 1.1 Phase 0 — 기반

| # | 기능 | 개념 근거 |
|---|---|---|
| F0-1 | 마스터 데이터 (Trial, Country, Site, Subject, Visit, CodeList) | [06](../concept/06-logical-data-model.md) 2.1 |
| F0-2 | SSO 인증, 세션 관리 | [08](../concept/08-platform-services.md) 1 |
| F0-3 | 3차원 RBAC (모듈 × 접근수준 × 데이터범위) + 눈가림 마스킹 | [08](../concept/08-platform-services.md) 2 |
| F0-4 | 관리자 화면 (사용자·역할·배정·감사 조회) | [08](../concept/08-platform-services.md) 2.5 |
| F0-5 | 감사 추적 (행위자 3분류, append-only) | [08](../concept/08-platform-services.md) 3 |
| F0-6 | 표준 template 정의와 Mapping Profile | [12](../concept/12-standard-source-templates.md) |
| F0-7 | 업로드 파이프라인과 4계층 검증 | [12](../concept/12-standard-source-templates.md) 5 |
| F0-8 | Data Drop, Snapshot, 출처 메타데이터 | [12](../concept/12-standard-source-templates.md) 2.2 |
| F0-9 | 테이블 CSV/Excel export | [08](../concept/08-platform-services.md) 5.4 |

### 1.2 Phase 1 — 엔진 검증

| # | 기능 | 개념 근거 |
|---|---|---|
| F1-1 | Assumption Set (SoA, 방문 스케줄, 등록 계획) 입력·버전 | [13](../concept/13-trial-configuration.md) 4.2~4.3 |
| F1-2 | Trial Config (유예 기간, 단계 on/off, 범위, 대상 목록, 지표 on/off) | [13](../concept/13-trial-configuration.md) |
| F1-3 | Expectation Engine — Due / Protocol / Forecast 3종 생성 | [03](../concept/03-core-concept-model.md) 3.4 |
| F1-4 | Progress Engine — 매칭, 단계 상태 판정, 지표 산출 | [15](../concept/15-metric-specification.md) 4~5 |
| F1-5 | D2 RTSM — 피험자 상태, 방문 윈도우 이탈 | [04](../concept/04-domain-concepts.md) 2 |
| F1-6 | D1 EDC — 병행 단계, 서명 특수 처리, 쿼리 기한 | [04](../concept/04-domain-concepts.md) 1 |
| F1-7 | 4단계 롤업과 MetricFact | [06](../concept/06-logical-data-model.md) 3.4 |
| F1-8 | 도메인 화면 (분모 토글, 드릴다운, 예외 병기) | [05](../concept/05-information-architecture.md) 3.3 |
| F1-9 | Subject 360 (D1 + D2 범위) | [05](../concept/05-information-architecture.md) 3.4 |
| F1-10 | 지표 정의 등록부 | [15](../concept/15-metric-specification.md) 2 |

### 1.3 Phase 1 완료 조건

> 실제 시험 하나의 RTSM·EDC 표준 파일을 업로드하면, 화면의 입력률·SDV율이 **담당자가 엑셀로 만든 숫자와 일치**한다. 불일치가 있으면 그 원인을 드릴다운으로 설명할 수 있다. golden dataset 전 케이스를 통과한다.

## 2. 미결 항목에 대해 취한 전제

[개념 11](../concept/11-risks-and-open-questions.md) 4.2의 업무 정의 항목 중 Phase 0~1에 영향을 주는 것들입니다. **확정되면 설정값만 바꾸면 되도록** 설계했습니다.

| # | 미결 항목 | 취한 전제 | 확정 시 영향 |
|---|---|---|---|
| A-1 | DP-04-1 반복 폼(AE/CM) 처리 | `DS03.FORMTYPE = 'LOG'`인 폼은 **entry 단계 분모에서 제외**, 입력된 건에 대해서만 이후 단계 추적 | `StageScopeRule` 설정 변경으로 대응 |
| A-2 | DP-04-2 query group 축 | `QUERYOWNER`, `QUERYGRP`, `QUERYTYPE` 3축을 모두 분해 가능하게 저장 | 화면 필터만 조정 |
| A-3 | DP-03-12 SAE 판정 기준 | `DS03.SAEFL` 컬럼 값을 그대로 사용. 미제공 시 `CFG06`의 `FORM_LIST`로 판정 | 설정 변경 |
| A-4 | DP-03-3 freeze/lock 기한 | `CFG01.DBL_PLANNED_DT` 기준 역산. 역산 일수는 `CFG04.GRACE_DAYS`에 음수로 표기 | 설정 변경 |
| A-5 | DP-02-3 역할 기본값 | [02](../concept/02-personas-and-use-cases.md) 3장 매트릭스를 역할 템플릿으로 탑재 | 관리자 화면에서 수정 |
| A-6 | DP-08-3 사유 필수 대상 | `WAIVED` 처리, 확정 데이터 정정, 설정 변경 3가지에만 요구 | 설정 테이블로 확장 |
| A-7 | DP-06-4 데이터 규모 | 시험당 피험자 1,000명 × 방문 30회 × 폼 20종 = 약 60만 항목 기준으로 인덱스 설계 | 파티션 전략 재검토 |
| A-8 | DP-08-1 SSO 프로토콜 | OIDC 우선, SAML 대체. 미확정 구간은 자체 계정으로 개발 | 인증 어댑터 교체 |

**A-7과 A-8은 확정을 기다리지 않고 진행**합니다. A-7은 파티셔닝을 나중에 추가해도 되고, A-8은 인증 계층이 격리되어 있기 때문입니다.

## 3. 범위 밖이지만 구조에 자리를 두는 것

당장 구현하지 않지만 **나중에 얹을 수 없어서** 지금 자리를 확보하는 항목입니다.

| 항목 | 지금 하는 것 | 나중에 하는 것 |
|---|---|---|
| 감사 추적 행위자 구분 | `actor_type` 컬럼과 기록 로직 | AI 행위 기록 |
| AI Tool API | 서비스 계층을 API 경계로 분리 | Gateway·권한 등급 |
| 샘플·영상 도메인 | 제네릭 `ExpectationItem`/`StageStatus` 스키마 | 도메인 어댑터·화면 |
| Part 11 | 감사 스키마, 변경 사유, append-only | 전자 서명, validation 문서 |
| 다중 시험 | 전 테이블 `trial_id` 스코프 | Portfolio 화면 |

## 4. 비기능 요구

| # | 항목 | 목표 |
|---|---|---|
| N-1 | 도메인 화면 응답 | 롤업 테이블 2초 이내 (시험 1개, 60만 항목 기준) |
| N-2 | 드릴다운 응답 | 1,000행 페이지 1초 이내 |
| N-3 | 업로드 처리 | 10만 행 5분 이내 (비동기 배치) |
| N-4 | 엔진 재실행 | 시험 1개 전체 재생성 15분 이내 |
| N-5 | 동시 사용자 | 50명 |
| N-6 | 가용성 | 업무 시간 기준. 야간 배치 창 허용 |

N-1이 사용자 채택을 좌우합니다. 이를 위해 화면은 **`MetricFact` 사전 집계만 조회**하고 원본을 집계하지 않습니다 ([03](03-engine-spec.md) 6장).

## 5. 용어

| 용어 | 정의 |
|---|---|
| **항목(Item)** | `ExpectationItem` 1건. 폼 인스턴스, 방문, 샘플, 영상 중 하나 |
| **단계(Stage)** | 항목이 통과하는 처리 단계. `StageStatus` 1건에 대응 |
| **기한(Due)** | 트리거일 + 유예 기간 |
| **분모 기준(Basis)** | `DUE` / `PROTOCOL` / `FORECAST` |
| **스냅샷(Snapshot)** | 지표 계산의 시점 좌표 |
| **Drop** | 업로드 1건. 불변 |
