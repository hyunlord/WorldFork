# Tier 1 Launch Guide (Preview)

> 작성: 2026-04-30 (Tier 0 종료 직후)
> 본격 시작: 본인 결정 + DGX Spark 셋업 후
> 상세: `docs/ROADMAP.md` 6장

---

## 0. Tier 0 → Tier 1 차이

| 항목 | Tier 0 | Tier 1 |
|---|---|---|
| LLM | claude/codex/gemini CLI (정액제 OAuth) | DGX Local LLM (Qwen3-8B / Gemma 4) |
| Latency | 14-33초/턴 | 1-3초/턴 (예상) |
| 시나리오 | 1개 (novice_dungeon_run) | 다수 (작품 자동 검색) |
| 도그푸딩 | 본인 1-2회 동작 확인 | 본인 5회 + 친구 3-5명 |
| Eval | 50케이스 인프라 | 50케이스 baseline 본격 측정 |
| AI Playtester | 3 페르소나 정의 | 6 페르소나 작동 |

---

## 1. Tier 1 진입 전 체크

### 환경 준비

- [ ] DGX Spark 사용 가능 (또는 동급 GPU)
- [ ] CUDA 12+ 셋업
- [ ] Python 3.11+ 환경
- [ ] 디스크 공간 100GB+ (모델 + 캐시)

### 모델 후보 (ROADMAP 11.4)

1. **Qwen3-8B Dense** (1순위) — 한국어 강점
2. **Gemma 4 E4B** — 비교 baseline
3. **HyperCLOVAX-1.5B** — 한국어 특화, fallback 후보

### 추론 서버 후보 (ROADMAP 6장)

1. **SGLang** — RadixAttention (worldview 공유 prefix 효과 측정)
2. **llama-cpp-python** — 가벼움, NVFP4 검증

---

## 2. Tier 1 우선순위 (ROADMAP 6장)

### Week 1: 로컬 LLM 인프라

```
1. DGX Spark 환경 셋업
2. 모델 다운로드 + 양자화 측정
   - NVFP4 vs MXFP4 vs Q4_K_M
   - 7B에서 41 TPS, 메모리 대역폭 273 GB/s 병목 검증
3. SGLang vs llama-cpp-python latency 비교
4. core/llm/local_client.py 구현
   - 기존 CLIClient와 동일 LLMClient ABC 인터페이스
5. API ↔ Local 동등성 검증
   - 같은 50 Eval 케이스 양쪽 실행, 점수 비교
6. Filter Pipeline 검증
   - GBNF 실패 시 post-hoc JSON 추출 (Day 5 이미 구현)
7. Fallback 체인 확인 (Local → Haiku → Sonnet)
```

### Week 2: 웹 검색 + 플랜 생성

```
1. 검색 어댑터 (위키 + 일부 커뮤니티, robots.txt 준수)
2. Interview Agent (모호 입력 시 3-5개 질문)
3. Planning Agent (Drafter)
4. Verify Plan Agent (Challenger, Cross-Model 강제)
5. IP Leakage 검증기 (Layer 6+7)
6. 플랜 표시 + 사용자 자연어 수정
```

### Week 3: 통합 + 본격 도그푸딩

```
1. Layer 2 game loop → 로컬 LLM 사용
2. AI Playtester 6 페르소나 작동
   - Tier 0 3개 + 추가: hardcore_lore_fan, speed_runner, roleplayer
3. 본인 5회 도그푸딩
4. 친구 3-5명 베타
5. 정성 피드백 수집 (Tier 1 졸업 조건)
```

---

## 3. Tier 0 자산 활용

이미 Tier 0에서 만든 것들이 Tier 1에 그대로 적용됨:

| 자산 | Tier 1 활용 방식 |
|---|---|
| `core/verify/` 전체 | Local LLM 응답에도 그대로 적용 |
| `core/eval/` 50케이스 | Local LLM 점수 baseline 측정 |
| `core/llm/cli_client.py` | 기존 CLI 호출 (verifier 역할 유지) |
| Cross-Model 매트릭스 | Local generator + CLI verifier |
| Ship Gate | Local LLM 추가 후에도 작동 |
| AI Playtester 3 페르소나 | 6개로 확장만 |

Tier 1에서 **새로 만들 것**: Local LLM Client + 웹 검색 + Plan 생성.
나머지는 Tier 0 자산 그대로 활용.

---

## 4. Tier 1 졸업 조건 (ROADMAP 6장)

- [ ] 100% 로컬 LLM 게임 진행 (API 0회)
- [ ] 응답 평균 latency 5초 이하
- [ ] 1시간 연속 플레이 안정 (메모리 누수 없음)
- [ ] 작품명 입력 → 플랜 생성 → 게임 시작 전체 흐름 작동
- [ ] IP leakage 90%+ 잡아냄
- [ ] Cross-Model 검증 작동 (강제)
- [ ] 본인 외 사용자 1명 이상 끝까지 플레이
- [ ] AI Playtester 6 페르소나 매일 1회 실행

---

## 5. Tier 1 시작 시 워크플로

```
1. 본인이 DGX Spark 사용 가능 상태 알림
2. Claude.ai에 "Tier 1 시작" 전달
3. CC_PROMPT_TIER_1_W1_DAY1.md 작성 (저)
4. Tier 0 워크플로 그대로 (저 검증 / Claude Code 실행 / 본인 결정)
```

**분량 예상**:

| 기간 | 사이클 수 |
|---|---|
| Week 1 (DGX 셋업 + Local LLM) | 5-7 사이클 |
| Week 2 (웹 검색 + 플랜) | 5-7 사이클 |
| Week 3 (통합 + 도그푸딩) | 5-7 사이클 |
| 합계 | 15-21 사이클 (Tier 0의 2-3배) |

---

## 6. 메모리 안전 정책 (Tier 0 학습)

Tier 0 Day 6에서 메모리 70GB 폭증 사고 발생. Tier 1 전 사이클 적용:

```
✅ pytest 호출은 작업당 1회 (병렬 spawn 금지)
✅ --cov 옵션은 최종 검증 1번만
✅ 각 작업 검증은 가벼운 python -c import 확인만
✅ subprocess가 pytest 부르는 패턴 금지 (재귀 위험)
✅ Local LLM 추론 서버 메모리 모니터링 (DGX 진입 후)
```

---

*Tier 1 본격 시작 = 본인이 DGX Spark 사용 가능할 때.*
*준비되면 알려주세요 — CC_PROMPT_TIER_1_W1_DAY1.md 바로 작성합니다.*
