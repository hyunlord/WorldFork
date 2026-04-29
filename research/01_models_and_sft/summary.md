# Summary — 01 Models and SFT

> Gemini 1, 2 결과 정리 (영문 raw → 한국어 핵심)
> 적용: ROADMAP 9.1, HARNESS_CORE 9.5, 11

## 핵심 결정 (ROADMAP에 반영됨)

### Tier 0 모델
- **Claude Haiku 3.5** (primary)
- **GPT-4o-mini** (cross-model verifier)
- 비용 추정: 한 세션 30턴 ~$0.10
- Korean 자연스러움 검증됨

### Tier 1 모델 (DGX Local)
- **Qwen3-8B Dense** (primary)
- **Gemma 4 E4B** (alternative, Apache 2.0)
- 양자화: **NVFP4** (DGX Spark 메모리 병목 해결)
- 추론 서버: **SGLang** (RadixAttention prefix 캐시)

### Tier 3 SFT
- 베이스: Qwen3-8B Dense 또는 Gemma 4 E4B
- 프레임워크: **Unsloth** (단일 노드, GRPO 통합)
- 회피: **DPO** (optimization collapse)
- 검토: **PEAR** (SFT-then-RL 가교)

## 핵심 발견

### 1. Dense > MoE for 페르소나 (★★★ 강한 합의)

```
MoE 문제: Expert fragmentation
  - Long-horizon에서 다른 expert 활성화
  - 새 expert가 이전 페르소나 contradicting
  - 페르소나 drift, 일관성 약함

Dense 우월:
  - 모든 파라미터 매 step 활성
  - 균일한 표현
  - 페르소나 coherence floor 높음
```

**근거**:
- Persona Selection Model (Anthropic alignment, 2026)
- "The Chameleon's Limit" (arxiv 2604.24698)
- Identity Drift 학술 문헌

**WorldSim 검증과 일치**: 0.8B SFT 85% vs 9B SFT 54%

### 2. DGX Spark 메모리 대역폭이 진짜 병목 (★★★)

```
하드웨어:
  - GB10 Grace-Blackwell
  - 128GB unified memory
  - 273 GB/s 메모리 대역폭 ← 병목
  - ~1 PFLOP FP4

성능 (Batch=1):
  - Qwen 7B + NVFP4 = 41 TPS
  - Llama 8B + NVFP4 = 38 TPS
  - GPT-OSS 20B + MXFP4 = 82 TPS (★ 작은 양자화로 더 빠름)
  - Llama 70B + FP8 = 2.7 TPS (사실상 비실용)
  - GPT-OSS 120B + MXFP4 = 55 TPS

동시 세션 (5초 latency 유지):
  - 7-14B: 12-15 sessions
  - 32B: 5-8 sessions
  - 70B: 2-4 sessions
```

**결론**: 70B는 메모리 충분해도 실질 처리량 부족. 7-14B 권장.

### 3. SGLang 우월 (DGX Spark 한정)

```
SGLang vs vLLM vs llama.cpp:

SGLang:
  ✅ RadixAttention (prefix 자동 캐시)
  ✅ "공유 worldview prompt" 패턴에 최적
  ✅ 분리된 prefill/decode

vLLM:
  ❌ DGX Spark에서 메모리 over-allocation
  ❌ NVFP4 sm121 커널 약함
  ⚠️ 데이터센터 GPU에는 좋음

llama.cpp:
  ✅ 단일 stream 효율
  ✅ 모델 swap 빠름
  ❌ 연속 배칭 약함
```

**결정**: Tier 1에서 측정 후 SGLang 채택 가능성 높음.

### 4. SFT 베스트 프랙티스 (2026)

```
프레임워크:
  - Unsloth: 단일 노드 최적, VRAM 70% 절감, 2-5x 속도
  - Axolotl: 멀티 GPU 분산
  - LLaMA-Factory, TorchTune: 보조

알고리즘:
  - SFT first (필수)
  - GRPO (critic-free, memory 효율)
  - DPO 회피 (optimization collapse)
  - PEAR 검토 (SFT-then-RL 가교)

합성 데이터:
  - Teacher: Claude Opus 4.7, GPT-5.5 Pro
  - 형식: ChatML / ShareGPT
  - 5000-10000 샘플
  - 사람 검증 20-30% 폐기 예상

한국어 SFT:
  - HuggingFace KREW Korean role-playing dataset
  - NVIDIA Nemotron Korean Personas (2026-04)
  - Chat template 함정 주의 (Gemma 3 → 4 해결됨)
```

### 5. Long Context vs RAG vs Hybrid

```
Long context (128K+):
  ❌ "Lost in the middle" 여전히 존재
  ❌ 64K+ 에서 attention dilution 심각
  ⚠️ 비용도 큼

RAG:
  ⚠️ 단순 RAG는 narrative consistency 약함
  ✅ 작품 검색에는 적합 (Tier 1)

Hybrid (권장):
  ✅ Short context (~16K) + 외부 메모리
  ✅ Hierarchical (요약 + 관계 + 로어북)
  ✅ Recursive Language Models (RLM) 검토 가치 (2026 트렌드)
```

## 신뢰도

- ★★★ Dense > MoE: 학술 근거 풍부
- ★★★ DGX Spark 병목: 다수 출처 일치
- ★★ SGLang 우월: 측정 권장
- ★★ NVFP4 효과: 실측 필요
- ★★ Unsloth + GRPO: 검증된 패턴

## 미해결 / 측정 권장

1. SGLang vs llama.cpp 실측 (Tier 1 Week 1)
2. Qwen3-8B vs Gemma 4 E4B 한국어 자연스러움 직접 비교
3. NVFP4 vs MXFP4 vs Q4_K_M 어느 게 best
4. GRPO 적용 시점 (SFT 직후 vs 나중)

## Raw 결과 참조

- `gemini1_raw.md`: Strategic Analysis (244줄, 영문, 79개 인용)
- `gemini2_raw.md`: WorldFork Architecture (315줄, 영문, 69개 인용)

총 인용 ~140개. 핵심 5-10개는 본인이 직접 확인 권장.
