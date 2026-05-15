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

from .cities.temples import get_deity_by_sub_area
from .floors.floor1 import get_floor1_definition
from .floors.floor1_rifts import FLOOR1_RIFT_DEFS, decide_variant
from .floors.registry import get_current_floor_definition
from .state_v2 import (
    SEVERITY_LEAVES_SCAR,
    SEVERITY_RECOVERY_DEFAULT,
    BossEncounter,
    Character,
    ClassType,
    Essence,
    EssenceColor,
    EssenceGrade,
    EssenceOrigin,
    EssenceType,
    FloorDefinition,
    FloorState,
    Injury,
    InjuryBodyPart,
    InjurySeverity,
    Item,
    ItemCategory,
    Location,
    Race,
    Realm,
    RiftDef,
    RiftSubAreaDef,
    Scar,
    SimulationStatus,
    WorldState,
    level_for_exp,
)

# ★ Phase 8 R1 — TIME_LIMIT_HOURS module 상수 제거. 본 시간 한도는 floor 본격
# (★ FloorDefinition.base_time_hours)에서 가져옴 (★ 단일 source of truth).
# 2층+ 본격 다른 한도 정의 가능 enabler.

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

# ★ Phase 8 exchange — 마석 환전 rate (★ 본문 9등급=20, 8등급=100).
# 7-0 등급 본문 명시 X → 등급당 5배 추정 (★ 9→8 = 5배 정합).
# 후속 본문 발견 시 보강 (★ namu §2.2 본격 본격 본격).
MAGE_STONE_EXCHANGE_RATE: dict[int, int] = {
    9: 20,         # ★ 본문 명시
    8: 100,        # ★ 본문 명시
    7: 500,        # 추측
    6: 2_500,
    5: 12_500,     # ★ namu "5등급 정수 수천만 스톤" 정합 본격 본격
    4: 62_500,
    3: 312_500,
    2: 1_562_500,
    1: 7_812_500,
    0: 39_062_500,  # 계층군주
}

# ★ Phase 8 exchange — 환전소 sub_area id (★ a-2 RAPDONIA 본격 본격).
EXCHANGE_OFFICE_SUB_AREA: str = "exchange_office"

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


# ─── Phase 9.3 — 부상 generation helpers (★ ATTACK producer) ───


def _severity_for_damage(hp_loss: int) -> str | None:
    """hp_loss → InjurySeverity value mapping (★ 본 commit 추측 — 본문 X).

    boundary (★ 후속 본문 발견 시 보강):
    - 0 이하: None (★ 부상 X)
    - 1-10: SCRATCH (★ 23화 narrative 본격)
    - 11-30: MINOR
    - 31-60: MAJOR (★ 25화 흉터 본격)
    - 61+: CRITICAL
    """
    if hp_loss <= 0:
        return None
    if hp_loss <= 10:
        return InjurySeverity.SCRATCH.value
    if hp_loss <= 30:
        return InjurySeverity.MINOR.value
    if hp_loss <= 60:
        return InjurySeverity.MAJOR.value
    return InjurySeverity.CRITICAL.value


