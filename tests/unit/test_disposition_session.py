"""V3 — 성향 엔진 세션 통합 테스트 (Phase 0+1+2 한 흐름).

자율 틱 → 지시 개입 → 영구 반영이 한 세션으로 엮이는가. 과거 사건(배신/도움/붕괴)이
재등장/재방문 때 코드로 돌아오는가(end-to-end).
"""

from unittest.mock import MagicMock

from service.sim.disposition import PRESET_SCOUT, Companion, DispoAction
from service.sim.disposition_session import DispositionSession
from service.sim.disposition_tick import TickEnemy, TickWorld
from service.sim.world_memory import Attitude, WorldState


def _session() -> DispositionSession:
    world = TickWorld(
        companion=Companion("철수", PRESET_SCOUT, pos=(0, 0)),
        enemies=[TickEnemy("고블린", pos=(1, 0), hp=30)],
        unexplored_pos=(0, 3),
    )
    return DispositionSession(world=world, memory=WorldState())


def _client(reaction: str, action: str) -> MagicMock:
    c = MagicMock()
    c.generate_json.return_value = MagicMock(
        parsed={"reaction": reaction, "action": action, "reason": "근거", "speech": "발화."}
    )
    return c


def _perm_client(**parsed: object) -> MagicMock:
    c = MagicMock()
    c.generate_json.return_value = MagicMock(parsed=parsed)
    return c


def test_tick_then_command_then_record() -> None:
    s = _session()
    # 1. 자율 틱(Phase 0) — 명령 없으면 성향대로
    r0 = s.tick()
    assert isinstance(r0.action, DispoAction)
    # 2. 개입(Phase 1) — 순응 → current_order 설정 → 다음 틱이 따름
    resp = s.command("정찰해", "좁은 틈", client=_client("comply", "scout"))
    assert resp.action is DispoAction.SCOUT
    assert s.world.companion.current_order is DispoAction.SCOUT
    assert s.tick().action is DispoAction.SCOUT
    # 3. 영구 반영(Phase 2) — 붕괴는 영구로 기록 → 재방문 막힘
    assert s.record_event(
        "천장을 무너뜨렸다", "통로 붕괴", "북쪽통로",
        client=_perm_client(
            permanent=True, kind="flag", subject="x", content="무너짐",
            relationship_delta=0,
        ),
    )
    assert s.is_path_blocked("북쪽통로") is True


def test_betrayal_returns_as_hostility() -> None:
    s = _session()
    # 과거: 상인 배신을 영구 기록
    s.record_event(
        "노움 상인을 배신했다", "마석 강탈", "노움상인",
        client=_perm_client(
            permanent=True, kind="relationship", subject="x",
            content="배신당함", relationship_delta=-45,
        ),
    )
    # 나중: 재등장 시 코드가 적대로 반영
    assert s.attitude("노움상인") is Attitude.HOSTILE


def test_ephemeral_not_recorded() -> None:
    s = _session()
    # 일회성(영구 아님) → 세계에 안 남음(선택적 영구)
    recorded = s.record_event(
        "고블린을 처치했다", "「피해 9」", "고블린",
        client=_perm_client(
            permanent=False, kind="none", subject="", content="",
            relationship_delta=0,
        ),
    )
    assert recorded is False
    assert s.attitude("고블린") is Attitude.NEUTRAL


def test_befriend_accumulates() -> None:
    s = _session()
    s.befriend("동료", 70, "여러 번 구해줌")
    assert s.attitude("동료") is Attitude.DEVOTED
