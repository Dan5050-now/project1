# 12. 표준 Source Dataset Template

*검토 반영 신규 문서 (요구사항 7)*
*v2: 앱의 입력 경계를 vendor 원본 파일이 아니라 **vendor data로 만든 사내 표준 파일**로 확정 (DP-12-6)*
*v2.1: 결합형 파일의 실제 형식 초안을 [16](16-external-data-format-draft.md)로 분리. 양측 원시값 포함이 확정됨 (DP-12-8)*

## 1. 왜 표준 template인가

### 1.1 문제

시험마다 EDC 종류가 다르고, 같은 EDC라도 시험마다 리포트 구조가 다르며, vendor마다 컬럼명과 코드값이 제각각입니다. 이 상태에서 앱이 **특정 시스템이나 특정 시험 설계를 전제로 개발되면**, 다른 시험에는 쓸 수 없거나 시험마다 코드를 고쳐야 합니다. 그러면 앱의 수명은 첫 시험과 함께 끝납니다.

### 1.2 해결 방향 — 앱의 입력 경계 (DP-12-6 확정)

**앱은 vendor 원본 파일을 직접 받지 않습니다. vendor data를 이용해 사내에서 이미 만들고 있는 표준 파일을 입력으로 삼습니다.** external data reconciliation file이 대표적인 예입니다.

```
  vendor 원본 파일                    사내 표준화 작업                앱
  ────────────────                   ──────────────────            ──────
  Central lab CSV      ──┐
  Bioanalytics 리포트  ──┼──> [DM·vendor 관리자가          ──> ┌──────────────┐
  BICR vendor 리포트   ──┤     external data recon file      │ 표준 Source  │
  EDC 추출             ──┘     등 표준 파일로 정리]           │  Template    │
  RTSM 추출            ──┘                                    └──────┬───────┘
                                    ▲                                ▼
                            앱의 경계 밖                    처리 코드는 하나
```

이 결정이 갖는 의미는 큽니다.

| 항목 | 효과 |
|---|---|
| **vendor 형식 변동의 흡수** | vendor가 리포트 형식을 바꿔도 앱은 영향을 받지 않습니다. 표준화 단계에서 흡수됩니다 |
| **기존 업무와의 정합** | 이미 만들고 있는 파일을 재사용하므로 신규 작업이 거의 추가되지 않습니다 |
| **template 설계의 기준** | 표준 template은 이론적 이상형이 아니라 **사내 표준 파일의 실제 구조에 맞춰** 설계합니다 |
| **부담의 이동** | 변환 부담이 앱 사용자가 아니라 이미 그 일을 하고 있는 담당자에게 남습니다 |

반면 대가도 있습니다. **vendor 원본에서 표준 파일이 만들어지는 과정이 앱의 시야 밖에 있습니다.** 표준화 과정에서 누락이나 오류가 생기면 앱은 그것을 알 수 없습니다. 이에 대한 대응이 1.3의 출처 메타데이터와 5장의 검증입니다.

### 1.3 앱 밖에서 일어나는 일을 기록한다

표준화가 앱 경계 밖에서 일어나므로, **어느 vendor 데이터로 언제 누가 만든 파일인지**를 파일 자체가 지니고 들어와야 합니다. 이것이 없으면 나중에 "이 숫자의 출처가 무엇인가"에 답할 수 없고, GCP와 computerised system validation 관점의 추적성도 끊깁니다.

모든 업로드는 **출처 메타데이터(provenance)** 를 함께 제출합니다 (2.3).

### 1.4 남는 변환 부담과 그 완화

표준 파일을 쓰더라도 앱의 template과 완전히 같지는 않을 수 있습니다. 남는 차이는 다음으로 흡수합니다.

| 장치 | 내용 |
|---|---|
| Template 배포 | 컬럼 설명, 자료형, 허용값, 예시 행이 포함된 Excel/CSV 파일 |
| Mapping Profile | 사내 표준 파일의 컬럼명을 앱 표준 컬럼에 연결하는 매핑을 저장 ([08](08-platform-services.md) 5.2). **한 번 설정하면 이후 사내 표준 파일을 그대로 업로드** |
| 검증 리포트 | 업로드 즉시 원본 행 번호와 함께 오류 지점 표시 |
| AI 보조 | 내부 LLM이 매핑과 점검을 보조 ([14](14-ai-extensibility.md)) |

> **설계 원칙 (검토 반영).** 사내에 표준 DTS가 없고 시험마다 vendor와 새로 셋업하므로, 앱 template은 **따라가는 대상이 아니라 DTS 협의에 들고 들어가는 sponsor 측 기준안**입니다. 협의용 worksheet와 우선순위 구분은 [16](16-external-data-format-draft.md) 2.2에 있습니다.

## 2. 공통 규약

