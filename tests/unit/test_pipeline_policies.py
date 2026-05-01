"""W2 D1 작업 2: Pipeline policies 테스트."""

import pytest

from service.pipeline.policies import DEFAULT_LAYER2_POLICY, Layer2Policy


class TestLayer2Policy:
    def test_default_values(self) -> None:
        p = DEFAULT_LAYER2_POLICY
        assert p.threshold_score == 70
        assert p.max_retries == 3
        assert p.plan_verify_threshold == 80
        assert p.use_mechanical_first is True
        assert p.ip_leakage_strict is True
        assert p.ip_masking_required is True

    def test_custom_policy(self) -> None:
        p = Layer2Policy(threshold_score=90, max_retries=5)
        assert p.threshold_score == 90
        assert p.max_retries == 5
        assert p.use_mechanical_first is True

    def test_immutable(self) -> None:
        p = DEFAULT_LAYER2_POLICY
        with pytest.raises((AttributeError, Exception)):
            p.threshold_score = 100  # type: ignore[misc]

    def test_fallback_chain_local_first(self) -> None:
        p = DEFAULT_LAYER2_POLICY
        assert p.fallback_chain[0].startswith("qwen")
        assert p.fallback_chain[1].startswith("qwen")
        assert p.fallback_chain[-1] == "user_notification"

    def test_plan_threshold_stricter_than_game(self) -> None:
        p = DEFAULT_LAYER2_POLICY
        assert p.plan_verify_threshold > p.threshold_score
