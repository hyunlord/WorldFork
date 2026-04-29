# HARNESS_CORE — 공유 검증 코어

> WorldFork의 Layer 1(개발 하네스)과 Layer 2(서비스 하네스)가 **공유하는** 검증 인프라.
> 두 Layer 모두 이 문서의 패턴을 따른다. Layer별 정책은 별도 문서.
>
> 작성: 2026-04-29
> 상태: 초안 v0.1
> 의존: ROADMAP.md (먼저 읽기)
> 후속: HARNESS_LAYER1_DEV.md, HARNESS_LAYER2_SERVICE.md, AI_PLAYTESTER.md

---

## 0. 이 문서의 목적과 범위

### 다루는 것 (CORE)
- 4 층위 검증 모델 구체화
- Mechanical Checker / LLM-as-Judge 구조
- Cross-Model 매트릭스
- Eval Set 구조 + 버전 관리
- Scoring 알고리즘
- 5-Section System Prompt 템플릿
- Retry + Feedback Loop (정보 격리)
- LLM Client 추상화
- 결과 저장 + 실험 추적
- Configuration (harness.yaml 스키마)

### 다루지 않는 것 (별도 문서)
- Ship Gate 점수 정책 → `HARNESS_LAYER1_DEV.md`
- pre-commit / CI 설정 → `HARNESS_LAYER1_DEV.md`
- 게임 파이프라인 / Retry 횟수 → `HARNESS_LAYER2_SERVICE.md`
- Fallback 체인 정책 → `HARNESS_LAYER2_SERVICE.md`
- AI Playtester 페르소나 / CLI 매핑 → `AI_PLAYTESTER.md`

### 작성 원칙
- 의사코드 수준 (Tier 0 시작 시 그대로 코드로 옮길 수 있는 정도)
- Python 위주 (Hybrid 스택의 백엔드/LLM 측면)
- 변경 가능 (Living Harness — 외부 설정 우선)
- 자료의 검증된 패턴 그대로 차용

---

## 1. 4 층위 검증 모델

### 1.1 층위 개요

| 층위 | 대상 | 도구 | 결정성 | 비용 |
|---|---|---|---|---|
| **1: 코드** | 결정론적 로직 (게임 룰, 상태, DB) | pytest / Vitest | 결정적 | 0 |
| **2: Eval** | LLM 응답 분포 | 자체 runner + LLM-as-Judge | 비결정적 | 토큰 |
| **3: E2E** | 사용자 흐름 전체 | pytest 시나리오 + Playwright (Tier 2+) | 부분 결정적 | 토큰 |
| **3.5: AI Playtester** | "사용자 경험" 자동 시뮬 | Claude Code / Codex CLI / Gemini CLI | 비결정적 | 정액제 |
| **4: 인간** | "재미" / 정성 | 본인 + 친구 + 베타 | 비결정적 | 시간 |

### 1.2 층위 1 — 코드 테스트

**범위**: LLM과 무관하게 결정론적 로직.

```python
# tests/test_combat.py
def test_attack_calculates_damage():
    """공격이 정확한 데미지 계산"""
    state = GameState(player_attack=10, enemy_defense=3)
    result = process_attack(state)
    assert result.damage == 7

def test_inventory_does_not_allow_duplicates():
    state = GameState()
    state.add_item("sword")
    state.add_item("sword")
    assert state.inventory.count("sword") == 1

def test_save_load_preserves_state():
    state = GameState(hp=80, location="forest")
    saved = state.serialize()
    loaded = GameState.deserialize(saved)
    assert loaded.hp == 80
    assert loaded.location == "forest"
```

**원칙**:
- LLM 호출은 **mock**으로 (결정론적 검증)
- Coverage 목표 80%+
- 핵심 게임 룰 / 상태 관리 / DB / 직렬화는 필수

자료의 함정 24 회피 ("Test 없는 리팩토링 = 기도").

### 1.3 층위 2 — LLM 응답 평가

**범위**: LLM 출력의 분포 평가.

```python
# evals/run_eval.py
def evaluate(eval_set: EvalSet, target: LLMClient, judge: LLMClient) -> EvalResult:
    items = eval_set.load()
    results = []
    
    for item in items:
        # 1. 대상 LLM이 응답 생성
        response = target.generate(item.prompt)
        
        # 2. Mechanical 검증 (0 토큰)
        mechanical = run_mechanical_checks(response, item)
        
        # 3. LLM-as-Judge (Mechanical 통과 시만)
        if mechanical.passed:
            llm_score = judge.evaluate(response, item.criteria)
        else:
            llm_score = None  # 비용 절감
        
        results.append({
            "item_id": item.id,
            "response": response,
            "mechanical": mechanical.to_dict(),
            "llm_judge": llm_score.to_dict() if llm_score else None,
            "final_score": compute_final_score(mechanical, llm_score),
        })
    
    return EvalResult(items=results, eval_set_version=eval_set.version)
```

**원칙**:
- 시드 변동 (다양성 측정)
- 같은 eval set 버전으로 회귀 비교
- Mechanical 통과 후 LLM Judge (자료의 Evidence Gating)

### 1.4 층위 3 — E2E 시나리오

**범위**: 처음~끝 사용자 흐름.

```python
# tests/e2e/test_30min_scenario.py
def test_user_can_complete_kings_death_scenario():
    """미스터리 시나리오를 정해진 행동으로 완주 가능한가"""
    game = Game.start(scenario="kings_death")
    
    # 결정된 행동 시퀀스
    actions = load_test_actions("kings_death_walkthrough.yaml")
    
    for action in actions:
        result = game.process_action(action)
        assert not result.is_error
    
    assert game.state.is_completed
    assert game.state.ending in ["true_solution", "partial_solution"]
```

**원칙**:
- LLM 호출은 실제로 (시나리오 검증)
- 시드 고정 (재현 가능)
- 시나리오별 1개+ 시나리오 파일

### 1.5 층위 3.5 — AI Playtester (개요)

**범위**: 다양한 페르소나로 자동 플레이.

```python
# 개요만. 상세는 AI_PLAYTESTER.md
class AIPlaytester:
    def __init__(self, persona: Persona, cli: CLIProvider):
        self.persona = persona
        self.cli = cli
    
    def play(self, game_endpoint: str, n_turns: int = 30) -> Verdict:
        # CLI를 통해 페르소나가 "사용자처럼" 게임 플레이
        # 결과 = 평가 + 발견 이슈
        ...
```

핵심 원칙만 기억:
- 게임 LLM ≠ Playtester LLM (Cross-Model 강제)
- 정액제 CLI 우선 (claude-code / codex-cli / gemini-cli)
- 페르소나 = YAML 정의

상세: `AI_PLAYTESTER.md`

### 1.6 층위 4 — 인간 도그푸딩

**범위**: 정량으로 측정 못 하는 정성 평가.

```
- 본인 N회 플레이 (각 Tier 끝)
- 친구 N명 (Tier별 증가)
- 외부 베타 (Tier 3)
```

**원칙**:
- AI Playtester로 대체 불가 (메타 14.5)
- "재미", "다시 하고 싶음", "와닿음" 측정
- 자료의 함정 30 회피 (자기 만족 평가 X)

---

## 2. Mechanical Checker

### 2.1 구조

```python
# core/verify/mechanical.py

@dataclass
class CheckFailure:
    rule: str               # 어느 룰 실패
    severity: Literal["critical", "major", "minor"]
    detail: str             # 무엇이 실패했나
    suggestion: str = ""    # 어떻게 고치면 좋은가 (재시도용)


@dataclass
class MechanicalResult:
    passed: bool
    score: float            # 0-100
    failures: list[CheckFailure]
    
    def to_dict(self) -> dict: ...


class MechanicalChecker:
    """LLM 호출 0회. 즉시 실패 케이스 잡기."""
    
    def __init__(self, rules: list[Rule]):
        self.rules = rules
    
    def check(self, response: str, context: dict) -> MechanicalResult:
        failures = []
        for rule in self.rules:
            failure = rule.check(response, context)
            if failure:
                failures.append(failure)
        
        score = self._compute_score(failures)
        passed = len(failures) == 0
        return MechanicalResult(passed=passed, score=score, failures=failures)
    
    def _compute_score(self, failures: list[CheckFailure]) -> float:
        # critical 1개 = 0점
        # major 1개 = -30
        # minor 1개 = -10
        if any(f.severity == "critical" for f in failures):
            return 0.0
        score = 100.0
        for f in failures:
            score -= 30 if f.severity == "major" else 10
        return max(0.0, score)
```

### 2.2 5가지 표준 룰

WorldFork의 모든 LLM 응답에 적용:

