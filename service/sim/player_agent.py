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

## 응답 규칙 (★ 절대 준수)
- 응답은 반드시 JSON 1개만. 설명/주석/코드블록 X.
- JSON 형식: {"action_type": "...", "target": "...", "rationale": "..."}
- rationale은 한국어 1-2문장 짧게.

## 1층 진행 단계 (★ 어둠 미궁 본질)

**1단계: 빛 확보 (★ 가시거리 10m → 50m+)**
- 현재 has_active_light=false 면 ACTIVATE_LIGHT 우선
- target: "횃불" 또는 "정령 등불" (★ 종족 한정)
- 빛 X면 약탈자/몬스터 인지 X = 매우 위험

**2단계: 탐색 + 이동 (★ sub_areas)**
- 빛 확보 후 EXPLORE → 정수/몬스터/통로 발견
- MOVE → 인접 sub_area 이동 (★ accessible_from)
- target: sub_area 이름 (예: "북쪽 통로", "비석 공동")

**3단계: 정수 / 마석 / 자원 수집**
- ABSORB_ESSENCE: 떠다니는 정수 흡수 (★ 30분 자연 소멸)
- 정수 흡수 = 능력 강화 (★ 13/14화 본문)
- target: 정수 이름 (예: "고블린 정수")

**4단계: 전투 / 도주 결정**
- ATTACK: 약한 몬스터 (★ 9등급)
- FLEE: 강한 적 / HP 낮을 때
- target: 몬스터 이름

**5단계: 휴식 (★ HP 회복)**
- REST: 4시간 교대 (★ 27화 본문)
- 빛 자원 OFF 후 휴식 권장

**6단계: 균열 진입 (★ 1층 탈출 / 보상)**
- OFFER_TO_STONE: 비석 공물 (★ 마석 → 의도적 균열, 374화)
- ENTER_RIFT: 균열 포탈 진입
- EXIT_RIFT: 균열 탈출
- target: 균열 이름 (예: "green_mine") 또는 마석 등급

## action_type 가능 값 (13 종류 — 다양 사용 본격)

| action_type | 사용 시점 | target |
|---|---|---|
| activate_light | 빛 X 진입 시 우선 | "횃불"/"정령 등불" |
| move | sub_area 이동 | sub_area 이름 |
| explore | 빛 확보 후 정탐 | null |
| attack | 약한 몬스터 발견 | 몬스터 이름 |
| absorb_essence | 정수 떠다님 | 정수 이름 |
| use_item | 아이템 사용 | 아이템 이름 |
| offer_to_stone | 균열 진입 직전 | 마석 등급 |
| enter_rift | 균열 발견 | 균열 이름 |
| exit_rift | 균열 안에서 | 균열 이름 |
| rest | HP/MP 낮을 때 | null |
| wait | 시간 흘려야 할 때 | null |
| communicate | 파티원 소식 | 받는 자 |
| flee | 강한 적 만남 | 위협 이름 |

## 절대 금지 (★ 본 prompt 본격)
- ❌ **빛 활성: O 인데 ACTIVATE_LIGHT 출력 X** (★ 이미 빛 켜짐, 다음 단계 진행)
- ❌ 같은 action_type 3회 연속 반복 X (★ 다양 사용 본격)
- ❌ EXPLORE만 반복 (★ 1층 진행 X)
- ❌ MOVE만 반복 (★ 빛 X면 위험)
- ❌ rationale 영어 (★ 한국어만)
- ❌ JSON 외 출력 (★ 설명 X / 코드블록 X)

## 단계 결정 알고리즘 (★ 직접 적용)

```
if 빛 활성 == X and 미궁 시간 == 0:
    → activate_light, target="횃불"
elif HP < 30%:
    → rest
elif 정수 슬롯 < 3 and 미궁 시간 > 5:
    → explore (★ 정수 발견) or move (★ 새 영역) or absorb_essence (★ 발견 시)
elif 자원 충분 (정수 5+):
    → offer_to_stone or enter_rift (★ 1층 탈출)
else:
    → explore / move / attack / communicate / wait 중 1개 (★ 단계별 다양)
```

## 작품 본질
- 미궁 시간 한도: 168시간 (★ 7일)
- HP 0 = 영구사망 (★ 부활 X)
- 어둠 기본 (★ 가시거리 10m)
- 빛 활성 시 몬스터 등장 위험도 ↑
- 정수 흡수: 살이 닿으면 자동, 30분 자연 소멸
- 약탈자 (★ 수정 연합) 위험

## few-shot 예시

### 예시 1 (★ 진입 직후)
상황: 비요른, HP 150, has_active_light=false, hours_in_dungeon=0
출력:
{"action_type": "activate_light", "target": "횃불",
 "rationale": "어둠 속 가시거리 10m. 횃불 활성으로 시야 확보 우선."}

### 예시 2 (★ 정수 발견)
상황: 에르웬, HP 90, 정수 슬롯 0/9, 떠다니는 청록색 정수 발견
출력:
{"action_type": "absorb_essence", "target": "청록색 정수",
 "rationale": "30분 안 자연 소멸. 살이 닿아 자동 흡수."}

