# Tier 0 회고 (2026-04-29 ~ 2026-04-30)

> ROADMAP 6장 "Tier 1 진입 조건"의 "Tier 0 회고 완료" 항목 충족.

---

## 0. 한 줄 요약

Tier 0 7일 사이클 완료. **~6,142줄 코드, 223+ tests pass, Ship Gate 100/100 A등급**.
하네스 3단 (Mechanical / LLM Judge / Eval Set) 모두 정확히 구현. 본인 인사이트로 도그푸딩은 Tier 1+ DGX 후로 합리적 미룸.

---

## 1. 핵심 통계

| 항목 | 수치 |
|---|---|
| 기간 | 2026-04-29 ~ 2026-04-30 (실제 작업) |
| 누적 commit | 8개 (abcd0ec → 5ed9eb8) |
| 누적 코드 | ~6,142줄 |
| 누적 테스트 | 223개 (slow 2 deselected) |
| Ship Gate | 100/100 A등급 |
| 외부 패키지 추가 | 0건 (runtime) |

### Day별 산출물

| Day | 핵심 산출물 | 비고 |
|---|---|---|
| 1 | LLMClient + 첫 시나리오 (novice_dungeon_run) | CLI 3종 추상화 |
| 2 | 분기 메타데이터 + Phase 추적 | BranchMeta, PhaseTracker |
| 3 | ★ Mechanical 7룰 (한국어 특화 포함) | 0-토큰 게이트 |
| 4 | ★ LLM Judge + Cross-Model + Retry | 정보 격리 + Ablation 인프라 v0.1 |
| 5 | ★ Eval Set + Filter + Ship Gate | 50케이스, 5카테고리 |
| 6 | Ablation v0.2 + AI Playtester (3 페르소나) | FeedbackMode ENUM |
| 7 | 졸업 + 회고 (이 문서) | 정리·문서 중심 |

---

## 2. 잘된 것

### 2-1. 하네스 3단 본격 작동

```
Mechanical (즉시 실패, 0 토큰)
  → LLM Judge (품질 평가, 점수 기록)
  → Eval Set (회귀 측정, 50 케이스)
```

매 commit Ship Gate 자동 검증 (100/100 A등급 유지).

### 2-2. 자료 패턴 정확히 적용

- HARNESS_CORE 2-9장 모두 구현
- 한국어 특화 룰 (외부 도구에 없는 차별화)
- Cross-Model 강제 (Wataoka 2024 패턴)
- Information Isolation Ablation 인프라

### 2-3. 외부 패키지 0건 streak 유지

- CLI subprocess만으로 cross-family 호출 (claude / codex / gemini)
- anthropic / openai / google SDK 추가 X
- 정액제 OAuth만 사용 (비용 $0)

### 2-4. 워크플로 작동

```
Claude.ai (검증자 / 프롬프트 작성)
  + Claude Code (실행자 / 코드 작성)
  + 본인 (메신저 / 최종 결정자)
```

각 사이클마다 git pull로 코드 검증. 두 Layer 시스템 (개발 + 서비스) 패턴 그대로.

### 2-5. Claude Code 능동성

- Day 3: `korean_rules.py` regex 오탐 자동 발견 + 수정
- 단순 코드 작성자가 아닌 능동적 검증자 역할

---

## 3. 못된 것 / 한계

### 3-1. claude -p latency 14-33초

실제 도그푸딩 부담. 환경 검증 시 12.7초였지만 실사용 시 변동 큼.
→ **Tier 1+ DGX Local LLM (1-3초 예상)에서 해결**.

### 3-2. service/game/loop.py coverage 36% 그대로

`play_game()` E2E 영역 단위 테스트 어려움.
→ Tier 1+ EvalRunner 통합 시 자연 보완.

### 3-3. Ablation 실측 skip

Mock으로만 인프라 검증. FeedbackMode별 실제 점수 차이 미측정.
→ Tier 1+ DGX에서 본격 측정.

### 3-4. 본격 도그푸딩 X

본인 1-2회 동작 확인만. 친구 베타 X.
→ Tier 1+ DGX 진입 후.

### 3-5. ★ Day 6 메모리 70GB 폭증 사고

**원인**: pytest 4개 프로세스 동시 실행 + `--cov` 누적.
`.coverage.*pid*.*` 파일 4개 생성 = 4중 병렬 pytest.

**학습**:
- pytest 호출은 작업당 1회만
- `--cov` 옵션은 최종 검증 1번만
- subprocess가 pytest 부르는 패턴 금지 (무한 재귀 위험)
- 각 작업 검증은 가벼운 `python -c import`만

**Day 7부터 적용**: `graduation_check.sh`에서 `verify.sh` 호출 제거.
`test_graduation.py` 삭제 (subprocess→pytest 재귀 제거).

---

## 4. 본인 인사이트 검증

### 인사이트 1: "검증이 잘되고 있는지 모르겠어" (Day 1)

**해결**: Day 3-5에서 명시적 가시화.
```
콘솔에 [Mechanical: 7/7 통과 ✅] 명확히 표시
Ship Gate 100/100 A등급 자동 검증
```

