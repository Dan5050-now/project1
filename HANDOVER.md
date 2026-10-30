# 인수 인계 — 사내 PC에서 개발 이어가기

이 문서는 현재까지의 산출물과 다음 작업을 사내 PC에서 이어가기 위한 안내입니다.

작성 시점의 최신 커밋은 `7599cae`이며, 브랜치는 `claude/clinical-trial-progress-app-1166ci`입니다.

## 1. 가져오는 방법

### 1.1 GitHub 접근이 가능한 경우 (권장)

```bash
git clone https://github.com/Dan5050-now/project1.git
cd project1
git checkout claude/clinical-trial-progress-app-1166ci
```

### 1.2 사내망에서 GitHub 접근이 막힌 경우

전달받은 압축 파일을 풀면 **`.git` 이력까지 그대로** 들어 있습니다.

```bash
unzip project1-handover.zip
cd project1
git log --oneline        # 11개 커밋 확인
git status               # clean 이어야 함
```

이후 사내 Git 서버로 옮기실 때는 원격만 바꾸시면 됩니다.

```bash
git remote set-url origin <사내 Git 저장소 URL>
git push -u origin claude/clinical-trial-progress-app-1166ci
```

## 2. 산출물 구성

파일 49개, 문서 27개입니다. 코드는 아직 없습니다.

```
README.md                       프로젝트 개요
HANDOVER.md                     이 문서

docs/concept/                   개념 설계 (확정)
├── README.md                   문서 지도 + 확정된 전제 + 개정 이력
├── 00~11                       비전·벤치마크·핵심 모델·도메인·IA·데이터모델·
│                               예측·플랫폼·기술스택·로드맵·리스크
├── 12~16                       표준 template·시험 설정·AI 확장·지표 명세·
│                               external data 형식 초안
└── templates/                  실물 양식 (Excel에서 열림)
    ├── DTS_VARIABLE_REQUEST_v0.2.csv        vendor DTS 협의용
    ├── EXT_SAMPLE_RECON_v0.1.csv            샘플 대조 형식 예시
    ├── EXT_IMAGE_RECON_v0.1.csv             영상 대조 형식 예시
    ├── TRANSFER_HEADER_v0.1.csv             전송 메타데이터
    ├── CFG10_WAIVER_RULE_WORKSHEET_v0.1.csv 예외 규칙 확정용 ← 기입 대기
    └── CFG10_STAGE_REFERENCE_v0.1.csv       단계 코드 참조표

docs/spec/                      상세 사양 (Phase 0 + Phase 1)
├── README.md                   범위 + 확정 전제 + 개정 이력
├── 01 범위와 전제              미결 항목에 취한 전제 8건
├── 02 물리 데이터 모델         테이블·제약·인덱스·파티셔닝
├── 03 엔진 사양                Expectation·Progress·Rollup 알고리즘
├── 04 유입 사양                업로드 파이프라인, 검증 규칙 30여 개
├── 05 API 사양                 REST 엔드포인트
├── 06 화면 사양                화면별 요소와 동작
├── 07 권한·감사 사양           RBAC, 마스킹, 감사 추적
├── 08 테스트 계획              계층별 전략, 인수 판정 기준
└── golden/                     실행 가능한 검증 데이터
    ├── README.md               경계 조건 14개 설명
    ├── input/                  설정 7개 + 표준 dataset 4개
    └── expected/               항목 상태·지표·검증 결과 기대값
```

## 3. 읽는 순서

처음 보는 사람에게 권하는 순서입니다.

