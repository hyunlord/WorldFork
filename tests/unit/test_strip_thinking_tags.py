"""strip_thinking_tags 단위 테스트."""

from __future__ import annotations

from service.sim.llm_helpers import strip_thinking_tags


def test_strip_basic_thinking() -> None:
    """<think>...</think> 제거."""
    text = "<think>고민중</think>실제 응답"
    assert strip_thinking_tags(text) == "실제 응답"


def test_strip_multiline_thinking() -> None:
    """다중 줄 thinking 제거."""
    text = "<think>\n고민\n중간\n</think>\n응답"
    assert strip_thinking_tags(text) == "응답"


def test_no_thinking_unchanged() -> None:
    """thinking X 변경 X."""
    text = "그냥 응답"
    assert strip_thinking_tags(text) == "그냥 응답"


def test_strip_multiple_thinking() -> None:
    """여러 <think> 제거."""
    text = "<think>first</think>중간<think>second</think>끝"
    assert strip_thinking_tags(text) == "중간끝"


def test_strip_case_insensitive() -> None:
    """대소문자 무관."""
    text = "<THINK>고민</THINK>응답"
    assert strip_thinking_tags(text) == "응답"


def test_empty_input() -> None:
    """빈 input 정합."""
    assert strip_thinking_tags("") == ""


def test_strips_whitespace() -> None:
    """결과 strip."""
    text = "<think>x</think>  응답  "
    assert strip_thinking_tags(text) == "응답"
