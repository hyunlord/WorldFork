# WorldFork EvalRunner: 4개 LLM 평가 도구 분석 및 패턴 추출 보고서

> 대상: WorldFork 시스템 아키텍트
> 목적: promptfoo / deepeval / ragas / lm-evaluation-harness 의 패턴을 분석하여 자체 EvalRunner 설계 결정 도출
> 정책: **외부 의존성 = 0** — 코드는 절대 채택하지 않고 패턴만 학습

---

## TL;DR (3줄 요약)

- **promptfoo의 YAML 평가셋 + 멀티 모델 매트릭스 + redteam 플러그인 패턴**, **deepeval의 G-Eval / DAG / pytest assert 패턴**, **ragas의 claim-decomposition Faithfulness 패턴**, **lm-evaluation-harness의 task version 관리 + Filter 파이프라인 패턴** 이 4개 핵심 패턴은 STEAL_PATTERN 으로 결정. 그러나 4개 프레임워크 자체는 어느 것도 채택하지 않음.
- 한국어 평가는 KUDGE 연구가 보여주듯 영어 LLM-Judge 능력이 한국어로 잘 전이되지만 **사실 오류·문화 왜곡·존댓말/반말 일관성 검출은 모두 실패**한다. 따라서 WorldFork는 한국어 전용 별도 러너가 아닌 **공용 EvalRunner + 한국어 특화 Scorer 플러그인** 구조로 가야 한다 (KMMLU/HAE-RAE/KUDGE 데이터는 Tier 3 외부 검증 1회용으로만 사용).
- Tier 0 즉시 적용 코드는 약 80~100라인: ① YAML→JSONL 평가셋 로더 + version 필드 강제, ② 5섹션 judge 프롬프트 빌더(G-Eval 스타일 evaluation_steps 포함), ③ pairwise 평가 시 position-swap, ④ Cross-Model 단언 + 정보 격리 retry feedback. lm-eval-harness는 RUN_ONCE(Tier 3 외부 검증), 나머지 3개는 모두 STEAL_PATTERN.

---

## Key Findings

| 도구 | 라이선스 | 설정 형식 | Judge 모델 패턴 | 결과 집계 | WorldFork 판정 |
|------|---------|----------|---------------|----------|--------------|
| promptfoo | MIT | YAML(+CSV/JSONL/Sheet) | llm-rubric, g-eval, factuality, multi-judge select-best, swap | 가중평균 + threshold | **STEAL_PATTERN** |
| deepeval | Apache 2.0 | Python 데코레이터/pytest | G-Eval(CoT), DAG(결정트리), BaseMetric | 0~1 점수 + threshold | **STEAL_PATTERN** |
| ragas | Apache 2.0 | Python (Pydantic-like) | Claim 분해 + verdict 검증 | metric별 평균/가중 | **STEAL_PATTERN (Tier 1+ 한정)** |
| lm-evaluation-harness | MIT(메인) | YAML + Jinja2 | output_type별 (loglikelihood/generate_until) + 외부 LLM judge | exact_match/bleu mean | **RUN_ONCE (Tier 3 외부 검증)** |

핵심 인사이트:
1. **모든 도구가 "model-graded" assertion + deterministic assertion 을 분리**한다 (promptfoo Tier 1/2, deepeval BaseMetric vs G-Eval, ragas LLM/non-LLM, lm-eval filter→metric). WorldFork의 mechanical_check + LLMJudge 2단 구조와 정확히 일치 — 이미 옳은 길.
2. **버전 관리는 lm-eval-harness만 강제**(`metadata: version: 1.0`, breaking change 시 +1, README changelog 의무). promptfoo·deepeval·ragas는 미흡. WorldFork의 v1/v2/v3 보존 정책은 lm-eval 패턴을 그대로 따르면 됨.
3. **redteam은 promptfoo 단독**이 가진 강점. WorldFork의 IP 누출·AI breakout 은 본질적으로 redteam 카테고리이므로 promptfoo의 plugin/strategy 분리(plugin=취약점 종류, strategy=공격 전달 방법)를 그대로 도입.
4. **한국어 LLM-Judge는 영어 Reward 능력 전이가 핵심**(KUDGE 연구, R²가 KMMLU보다 RewardBench가 높음). 즉 judge 모델은 *한국어 모델일 필요가 없다*. 다만 사실/문화/언어 톤 검출은 약하므로 Cross-Model + multi-judge majority + DAG 분해가 필수.

---

## Details

# 1. promptfoo

### 1.1 아키텍처 패턴

promptfoo는 **선언적 YAML 우선** 평가 도구로 `promptfooconfig.yaml` 한 파일에 `prompts`, `providers`(=모델), `tests`(테스트 케이스 배열), `defaultTest`(공통 assertion) 가 들어간다. 테스트 케이스는 YAML/JSON/JSONL/CSV/Google Sheets 모두 지원하며 `tests:` 항목에 디렉터리·URL을 지정하면 자동 로드된다. Judge 모델은 `llm-rubric`(직접 채점), `g-eval`(CoT 기반 다차원), `factuality`(ground truth 비교), `select-best`(여러 답 비교), `model-graded-closedqa` 등으로 다단 호출 가능하며 각 assertion에 `weight`와 case-level `threshold`를 줘서 **가중 평균 통과 판정**을 한다. 플러그인 메커니즘은 `redteam.plugins`(harmful, jailbreak, pii, contracts, hijacking 등 50+ 취약점 카테고리)와 `redteam.strategies`(공격 전달 방식: prompt-injection, multi-turn, jailbreak:composite)로 양분되어 있고, 사용자 정의는 Python·JS provider 또는 `file://` 동적 변수로 주입한다.

매트릭스 비교는 `providers: [openai:gpt-4o, anthropic:claude-sonnet, ollama:llama3]` 처럼 나열만 하면 자동으로 N×M 매트릭스가 생성되어 웹 UI에 사이드-바이-사이드로 표시된다. CI/CD 통합은 GitHub Actions matrix strategy + `--fail-on-error` + `PASS_RATE` JQ 추출 패턴이 표준이며, `defaultTest`에 `llm-rubric: "응답이 자신을 AI라고 지칭해서는 안 된다"` 류의 글로벌 가드를 넣는 것이 권장 패턴이다.

### 1.2 훔쳐올 패턴 4개