```python
# core/verify/standard_rules.py

class JsonValidityRule(Rule):
    """JSON 응답이어야 할 때 파싱 가능한가"""
    severity = "critical"
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        if not context.get("requires_json"):
            return None
        try:
            json.loads(response)
            return None
        except json.JSONDecodeError as e:
            return CheckFailure(
                rule="json_validity",
                severity="critical",
                detail=f"JSON parse error: {e}",
                suggestion="Output valid JSON. No markdown fences, no preamble."
            )


class KoreanRatioRule(Rule):
    """한국어 비율이 충분한가 (한국어 게임)"""
    severity = "major"
    threshold = 0.7
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        if not context.get("language") == "ko":
            return None
        korean_chars = sum(1 for c in response if 0xAC00 <= ord(c) <= 0xD7A3)
        ratio = korean_chars / max(1, len(response))
        if ratio < self.threshold:
            return CheckFailure(
                rule="korean_ratio",
                severity="major",
                detail=f"Korean ratio {ratio:.1%} < {self.threshold:.0%}",
                suggestion="Respond primarily in Korean. Avoid English unless necessary."
            )
        return None


class LengthRule(Rule):
    """응답 길이가 적절한가"""
    severity = "minor"
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        max_len = context.get("max_length", 500)
        if len(response) > max_len * 1.5:
            return CheckFailure(
                rule="length",
                severity="minor",
                detail=f"Response too long: {len(response)} chars (max {max_len})",
                suggestion=f"Keep response under {max_len} characters."
            )
        return None


class AIBreakoutRule(Rule):
    """AI 본능 누설 ('I am an AI', 'ChatGPT' 등)"""
    severity = "major"
    forbidden = [
        "I'm an AI", "I am an AI", "language model", "ChatGPT",
        "as an AI", "I cannot", "AI 어시스턴트",
    ]
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        if not context.get("character_response"):
            return None
        leaked = [p for p in self.forbidden if p.lower() in response.lower()]
        if leaked:
            return CheckFailure(
                rule="ai_breakout",
                severity="major",
                detail=f"AI breakout phrases: {leaked}",
                suggestion="Stay in character. Do not mention being an AI."
            )
        return None


class GameStateConsistencyRule(Rule):
    """LLM이 게임 상태에 없는 것을 도입하지 않는가"""
    severity = "major"
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        if not context.get("game_state"):
            return None
        state = context["game_state"]
        # 인벤토리에 없는 아이템 사용
        mentioned_items = extract_item_mentions(response)
        invalid = [i for i in mentioned_items if i not in state.inventory]
        if invalid:
            return CheckFailure(
                rule="game_state_consistency",
                severity="major",
                detail=f"Used items not in inventory: {invalid}",
                suggestion=f"Only use items from: {state.inventory}"
            )
        return None
```

### 2.3 게임 도메인 룰 추가 패턴

표준 5개에 도메인 특화 룰 추가:

```python
# game/rules/world_canon_rule.py
class WorldCanonRule(Rule):
    """세계관 캐논 위반 감지 (Tier 1+)"""
    severity = "major"
    
    def __init__(self, world_spec: WorldSpec):
        self.allowed = world_spec.allowed_elements
        self.forbidden = world_spec.forbidden_elements
    
    def check(self, response: str, context: dict) -> CheckFailure | None:
        violations = []
        for forbidden in self.forbidden:
            if forbidden.lower() in response.lower():
                violations.append(forbidden)
        if violations:
            return CheckFailure(
                rule="world_canon",
                severity="major",
                detail=f"World canon violations: {violations}",
                suggestion=f"This world does not have: {violations}. Use only canon elements."
            )
        return None
```

새 룰 추가 = 단순 클래스 추가. Mechanical Checker는 룰 리스트만 받음.

---

## 3. LLM-as-Judge

### 3.1 구조

```python
# core/verify/llm_judge.py

@dataclass
class JudgeScore:
    score: float                    # 0-100
    verdict: Literal["pass", "warn", "fail"]
    issues: list[str]               # 발견된 이슈
    suggestions: list[str]          # 개선 제안
    judge_model: str                # 어떤 모델이 판정했나
    cost_usd: float
    latency_ms: int


class LLMJudge:
    """다른 모델로 LLM 응답 평가"""
    
    def __init__(self, judge_client: LLMClient):
        self.judge = judge_client
    
    def evaluate(
        self,
        response: str,
        criteria: JudgeCriteria,
        context: dict | None = None,
    ) -> JudgeScore:
        prompt = self._build_judge_prompt(response, criteria, context)
        result = self.judge.generate_json(prompt, schema=JUDGE_SCHEMA)
        return JudgeScore(
            score=result["score"],
            verdict=result["verdict"],
            issues=result["issues"],
            suggestions=result["suggestions"],
            judge_model=self.judge.model_name,
            cost_usd=result["_cost_usd"],
            latency_ms=result["_latency_ms"],
        )
```

### 3.2 Judge Prompt 템플릿

5-section 구조 그대로:

```python
JUDGE_PROMPT_TEMPLATE = """
# IDENTITY
You are an evaluation expert for the WorldFork game system.
Your job is to score LLM responses on multiple criteria, not as the original LLM.

# TASK
Evaluate the following response based on the given criteria.
Be objective. Do NOT favor the response just because it sounds plausible.

# CRITERIA
{criteria_description}

Specifically score:
{specific_dimensions}

# CONTEXT
{context_description}

# RESPONSE TO EVALUATE
---
{response}
---

# OUTPUT FORMAT
Respond ONLY with valid JSON, no markdown fences.

Schema:
{{
  "score": <0-100>,
  "verdict": "pass" | "warn" | "fail",
  "issues": [<list of specific issues found>],
  "suggestions": [<list of concrete improvements>]
}}

Score guidelines:
- 95-100: Excellent, no issues
- 85-94: Good, minor issues
- 70-84: Acceptable, some issues
- 50-69: Weak, multiple issues
- 0-49: Failed, critical issues

# EXAMPLES
{few_shot_examples}
"""
```

각 평가 카테고리별 specific_dimensions:

```yaml
# core/verify/judge_criteria.yaml

persona_consistency:
  description: "Does the response stay in character?"
  dimensions:
    - "Speech style matches the character's defined voice"
    - "Personality traits reflected in response"
    - "Does NOT break character (e.g., AI mentions)"
    - "Length appropriate for character"

korean_quality:
  description: "Is the Korean natural and appropriate?"
  dimensions:
    - "Grammar correctness"
    - "Natural phrasing (not translated-sounding)"
    - "Appropriate formality (반말/존댓말)"
    - "No mixed-language confusion"

ip_leakage:
  description: "Does the response leak copyrighted IP?"
  dimensions:
    - "No direct quotes from original work (15+ words)"
    - "No proper character names from copyrighted source"
    - "No unique world-specific terminology verbatim"
    - "Concepts inspired but not copied"

world_consistency:
  description: "Is the response consistent with the world setting?"
  dimensions:
    - "Uses only allowed world elements"
    - "Does not violate stated rules (magic, technology, etc.)"
    - "Character knowledge appropriate to setting"
    - "Tone matches the world's atmosphere"

# 추가 카테고리는 Living Harness 원칙으로 yaml에 추가
```

### 3.3 Cross-Model 강제

```python
# core/verify/cross_model.py

class CrossModelEnforcer:
    """생성자와 검증자가 같은 모델이면 거부"""
    
    @staticmethod
    def select_judge(generator_model: str, available_judges: list[str]) -> str:
        """생성자와 다른 모델 선택"""
        candidates = [m for m in available_judges if m != generator_model]
        if not candidates:
            raise CrossModelError(
                f"No judge available different from generator '{generator_model}'"
            )
        return candidates[0]  # 첫 사용 가능한 후보
    
    @staticmethod
    def assert_different(generator: str, judge: str):
        """동일 모델 사용 시 즉시 에러"""
        if generator == judge:
            raise CrossModelError(
                f"Self-rationalization risk: generator and judge are both '{generator}'"
            )
```

**원칙**: 자료의 가장 중요한 검증 패턴. 같은 모델로 self-eval은 무의미.

---

## 4. Cross-Model 매트릭스

### 4.1 매트릭스 형식

`config/cross_model.yaml`:

```yaml
# WorldFork Cross-Model Matrix v1
# 검증 카테고리별 generator → verifier 매핑

categories:
  
  game_response:
    description: "캐릭터 응답 / GM 묘사"
    generator:
      tier_0: claude_haiku_3_5      # API
      tier_1: local_qwen_2b          # DGX
      tier_3_sft: worldfork_qwen_sft # 자체 SFT
    verifier:
      primary: claude_haiku_3_5
      challenger: gpt_4o_mini
      fallback: gemini_flash
    constraint: "verifier != generator"
  
  plan_generation:
    description: "작품 정보 → 게임 플랜"
    generator:
      drafter: claude_opus
    verifier:
      challenger: gemini_pro       # ★ 다른 모델 (드래프터 reasoning 못 봄)
      quality_check: gpt_4o
    constraint: "challenger != drafter, quality_check != drafter"
  
  ip_leakage:
    description: "저작권 누출 검사"
    generator: any
    verifier:
      primary: claude_opus          # IP 판단력 강한 모델
      secondary: gpt_4o
    constraint: "verifier != generator"
  
  ai_playtester:
    description: "사용자 시뮬"
    generator: any                  # 게임 LLM
    verifier:
      # 각 페르소나별 별도 정의 (AI_PLAYTESTER.md 참조)
      see: AI_PLAYTESTER.md
    constraint: "playtester_cli != game_llm"

# Available models
models:
  claude_haiku_3_5:
    type: api
    provider: anthropic
    cost_per_1k_input: 0.0008
    cost_per_1k_output: 0.004
  
  claude_opus:
    type: api
    provider: anthropic
    # 비싸므로 plan_generation과 ip_leakage에만
  
  gpt_4o_mini:
    type: api
    provider: openai
  
  gpt_4o:
    type: api
    provider: openai
  
  gemini_pro:
    type: api
    provider: google
  
  gemini_flash:
    type: api
    provider: google
  
  local_qwen_2b:
    type: local
    endpoint: http://dgx:8080
    model_path: qwen3.5-2b-instruct-q4_k_m.gguf
    cost_per_1k: 0
  
  worldfork_qwen_sft:
    type: local
    endpoint: http://dgx:8080
    model_path: worldfork_v1_q4_k_m.gguf  # Tier 3 SFT
```

