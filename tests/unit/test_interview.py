"""W2 D2 Phase 3: Interview Agent 테스트."""

import pytest

from service.pipeline.intent_classifier import IntentClassification, IntentClassifier
from service.pipeline.interview import OFF_TOPIC_GUIDE, InterviewAgent, InterviewSessionResult
from service.pipeline.question_generator import MockQuestionGenerator


class _FakeClassifier(IntentClassifier):
    """고정 분류 결과 반환용."""

    def __init__(self, intent: str, confidence: float = 0.9) -> None:
        self._fixed = IntentClassification(intent=intent, confidence=confidence)  # type: ignore[arg-type]

    def classify(self, user_input: str) -> IntentClassification:
        return self._fixed


class TestInterviewAgentClear:
    def test_clear_input_skips(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("clear"))
        result = agent.run("바바리안 세계에서 주인공으로 플레이하고 싶어")
        assert result.skip is True
        assert result.wait_for_user is False

    def test_clear_parsed_input_preserved(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("clear"))
        result = agent.run("나의 입력")
        assert result.parsed_input == "나의 입력"

    def test_clear_no_questions(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("clear"))
        result = agent.run("test")
        assert result.questions == []

    def test_to_interview_result_clear(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("clear"))
        session = agent.run("test")
        ir = session.to_interview_result()
        assert ir.skip is True


class TestInterviewAgentAmbiguous:
    def test_ambiguous_generates_questions(self) -> None:
        agent = InterviewAgent(
            classifier=_FakeClassifier("ambiguous"),
            mock_gen=MockQuestionGenerator(questions=["Q1", "Q2", "Q3"]),
        )
        result = agent.run("모르겠어")
        assert result.skip is False
        assert len(result.questions) >= 1
        assert result.wait_for_user is True

    def test_ambiguous_uses_mock_by_default(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("ambiguous"))
        result = agent.run("뭔가")
        assert result.skip is False
        assert len(result.questions) > 0


class TestInterviewAgentOffTopic:
    def test_off_topic_returns_guide(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("off_topic"))
        result = agent.run("오늘 날씨 어때")
        assert result.skip is False
        assert OFF_TOPIC_GUIDE in result.questions
        assert result.wait_for_user is True


class TestInterviewSessionResult:
    def test_defaults(self) -> None:
        r = InterviewSessionResult()
        assert r.skip is False
        assert r.cost_usd == 0.0
        assert r.classification is None

    def test_to_interview_result_ambiguous(self) -> None:
        r = InterviewSessionResult(
            skip=False, questions=["Q1"], wait_for_user=True
        )
        ir = r.to_interview_result()
        assert ir.wait_for_user is True
        assert "Q1" in ir.questions


class TestInterviewAgentIntegration:
    def test_real_clear_input(self) -> None:
        agent = InterviewAgent()
        result = agent.run("바바리안 던전에서 주인공으로 플레이하고 싶어요")
        assert result.skip is True

    def test_real_off_topic(self) -> None:
        agent = InterviewAgent()
        result = agent.run("파이썬 코딩 도와줘")
        assert result.skip is False
        assert result.wait_for_user is True

    def test_classification_stored(self) -> None:
        agent = InterviewAgent(classifier=_FakeClassifier("clear", 0.95))
        result = agent.run("test")
        assert result.classification is not None
        assert result.classification.confidence == pytest.approx(0.95)