### 인사이트 2: "DGX Spark 후부터 본격 테스트" (Day 1)

**검증**: ROADMAP 패턴과 정합.
```
Tier 0 = 컨셉 검증 (코드 + 하네스)
Tier 1+ = 본격 도그푸딩 (Local LLM + 친구 베타)
```

### 인사이트 3: "75% coverage 만족하는게 맞나?" (Day 2)

**해결**: Day 3부터 핵심/E2E/의도 분류.
```
🟢 핵심 95+, 미커버 모두 의도적 → OK
🟡 일부 의도적 → review
🔴 빠뜨림 발견 → 추가 작업
```

### 인사이트 4: "Claude Code에 시켜야지" (Day 2 환경 검증)

**검증**: 워크플로 핵심 패턴.
```
저(Claude.ai) = 검증자 + 프롬프트 작성
Claude Code  = 실행자 + 코드 작성
본인         = 메신저 + 최종 결정자
```

### 인사이트 5: "사용자 직접 플레이 X" (Day 3)

**검증**: ROADMAP 메타 14.4 (YAGNI) 정합.
```
Tier 0에서 게임 재미 검증 X
졸업 조건 = 코드 + 하네스 작동
재미는 Tier 1+ DGX 후 본격
```

---

## 5. 자료 패턴 검증 결과

| 자료 섹션 | 구현 여부 | Day |
|---|---|---|
| HARNESS_CORE 2장 — Mechanical | ✅ | Day 3 |
| HARNESS_CORE 3장 — LLM Judge | ✅ | Day 4 |
| HARNESS_CORE 4장 — Cross-Model | ✅ | Day 4 |
| HARNESS_CORE 5장 — Eval Set | ✅ | Day 5 |
| HARNESS_CORE 5.5 — Filter Pipeline | ✅ | Day 5 |
| HARNESS_CORE 6장 — Scoring | ✅ | Day 5 |
| HARNESS_CORE 7장 — 5-Section Prompt | ✅ | Day 1+ |
| HARNESS_CORE 8장 — Retry + Information Isolation | ✅ | Day 4 |
| HARNESS_CORE 8.4 — Ablation 인프라 v0.2 | ✅ | Day 4+6 |
| HARNESS_CORE 9장 — LLM Client 추상화 | ✅ | Day 1 |
| HARNESS_LAYER1_DEV 2장 — Ship Gate | ✅ | Day 5 |
| AI_PLAYTESTER 2.1 — 페르소나 YAML | ✅ | Day 6 |
| AI_PLAYTESTER 3.1 — Tier 0 3 페르소나 | ✅ | Day 6 |

---

## 6. Tier 1 진입 결정

### 진입 조건 체크 (ROADMAP 6장)

| 항목 | 상태 |
|---|---|
| Tier 0 졸업 조건 자동 검증 모두 통과 | ✅ |
| Tier 0 회고 완료 (이 문서) | ✅ |
| DGX Spark 셋업 가능 상태 | ⏭ 본인 결정 |

### Tier 1 진입 시 우선순위

```
Week 1: 로컬 LLM 인프라 (DGX)
  - DGX Spark 환경 셋업
  - 모델 측정 (Qwen3-8B Dense / Gemma 4 E4B)
  - 양자화 측정 (NVFP4 vs MXFP4 vs Q4_K_M)
  - core/llm/local_client.py 구현

Week 2: 웹 검색 + 플랜 생성
  - 검색 어댑터 (위키 + 일부 커뮤니티)
  - Interview Agent + Planning Agent
  - IP Leakage 검증기 (Layer 6+7)

Week 3: 통합 + 본격 도그푸딩
  - Layer 2 게임 루프 로컬 LLM 사용
  - AI Playtester 6 페르소나 작동
  - 본인 5회 + 친구 3-5명 플레이
```

---

## 7. 메타 회고

**성공 요인**:

1. **자료 우선** — 모든 결정은 docs/HARNESS_*.md / ROADMAP.md 참조
2. **본인 인사이트 즉시 반영** — 각 Day에 결정한 정책 후속 적용
3. **검증 가시성** — 콘솔 출력 + 통계 + Ship Gate 점수
4. **외부 패키지 0건 정책 유지** — CLI subprocess + 정액제 OAuth만
5. **Claude Code 능동성 활용** — 단순 작성자가 아닌 검증자

**배운 점**:

1. Tier 0의 목적은 "코드 작동" + "하네스 빌드"이지 "재미 검증"이 아님
2. `claude -p`의 14-33초는 구조적 한계 (subprocess overhead) — DGX Local LLM 필요
3. 워크플로 (Claude.ai 검증자 + Claude Code 실행자)는 두 Layer 시스템 패턴 그대로
4. 본인 인사이트가 종종 자료 패턴과 정합 — 직관 + 자료 양방향 검증

---

*Tier 0 종료. Tier 1 진입 결정 대기 (본인 + DGX Spark 가용성 확인 후).*
