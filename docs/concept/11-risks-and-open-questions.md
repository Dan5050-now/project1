# 11. 리스크와 미결 사항

## 1. 주요 리스크

리스크는 발생 가능성과 영향도로 평가했습니다. 가장 위험한 것부터 나열합니다.

### 1.1 R1 — 숫자 불일치로 인한 신뢰 상실 (높음 / 치명적)

**내용.** 앱의 숫자가 기존 엑셀 리포트와 다르면 사용자는 앱을 믿지 않습니다. 한 번 잃은 신뢰는 회복되지 않으며, 사람들은 조용히 엑셀로 돌아갑니다.

**원인.** 대부분 정의 불일치입니다. "expected form"이 무엇을 세는지에 대한 합의가 없으면 숫자는 반드시 달라집니다. 벤치마크([01](01-benchmark.md) 2.2)에서 확인한 업계의 교훈과 일치합니다.

**대응.**
- 지표 정의 등록부를 Phase 1부터 운영 ([08](08-platform-services.md) 6장)
- Phase 1 완료 조건을 "기존 엑셀과 숫자 일치"로 설정 ([10](10-mvp-and-roadmap.md) 3장)
- 불일치 시 드릴다운으로 원인을 설명할 수 있는 구조 (설계 원칙 4.3)

### 1.2 R2 — 소스 데이터의 품질과 식별자 불일치 (높음 / 큼)

**내용.** vendor 리포트의 식별자가 서로 맞지 않아 매칭에 실패합니다. 샘플에서 특히 심각합니다 ([04](04-domain-concepts.md) 4.3).

**대응.**
- 다단계 폴백 매칭 설계
- 매칭 실패를 숨기지 않고 Reconciliation Center에 노출 — **실패를 기능으로 전환**
- Phase 2 검증에서 vendor 리포트 3종 이상으로 매칭률 측정

### 1.3 R3 — 가정·설정 관리의 부담 (중간 / 큼)

**내용.** SoA, 방문 스케줄, 유예 기간, 단계 범위, 대상 목록을 시험마다 입력해야 합니다. **이 부담이 크면 새 시험에 앱을 적용하지 않게 되고, 앱은 첫 시험에서 멈춥니다.**

DP-12-6 확정으로 **데이터 준비 부담은 크게 줄었습니다.** 앱의 입력이 vendor 원본이 아니라 이미 만들고 있는 사내 표준 파일이므로, 새로 만들어야 하는 파일이 사실상 없습니다. 그래서 등급을 높음에서 중간으로 내렸습니다. 남는 부담은 시험 설정 입력입니다.

**대응.**
- **입력 경계를 사내 표준 파일로 이동** ([12](12-standard-source-templates.md) 1.2) — 가장 큰 완화
- **Mapping Profile** — 한 번 설정하면 사내 표준 파일을 그대로 업로드 ([08](08-platform-services.md) 5.2)
- 설정 template의 기본값 내장 — 비워두면 표준 기본값 적용 ([13](13-trial-configuration.md) 6장)
- 유사 시험에서 설정·가정 복제, 조직 표준 템플릿 등록
- 검증 리포트에 원본 행 번호 표시로 수정 위치를 즉시 특정
- 향후 AI 매핑 제안 ([14](14-ai-extensibility.md) 3.1), USDM/SoA import ([01](01-benchmark.md) 2.3)

**측정.** Phase 2에서 **신규 시험 온보딩에 걸리는 시간**을 측정합니다. 이것이 며칠 단위면 실패이고, 반나절 안이면 성공입니다.

### 1.3b R3b — 표준화 과정이 앱의 시야 밖에 있음 (중간 / 큼)

**내용.** DP-12-6 확정에 따르는 새 리스크입니다. vendor 원본에서 사내 표준 파일이 만들어지는 과정이 앱 경계 밖이므로, **그 과정에서 누락이나 오류가 생기면 앱은 알 수 없습니다.** 앱은 받은 파일이 완전하다고 가정할 수밖에 없습니다.

