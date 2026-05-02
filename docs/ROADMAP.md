# WorldFork — Project Roadmap

> **세계관에 들어가서 사는 인터랙티브 게임**
> 작품 정보를 입력하면 그 세계관에 진입한 것처럼 플레이하는 LLM 기반 게임 서비스
>
> 작성: 2026-04-29
> 상태: 초안 v0.1 (착수 전 설계 단계)
> 레포: https://github.com/hyunlord/WorldFork

---

## 0. 이 문서의 목적

WorldFork 개발의 **큰 그림과 단계적 목표**를 정의한다. 상세 구현은 별도 문서:
- `HARNESS_CORE.md` — 두 Layer가 공유하는 검증 코어
- `HARNESS_LAYER1_DEV.md` — 개발 하네스 (코드 변경 검증)
- `HARNESS_LAYER2_SERVICE.md` — 서비스 하네스 (게임 런타임 검증)
- `LESSONS.md` — WorldSim + AutoDev 자료 통합 교훈
- `ANTI_PATTERNS.md` — 절대 하지 말 것

**이 문서가 의도적으로 안 다루는 것**:
- 상세 기술 스펙 (변경 잦음 → 별도 design 문서)
- 모든 기능 리스트 (YAGNI 위반)
- UI/UX 디테일 (Tier 2+에서)
- 비즈니스 모델 / 마케팅
- 인프라 운영 (출시 후)

---

## 1. 비전 — 한 줄 요약

> **"사용자가 좋아하는 작품의 세계관에 들어가서 캐릭터로 살아보는 게임"**

### 핵심 차별화 (vs 경쟁)

| 항목 | Crack (wrtn.ai) | AI Dungeon | **WorldFork** |
|---|---|---|---|
| 시나리오 입력 | 정해진 시나리오 | 자유 텍스트 | **작품명 검색 자동 + 사용자 검토** |
| 게임성 | 약함 (자유 채팅) | 약함 (스토리만) | **강함 (스탯/주사위/상태)** |
| 세계관 충실도 | 시나리오 의존 | LLM 자유 | **검색 + 플랜 검증** |
| NPC 살아있음 | 없음 | 약함 | **하이브리드 (이벤트 기반)** |
| 다양성 | 단일 모드 | 단일 모드 | **4축 (진입/모드/장르/자유도)** |
| 검증 시스템 | 불투명 | 없음 | **3계층 검증 + Cross-Model** |

### 사용자 경험 흐름 (한 문장)

```
작품명 입력 → 자동 검색·플랜 생성 → 검토·수정 → 게임 시작 → 플레이
```

---

## 2. 두 Layer 시스템 (핵심 아키텍처)

WorldFork는 **두 개의 하네스**가 같은 검증 코어를 공유하는 구조다.

### 왜 두 Layer인가

AutoDev 프로젝트 자료에서 검증된 패턴:
- **개발할 때**의 검증과 **사용자가 쓸 때**의 검증이 **같은 엔진 공유**
- 결과: 개발 자체가 도그푸딩 → "made but never used" 함정 자동 회피
- 결과: 마케팅 메시지 = 실제 동작 (정직성 보장)

### 구조도

```
┌──────────────────────────────────────────────────────┐
│  공유 코어 (Shared Core)                              │
│  - VerifyAgent (LLM 평가기)                           │
│  - Mechanical Checker (형식 검증, 0 토큰)             │
│  - Cross-Model Selector                               │
│  - Eval Set Runner                                    │
│  - Scoring System (0-100)                             │
│  - Prompt Loader (3-tier)                             │
│  - LLM Clients (local + API fallback)                 │
└──────────────────────────────────────────────────────┘
              ↑                          ↑
              │                          │
    ┌─────────┴────────┐    ┌────────────┴─────────┐
    │ Layer 1 (Dev)     │   │ Layer 2 (Service)     │
    │                   │   │                       │
    │ 개발자가 코드 수정 │   │ 사용자가 게임 플레이   │
    │ → ship gate 검증   │   │ → 응답마다 검증        │
    │ → main에 push 가능 │   │ → 통과 시 사용자에게  │
    │                   │   │                       │
    │ scripts/verify.sh │   │ service/pipeline.py   │
    │ pre-commit hook   │   │ retry/fallback chain  │
    │ CI workflow       │   │                       │
    └───────────────────┘    └───────────────────────┘
```

### 두 Layer의 정책 차이

같은 엔진을 쓰지만 **운영 정책은 다르다**:

| 항목 | Layer 1 (개발) | Layer 2 (서비스) |
|---|---|---|
| Threshold | 95+ (엄격) | 70+ (관대) |
| 자동 재시도 | 0회 (개발자 수정) | 3회 (자동) |
| 검증 범위 | 전체 eval set | 빠른 일부만 |
| 실패 시 | commit 차단 | 재생성 / fallback |
| 비용 한도 | 무관 (개발 시) | per-request 한도 |

상세는 `HARNESS_LAYER1_DEV.md`, `HARNESS_LAYER2_SERVICE.md` 참조.

### 두 Layer가 공유하는 것

- **같은 verifier 코드** — 게임 응답 검증과 코드 변경 검증이 동일 함수 호출
- **같은 eval set** — 캐릭터 일관성 평가셋이 양쪽에서 사용
- **같은 점수 체계** — 0-100 스케일, 같은 카테고리
- **같은 Cross-Model 규칙** — 검증자 ≠ 생성자

---

## 3. 핵심 컨셉 — 4가지 디자인 원칙

### 원칙 1: 게임 로직(코드) + 묘사(LLM) 분리

WorldSim 자료의 가장 중요한 결론. Crack과의 결정적 차이.

```
❌ Crack 스타일 (LLM이 모든 결정):
  사용자: "검을 휘둘러"
  LLM: "당신은 검을 휘둘렀고 적은 죽었다"
  → 게임 밸런스 무너짐, 상태 추적 불가

✅ WorldFork 스타일 (코드 + LLM 분리):
  사용자: "검을 휘둘러"
  게임코드: 명중률/데미지 계산 → 적 HP 14 잔존
  LLM: [결과 받아서] "검이 어깨를 베었다, 적이 분노한다"
  → 게임 밸런스 가능, 상태 추적 가능, 디버깅 가능
```

### 원칙 2: 작은 모델 + GBNF JSON 강제

WorldSim 검증 결과: **Qwen 0.8B SFT 일관성 85% > Qwen 9B SFT 54%**.
큰 모델이 캐릭터 일관성에 더 좋지 않다.

DGX Spark 사용 시에도 의도적으로 작은 모델 우선 검토. 큰 모델은 마지막 카드.

JSON 출력은 **GBNF grammar로 강제** — 100% 유효 보장 (프롬프트 부탁 = 35% 실패).

### 원칙 3: Cross-Model Verification

같은 LLM이 자기 출력 검증하면 **self-rationalization** 발생 ("내가 만든 거니까 좋다").

```
생성: Coding Model (예: 로컬 Qwen)
검증: Verify Model (예: API Claude Haiku)
→ 다른 모델이 "객관적으로" 평가
```

**정보 격리**: 재시도 시 점수/verdict는 절대 LLM에 안 보냄. issues+suggestions만. 점수 게이밍 방지.

### 원칙 4: Hybrid 게임 모드 (사용자 주인공 + NPC 살아있음)

```
주: 인터랙티브 (사용자 = 주인공)
부: 백그라운드 시뮬 (5-10 NPC가 자기 일 함)

LLM 호출:
  - 사용자 행동 응답
  - NPC 만날 때 페르소나 활성화
  - 큰 이벤트 발생 시
  - 평소엔 룰 기반 (LLM 호출 X)
```

이벤트 기반(no tick) 시뮬 = WorldSim 자료의 "전략 4". 시뮬 난이도 회피하면서 살아있는 느낌 유지.

---

## 4. 사용자 경험 흐름 (Layer 2 상세)

### 4.1 진입 단계 (작품 → 플랜)

```
[1] 작품명 입력
    "원피스 세계관으로 게임하고 싶어"
    
[2] Interview Agent (모호하면 질문)
    Q1. 어떤 시점으로?
        a) 주인공 파티 합류 b) 다른 세력 c) 마을 주민
    Q2. 어떤 시간대?
    Q3. 플레이 스타일?
    
[3] 웹 검색 (병렬)
    - 위키 (공식 설정)
    - 팬 커뮤니티 (반응, 인기 포인트)
    - 출처별 신뢰도 분류
    
[4] Planning Agent (Drafter, Claude Opus)
    검색 결과 → 게임 플랜 v1
    - 세계관 요약 (IP 마스킹 적용)
    - 주요 NPC 페르소나
    - 추천 진입 방식 3가지
    - 추천 게임 시스템
    
[5] Verify Agent (Challenger, Gemini ≠ Drafter)
    - 원작 충실도 체크
    - 저작권 누출 체크 (IP leakage score)
    - 세계관 모순 체크
    
[6] 사용자 검토 / 수정
    - 자연어로 "이 부분 바꿔줘"
    - 직접 텍스트 수정
    - Diff 표시 (변경사항 명확히)
    - 확정 시 게임 시작
```

### 4.2 게임 진행 단계

```
[게임 루프]
사용자 행동 입력 (자연어 + 선택지)
        ↓
[행동 분류] (룰 기반)
   - 이동/대화/전투/조사 등
        ↓
[게임 로직 처리] (코드)
   - 스탯/주사위/상태 변경
   - HP/인벤토리/관계 업데이트
        ↓
[NPC 백그라운드 tick] (이벤트 기반)
   - 만난 NPC만 페르소나 활성화
   - 큰 이벤트만 LLM 호출
        ↓
[GM 묘사 생성] (LLM)
   - 캐릭터 응답 (페르소나)
   - 환경 묘사 (분위기)
        ↓
[검증 3계층]
   Stage 1: Mechanical (0 토큰)
   Stage 2: Lore Visual (선택)
   Stage 3: LLM Cross-Check
        ↓
[통과] → 사용자에게 출력
[실패] → 재생성 (issues only) max 3회
[3회 실패] → Fallback (다른 모델)
```

