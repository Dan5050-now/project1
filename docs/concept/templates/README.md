# Template 파일 (Draft v0.1)

[16. External Data Source Format — Draft v0.1](../16-external-data-format-draft.md)의 실물 template입니다.

Excel에서 그대로 열어 검토하실 수 있습니다. 파일은 **UTF-8 with BOM**으로 저장되어 있어 Excel에서 한글이 깨지지 않습니다.

| 파일 | 용도 | 내용 |
|---|---|---|
| [`DTS_VARIABLE_REQUEST_v0.2.csv`](DTS_VARIABLE_REQUEST_v0.2.csv) | **vendor와 DTS 협의할 때 건네는 양식** | 전 컬럼 91개. 우선순위·조건·설명·검토 이력 포함, vendor 기입 칸 4개 |
| [`TRANSFER_HEADER_v0.1.csv`](TRANSFER_HEADER_v0.1.csv) | 파일 형식 예시 | 전송 단위의 출처 메타데이터. **매 전송마다 동반** |
| [`EXT_SAMPLE_RECON_v0.1.csv`](EXT_SAMPLE_RECON_v0.1.csv) | 파일 형식 예시 | 샘플 대조. 헤더 43열 + 예시 8행 |
| [`EXT_IMAGE_RECON_v0.1.csv`](EXT_IMAGE_RECON_v0.1.csv) | 파일 형식 예시 | 영상 대조. 헤더 34열 + 예시 7행 |
| [`CFG10_WAIVER_RULE_WORKSHEET_v0.1.csv`](CFG10_WAIVER_RULE_WORKSHEET_v0.1.csv) | **이슈 유형별 예외 범위 확정용** | 후보 유형 33개 + 빈 행 9개. 제안값 포함 |
| [`CFG10_STAGE_REFERENCE_v0.1.csv`](CFG10_STAGE_REFERENCE_v0.1.csv) | 참조표 | 선택 가능한 단계 코드 목록 |

## DTS 협의 worksheet 사용법

사내에 표준 DTS가 없고 시험마다 vendor와 새로 셋업하므로, 이 worksheet가 **협의의 출발점**이 됩니다 ([16번 문서 2.2](../16-external-data-format-draft.md)).

```
① worksheet를 vendor에게 전달
        ↓
② vendor가 오른쪽 4개 칸을 기입
   VENDOR_CAN_PROVIDE / VENDOR_COLUMN_NAME / VENDOR_FORMAT / VENDOR_NOTE
        ↓
③ MUST 항목 중 제공 불가한 것을 협의
        ↓
④ 합의된 내용이 그 시험의 DTS가 됨
        ↓
⑤ VENDOR_COLUMN_NAME이 그대로 앱의 Mapping Profile 입력이 됨
```

⑤가 이 양식의 실질적 가치입니다. 협의 산출물을 시스템 설정으로 **옮겨 적는 작업과 그 과정의 오류가 사라집니다.**

### 우선순위

| 우선순위 | 의미 | 샘플 | 영상 |
|---|---|---|---|
| **MUST** | 없으면 해당 도메인이 동작하지 않음 | 13 | 10 |
| **SHOULD** | 특정 지표나 분석이 불가능해짐 | 13 | 11 |
| **NICE** | 있으면 유용 | 17 | 13 |

MUST가 적은 것이 의도입니다. **협의에서 반드시 지켜야 할 선을 좁게 잡아야** vendor와의 합의가 현실적입니다.

`PRIORITY_CONDITION` 열에는 **시험 설계에 따라 우선순위가 올라가는 조건**이 적혀 있습니다. 예를 들어 `CL_LABID`는 기본 SHOULD이지만 복수 central lab을 분리 운영하는 시험에서는 MUST입니다. 협의 전에 해당 시험이 어느 조건에 걸리는지 먼저 확인하시면 됩니다.

`REVIEW_NOTE` 열에는 v0.1에서 무엇이 어떻게 바뀌었는지가 기록되어 있습니다.

### MUST를 확보하지 못하면

