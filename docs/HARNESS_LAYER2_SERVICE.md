# HARNESS_LAYER2_SERVICE — 서비스 하네스

> WorldFork **사용자 게임 플레이 시** (런타임) 검증 시스템.
> 매 LLM 응답마다 자동 검증, 통과 시 사용자에게 출력.
>
> 작성: 2026-04-29
> 상태: 초안 v0.1
> 의존: ROADMAP.md, HARNESS_CORE.md (먼저 읽기)
> 관련: HARNESS_LAYER1_DEV.md, AI_PLAYTESTER.md

---

## 0. 이 문서의 목적과 범위

### Layer 2란

**완성된 게임이 사용자 입력을 처리할 때 작동하는 검증 시스템.**

목적:
- 응답 품질 보장 (사용자에게 나쁜 응답 안 가게)
- 비용 / latency 균형 (실시간 게임이라 빨라야 함)
- 자동 복구 (재시도, fallback)
- 정보 격리 (점수 누설 차단)

CORE의 검증 엔진 + Layer 2 정책 + 게임 파이프라인 = 서비스 하네스.

### 다루는 것

- 게임 파이프라인 8단계 (Interview → Plan → Verify → Game Loop)
- Retry policy (max 3, 정보 격리 강제)
- Fallback chain (Local → API → User)
- Error 4-tier 분류
- Layer 2 고유 정책 (threshold 70, retries 3)
- 사용자 비용 표시
- Empty state / 사용자 흐름

### 다루지 않는 것

- 개발 시 검증 → `HARNESS_LAYER1_DEV.md`
- AI Playtester → `AI_PLAYTESTER.md`
- 검증 엔진 자체 → `HARNESS_CORE.md`
- 웹 UI 디자인 (별도, Tier 2)

---

## 1. Layer 2 정책 요약

| 항목 | Layer 2 (서비스) | 이유 |
|---|---|---|
| **Threshold** | 70+ | 게임 응답은 약간 관대 (재미 우선) |
| **Retries** | 3 | 자동 재시도 (사용자 노출 X) |
| **검증 범위** | 빠른 일부만 (Mechanical 우선) | 실시간성 |
| **실패 시** | 재생성 → fallback | 사용자에게 끊김 없게 |
| **비용 한도** | per-request 한도 | 비용 폭발 방지 |
| **속도** | 5초 이내 우선 | 사용자 이탈 방지 |

`config/harness.yaml`:

```yaml
layer2:
  threshold: 70
  retries: 3
  eval_scope: mechanical_priority   # Mechanical 우선
  on_fail: regenerate_then_fallback
  
  cost_per_request:
    soft_limit_usd: 0.10           # 0.10 도달 시 경고 로그
    hard_limit_usd: 0.50           # 0.50 도달 시 즉시 fallback
  
  latency:
    target_p50_seconds: 3.0        # 50% 사용자가 3초 이내
    target_p95_seconds: 8.0        # 95% 사용자가 8초 이내
    timeout_seconds: 30.0          # 30초 = 강제 fallback
  
  retry_strategy:
    same_model_retries: 1           # 같은 모델 재시도 1회
    cross_model_retries: 1           # 다른 모델 시도 1회
    api_fallback_retries: 1         # API fallback 1회
  
  empty_state:
    show_demo_scenario: true        # 첫 사용자에게 demo
    onboarding_max_seconds: 300     # 5분 안에 게임 시작
```

---

## 2. 게임 파이프라인 8단계

자료의 AutoDev 파이프라인 패턴을 WorldFork에 적용.

### 2.1 전체 흐름

```
[사용자 입력]
   ↓
[1. Interview Agent]      (모호하면 질문, 명확하면 통과)
   ↓
[2. Planning Agent]        (작품 검색 + 게임 플랜 생성)
   ↓
[3. Plan Verify]           (Cross-Model 검증, IP leakage 등)
   ↓
[4. Plan Review]           (사용자 검토 + 자연어 수정)
   ↓
[5. Agent Selection]       (게임 LLM 선택, Tier별 다름)
   ↓
[6. Verify Agent Selection] (Verify LLM, Cross-Model 강제)
   ↓
[7. Game Loop]             (검증 + 재시도 + fallback)
   ↓
[8. Complete / Save]       (저장, 다음 세션 준비)
```

### 2.2 단계별 상세

#### Stage 1: Interview Agent

```python
# service/pipeline/interview.py

class InterviewAgent:
    """모호한 입력 → 질문, 명확한 입력 → 통과"""
    
    def __init__(self, registry: LLMRegistry):
        self.classifier = registry.get_client("claude_haiku_3_5")  # 빠르고 저렴
    
    def run(self, user_input: str) -> InterviewResult:
        # 1. 의도 분류
        intent = self._classify_intent(user_input)
        
        if intent == "clear":
            # 명확한 입력 → 다음 단계
            return InterviewResult(skip=True, parsed_input=user_input)
        
        # 2. 질문 생성 (3-5개)
        questions = self._generate_questions(user_input)
        return InterviewResult(
            skip=False,
            questions=questions,
            wait_for_user=True,
        )
    
    def _classify_intent(self, user_input: str) -> Literal["clear", "ambiguous"]:
        """15단어 미만 + 핵심 동사/스택 없음 → ambiguous"""
        if len(user_input.split()) < 15:
            return "ambiguous"
        
        # 키워드 휴리스틱
        has_work_name = bool(re.search(r"[가-힣]+|[A-Z]\w+", user_input))
        has_intent_word = any(w in user_input for w in [
            "하고싶", "플레이", "되고싶", "살아보", "체험",
        ])
        
        if has_work_name and has_intent_word:
            return "clear"
        return "ambiguous"
```

질문 형식 (5-section prompt 사용):

```python
INTERVIEW_PROMPT = """
# IDENTITY
You are a game configuration interviewer for WorldFork.

# TASK
The user gave ambiguous input. Generate 3-5 multiple-choice questions
to clarify their game preferences.

# SPEC
Questions should cover (when relevant):
- 작품/세계관 (which work?)
- 진입 방식 (protagonist / sidekick / extra / antagonist / regression)
- 플레이 스타일 (combat / social / exploration / puzzle / political)
- 시간대 (early / middle / late / post-canon)
- 자유도 (canon-faithful / branching / completely-free)

# OUTPUT FORMAT
JSON only:
{{
  "questions": [
    {{
      "id": "entry_point",
      "text": "어떤 시점으로 들어가고 싶으세요?",
      "options": ["주인공", "조연", "엑스트라", "적대 세력", "회귀"],
    }},
    ...
  ]
}}

# EXAMPLES
{few_shot}

# USER INPUT
{user_input}
"""
```

#### Stage 2: Planning Agent