| 순서 | 문서 | 이유 |
|---|---|---|
| 1 | [`docs/concept/03`](docs/concept/03-core-concept-model.md) | 여섯 도메인을 네 아키타입으로 정리한 문서. 나머지는 모두 이것의 적용 |
| 2 | [`docs/spec/02`](docs/spec/02-data-model.md) 1장 | 모델링 결정 5개. 되돌리기 어려운 것들 |
| 3 | [`docs/spec/03`](docs/spec/03-engine-spec.md) 3.2 | 상태 판정 알고리즘. 순서가 결과를 바꿈 |
| 4 | [`docs/spec/golden/README.md`](docs/spec/golden/README.md) | 사양이 실제로 어떤 숫자를 내야 하는지 |
| 5 | [`docs/concept/11`](docs/concept/11-risks-and-open-questions.md) 3~4장 | 확정된 결정과 남은 결정 |

## 4. 개발 환경

[`docs/spec/README.md`](docs/spec/README.md)와 [`docs/concept/09`](docs/concept/09-tech-stack.md)에서 확정된 스택입니다.

### 4.1 필요한 것

| 구분 | 버전 | 용도 |
|---|---|---|
| Python | 3.12+ | |
| PostgreSQL | 16+ | JSONB, 선언적 파티셔닝, 윈도우 함수 |
| Redis | 7+ | Celery 브로커 |
| Node.js | — | **불필요.** MVP는 서버 렌더링 |

### 4.2 주요 패키지

```
django>=5.0
djangorestframework
django-guardian              객체 수준 권한
django-simple-history        감사 추적·버전
django-import-export         대량 import
django-allauth               SSO (OIDC/SAML)
celery[redis]
psycopg[binary]
pandas                       매칭·집계
openpyxl                     Excel 입출력
pyarrow                      Parquet export
plotly                       차트
pytest, pytest-django, factory_boy
ruff, black, mypy
```

### 4.3 사내 환경에서 확인이 필요한 것

| # | 항목 | 사양 참조 |
|---|---|---|
| A-8 | SSO 프로토콜 (OIDC / SAML) — 미확정 동안 자체 계정으로 개발 가능 | [01](docs/spec/01-scope-and-assumptions.md) 2장 |
| DP-09-2 | 사내 IT의 기술 스택 제약 | [09](docs/concept/09-tech-stack.md) 5장 |
| DP-09-3 | 배포 환경 (사내 서버 / 클라우드) | 동일 |
| DP-08-5 | 외부 BI 도구의 읽기 전용 DB 연결 허용 여부 | [08](docs/concept/08-platform-services.md) 8장 |
| DP-14-7 | 내부 LLM 연결·인증 방식 (Phase 3부터 필요) | [14](docs/concept/14-ai-extensibility.md) 8장 |

## 5. 다음 작업

### 5.1 바로 시작할 수 있는 것 — Phase 0

[`docs/spec/01`](docs/spec/01-scope-and-assumptions.md) 1.1의 F0-1 ~ F0-9입니다. 미결 항목에 막히지 않는 순서로 적었습니다.

```
1. 프로젝트 골격          docs/spec/09 3.5의 모듈 구조
2. 마스터 데이터 모델     docs/spec/02 2장
3. 감사 추적              docs/spec/07 3장  ← 나중에 얹을 수 없음
4. RBAC + 관리자 화면     docs/spec/07 2장  ← 나중에 얹을 수 없음
5. 업로드 파이프라인      docs/spec/04
6. 스냅샷·버전            docs/spec/02 1.2
```

3번과 4번을 먼저 하는 이유는 [`docs/spec/01`](docs/spec/01-scope-and-assumptions.md) 3장에 있습니다. 감사 추적의 행위자 구분과 권한 모델은 **기능을 먼저 만들고 나중에 얹을 수 없습니다.**

### 5.2 Phase 0에서 함께 만들 것

```
golden dataset 테스트 하네스    docs/spec/08 2장
  → Phase 1 엔진을 구현하기 전에 테스트가 먼저 돌아야 합니다
  → docs/spec/golden/ 의 input 을 적재하고 expected 와 대조하는 코드
```

### 5.3 결정 대기 중인 항목

개발을 막지는 않지만, Phase 1 전에 확정되어야 합니다.

