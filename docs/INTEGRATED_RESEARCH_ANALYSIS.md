# WorldFork 딥리서치 통합 분석 (Phase B 결과)

> 6개 딥리서치 결과 통합 → ROADMAP / HARNESS v0.2 업데이트 계획
>
> 작성: 2026-04-29
> 입력 자료:
> - Claude 1: WorldFork_EvalRunner (Eval 도구 분석, 694줄)
> - Claude 2: WorldFork_HARNESS Eval 도구 (456줄)
> - Gemini 1: Strategic Analysis (모델/SFT, 244줄)
> - Gemini 2: WorldFork Architecture (315줄)
> - GPT 1: 한국 시장 경쟁 분석 (200줄)
> - GPT 2: 프로덕션 AI 툴링 지형도 (152줄)

---

## 0. Executive Summary

6개 결과를 통합한 결과, 다음과 같은 큰 그림이 그려졌어요:

**기존 ROADMAP/HARNESS의 핵심 가설들은 대체로 검증됨**:
- Cross-Model verification → 학술적으로 정당화 (Wataoka et al. 2024, self-preference bias)
- 작은 모델 + SFT가 페르소나 일관성 강함 → 학술 근거 확인 (Persona Selection Model, Identity Drift)
- Mechanical 우선 + LLM-Judge 패턴 → 4개 외부 도구 모두 채택
- Eval Set 버전 관리 → lm-evaluation-harness가 검증된 패턴

**하지만 일부 결정은 재검토 필요**:
- ⚠️ **Ship gate 95+가 너무 엄격할 수 있음** (judge LLM은 0.7-0.9에 답 몰림)
- ⚠️ **Information isolation은 외부 도구 어디도 안 함** — score 격리가 실제 효과 있는지 ablation 필요
- ⚠️ **GBNF 강제는 lock-in 위험** (Claude/GPT-4o는 grammar 미지원)
- ⚠️ **Cross-Model verification 비용 2배** — judge에는 cheaper model 권장 패턴

**큰 발견** (예상 못 한 것들):
- ⭐ **DGX Spark는 메모리 대역폭이 병목** (273 GB/s) → 70B 모델은 비현실적, 8-20B 권장
- ⭐ **NVFP4 / MXFP4 양자화가 결정적** — 이거 없으면 latency 목표 못 맞춤
- ⭐ **SGLang이 DGX Spark에서 우월** (vLLM/llama.cpp보다) — RadixAttention으로 prefix 캐시
- ⭐ **MoE는 페르소나에 약함** (Expert fragmentation 현상) — Dense 권장
- ⭐ **한국 시장은 이미 살아있음** — Crack 7000만 달러 ARR, 제타 MAU 402만, 일본 확장 검증됨
- ⭐ **저작권/미성년자 리스크는 진입 조건** — 미루면 안 됨
- ⭐ **promptfoo가 OpenAI에 인수됨** (2026-03) — 의존성 추가 시 주의
- ⭐ **AutoGen은 maintenance mode**, Microsoft Agent Framework로 승계됨

---

## 1. Cross-Cutting Findings (3+ 결과 공통)

### 1.1 Dense > MoE for 페르소나 (★★★ 강한 일치)

**출처**: Gemini 1, Gemini 2, Claude 1
- Gemini 1: "MoE 모델은 expert fragmentation 현상 — 토큰이 다른 expert로 라우팅되며 페르소나 contradicting"
- Gemini 2: "Dense 8B-20B는 페르소나 일관성 우월, MoE는 long-horizon에 약함"
- Claude 2 (검증): "이 발견은 WorldSim의 결과와도 일치"

**근거 논문**:
- Persona Selection Model (Anthropic alignment, 2026)
- "The Chameleon's Limit: Persona Collapse and Homogenization" (2604.24698)
- "Identity Drift" 학술 문헌

**WorldFork 영향**: 
- Tier 1 모델 선택 = **Qwen3-8B Dense** 또는 **Gemma 4 E4B** (MoE 회피)
- ROADMAP 9.1 답함

