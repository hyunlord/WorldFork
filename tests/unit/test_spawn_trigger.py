"""Phase D step 6c — spawn trigger unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from service.canon.schema import CanonFacts, Location
from service.sim.spawn_trigger import (
    SPAWN_COOLDOWN_TURNS,
    determine_location_type,
    should_spawn,
    trigger_spawn,
)

# ─── determine_location_type ───


def _facts_with_location(name: str, loc_type: str) -> CanonFacts:
    loc = Location(name=name, location_type=loc_type)  # type: ignore[arg-type]
    return CanonFacts(locations=[loc])


def test_determine_exact_match() -> None:
    facts = _facts_with_location("마탑", "dungeon")
    assert determine_location_type("마탑", facts) == "dungeon"


def test_determine_partial_match() -> None:
    facts = _facts_with_location("마탑", "dungeon")
    assert determine_location_type("마탑 1층", facts) == "dungeon"


def test_determine_heuristic_rift() -> None:
    assert determine_location_type("차원 균열 내부", None) == "rift"


def test_determine_heuristic_city() -> None:
    assert determine_location_type("라스카니아 광장", None) == "city"


def test_determine_heuristic_dungeon() -> None:
    assert determine_location_type("지하 동굴", None) == "dungeon"


def test_determine_heuristic_wilderness_fallback() -> None:
    assert determine_location_type("알 수 없는 평원", None) == "wilderness"


def test_determine_no_facts_dungeon_name() -> None:
    assert determine_location_type("마탑 지하", None) == "dungeon"


# ─── should_spawn ───


def test_should_spawn_city_rate_zero() -> None:
    assert not should_spawn("city", turn_count=10, last_spawn_turn=0)


def test_should_spawn_cooldown_blocks() -> None:
    assert not should_spawn("dungeon", turn_count=1, last_spawn_turn=0)


def test_should_spawn_cooldown_exact_boundary() -> None:
    assert not should_spawn(
        "dungeon", turn_count=SPAWN_COOLDOWN_TURNS - 1, last_spawn_turn=0
    )


def test_should_spawn_after_cooldown_random_true() -> None:
    with patch("service.sim.spawn_trigger.random.random", return_value=0.0):
        assert should_spawn("dungeon", turn_count=10, last_spawn_turn=0)


def test_should_spawn_after_cooldown_random_false() -> None:
    with patch("service.sim.spawn_trigger.random.random", return_value=0.99):
        assert not should_spawn("dungeon", turn_count=10, last_spawn_turn=0)


def test_should_spawn_rift_higher_rate() -> None:
    # rift rate=0.60 > dungeon rate=0.30
    with patch("service.sim.spawn_trigger.random.random", return_value=0.50):
        assert should_spawn("rift", turn_count=10, last_spawn_turn=0)
        assert not should_spawn("dungeon", turn_count=10, last_spawn_turn=0)


def test_should_spawn_wilderness() -> None:
    with patch("service.sim.spawn_trigger.random.random", return_value=0.10):
        assert should_spawn("wilderness", turn_count=10, last_spawn_turn=0)


# ─── trigger_spawn ───


def _mock_table(enemy_name: str = "테스트 적") -> MagicMock:
    from service.sim.enemy import Enemy
    e = Enemy(name=enemy_name, hp=20, max_hp=20, attack=5, defense=2)
    table = MagicMock()
    table.get_location_grade.return_value = 3
    table.spawn_for_location.return_value = [e]
    return table


def test_trigger_spawn_no_spawn_returns_empty() -> None:
    table = _mock_table()
    with patch("service.sim.spawn_trigger.should_spawn", return_value=False):
        result = trigger_spawn(
            location_name="마탑",
            location_type="dungeon",
            turn_count=10,
            last_spawn_turn=0,
            spawn_table=table,
        )
    assert result == []


def test_trigger_spawn_returns_enemy_dicts() -> None:
    table = _mock_table("고블린")
    with patch("service.sim.spawn_trigger.should_spawn", return_value=True):
        with patch("service.sim.spawn_trigger.random.randint", return_value=1):
            result = trigger_spawn(
                location_name="마탑",
                location_type="dungeon",
                turn_count=10,
                last_spawn_turn=0,
                spawn_table=table,
            )
    assert len(result) == 1
    assert result[0]["name"] == "고블린"


def test_trigger_spawn_calls_table_with_location_type() -> None:
    table = _mock_table()
    with patch("service.sim.spawn_trigger.should_spawn", return_value=True):
        with patch("service.sim.spawn_trigger.random.randint", return_value=1):
            trigger_spawn(
                location_name="마탑",
                location_type="dungeon",
                turn_count=10,
                last_spawn_turn=0,
                spawn_table=table,
            )
    table.spawn_for_location.assert_called_once_with("마탑", "dungeon", 1)


def test_trigger_spawn_empty_enemy_pool_returns_empty() -> None:
    table = MagicMock()
    table.get_location_grade.return_value = 3
    table.spawn_for_location.return_value = []
    with patch("service.sim.spawn_trigger.should_spawn", return_value=True):
        with patch("service.sim.spawn_trigger.random.randint", return_value=1):
            result = trigger_spawn(
                location_name="마탑",
                location_type="dungeon",
                turn_count=10,
                last_spawn_turn=0,
                spawn_table=table,
            )
    assert result == []