특히 위험한 경우는 부분 추출입니다. 표준 파일이 일부 사이트나 일부 기간만 담고 있으면, 앱은 그 범위가 전부인 줄 알고 "빠진 것이 없다"고 표시합니다.

**대응.**
- **출처 메타데이터 필수화** ([12](12-standard-source-templates.md) 2.2) — 어느 vendor 데이터를 언제 누가 추출해 만든 파일인지 기록
- 완결성 점검 C2·C3·C5 — 이전 Drop 대비 행 수 급감, 사이트 커버리지 누락, 추출일 역행 탐지
- 결합형 파일의 한쪽 값 전체 결측 탐지 (C6)
- 앱의 자체 판정과 파일 판정의 비교 (X6) — 표준화 단계의 기준 차이를 드러냄
- Feed 신뢰도 표시 ([12](12-standard-source-templates.md) 5.6)

**한계를 명시합니다.** 위 대응은 **탐지 가능한 이상만** 잡습니다. 표준화 단계에서 일관되게 누락된 항목은 앱이 원리적으로 발견할 수 없습니다. 이것은 설계로 해결되는 문제가 아니라 **표준 파일 작성 절차의 품질 관리로 다뤄야 할 문제**입니다.

### 1.4 R4 — 예측 기능의 오해와 오용 (중간 / 큼)

**내용.** 예측값이 사실처럼 받아들여져 잘못된 의사결정으로 이어집니다. 특히 SDV 적정성 판정과 마일스톤 `AT_RISK` 판정이 위험합니다.

**대응.**
- 구간 추정과 근거 표시를 강제 ([07](07-prediction-and-analytics.md) 4장)
- 예측과 사실의 시각적 구분
- Layer 3(학습 모델)을 성급히 도입하지 않음

### 1.5 R5 — 눈가림 정보의 노출 (낮음 / 치명적)

**내용.** 층화 정보나 배정군이 권한 없는 사용자에게 노출됩니다. **export 경로에서 마스킹이 누락되는 것이 전형적인 사고 유형**입니다.

**대응.**
- 마스킹을 데이터 접근 계층에서 한 번만 적용 ([08](08-platform-services.md) 2.4)
- export도 동일 계층을 거치도록 강제
- 권한 시나리오 테스트를 Phase 0 완료 조건에 포함

### 1.6 R6 — 범위 확대 (높음 / 중간)

**내용.** 사용자가 늘어나면서 요청이 쌓이고, 앱이 CTMS나 EDC의 영역까지 넘보게 됩니다.

**대응.** [00](00-overview.md) 2.2의 Non-goals를 명시적 경계로 유지하고, 변경 시 문서를 갱신합니다.

### 1.7 R7 — 성능 (중간 / 중간)

**내용.** 통합 `EXPECTATION_ITEM` 모델은 행 수가 큽니다. 대규모 시험 여러 개가 쌓이면 조회가 느려집니다.

**추정.** 피험자 500명 × 방문 20회 × 폼 15종 = 시험당 약 15만 항목. 단계까지 곱하면 100만 행 규모. 시험 10개면 1천만 행. PostgreSQL이 충분히 감당하는 규모이나 인덱스와 파티셔닝 설계가 필요합니다.

**대응.** `(trial_id, snapshot_id)` 파티셔닝, `MetricFact` 사전 집계 ([06](06-logical-data-model.md) 3.4), 실제 규모 확인 (DP-06-4)

### 1.8 R8 — Validation 승격 시의 재작업 (낮음 / 큼)

**내용.** 나중에 GxP validated system으로 승격할 때 감사 추적이나 접근 통제가 요건을 만족하지 못해 재설계가 필요해집니다.

**대응.** 확정 전제에 따라 Part 11 수준의 감사 추적 스키마를 처음부터 적용하고, **행위자 구분(사람/AI/엔진)을 Phase 0부터 포함**하며, 격차 목록을 관리합니다 ([08](08-platform-services.md) 3.6).

### 1.9 R9 — 매칭 키 입도 부족으로 인한 오판정 (중간 / 큼)