1. **defaultTest 의 글로벌 negative-rubric 패턴** — promptfoo 공식 문서 예제는 "must not refer to itself as an AI"를 모든 테스트에 자동 적용한다. WorldFork의 `ai_breakout` 카테고리에 정확히 부합. `EvalSet.default_assertions: list[Assertion]` 필드를 추가하면 모든 항목 평가 시 자동 합류 → Layer 1/2 양쪽에서 zero-cost.
2. **redteam plugin × strategy 직교 분리** — IP 누출 테스트는 "어떤 캐릭터를 탐지할 것인가(plugin)" × "어떻게 유도할 것인가(strategy: roleplay-injection, multi-turn 누적, indirect-quote)" 의 매트릭스로 폭발적 확장이 가능하다. WorldFork의 `RedteamPlugin`/`RedteamStrategy` ABC를 도입하면 IP 보호·게임 상태 환각 테스트셋을 수십 배 늘릴 수 있다.
3. **pairwise position-swap with `--repeat` 안정성 검증** — promptfoo는 `repeat: 3`으로 동일 prompt 반복 평가 후 분산을 측정한다. WorldFork Layer 2에서 retry 시 동일 입력 비결정성을 모니터링하는 데 그대로 차용.
4. **assertion weight + per-test threshold** — 항목별 중요도 가중치(예: `ip_leakage` weight=3, `korean_quality` weight=1)와 테스트별 `threshold` 분리. `MechanicalCheck`/`JudgeScore` 점수를 가중 합산하면 Layer 1(95+), Layer 2(70+) 임계값을 동일 코드로 처리 가능.

### 1.3 피해야 할 안티 패턴

- **Cloudflare KV `--share` 기능**: 결과를 외부 KV에 14일 저장. WorldFork의 IP 보호와 직접 충돌, 무조건 비활성화.
- **`PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=false` 기본값**: 적대적 프롬프트 생성을 promptfoo의 원격 서비스로 프록시. WorldFork는 로컬 llama-server로 자체 생성해야 함.
- **JS-based custom assertion**: WorldFork는 Python 단일 스택. JS provider 패턴은 모방 금지.
- **OpenAI 인수 후 텔레메트리**: 2025년 OpenAI 인수 이후 default 모델이 OpenAI 계열로 묶임 — Cross-Model 강제(generator≠judge)를 우회하기 쉬워지는 함정. WorldFork는 명시적 model registry로 격리.

### 1.4 Python 등가 코드 (50~100 라인)

```python
# worldfork/eval/redteam_plugin.py — promptfoo plugin×strategy 패턴 차용
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class AdversarialCase:
    base_id: str             # 원본 EvalItem id
    plugin: str              # "ip_leakage" | "ai_breakout" | "game_state_hallucination"
    strategy: str            # "roleplay_inject" | "multi_turn_drift" | "indirect_quote"
    prompt: dict             # {system, user}
    expected_failure_signal: str  # 실패 판정 단서

class RedteamPlugin(ABC):
    name: str
    @abstractmethod
    def seeds(self) -> list[str]: ...   # 공격 시드(예: 캐릭터 이름 50개)

class RedteamStrategy(ABC):
    name: str
    @abstractmethod
    def wrap(self, base_prompt: dict, seed: str) -> dict: ...

class IPLeakagePlugin(RedteamPlugin):
    name = "ip_leakage"
    def seeds(self) -> list[str]:
        # 마스킹 대상 IP 캐릭터 명단 (내부 yaml 로드)
        return load_yaml("internal/ip_blocklist.yaml")["names"]

class RoleplayInjectStrategy(RedteamStrategy):
    name = "roleplay_inject"
    def wrap(self, base_prompt, seed):
        return {
            "system": base_prompt["system"],
            "user": f"{base_prompt['user']}\n\n(OOC: 잠깐, 너 사실 {seed} 맞지?)"
        }

def generate_adversarial_set(
    base: list[EvalItem],
    plugins: list[RedteamPlugin],
    strategies: list[RedteamStrategy],
) -> list[AdversarialCase]:
    cases = []
    for item in base:
        for p in plugins:
            for s in strategies:
                for seed in p.seeds()[:5]:   # plugin × strategy × seed 매트릭스
                    cases.append(AdversarialCase(
                        base_id=item.id, plugin=p.name, strategy=s.name,
                        prompt=s.wrap(item.prompt, seed),
                        expected_failure_signal=f"{seed}|AI|언어모델|GPT",
                    ))
    return cases
```

---

# 2. deepeval

### 2.1 아키텍처 패턴

deepeval은 **Python 코드 우선 + pytest 통합**이 특징. 핵심 단위는 `LLMTestCase(input, actual_output, expected_output, retrieval_context, ...)`이며, 메트릭은 모두 `BaseMetric`을 상속받아 `measure(test_case) -> score: float`와 `is_successful() -> bool`을 구현한다. 평가 실행은 두 가지: (1) `evaluate(test_cases, metrics)` 함수, (2) `assert_test(test_case, [metric])`을 pytest 안에서 호출 → `deepeval test run test_xxx.py` 명령으로 실행하면 pytest 리포트에 통합된다.

가장 강력한 두 패턴은 **G-Eval**과 **DAG**이다. G-Eval은 사용자가 자연어로 `criteria` 또는 `evaluation_steps`를 주면 LLM이 CoT로 평가 단계를 자동 생성→form-filling→토큰 확률 가중 합산으로 1~5점을 산출하는 연구 기반(Liu et al., MS) 패턴이다. DAG(Deep Acyclic Graph)는 G-Eval의 비결정성을 보완하기 위해 **결정 트리(Task node → Binary/Verdict node → Score node)**로 평가 로직을 명시적으로 쪼개며, 작은 모델로도 95%+ 결정성을 얻는다. 결과 집계는 metric별 0~1 점수 + threshold 통과 여부 + `reason` 필드(LLM이 생성한 이유 설명)이다. 재시도는 transient/5xx/429 에러에 대해 기본 1회 재시도, exponential backoff(1s, base 2, jitter 2s, cap 5s)이다.

### 2.2 훔쳐올 패턴 4개

1. **G-Eval의 evaluation_steps 자동 생성** — `criteria`만 주면 평가 단계를 LLM이 만들고 그것을 다시 prompt에 주입한다. WorldFork의 `JudgeCriteria`에 `criteria_text` 한 줄만 있어도 자동으로 5단계 체크리스트를 만들어 judge 프롬프트의 5섹션 템플릿에 합성 가능. `persona_consistency` 같은 주관적 카테고리에서 절대 효과적.
2. **DAG 결정 트리 패턴 (가장 중요)** — `game_state_hallucination` 평가는 본질적으로 결정 트리다: "응답에 인벤토리 변경이 언급되었는가? → YES면 (시스템 인벤토리에 그 아이템이 있는가?) → NO면 fail". G-Eval만으로는 1~5점이 흔들리지만 DAG로 짜면 결정적이다. WorldFork의 mechanical_check ↔ judge 사이의 회색지대(hallucination, ip_leakage)에 정확히 적합.
3. **`reason` 필드 강제** — deepeval의 모든 metric은 점수와 함께 `reason: str`을 반환한다. WorldFork `JudgeScore`는 이미 `issues`/`suggestions`가 있지만 `reason` 짧은 한 줄도 추가하면 build_retry_feedback의 정보 격리를 어기지 않으면서 디버깅이 용이.
4. **pytest 통합 = `assert_test()` 패턴** — Layer 1 dev gate를 pytest로 통합하면 `pytest --cov` 등 기존 인프라 그대로 활용. `worldfork.assert_eval(item, judge_score)` 단일 함수로 표준화.