def _generate_injury_from_damage(
    hp_loss: int, rng: random.Random | None = None
) -> Injury | None:
    """hp_loss 본격 Injury instance 본격 (★ ATTACK 본격 본격 caller).

    severity = hp_loss boundary mapping (★ _severity_for_damage)
    body_part = 5 부위 random (★ rng inject 본격 reproducibility)
    recovery_days = SEVERITY_RECOVERY_DEFAULT[severity]
    scar = SEVERITY_LEAVES_SCAR[severity]
    """
    severity = _severity_for_damage(hp_loss)
    if severity is None:
        return None
    if rng is None:
        rng = random.Random()
    body_part = rng.choice(list(InjuryBodyPart)).value
    return Injury(
        severity=severity,
        body_part=body_part,
        recovery_days=SEVERITY_RECOVERY_DEFAULT[severity],
        scar=SEVERITY_LEAVES_SCAR[severity],
    )


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
        side: list[str] = [
            f"{attacker.name} HP {attacker.hp}/{attacker.hp_max}"
        ]
        # ★ Phase 9.3 — hp_loss 본격 부상 generation (★ producer)
        injury = _generate_injury_from_damage(received)
        if injury is not None:
            attacker.injuries.append(injury)
            side.append(
                f"injury_inflicted={attacker.name}:"
                f"{injury.body_part}_{injury.severity}"
            )
        return TurnResult(
            success=False,
            action_type="attack",
            message=(
                f"{attacker.name} → {target_monster_name} 공격 "
                f"(데미지 {attacker_dmg}). 처치 X. 받은 데미지 {received}."
            ),
            side_effects=side,
        )

    advance_time(party, world, elapsed_hours=0.5)

    # ★ Phase 8 B — first kill 본격 exp drop ("딱 한번" mechanism).
    exp_awarded, leveled_up = _award_kill_exp(
        attacker, monster.name, grade_value, world
    )

    side = [f"드롭: {grade_value}등급 마석", "시간 0.5h 경과"]
    msg_tail = ""
    if exp_awarded > 0:
        side.append(f"exp_gained={attacker.name}:{exp_awarded}")
        msg_tail = f" 경험치 +{exp_awarded}."
    if leveled_up:
        side.append(f"level_up={attacker.name}:{attacker.level}")
        side.append(
            f"soul_power_gain={attacker.name}:+{SOUL_POWER_GAIN_PER_LEVEL}"
        )
        msg_tail += (
            f" ⭐ 레벨 업! → Lv {attacker.level} "
            f"(영혼력 +{SOUL_POWER_GAIN_PER_LEVEL})."
        )

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
    # ★ Phase 8 village-schema-1 — Item.grade 본격 boss.boss_grade wire
    # (★ village-schema-2 commit 본격 환전 rate lookup 본격 사용처).
    stone = Item(
        name=f"{boss.boss_name}의 마석",
        category=ItemCategory.MATERIAL,
        weight=1,
        description=(
            f"균열 수호자 {boss.boss_name} ({boss.boss_grade}등급) 마석."
        ),
        grade=boss.boss_grade,
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
        side.append(
            f"soul_power_gain={attacker.name}:+{SOUL_POWER_GAIN_PER_LEVEL}"
        )
        exp_tail += (
            f" ⭐ 레벨 업! → Lv {attacker.level} "
            f"(영혼력 +{SOUL_POWER_GAIN_PER_LEVEL})."
        )

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
    # ★ Phase 9 rift-cooldown — 의도적 활성도 period 기록 (★ 자연 활성 next gate).
    world.rift_last_opened_periods[canonical] = world.month_number

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


# ★ Phase 8 (c) — 포션 회복량 (★ 본문 X 추측, 후속 본문 발견 시 보강).
# 본 commit minimal: hp_max 본격 50% 본격 본격 본격 게임성 채택.
POTION_HEAL_AMOUNT: int = 50


def _item_use_category(item: Item) -> str:
    """Item 종류 본격 substring 분류 (★ Phase 8 (c) — schema 변경 X).

    본 commit minimal — Item.category enum (★ MATERIAL/CONSUMABLE 등)
    본격 본격 본격 X 본격, name substring 본격 use-time 분류.
    후속 commit (★ schema-3) 본격 별도 use_category field 본격 본격.
    """
    name = item.name
    if "포션" in name:
        return "potion"
    if "식량" in name:
        return "food"
    if "횃불" in name:
        return "torch"
    return "unknown"


def use_item(
    character: Character,
    item_name: str,
) -> TurnResult:
    """아이템 사용 — Phase 8 (c) minimal effect.

    Scope:
    - 포션 → HP +POTION_HEAL_AMOUNT (★ hp_max cap)
    - 식량 / 횃불 → message only (★ effect X — 후속 hunger / visibility 본격)
    - 1회 사용 → inventory.items.remove

    실패:
    - inventory 본격 빈 → fail
    - item_name 본격 본격 본격 X → fail (★ substring 본격)

    호출 패턴 (★ sim_runner): use_item(actor, action.target)
    """
    if not character.inventory.items:
        return TurnResult(
            success=False,
            action_type="use_item",
            message=f"{character.name} 본격 아이템 X.",
        )

    target_item: Item | None = None
    for item in character.inventory.items:
        if item.name == item_name or item_name in item.name:
            target_item = item
            break

    if target_item is None:
        return TurnResult(
            success=False,
            action_type="use_item",
            message=f"{character.name} 본격 '{item_name}' 본격 X.",
        )

    category = _item_use_category(target_item)
    side_effects: list[str] = [
        f"item_used={character.name}:{target_item.name}"
    ]

    if category == "potion":
        old_hp = character.hp
        character.hp = min(
            character.hp_max, character.hp + POTION_HEAL_AMOUNT
        )
        healed = character.hp - old_hp
        message = (
            f"{character.name}이(가) {target_item.name}을(를) 마셨다. "
            f"HP +{healed} (★ 총 {character.hp}/{character.hp_max})."
        )
        side_effects.append(f"hp_gain={character.name}:+{healed}")
    elif category == "food":
        message = (
            f"{character.name}이(가) {target_item.name}을(를) 먹었다. "
            f"배가 든든해진다."
        )
    elif category == "torch":
        message = (
            f"{character.name}이(가) {target_item.name}에 불을 붙였다. "
            f"주위가 밝아진다."
        )
    else:
        message = (
            f"{character.name}이(가) {target_item.name}을(를) 사용했다. "
            f"(★ 본격 효과 미정 — 후속 commit 본격)"
        )

    # 1회 사용 — frozen Item 본격 list reference identity 본격 remove.
    character.inventory.items.remove(target_item)

    return TurnResult(
        success=True,
        action_type="use_item",
        message=message,
        side_effects=side_effects,
    )


# ─── 14b. 레벨 + 경험치 (★ Phase 8 B) ───

# ★ Phase 8 MP — 22화 본문 정합 "영혼력이 +10 상승합니다".
# level up 시 soul_power_max + soul_power 둘 다 +10 (★ "상승" 해석 본격).
# 종족별 시작값 (요정 60 / 바바리안 30 등)은 init_from_plan 본격 보존.
SOUL_POWER_GAIN_PER_LEVEL: int = 10


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
        # ★ Phase 8 MP — 22화 본문 정합 "영혼력이 +10 상승합니다".
        # 1 level up = +10 to both current and max (★ "상승" 해석).
        # 종족별 시작값 보존 (★ 요정 60 / 바바리안 30 etc — init_from_plan).
        levels_gained = new_level - old_level
        gain = SOUL_POWER_GAIN_PER_LEVEL * levels_gained
        actor.soul_power_max += gain
        actor.soul_power += gain

    return base_exp, leveled_up


# ─── 14. 1층 종료 조건 (★ Phase 8 A4) ───


def check_time_limit(
    world: WorldState,
    time_limit_hours: int,
    turn_number: int | None = None,
) -> bool:
    """시간 한도 도달 시 simulation_status → TIME_LIMIT_REACHED mutation.

    본질 (★ Phase 8 A4 + R1):
    - time_limit_hours 본격 caller가 FloorDefinition.base_time_hours 본격 전달
      (★ R1: module 상수 본격 단일 source of truth — FloorDefinition.base_time_hours)
    - 1층 본격: 7일 (168h) — 본문 1차 자료
    - 이미 종료 상태 (status != ACTIVE)면 no-op (★ idempotent)

    Args:
        world: WorldState (★ status mutate)
        time_limit_hours: 본 층 시간 한도 (★ FloorDefinition.base_time_hours)
        turn_number: trace 본격 turn (optional)

    Returns:
        True = 본 호출에서 신규 종료 발현. False = 이미 종료 또는 미달.
    """
    if world.simulation_status != SimulationStatus.ACTIVE:
        return False
    if world.hours_in_dungeon >= time_limit_hours:
        world.simulation_status = SimulationStatus.TIME_LIMIT_REACHED
        days = time_limit_hours // 24
        world.simulation_over_reason = (
            f"{days}일 ({time_limit_hours}시간) 만료. "
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
    # ★ Phase 8 (b) — 본문 톤 정합 (★ 37화 "일상다반사" 정합 무덤덤 어조).
    world.simulation_over_reason = "탐사대 전원이 미궁에서 쓰러졌다."
    world.simulation_over_turn = turn_number
    return True


def apply_time_limit_village_return(location: Location) -> None:
    """A4 TIME_LIMIT_REACHED 시 location → 마을 도착 mutation (★ Phase 8 a-3).

    본인 답 정합 (docs/village_spec.md §7):
    - 7일 (168h) 만료 → 자동 마을 포탈 귀환 (★ A4 simulation_over_reason)
    - 도착 = 라프도니아 7구역 중앙 광장 (★ 162화 본문 정합)
    - floor=0 (★ 본인 답 7.2: "미궁의 층수와 마을은 별개")
    - realm=CITY (★ existing Realm.CITY enum)

    PARTY_DEFEATED 본격 본격 마을 X (★ 본인 답: 시신 = 사물, 미궁 연료).
    FLOOR_TRANSITION 본격 본격 X (★ C 본격, 2층 본격).
    """
    # Local import 본격 — service/game/cities/ module 본격 단일 production caller.
    from .cities.registry import DEFAULT_CITY_ENTRY_SUB_AREA, DEFAULT_CITY_ID

    location.realm = Realm.CITY
    location.floor = 0
    location.sub_area = DEFAULT_CITY_ENTRY_SUB_AREA
    location.city_id = DEFAULT_CITY_ID
    # 균열 본격 reset (★ 마을 본격 균열 본격 X)
    location.rift_id = None
    location.rift_sub_area = None
    location.rift_is_variant = False
    # 마을 = 빛 환경 (★ namu §4 라프도니아 도시)
    location.has_light = True
    location.visibility_meters = 100


# ─── 15. 인접 층 진입 / 복귀 (★ Phase 8 C / R3+R4 generic) ───

# 본인 답 (2026-05-13): "한달마다 열리는 미궁에서 최초로 다음층 진입 파티 →
# 경험치 보너스". 본 sim instance 본격 "1 미궁 인스턴스" 본격 매핑 → 본 sim에서
# 최초 진입 시 1회만 적용 (★ floor 본격 별도).
FIRST_FLOOR_ENTRY_EXP_BONUS: int = 500

# 2층+ 콘텐츠 본격 후속 — 본 default 본격 minimal "도착 지점".
# 후속 commit 본격 FloorDefinition.arrival_sub_area 본격 본격 본격 정합.
_FLOOR_ARRIVAL_SUB_AREA: str = "도착 지점"


def enter_next_floor(
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """현재 층 → 다음 층 (current+1) 진입 (★ Phase 8 R3 generic).

    본질 (★ 본인 답):
    - 현재 층 portal_to_next 본격 sub_area 본격 진입 가능
    - simulation_status → FLOOR_TRANSITION
    - 본 sim 본격 최초 진입 파티 → 전 alive 멤버 +500 exp + level up

    실패:
    - simulation_status != ACTIVE
    - location.sub_area not in 현재 층 portal_to_next
    """
    if world.simulation_status != SimulationStatus.ACTIVE:
        return TurnResult(
            success=False,
            action_type="enter_next_floor",
            message=(
                "Simulation 종료 상태 — 층 진입 X "
                f"({world.simulation_status.value})."
            ),
        )

    current_floor = location.floor if location.floor is not None else 1
    next_floor = current_floor + 1

    current_floor_def = get_current_floor_definition(location)
    current_sub_area = location.sub_area
    if current_sub_area not in current_floor_def.portal_to_next:
        return TurnResult(
            success=False,
            action_type="enter_next_floor",
            message=(
                f"여기는 다음 층 포탈이 아니다 (현 위치: {current_sub_area}). "
                f"portal_to_next: {sorted(current_floor_def.portal_to_next)}."
            ),
        )

    arrival = _FLOOR_ARRIVAL_SUB_AREA
    floor_state = world.floor_states.setdefault(
        next_floor, FloorState(floor_number=next_floor, current_sub_area=arrival)
    )
    floor_state.entered = True
    floor_state.entry_sub_area_from_prev = current_sub_area

    side: list[str] = [
        f"floor_transition={next_floor}",
        f"entry_from={current_sub_area}",
    ]
    bonus_tail = ""
    if next_floor not in world.first_entry_parties:
        world.first_entry_parties.add(next_floor)
        for member in party:
            if not member.is_alive():
                continue
            member.experience += FIRST_FLOOR_ENTRY_EXP_BONUS
            side.append(
                f"exp_gained={member.name}:{FIRST_FLOOR_ENTRY_EXP_BONUS}"
            )
            new_level = level_for_exp(member.experience)
            if new_level > member.level:
                # ★ Phase 8 MP — 22화 본문 "+10 영혼력 상승" 정합.
                levels_gained = new_level - member.level
                gain = SOUL_POWER_GAIN_PER_LEVEL * levels_gained
                member.soul_power_max += gain
                member.soul_power += gain
                member.level = new_level
                side.append(f"level_up={member.name}:{new_level}")
                side.append(f"soul_power_gain={member.name}:+{gain}")
        side.append(f"first_floor_party={next_floor}")
        bonus_tail = (
            f"\n⭐ 본 미궁 최초 {next_floor}층 진입 파티 — 전원 +"
            f"{FIRST_FLOOR_ENTRY_EXP_BONUS} exp 보너스."
        )

    location.floor = next_floor
    location.sub_area = floor_state.current_sub_area

    world.simulation_status = SimulationStatus.FLOOR_TRANSITION
    world.simulation_over_reason = (
        f"{next_floor}층 진입: {current_sub_area} → {floor_state.current_sub_area}"
    )

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="enter_next_floor",
        message=(
            f"{next_floor}층 진입 — {current_sub_area} 포탈 통과 → "
            f"{floor_state.current_sub_area}.{bonus_tail}"
        ),
        side_effects=side,
    )


def exit_to_prev_floor(
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """현재 층 → 이전 층 (current-1) 복귀 (★ Phase 8 R3 generic, 본인 답 "왕복").

    본 함수 호출 시 location 본격 이전 층 entry_sub_area_from_prev 복귀,
    simulation_status 본격 ACTIVE 복원.

    실패:
    - 현재 층 floor_state 본격 X (★ 진입한 적 없음)
    - prev_floor < 1 (★ 1층 최하단)
    """
    current_floor = location.floor if location.floor is not None else 1
    prev_floor = current_floor - 1
    if prev_floor < 1:
        return TurnResult(
            success=False,
            action_type="exit_to_prev_floor",
            message="이전 층 X (★ 1층 최하단).",
        )

    floor_state = world.floor_states.get(current_floor)
    if floor_state is None or not floor_state.entered:
        return TurnResult(
            success=False,
            action_type="exit_to_prev_floor",
            message=f"{current_floor}층 진입 기록 없음 — 복귀 X.",
        )

    # entered=True 이면 enter_next_floor에서 entry_sub_area_from_prev를
    # 같은 시점에 set — invariant. None 시 caller가 state를 손상시킨 것.
    entry = floor_state.entry_sub_area_from_prev
    assert entry is not None, (
        "entry_sub_area_from_prev None — floor_state.entered invariant 위반."
    )

    floor_state.returned_to_prev = True

    location.floor = prev_floor
    location.sub_area = entry

    world.simulation_status = SimulationStatus.ACTIVE
    world.simulation_over_reason = None
    world.simulation_over_turn = None

    advance_time(party, world, elapsed_hours=0.5)

    return TurnResult(
        success=True,
        action_type="exit_to_prev_floor",
        message=f"{prev_floor}층 복귀 — {entry}.",
        side_effects=[
            f"floor_transition={prev_floor}",
            f"return_to={entry}",
        ],
    )


# ─── 16. 환전소 마석 → 스톤 (★ Phase 8 exchange) ───


def exchange_mage_stones(
    actor: Character,
    location: Location,
) -> TurnResult:
    """환전소 본격 마석 batch → 스톤 환전 (★ docs/village_spec.md §2-2).

    본질 (★ namu §2.2 본문 정합):
    - 9등급 마석 = 20 스톤
    - 8등급 마석 = 100 스톤
    - 7-0 등급: 추측 (★ 후속 본문 진단)

    Item.grade 본격 식별 (★ village-schema-1 5e654be 본격 wire):
    - grade is not None → 마석
    - rate 본격 0 본격 skip (★ Item.grade 있으나 rate table X)

    실패:
    - realm != CITY (★ Realm.CITY enum)
    - sub_area != EXCHANGE_OFFICE_SUB_AREA
    - 마석 X (★ inventory 본격 grade is not None Item 없음)
    """
    if location.realm != Realm.CITY:
        return TurnResult(
            success=False,
            action_type="exchange_mage_stones",
            message="환전소는 마을(CITY)에서만 작동.",
        )

    if location.sub_area != EXCHANGE_OFFICE_SUB_AREA:
        return TurnResult(
            success=False,
            action_type="exchange_mage_stones",
            message=(
                f"환전소({EXCHANGE_OFFICE_SUB_AREA})로 이동 필요. "
                f"현재: {location.sub_area}"
            ),
        )

    mage_stones = [
        i for i in actor.inventory.items if i.grade is not None
    ]
    if not mage_stones:
        return TurnResult(
            success=False,
            action_type="exchange_mage_stones",
            message=f"{actor.name} 본격 환전 가능 마석 X.",
        )

    total_stone = 0
    exchanged_count = 0
    exchanged_items: list[Item] = []
    for stone in mage_stones:
        # stone.grade is not None (★ 위 filter 본격 보장)
        rate = MAGE_STONE_EXCHANGE_RATE.get(stone.grade or 0, 0)
        if rate > 0:
            total_stone += rate
            exchanged_count += 1
            exchanged_items.append(stone)

    if exchanged_count == 0:
        # 모든 마석 본격 rate X (★ 본격 본격 불가능 본격 본격 본격)
        return TurnResult(
            success=False,
            action_type="exchange_mage_stones",
            message=(
                f"{actor.name} 마석 본격 환전 rate X "
                f"({len(mage_stones)}개 본격)."
            ),
        )

    # mutation — 환전된 Item 본격 list 본격 remove (★ Inventory.items mutable list).
    # Item frozen 본격 본격 list reference identity 본격 본격.
    for item in exchanged_items:
        actor.inventory.items.remove(item)
    actor.stone += total_stone

    return TurnResult(
        success=True,
        action_type="exchange_mage_stones",
        message=(
            f"{actor.name} 마석 {exchanged_count}개 환전. "
            f"+{total_stone} 스톤 (★ 총 {actor.stone})."
        ),
        side_effects=[
            f"exchanged_stones={actor.name}:{exchanged_count}",
            f"stone_gained={actor.name}:+{total_stone}",
        ],
    )


# ─── 17. 마을 turn loop (★ Phase 9 시간 mechanism) ───

# 본문 정합 (★ 19화 본문 직접 quote):
# "매월 1일이 되는 자정에는 미궁이 열린다.
#  이곳의 한 달은 정확히 30일이니, 약 4주 뒤면 다시 미궁에 들어가야 한다는 뜻."
DAYS_PER_MONTH: int = 30

# ★ HP/SP 회복 (★ 본문 X 추측, 후속 본문 발견 시 보강).
# 100 HP 본격 10일 본격 본격 full recovery (★ 30일 본격 본격 본격).
HP_RECOVERY_PER_DAY: int = 10
SP_RECOVERY_PER_DAY: int = 5


def execute_wait_in_village(
    actor_name: str,
    party: list[Character],
    world: WorldState,
) -> TurnResult:
    """마을 본격 1일 진행 + HP/SP 회복 (★ Phase 9 — 19화 정합).

    본인 답 정합:
    - HP/SP 30일 본격 회복 (★ 본격 본격 본격 본격)
    - 살아남은 멤버만 회복 (★ 죽은 멤버 영구)
    - 30일 wrap → month++

    실패:
    - simulation_status != TIME_LIMIT_REACHED (★ 마을 본격 본격 본격)

    ★ 본 commit (option 3 additive) — sim_runner 본격 TIME_LIMIT_REACHED 본격
    종료 본격 본격, 본 handler 본격 직접 호출 본격 본격 (★ 후속 commit 본격
    sim_runner loop cascade 본격).
    """
    if world.simulation_status != SimulationStatus.TIME_LIMIT_REACHED:
        return TurnResult(
            success=False,
            action_type="wait_in_village",
            message=(
                f"마을 turn loop 본격 X "
                f"(status={world.simulation_status.value})."
            ),
        )

    # 1일 진행 (★ wrap at DAYS_PER_MONTH)
    world.day_in_month += 1
    if world.day_in_month > DAYS_PER_MONTH:
        world.day_in_month = 1
        world.month_number += 1

    # HP/SP 회복 + 부상 회복 (★ 살아남은 멤버만)
    side_effects: list[str] = [
        f"day_advanced=month_{world.month_number}_day_{world.day_in_month}",
    ]
    for member in party:
        if not member.is_alive():
            continue  # ★ 죽은 멤버 영구 (★ 본인 답)
        old_hp = member.hp
        member.hp = min(member.hp_max, member.hp + HP_RECOVERY_PER_DAY)
        hp_gain = member.hp - old_hp
        old_sp = member.soul_power
        member.soul_power = min(
            member.soul_power_max,
            member.soul_power + SP_RECOVERY_PER_DAY,
        )
        sp_gain = member.soul_power - old_sp
        if hp_gain > 0:
            side_effects.append(f"hp_gain={member.name}:+{hp_gain}")
        if sp_gain > 0:
            side_effects.append(f"sp_gain={member.name}:+{sp_gain}")

        # ★ Phase 9.3 — 부상 자연 회복 mutation (★ frozen Injury 새 instance).
        # ★ Phase 9.6 — scar=True injury 회복 시 영구 흉터 누적 (★ 25화 정합).
        if member.injuries:
            remaining: list[Injury] = []
            for inj in member.injuries:
                new_days = inj.recovery_days - 1
                if new_days <= 0:
                    side_effects.append(
                        f"injury_healed={member.name}:"
                        f"{inj.body_part}_{inj.severity}"
                    )
                    if inj.scar:
                        new_scar = Scar(
                            body_part=inj.body_part,
                            origin_severity=inj.severity,
                        )
                        member.scars.append(new_scar)
                        side_effects.append(
                            f"scar_acquired={member.name}:"
                            f"{new_scar.body_part}_{new_scar.origin_severity}"
                        )
                else:
                    remaining.append(
                        Injury(
                            severity=inj.severity,
                            body_part=inj.body_part,
                            recovery_days=new_days,
                            scar=inj.scar,
                        )
                    )
            member.injuries[:] = remaining

    return TurnResult(
        success=True,
        action_type="wait_in_village",
        message=(
            f"마을에서 하루를 보냈다. "
            f"({world.month_number}월 {world.day_in_month}일)"
        ),
        side_effects=side_effects,
    )


# ─── Phase 9 rift-cooldown — A-1 spec 본격 실작동 mechanism ───
#
# 본문 정합 (★ docs/floor1_rifts_spec.md A-1):
# - 27화: 최소 3주기 / 5~6주기 본격 / 맥시멈 8주기
# - 28화: 통계학적 trigger (★ 본인 가설 '랜덤처럼 보여도 트리거')
# - 1 주기 = 1 month (★ WorldState.month_number, 19화 30일 정합)


def _eligible_rifts_for_period(
    floor_def: FloorDefinition,
    world: WorldState,
    current_period: int,
) -> list[str]:
    """현재 period 본격 자연 활성 가능 균열 본격 list.

    Eligibility:
    - cleared_rifts 제외 (★ 본 commit 본격 single-cycle reset 본격 X)
    - active_rifts 제외 (★ 이미 활성 본격 X)
    - last_opened X (★ 본격 본격 본격) → eligible
    - elapsed >= cooldown_min_periods → eligible
    """
    eligible: list[str] = []
    for rift in floor_def.rifts:
        if rift.rift_id in world.cleared_rifts:
            continue
        if rift.rift_id in world.active_rifts:
            continue
        last_opened = world.rift_last_opened_periods.get(rift.rift_id)
        if last_opened is None:
            eligible.append(rift.rift_id)
            continue
        elapsed = current_period - last_opened
        if elapsed >= rift.cooldown_min_periods:
            eligible.append(rift.rift_id)
    return eligible


def _select_rift_to_activate(
    rift_ids: list[str],
    floor_def: FloorDefinition,
    world: WorldState,
    current_period: int,
    rng: random.Random,
) -> str | None:
    """본문 정합 본격 활성 본격.

    27화 정합:
    - elapsed ∈ typical_range → 본문 정합 zone → candidate
    - elapsed >= max → forced (★ 맥시멈 본격)
    - first-time (last_opened X) → typical_range 본격 본격 본격 candidate
      (★ 28화 본인 가설 '랜덤처럼 보여도 트리거' 정합)
    - elapsed < typical low 본격 X → 본격 본격 X
    """
    candidates: list[str] = []
    rift_by_id = {r.rift_id: r for r in floor_def.rifts}
    for rift_id in rift_ids:
        rift = rift_by_id.get(rift_id)
        if rift is None:
            continue
        last_opened = world.rift_last_opened_periods.get(rift_id)
        lo, hi = rift.cooldown_typical_range
        if last_opened is None:
            # 본격 활성 X — typical_range 본격 본격 본격 candidate
            # (★ 본인 가설: 사실상 typical_range probabilistic trigger)
            candidates.append(rift_id)
            continue
        elapsed = current_period - last_opened
        if lo <= elapsed <= hi:
            candidates.append(rift_id)
        elif elapsed >= rift.cooldown_max_periods:
            candidates.append(rift_id)
    if not candidates:
        return None
    return rng.choice(candidates)


def activate_natural_rifts(
    world: WorldState,
    floor_def: FloorDefinition,
    rng: random.Random | None = None,
) -> list[str]:
    """현재 period 본격 자연 활성 균열 본격 mutation.

    1차 자료 (★ A-1 spec):
    - 27화: 5~6주기 본격 활성
    - 28화: 통계학적 trigger (★ 본인 가설 정합)
    - 의도적 활성 (★ A3 offer_to_stone) 본격 별도 path
    """
    if rng is None:
        rng = random.Random()

    current_period = world.month_number
    eligible = _eligible_rifts_for_period(
        floor_def, world, current_period
    )
    if not eligible:
        return []

    selected = _select_rift_to_activate(
        eligible, floor_def, world, current_period, rng
    )
    if selected is None:
        return []

    world.active_rifts.append(selected)
    world.rift_last_opened_periods[selected] = current_period
    return [selected]


def execute_enter_dungeon(
    actor_name: str,
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """매월 1일 자정 1층 재진입 (★ Phase 9 — 19화 본문 정합).

    본문 19화: "매월 1일이 되는 자정에는 미궁이 열린다".

    본인 답 정합:
    - 항상 1층 재진입 (★ 2층 본격 X)
    - inventory / stone / 동료 본격 보존
    - 균열 상태 reset (★ 본 commit 단순 — 후속 cooldown 본격)

    실패:
    - simulation_status != TIME_LIMIT_REACHED
    - day_in_month != 1
    - 살아남은 멤버 0 (★ 전멸 시 PARTY_DEFEATED 본격 본격)
    """
    if world.simulation_status != SimulationStatus.TIME_LIMIT_REACHED:
        return TurnResult(
            success=False,
            action_type="enter_dungeon",
            message=(
                f"마을 turn loop 본격 X "
                f"(status={world.simulation_status.value})."
            ),
        )

    if world.day_in_month != 1:
        return TurnResult(
            success=False,
            action_type="enter_dungeon",
            message=(
                f"미궁은 매월 1일 자정에만 열린다 (★ 19화). "
                f"현재: {world.month_number}월 {world.day_in_month}일."
            ),
        )

    alive = [m for m in party if m.is_alive()]
    if not alive:
        return TurnResult(
            success=False,
            action_type="enter_dungeon",
            message="살아남은 탐사대원 X — 진입 불가.",
        )

    # 1층 재진입 (★ 본인 답: 항상 1층)
    location.realm = Realm.DUNGEON
    location.floor = 1
    location.sub_area = "진입점"  # ★ floor1.py _ENTRANCE.name
    location.city_id = None
    location.rift_id = None
    location.rift_sub_area = None
    location.rift_is_variant = False
    location.has_light = False
    location.visibility_meters = 10

    # simulation 재시작
    world.simulation_status = SimulationStatus.ACTIVE
    world.simulation_over_reason = None
    world.simulation_over_turn = None
    world.hours_in_dungeon = 0

    # 균열 active 상태 reset (★ rift_last_opened_periods 본격 보존 — cooldown 본격)
    world.active_rifts = []
    world.active_boss_encounter = None

    # ★ Phase 9 rift-cooldown — 자연 활성 trigger (★ A-1 spec 본격 실작동)
    activated = activate_natural_rifts(world, get_floor1_definition())

    side_effects = [
        f"dungeon_re_entered=month_{world.month_number}",
        "floor_transition=1",
    ]
    message = (
        f"{world.month_number}월 1일 자정. "
        f"미궁이 다시 열렸다. 1층 진입점에 도착."
    )
    if activated:
        for rift_id in activated:
            side_effects.append(f"rift_activated={rift_id}")
        message += f" 균열 본격 활성: {', '.join(activated)}."

    return TurnResult(
        success=True,
        action_type="enter_dungeon",
        message=message,
        side_effects=side_effects,
    )


# ─── Phase 9.5 — 삼신교 신전 부상 치료 (★ 268/55/72화 본문 정합) ───

# severity별 치료 비용 (★ 본문 X 추측 — 후속 발견 시 보강).
HEAL_COST_PER_SEVERITY: dict[str, int] = {
    InjurySeverity.SCRATCH.value: 50,
    InjurySeverity.MINOR.value: 200,
    InjurySeverity.MAJOR.value: 1000,
    InjurySeverity.CRITICAL.value: 5000,
}


def execute_heal_at_temple(
    actor_name: str,
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """삼신교 신전 본격 부상 치료 (★ Phase 9.5 — 268/55/72화 정합).

    조건:
    - realm=CITY + sub_area=temple
    - 신 본격 race 거절 본격 X (★ 268화 바바리안-토베라 ⭐)
    - actor 본격 부상 본격
    - stone 비용 충분 (★ HEAL_COST_PER_SEVERITY)

    Mutation (★ atomic — 비용 부족 시 변경 X):
    - 모든 injury 제거 (★ batch)
    - stone 차감
    - side_effects: temple_healed / stone_paid / injury_healed_by_temple
    """
    # 1. 위치 검증
    if location.realm != Realm.CITY:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message="신전 본격 마을 본격 본격 작동.",
        )

    if location.sub_area is None:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message="sub_area X — 신전 위치 본격 X.",
        )

    deity = get_deity_by_sub_area(location.sub_area)
    if deity is None:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message=f"신전 위치 X (★ 현재: {location.sub_area}).",
        )

    # 2. actor 본격
    actor = next((m for m in party if m.name == actor_name), None)
    if actor is None:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message=f"{actor_name} 본격 본격 본격 X.",
        )

    # 3. race 거절 본격 (★ 268화 토베라-바바리안)
    if actor.race.value in deity.refuses_races:
        priest_part = (
            f"{deity.priest_rank} {deity.canonical_priest_name}"
            if deity.canonical_priest_name
            else deity.priest_rank
        )
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message=(
                f"{deity.temple_name}의 {priest_part}가 거절했다. "
                f"{deity.deity_name} 본격 {actor.race.value} "
                f"본격 신성력 X (★ 268화 본문 규율)."
            ),
        )

    # 4. 부상 본격
    if not actor.injuries:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message=f"{actor_name} 본격 본격 본격 부상 X.",
        )

    # 5. 비용 계산
    total_cost = sum(
        HEAL_COST_PER_SEVERITY.get(inj.severity, 0)
        for inj in actor.injuries
    )
    if actor.stone < total_cost:
        return TurnResult(
            success=False,
            action_type="heal_at_temple",
            message=(
                f"치료 비용 부족 ({actor.stone}/{total_cost} 스톤)."
            ),
        )

    # 6. mutation (★ atomic)
    healed = list(actor.injuries)
    actor.injuries.clear()
    actor.stone -= total_cost

    # ★ Phase 9.6 — scar=True injury 본격 영구 흉터 transition (★ 25화 정합)
    new_scars: list[Scar] = []
    for inj in healed:
        if inj.scar:
            scar = Scar(
                body_part=inj.body_part,
                origin_severity=inj.severity,
            )
            actor.scars.append(scar)
            new_scars.append(scar)

    side_effects = [
        f"temple_healed={actor_name}:{deity.deity_id}:{len(healed)}",
        f"stone_paid={actor_name}:-{total_cost}",
    ]
    for inj in healed:
        side_effects.append(
            f"injury_healed_by_temple={actor_name}:"
            f"{inj.body_part}_{inj.severity}"
        )
    for scar in new_scars:
        side_effects.append(
            f"scar_acquired={actor_name}:"
            f"{scar.body_part}_{scar.origin_severity}"
        )

    message = (
        f"{deity.temple_name}에서 {deity.priest_rank}가 "
        f"{actor_name} 본격 부상 {len(healed)}개를 치료했다. "
        f"-{total_cost} 스톤."
    )
    if new_scars:
        message += f" (★ 흉터 {len(new_scars)}개 영구 남음)"

    return TurnResult(
        success=True,
        action_type="heal_at_temple",
        message=message,
        side_effects=side_effects,
    )