[16번 문서 2.3](../16-external-data-format-draft.md)에 항목별 대안을 정리해 두었습니다. 원칙은 하나입니다. **계산할 수 없게 된 지표는 0%나 N/A로 표시하지 않고 화면에서 제외**하고 사유를 남깁니다. 근거 없는 숫자를 보여주는 것보다 없다고 말하는 편이 낫습니다.

## 예시 행이 보여주는 것

예시 데이터는 실재하지 않는 가상의 시험(`ABC-301`)입니다. 각 행은 대조에서 마주치는 상황 하나씩을 나타냅니다.

### EXT_SAMPLE_RECON

| 행 | 피험자 | 상황 | 앱의 판정 |
|---|---|---|---|
| 1 | 1023-007 | PK pre-dose, 정상 | 매칭, 분석 완료 |
| 2 | 1023-007 | **같은 방문의 PK 1h.** `TPTNUM`으로만 1행과 구분됨 | 매칭, 분석 완료 |
| 3 | 1023-012 | EDC는 채취 Y인데 lab 미수령 | `EDC_Y_NOT_RECEIVED` |
| 4 | 1023-015 | lab에는 있는데 EDC 미기록 | `RECEIVED_NOT_IN_EDC` |
| 5 | 1023-021 | 채취일이 EDC 08-20, lab 08-21 | `MATCHED_DISCREPANT` |
| 6 | 1023-024 | 용혈로 분석 불가, 재채취 불가 | `WAIVED (ISSUE_BLOCKED)` — 분모 제외 |
| 7 | 1023-030 | 배송 중, 기한 내 | `PENDING` |
| 8 | 1023-024 | 6행의 재채취 (`REPEATSEQ = 2`) | 매칭, 분석 배정됨 |

2행이 `TPTNUM`을 매칭 키에 넣어야 하는 이유를 보여줍니다. 1행과 2행은 **같은 피험자·같은 방문·같은 kit 유형**이므로, timepoint 없이는 구분되지 않습니다.

6행과 8행의 관계도 중요합니다. 같은 timepoint의 최초 채취와 재채취가 `REPEATSEQ`로 구분되며, 최초 건은 예외 처리되고 재채취 건이 추적을 이어받습니다.

### EXT_IMAGE_RECON

| 행 | 피험자 | 상황 | 앱의 판정 |
|---|---|---|---|
| 1 | 1023-007 | 정상, 2인 판독 완료 | 매칭, 판독 완료 |
| 2 | 1023-012 | EDC는 촬영 Y인데 BICR 미업로드 | `EDC_Y_NOT_RECEIVED` |
| 3 | 1023-015 | BICR에는 있는데 EDC 미기록 | `RECEIVED_NOT_IN_EDC` |
| 4 | 1023-021 | EDC는 CT, BICR은 MRI | `MATCHED_DISCREPANT` |
| 5 | 1023-024 | QC 실패 (조영제 누락) | QC 실패 집계, 재촬영 요청 |
| 6 | 1023-024 | 5행의 재촬영 (`IMGSEQ = 2`) | 매칭, 판독 배정됨 |
| 7 | 1023-030 | 촬영 후 업로드 대기, 기한 내 | `PENDING` |

4행이 **양쪽의 검사 방법을 각각 받아야 하는 이유**입니다. `EDC_MODALITY`와 `BICR_MODALITY`를 따로 두지 않으면 이 불일치를 잡을 수 없습니다.

## 검토하실 때

- **MUST / SHOULD / NICE 구분이 타당한지**를 먼저 봐주시면 좋겠습니다. 이 구분이 곧 vendor 협의에서 어디까지 양보할 수 있는지를 정합니다.
- vendor가 실제로 제공하기 어려울 것 같은 MUST 항목이 있다면 알려주세요. 그 항목이 없을 때 앱이 무엇을 포기해야 하는지 함께 정리하겠습니다.
- 컬럼명은 협의 과정에서 vendor 것을 따라도 무방합니다. 이름을 맞추는 것보다 **의미가 빠지지 않는 것**이 중요합니다.


---

