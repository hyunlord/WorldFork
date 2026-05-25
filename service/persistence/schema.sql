-- WorldFork 세션 + 턴 스키마 (Phase D step 4 + audit step 2 fix 4)
-- DB 경로: .local/worldfork.db (gitignored)
-- 이 파일은 sessions table의 모든 column을 포함한다.
-- 기존 DB backward-compat: sqlite_store.py _migrate() 참고.

CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT    PRIMARY KEY,
    created_at   REAL    NOT NULL,
    last_active  REAL    NOT NULL,

    -- 기본 stat
    current_hp   INTEGER NOT NULL DEFAULT 100,
    max_hp       INTEGER NOT NULL DEFAULT 100,

    -- inventory + location
    inventory    TEXT    NOT NULL DEFAULT '[]',
    location     TEXT    NOT NULL DEFAULT '1층 입구',

    -- turn
    turn_count       INTEGER NOT NULL DEFAULT 0,
    last_spawn_turn  INTEGER NOT NULL DEFAULT -10,

    -- status / equipment (JSON 직렬화)
    status_effects   TEXT    NOT NULL DEFAULT '[]',
    equipment        TEXT    NOT NULL DEFAULT '{"weapon":null,"armor":null,"accessory":null}',

    -- 캐릭터 진행
    player_level     INTEGER NOT NULL DEFAULT 1,
    player_xp        INTEGER NOT NULL DEFAULT 0,
    max_essences     INTEGER NOT NULL DEFAULT 1,
    soul_power       INTEGER NOT NULL DEFAULT 10,
    absorbed_essences      TEXT NOT NULL DEFAULT '[]',
    defeated_monster_types TEXT NOT NULL DEFAULT '[]',

    -- dungeon floor / clock
    floor_number     INTEGER NOT NULL DEFAULT 0,
    hours_in_dungeon REAL    NOT NULL DEFAULT 0.0,

    -- 마석 잔액
    stone_balance    INTEGER NOT NULL DEFAULT 0,

    -- rift 상태
    rift_id          TEXT    DEFAULT NULL,
    rift_sub_area    TEXT    DEFAULT NULL,
    rift_is_variant  INTEGER NOT NULL DEFAULT 0,

    -- 최초 포탈 개방 여부 (ep_0022)
    portal_first_opened INTEGER NOT NULL DEFAULT 0,

    -- 게임 내 경과 시간 (minute 단위, audit-step168h)
    time_elapsed        INTEGER NOT NULL DEFAULT 0,

    -- 종족 (phase-e-1, ★ default 바바리안)
    race                TEXT    NOT NULL DEFAULT 'barbarian',

    -- 시나리오 모드 (phase-e-2, ★ default bjorn)
    scenario_mode       TEXT    NOT NULL DEFAULT 'bjorn'
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


CREATE INDEX IF NOT EXISTS idx_turns_session
    ON turns(session_id, turn_number);

CREATE INDEX IF NOT EXISTS idx_sessions_last_active
    ON sessions(last_active);