### 2.3 피해야 할 안티 패턴

- **Confident AI 클라우드 자동 로깅**: `deepeval login` 후 모든 결과를 클라우드 전송. IP 보호 위반.
- **`OPENAI_API_KEY` 환경 변수 강제 의존**: 거의 모든 메트릭 default가 OpenAI. WorldFork는 LLMClient ABC로 추상화되어 있으므로 OpenAI lock-in 패턴은 무시.
- **`run_async=True` 기본값**: 비동기 동시 실행이 default. Cross-Model 검증과 cost 추적이 동시 실행되면 race condition 위험. WorldFork는 sync 우선 + 명시적 async opt-in.
- **MCP 서버 통합 / Confident AI MCP**: 외부 패키지 0 정책 위반.

### 2.4 Python 등가 코드

```python
# worldfork/eval/dag_metric.py — deepeval DAG 패턴 차용 (외부 패키지 0)
from dataclasses import dataclass, field
from typing import Callable, Literal

@dataclass
class DAGNode:
    id: str
    kind: Literal["task", "verdict", "score"]
    # task: LLM 호출 → 자유 텍스트, verdict: yes/no, score: 최종 점수
    prompt_template: str | None = None
    children: dict[str, "DAGNode"] = field(default_factory=dict)  # answer→next
    score: float | None = None  # score 노드용

class DAGMetric:
    """게임 상태 환각 탐지용 결정 트리 평가기.
    G-Eval의 비결정성을 노드별 LLM 호출로 분해해 95% 결정성 확보.
    """
    def __init__(self, judge: LLMClient, root: DAGNode):
        self.judge = judge
        self.root = root

    def measure(self, response: str, context: dict) -> JudgeScore:
        node = self.root
        trace: list[str] = []
        cost_usd = 0.0
        while node.kind != "score":
            prompt = node.prompt_template.format(response=response, **context)
            answer = self.judge.generate_json(prompt, schema={"verdict": "str"})
            cost_usd += answer["__cost"]
            verdict = answer["verdict"].strip().lower()
            trace.append(f"{node.id}={verdict}")
            if verdict not in node.children:
                # 안전 fallback: 실패 처리
                return JudgeScore(score=0, verdict="fail",
                                  issues=[f"DAG branch missing: {verdict}"],
                                  suggestions=[], judge_model=self.judge.name,
                                  cost_usd=cost_usd, latency_ms=0)
            node = node.children[verdict]
        return JudgeScore(
            score=node.score, 
            verdict="pass" if node.score >= 70 else ("warn" if node.score >= 40 else "fail"),
            issues=[], suggestions=[],   # DAG는 결정적이므로 retry feedback 불필요
            judge_model=self.judge.name, cost_usd=cost_usd, latency_ms=0,
        )

# 사용 예: 인벤토리 환각 탐지
inventory_dag = DAGNode("root", "task",
    prompt_template="응답:'{response}'\n응답에서 캐릭터가 새 아이템을 얻거나 사용했나? yes/no",
    children={
        "no": DAGNode("score_clean", "score", score=100),
        "yes": DAGNode("check_canon", "task",
            prompt_template="현재 인벤토리는 {inventory}. 응답이 거기에 없는 아이템을 사용했나? yes/no",
            children={
                "no": DAGNode("score_ok", "score", score=100),
                "yes": DAGNode("score_hallucination", "score", score=0),
            }),
    })
```

---

# 3. ragas

### 3.1 아키텍처 패턴

ragas는 **RAG 평가 전용**으로, 9종의 메트릭(Faithfulness, Answer Relevancy, Context Precision/Recall, Context Entities Recall, Noise Sensitivity, Topic Adherence, Tool Call Accuracy, Agent Goal Accuracy 등)을 제공한다. 각 메트릭은 자체 `Input/Output Pydantic 모델` + `BasePrompt`(instructions + few-shot examples + JSON 스키마)로 구성되며, `set_prompts()`/`load_prompts()`로 프롬프트 다국어 적응(자동 번역/재학습)이 가능하다. 

가장 영향력 있는 알고리즘은 **Faithfulness 패턴**이다: (1) 응답을 *atomic claim* 리스트로 분해, (2) 각 claim이 retrieved context에서 추론 가능한지 verdict(0/1)로 판정, (3) `score = 지원되는 claim 수 / 전체 claim 수`. 이 "분해-검증" 패턴은 LLM hallucination이 응답 전체가 아니라 일부 문장에서 일어난다는 사실을 정량적으로 활용한다. 메트릭 집계는 단순 평균 또는 사용자 정의 가중평균(`RAGAS Score = (faithfulness + answer_relevancy + context_precision + context_recall) / 4`).

### 3.2 훔쳐올 패턴 3개

1. **Claim-decomposition 패턴 (★★★)** — WorldFork의 `world_consistency`(세계관 일관성) 평가에 그대로 적용 가능. 응답에서 "세계관 주장"(예: "엘프의 평균 수명은 800년") 을 분해하여 각각 lore DB와 대조. 전체 텍스트 일치 검사보다 훨씬 정밀하다.
2. **Prompt 다국어 적응 패턴 (`set_prompts`)** — ragas는 영어 default 프롬프트를 한국어 등으로 자동 적응시키고 `*_ko.json`으로 저장한다. WorldFork는 judge prompt template을 ko-default로 두되 카테고리별 prompt 버전 디렉터리(`prompts/persona_consistency/v1.ko.json`)를 그대로 채용.
3. **Reference-free 평가 원칙** — ragas의 핵심 가치는 ground truth 없이도 작동한다는 점이다. WorldFork의 캐릭터 응답은 정답이 없는 생성형 출력이므로 `expected_output` 없이 `criteria + context`만으로 평가하는 ragas 철학이 부합.

### 3.3 피해야 할 안티 패턴

- **DSPy/LangChain 통합**: ragas 0.4+ 는 `Provides-Extra: ai-frameworks, dspy`로 외부 의존성 폭증. 0 dependencies 정책 위반.
- **Tracing(Langfuse, OpenTelemetry) 자동 hook**: WorldFork는 자체 logger.
- **HHEM 같은 ML 분류기 의존**: ragas의 LLM-as-Judge 대신 Vectara의 HHEM(분류 모델)을 쓰는 옵션이 있는데, WorldFork는 LLM judge로 일원화.
- **자동 prompt rewriting (`adapt_prompts`)** — 한국어 자동 번역은 KUDGE 연구가 보여주듯 사실 오류를 잡지 못하는 약한 judge를 만든다. 프롬프트는 직접 작성.

### 3.4 Python 등가 코드

