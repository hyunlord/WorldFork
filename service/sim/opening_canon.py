"""AI GM 오프닝 슬라이스 — 최소 캐논 앵커(성인식 → 미궁1층 → 첫 조우 → 마무리).

NARRATIVE_DESIGN §4 끌개 모델: 오프닝 4비트만 앵커로 둔다(740화 인덱싱 금지 — YAGNI).
GM이 비트를 견인할 최소 사실(인물 5축·장소·첫 몹·무기)만 담는다. 세부 캐논은 WORLD_BIBLE.

★ IP 규율: 코드·git·로그 = 변환명(투르윈/카이라/라스카니아), 화면 = 원작명은 프론트
unmaskIp(frontend/lib/api/v2.ts). 여기 문자열은 전부 변환명 — git에 원작 IP가 들어가지 않는다.
(gm_narrator.build_gm_canon은 _PERSONA_ANCHOR에 원작명을 박아 두어 재사용하지 않는다 — 변환명 충돌.)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from service.sim.disposition import Disposition
from service.util.korean import eul_reul

# 변환명(화면 unmask: 투르윈→비요른, 카이라→아이나르).
PLAYER_NAME = "투르윈"
KAIRA_NAME = "카이라"

# 동행 동료 카이라(아이나르) 5축 — WORLD_BIBLE §11(충성80/저돌75/지혜35/변덕25/유대65).
KAIRA_DISPOSITION = Disposition(
    loyalty=80,
    aggression=75,
    wisdom=35,
    whimsy=25,
    bond=65,
    background="흑곰족 대검 전사, 성인식 동기. 우직·강직, 돌격 본능에 신중함은 부족.",
)


class Beat(StrEnum):
    """오프닝 4비트(끌개) — 발생은 예약, 전개·결과는 자유."""

    COMING_OF_AGE = "coming_of_age"  # 성인식 — 무기 선택(=빌드)
    DUNGEON_ENTRY = "dungeon_entry"  # 미궁 1층 수정 동굴 진입
    FIRST_ENCOUNTER = "first_encounter"  # 첫 조우(전투)
    AFTERMATH = "aftermath"  # 마무리 — 관계·결과 기록


_BEAT_ORDER: tuple[Beat, ...] = (
    Beat.COMING_OF_AGE,
    Beat.DUNGEON_ENTRY,
    Beat.FIRST_ENCOUNTER,
    Beat.AFTERMATH,
)


def next_beat(beat: Beat) -> Beat | None:
    """다음 비트(마지막이면 None) — scene_transition 검증·진행에 쓴다."""
    i = _BEAT_ORDER.index(beat)
    return _BEAT_ORDER[i + 1] if i + 1 < len(_BEAT_ORDER) else None


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


_ANCHORS: dict[Beat, BeatAnchor] = {
    Beat.COMING_OF_AGE: BeatAnchor(
        Beat.COMING_OF_AGE,
        goal=f"{PLAYER_NAME}이 부족장 앞 성인식에서 무기를 골라 전사로 인정받는다.",
        scene="흑곰족 성지. 부족장이 청년들을 호명한다. 무기대에 양손도끼·양손망치·대검이 놓였다.",
        hint="무기 선택(=빌드)을 선택지로. 우직한 야만인을 연기하나 속은 계산적인 톤.",
    ),
    Beat.DUNGEON_ENTRY: BeatAnchor(
        Beat.DUNGEON_ENTRY,
        goal="일행이 한 달 만에 열린 미궁 1층 수정 동굴에 발을 들인다.",
        scene="미궁 1층. 벽의 수정이 스스로 빛나 횃불이 필요 없다. 통로가 어둠 속으로 뻗는다.",
        hint="탐색 방향·경계 태세를 선택지로. 미궁 한 달 주기·생존 긴장을 깐다.",
    ),
    Beat.FIRST_ENCOUNTER: BeatAnchor(
        Beat.FIRST_ENCOUNTER,
        goal="첫 조우(고블린/칼날늑대)와 교전한다. 무기·동료 운용이 생사를 가른다.",
        scene="수정 동굴 깊은 곳. 어둠 속에서 첫 몬스터가 모습을 드러낸다.",
        hint="전술 결정(돌격/엄호/거리)을 선택지로. 전투는 생생히, 더 길게 묘사.",
    ),
    Beat.AFTERMATH: BeatAnchor(
        Beat.AFTERMATH,
        goal=f"교전을 매듭짓고 {KAIRA_NAME}와의 관계·전리품을 정리한다.",
        scene="조우가 끝난 자리. 마석과 정수가 떨어져 있고, 동료가 곁에 선다.",
        hint="전리품 처리·동료와의 한마디를 선택지로. 결과를 세계에 남긴다.",
    ),
}


def anchor_for(beat: Beat) -> BeatAnchor:
    """비트의 끌개 앵커."""
    return _ANCHORS[beat]


def kaira_present(beat: Beat) -> bool:
    """카이라(아이나르) 동행 여부 — 미궁 진입부터 합류(성향 반응 노출 무대)."""
    return beat in (Beat.DUNGEON_ENTRY, Beat.FIRST_ENCOUNTER, Beat.AFTERMATH)


@dataclass(frozen=True)
class WeaponChoice:
    """성인식 무기 선택(=빌드). scenario.py 성인식과 정합."""

    id: str
    label: str
    build: str


# 성인식 무기 — 빌드 분기(WORLD_BIBLE §3.2 탱커/딜러 딜레마).
COMING_OF_AGE_WEAPONS: tuple[WeaponChoice, ...] = (
    WeaponChoice("axe", "양손도끼", "균형(탱커형 생존)"),
    WeaponChoice("hammer", "양손망치", "고화력 둔기"),
    WeaponChoice("greatsword", "대검", "고위험 고화력 딜러"),
)

# 첫 조우 몹(몹명은 IP 무관 — 일반 판타지 명칭).
FIRST_FOES: tuple[str, ...] = ("고블린", "칼날늑대")


@dataclass(frozen=True)
class SceneDetail:
    """비트별 '둘러보면 드러나는' 코드 소유 사실(A3.1).

    ★ 효과=코드 파생: explore가 GM 환각 아닌 이 사실을 공개한다(GM은 서술만). item이
    있으면 줍기(take) 가능 — 임의 아이템 날조 차단. 변환명·일반 판타지 명칭만(IP 0).
    """

    key: str  # dedup 키(discovered 추적)
    detail: str  # 공개 시 GM에 넘길 확정 사실(서술 재료)
    item: str | None = None  # 줍기 가능하면 아이템명


# 비트별 발견 가능 디테일(둘러보기→공개, 줍기→아이템). 코드 소유 — GM이 지어내지 않는다.
_SCENE_DETAILS: dict[Beat, tuple[SceneDetail, ...]] = {
    Beat.COMING_OF_AGE: (
        SceneDetail(
            "weapon_rack", "무기대에 양손도끼·양손망치·대검이 가지런히 놓여 빛을 받는다."
        ),
        SceneDetail("chieftain_gaze", "부족장이 청년들을 차례로 훑어보며 호명을 기다린다."),
    ),
    Beat.DUNGEON_ENTRY: (
        SceneDetail(
            "crystal_light", "벽을 메운 수정이 맥동하듯 빛을 토해 통로 깊은 곳까지 비춘다."
        ),
        SceneDetail(
            "drag_marks", "바닥에 길게 긁힌 자국이 어둠 속으로 이어진다 — 끌려간 흔적."
        ),
        SceneDetail(
            "crystal_shard",
            "발치에 손바닥만 한 수정 파편이 떨어져 희미하게 빛난다.",
            item="수정 파편",
        ),
    ),
    Beat.FIRST_ENCOUNTER: (
        SceneDetail("foe_shadow", "어둠 속에서 낮은 그르렁거림과 함께 윤곽이 다가온다."),
        SceneDetail("narrow_path", "통로가 좁아 물러설 곳이 마땅치 않다 — 정면 승부다."),
    ),
    Beat.AFTERMATH: (
        SceneDetail("spoils", "쓰러진 적 곁에 마석과 정수가 흩어져 있다."),
        SceneDetail("companion_breath", "카이라가 거친 숨을 고르며 곁에 선다."),
    ),
}


def scene_details(beat: Beat) -> tuple[SceneDetail, ...]:
    """비트의 발견 가능 디테일(A3.1 효과 매퍼가 explore/take에 쓴다)."""
    return _SCENE_DETAILS.get(beat, ())


@dataclass(frozen=True)
class BeatChoice:
    """비트 선택지 — ★ 코드 정의(LLM 생성 아님): 즉시 표시·결정적·캐논 grounding."""

    id: str
    label: str


# 비전투/전투 스캐폴드 선택지 — 각 선택이 실제 state_delta·전환을 일으킨다(무의미 금지).
# 성인식은 무기군(COMING_OF_AGE_WEAPONS, id=axe/hammer/greatsword)과 동기화(확정 정합).
_DUNGEON_CHOICES: tuple[BeatChoice, ...] = (
    BeatChoice("advance", "미궁 깊숙이 나아간다"),  # 진입 → 첫 조우로 전환
    BeatChoice("scout", "벽의 수정과 통로를 살핀다"),
    BeatChoice("guard", "카이라에게 선두 경계를 맡기고 전진한다"),
)
_ENCOUNTER_CHOICES: tuple[BeatChoice, ...] = (
    BeatChoice("charge", "도끼로 정면 돌격한다"),
    BeatChoice("flank", "카이라와 좌우로 협공한다"),
    BeatChoice("careful", "거리를 두고 빈틈을 노린다"),
    BeatChoice("defend", "방어 태세로 적의 공격을 받아친다"),
)
_AFTERMATH_CHOICES: tuple[BeatChoice, ...] = (
    BeatChoice("loot", "쓰러진 적의 전리품을 챙긴다"),
    BeatChoice("talk", "카이라와 한마디 나눈다"),
    BeatChoice("descend", "미궁 더 깊은 곳으로 향한다"),
)


def beat_choices(beat: Beat) -> tuple[BeatChoice, ...]:
    """비트별 코드 선택지 — 즉시 표시(LLM 대기 없음). 성인식은 무기군과 동기화."""
    if beat is Beat.COMING_OF_AGE:
        return tuple(
            BeatChoice(w.id, f"{w.label}{eul_reul(w.label)} 든다 — {w.build}")
            for w in COMING_OF_AGE_WEAPONS
        )
    if beat is Beat.DUNGEON_ENTRY:
        return _DUNGEON_CHOICES
    if beat is Beat.FIRST_ENCOUNTER:
        return _ENCOUNTER_CHOICES
    return _AFTERMATH_CHOICES


def build_anchor_prompt(beat: Beat, *, weapon: str = "") -> str:
    """현 비트의 캐논 앵커를 GM 프롬프트용 문자열로(변환명). 근거 없는 설정 차단용."""
    a = anchor_for(beat)
    lines = [
        f"[비트] {beat.value}",
        f"[목표] {a.goal}",
        f"[장면] {a.scene}",
        f"[선택지 성격] {a.hint}",
        f"[주인공] {PLAYER_NAME} — 흑곰족 거구 바바리안, 현대인의 영혼이 깃들었다. "
        "우직한 야만인을 연기하나 실리적·계산적.",
    ]
    if weapon:
        lines.append(f"[무기] {weapon} — 일관되게 쓴다.")
    if kaira_present(beat):
        lines.append(
            f"[동료] {KAIRA_NAME} — 흑곰족 대검 전사, 성인식 동기. 저돌적(돌격 본능)·우직, "
            "신중함은 부족. 성향대로 자율 반응하며 플레이어 지시에 순응/변형/거부한다."
        )
    if beat is Beat.FIRST_ENCOUNTER:
        lines.append(f"[적] {', '.join(FIRST_FOES)} 중 하나 — 미궁 1층 잡몹. 습성·약점이 있다.")
    return "\n".join(lines)
