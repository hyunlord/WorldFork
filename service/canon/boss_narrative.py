"""균열 보스 3-tier narrative 분류 로직 (audit-3-3).

ep_0032: 「핏빛 성채의 주인이 깊은 잠에서 깨어납니다.」
ep_0033: 문고리 색상 — 변종 단서
ep_0584: 일반 보스 효율 어조
ep_0587: 빙하굴 시체산 + 관짝 변종 단서
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class BossTier(StrEnum):
    NORMAL = "normal"     # 일반 수호자 — 효율 어조
    VARIANT = "variant"   # 상위 변이종 — 평소와 다름 인지
    HIDDEN = "hidden"     # 히든 보스 — 전례 없는 어조 (ep_0032)


@dataclass(frozen=True)
class BossNarrativeContext:
    """27B GM 호출 context."""

    rift_id: str
    rift_name: str
    sub_area_id: str
    boss_name: str
    boss_grade: int | None
    tier: BossTier
    is_variant_rift: bool
    visual_clues: list[str] = field(default_factory=list)


_HIDDEN_BOSS_NAMES: frozenset[str] = frozenset({
    "캠보르미어",
    "뱀파이어 공작 캠보르미어",
    "키르뒤",
    "타락한 짐승 키르뒤",
})

# 변종 균열 외형 단서 (ep_0033 문고리, ep_0587 관짝/시체산)
VARIANT_VISUAL_CLUES: dict[str, list[str]] = {
    "bloody_castle": [
        "보스룸 문고리의 색상이 평소와 다르다.",
        "데스나이트 대신 거대한 관짝이 보스룸 중앙에 놓여 있다.",
    ],
    "glacier_cave": [
        "보스룸 입구의 얼음 결정 모양이 평소와 다르다.",
        "보스룸 안쪽에서 시체산 아래로 무언가 삼키는 소리가 들린다.",
    ],
    "green_mine": [
        "갱도 깊은 곳의 바닥이 평소와 다른 색조의 점액으로 덮여 있다.",
    ],
    "iron_tomb": [
        "보스룸 안쪽에서 평소와 다른 금속 마찰음이 들린다.",
    ],
}

RIFT_NAMES: dict[str, str] = {
    "bloody_castle": "핏빛성채",
    "glacier_cave": "빙하굴",
    "green_mine": "녹색 탄광",
    "iron_tomb": "강철의 묘",
}

# 3-tier 시스템 메시지 template (ep_0032 정합)
SYSTEM_MESSAGE_TEMPLATES: dict[BossTier, str] = {
    BossTier.NORMAL: "「{rift_name}의 수호자가 모습을 드러냅니다.」",
    BossTier.VARIANT: "「{boss_name}이(가) 깊은 잠에서 깨어납니다.」",
    BossTier.HIDDEN: "「{rift_name}의 주인이 깊은 잠에서 깨어납니다.」",
}


def determine_boss_tier(
    boss_name: str,
    is_variant: bool,
    rift_id: str,  # noqa: ARG001
) -> BossTier:
    """boss_name + is_variant → 3-tier 결정.

    HIDDEN: 히든 보스 이름 명시 목록에 포함 (캠보르미어, 키르뒤).
    VARIANT: is_variant=True + HIDDEN 아님.
    NORMAL: 나머지.
    """
    if any(hb in boss_name for hb in _HIDDEN_BOSS_NAMES):
        return BossTier.HIDDEN
    if is_variant:
        return BossTier.VARIANT
    return BossTier.NORMAL


def build_visual_clues(rift_id: str, is_variant: bool) -> list[str]:
    """변종 균열 외형 단서 목록 반환."""
    if not is_variant:
        return []
    return list(VARIANT_VISUAL_CLUES.get(rift_id, []))


def format_system_message(tier: BossTier, rift_name: str, boss_name: str) -> str:
    """tier별 시스템 메시지 문자열 생성."""
    template = SYSTEM_MESSAGE_TEMPLATES[tier]
    return template.format(rift_name=rift_name, boss_name=boss_name)