# ─── Phase 9.7 — NPC 호감도 + 도서관 서적 탐지 (★ 19화 본문 정합) ───

AFFINITY_DELTA_DIALOGUE: int = 5  # ★ 추측 (본문 X — 후속 발견 시 보강)
AFFINITY_MAX: int = 100  # ★ 643화 본문 cap
LIBRARY_SEARCH_FEE: int = 3000  # ★ namu §4.3 본문 — 도서관 수수료 3천 스톤
LIBRARY_FREE_AFFINITY_THRESHOLD: int = 50  # ★ 본인 답 (★ 추측)
LIBRARIAN_NPC_ID: str = "ragna"  # ★ a-2 NPCDef.id


def _find_npc_in_sub_area(
    target: str | None, sub_area_id: str
) -> tuple[str, str] | None:
    """target (★ npc id 또는 name) 본격 RAPDONIA 본격 본격 sub_area 본격 NPC.

    Returns:
        (npc_id, npc_name) 본격 None.
    """
    from .cities.rapdonia import RAPDONIA

    sub = next(
        (s for s in RAPDONIA.sub_areas if s.id == sub_area_id), None
    )
    if sub is None or not sub.npc_ids:
        return None

    if not target:
        return None

    for npc_id in sub.npc_ids:
        npc = next((n for n in RAPDONIA.npcs if n.id == npc_id), None)
        if npc is None:
            continue
        if npc.id == target or npc.name == target:
            return (npc.id, npc.name)
    return None


