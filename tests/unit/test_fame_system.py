"""Phase 9.14 fame-system — 명성 + 초면 NPC 호감도 bonus.

검증 본질:
- Character.fame default 0 + 명시 설정
- FAME_GAIN_BOSS_DEFEAT = 10 / FAME_GAIN_RIFT_CLEAR = 5
- FAME_PER_AFFINITY_BONUS = 10
- Producer (★ _defeat_boss 본격 보스+균열 동시 site):
  * 파티 전원 fame += 15 (★ 10 + 5)
  * 죽은 멤버 영구 (★ fame X)
  * side_effect: fame_gain
- Consumer (★ execute_dialogue):
  * 초면 (★ npc_affinities dict key X) → starting = fame // 10
  * 재만남 → fame bonus X (★ 9.7 정합 유지)
  * AFFINITY_MAX cap 적용
  * 메시지 본격 명성 표시
- sim_runner ctx serialize: fame
- gm_agent prompt 본격 '명성 N' 표시

본문 정합:
- 452화: 명성 → 초면 NPC 기본 호감도 ↑
- 74-79화: 비요른 '작은 발칸' 명성 호칭

추측 (본문 X — docstring 명시):
- +10/+5 수치
- // 10 공식
"""

from __future__ import annotations

from typing import Any

from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS
from service.game.gm_agent import _gm_system_prompt
from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.game.turn_handler_v2 import (
    AFFINITY_DELTA_DIALOGUE,
    AFFINITY_MAX,
    FAME_GAIN_BOSS_DEFEAT,
    FAME_GAIN_RIFT_CLEAR,
    FAME_PER_AFFINITY_BONUS,
    _spawn_boss_encounter,
    execute_attack,
    execute_dialogue,
)
from service.sim.sim_runner import _refresh_context

# ─── 1. Character.fame field ───


def test_character_fame_default_0() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    assert c.fame == 0


def test_character_fame_explicit() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN, fame=50)
    assert c.fame == 50


# ─── 2. constants ───


def test_fame_constants() -> None:
    assert FAME_GAIN_BOSS_DEFEAT == 10
    assert FAME_GAIN_RIFT_CLEAR == 5
    assert FAME_PER_AFFINITY_BONUS == 10


# ─── 3. Producer — _defeat_boss 본격 fame ↑ ───


def _strong_attacker() -> Character:
    return Character(
        name="투르윈",
        race=Race.BARBARIAN,
        hp=200,
        hp_max=200,
        physical=100,
        strength=600,
        is_player=True,
    )


def _boss_world() -> WorldState:
    world = WorldState(active_rifts=["bloody_castle"])
    world.active_boss_encounter = _spawn_boss_encounter(
        FLOOR1_RIFT_DEFS["bloody_castle"], is_variant=False
    )
    world.active_boss_encounter.hp = 1
    return world


def test_boss_defeat_grants_fame_15_to_attacker() -> None:
    """attacker(=party 단독) 본격 보스+균열 = +15 fame."""
    attacker = _strong_attacker()
    world = _boss_world()
    pre = attacker.fame
    execute_attack(attacker, "보스", [attacker], world)
    assert attacker.fame == pre + (
        FAME_GAIN_BOSS_DEFEAT + FAME_GAIN_RIFT_CLEAR
    )


def test_boss_defeat_party_all_get_fame() -> None:
    """파티 전원 fame 공유 (★ 살아있는 멤버)."""
    attacker = _strong_attacker()
    ally = Character(name="에르웬", race=Race.FAERIE, hp=80, hp_max=80)
    world = _boss_world()
    execute_attack(attacker, "보스", [attacker, ally], world)
    assert attacker.fame == 15
    assert ally.fame == 15


def test_boss_defeat_dead_member_no_fame() -> None:
    """죽은 멤버 영구 — fame X (★ 본인 답 정합)."""
    attacker = _strong_attacker()
    dead = Character(name="시신", race=Race.HUMAN, hp=0, hp_max=100)
    world = _boss_world()
    execute_attack(attacker, "보스", [attacker, dead], world)
    assert attacker.fame == 15
    assert dead.fame == 0


def test_boss_defeat_side_effect_fame_gain() -> None:
    attacker = _strong_attacker()
    world = _boss_world()
    result = execute_attack(attacker, "보스", [attacker], world)
    assert any(
        s == "fame_gain=투르윈:+15_boss_rift"
        for s in result.side_effects
    )


# ─── 4. Consumer — execute_dialogue 초면 fame bonus ───


def _plaza_loc() -> Location:
    return Location(
        realm=Realm.CITY,
        floor=0,
        sub_area="district_7_plaza",
        city_id="rascania",
    )