### 1.2 SGLang이 DGX Spark에 최적 (★★★ 강한 일치)

**출처**: Gemini 1, Gemini 2, GPT 2
- 모두 동일 결론: vLLM은 DGX Spark에서 메모리 over-allocation 문제, llama.cpp는 prefill 약함
- SGLang의 RadixAttention = WorldFork의 "공유 worldview prompt" 패턴에 정확히 맞음
- "shared prefix가 매번 prefill 안 해도 됨" → time-to-first-token 크게 개선

**WorldFork 영향**:
- Tier 1 시작 시 **llama.cpp가 아닌 SGLang** 검토 (HARNESS_LAYER2의 fallback chain 변경)
- 단, 자료의 검증된 llama.cpp 경험과 충돌 → 측정 후 결정

### 1.3 NVFP4 / MXFP4 양자화가 결정적 (★★ 일치)

**출처**: Gemini 1, Gemini 2
- DGX Spark 273 GB/s 메모리 대역폭이 병목
- NVFP4: 7B에서 41 TPS, 8B에서 38 TPS
- MXFP4: 20B GPT-OSS에서 82 TPS (★ 오히려 빠름, 메모리 압축 효과)
- Q4_K_M (기존 자료) 대신 NVFP4 / MXFP4 검토

**WorldFork 영향**:
- HARNESS_CORE의 cross_model.yaml에서 quantization 명시 변경
- 측정 가치 큼

### 1.4 GRPO > DPO/PPO (★★ 일치)

**출처**: Gemini 1, Gemini 2
- DPO는 "optimization collapse" 문제
- PPO는 critic memory 2배
- GRPO는 critic 제거, group relative advantage
- Unsloth가 GRPO 단일 노드 최적

**WorldFork 영향**:
- ROADMAP 9.1 SFT 결정: DPO 회피, GRPO 검토 (Tier 3 SFT 시)
- 단, 자료의 "DPO 실패 경험" 그대로 유효 → 검증된 패턴

### 1.5 Information Isolation은 외부에 없음 (★★★ 강한 합의)

**출처**: Claude 1, Claude 2 모두
- 4개 도구 (promptfoo, deepeval, ragas, lm-eval) 어느 것도 retry feedback에서 score 격리 안 함
- **이론적**으로는 prompt-leak 방지에 좋음
- **실증적**으로는 ablation 부재 — score가 가장 강한 학습 신호인데 빼면 손실
- Claude 2 권장: "절충안 — score는 주되 어떤 메트릭의 score인지 안 알려주는 방식"

**WorldFork 영향**:
- ⚠️ 핵심 결정 재검토 필요
- Tier 0에서 ablation 실험 권장: score 포함 retry vs issues-only retry
- HARNESS_CORE 8.2 (Information Isolation) 보강 또는 절충

### 1.6 Eval 도구 4개 패턴 차용 (★★★ Claude 1, 2 일치)

**STEAL_PATTERN으로 결정된 4가지**:

| 도구 | 차용 패턴 |
|---|---|
| **promptfoo** | weight × threshold × metric_tag 3-속성 모델 + redteam plugin × strategy 직교 분리 + defaultTest 글로벌 negative-rubric + position-swap |
| **deepeval** | BaseMetric ABC + G-Eval evaluation_steps 자동 생성 + DAG decision-tree |
| **ragas** | PydanticPrompt schema 강제 + claim-decomposition Faithfulness |
| **lm-evaluation-harness** | Filter pipeline + metadata.version + Task versioning |

**채택 안 함**: 4개 도구 자체 의존성 (외부 패키지 0건 정책 유지)

---

## 2. 충돌 / 모순 (출처별 다른 견해)

### 2.1 Ship Gate Threshold 95+ vs 70+ vs ablation 필요

