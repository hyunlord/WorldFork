"""Eval Smoke Runner CLI (★ verify.sh [4/5] 호출).

사용:
  python scripts/smoke_runner.py

종료 코드:
  0: pass (pass_rate >= 95%)
  1: fail

출력:
  마지막 줄: SMOKE_PASS_RATE=<0-100>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.eval.smoke import PASS_RATE_THRESHOLD, run_smoke
from core.llm.local_client import get_qwen35_9b_q3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    print("[Eval Smoke] Qwen3.5-9B Q3 (8083) smoke 시작...")

    try:
        llm = get_qwen35_9b_q3()
    except Exception as e:
        print(f"  ❌ LLM init failed: {e}")
        print("SMOKE_PASS_RATE=0")
        sys.exit(1)

    result = run_smoke(llm)

    pct = int(result.pass_rate * 100)
    print(f"  Total: {result.total}")
    print(f"  Passed: {result.passed}")
    print(f"  Pass rate: {pct}%  (threshold: {int(PASS_RATE_THRESHOLD*100)}%)")

    failed = [a for a in result.attempts if not a.mechanical_passed]
    if failed:
        print(f"  Failed ({len(failed)}):")
        for a in failed[:5]:
            issues_str = ", ".join(a.issues[:3]) if a.issues else "unknown"
            print(f"    - {a.item_id} [{a.category}]: {issues_str}")

    print()
    print(f"SMOKE_PASS_RATE={pct}")

    sys.exit(0 if result.succeeded else 1)


if __name__ == "__main__":
    main()
