"""강제 귀환 state 변환 단위 테스트."""

from __future__ import annotations

from service.api.v2_freeform_router import (
    _force_return_narrative,
    _force_return_to_city,
    _post_apply_dungeon_clock,
)
from service.sim.session_manager import SessionState


def _make_state(**kwargs: object) -> SessionState:
    base: dict[str, object] = dict(
        session_id="test-sid",
        current_hp=80,
        max_hp=100,
        inventory=["고블린 정수", "마석"],
        location="1층 중심부",
        encounters=[{"name": "고블린"}],
        turn_count=10,
        created_at=0.0,
        last_active=0.0,
        status_effects=[{"type": "poison", "duration": 3}],
        player_level=5,
        player_xp=200,
        max_essences=5,
        soul_power=50,
        absorbed_essences=[{"essence_name": "칼날늑대"}],
        defeated_monster_types=["고블린"],
        floor_number=1,
        hours_in_dungeon=168.0,
    )
    base.update(kwargs)
    return SessionState(**base)  # type: ignore[arg-type]


class TestForceReturnToCity:
    def test_floor_reset_to_zero(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert state.floor_number == 0

    def test_location_set_to_plaza(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert "차원광장" in state.location

    def test_encounters_cleared(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert state.encounters == []

    def test_status_effects_cleared(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert state.status_effects == []

    def test_hours_in_dungeon_reset(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert state.hours_in_dungeon == 0.0

    def test_inventory_preserved(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert "고블린 정수" in state.inventory
        assert "마석" in state.inventory

    def test_level_xp_preserved(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert state.player_level == 5
        assert state.player_xp == 200

    def test_absorbed_essences_preserved(self) -> None:
        state = _make_state()
        _force_return_to_city(state)
        assert len(state.absorbed_essences) == 1
        assert state.absorbed_essences[0]["essence_name"] == "칼날늑대"

    def test_last_spawn_turn_reset(self) -> None:
        state = _make_state()
        state.last_spawn_turn = 5
        _force_return_to_city(state)
        assert state.last_spawn_turn == -10


class TestForceReturnNarrative:
    def test_contains_closure_message(self) -> None:
        text = _force_return_narrative()
        assert "미궁이 폐쇄되었습니다" in text

    def test_contains_light_visual(self) -> None:
        text = _force_return_narrative()
        assert "빛이 눈앞을" in text

    def test_contains_city_message(self) -> None:
        text = _force_return_narrative()
        assert "라프도니아로 이동합니다" in text


class TestPostApplyDungeonClock:
    def test_floor_zero_no_op(self) -> None:
        state = _make_state(floor_number=0, hours_in_dungeon=0.0)
        result = _post_apply_dungeon_clock(state, 0.0)
        assert result is None

    def test_force_return_triggered(self) -> None:
        state = _make_state(floor_number=1, hours_in_dungeon=168.5)
        result = _post_apply_dungeon_clock(state, 167.5)
        assert result is not None
        assert "폐쇄" in result
        assert state.floor_number == 0  # 귀환 완료

    def test_warning_1h_triggered(self) -> None:
        # 166.7h → 167.2h: 1h 경고 cross
        state = _make_state(floor_number=1, hours_in_dungeon=167.2)
        result = _post_apply_dungeon_clock(state, 166.7)
        assert result is not None
        assert "층계" in result
        assert state.floor_number == 1  # 귀환 X

    def test_no_event(self) -> None:
        state = _make_state(floor_number=1, hours_in_dungeon=50.0)
        result = _post_apply_dungeon_clock(state, 49.0)
        assert result is None
