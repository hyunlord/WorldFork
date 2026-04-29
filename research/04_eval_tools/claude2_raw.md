# WorldFork HARNESS를 위한 LLM 평가 도구 4종 심층 비교 분석

## TL;DR (3 bullets)
- **promptfoo / deepeval / ragas / lm-evaluation-harness 모두 LLM-as-judge + threshold + custom metric 베이스 클래스**라는 공통 패턴을 가지지만, 각 도구가 독자적으로 발전시킨 강점(promptfoo의 plugin×strategy 분리, deepeval의 DAG, ragas의 PydanticPrompt + KG-기반 합성 테스트셋, lm-eval-harness의 Filter pipeline + Task versioning)은 HARNESS가 아직 흡수하지 않은 영역이며 **선별적으로 차용**할 가치가 있습니다.
- HARNESS의 핵심 결정 사항(Cross-Model verification, Information isolation, GBNF 강제, 95/70 dual threshold) 중 일부는 학술적으로 정당화되지만(self-preference bias 완화, [VERIFIED]), **GBNF 강제와 Information isolation은 외부 4개 도구 어느 것도 채택하지 않는 비주류 선택**이며 실패 모드에 대한 근거가 추가로 필요합니다.
- 권장: 자체 EvalRunner를 유지하되, ① **deepeval의 BaseMetric 인터페이스 형태**(measure/a_measure/is_successful/threshold/reason), ② **lm-eval-harness의 Filter pipeline 및 Task version 키**, ③ **promptfoo의 weighted assertion + derived metric 집계**, ④ **ragas의 PydanticPrompt 패턴**을 코드 레벨에서 차용. 프레임워크 자체 의존은 추가하지 않습니다.

---

## Key Findings

### 1) 4개 도구 공통 패턴 (3+ 도구에 등장 → best practice)
- **LLM-as-judge with separate grader model**: 4/4 모두. 자기-선호 편향(self-preference bias)을 완화하기 위해 평가 모델을 분리하라는 최근 연구(Wataoka et al., 2024 [VERIFIED])와 정합. → HARNESS의 Cross-Model verification은 이 best practice에 부합.
- **Threshold 기반 pass/fail + 0~1 정규화 score**: 4/4 모두. (deepeval default 0.5, promptfoo `threshold`, ragas `threshold`, lm-eval `higher_is_better`).
- **Custom metric base class**: deepeval `BaseMetric`, ragas `MetricWithLLM/SingleTurnMetric`, lm-eval `Task` 클래스 → HARNESS도 동일 패턴 권장.
- **Async / 동시성 + 캐시**: promptfoo, deepeval (`AsyncConfig`, `CacheConfig`), lm-eval (`--cache_requests`).
- **Reason alongside score (verdict + 이유)**: deepeval `self.reason`, ragas `Verification.reason`, promptfoo llm-rubric JSON `{reason, score, pass}`.

### 2) 한 도구만 가진 패턴 (선별적 차용)
- **plugin × strategy 직교 구조 (promptfoo redteam만)**: plugin이 "어떤 취약성 카테고리"인가, strategy가 "어떻게 전달"하는가를 분리. 매우 깔끔한 설계.
- **DAG decision-tree metric (deepeval만)**: TaskNode → BinaryJudgmentNode → VerdictNode 위상 정렬 순회. 결정론성이 필요한 평가에 강력.
- **Filter pipeline (lm-eval만)**: 같은 모델 출력에 multiple parallel filter chain (예: gsm8k strict-match vs flexible-extract).
- **Task versioning + KoBEST 등 Korean 태스크 (lm-eval만, [VERIFIED])**: `metadata.version` 키로 재현성 추적.
- **KnowledgeGraph + evolution-기반 합성 테스트 (ragas만)**: simple/reasoning/multi_context 분포 지정.

---

## Details

### 도구 1: promptfoo

**Architecture pattern**
promptfoo는 Node/TS 기반 CLI로, `promptfooconfig.yaml`을 단일 진입점으로 둡니다. 구조는 `prompts × providers × tests` 데카르트 곱 매트릭스를 평가하는 모델로, 각 셀(`EvaluateResult`)에 대해 `assert: [...]` 배열을 적용합니다 [VERIFIED]. Assertion은 결정적(`contains`, `is-json`, `regex`, `javascript`/`python`)과 모델-기반(`llm-rubric`, `g-eval`, `factuality`, `select-best`, `model-graded-closedqa`)이 공존하며, 각각 `weight`, `threshold`, `metric` (집계 태그) 속성을 가집니다. `defaultTest`는 모든 테스트에 상속되는 베이스 설정이며 `defaultTest.options.provider`로 grader 모델을 글로벌하게 오버라이드합니다. 결과 집계는 (a) 가중 평균 score → threshold pass/fail, (b) `metric` 태그로 묶인 aggregate metric, (c) 평가 후 산출되는 `derivedMetric` (custom JS expression).

