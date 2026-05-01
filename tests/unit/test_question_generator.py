"""W2 D2 Phase 2: Question Generator + Prompts 테스트."""

from service.pipeline.prompts import INTERVIEW_PROMPT, build_interview_prompt
from service.pipeline.question_generator import (
    DEFAULT_QUESTIONS,
    MockQuestionGenerator,
    Question,
    QuestionGenerationResult,
    QuestionGenerator,
    _extract_string_array,
)


class TestBuildInterviewPrompt:
    def test_contains_user_input(self) -> None:
        prompt = build_interview_prompt("던전 모험 해보고 싶어")
        assert "던전 모험 해보고 싶어" in prompt

    def test_contains_identity_section(self) -> None:
        prompt = build_interview_prompt("test")
        assert "[IDENTITY]" in prompt

    def test_contains_output_format_section(self) -> None:
        prompt = build_interview_prompt("test")
        assert "[OUTPUT FORMAT]" in prompt

    def test_prompt_template_not_empty(self) -> None:
        assert len(INTERVIEW_PROMPT) > 100


class TestExtractStringArray:
    def test_valid_array(self) -> None:
        raw = '["질문1", "질문2", "질문3"]'
        result = _extract_string_array(raw)
        assert result == ["질문1", "질문2", "질문3"]

    def test_array_in_text(self) -> None:
        raw = '다음입니다: ["a", "b"] 감사합니다'
        result = _extract_string_array(raw)
        assert result == ["a", "b"]

    def test_no_array(self) -> None:
        result = _extract_string_array("배열 없는 텍스트")
        assert result is None

    def test_invalid_json(self) -> None:
        result = _extract_string_array("[invalid json")
        assert result is None

    def test_non_string_items_filtered(self) -> None:
        raw = '["ok", 123, null, "also_ok"]'
        result = _extract_string_array(raw)
        assert result == ["ok", "also_ok"]


class TestMockQuestionGenerator:
    def test_returns_default_questions(self) -> None:
        gen = MockQuestionGenerator()
        result = gen.generate("아무거나")
        assert len(result.questions) == len(DEFAULT_QUESTIONS)
        assert result.mock_used is True

    def test_custom_questions(self) -> None:
        gen = MockQuestionGenerator(questions=["Q1", "Q2"])
        result = gen.generate("test")
        assert result.question_texts() == ["Q1", "Q2"]

    def test_question_order(self) -> None:
        gen = MockQuestionGenerator(questions=["A", "B", "C"])
        result = gen.generate("test")
        for i, q in enumerate(result.questions):
            assert q.order == i


class TestQuestionGeneratorNoClient:
    def test_no_client_uses_mock(self) -> None:
        gen = QuestionGenerator(llm_client=None)
        result = gen.generate("판타지 플레이")
        assert result.mock_used is True
        assert result.error == "llm_client not configured"
        assert len(result.questions) > 0


class TestQuestionGeneratorWithFakeClient:
    def test_valid_llm_output(self) -> None:
        class FakeClient:
            def complete(self, prompt: str) -> str:
                return '["질문A", "질문B", "질문C"]'

        gen = QuestionGenerator(llm_client=FakeClient())
        result = gen.generate("판타지 던전")
        assert result.mock_used is False
        assert result.question_texts() == ["질문A", "질문B", "질문C"]

    def test_bad_llm_output_falls_back_to_mock(self) -> None:
        class BadClient:
            def complete(self, prompt: str) -> str:
                return "전혀 JSON 없는 응답"

        gen = QuestionGenerator(llm_client=BadClient())
        result = gen.generate("판타지")
        assert result.mock_used is True
        assert result.error == "json_parse_failed"

    def test_exception_falls_back_to_mock(self) -> None:
        class CrashClient:
            def complete(self, prompt: str) -> str:
                raise RuntimeError("API 오류")

        gen = QuestionGenerator(llm_client=CrashClient())
        result = gen.generate("던전")
        assert result.mock_used is True
        assert "API 오류" in (result.error or "")


class TestQuestionDataclass:
    def test_defaults(self) -> None:
        q = Question(text="테스트")
        assert q.order == 0

    def test_result_question_texts(self) -> None:
        r = QuestionGenerationResult(
            questions=[Question("A", 0), Question("B", 1)]
        )
        assert r.question_texts() == ["A", "B"]
