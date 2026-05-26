"""1층 균열 4종 진짜 정의 (★ Phase 8 A1 — namu 6장 본격 정합).

자료 출처:
- 32-44화: 핏빛성채 본격 (★ 뱀파이어 공작 캠보르미어 5등급 변종 수호자)
- 102-110화: 빙하굴 (★ 7등급 수호자 폭군 타룬바스, 9등급 서리 늑대)
- 374화: 녹색 탄광 (★ 8등급 고블린 광부, 의도적 진입)
- 456-457화: 강철의 묘
- 27화: 균열 = '미궁 속 미궁'
- 34화: 탈출 = 수호자 처치 → 포탈
- 나무위키 "게임 속 바바리안으로 살아남기/설정/미궁" (2026-05-13)
  - 챕터 구조 + 일반/변종 수호자 분리 + 보상 본격

★ Phase 8 A1 변경 (docs/floor1_rifts_spec.md 정합):
- boss_monster_name (단일) → normal_boss_name + variant_boss_name 분리
- sub_areas: tuple[RiftSubAreaDef, ...] — namu 본격 챕터 구조
- party_capacity = 5 (★ 본인 결정)
- intentional_offering_source_floor/area (★ 2층 망자의 땅 등)
- essence_color (★ 보상 정수 색)
- boss_weakness (★ 폭군 타룬바스 전격 등)

★ 표기 통일 (2026-05-13): namu 1차 자료 "캠보르미어" 채택.
"""

from __future__ import annotations

import random

from ..state_v2 import (
    BossWeakness,
    RiftChamberType,
    RiftDef,
    RiftEntryMethod,
    RiftSubAreaDef,
    VariantTrigger,
)

# ─── 1. 핏빛성채 (bloody_castle) — namu 6.1.1, 5 챕터 ───


_BLOODY_CASTLE = RiftDef(
    rift_id="bloody_castle",
    name="핏빛성채",
    floor=1,
    normal_boss_name="저주받은 기사 블라터",
    # ★ namu 명시 X — 챕터 5 본 나이트 7등급 → 일반 보스 6 추정 (★ 후속 진단)
    normal_boss_grade=6,
    variant_possible=True,
    variant_boss_name="뱀파이어 공작 캠보르미어",
    variant_boss_grade=5,  # ★ namu "전례 없는 변종 균열" + 기존 코드 정합
    variant_trigger=VariantTrigger(base_probability=0.02),  # ★ A2 — namu "매우 드물게"
    entrance_id="bc_ch1",
    boss_chamber_id="bc_ch5",
    sub_areas=(
        RiftSubAreaDef(
            id="bc_ch1",
            name="외곽 검문소",
            chamber_type=RiftChamberType.ENTRANCE,
            description="핏빛 성채 외곽 검문소. 데드맨 무리.",
            connections=("bc_ch2",),
            monsters=("데드맨", "병사 데드맨", "지휘관 데드맨"),
        ),
        RiftSubAreaDef(
            id="bc_ch2",
            name="도개교",
            chamber_type=RiftChamberType.CORRIDOR,
            description=(
                "뿔피리 불면 도개교↓ + 수성 마법진 활성. "
                "핏물 위 데드맨이 기어옴 — 도개교 내려올 때까지 버티기."
            ),
            connections=("bc_ch1", "bc_ch3"),
            monsters=("데드맨",),
        ),
        RiftSubAreaDef(
            id="bc_ch3",
            name="외성벽 시가지",
            chamber_type=RiftChamberType.CORRIDOR,
            description="한 무리당 수십 마리. 9-8등급 언데드 군집.",
            connections=("bc_ch2", "bc_ch4"),
            monsters=(
                "스켈레톤 아처",
                "스켈레톤 메이지",
                "구울",
                "데스핀드",
            ),
        ),
        RiftSubAreaDef(
            id="bc_ch4",
            name="내성벽 지하 감옥",
            chamber_type=RiftChamberType.MID_BOSS,
            description="중간 보스 시체골렘 (7등급).",
            connections=("bc_ch3", "bc_ch5"),
            monsters=(
                "스컬 랫",
                "벤시",
                "데스핀드",
                "키메라 울프",
                "구울로드",
            ),
            mid_boss_name="시체골렘",
            mid_boss_grade=7,
        ),
        RiftSubAreaDef(
            id="bc_ch5",
            name="영주성 악마 숭배실",
            chamber_type=RiftChamberType.BOSS,
            description="'ㅁ' 자 구조. 마지막 챕터, 수호자 출현.",
            connections=("bc_ch4",),
            monsters=(
                "가고일 석상",
                "데스핀드",
                "키메라 울프",
                "본 나이트",
            ),
        ),
    ),
    intentional_offering_source_floor=2,
    intentional_offering_source_area="망자의 땅",
    intentional_offering_grade=8,
    essence_color="red",
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    party_capacity=5,
    boss_drop_rate=0.33,
    description=(
        "핏빛 성채 내부 (★ 1층 균열, 5 챕터). "
        "외곽 검문소 → 도개교 → 외성벽 시가지 → 내성벽 지하 감옥 → "
        "영주성 악마 숭배실. 일반: 저주받은 기사 블라터, "
        "변종: 뱀파이어 공작 캠보르미어 (5등급 — 라스카니아 최초 전례)."
    ),
)


