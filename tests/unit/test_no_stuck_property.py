"""A3.3 — no-stuck property test (구조적 안전성 증명).

★ A3의 핵심 증명: 자유 입력으로 어떻게 막 쳐도 엔진은 멈추지 않는다.
임의 입력 시퀀스를 라우터에 흘려 단언:
  - 안전(safety): 매 act가 선택지 ≥1(막다른 길 0), 비트는 역행 0(앞으로만), 예외/500 0.
  - 생존(liveness): progress 누적·soft-floor로 끝내 마무리(aftermath) 도달 — 전진/탐색/무작위 모두.

LLM(gm_beat·interpret_command·classify_intent·resolve_round)은 전부 mock — 전환·progress·
선택지는 코드 결정(map_effect/_beat_done)이라 결정적. stuck 회귀를 구조적으로 막는다.
"""

from __future__ import annotations

import random
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from service.api.gm_session_router import _PERSISTENT_WORLD, _SESSIONS, router
from service.api.schemas.freeform_action import IntentMatch
from service.sim.disposition import DispoAction
from service.sim.disposition_command import CommandReaction, CommandResponse
from service.sim.narrative_combat import RoundResult
from service.sim.narrative_gm import GMBeatResult, GMStateDelta

# 비트 순서(역행 검출용).
_ORDER = ["coming_of_age", "dungeon_entry", "first_encounter", "aftermath"]

# 임의 입력 풀 — 모든 효과 종류 + mechanical 분류 가능(9B 미의존). (kind, payload)
_FREE = [
    "북쪽으로 나아간다",  # move/advance
    "주변을 둘러본다",  # explore
    "수정 파편을 주워 챙긴다",  # take
    "휴식한다",  # rest → default
    "카이라에게 말을 건다",  # dialogue(directive)
    "춤을 춘다",  # 불확실 → default
    "뒤돌아 도망친다",  # flee(첫 조우 회피)
]
_CHOICES = ["axe", "advance", "scout", "guard", "loot", "talk", "descend", "charge", "flank"]


def _beat() -> GMBeatResult:
    return GMBeatResult(narration="장면.", state_delta=GMStateDelta())


def _reaction() -> CommandResponse:
    return CommandResponse(CommandReaction.COMPLY, DispoAction.FOLLOW, "근거", "발화")


def _defeat(**kw: object) -> RoundResult:
    # 전투는 한 방에 처치 → 마무리로 전진(liveness 보장).
    return RoundResult(
        lines=["적을 쓰러뜨렸다."], player_hp=120, player_status=[], foe_hp=0,
        kaira_reaction=_reaction(), foe_defeated=True, drops=[], illustration=None,
    )


def _client() -> TestClient:
    _SESSIONS.clear()
    _PERSISTENT_WORLD.flags.clear()
    _PERSISTENT_WORLD.npc_memories.clear()
    _PERSISTENT_WORLD.relationships.clear()
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _act(c: TestClient, sid: str, rng: random.Random) -> dict:
    """임의 입력 1회 — 절반은 선택지, 절반은 자유 텍스트."""
    if rng.random() < 0.5:
        payload = {"session_id": sid, "choice_id": rng.choice(_CHOICES)}
    else:
        payload = {"session_id": sid, "free_text": rng.choice(_FREE)}
    r = c.post("/api/gm/session/act", json=payload)
    assert r.status_code == 200, f"act 실패 status={r.status_code} payload={payload}"
    return r.json()


# 모든 LLM mock — 코드 경로만 결정적으로 검증.
def _patches():  # type: ignore[no-untyped-def]
    return (
        patch("service.api.gm_session_router.gm_beat", return_value=_beat()),
        patch("service.api.gm_session_router.interpret_command", return_value=_reaction()),
        patch(
            "service.api.gm_session_router.classify_intent",
            return_value=IntentMatch(matched_action=None, confidence=0.2, reason="자유"),
        ),
        patch("service.api.gm_session_router.resolve_round", side_effect=_defeat),
    )


class TestSafetyInvariants:
    def test_arbitrary_sequences_never_dead_end_or_regress(self) -> None:
        # ★ 임의 시퀀스 — 매 act 선택지≥1, 비트 역행 0, 예외/500 0.
        for seed in range(8):
            rng = random.Random(seed)
            c = _client()
            p1, p2, p3, p4 = _patches()
            with p1, p2, p3, p4:
                body = c.post("/api/gm/session/start").json()
                assert len(body["choices"]) >= 1
                idx = _ORDER.index(body["beat"])
                for _ in range(40):
                    body = _act(c, body["session_id"], rng)
                    assert len(body["choices"]) >= 1, "막다른 길(선택지 0)"
                    new_idx = _ORDER.index(body["beat"])
                    assert new_idx >= idx, "비트 역행"
                    idx = new_idx


class TestLiveness:
    def _run_to_end(self, actions: list[dict], max_steps: int = 60) -> str:
        c = _client()
        p1, p2, p3, p4 = _patches()
        with p1, p2, p3, p4:
            sid = c.post("/api/gm/session/start").json()["session_id"]
            body = {"beat": "coming_of_age"}
            for i in range(max_steps):
                payload = {"session_id": sid, **actions[min(i, len(actions) - 1)]}
                body = c.post("/api/gm/session/act", json=payload).json()
                if body["beat"] == "aftermath":
                    return "aftermath"
        return body["beat"]

    def test_advance_only_reaches_aftermath(self) -> None:
        # 무기 → 전진 반복 → 누적 끌개로 첫 조우 → 전투 처치 → 마무리.
        actions = [{"choice_id": "axe"}] + [{"free_text": "북쪽으로 나아간다"}]
        assert self._run_to_end(actions) == "aftermath"

    def test_explore_only_reaches_aftermath_via_soft_floor(self) -> None:
        # ★ 디테일 소진 후 둘러보기만 반복해도 soft-floor가 끌어 마무리 도달(막다른 길 0).
        actions = [{"choice_id": "axe"}] + [{"free_text": "주변을 둘러본다"}]
        assert self._run_to_end(actions) == "aftermath"

    def test_random_with_weapon_reaches_aftermath(self) -> None:
        # 무기 확정 후 무작위로 막 쳐도 끝내 마무리(누적·전투처치·회피 모두 전진).
        for seed in range(5):
            rng = random.Random(seed + 100)
            c = _client()
            p1, p2, p3, p4 = _patches()
            with p1, p2, p3, p4:
                sid = c.post("/api/gm/session/start").json()["session_id"]
                c.post("/api/gm/session/act", json={"session_id": sid, "choice_id": "axe"})
                reached = False
                for _ in range(60):
                    body = _act(c, sid, rng)
                    if body["beat"] == "aftermath":
                        reached = True
                        break
                assert reached, f"seed={seed}: 마무리 미도달(stuck)"
