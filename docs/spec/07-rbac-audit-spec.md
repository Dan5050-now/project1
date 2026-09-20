# 07. 권한·감사 사양

[개념 08](../concept/08-platform-services.md) 2~3장의 구현 사양입니다. **나중에 얹을 수 없는 영역**이므로 Phase 0에서 완성합니다.

## 1. 인증

| 항목 | 사양 |
|---|---|
| 1차 | OIDC (Authorization Code + PKCE). `django-allauth` |
| 대체 | SAML 2.0 |
| 개발 구간 | 자체 계정 (DP-08-1 미확정 동안) |
| 세션 | 8시간 만료, 30분 비활동 자동 로그아웃 |
| 계정 생명주기 | 생성 / 비활성화 / 재활성화. **삭제 없음** |

계정을 삭제하지 않는 이유는 감사 로그의 행위자를 특정할 수 없게 되기 때문입니다. 비활성 계정은 로그인만 차단되고 참조는 유지됩니다.

### 1.1 인증 계층 격리

```
AuthAdapter (인터페이스)
  ├─ OIDCAdapter
  ├─ SAMLAdapter
  └─ LocalAdapter        # 개발·대체용
```

사내 SSO 방식이 확정되면 어댑터만 교체합니다. 애플리케이션 코드는 `request.user`만 봅니다.

## 2. 권한 모델

### 2.1 3차원

```
권한 = 모듈(module_code) × 접근수준(access_level) × 데이터범위(data_scope)
        + 눈가림 해제 여부(unblinded)
```

| 차원 | 값 |
|---|---|
| 모듈 | `D1`~`D6`, `RECON`, `ISSUE`, `CONFIG`, `EXPORT`, `ADMIN` |
| 접근수준 | `NONE` < `READ` < `WRITE` |
| 데이터범위 | 전체 / 시험 / 국가 / 사이트 |
| 눈가림 | boolean |

### 2.2 판정 알고리즘

```
function check(user, trial, module, required_level, target=None):
    grants = user_role.where(user=user, trial=trial)
    if not grants:                          raise 404      # 존재 노출 방지
    level = max(g.role.permission[module].access_level for g in grants)
    if level == 'NONE':                     raise 403 module-forbidden
    if rank(level) < rank(required_level):  raise 403 write-forbidden
    if target and not in_scope(target, grants):
        raise 403 scope-forbidden
    return grants
```

복수 역할을 가진 경우 **가장 높은 권한이 적용**됩니다. 합집합 방식이며, 제한을 의도하면 역할을 분리해야 합니다.

### 2.3 데이터 범위 적용

모든 조회 쿼리는 서비스 계층에서 범위 필터를 자동 적용합니다.

```python
class ScopedQuerySet:
    def for_user(self, user, trial):
        scope = resolve_scope(user, trial)
        if scope.is_all:   return self
        q = Q()
        if scope.country_ids: q |= Q(country_id__in=scope.country_ids)
        if scope.site_ids:    q |= Q(site_id__in=scope.site_ids)
        return self.filter(q)
```

**모델 매니저가 아니라 서비스 계층에 두는 것**이 중요합니다. 매니저에 두면 배치·엔진이 우회해야 하는데, 그 우회 경로가 권한 누수의 통로가 됩니다. 엔진은 명시적으로 `unscoped()`를 호출합니다.

### 2.4 눈가림 마스킹

| 항목 | 사양 |
|---|---|
| 대상 필드 | `subject.arm`, `subject.strata`, 그리고 `CFG` 지정 필드 |
| 적용 지점 | **서비스 계층 1곳** |
| 표현 | 값은 `null`, `{field}_masked: true` 동반 |
| 적용 범위 | 화면, API, **export, 드릴다운, 비교 모드 전부** |
| 해제 | `permission.unblinded = true` |
| 비활성화 | `trial.blinded = false`면 마스킹 없음 |

```python
def apply_masking(obj, user, trial):
    if not trial.blinded:               return obj
    if has_unblind(user, trial):        return obj
    for f in MASKED_FIELDS:
        setattr(obj, f, None)
        setattr(obj, f + '_masked', True)
    return obj
```

**export 경로에서 마스킹이 빠지는 것이 전형적 사고**이므로 ([개념 08](../concept/08-platform-services.md) 2.4), export도 동일 함수를 지납니다. 이를 테스트로 강제합니다 ([08](08-test-plan.md) 5.2).

### 2.5 역할 템플릿

[개념 02](../concept/02-personas-and-use-cases.md) 3장의 매트릭스를 초기 데이터로 탑재합니다.

| 역할 | D1 | D2 | ISSUE | CONFIG | EXPORT | ADMIN | unblinded |
|---|---|---|---|---|---|---|---|
| CDM Lead | W | R | W | W | R | - | X |
| CRA | R | R | R | - | R | - | X |
| ClinOps Lead | R | W | R | R | R | - | X |
| PM | R | R | R | R | R | - | X |
| Manager | R | R | R | - | R | - | X |
| Unblinded Statistician | R | R | - | - | R | - | **O** |
| System Admin | - | - | - | - | - | W | X |

관리자에게 업무 데이터 권한이 없는 것이 통제의 기본입니다.

## 3. 감사 추적

### 3.1 기록 대상

| 대상 | 기록 |
|---|---|
| 데이터 변경 | CREATE / UPDATE / DELETE, 변경 필드만 |
| 인증 | LOGIN / LOGOUT / 로그인 실패 |
| 업로드·확정 | IMPORT, 상태 전이 |
| 엔진 실행 | ENGINE_RUN (실행 단위 1건) |
| Export | EXPORT (대상, 행 수, 필터) |
| 설정·가정 활성화 | UPDATE + 사유 |
| 권한 변경 | UPDATE (관리자 행위) |

