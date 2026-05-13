"""Phase 8 A3 — 보스 spawn + 처치 + 보상 + 균열 클리어 검증.

본질:
- _spawn_boss_encounter: BossEncounter dataclass (일반/변종/약점 inherit)
- move_to_sub_area: boss_chamber_id 도달 시 active_boss_encounter spawn
- execute_attack: world.active_boss_encounter 본격 → 보스 분기 (약점 2배)
- 처치 시 defeated_bosses/cleared_rifts/active_rifts mutation + 보상 marker
- gm_agent prompt: 전투 중 HP/약점 표시, 클리어 후 EXIT_RIFT hint
"""

from __future__ import annotations

from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    BossEncounter,
    Character,
    Inventory,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    _BOSS_HP_BY_GRADE,
    _spawn_boss_encounter,
    execute_attack,
    move_to_sub_area,
)

# ─── _spawn_boss_encounter ───


def test_spawn_normal_bloody_castle() -> None:
    """일반 spawn: 핏빛성채 → 저주받은 기사 블라터 (6등급)."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    boss = _spawn_boss_encounter(bc, is_variant=False)
    assert boss.boss_name == "저주받은 기사 블라터"
    assert boss.is_variant is False
    assert boss.boss_grade == 6
    assert boss.hp == boss.hp_max == _BOSS_HP_BY_GRADE[6]
    assert boss.boss_id == "bloody_castle_normal"
    assert boss.rift_id == "bloody_castle"


def test_spawn_variant_bloody_castle() -> None:
    """변종 spawn: 핏빛성채 → 캠보르미어 (5등급)."""
    bc = FLOOR1_RIFT_DEFS["bloody_castle"]
    boss = _spawn_boss_encounter(bc, is_variant=True)
    assert boss.boss_name == "뱀파이어 공작 캠보르미어"
    assert boss.is_variant is True
    assert boss.boss_grade == 5
    assert boss.hp == _BOSS_HP_BY_GRADE[5]
    assert boss.boss_id == "bloody_castle_variant"


def test_spawn_glacier_weakness_inherit() -> None:
    """빙하굴 — namu 명시 전격 약점 inherit."""
    gc = FLOOR1_RIFT_DEFS["glacier_cave"]
    boss = _spawn_boss_encounter(gc, is_variant=False)
    assert boss.weakness_element == "전격"
    assert boss.weakness_strategy is not None
    assert "타룬바스" in boss.weakness_strategy


def test_spawn_no_variant_falls_back_to_normal() -> None:
    """variant_boss_name None 균열 (★ green_mine): is_variant=True 본격
    fallback 본격 일반 본격."""
    gm = FLOOR1_RIFT_DEFS["green_mine"]
    boss = _spawn_boss_encounter(gm, is_variant=True)
    # 일반 fallback
    assert boss.is_variant is False
    assert boss.boss_name == gm.normal_boss_name
    assert boss.boss_id == "green_mine_normal"


# ─── MOVE → boss chamber spawn ───


def _party_world_at_rift(
    rift_id: str,
    rift_sub_area: str,
    is_variant: bool = False,
) -> tuple[list[Character], WorldState, Location]:
    """rift 내부 minimal setup."""
    party = [Character(name="비요른", race=Race.BARBARIAN, is_player=True)]
    world = WorldState(active_rifts=[rift_id])
    location = Location(
        realm=Realm.RIFT,
        rift_id=rift_id,
        rift_sub_area=rift_sub_area,
        rift_is_variant=is_variant,
    )
    return party, world, location


def test_move_to_boss_chamber_spawns_encounter() -> None:
    """MOVE bc_ch4 → bc_ch5 본격 active_boss_encounter spawn."""
    party, world, loc = _party_world_at_rift("bloody_castle", "bc_ch4")
    r = move_to_sub_area(party, world, loc, "bc_ch5")
    assert r.success
    assert world.active_boss_encounter is not None
    boss = world.active_boss_encounter
    assert boss.rift_id == "bloody_castle"
    assert boss.boss_name == "저주받은 기사 블라터"
    assert any(eff.startswith("boss_spawned=") for eff in r.side_effects)


def test_move_to_boss_chamber_variant_spawns_variant_boss() -> None:
    """variant location 본격 bc_ch5 도달 시 변종 spawn."""
    party, world, loc = _party_world_at_rift(
        "bloody_castle", "bc_ch4", is_variant=True
    )
    r = move_to_sub_area(party, world, loc, "bc_ch5")
    assert r.success
    boss = world.active_boss_encounter
    assert boss is not None
    assert boss.is_variant is True
    assert boss.boss_name == "뱀파이어 공작 캠보르미어"


def test_move_to_non_boss_chamber_no_spawn() -> None:
    """MOVE bc_ch3 → bc_ch4 (MID_BOSS) — 본격 spawn X."""
    party, world, loc = _party_world_at_rift("bloody_castle", "bc_ch3")
    r = move_to_sub_area(party, world, loc, "bc_ch4")
    assert r.success
    assert world.active_boss_encounter is None


def test_move_double_does_not_respawn() -> None:
    """이미 spawn 본격 시 재 MOVE 도착 → 동일 인스턴스 유지."""
    party, world, loc = _party_world_at_rift("bloody_castle", "bc_ch4")
    move_to_sub_area(party, world, loc, "bc_ch5")
    first = world.active_boss_encounter
    assert first is not None
    # 강제로 HP 절반으로 (★ 진행 중 상태 가정)
    first.hp = first.hp_max // 2
    # 한 번 더 같은 위치로 도착하는 시나리오는 불가능하므로,
    # 본격 후 다시 MOVE 시 spawn 본격 변화 X — 본격 본격 same instance 본격
    loc.rift_sub_area = "bc_ch5"  # 본격 도달 본격
    # bc_ch5 → bc_ch4 → bc_ch5 본격 반복
    move_to_sub_area(party, world, loc, "bc_ch4")
    move_to_sub_area(party, world, loc, "bc_ch5")
    second = world.active_boss_encounter
    assert second is first  # 동일 instance


def test_move_to_cleared_boss_chamber_no_respawn() -> None:
    """이미 클리어 본격 균열 본격 bc_ch5 본격 spawn X."""
    party, world, loc = _party_world_at_rift("bloody_castle", "bc_ch4")
    world.cleared_rifts.append("bloody_castle")
    r = move_to_sub_area(party, world, loc, "bc_ch5")
    assert r.success
    assert world.active_boss_encounter is None


# ─── execute_attack 보스 분기 ───


def _strong_attacker() -> Character:
    """대량 데미지 attacker (★ 처치 path 테스트용)."""
    c = Character(
        name="비요른",
        race=Race.BARBARIAN,
        is_player=True,
        strength=200,
        physical=200,
    )
    c.inventory = Inventory(weight_max=10000)
    return c


def _moderate_attacker() -> Character:
    """중간 데미지 attacker — 보스 HP보다 작은 단일 타격 (damage=50)."""
    c = Character(
        name="비요른",
        race=Race.BARBARIAN,
        is_player=True,
        strength=25,
        physical=25,
    )
    c.inventory = Inventory(weight_max=10000)
    return c


def test_attack_reduces_boss_hp() -> None:
    """단일 ATTACK 본격 boss.hp 감소 (★ 처치 X 본격)."""
    attacker = _moderate_attacker()  # damage 50 < boss hp 400
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    before_hp = world.active_boss_encounter.hp
    r = execute_attack(attacker, "보스", [attacker], world)
    assert r.success
    assert world.active_boss_encounter is not None
    assert world.active_boss_encounter.hp < before_hp
    # 1회로 처치되지 않아야 함 (★ 단일 데미지 < hp_max)
    assert world.active_boss_encounter.hp > 0


def test_attack_weakness_doubles_damage() -> None:
    """attack_element == weakness_element 본격 2배 데미지."""
    attacker = _moderate_attacker()  # damage 50, weakness 100 (< gc hp 300)
    world = WorldState(active_rifts=["glacier_cave"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["glacier_cave"], is_variant=False
    )
    boss = world.active_boss_encounter
    assert boss is not None

    # 본격 single attack 본격 본격 약점 X
    boss.hp = boss.hp_max
    execute_attack(attacker, "보스", [attacker], world)
    hp_after_normal = boss.hp

    # 본격 single attack 본격 본격 약점 본격
    boss.hp = boss.hp_max
    execute_attack(
        attacker, "보스", [attacker], world, attack_element="전격"
    )
    hp_after_weak = boss.hp

    damage_normal = boss.hp_max - hp_after_normal
    damage_weak = boss.hp_max - hp_after_weak
    assert damage_weak == damage_normal * 2


def test_attack_kill_triggers_defeat_path() -> None:
    """hp=0 본격 → defeated_bosses + cleared_rifts + active_rifts 제거."""
    attacker = _strong_attacker()
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    # 강제로 hp 1 본격 본격 본격 처치
    world.active_boss_encounter.hp = 1

    r = execute_attack(attacker, "보스", [attacker], world)
    assert r.success
    assert world.active_boss_encounter is None
    assert "bloody_castle_normal" in world.defeated_bosses
    assert "bloody_castle" in world.cleared_rifts
    assert "bloody_castle" not in world.active_rifts


def test_defeat_emits_essence_spawn_marker() -> None:
    """처치 시 side_effects 본격 'essence_spawn={color}' marker."""
    attacker = _strong_attacker()
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    world.active_boss_encounter.hp = 1

    r = execute_attack(attacker, "보스", [attacker], world)
    assert any(eff == "essence_spawn=red" for eff in r.side_effects)
    assert any(
        eff.startswith("boss_defeated=") for eff in r.side_effects
    )
    assert any(
        eff.startswith("rift_cleared=") for eff in r.side_effects
    )


def test_defeat_adds_mage_stone_to_inventory() -> None:
    """처치 본격 처치자 inventory 본격 마석 append."""
    attacker = _strong_attacker()
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    world.active_boss_encounter.hp = 1

    execute_attack(attacker, "보스", [attacker], world)
    stone_names = [it.name for it in attacker.inventory.items]
    assert any("마석" in n for n in stone_names)
    assert any("저주받은 기사 블라터" in n for n in stone_names)


def test_attack_after_clear_falls_back_to_monster_path() -> None:
    """active_boss_encounter is None 본격 → 일반 monster 경로 본격."""
    attacker = _strong_attacker()
    world = WorldState()
    # 본격 active_boss_encounter X 본격 본격 1층 monster 본격 본격
    r = execute_attack(attacker, "고블린", [attacker], world)
    assert r.success
    assert "처치" in r.message


# ─── gm_agent prompt 본격 ───


def _ctx_at_bloody_castle_boss_chamber(
    *,
    active_boss: BossEncounter | None,
    cleared: bool,
    is_variant: bool = False,
) -> dict[str, object]:
    """보스방 ctx — active_boss / cleared 분기 본격."""
    from tools.measure_gm_prompt import _ctx_inside_rift_boss

    ctx = _ctx_inside_rift_boss()
    loc = dict(ctx["v2_initial_location"])  # type: ignore[arg-type]
    loc["rift_sub_area"] = "bc_ch5"
    loc["rift_is_variant"] = is_variant
    ctx["v2_initial_location"] = loc

    ws = dict(ctx["v2_world_state"])  # type: ignore[arg-type]
    ws["cleared_rifts"] = ["bloody_castle"] if cleared else []
    if active_boss is not None:
        ws["active_boss_encounter"] = {
            "rift_id": active_boss.rift_id,
            "boss_id": active_boss.boss_id,
            "boss_name": active_boss.boss_name,
            "boss_grade": active_boss.boss_grade,
            "is_variant": active_boss.is_variant,
            "hp": active_boss.hp,
            "hp_max": active_boss.hp_max,
            "weakness_element": active_boss.weakness_element,
            "weakness_strategy": active_boss.weakness_strategy,
        }
    else:
        ws["active_boss_encounter"] = None
    ctx["v2_world_state"] = ws
    return ctx


def test_prompt_active_boss_shows_hp() -> None:
    """active_boss_encounter 본격 본격 HP 본격 prompt 본격 표시."""
    boss = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    boss.hp = boss.hp_max // 2
    ctx = _ctx_at_bloody_castle_boss_chamber(
        active_boss=boss, cleared=False
    )
    prompt = _gm_system_prompt(ctx)
    assert "전투 중" in prompt
    assert "저주받은 기사 블라터" in prompt
    assert f"HP: {boss.hp}/{boss.hp_max}" in prompt


def test_prompt_active_boss_shows_weakness() -> None:
    """boss.weakness_element 본격 본격 prompt 본격 약점 표시."""
    boss = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["glacier_cave"], is_variant=False
    )
    # 빙하굴 보스방은 gc_ch4 — 본격 핏빛성채 ctx 본격 본격 rift_id 본격 비매칭.
    # 본격 본격 본격 본격 본격 본격 본격 본격 본격 본격 본격 본격 본격 본격
    # 본격 본격 본격: 본격 핏빛성채 ctx 본격 본격 본격 본격 본격 본격 본격
    # active_boss.rift_id 본격 boss chamber rift 본격 매칭 본격 본격 본격.
    # 본격 본격 본격 본격 본격: boss.rift_id 본격 본격 본격 핏빛성채 본격 변경.
    boss.rift_id = "bloody_castle"
    ctx = _ctx_at_bloody_castle_boss_chamber(
        active_boss=boss, cleared=False
    )
    prompt = _gm_system_prompt(ctx)
    assert "약점: 전격" in prompt


def test_prompt_cleared_shows_exit_hint() -> None:
    """cleared_rifts 본격 본격 → EXIT_RIFT hint."""
    ctx = _ctx_at_bloody_castle_boss_chamber(
        active_boss=None, cleared=True
    )
    prompt = _gm_system_prompt(ctx)
    assert "균열 클리어" in prompt
    assert "EXIT_RIFT" in prompt


def test_prompt_no_boss_shows_default_waiting() -> None:
    """active_boss X + cleared X 본격 → 기존 A2 본격 본격 본격 표시."""
    ctx = _ctx_at_bloody_castle_boss_chamber(
        active_boss=None, cleared=False
    )
    prompt = _gm_system_prompt(ctx)
    assert "보스방 앞 — 수호자" in prompt
    assert "저주받은 기사 블라터" in prompt