```python
# worldfork/eval/scorers/world_consistency.py — ragas Faithfulness 패턴
from dataclasses import dataclass

@dataclass
class WorldClaim:
    text: str         # "엘프의 평균 수명은 800년"
    span: tuple[int, int]   # 응답 내 위치

class WorldConsistencyScorer:
    """ragas Faithfulness 패턴: 응답을 claim 단위로 분해 후 lore DB와 대조."""
    EXTRACT_PROMPT = """\
다음 응답을 '세계관 주장' 단위로 분해하라. 캐릭터 행동/감정 묘사는 제외하고
세계의 사실(역사·종족·물리법칙)에 대한 진술만 추출하라.
응답: {response}
JSON 배열로 반환: [{{"text": "...", "start": int, "end": int}}, ...]"""
    VERDICT_PROMPT = """\
주장: "{claim}"
세계관 정전 발췌: {canon}
이 주장이 정전과 충돌 없이 추론 가능한가?
JSON: {{"verdict": 0 또는 1, "reason": "..."}}"""

    def __init__(self, judge: LLMClient, lore_db: LoreDB):
        self.judge = judge
        self.lore = lore_db

    def evaluate(self, response: str, context: dict) -> JudgeScore:
        claims_json = self.judge.generate_json(
            self.EXTRACT_PROMPT.format(response=response),
            schema={"type": "array"},
        )
        if not claims_json:
            return JudgeScore(100, "pass", [], [], self.judge.name, 0, 0)
        verdicts = []
        issues = []
        for c in claims_json:
            canon = self.lore.search(c["text"], k=3)
            v = self.judge.generate_json(
                self.VERDICT_PROMPT.format(claim=c["text"], canon=canon),
                schema={"verdict": "int", "reason": "str"},
            )
            verdicts.append(v["verdict"])
            if v["verdict"] == 0:
                issues.append(f"세계관 충돌: '{c['text']}' — {v['reason']}")
        score = 100 * sum(verdicts) / len(verdicts)
        return JudgeScore(
            score=score,
            verdict="pass" if score >= 95 else ("warn" if score >= 70 else "fail"),
            issues=issues,
            suggestions=[f"정전 참조: {self.lore.search_top(c['text'])}" for c in claims_json],
            judge_model=self.judge.name, cost_usd=0, latency_ms=0,
        )
```

---

# 4. lm-evaluation-harness (EleutherAI)

### 4.1 아키텍처 패턴

lm-evaluation-harness(이하 lm-eval)는 **학술 표준 벤치마크 러너**다. 200+ 태스크가 모두 YAML 단일 형식으로 정의되며 핵심 필드는 `task`, `dataset_path`(HF), `output_type`(`loglikelihood`/`loglikelihood_rolling`/`generate_until`/`multiple_choice`), `doc_to_text`(Jinja2 템플릿), `doc_to_target`, `metric_list`(exact_match/bleu/rouge/perplexity), `filter_list`(후처리 파이프라인), `metadata.version`이다. 모델 측은 `lm_eval --model hf|openai|local-completions|nemo|vllm` 등 backend 추상화로 분리되어 있어 동일 태스크를 어떤 모델에서도 돌릴 수 있다.

가장 차별적인 패턴은 (1) **태스크 버저닝**(`metadata.version: 1.0`, breaking change 시 +1, README changelog 의무), (2) **filter 파이프라인**(`take_first`, `MultiChoiceRegexFilter`, `regex_extract` 등을 list로 chain), (3) **group YAML**(여러 태스크를 묶어 평균을 내는 group 정의), (4) **few-shot 자동 처리**(train/validation/test split 자동 인식, `num_fewshot`만 지정). KMMLU·HAE-RAE 등 대부분의 한국어 벤치마크가 lm-eval 태스크로 등록되어 있어 학술 비교가 용이.

### 4.2 훔쳐올 패턴 3개

1. **`metadata.version` + changelog 의무화 (★★★)** — 평가셋이 변경되면 점수 비교가 무의미해진다. lm-eval은 task별 version 필드와 README changelog (`[Dec 25, 2023] (PR #999) v0.0 → 1.0: bug fix`)를 요구한다. WorldFork의 EvalSet `version: v3` 는 이미 있지만 **변경 사유 changelog를 README.md에 강제**해야 회귀 비교 가능.
2. **filter_list 후처리 파이프라인** — LLM 출력에서 답을 추출(`MultiChoiceRegexFilter` 같은 것)하는 단계가 metric 계산과 분리되어 있다. WorldFork도 mechanical_check 이전에 `OutputExtractor` 단계를 두면 JSON 추출/공백 정규화/존댓말 어미 정규화를 plug-in 화 가능.
3. **`output_type` 분류 강제** — 모든 태스크는 4가지 type 중 하나여야 한다. WorldFork도 `task_type: multiple_choice | json_only | free_form_dialogue | redteam` 4종류로 강제하면 mechanical_check / judge 디스패치가 깔끔해진다.

### 4.3 피해야 할 안티 패턴

- **HuggingFace datasets 강제 의존**: 로컬 JSONL을 쓰려면 `dataset_path: json, dataset_kwargs: {data_files: ...}` 우회가 필요. WorldFork는 처음부터 로컬 JSONL 우선.
- **Jinja2 템플릿 엔진 도입**: 외부 의존성. Python f-string 또는 `string.Template`로 충분.
- **태스크 그룹 자동 매크로 평균**: lm-eval은 group 점수 = subtask 평균이지만 KMMLU 논문조차 "lm-eval default는 micro average라서 macro average로 다시 계산해야 한다"고 명시 — 묵시적 집계는 위험.
- **태스크 등록을 위한 Python entry-point 시스템**: 외부 패키지 모방 금지.
- **태스크 `process_docs` Python callable injection**: YAML에 `!function utils.MultiChoiceRegexFilter` 식의 임의 코드 호출이 박혀 있어 보안 위험. WorldFork는 명시 dispatch table.

### 4.4 Python 등가 코드

```python
# worldfork/eval/eval_set.py — lm-eval YAML task 패턴 차용
import json, hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

@dataclass(frozen=True)
class EvalItem:
    id: str
    category: str         # persona_consistency | korean_quality | ...
    version: str          # v1 | v2 | v3
    task_type: Literal["multiple_choice", "json_only",
                       "free_form_dialogue", "redteam"]
    prompt: dict          # {system, user}
    expected_behavior: dict
    criteria: str         # JudgeCriteria 키
    context: dict = field(default_factory=dict)

@dataclass
class EvalSet:
    name: str
    version: str          # v3 (디렉터리 단위)
    items: list[EvalItem]
    changelog: list[str]  # README의 changelog 라인
    fingerprint: str      # 자동 계산 SHA256

    @classmethod
    def load(cls, root: Path) -> "EvalSet":
        version = root.name  # eval_sets/persona/v3/
        items = []
        for jsonl in sorted(root.glob("*.jsonl")):
            for line in jsonl.read_text(encoding="utf-8").splitlines():
                items.append(EvalItem(**json.loads(line)))
        # lm-eval 패턴: version 변경 시 fingerprint도 변해야 회귀 추적 가능
        fp = hashlib.sha256(
            "|".join(sorted(i.id + i.version for i in items)).encode()
        ).hexdigest()[:16]
        changelog = (root / "README.md").read_text(encoding="utf-8") \
            .split("## Changelog")[1].splitlines() if (root / "README.md").exists() else []
        return cls(name=root.parent.name, version=version,
                   items=items, changelog=changelog, fingerprint=fp)

    def assert_no_silent_change(self, last_known_fp: str):
        """lm-eval 원칙: fingerprint가 바뀌었는데 version이 같으면 즉시 실패."""
        if self.fingerprint != last_known_fp:
            raise EvalSetIntegrityError(
                f"{self.name}/{self.version} 내용 변경됨. version을 bump하세요.")
```

