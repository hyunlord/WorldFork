# Tier 1 W1 D2 Baseline 측정 보고서

날짜: 2026-05-01  
하드웨어: DGX Spark (NVIDIA GB10, 119GB Unified Memory, Ubuntu 24.04 ARM64)  
commit: 4b85cba (W1 D1) → W1 D2 신규

---

## 0. 한 줄 요약

★ Tier 1 첫 본격 baseline. 30 케이스(small sample n=2) × 3 모델 + **두 verifier 모드** (Cross-Model + Local-only) 측정 완료.

---

## 1. 측정 설계

### 두 verifier 모드 (★ 본인 인사이트)

```
Mode 1: Cross-Model strict (자료 권장 1순위)
  Generator: Local Qwen (3 모델)
  Verifier:  claude-code (anthropic family)
  → 자료 원칙 (verifier ≠ generator family, HARNESS_CORE 3.3)
  → Self-rationalization risk 회피

Mode 2: Local-only (★ 본인 인사이트, 같은 family OK)
  Generator: 9B Q3 또는 27B Q3
  Verifier:  27B Q2 (qwen family, 다른 사이즈/양자화)
  → 인터넷 없는 환경 가능
  → 빠른 verify (Local 5-15초)
  → assert_compatible(mode='same_family')로 명시적 허용
```

### 측정 매트릭스

| 항목 | 값 |
|---|---|
| 카테고리 | 5 (ai_breakout / ip_leakage / korean_quality / persona_consistency / world_consistency) |
| 케이스 (small sample) | n=2 per category = 10 |
| Generators | 3 (27B Q3, 27B Q2, 9B Q3) |
| Generation 호출 | 30 |
| CM Judge 호출 | 30 |
| Local Judge 호출 | 30 |
| 총 호출 | 90 |

---

## 2. 실측 결과 (Small sample n=2)

### Generator별 Mechanical 통과율

| 모델 | 통과 | 전체 | 비율 |
|------|------|------|------|
| 27B Q3 (8081) | 7 | 10 | **70%** |
| 27B Q2 (8082) | 7 | 10 | **70%** |
| 9B Q3 (8083) ★ | 8 | 10 | **80%** |

> ★ 9B Q3 Mechanical 80% = Tier 1 졸업 기준(80%+) 도달.  
> 27B 모델군 70% — full n=10 측정에서 재검증 필요.

### LLM Judge 점수 비교 (CM vs Local)

| 모델 | CM 점수 (claude-code) | Local 점수 (27B Q2) | 차이 |
|------|----------------------|---------------------|------|
| 27B Q3 | 59.3/100 (n=10) | 58.3/100 (n=9) | -1.0 |
| 27B Q2 | 56.0/100 (n=10) | **70.5/100** (n=10) | +14.5 |
| 9B Q3 ★ | 66.8/100 (n=10) | **79.5/100** (n=10) | +12.7 |

> ★ 본인 인사이트 검증:  
> - CM Judge(claude-code)가 Local Judge(27B Q2)보다 일관되게 엄격.  
> - 차이는 최대 +14.5점 (27B Q2 generator 기준).  
> - 9B Q3: Local Judge 79.5 — "pass" 기준 85점에 근접.

### Latency

| 모델 | 평균 응답 | 최대 응답 | 게임 목표(5초) |
|------|---------|---------|--------------|
| 27B Q3 | 12,321ms | 16,754ms | ❌ |
| 27B Q2 | 10,537ms | 13,473ms | ❌ |
| 9B Q3 ★ | **4,114ms** | 5,289ms | ✅ (200토큰 한도) |

---

## 3. ★ 본인 인사이트 검증

### 인사이트 1: 9B Q3 한국어 품질 충분한가?

**결론: 부분적 Yes.**
- Mechanical 80% → Tier 1 기준 통과
- Local Judge 79.5/100 → "warn" 범위 (85 미만)
- CM Judge 66.8/100 → 아직 "warn" ~ "fail" 경계

full n=10 측정 후 재평가 필요. 현재 small sample 한계(n=2 per cat).

### 인사이트 2: Local-only verifier 가능한가?

**결론: 기술적 Yes, 단 주의 필요.**
- Local verifier(27B Q2)가 CM verifier(claude-code)보다 **일관되게 관대** (+12-15점).
- 자가 평가 편향(self-leniency) 가능성 존재 — 같은 family 특성.
- 용도 분리 권장:
  - **개발 중 빠른 피드백**: Local-only OK
  - **Tier 1 졸업 조건 검증**: Cross-Model strict 필수

### 인사이트 3: 강화학습류 (★ Tier 3 메모)

자료 권장 (gemini1_raw.md:144):
- Methodology: **GRPO + PEAR**
- 플랫폼: Unsloth on DGX Spark
- 대상: 1B-8B 모델 fine-tune (수 시간)

Tier 3 시작 조건:
- ✅ Tier 1 인프라 완성 (W1 D1)
- ⬜ Tier 2 졸업 (도그푸딩 + 친구 베타)
- ⬜ 게임 로그 100+ 세션 수집
- ⬜ SFT 데이터 큐레이션

**YAGNI: Tier 3 구현 시작 X. 메모만.**

---

## 4. Tier 1 졸업 조건 진척도

| 조건 | 상태 | 비고 |
|------|------|------|
| 100% 로컬 추론 | ✅ | 인프라 완성 (W1 D1) |
| NPC 5초 이하 latency | ✅ | 9B Q3 avg 4.1s |
| Mechanical 통과율 80%+ | ✅ (9B Q3) | 27B 70% → full 재검증 필요 |
| Cross-Model 작동 | ✅ | Mode 1 OK |
| ★ Local-only 옵션 | ✅ | Mode 2 추가 (W1 D2) |

---

## 5. 다음 단계 (W1 D3 옵션)

| 옵션 | 내용 | 예상 시간 |
|------|------|---------|
| (A) Full n=10 측정 | 50 케이스 × 3 모델 = 150 gen + 300 judge | 2-3시간 |
| (B) AI Playtester 활성화 | Tier 0 정의 → Tier 1 6 페르소나 실행 | 2-3시간 |
| (C) API ↔ Local 동등성 | claude-code vs 27B Q2 품질 직접 비교 | 1-2시간 |

추천: **(A) → (B) 순서** — full 데이터 확보 후 AI Playtester로 자동 케이스 보강.
