"""Layer 1 Verify Agent CLI (★ verify.sh [5/5] 호출).

★ 진짜 LLM 호출 (codex 우선).
★ 자기 합리화 차단 시작.

사용:
  python scripts/verify_layer1_review.py

종료 코드:
  0: pass (score >= 18)
  1: fail

점수 출력:
  STDOUT 마지막 줄: SCORE=<n>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm.cli_client import CLIClient
from core.llm.client import LLMError
from core.verify.layer1_review import Layer1ReviewAgent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    print("[Layer 1 Verify Agent] codex로 git diff 리뷰 시작...")

    try:
        reviewer = CLIClient(model_key="codex", timeout_seconds=180.0)
    except (LLMError, Exception) as e:
        print(f"  ❌ Reviewer init failed: {e}")
        print("SCORE=0")
        sys.exit(1)

    try:
        agent = Layer1ReviewAgent(reviewer=reviewer)
    except ValueError as e:
        print(f"  ❌ Cross-Model violation: {e}")
        print("SCORE=0")
        sys.exit(1)

    print(f"  Reviewer: {reviewer.model_name} (★ Cross-Model OK)")

    result = agent.review(ref_old="HEAD~1", ref_new="HEAD")

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