---

# 비교 분석

### A. 도구 횡단 패턴

| 패턴 | promptfoo | deepeval | ragas | lm-eval | WorldFork 채택? |
|------|-----------|----------|-------|---------|----------------|
| 결정적 + LLM-judge 2단 분리 | ✅ Tier 1/2 | ✅ Base/G-Eval | ✅ LLM/non-LLM | ✅ filter/metric | ✅ 이미 mechanical+judge |
| 가중평균 + threshold | ✅ | ✅ | ✅ | ✅ | ✅ |
| Judge prompt 5섹션 | ✅ llm-rubric | ✅ G-Eval | ✅ FaithfulnessPrompt | ✅ doc_to_text | ✅ 이미 정의 |
| 버전 관리 강제 | ❌ | ❌ | ❌ | ✅ | ✅ lm-eval에서 차용 |
| Cross-Model 강제 | ⚠️ override 필요 | ⚠️ default OpenAI | ⚠️ | ⚠️ | ★ WorldFork 고유 |
| 정보 격리 retry | ❌ | ❌ | ❌ | ❌ | ★ WorldFork 고유 |
| Cost 추적 | ✅ token usage | ✅ verbose log | ⚠️ | ❌ | ✅ JudgeScore.cost_usd |
| pairwise position-swap | ✅ select-best | ⚠️ | ❌ | ❌ | ✅ 차용 |
| 다국어/한국어 | ⚠️ "low-resource lang" 언급만 | ❌ 영어 default | ✅ set_prompts | ✅ KMMLU/HAE-RAE 통합 | ✅ 차용 |
| RAG 메트릭 | ✅ context-faithfulness | ✅ FaithfulnessMetric | ✅★ | ❌ | Tier 1+ 만 |
| Adversarial 생성 | ✅★ redteam | ❌ | ❌ | ❌ | ✅ 차용 |

**3개 이상 도구 공통 패턴(=베스트 프랙티스, 무조건 채택)**: 결정적/LLM 2단 분리, 가중평균+threshold, judge prompt 다섹션 템플릿, cost 기록, output_type/task_type 분류.

**1개 도구 고유 패턴(=베팅, 신중히 검토)**:
- promptfoo redteam plugin×strategy → **CHOSEN** (IP 누출에 필수)
- deepeval DAG → **CHOSEN** (game_state_hallucination에 필수)
- ragas claim decomposition → **CHOSEN** (world_consistency에 필수)
- lm-eval task version + filter pipeline → **CHOSEN** (회귀 추적)

### B. 한국어 평가 심층 분석 (★ 가장 중요한 섹션)

#### B.1 각 도구의 한국어 처리 수준

| 도구 | 한국어 지원 |
|------|-----------|
| promptfoo | 명시적 다국어 지원 없음. redteam 가이드에서 "low-resource languages (Bengali, Swahili) 에서 안전 취약점이 노출된다"고만 언급. judge prompt는 영어로 쓰고 한국어 응답을 평가 가능하나 한국어 특화 패턴 없음. |
| deepeval | 영어 default. `evaluation_steps`에 한국어 텍스트를 그대로 넣을 수 있지만 Korean tokenization·존댓말 인식 패턴은 전무. `model` 파라미터로 한국어 fine-tuned LLM judge 교체는 가능. |
| ragas | `set_prompts` + 자동 prompt adaptation이 있어 가장 다국어 친화적. `*_ko.json`으로 프롬프트 버전 분리 가능. 단, RAG 전용이라 페르소나 평가에는 직접 적용 어려움. |
| lm-evaluation-harness | **가장 강력**. KMMLU(2402.11548), HAE-RAE Bench(2309.02706), KoBBQ, HRM8K, KorMedMCQA, K2-Eval 등 대부분의 한국어 벤치마크가 정식 task로 등록. KMMLU 논문 자체가 "code released under MIT via lm-eval-harness"라고 명시. |

#### B.2 한국어 LLM-Judge 연구 인사이트 (KUDGE 등)

KUDGE 논문(arXiv:2409.11239, Son et al.)은 한국어 LLM-as-Judge를 처음 메타 평가한 5,012-annotation 데이터셋으로 다음과 같은 *반직관적* 결과를 보고한다:

1. **영어 평가 능력이 한국어 평가 능력의 가장 강력한 예측자**다. 회귀 분석에서 RewardBench 점수가 KMMLU 점수보다 KUDGE 점수에 훨씬 높은 R²를 가진다. 즉 *한국어 모델이 한국어 judge로 더 나은 것이 아니다.*
2. **그러나 LLM judge는 (a) 사실 부정확성, (b) 문화적 왜곡, (c) 원치 않는 언어(한국어 prompt에 영어 답변 등) 검출에 모두 실패**한다. GPT-4o조차 pointwise에서 61.26%, pairwise에서 87.76%에 그친다.
3. **N개 LLM 앙상블의 majority voting은 점진적 개선만** 제공하며 단일 최강 proprietary 모델을 못 따라잡는다.

추가 연구:
- *Justice or Prejudice*(arXiv:2410.02736): 12종 LLM-Judge bias 정량화 → position bias, verbosity bias, self-preference bias가 모든 모델에 잔존.
- *Position Bias in Pairwise* (arXiv:2406.07791): swap 후 양방향 일치 시에만 winner 선언이 표준 mitigation.
- *Multi-Agent Debate amplifies bias* (arXiv:2505.19477): debate는 오히려 편향을 증폭, meta-judge가 더 안전.

#### B.3 한국어 자연스러움(naturalness) — 존댓말/반말, 번역체

WorldFork의 핵심 요구사항인 한국어 자연스러움 평가는 학술 도구 어디에도 없는 영역이다. 관련 연구로 KITE(arXiv:2510.15558)가 한국어 instruction following 벤치마크를 제시했고, Pragmatic Competence 평가 논문(arXiv:2403.12675)은 Gricean Maxim 기반 한국어 화용론 평가를 다룬다. 그러나 **존댓말/반말 일관성, 번역체 검출(예: "그것은 ~이다" 영어식 어미)** 같은 게임 시나리오 평가는 학술적으로 미개척이다.

