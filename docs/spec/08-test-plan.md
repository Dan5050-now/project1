# 08. 테스트 계획

## 1. 계층

| 계층 | 대상 | 비중 | 실행 |
|---|---|---|---|
| 단위 | 순수 함수 (기한 계산, 조건식, 상태 판정) | 높음 | 매 커밋 |
| **Golden** | **엔진 전체 (입력 → 지표)** | **최고** | 매 커밋 |
| 통합 | 업로드 → 확정 → 엔진 → API | 중간 | 매 커밋 |
| 권한 | 역할별 시나리오 | 높음 | 매 커밋 |
| 성능 | N-1~N-5 | — | 주 1회 |
| 인수 | 실제 시험 데이터 대 엑셀 | — | Phase 1 완료 판정 |

Golden 계층이 최우선입니다. **이 프로젝트의 실패 모드 1순위가 숫자 불일치**이므로 ([개념 11](../concept/11-risks-and-open-questions.md) R1), 숫자를 지키는 테스트가 가장 중요합니다.

## 2. Golden dataset 테스트

### 2.1 실행

```
1. GOLD-001 시험 생성, CFG01~CFG06 적재
2. DS01~DS04 업로드 및 확정
3. as_of = 2026-09-30 으로 엔진 실행
4. stage_status 현재 행을 expected/EXPECTED_STAGE_STATUS.csv 와 대조
5. metric_fact 를 expected/EXPECTED_METRICS.csv 와 대조
6. validation_finding 을 expected/EXPECTED_FINDINGS.csv 와 대조
```

### 2.2 대조 규칙

| 항목 | 규칙 |
|---|---|
| 항목 수준 | `expected`에 있는 행은 **정확히 일치**. 없는 조합은 `NOT_DUE` 또는 `NOT_APPLICABLE`이어야 함 |
| 지표 | `due`/`completed`/`backlog`/`overdue`/`waived` 정수 일치, `rate` 소수 4자리 일치 |
| `rate` 공란 | `NULL`이어야 함. **`0`이면 실패** |
| 비활성 단계 | `metric_fact`에 행이 **존재하지 않아야** 함. 0 행이 있으면 실패 |
| 검증 결과 | 코드·심각도·대상이 일치. 추가 경고는 허용, 누락은 실패 |

3행과 4행이 특별히 중요합니다. **`N/A`를 `0`으로, "지표 없음"을 "0%"로 만드는 회귀**가 가장 흔하고 가장 설명하기 어렵습니다.

### 2.3 필수 검증 케이스

[golden/README.md](golden/README.md) 4장의 E1~E11, E17~E20이 각각 개별 테스트 케이스입니다. 하나라도 실패하면 빌드가 깨집니다.

검토로 추가된 두 규칙은 별도 테스트로 둡니다.

```python
def test_waiver_scope_follows_issue_type():
    # E7 — CODING_UNRESOLVABLE 은 coding 만 막는다
    item = item_of('G-001', 'V1', 'AE')
    assert status(item, 'coding') == 'WAIVED'
    assert status(item, 'sign')   == 'PENDING'      # 전부 막으면 실패

def test_transfer_moves_whole_subject():
    # E20 — 이전 시 전 항목이 새 사이트로 이동한다
    assert site_of(item_of('G-007', 'V1', 'DM')) == 'S02'   # S01에서 수행됐지만 S02
    assert site_of(item_of('G-007', 'V2', 'VS')) == 'S02'
    assert count_items(site='S01', subject='G-007') == 0     # S01에 흔적 없음

def test_transfer_with_open_items_is_flagged():
    # E20 — 이전 시점 미종결은 막지 않되 반드시 드러낸다
    assert metric('quality.transfer_with_open_items').value == 1
    assert finding('X9', subject='G-007') is not None
```

### 2.4 Simpson 회귀 테스트

```python
def test_rollup_is_not_average_of_rates():
    trial = metric('edc.entry.rate', level='TRIAL')
    s01   = metric('edc.entry.rate', level='SITE', site='S01')
    s02   = metric('edc.entry.rate', level='SITE', site='S02')
    assert trial.rate == Decimal('0.8182')
    assert round((s01.rate + s02.rate) / 2, 4) == Decimal('0.8167')
    assert trial.rate != (s01.rate + s02.rate) / 2      # 핵심
```

마지막 단언이 목적입니다. 구현이 하위 비율을 평균하면 이 테스트가 잡습니다.

## 3. 단위 테스트

| 대상 | 케이스 |
|---|---|
| `determine_status` | 판정 순서 4단계. 순서를 바꾸면 실패하도록 구성 |
| `resolve_trigger` | 7개 트리거 × 선행 미완료 |
| `parse_grace` | 정수 / `N/A` / `DBL_BASED` / 잘못된 값 |
| 부분 날짜 | `LATEST` / `EARLIEST` / `EXCLUDE` |
| 조건식 | 연산자 전체 + **NULL 피연산자는 false** |
| 매칭 키 정규화 | 대소문자·공백. `01` vs `1`은 **같아지지 않아야 함** |
| 쿼리 기한 | 소유자별 + DEFAULT 폴백 |
| 롤업 | `due=0` → `NULL` |

### 3.1 판정 순서 테스트

```python
def test_waiver_beats_completion():
    """예외 판정이 완료 판정보다 먼저여야 한다."""
    item = make_item(completed=True, waived=True)
    assert determine_status(item, 'entered') == 'WAIVED'
```

순서가 뒤바뀌면 이미 완료된 항목이 분모에서 빠지는 오류가 생깁니다.

## 4. 통합 테스트

