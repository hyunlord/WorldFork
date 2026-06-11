"""V3 성향 엔진 데모 하니스 — Phase 0+1+2를 한 흐름으로 실행(실행 가능한 진입점).

게임 통합 전, 엔진이 end-to-end로 작동함을 직접 돌려 보는 러너(다른 tools/ 러너와 동일
관행). 자율 틱(Phase 0) → 자연어 지시 개입(Phase 1, LLM) → 중요 사건 영구 반영(Phase 2,
LLM) → 재등장 태도까지 한 번에 보여 준다. disposition_session/world_memory의 프로덕션 호출자.

실행: python tools/v3_disposition_demo.py  (Gemma pivotal 8085 필요 — 지시/영구 판정에 LLM)
"""

from __future__ import annotations

from service.sim.disposition import PRESET_SCOUT, Companion
from service.sim.disposition_session import DispositionSession
from service.sim.disposition_tick import TickEnemy, TickWorld
from service.sim.world_memory import WorldState


def build_session() -> DispositionSession:
    """데모 세션 — 신중한 정찰꾼 1명 + 적 + 미탐색 지점."""
    world = TickWorld(
        companion=Companion("철수", PRESET_SCOUT, pos=(0, 0)),
        enemies=[TickEnemy("고블린", pos=(4, 0), hp=30)],
        player_pos=(0, 0),
        unexplored_pos=(0, 3),
    )
    return DispositionSession(world=world, memory=WorldState())


def run_demo() -> None:
    s = build_session()
    print("=== V3 성향 엔진 데모 (Phase 0+1+2) ===")

    # Phase 0 — 평소 자율 틱(코드, LLM 없음)
    print("\n[Phase 0] 자율 틱 (성향대로, 코드):")
    for _ in range(3):
        r = s.tick()
        tail = f" — {r.note}" if r.note else ""
        print(f"  틱 {r.tick}: {r.action.value} @ {r.companion_pos}{tail}")

    # Phase 1 — 위험한 지시에 개입(성향 통과, LLM)
    print("\n[Phase 1] 지시 개입 (성향 해석, LLM):")
    resp = s.command("저 좁은 틈으로 혼자 먼저 들어가 정찰해", "함정 의심")
    print(f"  반응: {resp.reaction.value} → {resp.action.value}")
    print(f"  근거: {resp.reason}")
    print(f"  발화: {resp.speech}")
    print(f"  current_order: {s.world.companion.current_order}")

    # Phase 2 — 중요 사건의 영구 반영(LLM 판정 → 코드 기록)
    print("\n[Phase 2] 영구 반영 (LLM 판정 → 코드 기록):")
    for action, outcome, subject in (
        ("노움 상인을 배신하고 마석을 빼앗았다", "상인 분노", "노움상인"),
        ("고블린을 베어 처치했다", "「피해 14」", "고블린"),
        ("북쪽 천장을 무너뜨렸다", "통로 붕괴", "북쪽통로"),
    ):
        recorded = s.record_event(action, outcome, subject)
        print(f"  {action[:20]} → 기록={recorded}")

    print("\n[재등장 반영] 과거 → 나중 의미:")
    print(f"  노움상인 태도: {s.attitude('노움상인').value}")
    print(f"  북쪽통로 막힘: {s.is_path_blocked('북쪽통로')}")
    print(f"  세계 상태: flags={s.memory.flags} relationships={s.memory.relationships}")


if __name__ == "__main__":
    run_demo()
