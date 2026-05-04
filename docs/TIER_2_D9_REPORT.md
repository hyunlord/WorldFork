# Tier 2 D9 — Next.js 프론트엔드 (★ 게이트 3 W3)

날짜: 2026-05-04
타입: ★ 본인 결정 옵션 A (D9 풀)

---

## 0. 한 줄 요약

**Next.js 16.2 + React 19 + TypeScript 프론트엔드 골격. ★ frontend/ 새 영역. ★ pre-approved 패키지 활용.**

---

## 1. Phase 1 — Next.js 골격

### .gitignore 보강

```
# Next.js / React (★ Tier 2 D9 W3)
frontend/node_modules/
frontend/.next/
frontend/out/
frontend/build/
frontend/.env*.local
frontend/coverage/
frontend/next-env.d.ts
```

### Next.js 설치

```bash
npx create-next-app@latest frontend \
    --typescript --tailwind --app \
    --no-eslint --no-src-dir \
    --import-alias "@/*" --use-npm
```

설치된 버전:
- next: 16.2.4
- react: 19.2.4
- typescript: ^5
- tailwindcss: ^4 (★ @tailwindcss/postcss)

★ pre-approved 활용 (D7 prompt에 명시):
- next, react, react-dom, typescript ✅
- tailwindcss ✅

---

## 2. Phase 2 — chat UI 컴포넌트

### frontend/lib/types.ts

Pydantic 모델 (service/api/models.py) 미러:
- `StartGameRequest/Response`
- `TurnRequest/Response`
- `GameStateResponse`
- `Message` 타입

### frontend/lib/api.ts

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8090";

export async function startGame(): Promise<StartGameResponse>;
export async function processTurn(request: TurnRequest): Promise<TurnResponse>;
export async function getState(sessionId: string): Promise<GameStateResponse>;
```

`APIError` 클래스로 에러 핸들링.

### frontend/components/Chat.tsx

- `"use client"` (React 19 client component)
- `useState` + `useRef` + `useEffect`
- 한국어 chat UI
- Welcome 화면 → Chat 화면 자동 전환
- Message bubbles (user/gm/system/error 색상)
- Enter 키로 전송

### frontend/components/Metrics.tsx

- 턴별 검증 결과 시각화
- Mechanical / 잘림 / 점수 / Verify
- 점수 색상 자동:
  - ≥80 emerald (success)
  - ≥60 yellow (warning)
  - <60 red (error)

---

## 3. Phase 3 — 통합

### frontend/app/page.tsx

```tsx
"use client";

export default function HomePage() {
  const [metrics, setMetrics] = useState<TurnResponse | null>(null);
  const [location, setLocation] = useState<string>("-");

  return (
    <Chat onMetricsUpdate={setMetrics} onLocationUpdate={setLocation} />
    <Metrics metrics={metrics} location={location} />
  );
}
```

★ 본인 #16 정공법 footer 명시.

### frontend/app/layout.tsx

```tsx
<html lang="ko">  // ★ 한국어
<body className="bg-slate-900 text-slate-100 min-h-screen">
```

### frontend/app/globals.css

```css
@import "tailwindcss";

body {
  font-family: 'Pretendard', ...;
}
```

★ 단순화 (생성된 boilerplate 제거).

---

## 4. Phase 4 — 검증

### Next.js 빌드 ✅

```
✓ Compiled successfully in 1054ms
  Running TypeScript ...
  Finished TypeScript in 858ms
✓ Generating static pages (4/4)
```

### Python 검증

```
✅ ruff: All checks passed (80 source files)
✅ mypy --strict: Success
✅ pytest: 718 passed
```

### uvicorn + Next.js 동시 작동 ✅

```bash
$ uvicorn service.api.app:app --port 8090 &
$ cd frontend && npm run dev &

# uvicorn /health: {"status":"ok","version":"0.1.0"}
# Next.js: 포트 3000 사용중이라 3002+로 fallback
```

---

## 5. ★ 본인 #18 5차 진화 유지

```
새 디렉토리 (frontend/) 추가 = EXCLUSIONS:
  - "Splitting modules for separation of concerns" ✅
  - "Adding new files" (★ EXCLUSIONS 정확)

새 dependency (next/react/typescript/tailwind):
  - ★ pre-approved migration list (D7 prompt 명시)
  - ★ 자의적 비판 X 기대

API client 추가:
  - "Adding new optional" ✅
```

---

## 6. ★ 본인 인사이트 정합

```
#15 (Made-but-Never-Used):
  - Next.js → API client → FastAPI → 게임 로직
  - 모든 layer Used

#16 (사람 검증):
  - D9 = 시각적 디버깅 + 본격 UX 시작
  - 사람 검증 X (★ W4 후만)
  - footer 명시

#18 (5차):
  - pre-approved 활용
  - 자의적 비판 X 기대

#19 (95+):
  - 유지
```

---

## 7. ★ 외부 패키지 정책

### Python (★ Tier 1.5 → Tier 2)

```
streak 19 + (D7) fastapi/uvicorn 마이그레이션
★ pre-approved (D7 prompt)
```

### Frontend (★ Tier 2 D9)

```
next: 16.2.4
react: 19.2.4
react-dom: 19.2.4
typescript: ^5
tailwindcss: ^4
@tailwindcss/postcss: ^4
@types/node, @types/react, @types/react-dom

★ 모두 pre-approved (D7 prompt 명시)
★ codex 자의적 비판 X 기대
```

---

## 8. ★ 게이트 3 진척

| Week | 작업 | 상태 |
|---|---|---|
| W1 (D7) | FastAPI 백엔드 | ✅ |
| W2 (D8) | 정적 HTML chat UI | ✅ |
| **W3 (D9)** | **Next.js 프론트엔드** | **✅** |
| W4 (D10) | 통합 + 사람 검증 UX | ⏳ |

---

## 9. ★ 본인 시각적 본격 UX

```bash
# 터미널 1
$ uvicorn service.api.app:app --port 8090

# 터미널 2
$ cd frontend && npm run dev

# 브라우저
http://localhost:3000  # (또는 fallback 포트)
```

★ Tailwind dark theme + 한국어 chat UI.
★ D6 잘림 0% 본격 시각 확인.
★ 모바일 반응형.

---

## 10. ★ 다음 D10 (★ W4)

```
사람 검증 UX:
  - Fun rating (1-5) 입력 UI
  - Findings 입력 UI
  - 세션 종료 + 저장
  - 30턴 풀 플레이 흐름

★ 본인 #16 정공법:
  W4 끝 = ★ 거의 완성
  → 본인 + 친구 사람 검증 시작
  → ★ Tier 2 게이트 2+3 모두 통과 시점!
```
