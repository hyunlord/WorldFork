"""Layer 1 Verify Agent CLI (★ verify.sh [5/5] 호출).

★ 진짜 LLM 호출 (codex 우선).
★ 자기 합리화 차단 시작.

사용:
  python scripts/verify_layer1_review.py

종료 코드:
  0: pass (score >= 18)
  1: fail
  2: flake (codex CLI timeout 전체 소진 — verify SKIP)

점수 출력:
  STDOUT 마지막 줄: SCORE=<n>  또는 SCORE=FLAKE (exit 2)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm.cli_client import CLIClient
from core.llm.client import LLMError
from core.verify.layer1_review import Layer1ReviewAgent, Layer1ReviewResult

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CODEX_TIMEOUT_SECONDS = 600.0  # 180s → 600s
CODEX_MAX_RETRIES = 1          # timeout 발생 시 1회 retry


def _debate_enabled() -> bool:
    """config/harness.yaml debate_mode.enabled 읽기 (default True)."""
    import yaml

    cfg = Path(__file__).resolve().parents[1] / "config" / "harness.yaml"
    try:
        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        dm = data.get("debate_mode", {})
        return bool(dm.get("enabled", True)) if isinstance(dm, dict) else True
    except (OSError, yaml.YAMLError):
        return True


def _is_timeout_error(result: Layer1ReviewResult) -> bool:
    """LLM call failed: CLI timeout 에러 여부 판정."""
    return bool(result.error and "CLI timeout" in result.error)


def run_review_with_retry(
    agent: Layer1ReviewAgent,
    ref_old: str = "HEAD~1",
    ref_new: str = "HEAD",
    max_attempts: int = CODEX_MAX_RETRIES + 1,
) -> tuple[Layer1ReviewResult | None, bool]:
    """agent.review() 호출 + timeout 시 retry.

    Returns:
        (result, is_flake) — is_flake=True 시 result=None.
    """
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            print(
                f"  [retry {attempt}/{max_attempts}] "
                f"codex CLI 재시도 (timeout {CODEX_TIMEOUT_SECONDS}s)..."
            )
        r = agent.review(ref_old=ref_old, ref_new=ref_new)
        if _is_timeout_error(r):
            print(f"  ⚠️  timeout (attempt {attempt}/{max_attempts})")
            continue
        return r, False
    return None, True


def main() -> None:
    print("[Layer 1 Verify Agent] codex로 git diff 리뷰 시작...")

    try:
        reviewer = CLIClient(model_key="codex", timeout_seconds=CODEX_TIMEOUT_SECONDS)
    except (LLMError, Exception) as e:
        print(f"  ❌ Reviewer init failed: {e}")
        print("SCORE=0")
        sys.exit(1)

    use_debate = _debate_enabled()
    try:
        agent = Layer1ReviewAgent(reviewer=reviewer, use_debate=use_debate)
    except ValueError as e:
        print(f"  ❌ Cross-Model violation: {e}")
        print("SCORE=0")
        sys.exit(1)

    mode = "debate(codex→27B→9B)" if use_debate else "single review"
    print(f"  Reviewer: {reviewer.model_name} (★ Cross-Model OK) — {mode}")

    result, is_flake = run_review_with_retry(agent)
    if is_flake:
        print("  ⚠️  codex CLI flake detected — Verify SKIP")
        print("SCORE=FLAKE")
        sys.exit(2)

    assert result is not None

    print()
    print(f"  Score: {result.score}/25")
    print(f"  Verdict: {result.verdict}")
    print(f"  Reviewer: {result.reviewer_model}")
    if result.error:
        print(f"  Error: {result.error}")

    if result.anti_pattern_matches:
        print(f"  Anti-patterns: {len(result.anti_pattern_matches)}")
        for m in result.anti_pattern_matches[:3]:
            print(f"    - [{m.anti_pattern.severity}] {m.anti_pattern.id}: line {m.line}")

    if result.issues:
        print(f"  Issues: {len(result.issues)}")
        for i in result.issues[:5]:
            print(f"    - [{i.severity}] {i.file}:{i.line} — {i.description[:80]}")

    if result.summary:
        print(f"  Summary: {result.summary[:200]}")

    print()
    print(f"SCORE={result.score}")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
