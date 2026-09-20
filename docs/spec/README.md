# 상세 사양서 (Specification)

개념 설계([`../concept/`](../concept/README.md))가 확정된 뒤 작성한 구현 사양입니다.

## 1. 범위

**Phase 0(기반) + Phase 1(엔진 검증)** 만 다룹니다 ([개념 10](../concept/10-mvp-and-roadmap.md)).

| 포함 | 제외 |
|---|---|
| 마스터 데이터, 인증·RBAC, 감사 추적, 관리자 화면 | D3 SDV 계획 |
| 표준 template `DS01`~`DS04` 업로드와 검증 | D4 샘플, D5 영상 |
| 시험 설정(`CFG01`~`CFG09`) | D6 타임라인 |
| Expectation Engine, Progress Engine | 예측 Layer 2, KRI |
| D2 RTSM, D1 EDC 지표와 화면 | AI 연동 |
| 스냅샷·버전 관리, export | Portfolio 화면 |

Phase 2 이후 사양은 **Phase 1의 완료 조건(기존 엑셀 리포트와 숫자 일치)이 충족된 뒤** 작성합니다. 검증되지 않은 엔진 위에 사양을 쌓으면 전부 다시 써야 합니다.

다만 **데이터 모델과 엔진은 6개 도메인 전체를 수용하는 구조**로 설계합니다 ([개념 03](../concept/03-core-concept-model.md) 1장). Phase 2에서 추가되는 것은 도메인 어댑터와 화면이지 스키마가 아닙니다.

## 2. 문서 구성

| 번호 | 문서 | 내용 |
|---|---|---|
| 01 | [범위와 전제](01-scope-and-assumptions.md) | 구현 범위, 미결 항목에 대해 취한 전제 |
| 02 | [물리 데이터 모델](02-data-model.md) | 테이블 정의, 제약, 인덱스, 파티셔닝 |
| 03 | [엔진 사양](03-engine-spec.md) | Expectation·Progress Engine 알고리즘 |
| 04 | [유입 사양](04-ingestion-spec.md) | 업로드 파이프라인, 검증 규칙 |
| 05 | [API 사양](05-api-spec.md) | REST 엔드포인트 |
| 06 | [화면 사양](06-screen-spec.md) | 화면별 요소와 동작 |
| 07 | [권한·감사 사양](07-rbac-audit-spec.md) | RBAC 구현, 감사 추적 |
| 08 | [테스트 계획](08-test-plan.md) | golden dataset, 경계 조건, 검증 절차 |
| — | [`golden/`](golden/) | golden dataset 실물 (입력 10개 + 기대 출력 3개) |

golden dataset은 **사양의 자기 검증 장치**입니다. 입력 파일로 이 사양대로 계산하면 `expected/`가 나와야 하며, 나오지 않으면 구현이나 사양 중 하나가 틀린 것입니다.

## 3. 개념 문서와의 관계

사양은 개념을 **구현 가능한 수준으로 좁힌 것**이며, 개념을 바꾸지 않습니다. 개념과 사양이 충돌하면 개념이 우선하고, 사양을 고칩니다.

각 사양 항목에는 근거가 되는 개념 문서의 절 번호를 답니다. 근거 없는 사양 항목은 두지 않습니다.

## 4. 확정된 설계 전제

| 항목 | 결정 | 근거 |
|---|---|---|
| 기술 스택 | Django 5 + DRF + PostgreSQL 16 + Celery | [개념 09](../concept/09-tech-stack.md) |
| 분모 기준 | Due 기본, 3종 모두 저장, 토글 전환 | [개념 03](../concept/03-core-concept-model.md) 3.4 |
| 예외 상태 | `WAIVED` 단일, 분모 제외 | [개념 03](../concept/03-core-concept-model.md) 3.3 |
| EDC 단계 | 입력 후 5단계 병행 → lock | [개념 04](../concept/04-domain-concepts.md) 1.2 |
| 입력 경계 | 사내 표준 파일 (vendor 원본 아님) | [개념 12](../concept/12-standard-source-templates.md) 1.2 |
| 값의 추정 | 하지 않음 | [개념 15](../concept/15-metric-specification.md) 3.3b |