```python
# service/pipeline/planning.py

class PlanningAgent:
    """검색 + 플랜 생성"""
    
    def __init__(self, registry: LLMRegistry, search: WebSearch):
        self.drafter = registry.get_client("claude_opus")
        self.search = search
    
    def run(
        self,
        work_name: str,
        user_preferences: dict,
    ) -> PlanResult:
        # 1. 웹 검색 (병렬)
        search_results = self.search.search_parallel(
            sources=["wiki", "namuwiki", "fan_community"],
            query=work_name,
        )
        
        # 2. 정보 분류 (공식 / 팬 해석 / 팬픽)
        classified = classify_sources(search_results)
        
        # 3. IP Masking 적용
        masked = apply_ip_masking(classified)
        
        # 4. 5-section prompt로 플랜 생성
        prompt = self._build_planning_prompt(masked, user_preferences)
        plan = self.drafter.generate_json(prompt, schema=PLAN_SCHEMA)
        
        return PlanResult(
            plan=plan,
            sources_used=classified.summary(),
            ip_masking_applied=True,
            cost=plan.cost_usd,
        )
```

#### Stage 3: Plan Verify (Cross-Model)

```python
# service/pipeline/plan_verify.py

class PlanVerifyAgent:
    """Cross-Model로 플랜 검증 (Debate Mode 적용)"""
    
    def __init__(self, registry: LLMRegistry):
        # CORE의 DebateJudge 활용
        self.judge = DebateJudge(
            drafter=registry.get_client("claude_opus"),         # 1차
            challenger=registry.get_client("gemini_pro"),       # ★ Drafter reasoning 못 봄
            quality_checker=registry.get_client("gpt_4o"),
        )
    
    def verify(
        self,
        plan: dict,
        original_search_results: dict,
        user_preferences: dict,
    ) -> PlanVerifyResult:
        # 검증 항목:
        # 1. IP leakage (저작권 누출)
        # 2. World consistency (세계관 일관성)
        # 3. User preference match (사용자 의도 충실)
        # 4. Plan quality (실행 가능성)
        
        criteria = JudgeCriteria.compose([
            "ip_leakage",
            "world_consistency",
            "user_preference_match",
            "plan_quality",
        ])
        
        debate_result = self.judge.evaluate(
            target_response=json.dumps(plan),
            criteria=criteria,
            context={
                "search_results": original_search_results,
                "user_preferences": user_preferences,
            },
        )
        
        return PlanVerifyResult(
            score=debate_result.final_score.score,
            verdict=debate_result.final_score.verdict,
            ip_leakage_score=extract_subscore(debate_result, "ip_leakage"),
            issues=debate_result.final_score.issues,
            suggestions=debate_result.final_score.suggestions,
        )
```

#### Stage 4: Plan Review (사용자 개입)

```python
# service/pipeline/plan_review.py

class PlanReviewSession:
    """사용자가 플랜 검토 / 수정"""
    
    def __init__(self, plan: dict, verify_result: PlanVerifyResult):
        self.plan = plan
        self.verify_result = verify_result
        self.thread = ConversationThread()
    
    def show_to_user(self) -> str:
        """사용자에게 플랜 표시 (저작권 경고 포함)"""
        return format_plan_for_user(
            plan=self.plan,
            verify_score=self.verify_result.score,
            ip_warnings=self.verify_result.ip_warnings,
        )
    
    def handle_user_edit(self, user_message: str) -> EditResult:
        """자연어로 수정 요청 처리"""
        # 1. Intent 분류 (modify / approve / clarify / cancel)
        intent = self._classify_edit_intent(user_message)
        
        if intent == "approve":
            return EditResult(approved=True, plan=self.plan)
        
        if intent == "cancel":
            return EditResult(cancelled=True)
        
        # 2. modify intent
        modified_plan = self._apply_modification(self.plan, user_message)
        
        # 3. Diff 계산
        diff = compute_diff(self.plan, modified_plan)
        
        # 4. 재검증 (Cross-Model)
        new_verify = PlanVerifyAgent(registry).verify(
            modified_plan, original_search_results, user_preferences
        )
        
        # 5. 사용자에게 diff + 재검증 결과 보여줌
        return EditResult(
            modified=True,
            new_plan=modified_plan,
            diff=diff,
            new_verify=new_verify,
        )
```

#### Stage 5: Agent Selection

```python
# service/pipeline/agent_selection.py

class AgentSelector:
    """Tier + cost preference 따라 게임 LLM 선택"""
    
    def __init__(self, registry: LLMRegistry, matrix: CrossModelMatrix):
        self.registry = registry
        self.matrix = matrix
    
    def select_game_llm(
        self,
        tier: str,
        cost_preference: Literal["cheap", "balanced", "premium"],
    ) -> LLMClient:
        # Tier별 후보
        candidates = self.matrix.get_generator_candidates("game_response", tier)
        
        # cost preference 적용
        if cost_preference == "cheap":
            # 가장 저렴 (보통 local_qwen 또는 haiku)
            return self.registry.get_client(candidates[0])
        elif cost_preference == "premium":
            # 가장 좋은 품질 (보통 opus)
            return self.registry.get_client(candidates[-1])
        else:
            # 중간 (보통 sonnet 또는 4b 모델)
            return self.registry.get_client(candidates[len(candidates) // 2])
```

#### Stage 6: Verify Agent Selection

```python
# service/pipeline/verify_selection.py

class VerifyAgentSelector:
    """Cross-Model 강제: 게임 LLM과 다른 모델"""
    
    def select_verify_llm(
        self,
        game_llm: LLMClient,
        category: str,
    ) -> LLMClient:
        # 매트릭스에서 verifier 후보
        verifier_name = self.matrix.get_verifier(
            category=category,
            role="primary",
        )
        
        # 게임 LLM과 같으면 다른 거 선택
        if verifier_name == game_llm.model_name:
            verifier_name = self.matrix.get_verifier(
                category=category,
                role="challenger",  # primary가 같으면 challenger 사용
            )
        
        # 그래도 같으면 에러
        if verifier_name == game_llm.model_name:
            raise CrossModelError(
                f"No verifier different from game LLM '{game_llm.model_name}'"
            )
        
        return self.registry.get_client(verifier_name)
```

#### Stage 7: Game Loop (핵심)

```python
# service/pipeline/game_loop.py

class GameLoop:
    """매 사용자 행동마다 작동하는 검증 루프"""
    
    def __init__(
        self,
        game_llm: LLMClient,
        verify_llm: LLMClient,
        config: Layer2Config,
    ):
        self.game = game_llm
        self.verify = verify_llm
        self.config = config
        
        # CORE의 RetryRunner 활용
        self.runner = RetryRunner(
            client=game_llm,
            verifier=Verifier(
                mechanical=MechanicalChecker(STANDARD_RULES + GAME_RULES),
                judge=LLMJudge(verify_llm),
            ),
            max_retries=config.retries,  # 3
        )
        
        # Fallback chain
        self.fallback = FallbackChain(config.fallback_chain)
        
        # 비용 추적
        self.cost_tracker = CostTracker()
    
    def process_action(
        self,
        user_action: str,
        game_state: GameState,
    ) -> GameLoopResult:
        # 1. 행동 분류 (룰 기반, LLM 호출 없음)
        action_type = classify_action(user_action, game_state)
        
        # 2. 게임 로직 처리 (코드, LLM 호출 없음)
        logic_result = process_game_logic(action_type, game_state)
        
        # 3. LLM 묘사 생성 (검증 포함)
        prompt = build_gm_prompt(logic_result, game_state)
        
        # 비용 한도 체크
        if self.cost_tracker.session_cost() > self.config.cost_per_request.hard_limit:
            return self._handle_cost_exceeded(game_state)
        
        # 4. Retry runner 실행
        retry_result = self.runner.run(
            prompt=prompt,
            context={
                "layer": "2",
                "category": "game_response",
                "language": "ko",
                "character_response": True,
                "game_state": game_state,
            },
        )
        
        # 5. 통과 → 사용자에게
        if retry_result.succeeded:
            return GameLoopResult(
                response=retry_result.final_response,
                game_state=apply_logic(game_state, logic_result),
                attempts=len(retry_result.attempts),
                cost=self.cost_tracker.last_request_cost(),
            )
        
        # 6. 모두 실패 → Fallback
        return self._fallback(prompt, game_state)
```

