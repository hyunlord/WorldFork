"""V3 Phase 0 — 성향 코어 단위 테스트.

성향 → 기본 행동 매핑(default_action)이 결정적이고, 성향이 다르면 다른 행동을
고르는지 검증(LLM 없이). 틱 루프에서 저돌적 동료와 신중한 동료의 궤적이 갈리는가.
"""

import pytest

from service.sim.disposition import (
    PRESET_BERSERKER,
    PRESET_GUARDIAN,
    PRESET_SCOUT,
    Companion,
    DispoAction,
    Disposition,
    WorldView,
    default_action,
)
from service.sim.disposition_tick import (
    TickEnemy,
    TickWorld,
    run_ticks,
    step_tick,
)


class TestDispositionModel:
    def test_axes_default_mid(self) -> None:
        d = Disposition()
        assert d.loyalty == d.aggression == d.wisdom == d.whimsy == d.bond == 50

    def test_axis_range_validated(self) -> None:
        with pytest.raises(ValueError):
            Disposition(aggression=120)
        with pytest.raises(ValueError):
            Disposition(bond=-1)

    def test_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        d = Disposition()
        with pytest.raises(FrozenInstanceError):
            d.aggression = 90  # type: ignore[misc]


class TestDefaultAction:
    """성향 → 행동 — 같은 상황, 다른 성향 = 다른 선택 (Phase 0 핵심)."""

    def test_aggressive_charges(self) -> None:
        w = WorldView(enemy_near=True, enemy_distance=3)
        assert default_action(Disposition(aggression=85), w) is DispoAction.CHARGE

    def test_cautious_keeps_range(self) -> None:
        w = WorldView(enemy_near=True, enemy_distance=3)
        assert default_action(Disposition(aggression=25), w) is DispoAction.RANGED

    def test_same_enemy_split_by_aggression(self) -> None:
        # ★ 같은 적, 다른 저돌성 → 돌격 vs 원거리 (성향이 좌우)
        w = WorldView(enemy_near=True, enemy_distance=3)
        assert default_action(PRESET_BERSERKER, w) is DispoAction.CHARGE
        assert default_action(PRESET_SCOUT, w) is DispoAction.RANGED

    def test_wise_scouts_unexplored(self) -> None:
        w = WorldView(unexplored=True)
        assert default_action(PRESET_SCOUT, w) is DispoAction.SCOUT
        # 지혜 낮으면 정찰 안 함 → 추종
        assert default_action(Disposition(wisdom=30), w) is DispoAction.FOLLOW

    def test_bonded_rescues_ally(self) -> None:
        w = WorldView(enemy_near=True, enemy_distance=2, ally_in_danger=True)
        # 유대↑ → 전투보다 구원 우선
        assert default_action(PRESET_GUARDIAN, w) is DispoAction.RESCUE
        # 유대 낮으면 구원 안 가고 전투/원거리
        assert default_action(Disposition(bond=30, aggression=85), w) is DispoAction.CHARGE

    def test_idle_follows(self) -> None:
        assert default_action(Disposition(), WorldView()) is DispoAction.FOLLOW

    def test_mid_aggression_uses_distance(self) -> None:
        adj = WorldView(enemy_near=True, enemy_distance=1)
        far = WorldView(enemy_near=True, enemy_distance=5)
        assert default_action(Disposition(aggression=50), adj) is DispoAction.CHARGE
        assert default_action(Disposition(aggression=50), far) is DispoAction.RANGED


class TestTickLoop:
    def _world(self, dispo: Disposition) -> TickWorld:
        return TickWorld(
            companion=Companion("동료", dispo, pos=(0, 0), attack=12),
            enemies=[TickEnemy("고블린", pos=(5, 0), hp=30)],
            player_pos=(0, 0),
            unexplored_pos=(0, 5),
        )

    def test_berserker_closes_and_strikes(self) -> None:
        # 저돌적 동료: 적에게 돌진 → 붙으면 타격(적 HP 감소)
        w = self._world(PRESET_BERSERKER)
        results = run_ticks(w, 8)
        assert any(r.action is DispoAction.CHARGE for r in results)
        assert w.enemies[0].hp < 30  # 결국 타격함
        # 저돌성 85 ≥ 80 → 강타(결정적)
        assert any("강타" in r.note for r in results)

    def test_scout_goes_to_unexplored(self) -> None:
        # 신중·영민 동료: 적이 멀면 정찰로 미탐색 지점 향함
        w = TickWorld(
            companion=Companion("정찰꾼", PRESET_SCOUT, pos=(0, 0)),
            enemies=[],  # 적 없음 → 정찰 우선
            player_pos=(0, 0),
            unexplored_pos=(0, 4),
        )
        results = run_ticks(w, 6)
        assert any(r.action is DispoAction.SCOUT for r in results)
        # 정찰 지점 도달 후 미탐색 해소(완료) → 이후 플레이어 곁으로 복귀(자율).
        assert w.unexplored_pos is None
        assert any(r.action is DispoAction.FOLLOW for r in results)

    def test_different_disposition_different_trajectory(self) -> None:
        # ★ Phase 0 핵심: 같은 세계, 성향만 다르면 궤적이 갈린다(LLM 없이)
        wb = self._world(PRESET_BERSERKER)
        ws = self._world(PRESET_SCOUT)
        run_ticks(wb, 4)
        run_ticks(ws, 4)
        # 저돌적은 적(5,0) 쪽으로, 신중한은 적과 거리 유지/정찰 → 위치 다름
        assert wb.companion.pos != ws.companion.pos

    def test_deterministic(self) -> None:
        # 같은 입력 → 같은 결과 (random 없음 — Phase 0 결정적)
        a = self._world(PRESET_BERSERKER)
        b = self._world(PRESET_BERSERKER)
        ra = [(r.action, r.companion_pos) for r in run_ticks(a, 6)]
        rb = [(r.action, r.companion_pos) for r in run_ticks(b, 6)]
        assert ra == rb

    def test_step_tick_increments(self) -> None:
        w = self._world(PRESET_BERSERKER)
        r = step_tick(w)
        assert r.tick == 1 and w.tick == 1