**훔칠 만한 5가지**
1. **`weight` + `threshold` + `metric` 태그 3-속성 모델** — 단순한데 표현력이 높음. HARNESS의 mechanical checker / persona / Korean naturalness 등을 메트릭 태그로 묶어 카테고리별 집계가 가능.
2. **`rubricPrompt` 다국어 오버라이드 패턴** — promptfoo 공식 문서가 한국어/일본어/독일어 system message로 grader 출력 언어를 제어하는 예시를 명시 [VERIFIED]. HARNESS Korean-first 환경에서 그대로 응용 가능.
3. **`plugin × strategy` 분리 (redteam)** — IP leakage / AI breakout / persona break 등을 plugin으로, 전달 방식(직접, 다중 turn, 인코딩, jailbreak)을 strategy로 분리하면 AI Playtester 어드밴서리얼 모듈을 깔끔히 설계할 수 있음.
4. **`--repeat N` + 기본 비결정성 인지** — "Same prompt produces different results across runs ... measure variance" [VERIFIED]. HARNESS의 retry 3회와는 다른 *측정 분산* 개념. 두 가지를 구분해야 함.
5. **Python provider `file://` 인터페이스** — `call_api(prompt, options, context) -> dict` 시그니처는 Korean LLM 백엔드 통합 시 차용 가능.

**훔치지 말 것**
- Node/TS 런타임 의존성 → 외부 의존 최소화 정책에 위배.
- Web viewer, Cloudflare KV share — 게임 보안상 불필요.
- `model-graded-closedqa` 등 OpenAI evals에서 단순 포팅한 prompt들 — 한국어 도메인 평가에 그대로 쓰기엔 부적합.
- Cloud-targeted enterprise red-team service — 자체 시나리오로 충분.

**코드 예시 (Python 등가)**
```python
# harness/assertion.py
from dataclasses import dataclass
from typing import Callable, Literal, Optional

@dataclass
class Assertion:
    type: Literal["contains", "is_json", "regex", "llm_rubric", "py_fn"]
    value: str | Callable | None = None
    weight: float = 1.0
    threshold: float = 0.5
    metric: Optional[str] = None  # 태그 집계용 (예: "PersonaConsistency")

@dataclass
class AssertResult:
    passed: bool
    score: float          # 0~1
    reason: str
    metric_tag: Optional[str]

class AssertionRunner:
    def __init__(self, judge_invoker, mechanical_invoker):
        self.judge = judge_invoker         # cross-model judge
        self.mech = mechanical_invoker     # 정규식/JSON validator 등

    def run(self, output: str, ctx: dict, assertions: list[Assertion]) -> list[AssertResult]:
        results = []
        for a in assertions:
            if a.type == "is_json":
                ok = self.mech.is_valid_json(output, schema=a.value)
                results.append(AssertResult(ok, 1.0 if ok else 0.0,
                                            "schema valid" if ok else "schema invalid",
                                            a.metric))
            elif a.type == "llm_rubric":
                # cross-model 강제: judge 모델 != 생성 모델
                v = self.judge.grade(output, rubric=a.value, ctx=ctx)
                results.append(AssertResult(v.score >= a.threshold,
                                            v.score, v.reason, a.metric))
            # ... contains / regex / py_fn
        return results

    @staticmethod
    def aggregate(results: list[AssertResult]) -> dict:
        # promptfoo 식 weighted average
        total_w = sum(r.weight for r in results) or 1.0
        composite = sum(r.score * r.weight for r in results) / total_w
        # metric 태그별 micro-mean
        by_tag: dict[str, list[float]] = {}
        for r in results:
            if r.metric_tag:
                by_tag.setdefault(r.metric_tag, []).append(r.score)
        per_tag = {k: sum(v) / len(v) for k, v in by_tag.items()}
        return {"composite": composite, "by_metric": per_tag}
```

---

### 도구 2: deepeval

**Architecture pattern**
deepeval은 pytest 통합형 Python 프레임워크입니다. 핵심 추상은 `LLMTestCase(input, actual_output, expected_output, retrieval_context, ...)`와 `BaseMetric` (`measure(test_case) -> float`, `a_measure`, `is_successful`, `threshold`, `score`, `reason`, `error`) 둘로 구성됩니다 [VERIFIED, 공식 docs]. 메트릭은 50+개 내장(G-Eval, DAG, Faithfulness, AnswerRelevancy, ContextualRelevancy 등)이며, 거의 모두 LLM-as-judge 기반인데 내부적으로 **QAG (Question-Answer-Generation)** 패턴을 사용 — 출력을 atomic claim으로 쪼개고 각각에 verdict를 받아 비율 집계 [VERIFIED]. G-Eval은 criteria → CoT evaluation_steps 자동 생성 → form-filling score → 토큰 확률 정규화. DAG (2025-02 도입, [VERIFIED])는 TaskNode/BinaryJudgmentNode/NonBinaryJudgmentNode/VerdictNode를 위상 정렬 순회하여 결정론적 점수 산출.

