"""element rules game 연결 정합 — 실제 canon 보강 효과 검증 (★ rules game 2번째)."""

import json
from pathlib import Path

from service.canon.effects import get_essence_attack_element, get_mechanism_element

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def _load() -> dict:
    with open(CANON_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_element_rules_extractable() -> None:
    """element rules 보유 mechanism이 element를 산출 (★ 86건+ bullet)."""
    data = _load()
    extracted = sum(1 for m in data["mechanisms"] if get_mechanism_element(m))
    assert extracted >= 50, f"element 추출 mechanism: {extracted}"


def test_element_rules_boost_essences() -> None:
    """★ made-but-used — 이름 element 매칭 실패 정수를 mechanism element로 보강."""
    data = _load()
    mech_elem = {
        m["name"]: get_mechanism_element(m)
        for m in data["mechanisms"]
        if get_mechanism_element(m)
    }
    boosted = []
    for e in data["essences"]:
        src = e.get("source_monster")
        current = get_essence_attack_element(src) if src else None
        if not current and e.get("name") in mech_elem:
            boosted.append((e["name"], mech_elem[e["name"]]))
    # 흡수 시 element 공격을 새로 얻는 정수 (combat 약점/감응도 연결)
    assert len(boosted) >= 5, f"보강 정수: {len(boosted)}"


def test_boosted_element_in_combat_vocabulary() -> None:
    """보강 element는 combat element vocabulary 정합 (★ 13deef0 약점 매칭)."""
    valid = {"불", "냉기", "전격", "신성력", "빛", "독"}
    data = _load()
    for m in data["mechanisms"]:
        el = get_mechanism_element(m)
        if el:
            assert el in valid, f"{m['name']!r} 비표준 element: {el}"
