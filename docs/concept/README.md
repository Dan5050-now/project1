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
| 11 | [리스크와 미결 사항](11-risks-and-open-questions.md) | 리스크 등록부, 확정된 결정, 결정 대기 목록 |
| 12 | [표준 Source Dataset Template](12-standard-source-templates.md) | 앱이 요구하는 표준 데이터 형식과 업로드 검증 |
| 13 | [Trial Configuration Template](13-trial-configuration.md) | 유예 기간, 단계 on/off, 대상 목록 등 시험별 설정 |
| 14 | [AI 활용 확장성](14-ai-extensibility.md) | AI 권한 모델, Tool API, 행위자 구분 감사 추적 |
| 15 | [지표 계산 명세](15-metric-specification.md) | 처리 조건과 계산식, 재현 가능성 |

## 확정된 전제

| 항목 | 결정 | 근거 |
|---|---|---|
| 데이터 유입 | **파일 업로드 우선, 커넥터 확장 가능 구조** | vendor API 계약·인증 협의 없이 즉시 시작 가능하고, 현실의 vendor 리포트 관행과 일치 |
| 규제 수준 | **Non-GxP 내부 도구 + 21 CFR Part 11 대비 설계** | 개념 검증 속도를 지키면서 나중에 validation으로 승격할 때 재설계 위험을 없앰 |
| 개발 언어 | **Python** | 요구사항으로 지정됨 |
| 분모 기준 | **Due 기본 + 3종 토글 전환** | 운영 지표로서 Due가 유용하되, 총량·예측 관점도 필요 |
| 예외 상태 | **`WAIVED` 단일 상태, 분모 제외** | 해결 불가와 의도적 면제 모두 예외 사항이며, 분모에 남기면 지표가 영구 왜곡 |
| 시스템 호환성 | **표준 template + 시험별 설정** | 특정 EDC·시험 설계에 종속되지 않기 위함 |
| 입력 경계 | **vendor 원본이 아니라 vendor data로 만든 사내 표준 파일** (external data reconciliation file 등) | 이미 만들고 있는 파일을 재사용하고, vendor 형식 변동을 표준화 단계에서 흡수 |
| 대조 판정 | **파일의 판정을 수입하지 않고 앱이 양측 원시값으로 자체 판정** | 외부 판정은 앱이 재현할 수 없어 계산식 명세 밖에 놓임 |
| AI 연결 | **사내 내부 LLM** | 데이터가 조직 경계를 벗어나지 않음. 어댑터 계층은 교체·기록을 위해 유지 |
| AI의 역할 | **보조 수단. 보고되는 숫자는 계산하지 않음** | 재현되지 않는 숫자는 GCP·CSV 관점에서 근거가 될 수 없음 |

## 개정 이력

| 버전 | 일자 | 내용 |
|---|---|---|
| v1 | 2026-09-15 | 초안 작성 (문서 00~11) |
| v2 | 2026-09-18 | 1차 검토 반영 — 분모 기준 토글, 상태 통합, 유예 기간 재정의, EDC 병행 단계, Reconciliation 재정의, 표준 template·설정 template·AI 확장·지표 명세 추가 (문서 12~15 신규) |
| v2.1 | 2026-09-19 | DP-12-6 확정 (입력 경계를 사내 표준 파일로 이동, 결합형 `DS05R`·`DS08R` 추가, 출처 메타데이터 필수화, 자체 판정 원칙), DP-14-3 확정 (사내 내부 LLM 연결) |
