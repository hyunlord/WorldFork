"""Day 1: GameState + Character 단위 테스트."""

import pytest

from service.game.state import Character, GameState


class TestCharacter:
    def test_default(self) -> None:
        c = Character(name="투르윈", role="주인공")
        assert c.hp == 100
        assert c.inventory == []
        assert c.is_alive()

    def test_dead(self) -> None:
        c = Character(name="투르윈", role="주인공", hp=0)
        assert not c.is_alive()

    def test_inventory(self) -> None:
        c = Character(name="셰인", role="동료", inventory=["지팡이"])
        assert "지팡이" in c.inventory


class TestGameState:
    def test_initial(self) -> None:
        s = GameState(scenario_id="test")
        assert s.turn == 0
        assert s.history == []
        assert s.total_cost_usd() == 0.0
        assert s.avg_latency_ms() == 0.0

    def test_add_turn(self) -> None:
        s = GameState(scenario_id="test")
        s.add_turn(
            user_action="둘러본다",
            gm_response="주변엔 아무것도 없다.",
            cost_usd=0.0,
            latency_ms=12000,
        )
        assert s.turn == 1
        assert len(s.history) == 1
        assert s.history[0].user_action == "둘러본다"
        assert s.history[0].latency_ms == 12000

    def test_total_cost(self) -> None:
        s = GameState(scenario_id="test")
        s.add_turn("a1", "r1", 0.001, 100)
        s.add_turn("a2", "r2", 0.002, 200)
        assert s.total_cost_usd() == pytest.approx(0.003)

    def test_avg_latency(self) -> None:
        s = GameState(scenario_id="test")
        s.add_turn("a", "r", 0.0, 10000)
        s.add_turn("a", "r", 0.0, 14000)
        assert s.avg_latency_ms() == pytest.approx(12000)

    def test_completed_max_turns(self) -> None:
        s = GameState(scenario_id="test")
        for i in range(5):
            s.add_turn(f"a{i}", "r", 0.0, 100)
        assert not s.is_completed(max_turns=10)
        assert s.is_completed(max_turns=5)

    def test_completed_ending_marker(self) -> None:
        s = GameState(scenario_id="test")
        s.add_turn("a", "결말입니다 [ENDING]", 0.0, 100)
        assert s.is_completed(max_turns=10)

    def test_get_player(self) -> None:
        s = GameState(scenario_id="test")
        s.characters["player"] = Character(name="투르윈", role="주인공")
        s.characters["npc"] = Character(name="셰인", role="동료")

        player = s.get_player()
        assert player is not None
        assert player.name == "투르윈"

    def test_get_player_none(self) -> None:
        s = GameState(scenario_id="test")
        assert s.get_player() is None


# Day 2: 분기 추적 필드 테스트

class TestPhaseProgress:
    def test_default(self) -> None:
        from service.game.state import PhaseProgress
        p = PhaseProgress()
        assert p.current_phase_id == "phase_1_entry"
        assert p.completed_triggers == []
        assert p.phase_started_turn == 0


class TestGameStatePhaseTracking:
    def test_default_phase(self) -> None:
        s = GameState(scenario_id="test")
        assert s.phase_progress.current_phase_id == "phase_1_entry"
        assert s.selected_ending is None

    def test_is_in_phase(self) -> None:
        s = GameState(scenario_id="test")
        assert s.is_in_phase("phase_1_entry")
        assert not s.is_in_phase("phase_4_ending")

    def test_mark_trigger(self) -> None:
        s = GameState(scenario_id="test")
        s.mark_trigger_completed("meet_shane")
        assert s.has_completed_trigger("meet_shane")
        assert not s.has_completed_trigger("nonexistent")

    def test_mark_trigger_idempotent(self) -> None:
        """같은 trigger 두 번 표시해도 한 번만 기록."""
        s = GameState(scenario_id="test")
        s.mark_trigger_completed("meet_shane")
        s.mark_trigger_completed("meet_shane")
        assert s.phase_progress.completed_triggers.count("meet_shane") == 1
