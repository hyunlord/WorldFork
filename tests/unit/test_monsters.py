"""monsters.py 본격 단위 검증 (★ Phase 3, 9등급 7종)."""

from __future__ import annotations

from tools.visual.monsters import (
    MONSTERS,
    build_monster_prompt,
)


def test_seven_monsters() -> None:
    assert len(MONSTERS) == 7


def test_canonical_monster_names() -> None:
    """본문 정합 7종 (★ 1층 9등급)."""
    expected = {
        "고블린",
        "고블린_궁수",
        "노움",
        "슬라임",
        "칼날늑대",
        "레이스",
        "위치스램프",
    }
    assert set(MONSTERS.keys()) == expected


def test_monster_required_fields() -> None:
    required = {"english", "physical", "weapon", "behavior"}
    for name, data in MONSTERS.items():
        assert required.issubset(data.keys()), (
            f"{name}: 누락 {required - data.keys()}"
        )


def test_goblin_archer_has_bow() -> None:
    """고블린 궁수 활 본문 정합."""
    data = MONSTERS["고블린_궁수"]
    text = (data["weapon"] + data["physical"]).lower()
    assert "bow" in text


def test_bladewolf_has_blades() -> None:
    """칼날늑대 50/221화 정합."""
    data = MONSTERS["칼날늑대"]
    text = (data["physical"] + data["weapon"]).lower()
    assert "blade" in text or "razor" in text


def test_wraith_is_ethereal() -> None:
    """레이스 60/17화 정합 (★ 빛 약점, ethereal)."""
    data = MONSTERS["레이스"]
    text = (data["physical"] + data["behavior"]).lower()
    assert "ethereal" in text or "ghostly" in text or "shadow" in text


def test_witchlamp_has_flame() -> None:
    """위치스램프 지능형 본문 정합."""
    data = MONSTERS["위치스램프"]
    text = (data["physical"] + data["behavior"]).lower()
    assert "flame" in text or "lantern" in text or "lamp" in text


def test_build_monster_prompt_contains_grade() -> None:
    """9등급 본문 정합."""
    data = MONSTERS["고블린"]
    prompt = build_monster_prompt("고블린", data)
    assert "9th grade" in prompt or "ninth" in prompt.lower()
