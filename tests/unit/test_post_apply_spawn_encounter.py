"""서빙 2단계 — _post_apply_spawn 조우 라인 결선 (결정적 통합 테스트).

스폰은 확률적(spawn rate 0.30)이라 브라우저 E2E로는 flaky. 결선 자체는
trigger_spawn을 강제해 결정적으로 검증한다(새 적대 적 → 등장 라인 반환).
"""

from __future__ import annotations

from typing import Any

from service.api import v2_freeform_router as router
from service.sim.session_manager import SessionState


def _state(**over: Any) -> SessionState:
    base = dict(
        session_id="t",
        current_hp=100,
        max_hp=100,
        inventory=[],
        location="던전 1층",
        encounters=[],
        turn_count=5,
        created_at=0.0,
        last_active=0.0,
        last_spawn_turn=-10,
        floor_number=1,
    )
    base.update(over)
    return SessionState(**base)  # type: ignore[arg-type]


def test_hostile_spawn_returns_encounter_line(monkeypatch: Any) -> None:
    enemy = {"name": "뱀파이어", "enemy_type": "undead", "hostile": True}
    monkeypatch.setattr(router, "get_spawn_table", lambda: object())
    monkeypatch.setattr(router, "get_canon_facts", lambda: None)
    monkeypatch.setattr(router, "determine_location_type", lambda *a, **k: "dungeon")
    monkeypatch.setattr(router, "trigger_spawn", lambda **k: [enemy])

    state = _state()
    line = router._post_apply_spawn(state)

    assert line is not None
    assert "뱀파이어" in line  # 등장 서사에 적 이름 (조용한 출현 X)
    assert state.encounters == [enemy]  # state도 갱신


def test_no_spawn_returns_none(monkeypatch: Any) -> None:
    monkeypatch.setattr(router, "get_spawn_table", lambda: object())
    monkeypatch.setattr(router, "get_canon_facts", lambda: None)
    monkeypatch.setattr(router, "determine_location_type", lambda *a, **k: "dungeon")
    monkeypatch.setattr(router, "trigger_spawn", lambda **k: [])

    assert router._post_apply_spawn(_state()) is None


def test_existing_encounters_skip(monkeypatch: Any) -> None:
    # 이미 적이 있으면 재스폰/재연출 안 함
    monkeypatch.setattr(router, "get_spawn_table", lambda: object())
    state = _state(encounters=[{"name": "기존적", "hostile": True}])
    assert router._post_apply_spawn(state) is None
