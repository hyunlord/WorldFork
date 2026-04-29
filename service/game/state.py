"""Tier 0 GameState — 간단 인벤토리 + HP만.

Day 1: 미니멀 구조.
Day 2: 분기 추적 필드 추가 (실제 분기 동작은 Tier 1+).
Day 5: SQL 직렬화 (Tier 2).
"""

from dataclasses import dataclass, field


@dataclass
class Character:
    """게임 등장인물 (플레이어 + NPC)."""

    name: str
    role: str           # "주인공" | "동료" | "GM" | NPC
    hp: int = 100
    inventory: list[str] = field(default_factory=list)

    def is_alive(self) -> bool:
        return self.hp > 0


@dataclass
class TurnLog:
    """한 턴의 기록."""

    turn: int
    user_action: str
    gm_response: str
    cost_usd: float
    latency_ms: int


@dataclass
class PhaseProgress:
    """현재 진행 중인 Phase 추적 (Day 2)."""

    current_phase_id: str = "phase_1_entry"
    completed_triggers: list[str] = field(default_factory=list)
    phase_started_turn: int = 0


@dataclass
class GameState:
    """게임 진행 상태.

    Day 1: turn, characters, location, history (in-memory만).
    Day 2: 분기 추적 필드 추가.
    Day 5+: SQL 영속화.
    """

    scenario_id: str
    turn: int = 0
    location: str = ""
    characters: dict[str, Character] = field(default_factory=dict)
    history: list[TurnLog] = field(default_factory=list)

    # Day 2: 분기 추적 (실제 분기 동작은 Tier 1+)
    phase_progress: PhaseProgress = field(default_factory=PhaseProgress)
    selected_ending: str | None = None

    def add_turn(
        self,
        user_action: str,
        gm_response: str,
        cost_usd: float,
        latency_ms: int,
    ) -> None:
        self.turn += 1
        self.history.append(TurnLog(
            turn=self.turn,
            user_action=user_action,
            gm_response=gm_response,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        ))

    def total_cost_usd(self) -> float:
        return sum(t.cost_usd for t in self.history)

    def avg_latency_ms(self) -> float:
        if not self.history:
            return 0.0
        return sum(t.latency_ms for t in self.history) / len(self.history)

    def is_completed(self, max_turns: int = 10) -> bool:
        """Day 1 단순 종료 조건.

        Day 2+에 분기 / 결말 추가 예정.
        """
        if self.turn >= max_turns:
            return True
        if self.history and "[ENDING]" in self.history[-1].gm_response.upper():
            return True
        return False

    def get_player(self) -> "Character | None":
        """주인공 캐릭터 반환."""
        for char in self.characters.values():
            if char.role == "주인공":
                return char
        return None

    def is_in_phase(self, phase_id: str) -> bool:
        """현재 phase 확인."""
        return self.phase_progress.current_phase_id == phase_id

    def mark_trigger_completed(self, trigger_id: str) -> None:
        """trigger 완료 표시 (Tier 1+에 사용)."""
        if trigger_id not in self.phase_progress.completed_triggers:
            self.phase_progress.completed_triggers.append(trigger_id)

    def has_completed_trigger(self, trigger_id: str) -> bool:
        return trigger_id in self.phase_progress.completed_triggers