# CFG10 Waiver Rule Worksheet 사용법

[S-02-6 / DP-13-7](../11-risks-and-open-questions.md) — **해결 불가 이슈가 어느 단계를 예외 처리할지**를 유형별로 확정하기 위한 양식입니다. 결과는 [`CFG10`](../13-trial-configuration.md) 시트가 됩니다.

## 1. 채우는 칸

왼쪽 8열은 제가 채워둔 참고 정보이고, **오른쪽 7열이 기입 칸**입니다.

| 칸 | 내용 |
|---|---|
| `EXISTS_IN_TRIAL` | `Y`/`N` — 이 유형이 우리 시험에 존재하는가 |
| `UNRESOLVABLE_OCCURS` | `Y`/`N` — **해결 불가 판정이 실제로 내려지는가** |
| `BLOCKED_STAGES` | 불가능해지는 단계. 쉼표 구분 또는 `ALL_INCOMPLETE` |
| `WAIVER_TYPE` | `ISSUE_BLOCKED` / `PROTOCOL_EXEMPT` / `OPERATIONAL_WAIVER` |
| `DECIDED_BY` | 판단한 사람 또는 기능 (CDM / Biomarker / Imaging) |
| `BASIS_DOC` | 근거 문서명 |
| `NOTE` | 비고 |

`UNRESOLVABLE_OCCURS = N`이면 나머지는 비워두시면 됩니다. **그 유형은 `CFG10`에 들어가지 않습니다.**

선택 가능한 단계 코드는 [`CFG10_STAGE_REFERENCE_v0.1.csv`](CFG10_STAGE_REFERENCE_v0.1.csv)에 있습니다.

## 2. 판단 기준 한 줄

유형마다 이 질문 하나만 던지면 됩니다.

> **이 이슈가 끝까지 해결되지 않으면, 물리적으로 완료 처리가 불가능해지는 단계는 무엇인가.**

"어려워지는" 단계나 "늦어지는" 단계가 아닙니다. **그 데이터·검체·영상 없이 그 단계를 완료로 찍을 수 있는가**로 환원하면 답이 대체로 하나로 모입니다.

`SUGGESTED_BLOCKED_STAGES`는 이 기준으로 제가 미리 채운 제안값입니다. 동의하시면 그대로 `BLOCKED_STAGES`에 옮기시고, 다르면 고쳐주시면 됩니다. **제안과 결정을 다른 열에 둔 이유는 나중에 왜 그렇게 정했는지 추적하기 위함**입니다.

## 3. 먼저 걸러낼 세 가지

실무에서 자주 섞이는 지점입니다. **첫 번째는 `CFG10`의 대상이 아닙니다.**

| 상황 | 올바른 처리 | 워크시트 |
|---|---|---|
| **기대 자체가 잘못됨** (방문이 없었는데 항목이 생성됨) | 데이터·설정 정정 | `UNRESOLVABLE_OCCURS = N` |
| 프로토콜상 해당 없음으로 확인 | `PROTOCOL_EXEMPT` | 기입 |
| 해야 하는데 영구히 불가능 | `ISSUE_BLOCKED` | 기입 |

제안값에 "주의 — 기대 자체가 잘못된 경우일 수 있음"으로 적힌 유형(`DATA_NOT_COLLECTED`, `NOT_COLLECTED`, `NOT_PERFORMED`)이 특히 이 혼동이 생기는 곳입니다.

## 4. 규칙이 필요한 유형은 소수입니다

제안값을 보시면 분포가 이렇습니다.

| 도메인 | 후보 유형 | 규칙 제안 |
|---|---|---|
| QUERY | 15 | **5** |
| SAMPLE | 10 | 9 |
| IMAGE | 8 | 7 |

쿼리 유형은 대부분 **빈 값이나 불일치가 남더라도 후속 단계를 완료할 수 있어** 예외 처리가 필요 없습니다. 검체와 영상은 물건 자체가 없어지거나 못 쓰게 되는 경우가 많아 비율이 높습니다.

