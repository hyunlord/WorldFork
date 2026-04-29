"""Tier 0 콘솔 게임 루프 (Day 1).

본인이 직접 콘솔에서 5턴 플레이 가능.
Day 2: 분기 추가.
Day 4: LLM Judge로 응답 검증.
Tier 2: 웹 UI로 이동.
"""

from pathlib import Path
from typing import Any

import yaml

from core.llm.cli_client import get_default_game_gm
from core.llm.client import LLMClient, Prompt

from .state import Character, GameState

SCENARIO_DIR = Path(__file__).resolve().parents[2] / "scenarios" / "tier_0"


def load_scenario(scenario_id: str) -> dict[str, Any]:
    """YAML 시나리오 로드."""
    path = SCENARIO_DIR / f"{scenario_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def build_gm_prompt(
    scenario: dict[str, Any],
    state: GameState,
    user_action: str,
) -> Prompt:
    """5-section system prompt 구성 (HARNESS_CORE 7장)."""

    # IDENTITY
    identity = "당신은 텍스트 어드벤처 게임의 게임 마스터(GM)다."

    # TASK
    task = """사용자의 행동을 받아:
1. 결과를 자연스러운 한국어로 묘사 (2-4 문장)
2. 등장 캐릭터의 반응을 캐릭터 페르소나에 맞게 표현
3. 다음 행동 선택지 2-4개 제시 (사용자가 선택하거나 자유 입력)"""

    # SPEC
    pc = scenario["setting"]["player_character"]
    chars_desc = "\n".join(
        f"- {c['name']} ({c['role']}):\n  {c['persona'].strip()}"
        for c in scenario["characters"]
    )
    spec = f"""세계관: {scenario['setting']['world']}

배경:
{scenario['setting']['premise'].strip()}

플레이어 캐릭터: {pc['name']} ({pc['race']}, {pc.get('height', '')}, {pc.get('skin', '')} 피부)
배경: {pc.get('background', '')}

등장 캐릭터:
{chars_desc}

룰:
- 자연스러운 한국어 (번역투 X)
- 캐릭터 일관성 유지
- 절대 "AI", "Claude", "ChatGPT" 같은 자기 정체 노출 X
- 게임 상태 위반 X (인벤토리에 없는 아이템 사용 X)
- 작품명 / 원작 캐릭터명 직접 사용 X (비요른 / 라프도니아 / 정윤강 등 차단)"""

    # OUTPUT FORMAT
    output_format = """한국어 자연스러운 묘사. 2-4 문장 + 선택지 2-4개.
JSON 형식 X — Day 1은 자유 텍스트.

응답 끝에 다음 형식의 선택지 추가:
다음 행동:
- 선택지 1
- 선택지 2
- 선택지 3
- (자유 입력)

응답에는 묘사와 선택지만 포함하라. 메타 발언 / 작가 노트 X."""

    # EXAMPLES
    examples = """[예시]
사용자 행동: "셰인에게 다가가 인사"
GM 응답:
셰인이 환하게 웃으며 손을 마주 든다.
"투르윈, 드디어 오셨군요. 길드 등록은 끝난 듯하니, 이제 미궁 진입 절차를 밟으면 되겠습니다."
그가 옆 사무실 문을 가리킨다. 안에서 묵직한 목소리가 흘러나온다.

다음 행동:
- 사무실로 들어간다
- 셰인에게 미궁에 대해 물어본다
- 주변을 좀 더 둘러본다
- (자유 입력)"""

    system = f"""# IDENTITY
{identity}

# TASK
{task}

# SPEC
{spec}

# OUTPUT FORMAT
{output_format}

# EXAMPLES
{examples}"""

    # 최근 history (5턴까지)
    if state.history:
        history_lines = []
        for log in state.history[-5:]:
            history_lines.append(f"[Turn {log.turn}]")
            history_lines.append(f"사용자: {log.user_action}")
            response_preview = log.gm_response[:200]
            if len(log.gm_response) > 200:
                response_preview += "..."
            history_lines.append(f"GM: {response_preview}")
        history_str = "\n".join(history_lines)
    else:
        history_str = "(첫 턴)"

    user = f"""# RECENT HISTORY
{history_str}

# CURRENT STATE
턴: {state.turn + 1}
위치: {state.location}

# USER ACTION
{user_action}

위 행동에 대한 GM 응답을 작성해라."""

    return Prompt(system=system, user=user)


def initialize_state(scenario: dict[str, Any]) -> GameState:
    """시나리오에서 초기 GameState 생성."""
    state = GameState(scenario_id=scenario["id"])
    state.location = scenario["opening_scene"]["location"]

    pc = scenario["setting"]["player_character"]
    state.characters["player"] = Character(
        name=pc["name"],
        role="주인공",
        hp=100,
    )

    for char_def in scenario["characters"]:
        state.characters[char_def["id"]] = Character(
            name=char_def["name"],
            role=char_def["role"],
            hp=100,
        )

    return state


def print_opening(scenario: dict[str, Any]) -> None:
    """시나리오 오프닝 출력."""
    print("\n" + "=" * 60)
    print(f"  {scenario['title']}")
    print("=" * 60)
    print()
    print(scenario["opening_scene"]["description"].strip())
    print()
    print("선택:")
    for i, opt in enumerate(scenario["opening_scene"]["initial_options"], 1):
        print(f"  {i}. {opt}")
    print()


def play_game(
    scenario_id: str = "novice_dungeon_run",
    client: LLMClient | None = None,
    max_turns: int = 5,
) -> GameState:
    """콘솔 게임 루프.

    Args:
        scenario_id: 시나리오 식별자
        client: LLM 클라이언트 (None이면 claude_code default)
        max_turns: 최대 턴 (Day 1은 5턴)

    Returns:
        최종 GameState
    """
    scenario = load_scenario(scenario_id)
    state = initialize_state(scenario)

    print_opening(scenario)

    if client is None:
        client = get_default_game_gm()

    print(f"[게임 GM: {client.model_name}]")
    print(f"[최대 {max_turns}턴]")
    print()

    while not state.is_completed(max_turns=max_turns):
        try:
            user_action = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n게임 중단.")
            break

        if not user_action:
            continue

        if user_action.lower() in {"exit", "quit", "종료", "q"}:
            print("\n게임 종료 (사용자 요청).")
            break

        prompt = build_gm_prompt(scenario, state, user_action)

        print()
        print("[GM 응답 생성 중... (~12초)]")
        try:
            response = client.generate(prompt)
        except Exception as e:
            print(f"❌ LLM 호출 실패: {e}")
            print("재시도하시겠습니까? (다른 액션 입력)")
            continue

        print()
        print(response.text)
        print()
        print(
            f"[턴 {state.turn + 1} | "
            f"비용: ${response.cost_usd:.4f} | "
            f"Latency: {response.latency_ms / 1000:.1f}s]"
        )
        print()

        state.add_turn(
            user_action=user_action,
            gm_response=response.text,
            cost_usd=response.cost_usd,
            latency_ms=response.latency_ms,
        )

    print("=" * 60)
    print(
        f"  게임 종료. 총 {state.turn}턴, "
        f"누적 비용 ${state.total_cost_usd():.4f}, "
        f"평균 latency {state.avg_latency_ms() / 1000:.1f}s"
    )
    print("=" * 60)
    print()

    return state


def main() -> None:
    """python -m service.game.loop 진입점."""
    play_game()


if __name__ == "__main__":
    main()
