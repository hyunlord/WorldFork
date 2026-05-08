"""turn_handler_v2 12 ActionType 함수 단위 테스트 (★ 3차 commit)."""

from __future__ import annotations

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    absorb_floating_essence,
    activate_light,
    enter_rift,
    execute_attack,
    exit_rift,
    explore_area,
    flee_from_threat,
    move_to_sub_area,
    offer_to_stone,
    rest,
    send_message_stone,
    use_item,
)


def _bjorn() -> Character:
    return Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=150,
        hp_max=150,
        physical=14,
        strength=16,
        bone_strength=12,
        is_player=True,
    )


def _erwen() -> Character:
    return Character(name="에르웬", race=Race.FAERIE, hp=90, hp_max=90)


# ─── activate_light ───


def test_activate_torch_for_barbarian() -> None:
    c = _bjorn()
    r = activate_light(c, "횃불")
    assert r.success
    assert c.has_active_light()


def test_activate_spirit_for_human_blocked() -> None:
    c = Character(name="X", race=Race.HUMAN)
    r = activate_light(c, "정령 등불")
    assert not r.success


def test_activate_spirit_for_faerie() -> None:
    c = _erwen()
    r = activate_light(c, "정령 등불")
    assert r.success
    assert c.has_active_light()


def test_activate_unknown_source() -> None:
    c = _bjorn()
    r = activate_light(c, "없는 자원")
    assert not r.success


# ─── move ───


def test_move_to_known_area() -> None:
    party = [_bjorn()]
    world = WorldState()
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")

    r = move_to_sub_area(party, world, loc, "북쪽 통로")
    assert r.success


def test_move_to_non_adjacent_blocked() -> None:
    party = [_bjorn()]
    world = WorldState()
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")

    # 진입점.accessible_from = ("북쪽 통로",) → 동쪽 통로 X
    r = move_to_sub_area(party, world, loc, "동쪽 통로")
    assert not r.success


def test_move_to_unknown_area() -> None:
    party = [_bjorn()]
    world = WorldState()
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")

    r = move_to_sub_area(party, world, loc, "없는 영역")
    assert not r.success


# ─── attack ───


def test_attack_kills_goblin() -> None:
    """비요른 strength 16 + physical 14 = 30 → 처치."""
    c = _bjorn()
    r = execute_attack(c, "고블린", [c], WorldState())
    assert r.success


def test_attack_unknown_monster() -> None:
    c = _bjorn()
    r = execute_attack(c, "없는 몬스터", [c], WorldState())
    assert not r.success


def test_attack_weak_attacker_takes_damage() -> None:
    """약한 공격자 — 처치 X + 피해."""
    c = Character(
        name="X",
        race=Race.HUMAN,
        hp=100,
        hp_max=100,
        physical=5,
        strength=5,
        bone_strength=4,
    )
    r = execute_attack(c, "고블린", [c], WorldState())
    assert not r.success
    assert c.hp < 100


# ─── absorb_essence ───


def test_absorb_known_essence() -> None:
    c = _bjorn()
    r = absorb_floating_essence(c, "고블린 정수")
    assert r.success
    assert c.essence_slots_used() == 1


def test_absorb_unknown_essence() -> None:
    c = _bjorn()
    r = absorb_floating_essence(c, "없는 정수")
    assert not r.success


# ─── rest / explore / message / flee ───


def test_rest_advances_4h() -> None:
    party = [_bjorn()]
    world = WorldState()
    r = rest(party, world)
    assert r.success
    assert world.hours_in_dungeon == 4


def test_explore_advances_time() -> None:
    party = [_bjorn()]
    world = WorldState()
    r = explore_area(party, world)
    assert r.success


def test_send_message_stone() -> None:
    sender = _bjorn()
    r = send_message_stone(sender, "에르웬", "도와줘")
    assert r.success
    assert "300m" in str(r.side_effects)


def test_flee_advances_time() -> None:
    party = [_bjorn()]
    world = WorldState()
    r = flee_from_threat(party, world, "약탈자")
    assert r.success


# ─── offer / enter / exit rift ───


def test_offer_to_stone_known_rift() -> None:
    c = _bjorn()
    world = WorldState()
    r = offer_to_stone(c, "green_mine", world)
    assert r.success
    assert "green_mine" in world.active_rifts


def test_offer_to_stone_unknown_rift() -> None:
    c = _bjorn()
    world = WorldState()
    r = offer_to_stone(c, "없는_균열", world)
    assert not r.success


def test_enter_rift_after_offer() -> None:
    c = _bjorn()
    world = WorldState()
    offer_to_stone(c, "green_mine", world)

    r = enter_rift([c], world, "green_mine")
    assert r.success


def test_enter_rift_without_offer_blocked() -> None:
    world = WorldState()
    r = enter_rift([_bjorn()], world, "green_mine")
    assert not r.success


def test_exit_rift_removes_from_active() -> None:
    c = _bjorn()
    world = WorldState()
    offer_to_stone(c, "green_mine", world)
    enter_rift([c], world, "green_mine")

    r = exit_rift([c], world, "green_mine")
    assert r.success
    assert "green_mine" not in world.active_rifts


# ─── use_item ───


def test_use_item_basic() -> None:
    c = _bjorn()
    r = use_item(c, "마도구")
    assert r.success