모든 template에 적용되는 규칙입니다.

| 항목 | 규약 |
|---|---|
| 파일 형식 | CSV (UTF-8, BOM 허용) 또는 Excel (.xlsx) |
| 헤더 | 1행이 컬럼명. 표준 컬럼명은 **대문자 영문 + 언더스코어** |
| 날짜 | **ISO 8601** `YYYY-MM-DD`. 시각 포함 시 `YYYY-MM-DDThh:mm:ss` |
| 시간대 | 명시 없으면 시험 기준 시간대. 설정에서 지정 |
| 결측 | 빈 문자열. `NA`, `.`, `NULL` 등은 결측으로 해석하되 경고 |
| 부분 날짜 | `YYYY-MM` 또는 `YYYY` 허용. 기한 계산 시 처리 규칙은 [15](15-metric-specification.md) |
| Boolean | `Y` / `N` (대소문자 무관). `1`/`0`, `TRUE`/`FALSE`도 허용하되 경고 |
| 행 단위 | template마다 명시 (예: DS03은 폼 인스턴스 1건 = 1행) |
| 파일명 | `<TRIAL>_<DATASET>_<YYYYMMDD>.csv` 권고. 강제는 아님 |
| 추가 컬럼 | 표준에 없는 컬럼은 **무시하되 목록을 보고**. 삭제하지 않고 원본 Data Drop에 보존 |

### 2.1 매칭 키 선언 (필수)

각 업로드에는 **매칭 키 선언**이 반드시 포함됩니다. [03](03-core-concept-model.md) 5.1에서 정의한 대로, 매칭 키 입도가 소스보다 거칠면 reconciliation 판정이 조용히 틀리기 때문입니다.

선언은 Feed 설정에 저장되며 업로드마다 재입력할 필요가 없습니다. 다만 **입도가 권고 수준에 미달하면 경고가 표시되고 해당 Feed의 reconciliation이 "신뢰도 낮음"으로 표시**됩니다.

### 2.2 출처 메타데이터 (필수)

표준화가 앱 밖에서 일어나므로(1.3), 모든 업로드는 다음을 함께 제출합니다. 파일 내 별도 시트나 업로드 화면 입력 중 하나로 받습니다.

| 항목 | 필수 | 설명 |
|---|---|---|
| `SRC_SYSTEM` | ● | 원본 시스템·vendor (예: `CentralLab-A`, `Rave`, `BICR-B`) |
| `SRC_EXTRACT_DT` | ● | **vendor 원본 데이터의 추출 기준일.** 파일 작성일이 아님 |
| `SRC_FILE_REF` | | 원본 파일명 또는 사내 관리 번호 |
| `PREPARED_BY` | ● | 표준 파일을 만든 사람 |
| `PREPARED_DT` | ● | 표준 파일 작성일 |
| `TEMPLATE_VERSION` | ● | 사용한 template 버전 |
| `PERIOD_FROM` / `PERIOD_TO` | | 데이터 대상 기간 |
| `NOTE` | | 부분 추출 등 특이사항 |

`SRC_EXTRACT_DT`와 `PREPARED_DT`를 분리한 것이 중요합니다. **지표의 시간 기준은 원본 추출 시점**이지 파일을 만든 시점이 아닙니다. 둘이 며칠 벌어지면 "최신 데이터"의 의미가 달라집니다.

이 메타데이터는 Data Drop에 저장되어 화면과 export에 함께 표시됩니다. 스냅샷 좌표 옆에 `central lab 추출 2026-09-12`처럼 나타납니다.

### 2.3 식별자 규약

| 컬럼 | 의미 | 비고 |
|---|---|---|
| `STUDYID` | 시험 식별자 | 모든 dataset 공통 필수 |
| `SITEID` | 사이트 식별자 | 시험 내 유일 |
| `SUBJID` | 피험자 번호 | **시험 내 유일**해야 함 |
| `VISITID` | 방문 식별 코드 | SoA의 방문 코드와 일치해야 함 |
| `VISITNAME` | 방문 표시명 | 화면 표시용 |

`SUBJID`와 `VISITID`의 값이 dataset 간에 **정확히 일치**해야 매칭이 성립합니다. 이것이 업로드 검증의 1순위 점검 항목입니다.

## 3. 표준 Dataset 목록

### 3.1 두 가지 입력 형태

사내 표준 파일은 두 가지 형태 중 하나입니다. 앱은 **둘 다 받습니다.**

| 형태 | 구조 | 대표 예 |
|---|---|---|
| **결합형 (joined)** | 한 행에 EDC측과 vendor측 값이 **나란히** 들어 있음 | **external data reconciliation file** |
| 분리형 (separate) | 소스별로 파일이 나뉘어 있고 앱이 매칭 | vendor 리포트를 소스별로 정리한 파일 |

