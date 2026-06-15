"""WORLDFORK_PACK 조립 — 엔진이 소비하는 WorldFork 데이터 전체(SSOT, A1.2c로 팩 완성).

엔진(narrative_gm·gm_session_router·opening_canon 로직·scene_effect·rag·ip)이 이 팩을
require_active_pack()으로 소비한다. 여기 정의가 원본이고 엔진 모듈엔 WorldFork 하드코딩이 없다.
타입(Beat/BeatAnchor/SceneDetail/WeaponChoice/BeatChoice 등 메커니즘)은 엔진 소유 — 여기선 데이터만.
★ IP: 코드·git = 변환명(투르윈/카이라). 화면 노출은 프론트 unmaskIp.
"""

from __future__ import annotations

from service.engine.content_pack import CompanionSpec, ContentPack, FoeSpec, RagConfig
from service.sim.disposition import Disposition
from service.sim.opening_canon import (
    Beat,
    BeatAnchor,
    BeatChoice,
    SceneDetail,
    WeaponChoice,
)

# 변환명(화면 unmask: 투르윈→비요른, 카이라→아이나르).
_PLAYER_NAME = "투르윈"
_KAIRA_NAME = "카이라"

# 동행 동료 카이라(아이나르) 5축 — WORLD_BIBLE §11(충성80/저돌75/지혜35/변덕25/유대65).
_KAIRA_DISPOSITION = Disposition(
    loyalty=80,
    aggression=75,
    wisdom=35,
    whimsy=25,
    bond=65,
    background="흑곰족 대검 전사, 성인식 동기. 우직·강직, 돌격 본능에 신중함은 부족.",
)

# GM 시스템 프롬프트(페르소나+출력계약 블렌드) — narrative_gm이 build_gm_prompt에서 소비.
_GM_SYSTEM_PERSONA = (
    "# 역할\n"
    "당신은 한국 web novel '게임 속 바바리안으로 살아남기' 세계의 게임 마스터(GM)다. "
    "장면을 1인칭('나는') 문어체 한국어로 펼치고, 플레이어의 선택을 받아 진전시킨다. "
    "메타·시스템·규칙 설명·AI 자칭·사과는 금지한다.\n\n"
    "# 톤\n"
    "냉소·실리주의 + 생존 긴장 + 바바리안 위장 코미디(우직한 야만인을 연기하나 속은 계산적). "
    "시스템 고지는 낫표 「」 합쇼체로 쓴다(예: 「성인식이 시작됩니다.」).\n\n"
    "# 캐논 고정\n"
    "아래 앵커만 근거로 삼는다. 근거 없는 새 고유명사·설정 확정은 금지.\n{anchor}\n\n"
    "{grounding}"
    "# 끌개\n"
    "[목표]를 향해 부드럽게 견인하되 강제하지 않는다. 플레이어가 다른 길을 택하면 막지 말고 "
    "자연스럽게 이어 가되, 적절한 때 [목표]가 다른 형태로 다시 다가오게 한다.\n"
    "★ 플레이어가 무언가를 확정·획득·결정하면(예: 무기 선택, 처치, 합의) 그 변화를 반드시 "
    "state_delta(flags/inventory_add/relationship_delta)에 싣는다.\n"
    "★ 플레이어 입력이 현 장면에서 불가능하거나 장면 밖이면(예: 동굴에서 갑자기 왕을 만난다) "
    "막지 말고, 그 시도를 장면 안의 결과로 받아 재유도한다(장면 밖으로 끌려가지 않음).\n\n"
    "# 출력 계약 (엄수)\n"
    "★ 너는 '서술'만 한다. 선택지·상태 수치·무기/아이템 보유·진행 단계는 코드가 정한다 — "
    "지어내지 마라(특히 무기·장비·성인식 완료 여부). 주어진 [무기]·[상태]에만 맞춰 묘사한다.\n"
    "- narration: 장면 서술(2~5문장, 전투·중대 장면은 더 길게 허용).\n"
    "- state_delta: 관계 변화만 선택적으로. relationship_delta(이름:정수), "
    "inventory_add(서사상 자연히 얻은 물건만). ★ flags·hp·무기는 넣지 마라(코드 소관).\n"
    "- speaker: 핵심 화자 이름(포트레이트용, 없으면 생략).\n"
    "- illustration: 이 순간에 띄울 스틸(아래 목록 중 하나만, 없으면 생략): {illustrations}."
)