긴 꼬리는 비워두셔도 안전합니다. 규칙이 없으면 예외 처리가 안 되고, 그러면 backlog에 남아 눈에 띕니다 ([개념 13](../13-trial-configuration.md) 4.10).

## 5. Phase 1에는 QUERY만 필요합니다

사양 범위가 Phase 0+1이고 거기에는 검체·영상 도메인이 없습니다. **지금 확정이 필요한 것은 `PHASE = 1` 행, 즉 QUERY 15개뿐**입니다.

검체·영상은 Phase 2 착수 시점에 central lab과 BICR vendor의 실제 issue code를 손에 들고 하시면 됩니다. 지금 채워두셔도 무방하지만 그때 다시 볼 가치가 있습니다.

## 6. 가장 빠른 채우기 순서

```
① 지난 시험의 EDC 쿼리 export를 받습니다
② QUERYTYPE 별 건수를 셉니다
③ 상위 10개만 봅니다
④ 그중 "끝까지 해결 안 된 채 종결된" 건이 있는 유형을 고릅니다  ← UNRESOLVABLE_OCCURS = Y
⑤ 그 유형에만 BLOCKED_STAGES 를 정합니다
⑥ 워크시트에 없는 사내 고유 유형은 빈 행에 추가합니다
```

④가 핵심입니다. 유형 목록은 문서에서 얻을 수 있지만, **"해결 불가 판정이 실제로 내려지는가"는 과거 데이터에서만 확인**됩니다.

### 어디서 찾는가

| 필요한 정보 | 출처 | 소유자 |
|---|---|---|
| 쿼리 유형 목록 | EDC의 query/discrepancy 설정, Data Validation Specification | CDM / EDC builder |
| 실제 발생 분포 | EDC 쿼리 export의 `QUERYTYPE` 빈도 | CDM |
| 해결 불가 처리 관행 | DMP의 쿼리 종결 규칙, unresolvable·NA 처리 절차 | CDM lead |
| 검체 이슈 유형 | Central lab manual의 issue code 목록 | Biomarker mgr / central lab |
| 검체 이슈 → 분석 가능 여부 | Bioanalytical lab의 sample acceptance criteria | Bioanalytical lab |
| 영상 이슈 유형 | Imaging Manual의 QC failure reason | Imaging mgr / BICR vendor |
| 영상 이슈 → 판독 가능 여부 | Imaging Review Charter의 evaluability 규정 | Imaging mgr / BICR |

문서에 **"이 이슈는 어느 단계를 막는다"가 적혀 있는 경우는 없습니다.** 문서에서 얻는 것은 유형 목록이고, 차단 범위는 기능별 리드의 판단으로 채워야 합니다. 그래서 `DECIDED_BY` 칸을 두었습니다.

## 7. 함께 결정이 필요한 것 두 가지

워크시트 밖의 항목이지만 같이 정해져야 합니다.

### 7.1 `unresolvable` 판정은 어디서 오는가

현재 문서 간 불일치가 있습니다.

| 위치 | 내용 |
|---|---|
| [사양 05 §2.5](../../spec/05-api-spec.md) | 앱에서 사람이 `PATCH`로 설정 (사유 필수) |
| [golden `DS04`](../../spec/golden/input/DS04_QUERY.csv) | `UNRESOLVABLE` 컬럼으로 파일에서 받음 |
| [개념 12 §4.4](../12-standard-source-templates.md) | 해당 컬럼 없음 |

EDC 쿼리에는 보통 `unresolvable` 상태가 없고 closed/cancelled만 있으므로 **앱에서 사람이 판정하는 쪽**이 현실적이라고 봅니다. 결정하시면 세 문서를 일치시키겠습니다.

### 7.2 조직 표준으로 둘 것인가 시험별로 둘 것인가

`CFG10`은 시험별 설정이지만, 매 시험 새로 채우는 것은 부담입니다. **조직 표준 기본값을 등록하고 시험별로 덮어쓰는 방식**을 권고합니다 ([개념 13](../13-trial-configuration.md) 6장의 조직 표준 템플릿과 같은 구조).
