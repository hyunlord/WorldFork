"""Planning Agent (★ 자료 2.2 Stage 2).

흐름:
  1. 검색 (Mock 우선)
  2. 분류 (공식/팬해석/팬픽)
  3. IP Masking 적용
  4. 5-section PLANNING_PROMPT으로 Plan 생성 (LLM, Mock 우선)
"""

from typing import Any, Protocol

from core.eval.filter_pipeline import STANDARD_FILTER_PIPELINE
from core.llm.client import LLMResponse, Prompt
from service.search.adapter import SearchBundle, SearchQuery, WebSearchAdapter

from .ip_masking import apply_ip_masking
from .prompts import build_planning_prompt
from .source_classifier import classify_sources, filter_high_confidence
from .types import CharacterPlan, Plan, PlanResult, WorldSetting


class PlanLLMClient(Protocol):
    """Plan 생성 LLM 인터페이스."""

    @property
    def model_name(self) -> str: ...

    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse: ...


PLAN_REQUIRED_FIELDS = {
    "work_name", "work_genre", "main_character",
    "world", "opening_scene", "initial_choices",
}

MOCK_PLAN_DATA: dict[str, Plan] = {
    "novice_dungeon_run": Plan(
        work_name="novice_dungeon_run",
        work_genre="판타지/모험",
        main_character=CharacterPlan(
            name="투르윈", role="주인공",
            description="신참 모험가 (성장형)",
        ),
        supporting_characters=[
            CharacterPlan(name="셰인", role="조력자", description="노련한 멘토"),
            CharacterPlan(name="에라드", role="동료", description="전사형 동료"),
        ],
        world=WorldSetting(
            setting_name="신참 던전 세계",
            genre="판타지",
            tone="진지하면서 희망적",
            rules=["마법 존재", "괴물 위험", "성장 가능"],
        ),
        opening_scene=(
            "투르윈은 수도원 아래 신참 던전 입구에 서 있다. "
            "어두운 던전 안에서 들리는 작은 소리들과 멀리서 비추는 약한 빛."
        ),
        initial_choices=[
            "조심스럽게 던전 입구로 들어가기",
            "주변 환경을 자세히 관찰하기",
            "동료를 찾기 위해 마을로 돌아가기",
        ],
        ip_masking_applied=True,
    ),
}


class MockPlanningAgent:
    """Mock LLM (★ Tier 1-2 본격 호출 X)."""

    def __init__(self, custom_data: dict[str, Plan] | None = None) -> None:
        self._data = custom_data or MOCK_PLAN_DATA

    def run(
        self,
        work_name: str,
        user_preferences: dict[str, str] | None = None,
        search_adapter: WebSearchAdapter | None = None,
    ) -> PlanResult:
        plan_template = self._data.get(work_name.lower().strip())
        if plan_template is None:
            return PlanResult(
                plan=Plan(
                    work_name="",
                    work_genre="",
                    main_character=CharacterPlan(name="", role="", description=""),
                ),
                error=f"No mock plan for '{work_name}'",
            )

        prefs = user_preferences or {}
        plan = Plan(
            work_name=plan_template.work_name,
            work_genre=plan_template.work_genre,
            main_character=plan_template.main_character,
            supporting_characters=list(plan_template.supporting_characters),
            world=plan_template.world,
            opening_scene=plan_template.opening_scene,
            initial_choices=list(plan_template.initial_choices),
            user_preferences=dict(prefs),
            ip_masking_applied=True,
            sources_used=["mock"],
        )

        return PlanResult(
            plan=plan,
            cost_usd=0.0,
            sources_summary="mock data",
            ip_masking_applied=True,
        )


class PlanningAgent:
    """Planning Agent 본체 (★ 자료 2.2 Stage 2).

    Tier 1-2 본격 LLM 호출은 Mock으로 폴백.
    """

    def __init__(
        self,
        llm_client: PlanLLMClient,
        search_adapter: WebSearchAdapter,
    ) -> None:
        self._llm = llm_client
        self._search = search_adapter

    def run(
        self,
        work_name: str,
        user_preferences: dict[str, str] | None = None,
    ) -> PlanResult:
        prefs = user_preferences or {}

        try:
            search_bundle = self._search.search(SearchQuery(
                query=work_name,
                sources=["wiki", "namuwiki", "fan_community"],
                max_per_source=3,
            ))
        except Exception as e:
            return self._error(f"Search failed: {e}")

        classified = classify_sources(search_bundle)

        if classified.total == 0:
            return self._error(f"No search results for '{work_name}'")

        high_conf = filter_high_confidence(classified, min_confidence=0.6)

        prompt_text = build_planning_prompt(
            sources_summary=high_conf.summary(),
            user_preferences=prefs,
        )
        prompt = Prompt(
            system="You are a JSON-only generator. Output valid JSON only.",
            user=prompt_text,
        )

        try:
            response = self._llm.generate(prompt, max_tokens=2000)
        except Exception as e:
            return self._error(f"LLM call failed: {e}")

        filter_result = STANDARD_FILTER_PIPELINE.extract(response.text)
        if not filter_result.succeeded or not filter_result.parsed:
            return self._error("Plan JSON parsing failed")

        try:
            plan = self._dict_to_plan(filter_result.parsed, prefs, search_bundle)
        except (KeyError, TypeError, ValueError) as e:
            return self._error(f"Plan field extraction failed: {e}")

        # LLM이 IP를 누설할 수 있으므로 한 번 더 masking (★ 자료 정신)
        plan = apply_ip_masking(plan)

        return PlanResult(
            plan=plan,
            cost_usd=response.cost_usd,
            sources_summary=high_conf.summary(),
            ip_masking_applied=True,
        )

    def _error(self, msg: str) -> PlanResult:
        return PlanResult(
            plan=Plan(
                work_name="",
                work_genre="",
                main_character=CharacterPlan(name="", role="", description=""),
            ),
            error=msg,
        )

    @staticmethod
    def _dict_to_plan(
        data: dict[str, Any],
        prefs: dict[str, str],
        search_bundle: SearchBundle,
    ) -> Plan:
        """JSON dict → Plan dataclass."""
        missing = PLAN_REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ValueError(f"Missing fields: {missing}")

        mc_data = data["main_character"]
        if not isinstance(mc_data, dict):
            raise TypeError("main_character must be dict")
        main_char = CharacterPlan(
            name=str(mc_data.get("name", "")),
            role=str(mc_data.get("role", "주인공")),
            description=str(mc_data.get("description", "")),
        )

        supporting: list[CharacterPlan] = []
        for sc_data in data.get("supporting_characters", []):
            if isinstance(sc_data, dict):
                supporting.append(CharacterPlan(
                    name=str(sc_data.get("name", "")),
                    role=str(sc_data.get("role", "")),
                    description=str(sc_data.get("description", "")),
                ))

        world_data = data["world"]
        if not isinstance(world_data, dict):
            raise TypeError("world must be dict")
        world = WorldSetting(
            setting_name=str(world_data.get("setting_name", "")),
            genre=str(world_data.get("genre", "")),
            tone=str(world_data.get("tone", "")),
            rules=list(world_data.get("rules", [])),
        )

        return Plan(
            work_name=str(data["work_name"]),
            work_genre=str(data["work_genre"]),
            main_character=main_char,
            supporting_characters=supporting,
            world=world,
            opening_scene=str(data["opening_scene"]),
            initial_choices=list(data["initial_choices"]),
            user_preferences=prefs,
            ip_masking_applied=False,  # apply_ip_masking에서 True로 바뀜
            sources_used=[r.source for r in search_bundle.results],
        )
