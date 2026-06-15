"""AI GM 슬라이스 Phase 3 — 내러티브 턴 전투 단위 테스트.

좌표 없는 라운드(플레이어 + 카이라 성향 + 적), 프리미티브 재사용(명중/치명/출혈/드롭),
처치 시 마석·정수 드롭. 카이라는 성향 마찰(interpret_command, mock). rand 주입으로 결정적.
"""

from collections.abc import Callable
from unittest.mock import MagicMock, patch

from service.content.worldfork import WORLDFORK_PACK
from service.sim.disposition import Companion, DispoAction
from service.sim.disposition_command import CommandReaction, CommandResponse
from service.sim.loot import Inventory
from service.sim.narrative_combat import Foe, player_attack_damage, resolve_round
from service.sim.status import StatusType

KAIRA_DISPOSITION = WORLDFORK_PACK.companion.disposition  # A1.2c: 팩 소유


def _seq(values: list[float]) -> Callable[[], float]:
    box = {"i": 0}

    def nxt() -> float:
        i = box["i"]
        box["i"] = min(i + 1, len(values) - 1)
        return values[i]

    return nxt


def _kaira() -> Companion:
    return Companion("카이라", KAIRA_DISPOSITION, hp=140, max_hp=140, attack=14)


def _reaction(action: DispoAction = DispoAction.CHARGE) -> CommandResponse:
    return CommandResponse(CommandReaction.COMPLY, action, "근거", "내 대검이 나선다!")


def test_weapon_damage_differs() -> None:
    assert player_attack_damage("양손망치") > player_attack_damage("대검")
    assert player_attack_damage("맨손없음") == player_attack_damage("")  # 미지정 기본


def test_player_and_kaira_damage_foe() -> None:
    foe = Foe("고블린", hp=60, max_hp=60, attack=8)
    inv = Inventory()
    with patch(
        "service.sim.narrative_combat.interpret_command", return_value=_reaction()
    ):
        # rand: 플레이어 명중(0.0) + 치명 아님(0.9) ... 적 빗맞음(0.99)
        rr = resolve_round(
            player_action="도끼로 돌격",
            weapon="양손도끼",
            player_hp=120,
            player_max_hp=120,
            player_status=[],
            foe=foe,
            kaira=_kaira(),
            inv=inv,
            situation="전투",
            rand=_seq([0.0, 0.9, 0.99]),
        )
    # 플레이어 16 + 카이라 charge 14 = 30 피해 → 60-30=30
    assert foe.hp == 30
    assert not rr.foe_defeated
    assert rr.kaira_reaction is not None and rr.kaira_reaction.action is DispoAction.CHARGE


def test_foe_hits_and_bleeds_player() -> None:
    foe = Foe("고블린", hp=200, max_hp=200, attack=12)  # 안 죽게
    with patch(
        "service.sim.narrative_combat.interpret_command",
        return_value=_reaction(DispoAction.FOLLOW),  # 카이라 비전투
    ):
        rr = resolve_round(
            player_action="방어",
            weapon="양손도끼",
            player_hp=100,
            player_max_hp=100,
            player_status=[],
            foe=foe,
            kaira=_kaira(),
            inv=Inventory(),
            situation="전투",
            rand=_seq([0.99, 0.0, 0.0]),  # 플레이어 빗맞음, 적 명중(0.0)+출혈(0.0)
        )
    assert rr.player_hp < 100  # 적 피해
    assert any(st.type is StatusType.BLEED for st in rr.player_status)  # 출혈 부여


def test_kill_drops_mana_and_essence() -> None:
    foe = Foe("고블린", hp=10, max_hp=40, attack=8, grade=9, essence_drop="고블린 정수")
    inv = Inventory()
    with patch(
        "service.sim.narrative_combat.interpret_command", return_value=_reaction()
    ):
        rr = resolve_round(
            player_action="도끼로 돌격",
            weapon="양손도끼",
            player_hp=120,
            player_max_hp=120,
            player_status=[],
            foe=foe,
            kaira=_kaira(),
            inv=inv,
            situation="전투",
            rand=_seq([0.0, 0.9]),  # 플레이어 16 피해 → 10-16=0 처치
        )
    assert rr.foe_defeated
    assert inv.stones >= 20  # 9등급 마석
    assert "고블린 정수" in inv.essences  # 정수 수집
    assert any("쓰러뜨" in ln for ln in rr.lines)


def test_aggressive_kaira_refuses_defend() -> None:
    # ★ 성향 마찰 — '방어' 지시에도 저돌적 카이라가 거부하고 돌격(피해 발생).
    foe = Foe("고블린", hp=60, max_hp=60, attack=8)
    refuse_charge = CommandResponse(
        CommandReaction.REFUSE, DispoAction.CHARGE, "물러설 수 없다", "방어라니, 내 도끼가 먼저다!"
    )
    fake = MagicMock(return_value=refuse_charge)
    with patch("service.sim.narrative_combat.interpret_command", fake):
        rr = resolve_round(
            player_action="모두 방어 태세로",
            weapon="대검",
            player_hp=120,
            player_max_hp=120,
            player_status=[],
            foe=foe,
            kaira=_kaira(),
            inv=Inventory(),
            situation="전투",
            rand=_seq([0.99, 0.0]),  # 플레이어 빗맞음 → 적 피해는 카이라만
        )
    assert rr.kaira_reaction is not None
    assert rr.kaira_reaction.reaction is CommandReaction.REFUSE
    assert foe.hp < 60  # 거부했지만 돌격해 피해(성향대로)