**Claude 2의 비판**: "judge LLM은 0.7-0.9 구간에 답 몰림 — 95+는 노이즈일 수 있음"
**기존 ROADMAP**: 95+ 강제 (Layer 1)
**해석**: Claude 2 분석이 정당. 단 binary metric (DAG 등) 다수 + threshold 사실상 0으로 재설계 검토

**결정 권장**:
- Ship gate 95+ 유지하되 binary mechanical 우선 + LLM judge weight 낮춤
- 또는 95+ → 90+로 완화 (실제 데이터로 결정)
- Tier 0에서 baseline 측정 후 결정

### 2.2 GBNF 강제 vs 호환성

**Gemini 2 / 자료**: GBNF가 한국어 JSON 안정성에 핵심
**Claude 2의 비판**: "Claude/GPT-4o는 grammar 미지원 → generator 후보 좁아짐"

**해석**: 
- Layer 2 (서비스, 로컬 LLM) = GBNF 유지
- Layer 1 (개발 검증, API 모델) = post-hoc JSON validation으로 완화
- 자료의 "함정 19" 경고와도 일치 (post-hoc 검증 필수)

### 2.3 Eval Tool 채택 여부

**ROADMAP 9.4**: "외부 패키지 0건" 정책
**Claude 1, 2 권장**: 4개 도구 의존성 추가 안 함 + 패턴만 차용 ✅
**Claude 2 추가 권장**: lm-evaluation-harness만 별도 — KoBEST/KMMLU/HAERAE로 모델 1차 필터링 (외부 단발 사용)

**결정**: Claude 권장 그대로 채택 가능. lm-eval은 "선택적 RUN_ONCE 외부 도구"로.

### 2.4 한국 시장 차별화 — 동반자 vs 서사

**GPT 1**: "한국은 서사형(story-first) > 동반자형(companion-first)"
- 규제 회피 (미성년자 보호), IP 협업 가능, 팬덤/UGC 친화
- Crack/Zeta 모두 서사형 성공
- WorldFork 컨셉이 정확히 서사형 → 정합

**WorldFork 영향**:
- ROADMAP 차별화 표 강화 (서사형 포지셔닝 명문화)
- AI Playtester 페르소나에 한국 10대-20대 더 강조

---

## 3. 새로 풀린 결정들 (Open → Closed)

### 3.1 ROADMAP 9.1 (모델 선택) — ✅ 풀림

**결정**:

```yaml
Tier 0 (API):
  primary: claude-haiku-3.5         # 빠르고 저렴
  cross_model_verifier: gpt-4o-mini  # 다른 family
  reasoning: "한국어 좋음, 비용 낮음, GBNF 무관 (post-hoc validation)"

Tier 1 (DGX Local):
  primary: Qwen3-8B Dense           # 페르소나 강함, MoE 회피
  alternative: Gemma 4 E4B          # 라이선스 Apache 2.0
  quantization: NVFP4 또는 MXFP4    # DGX Spark 메모리 병목 해결
  inference_server: SGLang          # llama.cpp보다 prefix 캐시 유리
  fallback: Claude Haiku (API)
  reasoning: |
    - Dense > MoE (페르소나 fragmentation 회피)
    - 7-14B = 12-15 동시 세션 가능 (5초 latency 목표)
    - 32B+ = 동시성 5-8명으로 줄어듦, 비실용적
    
Tier 3 SFT (선택):
  base_model: Qwen3-8B Dense 또는 Gemma 4 E4B
  framework: Unsloth (단일 노드, GRPO 통합)
  technique: SFT first, GRPO 검토
  data_size: 5000 합성 (Claude Opus 4.7 또는 GPT-5.5 Pro teacher)
  caveat: |
    - DPO 회피 (자료 + Gemini 검증)
    - PEAR 기법 검토 (SFT-then-RL 가교)
    - Korean role-playing dataset (HuggingFace KREW) 활용 가능
```

### 3.2 ROADMAP 9.4 (Eval 도구) — ✅ 풀림

