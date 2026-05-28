"""canon_facts_v3.json essence abilities 정합 검증."""

import json
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def test_abilities_schema_valid() -> None:
    """모든 essence abilities — dict 형태 + parsed list 정합."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for essence in data["essences"]:
        abilities = essence.get("abilities")
        if abilities is None or abilities == {}:
            continue
        assert isinstance(abilities, dict), \
            f"{essence.get('name')!r} abilities 타입 X: {type(abilities)}"

        # parsed 정합
        parsed = abilities.get("parsed", [])
        assert isinstance(parsed, list), \
            f"{essence.get('name')!r} parsed list X"
        for p in parsed:
            assert isinstance(p, dict)
            assert "name" in p and "tier" in p
            assert p["tier"] in ("상", "중", "하"), \
                f"{essence.get('name')!r} tier 무효: {p['tier']!r}"


def test_coverage_improved() -> None:
    """abilities filled 19% → 20%+ 정합 (★ 본문 ep 부재 essence는 추출 X).

    실제 결과 22.7% — 본문 명시 essence 제한 정합.
    """
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences = data["essences"]
    filled = 0
    for e in essences:
        a = e.get("abilities")
        if isinstance(a, dict) and len(str(a.get("text", ""))) >= 10:
            filled += 1

    coverage = filled / len(essences)
    assert coverage > 0.20, f"coverage: {coverage:.1%}"


def test_parsed_entries_have_valid_tier() -> None:
    """신규 추출 parsed 정합 tier 상/중/하."""
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    parsed_total = 0
    for e in data["essences"]:
        a = e.get("abilities")
        if not isinstance(a, dict):
            continue
        for p in a.get("parsed", []):
            assert isinstance(p, dict)
            assert p.get("tier") in ("상", "중", "하")
            parsed_total += 1

    # 최소 50개 parsed entry 확보 정합
    assert parsed_total > 50, f"parsed total: {parsed_total}"


def test_version_bumped_to_3_3() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", "")
    assert version not in ("3.0.0", "3.1.0", "3.2.0"), \
        f"version not bumped: {version}"