### 4.2 카테고리별 매핑 활용

```python
# core/verify/matrix.py

class CrossModelMatrix:
    def __init__(self, config_path: Path):
        self.config = load_yaml(config_path)
    
    def get_generator(self, category: str, tier: str) -> str:
        return self.config["categories"][category]["generator"].get(tier)
    
    def get_verifier(self, category: str, role: str = "primary") -> str:
        return self.config["categories"][category]["verifier"][role]
    
    def assert_constraint(self, category: str, generator: str, verifier: str):
        constraint = self.config["categories"][category]["constraint"]
        if "verifier != generator" in constraint and generator == verifier:
            raise CrossModelError(...)
```

### 4.3 변경 절차

Living Harness 원칙. 매트릭스도 외부 설정.

```
1. 변경 제안 (예: "tier_1에서 game_response generator를 qwen_4b로")
2. 영향 측정 (eval set 양쪽 실행, 점수 비교)
3. config/cross_model.yaml 업데이트
4. 회귀 측정 (이전 baseline 대비)
5. ROADMAP 미해결 의사결정 섹션 업데이트
```

### 4.4 Debate Mode (고비용 / 고신뢰도)

자료의 Drafter → Challenger → Quality Checker 패턴.
**중요한 검증**(플랜 생성, IP 누출 검사, 출시 게이트 등)에 적용.

#### 왜 Debate Mode인가

단일 LLM Judge의 한계:
- 가짜 양성 (false positive) — "이 코드 좋아 보입니다" 무한 루프
- 한 시각에서만 평가
- 미묘한 이슈 놓침

Debate 효과:
- 다른 모델이 반박하며 다른 시각 제공
- localStorage persistence 같은 미묘한 이슈 발견 (자료 사례)
- 단일 LLM이 놓친 케이스 잡음

비용/신뢰도 트레이드오프:
- 비용 3배 (Drafter + Challenger + Quality)
- 시간 3배
- 신뢰도 향상 (정량 측정 어렵지만 자료에서 검증)

#### 구조

```python
# core/verify/debate.py

@dataclass
class DebateResult:
    drafter_score: JudgeScore       # 1차 평가
    challenger_score: JudgeScore    # 반박 평가
    final_score: JudgeScore         # Quality Checker 최종
    
    # 가중 합 (drafter 60% + challenger 40%)
    @property
    def weighted_score(self) -> float:
        return (
            self.drafter_score.score * 0.6
            + self.challenger_score.score * 0.4
        )


class DebateJudge:
    """3개 모델 협력 평가"""
    
    def __init__(
        self,
        drafter: LLMClient,
        challenger: LLMClient,
        quality_checker: LLMClient,
    ):
        # Cross-Model 강제: 3개 모두 다른 모델
        models = {drafter.model_name, challenger.model_name, quality_checker.model_name}
        if len(models) < 3:
            raise CrossModelError(
                f"Debate Mode requires 3 different models, got {models}"
            )
        self.drafter = drafter
        self.challenger = challenger
        self.quality = quality_checker
    
    def evaluate(
        self,
        target_response: str,
        criteria: JudgeCriteria,
        context: dict,
    ) -> DebateResult:
        # 1. Drafter — 1차 평가
        drafter_result = self._draft(target_response, criteria, context)
        
        # 2. Challenger — 반박 (★ Drafter의 reasoning은 못 봄)
        challenger_result = self._challenge(
            target_response,
            criteria,
            context,
            # 의도적으로 drafter_result 안 넘김
            # → 자료의 "Challenger 코드 격리" 패턴
        )
        
        # 3. Quality Checker — 최종 종합
        final_result = self._quality_check(
            target_response,
            criteria,
            drafter_result,
            challenger_result,
        )
        
        return DebateResult(
            drafter_score=drafter_result,
            challenger_score=challenger_result,
            final_score=final_result,
        )
    
    def _draft(self, response, criteria, context) -> JudgeScore:
        prompt = build_drafter_prompt(response, criteria, context)
        return self._call(self.drafter, prompt)
    
    def _challenge(self, response, criteria, context) -> JudgeScore:
        # ★ Drafter 결과 못 봄. 원본만 보고 독립 평가
        prompt = build_challenger_prompt(response, criteria, context)
        return self._call(self.challenger, prompt)
    
    def _quality_check(
        self, response, criteria, drafter, challenger
    ) -> JudgeScore:
        # Quality Checker만 둘 다 봄
        prompt = build_quality_prompt(response, criteria, drafter, challenger)
        return self._call(self.quality, prompt)
```

#### Challenger 코드/Reasoning 격리 (핵심)

자료의 가장 중요한 패턴:

> "Debate Challenger: 프로젝트 코드를 아예 못 봄 (플랜+요청만 봄)
> 코드를 보면 '구현이 이미 있으니 맞겠지' 편향 발생"

WorldFork 적용:

```python
def build_challenger_prompt(
    response: str,
    criteria: JudgeCriteria,
    context: dict,
    drafter_result: None = None,  # ★ None만 받음 (절대 채우지 않음)
) -> str:
    """Challenger는 Drafter의 평가/이유 못 봄"""
    if drafter_result is not None:
        raise InformationLeakError(
            "Challenger must not see Drafter's reasoning"
        )
    
    return f"""
# IDENTITY
You are an independent evaluator. Your job is to find issues.
Another evaluator has already reviewed this — but you don't know their findings.
Form your own judgment.

# TASK
Critically evaluate the response. Find issues the original generator might have missed.
Be skeptical. Look for problems.

# CRITERIA
{criteria.description}

# CONTEXT
{filter_context_for_challenger(context)}
# (게임 상태나 LLM reasoning 같은 편향 정보 제외)

# RESPONSE TO EVALUATE
{response}

# OUTPUT
JSON: {{"score": 0-100, "verdict": "...", "issues": [...], "suggestions": [...]}}
"""
```

#### Quality Checker 종합

```python
def build_quality_prompt(
    response: str,
    criteria: JudgeCriteria,
    drafter: JudgeScore,
    challenger: JudgeScore,
) -> str:
    """Quality Checker만 둘 다 봄"""
    return f"""
# IDENTITY
You are a quality checker. Two evaluators reviewed this response independently.

# DRAFTER FOUND
Score: {drafter.score}
Issues: {drafter.issues}

# CHALLENGER FOUND  
Score: {challenger.score}
Issues: {challenger.issues}

# YOUR TASK
1. Are the issues from each evaluator real? (Not false positive)
2. Did either miss something the other caught?
3. What is the final verdict?

# RESPONSE
{response}

# OUTPUT
JSON: {{
  "score": <final 0-100>,
  "verdict": "pass" | "warn" | "fail",
  "validated_issues": [<only real issues>],
  "false_positives": [<issues that aren't real>],
  "suggestions": [<concrete improvements>]
}}
"""
```

#### Debate 적용 시점

비용이 크므로 모든 검증에 X. 다음에만 적용:

```yaml
# config/harness.yaml에 정의

debate_mode:
  enabled_for:
    - plan_generation        # 플랜 생성 (Tier 1+)
    - ip_leakage_check       # 저작권 검증 (Tier 1+)
    - layer1_ship_gate       # Layer 1 출시 게이트
    - tier_3_pre_release     # Tier 3 출시 전 검증
  
  disabled_for:
    - game_response          # 매 응답 = 비용 폭발
    - mechanical_only        # 단순 형식 검증
    - ai_playtester          # 자체가 다중 페르소나
  
  models:
    drafter: claude_opus
    challenger: gemini_pro
    quality_checker: gpt_4o
```

#### Single Judge vs Debate 선택

```python
class JudgeRouter:
    """검증 카테고리별 Single 또는 Debate 선택"""
    
    def __init__(self, config: dict, registry: LLMRegistry):
        self.debate_categories = set(
            config["debate_mode"]["enabled_for"]
        )
        self.registry = registry
    
    def get_judge(self, category: str) -> LLMJudge | DebateJudge:
        if category in self.debate_categories:
            return self._build_debate_judge(category)
        else:
            return self._build_single_judge(category)
```

#### Debate Mode와 정보 격리

자료의 함정 모두 회피:

```
Drafter:
  - 원본 응답 + 기준 본다
  - 자기 평가 진행
  
Challenger:
  - 원본 응답 + 기준 본다
  - ★ Drafter의 reasoning / score / verdict 못 봄
  - 독립 평가
  - "이미 평가됐다"는 정보 자체가 편향이라 차단
  
Quality Checker:
  - 두 평가 결과 본다
  - 어느 게 false positive인지 판단
  - 최종 점수 산출

재시도 시 (게임 응답 → Drafter):
  - Drafter의 issues + suggestions만 전달
  - score / verdict 안 전달
  - "85점이니 살짝만" 합리화 차단
```

---

## 5. Eval Set

### 5.1 디렉토리 구조

```
evals/
├── README.md                          # eval set 개요
├── persona_consistency/
│   ├── v1.jsonl                       # 첫 버전 (보존)
│   ├── v2.jsonl                       # 추가/수정
│   ├── v3.jsonl                       # 현재
│   ├── CHANGELOG.md                   # 변경 이력
│   └── README.md                      # 카테고리 설명
├── korean_quality/
│   ├── v1.jsonl
│   └── ...
├── json_validity/
├── ip_leakage/
├── world_consistency/
├── ai_breakout/
└── game_state_hallucination/
```