**결정**: 외부 의존성 0 정책 유지 + 4개 도구 패턴 차용

```python
# 자체 EvalRunner 핵심 클래스 (Claude 1, 2 합의)

class BaseMetric(ABC):
    """deepeval BaseMetric 패턴"""
    threshold: float
    
    @abstractmethod
    def measure(self, response: str, context: dict) -> MetricResult: ...
    
    @abstractmethod
    async def a_measure(self, response: str, context: dict) -> MetricResult: ...
    
    def is_successful(self) -> bool: ...

@dataclass
class Assertion:
    """promptfoo weight × threshold × metric_tag 3-속성"""
    type: Literal["mechanical", "llm_rubric", "g_eval", "py_fn"]
    weight: float = 1.0
    threshold: float = 0.5
    metric: Optional[str] = None    # 카테고리 태그

class FilterPipeline:
    """lm-eval Filter pipeline 패턴
    GBNF 실패 시 post-hoc JSON 추출 fallback"""
    filters: list[Filter]
    def apply(self, raw_output: str) -> dict: ...

class JudgePrompt:
    """ragas PydanticPrompt 패턴
    judge 출력 schema 강제"""
    input_schema: BaseModel
    output_schema: BaseModel
    
class EvalSpec:
    """lm-eval metadata.version 패턴"""
    version: str = "0.1.0"          # 변경 시 +1
    items: list[EvalItem]
```

### 3.3 ROADMAP 9.2 (경쟁 차별화) — ✅ 풀림

**핵심 인사이트** (GPT 1):

```
한국 시장 = 살아있음:
  - 제타 MAU 402만, 월 사용시간 5,248만 시간 (2026-02)
  - Crack ARR 7000만 달러 (2025년 말)
  - 87%가 10-20대
  - 일본 확장 검증됨 (MiraiMind 200만 다운로드)

WorldFork 차별화 포인트:
  ✅ 서사형 (story-first) — 동반자형보다 규제 + IP 친화
  ✅ Plan review/edit workflow — 다른 서비스에 없음
  ✅ 4축 다양성 (entry/mode/genre/freedom) — 명확한 차별화
  ✅ Hybrid game mechanics — 채팅에 없음
  ✅ 한국어 장르 프리셋 — 로컬 우월

위험:
  ❌ 미성년자 보호 (Character.AI 소송 사례)
  ❌ IP/실존 인물 (디즈니 경고장)
  ❌ 개인정보 (이루다 판결 — 손해배상)
  ❌ 메모리 비용 폭증 (장기 RP 핵심)
  ❌ 커뮤니티 부정적 회전
```

**가격 전략**:
- 무료 진입 + 웹 구독 + 코인/에피소드 + creator economy
- 웹: 8,900~12,900원 / 앱: 11,900~15,900원
- 앱스토어 수수료 회피 (웹 결제 우선)

### 3.4 ROADMAP 9.3 (기술 패턴) — ✅ 풀림

**Tier 1+ 추가 결정**:

```yaml
Memory architecture (long session):
  approach: hierarchical
  short_term: 컨텍스트 윈도우 (~16K)
  long_term: Knowledge Graph (Zep / Letta 패턴 차용)
  reasoning: |
    - Lost-in-the-middle 여전히 존재 (논문 검증)
    - RAG 단독은 narrative consistency 약함
    - Recursive Language Model (RLM, 2026 트렌드) 검토 가치
    - Hybrid (short context + structured memory) 권장

Generative agents pattern:
  base: Stanford Generative Agents (Park et al. 2023)
  improvements: 
    - OASIS (event-driven, no-tick simulation)
    - "Persona Collapse" 회피 (homogenization 방지)
  korean_specific:
    - HuggingFace KREW Korean role-playing dataset
    - NVIDIA Nemotron Korean Personas (honorific-aware, 2026-04)

Web search (Tier 1 검색 파이프라인):
  primary: Brave Search API (privacy 친화)
  alternative: Tavily (LLM 친화 결과)
  korean_sources:
    - 나무위키 (gentle scraping, robots.txt 준수)
    - 디시인사이드 (커뮤니티 신호, 약함)
  caveat: "Reddit/Discord 직접 스크래핑 금지 (ToS)"
```