| # | 항목 | 양식·문서 |
|---|---|---|
| **S-02-6** | `CFG10` 이슈 유형별 예외 범위 (Phase 1은 QUERY 15개만) | [`templates/CFG10_WAIVER_RULE_WORKSHEET_v0.1.csv`](docs/concept/templates/CFG10_WAIVER_RULE_WORKSHEET_v0.1.csv) |
| **S-02-8** | `unresolvable` 판정을 앱에서 할 것인가 파일 컬럼으로 받을 것인가 | [`templates/README.md`](docs/concept/templates/README.md) 7.1 |
| DP-16-7 | DTS 협의 worksheet를 표준 절차에 넣을 것인가 | [`templates/DTS_VARIABLE_REQUEST_v0.2.csv`](docs/concept/templates/DTS_VARIABLE_REQUEST_v0.2.csv) |
| DP-12-7 | 사내 external data recon file 샘플로 형식 확정 | [16](docs/concept/16-external-data-format-draft.md) |
| DP-10-3 | Phase 1 인수 테스트 대상 시험 선정 | [10](docs/concept/10-mvp-and-roadmap.md) 9장 |

**S-02-8은 문서 3개가 불일치한 상태**입니다. 결정 후 일치시켜야 합니다.

### 5.4 검토가 남은 사양

| 문서 | 상태 |
|---|---|
| 01~03 | 검토 완료, 반영됨 |
| 04~08 | **미검토** |

## 6. 작업 규칙

이어서 작업하실 때 지켜야 할 것들입니다. 지금까지 이 규칙으로 작성했습니다.

| 규칙 | 근거 |
|---|---|
| 개념과 사양이 충돌하면 **개념이 우선**하고 사양을 고친다 | [`docs/spec/README.md`](docs/spec/README.md) 3장 |
| 사양 항목에는 **근거가 되는 개념 문서의 절 번호**를 단다 | 동일 |
| golden 기대값이 틀렸다고 판단되면 **코드에 맞추지 않고** 어느 쪽이 옳은지 먼저 판정한다 | [`golden/README.md`](docs/spec/golden/README.md) 6장 |
| 계산식이 바뀌면 `metric_definition` 버전을 올리고 과거 스냅샷은 과거 정의를 유지한다 | [15](docs/concept/15-metric-specification.md) 7.3 |
| 알 수 없는 값은 **추정하지 않는다** | [15](docs/concept/15-metric-specification.md) 3.3b |
| 계산 불가가 된 지표는 0%나 N/A로 표시하지 않고 **화면에서 제외**하고 사유를 남긴다 | [16](docs/concept/16-external-data-format-draft.md) 2.3 |

## 7. 핵심 설계 결정 요약

사양을 읽기 전에 알아두면 좋은 것들입니다. 상세는 각 문서에 있습니다.

| 결정 | 내용 |
|---|---|
| 아키타입 | 여섯 도메인이 네 패턴으로 수렴. 하나의 메트릭 커널 + 도메인 어댑터 |
| 분모 기준 | Due 기본. Protocol·Forecast도 저장하고 토글 전환 |
| 예외 상태 | `WAIVED` 단일. 분모 제외. 차단 범위는 이슈 유형별 규칙 |
| EDC 단계 | 입력 후 SDV·리뷰·코딩·freeze·서명 **병행** → lock |
| investigator sign | 유예 기간 없음. 미서명 건수만, 전체/SAE 구분 |
| 입력 경계 | vendor 원본이 아니라 **사내 표준 파일** |
| 대조 판정 | 파일의 판정을 수입하지 않고 **앱이 양측 원시값으로 자체 판정** |
| 사이트 이전 | 피험자 **전 항목이 새 사이트로 이동**. 미종결 시 경고 |
| AI | 보조 수단. **보고되는 숫자를 계산하지 않음.** 내부 LLM 연결 |
| 값의 추정 | 하지 않음 |
