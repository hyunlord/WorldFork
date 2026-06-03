"""일반 적 조우 등장 라인 (서빙 2단계) 단위 테스트."""

from __future__ import annotations

from service.sim.encounter_narrative import _i_ga, compose_encounter_line


def test_includes_enemy_name() -> None:
    line = compose_encounter_line({"name": "뱀파이어", "enemy_type": "undead"}, 0)
    assert "뱀파이어" in line
    # 등장 서사 — 마지막에 전투 직전 호흡 마침표
    assert line.endswith(".")


def test_type_flavored_opener_undead() -> None:
    # undead → 음산한 어조('어둠'/'썩은' 류) — physical default와 구분
    line = compose_encounter_line({"name": "구울", "enemy_type": "undead"}, 0)
    assert any(kw in line for kw in ("어둠", "썩은"))


def test_unknown_type_falls_back_physical() -> None:
    line = compose_encounter_line({"name": "오크", "enemy_type": "weird"}, 0)
    assert "오크" in line  # 미지 타입도 physical opener로 라인 생성


def test_varies_by_turn() -> None:
    # 같은 적이 또 나와도 turn 회전으로 다른 문장(조용한 반복 X)
    e = {"name": "스켈레톤", "enemy_type": "undead"}
    lines = {compose_encounter_line(e, t) for t in range(6)}
    assert len(lines) >= 2


def test_josa_batchim() -> None:
    assert _i_ga("뱀파이어") == "가"  # 받침 無
    assert _i_ga("구울") == "이"  # 받침 有
    assert _i_ga("") == "가"


def test_empty_name_safe() -> None:
    line = compose_encounter_line({"enemy_type": "physical"}, 1)
    assert "적" in line  # name 부재 → '적' fallback
