"""SimRunner — 단순 오케스트레이터 (★ agent X).

본인 결정:
- agent X (★ 단순 Python 함수)
- gm_agent + player_agent 호출
- turn_handler mutate 트리거
- 결과 누적

본 commit 1차: schema + 빈 run() (★ LLM X mock)
2차 commit: 진짜 1턴 작동
3차 commit: 50턴 자동
4차 commit: 통계 분석
"""

from __future__ import annotations

from service.game.state_v2 import Character

from .player_agent import MockPlayerAgent
from .types import SimConfig, SimResult


class SimRunner:
    """단순 오케스트레이터 (★ agent X).

    본 commit 1차: schema + 빈 run() (★ LLM X)
    2차 commit: 1턴 진짜 작동
    """

    def __init__(
        self,
        config: SimConfig,
        player_agent: MockPlayerAgent | None = None,
    ) -> None:
        self.config = config
        self.player_agent = player_agent or MockPlayerAgent()

    def initialize_party(self) -> dict[str, Character]:
        """파티 초기화 (★ 1층 시작 시점).

        본 commit 1차: 빈 dict 반환 (★ 2차 commit이 init_from_plan 통합).
        """
        return {}

    def run(self) -> SimResult:
        """N턴 시뮬 실행.

        본 commit 1차: 빈 결과 반환 (★ schema 본질)
        2차 commit: 1턴 진짜 작동
        3차 commit: N턴 자동
        """
        return SimResult(
            sim_id=f"sim_{self.config.scenario_id}",
            config_summary=(
                f"max_turns={self.config.max_turns}, "
                f"player={self.config.player_llm_model}, "
                f"gm={self.config.gm_llm_model}"
            ),
            total_turns=self.config.max_turns,
            completed_turns=0,
            end_reason="not_yet_implemented_1차_commit",
        )