**내용.** 샘플의 kit 유형이나 영상의 modality가 매칭 키에 포함되지 않으면, 일부만 도착했는데 전부 도착한 것으로 판정됩니다. **틀린 답을 자신 있게 내놓는** 유형의 오류라 발견이 늦습니다.

**대응.**
- Feed마다 매칭 키를 명시적으로 선언 ([03](03-core-concept-model.md) 5.1)
- 입도가 권고에 미달하면 경고 + reconciliation 신뢰도 낮음 표시
- golden dataset에 경계 조건 E12로 포함 ([15](15-metric-specification.md) 7.2)

### 1.10 R10 — AI 도입에 따른 설명 가능성 저하 (낮음 / 치명적)

**내용.** AI가 앱에 결합된 뒤 "이 숫자를 누가 만들었는가", "이 레코드는 사람이 만든 것인가"에 답할 수 없게 됩니다. GCP와 computerised system validation 관점에서 치명적입니다.

**대응.**
- **AI는 보고되는 숫자를 계산하지 않음** ([14](14-ai-extensibility.md) 원칙 1.1)
- 사전 등록된 작업만 수행, 기본은 제안 방식
- 감사 추적의 행위자 구분과 AI 실행 기록 ([14](14-ai-extensibility.md) 5장)
- `ai/` 모듈을 코드 경계로 분리 ([09](09-tech-stack.md) 3.5)
- **내부 LLM 연결**로 데이터가 조직 경계를 벗어나지 않음 ([14](14-ai-extensibility.md) 4.3)

다만 내부 LLM이라도 **모델 버전이 바뀌면 과거 AI 실행 결과의 재현은 보장되지 않습니다.** 이것을 숨기지 않고 실행 기록에 모델 식별자와 함께 명시합니다 (DP-14-8).

### 1.11 R11 — 설정 변경으로 인한 지표 혼란 (중간 / 중간)

**내용.** 유예 기간이나 단계 on/off를 바꾸면 모든 지표가 바뀝니다. 사용자가 "왜 갑자기 숫자가 달라졌는지" 모르면 신뢰를 잃습니다.

**대응.**
- 설정을 버전 관리하고 계산 좌표에 포함 ([03](03-core-concept-model.md) 7.2)
- 과거 스냅샷은 과거 설정으로 계산된 값 유지 ([08](08-platform-services.md) 4.2)
- 화면 상단에 설정 버전 항시 표시, 비교 시 버전 차이 경고
- 설정 변경 영향 미리보기 ([13](13-trial-configuration.md) 5장)

## 2. 리스크 요약

| # | 리스크 | 가능성 | 영향 | 대응 문서 |
|---|---|---|---|---|
| R1 | 숫자 불일치로 신뢰 상실 | 높음 | 치명적 | 08-6장, 10-3장 |
| R2 | 소스 데이터 식별자 불일치 | 높음 | 큼 | 04-4.3, 03-5장 |
| R3 | 가정·설정 관리 부담 | 중간 | 큼 | 08-5.2, 13-6장 |
| R3b | **표준화 과정이 앱 시야 밖** | 중간 | 큼 | 12-2.2, 12-5장 |
| R4 | 예측 오용 | 중간 | 큼 | 07-4장 |
| R5 | 눈가림 정보 노출 | 낮음 | 치명적 | 08-2.4 |
| R6 | 범위 확대 | 높음 | 중간 | 00-2.2 |
| R7 | 성능 | 중간 | 중간 | 06-3.4 |
| R8 | Validation 재작업 | 낮음 | 큼 | 08-3.6 |
| R9 | 매칭 키 입도 부족 | 중간 | 큼 | 03-5.1, 15-7.2 |
| R10 | AI 도입 시 설명 가능성 저하 | 낮음 | 치명적 | 14 전체 |
| R11 | 설정 변경으로 인한 지표 혼란 | 중간 | 중간 | 13-5장, 08-4.2 |

## 3. 확정된 결정 (검토 완료)

1차 검토에서 확정된 사항입니다. 이후 설계는 모두 이 결정을 전제로 합니다.