---

## 4. 새로 등장한 우려 사항

### 4.1 promptfoo OpenAI 인수 (★★ 주의)

**출처**: Claude 2
- 2026-03 OpenAI 인수
- default 모델이 OpenAI 계열로 묶일 가능성
- Cross-Model 강제 (generator ≠ judge) 우회 위험

**대응**: 패턴만 차용, 의존성 추가 X 유지. 더 의심해서 검토.

### 4.2 AutoGen 종료, Microsoft Agent Framework 승계

**출처**: GPT 2
- AutoGen 공식 maintenance mode (2026)
- Microsoft Agent Framework 1.0 GA (2026-04)
- ROADMAP에서 AutoGen 언급 시 업데이트 필요

**WorldFork 영향**: 우리는 자체 구현이라 직접 영향 없음. 단 패턴 학습 시 MAF 검토.

### 4.3 한국 규제 강화 (2026)

**출처**: GPT 1
- 한국 AI 기본법 투명성 가이드라인 시행 (2026)
- 미성년자 보호 강화 (Character.AI 사례 영향)
- 이루다 판결 (개인정보 손해배상 확정)

**WorldFork 영향**:
- ROADMAP 10.1 저작권 리스크 → 10.1 + 10.2 (개인정보 + 미성년자 + IP) 분리 필요
- Tier 3 출시 전 법적 검토 필수
- 청소년/성인 이원화 설계 from Tier 0

### 4.4 메모리 비용이 사용자 차별화 핵심

**출처**: GPT 1 (한국 시장 분석)
- c.ai+, AI Dungeon, Kindroid, NovelAI 모두 메모리 차별화로 유료화
- "더 나은 기억"이 가장 강한 결제 동기

**WorldFork 영향**:
- HARNESS_LAYER2의 메모리/컨텍스트 설계 가치 큼
- 단순 long context보다 hierarchical memory가 더 가치 있음
- ROADMAP에 명시적 차별화 포인트로 추가

### 4.5 KV Cache 메모리가 진짜 병목

**출처**: Gemini 2
- 동시 세션 N개 = KV cache N배 누적
- DGX Spark 128GB 중 모델 + KV cache + 기타 시스템
- 7B 모델 = 12-15 동시 세션 한계 (5초 latency 기준)

**WorldFork 영향**:
- HARNESS_LAYER2의 cost_per_request에 KV cache 고려 추가
- 동시 사용자 한도 명시적 설정 필요

---

## 5. ROADMAP / HARNESS v0.2 업데이트 계획

### 5.1 ROADMAP.md 업데이트 항목

```markdown
## 9.1 모델 선택 / SFT 전략 — ✅ 결정됨

(섹션 위 통합 분석 3.1 내용 그대로 반영)

추가:
- "DGX Spark는 메모리 대역폭 병목 (273 GB/s)" 명시
- "NVFP4/MXFP4 양자화 필수" 명시  
- "MoE 회피 (Expert fragmentation)" 명시
- "SGLang 검토 (llama.cpp 대신)" 추가

## 9.2 경쟁 차별화 — ✅ 보강됨

차별화 표에 다음 추가:
| 차원 | WorldFork | Crack | 제타 | character.ai |
|---|---|---|---|---|
| 포지셔닝 | 서사 | 서사 | 서사 | 동반자 |
| Plan review/edit | ✅ | ❌ | ❌ | ❌ |
| 4축 다양성 | ✅ | ❌ | ❌ | 한정 |
| Hybrid game | ✅ | ❌ | ❌ | ❌ |
| 한국어 장르 프리셋 | ✅ | ✅ | ✅ | △ |

## 9.3 기술 패턴 — ✅ 결정됨

Memory architecture, search APIs, generative agents 패턴 결정 (3.4 내용)

## 9.4 Eval 도구 참고 — ✅ 결정됨

- 외부 의존성 추가 안 함
- 4개 도구 패턴 차용 (3.2 내용)
- lm-eval은 RUN_ONCE 외부 도구

## 10. 위험 요소 (Risk Register) 분리

10.1 저작권 리스크 (HIGH)
10.2 개인정보 리스크 (HIGH, 한국 강함) ← 신규
10.3 미성년자 보호 (HIGH, 진입 조건) ← 신규
10.4 메모리 비용 (HIGH, 사용자 차별화이자 비용)  ← 신규
10.5 모델 lock-in (MEDIUM, GBNF 호환성)
... (기존 + 신규)

## 11. 테스트 전략 — Information Isolation 절충 추가

11.7 Information Isolation 검증 계획 ← 신규
- Tier 0에서 ablation: score 포함 retry vs issues-only retry
- 결과로 최종 결정
```

