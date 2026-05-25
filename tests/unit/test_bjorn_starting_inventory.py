"""Phase E-3: 비요른 시작 inventory 본문 정합 테스트."""

from __future__ import annotations

import asyncio
from pathlib import Path

from service.canon.scenario import SCENARIO_CONFIGS, ScenarioMode
from service.persistence.sqlite_store import SqliteStore
from service.sim.session_manager import SessionManager


def test_bjorn_has_starting_inventory() -> None:
    config = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert len(config.starting_inventory) > 0


def test_bjorn_has_weapon() -> None:
    config = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    inv = config.starting_inventory
    weapon_keywords = ["도끼", "검", "방패", "곤봉", "망치"]
    assert any(any(kw in item for kw in weapon_keywords) for item in inv)


def test_bjorn_inventory_contains_shield() -> None:
    """ep_0005: '방패 하나만 달랑 가진 좆밥 바바리안'."""
    config = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert "방패" in config.starting_inventory


def test_bjorn_inventory_no_torch() -> None:
    """ep_0004: 횃불 없이 시작 (wiki 008 탐험 용품은 구매 아이템)."""
    config = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    assert not any("횃불" in item for item in config.starting_inventory)


def test_bjorn_inventory_no_food() -> None:
    """ep_0003 식량은 도시 체류용 — 미궁 진입 시점엔 소지 안 함."""
    config = SCENARIO_CONFIGS[ScenarioMode.BJORN]
    food_kws = ["빵", "식량", "음식"]
    assert not any(kw in item for item in config.starting_inventory for kw in food_kws)


def test_new_explorer_inventory_empty() -> None:
    """NEW_EXPLORER는 commit 4에서 종족별 적용 예정."""
    config = SCENARIO_CONFIGS[ScenarioMode.NEW_EXPLORER]
    assert config.starting_inventory == ()


def test_bjorn_create_session_inventory(tmp_path: Path) -> None:
    """create_session BJORN → inventory = ['방패']."""
    store = SqliteStore(tmp_path / "test.db")
    mgr = SessionManager(store)
    state = asyncio.run(mgr.create_session())
    assert state.inventory == ["방패"]


def test_bjorn_create_session_explicit_inventory_override(tmp_path: Path) -> None:
    """명시적 inventory 전달 시 시나리오 기본값 무시."""
    store = SqliteStore(tmp_path / "test.db")
    mgr = SessionManager(store)
    state = asyncio.run(mgr.create_session(inventory=["도끼", "방패"]))
    assert state.inventory == ["도끼", "방패"]


def test_bjorn_create_session_empty_override(tmp_path: Path) -> None:
    """빈 리스트 명시 시 → 빈 inventory (시나리오 기본값 무시)."""
    store = SqliteStore(tmp_path / "test.db")
    mgr = SessionManager(store)
    state = asyncio.run(mgr.create_session(inventory=[]))
    assert state.inventory == []
