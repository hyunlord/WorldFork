"""Eval Set 스키마 + 버전 관리 (HARNESS_CORE 5장).

Day 5: EvalSpec / EvalItem.
이후:
  - Day 6: AI Playtester가 auto_added/에 자동 추가
  - Tier 1+: SQL 기반 영속화
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parents[2] / "evals"


@dataclass
class EvalItem:
    """평가 항목 (HARNESS_CORE 5.2)."""

    id: str
    category: str
    version: str
    prompt: dict[str, str]                     # {system, user}
    expected_behavior: dict[str, Any]
    criteria: str
    context: dict[str, Any]

    @classmethod
    def from_json_line(cls, line: str) -> "EvalItem":
        data = json.loads(line)
        return cls(
            id=data["id"],
            category=data["category"],
            version=data["version"],
            prompt=data["prompt"],
            expected_behavior=data.get("expected_behavior", {}),
            criteria=data.get("criteria", data["category"]),
            context=data.get("context", {}),
        )

    def to_json_line(self) -> str:
        return json.dumps({
            "id": self.id,
            "category": self.category,
            "version": self.version,
            "prompt": self.prompt,
            "expected_behavior": self.expected_behavior,
            "criteria": self.criteria,
            "context": self.context,
        }, ensure_ascii=False)


@dataclass
class EvalSpec:
    """eval set 1 카테고리 (HARNESS_CORE 5.4)."""

    category: str
    version: str
    items: list[EvalItem] = field(default_factory=list)
    fingerprint: str = ""

    @classmethod
    def load(cls, category: str, version: str) -> "EvalSpec":
        path = EVALS_DIR / category / f"{version}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Eval set not found: {path}")

        items: list[EvalItem] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            items.append(EvalItem.from_json_line(line))

        return cls(
            category=category,
            version=version,
            items=items,
            fingerprint=cls._compute_fingerprint(items),
        )

    @staticmethod
    def _compute_fingerprint(items: list[EvalItem]) -> str:
        """무결성 fingerprint (lm-eval 패턴)."""
        ids = sorted(i.id for i in items)
        return hashlib.sha256(",".join(ids).encode("utf-8")).hexdigest()[:12]

    def total_count(self) -> int:
        return len(self.items)

    def by_id(self, item_id: str) -> EvalItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None


def list_categories() -> list[str]:
    """evals/ 디렉토리에서 카테고리 목록."""
    if not EVALS_DIR.exists():
        return []
    return sorted([
        p.name for p in EVALS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name != "auto_added"
    ])


def latest_version(category: str) -> str | None:
    """카테고리 최신 버전."""
    cat_dir = EVALS_DIR / category
    if not cat_dir.exists():
        return None

    versions = []
    for f in cat_dir.glob("v*.jsonl"):
        stem = f.stem
        if stem.startswith("v") and stem[1:].isdigit():
            versions.append(stem)

    if not versions:
        return None
    return max(versions, key=lambda v: int(v[1:]))
