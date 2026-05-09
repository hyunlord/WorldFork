"""rifts.py 본격 단위 검증 (★ Phase 4, 1층 균열 4종)."""

from __future__ import annotations

from tools.visual.rifts import (
    RIFTS,
    build_rift_prompt,
)


def test_four_rifts() -> None:
    assert len(RIFTS) == 4


def test_canonical_rift_names() -> None:
    """본문 정합 4종 (★ 27화)."""
    expected = {"핏빛성채", "빙하굴", "녹색탄광", "강철의_묘"}
    assert set(RIFTS.keys()) == expected


def test_rift_required_fields() -> None:
    required = {"english", "atmosphere", "details", "mood", "color_theme"}
    for name, data in RIFTS.items():
        assert required.issubset(data.keys()), (
            f"{name}: 누락 {required - data.keys()}"
        )


def test_blood_fortress_mentions_necronomicon() -> None:
    """핏빛성채 네크로노미콘 본문 정합."""
    data = RIFTS["핏빛성채"]
    text = data["details"].lower()
    assert "necronomicon" in text or "grimoire" in text


def test_blood_fortress_mentions_goddess_tears() -> None:
    """핏빛성채 여신의 눈물 본문 정합."""
    data = RIFTS["핏빛성채"]
    text = data["details"].lower()
    assert "tears" in text or "weeping" in text


def test_ice_glacier_is_cold() -> None:
    """빙하굴 102화 정합."""
    data = RIFTS["빙하굴"]
    text = (data["atmosphere"] + data["details"]).lower()
    assert "ice" in text or "frozen" in text or "frost" in text


def test_green_mine_is_toxic() -> None:
    """녹색탄광 본문 정합."""
    data = RIFTS["녹색탄광"]
    text = (data["atmosphere"] + data["details"]).lower()
    assert "toxic" in text or "green" in text


def test_steel_tomb_is_metallic() -> None:
    """강철의_묘 본문 정합."""
    data = RIFTS["강철의_묘"]
    text = (data["atmosphere"] + data["details"]).lower()
    assert "steel" in text or "metal" in text or "iron" in text


def test_all_rifts_mention_8th_grade() -> None:
    """모두 8등급 보스 lair 본격."""
    for name, data in RIFTS.items():
        text = data["details"].lower()
        assert "8th grade" in text or "boss lair" in text, (
            f"{name}: 8등급 본격 누락"
        )


def test_build_rift_prompt_no_characters() -> None:
    data = RIFTS["핏빛성채"]
    prompt = build_rift_prompt("핏빛성채", data)
    assert "no characters" in prompt.lower()


def test_build_rift_prompt_contains_color_theme() -> None:
    data = RIFTS["빙하굴"]
    prompt = build_rift_prompt("빙하굴", data)
    assert "blue" in prompt.lower() or "ice" in prompt.lower()
