"""Question Generator — Mock + Real LLM (★ 자료 2.2 Stage 1).

Mock: 기본 3-질문 반환 (Tier 1 기본값)
Real: LLM 호출 + JSON 배열 추출 (Tier 2+)
"""

import json
import re
from dataclasses import dataclass, field
from typing import Protocol

from .prompts import build_interview_prompt

DEFAULT_QUESTIONS: list[str] = [
    "어떤 장르/세계관을 원하시나요?",
    "주인공으로 시작하시겠어요, 아니면 다른 역할로?",
    "전투 중심인가요, 스토리/탐험 중심인가요?",
]

_ARRAY_RE = re.compile(r"\[.*?\]", re.DOTALL)


class LLMClient(Protocol):
    """LLM 클라이언트 프로토콜 (duck-typing)."""

    def complete(self, prompt: str) -> str: ...


@dataclass
class Question:
    """인터뷰 질문 단위."""

    text: str
    order: int = 0


@dataclass
class QuestionGenerationResult:
    """질문 생성 결과."""

    questions: list[Question] = field(default_factory=list)
    raw_output: str = ""
    cost_usd: float = 0.0
    mock_used: bool = False
    error: str | None = None

    def question_texts(self) -> list[str]:
        return [q.text for q in self.questions]


def _extract_string_array(raw: str) -> list[str] | None:
    """raw LLM 출력에서 첫 번째 JSON 문자열 배열 추출."""
    match = _ARRAY_RE.search(raw)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    texts = [str(item) for item in parsed if isinstance(item, str)]
    return texts if texts else None


class MockQuestionGenerator:
    """Mock 질문 생성기 (LLM 호출 X)."""

    def __init__(self, questions: list[str] | None = None) -> None:
        self._questions = questions or DEFAULT_QUESTIONS

    def generate(self, user_input: str) -> QuestionGenerationResult:  # noqa: ARG002
        qs = [Question(text=t, order=i) for i, t in enumerate(self._questions)]
        return QuestionGenerationResult(questions=qs, mock_used=True)


class QuestionGenerator:
    """Real LLM 질문 생성기.

    ★ Tier 1에서는 LLM 실패 시 Mock fallback.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._client = llm_client
        self._mock = MockQuestionGenerator()

    def generate(self, user_input: str) -> QuestionGenerationResult:
        if self._client is None:
            result = self._mock.generate(user_input)
            result.mock_used = True
            result.error = "llm_client not configured"
            return result

        prompt = build_interview_prompt(user_input)
        try:
            raw: str = self._client.complete(prompt)
        except Exception as exc:
            result = self._mock.generate(user_input)
            result.mock_used = True
            result.error = str(exc)
            return result

        texts = _extract_string_array(raw)
        if texts is None:
            result = self._mock.generate(user_input)
            result.mock_used = True
            result.raw_output = raw
            result.error = "json_parse_failed"
            return result

        qs = [Question(text=t, order=i) for i, t in enumerate(texts)]
        return QuestionGenerationResult(questions=qs, raw_output=raw, mock_used=False)
