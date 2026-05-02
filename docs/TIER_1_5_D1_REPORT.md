# Tier 1.5 D1 — Layer 1 인프라 + Verify Agent (★ 자기 합리화 차단 시작)

날짜: 2026-05-02
타입: ★ Tier 1.5 첫 사이클

## 0. 한 줄 요약

.autodev/ 인프라 + Verify Agent 진짜 LLM 호출 시작.
★ Cross-LLM 자기 합리화 차단 작동. 가짜 100/100 → 진짜 동작.

---

## 1. Phase 1 — .autodev/ 인프라 + prompt_loader

### 산출물
- `.autodev/agents/code_reviewer.md` (★ 5-section LAYER1_REVIEW_PROMPT)
  * 자료 LAYER1 3.2 + 본인 자료 (AutoDev 정보 격리) 정합
  * Cross-Model violations, Hardcoded scores, Info leaks, YAGNI 항목
- `.autodev/agents/coder.md` (D2+ 본격)
- `.autodev/agents/planner.md` (D2+ 본격)
- `.autodev/hooks.json` (D2 본격)
- `core/harness/prompt_loader.py`
  * 3-tier 우선순위: project > user > default
  * YAML frontmatter 파싱
  * `{{var}}` 템플릿 치환
- `tests/unit/test_prompt_loader.py` — 11 tests (ruff + mypy OK)

---

## 2. Phase 2 — AntiPatternChecker

### 산출물
- `core/verify/anti_pattern_check.py`
- 6 패턴 (LLM 호출 0회):

| ID | Severity | 설명 |
|---|---|---|
| hardcoded_score | critical | `.score = 95` 등 하드코딩 점수 |
| info_leak_in_retry | critical | retry 피드백에 score/verdict 포함 |
| same_model_generate_verify | critical | 같은 모델로 생성+검증 |
| made_but_never_used | major | 선언하고 실제 사용 X |
| mock_only_test | major | Mock 전용 테스트 |
| external_pkg_added | critical | 버전 지정자 포함 신규 외부 패키지 |

- `tests/unit/test_anti_pattern.py` — 16 tests (ruff + mypy OK)

### 버그 수정
- `external_pkg_added` 패턴 초기 버전 → `.md` 파일 JSON 예시 오탐
- 버전 지정자 `>=|<=|==|~=|!=|>|<|[` 필수 조건 추가로 해결

---

## 3. Phase 3 — Layer1 Review Agent

### 산출물
- `core/verify/layer1_review.py`
  * ★ Cross-Model 강제: `forbidden_reviewers=("claude_code", "claude")` → 즉시 reject
  * AntiPattern 사전 cheap check + LLM 리뷰 페널티 통합
  * ★ 정보 격리: git diff만 전달, 점수/verdict X
  * JSON 파싱: `STANDARD_FILTER_PIPELINE`
  * cutoff: score >= 18 (72%)
- `tests/unit/test_layer1_review.py` — 12 tests (ruff + mypy OK)

### 주요 검증
```python
# ★ Claude로 자기 합리화 시도 → 즉시 reject
with pytest.raises(ValueError, match="forbidden"):
    Layer1ReviewAgent(reviewer=MockClaudeLLM())
```

---

## 4. Phase 4 — scripts/verify.sh 진짜 + 자기 검증

### 산출물
- `scripts/verify_layer1_review.py` — Verify Agent CLI
- `scripts/verify.sh` 업데이트:
  * [5/5] `import` 검증 (가짜) → codex LLM 호출 (진짜)
  * `SCORE_LINE` 추출 → `VERIFY_SCORE` 반영

### 개선 사항
- 코드 파일만 diff (`*.py`, `*.sh`, `*.yaml`, `*.yml`, `*.json`, `*.toml`)
  * docs-only 커밋: "No code changes" → 25/25 pass (★ 정상)
  * 코드 변경 커밋: codex 진짜 리뷰 → 진짜 점수
- timeout 180초 (기존 120초 → timeout 이슈 해결)

### ★ 자기 검증 결과 (정직)

```
1차 시도 (오탐 전):
  [5/5] Verify Agent: 0/25 (AntiPattern 9개 오탐)
  TOTAL: 75/100 ← ★ 진짜 점수 (이전 가짜 100/100 vs 진짜 75/100)

수정 후:
  external_pkg_added 패턴 좁힘 (버전 지정자 필수)

3차 시도 (docs-only 커밋에서):
  [5/5] Verify Agent: 25/25 (No code changes → pass)
  TOTAL: 100/100 ← docs-only 커밋은 올바르게 pass

★ 다음 commit (D1 코드)에서:
  codex가 D1 Python 코드 실제 리뷰
  ★ 자기 합리화 차단 본격 시작
```

---

## 5. ★ 본인 #18 정신 시작

```
★ Cross-LLM 자기 합리화 차단 구조:
  작성: Claude Code (Sonnet 4.6)
  검증: codex gpt-5.4 (★ 다른 family)
  
  → "내가 짠 코드 + 다른 LLM이 검증"
  → "forbidden" 강제 (같은 family = ValueError)
  → 정보 격리 (점수/verdict 안 줌)

★ 매 단계 독립 agent (본인 자료보다 깊음):
  D1: 인프라 구축
  D2~: 매 commit에서 codex 독립 리뷰
```

---

## 6. 검증 최종

```
pytest tests/unit/ : 582 passed
ruff check core/ service/ tools/ tests/ : All checks passed
mypy core/ service/ --strict : 55 source files, 0 errors
```

---

## 7. ★ 다음 D2

- Pre-commit Hook (`.git/hooks/pre-commit`)
- 12 Hook 이벤트 시스템 (`core/harness/hooks.py`)
- 자율 Fix max 3 사이클 (`core/harness/auto_fix.py`)
- ★ D2부터 매 commit 자동 검증 (Hook 작동)
