"""라프도니아 도시 정의 (★ Phase 8 (a-2)).

본 commit 본문 정합 (★ docs/village_spec.md §7 + .local/novel_bodies/):
- 3화: "라프도니아......" 도시 진입
- 16화: 에르웬 본격 본격
- 19화: "매월 1일 자정 미궁 열림, 한 달 정확히 30일"
- 127화: "현재 거주 중인 7구역"
- 162화: "7구역의 중앙 광장. 모임 장소" + "오늘은 미궁이 열리는 날"
- namu §4.3: 시설 18개 (★ 본 commit 9개 선택)
- namu §7.1: 탐험가 길드 본점
- namu §4.3: 라비기온 중앙 도서관 — 사서 라그나

본 commit data-only. Location.city_id / 환전 mechanism / gm_agent prompt 본격
후속 (a-3) commit.

작품 IP masking (★ docs/PHASE_C_LAUNCH_GUIDE 7장 정합):
- 본 commit은 1차 자료 매핑 본격 — 비식별 layer는 service/pipeline/ip_masking.py 본격.
"""

from __future__ import annotations

from .city_definition import CityDefinition, CitySubAreaDef, NPCDef

# ─── NPCs (★ 4 canonical 본문 인물 + 5 직책만) ───

RAPDONIA_NPCS: tuple[NPCDef, ...] = (
    # ── 본문 등장 인물 (★ is_canonical=True) ──
    NPCDef(
        id="aenar",
        name="아이나르",
        role="barbarian_companion",
        sub_area_id="district_7_plaza",
        dialogue_intro="프넬린의 두 번째 딸 — 바바리안 동료 (★ 3화).",
        is_canonical=True,
    ),
    NPCDef(
        id="erwen",
        name="에르웬",
        role="party_companion",
        sub_area_id="district_7_plaza",
        dialogue_intro="비요른의 동료 — 요정 (★ 16/18화). 회계/세금 정보.",
        is_canonical=True,
    ),
    NPCDef(
        id="misha",
        name="미샤",
        role="city_native",
        sub_area_id="district_7_plaza",
        dialogue_intro="적묘족 수인 — 7구역 거주 (★ 127화 동행).",
        is_canonical=True,
    ),
    NPCDef(
        id="ragna",
        name="라그나",
        role="librarian",
        sub_area_id="central_library",
        dialogue_intro=(
            "라비기온 중앙 도서관 사서 — 서적 탐지 마법 사용 (★ namu §4.3)."
        ),
        is_canonical=True,
    ),
    # ── 직책만 (★ is_canonical=False — 본문 등장 X 이름) ──
    NPCDef(
        id="exchange_clerk",
        name="환전소 직원",
        role="exchange_clerk",
        sub_area_id="exchange_office",
        is_canonical=False,
    ),
    NPCDef(
        id="innkeeper",
        name="여관 주인",
        role="innkeeper",
        sub_area_id="inn",
        is_canonical=False,
    ),
    NPCDef(
        id="blacksmith_master",
        name="대장장이",
        role="blacksmith",
        sub_area_id="blacksmith",
        is_canonical=False,
    ),
    NPCDef(
        id="store_owner",
        name="잡화점 주인",
        role="general_store_owner",
        sub_area_id="general_store",
        is_canonical=False,
    ),
    NPCDef(
        id="market_broker",
        name="알미너스 거래소 중개인",
        role="market_broker",
        sub_area_id="alminus_market",
        is_canonical=False,
    ),
    # ── Phase 9.5 삼신교 사제 (★ 268/55/72화 정합) ──
    NPCDef(
        id="rairin_ersina",
        name="라이린 에르시나",
        role="priest",
        sub_area_id="toberah_temple",
        dialogue_intro=(
            "토베라 교단 정사제 — 바바리안 거절 규율 (★ 268화)."
        ),
        is_canonical=True,
    ),
    NPCDef(
        id="reatlas_priest",
        name="레아틀라스 사제",
        role="priest",
        sub_area_id="reatlas_temple",
        is_canonical=False,
    ),
    NPCDef(
        id="elisa",
        name="엘리사",
        role="priest",
        sub_area_id="karuyi_temple",
        dialogue_intro="카루이 사제 (★ 72화).",
        is_canonical=True,
    ),
)


# ─── Sub Areas (★ 9개 — namu §4.3 + 본문 162화) ───