### 3.2 행위자 구분

```python
@dataclass
class Actor:
    type: Literal['HUMAN','AI','ENGINE']
    user_id: int | None
    agent_id: int | None
    engine: str | None
    ai_run_id: int | None
    initiated_by: int | None
```

| `actor_type` | Phase 1 사용처 |
|---|---|
| `HUMAN` | 화면·API를 통한 모든 조작 |
| `ENGINE` | ExpectationEngine, ProgressEngine, RollupEngine, 일 배치 |
| `AI` | **Phase 1 미사용.** 스키마와 기록 경로만 확보 |

`AI`를 미리 두는 이유는 [개념 14](../concept/14-ai-extensibility.md) 7장의 판단입니다. 나중에 얹으면 과거 기록과 구분이 안 됩니다.

### 3.3 구현

```python
class AuditContext:
    """요청 단위 컨텍스트. 미들웨어가 설정."""
    actor: Actor
    source: str        # UI | IMPORT | API | ENGINE
    reason: str | None

@receiver(post_save)
def audit_on_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS: return
    ctx = AuditContext.current()
    if ctx is None:
        raise AuditContextMissing(sender)     # 조용히 누락되지 않게
    AuditLog.objects.create(...)
```

`AuditContextMissing`을 **예외로 던지는 것**이 중요합니다. 컨텍스트 없이 저장되면 행위자 없는 로그가 생기는데, 그것을 허용하면 감사 추적의 의미가 사라집니다. 배치도 명시적으로 컨텍스트를 설정해야 합니다.

### 3.4 append-only 강제

| 층 | 방법 |
|---|---|
| DB | `REVOKE UPDATE, DELETE ON audit_log FROM app_role` |
| ORM | `AuditLog.save()`가 기존 PK면 예외, `delete()`는 항상 예외 |
| 마이그레이션 | 감사 테이블 변경은 별도 승인 절차 |

### 3.5 사유 필수 작업

| 작업 | 사유 |
|---|---|
| `WAIVED` 처리 | 필수 |
| 확정된 데이터 정정 | 필수 |
| 설정·가정 활성화 | 필수 |
| Drop 폐기 | 필수 |
| 동일 파일 강제 재업로드 | 필수 |
| 일반 조회·export | 불필요 |

전 변경에 사유를 요구하지 않는 이유는 [개념 08](../concept/08-platform-services.md) 3.3의 판단입니다. 모두 요구하면 "수정"이라고만 적게 되어 의미가 없어집니다.

### 3.6 엔진 실행 기록

행 단위 로그가 폭증하지 않도록 **실행 단위로 1건**을 남기고 영향 범위를 요약합니다.

```json
{ "action": "ENGINE_RUN", "entity_type": "EngineRun", "entity_id": "1042",
  "actor_type": "ENGINE", "actor_engine": "ProgressEngine",
  "new_value": { "trigger": "UPLOAD", "drop_id": 88,
                 "items_updated": 12403, "statuses_changed": 2841,
                 "assumption_version": 3, "trial_config_version": 2 } }
```

다만 **`WAIVED` 전이는 예외**입니다. 분모에서 항목을 빼는 결정이므로 항목 단위로 기록합니다.

### 3.7 조회

| 화면 | 기능 |
|---|---|
| 엔티티별 이력 | 항목·피험자·설정 상세 화면의 "이력" 탭 |
| 전역 검색 | 관리자 화면. 시험·행위자 유형·엔티티·기간 필터 |
| Export | CSV. **export 자체도 감사 기록** |

## 4. 동시성

| 상황 | 처리 |
|---|---|
| 같은 레코드 동시 수정 | 낙관적 잠금 (`version` 컬럼). 충돌 시 409 |
| 같은 Feed 동시 업로드 | Drop은 각각 생성, `promote`는 Feed 단위 락으로 순차 |
| 엔진 실행 중 조회 | 이전 `READY` 스냅샷 조회. 진행 중 스냅샷은 비노출 |
| 엔진 중복 실행 | 시험 단위 advisory lock |

```sql
SELECT pg_try_advisory_lock(hashtext('engine:' || :trial_id));
```

## 5. Part 11 대비 현황

| 요건 | Phase 1 | 이후 |
|---|---|---|
| 생성·수정·삭제 기록 | **구현** | — |
| 시각 (서버 생성) | **구현** | — |
| 행위자 식별 (사람/AI/엔진) | **구현** | — |
| 변경 사유 | **선별 구현** | 범위 확대 검토 |
| append-only | **구현** | — |
| 감사 추적 조회 | **구현** | — |
| 전자 서명 | 미구현 | Part 11 Subpart C |
| CSV 문서 (URS/FS/DS/IQ/OQ/PQ) | 미작성 | validation 시 |
| 변경 통제 절차 | 미수립 | validation 시 |
| 정기 감사 추적 검토 절차 | 미수립 | validation 시 |

## 6. 미결 사항

| # | 사항 | 제안 |
|---|---|---|
| S-07-1 | 복수 역할의 권한 합집합 방식이 타당한가 | 타당. 제한은 역할 분리로 |
| S-07-2 | `unblinded` 권한 보유자 범위 | 최소화. 배정 시 관리자 2인 승인 검토 |
| S-07-3 | 감사 로그 파티셔닝 필요 여부 | 연 단위 RANGE 파티션, 규모 확인 후 |
| S-07-4 | 로그인 실패 기록 보존 기간 | 90일 |
