"""audit-2 — rift monster lookup (RiftSubAreaDef.monsters) 단위 테스트."""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import execute_attack

# ─── 픽스처 ───


def _char(name: str = "투르윈", strength: int = 30, physical: int = 10) -> Character:
    return Character(
        name=name,
        race=Race.BARBARIAN,
        level=1,
        hp=150,
        hp_max=150,
        strength=strength,
        physical=physical,
        bone_strength=20,
    )


def _world() -> WorldState:
    return WorldState()


def _rift_location(
    rift_id: str = "bloody_castle",
    rift_sub_area: str = "bc_ch1",
) -> Location:
    return Location(
        realm=Realm.RIFT,
        rift_id=rift_id,
        rift_sub_area=rift_sub_area,
    )


# ─── 테스트 ───


def test_rift_monster_valid() -> None:
    """bc_ch1 데드맨 공격 — 정합 lookup + 처치 성공."""
    char = _char(strength=25, physical=10)  # 합계 35 ≥ 30
    r = execute_attack(char, "데드맨", [char], _world(), current_location=_rift_location())
    assert r.success is True
    assert "데드맨" in r.message
    assert "처치" in r.message


def test_rift_monster_valid_mid_boss() -> None:
    """bc_ch4 시체골렘 공격 — mid_boss_grade=7 정합."""
    char = _char(strength=25, physical=10)
    loc = _rift_location(rift_sub_area="bc_ch4")
    r = execute_attack(char, "시체골렘", [char], _world(), current_location=loc)
    assert r.success is True
    assert "7등급" in r.message


def test_rift_monster_not_in_chamber() -> None:
    """bc_ch1에서 고블린 공격 → 챔버 몬스터 X 실패."""
    char = _char()
    r = execute_attack(char, "고블린", [char], _world(), current_location=_rift_location())
    assert r.success is False
    assert "챔버" in r.message
    assert "외곽 검문소" in r.message


def test_rift_invalid_rift_id() -> None:
    """존재 X rift_id → 균열 정의 없음 실패."""
    loc = Location(realm=Realm.RIFT, rift_id="unknown_rift", rift_sub_area="ch1")
    char = _char()
    r = execute_attack(char, "데드맨", [char], _world(), current_location=loc)
    assert r.success is False
    assert "균열 정의 없음" in r.message


def test_rift_invalid_sub_area() -> None:
    """존재 X rift_sub_area → 챔버 정의 없음 실패."""
    loc = _rift_location(rift_sub_area="bc_ch99")
    char = _char()
    r = execute_attack(char, "데드맨", [char], _world(), current_location=loc)
    assert r.success is False
    assert "챔버 정의 없음" in r.message


def test_dungeon_attack_unaffected() -> None:
    """DUNGEON realm 시 기존 floor1 lookup 유지 — 고블린 정상 처치."""
    char = _char(strength=25, physical=10)
    loc = Location(realm=Realm.DUNGEON, sub_area="진입점")
    r = execute_attack(char, "고블린", [char], _world(), current_location=loc)
    assert r.success is True
    assert "고블린" in r.message


def test_no_location_dungeon_fallback() -> None:
    """current_location=None → 기존 1층 동작 보존."""
    char = _char(strength=25, physical=10)
    r = execute_attack(char, "고블린", [char], _world(), current_location=None)
    assert r.success is True


def test_rift_attack_drop_in_side_effects() -> None:
    """rift 처치 시 마석 드롭 side_effect 정합."""
    char = _char(strength=25, physical=10)
    r = execute_attack(char, "데드맨", [char], _world(), current_location=_rift_location())
    assert any("드롭" in s for s in r.side_effects)
