"""I-G1 ability tier stat scaling 단위 테스트."""

from __future__ import annotations

from service.canon.effects import (
    TIER_VALUE,
    apply_parsed_abilities,
    classify_ability,
    essence_to_slot,
)
from service.sim.player_state import (
    EssenceSlot,
    compute_total_resistances,
    compute_total_stats,
    slot_from_dict,
    slot_to_dict,
)


def test_tier_values() -> None:
    assert TIER_VALUE["상"] == 3
    assert TIER_VALUE["중"] == 2
    assert TIER_VALUE["하"] == 1


def test_classify_attack() -> None:
    assert classify_ability("근력") == ("attack", None)
    assert classify_ability("완력") == ("attack", None)
    assert classify_ability("절삭력") == ("attack", None)
    assert classify_ability("골강도") == ("attack", None)


def test_classify_dex() -> None:
    assert classify_ability("민첩") == ("dex", None)
    assert classify_ability("직감") == ("dex", None)
    assert classify_ability("유연성") == ("dex", None)


def test_classify_resistance() -> None:
    assert classify_ability("독 내성") == ("resistance", "독")
    assert classify_ability("독내성") == ("resistance", "독")
    assert classify_ability("냉기응축") == ("resistance", "냉기")
    assert classify_ability("오한") == ("resistance", "냉기")
    assert classify_ability("고통내성") == ("resistance", "고통")


def test_classify_sensitivity() -> None:
    """★ 감응도는 공격 element 계수 — resistance 아님 (canon 정합)."""
    assert classify_ability("냉기 감응도") == ("sensitivity", "냉기")
    assert classify_ability("화염 감응도") == ("sensitivity", "불")
    assert classify_ability("모든 속성 감응도") == ("sensitivity", "")


def test_classify_etc() -> None:
    assert classify_ability("소화력") == ("etc", None)
    assert classify_ability("부여") == ("etc", None)
    assert classify_ability("과부하") == ("etc", None)
    assert classify_ability("피의 샘") == ("etc", None)


def test_classify_empty() -> None:
    assert classify_ability("") == ("etc", None)
    assert classify_ability("   ") == ("etc", None)


def test_apply_attack_bonus() -> None:
    """공격 ability → stat_bundle["attack_bonus"] += tier."""
    stats, res, etc = apply_parsed_abilities([
        {"name": "근력", "tier": "상"},
    ])
    assert stats == {"attack_bonus": 3}
    assert res == {}
    assert etc == []


def test_apply_dex_to_agility() -> None:
    """민첩 ability → stat_bundle["agility"]."""
    stats, _, _ = apply_parsed_abilities([
        {"name": "민첩", "tier": "중"},
        {"name": "직감", "tier": "하"},
    ])
    assert stats == {"agility": 3}  # 2 + 1


def test_apply_resistance_dict() -> None:
    """저항 ability → resistances[type] += tier."""
    _, res, _ = apply_parsed_abilities([
        {"name": "독 내성", "tier": "중"},
        {"name": "냉기응축", "tier": "하"},
    ])
    assert res == {"독": 2, "냉기": 1}


def test_apply_etc_log_only() -> None:
    """미분류 ability → etc_logs (stat 영향 X)."""
    stats, res, etc = apply_parsed_abilities([
        {"name": "소화력", "tier": "중"},
    ])
    assert stats == {}
    assert res == {}
    assert etc == ["소화력(중)"]


def test_apply_mixed() -> None:
    """공격 + 저항 + 미분류 혼합."""
    stats, res, etc = apply_parsed_abilities([
        {"name": "근력", "tier": "상"},      # attack +3
        {"name": "독 내성", "tier": "중"},   # 독 +2
        {"name": "소화력", "tier": "하"},    # etc
    ])
    assert stats == {"attack_bonus": 3}
    assert res == {"독": 2}
    assert etc == ["소화력(하)"]


