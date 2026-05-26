"""Phase 9.17-c1 npc-encounter-types — EncounterType NPC 4 value 확장.

검증 본질:
- EncounterType 신규 4 value (NPC_PEACEFUL/NEUTRAL/HOSTILE/RESOURCE)
- 기존 6 type regression
- Encounter dataclass 본격 신규 NPC type 정합
- ENCOUNTER_TTL 본격 신규 type 매핑
- _gm_system_prompt NPC encounter 가이드 포함
- 후속 consumer (9.17-c2 / 9.17-d) trigger 가능

본문 정합:
- 6화: 한스 만남 (PEACEFUL/RESOURCE)
- 24화: 인간 셋 통과 (NEUTRAL) / 약탈자 (HOSTILE)
- 37/51화: 약탈자 (HOSTILE)
"""

from __future__ import annotations

from typing import Any

from service.game.gm_agent import _gm_system_prompt
from service.sim.types import (
    ENCOUNTER_TTL,
    Encounter,
    EncounterType,
)

# ─── 1. NPC 4 value ───


def test_npc_peaceful_value_6hwa() -> None:
    """6화 정합 — 한스 만남."""
    assert EncounterType.NPC_PEACEFUL.value == "npc_peaceful"


def test_npc_neutral_value_24hwa() -> None:
    """24화 정합 — 인간 셋 통과."""
    assert EncounterType.NPC_NEUTRAL.value == "npc_neutral"


def test_npc_hostile_value_24_37_51hwa() -> None:
    """24/37/51화 정합 — 약탈자."""
    assert EncounterType.NPC_HOSTILE.value == "npc_hostile"


def test_npc_resource_value_6hwa() -> None:
    """6화 정합 — 연못 spot."""
    assert EncounterType.NPC_RESOURCE.value == "npc_resource"


# ─── 2. 기존 6 type regression ───


def test_essence_unchanged() -> None:
    assert EncounterType.ESSENCE.value == "essence"


def test_monster_unchanged() -> None:
    assert EncounterType.MONSTER.value == "monster"


def test_rift_unchanged() -> None:
    assert EncounterType.RIFT.value == "rift"


def test_item_unchanged() -> None:
    assert EncounterType.ITEM.value == "item"


def test_event_unchanged() -> None:
    assert EncounterType.EVENT.value == "event"


def test_narrative_unchanged() -> None:
    assert EncounterType.NARRATIVE.value == "narrative"


# ─── 3. 총 count ───


def test_total_encounter_types_10() -> None:
    """기존 6 + NPC 4 = 10."""
    assert len(list(EncounterType)) == 10


def test_npc_types_all_in_enum() -> None:
    npc_values = {
        "npc_peaceful",
        "npc_neutral",
        "npc_hostile",
        "npc_resource",
    }
    all_values = {t.value for t in EncounterType}
    assert npc_values.issubset(all_values)


# ─── 4. Encounter dataclass + NPC type 정합 ───


def test_encounter_npc_peaceful_create() -> None:
    enc = Encounter(
        type=EncounterType.NPC_PEACEFUL,
        name="다른 탐험가",
        location="south_lake",
        description=(
            "어둠 속에서 다른 탐험가의 인기척이 느껴진다. 위협적이지 않다."
        ),
    )
    assert enc.type == EncounterType.NPC_PEACEFUL


def test_encounter_npc_hostile_create() -> None:
    enc = Encounter(
        type=EncounterType.NPC_HOSTILE,
        name="약탈자 무리",
        location="north_passage",
        description="약탈자 무리의 기척이 느껴진다.",
    )
    assert enc.type == EncounterType.NPC_HOSTILE


def test_encounter_npc_resource_create() -> None:
    enc = Encounter(
        type=EncounterType.NPC_RESOURCE,
        name="연못",
        location="cave",
        description="물 떨어지는 소리. 작은 연못을 발견했다.",
    )
    assert enc.type == EncounterType.NPC_RESOURCE


def test_encounter_string_coerce_npc_neutral() -> None:
    """str → enum coerce (★ sim_gm_agent 본격 정합)."""
    coerced = EncounterType("npc_neutral")
    assert coerced == EncounterType.NPC_NEUTRAL


# ─── 5. ENCOUNTER_TTL 매핑 ───


def test_ttl_npc_peaceful_present() -> None:
    assert EncounterType.NPC_PEACEFUL in ENCOUNTER_TTL
    assert ENCOUNTER_TTL[EncounterType.NPC_PEACEFUL] > 0


def test_ttl_npc_neutral_present() -> None:
    assert EncounterType.NPC_NEUTRAL in ENCOUNTER_TTL
    assert ENCOUNTER_TTL[EncounterType.NPC_NEUTRAL] > 0


def test_ttl_npc_hostile_present() -> None:
    assert EncounterType.NPC_HOSTILE in ENCOUNTER_TTL


def test_ttl_npc_resource_present() -> None:
    assert EncounterType.NPC_RESOURCE in ENCOUNTER_TTL


def test_ttl_all_types_mapped() -> None:
    """ENCOUNTER_TTL 본격 모든 EncounterType 매핑."""
    for t in EncounterType:
        assert t in ENCOUNTER_TTL, f"{t} TTL X"


# ─── 6. _gm_system_prompt — NPC encounter 가이드 ───


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
        "current_location": "1층 진입점",
        "current_turn": 0,
    }


def test_prompt_includes_npc_guide_header() -> None:
    prompt = _gm_system_prompt(_base_ctx())
    assert "NPC encounter" in prompt
    assert "9.17-c1" in prompt


def test_prompt_includes_all_4_types() -> None:
    prompt = _gm_system_prompt(_base_ctx())
    assert "npc_peaceful" in prompt
    assert "npc_neutral" in prompt
    assert "npc_hostile" in prompt
    assert "npc_resource" in prompt


def test_prompt_includes_chapter_citations() -> None:
    """본문 정합 — 6/24/37/51화 인용."""
    prompt = _gm_system_prompt(_base_ctx())
    assert "6화" in prompt
    assert "24화" in prompt
    assert "51화" in prompt


def test_prompt_includes_peaceful_narrative_hans() -> None:
    """6화 한스 narrative 가이드."""
    prompt = _gm_system_prompt(_base_ctx())
    assert "한스" in prompt


def test_prompt_includes_hostile_narrative_predator() -> None:
    """약탈자 narrative 가이드."""
    prompt = _gm_system_prompt(_base_ctx())
    assert "약탈자" in prompt


def test_prompt_includes_frequency_guide() -> None:
    """24화 — 시간 흐를수록 빈도 ↑."""
    prompt = _gm_system_prompt(_base_ctx())
    assert "빈도" in prompt
    assert "흐를수록" in prompt


def test_prompt_within_diet_budget() -> None:
    """NPC encounter 추가 후 diet budget (★ 4500 chars) 유지."""
    prompt = _gm_system_prompt(_base_ctx())
    assert len(prompt) < 4500
