# Summary — 04 Eval Tools

> Claude 1, 2 결과 정리 (4개 도구 패턴 분석)
> 적용: ROADMAP 9.4, HARNESS_CORE 5.5 / 6 / 8

## 핵심 결정 (ROADMAP에 반영됨)

### 정책: 외부 의존성 0 + 패턴 차용

```
4개 도구 모두 분석:
  - promptfoo
  - deepeval
  - ragas
  - lm-evaluation-harness

채택 안 함: 도구 자체 의존성
차용: 검증된 패턴 4가지
```

### 차용 패턴 매트릭스

| 도구 | 차용 패턴 | HARNESS 적용 위치 |
|---|---|---|
| **promptfoo** | weight × threshold × metric_tag<br>redteam plugin × strategy<br>defaultTest 글로벌<br>position-swap | CORE 5장, 4.4 Debate, AI Playtester |
| **deepeval** | BaseMetric ABC<br>G-Eval evaluation_steps 자동<br>DAG decision-tree | CORE 3장, 6장 |
| **ragas** | PydanticPrompt schema 강제<br>claim-decomposition | CORE 3.2, Tier 1+ 작품 검색 |
| **lm-eval** | Filter pipeline (post-hoc)<br>metadata.version<br>Task versioning | CORE 5.5 (신규), 5.4 |

### 예외: lm-evaluation-harness "RUN_ONCE"

```
용도: Tier 3 출시 전 외부 검증 1회
- KoBEST, KMMLU, HAERAE 점수
- generator 후보 모델 1차 필터링
- 검증 후 의존성 제거
```

## 핵심 발견

### 1. Cross-tool 공통 패턴 (3+ 도구) (★★★)

```
4/4 모두 가진 패턴 = best practice:
  
  ✅ LLM-as-judge with separate grader
     → Cross-Model verification 정당화
     
  ✅ Threshold 기반 pass/fail + 0~1 정규화
     → HARNESS의 score 시스템과 일치
     
  ✅ Custom metric base class
     → BaseMetric ABC 패턴 차용
     
  ✅ Async / 동시성 + 캐시
     → 비용 효율
     
  ✅ Reason alongside score
     → "verdict + 이유" 둘 다 출력
```

### 2. 단일 도구 고유 패턴 (★★)

```
promptfoo만:
  - plugin × strategy 직교 분리 (redteam)
  - --repeat 분산 측정
  
deepeval만:
  - DAG decision-tree
  - pytest 통합
  
ragas만:
  - KnowledgeGraph + evolution 합성 테스트
  - PydanticPrompt
  
lm-eval만:
  - Filter pipeline
  - Task versioning
  - KoBEST 등 Korean 태스크
```

### 3. HARNESS의 비주류 결정 검토 (★★★ 자기비판)

#### Cross-Model verification — 정당함

```
근거: Wataoka et al. 2024 [VERIFIED]
  - GPT-4가 자기 출력에 유리한 점수 (self-preference bias)
  - Cross-family judge가 가장 효과적 완화책

비용 우려:
  - Layer 1 매 commit = CI 비용 폭증
  - 외부 도구는 cost-aware grader 옵션 강조
  - WorldFork도 token-budget 메커니즘 명시 필요
```

#### Information Isolation — 부분적 정당, 위험

```
이론: prompt-leak 방지에 좋음
실증: 4개 외부 도구 어디도 안 함
  - retry 메커니즘 자체가 약함 (promptfoo --repeat은 새 호출)
  - 학습 신호로서 score가 가장 강함
  - issues+suggestions만으로 충분한지 미검증

권장 (Claude 2):
  Tier 0에서 ablation 실험
  A: score 노출
  B: issues only (현재)
  C: 절충 (어떤 메트릭의 score인지 비식별)
  
→ ROADMAP 11.7.1 + HARNESS_CORE 8.4 신규 섹션
```

#### GBNF 강제 — 정당 + lock-in

```
정당성:
  - llama.cpp / vLLM / SGLang grammar 지원
  - JSON 100% 안정성
  
lock-in 위험:
  - Claude / GPT-4o는 grammar 미지원
  - Layer 1 verifier 후보 좁아짐
  - 자료 함정 19도 post-hoc 검증 권장

해결책:
  Filter Pipeline (lm-eval 패턴 차용)
  - GBNF 시도 → 실패 시 post-hoc JSON 추출
  → HARNESS_CORE 5.5 신규 섹션
```

#### Ship gate 95+ — 과도하게 엄격할 가능성