# 전투/장면 스틸 자산(public/assets/worldfork/<key>.png). narrative_gm이 화이트리스트로 소비.
_ILLUSTRATION_KEYS: frozenset[str] = frozenset({
    "ui_gameplay_bg_crystal",
    "ui_combat_bjorn_action",
    "ui_combat_vfx_axe_strike",
    "ui_combat_vfx_magic_missile",
    "ui_combat_monster_goblin",
    "ui_combat_monster_blade_wolf",
    "ui_combat_monster_ghoul",
    "ui_combat_monster_gnome",
})

# ── 캐논 인덱스(오프닝 4비트) — opening_canon 로직이 소비 ──────────────────────────
_BEATS: tuple[Beat, ...] = (
    Beat.COMING_OF_AGE,
    Beat.DUNGEON_ENTRY,
    Beat.FIRST_ENCOUNTER,
    Beat.AFTERMATH,
)

_ANCHORS: dict[Beat, BeatAnchor] = {
    Beat.COMING_OF_AGE: BeatAnchor(
        Beat.COMING_OF_AGE,
        goal=f"{_PLAYER_NAME}이 부족장 앞 성인식에서 무기를 골라 전사로 인정받는다.",
        scene="흑곰족 성지. 부족장이 청년들을 호명한다. 무기대에 양손도끼·양손망치·대검이 놓였다.",
        hint="무기 선택(=빌드)을 선택지로. 우직한 야만인을 연기하나 속은 계산적인 톤.",
    ),
    Beat.DUNGEON_ENTRY: BeatAnchor(
        Beat.DUNGEON_ENTRY,
        goal="일행이 한 달 만에 열린 미궁 1층 수정 동굴에 발을 들인다.",
        scene="미궁 1층. 벽의 수정이 스스로 빛나 횃불이 필요 없다. 통로가 어둠 속으로 뻗는다.",
        hint="탐색 방향·경계 태세를 선택지로. 미궁 한 달 주기·생존 긴장을 깐다.",
    ),
    Beat.FIRST_ENCOUNTER: BeatAnchor(
        Beat.FIRST_ENCOUNTER,
        goal="첫 조우(고블린/칼날늑대)와 교전한다. 무기·동료 운용이 생사를 가른다.",
        scene="수정 동굴 깊은 곳. 어둠 속에서 첫 몬스터가 모습을 드러낸다.",
        hint="전술 결정(돌격/엄호/거리)을 선택지로. 전투는 생생히, 더 길게 묘사.",
    ),
    Beat.AFTERMATH: BeatAnchor(
        Beat.AFTERMATH,
        goal=f"교전을 매듭짓고 {_KAIRA_NAME}와의 관계·전리품을 정리한다.",
        scene="조우가 끝난 자리. 마석과 정수가 떨어져 있고, 동료가 곁에 선다.",
        hint="전리품 처리·동료와의 한마디를 선택지로. 결과를 세계에 남긴다.",
    ),
}

_SCENE_DETAILS: dict[Beat, tuple[SceneDetail, ...]] = {
    Beat.COMING_OF_AGE: (
        SceneDetail(
            "weapon_rack", "무기대에 양손도끼·양손망치·대검이 가지런히 놓여 빛을 받는다."
        ),
        SceneDetail("chieftain_gaze", "부족장이 청년들을 차례로 훑어보며 호명을 기다린다."),
    ),
    Beat.DUNGEON_ENTRY: (
        SceneDetail(
            "crystal_light", "벽을 메운 수정이 맥동하듯 빛을 토해 통로 깊은 곳까지 비춘다."
        ),
        SceneDetail(
            "drag_marks", "바닥에 길게 긁힌 자국이 어둠 속으로 이어진다 — 끌려간 흔적."
        ),
        SceneDetail(
            "crystal_shard",
            "발치에 손바닥만 한 수정 파편이 떨어져 희미하게 빛난다.",
            item="수정 파편",
        ),
    ),
    Beat.FIRST_ENCOUNTER: (
        SceneDetail("foe_shadow", "어둠 속에서 낮은 그르렁거림과 함께 윤곽이 다가온다."),
        SceneDetail("narrow_path", "통로가 좁아 물러설 곳이 마땅치 않다 — 정면 승부다."),
    ),
    Beat.AFTERMATH: (
        SceneDetail("spoils", "쓰러진 적 곁에 마석과 정수가 흩어져 있다."),
        SceneDetail("companion_breath", "카이라가 거친 숨을 고르며 곁에 선다."),
    ),
}

