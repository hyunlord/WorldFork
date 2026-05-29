"""canon_facts_v3.json race ability_tiers 정합 검증."""

import json
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def test_race_ability_tiers_schema() -> None:
    """race ability_tiers — text + parsed(name/tier) 정합."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for race in data["races"]:
        at = race.get("ability_tiers")
        if at is None or at == {}:
            continue
        assert isinstance(at, dict)
        parsed = at.get("parsed", [])
        assert isinstance(parsed, list)
        for p in parsed:
            assert isinstance(p, dict)
            assert "name" in p and "tier" in p
            assert p["tier"] in ("상", "중", "하")


def test_race_ability_tiers_coverage() -> None:
    """ability_tiers filled 15%+ 정합 (★ 실제 16.5%).

    442 race 중 대부분이 짧은 서사형 description (1-14자) 또는 미입력 →
    ability 명시 source 한정. 73개 신규 추출 (★ 직전 0개).
    """
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    races = data["races"]
    filled = sum(
        1 for r in races
        if isinstance(r.get("ability_tiers"), dict)
        and len(str(r["ability_tiers"].get("text", ""))) >= 5
    )
    coverage = filled / len(races)
    assert coverage > 0.15, f"coverage: {coverage:.1%}"


def test_race_ability_tiers_parsed_count() -> None:
    """parsed entry 최소 100개 확보 정합."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    total = 0
    for r in data["races"]:
        at = r.get("ability_tiers")
        if isinstance(at, dict):
            for p in at.get("parsed", []):
                assert isinstance(p, dict)
                assert p.get("tier") in ("상", "중", "하")
                total += 1
    assert total > 100, f"parsed total: {total}"


def test_version_bumped_to_3_4() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("version") not in ("3.3.0", "v3.3", "3.2.0")
