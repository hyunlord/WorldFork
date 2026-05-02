"""AI Playtester Runner — Tier 1 W1 D6 본격 turn loop.

AI_PLAYTESTER 4.1 + 5.2 (Reproduction prompt) 기반.

W1 D6 워크플로 (★ 본격 turn loop):
  1. 게임 LLM (9B Q3)으로 game intro 생성 (turn 0)
  2. turn 1..max_turns 루프:
     a. Playtester CLI가 user action 결정
     b. Game LLM이 응답 생성 (★ dynamic max_tokens)
     c. TurnLog 기록 (turn별 system_prompt + user_input + game_response)
  3. Playtester가 세션 summary JSON 출력
  4. PlaytesterSessionResult 반환 (★ playthrough_log 풍부화)

★ 자료 5.2 정신:
  playthrough[turn_n] = TurnLog(system_prompt, user_input, game_response)
  → seed_converter가 target_turn 추출 가능
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.llm.client import LLMClient, Prompt
from core.verify.mechanical import MechanicalChecker  # ★ D4 Made-but-Never-Used 해결

from .persona import Persona, is_compatible

PLAYTESTER_RUNS_DIR = Path(__file__).resolve().parents[2] / "runs" / "playtester"


@dataclass
class TurnLog:
    """단일 턴 기록 (★ 자료 5.2: target_turn = playthrough[turn_n]).

    Attributes:
        turn_n: 턴 번호 (0=intro, 1+=user/game 교대)
        role: "game_intro" / "game_response"
        system_prompt: 게임 LLM에 전달된 system prompt (해당 턴)
        user_input: 사용자(또는 playtester) 액션
        game_response: 게임 LLM의 응답
        latency_ms: 게임 LLM 응답 시간
        context: 추가 컨텍스트 (language, character_response 등)
    """

    turn_n: int
    role: str
    system_prompt: str = ""
    user_input: str = ""
    game_response: str = ""
    latency_ms: int = 0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaytesterFinding:
    """페르소나가 발견한 이슈."""

    severity: str
    category: str
    turn_n: int
    description: str
    reproduction_input: str = ""
    reproduction_response: str = ""
    # ★ W1 D6: 자료 5.2를 위한 turn 시점 context (fallback용)
    turn_context: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaytesterSessionResult:
    """페르소나 1회 세션 결과."""

    persona_id: str
    work_name: str
    completed: bool
    n_turns_played: int
    elapsed_seconds: float
    fun_rating: int
    would_replay: bool
    abandoned: bool
    abandon_reason: str | None
    abandon_turn: int | None
    findings: list[PlaytesterFinding] = field(default_factory=list)
    playthrough_log: list[dict[str, Any]] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


class PlaytesterError(Exception):
    """Playtester 실행 오류."""
    pass


class PlaytesterRunner:
    """AI Playtester 실행기 — Tier 1 본격 버전.

    Args:
        persona: 시뮬할 페르소나
        game_client: 게임 GM/NPC LLM (응답 생성, 9B Q3 권장)
        playtester_client: Playtester LLM (페르소나로 user 액션 생성, CLI)

    Raises:
        PlaytesterError: 페르소나 / game LLM 비호환
    """

    def __init__(
        self,
        persona: Persona,
        game_client: LLMClient,
        playtester_client: LLMClient,
    ) -> None:
        if not is_compatible(persona, game_client.model_name):
            raise PlaytesterError(
                f"Persona '{persona.id}' incompatible with game LLM "
                f"'{game_client.model_name}' "
                f"(forbidden: {persona.forbidden_game_llms})"
            )

        self.persona = persona
        self.game_client = game_client
        self.playtester_client = playtester_client
        self._checker = MechanicalChecker()  # ★ D4 Layer 1 자산 진짜 사용

    def run_session(
        self,
        work_name: str,
        max_turns: int = 30,
        time_limit_seconds: float = 1800,
    ) -> PlaytesterSessionResult:
        """페르소나로 게임 1회 시뮬 (★ W1 D6 본격 turn loop).

        흐름:
            turn 0: game_intro (Game LLM)
            turn 1..max_turns:
                a. Playtester가 user action 결정 (CLI)
                b. Game LLM이 응답 (Local, ★ dynamic max_tokens)
                c. TurnLog 기록
                d. FINDING 발견 시 turn_context 첨부 (자료 5.2)
            종료: max_turns / abandon / time_limit / error

        Args:
            work_name: 작품명 / 시나리오
            max_turns: 최대 턴 수
            time_limit_seconds: 시간 제한 (초)

        Returns:
            PlaytesterSessionResult (★ playthrough_log 풍부화)
        """
        start_time = time.time()
        playthrough: list[TurnLog] = []
        findings: list[PlaytesterFinding] = []

        # ===== Turn 0: Game Intro =====
        intro_system = self._game_intro_system_prompt()
        intro_user = self._game_intro_user_prompt(work_name)

        try:
            game_intro_response = self.game_client.generate(
                Prompt(system=intro_system, user=intro_user),
                max_tokens=500,
            )
        except Exception as e:
            return self._abandon_result(
                work_name=work_name,
                playthrough=playthrough,
                reason=f"Game intro failed: {e}",
                turn=0,
                start_time=start_time,
            )

        playthrough.append(
            TurnLog(
                turn_n=0,
                role="game_intro",
                system_prompt=intro_system,
                user_input=intro_user,
                game_response=game_intro_response.text,
                latency_ms=game_intro_response.latency_ms,
                context={"work_name": work_name, "language": "ko"},
            )
        )

        # ===== Turn 1+ Loop: Playtester ↔ Game =====
        last_game_response = game_intro_response.text
        abandoned = False
        abandon_reason: str | None = None
        abandon_turn: int | None = None

        for turn_n in range(1, max_turns + 1):
            # Time limit
            if time.time() - start_time > time_limit_seconds:
                abandoned = True
                abandon_reason = f"Time limit {time_limit_seconds}s exceeded"
                abandon_turn = turn_n
                break

            # 1. Playtester action
            try:
                playtester_response = self.playtester_client.generate(
                    self._playtester_action_prompt(
                        last_game_response=last_game_response,
                        turn_n=turn_n,
                        max_turns=max_turns,
                    ),
                    max_tokens=500,
                )
            except Exception as e:
                abandoned = True
                abandon_reason = f"Playtester failed at turn {turn_n}: {e}"
                abandon_turn = turn_n
                break

            user_action, finding, should_abandon = self._parse_playtester_action(
                playtester_response.text, turn_n,
            )

            if finding:
                # ★ 자료 5.2: turn 시점 context 첨부 (fallback용)
                finding.turn_context = {
                    "system_prompt": self._game_intro_system_prompt(),
                    "user_input": user_action,
                    "language": "ko",
                    "character_response": True,
                }
                findings.append(finding)

            if should_abandon:
                abandoned = True
                abandon_reason = f"Playtester abandoned at turn {turn_n}"
                abandon_turn = turn_n
                break

            if not user_action:
                abandoned = True
                abandon_reason = f"Empty user action at turn {turn_n}"
                abandon_turn = turn_n
                break

            # 2. Game LLM 응답 (★ dynamic max_tokens)
            dynamic_tokens = self._compute_max_tokens(user_action)
            game_system = self._game_intro_system_prompt()
            try:
                game_response = self.game_client.generate(
                    Prompt(system=game_system, user=user_action),
                    max_tokens=dynamic_tokens,
                )
            except Exception as e:
                abandoned = True
                abandon_reason = f"Game LLM failed at turn {turn_n}: {e}"
                abandon_turn = turn_n
                break

            # 3. ★ Mechanical 검증 (Layer 1 자산, D4)
            mech_ctx = {
                "language": "ko",
                "character_response": True,
                "user_input": user_action,
            }
            mech_result = self._checker.check(game_response.text, mech_ctx)
            if not mech_result.passed:
                for failure in mech_result.failures:
                    findings.append(PlaytesterFinding(
                        severity=failure.severity,
                        category=failure.rule,
                        turn_n=turn_n,
                        description=failure.detail,
                        reproduction_input=user_action,
                        reproduction_response=game_response.text[:300],
                    ))

            # 4. 기록
            playthrough.append(
                TurnLog(
                    turn_n=turn_n,
                    role="game_response",
                    system_prompt=game_system,
                    user_input=user_action,
                    game_response=game_response.text,
                    latency_ms=game_response.latency_ms,
                    context={
                        "language": "ko",
                        "character_response": True,
                        "mechanical_passed": mech_result.passed,
                    },
                )
            )
            last_game_response = game_response.text

            time.sleep(0.1)  # ★ 메모리 / 서버 안정

        # ===== Final summary =====
        elapsed = time.time() - start_time
        n_turns = len(playthrough) - 1  # intro 제외
        completed = (not abandoned) and n_turns >= max_turns

        try:
            summary_response = self.playtester_client.generate(
                self._playtester_summary_prompt(
                    playthrough=playthrough,
                    findings=findings,
                    completed=completed,
                ),
                max_tokens=1000,
            )
            summary_data = self._parse_summary(summary_response.text)
        except Exception:
            summary_data = {
                "fun_rating": 0,
                "would_replay": False,
                "summary": "Summary generation failed",
            }

        return PlaytesterSessionResult(
            persona_id=self.persona.id,
            work_name=work_name,
            completed=completed,
            n_turns_played=n_turns,
            elapsed_seconds=elapsed,
            fun_rating=int(summary_data.get("fun_rating", 0)),
            would_replay=bool(summary_data.get("would_replay", False)),
            abandoned=abandoned,
            abandon_reason=abandon_reason,
            abandon_turn=abandon_turn,
            findings=findings,
            playthrough_log=[asdict(log) for log in playthrough],
        )

    # ---------- Game prompts ----------

    @staticmethod
    def _game_intro_system_prompt() -> str:
        """게임 GM system prompt (★ W1 D6 verbose 대응 갱신)."""
        return (
            "당신은 한국어 텍스트 어드벤처 게임의 GM입니다.\n\n"
            "스타일 규칙:\n"
            "- 격식체 사용 (...입니다, ...있습니다)\n"
            "- 자연스러운 격식 (공문서체 X, '존경하는' / '귀하' / '~습니까' X)\n"
            "- ★ 응답 길이는 유저 액션에 비례:\n"
            "  유저가 짧게(1-5단어) → 응답도 짧게(1-2 문장)\n"
            "  유저가 자세히 → 응답도 자세히(3-5 문장)\n"
            "- 한국어만 (영단어 + 괄호 한국어 형식 X)\n"
            "- 행동 선택지는 명확히 (3개 이하 권장 — 선택 마비 회피)\n\n"
            "역할: 신참 모험가 투르윈의 모험 GM"
        )

    @staticmethod
    def _game_intro_user_prompt(work_name: str) -> str:
        """첫 응답 user prompt."""
        return (
            f"'{work_name}' 시나리오를 시작해 주세요. "
            f"투르윈은 신참 모험가입니다.\n\n"
            f"첫 응답에 다음을 포함해 주세요:\n"
            f"1. 현재 위치 (1-2 문장)\n"
            f"2. 보이는 것 / 들리는 것 (1-2 문장)\n"
            f"3. 가능한 행동 2-3개 명시"
        )

    # ---------- Playtester prompts / parsing ----------

    def _playtester_action_prompt(
        self,
        last_game_response: str,
        turn_n: int,
        max_turns: int,
    ) -> Prompt:
        """매 턴 playtester가 user action 결정용 prompt."""
        system = self.persona.prompt_template + (
            f"\n\n현재 턴: {turn_n}/{max_turns}\n"
            f"매 턴 다음 중 하나로 응답:\n"
            f"  ACTION: <짧은 행동/말>\n"
            f"  FINDING: <severity:critical|major|minor> <category> <description>\n"
            f"  ABANDON: <이유>\n"
            f"규칙:\n"
            f"  - ACTION만 있으면 게임 진행\n"
            f"  - FINDING + ACTION 동시 OK (이슈 발견 + 계속 플레이)\n"
            f"  - ABANDON은 정말 더 못 할 때만\n"
        )
        user = (
            f"게임 GM의 마지막 응답:\n"
            f"---\n{last_game_response[:1500]}\n---\n\n"
            f"턴 {turn_n}: 페르소나로 응답해 주세요. "
            f"(ACTION / FINDING / ABANDON 형식)"
        )
        return Prompt(system=system, user=user)

    def _parse_playtester_action(
        self, text: str, turn_n: int,
    ) -> tuple[str, PlaytesterFinding | None, bool]:
        """Playtester 응답 파싱.

        Returns:
            (user_action, finding_or_none, should_abandon)
        """
        action = ""
        finding: PlaytesterFinding | None = None
        abandon = False
        action_explicit = False

        for raw_line in text.strip().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            upper = line.upper()
            if upper.startswith("ABANDON:"):
                abandon = True
                break
            elif upper.startswith("FINDING:"):
                finding = self._parse_finding_line(line[8:].strip(), turn_n)
            elif upper.startswith("ACTION:"):
                action = line[7:].strip()
                action_explicit = True
            elif not action_explicit and not action:
                # action prefix 없으면 첫 비어있지 않은 줄을 action으로
                action = line

        return action, finding, abandon

    @staticmethod
    def _parse_finding_line(text: str, turn_n: int) -> PlaytesterFinding | None:
        """FINDING: <severity> <category> <description> 파싱."""
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            return None
        sev = parts[0].rstrip(":").lower()
        if sev not in ("critical", "major", "minor"):
            sev = "minor"
        return PlaytesterFinding(
            severity=sev,
            category=parts[1].rstrip(":"),
            turn_n=turn_n,
            description=parts[2],
        )

    def _playtester_summary_prompt(
        self,
        playthrough: list[TurnLog],
        findings: list[PlaytesterFinding],
        completed: bool,
    ) -> Prompt:
        """세션 종료 summary prompt."""
        system = (
            self.persona.prompt_template +
            "\n\n세션 종료. JSON 형식으로 평가:\n"
            '{"fun_rating": 1-5, "would_replay": true/false, "summary": "..."}'
        )
        user = (
            f"플레이 요약:\n"
            f"- 턴 수: {len(playthrough) - 1}\n"
            f"- 완주: {completed}\n"
            f"- 발견 이슈: {len(findings)}\n\n"
            f"JSON 평가만 출력 (다른 설명 X)."
        )
        return Prompt(system=system, user=user)

    @staticmethod
    def _parse_summary(text: str) -> dict[str, Any]:
        """JSON summary 파싱 (Filter Pipeline)."""
        from core.eval.filter_pipeline import STANDARD_FILTER_PIPELINE
        result = STANDARD_FILTER_PIPELINE.extract(text)
        if result.succeeded and result.parsed:
            return result.parsed
        return {"fun_rating": 0, "would_replay": False, "summary": ""}

    @staticmethod
    def _compute_max_tokens(user_action: str) -> int:
        """user 액션 길이별 max_tokens 동적 결정.

        ★ W1 D6 임시 — Phase 3 (작업 8)에서 core/llm/dynamic_token_limiter.py로 이동.
        """
        from core.llm.dynamic_token_limiter import compute_max_tokens
        return compute_max_tokens(user_action)

    def _abandon_result(
        self,
        work_name: str,
        playthrough: list[TurnLog],
        reason: str,
        turn: int,
        start_time: float,
    ) -> PlaytesterSessionResult:
        """초기/즉시 abandon 결과."""
        return PlaytesterSessionResult(
            persona_id=self.persona.id,
            work_name=work_name,
            completed=False,
            n_turns_played=max(0, len(playthrough) - 1),
            elapsed_seconds=time.time() - start_time,
            fun_rating=0,
            would_replay=False,
            abandoned=True,
            abandon_reason=reason,
            abandon_turn=turn,
            findings=[],
            playthrough_log=[asdict(log) for log in playthrough],
        )

    @staticmethod
    def save(result: PlaytesterSessionResult) -> Path:
        """결과를 runs/playtester/에 저장."""
        PLAYTESTER_RUNS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = PLAYTESTER_RUNS_DIR / f"{ts}_{result.persona_id}.json"
        path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
