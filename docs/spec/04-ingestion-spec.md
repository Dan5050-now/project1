# 04. 유입 사양

[개념 12](../concept/12-standard-source-templates.md)의 업로드 파이프라인을 구현 수준으로 명세합니다. Phase 1 대상은 `DS01`~`DS04`와 `CFG01`~`CFG09`입니다.

## 1. 파이프라인

```
① 업로드      파일 + 출처 메타데이터 수신, Data Drop 생성 (state=UPLOADED)
      ▼
② 파싱        매핑 적용, staging_record 생성
      ▼
③ 검증        S / C / I / X 4계층 (3장)
      ▼
④ 미리보기    신규·변경·거부 건수, 검증 리포트 (state=VALIDATED)
      ▼
⑤ 확정        사용자 승인 (state=PROMOTED)
      ▼
⑥ 엔진        ExpectationEngine → ProgressEngine → RollupEngine
      ▼
⑦ 스냅샷      state=READY
```

②~③은 Celery 비동기입니다. N-3(10만 행 5분)을 만족하려면 동기 처리로는 불가능합니다.

⑤가 **명시적 승인**인 것이 중요합니다. 자동 반영하면 잘못된 파일이 조용히 지표를 바꿉니다.

## 2. 파싱

### 2.1 파일 수용

| 항목 | 사양 |
|---|---|
| 형식 | CSV(UTF-8, BOM 허용), XLSX |
| 최대 크기 | 200 MB |
| 최대 행 수 | 1,000,000 |
| 구분자 | 쉼표. 탭은 자동 감지 |
| 인코딩 감지 | UTF-8 우선, 실패 시 CP949 시도 후 경고 |

CP949 폴백을 두는 이유는 사내에서 Excel로 저장한 CSV가 흔하기 때문입니다.

### 2.2 매핑 적용

```
for row in file:
    raw        = dict(row)                                # 원본 보존
    normalized = {}
    for app_col, src_col in mapping.column_map.items():
        v = raw.get(src_col)
        v = apply_code_map(app_col, v, mapping.code_map)
        v = coerce_type(app_col, v, template.column_spec)
        normalized[app_col] = v
    staging_record.create(raw=raw, normalized=normalized, source_row_no=n)
```

`raw`를 그대로 보존하는 것이 [02](02-data-model.md) 4.3의 요구입니다.

### 2.3 타입 변환 규칙

| 타입 | 수용 | 결과 |
|---|---|---|
| date | `YYYY-MM-DD`, `YYYY-MM`, `YYYY`, `DDMMMYYYY` | ISO. 부분 날짜는 `partial` 플래그 유지 |
| time | `hh:mm`, `hh:mm:ss` | `hh:mm` |
| Y/N | `Y`/`N`/`1`/`0`/`TRUE`/`FALSE`/`예`/`아니오` | boolean. 비표준 값은 WARN |
| number | 쉼표 제거, 공백 제거 | numeric |
| code | 대소문자 무시 후 코드 목록 대조 | 정규 코드 |

부분 날짜는 **변환 시점에 확정하지 않고 플래그를 유지**합니다. 확정은 엔진에서 `CFG01.PARTIAL_DATE_RULE`로 합니다 ([개념 15](../concept/15-metric-specification.md) 3.2). 변환 단계에서 확정하면 설정이 바뀌어도 반영되지 않습니다.

## 3. 검증 규칙

각 규칙은 **독립 실행 가능한 함수**로 구현합니다. 향후 AI 검증 보조가 같은 인터페이스를 쓰기 위함입니다 ([개념 14](../concept/14-ai-extensibility.md) 3.1).

```python
class Check:
    code: str            # 'S1' ...
    layer: str           # STRUCTURAL | COMPLETENESS | INTEGRITY | CONSISTENCY
    severity: str        # REJECT | WARN
    scope: str           # ROW | FILE | CROSS_DROP
    def run(ctx) -> list[Finding]: ...
```

### 3.1 구조 (S)

