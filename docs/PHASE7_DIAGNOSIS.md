# Phase 7 진단 + 분해

## 본 commit (★ Phase 7 진단)

F8 마무리 후 Phase 7 본격 본격 — 기존 backend/frontend + HTML mockup → 게임 통합 본격 본격 분해.

## 기존 인프라 본격 (★ Step 1 실측)

### 1. Backend ✅ 존재 (★ port 8090)

- **Framework**: FastAPI 본격 본격
- **Entry**: `service/api/app.py` (★ `create_app()`)
- **현재 endpoints** (★ Tier 2 D7 본격 4개):
  - `POST /game/start` — 세션 시작 (Plan 생성)
  - `POST /game/turn` — 단일 턴
  - `GET /game/state/{session_id}` — 게임 상태
  - `POST /game/end` — 세션 종료 + 저장
- **Models**: Pydantic (`service/api/models.py`)
- **Static UI**: `service/api/static/` (★ D8 W2 vanilla JS chat — index.html + app.js + style.css)
- **CORS**: localhost:3000/4000 + 100.70.109.50 + env var (ALLOWED_ORIGINS)

### 2. Frontend ✅ 존재 (★ port 4000)

- **Framework**: Next.js 16.2.4 + React 19.2.4 + TailwindCSS 4
- **TypeScript**: strict 본격
- **Entry**: `frontend/app/page.tsx` (★ App Router)
- **Components** (★ Tier 2 D10 본격 5개):
  - `Chat.tsx` — 메인 대화 본격
  - `Metrics.tsx` — 본격 표시
  - `EndSession.tsx` — 세션 종료
  - `FindingsInput.tsx` — finding 입력
  - `FunRating.tsx` — 별점
- **lib**: api.ts + types.ts
- **Backend URL**: `http://100.70.109.50:8090` (★ Tailscale 본격)

### 3. HTML mockup ✅ (★ Phase 6, 8개 본격)

- **Path**: `tools/visual/ui_mockup/`
- **8개 화면**:
  - `index.html` (★ Phase 6 hub)
  - `start_menu.html` (★ 시작 메뉴)
  - `main_screen.html` (★ 메인 화면)
  - `gameplay_screen.html` (★ 게임 진행)
  - `character_sheet.html` (★ 캐릭터 시트)
  - `combat_screen.html` (★ 전투)
  - `dialogue_screen.html` (★ 대화)
  - `rift_entry.html` (★ 균열 진입)
- **본격 styling**: Noto Serif KR + ComfyUI 본격 본격 이미지 reference
- **본격 본격**: 100% static (★ dynamic data binding X)
- **합계**: 2330 lines HTML/CSS

### 4. Game State serialize 본격

- **Tier 0** (`service/game/state.py`): GameState minimal — turn / location / history / characters
- **Tier 2** (`service/game/state_v2.py`): Character V2 (★ 50+ stats) / WorldState (★ active_rifts, hours_in_dungeon) / Location
- **현재 API serialize**: `GET /game/state/{session_id}` 본격 Tier 0 GameState만 dict 본격 (★ turn/location/history)
- **본격 gap**: Tier 2 (Character V2 + WorldState + Location) 본격 API serialize X
- **본격 X**: dataclass `asdict` 본격 본격 — 본격 수동 serialize 본격 본격

## Phase 7 본격 본질 (★ 본격 finding)

**케이스 A 변형** 본격 — backend + frontend 본격 본격 본격, 그러나 본격 gap:

| Component | 상태 | gap |
|---|---|---|
| Backend FastAPI | ✅ 존재 | Tier 0 state만 API, Tier 2 state X |
| Frontend Next.js | ✅ 존재 | Chat 본격, 시각화 X (character/rift/combat/etc.) |
| HTML mockup | ✅ 8개 | 100% static, dynamic binding X |
| Sim runner | ✅ 존재 | API 본격 본격 X |
| Game state serialize | ⚠️ Tier 0만 | Tier 2 본격 X |

## Phase 7 분해 (★ 본격 결정)

```
Phase 7a: backend Tier 2 state API (★ 첫 commit 후보)
  - Tier 2 GameState (★ Character V2 + WorldState + Location) Pydantic serialize
  - 신규 endpoint: GET /api/v2/state/{session_id} 또는 본격
  - sim_runner 본격 통합 본격
  - 시간 ~2-3시간

Phase 7b: frontend routing skeleton
  - Next.js routing: /, /game, /character, /combat, /rift, /dialogue
  - 5 placeholder pages
  - HTML mockup 본격 React 변환 본격
  - 시간 ~3-4시간

Phase 7c-7g: 5 화면 본격 implement
  - 7c: gameplay (★ 메인 게임 loop UI)
  - 7d: character sheet
  - 7e: combat
  - 7f: dialogue
  - 7g: rift entry
  - 각 ~3-4시간

Phase 7h: 동적 사이클 통합
  - sim_runner ↔ frontend (WebSocket / polling)
  - 본격 turn 본격 본격 본격
  - 시간 ~4-5시간

총: ~7-10 commits, ~25-35시간
```

## 첫 commit 본격 후보 (★ Step 3 본격)

### 후보 1: Phase 7a backend Tier 2 state API ⭐ 추천

- **본격 가능**: Tier 2 GameState (★ Character V2 + WorldState + Location) serialize endpoint
- **시간**: ~2-3시간
- **본격 본격**: 이미 Pydantic + FastAPI 본격 — 본격 단순 본격
- **본격 본격**: frontend 본격 본격 데이터 본격 본격
- **본격 path**:
  - `service/api/models.py` — Tier 2 GameStateV2Response 본격 추가
  - `service/api/game_routes.py` — `/v2/state/{session_id}` 본격 endpoint
  - 또는 본격 단순: 기존 `/game/state` 본격 v2 본격 본격
  - tests: unit + smoke

### 후보 2: Phase 7b frontend skeleton routing

- **본격 가능**: Next.js routing + 5 placeholder
- **시간**: ~3-4시간
- **본격 본격**: backend Tier 2 data 본격 본격 X면 본격 placeholder 본격 본격

### 후보 3: 통합 운영 시뮬 (end-to-end)

- **본격 가능**: sim_runner → backend → frontend 연결 본격
- **시간**: ~4-5시간
- **본격 본격**: 본격 첫 commit 본격 본격 본격

### 후보 4: 본인 다른 본격 본질

## 본격 본격 (★ 본인 답할 결정)

```
1. 분해 본격 OK? (★ 7a-7h)
   - 케이스 A 변형 본격
   - 약 7-10 commits

2. 첫 commit 본격?
   - 후보 1 (★ 추천): Phase 7a backend Tier 2 state API
   - 후보 2: Phase 7b frontend routing
   - 후보 3: 통합 운영 시뮬
   - 후보 4: 본인 다른 본격

3. backend / frontend 본격 (★ 본격 본격 본격 본격)
   - 본격 새 endpoint 본격 vs 기존 endpoint 본격
   - frontend Next.js 본격 vs 본격 routing 본격
```

## 예상 시간

- Phase 7 전체: ~25-35시간 (★ 7-10 commits)
- 첫 commit (후보 1): ~2-3시간
- 본격 cycle 본격 X (★ weekly limit 본격)
