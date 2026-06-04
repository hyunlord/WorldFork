"""Phase D step 4 — SessionManager 단위 테스트."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from service.persistence.sqlite_store import SqliteStore
from service.sim.action_context import ActionResult
from service.sim.session_manager import SessionManager


def _make_manager(tmp_path: Path) -> SessionManager:
    store = SqliteStore(tmp_path / "test.db")
    return SessionManager(store)


def run(coro):  # type: ignore[no-untyped-def]
    return asyncio.run(coro)


class TestCreateSession:
    def test_default_state(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session())
        # phase-e-2: 기본 = BJORN + BARBARIAN → HP=120, 위치=라스카니아 차원광장
        assert state.current_hp == 120
        assert state.max_hp == 120
        assert state.inventory == ["방패"]  # phase-e-3: BJORN 기본 시작 아이템
        assert "라스카니아" in state.location
        assert state.turn_count == 0
        assert len(state.session_id) == 36  # UUID format

    def test_custom_state(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(
            mgr.create_session(
                current_hp=50,
                max_hp=80,
                inventory=["단검"],
                location="2층",
            )
        )
        assert state.current_hp == 50
        assert state.inventory == ["단검"]
        assert state.location == "2층"


class TestGetSession:
    def test_get_existing(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        created = run(mgr.create_session())
        found = run(mgr.get_session(created.session_id))
        assert found is not None
        assert found.session_id == created.session_id

    def test_get_missing(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        result = run(mgr.get_session("nonexistent-id"))
        assert result is None

    def test_resume_after_cache_clear(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        store = SqliteStore(db)
        mgr1 = SessionManager(store)
        state = run(mgr1.create_session(current_hp=77))

        mgr2 = SessionManager(store)
        found = run(mgr2.get_session(state.session_id))
        assert found is not None
        assert found.current_hp == 77


class TestApplyResult:
    def test_hp_change(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(current_hp=80, max_hp=100))
        result = ActionResult(
            narrative="검에 베였다. 피가 흘렀다.",
            hp_change=-20,
        )
        updated = run(
            mgr.apply_result(state.session_id, result, "공격", "intent")
        )
        assert updated.current_hp == 60
        assert updated.turn_count == 1

    def test_hp_clamped_to_zero(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(current_hp=10, max_hp=100))
        result = ActionResult(narrative="치명적인 일격을 맞았다.", hp_change=-50)
        updated = run(
            mgr.apply_result(state.session_id, result, "전투", "intent")
        )
        assert updated.current_hp == 0

    def test_hp_clamped_to_max(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(current_hp=90, max_hp=100))
        result = ActionResult(narrative="성스러운 치유를 받았다.", hp_change=30)
        updated = run(
            mgr.apply_result(state.session_id, result, "휴식", "intent")
        )
        assert updated.current_hp == 100

    def test_combat_resolve_resets_spawn_cooldown(self, tmp_path: Path) -> None:
        """★ 처치(encounter_resolved) 직후 재스폰 쿨다운을 현재 turn으로 리셋 —
        죽은 적의 옛 스폰 turn 탓에 즉시 재스폰되던 '쉴 틈 없음' 해소."""
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session())
        state.last_spawn_turn = -10  # 스폰이 오래 전(쿨다운 만료 상태)
        result = ActionResult(narrative="적을 쓰러뜨렸다.", encounter_resolved=True)
        updated = run(
            mgr.apply_result(state.session_id, result, "공격", "intent")
        )
        # 처치 후 쿨다운 리셋 — last_spawn_turn == 현재 turn(즉시 재스폰 차단)
        assert updated.last_spawn_turn == updated.turn_count

    def test_non_combat_keeps_spawn_cooldown(self, tmp_path: Path) -> None:
        """비전투 행동은 재스폰 쿨다운을 건드리지 않는다."""
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session())
        state.last_spawn_turn = 3
        result = ActionResult(narrative="주변을 둘러봤다.")  # resolved=False
        updated = run(
            mgr.apply_result(state.session_id, result, "탐색", "intent")
        )
        assert updated.last_spawn_turn == 3

    def test_inventory_add_remove(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(inventory=["낡은 검"]))
        result = ActionResult(
            narrative="아이템을 교환했다.",
            inventory_add=["강화 검"],
            inventory_remove=["낡은 검"],
        )
        updated = run(
            mgr.apply_result(state.session_id, result, "교환", "fallback")
        )
        assert "강화 검" in updated.inventory
        assert "낡은 검" not in updated.inventory

    def test_location_change(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(location="1층 입구"))
        result = ActionResult(narrative="북쪽으로 이동했다.", location="1층 중앙")
        updated = run(
            mgr.apply_result(state.session_id, result, "이동", "intent")
        )
        assert updated.location == "1층 중앙"

    def test_missing_session_raises(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        result = ActionResult(narrative="행동을 수행했다.")
        with pytest.raises(KeyError):
            run(mgr.apply_result("bad-id", result, "행동", "intent"))


class TestEndSession:
    def test_end_removes_session(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session())
        run(mgr.end_session(state.session_id))
        found = run(mgr.get_session(state.session_id))
        assert found is None

    def test_end_missing_ok(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        run(mgr.end_session("nonexistent-id"))  # should not raise


class TestGetOrCreate:
    def test_create_when_no_id(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.get_or_create(None))
        assert state.session_id is not None
        assert state.current_hp == 120  # phase-e-2: BJORN+BARBARIAN default

    def test_get_existing_by_id(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        created = run(mgr.create_session(current_hp=55))
        found = run(mgr.get_or_create(created.session_id))
        assert found.session_id == created.session_id
        assert found.current_hp == 55

    def test_create_new_when_id_missing(self, tmp_path: Path) -> None:
        mgr = _make_manager(tmp_path)
        state = run(mgr.get_or_create("no-such-id", current_hp=70))
        assert state.current_hp == 70
        assert state.session_id != "no-such-id"


class TestFloorChangeEncounters:
    """층 이동 시 이전 encounters 비움 — 마을 NPC(부족장) 던전 잔존 해소."""

    def test_floor_change_clears_town_encounters(self, tmp_path: Path) -> None:
        from service.canon.scenario import ScenarioMode

        mgr = _make_manager(tmp_path)
        # 성인식 마을 — 부족장 NPC seed
        state = run(mgr.create_session(scenario_mode=ScenarioMode.BJORN))
        assert any("부족장" in str(e.get("name", "")) for e in state.encounters)

        # 던전 진입(floor_change=1) → 이전 마을 encounters 무효
        result = ActionResult(
            narrative="던전 1층에 들어섰다.",
            location="던전 1층",
            floor_change=1,
        )
        state = run(
            mgr.apply_result(
                state.session_id, result, user_input="미궁으로", resolved_path="intent"
            )
        )
        assert state.floor_number == 1
        assert not any(
            "부족장" in str(e.get("name", "")) for e in state.encounters
        )

    def test_no_floor_change_keeps_encounters(self, tmp_path: Path) -> None:
        from service.canon.scenario import ScenarioMode

        mgr = _make_manager(tmp_path)
        state = run(mgr.create_session(scenario_mode=ScenarioMode.BJORN))
        # 층 이동 없는 행동(대화 등) → encounters 유지
        result = ActionResult(narrative="부족장과 대화했다.", time_advance=1)
        state = run(
            mgr.apply_result(
                state.session_id, result, user_input="대화", resolved_path="intent"
            )
        )
        assert any("부족장" in str(e.get("name", "")) for e in state.encounters)
