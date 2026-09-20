# 05. API 사양

Django REST Framework 기준입니다. 화면은 이 API를 통해서만 데이터를 읽습니다. **서버 렌더링 화면도 같은 서비스 계층을 호출**하므로, 나중에 프론트엔드를 교체해도 로직이 이동하지 않습니다 ([개념 09](../concept/09-tech-stack.md) 3.3).

## 1. 공통 규약

| 항목 | 사양 |
|---|---|
| Base | `/api/v1/` |
| 인증 | 세션(화면) 또는 Bearer 토큰(외부) |
| 권한 | 모든 엔드포인트에서 모듈·접근수준·데이터범위 3차원 검사 ([07](07-rbac-audit-spec.md)) |
| 페이징 | 커서 기반. `?cursor=&limit=` (기본 100, 최대 1000) |
| 정렬 | `?ordering=field,-field2` |
| 오류 | RFC 7807 `application/problem+json` |
| 시간대 | 응답은 UTC ISO 8601. 표시 변환은 클라이언트 |

### 1.1 계산 좌표 파라미터

지표를 읽는 모든 엔드포인트는 다음을 받습니다. 생략 시 최신 `READY` 스냅샷과 그 좌표를 씁니다.

| 파라미터 | 기본 | 설명 |
|---|---|---|
| `snapshot` | 최신 READY | 스냅샷 ID |
| `basis` | `DUE` | `DUE`/`PROTOCOL`/`FORECAST` |
| `forecast_to` | — | `basis=FORECAST`일 때 필수 |

응답에는 **사용된 좌표가 항상 포함**됩니다.

```json
"meta": {
  "snapshot_id": 812, "as_of": "2026-09-14T08:00:00Z", "is_official": true,
  "assumption_version": 3, "trial_config_version": 2, "metric_def_version": 1,
  "basis": "DUE", "src_extract_on": "2026-09-12"
}
```

좌표 없는 숫자를 응답하지 않는 것이 [개념 03](../concept/03-core-concept-model.md) 7.2의 구현입니다.

### 1.2 마스킹

눈가림 대상 필드는 권한이 없으면 **키는 유지하고 값만 치환**합니다.

```json
{ "subject_code": "1023-007", "arm": null, "arm_masked": true, "strata": null, "strata_masked": true }
```

키를 지우지 않는 이유는 클라이언트가 필드 부재와 마스킹을 구분해야 하기 때문입니다. 마스킹은 **직렬화 계층이 아니라 서비스 계층**에서 적용됩니다. export도 같은 계층을 지나므로 우회 경로가 생기지 않습니다 ([개념 08](../concept/08-platform-services.md) 2.4).

## 2. 엔드포인트

### 2.1 마스터

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/` | 접근 가능한 시험 목록 |
| GET | `/trials/{id}/` | 시험 상세 |
| GET | `/trials/{id}/sites/` | 사이트 목록 (데이터범위 적용) |
| GET | `/trials/{id}/subjects/` | 피험자 목록. `?site=&status=&is_forecast=` |
| GET | `/trials/{id}/subjects/{sid}/` | 피험자 상세 |

### 2.2 지표 조회

#### `GET /trials/{id}/metrics/`

롤업 테이블의 데이터원입니다.

| 파라미터 | 설명 |
|---|---|
| `level` | `TRIAL`/`COUNTRY`/`SITE`/`SUBJECT` (필수) |
| `domain` | `EDC`/`VISIT` |
| `metric` | 지표 코드 복수 지정 가능 |
| `stage` | 단계 코드 복수 지정 가능 |
| `country`, `site`, `subject` | 필터 |
| `group_by` | `owner` 등 분해 축 |

```json
{
  "meta": { ... },
  "results": [
    { "level": "SITE", "site_id": 12, "site_code": "1023", "country_code": "KR",
      "stage_code": "entered",
      "due_count": 1240, "completed_count": 1128, "backlog_count": 112,
      "overdue_count": 34, "waived_count": 8, "rate": 0.9097,
      "aging_median": 6.0, "aging_p90": 19.0 }
  ]
}
```

`rate`가 `null`이면 `N/A`입니다. **0.0과 구분됩니다.**

#### `GET /trials/{id}/metrics/compare/`

비교 모드용입니다. `?snapshot_a=&snapshot_b=`.

두 스냅샷의 `trial_config_version` 또는 `metric_def_version`이 다르면 응답에 경고가 포함됩니다.

```json
"warnings": [
  { "code": "CONFIG_VERSION_DIFFERS", "message": "설정 버전이 다릅니다 (v1 vs v2). 변화의 원인이 실적인지 설정인지 구분할 수 없습니다." }
]
```

### 2.3 드릴다운

#### `GET /trials/{id}/items/`

집계 숫자를 구성하는 개별 항목입니다. **롤업 테이블의 어느 칸을 클릭하든 같은 파라미터 집합으로 도달**합니다.

| 파라미터 | 설명 |
|---|---|
| `domain`, `stage`, `status` | `status=PENDING,OVERDUE` 처럼 복수 |
| `level`, `country`, `site`, `subject` | 범위 |
| `basis`, `snapshot` | 좌표 |
| `waived` | `true`면 예외 항목만 |

```json
{ "results": [
  { "item_id": 88213, "subject_code": "1023-007", "site_code": "1023",
    "visit_code": "C2D1", "activity_code": "AE", "repeat_seq": 1,
    "stage_code": "entered", "status": "OVERDUE",
    "trigger_on": "2026-08-20", "due_on": "2026-09-03", "aging_days": 11,
    "waiver_type": null, "issue_count": 2 }
] }
```

#### `GET /trials/{id}/items/{item_id}/`

항목 1건의 전 단계 상태와 이력입니다. `?history=true`면 SCD2 이력을 함께 반환합니다.

### 2.4 Subject 360

`GET /trials/{id}/subjects/{sid}/timeline/`

방문 축으로 정렬된 도메인별 상태입니다.

```json
{ "subject": { ... },
  "visits": [
    { "visit_code": "V4", "target_on": "2026-06-10", "window": ["2026-06-07","2026-06-13"],
      "actual_on": "2026-06-16", "deviation_type": "OVER", "deviation_days": 3,
      "domains": { "EDC": { "entered": "DONE", "sdv": "OVERDUE" } },
      "issues": [ { "id": 4412, "owner": "DM", "state": "OPEN", "overdue": true } ] }
  ] }