def execute_dialogue(
    actor_name: str,
    target: str | None,
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """NPC 본격 대화 → 호감도 +5 (★ Phase 9.7 minimal).

    조건:
    - realm=CITY + 현재 sub_area 본격 NPC 본격
    - target 본격 NPC id 또는 한국어 name 본격 본격 본격

    Mutation:
    - world.npc_affinities[npc_id] += AFFINITY_DELTA_DIALOGUE (★ cap 100)
    """
    if location.realm != Realm.CITY:
        return TurnResult(
            success=False,
            action_type="dialogue",
            message="대화는 마을 본격.",
        )
    if location.sub_area is None:
        return TurnResult(
            success=False,
            action_type="dialogue",
            message="sub_area X — 대화 본격 X.",
        )

    found = _find_npc_in_sub_area(target, location.sub_area)
    if found is None:
        return TurnResult(
            success=False,
            action_type="dialogue",
            message=f"본 위치 본격 '{target}' NPC X.",
        )
    npc_id, npc_name = found

    # actor 본격 검증 (★ 본 commit 본격 본격 X — 본격 본격)
    actor = next((m for m in party if m.name == actor_name), None)
    if actor is None:
        return TurnResult(
            success=False,
            action_type="dialogue",
            message=f"{actor_name} 본격 본격 X.",
        )

    current = world.npc_affinities.get(npc_id, 0)
    new_value = min(AFFINITY_MAX, current + AFFINITY_DELTA_DIALOGUE)
    world.npc_affinities[npc_id] = new_value

    return TurnResult(
        success=True,
        action_type="dialogue",
        message=(
            f"{actor_name}이(가) {npc_name}와(과) 대화했다. "
            f"호감도 {current} → {new_value}."
        ),
        side_effects=[
            f"affinity_changed={npc_id}:{current}->{new_value}",
        ],
    )


def execute_library_search(
    actor_name: str,
    target: str | None,
    party: list[Character],
    world: WorldState,
    location: Location,
) -> TurnResult:
    """도서관 서적 탐지 마법 — 19화 '파르시티에브' 본문 정합.

    조건:
    - realm=CITY + sub_area=central_library
    - target 본격 검색 키워드 (★ 19화: 키워드 본격 책 이끌림)
    - 라그나 호감도 < threshold 본격 stone 본격 (★ namu §4.3 3천)
    - 라그나 호감도 ≥ threshold 본격 무료 (★ 본인 답 — 친해진 본격)

    본 commit 본격 X (★ 후속):
    - Book schema (★ target → book lookup)
    - 책 효과 mechanism (★ 9.8 본격)
    """
    if location.realm != Realm.CITY:
        return TurnResult(
            success=False,
            action_type="library_search",
            message="도서관은 마을 본격.",
        )
    if location.sub_area != "central_library":
        return TurnResult(
            success=False,
            action_type="library_search",
            message=(
                "중앙 도서관 본격 본격 본격 (★ central_library)."
            ),
        )
    if not target:
        return TurnResult(
            success=False,
            action_type="library_search",
            message="검색 키워드 본격 본격.",
        )

    actor = next((m for m in party if m.name == actor_name), None)
    if actor is None:
        return TurnResult(
            success=False,
            action_type="library_search",
            message=f"{actor_name} 본격 본격 X.",
        )

    affinity = world.npc_affinities.get(LIBRARIAN_NPC_ID, 0)
    free = affinity >= LIBRARY_FREE_AFFINITY_THRESHOLD

    if not free:
        if actor.stone < LIBRARY_SEARCH_FEE:
            return TurnResult(
                success=False,
                action_type="library_search",
                message=(
                    f"수수료 부족 "
                    f"({actor.stone}/{LIBRARY_SEARCH_FEE} 스톤). "
                    f"라그나 호감도 ≥ "
                    f"{LIBRARY_FREE_AFFINITY_THRESHOLD} 시 무료."
                ),
            )
        actor.stone -= LIBRARY_SEARCH_FEE

    msg = (
        f"라그나가 '파르시티에브'를 읊조렸다. "
        f"'{target}' 본격 본격 책으로 이끌림이 발생한다."
    )
    side_effects = [f"library_search={actor_name}:{target}"]
    if free:
        msg += f" (★ 호감도 {affinity} — 수수료 면제)"
    else:
        msg += f" -{LIBRARY_SEARCH_FEE} 스톤."
        side_effects.append(
            f"stone_paid={actor_name}:-{LIBRARY_SEARCH_FEE}"
        )

    return TurnResult(
        success=True,
        action_type="library_search",
        message=msg,
        side_effects=side_effects,
    )


# ─── Phase 9.9-a — 길드 모집 minimal (★ 본인 답 / 6화 mention) ───

# 본 commit 추측 (★ 본문 X — 후속 본문 발견 시 보강).
RECRUIT_BASE_COST: int = 5000  # ★ 신참 모집 stone 비용 (★ namu §7.1 본격 X)

# 본 commit 모집 가능 6 종족 (★ Race enum value 정합 — 43화 본문).
GUILD_RECRUITABLE_RACES: tuple[str, ...] = (
    "인간",
    "드워프",
    "수인",
    "요정",
    "바바리안",
    "용인족",
)

# ─── Phase 9.9-c — 종족 가중치 + 상성 + 호감도 boost (★ 본문 strict) ───

# base 가중치 (★ 본인 답 default — 본문 수치 명시 X 추측).
# 123화: 용인족 캐릭터 선택 차단 (★ 매우 희귀 = 1).
# 123화: 바바리안 채팅방 0명 (★ 희귀 = 4).
RACE_BASE_WEIGHT: dict[str, int] = {
    "인간": 50,
    "드워프": 15,
    "수인": 15,
    "요정": 15,
    "바바리안": 4,
    "용인족": 1,
}

# 종족 상성 (★ 본문 strict — 추측 회피).
# 9화 본문: 바바리안 ↔ 요정 적대 (★ 양방향).
# 44/97/119화: 인간 → 바바리안 차별 (★ 본인 답 단방향).
HOSTILE_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("바바리안", "요정"),
        ("요정", "바바리안"),
        ("인간", "바바리안"),  # ★ 단방향 (★ 본인 답)
    }
)

