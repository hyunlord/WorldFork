"""성인식 무기 선택 (★ ep_0002) — scenario 데이터 + equipment build + element + create_session.

방패 고정 해소: 부족장 앞 무기 선택(ep_0002:48 "스스로에게 맞는 무기를 골라라")이
시작 장착 무기 + element(4284fbc)로 이어지는지 검증.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from service.canon.items import build_weapon_equipment
from service.canon.races import Race
from service.canon.scenario import (
    COMING_OF_AGE_WEAPONS,
    DEFAULT_COMING_OF_AGE_WEAPON,
    ScenarioMode,
    _eul_reul,
    build_starting_narrative,
    find_coming_of_age_weapon,
)
from service.persistence.sqlite_store import SqliteStore
from service.sim.equipment import EquipmentSlot
from service.sim.session_manager import SessionManager


def _make_manager(tmp_path: Path) -> SessionManager:
    return SessionManager(SqliteStore(tmp_path / "test.db"))


def test_coming_of_age_weapons_canon() -> None:
    """본문 ep_0002 무기 후보 + 비요른 방패(ep_0003)."""
    names = {w.name for w in COMING_OF_AGE_WEAPONS}
    assert "양손 도끼" in names  # ep_0002:74
    assert "한손 검" in names  # ep_0002:120
    assert "창" in names  # ep_0002:422
    assert "방패" in names  # 비요른 — 그 누구도 고르지 않은 무기
    assert DEFAULT_COMING_OF_AGE_WEAPON == "방패"


def test_find_coming_of_age_weapon() -> None:
    assert find_coming_of_age_weapon("방패") is not None
    assert find_coming_of_age_weapon("없는무기") is None


def test_build_weapon_equipment_physical() -> None:
    """본문 평범 무기 → element 없음(물리)."""
    eq = build_weapon_equipment("양손 도끼", 6, "묵직한 양손 도끼.")
    assert eq.slot == EquipmentSlot.WEAPON
    assert eq.name == "양손 도끼"
    assert eq.attack_bonus == 6
    assert eq.element == ""


def test_build_weapon_equipment_element() -> None:
    """element 무기 → _parse_element 반영 (★ 4284fbc — 화염→불, 냉기→냉기)."""
    assert build_weapon_equipment("화염 검", 5).element == "불"
    assert build_weapon_equipment("냉기 창").element == "냉기"


def test_eul_reul_josa() -> None:
    """목적격 조사 — 받침 有 '을' / 無 '를'."""
    assert _eul_reul("방패") == "를"
    assert _eul_reul("검") == "을"
    assert _eul_reul("도끼") == "를"
    assert _eul_reul("창") == "을"


def test_build_narrative_weapon_dynamic() -> None:
    """선택 무기 narrative 동적 반영 (★ ep_0002)."""
    n = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN, "양손 도끼")
    assert "양손 도끼를" in n
    n2 = build_starting_narrative(ScenarioMode.BJORN, Race.BARBARIAN, None)
    assert "양손 도끼" not in n2  # weapon 미지정 → 무기 문장 없음


def test_create_session_weapon_equipped(tmp_path: Path) -> None:
    """무기 선택 → inventory + equipment.weapon 장착 (★ 방패 고정 해소)."""
    mgr = _make_manager(tmp_path)
    state = asyncio.run(
        mgr.create_session(scenario_mode=ScenarioMode.BJORN, weapon="양손 도끼")
    )
    assert "양손 도끼" in state.inventory
    weapon = state.equipment.get("weapon")
    assert isinstance(weapon, dict)
    assert weapon["name"] == "양손 도끼"
    assert weapon["attack_bonus"] == 6


def test_create_session_default_shield(tmp_path: Path) -> None:
    """무기 미지정(legacy) → scenario 방패 inventory 유지 (회귀 방지)."""
    mgr = _make_manager(tmp_path)
    state = asyncio.run(mgr.create_session(scenario_mode=ScenarioMode.BJORN))
    assert "방패" in state.inventory  # scenario.starting_inventory 유지


def test_match_weapon_in_text() -> None:
    """성인식 무기 선택 — 입력에서 무기명 추출 (게임 엔진 3단계)."""
    from service.sim.weapon_choice import match_weapon_in_text

    assert match_weapon_in_text("양손 도끼를 고른다") == "양손 도끼"
    assert match_weapon_in_text("한손 검을 손에 쥔다") == "한손 검"
    # 긴 이름 우선 — '양손 대검'이 '양손 도끼'와 겹치지 않음
    assert match_weapon_in_text("양손 대검을 고른다") == "양손 대검"
    assert match_weapon_in_text("주변을 둘러본다") is None


def test_make_weapon_equipment_dict() -> None:
    """무기명 → equipment dict (element + attack_bonus, 35a0ef6 정합)."""
    from service.sim.weapon_choice import make_weapon_equipment

    eq = make_weapon_equipment("양손 도끼")
    assert eq["name"] == "양손 도끼"
    assert eq["attack_bonus"] == 6
    assert "element" in eq  # 무기 element (물리는 "")
