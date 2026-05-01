"""Interview Agent (★ 자료 2.2 Stage 1).

clear → skip (질문 X, 다음 단계)
ambiguous → questions 생성
off_topic → guide 메시지
LLM 실패 → Mock fallback
"""

from dataclasses import dataclass, field

from .intent_classifier import IntentClassification, IntentClassifier
from .question_generator import MockQuestionGenerator, QuestionGenerationResult, QuestionGenerator
from .types import InterviewResult

OFF_TOPIC_GUIDE = (
    "죄송합니다. 이 서비스는 인터랙티브 소설 게임입니다. "
    "원하시는 장르나 캐릭터를 알려주시면 게임을 시작할 수 있어요."
)


@dataclass
class InterviewSessionResult:
    """Interview Agent 세션 결과 (InterviewResult 확장)."""

    skip: bool = False
    parsed_input: str = ""
    questions: list[str] = field(default_factory=list)
    wait_for_user: bool = False
    classification: IntentClassification | None = None
    question_generation: QuestionGenerationResult | None = None
    cost_usd: float = 0.0

    def to_interview_result(self) -> InterviewResult:
        return InterviewResult(
            skip=self.skip,
            parsed_input=self.parsed_input,
            questions=self.questions,
            wait_for_user=self.wait_for_user,
        )


class InterviewAgent:
    """Interview Agent — intent classify → question generate."""

    def __init__(
        self,
        classifier: IntentClassifier | None = None,
        question_gen: QuestionGenerator | None = None,
        mock_gen: MockQuestionGenerator | None = None,
    ) -> None:
        self._classifier = classifier or IntentClassifier()
        self._question_gen = question_gen or QuestionGenerator(llm_client=None)
        self._mock_gen = mock_gen or MockQuestionGenerator()

    def run(self, user_input: str) -> InterviewSessionResult:
        classification = self._classifier.classify(user_input)

        if classification.intent == "clear":
            return InterviewSessionResult(
                skip=True,
                parsed_input=user_input,
                classification=classification,
            )

        if classification.intent == "off_topic":
            return InterviewSessionResult(
                skip=False,
                questions=[OFF_TOPIC_GUIDE],
                wait_for_user=True,
                classification=classification,
            )

        # ambiguous → generate questions
        gen_result = self._question_gen.generate(user_input)
        questions = gen_result.question_texts()
        if not questions:
            gen_result = self._mock_gen.generate(user_input)
            questions = gen_result.question_texts()

        return InterviewSessionResult(
            skip=False,
            questions=questions,
            wait_for_user=True,
            classification=classification,
            question_generation=gen_result,
        )
