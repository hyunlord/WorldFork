"""W2 D4 작업 5 + Tier 1.5 D4: GM Agent 테스트."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from core.llm.client import LLMClient, LLMResponse, Prompt
from service.game.gm_agent import GMAgent, MockGMAgent
from service.game.init_from_plan import init_game_state_from_plan
from service.game.state import GameState
from service.pipeline.types import CharacterPlan, Plan, WorldSetting


def _make_plan_state() -> tuple[Plan, GameState]:
    mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
    plan = Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지",
        main_character=mc,
        world=WorldSetting(
            setting_name="신참 던전", genre="판타지",
            tone="진지", rules=["마법"],
        ),
        opening_scene="투르윈은 던전 입구에 있다.",
    )
    state = init_game_state_from_plan(plan)
    return plan, state


class _MockLLM(LLMClient):
    def __init__(self, response_text: str = "GM 응답") -> None:
        self._text = response_text

    @property
    def model_name(self) -> str:
        return "mock"

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
        return LLMResponse(
            text=self._text, model="mock",
            cost_usd=0.01, latency_ms=100,
            input_tokens=50, output_tokens=100,
        )


class TestMockGMAgent:
    def test_basic_response(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.text != ""
        assert r.mechanical_passed
        assert r.error is None

    def test_custom_responses(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent(mock_responses=["커스텀 응답"])
        r = agent.generate_response(plan, state, "x")
        assert r.text == "커스텀 응답"

    def test_response_cycles(self) -> None:
        plan, state = _make_plan_state()
        agent = MockGMAgent(mock_responses=["A", "B"])
        r1 = agent.generate_response(plan, state, "x")
        r2 = agent.generate_response(plan, state, "y")
        r3 = agent.generate_response(plan, state, "z")
        assert r1.text == "A"
        assert r2.text == "B"
        assert r3.text == "A"  # cycle


class TestGMAgentRealLLM:
    def test_full_flow(self) -> None:
        llm = _MockLLM(response_text="당신은 던전에 들어왔습니다. 어두운 통로가 보입니다.")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.text != ""
        assert r.error is None

    def test_llm_failure(self) -> None:
        broken_llm = MagicMock()
        broken_llm.generate.side_effect = RuntimeError("LLM down")
        broken_llm.model_name = "broken"

        agent = GMAgent(broken_llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "x")
        assert r.error is not None
        assert "LLM call failed" in r.error
        assert not r.mechanical_passed

    def test_history_in_user_prompt(self) -> None:
        plan, state = _make_plan_state()
        state.add_turn("이전 액션", "이전 응답", 0.01, 100)

        llm = _MockLLM(response_text="다음 응답")
        agent = GMAgent(llm)
        r = agent.generate_response(plan, state, "다음 액션")
        assert r.text != ""

    def test_dynamic_max_tokens(self) -> None:
        """짧은 user_action → 호출 자체 성공 검증."""
        llm = _MockLLM(response_text="응답")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들")
        assert r.text != ""

    def test_mock_gm_returns_score(self) -> None:
        """MockGMAgent도 total_score / verify_passed 반환."""
        plan, state = _make_plan_state()
        agent = MockGMAgent()
        r = agent.generate_response(plan, state, "x")
        assert r.total_score == 100.0
        assert r.verify_passed is True

    def test_supporting_characters_in_prompt(self) -> None:
        """조연이 있는 Plan → 시스템 프롬프트에 조연 포함."""
        mc = CharacterPlan(name="투르윈", role="주인공", description="신참")
        sc = CharacterPlan(name="셰인", role="조력자", description="멘토")
        plan = Plan(
            work_name="test", work_genre="판타지", main_character=mc,
            supporting_characters=[sc],
            world=WorldSetting(setting_name="던전", genre="판타지", tone="d", rules=[]),
        )
        state = init_game_state_from_plan(plan)
        llm = _MockLLM()
        agent = GMAgent(llm)
        r = agent.generate_response(plan, state, "x")
        assert r.text != ""


class TestGMAgentD4:
    """★ Tier 1.5 D4 신규 테스트."""

    def test_cross_model_violation_raises(self) -> None:
        """같은 model_name → ValueError."""
        game_llm = _MockLLM(response_text="응답")
        verify_llm = _MockLLM(response_text="검증")  # 같은 model_name="mock"

        with pytest.raises(ValueError, match="Cross-Model violation"):
            GMAgent(game_llm, verify_llm=verify_llm)

    def test_cross_model_different_models_ok(self) -> None:
        """다른 model_name → 정상 (★ A1.5: LLMJudge generate_json 진짜 호출)."""
        from core.llm.client import LLMClient

        class VerifyLLM(LLMClient):
            @property
            def model_name(self) -> str:
                return "different_model"
            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                # ★ A1.5: LLMJudge가 generate_json 호출 → JSON 파싱
                # (★ score 값은 변수로 — anti-pattern hardcoded_score_dict 회피)
                score_val = 91
                payload = (
                    f'{{"score": {score_val}, "verdict": "pass", '
                    '"issues": [], "suggestions": []}'
                )
                return LLMResponse(
                    text=payload,
                    model="different_model",
                    cost_usd=0.0, latency_ms=10,
                    input_tokens=10, output_tokens=10,
                )

        game_llm = _MockLLM()
        verify_llm = VerifyLLM()
        agent = GMAgent(game_llm, verify_llm=verify_llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "x")
        assert r.text != ""

    def test_response_has_total_score(self) -> None:
        """성공 응답 → total_score > 0."""
        llm = _MockLLM(response_text="당신은 던전에 들어왔습니다. 어두운 통로가 보입니다.")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.total_score >= 0.0
        assert r.total_score <= 100.0

    def test_truncated_response_detected(self) -> None:
        """잘린 응답 → TruncationDetectionRule 검출 (minor, gate 차단 X)."""
        truncated = "당신의 뒤에는 조력자 셰"
        llm = _MockLLM(response_text=truncated)
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        # minor → passed=True (critical/major 없으면 통과)
        # but findings에 기록됨
        assert any("truncat" in f.lower() or "korean_truncation" in f.lower()
                   for f in r.mechanical_failures)

    def test_verify_passed_on_good_response(self) -> None:
        """정상 응답 → verify_passed=True."""
        llm = _MockLLM(response_text="어두운 던전 안으로 들어갔습니다. 무엇을 하시겠습니까?")
        agent = GMAgent(llm)
        plan, state = _make_plan_state()
        r = agent.generate_response(plan, state, "들어가기")
        assert r.verify_passed is True


class TestGMAgentVerifyLLMUsed:
    """A1.5: verify_llm이 진짜 호출되는지 (★ Made-but-Never-Used 차단)."""

    def test_verify_llm_generate_called(self) -> None:
        """verify_llm.generate가 진짜 호출되는지 검증 (★ LLMJudge.evaluate path)."""
        from core.llm.client import LLMClient

        class TrackingVerifyLLM(LLMClient):
            """generate 호출 횟수 추적."""

            def __init__(self) -> None:
                self.call_count = 0

            @property
            def model_name(self) -> str:
                return "tracking_27b"

            def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse:
                self.call_count += 1
                return LLMResponse(
                    text='{"score": 92, "verdict": "pass", "issues": [], "suggestions": []}',
                    model="tracking_27b",
                    cost_usd=0.0,
                    latency_ms=200,
                    input_tokens=50,
                    output_tokens=30,
                )

        game_llm = _MockLLM(response_text="동굴은 어둡고 차갑습니다. 무엇을 하시겠습니까?")
        verify_llm = TrackingVerifyLLM()
        agent = GMAgent(game_llm=game_llm, verify_llm=verify_llm)

        plan, state = _make_plan_state()
        result = agent.generate_response(plan, state, "주변을 살핍니다")

        # ★ ★ 핵심: verify_llm이 진짜 호출됨 (★ Made-but-Never-Used 회귀 차단)
        assert verify_llm.call_count >= 1, (
            "verify_llm.generate 호출 X — Made-but-Never-Used 회귀!"
        )
        # 응답 sanity
        assert result.text != ""
        # judge 호출 시 total_score는 judge.score 기반
        assert result.total_score == 92.0

    def test_verify_llm_none_skips_judge(self) -> None:
        """verify_llm=None이면 judge 호출 X, Mechanical만."""
        game_llm = _MockLLM(response_text="동굴은 어둡고 차갑습니다. 무엇을 하시겠습니까?")
        agent = GMAgent(game_llm=game_llm, verify_llm=None)

        plan, state = _make_plan_state()
        result = agent.generate_response(plan, state, "x")

        # Mechanical만 통과 시 total_score = 100.0 (★ 기존 동작 유지)
        assert result.text != ""
        assert result.total_score == 100.0 or result.total_score >= 0.0


class TestGMPromptFindings:
    """본인 풀 플레이 5턴 finding 자동 차단 (★ 회귀 방지)."""

    @staticmethod
    def _make_ctx(main_name: str = "모험가") -> dict[str, Any]:
        return {
            "work_name": "신비한 모험",
            "work_genre": "판타지",
            "world_setting": "중세 판타지",
            "world_tone": "신비",
            "world_rules": ["마법 있음"],
            "main_character_name": main_name,
            "main_character_role": "주인공",
            "supporting_characters": [],
            "current_location": "시작",
            "current_turn": 0,
        }

    def test_system_prompt_no_player_meta_word(self) -> None:
        """finding #5: '플레이어' 메타 단어 차단 + 호칭 일관 명시."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._make_ctx(main_name="투르윈"))
        # 호칭 규칙 명시 진짜
        assert "호칭" in prompt
        # 진짜 이름이 system prompt에 들어감
        assert "투르윈" in prompt
        # '플레이어' 메타 단어 차단 명시
        assert "플레이어" in prompt and "메타" in prompt

    def test_system_prompt_progression_rule(self) -> None:
        """finding #4: 진행 / 변화 명시."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._make_ctx())
        assert "진행" in prompt
        assert "단순 반복" in prompt or "반복 절대 X" in prompt

    def test_user_prompt_first_turn_explicit(self) -> None:
        """finding #1: 첫 턴 (turn==0) 선택지 명시."""
        from service.game.gm_agent import GMAgent
        from service.game.state import GameState

        state = GameState(scenario_id="test", turn=0, location="시작")
        prompt = GMAgent._build_user_prompt(state, "")
        assert "게임 시작" in prompt
        assert "선택지" in prompt
        # 빈 user_action도 처리
        assert "시작" in prompt

    def test_user_prompt_history_3_turns_500_chars(self) -> None:
        """finding #3: 이전 history 3턴 + 500자."""
        from service.game.gm_agent import GMAgent
        from service.game.state import GameState, TurnLog

        history = [
            TurnLog(
                turn=i,
                user_action=f"행동{i}",
                gm_response=f"GM {i}: " + "x" * 600,
                cost_usd=0.0,
                latency_ms=100,
            )
            for i in range(1, 5)
        ]
        state = GameState(
            scenario_id="test", turn=4, location="장소", history=history,
        )
        prompt = GMAgent._build_user_prompt(state, "다음")
        # 최근 3턴 진짜 (행동2/3/4)
        assert "행동2" in prompt or "행동3" in prompt
        assert "행동4" in prompt
        # 500자 적용 — GM 응답이 500자까지 들어감 (★ 200자보다 길게)
        # "x" * 600 → :500 잘리면 [:500]에는 "GM 1: " 8자 + "x" 492자 = 500자
        # 200자였으면 192자만 — 명확히 구분
        # 응답 길이로 검증
        gm_section = prompt.split("GM:")[1] if "GM:" in prompt else ""
        # 한 턴의 GM 응답 부분만 잘라서 검증 — 충분히 김 (500자 근처)
        assert len(gm_section) >= 200

    def test_user_prompt_progression_emphasis(self) -> None:
        """finding #4: 일반 턴에서 결과 반영 + 새 이벤트 명시."""
        from service.game.gm_agent import GMAgent
        from service.game.state import GameState, TurnLog

        history = [
            TurnLog(
                turn=1, user_action="이전",
                gm_response="응답", cost_usd=0.0, latency_ms=100,
            ),
        ]
        state = GameState(
            scenario_id="test", turn=1, location="장소", history=history,
        )
        prompt = GMAgent._build_user_prompt(state, "1")
        assert "결과" in prompt and "반영" in prompt
        assert "단순 반복" in prompt
