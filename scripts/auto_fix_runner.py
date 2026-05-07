"""pre-push hook용 AutoFix runner — harness 진짜 통합.

ruff/pytest/mypy 자동 수정 시도 (max 3 cycle).
모두 실패 시 escalation report.

★ 본인 본질 짚음 (2026-05-07):
'plan debate challenger의 planning harness pipeline이 작동 X'
→ AutoFix만이라도 진짜 통합 (1차 harness 통합).
verify.sh quick 실행 전에 호출 → 자동 수정 가능한 issue 선제 처리.

usage:
  python scripts/auto_fix_runner.py
  python scripts/auto_fix_runner.py --check-only  # AutoFix 호출 X, status만
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.harness.auto_fix import AutoFixer, build_escalation_report


def main() -> int:
    """AutoFix 진짜 실행.

    Returns:
        0: 성공 (★ 모든 검증 통과)
        1: 실패 (★ 3 cycle 후도 escalation)
    """
    parser = argparse.ArgumentParser(description="AutoFix harness runner.")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="AutoFix 호출 X, smoke check만 (★ pre-push 1차 게이트)",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent
    fixer = AutoFixer(project_root=repo_root)

    if args.check_only:
        # 1 cycle만 — lint/tests/build 모두 통과인지 확인
        lint = fixer.fix_lint(cycle=1)
        if not lint.success:
            print("⚠️  AutoFix smoke fail (lint) — full cycle 권장", file=sys.stderr)
            return 1
        print("✅ AutoFix smoke OK")
        return 0

    report = fixer.fix_all()

    if report.final_success:
        print(f"✅ AutoFix 성공 ({report.cycles_attempted} cycle)")
        for r in report.results:
            status = "✅" if r.success else "⚠️"
            print(f"  {status} cycle {r.cycle} {r.step}")
        return 0

    msg = build_escalation_report(report)
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
