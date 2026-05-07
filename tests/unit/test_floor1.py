"""1층 진짜 정의 테스트.

본인 본질 (2026-05-07):
1층 작품 본질 정합 + Made But Never Used 차단.
"""

from __future__ import annotations

from service.game.floors.floor1 import (
    FLOOR1_MONSTERS,
    FLOOR1_SUB_AREAS,
    get_floor1_definition,
)
from service.game.state_v2 import (
    MonsterArea,
    MonsterDef,
    MonsterGrade,
    SubArea,
)


def _find_monster(name: str) -> MonsterDef | None:
    return next((m for m in FLOOR1_MONSTERS if m.name == name), None)


def _find_sub_area(name: str) -> SubArea | None:
    return next((sa for sa in FLOOR1_SUB_AREAS if sa.name == name), None)


def test_floor1_has_7_monsters() -> None:
    """1층 9등급 몬스터 7종."""
    assert len(FLOOR1_MONSTERS) == 7
    names = {m.name for m in FLOOR1_MONSTERS}
    assert "고블린" in names
    assert "노움" in names
    assert "슬라임" in names
    assert "레이스" in names
    assert "칼날늑대" in names


def test_floor1_all_monsters_grade_9() -> None:
    """모든 1층 일반 몬스터 9등급."""
    for m in FLOOR1_MONSTERS:
        assert m.grade == MonsterGrade.GRADE_9


def test_noom_in_south() -> None:
    """노움은 남쪽 영역 (★ 27화 본문)."""
    noom = _find_monster("노움")
    assert noom is not None
    assert noom.area == MonsterArea.SOUTH


def test_wraith_no_light_required() -> None:
    """레이스는 영체 — 빛 X 활성 (★ 어둠 본질)."""
    wraith = _find_monster("레이스")
    assert wraith is not None
    assert not wraith.requires_light


def test_blade_wolf_no_light_required() -> None:
    """칼날늑대는 후각 추적 — 빛 X 활성."""
    bw = _find_monster("칼날늑대")
    assert bw is not None
    assert not bw.requires_light


def test_floor1_has_6_sub_areas() -> None:
    """1층 sub_area 6개."""
    assert len(FLOOR1_SUB_AREAS) == 6
    names = {sa.name for sa in FLOOR1_SUB_AREAS}
    assert "진입점" in names
    assert "비석 공동" in names
    assert "포탈 근처" in names


def test_stone_hall_landmark() -> None:
    """비석 공동에 비석 (★ 374화 본문)."""
    sh = _find_sub_area("비석 공동")
    assert sh is not None
    assert sh.has_landmark
    assert sh.landmark_type == "비석"


def test_portal_near_not_dark() -> None:
    """포탈 근처는 빛 자체 발산 (★ 어둠 X)."""
    pn = _find_sub_area("포탈 근처")
    assert pn is not None
    assert not pn.is_dark


def test_get_floor1_definition_complete() -> None:
    """풀 정의 진짜 반환."""
    f1 = get_floor1_definition()
    assert f1.name == "수정동굴"
    assert len(f1.monsters) == 7
    assert len(f1.sub_areas) == 6
    assert f1.is_dark_default
    assert f1.base_time_hours == 168


def test_get_monster_by_name_not_found() -> None:
    assert _find_monster("존재하지 않는 몬스터") is None


def test_get_sub_area_by_name_not_found() -> None:
    assert _find_sub_area("존재하지 않는 영역") is None
