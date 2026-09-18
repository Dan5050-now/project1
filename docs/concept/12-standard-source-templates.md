# 12. 표준 Source Dataset Template

*검토 반영 신규 문서 (요구사항 7)*

## 1. 왜 표준 template인가

### 1.1 문제

시험마다 EDC 종류가 다르고, 같은 EDC라도 시험마다 리포트 구조가 다르며, vendor마다 컬럼명과 코드값이 제각각입니다. 이 상태에서 앱이 **특정 시스템이나 특정 시험 설계를 전제로 개발되면**, 다른 시험에는 쓸 수 없거나 시험마다 코드를 고쳐야 합니다. 그러면 앱의 수명은 첫 시험과 함께 끝납니다.

### 1.2 해결 방향

**앱이 요구하는 표준 형식을 먼저 정의하고, 사용자가 시험의 실제 source data를 그 형식에 맞춰 준비해 업로드합니다.** 앱은 정해진 형식만 알면 되므로 처리 코드가 하나로 고정되고, 오류 발생 지점이 줄어듭니다.

```
  [시험 A]  Rave 리포트     ──┐
  [시험 B]  Veeva 리포트    ──┤
  [시험 C]  IRT + 자체 추출 ──┼──> 사용자가 표준 template 형식으로 준비
  [시험 D]  Lab vendor CSV  ──┘         │
                                        ▼
                            ┌───────────────────────┐
                            │  표준 Source Template │
                            │  (고정 스키마)          │
                            └───────────┬───────────┘
                                        ▼
                            앱의 처리 코드는 하나
```

### 1.3 이 방식의 대가와 그 대가를 줄이는 장치

솔직히 말하면 이 방식은 **사용자에게 변환 부담을 넘깁니다.** 그 부담을 줄이기 위해 다음을 함께 제공합니다.

| 장치 | 내용 |
|---|---|
| Template 배포 | 컬럼 설명, 자료형, 허용값, 예시 행이 포함된 Excel/CSV 파일 |
| Mapping Profile | 사용자의 원본 컬럼명을 표준 컬럼에 연결하는 매핑을 앱에 저장 ([08](08-platform-services.md) 5.2). **한 번 설정하면 이후 원본 그대로 업로드 가능** |
| 검증 리포트 | 업로드 즉시 원본 행 번호와 함께 오류 지점 표시 |
| 변환 가이드 | 주요 EDC·vendor별 변환 예시 문서 |
| AI 보조 | 향후 AI가 변환·점검을 수행 ([14](14-ai-extensibility.md)) |

Mapping Profile이 핵심입니다. **표준 template은 목표 형식이지 업로드 필수 형식이 아닙니다.** 매핑이 설정되면 사용자는 원본 리포트를 그대로 올릴 수 있고, 앱이 표준 형식으로 변환합니다.

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

### 2.1 필수 메타데이터 — 매칭 키 선언

각 업로드에는 **매칭 키 선언**이 반드시 포함됩니다. [03](03-core-concept-model.md) 5.1에서 정의한 대로, 매칭 키 입도가 소스보다 거칠면 reconciliation 판정이 조용히 틀리기 때문입니다.

선언은 Feed 설정에 저장되며 업로드마다 재입력할 필요가 없습니다. 다만 **입도가 권고 수준에 미달하면 경고가 표시되고 해당 Feed의 reconciliation이 "신뢰도 낮음"으로 표시**됩니다.

### 2.2 식별자 규약

| 컬럼 | 의미 | 비고 |
|---|---|---|
| `STUDYID` | 시험 식별자 | 모든 dataset 공통 필수 |
| `SITEID` | 사이트 식별자 | 시험 내 유일 |
| `SUBJID` | 피험자 번호 | **시험 내 유일**해야 함 |
| `VISITID` | 방문 식별 코드 | SoA의 방문 코드와 일치해야 함 |
| `VISITNAME` | 방문 표시명 | 화면 표시용 |

`SUBJID`와 `VISITID`의 값이 dataset 간에 **정확히 일치**해야 매칭이 성립합니다. 이것이 업로드 검증의 1순위 점검 항목입니다.

## 3. 표준 Dataset 목록

