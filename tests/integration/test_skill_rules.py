"""canon_facts skill mechanism rules 정합 검증 (★ generalize 활용 — SKILL element 보강)."""

import json
from pathlib import Path

from scripts.extract_mechanism_rules import get_extract_system

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def _by_category(cat: str) -> list[dict]:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [m for m in data["mechanisms"] if m.get("category") == cat]


def test_skill_extract_system() -> None:
    """★ skill 전용 prompt — combat fallback 아님 (element 가이드 보강)."""
    system = get_extract_system("skill")
    assert "스킬" in system
    assert "element" in system  # ★ 검기/화염 등 element 보강
    assert system != get_extract_system("combat")
    assert system != get_extract_system("magic")


def test_skill_rules_are_str_list() -> None:
    """skill rules는 list[str] (★ ba9be86 형식 정합)."""
    for m in _by_category("skill"):
        rules = m.get("rules")
        if rules:
            assert isinstance(rules, list)
            for r in rules:
                assert isinstance(r, str) and r.strip()


def test_skill_rules_coverage_improved() -> None:
    """skill rules coverage 향상 (★ 직전 48/1317 ≈ 3.6%)."""
    skill = _by_category("skill")
    filled = sum(1 for m in skill if isinstance(m.get("rules"), list) and m["rules"])
    assert filled / len(skill) > 0.10, f"coverage: {filled}/{len(skill)}"


def test_combat_rules_preserved() -> None:
    """★ 회귀 — combat rules 보존 (d2d6706, 93/266)."""
    combat = _by_category("combat")
    filled = sum(1 for m in combat if isinstance(m.get("rules"), list) and m["rules"])
    assert filled >= 90, f"combat rules 손실: {filled}"


def test_magic_rules_preserved() -> None:
    """★ 회귀 — magic rules 보존 (ba9be86, 383/1150)."""
    magic = _by_category("magic")
    filled = sum(1 for m in magic if isinstance(m.get("rules"), list) and m["rules"])
    assert filled >= 380, f"magic rules 손실: {filled}"


def test_skill_rules_no_raw_ip() -> None:
    """★ IP 보호 — skill rule 산출물에 원본 IP 명칭 미포함 (mask_ip)."""
    raw_ip = ["라프도니아", "비요른 얀델", "에르웬 포르나치"]
    for m in _by_category("skill"):
        for rule in m.get("rules", []):
            for ip in raw_ip:
                assert ip not in rule, f"{m.get('name')!r} IP 누설: {ip}"


def test_version_bumped() -> None:
    """skill 추출 후 version bump (★ 3.6.0 → 3.7.0)."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("version") not in ("3.5.0", "3.6.0"), data.get("version")