#### Stage 8: Complete / Save

```python
# service/pipeline/complete.py

class CompletionHandler:
    """게임 종료 / 저장"""
    
    def on_save(self, game_state: GameState) -> SaveResult:
        # 1. 영속화 (SQLite)
        save_id = self.db.save(game_state)
        
        # 2. 컨텍스트 요약 (다음 세션용)
        summary = self._summarize_session(game_state)
        
        return SaveResult(save_id=save_id, summary=summary)
    
    def on_complete(self, game_state: GameState) -> None:
        # 1. 결말 분류 (true / partial / fail)
        ending = classify_ending(game_state)
        
        # 2. 사용자에게 결말 표시
        # 3. 통계 기록 (정성 피드백 옵션)
        # 4. AI Playtester eval 시드로 누적 (interesting case면)
```

---

## 3. Retry Policy (정보 격리 강제)

### 3.1 3단계 재시도 전략

```python
# service/retry/strategy.py

class Layer2RetryStrategy:
    """3단계 재시도. 각 단계마다 다른 접근."""
    
    def __init__(self, registry: LLMRegistry, matrix: CrossModelMatrix):
        self.registry = registry
        self.matrix = matrix
    
    def get_retry_plan(
        self,
        original_model: str,
        category: str,
        attempt: int,
    ) -> RetryPlan:
        """attempt에 따라 다른 전략"""
        
        if attempt == 1:
            # 같은 모델 재시도 (issues 피드백)
            return RetryPlan(
                model=original_model,
                strategy="same_model_with_feedback",
                temperature_adjust=0.1,  # 약간 다양성 추가
            )
        
        elif attempt == 2:
            # 다른 모델로 시도 (Cross-Model)
            alt_model = self.matrix.get_alternative(category, exclude=[original_model])
            return RetryPlan(
                model=alt_model,
                strategy="cross_model_retry",
                temperature_adjust=0,
            )
        
        elif attempt == 3:
            # 마지막 시도: API fallback (로컬이었으면)
            if self.registry.is_local(original_model):
                return RetryPlan(
                    model="claude_haiku_3_5",  # 빠르고 저렴한 API
                    strategy="api_fallback",
                    temperature_adjust=0,
                )
            else:
                # 이미 API였으면 더 큰 API
                return RetryPlan(
                    model="claude_sonnet",
                    strategy="api_premium_fallback",
                    temperature_adjust=0,
                )
```

### 3.2 정보 격리 강제 (CORE 패턴)

CORE의 Prompt.with_retry_feedback() 그대로 사용. 각 재시도마다:

```python
def execute_retry(
    original_prompt: Prompt,
    previous_attempts: list[VerifyAttempt],
    plan: RetryPlan,
) -> Prompt:
    """재시도 prompt 구성"""
    
    # 1. 마지막 attempt의 feedback 추출
    last_attempt = previous_attempts[-1]
    feedback = build_retry_feedback(
        mechanical=last_attempt.result.mechanical,
        judge=last_attempt.result.judge,
    )
    # ★ feedback에는 score/verdict 절대 없음 (CORE에서 코드 레벨 차단)
    
    # 2. 새 모델 / 같은 모델 prompt 구성
    if plan.strategy == "cross_model_retry":
        # 다른 모델은 자기 prompt 스타일 선호 가능
        # → 5-section 그대로 + feedback만 추가
        retry_prompt = original_prompt.with_retry_feedback(feedback)
    elif plan.strategy == "api_fallback":
        # API는 더 강한 instruction 가능
        retry_prompt = original_prompt.with_retry_feedback(
            feedback,
            extra_instruction="The previous attempts failed. Be especially careful."
        )
    else:
        retry_prompt = original_prompt.with_retry_feedback(feedback)
    
    return retry_prompt
```

### 3.3 재시도 한도

```yaml
# config/harness.yaml
layer2:
  retries: 3                    # 총 3회
  
  # 단계별 분배
  retry_strategy:
    same_model_retries: 1
    cross_model_retries: 1
    api_fallback_retries: 1
  
  # 비용 제한
  retry_cost_limit_usd: 0.30    # 재시도 합계 비용
  
  # 시간 제한
  retry_total_timeout_seconds: 20.0
```

---

## 4. Fallback Chain

### 4.1 5단계 Fallback

```
사용자 입력
   ↓
[1] Local LLM (DGX Qwen)        ← 정상 케이스
   ↓ (실패)
[2] Local LLM 재시도 (다른 시드)
   ↓ (실패)
[3] API Haiku (저렴)
   ↓ (실패)
[4] API Sonnet (더 강함)
   ↓ (실패)
[5] 사용자에게 사과 + 직접 입력 안내
```

자료의 "Anti-Pattern 7: 외부 의존성 = 진입 장벽" 회피하면서 안정성 확보.

### 4.2 구현

```python
# service/fallback/chain.py

class FallbackChain:
    """단계적 fallback. 비용 / 안정성 균형."""
    
    def __init__(self, config: FallbackConfig):
        self.steps = self._build_chain(config)
    
    def _build_chain(self, config) -> list[FallbackStep]:
        """Tier별로 다른 chain"""
        if config.tier == "1":
            # Tier 1: 로컬 우선
            return [
                FallbackStep(model="local_qwen_2b", retries=2),
                FallbackStep(model="claude_haiku_3_5", retries=1),
                FallbackStep(model="claude_sonnet", retries=1),
                FallbackStep(model="USER_REPORT", retries=0),
            ]
        elif config.tier == "0":
            # Tier 0: API만
            return [
                FallbackStep(model="claude_haiku_3_5", retries=2),
                FallbackStep(model="claude_sonnet", retries=1),
                FallbackStep(model="USER_REPORT", retries=0),
            ]
        else:
            return self._default_chain()
    
    def execute(
        self,
        prompt: Prompt,
        verifier: Verifier,
        context: dict,
    ) -> FallbackResult:
        attempts = []
        total_cost = 0.0
        
        for step in self.steps:
            if step.model == "USER_REPORT":
                # 모든 모델 실패
                return FallbackResult(
                    succeeded=False,
                    user_message=self._build_failure_message(attempts),
                    total_cost=total_cost,
                )
            
            # 모델로 시도
            client = self.registry.get_client(step.model)
            result = self._try_with_retries(client, prompt, verifier, step.retries)
            
            attempts.append(result)
            total_cost += result.cost
            
            if result.succeeded:
                return FallbackResult(
                    succeeded=True,
                    final_response=result.response,
                    fallback_step=step.model,
                    attempts=attempts,
                    total_cost=total_cost,
                )
            
            # 비용 한도 체크
            if total_cost > self.config.fallback_cost_limit:
                return FallbackResult(
                    succeeded=False,
                    user_message="Cost limit reached. Try simpler input.",
                    total_cost=total_cost,
                )
        
        # 모든 단계 실패
        return FallbackResult(
            succeeded=False,
            user_message=self._build_failure_message(attempts),
            total_cost=total_cost,
        )
```

