"""정수 source_monster → 공격 element 단위 테스트."""

from __future__ import annotations

from service.canon.effects import essence_to_slot, get_essence_attack_element
from service.sim.player_state import (
    EssenceSlot,
    compute_total_attack_elements,
    slot_from_dict,
    slot_to_dict,
)

# ── get_essence_attack_element — 이름 keyword ───────────────────────────────


def test_fire_monster_element() -> None:
    assert get_essence_attack_element("용암거인") == "불"
    assert get_essence_attack_element("화염 도마뱀") == "불"


def test_cold_monster_element() -> None:
    assert get_essence_attack_element("서리늑대") == "냉기"
    assert get_essence_attack_element("얼음 정령") == "냉기"


def test_lightning_monster_element() -> None:
    assert get_essence_attack_element("번개 까마귀") == "전격"


def test_holy_light_element() -> None:
    assert get_essence_attack_element("성기사단장") == "신성력"
    assert get_essence_attack_element("빛의 수호자") == "빛"


def test_poison_element() -> None:
    assert get_essence_attack_element("맹독 거미") == "독"


def test_no_element_keyword() -> None:
    """element 키워드 없는 monster → None (물리는 무기 담당)."""
    assert get_essence_attack_element("고블린") is None
    assert get_essence_attack_element("오크 전사") is None


def test_false_positive_guarded() -> None:
    """오탐 차단 — 불행/고뇌/광대는 element 키워드 아님."""
    assert get_essence_attack_element("불행의 선지자") is None  # 불행 ≠ 불
    assert get_essence_attack_element("고뇌의 화관") is None     # 고뇌 ≠ 뇌
    assert get_essence_attack_element("광대") is None            # 광대 ≠ 광


def test_empty_source() -> None:
    assert get_essence_attack_element(None) is None
    assert get_essence_attack_element("") is None
    assert get_essence_attack_element("   ") is None


# ── essence_to_slot — attack_elements 설정 ──────────────────────────────────


def test_essence_to_slot_fire_grants_element() -> None:
    slot = essence_to_slot({
        "name": "용암거인 정수",
        "grade": 5,
        "source_monster": "용암거인",
    })
    assert slot.attack_elements == ["불"]


def test_essence_to_slot_no_source_no_element() -> None:
    slot = essence_to_slot({"name": "고블린 정수", "source_monster": "고블린"})
    assert slot.attack_elements == []


def test_essence_to_slot_missing_source() -> None:
    slot = essence_to_slot({"name": "X"})
    assert slot.attack_elements == []


# ── 직렬화 + 합집합 ─────────────────────────────────────────────────────────


def test_slot_serialize_attack_elements() -> None:
    slot = EssenceSlot(essence_name="X", attack_elements=["불"])
    d = slot_to_dict(slot)
    assert d["attack_elements"] == ["불"]
    assert slot_from_dict(d).attack_elements == ["불"]


def test_slot_from_dict_backward_compat() -> None:
    """기존 dict (attack_elements 미보유) → 빈 list."""
    slot = slot_from_dict({"essence_name": "옛정수", "stat_bundle": {}, "grade": 3})
    assert slot.attack_elements == []


def test_compute_total_attack_elements_dedup() -> None:
    """다중 정수 element 합집합 — 순서 유지 dedup (★ Q3 c)."""
    slots = [
        EssenceSlot(essence_name="A", attack_elements=["불"]),
        EssenceSlot(essence_name="B", attack_elements=["냉기"]),
        EssenceSlot(essence_name="C", attack_elements=["불"]),  # 중복
    ]
    assert compute_total_attack_elements(slots) == ["불", "냉기"]