| 코드 | 점검 | 심각도 | 범위 |
|---|---|---|---|
| `S1` | 필수 컬럼 존재 | REJECT | FILE |
| `S2` | 자료형 적합 | REJECT | ROW |
| `S3` | 날짜 형식 | REJECT | ROW |
| `S4` | 코드값이 `code_list`에 존재 | REJECT | ROW |
| `S5` | 매칭 키 컬럼 결측 | REJECT | ROW |
| `S6` | 출처 메타데이터 필수 항목 존재 | REJECT | FILE |
| `S7` | 결합형 파일의 양측 원시값 컬럼 존재 | WARN | FILE |

`S1`·`S6`은 FILE 범위이므로 **한 건이라도 실패하면 업로드 전체가 거부**됩니다.

### 3.2 완결성 (C)

| 코드 | 점검 | 심각도 |
|---|---|---|
| `C1` | 필수 항목 결측률이 임계(기본 5%) 초과 | WARN |
| `C2` | 이전 Drop 대비 행 수 20% 이상 감소 | WARN |
| `C3` | 이전 Drop에 있던 사이트가 통째로 누락 | WARN |
| `C4` | 최근 N일(기본 14) 데이터가 없음 | WARN |
| `C5` | `src_extract_on`이 직전 Drop보다 과거 | WARN |
| `C6` | 결합형 파일에서 한쪽 값이 전부 결측 | WARN |
| `C7` | `declared_row_count` ≠ 실제 행 수 | WARN |

`C2`·`C3`이 부분 추출을 잡는 규칙입니다. 표준화 과정이 앱 시야 밖이라는 리스크 R3b의 주 완화 장치입니다.

### 3.3 무결성 (I)

| 코드 | 점검 | 심각도 |
|---|---|---|
| `I1` | 동일 매칭 키 중복 행 | WARN |
| `I2` | `SUBJID`가 `subject`에 없음 | ROW 보류 |
| `I3` | `VISITID`가 `visit_schedule`에 없음 | WARN |
| `I4` | 완료일이 트리거일보다 이전 | WARN |
| `I5` | 미래 날짜 또는 1990년 이전 | WARN |
| `I6` | `FORMID`가 `soa_activity`에 없음 | WARN |

`I2`의 "보류"는 거부와 다릅니다. **행을 보관하되 반영하지 않고**, 해당 피험자가 이후 Drop으로 들어오면 자동 재처리합니다. DS01과 DS03의 전송 순서가 뒤바뀌는 일이 흔하기 때문입니다.

### 3.4 일관성 (X)

| 코드 | 점검 | 심각도 |
|---|---|---|
| `X1` | 플래그 `Y`인데 날짜 결측 | WARN |
| `X2` | 단계 순서 모순 (SDV 완료인데 입력 미완료) | WARN |
| `X3` | dataset 간 모순 | Reconciliation 이관 |
| `X4` | 이전 Drop 대비 상태 역행 | **WARN (강)** |
| `X5` | 탈락 이후 방문 발생 | WARN |
| `X6` | 파일의 `RECON_STATUS`와 앱 판정 불일치 | WARN |

`X4`는 별도 목록으로 화면에 노출합니다. 실무에서 가장 자주 발생하고, 놓치면 지표가 이유 없이 떨어집니다.

### 3.5 설정 파일 검증 (CFG)

| 코드 | 점검 | 심각도 |
|---|---|---|
| `CHK-CFG-001` | `CFG02.VISITID`와 `CFG03.VISITID` 정합 | REJECT |
| `CHK-CFG-002` | `CFG03.ACTIVITY_CODE`가 `CFG09`에 존재 | REJECT |
| `CHK-CFG-003` | `CFG03.TARGET_LIST`가 `CFG07`에 존재 | REJECT |
| `CHK-CFG-004` | 조건식 파싱 성공 | REJECT |
| `CHK-CFG-005` | `CFG04.GRACE_DAYS` 형식 (정수/`N/A`/`DBL_BASED`) | REJECT |
| `CHK-CFG-006` | `CFG08.METRIC_CODE`가 `metric_definition`에 존재 | REJECT |
| `CHK-CFG-007` | `CFG01.ANCHOR_RULE`이 허용값 | REJECT |