### 4.3 Fallback 시 사용자 메시지

```python
def build_failure_message(attempts: list[Attempt]) -> str:
    """모든 모델 실패 시 사용자에게 보여줄 메시지"""
    return f"""
    죄송합니다. 응답을 생성하는 데 어려움이 있습니다.
    
    가능한 해결 방법:
    1. 입력을 더 단순하게 다시 시도
    2. 다른 행동 시도
    3. 게임 저장 후 잠시 후 재시도
    
    [기술적 정보 (선택)]
    시도된 모델: {len(attempts)}개
    각 모델 실패 이유: ...
    
    [버그 리포트 채널]
    Discord: ...
    GitHub Issue: ...
    """
```

자료의 패턴: **정직한 한계 명시**. "AI 자동화" 대신 "어려움이 있습니다" + 대안 제시.

### 4.4 Fallback 통계 추적

```python
# service/monitoring/fallback_metrics.py

class FallbackMetrics:
    """Fallback 사용 패턴 추적 (개선 신호)"""
    
    def record(self, result: FallbackResult, context: dict):
        self.db.execute("""
            INSERT INTO fallback_events (
                timestamp, succeeded, fallback_step, total_cost,
                category, n_attempts
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (...))
    
    def daily_report(self) -> str:
        """일일 fallback 리포트"""
        return f"""
        Fallback 통계 (오늘):
        ─────────────────────────
        총 요청:           {self.total_requests}
        Fallback 발생:     {self.fallback_count} ({self.fallback_rate:.1%})
        
        단계별 도달:
          Local Qwen 통과:        {self.local_pass:.1%}
          API Haiku 도달:         {self.api_haiku:.1%}
          API Sonnet 도달:        {self.api_sonnet:.1%}
          USER_REPORT:            {self.user_report:.1%}
        
        평균 fallback 비용:     ${self.avg_fallback_cost:.3f}
        """
```

**fallback rate가 5% 이상**이면 회귀 신호 → 조사.

---

## 5. Error 4-Tier 분류

자료의 패턴: 재시도 가능 여부 / 어디까지 거슬러 올라가야 하나로 분류.

### 5.1 Tier 분류

```python
# service/error/tiers.py

class ErrorTier(Enum):
    """에러 tier — 어디로 거슬러 올라가야 하나"""
    
    TIER_1 = "retry_same_model"       # 같은 모델 재시도
    TIER_2 = "retry_cross_model"      # 다른 모델 시도
    TIER_3 = "replan"                  # 플랜 재생성
    TIER_4 = "user_intervention"      # 사용자 개입 필요


@dataclass
class ClassifiedError:
    tier: ErrorTier
    original_error: Exception
    user_message: str | None
    technical_detail: str
    recovery_action: str
```

### 5.2 분류 룰

```python
# service/error/classifier.py

class ErrorClassifier:
    """에러를 tier로 분류"""
    
    def classify(self, error: Exception, context: dict) -> ClassifiedError:
        # Tier 1: 같은 모델 재시도 가능
        if isinstance(error, (
            JsonParseError,
            LengthError,
            FormatError,
        )):
            return ClassifiedError(
                tier=ErrorTier.TIER_1,
                original_error=error,
                user_message=None,  # 사용자에게 안 보임
                technical_detail=str(error),
                recovery_action="retry_with_feedback",
            )
        
        # Tier 2: 다른 모델 시도
        if isinstance(error, (
            PersonaConsistencyError,
            KoreanQualityError,
            CharacterBreakError,
        )):
            return ClassifiedError(
                tier=ErrorTier.TIER_2,
                original_error=error,
                user_message=None,
                technical_detail=str(error),
                recovery_action="cross_model_retry",
            )
        
        # Tier 3: 플랜 재검토 필요
        if isinstance(error, (
            WorldConsistencyError,    # 세계관 위반 반복
            IPLeakageDetected,        # 저작권 누출
            PlanIncompatibleError,    # 플랜 자체 문제
        )):
            return ClassifiedError(
                tier=ErrorTier.TIER_3,
                original_error=error,
                user_message="플랜에 문제가 발견되어 재구성합니다.",
                technical_detail=str(error),
                recovery_action="replan",
            )
        
        # Tier 4: 사용자 개입
        if isinstance(error, (
            CostLimitExceeded,
            TimeoutError,
            ModelUnavailableError,
        )):
            return ClassifiedError(
                tier=ErrorTier.TIER_4,
                original_error=error,
                user_message=self._build_user_message(error),
                technical_detail=str(error),
                recovery_action="user_decide",
            )
        
        # Unknown → Tier 4 (안전한 fallback)
        return ClassifiedError(
            tier=ErrorTier.TIER_4,
            original_error=error,
            user_message="예상치 못한 오류입니다.",
            technical_detail=str(error),
            recovery_action="user_decide",
        )
```

### 5.3 Tier별 처리

```python
# service/error/handler.py

class ErrorHandler:
    """Tier에 따라 다른 복구 동작"""
    
    def handle(self, classified: ClassifiedError, context: dict) -> RecoveryAction:
        if classified.tier == ErrorTier.TIER_1:
            # 같은 모델 재시도 (Layer 2 retry strategy)
            return RecoveryAction.RETRY_SAME
        
        elif classified.tier == ErrorTier.TIER_2:
            # Cross-model 시도
            return RecoveryAction.RETRY_CROSS_MODEL
        
        elif classified.tier == ErrorTier.TIER_3:
            # 플랜 재검토 (Stage 2-3 다시)
            return RecoveryAction.REPLAN
        
        elif classified.tier == ErrorTier.TIER_4:
            # 사용자에게 보고
            self._show_user_message(classified)
            return RecoveryAction.USER_INTERVENTION
```

### 5.4 Re-plan Outer Loop

자료의 AutoDev 패턴 그대로:

