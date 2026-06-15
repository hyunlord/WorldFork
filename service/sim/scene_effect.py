"""A3.1 — 자유 입력 → 코드 확정 효과 매퍼 (de-rail 1단계).

★ 핵심(NARRATIVE_DESIGN §4·ROADMAP A3): 전투의 confirmed 패턴(코드가 확정 → GM이
'이미 일어난 일'을 서술)을 모든 자유 행동으로 일반화한다. 분류된 intent를 작은 결정적
효과로 환원해 자유 입력이 '항상 무언가를 바꾸게' 한다(stuck 소멸의 토대 — 전환 자체는 A3.2).

가드레일(하드 라인):
- 효과는 전부 코드 파생. GM 파생 금지(GM은 서술만). hp/flags/무기/전환/stones는 코드 소관.
- 불확실 intent → 보수적 기본(최소 progress + 순수 서술, confirmed 없음). 과잉 부여·크래시 0.
- 단조 progress 불변식: 모든 효과의 progress_delta ≥ 1(진행도를 줄이지 않는다).
- 아이템은 코드 소유 SceneDetail.item만 부여(임의 날조 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from service.api.schemas.freeform_action import IntentMatch
from service.engine.content_pack import require_active_pack
from service.sim.opening_canon import Beat, scene_details
from service.util.korean import eul_reul


@dataclass(frozen=True)
class ProgressPolicy:
    """progress 증분 정책 — ★ 설정값(하드코딩 산재 금지). A3.3 도그푸딩 튜닝 1순위.

    전진(advance/move)이 캐논 진행의 주 동력. 둘러보기/대화는 실효는 있되 캐논 진행엔
    모듈하게(머무를 자유 보존) — explore는 Phase 0 제안(+20)보다 낮춰 시작.
    """

    advance: int = 40  # 전진 = 주 동력(move/enter)
    explore: int = 6  # 둘러보기 = 실효 있되 모듈(머무를 자유)
    dialogue: int = 2  # 대화 = 캐논 진행엔 거의 영향 X
    take: int = 4  # 줍기
    default: int = 3  # 불확실/기타 = 최소(보수적). ★ 단조 불변식 위해 ≥1
    # soft-floor(no-stuck 보강) — 정체(새 발견 없음·비전진)가 누적되면 견인 가속.
    stall_after: int = 2  # 연속 정체 N회 후 bump
    stall_bump: int = 20  # 정체 시 progress 가속분(단조 — 항상 증가)


_POLICY = ProgressPolicy()


def beat_threshold(beat: Beat) -> int | None:
    """비트별 progress 전환 임계(팩 소유 — A1.2c). 없으면 None(이벤트 게이트 비트)."""
    return require_active_pack().beat_thresholds.get(beat)


def pull_flavor(beat: Beat, progress: int) -> str | None:
    """progress-gated 비트의 차오른 정도별 '끌개' 견인 힌트(★ 수치 노출 금지 — 메타 차단).

    진행도가 높을수록 [목표]가 강하게 다가오게 서술시킨다. 임계·텍스트는 팩 소유. 임계 없으면 None.
    """
    thr = beat_threshold(beat)
    if not thr:
        return None
    low, mid, high = require_active_pack().pull_flavors
    ratio = progress / thr
    if ratio < 0.34:
        return low
    if ratio < 0.67:
        return mid
    return high

# intent.matched_action(PlayerActionType value) → 효과 분류.
_ADVANCE_ACTIONS = frozenset({"move", "enter_dungeon", "enter_next_floor", "move_chamber"})
_EXPLORE_ACTIONS = frozenset({"explore", "examine_stats"})
_DIALOGUE_ACTIONS = frozenset({"dialogue", "communicate"})
# 줍기 — intent 어휘에 없어 키워드로(handle은 코드 소유 takeable만 부여).
_TAKE_WORDS = ("집어", "집는", "줍", "주워", "챙", "획득", "거둬", "거둔", "주섬")


@dataclass
class SceneEffect:
    """자유 행동의 코드 확정 효과 — GM은 confirmed_lines를 '이미 일어난 일'로 서술만 한다."""

    progress_delta: int = 0
    confirmed_lines: list[str] = field(default_factory=list)
    newly_discovered: list[str] = field(default_factory=list)  # SceneDetail.key
    inventory_add: list[str] = field(default_factory=list)
    relationship_delta: dict[str, int] = field(default_factory=dict)
    kind: str = "default"  # explore/advance/dialogue/take/default(진단·테스트용)


def _next_unseen(beat: Beat, discovered: list[str], *, with_item: bool = False) -> object:
    """아직 공개 안 된 다음 디테일(with_item이면 줍기 가능한 것만). 없으면 None."""
    for d in scene_details(beat):
        if d.key in discovered:
            continue
        if with_item and d.item is None:
            continue
        return d
    return None


def map_effect(
    intent: IntentMatch | None,
    action: str,
    beat: Beat,
    discovered: list[str],
    *,
    kaira_name: str = "",
    policy: ProgressPolicy = _POLICY,
) -> SceneEffect:
    """분류된 intent + 행동 텍스트 → 코드 확정 효과(★ 결정적, GM 무관).

    discovered: 현 비트에서 이미 공개된 SceneDetail.key 목록(반복 방지).
    kaira_name: 카이라 동행 시 이름(대화 시 관계 증분 대상). 비동행이면 빈 문자열.
    """
    matched = intent.matched_action if intent and intent.matched_action else None

    # 줍기 — 코드 소유 takeable만(임의 아이템 날조 0).
    if any(w in action for w in _TAKE_WORDS):
        d = _next_unseen(beat, discovered, with_item=True)
        if d is not None:
            item = d.item  # type: ignore[attr-defined]
            return SceneEffect(
                progress_delta=policy.take,
                confirmed_lines=[
                    f"{d.detail} {item}{eul_reul(item)} 손에 넣는다."  # type: ignore[attr-defined]
                ],
                newly_discovered=[d.key],  # type: ignore[attr-defined]
                inventory_add=[item],
                kind="take",
            )
        return SceneEffect(
            progress_delta=policy.take,
            confirmed_lines=["마땅히 챙길 만한 것은 보이지 않는다."],
            kind="take",
        )

    # 둘러보기 — 코드 소유 디테일을 차례로 공개(반복 방지).
    if matched in _EXPLORE_ACTIONS:
        d = _next_unseen(beat, discovered)
        if d is not None:
            return SceneEffect(
                progress_delta=policy.explore,
                confirmed_lines=[d.detail],  # type: ignore[attr-defined]
                newly_discovered=[d.key],  # type: ignore[attr-defined]
                kind="explore",
            )
        return SceneEffect(
            progress_delta=policy.explore,
            confirmed_lines=["더는 새로이 눈에 띄는 것이 없다."],
            kind="explore",
        )

    # 전진 — 주 동력(캐논 견인). 전환 판정은 A3.2가 progress로.
    if matched in _ADVANCE_ACTIONS:
        return SceneEffect(
            progress_delta=policy.advance,
            confirmed_lines=["한 걸음 더 깊이 발을 들인다."],
            kind="advance",
        )

    # 대화 — 카이라 동행 시 소폭 유대(+1). 발화 자체는 _kaira_react가 confirmed로.
    if matched in _DIALOGUE_ACTIONS:
        rel = {kaira_name: 1} if kaira_name else {}
        return SceneEffect(
            progress_delta=policy.dialogue, relationship_delta=rel, kind="dialogue"
        )

    # 불확실/기타 — 보수적: 최소 progress + 순수 서술(confirmed 없음). 과잉 부여 0.
    return SceneEffect(progress_delta=policy.default, kind="default")