### 4.3 다양성 4축

같은 작품이어도 매번 다른 게임이 가능:

| 축 | 옵션 | 효과 |
|---|---|---|
| **진입 방식** | 주인공 빙의 / 조연 / 엑스트라 / 적대 / 회귀 | 시점 변화 |
| **플레이 모드** | 단일 / 파티 / 진영 / 멀티시점 | 스케일 변화 |
| **장르 시스템** | 모험/관계/경영/추리/정치 | 메카닉 변화 |
| **자유도** | 원작 충실 / 분기 가능 / 완전 자유 | 분기 폭 변화 |

5 × 4 × 5 × 3 = 300가지 조합. 재플레이 가치의 핵심.

Tier 0에서는 1축만 살리고 시작 (YAGNI).

---

## 5. Tier 0 — 검증 (1주)

> **목표**: 컨셉이 재미있는지 검증. API로 빠르게 프로토타입.

### Tier 0 진입 조건
- ROADMAP, HARNESS 문서 작성 완료
- 딥리서치 결과 정리 완료
- WorldFork 레포에 첫 commit (구조만)

### Tier 0 작업

**Day 1-2: 인프라 + Layer 1 시작**
- [ ] 프로젝트 구조 셋업 (모노레포 / 디렉토리)
- [ ] requirements.txt / package.json
- [ ] `.env.example` (모든 필수 환경변수 포함)
- [ ] `scripts/verify.sh` 최소 버전 (build + tsc/pytest)
- [ ] pre-commit hook
- [ ] GitHub Actions CI 기본
- [ ] **첫 commit으로 ship gate 검증** (자기 검증)

**Day 3-4: Layer 2 최소 게임 루프 (API 사용)**
- [ ] LLM Client 추상화 (Anthropic API 시작)
- [ ] 5-section system prompt 템플릿
- [ ] GameState 클래스 (HP/인벤토리)
- [ ] Pydantic 스키마 강제 (JSON)
- [ ] 콘솔 게임 루프 (사용자 입력 → LLM → 결과)
- [ ] 시나리오: **본인이 잘 아는 작품 1개** (Tier 0 한정, 저작권 검증용 아님 — 컨셉 검증용)
  - 본인이 잘 알면 LLM 응답이 "그럴듯한지" 즉시 판단 가능
  - 저작권 마스킹은 Tier 1+에서 본격 적용
- [ ] 다양성 4축 중 **장르 시스템 축만** 살림 (모험/관계/추리 중 시작 시 1개 선택)
  - 같은 작품 + 다른 장르 = 다른 게임 검증
  - 나머지 3축은 Tier 1+

**Day 5: Eval Set v1 + Mechanical 검증기**
- [ ] eval_sets/ 디렉토리 구조
- [ ] persona_consistency.jsonl (10-20개)
- [ ] korean_quality.jsonl (10개)
- [ ] json_validity.jsonl (10개)
- [ ] mechanical_checker.py (5가지 룰)
- [ ] 룰 기반 평가기 + CSV 추적

**Day 6: 도그푸딩 + 짧은 시나리오 + v0.2 Ablation 측정**
- [ ] 처음부터 끝까지 30분 플레이 가능한 시나리오
- [ ] **본인이 직접 5번 플레이** (made but never used 회피)
- [ ] **AI Playtester 3 페르소나** (casual / troll / beginner) 각 1회
  - Claude Code 또는 Codex CLI 호출
  - 게임 LLM과 다른 모델 강제 (Cross-Model)
  - 결과 → eval 시드로 누적
- [ ] 평가셋 결과 baseline 측정
- [ ] **v0.2 Ablation #1: Information Isolation** (11.7.1 참조)
  - 100 케이스, 3가지 모드 (A: score 노출, B: issues only, C: 절충) 비교
  - Retry 후 점수 개선폭 측정
  - 결과 → HARNESS_CORE 8장 확정
- [ ] **v0.2 Ablation #2: Ship Gate Threshold** (11.7.2 참조)
  - 점수 분포 분석 (P50, P95, std)
  - 95+ 유지 vs 90+ vs binary-mech-only 결정
  - 결과 → HARNESS_LAYER1_DEV Ship Gate 정책 확정
- [ ] 발견된 이슈 → 다음 eval 시드로

**Day 7: 외부 검증**
- [ ] 친구 3-5명 테스트
- [ ] "재미있나?" 정성 피드백
- [ ] 5분 안에 흥미 잃는지
- [ ] 어디서 막히는지
- [ ] **인간 피드백 > AI 시뮬** (메타 14.5)

### Tier 0 졸업 조건

- [ ] 30분 플레이 시나리오 완주 가능
- [ ] 본인 5회 + 친구 3-5명 플레이
- [ ] **친구 3명 이상 끝까지 완주**
- [ ] 정성 피드백 평균 "재미있다" 이상
- [ ] Mechanical check 통과율 80%+
- [ ] Persona consistency baseline 측정 완료
- [ ] Layer 1 ship gate가 매 commit 작동 확인
- [ ] 비용 추적 작동 (한 세션당 API 비용 측정)
- [ ] AI Playtester 3 페르소나 작동 확인 (Cross-Model 매핑 검증)

### Tier 0 Pivot 신호 (다음 단계 가지 말 것)

- 친구 5명 중 3명 이상 "재미없다"
- 본인이 다시 플레이하고 싶지 않음
- 컨셉 자체에 의문 발생
- AI Playtester 모든 페르소나가 "이 게임 의도 모르겠다"

→ Tier 0 결과 회고 → 컨셉 수정 또는 폐기

### Tier 0에서 의도적으로 안 하는 것

- ❌ 로컬 LLM (DGX) — Tier 1 작업
- ❌ 웹 검색 / 작품 자동 파싱 — Tier 1+
- ❌ GBNF — Tier 1 (API는 JSON mode 제공)
- ❌ 캐릭터 5명+ — 1-2명만
- ❌ 다양성 4축 다 구현 — 1축만 (장르 시스템)
- ❌ Save/Load — Tier 2
- ❌ UI 웹페이지 — 콘솔만
- ❌ AI Playtester 6+ 페르소나 — Tier 1
- ❌ Mutation testing — Tier 3

YAGNI. Tier 0의 목적은 **컨셉 검증**이지 완성품 만들기가 아니다.

### Tier 0 실측 결과 (v0.2.1, 2026-04-30)

Tier 0 7일 사이클 완료. 본인 인사이트로 졸업 조건을 가볍게 재해석.

#### 자동 검증 통과 (코드 / 하네스 / 인프라)

- ✅ 하네스 3단 본격 작동 (Mechanical / LLM Judge / Eval Set)
- ✅ Mechanical Checker 7룰 (한국어 특화 포함)
- ✅ LLM Judge + Cross-Model 매트릭스 활성화
- ✅ Eval Set 50 케이스 (5 카테고리)
- ✅ Layer 1 Ship Gate 100/100 A등급
- ✅ AI Playtester 3 페르소나 정의 (다른 CLI 3종)
- ✅ 비용 추적 인프라 (cost_usd / latency_ms)
- ✅ 외부 패키지 추가 0건 (runtime)

#### Tier 1+ 후로 미룸 (본인 인사이트)

- ⏭ 30분 시나리오 완주 가능 — DGX Local LLM 진입 후
- ⏭ 본인 5회 + 친구 3-5명 플레이 — DGX 후
- ⏭ 친구 3명 끝까지 완주 — DGX 후
- ⏭ 정성 피드백 평균 "재미있다" — DGX 후
- ⏭ Mechanical 통과율 80%+ baseline — DGX 후 본격 측정
- ⏭ Persona consistency baseline — DGX 후 본격 측정

이유: `claude -p` latency 14-33초로 도그푸딩 부담. DGX Local LLM (1-3초 예상)에서 본격.

#### 회고 문서

`docs/RETROSPECTIVE_TIER_0.md` 참조.

---

*[섹션 6-10 — 본격 작성]*

---

## 6. Tier 1 — 로컬 LLM + 웹 검색 흐름 (2-3주)

> **목표**: API → 로컬 전환 + 작품 자동 검색·플랜 흐름 작동.

### Tier 1 진입 조건
- Tier 0 졸업 조건 모두 통과
- Tier 0 회고 완료 (잘된 것 / 못된 것 정리)
- DGX Spark 셋업 가능 상태

### Tier 1 작업

**Week 1: 로컬 LLM 인프라 (DGX) — v0.2 결정 반영**
- [ ] DGX Spark 환경 셋업 (CUDA, Python)
- [ ] **추론 서버 측정**: SGLang vs llama-cpp-python (Tier 0 ablation)
  - SGLang RadixAttention 효과 측정 (worldview 공유 prefix)
  - 결과로 primary 결정
- [ ] **모델 측정**: Qwen3-8B Dense vs Gemma 4 E4B
  - 한국어 자연스러움 비교
  - 페르소나 일관성 비교
  - Latency 비교
- [ ] **양자화 측정**: NVFP4 vs MXFP4 vs Q4_K_M
  - DGX Spark 메모리 대역폭 273 GB/s 병목 검증
  - 7B에서 41 TPS, 20B에서 82 TPS 재현 가능한지
- [ ] LLM Client에 local 모델 추가 (기존 추상화 활용)
- [ ] **API ↔ Local 동등성 검증** (eval set 양쪽 실행, 점수 비교)
- [ ] **Filter Pipeline 검증** (GBNF 실패 시 post-hoc JSON 추출, lm-eval 패턴)
- [ ] 추론 속도 측정 (tps), 메모리 사용 측정, KV cache 추적
- [ ] Fallback 체인 작동 확인 (Local → Haiku → Sonnet)
- [ ] **동시 세션 한도 측정**: 7B 모델로 12-15 동시 세션 가능한지

**Week 2: 웹 검색 + 플랜 생성 흐름**
- [ ] 검색 어댑터 (위키 + 일부 커뮤니티, robots.txt 준수)
- [ ] Interview Agent (모호 입력 시 3-5개 질문)
- [ ] Planning Agent (Drafter 역할)
- [ ] Verify Plan Agent (Challenger, Cross-Model 강제)
  - **Challenger는 검색 결과 + 사용자 요청만 봄**, Drafter의 reasoning 못 봄
