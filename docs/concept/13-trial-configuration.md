# 13. Trial Configuration Template

*검토 반영 신규 문서 (요구사항 8)*

## 1. 목적

시험 설계 요소 중 **앱이 데이터를 처리하는 데 필요한 정보**를 표준 template으로 받습니다. 사용자가 시험 시작 시 한 번 채워 업로드하면, 앱이 그 설정을 적용해 기대 항목을 생성하고 지표를 계산합니다.

[12](12-standard-source-templates.md)의 source template이 **주기적으로 들어오는 실적 데이터**라면, 이 문서의 configuration template은 **시험당 한 번 정의하고 필요 시 개정하는 설정**입니다.

```
  Trial Configuration Template  (시험당 1회, 개정 시 버전 증가)
        │
        ├── 방문 스케줄, SoA        → 무엇이 언제 나와야 하는가
        ├── 유예 기간               → 언제부터 밀린 것인가
        ├── 단계 범위 규칙          → 무엇이 분모에 들어가는가
        ├── 지표 on/off             → 무엇을 볼 것인가
        └── 대상 목록               → 누구에게 적용되는가
```

## 2. 설정이 지표를 바꾼다는 사실

이 문서의 설정은 단순한 환경 변수가 아닙니다. **유예 기간 하나만 바꿔도 모든 사이트의 overdue 건수가 바뀝니다.** 따라서 configuration은 다음 성격을 가집니다.

| 성격 | 내용 |
|---|---|
| 버전 관리 대상 | `trial_config_version`이 지표 계산 좌표에 포함됨 ([03](03-core-concept-model.md) 7.2) |
| 감사 추적 대상 | 모든 변경이 누가·언제·무엇을·왜로 기록됨 |
| 소급 재계산 금지 | 과거 스냅샷은 그 당시 설정으로 계산된 값을 유지 |
| 변경 영향 미리보기 | 적용 전에 지표 변화를 보여줌 (Phase 2) |

## 3. Template 구성

하나의 Excel 워크북에 시트로 구성하는 것을 권고합니다. 시트별로 CSV 업로드도 가능하게 합니다.

| 시트 | 이름 | 내용 | 필수 |
|---|---|---|---|
| `CFG01` | Trial Settings | 시험 전역 설정 | ● |
| `CFG02` | Visit Schedule | 방문 정의와 윈도우 | ● |
| `CFG03` | Schedule of Activities | 방문 × 활동 매트릭스 | ● |
| `CFG04` | Stage Settings | 단계별 유예 기간과 on/off | ● |
| `CFG05` | Query Settings | 쿼리 소유자별 기한 | 권장 |
| `CFG06` | Stage Scope Rules | partial SDV, 코딩·서명 대상 | 권장 |
| `CFG07` | Subject Target Lists | 피험자별 적용 대상 목록 | 선택 |
| `CFG08` | Metric Switches | 지표 적용 여부 | 권장 |
| `CFG09` | Code Lists | 코드값 목록 | ● |

## 4. 시트 명세

### 4.1 CFG01 — Trial Settings

`KEY` / `VALUE` 2열 구조입니다.

| KEY | 예시 값 | 설명 |
|---|---|---|
| `STUDYID` | ABC-301 | 시험 식별자 |
| `STUDY_TITLE` | — | 시험명 |
| `PHASE` | 3 | 상 |
| `ANCHOR_RULE` | `RANDDT` | 방문 윈도우 기준일. `RANDDT` / `ENRLDT` / `FIRSTDOSEDT` |
| `DAY_BASIS` | `CALENDAR` | 유예 기간 계산 기준. **기본 `CALENDAR`** |
| `TIMEZONE` | Asia/Seoul | 기준 시간대 |
| `PARTIAL_DATE_RULE` | `LATEST` | 부분 날짜 처리. `EARLIEST` / `LATEST` / `EXCLUDE` |
| `DBL_PLANNED_DT` | 2027-03-31 | freeze·lock 기한의 기준 |
| `INTERIM_DBL_DT` | 2026-12-15 | 중간 DBL (복수 가능) |
| `DISCONT_VISIT_RULE` | `FOLLOWUP_ONLY` | 탈락 후 방문 처리. `ALL_NA` / `FOLLOWUP_ONLY` / `ALL_EXPECTED` |
| `BLINDED` | `Y` | 눈가림 시험 여부. 마스킹 적용 여부 결정 |

### 4.2 CFG02 — Visit Schedule

