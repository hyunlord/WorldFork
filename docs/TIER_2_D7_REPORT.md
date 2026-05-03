# Tier 2 D7 — Web UI 시작 (★ 게이트 3 W1, FastAPI 백엔드)

날짜: 2026-05-04
타입: ★ 본인 결정 옵션 A (Web UI 시작)

---

## 0. 한 줄 요약

**FastAPI 백엔드 첫 단계. 게임 로직 그대로 활용. ★ 게이트 3 W1 시작. 외부 패키지 streak 19 → 마이그레이션 (★ 본인 결정).**

---

## 1. 본인 결정 (★ Web UI 본격)

```
- 결정 1: A 게이트 2 우선 ✅ (★ D6 잘림 0%)
- 결정 2: D Next.js 본격
- 결정 3: 시나리오 2 (~55-80h)

★ Tier 2 게이트 3 단계:
  W1 (★ D7): FastAPI 백엔드 ← 지금
  W2 (D8): 정적 HTML
  W3 (D9): Next.js
  W4 (D10): 통합 + UX
```

---

## 2. Phase 1 — FastAPI dependency

### pyproject.toml 변경

```diff
dependencies = [
    "anthropic>=0.39.0",
    "httpx>=0.27.0",
    "pydantic>=2.0",
    "pyyaml>=6.0",
    ...
+   # ★ Tier 2 D7: Web UI 백엔드 (게이트 3 W1)
+   # 외부 패키지 0건 streak 19번 → 마이그레이션 (★ 본인 결정 D)
+   "fastapi>=0.115",
+   "uvicorn[standard]>=0.32",
]
```

### ★ streak 마이그레이션 정직 인정

```
이전: 외부 패키지 0건 streak 19번 (Tier 1.5 → Tier 2 D6)
D7: ★ FastAPI + uvicorn 추가
→ ★ streak 19에서 끝
→ ★ 본인 결정 따라 OK (Web UI 위해 정직 인정)

★ 설치 확인:
  fastapi: 0.136.1
  uvicorn: 0.46.0
```

---

## 3. Phase 2 — service/api/ 골격

### 신규 파일

```
service/api/
├── __init__.py
├── app.py        (FastAPI app + CORS + /health)
├── models.py     (Pydantic 요청/응답 모델)
└── game_routes.py (★ /game/* 라우트)
```

### models.py

```python
StartGameRequest / StartGameResponse
TurnRequest / TurnResponse
GameStateResponse
ErrorResponse
```

### app.py

- FastAPI app 생성
- CORS (★ Next.js localhost:3000 위해)
- `/health` 라우트
- `/game/*` router 포함

---

## 4. Phase 3 — game_routes.py

### 라우트 3개

```
POST /game/start         → Plan + GameState 초기화 + session_id
POST /game/turn          → user_action → GMAgent + GameLoop → 응답
GET  /game/state/{sid}   → 현재 상태 (turn, location, history)
```

### ★ 게임 로직 그대로 활용

```python
# service/game/ 모두 변경 X
from service.game.gm_agent import GMAgent
from service.game.game_loop import GameLoop
from service.game.init_from_plan import init_game_state_from_plan
from service.pipeline.types import CharacterPlan, Plan, WorldSetting

# API는 얇은 wrapper
gm = GMAgent(game_llm=llm, mechanical_checker=MechanicalChecker())
loop = GameLoop(gm)
result = loop.process_action(plan, state, request.user_action)
```

### in-memory 세션

```python
_sessions: dict[str, dict[str, Any]] = {}
# Production: Redis / DB 등 고려
```

---

## 5. Phase 4 — 검증 + 작동

### tests/integration/test_api_routes.py +5

```
TestHealthRoute:
  test_health_ok ✅

TestGameRoutes:
  test_start_game ✅
  test_state_not_found ✅
  test_turn_session_not_found ✅
  test_start_then_state ✅
```

### ★ uvicorn 실제 작동 확인

```bash
$ uvicorn service.api.app:app --host 127.0.0.1 --port 8090 &
$ curl http://127.0.0.1:8090/health
{"status":"ok","version":"0.1.0"}

$ curl -X POST http://127.0.0.1:8090/game/start -d '{}'
{
  "session_id": "3611eb19-...",
  "plan": {
    "work_name": "신비한 모험",
    "world_setting": "중세 판타지 세계",
    "opening_scene": "..."
  },
  "initial_state": {"turn": 0, "location": "..."},
  "message": "Game started"
}
```

★ 진짜 작동 입증.

---

## 6. Phase 5 — 검증

```
✅ ruff: All checks passed (80 source files)
✅ mypy --strict: Success (80 files)
✅ pytest: 715 passed (684 → 715, +31)
   - +5 test_api_routes
   - +26 기존 (game_token_policy 7 + 기타)
```

---

## 7. ★ 본인 #18 5차 진화 유지

### 새 prompt EXCLUSIONS 적용 시점

```
codex 검증 시 새 dependency / 새 모듈 추가 = ★ EXCLUSIONS 정확히:
  - "Adding new optional parameters" ✅
  - "Splitting modules" ✅
  - "Adding documentation" ✅

★ 자의적 비판 (drift / scope / breaking) 0건 기대:
  - 게임 로직 변경 X
  - 새 모듈 추가만
  - 기존 caller 영향 X
```

### Verify 25/25 기대

```
D6: 25/25 (★ 새 prompt 작동 입증)
D7: ★ 같은 패턴 (★ 새 모듈 + dependency)
```

---

## 8. ★ 본인 인사이트 정합

```
#15 (Made-but-Never-Used):
  ★ API가 game 로직 진짜 사용 (★ wrapper)

#16 (사람 검증):
  ★ Web UI 환경 구축 시작
  ★ 잘림 0% + Web UI = 사람 검증 가능

#18 (5차):
  ★ 새 prompt EXCLUSIONS 유지

#19 (95+):
  ★ 유지

#21 (매 사이클 검증):
  ★ uvicorn + curl 진짜 작동 확인
```

---

## 9. ★ 게이트 3 단계 (★ 본인 #16 정공법)

```
W1 (D7): FastAPI 백엔드 ✅          ← 지금
W2 (D8): 정적 HTML chat UI
W3 (D9): Next.js 프론트엔드
W4 (D10): 통합 + 사람 검증 UX
★ 그 후: 본인 + 친구 사람 검증
```

---

## 10. 외부 패키지 streak

```
이전: 19번 (Tier 1.5 → Tier 2 D6)
★ D7: ★ 마이그레이션 (★ Web UI 위해 정직)
- fastapi>=0.115
- uvicorn[standard]>=0.32

★ 본인 결정 D 따라 OK
★ commit message에 정직 명시
```

---

## 11. ★ 다음 D8 (★ W2)

```
정적 HTML chat UI:
  - templates/index.html (★ 단순 chat)
  - vanilla JS + fetch API
  - 백엔드 통합 작동
  - ★ 첫 사람 시각 검증 가능

★ JS 외부 패키지 0건 (★ vanilla)
```
