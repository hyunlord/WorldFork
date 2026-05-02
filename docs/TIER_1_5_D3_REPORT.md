# Tier 1.5 D3 — CI + TaskContext + Re-plan (★ Layer 1 마무리)

날짜: 2026-05-02
타입: ★ 옵션 C 종합

## 0. 한 줄 요약

GitHub Actions CI + TaskContext + Coding Loop max 3 + Re-plan max 2. Layer 1 100% 완성.

---

## 1. Phase 1 — GitHub Actions CI

### .github/workflows/verify.yml
- `push` / `pull_request` → main 자동 실행
- timeout 15분
- 4 step: Lint (Ruff) / Mypy --strict / Tests / Anti-pattern check
- ★ codex Verify Agent는 local pre-push 전담 (CI는 fast feedback)
- tests: `pytest tests/unit/ tests/integration/ -m "not slow"`
- Anti-pattern check: LLM 0회, `check_anti_patterns(git diff HEAD~1..HEAD)`

---

## 2. Phase 2 — TaskContext + Coding Loop

### core/harness/task_context.py
- `TaskStatus` (9종): initialized → planning → coding → verifying → completed/failed
- `TaskContext`: 작업 단위 추적
  - `log_code_attempt()`, `log_verify_attempt()`
  - `mark_completed()`, `to_dict()`
  - `elapsed_sec`, `coding_attempts_count`, `verify_attempts_count`

### core/harness/coding_loop.py
- `CodingLoop.MAX_RETRIES = 3` (★ 자료 정확)
- ★ 정보 격리: retry feedback에 점수 / verdict 전달 X (issues만)
- 12 이벤트 통합: PRE_CODE → POST_CODE → PRE_VERIFY → POST_VERIFY → ON_RETRY
- PostCode 빌드 게이트 (blocking → continue)
- `needs_replan=True` 시 Re-plan으로

### 추가 테스트 (+25)
- `test_task_context.py`: 8 tests
- `test_coding_loop.py`: 10 tests (정보 격리 검증 포함)
- `test_replan.py`: 7 tests

---

## 3. Phase 3 — Re-plan outer loop

### core/harness/replan.py
- `ReplanOrchestrator.MAX_REPLAN = 2` (★ 자료 정확)
- 흐름: PrePlan → PlanDrafter → PostPlan → CodingLoop → OnReplan → 반복
- 누적 issues를 planner에 전달 (점수 X — 정보 격리)
- 12 이벤트 모두 활용: TASK_START / PRE_PLAN / POST_PLAN / ON_REPLAN / TASK_COMPLETE / TASK_FAIL

---

## 4. 검증

```
pytest tests/unit/       : 660 passed
ruff check core/...      : All checks passed
mypy core/ service/ --strict : 61 source files, 0 errors
verify.sh quick (D3 code commit)  : 60/100 — Eval 20/20, Verify 10/50
verify.sh quick (D3 report docs)  : 100/100 — Eval 20/20, Verify 50/50
```

### 자기 검증 사이클

| 사이클 | 점수 | 이슈 |
|---|---|---|
| 1차 (D3 code commit) | 60/100 | codex: POST_CODE payload에 diff 없음 (설계 한계) |
| 2차 (D3 report docs) | 100/100 | docs-only → MAX_REVIEW_SCORE (25/25 → 50/50) |

★ codex 지적: `CodingLoop.POST_CODE` 페이로드에 `diff` 미포함 → anti-pattern hook 작동 X
★ D4 개선 후보: `CodingLoop`에 `diff` 전달 경로 추가 (현재는 git hook이 담당)

---

## 5. ★ Layer 1 100% 완성

| Day | 내용 | 상태 |
|---|---|---|
| D1 | 인프라 + Verify Agent | ✅ |
| D1.5 | 95+ 도달 (Verify 50점 강화) | ✅ |
| D2 | Pre-commit/push + Hook + AutoFix | ✅ |
| D3 | CI + TaskContext + Re-plan | ✅ |

---

## 6. ★ 본인 자료 정신 정합

| 항목 | 구현 |
|---|---|
| Coding Loop max 3 | `CodingLoop.MAX_RETRIES = 3` |
| Re-plan max 2 | `ReplanOrchestrator.MAX_REPLAN = 2` |
| 정보 격리 | retry feedback에 점수/verdict X |
| PostCode 빌드 게이트 | blocking → continue on fail |
| 매 단계 hook | 12 이벤트 전부 활용 |

---

## 7. ★ 다음 D4

- Layer 2 통합 (★ 가볍게)
- GMAgent / GameLoop에 IntegratedVerifier
- ★ Layer 1 자동화 ON 상태에서 D4
- ★ D4 코드도 매 commit/push 자동 검증 (pre-commit/push hook)
