"""V3 수직 슬라이스 Phase 2 — enemy_step(적 반격) + HP 0 처리 단위 테스트.

적이 근접 시 명중/빗맞음/피해/출혈로 반격하는가(일방 전투 아님), 출혈이 지속 피해를
주는가, 멀면 접근(벽 인지)하는가, HP 0 동료는 전투불능(party_step 건너뜀)이고 비요른
HP 0이면 패배 상태인가. ★ 퍼머데스·세이브·명부는 범위 밖(구현하지 않음).
"""

from collections.abc import Callable

from service.sim.disposition import PRESET_BERSERKER, PRESET_GUARDIAN, Companion
from service.sim.disposition_tick import TickEnemy
from service.sim.dungeon_map import crystal_cave
from service.sim.party import PartyWorld, enemy_step, party_step
from service.sim.status import StatusType


def _seq(values: list[float]) -> Callable[[], float]:
    """결정적 rand — 호출마다 다음 값(부족하면 마지막 값 반복)."""
    box = {"i": 0}

    def nxt() -> float:
        i = box["i"]
        box["i"] = min(i + 1, len(values) - 1)
        return values[i]

    return nxt


def _one(pos: tuple[int, int], hp: int = 100) -> PartyWorld:
    """동료 1명(수호자) — 플레이어는 멀리 둬 적이 동료를 노리게."""
    return PartyWorld(
        companions=[Companion("수호자", PRESET_GUARDIAN, pos=pos, hp=hp, max_hp=100)],
        player_pos=(40, 40),
        player_hp=100,
    )


class TestEnemyAttack:
    def test_adjacent_hit_deals_damage(self) -> None:
        w = _one((5, 5))
        w.enemies = [TickEnemy("고블린", pos=(5, 6), hp=30, attack=12)]
        notes = enemy_step(w, rand=_seq([0.0, 0.9]))  # 명중, 출혈 X
        assert w.companions[0].hp == 88
        assert any("명중" in n for n in notes)

    def test_miss_no_damage(self) -> None:
        w = _one((5, 5))
        w.enemies = [TickEnemy("고블린", pos=(5, 6), hp=30, attack=12)]
        notes = enemy_step(w, rand=_seq([0.99]))  # 빗맞음
        assert w.companions[0].hp == 100
        assert any("빗나감" in n for n in notes)

    def test_bleed_applied_and_ticks(self) -> None:
        w = _one((5, 5))
        w.enemies = [TickEnemy("고블린", pos=(5, 6), hp=30, attack=10)]
        enemy_step(w, rand=_seq([0.0, 0.0]))  # 명중 + 출혈 부여
        comp = w.companions[0]
        assert any(s.type is StatusType.BLEED for s in comp.status)
        hp_after_hit = comp.hp  # 90
        # 다음 틱 — 출혈 지속 피해(공격 빗맞춰도 출혈은 깎인다).
        enemy_step(w, rand=_seq([0.99]))
        assert comp.hp < hp_after_hit

    def test_distant_enemy_moves_closer(self) -> None:
        w = _one((5, 5))
        w.enemies = [TickEnemy("고블린", pos=(5, 9), hp=30, attack=10)]
        before = w.enemies[0].pos
        enemy_step(w, rand=_seq([0.0]))
        assert w.enemies[0].pos != before  # 접근(공격 사거리 밖)
        assert w.companions[0].hp == 100  # 아직 피해 없음

    def test_enemy_respects_walls_on_approach(self) -> None:
        m = crystal_cave()
        w = PartyWorld(
            companions=[Companion("수호자", PRESET_GUARDIAN, pos=(1, 5), hp=100)],
            player_pos=(40, 40),
            blocked=m.is_blocked,
        )
        w.enemies = [TickEnemy("고블린", pos=(8, 5), hp=30, attack=10)]
        enemy_step(w, rand=_seq([0.0]))
        assert not m.is_blocked(w.enemies[0].pos)  # 벽으로 이동 안 함


class TestHpZero:
    def test_companion_downed_skipped_in_party_step(self) -> None:
        w = PartyWorld(
            companions=[
                Companion("전사", PRESET_BERSERKER, pos=(0, 0), hp=0, max_hp=100),
                Companion("수호자", PRESET_GUARDIAN, pos=(0, 1), hp=100, max_hp=100),
            ],
        )
        assert w.companions[0].downed
        results = party_step(w)
        actors = {r.note.split(":")[0] for r in results}
        assert "전사" not in actors  # 전투불능 동료는 행동 안 함
        assert "수호자" in actors

    def test_enemy_skips_downed_target(self) -> None:
        # 쓰러진 동료(hp0) 옆 적은 그를 노리지 않고, 생존 대상으로 이동.
        w = PartyWorld(
            companions=[
                Companion("쓰러짐", PRESET_GUARDIAN, pos=(5, 5), hp=0, max_hp=100),
                Companion("생존", PRESET_GUARDIAN, pos=(20, 20), hp=100, max_hp=100),
            ],
            player_pos=(40, 40),
        )
        w.enemies = [TickEnemy("고블린", pos=(5, 6), hp=30, attack=10)]
        enemy_step(w, rand=_seq([0.0]))
        assert w.companions[0].hp == 0  # 쓰러진 동료는 추가 피해 없음
        assert w.enemies[0].pos != (5, 6)  # 생존 대상 쪽으로 이동

    def test_player_zero_is_defeat(self) -> None:
        w = _one((40, 41), hp=100)  # 동료 멀리, 적이 플레이어 옆
        w.player_hp = 8
        w.enemies = [TickEnemy("고블린", pos=(40, 40), hp=30, attack=12)]
        assert not w.defeat
        enemy_step(w, rand=_seq([0.0, 0.9]))  # 플레이어 명중 12 → 0 클램프
        assert w.player_hp == 0
        assert w.defeat  # 슬라이스 패배

    def test_hp_clamped_nonneg(self) -> None:
        w = _one((5, 5), hp=3)
        w.enemies = [TickEnemy("고블린", pos=(5, 6), hp=30, attack=50)]
        enemy_step(w, rand=_seq([0.0, 0.9]))
        assert w.companions[0].hp == 0  # 음수 방치 금지 — 0 클램프
