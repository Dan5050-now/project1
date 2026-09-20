# 16. External Data Source Format — Draft v0.1

*DP-12-7에 따른 초안. 벤치마킹 결과를 반영해 작성했으며, 검토 의견을 받아 확정합니다.*
*v0.2: Q1~Q3 검토 반영 — `TPTNUM` 매칭 키 확정, 사내 DTS 부재에 따른 위치 변경, 누적 전송 확정*

> **이 문서의 위치.** [12](12-standard-source-templates.md)가 앱이 받는 표준 dataset 전반을 다룬다면, 이 문서는 그중 **external data reconciliation file**의 형식을 실제 사용 가능한 수준으로 구체화한 초안입니다. 실물 template 파일은 [`templates/`](templates/)에 있습니다.

## 1. 벤치마킹 결과

### 1.1 업계는 이 문제를 DTS/DTA로 다룬다

external data를 주고받는 업계 표준 장치는 **Data Transfer Specification(DTS)** 또는 **Data Transfer Agreement(DTA)** 입니다. vendor가 초안을 만들어 회람하면 CDM이 검토하고 시험팀과 vendor가 최종 합의하는 문서이며, 다음을 담습니다.

| DTS/DTA 구성 요소 | 이 초안의 반영 |
|---|---|
| 파일 명명 규칙 | 4.1 |
| 파일 형식 (Excel / CSV / SAS) | 4.2 |
| 변수명·레이블·자료형 | 5장, 6장 |
| 허용값과 controlled terminology | 7장 |
| **전송 주기** | 4.3 |
| **누적(cumulative) 대 증분(incremental)** | **4.4 — 이 초안의 중요한 결정** |
| 전송 방법·암호화·수신자 | 앱 범위 밖 (사내 절차) |
| 검사명·단위·이상치 플래그 | 샘플 결과값은 이 앱의 범위 밖 |

시사점은 명확합니다. **앱의 표준 형식을 새로 발명할 필요가 없습니다.** 이미 사내에 DTS가 있다면 그 구조를 따르고, 앱이 필요로 하는 항목만 추가하는 것이 맞습니다.

