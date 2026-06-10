"""GM LLM 내러티브 — 누적 맥락 narrative 생성 검증 (mock 27B)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from service.sim.gm_narrator import (
    GM_NARRATE_ACTIONS,
    _gm_client,
    _gm_temperature,
    compose_gm_narrative,
    gm_model_label,
)
from service.sim.types import PlayerActionType


def test_gm_narrate_actions_scope() -> None:
    # 서사형(탐색/대화/대기) + 전투(5단계 확대)는 GM 서사, 수치/상점은 handler 유지
    assert PlayerActionType.EXPLORE in GM_NARRATE_ACTIONS
    assert PlayerActionType.DIALOGUE in GM_NARRATE_ACTIONS
    assert PlayerActionType.WAIT in GM_NARRATE_ACTIONS
    # ★ 5단계 — 전투도 GM 주도 (수치는 handle_attack, 서사는 GM)
    assert PlayerActionType.ATTACK in GM_NARRATE_ACTIONS
    assert PlayerActionType.FLEE in GM_NARRATE_ACTIONS
    # 상점/장착 등 순수 수치 action은 GM 비대상
    assert PlayerActionType.SHOP_BUY not in GM_NARRATE_ACTIONS


def _fake_client(narrative: str) -> MagicMock:
    fake = MagicMock()
    fake.generate_json.return_value = MagicMock(parsed={"narrative": narrative})
    return fake


def test_compose_returns_llm_narrative() -> None:
    fake = _fake_client("나는 부족 성지를 천천히 둘러보았다. 횃불이 흔들렸다.")
    with patch("service.sim.gm_narrator.get_gemma4_12b", return_value=fake):
        out = compose_gm_narrative(
            "주변을 둘러본다", "특별한 변화 없음", "부족 성지",
            "부족장", [("이전 행동", "이전 결과")],
        )
    assert "부족 성지" in out


def test_compose_empty_on_too_short() -> None:
    fake = _fake_client("짧다")
    with patch("service.sim.gm_narrator.get_gemma4_12b", return_value=fake):
        out = compose_gm_narrative("x", "f", "l", "s", [])
    assert out == ""


def test_compose_empty_on_exception() -> None:
    with patch(
        "service.sim.gm_narrator.get_gemma4_12b", side_effect=RuntimeError("down")
    ):
        out = compose_gm_narrative("x", "f", "l", "s", [])
    assert out == ""


def test_history_passed_to_prompt() -> None:
    captured: dict[str, str] = {}

    def gen(prompt: object, **_: object) -> MagicMock:
        captured["user"] = getattr(prompt, "user", "")
        return MagicMock(parsed={"narrative": "충분히 긴 GM narrative 결과 문장이다."})

    fake = MagicMock()
    fake.generate_json.side_effect = gen
    with patch("service.sim.gm_narrator.get_gemma4_12b", return_value=fake):
        compose_gm_narrative(
            "행동", "확정사실", "위치", "주변", [("과거행동", "과거결과")],
        )
    # 누적 히스토리가 프롬프트에 포함 (맥락 인지)
    assert "과거행동" in captured["user"]
    assert "확정사실" in captured["user"]


def test_routing_pivotal_gemma_default(monkeypatch: pytest.MonkeyPatch) -> None:
    # 기본(GEMMA_GM 미설정): pivotal → Gemma(8085), 단순 → Qwen3.5-4B Q8(8088)
    monkeypatch.delenv("GEMMA_GM", raising=False)
    assert gm_model_label(True) == "gemma"
    assert gm_model_label(False) == "4b"
    assert "8085" in _gm_client(True)._base_url
    assert "8088" in _gm_client(False)._base_url


def test_routing_pivotal_27b_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    # GEMMA_GM=0 폴백: pivotal → 27B(8081)
    monkeypatch.setenv("GEMMA_GM", "0")
    assert gm_model_label(True) == "27b"
    assert "8081" in _gm_client(True)._base_url
    # 단순 경로는 토글 무관 빠른 tier(4B Q8) 유지
    assert gm_model_label(False) == "4b"


def test_gm_temperature_per_model(monkeypatch: pytest.MonkeyPatch) -> None:
    # Gemma pivotal = 공식 권장 1.0(변주↑), 27B 폴백/단순 9B = 0.8
    monkeypatch.delenv("GEMMA_GM", raising=False)
    assert _gm_temperature(True) == 1.0  # Gemma
    assert _gm_temperature(False) == 0.8  # 9B
    monkeypatch.setenv("GEMMA_GM", "0")
    assert _gm_temperature(True) == 0.8  # 27B 폴백
