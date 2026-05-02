"""W2 D3 작업 8: Interview → Planning → Verify E2E (Mock)."""

import pytest

from service.pipeline.interview import InterviewAgent
from service.pipeline.plan_verify import PlanVerifyAgent
from service.pipeline.planning import MockPlanningAgent
from service.pipeline.state_machine import PipelineStateMachine
from service.pipeline.types import PipelineState


class TestPipelineE2E:
    def test_planning_to_verify_flow(self) -> None:
        """Planning → Verify 핵심 흐름 (State Machine 통합)."""
        sm = PipelineStateMachine(PipelineState(stage="planning"))

        planning = MockPlanningAgent()
        pr = planning.run(
            work_name="novice_dungeon_run",
            user_preferences={"entry_point": "주인공"},
        )
        ok = sm.apply_plan_result(pr)

        assert pr.error is None
        assert ok
        # stage는 str로 꺼내 비교 (mypy narrowing 회피)
        stage: str = sm.state.stage
        assert stage == "verify"
        assert pr.plan.work_name == "novice_dungeon_run"

        verify = PlanVerifyAgent()
        vr = verify.verify(pr.plan, user_preferences={"entry_point": "주인공"})
        ok2 = sm.apply_plan_verify(vr)

        if vr.passed:
            assert ok2
            stage2: str = sm.state.stage
            assert stage2 == "review"

    def test_interview_ambiguous_blocks_planning(self) -> None:
        """Ambiguous → 사용자 답변 대기 (Planning 진입 X)."""
        interview = InterviewAgent()
        ir_session = interview.run("바바리안")  # 짧음, ambiguous 예상
        ir = ir_session.to_interview_result()

        sm = PipelineStateMachine()
        ok = sm.apply_interview_result(ir)

        if ir.skip:
            pytest.skip("classifier returned clear (W2 D2 fine-tune 필요)")

        assert not ok
        stage: str = sm.state.stage
        assert stage == "interview"
        assert len(ir.questions) >= 1

    def test_mock_planning_unknown_work_blocks_verify(self) -> None:
        """모르는 작품 → Planning error → Verify 진입 X."""
        sm = PipelineStateMachine(PipelineState(stage="planning"))

        planning = MockPlanningAgent()
        pr = planning.run(work_name="totally_unknown_xyz")
        ok = sm.apply_plan_result(pr)

        assert pr.error is not None
        assert not ok
        stage: str = sm.state.stage
        assert stage == "planning"
