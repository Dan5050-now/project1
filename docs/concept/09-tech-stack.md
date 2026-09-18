# 09. 기술 스택 권고

요구사항 C1은 Python 개발을 지정했습니다. 이 문서는 Python 생태계 안에서 선택지를 비교하고 **하나의 권고안**을 제시합니다.

## 1. 선택 기준

기술 선택은 요구사항에서 직접 도출합니다. 다음 여섯 가지가 판단 기준입니다.

| # | 기준 | 출처 |
|---|---|---|
| K1 | 다중 사용자 동시 접근, 세밀한 RBAC, 관리자 화면 | C2 |
| K2 | 모든 데이터 변경의 감사 추적 | C3 |
| K3 | 레코드 수준 버전 관리 | C4 |
| K4 | 대량 import/export | C5, C6 |
| K5 | 개발 속도 — 개념 검증 단계에서 중요 | 프로젝트 성격 |
| K6 | Part 11 validation으로 승격 가능성 | 확정 전제 |
| K7 | **표준 template 기반 대량 검증 처리** | 검토 반영 (요구사항 7, 8) |
| K8 | **AI 통합 지점의 격리 가능성** | 검토 반영 (요구사항 9, 10) |

## 2. 선택지 비교

### 2.1 옵션 A — Streamlit (또는 Dash) 중심

데이터 앱을 빠르게 만드는 접근입니다.

**장점.** 개발 속도가 압도적입니다. Python만으로 화면까지 만들 수 있어 초기 프로토타입을 며칠 만에 볼 수 있습니다.

**단점.** 치명적인 것이 여럿입니다. 인증과 RBAC가 프레임워크 차원에서 제공되지 않아 직접 구현해야 하고, 그 구현은 보안적으로 취약해지기 쉽습니다. 세밀한 권한 제어(모듈 × 접근수준 × 데이터범위)를 화면 조건문으로 처리하게 되어 유지보수가 무너집니다. 쓰기 작업이 많은 화면(SDV 계획 편집, 타임라인 관리)에는 적합하지 않습니다. 동시 편집 제어가 없습니다.

**판정.** K1, K2, K6에서 부적합. **프로토타입 용도로만 적합**합니다.

### 2.2 옵션 B — Django + Django REST Framework

풀스택 프레임워크 접근입니다.

**장점.** 요구사항과의 정합성이 두드러집니다.

| 요구사항 | Django의 대응 |
|---|---|
| C2 사용자·역할 관리 | 내장 auth 시스템 + admin. 관리자 화면을 거의 무료로 얻음 |
| C2 객체 수준 권한 | `django-guardian`으로 시험·사이트 범위 제한 |
| C3 감사 추적 | `django-simple-history`, `django-auditlog` — **모델에 한 줄 추가로 전 변경 이력 기록** |
| C4 버전 관리 | 위 라이브러리가 레코드 이력을 그대로 제공 |
| C5 import/export | `django-import-export` — 템플릿, 미리보기, 검증이 이미 구현됨 |
| K6 마이그레이션 관리 | 내장 migration이 스키마 변경 이력을 남김 (validation 시 유용) |

즉 [08](08-platform-services.md)에서 정의한 플랫폼 서비스의 **상당 부분이 이미 만들어져 있습니다**. 이것이 이 프로젝트에서 갖는 의미는 큽니다. 플랫폼 기능을 직접 만드는 데 쓸 몇 달을 업무 로직에 쓸 수 있습니다.

**단점.** 대시보드 중심 UI를 만들려면 프론트엔드 작업이 별도로 필요합니다. 비동기 처리는 FastAPI보다 약합니다(다만 이 앱은 대량 배치가 주이고 고동시성 API가 아니므로 문제되지 않습니다).

### 2.3 옵션 C — FastAPI + SQLAlchemy + React

API 중심 접근입니다.

**장점.** API 설계 자유도가 높고 성능이 좋습니다. 프론트엔드를 완전히 분리할 수 있습니다.

**단점.** 인증, 권한, 감사 추적, 관리자 화면, import/export를 **전부 직접 만들어야 합니다**. 벤치마크에서 확인한 참조 구현들이 존재하지만, 그것들을 조합하고 검증하는 작업 자체가 상당합니다. 개념 검증 단계에서 이 비용은 정당화하기 어렵습니다.

## 3. 권고안