| 코드 | 이름 | 행 단위 | 주 출처 | 필수 |
|---|---|---|---|---|
| `DS01` | Subject | 피험자 1명 | RTSM / EDC | **필수** |
| `DS02` | Visit | 피험자·방문 1건 | RTSM / EDC | **필수** |
| `DS03` | Form Status | 폼 인스턴스 1건 | EDC | **필수** |
| `DS04` | Query | 쿼리 1건 | EDC | 권장 |
| `DS05` | Sample (EDC) | 샘플 1건 | EDC | 샘플 추적 시 |
| `DS06` | Sample (Central Lab) | 샘플 1건 | Central lab | 샘플 추적 시 |
| `DS07` | Sample (Bioanalytics Lab) | 샘플 1건 | Bioanalytics lab | 샘플 추적 시 |
| `DS08` | Image (EDC) | 영상 검사 1건 | EDC | 영상 추적 시 |
| `DS09` | Image (BICR) | 영상 검사 1건 | BICR vendor | 영상 추적 시 |
| `DS10` | SDV Visit | 방문 계획 1건 | CTMS 또는 앱 직접 입력 | 선택 |

`DS01`~`DS03`이 최소 구성입니다. 이 셋만으로 D1·D2 도메인이 동작합니다.

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

### 4.5 DS05 — Sample (EDC)

EDC에 기록된 채취 사실. Reconciliation의 한쪽 축입니다.

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

### 4.6 DS06 — Sample (Central Lab)

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

### 4.7 DS07 — Sample (Bioanalytics Lab)

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

### 4.8 DS08 — Image (EDC)

| 컬럼 | 필수 | 자료형 | 설명 |
|---|---|---|---|
| `STUDYID`, `SITEID`, `SUBJID`, `VISITID` | ● | text | 식별자 |
| `MODALITY` | ● | code | **검사 방법** (`CT` / `MRI` / `PET` / `XRAY` 등). **매칭 키 필수 요소** |
| `IMGSEQ` | | integer | 순번 |
| `IMGDONEFL` | ● | Y/N | 영상 획득 여부 |
| `IMGDT` | | date | **획득일.** 업로드 기한의 트리거 |
| `NOTDONERS` | | text | 미실시 사유 |

### 4.9 DS09 — Image (BICR)

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

### 4.10 DS10 — SDV Visit

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

### 5.2 완결성 검증 (Completeness)

| # | 점검 | 실패 시 |
|---|---|---|
| C1 | 필수 항목의 결측률 | 임계 초과 시 경고 |
| C2 | 기대 대비 행 수 (이전 Drop 대비 급감) | 경고 — 부분 추출 의심 |
| C3 | 사이트·방문 커버리지 (특정 사이트 통째 누락) | 경고 |
| C4 | 기간 커버리지 (최근 데이터 누락) | 경고 |

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

X4가 특히 중요합니다. 실무에서 흔히 발생하며, 놓치면 지표가 이유 없이 떨어집니다.

### 5.5 검증 결과의 처리

```
거부(REJECT)  → 해당 행이 반영되지 않음. 원본 행 번호와 사유를 리포트
경고(WARN)    → 반영하되 목록으로 보고. 사용자가 확인 후 진행 결정
통과(PASS)    → 반영
```

**경고가 있어도 업로드를 막지 않습니다.** 실무 데이터는 항상 불완전하고, 완벽을 요구하면 앱을 쓰지 않게 됩니다. 대신 **경고 이력이 남고 화면에 데이터 품질 지표로 표시**됩니다.

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
| DP-12-1 | 4장 dataset 10종 구성이 적절한가. 빠진 것이 있는가 (ePRO, 실험실 검사값, 투약 등) | 현 10종으로 시작 |
| DP-12-2 | DS03의 컬럼 구조 — 단계별 컬럼 방식(wide) vs 단계별 행 방식(long) | **wide 권고** (EDC 리포트 관행과 일치) |
| DP-12-3 | `~REQFL` 컬럼을 필수로 할 것인가 | 선택 유지 (설정으로 대체 가능) |
| DP-12-4 | 컬럼명을 CDISC(CDASH/SDTM) 관행에 더 가깝게 맞출 것인가 | 현 수준 유지 — 완전 준수는 과함 |
| DP-12-5 | 5.5의 "경고여도 업로드 허용" 방침에 동의하는가 | 동의 권고 |
| DP-12-6 | 실제 사용 중인 EDC·lab·BICR vendor의 리포트 샘플을 확보해 template 검증 필요 | **Phase 1 전 필수** |