| # | 시나리오 | 기대 |
|---|---|---|
| I-1 | 업로드 → 검증 → 미리보기 → 확정 → 엔진 → 조회 | 전 단계 성공, 스냅샷 `READY` |
| I-2 | 같은 파일 재업로드 | 중복 감지, 지표 불변, 감사 로그 없음 |
| I-3 | 누적 파일 재업로드 (일부 변경) | 변경 행만 갱신, 감사 로그는 변경분만 |
| I-4 | 설정 변경 후 활성화 | 새 스냅샷 생성, **과거 스냅샷 값 불변** |
| I-5 | 엔진 실패 | 스냅샷 `FAILED`, 이전 스냅샷 계속 조회 가능 |
| I-6 | DS03 먼저, DS01 나중 | `I2` 보류 후 자동 재처리 |
| I-7 | 증분 전송 | 기간 밖 항목 상태 불변 |
| I-8 | 일 배치 (날짜만 경과) | `PENDING` → `OVERDUE` 전이, 항목 생성 없음 |
| I-9 | 사이트 이전 Drop 반영 | `X7` 경고, 이력 추가, **전 항목 재귀속**, 과거 스냅샷 불변 |
| I-11 | `SITETRFDT` 없는 이전 | 추출일로 대체, `X10` 경고, `transfer_date_source='INFERRED'` |
| I-10 | `CFG10` 규칙 없는 해결 불가 이슈 | 예외 처리 안 됨, `X8` 경고, backlog 유지 |

I-4가 [개념 08](../concept/08-platform-services.md) 4.2 규칙 3의 검증입니다.

## 5. 권한 테스트

### 5.1 역할 시나리오

각 역할 템플릿으로 로그인해 다음을 확인합니다.

| 검사 | 기대 |
|---|---|
| 권한 없는 모듈 | 내비에 없음, API 403 |
| 읽기 전용 역할의 쓰기 | 403 `write-forbidden` |
| 범위 밖 사이트 조회 | 404 (범위 밖과 부재를 구분하지 않음) |
| 범위 밖 사이트가 롤업에 포함되는가 | 포함되지 않아야 함 |

### 5.2 마스킹 누수 테스트

```python
@pytest.mark.parametrize('path', [
    '/api/v1/trials/1/subjects/',
    '/api/v1/trials/1/subjects/1/timeline/',
    '/api/v1/trials/1/items/',
    '/api/v1/trials/1/export/items/',        # export 경로
    '/api/v1/trials/1/export/metrics/',
])
def test_no_blinded_leak(blinded_user, path):
    body = get(path, user=blinded_user).content
    assert b'ARM_1' not in body and b'STRAT_A' not in body
```

**export 경로를 반드시 포함**합니다. 마스킹이 빠지는 전형적 위치이기 때문입니다 ([개념 08](../concept/08-platform-services.md) 2.4, [07](07-rbac-audit-spec.md) 2.4).

### 5.3 감사 추적 테스트

| 검사 | 기대 |
|---|---|
| 컨텍스트 없는 저장 | `AuditContextMissing` 예외 |
| 감사 로그 UPDATE·DELETE | DB 권한 거부 |
| `WAIVED` 처리 시 사유 누락 | CHECK 제약 위반 |
| 엔진 실행 | `actor_type='ENGINE'` 1건 |
| `WAIVED` 전이 | 항목 단위 기록 |

## 6. 성능 테스트

| 요구 | 데이터 | 기준 |
|---|---|---|
| N-1 화면 2초 | 60만 항목 | `/metrics/` p95 < 500 ms |
| N-2 드릴다운 1초 | 동일 | `/items/` 1,000행 p95 < 1 s |
| N-3 업로드 5분 | 10만 행 | 검증 포함 |
| N-4 재생성 15분 | 60만 항목 | 전체 재계산 |
| N-5 동시 50명 | — | 오류율 0 |

합성 데이터 생성기를 함께 만듭니다. `scripts/gen_perf_data.py`.

## 7. 인수 테스트 (Phase 1 완료 판정)

### 7.1 절차

```
1. 대상 시험 선정 (개념 10 9장 기준)
2. 담당자가 만든 기존 엑셀 리포트와 같은 기준일로 앱 실행
3. 지표별로 숫자 대조
4. 불일치 건은 드릴다운으로 원인 규명
```

### 7.2 판정

| 결과 | 판정 |
|---|---|
| 숫자 일치 | 통과 |
| 불일치하나 **원인이 정의 차이로 설명됨** | 통과. 지표 정의 등록부에 기록 |
| 불일치하고 원인 불명 | **실패** |

두 번째 행이 중요합니다. 엑셀이 항상 옳은 것은 아닙니다. **설명할 수 있으면 통과**이고, 설명할 수 없으면 실패입니다.

### 7.3 기록

대조 결과는 시험별 문서로 남깁니다. 정의 차이로 판정된 항목은 [개념 15](../concept/15-metric-specification.md)의 지표 정의에 반영합니다.

## 8. CI

```yaml
on: [push, pull_request]
jobs:
  test:
    steps:
      - lint (ruff, black --check)
      - typecheck (mypy)
      - unit
      - golden            # 실패 시 이후 단계 중단
      - integration
      - permission
```

golden 실패 시 중단하는 이유는 **엔진이 틀린 상태에서 다른 테스트 결과가 의미가 없기** 때문입니다.

## 9. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-08-1 | 성능 테스트 환경을 운영과 동일 사양으로 할 것인가 | 동일 사양 권고 |
| S-08-2 | 인수 테스트 대상 시험 | DP-10-3 |
| S-08-3 | golden dataset에 Phase 2 도메인을 언제 추가할 것인가 | Phase 2 착수 시 |
