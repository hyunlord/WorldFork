"""Phase D step 4/6b — in-memory + SQLite 세션 매니저."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from service.persistence.sqlite_store import SessionRow, SqliteStore, TurnRow
from service.sim.action_context import ActionResult
from service.sim.equipment import DEFAULT_EQUIPMENT_DICT

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
        floor_number=s.floor_number,
        hours_in_dungeon=s.hours_in_dungeon,
        stone_balance=s.stone_balance,
        rift_id=s.rift_id,
        rift_sub_area=s.rift_sub_area,
        rift_is_variant=s.rift_is_variant,
        portal_first_opened=s.portal_first_opened,
        time_elapsed=s.time_elapsed,
        race=s.race,
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
        floor_number=r.floor_number,
        hours_in_dungeon=r.hours_in_dungeon,
        stone_balance=r.stone_balance,
        rift_id=r.rift_id,
        rift_sub_area=r.rift_sub_area,
        rift_is_variant=r.rift_is_variant,
        portal_first_opened=r.portal_first_opened,
        time_elapsed=r.time_elapsed,
        race=r.race,
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
        current_hp: int = 100,
        max_hp: int = 100,
        inventory: list[str] | None = None,
        location: str = "1층 입구",
    ) -> SessionState:
        await self.evict_stale()
        now = _now()
        state = SessionState(
            session_id=_new_id(),
            current_hp=current_hp,
            max_hp=max_hp,
            inventory=list(inventory or []),
            location=location,
            encounters=[],
            turn_count=0,
            created_at=now,
            last_active=now,
            status_effects=[],
            equipment=dict(DEFAULT_EQUIPMENT_DICT),
            last_spawn_turn=-10,
            player_level=1,
            player_xp=0,
            max_essences=1,
            soul_power=10,
            absorbed_essences=[],
            defeated_monster_types=[],
            floor_number=0,
            hours_in_dungeon=0.0,
            stone_balance=0,
            rift_id=None,
            rift_sub_area=None,
            rift_is_variant=False,
            portal_first_opened=False,
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
        current_hp: int = 100,
        max_hp: int = 100,
        inventory: list[str] | None = None,
        location: str = "1층 입구",
    ) -> SessionState:
        """session_id가 있으면 조회, 없으면 신규 생성."""
        if session_id is not None:
            state = await self.get_session(session_id)
            if state is not None:
                return state
        return await self.create_session(
            current_hp=current_hp,
            max_hp=max_hp,
            inventory=inventory,
            location=location,
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
