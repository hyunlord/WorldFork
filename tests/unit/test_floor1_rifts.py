"""1층 균열 4종 진짜 정의 테스트.

본인 본질 (2026-05-07):
- 핏빛성채 5등급 변종 수호자 (★ 33화 본문)
- 빙하굴 7등급 예티 + 9등급 서리늑대
- 녹색탄광 8등급 고블린 광부
- 강철의 묘
"""

from __future__ import annotations

from service.game.floors.floor1 import get_floor1_definition
from service.game.floors.floor1_rifts import FLOOR1_RIFTS
from service.game.state_v2 import RiftDef, RiftEntryMethod


def _find_rift(rift_id: str) -> RiftDef | None:
    return next((r for r in FLOOR1_RIFTS if r.rift_id == rift_id), None)


def test_floor1_has_4_rifts() -> None:
    """1층 균열 4종."""
    assert len(FLOOR1_RIFTS) == 4
    ids = {r.rift_id for r in FLOOR1_RIFTS}
    assert "bloody_castle" in ids
    assert "glacier_cave" in ids
    assert "green_mine" in ids
    assert "iron_tomb" in ids


def test_bloody_castle_variant_boss() -> None:
    """핏빛성채: 5등급 변종 수호자 (★ 33화 본문)."""
    bc = _find_rift("bloody_castle")
    assert bc is not None
    assert bc.boss_grade == 5
    assert bc.boss_is_variant
    assert "캠브로미어" in bc.boss_monster_name
    assert "네크로노미콘" in bc.hidden_pieces
    assert "여신의 눈물" in bc.hidden_pieces
    assert "시체골렘" in bc.regular_monster_names


def test_glacier_cave_yeti_and_wolf() -> None:
    """빙하굴: 7등급 예티 + 9등급 서리늑대 (★ 102-110화)."""
    gc = _find_rift("glacier_cave")
    assert gc is not None
    assert "예티" in gc.regular_monster_names
    assert "서리늑대" in gc.regular_monster_names
    # ★ 보스 이름은 1차 자료 X — 빈 문자열 (정직)
    assert gc.boss_monster_name == ""


def test_green_mine_goblin_miner() -> None:
    """녹색탄광: 8등급 고블린 광부 + 녹색 보석 (★ 374화)."""
    gm = _find_rift("green_mine")
    assert gm is not None
    assert "고블린 광부" in gm.regular_monster_names
    assert "녹색 보석" in gm.hidden_pieces


def test_iron_tomb_unknown_boss() -> None:
    """강철의 묘: 자료 X 부분은 빈 문자열 (★ 정직)."""
    it = _find_rift("iron_tomb")
    assert it is not None
    assert it.boss_monster_name == ""
    assert it.regular_monster_names == ()


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


def test_floor1_definition_includes_4_rifts() -> None:
    """Floor1Definition.rifts 진짜 4종."""
    f1 = get_floor1_definition()
    assert len(f1.rifts) == 4