### 5.2 JSONL 형식

```jsonl
{"id": "persona_001", "category": "persona_consistency", "version": "v3", "prompt": {"system": "당신은 엘리자베스 왕비입니다...", "user": "왕비님, 어디 계셨습니까?"}, "expected_behavior": {"in_character": true, "speech_style": "격식체", "no_ai_mentions": true}, "criteria": "persona_consistency", "context": {"language": "ko", "character_response": true, "max_length": 200}}
{"id": "persona_002", "category": "persona_consistency", "version": "v3", "prompt": {"system": "...", "user": "당신 누구입니까? AI인가요?"}, "expected_behavior": {"in_character": true, "no_ai_mentions": true, "respond_as_character_to_meta_question": true}, "criteria": "persona_consistency", "context": {"language": "ko", "character_response": true}}
```

각 항목 필드:
- `id`: 고유 식별자
- `category`: 평가 카테고리
- `version`: 평가셋 버전
- `prompt`: system + user
- `expected_behavior`: 무엇을 기대하는가 (LLM-as-Judge에 전달)
- `criteria`: 어떤 judge criteria 사용
- `context`: Mechanical Checker에 전달할 컨텍스트

### 5.3 카테고리

```
필수 (Tier 0부터):
  - persona_consistency      캐릭터 일관성
  - korean_quality           한국어 자연스러움
  - json_validity            JSON 출력 유효성
  - ai_breakout              AI 본능 누설
  - game_state_hallucination 인벤토리/상태 누설

Tier 1 추가:
  - ip_leakage               저작권 누출
  - world_consistency        세계관 일관성
  - plan_quality             플랜 생성 품질

Tier 2 추가:
  - long_session_drift       30턴 후 일관성
  - relationship_consistency 캐릭터 간 관계 일관성
  - genre_tone_match         장르 시스템별 톤

Tier 3 추가:
  - sft_improvement          SFT 후 개선 측정용
```

### 5.4 버전 관리

```
변경 시 절차:

1. 새 버전 파일 생성
   evals/persona_consistency/v4.jsonl
   
2. CHANGELOG.md 업데이트
   ## v4 (2026-05-15)
   - 추가: 시간선 일관성 케이스 5개 (case_id: 046-050)
   - 수정: case_001의 expected_behavior 보강
   - 폐기: case_022 (중복)
   
3. 영향 측정
   python evals/compare.py \
     --model qwen_2b \
     --old persona_consistency/v3 \
     --new persona_consistency/v4
   
4. config/harness.yaml 업데이트
   eval_sets:
     persona_consistency:
       version: v4    # ← 변경
   
5. baseline 재측정
   python evals/run.py --eval-set persona_consistency --version v4
   결과 → runs/baseline_v4_{timestamp}.json
```

이전 버전 절대 삭제 금지. 회귀 비교용 보존.

### 5.5 Filter Pipeline (v0.2 신규, lm-eval 패턴 차용)

LLM 응답에서 구조화된 출력을 추출하는 fallback 체인.

#### 왜 필요한가

```
GBNF (생성 시점 강제):
  - llama.cpp, vLLM, SGLang에서 지원
  - 100% 형식 보장
  
GBNF가 안 되는 경우:
  - Claude API (function calling만, JSON 강제 X)
  - GPT-4o (function calling, JSON mode 있지만 grammar 아님)
  - 일부 로컬 모델 / 추론 엔진

문제:
  - Layer 1 verifier는 다양한 모델 사용 (Cross-Model)
  - 일부 verifier가 GBNF 미지원 = 응답 파싱 실패
  - 외부 도구 (lm-eval, promptfoo) 모두 post-hoc 추출로 해결
```

#### 구조

```python
# core/eval/filter_pipeline.py

class Filter(ABC):
    """LLM 출력 후처리 단계"""
    
    @abstractmethod
    def apply(self, raw_output: str, context: dict) -> FilterResult:
        ...


@dataclass
class FilterResult:
    succeeded: bool
    parsed: dict | None
    error: str | None
    filter_used: str   # 어느 필터가 성공했나


class FilterPipeline:
    """다중 필터를 우선순위 순으로 시도"""
    
    def __init__(self, filters: list[Filter]):
        self.filters = filters
    
    def extract(self, raw_output: str, context: dict) -> FilterResult:
        errors = []
        for f in self.filters:
            result = f.apply(raw_output, context)
            if result.succeeded:
                return result
            errors.append(f"{f.__class__.__name__}: {result.error}")
        
        return FilterResult(
            succeeded=False,
            parsed=None,
            error=f"All filters failed: {'; '.join(errors)}",
            filter_used=None,
        )


# 표준 필터 체인 (우선순위 순)

class GBNFNativeFilter(Filter):
    """GBNF로 강제된 응답 (이미 valid JSON)"""
    def apply(self, raw_output, context):
        try:
            return FilterResult(True, json.loads(raw_output), None, "gbnf")
        except json.JSONDecodeError as e:
            return FilterResult(False, None, str(e), "gbnf")


class MarkdownFenceFilter(Filter):
    """```json ... ``` 마크다운 펜스 추출"""
    PATTERN = re.compile(r"```(?:json)?\s*\n(.*?)\n```", re.DOTALL)
    
    def apply(self, raw_output, context):
        match = self.PATTERN.search(raw_output)
        if not match:
            return FilterResult(False, None, "No markdown fence", "markdown_fence")
        try:
            return FilterResult(True, json.loads(match.group(1)), None, "markdown_fence")
        except json.JSONDecodeError as e:
            return FilterResult(False, None, str(e), "markdown_fence")


class FirstJsonObjectFilter(Filter):
    """텍스트 안 첫 번째 { ... } 추출"""
    
    def apply(self, raw_output, context):
        # 중괄호 매칭으로 첫 번째 완전한 JSON 객체 찾기
        depth = 0
        start = -1
        for i, c in enumerate(raw_output):
            if c == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0 and start != -1:
                    candidate = raw_output[start:i+1]
                    try:
                        return FilterResult(True, json.loads(candidate), None, "first_json_object")
                    except json.JSONDecodeError:
                        start = -1   # 다음 후보 찾기
        return FilterResult(False, None, "No complete JSON object found", "first_json_object")


class RetryWithStricterPromptFilter(Filter):
    """LLM에 재시도 요청 (마지막 수단, 비용 발생)"""
    
    def __init__(self, llm_client: LLMClient, max_retries: int = 1):
        self.llm = llm_client
        self.max_retries = max_retries
    
    def apply(self, raw_output, context):
        for attempt in range(self.max_retries):
            stricter_prompt = f"""
            The following response is NOT valid JSON.
            Output ONLY valid JSON. No markdown, no text, no preamble.
            
            Original response:
            {raw_output}
            
            Schema needed: {context.get('schema', 'Any valid JSON')}
            """
            try:
                fixed = self.llm.generate(stricter_prompt)
                return FilterResult(True, json.loads(fixed), None, "retry_stricter")
            except Exception as e:
                continue
        return FilterResult(False, None, "Retry attempts exhausted", "retry_stricter")


# 표준 파이프라인
STANDARD_FILTER_PIPELINE = FilterPipeline([
    GBNFNativeFilter(),              # 1순위: GBNF 성공 시
    MarkdownFenceFilter(),           # 2순위: 마크다운 펜스
    FirstJsonObjectFilter(),         # 3순위: 첫 JSON 객체 추출
    # RetryWithStricterPromptFilter(...)  # 4순위: 재시도 (선택)
])
```

#### 사용 예시

```python
# Layer 1 verifier 코드
verifier_response = verifier_client.generate(prompt)

# Filter Pipeline으로 파싱 시도
pipeline = STANDARD_FILTER_PIPELINE
result = pipeline.extract(verifier_response, context={"schema": JUDGE_SCHEMA})

if result.succeeded:
    judge_score = result.parsed
    log.debug(f"Filter used: {result.filter_used}")
else:
    # 모든 필터 실패 → 에러
    raise ParsingError(result.error)
```

#### Tier별 활용

```yaml
Tier 0:
  # API 모델 (Haiku, GPT-4o-mini)
  # GBNF 미지원이지만 JSON mode 사용 가능
  # → MarkdownFenceFilter, FirstJsonObjectFilter 위주

Tier 1+:
  # 로컬 모델 (Qwen, Gemma) + GBNF
  # → GBNFNativeFilter 1순위
  # API fallback 시 다른 필터로 자동 전환
```

#### 측정 (Tier 1 진입 시 ablation)

```
검증 계획 (ROADMAP 11.7.3):
  - GBNF 모드만 vs Filter Pipeline 모드 비교
  - 100 케이스에서 성공률 측정
  - Cross-Model 환경에서 효과 검증
```

자료의 함정 19 회피 + lm-eval 패턴 차용 = 안정성 강화.

---

## 6. Scoring

### 6.1 알고리즘

`harness.yaml`로 선택:

```yaml
scoring:
  algorithm: geometric_mean    # weighted_sum | geometric_mean | min
  fail_fast: true              # mechanical critical 1개면 즉시 0점
```

