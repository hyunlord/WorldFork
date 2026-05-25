"""create_session 종족/시나리오 적용 검증 (phase-e-2)."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from service.canon.races import Race
from service.canon.scenario import ScenarioMode
from service.sim.session_manager import SessionManager


def _make_manager() -> SessionManager:
    store = MagicMock()
    store.save_session = MagicMock(return_value=None)
    store.load_session = MagicMock(return_value=None)
    store.list_sessions = MagicMock(return_value=[])
    mgr = SessionManager(store)
    return mgr


def _run(coro: object) -> object:
    return asyncio.run(coro)  # type: ignore[arg-type]


def test_create_session_bjorn_default_barbarian() -> None:
    """BJORN 기본 — race=BARBARIAN, HP=120, 영혼력=10."""
    mgr = _make_manager()
    state = _run(mgr.create_session())
    assert state.race == "barbarian"
    assert state.current_hp == 120
    assert state.max_hp == 120
    assert state.soul_power == 10
    assert state.max_essences == 1
    assert state.scenario_mode == "bjorn"


def test_create_session_new_explorer_fairy() -> None:
    """NEW_EXPLORER + 요정 — HP=80, 영혼력=20, 슬롯=2."""
    mgr = _make_manager()
    state = _run(mgr.create_session(race=Race.FAIRY, scenario_mode=ScenarioMode.NEW_EXPLORER))
    assert state.race == "fairy"
    assert state.current_hp == 80
    assert state.max_hp == 80
    assert state.soul_power == 20
    assert state.max_essences == 2
    assert state.scenario_mode == "new_explorer"


def test_create_session_bjorn_ignores_user_race() -> None:
    """BJORN — 종족 지정해도 BARBARIAN 고정."""
    mgr = _make_manager()
    state = _run(mgr.create_session(race=Race.FAIRY, scenario_mode=ScenarioMode.BJORN))
    assert state.race == "barbarian"
    assert state.current_hp == 120


def test_create_session_new_explorer_default_human() -> None:
    """NEW_EXPLORER race=None → HUMAN (HP=100)."""
    mgr = _make_manager()
    state = _run(mgr.create_session(scenario_mode=ScenarioMode.NEW_EXPLORER))
    assert state.race == "human"
    assert state.current_hp == 100


def test_create_session_bjorn_location() -> None:
    """BJORN 시작 위치 — 라스카니아 차원광장 포함."""
    mgr = _make_manager()
    state = _run(mgr.create_session())
    assert "라스카니아" in state.location


def test_create_session_custom_location_override() -> None:
    """location 명시 시 시나리오 기본값 무시."""
    mgr = _make_manager()
    state = _run(mgr.create_session(location="테스트 위치"))
    assert state.location == "테스트 위치"


def test_create_session_legacy_hp_override() -> None:
    """legacy current_hp/max_hp 파라미터 — 명시 시 race config 대신 적용."""
    mgr = _make_manager()
    state = _run(mgr.create_session(current_hp=50, max_hp=50))
    assert state.current_hp == 50
    assert state.max_hp == 50