- [ ] IP Leakage 검증기 (Layer 6+7 통합)
- [ ] 플랜 표시 + 사용자 검토 / 자연어 수정 흐름
- [ ] Diff 표시 (modify intent 시)

**Week 3: 통합 + Layer 1/2 동기화**
- [ ] Layer 2 game loop이 로컬 LLM 사용
- [ ] Layer 1 ship gate가 로컬 LLM도 검증 대상에 포함
- [ ] Cross-Model 매트릭스 정착 (생성/검증 모델 매핑 테이블)
- [ ] 비용 추적 (Local: 0원, API: 호출별)
- [ ] 1시간 플레이 안정성 테스트 (메모리 누수 / KV cache 폭증 점검)
- [ ] **AI Playtester 6 페르소나 전체 작동** (CLI 매핑 정착)
  - claude-code: casual, speed_runner, troll
  - codex-cli: hardcore_fan, roleplayer
  - gemini-cli: confused_beginner
- [ ] 본인 도그푸딩 3회 + 친구 베타 2명 (인간 피드백 우선)

### Tier 1 졸업 조건

- [ ] 100% 로컬 LLM 게임 진행 가능 (API 0회)
- [ ] 응답 평균 latency 5초 이하
- [ ] 1시간 연속 플레이 안정 (메모리 누수 없음)
- [ ] 작품명 입력 → 플랜 생성 → 게임 시작 전체 흐름 작동
- [ ] Plan Verify가 IP leakage 90%+ 잡아냄 (eval 기준)
- [ ] GBNF JSON 100% 유효
- [ ] Cross-Model 검증 작동 확인 (생성 ≠ 검증 모델 강제)
- [ ] **본인 외 사용자 1명 이상이 작품명만 입력해서 게임 끝까지** (외부 사용자 시뮬레이션)
- [ ] AI Playtester 6 페르소나 매일 1회 실행 + 결과 누적
- [ ] 정액제 한도 내에서 AI Playtester 안정 작동

### Tier 1 Pivot 신호

- 로컬 모델 응답 품질이 API 대비 너무 떨어짐 (eval 점수 -20% 이상)
  → 더 큰 모델 시도 / SFT 검토(Tier 3 앞당김) / API 하이브리드 결정
- 웹 검색이 작품 정보를 제대로 못 가져옴
  → 사용자가 정보 직접 붙여넣기 fallback 강화
- 응답 latency 10초 이상 지속
  → 모델 작게, 컨텍스트 줄임, GPU offload 점검
- AI Playtester 페르소나 다수가 같은 이슈 반복 발견
  → 그 이슈 우선 해결 (회귀 시드로 활용)

### Tier 1에서 의도적으로 안 하는 것

- ❌ 다양성 4축 다 구현 — Tier 2
- ❌ 캐릭터 5명+ 동시 — Tier 2
- ❌ Save/Load 정식 — Tier 2 (임시 in-memory만)
- ❌ 웹 UI — Tier 2 시작
- ❌ SFT — Tier 3 (필요 시)
- ❌ 모바일 — 출시 후
- ❌ AI Playtester 10+ 페르소나 — Tier 2

---

## 7. Tier 2 — 다양성 + 안정화 + 웹 UI (4-6주)

> **목표**: 사용자에게 보여줄 만한 품질 + 다양성 + 웹 UI.

### Tier 2 진입 조건
- Tier 1 졸업 조건 모두 통과
- 외부 사용자 1명 이상이 끝까지 플레이
- DGX 로컬 LLM 안정 작동

### Tier 2 작업

**Week 1-2: 캐릭터 / 관계 시스템 강화**
- [ ] 캐릭터 5명+ 동시 관리 (CharacterManager)
- [ ] 페르소나 YAML + 자연어 description
- [ ] 관계 시스템 (trust/affection 수치 → 자연어 변환)
- [ ] 이벤트 → 관계 변화 룰 엔진
- [ ] Hybrid 모드: NPC 백그라운드 tick (이벤트 기반)
- [ ] 캐릭터 일관성 80%+ 달성 (eval 기준)
- [ ] 후처리 검증 + 재생성 루프 (정보 격리 강제)

**Week 3: 다양성 4축 전체 구현**
- [ ] 진입 방식 5가지 선택지 UI
- [ ] 플레이 모드 (단일/파티/진영)
- [ ] 장르 시스템 (모험/관계/경영/추리/정치)
- [ ] 자유도 (충실/분기/자유)
- [ ] 같은 작품 다른 조합 = 다른 게임 검증
- [ ] eval set에 다양성 케이스 추가

**Week 4: Save/Load + DB**
- [ ] SQLite + Drizzle/SQLAlchemy
- [ ] GameState 영속화
- [ ] Event log (모든 이벤트 영구 저장)
- [ ] Save/Load → 컨텍스트 재구성
- [ ] 여러 슬롯 지원
- [ ] 로드 후 게임 진행 깨지지 않음 검증

**Week 5: 웹 UI 시작**
- [ ] 백엔드 API (FastAPI)
- [ ] 프론트엔드 (Next.js)
- [ ] 핵심 화면: 작품 입력 → 플랜 검토 → 게임 진행 → Save/Load
- [ ] 반응형 (모바일 고려, 모바일 전용은 출시 후)
- [ ] 비용/시간 표시 (사용자 신뢰)
- [ ] Empty state 처리 (새 사용자 진입점)
- [ ] **Playwright E2E 테스트 도입** (Layer 1 ship gate에 통합)

**Week 6: Polish + AI Playtester 다양화 + 외부 베타**
- [ ] **AI Playtester 10-12 페르소나로 확장**
  - 추가: explorer / min_max / story_lover / completionist / non_korean / chaos_agent
- [ ] 다양성 4축 모든 조합 자동 시뮬 (cross combination test)
- [ ] 버그 수정 (AI + 인간 도그푸딩 발견 이슈)
- [ ] 5-10명 베타 테스트 (인간 피드백, 우선순위 높음)
- [ ] 정량 (eval) + 정성 (재미) 둘 다 측정
- [ ] 회귀 테스트 (Tier 1 시나리오들 깨지지 않음)
- [ ] Layer 1 ship gate 95+ 유지

### Tier 2 졸업 조건

- [ ] 캐릭터 일관성 80%+ (cross-model eval)
- [ ] 5+ 캐릭터 동시 관리, 관계 일관성 유지
- [ ] Save/Load 안정 (10회 반복 → 깨짐 없음)
- [ ] 1-3시간 캠페인 가능
- [ ] 짧은 세션 (30분) 가능
- [ ] 웹 UI에서 처음~끝 플레이 가능
- [ ] 외부 베타 5명+ 평균 4/5 이상
- [ ] **다양성 4축 모두 작동, 같은 작품 다른 조합 = 다른 게임**
- [ ] 비용 추적 + 사용자 표시 작동
- [ ] Layer 1 ship gate 매 commit 통과
- [ ] AI Playtester 10-12 페르소나 작동, 회귀 케이스 자동 누적

### Tier 2 Pivot 신호

- 캐릭터 일관성 70% 이하 정체 (프롬프트 강화로 안 올라감)
  → Tier 3 SFT 검토 (앞당김) 또는 컨셉 단순화
- 베타 평균 3/5 이하 (인간 피드백 우선)
  → 게임 디자인 재검토 (재미 부족)
- 웹 UI 개발이 계획보다 1.5배 이상 지연
  → MVP 줄이기 / Steam/Itch.io 같은 desktop 출시로 변경 검토
- 다양성 4축 조합이 실제로 다른 게임 느낌 안 줌
  → 축 단순화 (4 → 2-3)

---

## 8. Tier 3 — 출시 준비 + 베타 (2-3주, 또는 SFT 4주)

> **목표**: 공개 출시 가능 품질. SFT는 필요 시.

### Tier 3 진입 조건
- Tier 2 졸업 조건 모두 통과
- 베타 평균 4/5 이상

### Tier 3 작업 (필수)

**Week 1: 출시 인프라**
- [ ] 도메인 + 호스팅 (Vercel/Railway 등)
- [ ] DGX 서빙 외부 노출 (보안 점검)
- [ ] HTTPS, CORS, 인증
- [ ] 사용자 가입 / 게스트 흐름
- [ ] LLM 비용 정책 (게스트 제한 / 본인 API 키 옵션 / 정액제 등)
- [ ] 모니터링 (에러, latency, 비용)
- [ ] 백업 / 복구

**Week 2: 외부 사용자 시뮬레이션 + Polish**
- [ ] 새 환경(다른 PC / 브라우저)에서 첫 사용 시뮬
- [ ] Onboarding 흐름 (첫 사용자가 5분 안에 게임 시작)
- [ ] Empty state 모든 화면 점검
- [ ] 에러 메시지 사용자 친화적
- [ ] 마케팅 메시지 = 실제 동작 검증 (AutoDev 함정 회피)
- [ ] 정직한 한계 명시 (LLM 비용, 응답 시간 등)
- [ ] **AI Playtester 전체 페르소나 + 무작위 변형** (LLM이 즉석 페르소나 생성)
- [ ] **Mutation testing 1회 실행** (mutmut, 정직성 검증)
- [ ] **외부 도구 1회 검증** (lm-eval-harness 등으로 자체 평가 편향 점검)

**Week 3: 공개 베타 + 피드백**
- [ ] 소규모 공개 (Discord 커뮤니티 등)
- [ ] 외부 사용자 20-50명 (인간 베타, 우선순위 최고)
- [ ] 이슈 추적 + 우선순위 분류
- [ ] 핫픽스 vs Tier 3.5 분리
- [ ] 출시 결정

### Tier 3 작업 (선택, SFT 필요 시)

다음 모두 해당 시 SFT 진행:
- [ ] 캐릭터 일관성 70-78% 정체
- [ ] 프롬프트 강화로 더 안 올라감
- [ ] 캐릭터 5명 이상 동시 사용
- [ ] DGX에서 학습 가능