### 5.2 HARNESS_CORE.md 업데이트 항목

```markdown
## 4.4 Debate Mode — 강화

다음 추가:
- promptfoo의 redteam plugin × strategy 직교 분리 패턴 차용
- 적용: ip_leakage, ai_breakout 평가 시

## 5. Eval Set — 보강

5.1 디렉토리 구조에 다음 추가:
- evals/auto_added/ (AI Playtester 시드)
- evals/external_validation/ (lm-eval RUN_ONCE 시)

5.5 Filter Pipeline ← 신규
- lm-eval 패턴
- GBNF 실패 시 post-hoc JSON 추출 fallback

## 6. Scoring — 절충 검토

6.1 알고리즘에 추가:
- "geometric_mean 95+가 노이즈일 수 있음 — Tier 0 baseline 측정 후 결정"
- binary mechanical 비중 강화

## 8. Retry + Feedback Loop — Information Isolation 절충

8.4 Information Isolation Ablation Plan ← 신규
- Tier 0에서 양쪽 모드 모두 구현
- 100 케이스 비교: score 포함 vs issues-only
- 회귀 측정으로 최종 결정

## 9. LLM Client — 추론 서버 선택 추가

9.5 Inference Server ← 신규
- DGX Spark에서 SGLang 권장 (RadixAttention)
- llama.cpp는 단일 stream / 개발 환경
- vLLM은 메모리 over-allocation 주의

## 11. Configuration — 양자화 명시

quantization 필드 추가:
- nvfp4 / mxfp4 / q4_k_m 옵션
- DGX Spark 권장: nvfp4
```

### 5.3 HARNESS_LAYER2_SERVICE.md 업데이트

```markdown
## 4. Fallback Chain — 추론 서버별 구체화

Tier 1 chain:
  - sglang_qwen_8b_nvfp4 (DGX, 권장)
  - llama_cpp_qwen_8b_q4 (개발 환경)
  - claude_haiku (API fallback)
  - claude_sonnet
  - USER_REPORT

## 6. 비용/Latency — KV Cache 추가

6.4 KV Cache 추적 ← 신규
- 동시 세션 × KV size 추적
- DGX Spark 한도 알림

## 7. Empty State — 한국 시장 사용자 흐름

7.4 한국 시장 onboarding ← 신규
- 무료 진입 즉시 데모
- 5분 안에 첫 응답
- 가격 표시 (한국 기준)
```

### 5.4 AI_PLAYTESTER.md 업데이트

```markdown
## 3. 페르소나 — 한국 사용자 강조

10대-20대 비중 87% 반영:
- casual_korean_player → casual_korean_teen, casual_korean_20s 분리
- 새 페르소나: chaos_agent_minor (미성년자 보호 검증)
- 새 페르소나: paying_user_premium (결제 의향 검증)

## 5. 발견 이슈 → Eval 시드 — 한국 시장 특화

5.5 한국 시장 특화 카테고리 ← 신규
- ip_leakage_kr (한국 IP — 웹툰/웹소설/아이돌)
- minor_protection_violation
- payment_friction_korean
```

