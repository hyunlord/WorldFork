"""V3 Phase 3 — 파티 확장 단위 테스트.

파티 전원 자율(코드 0토큰), 분기점 감지(LLM 빈도 — 평소 없음/사건만), 파티 제어
(특정/전원, 같은 명령 다른 반응), 동료 위기 → 유대 높은 동료 구원.
"""

from unittest.mock import MagicMock

from service.sim.disposition import (
    PRESET_BERSERKER,
    PRESET_GUARDIAN,
    PRESET_SCOUT,
    Companion,
    DispoAction,
)
from service.sim.disposition_tick import TickEnemy
from service.sim.party import (
    BranchReason,
    PartyWorld,
    command_all,
    command_member,
    detect_branch,
    party_step,
)


def _party() -> PartyWorld:
    return PartyWorld(
        companions=[
            Companion("전사", PRESET_BERSERKER, pos=(0, 0)),
            Companion("정찰꾼", PRESET_SCOUT, pos=(0, 1)),
            Companion("수호자", PRESET_GUARDIAN, pos=(0, 2)),
        ],
    )


def _client(reaction: str, action: str) -> MagicMock:
    c = MagicMock()
    c.generate_json.return_value = MagicMock(
        parsed={"reaction": reaction, "action": action, "reason": "근거", "speech": "발화."}
    )
    return c


class TestPartyAutonomy:
    def test_all_act_each_tick(self) -> None:
        w = _party()
        results = party_step(w)
        assert len(results) == 3  # 전원 행동
        assert all(isinstance(r.action, DispoAction) for r in results)

    def test_members_differ_in_combat(self) -> None:
        # 같은 적, 파티 성향 다름 → 전사 돌격 / 정찰꾼 원거리(다른 행동)
        w = _party()
        w.enemies = [TickEnemy("고블린", pos=(5, 0), hp=30)]
        results = {r.note.split(":")[0]: r.action for r in party_step(w)}
        assert results["전사"] is DispoAction.CHARGE
        assert results["정찰꾼"] is DispoAction.RANGED

    def test_deterministic(self) -> None:
        a, b = _party(), _party()
        a.enemies = [TickEnemy("g", (4, 0), 30)]
        b.enemies = [TickEnemy("g", (4, 0), 30)]
        ra = [(r.action, r.companion_pos) for r in party_step(a)]
        rb = [(r.action, r.companion_pos) for r in party_step(b)]
        assert ra == rb


class TestBranchDetection:
    """★ LLM 빈도 — 평소 분기점 없음(LLM 0), 사건에만 분기점."""

    def test_calm_no_branch(self) -> None:
        # 적 없음 + 전원 건강 → 분기점 없음(LLM 호출 불필요)
        assert detect_branch(_party()) == []

    def test_new_enemy_branch(self) -> None:
        w = _party()
        w.enemies = [TickEnemy("고블린", pos=(3, 0), hp=30)]
        assert BranchReason.NEW_ENEMY in detect_branch(w)

    def test_no_repeat_new_enemy(self) -> None:
        # 같은 적이 계속 있으면 두 번째부턴 NEW_ENEMY 아님(빈도 억제)
        w = _party()
        w.enemies = [TickEnemy("고블린", pos=(3, 0), hp=30)]
        detect_branch(w)  # 1회차 — new_enemy
        assert BranchReason.NEW_ENEMY not in detect_branch(w)

    def test_ally_critical_branch(self) -> None:
        w = _party()
        w.companions[0].hp = 10  # 전사 위기
        assert BranchReason.ALLY_CRITICAL in detect_branch(w)

    def test_conflict_branch(self) -> None:
        # 전사(돌격) + 정찰꾼(원거리) 공존 → 의견 충돌 분기점
        w = _party()
        w.enemies = [TickEnemy("고블린", pos=(3, 0), hp=30)]
        assert BranchReason.CONFLICT in detect_branch(w)

    def test_llm_frequency_low(self) -> None:
        # ★ 평소 N틱 진행 동안 분기점 0 — 파티여도 LLM 빈도 안 터진다
        w = _party()
        branch_ticks = 0
        for _ in range(10):
            party_step(w)
            if detect_branch(w):
                branch_ticks += 1
        assert branch_ticks == 0  # 적 없는 평온한 진행 → LLM 0


class TestPartyControl:
    def test_command_specific_member(self) -> None:
        w = _party()
        r = command_member(w, "정찰꾼", "정찰해", "x", client=_client("comply", "scout"))
        assert r is not None and r.action is DispoAction.SCOUT
        # 지시받은 동료만 order 설정, 나머지는 자율
        assert w.companions[1].current_order is DispoAction.SCOUT
        assert w.companions[0].current_order is None

    def test_command_unknown_member(self) -> None:
        r = command_member(_party(), "없는이", "x", "y", client=_client("comply", "scout"))
        assert r is None

    def test_command_all_each_interprets(self) -> None:
        # 전원 지시 — 각자 자기 성향으로 해석(mock은 동일하나 전원에 적용)
        w = _party()
        out = command_all(w, "후퇴", "x", client=_client("comply", "follow"))
        assert set(out.keys()) == {"전사", "정찰꾼", "수호자"}
        assert all(c.current_order is DispoAction.FOLLOW for c in w.companions)


class TestRescueAlly:
    def test_guardian_rescues_critical_member(self) -> None:
        # 동료(정찰꾼) 위기 → 유대 높은 수호자가 구원 행동
        w = _party()
        w.companions[1].hp = 5  # 정찰꾼 위기
        results = {r.note.split(":")[0]: r.action for r in party_step(w)}
        assert results["수호자"] is DispoAction.RESCUE