**SFT 작업 (Week 1-4 별도)**:
- [ ] 합성 데이터 5K (Teacher: Claude/GPT)
- [ ] 사람 검증 (20-30% 폐기 예상)
- [ ] Train/Eval split
- [ ] Unsloth + QLoRA 학습
- [ ] Loss 추적 (정상 감소 확인)
- [ ] Eval 비교 (베이스라인 대비 +10%+ 개선 시 채택)
- [ ] GGUF 변환 + 배포

### Tier 3 졸업 조건 (출시 준비)

- [ ] 외부 사용자 20-50명 베타 통과
- [ ] 평균 평점 4/5 이상
- [ ] 처음 5분 안에 게임 시작 가능
- [ ] 비용 정책 명확 + 작동
- [ ] 모니터링 / 에러 추적 작동
- [ ] 마케팅 메시지 정직성 검증 완료
- [ ] Layer 1 / Layer 2 ship gate 동시 95+/70+ 유지

---

## 9. 결정 사항 (Phase B 딥리서치 완료, v0.2)

> 6개 딥리서치 (Claude × 2, Gemini × 2, GPT × 2) 결과 기반.
> 통합 분석 → `INTEGRATED_RESEARCH_ANALYSIS.md`
> Raw 결과 → `research/{01-04}/`

### 9.1 모델 선택 / SFT 전략 — ✅ 결정

#### Tier 0 (API 프로토타입)

```yaml
primary_model: claude-haiku-3.5
verifier_model: gpt-4o-mini      # Cross-Model 강제 (다른 family)
reasoning: |
  - Claude는 한국어 자연스러움 우월
  - Haiku = 빠르고 저렴 (~$0.0008/1k input, $0.004/1k output)
  - GBNF 무관 (post-hoc JSON validation 사용)
  - Tier 0 비용 추정: 한 세션 30턴 ~$0.10
```

#### Tier 1 (DGX Local + Web Search)

```yaml
primary_model: Qwen3-8B Dense
alternative_model: Gemma 4 E4B   # 라이선스 더 깨끗 (Apache 2.0)
quantization: NVFP4              # ★ DGX Spark 메모리 대역폭 병목 해결
inference_server: SGLang         # ★ RadixAttention prefix 캐시 (worldview 공유에 최적)
fallback: claude-haiku-3.5

reasoning: |
  - Dense > MoE: Expert fragmentation으로 long-horizon 페르소나 약함
    (Persona Selection Model, Identity Drift 학술 문헌 검증)
  - 7-14B = 12-15 동시 세션 (5초 latency 달성)
  - 32B+ = 동시성 5-8명, 동시 사용자 모델로 비현실적
  - DGX Spark 273 GB/s 메모리 대역폭이 진짜 병목
  - NVFP4: 7B에서 41 TPS, MXFP4: 20B에서 82 TPS
  - SGLang의 RadixAttention = WorldFork "공유 worldview prompt"에 정확히 맞음

caveats:
  - Qwen 한국어 시 가끔 중국어 토큰 누설 (system prompt로 강하게 제어 필요)
  - Gemma 4의 system role 지원 (Gemma 3의 함정 해결됨)
```

#### Tier 3 SFT (선택)

```yaml
base_model: Qwen3-8B Dense 또는 Gemma 4 E4B
framework: Unsloth               # 단일 노드 최적, GRPO 통합
technique: SFT first, GRPO 검토
data_size: 5000-10000 합성
teacher_models:
  - Claude Opus 4.7
  - GPT-5.5 Pro

avoid:
  - DPO (optimization collapse, WorldSim에서도 검증)
  - PPO (critic memory 2배)

consider:
  - PEAR (Policy Evaluation-inspired Algorithm for Reward)
    SFT-then-RL 가교, catastrophic forgetting 방지
  - HuggingFace KREW Korean role-playing dataset 활용
  - NVIDIA Nemotron Korean Personas (honorific-aware, 2026-04 출시)
```

### 9.2 경쟁 서비스 분석 — ✅ 보강

#### 한국 시장 검증됨

```
시장 활성도:
  - 제타 (스캐터랩): MAU 402만, 월 사용시간 5,248만 시간 (2026-02)
  - Crack (뤼튼): ARR $7000만 (2025년 말)
  - 사용자 87%가 10-20대
  - 일본 확장 검증 (MiraiMind 200만 다운로드)

승자 패턴:
  Characters → Scenes/Plots → Public Chat/Fork → Creator Rewards → Subscription
  반복 루프가 retention의 핵심
```

#### 차별화 포인트 (검증됨)

| 차원 | WorldFork | Crack | 제타 | character.ai | AI Dungeon |
|---|---|---|---|---|---|
| 포지셔닝 | 서사 | 서사 | 서사 | 동반자 | 서사+게임 |
| Plan review/edit | ✅ | ❌ | ❌ | ❌ | ❌ |
| 4축 다양성 | ✅ | ❌ | ❌ | 한정 | ❌ |
| Hybrid game mechanics | ✅ | ❌ | ❌ | ❌ | ✅ |
| 한국어 장르 프리셋 | ✅ | ✅ | ✅ | △ | ❌ |
| Cross-Model verify | ✅ | ❌ | ❌ | ❌ | ❌ |
| 명시적 IP 마스킹 | ✅ | ❌ | ❌ | ❌ | ❌ |

#### 가격 전략 (Tier 3에서 적용)

```yaml
model: 무료 진입 + 웹 구독 + 코인/에피소드 + creator economy

pricing:
  web_subscription: 8,900~12,900원/월
  app_subscription: 11,900~15,900원/월   # 앱스토어 수수료 반영
  preferred: web 결제 (수수료 회피)

subscription_benefits:
  - 더 나은 메모리 / 더 긴 컨텍스트  # ★ 가장 강한 결제 동기
  - 광고 제거
  - 고급 장르 모델
  - 이미지/보이스 크레딧
```

#### 핵심 위험 (한국 시장 특화)

```
1. 개인정보 (이루다 판결, PIPC 제재 + 손해배상 확정)
2. 미성년자 보호 (Character.AI 소송, Kentucky AG, KCSC 가이드라인)
3. IP/실존 인물 (디즈니 경고장, 한국 저작권위원회 가이드라인)
4. 메모리 비용 폭증 (장기 RP의 핵심이자 비용)
5. 커뮤니티 부정적 회전 (필터 / 광고 / 품질)
```

### 9.3 기술 패턴 — ✅ 결정

#### Memory Architecture (Tier 1+)

```yaml
approach: hierarchical
short_term: 컨텍스트 윈도우 (~16K, 모델별 다름)
long_term: 
  - 요약 메모리 (LLM 압축, 매 N턴마다)
  - 관계 메모리 (캐릭터 간, key-value)
  - 로어북 (worldview canon, RAG 사용)

reasoning: |
  - "Lost in the middle" 여전히 존재 (논문 검증, 64K 이상에서 심각)
  - 단순 long context 의존은 narrative consistency 약함
  - Hybrid (short context + structured memory) 권장
  - GPT 1 분석: 메모리가 한국 시장 가장 강한 결제 동기

future_consideration:
  - Recursive Language Models (RLM, 2026 트렌드, Tier 3 검토)
  - Knowledge Graph (Zep/Letta 패턴, Tier 2+ 검토)
  - AriGraph (storyworld 전용)
```

#### Web Search APIs (Tier 1)

```yaml
primary: Brave Search API     # privacy 친화, ToS 명확
alternative: Tavily            # LLM 친화 결과 형식
korean_sources:
  - 나무위키 (gentle scraping, robots.txt 준수)
  - 디시인사이드 / 아카라이브 (커뮤니티 신호, 약함)

avoid:
  - Reddit/Discord 직접 스크래핑 (ToS 위반)
  - 무차별 크롤링 (저작권 + ToS)
```

#### Generative Agents 패턴 (Tier 2+)

```yaml
base: Stanford Generative Agents (Park et al. 2023)
improvements:
  - OASIS pattern (event-driven, no-tick simulation)
  - Persona Collapse 회피 (homogenization 방지)
  
korean_specific:
  - HuggingFace KREW Korean role-playing dataset
  - NVIDIA Nemotron Korean Personas (2026-04)
```

### 9.4 Eval / 테스트 도구 참고 범위 — ✅ 결정

#### 정책: 외부 의존성 0 + 패턴만 차용

4개 도구 모두 분석 완료. 어느 것도 직접 의존성 X.
대신 검증된 패턴 4가지 자체 EvalRunner에 적용:

| 도구 | 차용 패턴 | 적용 위치 |
|---|---|---|
| **promptfoo** | weight × threshold × metric_tag 3-속성<br>redteam plugin × strategy 직교 분리<br>defaultTest 글로벌 negative-rubric<br>position-swap (pairwise) | HARNESS_CORE 5장 Eval Set<br>HARNESS_CORE 4.4 Debate Mode<br>AI Playtester 어드밴서리얼 페르소나 |
| **deepeval** | BaseMetric ABC<br>G-Eval evaluation_steps 자동 생성<br>DAG decision-tree | HARNESS_CORE 3장 LLM-as-Judge<br>HARNESS_CORE 6장 Scoring |
| **ragas** | PydanticPrompt schema 강제<br>claim-decomposition Faithfulness | HARNESS_CORE 3.2 Judge Prompt<br>Tier 1+ 작품 검색 검증 |
| **lm-eval** | Filter pipeline (post-hoc 추출)<br>metadata.version 강제<br>Task versioning | HARNESS_CORE 5.5 Filter Pipeline (신규)<br>HARNESS_CORE 5.4 버전 관리 |

#### 예외: lm-evaluation-harness "RUN_ONCE" 사용

```
용도: Tier 3 출시 전 외부 검증 1회
대상: KoBEST, KMMLU, HAERAE 점수로 generator 후보 모델 1차 필터링
의존: 일시적 (검증 후 제거)
```

#### Tier 0 즉시 적용 코드 (~80줄)

