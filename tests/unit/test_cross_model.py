"""Day 4: Cross-Model Enforcer 단위 테스트."""

from typing import Any

import pytest

from core.verify.cross_model import (
    CategorySpec,
    CrossModelEnforcer,
    CrossModelError,
)

# ─── 인라인 mock 매트릭스 ─────────────────────────────────────

MOCK_MATRIX: dict[str, Any] = {
    "categories": {
        "test_category": {
            "description": "Test category",
            "generator": {"tier_0": "claude_code"},
            "verifier": {"primary": "codex", "fallback": "gemini"},
            "constraint": "verifier != generator",
        },
        "any_generator": {
            "description": "Any generator allowed",
            "generator": "any",
            "verifier": {"primary": "codex"},
        },
        "single_string_gen": {
            "description": "Single string generator",
            "generator": "gemini",
            "verifier": {"primary": "codex"},
        },
    },
    "enforcement": {
        "enabled": True,
        "on_violation": "error",
    },
}

DISABLED_MATRIX: dict[str, Any] = {
    **MOCK_MATRIX,
    "enforcement": {"enabled": False},
}


# ─── CrossModelEnforcer init ──────────────────────────────────


class TestCrossModelEnforcerInit:
    def test_init_with_explicit_matrix(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        assert enforcer.is_enabled()

    def test_init_disabled(self) -> None:
        enforcer = CrossModelEnforcer(matrix=DISABLED_MATRIX)
        assert not enforcer.is_enabled()


# ─── get_category ─────────────────────────────────────────────


class TestGetCategory:
    def test_known_category_returns_spec(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        spec = enforcer.get_category("test_category")
        assert isinstance(spec, CategorySpec)
        assert spec.category == "test_category"
        assert "Test category" in spec.description

    def test_generator_keys_parsed_from_dict(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        spec = enforcer.get_category("test_category")
        assert "claude_code" in spec.generator_keys

    def test_verifier_keys_include_primary_and_fallback(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        spec = enforcer.get_category("test_category")
        assert "codex" in spec.verifier_keys
        assert "gemini" in spec.verifier_keys

    def test_any_generator_yields_empty_generator_keys(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        spec = enforcer.get_category("any_generator")
        assert spec.generator_keys == []

    def test_single_string_generator_parsed(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        spec = enforcer.get_category("single_string_gen")
        assert "gemini" in spec.generator_keys

    def test_unknown_category_raises(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        with pytest.raises(CrossModelError, match="Unknown category"):
            enforcer.get_category("does_not_exist")


# ─── check_pair ───────────────────────────────────────────────


class TestCheckPair:
    def test_valid_pair_does_not_raise(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        # claude_code 생성 → codex 검증: 정상
        enforcer.check_pair("test_category", "claude_code", "codex")

    def test_same_generator_and_verifier_raises(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        with pytest.raises(CrossModelError, match="generator == verifier"):
            enforcer.check_pair("test_category", "claude_code", "claude_code")

    def test_same_pair_disabled_does_not_raise(self) -> None:
        enforcer = CrossModelEnforcer(matrix=DISABLED_MATRIX)
        # enforcement disabled → 위반이어도 raise 없음
        enforcer.check_pair("test_category", "claude_code", "claude_code")

    def test_unknown_category_raises(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        with pytest.raises(CrossModelError):
            enforcer.check_pair("unknown_cat", "a", "b")

    def test_different_models_passes(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        enforcer.check_pair("test_category", "claude_code", "gemini")

    def test_violation_message_includes_category(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        with pytest.raises(CrossModelError) as exc:
            enforcer.check_pair("test_category", "codex", "codex")
        assert "test_category" in str(exc.value)


# ─── get_verifier_for ─────────────────────────────────────────


class TestGetVerifierFor:
    def test_returns_primary_when_different_from_generator(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        v = enforcer.get_verifier_for("test_category", "claude_code")
        # primary=codex, codex != claude_code → codex 반환
        assert v == "codex"

    def test_returns_fallback_when_primary_equals_generator(self) -> None:
        matrix: dict[str, Any] = {
            "categories": {
                "cat": {
                    "description": "d",
                    "generator": {"t0": "codex"},
                    "verifier": {"primary": "codex", "fallback": "gemini"},
                },
            },
            "enforcement": {"enabled": True},
        }
        enforcer = CrossModelEnforcer(matrix=matrix)
        v = enforcer.get_verifier_for("cat", "codex")
        assert v == "gemini"

    def test_raises_when_all_verifiers_same_as_generator(self) -> None:
        matrix: dict[str, Any] = {
            "categories": {
                "stuck": {
                    "description": "d",
                    "generator": {"t0": "claude_code"},
                    "verifier": {"primary": "claude_code"},
                },
            },
            "enforcement": {"enabled": True},
        }
        enforcer = CrossModelEnforcer(matrix=matrix)
        with pytest.raises(CrossModelError):
            enforcer.get_verifier_for("stuck", "claude_code")

    def test_unknown_category_raises(self) -> None:
        enforcer = CrossModelEnforcer(matrix=MOCK_MATRIX)
        with pytest.raises(CrossModelError, match="Unknown category"):
            enforcer.get_verifier_for("no_such", "claude_code")


# ─── 실제 config/cross_model.yaml 로드 검증 ──────────────────


def test_real_matrix_loads_without_error() -> None:
    enforcer = CrossModelEnforcer()
    assert enforcer.is_enabled()


def test_real_matrix_game_response_category() -> None:
    enforcer = CrossModelEnforcer()
    spec = enforcer.get_category("game_response")
    assert "claude_code" in spec.generator_keys
    assert "codex" in spec.verifier_keys


def test_real_matrix_rejects_same_model_pair() -> None:
    enforcer = CrossModelEnforcer()
    with pytest.raises(CrossModelError):
        enforcer.check_pair("game_response", "claude_code", "claude_code")


def test_real_matrix_accepts_cross_pair() -> None:
    enforcer = CrossModelEnforcer()
    enforcer.check_pair("game_response", "claude_code", "codex")


def test_real_matrix_all_categories_parseable() -> None:
    enforcer = CrossModelEnforcer()
    for cat in ["game_response", "persona_consistency", "korean_quality", "ip_leakage_judge"]:
        spec = enforcer.get_category(cat)
        assert spec.category == cat
        assert len(spec.description) > 0
