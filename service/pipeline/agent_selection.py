"""Agent Selection (★ 자료 2.2 Stage 5-6).

Tier별 게임 LLM 선택:
  - Tier 1: 로컬 모델 우선 (qwen35-9b-q3 / qwen36-27b-q2)
  - Tier 2+: API 모델 옵션 (미래)

cost_preference:
  - cheap: 가장 저렴 (9b-q3)
  - balanced: 중간 (27b-q2)
  - premium: 큰 모델
"""

from dataclasses import dataclass
from typing import Literal

TIER_CANDIDATES: dict[str, list[str]] = {
    "tier_1": [
        "qwen35-9b-q3",
        "qwen36-27b-q2",
    ],
    "tier_2": [
        "qwen35-9b-q3",
        "qwen36-27b-q2",
        # "claude_haiku_3_5",  # API (Tier 2+ 추가)
    ],
}


@dataclass
class AgentSelection:
    """Agent 선택 결과."""

    game_llm_key: str
    verify_llm_key: str
    tier: str
    cost_preference: str
    reasoning: str = ""


def select_game_llm(
    tier: str = "tier_1",
    cost_preference: Literal["cheap", "balanced", "premium"] = "cheap",
) -> str:
    """Game LLM 선택 (★ 자료 Stage 5)."""
    candidates = TIER_CANDIDATES.get(tier, TIER_CANDIDATES["tier_1"])

    if not candidates:
        raise ValueError(f"No candidates for tier '{tier}'")

    if cost_preference == "cheap":
        return candidates[0]
    elif cost_preference == "premium":
        return candidates[-1]
    else:
        return candidates[len(candidates) // 2]


def select_verify_llm(
    game_llm_key: str,
    tier: str = "tier_1",
) -> str:
    """Verify LLM 선택 (★ Cross-Model 강제, 자료 Stage 6).

    game_llm 과 다른 모델 선택. 미등록 tier는 폴백 없음.
    """
    candidates = TIER_CANDIDATES.get(tier, [])
    available = [m for m in candidates if m != game_llm_key]

    if not available:
        raise ValueError(
            f"No verify LLM available (game={game_llm_key}, tier={tier})"
        )

    return available[0]


def select_agents(
    tier: str = "tier_1",
    cost_preference: Literal["cheap", "balanced", "premium"] = "cheap",
) -> AgentSelection:
    """Agent 페어 선택 (자료 Stage 5+6 통합)."""
    game_llm = select_game_llm(tier, cost_preference)
    verify_llm = select_verify_llm(game_llm, tier)

    return AgentSelection(
        game_llm_key=game_llm,
        verify_llm_key=verify_llm,
        tier=tier,
        cost_preference=cost_preference,
        reasoning=(
            f"Tier {tier}: game={game_llm} ({cost_preference}), "
            f"verify={verify_llm} (Cross-Model)"
        ),
    )
