"""canon_facts_v3.json character role 정합 검증."""

import json
from collections import Counter
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def test_all_characters_have_valid_role() -> None:
    """모든 character 6 taxonomy 중 1개 보유."""
    from scripts.normalize_character_role import ALL_ROLES

    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for c in data["characters"]:
        role = c.get("role")
        assert role in ALL_ROLES, f"invalid: {c.get('name')} → {role!r}"


def test_no_none_role() -> None:
    """role None 0개 (직전 49.9% → 0%)."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    none_count = sum(1 for c in data["characters"] if not c.get("role"))
    assert none_count == 0


def test_role_distribution_reasonable() -> None:
    """엑스트라 + 주민 합산 전체 30% 이상."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    roles: Counter[str] = Counter(str(c.get("role", "")) for c in data["characters"])
    total = sum(roles.values())
    extra_resident = roles.get("엑스트라", 0) + roles.get("주민", 0)
    assert extra_resident > total * 0.30, f"엑스트라+주민: {extra_resident}/{total}"


def test_version_bumped_to_3_2() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", "")
    assert version not in ("3.0.0", "3.1.0", "v3", "v3.1"), f"version not bumped: {version}"
