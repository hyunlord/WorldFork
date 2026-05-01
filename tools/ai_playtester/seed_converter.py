"""Finding → Eval Seed 변환 (AI_PLAYTESTER 5장).

★ 핵심 패턴:
  AI Playtester 발견 이슈 → eval set 자동 추가
  → 다음 baseline에 회귀 검증
  → "made but never used" 회피
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .runner import PlaytesterFinding, PlaytesterSessionResult

EVALS_AUTO_ADDED_DIR = Path(__file__).resolve().parents[2] / "evals" / "auto_added"

# 카테고리 매핑 (자료 5.2)
CATEGORY_MAPPING: dict[str, str] = {
    "ip_leakage": "ip_leakage",
    "ip_leak": "ip_leakage",
    "world": "world_consistency",
    "world_canon_violation": "world_consistency",
    "persona": "persona_consistency",
    "persona_break": "persona_consistency",
    "persona_drift": "persona_consistency",
    "verbose": "korean_quality",
    "tone_mismatch": "korean_quality",
    "korean_unnatural": "korean_quality",
    "localization": "korean_quality",
    "broken_ux": "general",
    "other": "general",
    "ai_breakout": "ai_breakout",
    "ai_break": "ai_breakout",
}

_EXPECTED_BEHAVIORS: dict[str, dict[str, Any]] = {
    "ip_leakage": {"no_original_ip": True, "uses_renamed_only": True},
    "world_consistency": {"world_consistent": True, "no_modern_tech": True},
    "persona_consistency": {"persona_consistent": True, "speech_style_consistent": True},
    "korean_quality": {"natural_korean": True, "no_translation_feel": True},
    "ai_breakout": {"no_ai_mention": True, "stay_in_character": True},
    "general": {"avoid_issue": True},
}


def _map_category(finding_category: str) -> str:
    return CATEGORY_MAPPING.get(finding_category.lower(), "general")


def _derive_expected_behavior(finding: PlaytesterFinding) -> dict[str, Any]:
    cat = _map_category(finding.category)
    return _EXPECTED_BEHAVIORS.get(cat, {"avoid_issue": True})


@dataclass
class EvalSeed:
    """자동 변환된 Eval 시드."""

    id: str
    category: str
    version: str
    prompt: dict[str, str]
    expected_behavior: dict[str, Any]
    criteria: str
    context: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonl(self) -> str:
        return json.dumps({
            "id": self.id,
            "category": self.category,
            "version": self.version,
            "prompt": self.prompt,
            "expected_behavior": self.expected_behavior,
            "criteria": self.criteria,
            "context": self.context,
            "metadata": self.metadata,
        }, ensure_ascii=False)


class FindingToEvalSeed:
    """Finding → EvalSeed 변환기 (AI_PLAYTESTER 5.2)."""

    def convert(
        self,
        finding: PlaytesterFinding,
        session: PlaytesterSessionResult,
    ) -> EvalSeed:
        """단일 finding → seed."""
        category = _map_category(finding.category)
        seed_id = self._generate_id(finding, session)

        intro = ""
        for log in session.playthrough_log:
            if isinstance(log, dict) and log.get("role") == "game_intro":
                intro = str(log.get("text", ""))
                break

        prompt: dict[str, str] = {
            "system": "당신은 텍스트 어드벤처 게임 GM. 한국어, 격식체.",
            "user": (
                f"신참 모험가 투르윈으로 게임 시작. "
                f"{finding.description[:100]}"
            ),
        }

        return EvalSeed(
            id=seed_id,
            category=category,
            version="auto_added",
            prompt=prompt,
            expected_behavior=_derive_expected_behavior(finding),
            criteria=category,
            context={
                "language": "ko",
                "character_response": True,
                "auto_seed": True,
            },
            metadata={
                "source": "ai_playtester",
                "persona": session.persona_id,
                "discovered_at": datetime.now().isoformat(),
                "severity": finding.severity,
                "original_description": finding.description,
                "session_work_name": session.work_name,
                "intro_excerpt": intro[:200],
            },
        )

    @staticmethod
    def _generate_id(
        finding: PlaytesterFinding,
        session: PlaytesterSessionResult,
    ) -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        suffix = uuid.uuid4().hex[:8]
        return f"playtester_{session.persona_id}_{date_str}_{suffix}"


@dataclass
class SeedAdditionResult:
    """시드 추가 결과."""

    added: list[EvalSeed]
    rejected: list[tuple[EvalSeed, str]]
    daily_count_before: int
    daily_count_after: int


class SeedManager:
    """시드 추가 + 한도 강제 (자료 5.4)."""

    def __init__(
        self,
        max_per_day: int = 20,
        max_per_category: int = 5,
    ) -> None:
        self.max_per_day = max_per_day
        self.max_per_category = max_per_category

    def add_seeds(self, seeds: list[EvalSeed]) -> SeedAdditionResult:
        EVALS_AUTO_ADDED_DIR.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        existing_today = self._count_today(today)
        cat_counts = self._count_by_category_today(today)

        added: list[EvalSeed] = []
        rejected: list[tuple[EvalSeed, str]] = []

        for seed in seeds:
            if (existing_today + len(added)) >= self.max_per_day:
                rejected.append((seed, f"max_per_day ({self.max_per_day}) reached"))
                continue

            cat_today = cat_counts.get(seed.category, 0)
            cat_in_batch = sum(1 for s in added if s.category == seed.category)
            if (cat_today + cat_in_batch) >= self.max_per_category:
                rejected.append(
                    (seed, f"max_per_category ({self.max_per_category}) reached")
                )
                continue

            self._save_seed(seed)
            added.append(seed)

        return SeedAdditionResult(
            added=added,
            rejected=rejected,
            daily_count_before=existing_today,
            daily_count_after=existing_today + len(added),
        )

    def _count_today(self, today: str) -> int:
        if not EVALS_AUTO_ADDED_DIR.exists():
            return 0
        date_prefix = f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        count = 0
        for f in EVALS_AUTO_ADDED_DIR.glob("*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    discovered = data.get("metadata", {}).get("discovered_at", "")
                    if discovered.startswith(date_prefix):
                        count += 1
                except json.JSONDecodeError:
                    pass
        return count

    def _count_by_category_today(self, today: str) -> dict[str, int]:
        if not EVALS_AUTO_ADDED_DIR.exists():
            return {}
        date_prefix = f"{today[:4]}-{today[4:6]}-{today[6:8]}"
        counts: dict[str, int] = {}
        for f in EVALS_AUTO_ADDED_DIR.glob("*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    discovered = data.get("metadata", {}).get("discovered_at", "")
                    if discovered.startswith(date_prefix):
                        cat = str(data.get("category", "general"))
                        counts[cat] = counts.get(cat, 0) + 1
                except json.JSONDecodeError:
                    pass
        return counts

    @staticmethod
    def _save_seed(seed: EvalSeed) -> Path:
        path = EVALS_AUTO_ADDED_DIR / f"{seed.category}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(seed.to_jsonl() + "\n")
        return path
