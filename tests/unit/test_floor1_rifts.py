"""1층 균열 4종 진짜 정의 테스트 (★ Phase 8 A1 — namu 정합).

본인 본질 (2026-05-13):
- 핏빛성채: 5 챕터, 일반 블라터 + 변종 캠보르미어 5등급 (★ 33화)
- 빙하굴: 4 챕터, 일반 폭군 타룬바스 7등급 + 변종 키르뒤, 전격 약점
- 녹색 탄광: 4 챕터, 일반 킹 슬라임, 변종 X
- 강철의 묘: 4 챕터, 일반 철인 일디움, 변종 X
"""

from __future__ import annotations

from service.game.floors.floor1 import get_floor1_definition
from service.game.floors.floor1_rifts import FLOOR1_RIFT_DEFS, FLOOR1_RIFTS
from service.game.state_v2 import RiftChamberType, RiftDef, RiftEntryMethod


def _find_rift(rift_id: str) -> RiftDef | None:
    return FLOOR1_RIFT_DEFS.get(rift_id)


def test_floor1_has_4_rifts() -> None:
    """1층 균열 4종."""
    assert len(FLOOR1_RIFTS) == 4
    assert len(FLOOR1_RIFT_DEFS) == 4
    ids = set(FLOOR1_RIFT_DEFS)
    assert ids == {"bloody_castle", "glacier_cave", "green_mine", "iron_tomb"}


def test_bloody_castle_normal_and_variant() -> None:
    """핏빛성채: 일반 블라터 + 변종 캠보르미어 5등급 (★ namu 6.1.1)."""
    bc = _find_rift("bloody_castle")
    assert bc is not None
    # ★ 일반 수호자
    assert bc.normal_boss_name == "저주받은 기사 블라터"
    assert bc.normal_boss_grade == 6  # ★ placeholder, 후속 진단
    # ★ 변종 수호자 (표기 통일: 캠보르미어)
    assert bc.variant_possible is True
    assert bc.variant_boss_name == "뱀파이어 공작 캠보르미어"
    assert bc.variant_boss_grade == 5
    # ★ 5 챕터
    assert len(bc.sub_areas) == 5
    assert bc.entrance_id == "bc_ch1"
    assert bc.boss_chamber_id == "bc_ch5"
    # ★ 정수 색
    assert bc.essence_color == "red"
    # ★ 공물
    assert bc.intentional_offering_source_floor == 2
    assert bc.intentional_offering_source_area == "망자의 땅"


def test_bloody_castle_chapter_structure() -> None:
    """핏빛성채 5 챕터: 외곽 검문소 → ... → 영주성 악마 숭배실."""
    bc = _find_rift("bloody_castle")
    assert bc is not None
    names = [sa.name for sa in bc.sub_areas]
    assert names == [
        "외곽 검문소",
        "도개교",
        "외성벽 시가지",
        "내성벽 지하 감옥",
        "영주성 악마 숭배실",
    ]
    # ★ 중간 보스: 시체골렘 (chapter 4)
    ch4 = bc.sub_areas[3]
    assert ch4.chamber_type == RiftChamberType.MID_BOSS
    assert ch4.mid_boss_name == "시체골렘"
    assert ch4.mid_boss_grade == 7


def test_glacier_cave_grade_7_and_weakness() -> None:
    """빙하굴: 폭군 타룬바스 7등급 + 전격 약점 (★ namu 6.1.2)."""
    gc = _find_rift("glacier_cave")
    assert gc is not None
    assert gc.normal_boss_name == "폭군 타룬바스"
    # ★ namu "수호자조차 7등급에 불과" 명시 — 기존 코드 8 → 7로 변경
    assert gc.normal_boss_grade == 7
    assert gc.variant_boss_name == "타락한 짐승 키르뒤"
    assert gc.variant_boss_grade is None  # ★ namu X
    # ★ 전격 약점
    assert gc.boss_weakness is not None
    assert gc.boss_weakness.element == "전격"
    # ★ 4 챕터 + 저체온증 필드 효과 (chapter 3)
    assert len(gc.sub_areas) == 4
    ch3 = gc.sub_areas[2]
    assert ch3.field_effect is not None
    assert "저체온증" in ch3.field_effect
    # ★ 정수 색
    assert gc.essence_color == "blue"


