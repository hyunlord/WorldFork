"""예측 생성 캐시 — 정해진 선택지(버튼)를 유휴 시간에 미리 생성, 클릭 시 캐시 히트.

게임 선택지는 한정(추천 버튼)이라 예측 가능(자유 입력 채팅과 다름). 사용자가 현재 서사를
읽는 유휴 동안 다음 후보를 dry-run(상태 복사본)으로 미리 생성해 캐시한다. 다음 행동이
예측과 맞고 상태가 그대로면(turn_count 일치) 즉시 반환 → decode 천장과 무관한 0초 체감.

★ stale 안전: turn_count를 키에 포함 → 한 턴이라도 진행하면 옛 예측은 키 불일치로 자동 무효.
★ 정직: 자유 입력(예측 불가)은 캐시 미스 → 기존 스트리밍 경로로 폴백.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from service.api.schemas.freeform_action import FreeformActionResponse
    from service.sim.session_manager import SessionState

# 비용 균형 — 안 누른 후보는 낭비라 캐시를 작게 묶는다(유휴 생성 + LRU).
_MAX_ENTRIES = 64

_Key = tuple[str, int, str]


@dataclass
class Prediction:
    """예측된 한 행동의 완성 결과 — 응답 + 적중 시 커밋할 다음 상태."""

    response: FreeformActionResponse
    next_state: SessionState


_CACHE: OrderedDict[_Key, Prediction] = OrderedDict()


def _key(session_id: str, turn_count: int, action: str) -> _Key:
    return (session_id, turn_count, action.strip())


def put(
    session_id: str, turn_count: int, action: str, pred: Prediction
) -> None:
    """예측 결과 저장 — LRU 상한 초과 시 오래된 항목부터 제거."""
    k = _key(session_id, turn_count, action)
    _CACHE[k] = pred
    _CACHE.move_to_end(k)
    while len(_CACHE) > _MAX_ENTRIES:
        _CACHE.popitem(last=False)


def take(session_id: str, turn_count: int, action: str) -> Prediction | None:
    """예측 적중 시 pop(1회 소비). 미스면 None(자유 입력/예측 안 됨 → 기존 경로)."""
    return _CACHE.pop(_key(session_id, turn_count, action), None)


def has(session_id: str, turn_count: int, action: str) -> bool:
    """이미 예측됨 여부 — 중복 백그라운드 생성 방지."""
    return _key(session_id, turn_count, action) in _CACHE


def clear_session(session_id: str) -> None:
    """세션 종료/리셋 시 정리."""
    for k in [k for k in _CACHE if k[0] == session_id]:
        _CACHE.pop(k, None)


def stats() -> dict[str, int]:
    """관측용 — 캐시 크기."""
    return {"entries": len(_CACHE), "max": _MAX_ENTRIES}
