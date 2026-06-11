"""V3 Phase 1 — 지시 해석 단위 테스트 (LLM mock).

interpret_command이 LLM 출력(JSON)을 CommandResponse로 파싱하고, LLM 실패 시 결정적
성향 폴백으로 흡수하는지. 같은 지시라도 성향이 다르면 폴백 반응이 갈리는지(순응/변형/거부).
변덕 축 → temperature 매핑. order가 틱 루프에 반영되는지(코드 연결).
"""

from unittest.mock import MagicMock

from service.sim.disposition import (
    PRESET_GUARDIAN,
    PRESET_SCOUT,
    Companion,
    DispoAction,
    Disposition,
)
from service.sim.disposition_command import (
    CommandReaction,
    apply_order,
    interpret_command,
    whimsy_temperature,
)
from service.sim.disposition_tick import TickEnemy, TickWorld, run_ticks


def _client(reaction: str, action: str) -> MagicMock:
    c = MagicMock()
    c.generate_json.return_value = MagicMock(
        parsed={
            "reaction": reaction,
            "action": action,
            "reason": "성향 근거 한 줄",
            "speech": "동료 발화.",
        }
    )
    return c


def _comp(d: Disposition) -> Companion:
    return Companion("철수", d)


class TestInterpretParse:
    def test_parses_llm_json(self) -> None:
        comp = _comp(PRESET_GUARDIAN)
        r = interpret_command(comp, "정찰해", "좁은 틈", client=_client("comply", "scout"))
        assert r.reaction is CommandReaction.COMPLY
        assert r.action is DispoAction.SCOUT
        assert r.reason and r.speech

    def test_refuse_parsed(self) -> None:
        comp = _comp(PRESET_SCOUT)
        r = interpret_command(comp, "혼자 들어가", "함정 의심", client=_client("refuse", "follow"))
        assert r.reaction is CommandReaction.REFUSE


class TestFallback:
    """LLM 실패(예외) → 결정적 성향 폴백. 같은 지시, 성향 다름 → 다른 반응."""

    def _broken(self) -> MagicMock:
        from core.llm.client import LLMError

        c = MagicMock()
        c.generate_json.side_effect = LLMError("down")
        return c

    def test_wise_disloyal_refuses_risky(self) -> None:
        # 지혜↑ + 충성↓ + 위험 지시 → 거부 (정찰꾼: wisdom 80, loyalty 45)
        r = interpret_command(
            _comp(PRESET_SCOUT), "저 좁은 틈으로 먼저 들어가", "어둠", client=self._broken()
        )
        assert r.reaction is CommandReaction.REFUSE
        assert r.action is DispoAction.FOLLOW

    def test_loyal_complies(self) -> None:
        # 충성↑(수호자 loyalty 80) → 순응
        r = interpret_command(
            _comp(PRESET_GUARDIAN), "앞으로 가", "평지", client=self._broken()
        )
        assert r.reaction is CommandReaction.COMPLY

    def test_same_command_different_disposition(self) -> None:
        # ★ 같은 위험 지시, 성향만 다름 → 거부 vs 순응 (Phase 1 핵심)
        cmd, sit = "혼자 좁은 틈에 먼저 들어가", "함정 의심"
        r_scout = interpret_command(_comp(PRESET_SCOUT), cmd, sit, client=self._broken())
        r_guard = interpret_command(_comp(PRESET_GUARDIAN), cmd, sit, client=self._broken())
        assert r_scout.reaction is CommandReaction.REFUSE
        assert r_guard.reaction is not CommandReaction.REFUSE  # 충성↑ → 따름/변형


class TestWhimsyTemperature:
    def test_low_whimsy_consistent(self) -> None:
        assert whimsy_temperature(0) < 0.4

    def test_high_whimsy_unpredictable(self) -> None:
        assert whimsy_temperature(100) > 0.9

    def test_monotonic(self) -> None:
        assert whimsy_temperature(20) < whimsy_temperature(80)


class TestApplyOrder:
    def test_comply_sets_order_and_tick_follows(self) -> None:
        comp = _comp(PRESET_SCOUT)
        apply_order(comp, interpret_command(comp, "정찰", "x", client=_client("comply", "scout")))
        assert comp.current_order is DispoAction.SCOUT
        # 틱 루프가 order를 따른다(성향 자율 대신 명령 수행) — 적이 코앞이어도 scout.
        world = TickWorld(
            companion=comp,
            enemies=[TickEnemy("고블린", pos=(1, 0), hp=30)],
            unexplored_pos=(0, 3),
        )
        results = run_ticks(world, 1)
        assert results[0].action is DispoAction.SCOUT  # default(전투)가 아니라 명령(scout)

    def test_refuse_keeps_autonomy(self) -> None:
        comp = _comp(PRESET_SCOUT)
        apply_order(comp, interpret_command(comp, "돌격", "x", client=_client("refuse", "follow")))
        assert comp.current_order is None  # 거부 → 자율(default_action)
