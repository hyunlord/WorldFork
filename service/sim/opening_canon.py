"""AI GM 오프닝 슬라이스 — 캐논 타입(메커니즘) + 접근자(팩 소비).

NARRATIVE_DESIGN §4 끌개 모델: 오프닝 4비트 앵커. ★ A1.2c: WorldFork 데이터(앵커·장면 디테일·
무기·선택지·이름)는 콘텐츠팩 소유(service/content/worldfork/pack.py). 여기엔 타입 정의 +
순서/디스패치 로직만 두고, 데이터는 require_active_pack()에서 읽는다(작품 무관 엔진).

★ IP 규율: 코드·git·로그 = 변환명. 화면 = 원작명은 프론트 unmaskIp(frontend/lib/api/v2.ts).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from service.engine.content_pack import require_active_pack
from service.util.korean import eul_reul


class Beat(StrEnum):
    """오프닝 4비트(끌개) — 발생은 예약, 전개·결과는 자유."""

    COMING_OF_AGE = "coming_of_age"  # 성인식 — 무기 선택(=빌드)
    DUNGEON_ENTRY = "dungeon_entry"  # 미궁 1층 수정 동굴 진입
    FIRST_ENCOUNTER = "first_encounter"  # 첫 조우(전투)
    AFTERMATH = "aftermath"  # 마무리 — 관계·결과 기록


def next_beat(beat: Beat) -> Beat | None:
    """다음 비트(마지막이면 None) — 순서는 팩 소유. scene_transition 검증·진행에 쓴다."""
    beats = require_active_pack().beats
    i = beats.index(beat)
    return beats[i + 1] if i + 1 < len(beats) else None


def parse_beat(value: str) -> Beat | None:
    """문자열 → Beat(유효하지 않으면 None) — GM state_delta.scene_transition 검증."""
    try:
        return Beat(value)
    except ValueError:
        return None


@dataclass(frozen=True)
class BeatAnchor:
    """한 비트의 끌개 — 목표(부드럽게 견인)·장면 배경·선택지 성격 힌트."""

    beat: Beat
    goal: str
    scene: str
    hint: str


def anchor_for(beat: Beat) -> BeatAnchor:
    """비트의 끌개 앵커(팩 소유)."""
    return require_active_pack().anchors[beat]


def kaira_present(beat: Beat) -> bool:
    """동행 동료 합류 여부(팩 소유) — 미궁 진입부터 합류(성향 반응 노출 무대)."""
    return beat in require_active_pack().companion_present_beats


@dataclass(frozen=True)
class WeaponChoice:
    """성인식 무기 선택(=빌드). scenario.py 성인식과 정합."""

    id: str
    label: str
    build: str


@dataclass(frozen=True)
class SceneDetail:
    """비트별 '둘러보면 드러나는' 코드 소유 사실(A3.1).

    ★ 효과=코드 파생: explore가 GM 환각 아닌 이 사실을 공개한다(GM은 서술만). item이
    있으면 줍기(take) 가능 — 임의 아이템 날조 차단. 변환명·일반 판타지 명칭만(IP 0).
    """

    key: str  # dedup 키(discovered 추적)
    detail: str  # 공개 시 GM에 넘길 확정 사실(서술 재료)
    item: str | None = None  # 줍기 가능하면 아이템명


def scene_details(beat: Beat) -> tuple[SceneDetail, ...]:
    """비트의 발견 가능 디테일(팩 소유 — A3.1 효과 매퍼가 explore/take에 쓴다)."""
    return require_active_pack().scene_details.get(beat, ())


@dataclass(frozen=True)
class BeatChoice:
    """비트 선택지 — ★ 코드 정의(LLM 생성 아님): 즉시 표시·결정적·캐논 grounding."""

    id: str
    label: str


def beat_choices(beat: Beat) -> tuple[BeatChoice, ...]:
    """비트별 코드 선택지(팩 소유) — 즉시 표시(LLM 대기 없음). 성인식은 무기군과 동기화."""
    pack = require_active_pack()
    if beat is Beat.COMING_OF_AGE:
        return tuple(
            BeatChoice(w.id, f"{w.label}{eul_reul(w.label)} 든다 — {w.build}")
            for w in pack.weapons
        )
    return pack.beat_choices.get(beat, ())


def build_anchor_prompt(beat: Beat, *, weapon: str = "") -> str:
    """현 비트의 캐논 앵커를 GM 프롬프트용 문자열로(변환명). 근거 없는 설정 차단용.

    구조([비트]/[목표]…)는 엔진, 이름·설명·앵커 텍스트는 팩 소유(A1.2c).
    """
    pack = require_active_pack()
    a = anchor_for(beat)
    lines = [
        f"[비트] {beat.value}",
        f"[목표] {a.goal}",
        f"[장면] {a.scene}",
        f"[선택지 성격] {a.hint}",
        f"[주인공] {pack.player_name} — {pack.player_brief}",
    ]
    if weapon:
        lines.append(f"[무기] {weapon} — 일관되게 쓴다.")
    if kaira_present(beat):
        lines.append(f"[동료] {pack.companion.name} — {pack.companion_brief}")
    if beat is Beat.FIRST_ENCOUNTER:
        lines.append(f"[적] {', '.join(pack.first_foe_names)} 중 하나 — {pack.first_foe_desc}")
    return "\n".join(lines)