DP-12-6 확정에 따라 **결합형이 기본**입니다. 이미 만들고 있는 external data reconciliation file을 그대로 쓰는 것이 이 결정의 취지이기 때문입니다.

### 3.2 결합형 파일을 받을 때의 핵심 규칙

결합형 파일에는 보통 대조 결과(match status)가 이미 들어 있습니다. 여기서 설계 판단이 갈립니다.

> **규칙. 앱은 파일에 적힌 대조 결과를 그대로 받아들이지 않습니다. 양측 원시값으로 자체 판정한 뒤, 파일의 결과와 비교합니다.**

이유는 두 가지입니다.

**첫째, 재현 가능성입니다.** 요구사항 11에 따라 모든 숫자는 명세된 계산식으로 재현되어야 합니다. 외부에서 만들어진 판정을 그대로 수입하면 그 판정은 앱이 재현할 수 없고, 계산식 명세([15](15-metric-specification.md))의 바깥에 놓입니다.

**둘째, 판정 불일치 자체가 유용한 정보입니다.** 앱의 판정과 파일의 판정이 다르면, 둘 중 하나가 틀렸거나 판정 기준이 다른 것입니다. 어느 쪽이든 확인할 가치가 있습니다.

```
결합형 파일 1행
  ├─ EDC측 값      (COLLFL, COLLDT, KITTYPE ...)   ──┐
  ├─ vendor측 값   (RECVDT, ACCESSNO, SAMPSTAT ...) ──┼──> 앱의 자체 판정
  └─ 파일의 대조 결과 (RECON_STATUS)  ────────────────┼──> 비교
                                                      ▼
                                          일치 → 정상
                                          불일치 → 별도 목록으로 보고
```

**따라서 결합형 파일에는 양측의 원시값이 모두 들어 있어야 합니다.**

**DP-12-8로 이 점이 확정되었습니다.** 사내 표준 파일에는 대조에 사용되는 원시값이 포함됩니다. 따라서 앱은 항상 자체 판정이 가능하며, "판정 수입" 모드(5.6)는 이 전제가 깨지는 경우에 대한 안전장치로만 남습니다.

결합형 파일의 실제 컬럼 명세와 실물 template은 [16. External Data Source Format — Draft v0.1](16-external-data-format-draft.md)에 있습니다.

### 3.3 Dataset 목록

| 코드 | 이름 | 형태 | 행 단위 | 필수 |
|---|---|---|---|---|
| `DS01` | Subject | 단일 | 피험자 1명 | **필수** |
| `DS02` | Visit | 단일 | 피험자·방문 1건 | **필수** |
| `DS03` | Form Status | 단일 | 폼 인스턴스 1건 | **필수** |
| `DS04` | Query | 단일 | 쿼리 1건 | 권장 |
| **`DS05R`** | **Sample Reconciliation** | **결합형** | **샘플 1건 (EDC + lab)** | **샘플 추적 시 기본** |
| `DS05` | Sample (EDC) | 분리형 | 샘플 1건 | 분리형 사용 시 |
| `DS06` | Sample (Central Lab) | 분리형 | 샘플 1건 | 분리형 사용 시 |
| `DS07` | Sample (Bioanalytics Lab) | 분리형 | 샘플 1건 | 분리형 사용 시 |
| **`DS08R`** | **Image Reconciliation** | **결합형** | **영상 검사 1건 (EDC + BICR)** | **영상 추적 시 기본** |
| `DS08` | Image (EDC) | 분리형 | 영상 검사 1건 | 분리형 사용 시 |
| `DS09` | Image (BICR) | 분리형 | 영상 검사 1건 | 분리형 사용 시 |
| `DS10` | SDV Visit | 단일 | 방문 계획 1건 | 선택 |

`DS01`~`DS03`이 최소 구성입니다. 이 셋만으로 D1·D2 도메인이 동작합니다.

샘플과 영상은 **결합형(`DS05R`, `DS08R`)이 기본**이고, 분리형(`DS05`~`DS09`)은 사내에 결합형 표준 파일이 없는 경우의 대안입니다. 분리형은 컬럼 정의가 결합형의 각 절반과 동일하므로, 두 형태 사이의 전환에 추가 설계가 필요하지 않습니다.

## 4. Dataset 명세

### 4.1 DS01 — Subject

