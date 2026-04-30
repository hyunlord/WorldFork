"""Local LLM Client — llama-server HTTP (OpenAI compat).

Tier 1 W1 D1: DGX Spark 3-server 구성.
  - qwen36-27b-q3 (8081): GM 후보, 긴 응답
  - qwen36-27b-q2 (8082): 본인 직관 baseline
  - qwen35-9b-q3  (8083): NPC dialogue ★ (38 tok/s, 5초 이하)

Thinking OFF: chat_template_kwargs={"enable_thinking": false} 기본 적용.
  Qwen3.5/3.6 공통 — 사용 전 반드시 OFF 해야 latency 정상.
"""

import time
from typing import Any

import requests

from .client import LLMClient, LLMError, LLMResponse, Prompt

_THINKING_OFF: dict[str, Any] = {"enable_thinking": False}


class LocalLLMClient(LLMClient):
    """llama-server / SGLang / vLLM OpenAI-compat HTTP 클라이언트.

    chat_template_kwargs defaults to thinking OFF for Qwen3.x series.
    """

    def __init__(
        self,
        model_key: str,
        base_url: str,
        model_name_in_request: str = "default",
        timeout: int = 120,
        chat_template_kwargs: dict[str, Any] | None = None,
    ) -> None:
        self._key = model_key
        self._base_url = base_url.rstrip("/")
        self._model_name_in_request = model_name_in_request
        self._timeout = timeout
        # Qwen3.x thinking OFF — caller가 명시적으로 None 전달하면 그대로
        self._chat_template_kwargs: dict[str, Any] = (
            _THINKING_OFF if chat_template_kwargs is None else chat_template_kwargs
        )

    @property
    def model_name(self) -> str:
        return self._key

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        """OpenAI-compat /v1/chat/completions 호출."""
        messages: list[dict[str, str]] = []
        if prompt.system:
            messages.append({"role": "system", "content": prompt.system})
        messages.append({"role": "user", "content": prompt.user})

        payload: dict[str, Any] = {
            "model": self._model_name_in_request,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", 1500),
            "temperature": kwargs.get("temperature", 0.7),
        }
        if self._chat_template_kwargs:
            payload["chat_template_kwargs"] = self._chat_template_kwargs

        start = time.time()
        try:
            resp = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            raise LLMError(f"Local LLM request failed [{self._key}]: {e}") from e

        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            raise LLMError(
                f"Local LLM HTTP {resp.status_code} [{self._key}]: {resp.text[:500]}"
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMError(f"JSON parse failed [{self._key}]: {e}") from e

        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(
                f"Unexpected response format [{self._key}]: {data}"
            ) from e

        usage = data.get("usage", {})
        return LLMResponse(
            text=text,
            model=self._key,
            cost_usd=0.0,
            latency_ms=latency_ms,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            raw={"data": data, "base_url": self._base_url},
        )


# ---------------------------------------------------------------------------
# Factory 함수
# ---------------------------------------------------------------------------

def get_qwen36_27b_q3() -> LocalLLMClient:
    """Qwen3.6-27B Q3_K_XL — GM 후보, 높은 품질 (port 8081)."""
    return LocalLLMClient(
        model_key="qwen36-27b-q3",
        base_url="http://localhost:8081",
        model_name_in_request="qwen36-27b-q3",
    )


def get_qwen36_27b_q2() -> LocalLLMClient:
    """Qwen3.6-27B Q2_K_XL — 본인 직관 baseline, 14.5 tok/s (port 8082)."""
    return LocalLLMClient(
        model_key="qwen36-27b-q2",
        base_url="http://localhost:8082",
        model_name_in_request="qwen36-27b-q2",
    )


def get_qwen35_9b_q3() -> LocalLLMClient:
    """Qwen3.5-9B Q3_K_XL — NPC dialogue ★, 38 tok/s / 5초 이하 (port 8083)."""
    return LocalLLMClient(
        model_key="qwen35-9b-q3",
        base_url="http://localhost:8083",
        model_name_in_request="qwen35-9b-q3",
    )


def get_default_npc() -> LocalLLMClient:
    """실시간 NPC 응답용 — 9B Q3 (38 tok/s)."""
    return get_qwen35_9b_q3()


def get_default_gm() -> LocalLLMClient:
    """GM / 내러티브 생성용 — 27B Q2 (본인 직관 baseline)."""
    return get_qwen36_27b_q2()
