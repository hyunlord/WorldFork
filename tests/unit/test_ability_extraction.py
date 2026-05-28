"""I-G1 essence abilities 추출 로직 단위 테스트."""

from scripts.extract_essence_abilities import (
    get_ep_numbers,
    get_quotes,
    get_wiki_pages,
    is_empty_abilities,
    strip_thinking_tags,
)


def test_is_empty_no_abilities() -> None:
    assert is_empty_abilities({"name": "X"}) is True
    assert is_empty_abilities({"name": "X", "abilities": None}) is True
    assert is_empty_abilities({"name": "X", "abilities": {}}) is True


def test_is_empty_short_text() -> None:
    assert is_empty_abilities({"abilities": {"text": "짧음"}}) is True
    assert is_empty_abilities({"abilities": {"text": ""}}) is True


def test_is_empty_filled() -> None:
    assert is_empty_abilities({
        "abilities": {"text": "유연성(하), 후각(하), 독 내성(하)"}
    }) is False


def test_get_ep_numbers() -> None:
    essence = {
        "citations": [
            {"ep_number": 100, "source": "canon"},
            {"ep_number": 200, "source": "canon"},
            {"ep_number": None, "wiki_page": "X"},
        ]
    }
    assert get_ep_numbers(essence) == [100, 200]


def test_get_ep_numbers_empty() -> None:
    assert get_ep_numbers({}) == []
    assert get_ep_numbers({"citations": []}) == []


def test_get_quotes_filters_short() -> None:
    """30자 미만 quote 제외."""
    essence = {
        "citations": [
            {"quote": "짧음"},
            {"quote": "이것은 30자 이상의 충분히 긴 quote 본문 텍스트입니다."},
            {"quote": None},
        ]
    }
    quotes = get_quotes(essence)
    assert len(quotes) == 1
    assert "30자 이상" in quotes[0]


def test_get_wiki_pages() -> None:
    essence = {
        "citations": [
            {"wiki_page": "011_정수"},
            {"wiki_page": ""},
            {"wiki_page": None},
        ]
    }
    assert get_wiki_pages(essence) == ["011_정수"]


def test_strip_thinking_tags() -> None:
    assert strip_thinking_tags("<think>고민</think>응답") == "응답"
    assert strip_thinking_tags("그냥 응답") == "그냥 응답"
    assert strip_thinking_tags(
        "<think>\n여러 줄\n생각\n</think>최종"
    ) == "최종"
