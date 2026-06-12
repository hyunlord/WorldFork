"""V3 수직 슬라이스 Phase 1 — 수정 동굴 타일맵 + 벽 인지 이동 단위 테스트.

타일맵 지형(경계/벽/계단/광원)과, 이동 보조(_advance)가 blocked로 벽을 피하되
blocked 미지정 시 Phase 0 궤적(_step_toward)과 동일함을 검증.
"""

from service.sim.disposition import PRESET_BERSERKER, Companion, DispoAction
from service.sim.disposition_tick import (
    TickContext,
    TickEnemy,
    _advance,
    _step_away,
    _step_toward,
    act_companion,
)
from service.sim.dungeon_map import crystal_cave


class TestDungeonMap:
    def test_dimensions(self) -> None:
        m = crystal_cave()
        assert (m.width, m.height) == (12, 8)

    def test_border_is_wall(self) -> None:
        m = crystal_cave()
        assert m.is_wall(0, 0) and m.is_wall(11, 7)
        assert m.is_blocked((0, 4))  # 좌측 벽
        assert not m.is_blocked((2, 2))  # 내부 바닥

    def test_out_of_bounds_blocked(self) -> None:
        m = crystal_cave()
        assert m.is_blocked((-1, 3)) and m.is_blocked((12, 3))

    def test_stair_present_and_walkable(self) -> None:
        m = crystal_cave()
        stair = m.stair()
        assert stair is not None
        assert not m.is_blocked(stair)  # 계단은 통과 가능
        assert m.char(stair[0], stair[1]) == ">"

    def test_crystals_emit_light(self) -> None:
        m = crystal_cave()
        assert len(m.crystals()) >= 2
        # 수정 자리는 밝다.
        cx, cy = m.crystals()[0]
        assert m.is_lit(cx, cy)
        # 광원 반경 밖인 바닥 칸이 있어 어둠이 실재한다(광원 메커니즘).
        dark = [
            (x, y)
            for y, row in enumerate(m.grid)
            for x, c in enumerate(row)
            if c in (".", ">") and not m.is_lit(x, y)
        ]
        assert dark, "광원 반경 밖 어두운 바닥이 있어야 한다"

    def test_center_obstacle(self) -> None:
        # 가운데 2x2 장애물 — 우회로(2·5·6행)는 트여 있음.
        m = crystal_cave()
        assert m.is_blocked((5, 3)) and m.is_blocked((6, 4))
        assert not m.is_blocked((5, 2))  # 윗통로 열림


class TestAdvance:
    def test_no_blocked_matches_step_toward(self) -> None:
        # blocked=None → Phase 0 _step_toward와 바이트 동일(궤적 불변).
        for src, dst in [((0, 0), (3, 0)), ((2, 2), (2, 5)), ((4, 1), (1, 3))]:
            assert _advance(src, dst, None) == _step_toward(src, dst)

    def test_no_blocked_matches_step_away(self) -> None:
        for src, threat in [((2, 2), (0, 2)), ((2, 2), (2, 0)), ((2, 2), (2, 2))]:
            assert _advance(src, threat, None, away=True) == _step_away(src, threat)

    def test_detours_around_wall(self) -> None:
        m = crystal_cave()
        # (4,3)에서 동쪽(5,3)은 벽 → x 막힘, y로 우회.
        nxt = _advance((4, 3), (8, 3), m.is_blocked)
        assert nxt != (5, 3)
        assert not m.is_blocked(nxt)

    def test_stops_when_fully_blocked(self) -> None:
        m = crystal_cave()
        # 좌상단 구석 (1,1): 서/북이 벽이라 (0,0) 쪽으론 못 감 → 제자리.
        assert _advance((1, 1), (0, 0), m.is_blocked) == (1, 1)


class TestCompanionRespectsWalls:
    def test_charge_never_enters_wall(self) -> None:
        # 벽 너머 적으로 돌격해도 동료가 벽 칸에 들어가지 않는다.
        m = crystal_cave()
        comp = Companion("전사", PRESET_BERSERKER, pos=(4, 3), attack=16)
        ctx = TickContext(
            [TickEnemy("고블린", pos=(8, 3), hp=40)], blocked=m.is_blocked
        )
        action, _ = act_companion(comp, ctx)
        assert action is DispoAction.CHARGE
        assert not m.is_blocked(comp.pos)  # 이동 후에도 바닥
