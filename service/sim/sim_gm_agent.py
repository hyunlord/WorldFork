"""SimGMAgent — 시뮬 전용 GM (★ encounter 출력 본격).

본 commit (★ C 본격) 본질:
- service/game/gm_agent.py (★ 본격 게임 GM, narrative 본격) 별도
- 본 모듈은 시뮬 한정 (★ encounter mechanical 출력만)
- 27B Q2 (★ 8082) 권장

직전 commit (A) ceiling 진짜 해소:
'정수/몬스터/균열 ActionType은 ctx에 encounter 부재 → 9B Q3 합리적 선택 X'
→ 본 모듈이 GM encounter spawn으로 직접 해소
→ diversity 8+/13 본격 가능

후속 commit (D) 통합 가능:
- game/gm_agent + sim/sim_gm_agent 통합
- 본 commit은 분리 (★ MBNU 차단 + 단계적 정공법)
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.llm.client import LLMClient, Prompt

from .types import Encounter, EncounterType, GMResponse

SIM_GM_SYSTEM_PROMPT = """당신은 RPG 게임의 GM (게임 마스터)입니다.
플레이어가 1층 미궁을 탐색하는 동안 적절한 encounter를 출력합니다.

## 응답 규칙 (★ 절대 준수)
- 응답은 반드시 JSON 1개만. 설명/주석/코드블록 X.
- JSON 형식:
{
  "encounters": [
    {"type": "essence|monster|rift|item|event|narrative",
     "name": "...",
     "location": "...",
     "description": "...",
     "details": {...}}
  ],
  "narrative": "분위기 묘사 1-2문장"
}
- encounters는 0-2개 (★ 매 턴 항상 spawn X)
- 빈 turn은 narrative만

## 1층 본문 본질 (★ 작품 매핑)

**1층 = 어둠 미궁 (★ 가시거리 10m)**
- 빛 X면 몬스터/정수 인지 X
- 빛 활성 시 몬스터 등장 위험도 ↑

**1층 sub_areas (★ 본문):**
- 진입점 (★ 안전, encounter 거의 X)
- 북쪽 통로 / 남쪽 통로 (★ 22화 노움 = 남쪽)
- 수정 동굴 (★ 109/151/478화, 정수 풍부)
- 비석 공동 (★ 374화 공물 비석)
- 포탈 영역 (★ 균열 4종 입구)

**1층 9등급 몬스터 (★ 7종):**
- 고블린 / 고블린 궁수 (★ 전역)
- 노움 (★ 남쪽, 22화)
- 슬라임 (★ 전역)
- 칼날늑대 (★ 50/221화)
- 레이스 (★ 60/17화, 빛 약점)
- 위치스램프 (★ 지능형)

**1층 9등급 정수 색깔 풀:**
- 고블린: 갈색
- 노움: 흙색
- 슬라임: 청록색 / 산성록
- 칼날늑대: 핏빛
- 레이스: 회청색
- 30분 자연 소멸 (★ 13/14화)

**1층 균열 4종 (★ 1차 자료):**
- 핏빛성채 (★ 8등급 보스 + 네크로노미콘 + 여신의 눈물)
- 빙하굴 (★ 8등급 보스, 102화 6시간 1챕터)
- 녹색탄광 (★ 8등급 보스)
- 강철의 묘 (★ 8등급 보스)
- 보스 정수 드롭률 33%

## encounter spawn 가이드 (★ 빈도 본격, 다양 보장)

**핵심 원칙: encounter spawn 적극 (★ 다양성 확보)**
- 빛 X 상태도 ITEM (★ 횃불 발견) / EVENT 가능
- 빛 활성 후 거의 매 턴 spawn (★ 다양 ActionType 유도)
- 같은 type 3턴 연속 X — 다양 본격

**진입 직후 (hours_in_dungeon=0, 빛 X):**
- ✅ ITEM 발현 (★ "버려진 횃불" 등 50%)
- ✅ EVENT 발현 (★ "메아리 / 발자국" 30%)
- ✅ narrative (★ 분위기 묘사)

**빛 활성 후 (★ has_active_light=true):**
- ✅ ESSENCE 발현 (★ ~50%, 색깔 본격 다양)
- ✅ MONSTER 발현 (★ ~40%, 영역별)
- ✅ ITEM 발현 (★ ~20%)

**탐색 본격 (★ EXPLORE / MOVE 후):**
- ✅ ESSENCE 발현 (★ ~60%, 색깔별 다양)
- ✅ MONSTER 발현 (★ ~50%)
- ✅ ITEM 발현 (★ ~20%)

**시간 누적 (★ hours > 24h):**
- ✅ RIFT 발견 본격 (★ 포탈 영역에서)
- ✅ EVENT (★ 약탈자 조우)

**HP 낮음 / REST 후:**
- ✅ narrative + 가벼운 ITEM/EVENT 가능 (★ MONSTER X)

## 절대 금지
- ❌ 몬스터 등급 9 외 (★ 1층은 9등급만, 균열 안만 8등급)
- ❌ 9등급 정수 색 풀 외 색
- ❌ encounter 매 턴 spawn (★ 빈 turn 본격)
- ❌ rationale 영어 (★ 한국어만)

## few-shot 예시