```python
# core/verify/scoring.py

class Scorer:
    def __init__(self, algorithm: str, weights: dict[str, float]):
        self.algorithm = algorithm
        self.weights = weights
    
    def compute(self, scores: dict[str, float]) -> float:
        """카테고리별 점수 → 최종 점수"""
        if self.algorithm == "weighted_sum":
            return sum(s * self.weights[cat] for cat, s in scores.items())
        
        elif self.algorithm == "geometric_mean":
            # 한 카테고리가 0이면 전체 0
            if any(s == 0 for s in scores.values()):
                return 0.0
            product = 1.0
            for s in scores.values():
                product *= s / 100  # 0-1 범위로
            return (product ** (1 / len(scores))) * 100
        
        elif self.algorithm == "min":
            return min(scores.values())
        
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
```

### 6.2 Fail-Fast 정책

자료의 핵심 원칙: **점수 하드코딩 금지 + 명백한 실패는 즉시 0점**.

```python
def evaluate_with_fail_fast(response, item, mechanical, judge):
    # 1. Mechanical critical 실패 = 즉시 0점
    if any(f.severity == "critical" for f in mechanical.failures):
        return Score(value=0, reason="mechanical_critical_fail")
    
    # 2. Mechanical major 다수 실패 = 즉시 낮은 점수
    if len([f for f in mechanical.failures if f.severity == "major"]) >= 2:
        return Score(value=20, reason="multiple_major_fails")
    
    # 3. 나머지는 LLM Judge로
    judge_score = judge.evaluate(response, item.criteria)
    
    # 4. 최종 점수 = 가중 합 (mechanical 30 + judge 70)
    final = mechanical.score * 0.3 + judge_score.score * 0.7
    return Score(value=final, mechanical=mechanical, judge=judge_score)
```

### 6.3 점수 누설 금지 (정보 격리)

자료의 핵심 원칙. 재시도 시 점수를 LLM에 절대 전달하지 않는다.

```python
# core/verify/feedback.py

@dataclass
class RetryFeedback:
    """재시도 시 LLM에 전달하는 정보"""
    issues: list[str]            # ✅ 무엇이 문제인가
    suggestions: list[str]       # ✅ 어떻게 고치면 되는가
    
    # ❌ 절대 포함 금지
    # score: float
    # verdict: str  
    # threshold: float
    
    def to_prompt(self) -> str:
        text = "Please revise the previous response. Issues found:\n\n"
        for issue in self.issues:
            text += f"- {issue}\n"
        text += "\nSuggestions:\n"
        for suggestion in self.suggestions:
            text += f"- {suggestion}\n"
        text += "\nRevise to address ALL issues."
        return text


def build_retry_feedback(
    mechanical: MechanicalResult,
    judge: JudgeScore | None,
) -> RetryFeedback:
    """검증 결과 → 재시도 피드백 (점수 제외)"""
    issues = [f.detail for f in mechanical.failures]
    suggestions = [f.suggestion for f in mechanical.failures if f.suggestion]
    
    if judge:
        issues.extend(judge.issues)
        suggestions.extend(judge.suggestions)
    
    return RetryFeedback(issues=issues, suggestions=suggestions)
```

자료의 anti-pattern 회피:
> "85점이니까 조금만 고치면 되겠지" → 본질 안 고침

---

## 7. 5-Section System Prompt

### 7.1 표준 구조

WorldFork의 모든 LLM 호출에 적용:

```python
# core/prompts/template.py

SYSTEM_PROMPT_TEMPLATE = """
# IDENTITY
{identity}

# TASK
{task}

# SPEC
{spec}

# OUTPUT FORMAT
{output_format}

# EXAMPLES
{examples}
"""


def build_system_prompt(
    role: str,
    spec_fragments: list[str],
    examples: list[Example],
    context: dict,
) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        identity=load_identity(role, context),
        task=load_task(role),
        spec="\n\n".join(spec_fragments),
        output_format=load_output_format(role),
        examples="\n\n".join(format_example(e) for e in examples),
    )
```

### 7.2 Dynamic Context Assembly

자료의 함정 13 회피 ("컨텍스트 = 모든 정보 다 넣기").

```python
# core/prompts/assembler.py

class PromptAssembler:
    """관련 fragment만 동적으로 조립"""
    
    def __init__(self, fragments: dict[str, str], examples: dict[str, list]):
        self.fragments = fragments  # {"agent": "...", "shell": "...", ...}
        self.examples = examples
    
    def assemble(self, role: str, user_input: str, context: dict) -> str:
        # 1. 키워드 감지
        relevant_fragments = self._select_fragments(user_input, context)
        
        # 2. Few-shot 선택
        relevant_examples = self._select_examples(role, user_input, n=3)
        
        # 3. 시스템 프롬프트 조립
        return build_system_prompt(
            role=role,
            spec_fragments=[self.fragments[f] for f in relevant_fragments],
            examples=relevant_examples,
            context=context,
        )
    
    def _select_fragments(self, user_input: str, context: dict) -> list[str]:
        # 키워드 → fragment 매핑 (단순 regex로 시작)
        selected = ["base_spec"]  # 항상 포함
        
        if context.get("requires_combat"):
            selected.append("combat_rules")
        if "마법" in user_input or "주문" in user_input:
            selected.append("magic_system")
        # ...
        
        return selected
```

자료의 효과: 평균 토큰 ~40% 감소.

### 7.3 Examples 관리

```
core/prompts/
├── identities/
│   ├── gm.md
│   ├── character.md
│   ├── verifier.md
│   ├── interview.md
│   └── plan_drafter.md
├── tasks/
│   └── ...
├── specs/
│   ├── base_spec.md
│   ├── combat_rules.md
│   ├── magic_system.md
│   └── ...
└── examples/
    ├── character_response/
    │   ├── ex_001.yaml
    │   ├── ex_002.yaml
    │   └── ...
    ├── plan_generation/
    └── ...
```

각 예시 = YAML:

```yaml
# core/prompts/examples/character_response/ex_001.yaml
id: char_response_ex_001
character: queen_elizabeth
input:
  user: "왕은 어디 계신가?"
output:
  dialogue: "...글쎄요, 제가 알 일이 아닙니다."
  tone: "neutral"
  internal_thought: "이 자가 무얼 알고 있는 거지?"
metadata:
  added: 2026-04-29
  source: tier_0_session_03
  used_in_eval: false
```

자료의 권장: **5-10 examples**가 sweet spot. 추상 묘사 < 실제 예시.

### 7.4 3-Tier 프롬프트 로딩

자료의 패턴:

```python
# core/prompts/loader.py

def load_prompt(role: str, scenario_dir: Path | None = None) -> str:
    """
    1순위: {scenario_dir}/prompts/{role}.md
    2순위: ~/.worldfork/prompts/{role}.md
    3순위: core/prompts/identities/{role}.md (default)
    """
    candidates = []
    if scenario_dir:
        candidates.append(scenario_dir / "prompts" / f"{role}.md")
    candidates.append(Path.home() / ".worldfork" / "prompts" / f"{role}.md")
    candidates.append(Path("core/prompts/identities") / f"{role}.md")
    
    for path in candidates:
        if path.exists():
            return path.read_text()
    raise PromptNotFoundError(role)
```

작품별 톤 변경 (코미디 vs 다크 판타지) 등에 활용.

---

## 8. Retry + Feedback Loop

### 8.1 구조

```python
# core/verify/retry.py

class RetryRunner:
    """검증 실패 시 피드백과 함께 재시도"""
    
    def __init__(
        self,
        client: LLMClient,
        verifier: Verifier,
        max_retries: int,        # Layer별 다름
    ):
        self.client = client
        self.verifier = verifier
        self.max_retries = max_retries
    
    def run(
        self,
        prompt: Prompt,
        context: dict,
    ) -> RetryResult:
        attempts = []
        current_prompt = prompt
        
        for attempt in range(self.max_retries + 1):
            # 1. 생성
            response = self.client.generate(current_prompt)
            
            # 2. 검증 (Mechanical → LLM Judge)
            verify_result = self.verifier.verify(response, context)
            attempts.append(VerifyAttempt(
                attempt_n=attempt,
                response=response,
                result=verify_result,
            ))
            
            # 3. 통과 시 종료
            if verify_result.passed:
                return RetryResult(
                    final_response=response,
                    final_result=verify_result,
                    attempts=attempts,
                    succeeded=True,
                )
            
            # 4. 실패 시 피드백 prompt 구성 (정보 격리)
            feedback = build_retry_feedback(
                verify_result.mechanical,
                verify_result.judge,
            )
            current_prompt = prompt.with_retry_feedback(feedback)
        
        # max retry 초과
        return RetryResult(
            final_response=attempts[-1].response,
            final_result=attempts[-1].result,
            attempts=attempts,
            succeeded=False,
        )
```

### 8.2 정보 격리 강제

```python
# core/verify/retry.py

class Prompt:
    def with_retry_feedback(self, feedback: RetryFeedback) -> "Prompt":
        """재시도 prompt에 피드백 추가 — 점수는 절대 안 들어감"""
        # 자동 검증
        feedback_dict = feedback.to_dict()
        FORBIDDEN_KEYS = {"score", "verdict", "threshold", "passed"}
        leaked = set(feedback_dict.keys()) & FORBIDDEN_KEYS
        if leaked:
            raise InformationLeakError(
                f"Forbidden keys in retry feedback: {leaked}"
            )
        
        return Prompt(
            system=self.system,
            user=self.user + "\n\n" + feedback.to_prompt(),
        )
```

이 검증을 우회하면 즉시 에러. 자료의 패턴 강제.

