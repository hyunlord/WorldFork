"""essences.py 본격 단위 검증 (★ Phase 3, 13/14화 정합)."""

from __future__ import annotations

from tools.visual.essences import (
    ESSENCES,
    build_essence_prompt,
)


def test_five_essences() -> None:
    assert len(ESSENCES) == 5


def test_canonical_essence_names() -> None:
    expected = {
        "갈색_정수",
        "흙색_정수",
        "청록_정수",
        "핏빛_정수",
        "회청_정수",
    }
    assert set(ESSENCES.keys()) == expected


def test_essence_required_fields() -> None:
    required = {"color", "source", "details"}
    for _name, data in ESSENCES.items():
        assert required.issubset(data.keys())


def test_essence_sources_match_monsters() -> None:
    """정수 source가 몬스터 매핑 (★ 5/7 매핑)."""
    expected_sources = {"goblin", "gnome", "slime", "bladewolf", "wraith"}
    actual_sources = {data["source"] for data in ESSENCES.values()}
    assert actual_sources == expected_sources


def test_build_essence_prompt_contains_floating() -> None:
    """정수 = floating orb (★ 13/14화 떠다님)."""
    data = ESSENCES["청록_정수"]
    prompt = build_essence_prompt("청록_정수", data)
    assert "floating" in prompt.lower()


def test_build_essence_prompt_contains_color() -> None:
    """정수 prompt에 색 본격 명시."""
    data = ESSENCES["핏빛_정수"]
    prompt = build_essence_prompt("핏빛_정수", data)
    assert "crimson" in prompt.lower() or "red" in prompt.lower()
