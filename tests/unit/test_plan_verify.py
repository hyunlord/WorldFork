"""W2 D3 작업 6: Plan Verify 테스트."""

from service.pipeline.plan_verify import (
    MockPlanVerifyAgent,
    PlanVerifyAgent,
    check_ip_leakage,
    check_plan_quality,
    check_user_preference_match,
    check_world_consistency,
)
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _clean_plan() -> Plan:
    return Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="투르윈", role="주인공", description="신참 모험가",
        ),
        supporting_characters=[
            CharacterPlan(name="셰인", role="조력자", description="멘토"),
        ],
        world=WorldSetting(
            setting_name="신참 던전",
            genre="판타지",
            tone="진지",
            rules=["마법 존재", "괴물 위험"],
        ),
        opening_scene="투르윈은 던전 입구에 서 있다. 어둠이 깊다.",
        initial_choices=["들어가기", "살피기", "돌아가기"],
    )


def _dirty_plan_with_ip() -> Plan:
    return Plan(
        work_name="바바리안",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="비요른", role="주인공", description="바바리안",
        ),
        world=WorldSetting(setting_name="라프도니아", genre="판타지", tone="d", rules=[]),
    )


class TestCheckIPLeakage:
    def test_clean_plan_high_score(self) -> None:
        score, issues = check_ip_leakage(_clean_plan())
        assert score >= 90
        assert len(issues) == 0

    def test_dirty_plan_low_score(self) -> None:
        score, issues = check_ip_leakage(_dirty_plan_with_ip())
        assert score < 70
        assert len(issues) > 0


class TestCheckWorldConsistency:
    def test_clean_world(self) -> None:
        score, issues = check_world_consistency(_clean_plan())
        assert score >= 80

    def test_empty_world_low_score(self) -> None:
        plan = _clean_plan()
        plan.world.rules = []
        plan.world.setting_name = ""
        score, issues = check_world_consistency(plan)
        assert score < 80
        assert len(issues) >= 1


class TestCheckUserPreferences:
    def test_match(self) -> None:
        score, issues = check_user_preference_match(
            _clean_plan(), {"entry_point": "주인공"},
        )
        assert score == 100

    def test_mismatch(self) -> None:
        plan = _clean_plan()
        plan.main_character.role = "엑스트라"
        score, issues = check_user_preference_match(
            plan, {"entry_point": "주인공"},
        )
        assert score < 100


class TestCheckPlanQuality:
    def test_full_plan_pass(self) -> None:
        score, issues = check_plan_quality(_clean_plan())
        assert score >= 90

    def test_empty_opening_low(self) -> None:
        plan = _clean_plan()
        plan.opening_scene = ""
        score, issues = check_plan_quality(plan)
        assert score < 80

    def test_too_few_choices_low(self) -> None:
        plan = _clean_plan()
        plan.initial_choices = ["one"]
        score, issues = check_plan_quality(plan)
        assert score < 90


class TestMockPlanVerifyAgent:
    def test_force_pass(self) -> None:
        agent = MockPlanVerifyAgent(force_pass=True)
        r = agent.verify(_dirty_plan_with_ip())
        assert r.passed
        assert isinstance(r.score, float)

    def test_real_score_dirty(self) -> None:
        agent = MockPlanVerifyAgent(force_pass=False)
        r = agent.verify(_dirty_plan_with_ip())
        assert r.score < 80
        assert not r.passed

    def test_real_score_clean(self) -> None:
        agent = MockPlanVerifyAgent(force_pass=False)
        r = agent.verify(_clean_plan(), user_preferences={"entry_point": "주인공"})
        assert r.score >= 80


class TestPlanVerifyAgent:
    def test_pass_clean_plan(self) -> None:
        agent = PlanVerifyAgent()
        r = agent.verify(_clean_plan(), user_preferences={"entry_point": "주인공"})
        assert r.passed
        assert r.ip_leakage_score >= 90

    def test_fail_dirty_plan(self) -> None:
        agent = PlanVerifyAgent()
        r = agent.verify(_dirty_plan_with_ip())
        assert not r.passed
        assert r.ip_leakage_score < 70