### 예시 3 (★ HP 낮음)
상황: 비요른, HP 40/150, 미궁 시간 12h, has_active_light=true
출력:
{"action_type": "rest", "target": null,
 "rationale": "HP 27% 낮음. 4시간 휴식으로 회복 필요."}
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
    """게임 컨텍스트 → user prompt (★ 본 commit 본격 보강).

    - 진행 상태 명확 (★ HP / 빛 / 정수 / 시간)
    - 추천 다음 행동 힌트 (★ rule-based 5종)
    - 13 ActionType 다양 유도
    """
    chars = ctx.get("v2_characters") or {}
    actor = chars.get(actor_name) or {}
    world = ctx.get("v2_world_state") or {}
    location = ctx.get("v2_initial_location") or {}
    floor_def = ctx.get("v2_floor_definition") or {}

    hp = actor.get("hp", 0)
    hp_max = actor.get("hp_max", 1)
    hp_pct = (hp / hp_max * 100) if hp_max > 0 else 0
    has_light = bool(actor.get("has_active_light", False))
    essence_slots = int(actor.get("essence_slots_used", 0))
    hours = int(world.get("hours_in_dungeon", 0))

    # ─── 추천 다음 행동 힌트 (★ rule-based) ───
    hints: list[str] = []
    if not has_light and hours == 0:
        hints.append("⚠️ 빛 자원 X — ACTIVATE_LIGHT 우선 권장")
    if hp_pct < 30:
        hints.append("⚠️ HP 30% 미만 — REST 권장")
    if has_light and location.get("sub_area") == "진입점":
        hints.append(
            "💡 진입점 정체 — MOVE 권장 (★ 북쪽 통로 / 남쪽 통로)"
        )
    if essence_slots < 3 and hours > 5:
        hints.append("💡 정수 슬롯 빔 — EXPLORE/ABSORB_ESSENCE 권장")
    if hours > 24 and essence_slots >= 5:
        hints.append("💡 자원 충분 — OFFER_TO_STONE/ENTER_RIFT 권장 (★ 1층 탈출)")
    if hours > 100:
        hints.append("⚠️ 168h 한도 임박 — 균열 진입 우선")

    # ★ C commit: encounter type별 힌트 (★ GM이 spawn한 결과 인식)
    encounters = ctx.get("active_encounters") or []
    for e in encounters:
        etype = e.get("type", "")
        ename = e.get("name", "?")
        if etype == "essence":
            hints.append(
                f"💎 정수 발견 ({ename}) — ABSORB_ESSENCE 우선 (30분 자연 소멸)"
            )
        elif etype == "monster":
            hints.append(f"⚔️ 몬스터 발견 ({ename}) — ATTACK 또는 FLEE")
        elif etype == "rift":
            hints.append(
                f"🌀 균열 발견 ({ename}) — ENTER_RIFT 또는 OFFER_TO_STONE"
            )
        elif etype == "item":
            hints.append(f"🎁 아이템 발견 ({ename}) — USE_ITEM 검토")
        elif etype == "event":
            hints.append(f"⚠️ 이벤트 ({ename}) — 상황 평가 후 결정")

    hint_text = "\n".join(hints) if hints else "(★ 진행 단계 자유 결정)"

    lines = [
        "## 현재 상황",
        "",
        f"**플레이어**: {actor_name} ({actor.get('race', '?')})",
        f"- HP: {hp}/{hp_max} ({hp_pct:.0f}%)",
        f"- 빛 활성: {'O' if has_light else 'X'}",
        f"- 정수 슬롯 사용: {essence_slots}",
        "",
        f"**위치**: {location.get('realm', '?')} "
        f"{location.get('floor', '?')}층 {location.get('sub_area', '?')}",
        f"- 가시거리: {location.get('visibility_meters', 10)}m",
        f"- 빛 자원 있음: {'O' if location.get('has_light', False) else 'X'}",
        "",
        f"**미궁 시간**: {hours}h / 168h",
    ]
    if active_rifts := world.get("active_rifts"):
        lines.append(f"**활성 균열**: {', '.join(active_rifts)}")
    if party_members := world.get("party_members"):
        lines.append(f"**파티**: {', '.join(party_members)}")

    if sub_areas := floor_def.get("sub_areas"):
        lines.append("")
        lines.append("**Sub Areas (★ 1층)**")
        for sa in sub_areas[:6]:
            lines.append(f"- {sa['name']}: {sa.get('description', '')[:50]}")

    # ★ C commit: GM이 spawn한 active encounters 본격 출력
    if encounters:
        lines.append("")
        lines.append("**현재 encounter (★ GM 출력)**")
        for e in encounters:
            etype = e.get("type", "?")
            ename = e.get("name", "?")
            eloc = e.get("location", "?")
            edesc = e.get("description", "")
            lines.append(f"- [{etype}] {ename} @ {eloc}")
            if edesc:
                lines.append(f"  설명: {edesc}")

    lines.extend(
        [
            "",
            "## 추천 힌트",
            hint_text,
            "",
            "## 출력 (★ JSON 1개만)",
        ]
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