### 8.3 max_retry 정책

CORE는 **인터페이스만 정의**, 실제 횟수는 Layer별:

```yaml
# Layer 1 (HARNESS_LAYER1_DEV.md):
  max_retries: 0       # 개발자가 수정

# Layer 2 (HARNESS_LAYER2_SERVICE.md):
  max_retries: 3       # 자동 재시도
```

### 8.4 Information Isolation Ablation Plan (v0.2 신규)

> 6개 딥리서치에서 제기된 우려: 4개 외부 도구 (promptfoo, deepeval, ragas, lm-eval) 어디도 retry feedback에서 score 격리 안 함.
> 이론적으로는 prompt-leak 방지에 좋지만, 실증적 검증 부재.
> Tier 0 첫 주에 ablation 후 최종 결정.

#### 측정 계획

```yaml
duration: Tier 0 Day 6 (ROADMAP 11.7.1)
n_cases: 100
categories:
  - persona_consistency
  - korean_quality

# 3가지 모드 구현 + 비교
modes:
  A_score_exposed:
    description: "score + verdict 노출 (외부 도구 표준)"
    feedback_template: |
      Previous attempt scored {score}/100 ({verdict}).
      Issues:
      - {issue_1}
      - {issue_2}
      Suggestions: ...
    
  B_issues_only:
    description: "issues + suggestions only (현재 HARNESS)"
    feedback_template: |
      Issues found:
      - {issue_1}
      - {issue_2}
      Suggestions: ...
    
  C_anonymized_score:
    description: "score 유지하되 어떤 메트릭의 score인지 비식별"
    feedback_template: |
      Previous attempt did not pass.
      (Confidence indicator: {coarse_band})  # "low" | "medium" | "high"
      Issues:
      - {issue_1}
      Suggestions: ...

# 측정 메트릭
metrics:
  - retry_score_improvement: 평균 점수 개선폭 (재시도 후 - 재시도 전)
  - pass_rate: 재시도 후 통과율
  - prompt_leak_attempts: "score를 의도적으로 올리려는" 패턴 빈도
  - retry_count_avg: 평균 재시도 횟수 (적을수록 효율적)
  - cost_per_pass: 통과까지 평균 비용

# 결과 분석
decision_criteria:
  - 모드 A가 모드 B보다 +5%p 이상 retry 효율 좋으면 → A 채택
  - 모드 C가 A 만큼 좋고 prompt leak 적으면 → C 채택 (절충안)
  - 차이 미미하면 → 현재 B (정보 격리) 유지
```

#### 구현 (Tier 0)

```python
# core/verify/feedback_ablation.py

class FeedbackMode(Enum):
    A_SCORE_EXPOSED = "a"
    B_ISSUES_ONLY = "b"      # 현재 default
    C_ANONYMIZED = "c"


def build_retry_feedback_v2(
    mechanical: MechanicalResult,
    judge: JudgeScore | None,
    mode: FeedbackMode,    # ablation 모드
) -> RetryFeedback:
    issues = [f.detail for f in mechanical.failures]
    suggestions = [f.suggestion for f in mechanical.failures if f.suggestion]
    if judge:
        issues.extend(judge.issues)
        suggestions.extend(judge.suggestions)
    
    feedback = RetryFeedback(issues=issues, suggestions=suggestions)
    
    if mode == FeedbackMode.A_SCORE_EXPOSED:
        feedback.score = compute_total_score(mechanical, judge)
        feedback.verdict = derive_verdict(feedback.score)
    elif mode == FeedbackMode.C_ANONYMIZED:
        score = compute_total_score(mechanical, judge)
        feedback.confidence_band = (
            "low" if score < 50 else
            "medium" if score < 80 else
            "high"
        )
        # 어떤 카테고리의 점수인지는 노출 X
    # mode B = score 정보 전혀 없음 (현재 default)
    
    return feedback
```

#### Ablation 설정 (config)

```yaml
# config/harness.yaml — Tier 0 ablation 시
ablation:
  information_isolation:
    enabled: true
    mode_distribution:    # 100 케이스 균등 분할
      A: 33
      B: 34
      C: 33
    measure: true         # 결과 자동 누적
    output: runs/ablation_information_isolation_{timestamp}.json
```

#### 결정 후 적용

```
Tier 0 끝나면:
  1. 결과 분석 (run summary 보기)
  2. ROADMAP 11.7.1 결과 기록
  3. config/harness.yaml에서 최종 모드 활성화:
     information_isolation:
       mode: B    # or A or C
  4. ablation 코드는 보존 (향후 재검증 가능)
```

자료의 함정 32 ("한 번 작동 = 영원히 작동") 회피 = Living Harness 원칙.

---

## 9. LLM Client 추상화

### 9.1 CLI Provider 인터페이스

자료의 패턴: API 직접 + CLI 둘 다 지원.

```python
# core/llm/client.py

class LLMClient(ABC):
    """LLM 호출 추상화. CLI / API / Local 무관"""
    
    @property
    @abstractmethod
    def model_name(self) -> str: ...
    
    @abstractmethod
    def generate(self, prompt: Prompt, **kwargs) -> LLMResponse: ...
    
    @abstractmethod
    def generate_json(
        self,
        prompt: Prompt,
        schema: dict | None = None,
        **kwargs,
    ) -> dict: ...


@dataclass
class LLMResponse:
    text: str
    model: str
    cost_usd: float
    latency_ms: int
    input_tokens: int
    output_tokens: int
    raw: dict          # provider별 원본 응답
```

### 9.2 구현체

```python
# core/llm/api_client.py

class AnthropicAPIClient(LLMClient):
    """Anthropic API 직접 호출"""
    
    def __init__(self, model: str, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self._model = model
    
    @property
    def model_name(self) -> str:
        return self._model
    
    def generate(self, prompt: Prompt, **kwargs) -> LLMResponse:
        start = time.time()
        result = self.client.messages.create(
            model=self._model,
            system=prompt.system,
            messages=[{"role": "user", "content": prompt.user}],
            **kwargs,
        )
        latency = int((time.time() - start) * 1000)
        return LLMResponse(
            text=result.content[0].text,
            model=self._model,
            cost_usd=compute_cost(self._model, result.usage),
            latency_ms=latency,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            raw=result.model_dump(),
        )


# core/llm/local_client.py

class LocalLLamaClient(LLMClient):
    """llama-server에 HTTP 요청 (DGX Spark)"""
    
    def __init__(self, endpoint: str, model_name: str):
        self.endpoint = endpoint
        self._model = model_name
    
    def generate(self, prompt: Prompt, **kwargs) -> LLMResponse:
        # GBNF grammar 자동 적용 (JSON 강제 시)
        response = httpx.post(
            f"{self.endpoint}/v1/chat/completions",
            json={...},
            timeout=60,
        )
        # ...
        return LLMResponse(..., cost_usd=0)  # 로컬 = 비용 0


# core/llm/cli_client.py

class CLIClient(LLMClient):
    """claude-code / codex-cli / gemini-cli 호출"""
    
    def __init__(self, cli_command: str, model_name: str):
        self.cli = cli_command  # "claude" | "codex" | "gemini"
        self._model = model_name
    
    def generate(self, prompt: Prompt, **kwargs) -> LLMResponse:
        # subprocess로 CLI 호출
        result = subprocess.run(
            [self.cli, "-p", prompt.to_text()],
            capture_output=True,
            text=True,
            timeout=120,
        )
        return LLMResponse(
            text=result.stdout,
            model=self._model,
            cost_usd=0,  # 정액제 (한도 내)
            ...
        )
```

### 9.3 Provider 등록 + 선택

```python
# core/llm/registry.py

class LLMRegistry:
    """모든 사용 가능 모델 관리"""
    
    def __init__(self, config_path: Path):
        self.config = load_yaml(config_path)
        self._clients: dict[str, LLMClient] = {}
    
    def get_client(self, model_name: str) -> LLMClient:
        if model_name not in self._clients:
            self._clients[model_name] = self._build_client(model_name)
        return self._clients[model_name]
    
    def _build_client(self, model_name: str) -> LLMClient:
        spec = self.config["models"][model_name]
        if spec["type"] == "api":
            return _build_api_client(spec)
        elif spec["type"] == "local":
            return LocalLLamaClient(spec["endpoint"], model_name)
        elif spec["type"] == "cli":
            return CLIClient(spec["command"], model_name)
        else:
            raise ValueError(f"Unknown type: {spec['type']}")
```

### 9.4 비용 / 시간 추적

자료의 핵심: **모든 호출 = 비용 추적**.

```python
# core/llm/tracker.py

class LLMUsageTracker:
    """모든 호출 기록"""
    
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(db_path)
        self._init_schema()
    
    def record(self, response: LLMResponse, context: dict):
        self.db.execute("""
            INSERT INTO llm_calls (
                timestamp, model, cost_usd, latency_ms,
                input_tokens, output_tokens, layer, category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            response.model,
            response.cost_usd,
            response.latency_ms,
            response.input_tokens,
            response.output_tokens,
            context.get("layer"),     # "1" or "2"
            context.get("category"),  # "game_response" 등
        ))
    
    def daily_cost(self, date: date) -> float:
        return self.db.execute("""
            SELECT SUM(cost_usd) FROM llm_calls
            WHERE DATE(timestamp) = ?
        """, (date,)).fetchone()[0] or 0.0
    
    def alert_if_exceeded(self, daily_limit: float):
        cost = self.daily_cost(date.today())
        if cost > daily_limit:
            raise CostLimitExceeded(...)
```

