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
    # ★ Phase 8 C / R3 — 인접 층 진입 / 복귀 (★ generic)
    ENTER_NEXT_FLOOR = "enter_next_floor"      # 현재 층 → current+1
    EXIT_TO_PREV_FLOOR = "exit_to_prev_floor"  # 현재 층 → current-1 (★ 왕복)
    # ★ Phase 8 exchange — 마을 환전소 본격 마석 → 스톤 batch 환전
    EXCHANGE_MAGE_STONES = "exchange_mage_stones"
    # ★ Phase 9 — 마을 시간 mechanism (★ 19화 매월 1일 / 30일 정합).
    # 본 actions는 TIME_LIMIT_REACHED status 본격 본격 사용 (★ 마을 turn loop).
    WAIT_IN_VILLAGE = "wait_in_village"  # ★ 1일 진행 (HP/SP 회복)
    ENTER_DUNGEON = "enter_dungeon"      # ★ 매월 1일 자정 1층 재진입
    # ★ Phase 9.5 — 삼신교 신전 부상 치료 (★ 268/55/72화 정합)
    HEAL_AT_TEMPLE = "heal_at_temple"


@dataclass
class PlayerAction:
    """플레이어 단일 행동 (★ structured output 본질).

    LLM 9B가 JSON 출력 → sim_runner가 turn_handler 매핑.
    """

    action_type: PlayerActionType
    actor_name: str                        # "비요른" / "에르웬"
    target: str | None = None              # "횃불" / "고블린" / "북쪽 통로" 등
    rationale: str = ""                    # LLM 선택 이유 (★ 분석용)
    # ★ Phase 8 A3 — 옵션 메타 (예: ATTACK의 attack_element → 보스 약점 2배)
    metadata: dict[str, Any] = field(default_factory=dict)


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


# ─── F commit 본격: DungeonPhase + phase별 type 분포 ───


class DungeonPhase(StrEnum):
    """1층 미궁 진행 단계 (★ F commit, 작품 본문 정합).

    1차 자료:
    - 11화: 빛 / 메시지 스톤 / 약탈자 (★ ENTRY)
    - 13/14화: 정수 흡수 (★ EXPLORE)
    - 22화: 노움 (★ COMBAT)
    - 27화: 균열 / 휴식 (★ RIFT)
    - 168h: 미궁 한도
    """

    ENTRY = "entry"        # h<5: NARRATIVE 위주
    EXPLORE = "explore"    # 5<h<24: ESSENCE/MONSTER 본격
    COMBAT = "combat"      # 24<h<72: MONSTER/ITEM 본격
    RIFT = "rift"          # h>72: RIFT 본격


def determine_phase(hours_in_dungeon: int) -> DungeonPhase:
    """미궁 시간 → phase 본격 결정 (★ G commit, F 회귀 답).

    F commit (★ 회귀 본질):
    - h<5 ENTRY → ENTRY 본격 갇힘 (★ 시간 진행 X)

    G commit (★ 본격 완화):
    - h<2 ENTRY (★ 짧게)
    - 2≤h<24 EXPLORE 본격
    - 24≤h<72 COMBAT 유지
    - h≥72 RIFT 유지
    """
    if hours_in_dungeon < 2:
        return DungeonPhase.ENTRY
    if hours_in_dungeon < 24:
        return DungeonPhase.EXPLORE
    if hours_in_dungeon < 72:
        return DungeonPhase.COMBAT
    return DungeonPhase.RIFT


# ─── G commit 본격: ActionType별 시간 진행 매핑 ───

ACTION_HOURS_DELTA: dict[PlayerActionType, float] = {
    # 즉시 (★ 작품 본문)
    PlayerActionType.ACTIVATE_LIGHT: 0.1,    # ★ 11화 빛 활성 즉시
    PlayerActionType.ABSORB_ESSENCE: 0.1,    # ★ 13/14화 살이 닿으면 자동
    PlayerActionType.USE_ITEM: 0.2,
    # 짧음
    PlayerActionType.MOVE: 0.5,              # sub_area 이동
    PlayerActionType.ATTACK: 0.5,
    PlayerActionType.COMMUNICATE: 0.5,
    PlayerActionType.FLEE: 0.5,
    PlayerActionType.ENTER_RIFT: 0.5,
    PlayerActionType.EXIT_RIFT: 0.5,
    # ★ Phase 8 C / R3 — 층 전환 본격 RIFT 본격 정합 (★ 0.5h)
    PlayerActionType.ENTER_NEXT_FLOOR: 0.5,
    PlayerActionType.EXIT_TO_PREV_FLOOR: 0.5,
    # ★ Phase 8 exchange — 환전 batch (★ 마을 본격, 본격 짧음)
    PlayerActionType.EXCHANGE_MAGE_STONES: 0.5,
    # ★ Phase 9 — 마을 시간 본격 (★ 마을 별도 day counter — 본 hours 본격 본격 0).
    PlayerActionType.WAIT_IN_VILLAGE: 0.0,
    PlayerActionType.ENTER_DUNGEON: 0.0,
    PlayerActionType.HEAL_AT_TEMPLE: 0.0,
    # 중간
    PlayerActionType.EXPLORE: 1.0,           # 정탐
    PlayerActionType.OFFER_TO_STONE: 1.0,    # ★ 374화 비석 공물
    # 길음
    PlayerActionType.WAIT: 2.0,
    PlayerActionType.REST: 4.0,              # ★ 27화 휴식 4시간 본문
}


