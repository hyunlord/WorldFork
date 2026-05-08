"""PlayerAgent — 자동 player LLM (★ 9B Q3 권장).

본인 본질:
- structured output (JSON action)
- 게임 컨텍스트 본 → 행동 결정
- 비용 ↓ (★ 9B Q3)

1차 commit: MockPlayerAgent schema 본격 (★ 단위 테스트 caller)
2차 commit (★ 본 commit): 진짜 LLM PlayerAgent class + JSON parsing
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from core.llm.client import LLMClient, Prompt

from .types import PlayerAction, PlayerActionType


@dataclass
class PlayerAgentResponse:
    """PlayerAgent 응답 (★ 1차 commit 호환)."""

    action: PlayerAction
    raw_text: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


class MockPlayerAgent:
    """Mock PlayerAgent (★ 1차 commit, 단위 테스트 caller)."""

    def __init__(self, mock_actions: list[PlayerAction] | None = None) -> None:
        self._actions = mock_actions or [
            PlayerAction(
                action_type=PlayerActionType.WAIT,
                actor_name="비요른",
                rationale="기본 mock action",
            ),
        ]
        self._call_count = 0

    def generate_action(
        self,
        actor_name: str,
        game_context: dict[str, Any],
    ) -> PlayerAgentResponse:
        action = self._actions[self._call_count % len(self._actions)]
        action_with_actor = PlayerAction(
            action_type=action.action_type,
            actor_name=actor_name,
            target=action.target,
            rationale=action.rationale,
        )
        self._call_count += 1
        return PlayerAgentResponse(
            action=action_with_actor,
            raw_text=f"mock action {action.action_type.value}",
            cost_usd=0.0,
            latency_ms=10,
        )


# ─── 진짜 LLM PlayerAgent (★ 2차 commit) ───

PLAYER_AGENT_SYSTEM_PROMPT = """당신은 RPG 게임 플레이어입니다.
주어진 게임 상황을 보고 다음 행동을 결정해야 합니다.

응답 규칙 (★ 절대 준수):
- 응답은 반드시 JSON 1개만. 설명/주석/코드블록 X.
- JSON 형식: {"action_type": "...", "target": "...", "rationale": "..."}

action_type 가능 값 (13 종류):
- "activate_light": 빛 자원 활성 (target = 빛 자원 이름, 예: "횃불")
- "move": 이동 (target = sub_area 이름)
- "explore": 탐색
- "attack": 전투 (target = 몬스터 이름)
- "absorb_essence": 정수 흡수 (target = 정수 이름)
- "use_item": 아이템 사용 (target = 아이템 이름)
- "offer_to_stone": 비석 공물 (★ 균열 진입, target = 마석 등급)
- "enter_rift": 균열 포탈 진입 (target = 균열 이름)
- "exit_rift": 균열 탈출
- "rest": 휴식 (★ 4시간)
- "wait": 시간 흐름
- "communicate": 메시지 스톤 통신 (target = 받는 자)
- "flee": 도주

작품 본질 (★ 1층):
- 어둠 기본 (★ 가시거리 10m)
- 빛 활성 시 몬스터 등장 위험
- 정수는 살이 닿으면 자동 흡수, 30분 자연 소멸
- 약탈자 (★ 수정 연합) 위험
- 168시간 한도

