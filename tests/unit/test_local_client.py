"""Tier 1 W1 D1: LocalLLMClient 단위 테스트 (Mock 기반, 실제 HTTP 호출 X)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from core.llm.client import LLMError, Prompt
from core.llm.local_client import (
    LocalLLMClient,
    get_default_gm,
    get_default_npc,
    get_qwen35_9b_q3,
    get_qwen36_27b_q2,
    get_qwen36_27b_q3,
)

_SAMPLE_RESPONSE = {
    "choices": [{"message": {"content": "안녕하세요. 셰인입니다."}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 50, "completion_tokens": 30},
}


def _mock_ok(content: str = "안녕하세요. 셰인입니다.") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 30},
    }
    return resp


class TestLocalLLMClientInit:
    def test_defaults(self) -> None:
        c = LocalLLMClient(model_key="test", base_url="http://localhost:8081")
        assert c.model_name == "test"
        assert c._base_url == "http://localhost:8081"
        assert c._chat_template_kwargs == {"enable_thinking": False}

    def test_trailing_slash_stripped(self) -> None:
        c = LocalLLMClient(model_key="x", base_url="http://localhost:8081/")
        assert c._base_url == "http://localhost:8081"

    def test_custom_chat_template_kwargs(self) -> None:
        c = LocalLLMClient(
            model_key="x",
            base_url="http://localhost:8081",
            chat_template_kwargs={"enable_thinking": True},
        )
        assert c._chat_template_kwargs == {"enable_thinking": True}

    def test_empty_chat_template_kwargs(self) -> None:
        c = LocalLLMClient(
            model_key="x",
            base_url="http://localhost:8081",
            chat_template_kwargs={},
        )
        assert c._chat_template_kwargs == {}

    def test_thinking_off_in_payload(self) -> None:
        """thinking OFF가 실제 payload에 포함되는지."""
        with patch("core.llm.local_client.requests.post") as mock_post:
            mock_post.return_value = _mock_ok()
            c = LocalLLMClient(model_key="t", base_url="http://x")
            c.generate(Prompt(system="s", user="u"))
            payload = mock_post.call_args.kwargs["json"]
            assert payload["chat_template_kwargs"] == {"enable_thinking": False}


class TestLocalLLMClientGenerate:
    @patch("core.llm.local_client.requests.post")
    def test_success(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="test", base_url="http://localhost:8081")
        r = c.generate(Prompt(system="셰인.", user="안녕"))

        assert r.text == "안녕하세요. 셰인입니다."
        assert r.model == "test"
        assert r.cost_usd == 0.0
        assert r.input_tokens == 50
        assert r.output_tokens == 30
        assert r.latency_ms >= 0

    @patch("core.llm.local_client.requests.post")
    def test_system_prompt_included(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="t", base_url="http://x")
        c.generate(Prompt(system="시스템", user="유저"))
        payload = mock_post.call_args.kwargs["json"]
        messages = payload["messages"]
        assert messages[0] == {"role": "system", "content": "시스템"}
        assert messages[1] == {"role": "user", "content": "유저"}

    @patch("core.llm.local_client.requests.post")
    def test_empty_system_not_included(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="t", base_url="http://x")
        c.generate(Prompt(system="", user="유저"))
        payload = mock_post.call_args.kwargs["json"]
        assert payload["messages"][0]["role"] == "user"
        assert len(payload["messages"]) == 1

    @patch("core.llm.local_client.requests.post")
    def test_kwargs_forwarded(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="t", base_url="http://x")
        c.generate(Prompt(system="", user="u"), max_tokens=99, temperature=0.1)
        payload = mock_post.call_args.kwargs["json"]
        assert payload["max_tokens"] == 99
        assert payload["temperature"] == 0.1

    @patch("core.llm.local_client.requests.post")
    def test_http_error(self, mock_post: MagicMock) -> None:
        resp = MagicMock()
        resp.status_code = 500
        resp.text = "Internal Server Error"
        mock_post.return_value = resp
        c = LocalLLMClient(model_key="test", base_url="http://x")
        with pytest.raises(LLMError, match="500"):
            c.generate(Prompt(system="", user="hi"))

    @patch("core.llm.local_client.requests.post")
    def test_request_exception(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.RequestException("Connection refused")
        c = LocalLLMClient(model_key="test", base_url="http://x")
        with pytest.raises(LLMError, match="Local LLM request failed"):
            c.generate(Prompt(system="", user="hi"))

    @patch("core.llm.local_client.requests.post")
    def test_unexpected_response_format(self, mock_post: MagicMock) -> None:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"unexpected": "format"}
        mock_post.return_value = resp
        c = LocalLLMClient(model_key="test", base_url="http://x")
        with pytest.raises(LLMError, match="Unexpected response format"):
            c.generate(Prompt(system="", user="hi"))

    @patch("core.llm.local_client.requests.post")
    def test_cost_always_zero(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="t", base_url="http://x")
        r = c.generate(Prompt(system="", user="u"))
        assert r.cost_usd == 0.0

    @patch("core.llm.local_client.requests.post")
    def test_raw_contains_base_url(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _mock_ok()
        c = LocalLLMClient(model_key="t", base_url="http://localhost:8081")
        r = c.generate(Prompt(system="", user="u"))
        assert r.raw["base_url"] == "http://localhost:8081"


class TestLocalLLMClientGenerateJSON:
    """Phase A.3-b — generate_json + response_format json_schema 강제."""

    _SCHEMA = {
        "properties": {
            "score": {"type": "number"},
            "verdict": {"type": "string"},
        },
        "required": ["score", "verdict"],
    }

    @patch("core.llm.local_client.requests.post")
    def test_supports_schema_injects_response_format(
        self, mock_post: MagicMock
    ) -> None:
        """supports_json_schema=True 시 response_format 자동 주입."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [
                {"message": {"content": '{"score": 92, "verdict": "pass"}'}}
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        }
        mock_post.return_value = resp
        c = LocalLLMClient(
            model_key="t",
            base_url="http://x",
            supports_json_schema=True,
        )
        result = c.generate_json(Prompt(system="", user="u"), schema=self._SCHEMA)

        payload = mock_post.call_args.kwargs["json"]
        rf = payload["response_format"]
        assert rf["type"] == "json_schema"
        assert rf["json_schema"]["strict"] is True
        wrapped = rf["json_schema"]["schema"]
        assert wrapped["type"] == "object"
        assert wrapped["additionalProperties"] is False
        assert wrapped["required"] == ["score", "verdict"]

        assert result.parsed == {"score": 92, "verdict": "pass"}
        assert result.model == "t"

    @patch("core.llm.local_client.requests.post")
    def test_without_supports_schema_falls_back(
        self, mock_post: MagicMock
    ) -> None:
        """supports_json_schema=False 면 response_format 미주입 + post-hoc parse."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [
                {"message": {"content": '{"score": 78, "verdict": "warn"}'}}
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8},
        }
        mock_post.return_value = resp
        c = LocalLLMClient(model_key="fallback", base_url="http://x")
        result = c.generate_json(
            Prompt(system="", user="u"), schema=self._SCHEMA
        )
        payload = mock_post.call_args.kwargs["json"]
        assert "response_format" not in payload
        assert result.parsed == {"score": 78, "verdict": "warn"}

    @patch("core.llm.local_client.requests.post")
    def test_schema_none_falls_back(self, mock_post: MagicMock) -> None:
        """schema=None 이면 supports flag 와 무관하게 fallback."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [
                {"message": {"content": '{"k": 1}'}}
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3},
        }
        mock_post.return_value = resp
        c = LocalLLMClient(
            model_key="t",
            base_url="http://x",
            supports_json_schema=True,
        )
        c.generate_json(Prompt(system="", user="u"), schema=None)
        payload = mock_post.call_args.kwargs["json"]
        assert "response_format" not in payload

    @patch("core.llm.local_client.requests.post")
    def test_preserves_explicit_additional_properties(
        self, mock_post: MagicMock
    ) -> None:
        """입력 schema 가 type=object + additionalProperties 명시 시 원본 유지."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": "{}"}}],
            "usage": {},
        }
        mock_post.return_value = resp
        c = LocalLLMClient(
            model_key="t",
            base_url="http://x",
            supports_json_schema=True,
        )
        explicit_schema = {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
            "required": ["x"],
            "additionalProperties": True,
        }
        c.generate_json(Prompt(system="", user="u"), schema=explicit_schema)
        wrapped = mock_post.call_args.kwargs["json"]["response_format"][
            "json_schema"
        ]["schema"]
        assert wrapped["additionalProperties"] is True

    @patch("core.llm.local_client.requests.post")
    def test_empty_content_under_schema_raises(
        self, mock_post: MagicMock
    ) -> None:
        """SGLang 가 reasoning_content 만 채우고 content=null 인 케이스 explicit 에러."""
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": None}}],
            "usage": {},
        }
        mock_post.return_value = resp
        c = LocalLLMClient(
            model_key="t",
            base_url="http://x",
            supports_json_schema=True,
        )
        with pytest.raises(LLMError, match="Empty content"):
            c.generate_json(Prompt(system="", user="u"), schema=self._SCHEMA)


class TestFactoryFunctions:
    def test_get_qwen36_27b_q3(self) -> None:
        c = get_qwen36_27b_q3()
        assert c.model_name == "qwen36-27b-q3"
        assert "8081" in c._base_url
        assert c._chat_template_kwargs == {"enable_thinking": False}
        assert c._supports_json_schema is True

    def test_get_qwen35_9b_q3_no_schema_support(self) -> None:
        c = get_qwen35_9b_q3()
        assert c._supports_json_schema is False

    def test_get_qwen36_27b_q2(self) -> None:
        c = get_qwen36_27b_q2()
        assert c.model_name == "qwen36-27b-q2"
        assert "8082" in c._base_url
        assert c._chat_template_kwargs == {"enable_thinking": False}

    def test_get_qwen35_9b_q3(self) -> None:
        c = get_qwen35_9b_q3()
        assert c.model_name == "qwen35-9b-q3"
        assert "8083" in c._base_url
        assert c._chat_template_kwargs == {"enable_thinking": False}

    def test_get_default_npc_is_9b(self) -> None:
        c = get_default_npc()
        assert c.model_name == "qwen35-9b-q3"
        assert "8083" in c._base_url

    def test_get_default_gm_is_q2(self) -> None:
        c = get_default_gm()
        assert c.model_name == "qwen36-27b-q2"
        assert "8082" in c._base_url
