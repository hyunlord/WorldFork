"""CLI 기반 LLM Client (Day 1).

claude / codex / gemini 같은 CLI를 subprocess로 호출.
정액제 OAuth로 작동 (API 키 X). 비용 = 0 (한도 내).

HARNESS_CORE 9.2 패턴 적용.
"""

import subprocess
import time
from pathlib import Path
from typing import Any

import yaml

from .client import LLMClient, LLMError, LLMResponse, Prompt

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


def get_default_game_gm() -> CLIClient:
    """Day 1 게임 GM 기본 클라이언트 (claude -p).

    환경 검증 결과 12.7초로 가장 빠름 + 한국어 품질 최상.
    """
    return CLIClient(model_key="claude_code")