### 예시 1 (★ 진입 직후, 빛 X)
입력: hours=0, has_active_light=false, sub_area=진입점
출력:
{"encounters": [], "narrative": "어둠 속 가시거리 10m. 발 밑조차 잘 보이지 않는다."}

### 예시 2 (★ 빛 활성 + 남쪽)
입력: hours=2, has_active_light=true, sub_area=남쪽 통로
출력:
{"encounters": [{"type": "monster", "name": "노움", "location": "남쪽 통로",
 "description": "흙더미 사이 노움 한 마리.",
 "details": {"grade": 9, "hp": 30}}],
 "narrative": "횃불 빛이 흙벽을 비추자 노움이 모습을 드러낸다."}

### 예시 3 (★ 수정 동굴 탐색)
입력: hours=6, has_active_light=true, sub_area=수정 동굴
출력:
{"encounters": [{"type": "essence", "name": "청록색 정수", "location": "수정 동굴",
 "description": "수정 사이 떠다니는 청록색 정수.",
 "details": {"color": "청록색", "grade": 9, "ttl_minutes": 30}}],
 "narrative": "수정이 빛을 반사하며 정수가 떠다닌다."}
"""


def _build_gm_prompt(turn_number: int, ctx: dict[str, Any]) -> str:
    """GM 컨텍스트 → user prompt."""
    chars = ctx.get("v2_characters") or {}
    world = ctx.get("v2_world_state") or {}
    location = ctx.get("v2_initial_location") or {}

    party_lines = []
    for name, c in chars.items():
        party_lines.append(
            f"  - {name}: HP {c.get('hp', '?')}/{c.get('hp_max', '?')}, "
            f"빛 {'O' if c.get('has_active_light') else 'X'}, "
            f"정수 {c.get('essence_slots_used', 0)}"
        )
    party_text = "\n".join(party_lines) if party_lines else "  (정보 X)"

    return (
        f"## 턴 {turn_number}\n\n"
        f"**위치**: {location.get('realm', '?')} "
        f"{location.get('floor', 1)}층 "
        f"{location.get('sub_area', '진입점')}\n"
        f"- 가시거리: {location.get('visibility_meters', 10)}m\n"
        f"- 빛 자원 있음: {'O' if location.get('has_light', False) else 'X'}\n\n"
        f"**미궁 시간**: {world.get('hours_in_dungeon', 0)}h / 168h\n\n"
        f"**파티 상태**:\n{party_text}\n\n"
        f"## 이 턴 encounter 결정 (★ JSON 1개)\n"
    )


def _data_to_encounters(
    data: dict[str, Any],
) -> tuple[list[Encounter], str]:
    """JSON dict → (encounters, narrative)."""
    raw_encounters = data.get("encounters") or []
    narrative = str(data.get("narrative", ""))

    encounters: list[Encounter] = []
    for e in raw_encounters:
        if not isinstance(e, dict):
            continue
        type_str = str(e.get("type", "narrative"))
        try:
            etype = EncounterType(type_str)
        except ValueError:
            etype = EncounterType.NARRATIVE

        details = e.get("details", {})
        if not isinstance(details, dict):
            details = {}

        encounters.append(
            Encounter(
                type=etype,
                name=str(e.get("name", "?")),
                location=str(e.get("location", "?")),
                description=str(e.get("description", "")),
                details=details,
            )
        )

    return encounters, narrative


def _parse_gm_json(text: str) -> tuple[list[Encounter], str]:
    """GM 응답 → (encounters, narrative). 안전 fallback."""
    text = text.strip()

    # 코드블록 우선 추출
    code_block = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL
    )
    if code_block:
        try:
            data = json.loads(code_block.group(1))
            return _data_to_encounters(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # 직접 JSON
    try:
        data = json.loads(text)
        return _data_to_encounters(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # 텍스트 안 첫 {...}
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return _data_to_encounters(data)
        except (json.JSONDecodeError, ValueError):
            pass

    return [], ""


class MockSimGMAgent:
    """Mock SimGMAgent (★ 단위 테스트 caller)."""

    def __init__(
        self, mock_responses: list[GMResponse] | None = None
    ) -> None:
        self._responses = mock_responses or [
            GMResponse(encounters=[], narrative="기본 mock narrative"),
        ]
        self._call_count = 0

    def generate_encounters(
        self,
        turn_number: int,
        game_context: dict[str, Any],
    ) -> GMResponse:
        response = self._responses[
            self._call_count % len(self._responses)
        ]
        self._call_count += 1
        return response


class SimGMAgent:
    """진짜 LLM SimGMAgent (★ 27B Q2 권장).

    LLM 호출 → JSON parsing → GMResponse.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    def generate_encounters(
        self,
        turn_number: int,
        game_context: dict[str, Any],
    ) -> GMResponse:
        """LLM 호출 → encounters / narrative 생성."""
        user_text = _build_gm_prompt(turn_number, game_context)
        prompt = Prompt(system=SIM_GM_SYSTEM_PROMPT, user=user_text)

        response = self.llm_client.generate(prompt, max_tokens=400)

        encounters, narrative = _parse_gm_json(response.text)

        return GMResponse(
            encounters=encounters,
            narrative=narrative,
            raw_text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )
