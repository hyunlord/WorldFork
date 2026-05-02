"""Tier 1.5 D3 작업 8: Re-plan outer loop 테스트."""

from pathlib import Path
from unittest.mock import MagicMock

from core.harness.coding_loop import CodingLoop
from core.harness.hooks import HookManager
from core.harness.replan import ReplanOrchestrator
from core.harness.task_context import TaskStatus


def _make_hooks(tmp_path: Path) -> HookManager:
    return HookManager(
        project_dir=tmp_path / "proj",
        user_dir=tmp_path / "home",
    )


def _build_orch(
    tmp_path: Path,
    success_after_replans: int | None = 0,
) -> tuple[ReplanOrchestrator, MagicMock, MagicMock, MagicMock]:
    """Helper: builds orchestrator with controlled success timing.

    success_after_replans=None → always fails.
    success_after_replans=N   → fails N complete replan cycles, then succeeds.
    """
    hooks = _make_hooks(tmp_path)
    planner: MagicMock = MagicMock(return_value={"steps": ["x"]})
    code_fn: MagicMock = MagicMock(return_value={"code": "x", "build_passed": True})

    if success_after_replans is None:
        verify_fn: MagicMock = MagicMock(return_value={
            "score": 60, "verdict": "fail", "issues": ["bad"],
        })
    else:
        responses = []
        # Each replan cycle = MAX_RETRIES verifier calls (all fail)
        for _ in range(success_after_replans):
            for _ in range(CodingLoop.MAX_RETRIES):
                responses.append({"score": 60, "verdict": "fail", "issues": ["bad"]})
        responses.append({"score": 96, "verdict": "pass", "issues": []})
        verify_fn = MagicMock(side_effect=responses)

    loop = CodingLoop(hooks, code_fn, verify_fn, cutoff_score=95)
    orch = ReplanOrchestrator(hooks, planner, loop)
    return orch, planner, code_fn, verify_fn


class TestReplanConstants:
    def test_max_replan_value(self) -> None:
        assert ReplanOrchestrator.MAX_REPLAN == 2


class TestReplanFirstTryPass:
    def test_no_replan_needed(self, tmp_path: Path) -> None:
        orch, planner, _, _ = _build_orch(tmp_path, success_after_replans=0)
        task, result = orch.run("test task")

        assert result.final_succeeded
        assert result.replan_count == 0
        assert task.success
        assert planner.call_count == 1

    def test_task_completed_status(self, tmp_path: Path) -> None:
        orch, _, _, _ = _build_orch(tmp_path, success_after_replans=0)
        task, result = orch.run("test")
        assert task.status == TaskStatus.COMPLETED


class TestReplanWithRetries:
    def test_replan_once_then_pass(self, tmp_path: Path) -> None:
        orch, planner, _, _ = _build_orch(tmp_path, success_after_replans=1)
        task, result = orch.run("test")

        assert result.final_succeeded
        assert result.replan_count == 1
        assert planner.call_count == 2  # initial + 1 replan

    def test_max_replan_reached(self, tmp_path: Path) -> None:
        orch, planner, _, _ = _build_orch(tmp_path, success_after_replans=None)
        task, result = orch.run("test")

        assert not result.final_succeeded
        assert result.replan_count == ReplanOrchestrator.MAX_REPLAN
        assert task.error == "Max re-plan reached"
        assert task.status == TaskStatus.FAILED
        assert planner.call_count == ReplanOrchestrator.MAX_REPLAN + 1

    def test_replan_twice_then_pass(self, tmp_path: Path) -> None:
        orch, planner, _, _ = _build_orch(tmp_path, success_after_replans=2)
        task, result = orch.run("test")

        assert result.final_succeeded
        assert result.replan_count == 2
        assert planner.call_count == 3


class TestReplanIssueAccumulation:
    def test_issues_passed_to_planner_on_replan(self, tmp_path: Path) -> None:
        orch, planner, _, _ = _build_orch(tmp_path, success_after_replans=1)
        orch.run("test task")

        second_call = planner.call_args_list[1]
        description, issues = second_call[0]
        assert isinstance(issues, list)
        assert len(issues) > 0

    def test_plan_stored_on_task(self, tmp_path: Path) -> None:
        orch, _, _, _ = _build_orch(tmp_path, success_after_replans=0)
        task, result = orch.run("test")
        assert task.plan == {"steps": ["x"]}
        assert result.final_plan == {"steps": ["x"]}