| # | 결정 | 반영 위치 |
|---|---|---|
| DP-03-1 | Due-expected 기본 + **3종 토글 전환** | [03](03-core-concept-model.md) 3.4, [05](05-information-architecture.md) 3.3 |
| DP-03-2 | `BLOCKED`와 `WAIVED`를 **`WAIVED`로 통합**, 분모 제외 | [03](03-core-concept-model.md) 3.3 |
| DP-03-3 | 유예 기간 **달력일 기준 재정의**, 시험별 설정 | [03](03-core-concept-model.md) 3.5, [13](13-trial-configuration.md) 4.4 |
| DP-03-3-c1 | data review **시험별 적용 여부 on/off** | [04](04-domain-concepts.md) 1.4 |
| DP-03-3-e1 | investigator sign **유예 없이 pending 건수만, 전체/SAE 구분** | [04](04-domain-concepts.md) 1.5 |
| DP-03-3-g | sample 중앙랩 도착 **채취일 기준 +30일** | [04](04-domain-concepts.md) 4.2 |
| DP-03-3-h~i | image **taken(+0) / uploaded(+14)** 분리 | [04](04-domain-concepts.md) 5.2 |
| DP-03-3-j~k | query **open(+14) / answered(+30), 소유자별 차등** | [04](04-domain-concepts.md) 1.6 |
| DP-03-4 | `backlog = PENDING + OVERDUE`, `WAIVED` 분모 제외 | [03](03-core-concept-model.md) 3.6 |
| DP-03-5 | EDC **입력 후 5단계 병행 → lock** | [03](03-core-concept-model.md) 3.1, [04](04-domain-concepts.md) 1.2 |
| DP-03-6 | Reconciliation **매칭 키 입도 선언 + 샘플 유형 재정의** | [03](03-core-concept-model.md) 5장, [04](04-domain-concepts.md) 4.4 |
| 요구사항 7 | **표준 source dataset template** 도입 | [12](12-standard-source-templates.md) |
| 요구사항 8 | **Trial Configuration template** 도입 | [13](13-trial-configuration.md) |
| 요구사항 9 | **AI 확장 구조** (Tool API, 권한 등급, 등록된 작업) | [14](14-ai-extensibility.md) |
| 요구사항 10 | 감사 추적 **행위자 구분 (사람/AI/엔진)** | [08](08-platform-services.md) 3.5, [14](14-ai-extensibility.md) 5장 |
| 요구사항 11 | **지표 계산 명세와 재현 가능성** | [15](15-metric-specification.md) |
| **DP-12-6** | **앱의 입력 경계 = vendor 원본이 아니라 vendor data로 만든 사내 표준 파일** (external data reconciliation file 등) | [12](12-standard-source-templates.md) 1.2, 3장 |
| **DP-14-3** | **사내 내부 LLM 연결** — 외부 전송 없음, 어댑터 계층은 유지 | [14](14-ai-extensibility.md) 4.3 |
| **DP-12-8** | **표준 파일에 대조용 원시값 포함** — 앱은 항상 자체 판정 가능 | [12](12-standard-source-templates.md) 3.2 |
| DP-12-7 | **벤치마킹 기반 형식 초안 작성** — Q1~Q3 확정 반영 완료 | [16](16-external-data-format-draft.md) |
| **DP-16-1** | **매칭 키에 nominal timepoint(`TPTNUM`) 포함** | [16](16-external-data-format-draft.md) 1.2 |
| **DP-16-2** | **누적 전송** — 현재 관행과 일치 | [16](16-external-data-format-draft.md) 4.4 |
| **Q2 확정** | **사내 표준 DTS 없음. 앱 template이 vendor DTS 협의의 sponsor 측 기준안이 됨** | [16](16-external-data-format-draft.md) 2.2 |
| **DP-16-6** | **우선순위 검토 완료** — 19건 반영, 조건부 우선순위 도입 | [16](16-external-data-format-draft.md) 2.2 |
| **DP-16-8** | **MUST 미확보 시 대안 정의** — 계산 불가 지표는 화면에서 제외 | [16](16-external-data-format-draft.md) 2.3 |
| **DP-16-9** | **근사 완료일 사용 안 함** — 혼선 위험이 실익보다 큼 | [16](16-external-data-format-draft.md) 2.4, [15](15-metric-specification.md) 3.3b |