피험자 마스터. 기대 항목 생성의 출발점입니다.

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID` | ● | text | 시험 식별자 |
| `SITEID` | ● | text | 사이트 식별자 |
| `COUNTRY` | ● | text | ISO 3166-1 alpha-2 권고 (KR, US, JP) |
| `SUBJID` | ● | text | 피험자 번호 |
| `SUBJSTAT` | ● | code | 피험자 상태 ([13](13-trial-configuration.md)의 상태 목록 값) |
| `SCRNDT` | | date | 스크리닝일 |
| `ENRLDT` | | date | 등록일 |
| `RANDDT` | | date | 무작위배정일 |
| `ANCHORDT` | ● | date | **방문 윈도우 기준일**. 시험 설정에 따라 RANDDT 또는 첫 투여일 |
| `LASTVISDT` | | date | 마지막 방문일 |
| `SITETRFDT` | | date | **사이트 이전일.** 이전이 있었던 경우. 없으면 파일 추출일로 대체되며 경고 |
| `DSCONTDT` | | date | 중도탈락일 |
| `DSCONTRS` | | text | 중도탈락 사유 |
| `STRATA1`~`STRATA5` | | text | 층화 인자. **눈가림 마스킹 대상** |
| `ARM` | | text | 배정군. **눈가림 마스킹 대상** |
| `COHORT` | | text | 코호트. 조건부 SoA 적용의 기준 |
| `SEX` | | code | 조건부 규칙(임신검사 등)에 사용 |

### 4.2 DS02 — Visit

방문 실적. 예정 방문은 SoA에서 생성되므로 **실제 발생한 방문만** 올립니다.

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID` | ● | text | 식별자 |
| `VISITID` | ● | text | SoA의 방문 코드와 일치 |
| `VISITNAME` | | text | 표시명 |
| `VISITDT` | ● | date | 실제 방문일 |
| `VISITSTAT` | ● | code | `OCCURRED` / `NOT_DONE` / `CANCELLED` |
| `UNSCHFL` | | Y/N | 비예정 방문 여부 |
| `VISITSEQ` | | integer | 비예정 방문의 순번 |

### 4.3 DS03 — Form Status

가장 중요한 dataset입니다. **폼 인스턴스 1건이 1행**이고, 각 단계의 완료 여부와 시각을 컬럼으로 가집니다.

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `FORMID` | ● | text | 폼 코드. SoA의 폼 코드와 일치 |
| `FORMNAME` | | text | 표시명 |
| `FORMSEQ` | | integer | 반복 폼의 순번 |
| `FORMTYPE` | | code | `STANDARD` / `LOG` — LOG는 entry 분모에서 제외 ([04](04-domain-concepts.md) 1.7) |
| `SAEFL` | | Y/N | **SAE 해당 여부.** investigator sign의 전체/SAE 구분에 사용 ([04](04-domain-concepts.md) 1.5) |
| `ENTERFL` | ● | Y/N | 입력 완료 |
| `ENTERDT` | | datetime | 입력 완료 시각 |
| `SDVREQFL` | | Y/N | **SDV 대상 여부.** partial SDV 반영. 없으면 시험 설정으로 판정 |
| `SDVFL` | | Y/N | SDV 완료 |
| `SDVDT` | | datetime | SDV 완료 시각 |
| `REVREQFL` | | Y/N | 리뷰 대상 여부 |
| `REVFL` | | Y/N | 리뷰 완료 |
| `REVDT` | | datetime | 리뷰 완료 시각 |
| `CODEREQFL` | | Y/N | 코딩 대상 여부 |
| `CODEFL` | | Y/N | 코딩 완료 |
| `CODEDT` | | datetime | 코딩 완료 시각 |
| `SIGNREQFL` | | Y/N | 서명 대상 여부 |
| `SIGNFL` | ● | Y/N | 서명 완료 |
| `SIGNDT` | | datetime | 서명 시각 (audit trail 기반. 없어도 무방) |
| `FRZFL` | | Y/N | Freeze 완료 |
| `FRZDT` | | datetime | Freeze 시각 |
| `LOCKFL` | | Y/N | Lock 완료 |
| `LOCKDT` | | datetime | Lock 시각 |

> **설계 주의.** `SIGNDT`를 필수로 두지 않은 것은 [04](04-domain-concepts.md) 1.5의 특수 처리 때문입니다. 서명 시각은 audit trail에서만 확보되는 경우가 많으므로, **시각 없이 `SIGNFL`만으로 pending 건수를 셀 수 있게** 설계했습니다.
>
> `~REQFL` 컬럼들도 선택입니다. 제공되면 그 값을 쓰고, 없으면 시험 설정의 범위 규칙으로 판정합니다. EDC가 대상 여부를 내보내는 경우와 그렇지 않은 경우를 모두 수용하기 위함입니다.

