"""V3 — 성향 엔진 세션 (Phase 0+1+2 통합 진입점).

흩어진 세 토대를 한 세션으로 엮는다 — 자율 틱(Phase 0) + 지시 해석(Phase 1) +
영구 반영(Phase 2). 게임/데모/테스트가 이 세션 하나로 엔진을 굴린다(world_memory·
disposition_command의 프로덕션 호출자).

흐름: 평소 tick()로 동료가 성향대로 자율(코드) → 플레이어가 command()로 개입하면 성향
통과(LLM) → 중요 사건은 record_event()로 영구성 판정(LLM) 후 세계에 남김(코드). 관계는
도움/배신 누적으로 변하고, 재등장 시 attitude()/is_path_blocked()로 코드가 반영한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.llm.local_client import LocalLLMClient
from service.sim.disposition_command import (
    CommandResponse,
    apply_order,
    interpret_command,
)
from service.sim.disposition_tick import TickResult, TickWorld, step_tick
from service.sim.world_memory import (
    Attitude,
    WorldState,
    adjust_relationship,
    is_blocked,
    judge_permanence,
    npc_attitude,
    record,
)


@dataclass
class DispositionSession:
    """성향 엔진 한 세션 — 틱 세계(Phase 0/1) + 영구 세계(Phase 2)."""

    world: TickWorld
    memory: WorldState

    def tick(self) -> TickResult:
        """평소 한 틱 — 동료가 성향(또는 현재 명령)대로 자율(코드, LLM 없음)."""
        return step_tick(self.world)

    def command(
        self,
        text: str,
        situation: str,
        *,
        client: LocalLLMClient | None = None,
    ) -> CommandResponse:
        """플레이어 개입 — 지시를 성향으로 해석(순응/변형/거부) 후 동료에 반영(Phase 1)."""
        resp = interpret_command(self.world.companion, text, situation, client=client)
        apply_order(self.world.companion, resp)
        return resp

    def record_event(
        self,
        action: str,
        outcome: str,
        subject: str,
        *,
        client: LocalLLMClient | None = None,
    ) -> bool:
        """중요 사건의 영구성을 판정(LLM)해 세계에 남긴다(Phase 2). subject=게임 정규 ID.

        영구가 아니면(일회성) 기록 안 함(선택적 영구). 기록했으면 True.
        """
        rec = judge_permanence(action, outcome, client=client)
        rec.subject = subject  # LLM 판정 위에 게임 정규 ID를 코드가 지정
        return record(self.memory, rec)

    def befriend(self, name: str, delta: int, note: str = "") -> None:
        """성향 자율/지시 누적을 관계로 — 동료 도움·구원 등(Phase 0/1 → Phase 2)."""
        adjust_relationship(self.memory, name, delta, note)

    def attitude(self, npc: str) -> Attitude:
        """재등장 NPC 태도 — 과거 기억·관계로 코드가 결정(Phase 2)."""
        return npc_attitude(self.memory, npc)

    def is_path_blocked(self, location: str) -> bool:
        """세계 재방문 — 무너뜨린 곳 등 통행 불가 여부(Phase 2)."""
        return is_blocked(self.memory, location)
