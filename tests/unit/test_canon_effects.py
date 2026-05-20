"""Phase D step 6a — canon effects parse + skill 분류 tests."""

from __future__ import annotations

from service.canon.effects import classify_skill, parse_ability_text, parse_essence_abilities

# ── parse_ability_text ────────────────────────────────────────────────────────


def test_parse_numeric_positive() -> None:
    result = parse_ability_text("절삭력+12")
    assert result.get("attack_bonus") == 12


def test_parse_numeric_negative() -> None:
    result = parse_ability_text("유연성-7")
    assert result.get("agility") == -7


def test_parse_numeric_multiple() -> None:
    result = parse_ability_text("절삭력+12, 민첩성+15, 유연성-7")
    assert result.get("attack_bonus") == 12
    assert result.get("agility") == 15 - 7  # 두 키워드 합산


def test_parse_numeric_real_example() -> None:
    text = "절삭력+12, 골밀도+55, 민첩성+15, 지구력+15, 유연성-7, 신장-25."
    result = parse_ability_text(text)
    assert result.get("attack_bonus") == 12
    assert result.get("defense_bonus") == 55
    assert result.get("max_hp_bonus") == 15


def test_parse_grade_ha() -> None:
    result = parse_ability_text("근력(하)")
    assert result.get("strength") == 1


def test_parse_grade_jung() -> None:
    result = parse_ability_text("민첩성(중)")
    assert result.get("agility") == 2


def test_parse_grade_sang() -> None:
    result = parse_ability_text("후각(상)")
    assert result.get("perception") == 3


def test_parse_empty_text() -> None:
    assert parse_ability_text("") == {}


def test_parse_no_match() -> None:
    assert parse_ability_text("일반적인 능력") == {}


def test_parse_essence_abilities_text_format() -> None:
    abilities = {"text": "절삭력+12, 민첩성+15"}
    result = parse_essence_abilities(abilities)
    assert result.get("attack_bonus") == 12
    assert result.get("agility") == 15


def test_parse_essence_abilities_empty_dict() -> None:
    assert parse_essence_abilities({}) == {}


def test_parse_essence_abilities_no_text_key() -> None:
    assert parse_essence_abilities({"other": "value"}) == {}


# ── classify_skill ────────────────────────────────────────────────────────────


def test_classify_passive_suffix() -> None:
    assert classify_skill("독화살 (P)") == "passive"


def test_classify_active_suffix() -> None:
    assert classify_skill("도둑걸음 (A)") == "active"


def test_classify_passive_prefix() -> None:
    assert classify_skill("(P) 방부제: 상처 악화 효과 감소") == "passive"


def test_classify_active_prefix() -> None:
    assert classify_skill("(A) 생기 흡수: 타격 시 재생력 상승") == "active"


def test_classify_unknown() -> None:
    assert classify_skill("알 수 없는 스킬") == "unknown"


def test_classify_empty() -> None:
    assert classify_skill("") == "unknown"


def test_classify_case_insensitive() -> None:
    assert classify_skill("스킬 (a)") == "active"
    assert classify_skill("스킬 (p)") == "passive"
