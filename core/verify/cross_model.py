"""Cross-Model 강제 (HARNESS_CORE 4장).

verifier != generator 강제.
config/cross_model.yaml 매트릭스 기반.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import yaml

CROSS_MODEL_PATH = Path(__file__).resolve().parents[2] / "config" / "cross_model.yaml"


class CrossModelError(Exception):
    """Cross-Model 제약 위반."""

    pass


@dataclass
class CategorySpec:
    """카테고리별 generator / verifier 정의."""

    category: str
    description: str
    generator_keys: list[str]
    verifier_keys: list[str]
    constraint: str = "verifier != generator"


def _load_matrix() -> dict[str, Any]:
    """Cross-model 매트릭스 YAML 로드."""
    if not CROSS_MODEL_PATH.exists():
        raise CrossModelError(f"Cross-model matrix not found: {CROSS_MODEL_PATH}")
    data = yaml.safe_load(CROSS_MODEL_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise CrossModelError(
            f"Invalid cross-model matrix (expected dict): {type(data).__name__}"
        )
    return data


class CrossModelEnforcer:
    """Cross-Model 제약 강제.

    - check_pair(category, generator, verifier): 위반 시 raise
    - get_verifier_for(category, generator): 카테고리에 맞는 verifier 자동 선택
    """

    def __init__(self, matrix: dict[str, Any] | None = None) -> None:
        if matrix is None:
            matrix = _load_matrix()
        self._matrix = matrix
        enforcement = matrix.get("enforcement", {}) or {}
        self._enabled: bool = bool(enforcement.get("enabled", True))
        on_viol = enforcement.get("on_violation", "error")
        self._on_violation: Literal["error", "warn"] = (
            cast(Literal["error", "warn"], on_viol)
            if on_viol in ("error", "warn")
            else "error"
        )

    def get_category(self, category: str) -> CategorySpec:
        """카테고리 spec 반환."""
        categories = self._matrix.get("categories", {}) or {}
        if category not in categories:
            raise CrossModelError(f"Unknown category: {category}")

        spec = categories[category]

        gen_keys: list[str] = []
        gen_def = spec.get("generator")
        if isinstance(gen_def, dict):
            gen_keys = [str(v) for v in gen_def.values() if isinstance(v, str)]
        elif gen_def == "any":
            gen_keys = []
        elif isinstance(gen_def, str):
            gen_keys = [gen_def]

        ver_keys: list[str] = []
        ver_def = spec.get("verifier", {})
        if isinstance(ver_def, dict):
            ver_keys = [str(v) for v in ver_def.values() if isinstance(v, str)]
        elif isinstance(ver_def, str):
            ver_keys = [ver_def]

        return CategorySpec(
            category=category,
            description=str(spec.get("description", "")),
            generator_keys=gen_keys,
            verifier_keys=ver_keys,
            constraint=str(spec.get("constraint", "verifier != generator")),
        )

    def check_pair(
        self,
        category: str,
        generator: str,
        verifier: str,
    ) -> None:
        """generator + verifier 조합 검증.

        Raises:
            CrossModelError: enforcement on_violation == 'error' 일 때 위반
        """
        if not self._enabled:
            return

        # 카테고리 존재 확인 (등록 안 된 카테고리는 raise)
        self.get_category(category)

        if generator == verifier:
            msg = (
                f"Cross-Model violation: generator == verifier ('{generator}') "
                f"for category '{category}'. "
                f"Use a different model family for verification."
            )
            if self._on_violation == "error":
                raise CrossModelError(msg)
            import warnings

            warnings.warn(msg, stacklevel=2)

    def get_verifier_for(self, category: str, generator: str) -> str:
        """카테고리에 맞는 verifier 자동 선택.

        spec.verifier_keys 순서대로 시도, generator와 다른 첫 키 반환.
        """
        spec = self.get_category(category)

        for v in spec.verifier_keys:
            if v != generator:
                return v

        raise CrossModelError(
            f"No verifier available for category '{category}' "
            f"(generator: {generator}, options: {spec.verifier_keys})"
        )

    def is_enabled(self) -> bool:
        return self._enabled
