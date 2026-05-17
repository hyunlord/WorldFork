"""Phase 9.18-b — NPC encounter type spawn (★ §E 완전 해소).

본 commit (★ A + B 통합):
A. SIM_GM_SYSTEM_PROMPT 본격 NPC type 4 가이드 + JSON schema enum 확장
B. PHASE_TYPE_WEIGHTS 본격 NPC type 본격 분포 추가 (★ phase 본격 본격)
   + PHASE_PRIORITY_TYPES 본격 NPC 포함 (★ prompt 본격 본격 표시)

기대 효과 (★ 30턴 playthrough):
- NPC type spawn 0/13 → NPC type 본격 spawn 본격 본격
- 9.17 시리즈 trigger (★ FORM_NIGHT_COMPANION / ENGAGE_BANDIT 본격 본격 가능)
"""

from __future__ import annotations

from service.sim.sim_gm_agent import (
    PHASE_MISMATCH_WEIGHT_THRESHOLD,
    SIM_GM_SYSTEM_PROMPT,
    _is_phase_mismatch,
)
from service.sim.types import (
    PHASE_PRIORITY_TYPES,
    PHASE_TYPE_WEIGHTS,
    DungeonPhase,
    Encounter,
    EncounterType,
)

# ─── PHASE_TYPE_WEIGHTS — NPC type 분포 ───


class TestNPCInPhaseWeights:
    def test_entry_has_neutral_peaceful(self) -> None:
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.ENTRY]
        assert EncounterType.NPC_NEUTRAL in weights
        assert EncounterType.NPC_PEACEFUL in weights
        assert weights[EncounterType.NPC_NEUTRAL] > 0
        assert weights[EncounterType.NPC_PEACEFUL] > 0

    def test_entry_no_hostile(self) -> None:
        """ENTRY 본격 hostile 본격 X (★ 본문 — 진입 직후 위험 ↓)."""
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.ENTRY]
        assert EncounterType.NPC_HOSTILE not in weights

    def test_explore_has_all_non_hostile_npc(self) -> None:
        """EXPLORE 본격 peaceful/neutral/resource 본격."""
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.EXPLORE]
        assert weights[EncounterType.NPC_NEUTRAL] > 0
        assert weights[EncounterType.NPC_PEACEFUL] > 0
        assert weights[EncounterType.NPC_RESOURCE] > 0

    def test_explore_no_hostile(self) -> None:
        """EXPLORE 본격 hostile 본격 X (★ COMBAT 이후)."""
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.EXPLORE]
        assert EncounterType.NPC_HOSTILE not in weights

    def test_combat_has_hostile(self) -> None:
        """COMBAT 본격 hostile 강화 (★ 24/37/51화 약탈자)."""
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.COMBAT]
        assert EncounterType.NPC_HOSTILE in weights
        assert weights[EncounterType.NPC_HOSTILE] >= 0.20  # 검증용 ↑

    def test_rift_has_hostile_max(self) -> None:
        """RIFT 본격 hostile 최대 (★ 위험 ↑)."""
        weights = PHASE_TYPE_WEIGHTS[DungeonPhase.RIFT]
        assert EncounterType.NPC_HOSTILE in weights
        assert weights[EncounterType.NPC_HOSTILE] >= 0.25  # 검증용 ↑

    def test_each_phase_sum_1_0(self) -> None:
        """각 phase 본격 합 1.0 유지 (★ regression)."""
        for phase, weights in PHASE_TYPE_WEIGHTS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, (
                f"{phase.value} sum = {total:.4f}"
            )

    def test_no_resource_in_combat_or_rift(self) -> None:
        """resource 본격 EXPLORE 본격 한정 (★ 6화 본문 본격 본격)."""
        for phase in (DungeonPhase.COMBAT, DungeonPhase.RIFT):
            weights = PHASE_TYPE_WEIGHTS[phase]
            assert EncounterType.NPC_RESOURCE not in weights

    def test_all_npc_weights_above_threshold(self) -> None:
        """모든 NPC weight 본격 PHASE_MISMATCH_WEIGHT_THRESHOLD 본격 (★ retry 본격 본격 본격)."""
        npc_types = {
            EncounterType.NPC_PEACEFUL,
            EncounterType.NPC_NEUTRAL,
            EncounterType.NPC_HOSTILE,
            EncounterType.NPC_RESOURCE,
        }
        for phase, weights in PHASE_TYPE_WEIGHTS.items():
            for etype in npc_types & weights.keys():
                assert weights[etype] >= PHASE_MISMATCH_WEIGHT_THRESHOLD, (
                    f"{phase.value}/{etype.value} weight "
                    f"{weights[etype]} < threshold "
                    f"{PHASE_MISMATCH_WEIGHT_THRESHOLD}"
                )


# ─── PHASE_PRIORITY_TYPES — NPC 본격 포함 ───


class TestNPCInPriorityTypes:
    def test_entry_priority_has_npc(self) -> None:
        priority = PHASE_PRIORITY_TYPES[DungeonPhase.ENTRY]
        assert EncounterType.NPC_NEUTRAL in priority
        assert EncounterType.NPC_PEACEFUL in priority

    def test_combat_priority_has_hostile(self) -> None:
        priority = PHASE_PRIORITY_TYPES[DungeonPhase.COMBAT]
        assert EncounterType.NPC_HOSTILE in priority

    def test_rift_priority_has_hostile(self) -> None:
        priority = PHASE_PRIORITY_TYPES[DungeonPhase.RIFT]
        assert EncounterType.NPC_HOSTILE in priority


