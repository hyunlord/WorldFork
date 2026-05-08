"""SimGMAgent — 시뮬 전용 GM (★ encounter 출력 본격).

본 commit (★ A.6 본격, server-side enforcement):
- prompt-only enforcement = LLM stochastic 본격 X 따른다 (★ B commit 입증)
- server-side rejection 본격 (★ Step A)
- type rotation balance 강제 (★ Step B)
- fallback narrative 안전 (★ Step C)

직전 commit (A.5) 한계:
- _last_encounter_types tracking + prompt 출력
- SIM_GM_SYSTEM_PROMPT '직전 type 연속 절대 금지' 명시
- = prompt-only → 4-way 모두 absorb_essence 74-94% dominance

본 commit 정공법 본질:
- LLM 응답 받고 직전 type / dominance 검증
- 위반 시 재호출 (★ MAX_RETRY_COUNT)
- retry 모두 실패 시 fallback narrative
- enforcement_stats 본격 측정 (★ retry / fallback)
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from typing import Any

from core.llm.client import LLMClient, Prompt

from .types import Encounter, EncounterType, GMResponse

log = logging.getLogger(__name__)


# ─── 본 commit 본격 본질 ───

# Step A 본격: 직전 1턴과 같은 type 본격 X (★ _is_violation last_type 직접 검증)

# dominance 검증 (★ Step B)
DOMINANCE_WINDOW = 5            # 직전 5턴
DOMINANCE_THRESHOLD = 0.6       # 60%+ 시 dominance
DOMINANCE_TYPES_TO_REJECT = 3   # 직전 5턴 중 같은 type 3+

# retry 본격
MAX_RETRY_COUNT = 2             # LLM 재호출 최대 2회

# fallback narrative (★ Step C)
FALLBACK_NARRATIVE = "주변이 잠시 고요해진다. 미궁의 어둠이 천천히 흐른다."

# tracking 본격
LAST_TYPES_WINDOW = 10          # _last_encounter_types 최근 10개 유지


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

## 🔥 본격 다양 강제 (★ A.6 server-side enforcement)

**직전 spawn type과 같은 type 연속 spawn 절대 금지**:
- 직전이 ESSENCE → 본 turn은 MONSTER / RIFT / ITEM / EVENT 中
- 직전이 MONSTER → 본 turn은 ESSENCE / RIFT / ITEM / EVENT 中
- = 같은 type 연속은 SEVERE 정합 위반
- ★ A.6 본격: server가 응답 검증, 위반 시 재호출 + fallback narrative

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

## 🚫 절대 금지 (★ A.6 server-side 본격)
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


# ─── 본격 helpers (★ A.6 server-side) ───


def _detect_dominant_types(
    last_types: list[str],
    window: int = DOMINANCE_WINDOW,
    threshold: float = DOMINANCE_THRESHOLD,
    consecutive: int = DOMINANCE_TYPES_TO_REJECT,
) -> list[str]:
    """직전 window 안 dominance type 본격 검출 (★ Step B)."""
    if not last_types:
        return []

    recent = last_types[-window:]
    if len(recent) < 2:
        return []

    counter: Counter[str] = Counter(recent)
    total = len(recent)

    return [
        t for t, c in counter.items()
        if c / total >= threshold or c >= consecutive
    ]


def _build_forbidden_section(
    last_type: str | None,
    dominant_types: list[str],
) -> str:
    """본 turn force-reject 본격 섹션 (★ A.6 동적 주입).

    LLM에 본격 본질 강제:
    - 직전 type 명시
    - dominance type 명시
    - 본 turn은 위 type 외 본격 spawn 또는 narrative만
    """
    if not last_type and not dominant_types:
        return "(★ 본 turn 자유 spawn)"

    lines = ["**본 turn 절대 spawn 금지**:"]
    if last_type:
        lines.append(f"- ❌ {last_type} (★ 직전 turn과 같음)")
    for dt in dominant_types:
        if dt != last_type:
            lines.append(f"- ❌ {dt} (★ 직전 5턴 dominance)")

    lines.append("")
    lines.append("→ 본 turn은 위 type 외 본격 spawn 또는 narrative만")

    return "\n".join(lines)


def _is_violation(
    new_encounters: list[Encounter],
    last_type: str | None,
    dominant_types: list[str],
) -> tuple[bool, str]:
    """본 turn encounter가 rule 위반? (★ A.6 본격).

    Returns:
        (위반 여부, reason)
    """
    forbidden = set(dominant_types)
    if last_type:
        forbidden.add(last_type)

    if not forbidden:
        return False, ""

    # narrative-only는 항상 OK (★ 안전)
    non_narrative = [
        e for e in new_encounters
        if e.type != EncounterType.NARRATIVE
    ]
    if not non_narrative:
        return False, ""

    # 본 turn type 검증
    for e in non_narrative:
        if e.type.value in forbidden:
            return True, f"{e.type.value} 본격 spawn 금지"

    return False, ""


def _make_fallback_response(
    narrative: str = FALLBACK_NARRATIVE,
) -> GMResponse:
    """fallback narrative 본격 (★ Step C)."""
    return GMResponse(
        encounters=[
            Encounter(
                type=EncounterType.NARRATIVE,
                name="고요",
                location="미궁",
                description=narrative,
            )
        ],
        narrative=narrative,
        raw_text="(★ A.6 fallback)",
        cost_usd=0.0,
        latency_ms=0,
    )


def _build_gm_prompt(
    turn_number: int,
    ctx: dict[str, Any],
    last_encounter_types: list[str] | None = None,
    dominant_types: list[str] | None = None,
) -> str:
    """GM 컨텍스트 → user prompt (★ A.6 force-reject 본격)."""
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

    # 직전 types 출력 (★ A.5 유지)
    last_types_text = ""
    if last_encounter_types:
        recent = last_encounter_types[-DOMINANCE_WINDOW:]
        last_types_text = (
            "\n**직전 spawn types (★ A.5 tracking)**:\n"
            f"{', '.join(recent)}\n"
        )

    # ★ A.6 본격: forbidden section (★ server-side 동적)
    last_type = last_encounter_types[-1] if last_encounter_types else None
    forbidden_section = _build_forbidden_section(
        last_type=last_type,
        dominant_types=dominant_types or [],
    )

    # active encounters 출력 (★ A.5 누적)
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
        f"- 빛 자원 있음: "
        f"{'O' if location.get('has_light', False) else 'X'}\n\n"
        f"**미궁 시간**: {world.get('hours_in_dungeon', 0)}h / 168h\n\n"
        f"**파티 상태**:\n{party_text}\n"
        f"{active_text}{last_types_text}\n"
        f"## 🔥 본 turn 강제 룰 (★ A.6 server-side)\n"
        f"{forbidden_section}\n\n"
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
    """진짜 LLM SimGMAgent — server-side enforcement 본격 (★ A.6).

    본 commit 본격:
    1. LLM 호출 → encounter 응답
    2. server-side rule check (★ 직전 type / dominance)
    3. 위반 시 retry (★ MAX_RETRY_COUNT)
    4. retry 모두 실패 시 fallback narrative
    5. enforcement_stats 본격 측정
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_retry: int = MAX_RETRY_COUNT,
    ) -> None:
        self.llm_client = llm_client
        self.max_retry = max_retry
        self._last_encounter_types: list[str] = []
        # ★ A.6 본격: enforcement metrics
        self._retry_count_total = 0
        self._fallback_count = 0

    @property
    def model_name(self) -> str:
        return self.llm_client.model_name

    @property
    def enforcement_stats(self) -> dict[str, int]:
        """본 commit 본격 metrics (★ retry / fallback 카운트)."""
        return {
            "retry_count": self._retry_count_total,
            "fallback_count": self._fallback_count,
        }

    def generate_encounters(
        self,
        turn_number: int,
        game_context: dict[str, Any],
    ) -> GMResponse:
        """LLM 호출 + server-side enforcement (★ A.6 본격)."""
        # ★ Step B: dominance 검출
        dominant_types = _detect_dominant_types(self._last_encounter_types)

        last_response: Any = None
        last_violation = ""

        # ★ Step A: retry loop
        for attempt in range(self.max_retry + 1):
            user_text = _build_gm_prompt(
                turn_number,
                game_context,
                last_encounter_types=self._last_encounter_types,
                dominant_types=dominant_types,
            )
            prompt = Prompt(system=SIM_GM_SYSTEM_PROMPT, user=user_text)

            response = self.llm_client.generate(prompt, max_tokens=400)
            encounters, narrative = _parse_gm_json(response.text)

            # rule check
            last_type = (
                self._last_encounter_types[-1]
                if self._last_encounter_types
                else None
            )
            violation, reason = _is_violation(
                encounters, last_type, dominant_types
            )

            if not violation:
                # OK — tracking 갱신 + return
                for e in encounters:
                    self._last_encounter_types.append(e.type.value)
                self._last_encounter_types = self._last_encounter_types[
                    -LAST_TYPES_WINDOW:
                ]

                return GMResponse(
                    encounters=encounters,
                    narrative=narrative,
                    raw_text=response.text,
                    cost_usd=response.cost_usd,
                    latency_ms=response.latency_ms,
                )

            # 위반 — retry (★ 실제 재호출 본격일 때만 카운트)
            log.warning(
                "GM rule violation turn=%d attempt=%d reason=%s",
                turn_number,
                attempt + 1,
                reason,
            )
            if attempt < self.max_retry:
                self._retry_count_total += 1
            last_response = response
            last_violation = reason

        # ★ Step C: retry 모두 실패 → fallback narrative
        log.warning(
            "GM enforcement fallback turn=%d violation=%s",
            turn_number,
            last_violation,
        )
        self._fallback_count += 1

        fallback = _make_fallback_response()
        # 직전 type tracking에 narrative 본격 추가
        self._last_encounter_types.append(EncounterType.NARRATIVE.value)
        self._last_encounter_types = self._last_encounter_types[
            -LAST_TYPES_WINDOW:
        ]

        # 비용/지연은 마지막 LLM 응답 누적 본격 (★ retry 횟수만큼)
        if last_response is not None:
            attempts = self.max_retry + 1
            return GMResponse(
                encounters=fallback.encounters,
                narrative=fallback.narrative,
                raw_text=f"(★ A.6 fallback after {attempts} attempts)",
                cost_usd=last_response.cost_usd * attempts,
                latency_ms=last_response.latency_ms * attempts,
            )
        return fallback

    def reset_history(self) -> None:
        """시뮬 시작 시 호출 (★ 직전 시뮬 영향 X + metrics reset)."""
        self._last_encounter_types = []
        self._retry_count_total = 0
        self._fallback_count = 0
