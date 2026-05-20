-- WorldFork 세션 + 턴 스키마 (Phase D step 4)
-- DB 경로: .local/worldfork.db (gitignored)

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT    PRIMARY KEY,
    created_at   REAL    NOT NULL,
    last_active  REAL    NOT NULL,
    current_hp   INTEGER NOT NULL DEFAULT 100,
    max_hp       INTEGER NOT NULL DEFAULT 100,
    inventory    TEXT    NOT NULL DEFAULT '[]',
    location     TEXT    NOT NULL DEFAULT '1층 입구',
    turn_count   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS turns (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT    NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    turn_number   INTEGER NOT NULL,
    created_at    REAL    NOT NULL,
    user_input    TEXT    NOT NULL,
    narrative     TEXT    NOT NULL,
    resolved_path TEXT    NOT NULL,
    state_delta   TEXT    NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id, turn_number);
