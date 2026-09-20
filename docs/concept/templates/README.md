# Template 파일 (Draft v0.1)

[16. External Data Source Format — Draft v0.1](../16-external-data-format-draft.md)의 실물 template입니다.

Excel에서 그대로 열어 검토하실 수 있습니다. 파일은 **UTF-8 with BOM**으로 저장되어 있어 Excel에서 한글이 깨지지 않습니다.

| 파일 | 용도 | 내용 |
|---|---|---|
| [`DTS_VARIABLE_REQUEST_v0.2.csv`](DTS_VARIABLE_REQUEST_v0.2.csv) | **vendor와 DTS 협의할 때 건네는 양식** | 전 컬럼 91개. 우선순위·조건·설명·검토 이력 포함, vendor 기입 칸 4개 |
| [`TRANSFER_HEADER_v0.1.csv`](TRANSFER_HEADER_v0.1.csv) | 파일 형식 예시 | 전송 단위의 출처 메타데이터. **매 전송마다 동반** |
| [`EXT_SAMPLE_RECON_v0.1.csv`](EXT_SAMPLE_RECON_v0.1.csv) | 파일 형식 예시 | 샘플 대조. 헤더 43열 + 예시 8행 |
| [`EXT_IMAGE_RECON_v0.1.csv`](EXT_IMAGE_RECON_v0.1.csv) | 파일 형식 예시 | 영상 대조. 헤더 34열 + 예시 7행 |

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