target은 상황에 맞는 값 (예: "북쪽 통로", "고블린", "횃불"). target 없는 경우 null.
rationale은 짧게 (★ 1-2문장).
"""


class PlayerAgent:
    """진짜 LLM PlayerAgent (★ 2차 commit).

    LLM 호출 → JSON parsing → PlayerAction 반환.
    본 commit은 1턴 호출 검증 (★ 50턴은 3차 commit).
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    def generate_action(
        self,
        actor_name: str,
        game_context: dict[str, Any],
    ) -> PlayerAgentResponse:
        """LLM 호출 → action 생성.

        Args:
            actor_name: 누구의 행동인지 (★ "비요른" / "에르웬")
            game_context: 게임 상황 dict (★ HP/위치/빛/시간 등)

        Returns:
            PlayerAgentResponse (★ JSON parsing 실패 시 기본 WAIT fallback)
        """
        user_text = _build_player_prompt(actor_name, game_context)

        prompt = Prompt(
            system=PLAYER_AGENT_SYSTEM_PROMPT,
            user=user_text,
        )

        response = self.llm_client.generate(prompt, max_tokens=300)

        action = _parse_action_json(response.text, actor_name)

        return PlayerAgentResponse(
            action=action,
            raw_text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )


def _build_player_prompt(actor_name: str, ctx: dict[str, Any]) -> str:
    """게임 컨텍스트 → user prompt (★ 캐릭터/위치/진행/sub_areas)."""
    lines = [f"[캐릭터] {actor_name}"]

    if v2_chars := ctx.get("v2_characters"):
        if char := v2_chars.get(actor_name):
            lines.append(f"종족: {char.get('race', '?')}")
            lines.append(
                f"HP: {char.get('hp', '?')}/{char.get('hp_max', '?')}"
            )
            lines.append(
                f"메인: 육체 {char.get('physical', '?')} "
                f"정신 {char.get('mental', '?')} "
                f"이능 {char.get('special', '?')}"
            )
            lines.append(
                f"근력 {char.get('strength', '?')} "
                f"민첩 {char.get('agility', '?')}"
            )

    if loc := ctx.get("v2_initial_location"):
        lines.append(
            f"\n[위치] {loc.get('realm', '?')} "
            f"{loc.get('floor', '')}층 {loc.get('sub_area', '')}"
        )
        lines.append(f"가시거리: {loc.get('visibility_meters', '?')}m")
        lines.append(
            f"빛: {'활성' if loc.get('has_light') else '비활성 (★ 어둠)'}"
        )

    if ws := ctx.get("v2_world_state"):
        lines.append(
            f"\n[진행] 미궁 시간 {ws.get('hours_in_dungeon', 0)}h / 168h"
        )
        if ws.get("is_dark_zone"):
            lines.append("★ 어둠 영역")
        if rifts := ws.get("active_rifts"):
            lines.append(f"활성 균열: {', '.join(rifts)}")

    if fd := ctx.get("v2_floor_definition"):
        if sub_areas := fd.get("sub_areas"):
            lines.append("\n[Sub Areas]")
            for sa in sub_areas[:6]:
                lines.append(
                    f"- {sa['name']}: {sa.get('description', '')[:50]}"
                )

    lines.append(
        f"\n위 상황에서 {actor_name}의 다음 행동을 JSON 1개로 답하시오."
    )
    return "\n".join(lines)


def _parse_action_json(raw_text: str, actor_name: str) -> PlayerAction:
    """LLM 응답 JSON parsing — 안전 fallback (★ 실패 시 WAIT)."""
    text = raw_text.strip()

    # ```json ... ``` 코드블록 우선 추출
    code_block_match = re.search(
        r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL
    )
    if code_block_match:
        text = code_block_match.group(1)
    else:
        # 텍스트 안 첫 {...}
        json_match = re.search(r"\{[^{}]*\}", text)
        if json_match:
            text = json_match.group(0)

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return PlayerAction(
            action_type=PlayerActionType.WAIT,
            actor_name=actor_name,
            rationale=f"[parse_failed] {raw_text[:100]}",
        )

    action_type_str = parsed.get("action_type", "wait")
    try:
        action_type = PlayerActionType(action_type_str)
    except ValueError:
        action_type = PlayerActionType.WAIT

    return PlayerAction(
        action_type=action_type,
        actor_name=actor_name,
        target=parsed.get("target"),
        rationale=str(parsed.get("rationale", ""))[:200],
    )
