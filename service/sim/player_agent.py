"""PlayerAgent — 자동 player LLM (★ 9B Q3 권장).

본인 본질:
- structured output (JSON action)
- 게임 컨텍스트 본 → 행동 결정
- 비용 ↓ (★ 9B Q3)

1차 commit: MockPlayerAgent schema 본격 (★ 단위 테스트 caller)
2차 commit: 진짜 LLM PlayerAgent class + JSON parsing
A.5 commit (b8ee50b): encounter type별 hint + active encounters 출력
E commit (★ 본 commit, A.6 mirror): server-side ActionType enforcement
- prompt-only enforcement = LLM 본격 X 따른다 (★ A.6 4-way 입증)
- A.6가 GM에 적용한 패턴을 Player에 동일 본격 적용
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from core.llm.client import LLMClient, LLMResponse, Prompt

from .types import PlayerAction, PlayerActionType

log = logging.getLogger(__name__)


# ─── 본 commit 본격 본질 (★ A.6 mirror) ───

# 직전 ActionType 연속 검증 (★ Step A)
# (★ history 길이 N 모두 같음 → 새로 같은 action 시도하면 N+1 연속 → 위반)
MAX_CONSECUTIVE_SAME_ACTION = 3

# dominance 검증 (★ Step B)
ACTION_DOMINANCE_WINDOW = 8       # 직전 8턴
ACTION_DOMINANCE_THRESHOLD = 0.5  # 50%+ 시 dominance
ACTION_DOMINANCE_COUNT = 5        # 직전 8턴 중 같은 ActionType 5+

# retry 본격
MAX_PLAYER_RETRY_COUNT = 2

# tracking 본격 (★ 50턴 × 2 actor 본격)
LAST_ACTIONS_WINDOW = 15

# encounter type별 required ActionType (★ Step C)
ENCOUNTER_REQUIRED_ACTIONS: dict[str, tuple[str, ...]] = {
    "essence": ("absorb_essence",),
    "monster": ("attack", "flee", "use_item"),
    "rift": ("enter_rift", "offer_to_stone", "exit_rift"),
    "item": ("use_item",),
    "event": ("communicate", "wait", "explore"),
    # narrative는 자유
}

# fallback rule-based ActionType (★ Step D 안전)
FALLBACK_ACTIONS_BY_PRIORITY: tuple[str, ...] = (
    "absorb_essence",
    "attack",
    "explore",
    "move",
    "rest",
    "wait",
)

# parse failure marker (★ _parse_action_json 본격 호환)
PARSE_FAILED_MARKER = "[parse_failed]"


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


# ─── 진짜 LLM PlayerAgent (★ 2차 commit base + E commit enforcement) ───

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
- ★ 조건: floating essence 발견 + 슬롯 < 5
- ⚠️ 슬롯 5/5 FULL 시 ABSORB_ESSENCE 사용 금지 (★ can_absorb False → 호출 자체 X)
- → 슬롯 가득 시 OFFER_TO_STONE (비석 공물)로 슬롯 비우기 권장

**4단계: 전투 / 도주 결정**
- ATTACK: 약한 몬스터 (★ 9등급)
- FLEE: 강한 적 / HP 낮을 때
- target: 몬스터 이름

**5단계: 휴식 (★ HP 회복)**
- REST: 4시간 교대 (★ 27화 본문)
- 빛 자원 OFF 후 휴식 권장

**6단계: 균열 진입 (★ 1층 탈출 / 보상)**
- OFFER_TO_STONE: 비석 공물 (★ 마석 → 의도적 균열, 374화)
  ★ 본격 본질 (★ 균열 활성화 필수 mechanism):
    1. 비석 공동 위치 + 정수/마석 본격
    2. 공물 → world.active_rifts에 등록 → ENTER_RIFT 가능
  ★ 활성 균열 없을 때 RIFT encounter 발견 시 우선 호출
  - target: 균열 이름 (예: "핏빛성채")
- ENTER_RIFT: 균열 포탈 진입
  ★ 조건: world.active_rifts ≥ 1 (★ 활성 균열 존재) + location.realm != RIFT
  ⚠️ 활성 균열 없으면 사용 금지 (★ success=False)
  ⚠️ 이미 균열 안 (realm=RIFT) 본격 시 사용 금지 — EXIT_RIFT 또는 ATTACK
  → 활성 X 시: OFFER_TO_STONE 먼저
  - target: 활성 균열 이름 (예: "핏빛성채")
- EXIT_RIFT: 균열 탈출 → 1층 복귀
  ★ 조건: location.realm == RIFT (★ 균열 안 본격)
  ★ 시점 본격:
    1. 균열 클리어 후 (★ 보상 획득)
    2. 위험 본격 (HP 낮음 / 강적)
    3. 충분 본격 (★ 시간 1-2h 이상)
  ⚠️ 균열 밖 (realm=DUNGEON) 본격 시 사용 X
  - target: 현재 균열 이름 (★ location.rift_id)

**★ F8 균열 사이클 본격 순서**:
  1. OFFER_TO_STONE (★ 비석 공물) → world.active_rifts 등록
  2. ENTER_RIFT → 균열 안 진입 (realm = RIFT)
  3. ATTACK / EXPLORE / ABSORB 본격 (★ 균열 안 행동)
  4. EXIT_RIFT → 1층 복귀 (★ active_rifts에서 본격 제거됨)
  5. **다시 OFFER_TO_STONE → ENTER_RIFT** (★ active_rifts empty 본격 본격)

⚠️ EXIT_RIFT 직후 active_rifts empty 본격 — ENTER_RIFT 호출 X (★ success=False)
→ EXIT 후 반드시 OFFER_TO_STONE 먼저 (★ 새 균열 활성화)

## action_type 가능 값 (13 종류 — 다양 사용 본격)

| action_type | 사용 시점 | target |
|---|---|---|
| activate_light | 빛 X 진입 시 우선 | "횃불"/"정령 등불" |
| move | sub_area 이동 | sub_area 이름 |
| explore | 빛 확보 후 정탐 | null |
| attack | 약한 몬스터 발견 | 몬스터 이름 |
| absorb_essence | 정수 떠다님 | 정수 이름 |
| use_item | 아이템 사용 | 아이템 이름 |
| offer_to_stone | 균열 활성화 (★ EXIT 후 본격) | 균열 이름 (예: "핏빛성채") |
| enter_rift | 균열 발견 | 균열 이름 |
| exit_rift | 균열 안에서 | 균열 이름 |
| rest | HP/MP 낮을 때 | null |
| wait | 시간 흘려야 할 때 | null |
| communicate | 파티원 소식 | 받는 자 |
| flee | 강한 적 만남 | 위협 이름 |

## 🔥 본격 ActionType 다양 강제 (★ E commit server-side)

stochastic LLM은 익숙 ActionType만 도피하는 본질이 있다.
본 turn 본격 다양 강제 (★ A.6 GM mirror):

**encounter type별 required ActionType (★ 매핑 본격)**:
- ESSENCE encounter → ABSORB_ESSENCE
- MONSTER encounter → ATTACK / FLEE / USE_ITEM 中
- RIFT encounter → ENTER_RIFT / OFFER_TO_STONE / EXIT_RIFT 中
- ITEM encounter → USE_ITEM
- EVENT encounter → COMMUNICATE / WAIT / EXPLORE 中
- narrative-only → 자유

**직전 ActionType 인식**:
- 직전 3 연속 같은 ActionType → 본 turn 본격 다른 ActionType
- 50%+ dominance → 본 turn 본격 다른 ActionType
- ★ E commit: server가 응답 검증, 위반 시 재호출 + fallback

## 절대 금지 (★ 본 prompt 본격)
- ❌ **빛 활성: O 인데 ACTIVATE_LIGHT 출력 X** (★ 이미 빛 켜짐, 다음 단계 진행)
- ❌ 같은 action_type 3+ 연속 반복 X (★ E commit server-side)
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


# ─── 본격 helpers (★ A.6 mirror) ───


def _detect_dominant_actions(
    last_actions: list[str],
    window: int = ACTION_DOMINANCE_WINDOW,
    threshold: float = ACTION_DOMINANCE_THRESHOLD,
    consecutive: int = ACTION_DOMINANCE_COUNT,
) -> list[str]:
    """직전 window 안 dominance ActionType 검출 (★ A.6 mirror)."""
    if not last_actions:
        return []

    recent = last_actions[-window:]
    if len(recent) < 3:
        return []

    counter: Counter[str] = Counter(recent)
    total = len(recent)

    return [
        a for a, c in counter.items()
        if c / total >= threshold or c >= consecutive
    ]


def _is_consecutive_violation(
    last_actions: list[str],
    new_action: str,
    max_consecutive: int = MAX_CONSECUTIVE_SAME_ACTION,
) -> bool:
    """직전 max_consecutive 모두 same + new도 same → violation."""
    if len(last_actions) < max_consecutive:
        return False

    recent = last_actions[-max_consecutive:]
    return all(a == new_action for a in recent)


def _is_action_violation(
    new_action: str,
    last_actions: list[str],
    dominant_actions: list[str],
) -> tuple[bool, str]:
    """본 turn ActionType 위반? (★ A.6 mirror).

    Returns:
        (위반 여부, reason)
    """
    if _is_consecutive_violation(last_actions, new_action):
        return (
            True,
            f"{new_action} {MAX_CONSECUTIVE_SAME_ACTION}+ 연속",
        )

    if new_action in dominant_actions:
        return True, f"{new_action} dominance"

    return False, ""


def _build_forbidden_action_section(
    last_action: str | None,
    dominant_actions: list[str],
) -> str:
    """본 turn forbidden ActionType 섹션 (★ A.6 mirror)."""
    if not last_action and not dominant_actions:
        return "(★ 본 turn ActionType 자유 결정)"

    lines = ["**본 turn 절대 금지 ActionType**:"]
    if last_action:
        lines.append(
            f"- ❌ {last_action} (★ 직전 "
            f"{MAX_CONSECUTIVE_SAME_ACTION} 연속)"
        )
    for da in dominant_actions:
        if da != last_action:
            lines.append(f"- ❌ {da} (★ 직전 8턴 dominance)")

    lines.append("")
    lines.append("→ 본 turn은 위 ActionType 외 본격 선택")

    return "\n".join(lines)


def _build_required_action_section(
    encounters: list[dict[str, Any]],
) -> str:
    """본 turn required ActionType 섹션 (★ encounter 매핑 본격)."""
    if not encounters:
        return (
            "(★ encounter X — 자유 결정, EXPLORE / MOVE / REST 추천)"
        )

    lines = ["**본 turn 본격 required ActionType (encounter 매핑)**:"]
    matched = False
    for e in encounters:
        etype = str(e.get("type", ""))
        ename = e.get("name", "?")
        required = ENCOUNTER_REQUIRED_ACTIONS.get(etype, ())
        if required:
            req_text = " / ".join(req.upper() for req in required)
            lines.append(
                f"- {etype} ({ename}) → **{req_text} 본격 우선**"
            )
            matched = True

    if not matched:
        lines.append("(★ narrative encounter — 자유 결정)")

    return "\n".join(lines)


def _make_fallback_action(
    actor_name: str,
    encounters: list[dict[str, Any]],
    last_actions: list[str],
    dominant_actions: list[str],
) -> PlayerAction:
    """fallback rule-based ActionType (★ Step D 안전).

    1. encounter 본격 인식 → required ActionType (★ dominance 외)
    2. priority list (★ dominance / 직전 외)
    3. 최후 EXPLORE
    """
    forbidden = set(dominant_actions)
    last_action = last_actions[-1] if last_actions else None
    if last_action and _is_consecutive_violation(last_actions, last_action):
        forbidden.add(last_action)

    # 1) encounter 본격 인식
    for e in encounters or []:
        etype = str(e.get("type", ""))
        required = ENCOUNTER_REQUIRED_ACTIONS.get(etype, ())
        for req in required:
            if req not in forbidden:
                return PlayerAction(
                    action_type=PlayerActionType(req),
                    actor_name=actor_name,
                    target=str(e.get("name", "")) or None,
                    rationale=(
                        f"(★ E fallback) {etype} encounter required {req}"
                    ),
                )

    # 2) priority list 본격
    for action in FALLBACK_ACTIONS_BY_PRIORITY:
        if action not in forbidden:
            return PlayerAction(
                action_type=PlayerActionType(action),
                actor_name=actor_name,
                target=None,
                rationale=f"(★ E fallback) priority {action}",
            )

    # 3) 최후 EXPLORE
    return PlayerAction(
        action_type=PlayerActionType.EXPLORE,
        actor_name=actor_name,
        target=None,
        rationale="(★ E fallback) default explore",
    )


# ─── PlayerAgent v3 본격 (★ E, A.6 mirror) ───


class PlayerAgent:
    """진짜 LLM PlayerAgent — server-side enforcement 본격 (★ E).

    본 commit 본격 (★ A.6 mirror):
    1. LLM 호출 → ActionType 응답
    2. server-side rule check (★ 직전 / dominance)
    3. 위반 시 retry (★ MAX_PLAYER_RETRY_COUNT)
    4. retry 모두 실패 시 fallback rule-based ActionType
    5. enforcement_stats 본격 측정
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_retry: int = MAX_PLAYER_RETRY_COUNT,
    ) -> None:
        self.llm_client = llm_client
        self.max_retry = max_retry
        self._last_actions: list[str] = []
        # ★ E 본격: enforcement metrics (★ A.6 mirror)
        self._retry_count_total = 0
        self._fallback_count = 0

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    @property
    def enforcement_stats(self) -> dict[str, int]:
        """본 commit 본격 metrics (★ A.6 mirror)."""
        return {
            "retry_count": self._retry_count_total,
            "fallback_count": self._fallback_count,
        }

    def generate_action(
        self,
        actor_name: str,
        game_context: dict[str, Any],
    ) -> PlayerAgentResponse:
        """LLM 호출 + server-side enforcement (★ E 본격)."""
        # ★ Step B: dominance 검출
        dominant_actions = _detect_dominant_actions(self._last_actions)

        encounters_raw = game_context.get("active_encounters") or []
        encounters: list[dict[str, Any]] = [
            e for e in encounters_raw if isinstance(e, dict)
        ]

        last_response: LLMResponse | None = None
        last_violation = ""

        # ★ Step A: retry loop
        for attempt in range(self.max_retry + 1):
            user_text = _build_player_prompt(
                actor_name,
                game_context,
                last_actions=self._last_actions,
                dominant_actions=dominant_actions,
            )
            prompt = Prompt(
                system=PLAYER_AGENT_SYSTEM_PROMPT,
                user=user_text,
            )
            response = self.llm_client.generate(prompt, max_tokens=300)
            action = _parse_action_json(response.text, actor_name)

            # rule check
            violation, reason = _is_action_violation(
                new_action=action.action_type.value,
                last_actions=self._last_actions,
                dominant_actions=dominant_actions,
            )

            if not violation:
                # OK — tracking 갱신 + return
                self._last_actions.append(action.action_type.value)
                self._last_actions = self._last_actions[-LAST_ACTIONS_WINDOW:]

                return PlayerAgentResponse(
                    action=action,
                    raw_text=response.text,
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )

            # 위반 — retry (★ 실제 재호출 시에만 카운트)
            log.warning(
                "Player rule violation actor=%s attempt=%d reason=%s",
                actor_name,
                attempt + 1,
                reason,
            )
            if attempt < self.max_retry:
                self._retry_count_total += 1
            last_response = response
            last_violation = reason

        # ★ Step D: retry 모두 실패 → fallback rule-based
        log.warning(
            "Player enforcement fallback actor=%s violation=%s",
            actor_name,
            last_violation,
        )
        self._fallback_count += 1

        fallback = _make_fallback_action(
            actor_name=actor_name,
            encounters=encounters,
            last_actions=self._last_actions,
            dominant_actions=dominant_actions,
        )
        self._last_actions.append(fallback.action_type.value)
        self._last_actions = self._last_actions[-LAST_ACTIONS_WINDOW:]

        # 비용/지연 마지막 LLM 응답 누적 본격
        if last_response is not None:
            attempts = self.max_retry + 1
            return PlayerAgentResponse(
                action=fallback,
                raw_text=(
                    f"(★ E fallback after {attempts} attempts) "
                    f"{last_violation}"
                ),
                cost_usd=last_response.cost_usd * attempts,
                latency_ms=last_response.latency_ms * attempts,
            )
        return PlayerAgentResponse(
            action=fallback,
            raw_text="(★ E fallback)",
            cost_usd=0.0,
            latency_ms=0,
        )

    def reset_history(self) -> None:
        """시뮬 시작 시 호출 (★ A.6 mirror)."""
        self._last_actions = []
        self._retry_count_total = 0
        self._fallback_count = 0


