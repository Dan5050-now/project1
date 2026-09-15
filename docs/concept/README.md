# Clinical Trial Progress Management App — 개념 설계 (Concept Design)

이 디렉터리는 **임상시험 데이터/샘플/이미지/SDV/타임라인 통합 진척 관리 앱**의 개념 설계 문서입니다.
아직 구현 단계가 아니며, 검토와 수정을 거쳐 상세 계획과 사양(specification)으로 발전시키는 것이 목적입니다.

## 검토 방법

모든 섹션에는 `1.2`, `4.3.1` 같은 **고유 번호**가 붙어 있습니다.
수정 의견을 주실 때 `03번 문서 3.2는 이렇게 바꿔줘` 형태로 지적해 주시면 해당 부분만 정확히 반영하겠습니다.

각 문서 끝에는 **검토 포인트(Decision Points)** 가 있습니다. 결정이 필요한 항목을 모아둔 것이니 그 부분을 우선 봐 주시면 좋겠습니다.

## 문서 구성

| 번호 | 문서 | 내용 |
|---|---|---|
| 00 | [개요와 제품 비전](00-overview.md) | 문제 정의, 비전, 범위, 설계 원칙 |
| 01 | [벤치마크 조사](01-benchmark.md) | 상용 솔루션·업계 표준 조사 결과와 시사점 (출처 포함) |
| 02 | [사용자와 활용 시나리오](02-personas-and-use-cases.md) | 페르소나, 핵심 질문, 사용 시나리오 |
| 03 | [핵심 개념 모델](03-core-concept-model.md) | **문서 전체의 중심.** 4개 아키타입과 3개 엔진 |
| 04 | [도메인별 개념 정의](04-domain-concepts.md) | EDC/RTSM/SDV/Sample/Image/Timeline 6개 도메인 |
| 05 | [정보 구조와 화면 개념](05-information-architecture.md) | 내비게이션, 화면 개념, 드릴다운 |
| 06 | [논리 데이터 모델](06-logical-data-model.md) | 개념 수준 ERD와 엔티티 정의 |
| 07 | [예측과 분석](07-prediction-and-analytics.md) | 예측 모델 개념, KRI/QTL |
| 08 | [플랫폼 공통 서비스](08-platform-services.md) | RBAC, audit trail, 버전 관리, import/export, BI 연동 |
| 09 | [기술 스택 권고](09-tech-stack.md) | 옵션 비교와 단일 권고안 |
| 10 | [MVP 범위와 로드맵](10-mvp-and-roadmap.md) | 단계별 개발 계획 |
| 11 | [리스크와 미결 사항](11-risks-and-open-questions.md) | 리스크 등록부, 결정 대기 목록 |

## 확정된 전제

| 항목 | 결정 | 근거 |
|---|---|---|
| 데이터 유입 | **파일 업로드 우선, 커넥터 확장 가능 구조** | vendor API 계약·인증 협의 없이 즉시 시작 가능하고, 현실의 vendor 리포트 관행과 일치 |
| 규제 수준 | **Non-GxP 내부 도구 + 21 CFR Part 11 대비 설계** | 개념 검증 속도를 지키면서 나중에 validation으로 승격할 때 재설계 위험을 없앰 |
| 개발 언어 | **Python** | 요구사항으로 지정됨 |