- [Understanding Data Transfer Specifications in Clinical Data Management](https://ecommercefastlane.com/data-transfer-specifications-in-clinical-data-management/)
- [8 Benefits of Data Transfer Specifications in Clinical Data Management](https://aitimejournal.com/8-benefits-of-data-transfer-specifications-in-clinical-data-management)
- [Reviewing External Vendor Data Transfer Specifications (PHUSE US 2023, PDF)](https://www.lexjansen.com/phuse-us/2023/dh/PAP_DH12.pdf)
- [The Significance of Generic Data Transfer Specification (PHUSE 2024, PDF)](https://www.lexjansen.com/phuse/2024/ds/PAP_DS02.pdf)
- [External Data Transfers — SCDM 리뷰 논문 (PDF)](https://scdm.org/wp-content/uploads/2024/07/External-Data-Transfers.pdf)

### 1.2 대조 키에 **nominal timepoint**가 들어간다

이번 벤치마킹에서 가장 중요한 발견입니다. 업계의 external data 대조는 다음 식별자를 비교합니다.

> EDC 데이터의 고유 식별자 — **피험자 번호, 방문, nominal time point, 채취일, 채취시각** — 를 external data의 같은 항목과 비교한다.

우리가 앞서 확정한 매칭 키는 `kit 유형 + 피험자 + 방문`이었는데, **nominal timepoint가 빠져 있었습니다.** PK 샘플은 한 방문에서 pre-dose, 1h, 2h, 4h처럼 여러 시점에 채취되므로, timepoint가 없으면 **같은 방문의 PK 샘플들이 서로 구분되지 않습니다.** kit 유형을 빠뜨렸을 때와 똑같은 오판정이 timepoint 축에서 발생합니다.

따라서 매칭 키를 다음과 같이 보완할 것을 제안합니다.

```
기존:  KITTYPE + SUBJID + VISITID
보완:  KITTYPE + SUBJID + VISITID + TPTNUM  [+ REPEATSEQ]
```

`TPTNUM`이 없는 kit 유형(단일 채취 ADA 등)은 `0` 또는 공란으로 두면 되므로, 이 보완이 단일 채취 샘플에 부담을 주지 않습니다.

- [Clinical Data Management: Data Integration vs. Data Reconciliation — Precision for Medicine](https://www.precisionformedicine.com/blog/clinical-data-management-data-integration-vs-data-reconciliation/)
- [The Role of Reconciliation in Clinical Data Management — Quanticate](https://www.quanticate.com/blog/reconciliation-in-clinical-data-management)

### 1.3 accession number는 보조 키일 뿐이다

benchmark에서 확인된 알려진 문제입니다. **동일한 accession number가 서로 다른 피험자에 쓰이는 경우**가 실제로 발생합니다. 따라서 accession number를 1차 매칭 키로 삼으면 안 되고, **kit ID → accession number → 논리 키(유형+피험자+방문+시점)** 의 폴백 순서를 유지합니다 ([04](04-domain-concepts.md) 4.3).

### 1.4 양측 원시값을 모두 담는 것이 업계 관행과도 맞다

DP-12-8로 확정된 사항이 업계 관행과 일치함을 확인했습니다. 대조는 **양측의 같은 항목을 비교**하는 작업이므로, 파일에는 EDC측 값과 vendor측 값이 **모두** 들어 있어야 합니다. 특히 채취일·채취시각은 양쪽이 각자 기록하며 이 둘의 불일치가 대표적인 discrepancy 유형입니다.

### 1.5 near-SDTM 형식이 권장된다

데이터는 SDTM에 가까운 형식으로 수집·저장·전송하는 것이 추적성과 데이터 계보 확보에 유리하다는 것이 업계 권고입니다. 이 초안의 변수명은 SDTM/CDASH 관행(`STUDYID`, `SUBJID`, `VISITNUM`, `--DTC`)을 따르되, 완전 준수를 목표로 하지는 않습니다. 이 앱은 제출용 데이터가 아니라 운영 추적 데이터를 다루기 때문입니다.

- [Transform Incoming Lab Data into SDTM LB Domain (PharmaSUG 2012, PDF)](https://pharmasug.org/proceedings/2012/DS/PharmaSUG-2012-DS01.pdf)
- [Use of SAS Reports for External Vendor Data Reconciliation (PharmaSUG 2015, PDF)](https://pharmasug.org/proceedings/2015/IB/PharmaSUG-2015-IB02.pdf)

### 1.6 영상은 sponsor가 보낸 목록과 vendor 목록을 맞춘다

영상 대조의 구조는 샘플과 같습니다. sponsor가 EDC/IVRS의 scan 정보를 가지고 있고 vendor는 자체 repository의 정보를 가지고 있으며, 양쪽 목록을 맞추는 것이 대조입니다. sponsor가 vendor에게 등록 목록이나 scan listing을 제공하는 것도 표준 관행입니다.

- [Benefits of Oncology Image Collection Reconciliation — Clario](https://clario.com/resources/articles/benefits-of-oncology-image-collection-reconciliation/)
- [Medical Imaging Workflow Optimization for Clinical Trials — Collective Minds](https://collectiveminds.health/articles/medical-imaging-workflow)

## 2. 초안의 설계 원칙

| # | 원칙 | 근거 |
|---|---|---|
| P1 | **사내 표준 DTS가 없으므로, 이 형식이 vendor와 DTS를 셋업할 때의 기준안이 된다** | 2.2 |
| P2 | 한 행이 **대조 단위 하나**다 (샘플 1건, 영상 검사 1건) | 대조 결과를 행 단위로 판정하기 위함 |
| P3 | **양측 원시값을 모두 담는다.** 대조 결과만 담지 않는다 | DP-12-8, 1.4 |
| P4 | 매칭 키는 **kit 유형·modality와 nominal timepoint를 포함**한다 | 1.2 |
| P5 | 파일의 대조 결과는 **참고값**이며 앱이 자체 판정한다 | [03](03-core-concept-model.md) 5.1 |
| P6 | **누적 전송을 기본**으로 한다 | 4.4 |
| P7 | 결과값(농도, 역가 등)은 담지 않는다 | 이 앱은 진척을 추적하지 결과를 다루지 않음 |

P7을 명시하는 이유는 범위 관리 때문입니다. 분석 결과값까지 받기 시작하면 이 앱이 데이터 저장소가 되어 [00](00-overview.md) 2.2의 Non-goals를 넘게 됩니다.

### 2.1 검토로 확정된 사항

| # | 질문 | 답변 | 반영 |
|---|---|---|---|
| Q1 | 매칭 키에 `TPTNUM` 포함 | **포함 필요** | 확정. [03](03-core-concept-model.md) 5.2, [04](04-domain-concepts.md) 4.3에 반영 |
| Q2 | 사내 DTS 존재 여부 | **없음. 매번 vendor와 DTS 셋업** | 이 형식의 위치가 바뀜 (2.2) |
| Q3 | 누적 전송 가능 여부 | **일반적으로 누적 파일 수령** | 확정. 증분은 예외 처리로만 유지 (4.4) |

### 2.2 이 형식의 위치가 바뀐다 (Q2 반영)

초안은 "사내 DTS가 있으면 그것을 따른다"는 전제로 썼습니다. **사내 표준 DTS가 없고 시험마다 vendor와 새로 셋업한다면, 이 형식의 위치가 달라집니다.**

```
[초안의 전제]                          [실제]

사내 DTS (기준)                        시험마다 vendor와 DTS 협의
     │                                        │
     ▼ 따른다                                 │ 이 형식을 들고 들어간다
  앱 template                         ┌───────▼────────┐
                                      │  앱 template   │  ← sponsor 측 기준안
                                      └───────┬────────┘
                                              ▼
                                       vendor별 DTS 합의
```

즉 이 형식은 **앱이 수동적으로 맞추는 대상이 아니라, DTS 협의에 들고 들어가는 sponsor 측 요구사항**이 됩니다.

#### 이것이 좋은 이유

| 항목 | 효과 |
|---|---|
| 시험 간 변동 감소 | 매번 백지에서 협의하는 대신 같은 기준안에서 출발하므로, 시험마다 형식이 달라지는 폭이 줄어듭니다 |
| 협의 시간 단축 | vendor가 채워 넣을 양식이 준비되어 있습니다 |
| Mapping 작업 감소 | 협의 단계에서 이미 맞춰지므로 앱의 Mapping Profile이 흡수할 차이가 줄어듭니다 |
| 누락 예방 | "그 항목은 빠졌네"를 DBL 직전이 아니라 셋업 시점에 발견합니다 |

#### 다만 vendor가 전부 줄 수 있는 것은 아닙니다

DTS 협의에서 vendor가 제공할 수 없는 항목이 반드시 나옵니다. 그래서 **모든 컬럼을 동등하게 요구하지 않고 우선순위를 나눕니다.**

| 우선순위 | 의미 | 협의에서의 태도 |
|---|---|---|
| **MUST** | 없으면 앱의 해당 도메인이 동작하지 않음 | 반드시 확보. 안 되면 대안 협의 |
| **SHOULD** | 특정 지표나 분석이 불가능해짐 | 요청하되 대안 수용 가능 |
| **NICE** | 있으면 유용 | 부담되면 생략 |

| Dataset | MUST | SHOULD | NICE |
|---|---|---|---|
| Sample Reconciliation | 11 | 14 | 18 |
| Image Reconciliation | 10 | 11 | 13 |
| *(Transfer Header)* | *8* | *5* | *1* |

MUST 항목만 보면 요구가 크지 않습니다. **샘플 11개, 영상 10개**이며 대부분 vendor가 이미 관리하는 값입니다. Transfer Header는 대부분 표준 파일 작성자가 채우는 항목이라 vendor 부담이 아닙니다.

> **초안 v0.1에서 바로잡은 것.** v0.1에서 필수(●)로 표시한 컬럼이 실제보다 적었습니다. `EDC_COLLDTC`와 `CL_RECVDTC`가 빠져 있었는데, 이 둘이 없으면 **중앙랩 도착 기한을 계산할 수 없어** 해당 항목이 통째로 "기한 산정 불가"로 빠집니다. 영상도 `EDC_IMGDTC`와 `BICR_UPLDDTC`가 같은 이유로 필수입니다. v0.2에서 MUST로 올렸습니다.

#### DTS 협의용 worksheet

vendor에게 바로 건넬 수 있는 양식을 만들었습니다.

**[`templates/DTS_VARIABLE_REQUEST_v0.1.csv`](templates/DTS_VARIABLE_REQUEST_v0.1.csv)**

앱이 요구하는 전 컬럼이 우선순위와 설명과 함께 들어 있고, vendor가 채울 칸이 오른쪽에 있습니다.

| vendor 기입 칸 | 내용 |
|---|---|
| `VENDOR_CAN_PROVIDE` | `Y` / `N` / `PARTIAL` |
| `VENDOR_COLUMN_NAME` | vendor 시스템에서의 컬럼명 |
| `VENDOR_FORMAT` | 자료형·형식이 다를 경우 |
| `VENDOR_NOTE` | 제약 사항, 제공 조건 |

이 worksheet의 가치는 협의에서 끝나지 않습니다. **vendor가 기입한 `VENDOR_COLUMN_NAME`이 그대로 앱의 Mapping Profile 입력이 됩니다** ([08](08-platform-services.md) 5.2). 협의 산출물이 곧 시스템 설정이 되므로 옮겨 적는 작업이 사라집니다.

## 3. 파일 구성

| 파일 | 내용 | Template |
|---|---|---|
| Transfer Header | 전송 단위의 출처 메타데이터 | [`TRANSFER_HEADER_v0.1.csv`](templates/TRANSFER_HEADER_v0.1.csv) |
| Sample Reconciliation | 샘플 대조 데이터 | [`EXT_SAMPLE_RECON_v0.1.csv`](templates/EXT_SAMPLE_RECON_v0.1.csv) |
| Image Reconciliation | 영상 대조 데이터 | [`EXT_IMAGE_RECON_v0.1.csv`](templates/EXT_IMAGE_RECON_v0.1.csv) |

Excel 워크북으로 제출하는 경우 세 시트로 구성합니다. Transfer Header는 **매 전송마다 반드시 동반**됩니다.

## 4. 전송 규약

### 4.1 파일 명명

```
<STUDYID>_<DATASET>_<TRANSFERTYPE>_<YYYYMMDD>[_<SEQ>].csv

예:  ABC301_SAMPLERECON_CUM_20260918.csv
     ABC301_IMAGERECON_CUM_20260918.csv
```

강제하지 않습니다. 사내 규칙이 있으면 그것을 따르고, 앱은 Transfer Header의 내용으로 판단합니다. **파일명에 의존하지 않는 것**이 설계 방침입니다. 파일명은 사람이 바꾸기 쉽기 때문입니다.

### 4.2 파일 형식

CSV(UTF-8) 또는 Excel(.xlsx). 날짜는 ISO 8601 `YYYY-MM-DD`, 시각은 `hh:mm`. 부분 날짜는 `YYYY-MM`, `YYYY`를 허용하며 처리 규칙은 [15](15-metric-specification.md) 3.2를 따릅니다.

### 4.3 전송 주기

시험별로 정합니다. 권고는 **주 1회**이며, DBL 전 구간에서는 주 2회 이상으로 조정합니다. 주기 자체는 앱 설정 항목이 아니지만, **직전 전송 이후 경과일이 예상 주기를 넘으면 화면에 데이터 최신성 경고**가 표시됩니다 ([15](15-metric-specification.md) 6.8 `quality.src_extract_lag`).

### 4.4 누적 전송 (Q3 확정)

**현재 일반적으로 누적 파일을 수령하고 있음이 확인되었습니다.** 따라서 누적이 기본이며, 아래 증분 관련 규정은 예외 상황에 대한 대비로만 유지합니다.

DTS 관행에서 전송 유형은 누적(cumulative)과 증분(incremental) 중 하나를 고릅니다. **이 앱은 누적을 요구합니다.**

이유가 분명합니다. 증분 파일만 받으면 앱은 **"이번에 안 보낸 것"과 "존재하지 않는 것"을 구분할 수 없습니다.** 이 앱의 존재 이유가 "무엇이 빠져 있는가"에 답하는 것인데, 증분 전송에서는 그 질문 자체가 성립하지 않습니다.

증분 전송이 불가피한 경우(파일 크기 등)에는 다음을 요구합니다. **DTS 협의 시 누적 전송을 명시적으로 합의 항목에 넣는 것**이 가장 확실한 예방책입니다.

| 요구 | 내용 |
|---|---|
| `TRANSFER_TYPE = INCREMENTAL` 명시 | Transfer Header |
| `PERIOD_FROM` / `PERIOD_TO` 필수 | 그 기간 밖의 항목은 **"미수령"이 아니라 "알 수 없음"** 으로 처리 |
| 주기적 전체 재전송 | 월 1회 이상 누적 전송으로 전체 상태 동기화 |

증분 전송 중인 Feed는 화면에 그 사실이 표시되고 reconciliation 신뢰도가 **주의**로 표기됩니다.

### 4.5 행 수 확인

Transfer Header의 `ROW_COUNT`와 실제 행 수를 대조합니다. 불일치는 전송 중 잘림(truncation)의 가장 흔한 신호입니다.

## 5. Sample Reconciliation 형식

한 행 = 샘플 1건. Template: [`EXT_SAMPLE_RECON_v0.1.csv`](templates/EXT_SAMPLE_RECON_v0.1.csv)

### 5.1 식별·매칭 블록

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID` | ● | text | 시험 식별자 |
| `SITEID` | ● | text | 사이트 |
| `SUBJID` | ● | text | 피험자 번호 |
| `VISITID` | ● | text | 방문 코드. SoA와 일치 |
| `VISITNUM` | | number | 방문 순서 |
| `VISIT` | | text | 방문 표시명 |
| `KITTYPE` | ● | code | **kit 유형** (`PK`/`ADA`/`NAB` 등). 매칭 키 |
| `TPTNUM` | ● | number | **nominal timepoint 번호.** 단일 채취는 `0` (1.2) |
| `TPTNAME` | | text | timepoint 표시명 (`Pre-dose`, `1h post-dose`) |
| `REPEATSEQ` | | number | 재채취 순번. 최초 `1` |
| `KITID` | | text | kit / barcode 식별자. **1차 매칭 식별자** |
| `ACCESSNO` | | text | lab accession number. **보조 키** (1.3) |

### 5.2 EDC측 원시값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `EDC_COLLFL` | ● | Y/N | **채취 여부.** 대조 유형 판정의 한 축 |
| `EDC_COLLDTC` | ● | date | EDC 기록 채취일. **중앙랩 도착 기한의 트리거** |
| `EDC_COLLTM` | | time | EDC 기록 채취시각 |
| `EDC_TPTNAME` | | text | EDC 기록 timepoint. `TPTNAME`과 대조 |
| `EDC_NOTDONERS` | | text | 미채취 사유 |
| `EDC_ENTERDTC` | | date | EDC 입력일. 입력 지연 분석용 |

### 5.3 Central lab측 원시값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `CL_LABID` | | text | 복수 central lab 구분 |
| `CL_RECVFL` | ● | Y/N | **수령 여부.** 대조 유형 판정의 다른 한 축 |
| `CL_COLLDTC` | | date | **lab이 기록한 채취일.** `EDC_COLLDTC`와 대조 |
| `CL_COLLTM` | | time | lab이 기록한 채취시각 |
| `CL_SHIPDTC` | | date | 사이트 출고일. **기록만 하고 기한 계산에는 미사용** |
| `CL_RECVDTC` | ● | date | central lab 도착일 |
| `CL_SAMPSTAT` | ● | code | `RECEIVED`/`IN_TRANSIT`/`LOST`/`REJECTED`/`NOT_SHIPPED` |
| `CL_CONDITION` | | code | 수령 상태 `ACCEPTABLE`/`COMPROMISED` |
| `CL_ISSUETYPE` | | code | 7.3의 이슈 코드 |
| `CL_ISSUETXT` | | text | 이슈 상세 |
| `CL_ALIQUOTN` | | number | 분주 개수 |
| `CL_SHIPBADTC` | | date | bioanalytics lab 출고일 |

### 5.4 Bioanalytics lab측 원시값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `BA_LABID` | | text | 복수 lab 구분 |
| `BA_RECVFL` | | Y/N | 수령 여부 |
| `BA_RECVDTC` | | date | 도착일 |
| `BA_ASSAYCD` | | text | 분석법 코드 |
| `BA_ANALSTAT` | | code | `NOT_ASSIGNED`/`ASSIGNED`/`ANALYZED`/`REJECTED` |
| `BA_ANALDTC` | | date | 분석 완료일 |
| `BA_RESULTFL` | | Y/N | 결과 전달 여부. **결과값 자체는 받지 않음** (P7) |
| `BA_REJRS` | | text | 거부 사유 |

### 5.5 파일의 대조 결과 (참고값)

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `RECON_STATUS` | | code | 파일 작성자의 판정 |
| `RECON_CAT` | | text | 판정 분류 |
| `RECON_COMMENT` | | text | 코멘트 |
| `RECON_RESOLVED` | | Y/N | 해결 여부 |
| `RECON_UPDDTC` | | date | 판정 갱신일 |

이 블록은 **앱의 판정과 비교되는 참고값**입니다 (P5). 없어도 앱은 동작합니다.

## 6. Image Reconciliation 형식

한 행 = 영상 검사 1건. Template: [`EXT_IMAGE_RECON_v0.1.csv`](templates/EXT_IMAGE_RECON_v0.1.csv)

### 6.1 식별·매칭 블록

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID` | ● | text | 식별자 |
| `VISITID` | ● | text | 방문 코드 |
| `VISITNUM`, `VISIT` | | number/text | 방문 순서·표시명 |
| `MODALITY` | ● | code | **검사 방법** (`CT`/`MRI`/`PET`/`XRAY`/`BONESCAN`). 매칭 키 |
| `ANATREG` | | code | 해부학적 부위 (`CHEST`/`ABDOMEN`/`WHOLEBODY` 등) |
| `IMGSEQ` | | number | 동일 조건 복수 검사 순번 |
| `SCANUID` | | text | vendor의 검사 식별자 |

### 6.2 EDC측 원시값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `EDC_IMGDONEFL` | ● | Y/N | 영상 획득 여부 |
| `EDC_IMGDTC` | ● | date | EDC 기록 획득일. **업로드 기한의 트리거** |
| `EDC_MODALITY` | | code | **EDC 기록 검사 방법.** `BICR_MODALITY`와 대조 |
| `EDC_ANATREG` | | code | EDC 기록 부위 |
| `EDC_NOTDONERS` | | text | 미실시 사유 |

`EDC_MODALITY`를 매칭 키의 `MODALITY`와 별도로 두는 것이 중요합니다. 벤치마크에서 확인한 대로 **평가 방법의 일관성 확인이 표준 대조 항목**이며, 양쪽이 각자 기록한 값을 비교해야 불일치를 잡을 수 있습니다.

### 6.3 BICR측 원시값

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `BICR_IMGFL` | ● | Y/N | BICR 보유 여부 |
| `BICR_IMGDTC` | | date | BICR 기록 획득일. `EDC_IMGDTC`와 대조 |
| `BICR_MODALITY` | | code | BICR 기록 검사 방법 |
| `BICR_ANATREG` | | code | BICR 기록 부위 |
| `BICR_UPLDDTC` | ● | date | 업로드일 |
| `BICR_QCSTAT` | | code | `PENDING`/`PASSED`/`FAILED` |
| `BICR_QCDTC` | | date | QC 완료일 |
| `BICR_QCFAILRS` | | code | QC 실패 사유 (7.4) |
| `BICR_ASSIGNDTC` | | date | 판독자 배정일 |
| `BICR_READSTAT` | ● | code | `NOT_ASSIGNED`/`ASSIGNED`/`READ` |
| `BICR_READDTC` | | date | 판독 완료일 |
| `BICR_READN` | | number | 완료된 판독 수 (double read 대비) |
| `BICR_ADJFL` | | Y/N | adjudication 필요 여부 |
| `BICR_IMGSTAT` | | code | `AVAILABLE`/`LOST`/`WITHDRAWN` |

### 6.4 파일의 대조 결과 (참고값)

샘플과 동일한 `RECON_*` 블록입니다.

## 7. Controlled Terminology 초안

앱은 이 목록을 [13](13-trial-configuration.md) `CFG09`에서 시험별로 관리합니다. 아래는 기본값입니다.

### 7.1 `KITTYPE`

`PK` / `ADA` / `NAB` / `PD` / `BIOMARKER` / `GENOMIC` / `SAFETY_LAB` / `PREGNANCY` / `OTHER`

### 7.2 `CL_SAMPSTAT` · `BA_ANALSTAT`

| 컬럼 | 값 |
|---|---|
| `CL_SAMPSTAT` | `NOT_SHIPPED` / `IN_TRANSIT` / `RECEIVED` / `LOST` / `REJECTED` |
| `BA_ANALSTAT` | `NOT_ASSIGNED` / `ASSIGNED` / `ANALYZED` / `REJECTED` |

### 7.3 `CL_ISSUETYPE`

`HEMOLYSIS` / `INSUFF_VOL` / `TEMP_EXCURSION` / `BROKEN_CONTAINER` / `LABEL_MISMATCH` / `WRONG_TUBE` / `EXPIRED_KIT` / `CLOTTED` / `OTHER`

### 7.4 `BICR_QCFAILRS`

`INCORRECT_MODALITY` / `INCOMPLETE_SERIES` / `POOR_QUALITY` / `WRONG_TIMEPOINT` / `PHI_PRESENT` / `MISSING_CONTRAST` / `OTHER`

### 7.5 `RECON_STATUS` (파일 작성자 판정)

`MATCHED` / `EDC_ONLY` / `VENDOR_ONLY` / `DISCREPANT` / `AMBIGUOUS` / `RESOLVED`

앱의 판정 유형([04](04-domain-concepts.md) 4.4)과 이름이 다른 것은 의도적입니다. **둘을 섞으면 어느 쪽 판정인지 혼동**되기 때문입니다. 앱은 자체 유형으로 판정하고, 이 값과의 대응은 매핑 테이블로 관리합니다.

## 8. 앱의 판정 로직 (참고)

이 형식이 앱의 4개 대조 유형으로 어떻게 판정되는지입니다. 상세는 [15](15-metric-specification.md)에 명세됩니다.

```
매칭 키 = KITTYPE + SUBJID + VISITID + TPTNUM [+ REPEATSEQ]

IF   EDC_COLLFL = 'Y'  AND  CL_RECVFL = 'N'  AND  CL_SAMPSTAT ∈ {NOT_SHIPPED, IN_TRANSIT, LOST}
     → EDC_Y_NOT_RECEIVED   (구간: CENTRAL)

IF   EDC_COLLFL ∈ {'N', 결측}  AND  CL_RECVFL = 'Y'
     → RECEIVED_NOT_IN_EDC   (구간: CENTRAL)

IF   양측 존재  AND  ( EDC_COLLDTC ≠ CL_COLLDTC
                    OR EDC_TPTNAME ≠ TPTNAME
                    OR EDC_MODALITY ≠ BICR_MODALITY )
     → MATCHED_DISCREPANT

IF   동일 매칭 키에 복수 행
     → AMBIGUOUS_MATCH
```

bioanalytics 구간도 같은 논리를 `CL_SHIPBADTC`와 `BA_RECVFL`에 적용합니다.

## 9. Template 파일 사용법

[`templates/`](templates/)의 세 CSV는 **헤더와 예시 행을 담은 실물 파일**입니다. Excel에서 열어 그대로 검토하실 수 있습니다.

예시 행은 각 대조 유형이 실제로 어떻게 표현되는지 보여주도록 구성했습니다.

| 예시 행 | 보여주는 것 |
|---|---|
| 1~2 | 정상 매칭 (PK pre-dose, 1h) |
| 3 | `EDC_Y_NOT_RECEIVED` — 채취했으나 lab 미수령 |
| 4 | `RECEIVED_NOT_IN_EDC` — lab에는 있으나 EDC 미기록 |
| 5 | `MATCHED_DISCREPANT` — 채취일 불일치 |
| 6 | 용혈로 분석 불가 → 앱에서 `WAIVED` 전이 대상 |
| 7 | 배송 중 |
| 8 | 재채취 (`REPEATSEQ = 2`) |

## 10. 검토 요청 사항

초안이므로 다음을 중심으로 의견 주시면 반영하겠습니다.

| # | 확인 사항 | 초안의 선택 |
|---|---|---|
| ~~Q1~~ | ~~`TPTNUM`을 매칭 키에 넣는 것이 맞는가~~ | **확정 — 포함** |
| ~~Q2~~ | ~~사내 DTS가 이미 있는가~~ | **확정 — 없음. 이 형식이 DTS 협의 기준안이 됨 (2.2)** |
| ~~Q3~~ | ~~누적 전송이 가능한가~~ | **확정 — 누적 수령** |
| Q4 | 샘플 추적 단위가 kit인가 aliquot인가 | 초안은 **kit 단위**, `CL_ALIQUOTN`으로 분주 수만 기록 |
| Q5 | bioanalytics 블록을 같은 파일에 둘 것인가 분리할 것인가 | 같은 파일 |
| Q6 | 7장 controlled terminology에 추가·수정할 값 | — |
| Q7 | `RECON_*` 블록이 실제 사내 파일에 존재하는가 | 없어도 무방 |
| Q8 | 결과값(농도 등)을 제외하는 것에 동의하는가 (P7) | 제외 |
| Q9 | 영상의 `ANATREG`를 매칭 키에 넣을 것인가 | 초안은 **제외**, 필요 시 추가 |
| Q10 | 컬럼 수가 실무적으로 과한가 | **MUST는 샘플 11개·영상 10개** (2.2) |
| **Q11** | **2.2의 MUST / SHOULD / NICE 구분이 타당한가** | worksheet 참조 |
| **Q12** | **DTS 협의용 worksheet를 실제로 vendor에게 건넬 것인가** | 권고 |

## 11. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| ~~DP-16-1~~ | ~~매칭 키에 `TPTNUM` 추가~~ | **확정 — 추가.** [03](03-core-concept-model.md) 5.2, [04](04-domain-concepts.md) 4.3 반영 완료 |
| ~~DP-16-2~~ | ~~누적 전송 기본 방침~~ | **확정 — 누적** |
| DP-16-6 | 2.2의 MUST/SHOULD/NICE 구분이 타당한가 | 실무 검토 필요 |
| DP-16-7 | DTS 협의 worksheet를 표준 절차에 넣을 것인가 | **넣기 권고** — 협의 산출물이 Mapping Profile 입력이 됨 |
| DP-16-8 | vendor가 MUST 항목을 제공하지 못할 때의 대안 절차 | 시험별 판단. 해당 도메인 추적 범위 축소를 명시 |
| DP-16-3 | 샘플 추적 단위 (kit vs aliquot) — DP-04-10과 연결 | **kit 단위** |
| DP-16-4 | 7장 CT 기본값의 적절성 | 실무 검토 필요 |
| DP-16-5 | `RECON_STATUS` 값과 앱 판정 유형의 매핑 테이블 필요 여부 | 필요 |
