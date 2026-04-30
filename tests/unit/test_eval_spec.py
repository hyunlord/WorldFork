"""Day 5: EvalSpec 단위 테스트."""

import json

import pytest

from core.eval.spec import (
    EvalItem,
    EvalSpec,
    latest_version,
    list_categories,
)


class TestEvalItem:
    def test_from_json_line(self) -> None:
        line = json.dumps({
            "id": "test_001",
            "category": "test_cat",
            "version": "v1",
            "prompt": {"system": "s", "user": "u"},
            "expected_behavior": {"x": 1},
            "criteria": "test_cat",
            "context": {"language": "ko"},
        })
        item = EvalItem.from_json_line(line)
        assert item.id == "test_001"
        assert item.prompt["system"] == "s"

    def test_to_from_roundtrip(self) -> None:
        original = EvalItem(
            id="x", category="c", version="v1",
            prompt={"system": "s", "user": "u"},
            expected_behavior={}, criteria="c", context={},
        )
        line = original.to_json_line()
        recovered = EvalItem.from_json_line(line)
        assert recovered.id == original.id


class TestEvalSpec:
    def test_load_real_persona_consistency(self) -> None:
        spec = EvalSpec.load("persona_consistency", "v1")
        assert spec.category == "persona_consistency"
        assert spec.total_count() == 10
        assert spec.fingerprint != ""

    def test_load_real_korean_quality(self) -> None:
        spec = EvalSpec.load("korean_quality", "v1")
        assert spec.total_count() == 10

    def test_load_real_ip_leakage(self) -> None:
        spec = EvalSpec.load("ip_leakage", "v1")
        assert spec.total_count() == 10
        # 게임 속 바바리안 특화
        for item in spec.items:
            forbidden = item.context.get("ip_forbidden_terms", [])
            if forbidden:
                assert any(
                    term in [
                        "비요른", "라프도니아", "정윤강", "던전 앤 스톤",
                        "겜바바", "이한수", "한노아", "에쉬드",
                        "게임 속 바바리안", "Dungeon and Stone",
                    ]
                    for term in forbidden
                ), f"Item {item.id} not WorldFork-specific: {forbidden}"

    def test_load_unknown(self) -> None:
        with pytest.raises(FileNotFoundError):
            EvalSpec.load("does_not_exist", "v1")

    def test_by_id(self) -> None:
        spec = EvalSpec.load("persona_consistency", "v1")
        item = spec.by_id("persona_001")
        assert item is not None
        assert item.id == "persona_001"

    def test_fingerprint_stable(self) -> None:
        s1 = EvalSpec.load("persona_consistency", "v1")
        s2 = EvalSpec.load("persona_consistency", "v1")
        assert s1.fingerprint == s2.fingerprint


class TestListCategories:
    def test_real(self) -> None:
        cats = list_categories()
        assert "persona_consistency" in cats
        assert "korean_quality" in cats
        assert "ip_leakage" in cats
        assert "ai_breakout" in cats
        assert "world_consistency" in cats


class TestLatestVersion:
    def test_existing(self) -> None:
        v = latest_version("persona_consistency")
        assert v == "v1"

    def test_unknown(self) -> None:
        v = latest_version("does_not_exist")
        assert v is None
