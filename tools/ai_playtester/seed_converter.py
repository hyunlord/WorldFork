"""Finding → Eval Seed 변환 (★ W1 D6 자료 5.2 정확 구현).

★ 핵심 패턴 (자료 5.2):
    AI Playtester finding → eval set 자동 추가
    → 다음 baseline에 회귀 검증
    → "made but never used" 회피

★ W1 D6 정정 (본인 인사이트 #11):
    이전: prompt.user = description (재현 prompt 아님)
    이전: expected_behavior = avoid_issue=True (모호)

    이후 (자료 5.2 정확):
    - prompt = playthrough[finding.turn_n] 의 system_prompt + user_input
    - expected_behavior = 카테고리별 명시 (자료 4.2)
    - target_turn 없으면 None 반환 (시드 거부)
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from .runner import PlaytesterFinding, PlaytesterSessionResult

EVALS_AUTO_ADDED_DIR = Path(__file__).resolve().parents[2] / "evals" / "auto_added"

# 카테고리 매핑 (자료 5.2 + ★ W1 D7 확장 — 자료 5.5 부분 적용)
# W1 D6 Round 4 발견 카테고리 (AI/prompt/IP/clarity/pacing/worldbuilding) 모두 매핑
CATEGORY_MAPPING: dict[str, str] = {
    # ip_leakage 변형
    "ip_leakage": "ip_leakage",
    "ip_leak": "ip_leakage",
    "ip": "ip_leakage",                     # ★ W1 D7 (W1 D6 4건)
    "intellectual_property": "ip_leakage",  # ★ W1 D7

    # world_consistency 변형
    "world": "world_consistency",
    "world_canon_violation": "world_consistency",
    "worldbuilding": "world_consistency",   # ★ W1 D7
    "space_rules": "world_consistency",     # ★ W1 D7
    "anachronism": "world_consistency",     # ★ W1 D7
    "magic_system": "world_consistency",    # ★ W1 D7
    "context_loss": "world_consistency",    # ★ W1 D7

    # persona_consistency 변형
    "persona": "persona_consistency",
    "persona_break": "persona_consistency",
    "persona_drift": "persona_consistency",
    "personality": "persona_consistency",   # ★ W1 D7

    # korean_quality 변형
    "verbose": "korean_quality",
    "verbose_clueless": "korean_quality",   # ★ W1 D7
    "tone_mismatch": "korean_quality",
    "korean_unnatural": "korean_quality",
    "localization": "korean_quality",
    "speech_style": "korean_quality",       # ★ W1 D7
    "honorifics": "korean_quality",         # ★ W1 D7
    "wording": "korean_quality",            # ★ W1 D7
    "language": "korean_quality",           # ★ W1 D7
    "language_quality": "korean_quality",   # ★ W1 D7
    "language_mixing": "korean_quality",    # ★ W1 D7
    "외국어혼입": "korean_quality",          # ★ W1 D7

    # ai_breakout 변형 (★ W1 D6 5건 + prompt 2건)
    "ai_breakout": "ai_breakout",
    "ai_break": "ai_breakout",
    "ai": "ai_breakout",                    # ★ W1 D7
    "prompt": "ai_breakout",                # ★ W1 D7
    "prompt_injection": "ai_breakout",      # ★ W1 D7
    "prompt_injection_resistance": "ai_breakout",  # ★ W1 D7
    "meta_question": "ai_breakout",         # ★ W1 D7
    "self_disclosure": "ai_breakout",       # ★ W1 D7

    # ★ NEW: ux 카테고리 (자료 5.5 부분 적용)
    "ux": "ux",
    "ui": "ux",                             # ★ W1 D7
    "broken_ux": "ux",                      # ★ W1 D7 (general → ux)
    "clarity": "ux",                        # ★ W1 D7
    "pacing": "ux",                         # ★ W1 D7
    "navigation": "ux",                     # ★ W1 D7
    "too_many_choices": "ux",               # ★ W1 D7
    "onboarding": "ux",                     # ★ W1 D7
    "feedback": "ux",                       # ★ W1 D7
    "help": "ux",                           # ★ W1 D7
    "repetitive_intro": "ux",               # ★ W1 D7
    "fun": "ux",                            # ★ W1 D7

    # general (catch-all)
    "other": "general",
    "encoding": "general",                  # ★ W1 D7
    "truncation": "general",                # ★ W1 D7
    "구조/언어": "general",                  # ★ W1 D7
    "spatial/worldbuilding": "world_consistency",  # ★ W1 D7
    "<detail>": "general",                  # ★ W1 D7
}

# ★ Expected behaviors 카테고리별 (자료 4.2 그대로 + ★ W1 D7 ux 추가)
EXPECTED_BEHAVIORS_BY_CATEGORY: dict[str, dict[str, Any]] = {
    "persona_consistency": {
        "in_character": True,
        "no_ai_mentions": True,
        "speech_style_consistent": True,
    },
    "korean_quality": {
        "natural_korean": True,
        "no_translation_feel": True,
        "no_excessive_honorifics": True,
        "no_korean_english_mix": True,
    },
    "ip_leakage": {
        "no_proper_names": True,
        "uses_renamed_only": True,
    },
    "world_consistency": {
        "world_consistent": True,
        "no_anachronism": True,
    },
    "ai_breakout": {
        "no_ai_mentions": True,
        "stay_in_character": True,
        "deflect_meta_question": True,
    },
    # ★ W1 D7 NEW
    "ux": {
        "clear_choices": True,
        "no_navigation_loss": True,
        "appropriate_pacing": True,
    },
    "general": {
        "no_truncation": True,
        "appropriate_length": True,
    },
}


def _map_category(finding_category: str) -> str:
    return CATEGORY_MAPPING.get(finding_category.lower(), "general")


def _derive_expected_behavior(finding: PlaytesterFinding) -> dict[str, Any]:
    """카테고리별 명시적 expected_behavior (★ 자료 4.2 그대로).

    severity=critical 이면 critical_avoidance=True 추가.
    """
    cat = _map_category(finding.category)
    base = EXPECTED_BEHAVIORS_BY_CATEGORY.get(
        cat, EXPECTED_BEHAVIORS_BY_CATEGORY["general"]
    ).copy()

    if finding.severity == "critical":
        base["critical_avoidance"] = True

    return base


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
    """Finding → EvalSeed 변환기 (★ W1 D6 자료 5.2 정확)."""

    def convert(
        self,
        finding: PlaytesterFinding,
        session: PlaytesterSessionResult,
    ) -> EvalSeed | None:
        """단일 finding → seed (★ 자료 5.2: target_turn = playthrough[finding.turn_n]).

        우선순위:
            1. playthrough_log 에서 turn_n 매칭 entry 찾기
            2. 없으면 finding.turn_context fallback
            3. 둘 다 없으면 None (시드 거부)

        Returns:
            EvalSeed 또는 None (turn 정보 부족 시)
        """
        prompt, ctx = self._extract_prompt_and_context(finding, session)
        if prompt is None:
            return None

        category = _map_category(finding.category)
        seed_id = self._generate_id(finding, session)

        return EvalSeed(
            id=seed_id,
            category=category,
            version="auto_added",
            prompt=prompt,
            expected_behavior=_derive_expected_behavior(finding),
            criteria=category,
            context=ctx,
            metadata={
                "source": "ai_playtester",
                "persona": session.persona_id,
                "discovered_at": datetime.now().isoformat(),
                "severity": finding.severity,
                "original_description": finding.description,
                "session_work_name": session.work_name,
                "finding_turn_n": finding.turn_n,
            },
        )

    @staticmethod
    def _extract_prompt_and_context(
        finding: PlaytesterFinding,
        session: PlaytesterSessionResult,
    ) -> tuple[dict[str, str] | None, dict[str, Any]]:
        """target_turn → (prompt, context). 없으면 (None, {})."""
        target_turn = FindingToEvalSeed._get_target_turn(session, finding.turn_n)

        if target_turn is not None:
            system = str(target_turn.get("system_prompt", ""))
            user = str(target_turn.get("user_input", ""))
            if system and user:
                ctx_raw = target_turn.get("context", {"language": "ko"})
                ctx: dict[str, Any] = (
                    dict(ctx_raw) if isinstance(ctx_raw, dict) else {"language": "ko"}
                )
                return {"system": system, "user": user}, ctx

        # Fallback: turn_context (run_session에서 첨부)
        if finding.turn_context:
            system = str(finding.turn_context.get("system_prompt", ""))
            user = str(finding.turn_context.get("user_input", ""))
            if system and user:
                ctx = {
                    "language": finding.turn_context.get("language", "ko"),
                    "character_response": finding.turn_context.get(
                        "character_response", True
                    ),
                }
                return {"system": system, "user": user}, ctx

        # 둘 다 부재 → 시드 거부 (★ 자료 5.2 정신)
        return None, {}

    @staticmethod
    def _get_target_turn(
        session: PlaytesterSessionResult,
        turn_n: int,
    ) -> dict[str, Any] | None:
        """playthrough[turn_n] 추출 (★ 자료 5.2)."""
        for log in session.playthrough_log:
            if not isinstance(log, dict):
                continue
            if log.get("turn_n") == turn_n:
                return log
        return None

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
    none_rejected: int = 0  # ★ W1 D6: turn 부족으로 거부된 None 시드 수


class SeedManager:
    """시드 추가 + 한도 강제 (자료 5.4) + ★ W1 D6 None 처리."""

    def __init__(
        self,
        max_per_day: int = 20,
        max_per_category: int = 5,
    ) -> None:
        self.max_per_day = max_per_day
        self.max_per_category = max_per_category

    def add_seeds(
        self, seeds: list[EvalSeed | None]
    ) -> SeedAdditionResult:
        """시드 추가 (★ W1 D6: None 시드는 자동 reject).

        None 시드는 자료 5.2 위반 (target_turn 없음) 으로 거부.
        """
        valid_seeds: list[EvalSeed] = [s for s in seeds if s is not None]
        none_count = len(seeds) - len(valid_seeds)

        if none_count > 0:
            print(f"  [SeedManager] {none_count} seeds rejected (no target_turn)")

        EVALS_AUTO_ADDED_DIR.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y%m%d")
        existing_today = self._count_today(today)
        cat_counts = self._count_by_category_today(today)

        added: list[EvalSeed] = []
        rejected: list[tuple[EvalSeed, str]] = []

        for seed in valid_seeds:
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
            none_rejected=none_count,
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
