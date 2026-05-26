"""LLM 응답 후처리 helper — thinking 태그 제거 등."""

from __future__ import annotations

import re

# Qwen3 thinking 모드: content에 <think>...</think> 가 포함될 경우 제거
THINKING_PATTERN: re.Pattern[str] = re.compile(
    r"<think>.*?</think>",
    re.DOTALL | re.IGNORECASE,
)


def strip_thinking_tags(text: str) -> str:
    """<think>...</think> 블록 제거 후 strip.

    Qwen3 thinking 모드 활성 시 content에 thinking 포함 가능.
    /no_think directive 미적용 시 fallback 정합.
    - 다중 줄 / 다중 인스턴스 정합
    - 대소문자 무관
    """
    if not text:
        return text
    cleaned = THINKING_PATTERN.sub("", text)
    return cleaned.strip()
