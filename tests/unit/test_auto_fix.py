"""Tier 1.5 D2: AutoFixer 테스트."""

from pathlib import Path
from unittest.mock import patch

from core.harness.auto_fix import (
    MAX_CYCLES,
    AutoFixer,
    AutoFixReport,
    FixResult,
    build_escalation_report,
)


class TestFixResult:
    def test_success_fields(self) -> None:
        r = FixResult(cycle=1, step="lint", success=True, stdout="OK")
        assert r.success
        assert r.cycle == 1

    def test_failure_fields(self) -> None:
        r = FixResult(cycle=2, step="tests", success=False, stderr="FAIL")
        assert not r.success
        assert r.stderr == "FAIL"


class TestAutoFixReport:
    def test_defaults(self) -> None:
        report = AutoFixReport(cycles_attempted=0)
        assert not report.final_success
        assert not report.escalation_required
        assert report.results == []


class TestAutoFixer:
    def _make_fixer(self) -> AutoFixer:
        return AutoFixer(project_root=Path("."))

    def test_fix_all_succeeds_first_cycle(self) -> None:
        fixer = self._make_fixer()
        with patch.object(fixer, "fix_lint", return_value=FixResult(1, "lint", True)):
            with patch.object(fixer, "fix_tests", return_value=FixResult(1, "tests", True)):
                with patch.object(fixer, "fix_build", return_value=FixResult(1, "build", True)):
                    report = fixer.fix_all()
        assert report.final_success
        assert report.cycles_attempted == 1
        assert not report.escalation_required

    def test_fix_all_fails_all_cycles(self) -> None:
        fixer = self._make_fixer()
        lint_fails = [FixResult(i, "lint", False, stderr="err") for i in range(1, 4)]
        test_fails = [FixResult(i, "tests", False) for i in range(1, 4)]
        build_fails = [FixResult(i, "build", False) for i in range(1, 4)]
        with patch.object(fixer, "fix_lint", side_effect=lint_fails):
            with patch.object(
                fixer, "fix_tests", side_effect=test_fails
            ):
                with patch.object(
                    fixer, "fix_build", side_effect=build_fails
                ):
                    report = fixer.fix_all()
        assert not report.final_success
        assert report.escalation_required
        assert report.cycles_attempted == MAX_CYCLES

    def test_fix_all_succeeds_third_cycle(self) -> None:
        fixer = self._make_fixer()
        ok_lint = FixResult(3, "lint", True)
        ok_tests = FixResult(3, "tests", True)
        ok_build = FixResult(3, "build", True)

        lint_results = [FixResult(i, "lint", False) for i in range(1, 3)] + [ok_lint]
        test_results = [FixResult(i, "tests", False) for i in range(1, 3)] + [ok_tests]
        build_results = [FixResult(i, "build", False) for i in range(1, 3)] + [ok_build]

        with patch.object(fixer, "fix_lint", side_effect=lint_results):
            with patch.object(fixer, "fix_tests", side_effect=test_results):
                with patch.object(fixer, "fix_build", side_effect=build_results):
                    report = fixer.fix_all()
        assert report.final_success
        assert report.cycles_attempted == 3

    def test_max_cycles_constant(self) -> None:
        assert MAX_CYCLES == 3


class TestBuildEscalationReport:
    def test_report_contains_failure_summary(self) -> None:
        report = AutoFixReport(
            cycles_attempted=3,
            results=[
                FixResult(1, "lint", False, stderr="ruff: E501"),
                FixResult(1, "tests", False, stderr="pytest: FAILED"),
                FixResult(1, "build", False, stderr="mypy: error"),
            ],
            escalation_required=True,
        )
        msg = build_escalation_report(report)
        assert "FAILED" in msg
        assert "3" in msg
        assert "Manual intervention" in msg

    def test_report_contains_instructions(self) -> None:
        report = AutoFixReport(cycles_attempted=3, escalation_required=True)
        msg = build_escalation_report(report)
        assert "ruff" in msg
        assert "pytest" in msg
        assert "mypy" in msg
