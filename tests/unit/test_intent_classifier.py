"""W2 D2 Phase 1: Intent Classifier 테스트."""

from service.pipeline.intent_classifier import (
    ENTRY_KEYWORDS_KO,
    INTENT_KEYWORDS_KO,
    WORK_PATTERNS,
    IntentClassification,
    IntentClassifier,
)


class TestIntentClassifierClear:
    def test_work_plus_intent(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("바바리안 세계에서 주인공으로 플레이하고 싶어")
        assert result.intent == "clear"
        assert result.confidence >= 0.8

    def test_work_plus_intent_short_form(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("던전 판타지 세계 체험해보고 싶어요")
        assert result.intent == "clear"

    def test_five_words_with_work(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("novice_dungeon_run 세계에서 모험을 시작하고 싶습니다")
        assert result.intent == "clear"

    def test_entry_keyword_long(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("판타지 세계에서 마법사 캐릭터로 플레이 하고 싶어요")
        assert result.intent == "clear"


class TestIntentClassifierAmbiguous:
    def test_empty_input(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("")
        assert result.intent == "ambiguous"
        assert result.confidence == 1.0

    def test_whitespace_only(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("   ")
        assert result.intent == "ambiguous"

    def test_too_short_no_keywords(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("뭔가 하고 싶어")
        assert result.intent == "ambiguous"

    def test_one_word(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("판타지")
        assert result.intent == "ambiguous"

    def test_vague_long_sentence(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("그냥 어떤 것 같은 느낌이 드는데 잘 모르겠어요")
        assert result.intent == "ambiguous"


class TestIntentClassifierOffTopic:
    def test_weather(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("오늘 날씨 어때")
        assert result.intent == "off_topic"

    def test_coding(self) -> None:
        clf = IntentClassifier()
        result = clf.classify("파이썬 코딩 도와줘")
        assert result.intent == "off_topic"

    def test_off_topic_with_intent_stays_ambiguous_or_clear(self) -> None:
        clf = IntentClassifier()
        # 오프토픽 + 의도 키워드 동시 → off_topic 탈출
        result = clf.classify("날씨 얘기지만 게임 플레이하고 싶어요 판타지 던전에서")
        assert result.intent != "off_topic"


class TestIntentClassificationDataclass:
    def test_defaults(self) -> None:
        ic = IntentClassification(intent="clear", confidence=0.9)
        assert ic.detected_features == []
        assert ic.reason == ""

    def test_with_features(self) -> None:
        ic = IntentClassification(
            intent="ambiguous",
            confidence=0.5,
            detected_features=["work:던전"],
            reason="test",
        )
        assert "work:던전" in ic.detected_features


class TestKeywordConfig:
    def test_intent_keywords_not_empty(self) -> None:
        assert len(INTENT_KEYWORDS_KO) > 0
        assert "플레이" in INTENT_KEYWORDS_KO

    def test_entry_keywords_not_empty(self) -> None:
        assert len(ENTRY_KEYWORDS_KO) > 0
        assert "주인공" in ENTRY_KEYWORDS_KO

    def test_work_patterns_not_empty(self) -> None:
        assert len(WORK_PATTERNS) > 0
        assert "던전" in WORK_PATTERNS
