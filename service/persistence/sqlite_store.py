"""Phase D step 4/6b — SQLite 기반 세션/턴 영속 스토어."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_EQUIPMENT = '{"weapon":null,"armor":null,"accessory":null}'


@dataclass
class SessionRow:
    session_id: str
    created_at: float
    last_active: float
    current_hp: int
    max_hp: int
    inventory: list[str]
    location: str
    turn_count: int
    status_effects: list[dict[str, object]] = field(default_factory=list)  # ★ 6b
    equipment: dict[str, object] = field(  # ★ 6b
        default_factory=lambda: {"weapon": None, "armor": None, "accessory": None}
    )


@dataclass
class TurnRow:
    session_id: str
    turn_number: int
    created_at: float
    user_input: str
    narrative: str
    resolved_path: str
    state_delta: dict[str, object] = field(default_factory=dict)
    id: int = 0


class SqliteStore:
    """SQLite 세션/턴 영속 스토어 (Python stdlib only)."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        schema_path = Path(__file__).parent / "schema.sql"
        sql = schema_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(sql)
        self._migrate()

    def _migrate(self) -> None:
        """기존 DB에 새 컬럼 추가 (ALTER TABLE — 이미 있으면 무시)."""
        migrations = [
            (
                "status_effects",
                "ALTER TABLE sessions ADD COLUMN status_effects TEXT NOT NULL DEFAULT '[]'",
            ),
            (
                "equipment",
                "ALTER TABLE sessions ADD COLUMN equipment TEXT NOT NULL DEFAULT"
                f" '{_DEFAULT_EQUIPMENT}'",
            ),
        ]
        with self._connect() as conn:
            cur = conn.execute("PRAGMA table_info(sessions)")
            existing_cols = {row["name"] for row in cur.fetchall()}
            for col_name, alter_sql in migrations:
                if col_name not in existing_cols:
                    conn.execute(alter_sql)

    # ── sessions ──────────────────────────────────────────────────────────────

    def save_session(self, row: SessionRow) -> None:
        sql = """
        INSERT INTO sessions
            (session_id, created_at, last_active, current_hp, max_hp,
             inventory, location, turn_count, status_effects, equipment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            last_active    = excluded.last_active,
            current_hp     = excluded.current_hp,
            max_hp         = excluded.max_hp,
            inventory      = excluded.inventory,
            location       = excluded.location,
            turn_count     = excluded.turn_count,
            status_effects = excluded.status_effects,
            equipment      = excluded.equipment
        """
        with self._connect() as conn:
            conn.execute(
                sql,
                (
                    row.session_id,
                    row.created_at,
                    row.last_active,
                    row.current_hp,
                    row.max_hp,
                    json.dumps(row.inventory, ensure_ascii=False),
                    row.location,
                    row.turn_count,
                    json.dumps(row.status_effects, ensure_ascii=False),
                    json.dumps(row.equipment, ensure_ascii=False),
                ),
            )

    def load_session(self, session_id: str) -> SessionRow | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        status_raw = row["status_effects"] if "status_effects" in row.keys() else "[]"
        equipment_raw = row["equipment"] if "equipment" in row.keys() else _DEFAULT_EQUIPMENT
        status_parsed = json.loads(status_raw)
        equipment_parsed = json.loads(equipment_raw)
        return SessionRow(
            session_id=row["session_id"],
            created_at=row["created_at"],
            last_active=row["last_active"],
            current_hp=row["current_hp"],
            max_hp=row["max_hp"],
            inventory=json.loads(row["inventory"]),
            location=row["location"],
            turn_count=row["turn_count"],
            status_effects=status_parsed if isinstance(status_parsed, list) else [],
            equipment=(
                equipment_parsed if isinstance(equipment_parsed, dict)
                else {"weapon": None, "armor": None, "accessory": None}
            ),
        )

    def delete_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM sessions WHERE session_id = ?", (session_id,)
            )

    # ── turns ─────────────────────────────────────────────────────────────────

    def save_turn(self, turn: TurnRow) -> None:
        sql = """
        INSERT INTO turns
            (session_id, turn_number, created_at, user_input, narrative,
             resolved_path, state_delta)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            conn.execute(
                sql,
                (
                    turn.session_id,
                    turn.turn_number,
                    turn.created_at,
                    turn.user_input,
                    turn.narrative,
                    turn.resolved_path,
                    json.dumps(turn.state_delta, ensure_ascii=False),
                ),
            )

    def list_turns(self, session_id: str, limit: int = 50) -> list[TurnRow]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM turns WHERE session_id = ?"
                " ORDER BY turn_number ASC LIMIT ?",
                (session_id, limit),
            )
            rows = cur.fetchall()
        return [
            TurnRow(
                id=r["id"],
                session_id=r["session_id"],
                turn_number=r["turn_number"],
                created_at=r["created_at"],
                user_input=r["user_input"],
                narrative=r["narrative"],
                resolved_path=r["resolved_path"],
                state_delta=json.loads(r["state_delta"]),
            )
            for r in rows
        ]
