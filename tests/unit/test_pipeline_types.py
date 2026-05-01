"""W2 D1 작업 1: Pipeline types 테스트."""


from service.pipeline.types import (
    CharacterPlan,
    InterviewResult,
    PipelineState,
    Plan,
    PlanVerifyResult,
    WorldSetting,
)


class TestInterviewResult:
    def test_skip_with_input(self) -> None:
        r = InterviewResult(skip=True, parsed_input="바바리안 게임")
        assert r.skip is True
        assert r.parsed_input == "바바리안 게임"

    def test_questions_default_when_not_skip(self) -> None:
        r = InterviewResult(skip=False)
        assert r.skip is False
        assert len(r.questions) > 0

    def test_explicit_questions(self) -> None:
        r = InterviewResult(
            skip=False,
            questions=["어떤 작품?", "어떤 캐릭터?"],
            wait_for_user=True,
        )
        assert len(r.questions) == 2
        assert r.wait_for_user is True

    def test_skip_true_no_auto_question(self) -> None:
        r = InterviewResult(skip=True)
        assert r.questions == []


class TestPlanModel:
    def test_minimal_plan(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        plan = Plan(work_name="novice_dungeon_run", work_genre="판타지", main_character=mc)
        assert plan.work_name == "novice_dungeon_run"
        assert plan.main_character.name == "투르윈"
        assert plan.ip_masking_applied is False

    def test_plan_to_dict(self) -> None:
        mc = CharacterPlan(name="x", role="주인공", description="d")
        plan = Plan(work_name="w", work_genre="g", main_character=mc)
        d = plan.to_dict()
        assert d["work_name"] == "w"
        assert d["main_character"]["name"] == "x"

    def test_full_plan_with_supporting(self) -> None:
        mc = CharacterPlan(name="투르윈", role="주인공", description="d")
        sc = CharacterPlan(name="GM", role="GM", description="안내자")
        plan = Plan(
            work_name="test",
            work_genre="판타지",
            main_character=mc,
            supporting_characters=[sc],
            world=WorldSetting(
                setting_name="신참 던전",
                genre="판타지",
                tone="진지",
                rules=["마법 존재", "괴물 존재"],
            ),
            opening_scene="던전 입구",
            initial_choices=["들어가기", "주변 살피기"],
            ip_masking_applied=True,
        )
        assert len(plan.supporting_characters) == 1
        assert plan.world.setting_name == "신참 던전"
        assert len(plan.initial_choices) == 2


class TestPlanVerifyResult:
    def test_pass_perfect(self) -> None:
        r = PlanVerifyResult(passed=True, score=100.0)
        assert r.passed is True
        assert r.ip_leakage_score == 100.0

    def test_fail_with_reasons(self) -> None:
        r = PlanVerifyResult(
            passed=False,
            score=40.0,
            failures=["IP 누출", "캐릭터 일관성"],
            ip_leakage_score=20.0,
        )
        assert not r.passed
        assert len(r.failures) == 2


class TestPipelineState:
    def test_initial(self) -> None:
        s = PipelineState()
        assert s.stage == "interview"
        assert s.user_input_raw == ""
        assert s.cumulative_cost_usd == 0.0

    def test_after_interview(self) -> None:
        s = PipelineState(
            stage="planning",
            user_input_raw="바바리안 게임",
            work_name_input="바바리안",
            interview_result=InterviewResult(skip=True, parsed_input="바바리안"),
        )
        assert s.stage == "planning"
        assert s.interview_result is not None
        assert s.interview_result.skip is True