설정 파일은 **REJECT만 있고 WARN이 없습니다.** 설정이 부분적으로만 반영되면 지표가 설명 불가능해지기 때문입니다.

## 4. 미리보기

확정 전에 사용자에게 보여주는 내용입니다.

| 영역 | 내용 |
|---|---|
| 요약 | 전체 / 신규 / 변경 / 동일 / 거부 / 경고 건수 |
| 검증 리포트 | 규칙 코드별 건수, 원본 행 번호 포함 목록 |
| 영향 추정 | 확정 시 변경될 항목 수, 주요 지표의 변화 방향 |
| 경고 강조 | `C2`·`C3`·`X4`는 상단 배너로 별도 표시 |

**영향 추정은 지표 값을 계산하지 않고 방향만** 보여줍니다. 정확한 값은 확정 후 엔진이 산출합니다. 미리보기를 위해 엔진을 두 번 돌리는 것은 비용 대비 실익이 없습니다.

## 5. 확정과 반영

### 5.1 멱등 upsert

```
key = (trial, dataset, match_key_hash)
기존 없음 → INSERT
기존 있음 → 값이 다른 필드만 UPDATE + 감사 로그
값 동일   → no-op (감사 로그 없음)
```

값이 같으면 감사 로그를 남기지 않는 것이 중요합니다. 누적 파일을 매주 올리면 대부분의 행이 동일하므로, 이를 기록하면 감사 로그가 무의미하게 폭증합니다.

### 5.2 Drop 간 우선순위

같은 항목이 여러 Feed에 있을 때는 `feed.priority`(정수, 작을수록 우선)를 따릅니다. 동률이면 `src_extract_on`이 최신인 Drop이 우선합니다.

### 5.3 증분 전송 처리

```
if drop.transfer_type == 'INCREMENTAL':
    covered = (drop.period_from, drop.period_to)
    # 기간 밖 항목은 상태를 건드리지 않음
    # 기간 안에 없는 기존 항목도 '미수령'으로 바꾸지 않음
```

[개념 16](../concept/16-external-data-format-draft.md) 4.4의 "기간 밖은 알 수 없음"을 구현합니다.

## 6. 감사 기록

| 시점 | `action` | `entity_type` |
|---|---|---|
| 업로드 | `IMPORT` | `DataDrop` |
| 확정 | `UPDATE` | `DataDrop` (state 전이) |
| 데이터 반영 | `CREATE`/`UPDATE` | 대상 엔티티 (행 단위) |
| 엔진 실행 | `ENGINE_RUN` | `EngineRun` (실행 단위 1건) |

행 단위 반영 로그는 건수가 많으므로 **변경된 필드만** `old_value`/`new_value`에 담습니다.

## 7. 오류 처리

| 상황 | 처리 |
|---|---|
| 파싱 실패 (파일 깨짐) | Drop `REJECTED`, 원인 표시 |
| 검증 REJECT 다수 | Drop은 `VALIDATED`로 두고 확정 버튼 비활성화 |
| 확정 중 실패 | 트랜잭션 롤백, Drop `VALIDATED`로 복귀 |
| 엔진 실패 | 스냅샷 `FAILED`, 이전 스냅샷 유지, 관리자 알림 |

**엔진 실패 시 이전 스냅샷이 계속 조회된다는 점**이 중요합니다. 화면이 비지 않습니다.

## 8. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-04-1 | `C1` 결측률 임계 5%가 적절한가 | 시험별 설정 |
| S-04-2 | `C2` 행 수 감소 20%가 적절한가 | 시험별 설정 |
| S-04-3 | 동일 파일 재업로드를 강제 허용할 수 있게 할 것인가 | **허용**, 사유 입력 필수 |
| S-04-4 | 파일 보관 기간 | 원본 파일은 스냅샷 보존 기간과 동일 |
