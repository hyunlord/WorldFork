"""Pipeline State Machine (★ 자료 2.2 8-stage).

forward-only 전이: interview → planning → verify → review
  → agent_select → verify_select → game_loop → complete
"""

from typing import Literal

from .types import InterviewResult, PipelineState, Plan, PlanVerifyResult

StageType = Literal[
    "interview", "planning", "verify", "review",
    "agent_select", "verify_select", "game_loop", "complete",
]

STAGES: list[StageType] = [
    "interview",
    "planning",
    "verify",
    "review",
    "agent_select",
    "verify_select",
    "game_loop",
    "complete",
]


class PipelineStateMachine:
    """8단계 파이프라인 상태 머신.

    forward-only: 이전 단계로 되돌아갈 수 없음.
    """

    def __init__(self, state: PipelineState | None = None) -> None:
        self._state = state or PipelineState()

    @property
    def state(self) -> PipelineState:
        return self._state

    @property
    def current_stage(self) -> StageType:
        return self._state.stage

    def advance_to(self, target: StageType) -> None:
        """forward-only 전이. 현재 단계보다 앞의 단계로는 이동 불가."""
        current_idx = STAGES.index(self._state.stage)
        target_idx = STAGES.index(target)
        if target_idx <= current_idx:
            raise ValueError(
                f"backward transition not allowed: {self._state.stage} → {target}"
            )
        self._state.stage = target

    def advance(self) -> StageType:
        """다음 단계로 자동 전이."""
        current_idx = STAGES.index(self._state.stage)
        if current_idx >= len(STAGES) - 1:
            raise ValueError("already at final stage: complete")
        next_stage = STAGES[current_idx + 1]
        self._state.stage = next_stage
        return next_stage

    def apply_interview_result(self, result: InterviewResult) -> None:
        self._state.interview_result = result
        self._state.user_input_raw = result.parsed_input
        if result.skip:
            self.advance_to("planning")

    def apply_plan_result(self, plan: Plan) -> None:
        self._state.plan = plan
        self.advance_to("verify")

    def apply_plan_verify(self, result: PlanVerifyResult) -> None:
        self._state.plan_verify_result = result
        if result.passed:
            self.advance_to("review")
        # 실패 시 같은 단계 유지 (재시도 로직은 호출자 책임)

    def is_complete(self) -> bool:
        return self._state.stage == "complete"
