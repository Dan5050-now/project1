# Clinical Trial Progress Management App

임상시험의 데이터, 검체, 영상, SDV, 프로젝트 타임라인 진척을 **예측하고 추적**하는 통합 관리 앱입니다.

여러 시스템에 흩어진 "실제로 들어온 것"을 모으는 데 그치지 않고, 프로토콜 가정과 RTSM 실적에서 **"들어왔어야 하는 것"을 생성**하여 둘을 대조하는 것이 이 앱의 핵심입니다.

## 현재 상태

**상세 사양 단계.** 구현 코드는 아직 없습니다.

| 단계 | 산출물 | 상태 |
|---|---|---|
| 개념 설계 | [`docs/concept/`](docs/concept/README.md) | 완료 (구조 결정 확정) |
| 상세 사양 | [`docs/spec/`](docs/spec/README.md) | **Phase 0 + Phase 1 범위 작성 완료** |
| 구현 | — | 미착수 |

사양은 Phase 0(기반)과 Phase 1(엔진 검증)만 다룹니다. Phase 2 이후는 엔진이 실제 시험 데이터로 검증된 뒤에 작성합니다.

## 다루는 범위

| 도메인 | 집계 레벨 |
|---|---|
| EDC 데이터 진척 (입력 → SDV·리뷰·코딩·freeze·서명 병행 → lock) | trial / country / site / subject |
| RTSM 시험 현황 (피험자 상태, 층화, 방문 윈도우 준수) | trial / country / site / subject |
| SDV 방문 계획 관리 (계획·실적·CRA 리소스·적정성 평가) | trial / country / site |
| 검체 진척 관리 (채취 → 배송 → 도착 → 대조 → 분석) | trial / country / site / subject |
| 영상 진척 관리 (획득 → 업로드 → QC → 배정 → 판독) | trial / country / site / subject |
| 프로젝트 타임라인 (마일스톤, 상세 task) | trial |

## 문서

시작점은 [`docs/concept/README.md`](docs/concept/README.md)입니다.

구현 사양은 [`docs/spec/README.md`](docs/spec/README.md)에서 시작하며, [golden dataset](docs/spec/golden/)이 사양의 검증 기준입니다.

핵심 설계를 빠르게 파악하려면 [`03-core-concept-model.md`](docs/concept/03-core-concept-model.md)를 먼저 보시면 됩니다. 여섯 도메인을 네 개의 아키타입으로 정리한 문서이며, 나머지 문서는 모두 그 개념의 적용입니다.

앱이 특정 EDC나 특정 시험 설계에 종속되지 않도록, 데이터는 [표준 template](docs/concept/12-standard-source-templates.md)으로 받고 시험마다 달라지는 것은 [설정](docs/concept/13-trial-configuration.md)으로 받습니다. 입력 경계는 vendor 원본 파일이 아니라 vendor data로 사내에서 이미 만들고 있는 표준 파일(external data reconciliation file 등)입니다. 모든 계산식은 [지표 명세](docs/concept/15-metric-specification.md)에 재현 가능한 형태로 정의됩니다.
