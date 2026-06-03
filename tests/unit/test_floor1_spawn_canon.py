"""서빙 4단계 — 1층 스폰 고증 게이팅 (결정적 단위 테스트).

스폰은 확률적(rate 0.30)이라 브라우저 E2E로는 flaky. 1층 풀 구성 자체는
결정적으로 검증 — 엔트리 몬스터만, 뱀파이어(심층) 등 제외.
"""

from __future__ import annotations

import random

from service.canon.loader import load_canon_facts
from service.canon.spawn import SpawnTable
from service.sim.spawn_trigger import (
    FLOOR1_MONSTER_NAMES,
    floor_canonical_pool,
    trigger_spawn,
)


def test_floor1_pool_is_canonical_entry() -> None:
    pool = floor_canonical_pool(1)
    assert pool is not None
    names = {e.name for e in pool}
    assert names == set(FLOOR1_MONSTER_NAMES)
    # 본문 1층 수정동굴 엔트리 — 고블린/슬라임 포함
    assert "고블린" in names
    assert "슬라임" in names
    # 심층 몬스터(뱀파이어) 부재 — 1층 입구 고증
    assert "뱀파이어" not in names


def test_floor1_pool_weak_grade() -> None:
    # codebase grade 1 = 약체(엔트리). 강한 등급 누출 없음.
    pool = floor_canonical_pool(1)
    assert pool is not None
    assert all(e.grade == 1 for e in pool)


def test_deeper_and_village_use_existing() -> None:
    # 2층+/마을(0층)은 None → 기존 스폰 유지(이 단계 범위는 1층 입구).
    assert floor_canonical_pool(2) is None
    assert floor_canonical_pool(0) is None


def test_trigger_spawn_floor1_excludes_vampire() -> None:
    st = SpawnTable(load_canon_facts())
    random.seed(0)
    names: set[str] = set()
    for t in range(60):
        for e in trigger_spawn(
            "던전 1층",
            "dungeon",
            turn_count=t * 5,
            last_spawn_turn=-100,
            spawn_table=st,
            floor_number=1,
        ):
            names.add(str(e["name"]))
    assert names  # 무언가는 스폰됨
    assert "뱀파이어" not in names
    # race 잡종(종족명) 미스폰
    assert not (names & {"바바리안족", "고양이귀", "드워프", "이세계인"})
    # 전부 canonical 엔트리 풀 소속
    assert names <= set(FLOOR1_MONSTER_NAMES)


def test_gm_max_tokens_tuned() -> None:
    from service.sim.gm_narrator import GM_MAX_TOKENS

    # 서사 80-160 충분 — 상한 축소(벽시계 단축), 잘림 없는 범위
    assert 120 <= GM_MAX_TOKENS <= 200