# 성인식 무기 — 빌드 분기(WORLD_BIBLE §3.2 탱커/딜러 딜레마).
_WEAPONS: tuple[WeaponChoice, ...] = (
    WeaponChoice("axe", "양손도끼", "균형(탱커형 생존)"),
    WeaponChoice("hammer", "양손망치", "고화력 둔기"),
    WeaponChoice("greatsword", "대검", "고위험 고화력 딜러"),
)

# 비전투/전투 스캐폴드 선택지(성인식은 weapons에서 동적 생성 — opening_canon.beat_choices).
_BEAT_CHOICES: dict[Beat, tuple[BeatChoice, ...]] = {
    Beat.DUNGEON_ENTRY: (
        BeatChoice("advance", "미궁 깊숙이 나아간다"),
        BeatChoice("scout", "벽의 수정과 통로를 살핀다"),
        BeatChoice("guard", "카이라에게 선두 경계를 맡기고 전진한다"),
    ),
    Beat.FIRST_ENCOUNTER: (
        BeatChoice("charge", "도끼로 정면 돌격한다"),
        BeatChoice("flank", "카이라와 좌우로 협공한다"),
        BeatChoice("careful", "거리를 두고 빈틈을 노린다"),
        BeatChoice("defend", "방어 태세로 적의 공격을 받아친다"),
    ),
    Beat.AFTERMATH: (
        BeatChoice("loot", "쓰러진 적의 전리품을 챙긴다"),
        BeatChoice("talk", "카이라와 한마디 나눈다"),
        BeatChoice("descend", "미궁 더 깊은 곳으로 향한다"),
    ),
}

WORLDFORK_PACK = ContentPack(
    pack_id="worldfork",
    gm_system_persona=_GM_SYSTEM_PERSONA,
    first_foe=FoeSpec(name="고블린", hp=36, attack=8, essence_drop="고블린 정수"),
    companion=CompanionSpec(
        name=_KAIRA_NAME, disposition=_KAIRA_DISPOSITION, hp=140, attack=14
    ),
    grounding_episode_range=(1, 20),
    grounding_top_k=3,
    grounding_char_budget=1000,
    illustration_keys=_ILLUSTRATION_KEYS,
    rag=RagConfig(
        index_dir=".local/rag",
        cache_dir=".local/hf_cache",
        model_name="BAAI/bge-m3",
        episode_range=(1, 20),
        top_k=4,
    ),
    rag_chapter_header_pattern=r"게임 속 .{0,24}?살아남기\s*-?\s*\d*\s*화?",
    ip_replacements={
        "라프도니아 왕국": "라스카니아 왕국",
        "라프도니아": "라스카니아",
        "비요른 얀델": "투르윈",
        "비요른": "투르윈",
        "에르웬": "실렌",
        "아이나르": "카이라",
        "에쉬드": "셰인",
    },
    ip_keywords=(
        "바바리안",
        "주인공으로 살아남기",
        "회귀",
        "환생",
        "비요른",
        "비요른 얀델",
        "라프도니아",
        "라프도니아 왕국",
        "에르웬",
        "아이나르",
        "에쉬드",
        "두모카",
        "넘버스",
    ),
    ip_fallback_name="투르윈",
    # 캐논 인덱스
    beats=_BEATS,
    anchors=_ANCHORS,
    scene_details=_SCENE_DETAILS,
    weapons=_WEAPONS,
    weapon_aliases=(("도끼", "양손도끼"), ("망치", "양손망치"), ("대검", "대검"), ("검을", "대검")),
    beat_choices=_BEAT_CHOICES,
    beat_thresholds={Beat.DUNGEON_ENTRY: 100},
    pull_flavors=(
        "미궁 깊은 곳에서 희미한 기척이 손짓하듯 흘러나온다.",
        "더 깊은 어둠이 점점 또렷하게 너를 끌어당긴다.",
        "미궁이 너를 집어삼킬 듯 강하게 빨아들인다 — 다음 걸음이 임박했다.",
    ),
    companion_present_beats=frozenset(
        {Beat.DUNGEON_ENTRY, Beat.FIRST_ENCOUNTER, Beat.AFTERMATH}
    ),
    player_name=_PLAYER_NAME,
    player_brief=(
        "흑곰족 거구 바바리안, 현대인의 영혼이 깃들었다. "
        "우직한 야만인을 연기하나 실리적·계산적."
    ),
    companion_brief=(
        "흑곰족 대검 전사, 성인식 동기. 저돌적(돌격 본능)·우직, 신중함은 부족. "
        "성향대로 자율 반응하며 플레이어 지시에 순응/변형/거부한다."
    ),
    first_foe_names=("고블린", "칼날늑대"),
    first_foe_desc="미궁 1층 잡몹. 습성·약점이 있다.",
)
