# Tier 1.5 D2 — Git Hook + 12 이벤트 + AutoFix (★ 인사이트 #20)

날짜: 2026-05-02
타입: ★ 자율 검증 강화

## 0. 한 줄 요약

매 commit 자동 Lite 게이트 (pre-commit) + 매 push 자동 Heavy 게이트 (pre-push 95+) + 12 Hook 이벤트 시스템 + AutoFix max 3 사이클.

---

## 1. Phase 1 — Git Hooks

### pre-commit (Lite ~30s)
- Ruff lint → fail 시 commit 차단
- Mypy type check → warning-only (비차단)
- pytest --lf (last-failed only) → fail 시 commit 차단

### pre-push (Heavy ~60s)
- verify.sh quick 전체 실행
- 95+ 미달 시 push 차단
- `SKIP_VERIFY=1` 환경변수로 긴급 우회 (audit log 기록)

### scripts/install_hooks.sh
- `scripts/hooks/` 백업본 → `.git/hooks/` 설치
- `--check` 모드로 설치 상태 확인

---

## 2. Phase 2 — 12 Hook 이벤트 시스템

### HookEvent (12개)
```
TASK_START → PRE_PLAN → POST_PLAN → PLAN_REVIEW →
PRE_CODE → POST_CODE → PRE_VERIFY → POST_VERIFY →
ON_RETRY → ON_REPLAN → TASK_COMPLETE → TASK_FAIL
```

### Priority Merge
- built-in (priority=10) < global ~/.autodev/ (50) < project .autodev/ (90)
- 같은 priority → 등록 순서

### Built-in Hooks (3종)
| Hook | 이벤트 | 역할 |
|---|---|---|
| builtin_post_code_blocking | POST_CODE | Critical anti-pattern → abort |
| builtin_external_pkg_check | POST_CODE | 미승인 외부 패키지 → abort |
| builtin_verify_threshold | POST_VERIFY | score < 95 → abort |

### .autodev/hooks.json v0.2.0
- 12 이벤트 키 명시 (빈 배열 = project override 없음)

---

## 3. Phase 3 — AutoFix max 3 사이클

### 사이클 구조
```
cycle 1~3:
  fix_lint  → ruff --fix + 재검사
  fix_tests → pytest --lf
  fix_build → mypy --strict
  → 전부 성공 시 종료
→ 3회 실패 시 escalation_report
```

### 특징
- LLM 호출 0회 (Mechanical only)
- `MAX_CYCLES = 3` 상수
- `build_escalation_report()` → 수동 개입 안내

---

## 4. 자기 검증

```
pytest tests/unit/       : 635 passed
ruff check core/...      : All checks passed
mypy core/ service/ --strict : 58 source files, 0 errors
verify.sh quick          : 100/100 A grade
```

### 신규 테스트 (+28)
- `test_hooks.py`: 12 이벤트, 3 built-in, HookManager register/trigger/abort/priority
- `test_auto_fix.py`: FixResult, AutoFixReport, 3 cycle scenarios, escalation report

---

## 5. ★ 다음 D3

- `core/harness/context.py` — TaskContext 전역 상태
- `core/harness/session.py` — 세션 관리 + 재개
- verify.sh에 Hook 시스템 통합
- ★ pre-commit hook이 첫 번째 실제 방어선
