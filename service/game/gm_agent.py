"""GM Agent (★ Tier 1.5 D4 — IntegratedVerifier + Cross-Model 강제).

★ D4 변경:
  - Cross-Model 강제 (game_llm ≠ verify_llm, 본인 #18)
  - judge_score / total_score / verify_passed 반환
  - TruncationDetectionRule 포함 Mechanical 검증
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

from core.llm.client import LLMClient, LLMResponse, Prompt
from core.llm.game_token_policy import compute_game_max_tokens
from core.verify.integrated import IntegratedVerifier
from core.verify.llm_judge import JudgeCriteria, LLMJudge
from core.verify.mechanical import MechanicalChecker
from service.pipeline.types import Plan

from .init_from_plan import build_game_context
from .state import GameState

# ★ 게임 응답 검증 기준 (★ Cross-Model LLM Judge용, A1.5)
GAME_CRITERIA = JudgeCriteria(
    name="game_response_quality",
    description="한국어 텍스트 어드벤처 게임 응답의 품질 평가",
    dimensions=[
        "한국어 자연스러움 (한자/외국어 혼입 X)",
        "캐릭터 페르소나 일관성",
        "세계관 일관성",
        "사용자 행동에 대한 적절한 반응",
        "응답 완결성 (잘림 X)",
    ],
)


class GameLLMClient(Protocol):
    @property
    def model_name(self) -> str: ...
    def generate(self, prompt: Prompt, **kwargs: Any) -> LLMResponse: ...


@dataclass
class GMResponse:
    """GM Agent 응답 (★ D4 풍부 정보)."""

    text: str
    cost_usd: float = 0.0
    latency_ms: int = 0
    mechanical_passed: bool = True
    mechanical_failures: list[str] = field(default_factory=list)

    # ★ D4 추가
    judge_score: float | None = None
    judge_passed: bool | None = None
    total_score: float = 0.0   # 0-100
    verify_passed: bool = True

    error: str | None = None


def _gm_system_prompt(ctx: dict[str, Any]) -> str:
    """GM system prompt (★ Plan 컨텍스트 + 잘림 방지 명시)."""
    supporting_line = ""
    if ctx["supporting_characters"]:
        supporting_line = (
            "- 조연: "
            + ", ".join(
                f"{c['name']} ({c['role']})"
                for c in ctx["supporting_characters"]
            )
            + "\n"
        )

    main_name = ctx["main_character_name"]

    # ★ Tier 2 D12: v2_characters 진짜 사용 (★ Made But Never Used 차단)
    # 일반 30+ + 특이 5 → prompt에 진짜 노출 (★ Layer 4 본질, 2026-05-07)
    v2_block = ""
    v2_chars = ctx.get("v2_characters") or {}
    if v2_chars:
        v2_lines = []
        for name, info in v2_chars.items():
            race = info.get("race", "")
            sub_race = info.get("sub_race")
            race_str = f"{race}/{sub_race}" if sub_race else race
            hp = info.get("hp", 0)
            hp_max = info.get("hp_max", 0)
            soul = info.get("soul_power", 0)
            height = info.get("height", 0)

            line = f"  - **{name}** ({race_str})"
            line += f": HP {hp}/{hp_max}, 영혼력 {soul}, 신장 {height}cm"
            line += (
                f", 메인 [육체 {info.get('physical', 0)} "
                f"정신 {info.get('mental', 0)} 이능 {info.get('special', 0)}]"
            )
            line += (
                f", 1티어 [근력 {info.get('strength', 0)} "
                f"민첩 {info.get('agility', 0)} "
                f"유연성 {info.get('flexibility', 0)}]"
            )
            # 감각 (★ 7)
            line += (
                f", 감각 [시각 {info.get('sight', 0)} "
                f"후각 {info.get('smell', 0)} "
                f"청각 {info.get('hearing', 0)} "
                f"인지 {info.get('cognitive_speed', 0)} "
                f"명중 {info.get('accuracy', 0)} "
                f"회피 {info.get('evasion', 0)} "
                f"도약 {info.get('jump_power', 0)}]"
            )
            # 방어 (★ 5 + 5 속성저항)
            line += (
                f", 방어 [골강도 {info.get('bone_strength', 0)} "
                f"골밀도 {info.get('bone_density', 0)} "
                f"물리내성 {info.get('physical_resistance', 0)} "
                f"내구 {info.get('durability', 0)} "
                f"고통 {info.get('pain_resistance', 0)}]"
            )
            line += (
                f", 속성저항 [독 {info.get('poison_resistance', 0)} "
                f"화염 {info.get('fire_resistance', 0)} "
                f"냉기 {info.get('cold_resistance', 0)} "
                f"번개 {info.get('lightning_resistance', 0)} "
                f"어둠 {info.get('dark_resistance', 0)}]"
            )
            # 행운/기술 (★ 6)
            line += (
                f", 행운/기술 [행운 {info.get('luck', 0)} "
                f"손재주 {info.get('dexterity', 0)} "
                f"절삭 {info.get('cutting_power', 0)} "
                f"투쟁심 {info.get('fighting_spirit', 0)} "
                f"인내 {info.get('endurance', 0)} "
                f"지구력 {info.get('stamina', 0)}]"
            )
            # 재생 + 마법
            line += (
                f", 재생 [재생력 {info.get('regen_rate', 0)} "
                f"자연재생 {info.get('natural_regen', 0)}]"
            )
            line += (
                f", 마법 [항마력 {info.get('magic_resistance', 0)} "
                f"정신력 {info.get('mental_power', 0)}]"
            )

            # ★ 특이 스탯 — 0 초과만 노출 (★ 일상/대화/행동 영향)
            specials: list[str] = []
            if (v := info.get("obsession", 0)) > 0:
                specials.append(f"집착 {v}")
            if (v := info.get("sixth_sense", 0)) > 0:
                specials.append(f"육감 {v}")
            if (v := info.get("support_rating", 0)) > 0:
                specials.append(f"지지도 {v}")
            if (v := info.get("perception_interference", 0)) > 0:
                specials.append(f"인식방해 {v}")
            if specials:
                line += f", 특이 [{', '.join(specials)}]"

            line += f", 정수슬롯 {info.get('essence_slot_max', 5)}"

            # ★ Stage 7: 빛 자원 활성 시만 노출 (★ 1층 어둠 본질)
            light_state = info.get("light_state") or {}
            if light_state.get("has_active_light"):
                src = light_state.get("active_source_name", "")
                dur = light_state.get("remaining_duration_hours", 0.0)
                line += f", 빛 [{src} {dur}h 남음]"
                cd = light_state.get("cooldown_remaining_hours", 0.0)
                if cd > 0.0:
                    line += f" 회복 대기 {cd}h"
            v2_lines.append(line)

        v2_block = (
            "캐릭터 스탯 (★ 작품 본질):\n"
            + "\n".join(v2_lines)
            + "\n\n"
            "특이 스탯은 일상/대화/행동 본질에 영향:\n"
            "- 집착: 강박적 추적, 두려움/매료 발산\n"
            "- 육감: 거짓말 감지, 위험 직감, 함정 직감\n"
            "- 지지도: 우두머리 권위, 명령 수행률, 부족 충성도\n"
            "- 인식방해: 빙의 정체 은폐, 현대 지식 발설해도 NPC 인지 왜곡\n\n"
        )

    # ★ Stage 1 (2026-05-07): WorldState + Location 진짜 출력 (★ Layer 4 본질)
    world_state = ctx.get("v2_world_state") or {}
    if world_state:
        ws_lines = ["게임 진행 상태 (★ 작품 본질):"]
        ws_lines.append(
            f"- 라운드: {world_state.get('current_round', 1)} "
            "(★ 라프도니아 N번째 도전)"
        )
        ws_lines.append(
            f"- 미궁 시간: {world_state.get('hours_in_dungeon', 0)}시간"
        )
        if world_state.get("is_dimension_collapse"):
            ws_lines.append(
                "- ★ 차원 붕괴 진행 중 (★ 100판 1번 재앙)"
            )
        if world_state.get("is_dark_zone"):
            ws_lines.append(
                "- ★ 어둠 영역: 빛 없으면 가시거리 10m, "
                "몬스터 비활성화 가능"
            )
        if rifts := world_state.get("active_rifts"):
            ws_lines.append(f"- 활성 균열: {', '.join(rifts)}")
        if party := world_state.get("party_members"):
            ws_lines.append(f"- 파티원: {', '.join(party)}")
        if shares := world_state.get("party_share_ratios"):
            shares_str = ", ".join(
                f"{n} {int(r * 100)}%" for n, r in shares.items()
            )
            ws_lines.append(f"- 분배 룰: {shares_str}")
        # ★ Stage 7: 동적 현상금 (PvP 진행 중)
        if bounties := world_state.get("active_bounties"):
            ws_lines.append(f"- 활성 현상금 ({len(bounties)}):")
            for b in bounties:
                target = b.get("target_name", "")
                amount = b.get("amount_stones", 0)
                issuer = b.get("issuer_name", "")
                faction = b.get("issuer_faction")
                cond = b.get("kill_condition", "")
                fac_str = f"/{faction}" if faction else ""
                ws_lines.append(
                    f"  * {target}: {amount:,}스톤 "
                    f"(발령 {issuer}{fac_str}, {cond})"
                )
        v2_block += "\n".join(ws_lines) + "\n\n"

    loc = ctx.get("v2_initial_location") or {}
    if loc:
        loc_lines = ["시작 위치:"]
        loc_lines.append(f"- 영역: {loc.get('realm', '')}")
        if loc.get("floor"):
            loc_lines.append(f"- 층: {loc['floor']}층")
        if loc.get("sub_area"):
            loc_lines.append(f"- 세부 위치: {loc['sub_area']}")
        if loc.get("rift_id"):
            loc_lines.append(f"- 균열 ID: {loc['rift_id']}")
        loc_lines.append(
            f"- 가시거리: {loc.get('visibility_meters', 10)}m "
            "(★ 빛 없으면 10m)"
        )
        loc_lines.append(
            f"- 빛: {'활성' if loc.get('has_light') else '비활성 (★ 어둠)'}"
        )
        v2_block += "\n".join(loc_lines) + "\n\n"
        v2_block += (
            "환경은 일상/대화/행동에 진짜 영향:\n"
            "- 어둠: 빛 없이 시야 10m 한도, 몬스터 활성화 X (★ 빛 자원 필수)\n"
            "- 균열: 미궁 속 미궁 (★ 추가 인원 무작위 진입 가능)\n"
            "- 차원 붕괴: 진짜 재앙 (★ 100판 1번)\n"
            "- 분배: 9:1 / 6:4 등 사전 합의\n\n"
        )

    # ★ Stage 2 (2026-05-07): Floor1Definition prompt 진짜 출력 (Layer 4)
    floor_def = ctx.get("v2_floor_definition") or {}
    if floor_def:
        fd_lines = ["현재 층 정의 (★ 작품 본질):"]
        fd_lines.append(
            f"- 이름: {floor_def.get('name', '')} "
            f"({floor_def.get('floor_number', 0)}층)"
        )
        fd_lines.append(
            f"- 기본 시간: {floor_def.get('base_time_hours', 0)}시간"
        )
        fd_lines.append(
            f"- 기본 가시거리: {floor_def.get('base_visibility_meters', 0)}m"
        )
        if floor_def.get("is_dark_default"):
            fd_lines.append(
                "- ★ 어둠 기본: 빛 없으면 몬스터 활성화 X"
            )

        sub_areas = floor_def.get("sub_areas") or []
        if sub_areas:
            fd_lines.append(f"\nSub Areas ({len(sub_areas)}):")
            for sa in sub_areas:
                line = f"- {sa.get('name', '')}"
                if lt := sa.get("landmark_type"):
                    line += f" ({lt})"
                line += f": {sa.get('description', '')}"
                if af := sa.get("accessible_from"):
                    line += f" → 인접 [{', '.join(af)}]"
                if mn := sa.get("monster_names"):
                    line += f", 몬스터 [{', '.join(mn)}]"
                fd_lines.append(line)

        monsters = floor_def.get("monsters") or []
        if monsters:
            fd_lines.append(f"\n등장 몬스터 ({len(monsters)}):")
            for m in monsters:
                line = (
                    f"- {m.get('name', '')} "
                    f"({m.get('grade', 0)}등급, {m.get('area', '')})"
                )
                line += f": {m.get('behavior', '')}"
                if not m.get("requires_light", True):
                    line += " (★ 어둠 활성 가능)"
                if drops := m.get("drops"):
                    drop_names = [d.get("essence_name", "") for d in drops]
                    line += f" → {', '.join(drop_names)}"
                fd_lines.append(line)

        light_sources = floor_def.get("light_sources") or []
        if light_sources:
            fd_lines.append(f"\n빛 자원 ({len(light_sources)}):")
            for ls in light_sources:
                line = f"- {ls.get('name', '')} ({ls.get('light_type', '')})"
                duration = ls.get("duration_hours")
                if duration:
                    line += f": {duration}시간 지속"
                else:
                    line += ": 단발"
                if cd := ls.get("cooldown_hours"):
                    line += f", 회복 {cd}시간"
                line += f", 반경 {ls.get('radius_meters', 0)}m"
                if cost := ls.get("cost_stones"):
                    line += f", {cost}스톤"
                if ls.get("is_consumable"):
                    line += " (소비)"
                if race := ls.get("requires_race"):
                    line += f" — {race} 한정"
                fd_lines.append(line)

        bounty = floor_def.get("bounty_config")
        if bounty:
            fd_lines.append("\nPvP / 약탈자 시스템:")
            ms = bounty.get("message_stone") or {}
            if ms:
                ms_line = (
                    f"- 메시지 스톤: 반경 {ms.get('range_meters', 0)}m 통신"
                )
                if ms.get("requires_pre_resonance"):
                    ms_line += " (★ 미리 공명 필수)"
                fd_lines.append(ms_line)
            factions = bounty.get("known_factions") or []
            if factions:
                fd_lines.append(f"- 알려진 약탈자 집단 ({len(factions)}):")
                for fac in factions:
                    fac_line = f"  - {fac.get('name', '')}"
                    primary = fac.get("primary_floors") or []
                    if primary:
                        floors_str = ", ".join(f"{n}층" for n in primary)
                        fac_line += f" ({floors_str} 주 무대)"
                    if desc := fac.get("description"):
                        fac_line += f": {desc}"
                    fd_lines.append(fac_line)
            std = bounty.get("standard_bounty_stones", 0)
            esc = bounty.get("escalated_bounty_stones", 0)
            if std and esc:
                fd_lines.append(
                    f"- 현상금: 표준 {std:,}스톤 → 강화 {esc:,}스톤"
                )

        rifts = floor_def.get("rifts") or []
        if rifts:
            fd_lines.append(f"\n균열 ({len(rifts)}):")
            for r in rifts:
                line = f"- {r.get('name', '')} ({r.get('rift_id', '')})"
                if desc := r.get("description"):
                    line += f": {desc}"
                boss_label = r.get("boss_monster_name") or "(자료 X)"
                line += f"\n  보스: {boss_label} ({r.get('boss_grade', 0)}등급"
                if r.get("boss_is_variant"):
                    line += ", 변종"
                drop_pct = int(r.get("boss_drop_rate", 0) * 100)
                line += f", {drop_pct}% 정수 드롭)"
                if regs := r.get("regular_monster_names"):
                    line += f"\n  일반: {', '.join(regs)}"
                if entries := r.get("entry_methods"):
                    line += f"\n  진입: {', '.join(entries)}"
                    if grade := r.get("intentional_offering_grade"):
                        line += f" ({grade}등급 마석 공물)"
                if hidden := r.get("hidden_pieces"):
                    line += f"\n  히든: {', '.join(hidden)}"
                fd_lines.append(line)

        v2_block += "\n".join(fd_lines) + "\n\n"
        v2_block += (
            "층 본질 LLM 가이드 (★ 일상/대화/행동 영향):\n"
            "- 빛/어둠: 빛 없으면 가시거리 10m, 일부 몬스터 활성화 X\n"
            "- 빛 자원 관리 (★ 11화): 횃불 3일/정령 10시간 한정,\n"
            "  빛 활성 시 몬스터 등장 위험 ↑, 칼날늑대/레이스는 어둠도 활성\n"
            "- 영역별 몬스터: 노움은 남쪽, 칼날늑대/레이스는 동쪽 등\n"
            "- 비석 공동: 의도적 균열 진입 (★ 8등급 마석 공물 → 초록색 포탈)\n"
            "- 시간 한도: 168시간 (★ 1주, 1층 한정)\n"
            "- 균열 본질 (★ 27/34화):\n"
            "  * 균열 = 미궁 속 미궁 (인스턴트 던전)\n"
            "  * 탈출: 수호자 처치 → 포탈\n"
            "  * 1-5층 균열 = 매번 리셋\n"
            "  * 추가 인원 무작위 진입 가능 (★ 의도적 진입도 1층 전역 포탈)\n"
            "- PvP 본질 (★ 10/11화):\n"
            "  * 메시지 스톤으로 약탈자 정보 전달 (★ 위치/추적/현상금)\n"
            "  * 약탈자 집단은 입막음/강탈/보복 목적\n"
            "  * 정수 보이면 강탈 시도 위험 ↑\n"
            "  * 위치 노출 시 즉각 이동 또는 대처\n\n"
            "1층 진행 룰 (★ 본문 본질):\n"
            "- 시간: 1층 한도 168시간 (★ 7일). 휴식 4시간씩 교대 (★ 27화)\n"
            "- 챕터: 균열 진입 시 챕터 단위 진행 (★ 빙하굴 1챕터 = 6시간, 102화)\n"
            "- 정수 흡수 메커니즘 (★ 13/14화):\n"
            "  * 정수와 살이 맞닿으면 자동 흡수 (★ 다른 캐릭터에게 먹이기 가능)\n"
            "  * 흡수 X면 30분 후 자연 소멸\n"
            "  * 약탈자가 정수 보면 강탈 시도 (★ 4명 이내 위협으로 도주 가능)\n"
            "- 마석 분배 룰 (★ 11/12/17화):\n"
            "  * 일반 9:1 (★ 메인 딜러 우대)\n"
            "  * 검사/궁수 강화 등급은 중량 우대 분배\n"
            "  * 사전 합의 또는 공헌도 기반\n"
            "- 마석 회수: 시신 사라질 때 떨어진 마석만 줍기 (★ 13화)\n"
            "- 화살 회수: 본문 룰 — 그냥 주워서 사용 (★ 11화)\n\n"
        )

    return (
        f"당신은 한국어 텍스트 어드벤처 게임의 GM입니다.\n\n"
        f"세계관:\n"
        f"- 작품: {ctx['work_name']} ({ctx['work_genre']})\n"
        f"- 배경: {ctx['world_setting']}\n"
        f"- 톤: {ctx['world_tone']}\n"
        f"- 규칙: {', '.join(ctx['world_rules'])}\n\n"
        f"등장 인물:\n"
        f"- 주인공: {main_name} ({ctx['main_character_role']})\n"
        f"{supporting_line}\n"
        f"{v2_block}"
        f"현재 위치: {ctx['current_location']}\n"
        f"현재 턴: {ctx['current_turn']}\n\n"
        f"스타일 규칙:\n"
        f"- 격식체 사용 (...입니다, ...있습니다)\n"
        f"- 자연스러운 격식 (공문서체 X)\n"
        f"- 응답 길이는 유저 액션에 비례\n"
        f"- ★ 한국어만 (한자 X)\n"
        f"- ★ 응답은 반드시 완전한 문장으로 끝낼 것 (다/요/까/.)\n\n"
        f"호칭 규칙 (★ 본인 finding #5):\n"
        f"- 주인공 호칭은 '{main_name}'으로 일관되게\n"
        f"- '플레이어', '플레이어님' 같은 메타 단어 절대 사용 X\n"
        f"- 또는 2인칭 '당신'을 일관되게 사용 (★ 섞어 쓰기 X)\n\n"
        f"진행 규칙 (★ 본인 finding #4):\n"
        f"- 매 턴 위치 변화 또는 새 이벤트가 발생 (★ 단순 반복 X)\n"
        f"- 같은 묘사 / 같은 선택지 반복 절대 X\n"
        f"- 주인공 행동에 따라 NPC, 환경, 단서가 진짜 다르게 등장\n"
        f"- 이전 턴의 결과가 현재 턴에 반영 (★ 인과관계)\n\n"
        f"응답 구조 (★ 본인 finding #1):\n"
        f"- 묘사: 2-4 문장 (★ 현재 상황, 감각, 분위기)\n"
        f"- 선택지: 매 턴 정확히 3개 (★ 첫 턴 포함)\n"
        f"  - 형식: '1. ...', '2. ...', '3. ...' (★ 새 줄 분리)\n"
        f"  - 각 선택지는 서로 다른 방향 / 결과를 암시\n"
        f"  - 단순 변형 X (★ '빠르게'/'천천히' 같은 속도 차이만 X)\n"
    )


class MockGMAgent:
    """Mock GM (★ 테스트용, Layer 2 통합 후도 유지)."""

    def __init__(self, mock_responses: list[str] | None = None) -> None:
        self._responses = mock_responses or [
            "당신은 던전 입구에 도착했습니다. "
            "어두운 통로 앞에서 잠시 멈춰 섰습니다. 어떻게 하시겠습니까?",
        ]
        self._call_count = 0

    def generate_response(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GMResponse:
        text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return GMResponse(
            text=text,
            cost_usd=0.0,
            latency_ms=10,
            mechanical_passed=True,
            mechanical_failures=[],
            total_score=100.0,
            verify_passed=True,
        )


class GMAgent:
    """GM Agent (★ Tier 1.5 D4).

    흐름:
      1. Plan + State → 컨텍스트 빌드
      2. system prompt + user prompt
      3. dynamic max_tokens (Layer 1)
      4. LLM 호출 (game_llm)
      5. ★ Mechanical 검증 (TruncationDetectionRule 포함)
      6. ★ 통합 점수 반환

    ★ Cross-Model 강제 (본인 #18):
      - game_llm ≠ verify_llm
      - verify_llm 없으면 Mechanical만 (점수 = Mechanical 100%)
    """

    def __init__(
        self,
        game_llm: GameLLMClient,
        verify_llm: LLMClient | None = None,
        mechanical_checker: MechanicalChecker | None = None,
    ) -> None:
        """
        Args:
            game_llm: 게임 응답 생성 LLM
            verify_llm: Cross-Model 검증 LLM (None이면 Mechanical만)
                        game_llm과 같은 모델이면 ValueError
            mechanical_checker: Layer 1 자산 (TruncationDetectionRule 포함)
        """
        if verify_llm is not None and verify_llm.model_name == game_llm.model_name:
            raise ValueError(
                f"Cross-Model violation: game_llm and verify_llm both "
                f"'{game_llm.model_name}'. Use different models (★ 본인 #18)."
            )

        self._game_llm = game_llm
        self._verify_llm = verify_llm
        mechanical = mechanical_checker or MechanicalChecker()
        self._checker = mechanical  # 호환성 유지 (★ 기존 tests용)

        # ★ ★ A1.5: IntegratedVerifier (Mechanical + LLM Judge 진짜 통합)
        # verify_llm 있으면 LLMJudge 활성화 (★ Cross-Model)
        judge: LLMJudge | None = None
        if verify_llm is not None:
            judge = LLMJudge(judge_client=verify_llm)
        self._verifier = IntegratedVerifier(
            mechanical=mechanical,
            judge=judge,
            skip_judge_on_critical=True,  # critical 시 judge 스킵 (비용/지연 ↓)
        )

    def generate_response(
        self,
        plan: Plan,
        state: GameState,
        user_action: str,
    ) -> GMResponse:
        """게임 응답 생성 + 검증."""
        ctx = build_game_context(plan, state)
        system = _gm_system_prompt(ctx)
        user_prompt = self._build_user_prompt(state, user_action)
        prompt = Prompt(system=system, user=user_prompt)

        if state.turn == 0:
            max_tokens = 800
        else:
            max_tokens = compute_game_max_tokens(user_action)

        try:
            response = self._game_llm.generate(prompt, max_tokens=max_tokens)
        except Exception as e:
            return GMResponse(
                text="",
                error=f"LLM call failed: {e}",
                mechanical_passed=False,
                mechanical_failures=[str(e)],
                total_score=0.0,
                verify_passed=False,
            )

        # ★ ★ ★ A1.5: 통합 검증 (Mechanical + LLM Judge, ★ verify_llm 진짜 호출!)
        verify_ctx: dict[str, Any] = {
            "language": "ko",
            "character_response": True,
            "user_input": user_action,
        }
        # criteria는 verify_llm 있을 때만 (★ judge 호출 결정)
        criteria = GAME_CRITERIA if self._verify_llm is not None else None
        integrated_result = self._verifier.verify(
            response.text, verify_ctx, criteria=criteria
        )
        mech_result = integrated_result.mechanical

        # ★ 통합 점수: Judge 호출됐으면 judge.score, 아니면 Mechanical 기준
        if integrated_result.judge is not None:
            total_score = integrated_result.judge.score
        else:
            # ★ hardcoded 100.0 차단 (codex 5.5 진단) — mech_result.score 진짜 점수
            total_score = mech_result.score
        verify_passed = integrated_result.passed

        return GMResponse(
            text=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
            mechanical_passed=mech_result.passed,
            mechanical_failures=[
                f"{f.rule}: {f.detail}" for f in mech_result.failures
            ],
            total_score=total_score,
            verify_passed=verify_passed,
        )

    @staticmethod
    def _build_user_prompt(state: GameState, user_action: str) -> str:
        """최근 history + 현재 액션으로 user prompt 구성.

        ★ 본인 풀 플레이 finding 반영:
          - finding #3: history 1턴 → 3턴, 200자 → 500자 (★ 이전 선택 반영)
          - finding #1: 첫 턴 (state.turn==0) 명시 (★ 빈 입력도 시작)
          - finding #4: 일반 턴에서 '결과 반영 + 새 이벤트' 명시
        """
        parts: list[str] = []

        # ★ 최근 3턴 (★ finding #3, 1 → 3)
        if state.history:
            recent_turns = state.history[-3:]
            for h in recent_turns:
                parts.append(
                    f"[이전 턴 {h.turn}]\n"
                    f"플레이어: {h.user_action}\n"
                    f"GM: {h.gm_response[:500]}\n"  # ★ 200 → 500
                )

        # ★ 현재 턴 — 첫 턴 vs 일반 턴 분기 (★ finding #1, #4)
        if state.turn == 0:
            parts.append(
                f"[현재 턴 {state.turn + 1}] (★ 게임 시작)\n"
                f"플레이어: {user_action or '시작'}\n"
                f"GM: 시작 위치 묘사 + 3가지 행동 선택지 제공"
            )
        elif state.history:
            parts.append(
                f"[현재 턴 {state.turn + 1}]\n"
                f"플레이어가 '{user_action}'를 선택했음.\n"
                f"위 선택의 결과를 반영하여 진행 + 새 3가지 선택지 제공.\n"
                f"이전 묘사와 다른 새 위치/이벤트/단서 등장 (★ 단순 반복 X).\n"
                f"플레이어: {user_action}"
            )
        else:
            parts.append(f"[현재 턴 {state.turn + 1}]\n플레이어: {user_action}")

        return "\n".join(parts)
