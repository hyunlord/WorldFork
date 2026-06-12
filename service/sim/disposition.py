"""V3 Phase 0 — 성향 코어 (LLM 없이, 코드만 결정적).

DESIGN_disposition_engine.md 1·2장 구현. 파티원의 5축 성향과, 성향 → 기본 행동
패턴 매핑(default_action)을 코드로 둔다. LLM은 Phase 1(지시 해석)에서 얹는다 —
Phase 0은 '게임 먼저': 코드만으로 동료가 성향대로 자율 행동하는지 검증한다.

핵심: 평소 틱의 행동 결정은 0토큰(코드). LLM은 분기점·개입에서만(Phase 1+).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from service.sim.status import StatusEffect

# 성향 임계 — 높음/낮음 경계. DESIGN 2장 기본 패턴 매핑에 사용.
_HIGH = 60
_LOW = 40


class DispoAction(StrEnum):
    """성향이 고른 기본 행동 (코드 결정 — 즉각)."""

    CHARGE = "charge"  # 돌격 (저돌↑ + 적 근처)
    RANGED = "ranged"  # 엄폐 후 원거리 (신중 + 적 근처)
    SCOUT = "scout"  # 정찰 (지혜↑ + 미탐색)
    RESCUE = "rescue"  # 구원 (유대↑ + 아군 위기)
    FOLLOW = "follow"  # 추종 (기본 — 플레이어 곁)
    HOLD = "hold"  # 대기 (특이 상황 없음)


@dataclass(frozen=True)
class Disposition:
    """5축 성향 (각 0-100). DESIGN 1장. 영문 필드 + 한글 축명 주석.

    한 줄 배경(background)은 Phase 1 지시 해석(LLM)에서 쓰일 맥락 — Phase 0은 미사용.
    """

    loyalty: int = 50  # 충성 — 지시 수용도(낮으면 자기 판단)
    aggression: int = 50  # 저돌 — 자율 전투(돌격/정찰)
    wisdom: int = 50  # 지혜 — 위험 간파(거부 근거)
    whimsy: int = 50  # 변덕 — 예측 가능성(Phase 1 LLM 불확실성 축)
    bond: int = 50  # 유대 — 관계 가중(아군 구원)
    background: str = ""  # 한 줄 배경(예: "전직 도굴꾼, 함정에 예민") — Phase 1용

    def __post_init__(self) -> None:
        for axis, val in (
            ("loyalty", self.loyalty),
            ("aggression", self.aggression),
            ("wisdom", self.wisdom),
            ("whimsy", self.whimsy),
            ("bond", self.bond),
        ):
            if not 0 <= val <= 100:
                raise ValueError(f"성향 {axis}는 0-100이어야 한다: {val}")


@dataclass
class Companion:
    """파티원 — 성향 + 게임 상태(위치/HP). Phase 0은 1명으로 검증.

    current_order — Phase 1 지시 해석이 설정하는 현재 명령(코드 틱 반영). None이면
    성향 자율(default_action). 거부 시 None 유지.
    """

    name: str
    disposition: Disposition
    pos: tuple[int, int] = (0, 0)
    hp: int = 100
    max_hp: int = 100
    attack: int = 12
    current_order: DispoAction | None = None
    status: list[StatusEffect] = field(default_factory=list)  # 출혈 등(Phase 2 enemy_step)

    @property
    def downed(self) -> bool:
        """전투불능(HP 0) — 틱 행동 중지, 렌더 '쓰러짐'. 제거/부활 없음(슬라이스)."""
        return self.hp <= 0


@dataclass
class WorldView:
    """동료가 인식하는 현재 상황 — default_action 입력(결정적).

    틱 루프가 게임 상태에서 채워 넣는다(코드). 모든 필드는 코드가 계산.
    """

    enemy_near: bool = False  # 적대 조우 존재
    enemy_distance: int = 99  # 가장 가까운 적까지 거리(맨해튼)
    unexplored: bool = False  # 미탐색 영역 남음
    ally_in_danger: bool = False  # 아군/플레이어 위기(저HP)


def default_action(d: Disposition, w: WorldView) -> DispoAction:
    """성향 → 기본 행동 (★ 코드, 즉각, LLM 없이). DESIGN 2장 매핑.

    우선순위: 아군 구원 > 전투(저돌성 분기) > 정찰 > 추종.
    같은 상황도 성향이 다르면 다른 행동을 고른다 — Phase 0 검증의 핵심.
    """
    # 유대↑ + 아군 위기 → 구원(동료를 살리러 — 최우선)
    if w.ally_in_danger and d.bond >= _HIGH:
        return DispoAction.RESCUE
    # 적 근처 → 저돌성으로 돌격/원거리 분기
    if w.enemy_near:
        if d.aggression >= _HIGH:
            return DispoAction.CHARGE
        if d.aggression <= _LOW:
            return DispoAction.RANGED
        # 중간 저돌 — 거리로 결정(붙었으면 돌격, 멀면 원거리)
        return DispoAction.CHARGE if w.enemy_distance <= 1 else DispoAction.RANGED
    # 미탐색 + 지혜↑ → 정찰(영민한 동료가 앞서 살핌)
    if w.unexplored and d.wisdom >= _HIGH:
        return DispoAction.SCOUT
    # 기본 — 플레이어 곁을 따른다
    return DispoAction.FOLLOW


# 자주 쓰는 성향 프리셋 — 검증/데모용(저돌적 전사 vs 신중한 정찰꾼 등).
PRESET_BERSERKER = Disposition(
    loyalty=60, aggression=85, wisdom=35, whimsy=40, bond=55,
    background="흑곰족 전사, 피를 보면 물러서지 않는다",
)
PRESET_SCOUT = Disposition(
    loyalty=45, aggression=30, wisdom=80, whimsy=30, bond=50,
    background="전직 도굴꾼, 함정과 위험에 예민하다",
)
PRESET_GUARDIAN = Disposition(
    loyalty=80, aggression=50, wisdom=60, whimsy=20, bond=85,
    background="동료를 지키는 데 헌신하는 방패잡이",
)
