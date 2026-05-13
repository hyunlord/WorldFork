"""Tier 2 D12 — game-loop turn handler.

Stage 7 schema 진짜 production mutate (★ 본 commit 3차 — 12 ActionType 본격):
- Character.light_state (빛 자원 활성/소진/회복/consumables)
- Character.has_active_light (호출)
- Character.absorb_essence (호출)
- Character.is_alive / hp (HP 변동)
- WorldState.active_rifts / hours_in_dungeon

본 모듈은 LLM 호출 X — Mechanical mutate만.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from .floors.floor1 import FLOOR_TWO_PORTAL_SUB_AREAS, get_floor1_definition
from .floors.floor1_rifts import FLOOR1_RIFT_DEFS, decide_variant
from .state_v2 import (
    BossEncounter,
    Character,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    Item,
    ItemCategory,
    Location,
    Realm,
    RiftDef,
    RiftSubAreaDef,
    SimulationStatus,
    WorldState,
    level_for_exp,
)

# ★ Phase 8 A4 — 1층 시간 한도. 본문 1차 자료: 7일 (168h).
TIME_LIMIT_HOURS: int = 168

# ★ Phase 8 B — 등급별 base exp (★ 9 = 1층 본격 본격, 0 = 계층군주).
# 본인 #19: 1차 자료 명시 X → 추측. balance commit 본격 정정 가능.
# threshold table (★ state_v2.LEVEL_EXP_THRESHOLDS) 본격 정합:
# - 9등급 2회 = 100 exp = level 2 (★ "딱 한번" mechanism 본격 spread 본격 본격)
# - 5등급 변종 보스 1회 = 800 exp = level 4
MONSTER_EXP_BY_GRADE: dict[int, int] = {
    9: 50,
    8: 100,
    7: 200,
    6: 400,
    5: 800,
    4: 1600,
    3: 3200,
    2: 6400,
    1: 12800,
    0: 25600,  # 계층군주
}

# ★ Phase 8 A3 — boss grade → 기본 HP (★ 5등급=600, 8등급=200; spec X 시 추측,
# 후속 balance commit에서 본문 정합 본격 조정).
_BOSS_HP_BY_GRADE: dict[int, int] = {
    5: 600,
    6: 400,
    7: 300,
    8: 200,
    9: 150,
}


def _spawn_boss_encounter(
    rift_def: RiftDef,
    is_variant: bool,
) -> BossEncounter:
    """boss_chamber 도달 시 spawn (★ Phase 8 A3).

    is_variant True + variant_boss_name 정의 시 변종, 아니면 일반.
    A1의 BossWeakness 본격 inherit.
    """
    if is_variant and rift_def.variant_boss_name is not None:
        boss_name = rift_def.variant_boss_name
        boss_grade = rift_def.variant_boss_grade or rift_def.normal_boss_grade
        boss_id = f"{rift_def.rift_id}_variant"
        variant_flag = True
    else:
        boss_name = rift_def.normal_boss_name
        boss_grade = rift_def.normal_boss_grade
        boss_id = f"{rift_def.rift_id}_normal"
        variant_flag = False

    base_hp = _BOSS_HP_BY_GRADE.get(boss_grade, 200)

    weakness_element: str | None = None
    weakness_strategy: str | None = None
    if rift_def.boss_weakness is not None:
        weakness_element = rift_def.boss_weakness.element
        weakness_strategy = rift_def.boss_weakness.note or None

    return BossEncounter(
        rift_id=rift_def.rift_id,
        boss_id=boss_id,
        boss_name=boss_name,
        boss_grade=boss_grade,
        is_variant=variant_flag,
        hp=base_hp,
        hp_max=base_hp,
        weakness_element=weakness_element,
        weakness_strategy=weakness_strategy,
    )


@dataclass
class TurnResult:
    """Turn 처리 결과."""

    success: bool
    action_type: str
    message: str
    side_effects: list[str] = field(default_factory=list)


# ─── 1. WAIT / 시간 흐름 ───


def advance_time(
    characters: list[Character],
    world: WorldState,
    elapsed_hours: float,
) -> TurnResult:
    """시간 흐름 — 빛 자원 차감 + cooldown 회복 + 미궁 시간 누적.

    - light_state.remaining_duration_hours 차감
    - 정령 자원 소진 시 cooldown 2h 진입 (★ 11화)
    - 사망자는 처리 X
    """
    side: list[str] = []

    for c in characters:
        if not c.is_alive():
            continue

        ls = c.light_state

        # 기존 cooldown 먼저 차감 (신규 cooldown 진입 분리)
        if ls.cooldown_remaining_hours > 0:
            ls.cooldown_remaining_hours = max(
                0.0, ls.cooldown_remaining_hours - elapsed_hours
            )
            if ls.cooldown_remaining_hours == 0.0:
                side.append(f"{c.name}의 정령 회복 완료.")

        if ls.active_source_name and ls.remaining_duration_hours > 0:
            ls.remaining_duration_hours = max(
                0.0, ls.remaining_duration_hours - elapsed_hours
            )
            if ls.remaining_duration_hours == 0.0:
                spent = ls.active_source_name
                ls.active_source_name = None
                if "정령" in spent:
                    ls.cooldown_remaining_hours = 2.0  # ★ 11화
                side.append(f"{c.name}의 {spent} 소진.")

    world.hours_in_dungeon += int(elapsed_hours)

    return TurnResult(
        success=True,
        action_type="wait",
        message=f"{elapsed_hours}시간 경과.",
        side_effects=side,
    )


# ─── 2. 빛 활성 ───


def activate_light(
    character: Character,
    source_name: str,
) -> TurnResult:
    """빛 자원 활성 (★ Floor1Definition 검색 + 종족 한정).

    - 횃불 (★ 누구나, 72h, 1만 스톤)
    - 정령 등불 (★ 요정 한정, 10h, 회복 2h)
    - 조명탄 (★ 50m 단발)
    """
    f1 = get_floor1_definition()
    source = next((ls for ls in f1.light_sources if ls.name == source_name), None)

    if source is None:
        return TurnResult(
            success=False,
            action_type="activate_light",
            message=(
                f"{source_name} 자원 없음 "
                "(★ 1층 빛 자원: 횃불/정령 등불/조명탄)."
            ),
        )

    if source.requires_race is not None:
        if character.race.value != source.requires_race:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=(
                    f"{character.name}({character.race.value})는 "
                    f"{source.name} 사용 X ({source.requires_race} 한정)."
                ),
            )

    if source.is_consumable:
        cur = character.light_state.consumables.get(source.name, 0)
        if cur <= 0:
            return TurnResult(
                success=False,
                action_type="activate_light",
                message=f"{source.name} 보유 X.",
            )
        character.light_state.consumables[source.name] = cur - 1

    character.light_state.active_source_name = source.name
    character.light_state.remaining_duration_hours = source.duration_hours or 0.0

    side: list[str] = [f"가시거리 {source.radius_meters}m"]
    if source.duration_hours:
        side.append(f"지속 {source.duration_hours}h")
    else:
        side.append("단발")

    return TurnResult(
        success=True,
        action_type="activate_light",
        message=f"{character.name}이(가) {source.name} 활성.",
        side_effects=side,
    )


# ─── 3. 이동 ───


def move_to_sub_area(
    party: list[Character],
    world: WorldState,
    current_location: Location,
    target_sub_area: str,
) -> TurnResult:
    """sub_area 이동 — Floor1 (DUNGEON) + 균열 내부 (RIFT) 본격.

    accessible_from / connections semantic = OUTBOUND (★ 현재 영역에서
    갈 수 있는 곳).

    Phase 8 A1: realm == RIFT 시 rift_def.sub_areas + RiftSubAreaDef
    .connections 본격 사용. target은 sub_area.id 또는 .name 본격.
    """
    # ★ Phase 8 A1 — 균열 내부 이동
    if current_location.realm == Realm.RIFT:
        rift_def = (
            FLOOR1_RIFT_DEFS.get(current_location.rift_id)
            if current_location.rift_id
            else None
        )
        if rift_def is None:
            return TurnResult(
                success=False,
                action_type="move",
                message=(
                    "현재 균열 정의 X "
                    f"(rift_id={current_location.rift_id})."
                ),
            )

        target = next(
            (
                sa
                for sa in rift_def.sub_areas
                if sa.id == target_sub_area or sa.name == target_sub_area
            ),
            None,
        )
        if target is None:
            return TurnResult(
                success=False,
                action_type="move",
                message=(
                    f"{target_sub_area} chamber 없음 "
                    f"(★ {rift_def.name} {len(rift_def.sub_areas)} 챕터)."
                ),
            )

        current_id = current_location.rift_sub_area
        current_rift_sa: RiftSubAreaDef | None = None
        if current_id:
            current_rift_sa = next(
                (sa for sa in rift_def.sub_areas if sa.id == current_id),
                None,
            )
            if current_rift_sa is None:
                return TurnResult(
                    success=False,
                    action_type="move",
                    message=f"현재 챕터 {current_id} 정의 X.",
                )
            if target.id not in current_rift_sa.connections:
                adj_names = ", ".join(
                    next(
                        (
                            s.name
                            for s in rift_def.sub_areas
                            if s.id == cid
                        ),
                        cid,
                    )
                    for cid in current_rift_sa.connections
                ) or "없음"
                return TurnResult(
                    success=False,
                    action_type="move",
                    message=(
                        f"{current_rift_sa.name} → {target.name} 인접 X "
                        f"(인접: {adj_names})."
                    ),
                )

        advance_time(party, world, elapsed_hours=0.5)

        from_label = (
            current_rift_sa.name if current_rift_sa is not None else "진입"
        )

        side: list[str] = [
            f"target_rift_sub_area={target.id}",
            "시간 0.5h 경과",
        ]

        # ★ Phase 8 A3 — boss_chamber 도달 시 active_boss_encounter spawn
        # 본격: 이미 spawn 본격 / 클리어 본격 X 시 신규 spawn 본격.
        if (
            target.id == rift_def.boss_chamber_id
            and world.active_boss_encounter is None
            and rift_def.rift_id not in world.cleared_rifts
        ):
            boss = _spawn_boss_encounter(
                rift_def=rift_def,
                is_variant=current_location.rift_is_variant,
            )
            world.active_boss_encounter = boss
            variant_label = " (변종)" if boss.is_variant else ""
            side.append(f"boss_spawned={boss.boss_id}")
            extra_msg = (
                f" ⚔ {boss.boss_name}{variant_label} 등장 "
                f"(HP {boss.hp}/{boss.hp_max}, {boss.boss_grade}등급)."
            )
        else:
            extra_msg = ""

        return TurnResult(
            success=True,
            action_type="move",
            message=(
                f"[{rift_def.name}] {from_label} → {target.name}." + extra_msg
            ),
            side_effects=side,
        )

    # ─── 일반 1층 (DUNGEON) 이동 ───
    f1 = get_floor1_definition()
    target_sa = next(
        (sa for sa in f1.sub_areas if sa.name == target_sub_area), None
    )

    if target_sa is None:
        return TurnResult(
            success=False,
            action_type="move",
            message=f"{target_sub_area} sub_area 없음 (★ 1층 6 영역).",
        )

    current_name = current_location.sub_area
    if current_name:
        current_floor_sa = next(
            (sa for sa in f1.sub_areas if sa.name == current_name), None
        )
        if current_floor_sa is None:
            return TurnResult(
                success=False,
                action_type="move",
                message=f"현재 위치 {current_name} 정의 X.",
            )
        if target_sub_area not in current_floor_sa.accessible_from:
            return TurnResult(
                success=False,
                action_type="move",
                message=(
                    f"{current_name} → {target_sub_area} 인접 X "
                    f"(인접: "
                    f"{', '.join(current_floor_sa.accessible_from) or '없음'})."
                ),
            )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="move",
        message=f"{current_name or '시작'} → {target_sub_area}.",
        side_effects=[
            f"target_sub_area={target_sub_area}",
            "시간 0.5h 경과",
        ],
    )


# ─── 4. 전투 ───


def execute_attack(
    attacker: Character,
    target_monster_name: str,
    party: list[Character],
    world: WorldState,
    attack_element: str | None = None,
) -> TurnResult:
    """전투 — 단순 공식 (★ 본 commit 본격, LLM 평가 X).

    공식:
    - 공격 = strength + physical
    - 9등급 몬스터 HP 30
    - 공격 < 30이면 처치 X + 받는 데미지 = max(0, 10 - bone_strength//2)

    Phase 8 A3:
    - world.active_boss_encounter 본격 시 보스 분기 (target string 무관 —
      보스 chamber 도달 후 모든 ATTACK은 보스 대상).
    - attack_element == boss.weakness_element → 2배 데미지.
    """
    # ★ Phase 8 A3 — 보스 encounter 우선 분기
    if world.active_boss_encounter is not None:
        return _execute_attack_boss(
            attacker, world.active_boss_encounter, party, world, attack_element
        )

    f1 = get_floor1_definition()
    monster = next(
        (m for m in f1.monsters if m.name == target_monster_name), None
    )

    if monster is None:
        return TurnResult(
            success=False,
            action_type="attack",
            message=f"{target_monster_name} 1층 몬스터 X.",
        )

    grade_value = int(monster.grade)

    attacker_dmg = attacker.strength + attacker.physical
    if attacker_dmg < 30:
        received = max(0, 10 - attacker.bone_strength // 2)
        attacker.hp = max(0, attacker.hp - received)
        return TurnResult(
            success=False,
            action_type="attack",
            message=(
                f"{attacker.name} → {target_monster_name} 공격 "
                f"(데미지 {attacker_dmg}). 처치 X. 받은 데미지 {received}."
            ),
            side_effects=[
                f"{attacker.name} HP {attacker.hp}/{attacker.hp_max}"
            ],
        )

    advance_time(party, world, elapsed_hours=0.5)

    # ★ Phase 8 B — first kill 본격 exp drop ("딱 한번" mechanism).
    exp_awarded, leveled_up = _award_kill_exp(
        attacker, monster.name, grade_value, world
    )

    side: list[str] = [f"드롭: {grade_value}등급 마석", "시간 0.5h 경과"]
    msg_tail = ""
    if exp_awarded > 0:
        side.append(f"exp_gained={attacker.name}:{exp_awarded}")
        msg_tail = f" 경험치 +{exp_awarded}."
    if leveled_up:
        side.append(f"level_up={attacker.name}:{attacker.level}")
        msg_tail += f" ⭐ 레벨 업! → Lv {attacker.level}."

    return TurnResult(
        success=True,
        action_type="attack",
        message=(
            f"{attacker.name}이(가) {target_monster_name} 처치 "
            f"({grade_value}등급).{msg_tail}"
        ),
        side_effects=side,
    )


# ─── 4.b 보스 전투 (★ Phase 8 A3) ───


def _execute_attack_boss(
    attacker: Character,
    boss: BossEncounter,
    party: list[Character],
    world: WorldState,
    attack_element: str | None,
) -> TurnResult:
    """보스 단일 ATTACK — base = strength+physical, 약점 시 2배."""
    base_damage = attacker.strength + attacker.physical
    weakness_bonus = 0
    if (
        boss.weakness_element is not None
        and attack_element is not None
        and attack_element == boss.weakness_element
    ):
        weakness_bonus = base_damage  # ★ 2배

    total_damage = base_damage + weakness_bonus
    new_hp = max(0, boss.hp - total_damage)
    boss.hp = new_hp

    if new_hp == 0:
        return _defeat_boss(attacker, boss, party, world, total_damage)

    advance_time(party, world, elapsed_hours=0.5)

    weak_tag = " ⚠ 약점!" if weakness_bonus > 0 else ""
    return TurnResult(
        success=True,
        action_type="attack",
        message=(
            f"{attacker.name} → {boss.boss_name} "
            f"공격 ({total_damage} 데미지).{weak_tag} "
            f"HP {boss.hp}/{boss.hp_max}."
        ),
        side_effects=[
            f"boss_hp={boss.hp}/{boss.hp_max}",
            "시간 0.5h 경과",
        ],
    )


def _defeat_boss(
    attacker: Character,
    boss: BossEncounter,
    party: list[Character],
    world: WorldState,
    last_damage: int,
) -> TurnResult:
    """보스 처치 — 정수 marker + 마석 inventory + world state mutate."""
    rift_def = FLOOR1_RIFT_DEFS.get(boss.rift_id)
    essence_color = rift_def.essence_color if rift_def is not None else "green"

    # 마석 inventory append (★ Inventory.add overweight 시 False)
    stone = Item(
        name=f"{boss.boss_name}의 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        description=(
            f"균열 수호자 {boss.boss_name} ({boss.boss_grade}등급) 마석."
        ),
    )
    stone_added = attacker.inventory.add(stone)

    # world state mutation
    if boss.boss_id not in world.defeated_bosses:
        world.defeated_bosses.append(boss.boss_id)
    if boss.rift_id not in world.cleared_rifts:
        world.cleared_rifts.append(boss.rift_id)
    if boss.rift_id in world.active_rifts:
        world.active_rifts.remove(boss.rift_id)
    world.active_boss_encounter = None

    advance_time(party, world, elapsed_hours=0.5)

    # ★ Phase 8 B — 보스 first kill 본격 exp drop. boss_id 본격 species id
    # (★ "bloody_castle_variant" 등 variant-aware — variant/normal 본격 별도).
    exp_awarded, leveled_up = _award_kill_exp(
        attacker, boss.boss_id, boss.boss_grade, world
    )

    rift_name = rift_def.name if rift_def is not None else boss.rift_id
    variant_label = " (변종)" if boss.is_variant else ""
    stone_tag = (
        f"{boss.boss_name}의 마석"
        if stone_added
        else f"{boss.boss_name}의 마석 (소지 X — 무게 한계)"
    )

    exp_tail = ""
    side = [
        f"essence_spawn={essence_color}",
        f"boss_defeated={boss.boss_id}",
        f"rift_cleared={boss.rift_id}",
        "시간 0.5h 경과",
    ]
    if exp_awarded > 0:
        side.append(f"exp_gained={attacker.name}:{exp_awarded}")
        exp_tail = f" 경험치 +{exp_awarded}."
    if leveled_up:
        side.append(f"level_up={attacker.name}:{attacker.level}")
        exp_tail += f" ⭐ 레벨 업! → Lv {attacker.level}."

    message = (
        f"⚔ {boss.boss_name}{variant_label} 처치! ({last_damage} 데미지) "
        f"보상: {essence_color} 정수, {stone_tag}.{exp_tail} "
        f"균열 '{rift_name}' 클리어 — 포탈이 열렸다 (EXIT_RIFT)."
    )

    return TurnResult(
        success=True,
        action_type="attack",
        message=message,
        side_effects=side,
    )


# ─── 5. 정수 흡수 ───

# ★ F4: GM이 정수를 색깔로 spawn (sim_gm_agent.py 146-152) — Player LLM이
# '갈색 정수' 등 색명을 ABSORB target으로 사용. 그러나 floor1.py drops는
# 본문 정합 본격 monster 본격 명명 ('고블린 정수' 등). 본 매핑이 둘을 연결.
_COLOR_TO_ESSENCE_NAME: dict[str, str] = {
    "갈색 정수": "고블린 정수",
    "흙색 정수": "노움 정수",
    "청록색 정수": "슬라임 정수",
    "산성록 정수": "슬라임 정수",
    "핏빛 정수": "칼날늑대 정수",
    "회청색 정수": "레이스 정수",
    "녹색 정수": "위치스램프 정수",
}


def absorb_floating_essence(
    character: Character,
    essence_name: str,
) -> TurnResult:
    """정수 흡수 (★ 13/14화 본문, Character.absorb_essence 진짜 호출).

    본 commit 단순화:
    - 1층 9등급 정수 매핑 (★ Floor1 monsters drops)
    - 살이 닿음 가정 (★ 후속 commit에 거리 시뮬)
    - ★ F4: 색명 → monster명 alias 매핑 (★ GM prompt 색 본격)
    """
    canonical_name = _COLOR_TO_ESSENCE_NAME.get(essence_name, essence_name)

    f1 = get_floor1_definition()
    found = None
    for m in f1.monsters:
        for d in m.drops:
            if d.essence_name == canonical_name:
                found = d
                break
        if found is not None:
            break

    if found is None:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=f"{essence_name} 1층 정수 X.",
        )

    color = found.color_pool[0] if found.color_pool else EssenceColor.GREEN
    essence = Essence(
        name=canonical_name,
        grade=EssenceGrade.GRADE_9,
        color=color,
        essence_type=EssenceType.DPS_MELEE,
        origin=EssenceOrigin.MONSTER_DROP,
        monster_source=canonical_name.replace(" 정수", ""),
    )

    success = character.absorb_essence(essence)

    if not success:
        return TurnResult(
            success=False,
            action_type="absorb_essence",
            message=(
                f"{character.name}이(가) {essence_name} 흡수 X "
                f"(슬롯 {character.essence_slots_used()}/"
                f"{character.essence_slot_max()})."
            ),
        )

    return TurnResult(
        success=True,
        action_type="absorb_essence",
        message=f"{character.name}이(가) {essence_name} 흡수.",
        side_effects=[
            f"슬롯 {character.essence_slots_used()}/"
            f"{character.essence_slot_max()}",
        ],
    )


# ─── 6. 휴식 ───


def rest(
    party: list[Character],
    world: WorldState,
    hours: float = 4.0,
) -> TurnResult:
    """휴식 — 4시간 교대 (★ 27화 본문)."""
    advance_time(party, world, elapsed_hours=hours)
    return TurnResult(
        success=True,
        action_type="rest",
        message=f"{hours}시간 휴식.",
        side_effects=[f"미궁 시간 {world.hours_in_dungeon}h / 168h"],
    )


# ─── 7. 메시지 스톤 ───


def send_message_stone(
    sender: Character,
    target_name: str,
    message_text: str,
) -> TurnResult:
    """메시지 스톤 통신 — 300m 본질 (★ 10화)."""
    return TurnResult(
        success=True,
        action_type="communicate",
        message=f"{sender.name} → {target_name}: '{message_text[:50]}'.",
        side_effects=["300m 반경 통신", "공명 stone 필수"],
    )


# ─── 8. 도주 ───


def flee_from_threat(
    party: list[Character],
    world: WorldState,
    threat_description: str,
) -> TurnResult:
    """도주 — 단순 시간 흐름 (★ 14화)."""
    advance_time(party, world, elapsed_hours=0.5)
    return TurnResult(
        success=True,
        action_type="flee",
        message=f"위협({threat_description}) 도주.",
        side_effects=["시간 0.5h", "다른 sub_area로 이동 가능"],
    )


# ─── 9. 비석 공물 ───


def _resolve_rift_id(target: str) -> str | None:
    """rift_id 또는 한국어 name → canonical rift_id (★ F6).

    LLM은 한국어 name ('핏빛성채') 사용. floor1.py는 rift_id ('bloody_castle').
    본격 alias bridge — F4 essence color→monster명 대 본격 동일 패턴.
    """
    f1 = get_floor1_definition()
    for r in f1.rifts:
        if r.rift_id == target or r.name == target:
            return r.rift_id
    return None


def offer_to_stone(
    character: Character,
    rift_id: str,
    world: WorldState,
) -> TurnResult:
    """비석 공물 — 8등급 마석 → 균열 진입 가능 (★ 374화).

    본 commit 단순화: rift_id 검증만 (★ 마석 차감은 inventory 통합 시).
    ★ F6: target은 rift_id 또는 한국어 name 본격.
    """
    canonical = _resolve_rift_id(rift_id)
    if canonical is None:
        return TurnResult(
            success=False,
            action_type="offer_to_stone",
            message=f"균열 {rift_id} X (★ 1층 4 균열).",
        )

    f1 = get_floor1_definition()
    rift = next(r for r in f1.rifts if r.rift_id == canonical)

    if canonical not in world.active_rifts:
        world.active_rifts.append(canonical)

    return TurnResult(
        success=True,
        action_type="offer_to_stone",
        message=(
            f"{character.name}이(가) 비석에 8등급 마석 공물 → "
            f"{rift.name} 균열 활성."
        ),
        side_effects=[f"active_rifts={world.active_rifts}"],
    )


# ─── 10. 균열 진입 ───


def enter_rift(
    party: list[Character],
    world: WorldState,
    rift_id: str,
    rng: random.Random | None = None,
    force_variant: bool | None = None,
) -> TurnResult:
    """균열 진입 — Location 변경은 caller가 (★ side_effect 명시).

    Phase 8 A1:
    - party_capacity 검증 (★ 5명 한도, 본인 결정)
    - entrance_id 발행 → caller가 location.rift_sub_area 설정

    Phase 8 A2:
    - variant 결정 (★ rift_def.variant_trigger.base_probability)
    - rng inject 본격 reproducibility (test seed)
    - force_variant: True/False 본격 강제 (★ test/e2e 본격)

    ★ F6: target은 rift_id 또는 한국어 name 본격.
    """
    canonical = _resolve_rift_id(rift_id)
    if canonical is None or canonical not in world.active_rifts:
        return TurnResult(
            success=False,
            action_type="enter_rift",
            message=f"균열 {rift_id} 비활성 (먼저 비석 공물).",
        )

    rift_def = FLOOR1_RIFT_DEFS.get(canonical)
    if rift_def is None:
        return TurnResult(
            success=False,
            action_type="enter_rift",
            message=f"균열 {canonical} 정의 X.",
        )

    # ★ Phase 8 A1 — 파티 5명 한도
    alive_party = [c for c in party if c.is_alive()]
    if len(alive_party) > rift_def.party_capacity:
        return TurnResult(
            success=False,
            action_type="enter_rift",
            message=(
                f"파티 {len(alive_party)}명 — {rift_def.name} 한도 "
                f"{rift_def.party_capacity}명 초과 (진입 X)."
            ),
        )

    # ★ Phase 8 A2 — 변종 결정
    if force_variant is not None:
        is_variant = force_variant and rift_def.variant_boss_name is not None
    else:
        is_variant = decide_variant(rift_def, rng)

    advance_time(party, world, elapsed_hours=0.5)

    variant_msg = ""
    if is_variant:
        # ★ 본인 답 6.6 — 진입 시점 시각/공기 hint (★ chamber 도달 시 본격 명시)
        variant_msg = " ⚠ 공기가 다르다. 평소와 다른 무엇이 기다린다."

    return TurnResult(
        success=True,
        action_type="enter_rift",
        message=(
            f"균열 {canonical} 진입 → {rift_def.entrance_id}.{variant_msg}"
        ),
        side_effects=[
            "target_realm=RIFT",
            f"target_rift_id={canonical}",
            f"target_rift_sub_area={rift_def.entrance_id}",
            f"target_rift_is_variant={is_variant}",
            "시간 0.5h",
        ],
    )


# ─── 11. 균열 탈출 ───


def exit_rift(
    party: list[Character],
    world: WorldState,
    rift_id: str,
) -> TurnResult:
    """균열 탈출 — 1층 복귀.

    ★ F6: target은 rift_id 또는 한국어 name 본격.
    """
    canonical = _resolve_rift_id(rift_id) or rift_id
    if canonical in world.active_rifts:
        world.active_rifts.remove(canonical)

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="exit_rift",
        message=f"균열 {canonical} 탈출 → 1층.",
        side_effects=["target_realm=DUNGEON", "시간 0.5h"],
    )


# ─── 12. 탐색 ───


def explore_area(
    party: list[Character],
    world: WorldState,
) -> TurnResult:
    """탐색 — 시간 흐름 + 가능성 발견."""
    advance_time(party, world, elapsed_hours=0.5)
    return TurnResult(
        success=True,
        action_type="explore",
        message="주변 탐색.",
        side_effects=["시간 0.5h"],
    )


# ─── 13. 아이템 사용 ───


def use_item(
    character: Character,
    item_name: str,
) -> TurnResult:
    """아이템 사용 — 본 commit 단순화 (★ 후속 commit에 inventory 통합)."""
    return TurnResult(
        success=True,
        action_type="use_item",
        message=f"{character.name}이(가) {item_name} 사용.",
        side_effects=[],
    )


# ─── 14b. 레벨 + 경험치 (★ Phase 8 B) ───


def _award_kill_exp(
    actor: Character,
    species_id: str,
    grade: int,
    world: WorldState,
) -> tuple[int, bool]:
    """처치 본격 actor exp drop + level up check (★ 본인 답 mechanism).

    본질 (★ Phase 8 B):
    - 같은 species (★ MonsterDef.name / Boss.boss_id) 두 번째 처치 → 0 exp
    - first kill → MONSTER_EXP_BY_GRADE[grade] base exp
    - actor.experience += base
    - level_for_exp(actor.experience) > actor.level 시 level up
      → actor.level update (★ essence_slot_max도 같이 자동 증가 — level 본격)

    Args:
        actor: 처치자
        species_id: 본격 species 식별자 (★ 정상 monster.name / 보스 boss.boss_id)
        grade: 0-9 (★ 0 = 계층군주)
        world: WorldState (★ first_killed_species mutation)

    Returns:
        (awarded_exp, leveled_up) — 본격 awarded_exp = 0 본격 두 번째 처치.
    """
    if species_id in world.first_killed_species:
        return 0, False

    base_exp = MONSTER_EXP_BY_GRADE.get(grade, 50)
    actor.experience += base_exp
    world.first_killed_species.add(species_id)

    old_level = actor.level
    new_level = level_for_exp(actor.experience)
    leveled_up = new_level > old_level
    if leveled_up:
        actor.level = new_level

    return base_exp, leveled_up


# ─── 14. 1층 종료 조건 (★ Phase 8 A4) ───


def check_time_limit(
    world: WorldState,
    turn_number: int | None = None,
) -> bool:
    """168h 도달 시 simulation_status → TIME_LIMIT_REACHED 본격 mutation.

    본질 (★ Phase 8 A4):
    - 7일 (168h) 만료 = 1층 강제 종료 → 마을 자동 귀환 (★ 후속 location mutate)
    - 이미 종료 상태 (status != ACTIVE)면 no-op (★ idempotent)

    Returns:
        True = 본 호출에서 신규 종료 발현. False = 이미 종료 또는 미달.
    """
    if world.simulation_status != SimulationStatus.ACTIVE:
        return False
    if world.hours_in_dungeon >= TIME_LIMIT_HOURS:
        world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
        world.simulation_over_reason = (
            f"7일 ({TIME_LIMIT_HOURS}시간) 만료. "
            "미궁 자동 마을 포탈 귀환."
        )
        world.simulation_over_turn = turn_number
        return True
    return False


def check_party_defeated(
    party: list[Character],
    world: WorldState,
    turn_number: int | None = None,
) -> bool:
    """전원 HP=0 시 simulation_status → PARTY_DEFEATED 본격 mutation.

    본질 (★ Phase 8 A4):
    - 탐사대 전원 사망 = 1층 강제 종료
    - 부분 사망 (★ 1명 alive) → ACTIVE 유지

    Returns:
        True = 본 호출에서 신규 종료 발현. False = 이미 종료 또는 미달.
    """
    if world.simulation_status != SimulationStatus.ACTIVE:
        return False
    if not party:
        return False
    if any(c.is_alive() for c in party):
        return False
    world.simulation_status = SimulationStatus.PARTY_DEFEATED
    world.simulation_over_reason = "탐사대 전원 사망."
    world.simulation_over_turn = turn_number
    return True


# ─── 15. 2층 진입 / 1층 복귀 (★ Phase 8 C) ───

# 본인 답 (2026-05-13): "한달마다 열리는 미궁에서 최초로 다음층 진입 파티 →
# 경험치 보너스". 본 sim instance 본격 "1 미궁 인스턴스" 본격 매핑 → 본 sim에서
# 최초 진입 시 1회만 적용.
FIRST_FLOOR_TWO_ENTRY_EXP_BONUS: int = 500


def enter_floor_two(
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """1층 4 포탈 통로 → 2층 진입 본격 (★ Phase 8 C).

    본질 (★ 본인 답):
    - 1층 동/서/남/북 포탈 통로 (FLOOR_TWO_PORTAL_SUB_AREAS) 본격 진입 가능
    - simulation_status → FLOOR_TRANSITION (★ A4 enum 본격 본격 사용처)
    - 본 sim 본격 최초 진입 파티 → 전 alive 멤버 +500 exp + level up

    실패:
    - simulation_status != ACTIVE (★ 본격 종료 상태)
    - location.sub_area not in FLOOR_TWO_PORTAL_SUB_AREAS
    """
    if world.simulation_status != SimulationStatus.ACTIVE:
        return TurnResult(
            success=False,
            action_type="enter_floor_two",
            message=(
                "Simulation 종료 상태 — 2층 진입 X "
                f"({world.simulation_status.value})."
            ),
        )

    current = location.sub_area
    if current not in FLOOR_TWO_PORTAL_SUB_AREAS:
        return TurnResult(
            success=False,
            action_type="enter_floor_two",
            message=(
                f"여기는 2층 포탈 통로가 아니다 (현 위치: {current}). "
                "동/서/남/북 포탈 통로로 이동 후 진입."
            ),
        )

    world.floor_two.entered = True
    world.floor_two.entry_sub_area_from_floor1 = current

    side: list[str] = ["floor_transition=2", f"entry_from={current}"]
    bonus_tail = ""
    if not world.floor_two.first_party_bonus_claimed:
        world.floor_two.first_party_bonus_claimed = True
        for member in party:
            if not member.is_alive():
                continue
            member.experience += FIRST_FLOOR_TWO_ENTRY_EXP_BONUS
            side.append(
                f"exp_gained={member.name}:"
                f"{FIRST_FLOOR_TWO_ENTRY_EXP_BONUS}"
            )
            new_level = level_for_exp(member.experience)
            if new_level > member.level:
                member.level = new_level
                side.append(f"level_up={member.name}:{new_level}")
        side.append("first_floor_two_party=true")
        bonus_tail = (
            f"\n⭐ 본 미궁 최초 2층 진입 파티 — 전원 +"
            f"{FIRST_FLOOR_TWO_ENTRY_EXP_BONUS} exp 보너스."
        )

    location.floor = 2
    location.sub_area = world.floor_two.current_sub_area

    world.simulation_status = SimulationStatus.FLOOR_TRANSITION
    world.simulation_over_reason = (
        f"2층 진입: {current} → {world.floor_two.current_sub_area}"
    )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="enter_floor_two",
        message=(
            f"2층 진입 — {current} 포탈 통과 → "
            f"{world.floor_two.current_sub_area}.{bonus_tail}"
        ),
        side_effects=side,
    )


def exit_to_floor_one(
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """2층 → 1층 복귀 (★ Phase 8 C — 본인 답 "왕복 가능").

    본 함수 호출 시 location 본격 1층 entry_sub_area_from_floor1 복귀,
    simulation_status 본격 ACTIVE 복원.

    실패:
    - floor_two.entered == False (★ 진입한 적 없음)
    """
    if not world.floor_two.entered:
        return TurnResult(
            success=False,
            action_type="exit_to_floor_one",
            message="2층 진입 기록 없음 — 복귀 X.",
        )

    # entered=True 이면 enter_floor_two에서 entry_sub_area_from_floor1을
    # 같은 시점에 set — invariant. None 시 caller가 state를 손상시킨 것.
    entry = world.floor_two.entry_sub_area_from_floor1
    assert entry is not None, (
        "entry_sub_area_from_floor1 None — floor_two.entered invariant 위반."
    )

    world.floor_two.returned_to_floor1 = True

    location.floor = 1
    location.sub_area = entry

    world.simulation_status = SimulationStatus.ACTIVE
    world.simulation_over_reason = None
    world.simulation_over_turn = None

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="exit_to_floor_one",
        message=f"1층 복귀 — {entry}.",
        side_effects=[
            "floor_transition=1",
            f"return_to={entry}",
        ],
    )
