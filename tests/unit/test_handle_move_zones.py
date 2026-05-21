"""Phase D step 7 — handle_move zone 전환 단위 테스트."""

from __future__ import annotations

import asyncio

from service.api.schemas.freeform_action import ExtractedEntities
from service.sim.action_context import ActionContext
from service.sim.action_handlers import handle_move


def _ctx(
    location: str = "1층 중심부",
    user_input: str = "",
    floor_number: int = 1,
    entities_direction: str | None = None,
) -> ActionContext:
    entities = ExtractedEntities(direction=entities_direction)
    return ActionContext(
        current_hp=100,
        max_hp=100,
        inventory=[],
        location=location,
        user_input=user_input,
        floor_number=floor_number,
        extracted_entities=entities,
    )


def run(coro: object) -> object:
    import inspect
    if inspect.iscoroutine(coro):
        return asyncio.run(coro)  # type: ignore[arg-type]
    return coro


class TestMoveNoDirection:
    def test_no_direction_fails(self) -> None:
        result = run(handle_move(_ctx(user_input="이동해")))
        assert not result.success  # type: ignore[union-attr]
        assert result.fail_reason == "no_direction"  # type: ignore[union-attr]


class TestMoveTown:
    def test_town_move_success(self) -> None:
        result = run(handle_move(_ctx(location="마을", floor_number=0, user_input="북쪽으로")))
        assert result.success  # type: ignore[union-attr]
        assert result.location is None  # 마을에서는 zone 이동 없음

    def test_town_move_narrative_contains_direction(self) -> None:
        result = run(handle_move(_ctx(location="마을", floor_number=0, user_input="남쪽으로 이동")))
        assert "남쪽" in result.narrative  # type: ignore[union-attr]


class TestMoveDungeonZone:
    def test_center_north_to_north_zone(self) -> None:
        result = run(handle_move(_ctx(location="1층 중심부", user_input="북쪽으로")))
        assert result.location == "1층 북쪽 지구"  # type: ignore[union-attr]
        assert result.success  # type: ignore[union-attr]

    def test_center_south_to_south_zone(self) -> None:
        result = run(handle_move(_ctx(location="1층 중심부", user_input="남쪽으로")))
        assert result.location == "1층 남쪽 지구"  # type: ignore[union-attr]

    def test_center_east_to_east_zone(self) -> None:
        result = run(handle_move(_ctx(location="1층 중심부", user_input="동쪽으로")))
        assert result.location == "1층 동쪽 지구"  # type: ignore[union-attr]

    def test_center_west_to_west_zone(self) -> None:
        result = run(handle_move(_ctx(location="1층 중심부", user_input="서쪽으로")))
        assert result.location == "1층 서쪽 지구"  # type: ignore[union-attr]

    def test_entities_direction_overrides_text(self) -> None:
        result = run(handle_move(_ctx(
            location="1층 중심부",
            user_input="이동",
            entities_direction="east",
        )))
        assert result.location == "1층 동쪽 지구"  # type: ignore[union-attr]

    def test_move_time_advance(self) -> None:
        result = run(handle_move(_ctx(location="1층 중심부", user_input="북쪽으로")))
        assert result.time_advance == 1  # type: ignore[union-attr]


class TestMoveLightingNarrative:
    def test_bright_zone_has_light_description(self) -> None:
        result = run(handle_move(_ctx(location="1층 초입부", user_input="남쪽으로")))
        assert result.location == "1층 입구"  # type: ignore[union-attr]
        assert "수정" in result.narrative  # type: ignore[union-attr]

    def test_very_dark_zone_warns(self) -> None:
        result = run(handle_move(_ctx(location="1층 동쪽 지구", user_input="북쪽으로")))
        assert result.location == "1층 암흑지대"  # type: ignore[union-attr]
        assert "빛" in result.narrative  # type: ignore[union-attr]

    def test_normal_zone_no_extra_lighting_note(self) -> None:
        result = run(handle_move(_ctx(location="1층 입구", user_input="북쪽으로")))
        assert result.location == "1층 초입부"  # type: ignore[union-attr]


class TestMoveNoAdjacentZone:
    def test_unknown_location_fails(self) -> None:
        result = run(handle_move(_ctx(location="알 수 없는 곳", user_input="북쪽으로")))
        assert not result.success  # type: ignore[union-attr]
        assert result.fail_reason == "no_adjacent_zone"  # type: ignore[union-attr]
