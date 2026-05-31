"""피해 반사 passive — 확률적 보복 tier → 반사율 단위 테스트 (★ rules game 4번째)."""

from __future__ import annotations

from service.canon.effects import essence_to_slot, extract_reflect_ratio
from service.sim.player_state import (
    compute_total_reflect,
    slot_from_dict,
    slot_to_dict,
)


def test_reflect_tier_mapping() -> None:
    """확률적 보복 tier → 반사율 (최상0.25/상0.20/중0.15/하0.10)."""
    assert extract_reflect_ratio([{"name": "확률적 보복", "tier": "최상"}]) == 0.25
    assert extract_reflect_ratio([{"name": "확률적 보복", "tier": "상"}]) == 0.20
    assert extract_reflect_ratio([{"name": "확률적 보복", "tier": "중"}]) == 0.15
    assert extract_reflect_ratio([{"name": "확률적 보복", "tier": "하"}]) == 0.10


def test_reflect_keyword_variants() -> None:
    """'반사'/'보복' 키워드 모두 인식."""
    assert extract_reflect_ratio([{"name": "피해 반사", "tier": "상"}]) == 0.20
    assert extract_reflect_ratio([{"name": "확률적 보복", "tier": "중"}]) == 0.15


def test_reflect_unknown_tier_defaults() -> None:
    """tier 미상 → 0.10 (기본 반사)."""
    assert extract_reflect_ratio([{"name": "확률적 보복"}]) == 0.10


def test_reflect_non_reflect_ignored() -> None:
    """'반사'/'보복' 미포함 → 0."""
    assert extract_reflect_ratio([{"name": "근력", "tier": "상"}]) == 0.0
    assert extract_reflect_ratio([]) == 0.0


def test_reflect_takes_max_not_sum() -> None:
    """중복 반사 능력은 최댓값 (과반사 방지)."""
    parsed = [
        {"name": "확률적 보복", "tier": "하"},
        {"name": "피해 반사", "tier": "상"},
    ]
    assert extract_reflect_ratio(parsed) == 0.20  # 0.10+0.20 아님


def test_essence_to_slot_reflect() -> None:
    """essence parsed → EssenceSlot.reflect_ratio."""
    slot = essence_to_slot(
        {"name": "벨라리오스", "abilities": {"parsed": [{"name": "확률적 보복", "tier": "중"}]}}
    )
    assert slot.reflect_ratio == 0.15


def test_essence_to_slot_no_reflect() -> None:
    """반사 능력 없는 정수 → 0."""
    slot = essence_to_slot({"name": "철골렘", "abilities": {"text": "근력 상승"}})
    assert slot.reflect_ratio == 0.0


def test_slot_reflect_round_trip() -> None:
    """slot 직렬화 reflect_ratio 보존 (영속성)."""
    slot = essence_to_slot(
        {"name": "임프의 정수", "abilities": {"parsed": [{"name": "확률적 보복", "tier": "하"}]}}
    )
    restored = slot_from_dict(slot_to_dict(slot))
    assert restored.reflect_ratio == 0.10


def test_compute_total_reflect_max() -> None:
    """흡수 정수 반사율 최댓값 (★ 합산 아님)."""
    slots = [
        essence_to_slot(
            {"name": "A", "abilities": {"parsed": [{"name": "확률적 보복", "tier": "하"}]}}
        ),
        essence_to_slot(
            {"name": "B", "abilities": {"parsed": [{"name": "확률적 보복", "tier": "상"}]}}
        ),
        essence_to_slot({"name": "C", "abilities": {"text": "근력"}}),
    ]
    assert compute_total_reflect(slots) == 0.20  # max(0.10, 0.20, 0.0)