```python
# core/eval/tier0_quickwins.py - 외부 의존 0
1. EvalSet fingerprint 무결성 (lm-eval 패턴)
2. defaultTest 글로벌 negative-rubric (promptfoo 패턴)
   - AI breakout regex 검출
   - IP blocklist + 15단어 인용 휴리스틱
3. 한국어 존댓말/반말 일관성 (mechanical, 외부 도구 어디에도 없음)
4. G-Eval evaluation_steps 자동 생성 + 디스크 캐시 (deepeval 패턴)
5. position-swap pairwise (학술 + promptfoo 패턴)
```

상세 코드: `INTEGRATED_RESEARCH_ANALYSIS.md` Action Items 참조.

### 9.5 재검토 필요한 결정 (Tier 0에서 ablation) — ⚠️ 진행 중

딥리서치에서 새로 제기된 우려. Tier 0 첫 주 측정 후 결정.

#### 9.5.1 Ship Gate Threshold 95+ 적정성

```
우려:
  - Judge LLM은 일반적으로 0.7-0.9 구간에 답 몰림
  - 95+는 노이즈일 수 있음 (4개 외부 도구 모두 0.5 default)
  - geometric_mean 95+가 실제 차이를 만드는지 측정 필요

Tier 0 측정 계획:
  1. Baseline 100 케이스 평가
  2. 점수 분포 확인 (P50, P95, std)
  3. Mechanical (binary) vs LLM Judge (continuous) 비중 조정
  4. 결과로 95+ 유지 vs 90+ vs binary-mech-only 결정
```

#### 9.5.2 Information Isolation 효과

```
우려:
  - 4개 외부 도구 어디도 retry feedback에서 score 격리 안 함
  - 이론적으로는 prompt-leak 방지에 좋지만
  - 실증적으로 score가 가장 강한 학습 신호 (빼면 손실)
  - Claude 2 권장: "어떤 메트릭의 score인지만 안 알려주는 절충"

Tier 0 ablation 계획:
  1. 100 케이스 양쪽 모드 구현
     A: score + verdict 노출 (기존 outside 도구 방식)
     B: issues + suggestions only (현재 HARNESS 방식)
     C: 절충 — score 유지하되 어떤 메트릭의 score인지 비식별
  2. Retry 후 점수 개선폭 비교
  3. 결과로 HARNESS_CORE 8장 최종 확정
```

#### 9.5.3 GBNF 강제 vs 호환성

```
우려:
  - Claude/GPT-4o는 grammar 미지원 (function calling만)
  - GBNF lock-in으로 Layer 1 verifier 후보 좁아짐
  - 자료의 함정 19도 post-hoc 검증 권장

해결책 (Tier 1에서 적용):
  Layer 2 (서비스, 로컬 LLM):
    GBNF 유지 — JSON 100% 안정성
  
  Layer 1 (개발 검증, 다양한 모델):
    Filter Pipeline 패턴 (lm-eval 차용)
    - GBNF 시도 → 실패 시 post-hoc JSON 추출
    - 다양한 추출 전략 병렬
```

### 9.6 새로 등장한 우려 사항

#### 9.6.1 promptfoo OpenAI 인수 (2026-03)

```
영향: default 모델이 OpenAI 계열로 묶일 가능성
대응:
  - 패턴만 차용 (의존성 X) — 이미 우리 정책
  - 추후 promptfoo의 redteam 패턴 변화 추적
```

#### 9.6.2 AutoGen → Microsoft Agent Framework 승계

```
영향: 자료의 "AutoGen 패턴" 일부 outdated
대응:
  - 우리는 자체 구현이라 직접 영향 없음
  - 학습 시 MAF 1.0 (2026-04 GA) 검토
  - ROADMAP 부록의 "AutoGen 자료" 표기는 "AutoGen + MAF 후속" 명시
```

#### 9.6.3 한국 규제 강화 (2026)

```
영향: 출시 전 법적 검토 필수
신규 사안:
  - 한국 AI 기본법 투명성 가이드라인 시행
  - 미성년자 보호 강화 (Character.AI 사례 영향)
  - 이루다 판결 확정 (개인정보 손해배상)

대응 (10장 위험 요소에 반영):
  - 청소년/성인 이원화 from Tier 0
  - 데이터 수집 동의 명시적
  - AI 생성 표시 의무
```

#### 9.6.4 KV Cache 메모리 병목

```
영향: 동시 세션 한도 명시 필요
계산:
  - 7B 모델 + Q4 = ~7GB
  - 추가: KV cache는 컨텍스트 × 활성 세션
  - DGX Spark 128GB 중 시스템 + 모델 + KV 합계
  - 7B에서 12-15 동시 세션 한계 (5초 latency)

대응 (HARNESS_LAYER2에 반영):
  - 동시 사용자 한도 명시
  - KV cache 추적 메트릭 추가
```

---

## 10. 위험 요소 (Risk Register)

> v0.2 업데이트: 한국 시장 분석 결과로 위험 분리.
> 진입 조건이 된 위험은 별도 섹션 (10.2 개인정보, 10.3 미성년자).

### 10.1 저작권 / IP 리스크 (HIGH)

| 위험 | 영향 | 회피 |
|---|---|---|
| 작품 직접 인용 / 캐릭터명 그대로 사용 | 법적 책임, 서비스 중단 | IP Masking 검증기 (Plan Verify) |
| 사용자가 직접 입력한 IP 콘텐츠 | DMCA 등 | "사용자 정의 우선" 포지셔닝 + 약관 |
| 게임 결과물의 저작권 (사용자? 서비스?) | 분쟁 가능 | 약관 명시 (Tier 3 출시 전 법무 검토) |
| AI 학습 데이터 저작권 | 모델 자체 이슈 | Apache 2.0 / 명시적 라이선스 모델만 사용 |
| **디즈니식 경고장** (실존 작품/캐릭터) | 서비스 중단 | 유명 IP 자동 감지 + 사용자 경고 |
| **실존 인물 / 연예인** | 인격권 분쟁 | 초기부터 강하게 차단 |

**의식적 결정** (v0.2 강화):
- 메인: "당신만의 세계관" (사용자 입력 우선)
- 보조: "기존 작품 참고" (영감 차용 수준, IP Masking 강제)
- 검증: Plan Verify Agent가 IP Leakage 점수 매김 (Debate Mode)
- **공식 IP 라이선스 협업** (Tier 3+): 웹소설/웹툰 IP 홀더와 파트너십
- **실존 인물 / 미성년 캐릭터 초기부터 차단**

### 10.2 개인정보 리스크 (HIGH, 한국 시장 진입 조건) ← v0.2 신규

| 위험 | 영향 | 회피 |
|---|---|---|
| 사용자 대화 로그 저장 / 학습 활용 | 이루다 사건 (PIPC 제재 + 손해배상 확정) | 학습 활용 X 명시, 옵트인 동의 강제 |
| 데이터 수집 동의 부재 | 한국 PIPA 위반, 손해배상 가능 | 가입 시 명시적 동의, 약관 투명성 |
| GDPR / K-PDPA 위반 | 글로벌 서비스 불가 | 데이터 처리 정책 명문화 |
| 사용자 데이터 유출 | 평판 + 법적 | 암호화 / 익명화 / 접근 통제 |

**의식적 결정**:
- 사용자 대화는 **모델 학습에 X** (Tier 0부터 약속)
- AI Playtester로 합성 데이터 활용 (사용자 데이터 의존 회피)
- 약관 / 개인정보 처리방침 Tier 3 출시 전 한국 법무 검토 필수
- **이루다 판결 선례**: 한국에서 데이터 출처 적법성 = 평판이 아닌 실질 법적 비용

### 10.3 미성년자 보호 리스크 (HIGH, 진입 조건) ← v0.2 신규

| 위험 | 영향 | 회피 |
|---|---|---|
| 미성년자 부적절 콘텐츠 노출 | 소송 (Character.AI 사례) | 청소년/성인 이원화 from Tier 0 |
| 정신건강 위해 (자해 / 자살 등) | 형사 소송, KCSC 가이드라인 위반 | 안전 필터 + 응급 리소스 안내 |
| 미성년자 데이터 수집 | KCC 이용자 보호 가이드라인 | 나이 확인 강제, 보호자 동의 (필요 시) |
| 청소년 보호법 위반 | 서비스 중단 | 한국 KCC 가이드라인 사전 준수 |

**의식적 결정**:
- **청소년 / 성인 모드 분리** Tier 0부터 설계 (나중에 추가 X)
- 청소년 모드 = 더 강한 안전 필터, 정신건강 리소스 표시
- 성인 모드 = 나이 확인 (성인 인증 메커니즘)
- **Character.AI 소송 사례** 참고:
  - 자해 / 자살 관련 응답 = 즉시 모더레이션 + 리소스 표시
  - 미성년자 오픈엔디드 채팅 제한 검토

### 10.4 메모리 비용 리스크 (HIGH, 차별화 동시에 비용) ← v0.2 신규

| 위험 | 영향 | 회피 |
|---|---|---|
| 장기 RP 컨텍스트 폭증 | 비용 폭발 | Hierarchical memory (요약 + 관계 + 로어북) |
| 메모리 품질이 사용자 차별화 | 무료 사용자 이탈 | 유료 차별화 = "더 나은 메모리" |
| KV Cache 동시 세션 한도 | 동시 사용자 한계 | 7B 모델 = 12-15 동시 세션 명시 |
| Long context 비용 (API 시) | 운영비 압박 | RAG + 외부 메모리 우선 |

**의식적 결정** (GPT 1 한국 시장 분석 기반):
- 메모리 = WorldFork 차별화 핵심
- c.ai+, AI Dungeon, Kindroid, NovelAI 모두 메모리로 유료화
- **무료**: 짧은 세션 / 기본 메모리
- **유료**: 더 긴 세션 / 더 나은 메모리 / 더 많은 캐릭터 추적
- KV Cache는 HARNESS_LAYER2에서 명시적 추적

