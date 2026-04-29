"""Mechanical Checker E2E 통합 테스트.

테스트 1 (fast): Mock LLM → IP 누출 강제 감지 + 콘솔 출력 검증
테스트 2 (slow): 실제 claude -p 호출 1턴 + Mechanical 검증

실행:
  pytest tests/integration/ -v -s               # 느린 테스트 제외
  pytest tests/integration/ -v -s -m slow       # 실제 LLM 테스트만
  pytest tests/integration/ -v -s -m "not slow" # 빠른 테스트만
"""

import time
from typing import Any

import pytest

from core.llm.client import LLMClient, LLMResponse, Prompt
from core.verify.mechanical import MechanicalChecker, build_check_context
from service.game.loop import build_gm_prompt, initialize_state, load_scenario

# ─── 공통 헬퍼 ────────────────────────────────────────────────


class MockLLMClient(LLMClient):
    """테스트용 고정 응답 클라이언트. 외부 호출 0회."""

    def __init__(self, response_text: str, model: str = "mock"):
        self._text = response_text
        self._model = model

    @property
    def model_name(self) -> str:
        return self._model

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text,
            model=self._model,
            cost_usd=0.0,
            latency_ms=1,
            input_tokens=0,
            output_tokens=0,
        )


def run_one_turn(
    user_action: str,
    client: LLMClient,
    scenario_id: str = "novice_dungeon_run",
) -> dict[str, Any]:
    """1턴 실행 + Mechanical 검증 (play_game() 없이 직접 호출).

    Returns:
        {response_text, mech_result, elapsed_ms, model_name}
    """
    scenario = load_scenario(scenario_id)
    state = initialize_state(scenario)
    prompt = build_gm_prompt(scenario, state, user_action)

    t0 = time.monotonic()
    response = client.generate(prompt)
    elapsed_ms = int((time.monotonic() - t0) * 1000)

    checker = MechanicalChecker()
    ctx = build_check_context(scenario)
    mech_result = checker.check(response.text, ctx)  # _passed_rules는 checker가 채움

    return {
        "response_text": response.text,
        "mech_result": mech_result,
        "elapsed_ms": elapsed_ms,
        "model_name": client.model_name,
        "cost_usd": response.cost_usd,
    }


def print_turn_report(label: str, result: dict[str, Any]) -> None:
    """턴 결과를 콘솔 게임 형식으로 출력."""
    mech = result["mech_result"]
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  모델: {result['model_name']} | {result['elapsed_ms']}ms")
    print()
    print("  [GM 응답]")
    for line in result["response_text"][:500].splitlines():
        print(f"  {line}")
    if len(result["response_text"]) > 500:
        print("  ...")
    print()
    print(f"  [{mech.summary_line()} | 비용: ${result['cost_usd']:.4f}]")
    if not mech.passed:
        for f in mech.failures:
            print(f"  ⚠️  {f.rule} ({f.severity}): {f.detail}")
            print(f"     → {f.suggestion}")
    print(f"{'=' * 60}")


# ─── 테스트 1: Mock LLM — IP 누출 강제 감지 ──────────────────


def test_mock_ip_leakage_detected() -> None:
    """Mock LLM이 IP 누출 응답 → ip_leakage critical 감지."""
    bad_response = (
        "비요른은 라프도니아 왕국의 바바리안이다. "
        "그는 던전 앤 스톤의 용사로서 오늘도 모험을 떠난다."
    )
    client = MockLLMClient(bad_response)
    result = run_one_turn("셰인에게 인사한다", client)

    print_turn_report("테스트 1: Mock IP 누출 감지", result)

    mech = result["mech_result"]
    assert not mech.passed, "IP 누출이 있으므로 passed=False여야 함"
    assert mech.score == 0.0, "critical 실패 → score 0"
    assert mech.critical_count() >= 1

    leaked_rules = [f.rule for f in mech.failures]
    assert "ip_leakage" in leaked_rules, f"ip_leakage 미감지: {leaked_rules}"


def test_mock_clean_response_passes() -> None:
    """Mock LLM 정상 응답 → 전체 룰 통과."""
    good_response = (
        '셰인이 환하게 웃으며 손을 마주 든다. '
        '"투르윈, 드디어 오셨군요. 길드 등록은 끝나셨나요?"\n'
        "그가 길드 사무실 쪽으로 손짓한다.\n\n"
        "다음 행동:\n- 사무실로 들어간다\n- 셰인에게 미궁에 대해 묻는다"
    )
    client = MockLLMClient(good_response)
    result = run_one_turn("셰인에게 인사한다", client)

    print_turn_report("테스트 2: Mock 정상 응답", result)

    mech = result["mech_result"]
    assert mech.passed, f"정상 응답이 실패: {[f.rule for f in mech.failures]}"
    assert mech.score == 100.0


# ─── 테스트 3: 실제 LLM 1턴 ──────────────────────────────────


@pytest.mark.slow
def test_one_turn_real_llm() -> None:
    """실제 claude -p 호출 1턴 + Mechanical 검증.

    -m slow 옵션으로만 실행.
    예상 시간: 14-33초
    """
    from core.llm.cli_client import get_default_game_gm

    client = get_default_game_gm()

    print(f"\n[실제 LLM 호출 시작 | 모델: {client.model_name}]")
    print("[예상 시간: 14-33초]")

    result = run_one_turn("셰인에게 다가가 인사한다", client)

    print_turn_report("테스트 3: 실제 LLM 1턴", result)

    mech = result["mech_result"]

    # 최소 검증: Mechanical이 실행됐고 응답이 있음
    assert len(result["response_text"]) > 10, "응답이 너무 짧음"
    assert result["elapsed_ms"] > 0
    assert mech.score >= 0.0
    assert mech.passed_rules() >= 0

    # 실제 LLM 응답이 기본 한국어 룰을 통과하기를 기대
    if not mech.passed:
        print("\n  [참고] 룰 위반 있음 — Day 4 재시도 로직에서 처리 예정")