### 4.4 DS04 — Query

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID` | ● | text | 식별자 |
| `VISITID`, `FORMID` | | text | 대상 항목 (있으면 폼에 연결) |
| `QUERYID` | ● | text | 쿼리 식별자 |
| `QUERYSTAT` | ● | code | `OPEN` / `ANSWERED` / `CLOSED` / `CANCELLED` |
| `QUERYOWNER` | ● | code | **소유자.** `DM` / `CRA` / `MM` / `PV` 등. 기한 차등의 기준 ([04](04-domain-concepts.md) 1.6) |
| `QUERYGRP` | | text | query group. 그룹별 분해 조회의 축 |
| `QUERYTYPE` | | text | 쿼리 유형 |
| `QUERYOPNDT` | ● | date | **생성일.** 기한 계산의 트리거 |
| `QUERYANSDT` | | date | 응답일 |
| `QUERYCLSDT` | | date | 종결일 |

### 4.5 DS05R — Sample Reconciliation (결합형, 기본)

**external data reconciliation file에 대응하는 형식입니다.** 한 행이 샘플 1건이며, EDC측과 lab측 값이 나란히 들어갑니다.

> **아래는 개념 수준의 컬럼 구성입니다. 확정 명세와 실물 template은 [16](16-external-data-format-draft.md) 5장에 있습니다.** 16번 문서는 벤치마킹을 거쳐 `TPTNUM`(nominal timepoint) 등을 보강한 v0.1 초안이며, 이 절의 목록보다 우선합니다.

#### 식별·매칭

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `KITTYPE` | ● | code | **kit 유형** (`PK` / `ADA` / `NAB` 등). **매칭 키 필수 요소** ([03](03-core-concept-model.md) 5.1) |
| `SAMPSEQ` | | integer | 동일 유형 복수 채취 시 순번 |
| `KITID` | | text | kit / barcode 식별자 |
| `ACCESSNO` | | text | lab accession number |

#### EDC측 값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `EDC_COLLFL` | ● | Y/N | EDC상 채취 여부 |
| `EDC_COLLDT` | | date | EDC상 채취일. **central lab 도착 기한의 트리거** |
| `EDC_COLLTM` | | time | 채취 시각 |
| `EDC_NOTDONERS` | | text | 미채취 사유 |

#### Central lab측 값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `CL_RECVFL` | ● | Y/N | central lab 수령 여부 |
| `CL_RECVDT` | | date | 수령일 |
| `CL_SHIPDT` | | date | 사이트 출고일. **알면 기록, 기한 계산에는 미사용** ([04](04-domain-concepts.md) 4.2) |
| `CL_SAMPSTAT` | | code | `RECEIVED` / `IN_TRANSIT` / `LOST` / `REJECTED` |
| `CL_SHIPBADT` | | date | bioanalytics lab 출고일 |
| `CL_ISSUETYPE` | | code | `HEMOLYSIS` / `INSUFF_VOL` / `TEMP_EXCURSION` / `BROKEN` / `LABEL_MISMATCH` 등 |
| `CL_ISSUETXT` | | text | 이슈 상세 |
| `CL_LABID` | | text | 복수 central lab 운영 시 구분 |

#### Bioanalytics lab측 값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `BA_RECVFL` | | Y/N | bioanalytics lab 수령 여부 |
| `BA_RECVDT` | | date | 수령일 |
| `BA_ANALSTAT` | | code | `ASSIGNED` / `ANALYZED` / `REJECTED` |
| `BA_ANALDT` | | date | 분석 완료일 |
| `BA_REJRS` | | text | 거부 사유 |
| `BA_LABID` | | text | 복수 lab 구분 |

#### 파일이 담고 있는 대조 결과 (선택)

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `RECON_STATUS` | | code | 파일 작성자가 판정한 대조 결과 |
| `RECON_COMMENT` | | text | 판정 코멘트 |
| `RECON_RESOLVED` | | Y/N | 해결 완료 여부 |

`RECON_STATUS`는 **참고값으로만 저장**됩니다. 앱은 위의 EDC측·lab측 원시값으로 자체 판정하고, 두 결과가 다르면 별도 목록으로 보고합니다 (3.2). 앱의 판정 유형은 [04](04-domain-concepts.md) 4.4의 4종입니다.

> **설계 주의.** 사내 표준 파일이 `EDC_COLLFL`이나 `CL_RECVFL` 같은 **양측 원시값 없이 `RECON_STATUS`만 담고 있다면**, 앱은 자체 판정을 할 수 없습니다. 이 경우 Feed가 "판정 수입" 모드로 표시되고 reconciliation 신뢰도가 낮음으로 표기됩니다. **Phase 0에서 실제 파일을 확인해 이 컬럼들이 존재하는지 먼저 확인해야 합니다.**

### 4.6 DS05 — Sample (EDC) *(분리형)*

결합형(`DS05R`)을 쓰지 않는 경우의 대안입니다. EDC에 기록된 채취 사실만 담습니다. 컬럼 의미는 `DS05R`의 EDC측 절반과 같으며 접두사만 없습니다.

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `KITTYPE` | ● | code | **kit 유형** (`PK` / `ADA` / `NAB` 등). **매칭 키의 필수 요소** |
| `SAMPSEQ` | | integer | 동일 유형 복수 채취 시 순번 |
| `COLLFL` | ● | Y/N | **채취 여부.** Reconciliation 유형 판정의 기준 |
| `COLLDT` | | date | 채취일. **central lab 도착 기한의 트리거** |
| `COLLTM` | | time | 채취 시각 |
| `KITID` | | text | kit / barcode 식별자 |
| `NOTDONERS` | | text | 미채취 사유 |

### 4.7 DS06 — Sample (Central Lab) *(분리형)*

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `KITTYPE` | ● | code | 매칭 키 요소 |
| `SAMPSEQ` | | integer | 순번 |
| `KITID` | | text | 1차 매칭 식별자 |
| `ACCESSNO` | | text | central lab accession number |
| `SHIPDT` | | date | 사이트 출고일. **알면 기록, 기한 계산에는 미사용** ([04](04-domain-concepts.md) 4.2) |
| `RECVDT` | | date | central lab 도착일 |
| `SAMPSTAT` | ● | code | `RECEIVED` / `IN_TRANSIT` / `LOST` / `REJECTED` |
| `SHIPBADT` | | date | bioanalytics lab로 출고일 |
| `ISSUETYPE` | | code | `HEMOLYSIS` / `INSUFF_VOL` / `TEMP_EXCURSION` / `BROKEN` / `LABEL_MISMATCH` 등 |
| `ISSUETXT` | | text | 이슈 상세 |
| `LABID` | | text | 복수 central lab 운영 시 구분 |

### 4.8 DS07 — Sample (Bioanalytics Lab) *(분리형)*

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SUBJID`, `VISITID`, `KITTYPE` | ● | text/code | 식별자 + 매칭 키 |
| `SAMPSEQ` | | integer | 순번 |
| `KITID`, `ACCESSNO` | | text | 매칭 식별자 |
| `RECVDT` | | date | bioanalytics lab 도착일 |
| `ANALSTAT` | ● | code | `ASSIGNED` / `ANALYZED` / `REJECTED` |
| `ANALDT` | | date | 분석 완료일 |
| `REJRS` | | text | 거부 사유 |
| `LABID` | | text | 복수 lab 구분 |

