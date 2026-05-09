"""sub_areas.py 본격 단위 검증 (★ Phase 2 B)."""

from __future__ import annotations

from tools.visual.sub_areas import (
    SUB_AREAS,
    build_sub_area_prompt,
)


def test_six_sub_areas() -> None:
    assert len(SUB_AREAS) == 6


def test_sub_areas_canonical_names() -> None:
    """본문 정합 6개 (★ 작품 본문)."""
    expected = {
        "진입점",
        "북쪽_통로",
        "남쪽_통로",
        "수정_동굴",
        "비석_공동",
        "포탈_영역",
    }
    assert set(SUB_AREAS.keys()) == expected


def test_sub_area_required_fields() -> None:
    required = {"english", "atmosphere", "details", "mood"}
    for name, data in SUB_AREAS.items():
        assert required.issubset(data.keys()), (
            f"{name}: 누락 {required - data.keys()}"
        )


def test_portal_zone_mentions_four_rifts() -> None:
    """포탈 영역 4 균열 본문 정합 (★ 핏빛/빙하/녹색/강철)."""
    data = SUB_AREAS["포탈_영역"]
    details = data["details"].lower()
    assert "four" in details
    assert "blood" in details or "crimson" in details
    assert "blue" in details or "ice" in details


def test_southern_passage_mentions_gnome() -> None:
    """남쪽 통로 노움 22화 정합."""
    data = SUB_AREAS["남쪽_통로"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert "gnome" in text


def test_crystal_cavern_mentions_essences() -> None:
    """수정 동굴 정수 13/14화 정합."""
    data = SUB_AREAS["수정_동굴"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert "essence" in text or "crystal" in text


def test_stele_hollow_mentions_offering() -> None:
    """비석 공동 374화 공물 정합."""
    data = SUB_AREAS["비석_공동"]
    text = (data["atmosphere"] + " " + data["details"]).lower()
    assert "stele" in text or "offering" in text or "monument" in text


def test_build_prompt_contains_no_characters() -> None:
    """sub_area prompt는 환경만 (★ no characters)."""
    data = SUB_AREAS["진입점"]
    prompt = build_sub_area_prompt("진입점", data)
    assert "no characters" in prompt.lower()


def test_build_prompt_contains_english_name() -> None:
    """prompt에 english 명 본격."""
    data = SUB_AREAS["수정_동굴"]
    prompt = build_sub_area_prompt("수정_동굴", data)
    assert "crystal cavern" in prompt.lower()


def test_build_prompt_contains_first_floor() -> None:
    """1층 본문 본격 명시."""
    data = SUB_AREAS["진입점"]
    prompt = build_sub_area_prompt("진입점", data)
    assert "first floor" in prompt.lower()