```python
# service/pipeline/replan_loop.py

class ReplanLoop:
    """Tier 3 에러 발생 시 플랜 재생성"""
    
    MAX_REPLAN_ATTEMPTS = 2       # 자료의 패턴
    
    def run(
        self,
        original_plan: dict,
        error: ClassifiedError,
        user_preferences: dict,
    ) -> ReplanResult:
        for attempt in range(self.MAX_REPLAN_ATTEMPTS):
            # 1. 에러 정보로 플랜 재생성
            new_plan = self._regenerate_plan(
                original_plan=original_plan,
                error_feedback=error.technical_detail,
                user_preferences=user_preferences,
            )
            
            # 2. 재검증 (Cross-Model)
            verify_result = PlanVerifyAgent(...).verify(new_plan, ...)
            
            if verify_result.verdict == "pass":
                return ReplanResult(
                    succeeded=True,
                    new_plan=new_plan,
                    replan_attempts=attempt + 1,
                )
        
        # Max replan 초과 → Tier 4
        return ReplanResult(
            succeeded=False,
            user_message="플랜 재구성에 실패했습니다. 다른 작품으로 시도해보세요.",
        )
```

---

## 6. 비용 / Latency 추적 (Layer 2)

### 6.1 사용자 노출

자료의 패턴: **비용 명시 = 사용자 신뢰**.

```
게임 진행 중 UI에 표시:
  
  ┌──────────────────────────────────────┐
  │  현재 세션 비용: $0.024 / $0.50       │
  │  마지막 응답: 2.3초 / $0.0008         │
  │  ████░░░░░░ 4.8% 사용                 │
  └──────────────────────────────────────┘
```

```python
# service/monitoring/user_display.py

@dataclass
class UserCostDisplay:
    session_cost: float
    session_limit: float
    last_request_cost: float
    last_request_latency_ms: int
    
    @property
    def percentage_used(self) -> float:
        return (self.session_cost / self.session_limit) * 100
    
    def to_widget_data(self) -> dict:
        return {
            "session_cost_usd": round(self.session_cost, 3),
            "session_limit_usd": round(self.session_limit, 2),
            "percentage": round(self.percentage_used, 1),
            "last_latency_ms": self.last_request_latency_ms,
            "warning": self.percentage_used > 80,
        }
```

### 6.2 Per-Request 한도

```python
# service/cost/limits.py

class CostLimiter:
    """요청별 / 세션별 비용 한도"""
    
    def __init__(self, config: Layer2Config):
        self.config = config
        self.session_costs: dict[str, float] = {}  # session_id → cumulative
    
    def check_can_proceed(
        self,
        session_id: str,
        estimated_cost: float,
    ) -> CostCheckResult:
        current = self.session_costs.get(session_id, 0.0)
        projected = current + estimated_cost
        
        # Hard limit (즉시 차단)
        if projected > self.config.cost_per_request.hard_limit_usd:
            return CostCheckResult(
                can_proceed=False,
                reason="hard_limit_exceeded",
                action="fallback_to_cheap_model",
            )
        
        # Soft limit (경고)
        if projected > self.config.cost_per_request.soft_limit_usd:
            return CostCheckResult(
                can_proceed=True,
                reason="soft_limit_warning",
                action="log_warning",
            )
        
        return CostCheckResult(can_proceed=True)
    
    def record(self, session_id: str, cost: float):
        self.session_costs[session_id] = (
            self.session_costs.get(session_id, 0.0) + cost
        )
```

### 6.3 Latency 모니터링

```python
# service/monitoring/latency.py

class LatencyTracker:
    """P50, P95, P99 추적"""
    
    def __init__(self, config: Layer2Config):
        self.target_p50 = config.latency.target_p50_seconds
        self.target_p95 = config.latency.target_p95_seconds
        self.timeout = config.latency.timeout_seconds
        self.buffer: list[float] = []  # 최근 1000개
    
    def record(self, latency_seconds: float):
        self.buffer.append(latency_seconds)
        if len(self.buffer) > 1000:
            self.buffer.pop(0)
    
    def metrics(self) -> dict:
        if len(self.buffer) < 10:
            return {"insufficient_data": True}
        
        sorted_buffer = sorted(self.buffer)
        return {
            "p50": sorted_buffer[len(sorted_buffer) // 2],
            "p95": sorted_buffer[int(len(sorted_buffer) * 0.95)],
            "p99": sorted_buffer[int(len(sorted_buffer) * 0.99)],
            "p50_target_met": self._p50() <= self.target_p50,
            "p95_target_met": self._p95() <= self.target_p95,
            "n_samples": len(self.buffer),
        }
    
    def alert_if_degraded(self):
        m = self.metrics()
        if not m.get("p95_target_met"):
            log.warning(f"Latency P95 degraded: {m['p95']:.1f}s > {self.target_p95}s")
```

### 6.4 KV Cache 추적 (v0.2 신규, DGX Spark 메모리 병목 대응)

> 6개 딥리서치 결과: KV cache가 진짜 동시 세션 한도 결정자.
> 7B 모델 + NVFP4 = 12-15 동시 세션 (5초 latency 유지하며).

#### 동시 세션 한도

```yaml
# config/harness.yaml
inference:
  max_concurrent_sessions: 12   # 7B + NVFP4 기준
  kv_cache_alert_pct: 80
  
  # 모델별 추정 (Tier 1 측정 후 보정)
  model_capacity:
    qwen3_8b_dense_nvfp4:
      max_sessions: 12
      kv_per_session_mb: 1024
    gemma_4_e4b_nvfp4:
      max_sessions: 14
      kv_per_session_mb: 800
    qwen_2b_q4:
      max_sessions: 30          # 더 작아 더 많이
      kv_per_session_mb: 400
```

#### 추적 구현

```python
# service/monitoring/kv_cache_tracker.py

class KVCacheTracker:
    """동시 세션 + KV cache 메모리 추적"""
    
    def __init__(self, config: InferenceConfig):
        self.max_sessions = config.max_concurrent_sessions
        self.alert_pct = config.kv_cache_alert_pct
        self.active_sessions: dict[str, SessionInfo] = {}
    
    def can_accept_new_session(self) -> bool:
        return len(self.active_sessions) < self.max_sessions
    
    def register_session(self, session_id: str, estimated_kv_mb: float):
        if not self.can_accept_new_session():
            raise CapacityExceededError(
                f"Max concurrent sessions ({self.max_sessions}) reached. "
                f"Currently active: {len(self.active_sessions)}"
            )
        self.active_sessions[session_id] = SessionInfo(
            started_at=datetime.now(),
            estimated_kv_mb=estimated_kv_mb,
        )
    
    def deregister_session(self, session_id: str):
        self.active_sessions.pop(session_id, None)
    
    def utilization_pct(self) -> float:
        return (len(self.active_sessions) / self.max_sessions) * 100
    
    def alert_if_high_load(self):
        pct = self.utilization_pct()
        if pct > self.alert_pct:
            log.warning(
                f"KV cache utilization {pct:.0f}% — "
                f"{len(self.active_sessions)}/{self.max_sessions} sessions"
            )
```

#### 사용자에게 노출 (capacity 알림)

```python
# 새 세션 시작 시
def start_user_session(user_id: str) -> SessionResult:
    if not kv_tracker.can_accept_new_session():
        return SessionResult(
            success=False,
            user_message=(
                "현재 사용자가 많아 잠시 후 다시 시도해주세요.\n"
                "예상 대기 시간: 약 1-2분"
            ),
            queue_position=get_queue_position(user_id),
        )
    
    session = create_session(user_id)
    kv_tracker.register_session(session.id, estimated_kv_mb=1024)
    return SessionResult(success=True, session=session)
```