### 4.9 DS08R — Image Reconciliation (결합형, 기본)

영상의 결합형 파일입니다. 한 행이 영상 검사 1건이며, EDC측과 BICR측 값이 나란히 들어갑니다.

> **확정 명세와 실물 template은 [16](16-external-data-format-draft.md) 6장에 있습니다.**

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `MODALITY` | ● | code | **검사 방법** (`CT` / `MRI` / `PET` 등). **매칭 키 필수 요소** |
| `IMGSEQ` | | integer | 순번 |
| `EDC_IMGDONEFL` | ● | Y/N | EDC상 영상 획득 여부 |
| `EDC_IMGDT` | | date | EDC상 획득일 |
| `EDC_NOTDONERS` | | text | 미실시 사유 |
| `BICR_IMGFL` | ● | Y/N | BICR에 영상 존재 여부 |
| `BICR_IMGDT` | | date | BICR 기록 획득일. **EDC와 대조 대상** |
| `BICR_UPLDDT` | | date | 업로드일 |
| `BICR_QCSTAT` | | code | `PASSED` / `FAILED` / `PENDING` |
| `BICR_QCDT` | | date | QC 완료일 |
| `BICR_QCFAILRS` | | text | QC 실패 사유 |
| `BICR_ASSIGNDT` | | date | 판독자 배정일 |
| `BICR_READSTAT` | ● | code | `NOT_ASSIGNED` / `ASSIGNED` / `READ` |
| `BICR_READDT` | | date | 판독 완료일 |
| `BICR_IMGSTAT` | | code | `AVAILABLE` / `LOST` |
| `RECON_STATUS` | | code | 파일 작성자의 대조 결과. **참고값** |
| `RECON_COMMENT` | | text | 판정 코멘트 |

벤치마크([01](01-benchmark.md) 1.4)에서 확인한 INV 대 BICR 일관성 대조(피험자 집합, 스캔 집합, 방문, 날짜, 평가 방법)가 이 한 파일로 수행됩니다.

### 4.10 DS08 — Image (EDC) *(분리형)*

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `MODALITY` | ● | code | **검사 방법** (`CT` / `MRI` / `PET` / `XRAY` 등). **매칭 키 필수 요소** |
| `IMGSEQ` | | integer | 순번 |
| `IMGDONEFL` | ● | Y/N | 영상 획득 여부 |
| `IMGDT` | | date | **획득일.** 업로드 기한의 트리거 |
| `NOTDONERS` | | text | 미실시 사유 |

