"""WORLDFORK_PACK 조립 — 엔진이 소비하는 WorldFork 데이터(A1.2 — 팩이 소스).

엔진(narrative_gm·gm_session_router)이 이 팩을 require_active_pack()으로 소비한다. 여기 정의가
원본(SSOT)이고, 엔진 모듈엔 중복 리터럴이 없다. 캐논 인덱스·RAG·IP는 A1.2b에서 소비처와 함께 합류.
★ IP: 코드·git = 변환명(투르윈/카이라). 화면 노출은 프론트 unmaskIp.
"""

from __future__ import annotations

from service.engine.content_pack import CompanionSpec, ContentPack, FoeSpec
from service.sim.opening_canon import KAIRA_DISPOSITION, KAIRA_NAME

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

WORLDFORK_PACK = ContentPack(
    pack_id="worldfork",
    gm_system_persona=_GM_SYSTEM_PERSONA,
    first_foe=FoeSpec(name="고블린", hp=36, attack=8, essence_drop="고블린 정수"),
    companion=CompanionSpec(
        name=KAIRA_NAME, disposition=KAIRA_DISPOSITION, hp=140, attack=14
    ),
    grounding_episode_range=(1, 20),
    grounding_top_k=3,
    grounding_char_budget=1000,
    illustration_keys=_ILLUSTRATION_KEYS,
)