# ─── 2. 빙하굴 (glacier_cave) — namu 6.1.2, 4 챕터 ───


_GLACIER_CAVE = RiftDef(
    rift_id="glacier_cave",
    name="빙하굴",
    floor=1,
    normal_boss_name="폭군 타룬바스",
    # ★ namu "수호자조차 7등급에 불과" 명시 (★ 1층 균열 중 가장 쉬움)
    normal_boss_grade=7,
    variant_possible=True,
    variant_boss_name="타락한 짐승 키르뒤",
    variant_boss_grade=None,  # ★ namu 명시 X (★ 후속 진단)
    variant_trigger=VariantTrigger(base_probability=0.02),  # ★ A2 — namu "매우 드물게"
    boss_weakness=BossWeakness(
        element="전격",
        note="폭군 타룬바스 — namu 명시 전격 속성 약점",
    ),
    entrance_id="gc_ch1",
    boss_chamber_id="gc_ch4",
    sub_areas=(
        RiftSubAreaDef(
            id="gc_ch1",
            name="동굴 입구",
            chamber_type=RiftChamberType.ENTRANCE,
            description=(
                "문지기 예티 처치 후 얼음 동굴 진입. "
                "1층 수정동굴 유사 지형 — 기둥으로 길 찾기."
            ),
            connections=("gc_ch2",),
            monsters=("서리 늑대", "예티"),
        ),
        RiftSubAreaDef(
            id="gc_ch2",
            name="지하 + 토템",
            chamber_type=RiftChamberType.MID_BOSS,
            description=(
                "얼음 계단 → 지하. 세 번째 기둥 부수면 영약 (1회 한 냉기 "
                "저항↑). 토템 30분 9 웨이브 → 중간 보스 상위 변이종 예티. "
                "마지막 웨이브에 천장 균열에 폭군 타룬바스 등장 → "
                "지면 붕괴 → 3챕터 추락."
            ),
            connections=("gc_ch1", "gc_ch3"),
            monsters=(
                "서리 늑대",
                "샤벨 타이거",
                "웜스톤",
                "아이스 골렘",
                "예티",
            ),
            mid_boss_name="상위 변이종 예티",
            mid_boss_grade=None,
            hidden_pieces=("냉기 저항 영약",),
        ),
        RiftSubAreaDef(
            id="gc_ch3",
            name="지하수맥 동굴",
            chamber_type=RiftChamberType.CORRIDOR,
            description=(
                "미끄럽고 입체적. 메인 통로 + 급경사 + 로프 구간. "
                "아이스 오크 3마리 (주술사 1, 전사 2)가 얼음 기둥에서 깨어남."
            ),
            connections=("gc_ch2", "gc_ch4"),
            monsters=(
                "샤벨 타이거",
                "웜스톤",
                "아울베어",
                "아이스 오크",
                "아이스 오크 주술사",
            ),
            field_effect=(
                "저체온증 — 냉기 내성 X 시 민첩 최대 -30, 받는 냉기 2배. "
                "지하수맥 폭포 추락 HP↓."
            ),
        ),
        RiftSubAreaDef(
            id="gc_ch4",
            name="보스방",
            chamber_type=RiftChamberType.BOSS,
            description=(
                "천장 얼음 가루 → 수호자 등장. "
                "폭군 타룬바스 — 라이칸스로프 기반, 1.5배 크기 + 2배 스탯, "
                "얼음 몽둥이, 두꺼운 서리, 전격 속성 약점."
            ),
            connections=("gc_ch3",),
            monsters=("서리 늑대",),
        ),
    ),
    intentional_offering_source_floor=2,
    intentional_offering_source_area="짐승의 소굴",
    intentional_offering_grade=8,
    essence_color="blue",
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    party_capacity=5,
    boss_drop_rate=0.33,
    description=(
        "얼어붙은 설산 + 호수 30분 도보 → 굴 (★ 102-110화). "
        "1층 균열 중 가장 쉬움 (수호자 7등급). "
        "동굴 입구 → 지하/토템 → 지하수맥 → 보스방. "
        "일반: 폭군 타룬바스, 변종: 타락한 짐승 키르뒤."
    ),
)


