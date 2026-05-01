"""Intent Classifier — rule-based (★ 자료 2.2 Stage 1).

분류 결과:
  - clear: 명확한 입력 (작품명 + 의도 키워드 or 5단어 이상)
  - ambiguous: 애매한 입력 (짧거나 의도 불분명)
  - off_topic: 게임과 무관한 입력
"""

from dataclasses import dataclass, field
from typing import Literal

# 플레이 의도 키워드 (한국어)
INTENT_KEYWORDS_KO: list[str] = [
    "하고싶",
    "플레이",
    "되고싶",
    "살아보",
    "체험",
    "해보고",
    "해보",
    "하고 싶",
    "되고 싶",
    "살고 싶",
    "살아보고",
    "시작",
    "시작하",
    "진행",
]

# 역할/포지션 키워드 (한국어)
ENTRY_KEYWORDS_KO: list[str] = [
    "주인공",
    "조연",
    "엑스트라",
    "캐릭터",
    "역할",
    "포지션",
    "빌런",
    "악당",
    "영웅",
    "탐정",
    "기사",
    "마법사",
    "전사",
]

# 알려진 작품명/세계관 패턴 (부분 매칭)
WORK_PATTERNS: list[str] = [
    "바바리안",
    "던전",
    "판타지",
    "회귀",
    "환생",
    "이세계",
    "무협",
    "로맨스",
    "현대",
    "학원",
    "아포칼립스",
    "SF",
    "마법",
    "novice_dungeon_run",
    "투르윈",
]

# 오프토픽 키워드 (게임과 무관)
OFF_TOPIC_KEYWORDS: list[str] = [
    "날씨",
    "주식",
    "뉴스",
    "스포츠",
    "음식",
    "레시피",
    "쇼핑",
    "정치",
    "경제",
    "코딩",
    "프로그래밍",
    "번역",
    "수학",
    "계산",
]

MIN_CLEAR_WORDS = 5


@dataclass
class IntentClassification:
    """Intent 분류 결과."""

    intent: Literal["clear", "ambiguous", "off_topic"]
    confidence: float
    detected_features: list[str] = field(default_factory=list)
    reason: str = ""


class IntentClassifier:
    """Rule-based intent 분류기.

    자료 2.2 Stage 1: LLM 없이 키워드 + 휴리스틱으로 분류.
    """

    def classify(self, user_input: str) -> IntentClassification:
        text = user_input.strip()

        if not text:
            return IntentClassification(
                intent="ambiguous",
                confidence=1.0,
                reason="빈 입력",
            )

        features: list[str] = []

        # 오프토픽 체크 (먼저)
        off_hits = [kw for kw in OFF_TOPIC_KEYWORDS if kw in text]
        if off_hits:
            features.extend(f"off_topic:{kw}" for kw in off_hits)
            # 오프토픽 키워드만 있고 의도 키워드 없으면 off_topic
            intent_hits = [kw for kw in INTENT_KEYWORDS_KO if kw in text]
            if not intent_hits:
                return IntentClassification(
                    intent="off_topic",
                    confidence=0.7,
                    detected_features=features,
                    reason=f"오프토픽 키워드 감지: {off_hits}",
                )

        # 의도 키워드 체크
        intent_hits = [kw for kw in INTENT_KEYWORDS_KO if kw in text]
        features.extend(f"intent:{kw}" for kw in intent_hits)

        # 작품/세계관 패턴 체크
        work_hits = [p for p in WORK_PATTERNS if p in text]
        features.extend(f"work:{p}" for p in work_hits)

        # 역할 키워드 체크
        entry_hits = [kw for kw in ENTRY_KEYWORDS_KO if kw in text]
        features.extend(f"entry:{kw}" for kw in entry_hits)

        # 단어 수 (공백 기준)
        n_words = len(text.split())

        # 분류 로직
        if work_hits and intent_hits:
            return IntentClassification(
                intent="clear",
                confidence=0.9,
                detected_features=features,
                reason=f"작품패턴+의도키워드: {work_hits}, {intent_hits}",
            )

        if n_words >= MIN_CLEAR_WORDS and work_hits:
            return IntentClassification(
                intent="clear",
                confidence=0.6,
                detected_features=features,
                reason=f"5단어+작품패턴: n={n_words}, works={work_hits}",
            )

        if n_words >= MIN_CLEAR_WORDS and (intent_hits or entry_hits):
            return IntentClassification(
                intent="clear",
                confidence=0.6,
                detected_features=features,
                reason=f"5단어+의도/역할: n={n_words}",
            )

        if n_words <= 4:
            return IntentClassification(
                intent="ambiguous",
                confidence=0.9,
                detected_features=features,
                reason=f"짧은 입력: {n_words}단어",
            )

        return IntentClassification(
            intent="ambiguous",
            confidence=0.5,
            detected_features=features,
            reason="의도 불분명",
        )
