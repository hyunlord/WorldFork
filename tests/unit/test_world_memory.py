"""V3 Phase 2 — 영구 세계 단위 테스트.

선택적 영구(핵심만 기록, 일회성 휘발), LLM 영구 판정(mock) + 결정적 폴백,
재등장 반영(NPC 태도/세계 막힘/관계 누적), 과거 행동 → 나중 의미 시나리오.
"""

from unittest.mock import MagicMock

from service.sim.world_memory import (
    Attitude,
    PermanenceKind,
    PermanenceRecord,
    WorldState,
    adjust_relationship,
    is_blocked,
    judge_permanence,
    npc_attitude,
    record,
)


class TestSelectivePermanence:
    def test_ephemeral_skipped(self) -> None:
        # 일회성(영구 아님) → 세계에 안 남는다(폭발 방지)
        w = WorldState()
        assert record(w, PermanenceRecord(False, PermanenceKind.NONE, "", "", 0)) is False
        assert w.flags == {} and w.npc_memories == {} and w.relationships == {}

    def test_flag_recorded(self) -> None:
        w = WorldState()
        record(w, PermanenceRecord(True, PermanenceKind.FLAG, "수정동굴_천장", "무너짐"))
        assert w.flags["수정동굴_천장"] == "무너짐"

    def test_memory_recorded(self) -> None:
        w = WorldState()
        record(w, PermanenceRecord(True, PermanenceKind.MEMORY, "노움상인", "비요른에게 배신당함"))
        assert "비요른에게 배신당함" in w.npc_memories["노움상인"]

    def test_relationship_clamped(self) -> None:
        w = WorldState()
        record(w, PermanenceRecord(True, PermanenceKind.RELATIONSHIP, "철수", "", 80))
        record(w, PermanenceRecord(True, PermanenceKind.RELATIONSHIP, "철수", "", 80))
        assert w.relationships["철수"] == 100  # 상한 클램프


class TestJudgePermanence:
    def _client(self, **parsed: object) -> MagicMock:
        c = MagicMock()
        c.generate_json.return_value = MagicMock(parsed=parsed)
        return c

    def test_llm_permanent_parsed(self) -> None:
        c = self._client(
            permanent=True, kind="flag", subject="다리", content="불탐", relationship_delta=0
        )
        r = judge_permanence("다리를 불태웠다", "다리 소실", client=c)
        assert r.permanent and r.kind is PermanenceKind.FLAG

    def test_fallback_ephemeral_for_combat(self) -> None:
        from core.llm.client import LLMError

        c = MagicMock()
        c.generate_json.side_effect = LLMError("down")
        # 평범한 전투 → 휘발(영구 신호어 없음)
        r = judge_permanence("고블린을 공격한다", "「피해 9」", client=c)
        assert r.permanent is False and r.kind is PermanenceKind.NONE

    def test_fallback_betrayal_permanent(self) -> None:
        from core.llm.client import LLMError

        c = MagicMock()
        c.generate_json.side_effect = LLMError("down")
        r = judge_permanence("노움 상인을 배신하고 마석을 빼앗았다", "상인 분노", client=c)
        # 배신 = 관계 변화 + 기억(record가 둘 다 반영)
        assert r.permanent and r.kind is PermanenceKind.RELATIONSHIP
        assert r.relationship_delta < 0

    def test_fallback_collapse_flag(self) -> None:
        from core.llm.client import LLMError

        c = MagicMock()
        c.generate_json.side_effect = LLMError("down")
        r = judge_permanence("천장을 무너뜨렸다", "통로 붕괴", client=c)
        assert r.permanent and r.kind is PermanenceKind.FLAG


class TestReencounter:
    def test_betrayed_npc_hostile(self) -> None:
        w = WorldState()
        rec = PermanenceRecord(
            True, PermanenceKind.RELATIONSHIP, "노움", "비요른에게 배신당함", -45
        )
        record(w, rec)
        assert npc_attitude(w, "노움") is Attitude.HOSTILE

    def test_helped_npc_friendly(self) -> None:
        w = WorldState()
        adjust_relationship(w, "촌장", 30, "위기에서 구원받음")
        assert npc_attitude(w, "촌장") is Attitude.FRIENDLY

    def test_devoted_at_high_bond(self) -> None:
        w = WorldState()
        adjust_relationship(w, "동료", 70, "여러 번 도움")
        assert npc_attitude(w, "동료") is Attitude.DEVOTED

    def test_unknown_npc_neutral(self) -> None:
        assert npc_attitude(WorldState(), "처음본자") is Attitude.NEUTRAL

    def test_collapsed_location_blocked(self) -> None:
        w = WorldState()
        record(w, PermanenceRecord(True, PermanenceKind.FLAG, "북쪽통로", "무너짐"))
        assert is_blocked(w, "북쪽통로") is True
        assert is_blocked(w, "남쪽통로") is False


class TestPastMatters:
    """★ 과거 행동 → 나중 의미 (통합 시나리오)."""

    def test_betrayal_returns_as_hostility(self) -> None:
        from core.llm.client import LLMError

        w = WorldState()
        broken = MagicMock()
        broken.generate_json.side_effect = LLMError("down")
        # 1. 과거: 상인 배신 → 영구 판정 → 기록
        rec = judge_permanence("노움 상인을 배신했다", "마석 강탈", client=broken)
        rec.subject = "노움상인"  # 판정이 대상을 특정(폴백은 일반명 → 호출자가 지정)
        record(w, rec)
        # 2. 나중: 노움상인 재등장 → 코드가 적대로 반영
        assert npc_attitude(w, "노움상인") is Attitude.HOSTILE
        assert any("배신" in m for m in w.npc_memories["노움상인"])

    def test_collapse_blocks_revisit(self) -> None:
        from core.llm.client import LLMError

        w = WorldState()
        broken = MagicMock()
        broken.generate_json.side_effect = LLMError("down")
        rec = judge_permanence("북쪽 천장을 무너뜨렸다", "통로 붕괴", client=broken)
        rec.subject = "북쪽통로"
        record(w, rec)
        assert is_blocked(w, "북쪽통로") is True
