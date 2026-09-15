# 01. 벤치마크 조사

이 문서는 개념 설계의 근거가 된 조사 결과입니다. 상용 솔루션이 이미 해결한 문제는 다시 발명하지 않고, 상용 솔루션이 비워둔 자리를 이 앱의 차별점으로 삼는 것이 목적입니다.

조사 시점은 2026년 9월이며, 모든 항목에 출처 링크를 달았습니다.

## 1. 상용 솔루션

### 1.1 Veeva Vault CDB (Clinical Database)

가장 가까운 참조 대상입니다. EDC, RTSM, eCOA, lab, imaging 등 여러 소스의 데이터를 자동으로 **집계·대조·정제**하여 하나의 조화된 데이터 패키지로 만드는 것을 표방합니다. Veeva 자체 EDC뿐 아니라 Medidata Rave 같은 타사 EDC도 소스로 받아들이며, 데이터 집계와 정제 시간을 30~50% 단축했다고 발표했습니다.

**시사점.** "여러 vendor 소스를 하나로 모아 대조한다"는 문제 정의 자체는 업계가 이미 인정한 방향입니다. 다만 CDB의 초점은 **데이터 정제(cleaning)** 로, 데이터를 깨끗하게 만드는 데 있습니다. 이 앱의 초점인 **진척 예측과 backlog 추적**과는 목적이 다릅니다. 즉 CDB는 "이 데이터가 맞는가"를, 이 앱은 "이 데이터가 언제 다 들어오는가"를 답합니다.