# 8화 본문: '바바리안만큼 호방한 드워프' — 친화 (★ 양방향).
FRIENDLY_PAIRS: frozenset[tuple[str, str]] = frozenset(
    {
        ("바바리안", "드워프"),
        ("드워프", "바바리안"),
    }
)

SAME_RACE_MULTIPLIER: float = 2.0
FRIENDLY_MULTIPLIER: float = 1.5
HOSTILE_MULTIPLIER: float = 0.3
NEUTRAL_MULTIPLIER: float = 1.0

# 호감도 boost (★ 본인 답 default — 본문 X 추측).
AFFINITY_BOOST_RARE_THRESHOLD: int = 50
AFFINITY_BOOST_UNCOMMON_THRESHOLD: int = 25
RARE_RACE_AFFINITY_MULTIPLIER: float = 10.0  # ★ 용인족 ×10 @ 50
UNCOMMON_RACE_AFFINITY_MULTIPLIER: float = 2.0  # ★ 바바리안/용인족 ×2 @ 25

GUILD_CLERK_NPC_ID: str = "frail_guild_clerk"


def _race_relation_multiplier(
    actor_race: str, target_race: str
) -> float:
    """종족 상성 multiplier (★ 본문 strict 정합).

    - 같은 종족 → ×2 (★ 본인 답)
    - 친화 → ×1.5 (★ 8화 바바리안-드워프 호방)
    - 적대 → ×0.3 (★ 9화 바바리안-요정 양방향, 44/97/119화 인간→바바리안 단방향)
    - 중립 → ×1.0
    """
    if actor_race == target_race:
        return SAME_RACE_MULTIPLIER
    if (actor_race, target_race) in HOSTILE_PAIRS:
        return HOSTILE_MULTIPLIER
    if (actor_race, target_race) in FRIENDLY_PAIRS:
        return FRIENDLY_MULTIPLIER
    return NEUTRAL_MULTIPLIER


