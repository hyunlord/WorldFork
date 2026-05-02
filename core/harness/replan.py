"""Re-plan outer loop max 2 (★ 본인 자료 AutoDev 정확).

CodingLoop max 3 retry 모두 실패 → Re-plan 사이클:
  - Plan 재작성 (★ 다른 LLM 가능)
  - 새 plan으로 CodingLoop 재진입
  - max 2 사이클

★ 본인 자료 정신:
  매 단계 독립 agent
  Plan Drafter ≠ Coder ≠ Verifier
  정보 격리: 점수 절대 전달 X
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .coding_loop import CodingLoop, CodingResult
from .hooks import HookEvent, HookManager
from .task_context import TaskContext, TaskStatus


@dataclass
class ReplanResult:
    """Re-plan 결과."""

    final_succeeded: bool
    coding_results: list[CodingResult] = field(default_factory=list)
    replan_count: int = 0
    final_plan: dict[str, Any] | None = None
    abort_reason: str = ""


PlanDrafterFn = Callable[[str, list[str]], dict[str, Any]]


class ReplanOrchestrator:
    """Re-plan outer loop max 2 (★ 본인 자료 정신).

    흐름:
      PrePlan → PlanDrafter → PostPlan → CodingLoop
      → CodingLoop 실패 → OnReplan → 새 plan → CodingLoop
      → max 2 사이클 후 TaskFail
    """

    MAX_REPLAN = 2

    def __init__(
        self,
        hook_manager: HookManager,
        plan_drafter: PlanDrafterFn,
        coding_loop: CodingLoop,
    ) -> None:
        """
        Args:
            hook_manager: 12 이벤트 manager
            plan_drafter: (description, accumulated_issues) → plan dict
            coding_loop: CodingLoop 인스턴스
        """
        self._hooks = hook_manager
        self._planner = plan_drafter
        self._loop = coding_loop

    def run(
        self,
        task_description: str,
        layer: str = "1",
    ) -> tuple[TaskContext, ReplanResult]:
        """전체 흐름 실행.

        Returns:
            (TaskContext, ReplanResult)
        """
        task = TaskContext(description=task_description, layer=layer)
        result = ReplanResult(final_succeeded=False)

        # TaskStart hook
        ctx = self._hooks.trigger(
            HookEvent.TASK_START,
            payload={"task_id": task.task_id, "description": task_description},
        )
        if ctx.abort:
            result.abort_reason = ctx.abort_reason
            task.mark_completed(success=False)
            return task, result

        # Re-plan 사이클 (★ max 2 → 총 3회 plan 작성)
        accumulated_issues: list[str] = []

        for replan_n in range(self.MAX_REPLAN + 1):
            task.status = TaskStatus.PLANNING
            task.replan_count = replan_n

            # PrePlan hook
            self._hooks.trigger(
                HookEvent.PRE_PLAN,
                payload={"replan_n": replan_n},
            )

            # Plan 작성 (★ feedback에 점수 X)
            try:
                plan = self._planner(task_description, accumulated_issues)
            except Exception as e:
                result.abort_reason = f"Planner failed: {e}"
                task.mark_completed(success=False)
                return task, result

            task.plan = plan
            result.final_plan = plan

            # PostPlan hook
            self._hooks.trigger(
                HookEvent.POST_PLAN,
                payload={"plan": plan},
            )

            # CodingLoop 실행
            coding_result = self._loop.run(task)
            result.coding_results.append(coding_result)

            if coding_result.succeeded:
                result.final_succeeded = True
                result.replan_count = replan_n

                # TaskComplete hook
                self._hooks.trigger(
                    HookEvent.TASK_COMPLETE,
                    payload={
                        "task_id": task.task_id,
                        "final_score": coding_result.final_score,
                    },
                )
                task.mark_completed(success=True)
                return task, result

            # CodingLoop 실패 → 이슈 누적 (점수 X)
            accumulated_issues.extend(coding_result.issues_for_retry)

            # 마지막 시도가 아니면 OnReplan
            if replan_n < self.MAX_REPLAN:
                task.status = TaskStatus.REPLANNING
                self._hooks.trigger(
                    HookEvent.ON_REPLAN,
                    payload={
                        "replan_n": replan_n + 1,
                        "issues_count": len(accumulated_issues),
                    },
                )

        # ★ 모두 실패
        result.replan_count = self.MAX_REPLAN

        # TaskFail hook
        self._hooks.trigger(
            HookEvent.TASK_FAIL,
            payload={"task_id": task.task_id, "reason": "max replan reached"},
        )

        task.error = "Max re-plan reached"
        task.mark_completed(success=False)

        return task, result