#### Tier별 정책

```yaml
Tier 0 (API):
  # API는 capacity 무관 (Anthropic / OpenAI 측 처리)
  enabled: false

Tier 1+ (DGX Local):
  enabled: true
  max_sessions: 12      # Qwen3-8B + NVFP4 기준
  
  # 한도 도달 시 동작
  on_full:
    - queue_user        # 대기열
    - estimate_wait     # 예상 시간 표시
    - graceful_degrade  # 더 작은 모델로 fallback (선택)

Tier 2 (Web UI):
  # 대시보드에 실시간 표시
  show_capacity_widget: true
  show_queue_position: true
```

자료의 함정 회피 + 6개 딥리서치 강한 합의 = capacity 명시.

---

## 7. Empty State / Onboarding

자료의 함정 회피: "새 사용자가 5분 안에 게임 시작 못 하면 이탈".

### 7.1 첫 사용자 흐름

```python
# service/onboarding/flow.py

class OnboardingFlow:
    """새 사용자가 첫 게임 시작까지"""
    
    MAX_ONBOARDING_SECONDS = 300  # 5분
    
    def start_for_new_user(self) -> OnboardingScreen:
        """첫 화면"""
        return OnboardingScreen(
            type="welcome",
            options=[
                # 즉시 시작 가능한 옵션 우선
                OnboardingOption(
                    id="demo",
                    title="🎮 데모 시작 (1분)",
                    description="미리 만들어진 짧은 시나리오",
                    estimated_time_seconds=60,
                ),
                OnboardingOption(
                    id="popular_work",
                    title="📚 인기 작품으로 (2분)",
                    description="많이 플레이된 세계관 중 선택",
                    estimated_time_seconds=120,
                ),
                OnboardingOption(
                    id="custom_input",
                    title="✏️ 직접 입력 (5분+)",
                    description="원하는 작품 이름 입력",
                    estimated_time_seconds=300,
                ),
            ],
        )
```

### 7.2 Demo Scenario (Empty State 핵심)

```yaml
# data/demo_scenarios/intro_fantasy.yaml
id: intro_fantasy_demo
title: "마법사의 첫날"
estimated_time_minutes: 5

description: |
  마법 학교에 막 입학한 신입생 시점.
  WorldFork의 모든 핵심 기능을 5분 안에 체험.

setup:
  pre_made: true               # 검색 / 플랜 생성 단계 스킵
  characters: 3
  scenes: 4
  ending_options: 2

# Tier 0 시나리오와 같은 형식 그대로 재활용
```

자료의 함정 회피: 새 사용자 = 데이터 0건. UI가 빈 상태에서 즉시 시작 가능해야.

### 7.3 진입 장벽 측정

```python
# service/monitoring/onboarding_metrics.py

class OnboardingMetrics:
    """첫 사용자 이탈 측정"""
    
    def record_step(self, user_id: str, step: str, elapsed_seconds: float):
        self.db.execute("""
            INSERT INTO onboarding_steps (
                user_id, step, elapsed_seconds, timestamp
            ) VALUES (?, ?, ?, ?)
        """, (user_id, step, elapsed_seconds, datetime.now()))
    
    def funnel_report(self) -> dict:
        """Funnel: 단계별 이탈율"""
        return {
            "step_1_welcome":      {"reach_rate": 1.00, "median_seconds": 2},
            "step_2_choice":       {"reach_rate": 0.85, "median_seconds": 8},
            "step_3_first_input":  {"reach_rate": 0.72, "median_seconds": 25},
            "step_4_first_response": {"reach_rate": 0.65, "median_seconds": 45},
            "step_5_completion":   {"reach_rate": 0.30, "median_seconds": 1800},
        }
    
    def alert_if_funnel_dropped(self):
        # 어느 단계에서 30% 이상 이탈하면 알람
        ...
```

### 7.4 한국 시장 onboarding (v0.2 신규, GPT 1 분석 반영)

> 한국 시장 검증된 패턴: Crack/제타가 성공한 onboarding 흐름.
> 87% 사용자가 10-20대, 캐릭터 + 서사 + UGC 우선.

#### 한국 사용자 첫 화면 (Tier 2+)

```python
# service/onboarding/korean_market.py

class KoreanOnboardingFlow(OnboardingFlow):
    """한국 시장 특화 onboarding"""
    
    def start_for_new_korean_user(self) -> OnboardingScreen:
        # 한국 시장 검증된 진입 패턴
        return OnboardingScreen(
            type="welcome_korean",
            language="ko",
            options=[
                OnboardingOption(
                    id="popular_korean_genres",
                    title="🎭 인기 장르로 빠른 시작 (1-2분)",
                    description="로맨스 / BL / 이세계 / 학원물 / 추리",
                    estimated_time_seconds=120,
                ),
                OnboardingOption(
                    id="webnovel_inspired",
                    title="📚 웹소설 / 웹툰 스타일 (3분)",
                    description="익숙한 스타일로 즉시 시작",
                    estimated_time_seconds=180,
                ),
                OnboardingOption(
                    id="custom_input",
                    title="✏️ 직접 작품 입력 (5분+)",
                    description="원하는 작품 이름으로 시작",
                    estimated_time_seconds=300,
                ),
                OnboardingOption(
                    id="continue_session",
                    title="🎮 이어하기",
                    description="이전 세션 불러오기",
                    visible_if="has_previous_session",
                ),
            ],
            
            # 청소년 모드 (10대) 자동 적용 옵션
            age_gate=AgeGate(
                ask=True,
                modes=["청소년 (만 18세 미만)", "성인 (만 18세 이상)"],
                store=True,   # 다음 방문 시 기억
            ),
        )
```

#### 한국 시장 인기 장르 프리셋

```yaml
# data/korean_genres.yaml

genres:
  romance:
    title: "로맨스"
    description: "현대 / 사극 / 학원 / 직장"
    audience: "10-30대 여성 + 일부 남성"
    
  isekai:
    title: "이세계 / 회귀"
    description: "환생 / 회귀 / 빙의 / 이세계 트립"
    audience: "10-30대 전반"
    
  school:
    title: "학원물"
    description: "학교 / 동아리 / 청춘"
    audience: "10-20대"
    
  fantasy_modern:
    title: "현대 판타지"
    description: "각성 / 능력자 / 헌터"
    audience: "10-30대 남성"
    
  bl_gl:
    title: "BL / GL"
    description: "동성 로맨스"
    audience: "10-30대 (성인 인증)"
    age_restriction: "18+"
    
  mystery:
    title: "추리 / 미스터리"
    description: "사건 / 범죄 / 추리"
    audience: "20-40대"
    
  horror:
    title: "공포 / 호러"
    description: "괴담 / 미스터리 호러"
    audience: "20-30대"
    age_restriction: "15+"
    
  idol:
    title: "아이돌 / 팬픽"
    description: "아이돌 시뮬 (가상 인물만, 실존 인물 X)"
    audience: "10-20대"
    safety_note: "실존 연예인 / 그룹명 자동 차단"
```

