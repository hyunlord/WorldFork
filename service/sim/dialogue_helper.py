"""hybrid dialogue 분기 helper — template vs 27B 결정."""

from __future__ import annotations

SHORT_GREETING_KEYWORDS: frozenset[str] = frozenset([
    "안녕", "인사", "ㅎㅇ", "반갑", "헬로", "감사", "고마",
])

DEEP_DIALOGUE_KEYWORDS: frozenset[str] = frozenset([
    "물어", "질문", "이야기", "대화", "묻", "알려", "설명", "조언", "도움",
    "부탁", "알고", "궁금", "무슨", "어떤", "왜", "어떻게", "뭐라",
])


def is_deep_dialogue(user_input: str) -> bool:
    """True → 27B 호출, False → template.

    rules (우선순위 순):
    1. DEEP keyword 포함 → True
    2. 15자 미만 + SHORT keyword → False
    3. 30자 초과 → True
    4. default → False (latency 절약)
    """
    text = user_input.strip()
    if any(kw in text for kw in DEEP_DIALOGUE_KEYWORDS):
        return True
    if len(text) < 15 and any(kw in text for kw in SHORT_GREETING_KEYWORDS):
        return False
    if len(text) > 30:
        return True
    return False
