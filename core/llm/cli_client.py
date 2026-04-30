"""CLI 기반 LLM Client (Day 1).

claude / codex / gemini 같은 CLI를 subprocess로 호출.
정액제 OAuth로 작동 (API 키 X). 비용 = 0 (한도 내).

HARNESS_CORE 9.2 패턴 적용.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from .client import JSONLLMResponse, LLMClient, LLMError, LLMResponse, Prompt

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "config" / "llm_registry.yaml"


def _load_registry() -> dict[str, Any]:
    """LLM Registry YAML 로드."""
    if not REGISTRY_PATH.exists():
        raise LLMError(f"LLM registry not found: {REGISTRY_PATH}")
    return yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


class CLIClient(LLMClient):
    """subprocess 기반 CLI LLM 클라이언트.

    config/llm_registry.yaml에서 모델 설정 로드.
    OAuth 정액제로 작동 (claude / codex / gemini 모두).
    """

    def __init__(
        self,
        model_key: str,
        timeout_seconds: float = 120.0,
        registry: dict[str, Any] | None = None,
    ):
        """
        Args:
            model_key: registry의 models.{key} (예: "claude_code")
            timeout_seconds: subprocess timeout
            registry: 명시적 registry (테스트용). None이면 파일에서 로드.
        """
        if registry is None:
            registry = _load_registry()

        if model_key not in registry["models"]:
            raise LLMError(
                f"Model '{model_key}' not found in registry. "
                f"Available: {list(registry['models'].keys())}"
            )

        self._key = model_key
        self._spec: dict[str, Any] = registry["models"][model_key]
        self._timeout = timeout_seconds

        if self._spec["type"] != "cli":
            raise LLMError(
                f"Model '{model_key}' is not a CLI model "
                f"(type: {self._spec['type']})"
            )

    @property
    def model_name(self) -> str:
        return str(self._spec["model_id"])

    @property
    def family(self) -> str:
        """Cross-Model verifier 선택 시 사용 (Day 4)."""
        return str(self._spec.get("family", "unknown"))

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        """CLI subprocess 호출.

        Args:
            prompt: 5-section 프롬프트
            **kwargs: 향후 확장용 (Day 1은 사용 안 함)

        Returns:
            LLMResponse (cost_usd=0, 정액제)

        Raises:
            LLMError: subprocess 실패, timeout
        """
        prompt_text = prompt.to_text()

        # registry의 args 템플릿 채우기
        cmd = [self._spec["command"]]
        for arg in self._spec["args"]:
            if "{prompt_text}" in arg:
                cmd.append(arg.replace("{prompt_text}", prompt_text))
            else:
                cmd.append(arg)

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(
                f"CLI timeout after {self._timeout}s for {self._key}: {e}"
            ) from e
        except FileNotFoundError as e:
            raise LLMError(
                f"CLI not found: {self._spec['command']} "
                f"(model: {self._key}). Install or check PATH."
            ) from e

        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise LLMError(
                f"CLI failed (exit {result.returncode}) for {self._key}.\n"
                f"stdout: {result.stdout[:500]}\n"
                f"stderr: {result.stderr[:500]}"
            )

        # stdout = LLM 응답 텍스트
        # stderr = 진행 메시지 / 경고 (codex의 'failed to record rollout' 등)
        text = result.stdout.strip()

        if not text:
            raise LLMError(
                f"Empty response from {self._key}.\n"
                f"stderr: {result.stderr[:500]}"
            )

        # CLI는 토큰 정보를 항상 안 줌.
        # Day 1은 토큰 카운트 0으로 두고, 정확한 추적은 Day 5 CostTracker에서.
        return LLMResponse(
            text=text,
            model=self.model_name,
            cost_usd=0.0,           # 정액제 (한도 내)
            latency_ms=latency_ms,
            input_tokens=0,         # CLI 미제공
            output_tokens=0,        # CLI 미제공
            raw={
                "stdout": result.stdout,
                "stderr": result.stderr[:1000],
                "cmd": cmd[:2] + ["...prompt truncated..."],
                "returncode": result.returncode,
            },
        )


    def generate_json(
        self,
        prompt: Prompt,
        schema: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> JSONLLMResponse:
        """JSON 응답 생성.

        claude_code는 `claude -p ... --output-format json` native JSON wrapper 사용.
        나머지 모델은 default post-hoc 파싱 (super().generate_json).
        """
        if self._key == "claude_code":
            return self._generate_json_claude(prompt, schema, **kwargs)
        return super().generate_json(prompt, schema, **kwargs)

    def _generate_json_claude(
        self,
        prompt: Prompt,
        schema: dict[str, Any] | None,
        **kwargs: Any,
    ) -> JSONLLMResponse:
        """claude -p --output-format json 호출.

        claude CLI의 wrapper JSON:
          {"result": "<text>", "usage": {"input_tokens": ..., "output_tokens": ...},
           "total_cost_usd": 0.0, ...}
        result 안에 실제 LLM 응답 텍스트 (마크다운 펜스 가능).
        """
        prompt_text = prompt.to_text()
        cmd = [self._spec["command"], "-p", prompt_text, "--output-format", "json"]

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise LLMError(
                f"CLI timeout after {self._timeout}s for {self._key}: {e}"
            ) from e
        except FileNotFoundError as e:
            raise LLMError(
                f"CLI not found: {self._spec['command']} "
                f"(model: {self._key}). Install or check PATH."
            ) from e

        latency_ms = int((time.time() - start) * 1000)

        if result.returncode != 0:
            raise LLMError(
                f"CLI failed (exit {result.returncode}) for {self._key}.\n"
                f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
            )

        try:
            wrapper = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse claude JSON wrapper: {e}\n"
                f"stdout: {result.stdout[:500]}"
            ) from e

        if not isinstance(wrapper, dict):
            raise LLMError(
                f"Expected wrapper object from claude, got {type(wrapper).__name__}"
            )

        actual_text = wrapper.get("result", "")
        if not actual_text or not isinstance(actual_text, str):
            raise LLMError(f"Empty or non-string 'result' in claude JSON wrapper: {wrapper}")

        text = actual_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            if lines[-1].strip() == "```":
                text = "\n".join(lines[1:-1])
            else:
                text = "\n".join(lines[1:])

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(
                f"Failed to parse JSON response: {e}\nText: {text[:500]}"
            ) from e

        if not isinstance(parsed, dict):
            raise LLMError(
                f"Expected JSON object, got {type(parsed).__name__}: {text[:200]}"
            )

        if schema:
            for key in schema.get("required", []):
                if key not in parsed:
                    raise LLMError(f"Missing required key in JSON: {key}")

        usage = wrapper.get("usage", {}) or {}
        return JSONLLMResponse(
            parsed=parsed,
            text=actual_text,
            model=self.model_name,
            cost_usd=float(wrapper.get("total_cost_usd", 0.0)),
            latency_ms=latency_ms,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
            raw={
                "wrapper": wrapper,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500],
            },
        )


def get_default_game_gm() -> CLIClient:
    """Day 1 게임 GM 기본 클라이언트 (claude -p).

    환경 검증 결과 12.7초로 가장 빠름 + 한국어 품질 최상.
    """
    return CLIClient(model_key="claude_code")