## 4. 결정 대기 목록

### 4.1 구조를 좌우하는 결정

| # | 사항 | 제안 | 문서 |
|---|---|---|---|
| **DP-06-1** | **통합 EXPECTATION_ITEM 모델 채택** | 채택 | [06](06-logical-data-model.md) 3.1 |
| **DP-09-1** | **Django 스택 채택** | 채택 | [09](09-tech-stack.md) 3장 |
| **DP-14-1** | **AI는 보고되는 숫자를 계산하지 않는다** | 채택 | [14](14-ai-extensibility.md) 1.1 |
| **DP-03-13** | **외부에서 만들어진 대조 판정을 수입하지 않고 앱이 자체 판정한다** | 채택 | [03](03-core-concept-model.md) 5.1 |
| **DP-00-3** | **다중 시험(포트폴리오) 전제** | 채택 | [00](00-overview.md) 5장 |
| **DP-00-5** | **"표준 형식 + 시험별 설정" 접근** | 채택 | [00](00-overview.md) 4.8 |
| **DP-02-2** | **사이트 직원의 직접 접근 여부** | 접근 없음 | [02](02-personas-and-use-cases.md) 5장 |
| **DP-06-6** | `TrialConfig`를 `AssumptionSet`과 분리 | 분리 | [06](06-logical-data-model.md) 5장 |

### 4.2 업무 정의가 필요한 결정

| # | 사항 | 문서 |
|---|---|---|
| DP-03-8 | sample `received(bioanalytics)`, `analyzed`의 유예 기간 값 | [03](03-core-concept-model.md) 3.5 |
| DP-03-9 | image `QC passed`, `read`의 유예 기간 값 | [03](03-core-concept-model.md) 3.5 |
| DP-03-10 | 쿼리 소유자 구분에 추가할 대상 | [03](03-core-concept-model.md) 10장 |
| DP-03-12 | investigator sign의 **SAE 판정 기준** (폼 종류 / 플래그 / 심각도) | [03](03-core-concept-model.md) 10장 |
| DP-04-1 | 반복 폼(AE, CM)의 기대치 처리 방식 | [04](04-domain-concepts.md) 1.9 |
| DP-04-2 | query group의 축 정의 | [04](04-domain-concepts.md) 1.9 |
| DP-04-8 | SDV 일일 처리량의 측정 단위 | [04](04-domain-concepts.md) 3.4 |
| DP-04-10 | 샘플 추적 단위 (draw vs aliquot) | [04](04-domain-concepts.md) 4.7 |
| DP-04-21 | kit 유형 목록 (PK/ADA/NAB 외) | [04](04-domain-concepts.md) 4.7 |
| DP-04-14 | 영상 추적 단위 | [04](04-domain-concepts.md) 5.6 |
| DP-08-3 | 변경 사유 필수 입력 대상 | [08](08-platform-services.md) 8장 |
| DP-12-1 | 표준 dataset 10종 구성의 적절성 | [12](12-standard-source-templates.md) 7장 |
| DP-12-2 | DS03의 wide vs long 구조 | [12](12-standard-source-templates.md) 7장 |
| DP-13-1 | 설정 template 9개 시트 구성의 적절성 | [13](13-trial-configuration.md) 7장 |
| DP-15-3 | 지표 목록에서 빠진 것 | [15](15-metric-specification.md) 8장 |
| DP-15-5 | 지표 정의 변경 승인자 | [15](15-metric-specification.md) 8장 |

### 4.3 조직·환경 확인이 필요한 사항