def _affinity_boost_multiplier(
    target_race: str, affinity: int
) -> float:
    """길드 NPC 호감도 본격 희귀 종족 boost (★ 본인 답).

    - affinity ≥ 50 + 용인족 → ×10
    - affinity ≥ 25 + 바바리안/용인족 → ×2
    - 그 외 → ×1.0
    """
    if (
        affinity >= AFFINITY_BOOST_RARE_THRESHOLD
        and target_race == "용인족"
    ):
        return RARE_RACE_AFFINITY_MULTIPLIER
    if (
        affinity >= AFFINITY_BOOST_UNCOMMON_THRESHOLD
        and target_race in ("바바리안", "용인족")
    ):
        return UNCOMMON_RACE_AFFINITY_MULTIPLIER
    return 1.0


def _compute_race_weights(
    actor_race: str, guild_clerk_affinity: int
) -> dict[str, float]:
    """본인 종족 + 호감도 본격 최종 가중치."""
    weights: dict[str, float] = {}
    for race in GUILD_RECRUITABLE_RACES:
        base = float(RACE_BASE_WEIGHT[race])
        relation = _race_relation_multiplier(actor_race, race)
        boost = _affinity_boost_multiplier(race, guild_clerk_affinity)
        weights[race] = base * relation * boost
    return weights


