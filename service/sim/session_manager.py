"""Phase D step 4/6b — in-memory + SQLite 세션 매니저."""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from service.persistence.sqlite_store import SessionRow, SqliteStore, TurnRow
from service.sim.action_context import ActionResult
from service.sim.equipment import DEFAULT_EQUIPMENT_DICT


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
    last_spawn_turn: int = -10  # cooldown skip on first move


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
        encounters=[],  # encounters는 turn마다 재구성 — DB 비저장
        turn_count=r.turn_count,
        status_effects=list(r.status_effects),
        equipment=dict(r.equipment),
        last_spawn_turn=r.last_spawn_turn,
    )


class SessionManager:
    """in-memory cache + SQLite 영속화 세션 매니저.

    asyncio.to_thread 로 sync SQLite 호출을 비동기 처리.
    """

    def __init__(self, store: SqliteStore) -> None:
        self._store = store
        self._cache: dict[str, SessionState] = {}

    # ── public API ────────────────────────────────────────────────────────────

    async def create_session(
        self,
        current_hp: int = 100,
        max_hp: int = 100,
        inventory: list[str] | None = None,
        location: str = "1층 입구",
    ) -> SessionState:
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
        )
        self._cache[state.session_id] = state
        await asyncio.to_thread(self._store.save_session, _to_row(state))
        return state

    async def get_session(self, session_id: str) -> SessionState | None:
        if session_id in self._cache:
            return self._cache[session_id]
        row = await asyncio.to_thread(self._store.load_session, session_id)
        if row is None:
            return None
        state = _from_row(row)
        self._cache[session_id] = state
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
        # status + equipment update (★ 6b)
        if result.status_update is not None:
            state.status_effects = list(result.status_update)
        if result.equipment_update is not None:
            eq = dict(state.equipment)
            eq.update(result.equipment_update)
            state.equipment = eq
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

    async def end_session(self, session_id: str) -> None:
        self._cache.pop(session_id, None)
        await asyncio.to_thread(self._store.delete_session, session_id)

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
