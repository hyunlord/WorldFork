"""Tier 1.5 D3 작업 5: Coding Loop 테스트."""

from pathlib import Path
from unittest.mock import MagicMock

from core.harness.coding_loop import CodingLoop
from core.harness.hooks import HookManager
from core.harness.task_context import TaskContext


def _make_hooks(tmp_path: Path) -> HookManager:
    return HookManager(
        project_dir=tmp_path / "proj",
        user_dir=tmp_path / "home",
    )


class TestCodingLoopMaxRetries:
    def test_max_retries_constant(self) -> None:
        assert CodingLoop.MAX_RETRIES == 3


class TestCodingLoopFirstSuccess:
    def test_pass_first_try(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(return_value={
            "score": 96, "verdict": "pass", "issues": [],
        })

        loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
        task = TaskContext()
        result = loop.run(task)

        assert result.succeeded
        assert result.attempts == 1
        assert result.final_score == 96
        assert task.coding_attempts_count == 1

    def test_coder_called_once_on_first_pass(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(return_value={
            "score": 97, "verdict": "pass", "issues": [],
        })
        loop = CodingLoop(hooks, code_fn, verify_fn)
        loop.run(TaskContext())
        assert code_fn.call_count == 1


class TestCodingLoopRetry:
    def test_retry_on_low_score(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        # 81 < 95 → retry; 96 >= 95 → pass
        verify_fn = MagicMock(side_effect=[
            {"score": 81, "verdict": "warn", "issues": ["fix this"]},
            {"score": 96, "verdict": "pass", "issues": []},
        ])

        loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
        task = TaskContext()
        result = loop.run(task)

        assert result.succeeded
        assert result.attempts == 2
        assert code_fn.call_count == 2

    def test_all_3_fail_replan(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(return_value={
            "score": 60, "verdict": "fail", "issues": ["bad"],
        })

        loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
        task = TaskContext()
        result = loop.run(task)

        assert not result.succeeded
        assert result.attempts == 3
        assert result.needs_replan
        assert not result.abort_reason


class TestCodingLoopBuildGate:
    def test_build_fail_retries_without_verify(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(side_effect=[
            {"code": "x", "build_passed": False},
            {"code": "y", "build_passed": True},
        ])
        verify_fn = MagicMock(return_value={
            "score": 96, "verdict": "pass", "issues": [],
        })

        loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
        result = loop.run(TaskContext())

        # build fail → continue → second attempt passes
        assert result.succeeded
        # Verifier called only once (build fail skips verify)
        assert verify_fn.call_count == 1


class TestInformationIsolation:
    def test_retry_feedback_no_score(self, tmp_path: Path) -> None:
        """★ 본인 자료 정신: retry feedback에 점수 / verdict 없음."""
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(side_effect=[
            {"score": 81, "verdict": "warn", "issues": [
                {"description": "needs refactor", "severity": "minor"},
            ]},
            {"score": 96, "verdict": "pass", "issues": []},
        ])

        loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
        loop.run(TaskContext())

        assert code_fn.call_count == 2
        second_feedback = code_fn.call_args_list[1][0][0]
        for item in second_feedback:
            assert "81" not in str(item)
            assert "score" not in str(item).lower()
            assert "verdict" not in str(item).lower()
            assert "warn" not in str(item).lower()

    def test_retry_feedback_contains_issues(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(side_effect=[
            {"score": 72, "verdict": "fail", "issues": ["use real eval"]},
            {"score": 96, "verdict": "pass", "issues": []},
        ])

        loop = CodingLoop(hooks, code_fn, verify_fn)
        loop.run(TaskContext())

        second_feedback = code_fn.call_args_list[1][0][0]
        assert len(second_feedback) >= 1
        assert "use real eval" in second_feedback


class TestCodingLoopTaskStatus:
    def test_task_status_transitions(self, tmp_path: Path) -> None:
        hooks = _make_hooks(tmp_path)
        code_fn = MagicMock(return_value={"code": "x", "build_passed": True})
        verify_fn = MagicMock(return_value={
            "score": 96, "verdict": "pass", "issues": [],
        })
        loop = CodingLoop(hooks, code_fn, verify_fn)
        task = TaskContext()
        loop.run(task)
        assert task.verify_attempts_count == 1
