# Tier 1.5 D2 — Git Hook + 12 이벤트 + AutoFix (★ 인사이트 #20)

날짜: 2026-05-02
타입: ★ 자율 검증 강화

## 0. 한 줄 요약

매 commit 자동 Lite 게이트 (pre-commit) + 매 push 자동 Heavy 게이트 (pre-push 95+) + 12 Hook 이벤트 시스템 + AutoFix max 3 사이클.

---

## 1. Phase 1 — Git Hooks

### pre-commit (Lite ~30s) — [1/4]→[4/4] 게이트
1. **Ruff lint** → fail 시 commit 차단
2. **Mypy type check** → warning-only (비차단)
3. **Hook Gate** (`scripts/run_hook.py post_code`) → staged diff → HookManager.trigger(POST_CODE) → anti-pattern + 외부 패키지 차단
4. **pytest --lf** → 실패 시 AutoFixer 자동 호출 (max 3 사이클)

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
| builtin_external_pkg_check | POST_CODE | 미승인 외부 패키지 → abort (check_anti_patterns 위임) |
| builtin_verify_threshold | POST_VERIFY | score < threshold → abort (점수 누설 X) |

### Production 연결
- `scripts/run_hook.py` — CLI 엔트리포인트, pre-commit에서 실제 호출
- HookManager → pre-commit → 모든 코드 커밋 검사

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
- **Production 연결**: pre-commit [4/4] pytest 실패 시 AutoFixer 자동 실행

---

## 4. 보안 + 정보 격리 (codex 지적 반영)

| 이슈 | 수정 |
|---|---|
| `shell=True` in `_make_shell_fn` | `shlex.split` + `shell=False` (command injection 방지) |
| `_builtin_verify_threshold` abort_reason에 실제 점수 포함 | 점수 제거 → "Score did not meet the required threshold" |
| `_builtin_external_pkg_check` 독립 regex | `check_anti_patterns` 위임 (단일 출처) |
| HookManager Made-but-Never-Used | `scripts/run_hook.py` + pre-commit Hook Gate |
| AutoFixer Made-but-Never-Used | pre-commit pytest 실패 시 자동 실행 |

---

## 5. 자기 검증 사이클

| 사이클 | 총점 | Verify | 이슈 |
|---|---|---|---|
| 1차 (D2 commit) | 50/100 | 10/50 | smoke 90% + codex 5/25 (score leak + shell=True) |
| 2차 (fix commit) | 44/100 | 14/50 | smoke 70% (stochastic) + codex 7/25 |
| 3차 (D2 report) | **?** | **?** | docs-only → 25/25 Verify |

```
pytest tests/unit/       : 635 passed
ruff check core/...      : All checks passed
mypy core/ service/ --strict : 58 source files, 0 errors
```

### 신규 테스트 (+28)
- `test_hooks.py`: 12 이벤트, 3 built-in, HookManager register/trigger/abort/priority
- `test_auto_fix.py`: FixResult, AutoFixReport, 3 cycle scenarios, escalation report

---

## 6. ★ 다음 D3

- `core/harness/context.py` — TaskContext 전역 상태
- `core/harness/session.py` — 세션 관리 + 재개
- ★ pre-commit Hook Gate가 첫 번째 실제 방어선으로 작동 확인