### 10.5 기술 리스크 (MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| 컨텍스트 폭증 (긴 작품 정보) | 응답 품질 저하 | RAG + 4-16K context 유지 |
| 캐릭터 일관성 70% 정체 | 사용자 이탈 | 프롬프트 강화 → SFT (Tier 3) |
| LLM 환각 (없는 캐릭터/설정 도입) | 게임 깨짐 | World Canon Verify (Mechanical + LLM) |
| DGX 서빙 다운 | 서비스 중단 | API Fallback Chain |
| 응답 latency 10초+ | 사용자 이탈 | 모델 작게 / NVFP4 / SGLang 캐시 |
| KV cache 메모리 폭증 (긴 세션) | OOM | 컨텍스트 요약 + 외부 메모리 |
| **GBNF lock-in** (v0.2 신규) | Layer 1 verifier 후보 좁아짐 | Filter Pipeline (post-hoc 추출 fallback) |
| **MoE 모델 페르소나 fragmentation** (v0.2 신규) | 일관성 약함 | Dense 모델 우선 선택 |


### 10.6 일정 리스크 (MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| Tier 1 DGX 셋업 지연 (2주 → 4주) | 전체 지연 | Tier 0에서 API로 안전 진행 |
| 웹 UI 개발 예상보다 오래 | Tier 2 지연 | Tier 2 MVP 우선 / 모바일은 출시 후 |
| SFT 학습 실패 (loss stuck 등) | Tier 3 지연 | Chat template 사전 검증 / SFT는 선택 |
| "한 번 더" 무한 진행 (마감 못 함) | 컨디션 저하, 품질 저하 | 객관적 마감 데이터 (7가지 체크) |

### 10.7 워크플로 리스크 (HIGH, AutoDev 자료 기반)

| 위험 | 영향 | 회피 |
|---|---|---|
| **Made But Never Used** | 마케팅-실제 gap | Tier 0부터 도그푸딩 강제, ship gate 매 commit |
| **점수 하드코딩** | Verify 정직성 무너짐 | Mechanical = 진짜 점수만, hardcode 금지 |
| **Self-Rationalization** | 자기 코드 자기 통과 | Cross-Model 강제, Challenger 코드 격리 |
| **CI 깨진 채로 운영** | 회귀 누적 | 매 PR 후 GitHub Actions 확인, 자율 fix max 3 |
| **외부 의존성 강제** | 신규 사용자 진입 장벽 | Graceful degradation, Local 우선 |
| **PR 양 = 가치 착각** | 핵심 가치 놓침 | 매 PR 후 "이게 가치 있나" 자문 |

### 10.8 비용 리스크 (LOW-MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| API 비용 폭증 (Tier 0/Fallback) | 개인 부담 | Haiku 우선, 비용 추적, 한도 알람 |
| DGX 전기 비용 | 운영 비용 | 모니터링, 사용 안 할 때 sleep |
| 사용자 LLM 비용 (서비스 출시 후) | 사용자 부담 / 운영 부담 | 명확한 정책 (게스트 제한 / 본인 키 / 정액) |

### 10.9 사용자 리스크 (MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| 작품 정보 부족한 마이너 작품 | "재미없다" | 사용자 직접 입력 fallback |
| 사용자 기대 = 원작 충실 (LLM은 변형) | 실망 | 자유도 축으로 사용자가 선택 |
| 부적절 콘텐츠 생성 (성인/폭력 등) | 신뢰 저하, 법적 | Content moderation 추가 (Tier 2+) |
| 사용자 데이터 (대화 로그 등) 유출 | GDPR 등 | 암호화, 익명화, 명시적 동의 |

### 10.10 AI Playtester 한계 (MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| AI가 "재미"를 측정 못 함 | 정량은 OK인데 실제 재미 없음 | 인간 도그푸딩 병행 (메타 14.5) |
| AI 페르소나가 LLM bias 반영 | 특정 응답 선호 편향 | 다양한 페르소나 + Cross-Model |
| 자기 강화 (게임 LLM = Playtester LLM) | 자기 합리화 | CLI 매핑으로 모델 분리 강제 |
| AI가 못 잡는 정성 이슈 | "이상한데 뭔지 모르겠음" | 인간 1명 = AI 1000명 가치 인정 |

### 10.11 정액제 / 비용 리스크 보강 (LOW-MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| Claude Pro/ChatGPT Plus 한도 초과 | AI Playtester 차단 | 자동 차단 + 알림, 일일 페르소나 수 조절 |
| 정액제 정책 변경 (가격 인상 등) | 비용 증가 | API 직접 호출 fallback 옵션 |
| Claude Code / Codex CLI 외부 변경 | 호환성 깨짐 | Adapter 추상화 (CLI Provider 인터페이스) |

### 10.12 Eval Set 회귀 / 변경 리스크 (MEDIUM)

| 위험 | 영향 | 회피 |
|---|---|---|
| Eval set 변경 시 비교 깨짐 | 회귀 측정 불가 | 버전 관리 (v1, v2, v3) + 보존 |
| 새 케이스가 너무 어려움 | 점수 급락, 실제 회귀 아님 | 변경 시 영향 측정 → 적용 |
| Judge model 변경 | 점수 체계 변동 | Judge 변경 시 baseline 재측정 |

---

## 11. 테스트 전략 (4 층위 + AI Playtester)

> **이 섹션이 하네스의 선결 조건**. 테스트 없는 검증 시스템 = 검증 시스템 자체를 검증할 수 없음.

### 11.1 4 층위 모델

WorldFork에서 "테스트"는 4가지 다른 의미를 가진다. 각각 다른 도구/방법.

| 층위 | 대상 | 도구 | 특징 |
|---|---|---|---|
| **층위 1: 코드** | 결정론적 로직 (게임 룰, 상태, DB) | pytest / Vitest | 입력→출력 결정적, mock LLM |
| **층위 2: Eval** | LLM 응답 분포 | 자체 eval runner + LLM-as-Judge | 분포로 평가, 회귀 비교 |
| **층위 3: E2E** | 사용자 흐름 전체 | pytest 시나리오 + Playwright (Tier 2+) | 처음~끝 작동 |
| **층위 3.5: AI Playtester** | "사용자 경험" 자동 시뮬 | Claude Code + Codex CLI + (Gemini CLI) | 다양한 페르소나로 자동 |
| **층위 4: 인간** | "재미" / 정성 | 본인 + 친구 + 베타 | 자동화 불가 |

**원칙**:
- 모든 결정론적 로직 = 층위 1 필수
- 모든 LLM 응답 = 층위 2 필수
- 모든 사용자 흐름 = 층위 3 시나리오 1개+
- 모든 Tier 끝 = 층위 4 강제 (도그푸딩)
- 인간 피드백 > AI 시뮬 (메타 14.5)

### 11.2 Layer 1/2 매트릭스

각 층위가 두 Layer에서 다르게 작동:

```
            Layer 1 (개발)              Layer 2 (서비스)
            ─────────────              ─────────────
층위 1     pre-commit hook              런타임 invariant
(코드)     매 commit 자동                (HP/인벤토리 깨짐 X)
           예: pytest

층위 2     ship gate 30%                매 응답 검증
(Eval)     매 commit 회귀 체크           재시도 트리거
           예: persona_eval

층위 3     CI 통합 테스트                사용자 흐름 모니터링
(E2E)      매일 1회 전체 시나리오         에러율 추적

층위 3.5   매 commit AI 1-2 페르소나 빠른    매 주요 기능 추가 후 전체
(AI)       주 1회 전체 페르소나           실패 케이스 → eval 시드

층위 4     매 Tier 끝 도그푸딩          외부 베타 + 피드백
(인간)     본인 + 친구                  20-50명 (Tier 3)
```

같은 층위가 양쪽에서 다른 정책. 자료의 "구조 유사 + 별도 정책" 패턴.

### 11.3 도구 스택

```yaml
Python 측 (백엔드 + LLM + 게임 로직):
  pytest:           # 표준
  pytest-asyncio:   # async LLM 호출
  pytest-cov:       # coverage
  pytest-mock:      # mock 간편화
  pytest-xdist:     # 병렬 실행 (eval 시)
  hypothesis:       # property-based testing (게임 룰)

TypeScript 측 (프론트, Tier 2 진입 시):
  vitest:           # Jest 호환 + 빠름
  @testing-library/react:
  msw:              # API 모킹

E2E (Tier 2+):
  Playwright:       # 웹 UI

Eval Runner (자체 제작 + 기존 도구 패턴 차용):
  자체 핵심:        # WorldFork specific
  promptfoo 차용:   # YAML 평가셋 형식
  deepeval 차용:    # judge metric 정의
  ragas 차용:       # 충실도 측정 (RAG 평가, Tier 1+)
  lm-eval-harness:  # Tier 3 출시 전 외부 검증 1회

AI Playtester:
  claude-code CLI:  # Claude Pro/Max 정액제
  codex CLI:        # ChatGPT Plus 정액제
  gemini CLI:       # 선택, 정액제

Coverage 목표:
  Python core:      80%+
  TypeScript:       70%+
  LLM 통합:         별도 (Eval로 커버)
```

### 11.4 AI Playtester 상세

**구조**:

```python
# tools/ai_playtester.py
class AIPlaytester:
    def __init__(self, persona: Persona, cli_provider: CLIProvider):
        self.persona = persona
        self.cli = cli_provider  # claude-code / codex-cli / gemini-cli
    
    def play_session(self, game_endpoint, n_turns=30):
        prompt = self.persona.to_prompt(game_endpoint, n_turns)
        result = self.cli.invoke(prompt)
        return self.parse_verdict(result)
```

**CLI 매핑 원칙**:

```
게임 LLM (검증 대상) ≠ Playtester LLM (검증 주체)

게임:                           Playtester:
- Tier 0: Claude Haiku (API)    Codex CLI (다른 모델)
- Tier 1+: 로컬 Qwen             Claude Code 또는 Codex CLI
- Tier 3 SFT: 자체 SFT 모델     Claude Code + Codex CLI 혼합
```

**페르소나 정의 파일** (`personas/{id}.yaml`):

```yaml
id: casual_korean_player
version: 1
language: ko
demographic: "한국 20대"

behavior:
  response_length: short
  pace: medium
  patience: low

preferences:
  fun_factor: high
  story_depth: medium
  challenge: low

expected_findings:
  - "Onboarding이 5분 넘으면 이탈"
  - "복잡한 시스템 거부감"
  - "자연스러운 한국어 기대"

cli_to_use: claude-code

prompt_template: |
  너는 한국 20대 캐주얼 게이머야.
  - 짧고 간결한 응답 선호
  - 복잡하면 빨리 이탈
  - "재미"가 최우선
  ...
```

