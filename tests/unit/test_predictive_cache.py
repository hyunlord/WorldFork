"""예측 생성 캐시 단위 테스트 — put/take/has + turn_count 자동 무효 + LRU 상한."""

from typing import cast
from unittest.mock import MagicMock

from service.sim import predictive_cache
from service.sim.predictive_cache import Prediction


def _pred() -> Prediction:
    return cast(Prediction, MagicMock(spec=Prediction))


def _clear() -> None:
    predictive_cache._CACHE.clear()


def test_put_take_hit() -> None:
    _clear()
    p = _pred()
    predictive_cache.put("s1", 3, "주변을 살핀다", p)
    assert predictive_cache.has("s1", 3, "주변을 살핀다")
    got = predictive_cache.take("s1", 3, "주변을 살핀다")
    assert got is p
    # take는 1회 소비 — 두 번째는 미스
    assert predictive_cache.take("s1", 3, "주변을 살핀다") is None


def test_turn_count_invalidates() -> None:
    _clear()
    predictive_cache.put("s1", 3, "탐색", _pred())
    # 다음 턴(turn_count 불일치) → 미스(stale 자동 무효)
    assert predictive_cache.take("s1", 4, "탐색") is None
    # 원 키는 유지(소비 안 됨)
    assert predictive_cache.has("s1", 3, "탐색")


def test_action_whitespace_normalized() -> None:
    _clear()
    predictive_cache.put("s1", 1, "  탐색한다 ", _pred())
    assert predictive_cache.take("s1", 1, "탐색한다") is not None


def test_miss_for_freeform() -> None:
    _clear()
    predictive_cache.put("s1", 1, "주변을 살핀다", _pred())
    # 예측 안 된 자유 입력 → 미스(기존 경로 폴백)
    assert predictive_cache.take("s1", 1, "벽의 이끼를 핥아본다") is None


def test_lru_bound() -> None:
    _clear()
    for i in range(predictive_cache._MAX_ENTRIES + 10):
        predictive_cache.put("s1", i, f"act{i}", _pred())
    assert predictive_cache.stats()["entries"] == predictive_cache._MAX_ENTRIES
    # 가장 오래된 항목은 밀려남
    assert not predictive_cache.has("s1", 0, "act0")


def test_clear_session() -> None:
    _clear()
    predictive_cache.put("s1", 1, "a", _pred())
    predictive_cache.put("s2", 1, "b", _pred())
    predictive_cache.clear_session("s1")
    assert not predictive_cache.has("s1", 1, "a")
    assert predictive_cache.has("s2", 1, "b")
