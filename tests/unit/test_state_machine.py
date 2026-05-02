"""W2 D2 Phase 3: PipelineStateMachine 테스트."""

import pytest

from service.pipeline.state_machine import STAGES, PipelineStateMachine
from service.pipeline.types import (
    CharacterPlan,
    InterviewResult,
    PipelineState,
    Plan,
    PlanResult,
    PlanVerifyResult,
)


class TestStagelist:
    def test_starts_with_interview(self) -> None:
        assert STAGES[0] == "interview"

    def test_ends_with_complete(self) -> None:
        assert STAGES[-1] == "complete"

    def test_eight_stages(self) -> None:
        assert len(STAGES) == 8

    def test_planning_before_verify(self) -> None:
        assert STAGES.index("planning") < STAGES.index("verify")


class TestPipelineStateMachineInit:
    def test_default_stage_is_interview(self) -> None:
        sm = PipelineStateMachine()
        assert sm.current_stage == "interview"

    def test_custom_state(self) -> None:
        state = PipelineState(stage="planning")
        sm = PipelineStateMachine(state=state)
        assert sm.current_stage == "planning"


class TestAdvanceTo:
    def test_forward_allowed(self) -> None:
        sm = PipelineStateMachine()
        sm.advance_to("planning")
        assert sm.current_stage == "planning"

    def test_backward_raises(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="planning"))
        with pytest.raises(ValueError, match="backward"):
            sm.advance_to("interview")

    def test_same_stage_raises(self) -> None:
        sm = PipelineStateMachine()
        with pytest.raises(ValueError, match="backward"):
            sm.advance_to("interview")

    def test_skip_stages_allowed(self) -> None:
        sm = PipelineStateMachine()
        sm.advance_to("verify")
        assert sm.current_stage == "verify"


class TestAdvance:
    def test_auto_advance(self) -> None:
        sm = PipelineStateMachine()
        next_stage = sm.advance()
        assert next_stage == "planning"
        assert sm.current_stage == "planning"

    def test_advance_from_complete_raises(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="complete"))
        with pytest.raises(ValueError, match="final"):
            sm.advance()


class TestApplyResults:
    def _make_plan(self) -> Plan:
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        return Plan(work_name="test", work_genre="판타지", main_character=mc)

    def test_apply_clear_interview_result(self) -> None:
        sm = PipelineStateMachine()
        ir = InterviewResult(skip=True, parsed_input="입력")
        sm.apply_interview_result(ir)
        assert sm.current_stage == "planning"
        assert sm.state.interview_result is ir

    def test_apply_ambiguous_interview_no_advance(self) -> None:
        sm = PipelineStateMachine()
        ir = InterviewResult(skip=False, questions=["Q?"])
        sm.apply_interview_result(ir)
        assert sm.current_stage == "interview"

    def test_apply_plan_result(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="planning"))
        plan = self._make_plan()
        result = PlanResult(plan=plan)
        ok = sm.apply_plan_result(result)
        assert ok
        assert sm.current_stage == "verify"
        assert sm.state.plan is plan

    def test_apply_plan_result_error_no_advance(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="planning"))
        plan = self._make_plan()
        result = PlanResult(plan=plan, error="something failed")
        ok = sm.apply_plan_result(result)
        assert not ok
        assert sm.current_stage == "planning"

    def test_apply_plan_verify_passed(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="verify"))
        result = PlanVerifyResult(passed=True, score=90.0)
        sm.apply_plan_verify(result)
        assert sm.current_stage == "review"

    def test_apply_plan_verify_failed_stays(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="verify"))
        result = PlanVerifyResult(passed=False, score=40.0)
        sm.apply_plan_verify(result)
        assert sm.current_stage == "verify"

    def test_is_complete(self) -> None:
        sm = PipelineStateMachine(PipelineState(stage="complete"))
        assert sm.is_complete() is True

    def test_not_complete(self) -> None:
        sm = PipelineStateMachine()
        assert sm.is_complete() is False
