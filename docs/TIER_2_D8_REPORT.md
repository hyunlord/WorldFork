# Tier 2 D8 — 정적 HTML chat UI (★ 게이트 3 W2)

날짜: 2026-05-04
타입: ★ 본인 결정 옵션 A (D8 풀)

---

## 0. 한 줄 요약

**정적 HTML chat UI 신규. vanilla JS + fetch. ★ 본인 시각적 첫 확인 가능. 외부 패키지 0건 streak (★ JS 영역).**

---

## 1. Phase 1 — HTML 골격

### service/api/static/index.html

```
welcome → chat → metrics 흐름
```

- `<header>`: WorldFork 제목 + 세션/턴 status
- `<main>`: 게임 영역 + Metrics aside
  - `#welcome`: 게임 시작 버튼
  - `#chat`: 메시지 + 입력창
  - `#metrics`: Mechanical / 잘림 / 점수 / Verify / 위치
- `<footer>`: ★ 본인 #16 정공법 명시 (사람 검증 X)

---

## 2. Phase 2 — CSS

### service/api/static/style.css

★ **vanilla CSS** (외부 패키지 0건):
- Dark theme (`#1a1a2e` 베이스)
- Accent: `#4cc9f0` (밝은 청색)
- Success/Warning/Error 상태 색상
- 반응형 (768px 미디어 쿼리)
- slideIn 애니메이션 + 로딩 스피너

---

## 3. Phase 3 — JS

### service/api/static/app.js

★ **vanilla JS + fetch** (외부 패키지 0건):
- IIFE wrapper (★ strict mode)
- `addMessage(content, type)` — user/gm/system/error 분기
- `updateMetrics(data)` — 점수 색상 자동 (≥80 success, ≥60 warning, <60 error)
- `setLoading(loading)` — 버튼 disable + 스피너
- `startGame()` → POST /game/start
- `sendAction()` → POST /game/turn + 잘림 경고
- `refreshState()` → GET /game/state/{sid}
- Enter 키로 전송

---

## 4. Phase 4 — FastAPI StaticFiles 통합

### service/api/app.py 변경

```python
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# /static/* → CSS/JS
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# / → index.html
@app.get("/")
async def root() -> FileResponse:
    return FileResponse(str(static_dir / "index.html"))
```

### tests/integration/test_api_routes.py +3

```
TestStaticFiles:
  test_root_serves_index ✅ ("WorldFork" + "한국어" 검증)
  test_static_css ✅ (Content-Type: css)
  test_static_js ✅
```

---

## 5. Phase 5 — 작동 + 검증

### uvicorn 실제 작동 확인

```bash
$ uvicorn service.api.app:app --host 127.0.0.1 --port 8090 &

$ curl http://127.0.0.1:8090/health
{"status":"ok","version":"0.1.0"}

$ curl http://127.0.0.1:8090/
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    ...
    <title>WorldFork — 한국어 어드벤처</title>

$ curl http://127.0.0.1:8090/static/style.css
/* WorldFork chat UI (★ Tier 2 D8 W2) */
...

$ curl http://127.0.0.1:8090/static/app.js
/* WorldFork chat UI logic (★ Tier 2 D8 W2) */
...

$ curl -X POST http://127.0.0.1:8090/game/start -d '{}'
{"session_id":"78117616-...","plan":{...},"initial_state":{...}}
```

★ 모두 ✅ 작동.

### 검증 결과

```
✅ ruff: All checks passed (80 source files)
✅ mypy --strict: Success
✅ pytest: 718 passed (715 → 718, +3 static file tests)
```

---

## 6. ★ 본인 시각적 첫 확인 가능

```
브라우저:
  http://localhost:8090/

★ chat UI 시각적 확인
★ "게임 시작" 버튼 → 한 턴 입력 → 응답
★ 잘림 0% (★ D6 fix) 진짜 시각 확인
★ Metrics 실시간 업데이트
```

---

## 7. ★ 외부 패키지 정책

```
JS/CSS 영역:
  ★ vanilla 100% (★ 외부 패키지 0건)
  - jquery / react / vue 등 X
  - bootstrap / tailwind / framer 등 X

Python 영역:
  fastapi / uvicorn (D7 추가, pre-approved) 그대로
  ★ 추가 dependency X

★ 0건 streak 유지 (JS 영역에서)
```

---

## 8. ★ 본인 #16 정공법 유지

```
D8 정적 HTML 가치:
  ✅ 시각적 디버깅 가능
  ✅ 백엔드 작동 확인
  ✅ D9 (Next.js) 마이그레이션 기준

★ 그러나 사람 검증 X:
  - 거의 완성 X (★ chat UI만)
  - 본인 #16: Web UI 거의 완성 후만
  - W3 (Next.js) + W4 (UX) 후만 진짜 사람 검증
```

---

## 9. ★ 본인 #18 5차 진화 유지

```
D7에서 입증:
  - 새 prompt EXCLUSIONS 작동 (Verify 25/25)
  - prompt 보강으로 본인 결정 SPEC 반영

D8 적용:
  - HTML/CSS/JS 추가 = "Adding new files" (EXCLUSIONS 정확)
  - StaticFiles 통합 = "Adding new optional"
  - ★ 자의적 비판 X 기대
  - ★ Verify 25/25 기대
```

---

## 10. 본인 인사이트 정합

```
#15 (Made-but-Never-Used):
  ★ Static UI가 game API 진짜 사용 (★ wrapper)

#16 (사람 검증):
  ★ D9 + D10 후만
  ★ D8은 시각적 디버깅

#18 (5차):
  ★ 새 prompt EXCLUSIONS 유지
  ★ 새 파일 추가 = 자의적 비판 X 기대

#19 (95+):
  ★ 유지

#21 (매 사이클 검증):
  ★ uvicorn + curl 진짜 작동
```

---

## 11. ★ 게이트 3 진척

| Week | 작업 | 상태 |
|---|---|---|
| W1 (D7) | FastAPI 백엔드 | ✅ |
| **W2 (D8)** | **정적 HTML chat UI** | **✅** |
| W3 (D9) | Next.js 프론트엔드 | ⏳ |
| W4 (D10) | 통합 + 사람 검증 UX | ⏳ |

---

## 12. ★ 다음 D9 (★ W3)

```
Next.js + React 프론트엔드:
  - frontend/ 디렉토리 신규
  - Next.js 14+ App Router
  - TypeScript
  - 본격 UX (★ shadcn/ui or 자체 컴포넌트)
  - 모바일 OK

★ 외부 패키지 (★ pre-approved migration list):
  - next, react, react-dom, typescript
  - vitest (★ 테스트)
  - tailwindcss (★ 선택)

★ 시간: ~1주 (★ 시나리오 2 일정)
```