def action_hours_delta(
    action_type: PlayerActionType,
    time_scale: float = 1.0,
) -> float:
    """ActionType → 미궁 시간 진행 (★ G commit 본격 + H scale).

    1차 자료:
    - 27화: 휴식 4시간 교대
    - 13/14화: 정수 흡수 살이 닿으면 자동 (★ 즉시)
    - 11화: 빛 활성 즉시
    - 374화: 비석 공물 본격

    Args:
        action_type: ActionType
        time_scale: 시간 진행 배율 (★ H commit, default 1.0)
            * 1.0 = G commit base 본격
            * 2.0 = H commit RIFT 도달 본격 (★ 50턴에 78h+)

    Returns:
        시간 진행 시간 (★ scale 적용 본격)
    """
    base = ACTION_HOURS_DELTA.get(action_type, 0.5)
    return base * time_scale


# phase별 권장 type 분포 (★ F commit, 본격 본질, sum ~1.0)
PHASE_TYPE_WEIGHTS: dict[DungeonPhase, dict[EncounterType, float]] = {
    DungeonPhase.ENTRY: {
        EncounterType.NARRATIVE: 0.60,
        EncounterType.ESSENCE: 0.20,
        EncounterType.EVENT: 0.20,
    },
    DungeonPhase.EXPLORE: {
        EncounterType.ESSENCE: 0.35,
        EncounterType.MONSTER: 0.25,
        EncounterType.ITEM: 0.20,
        EncounterType.EVENT: 0.10,
        EncounterType.NARRATIVE: 0.10,
    },
    DungeonPhase.COMBAT: {
        EncounterType.MONSTER: 0.40,
        EncounterType.ESSENCE: 0.25,
        EncounterType.ITEM: 0.15,
        EncounterType.EVENT: 0.10,
        EncounterType.NARRATIVE: 0.10,
    },
    DungeonPhase.RIFT: {
        EncounterType.RIFT: 0.40,
        EncounterType.MONSTER: 0.25,
        EncounterType.EVENT: 0.15,
        EncounterType.NARRATIVE: 0.10,
        EncounterType.ESSENCE: 0.10,
    },
}


# phase별 spawn 빈도 (★ F commit, 본격 본질)
PHASE_SPAWN_FREQUENCY: dict[DungeonPhase, float] = {
    DungeonPhase.ENTRY: 0.30,    # 진입 본격 낮음
    DungeonPhase.EXPLORE: 0.70,  # 탐색 본격 높음
    DungeonPhase.COMBAT: 0.80,   # 몬스터 본격 높음
    DungeonPhase.RIFT: 0.90,     # 균열 본격 매우 높음
}


# phase별 권장 (top weight) types (★ enforcement 본격)
PHASE_PRIORITY_TYPES: dict[DungeonPhase, list[EncounterType]] = {
    DungeonPhase.ENTRY: [
        EncounterType.NARRATIVE,
        EncounterType.ESSENCE,
        EncounterType.EVENT,
    ],
    DungeonPhase.EXPLORE: [
        EncounterType.ESSENCE,
        EncounterType.MONSTER,
        EncounterType.ITEM,
        EncounterType.EVENT,
        EncounterType.NARRATIVE,
    ],
    DungeonPhase.COMBAT: [
        EncounterType.MONSTER,
        EncounterType.ESSENCE,
        EncounterType.ITEM,
        EncounterType.EVENT,
        EncounterType.NARRATIVE,
    ],
    DungeonPhase.RIFT: [
        EncounterType.RIFT,
        EncounterType.MONSTER,
        EncounterType.EVENT,
        EncounterType.NARRATIVE,
        EncounterType.ESSENCE,
    ],
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

    # ★ Phase 8 A3 E2E — 보스 사이클 trace용 per-turn snapshot
    # (서비스 운용 시 None — sim_runner._action_to_turn_log 본격 population)
    world_snapshot: dict[str, Any] | None = None
    location_snapshot: dict[str, Any] | None = None


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

    # ★ F commit phase enforcement metric (GM, phase mismatch)
    gm_phase_mismatch_count: int = 0


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

    # ★ H commit base + I commit (1-3h 미달 직접 답):
    # H 48.0 → I 72.0 (★ 첫 turn부터 RIFT phase 본격)
    initial_hours_in_dungeon: float = 72.0  # ★ I: RIFT phase 시작
    time_scale: float = 2.0                 # ★ H delta 2배 본격

    # ★ Phase 8 A3 E2E — ENTER_RIFT 시 변종 강제 옵션
    # None: 기본 (★ rng 본격 base_probability)
    # True/False: 결정적 — A2 decide_variant 본격 우회 (variant_boss_name X
    # 균열은 True여도 일반 fallback, A1 본격)
    force_variant: bool | None = None