### 4.11 DS09 — Image (BICR) *(분리형)*

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID`, `MODALITY` | ● | text/code | 식별자 + 매칭 키 |
| `IMGSEQ` | | integer | 순번 |
| `IMGDT` | | date | 획득일 (BICR 기록. EDC와 대조) |
| `UPLDDT` | | date | BICR 업로드일 |
| `QCSTAT` | | code | `PASSED` / `FAILED` / `PENDING` |
| `QCDT` | | date | QC 완료일 |
| `QCFAILRS` | | text | QC 실패 사유 |
| `ASSIGNDT` | | date | 판독자 배정일 |
| `READSTAT` | ● | code | `NOT_ASSIGNED` / `ASSIGNED` / `READ` |
| `READDT` | | date | 판독 완료일 |
| `IMGSTAT` | | code | `AVAILABLE` / `LOST` |

### 4.12 DS10 — SDV Visit

CTMS에서 내보내거나 앱에서 직접 입력합니다.

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID` | ● | text | 식별자 |
| `SDVVISITID` | ● | text | 방문 식별자 |
| `VISITTYPE` | | code | `SDV` / `INIT` / `CLOSE_OUT` / `OTHER` |
| `PLANDT` | ● | date | 계획일 |
| `ACTDT` | | date | 실제 방문일 |
| `SDVSTAT` | ● | code | `TENTATIVE` / `ARRANGED` / `COMPLETED` / `CANCELLED` |
| `PLANDAYS` | | number | 계획 방문 일수 |
| `CRACNT` | | integer | 투입 CRA 인원 |
| `CRAID` | | text | CRA 식별자 (복수 시 구분자로 분리) |
| `CANCELRS` | | text | 취소 사유 |

## 5. 업로드 검증 체크포인트

업로드 시 다음을 순서대로 점검합니다. 향후 이 점검을 AI가 수행할 수 있도록 각 항목을 **독립 실행 가능한 규칙**으로 설계합니다 ([14](14-ai-extensibility.md)).

### 5.1 구조 검증 (Structural)

| # | 점검 | 실패 시 |
|---|---|---|
| S1 | 필수 컬럼 존재 | 업로드 거부 |
| S2 | 자료형 적합 | 해당 행 거부 |
| S3 | 날짜 형식 | 해당 행 거부 |
| S4 | 코드값이 허용 목록에 존재 | 해당 행 거부 + 미등록 값 목록 보고 |
| S5 | 매칭 키 컬럼의 결측 | 해당 행 거부 |
| S6 | **출처 메타데이터 필수 항목 존재** (2.2) | 업로드 거부 |
| S7 | **결합형 파일의 양측 원시값 컬럼 존재** (3.2) | 경고 + "판정 수입" 모드 표시 |

### 5.2 완결성 검증 (Completeness)

| # | 점검 | 실패 시 |
|---|---|---|
| C1 | 필수 항목의 결측률 | 임계 초과 시 경고 |
| C2 | 기대 대비 행 수 (이전 Drop 대비 급감) | 경고 — 부분 추출 의심 |
| C3 | 사이트·방문 커버리지 (특정 사이트 통째 누락) | 경고 |
| C4 | 기간 커버리지 (최근 데이터 누락) | 경고 |
| C5 | **`SRC_EXTRACT_DT`가 직전 Drop보다 오래됨** | 경고 — 구버전 파일 업로드 의심 |
| C6 | **결합형 파일에서 한쪽 값이 통째로 비어 있음** | 경고 — 표준화 단계 누락 의심 |

### 5.3 무결성 검증 (Integrity)

| # | 점검 | 실패 시 |
|---|---|---|
| I1 | 매칭 키 중복 (동일 키 복수 행) | 경고 + 중복 목록 |
| I2 | 참조 무결성 — `SUBJID`가 DS01에 존재 | 해당 행 보류 |
| I3 | 참조 무결성 — `VISITID`가 SoA에 존재 | 경고 + 미등록 방문 목록 |
| I4 | 날짜 논리 — 완료일이 트리거일보다 앞섬 | 경고 |
| I5 | 날짜 범위 — 미래 날짜, 비현실적 과거 | 경고 |

### 5.4 일관성 검증 (Consistency)

| # | 점검 | 실패 시 |
|---|---|---|
| X1 | 플래그와 날짜의 모순 (`ENTERFL`=Y 인데 `ENTERDT` 결측) | 경고 |
| X2 | 단계 순서 모순 (SDV 완료인데 입력 미완료) | 경고 |
| X3 | dataset 간 모순 (DS05 `COLLFL`=Y 인데 DS02에 방문 없음) | Reconciliation으로 이관 |
| X4 | 이전 Drop 대비 **역행** (완료였던 것이 미완료로) | **경고 강도 높음** — 부분 추출 또는 원본 정정 의심 |
| X5 | 피험자 상태와 방문의 모순 (탈락 이후 방문 발생) | 경고 |
| X6 | **파일의 `RECON_STATUS`와 앱 자체 판정의 불일치** | 경고 + 별도 목록 보고 (3.2) |

