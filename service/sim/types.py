"""AI Playtester schema (★ 1차 commit).

본인 본질:
- structured output JSON (★ player가 action 출력)
- 50턴 / run (★ 1층 풀)
- 단순 오케스트레이터 (★ Python)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class PlayerActionType(StrEnum):
    """플레이어 행동 분류 (★ structured output 본질).

    1층 자료 본문 매핑:
    - 11/23화: 빛 활성화 / 이동 / 메시지 스톤 통신
    - 13/14화: 정수 흡수 / 도주
    - 27/374화: 균열 진입 / 비석 공물
    - 약탈자 조우 시 도주/전투
    """

    ACTIVATE_LIGHT = "activate_light"      # 횃불/정령 활성
    MOVE = "move"                          # sub_area 이동
    EXPLORE = "explore"                    # 탐색
    ATTACK = "attack"                      # 전투
    ABSORB_ESSENCE = "absorb_essence"      # 정수 흡수
    USE_ITEM = "use_item"                  # 아이템 사용
    OFFER_TO_STONE = "offer_to_stone"      # 비석 공물 (균열 진입)
    ENTER_RIFT = "enter_rift"              # 균열 포탈 진입
    EXIT_RIFT = "exit_rift"                # 균열 탈출
    REST = "rest"                          # 휴식 (★ 4시간 교대)
    WAIT = "wait"                          # 시간 흐름
    COMMUNICATE = "communicate"            # 메시지 스톤 통신
    FLEE = "flee"                          # 도주


@dataclass
class PlayerAction:
    """플레이어 단일 행동 (★ structured output 본질).

    LLM 9B가 JSON 출력 → sim_runner가 turn_handler 매핑.
    """

    action_type: PlayerActionType
    actor_name: str                        # "비요른" / "에르웬"
    target: str | None = None              # "횃불" / "고블린" / "북쪽 통로" 등
    rationale: str = ""                    # LLM 선택 이유 (★ 분석용)


class EncounterType(StrEnum):
    """GM이 spawn하는 encounter 종류 (★ 1층 본문 본질).

    1차 자료:
    - 11화: 빛 / 메시지 스톤 / 약탈자
    - 13/14화: 정수 흡수 자동 / 30분 자연 소멸
    - 22화: 노움 (★ 1층 남쪽)
    - 27화: 균열 정의 / 휴식 4시간
    - 374화: 비석 공물
    """

    ESSENCE = "essence"      # 떠다니는 정수 (★ 13/14화)
    MONSTER = "monster"      # 몬스터 등장 (★ 22화 노움)
    RIFT = "rift"            # 균열 발견 (★ 핏빛성채 등)
    ITEM = "item"            # 아이템 발견
    EVENT = "event"          # 일반 이벤트
    NARRATIVE = "narrative"  # narrative만 (★ encounter X)


@dataclass(frozen=True, slots=True)
class Encounter:
    """GM이 spawn한 encounter (★ ctx에 통합).

    본 commit (★ A. encounter 보강):
    - spawned_at_turn: 누적 본격 (★ TTL 계산)
    - ttl_turns: 자연 소멸 (★ ESSENCE 30분 = 30턴)
    """

    type: EncounterType
    name: str                        # "고블린" / "청록색 정수" / "핏빛성채 균열"
    location: str                    # sub_area 이름
    description: str = ""            # 본문 분위기
    details: dict[str, Any] = field(default_factory=dict)

    # ★ A. encounter 보강 본격: TTL
    spawned_at_turn: int = 0
    ttl_turns: int = 30  # default ESSENCE 30분

    def is_expired(self, current_turn: int) -> bool:
        """TTL 만료 검증."""
        return (current_turn - self.spawned_at_turn) >= self.ttl_turns


# EncounterType별 default TTL (★ 본문 본질):
ENCOUNTER_TTL: dict[EncounterType, int] = {
    EncounterType.ESSENCE: 30,    # ★ 30분 자연 소멸 (13/14화)
    EncounterType.MONSTER: 5,     # ★ 처치/도주 (단순화)
    EncounterType.RIFT: 100,      # ★ 균열 안정 (★ 진입까지)
    EncounterType.ITEM: 50,       # ★ 아이템 길게
    EncounterType.EVENT: 3,       # ★ 이벤트 짧음
    EncounterType.NARRATIVE: 1,   # ★ 즉시 만료
}


@dataclass
class GMResponse:
    """GM 단일 턴 응답 (★ structured output)."""

    encounters: list[Encounter] = field(default_factory=list)
    narrative: str = ""              # 분위기 묘사 (★ 옵션)
    raw_text: str = ""
    cost_usd: float = 0.0
    latency_ms: int = 0


@dataclass
class TurnLog:
    """단일 턴 진짜 결과 — 분석 본질 (★ 빌드 패턴 / 균형 / 작품 매칭)."""

    turn_number: int
    actor_name: str
    action: PlayerAction
    success: bool
    message: str
    side_effects: list[str] = field(default_factory=list)

    # ★ 시뮬 분석 자료
    hp_before: int = 0
    hp_after: int = 0
    essence_slots_used: int = 0
    has_active_light: bool = False
    hours_in_dungeon: int = 0


@dataclass
class SimResult:
    """N턴 시뮬 결과 (★ 후속 분석 — HP/정수/시간 분포, 빌드 패턴)."""

    sim_id: str
    config_summary: str

    total_turns: int
    completed_turns: int                   # 영구사망 시 < total_turns

    turn_logs: list[TurnLog] = field(default_factory=list)

    # 종료 사유
    end_reason: str = ""                   # "max_turns" / "permadeath" / "exit_floor"

    # 통계 (★ 후속 commit 본격)
    final_hp_by_actor: dict[str, int] = field(default_factory=dict)
    essences_absorbed_by_actor: dict[str, int] = field(default_factory=dict)
    final_hours_in_dungeon: int = 0

    # 비용
    total_player_llm_cost: float = 0.0
    total_gm_llm_cost: float = 0.0
    total_latency_seconds: float = 0.0

    # ★ A.6 server-side enforcement metrics (GM)
    gm_retry_count: int = 0
    gm_fallback_count: int = 0

    # ★ E commit server-side enforcement metrics (Player, A.6 mirror)
    player_retry_count: int = 0
    player_fallback_count: int = 0


@dataclass
class SimConfig:
    """시뮬 설정 (★ 본인 결정 — 1층 / 50턴 / 9B+27B 비교)."""

    scenario_id: str = "barbarian_v2_floor1"
    max_turns: int = 50

    # ★ LLM 모델 (★ 본인 비교 본질)
    player_llm_model: str = "qwen2.5-coder-7b-instruct-q4"  # 9B 권장
    gm_llm_model: str = "qwen2.5-coder-32b-instruct-q4"     # 27B 권장

    # 시뮬 종료 조건
    stop_on_permadeath: bool = True        # 주인공 영구사망 시 stop
    stop_on_floor_exit: bool = False       # 1층 탈출 시 stop (★ 후속)

    # 분석 자료 저장
    save_turn_logs: bool = True
    output_path: str | None = None         # JSON 저장 경로
