"""IP Masking 기본 룰 (★ 자료 2.2 Stage 2 + 5.5 한국 시장).

원칙:
  - 작품명 / 캐릭터명 / 장소명 → 마스킹 (개념 유지)
  - Tier 1: 간단 키워드 매칭 (LLM 기반 마스킹은 Tier 2+)
  - apply_ip_masking: immutable (원본 Plan 변경 X)

자료 인용 (자료 5.5 한국 시장):
  ip_leakage_kr:
    - 웹툰/웹소설/아이돌 IP 누출
    - severity: critical
"""

from dataclasses import dataclass, field

from .types import CharacterPlan, Plan, WorldSetting

GENERIC_WORK_NAMES = [
    "novice_dungeon_run",
    "fantasy_adventure_x",
    "mystic_realm_y",
]

# 한국 IP 키워드 감지용 (본인 작품 포함)
KOREAN_IP_KEYWORDS = [
    "바바리안",
    "주인공으로 살아남기",
    "회귀",
    "환생",
    "비요른",
    "라프도니아",
]

GENERIC_REPLACEMENTS: dict[str, list[str]] = {
    "character": ["투르윈", "셰인", "에라드", "미아"],
    "place": ["북부 던전", "신참의 마을", "북녁 산맥"],
    "world": ["판타지 대륙", "고대 왕국", "신참 모험 세계"],
}


@dataclass
class MaskingResult:
    """IP Masking 적용 결과."""

    original: str
    masked: str
    keywords_detected: list[str] = field(default_factory=list)
    masking_applied: bool = False


def detect_ip_keywords(text: str) -> list[str]:
    """텍스트에서 IP 키워드 감지."""
    return [kw for kw in KOREAN_IP_KEYWORDS if kw in text]


def mask_text(
    text: str,
    keyword_replacements: dict[str, str] | None = None,
) -> MaskingResult:
    """텍스트 마스킹 (키워드 replace).

    Args:
        text: 원본
        keyword_replacements: 커스텀 매핑 (없으면 generic 기본)
    """
    detected = detect_ip_keywords(text)
    if not detected:
        return MaskingResult(original=text, masked=text, masking_applied=False)

    masked = text
    replacements = keyword_replacements or {}
    for kw in detected:
        replacement = replacements.get(kw) or GENERIC_REPLACEMENTS["character"][0]
        masked = masked.replace(kw, replacement)

    return MaskingResult(
        original=text,
        masked=masked,
        keywords_detected=detected,
        masking_applied=True,
    )


def apply_ip_masking(plan: Plan) -> Plan:
    """Plan 전체에 IP Masking 적용 (immutable).

    자료 2.2 Stage 2 apply_ip_masking 구현.
    원본 Plan은 변경하지 않고 새 Plan 반환.
    """
    work_m = mask_text(plan.work_name)
    main_name_m = mask_text(plan.main_character.name)
    main_desc_m = mask_text(plan.main_character.description)

    new_main = CharacterPlan(
        name=main_name_m.masked,
        role=plan.main_character.role,
        description=main_desc_m.masked,
        canonical_name=plan.main_character.name if main_name_m.masking_applied else "",
    )

    new_supporting: list[CharacterPlan] = []
    for sc in plan.supporting_characters:
        sc_name_m = mask_text(sc.name)
        sc_desc_m = mask_text(sc.description)
        new_supporting.append(
            CharacterPlan(
                name=sc_name_m.masked,
                role=sc.role,
                description=sc_desc_m.masked,
                canonical_name=sc.name if sc_name_m.masking_applied else "",
            )
        )

    world_m = mask_text(plan.world.setting_name)
    new_world = WorldSetting(
        setting_name=world_m.masked,
        genre=plan.world.genre,
        tone=plan.world.tone,
        rules=plan.world.rules,
        canonical_name=plan.world.setting_name if world_m.masking_applied else "",
    )

    opening_m = mask_text(plan.opening_scene)

    return Plan(
        work_name=work_m.masked,
        work_genre=plan.work_genre,
        main_character=new_main,
        supporting_characters=new_supporting,
        world=new_world,
        opening_scene=opening_m.masked,
        initial_choices=plan.initial_choices,
        user_preferences=plan.user_preferences,
        ip_masking_applied=True,
        sources_used=plan.sources_used,
    )