```
근거 (Claude 2 비판):
  - judge LLM은 0.7-0.9 구간에 답 몰림
  - deepeval default 0.5
  - promptfoo도 명시적 threshold 미설정 시 자유
  - 95+는 노이즈일 수 있음

권장:
  Tier 0에서 점수 분포 측정
  - Mechanical (binary) 비중 강화
  - LLM Judge weight 낮춤
  - 또는 95+ → 90+로 완화
  → ROADMAP 11.7.2 신규
```

### 4. 한국어 평가 — Common Runner + Korean Scorer (★★★)

```
연구 (KUDGE):
  - 영어 LLM-Judge 능력이 한국어로 잘 전이
  - 단, 사실 오류 / 문화 왜곡 / 존댓말-반말 일관성은 약함

WorldFork 권장:
  - 한국어 전용 별도 runner 만들지 X
  - Common EvalRunner + Korean-specific Scorer plugin
  - KMMLU/HAE-RAE/KUDGE 데이터는 Tier 3 외부 검증 1회용
  - 존댓말/반말 일관성 = mechanical 룰 (외부 도구 어디에도 없음)
```

### 5. Tier 0 즉시 적용 코드 (~80줄) (★★★)

```python
# core/eval/tier0_quickwins.py - 외부 의존 0

1. EvalSet fingerprint 무결성 (lm-eval 패턴)
   - 한 번 잘 만들고 영원히 작동 함정 회피

2. defaultTest 글로벌 negative-rubric (promptfoo)
   - AI breakout regex
   - IP blocklist
   - 15단어 인용 휴리스틱

3. 한국어 존댓말/반말 일관성 (mechanical)
   - 외부 도구 어디에도 없음
   - 자료 검증된 한국어 특화 룰

4. G-Eval evaluation_steps 자동 생성 + 캐시 (deepeval)
   - judge 호출 비용 절감
   - 일관된 평가 기준

5. position-swap pairwise (학술 + promptfoo)
   - position bias 검출
```

## 실행 가능한 클래스 outline

```python
# CORE 핵심 클래스 (4개 도구 통합 차용)

class BaseMetric(ABC):
    """deepeval BaseMetric"""
    threshold: float
    
    @abstractmethod
    def measure(self, response, context) -> MetricResult: ...
    @abstractmethod
    async def a_measure(self, response, context) -> MetricResult: ...

@dataclass
class Assertion:
    """promptfoo 3-속성"""
    type: Literal["mechanical", "llm_rubric", "g_eval", "py_fn"]
    weight: float = 1.0
    threshold: float = 0.5
    metric: Optional[str] = None    # 카테고리 태그

class FilterPipeline:
    """lm-eval 패턴, GBNF fallback"""
    filters: list[Filter]
    def apply(self, raw_output) -> FilterResult: ...

class JudgePrompt:
    """ragas PydanticPrompt"""
    input_schema: BaseModel
    output_schema: BaseModel

class EvalSpec:
    """lm-eval metadata.version"""
    version: str = "0.1.0"
    items: list[EvalItem]
```

## 신뢰도

- ★★★ 4개 도구 분석: Claude 1, 2 일치 (자기비판 모드 활성)
- ★★★ Cross-tool 공통 패턴: 3+ 도구 검증
- ★★ 한국어 평가 (KUDGE 연구): Claude 2의 학술 인용
- ★★ Information Isolation 비판: 외부 도구 부재 검증, ablation 권장

## 자기비판 부분 (Claude 2 강조)

```
"본 분석을 작성한 모델 자체가 HARNESS 문서를 작성한 모델과 동일하므로, 
비판 섹션에서도 미묘한 자기 정당화가 잔존할 수 있다."

권장: 
  - 외부 reviewer (다른 모델 또는 인간 엔지니어)로 한 번 더 검증
  - 특히 "Cross-Model verification은 정당함" 결론
  - 비용 대 효과는 여전히 HARNESS 우호적
```

## 미해결 / 측정 권장

1. Information Isolation ablation (Tier 0 첫 주, 11.7.1)
2. Ship gate 95+ 적정성 (Tier 0 baseline, 11.7.2)
3. GBNF + Filter Pipeline 효과 (Tier 1 진입, 11.7.3)
4. lm-eval RUN_ONCE 시점 (Tier 3 출시 전)

## Raw 결과 참조

- `claude1_raw.md`: WorldFork EvalRunner 보고서 (694줄, 한국어)
  - 더 상세, 코드 예시 풍부
  - Tier 0 즉시 적용 코드 포함
- `claude2_raw.md`: WorldFork HARNESS Eval 비교 (456줄, 한국어)
  - 더 자기비판적
  - HARNESS 결정 자체에 대한 비판 강함

두 보고서 보완적 — 1번이 코드 패턴, 2번이 자기비판 강함.
