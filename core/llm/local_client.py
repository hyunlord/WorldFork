"""Local LLM Client — llama-server / SGLang HTTP (OpenAI compat).

DGX Spark 구성 (Phase A.2 이후):
  - qwen3.6-27b   (8081): SGLang FP8 + MTP NEXTN, narrative GM
  - qwen35-9b-q3  (8083): llama-server, NPC dialogue (38 tok/s)

Thinking OFF: chat_template_kwargs={"enable_thinking": false} 기본 적용.
  Qwen3.5/3.6 공통 — 사용 전 반드시 OFF 해야 latency 정상.

Phase A.3-b 추가:
  - LocalLLMClient.generate_json 오버라이드
  - supports_json_schema=True 인 backend (★ SGLang xgrammar) 에서는 OpenAI
    response_format json_schema 본 inject → server-side 정합 강제
  - 그 외 backend 는 base class 의 post-hoc parse 그대로 사용
"""

import json
import re
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
import requests

from .client import (
    JSONLLMResponse,
    LLMClient,
    LLMError,
    LLMResponse,
    Prompt,
)

_THINKING_OFF: dict[str, Any] = {"enable_thinking": False}

# Fallback: reasoning_content 분리 미지원 server에서 content에 thinking 포함 시 제거
_THINK_RE: re.Pattern[str] = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def _to_strict_object_schema(
    partial: dict[str, Any],
) -> dict[str, Any]:
    """JUDGE_SCHEMA 류 sparse dict 본 SGLang strict-mode 정합 schema 본 변환.

    입력 dict 가 root ``type`` / ``additionalProperties`` 없이도, root object
    schema 본 정합 형태로 wrap. ``additionalProperties`` 가 명시되어 있으면
    원본 그대로 유지 (★ caller override 허용).
    """
    if partial.get("type") == "object" and "additionalProperties" in partial:
        return dict(partial)

    properties = partial.get("properties", {})
    required = partial.get("required", list(properties.keys()))
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": partial.get("additionalProperties", False),
    }