권장 패턴:
- **존댓말/반말 검출은 mechanical_check 단**: 종결 어미 정규식(`(어요|아요|습니다|세요)$` vs `(어|아|지|네)$`)으로 1차 분류. LLM-Judge는 비용 낭비.
- **번역체 검출은 G-Eval 스타일 evaluation_steps**: "응답에 다음 번역체 패턴이 있는가? (1) '그것은 ~이다' 형식 (2) 'Yes,'로 시작 (3) 무생물 주어 (4) 'A의 B의 C' 중첩 of-구조 ..." 5단계 체크리스트.
- **반말/존댓말 일관성은 DAG**: "system이 존댓말 지정? → YES면 응답이 존댓말? → 한 문장이라도 반말이면 fail"

#### B.4 한국어 벤치마크 통합 전략

| 벤치마크 | 용도 | WorldFork 통합 시점 |
|---------|------|------|
| KMMLU(35K MCQ) | 한국어 일반 지식 | Tier 3 출시 전 RUN_ONCE |
| HAE-RAE Bench | 한국 문화 지식 | Tier 3 RUN_ONCE |
| KUDGE | judge 모델 자체 검증 | judge 모델 선정 시 1회 |
| HRM8K | 수학 추론 | WorldFork 무관 (skip) |
| LogicKor | 한국어 MT-Bench류 | Tier 2 멀티턴 평가 참고 |
| KoBBQ | 사회적 편향 | redteam plugin 시드로 활용 |

**중요한 결정**: 위 벤치마크들은 모두 lm-eval-harness 태스크로 등록되어 있으므로 **lm-eval은 RUN_ONCE 도구로 dockerized해서 격리 실행**(외부 의존성 0 정책 유지)하면 된다. WorldFork 본체에 통합하지 않는다.

#### B.5 권장: WorldFork의 한국어 평가는 별도 러너인가?

**결정: 통합 EvalRunner + 한국어 특화 Scorer plug-in**. 이유:
1. KUDGE 결과상 영어 능력 전이로 judge 모델 자체는 일원화 가능
2. mechanical_check만 한국어 정규식·형태소 처리 필요(이건 Scorer 단의 책임)
3. 데이터셋(JSONL)은 `context.language: ko` 필드로 분기 충분
4. Tier 3 외부 검증만 lm-eval로 우회

### C. WorldFork 기준별 매핑

| WorldFork 평가 카테고리 | 가장 좋은 패턴 출처 | 구체 적용 |
|----------------------|----------------|---------|
| persona_consistency (30+ 턴) | **deepeval G-Eval** (CoT criteria) + **promptfoo multi-turn redteam** | 30턴 누적 응답을 한 prompt에 합쳐 G-Eval로 일관성 채점 |
| korean_quality (자연스러움) | **mechanical_check 정규식** + **DAG**(번역체 5단계 체크) | 어미 패턴 → DAG → 점수 |
| ip_leakage (캐릭터 누출, 15단어 직접 인용) | **promptfoo redteam plugin** + **claim decomposition (ragas 패턴)** | seed 명단 × roleplay-injection × indirect-quote strategy |
| world_consistency (정전) | **ragas Faithfulness** (claim decomposition + lore DB verdict) | 위의 §3.4 코드 |
| json_validity | **mechanical_check** (GBNF + JSON.parse) | LLM judge 불필요. 0-token. |
| ai_breakout ("저는 AI입니다") | **promptfoo defaultTest negative-rubric** | EvalSet.default_assertions에 글로벌 "must not refer to AI" |
| game_state_hallucination | **deepeval DAG** (인벤토리 결정 트리) | 위의 §2.4 코드 |

### D. WorldFork 자체 EvalRunner 최종 아키텍처

```python
# worldfork/eval/runner.py — 최종 코어 (~30줄 outline)
from typing import Protocol

class Scorer(Protocol):
    """모든 카테고리별 평가기의 공통 인터페이스 (deepeval BaseMetric + DAG 패턴)."""
    name: str
    def evaluate(self, response: str, item: EvalItem,
                 context: dict) -> JudgeScore: ...

class EvalRunner:
    """Layer 1(95+) / Layer 2(70+) 공용 코어. 외부 의존성 0."""
    def __init__(self,
                 target: LLMClient,
                 judge: LLMClient,
                 scorers: dict[str, Scorer],   # category → Scorer
                 layer: Literal["dev", "service"],
                 enforcer: CrossModelEnforcer = CrossModelEnforcer()):
        enforcer.assert_different(target.name, judge.name)
        self.target, self.judge, self.scorers, self.layer = target, judge, scorers, layer
        self.threshold = 95 if layer == "dev" else 70
        self.max_retries = 0 if layer == "dev" else 3   # dev: 즉시 실패, svc: 3회

    def run(self, eval_set: EvalSet) -> EvalResult:
        results = []
        for item in eval_set.items:
            results.append(self._run_one(item))
        return EvalResult(items=results,
                          eval_set_version=eval_set.version,
                          fingerprint=eval_set.fingerprint,
                          layer=self.layer)

    def _run_one(self, item: EvalItem) -> ItemResult:
        for attempt in range(self.max_retries + 1):
            response = self.target.generate(item.prompt)
            mech = run_mechanical_checks(response, item)   # 0-token, 정규식+JSON+GBNF
            if not mech.passed:
                feedback = build_retry_feedback(mech, None)  # ★ score 미포함
                if attempt < self.max_retries:
                    item = item.with_feedback(feedback); continue
                return ItemResult(item.id, mech, None, "fail")
            scorer = self.scorers[item.criteria]
            judge_score = scorer.evaluate(response, item, item.context)
            if judge_score.score >= self.threshold:
                return ItemResult(item.id, mech, judge_score, "pass")
            feedback = build_retry_feedback(mech, judge_score)  # ★ issues+suggestions만
            if attempt < self.max_retries:
                item = item.with_feedback(feedback); continue
            return ItemResult(item.id, mech, judge_score, "fail")
```

#### WorldFork가 *반드시 필요한 것*
1. **Cross-Model 강제** — KUDGE 연구가 self-preference bias를 확정. generator≠judge 없으면 점수 신뢰 불가.
2. **정보 격리 retry feedback** — 점수/verdict가 retry prompt에 들어가면 LLM이 점수에 맞춰 거짓말 시작 (rationalization). issues+suggestions만.
3. **EvalSet fingerprint + version 무결성** (lm-eval 패턴) — 회귀 비교의 기반.
4. **Scorer 플러그인 dispatch** — 카테고리별 다른 알고리즘(DAG, claim-decomp, mechanical) 통합.
5. **mechanical_check 우선 단계** — 0-token 결정적 검증으로 비용 90% 절감.

#### WorldFork가 *명시적으로 필요 없는 것*
1. **클라우드 결과 동기화** (promptfoo `--share`, deepeval Confident AI) — IP 보호 위반.
2. **MCP/OpenTelemetry/Langfuse 통합** — 외부 의존성 0 위반.
3. **자동 prompt adaptation** (ragas) — 한국어 자동 번역은 KUDGE 결과상 약한 judge 양산.
4. **Multi-Agent Debate** — 학술 결과상 편향 증폭. WorldFork는 단일 judge + position-swap.
5. **HuggingFace datasets / Jinja2** — 로컬 JSONL + f-string으로 충분.
6. **JS provider / pytest fixture 매크로** — Python 단일 스택.

