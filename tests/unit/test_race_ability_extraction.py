"""races ability_tiers 추출 로직 단위 테스트."""

from scripts.extract_race_abilities import (
    build_source,
    has_existing_tiers,
    strip_thinking_tags,
)


def test_has_existing_tiers_empty() -> None:
    assert has_existing_tiers({"name": "X"}) is False
    assert has_existing_tiers({"ability_tiers": None}) is False
    assert has_existing_tiers({"ability_tiers": {}}) is False
    assert has_existing_tiers({"ability_tiers": {"text": ""}}) is False


def test_has_existing_tiers_short() -> None:
    assert has_existing_tiers({"ability_tiers": {"text": "짧"}}) is False


def test_has_existing_tiers_filled() -> None:
    assert has_existing_tiers({
        "ability_tiers": {"text": "강인함(상), 재생(중)"}
    }) is True


def test_build_source_description_only() -> None:
    race = {"name": "X", "description": "추위에 강하고 재생력이 뛰어난 종족"}
    src = build_source(race)
    assert "설명:" in src
    assert "추위에 강하고" in src


def test_build_source_abilities_only() -> None:
    race = {"name": "고블린", "abilities": ["영악함", "덫 설치", "독 사용"]}
    src = build_source(race)
    assert "알려진 특성:" in src
    assert "영악함" in src
    assert "덫 설치" in src


def test_build_source_combined() -> None:
    race = {
        "name": "드워프",
        "description": "산악 지대 거주",
        "abilities": ["대장간 운영", "버클러 사용"],
    }
    src = build_source(race)
    assert "설명:" in src
    assert "알려진 특성:" in src


def test_build_source_empty() -> None:
    assert build_source({"name": "X"}) == ""
    assert build_source({"name": "X", "description": "", "abilities": []}) == ""


def test_strip_thinking_tags() -> None:
    assert strip_thinking_tags("<think>x</think>응답") == "응답"
    assert strip_thinking_tags("그냥 응답") == "그냥 응답"