def _weighted_random_race(
    weights: dict[str, float], rng: random.Random
) -> str:
    """가중치 기반 random 종족 선택."""
    total = sum(weights.values())
    if total <= 0:
        return "인간"  # ★ fallback
    r = rng.uniform(0.0, total)
    cumulative = 0.0
    for race, w in weights.items():
        cumulative += w
        if r <= cumulative:
            return race
    return next(iter(weights))


def _create_recruit_character(
    actor_race: str,
    guild_clerk_affinity: int,
    rng: random.Random,
) -> Character:
    """길드 모집 신참 (★ Phase 9.9-c 가중치 + 9.9-b grade/class).

    - 본인 종족 + 호감도 본격 가중치 random 종족 선택
    - level 1 / grade 1 / class WARRIOR (★ 5화 본문: 신참 = warrior)
    """
    weights = _compute_race_weights(actor_race, guild_clerk_affinity)
    race_value = _weighted_random_race(weights, rng)
    race_enum = next(r for r in Race if r.value == race_value)
    name = f"{race_value} 신참 #{rng.randint(1000, 9999)}"
    return Character(
        name=name,
        race=race_enum,
        hp=100,
        hp_max=100,
        level=1,
        experience=0,
        soul_power=20,
        soul_power_max=20,
        stone=0,
        grade=1,
        class_type=ClassType.WARRIOR.value,
    )


