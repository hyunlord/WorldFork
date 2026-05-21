"""Phase D step 3/6a/6b — 31 PlayerActionType deterministic handler.

LLM 호출 없음 — template narrative + state mutate.
27B narrative는 fallback path(freeform_handler)에서 담당.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from service.canon.context import get_entity_index, get_item_registry
from service.canon.effects import classify_skill, essence_to_slot, parse_essence_abilities
from service.sim.action_context import ActionContext, ActionResult
from service.sim.action_helpers import (
    extract_direction,
    extract_item_from_input,
    extract_item_from_inventory,
    get_entity_name,
    get_first_enemy,
    get_first_npc,
)
from service.sim.combat import (
    CombatTurnLog,
    cleanup_dead_enemies,
    execute_enemy_turn,
    execute_player_attack,
    find_target_index,
)
from service.sim.dungeon_zones import Direction, get_adjacent_zone, get_zone_info
from service.sim.enemy import Enemy, enemy_from_dict, enemy_to_dict
from service.sim.equipment import equipment_to_dict
from service.sim.player_state import slot_to_dict
from service.sim.status import deserialize_status, serialize_status
from service.sim.types import PlayerActionType
from service.sim.xp_curve import (
    compute_level_for_xp,
    compute_xp_grant,
    soul_power_gain_on_level_up,
)

_Handler = Callable[[ActionContext], Awaitable[ActionResult]]


# ─── 빛 / 탐색 ───


async def handle_activate_light(ctx: ActionContext) -> ActionResult:
    has_torch = any("횃불" in i or "torch" in i.lower() for i in ctx.inventory)
    if not has_torch:
        return ActionResult(
            narrative="비요른은 주머니를 더듬었으나 횃불을 찾지 못했습니다.",
            success=False,
            fail_reason="no_torch",
            time_advance=0,
        )
    return ActionResult(
        narrative="비요른은 부싯돌을 두드려 횃불에 불을 붙입니다. 어둠이 물러납니다.",
        time_advance=0,
    )


async def handle_explore(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative=(
            f"비요른은 {ctx.location}을 천천히 살핍니다."
            " 익숙해진 눈이 어둠 속에서 세세한 것들을 포착합니다."
        ),
        time_advance=2,
    )


async def handle_library_search(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative=(
            "비요른은 도서관 서가를 따라 걸으며 낯선 문자들을 훑어봅니다."
            " 파르시티에브 관련 기록이 눈에 들어옵니다."
        ),
        time_advance=2,
    )


# ─── 이동 ───

_KOR_TO_4WAY: dict[str, Direction] = {
    "북": "north", "남": "south", "동": "east", "서": "west",
}

_DIRECTION_KOR: dict[Direction, str] = {
    "north": "북쪽", "south": "남쪽", "east": "동쪽", "west": "서쪽",
}


def _extract_direction_4way(
    text: str, entities_direction: str | None
) -> Direction | None:
    """entities 우선, fallback → extract_direction → 4방향 변환."""
    if entities_direction in ("north", "south", "east", "west"):
        return entities_direction  # type: ignore[return-value]
    kor = extract_direction(text)
    if kor is None:
        return None
    return _KOR_TO_4WAY.get(kor)


def _lighting_narrative(zone_name: str, floor: int) -> str:
    """zone lighting 기반 어둠 묘사 suffix."""
    info = get_zone_info(zone_name, floor)
    if info is None:
        return ""
    if info.lighting == "very_dark":
        return " 빛이 사라졌습니다. 한 발 앞도 보이지 않습니다."
    if info.lighting == "dark":
        return " 어둠이 짙어졌습니다. 발밑을 주의해야 합니다."
    if info.lighting == "bright":
        return " 수정 빛이 은은하게 길을 비춥니다."
    return ""


async def handle_move(ctx: ActionContext) -> ActionResult:
    entities_dir = (
        ctx.extracted_entities.direction if ctx.extracted_entities else None
    )
    direction = _extract_direction_4way(ctx.user_input, entities_dir)
    if direction is None:
        return ActionResult(
            narrative="어느 방향으로 이동할지 명확하지 않습니다.",
            success=False,
            fail_reason="no_direction",
            time_advance=0,
        )

    dir_kor = _DIRECTION_KOR[direction]

    if ctx.floor_number == 0:
        return ActionResult(
            narrative=f"비요른은 {dir_kor}으로 발걸음을 옮깁니다.",
            time_advance=1,
        )

    next_zone = get_adjacent_zone(ctx.location, direction, ctx.floor_number)
    if next_zone is None:
        return ActionResult(
            narrative=f"{dir_kor}으로는 더 나아갈 수 없습니다.",
            success=False,
            fail_reason="no_adjacent_zone",
            time_advance=0,
        )

    lighting_note = _lighting_narrative(next_zone, ctx.floor_number)
    zone_info = get_zone_info(next_zone, ctx.floor_number)
    hint = zone_info.description_hint if zone_info else ""

    narrative = f"비요른은 {dir_kor}으로 나아가 {next_zone}에 들어섭니다."
    if hint:
        narrative += f" {hint}"
    if lighting_note:
        narrative += lighting_note

    return ActionResult(
        narrative=narrative,
        location=next_zone,
        time_advance=1,
    )


async def handle_enter_rift(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative=(
            "비요른은 숨을 한 번 들이켜고 균열 속으로 몸을 밀어 넣습니다."
            " 공기가 뒤틀리며 시야가 바뀝니다."
        ),
        location=f"{ctx.location} (균열 내부)",
        time_advance=1,
    )


async def handle_exit_rift(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative="비요른은 균열 경계를 되짚어 빠져나옵니다. 바깥의 냉기가 이마에 와 닿습니다.",
        location=(
            ctx.location.replace(" (균열 내부)", "")
            if "(균열 내부)" in ctx.location
            else ctx.location
        ),
        time_advance=1,
    )


async def handle_enter_next_floor(ctx: ActionContext) -> ActionResult:
    next_floor = ctx.floor_number + 1
    if next_floor > 10:
        return ActionResult(
            narrative="더 깊은 층으로 가는 길은 보이지 않습니다.",
            success=False,
            fail_reason="max_floor",
            time_advance=0,
        )
    return ActionResult(
        narrative=(
            "비요른은 층계를 내려가 다음 층으로 발을 딛습니다."
            " 더 짙은 어둠이 앞을 막아섭니다."
        ),
        location=f"{next_floor}층 입구",
        floor_change=1,
        time_advance=1,
    )


async def handle_exit_to_prev_floor(ctx: ActionContext) -> ActionResult:
    if ctx.floor_number <= 0:
        return ActionResult(
            narrative="이미 마을에 있습니다.",
            success=False,
            fail_reason="already_outside",
            time_advance=0,
        )
    prev_floor = ctx.floor_number - 1
    if prev_floor == 0:
        return ActionResult(
            narrative="비요른은 발걸음을 돌려 마을로 복귀합니다. 햇살이 눈을 찌릅니다.",
            location="마을",
            floor_change=-1,
            hours_in_dungeon_reset=True,
            time_advance=1,
        )
    return ActionResult(
        narrative="비요른은 발걸음을 돌려 이전 층으로 복귀합니다.",
        location=f"{prev_floor}층 입구",
        floor_change=-1,
        time_advance=1,
    )


async def handle_enter_dungeon(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative="자정이 지났습니다. 비요른은 던전 1층 입구 앞에 섰습니다. 새 달의 시작입니다.",
        location="던전 1층",
        floor_change=1,
        hours_in_dungeon_reset=True,
        time_advance=1,
    )


# ─── 전투 helpers ───


def _compute_player_attack(ctx: ActionContext) -> int:
    """base attack + 인벤토리 정수 abilities + active skill bonus."""
    base = 10
    index = get_entity_index()
    if index is None:
        return base

    bonus = 0
    for item in ctx.inventory:
        ref = index.lookup_by_name(item)
        if ref is None or ref.entity_type != "essence":
            continue
        raw = index.get_raw_essence(item)
        if raw is None:
            continue
        abilities_raw = raw.get("abilities", {})
        if not isinstance(abilities_raw, dict):
            continue
        effects = parse_essence_abilities(abilities_raw)
        bonus += effects.get("attack_bonus", 0)
        bonus += effects.get("strength", 0)
        skills_raw = raw.get("skills_granted")
        if isinstance(skills_raw, list):
            for skill in skills_raw:
                if classify_skill(str(skill)) == "active":
                    bonus += 2
    return base + bonus


def _compute_player_agility(ctx: ActionContext) -> int:
    """base agility + 인벤토리 정수 agility stat."""
    base = 5
    index = get_entity_index()
    if index is None:
        return base

    bonus = 0
    for item in ctx.inventory:
        ref = index.lookup_by_name(item)
        if ref is None or ref.entity_type != "essence":
            continue
        raw = index.get_raw_essence(item)
        if raw is None:
            continue
        abilities_raw = raw.get("abilities", {})
        if not isinstance(abilities_raw, dict):
            continue
        effects = parse_essence_abilities(abilities_raw)
        bonus += effects.get("agility", 0)
    return base + bonus


def _compute_player_defense(ctx: ActionContext) -> int:
    """base 5 + 정수 defense_bonus + 장비 defense_bonus."""
    base = 5
    bonus = 0
    index = get_entity_index()
    if index:
        for item in ctx.inventory:
            ref = index.lookup_by_name(item)
            if ref is None or ref.entity_type != "essence":
                continue
            raw = index.get_raw_essence(item)
            if raw is None:
                continue
            abilities_raw = raw.get("abilities", {})
            if not isinstance(abilities_raw, dict):
                continue
            effects = parse_essence_abilities(abilities_raw)
            bonus += effects.get("defense_bonus", 0)
    if ctx.equipment is not None:
        bonus += ctx.equipment.total_defense_bonus()
    return base + bonus


def _build_attack_narrative(
    player_log: CombatTurnLog,
    enemy_logs: list[CombatTurnLog],
    essence_drops: list[str],
    all_resolved: bool,
) -> str:
    """template 기반 전투 narrative."""
    parts: list[str] = []

    if player_log.enemy_resolved:
        parts.append(
            f"비요른은 {player_log.target_name}에게 일격을 가합니다."
            f" 쓰러지는 {player_log.target_name}에서 빛이 사그라듭니다."
        )
        for drop in essence_drops:
            parts.append(f" {drop}이(가) 바닥에 떨어집니다.")
    else:
        parts.append(
            f"비요른은 {player_log.target_name}을(를) 공격합니다."
            f" {player_log.damage_dealt} 피해를 줍니다."
        )

    for log in enemy_logs:
        if log.notes and "hp +" in log.notes:
            parts.append(f" {log.actor}이(가) 상처를 회복합니다.")
        elif log.damage_received > 0:
            parts.append(
                f" {log.actor}이(가) {log.action_name}으로 반격합니다."
                f" 비요른이 {log.damage_received} 피해를 받습니다."
            )
            if log.status_applied:
                parts.append(f" ({', '.join(log.status_applied)} 적용)")

    return "".join(parts)


# ─── 전투 ───


async def handle_attack(ctx: ActionContext) -> ActionResult:
    """multi-enemy turn loop 전투."""
    if not ctx.encounters:
        return ActionResult(
            narrative="공격할 대상이 없습니다.",
            success=False,
            fail_reason="no_target",
            time_advance=0,
        )

    enemies = [enemy_from_dict(e) for e in ctx.encounters]
    player_attack = _compute_player_attack(ctx)
    player_defense = _compute_player_defense(ctx)
    player_status = [deserialize_status(s) for s in ctx.status_effects]

    # Step 1: 플레이어 공격
    target_idx = find_target_index(enemies, ctx.user_input)
    item_pool = None
    registry = get_item_registry()
    if registry:
        item_pool = registry.all_items()
    enemies, player_log = execute_player_attack(
        enemies, target_idx, player_attack, ctx.user_input
    )

    # Step 2: 죽은 enemy 정리 + drop
    enemies, essence_drops, equipment_drops = cleanup_dead_enemies(enemies, item_pool)

    # Step 3: 남은 enemy turn
    enemy_logs: list[CombatTurnLog] = []
    hp_change = 0
    new_status = player_status
    if enemies:
        enemies, new_player_hp, new_status, enemy_logs = execute_enemy_turn(
            enemies, ctx.current_hp, ctx.max_hp, player_defense, player_status
        )
        hp_change = new_player_hp - ctx.current_hp

    all_resolved = len(enemies) == 0

    # Step 4: XP grant (★ 6d — ep_0022 first kill only)
    xp_gain = 0
    defeated_add: list[str] = []
    if player_log.enemy_resolved:
        original_target = enemy_from_dict(ctx.encounters[target_idx])
        monster_type = original_target.race or original_target.name
        is_first = monster_type not in ctx.defeated_monster_types
        modifiers: list[str] = []
        if "수호자" in original_target.name:
            modifiers.append("guardian")
        if "변이" in original_target.name or "상위" in original_target.name:
            modifiers.append("variant")
        if "계층군주" in original_target.name:
            modifiers.append("stratum_boss")
        xp_gain = compute_xp_grant(original_target.grade, is_first, modifiers)
        if is_first:
            defeated_add.append(monster_type)

    # Step 5: level up check
    level_up = False
    new_level: int | None = None
    if xp_gain > 0:
        computed = compute_level_for_xp(ctx.player_xp + xp_gain)
        if computed > ctx.player_level:
            level_up = True
            new_level = computed

    # Step 6: narrative — 27B 시도 후 template fallback
    narrative = _build_attack_narrative(player_log, enemy_logs, essence_drops, all_resolved)
    try:
        from service.sim.freeform_handler import compose_combat_narrative
        richer = await asyncio.to_thread(
            compose_combat_narrative, player_log, enemy_logs, essence_drops
        )
        if richer:
            narrative = richer
    except Exception:
        pass

    if xp_gain > 0:
        narrative += f"\n\n경험치 +{xp_gain}을 획득합니다."
    if level_up and new_level is not None:
        sp_gain = soul_power_gain_on_level_up(new_level)
        narrative += (
            f"\n\n「캐릭터의 레벨이 {new_level}로 상승했습니다.」"
            f"\n「영혼력이 +{sp_gain} 상승합니다.」"
            f"\n「최대 흡수 가능 정수가 +1 증가합니다.」"
        )

    new_encounters = [enemy_to_dict(e) for e in enemies]
    new_status_dicts: list[dict[str, object]] = [serialize_status(s) for s in new_status]

    inventory_add = list(essence_drops)
    if equipment_drops:
        for eq_dict in equipment_drops:
            name_val = eq_dict.get("name")
            if isinstance(name_val, str):
                inventory_add.append(name_val)

    return ActionResult(
        narrative=narrative,
        hp_change=hp_change,
        inventory_add=inventory_add,
        encounter_resolved=all_resolved,
        encounters_update=new_encounters if not all_resolved else None,
        status_update=new_status_dicts,
        time_advance=1,
        xp_gain=xp_gain,
        level_up=level_up,
        new_level=new_level,
        defeated_monsters_add=defeated_add,
    )


async def handle_flee(ctx: ActionContext) -> ActionResult:
    if not ctx.encounters:
        return ActionResult(
            narrative="도주할 상황이 아닙니다.",
            success=False,
            fail_reason="no_combat",
            time_advance=0,
        )

    enemy_dict = get_first_enemy(ctx.encounters)
    enemy = enemy_from_dict(enemy_dict) if enemy_dict else Enemy(
        name="적", hp=30, max_hp=30, attack=8, defense=3
    )

    agility = _compute_player_agility(ctx)
    success_rate = max(0.20, min(0.90, 0.40 + agility * 0.05 - enemy.attack * 0.02))
    succeeded = random.random() < success_rate

    if succeeded:
        return ActionResult(
            narrative=f"비요른은 {enemy.name}의 시선을 흘리며 빠르게 물러납니다.",
            encounter_resolved=True,
            time_advance=3,
        )
    return ActionResult(
        narrative=f"비요른은 도주를 시도하지만 {enemy.name}이(가) 앞을 가로막습니다.",
        success=False,
        fail_reason="flee_failed",
        time_advance=2,
    )


async def handle_equip(ctx: ActionContext) -> ActionResult:
    """inventory 아이템을 장비 slot에 착용."""
    registry = get_item_registry()
    if registry is None:
        return ActionResult(
            narrative="장비 정보를 확인할 수 없습니다.",
            success=False,
            fail_reason="no_registry",
            time_advance=0,
        )
    item_name = _find_equippable(ctx.user_input, ctx.inventory, registry)
    if item_name is None or item_name not in ctx.inventory:
        return ActionResult(
            narrative="착용할 장비를 찾을 수 없습니다.",
            success=False,
            fail_reason="no_item",
            time_advance=0,
        )
    eq = registry.lookup(item_name)
    if eq is None:
        return ActionResult(
            narrative=f"{item_name}은(는) 장비가 아닙니다.",
            success=False,
            fail_reason="not_equipment",
            time_advance=0,
        )
    return ActionResult(
        narrative=f"비요른은 {item_name}을(를) 착용합니다.",
        inventory_remove=[item_name],
        equipment_update={eq.slot.value: equipment_to_dict(eq)},
        time_advance=1,
    )


async def handle_unequip(ctx: ActionContext) -> ActionResult:
    """장비 slot에서 아이템 해제 → inventory 복귀."""
    if ctx.equipment is None:
        return ActionResult(
            narrative="착용 중인 장비가 없습니다.",
            success=False,
            fail_reason="no_equipment",
            time_advance=0,
        )
    # user_input에서 slot 이름 매칭
    for slot_name in ("weapon", "armor", "accessory"):
        piece = getattr(ctx.equipment, slot_name)
        if piece is not None and (piece.name in ctx.user_input or slot_name in ctx.user_input):
            return ActionResult(
                narrative=f"비요른은 {piece.name}을(를) 벗습니다.",
                inventory_add=[piece.name],
                equipment_update={slot_name: None},
                time_advance=1,
            )
    return ActionResult(
        narrative="해제할 장비를 찾을 수 없습니다.",
        success=False,
        fail_reason="no_match",
        time_advance=0,
    )


def _find_equippable(
    user_input: str,
    inventory: list[str],
    registry: object,
) -> str | None:
    """user_input 또는 inventory에서 장비 이름 탐색."""
    from service.canon.items import ItemRegistry
    if not isinstance(registry, ItemRegistry):
        return None
    for name in inventory:
        if name in user_input and registry.lookup(name) is not None:
            return name
    # fallback: inventory 첫 장비
    for name in inventory:
        if registry.lookup(name) is not None:
            return name
    return None


async def handle_engage_bandit(ctx: ActionContext) -> ActionResult:
    enemy = get_first_enemy(ctx.encounters)
    name = get_entity_name(enemy, "약탈자") if enemy else "약탈자"
    return ActionResult(
        narrative=f"비요른은 {name}와 정면으로 맞섭니다. 약탈자의 눈에 잠깐 당혹감이 스칩니다.",
        encounter_resolved=False,
        time_advance=1,
    )


# ─── 아이템 ───


async def handle_absorb_essence(ctx: ActionContext) -> ActionResult:
    # 흡수 대상 결정 — entity 추출 우선, 없으면 inventory 첫 번째 정수
    essence_name: str | None = None
    if ctx.extracted_entities and ctx.extracted_entities.item:
        candidate = ctx.extracted_entities.item
        if candidate in ctx.inventory:
            essence_name = candidate
    if essence_name is None:
        essence_name = next((i for i in ctx.inventory if "정수" in i), None)

    if not essence_name or essence_name not in ctx.inventory:
        return ActionResult(
            narrative="흡수할 정수가 없습니다.",
            success=False,
            fail_reason="no_essence",
            time_advance=0,
        )

    # level limit check (ep_0022: max_essences = player_level)
    if len(ctx.absorbed_essences) >= ctx.max_essences:
        return ActionResult(
            narrative=(
                f"최대 흡수 가능 정수 수({ctx.max_essences})에 도달했습니다."
                " 새 정수를 흡수하려면 기존 정수 하나를 지워야 합니다."
            ),
            success=False,
            fail_reason="essence_limit_reached",
            time_advance=0,
        )

    # canon lookup → EssenceSlot
    slot_dict: dict[str, object] | None = None
    msg_lines: list[str] = [
        f"비요른은 {essence_name}을 손에 쥡니다."
        " 차가운 빛이 피부 아래로 스며들며 새 힘이 깃듭니다.",
        f"「{essence_name}이(가) 스며듭니다.」",
    ]
    index = get_entity_index()
    if index is not None:
        raw = index.get_raw_essence(essence_name)
        if raw is not None and isinstance(raw, dict):
            slot = essence_to_slot(raw)
            slot_dict = slot_to_dict(slot)
            for stat, delta in slot.stat_bundle.items():
                sign = "+" if delta >= 0 else ""
                action = "상승" if delta >= 0 else "하락"
                msg_lines.append(f"「{stat}이(가) {sign}{delta} {action}합니다.」")

    if slot_dict is None:
        from service.sim.player_state import EssenceSlot
        slot_dict = slot_to_dict(EssenceSlot(essence_name=essence_name))

    return ActionResult(
        narrative="\n".join(msg_lines),
        inventory_remove=[essence_name],
        time_advance=1,
        essence_slot_add=slot_dict,
    )


async def handle_remove_essence(ctx: ActionContext) -> ActionResult:
    """정수 제거 — EssenceSlot stat 역적용 (ep_0337 정합)."""
    essence_name: str | None = (
        ctx.extracted_entities.item
        if ctx.extracted_entities and ctx.extracted_entities.item
        else None
    )
    if not essence_name:
        return ActionResult(
            narrative="어떤 정수를 제거할지 명확하지 않습니다.",
            success=False,
            fail_reason="no_essence",
            time_advance=0,
        )

    slot = next(
        (s for s in ctx.essence_slots if s.essence_name == essence_name), None
    )
    if slot is None:
        return ActionResult(
            narrative=f"{essence_name}을(를) 흡수한 적이 없습니다.",
            success=False,
            fail_reason="not_absorbed",
            time_advance=0,
        )

    msg_lines = [f"「{essence_name}이(가) 제거되었습니다.」"]
    for stat, delta in slot.stat_bundle.items():
        sign = "-" if delta >= 0 else "+"
        abs_val = abs(delta)
        action = "하락" if delta >= 0 else "상승"
        msg_lines.append(f"「{stat}이(가) {sign}{abs_val} {action}합니다.」")

    return ActionResult(
        narrative="\n".join(msg_lines),
        time_advance=0,
        essence_slot_remove=essence_name,
    )


async def handle_examine_stats(ctx: ActionContext) -> ActionResult:
    """본인 능력치 / 레벨 / XP 확인."""
    total = ctx.total_stats
    lines = [
        "── 비요른의 현재 상태 ──",
        f"레벨: {ctx.player_level}  (XP: {ctx.player_xp})",
        f"HP: {ctx.current_hp}/{ctx.max_hp}",
        f"영혼력: {ctx.soul_power}",
        f"흡수 정수: {len(ctx.absorbed_essences)}/{ctx.max_essences}",
    ]
    if ctx.absorbed_essences:
        lines.append("\n흡수한 정수:")
        for slot in ctx.essence_slots:
            lines.append(f"  - {slot.essence_name}")
    if total:
        lines.append("\n능력치 합산:")
        for stat, val in sorted(total.items(), key=lambda x: -abs(x[1])):
            sign = "+" if val >= 0 else ""
            lines.append(f"  {stat}: {sign}{val}")
    if ctx.defeated_monster_types:
        lines.append(f"\n처치 완료 종: {len(ctx.defeated_monster_types)}종")
    return ActionResult(
        narrative="\n".join(lines),
        time_advance=0,
    )


async def handle_use_item(ctx: ActionContext) -> ActionResult:
    item = extract_item_from_inventory(ctx.user_input, ctx.inventory)
    if not item:
        return ActionResult(
            narrative="사용할 아이템을 찾을 수 없습니다.",
            success=False,
            fail_reason="no_item",
            time_advance=0,
        )
    if item not in ctx.inventory:
        return ActionResult(
            narrative=f"{item}을 가지고 있지 않습니다.",
            success=False,
            fail_reason="not_in_inventory",
            time_advance=0,
        )
    if "물약" in item:
        return ActionResult(
            narrative=(
                f"비요른은 {item}의 마개를 뽑아 단숨에 들이켭니다."
                " 체온이 돌아오는 것이 느껴집니다."
            ),
            inventory_remove=[item],
            hp_change=30,
            time_advance=1,
        )
    return ActionResult(
        narrative=f"비요른은 {item}을 사용합니다.",
        inventory_remove=[item],
        time_advance=1,
    )


async def handle_offer_to_stone(ctx: ActionContext) -> ActionResult:
    mage_stone = next((i for i in ctx.inventory if "마석" in i), None)
    if not mage_stone:
        return ActionResult(
            narrative="비석에 바칠 마석이 없습니다.",
            success=False,
            fail_reason="no_mage_stone",
            time_advance=0,
        )
    return ActionResult(
        narrative=f"비요른은 {mage_stone}을 비석 앞에 놓습니다. 돌 표면이 희미하게 빛납니다.",
        inventory_remove=[mage_stone],
        time_advance=1,
    )


# ─── 휴식 ───


async def handle_rest(ctx: ActionContext) -> ActionResult:
    recovery = min(20, ctx.max_hp - ctx.current_hp)
    return ActionResult(
        narrative="비요른은 벽에 등을 기댑니다. 짧은 침묵 속에 호흡이 고른 리듬을 찾아갑니다.",
        hp_change=recovery,
        time_advance=4,
    )


async def handle_wait(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative="비요른은 움직이지 않습니다. 시간이 흐릅니다.",
        time_advance=1,
    )


async def handle_wait_in_village(ctx: ActionContext) -> ActionResult:
    recovery = ctx.max_hp - ctx.current_hp
    return ActionResult(
        narrative=(
            "비요른은 마을에서 하루를 보냅니다."
            " 잠을 자고 식사를 하니 몸이 한결 가벼워집니다."
        ),
        hp_change=recovery,
        time_advance=24,
    )


async def handle_rest_and_night_watch(ctx: ActionContext) -> ActionResult:
    if ctx.encounters:
        return ActionResult(
            narrative="주변에 적대적인 기척이 있어 야영할 수 없습니다.",
            success=False,
            fail_reason="hostile_nearby",
            time_advance=0,
        )
    recovery = min(40, ctx.max_hp - ctx.current_hp)
    return ActionResult(
        narrative=(
            "비요른은 불침번을 세우며 야영지에 자리를 폅니다."
            " 교대로 눈을 붙이고 날이 밝기를 기다립니다."
        ),
        hp_change=recovery,
        time_advance=8,
    )


# ─── 통신 / 사회 ───


async def handle_communicate(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative=(
            "비요른은 메시지 스톤을 꺼내 손에 쥡니다."
            " 돌의 온기가 전해지며 목소리가 실립니다."
        ),
        time_advance=0,
    )


async def handle_dialogue(ctx: ActionContext) -> ActionResult:
    npc = get_first_npc(ctx.encounters)
    if not npc:
        return ActionResult(
            narrative="대화할 상대가 없습니다.",
            success=False,
            fail_reason="no_npc",
            time_advance=0,
        )
    name = get_entity_name(npc, "NPC")
    return ActionResult(
        narrative=f"비요른은 {name}에게 다가가 말을 건넵니다. 짧은 대화가 오고 갑니다.",
        affinity_changes={name: 1},
        time_advance=1,
    )


async def handle_reject_dialogue(ctx: ActionContext) -> ActionResult:
    npc = get_first_npc(ctx.encounters)
    if not npc:
        return ActionResult(
            narrative="거절할 대상이 없습니다.",
            success=False,
            fail_reason="no_npc",
            time_advance=0,
        )
    name = get_entity_name(npc, "NPC")
    return ActionResult(
        narrative=f"비요른은 {name}의 말을 잘라냅니다. 짤막한 침묵이 흐릅니다.",
        affinity_changes={name: -1},
        time_advance=0,
    )


async def handle_form_night_companion(ctx: ActionContext) -> ActionResult:
    npc = get_first_npc(ctx.encounters)
    name = get_entity_name(npc, "동행") if npc else "동행"
    return ActionResult(
        narrative=f"비요른은 {name}과 임시 협력 관계를 맺습니다. 말이 없어도 의미가 통합니다.",
        time_advance=0,
    )


async def handle_disband_night_companion(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative="비요른은 협력 관계를 끝맺습니다. 각자의 길로 향합니다.",
        time_advance=0,
    )


# ─── 상점 / 거래 ───


async def handle_shop_sell(ctx: ActionContext) -> ActionResult:
    item = extract_item_from_inventory(ctx.user_input, ctx.inventory)
    if not item or item not in ctx.inventory:
        return ActionResult(
            narrative="판매할 아이템을 찾을 수 없습니다.",
            success=False,
            fail_reason="no_item",
            time_advance=0,
        )
    return ActionResult(
        narrative=f"비요른은 상인에게 {item}을 내밉니다. 동전이 손바닥에 떨어집니다.",
        inventory_remove=[item],
        time_advance=1,
    )


async def handle_shop_buy(ctx: ActionContext) -> ActionResult:
    item = extract_item_from_input(ctx.user_input)
    if not item:
        return ActionResult(
            narrative="구매할 아이템을 찾을 수 없습니다.",
            success=False,
            fail_reason="no_item",
            time_advance=0,
        )
    return ActionResult(
        narrative=f"비요른은 상인에게 동전을 건네고 {item}을 손에 넣습니다.",
        inventory_add=[item],
        time_advance=1,
    )


async def handle_exchange_mage_stones(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative="비요른은 환전소 창구 앞에 섭니다. 마석과 스톤의 환율을 확인합니다.",
        time_advance=1,
    )


# ─── 서비스 ───


async def handle_heal_at_temple(ctx: ActionContext) -> ActionResult:
    recovery = ctx.max_hp - ctx.current_hp
    return ActionResult(
        narrative=(
            "비요른은 삼신교 신전 앞에 무릎을 꿇습니다."
            " 사제의 손이 상처 위에 닿자 열기가 가라앉습니다."
        ),
        hp_change=recovery,
        time_advance=2,
    )


async def handle_recruit_from_guild(ctx: ActionContext) -> ActionResult:
    return ActionResult(
        narrative=(
            "비요른은 길드 게시판 앞에서 신참자 목록을 훑어봅니다."
            " 빈자리를 채울 인원을 고릅니다."
        ),
        time_advance=2,
    )


# ─── dispatcher ───

ACTION_HANDLERS: dict[PlayerActionType, _Handler] = {
    PlayerActionType.ACTIVATE_LIGHT: handle_activate_light,
    PlayerActionType.MOVE: handle_move,
    PlayerActionType.EXPLORE: handle_explore,
    PlayerActionType.ATTACK: handle_attack,
    PlayerActionType.ABSORB_ESSENCE: handle_absorb_essence,
    PlayerActionType.USE_ITEM: handle_use_item,
    PlayerActionType.OFFER_TO_STONE: handle_offer_to_stone,
    PlayerActionType.ENTER_RIFT: handle_enter_rift,
    PlayerActionType.EXIT_RIFT: handle_exit_rift,
    PlayerActionType.REST: handle_rest,
    PlayerActionType.WAIT: handle_wait,
    PlayerActionType.COMMUNICATE: handle_communicate,
    PlayerActionType.FLEE: handle_flee,
    PlayerActionType.ENTER_NEXT_FLOOR: handle_enter_next_floor,
    PlayerActionType.EXIT_TO_PREV_FLOOR: handle_exit_to_prev_floor,
    PlayerActionType.EXCHANGE_MAGE_STONES: handle_exchange_mage_stones,
    PlayerActionType.WAIT_IN_VILLAGE: handle_wait_in_village,
    PlayerActionType.ENTER_DUNGEON: handle_enter_dungeon,
    PlayerActionType.HEAL_AT_TEMPLE: handle_heal_at_temple,
    PlayerActionType.DIALOGUE: handle_dialogue,
    PlayerActionType.LIBRARY_SEARCH: handle_library_search,
    PlayerActionType.RECRUIT_FROM_GUILD: handle_recruit_from_guild,
    PlayerActionType.REJECT_DIALOGUE: handle_reject_dialogue,
    PlayerActionType.SHOP_SELL: handle_shop_sell,
    PlayerActionType.SHOP_BUY: handle_shop_buy,
    PlayerActionType.FORM_NIGHT_COMPANION: handle_form_night_companion,
    PlayerActionType.DISBAND_NIGHT_COMPANION: handle_disband_night_companion,
    PlayerActionType.ENGAGE_BANDIT: handle_engage_bandit,
    PlayerActionType.REST_AND_NIGHT_WATCH: handle_rest_and_night_watch,
    PlayerActionType.EQUIP: handle_equip,
    PlayerActionType.UNEQUIP: handle_unequip,
    PlayerActionType.REMOVE_ESSENCE: handle_remove_essence,
    PlayerActionType.EXAMINE_STATS: handle_examine_stats,
}

assert len(ACTION_HANDLERS) == 33, f"handler count mismatch: {len(ACTION_HANDLERS)}"


async def dispatch_action(
    action_type: PlayerActionType,
    ctx: ActionContext,
) -> ActionResult:
    """action_type에 해당하는 핸들러 호출."""
    handler = ACTION_HANDLERS.get(action_type)
    if not handler:
        return ActionResult(
            narrative=f"{action_type.value} 행동은 아직 구현되지 않았습니다.",
            success=False,
            fail_reason="not_implemented",
            time_advance=0,
        )
    return await handler(ctx)