# ─── SIM_GM_SYSTEM_PROMPT — NPC type 가이드 + JSON schema ───


class TestSimGMSystemPromptHasNPCGuide:
    def test_npc_peaceful_in_prompt(self) -> None:
        assert "npc_peaceful" in SIM_GM_SYSTEM_PROMPT

    def test_npc_hostile_in_prompt(self) -> None:
        assert "npc_hostile" in SIM_GM_SYSTEM_PROMPT

    def test_npc_neutral_in_prompt(self) -> None:
        assert "npc_neutral" in SIM_GM_SYSTEM_PROMPT

    def test_npc_resource_in_prompt(self) -> None:
        assert "npc_resource" in SIM_GM_SYSTEM_PROMPT

    def test_json_schema_enum_includes_npc(self) -> None:
        """JSON schema enum 본격 NPC 4 type 본격 (★ 본격 본격 line wrap 본격)."""
        assert (
            "npc_peaceful | npc_neutral | npc_hostile | npc_resource"
            in SIM_GM_SYSTEM_PROMPT
        )

    def test_bandit_narrative_keyword(self) -> None:
        """약탈자 narrative 예시 (★ 24/37/51화 정합)."""
        assert "약탈자" in SIM_GM_SYSTEM_PROMPT

    def test_pond_narrative_keyword(self) -> None:
        """6화 연못 narrative 예시 (★ npc_resource 본문 정합)."""
        assert "연못" in SIM_GM_SYSTEM_PROMPT

    def test_npc_guide_section_header(self) -> None:
        """본격 'NPC encounter 가이드' section 본격 본격."""
        assert "NPC encounter 가이드" in SIM_GM_SYSTEM_PROMPT

    def test_prompt_size_under_5000_chars(self) -> None:
        """4500 budget 본격 본격 본격 X — SimGMAgent prompt 본격 본격 본격
        margin 본격 (★ V1 GMAgent 4500 budget 본격 본격 본격).
        """
        assert len(SIM_GM_SYSTEM_PROMPT) < 5000


# ─── _is_phase_mismatch — NPC type 본격 reject X ───


class TestPhaseEnforcementAcceptsNPC:
    def _enc(
        self, type_: EncounterType, name: str = "test"
    ) -> Encounter:
        return Encounter(
            type=type_,
            name=name,
            location="test_loc",
            description="test",
        )

    def test_npc_neutral_explore_accepted(self) -> None:
        """EXPLORE phase 본격 NPC_NEUTRAL 본격 본격 본격 (★ weight 15% >> 2%)."""
        encs = [self._enc(EncounterType.NPC_NEUTRAL)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.EXPLORE)
        assert violated is False, reason

    def test_npc_peaceful_entry_accepted(self) -> None:
        encs = [self._enc(EncounterType.NPC_PEACEFUL)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.ENTRY)
        assert violated is False, reason

    def test_npc_hostile_combat_accepted(self) -> None:
        encs = [self._enc(EncounterType.NPC_HOSTILE)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.COMBAT)
        assert violated is False, reason

    def test_npc_hostile_rift_accepted(self) -> None:
        encs = [self._enc(EncounterType.NPC_HOSTILE)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.RIFT)
        assert violated is False, reason

    def test_npc_resource_explore_accepted(self) -> None:
        encs = [self._enc(EncounterType.NPC_RESOURCE)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.EXPLORE)
        assert violated is False, reason

    def test_npc_hostile_entry_rejected(self) -> None:
        """ENTRY 본격 hostile 본격 본격 X (★ 진입 직후 위험 ↓ 본격 정합)."""
        encs = [self._enc(EncounterType.NPC_HOSTILE)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.ENTRY)
        assert violated is True

    def test_npc_resource_combat_rejected(self) -> None:
        """COMBAT 본격 resource 본격 본격 X (★ EXPLORE 본격 본격)."""
        encs = [self._enc(EncounterType.NPC_RESOURCE)]
        violated, reason = _is_phase_mismatch(encs, DungeonPhase.COMBAT)
        assert violated is True


# ─── 기존 type 본격 regression (★ B fix 본격 본격 본격 본격) ───


class TestExistingTypesStillAccepted:
    def _enc(self, type_: EncounterType) -> Encounter:
        return Encounter(
            type=type_, name="t", location="l", description="d"
        )

    def test_essence_explore_still_accepted(self) -> None:
        encs = [self._enc(EncounterType.ESSENCE)]
        violated, _ = _is_phase_mismatch(encs, DungeonPhase.EXPLORE)
        assert violated is False

    def test_monster_combat_still_accepted(self) -> None:
        encs = [self._enc(EncounterType.MONSTER)]
        violated, _ = _is_phase_mismatch(encs, DungeonPhase.COMBAT)
        assert violated is False

    def test_rift_rift_still_accepted(self) -> None:
        encs = [self._enc(EncounterType.RIFT)]
        violated, _ = _is_phase_mismatch(encs, DungeonPhase.RIFT)
        assert violated is False