class LocalLLMClient(LLMClient):
    """llama-server / SGLang / vLLM OpenAI-compat HTTP 클라이언트.

    chat_template_kwargs defaults to thinking OFF for Qwen3.x series.

    Phase A.3-b: supports_json_schema=True 인 backend (★ SGLang xgrammar
    backend) 본 generate_json 시 OpenAI response_format json_schema 본 사용.
    """

    def __init__(
        self,
        model_key: str,
        base_url: str,
        model_name_in_request: str = "default",
        timeout: int = 120,
        chat_template_kwargs: dict[str, Any] | None = None,
        supports_json_schema: bool = False,
    ) -> None:
        self._key = model_key
        self._base_url = base_url.rstrip("/")
        self._model_name_in_request = model_name_in_request
        self._timeout = timeout
        self._chat_template_kwargs: dict[str, Any] = (
            _THINKING_OFF if chat_template_kwargs is None else chat_template_kwargs
        )
        self._supports_json_schema = supports_json_schema

    @property
    def model_name(self) -> str:
        return self._key

    def _build_payload(
        self,
        prompt: Prompt,
        **kwargs: Any,
    ) -> dict[str, Any]:
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
        return payload

    def _post(
        self,
        payload: dict[str, Any],
    ) -> tuple[dict[str, Any], int]:
        start = time.time()
        try:
            resp = requests.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
        except requests.RequestException as e:
            raise LLMError(
                f"Local LLM request failed [{self._key}]: {e}"
            ) from e

        latency_ms = int((time.time() - start) * 1000)

        if resp.status_code != 200:
            raise LLMError(
                f"Local LLM HTTP {resp.status_code} [{self._key}]: "
                f"{resp.text[:500]}"
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise LLMError(
                f"JSON parse failed [{self._key}]: {e}"
            ) from e
        return data, latency_ms

    @staticmethod
    def _extract_content(data: dict[str, Any], key: str) -> str:
        try:
            return data["choices"][0]["message"]["content"]  # type: ignore[no-any-return]
        except (KeyError, IndexError) as e:
            raise LLMError(
                f"Unexpected response format [{key}]: {data}"
            ) from e

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        """OpenAI-compat /v1/chat/completions 호출."""
        payload = self._build_payload(prompt, **kwargs)
        data, latency_ms = self._post(payload)
        text = self._extract_content(data, self._key)
        if text is None:
            raise LLMError(
                f"Empty content [{self._key}] (★ reasoning tokens?): {data}"
            )
        text = _THINK_RE.sub("", text).strip()
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

    async def astream(
        self,
        prompt: Prompt,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """평문 narrative 토큰 스트리밍 (OpenAI-compat ``stream: true``).

        SGLang/llama-server가 SSE chunk(`delta.content`)를 점진 전달 → 호출자가
        토큰을 즉시 노출(체감 지연 제거). ``_build_payload``를 재사용하므로
        thinking-off·max_tokens·temperature 기본값이 그대로 적용된다.
        reasoning_content는 별도 필드라 thinking-off 시 content stream은 깨끗하다.
        JSON schema 강제는 적용하지 않는다(평문 — narrative 자유).
        """
        payload = self._build_payload(prompt, **kwargs)
        payload["stream"] = True
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/v1/chat/completions",
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode("utf-8", "replace")
                    raise LLMError(
                        f"Local LLM stream HTTP {resp.status_code} "
                        f"[{self._key}]: {body[:500]}"
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if not data or data == "[DONE]":
                        if data == "[DONE]":
                            break
                        continue
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = obj.get("choices") or [{}]
                    delta = choices[0].get("delta") or {}
                    piece = delta.get("content")
                    if piece:
                        yield piece

    def generate_json(
        self,
        prompt: Prompt,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> JSONLLMResponse:
        """JSON 응답 생성.

        ``supports_json_schema=True`` + ``schema`` 제공 시 SGLang
        ``response_format: json_schema`` 본 사용 (★ xgrammar 강제 정합).
        그 외 base class 의 post-hoc parse 본 fallback.
        """
        if not self._supports_json_schema or schema is None:
            return super().generate_json(prompt, schema, **kwargs)

        wrapped = _to_strict_object_schema(schema)
        payload = self._build_payload(prompt, **kwargs)
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": kwargs.get("schema_name", "Response"),
                "schema": wrapped,
                "strict": True,
            },
        }

        data, latency_ms = self._post(payload)
        text = self._extract_content(data, self._key)
        if text is None:
            raise LLMError(
                f"Empty content under json_schema [{self._key}]: {data}"
            )
        text = _THINK_RE.sub("", text).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"json_schema parse failed [{self._key}]: {e}\n"
                f"Text: {text[:500]}"
            ) from e

        if not isinstance(parsed, dict):
            raise LLMError(
                f"Expected JSON object [{self._key}], got "
                f"{type(parsed).__name__}: {text[:200]}"
            )

        usage = data.get("usage", {})
        return JSONLLMResponse(
            parsed=parsed,
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
    """Qwen3.6-27B — SGLang FP8 + MTP NEXTN, narrative GM (port 8081).

    Phase A.2: llama-server Q3 GGUF → SGLang safetensors FP8 on-the-fly +
    EAGLE/NEXTN speculative decoding. ``model_key`` 본 호환 위해 유지.

    Phase A.3-b: SGLang xgrammar backend 본 활용하여 generate_json 시
    ``response_format: json_schema`` 본 server-side 정합 강제.
    """
    return LocalLLMClient(
        model_key="qwen36-27b-q3",
        base_url="http://localhost:8081",
        model_name_in_request="qwen3.6-27b",
        supports_json_schema=True,
    )


def get_qwen36_27b_q2() -> LocalLLMClient:
    """Qwen3.6-27B Q2_K_XL — 본인 직관 baseline, 14.5 tok/s (port 8082)."""
    return LocalLLMClient(
        model_key="qwen36-27b-q2",
        base_url="http://localhost:8082",
        model_name_in_request="qwen36-27b-q2",
    )


def get_qwen35_9b_q3() -> LocalLLMClient:
    """Qwen3.5-9B Q3_K_XL — NPC dialogue ★, 38 tok/s / 5초 이하 (port 8083).

    Phase A.3-c: llama-server 의 OpenAI-compat response_format json_schema
    지원 (★ Phase C LLM filter 에서 검증) 본 활용하여 ``supports_json_schema``
    활성. encounter generator / smoke 의 schema 강제 robustness 강화.
    """
    return LocalLLMClient(
        model_key="qwen35-9b-q3",
        base_url="http://localhost:8083",
        model_name_in_request="qwen35-9b-q3",
        supports_json_schema=True,
    )


def get_default_npc() -> LocalLLMClient:
    """실시간 NPC 응답용 — 9B Q3 (38 tok/s)."""
    return get_qwen35_9b_q3()


def get_default_gm() -> LocalLLMClient:
    """GM / 내러티브 생성용 — 27B Q2 (본인 직관 baseline)."""
    return get_qwen36_27b_q2()