| # | 사항 | 문서 |
|---|---|---|
| **DP-16-7** | **DTS 협의 worksheet를 표준 절차에 넣을 것인가** | [16](16-external-data-format-draft.md) 2.2 |
| DP-16-10 | `SRC_EXTRACT_DTC` 확보 수준 — 데이터 최신성 지표의 근거 | [16](16-external-data-format-draft.md) 2.4 |
| DP-16-11 | 완료일 미제공 시 후속 단계를 비활성화할 것인가 건수만 집계할 것인가 | [15](15-metric-specification.md) 3.3b |
| DP-16-3 | 샘플 추적 단위 (kit vs aliquot) | [16](16-external-data-format-draft.md) 11장 |
| DP-16-4 | controlled terminology 기본값 | [16](16-external-data-format-draft.md) 7장 |
| DP-12-9 | 사내 실제 운영 형태가 결합형인가 분리형인가 | [12](12-standard-source-templates.md) 7장 |
| DP-14-7 | 내부 LLM의 연결·인증 방식 | [14](14-ai-extensibility.md) 8장 |
| DP-14-9 | 내부 LLM의 처리 용량 | [14](14-ai-extensibility.md) 8장 |
| DP-01-1 | 사내 기존 상용 도구 사용 여부 | [01](01-benchmark.md) 5장 |
| DP-01-3 | 사내 표준 KPI 정의서 존재 여부 | [01](01-benchmark.md) 5장 |
| DP-06-4 | 예상 데이터 규모 | [06](06-logical-data-model.md) 5장 |
| DP-08-1 | 사내 SSO 프로토콜 | [08](08-platform-services.md) 8장 |
| DP-08-5 | 읽기 전용 DB 연결 허용 여부 | [08](08-platform-services.md) 8장 |
| DP-08-6 | 감사 로그 보존 기간 | [08](08-platform-services.md) 8장 |
| DP-09-2 | 사내 IT 기술 스택 제약 | [09](09-tech-stack.md) 5장 |
| DP-09-3 | 배포 환경 (사내 서버 vs 클라우드) | [09](09-tech-stack.md) 5장 |
| DP-09-5 | 개발 인력 규모와 숙련도 | [09](09-tech-stack.md) 5장 |
| DP-13-5 | 시험 설정 변경 권한 보유자 | [13](13-trial-configuration.md) 7장 |
| DP-10-3 | Phase 1 검증 대상 시험 선정 | [10](10-mvp-and-roadmap.md) 10장 |

## 5. 다음 단계

**1단계.** 4.1의 구조 결정 7건을 확정합니다. 이것들이 바뀌면 이후 문서를 다시 써야 하므로 먼저 봐야 합니다.

**2단계.** [16](16-external-data-format-draft.md)의 남은 검토 항목(Q4~Q12)을 확인합니다. 실물 template과 DTS 협의 worksheet는 [`templates/`](templates/)에서 Excel로 바로 여실 수 있습니다.

우선순위 검토와 근사값 사용 여부가 모두 정리되어, external data 형식은 확정 수준에 도달했습니다. 남은 것은 실제 vendor 협의에서 검증하는 일입니다 (DP-16-7).

근사 완료일을 쓰지 않기로 한 결과, **vendor로부터 완료일을 받아내는 것의 중요도가 올라갔습니다.** `BICR_UPLDDTC`와 `BA_ANALDTC`는 우선순위가 SHOULD이지만, 확보하지 못하면 해당 후속 단계의 기한 관리를 포기해야 하므로 협의에서 우선적으로 요청할 항목입니다.

**3단계.** 4.2의 업무 정의를 실무 담당자와 확정합니다. 이것이 [15](15-metric-specification.md)의 지표 정의 등록부와 [13](13-trial-configuration.md)의 설정 기본값이 됩니다.

**4단계.** 나머지 조직·환경 사항을 확인합니다.

**5단계.** ~~상세 사양서 작성~~ → **[`docs/spec/`](../spec/README.md)에 Phase 0 + Phase 1 범위로 작성 완료.** 물리 데이터 모델, 엔진 알고리즘, 유입·API·화면·권한 사양, 테스트 계획, golden dataset을 포함합니다. Phase 2 이후 사양은 Phase 1 완료 조건이 충족된 뒤 작성합니다.

**6단계.** Phase 0 개발에 착수합니다.
