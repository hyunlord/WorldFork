"""
LLM Client 추상화 (HARNESS_CORE 9장).

Day 1 미니멀:
  - LLMClient ABC
  - Prompt (5-section system + user)
  - LLMResponse (text + cost + latency + tokens)
  - LLMError

이후 추가:
  - Day 4: generate_json() 메서드 (구조화 출력)
  - Day 5: 비동기 a_generate()
  - Tier 1: Local 모델 클라이언트 (DGX Spark)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Prompt:
    """5-section system prompt + user message.

    HARNESS_CORE 7장의 5-section 구조:
      - IDENTITY: 누구인가
      - TASK: 무엇을 하는가
      - SPEC: 컨텍스트 / 룰
      - OUTPUT FORMAT: 어떻게 응답
      - EXAMPLES: 예시 (선택)

    system 문자열에 위 5섹션 포함, user는 실제 입력.
    """

    system: str
    user: str

    def to_text(self) -> str:
        """전체 프롬프트를 단일 텍스트로 (CLI 호출용).

        CLI는 system / user 분리 못 받음 → 단일 문자열로 변환.
        """
        return f"[SYSTEM]\n{self.system}\n\n[USER]\n{self.user}"


@dataclass
class LLMResponse:
    """LLM 호출 결과.

    raw 는 provider별 원본 응답 (디버깅용).
    cost_usd 는 정액제 호출 시 0 (한도 내), API 호출 시 실제 비용.
    """

    text: str
    model: str
    cost_usd: float
    latency_ms: int
    input_tokens: int
    output_tokens: int
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient(ABC):
    """LLM 호출 추상화.

    API / Local / CLI 무관하게 동일 인터페이스.
    Day 1 미니멀: generate() 만.
    Day 4 추가 예정: generate_json(schema), 비동기 a_generate().
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델 식별자 (예: 'claude-code', 'codex', 'gemini')."""
        ...

    @abstractmethod
    def generate(self, prompt: "Prompt", **kwargs: Any) -> "LLMResponse":
        """프롬프트 보내고 응답 받기.

        Args:
            prompt: 5-section 프롬프트
            **kwargs: provider별 추가 옵션 (timeout 등)

        Returns:
            LLMResponse with text, cost, latency, tokens

        Raises:
            LLMError: CLI 호출 실패, timeout, 인증 실패 등
        """
        ...


class LLMError(Exception):
    """LLM 호출 실패."""

    pass