def _format_slot_status(count: int, max_slots: int) -> str:
    """슬롯 상태 본격 명시 — LLM 인지 본격 (★ F5).

    - 5/5 → FULL 경고 + OFFER_TO_STONE 권장
    - 4/5 → 거의 가득
    - < 4 → N 추가 가능
    """
    if count >= max_slots:
        return (
            f"{count}/{max_slots} ⚠️ FULL "
            "(★ ABSORB_ESSENCE 사용 금지, OFFER_TO_STONE 권장)"
        )
    if count >= max_slots - 1:
        return f"{count}/{max_slots} (★ 거의 가득, 1 추가 가능)"
    return f"{count}/{max_slots} ({max_slots - count} 추가 가능)"


def _build_player_prompt(
    actor_name: str,
    ctx: dict[str, Any],
    *,
    last_actions: list[str] | None = None,
    dominant_actions: list[str] | None = None,
) -> str:
    """게임 컨텍스트 → user prompt (★ A.5 base + E commit 본격).

    - 진행 상태 명확 (★ HP / 빛 / 정수 / 시간)
    - 추천 다음 행동 힌트 (★ rule-based 5종)
    - encounter type별 hint (★ A.5)
    - 직전 ActionType / dominance / forbidden + required (★ E commit)
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
    essence_slot_max = int(actor.get("essence_slot_max", 5))
    slot_full = essence_slots >= essence_slot_max
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
    if slot_full:
        # ★ F5: slot 5/5 FULL → ABSORB 금지 + OFFER 권장
        hints.append(
            "⚠️ 정수 슬롯 FULL — ABSORB_ESSENCE 사용 금지, "
            "OFFER_TO_STONE 으로 슬롯 비우기 권장"
        )
    elif hours > 24 and essence_slots >= essence_slot_max - 1:
        hints.append(
            "💡 자원 충분 — OFFER_TO_STONE/ENTER_RIFT 권장 (★ 1층 탈출)"
        )
    if hours > 100:
        hints.append("⚠️ 168h 한도 임박 — 균열 진입 우선")

    # ★ A.5 commit: encounter type별 힌트
    encounters_raw = ctx.get("active_encounters") or []
    encounters: list[dict[str, Any]] = [
        e for e in encounters_raw if isinstance(e, dict)
    ]
    for e in encounters:
        etype = e.get("type", "")
        ename = e.get("name", "?")
        if etype == "essence":
            # ★ F5: slot FULL 시 ABSORB 금지 — OFFER 우회 권장
            if slot_full:
                hints.append(
                    f"💎 정수 발견 ({ename}) — 슬롯 FULL → "
                    "OFFER_TO_STONE 으로 슬롯 비운 후 재시도"
                )
            else:
                hints.append(
                    f"💎 정수 발견 ({ename}) — ABSORB_ESSENCE 우선 "
                    "(30분 자연 소멸)"
                )
        elif etype == "monster":
            hints.append(f"⚔️ 몬스터 발견 ({ename}) — ATTACK 또는 FLEE")
        elif etype == "rift":
            # ★ F6: active_rifts 없으면 OFFER_TO_STONE 먼저 본격 명시
            active_rifts_now = world.get("active_rifts") or []
            if ename in active_rifts_now:
                hints.append(
                    f"🌀 균열 발견 ({ename}) — 활성 본격, ENTER_RIFT 가능"
                )
            else:
                hints.append(
                    f"🌀 균열 발견 ({ename}) — 비활성, "
                    "OFFER_TO_STONE 먼저 (★ active_rifts 등록 후 ENTER)"
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
        f"- 정수 슬롯: {_format_slot_status(essence_slots, essence_slot_max)}",
        "",
        f"**위치**: {location.get('realm', '?')} "
        f"{location.get('floor', '?')}층 {location.get('sub_area', '?')}",
        f"- 가시거리: {location.get('visibility_meters', 10)}m",
        f"- 빛 자원 있음: {'O' if location.get('has_light', False) else 'X'}",
        "",
        f"**미궁 시간**: {hours}h / 168h",
    ]
    # ★ F6: active_rifts 본격 명시 — empty 본격 ENTER_RIFT 금지 경고
    active_rifts_raw = world.get("active_rifts") or []
    # ★ F7: 현재 균열 안 본격 (★ realm == RIFT) 본격 EXIT_RIFT 가이드
    realm_now = location.get("realm", "")
    in_rift = realm_now == "균열" or realm_now == "RIFT"
    rift_id_now = location.get("rift_id")
    # ★ F8: post-EXIT 본격 검출 (★ last 3 actions 본격 exit_rift)
    recent_exit = bool(
        last_actions and "exit_rift" in last_actions[-3:]
    )
    if in_rift:
        lines.append(
            f"**현재 균열 안 본격** 🌀 (rift_id={rift_id_now}) — "
            "EXIT_RIFT로 1층 복귀 가능 (★ ENTER_RIFT 재호출 X)"
        )
    if active_rifts_raw:
        lines.append(
            f"**활성 균열**: {', '.join(active_rifts_raw)} "
            f"(★ ENTER_RIFT 가능)" if not in_rift
            else f"**활성 균열**: {', '.join(active_rifts_raw)} "
                 f"(★ 이미 진입 본격 — EXIT_RIFT 우선)"
        )
    elif recent_exit:
        # ★ F8: 방금 EXIT_RIFT 본격 — active_rifts empty 본격 강한 경고
        lines.append(
            "**활성 균열**: 없음 ⚠️ (★ 방금 EXIT_RIFT — active_rifts 비움)\n"
            "  → OFFER_TO_STONE으로 새 균열 활성화 먼저 "
            "(★ target=균열 이름)\n"
            "  ⚠️ ENTER_RIFT 다시 호출 X (★ success=False)"
        )
    else:
        lines.append(
            "**활성 균열**: 없음 ⚠️ "
            "(★ ENTER_RIFT 사용 금지 — OFFER_TO_STONE 먼저)"
        )
    if party_members := world.get("party_members"):
        lines.append(f"**파티**: {', '.join(party_members)}")

    if sub_areas := floor_def.get("sub_areas"):
        lines.append("")
        lines.append("**Sub Areas (★ 1층)**")
        for sa in sub_areas[:6]:
            lines.append(f"- {sa['name']}: {sa.get('description', '')[:50]}")

    # ★ A.5 commit: GM이 spawn한 active encounters
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

    # ★ E commit: 직전 ActionType 출력
    if last_actions:
        recent = last_actions[-5:]
        lines.append("")
        lines.append(
            f"**직전 5턴 ActionType (★ E tracking)**: {', '.join(recent)}"
        )

    # ★ E commit: 본 turn forbidden + required 동적 주입
    last_action_for_forbidden: str | None = None
    if last_actions and len(last_actions) >= MAX_CONSECUTIVE_SAME_ACTION:
        recent_n = last_actions[-MAX_CONSECUTIVE_SAME_ACTION:]
        if all(a == recent_n[0] for a in recent_n):
            last_action_for_forbidden = recent_n[0]

    forbidden_section = _build_forbidden_action_section(
        last_action=last_action_for_forbidden,
        dominant_actions=dominant_actions or [],
    )
    required_section = _build_required_action_section(encounters)

    lines.extend(
        [
            "",
            "## 추천 힌트",
            hint_text,
            "",
            "## 🔥 본 turn 강제 룰 (★ E server-side)",
            "",
            forbidden_section,
            "",
            required_section,
            "",
            "## 출력 (★ JSON 1개만)",
        ]
    )

    return "\n".join(lines)


def _parse_action_json(raw_text: str, actor_name: str) -> PlayerAction:
    """LLM 응답 JSON parsing — 안전 fallback (★ 실패 시 WAIT).

    본 commit 호환 본격 (★ A.5 commit 유지):
    - parse 실패 → WAIT + rationale에 [parse_failed] 마커
    - E commit retry는 rule violation 시에만 (★ parse 실패는 WAIT 통과)
    """
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
            rationale=f"{PARSE_FAILED_MARKER} {raw_text[:100]}",
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