# ─── 3. 녹색 탄광 (green_mine) — namu 6.1.3, 4 챕터 ───


_GREEN_MINE = RiftDef(
    rift_id="green_mine",
    name="녹색 탄광",
    floor=1,
    normal_boss_name="킹 슬라임",
    # ★ namu 명시 X — 챕터 4 슬라임 9등급 → 일반 보스 8 임시 (★ 후속 진단)
    normal_boss_grade=8,
    variant_possible=True,
    variant_boss_name=None,  # ★ namu/본인 둘 다 X (★ 후속 진단)
    variant_boss_grade=None,
    entrance_id="gm_ch1",
    boss_chamber_id="gm_ch4",
    sub_areas=(
        RiftSubAreaDef(
            id="gm_ch1",
            name="입구 갱도",
            chamber_type=RiftChamberType.ENTRANCE,
            description=(
                "일자 갱도. 천장 무너진 곳에서 시작 → 철로 따라 진행. "
                "히든 피스: 철로 끊긴 지점 벽 박살 → 샛길 → 300만 스톤 "
                "초록색 보석."
            ),
            connections=("gm_ch2",),
            monsters=("고블린 광부",),
            hidden_pieces=("green_gem_3m_stone",),
        ),
        RiftSubAreaDef(
            id="gm_ch2",
            name="무너진 다리",
            chamber_type=RiftChamberType.MID_BOSS,
            description=(
                "3분의 2 무너진 다리. 정공: 옆 통로 우회 / 스킵: 중급 "
                "이상 이동기. 중간 보스: 고블린 폭탄병 (6등급). "
                "히든 피스: 중간 보스방 주변 광물 박살 → 고블 쿼츠."
            ),
            connections=("gm_ch1", "gm_ch3"),
            monsters=(
                "고블린 광부",
                "광물 슬라임",
                "홉고블린 광부",
                "코퍼 골렘",
            ),
            mid_boss_name="고블린 폭탄병",
            mid_boss_grade=6,
            hidden_pieces=("gobl_quartz",),
        ),
        RiftSubAreaDef(
            id="gm_ch3",
            name="절벽 갱도",
            chamber_type=RiftChamberType.CORRIDOR,
            description="절벽 가장자리 원형 계단. 몬스터 처치 전진.",
            connections=("gm_ch2", "gm_ch4"),
            monsters=(),
        ),
        RiftSubAreaDef(
            id="gm_ch4",
            name="보스방",
            chamber_type=RiftChamberType.BOSS,
            description=(
                "탄광 최심 무너진 갱도. 폭발물로 길 열기 "
                "(고렙은 그냥 부숨). 50m 반경 공동."
            ),
            connections=("gm_ch3",),
            monsters=("슬라임",),
        ),
    ),
    intentional_offering_source_floor=2,
    intentional_offering_source_area="고블린 숲",
    intentional_offering_grade=8,
    essence_color="green",
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    party_capacity=5,
    boss_drop_rate=0.33,
    description=(
        "바닥 철로 + 나무 폐자재 + 음산 (★ 374화). "
        "입구 갱도 → 무너진 다리 → 절벽 갱도 → 보스방. "
        "일반: 킹 슬라임. (★ 변종 본문 X — 후속 진단)"
    ),
)


