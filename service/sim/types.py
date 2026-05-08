"""AI Playtester schema (★ 1차 commit).

본인 본질:
- structured output JSON (★ player가 action 출력)
- 50턴 / run (★ 1층 풀)
- 단순 오케스트레이터 (★ Python)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


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
