"""Stage 7 — Mechanical 검증 (★ 0 토큰 게이트).

본인 본질 (★ Stage 7, 2026-05-08):
- HP 0 → 사망 (★ Character.is_alive)
- 정수 흡수 가능/불가 (★ 슬롯 + 중복)
- 빛 자원 동적 상태 (★ 1층 어둠 본질)
- 현상금 동적 추가/처리 (★ PvP 진행)
- 종족 base 수치 (★ 바바리안 210cm vs 인간 170cm)
"""

from __future__ import annotations

from service.game.state_v2 import (
    BountyEntry,
    BountyKillCondition,
    Character,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    LightStateOnCharacter,
    Race,
    Skill,
    SkillType,
    WorldState,
)


def _make_essence(name: str, active_skill_name: str = "찌르기") -> Essence:
    return Essence(
        name=name,
        grade=EssenceGrade.GRADE_1,
        color=EssenceColor.RED,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source=name,
        active_skills=(
            Skill(
                name=active_skill_name,
                type=SkillType.ACTIVE,
                description="테스트 스킬",
            ),
        ),
        passive_skills=(),
    )


# ─── HP / 사망 ───


def test_character_alive_when_hp_positive() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    assert c.is_alive()


def test_character_dead_when_hp_zero() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.hp = 0
    assert not c.is_alive()


def test_character_dead_when_hp_negative() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.hp = -50
    assert not c.is_alive()


# ─── 정수 흡수 ───


def test_can_absorb_essence_when_slot_empty() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    e = _make_essence("고블린 정수")
    assert c.can_absorb_essence(e)
    assert c.absorb_essence(e)
    assert c.essence_slots_used() == 1


def test_cannot_absorb_when_slots_full() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    for i in range(5):
        assert c.absorb_essence(_make_essence(f"e{i}", f"스킬{i}"))
    assert c.essence_slots_used() == 5
    extra = _make_essence("추가", "추가스킬")
    assert not c.can_absorb_essence(extra)
    assert not c.absorb_essence(extra)


def test_cannot_absorb_duplicate_active_skill() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.absorb_essence(_make_essence("a", "찌르기"))
    dup = _make_essence("b", "찌르기")
    assert not c.can_absorb_essence(dup)


def test_layer_lord_essence_separate_slot() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    for i in range(5):
        assert c.absorb_essence(_make_essence(f"e{i}", f"스킬{i}"))
    # 일반 5칸 다 찼지만 계층군주는 별도
    layer_lord = Essence(
        name="계층군주 정수",
        grade=EssenceGrade.LAYER_LORD,
        color=EssenceColor.RAINBOW,
        essence_type=EssenceType.MAGE,
        origin=EssenceOrigin.LAYER_LORD_KILL,
        monster_source="계층군주",
        active_skills=(),
        passive_skills=(),
        is_layer_lord=True,
    )
    assert c.can_absorb_essence(layer_lord)
    assert c.absorb_essence(layer_lord)
    assert c.layer_lord_essence is not None


# ─── 빛 자원 동적 상태 ───


def test_no_active_light_by_default() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    assert not c.has_active_light()


def test_active_light_when_torch_lit() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=72.0,
    )
    assert c.has_active_light()


def test_no_active_light_when_duration_zero() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.light_state = LightStateOnCharacter(
        active_source_name="횃불",
        remaining_duration_hours=0.0,
    )
    assert not c.has_active_light()


def test_no_active_light_when_source_none() -> None:
    c = Character(name="에르웬", race=Race.FAERIE)
    c.light_state = LightStateOnCharacter(
        active_source_name=None,
        remaining_duration_hours=10.0,
    )
    assert not c.has_active_light()


def test_light_consumables_track_count() -> None:
    c = Character(name="비요른", race=Race.BARBARIAN)
    c.light_state = LightStateOnCharacter(consumables={"조명탄": 3})
    assert c.light_state.consumables["조명탄"] == 3


# ─── 현상금 동적 ───


def test_world_state_starts_with_no_bounties() -> None:
    ws = WorldState()
    assert ws.active_bounties == []


def test_bounty_dynamic_add() -> None:
    ws = WorldState()
    b = BountyEntry(
        target_name="비요른",
        amount_stones=10000,
        issuer_name="수정 연합",
        issuer_faction="수정 연합",
        kill_condition=BountyKillCondition.DEAD_OR_ALIVE,
        reason="정수 강탈 거부",
    )
    ws.active_bounties.append(b)
    assert len(ws.active_bounties) == 1
    assert ws.active_bounties[0].amount_stones == 10000


def test_bounty_kill_condition_variants() -> None:
    capture = BountyEntry(
        target_name="X",
        amount_stones=20000,
        issuer_name="Y",
        kill_condition=BountyKillCondition.CAPTURE_ONLY,
    )
    kill = BountyEntry(
        target_name="X",
        amount_stones=20000,
        issuer_name="Y",
        kill_condition=BountyKillCondition.KILL_ONLY,
    )
    assert capture.kill_condition == BountyKillCondition.CAPTURE_ONLY
    assert kill.kill_condition == BountyKillCondition.KILL_ONLY


# ─── 종족 base ───


def test_human_base_height() -> None:
    c = Character(name="X", race=Race.HUMAN)
    assert c.height == 170  # ★ default


def test_essence_slot_max_human_5() -> None:
    c = Character(name="X", race=Race.HUMAN)
    assert c.essence_slot_max() == 5
