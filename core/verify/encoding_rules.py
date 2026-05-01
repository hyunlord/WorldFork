"""Encoding 버그 검출 룰 (W1 D4 발견: '籠여져' 한자 깨짐).

9B Q3 GGUF 양자화의 토크나이저 엣지케이스 대응.
"""

import re
from typing import Any

from .rule import CheckFailure, Rule, SeverityLevel

# 한자 (CJK Unified Ideographs): Basic + Extension A
HANJA_PATTERN = re.compile(r"[一-鿿㐀-䶿]")

# 한자 + 한글 인접: 양자화 decoding 버그 시그니처 (예: '籠여져')
SUSPICIOUS_HANJA_KOREAN = re.compile(
    r"[一-鿿㐀-䶿][가-힯]"
)


class HanjaInKoreanRule(Rule):
    """한국어 응답에 한자 섞임 검출.

    한국어 게임 응답에서 한자는 일반적으로 사용 X.
    9B Q3 양자화 시 가끔 발생하는 decoding 버그.
    """

    @property
    def rule_id(self) -> str:
        return "hanja_in_korean"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        if context.get("language") != "ko":
            return None

        hanja_chars = HANJA_PATTERN.findall(response)
        if not hanja_chars:
            return None

        # 한자 + 한글 인접 = decoding 버그 시그니처 → major
        suspicious = SUSPICIOUS_HANJA_KOREAN.findall(response)
        if suspicious:
            return CheckFailure(
                rule=self.rule_id,
                severity="major",
                detail=(
                    f"한자+한글 인접 (decoding 버그 의심): "
                    f"{len(suspicious)}개. 예: {suspicious[:3]}"
                ),
            )

        # 한자 3개 이상만 단독 → minor
        if len(hanja_chars) >= 3:
            return CheckFailure(
                rule=self.rule_id,
                severity="minor",
                detail=f"한자 {len(hanja_chars)}개 (예: {hanja_chars[:3]})",
            )

        return None


class GarbledTextRule(Rule):
    """깨진 텍스트 패턴 검출 (Unicode replacement char).

    U+FFFD ('?') — 잘못된 UTF-8 디코딩 시 나타남.
    """

    @property
    def rule_id(self) -> str:
        return "garbled_text"

    @property
    def severity(self) -> SeverityLevel:
        return "major"

    def check(self, response: str, context: dict[str, Any]) -> CheckFailure | None:
        replacement_count = response.count("�")
        if replacement_count > 0:
            return CheckFailure(
                rule=self.rule_id,
                severity="major",
                detail=f"Unicode replacement chars (�): {replacement_count}개",
            )
        return None


def get_encoding_rules() -> list[Rule]:
    """W1 D5 encoding 룰 묶음."""
    return [HanjaInKoreanRule(), GarbledTextRule()]