| 컬럼 | 필수 | 설명 |
|---|---|---|
| `VISITID` | ● | 방문 코드. source dataset의 `VISITID`와 일치해야 함 |
| `VISITNAME` | ● | 표시명 |
| `VISITNUM` | ● | 정렬 순서 |
| `VISITTYPE` | | `SCREENING` / `TREATMENT` / `FOLLOWUP` / `UNSCHEDULED` |
| `OFFSET_DAYS` | ● | 기준일로부터의 목표일 |
| `WINDOW_BEFORE` | ● | 윈도우 하한 (일) |
| `WINDOW_AFTER` | ● | 윈도우 상한 (일) |
| `APPLY_COHORT` | | 적용 코호트. 비우면 전체 |
| `APPLY_CONDITION` | | 조건식 (4.10) |

### 4.3 CFG03 — Schedule of Activities

방문 × 활동 매트릭스입니다. **행 하나가 "이 방문에서 이 활동이 수행된다"는 사실 하나**를 나타냅니다.

| 컬럼 | 필수 | 설명 |
|---|---|---|
| `VISITID` | ● | 방문 코드 |
| `ACTIVITY_TYPE` | ● | `FORM` / `SAMPLE` / `IMAGE` |
| `ACTIVITY_CODE` | ● | 폼 코드 / kit 유형 / modality. source dataset의 `FORMID`·`KITTYPE`·`MODALITY`와 일치 |
| `ACTIVITY_NAME` | | 표시명 |
| `EXPECTED_COUNT` | | 기대 개수. 기본 1 |
| `FORM_TYPE` | | `STANDARD` / `LOG`. LOG는 entry 분모 제외 |
| `SAE_FLAG` | | 해당 폼이 SAE 관련인지 (investigator sign 구분용) |
| `APPLY_CONDITION` | | 조건식 (4.10) |
| `TARGET_LIST` | | CFG07의 목록 이름. 지정 시 그 목록의 피험자에게만 적용 |

`TARGET_LIST`가 검토에서 언급된 **"serum pregnancy sample이 필요한 피험자 목록"** 같은 경우를 처리하는 장치입니다 (4.8).

### 4.4 CFG04 — Stage Settings

각 단계의 유예 기간과 적용 여부를 정의합니다. **검토에서 확정된 기본값**이 반영되어 있습니다.

| `DOMAIN` | `STAGE_CODE` | `ENABLED` | `DUE_TRIGGER` | `GRACE_DAYS` | 비고 |
|---|---|---|---|---|---|
| EDC | `entered` | Y | `VISIT_DATE` | **14** | |
| EDC | `sdv` | Y | `ENTRY_DONE` | **60** | |
| EDC | `review` | **Y/N** | `ENTRY_DONE` | **30** | **시험별 on/off** |
| EDC | `coding` | Y | `ENTRY_DONE` | **60** | |
| EDC | `sign` | Y | — | **N/A** | **유예 없음. pending 건수만** |
| EDC | `freeze` | Y | `SIGN_DONE` | `DBL_BASED` | |
| EDC | `lock` | Y | `ALL_STAGES_DONE` | `DBL_BASED` | |
| SAMPLE | `collected` | Y | `VISIT_DATE` | **0** | |
| SAMPLE | `received_central` | Y | **`COLLECTION_DATE`** | **30** | 사이트 출고일 미사용 |
| SAMPLE | `received_bioanalytics` | Y | `CENTRAL_RECEIVED` | TBD | DP-03-8 |
| SAMPLE | `analyzed` | Y | `BIOANALYTICS_RECEIVED` | TBD | DP-03-8 |
| IMAGE | `taken` | Y | `VISIT_DATE` | **0** | |
| IMAGE | `uploaded` | Y | `IMAGE_DATE` | **14** | |
| IMAGE | `qc_passed` | Y | `UPLOAD_DATE` | TBD | DP-03-9 |
| IMAGE | `read` | Y | `ASSIGN_DATE` | TBD | DP-03-9 |

**`ENABLED = N`인 단계는 화면·집계·export에서 완전히 제외**됩니다. 0%로 표시되지 않습니다 ([04](04-domain-concepts.md) 1.4).

`GRACE_DAYS`의 특수값은 다음과 같습니다.

| 값 | 의미 |
|---|---|
| 정수 | 달력일 수 |
| `N/A` | 유예 기간 개념 미적용. `OVERDUE` 상태를 사용하지 않음 |
| `DBL_BASED` | `DBL_PLANNED_DT` 기준으로 역산 |

