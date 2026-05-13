"""CityDefinition schema (★ Phase 8 (a-2)).

본 모듈은 마을 콘텐츠 본격 schema. 별도 dataclass (★ FloorDefinition과 분리):
- 본인 답 7.2: "미궁의 층수와 마을은 별개 — 아예 다른 구역"
- 마을 본질: NPC + 거래 + 정보 수집 (★ FloorDefinition은 sub_areas/rifts/monsters)

본격 사용처: turn_handler_v2.apply_time_limit_village_return (★ A4 TIME_LIMIT_REACHED
시 location 본격 마을 mutation — DEFAULT_CITY / DEFAULT_CITY_ENTRY_SUB_AREA 본격).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CitySubAreaDef:
    """마을 sub_area 정의.

    floor1.SubArea와 분리 — 마을은 NPC 본격, sub_area_id 본격 영문 식별자
    (★ floor SubArea.name은 한국어, 본격 본격 본격 정합).
    """

    id: str
    name: str
    description: str
    connections: tuple[str, ...] = ()  # 인접 sub_area id (★ MOVE 본격)
    npc_ids: tuple[str, ...] = ()  # 본 sub_area 본격 NPC id


@dataclass(frozen=True, slots=True)
class NPCDef:
    """마을 NPC 정의 (★ docs/village_spec.md §7.4 정합).

    is_canonical:
    - True = 본문 직접 등장 인물 (★ 아이나르/에르웬/미샤/라그나)
    - False = 직책만 (★ 환전소 직원/여관 주인 등 — 본문 등장 X 이름)
    """

    id: str
    name: str
    role: str  # "exchange_clerk" / "innkeeper" / "barbarian_companion" 등
    sub_area_id: str
    dialogue_intro: str = ""  # 본문 출처 1-line — 후속 dialogue mechanism 본격
    is_canonical: bool = False


@dataclass(frozen=True, slots=True)
class CityDefinition:
    """마을 풀 정의."""

    city_id: str
    city_name: str
    entry_sub_area: str  # 진입 sub_area id (★ (a-3) 본격 본격 마을 도착 본격)
    sub_areas: tuple[CitySubAreaDef, ...]
    npcs: tuple[NPCDef, ...]
