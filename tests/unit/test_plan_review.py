"""W2 D5 작업 1: Plan Review 테스트."""

from service.pipeline.plan_review import (
    PlanReviewResult,
    classify_user_decision,
    format_plan_for_user,
    review_plan,
)
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan() -> Plan:
    mc = CharacterPlan(name="투르윈", role="주인공", description="신참 모험가")
    return Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=mc,
        world=WorldSetting(setting_name="신참 던전", genre="판타지", tone="진지", rules=["마법"]),
        opening_scene="투르윈은 던전 입구에 섰다.",
        initial_choices=["들어가기", "주변 살피기"],
    )


class TestClassifyUserDecision:
    def test_approve_ok(self) -> None:
        assert classify_user_decision("ok") == "approve"

    def test_approve_ne(self) -> None:
        assert classify_user_decision("네") == "approve"

    def test_approve_start(self) -> None:
        assert classify_user_decision("시작") == "approve"

    def test_modify_keywords(self) -> None:
        assert classify_user_decision("수정해줘") == "modify"

    def test_modify_change(self) -> None:
        assert classify_user_decision("change the world") == "modify"

    def test_cancel_keywords(self) -> None:
        assert classify_user_decision("취소") == "cancel"

    def test_cancel_quit(self) -> None:
        assert classify_user_decision("quit") == "cancel"

    def test_clarify_unknown(self) -> None:
        assert classify_user_decision("음...") == "clarify"

    def test_cancel_priority_over_approve(self) -> None:
        # "취소" + "ok" → cancel 우선
        assert classify_user_decision("ok 취소") == "cancel"


class TestReviewPlan:
    def test_approve_returns_approve(self) -> None:
        plan = _make_plan()
        r = review_plan(plan, "ok")
        assert isinstance(r, PlanReviewResult)
        assert r.decision == "approve"
        assert r.modification_request == ""

    def test_modify_fills_request(self) -> None:
        plan = _make_plan()
        r = review_plan(plan, "수정해줘, 캐릭터 이름 바꿔")
        assert r.decision == "modify"
        assert "수정" in r.modification_request

    def test_cancel_decision(self) -> None:
        plan = _make_plan()
        r = review_plan(plan, "취소할게")
        assert r.decision == "cancel"

    def test_raw_input_stored(self) -> None:
        plan = _make_plan()
        r = review_plan(plan, "네")
        assert r.raw_input == "네"


class TestFormatPlanForUser:
    def test_contains_work_name(self) -> None:
        plan = _make_plan()
        text = format_plan_for_user(plan)
        assert "novice_dungeon_run" in text

    def test_contains_character_name(self) -> None:
        plan = _make_plan()
        text = format_plan_for_user(plan)
        assert "투르윈" in text

    def test_contains_opening_scene(self) -> None:
        plan = _make_plan()
        text = format_plan_for_user(plan)
        assert "던전 입구" in text

    def test_contains_initial_choices(self) -> None:
        plan = _make_plan()
        text = format_plan_for_user(plan)
        assert "들어가기" in text
