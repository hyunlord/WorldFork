"""Phase 8 (a-2) — 라프도니아 도시 콘텐츠 unit 본격.

검증 본질:
- DEFAULT_CITY_ID / DEFAULT_CITY_ENTRY_SUB_AREA production 상수
- RAPDONIA: 9 sub_areas + 9 NPCs (4 canonical + 5 직책만)
- sub_area connections bidirectional 일관성
- NPC.sub_area_id 본격 sub_area 존재 본격
- 본문 정합 인물 (★ 아이나르/에르웬/미샤/라그나)

★ CITY_REGISTRY dict / DEFAULT_CITY instance 본격 제거 (★ R2 22d4607 codex YAGNI
선례 정합 — production caller X 시 제거).
"""

from __future__ import annotations

from service.game.cities.city_definition import (
    CitySubAreaDef,
    NPCDef,
)
from service.game.cities.rapdonia import (
    RAPDONIA,
    RAPDONIA_NPCS,
    RAPDONIA_SUB_AREAS,
)
from service.game.cities.registry import (
    DEFAULT_CITY_ENTRY_SUB_AREA,
    DEFAULT_CITY_ID,
)

# ─── 1. Production 상수 ───


def test_default_city_id_is_rapdonia() -> None:
    assert DEFAULT_CITY_ID == "rapdonia"
    assert DEFAULT_CITY_ID == RAPDONIA.city_id


def test_default_city_entry_sub_area() -> None:
    assert DEFAULT_CITY_ENTRY_SUB_AREA == "district_7_plaza"
    assert DEFAULT_CITY_ENTRY_SUB_AREA == RAPDONIA.entry_sub_area


# ─── 2. RAPDONIA structure ───


def test_rapdonia_basic_fields() -> None:
    assert RAPDONIA.city_id == "rapdonia"
    assert RAPDONIA.city_name == "라프도니아"
    assert RAPDONIA.entry_sub_area == "district_7_plaza"


def test_rapdonia_has_9_sub_areas() -> None:
    """docs/village_spec.md §7.3 본격 9개 sub_area."""
    assert len(RAPDONIA_SUB_AREAS) == 9


def test_rapdonia_sub_area_ids_unique() -> None:
    ids = [s.id for s in RAPDONIA_SUB_AREAS]
    assert len(ids) == len(set(ids))


def test_rapdonia_entry_sub_area_exists() -> None:
    ids = {s.id for s in RAPDONIA_SUB_AREAS}
    assert RAPDONIA.entry_sub_area in ids


def test_district_7_plaza_is_hub() -> None:
    """진입 광장 = 모임 장소 → 다수 연결 (★ 162화 본문 정합)."""
    plaza = next(
        s for s in RAPDONIA_SUB_AREAS if s.id == "district_7_plaza"
    )
    assert plaza.name == "라프도니아 7구역 중앙 광장"
    # 최소 5개 sub_area 연결 (★ 162화 "광장" hub 본질)
    assert len(plaza.connections) >= 5


def test_all_sub_area_connections_valid() -> None:
    """모든 connection target 본격 등록된 sub_area id 본격."""
    ids = {s.id for s in RAPDONIA_SUB_AREAS}
    for sub in RAPDONIA_SUB_AREAS:
        for conn in sub.connections:
            assert conn in ids, (
                f"sub_area {sub.id} connects to unknown {conn}"
            )


# ─── 3. NPCs ───


def test_rapdonia_has_9_npcs() -> None:
    assert len(RAPDONIA_NPCS) == 9


def test_npc_ids_unique() -> None:
    ids = [n.id for n in RAPDONIA_NPCS]
    assert len(ids) == len(set(ids))


def test_canonical_npcs_4() -> None:
    """본문 직접 등장 인물 4명 (★ docs/village_spec.md §7.4)."""
    canonical = [n for n in RAPDONIA_NPCS if n.is_canonical]
    assert len(canonical) == 4
    names = {n.name for n in canonical}
    assert names == {"아이나르", "에르웬", "미샤", "라그나"}


def test_placeholder_npcs_5() -> None:
    """직책 placeholder 5명 (★ 환전소/여관/대장간/잡화점/거래소 직원)."""
    placeholders = [n for n in RAPDONIA_NPCS if not n.is_canonical]
    assert len(placeholders) == 5


def test_canonical_npcs_have_dialogue_intro() -> None:
    """canonical NPC 본격 본문 출처 명시."""
    for n in RAPDONIA_NPCS:
        if n.is_canonical:
            assert n.dialogue_intro, f"{n.name} 본격 dialogue_intro X"


def test_ragna_in_central_library() -> None:
    """라그나 = 라비기온 중앙 도서관 사서 (★ namu §4.3)."""
    ragna = next(n for n in RAPDONIA_NPCS if n.id == "ragna")
    assert ragna.sub_area_id == "central_library"
    assert ragna.role == "librarian"


def test_companions_in_plaza() -> None:
    """비요른 동료 3명 (아이나르/에르웬/미샤) = 7구역 광장 (★ 본문)."""
    for npc_id in ("aenar", "erwen", "misha"):
        npc = next(n for n in RAPDONIA_NPCS if n.id == npc_id)
        assert npc.sub_area_id == "district_7_plaza"


def test_all_npc_sub_areas_exist() -> None:
    """모든 NPC.sub_area_id 본격 등록된 sub_area 본격."""
    ids = {s.id for s in RAPDONIA_SUB_AREAS}
    for npc in RAPDONIA_NPCS:
        assert npc.sub_area_id in ids


def test_sub_area_npc_ids_valid() -> None:
    """sub_area.npc_ids 본격 등록된 NPC 본격."""
    npc_ids = {n.id for n in RAPDONIA_NPCS}
    for sub in RAPDONIA_SUB_AREAS:
        for nid in sub.npc_ids:
            assert nid in npc_ids, f"{sub.id} unknown npc {nid}"


def test_sub_area_npc_ids_match_npc_sub_area_id() -> None:
    """양방향 정합 — sub_area.npc_ids 본격 NPC, NPC.sub_area_id 일치."""
    for sub in RAPDONIA_SUB_AREAS:
        for nid in sub.npc_ids:
            npc = next(n for n in RAPDONIA_NPCS if n.id == nid)
            assert npc.sub_area_id == sub.id


# ─── 4. CityDefinition schema 본격 ───


def test_city_definition_frozen() -> None:
    """frozen dataclass — 본격 mutation X."""
    import pytest
    with pytest.raises((AttributeError, Exception)):
        RAPDONIA.city_id = "other"  # type: ignore[misc]


def test_city_sub_area_def_minimal() -> None:
    """default empty tuples 본격."""
    sa = CitySubAreaDef(id="x", name="test", description="d")
    assert sa.connections == ()
    assert sa.npc_ids == ()


def test_npc_def_minimal() -> None:
    """default empty intro + is_canonical False."""
    n = NPCDef(id="x", name="test", role="r", sub_area_id="a")
    assert n.dialogue_intro == ""
    assert n.is_canonical is False


def test_city_definition_collections_match() -> None:
    """CityDefinition.sub_areas / .npcs 본격 module-level constants 일치."""
    assert RAPDONIA.sub_areas is RAPDONIA_SUB_AREAS
    assert RAPDONIA.npcs is RAPDONIA_NPCS