#### Onboarding 5분 안에 실제 게임 시작

```python
# 한국 사용자 평균 이탈 timing 반영 (GPT 1 분석)

KOREAN_MARKET_TIMING = {
    "step_1_welcome":         {"target_seconds": 5,   "drop_alert_at": 0.10},
    "step_2_genre_choice":    {"target_seconds": 15,  "drop_alert_at": 0.20},
    "step_3_first_input":     {"target_seconds": 30,  "drop_alert_at": 0.30},
    "step_4_first_response":  {"target_seconds": 60,  "drop_alert_at": 0.30},
    "step_5_engagement":      {"target_seconds": 180, "drop_alert_at": 0.40},
    # 5분 (300초) 안에 게임 시작 못 하면 강한 이탈
}


def funnel_alert_korean(metrics: dict):
    """한국 시장 기준 funnel 알람"""
    for step, target in KOREAN_MARKET_TIMING.items():
        actual_drop = 1 - metrics[step]["reach_rate"]
        if actual_drop > target["drop_alert_at"]:
            log.warning(
                f"Korean funnel alert: {step} drop {actual_drop:.0%} > "
                f"target {target['drop_alert_at']:.0%}"
            )
```

#### 청소년 / 성인 이원화 (10.3 위험 대응)

```yaml
# config/harness.yaml — Tier 2+ 활성화
korean_age_modes:
  enabled: true
  
  youth_mode:    # 만 18세 미만
    safety_filter_strength: high
    blocked_categories:
      - sexual_content
      - graphic_violence
      - suicide_self_harm
    show_resources_on_concern: true
    parental_consent_required: false  # KCC 가이드라인 검토 필요
    
  adult_mode:    # 만 18세 이상 (인증 후)
    safety_filter_strength: medium
    age_verification_required: true
    
  default_on_unverified: youth_mode  # 안전한 default
```

자료 + 한국 시장 분석 = 진입 조건이자 차별화.

---

## 8. AI Playtester 통합 (Layer 2)

### 8.1 Layer 2에서의 역할

상세는 `AI_PLAYTESTER.md`. 여기서는 **Layer 2와의 통합**만:

```python
# service/playtester/integration.py

class Layer2PlaytesterIntegration:
    """게임 서비스가 AI Playtester를 활용하는 방식"""
    
    def schedule_post_release_test(self, new_version: str):
        """새 버전 배포 후 자동 시뮬"""
        # 매 주요 기능 추가 후 전체 페르소나 자동 실행
        for persona in load_active_personas():
            playtester = AIPlaytester(persona, get_cli(persona.cli_to_use))
            result = playtester.play(self.game_endpoint, n_turns=30)
            
            # 실패 케이스 → eval set 시드로
            if not result.succeeded:
                self._convert_to_eval_seed(result)
    
    def _convert_to_eval_seed(self, playtester_result: PlaytesterResult):
        """Playtester가 발견한 이슈를 eval set에 추가"""
        for issue in playtester_result.issues:
            new_eval_item = {
                "id": f"playtester_{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}",
                "category": issue.category,
                "version": "auto_added",
                "prompt": issue.reproduction_prompt,
                "expected_behavior": issue.expected,
                "criteria": issue.criteria,
                "context": issue.context,
                "metadata": {
                    "source": "ai_playtester",
                    "persona": playtester_result.persona.id,
                    "discovered_at": datetime.now().isoformat(),
                },
            }
            self.eval_seed_queue.append(new_eval_item)
```

### 8.2 사용자 익명 데이터 (선택)

```yaml
# config/harness.yaml
layer2:
  user_data:
    collect_for_eval: false      # 기본 false (privacy 우선)
    # 사용자 명시적 동의 시:
    # - 응답 품질 낮은 케이스만 익명화하여 eval set에 추가
    # - 개인정보 / IP 정보 마스킹 강제
```

자료의 GDPR 우려 회피.

---

## 9. Hooks (Layer 2 사용)

CORE의 Hook 시스템 + Layer 2 specific:

```python
# service/hooks/layer2_builtin.py

def hook_pre_verify_log(ctx: HookContext) -> HookContext:
    """PreVerify: 검증 시작 로그"""
    if ctx.event != "PreVerify" or ctx.layer != "2":
        return ctx
    
    log.info(f"Layer 2 verify start: category={ctx.payload['category']}")
    return ctx


def hook_post_verify_metrics(ctx: HookContext) -> HookContext:
    """PostVerify: 메트릭 기록"""
    if ctx.event != "PostVerify" or ctx.layer != "2":
        return ctx
    
    metrics.record_verification(
        category=ctx.payload["category"],
        score=ctx.payload["score"],
        latency_ms=ctx.payload["latency_ms"],
        cost_usd=ctx.payload["cost_usd"],
    )
    return ctx


def hook_on_retry_log(ctx: HookContext) -> HookContext:
    """OnRetry: 재시도 발생 로그 (분석용)"""
    if ctx.event != "OnRetry" or ctx.layer != "2":
        return ctx
    
    metrics.record_retry(
        category=ctx.payload["category"],
        attempt_n=ctx.payload["attempt"],
        reason=ctx.payload["reason"],
    )
    return ctx


def hook_task_fail_user_message(ctx: HookContext) -> HookContext:
    """TaskFail: 사용자 메시지 표시"""
    if ctx.event != "TaskFail" or ctx.layer != "2":
        return ctx
    
    # 사용자 친화적 메시지 강제
    if not ctx.payload.get("user_message"):
        ctx.payload["user_message"] = "응답 생성에 어려움이 있습니다. 다시 시도해주세요."
    
    return ctx
```

---

## 10. Tier별 Layer 2 정책

각 Tier에서 Layer 2가 어떻게 다른지:

### Tier 0
```yaml
layer2:
  threshold: 70
  retries: 2                    # 빠른 검증
  fallback_chain:
    - claude_haiku_3_5
    - USER_REPORT
  cost_per_request:
    hard_limit_usd: 0.10
  latency:
    target_p95_seconds: 10.0    # API라 약간 관대
```

### Tier 1
```yaml
layer2:
  threshold: 70
  retries: 3
  fallback_chain:
    - local_qwen_2b
    - claude_haiku_3_5
    - claude_sonnet
    - USER_REPORT
  cost_per_request:
    hard_limit_usd: 0.30
  latency:
    target_p50_seconds: 3.0
    target_p95_seconds: 8.0
```

### Tier 2
```yaml
layer2:
  threshold: 75               # 약간 엄격
  retries: 3
  fallback_chain:
    - local_qwen_2b
    - claude_haiku_3_5
    - claude_sonnet
    - USER_REPORT
  cost_per_request:
    hard_limit_usd: 0.50
  latency:
    target_p50_seconds: 2.5    # 빠르게
    target_p95_seconds: 6.0
```

### Tier 3
```yaml
layer2:
  threshold: 80                # 출시 가능 품질
  retries: 3
  fallback_chain:
    - worldfork_qwen_sft       # SFT 모델 (있으면)
    - local_qwen_2b
    - claude_haiku_3_5
    - claude_sonnet
    - USER_REPORT
  cost_per_request:
    hard_limit_usd: 0.50
  latency:
    target_p50_seconds: 2.0
    target_p95_seconds: 5.0
```

