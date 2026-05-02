"""W2 D4 작업 1: Plan → GameState 테스트."""

from service.game.init_from_plan import (
    _extract_initial_location,
    build_game_context,
    init_game_state_from_plan,
)
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan() -> Plan:
    return Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=CharacterPlan(
            name="투르윈", role="주인공", description="신참",
        ),
        supporting_characters=[
            CharacterPlan(name="셰인", role="조력자", description="멘토"),
            CharacterPlan(name="에라드", role="동료", description="전사"),
        ],
        world=WorldSetting(
            setting_name="신참 던전 세계",
            genre="판타지",
            tone="진지",
            rules=["마법 존재", "괴물 위험"],
        ),
        opening_scene="투르윈은 던전 입구에 서 있다.",
        initial_choices=["들어가기", "살피기"],
        ip_masking_applied=True,
    )


class TestInitGameState:
    def test_basic_init(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)

        assert state.scenario_id == "novice_dungeon_run"
        assert state.turn == 0
        assert "투르윈" in state.characters
        assert "셰인" in state.characters
        assert "에라드" in state.characters
        assert len(state.history) == 0

    def test_main_character_role(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        mc = state.characters["투르윈"]
        assert mc.role == "주인공"
        assert mc.hp == 100

    def test_phase_progress_initialized(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        assert state.phase_progress.current_phase_id == "phase_1_opening"
        assert state.phase_progress.phase_started_turn == 0

    def test_location_extracted(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        assert "던전" in state.location or "입구" in state.location

    def test_custom_scenario_id(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan, scenario_id="custom_id")
        assert state.scenario_id == "custom_id"


class TestExtractLocation:
    def test_with_dungeon_keyword(self) -> None:
        loc = _extract_initial_location("투르윈은 어두운 던전 입구에 서 있다.")
        assert "던전" in loc

    def test_with_village(self) -> None:
        loc = _extract_initial_location("작은 마을의 광장에서 시작한다.")
        assert "마을" in loc or "광장" in loc

    def test_no_keyword_falls_back(self) -> None:
        loc = _extract_initial_location("뭔가 이상한 일이 일어났다.")
        assert len(loc) > 0

    def test_empty_returns_unknown(self) -> None:
        loc = _extract_initial_location("")
        assert loc == "unknown"


class TestGameContext:
    def test_full_context(self) -> None:
        plan = _make_plan()
        state = init_game_state_from_plan(plan)
        ctx = build_game_context(plan, state)

        assert ctx["work_name"] == "novice_dungeon_run"
        assert ctx["world_setting"] == "신참 던전 세계"
        assert ctx["main_character_name"] == "투르윈"
        assert len(ctx["supporting_characters"]) == 2
        assert ctx["language"] == "ko"
        assert ctx["character_response"] is True
        assert ctx["current_turn"] == 0
        assert ctx["ip_masking_applied"] is True
