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

## 🔥 본격 다양 강제 (★ 본 commit 본격)

**직전 spawn type과 같은 type 연속 spawn 절대 금지**:
- 직전이 ESSENCE → 본 turn은 MONSTER / RIFT / ITEM / EVENT 中
- 직전이 MONSTER → 본 turn은 ESSENCE / RIFT / ITEM / EVENT 中
- = 같은 type 연속은 SEVERE 정합 위반

**type rotation 본격**:
- 50턴 안 모든 type 1회 이상 spawn 권장
- 균등 분포 본격 (★ ESSENCE 25% / MONSTER 25% / RIFT 15% /
  ITEM 15% / EVENT 10% / NARRATIVE 10%)

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

## encounter spawn 빈도 본격 (★ ceiling 4 진짜 해소)

| 단계 | encounter spawn 확률 | type 우선 |
|---|---|---|
| 진입 직후 (h=0, light=X) | 30% | NARRATIVE / ITEM (★ 횃불) |
| 빛 활성 후 (h<5) | **70%** ↑ | ESSENCE / MONSTER |
| 탐색 본격 (h<24) | **80%** ↑ | ESSENCE / MONSTER / ITEM |
| 장기 탐색 (h>24) | **85%** ↑ | RIFT / EVENT 본격 |
| 균열 임박 (h>72) | 90% | RIFT 우선 |
| HP 낮음 / REST | 20% | NARRATIVE 우선 |

**type rotation 핵심**: 직전 turn type 본격 회피 → 다양 ActionType 유도

## 🚫 절대 금지 (★ 본 commit 본격)
- ❌ 직전 spawn type과 같은 type 연속 spawn (★ SEVERE 정합 위반)
- ❌ 매 턴 같은 location encounter (★ sub_area 다양)
- ❌ 9등급 외 몬스터 (★ 1층 본질, 균열 안만 8등급)
- ❌ 9등급 정수 색 풀 외 색
- ❌ rationale 영어 (★ 한국어만)

## few-shot 예시 (★ 다양 본격 — 직전 type 회피)

### 예시 1 (★ 직전 ESSENCE → 본 turn MONSTER 강제)
입력: 직전 type=essence, h=8, light=true, sub_area=수정 동굴
출력:
{"encounters": [{"type": "monster", "name": "슬라임", "location": "수정 동굴",
 "description": "수정 사이 청록색 슬라임이 미끄러진다.",
 "details": {"grade": 9, "hp": 25}}],
 "narrative": "동굴 안 슬라임이 빛에 반응한다."}

### 예시 2 (★ 직전 MONSTER → 본 turn RIFT 본격)
입력: 직전 type=monster, h=30, light=true, sub_area=포탈 영역
출력:
{"encounters": [{"type": "rift", "name": "핏빛성채", "location": "포탈 영역",
 "description": "벽면에 핏빛 균열이 열린다.",
 "details": {"name": "핏빛성채", "boss_grade": 8,
  "hidden": ["네크로노미콘"]}}],
 "narrative": "포탈 영역 끝, 핏빛으로 물든 균열이 모습을 드러낸다."}

### 예시 3 (★ 직전 RIFT → 본 turn ITEM 본격)
입력: 직전 type=rift, h=35, light=true, sub_area=비석 공동
출력:
{"encounters": [{"type": "item", "name": "메시지 스톤", "location": "비석 공동",
 "description": "비석 옆 메시지 스톤이 빛난다.",
 "details": {"value_stones": 50}}],
 "narrative": "비석 공동 안 메시지 스톤이 발견된다."}
"""


def _build_gm_prompt(
    turn_number: int,
    ctx: dict[str, Any],
    last_encounter_types: list[str] | None = None,
) -> str:
    """GM 컨텍스트 → user prompt (★ 본 commit: 직전 type 강제)."""
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

    # ★ 본 commit 본격: 직전 type 출력 (★ 다양 강제)
    last_type_text = ""
    if last_encounter_types:
        recent = last_encounter_types[-3:]
        last_type_text = (
            "\n**🔥 직전 spawn types (★ 같은 type 연속 절대 금지)**:\n"
            f"{', '.join(recent)}\n"
            "→ 본 turn은 위 types 외 type 본격 spawn\n"
        )

    # ★ 본 commit 본격: active encounters 출력 (★ 누적)
    active = ctx.get("active_encounters") or []
    active_text = ""
    if active:
        active_lines = ["**현재 active encounters (★ 누적)**:"]
        for e in active:
            ttl_rem = e.get("ttl_remaining", "?")
            active_lines.append(
                f"  - {e['type']} / {e['name']} / "
                f"{e['location']} (TTL {ttl_rem}턴)"
            )
        active_text = "\n" + "\n".join(active_lines) + "\n"

    return (
        f"## 턴 {turn_number}\n\n"
        f"**위치**: {location.get('realm', '?')} "
        f"{location.get('floor', 1)}층 "
        f"{location.get('sub_area', '진입점')}\n"
        f"- 가시거리: {location.get('visibility_meters', 10)}m\n"
        f"- 빛 자원 있음: {'O' if location.get('has_light', False) else 'X'}\n\n"
        f"**미궁 시간**: {world.get('hours_in_dungeon', 0)}h / 168h\n\n"
        f"**파티 상태**:\n{party_text}\n"
        f"{active_text}{last_type_text}\n"
        f"## 이 턴 encounter 결정 (★ JSON 1개, 다양 강제)\n"
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

    본 commit (★ A. encounter 보강):
    - 직전 encounter types tracking (★ 다양 강제)
    - reset_history() 본격 (★ 시뮬 시작 시)
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self._last_encounter_types: list[str] = []

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    def generate_encounters(
        self,
        turn_number: int,
        game_context: dict[str, Any],
    ) -> GMResponse:
        """LLM 호출 → encounters / narrative 생성 (★ 직전 type tracking)."""
        user_text = _build_gm_prompt(
            turn_number,
            game_context,
            last_encounter_types=self._last_encounter_types,
        )
        prompt = Prompt(system=SIM_GM_SYSTEM_PROMPT, user=user_text)

        response = self.llm_client.generate(prompt, max_tokens=400)

        encounters, narrative = _parse_gm_json(response.text)

        # ★ 본 commit 본격: 직전 type tracking 갱신
        for e in encounters:
            self._last_encounter_types.append(e.type.value)
        self._last_encounter_types = self._last_encounter_types[-5:]

        return GMResponse(
            encounters=encounters,
            narrative=narrative,
            raw_text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )

    def reset_history(self) -> None:
        """시뮬 시작 시 호출 (★ 직전 시뮬 영향 X)."""
        self._last_encounter_types = []