> ### **Django + Django REST Framework + PostgreSQL을 채택합니다.**

### 3.1 근거

판단은 명확합니다. **이 앱의 어려움은 화면이 아니라 플랫폼 요구사항(C2~C6)에 있습니다.** 그런데 그 요구사항들은 Django 생태계가 이미 성숙하게 해결해 둔 문제입니다. `django-simple-history` 한 줄로 얻는 감사 추적을 FastAPI에서 직접 만들면 몇 주가 걸리고, 그렇게 만든 것이 더 낫다는 보장도 없습니다.

Streamlit은 빠르지만 K1·K2·K6에서 벽에 부딪히고, 그 벽은 나중에 우회할 수 없어 재작성으로 이어집니다. FastAPI는 훌륭하지만 이 프로젝트가 API 성능 문제를 겪을 가능성은 낮은 반면, 플랫폼 기능을 직접 만드는 비용은 확실히 발생합니다.

### 3.2 전체 스택

| 계층 | 선택 | 근거 |
|---|---|---|
| 언어 | Python 3.12+ | 요구사항 C1 |
| 웹 프레임워크 | **Django 5.x** | 위 근거 |
| API | **Django REST Framework** | 외부 BI 연동(C6), 향후 프론트엔드 교체 대비 |
| DB | **PostgreSQL 16+** | JSONB(도메인 확장 속성), 파티셔닝, 윈도우 함수, 시계열 처리 |
| 배치·비동기 | **Celery + Redis** | 대량 import, Expectation Engine 재생성, 스냅샷 생성 |
| 계산 엔진 | **pandas / Polars** | 매칭과 집계. Polars는 대용량 시 검토 |
| 프론트엔드 (MVP) | **Django 템플릿 + HTMX + Alpine.js** | 별도 빌드 없이 서버 렌더링. 개발 속도 |
| 차트 | **Plotly** 또는 **ECharts** | 인터랙티브 드릴다운 지원 |
| 인증 | **SSO (SAML/OIDC)** + django-allauth | 사내 통합 |
| 권한 | django 내장 + **django-guardian** | 객체 수준 범위 제한 |
| 감사 추적 | **django-simple-history** | C3, C4 |
| Import/Export | **django-import-export** + openpyxl + pandas | C5, K7 |
| 검증 규칙 엔진 | **pandera** 또는 자체 규칙 레지스트리 | K7 — [12](12-standard-source-templates.md) 5장 |
| 분석 export | **Parquet (pyarrow)** + 읽기 전용 뷰 | C6 |
| AI Gateway | 자체 모듈 + 제공자 어댑터 | K8 — [14](14-ai-extensibility.md) 4장 |
| 테스트 | pytest + factory_boy | |
| 배포 | Docker + docker-compose | 재현 가능한 환경 (validation 대비) |

### 3.3 프론트엔드에 대한 결정

MVP는 **Django 템플릿 + HTMX**로 시작합니다. 이유는 개발 속도이며, 이 앱의 화면 대부분이 테이블과 드릴다운이라 HTMX로 충분하기 때문입니다.

다만 **DRF API를 처음부터 함께 만듭니다.** 나중에 React로 전환하고 싶어질 때 백엔드를 그대로 두고 프론트엔드만 교체할 수 있습니다. 이 결정이 초기에 약간의 추가 비용을 요구하지만, 되돌릴 수 없는 선택을 피하게 해줍니다.

### 3.4 아키텍처 개요

```
┌──────────────────────────────────────────────────────────┐
│  브라우저                                                 │
│  Django Templates + HTMX + Plotly                         │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│  Django                                                   │
│  ┌──────────┬──────────┬──────────┬──────────┐           │
│  │ Views    │ DRF API  │ Admin    │ Auth/RBAC│           │
│  └──────────┴──────────┴──────────┴──────────┘           │
│  ┌────────────────────────────────────────────┐          │
│  │ 도메인 서비스 (결정론 영역)                   │          │
│  │  ExpectationEngine · ProgressEngine         │          │
│  │  ReconciliationService · ForecastService    │          │
│  │  ValidationEngine · MetricEngine            │          │
│  └────────────────────────────────────────────┘          │
│  ┌────────────────────────────────────────────┐          │
│  │ AI Gateway (선택적 · 없어도 동작)             │          │
│  │  권한 검사 · Tool API · 제공자 어댑터         │          │
│  └────────────────────────────────────────────┘          │
│  ┌────────────────────────────────────────────┐          │
│  │ 모델 (django-simple-history 적용)            │          │
│  └────────────────────────────────────────────┘          │
└──────┬──────────────────────────────┬────────────────────┘
       │                              │
┌──────▼──────────┐         ┌─────────▼──────────┐
│  PostgreSQL     │         │  Celery + Redis    │
│  운영 스키마     │         │  import · 엔진 실행 │
│  분석 스키마     │         │  스냅샷 생성        │
│  (BI 읽기 전용) │         └────────────────────┘
└─────────────────┘
```

### 3.5 모듈 구조 (초안)

```
project/
├── core/              공통: 감사, 권한, 스냅샷, 버전
├── ingestion/         SourceSystem, Feed, MappingProfile, DataDrop
├── master/            Trial, Country, Site, Subject, Visit, CodeList
├── assumptions/       AssumptionSet, SoA, VisitSchedule
├── config/            TrialConfig, StageSetting, ScopeRule, TargetList  ← 요구사항 8
├── templates/         SourceTemplate, 검증 규칙 레지스트리            ← 요구사항 7
├── tracking/          ExpectationItem, StageStatus, Issue, Discrepancy
│   ├── engines/       ExpectationEngine, ProgressEngine, Reconciliation
│   └── domains/       edc.py, sample.py, image.py, visit.py  ← 도메인 어댑터
├── planning/          SDVVisit, Milestone, TimelineTask
├── analytics/         MetricFact, MetricDefinition, MetricEngine, Forecast
├── exports/           CSV/Excel/Parquet, BI 뷰
├── ai/                Gateway, ToolAPI, TaskRegistry, ProviderAdapter   ← 요구사항 9
└── adminpanel/        사용자·역할 관리, 감사 조회, AI 활동 조회
```

`ai/`가 **독립 모듈로 분리된 것이 핵심**입니다. 이 디렉터리를 통째로 제거해도 나머지 앱은 정상 동작합니다 ([14](14-ai-extensibility.md) 원칙 1.1). 규제 관점에서 "AI가 관여한 범위"를 코드 경계로도 설명할 수 있게 됩니다.

`config/`와 `templates/`가 별도 모듈인 것도 의도적입니다. 시험마다 달라지는 것을 코드가 아니라 **데이터로 다루기** 위한 구조입니다.

`tracking/domains/` 아래 네 개 파일이 [03](03-core-concept-model.md) 1장의 아키타입 설계가 코드로 나타난 모습입니다. 각 파일은 단계 체인 정의, Due 규칙, 매칭 키만 선언하고 계산 로직은 `engines/`가 공통으로 처리합니다.

## 4. 배제한 선택지와 이유

| 선택지 | 배제 이유 |
|---|---|
| Streamlit 단독 | RBAC·감사·동시성 요구를 만족 못 함 (2.1) |
| FastAPI 단독 | 플랫폼 기능 자체 구현 비용이 이 단계에서 정당화 안 됨 (2.3) |
| NoSQL (MongoDB 등) | 집계·조인 중심 워크로드, 트랜잭션 일관성 요구에 부적합 |
| 저코드 플랫폼 | 도메인 로직(Expectation Engine)의 복잡도를 감당 못 함 |
| 데이터 웨어하우스 우선 (dbt 등) | 쓰기 작업과 워크플로가 있는 앱이므로 OLTP가 먼저 필요 |

## 5. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-09-1 | **Django 권고안 채택 여부** | 채택 |
| DP-09-2 | 사내 IT가 허용하는 기술 스택 제약이 있는가 | 확인 필요 |
| DP-09-3 | 배포 환경 — 사내 서버인가 클라우드인가 | 확인 필요 (validation 범위에 영향) |
| DP-09-4 | 3.3의 HTMX 시작 + DRF 병행 전략에 동의하는가 | 동의 권고 |
| DP-09-5 | 개발 인력 규모와 Python/Django 숙련도 | 확인 필요 |
| DP-09-6 | 검증 규칙 엔진을 라이브러리로 쓸 것인가 자체 구현할 것인가 | 자체 레지스트리 권고 (AI 확장 대비) |
| DP-09-7 | AI 제공자를 외부 서비스로 할 것인가 온프레미스로 할 것인가 | **DP-14-3 결정에 종속** |