X4가 특히 중요합니다. 실무에서 흔히 발생하며, 놓치면 지표가 이유 없이 떨어집니다.

X6은 DP-12-6 결정에서 새로 생긴 점검입니다. 앱의 판정과 표준 파일의 판정이 다르다는 것은 **둘 중 하나가 틀렸거나 판정 기준이 다르다는 뜻**이므로, 어느 쪽이든 확인 가치가 있습니다. 초기에는 불일치가 많이 나올 것으로 예상되며, 그 목록을 보며 양쪽 기준을 맞춰가는 것이 Phase 1의 실질적 작업이 됩니다.

### 5.5 검증 결과의 처리

```
거부(REJECT)  → 해당 행이 반영되지 않음. 원본 행 번호와 사유를 리포트
경고(WARN)    → 반영하되 목록으로 보고. 사용자가 확인 후 진행 결정
통과(PASS)    → 반영
```

**경고가 있어도 업로드를 막지 않습니다.** 실무 데이터는 항상 불완전하고, 완벽을 요구하면 앱을 쓰지 않게 됩니다. 대신 **경고 이력이 남고 화면에 데이터 품질 지표로 표시**됩니다.

### 5.6 Feed 신뢰도 표시

검증 결과에 따라 각 Feed에 신뢰도가 매겨지고, 해당 도메인 화면에 표시됩니다.

| 신뢰도 | 조건 |
|---|---|
| **정상** | 매칭 키 입도 충족 + 결합형 양측 원시값 존재 + 출처 메타데이터 완비 |
| **주의** | 위 중 하나 미충족. 어느 항목인지 화면에 명시 |
| **판정 수입** | 결합형 파일에 대조 결과만 있고 원시값이 없음. **앱이 자체 판정을 하지 못하는 상태** |

"판정 수입" 상태의 reconciliation 지표는 **재현 가능성 요건을 만족하지 못합니다**([15](15-metric-specification.md) 1장). 화면에 그 사실이 명시되고, export에도 신뢰도 컬럼이 포함됩니다. 숨기지 않고 드러내는 것이 이 표시의 목적입니다.

## 6. Template 버전 관리

| 대상 | 버전 | 변경 시 |
|---|---|---|
| Template 정의 | `DS03 v1.2` | 컬럼 추가·삭제·의미 변경 시 증가 |
| Mapping Profile | `Feed X, mapping v3` | vendor 리포트 형식 변경 시 새 버전 |
| Data Drop | 각 Drop이 사용한 template·mapping 버전을 기록 | — |

과거 Data Drop은 **그 당시 template과 mapping으로 해석된 결과를 유지**합니다. Template을 바꿨다고 과거 데이터가 재해석되지 않습니다 ([08](08-platform-services.md) 4.2 규칙 3과 동일한 원칙).

## 7. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-12-1 | 4장 dataset 구성이 적절한가. 빠진 것이 있는가 (ePRO, 실험실 검사값, 투약 등) | 현 구성으로 시작 |
| DP-12-2 | DS03의 컬럼 구조 — 단계별 컬럼 방식(wide) vs 단계별 행 방식(long) | **wide 권고** (EDC 리포트 관행과 일치) |
| DP-12-3 | `~REQFL` 컬럼을 필수로 할 것인가 | 선택 유지 (설정으로 대체 가능) |
| DP-12-4 | 컬럼명을 CDISC(CDASH/SDTM) 관행에 더 가깝게 맞출 것인가 | 현 수준 유지 — 완전 준수는 과함 |
| DP-12-5 | 5.5의 "경고여도 업로드 허용" 방침에 동의하는가 | 동의 권고 |
| DP-12-6 | ~~vendor 리포트 샘플 확보~~ | **확정** — vendor 원본이 아니라 **vendor data로 만든 사내 표준 파일**(external data reconciliation file 등)을 입력 경계로 함 (1.2) |
| DP-12-7 | ~~사내 표준 파일 샘플 확보~~ | **진행** — 벤치마킹 기반 초안 작성 완료 ([16](16-external-data-format-draft.md)). 검토 의견 후 확정 |
| DP-12-8 | ~~양측 원시값 포함 여부~~ | **확정** — **대조에 사용되는 원시값을 포함** (3.2) |
| DP-12-9 | 결합형과 분리형 중 사내 실제 운영 형태는 무엇인가 | 결합형 전제 |
| DP-12-10 | 2.2 출처 메타데이터를 파일 내 시트로 받을 것인가 업로드 화면에서 받을 것인가 | **파일 내 시트** 권고 (파일과 함께 이동) |
