"""1층 PvP / 약탈자 시스템 정의.

자료 출처:
- 10화: 메시지 스톤 (★ 300m 통신, 공명 필수), 수정 연합 등장
- 11화: 현상금 1만 → 2만 스톤 (입막음 강화)
- 25/47/51/112화 등: 약탈자 본격 등장
"""

from __future__ import annotations

from ..state_v2 import BountyConfig, MessageStoneSpec, RaiderFaction

# ─── 1층 약탈자 집단 ───

_CRYSTAL_UNION = RaiderFaction(
    name="수정 연합",
    primary_floors=(1,),  # ★ 10화: '1층을 주 무대로 하는 어느 집단'
    description=(
        "1층 주 무대 약탈자 집단. 간부 + 다수 인력 + 메시지 스톤 통신."
    ),
)


FLOOR1_RAIDER_FACTIONS: tuple[RaiderFaction, ...] = (_CRYSTAL_UNION,)


# ─── 1층 PvP 시스템 ───

FLOOR1_BOUNTY_CONFIG = BountyConfig(
    message_stone=MessageStoneSpec(
        range_meters=300,
        requires_pre_resonance=True,
    ),
    known_factions=FLOOR1_RAIDER_FACTIONS,
    standard_bounty_stones=10000,
    escalated_bounty_stones=20000,
)
