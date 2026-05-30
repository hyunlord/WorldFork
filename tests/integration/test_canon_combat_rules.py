"""canon_facts_v3.json combat mechanism rules 정합 검증."""

import json
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def _combat() -> list[dict]:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [m for m in data["mechanisms"] if m.get("category") == "combat"]


def test_combat_rules_are_str_list() -> None:
    """combat rules는 list[str] (schema 정합)."""
    for m in _combat():
        rules = m.get("rules")
        if rules:
            assert isinstance(rules, list)
            for r in rules:
                assert isinstance(r, str)
                assert r.strip()


def test_combat_rules_coverage_improved() -> None:
    """combat rules coverage — 추출 후 25%+ (직전 10/266 ≈ 3.8%)."""
    combat = _combat()
    filled = sum(1 for m in combat if isinstance(m.get("rules"), list) and m["rules"])
    coverage = filled / len(combat)
    assert coverage > 0.25, f"coverage: {coverage:.1%}"


def test_combat_rules_no_raw_ip() -> None:
    """★ IP 보호 — 산출물 rule에 원본 IP 명칭 미포함."""
    raw_ip = ["라프도니아", "비요른 얀델", "에르웬 포르나치"]
    for m in _combat():
        for rule in m.get("rules", []):
            for ip in raw_ip:
                assert ip not in rule, f"{m.get('name')!r} rule IP 누설: {ip}"


def test_version_bumped_to_3_5() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("version") not in ("3.3.0", "3.4.0"), data.get("version")