### 11.5 AI Playtester 페르소나 — Tier별 구성

```
Tier 0 (3개, 가벼움):
  - casual_korean_player    한국 20대 캐주얼
  - troll                   이상한 입력 시도
  - confused_beginner       처음 게임, 자주 막힘

Tier 1 (6개, 기본):
  + hardcore_lore_fan       원작 깊이 아는 팬
  + speed_runner            빠른 진행 선호
  + roleplayer              캐릭터 몰입, 자연어 길게

Tier 2 (10-12개, 다양화):
  + explorer                구석구석 탐험
  + min_max_optimizer       최적 빌드 추구
  + story_lover             스토리 깊이
  + completionist           모든 옵션 시도
  + non_korean_speaker      영어 섞어 입력
  + chaos_agent             예상 못한 메타 발언

Tier 3 (전체 + 변형):
  + returning_player        Save/Load 검증
  + power_user              고급 기능 사용
  + 무작위 페르소나 변형     LLM이 즉석에서 페르소나 생성
```

각 페르소나 = 1개 YAML. 추가/수정 쉬움. **다양성 = 발견 가능성**.

### 11.6 정보 격리 (자료 패턴 적용)

```
게임 LLM → 응답 생성
        ↓
Playtester LLM (다른 모델) → 평가
        ↓
재시도 시 게임 LLM에 전달:
  ✅ issues + suggestions
  ❌ 점수 (페르소나별 평점)
  ❌ verdict (pass/fail)

이유: 점수 게이밍 방지 (자료의 "85점이니 살짝만 고치면" 합리화 차단)
```

### 11.7 Tier 0 Ablation Plans (v0.2 신규, 딥리서치 후속) ← 신규

> 6개 딥리서치 결과 일부 결정에 우려 제기. Tier 0 첫 주에 측정 후 최종 확정.

#### 11.7.1 Information Isolation 효과 측정

```
배경:
  - 4개 외부 도구 (promptfoo, deepeval, ragas, lm-eval) 어디도 retry 시 score 격리 안 함
  - 이론적: prompt-leak 방지에 좋음
  - 실증적 의문: score가 가장 강한 학습 신호인데 빼면 손실

측정 계획:
  N: 100 케이스
  카테고리: persona_consistency / korean_quality 위주
  
  3가지 모드 비교:
    A: score + verdict 노출 (외부 도구 표준)
    B: issues + suggestions only (현재 HARNESS)
    C: 절충 — score 유지하되 메트릭 비식별
  
  메트릭:
    - Retry 후 점수 개선폭
    - Pass rate 변화
    - 특정 함정 (prompt leak 시도) 발생 빈도

결과 → HARNESS_CORE.md 8장 최종 확정
```

#### 11.7.2 Ship Gate Threshold 측정

```
배경:
  - Judge LLM 출력은 보통 0.7-0.9에 몰림
  - 95+가 노이즈일 수 있음
  - 4개 외부 도구 모두 0.5 default

측정 계획:
  Tier 0 baseline 100 케이스 평가
  
  분석:
    - 점수 분포 (P50, P95, std)
    - Mechanical (binary) vs LLM Judge (continuous) 비중
    - 95+ 통과 사례의 실제 품질 vs 90+ 통과 사례
  
  결정:
    - 95+ 유지 (binary mech 비중 강화)
    - 90+로 완화
    - binary-mech-only 게이트 (LLM judge는 정보용)

결과 → HARNESS_LAYER1_DEV.md Ship Gate 정책 확정
```

#### 11.7.3 GBNF Filter Pipeline 검증 (Tier 1)

```
배경:
  - GBNF는 llama.cpp / vLLM grammar 의존
  - Claude / GPT-4o는 grammar 미지원 (function calling만)
  - Layer 1 verifier가 다양한 모델 사용 → fallback 필요

검증 계획 (Tier 1 진입 시):
  - GBNF 시도 → 성공 시 그대로
  - GBNF 실패 시 Filter Pipeline (post-hoc 추출)
    - JSON 마크다운 fence 제거
    - 다양한 추출 정규식 병렬 시도
    - 파싱 실패 시 재시도 prompt
  - 100 케이스에서 양 모드 성공률 비교

결과 → HARNESS_CORE.md 5.5 Filter Pipeline 확정
```

### 11.8 비용 / 한도 관리

```
정액제 우선 (Claude Pro / ChatGPT Plus):
  - 한도 내 = 추가 비용 0
  - 한도 초과 = 자동 차단 + 알림
  - 일일 페르소나 수 동적 조절

API 직접 호출 = Fallback:
  - 정액제 한도 초과 시
  - 또는 정액제 정책 변경 시
  - 비용 추적 + 한도 알람

Tier별 일일 비용 추정:
  Tier 0: 정액제만 (3 페르소나 × 1회/일)
  Tier 1: 정액제만 (6 페르소나 × 1회/일)
  Tier 2: 정액제 + 가끔 API (12 페르소나)
  Tier 3: 정액제 + API (전체 + 외부 검증)
```

---

## 12. Living Harness — 변경 가능한 검증 시스템

> 자료의 "함정 32: 한 번 작동 = 영원히 작동" 회피.
> 검증 방식과 기준은 개발 진행에 따라 **얼마든지 변경 가능**해야 한다.

### 12.1 외부 설정 (harness.yaml)

검증 정책을 코드 외부로 분리:

```yaml
# config/harness.yaml
layer1:  # 개발 하네스
  threshold: 95
  retries: 0
  evals:
    - persona_consistency
    - korean_quality
    - json_validity
    - ip_leakage
    - world_consistency
  judge_models:
    primary: claude-haiku-3.5
    challenger: gpt-4o-mini

layer2:  # 서비스 하네스
  threshold: 70
  retries: 3
  evals:
    - mechanical_only  # 빠른 일부만
  judge_models:
    primary: local_qwen_2b
    fallback: claude-haiku-3.5

eval_sets:
  persona_consistency:
    version: v1
    items: 50
    file: evals/persona_v1.jsonl
    weight: 0.3
  
  korean_quality:
    version: v1
    items: 30
    file: evals/korean_v1.jsonl
    weight: 0.2
  # ...

scoring:
  algorithm: weighted_sum  # or geometric_mean
  fail_fast: true          # mechanical 하나만 실패해도 즉시 fail

ai_playtester:
  enabled: true
  personas_active:
    - casual_korean_player
    - troll
    - confused_beginner
  daily_runs: 1
  cli_mapping:
    casual_korean_player: claude-code
    troll: codex-cli
    confused_beginner: gemini-cli
```

### 12.2 Eval Set 버전 관리

Eval set 자체도 버전 관리:

```
evals/
├── persona_consistency/
│   ├── v1.jsonl              # 첫 버전
│   ├── v2.jsonl              # 추가/수정
│   ├── v3.jsonl              # 현재
│   └── CHANGELOG.md          # 변경 이력
├── korean_quality/
│   ├── v1.jsonl
│   └── ...
└── ...
```

회귀 비교 시 같은 버전 사용:

```python
# 비교 시
new_score = run_eval(new_model, eval_set='persona_v3')
old_score = run_eval(old_model, eval_set='persona_v3')  # 같은 버전
```

### 12.3 변경 절차

```
1. 변경 제안 (git commit message 또는 ROADMAP에 기록)
   예: "eval: persona_consistency v3 추가
        - 시간선 일관성 케이스 5개 추가
        - 한국어 비속어 처리 케이스 추가"

2. 영향 측정
   - 현재 모델로 v2 vs v3 점수 비교
   - 점수 ±10% 이상 차이 → 분석
   - 어느 케이스가 점수 차이 만드는지 확인

3. 적용
   - config/harness.yaml에서 v3 활성화
   - 첫 적용 시 baseline 재측정
   - Layer 1/2 모두 동일 버전 사용

4. 회고 (1주 후)
   - 변경이 의미 있었나
   - 새 케이스가 실제 문제 발견했나
   - 점수 분포 어떻게 변했나
```

### 12.4 변경 가능 항목 분류

```
변경 자주 (개발 중, 매 commit 가능):
  - threshold (점수 기준)
  - retry 횟수
  - eval set 항목 추가/수정
  - judge model 변경
  - weight 조정
  - AI Playtester 페르소나 활성화

변경 가끔 (Tier 진입 시):
  - eval set 카테고리 추가
  - scoring algorithm
  - cross-model 매핑
  - CLI provider 변경

변경 드뭄 (전체 회고 시):
  - 4 층위 구조 자체
  - 두 Layer 분리
  - 정보 격리 원칙
```

### 12.5 회귀 방지

검증 시스템 자체의 회귀 방지:

```
- 이전 eval set 버전은 절대 삭제 X (보존)
- 새 버전 추가 시 이전 버전과 비교 데이터 저장
- harness.yaml 변경 = git diff로 기록
- 매 변경마다 baseline 재측정 + 결과 기록
```

자료의 "함정 32: 평가 셋 다양화 + 베타 사용자 피드백" 패턴.

---

## 13. 머신 구성

### 13.1 개발 PC (메인 작업)

```
역할:
- Claude Code 메인 작업
- VSCode / IDE
- WorldFork repo 개발
- pytest / 단위 테스트
- 게임 실행 (DGX의 LLM 호출)
- Layer 1 ship gate 실행

요구 사양:
- Claude Code 돌릴 정도 = 일반 개발 PC OK
- 16GB RAM 이상 권장
- 디스크 50GB+ (모델 캐시는 DGX)
```

### 13.2 DGX Spark (LLM 서빙 + 학습)

```
역할:
- 로컬 LLM 서빙 (llama-server, 포트 8080)
- LLM 학습 (Tier 3 SFT 시)
- 모델 GGUF 파일 보관
- 무거운 GPU 작업

접근 방식:
- SSH로 명령 실행
- 필요 시 Claude Code도 DGX에서 ssh로 호출 가능
- 헤드리스 (GUI 불필요)

구성:
- llama-cpp-python 서버 모드
- HTTP API 노출 (개발 PC에서 호출)
- 학습은 Unsloth + QLoRA
```