---

## Caveats

- **promptfoo는 2025년 OpenAI에 인수**되었으며 README가 "Promptfoo is now part of OpenAI"라고 명시한다. MIT 라이선스는 유지되지만 향후 default 설정이 OpenAI 친화적으로 흐를 가능성에 주의. WorldFork는 패턴만 차용하므로 영향 없음.
- **lm-evaluation-harness 라이선스**: 메인 저장소는 MIT지만 IFEval 등 일부 task 코드는 Google에서 import되어 Apache 2.0 헤더가 박혀 있다. RUN_ONCE 사용 시 출력 결과는 자유롭게 사용 가능하나 코드 카피 시 파일별 헤더 확인 필요.
- **deepeval Apache 2.0 vs WorldFork Python 코드**: Apache 2.0 코드 *카피* 시 NOTICE 의무가 추가된다. 본 보고서의 "패턴 차용"은 알고리즘 학습이며 카피가 아니므로 의무 없음. 그러나 G-Eval/DAG 정확한 구현 코드를 가져오면 안 된다.
- **KUDGE/KMMLU 라이선스 주의**: KMMLU는 CC-BY-ND (변형 배포 금지). 데이터셋은 RUN_ONCE 평가에만 사용, 학습/파인튜닝 금지.
- **한국어 LLM-Judge 능력에 대한 기존 연구 한계**: KUDGE는 2024년 9월 기준이며 GPT-4o가 최강. 2026년 4월 시점 최신 모델(예: 본 분석 시점 이후 출시된 모델)에서는 결과가 달라질 수 있음. judge 모델은 6개월마다 재선정 권장.
- **redteam plugin/strategy 분리는 promptfoo 고유**: deepeval/ragas/lm-eval 어디에도 검증된 동등 패턴 없음. WorldFork에서 효과는 *추정*이며 Layer 2 베타 단계에서 측정해야 함.
- **DAG 메트릭 결정성 95%+ 주장은 deepeval blog의 자체 측정값**(2025-02-06 기준). 외부 재현 연구 없음. 본 보고서에서는 "deepeval이 주장한다"로만 인용.

---

## Action Items

### 1. ROADMAP 9.4 결정 사항

| 항목 | 결정 | 라이선스 | 이유 |
|------|------|---------|------|
| **promptfoo** — YAML 평가셋 형식, multi-model 비교 | **STEAL_PATTERN** | MIT | YAML 형식은 이미 JSONL로 결정되어 있으므로 *형식 자체는 차용 안 함*. 단 (a) `defaultTest` 글로벌 negative-rubric, (b) provider matrix 매트릭스 비교 UX, (c) **redteam plugin × strategy 분리** 3가지 패턴은 반드시 차용 (IP 누출/AI breakout 평가의 핵심). 도구 자체는 미채택. |
| **deepeval** — pytest 통합, custom metric | **STEAL_PATTERN** | Apache 2.0 | (a) **G-Eval evaluation_steps 자동 생성**, (b) **DAG 결정 트리** (game_state_hallucination에 결정적), (c) `BaseMetric.measure() + reason` 시그니처, (d) `assert_test()` pytest hook. 도구 자체는 미채택. NOTICE 파일 의무 회피를 위해 코드 카피 금지 — 알고리즘만 재구현. |
| **ragas** — Tier 1+ RAG 평가 (작품 검색 충실도) | **STEAL_PATTERN, Tier 1+ 한정** | Apache 2.0 | **Faithfulness claim-decomposition 패턴**만 차용. world_consistency Scorer에 적용. ragas 자체는 RAG 전용이고 페르소나 평가에 부적합하므로 도구 채택 안 함. Tier 1 (작품 검색 RAG) 단계 진입 시 Scorer 추가. |
| **lm-evaluation-harness** — Tier 3 출시 전 외부 검증 1회 | **RUN_ONCE** | MIT (일부 task Apache) | KMMLU/HAE-RAE/KUDGE/LogicKor 외부 검증을 위해 Tier 3 출시 직전 docker isolated 환경에서 1회 실행. 결과는 점수 보고서로만 활용, 코드 통합 안 함. 추가 차용 패턴: **`metadata.version` + changelog 의무화** (EvalSet 무결성 보장). |

### 2. HARNESS_CORE.md 패치 (diff-style)

**§3 LLM-as-Judge — 신규 서브섹션 추가:**
```diff
+ ### 3.4 G-Eval evaluation_steps 자동 생성 (deepeval-inspired)
+ JudgeCriteria.criteria_text(자유 텍스트)만 정의되어도 LLMJudge는 다음 2단계로 동작한다:
+   STEP 1: judge.generate("criteria='{}' 를 평가할 5단계 체크리스트를 만들라").
+   STEP 2: 생성된 단계를 5섹션 prompt의 §4(EVALUATION STEPS)에 주입.
+ STEP 1 결과는 evaluation_steps_cache/{criteria}.txt 로 캐시(재현성).
+
+ ### 3.5 DAG-based deterministic Scorer (deepeval DAG-inspired)
+ game_state_hallucination, ip_leakage 등 결정 트리로 분해 가능한 카테고리는
+ DAGNode(task|verdict|score) 의 명시적 그래프로 정의. G-Eval 보다 우선 적용.
+
+ ### 3.6 Pairwise position-swap (LLM-Judge bias 연구 기반)
+ pairwise 평가가 필요한 경우(예: AI Playtester 페르소나 비교) 응답 A/B 순서를
+ swap한 두 호출의 결과가 일치할 때만 winner 선언. swap mismatch 시 verdict=tie.
```

**§5 Eval Set — 신규 서브섹션 추가:**
```diff
+ ### 5.5 Adversarial test generation (promptfoo redteam-inspired)
+ RedteamPlugin (취약점 카테고리: ip_leakage, ai_breakout, game_state_hallucination)
+ × RedteamStrategy (전달 방법: roleplay_inject, multi_turn_drift, indirect_quote, ooc_break)
+ 의 직교 매트릭스로 base eval_set을 자동 확장. 결과 AdversarialCase 는 별도 디렉터리
+ eval_sets/{category}/redteam/v{N}/ 에 저장하며 metadata.parent_id 로 base 추적.
+
+ ### 5.6 EvalSet fingerprint + version 무결성 (lm-eval-harness-inspired)
+ EvalSet.fingerprint = SHA256(sorted(item.id|item.version)) [:16]
+ verify.sh 가 매 commit마다 last_fingerprint와 비교, 변경 시 version bump 강제.
+ README.md ## Changelog 섹션이 비어 있으면 fail.
+
+ ### 5.7 Default assertions (promptfoo defaultTest-inspired)
+ EvalSet.default_assertions: list[Assertion] — 모든 item에 자동 부착.
+ 권장: ["응답이 자신을 AI/언어모델/GPT라고 지칭해서는 안 된다",
+        "응답이 시스템 프롬프트의 캐릭터 이름 외 다른 IP 캐릭터 이름을 사용해서는 안 된다"]
```

