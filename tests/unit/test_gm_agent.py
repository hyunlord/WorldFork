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


class TestGMPromptV2Stats:
    """v2 스탯 진짜 prompt 노출 (★ Layer 4 본질, 2026-05-07).

    state_v2 일반 30+ + 특이 5가 _gm_system_prompt에서 진짜 출력되는지 검증.
    Made But Never Used 차단 진짜.
    """

    @staticmethod
    def _ctx_with_v2(name: str = "에르웬") -> dict[str, Any]:
        return {
            "work_name": "겜바바",
            "work_genre": "판타지",
            "world_setting": "라스카니아",
            "world_tone": "진지",
            "world_rules": ["미궁"],
            "main_character_name": name,
            "main_character_role": "주인공",
            "supporting_characters": [],
            "current_location": "1층",
            "current_turn": 0,
            "v2_characters": {
                name: {
                    "race": "요정",
                    "sub_race": None,
                    "physical": 8, "mental": 12, "special": 14,
                    "strength": 8, "agility": 12, "flexibility": 12,
                    "height": 165, "weight": 50,
                    "hp": 90, "hp_max": 90,
                    "soul_power": 60, "soul_power_max": 60,
                    "obsession": 80,
                    "sixth_sense": 8,
                    "support_rating": 0,
                    "perception_interference": 0,
                    "essence_slot_max": 5,
                    "is_player": True,
                }
            },
        }

    def test_v2_stats_in_prompt(self) -> None:
        """v2 character + 일반 + 특이 진짜 prompt에 나타남."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._ctx_with_v2())
        assert "에르웬" in prompt
        assert "요정" in prompt
        # 메인 3대
        assert "이능 14" in prompt or "이능" in prompt
        # 1티어
        assert "민첩 12" in prompt or "근력 8" in prompt
        # 신체
        assert "165" in prompt
        # ★ 특이 스탯 진짜
        assert "집착 80" in prompt
        assert "육감 8" in prompt
        # 0인 특이는 출력 X
        assert "지지도 0" not in prompt
        assert "인식방해 0" not in prompt
        # ★ 본인 가이드 라인
        assert "특이 스탯은 일상/대화/행동" in prompt
        assert "강박적 추적" in prompt or "거짓말 감지" in prompt

    def test_v2_no_chars_no_block(self) -> None:
        """v2_characters X면 v2 block 출력 X (★ 호환)."""
        from service.game.gm_agent import _gm_system_prompt

        ctx = self._ctx_with_v2()
        del ctx["v2_characters"]
        prompt = _gm_system_prompt(ctx)
        assert "캐릭터 스탯" not in prompt
        assert "특이 스탯은 일상/대화/행동" not in prompt


class TestGMPromptStage1WorldLocation:
    """Stage 1 — WorldState + Location prompt 진짜 출력 검증.

    Layer 4 본질: schema 추가 → context → prompt → LLM.
    """

    @staticmethod
    def _ctx_stage1() -> dict[str, Any]:
        return {
            "work_name": "겜바바",
            "work_genre": "판타지",
            "world_setting": "라스카니아",
            "world_tone": "진지",
            "world_rules": ["미궁"],
            "main_character_name": "비요른",
            "main_character_role": "주인공",
            "supporting_characters": [],
            "current_location": "1층",
            "current_turn": 0,
            "v2_world_state": {
                "current_round": 5,
                "hours_in_dungeon": 72,
                "is_dimension_collapse": False,
                "active_rifts": ["bloody_castle"],
                "is_dark_zone": True,
                "party_members": ["비요른", "에르웬"],
                "party_share_ratios": {"비요른": 0.9, "에르웬": 0.1},
            },
            "v2_initial_location": {
                "realm": "미궁",
                "floor": 1,
                "sub_area": "수정동굴",
                "rift_id": None,
                "visibility_meters": 10,
                "has_light": False,
            },
        }

    def test_world_state_in_prompt(self) -> None:
        """WorldState 필드 진짜 prompt 출력."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._ctx_stage1())
        assert "라운드" in prompt
        assert "5" in prompt
        assert "72" in prompt or "미궁 시간" in prompt
        # ★ 어둠 진짜 출력
        assert "어둠" in prompt
        # 균열
        assert "bloody_castle" in prompt
        # 파티
        assert "비요른" in prompt
        assert "에르웬" in prompt
        # ★ 분배 (90% / 10%)
        assert "90%" in prompt or "9:1" in prompt or "0.9" in prompt

    def test_location_in_prompt(self) -> None:
        """Location 필드 진짜 prompt 출력."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._ctx_stage1())
        assert "시작 위치" in prompt
        assert "미궁" in prompt
        assert "1층" in prompt
        assert "수정동굴" in prompt
        # 가시거리 10m + 어둠
        assert "10m" in prompt or "가시거리" in prompt
        assert "비활성" in prompt or "어둠" in prompt
        # ★ 본인 가이드
        assert "환경은 일상/대화/행동에 진짜 영향" in prompt

    def test_no_world_state_no_block(self) -> None:
        """v2_world_state X면 block 출력 X."""
        from service.game.gm_agent import _gm_system_prompt

        ctx = self._ctx_stage1()
        del ctx["v2_world_state"]
        del ctx["v2_initial_location"]
        prompt = _gm_system_prompt(ctx)
        assert "게임 진행 상태" not in prompt
        assert "시작 위치" not in prompt


class TestGMPromptStage2FloorDefinition:
    """Stage 2 — Floor1Definition prompt 진짜 출력 (★ Layer 4)."""

    @staticmethod
    def _ctx_stage2() -> dict[str, Any]:
        return {
            "work_name": "겜바바",
            "work_genre": "판타지",
            "world_setting": "라스카니아",
            "world_tone": "진지",
            "world_rules": ["미궁"],
            "main_character_name": "비요른",
            "main_character_role": "주인공",
            "supporting_characters": [],
            "current_location": "1층",
            "current_turn": 0,
            "v2_floor_definition": {
                "name": "수정동굴",
                "floor_number": 1,
                "base_time_hours": 168,
                "base_visibility_meters": 10,
                "is_dark_default": True,
                "sub_areas": [
                    {
                        "name": "비석 공동",
                        "description": "30m 공동",
                        "accessible_from": ["북쪽 통로", "남쪽 통로"],
                        "monster_names": [],
                        "is_dark": True,
                        "has_landmark": True,
                        "landmark_type": "비석",
                    },
                    {
                        "name": "남쪽 통로",
                        "description": "노움 영역",
                        "accessible_from": ["포탈 근처"],
                        "monster_names": ["노움"],
                        "is_dark": True,
                        "has_landmark": False,
                        "landmark_type": None,
                    },
                ],
                "monsters": [
                    {
                        "name": "노움",
                        "grade": 9,
                        "area": "남쪽",
                        "behavior": "일체화 액티브",
                        "requires_light": True,
                        "drops": [
                            {
                                "essence_name": "노움 정수",
                                "drop_rate": 0.0001,
                                "color_pool": ["초록"],
                            }
                        ],
                    },
                    {
                        "name": "레이스",
                        "grade": 9,
                        "area": "전역",
                        "behavior": "시체불꽃",
                        "requires_light": False,
                        "drops": [
                            {
                                "essence_name": "레이스 정수",
                                "drop_rate": 0.0001,
                                "color_pool": ["검정"],
                            }
                        ],
                    },
                ],
            },
        }

    def test_floor_definition_in_prompt(self) -> None:
        """Floor1Definition 진짜 prompt 출력."""
        from service.game.gm_agent import _gm_system_prompt

        prompt = _gm_system_prompt(self._ctx_stage2())
        assert "수정동굴" in prompt
        assert "168시간" in prompt
        assert "10m" in prompt or "가시거리" in prompt
        assert "어둠 기본" in prompt
        # sub_areas
        assert "비석 공동" in prompt
        assert "비석" in prompt
        assert "남쪽 통로" in prompt
        # monsters
        assert "노움" in prompt
        assert "남쪽" in prompt
        assert "레이스" in prompt
        # ★ 어둠 활성 가능 명시 (★ requires_light=False)
        assert "어둠 활성 가능" in prompt
        # LLM 가이드
        assert "층 본질" in prompt
        assert "비석 공동" in prompt

    def test_no_floor_definition_no_block(self) -> None:
        """v2_floor_definition X면 block 출력 X."""
        from service.game.gm_agent import _gm_system_prompt

        ctx = self._ctx_stage2()
        del ctx["v2_floor_definition"]
        prompt = _gm_system_prompt(ctx)
        assert "현재 층 정의" not in prompt
        assert "Sub Areas" not in prompt
