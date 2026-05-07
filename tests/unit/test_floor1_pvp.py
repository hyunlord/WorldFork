"""1층 PvP / 약탈자 진짜 정의 테스트.

본인 본질 (2026-05-08):
- 수정 연합 (★ 10화): 1층 주 무대 약탈자 집단
- 메시지 스톤 (★ 10화): 300m 통신, 공명 필수
- 현상금 (★ 11화): 1만 → 2만 스톤
"""

from __future__ import annotations

from service.game.floors.floor1 import get_floor1_definition
from service.game.floors.floor1_pvp import (
    FLOOR1_BOUNTY_CONFIG,
    FLOOR1_RAIDER_FACTIONS,
)


def test_floor1_has_crystal_union() -> None:
    """1층 수정 연합 (★ 10화 본문)."""
    assert len(FLOOR1_RAIDER_FACTIONS) == 1
    cu = FLOOR1_RAIDER_FACTIONS[0]
    assert cu.name == "수정 연합"
    assert 1 in cu.primary_floors


def test_bounty_config_message_stone_300m() -> None:
    """메시지 스톤 300m + 공명 필수 (★ 10화)."""
    assert FLOOR1_BOUNTY_CONFIG.message_stone.range_meters == 300
    assert FLOOR1_BOUNTY_CONFIG.message_stone.requires_pre_resonance


def test_bounty_config_amounts_10k_20k() -> None:
    """현상금 표준 1만 → 강화 2만 (★ 11화)."""
    assert FLOOR1_BOUNTY_CONFIG.standard_bounty_stones == 10000
    assert FLOOR1_BOUNTY_CONFIG.escalated_bounty_stones == 20000


def test_floor1_definition_includes_bounty_config() -> None:
    f1 = get_floor1_definition()
    assert f1.bounty_config is not None
    assert f1.bounty_config.message_stone.range_meters == 300
    assert len(f1.bounty_config.known_factions) == 1