---

## 6. Action Items (우선순위)

### 즉시 (Tier 0 시작 전)

1. **ROADMAP v0.2 업데이트** (이 보고서 기반)
2. **HARNESS_CORE / LAYER2 / AI_PLAYTESTER v0.2**
3. **research/ 디렉토리 정리**
   ```
   research/
   ├── 01_models_and_sft/
   │   ├── gemini1_raw.md (이미 있음)
   │   ├── gemini2_raw.md (이미 있음)
   │   └── summary.md (요약 작성)
   ├── 02_competitive/
   │   ├── gpt1_raw.md
   │   └── summary.md
   ├── 03_technical_patterns/
   │   ├── gemini2_raw.md (다시 사용)
   │   ├── gpt2_raw.md
   │   └── summary.md
   ├── 04_eval_tools/
   │   ├── claude1_raw.md
   │   ├── claude2_raw.md
   │   └── summary.md
   └── 00_integrated_analysis.md (이 문서)
   ```

### Tier 0 첫 주

4. **Information Isolation ablation 실험**
   - 100 케이스, score 포함 vs issues-only
   - 결과로 HARNESS_CORE 8장 최종 확정

5. **Threshold 95+ 측정**
   - Tier 0 baseline에서 실제 분포 확인
   - 90+ vs 95+ 결정

### Tier 1 진입 전

6. **모델 / 추론 서버 선정 측정**
   - Qwen3-8B Dense vs Gemma 4 E4B
   - SGLang vs llama.cpp 실측
   - NVFP4 / MXFP4 / Q4_K_M 비교

7. **법적 검토 시작**
   - 한국 AI 투명성 가이드라인 적용
   - 미성년자 보호 설계 (이원화)
   - IP 마스킹 검증 방법론

---

## 7. 결과 신뢰도 평가

### 신뢰도 높음 (★★★)
- Eval 도구 4개 패턴 분석 (Claude 1, 2 일치)
- Dense > MoE (Gemini 1, 2 일치, 학술 근거)
- DGX Spark 메모리 대역폭 병목 (Gemini 2, 다수 출처)
- 한국 시장 동향 (GPT 1, 풍부한 출처)
- AutoGen 종료 / MAF 승계 (GPT 2, 공식 발표)

### 신뢰도 중간 (★★)
- SGLang 우월성 (DGX Spark에서) — 측정 권장
- NVFP4 결정성 — 실측 필요
- promptfoo OpenAI 인수 영향 — 향후 추적
- 한국 시장 가격 추정 — 실제 테스트 필요

### 신뢰도 낮음 (★ — 검증 필요)
- 정확한 사용자 수치 (DAU/MAU) — GPT 환각 가능
- 모델별 한국어 벤치마크 점수 — 본인 측정 필수
- 일본 시장 확장성 — 한국 검증 후
- 일부 인용 링크 — 본인 무작위 검증 권장

---

## 8. 결론

6개 딥리서치 결과는 WorldFork의 핵심 가설을 대체로 검증했고, 일부 결정에 새로운 근거를 제공했어요. 가장 큰 발견:

1. **WorldFork 전략이 한국 시장에 정합** — 서사형 + 한국어 + 차별화 모두 시장 대비 적절
2. **모델 선택 명확** — Qwen3-8B Dense + NVFP4 + SGLang
3. **Eval 시스템 강화** — 4개 도구 패턴 차용으로 자체 EvalRunner 설계 강화
4. **재검토할 결정 3개** — Threshold 95+, Information Isolation, GBNF 강제
5. **새 우려 4개** — promptfoo 인수, AutoGen 종료, 한국 규제, 메모리 비용

다음 작업은 **ROADMAP / HARNESS v0.2 업데이트** + **research/ 디렉토리 정리**.

---

*문서 끝. v0.1 통합 분석.*