# ─── 4. 강철의 묘 (iron_tomb) — namu 6.1.4, 4 챕터 ───


_IRON_TOMB = RiftDef(
    rift_id="iron_tomb",
    name="강철의 묘",
    floor=1,
    normal_boss_name="철인 일디움",
    # ★ namu 명시 X — 챕터 1-3 7등급 → 일반 보스 8 임시 (★ 후속 진단)
    normal_boss_grade=8,
    variant_possible=True,
    variant_boss_name=None,  # ★ namu/본인 둘 다 X (★ 후속 진단)
    variant_boss_grade=None,
    entrance_id="it_ch1",
    boss_chamber_id="it_ch4",
    sub_areas=(
        RiftSubAreaDef(
            id="it_ch1",
            name="복도 1",
            chamber_type=RiftChamberType.ENTRANCE,
            description=(
                "사방 어둡고 좁은 복도. 피라미드 내부 느낌. "
                "벽 = 금속 재질 + 벽화 같은 문양. "
                "함정 해체 정공 / 고렙은 밟아 없앰."
            ),
            connections=("it_ch2",),
            monsters=("수수께끼 문지기", "머미"),
        ),
        RiftSubAreaDef(
            id="it_ch2",
            name="복도 2",
            chamber_type=RiftChamberType.CORRIDOR,
            description="함정 + 복도. 묘실 향함.",
            connections=("it_ch1", "it_ch3"),
            monsters=("머미", "배리드언", "수호자의 눈"),
        ),
        RiftSubAreaDef(
            id="it_ch3",
            name="복도 3",
            chamber_type=RiftChamberType.CORRIDOR,
            description="복도 최심. 철기병/아이언 리자드맨 출현.",
            connections=("it_ch2", "it_ch4"),
            monsters=("철기병", "아이언 리자드맨"),
        ),
        RiftSubAreaDef(
            id="it_ch4",
            name="강철의 분묘",
            chamber_type=RiftChamberType.BOSS,
            description="마지막 챕터. 철인 일디움 출현.",
            connections=("it_ch3",),
            monsters=(),
        ),
    ),
    intentional_offering_source_floor=2,
    intentional_offering_source_area="바위사막",
    intentional_offering_grade=8,
    essence_color="yellow",
    entry_methods=(
        RiftEntryMethod.RANDOM_NATURAL,
        RiftEntryMethod.INTENTIONAL_OFFERING,
    ),
    party_capacity=5,
    boss_drop_rate=0.33,
    description=(
        "강철 갑주 묘 영역 (★ 456-457화). 4 챕터. "
        "복도 1-3 → 강철의 분묘. "
        "일반: 철인 일디움. (★ 변종 본문 X — 후속 진단)"
    ),
)


# ─── 통합 ───


FLOOR1_RIFT_DEFS: dict[str, RiftDef] = {
    _BLOODY_CASTLE.rift_id: _BLOODY_CASTLE,
    _GLACIER_CAVE.rift_id: _GLACIER_CAVE,
    _GREEN_MINE.rift_id: _GREEN_MINE,
    _IRON_TOMB.rift_id: _IRON_TOMB,
}


# ★ 기존 floor1.py 호환 — Floor1Definition.rifts: tuple[RiftDef, ...]
FLOOR1_RIFTS: tuple[RiftDef, ...] = tuple(FLOOR1_RIFT_DEFS.values())


# ─── Phase 8 A2: variant spawn 결정 ───


def decide_variant(
    rift_def: RiftDef,
    rng: random.Random | None = None,
) -> bool:
    """변종 균열 여부 결정 (★ Phase 8 A2).

    본 commit: 단순 base_probability (★ namu '매우 드물게').
    후속: trigger condition (★ defeated_bosses / floor_clears).

    rng=None 시 모듈 random — caller가 test 시 Random(seed) inject 본격.
    """
    if rift_def.variant_trigger is None:
        return False
    if rift_def.variant_boss_name is None:
        # 변종 보스 정의 X 시 variant 결정 X (★ namu/본인 X)
        return False
    if rng is None:
        return random.random() < rift_def.variant_trigger.base_probability
    return rng.random() < rift_def.variant_trigger.base_probability
