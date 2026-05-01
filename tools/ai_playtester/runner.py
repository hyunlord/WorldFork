"""AI Playtester Runner — Tier 1 본격 구현 (★ Tier 0 placeholder 대체).

AI_PLAYTESTER 4.1 기반.

워크플로 (W1 D3 간소화):
  1. 게임 LLM (9B Q3)으로 게임 intro 생성
  2. Playtester CLI가 페르소나로 30턴 시뮬 (단일 호출)
  3. JSON 결과 파싱 (Filter Pipeline)
  4. PlaytesterSessionResult 반환

W1 D4-5에서 정식 게임 루프 통합 예정.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from core.llm.client import LLMClient, Prompt

from .persona import Persona, is_compatible

PLAYTESTER_RUNS_DIR = Path(__file__).resolve().parents[2] / "runs" / "playtester"


@dataclass
class PlaytesterFinding:
    """페르소나가 발견한 이슈."""

    severity: str
    category: str
    turn_n: int
    description: str
    reproduction_input: str = ""
    reproduction_response: str = ""


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

    def run_session(
        self,
        work_name: str,
        max_turns: int = 30,
        time_limit_seconds: float = 1800,
    ) -> PlaytesterSessionResult:
        """페르소나로 게임 1회 시뮬 (W1 D3 간소화 버전).

        Args:
            work_name: 작품명 / 시나리오 (예: "novice_dungeon_run")
            max_turns: 최대 턴 수
            time_limit_seconds: 시간 제한 (초)

        Returns:
            PlaytesterSessionResult
        """
        start_time = time.time()

        # 1. 게임 시작 응답 (게임 LLM)
        game_intro_prompt = Prompt(
            system=(
                "당신은 한국어 텍스트 어드벤처 게임의 GM입니다.\n\n"
                "스타일 규칙:\n"
                "- 격식체 사용 (...입니다, ...있습니다)\n"
                "- 자연스러운 격식 (공문서체 X, '존경하는' / '귀하' / '~습니까' X)\n"
                "- 간결한 묘사 (3-5 문장 이내)\n"
                "- 한국어만 (영단어 + 괄호 한국어 형식 X)\n"
                "- 마지막에 명확한 행동 선택지 2-3개 제시\n\n"
                "역할: 신참 모험가 투르윈의 모험 시작 GM"
            ),
            user=(
                f"'{work_name}' 시나리오를 시작해 주세요. "
                f"투르윈은 신참 모험가입니다. "
                f"첫 응답에 다음을 포함해 주세요:\n"
                f"1. 현재 위치 (1-2 문장)\n"
                f"2. 보이는 것 / 들리는 것 (1-2 문장)\n"
                f"3. 가능한 행동 2-3개 명시"
            ),
        )

        try:
            game_intro = self.game_client.generate(
                game_intro_prompt, max_tokens=500
            )
        except Exception as e:
            return PlaytesterSessionResult(
                persona_id=self.persona.id,
                work_name=work_name,
                completed=False,
                n_turns_played=0,
                elapsed_seconds=time.time() - start_time,
                fun_rating=0,
                would_replay=False,
                abandoned=True,
                abandon_reason=f"Game LLM intro failed: {e}",
                abandon_turn=0,
            )

        # 2. Playtester CLI에 페르소나 + 게임 응답 던짐
        playtester_prompt = self._build_playtester_prompt(
            game_intro=game_intro.text,
            max_turns=max_turns,
        )

        try:
            playtester_response = self.playtester_client.generate(
                playtester_prompt, max_tokens=2000
            )
        except Exception as e:
            return PlaytesterSessionResult(
                persona_id=self.persona.id,
                work_name=work_name,
                completed=False,
                n_turns_played=0,
                elapsed_seconds=time.time() - start_time,
                fun_rating=0,
                would_replay=False,
                abandoned=True,
                abandon_reason=f"Playtester CLI failed: {e}",
                abandon_turn=0,
            )

        # 3. 응답 파싱
        return self._parse_playtester_output(
            persona_id=self.persona.id,
            work_name=work_name,
            playtester_text=playtester_response.text,
            game_intro=game_intro.text,
            elapsed_seconds=time.time() - start_time,
        )

    def _build_playtester_prompt(
        self,
        game_intro: str,
        max_turns: int,
    ) -> Prompt:
        system = self.persona.prompt_template + f"\n\n최대 {max_turns}턴까지 플레이."

        user = f"""게임이 시작되었다.

게임 intro 응답:
{game_intro}

너는 위 페르소나로 게임을 플레이해라. {max_turns}턴까지 또는 ABANDON할 때까지.

결과를 JSON으로 출력 (이게 마지막 응답):

```json
{{
  "completed": true,
  "n_turns_played": 30,
  "fun_rating": 3,
  "would_replay": true,
  "abandoned": false,
  "abandon_reason": null,
  "abandon_turn": null,
  "findings": [
    {{
      "severity": "minor",
      "category": "verbose",
      "turn_n": 5,
      "description": "설명"
    }}
  ],
  "summary": "전체 세션 요약 (1-3 문장)"
}}
```

중요: JSON만 출력. 다른 설명 X.
"""
        return Prompt(system=system, user=user)

    def _parse_playtester_output(
        self,
        persona_id: str,
        work_name: str,
        playtester_text: str,
        game_intro: str,
        elapsed_seconds: float,
    ) -> PlaytesterSessionResult:
        from core.eval.filter_pipeline import STANDARD_FILTER_PIPELINE

        result = STANDARD_FILTER_PIPELINE.extract(playtester_text)
        if not result.succeeded or not result.parsed:
            return PlaytesterSessionResult(
                persona_id=persona_id,
                work_name=work_name,
                completed=False,
                n_turns_played=0,
                elapsed_seconds=elapsed_seconds,
                fun_rating=0,
                would_replay=False,
                abandoned=True,
                abandon_reason=f"JSON parse failed: {result.error}",
                abandon_turn=0,
                playthrough_log=[
                    {"role": "game_intro", "text": game_intro},
                    {"role": "playtester_raw", "text": playtester_text[:500]},
                ],
            )

        data = result.parsed

        findings = [
            PlaytesterFinding(
                severity=str(f.get("severity", "minor")),
                category=str(f.get("category", "other")),
                turn_n=int(f.get("turn_n", 0)),
                description=str(f.get("description", "")),
            )
            for f in data.get("findings", [])
            if isinstance(f, dict)
        ]

        return PlaytesterSessionResult(
            persona_id=persona_id,
            work_name=work_name,
            completed=bool(data.get("completed", False)),
            n_turns_played=int(data.get("n_turns_played", 0)),
            elapsed_seconds=elapsed_seconds,
            fun_rating=int(data.get("fun_rating", 0)),
            would_replay=bool(data.get("would_replay", False)),
            abandoned=bool(data.get("abandoned", False)),
            abandon_reason=data.get("abandon_reason"),
            abandon_turn=data.get("abandon_turn"),
            findings=findings,
            playthrough_log=[
                {"role": "game_intro", "text": game_intro},
                {"role": "playtester_summary", "text": str(data.get("summary", ""))},
            ],
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
