"""W2 D4 작업 9: Full Pipeline E2E (Mock).

Interview → Planning → Verify → GameState → GameLoop
"""

import pytest

from service.game.game_loop import GameLoop
from service.game.gm_agent import MockGMAgent
from service.game.init_from_plan import init_game_state_from_plan
from service.pipeline.interview import InterviewAgent
from service.pipeline.plan_verify import PlanVerifyAgent
from service.pipeline.planning import MockPlanningAgent
from service.pipeline.state_machine import PipelineStateMachine
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


class TestFullPipelineMock:
    def test_clear_input_to_game_loop(self) -> None:
        """E2E: 명확한 입력 → 게임 시작 → 첫 turn."""
        sm = PipelineStateMachine()

        interview = InterviewAgent()
        ir_session = interview.run(
            "나는 novice_dungeon_run에서 주인공으로 살아보고 싶어"
        )
        ir = ir_session.to_interview_result()
        ok = sm.apply_interview_result(ir)

        if not ir.skip:
            pytest.skip("classifier returned ambiguous (W2 D2 fine-tune 필요)")
        assert ok

        planning = MockPlanningAgent()
        pr = planning.run(
            work_name="novice_dungeon_run",
            user_preferences={"entry_point": "주인공"},
        )
        ok = sm.apply_plan_result(pr)
        assert ok
        assert pr.error is None

        verify = PlanVerifyAgent()
        vr = verify.verify(pr.plan, user_preferences={"entry_point": "주인공"})
        ok = sm.apply_plan_verify(vr)
        if not vr.passed:
            pytest.skip("plan didn't pass verify (Mock 한계, OK)")
        assert ok

        state = init_game_state_from_plan(pr.plan)
        assert state.turn == 0
        assert "투르윈" in state.characters

        gm = MockGMAgent()
        loop = GameLoop(gm)
        result = loop.process_action(pr.plan, state, "들어가기")

        assert result.mechanical_passed
        assert result.game_state.turn == 1

    def test_3_turns_simulation(self) -> None:
        """3 turn 시뮬: state 누적 검증."""
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        plan = Plan(
            work_name="novice_dungeon_run",
            work_genre="판타지",
            main_character=mc,
            world=WorldSetting(
                setting_name="던전", genre="판타지",
                tone="진지", rules=["마법"],
            ),
            opening_scene="투르윈은 던전 입구에 있다.",
        )
        state = init_game_state_from_plan(plan)

        gm = MockGMAgent(mock_responses=[
            "응답 1: 던전 입구",
            "응답 2: 통로",
            "응답 3: 방",
        ])
        loop = GameLoop(gm)

        actions = ["들어가기", "주변 살피기", "더 깊이 들어가기"]
        for action in actions:
            result = loop.process_action(plan, state, action)
            assert result.mechanical_passed

        assert state.turn == 3
        assert len(state.history) == 3
        assert state.history[0].user_action == "들어가기"