### 4.5 CFG05 — Query Settings

| `QUERY_OWNER` | `OPEN_GRACE_DAYS` | `ANSWERED_GRACE_DAYS` |
|---|---|---|
| `PV` | **7** | 7 |
| `DM` | **14** | 14 |
| `MM` | **30** | 30 |
| `CRA` | **60** | 60 |
| *(기본값)* | **14** | **30** |

소유자가 목록에 없거나 source data의 `QUERYOWNER`가 비어 있으면 기본값 행을 적용합니다.

### 4.6 CFG06 — Stage Scope Rules

분모에 무엇이 들어가는지를 정의합니다.

| 컬럼 | 설명 |
|---|---|
| `STAGE_CODE` | 대상 단계 |
| `SCOPE_TYPE` | `ALL` / `FORM_LIST` / `PERCENT` / `SUBJECT_LIST` / `SOURCE_FLAG` |
| `SCOPE_VALUE` | 유형에 따른 값 |
| `APPLY_CONDITION` | 조건식 |

**partial SDV의 표현 예시.**

| STAGE_CODE | SCOPE_TYPE | SCOPE_VALUE | 의미 |
|---|---|---|---|
| `sdv` | `SOURCE_FLAG` | `SDVREQFL` | EDC가 내보낸 대상 플래그를 그대로 사용 (**권고**) |
| `sdv` | `FORM_LIST` | `AE,CM,EX,DS` | 지정 폼만 SDV 대상 |
| `sdv` | `PERCENT` | `30` | 피험자의 30%를 SDV 대상으로 (표본 선정 규칙 별도) |
| `sdv` | `SUBJECT_LIST` | `SDV_TARGET_SUBJ` | CFG07의 목록에 있는 피험자만 |
| `coding` | `FORM_LIST` | `AE,CM,MH` | 코딩 대상 폼 |
| `sign` | `ALL` | — | 전체 폼 서명 대상 |

`SOURCE_FLAG`를 권고하는 이유는 EDC가 판정한 결과를 그대로 쓰는 것이 가장 정확하기 때문입니다. EDC가 대상 여부를 내보내지 않는 경우에만 다른 방식을 씁니다.

### 4.7 CFG07 — Subject Target Lists

특정 피험자 집단에만 적용되는 활동이나 규칙을 표현합니다.

| 컬럼 | 설명 |
|---|---|
| `LIST_NAME` | 목록 이름. CFG03·CFG06에서 참조 |
| `LIST_DESC` | 설명 |
| `SUBJID` | 피험자 번호 (한 행에 한 명) |

**사용 예 — serum pregnancy 샘플 대상 피험자.**

```
LIST_NAME              LIST_DESC                          SUBJID
SERUM_PREG_SUBJ        가임기 여성, serum pregnancy 대상    1001-003
SERUM_PREG_SUBJ        가임기 여성, serum pregnancy 대상    1001-007
SERUM_PREG_SUBJ        가임기 여성, serum pregnancy 대상    1023-012
```

CFG03에서 해당 활동 행에 `TARGET_LIST = SERUM_PREG_SUBJ`를 지정하면, **그 목록의 피험자에게만 기대 샘플이 생성**됩니다. 목록에 없는 피험자에게는 `NOT_APPLICABLE`이 되어 분모에 들어가지 않습니다.

> **설계 판단 — 규칙과 목록 중 무엇을 쓸 것인가.**
>
> 위 예시는 `SEX = F AND 가임기` 같은 조건식(4.10)으로도 표현할 수 있습니다. 조건식이 더 우아하고 피험자가 추가될 때 자동 반영됩니다.
>
> 그런데 실무에서는 가임기 판정처럼 **앱이 가진 데이터만으로는 결정할 수 없는 기준**이 자주 등장합니다. 이때 조건식만 제공하면 사용자는 방법이 없습니다. 그래서 **조건식을 우선 권고하되 명시적 목록을 항상 사용할 수 있게** 둡니다. 둘 다 지정되면 목록이 우선합니다.

### 4.8 CFG08 — Metric Switches

시험에서 사용하지 않을 지표를 끕니다.

| 컬럼 | 설명 |
|---|---|
| `METRIC_CODE` | [15](15-metric-specification.md)의 지표 코드 |
| `ENABLED` | `Y` / `N` |
| `REASON` | 끄는 사유. 화면에 표시됨 |

예시입니다.

