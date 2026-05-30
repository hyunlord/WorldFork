"""감응도(sensitivity) element 위력 보정 단위 테스트."""

from __future__ import annotations

from service.canon.effects import essence_to_slot, parse_sensitivities
from service.sim.combat import (
    SENSITIVITY_SCALE,
    apply_sensitivity_bonus,
)
from service.sim.player_state import (
    EssenceSlot,
    compute_total_sensitivities,
    slot_from_dict,
    slot_to_dict,
)

# ── apply_sensitivity_bonus ─────────────────────────────────────────────────


def test_scale_constant() -> None:
    assert SENSITIVITY_SCALE == 0.02


def test_no_sensitivity_no_bonus() -> None:
    assert apply_sensitivity_bonus(100, ["불"], {}) == 100
    assert apply_sensitivity_bonus(100, ["불"], None) == 100


def test_no_element_no_bonus() -> None:
    """물리 단독 → 감응도 무관."""
    assert apply_sensitivity_bonus(100, ["물리"], {"불": 50}) == 100
    assert apply_sensitivity_bonus(100, None, {"불": 50}) == 100


def test_element_sensitivity_bonus() -> None:
    """불 element + 불 감응도 10 → +20% (scale 0.02)."""
    assert apply_sensitivity_bonus(100, ["물리", "불"], {"불": 10}) == 120


def test_sensitivity_element_mismatch() -> None:
    """공격 element와 감응도 element 불일치 → 보정 X."""
    assert apply_sensitivity_bonus(100, ["불"], {"냉기": 30}) == 100


def test_sensitivity_max_among_elements() -> None:
    """다중 element → 최대 감응도 적용."""
    assert apply_sensitivity_bonus(100, ["불", "냉기"], {"불": 5, "냉기": 20}) == 140


def test_min_one_damage() -> None:
    assert apply_sensitivity_bonus(0, ["불"], {"불": 10}) == 0


# ── parse_sensitivities / essence_to_slot ───────────────────────────────────


def test_parse_sensitivities() -> None:
    parsed = [
        {"name": "냉기 감응도", "tier": "상"},   # 냉기 +3
        {"name": "화염 감응도", "tier": "중"},   # 불 +2
        {"name": "근력", "tier": "상"},          # sensitivity 아님
    ]
    assert parse_sensitivities(parsed) == {"냉기": 3, "불": 2}


def test_essence_to_slot_sets_sensitivities() -> None:
    slot = essence_to_slot({
        "name": "빙정 정수",
        "abilities": {
            "text": "냉기 감응도(상)",
            "parsed": [{"name": "냉기 감응도", "tier": "상"}],
        },
    })
    assert slot.sensitivities == {"냉기": 3}
    # ★ 감응도는 resistance로 중복 분류 X
    assert "냉기" not in slot.resistances


def test_slot_serialize_sensitivities() -> None:
    slot = EssenceSlot(essence_name="X", sensitivities={"불": 5})
    d = slot_to_dict(slot)
    assert d["sensitivities"] == {"불": 5}
    assert slot_from_dict(d).sensitivities == {"불": 5}


def test_slot_backward_compat() -> None:
    """기존 dict (sensitivities 미보유) → 빈 dict."""
    slot = slot_from_dict({"essence_name": "옛정수", "stat_bundle": {}})
    assert slot.sensitivities == {}


def test_compute_total_sensitivities() -> None:
    slots = [
        EssenceSlot(essence_name="A", sensitivities={"불": 3}),
        EssenceSlot(essence_name="B", sensitivities={"불": 2, "냉기": 1}),
    ]
    assert compute_total_sensitivities(slots) == {"불": 5, "냉기": 1}
