"""Phase 9.17-e2 — rest 후 encounter generator wire (★ 6/7화 위험 정합).

본 commit (★ 9.17-e dead consumer 해소):
- REST_ENCOUNTER_WEIGHTS (★ HOSTILE 60 / NEUTRAL 30 / PEACEFUL 10)
- REST_ENCOUNTER_DESCRIPTIONS (★ 6/7/24화 narrative 정합)
- _generate_encounter_after_rest helper (★ 9.17-c1 fast variant)
- sim_runner trigger_encounter_after_rest wire (★ run_single_turn 본격)
"""

from __future__ import annotations

import random
from collections import Counter

from service.game.state_v2 import (
    Character,
    Location,
    Race,
    Realm,
    WorldState,
)
from service.sim.player_agent import MockPlayerAgent
from service.sim.sim_runner import (
    REST_ENCOUNTER_DESCRIPTIONS,
    REST_ENCOUNTER_WEIGHTS,
    SimRunner,
    _generate_encounter_after_rest,
)
from service.sim.types import (
    Encounter,
    EncounterType,
    PlayerAction,
    PlayerActionType,
    SimConfig,
)

# ─── REST_ENCOUNTER_WEIGHTS ───


class TestRestEncounterWeights:
    def test_hostile_majority(self) -> None:
        assert REST_ENCOUNTER_WEIGHTS["npc_hostile"] == 60

    def test_neutral_30(self) -> None:
        assert REST_ENCOUNTER_WEIGHTS["npc_neutral"] == 30

    def test_peaceful_10(self) -> None:
        assert REST_ENCOUNTER_WEIGHTS["npc_peaceful"] == 10

    def test_weights_sum_100(self) -> None:
        assert sum(REST_ENCOUNTER_WEIGHTS.values()) == 100

    def test_no_resource(self) -> None:
        """RESOURCE 본격 rest 중 X (★ 위험 분포만)."""
        assert "npc_resource" not in REST_ENCOUNTER_WEIGHTS

    def test_no_essence_no_monster(self) -> None:
        """rest 중 본격 NPC encounter only (★ 9.17-c1 NPC 4 type 본격)."""
        assert "essence" not in REST_ENCOUNTER_WEIGHTS
        assert "monster" not in REST_ENCOUNTER_WEIGHTS


# ─── REST_ENCOUNTER_DESCRIPTIONS ───


class TestRestEncounterDescriptions:
    def test_all_types_have_descriptions(self) -> None:
        for type_key in REST_ENCOUNTER_WEIGHTS:
            assert type_key in REST_ENCOUNTER_DESCRIPTIONS
            assert len(REST_ENCOUNTER_DESCRIPTIONS[type_key]) > 0

    def test_hostile_narrative_present(self) -> None:
        hostile_descs = REST_ENCOUNTER_DESCRIPTIONS["npc_hostile"]
        assert any("약탈자" in d for d in hostile_descs)


# ─── _generate_encounter_after_rest ───


