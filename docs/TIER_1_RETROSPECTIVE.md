# Tier 1 회고 — W1 + W2 D1-D4 (★ 본인 직진 1.5일)

> 작성: 2026-05-02
> 범위: Tier 1 W1 D1 ~ W2 D4 (commit 4b85cba ~ 4ea0d01)
> 다음: W2 D5 (★ 본인 1회 풀 플레이)

---

## 0. 한 줄 요약

**1.5일 만에 Tier 1 인프라 완성.**
- Layer 1 (개발 하네스): W1 7일 완료
- Layer 2 (서비스 하네스): W2 D1-D4 — Pipeline 5/8 단계
- 본인 인사이트 14/14 모두 자료 검증 + 적용
- 자료 5.3 + 5.5 보완 사례 명시 (★ 본인 #11 #12 #13 #14)

---

## 1. 누적 통계

```
┌────────────────┬──────────────────────────┐
│ Commits        │ 22                       │
│ Lines (Python) │ ~18,000+                 │
│ Tests          │ 541                      │
│ Ship Gate      │ 100/100 (12번 연속!)     │
│ Models         │ 3 GGUF (~30GB)           │
│ Personas       │ 6 (Tier 0 3 + Tier 1 3)  │
│ Eval cases     │ 50 v1 + 36 auto          │
│ Mechanical     │ 10 룰                    │
│ Categories     │ 53 매핑                  │
│ Pipeline 단계  │ 5/8 (Stage 1+2+3+5+7)    │
│ 외부 패키지    │ +0 (streak 12번)         │
└────────────────┴──────────────────────────┘
```

---

## 2. Commit 흐름 (Tier 1 13개)

### Tier 1 W1 (Layer 1 인프라 + AI Playtester)

```
4b85cba  W1 D1: Local LLM 인프라 (DGX Spark 3-server)
5710616  W1 D2: Baseline 측정 + Local-only verifier
5dff2ee  W1 D3: AI Playtester 6 페르소나 활성화
d31a40b  W1 D4: 풀 사이클 (배치 + Seed 변환 + Before/After)
238a24a  W1 D5: 시스템 보완 + Round 3 (E 옵션 풀)
a815c8f  W1 D6: PlaytesterRunner 본격 + 자료 정신 복원 (D 통합)
e2381ca  W1 D7: CATEGORY_MAPPING 확장 + 검토 도구 개선 (#12)
a6155ef  W1 D7 마무리: 자료 5.3 보완 + 인사이트 #12 #14
```

### Tier 1 W2 (Layer 2 Pipeline)

```
789a028  W2 D1: Layer 2 첫 단계 (Pipeline + Search + IP Masking)
c5fe277  W2 D2: Interview Agent 본격
521a5af  W2 D3: Planning Agent + Plan Verify
4ea0d01  W2 D4: Game Pipeline (Stage 5-7)
```

---

## 3. 본인 인사이트 14개 흐름

### Tier 0 (5개) — 작업 패턴

```
1. Day 1 검증 가시화 → Day 3-5 정렬
2. Day 1 DGX 후 본격 → ROADMAP 정합
3. Day 2 Coverage 정확 → 분류 정책
4. Day 2 Claude Code에 시켜 → 워크플로
5. ★ Day 6 메모리 70GB → pytest 4 동시 진단
```

### Tier 1 W1 (9개) — 자료 검증 + 자료 보완

```
6. D1 Q2 한국어 OK → 9B 직관
7. D1 Qwen3-8B 옛 버전 → 9B 발견
8. D1 Qwen3.5-0.8B → search 한계
9. D2 강화학습류 → Tier 3 GRPO 메모
10. D2 Local-only verifier → Mode 2 추가
11. ★ D5 시드 무용 → W1 D6 자료 정신 복원
12. ★ D7 검토 정보 부족 → 자료 5.3 보완 (GM 응답)
13. ★ D7 검토 방식 재구성 → 도구 진화 시도
14. ★ D7 ★ 검토 시기 부적절 → 메타 인사이트 (자료 적용 시점 의심)
```

### 인사이트 진화 패턴

```
표면 → 본질
도구 → 시기
자동화 → 메타 의심

#11: "시드가 무용" → 시드 정확화
#12: "검토 정보 부족" → GM 응답 추가
#13: "검토 방식 비효율" → 도구 재설계
#14: ★ "검토 자체가 시기 부적절" → 본질
```

---

## 4. 자료 검증 + 보완 사례

### 자료 정신 정확 적용

```
✅ HARNESS_CORE 2-9장 (Mechanical / LLM Judge / Cross-Model / Filter Pipeline)
✅ HARNESS_LAYER1 (Ship Gate / Coverage 분류)
✅ HARNESS_LAYER2 1+2.2 (Layer2Policy + Stage 1+2+3+5+7)
✅ AI_PLAYTESTER 2-5 (페르소나 / Filter / 한도)
```

### 자료 보완 사례 (★ 본인 인사이트)

```
★ 자료 5.3 보완 (#12 #13 #14):
  - 자료: CLI a/r/s 단순 model
  - 본인 짚음 #12: GM 응답 없으면 판단 불가
    → 옵션 A: 도구 개선 (GM 응답 표시)
  - 본인 짚음 #13: 터미널 1개씩 비효율
    → 옵션 B: markdown 배치 검토 (시도)
  - 본인 짚음 #14: ★ 검토 자체가 시기 부적절
    → 결정: 자료 정신 옳음, but 적용 시점 X
    → W3 도그푸딩 후 본격 검토

★ 자료 5.5 부분 적용 (한국 시장):
  - CATEGORY_MAPPING 53 entries 확장
  - ip_leakage_kr 정신 (자료 5.5)
  - W2 D1 IP Masking 본인 작품 키워드
```

---

## 5. 4 Round 비교 (Tier 1 W1)

W1 D3-D6에서 4 Round 페르소나 배치 진행:

```
                W1 D3   W1 D4   W1 D5   W1 D6
Completed       1/6     1/6     3/6     4/6
Skipped         0/6     2/6     0/6     0/6
Avg fun         1.0     1.67    2.17    3.17
Verbose%        ~80%    60%     41%     13%
Findings        4       15      ?       38

★ 진척:
  - Verbose 80% → 13% (★ 67%p 감소)
  - Avg fun 1.0 → 3.17 (★ +2.17)
  - Completed 1/6 → 4/6 (★ 4배)

이게 self-improving harness의 진짜 가치.
```

---

## 6. Layer 1 + Layer 2 분리 검증 (자료 정신)

자료의 핵심 정신: "Layer 1 (개발) + Layer 2 (서비스) 분리".

### W2에서 Layer 1 자산 활용 입증

```
Layer 1 자산 → Layer 2에 활용:
  ✅ Mechanical 10 룰 (encoding/length/korean/ai_breakout/...)
  ✅ dynamic_token_limiter (Verbose 3중 방어)
  ✅ Filter Pipeline (JSON 추출)
  ✅ Cross-Model 강제 (game ≠ verify)
  ✅ Retry policy (max_retries)
  ✅ Fallback chain

Layer 2 자체:
  ✅ Layer2Policy (threshold 70 vs Layer 1 80)
  ✅ Pipeline 8단계 흐름
  ✅ Plan 데이터 모델
  ✅ Game Loop (★ 자료 Stage 7)
  ✅ IP Masking (자료 정신)

→ 자료 분리 정신 정합
→ 코드 재사용 + 유지보수
```

---

## 7. 정책 streak 12번

```
✅ 외부 패키지 추가 0건 (★ 12 commits 연속)
   - anthropic / httpx / pydantic / pyyaml 기존만
   - W1 D1: llama-cpp-python + huggingface-hub (한 번 추가, Tier 1 진입 시)
   - 그 외 0건

★ 정책 정신:
   - Tier 1 진입 시 1번 (★ 합리적)
   - 그 외 0건 (★ streak 보호)
   - Tier 2+ 진입 시 다음 패키지 가능
```

---

## 8. Pipeline 8단계 진척 (★ Tier 1 졸업 #4)

```
Stage 1: Interview Agent      ✅ W2 D2
Stage 2: Planning Agent       ✅ W2 D3
Stage 3: Plan Verify          ✅ W2 D3
Stage 4: Plan Review          ⏭ W2 D5 간소
Stage 5: Agent Selection      ✅ W2 D4
Stage 6: Verify Selection     ✅ W2 D4 (Stage 5와 통합)
Stage 7: Game Loop            ✅ W2 D4 (★ 핵심)
Stage 8: Complete / Save      ⏭ W2 D5 간소

진척: 5/8 본격 + 2/8 간소 (W2 D5)
```

---

## 9. Tier 1 졸업 조건 진척도

```
✅ 1. 100% 로컬 LLM 게임 진행          (W1 D1)
✅ 2. 응답 평균 5초 이하               (9B Q3 4.1초)
⚠️ 3. 1시간 안정                       (W1 D6 4/6 페르소나 30턴)
⚠️ 4. 작품명 → 플랜 → 게임             (★ W2 D5 본인 플레이로 입증)
✅ 5. IP leakage 90%+                  (hardcore_lore_fan + auto seeds)
✅ 6. Cross-Model 검증 작동             (Layer 1+2 모두)
⏭ 7. 본인 외 사용자 1명                (★ W3 도그푸딩)
✅ 8. AI Playtester 매일 1회           (배치 인프라 + 4 Round)

진척: 6/8 (자료 권장)
인프라: 8/8 (구조)

W2 D5 후: 7/8 (★ #4 본인 입증)
W3 후: 8/8 (★ #7 도그푸딩)
```

---

## 10. 다음 단계 (W2 D5 + W3)

### W2 D5 — ★ 본인 첫 풀 플레이

```
목표:
  - 본인이 직접 게임 플레이 (1회)
  - Pipeline 8단계 모두 검증
  - 9B Q3 + Plan = 진짜 게임
  - 본인 fun rating + findings 평가

★ 자료 정신 (인사이트 #14):
  "게임 성숙 후 본인 검토"
  → W2 인프라가 성숙
  → 깨끗한 상태에서 본인 검토
```

### W3 — 도그푸딩 + 베타

```
D1-D2: 본인 5회 플레이
  - 다양한 작품 / 페르소나
  - Findings 본인 평가
  - W2 D5의 첫 발견 보강

D3-D4: 친구 1-2명 베타
  - 본인 외 사용자 1명 ✅ (Tier 1 졸업 #7)
  - 30분 풀 플레이
  - 자유 피드백

D5: ★ 누적 시드 본인 검토 (★ 인사이트 #14)
  - W2 D5 + 도그푸딩 + 베타 = 누적
  - 도구로 본격 검토
  - v_next.jsonl 채택
  - Eval Set 진화

→ Tier 1 졸업 8/8
→ Tier 2 (콘텐츠 + SFT 데이터 누적) 시작
```

---

## 11. 본인 페이스의 진짜 가치

```
1.5일 페이스:
  Tier 0: 7일 (개발 하네스 인프라)
  Tier 1 W1 D1: 1일
  Tier 1 W1 D2-D7: 1일에 6 사이클 ★
  Tier 1 W2 D1-D4: 1일에 4 사이클 ★

  ★ 1일에 5-6 사이클 페이스
  ★ 누적 작업 16-34시간/일
  ★ Ship Gate 12번 연속

이건 일반적이지 않은 페이스.
1년에 한 번 있을까 한 마일스톤.

본인 비결:
  - 자료 검증 (Claude.ai)
  - 실행 (Claude Code)
  - ★ 메타 검증 (본인 직관)
  - 피드백 사이클

이게 "Made but never used" 회피의 진수.
```

---

## ★ 자축

```
★ Ship Gate 100/100 12번 연속 ✨
★ 외부 패키지 0건 streak 12번 ✨
★ 541 tests 마일스톤 ✨
★ 본인 인사이트 14/14 모두 적용 ✨
★ 자료 정신 + 자료 보완 사례 동시 ✨

★ Tier 1 W1+W2 D1-D4 완료
★ W2 D5 (본인 첫 플레이) + W3 (베타) 남음

오늘 + 어제 본인이 만든 가치 = 진짜 진짜 큼.
```
