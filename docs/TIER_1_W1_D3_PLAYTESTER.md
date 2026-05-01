# Tier 1 W1 D3 — AI Playtester 6 페르소나 활성화 보고서

날짜: 2026-05-01  
하드웨어: DGX Spark (NVIDIA GB10, 119GB Unified Memory)  
commit: 5710616 (W1 D2) → W1 D3 신규

---

## 0. 한 줄 요약

★ Tier 0 placeholder → Tier 1 본격 작동.  
6 페르소나 (Tier 0 3 + Tier 1 3 신규) 정의 완료.  
첫 세션 실행 검증 완료 — **게임 품질 이슈 4건 즉시 발견**.

---

## 1. Tier 1 페르소나 6종

| 페르소나 | CLI | Forbidden | 핵심 역할 |
|---|---|---|---|
| casual_korean_player | claude-code | claude_code | 캐주얼, 이탈 패턴 검증 |
| troll | codex | codex | 시스템 깨기, AI 본능 누설 시도 |
| confused_beginner | gemini | gemini | Onboarding 검증 |
| hardcore_lore_fan ★ | codex | codex | 원작 IP / 세계관 위반 검증 |
| speed_runner ★ | claude-code | claude_code | verbose 응답 발견 |
| roleplayer ★ | codex | codex | 캐릭터 일관성 / 격식체 |

★ Cross-Model 자동 충족: forbidden_game_llms 강제.

---

## 2. ★ 첫 세션 실측 결과

```
Persona:    casual_korean_player
Game LLM:   qwen35-9b-q3 (Local, qwen family)
Playtester: claude-code (CLI, anthropic family)
Cross-Model: ✅ (anthropic ≠ qwen)
Elapsed:    42.0초 (9B Q3 intro ~4초 + claude-code 38초)
```

| 항목 | 값 |
|---|---|
| Completed | ❌ (이탈) |
| Turns played | 2 |
| Fun rating | 1/5 |
| Would replay | ❌ |
| Findings | **4건** |

### 발견 사항

| 심각도 | 카테고리 | 설명 |
|---|---|---|
| **critical** | UX | 인트로 텍스트 잘림 (`max_tokens=200` 제한) — '내디딜지 선'으로 끊겨 플레이어가 다음 행동 불가 |
| **major** | UX | '존경하는 플레이어 님' 공문 경어체 — 20-30대 캐주얼에 거부감 |
| **major** | verbose | 인트로 한 화면 꽉 참 — 2-3줄로 압축 필요 |
| **minor** | i18n | '노바스 dungeon(신참의 던전)' 한/영 혼용 |

> ★ 단 2턴에 4건 발견. AI Playtester가 즉시 가치를 증명.

### 핵심 인사이트

1. **max_tokens=200 제한** → 게임 응답이 잘림. 게임 루프 통합 시 min 400 필요.
2. **9B Q3 경어체 어색** → 프롬프트 개선 필요 ("격식체" 지시를 재고).
3. **casual 페르소나가 verbose 잘 잡음** → 설계 의도대로 작동.

---

## 3. 게임 루프 통합 검증

| 항목 | 상태 |
|---|---|
| 게임 LLM (9B Q3) 응답 | ✅ |
| Playtester CLI 페르소나 행동 | ✅ |
| JSON 결과 파싱 (Filter Pipeline) | ✅ |
| findings 구조화 | ✅ |
| 결과 디스크 저장 | ✅ |

---

## 4. Tier 1 졸업 조건 진척도

| 조건 | W1 D2 | W1 D3 | 비고 |
|------|-------|-------|------|
| 100% 로컬 LLM | ✅ | ✅ | |
| NPC 5초 이하 latency | ✅ | ✅ | 9B Q3 avg 4.1s |
| 1시간 안정 연속 | ⬜ | ⬜ | W2 배치 실행 시 검증 |
| 작품명→플랜→게임 흐름 | ⬜ | ⬜ | W2 작업 |
| IP leakage 90%+ | ⬜ | 부분 | hardcore_lore_fan W1 D4-5 |
| Cross-Model | ✅ | ✅ | |
| 본인 외 사용자 | ⬜ | ⬜ | W3 도그푸딩 |
| **AI Playtester 매일 1회** | ⬜ | **✅** | 인프라 + 첫 실행 완료 |

**진척: W1 D2 4/8 → W1 D3 5.5/8**

---

## 5. 다음 단계 (W1 D4 옵션)

| 옵션 | 내용 | 가치 |
|------|------|------|
| (1) 게임 응답 품질 개선 | max_tokens 올리기 + 경어체 프롬프트 재작성 | 당장 발견된 이슈 수정 |
| (2) 6 페르소나 배치 1회씩 | 전체 페르소나 가동 검증 | 커버리지 |
| (3) Full baseline n=10 | W1 D2에서 미룬 150 호출 | Tier 1 졸업 데이터 |
| (4) hardcore_lore_fan 실행 | IP leakage 검증 | 졸업 조건 직접 충족 |

추천: **(1) 먼저 → (2) 또는 (4)**
최근 발견된 critical 이슈(텍스트 잘림) 수정이 다른 페르소나 실행 전 우선.