class TestGenerateEncounterAfterRest:
    def test_returns_valid_npc_type(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng)
        assert enc.type in {
            EncounterType.NPC_HOSTILE,
            EncounterType.NPC_NEUTRAL,
            EncounterType.NPC_PEACEFUL,
        }

    def test_unique_name(self) -> None:
        rng = random.Random(42)
        enc1 = _generate_encounter_after_rest(rng)
        enc2 = _generate_encounter_after_rest(rng)
        assert enc1.name != enc2.name
        assert enc1.name.startswith("rest_enc_")
        assert enc2.name.startswith("rest_enc_")

    def test_description_matches_type(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng)
        type_key = enc.type.value
        assert enc.description in REST_ENCOUNTER_DESCRIPTIONS[type_key]

    def test_default_location_label(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng)
        assert enc.location == "rest_site"

    def test_custom_location_label(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(
            rng, location_label="floor1_corridor"
        )
        assert enc.location == "floor1_corridor"

    def test_spawned_at_turn(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng, turn_number=7)
        assert enc.spawned_at_turn == 7

    def test_ttl_turns_set(self) -> None:
        """TTL 본격 ENCOUNTER_TTL 본격 lookup (★ NPC types 본격 3-5)."""
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng)
        assert enc.ttl_turns > 0

    def test_deterministic_type_and_desc_with_seed(self) -> None:
        """seed 본격 type / description 본격 deterministic (★ uuid 본격 본격 변동)."""
        rng1 = random.Random(42)
        rng2 = random.Random(42)
        enc1 = _generate_encounter_after_rest(rng1)
        enc2 = _generate_encounter_after_rest(rng2)
        assert enc1.type == enc2.type
        assert enc1.description == enc2.description

    def test_distribution_approximate(self) -> None:
        """10000 sample 분포 본격 가중치 정합 (★ 60/30/10 ± 3%)."""
        rng = random.Random(42)
        types_seen = [
            _generate_encounter_after_rest(rng).type
            for _ in range(10000)
        ]
        counts = Counter(types_seen)
        # 60% ± 3% = 5700-6300
        assert 5700 <= counts[EncounterType.NPC_HOSTILE] <= 6300
        # 30% ± 3% = 2700-3300
        assert 2700 <= counts[EncounterType.NPC_NEUTRAL] <= 3300
        # 10% ± 3% = 700-1300
        assert 700 <= counts[EncounterType.NPC_PEACEFUL] <= 1300


# ─── SimRunner integration: REST → trigger → encounter spawn ───


def _make_dungeon_setup() -> tuple[
    dict[str, Character], WorldState, Location
]:
    bjorn = Character(
        name="비요른",
        race=Race.BARBARIAN,
        hp=50,
        hp_max=100,
        is_player=True,
    )
    party = {"비요른": bjorn}
    world = WorldState(party_members=["비요른"])
    location = Location(
        realm=Realm.DUNGEON,
        floor=1,
        sub_area="floor1_corridor",
    )
    return party, world, location


def _make_runner_with_rest_action() -> SimRunner:
    """REST_AND_NIGHT_WATCH 만 발현하는 mock player."""
    config = SimConfig(max_turns=1)
    rest_action = PlayerAction(
        actor_name="비요른",
        action_type=PlayerActionType.REST_AND_NIGHT_WATCH,
        rationale="rest test",
    )
    mock_player = MockPlayerAgent(mock_actions=[rest_action])
    return SimRunner(config=config, player_agent=mock_player)