RAPDONIA_SUB_AREAS: tuple[CitySubAreaDef, ...] = (
    CitySubAreaDef(
        id="district_7_plaza",
        name="라프도니아 7구역 중앙 광장",
        description=(
            "매월 1일 자정 미궁 포탈이 열리는 광장 (★ 19화). "
            "모임 장소로 많이 쓰는 곳 (★ 162화). "
            "동료를 기다리는 탐험가들이 바글바글하다."
        ),
        connections=(
            "explorer_guild_branch",
            "exchange_office",
            "inn",
            "general_store",
            "tavern",
            "central_library",
            # ★ Phase 9.5 삼신교 (★ 268화)
            "toberah_temple",
            "reatlas_temple",
            "karuyi_temple",
        ),
        npc_ids=("aenar", "erwen", "misha"),
    ),
    CitySubAreaDef(
        id="explorer_guild_branch",
        name="탐험가 길드 7구역 본점",
        description=(
            "탐험가 등록, 의뢰, 정수 표준가 조회 (★ namu §7.1). "
            "재난 지원금 + 현상금 중개."
        ),
        connections=("district_7_plaza",),
    ),
    CitySubAreaDef(
        id="exchange_office",
        name="환전소",
        description=(
            "마석 → 스톤 환전 (★ namu §2.2). "
            "9등급 마석 = 20 스톤, 8등급 마석 = 100 스톤."
        ),
        connections=("district_7_plaza", "alminus_market"),
        npc_ids=("exchange_clerk",),
    ),
    CitySubAreaDef(
        id="alminus_market",
        name="알미너스 중앙 거래소",
        description=(
            "컴멜비 본부 — 정수/마석/장비 본격 거래 (★ namu §4.3). "
            "검색 3천 스톤 / 감정 30만 스톤."
        ),
        connections=("exchange_office",),
        npc_ids=("market_broker",),
    ),
    CitySubAreaDef(
        id="inn",
        name="여관",
        description=(
            "숙박 + 식사 (★ 16화). "
            "컴멜비 본격 1박 9천 스톤 (★ namu §4.3)."
        ),
        connections=("district_7_plaza", "tavern"),
        npc_ids=("innkeeper",),
    ),
    CitySubAreaDef(
        id="blacksmith",
        name="대장간",
        description=(
            "무기/방어구 제작 + 수리 (★ namu §4.3). "
            "대형 대장간은 특정 클랜 전담."
        ),
        connections=("general_store",),
        npc_ids=("blacksmith_master",),
    ),
    CitySubAreaDef(
        id="general_store",
        name="잡화점",
        description=(
            "전리품 처분 + 포션/소모품 구매 (★ namu §4.3). "
            "횃불/식량/기본 탐사 용품."
        ),
        connections=("district_7_plaza", "blacksmith"),
        npc_ids=("store_owner",),
    ),
    CitySubAreaDef(
        id="central_library",
        name="라비기온 중앙 도서관",
        description=(
            "라비기온 남부 — 서적 탐지 마법 (★ namu §4.3). "
            "수수료 3천 스톤. 사서 라그나 1인."
        ),
        connections=("district_7_plaza",),
        npc_ids=("ragna",),
    ),
    CitySubAreaDef(
        id="tavern",
        name="주점",
        description=(
            "팀 우호 + 전리품 분배 + 정보 교류 (★ namu §4.3). "
            "여관 겸하기도 함."
        ),
        connections=("district_7_plaza", "inn"),
    ),
    # ── Phase 9.5 삼신교 (★ 268화 라프도니아 세 교단) ──
    CitySubAreaDef(
        id="toberah_temple",
        name="토베라 신전",
        description=(
            "삼신교 본격 신전 (★ 268화). "
            "정사제 라이린 에르시나. 바바리안 거절 규율."
        ),
        connections=("district_7_plaza",),
        npc_ids=("rairin_ersina",),
    ),
    CitySubAreaDef(
        id="reatlas_temple",
        name="레아틀라스 신전",
        description=(
            "삼신교 본격 신전 (★ 55화). 탐험의 신, 선 성향."
        ),
        connections=("district_7_plaza",),
        npc_ids=("reatlas_priest",),
    ),
    CitySubAreaDef(
        id="karuyi_temple",
        name="카루이 신전",
        description=(
            "삼신교 본격 신전 (★ 72화). 사제 엘리사."
        ),
        connections=("district_7_plaza",),
        npc_ids=("elisa",),
    ),
)


# ─── City Definition (★ 본 commit data 핵심) ───

RAPDONIA: CityDefinition = CityDefinition(
    city_id="rapdonia",
    city_name="라프도니아",
    entry_sub_area="district_7_plaza",
    sub_areas=RAPDONIA_SUB_AREAS,
    npcs=RAPDONIA_NPCS,
)