def execute_recruit_from_guild(
    actor_name: str,
    party: list[Character],
    world: WorldState,
    location: Location,
    rng: random.Random | None = None,
) -> TurnResult:
    """길드 신참 모험가 모집 (★ Phase 9.9-a minimal).

    조건:
    - realm=CITY + sub_area=explorer_guild_branch
    - 빈자리 (★ len(party) < world.max_party_members)
    - actor.stone ≥ RECRUIT_BASE_COST

    Mutation (★ atomic):
    - party.append(new_member)
    - actor.stone -= RECRUIT_BASE_COST

    본 commit 본격 X (★ 후속):
    - 9.9-b: 등급 + 직업
    - 9.9-c: 종족 가중치 + 호감도
    - 9.9-d: 분배 비율
    """
    if location.realm != Realm.CITY:
        return TurnResult(
            success=False,
            action_type="recruit_from_guild",
            message="길드는 마을 본격.",
        )
    if location.sub_area != "explorer_guild_branch":
        return TurnResult(
            success=False,
            action_type="recruit_from_guild",
            message="탐험가 길드 지부 본격 본격 본격.",
        )

    actor = next((m for m in party if m.name == actor_name), None)
    if actor is None:
        return TurnResult(
            success=False,
            action_type="recruit_from_guild",
            message=f"{actor_name} 본격 본격 X.",
        )

    if len(party) >= world.max_party_members:
        return TurnResult(
            success=False,
            action_type="recruit_from_guild",
            message=(
                f"파티 정원 만석 "
                f"({len(party)}/{world.max_party_members})."
            ),
        )

    if actor.stone < RECRUIT_BASE_COST:
        return TurnResult(
            success=False,
            action_type="recruit_from_guild",
            message=(
                f"모집 비용 부족 "
                f"({actor.stone}/{RECRUIT_BASE_COST} 스톤)."
            ),
        )

    # mutation (★ atomic)
    if rng is None:
        rng = random.Random()
    # ★ Phase 9.9-c — actor 종족 + 길드 호감도 본격 가중치
    guild_clerk_affinity = world.npc_affinities.get(GUILD_CLERK_NPC_ID, 0)
    new_member = _create_recruit_character(
        actor.race.value, guild_clerk_affinity, rng
    )
    party.append(new_member)
    world.party_members.append(new_member.name)
    actor.stone -= RECRUIT_BASE_COST

    return TurnResult(
        success=True,
        action_type="recruit_from_guild",
        message=(
            f"탐험가 길드에서 {new_member.name}({new_member.race.value}, "
            f"Lv {new_member.level})을(를) 모집했다. "
            f"-{RECRUIT_BASE_COST} 스톤. "
            f"파티 {len(party)}/{world.max_party_members}."
        ),
        side_effects=[
            f"member_recruited={new_member.name}:{new_member.race.value}",
            f"stone_paid={actor_name}:-{RECRUIT_BASE_COST}",
        ],
    )