**훔칠 만한 4가지**
1. **`BaseMetric` 시그니처 정확히 그대로** — `score / threshold / reason / error / success` 속성 + sync/async 짝. HARNESS Eval Runner의 메트릭 인터페이스 표준으로 거의 그대로 사용 가능.
2. **QAG (claim 분해 → 개별 verdict → 비율 집계)** — Korean naturalness, world canon consistency, IP leakage 등 multi-fact 검사에 특히 적합. 단일 LLM 호출로 "0~1 점수 줘"하는 것보다 hallucination이 적음.
3. **DAG decision-tree metric** — *결정론*이 필요한 평가(예: "JSON valid한가? → No이면 0점 / Yes이면 persona 검사로 진행")에 G-Eval보다 우월. HARNESS의 Mechanical Checker → LLM Judge 흐름을 한 메트릭 안에 묶는 데 이상적. ⚠️ DAG의 노드는 기본적으로 LLM 기반이며, 사용자들이 "deterministic 노드 추가" feature request를 올렸다는 점은 알려진 한계 [VERIFIED, GitHub issue #1472].
4. **`evaluation_cost` / 캐시 / `strict_mode` 스위치** — 토큰 비용 추적은 layer 2 service 운영 시 필수. `strict_mode=True`는 binary 0/1만 허용 → ship gate 95+ 같은 hard threshold와 잘 맞음.

**훔치지 말 것**
- pytest dependency / `deepeval test run` CLI — HARNESS는 이미 자체 runner가 있음.
- Confident AI 클라우드 통합 (MCP server, dataset cloud) — 게임 IP 보호 정책상 사용 불가.
- 50+ pre-built metric 전체 — 대부분 영어/RAG 가정. 필요한 것만 패턴 차용.

**코드 예시 (HARNESS_CORE 스타일)**
```python
# harness/metric_base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class TestCase:
    input: str
    actual_output: str
    expected_output: str | None = None
    context: list[str] | None = None
    metadata: dict | None = None  # persona_id, world_canon_refs 등

class BaseMetric(ABC):
    threshold: float = 0.7
    score: float = 0.0
    reason: str = ""
    success: bool = False
    error: str | None = None
    cost_usd: float = 0.0

    @abstractmethod
    async def a_measure(self, tc: TestCase) -> float: ...

    def is_successful(self) -> bool:
        return self.error is None and self.success

# deepeval QAG 패턴을 차용한 한국어 자연스러움 메트릭
class KoreanNaturalnessMetric(BaseMetric):
    def __init__(self, judge, threshold: float = 0.7):
        self.judge, self.threshold = judge, threshold

    async def a_measure(self, tc: TestCase) -> float:
        # 1) 응답을 문장 단위 claim으로 분해
        sentences = await self.judge.split_sentences_ko(tc.actual_output)
        # 2) 각 문장에 대해 어색함/번역체/존비어 일관성 verdict
        verdicts = await self.judge.batch_judge(
            sentences,
            rubric="다음 한국어 문장은 모국어 화자에게 자연스러운가? "
                   "어색하면 0, 자연스러우면 1. 이유를 함께 답하라.",
            schema={"verdict": "int", "reason": "str"}
        )
        # 3) 비율 집계 (deepeval QAG)
        passed = sum(v["verdict"] for v in verdicts)
        self.score = passed / max(len(verdicts), 1)
        self.reason = "; ".join(
            v["reason"] for v in verdicts if v["verdict"] == 0
        )[:500] or "all sentences natural"
        self.success = self.score >= self.threshold
        return self.score
```

---

### 도구 3: ragas

**Architecture pattern**
ragas는 RAG에 특화된 Python 평가 라이브러리이지만, 메트릭 추상은 일반화되어 있습니다. 핵심은 `Metric` (abstract) + mixin (`SingleTurnMetric`, `MultiTurnMetric`, `MetricWithLLM`, `MetricWithEmbeddings`)으로 다중 상속을 사용합니다 [VERIFIED, ragas/metrics/base.py]. 데이터는 `SingleTurnSample(user_input, response, retrieved_contexts, reference, ...)`. 차별화 포인트는 (1) **`PydanticPrompt[Input, Output]`** — prompt I/O를 Pydantic schema로 강제하여 grader 출력 파싱 안정성을 높임, (2) **`_required_columns`** — 메트릭이 어떤 필드를 요구하는지 선언적으로 명시, (3) **합성 테스트셋 생성**: Document → KnowledgeGraph (Node + Relationship) → default_transforms로 enrich → personas + scenarios → simple/reasoning/multi_context evolution 분포로 query 생성 [VERIFIED, ragas/testset/synthesizers]. 최신 ragas는 `@discrete_metric`, `@numeric_metric`, `@ranking_metric` 데코레이터 API도 제공.

**훔칠 만한 4가지**
1. **`PydanticPrompt[Input, Output]` 패턴** — judge prompt의 입력 타입과 출력 타입을 Pydantic 스키마로 묶음. HARNESS가 GBNF로 generation을 강제하듯, judge 출력에도 schema를 강제하면 파싱 실패율이 극적으로 떨어집니다 (실측 보고 다수, [INFERRED]).
2. **`_required_columns` 선언적 의존성** — 어떤 메트릭이 어떤 입력을 요구하는지 메타데이터로 가지면, runner가 미리 검증하여 layer 1 ship gate에서 schema mismatch를 빠르게 잡을 수 있음.
3. **KnowledgeGraph + persona-기반 합성 테스트 시드** — WorldFork의 world canon, NPC persona를 그대로 KG로 모델링하면 합성 dialogue 시드 생성에 활용 가능 → AI Playtester 입력 다양성 확보.
4. **`@discrete_metric` / `@numeric_metric` 데코레이터** — 가벼운 mechanical checker(예: AI breakout regex 검사)는 클래스 보일러플레이트 없이 함수형으로 정의.

**훔치지 말 것**
- Faithfulness, ContextRecall 등 RAG 핵심 메트릭 자체 — WorldFork는 RAG 시스템이 아님 (게임 상태/persona 기반). RAG 메트릭을 무리하게 매핑하면 평가 노이즈가 됨.
- LangChain wrapper (`LangchainLLMWrapper`) — 외부 의존 추가 의미 없음.
- evolution-기반 query 생성을 그대로 차용 — 영어 corpus 가정. 한국어 게임 대화에 맞춤 설계 필요.

**코드 예시 (PydanticPrompt 패턴)**
```python
# harness/judge_prompt.py
from pydantic import BaseModel, Field
from typing import Generic, TypeVar

I = TypeVar("I", bound=BaseModel)
O = TypeVar("O", bound=BaseModel)

class JudgePrompt(Generic[I, O]):
    instruction: str
    input_model: type[I]
    output_model: type[O]
    examples: list[tuple[I, O]] = []

    async def grade(self, judge_llm, data: I) -> O:
        rendered = self._render(data)
        # GBNF가 generator에 적용되듯, judge에는 JSON schema enforcement
        raw = await judge_llm.complete(
            rendered, json_schema=self.output_model.model_json_schema()
        )
        return self.output_model.model_validate_json(raw)

# WorldFork persona 일관성 메트릭의 prompt
class PersonaInput(BaseModel):
    persona_card: str = Field(description="NPC 페르소나 카드")
    user_utterance: str
    npc_response: str

class PersonaVerdict(BaseModel):
    in_character: bool
    issues: list[str] = Field(description="페르소나 이탈 항목")
    suggestions: list[str] = Field(description="개선 제안")
    # ⚠️ 의도적으로 score/verdict 점수는 출력 schema에서 제외
    # Information isolation: retry feedback에 이 객체에서 issues+suggestions만 노출

class PersonaConsistencyPrompt(JudgePrompt[PersonaInput, PersonaVerdict]):
    instruction = (
        "다음 NPC 응답이 주어진 페르소나 카드와 일치하는지 판정하라. "
        "이탈 항목과 개선 제안을 한국어로 작성하라."
    )
    input_model = PersonaInput
    output_model = PersonaVerdict
```

---

### 도구 4: lm-evaluation-harness

**Architecture pattern**
EleutherAI의 academic 벤치마크 harness. 모든 task는 `TaskConfig` dataclass의 YAML 표현이며, `output_type ∈ {generate_until, loglikelihood, multiple_choice, loglikelihood_rolling}` 4종만 존재합니다 [VERIFIED, lm_eval/api/task.py]. 모델 인터페이스는 `LM` 추상 클래스 (`generate_until`, `loglikelihood`, `loglikelihood_rolling`) 단 3개. 평가 흐름은 `dataset → doc_to_text/doc_to_target → LM.generate_until → Filter pipeline → metric_list aggregation`. 강력한 두 가지: (1) **Filter pipeline** — 같은 모델 출력에 *다중 병렬 filter chain*을 걸 수 있음 (예: gsm8k에 strict-match와 flexible-extract 동시 적용 후 self-consistency majority vote), (2) **`include`** YAML 상속과 `metadata.version` 키로 task 재현성을 못박음.

KoBEST, KMMLU, HAERAE, KoBEST-BoolQ 등 한국어 태스크가 이미 lm-eval-harness에 포팅되어 있음 [VERIFIED]. WorldFork가 베이스 모델 capability check (예: "KMMLU 70% 이상인 모델만 generator로 채택")이 필요하다면 직접 사용 가치가 있음.

**훔칠 만한 3가지**
1. **Filter pipeline (`filter_list`)** — `take_first`, `regex_extract`, `majority_vote` 같은 출력 후처리를 메트릭과 분리. HARNESS의 retry 3회는 이미 self-consistency의 일종이지만, lm-eval은 *같은 출력*에 *복수 추출 정책*을 동시에 적용해 어느 쪽이 더 robust한지 비교할 수 있다는 점이 다름. AI Playtester 출력에서 "선택한 액션"을 뽑는 데 유용.
2. **`metadata.version` + 결과 dict의 task version 키 동봉** — ROADMAP 9.4 단계에서 평가 결과를 git에 커밋한다면 *eval definition version*도 함께 기록하지 않으면 회귀 분석이 불가능. 이 키 한 줄이 6개월 후 큰 도움이 됨.
3. **`output_type` 명시적 enum** — 한국어 게임 평가는 거의 `generate_until` 한 종류이지만, 미래에 multiple-choice persona test (예: "이 페르소나가 다음 4가지 중 어떤 행동을 할까?")를 도입할 가능성을 미리 인터페이스로 열어두는 것은 저비용 베팅.

**훔치지 말 것**
- HuggingFace `datasets` 의존 — 자체 한국어 데이터로 충분.
- `loglikelihood`-기반 multiple-choice scoring 메커니즘 — closed API (Claude, GPT) 사용 시 logprob을 모두 못 받으므로 적용 한계. WorldFork가 generate_until 방식만 쓴다면 불필요한 복잡성.
- 학술 task 600+개 — 95% 이상이 영어이며 게임 도메인과 무관.

**코드 예시 (Filter pipeline 차용)**
```python
# harness/filters.py
from typing import Callable, Iterable
import re, json

Filter = Callable[[list[str]], list[str]]

def regex_extract(pattern: str, group: int = 1) -> Filter:
    rx = re.compile(pattern, re.DOTALL)
    return lambda outs: [(m.group(group) if (m := rx.search(o)) else "") for o in outs]

def take_first() -> Filter:
    return lambda outs: [outs[0]] if outs else [""]

def majority_vote() -> Filter:
    def _f(outs):
        if not outs: return [""]
        counts = {}
        for o in outs: counts[o] = counts.get(o, 0) + 1
        return [max(counts, key=counts.get)]
    return _f

def json_extract() -> Filter:
    # GBNF가 100% 보장하지만, Layer 2에서 GBNF 실패 시 fallback
    def _f(outs):
        results = []
        for o in outs:
            try: json.loads(o); results.append(o)
            except Exception:
                m = re.search(r"\{.*\}", o, re.DOTALL)
                results.append(m.group(0) if m else "")
        return results
    return _f

class FilterPipeline:
    def __init__(self, name: str, steps: list[Filter]):
        self.name, self.steps = name, steps
    def apply(self, outputs: list[str]) -> list[str]:
        cur = outputs
        for f in self.steps: cur = f(cur)
        return cur

# 같은 출력에 두 파이프라인 동시 적용 (lm-eval 핵심)
PIPELINES = [
    FilterPipeline("strict-json", [json_extract(), take_first()]),
    FilterPipeline("majority-vote", [json_extract(), majority_vote()]),
]
```

---

## 종합 비교 및 WorldFork 권장 사항

### A. Cross-tool 패턴 정리
| 패턴 | promptfoo | deepeval | ragas | lm-eval | HARNESS 채택 권장 |
|---|:---:|:---:|:---:|:---:|---|
| LLM-as-judge with separate grader | ✓ | ✓ | ✓ | ✓ | ✓ (이미 있음) |
| Threshold + 0-1 score | ✓ | ✓ | ✓ | ✓ | ✓ (이미 있음) |
| Custom metric base class | – | ✓ | ✓ | ✓ | ✓ **`BaseMetric` 표준화** |
| Async + cache | ✓ | ✓ | ✓ | ✓ | ✓ Layer 2 필수 |
| Reason + score 동시 반환 | ✓ | ✓ | ✓ | – | ✓ (Information isolation에서 score만 빼고 노출) |
| Filter pipeline | – | – | – | ✓ | ✓ **신규 도입 권장** |
| Plugin × Strategy 분리 | ✓ (redteam) | – | – | – | ✓ AI Playtester에 채택 |
| DAG decision-tree | – | ✓ | – | – | △ 복잡도가 정당화될 때만 |
| Synthetic test generation | △ (redteam) | △ (Synthesizer) | ✓ (KG-evolution) | – | △ 별도 모듈로 |
| Task versioning | – | – | – | ✓ | ✓ **반드시 도입** |
| Weighted assertions | ✓ | – | – | △ | ✓ |
| JSON-schema-enforced judge output | – | △ | ✓ (Pydantic) | – | ✓ ragas 패턴 차용 |

### B. WorldFork 요구사항별 베스트 매핑
- **한국어 평가**: promptfoo의 `rubricPrompt` 다국어 시스템 메시지 패턴이 가장 단순 [VERIFIED]. lm-eval은 KoBEST/KMMLU 등 한국어 *베이스 모델 capability* 벤치를 이미 갖고 있어 모델 선택에 활용 가능. → judge prompt는 한국어로 작성하고 system message에 "이유는 한국어로 답하라"를 명시.
- **게임 특화 criteria (persona, world canon, IP leakage, AI breakout)**: deepeval의 **DAG**가 개념적으로 가장 정합 — "JSON valid? → IP 누출? → AI breakout? → persona 일치?" 같은 단계적 게이트는 flat scoring보다 디버깅이 쉬움. 단, 비용 문제로 Layer 1만 DAG, Layer 2는 단일 composite metric 권장 [INFERRED].
- **Dual-layer (95 ship gate / 70 service)**: 어떤 외부 도구도 dual threshold를 native 지원하지 않음. deepeval `strict_mode=True`로 95 gate를 흉내낼 수 있으나, 자체 구현이 더 깔끔. promptfoo의 `weight × threshold` 모델이 dual layer에 가장 자연스러움.
- **AI Playtester 통합**: promptfoo redteam의 plugin × strategy 직교 구조를 그대로 차용. Playtester는 *strategy* 역할 (멀티턴 대화 유도, 페르소나 시험), HARNESS의 평가 카테고리는 *plugin* 역할.

### C. 자체 EvalRunner 핵심 클래스 outline (~30줄)

```python
# harness/eval_runner.py
import asyncio
from dataclasses import dataclass, field

@dataclass
class EvalSpec:
    version: str                              # ← lm-eval 차용 (재현성)
    layer: Literal["dev", "service"]
    threshold: float                           # 95 / 70
    metrics: list[BaseMetric]                  # ← deepeval BaseMetric 표준
    filters: dict[str, FilterPipeline] = field(default_factory=dict)  # ← lm-eval
    max_retries: int = 3                       # service만 사용
    grader_model: str = ""                     # ← cross-model 강제

@dataclass
class EvalResult:
    passed: bool
    composite_score: float
    by_metric: dict[str, float]
    reasons: dict[str, str]
    isolated_feedback: dict | None             # retry시만 노출 (issues+suggestions)
    cost_usd: float
    spec_version: str

class EvalRunner:
    def __init__(self, generator, judge, mech_checker):
        assert generator.model_id != judge.model_id, "cross-model required"
        self.gen, self.judge, self.mech = generator, judge, mech_checker

    async def run(self, tc: TestCase, spec: EvalSpec) -> EvalResult:
        # 1) 메트릭 동시 실행 (deepeval async pattern)
        scores = await asyncio.gather(*(m.a_measure(tc) for m in spec.metrics))
        # 2) promptfoo 식 weighted aggregate + tag별 micro-mean
        composite = sum(scores) / len(scores)
        passed = composite >= spec.threshold
        # 3) Information isolation 적용
        feedback = self._isolate(spec.metrics) if not passed else None
        return EvalResult(passed, composite,
                          {m.__class__.__name__: m.score for m in spec.metrics},
                          {m.__class__.__name__: m.reason for m in spec.metrics},
                          feedback,
                          sum(m.cost_usd for m in spec.metrics),
                          spec.version)

    def _isolate(self, metrics) -> dict:
        # score/verdict 절대 노출 금지, issues+suggestions만 추출
        return {"issues": [m.reason for m in metrics if not m.success],
                "suggestions": [getattr(m, "suggestion", "") for m in metrics]}
```

**무엇이 반드시 필요한가**
- BaseMetric 표준 인터페이스 (deepeval 패턴)
- Filter pipeline (lm-eval 패턴, JSON 추출 fallback에 필수)
- Spec version 키 (재현성)
- Cross-model assert (생성 ≠ 평가 모델)
- PydanticPrompt-style judge schema (ragas 패턴)
- Async batched judge 호출 (비용)

**무엇이 명시적으로 불필요한가**
- pytest 통합 (자체 Layer 1 ship gate가 동등 역할)
- Web viewer / cloud share
- Embedding-기반 메트릭 (지금은 X, 미래 옵션)
- 내장 RAG 메트릭 (faithfulness/context_recall) — WorldFork는 RAG가 아님
- 50+ pre-built 메트릭 — 게임 도메인 노이즈

### D. HARNESS 설계에 대한 비판적 자기-검토

이 섹션이 사용자가 가장 명시적으로 요청한 부분이며, 외부 도구를 분석한 *후* 작성합니다.

**1. 외부 3+ 도구가 가지는데 HARNESS에 누락된 것**
- **Task/Spec versioning** — lm-eval은 `metadata.version`을 강제. HARNESS 문서에 eval criteria 변경을 추적하는 키가 명시되지 않은 듯함 [SPECULATIVE, 첨부 문서 미확인]. Layer 1 ship gate 점수가 92 → 96으로 변할 때, 모델이 좋아진 건지 criteria가 완화된 건지 구분 못 하면 회귀 분석 불가.
- **Filter pipeline** — promptfoo, lm-eval 모두 출력 후처리를 메트릭과 분리. HARNESS는 GBNF로 출력 형태를 강제하므로 필요 없다고 가정할 수 있지만, **GBNF 실패 시 fallback** 경로가 필요. 외부 도구는 다중 추출 전략을 병렬로 시도해 robust.
- **Position/order swap, repeat 분산 측정** — promptfoo `--repeat 3`, deepeval `strict_mode`. HARNESS의 retry는 *재시도*이지 *측정 분산 추정*이 아님. Service Layer threshold 70이 모델 비결정성에서 오는 분산을 흡수할 수 있는지 확인 필요.
- **Weighted aggregation + metric 태그 집계** — promptfoo는 카테고리별 micro-mean을 제공. HARNESS가 7개 criteria를 단일 composite로 평균하면 "한국어 자연스러움이 30점이지만 다른 게 100점이라 통과" 같은 사고가 가능.

**2. HARNESS가 외부 도구가 회피하는 비주류 선택을 한 부분 (정당성 검토)**
- **Cross-Model verification 필수화** — *정당함*. Wataoka et al. 2024 [VERIFIED]는 GPT-4가 자기 출력에 유리한 점수를 주는 self-preference bias를 정량화했고, 가장 직접적인 완화책이 cross-family judge. 단, **비용이 2배** — Layer 1 ship gate가 매 commit 실행이라면 CI 비용 폭증. 외부 도구는 cost-aware grader 옵션을 강조 (deepeval `evaluation_cost`). HARNESS도 명시적인 token-budget 메커니즘이 필요해 보임.
- **Information isolation (retry feedback에 score/verdict 미노출)** — *부분적 정당함, 위험 있음*. 외부 4개 도구 중 어느 것도 이 패턴을 채택하지 않음 — 정확히 말하면 *retry 메커니즘 자체가 약함* (promptfoo `--repeat`은 새 호출, 피드백 안 줌). 이론적으로 prompt-leak 방지는 좋지만, **"모델이 무엇을 잘못했는지" 신호 중 가장 강한 것이 score**임. issues+suggestions만 주는 것이 충분한 학습 신호인지 실험적 검증 필요. [SPECULATIVE: 차라리 score는 주되 *어떤 메트릭의* score인지 안 알려주는 절충도 가능]. → **사용자 검증 필요**.
- **GBNF 강제 (생성 시점)** — *정당하지만 lock-in 위험*. 외부 도구는 모두 post-hoc JSON 검증 (`is-json` assertion, `parse_json` filter). GBNF는 llama.cpp/vLLM-grammar에 의존 → 폐쇄 API 모델(Claude, GPT-4o) 사용 시 적용 불가 [VERIFIED, llama.cpp issue #20345에서 보듯 thinking mode와의 충돌도 존재]. HARNESS가 self-hosted only를 가정한다면 OK, 그러나 generator 후보 풀이 줄어듦. 또한 GBNF는 *형식*만 강제하지 *의미적 일관성*은 보장 못 함 — 여전히 LLM Judge가 필요.
- **Ship gate 95+** — *과도하게 엄격*. deepeval default 0.5, promptfoo도 명시적 threshold 미설정 시 자유. 95+는 (a) 메트릭 보정이 잘 된 경우만 의미 있음 — judge LLM은 일반적으로 0.7-0.9 구간에 답을 몰아주는 경향 [VERIFIED, G-Eval paper 토큰 확률 정규화 동기]. (b) DAG 같은 결정론적 메트릭이 아니면 95 통과는 노이즈. → **strict_mode=True인 binary 메트릭 다수 + threshold 사실상 0**으로 재설계 검토 가치.

**3. HARNESS 설계의 위험과 외부 도구가 다루는 방식**
- **Cross-model 비용** — 외부 도구는 "judge는 cheaper model로 충분, 핵심은 family 다름" (예: generator=GPT-4o-mini, judge=Claude-Haiku) 패턴을 권장 [VERIFIED, promptfoo docs `--grader openai:gpt-5-mini`]. HARNESS가 동급 모델끼리 cross verification한다면 비용 낭비.
- **Single judge → judge 자체 편향** — Wataoka et al. 2024는 ensemble judge (3+ 모델 평균)를 권장 [VERIFIED]. HARNESS가 단일 verifier라면 그 verifier의 편향이 곧 평가 표준. Layer 1만이라도 2-3 judge ensemble을 고려하면 좋음.
- **GBNF rigidity와 모델 다양성의 trade-off** — Layer 2 service에서 generator 모델을 교체할 때 모든 모델이 GBNF 호환이어야 함 → 모델 풀이 좁아짐. 백엔드를 llama.cpp / vLLM에 lock-in하는 결과.
- **AI Playtester의 평가 분리** — promptfoo redteam은 plugin × strategy로 *공격*과 *카테고리*를 분리. HARNESS가 Playtester를 어떻게 통합하는지 문서에서 명확하지 않다면 [SPECULATIVE], 이 직교 모델을 도입할 가치가 큼.

---

## 액션 아이템

### 1. ROADMAP 9.4 (Eval tool reference scope)에 대한 결정사항
- **외부 프레임워크 직접 의존성 추가하지 않음** — 사용자 정책과 정합. promptfoo / deepeval / ragas / lm-eval 어느 것도 import하지 않음.
- **단, lm-evaluation-harness만 별도 Tier (베이스 모델 capability check 용도)** — KoBEST, KMMLU, HAERAE 점수로 generator 후보 모델을 1차 필터링하는 용도로 *런타임 외부* 도구로 활용 가능. HARNESS와 무관한 model selection 단계.
- **참조 패턴 4개 명시적 차용**: deepeval `BaseMetric`, ragas `PydanticPrompt`/`_required_columns`, lm-eval `Filter pipeline`/`metadata.version`, promptfoo `weight×threshold×metric_tag` aggregation.

### 2. EvalRunner에 추가할 구체 코드 패턴
1. `BaseMetric` ABC를 단일 표준으로 채택 (`measure`, `a_measure`, `is_successful`, `score`, `reason`, `error`, `threshold`, `cost_usd`).
2. `JudgePrompt[Input, Output]` 제네릭 + Pydantic schema enforcement (judge 출력 파싱 안정화).
3. `FilterPipeline` 클래스 + GBNF fallback chain (Layer 2 robustness).
4. `EvalSpec.version` 필드 + 결과에 spec_version 동봉 (회귀 분석).
5. Metric tag별 micro-mean (composite score 외에 카테고리별 가시성 확보).
6. Token budget tracking (`cost_usd` 누적, Layer 1 ship gate에서 회귀 임계 설정).
7. Optional: ensemble judge 옵션 (Layer 1 only, 2-3 judge 평균 → self-preference 추가 완화).

### 3. Tier 0에서 즉시 적용 가능한 패턴
- `BaseMetric` 인터페이스 정의 + `KoreanNaturalnessMetric`, `PersonaConsistencyMetric`, `JsonSchemaMetric`, `AIBreakoutMetric` 4개 minimal 구현.
- `JudgePrompt` Pydantic 스키마로 judge 출력 강제 (구현은 `instructor` 같은 라이브러리 없이 자체 JSON schema 검증).
- `EvalSpec.version="0.1.0"` 도입 + 결과 JSON에 명시.
- Cross-model 강제: `assert generator.model_id != judge.model_id` 한 줄 (이미 있다면 unit test 추가).
- `--repeat` 옵션을 EvalRunner에 추가하여 Layer 1에서 분산을 *측정* (재시도와 별개).

---

## Caveats / 본 분석의 명시적 한계

1. **단일 LLM 응답 분석**: 본 보고서는 한 번의 분석 세션 결과이며, 4개 도구 각각의 소스 코드를 commit-by-commit으로 실측 검증한 것은 아닙니다. promptfoo, deepeval은 2025-2026년 활발히 업데이트되고 있어 **DAG, redteam strategy, ragas KG transformation 등 신기능은 추가 변경 가능성**이 있습니다 [VERIFIED, 다수 release notes 2025년 2월~10월]. 본 분석에서 [VERIFIED]로 태깅한 항목도 사용자가 핵심 결정을 내리기 전 공식 docs에서 한 번 더 교차 확인 권장.
2. **지식 컷오프 한계**: 현재 시점(2026-04-29) 기준이지만, 실제 마지막 학습 컷오프와 검색된 페이지의 게시일이 일치하지 않습니다. 특히 promptfoo는 2026년 3월 OpenAI에 인수된 상태 [VERIFIED, GitHub README]이며 향후 라이선스/방향성이 변할 가능성 있음 — 의존성 추가 결정 시 유의.
3. **HARNESS 문서 직접 미확인**: 본 분석은 사용자가 시스템 프롬프트로 요약 제공한 HARNESS 속성에 기반합니다. HARNESS_CORE.md, HARNESS_LAYER1_DEV.md 등의 실제 내용은 제가 읽지 못했으므로, "HARNESS에 X가 누락"이라는 주장은 *요약 수준에서*의 추정입니다 [SPECULATIVE]. 실제 코드/문서에 이미 존재할 수 있는 기능을 누락했다고 잘못 지적했을 가능성을 배제하지 마십시오.
4. **자기-강화 편향 회피의 한계**: 본 분석을 작성한 모델 자체가 HARNESS 문서를 작성한 모델과 동일하므로, 비판 섹션(D)에서도 미묘한 자기 정당화가 잔존할 수 있습니다. 특히 "Cross-Model verification은 정당함"이라는 결론은 외부 학술 근거와 정합하지만, *비용 대 효과*에 대한 결론은 여전히 HARNESS 우호적입니다. 비판 강도는 사용자가 직접 외부 reviewer (다른 모델 또는 인간 엔지니어)를 통해 한 번 더 검증 권장.
5. **Information isolation에 대한 실증 부재**: 외부 4개 도구 어느 것도 "score를 retry feedback에서 빼는" 패턴을 사용하지 않으므로, 이 설계 결정의 효과(prompt-leak 방지 vs. 학습 신호 손실)에 대한 비교 데이터가 본 분석에는 없습니다. 작은 ablation 실험(score 포함 retry vs. issues-only retry)을 Layer 1에서 한 번 돌려보는 것을 권장합니다.
6. **GBNF 호환성**: llama.cpp 한정 정보이며 vLLM, SGLang의 grammar 지원 상황은 별도 확인 필요. Claude/GPT-4o는 grammar 미지원 (function calling만 가능)이라는 점은 [VERIFIED]이나, 이것이 HARNESS 모델 풀 결정에 미치는 영향은 사용자가 판단해야 합니다.