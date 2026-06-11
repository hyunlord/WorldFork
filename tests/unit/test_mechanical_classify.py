"""Mechanical 사전분류 단위 테스트 — 0토큰 규칙(방위 이동·휴식) + 오탐 fall-through.

★ 원칙 #5(Mechanical 우선): 명백한 행동만 즉시 분류, 모호하면 None(LLM 위임).
오탐 방지 검증이 핵심 — 동료/동굴/서재 등은 방위로 오인하면 안 된다.
"""

from service.sim.intent_classifier import mechanical_classify
from service.sim.types import PlayerActionType


class TestMechanicalMove:
    def test_north(self) -> None:
        m = mechanical_classify("북쪽으로 간다")
        assert m is not None
        assert m.matched_action == PlayerActionType.MOVE.value
        assert m.entities.direction == "north"
        assert m.confidence >= 0.9

    def test_south_idiom(self) -> None:
        m = mechanical_classify("남쪽 통로로 이동한다")
        assert m is not None
        assert m.entities.direction == "south"

    def test_east_euro(self) -> None:
        m = mechanical_classify("동으로 나아간다")
        assert m is not None
        assert m.entities.direction == "east"

    def test_west(self) -> None:
        m = mechanical_classify("서쪽으로 걸어간다")
        assert m is not None
        assert m.entities.direction == "west"


class TestMechanicalRest:
    def test_rest_keyword(self) -> None:
        m = mechanical_classify("잠시 휴식을 취한다")
        assert m is not None
        assert m.matched_action == PlayerActionType.REST.value

    def test_sleep(self) -> None:
        m = mechanical_classify("바닥에 드러눕는다")
        assert m is not None
        assert m.matched_action == PlayerActionType.REST.value


class TestMechanicalAttack:
    def test_attack_verb(self) -> None:
        m = mechanical_classify("고블린을 공격한다")
        assert m is not None
        assert m.matched_action == PlayerActionType.ATTACK.value

    def test_axe_swing(self) -> None:
        m = mechanical_classify("도끼를 휘두른다")
        assert m is not None
        assert m.matched_action == PlayerActionType.ATTACK.value

    def test_slash(self) -> None:
        m = mechanical_classify("칼날늑대를 베어버린다")
        assert m is not None
        assert m.matched_action == PlayerActionType.ATTACK.value

    def test_dodge_not_attack(self) -> None:
        # 공격을 피하는 맥락 → 공격 아님(LLM 위임).
        assert mechanical_classify("적의 공격을 피한다") is None

    def test_flee_not_attack(self) -> None:
        assert mechanical_classify("공격을 막고 도망친다") is None


class TestFallThrough:
    """오탐 방지 — 모호/비방위는 None(LLM 위임)."""

    def test_companion_not_east(self) -> None:
        # '동료에게 간다' — '동' 있으나 방위 접미 없음 → 오탐 금지.
        assert mechanical_classify("동료에게 간다") is None

    def test_cave_not_east(self) -> None:
        # '동굴' — 방위 아님.
        assert mechanical_classify("동굴을 살펴본다") is None

    def test_direction_without_verb(self) -> None:
        # 방위만, 이동 동사 없음 → 모호 → LLM.
        assert mechanical_classify("북쪽 벽이 차갑다") is None

    def test_freeform_action(self) -> None:
        assert mechanical_classify("벽의 이끼를 핥아본다") is None

    def test_empty(self) -> None:
        assert mechanical_classify("") is None
