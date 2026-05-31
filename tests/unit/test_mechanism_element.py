"""mechanism element rules → 공격 element 추출 단위 테스트 (★ rules game 연결)."""

from __future__ import annotations

from service.canon.effects import essence_to_slot, get_mechanism_element
from service.canon.entity_index import EntityIndex
from service.canon.schema import CanonFacts, Essence, Mechanism


def _make_index() -> EntityIndex:
    return EntityIndex(
        CanonFacts(
            essences=[Essence(name="불의 보주", grade=3, source_monster="불의 보주")],
            characters=[],
            locations=[],
            races=[],
            mechanisms=[
                Mechanism(
                    name="불의 보주",
                    category="magic",
                    description="화염 마법 구체",
                    rules=["화염 속성", "광역 폭발"],
                ),
                Mechanism(
                    name="강타",
                    category="skill",
                    description="물리 일격",
                    rules=["물리 피해", "넉백"],
                ),
            ],
        )
    )


def test_fire_element_rule() -> None:
    """불 속성 rule → 불."""
    assert get_mechanism_element({"rules": ["불 속성 공격", "잔여 마력 소모"]}) == "불"
    assert get_mechanism_element({"rules": ["화염 속성"]}) == "불"


def test_holy_element_rule() -> None:
    """신성 rule → 신성력 ('속성' 없는 명백한 element 명사 단독)."""
    assert get_mechanism_element({"rules": ["신성력 부여"]}) == "신성력"


def test_element_attribute_bullets() -> None:
    """빛/전격/냉기/독 속성 bullet 매핑."""
    assert get_mechanism_element({"rules": ["빛 속성"]}) == "빛"
    assert get_mechanism_element({"rules": ["전격 속성"]}) == "전격"
    assert get_mechanism_element({"rules": ["냉기 속성"]}) == "냉기"
    assert get_mechanism_element({"rules": ["독 속성"]}) == "독"


def test_no_element_rule() -> None:
    """element 무관 rule → 빈 문자열."""
    assert get_mechanism_element({"rules": ["물리 공격"]}) == ""
    assert get_mechanism_element({"rules": []}) == ""
    assert get_mechanism_element({}) == ""


def test_false_positive_blocked() -> None:
    """★ 오탐 차단 — 일반 문장·미지원 element는 빈 문자열."""
    # '빛을 꺼트림' — '속성' 없고 '빛'은 다의어 standalone 제외
    assert get_mechanism_element({"rules": ["붉게 달아오른 수정이 빛을 꺼트림"]}) == ""
    # 미지원 element (땅/혼돈/수)
    assert get_mechanism_element({"rules": ["땅 속성 대상 무효"]}) == ""
    assert get_mechanism_element({"rules": ["혼돈 속성 피해"]}) == ""
    # element 무관 서술
    assert get_mechanism_element({"rules": ["불가한 영혼인 경우 제거됨"]}) == ""


def test_invalid_rules_type() -> None:
    """rules가 list[str] 아님 → 빈 문자열 (방어)."""
    assert get_mechanism_element({"rules": "not a list"}) == ""
    assert get_mechanism_element({"rules": [123, None]}) == ""


def test_essence_to_slot_extra_elements() -> None:
    """★ essence_to_slot 보강 — extra_attack_elements 병합 (중복 제거)."""
    # source_monster 이름 매칭 X → extra로만 element 획득
    slot = essence_to_slot({"name": "불의 보주"}, extra_attack_elements=["불"])
    assert "불" in slot.attack_elements

    # source_monster 매칭 element와 extra 중복 → 1개만
    slot2 = essence_to_slot(
        {"name": "화룡", "source_monster": "화룡 정수"},
        extra_attack_elements=["불"],
    )
    assert slot2.attack_elements.count("불") == 1


def test_essence_to_slot_no_extra() -> None:
    """extra 미지정 → 기존 source_monster 동작 보존 (회귀)."""
    slot = essence_to_slot({"name": "철골렘", "source_monster": "철골렘"})
    assert slot.attack_elements == []  # 이름에 element keyword 없음


def test_lookup_mechanism_element() -> None:
    """★ EntityIndex — essence 동명 mechanism element rules → element."""
    idx = _make_index()
    assert idx.lookup_mechanism_element("불의 보주") == "불"  # 화염 속성 rule
    assert idx.lookup_mechanism_element("강타") == ""  # element rule 없음
    assert idx.lookup_mechanism_element("존재안함") == ""  # 미등록


def test_lookup_feeds_essence_slot() -> None:
    """★ 흡수 연결 — lookup element가 essence_to_slot 보강에 전달."""
    idx = _make_index()
    element = idx.lookup_mechanism_element("불의 보주")
    raw = idx.get_raw_essence("불의 보주")
    assert raw is not None
    slot = essence_to_slot(raw, extra_attack_elements=[element] if element else None)
    assert "불" in slot.attack_elements  # 이름 매칭 X였으나 mechanism으로 보강
