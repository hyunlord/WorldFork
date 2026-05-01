"""Tier 1 W1 D4: FindingToEvalSeed + SeedManager 단위 테스트."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from tools.ai_playtester.runner import PlaytesterFinding, PlaytesterSessionResult
from tools.ai_playtester.seed_converter import (
    EvalSeed,
    FindingToEvalSeed,
    SeedManager,
)


def _make_finding(
    severity: str = "major",
    category: str = "tone_mismatch",
    description: str = "공문서체 응답",
) -> PlaytesterFinding:
    return PlaytesterFinding(
        severity=severity,
        category=category,
        turn_n=1,
        description=description,
    )


def _make_session(
    persona_id: str = "casual_korean_player",
    intro_text: str = "게임 인트로...",
) -> PlaytesterSessionResult:
    return PlaytesterSessionResult(
        persona_id=persona_id,
        work_name="novice_dungeon_run",
        completed=False,
        n_turns_played=2,
        elapsed_seconds=42.0,
        fun_rating=1,
        would_replay=False,
        abandoned=True,
        abandon_reason="intro 잘림",
        abandon_turn=2,
        findings=[],
        playthrough_log=[{"role": "game_intro", "text": intro_text}],
    )


def _make_seed(category: str = "korean_quality", idx: int = 0) -> EvalSeed:
    return EvalSeed(
        id=f"test_{idx}",
        category=category,
        version="auto_added",
        prompt={"system": "", "user": ""},
        expected_behavior={},
        criteria=category,
        context={},
        metadata={"discovered_at": datetime.now().isoformat()},
    )


class TestFindingToEvalSeed:
    def test_tone_mismatch_maps_to_korean_quality(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("major", "tone_mismatch"), _make_session())
        assert seed.category == "korean_quality"

    def test_verbose_maps_to_korean_quality(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("major", "verbose"), _make_session())
        assert seed.category == "korean_quality"

    def test_ip_leak_maps_to_ip_leakage(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("critical", "ip_leak"), _make_session())
        assert seed.category == "ip_leakage"

    def test_broken_ux_maps_to_general(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("critical", "broken_ux"), _make_session())
        assert seed.category == "general"

    def test_unknown_category_maps_to_general(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("minor", "unknown_xyz"), _make_session())
        assert seed.category == "general"

    def test_version_is_auto_added(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session())
        assert seed.version == "auto_added"

    def test_metadata_persona_recorded(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session("speed_runner"))
        assert seed.metadata["persona"] == "speed_runner"

    def test_metadata_severity_recorded(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding("critical"), _make_session())
        assert seed.metadata["severity"] == "critical"

    def test_id_contains_persona(self) -> None:
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session("casual_korean_player"))
        assert "casual_korean_player" in seed.id

    def test_intro_excerpt_in_metadata(self) -> None:
        seed = FindingToEvalSeed().convert(
            _make_finding(), _make_session(intro_text="던전 입구에 서 있습니다.")
        )
        assert "던전" in seed.metadata["intro_excerpt"]

    def test_to_jsonl_roundtrip(self) -> None:
        import json
        seed = FindingToEvalSeed().convert(_make_finding(), _make_session())
        line = seed.to_jsonl()
        data = json.loads(line)
        assert data["version"] == "auto_added"
        assert data["category"] == "korean_quality"


class TestSeedManager:
    def test_add_within_limits(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=5)
            seeds = [_make_seed("korean_quality", i) for i in range(3)]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 3
            assert len(result.rejected) == 0
            assert result.daily_count_after == 3

    def test_max_per_category_enforced(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=2)
            seeds = [_make_seed("korean_quality", i) for i in range(5)]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 2
            assert len(result.rejected) == 3

    def test_max_per_day_enforced(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=3, max_per_category=10)
            seeds = [_make_seed("general", i) for i in range(5)]
            result = mgr.add_seeds(seeds)
            assert len(result.added) == 3
            assert len(result.rejected) == 2

    def test_mixed_categories_respected(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=2)
            seeds = (
                [_make_seed("korean_quality", i) for i in range(3)]
                + [_make_seed("general", i + 10) for i in range(3)]
            )
            result = mgr.add_seeds(seeds)
            added_cats = {s.category for s in result.added}
            assert "korean_quality" in added_cats
            assert "general" in added_cats
            # 각 카테고리 최대 2
            kq = sum(1 for s in result.added if s.category == "korean_quality")
            ge = sum(1 for s in result.added if s.category == "general")
            assert kq <= 2
            assert ge <= 2

    def test_jsonl_file_created(self, tmp_path: Path) -> None:
        import tools.ai_playtester.seed_converter as sc
        with patch.object(sc, "EVALS_AUTO_ADDED_DIR", tmp_path):
            mgr = SeedManager(max_per_day=20, max_per_category=5)
            mgr.add_seeds([_make_seed("ip_leakage")])
            assert (tmp_path / "ip_leakage.jsonl").exists()
