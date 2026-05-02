"""자율 Fix 사이클 — Tier 1.5 D2 (★ 인사이트 #20).

max 3 사이클: ruff --fix → pytest --lf → mypy
3회 모두 실패 시 escalation report 반환.
LLM 호출 0회 (Mechanical only).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FixResult:
    """단일 Fix 시도 결과."""

    cycle: int
    step: str
    success: bool
    stdout: str = ""
    stderr: str = ""


@dataclass
class AutoFixReport:
    """전체 Auto Fix 세션 결과."""

    cycles_attempted: int
    results: list[FixResult] = field(default_factory=list)
    final_success: bool = False
    escalation_required: bool = False
    escalation_message: str = ""


MAX_CYCLES = 3


def _run(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[bool, str, str]:
    """명령 실행 → (success, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return proc.returncode == 0, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Timeout after {timeout}s"
    except FileNotFoundError as e:
        return False, "", str(e)


class AutoFixer:
    """max 3사이클 자율 Fix.

    각 사이클: fix_lint → fix_tests → fix_build 순서.
    한 사이클이라도 성공하면 루프 종료.
    3회 모두 실패 시 escalation report.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self.project_root = project_root or Path.cwd()

    def fix_lint(self, cycle: int) -> FixResult:
        """ruff --fix 실행."""
        ok, out, err = _run(
            ["ruff", "check", "core/", "service/", "tools/", "tests/", "--fix", "--quiet"],
            cwd=self.project_root,
        )
        # ruff --fix: 수정 후 재검사
        ok2, out2, err2 = _run(
            ["ruff", "check", "core/", "service/", "tools/", "tests/", "--quiet"],
            cwd=self.project_root,
        )
        return FixResult(cycle=cycle, step="lint", success=ok2, stdout=out2, stderr=err2)

    def fix_tests(self, cycle: int) -> FixResult:
        """pytest --lf (last-failed) 실행."""
        ok, out, err = _run(
            ["pytest", "tests/unit/", "--lf", "-q", "--tb=short"],
            cwd=self.project_root,
            timeout=180,
        )
        return FixResult(cycle=cycle, step="tests", success=ok, stdout=out, stderr=err)

    def fix_build(self, cycle: int) -> FixResult:
        """mypy type check 실행."""
        ok, out, err = _run(
            ["mypy", "core/", "service/", "--strict", "--no-error-summary"],
            cwd=self.project_root,
        )
        return FixResult(cycle=cycle, step="build", success=ok, stdout=out, stderr=err)

    def fix_all(self) -> AutoFixReport:
        """최대 MAX_CYCLES 사이클 실행.

        모든 step(lint + tests + build)이 성공하면 final_success=True.
        """
        report = AutoFixReport(cycles_attempted=0)

        for cycle in range(1, MAX_CYCLES + 1):
            report.cycles_attempted = cycle

            lint_result = self.fix_lint(cycle)
            test_result = self.fix_tests(cycle)
            build_result = self.fix_build(cycle)

            report.results.extend([lint_result, test_result, build_result])

            if lint_result.success and test_result.success and build_result.success:
                report.final_success = True
                return report

        # 3회 모두 실패
        report.escalation_required = True
        report.escalation_message = build_escalation_report(report)
        return report


def build_escalation_report(report: AutoFixReport) -> str:
    """Auto Fix 3회 실패 → 에스컬레이션 메시지 생성."""
    lines = [
        f"AutoFix FAILED after {report.cycles_attempted} cycles.",
        "",
        "Step summary:",
    ]
    for r in report.results:
        status = "✅" if r.success else "❌"
        lines.append(f"  [{r.cycle}/{MAX_CYCLES}] {status} {r.step}")
        if not r.success and r.stderr:
            preview = r.stderr.strip().splitlines()
            for ln in preview[:3]:
                lines.append(f"      {ln}")

    lines += [
        "",
        "Manual intervention required:",
        "  1. ruff check . --fix && ruff check .",
        "  2. pytest tests/unit/ -x",
        "  3. mypy core/ service/ --strict",
    ]
    return "\n".join(lines)
