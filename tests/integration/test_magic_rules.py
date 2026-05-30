"""canon_facts magic mechanism rules 정합 검증 (★ extract generalize)."""

import json
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def _by_category(cat: str) -> list[dict]:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [m for m in data["mechanisms"] if m.get("category") == cat]


def test_magic_rules_are_str_list() -> None:
    """magic rules는 list[str] (schema 정합)."""
    for m in _by_category("magic"):
        rules = m.get("rules")
        if rules:
            assert isinstance(rules, list)
            for r in rules:
                assert isinstance(r, str) and r.strip()


def test_magic_rules_coverage_improved() -> None:
    """magic rules coverage 향상 (직전 61/1150 ≈ 5.3%)."""
    magic = _by_category("magic")
    filled = sum(1 for m in magic if isinstance(m.get("rules"), list) and m["rules"])
    assert filled / len(magic) > 0.10, f"coverage: {filled}/{len(magic)}"


def test_combat_rules_preserved() -> None:
    """★ generalize 회귀 — combat rules 보존 (d2d6706, 93/266)."""
    combat = _by_category("combat")
    filled = sum(1 for m in combat if isinstance(m.get("rules"), list) and m["rules"])
    assert filled >= 90, f"combat rules 손실: {filled}"


def test_magic_rules_no_raw_ip() -> None:
    """★ IP 보호 — magic rule 산출물에 원본 IP 명칭 미포함."""
    raw_ip = ["라프도니아", "비요른 얀델", "에르웬 포르나치"]
    for m in _by_category("magic"):
        for rule in m.get("rules", []):
            for ip in raw_ip:
                assert ip not in rule, f"{m.get('name')!r} IP 누설: {ip}"


def test_version_bumped_to_3_6() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("version") not in ("3.4.0", "3.5.0"), data.get("version")
