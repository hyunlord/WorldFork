# Summary — 03 Technical Patterns

> Gemini 2 (architecture) + GPT 2 (산업 도구) 결과 정리
> 적용: ROADMAP 9.3, HARNESS_CORE 9.5, 11

## 핵심 결정 (ROADMAP에 반영됨)

### Memory Architecture (Tier 1+)
- Hierarchical: 요약 + 관계 + 로어북
- Short context (~16K) + 외부 메모리
- RLM (Recursive Language Models) Tier 3 검토

### Web Search APIs (Tier 1)
- Primary: **Brave Search API**
- Alternative: Tavily (LLM 친화)
- Korean: 나무위키 (gentle scraping), 디시/아카라이브 (커뮤니티)

### Generative Agents 패턴 (Tier 2+)
- Base: Stanford Generative Agents (2023)
- Improvements: OASIS (event-driven, no-tick)
- Korean: HuggingFace KREW + NVIDIA Nemotron

### Vector DB (Tier 1+)
- 권장: **pgvector** (이미 PostgreSQL 사용 시)
- 대안: **Qdrant** (멀티테넌시 강함)
- 회피: Pinecone Pro (비용 큼, 필요 시만)

### Inference Server (HARNESS_CORE 9.5)
- DGX Spark: **SGLang** ★
- 일반 데이터센터: vLLM
- 개발 환경: llama.cpp

## 핵심 발견

### 1. AutoGen 종료, Microsoft Agent Framework 승계 (★★★)

```
2026 시점:
  AutoGen: 공식 maintenance mode
  Microsoft Agent Framework 1.0: 2026-04 GA
  
WorldFork 영향:
  - 자체 구현이라 직접 영향 X
  - 기존 자료의 "AutoGen" 참조는 outdated
  - 신규 패턴 학습 시 MAF 검토
  
다른 프레임워크 상태:
  LlamaIndex: 활발 (2026-04까지 잦은 릴리스)
  Haystack: 활발 (deepset 생태계)
  CrewAI: 빠른 릴리스, 워크플로 중심
  DSPy: 프롬프트 자동 최적화
  TGI: 2025-12부터 maintenance mode
```

### 2. 게임용 RAG는 특수 (★★)

```
일반 RAG와 다른 점:
  - 짧은 질의
  - 한국어 + 영어 혼용
  - 자주 변하는 데이터 (라이브 이벤트)
  - 멀티테넌시 (게임별 / 지역별 / 세션별)
  
권고:
  pgvector: Postgres 이미 운영 중일 때 가장 경제적
  Qdrant: 단일 컬렉션 + 페이로드 파티셔닝 (게임별 / 세션별)
  Weaviate: 관리형 보안 + RBAC (Tier 3+)
  Pinecone: 이벤트성 트래픽 (serverless)
  
주의:
  - 임베딩 모델 + 벡터 DB 동시 잠그지 말 것
  - 재색인 비용 미리 계산
```

### 3. SGLang RadixAttention (★★★)

```
WorldFork와의 fit:
  - "공유 worldview prompt" = prefix 캐시 효과 큼
  - 게임 worldview / 캐릭터 정의 / 룰 = 모든 요청 공통
  - 매번 prefill 안 해도 됨 → TTFT 크게 개선

운영 패턴 (Cursor / xAI / LinkedIn 채택):
  OpenAI 호환 endpoint
  + prefix-aware caching
  + 분리된 prefill/decode
  + Prometheus 메트릭
```

### 4. 한국 LLM 백본 후보 (★★★)

```
규제 / 데이터 거버넌스 고려:
  Upstage Solar: API 백본
  CLOVA Studio (HyperCLOVA X): 한국어 강함, OpenAI 호환
  EXAONE: 라이선스 검토 필수 (상용 제약)
  
ON-PREM 단계:
  - 자체 self-host (Qwen3-8B Dense + NVFP4 + SGLang)
  - 한국어 fine-tune 검토
```

### 5. CLI Agents 비교 (★★)

```
Claude Code:
  Pro: 코드 품질, MCP 통합
  Con: 좌석비 ($150-250/월 enterprise)

Codex CLI:
  Pro: ChatGPT Plus 정액제
  Con: 일부 기능 제한

Gemini CLI:
  Pro: 무료 / 저가
  Con: 한국어 약간 약함

Aider:
  Pro: 가장 가벼움, 오픈소스
  Con: 자동화 약함

WorldFork AI Playtester 매핑:
  claude-code: 5-8 페르소나
  codex-cli: 5-7 페르소나
  gemini-cli: 3-4 페르소나
```

### 6. 비용 산정 모델 (★★)

```
프로토타입:
  Gemini CLI 무료 + Claude Code 일부
  pgvector + Upstage/CLOVA API
  → 월 수십~수백 달러

싱글 타이틀 파일럿:
  vLLM/SGLang 1-2 노드
  Qdrant / Pinecone 소형
  5-10 개발자 CLI 좌석
  → 월 수천~1만 달러

본격 상용:
  다중 GPU
  HA + 24/7 관제
  다국어 평가
  → 월 수만 달러+
```

## 학술 패턴 (Gemini 1, 2 학술 부분)

### Memory Architectures

```
관련 시스템:
  MemGPT: hierarchical memory
  HippoRAG: knowledge graph 기반
  Letta: stateful agents
  Mem0: 단순 / 빠름
  Zep: 게임에 적합
  AriGraph: storyworld 전용 (Neo4j 기반)

WorldFork 권장:
  Tier 1: 단순 hierarchical (자체 구현)
  Tier 2: Zep / Letta 패턴 차용
  Tier 3+: 자체 KG 또는 RLM
```

### Generative Agents 진화

```
Stanford (2023): 25 agents, Smallville
  ↓
OASIS (2024): 1M+ agents, event-driven
  ↓
2026 트렌드:
  - 분산 시뮬레이션
  - Persona collapse 회피
  - Korean 특화 (Nemotron)

WorldFork 적용:
  - 5-12 NPC (적은 수)
  - Event-driven (no-tick) 채택
  - 자료 검증된 패턴 + OASIS 영감
```

## 신뢰도

- ★★★ AutoGen 종료 / MAF 승계: 공식 발표
- ★★★ SGLang 채택 사례: xAI/LinkedIn/Cursor 공개
- ★★ 비용 추정: 가격 페이지 기반, 변동 가능
- ★★ Vector DB 비교: 공식 문서 + 사용자 후기
- ★ 일부 신생 도구 (Letta / Zep / Mem0): 빠른 변화

## 미해결 / 측정 권장

1. SGLang vs vLLM 한국 환경 실측
2. Qdrant 단일 컬렉션 vs 멀티 컬렉션 멀티테넌시 비교
3. Upstage / CLOVA API 한국어 자연스러움 직접 평가
4. EXAONE 라이선스 상용 활용 가능성 확인

## Raw 결과 참조

- `gemini2_raw.md`: WorldFork Architecture (315줄, 영문, 69개 인용)
  - Part I: 모델 / 하드웨어 (01_models_and_sft에서 더 사용)
  - Part II: 멀티 에이전트 (이 카테고리 핵심)
  - Part III: SFT (01_models_and_sft에서 사용)
- `gpt2_raw.md`: 프로덕션 AI 툴링 (152줄, 한국어, 30+ citation)

이 카테고리는 두 출처가 보완적 — Gemini는 이론/학술, GPT는 산업/도구.
