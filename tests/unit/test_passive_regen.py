"""passive HP 재생 — 자연 재생력 tier → 매 턴 회복 단위 테스트 (★ rules game 3번째)."""

from __future__ import annotations

from service.canon.effects import essence_to_slot, extract_regen_per_turn
from service.sim.player_state import (
    compute_total_regen,
    slot_from_dict,
    slot_to_dict,
)


def test_regen_tier_mapping() -> None:
    """자연 재생력 tier → HP/turn (최상4/상3/중2/하1)."""
    assert extract_regen_per_turn([{"name": "자연 재생력", "tier": "최상"}]) == 4
    assert extract_regen_per_turn([{"name": "자연 재생력", "tier": "상"}]) == 3
    assert extract_regen_per_turn([{"name": "자연재생", "tier": "중"}]) == 2
    assert extract_regen_per_turn([{"name": "자연 재생력", "tier": "하"}]) == 1


def test_regen_tier_unknown_defaults_one() -> None:
    """tier 미상 → 1 (기본 재생)."""
    assert extract_regen_per_turn([{"name": "자연 재생력"}]) == 1
    assert extract_regen_per_turn([{"name": "재생력", "tier": "?"}]) == 1


def test_regen_non_regen_ability_ignored() -> None:
    """'재생' 미포함 ability → 0."""
    assert extract_regen_per_turn([{"name": "근력", "tier": "상"}]) == 0
    assert extract_regen_per_turn([]) == 0


def test_regen_takes_max_not_sum() -> None:
    """중복 재생 능력은 최댓값 (과회복 방지)."""
    parsed = [
        {"name": "자연 재생력", "tier": "하"},
        {"name": "자연재생", "tier": "상"},
    ]
    assert extract_regen_per_turn(parsed) == 3  # 1+3=4 아님


def test_essence_to_slot_regen() -> None:
    """essence parsed → EssenceSlot.regen_per_turn."""
    slot = essence_to_slot(
        {"name": "뱀파이어 정수", "abilities": {"parsed": [{"name": "자연 재생력", "tier": "중"}]}}
    )
    assert slot.regen_per_turn == 2


def test_essence_to_slot_no_regen() -> None:
    """재생 능력 없는 정수 → 0."""
    slot = essence_to_slot({"name": "철골렘", "abilities": {"text": "근력 상승"}})
    assert slot.regen_per_turn == 0


def test_slot_regen_round_trip() -> None:
    """slot_to_dict / slot_from_dict regen_per_turn 보존 (영속성)."""
    slot = essence_to_slot(
        {"name": "스톰거쉬의 정수", "abilities": {"parsed": [{"name": "자연 재생", "tier": "상"}]}}
    )
    restored = slot_from_dict(slot_to_dict(slot))
    assert restored.regen_per_turn == 3


def test_compute_total_regen() -> None:
    """흡수 정수들의 재생량 합산 (★ 매 턴 총 회복)."""
    slots = [
        essence_to_slot(
            {"name": "A", "abilities": {"parsed": [{"name": "자연 재생력", "tier": "중"}]}}
        ),
        essence_to_slot(
            {"name": "B", "abilities": {"parsed": [{"name": "자연재생", "tier": "하"}]}}
        ),
        essence_to_slot({"name": "C", "abilities": {"text": "근력"}}),
    ]
    assert compute_total_regen(slots) == 3  # 2 + 1 + 0
