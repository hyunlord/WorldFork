"""1층 균열 4종 진짜 정의.

자료 출처:
- 32-44화: 핏빛성채 본격 (★ 뱀파이어 공작 캠브로미어 5등급 변종 수호자)
- 102-110화: 빙하굴 (★ 7등급 예티 문지기, 9등급 서리늑대, 오한)
- 374화: 녹색탄광 (★ 8등급 고블린 광부, 의도적 진입)
- 456-457화: 강철의 묘
- 27화: 균열 = '미궁 속 미궁'
- 34화: 탈출 = 수호자 처치 → 포탈

★ 본인 #19 정직 정공법:
boss_monster_name이 1차 자료에 명시 X면 빈 문자열 ("").
placeholder 이름 X (★ Stage 1/2 학습 — codex가 fabricated 본질 짚을 위험).
"""

from __future__ import annotations

from ..state_v2 import RiftDef, RiftEntryMethod

# ─── 1층 균열 4종 ───


_BLOODY_CASTLE = RiftDef(
    rift_id="bloody_castle",
    name="핏빛성채",
    floor=1,
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    intentional_offering_grade=8,
    description="핏빛 성채 내부. 시체골렘 일반 + 변종 뱀파이어 수호자.",
    boss_monster_name="뱀파이어 공작 캠브로미어",  # ★ 33화 명시
    boss_grade=5,  # ★ 변종 5등급 수호자
    boss_drop_rate=0.33,
    boss_is_variant=True,  # ★ "전례가 없는 변종 균열"
    regular_monster_names=("시체골렘",),  # 8등급 일반
    hidden_pieces=("네크로노미콘", "여신의 눈물"),
)

_GLACIER_CAVE = RiftDef(
    rift_id="glacier_cave",
    name="빙하굴",
    floor=1,
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    intentional_offering_grade=8,
    description=(
        "얼어붙은 설산 + 호수 30분 도보 → 얼음 동굴. "
        "진입 시 7등급 예티 문지기. 오한 냉기 피해 환경."
    ),
    boss_monster_name="",  # ★ 1차 자료에 명시 X (정직)
    boss_grade=8,
    boss_drop_rate=0.33,
    boss_is_variant=False,
    regular_monster_names=("예티", "서리늑대"),  # 7등급 + 9등급
    hidden_pieces=(),
)

_GREEN_MINE = RiftDef(
    rift_id="green_mine",
    name="녹색탄광",
    floor=1,
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    intentional_offering_grade=8,
    description=(
        "갱도 + 철로 + 나무 폐자재. 천장 무너진 곳 시작 → 철로 따라 진행. "
        "고블린 광부 8등급 등장."
    ),
    boss_monster_name="",  # ★ 1차 자료에 명시 X (정직)
    boss_grade=8,
    boss_drop_rate=0.33,
    boss_is_variant=False,
    regular_monster_names=("고블린 광부",),
    hidden_pieces=("녹색 보석",),  # ★ 374화 300만 스톤
)

_IRON_TOMB = RiftDef(
    rift_id="iron_tomb",
    name="강철의 묘",
    floor=1,
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    intentional_offering_grade=8,
    description="강철 갑주 묘 영역. 1층 균열 4종 중 하나 (★ 456-457화).",
    boss_monster_name="",  # ★ 1차 자료에 명시 X (정직)
    boss_grade=8,
    boss_drop_rate=0.33,
    boss_is_variant=False,
    regular_monster_names=(),  # ★ 1차 자료에 명시 X
    hidden_pieces=(),
)


FLOOR1_RIFTS: tuple[RiftDef, ...] = (
    _BLOODY_CASTLE,
    _GLACIER_CAVE,
    _GREEN_MINE,
    _IRON_TOMB,
)
