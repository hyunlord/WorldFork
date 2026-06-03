"""Phase D step 6c — turn-end encounter auto spawn."""

from __future__ import annotations

import random
from copy import deepcopy
from typing import TYPE_CHECKING

from service.canon.schema import CanonFacts
from service.canon.spawn import (
    LOCATION_SPAWN_RATE,
    SpawnTable,
    _monster_name_to_enemy,
    spawn_count_for_grade,
)
from service.sim.enemy import Enemy

if TYPE_CHECKING:
    from service.game.state_v2 import RiftDef, RiftSubAreaDef

SPAWN_COOLDOWN_TURNS = 2

# ★ 서빙 4단계 고증 — 1층 수정동굴 정상 몬스터 (INTEGRATED_RESEARCH_V4).
#   기존 스폰 풀은 race 파생 잡종(바바리안족·고양이귀·뱀파이어 등 심층/종족)이
#   floor 무관하게 1층에 섞여 들던 결함. 얕은 층은 이 curated 엔트리 풀로 게이팅해
#   '뱀파이어가 1층 입구에' 같은 고증 단절을 해소(뱀파이어는 본문 심층 몬스터).
#   ※ codebase grade는 canon과 반대(1=약함) — 엔트리라 grade 1(약체)로 둔다.
FLOOR1_MONSTER_NAMES: tuple[str, ...] = (
    "고블린",
    "고블린 검사",
    "고블린 궁수",
    "노움",
    "슬라임",
    "칼날늑대",
    "레이스",
)


def floor_canonical_pool(floor_number: int) -> list[Enemy] | None:
    """얕은 층(1층)의 고증 정합 몬스터 풀 — 없으면 None(기존 로직 사용).

    1층만 curated(엔트리 몬스터). 2층+ 및 0층(마을)은 None 반환해 기존 스폰 유지.
    """
    if floor_number == 1:
        return [_monster_name_to_enemy(name, grade=1) for name in FLOOR1_MONSTER_NAMES]
    return None


def determine_location_type(
    location_name: str,
    facts: CanonFacts | None,
) -> str:
    """location name → location type (canon lookup → name heuristic)."""
    if facts is not None:
        for loc in facts.locations:
            if loc.name == location_name:
                return loc.location_type
            if loc.name and (loc.name in location_name or location_name in loc.name):
                return loc.location_type

    name = location_name.lower()
    if any(kw in name for kw in ("균열", "차원", "rift")):
        return "rift"
    if any(kw in name for kw in ("도시", "마을", "광장", "시장", "거리", "구역")):
        return "city"
    if any(kw in name for kw in ("탑", "성", "유적", "굴", "지하", "동굴", "미궁")):
        return "dungeon"
    return "wilderness"


def should_spawn(
    location_type: str,
    turn_count: int,
    last_spawn_turn: int,
) -> bool:
    """spawn 여부 결정 — rate check + cooldown check."""
    rate = LOCATION_SPAWN_RATE.get(location_type, 0.0)
    if rate <= 0.0:
        return False
    if turn_count - last_spawn_turn < SPAWN_COOLDOWN_TURNS:
        return False
    return random.random() < rate


def _find_rift_sub_area(
    rift_sub_area: str,
    rift_defs: dict[str, RiftDef],
) -> RiftSubAreaDef | None:
    """rift_defs에서 rift_sub_area id와 일치하는 RiftSubAreaDef 반환."""
    for rift_def in rift_defs.values():
        for sub in rift_def.sub_areas:
            if sub.id == rift_sub_area:
                return sub
    return None


def trigger_spawn(
    location_name: str,
    location_type: str,
    turn_count: int,
    last_spawn_turn: int,
    spawn_table: SpawnTable,
    rift_sub_area: str | None = None,
    rift_defs: dict[str, RiftDef] | None = None,
    floor_number: int = 0,
) -> list[dict[str, object]]:
    """spawn check 후 enemy dict 목록 반환 (비어 있으면 spawn 없음).

    rift_sub_area + rift_defs가 모두 있으면 RiftSubAreaDef.monsters 우선.
    floor_number가 얕은 층(1층)이면 고증 정합 엔트리 풀로 게이팅(심층 몬스터 제외).
    """
    if not should_spawn(location_type, turn_count, last_spawn_turn):
        return []

    from service.sim.enemy import enemy_to_dict

    if rift_sub_area and rift_defs:
        sub_def = _find_rift_sub_area(rift_sub_area, rift_defs)
        if sub_def is not None:
            enemies = spawn_table.spawn_for_rift_sub_area(sub_def, n=1)
            return [enemy_to_dict(e) for e in enemies]

    grade = spawn_table.get_location_grade(location_name)
    n_min, n_max = spawn_count_for_grade(grade)
    n = random.randint(n_min, n_max)

    # ★ 서빙 4단계 고증 — 얕은 층은 curated 엔트리 풀(고블린/노움/슬라임 등),
    #   심층/종족 잡종(뱀파이어 등) 미스폰. None이면 기존 location 풀 사용.
    floor_pool = floor_canonical_pool(floor_number)
    if floor_pool is not None:
        n = min(n, len(floor_pool))
        picked = (
            [deepcopy(e) for e in floor_pool]
            if len(floor_pool) <= n
            else [deepcopy(e) for e in random.sample(floor_pool, n)]
        )
        return [enemy_to_dict(e) for e in picked]

    enemies = spawn_table.spawn_for_location(location_name, location_type, n)
    if not enemies:
        return []

    return [enemy_to_dict(e) for e in enemies]
