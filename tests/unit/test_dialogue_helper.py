"""dialogue_helper.is_deep_dialogue 분기 검증."""

from __future__ import annotations

from service.sim.dialogue_helper import is_deep_dialogue


def test_short_greeting_template() -> None:
    """짧은 인사 → False (template)."""
    assert is_deep_dialogue("안녕하세요") is False
    assert is_deep_dialogue("인사한다") is False
    assert is_deep_dialogue("ㅎㅇ") is False
    assert is_deep_dialogue("반갑습니다") is False


def test_deep_keyword_27b() -> None:
    """DEEP keyword → True (27B)."""
    assert is_deep_dialogue("던전에 대해 물어본다") is True
    assert is_deep_dialogue("최근 소식을 알려달라") is True
    assert is_deep_dialogue("조언을 구한다") is True
    assert is_deep_dialogue("이야기를 나눈다") is True
    assert is_deep_dialogue("무기 강화에 대해 질문한다") is True


def test_long_input_27b() -> None:
    """30자 초과 → True."""
    long_text = "사실 나는 한참 동안 그를 바라보다가 천천히 입을 열어 무언가 말하기 시작했다"
    assert len(long_text) > 30
    assert is_deep_dialogue(long_text) is True


def test_short_ambiguous_default_template() -> None:
    """모호 짧은 input → False (default, latency 절약)."""
    assert is_deep_dialogue("응") is False
    assert is_deep_dialogue("어") is False
    assert is_deep_dialogue("그래") is False


def test_deep_keyword_overrides_short() -> None:
    """짧더라도 DEEP keyword 포함 시 True."""
    assert is_deep_dialogue("알려줘") is True
    assert is_deep_dialogue("도움 줘") is True