class TestSimRunnerWire:
    def test_rest_triggers_spawn_encounter(self) -> None:
        """trigger 시 _active_encounters 본격 새 encounter 추가."""
        # 다수 sample — trigger 본격 본격 random 본격 본격 발생 본격.
        # 1인 rest 본격 NIGHT_WATCH_ENCOUNTER_PROBABILITY=0.20 본격 본격.
        triggered = 0
        spawned = 0
        for _ in range(50):
            party, world, location = _make_dungeon_setup()
            runner = _make_runner_with_rest_action()
            log = runner.run_single_turn(
                turn_number=1,
                actor_name="비요른",
                party=party,
                world=world,
                location=location,
            )
            if "trigger_encounter_after_rest" in log.side_effects:
                triggered += 1
                # trigger 시 spawn 본격 본격 발생 (★ 100% wire 검증)
                spawned_in_log = any(
                    eff.startswith("encounter_spawned_after_rest=")
                    for eff in log.side_effects
                )
                assert spawned_in_log
                # _active_encounters 본격 새 encounter 추가
                assert len(runner._active_encounters) >= 1
                spawned += 1
        # 일정 sample 이상 trigger 발생 본격 본격 (★ 20% 본격 50 trials 본격 평균 10)
        assert triggered > 0
        assert spawned == triggered  # ★ 1:1 wire 본격 (★ trigger → spawn)

    def test_rest_no_trigger_no_spawn(self) -> None:
        """trigger 발생 X 시 _active_encounters 변화 X."""
        # 다수 sample — trigger X 본격 본격 본격 발생.
        for _ in range(50):
            party, world, location = _make_dungeon_setup()
            runner = _make_runner_with_rest_action()
            initial_encounter_count = len(runner._active_encounters)
            log = runner.run_single_turn(
                turn_number=1,
                actor_name="비요른",
                party=party,
                world=world,
                location=location,
            )
            if "trigger_encounter_after_rest" not in log.side_effects:
                # trigger X 본격 본격 본격 본격 변화 X
                assert len(runner._active_encounters) == initial_encounter_count
                return  # ★ 단일 sample 본격 본격 본격
        # 본격 본격 본격 본격 본격 50 sample 본격 모두 trigger 발생 본격 X
        # (★ NIGHT_WATCH_ENCOUNTER_PROBABILITY=0.20 본격 본격 본격 50 trials
        #   본격 0.8^50 ≈ 0 본격 본격 본격 X)

    def test_spawned_encounter_location_from_sub_area(self) -> None:
        """spawned encounter.location 본격 location.sub_area 정합."""
        for _ in range(50):
            party, world, location = _make_dungeon_setup()
            runner = _make_runner_with_rest_action()
            log = runner.run_single_turn(
                turn_number=1,
                actor_name="비요른",
                party=party,
                world=world,
                location=location,
            )
            if any(
                eff.startswith("encounter_spawned_after_rest=")
                for eff in log.side_effects
            ):
                # location.sub_area 본격 새 encounter.location 본격
                new_encs = [
                    e for e in runner._active_encounters
                    if e.name.startswith("rest_enc_")
                ]
                assert len(new_encs) >= 1
                assert new_encs[0].location == "floor1_corridor"
                return

    def test_spawned_encounter_in_active_encounters(self) -> None:
        """spawned encounter 본격 _active_encounters 본격 본격 검증."""
        for _ in range(50):
            party, world, location = _make_dungeon_setup()
            runner = _make_runner_with_rest_action()
            log = runner.run_single_turn(
                turn_number=1,
                actor_name="비요른",
                party=party,
                world=world,
                location=location,
            )
            if any(
                eff.startswith("encounter_spawned_after_rest=")
                for eff in log.side_effects
            ):
                spawned_names_in_eff = [
                    eff.split("=", 1)[1].split(":")[0]
                    for eff in log.side_effects
                    if eff.startswith("encounter_spawned_after_rest=")
                ]
                active_names = {
                    e.name for e in runner._active_encounters
                }
                for name in spawned_names_in_eff:
                    assert name in active_names
                return

    def test_spawned_encounter_uses_rift_id_if_in_rift(self) -> None:
        """rift 내부 본격 location.rift_id 본격 location label."""
        for _ in range(50):
            bjorn = Character(
                name="비요른",
                race=Race.BARBARIAN,
                hp=50,
                hp_max=100,
                is_player=True,
            )
            party: dict[str, Character] = {"비요른": bjorn}
            world = WorldState(party_members=["비요른"])
            # rift 내부 location
            location = Location(
                realm=Realm.DUNGEON,
                floor=1,
                sub_area="floor1_corridor",
                rift_id="bloody_castle",
            )
            runner = _make_runner_with_rest_action()
            runner.run_single_turn(
                turn_number=1,
                actor_name="비요른",
                party=party,
                world=world,
                location=location,
            )
            new_encs = [
                e for e in runner._active_encounters
                if e.name.startswith("rest_enc_")
            ]
            if new_encs:
                # rift_id 본격 location label 본격 (★ rift_id 우선)
                assert new_encs[0].location == "bloody_castle"
                return


# ─── Encounter dataclass 본격 정합 (★ schema 검증) ───


class TestEncounterDataclassCompat:
    def test_generated_is_encounter_instance(self) -> None:
        rng = random.Random(42)
        enc = _generate_encounter_after_rest(rng)
        assert isinstance(enc, Encounter)