```
METRIC_CODE                ENABLED  REASON
edc.review.rate            N        본 시험은 data review flagging 미적용
image.qc.fail_rate         N        영상 수집 없음
sample.recon.status        Y
```

**꺼진 지표는 화면·집계·export에서 사라지며, 0이나 N/A로 표시되지 않습니다.** 사유가 함께 표시되어 "왜 이 지표가 없는가"에 앱이 스스로 답합니다.

### 4.9 CFG09 — Code Lists

| 컬럼 | 설명 |
|---|---|
| `LIST_TYPE` | `SUBJECT_STATUS` / `KIT_TYPE` / `MODALITY` / `QUERY_OWNER` / `QUERY_GROUP` / `ISSUE_TYPE` / `WAIVER_TYPE` / `MILESTONE_TYPE` 등 |
| `CODE` | 코드값. source dataset의 값과 일치해야 함 |
| `LABEL` | 표시명 |
| `SORT_ORDER` | 정렬 순서 |
| `ACTIVE` | `Y` / `N` |

업로드된 source data에 이 목록에 없는 코드값이 있으면 검증 단계에서 보고됩니다 ([12](12-standard-source-templates.md) 5.1 S4).

### 4.10 조건식 (APPLY_CONDITION)

조건부 활동과 범위 규칙을 표현하는 간단한 식입니다. **제한된 문법**을 사용합니다. 자유로운 수식을 허용하면 검증도 재현도 어려워지기 때문입니다.

```
허용 항목:
  필드     SEX, COHORT, STRATA1~5, COUNTRY, SITEID, SUBJSTAT, ARM, VISITNUM
  연산자   = != IN NOT IN > >= < <=
  결합     AND OR NOT, 괄호

예시:
  SEX = 'F'
  COHORT IN ('A','B')
  COUNTRY = 'KR' AND VISITNUM >= 3
  SUBJSTAT != 'SCREEN_FAILED'
```

조건식은 파싱 후 **정규화된 형태로 저장**되며, 설정 버전의 일부로 감사 추적됩니다. 조건식 오류는 업로드 시점에 검출됩니다.

## 5. 설정 적용 흐름

```
① Template 업로드
      ↓
② 구조·참조 검증
   - VISITID가 CFG02와 CFG03 간 일치하는가
   - ACTIVITY_CODE가 CFG09의 코드 목록에 있는가
   - TARGET_LIST가 CFG07에 존재하는가
   - 조건식이 파싱되는가
      ↓
③ 영향 미리보기  (Phase 2)
   - 기대 항목 수가 몇 건에서 몇 건으로 바뀌는가
   - 주요 지표가 어떻게 변하는가
      ↓
④ 확정 — 새 trial_config_version 생성
      ↓
⑤ Expectation Engine 재실행 → 새 스냅샷 생성
```

④와 ⑤가 분리된 것이 중요합니다. **설정 확정이 곧바로 과거 데이터를 바꾸지 않습니다.** 새 스냅샷이 생기고, 과거 스냅샷은 과거 설정으로 계산된 값을 유지합니다.

## 6. 기본 설정 제공

시험마다 처음부터 채우게 하면 부담이 큽니다. 다음을 제공합니다.

| 장치 | 내용 |
|---|---|
| 기본값 내장 | CFG04·CFG05의 값은 비워두면 이 문서의 기본값이 적용됨 |
| 시험 복제 | 기존 시험의 설정을 복제해 수정 |
| 조직 표준 | 사내 표준 설정을 템플릿으로 등록해 신규 시험의 출발점으로 사용 |

## 7. 검토 포인트 (Decision Points)

| # | 결정 필요 사항 | 기본 제안 |
|---|---|---|
| DP-13-1 | 9개 시트 구성이 적절한가. 빠진 설정 항목이 있는가 | 실무 검토 필요 |
| DP-13-2 | 4.7의 "조건식 우선, 목록 병용" 방침에 동의하는가 | 동의 권고 |
| DP-13-3 | 4.10 조건식 문법의 범위가 충분한가 | 충분, 부족 시 목록으로 대체 |
| DP-13-4 | CFG03의 SoA를 이 template으로 받을 것인가, 별도 SoA 도구를 쓸 것인가 | 이 template으로 시작, USDM import는 후속 |
| DP-13-5 | 설정 변경 권한을 누구에게 줄 것인가 (시험 리드 / 시스템 관리자) | **시험 리드 + 승인 절차** |
| DP-13-6 | CFG01의 `PARTIAL_DATE_RULE` 기본값 | `LATEST` (보수적 판정) |