- [Veeva CDB 제품 페이지](https://www.veeva.com/products/veeva-cdb/)
- [Veeva Clinical Database 200 Study Milestone 발표](https://www.veeva.com/resources/veeva-clinical-database-crosses-200-study-milestone-cuts-time-to-aggregate-and-clean-study-data-by-30-50/)
- [Applied Clinical Trials 기사](https://www.appliedclinicaltrialsonline.com/view/veeva-clinical-database-crosses-200-study-milestone)

### 1.2 CTMS 대시보드 (Veeva / Medidata / Oracle)

현재 CTMS·EDC 대시보드는 등록 추이, 쿼리 적체, 사이트 스코어, 예산 소진율 등 수백 개의 KPI를 실시간으로 보여줍니다. 데이터 입력률, SDV율, 쿼리 aging(미해결·기한 초과 쿼리의 건수와 경과일)이 표준 지표로 자리잡았습니다.

**시사점.** 요구사항의 EDC 지표 a~h는 업계 표준 지표와 잘 맞습니다. 다만 대부분의 상용 대시보드는 **이미 발생한 것의 집계**에 머물고, 분모인 expected를 시스템이 능동적으로 생성하지 않습니다. 이 앱의 Expectation Engine이 바로 그 빈자리입니다.

- [CTMS Dashboards: KPIs and Metrics for Clinical Trials](https://intuitionlabs.ai/articles/ctms-dashboards-clinical-trial-kpis-metrics)
- [Veeva vs Medidata vs Oracle: CTMS Comparison Guide](https://intuitionlabs.ai/articles/veeva-medidata-oracle-ctms-comparison)
- [5 best EDC platforms for remote monitoring in clinical trials in 2026](https://www.viedoc.com/buyers-guides/best-edc-software-remote-monitoring)

### 1.3 RBQM 플랫폼 (CluePoints 등)

ICH E6(R3) 이후 RBQM 플랫폼들은 CtQ(Critical-to-Quality) 요소를 정의하고, 이를 KRI와 QTL로 연결해 중앙 모니터링하는 구조를 제공합니다. 핵심 메시지는 "**사전에 정의된 KRI, QTL, CtQ에 맞춰 데이터를 중앙 플랫폼에 통합하는 것이 효과적인 RBQM의 첫 단계**"라는 것입니다.

**시사점.** 이 앱이 만드는 지표(입력 지연, 쿼리 적체, 방문 윈도우 이탈, 샘플 분실률)는 그 자체로 **훌륭한 KRI 후보**입니다. 진척 관리 도구로 출발하되 KRI/QTL 프레임을 처음부터 염두에 두면, 나중에 RBQM 영역으로 자연스럽게 확장됩니다 (→ [07](07-prediction-and-analytics.md)).

- [Decoding ICH E6(R3): What It Means for RBQM — CluePoints](https://cluepoints.com/decoding-ich-e6r3-what-it-means-for-risk-based-quality-management-rbqm/)
- [ICH E6(R3), Demystified Part 2: Defining Critical-to-Quality](https://cluepoints.com/ich-e6r3-demystified-part-2-defining-critical-to-quality/)
- [Checking in on RBQM One Year After ICH E6(R3) — Astrix](https://www.astrixinc.com/blog/checking-in-on-rbqm-risk-based-quality-management-one-year-after-ich-e6r3/)

### 1.4 Imaging / BICR 플랫폼

영상 중앙 판독 플랫폼은 사이트 업로드, 비식별화, 눈가림 판독자 배정, 판독 계획 관리, 판독 불일치 조정(adjudication), 감사 추적까지를 하나의 워크플로로 다룹니다. 조사 과정에서 이 앱의 요구사항을 거의 그대로 서술한 문장을 발견했습니다.

> 시험의 어느 시점에서든 영상 팀은 다음 질문에 답할 수 있어야 한다. 이번 주에 어떤 영상이 **예상**되었는가, 어떤 것이 **도착**했는가, 어떤 것이 **QC에 실패**했는가, 어떤 쿼리가 열려 있는가, 어떤 것이 **기한을 넘겼는가**. 이것은 중앙 저장소와 직접 통합된 구조화된 추적 시스템을 요구하며, 수작업으로 갱신하는 별도 스프레드시트로는 불가능하다.

**시사점.** 요구사항의 image 도메인 설계가 업계가 인식한 실제 문제와 정확히 일치한다는 근거입니다. 또한 BICR 판독 데이터와 investigator 평가 데이터 간 **일관성 대조**(피험자 집합, 스캔 집합, 방문, 날짜, 평가 방법)가 표준 업무라는 점도 확인했습니다. 이는 image reconciliation 개념에 반영했습니다.

- [Medical Imaging Workflow Optimization for Clinical Trials — Collective Minds](https://collectiveminds.health/articles/medical-imaging-workflow)
- [Blinded Independent Central Review (BICR) Complete Guide](https://collectiveminds.health/articles/blinded-independent-central-review-bicr-complete-guide-for-clinical-trials)
- [BICR in Oncology Trials: Key Challenges — Cytel](https://cytel.com/perspectives/blinded-independent-central-review-in-oncology-trials-key-challenges/)
- [Central Review in Clinical Trials — QMENTA Glossary](https://www.qmenta.com/glossary/central-review-clinical-trials)

## 2. 업계 표준과 지표 정의

### 2.1 ICH E6(R3)

2025년 1월 6일 ICH가 채택했습니다. E6(R2)가 RBM을 도입했다면 E6(R3)는 이를 **RBQM**이라는 포괄적 접근으로 확장했습니다. 중앙 모니터링이 핵심 축이며, 원격·실시간 데이터 분석, 알고리즘 기반 이상 탐지, 그리고 **현장 모니터링 방문의 우선순위 결정**을 가능하게 하는 것으로 규정됩니다.

**시사점.** 마지막 항목이 특히 중요합니다. 요구사항의 SDV plan management(3-e, "현재 SDV 방문 계획이 예상 대비 충분한지 평가")는 E6(R3)가 명시적으로 지향하는 바와 정확히 같습니다. 즉 이 기능은 있으면 좋은 부가 기능이 아니라 **규제 방향과 정렬된 핵심 기능**으로 자리매김할 수 있습니다.

- [ICH E6(R3): Risk-Based Monitoring in practice — Efor](https://efor-group.com/en/risk-based-monitoring-impact-ich-e6-r3-clinical-trials/)
- [ICH E6(R3) Explained: Key Changes to GCP Guidelines](https://intuitionlabs.ai/articles/ich-e6-r3-gcp-guidelines-2026)
- [ICH E6(R3) and Risk-Based Quality Management — TRI](https://www.tritrials.com/ich-e6-r3-and-risk-based-quality-management/)

### 2.2 표준 지표 정의 (MCC / TransCelerate / SCDM)

Metrics Champion Consortium(MCC)은 이해관계자를 모아 표준 성과 지표를 정의했고, 여기에는 site activation date, database lock date 같은 **핵심 용어와 데이터 요소의 명확한 정의**가 포함됩니다. 핵심 용어를 정의하는 것이 현재 대 과거 성과를 동일 기준으로 비교하기 위한 필수 조건이라는 점이 강조됩니다. TransCelerate 모델에서는 품질 변화, 데이터 수집과 쿼리 해결의 적시성, 운영 효율을 핵심 지표로 삼습니다.

**시사점.** 이 앱에서 가장 위험한 실패 모드는 기술이 아니라 **정의의 불일치**입니다. "expected form"이 무엇을 세는지 팀마다 다르면 앱의 숫자는 신뢰를 잃습니다. 따라서 모든 지표에 **기계가 읽을 수 있는 정의(metric definition)를 데이터로 등록**하고 화면에서 즉시 확인할 수 있게 하는 것을 설계에 넣었습니다 (→ [08](08-platform-services.md) 6장).

- [Metrics in Clinical Data Management — SCDM 리뷰 논문 (PDF)](https://scdm.org/wp-content/uploads/2024/07/Metrics-in-Clinical-Data-Management.pdf)
- [Standardized Metrics for Better Risk Management — Avoca (WCG)](https://www.theavocagroup.com/news_events/standardized-metrics-for-better-risk-management-the-right-data-at-the-right-time/)
- [Finally, Standardized KPIs are Front and Center — Applied Clinical Trials](https://www.appliedclinicaltrialsonline.com/view/finally-standardized-kpis-are-front-and-center)
- [TransCelerate RBM Interactive Guide — Metrics](https://www.transceleratebiopharmainc.com/rbminteractiveguide/best-practices-for-implementation/metrics/)
- [Metrics in Clinical Data Management: An In-depth Guide](https://cdconnect.net/metrics-in-clinical-data-managemet/)

### 2.3 CDISC — SoA의 기계 판독 가능성

이 앱의 Expectation Engine에 직접 영향을 주는 조사 결과입니다. CDISC는 USDM(Unified Study Definitions Model)을 기반으로 프로토콜의 **Schedule of Activities(SoA)를 기계가 읽을 수 있게** 만드는 SOA Project를 진행 중입니다. 2025년 2월 시작된 CDISC 360i 이니셔티브는 2026년까지 Phase 2로 사양과 참조 구현을 만들고 있으며, SOA Workbench는 SoA를 구축해 USDM JSON으로 생성하는 참조 구현을 제공합니다. 이는 TransCelerate의 Digital Data Flow 이니셔티브와 협력 관계에 있습니다.

**시사점.** SoA는 이 앱에서 expected를 생성하는 **출발점**입니다. 지금은 SoA를 엑셀로 입력받아야 하지만, USDM JSON을 import 경로 중 하나로 설계해두면 향후 프로토콜에서 SoA를 자동으로 가져올 수 있습니다. 내부 SoA 모델을 USDM 개념(Study, StudyDesign, Encounter, Activity, Timing)에 **의도적으로 근접**시키는 것을 권고합니다.

- [CDISC Digital Data Flow (DDF)](https://www.cdisc.org/ddf)
- [CDISC 360i](https://www.cdisc.org/standards/cdisc-360i)
- [TransCelerate Digital Data Flow Initiative](https://www.transceleratebiopharmainc.com/initiatives/digital-data-flow/)
- [USDM in action – from protocol to SDTM](https://d4k.dk/2024/08/09/usdm-in-action_-from-protocol-to-sdtm/)
- [Modernization of Clinical Data Flow Leveraging CDISC 360i Standards (ACDM, PDF)](https://acdmglobal.org/wp-content/uploads/2026/01/Modernization-of-Clinical-Data-Flow.pdf)

### 2.4 21 CFR Part 11 및 GAMP 5 (2판)

21 CFR Part 11 Subpart B는 전자 기록을 생성·수정·삭제하는 조작자의 입력과 행위의 날짜와 시각을 독립적으로 기록하는 **안전하고, 컴퓨터가 생성하며, 시각이 찍힌 감사 추적**을 요구합니다. FDA Part 11은 변경과 삭제뿐 아니라 **데이터의 최초 입력(create)도 감사 추적에 기록**할 것을 요구합니다. GAMP 5 2판(2022년 7월)은 클라우드, AI/ML 검증, 애자일 개발에 대한 지침을 추가했으며, ALCOA+ 원칙의 준수가 전제입니다.

**시사점.** "Part 11 대비 설계"의 구체적 의미가 여기서 나옵니다. 지금 validation 패키지를 만들 필요는 없지만, 감사 추적 스키마는 **처음부터** 생성·수정·삭제를 모두 포착하고, append-only이며, 변경 사유를 담고, 시각을 신뢰 가능한 방식으로 기록해야 합니다. 나중에 얹을 수 없는 유일한 부분이 바로 이것입니다 (→ [08](08-platform-services.md) 3장).

- [FDA 21 CFR Part 11 Audit Trails: Definition, Requirements, and Compliance](https://simplerqms.com/21-cfr-part-11-audit-trail/)
- [21 CFR Part 11: IT Guide to Electronic Records & Signatures](https://intuitionlabs.ai/articles/21-cfr-part-11-it-compliance-guide)
- [Audit Trail Review: Regulation and Practice in GxP Environments — ISPE Pharmaceutical Engineering](https://ispe.org/pharmaceutical-engineering/march-april-2026/audit-trail-review-regulation-and-practice-gxp)
- [GAMP 5 Second Edition Explained — PSC Software](https://pscsoftware.com/gamp-5-second-edition-changing-validation/)
- [Navigating 21 CFR Part 11 Compliance: GAMP 5 and ALCOA — Cloudbyz](https://blog.cloudbyz.com/resources/navigating-21-cfr-part-11-compliance-leveraging-gamp-5-and-alcoa-principles-for-robust-electronic-records-and-signatures-management)

## 3. 기술 참조

Python 기반 엔터프라이즈 내부 앱에서 SSO, RBAC, 감사 로깅을 구현하는 패턴을 확인했습니다. FastAPI 계열에서는 감사 추적을 위한 플러그인과 미들웨어 패턴이 존재하며, FastAPI + React 조합의 RBAC 참조 구현도 공개되어 있습니다. 구체적 비교와 권고는 [09](09-tech-stack.md)에서 다룹니다.

- [FastAPI Enterprise Basics: SSO, RBAC, and Auditing](https://www.squash.io/implementing-fastapi-enterprise-functionalities-sso-rbac-and-auditing/)
- [fastapi_rbac 참조 구현 (GitHub)](https://github.com/mnaimfaizy/fastapi_rbac)
- [Django REST Framework vs FastAPI 비교](https://medium.com/django-unleashed/django-rest-framework-vs-fastapi-a-comprehensive-comparison-for-modern-web-apis-in-2024-8d977082c780)

## 4. 벤치마크 종합: 이 앱의 포지셔닝

조사를 종합하면 시장의 빈자리는 분명합니다.

| 도구 유형 | 잘하는 것 | 비워둔 자리 |
|---|---|---|
| EDC / CTMS 대시보드 | 이미 들어온 것의 집계, 실시간 표시 | **분모(expected)를 생성하지 않음**, 단일 시스템 범위 |
| Veeva CDB 류 데이터 허브 | 다중 소스 집계와 정제 | 목적이 데이터 품질이지 **진척 예측이 아님** |
| RBQM 플랫폼 | KRI/QTL, 통계적 이상 탐지 | 운영 backlog의 **일상적 추적과 예측**은 대상이 아님 |
| 엑셀 수작업 | 유연함, 즉시 시작 가능 | 재현 불가, 감사 추적 없음, 도메인 간 단절, 확장 불가 |

> **포지셔닝.** 이 앱은 EDC 대시보드와 RBQM 플랫폼 사이의 **운영 예측 계층(operational forecasting layer)** 입니다. 여러 소스를 가로질러 expected를 생성하고, 실적과 대조하며, 언제 해소되는지를 예측하는 것이 고유 영역입니다.

## 5. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-01-1 | 사내에 이미 쓰는 상용 도구(Veeva CDB, CluePoints 등)가 있는가. 있다면 중복 영역을 조정해야 함 | 없다고 전제 |
| DP-01-2 | 2.3의 USDM/SoA 호환을 초기부터 고려할 것인가 | **개념만 정렬**, import는 후속 단계 |
| DP-01-3 | 사내 표준 KPI 정의서가 이미 있는가 | 있다면 2.2의 metric definition 등록부에 그대로 수록 |
| DP-01-4 | 이 앱의 지표를 KRI로 승격시켜 RBQM으로 확장하는 것을 로드맵에 포함할 것인가 | **포함** (Phase 3) |