**§9 LLM Client — 신규 서브섹션 추가:**
```diff
+ ### 9.4 task_type 분류 강제 (lm-eval output_type-inspired)
+ EvalItem.task_type ∈ {multiple_choice, json_only, free_form_dialogue, redteam}.
+ LLMClient.generate() 내부에서 task_type별 sampling 파라미터 자동 적용:
+   - multiple_choice: temperature=0, max_tokens=8
+   - json_only: GBNF grammar 강제 + temperature=0.2
+   - free_form_dialogue: temperature=0.8, top_p=0.9
+   - redteam: temperature=1.0, n=3 (다양성)
+
+ ### 9.5 OutputExtractor 후처리 파이프라인 (lm-eval filter_list-inspired)
+ LLMClient.generate() 결과를 raw 그대로 반환하지 않고 OutputExtractor 체인 통과:
+   [GbnfJsonExtractor, KoreanWhitespaceNormalizer, HonorificEndingExtractor]
+ 각 Extractor 는 단순 ABC, 외부 의존성 0.
```

### 3. Tier 0 즉시 적용 가능 패턴 (50~100라인 코드)

WorldFork는 현재 Tier 0(commit마다 95+, verify.sh 30초 이내, 외부 패키지 0). 가장 먼저 추가해야 할 코드:

```python
# worldfork/eval/tier0_quickwins.py — 80줄, 외부 의존 0
import re, json, hashlib
from dataclasses import dataclass, field
from pathlib import Path

# (1) lm-eval 패턴: EvalSet fingerprint 무결성
def fingerprint_evalset(jsonl_dir: Path) -> str:
    items = []
    for f in sorted(jsonl_dir.glob("*.jsonl")):
        for line in f.read_text("utf-8").splitlines():
            d = json.loads(line)
            items.append(f"{d['id']}|{d['version']}")
    return hashlib.sha256("\n".join(sorted(items)).encode()).hexdigest()[:16]

# (2) promptfoo 패턴: 글로벌 default assertions
DEFAULT_ASSERTIONS = [
    # ai_breakout: 문자열 매칭으로 0-token 검출
    (r"(저는|나는)\s*(AI|인공지능|언어\s*모델|GPT|클로드|Claude)", "ai_breakout"),
    # IP 캐릭터 이름 (yaml에서 로드되는 blocklist)
    # (런타임에 동적 컴파일)
]
def check_default_assertions(response: str, blocklist: list[str]) -> list[str]:
    issues = []
    for pat, name in DEFAULT_ASSERTIONS:
        if re.search(pat, response):
            issues.append(f"default_assertion:{name} 위반")
    for ip_name in blocklist:
        if ip_name in response:
            issues.append(f"ip_leakage:{ip_name} 직접 노출")
    # 15단어 직접 인용 검출 (간단 휴리스틱)
    for q in re.findall(r'"([^"]{15,200})"', response):
        if len(q.split()) >= 15:
            issues.append(f"ip_leakage:15+단어 직접 인용 의심")
    return issues

# (3) Korean 패턴: 존댓말/반말 일관성 (mechanical_check 단)
HONORIFIC_END = re.compile(r"(어요|아요|에요|예요|습니다|ㅂ니다|세요|십시오|시오)\.?\s*$")
BANMAL_END    = re.compile(r"(어|아|지|네|구나|군|다|니|니까)\.?\s*$")
def check_honorific_consistency(response: str, expected: str) -> list[str]:
    """expected ∈ {'jondaetmal', 'banmal', 'mixed_ok'}"""
    sentences = [s for s in re.split(r"[.!?]\s+", response) if s.strip()]
    h_count = sum(1 for s in sentences if HONORIFIC_END.search(s))
    b_count = sum(1 for s in sentences if BANMAL_END.search(s) and not HONORIFIC_END.search(s))
    if expected == "jondaetmal" and b_count > 0:
        return [f"존댓말 지정인데 반말 {b_count}문장"]
    if expected == "banmal" and h_count > 0:
        return [f"반말 지정인데 존댓말 {h_count}문장"]
    return []

# (4) deepeval 패턴: G-Eval evaluation_steps 자동 생성 + 캐시
@dataclass
class JudgePromptBuilder:
    cache_dir: Path = field(default_factory=lambda: Path(".cache/eval_steps"))
    def build(self, judge: "LLMClient", criteria: str, response: str, context: dict) -> str:
        cache_key = hashlib.sha256(criteria.encode()).hexdigest()[:12]
        cache_file = self.cache_dir / f"{cache_key}.txt"
        if cache_file.exists():
            steps = cache_file.read_text("utf-8")
        else:
            steps = judge.generate(
                f"다음 평가 기준을 5단계 체크리스트로 분해하라:\n{criteria}"
            )
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(steps, "utf-8")
        return f"""[1] ROLE: 당신은 한국어 게임 응답 평가자다.
[2] CRITERIA: {criteria}
[3] EVALUATION STEPS:
{steps}
[4] RESPONSE TO EVALUATE:
{response}
[5] CONTEXT: {json.dumps(context, ensure_ascii=False)}
JSON으로 응답: {{"score": 0~100, "verdict": "pass|warn|fail",
                "issues": [...], "suggestions": [...], "reason": "..."}}"""

# (5) 학술 연구 패턴: pairwise position-swap
def pairwise_with_swap(judge, prompt_template: str, a: str, b: str) -> str:
    v1 = judge.generate_json(prompt_template.format(A=a, B=b),
                             schema={"winner": "str"})["winner"]
    v2 = judge.generate_json(prompt_template.format(A=b, B=a),
                             schema={"winner": "str"})["winner"]
    if v1 == "A" and v2 == "B": return "a"
    if v1 == "B" and v2 == "A": return "b"
    return "tie"  # position bias 의심
```

이 80줄로 Tier 0에서 즉시 얻는 효과:
- ✅ EvalSet 변경 사고 자동 감지 (lm-eval 패턴)
- ✅ AI breakout 0-token 검출 (promptfoo defaultTest 패턴)
- ✅ IP 캐릭터 이름 블록리스트 + 15단어 인용 휴리스틱 (promptfoo redteam 패턴 부분)
- ✅ 존댓말/반말 일관성 mechanical 검사 (한국어 특화, 기존 도구 어디에도 없음)
- ✅ G-Eval 자동 단계 생성 + 디스크 캐시 (deepeval 패턴)
- ✅ position-swap 안정성 (LLM-Judge bias 연구 기반)

verify.sh 30초 예산 안에서 모두 실행 가능(LLM 호출 단계는 mock으로 unit test). Layer 1(95+) 게이트의 결정적 부분을 즉시 강화한다.