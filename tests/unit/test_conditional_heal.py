"""HP 임계 회복 — enemy 조건부 회복 강도 매핑 단위 테스트 (★ rules game 5번째).

진단 정정: player 정수 조건부 회복은 0건이나, enemy_ai.select_ability에 HP<30%
회복 우선(조건 체크)이 실재 → enemy 회복량을 canon mechanism 강도로 정밀화 (case A).
"""

from __future__ import annotations

from service.canon.effects import extract_conditional_heal
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Mechanism


def _make_index() -> EntityIndex:
    return EntityIndex(
        CanonFacts(
            essences=[],
            characters=[],
            locations=[],
            races=[],
            mechanisms=[
                Mechanism(
                    name="회복(최상급)",
                    category="combat",
                    description="상급 회복",
                    rules=["신체 빠르게 재생"],
                ),
                Mechanism(
                    name="회복(중)",
                    category="combat",
                    description="중급 회복",
                    rules=["포션 사용 시 신체 재생"],
                ),
                Mechanism(
                    name="강타",
                    category="skill",
                    description="물리 일격",
                    rules=["물리 피해"],
                ),
            ],
        )
    )


def test_heal_ratio_full() -> None:
    """완전 회복 → 1.0 (광폭 패턴)."""
    m = {"name": "광폭 패턴", "rules": ["시간 초과 시 체력 완전 회복"]}
    assert extract_conditional_heal(m) == 1.0


def test_heal_ratio_tiers() -> None:
    """최상급·대폭·빠르게 0.5 / 중 0.3 / 기본 0.2."""
    assert extract_conditional_heal({"name": "회복(최상급)", "rules": ["빠르게 재생"]}) == 0.5
    assert extract_conditional_heal({"name": "회복(중)", "rules": ["신체 재생"]}) == 0.3
    assert extract_conditional_heal({"name": "[초재생]", "rules": ["2분간 재생"]}) == 0.2


def test_no_heal_ratio() -> None:
    """회복 무관 rule → 0.0."""
    assert extract_conditional_heal({"name": "강타", "rules": ["물리 피해"]}) == 0.0
    assert extract_conditional_heal({"rules": []}) == 0.0
    assert extract_conditional_heal({}) == 0.0


def test_invalid_rules_type() -> None:
    """rules가 list 아님 → name만으로 판정 (방어)."""
    assert extract_conditional_heal({"name": "회복기", "rules": "not a list"}) == 0.2


def test_lookup_mechanism_heal() -> None:
    """★ EntityIndex — ability name → 동명 mechanism 회복 강도."""
    idx = _make_index()
    assert idx.lookup_mechanism_heal("회복(최상급)") == 0.5
    assert idx.lookup_mechanism_heal("회복(중)") == 0.3
    assert idx.lookup_mechanism_heal("강타") == 0.0  # 회복 아님
    assert idx.lookup_mechanism_heal("존재안함") == 0.0  # 미등록