각 Tier 졸업 시 `harness.yaml`의 `layer2` 섹션 업데이트.

---

## 11. Layer 2 안티패턴

자료의 함정들 + Layer 2 specific:

### 11.1 절대 하면 안 되는 것

```
❌ 점수를 LLM 재시도 prompt에 포함
   → CORE의 InformationLeakError가 자동 차단

❌ 게임 LLM = Verify LLM (self-rationalization)
   → CrossModelEnforcer가 런타임 에러

❌ Fallback rate 모니터링 안 함
   → 무지하게 회귀 발생

❌ 비용 한도 없이 무한 retry
   → 비용 폭발

❌ 사용자에게 기술 에러 그대로 노출
   → "JSONDecodeError: ..." 같은 메시지

❌ Empty state에서 빈 화면
   → 첫 사용자 즉시 이탈

❌ Onboarding 5분 초과
   → 자료의 함정 그대로

❌ "AI 자동화" 마케팅 vs 실제 LLM 의존성
   → 정직한 한계 명시
```

### 11.2 의식적 회피 패턴

```python
WEEKLY_LAYER2_CHECK = """
Layer 2 자기 점검 (매주 일요일):

1. Fallback rate?
   - 5% 이상이면 회귀 신호 (어떤 카테고리가?)

2. P95 latency?
   - 목표 초과하면 모델 선택 / 컨텍스트 점검

3. 사용자 비용 분포?
   - 평균 / max / 한도 도달 비율

4. Onboarding funnel?
   - 어느 단계에서 이탈?

5. AI Playtester 발견 vs 인간 베타 발견?
   - 둘이 일치하면 OK
   - 인간만 발견 = AI 한계
   - AI만 발견 = AI bias 가능

6. 정보 격리 위반 알람?
   - InformationLeakError 발생 빈도
   - 0이어야 정상

7. Cross-Model 위반 알람?
   - CrossModelError 발생 빈도
   - 0이어야 정상

8. Empty state UI?
   - 새 사용자 첫 화면이 비어있지 않나
"""
```

---

## 12. Layer 2 사용 흐름 (전체 코드 예시)

```python
# service/main.py — 전체 흐름 통합 예시

async def handle_user_session(user_input: str, session_id: str):
    """사용자 세션 시작부터 끝까지"""
    
    # 1. Stage 1: Interview
    interview = InterviewAgent(registry).run(user_input)
    if not interview.skip:
        return await wait_for_user_answers(interview.questions)
    
    # 2. Stage 2-3: Plan + Verify
    plan_result = PlanningAgent(registry, search).run(
        work_name=interview.parsed_input,
        user_preferences=user_prefs,
    )
    verify_result = PlanVerifyAgent(registry).verify(
        plan=plan_result.plan,
        original_search_results=plan_result.sources_used,
        user_preferences=user_prefs,
    )
    
    # 3. Stage 4: Plan Review (사용자 개입)
    review = PlanReviewSession(plan_result.plan, verify_result)
    while True:
        user_response = await wait_for_user_input(review.show_to_user())
        edit_result = review.handle_user_edit(user_response)
        if edit_result.approved or edit_result.cancelled:
            break
    
    if edit_result.cancelled:
        return None
    
    final_plan = edit_result.plan if edit_result.approved else edit_result.new_plan
    
    # 4. Stage 5-6: Agent + Verify Selection
    game_llm = AgentSelector(registry, matrix).select_game_llm(
        tier=current_tier,
        cost_preference=user_prefs.cost_preference,
    )
    verify_llm = VerifyAgentSelector(registry, matrix).select_verify_llm(
        game_llm=game_llm,
        category="game_response",
    )
    
    # 5. Stage 7: Game Loop
    loop = GameLoop(game_llm, verify_llm, layer2_config)
    game_state = GameState.from_plan(final_plan)
    
    while not game_state.is_completed():
        user_action = await wait_for_user_action()
        
        try:
            result = loop.process_action(user_action, game_state)
            game_state = result.game_state
            await display_to_user(result.response, result.cost)
        
        except Exception as e:
            classified = ErrorClassifier().classify(e, context={...})
            recovery = ErrorHandler().handle(classified, context={...})
            
            if recovery == RecoveryAction.REPLAN:
                # Stage 2-3 다시
                ...
            elif recovery == RecoveryAction.USER_INTERVENTION:
                await display_user_message(classified.user_message)
                break
    
    # 6. Stage 8: Complete / Save
    completion = CompletionHandler().on_complete(game_state)
    return completion
```

---

## 13. 다음 작업

Layer 2 완료. 다음:

- **AI_PLAYTESTER.md** — AI 도그푸딩 상세 (페르소나 / CLI 매핑 / 시드 누적)

마지막 4번째 문서.

---

## 부록 A: service/ 디렉토리 구조

```
service/
├── pipeline/
│   ├── interview.py
│   ├── planning.py
│   ├── plan_verify.py
│   ├── plan_review.py
│   ├── agent_selection.py
│   ├── verify_selection.py
│   ├── game_loop.py
│   ├── complete.py
│   └── replan_loop.py
├── retry/
│   └── strategy.py
├── fallback/
│   └── chain.py
├── error/
│   ├── tiers.py
│   ├── classifier.py
│   └── handler.py
├── cost/
│   └── limits.py
├── monitoring/
│   ├── latency.py
│   ├── fallback_metrics.py
│   ├── onboarding_metrics.py
│   └── user_display.py
├── onboarding/
│   └── flow.py
├── playtester/
│   └── integration.py
├── hooks/
│   └── layer2_builtin.py
└── main.py
```

## 부록 B: Layer 2 설정 빠른 참조

```yaml
# config/harness.yaml — layer2 부분만
layer2:
  threshold: 70                      # Tier별 다름 (10번 섹션)
  retries: 3
  
  retry_strategy:
    same_model_retries: 1
    cross_model_retries: 1
    api_fallback_retries: 1
  
  fallback_chain:                    # Tier별 다름
    - local_qwen_2b
    - claude_haiku_3_5
    - claude_sonnet
    - USER_REPORT
  
  cost_per_request:
    soft_limit_usd: 0.10
    hard_limit_usd: 0.50
  
  latency:
    target_p50_seconds: 3.0
    target_p95_seconds: 8.0
    timeout_seconds: 30.0
  
  empty_state:
    show_demo_scenario: true
    onboarding_max_seconds: 300
```

## 부록 C: Error Tier 빠른 참조

| Tier | 발생 조건 | 복구 동작 | 사용자 노출 |
|---|---|---|---|
| **Tier 1** | JSON parse fail, length, format | retry_with_feedback | 안 됨 (자동) |
| **Tier 2** | persona, korean, character break | cross_model_retry | 안 됨 (자동) |
| **Tier 3** | world inconsistency, IP leakage | replan | "재구성합니다" 메시지 |
| **Tier 4** | cost limit, timeout, all models down | user_decide | 메시지 + 대안 |

---

*문서 끝. v0.1 초안.*
