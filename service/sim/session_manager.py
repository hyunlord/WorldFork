"""Phase D step 4/6b — in-memory + SQLite 세션 매니저."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from service.canon.items import build_weapon_equipment
from service.canon.races import Race, get_race_config
from service.canon.scenario import (
    SCENARIO_CONFIGS,
    ScenarioMode,
    find_coming_of_age_weapon,
    get_coming_of_age_npc,
    resolve_race_for_scenario,
)
from service.persistence.sqlite_store import SessionRow, SqliteStore, TurnRow
from service.sim.action_context import ActionResult
from service.sim.enemy import Enemy, enemy_to_dict
from service.sim.equipment import DEFAULT_EQUIPMENT_DICT, equipment_to_dict

ACTIVE_TIMEOUT = timedelta(hours=1)


@dataclass
class SessionState:
    """단일 플레이 세션 상태."""

    session_id: str
    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    encounters: list[dict[str, object]]
    turn_count: int
    created_at: float
    last_active: float
    status_effects: list[dict[str, object]] = field(default_factory=list)
    equipment: dict[str, object] = field(
        default_factory=lambda: dict(DEFAULT_EQUIPMENT_DICT)
    )
    last_spawn_turn: int = -10
    # ★ 6d — player progression (본문 정합: ep_0022 L1 시작)
    player_level: int = 1
    player_xp: int = 0
    max_essences: int = 1
    soul_power: int = 10
    absorbed_essences: list[dict[str, object]] = field(default_factory=list)
    defeated_monster_types: list[str] = field(default_factory=list)
    # ★ 감응도 소비 아이템 누적 (element → bonus) — 정수 외 영구 감응도
    player_sensitivities: dict[str, int] = field(default_factory=dict)
    # ★ 7 — dungeon floor
    floor_number: int = 0
    # ★ 168h — dungeon clock
    hours_in_dungeon: float = 0.0
    # ★ audit-c1 — 스톤 잔액
    stone_balance: int = 0
    # ★ audit-3 — rift state
    rift_id: str | None = None
    rift_sub_area: str | None = None
    rift_is_variant: bool = False
    # ★ 6d-followup — 최초 포탈 개방 여부 (ep_0022)
    portal_first_opened: bool = False
    # ★ audit-step168h — 게임 내 경과 시간 (minute 단위)
    # force return 시 +1440min (24h), 본문: wiki 010 "다음날 정오"
    time_elapsed: int = 0
    # ★ phase-e-1 — 종족 (★ default 바바리안, 본문 정합)
    race: str = "barbarian"
    # ★ phase-e-2 — 시나리오 모드 (★ default bjorn)
    scenario_mode: str = "bjorn"
    # ★ 게임 엔진 2단계 — 스토리 진전(07 StoryState): 단계 + 플래그
    story_phase: str = "declaration"
    story_flags: dict[str, bool] = field(default_factory=dict)


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> float:
    return time.time()


def _to_row(s: SessionState) -> SessionRow:
    return SessionRow(
        session_id=s.session_id,
        created_at=s.created_at,
        last_active=s.last_active,
        current_hp=s.current_hp,
        max_hp=s.max_hp,
        inventory=list(s.inventory),
        location=s.location,
        turn_count=s.turn_count,
        status_effects=list(s.status_effects),
        equipment=dict(s.equipment),
        last_spawn_turn=s.last_spawn_turn,
        player_level=s.player_level,
        player_xp=s.player_xp,
        max_essences=s.max_essences,
        soul_power=s.soul_power,
        absorbed_essences=list(s.absorbed_essences),
        defeated_monster_types=list(s.defeated_monster_types),
        player_sensitivities=dict(s.player_sensitivities),
        floor_number=s.floor_number,
        hours_in_dungeon=s.hours_in_dungeon,
        stone_balance=s.stone_balance,
        rift_id=s.rift_id,
        rift_sub_area=s.rift_sub_area,
        rift_is_variant=s.rift_is_variant,
        portal_first_opened=s.portal_first_opened,
        time_elapsed=s.time_elapsed,
        race=s.race,
        scenario_mode=s.scenario_mode,
        story_phase=s.story_phase,
        story_flags=dict(s.story_flags),
    )


def _from_row(r: SessionRow) -> SessionState:
    return SessionState(
        session_id=r.session_id,
        created_at=r.created_at,
        last_active=r.last_active,
        current_hp=r.current_hp,
        max_hp=r.max_hp,
        inventory=list(r.inventory),
        location=r.location,
        encounters=[],
        turn_count=r.turn_count,
        status_effects=list(r.status_effects),
        equipment=dict(r.equipment),
        last_spawn_turn=r.last_spawn_turn,
        player_level=r.player_level,
        player_xp=r.player_xp,
        max_essences=r.max_essences,
        soul_power=r.soul_power,
        absorbed_essences=list(r.absorbed_essences),
        defeated_monster_types=list(r.defeated_monster_types),
        player_sensitivities=dict(r.player_sensitivities),
        floor_number=r.floor_number,
        hours_in_dungeon=r.hours_in_dungeon,
        stone_balance=r.stone_balance,
        rift_id=r.rift_id,
        rift_sub_area=r.rift_sub_area,
        rift_is_variant=r.rift_is_variant,
        portal_first_opened=r.portal_first_opened,
        time_elapsed=r.time_elapsed,
        race=r.race,
        scenario_mode=r.scenario_mode,
        story_phase=r.story_phase,
        story_flags=dict(r.story_flags),
    )


class SessionManager:
    """in-memory cache + SQLite 영속화 세션 매니저.

    asyncio.to_thread 로 sync SQLite 호출을 비동기 처리.
    """

    def __init__(self, store: SqliteStore) -> None:
        self._store = store
        self._cache: dict[str, SessionState] = {}
        self._last_seen: dict[str, datetime] = {}

    # ── public API ────────────────────────────────────────────────────────────

    async def create_session(
        self,
        race: Race | None = None,
        scenario_mode: ScenarioMode = ScenarioMode.BJORN,
        inventory: list[str] | None = None,
        location: str | None = None,
        *,
        weapon: str | None = None,
        current_hp: int | None = None,
        max_hp: int | None = None,
    ) -> SessionState:
        await self.evict_stale()
        now = _now()
        resolved_race = resolve_race_for_scenario(scenario_mode, race)
        race_cfg = get_race_config(resolved_race)
        scenario_cfg = SCENARIO_CONFIGS[scenario_mode]
        use_hp = current_hp if current_hp is not None else race_cfg.hp_base
        use_max_hp = max_hp if max_hp is not None else race_cfg.hp_base
        use_location = location if location is not None else scenario_cfg.starting_location
        # inventory + 시작 무기 우선순위 (★ ep_0002 성인식 무기 선택):
        # 1. weapon 명시 (성인식 선택) → [weapon] (★ 방패 고정 해소)
        # 2. inventory 명시 (테스트 / custom 시나리오)
        # 3. scenario.starting_inventory (BJORN → 방패 default)
        # 4. race.starting_inventory_default (NEW_EXPLORER → 종족 정합)
        if weapon is not None:
            use_inventory = [weapon]
        elif inventory is not None:
            use_inventory = list(inventory)
        elif scenario_cfg.starting_inventory:
            use_inventory = list(scenario_cfg.starting_inventory)
        else:
            use_inventory = list(race_cfg.starting_inventory_default)
        # ★ 선택 무기 장착 (★ equipment.weapon + element — 4284fbc 정합)
        equipment_dict = dict(DEFAULT_EQUIPMENT_DICT)
        if weapon is not None:
            sw = find_coming_of_age_weapon(weapon)
            equipment_dict["weapon"] = equipment_to_dict(
                build_weapon_equipment(
                    weapon,
                    sw.attack_bonus if sw is not None else 0,
                    sw.description if sw is not None else "",
                )
            )
        # ★ 성인식 마을(floor 0) — 성년 의식 주재 NPC seed (대화 대상 + 추천 정합).
        #   비적대 Enemy(is_hostile=False) → get_first_npc가 찾아 handle_dialogue 작동.
        #   마을은 EncounterPanel 미표시(inVillage)라 '적대' 오표시 없음.
        start_encounters: list[dict[str, object]] = []
        if scenario_cfg.starting_floor == 0:
            npc_name = get_coming_of_age_npc(resolved_race)
            start_encounters = [
                enemy_to_dict(
                    Enemy(
                        name=npc_name,
                        hp=100,
                        max_hp=100,
                        attack=0,
                        defense=0,
                        is_hostile=False,
                    )
                )
            ]
        state = SessionState(
            session_id=_new_id(),
            current_hp=use_hp,
            max_hp=use_max_hp,
            inventory=use_inventory,
            location=use_location,
            encounters=start_encounters,
            turn_count=0,
            created_at=now,
            last_active=now,
            status_effects=[],
            equipment=equipment_dict,
            last_spawn_turn=-10,
            player_level=1,
            player_xp=0,
            max_essences=race_cfg.max_essences_base,
            soul_power=race_cfg.soul_power_base,
            absorbed_essences=[],
            defeated_monster_types=[],
            floor_number=0,
            hours_in_dungeon=0.0,
            stone_balance=0,
            rift_id=None,
            rift_sub_area=None,
            rift_is_variant=False,
            portal_first_opened=False,
            race=resolved_race.value,
            scenario_mode=scenario_mode.value,
        )
        self._cache[state.session_id] = state
        self._last_seen[state.session_id] = datetime.utcnow()
        await asyncio.to_thread(self._store.save_session, _to_row(state))
        return state

    async def get_session(self, session_id: str) -> SessionState | None:
        if session_id in self._cache:
            self._last_seen[session_id] = datetime.utcnow()
            return self._cache[session_id]
        row = await asyncio.to_thread(self._store.load_session, session_id)
        if row is None:
            return None
        state = _from_row(row)
        self._cache[session_id] = state
        self._last_seen[session_id] = datetime.utcnow()
        return state

    async def get_recent_turns(
        self, session_id: str, n: int = 8
    ) -> list[tuple[str, str]]:
        """최근 n턴 (user_input, narrative) 시간순 — GM 누적 컨텍스트용."""
        rows = await asyncio.to_thread(self._store.list_turns, session_id, 50)
        return [(r.user_input, r.narrative) for r in rows[-n:]]

    async def apply_result(
        self,
        session_id: str,
        result: ActionResult,
        user_input: str,
        resolved_path: str,
    ) -> SessionState:
        """ActionResult를 세션 상태에 반영하고 턴 기록을 저장한다."""
        state = await self.get_session(session_id)
        if state is None:
            raise KeyError(f"session not found: {session_id}")

        # state mutation
        state.current_hp = max(
            0, min(state.max_hp, state.current_hp + result.hp_change)
        )
        # ★ passive HP 재생 — 흡수 정수 자연 재생력 (매 턴, 생존 시, max_hp 상한)
        if 0 < state.current_hp < state.max_hp and state.absorbed_essences:
            from service.sim.player_state import compute_total_regen, slot_from_dict

            regen = compute_total_regen(
                [slot_from_dict(d) for d in state.absorbed_essences]
            )
            if regen > 0:
                state.current_hp = min(state.max_hp, state.current_hp + regen)
        if result.inventory_add:
            state.inventory.extend(result.inventory_add)
        if result.inventory_remove:
            state.inventory = [
                item for item in state.inventory if item not in result.inventory_remove
            ]
        if result.location is not None:
            state.location = result.location
        # encounters update (in-memory only, non-persisted)
        if result.encounters_update is not None:
            state.encounters = list(result.encounters_update)
        elif result.encounter_resolved:
            state.encounters = []
        if result.status_update is not None:
            state.status_effects = list(result.status_update)
        if result.equipment_update is not None:
            eq = dict(state.equipment)
            eq.update(result.equipment_update)
            state.equipment = eq
        # ★ 6d — XP / level / essence
        if result.xp_gain > 0:
            from service.sim.xp_curve import compute_level_for_xp, soul_power_gain_on_level_up
            state.player_xp += result.xp_gain
            computed = compute_level_for_xp(state.player_xp)
            if computed > state.player_level:
                sp_gain = soul_power_gain_on_level_up(computed)
                state.soul_power += sp_gain
                state.player_level = computed
                state.max_essences = computed
        if result.defeated_monsters_add:
            for m in result.defeated_monsters_add:
                if m not in state.defeated_monster_types:
                    state.defeated_monster_types.append(m)
        if result.essence_slot_add is not None:
            state.absorbed_essences.append(dict(result.essence_slot_add))
        if result.essence_slot_remove is not None:
            state.absorbed_essences = [
                s for s in state.absorbed_essences
                if s.get("essence_name") != result.essence_slot_remove
            ]
        # ★ 감응도 소비 아이템 → player_sensitivities 누적
        if result.sensitivity_add:
            for element, bonus in result.sensitivity_add.items():
                state.player_sensitivities[element] = (
                    state.player_sensitivities.get(element, 0) + bonus
                )
        # ★ 168h — hours_in_dungeon 누적 (floor_change 적용 전 현재 층 기준)
        if result.hours_in_dungeon_reset:
            state.hours_in_dungeon = 0.0
        elif state.floor_number >= 1:
            state.hours_in_dungeon += float(result.time_advance)
        if result.floor_change is not None:
            state.floor_number = max(0, state.floor_number + result.floor_change)
        # ★ audit-c1 — stone_balance 누적
        if result.stone_change != 0:
            state.stone_balance += result.stone_change
        # ★ 6d-followup — 최초 포탈 개방 flag (ep_0022)
        if result.portal_first_opened_set:
            state.portal_first_opened = True
        # ★ audit-3 — rift transition
        if result.rift_transition is not None:
            rt = result.rift_transition
            action = rt.get("action")
            if action == "enter":
                state.rift_id = str(rt["rift_id"]) if rt.get("rift_id") else None
                state.rift_sub_area = str(rt["rift_sub_area"]) if rt.get("rift_sub_area") else None
                state.rift_is_variant = bool(rt.get("is_variant", False))
            elif action == "move_to_chamber":
                state.rift_sub_area = str(rt["rift_sub_area"]) if rt.get("rift_sub_area") else None
            elif action == "exit":
                state.rift_id = None
                state.rift_sub_area = None
                state.rift_is_variant = False
        # ★ audit-step168h-followup — 일반 turn 경과 시간 누적 (minute 단위)
        state.time_elapsed += int(round(result.time_advance * 60))
        state.turn_count += 1
        state.last_active = _now()

        # persist
        self._cache[session_id] = state
        await asyncio.to_thread(self._store.save_session, _to_row(state))

        turn = TurnRow(
            session_id=session_id,
            turn_number=state.turn_count,
            created_at=state.last_active,
            user_input=user_input,
            narrative=result.narrative,
            resolved_path=resolved_path,
            state_delta={
                "hp_change": result.hp_change,
                "inventory_add": result.inventory_add,
                "inventory_remove": result.inventory_remove,
                "location": result.location,
                "time_advance": result.time_advance,
                "affinity_changes": result.affinity_changes,
                "encounter_resolved": result.encounter_resolved,
            },
        )
        await asyncio.to_thread(self._store.save_turn, turn)
        return state

    async def save_state(self, state: SessionState) -> None:
        """state를 cache + DB에 저장 (apply_result 없이 직접 갱신)."""
        self._cache[state.session_id] = state
        await asyncio.to_thread(self._store.save_session, _to_row(state))

    async def end_session(self, session_id: str) -> None:
        self._cache.pop(session_id, None)
        self._last_seen.pop(session_id, None)
        await asyncio.to_thread(self._store.delete_session, session_id)

    async def evict_stale(self) -> int:
        """ACTIVE_TIMEOUT 초과 in-memory cache entries 제거.

        SQLite는 유지 — 다음 access 시 reload.
        """
        now = datetime.utcnow()
        stale = [
            sid for sid, ts in self._last_seen.items()
            if now - ts > ACTIVE_TIMEOUT
        ]
        for sid in stale:
            self._cache.pop(sid, None)
            self._last_seen.pop(sid, None)
        return len(stale)

    async def get_or_create(
        self,
        session_id: str | None,
        *,
        current_hp: int | None = None,
        max_hp: int | None = None,
        inventory: list[str] | None = None,
        location: str | None = None,
    ) -> SessionState:
        """session_id가 있으면 조회, 없으면 신규 생성."""
        if session_id is not None:
            state = await self.get_session(session_id)
            if state is not None:
                return state
        return await self.create_session(
            inventory=inventory,
            location=location,
            current_hp=current_hp,
            max_hp=max_hp,
        )


# ── 싱글톤 (app 레벨에서 교체 가능) ─────────────────────────────────────────

_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        from pathlib import Path

        db_path = Path(".local/worldfork.db")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        store = SqliteStore(db_path)
        _manager = SessionManager(store)
    return _manager


def override_session_manager(mgr: SessionManager) -> None:
    """테스트용 싱글톤 교체."""
    global _manager
    _manager = mgr
