"""scripts/auto_fix_runner.py 단위 테스트.

본인 본질 (2026-05-07): harness Made But Never Used 차단.
AutoFix 진짜 호출 + escalation 본질 검증.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# scripts/ 디렉토리 import 경로 추가 (★ tests에서 직접 호출 가능)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def test_auto_fix_runner_module_exists() -> None:
    """모듈 import 가능 (★ Made But Never Used 차단)."""
    import auto_fix_runner  # noqa: F401


def test_auto_fix_runner_main_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AutoFix 성공 시 0."""
    from core.harness.auto_fix import AutoFixReport, FixResult

    fake_report = AutoFixReport(
        cycles_attempted=1,
        results=[FixResult(cycle=1, step="lint", success=True)],
        final_success=True,
    )

    import auto_fix_runner

    monkeypatch.setattr(sys, "argv", ["auto_fix_runner.py"])
    with patch.object(auto_fix_runner, "AutoFixer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.fix_all.return_value = fake_report
        mock_cls.return_value = mock_instance

        result = auto_fix_runner.main()
        assert result == 0


def test_auto_fix_runner_main_failure(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AutoFix 3 cycle 후도 실패 시 1 + escalation msg."""
    from core.harness.auto_fix import AutoFixReport, FixResult

    fake_report = AutoFixReport(
        cycles_attempted=3,
        results=[
            FixResult(cycle=1, step="lint", success=False, stderr="E1"),
            FixResult(cycle=2, step="lint", success=False, stderr="E2"),
            FixResult(cycle=3, step="lint", success=False, stderr="E3"),
        ],
        final_success=False,
        escalation_required=True,
        escalation_message="3 cycle 후도 실패",
    )

    import auto_fix_runner

    monkeypatch.setattr(sys, "argv", ["auto_fix_runner.py"])
    with patch.object(auto_fix_runner, "AutoFixer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.fix_all.return_value = fake_report
        mock_cls.return_value = mock_instance

        result = auto_fix_runner.main()
        assert result == 1
        captured = capsys.readouterr()
        # build_escalation_report가 stderr에 출력됨
        assert "FAILED" in captured.err or "fail" in captured.err.lower()


def test_auto_fix_runner_check_only_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--check-only smoke 통과 시 0."""
    import auto_fix_runner

    from core.harness.auto_fix import FixResult

    monkeypatch.setattr(sys, "argv", ["auto_fix_runner.py", "--check-only"])
    with patch.object(auto_fix_runner, "AutoFixer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.fix_lint.return_value = FixResult(
            cycle=1, step="lint", success=True
        )
        mock_cls.return_value = mock_instance

        result = auto_fix_runner.main()
        assert result == 0
        mock_instance.fix_lint.assert_called_once_with(cycle=1)
        # fix_all은 호출되면 X (★ check-only)
        mock_instance.fix_all.assert_not_called()


def test_auto_fix_runner_check_only_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--check-only smoke 실패 시 1."""
    import auto_fix_runner

    from core.harness.auto_fix import FixResult

    monkeypatch.setattr(sys, "argv", ["auto_fix_runner.py", "--check-only"])
    with patch.object(auto_fix_runner, "AutoFixer") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.fix_lint.return_value = FixResult(
            cycle=1, step="lint", success=False, stderr="ruff errors"
        )
        mock_cls.return_value = mock_instance

        result = auto_fix_runner.main()
        assert result == 1