def test_green_mine_hidden_pieces() -> None:
    """녹색 탄광: 4 챕터, 일반 킹 슬라임 + 히든 피스 (★ namu 6.1.3)."""
    gm = _find_rift("green_mine")
    assert gm is not None
    assert gm.normal_boss_name == "킹 슬라임"
    # ★ namu X — 변종 placeholder
    assert gm.variant_boss_name is None
    assert len(gm.sub_areas) == 4
    # ★ 챕터 1 히든: 300만 스톤 초록 보석
    ch1 = gm.sub_areas[0]
    assert "green_gem_3m_stone" in ch1.hidden_pieces
    # ★ 챕터 2 중간 보스: 고블린 폭탄병
    ch2 = gm.sub_areas[1]
    assert ch2.mid_boss_name == "고블린 폭탄병"
    assert "gobl_quartz" in ch2.hidden_pieces
    assert gm.essence_color == "green"


def test_iron_tomb_structure() -> None:
    """강철의 묘: 4 챕터, 일반 철인 일디움 (★ namu 6.1.4)."""
    it = _find_rift("iron_tomb")
    assert it is not None
    assert it.normal_boss_name == "철인 일디움"
    assert it.variant_boss_name is None  # ★ namu/본인 둘 다 X
    assert len(it.sub_areas) == 4
    assert it.essence_color == "yellow"


def test_all_rifts_drop_rate_33() -> None:
    """모든 균열 수호자 정수 33%."""
    for r in FLOOR1_RIFTS:
        assert r.boss_drop_rate == 0.33


def test_all_rifts_two_entry_methods() -> None:
    """모든 균열 무작위/의도적 진입 + 8등급 마석."""
    for r in FLOOR1_RIFTS:
        assert RiftEntryMethod.RANDOM_NATURAL in r.entry_methods
        assert RiftEntryMethod.INTENTIONAL_OFFERING in r.entry_methods
        assert r.intentional_offering_grade == 8


def test_all_rifts_party_capacity_5() -> None:
    """모든 균열 파티 한도 5명 (★ 본인 결정)."""
    for r in FLOOR1_RIFTS:
        assert r.party_capacity == 5


def test_all_rifts_have_boss_chamber() -> None:
    """모든 균열 마지막 챕터 = BOSS chamber_type."""
    for r in FLOOR1_RIFTS:
        boss_sa = next(
            (sa for sa in r.sub_areas if sa.id == r.boss_chamber_id), None
        )
        assert boss_sa is not None
        assert boss_sa.chamber_type == RiftChamberType.BOSS


def test_all_rifts_entrance_chamber() -> None:
    """모든 균열 진입 챕터 = ENTRANCE chamber_type."""
    for r in FLOOR1_RIFTS:
        ent_sa = next(
            (sa for sa in r.sub_areas if sa.id == r.entrance_id), None
        )
        assert ent_sa is not None
        assert ent_sa.chamber_type == RiftChamberType.ENTRANCE


def test_all_rifts_connections_bidirectional() -> None:
    """챕터 연결은 양방향 (★ A→B면 B의 connections에 A 포함)."""
    for r in FLOOR1_RIFTS:
        sa_by_id = {sa.id: sa for sa in r.sub_areas}
        for sa in r.sub_areas:
            for adj_id in sa.connections:
                adj = sa_by_id.get(adj_id)
                assert adj is not None, (
                    f"{r.rift_id}: {sa.id}의 연결 {adj_id} 존재 X"
                )
                assert sa.id in adj.connections, (
                    f"{r.rift_id}: {sa.id} ↔ {adj_id} 단방향 (양방향 X)"
                )


def test_floor1_definition_includes_4_rifts() -> None:
    """Floor1Definition.rifts 진짜 4종."""
    f1 = get_floor1_definition()
    assert len(f1.rifts) == 4