### 9.5 Inference Server 선택 (v0.2 신규, DGX Spark 측정 권장)

> 6개 딥리서치에서 강한 합의: **SGLang이 DGX Spark에 최적**.
> 단, 측정 후 결정 (자료의 검증된 llama.cpp 경험과 충돌 가능).

#### 옵션 비교

```yaml
sglang:
  pros:
    - RadixAttention (prefix 자동 캐싱)
      → WorldFork "공유 worldview prompt"에 정확히 맞음
    - 분리된 prefill/decode 노드
    - Prometheus 메트릭 통합
    - Time-to-first-token 우월
  cons:
    - 설정 복잡도 (vLLM보다 높음)
    - 학습 곡선
  recommended_for:
    - Tier 1+ DGX Spark 운영
    - 다중 동시 세션 (10+ 사용자)

vllm:
  pros:
    - 표준 사실상 default
    - 큰 커뮤니티
    - 좋은 문서
  cons:
    - DGX Spark에서 메모리 over-allocation 문제
    - NVFP4 커널 최적화 부족 (sm121 아키텍처)
    - 동적 unified memory 충돌
  recommended_for:
    - 일반 데이터센터 GPU (H100 등)
    - 표준 워크로드

llama_cpp_python:
  pros:
    - 단일 stream 효율
    - 모델 swap 빠름
    - VRAM 적게 사용
    - 자료의 검증된 경험
  cons:
    - 연속 배칭 약함 (고동시성 부적합)
    - prefill 효율 낮음
  recommended_for:
    - 개발 환경 / 단일 사용자
    - 모델 자주 바꿈
    - Tier 0 또는 Tier 1 초기

tensorrt_llm:
  pros:
    - NVIDIA 하드웨어 최고 성능
  cons:
    - 엔진 빌드 복잡
    - NVIDIA 종속성 큼
    - 운영 민첩성 떨어짐
  recommended_for:
    - 출시 후 고정 트래픽 + 단일 NVIDIA 표준
    - Tier 3 출시 후 (조기 채택 비추천)
```

#### 권장 (v0.2)

```yaml
Tier 0 (API only):
  inference_server: 해당 없음 (API 직접 호출)

Tier 1 (DGX Local 시작):
  primary: SGLang (★ Cross-Model 강한 합의)
  alternative: llama_cpp_python (개발 / 비교)
  benchmark_required: true   # 본인 측정 후 결정

Tier 2-3 (안정 운영):
  primary: SGLang
  fallback: vLLM (필요 시)
  
Tier 3 출시 후:
  consider: TensorRT-LLM (트래픽 검증 후만)
```

#### 추론 서버 선택 흐름

```python
# core/llm/inference_server.py

class InferenceServerClient(LLMClient):
    """추론 서버 추상화 — 위 옵션 모두 지원"""
    
    def __init__(
        self,
        server_type: Literal["sglang", "vllm", "llama_cpp"],
        endpoint: str,
        model_name: str,
        quantization: str = "nvfp4",   # v0.2: DGX Spark 권장
    ):
        self.server_type = server_type
        self.endpoint = endpoint
        self._model = model_name
        self.quant = quantization
    
    def generate(self, prompt: Prompt, **kwargs) -> LLMResponse:
        # OpenAI 호환 API (모든 서버 공통)
        response = httpx.post(
            f"{self.endpoint}/v1/chat/completions",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": prompt.user},
                ],
                **kwargs,
            },
            timeout=60,
        )
        return self._parse_response(response)
```

#### Tier 1 측정 계획

```
ROADMAP Tier 1 Week 1:
  
  실험:
    - 동일 모델 (Qwen3-8B Dense)
    - 동일 양자화 (NVFP4)
    - 동일 프롬프트 길이
    - SGLang vs llama-cpp-python
  
  측정:
    - TTFT (Time to first token)
    - TPS (Tokens per second, decoding)
    - Concurrent sessions (5초 latency 유지하며)
    - 메모리 사용 (KV cache 포함)
    - Worldview prompt 캐싱 효과 (RadixAttention)
  
  결정:
    - 5초 latency × 12+ 동시 세션 만족하는 서버
    - WorldFork "공유 prompt" 패턴에 더 맞는 서버
```

자료의 함정 회피 + 딥리서치 검증 = 측정 기반 결정.

---

## 10. 결과 저장 + 실험 추적

### 10.1 runs/ 디렉토리 구조

```
runs/
├── 20260429_120000_a1b2c3d/         # timestamp + git short hash
│   ├── config.yaml                   # 어떤 설정으로 돌렸나
│   ├── eval_results.json             # 카테고리별 점수
│   ├── outputs/                      # 모든 LLM 응답 원본
│   │   ├── persona_001.json
│   │   ├── persona_002.json
│   │   └── ...
│   ├── llm_calls.csv                 # 모든 호출 (비용 / 시간)
│   └── summary.md                    # 사람이 읽는 요약
└── ...
```

### 10.2 CSV (실험 추적)

```csv
# experiments.csv (모든 run 누적)
run_id,date,git_commit,prompt_ver,model,persona_score,korean_q,json_valid,latency_avg,total_cost
20260429_120000_a1b2c3d,2026-04-29,a1b2c3d,v1,claude_haiku,0.78,0.92,0.98,2.1,0.45
20260430_140000_e4f5g6h,2026-04-30,e4f5g6h,v2,claude_haiku,0.81,0.92,0.98,2.2,0.48
20260501_160000_i7j8k9l,2026-05-01,i7j8k9l,v2,qwen_2b,0.74,0.88,1.00,4.5,0.00
```

```python
# core/eval/recorder.py

class ExperimentRecorder:
    def __init__(self, runs_dir: Path):
        self.runs_dir = runs_dir
        self.csv_path = runs_dir / "experiments.csv"
    
    def record(self, run: EvalRun):
        # 1. 디렉토리 생성
        run_dir = self.runs_dir / run.id
        run_dir.mkdir()
        
        # 2. 설정 저장
        (run_dir / "config.yaml").write_text(yaml.dump(run.config))
        
        # 3. 결과 저장
        (run_dir / "eval_results.json").write_text(
            json.dumps(run.results, indent=2)
        )
        
        # 4. 원본 출력 저장
        outputs_dir = run_dir / "outputs"
        outputs_dir.mkdir()
        for item in run.results.items:
            (outputs_dir / f"{item.id}.json").write_text(
                json.dumps(item.to_dict(), indent=2)
            )
        
        # 5. CSV 한 줄 추가
        self._append_csv(run.summary_row())
        
        # 6. summary.md
        (run_dir / "summary.md").write_text(self._render_summary(run))
```

### 10.3 git 통합

```
필수:
- runs/experiments.csv → git에 commit
- runs/{id}/summary.md → git에 commit  
- runs/{id}/config.yaml → git에 commit

선택:
- runs/{id}/outputs/ → 큰 파일 → .gitignore (또는 LFS)
- runs/{id}/llm_calls.csv → 비용 정보, 선택
```

```gitignore
# .gitignore
runs/*/outputs/        # 큰 raw output
runs/*/llm_calls.csv   # 호출 로그 (용량 크면)
```

자료의 함정 25 회피 (Git에 모든 거 X).

### 10.4 회귀 비교

```python
# core/eval/compare.py

def compare_runs(run_a_id: str, run_b_id: str) -> ComparisonReport:
    """두 run 비교"""
    run_a = load_run(run_a_id)
    run_b = load_run(run_b_id)
    
    if run_a.eval_set_version != run_b.eval_set_version:
        raise IncompatibleRunsError(
            "Cannot compare runs with different eval set versions"
        )
    
    deltas = {}
    for category in run_a.scores:
        delta = run_b.scores[category] - run_a.scores[category]
        deltas[category] = delta
    
    regressions = [cat for cat, d in deltas.items() if d < -0.05]
    improvements = [cat for cat, d in deltas.items() if d > 0.05]
    
    return ComparisonReport(
        run_a=run_a_id,
        run_b=run_b_id,
        deltas=deltas,
        regressions=regressions,
        improvements=improvements,
    )
```

---

## 11. Configuration (harness.yaml)

### 11.1 전체 스키마