def _bjorn(fame: int = 0) -> Character:
    return Character(
        name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, fame=fame
    )


def test_first_meet_no_fame_baseline() -> None:
    """fame=0 → 초면 시작 0, +5 → 5 (★ 9.7 baseline)."""
    world = WorldState()
    actor = _bjorn(fame=0)
    result = execute_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert result.success is True
    assert world.npc_affinities["aenar"] == AFFINITY_DELTA_DIALOGUE


def test_first_meet_with_fame_50_bonus_5() -> None:
    """fame=50 → bonus 5 → 시작 5, +5 → 10."""
    world = WorldState()
    actor = _bjorn(fame=50)
    execute_dialogue("비요른", "카이라", [actor], world, _plaza_loc())
    assert world.npc_affinities["aenar"] == 10


def test_first_meet_with_fame_30_bonus_3() -> None:
    """fame=30 → bonus 3 → 시작 3, +5 → 8."""
    world = WorldState()
    actor = _bjorn(fame=30)
    execute_dialogue("비요른", "카이라", [actor], world, _plaza_loc())
    assert world.npc_affinities["aenar"] == 8


def test_repeat_meet_no_fame_bonus() -> None:
    """재만남 — fame bonus X (★ 9.7 호환 유지)."""
    world = WorldState()
    world.npc_affinities["aenar"] = 20  # ★ 이미 만남
    actor = _bjorn(fame=100)
    execute_dialogue("비요른", "카이라", [actor], world, _plaza_loc())
    # 재만남: 20 + 5 = 25 (★ fame 100 영향 X)
    assert world.npc_affinities["aenar"] == 25


def test_first_meet_fame_bonus_caps_at_max() -> None:
    """fame=1000 → bonus 100 → 시작 100, +5 → cap 100."""
    world = WorldState()
    actor = _bjorn(fame=1000)
    execute_dialogue("비요른", "카이라", [actor], world, _plaza_loc())
    assert world.npc_affinities["aenar"] == AFFINITY_MAX


def test_first_meet_message_shows_fame_bonus() -> None:
    world = WorldState()
    actor = _bjorn(fame=30)
    result = execute_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert "명성 30" in result.message
    assert "+3" in result.message


def test_first_meet_fame_0_no_bonus_message() -> None:
    """fame=0 → bonus 0 → 명성 표시 X (★ 메시지 정합)."""
    world = WorldState()
    actor = _bjorn(fame=0)
    result = execute_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert "명성" not in result.message


def test_repeat_meet_no_fame_message() -> None:
    """재만남 → fame 메시지 X."""
    world = WorldState()
    world.npc_affinities["aenar"] = 10
    actor = _bjorn(fame=100)
    result = execute_dialogue(
        "비요른", "카이라", [actor], world, _plaza_loc()
    )
    assert "명성" not in result.message


# ─── 5. sim_runner ctx serialize ───


def test_refresh_context_serializes_fame() -> None:
    party = {
        "비요른": Character(
            name="비요른", race=Race.BARBARIAN, hp=100, hp_max=100, fame=42
        ),
    }
    world = WorldState(party_members=["비요른"])
    loc = Location(realm=Realm.DUNGEON, floor=1, sub_area="진입점")
    base_ctx: dict[str, Any] = {
        "main_character_name": "비요른",
        "current_turn": 0,
    }
    ctx = _refresh_context(party, world, loc, base_ctx, [])
    assert ctx["v2_characters"]["비요른"]["fame"] == 42


# ─── 6. gm_agent prompt 본격 명성 표시 ───


def _base_ctx() -> dict[str, Any]:
    return {
        "work_name": "1층",
        "work_genre": "판타지",
        "world_setting": "라스카니아",
        "world_tone": "차분",
        "world_rules": ["1층 어둠"],
        "main_character_name": "비요른",
        "main_character_role": "주인공",
        "supporting_characters": [],
        "current_location": "1층",
        "current_turn": 0,
    }


def test_prompt_shows_fame() -> None:
    ctx = _base_ctx()
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
            "grade": 1,
            "class_type": "warrior",
            "fame": 25,
        },
    }
    prompt = _gm_system_prompt(ctx)
    assert "명성 25" in prompt


def test_prompt_fame_default_0() -> None:
    """fame key 없는 ctx → default 0 표시."""
    ctx = _base_ctx()
    ctx["v2_characters"] = {
        "비요른": {
            "race": "바바리안",
            "hp": 100,
            "hp_max": 100,
            "level": 1,
            "experience": 0,
            "physical": 14,
            "strength": 16,
            "grade": 1,
            "class_type": "warrior",
        },
    }
    prompt = _gm_system_prompt(ctx)
    assert "명성 0" in prompt
