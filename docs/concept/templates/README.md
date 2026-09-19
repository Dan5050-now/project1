# Template 파일 (Draft v0.1)

[16. External Data Source Format — Draft v0.1](../16-external-data-format-draft.md)의 실물 template입니다.

Excel에서 그대로 열어 검토하실 수 있습니다. 파일은 **UTF-8 with BOM**으로 저장되어 있어 Excel에서 한글이 깨지지 않습니다.

| 파일 | 내용 |
|---|---|
| [`TRANSFER_HEADER_v0.1.csv`](TRANSFER_HEADER_v0.1.csv) | 전송 단위의 출처 메타데이터. **매 전송마다 동반** |
| [`EXT_SAMPLE_RECON_v0.1.csv`](EXT_SAMPLE_RECON_v0.1.csv) | 샘플 대조. 헤더 + 예시 8행 |
| [`EXT_IMAGE_RECON_v0.1.csv`](EXT_IMAGE_RECON_v0.1.csv) | 영상 대조. 헤더 + 예시 7행 |

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

- 컬럼이 **사내 external data reconciliation file에 실제로 있는지**를 먼저 봐주시면 좋겠습니다. 없는 컬럼은 빼고, 있는데 빠진 컬럼은 알려주시면 추가하겠습니다.
- 컬럼명은 사내 명칭이 있으면 그쪽을 따르는 것이 맞습니다. 이름을 맞추는 것보다 **의미가 빠지지 않는 것**이 중요합니다.
- 필수(●) 표시된 컬럼은 [16번 문서](../16-external-data-format-draft.md) 5장과 6장에 정리되어 있습니다. 샘플 8개, 영상 7개뿐입니다.