```

### 2.5 이슈

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/{id}/issues/` | `?owner=&state=&overdue=&group=` |
| PATCH | `/trials/{id}/issues/{iid}/` | `unresolvable` 설정. **사유 필수** |

`unresolvable=true` 설정은 대상 항목을 `WAIVED`로 전이시키므로 ([03](03-engine-spec.md) 3.7), `WRITE` 권한과 사유가 모두 필요합니다.

### 2.6 업로드

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/{id}/feeds/` | Feed 목록과 신뢰도 |
| POST | `/trials/{id}/drops/` | 파일 + 출처 메타데이터. 비동기 |
| GET | `/trials/{id}/drops/{did}/` | 상태, 검증 요약 |
| GET | `/trials/{id}/drops/{did}/findings/` | 검증 결과 목록 |
| GET | `/trials/{id}/drops/{did}/findings/export/` | CSV 리포트 |
| POST | `/trials/{id}/drops/{did}/promote/` | 확정 |
| POST | `/trials/{id}/drops/{did}/reject/` | 폐기. 사유 필수 |

`POST /drops/`는 `202 Accepted`와 함께 `drop_id`를 반환하고, 클라이언트는 상태를 폴링합니다.

### 2.7 설정과 가정

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/{id}/configs/` | 버전 목록 |
| GET | `/trials/{id}/configs/{cid}/` | 상세 |
| GET | `/trials/{id}/configs/{cid}/diff/?against=` | 버전 간 차이 |
| POST | `/trials/{id}/configs/` | 업로드 (DRAFT 생성) |
| POST | `/trials/{id}/configs/{cid}/activate/` | 활성화. **사유 필수** |
| GET | `/trials/{id}/assumptions/` 외 | 동일 구조 |

활성화는 엔진 전체 재실행을 유발하므로 `202`를 반환합니다.

### 2.8 스냅샷

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/{id}/snapshots/` | `?official=true` |
| POST | `/trials/{id}/snapshots/` | 공식 스냅샷 생성. `label` 필수 |
| POST | `/trials/{id}/snapshots/{sid}/rebuild/` | 재계산 (관리자) |

### 2.9 지표 정의

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/metric-definitions/` | 전체 목록 |
| GET | `/metric-definitions/{code}/` | `?version=` |

화면의 `?` 아이콘이 이 엔드포인트를 호출합니다.

### 2.10 Export

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/trials/{id}/export/metrics/` | `?format=csv|xlsx|parquet`. **3종 basis 모두 포함** |
| GET | `/trials/{id}/export/items/` | 항목 수준 |
| GET | `/trials/{id}/export/issues/` | |
| GET | `/trials/{id}/export/audit/` | 관리자 전용 |

전 export는 **감사 로그에 기록**되며 마스킹이 적용됩니다.

대용량은 `202`와 함께 비동기 생성 후 다운로드 링크를 제공합니다. 임계는 10만 행입니다.

### 2.11 관리자

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET/POST | `/admin/users/` | |
| GET/POST | `/admin/roles/` | |
| POST | `/admin/user-roles/` | 사용자-시험-역할-범위 배정 |
| GET | `/admin/audit/` | `?trial=&actor_type=&entity_type=&from=&to=` |

## 3. 오류 코드

| HTTP | `type` | 상황 |
|---|---|---|
| 400 | `validation-error` | 파라미터 오류 |
| 400 | `forecast-to-required` | `basis=FORECAST`인데 `forecast_to` 없음 |
| 403 | `module-forbidden` | 모듈 접근 권한 없음 |
| 403 | `scope-forbidden` | 데이터 범위 밖 |
| 403 | `write-forbidden` | 읽기 전용 권한 |
| 404 | `not-found` | 존재하지 않거나 범위 밖 (구분하지 않음) |
| 409 | `snapshot-building` | 스냅샷 생성 중 |
| 409 | `config-conflict` | 활성 설정이 이미 변경됨 (낙관적 잠금) |
| 422 | `reason-required` | 사유 필수 작업에 사유 없음 |
| 429 | `rate-limited` | |

404가 범위 밖과 부재를 **구분하지 않는 것**은 의도입니다. 구분하면 존재 여부가 노출됩니다.

## 4. 성능

| 엔드포인트 | 목표 | 방법 |
|---|---|---|
| `/metrics/` | 500 ms | `metric_fact` 단일 조회 |
| `/items/` | 1 s | 부분 인덱스 + 커서 페이징 |
| `/subjects/{sid}/timeline/` | 1 s | 피험자 단위 조회 |
| `/export/` | 비동기 | 10만 행 초과 시 |

## 5. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-05-1 | 외부 BI 도구의 인증 방식 | 서비스 계정 + 토큰, 읽기 전용 역할 |
| S-05-2 | API 버전 정책 | `/v1/` 고정, 호환 깨지면 `/v2/` |
| S-05-3 | 비동기 export 링크 만료 | 24시간 |