def test_apply_empty_parsed() -> None:
    stats, res, etc = apply_parsed_abilities([])
    assert stats == {}
    assert res == {}
    assert etc == []


def test_apply_invalid_tier_default_mid() -> None:
    """tier 무효 시 default 중(2)."""
    stats, _, _ = apply_parsed_abilities([
        {"name": "근력", "tier": "X"},
    ])
    assert stats == {"attack_bonus": 2}


def test_essence_to_slot_with_parsed() -> None:
    """parsed 보유 essence → slot.stat_bundle + resistances 적용."""
    essence_data = {
        "name": "데스핀드",
        "grade": 7,
        "abilities": {
            "text": "고통내성(상), 근력(중), 소화력(하)",
            "parsed": [
                {"name": "고통내성", "tier": "상"},
                {"name": "근력", "tier": "중"},
                {"name": "소화력", "tier": "하"},
            ],
        },
    }
    slot = essence_to_slot(essence_data)
    assert slot.essence_name == "데스핀드"
    assert slot.grade == 7
    assert slot.stat_bundle == {"attack_bonus": 2}  # 근력(중)=2
    assert slot.resistances == {"고통": 3}
    assert slot.etc_abilities == ["소화력(하)"]


def test_essence_to_slot_parsed_skips_text_parse() -> None:
    """parsed 있으면 text-based parse skip (double counting 방지)."""
    essence_data = {
        "name": "테스트",
        "abilities": {
            "text": "근력(상)",
            "parsed": [{"name": "근력", "tier": "상"}],
        },
    }
    slot = essence_to_slot(essence_data)
    # parsed만 사용 → attack_bonus=3 (★ text+parsed 합산 6 X)
    assert slot.stat_bundle == {"attack_bonus": 3}


def test_essence_to_slot_no_parsed_uses_text() -> None:
    """parsed 없으면 기존 text-based parse 사용."""
    essence_data = {
        "name": "기존정수",
        "abilities": {"text": "민첩성(중)"},
    }
    slot = essence_to_slot(essence_data)
    # text-based parse → agility=2
    assert slot.stat_bundle == {"agility": 2}


def test_slot_serialize_resistances() -> None:
    """slot_to_dict / slot_from_dict resistances + etc_abilities 보존."""
    slot = EssenceSlot(
        essence_name="X",
        stat_bundle={"agility": 2},
        skills=[],
        grade=5,
        resistances={"독": 3, "냉기": 1},
        etc_abilities=["소화력(중)"],
    )
    d = slot_to_dict(slot)
    assert d["resistances"] == {"독": 3, "냉기": 1}

    restored = slot_from_dict(d)
    assert restored.resistances == {"독": 3, "냉기": 1}
    assert restored.etc_abilities == ["소화력(중)"]


def test_slot_from_dict_backward_compat() -> None:
    """기존 dict (resistances 미보유) → 빈 dict default."""
    old_dict = {
        "essence_name": "옛정수",
        "stat_bundle": {"agility": 1},
        "skills": [],
        "grade": 3,
    }
    slot = slot_from_dict(old_dict)
    assert slot.resistances == {}
    assert slot.etc_abilities == []


def test_compute_total_resistances() -> None:
    """다중 정수 흡수 시 resistances 합산."""
    slots = [
        EssenceSlot(essence_name="A", resistances={"독": 2, "냉기": 1}),
        EssenceSlot(essence_name="B", resistances={"독": 1, "고통": 3}),
    ]
    total = compute_total_resistances(slots)
    assert total == {"독": 3, "냉기": 1, "고통": 3}


def test_compute_total_stats_unchanged_by_resistances() -> None:
    """compute_total_stats는 stat_bundle만 — resistances 영향 X."""
    slots = [
        EssenceSlot(essence_name="A", stat_bundle={"agility": 2}, resistances={"독": 5}),
    ]
    assert compute_total_stats(slots) == {"agility": 2}
