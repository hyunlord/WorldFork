"""1층 (수정동굴) 진짜 정의 — 작품 본질.

본문 본질 (자료 출처):
- 11~14화: 빛/어둠 + 메시지 스톤 + 9등급 정수 흡수 + 약탈자
- 22화: 노움 (★ 1층 남쪽)
- 27화: 균열 정의 ("미궁 속 미궁")
- 50/221화: 칼날늑대
- 60/17화: 레이스
- 109/151/478/595화: 수정동굴
- 374화: 비석 공동 (★ 30m, 의도적 균열 진입)

자료 통합:
- 자동 생성: setting/location/location_수정동굴.md
- 1차 자료: 나무위키 미궁 페이지
- 디시: 1렙런 / 4렙런 빌드
"""

from __future__ import annotations

from ..state_v2 import (
    EssenceColor,
    EssenceDrop,
    Floor1Definition,
    MonsterArea,
    MonsterDef,
    MonsterGrade,
    SubArea,
)

# ─── 1층 9등급 몬스터 (★ 7종) ───


_GOBLIN = MonsterDef(
    name="고블린",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="고블린 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="조각칼 / 그르륵 / 군집 공격",
    requires_light=True,  # ★ 본문 11화 본질
)

_GOBLIN_SWORDSMAN = MonsterDef(
    name="고블린 검사",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="고블린 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="시미터 60cm / 일반 고블린보다 강력",
    requires_light=True,
)

_GOBLIN_ARCHER = MonsterDef(
    name="고블린 궁수",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="고블린 궁수 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="단궁 / 독화살 / 은신 마법 / 키키키키",
    requires_light=True,
)

_NOOM = MonsterDef(
    name="노움",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.SOUTH,  # ★ 27화 본문
    drops=(
        EssenceDrop(
            essence_name="노움 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="일체화 액티브 (★ 반경 3m 동화, 이동 X)",
    requires_light=True,
)

_SLIME = MonsterDef(
    name="슬라임",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="슬라임 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="물리 면역 / 골강도/근력/민첩 ↓ — 9등급 최악 정수 (★ 1차 자료)",
    requires_light=False,  # ★ 빛 X 활성 가능
)

_BLADE_WOLF = MonsterDef(
    name="칼날늑대",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="칼날늑대 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.GREEN,),
        ),
    ),
    behavior="후각 추적 / 야간 행동 가능",
    requires_light=False,  # ★ 추적자, 빛 X 활성
)

_WRAITH = MonsterDef(
    name="레이스",
    grade=MonsterGrade.GRADE_9,
    area=MonsterArea.GENERAL,
    drops=(
        EssenceDrop(
            essence_name="레이스 정수",
            drop_rate=0.0001,
            color_pool=(EssenceColor.BLACK,),  # ★ 어둠+화 속성
        ),
    ),
    behavior="시체불꽃 액티브 (★ 어둠+화 속성)",
    requires_light=False,  # ★ 영체, 어둠 본질
)


FLOOR1_MONSTERS: tuple[MonsterDef, ...] = (
    _GOBLIN,
    _GOBLIN_SWORDSMAN,
    _GOBLIN_ARCHER,
    _NOOM,
    _SLIME,
    _BLADE_WOLF,
    _WRAITH,
)


# ─── 1층 sub_area (★ 6 영역) ───


_PORTAL_NEAR = SubArea(
    name="포탈 근처",
    description="2층으로 향하는 포탈 주변. 빛이 자체 발산되어 가시거리 ↑.",
    accessible_from=("북쪽 통로", "남쪽 통로"),
    monster_names=("고블린", "고블린 검사"),
    is_dark=False,  # ★ 포탈 자체 빛
    has_landmark=True,
    landmark_type="포탈",
)

_NORTH_PASSAGE = SubArea(
    name="북쪽 통로",
    description="고블린 군집 영역. 어둠 기본.",
    accessible_from=("포탈 근처", "비석 공동"),
    monster_names=("고블린", "고블린 검사", "고블린 궁수"),
    is_dark=True,
    has_landmark=False,
)

_SOUTH_PASSAGE = SubArea(
    name="남쪽 통로",
    description="노움 영역. 어둠 + 좁은 통로.",
    accessible_from=("포탈 근처", "비석 공동"),
    monster_names=("노움", "슬라임"),
    is_dark=True,
    has_landmark=False,
)

_STONE_HALL = SubArea(
    name="비석 공동",
    description="반경 30m 공동 (★ 374화). 균열을 의도적으로 여는 비석 위치.",
    accessible_from=("북쪽 통로", "남쪽 통로", "동쪽 통로"),
    monster_names=(),  # ★ 안전 영역
    is_dark=True,
    has_landmark=True,
    landmark_type="비석",
)

_EAST_PASSAGE = SubArea(
    name="동쪽 통로",
    description="칼날늑대 / 레이스 영역.",
    accessible_from=("비석 공동",),
    monster_names=("칼날늑대", "레이스"),
    is_dark=True,
    has_landmark=False,
)

_ENTRANCE = SubArea(
    name="진입점",
    description="1층 시작 위치. 라프도니아 차원광장에서 연결.",
    accessible_from=("북쪽 통로",),
    monster_names=(),  # ★ 안전 영역
    is_dark=False,
    has_landmark=True,
    landmark_type="입구",
)


FLOOR1_SUB_AREAS: tuple[SubArea, ...] = (
    _ENTRANCE,
    _PORTAL_NEAR,
    _NORTH_PASSAGE,
    _SOUTH_PASSAGE,
    _STONE_HALL,
    _EAST_PASSAGE,
)


# ─── 1층 풀 정의 ───


FLOOR1_DEFINITION = Floor1Definition(
    name="수정동굴",
    floor_number=1,
    base_time_hours=168,
    base_visibility_meters=10,
    is_dark_default=True,
    sub_areas=FLOOR1_SUB_AREAS,
    monsters=FLOOR1_MONSTERS,
)


def get_floor1_definition() -> Floor1Definition:
    """1층 풀 정의 진짜 반환."""
    return FLOOR1_DEFINITION


def get_monster_by_name(name: str) -> MonsterDef | None:
    """1층 몬스터 이름으로 검색."""
    for m in FLOOR1_MONSTERS:
        if m.name == name:
            return m
    return None


def get_sub_area_by_name(name: str) -> SubArea | None:
    """sub_area 이름으로 검색."""
    for sa in FLOOR1_SUB_AREAS:
        if sa.name == name:
            return sa
    return None
