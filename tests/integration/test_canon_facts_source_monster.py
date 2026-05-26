"""canon_facts_v3.json source_monster 적용 정합 검증."""
import json
from pathlib import Path

CANON_PATH = Path(".local/canon/canon_facts_v3.json")


def test_all_essences_have_source_monster_field() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for essence in data["essences"]:
        assert "source_monster" in essence, f"missing field: {essence.get('name')}"


def test_source_monster_coverage_above_99pct() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences = data["essences"]
    has_source = sum(1 for e in essences if e.get("source_monster"))
    coverage = has_source / len(essences)
    assert coverage > 0.99, f"coverage: {coverage:.1%}"


def test_version_bumped() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    version = data.get("version", "")
    assert version != "3.0.0", f"version not bumped: {version}"
    assert version != "v3", f"version not bumped: {version}"


def test_specific_essences_x_jeongsoo_pattern() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences = {e["name"]: e for e in data["essences"]}

    samples = [
        ("고블린 정수", "고블린"),
        ("오크 정수", "오크"),
        ("서리늑대 정수", "서리늑대"),
    ]
    for name, expected in samples:
        if name in essences:
            got = essences[name]["source_monster"]
            assert got == expected, f"{name!r}: got {got!r}, expected {expected!r}"


def test_exception_maseok_is_none() -> None:
    with open(CANON_PATH, encoding="utf-8") as f:
        data = json.load(f)

    essences = {e["name"]: e for e in data["essences"]}

    for name in ("9등급 마석", "마석", "7등급 마석"):
        if name in essences:
            got = essences[name]["source_monster"]
            assert got is None, f"{name!r}: expected None, got {got!r}"