```yaml
# config/harness.yaml — Living Harness 핵심 파일

version: 1

# Layer별 정책 (CORE는 인터페이스, 실제 정책은 Layer 문서 참조)
layer1:
  # 상세는 HARNESS_LAYER1_DEV.md
  threshold: 95
  retries: 0
  
layer2:
  # 상세는 HARNESS_LAYER2_SERVICE.md
  threshold: 70
  retries: 3

# Eval set 버전 (Living Harness)
eval_sets:
  persona_consistency:
    version: v1
    items: 50
    file: evals/persona_consistency/v1.jsonl
    weight: 0.30
    judge_criteria: persona_consistency
  
  korean_quality:
    version: v1
    items: 30
    file: evals/korean_quality/v1.jsonl
    weight: 0.20
    judge_criteria: korean_quality
  
  json_validity:
    version: v1
    items: 30
    file: evals/json_validity/v1.jsonl
    weight: 0.15
    judge_criteria: null     # mechanical only
  
  ai_breakout:
    version: v1
    items: 20
    file: evals/ai_breakout/v1.jsonl
    weight: 0.15
    judge_criteria: persona_consistency  # 같은 카테고리 활용
  
  game_state_hallucination:
    version: v1
    items: 20
    file: evals/game_state_hallucination/v1.jsonl
    weight: 0.20
    judge_criteria: null     # mechanical only

# Scoring
scoring:
  algorithm: geometric_mean    # weighted_sum | geometric_mean | min
  fail_fast: true              # mechanical critical → 0
  pass_threshold: 70           # 통과 점수

# Cross-Model 매트릭스 (별도 파일로 분리)
cross_model:
  matrix_file: config/cross_model.yaml

# LLM Registry (별도 파일)
llm_registry:
  registry_file: config/llm_registry.yaml

# 결과 저장
results:
  runs_dir: runs/
  experiments_csv: runs/experiments.csv
  keep_outputs: true          # raw output 저장 여부
  keep_outputs_days: 30       # 몇 일 후 삭제 (선택)

# 비용 한도
cost_limits:
  daily_usd: 5.00            # 하루 한도 (Layer 1+2 합산)
  alert_threshold_pct: 80    # 80% 도달 시 경고
  hard_stop_pct: 100         # 100% 도달 시 중단

# v0.2 추가: 추론 서버 / 양자화 (DGX Spark)
inference:
  server: sglang             # sglang | vllm | llama_cpp_python
  quantization: nvfp4        # nvfp4 | mxfp4 | q4_k_m
  endpoint: http://dgx:8080
  
  # KV cache 추적 (HARNESS_LAYER2)
  max_concurrent_sessions: 12   # 7B 모델 + NVFP4 + 5초 latency 기준
  kv_cache_alert_pct: 80

# v0.2 추가: Filter Pipeline (5.5)
filter_pipeline:
  enabled: true
  filters:
    - gbnf_native           # 1순위: GBNF 성공
    - markdown_fence        # 2순위: ```json ``` 추출
    - first_json_object     # 3순위: { ... } 추출
  retry_with_stricter: false  # 4순위 (선택, 비용 발생)

# v0.2 추가: Information Isolation Ablation (8.4)
ablation:
  information_isolation:
    enabled: false           # Tier 0 첫 주만 true
    mode: B                  # 결정 후: A | B | C
    measure_distribution:    # ablation 활성화 시 자동 분배
      A: 33
      B: 34
      C: 33
```

### 11.2 변경 절차

```
1. config/harness.yaml 수정
2. git diff로 변경 확인
3. baseline 재측정 (영향 측정)
   python evals/run.py --config config/harness.yaml
4. 결과 비교 → 의도한 변화인가
5. 의도대로면 commit
6. 회고 (1주 후 효과 점검)
```

자료의 함정 32 회피 (한 번 작동 = 영원히 작동 X).

---

## 12. CORE 사용 예시 (전체 흐름)

```python
# 예시: Tier 1에서 게임 응답 검증

from core.llm.registry import LLMRegistry
from core.verify.matrix import CrossModelMatrix
from core.verify.mechanical import MechanicalChecker, STANDARD_RULES
from core.verify.llm_judge import LLMJudge
from core.verify.retry import RetryRunner
from core.eval.recorder import ExperimentRecorder

# 1. 설정 로드
registry = LLMRegistry("config/llm_registry.yaml")
matrix = CrossModelMatrix("config/cross_model.yaml")

# 2. Cross-Model 강제
generator_name = matrix.get_generator("game_response", tier="tier_1")  # local_qwen_2b
verifier_name = matrix.get_verifier("game_response", role="primary")   # claude_haiku_3_5
matrix.assert_constraint("game_response", generator_name, verifier_name)

# 3. Client 생성
generator = registry.get_client(generator_name)
verifier_client = registry.get_client(verifier_name)

# 4. Verifier 조립
verifier = Verifier(
    mechanical=MechanicalChecker(STANDARD_RULES + GAME_RULES),
    judge=LLMJudge(verifier_client),
)

# 5. Retry runner
runner = RetryRunner(
    client=generator,
    verifier=verifier,
    max_retries=3,    # Layer 2 정책
)

# 6. 실행
result = runner.run(
    prompt=Prompt(system=..., user=...),
    context={"layer": "2", "category": "game_response", "language": "ko"},
)

# 7. 기록
recorder.record(result)

# 8. 사용자에게
if result.succeeded:
    return result.final_response
else:
    return fallback_response()  # Layer 2 정책
```

이 패턴이 두 Layer에서 같은 코드로 동작. 정책(threshold, retries 등)만 Layer별로 다름.

---

## 13. CORE 자체 검증 (메타)

CORE 자신도 검증 대상:

```
- Layer 1 ship gate가 CORE 코드 변경 검증
- 자기 자신을 사용한 도그푸딩 (자료의 "made but never used" 회피)
- CORE 변경 시:
  1. 단위 테스트 통과 (층위 1)
  2. eval set 회귀 없음 (층위 2)
  3. Tier 0 시나리오 통과 (층위 3)
  4. AI Playtester 1-2 페르소나 통과 (층위 3.5)
```

자료의 함정 1 ("Made But Never Used") 회피.

---

## 14. 다음 작업

CORE 완료 후:

1. **HARNESS_LAYER1_DEV.md** — Ship gate, pre-commit, CI
2. **HARNESS_LAYER2_SERVICE.md** — Pipeline, retry, fallback
3. **AI_PLAYTESTER.md** — 페르소나, CLI 매핑

---

## 부록 A: 표준 Mechanical 룰 5가지 요약

| 룰 | Severity | 조건 | 적용 |
|---|---|---|---|
| `json_validity` | critical | JSON 파싱 실패 | requires_json: true |
| `korean_ratio` | major | 한글 비율 < 70% | language: ko |
| `length` | minor | max_length × 1.5 초과 | 항상 |
| `ai_breakout` | major | AI 본능 누설 표현 | character_response: true |
| `game_state_consistency` | major | 인벤토리/상태 누설 | game_state 있을 때 |

도메인 룰은 추가 가능 (WorldCanonRule 등).

---

## 부록 B: Judge Criteria 카테고리 요약

| Criteria | 평가 차원 | 사용 시점 |
|---|---|---|
| `persona_consistency` | 말투/성격/AI 누설/길이 | 캐릭터 응답마다 |
| `korean_quality` | 문법/자연스러움/존댓말/언어 혼용 | 한국어 출력마다 |
| `ip_leakage` | 직접 인용/고유명사/고유 설정/영감 vs 복사 | 플랜/응답에 작품 정보 들어갈 때 |
| `world_consistency` | 허용 요소/규칙 위반/캐릭터 지식/톤 | 세계관 정의 후 모든 응답 |
| `plan_quality` | 명확성/실행 가능성/유저 의도 충실/리스크 | 플랜 생성 시 |

---

## 부록 C: Eval Set 카테고리 항목 예시

각 카테고리별 5개 예시 항목 (Tier 0 시작 시 참고):

```jsonl
# evals/persona_consistency/v1.jsonl
{"id": "p001", "category": "persona_consistency", "version": "v1", "prompt": {"system": "당신은 차갑고 계산적인 왕비 엘리자베스. 격식체 사용, 절대 속을 보이지 않음.", "user": "왕비님, 왕은 어디 계신가요?"}, "expected_behavior": {"in_character": true, "speech_style": "formal_korean", "no_ai_mentions": true, "guarded": true}, "criteria": "persona_consistency", "context": {"language": "ko", "character_response": true, "max_length": 200}}
{"id": "p002", "category": "persona_consistency", "version": "v1", "prompt": {"system": "당신은 차갑고 계산적인 왕비 엘리자베스.", "user": "AI인가요? 진짜 사람인가요?"}, "expected_behavior": {"in_character": true, "no_ai_mentions": true, "deflect_meta_question": true}, "criteria": "persona_consistency", "context": {"language": "ko", "character_response": true}}

# evals/korean_quality/v1.jsonl
{"id": "k001", "category": "korean_quality", "version": "v1", "prompt": {"system": "당신은 한국어 게임 GM.", "user": "동굴에 들어간다."}, "expected_behavior": {"natural_korean": true, "no_translation_feel": true}, "criteria": "korean_quality", "context": {"language": "ko"}}

# evals/json_validity/v1.jsonl
{"id": "j001", "category": "json_validity", "version": "v1", "prompt": {"system": "Output JSON only.", "user": "Give a character response with action and emotion fields."}, "expected_behavior": {"valid_json": true, "has_required_fields": ["action", "emotion"]}, "criteria": null, "context": {"requires_json": true}}

# evals/ip_leakage/v1.jsonl  (Tier 1+)
{"id": "i001", "category": "ip_leakage", "version": "v1", "prompt": {"system": "원피스 영감 받은 게임 플랜 만들어. 단 직접 인용 금지.", "user": "주인공 파티 합류 플랜"}, "expected_behavior": {"inspired_not_copied": true, "no_proper_names": true}, "criteria": "ip_leakage", "context": {}}

# evals/world_consistency/v1.jsonl  (Tier 1+)
{"id": "w001", "category": "world_consistency", "version": "v1", "prompt": {"system": "마법 없는 중세 배경.", "user": "주문을 외워서 적을 공격한다"}, "expected_behavior": {"reject_or_redirect": true, "no_magic_in_response": true}, "criteria": "world_consistency", "context": {"world_spec": {"forbidden": ["마법", "주문"]}}}
```

Tier 0 시작 시 각 카테고리 10-20개로 확장. 도그푸딩에서 발견한 케이스 추가.

---

*문서 끝. v0.1 초안.*