### 13.3 git 형상관리 (WorldFork repo)

```
원격: https://github.com/hyunlord/WorldFork
브랜치: main (직접 작업)

워크플로:
- 개발 PC = 코드 작성, commit, push
- DGX = pull, 모델/데이터 동기화
- main만 사용 (1인 개발, branch 분기 없음)
- Layer 1 ship gate가 push 전 검증
```

### 13.4 분리 원칙 (자료 적용)

```
자료의 "Anti-Pattern 7: 외부 의존성 강제" 회피:
  - DGX 다운돼도 개발 가능 (API fallback)
  - 개발 PC만으로도 Tier 0 진행 가능
  - DGX는 "더 좋은 옵션"이지 "필수"가 아님

자료의 "메타 5: 반복 가능성":
  - 코드 = git에 (재현 가능)
  - 모델 = HuggingFace (재현 가능)
  - DGX 로컬에만 있는 코드 = 금지
```

---

## 14. 메타 — 이 ROADMAP의 사용법

### 14.1 살아있는 문서 (Living Document)

- ROADMAP은 **고정된 계획서**가 아니라 **진행 중 업데이트하는 문서**
- 각 Tier 졸업 시 회고 → 다음 Tier 작업 항목 보강
- 미해결 의사결정 풀릴 때마다 해당 섹션 업데이트
- git log로 ROADMAP의 변경 이력 추적

### 14.2 검증 없이 다음 단계 X (자료의 메타 2)

- Tier 졸업 조건 = 정량 + 정성 + 측정 가능
- 조건 미달 시 → 다음 Tier 진입 금지 → Pivot 또는 보강
- 조건 통과해도 회고 후 진행

### 14.3 YAGNI 절대 (자료의 메타 3)

- 각 Tier에 "의도적으로 안 하는 것" 섹션 명시
- "나중에 필요할 수도" = 거의 항상 안 필요함
- 의심 시 Tier 다음으로 미룸

### 14.4 사용자 (자기 자신) 즐거움 우선 (자료의 메타 4)

- 흥미 떨어지면 잠시 멈춤
- "의무감" 으로 진행 = 산출물 품질 저하
- 즐거움 = 산출물 품질 가장 강한 신호

### 14.5 인간 피드백 우선순위 (AI 시뮬보다 무겁게)

- AI Playtester가 "괜찮다"고 해도 인간이 "안 좋다"면 인간 우선
- AI 1000회 시뮬 < 인간 1명의 "와닿지 않아요"
- 자료의 함정 31 회피: "정량 지표만 신뢰 → 일관성 85% → 사용자는 재미없다"
- AI는 양/회귀, 인간은 질/재미

### 14.6 다음 세션 시작 시 컨텍스트

다음 Claude / Claude Code 세션 시작 시 던지기:

```
WorldFork 프로젝트 ROADMAP.md, HARNESS_*.md, AI_PLAYTESTER.md, 
INTEGRATED_RESEARCH_ANALYSIS.md 읽고 시작.

현재 위치: Tier {0/1/2/3} {진행중/졸업}, 문서 v0.2
머신: 개발 PC (작업) + DGX Spark (LLM 서빙)
레포: https://github.com/hyunlord/WorldFork (main)

핵심 원칙:
1. 두 Layer 시스템 (개발 + 서비스, 같은 코어)
2. Made But Never Used 회피 (도그푸딩 강제)
3. Cross-Model Verify (self-rationalization 방지)
4. 정보 격리 (점수 누설 X, issues only) — v0.2 ablation 검증 중
5. Mechanical 우선 (0 토큰 게이트)
6. YAGNI + 검증 우선
7. Living Harness (검증 기준 변경 가능, 외부 설정)
8. AI Playtester는 양/회귀, 인간은 질/재미 (인간 피드백 우선)
9. CLI 활용 (claude-code / codex-cli / gemini-cli 정액제)

v0.2 결정 사항 (Phase B 완료):
- Tier 1 모델: Qwen3-8B Dense + NVFP4 + SGLang (DGX 메모리 병목)
- Tier 0 모델: Claude Haiku 3.5 + GPT-4o-mini (cross-model)
- Eval 패턴: promptfoo / deepeval / ragas / lm-eval 차용 (의존성 X)
- 한국 시장 차별화: 서사형 + 4축 다양성 + 한국어 장르 프리셋
- 위험: 개인정보 + 미성년자 + 메모리비용 = 진입 조건

v0.2 재검토 항목 (Tier 0에서 ablation):
- Ship gate 95+ 적정성 → 90+ vs binary-mech-only 결정
- Information Isolation 효과 → 절충안 검토
- GBNF lock-in → Filter Pipeline fallback
```

---

## 15. 다음 작업 (이 ROADMAP 다음)

순서:

**Phase A: HARNESS 문서 작성** (다음 즉시)
1. **HARNESS_CORE.md** — 공유 검증 코어 상세 설계
   - 4 층위 모델 구체화
   - Mechanical / LLM-Judge / Cross-Model 구현 패턴
   - Eval Set 구조 + 버전 관리
   - Scoring 알고리즘
   - 5-section system prompt 템플릿
2. **HARNESS_LAYER1_DEV.md** — 개발 하네스
   - verify.sh / ship.sh 스크립트
   - pre-commit hook
   - GitHub Actions CI workflow
   - Layer 1 threshold 95+ 정책
3. **HARNESS_LAYER2_SERVICE.md** — 서비스 하네스
   - Pipeline (Interview → Plan → Verify → Game Loop)
   - Retry policy + Information Isolation
   - Fallback chain (Local → API)
   - Layer 2 threshold 70+ 정책
4. **AI_PLAYTESTER.md** — 별도 문서로 분리 (검증 시스템의 핵심)
   - 페르소나 정의 형식
   - CLI 매핑 매트릭스
   - 결과 누적 + eval 시드 흐름

**Phase B: 딥리서치** (Phase A 완료 후)
5. **딥리서치 프롬프트 작성** (Claude / GPT / Gemini 분담)
6. **딥리서치 실행** (사용자가 각 모델에 보내고 결과 가져옴)
7. **결과 통합 → ROADMAP / HARNESS v0.2 업데이트**

**Phase C: 실제 작업 시작**
8. **Tier 0 시작** (WorldFork 레포 첫 commit, 머신 셋업)

---

## 부록 A: 참조 문서 (이 프로젝트 컨텍스트)

이 ROADMAP의 결정에 사용된 자료:

### WorldSim 자료 (10K agent civilization simulator, 1년 검증)
- `00_README.md` — 전체 개요
- `01_concept_and_difficulty.md` — 컨셉 + 시뮬 난이도 회피
- `02_local_llm_stack.md` — llama.cpp + GGUF + 모델
- `03_character_and_persona.md` — 페르소나 시스템
- `04_structured_output.md` — GBNF JSON
- `05_prompt_engineering.md` — 프롬프트 패턴
- `06_training_or_not.md` — SFT 판단
- `07_state_and_scenario.md` — 상태 + 분기
- `08_implementation_roadmap.md` — Tier 0-3 패턴
- `09_pitfalls.md` — 32가지 함정
- `10_quick_reference.md` — 빠른 참조

### AutoDev Agent 자료 (멀티 에이전트 오케스트레이터, 6개월)
- `00-overview.md` — 4가지 핵심 가치
- `01-adpl-pipeline.md` — DSL + Engine 설계
- `02-multi-agent.md` — Plan/Code/Verify 분리 + Cross-Model
- `03-ai-builder.md` — 자연어 → DSL 패턴 (5-section, retry loop)
- `04-verify-honest.md` — 정직한 검증 시스템
- `05-workflow-patterns.md` — Ship/Streak/CI 패턴
- `06-anti-patterns.md` — 8가지 안티패턴

### AutoDev Harness 설명
- 두 Layer 시스템 (Dev + Service, 같은 엔진 공유)
- 검증 3계층 (Mechanical / VLM / LLM Cross-Check)
- 정보 격리 (점수/verdict/code 격리)
- 12개 Hook 이벤트
- 3-tier 프롬프트 로딩
- 에러 4-tier 분류 + Fallback 체인

---

## Tier 1.5 — 하네스 재구축 (★ 2026-05-02 본인 #15-#18 후)

★ 트리거: W2 D5 본인 첫 풀 플레이 → "사람이 검증할 가치 없는 상태" 짚음

### 진단
- 22 commits 동안 두 하네스 모두 30%만 진척
- Ship Gate 100/100 12번 = 자기 합리화 점수
- Verify Agent verify.sh = import 검증만 (가짜)

### 본인 인사이트
- #15: Layer 2 (서비스) 미통합
- #16: 사람 검증 = 게이트 통과 후만
- #17: Layer 1 (개발) 자동화 X
- #18: ★ 자기 합리화 차단 미구현

### 4 사이클 ROADMAP
참고: `docs/TIER_1_5_HARNESS_REBUILD_ROADMAP.md`

```
D1: Layer 1 인프라 + Verify Agent (★ 본격)
D2: Layer 1 Hook 시스템 + 자율 Fix
D3: Layer 1 CI + Re-plan + Eval Smoke 진짜
D4: Layer 2 통합 (★ 가볍게, Layer 1 타도록)
D5 (게이트 후): 본인 첫 진짜 검증 가능 플레이
```

### 환경 매핑
- Layer 1 (개발): codex + local qwen + claude code (★ 매 단계 독립)
- Layer 2 (서비스): local만 (★ ComfyUI 내릴 수도)

### 게이트 (★ 본인 #16)
- 게이트 1: Layer 2 자동 검증 통합 (D4)
- 게이트 1.5: Layer 1 자동화 (D1-D3)
- 게이트 2: 게임 완성도 (Tier 2)
- 게이트 3: Web UI (Tier 2)
- ★ 모든 게이트 통과 = 사람 검증 (Tier 2 후반)

---

*문서 끝. v0.2 — Tier 1.5 추가.*
